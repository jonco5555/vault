import typing
import pytest
import pytest_asyncio
import asyncio
from testcontainers.postgres import PostgresContainer

from vault.manager.auth_server import AuthService
from vault.user.auth_client import AuthClient
from vault.manager.db_manager import DBManager
from vault.manager.manager import Manager
from vault.common.generated import vault_pb2

MANAGER_IP = "127.0.0.1"
MANAGER_PORT = 9000

AUTH_IP = "127.0.0.1"
AUTH_PORT = 10000


@pytest_asyncio.fixture
async def db_manager(db: PostgresContainer):
    db_url = db.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://", 1
    )
    print(f"Using database URL: {db_url}")
    db = DBManager(db_url)
    await db.start()
    yield db
    await db.close()


@pytest_asyncio.fixture
async def manager(db: PostgresContainer) -> typing.AsyncGenerator[Manager, None]:
    manager = Manager(
        port=MANAGER_PORT,
        db_host=db.get_container_host_ip(),
        db_port=db.get_exposed_port(5432),
        db_username=db.username,
        db_password=db.password,
        db_name=db.dbname,
        num_of_share_servers=3,
        ip=MANAGER_IP,
    )
    await manager.start()
    yield manager
    await manager.close()


@pytest.mark.asyncio
async def test_grpc_flow(manager, db_manager):
    print("stating auth service...")
    auth_service = AuthService(
        db=db_manager,
        server_ip=AUTH_IP,
        server_port=AUTH_PORT,
        manager_server_ip=MANAGER_IP,
        manager_server_port=MANAGER_PORT,
    )

    auth_service_task = asyncio.create_task(auth_service.start_auth_server())

    auth_client = AuthClient(
        server_ip=AUTH_IP,
        server_port=AUTH_PORT,
    )

    USERNAME = "alice"
    PASSWORD = "password"
    BAD_PASSWORD = "bad_password"

    print("registring client...")
    await auth_client.register(
        username=USERNAME,
        password=PASSWORD,
    )
    print("client registered")

    print("registring another client...")
    await auth_client.register(
        username=USERNAME + "2",
        password=PASSWORD,
    )
    print("client another registered")

    print("do_secure_call...")
    try:
        res: bytes = await auth_client.do_secure_call(
            username=USERNAME,
            password=PASSWORD,
            request_probuf=vault_pb2.RetrieveSecretRequest(
                user_id=USERNAME, secret_id="secret_id", auth_token="to remove"
            ),
        )
        print("server responded:", res)
    except Exception as e:
        print(f"Error expected: user doesnt exist {e}")

    print("BAD do_secure_call...")
    try:
        res: bytes = await auth_client.do_secure_call(
            username=USERNAME,
            password=BAD_PASSWORD,
            payload_type="echo",
            payload=b"hello from bad client",
        )
        assert False
    except Exception:
        pass

    auth_service_task.cancel()
