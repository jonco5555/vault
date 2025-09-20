import logging
from typing import Optional

import grpc

from vault.common.generated.vault_pb2 import GenerateSharesResponse
from vault.common.generated.vault_pb2_grpc import (
    BootstrapServicer,
    add_BootstrapServicer_to_server,
)
from vault.crypto.asymmetric import encrypt
from vault.crypto.threshold import generate_key_and_shares
from vault.crypto.certificate_manager import get_certificate_manager
from vault.crypto.grpc_ssl import SSLContext

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class Bootstrap(BootstrapServicer):
    def __init__(self, port: int, ssl_context: Optional[SSLContext] = None):
        self._logger = logging.getLogger(__class__.__name__)
        self._port = port
        
        # SSL context for secure gRPC communication
        if ssl_context is None:
            # Create a default SSL context for bootstrap
            cert_manager = get_certificate_manager()
            self._ssl_context = cert_manager.issue_client_certificate("bootstrap")
        else:
            self._ssl_context = ssl_context

        # grpc server
        self._server = grpc.aio.server()
        add_BootstrapServicer_to_server(self, self._server)
        
        # Use secure server credentials
        server_credentials = self._ssl_context.create_server_credentials()
        self._port = self._server.add_secure_port(f"[::]:{self._port}", server_credentials)

    async def start(self):
        await self._server.start()
        self._logger.info(f"Bootstrap server started on port {self._port}")

    async def close(self):
        if self._server:
            await self._server.stop(grace=5.0)
        self._logger.info("Bootstrap server stopped")

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
