import grpc
from typing import Optional

from vault.common.generated.vault_pb2 import (
    RegisterRequest,
    RetrieveSecretRequest,
    StoreSecretRequest,
)
from vault.common.generated.vault_pb2_grpc import ManagerStub
from vault.common.types import Key
from vault.crypto.asymmetric import generate_key_pair
from vault.crypto.threshold import decrypt, encrypt, partial_decrypt
from vault.crypto.certificate_manager import get_certificate_manager
from vault.crypto.grpc_ssl import SSLContext


class User:
    def __init__(
        self,
        user_id: str,
        server_ip: str,
        server_port: int,
        threshold: int,
        num_of_share_servers: int,
        ssl_context: Optional[SSLContext] = None,
    ):
        self._user_id = user_id
        self._server_ip = server_ip
        self._server_port = server_port
        self._threshold = threshold
        self._num_of_share_servers = num_of_share_servers
        self._privkey_b64, self._pubkey_b64 = generate_key_pair()
        self.encrypted_share = None
        self._encryption_key = None
        self._secrets_ids = set()
        
        # SSL context for secure gRPC communication
        if ssl_context is None:
            # Create a default SSL context for this user
            cert_manager = get_certificate_manager()
            self._ssl_context = cert_manager.issue_client_certificate(f"user-{user_id}")
        else:
            self._ssl_context = ssl_context

    async def register(self):
        async with self._ssl_context.create_secure_channel(
            f"{self._server_ip}:{self._server_port}"
        ) as channel:
            stub = ManagerStub(channel)
            response = await stub.Register(
                RegisterRequest(
                    user_id=self._user_id,
                    user_public_key=self._pubkey_b64,
                )
            )

            self._encrypted_share = response.encrypted_share
            self._encryption_key = Key.model_validate_json(
                decrypt(
                    response.encrypted_key,  # Fixed this line - was incorrectly accessing _encrypted_shares
                    self._privkey_b64,
                )
            )

    async def store_secret(self, secret: str, secret_id: str) -> bool:
        self._secrets_ids.add(secret_id)
        encrypted_secret = encrypt(secret, self._encryption_key)
        async with self._ssl_context.create_secure_channel(
            f"{self._server_ip}:{self._server_port}"
        ) as channel:
            stub = ManagerStub(channel)
            response = await stub.StoreSecret(
                StoreSecretRequest(
                    user_id=self._user_id,
                    secret_id=secret_id,
                    secret=encrypted_secret,
                )
            )
            return response.success

    async def retrieve_secret(self, secret_id: str) -> str | None:
        # TODO: Do the user really needs to save secret_ids?
        if secret_id not in self._secrets_ids:
            print(f"Secret ID {secret_id} not found for user {self._user_id}")
            return None

        async with self._ssl_context.create_secure_channel(
            f"{self._server_ip}:{self._server_port}"
        ) as channel:
            stub = ManagerStub(channel)
            response = await stub.RetrieveSecret(
                RetrieveSecretRequest(
                    user_id=self._user_id,
                    secret_id=secret_id,
                    auth_token="valid_token",  # TODO: implement auth token
                )
            )

        if not response.partial_decryptions:
            print(f"Failed to retrieve secret {secret_id} for user {self._user_id}")
            return None

        share = Key.model_validate_json(
            decrypt(self._encrypted_share, self._privkey_b64)
        )
        partial_decrypted = partial_decrypt(response.secret, share)
        decrypted_secret = decrypt(
            [response.partial_decryptions, partial_decrypted],
            response.secret,
            self._threshold,
            self._num_of_share_servers,
        )
        return decrypted_secret

    def get_secrets_ids(self) -> set[str]:
        return self._secrets_ids
