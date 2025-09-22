import asyncio
from typing import Annotated

import typer

from vault.bootstrap.bootstrap import Bootstrap
from vault.common import types
from vault.common.constants import (
    BOOTSTRAP_SERVER_PORT,
    DB_DNS_ADDRESS,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USERNAME,
    MANAGER_NUM_SHARE_SERVERS,
    MANAGER_SERVER_DNS_ADDRESS,
    MANAGER_SERVER_PORT,
    SHARE_SERVER_PORT,
)
from vault.common.setup_unit import SetupUnit
from vault.manager.manager import Manager
from vault.share_server.share_server import ShareServer
from vault.user.user import User

app = typer.Typer()


@app.command()
async def manager(
    port: Annotated[
        int, typer.Option(envvar="MANAGER_SERVER_PORT")
    ] = MANAGER_SERVER_PORT,
    ip: Annotated[str, typer.Option(envvar="MANAGER_SERVER_IP")] = "[::]",
    db_host: Annotated[str, typer.Option(envvar="DB_DNS_ADDRESS")] = DB_DNS_ADDRESS,
    db_port: Annotated[int, typer.Option(envvar="DB_PORT")] = DB_PORT,
    db_username: Annotated[str, typer.Option(envvar="DB_USERNAME")] = DB_USERNAME,
    db_password: Annotated[str, typer.Option(envvar="DB_PASSWORD")] = DB_PASSWORD,
    db_name: Annotated[str, typer.Option(envvar="DB_NAME")] = DB_NAME,
    num_of_share_servers: Annotated[
        int, typer.Option(envvar="MANAGER_NUM_SHARE_SERVERS")
    ] = MANAGER_NUM_SHARE_SERVERS,
):
    """Run the Manager service."""
    manager_server = Manager(
        port=port,
        ip=ip,
        db_host=db_host,
        db_port=db_port,
        db_username=db_username,
        db_password=db_password,
        db_name=db_name,
        num_of_share_servers=num_of_share_servers,
    )
    await manager_server.start()
    manager_server._logger.info("Running until a signal is received")
    import signal

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handler(sig):
        print(f"Received signal: {sig!s}")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handler, sig)
    await stop_event.wait()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.remove_signal_handler(sig)
    manager_server._logger.info(
        "Got a termination signal, cleaning up and exiting gracefully"
    )
    await manager_server.stop()


@app.command()
async def bootstrap(
    port: Annotated[
        int, typer.Option(envvar="BOOTSTRAP_SERVER_PORT")
    ] = BOOTSTRAP_SERVER_PORT,
):
    """Run the Bootstrap service."""
    setup_unit = SetupUnit(types.ServiceType.BOOSTRAP_SERVER)
    bootstrap_server = Bootstrap(port=port)
    await bootstrap_server.start()
    await setup_unit.init_and_wait_for_shutdown()
    await bootstrap_server.close()
    await setup_unit.cleanup()


@app.command()
async def shareserver(
    port: Annotated[int, typer.Option(envvar="SHARE_SERVER_PORT")] = SHARE_SERVER_PORT,
):
    """Run the ShareServer service."""
    setup_unit = SetupUnit(types.ServiceType.SHARE_SERVER)
    share_server = ShareServer(port=port)
    await share_server.start()
    await setup_unit.init_and_wait_for_shutdown(share_server._pubkey_b64)
    await share_server.close()
    await setup_unit.cleanup()


@app.command()
async def user(
    user_id: Annotated[str, typer.Option(envvar="USER_ID")] = "alice",
    server_ip: Annotated[
        str, typer.Option(envvar="MANAGER_SERVER_DNS_ADDRESS")
    ] = MANAGER_SERVER_DNS_ADDRESS,
    server_port: Annotated[
        int, typer.Option(envvar="MANAGER_SERVER_PORT")
    ] = MANAGER_SERVER_PORT,
    threshold: Annotated[
        int, typer.Option(envvar="USER_THRESHOLD")
    ] = MANAGER_NUM_SHARE_SERVERS + 1,
    num_of_total_shares: Annotated[
        int, typer.Option(envvar="USER_NUM_TOTAL_SHARES")
    ] = MANAGER_NUM_SHARE_SERVERS + 1,
):
    """Simulate User client operations."""
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
