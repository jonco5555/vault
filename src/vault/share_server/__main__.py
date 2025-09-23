from vault.common import docker_utils, types
from vault.common.setup_unit import SetupUnit
from vault.share_server.share_server import ShareServer


async def main(
    port: int,
    setup_unit_port: int,
    setup_master_address: str,
    setup_master_port: int,
    ca_cert_path: str,
    ca_key_path: str,
):
    name = docker_utils.get_container_name(docker_utils.get_self_container_id())
    share_server = ShareServer(
        name=name, port=port, ca_cert_path=ca_cert_path, ca_key_path=ca_key_path
    )
    setup_unit = SetupUnit(
        port=setup_unit_port,
        service_type=types.ServiceType.SHARE_SERVER,
        setup_master_address=setup_master_address,
        setup_master_port=setup_master_port,
        server_creds=share_server._server_creds,
        client_creds=share_server._client_creds,
    )
    await share_server.start()
    await setup_unit.init_and_wait_for_shutdown(share_server._pubkey_b64)
    await share_server.close()
    await setup_unit.cleanup()
