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
        DB_host: str,
        DB_port: int,
        DB_username: str,
        DB_password: str,
        DB_name: str,
        vault_table_name: str,
        pubkeys_table_name: str,
    ):
        self._logger = logging.getLogger(__class__.__name__)
        # grpc server
        self._port = port
        self._server = None

        # DBs
        self._DB_base_url = f"postgresql+psycopg2://{DB_username}:{DB_password}@{DB_host}:{DB_port}/{DB_name}"
        self._vault_table_name = vault_table_name
        self._pubkeys_table_name = pubkeys_table_name

    def init_tables(self):
        from vault.sql import init_db

        init_db(self._vault_table_name, self._pubkeys_table_name)

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
