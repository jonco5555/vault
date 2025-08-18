import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from vault.manager.db_manager import DBManager


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
async def test_add_and_get_secret(db_manager: DBManager):
    user_id = "user1"
    secret_id = "sec1"
    secret = b"supersecret"
    await db_manager.add_secret(user_id, secret_id, secret)
    result = await db_manager.get_secret(user_id, secret_id)
    assert result.user_id == user_id
    assert result.secret_id == secret_id
    assert result.secret == secret


@pytest.mark.asyncio
async def test_add_and_get_pubkey(db_manager: DBManager):
    user_id = "user2"
    pubkey = b"publickeydata"
    await db_manager.add_pubkey(user_id, pubkey)
    result = await db_manager.get_pubkey(user_id)
    assert result.user_id == user_id
    assert result.public_key == pubkey
