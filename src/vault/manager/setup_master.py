import asyncio
import weakref
from concurrent import futures
from typing import List, Optional

import grpc
from google.protobuf.empty_pb2 import Empty

from vault.common import docker_utils, types
from vault.common.constants import (
    DOCKER_BOOTSTRAP_SERVER_COMMAND,
    DOCKER_IMAGE_NAME,
    DOCKER_SHARE_SERVER_COMMAND,
    SETUP_MASTER_SERVICE_PORT,
    SETUP_UNIT_SERVICE_PORT,
)
from vault.common.generated import setup_pb2, setup_pb2_grpc
from vault.manager.db_manager import DBManager


class SetupMaster(setup_pb2_grpc.SetupMaster):
    def __init__(
        self,
        db: DBManager,
        server_ip: str = "[::]",
    ):
        setup_pb2_grpc.SetupMaster.__init__(self)
        self._db = db
        self._wait_for_container_id_condition = asyncio.Condition()

        self._is_setup_finished = False
        self._is_setup_finished_lock = asyncio.Lock()

        self._server_ip = server_ip
        self._running_server_task = asyncio.create_task(
            self._start_setup_master_server(self._server_ip)
        )
        weakref.finalize(self, self.cleanup)

        self.bootstrap_idx = 0
        self.share_server_idx = 0

    @classmethod
    async def create(cls, db: DBManager, server_ip: str = "[::]"):
        retval = cls(db=db, server_ip=server_ip)
        await asyncio.sleep(0)  # start grpc server!

        return retval

    def cleanup(self):
        self._running_server_task.cancel()

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
    # async def do_setup(self, share_servers_num: int):
    #     for i in range(share_servers_num):
    #         print(f"spawning shareServer {i}")
    #         self.spawn_share_server()
    #     async with self._is_setup_finished_lock:
    #         self._is_setup_finished = True

    # async def is_setup_finished(self) -> bool:
    #     async with self._is_setup_finished_lock:
    #         return self._is_setup_finished

    async def spawn_bootstrap_server(self, block: bool = True):
        self.bootstrap_idx += 1
        print("spawn_container", flush=True)
        container = docker_utils.spawn_container(
            DOCKER_IMAGE_NAME,
            container_name=f"vault-bootstrap-{self.bootstrap_idx}",
            command=DOCKER_BOOTSTRAP_SERVER_COMMAND,
        )
        service_data = None
        if block:
            print("waiting for bootstrap registration", flush=True)
            service_data: types.ServiceData = (
                await self._wait_for_container_id_registration(container.short_id)
            )
        return service_data

    async def spawn_share_server(self, block: bool = True):
        self.share_server_idx += 1
        container = docker_utils.spawn_container(
            DOCKER_IMAGE_NAME,
            container_name=f"vault-share-{self.bootstrap_idx}",
            command=DOCKER_SHARE_SERVER_COMMAND,
        )

        service_data = None
        if block:
            print("waiting for share server registration", flush=True)
            service_data: types.ServiceData = (
                await self._wait_for_container_id_registration(container.short_id)
            )
        return service_data

    async def terminate_service(
        self, service_data: types.ServiceData, block: bool = True
    ):
        _address = f"{service_data.ip_address}:{SETUP_UNIT_SERVICE_PORT}"
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = setup_pb2_grpc.SetupUnitStub(channel)
            await stub.Terminate(Empty())
        if block:
            await self._wait_for_container_id_unregistration(service_data.container_id)
            await docker_utils.wait_for_container_to_stop(service_data.container_id)
            docker_utils.remove_container(service_data.container_id)

    async def get_all_share_servers(self) -> List[types.ServiceData]:
        # TODO
        pass

    # Private methods
    async def _start_setup_master_server(self, server_ip: str = "[::]"):
        try:
            server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
            setup_pb2_grpc.add_SetupMasterServicer_to_server(self, server)
            server.add_insecure_port(f"{server_ip}:{SETUP_MASTER_SERVICE_PORT}")
            await server.start()
            print(
                f"SetupMaster started start_setup_master_server on port {SETUP_MASTER_SERVICE_PORT}..."
            )
            await server.wait_for_termination()
        except asyncio.CancelledError:
            print("Stoppig setup master service...")
            await server.stop(grace=10)  # grace period of 10 seconds

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
