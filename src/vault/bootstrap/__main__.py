import asyncio

from vault.common.generated import setup_pb2
from vault.common.setup_unit import SetupUnit


async def main():
    setup_unit = SetupUnit(setup_pb2.ServiceType.BOOSTRAP_SERVER)

    print("stating bootstrap...")
    # TODO: run here the bootstrap service!
    other_task = asyncio.create_task(asyncio.sleep(1000))
    print("started bootstrap!")

    print("initing and waiting for shutdown...")
    await setup_unit.init_and_wait_for_shutdown()

    print("terminating bootstrap...")
    # TODO: kill here the bootstrap service!
    other_task.cancel()
    await asyncio.gather(other_task, return_exceptions=True)
    print("terminated bootstrap!")

    print("cleanup...")
    await setup_unit.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
