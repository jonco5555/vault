import asyncio

from vault.common.constants import (
    MANAGER_SERVER_PORT,
    DB_DNS_ADDRESS,
    DB_PORT,
    DB_USERNAME,
    DB_PASSWORD,
    DB_NAME,
)
from vault.manager.manager import Manager


async def main():
    NUMBER_OF_SHARES = 2
    manager_server = Manager(
        port=MANAGER_SERVER_PORT,
        ip="[::]",
        db_host=DB_DNS_ADDRESS,
        db_port=DB_PORT,
        db_username=DB_USERNAME,
        db_password=DB_PASSWORD,
        db_name=DB_NAME,
        num_of_share_servers=NUMBER_OF_SHARES,
    )
    await manager_server.start()
    print("spawned and started, sleeping...", flush=True)
    # do work with the bootstrap server
    await asyncio.sleep(5)
    print("wakeup!...", flush=True)

    await manager_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
