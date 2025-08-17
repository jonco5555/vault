import pytest
from testcontainers.postgres import PostgresContainer
from vault.db_manager import DBManager


@pytest.fixture(scope="module")
def db_manager():
    with PostgresContainer("postgres:16") as container:
        db_url = container.get_connection_url()
        db = DBManager(db_url)
        yield db


def test_add_and_get_secret(db_manager: DBManager):
    user_id = "user1"
    secret_id = "sec1"
    secret = b"supersecret"
    db_manager.add_secret(user_id, secret_id, secret)
    result = db_manager.get_secret(user_id, secret_id)
    assert result.user_id == user_id
    assert result.secret_id == secret_id
    assert result.secret == secret


def test_add_and_get_pubkey(db_manager: DBManager):
    user_id = "user2"
    pubkey = b"publickeydata"
    db_manager.add_pubkey(user_id, pubkey)
    result = db_manager.get_pubkey(user_id)
    assert result.user_id == user_id
    assert result.public_key == pubkey
