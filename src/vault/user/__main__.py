import asyncio

from vault.common.constants import (
    MANAGER_NUM_SHARE_SERVERS,
    MANAGER_SERVER_DNS_ADDRESS,
    MANAGER_SERVER_PORT,
)
from vault.user.user import User


async def simulate_client():
    user = User(
        user_id="alice",
        server_ip=MANAGER_SERVER_DNS_ADDRESS,
        server_port=MANAGER_SERVER_PORT,
        threshold=MANAGER_NUM_SHARE_SERVERS + 1,
        num_of_total_shares=MANAGER_NUM_SHARE_SERVERS + 1,
    )

    print("=== Simulating Client Operations ===", flush=True)

    # Step 1: Registration
    print("-> Registration phase", flush=True)
    await user.register()

    # Step 2: Store secret

    print("-> Storage phase", flush=True)
    secret = "my super secret"
    secret_id = "my super secret id"
    await user.store_secret(secret, secret_id)

    # Step 3: Retrieve secret
    print("-> Retrieval phase", flush=True)
    retrieved_secret = await user.retrieve_secret(secret_id)

    if retrieved_secret != secret:
        raise RuntimeError(f"Expected {secret=}, got {retrieved_secret=}")

    print("-> Storage phase2", flush=True)
    secret2 = "my super secret2"
    secret_id2 = "my super secret id2"
    await user.store_secret(secret2, secret_id2)

    # Step 3: Retrieve secret
    print("-> Retrieval phase2", flush=True)
    retrieved_secret2 = await user.retrieve_secret(secret_id2)

    if retrieved_secret2 != secret2:
        raise RuntimeError(f"Expected {secret2=}, got {retrieved_secret2=}")

    print("VICTORYYYYYY", flush=True)


if __name__ == "__main__":
    asyncio.run(simulate_client())
