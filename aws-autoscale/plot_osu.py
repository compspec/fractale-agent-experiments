import argparse
import json
import logging
import re
import sys
import os
import glob
from io import StringIO
import pandas

from metricsoperator.metrics.network.osu_benchmark import parse_multi_section

here = os.path.abspath(os.path.dirname(__file__))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from matplotlib.font_manager import FontProperties

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def get_log_from_json(json_file_path: str) -> str:
    """
    Safely opens, parses a JSON file, and navigates its structure
    to extract the pod log content.

    Args:
        json_file_path (str): The path to the JSON result file.

    Returns:
        The log content as a string, or None if not found.
    """
    logging.info(f"Parsing JSON file: {json_file_path}")
    with open(json_file_path, "r") as f:
        data = json.load(f)
    for log in data["steps"][1]["metadata"]["assets"]["logs"]:
        yield log["item"]


def find_benchmark_output(log_data: str, benchmark_name: str) -> str:
    """
    Uses a regular expression to find the output table for a specific OSU benchmark
    *within the unstructured log string*. This is the correct use of regex.

    Args:
        log_data (str): The raw log content from the pod.
        benchmark_name (str): The name of the benchmark (e.g., "osu_allreduce").

    Returns:
        A string containing just the benchmark's output table, or None if not found.
    """
    if "# OSU MPI" not in log_data:
        return
    if "# OSU MPI Allreduce Latency Test v7.3" in log_data:
        start = log_data.index("# OSU MPI Allreduce Latency Test v7.3") - 1
        log_data = log_data[start:]
        log_data = [x for x in log_data.split("\n") if "broker.info" not in x and x]
        return log_data

    elif "# OSU MPI Latency Test v7.3" in log_data:
        start = log_data.index("# OSU MPI Latency Test v7.3") - 1
        log_data = log_data[start:]
        log_data = [x for x in log_data.split("\n") if "broker.info" not in x and x]
        return log_data


def parse_benchmark_matrix(matrix_str: str) -> pd.DataFrame:
    """
    Parses the raw text of benchmark results into a Pandas DataFrame.

    Args:
        matrix_str (str): The string containing the size and latency data.

    Returns:
        A Pandas DataFrame with 'Size' and 'Latency' columns.
    """
    data = StringIO(matrix_str)
    df = pd.read_csv(
        data, delim_whitespace=True, header=None, names=["Size", "Latency"]
    )
    df["Size"] = pd.to_numeric(df["Size"])
    df["Latency"] = pd.to_numeric(df["Latency"])
    logging.info(
        f"Successfully parsed the matrix into a DataFrame with {len(df)} rows."
    )
    return df


def get_osu_title(slug):
    if slug == "osu_bw":
        title = "OSU Bandwidth"
    elif slug == "osu_latency":
        title = "OSU Latency"
    elif slug == "osu_allreduce":
        title = "OSU AllReduce"
    return title


def get_columns(command):
    """
    Get columns for data frame depending on command
    """
    # Size       Avg Latency(us)
    if "allreduce" in command:
        return ["size", "avg_latency_us"]
    # Size          Latency (us)
    elif "latency" in command:
        return ["size", "latency_us"]
    # Size      Bandwidth (MB/s)
    return ["size", "bandwidth_mb_s"]


def plot_results(dataframes: dict, output_file: str):
    """
    Plot result images to file
    """
    dfs = {}
    idxs = {}
    lookup = {}

    for analysis, results in dataframes.items():
        for entry in results:
            # The source of truth is the command
            command = f"osu_{analysis}"
            print(command)

            title = command
            columns = get_columns(title)
            if title not in dfs:
                idxs[title] = 0
                dfs[title] = pandas.DataFrame(columns=columns)
                lookup[title] = {"x": columns[0], "y": columns[1]}

            for datum in entry["matrix"]:
                dfs[title].loc[idxs[title], :] = datum
                idxs[title] += 1

    fig = plt.figure(figsize=(10, 3))
    gs = plt.GridSpec(1, 2, width_ratios=[2, 2])
    axes = []
    axes.append(fig.add_subplot(gs[0, 0]))
    axes.append(fig.add_subplot(gs[0, 1]))
    i = 0

    # Save each completed data frame to file and plot!
    for slug, subset in dfs.items():
        print(subset)

        # Separate x and y - latency (y) is a function of size (x)
        xlabel = "Message size in bytes"
        x = lookup[slug]["x"]
        y = lookup[slug]["y"]

        # for sty in plt.style.available:
        sns.lineplot(
            data=subset,
            ax=axes[i],
            x=x,
            y=y,
            markers=True,
            dashes=True,
            errorbar=("ci", 95),
        )

        axes[i].set_title(get_osu_title(slug), fontsize=12)
        axes[i].set_xticklabels(axes[i].get_xmajorticklabels(), fontsize=10)
        axes[i].set_yticklabels(axes[i].get_yticks(), fontsize=12)
        y_label = y.replace("_", " ")
        axes[i].set_xlabel("", fontsize=12)
        axes[i].set_ylabel(y_label + " (logscale)", fontsize=12)
        axes[i].set_xscale("log")
        axes[i].set_yscale("log")
        i += 1

    font_prop = FontProperties(size=14)
    fig.text(
        0.50,
        0.01,
        xlabel + " (logscale)",
        horizontalalignment="center",
        wrap=True,
        fontproperties=font_prop,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.subplots_adjust(bottom=0.15)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.clf()
    plt.close()


def process_benchmark_dir(results_dir: str, benchmark_name_map: dict) -> dict:
    """
    Discover and parse result files for a given set of benchmarks.
    """
    dataframes = {}
    for short_name, (dir_name, log_name) in benchmark_name_map.items():
        subdir_path = os.path.join(results_dir, dir_name)
        if not os.path.isdir(subdir_path):
            logging.warning(f"Directory not found: {subdir_path}")
            continue

        json_files = glob.glob(os.path.join(subdir_path, "result*.json"))
        if not json_files:
            logging.warning(f"No result*.json file found in {subdir_path}")
            continue

        # 1. Get log string by parsing JSON correctly
        for json_file in json_files:
            for log_content in get_log_from_json(json_file):

                # 2. Find benchmark table within the log string using regex
                matrix_str = find_benchmark_output(log_content, log_name)
                if not matrix_str:
                    continue

                # 3. Parse the table into a DataFrame
                if short_name not in dataframes:
                    dataframes[short_name] = []
                dataframes[short_name].append(parse_multi_section(matrix_str))
    return dataframes


def main():
    """
    Main entrypoint for the script.
    """
    parser = argparse.ArgumentParser(
        description="Parse and plot OSU benchmark results from a results directory."
    )
    parser.add_argument(
        "--results_dir",
        help="Path to the base results directory containing benchmark subdirectories.",
        default=os.path.join(here, "results"),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.path.join(here, "data", "img", "osu_benchmarks.svg"),
        help="Path to save the output plot image (default: osu_benchmarks.svg)",
    )
    args = parser.parse_args()

    # Maps the key we'll use to the subdirectory name and the benchmark name in the log
    benchmark_map = {
        "allreduce": ("osu-allreduce", "osu_allreduce"),
        "latency": ("osu-latency", "osu_latency"),
    }

    parsed_data = process_benchmark_dir(args.results_dir, benchmark_map)
    plot_results(parsed_data, args.output)


if __name__ == "__main__":
    main()
