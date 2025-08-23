import grpc

from common.generated import vault_setup_pb2
from common.generated import vault_setup_pb2_grpc
from common.constants import SETUP_MASTER_PORT, SETUP_MASTER_DNS_ADDRESS
from common import docker_utils
from common import types

class SetupUnit:
    def __init__(self, service_type: types.ServiceType, setup_master_address: str = SETUP_MASTER_DNS_ADDRESS):
        self._setup_master_address = setup_master_address
        self._setup_master_port = SETUP_MASTER_PORT
        self._service_type = service_type

    async def register(self):
        self_container_id = docker_utils.get_self_container_id()
        service_data = types.ServiceData(
            type = self._service_type,
            container_id = self_container_id,
            ip_address = docker_utils.get_container_address(self_container_id),

            #TODO: generate real private & public key
            public_key = b"blabla",
        )

        await self._register(service_data)
    
    async def unregister(self):
        await self._unregister(docker_utils.get_self_container_id())

    #TODO
    def get_public_key():
        pass

    #TODO
    def get_private_key():
        pass

    # Private methods
    async def _register(self, service_data: types.ServiceData):
        _address = f'{self._setup_master_address}:{self._setup_master_port}'
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = vault_setup_pb2_grpc.SetupMasterStub(channel)
            resp : vault_setup_pb2.RegisterResponse = await stub.Register(
                types.ServiceData_to_RegisterRequest(service_data)
                )
            if not resp.is_registered:
                raise RuntimeError(f"could not register container_id {service_data.container_id} of type {service_data.type}")

    async def _unregister(self, container_id: str):
        _address = f'{self._setup_master_address}:{self._setup_master_port}'
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = vault_setup_pb2_grpc.SetupMasterStub(channel)
            resp : vault_setup_pb2.UnregisterResponse = await stub.Unregister(
                vault_setup_pb2.UnregisterRequest(container_id=container_id))
            if not resp.is_unregistered:
                raise RuntimeError(f"could not unregister container_id {container_id}")