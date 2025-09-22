import asyncio
import signal

from vault.common.constants import (
    DB_DNS_ADDRESS,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USERNAME,
    MANAGER_NUM_SHARE_SERVERS,
    MANAGER_SERVER_PORT,
)
from vault.manager.manager import Manager


async def wait_for_signal(signals=(signal.SIGINT, signal.SIGTERM)):
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handler(sig):
        print(f"Received signal: {sig!s}")
        stop_event.set()

    # Register signal handlers
    for sig in signals:
        loop.add_signal_handler(sig, handler, sig)

    print("Sleeping until a signal is received... (Ctrl+C to interrupt)")
    await stop_event.wait()

    # Cleanup handlers
    for sig in signals:
        loop.remove_signal_handler(sig)

    print("Exiting gracefully.")


async def main():
    manager_server = Manager(
        port=MANAGER_SERVER_PORT,
        ip="[::]",
        db_host=DB_DNS_ADDRESS,
        db_port=DB_PORT,
        db_username=DB_USERNAME,
        db_password=DB_PASSWORD,
        db_name=DB_NAME,
        num_of_share_servers=MANAGER_NUM_SHARE_SERVERS,
    )
    await manager_server.start()
    print("spawned and started, waiting for signal for termination...", flush=True)

    await wait_for_signal()

    print("got termination signal, cleanup!...", flush=True)
    await manager_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
