from unittest.mock import patch

import grpc
import grpc_testing
import pytest
import pytest_asyncio
from grpc_testing._server._server import _Server

from vault.common import types
from vault.common.generated import vault_pb2 as pb2
from vault.common.generated.vault_pb2 import (
    DESCRIPTOR,
    DecryptRequest,
    PartialDecrypted,
    Secret,
    StoreShareRequest,
)
from vault.common.generated.vault_pb2_grpc import ShareServerStub
from vault.crypto.asymmetric import encrypt
from vault.share_server.share_server import ShareServer


@pytest.fixture
def user_id() -> str:
    return "user_1"


@pytest.fixture
def share():
    return types.Key(x="123", y="456").model_dump_json().encode()


@pytest.fixture
def share_server(share) -> tuple[_Server, bytes]:
    server = ShareServer(0)
    encrypted_share = encrypt(share, server._pubkey_b64)
    servicers = {
        DESCRIPTOR.services_by_name["ShareServer"]: server,
    }
    return grpc_testing.server_from_dictionary(
        servicers, grpc_testing.strict_real_time()
    ), encrypted_share


def invoke_method(request, server: _Server, method: str):
    method_descriptor = DESCRIPTOR.services_by_name["ShareServer"].methods_by_name[
        method
    ]
    rpc = server.invoke_unary_unary(
        method_descriptor=method_descriptor,
        invocation_metadata={},
        request=request,
        timeout=1,
    )
    return rpc.termination()


@pytest.mark.asyncio
async def test_store_share_success(share_server: tuple[_Server, bytes], user_id):
    # Arrange
    server, encrypted_share = share_server
    request = StoreShareRequest(user_id=user_id, encrypted_share=encrypted_share)

    # Act
    response, _, code, _ = invoke_method(request, server, "StoreShare")
    response = await response

    # Assert
    assert code == grpc.StatusCode.OK
    assert response.success


@pytest.mark.asyncio
async def test_decrypt_success_with_mocked_share_server(
    share_server: tuple[_Server, bytes], user_id
):
    # Arrange
    server, encrypted_share = share_server
    store_request = StoreShareRequest(user_id=user_id, encrypted_share=encrypted_share)
    decrypt_request = DecryptRequest(
        user_id=user_id,
        secret=Secret(
            c1=pb2.Key(x="123", y="456"),
            c2=pb2.Key(x="123", y="456"),
            ciphertext=b"ciphertext",
        ),
    )

    # Act
    # Store first
    store_response = await invoke_method(store_request, server, "StoreShare")[0]
    assert store_response.success

    with patch(
        "vault.share_server.share_server.partial_decrypt"
    ) as mock_partial_decrypt:
        mock_partial_decrypt.return_value = PartialDecrypted(
            x="123", yc1=pb2.Key(x="456", y="789")
        )
        # Decrypt
        response, _, code, _ = invoke_method(decrypt_request, server, "Decrypt")
        response = await response

        # Assert
        mock_partial_decrypt.assert_called_once()
        assert code == grpc.StatusCode.OK
        assert response.partial_decrypted_secret is not None


@pytest_asyncio.fixture
async def share_server_stub():
    share_server = ShareServer(50051)
    await share_server.start()
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = ShareServerStub(channel)
        yield stub, share_server._pubkey_b64

    await share_server.close()


@pytest.mark.asyncio
async def test_store_share_raises_exception_when_user_exists(share_server_stub):
    # Arrange
    stub, server_key = share_server_stub
    user_id = "user1"
    share = types.Key(x="123", y="456").model_dump_json().encode()
    encrypted_share = encrypt(share, server_key)
    request = StoreShareRequest(user_id=user_id, encrypted_share=encrypted_share)

    # Act
    response = await stub.StoreShare(request)
    assert response.success
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        # Duplicate store
        response = await stub.StoreShare(request)
        assert exc_info.value.code() == grpc.StatusCode.ALREADY_EXISTS
        assert not response.success


@pytest.mark.asyncio
async def test_decrypt_success(share_server_stub):
    # Arrange
    stub, server_key = share_server_stub
    user_id = "user1"
    share = types.Key(x="123", y="456").model_dump_json().encode()
    encrypted_share = encrypt(share, server_key)
    store_request = StoreShareRequest(user_id=user_id, encrypted_share=encrypted_share)
    decrypt_request = DecryptRequest(
        user_id=user_id,
        secret=Secret(
            c1=pb2.Key(x="123", y="456"),
            c2=pb2.Key(x="123", y="456"),
            ciphertext=b"ciphertext",
        ),
    )

    with patch(
        "vault.share_server.share_server.partial_decrypt"
    ) as mock_partial_decrypt:
        mock_partial_decrypt.return_value = PartialDecrypted(
            x="123", yc1=pb2.Key(x="456", y="789")
        )
        # Act
        store_response = await stub.StoreShare(store_request)
        assert store_response.success
        decrypt_response = await stub.Decrypt(decrypt_request)

        mock_partial_decrypt.assert_called_once()
        assert decrypt_response.partial_decrypted_secret is not None


@pytest.mark.asyncio
async def test_decrypt_not_found(share_server_stub):
    # Arrange
    stub, _ = share_server_stub
    user_id = "user1"
    request = DecryptRequest(
        user_id=user_id,
        secret=Secret(
            c1=pb2.Key(x="123", y="456"),
            c2=pb2.Key(x="123", y="456"),
            ciphertext=b"ciphertext",
        ),
    )

    # Act
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await stub.Decrypt(request)
        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
