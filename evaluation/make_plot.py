import matplotlib.pyplot as plt
import tempfile
import subprocess
import os
import pickle

from time import sleep


def make_plot(
    num_application_calls,
    latencies,
    throughputs,
    latencies_label,
    throughputs_label,
    x_label,
    title,
):
    # Create figure and primary axis
    fig, ax1 = plt.subplots(figsize=(8, 5))

    # Plot throughput on left y-axis
    color = "tab:blue"
    ax1.set_xlabel(x_label)
    ax1.set_ylabel(throughputs_label, color=color)
    ax1.plot(
        num_application_calls, throughputs, color=color, marker="o", label="Throughput"
    )
    ax1.tick_params(axis="y", labelcolor=color)

    # Create secondary y-axis for latency
    ax2 = ax1.twinx()
    color = "tab:red"
    ax2.set_ylabel(latencies_label, color=color)
    ax2.plot(num_application_calls, latencies, color=color, marker="x", label="Latency")
    ax2.tick_params(axis="y", labelcolor=color)

    # Add grid to both axes
    ax1.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
    ax2.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)

    # Optional: add legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper left")

    # Add a title
    plt.title(title)

    # Layout and show
    plt.tight_layout()
    plt.show()


def run_evaluation():
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Temporary dir created: {temp_dir}")

        subprocess.run(["docker-compose", "build"])
        subprocess.Popen(["docker-compose", "up"])
        sleep(15)
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-d",
                "-v",
                f"{temp_dir}:/data",
                "--network",
                "vault-net",
                "--name",
                "vault-user",
                "vault:latest",
                "vault",
                "evaluation_user",
                "--user-id",
                "alice",
                "--server-ip",
                "vault-manager",
                "--server-port",
                "5000",
                "--threshold",
                "3",
                "--num-of-total-shares",
                "3",
                "--ca-cert-path",
                "/app/certs/ca.crt",
            ]
        )
        sleep(60)
        subprocess.run(["docker-compose", "down"])

        with open(os.path.join(temp_dir, "lists.pkl")) as f:
            loaded_lists = pickle.load(f)
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
    (
        iterations,
        storage_latencies,
        storage_throughputs,
        retrieval_latencies,
        retrieval_throughputs,
    ) = run_evaluation()
    # iterations = [1, 2, 4, 6, 8, 10, 15, 20, 30, 40, 50, 70, 100]
    # storage_latencies = [
    #     0.1326596736907959,
    #     0.09514331817626953,
    #     0.09333491325378418,
    #     0.11376321315765381,
    #     0.09831899404525757,
    #     0.09919030666351318,
    # ]
    # storage_throughputs = [
    #     9.920326207015627,
    #     12.446578403457726,
    #     13.169570261661086,
    #     13.998168866955837,
    #     14.03204319709343,
    #     14.216586917417242,
    # ]
    # retrieval_latencies = [
    #     0.12810921669006348,
    #     0.1293184757232666,
    #     0.12521737813949585,
    #     0.13470284144083658,
    #     0.12433725595474243,
    #     0.13207013607025148,
    # ]
    # retrieval_throughputs = [
    #     7.825997070594931,
    #     10.115019256694023,
    #     9.700739760783312,
    #     8.790457923675545,
    #     11.224691997333192,
    #     10.817277091008126,
    # ]

    make_plot(
        num_application_calls=iterations,
        latencies=storage_latencies,
        throughputs=storage_throughputs,
        latencies_label="Storage Latency (s/req)",
        throughputs_label="Storage Throughput (req/s)",
        x_label="Storage Requests (req)",
        title="Storage Latency and Throughput vs Storage Requests",
    )

    make_plot(
        num_application_calls=iterations,
        latencies=retrieval_latencies,
        throughputs=retrieval_throughputs,
        latencies_label="Retrieval Latency (s/req)",
        throughputs_label="Retrieval Throughput (req/s)",
        x_label="Retrieval Requests (req)",
        title="Retrieval Latency and Throughput vs Retrieval Requests",
    )
