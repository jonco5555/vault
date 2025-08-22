import asyncio
from typing import Optional, List
import grpc
from concurrent import futures
import weakref

from common import docker_utils
from common.generated import vault_setup_pb2
from common.generated import vault_setup_pb2_grpc
from common.constants import (
    SETUP_MASTER_PORT,
    IMAGE_NAME,
    SHARE_SERVER_COMMAND,
    BOOTSTRAP_SERVER_COMMAND
    )

#TODO: move db manager to be in manager directory
from vault.db_manager import DBManager

class SetupMaster(vault_setup_pb2_grpc.SetupMaster):
    def __init__(self, db: DBManager, server_ip: str = "[::]"):
        vault_setup_pb2_grpc.SetupMaster.__init__(self)
        self._db = db
        self._wait_for_container_id_condition = asyncio.Condition()

        self._is_setup_finished = False
        self._is_setup_finished_lock = asyncio.Lock()

        self._server_ip = server_ip
        self._running_server_task = asyncio.create_task(self._start_setup_master_server(server_ip))
        weakref.finalize(self, self.cleanup)

    def cleanup(self):
        self._running_server_task.cancel()

    # vault_setup_pb2_grpc.SetupMaster inherited methods
    async def Register(self, request: vault_setup_pb2.RegisterRequest, context):
        await self._db.add_server(request.service_data)
        async with self._wait_for_container_id_condition:
            self._wait_for_container_id_condition.notify_all()
        return vault_setup_pb2.RegisterResponse(is_registered=True)
    
    async def Unregister(self, request: vault_setup_pb2.UnregisterRequest, context):
        is_unregistered = False
        try:
            await self._db.remove_server(request.container_id)
            async with self._wait_for_container_id_condition:
                self._wait_for_container_id_condition.notify_all()
            is_unregistered = True
        except Exception as e:
            pass
        return vault_setup_pb2.UnregisterResponse(is_unregistered=is_unregistered)
    
    # API method
    async def do_setup(self, share_servers_num: int):
        for i in range(share_servers_num):
            print(f"spawaning shareServer {i}")
            #TODO
        async with self._is_setup_finished_lock:
            self._is_setup_finished = True

    async def is_setup_finished(self) -> bool:
        async with self._is_setup_finished_lock:
            return self._is_setup_finished

    async def spawn_bootstrap_server(self) -> vault_setup_pb2.ServiceData:
        container = await docker_utils.spawn_container(IMAGE_NAME, command=BOOTSTRAP_SERVER_COMMAND)
        return await self._wait_for_container_id_registration(container.id)

    async def kill_server(self, container_id: str):
        #TODO
        pass
    
    async def get_all_share_servers(self) -> List[vault_setup_pb2.ServiceData]:
        #TODO        
        pass

    # Private methods
    async def _start_setup_master_server(self, server_ip: str = "[::]"):
        try:
            server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
            vault_setup_pb2_grpc.add_SetupMasterServicer_to_server(self, server)
            server.add_insecure_port(f'{server_ip}:{SETUP_MASTER_PORT}')
            await server.start()
            print(f"SetupMaster started start_setup_master_server on port {SETUP_MASTER_PORT}...")
            await server.wait_for_termination()
        except asyncio.CancelledError:
            print("Stoppig setup master service...")
            await server.stop(grace=10) # grace period of 10 seconds

    async def _spawn_share_server():
        docker_utils.spawn_container(IMAGE_NAME, command=SHARE_SERVER_COMMAND)

    async def _get_container_data(self, container_id: str) -> Optional[vault_setup_pb2.ServiceData]:
        return await self._db.get_server(container_id)

    async def _wait_for_container_id_registration(self, container_id: str, timeout_s: int = 10) -> vault_setup_pb2.ServiceData:
        check_interval_s = min(timeout_s, 3)
        start_time = asyncio.get_event_loop().time()
        while True:
            retval = await self._get_container_data(container_id)
            if retval:
                return retval

            # calculate remaining timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining_s = timeout_s - elapsed
            if remaining_s <= 0:
                raise TimeoutError(f"container_id '{container_id}' did not appear in DB within {timeout_s}s")

            # wait for either condition notification or timeout slice
            wait_time_s = min(check_interval_s, remaining_s)
            async with self._wait_for_container_id_condition:
                try:
                    await asyncio.wait_for(self._wait_for_container_id_condition.wait(), timeout=wait_time_s)
                    print("Woke up by notification, rechecking DB...")
                except asyncio.TimeoutError:
                    print(f"No notification in {remaining_s}s, rechecking DB...")

    async def _wait_for_container_id_unregistration(self, container_id: str, timeout_s: int = 10):
        check_interval_s = min(timeout_s, 3)
        start_time = asyncio.get_event_loop().time()
        while True:
            retval = await self._get_container_data(container_id)
            if retval is None:
                return

            # calculate remaining timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining_s = timeout_s - elapsed
            if remaining_s <= 0:
                raise TimeoutError(f"container_id '{container_id}' appears in DB within {timeout_s}s")

            # wait for either condition notification or timeout slice
            wait_time_s = min(check_interval_s, remaining_s)
            async with self._wait_for_container_id_condition:
                try:
                    await asyncio.wait_for(self._wait_for_container_id_condition.wait(), timeout=wait_time_s)
                    print("Woke up by notification, rechecking DB...")
                except asyncio.TimeoutError:
                    print(f"No notification in {remaining_s}s, rechecking DB...")