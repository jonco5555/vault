import grpc

from vault.grpc.vault_pb2_grpc import ManagerStub
from vault.grpc.vault_pb2 import (
    RegisterRequest,
    StoreSecretRequest,
    RetrieveSecretRequest,
)
from vault.crypto.asymmetric import generate_key_pair
from vault.crypto.threshold import encrypt, decrypt


class User:
    def __init__(
        self,
        user_id: str,
        server_ip: str,
        server_port: int,
        threshold: int,
        num_of_share_servers: int,
    ):
        self._user_id = user_id
        self._server_ip = server_ip
        self._server_port = server_port
        self._threshold = threshold
        self._num_of_share_servers = num_of_share_servers
        self._privkey_b64, self._pubkey_b64 = generate_key_pair()
        self._share = None
        self._encryption_key = None
        self._secrets_ids = set()

    async def register(self):
        async with grpc.aio.insecure_channel(
            f"{self._server_ip}:{self._server_port}"
        ) as channel:
            stub = ManagerStub(channel)
            response = await stub.Register(
                RegisterRequest(
                    user_id=self._user_id,
                    user_public_key=self._pubkey_b64,
                )
            )

            # TODO: decrypt share with self._privkey_b64
            self._share = response.share
            self._encryption_key = response.encryption_key

    async def store_secret(self, secret: str, secret_id: str) -> bool:
        self._secrets_ids.add(secret_id)
        encrypted_secret = encrypt(secret, self._encryption_key)
        async with grpc.aio.insecure_channel(
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
        if secret_id not in self._secrets_ids:
            print(f"Secret ID {secret_id} not found for user {self._user_id}")
            return None

        async with grpc.aio.insecure_channel(
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
        decrypted_secret = decrypt(
            response.partial_decryptions,
            response.secret,
            self._threshold,
            self._num_of_share_servers,
        )
        return decrypted_secret

    def get_secrets_ids(self) -> set[str]:
        return self._secrets_ids
