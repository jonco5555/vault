import grpc
import grpc_testing
import pytest
import pytest_asyncio
from grpc_testing._server._server import _Server

from vault.bootstrap.bootstrap import Bootstrap
from vault.common.generated.vault_pb2 import (
    DESCRIPTOR,
    GenerateSharesRequest,
)
from vault.common.generated.vault_pb2_grpc import BootstrapStub
from vault.common.types import Key
from vault.crypto.asymmetric import decrypt, generate_key_pair


@pytest.fixture
def key_pairs(request) -> tuple[list[bytes], list[bytes]]:
    n = request.param
    privates = []
    publics = []
    for i in range(n):
        priv, pub = generate_key_pair()
        privates.append(priv)
        publics.append(pub)
    return privates, publics


@pytest.fixture
def bootstrap_server() -> _Server:
    servicers = {
        DESCRIPTOR.services_by_name["Bootstrap"]: Bootstrap(0),
    }
    return grpc_testing.server_from_dictionary(
        servicers, grpc_testing.strict_real_time()
    )


def invoke_method(request, bootstrap_server: _Server):
    method_descriptor = DESCRIPTOR.services_by_name["Bootstrap"].methods_by_name[
        "GenerateShares"
    ]
    rpc = bootstrap_server.invoke_unary_unary(
        method_descriptor=method_descriptor,
        invocation_metadata={},
        request=request,
        timeout=1,
    )
    return rpc.termination()


@pytest.mark.asyncio
@pytest.mark.parametrize("num_of_share_servers", [3])
@pytest.mark.parametrize("key_pairs", [4], indirect=True)
async def test_generate_shares_works(
    num_of_share_servers: int, key_pairs, bootstrap_server: _Server
):
    # Arrange
    privs, pubs = key_pairs
    priv_user = privs[-1]  # last key is user's key
    request = GenerateSharesRequest(
        threshold=num_of_share_servers + 1,  # +1 for the user
        num_of_shares=num_of_share_servers + 1,
        public_keys=pubs,
    )

    # Act
    response, _, code, _ = invoke_method(request, bootstrap_server)
    response = await response

    # Assert
    assert code == grpc.StatusCode.OK
    assert len(response.encrypted_shares) == num_of_share_servers + 1
    Key.model_validate_json(decrypt(response.encrypted_key, priv_user))
    for enc_share, priv in zip(response.encrypted_shares, privs):
        Key.model_validate_json(decrypt(enc_share, priv))


@pytest.mark.asyncio
@pytest.mark.parametrize("num_of_share_servers", [2])
async def test_generate_shares_raises_exception_invalid_key(
    num_of_share_servers: int, bootstrap_server: _Server
):
    # Arrange
    pubs = [b"pub1", b"pub2", b"pub3"]
    request = GenerateSharesRequest(
        threshold=num_of_share_servers + 1,  # +1 for the user
        num_of_shares=num_of_share_servers + 1,
        public_keys=pubs,
    )

    # Act & assert
    response, _, _, _ = invoke_method(request, bootstrap_server)
    with pytest.raises(ValueError):
        response = await response


@pytest_asyncio.fixture
async def bootstrap_stub():
    bootstrap = Bootstrap(0)
    await bootstrap.start()
    async with grpc.aio.insecure_channel(f"localhost:{bootstrap._port}") as channel:
        stub = BootstrapStub(channel)
        yield stub

    await bootstrap.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("num_of_share_servers", [3])
@pytest.mark.parametrize("key_pairs", [4], indirect=True)
async def test_generate_shares_works_without_mocks(
    bootstrap_stub, num_of_share_servers, key_pairs
):
    # Arrange
    privs, pubs = key_pairs
    priv_user = privs[-1]  # last key is user's key

    # Act
    response = await bootstrap_stub.GenerateShares(
        GenerateSharesRequest(
            threshold=num_of_share_servers + 1,  # +1 for the user
            num_of_shares=num_of_share_servers + 1,
            public_keys=pubs,
        )
    )

    # Assert
    assert len(response.encrypted_shares) == num_of_share_servers + 1
    Key.model_validate_json(decrypt(response.encrypted_key, priv_user))


@pytest.mark.asyncio
@pytest.mark.parametrize("num_of_share_servers", [3])
@pytest.mark.parametrize("key_pairs", [2], indirect=True)
async def test_generate_shares_raises_invalid_arg_when_different_number_of_shares_and_keys(
    bootstrap_stub, num_of_share_servers, key_pairs
):
    # Arrange
    privs, pubs = key_pairs

    # Act
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await bootstrap_stub.GenerateShares(
            GenerateSharesRequest(
                threshold=num_of_share_servers + 1,  # +1 for the user
                num_of_shares=num_of_share_servers + 1,
                public_keys=pubs,
            )
        )
        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT
