import asyncio
import signal
from typing import Annotated

import typer

from vault.bootstrap.bootstrap import Bootstrap
from vault.common import docker_utils, types
from vault.common.setup_unit import SetupUnit
from vault.manager.manager import Manager
from vault.share_server.share_server import ShareServer
from vault.user.user import User

app = typer.Typer()


async def wait_for_signal(signals=(signal.SIGINT, signal.SIGTERM)):
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handler(sig):
        print(f"Received signal: {sig!s}")
        stop_event.set()

    # Register signal handlers
    for sig in signals:
        loop.add_signal_handler(sig, handler, sig)

    typer.echo("Running until a signal is received")
    await stop_event.wait()
    typer.echo("Got a termination signal, cleaning up and exiting gracefully")

    # Cleanup handlers
    for sig in signals:
        loop.remove_signal_handler(sig)


@app.command()
async def manager(
    port: Annotated[int, typer.Option(envvar="PORT")],
    db_host: Annotated[str, typer.Option(envvar="DB_HOST")],
    db_port: Annotated[int, typer.Option(envvar="DB_PORT")],
    db_username: Annotated[str, typer.Option(envvar="DB_USERNAME")],
    db_password: Annotated[str, typer.Option(envvar="DB_PASSWORD")],
    db_name: Annotated[str, typer.Option(envvar="DB_NAME")],
    num_of_share_servers: Annotated[int, typer.Option(envvar="NUM_SHARE_SERVERS")],
    setup_master_port: Annotated[int, typer.Option(envvar="SETUP_MASTER_PORT")],
    setup_unit_port: Annotated[int, typer.Option(envvar="SETUP_UNIT_PORT")],
    bootstrap_port: Annotated[int, typer.Option(envvar="BOOTSTRAP_PORT")],
    share_server_port: Annotated[int, typer.Option(envvar="SHARE_SERVER_PORT")],
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
    )
    await manager_server.start()
    await wait_for_signal()
    await manager_server.stop()


@app.command()
async def bootstrap(
    port: Annotated[int, typer.Option(envvar="PORT")],
    setup_unit_port: Annotated[int, typer.Option(envvar="SETUP_UNIT_PORT")],
    setup_master_address: Annotated[str, typer.Option(envvar="SETUP_MASTER_ADDRESS")],
    setup_master_port: Annotated[int, typer.Option(envvar="SETUP_MASTER_PORT")],
):
    setup_unit = SetupUnit(
        port=setup_unit_port,
        service_type=types.ServiceType.BOOSTRAP_SERVER,
        setup_master_address=setup_master_address,
        setup_master_port=setup_master_port,
    )
    name = docker_utils.get_container_name(docker_utils.get_self_container_id())
    bootstrap_server = Bootstrap(name=name, port=port)
    await bootstrap_server.start()
    await setup_unit.init_and_wait_for_shutdown()
    await bootstrap_server.close()
    await setup_unit.cleanup()


@app.command()
async def share_server(
    port: Annotated[int, typer.Option(envvar="PORT")],
    setup_unit_port: Annotated[int, typer.Option(envvar="SETUP_UNIT_PORT")],
    setup_master_address: Annotated[str, typer.Option(envvar="SETUP_MASTER_ADDRESS")],
    setup_master_port: Annotated[int, typer.Option(envvar="SETUP_MASTER_PORT")],
):
    setup_unit = SetupUnit(
        port=setup_unit_port,
        service_type=types.ServiceType.SHARE_SERVER,
        setup_master_address=setup_master_address,
        setup_master_port=setup_master_port,
    )
    name = docker_utils.get_container_name(docker_utils.get_self_container_id())
    share_server = ShareServer(name=name, port=port)
    await share_server.start()
    await setup_unit.init_and_wait_for_shutdown(share_server._pubkey_b64)
    await share_server.close()
    await setup_unit.cleanup()


@app.command()
async def user(
    user_id: Annotated[str, typer.Option(envvar="USER_ID")],
    server_ip: Annotated[str, typer.Option(envvar="SERVER_IP")],
    server_port: Annotated[int, typer.Option(envvar="SERVER_PORT")],
    threshold: Annotated[int, typer.Option(envvar="THRESHOLD")],
    num_of_total_shares: Annotated[int, typer.Option(envvar="TOTAL_SHARES")],
):
    user_obj = User(
        user_id=user_id,
        server_ip=server_ip,
        server_port=server_port,
        threshold=threshold,
        num_of_total_shares=num_of_total_shares,
    )
    print("=== Simulating Client Operations ===", flush=True)
    print("-> Registration phase", flush=True)
    await user_obj.register()
    print("-> Storage phase", flush=True)
    secret = "my super secret"
    secret_id = "my super secret id"
    await user_obj.store_secret(secret, secret_id)
    print("-> Retrieval phase", flush=True)
    retrieved_secret = await user_obj.retrieve_secret(secret_id)
    if retrieved_secret != secret:
        raise RuntimeError(f"Expected {secret=}, got {retrieved_secret=}")
    print("-> Storage phase2", flush=True)
    secret2 = "my super secret2"
    secret_id2 = "my super secret id2"
    await user_obj.store_secret(secret2, secret_id2)
    print("-> Retrieval phase2", flush=True)
    retrieved_secret2 = await user_obj.retrieve_secret(secret_id2)
    if retrieved_secret2 != secret2:
        raise RuntimeError(f"Expected {secret2=}, got {retrieved_secret2=}")
    print("VICTORYYYYYY", flush=True)


if __name__ == "__main__":
    app(prog_name="vault-cli")
