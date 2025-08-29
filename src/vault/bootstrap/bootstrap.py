from vault.common.generated.vault_pb2 import GenerateSharesResponse
from vault.common.generated.vault_pb2_grpc import BootstrapServicer
from vault.crypto.threshold import generate_key_and_shares


class Bootstrap(BootstrapServicer):
    async def GenerateShares(self, request, context):
        encryption_key, shares = generate_key_and_shares(
            request.threshold, request.num_of_shares
        )
        ########################################################
        # TODO: encrypt shares with request.public_keys
        ########################################################
        return GenerateSharesResponse(shares=shares, encryption_key=encryption_key)
