import asyncio

from vault.common.generated import setup_pb2
from vault.common.setup_unit import SetupUnit

from vault.bootstrap.bootstrap import Bootstrap
from vault.common.constants import BOOTSTRAP_SERVER_PORT


async def main():
    setup_unit = SetupUnit(setup_pb2.ServiceType.BOOSTRAP_SERVER)

    print("stating bootstrap...")
    # TODO: run here the bootstrap service!
    bootstrap_server = Bootstrap(port=BOOTSTRAP_SERVER_PORT)
    await bootstrap_server.start()

    print("initing and waiting for shutdown...")
    await setup_unit.init_and_wait_for_shutdown()

    print("terminating bootstrap...")
    # TODO: kill here the bootstrap service!
    await bootstrap_server.close()
    print("terminated bootstrap!")

    print("cleanup...")
    await setup_unit.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
