from typing import Tuple
from srptools import SRPContext, SRPClientSession, SRPServerSession


def srp_registration_client_generate_data(
    username: str, password: str
) -> Tuple[str, str, str]:
    context = SRPContext(username, password)
    username, password_verifier, salt = context.get_user_data_triplet()
    return username, password_verifier, salt


# Step one, to be run in the server.
# Generates session public key in server.
# Returns the server's session public key.
def srp_authentication_server_step_one(
    username: str, password_verifier: str
) -> Tuple[str, str]:
    context = SRPContext(username)
    server_session = SRPServerSession(context, password_verifier.encode())
    return server_session.public, server_session.private


# Step two, to be run in the client.
# Generates session keys in client and processes server's key.
# Returns the client's session public key, the shared session secret key,
# and the client's session session key proof.
def srp_authentication_client_step_two(
    username: str, password: str, server_public_key: str, salt: str
):
    # 4) user receive server public and salt and process them.
    client_session = SRPClientSession(SRPContext(username, password))
    client_session.process(server_public_key, salt)
    # 5) user Generate client public and session key.
    client_public = client_session.public
    client_session_key = client_session.key
    client_session_key_proof = client_session.key_proof
    return client_public, client_session_key, client_session_key_proof.decode()


# Step three, to be run in the server.
# Uses a private key to restore the previous session.
# Generates session keys in server and verifies the authentication.
# returns the shared secret session key. session Raises on error.
def srp_authentication_server_step_three(
    username: str,
    password_verifier: str,
    salt: str,
    server_private: str,
    client_public: str,
    client_session_key_proof: str,
) -> str:
    context = SRPContext(username)
    server_session = SRPServerSession(
        context, password_verifier=password_verifier, private=server_private
    )
    server_session.process(client_public, salt)
    if not server_session.verify_proof(client_session_key_proof.encode()):
        raise RuntimeError(f"verify_proof failed for {username}")
    return server_session.key
    # server_session_key = server_session.key
