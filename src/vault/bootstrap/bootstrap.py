import grpc

from vault.common.generated.vault_pb2 import GenerateSharesResponse
from vault.common.generated.vault_pb2_grpc import BootstrapServicer
from vault.crypto.asymmetric import encrypt
from vault.crypto.threshold import generate_key_and_shares


class Bootstrap(BootstrapServicer):
    async def GenerateShares(self, request, context):
        encryption_key, shares = generate_key_and_shares(
            request.threshold, request.num_of_shares
        )
        if len(shares) != len(request.public_keys):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                "Number of public keys must match number of shares requested"
            )
            return GenerateSharesResponse()

        encrypted_shares = [
            encrypt(share.model_dump_json().encode(), pub_key)
            for share, pub_key in zip(shares, request.public_keys)
        ]
        encrypted_key = encrypt(
            encryption_key.model_dump_json().encode(), request.public_keys.pop()
        )  # The last key is the user's key
        return GenerateSharesResponse(
            encrypted_shares=encrypted_shares, encrypted_key=encrypted_key
        )
