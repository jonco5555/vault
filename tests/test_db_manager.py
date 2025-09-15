import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from vault.common import types
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
async def test_add_and_get_secret(db_manager: DBManager):
    user_id = "user1"
    secret_id = "sec1"
    secret = b"supersecret"
    await db_manager.add_secret(user_id, secret_id, secret)
    result = await db_manager.get_secret(user_id, secret_id)
    assert result == secret


@pytest.mark.asyncio
async def test_add_user_and_get_pubkey(db_manager: DBManager):
    user_id = "user2"
    pubkey = b"publickeydata"
    await db_manager.add_user(user_id, pubkey)
    result = await db_manager.get_user_public_key(user_id)
    assert result == pubkey


@pytest.mark.asyncio
async def test_user_exists_true(db_manager: DBManager):
    user_id = "user3"
    pubkey = b"pubkeyexists"
    await db_manager.add_user(user_id, pubkey)
    exists = await db_manager.user_exists(user_id)
    assert exists is True


@pytest.mark.asyncio
async def test_user_exists_false(db_manager: DBManager):
    user_id = "nonexistent_user"
    exists = await db_manager.user_exists(user_id)
    assert exists is False


@pytest.mark.asyncio
async def test_add_and_get_server(db_manager: DBManager):
    _container_id = "1234"
    _invalid_container_id = "12345"

    _type = types.ServiceType.SHARE_SERVER
    _ip_address = "1.2.3.4"
    _public_key = b"publickeydata"

    reg_req = types.ServiceData(
        type=_type,
        container_id=_container_id,
        ip_address=_ip_address,
        public_key=_public_key,
    )

    await db_manager.add_server(reg_req)
    result = await db_manager.get_server(_invalid_container_id)
    assert result is None

    result: types.ServiceData = await db_manager.get_server(_container_id)
    assert result is not None
    assert result.container_id == _container_id
    assert result.type == _type
    assert result.ip_address == _ip_address
    assert result.public_key == _public_key

    try:
        result = await db_manager.remove_server(_invalid_container_id)
        assert False
    except Exception:
        pass

    result = await db_manager.remove_server(_container_id)

    result = await db_manager.get_server(_container_id)
    assert result is None
