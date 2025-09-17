import pytest

from vault.crypto.authentication import (
    srp_registration_client_generate_data,
    srp_authentication_server_step_one,
    srp_authentication_client_step_two,
    srp_authentication_server_step_three,
)


@pytest.mark.asyncio
async def test_happy_flow():
    #### REGISTRATION
    # 1) user picks cradentials
    USERNAME = "alice"
    PASSWORD = "password123"
    # 2) user generates data
    username, password_verifier, salt = srp_registration_client_generate_data(
        username=USERNAME,
        password=PASSWORD,
    )
    print(f"{username=}, {password_verifier=}, {salt=}")
    # 3) user sends username, password_verifier, salt to the server
    # 4) server confirms and stores in db

    #### AUTHENTICATION
    # 1) ==> user sends to server a username

    # pre-2) server retrieves from db the `password_verifier` and `salt`
    # 2) server generate server public.
    server_public, server_private = srp_authentication_server_step_one(
        username=username,
        password_verifier=password_verifier,
    )
    # 3) <== server sends to user a public and salt

    # 4) user receive server public and salt and process them.
    client_public, client_session_key, client_session_key_proof = (
        srp_authentication_client_step_two(
            username=USERNAME,
            password=PASSWORD,
            server_public_key=server_public,
            salt=salt,
        )
    )

    server_session_key = srp_authentication_server_step_three(
        username=USERNAME,
        password_verifier=password_verifier,
        salt=salt,
        server_private=server_private,
        client_public=client_public,
        client_session_key_proof=client_session_key_proof,
    )

    # now we have an agreed session key based on a password.
    assert server_session_key == client_session_key


@pytest.mark.asyncio
async def test_unhappy_flow():
    #### REGISTRATION
    # 1) user picks cradentials
    USERNAME = "alice"
    PASSWORD = "password123"
    BAD_PASSWORD = "BAD_PASSWORD"
    # 2) user generates data
    username, password_verifier, salt = srp_registration_client_generate_data(
        username=USERNAME,
        password=PASSWORD,
    )
    print(f"{username=}, {password_verifier=}, {salt=}")
    # 3) user sends username, password_verifier, salt to the server
    # 4) server confirms and stores in db

    #### AUTHENTICATION
    # 1) ==> user sends to server a username

    # pre-2) server retrieves from db the `password_verifier` and `salt`
    # 2) server generate server public.
    server_public, server_private = srp_authentication_server_step_one(
        username=username,
        password_verifier=password_verifier,
    )
    # 3) <== server sends to user a public and salt

    # 4) user receive server public and salt and process them.
    client_public, _, client_session_key_proof = srp_authentication_client_step_two(
        username=USERNAME,
        password=BAD_PASSWORD,
        server_public_key=server_public,
        salt=salt,
    )

    try:
        srp_authentication_server_step_three(
            username=USERNAME,
            password_verifier=password_verifier,
            salt=salt,
            server_private=server_private,
            client_public=client_public,
            client_session_key_proof=client_session_key_proof,
        )
        assert False
    except Exception:
        pass
