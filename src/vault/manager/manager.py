import logging
from typing import List

import grpc

from vault.common import types
from vault.common.generated.vault_pb2 import (
    DecryptRequest,
    DecryptResponse,
    GenerateSharesRequest,
    GenerateSharesResponse,
    PartialDecrypted,
    RegisterResponse,
    RetrieveSecretResponse,
    Secret,
    StoreSecretResponse,
    StoreShareRequest,
    StoreShareResponse,
)
from vault.common.generated.vault_pb2_grpc import (
    BootstrapStub,
    ManagerServicer,
    ShareServerStub,
    add_ManagerServicer_to_server,
)
from vault.crypto.certs import generate_component_cert_and_key, load_ca_cert
from vault.manager.db_manager import DBManager
from vault.manager.setup_master import SetupMaster

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Manager(ManagerServicer):
    def __init__(
        self,
        name: str,
        port: int,
        db_host: str,
        db_port: int,
        db_username: str,
        db_password: str,
        db_name: str,
        num_of_share_servers: int,
        setup_master_port: int,
        setup_unit_port: int,
        bootstrap_port: int,
        share_server_port: int,
        docker_image: str,
        ca_cert_path: str = "certs/ca.crt",
        ca_key_path: str = "certs/ca.key",
    ):
        self._logger = logging.getLogger(__class__.__name__)
        self._port = port
        self._cert, self._ssl_privkey = generate_component_cert_and_key(
            name=name,
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
        )
        self._ca_cert = load_ca_cert(ca_cert_path)
        self._num_of_share_servers = num_of_share_servers
        self._share_servers_data: List[types.ServiceData] = []
        self._ready = False
        self._bootstrap_port = bootstrap_port
        self._share_server_port = share_server_port

        # grpc server
        creds = grpc.ssl_server_credentials([(self._ssl_privkey, self._cert)])
        self._server = grpc.aio.server()
        add_ManagerServicer_to_server(self, self._server)
        self._port = self._server.add_secure_port(f"[::]:{self._port}", creds)

        # DB
        self._db = DBManager(
            f"postgresql+asyncpg://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

        # Setup master
        self._setup_master_service: SetupMaster = SetupMaster(
            port=setup_master_port,
            setup_unit_port=setup_unit_port,
            db=self._db,
            docker_image=docker_image,
        )

    async def start(self):
        await self._db.start()
        await self._setup_master_service.start()

        await self.launch_all_share_servers()

        await self._server.start()
        self._ready = True
        self._logger.info(f"Server started on port {self._port}")

    async def stop(self):
        self._ready = False
        await self._server.stop(grace=5.0)
        await self.terminate_all_share_servers()

        # db must live until _setup_master_service dies
        await self._setup_master_service.stop()
        await self._db.close()
        self._logger.info("Server stopped")

    async def Register(self, request, context):
        self._logger.info(f"Received registration request from user {request.user_id}")
        if not self._validate_server_ready(
            context
        ) or not await self._validate_user_not_exists(request.user_id, context):
            return RegisterResponse()

        # Add user to DB
        await self._db.add_user(request.user_id, request.user_public_key)

        # Get public keys of share servers
        public_keys = await self._db.get_servers_keys()
        if not self._validate_num_of_servers_in_db(len(public_keys), context):
            return RegisterResponse()

        # Add user's public key to the end of the list, where the bootstrap expects it
        public_keys.append(request.user_public_key)

        # Create bootstrap
        bootstrap_server_data = (
            await self._setup_master_service.spawn_bootstrap_server()
        )
        bootstrap_address = (
            f"{bootstrap_server_data.container_name}:{self._bootstrap_port}"
        )

        # Sending generate shares request to bootstrap
        creds = grpc.ssl_channel_credentials(root_certificates=self._ca_cert)
        async with grpc.aio.secure_channel(bootstrap_address, creds) as channel:
            stub = BootstrapStub(channel)
            bootstrap_response: GenerateSharesResponse = await stub.GenerateShares(
                GenerateSharesRequest(
                    threshold=self._num_of_share_servers + 1,  # +1 for the user
                    num_of_shares=self._num_of_share_servers + 1,
                    public_keys=public_keys,
                )
            )

        # terminate bootstrap
        await self._setup_master_service.terminate_service(bootstrap_server_data)

        # Get user's share, assuming it is the last one
        user_share = bootstrap_response.encrypted_shares.pop()

        # Send shares to share servers
        servers_addresses = await self._db.get_servers_addresses()
        creds = grpc.ssl_channel_credentials(root_certificates=self._ca_cert)
        for share, server_address in zip(
            bootstrap_response.encrypted_shares, servers_addresses
        ):
            async with grpc.aio.secure_channel(
                f"{server_address}:{self._share_server_port}", creds
            ) as channel:
                stub = ShareServerStub(channel)
                share_server_response: StoreShareResponse = await stub.StoreShare(
                    StoreShareRequest(user_id=request.user_id, encrypted_share=share)
                )
                if not share_server_response.success:
                    self._logger.error(
                        f"Failed to store share on server {server_address}"
                    )

        # Send to user his share and encryption key
        return RegisterResponse(
            encrypted_share=user_share, encrypted_key=bootstrap_response.encrypted_key
        )

    async def StoreSecret(self, request, context):
        self._logger.info(
            f"Storing secret {request.secret_id} for user {request.user_id}"
        )
        if not self._validate_server_ready(
            context
        ) or not await self._validate_user_exists(request.user_id, context):
            return StoreSecretResponse(success=False)

        # TODO: make sure .proto Secret is saved correctly in the DB
        await self._db.add_secret(
            request.user_id, request.secret_id, request.secret.SerializeToString()
        )
        return StoreSecretResponse(success=True)

    async def RetrieveSecret(self, request, context):
        self._logger.info(
            f"Retrieving secret {request.secret_id} for user {request.user_id}"
        )

        if not self._validate_server_ready(
            context
        ) or not await self._validate_user_exists(request.user_id, context):
            return StoreSecretResponse()

        # Get secret from DB
        bytes_secret = await self._db.get_secret(request.user_id, request.secret_id)
        if not bytes_secret:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Secret not found")
            return StoreSecretResponse()
        secret = Secret()
        secret.ParseFromString(bytes_secret)

        # Get partial decryptions from share servers
        servers_addresses = await self._db.get_servers_addresses()
        partial_decryptions: list[PartialDecrypted] = []
        creds = grpc.ssl_channel_credentials(root_certificates=self._ca_cert)
        for server_address in servers_addresses:
            async with grpc.aio.secure_channel(
                f"{server_address}:{self._share_server_port}", creds
            ) as channel:
                stub = ShareServerStub(channel)
                response: DecryptResponse = await stub.Decrypt(
                    DecryptRequest(user_id=request.user_id, secret=secret)
                )
                partial_decryptions.append(response.partial_decrypted_secret)
        return RetrieveSecretResponse(
            partial_decryptions=partial_decryptions, secret=secret
        )

    async def launch_all_share_servers(self):
        for i in range(self._num_of_share_servers):
            self._logger.debug(f"creating share server number {i}")
            self._share_servers_data.append(
                await self._setup_master_service.spawn_share_server()
            )

        # TODO: make paralel and by not blocking on each share server and sample the db.

    async def terminate_all_share_servers(self):
        for share_server_data in self._share_servers_data:
            self._logger.debug(
                f"terminating share server with container id {share_server_data.container_id}"
            )
            await self._setup_master_service.terminate_service(share_server_data)

        # TODO: make paralel and by not blocking on each share server and sample the db.

    # private methdods
    def _validate_server_ready(self, context):
        if not self._ready:
            self._logger.debug("Server is not ready to accept requests")
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Server is not ready")
            return False
        return True

    async def _validate_user_exists(self, user_id, context):
        if not await self._db.user_exists(user_id):
            self._logger.debug(f"User {user_id} does not exist")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User does not exist")
            return False
        return True

    async def _validate_user_not_exists(self, user_id, context):
        if await self._db.user_exists(user_id):
            self._logger.debug(f"User {user_id} already exists")
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("User already exists")
            return False
        return True

    def _validate_num_of_servers_in_db(self, num_in_db: int, context):
        if num_in_db != self._num_of_share_servers:
            self._logger.debug(
                f"Not enough share servers registered. Required: {self._num_of_share_servers}, Available: {num_in_db}"
            )
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("Not enough share servers registered")
            return False
        return True
