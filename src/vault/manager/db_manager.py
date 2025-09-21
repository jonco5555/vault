import logging
from typing import Optional

from sqlalchemy import NullPool, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from vault.common.types import ServiceData

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Base(DeclarativeBase):
    pass


class Vault(Base):
    __tablename__ = "vault"
    user_id: Mapped[str] = mapped_column(primary_key=True)
    secret_id: Mapped[str] = mapped_column(primary_key=True)
    secret: Mapped[bytes] = mapped_column()


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(primary_key=True)
    public_key: Mapped[bytes] = mapped_column()


class Server(Base):
    __tablename__ = "servers"
    container_id: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[int] = mapped_column()
    ip_address: Mapped[str] = mapped_column()
    public_key: Mapped[bytes] = mapped_column()


class AuthClient(Base):
    __tablename__ = "auth_clients"
    username: Mapped[str] = mapped_column(primary_key=True)
    verifier: Mapped[str] = mapped_column()
    salt: Mapped[str] = mapped_column()


class DBManager:
    def __init__(self, db_url: str):
        self._logger = logging.getLogger(__class__.__name__)
        self._logger.info(f"initializing with {db_url=}")
        self._engine = create_async_engine(
            db_url, poolclass=NullPool
        )  # TODO: Using NullPool made the tests pass, need to investigate
        self._session = async_sessionmaker(bind=self._engine, expire_on_commit=False)

    @classmethod
    async def create(cls, db_url: str):
        retval = cls(db_url=db_url)
        await retval.start()

        return retval

    async def start(self):
        self._logger.info("Creating Tables")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        self._logger.info("Stopping DBManager")
        await self._engine.dispose()

    async def add_secret(self, user_id: str, secret_id: str, secret: bytes):
        self._logger.info(f"Adding secret for user_id={user_id}, secret_id={secret_id}")
        async with self._session() as session:
            entry = Vault(user_id=user_id, secret_id=secret_id, secret=secret)
            session.add(entry)
            await session.commit()

    async def get_secret(self, user_id: str, secret_id: str):
        self._logger.info(
            f"Retrieving secret for user_id={user_id}, secret_id={secret_id}"
        )
        async with self._session() as session:
            result = await session.execute(
                select(Vault.secret).filter_by(user_id=user_id, secret_id=secret_id)
            )
            return result.scalar()

    async def add_user(self, user_id: str, public_key: bytes):
        self._logger.info(f"Adding public key for user_id={user_id}")
        async with self._session() as session:
            entry = User(user_id=user_id, public_key=public_key)
            session.add(entry)
            await session.commit()

    async def get_user_public_key(self, user_id: str):
        self._logger.info(f"Retrieving public key for user_id={user_id}")
        async with self._session() as session:
            result = await session.execute(
                select(User.public_key).filter_by(user_id=user_id)
            )
            return result.scalar()

    async def user_exists(self, user_id: str) -> bool:
        self._logger.info(f"Checking if user exists: {user_id}")
        async with self._session() as session:
            result = await session.execute(select(User).filter_by(user_id=user_id))
            return result.scalars().first() is not None

    async def add_server(self, register_request: ServiceData):
        self._logger.info(
            f"Adding server with container_id={register_request.container_id}"
        )
        async with self._session() as session:
            entry = Server(
                container_id=register_request.container_id,
                type=register_request.type,
                ip_address=register_request.ip_address,
                public_key=register_request.public_key,
            )
            session.add(entry)
            await session.commit()

    async def remove_server(self, container_id: str):
        self._logger.info(f"Removing server with container_id={container_id}")
        async with self._session() as session:
            row = await session.get(Server, container_id)
            if not row:
                raise RuntimeError(f"Server with {container_id=} doesnt exist")
            await session.delete(row)
            await session.commit()

    async def get_server(self, container_id: str) -> Optional[ServiceData]:
        self._logger.info(f"Retrieving server data for container_id={container_id}")
        async with self._session() as session:
            result = await session.get(Server, container_id)

            retval: Optional[ServiceData] = None
            if result:
                retval = ServiceData(
                    container_id=result.container_id,
                    type=result.type,
                    ip_address=result.ip_address,
                    public_key=result.public_key,
                )

            return retval

    async def get_servers_keys(self) -> list[bytes]:
        self._logger.info("Retrieving all servers public keys")
        async with self._session() as session:
            result = await session.execute(select(Server))
            servers = result.scalars().all()
            return [server.public_key for server in servers]

    async def get_servers_addresses(self) -> list[str]:
        self._logger.info("Retrieving all servers ip addresses")
        async with self._session() as session:
            result = await session.execute(select(Server))
            servers = result.scalars().all()
            return [server.ip_address for server in servers]

    async def add_auth_client(self, username: str, verifier: str, salt: str):
        self._logger.info(f"Adding AuthClient with {username=}")
        async with self._session() as session:
            entry = AuthClient(
                username=username,
                verifier=verifier,
                salt=salt,
            )
            session.add(entry)
            await session.commit()

    async def get_auth_client_verifier(self, username: str) -> str:
        self._logger.info(f"Retrieving AuthClient auth_record for {username=}")
        async with self._session() as session:
            result = await session.get(AuthClient, username)
            if not result:
                raise RuntimeError(f"AuthClient with {username=} doesnt exist")
            return result.verifier

    async def get_auth_client_salt(self, username: str) -> str:
        self._logger.info(f"Retrieving AuthClient auth_record for {username=}")
        async with self._session() as session:
            result = await session.get(AuthClient, username)
            if not result:
                raise RuntimeError(f"AuthClient with {username=} doesnt exist")
            return result.salt

    async def remove_auth_client(self, username: str):
        self._logger.info(f"Retrieving AuthClient auth_record for {username=}")
        async with self._session() as session:
            row = await session.get(AuthClient, username)
            if not row:
                raise RuntimeError(f"AuthClient with {username=} doesnt exist")
            await session.delete(row)
            await session.commit()
