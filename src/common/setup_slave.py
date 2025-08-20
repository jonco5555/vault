import grpc
from typing import Optional

from common.generated import vault_setup_pb2
from common.generated import vault_setup_pb2_grpc


class SetupSlave:
    def __init__(self, setup_master_address: str, setup_master_port: int):
        self.setup_master_address = setup_master_address
        self.setup_master_port = setup_master_port

    async def register(self, service_data: vault_setup_pb2.ServiceData):
        _address = f'{self.setup_master_address}:{self.setup_master_port}'
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = vault_setup_pb2_grpc.SetupMasterStub(channel)
            resp : vault_setup_pb2.RegisterResponse = await stub.Register(
                vault_setup_pb2.RegisterRequest(service_data=service_data))
            if not resp.is_registered:
                raise RuntimeError(f"could not register container_id {container_id} of type {type}")
    
    async def unregister(self, container_id: str):
        _address = f'{self.setup_master_address}:{self.setup_master_port}'
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = vault_setup_pb2_grpc.SetupMasterStub(channel)
            resp : vault_setup_pb2.UnregisterResponse = await stub.Unregister(
                vault_setup_pb2.UnregisterRequest(type=type, container_id=container_id, container_ip=container_ip, public_key=public_key))
            if not resp.is_registered:
                raise RuntimeError(f"could not unregister container_id {container_id}")