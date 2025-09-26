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
from vault.crypto.asymmetric import decrypt, encrypt, generate_key_pair
from vault.crypto.certs import generate_component_cert_and_key, load_ca_cert
from vault.crypto.threshold import partial_decrypt

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class ShareServer(ShareServerServicer):
    def __init__(
        self,
        name: str,
        port: int,
        ca_cert_path: str = "certs/ca.crt",
        ca_key_path: str = "certs/ca.key",
    ):
        self._logger = logging.getLogger(__class__.__name__)
        self._port = port
        self._cert, self._ssl_privkey = generate_component_cert_and_key(
            name=name,
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
        )
        self._ca_cert = load_ca_cert(ca_cert_path)

        # grpc server
        self._server_creds = grpc.ssl_server_credentials(
            [(self._ssl_privkey, self._cert)]
        )
        self._client_creds = grpc.ssl_channel_credentials(
            root_certificates=self._ca_cert
        )
        self._server = grpc.aio.server()
        add_ShareServerServicer_to_server(self, self._server)
        self._port = self._server.add_secure_port(
            f"[::]:{self._port}", self._server_creds
        )

        self._privkey_b64, self._pubkey_b64 = generate_key_pair()
        self._encrypted_shares: dict[bytes] = {}

    async def start(self):
        await self._server.start()
        self._logger.info(f"Share server started on port {self._port}")

    async def close(self):
        if self._server:
            await self._server.stop(grace=5.0)
        self._logger.info("Share server stopped")

    async def StoreShare(self, request, context):
        self._logger.info(f"Share server storing share for {request.user_id}")
        if request.user_id in self._encrypted_shares:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Share for this user already exists.")
            return StoreShareResponse(success=False)
        self._encrypted_shares[request.user_id] = request.encrypted_share
        return StoreShareResponse(success=True)

    async def DeleteShare(self, request, context):
        self._logger.info(f"Share server deleting share for {request.user_id}")
        if request.user_id not in self._encrypted_shares:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Share does not exist for this user")
            return DeleteShareResponse(success=False)
        del self._encrypted_shares[request.user_id]
        return DeleteShareResponse(success=True)

    async def Decrypt(self, request, context):
        self._logger.info(f"Share server decrypting using share for {request.user_id}")
        if request.user_id not in self._encrypted_shares:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No share found for this user.")
            return DecryptResponse()
        share = Key.model_validate_json(
            decrypt(self._encrypted_shares.get(request.user_id), self._privkey_b64)
        )
        partial_decryption = partial_decrypt(request.secret, share)
        encrypted_partial_decryption = encrypt(
            partial_decryption.model_dump_json().encode(), request.user_public_key
        )
        return DecryptResponse(
            encrypted_partial_decryption=encrypted_partial_decryption
        )
