import logging
from srptools import SRPContext, SRPClientSession

import grpc
from vault.common.generated import auth_pb2, auth_pb2_grpc


logger = logging.getLogger("auth-client")
logging.basicConfig(level=logging.INFO)

SERVER = "localhost:50051"


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
        srp_context = SRPContext(username, password)
        username, password_verifier, salt = srp_context.get_user_data_triplet()

        print(f"{srp_context.generator=}, {srp_context.prime=}")
        print(f"{username=}, {password_verifier=}, {salt=}")
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
            print(f"{resp.ok=}")

    # --- Client code: secure call ---
    async def do_secure_call(
        self, username: str, password: str, payload_type: str, payload: bytes
    ) -> bytes:
        _address = f"{self._auth_server_ip}:{self._auth_server_port}"
        async with grpc.aio.insecure_channel(_address) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            # metadata = (("username", username),)
            call = stub.SecureCall()

            # send client_init
            print("stage one ==>\n")
            await call.write(
                auth_pb2.SecureReqMsgWrapper(
                    first_step=auth_pb2.SRPFirstStep(username=username)
                )
            )

            # read server_resp
            srv_msg: auth_pb2.SecureRespMsgWrapper = await call.read()
            print("stage two <==\n")
            if not srv_msg or not srv_msg.HasField("second_step"):
                raise RuntimeError("expected server_resp")
            second_step: auth_pb2.SRPSecondStep = srv_msg.second_step

            # produce client_final and session_key
            # 4) user receive server public and salt and process them.
            srp_context = SRPContext(username, password)
            print(f"{srp_context.generator=}, {srp_context.prime=}")
            client_session = SRPClientSession(srp_context)
            print(f"{second_step.server_public_key=}, {second_step.salt=}")
            client_session.process(second_step.server_public_key, second_step.salt)
            # 5) user Generate client public and session key.
            client_public = client_session.public
            # client_session_key = client_session.key
            client_session_key_proof = client_session.key_proof

            print("stage three ==>\n")
            # send client_final
            print(f"{client_public=}, {client_session_key_proof=}")
            await call.write(
                auth_pb2.SecureReqMsgWrapper(
                    third_step=auth_pb2.SRPThirdStep(
                        client_public_key=client_public,
                        client_session_key_proof=client_session_key_proof,
                    )
                )
            )
            print("stage three finish ==>\n")
            srv_msg2: auth_pb2.SecureRespMsgWrapper = await call.read()
            print("stage three ack <==\n")
            if not srv_msg2 or not srv_msg2.HasField("third_step_ack"):
                raise RuntimeError("expected third_step_ack")

            if not srv_msg2.third_step_ack.ok:
                raise RuntimeError("expected ok")

            # send application request
            app_req = auth_pb2.AppRequest(payload_type=payload_type, payload=payload)
            await call.write(auth_pb2.SecureReqMsgWrapper(app_req=app_req))

            # read app response
            resp_msg = await call.read()
            if not resp_msg or not resp_msg.HasField("app_resp"):
                raise RuntimeError("expected app_resp")
            app_res: auth_pb2.AppResponse = resp_msg.app_resp
            ct_resp = app_res.payload
            await call.done_writing()
            return ct_resp
