import logging
from typing import Union

import grpc

from vault.common.generated.vault_pb2 import (
    InnerRequest,
    InnerResponse,
    RegisterRequest,
    RegisterResponse,
    RetrieveSecretRequest,
    RetrieveSecretResponse,
    SecureReqMsgWrapper,
    SecureRespMsgWrapper,
    SRPFirstStep,
    SRPThirdStep,
    StoreSecretRequest,
    StoreSecretResponse,
)
from vault.common.generated.vault_pb2_grpc import ManagerStub
from vault.common.types import Key, PartialDecryption
from vault.crypto import asymmetric, certs, threshold
from vault.crypto.authentication import (
    srp_authentication_client_step_two,
    srp_registration_client_generate_data,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class User:
    def __init__(
        self,
        user_id: str,
        server_ip: str,
        server_port: int,
        threshold: int,
        num_of_total_shares: int,
        ca_cert_path: str = "certs/ca.crt",
    ):
        self._logger = logging.getLogger(__class__.__name__)
        self._user_id = user_id
        self._server_ip = server_ip
        self._server_port = server_port
        self._threshold = threshold
        self._num_of_total_shares = num_of_total_shares
        self._privkey_b64, self._pubkey_b64 = asymmetric.generate_key_pair()
        self._ca_cert = certs.load_ca_cert(ca_cert_path)
        self._creds = grpc.ssl_channel_credentials(root_certificates=self._ca_cert)
        self._encrypted_share = None
        self._encryption_key = None
        self._secrets_ids = set()

    async def register(self, password: str):
        _, password_verifier, salt = srp_registration_client_generate_data(
            username=self._user_id,
            password=password,
        )

        async with grpc.aio.secure_channel(
            f"{self._server_ip}:{self._server_port}", self._creds
        ) as channel:
            stub = ManagerStub(channel)
            response: RegisterResponse = await stub.Register(
                RegisterRequest(
                    user_id=self._user_id,
                    verifier=password_verifier,
                    salt=salt,
                    user_public_key=self._pubkey_b64,
                )
            )

            self._encrypted_share = response.encrypted_share
            self._encryption_key = Key.model_validate_json(
                asymmetric.decrypt(
                    response.encrypted_key,
                    self._privkey_b64,
                )
            )

    # --- Client code: secure call ---
    async def do_secure_call(
        self,
        password: str,
        request_protobuf: Union[
            RegisterRequest,
            StoreSecretRequest,
            RetrieveSecretRequest,
        ],
    ) -> bytes:
        async with grpc.aio.secure_channel(
            f"{self._server_ip}:{self._server_port}", self._creds
        ) as channel:
            stub = ManagerStub(channel)
            call = stub.SecureCall()

            # send client_init
            await call.write(
                SecureReqMsgWrapper(auth_step_1=SRPFirstStep(username=self._user_id))
            )

            # read server_resp
            auth_step_2_msg: SecureRespMsgWrapper = await call.read()
            if not auth_step_2_msg or not auth_step_2_msg.HasField("auth_step_2"):
                raise RuntimeError("expected auth_step_2")

            salt: str = auth_step_2_msg.auth_step_2.salt
            server_public: str = auth_step_2_msg.auth_step_2.server_public_key

            client_public, _client_session_key, client_session_key_proof = (
                srp_authentication_client_step_two(
                    username=self._user_id,
                    password=password,
                    server_public_key=server_public,
                    salt=salt,
                )
            )

            await call.write(
                SecureReqMsgWrapper(
                    auth_step_3=SRPThirdStep(
                        client_public_key=client_public,
                        client_session_key_proof=client_session_key_proof,
                    )
                )
            )
            auth_step_3_ack_msg: SecureRespMsgWrapper = await call.read()
            if not auth_step_3_ack_msg or not auth_step_3_ack_msg.HasField(
                "auth_step_3_ack"
            ):
                raise RuntimeError("expected auth_step_3_ack")

            if not auth_step_3_ack_msg.auth_step_3_ack.ok:
                raise RuntimeError("expected ok")

            # send application request
            app_req = self._create_inner_request_from_user_request(request_protobuf)
            await call.write(SecureReqMsgWrapper(app_req=app_req))

            # read app response
            app_resp_msg = await call.read()
            await call.done_writing()

            if not app_resp_msg or not app_resp_msg.HasField("app_resp"):
                raise RuntimeError("expected app_resp")
            app_res = self._create_user_response_from_inner_response(
                app_resp_msg.app_resp
            )
            return app_res

    def _create_inner_request_from_user_request(
        self,
        request_protobuf: Union[
            StoreSecretRequest,
            RetrieveSecretRequest,
        ],
    ) -> InnerRequest:
        if type(request_protobuf) is StoreSecretRequest:
            return InnerRequest(store=request_protobuf)
        elif type(request_protobuf) is RetrieveSecretRequest:
            return InnerRequest(retrieve=request_protobuf)
        else:
            raise RuntimeError(
                f"unknown request_protobuf type: {type(request_protobuf)}"
            )

    def _create_user_response_from_inner_response(
        self,
        inner_response: InnerResponse,
    ) -> Union[
        StoreSecretResponse,
        RetrieveSecretResponse,
    ]:
        if inner_response.HasField("store"):
            return inner_response.store
        elif inner_response.HasField("retrieve"):
            return inner_response.retrieve
        else:
            raise RuntimeError("unknown InnerRequest body type")

    async def store_secret(self, password: str, secret: str, secret_id: str) -> bool:
        self._secrets_ids.add(secret_id)
        encrypted_secret = threshold.encrypt(secret, self._encryption_key)
        response: StoreSecretResponse = await self.do_secure_call(
            password=password,
            request_protobuf=StoreSecretRequest(
                user_id=self._user_id,
                secret_id=secret_id,
                secret=encrypted_secret,
            ),
        )
        return response.success

    async def retrieve_secret(self, password: str, secret_id: str) -> str | None:
        if secret_id not in self._secrets_ids:
            print(f"Secret ID {secret_id} not found for user {self._user_id}")
            return None

        response: RetrieveSecretResponse = await self.do_secure_call(
            password=password,
            request_protobuf=RetrieveSecretRequest(
                user_id=self._user_id,
                secret_id=secret_id,
            ),
        )

        if not response.encrypted_partial_decryptions:
            print(f"Failed to retrieve secret {secret_id} for user {self._user_id}")
            return None

        share = Key.model_validate_json(
            asymmetric.decrypt(self._encrypted_share, self._privkey_b64)
        )
        partial_decrypted = threshold.partial_decrypt(response.secret, share)

        list_partially_decrypted = [
            PartialDecryption.model_validate_json(
                asymmetric.decrypt(encrypted_partial_decrypted, self._privkey_b64)
            )
            for encrypted_partial_decrypted in response.encrypted_partial_decryptions
        ]
        list_partially_decrypted.append(partial_decrypted)

        decrypted_secret = threshold.decrypt(
            list_partially_decrypted,
            response.secret,
            self._threshold,
            self._num_of_total_shares,
        )
        return decrypted_secret

    def get_secrets_ids(self) -> set[str]:
        return self._secrets_ids
