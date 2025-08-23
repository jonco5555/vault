SETUP_MASTER_PORT = 5000
SETUP_MASTER_DNS_ADDRESS = "vault-manager"

DOCKER_IMAGE_NAME = "vault"
DOCKER_SHARE_SERVER_COMMAND = "python -m src.share_server"
DOCKER_BOOTSTRAP_SERVER_COMMAND = "python -m src.bootstrap"
DOCKER_NETWORK_NAME = "vault-net"

DB_DNS_ADDRESS = "vault-postgres"
DB_PORT = 5432
DB_USERNAME = "user"
DB_PASSWORD = "pass"
DB_NAME = "proddb"
DB_URL = f"postgresql+asyncpg://{DB_USERNAME}:{DB_PASSWORD}@{DB_DNS_ADDRESS}:{DB_PORT}/{DB_NAME}"
