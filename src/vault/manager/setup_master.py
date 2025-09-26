import asyncio
from concurrent import futures
from typing import Optional

import grpc
from google.protobuf.empty_pb2 import Empty

from vault.common import docker_utils, types
from vault.common.generated import setup_pb2, setup_pb2_grpc
from vault.manager.db_manager import DBManager


class SetupMaster(setup_pb2_grpc.SetupMaster):
    def __init__(
        self,
        port: int,
        setup_unit_port: int,
        db: DBManager,
        server_creds: grpc.ServerCredentials,
        client_creds: grpc.ChannelCredentials,
    ):
        setup_pb2_grpc.SetupMaster.__init__(self)
        self._db = db
        self._wait_for_container_id_condition = asyncio.Condition()

        self._is_setup_finished = False
        self._is_setup_finished_lock = asyncio.Lock()

        self._port = port
        self._setup_unit_port = setup_unit_port
        self._client_creds = client_creds

        # grpc server
        self._server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        setup_pb2_grpc.add_SetupMasterServicer_to_server(self, self._server)
        self._server.add_secure_port(f"[::]:{self._port}", server_creds)

        self._ready = False

    async def start(self):
        await self._server.start()
        self._ready = True
        print("SetupMaster started!")

    async def stop(self):
        self._ready = False
        await self._server.stop(grace=5.0)
        print("SetupMaster stopped")

    # setup_pb2_grpc.SetupMaster inherited methods
    async def SetupRegister(self, request: setup_pb2.SetupRegisterRequest, context):
        print("in Register!", flush=True)
        await self._db.add_server(types.SetupRegisterRequest_to_ServiceData(request))
        async with self._wait_for_container_id_condition:
            self._wait_for_container_id_condition.notify_all()
        return setup_pb2.SetupRegisterResponse(is_registered=True)

    async def SetupUnregister(self, request: setup_pb2.SetupUnregisterRequest, context):
        print("in SetupUnregister!", flush=True)
        is_unregistered = False
        try:
            await self._db.remove_server(request.container_id)
            async with self._wait_for_container_id_condition:
                self._wait_for_container_id_condition.notify_all()
            is_unregistered = True
        except Exception:
            pass
        return setup_pb2.SetupUnregisterResponse(is_unregistered=is_unregistered)

    # API methods
    async def spawn_server(
        self,
        image: str,
        container_name: str = None,
        command: str = None,
        network: str = None,
        environment: dict = {},
        block: bool = True,
    ):
        container = docker_utils.spawn_container(
            image,
            container_name=container_name,
            command=command,
            network=network,
            environment=environment,
        )

        service_data = None
        if block:
            print(f"waiting for {container_name} registration", flush=True)
            service_data: types.ServiceData = (
                await self._wait_for_container_id_registration(container.short_id)
            )
        return service_data

    async def terminate_service(
        self, service_data: types.ServiceData, block: bool = True
    ):
        _address = f"{service_data.container_name}:{self._setup_unit_port}"
        async with grpc.aio.secure_channel(_address, self._client_creds) as channel:
            stub = setup_pb2_grpc.SetupUnitStub(channel)
            await stub.Terminate(Empty())
        if block:
            await self._wait_for_container_id_unregistration(service_data.container_id)
            await docker_utils.wait_for_container_to_stop(service_data.container_id)
            docker_utils.remove_container(service_data.container_id)

    # Private methods
    async def _get_container_data(
        self, container_id: str
    ) -> Optional[types.ServiceData]:
        return await self._db.get_server(container_id)

    async def _wait_for_container_id_registration(
        self, container_id: str, timeout_s: int = 10
    ) -> types.ServiceData:
        start_time = asyncio.get_event_loop().time()
        while True:
            retval = await self._get_container_data(container_id)
            if retval:
                return retval

            # calculate remaining timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining_s = timeout_s - elapsed
            if remaining_s <= 0:
                raise TimeoutError(
                    f"container_id '{container_id}' did not appear in DB within {timeout_s}s"
                )

            async with self._wait_for_container_id_condition:
                try:
                    await asyncio.wait_for(
                        self._wait_for_container_id_condition.wait(),
                        timeout=remaining_s,
                    )
                    print("Woke up by notification, rechecking DB...")
                except asyncio.TimeoutError:
                    print(f"No notification in {remaining_s}s, rechecking DB...")

    async def _wait_for_container_id_unregistration(
        self, container_id: str, timeout_s: int = 10
    ):
        start_time = asyncio.get_event_loop().time()
        while True:
            retval = await self._get_container_data(container_id)
            if retval is None:
                return

            # calculate remaining timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining_s = timeout_s - elapsed
            if remaining_s <= 0:
                raise TimeoutError(
                    f"container_id '{container_id}' appears in DB within {timeout_s}s"
                )

            async with self._wait_for_container_id_condition:
                try:
                    await asyncio.wait_for(
                        self._wait_for_container_id_condition.wait(),
                        timeout=remaining_s,
                    )
                    print("Woke up by notification, rechecking DB...")
                except asyncio.TimeoutError:
                    print(f"No notification in {remaining_s}s, rechecking DB...")
