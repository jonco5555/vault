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
    save_name,
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
    plt.savefig(f"./evaluation/figures/{save_name}", dpi=300, bbox_inches="tight")
    plt.show()


def run_evaluation():
    tmpdir = tempfile.TemporaryDirectory()
    temp_dir = tmpdir.name
    print(f"Temporary dir created: {temp_dir}")

    subprocess.run(["docker-compose", "build"])
    subprocess.Popen(["docker-compose", "up", "-d"])
    sleep(15)
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-it",
            "--network",
            "vault-net",
            "--name",
            "vault-user",
            "-v",
            f"{temp_dir}:/vol",
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
            "3",
            "--num-of-total-shares",
            "3",
            "--ca-cert-path",
            "/app/certs/ca.crt",
        ]
    )
    subprocess.run(["docker-compose", "down"])

    with open(os.path.join(temp_dir, "lists.pkl"), "rb") as f:
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
    # (
    #     iterations,
    #     storage_latencies,
    #     storage_throughputs,
    #     retrieval_latencies,
    #     retrieval_throughputs,
    # ) = run_evaluation()
    iterations = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    # ZERO SHARE SERVERS
    # num_share_servers=0
    # storage_latencies=[0.10344233512878417, 0.10239672660827637, 0.0874090313911438, 0.09212887287139893, 0.0938804030418396, 0.08751969814300536, 0.09135931730270386, 0.08795297145843506, 0.08732304573059083, 0.09266062047746447, 0.09989157676696778]
    # storage_throughputs=[12.973018448559246, 13.362290297494896, 15.062595559657508, 15.088146303402285, 14.622280767533917, 15.359914875471759, 14.117917920725704, 14.880683137963555, 14.032023245837765, 14.503087416895967, 13.46760402616854]
    # retrieval_latencies=[0.10175595283508301, 0.10812406539916992, 0.10844616889953614, 0.1074806292851766, 0.10241873264312744, 0.10159997940063477, 0.10215119123458863, 0.10206617968423026, 0.10283526480197906, 0.11762855847676595, 0.11722919464111328]
    # retrieval_throughputs=[12.079081434294157, 11.803582805953482, 12.56324674986244, 12.458459465020129, 12.325908789890079, 12.70465768548213, 12.249782830849886, 12.245156813438717, 12.33830797474875, 12.36730696624749, 10.278662929628121]

    # TWO SHARE SERVERS:
    # num_share_servers=2
    # storage_latencies=[0.08656125068664551, 0.09482369422912598, 0.08774614334106445, 0.08816237449645996, 0.08779698610305786, 0.09167262077331544, 0.09133858283360799, 0.10409442697252547, 0.09769537150859833, 0.08982275591956244, 0.09177240371704101]
    # storage_throughputs=[13.914908242575605, 15.001441378802218, 13.315629126605343, 14.831987054601143, 14.910149222215152, 12.788002661809408, 11.86101504152751, 13.540097467985142, 12.596504257919507, 14.284187272533256, 13.86432012371604]
    # retrieval_latencies=[0.12269158363342285, 0.11517317295074463, 0.11610478162765503, 0.11586401462554932, 0.11552339792251587, 0.12600137233734132, 0.11910789012908936, 0.14550838470458985, 0.14198515117168425, 0.12097434467739529, 0.119407377243042]
    # retrieval_throughputs=[11.374365221371843, 11.729126590161615, 11.934332920138667, 10.784555085780795, 11.487670855249748, 9.496872078434764, 10.548242514534847, 10.862319772203053, 10.200858625562505, 11.545105884093715, 10.848804670721128]

    # FOUR SHARE SERVERS:
    # num_share_servers=4
    # storage_latencies=[0.09959678649902344, 0.09958405494689941, 0.09241591691970825, 0.08990127245585124, 0.09393458366394043, 0.09395970344543457, 0.09466457764307658, 0.09747734410422189, 0.10949640274047852, 0.09154994752671984, 0.10233944654464722]
    # storage_throughputs=[11.829889826975721, 11.779793921909615, 14.968305287043915, 14.612914734213343, 12.604763302542205, 13.929449297922284, 12.427553292161694, 13.027942418520471, 12.227755021244695, 14.042717031971817, 13.843890977589409]
    # retrieval_latencies=[0.20653853416442872, 0.136871337890625, 0.13047205209732055, 0.1363866170247396, 0.13548480868339538, 0.15640661239624024, 0.14210898478825887, 0.14394753319876535, 0.144480362534523, 0.1334781461291843, 0.16337846517562865]
    # retrieval_throughputs=[7.79785208357115, 8.620253167158516, 10.925301257542834, 10.776574852884123, 9.456431561697983, 9.885979595157702, 9.173975532151536, 8.774172463318157, 8.317722703575589, 10.090098373868063, 9.386424539231907]

    # EIGHT SHARE SERVERS:
    num_share_servers = 8
    storage_latencies = [
        0.09295716285705566,
        0.08777565956115722,
        0.09878194332122803,
        0.08858563105265299,
        0.09348608255386352,
        0.09104504585266113,
        0.09506626923878987,
        0.09516617230006627,
        0.09608559608459473,
        0.08875725799136691,
        0.10219867944717408,
    ]
    storage_throughputs = [
        12.120304228217398,
        14.336873653238245,
        13.349726993362223,
        13.719971066065455,
        13.44567921764898,
        14.354406863386957,
        13.790340425312724,
        12.807511660084888,
        13.481510451330683,
        14.154075210937465,
        12.755575423156223,
    ]
    retrieval_latencies = [
        0.1722555637359619,
        0.15796144008636476,
        0.1670721650123596,
        0.167867644627889,
        0.1717471718788147,
        0.2005323839187622,
        0.18219200372695923,
        0.1733016014099121,
        0.17200062274932862,
        0.1764021529091729,
        0.1987622618675232,
    ]
    retrieval_throughputs = [
        7.9270147597347425,
        8.667330273468133,
        7.78009704568797,
        8.136041408944884,
        7.184903511675414,
        8.386898414627163,
        8.21643560459869,
        8.265774342303706,
        8.75538349085332,
        8.304515552788514,
        8.013353245155646,
    ]

    make_plot(
        num_application_calls=iterations,
        latencies=storage_latencies,
        throughputs=storage_throughputs,
        latencies_label="Storage Latency (s/req)",
        throughputs_label="Storage Throughput (req/s)",
        x_label="Storage Requests (req)",
        title=f"Storage Latency and Throughput vs Storage Requests ({num_share_servers} Share servers)",
        save_name=f"Storage_Latency_Throughput_{num_share_servers}_Share_servers",
    )

    make_plot(
        num_application_calls=iterations,
        latencies=retrieval_latencies,
        throughputs=retrieval_throughputs,
        latencies_label="Retrieval Latency (s/req)",
        throughputs_label="Retrieval Throughput (req/s)",
        x_label="Retrieval Requests (req)",
        title=f"Retrieval Latency and Throughput vs Retrieval Requests ({num_share_servers} Share servers)",
        save_name=f"Retrieval_Latency_Throughput_{num_share_servers}_Share_servers",
    )
