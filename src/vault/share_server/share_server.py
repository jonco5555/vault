import logging

import grpc

from vault.common.generated.vault_pb2 import (
    DecryptResponse,
    DeleteShareResponse,
    StoreShareResponse,
)
from vault.common.generated.vault_pb2_grpc import (
    ShareServerServicer,
    add_ShareServerServicer_to_server,
)
from vault.common.types import Key
from vault.crypto.asymmetric import decrypt, generate_key_pair
from vault.crypto.threshold import partial_decrypt

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class ShareServer(ShareServerServicer):
    def __init__(self, port: int):
        self._logger = logging.getLogger(__class__.__name__)
        # grpc server
        self._port = port
        self._server = grpc.aio.server()
        add_ShareServerServicer_to_server(self, self._server)
        self._server.add_insecure_port(f"[::]:{self._port}")

        self._privkey_b64, self._pubkey_b64 = generate_key_pair()
        self._encrypted_shares: dict[bytes] = {}

    async def start(self):
        await self._server.start()
        self._logger.info(f"Bootstrap server started on port {self._port}")

    async def close(self):
        if self._server:
            await self._server.stop(grace=5.0)
        self._logger.info("Bootstrap server stopped")

    # TODO: Register to manager as server
    async def register():
        pass

    async def StoreShare(self, request, context):
        if request.user_id in self._encrypted_shares:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Share for this user already exists.")
            return StoreShareResponse(success=False)
        self._encrypted_shares[request.user_id] = request.encrypted_share
        return StoreShareResponse(success=True)

    async def DeleteShare(self, request, context):
        if request.user_id not in self._encrypted_shares:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Share does not exist for this user")
            return DeleteShareResponse(success=False)
        del self._encrypted_shares[request.user_id]
        return DeleteShareResponse(success=True)

    async def Decrypt(self, request, context):
        if request.user_id not in self._encrypted_shares:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No share found for this user.")
            return DecryptResponse()
        share = Key.model_validate_json(
            decrypt(self._encrypted_shares.get(request.user_id), self._privkey_b64)
        )
        partial_decrypted = partial_decrypt(request.secret, share)
        return DecryptResponse(partial_decrypted_secret=partial_decrypted)
