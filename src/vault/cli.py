import asyncio
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def manager(
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
    docker_image: Annotated[str, typer.Option(envvar="DOCKER_IMAGE")],
    ca_cert_path: Annotated[str, typer.Option(envvar="CA_CERT_PATH")],
    ca_key_path: Annotated[str, typer.Option(envvar="CA_KEY_PATH")],
):
    from vault.manager.__main__ import main

    asyncio.run(
        main(
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
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
        )
    )


@app.command()
def bootstrap(
    port: Annotated[int, typer.Option(envvar="PORT")],
    setup_unit_port: Annotated[int, typer.Option(envvar="SETUP_UNIT_PORT")],
    setup_master_address: Annotated[str, typer.Option(envvar="SETUP_MASTER_ADDRESS")],
    setup_master_port: Annotated[int, typer.Option(envvar="SETUP_MASTER_PORT")],
    ca_cert_path: Annotated[str, typer.Option(envvar="CA_CERT_PATH")],
    ca_key_path: Annotated[str, typer.Option(envvar="CA_KEY_PATH")],
):
    from vault.bootstrap.__main__ import main

    asyncio.run(
        main(
            port=port,
            setup_unit_port=setup_unit_port,
            setup_master_address=setup_master_address,
            setup_master_port=setup_master_port,
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
        )
    )


@app.command()
def share_server(
    port: Annotated[int, typer.Option(envvar="PORT")],
    setup_unit_port: Annotated[int, typer.Option(envvar="SETUP_UNIT_PORT")],
    setup_master_address: Annotated[str, typer.Option(envvar="SETUP_MASTER_ADDRESS")],
    setup_master_port: Annotated[int, typer.Option(envvar="SETUP_MASTER_PORT")],
    ca_cert_path: Annotated[str, typer.Option(envvar="CA_CERT_PATH")],
    ca_key_path: Annotated[str, typer.Option(envvar="CA_KEY_PATH")],
):
    from vault.share_server.__main__ import main

    asyncio.run(
        main(
            port=port,
            setup_unit_port=setup_unit_port,
            setup_master_address=setup_master_address,
            setup_master_port=setup_master_port,
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
        )
    )


@app.command()
def user(
    user_id: Annotated[str, typer.Option(envvar="USER_ID")],
    server_ip: Annotated[str, typer.Option(envvar="SERVER_IP")],
    server_port: Annotated[int, typer.Option(envvar="SERVER_PORT")],
    threshold: Annotated[int, typer.Option(envvar="THRESHOLD")],
    num_of_total_shares: Annotated[int, typer.Option(envvar="TOTAL_SHARES")],
    ca_cert_path: Annotated[str, typer.Option(envvar="CA_CERT_PATH")],
):
    from vault.user.__main__ import main

    asyncio.run(
        main(
            user_id=user_id,
            server_ip=server_ip,
            server_port=server_port,
            threshold=threshold,
            num_of_total_shares=num_of_total_shares,
            ca_cert_path=ca_cert_path,
        )
    )


if __name__ == "__main__":
    app(prog_name="vault-cli")
