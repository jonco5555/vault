import os

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from vault.common import types
from vault.common.setup_unit import SetupUnit
from vault.manager.db_manager import DBManager
from vault.manager.setup_master import SetupMaster


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


@pytest.mark.skip(reason="Fix needed after adding the SetupUnit server")
@pytest.mark.asyncio
async def test_setup_private_api(db_manager: DBManager):
    local_server_address = "127.0.0.1"

    setup_master = SetupMaster(
        db=db_manager,
        server_ip=local_server_address,
    )
    setup_slave = SetupUnit(
        service_type=types.ServiceType.BOOSTRAP_SERVER,
        setup_master_address=local_server_address,
    )

    _container_id = "blabla"
    setup_slave_data = types.ServiceData(
        type=types.ServiceType.BOOSTRAP_SERVER,
        container_id=_container_id,
        ip_address="1.2.3.4",
        public_key=b"blabla",
    )

    await setup_master._wait_for_container_id_unregistration(
        container_id=_container_id, timeout_s=3
    )

    await setup_slave._register(setup_slave_data)
    registered_data: types.ServiceData = (
        await setup_master._wait_for_container_id_registration(
            container_id=_container_id, timeout_s=3
        )
    )
    assert registered_data.container_id == _container_id

    await setup_slave._unregister(_container_id)
    await setup_master._wait_for_container_id_unregistration(
        container_id=_container_id, timeout_s=3
    )


@pytest.mark.skipif(os.geteuid() != 0, reason="Requires root privileges")
@pytest.mark.asyncio
async def test_setup_public_api(db_manager: DBManager):
    local_server_address = "127.0.0.1"

    setup_master = SetupMaster(
        db=db_manager,
        server_ip=local_server_address,
    )

    service_date, container = setup_master.spawn_bootstrap_service()

    # Wait for container to finish and get logs
    container.wait()
    print(container.logs().decode("utf-8"))

    # Optionally remove container
    container.remove()

    setup_master._wait_for_container_id_unregistration(service_date.container_id)
