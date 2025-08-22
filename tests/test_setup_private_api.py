
import pytest
import pytest_asyncio
import asyncio
from testcontainers.postgres import PostgresContainer
from vault.db_manager import DBManager
from common.generated import vault_setup_pb2

from common.setup_slave import SetupSlave
from manager.setup_master import SetupMaster

@pytest_asyncio.fixture(scope="module")
async def db_manager():
    with PostgresContainer("postgres:16") as container:
        db_url = container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+asyncpg://", 1
        )
        print(f"Using database URL: {db_url}")
        db = DBManager(db_url)
        await db.start()
        yield db
        await db.close()

@pytest.mark.asyncio
async def test_setup_master_slave(db_manager: DBManager):
    local_server_address = "127.0.0.1"

    setup_master = SetupMaster(
        db = db_manager,
        server_ip = local_server_address,
        )
    setup_slave = SetupSlave(
        service_type = vault_setup_pb2.ServiceType.BOOSTRAP_SERVER,
        setup_master_address = local_server_address,
        )

    _container_id = "blabla"
    setup_slave_data = vault_setup_pb2.ServiceData()
    setup_slave_data.type = vault_setup_pb2.ServiceType.BOOSTRAP_SERVER
    setup_slave_data.container_id = _container_id
    setup_slave_data.ip_address = "1.2.3.4"
    setup_slave_data.public_key = b"blabla"

    await setup_master._wait_for_container_id_unregistration(container_id=_container_id, timeout_s=3)

    await setup_slave._register(setup_slave_data)
    registered_data: vault_setup_pb2.ServiceData = await setup_master._wait_for_container_id_registration(container_id=_container_id, timeout_s=3)
    assert registered_data.container_id == _container_id

    await setup_slave._unregister(_container_id)
    await setup_master._wait_for_container_id_unregistration(container_id=_container_id, timeout_s=3)
