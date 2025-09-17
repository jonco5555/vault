import pytest
import pytest_asyncio
import asyncio
from testcontainers.postgres import PostgresContainer

from vault.manager.auth_server import AuthService
from vault.user.auth_client import AuthClient
from vault.manager.db_manager import DBManager


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


@pytest.mark.asyncio
async def test_grpc_flow(db_manager):
    print("stating auth service...")
    auth_service = AuthService(
        db=db_manager,
        server_ip="127.0.0.1",
        server_port=10000,
    )

    auth_service_task = asyncio.create_task(auth_service.start_auth_server())

    auth_client = AuthClient(
        server_ip="127.0.0.1",
        server_port=10000,
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

    print("do_secure_call...")
    res: bytes = await auth_client.do_secure_call(
        username=USERNAME,
        password=PASSWORD,
        payload_type="echo",
        payload=b"hello from client",
    )
    print("server responded:", res)

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
