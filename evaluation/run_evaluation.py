from typing import Optional
import argparse
import matplotlib.pyplot as plt
import subprocess
import os
import json

from time import sleep


def make_plot(
    num_application_calls,
    latencies,
    throughputs,
    latencies_label,
    throughputs_label,
    x_label,
    title,
    save_name: Optional[str] = None,
):
    _, ax1 = plt.subplots(figsize=(8, 5))
    color = "tab:blue"
    ax1.set_xlabel(x_label)
    ax1.set_ylabel(throughputs_label, color=color)
    ax1.plot(
        num_application_calls, throughputs, color=color, marker="o", label="Throughput"
    )
    ax1.tick_params(axis="y", labelcolor=color)

    ax2 = ax1.twinx()
    color = "tab:red"
    ax2.set_ylabel(latencies_label, color=color)
    ax2.plot(num_application_calls, latencies, color=color, marker="x", label="Latency")
    ax2.tick_params(axis="y", labelcolor=color)

    ax1.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
    ax2.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)

    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")

    plt.title(title)

    plt.tight_layout()
    if save_name:
        plt.savefig(f"./evaluation/figures/{save_name}", dpi=300, bbox_inches="tight")
    plt.show()


def run_evaluation(num_share_servers):
    # 'NUM_SHARE_SERVERS_ENV' is parameter for 'docker-compose up'``
    env = os.environ.copy()
    env["NUM_SHARE_SERVERS_ENV"] = str(num_share_servers)

    subprocess.run(["docker-compose", "build"])
    subprocess.Popen(["docker-compose", "up", "-d"], env=env)
    sleep(15)
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-it",
            "--network",
            "vault-net",
            "--name",
            "vault-user",
            "vault:latest",
            "vault",
            "evaluation-user",
            "--user-id",
            "alice",
            "--server-ip",
            "vault-manager",
            "--server-port",
            "5000",
            "--threshold",
            f"{num_share_servers + 1}",
            "--num-of-total-shares",
            f"{num_share_servers + 1}",
            "--ca-cert-path",
            "/app/certs/ca.crt",
        ],
        # capture output to retrieve test results
        capture_output=True,
        text=True,
    )
    output_str = result.stdout.strip()
    print(f"raw test results: {output_str}")
    loaded_lists = json.loads(output_str)

    subprocess.run(["docker-compose", "down"])

    iterations = loaded_lists["iterations"]
    storage_latencies = loaded_lists["storage_latencies"]
    storage_throughputs = loaded_lists["storage_throughputs"]
    retrieval_latencies = loaded_lists["retrieval_latencies"]
    retrieval_throughputs = loaded_lists["retrieval_throughputs"]
    return (
        iterations,
        storage_latencies,
        storage_throughputs,
        retrieval_latencies,
        retrieval_throughputs,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run latency-throughput evaluation on a vault system"
    )
    parser.add_argument("--num-share-servers", type=int, required=True)
    args = parser.parse_args()

    (
        iterations,
        storage_latencies,
        storage_throughputs,
        retrieval_latencies,
        retrieval_throughputs,
    ) = run_evaluation(num_share_servers=args.num_share_servers)

    make_plot(
        num_application_calls=iterations,
        latencies=storage_latencies,
        throughputs=storage_throughputs,
        latencies_label="Storage Latency (s/req)",
        throughputs_label="Storage Throughput (req/s)",
        x_label="Storage Requests (req)",
        title=f"Storage Latency and Throughput vs Storage Requests ({args.num_share_servers} Share servers)",
        save_name=f"Storage_Latency_Throughput_{args.num_share_servers}_Share_servers",
    )

    make_plot(
        num_application_calls=iterations,
        latencies=retrieval_latencies,
        throughputs=retrieval_throughputs,
        latencies_label="Retrieval Latency (s/req)",
        throughputs_label="Retrieval Throughput (req/s)",
        x_label="Retrieval Requests (req)",
        title=f"Retrieval Latency and Throughput vs Retrieval Requests ({args.num_share_servers} Share servers)",
        save_name=f"Retrieval_Latency_Throughput_{args.num_share_servers}_Share_servers",
    )
