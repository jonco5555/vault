from manager.setup_master import SetupMaster
from vault.db_manager import DBManager
from common.constants import DB_URL
import asyncio


async def main():
    db_url = DB_URL
    db_manager = await DBManager.create(db_url)

    print("before!", flush=True)
    setup_master = await SetupMaster.create(db_manager)
    print("after!", flush=True)

    print("spawning bootstrap server", flush=True)
    service_data = await setup_master.spawn_bootstrap_service()

    print("spawned, sleeping...", flush=True)
    # do work with the bootstrap server
    await asyncio.sleep(10)
    print("wakeup!...", flush=True)

    print("waiting for unregistration", flush=True)
    await setup_master.terminate_service(service_data)
    print("unregistered", flush=True)
    # Wait for container to finish and get logs

    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())