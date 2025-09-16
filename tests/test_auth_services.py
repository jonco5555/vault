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
async def test_basic_flow(db_manager):
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
    PASSWORD = "secret-password"
    print("registring client...")
    await auth_client.register(USERNAME, PASSWORD)
    print("client registered")

    print("do_secure_call...")
    res: bytes = await auth_client.do_secure_call(
        USERNAME, PASSWORD, "echo", b"hello from client"
    )
    # assert b"hello from client" == res
    print("server responded:", res)

    auth_service_task.cancel()
