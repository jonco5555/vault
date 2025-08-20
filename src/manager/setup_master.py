import asyncio
from typing import Optional, List
import grpc
import futures
import docker_utils

from common.generated import vault_setup_pb2
from common.generated import vault_setup_pb2_grpc

#TODO: move db manager to be in manager directory
from vault.db_manager import DBManager

SETUP_MASTER_PORT = 5000
IMAGE_NAME = "vault"
SHARE_SERVER_COMMAND = "python -m src.share_server"
BOOTSTRAP_SERVER_COMMAND = "python -m src.bootstrap"

class SetupMaster(vault_setup_pb2_grpc.SetupMaster):
    def __init__(self, _db: DBManager):
        vault_setup_pb2_grpc.SetupMaster.__init__(self)
        self.db = _db
        self.wait_for_container_id_condition = asyncio.Condition()

        self._is_setup_finished = False
        self.is_setup_finished_lock = asyncio.Lock()
    
    # vault_setup_pb2_grpc.SetupMaster inherited methods
    async def Register(self, request: vault_setup_pb2.RegisterRequest, context):
        await self.db.add_server(request.service_data)
        async with self.wait_for_container_id_condition:
            self.wait_for_container_id_condition.notify_all()
        return vault_setup_pb2.RegisterResponse(is_registered=True)
    
    async def Unregister(self, request: vault_setup_pb2.RegisterRequest, context):
        is_unregistered = False
        try:
            await self.db.remove_server(request.service_data.container_id)
            async with self.wait_for_container_id_condition:
                self.wait_for_container_id_condition.notify_all()
            is_unregistered = True
        except:
            pass
        return vault_setup_pb2.UnregisterResponse(is_registered=is_unregistered)
    
    # API method
    async def start_setup_master_server(self):
        server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        vault_setup_pb2_grpc.add_SetupMasterServicer_to_server(self, server)
        server.add_insecure_port(f'[::]:{SETUP_MASTER_PORT}')
        await server.start()
        print(f"SetupMaster started start_setup_master_server on port {SETUP_MASTER_PORT}...")
        await server.wait_for_termination()

    async def do_setup(self, share_servers_num: int):
        for i in range(share_servers_num):
            print(f"spawaning shareServer {i}")
            #TODO
        async with self.is_setup_finished_lock:
            self._is_setup_finished = True

    async def is_setup_finished(self) -> bool:
        async with self.is_setup_finished_lock:
            return self._is_setup_finished

    async def spawn_bootstrap_server(self) -> vault_setup_pb2.ServiceData:
        container = await docker_utils.spawn_container(IMAGE_NAME, command=BOOTSTRAP_SERVER_COMMAND)
        return await self._wait_for_container_id(container.id)

    async def kill_server(self, container_id: str):
        #TODO
        pass
    
    async def get_all_share_servers(self) -> List[vault_setup_pb2.ServiceData]:
        #TODO        
        pass

    # Private methods
    async def _spawn_share_server():
        docker_utils.spawn_container(IMAGE_NAME, command=SHARE_SERVER_COMMAND)

    async def _get_container_data(self, container_id: str) -> Optional[vault_setup_pb2.ServiceData]:
        return await self.db.get_server(container_id)

    async def _wait_for_container_id(self, container_id: str, timeout_s: int = 10) -> vault_setup_pb2.ServiceData:
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
            async with self.wait_for_container_id_condition:
                try:
                    await asyncio.wait_for(self.wait_for_container_id_condition.wait(), timeout=wait_time_s)
                    print("Woke up by notification, rechecking DB...")
                except asyncio.TimeoutError:
                    print(f"No notification in {remaining_s}s, rechecking DB...")