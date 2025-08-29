import asyncio
from concurrent import futures

import grpc
from google.protobuf.empty_pb2 import Empty

from vault.common import docker_utils, types
from vault.common.constants import SETUP_MASTER_DNS_ADDRESS, SETUP_PORT
from vault.common.generated import setup_pb2, setup_pb2_grpc


class SetupUnit(setup_pb2_grpc.SetupUnit):
    def __init__(
        self,
        service_type: types.ServiceType,
        server_ip: str = "[::]",
        setup_master_address: str = SETUP_MASTER_DNS_ADDRESS,
    ):
        self._setup_master_address = setup_master_address
        self._setup_master_port = SETUP_PORT
        self._service_type = service_type

        self._termination_condvar = asyncio.Condition()

        self._server_ip = server_ip
        self._running_server = None
        self._running_server_task = asyncio.create_task(
            self._start_setup_unit_server(self._server_ip)
        )

    # setup_pb2_grpc.SetupUnit inherited methods
    async def Terminate(self, request: Empty, context):
        print("in Terminate!", flush=True)
        async with self._termination_condvar:
            self._termination_condvar.notify_all()
        return Empty()

    # API methods
    async def init_and_wait_for_shutdown(self):
        await self.register()
        async with self._termination_condvar:
            await self._termination_condvar.wait()

    async def cleanup(self):
        await self.unregister()
        await self._running_server.stop(grace=10)  # 10 seconds to gracefuly shutdown

    async def register(self):
        self_container_id = docker_utils.get_self_container_id()
        service_data = types.ServiceData(
            type=self._service_type,
            container_id=self_container_id,
            ip_address=docker_utils.get_container_address(self_container_id),
            # TODO: generate real private & public key
            public_key=b"blabla",
        )

        await self._register(service_data)

    async def unregister(self):
        await self._unregister(docker_utils.get_self_container_id())

    # TODO
    def get_public_key():
        pass

    # TODO
    def get_private_key():
        pass

    # Private methods
    async def _start_setup_unit_server(self, server_ip: str = "[::]"):
        try:
            self._running_server = grpc.aio.server(
                futures.ThreadPoolExecutor(max_workers=2)
            )
            setup_pb2_grpc.add_SetupUnitServicer_to_server(self, self._running_server)
            self._running_server.add_insecure_port(f"{server_ip}:{SETUP_PORT}")
            await self._running_server.start()
            print(
                f"SetupUnit started start_setup_master_server on port {SETUP_PORT}..."
            )
            await self._running_server.wait_for_termination()
        except asyncio.CancelledError:
            print("Stoppig setup unit service...")
            await self._running_server.stop(grace=10)  # grace period of 10 seconds

    async def _register(self, service_data: types.ServiceData):
        _address = f"{self._setup_master_address}:{self._setup_master_port}"
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = setup_pb2_grpc.SetupMasterStub(channel)
            resp: setup_pb2.RegisterResponse = await stub.Register(
                types.ServiceData_to_SetupRegisterRequest(service_data)
            )
            if not resp.is_registered:
                raise RuntimeError(
                    f"could not register container_id {service_data.container_id} of type {service_data.type}"
                )

    async def _unregister(self, container_id: str):
        _address = f"{self._setup_master_address}:{self._setup_master_port}"
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = setup_pb2_grpc.SetupMasterStub(channel)
            resp: setup_pb2.UnregisterResponse = await stub.Unregister(
                setup_pb2.UnregisterRequest(container_id=container_id)
            )
            if not resp.is_unregistered:
                raise RuntimeError(f"could not unregister container_id {container_id}")
