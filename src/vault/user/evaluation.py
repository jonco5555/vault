import asyncio
import uuid
import time
import json

from typing import Dict

from vault.user.user import User


# To run several times, each time on different number of share servers
async def benchmark_parallel_main(
    user_obj: User,
    password: str,
    iterations: int,
):
    async def store_single_secret(
        user_obj: User,
    ):
        curr_secret: str = str(uuid.uuid4())
        curr_secret_id: str = str(uuid.uuid4())
        storage_start_time = time.time()
        await user_obj.store_secret(
            password=password,
            secret=curr_secret,
            secret_id=curr_secret_id,
        )
        storage_end_time = time.time()
        return curr_secret_id, storage_end_time - storage_start_time

    async def retrieve_single_secret(user_obj: User, curr_secret_id: str):
        storage_start_time = time.time()
        curr_secret = await user_obj.retrieve_secret(
            password=password,
            secret_id=curr_secret_id,
        )
        storage_end_time = time.time()
        return curr_secret_id, curr_secret, storage_end_time - storage_start_time

    storage_start_time = time.time()
    tasks = [
        asyncio.create_task(store_single_secret(user_obj)) for i in range(iterations)
    ]
    results = await asyncio.gather(*tasks)
    storage_stop_time = time.time()
    storage_total_time = storage_stop_time - storage_start_time
    secret_ids_to_storage_time = {item[0]: item[1] for item in results}
    single_storage_avg_time = sum(secret_ids_to_storage_time.values()) / len(
        secret_ids_to_storage_time.values()
    )

    retrieval_start_time = time.time()
    tasks = [
        asyncio.create_task(retrieve_single_secret(user_obj, curr_secret_id))
        for curr_secret_id in secret_ids_to_storage_time.keys()
    ]
    results = await asyncio.gather(*tasks)
    retrieval_stop_time = time.time()
    retrieval_total_time = retrieval_stop_time - retrieval_start_time
    secret_ids_to_retrieval_time = {item[0]: item[2] for item in results}
    single_retrieval_avg_time = sum(secret_ids_to_retrieval_time.values()) / len(
        secret_ids_to_retrieval_time.values()
    )

    storage_throughput = iterations / storage_total_time
    retrieval_throughput = iterations / retrieval_total_time
    storage_latency = single_storage_avg_time
    retrieval_latency = single_retrieval_avg_time
    return storage_throughput, storage_latency, retrieval_throughput, retrieval_latency


async def benchmark_sequential_main(
    user_obj: User,
    password: str,
    iterations: int,
):
    secrets: Dict[str, str] = {}

    # print("Storing secrets...", flush=True)
    storage_start_time = time.time()
    for i in range(iterations):
        curr_secret: str = str(uuid.uuid4())
        curr_secret_id: str = str(uuid.uuid4())
        await user_obj.store_secret(
            password=password,
            secret=curr_secret,
            secret_id=curr_secret_id,
        )
        secrets[curr_secret_id] = curr_secret
    storage_end_time = time.time()
    storage_total_time = storage_end_time - storage_start_time
    storage_avg_time = storage_total_time / iterations

    retrieval_start_time = time.time()
    for curr_secret_id, curr_secret in secrets.items():
        retrieved_secret = await user_obj.retrieve_secret(
            password=password,
            secret_id=curr_secret_id,
        )
        if retrieved_secret != curr_secret:
            raise RuntimeError(f"Expected {retrieved_secret=}, got {curr_secret=}")
    retrieval_end_time = time.time()
    retrieval_total_time = retrieval_end_time - retrieval_start_time
    retrieval_avg_time = retrieval_total_time / iterations

    storage_latency = storage_avg_time
    retrieval_latency = retrieval_avg_time
    return storage_latency, retrieval_latency


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
    password = "mypass"

    await user_obj.register(password=password)

    iterations = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        10,
        12,
        15,
        18,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100,
    ]
    storage_latencies = []
    storage_throughputs = []
    retrieval_latencies = []
    retrieval_throughputs = []
    for iter in iterations:
        (
            storage_throughput,
            storage_latency,
            retrieval_throughput,
            retrieval_latency,
        ) = await benchmark_parallel_main(
            user_obj=user_obj,
            password=password,
            iterations=iter,
        )
        storage_latencies.append(storage_latency)
        storage_throughputs.append(storage_throughput)
        retrieval_latencies.append(retrieval_latency)
        retrieval_throughputs.append(retrieval_throughput)
    to_print = {
        "iterations": iterations,
        "storage_latencies": storage_latencies,
        "storage_throughputs": storage_throughputs,
        "retrieval_latencies": retrieval_latencies,
        "retrieval_throughputs": retrieval_throughputs,
    }

    # This is not ideal, but currently the way for us to retrieve the test results is
    # through the stdout of the evaluation-user docker. so we print the results, and
    # catch them in the test script.
    print(json.dumps(to_print))

    # print("--------------BENCHMARK-SUMMERY--------------")
    # print(f"{storage_latencies=}")
    # print(f"{storage_throughputs=}")
    # print(f"{retrieval_latencies=}")
    # print(f"{retrieval_throughputs=}")
