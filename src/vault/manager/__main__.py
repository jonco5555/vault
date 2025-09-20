import asyncio

from vault.common.constants import (
    MANAGER_SERVER_PORT,
    DB_DNS_ADDRESS,
    DB_PORT,
    DB_USERNAME,
    DB_PASSWORD,
    DB_NAME,
    MANAGER_NUM_SHARE_SERVERS,
)
from vault.manager.manager import Manager


async def main():
    manager_server = Manager(
        port=MANAGER_SERVER_PORT,
        ip="[::]",
        db_host=DB_DNS_ADDRESS,
        db_port=DB_PORT,
        db_username=DB_USERNAME,
        db_password=DB_PASSWORD,
        db_name=DB_NAME,
        num_of_share_servers=MANAGER_NUM_SHARE_SERVERS,
    )
    await manager_server.start()
    print("spawned and started, sleeping...", flush=True)

    await asyncio.sleep(600)
    print("wakeup!...", flush=True)

    await manager_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
