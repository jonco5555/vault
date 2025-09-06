import typing
from unittest.mock import patch

import grpc
import grpc_testing
import pytest
import pytest_asyncio
from grpc_testing._server._server import _Server
from testcontainers.postgres import PostgresContainer

from vault.common.generated import vault_pb2 as pb2
from vault.common.generated.vault_pb2 import (
    DESCRIPTOR,
    Secret,
    StoreSecretRequest,
)
from vault.manager.manager import Manager


@pytest_asyncio.fixture(scope="module")
def db() -> typing.Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:16") as container:
        yield container


@pytest_asyncio.fixture
async def manager(db: PostgresContainer):
    manager = Manager(
        port=0,
        db_host=db.get_container_host_ip(),
        db_port=db.get_exposed_port(5432),
        db_username=db.username,
        db_password=db.password,
        db_name=db.dbname,
        num_of_share_servers=3,
    )
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


def invoke_method(request, server: _Server, method: str):
    method_descriptor = DESCRIPTOR.services_by_name["Manager"].methods_by_name[method]
    rpc = server.invoke_unary_unary(
        method_descriptor=method_descriptor,
        invocation_metadata={},
        request=request,
        timeout=1,
    )
    return rpc.termination()


@pytest.mark.asyncio
async def test_store_secret_works(manager: Manager, manager_server: _Server):
    # Arrange
    request = StoreSecretRequest(
        user_id="user1",
        secret_id="secret1",
        secret=Secret(
            c1=pb2.Key(x="1234", y="2345"),
            c2=pb2.Key(x="3456", y="4567"),
            ciphertext=b"ciphertext",
        ),
    )
    with (
        patch.object(Manager, "_validate_server_ready", return_value=True),
        patch.object(Manager, "_validate_user_exists", return_value=True),
    ):
        # Act
        response, _, code, _ = invoke_method(request, manager_server, "StoreSecret")
        response = await response

    # Assert
    assert code == grpc.StatusCode.OK
    assert response.success
    assert (
        await manager._db.get_secret("user1", "secret1")
        == request.secret.SerializeToString()
    )
