import grpc
from typing import Optional
from .generated import vault_setup_pb2
from .generated import vault_setup_pb2_grpc


class SetupSlave:
    def __init__(self, setup_master_address: str, setup_master_port: int):
        self.setup_master_address = setup_master_address
        self.setup_master_port = setup_master_port

    async def register(self, type: int, container_id: str, container_ip: str, public_key: Optional[bytes]):
        _address = f'{self.setup_master_address}:{self.setup_master_port}'
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = vault_setup_pb2_grpc.SetupMasterStub(channel)
            resp : vault_setup_pb2.RegisterResponse = await stub.Register(
                vault_setup_pb2.RegisterRequest(type=type, container_id=container_id, container_ip=container_ip, public_key=public_key))
            if not resp.is_registered:
                raise RuntimeError(f"could not register container_id {container_id} of type {type}")
            