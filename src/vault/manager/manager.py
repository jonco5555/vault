from vault.manager.db_manager import DBManager
from vault.grpc.vault_pb2_grpc import (
    ManagerServicer,
    add_ManagerServicer_to_server,
    BootstrapStub,
)
from vault.grpc.vault_pb2 import (
    RegisterResponse,
    GenerateSharesRequest,
    GenerateSharesResponse,
)
import logging
import grpc

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
        # grpc server
        self._port = port
        self._server = grpc.aio.server()
        add_ManagerServicer_to_server(self, self._server)
        self._server.add_insecure_port(f"[::]:{self._port}")

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
        if not self._ready:
            self._logger.debug("Server is not ready to accept requests")
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Server is not ready")
            return RegisterResponse()

        if await self._db.user_exists(request.user_id):
            self._logger.debug(f"User {request.user_id} already exists")
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("User already exists")
            return RegisterResponse()

        ########################
        # TODO: Deploy bootstrap
        ########################

        # Sending generate shares request to bootstrap
        bootstrap_address = "bootstrap.example.com:50051"
        async with grpc.aio.insecure_channel(bootstrap_address) as channel:
            stub = BootstrapStub(channel)
            response: GenerateSharesResponse = await stub.GenerateShares(
                GenerateSharesRequest(
                    num_of_shares=self._num_of_share_servers + 1,  # +1 for the user
                    user_public_key=request.user_public_key,
                )
            )

        ##############################################
        # TODO: send to all share servers their shares
        ##############################################

        # Send to user his share and encryption key
        user_share = next(
            (s.share for s in response.shares if s.share_server_id == request.user_id)
        )
        return RegisterResponse(
            share=user_share, encryption_key=response.encryption_key
        )
