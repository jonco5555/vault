from vault.db_manager import DBManager
from vault.vault_pb2_grpc import ManagerServicer, add_ManagerServicer_to_server
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
    ):
        self._logger = logging.getLogger(__class__.__name__)
        # grpc server
        self._port = port
        self._server = None

        # DB
        self._db_base_url = (
            f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        self._db = DBManager(self._db_base_url)

    async def start(self):
        self._server = grpc.aio.server()
        add_ManagerServicer_to_server(self, self._server)
        self._server.add_insecure_port(f"[::]:{self._port}")
        await self._server.start()
        self._logger.info(f"Manager started on port {self._port}")

    async def stop(self):
        if self._server:
            await self._server.stop(grace=5.0)
        self._logger.info("Manager stopped")
