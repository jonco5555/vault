import logging
from typing import List

import grpc

from vault.common import types
from vault.common.generated.vault_pb2 import (
    DecryptRequest,
    DecryptResponse,
    GenerateSharesRequest,
    GenerateSharesResponse,
    InnerRequest,
    InnerResponse,
    RegisterRequest,
    RegisterResponse,
    RetrieveSecretRequest,
    RetrieveSecretResponse,
    Secret,
    SecureReqMsgWrapper,
    SecureRespMsgWrapper,
    SRPSecondStep,
    SRPThirdStepAck,
    StoreSecretRequest,
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
from vault.crypto.authentication import (
    srp_authentication_server_step_one,
    srp_authentication_server_step_three,
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
        docker_network: str,
        bootstrap_command: str,
        share_server_command: str,
        ca_cert_path: str = "certs/ca.crt",
        ca_key_path: str = "certs/ca.key",
    ):
        self._logger = logging.getLogger(__class__.__name__)
        self._port = port
        self._name = name
        self._cert, self._ssl_privkey = generate_component_cert_and_key(
            name=name,
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
        )
        self._ca_cert = load_ca_cert(ca_cert_path)
        self._num_of_share_servers = num_of_share_servers
        self._share_servers_data: List[types.ServiceData] = []
        self._ready = False
        self._setup_master_port = setup_master_port
        self._setup_unit_port = setup_unit_port
        self._bootstrap_port = bootstrap_port
        self._share_server_port = share_server_port
        self._docker_image = docker_image
        self._docker_network = docker_network
        self._bootstrap_command = bootstrap_command
        self._share_server_command = share_server_command
        self._ca_cert_path = ca_cert_path
        self._ca_key_path = ca_key_path

        # grpc server
        self._client_creds = grpc.ssl_channel_credentials(
            root_certificates=self._ca_cert
        )
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
            server_creds=creds,
            client_creds=self._client_creds,
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

    async def Register(self, request: RegisterRequest, context) -> RegisterResponse:
        self._logger.info("Register request for %s", request.user_id)
        try:
            await self._db.add_auth_client(
                username=request.user_id, verifier=request.verifier, salt=request.salt
            )
        except Exception as e:
            await context.abort(
                grpc.StatusCode.INTERNAL, f"SRP registration failed {e}"
            )
            return

        try:
            return await self._register(request)
        except RuntimeError as e:
            await context.abort(
                grpc.StatusCode.UNKNOWN, f"_vault_register had error: {e}"
            )
            return

    async def SecureCall(self, request_iterator, context):
        """
        Bidirectional stream handling:
        """
        req_iter = request_iterator.__aiter__()

        try:
            auth_step_1_msg: SecureReqMsgWrapper = await req_iter.__anext__()
        except StopAsyncIteration:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no messages")
            return

        if not auth_step_1_msg or not auth_step_1_msg.HasField("auth_step_1"):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "expected auth_step_1"
            )
            return

        username: str = auth_step_1_msg.auth_step_1.username
        password_verifier: str = await self._db.get_auth_client_verifier(username)
        salt: str = await self._db.get_auth_client_salt(username)

        server_public, server_private = srp_authentication_server_step_one(
            username=username,
            password_verifier=password_verifier,
        )
        yield SecureRespMsgWrapper(
            auth_step_2=SRPSecondStep(
                server_public_key=server_public,
                salt=salt,
            )
        )

        try:
            auth_step_3_msg: SecureReqMsgWrapper = await req_iter.__anext__()
        except StopAsyncIteration:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no auth_step_3")
            return

        if not auth_step_3_msg or not auth_step_3_msg.HasField("auth_step_3"):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT, "expected auth_step_3"
            )
            return

        client_public: str = auth_step_3_msg.auth_step_3.client_public_key
        client_session_key_proof: str = (
            auth_step_3_msg.auth_step_3.client_session_key_proof
        )

        _ = srp_authentication_server_step_three(
            username=username,
            password_verifier=password_verifier,
            salt=salt,
            server_private=server_private,
            client_public=client_public,
            client_session_key_proof=client_session_key_proof,
        )

        yield SecureRespMsgWrapper(
            auth_step_3_ack=SRPThirdStepAck(
                ok=True,
            )
        )

        try:
            app_request_msg: SecureReqMsgWrapper = await req_iter.__anext__()
        except StopAsyncIteration:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "expected app_req")
            return

        if not app_request_msg or not app_request_msg.HasField("app_req"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "expected app_req")
            return

        app_req: InnerRequest = app_request_msg.app_req
        try:
            app_resp: InnerResponse = await self._handle_user_inner_request(app_req)
        except RuntimeError as e:
            await context.abort(
                grpc.StatusCode.UNKNOWN, f"_handle_user_inner_request had error: {e}"
            )
            return

        # Must yield here - otherwise python is mad.
        yield SecureRespMsgWrapper(app_resp=app_resp)

    async def _handle_user_inner_request(
        self, inner_request: InnerRequest
    ) -> InnerResponse:
        if inner_request.HasField("store"):
            return InnerResponse(store=await self.store_secret(inner_request.store))
        elif inner_request.HasField("retrieve"):
            return InnerResponse(
                retrieve=await self.retrieve_secret(inner_request.retrieve)
            )
        else:
            raise RuntimeError("unknown InnerRequest body type")

    async def _register(self, request: RegisterRequest) -> RegisterResponse:
        self._logger.info(f"Received registration request from user {request.user_id}")

        self._validate_server_ready()
        await self._validate_user_not_exists(request.user_id)

        # Add user to DB
        await self._db.add_user(request.user_id, request.user_public_key)

        # Get public keys of share servers
        public_keys = await self._db.get_servers_keys()
        self._validate_num_of_servers_in_db(len(public_keys))

        # Add user's public key to the end of the list, where the bootstrap expects it
        public_keys.append(request.user_public_key)

        # Create bootstrap
        bootstrap_server_data = await self._setup_master_service.spawn_server(
            image=self._docker_image,
            container_name=f"vault-bootstrap-{request.user_id}",
            command=self._bootstrap_command,
            network=self._docker_network,
            environment={
                "PORT": self._bootstrap_port,
                "SETUP_UNIT_PORT": self._setup_unit_port,
                "SETUP_MASTER_ADDRESS": self._name,
                "SETUP_MASTER_PORT": self._setup_master_port,
                "CA_CERT_PATH": self._ca_cert_path,
                "CA_KEY_PATH": self._ca_key_path,
            },
        )
        bootstrap_address = (
            f"{bootstrap_server_data.container_name}:{self._bootstrap_port}"
        )

        # Sending generate shares request to bootstrap
        async with grpc.aio.secure_channel(
            bootstrap_address, self._client_creds
        ) as channel:
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
        for share, server_address in zip(
            bootstrap_response.encrypted_shares, servers_addresses
        ):
            async with grpc.aio.secure_channel(
                f"{server_address}:{self._share_server_port}", self._client_creds
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

    async def store_secret(self, request: StoreSecretRequest) -> StoreSecretResponse:
        self._logger.info(
            f"Storing secret {request.secret_id} for user {request.user_id}"
        )
        self._validate_server_ready()
        await self._validate_user_exists(request.user_id)
        await self._db.add_secret(
            request.user_id, request.secret_id, request.secret.SerializeToString()
        )
        return StoreSecretResponse(success=True)

    async def retrieve_secret(
        self, request: RetrieveSecretRequest
    ) -> RetrieveSecretResponse:
        self._logger.info(
            f"Retrieving secret {request.secret_id} for user {request.user_id}"
        )

        self._validate_server_ready()
        await self._validate_user_exists(request.user_id)

        # Get secret from DB
        bytes_secret = await self._db.get_secret(request.user_id, request.secret_id)
        if not bytes_secret:
            raise RuntimeError("Secret not found")
        secret = Secret()
        secret.ParseFromString(bytes_secret)

        # Get partial decryptions from share servers
        servers_addresses = await self._db.get_servers_addresses()
        encrypted_partial_decryptions: list[bytes] = []
        for server_address in servers_addresses:
            async with grpc.aio.secure_channel(
                f"{server_address}:{self._share_server_port}", self._client_creds
            ) as channel:
                stub = ShareServerStub(channel)
                response: DecryptResponse = await stub.Decrypt(
                    DecryptRequest(
                        user_id=request.user_id,
                        secret=secret,
                        user_public_key=await self._db.get_user_public_key(
                            request.user_id
                        ),
                    )
                )
                encrypted_partial_decryptions.append(
                    response.encrypted_partial_decryption
                )
        return RetrieveSecretResponse(
            encrypted_partial_decryptions=encrypted_partial_decryptions, secret=secret
        )

    async def launch_all_share_servers(self):
        environment = {
            "PORT": self._share_server_port,
            "SETUP_UNIT_PORT": self._setup_unit_port,
            "SETUP_MASTER_ADDRESS": self._name,
            "SETUP_MASTER_PORT": self._setup_master_port,
            "CA_CERT_PATH": self._ca_cert_path,
            "CA_KEY_PATH": self._ca_key_path,
        }
        for i in range(self._num_of_share_servers):
            self._logger.info(f"creating share server number {i}")
            self._share_servers_data.append(
                await self._setup_master_service.spawn_server(
                    image=self._docker_image,
                    container_name=f"vault-share-{i}",
                    command=self._share_server_command,
                    network=self._docker_network,
                    environment=environment,
                ),
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
    def _validate_server_ready(self):
        if not self._ready:
            raise RuntimeError("Server is not ready to accept requests")

    async def _validate_user_not_exists(self, user_id):
        if await self._db.user_exists(user_id):
            raise RuntimeError(f"User {user_id} already exists")

    async def _validate_user_exists(self, user_id):
        if not await self._db.user_exists(user_id):
            raise RuntimeError(f"User {user_id} does not exists")

    def _validate_num_of_servers_in_db(self, num_in_db: int):
        if num_in_db != self._num_of_share_servers:
            raise RuntimeError(
                f"Not enough share servers registered. Required: {self._num_of_share_servers}, Available: {num_in_db}"
            )
