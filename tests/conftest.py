import typing

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from vault.common.generated.vault_pb2 import Key, Secret


@pytest.fixture
def user_id() -> str:
    return "user_1"


@pytest_asyncio.fixture
def db() -> typing.Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:16") as container:
        yield container


@pytest.fixture
def secret() -> Secret:
    return Secret(
        c1=Key(x="1234", y="2345"), c2=Key(x="3456", y="4567"), ciphertext=b"ciphertext"
    )
