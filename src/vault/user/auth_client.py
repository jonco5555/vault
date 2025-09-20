from typing import Union
import logging

import grpc
from vault.common.generated import auth_pb2, auth_pb2_grpc
from vault.common.generated import vault_pb2

from vault.crypto.authentication import (
    srp_registration_client_generate_data,
    srp_authentication_client_step_two,
)

logger = logging.getLogger("auth-client")
logging.basicConfig(level=logging.INFO)


class AuthClient:
    def __init__(
        self,
        server_ip: str,
        server_port: int,
    ):
        self._auth_server_ip = server_ip
        self._auth_server_port = server_port

    # --- Client code: registration ---
    async def register(self, username: str, password: str):
        _, password_verifier, salt = srp_registration_client_generate_data(
            username=username,
            password=password,
        )

        _address = f"{self._auth_server_ip}:{self._auth_server_port}"
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            resp: auth_pb2.AuthRegisterResponse = await stub.AuthRegister(
                auth_pb2.AuthRegisterRequest(
                    username=username,
                    verifier=password_verifier,
                    salt=salt,
                )
            )
            if not resp.ok:
                raise RuntimeError(f"could not register user {username}")

    # --- Client code: secure call ---
    async def do_secure_call(
        self,
        username: str,
        password: str,
        request_protobuf: Union[
            vault_pb2.RegisterRequest,
            vault_pb2.StoreSecretRequest,
            vault_pb2.RetrieveSecretRequest,
        ],
    ) -> bytes:
        _address = f"{self._auth_server_ip}:{self._auth_server_port}"
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            call = stub.SecureCall()

            # send client_init
            await call.write(
                auth_pb2.SecureReqMsgWrapper(
                    first_step=auth_pb2.SRPFirstStep(username=username)
                )
            )

            # read server_resp
            srv_msg: auth_pb2.SecureRespMsgWrapper = await call.read()
            if not srv_msg or not srv_msg.HasField("second_step"):
                raise RuntimeError("expected server_resp")

            salt: str = srv_msg.second_step.salt
            server_public: str = srv_msg.second_step.server_public_key

            client_public, client_session_key, client_session_key_proof = (
                srp_authentication_client_step_two(
                    username=username,
                    password=password,
                    server_public_key=server_public,
                    salt=salt,
                )
            )

            await call.write(
                auth_pb2.SecureReqMsgWrapper(
                    third_step=auth_pb2.SRPThirdStep(
                        client_public_key=client_public,
                        client_session_key_proof=client_session_key_proof,
                    )
                )
            )
            srv_msg2: auth_pb2.SecureRespMsgWrapper = await call.read()
            if not srv_msg2 or not srv_msg2.HasField("third_step_ack"):
                raise RuntimeError("expected third_step_ack")

            if not srv_msg2.third_step_ack.ok:
                raise RuntimeError("expected ok")

            # send application request
            app_req = self._create_inner_request_from_user_request(request_protobuf)
            await call.write(auth_pb2.SecureReqMsgWrapper(app_req=app_req))

            # read app response
            resp_msg = await call.read()
            await call.done_writing()

            if not resp_msg or not resp_msg.HasField("app_resp"):
                raise RuntimeError("expected app_resp")
            app_res = self._create_user_response_from_inner_response(resp_msg.app_resp)
            return app_res

    def _create_inner_request_from_user_request(
        self,
        request_protobuf: Union[
            vault_pb2.RegisterRequest,
            vault_pb2.StoreSecretRequest,
            vault_pb2.RetrieveSecretRequest,
        ],
    ) -> auth_pb2.InnerRequest:
        if type(request_protobuf) is vault_pb2.RegisterRequest:
            return auth_pb2.InnerRequest(register=request_protobuf)
        elif type(request_protobuf) is vault_pb2.StoreSecretRequest:
            return auth_pb2.InnerRequest(store=request_protobuf)
        elif type(request_protobuf) is vault_pb2.RetrieveSecretRequest:
            return auth_pb2.InnerRequest(retrieve=request_protobuf)
        else:
            raise RuntimeError(
                f"unknown request_protobuf type: {type(request_protobuf)}"
            )

    def _create_user_response_from_inner_response(
        self,
        inner_response: auth_pb2.InnerRequest,
    ) -> Union[
        vault_pb2.RegisterRequest,
        vault_pb2.StoreSecretRequest,
        vault_pb2.RetrieveSecretRequest,
    ]:
        if inner_response.HasField("register"):
            return inner_response.register
        elif inner_response.HasField("store"):
            return inner_response.store
        elif inner_response.HasField("retrieve"):
            return inner_response.retrieve
        else:
            raise RuntimeError("unknown InnerRequest body type")
