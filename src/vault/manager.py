from vault.db_manager import DBManager
from vault.setup_pb2_grpc import ManagerServicer, add_ManagerServicer_to_server
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
        self._server = grpc.aio.server()
        add_ManagerServicer_to_server(self, self._server)
        self._server.add_insecure_port(f"[::]:{self._port}")

        # DB
        self._db = DBManager(
            f"postgresql+asyncpg://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

    async def start(self):
        await self._db.start()
        await self._server.start()
        self._logger.info(f"Manager started on port {self._port}")

    async def close(self):
        self._db.close()
        if self._server:
            await self._server.stop(grace=5.0)
        self._logger.info("Manager stopped")
