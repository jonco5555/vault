import asyncio
from vault.user.user import User
from vault.common.constants import (
    MANAGER_SERVER_DNS_ADDRESS,
    MANAGER_SERVER_PORT,
    MANAGER_NUM_SHARE_SERVERS,
)


async def simulate_client():
    user = User(
        user_id="alice",
        server_ip=MANAGER_SERVER_DNS_ADDRESS,
        server_port=MANAGER_SERVER_PORT,
        threshold=MANAGER_NUM_SHARE_SERVERS + 1,
        num_of_share_servers=MANAGER_NUM_SHARE_SERVERS,
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

    print(f"{retrieved_secret=}, {secret=}", flush=True)
    if retrieved_secret != secret:
        raise RuntimeError(f"Expected {secret=}, got {retrieved_secret=}")


if __name__ == "__main__":
    asyncio.run(simulate_client())
