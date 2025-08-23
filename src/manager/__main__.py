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
    service_data = await setup_master.spawn_bootstrap_server()

    print("waiting for unregistration", flush=True)
    await setup_master._wait_for_container_id_unregistration(service_data.container_id, timeout_s=20)
    print("unregistered", flush=True)
    # Wait for container to finish and get logs

    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())