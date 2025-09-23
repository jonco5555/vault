from vault.user.user import User


async def main(
    user_id: str,
    server_ip: str,
    server_port: int,
    threshold: int,
    num_of_total_shares: int,
    ca_cert_path: str,
):
    user_obj = User(
        user_id=user_id,
        server_ip=server_ip,
        server_port=server_port,
        threshold=threshold,
        num_of_total_shares=num_of_total_shares,
        ca_cert_path=ca_cert_path,
    )
    print("=== Simulating Client Operations ===", flush=True)
    print("-> Registration phase", flush=True)
    await user_obj.register()
    print("-> Storage phase", flush=True)
    secret = "my super secret"
    secret_id = "my super secret id"
    await user_obj.store_secret(secret, secret_id)
    print("-> Retrieval phase", flush=True)
    retrieved_secret = await user_obj.retrieve_secret(secret_id)
    if retrieved_secret != secret:
        raise RuntimeError(f"Expected {secret=}, got {retrieved_secret=}")
    print("-> Storage phase2", flush=True)
    secret2 = "my super secret2"
    secret_id2 = "my super secret id2"
    await user_obj.store_secret(secret2, secret_id2)
    print("-> Retrieval phase2", flush=True)
    retrieved_secret2 = await user_obj.retrieve_secret(secret_id2)
    if retrieved_secret2 != secret2:
        raise RuntimeError(f"Expected {secret2=}, got {retrieved_secret2=}")
    print("VICTORYYYYYY", flush=True)
