import asyncio

from vault.common.constants import DB_URL
from vault.manager.db_manager import DBManager
from vault.manager.setup_master import SetupMaster


async def main():
    db_url = DB_URL
    db_manager = await DBManager.create(db_url)

    print("before!", flush=True)
    setup_master = await SetupMaster.create(db_manager)
    print("after!", flush=True)

    print("spawning bootstrap server", flush=True)
    bootstrap_service_data = await setup_master.spawn_bootstrap_server()

    print("spawning share server", flush=True)
    share_server_data = await setup_master.spawn_share_server()

    print("spawned, sleeping...", flush=True)
    # do work with the bootstrap server
    await asyncio.sleep(10)
    print("wakeup!...", flush=True)

    print("waiting for unregistration", flush=True)
    await setup_master.terminate_service(bootstrap_service_data)
    await setup_master.terminate_service(share_server_data)
    print("unregistered", flush=True)
    # Wait for container to finish and get logs

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
