import grpc

from vault.common.generated.vault_pb2 import DecryptResponse, Key, StoreShareResponse
from vault.common.generated.vault_pb2_grpc import ShareServerServicer
from vault.crypto.threshold import partial_decrypt


class ShareServer(ShareServerServicer):
    def __init__(self):
        self._shares: dict[Key] = {}

    async def StoreShare(self, request, context):
        if request.user_id in self._shares:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Share for this user already exists.")
            return StoreShareResponse(success=False)
        self._shares[request.user_id] = request.share
        return StoreShareResponse(success=True)

    async def Decrypt(self, request, context):
        if request.user_id not in self._shares:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No share found for this user.")
            return DecryptResponse()
        partial_decrypted = partial_decrypt(
            request.secret, self._shares.get(request.user_id)
        )
        return DecryptResponse(partial_decrypted=partial_decrypted)
