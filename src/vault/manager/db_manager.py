from sqlalchemy import NullPool, select

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import logging


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

    async def user_exists(self, user_id: str) -> bool:
        self._logger.info(f"Checking if user exists: {user_id}")
        async with self._session() as session:
            result = await session.execute(select(PubKey).filter_by(user_id=user_id))
            return result.scalars().first() is not None
