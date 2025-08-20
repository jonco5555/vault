import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from vault.db_manager import DBManager
from common.generated import vault_setup_pb2

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

@pytest.mark.asyncio
async def test_add_and_get_server(db_manager: DBManager):
    _container_id = "1234"
    _invalid_container_id = "12345"

    _type = vault_setup_pb2.ServiceType.SHARE_SERVER
    _ip_address = "1.2.3.4"
    _public_key = b"publickeydata"

    reg_req = vault_setup_pb2.ServiceData()
    reg_req.type = _type
    reg_req.container_id = _container_id
    reg_req.ip_address = _ip_address
    reg_req.public_key = _public_key
    
    await db_manager.add_server(reg_req)
    result = await db_manager.get_server(_invalid_container_id)
    assert result is None

    result: vault_setup_pb2.ServiceData = await db_manager.get_server(_container_id)
    assert result is not None
    assert result.container_id == _container_id
    assert result.type == _type
    assert result.ip_address == _ip_address
    assert result.public_key == _public_key

    try:
        result = await db_manager.remove_server(_invalid_container_id)
        assert False
    except:
        pass

    result = await db_manager.remove_server(_container_id)

    result = await db_manager.get_server(_container_id)
    assert result is None