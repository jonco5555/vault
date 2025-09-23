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
def share():
    return types.Key(x="123", y="456").model_dump_json().encode()


@pytest_asyncio.fixture
async def server():
    return ShareServer("share", 0)


@pytest.fixture
def share_server(server) -> _Server:
    servicers = {
        DESCRIPTOR.services_by_name["ShareServer"]: server,
    }
    return grpc_testing.server_from_dictionary(
        servicers, grpc_testing.strict_real_time()
    )


@pytest_asyncio.fixture
async def share_server_stub(server: ShareServer):
    await server.start()
    creds = grpc.ssl_channel_credentials(root_certificates=server._cert)
    async with grpc.aio.secure_channel(f"localhost:{server._port}", creds) as channel:
        stub = ShareServerStub(channel)
        yield stub

    await server.close()


@pytest.fixture
def partial_decrypt_mocker():
    with patch(
        "vault.share_server.share_server.partial_decrypt"
    ) as mock_partial_decrypt:
        mock_partial_decrypt.return_value = PartialDecrypted(
            x="123", yc1=pb2.Key(x="456", y="789")
        )
        yield mock_partial_decrypt
        mock_partial_decrypt.assert_called_once()


@pytest.fixture
def store_request(user_id, share, server):
    encrypted_share = encrypt(share, server._pubkey_b64)
    return StoreShareRequest(user_id=user_id, encrypted_share=encrypted_share)


@pytest.fixture
def decrypt_request(user_id):
    return DecryptRequest(
        user_id=user_id,
        secret=Secret(
            c1=pb2.Key(x="123", y="456"),
            c2=pb2.Key(x="123", y="456"),
            ciphertext=b"ciphertext",
        ),
    )


@pytest.fixture
def delete_request(user_id):
    return StoreShareRequest(user_id=user_id)


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
async def test_store_share_success(share_server: _Server, store_request):
    # Act
    response, _, code, _ = invoke_method(store_request, share_server, "StoreShare")
    response = await response

    # Assert
    assert code == grpc.StatusCode.OK
    assert response.success


@pytest.mark.asyncio
async def test_decrypt_success_with_mocked_share_server(
    share_server: _Server,
    store_request,
    partial_decrypt_mocker,
    decrypt_request,
):
    # Act
    # Store first
    store_response = await invoke_method(store_request, share_server, "StoreShare")[0]
    assert store_response.success
    # Decrypt
    response, _, code, _ = invoke_method(decrypt_request, share_server, "Decrypt")
    response = await response

    # Assert
    assert code == grpc.StatusCode.OK
    assert response.partial_decrypted_secret is not None


@pytest.mark.asyncio
async def test_store_share_raises_exception_when_user_exists(
    share_server_stub, store_request
):
    # Act
    response = await share_server_stub.StoreShare(store_request)
    assert response.success
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        # Duplicate store
        response = await share_server_stub.StoreShare(store_request)
        assert exc_info.value.code() == grpc.StatusCode.ALREADY_EXISTS
        assert not response.success


@pytest.mark.asyncio
async def test_decrypt_success(
    share_server_stub, store_request, partial_decrypt_mocker, decrypt_request
):
    # Act
    store_response = await share_server_stub.StoreShare(store_request)
    assert store_response.success
    decrypt_response = await share_server_stub.Decrypt(decrypt_request)

    # Assert
    assert decrypt_response.partial_decrypted_secret is not None


@pytest.mark.asyncio
async def test_decrypt_not_found(share_server_stub, decrypt_request):
    # Act
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await share_server_stub.Decrypt(decrypt_request)

        # Assert
        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_success_with_mocked_share_server(
    share_server: _Server,
    store_request,
    delete_request,
):
    # Act
    # Store first
    store_response = await invoke_method(store_request, share_server, "StoreShare")[0]
    assert store_response.success
    # Decrypt
    response, _, code, _ = invoke_method(delete_request, share_server, "DeleteShare")
    response = await response

    # Assert
    assert code == grpc.StatusCode.OK


@pytest.mark.asyncio
async def test_delete_not_found(share_server_stub, delete_request):
    # Act
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await share_server_stub.DeleteShare(delete_request)

        # Assert
        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
