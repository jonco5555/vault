import pytest
from srptools import SRPContext, SRPClientSession, SRPServerSession


@pytest.mark.asyncio
async def test_happy_flow():
    #### REGISTRATION
    # 1) user picks cradentials
    USERNAME = "alice"
    PASSWORD = "password123"
    # 2) user generates data
    context = SRPContext(USERNAME, PASSWORD)
    username, password_verifier, salt = context.get_user_data_triplet()
    print(f"{username=}, {password_verifier=}, {salt=}")
    # 3) user sends username, password_verifier, salt to the server
    # 4) server confirms and stores in db

    #### AUTHENTICATION
    # 1) ==> user sends to server a username

    # pre-2) server retrieves from db the `password_verifier` and `salt`
    # 2) server generate server public.
    server_session = SRPServerSession(SRPContext(username), password_verifier)
    server_public = server_session.public
    # 3) <== server sends to user a public and salt

    # 4) user receive server public and salt and process them.
    client_session = SRPClientSession(SRPContext(username, "password123"))
    client_session.process(server_public, salt)
    # 5) user Generate client public and session key.
    client_public = client_session.public
    client_session_key = client_session.key
    client_session_key_proof = client_session.key_proof

    # 6) ==> user send `client_public` and `client_session_key_proof` to server
    # 7) server Process client public key generates a session key
    server_session.process(client_public, salt)
    assert server_session.verify_proof(client_session_key_proof)
    server_session_key = server_session.key

    # now we have an agreed session key based on a password.
    assert server_session_key == client_session_key


@pytest.mark.asyncio
async def test_unhappy_flow():
    #### REGISTRATION
    # 1) user picks cradentials
    USERNAME = "alice"
    PASSWORD = "password123"
    # 2) user generates data
    context = SRPContext(USERNAME, PASSWORD)
    username, password_verifier, salt = context.get_user_data_triplet()
    print(f"{username=}, {password_verifier=}, {salt=}")
    # 3) user sends username, password_verifier, salt to the server
    # 4) server confirms and stores in db

    #### AUTHENTICATION
    # 1) ==> user sends to server a username

    # pre-2) server retrieves from db the `password_verifier` and `salt`
    # 2) server generate server public.
    server_session = SRPServerSession(SRPContext(username), password_verifier)
    server_public = server_session.public
    # 3) <== server sends to user a public and salt

    # 4) user receive server public and salt and process them.
    client_session = SRPClientSession(SRPContext(username, "bad_pass"))
    client_session.process(server_public, salt)
    # 5) user Generate client public and session key.
    client_public = client_session.public
    client_session_key = client_session.key
    client_session_key_proof = client_session.key_proof

    # 6) ==> user send `client_public` and `client_session_key_proof` to server
    # 7) server Process client public key generates a session key
    server_session.process(client_public, salt)
    assert not server_session.verify_proof(client_session_key_proof)
    server_session_key = server_session.key

    # now we have an agreed session key based on a password.
    assert server_session_key != client_session_key
