from vault.bootstrap.bootstrap import Bootstrap
from vault.common import docker_utils, types
from vault.common.setup_unit import SetupUnit


async def main(
    port: int,
    setup_unit_port: int,
    setup_master_address: str,
    setup_master_port: int,
    ca_cert_path: str,
    ca_key_path: str,
):
    setup_unit = SetupUnit(
        port=setup_unit_port,
        service_type=types.ServiceType.BOOSTRAP_SERVER,
        setup_master_address=setup_master_address,
        setup_master_port=setup_master_port,
    )
    name = docker_utils.get_container_name(docker_utils.get_self_container_id())
    bootstrap_server = Bootstrap(
        name=name, port=port, ca_cert_path=ca_cert_path, ca_key_path=ca_key_path
    )
    await bootstrap_server.start()
    await setup_unit.init_and_wait_for_shutdown()
    await bootstrap_server.close()
    await setup_unit.cleanup()
