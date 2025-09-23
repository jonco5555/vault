import typing

import grpc_testing
import pytest
import pytest_asyncio
from grpc_testing._server._server import _Server
from testcontainers.postgres import PostgresContainer

from vault.common.generated.vault_pb2 import (
    DESCRIPTOR,
    RetrieveSecretRequest,
    Secret,
    StoreSecretRequest,
)
from vault.manager.manager import Manager


@pytest.fixture
def secret_id() -> str:
    return "secret1"


@pytest_asyncio.fixture
async def manager(db: PostgresContainer) -> typing.AsyncGenerator[Manager, None]:
    manager = Manager(
        name="manager",
        port=0,
        db_host=db.get_container_host_ip(),
        db_port=db.get_exposed_port(5432),
        db_username=db.username,
        db_password=db.password,
        db_name=db.dbname,
        num_of_share_servers=3,
        setup_master_port=4000,
        setup_unit_port=5000,
        bootstrap_port=5000,
        share_server_port=5000,
        docker_image="vault",
    )
    manager._ready = True
    await manager._db.start()
    yield manager
    await manager._db.close()


@pytest.fixture
def manager_server(manager) -> _Server:
    servicers = {
        DESCRIPTOR.services_by_name["Manager"]: manager,
    }
    return grpc_testing.server_from_dictionary(
        servicers, grpc_testing.strict_real_time()
    )


@pytest.mark.asyncio
async def test_store_secret_works(
    user_id: str,
    manager: Manager,
    manager_server: _Server,
    secret: Secret,
    secret_id: str,
):
    # Arrange
    request = StoreSecretRequest(
        user_id=user_id,
        secret_id=secret_id,
        secret=secret,
    )
    await manager._db.add_user(user_id, b"user_pubkey")

    response = await manager.store_secret(request)
    assert response.success

    # Assert
    assert (
        await manager._db.get_secret(user_id, secret_id) == secret.SerializeToString()
    )


@pytest.mark.asyncio
async def test_retrieve_secret_works(
    manager: Manager,
    manager_server: _Server,
    secret: Secret,
    user_id: str,
    secret_id: str,
):
    # Arrange
    await manager._db.add_user(user_id, b"user_pubkey")
    await manager._db.add_secret(user_id, secret_id, secret.SerializeToString())
    request = RetrieveSecretRequest(user_id=user_id, secret_id=secret_id)
    response = await manager.retrieve_secret(request)

    # Assert
    assert response.secret == secret
