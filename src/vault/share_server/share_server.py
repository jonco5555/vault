import grpc

from vault.common.generated.vault_pb2 import DecryptResponse, StoreShareResponse
from vault.common.generated.vault_pb2_grpc import ShareServerServicer
from vault.common.types import Key
from vault.crypto.asymmetric import decrypt, generate_key_pair
from vault.crypto.threshold import partial_decrypt


class ShareServer(ShareServerServicer):
    def __init__(self):
        self._privkey_b64, self._pubkey_b64 = generate_key_pair()
        self._encrypted_shares: dict[bytes] = {}

    # TODO: Register to manager as server

    async def StoreShare(self, request, context):
        if request.user_id in self._encrypted_shares:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Share for this user already exists.")
            return StoreShareResponse(success=False)
        self._encrypted_shares[request.user_id] = request.encrypted_share
        return StoreShareResponse(success=True)

    async def Decrypt(self, request, context):
        if request.user_id not in self._encrypted_shares:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No share found for this user.")
            return DecryptResponse()
        share = Key.model_validate_json(
            decrypt(self._encrypted_shares.get(request.user_id), self._privkey_b64)
        )
        partial_decrypted = partial_decrypt(request.secret, share)
        return DecryptResponse(partial_decrypted=partial_decrypted)
