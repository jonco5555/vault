import asyncio

from vault.common import types
from vault.common.constants import SHARE_SERVER_PORT
from vault.common.setup_unit import SetupUnit
from vault.share_server.share_server import ShareServer


async def main():
    setup_unit = SetupUnit(types.ServiceType.SHARE_SERVER)
    share_server = ShareServer(port=SHARE_SERVER_PORT)
    await share_server.start()
    await setup_unit.init_and_wait_for_shutdown(share_server._pubkey_b64)
    await share_server.close()
    await setup_unit.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
