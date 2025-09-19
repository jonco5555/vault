import logging

import grpc

from vault.common.generated.vault_pb2 import (
    GenerateSharesRequest,
    GenerateSharesResponse,
    PartialDecrypted,
    RegisterResponse,
    RetrieveSecretResponse,
    Secret,
    StoreSecretResponse,
)
from vault.common.generated.vault_pb2_grpc import (
    BootstrapStub,
    ManagerServicer,
    ShareServerStub,
    add_ManagerServicer_to_server,
)
from vault.crypto.ssl import generate_cert_and_keys
from vault.manager.db_manager import DBManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Manager(ManagerServicer):
    def __init__(
        self,
        port: int,
        db_host: str,
        db_port: int,
        db_username: str,
        db_password: str,
        db_name: str,
        num_of_share_servers: int,
    ):
        self._logger = logging.getLogger(__class__.__name__)
        self._port = port
        self._cert, self._ssl_pubkey, self._ssl_privkey = generate_cert_and_keys(
            common_name="manager"
        )

        # grpc server
        creds = grpc.ssl_server_credentials([(self._ssl_privkey, self._cert)])
        self._server = grpc.aio.server()
        add_ManagerServicer_to_server(self, self._server)
        self._port = self._server.add_secure_port(f"[::]:{self._port}", creds)

        # DB
        self._db = DBManager(
            f"postgresql+asyncpg://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

        self._num_of_share_servers = num_of_share_servers
        self._ready = False

    async def start(self):
        await self._db.start()
        await self._server.start()
        self._ready = True
        self._logger.info(f"Server started on port {self._port}")

    async def close(self):
        self._ready = False
        self._db.close()
        if self._server:
            await self._server.stop(grace=5.0)
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

        ########################
        # TODO: Deploy bootstrap
        ########################
        bootstrap_address = "bootstrap.example.com:50051"

        # Sending generate shares request to bootstrap
        creds = grpc.ssl_channel_credentials(root_certificates=None)
        async with grpc.aio.secure_channel(bootstrap_address, creds) as channel:
            stub = BootstrapStub(channel)
            response: GenerateSharesResponse = await stub.GenerateShares(
                GenerateSharesRequest(
                    threshold=self._num_of_share_servers + 1,  # +1 for the user
                    num_of_shares=self._num_of_share_servers + 1,
                    public_keys=public_keys,
                )
            )
        ######################
        # TODO: Kill bootstrap
        ######################

        # Get user's share, assuming it is the last one
        user_share = response.encrypted_shares.pop()

        # Send shares to share servers
        servers_addresses = await self._db.get_servers_addresses()
        for share, server_address in zip(response.encrypted_shares, servers_addresses):
            async with grpc.aio.secure_channel(server_address, creds) as channel:
                stub = ShareServerStub(channel)
                await stub.StoreShare(encrypted_share=share, user_id=request.user_id)

        # Send to user his share and encryption key
        return RegisterResponse(
            encrypted_share=user_share, encrypted_key=response.encrypted_key
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

        ###################################
        # TODO: Validate request.auth_token
        ###################################

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
        creds = grpc.ssl_channel_credentials(root_certificates=None)
        for server_address in servers_addresses:
            async with grpc.aio.secure_channel(server_address, creds) as channel:
                stub = ShareServerStub(channel)
                response = await stub.Decrypt(user_id=request.user_id, secret=secret)
                partial_decryptions.append(response.partial_decrypted_secret)
        return RetrieveSecretResponse(
            partial_decryptions=partial_decryptions, secret=secret
        )

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

    async def _validate_num_of_servers_in_db(self, num_in_db: int, context):
        if num_in_db != self._num_of_share_servers:
            self._logger.debug(
                f"Not enough share servers registered. Required: {self._num_of_share_servers}, Available: {num_in_db}"
            )
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("Not enough share servers registered")
            return False
        return True
