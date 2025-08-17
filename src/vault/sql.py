from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class VaultDB:
    def __init__(self, DB_base_url, vault_table_name, pubkeys_table_name):
        self.Base = declarative_base()
        self.engine = create_engine(DB_base_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.vault_table_name = vault_table_name
        self.pubkeys_table_name = pubkeys_table_name
        self.Vault = self._get_vault_table()
        self.PubKey = self._get_pubkeys_table()

    def _get_vault_table(self):
        Base = self.Base
        table_name = self.vault_table_name

        class Vault(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True, autoincrement=True)
            user_id = Column(String, nullable=False)
            password_id = Column(String, nullable=False)
            password = Column(String, nullable=False)

        return Vault

    def _get_pubkeys_table(self):
        Base = self.Base
        table_name = self.pubkeys_table_name

        class PubKey(Base):
            __tablename__ = table_name
            id = Column(Integer, primary_key=True, autoincrement=True)
            ip = Column(String, nullable=False)
            port = Column(Integer, nullable=False)
            pubkey = Column(String, nullable=False)
            metadata = Column(String, nullable=True)

        return PubKey

    def init_tables(self):
        self.Base.metadata.create_all(bind=self.engine)
