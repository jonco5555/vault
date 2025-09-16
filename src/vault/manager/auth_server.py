import logging
import asyncio

from concurrent import futures

import grpc
from vault.common.generated import auth_pb2, auth_pb2_grpc
from vault.manager.db_manager import DBManager
from srptools import SRPContext, SRPServerSession


# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-server")

# # --- Utility: derive AEAD key from session key ---
# TODO: probably ot used - think how to remove this
# def derive_aead_key(session_key: bytes, info=b"auth-opaque-aead"):
#     hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info)
#     return hkdf.derive(session_key)


# --- gRPC service implementation ---
class AuthService(auth_pb2_grpc.AuthServiceServicer):
    def __init__(
        self,
        db: DBManager,
        server_ip: str,
        server_port: int,
    ):
        self._logger = logging.getLogger(__class__.__name__)
        self._server_ip = server_ip
        self._server_port = server_port

        self._server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        auth_pb2_grpc.add_AuthServiceServicer_to_server(self, self._server)
        self._server.add_insecure_port(f"{self._server_ip}:{self._server_port}")

        # DB
        self._db = db

    async def AuthRegister(self, request: auth_pb2.AuthRegisterRequest, context):
        logger.info("Register request for %s", request.username)
        try:
            await self._db.add_auth_client(
                username=request.username, verifier=request.verifier, salt=request.salt
            )
        except Exception as e:
            logger.exception("SRP registration failed")
            return auth_pb2.AuthRegisterResponse(ok=False, err=str(e))
        return auth_pb2.AuthRegisterResponse(ok=True)

    async def SecureCall(self, request_iterator, context):
        """
        Bidirectional stream handling:
        """
        # md = dict(context.invocation_metadata())
        # username = md.get("username")
        # if not username:
        #     await context.abort(grpc.StatusCode.UNAUTHENTICATED, "username metadata required")
        # logger.info("SecureCall stream started for user=%s", username)

        ait = request_iterator.__aiter__()

        # 1) Expect client_init
        try:
            msg: auth_pb2.SecureReqMsgWrapper = await ait.__anext__()
        except StopAsyncIteration:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no messages")
            return

        if not msg or not msg.HasField("first_step"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "expected first_step")
            return

        username: str = msg.first_step.username
        password_verifier: str = await self._db.get_auth_client_verifier(username)
        salt: str = await self._db.get_auth_client_salt(username)
        # 2) server starts SRP login
        print(f"{username=}, {password_verifier=}, {salt=}")

        srp_context = SRPContext(username)
        print(f"{srp_context.generator=}, {srp_context.prime=}")
        server_session = SRPServerSession(srp_context, password_verifier)
        server_public_key = server_session.public

        # send server_resp
        print(f"{server_public_key=}, {salt=}")
        yield auth_pb2.SecureRespMsgWrapper(
            second_step=auth_pb2.SRPSecondStep(
                server_public_key=server_public_key,
                salt=salt,
            )
        )

        # 3) expect client_final
        try:
            msg2: auth_pb2.SecureReqMsgWrapper = await ait.__anext__()
        except StopAsyncIteration:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "no third_step")
            return

        if not msg2 or not msg2.HasField("third_step"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "expected third_step")
            return

        third_step: auth_pb2.SRPThirdStep = msg2.third_step

        # 4) finish login and get session key
        try:
            print(
                f"authenticating... {third_step.client_public_key=} {third_step.client_session_key_proof=} {salt=}"
            )
            server_session.process(third_step.client_public_key, salt)
        except Exception as e:
            print("err 1")
            logger.exception("opaque finish failed")
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "opaque finish failed: " + str(e)
            )
            return

        print(f"verify_proof... {third_step.client_session_key_proof=}")
        if not server_session.verify_proof(third_step.client_session_key_proof):
            print("err 2")
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED, "authentication failed"
            )
            return

        yield auth_pb2.SecureRespMsgWrapper(
            third_step_ack=auth_pb2.SRPThirdStepAck(
                ok=True,
            )
        )

        # 5) expect application request
        try:
            msg3: auth_pb2.SecureReqMsgWrapper = await ait.__anext__()
        except StopAsyncIteration:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "expected app_req")
            return

        if not msg3 or not msg3.HasField("app_req"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "expected app_req")
            return

        app_req: auth_pb2.AppRequest = msg3.app_req

        print(f"app_req: {app_req.payload_type}, {app_req.payload}")

        app_resp: auth_pb2.AppResponse = auth_pb2.AppResponse(
            payload_type=app_req.payload_type, payload=app_req.payload
        )

        # process request (dummy echo)
        logger.info(
            "Processed payload_type=%s, user=%s", app_req.payload_type, username
        )

        yield auth_pb2.SecureRespMsgWrapper(app_resp=app_resp)

    async def start_auth_server(self):
        try:
            await self._server.start()
            print(
                f"AuthService started start_auth_server on port {self._server_port}..."
            )
            await self._server.wait_for_termination()
        except asyncio.CancelledError:
            print("Stoppig Authservice...")
            await self._server.stop(grace=10)  # grace period of 10 seconds
