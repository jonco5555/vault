from sqlalchemy import NullPool, select

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import logging

from typing import Optional
from common.generated import vault_setup_pb2

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


class PubKey(Base):
    __tablename__ = "pubkeys"
    user_id: Mapped[str] = mapped_column(primary_key=True)
    public_key: Mapped[bytes] = mapped_column()

class Server(Base):
    __tablename__ = "servers"
    container_id: Mapped[str] = mapped_column(primary_key=True)
    type: Mapped[int] = mapped_column()
    ip_address: Mapped[str] = mapped_column()
    public_key: Mapped[bytes] = mapped_column(nullable=True)

class DBManager:
    def __init__(self, db_url: str):
        self._logger = logging.getLogger(__class__.__name__)
        self._engine = create_async_engine(
            db_url, echo=True, poolclass=NullPool
        )  # TODO: Using NullPool made the tests pass, need to investigate
        self._session = async_sessionmaker(bind=self._engine, expire_on_commit=False)

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
                select(Vault).filter_by(user_id=user_id, secret_id=secret_id)
            )
            return result.scalars().first()

    async def add_pubkey(self, user_id: str, public_key: bytes):
        self._logger.info(f"Adding public key for user_id={user_id}")
        async with self._session() as session:
            entry = PubKey(user_id=user_id, public_key=public_key)
            session.add(entry)
            await session.commit()

    async def get_pubkey(self, user_id: str):
        self._logger.info(f"Retrieving public key for user_id={user_id}")
        async with self._session() as session:
            result = await session.execute(select(PubKey).filter_by(user_id=user_id))
            return result.scalars().first()
        
    async def add_server(self, register_request: vault_setup_pb2.ServiceData):
        self._logger.info(f"Adding server with container_id={register_request.container_id}")
        async with self._session() as session:
            pubkey: Optional[bytes] = None
            if register_request.HasField("public_key"):
                pubkey = register_request.public_key
            entry = Server(container_id=register_request.container_id,
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

    async def get_server(self, container_id: str) -> Optional[vault_setup_pb2.ServiceData]:
        self._logger.info(f"Retrieving server data for container_id={container_id}")
        async with self._session() as session:
            result = await session.get(Server, container_id)
            
            retval: Optional[vault_setup_pb2.ServiceData] = None
            if result:
                retval = vault_setup_pb2.ServiceData()
                retval.container_id = result.container_id
                retval.type = result.type
                retval.ip_address = result.ip_address
                if result.public_key:
                    retval.public_key = result.public_key

            return retval

