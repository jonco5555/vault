from sqlalchemy import Column, String, LargeBinary, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import logging

Base = declarative_base()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Vault(Base):
    __tablename__ = "vault"
    user_id = Column(String, primary_key=True)
    secret_id = Column(String, primary_key=True)
    secret = Column(LargeBinary, nullable=False)


class PubKey(Base):
    __tablename__ = "pubkeys"
    user_id = Column(String, primary_key=True)
    public_key = Column(LargeBinary, nullable=False)


class DBManager:
    def __init__(self, db_url: str):
        self._logger = logging.getLogger(__class__.__name__)
        self._engine = create_async_engine(db_url, echo=True)
        Base.metadata.create_all(self._engine)
        self._session = async_sessionmaker(bind=self._engine, expire_on_commit=False)

    async def start(self):
        self._logger.info("Creating Tables")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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
