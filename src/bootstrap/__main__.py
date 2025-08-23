from common.setup_unit import SetupUnit
from common.generated import vault_setup_pb2
import asyncio


async def main():
    setup_slave = SetupUnit(vault_setup_pb2.ServiceType.BOOSTRAP_SERVER)

    print("hello bootstrap!")
    print("registring...")
    await setup_slave.register()
    print("registred, sleeping")
    await asyncio.sleep(10)
    print("wakeup! unregistring...")
    await setup_slave.unregister()
    print("unregistred, bye bye!")

if __name__ == "__main__":
    asyncio.run(main())