import asyncio
import signal

from vault.common import docker_utils
from vault.manager.manager import Manager


async def wait_for_signal(signals=(signal.SIGINT, signal.SIGTERM)):
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handler(sig):
        print(f"Received signal: {sig!s}", flush=True)
        stop_event.set()

    # Register signal handlers
    for sig in signals:
        loop.add_signal_handler(sig, handler, sig)

    print("Running until a signal is received", flush=True)
    await stop_event.wait()
    print("Got a termination signal, cleaning up and exiting gracefully", flush=True)

    # Cleanup handlers
    for sig in signals:
        loop.remove_signal_handler(sig)


async def main(
    port: int,
    db_host: str,
    db_port: int,
    db_username: str,
    db_password: str,
    db_name: str,
    num_of_share_servers: int,
    setup_master_port: int,
    setup_unit_port: int,
    bootstrap_port: int,
    share_server_port: int,
    docker_image: str,
    docker_network: str,
    bootstrap_command: str,
    share_server_command: str,
    ca_cert_path: str,
    ca_key_path: str,
):
    name = docker_utils.get_container_name(docker_utils.get_self_container_id())
    manager_server = Manager(
        name=name,
        port=port,
        db_host=db_host,
        db_port=db_port,
        db_username=db_username,
        db_password=db_password,
        db_name=db_name,
        num_of_share_servers=num_of_share_servers,
        setup_master_port=setup_master_port,
        setup_unit_port=setup_unit_port,
        bootstrap_port=bootstrap_port,
        share_server_port=share_server_port,
        docker_image=docker_image,
        docker_network=docker_network,
        bootstrap_command=bootstrap_command,
        share_server_command=share_server_command,
        ca_cert_path=ca_cert_path,
        ca_key_path=ca_key_path,
    )
    await manager_server.start()
    await wait_for_signal()
    await manager_server.stop()
