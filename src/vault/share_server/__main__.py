import asyncio

from vault.common.setup_unit import SetupUnit

from vault.share_server.share_server import ShareServer
from vault.common.constants import SHARE_SERVER_PORT
from vault.common import types


async def main():
    setup_unit = SetupUnit(types.ServiceType.SHARE_SERVER)

    print("stating share server...")
    # TODO: run here the share_server service!
    share_server = ShareServer(port=SHARE_SERVER_PORT)
    await share_server.start()

    print("initing and waiting for shutdown...")
    await setup_unit.init_and_wait_for_shutdown()

    print("terminating share server...")
    # TODO: kill here the share_server service!
    await share_server.close()
    print("terminated share_server!")

    print("cleanup...")
    await setup_unit.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
