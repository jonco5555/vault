import asyncio

from vault.bootstrap.bootstrap import Bootstrap
from vault.common import types
from vault.common.constants import BOOTSTRAP_SERVER_PORT
from vault.common.setup_unit import SetupUnit


async def main():
    setup_unit = SetupUnit(types.ServiceType.BOOSTRAP_SERVER)
    bootstrap_server = Bootstrap(port=BOOTSTRAP_SERVER_PORT)
    await bootstrap_server.start()
    await setup_unit.init_and_wait_for_shutdown()
    await bootstrap_server.close()
    await setup_unit.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
