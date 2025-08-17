#!/usr/bin/env python3

import json
import sys
import os
import re
import difflib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import argparse
from io import BytesIO
from typing import List, Dict, Tuple
from matplotlib.ticker import MaxNLocator

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)

sns.set_theme(style="whitegrid", palette="muted")


def get_parser():
    parser = argparse.ArgumentParser(
        description="Run analysis",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--results",
        help="root directory with results",
        default=os.path.join(here, "results"),
    )
    parser.add_argument(
        "--out",
        help="directory to save parsed results",
        default=os.path.join(here, "data"),
    )
    return parser


def main():
    """
    Find application result files to parse.
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    outdir = os.path.abspath(args.out)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    output_path = os.path.join(outdir, "analysis_report.html")
    steps_df, lammps_df = process_results(args.results)

    if steps_df.empty:
        print("No valid result files found. Report cannot be generated.")
        return

    create_report(steps_df, lammps_df, output_path=output_path)


def convert_walltime_to_seconds(walltime):
    if isinstance(walltime, int) or isinstance(walltime, float):
        return int(float(walltime) * 60.0)
    elif isinstance(walltime, str) and walltime.isnumeric():
        return int(float(walltime) * 60.0)
    elif ":" in walltime:
        seconds = 0.0
        for i, value in enumerate(walltime.split(":")[::-1]):
            seconds += float(value) * (60.0**i)
        return seconds
    elif not walltime or (isinstance(walltime, str) and walltime == "inf"):
        return 0
    msg = f"Walltime value '{walltime}' is not an integer or colon-separated string."
    raise ValueError(msg)


def parse_lammps_log(log_content):
    wall_time_list = [
        x.split("Total wall time: ")[-1]
        for x in log_content.split("\n")
        if "Total wall time" in x
    ]
    if not wall_time_list:
        return None, None
    wall_time = convert_walltime_to_seconds(wall_time_list[0])
    cpu_utilization_match = re.search(r"([\d.]+)% CPU use", log_content)
    cpu_utilization = (
        float(cpu_utilization_match.group(1)) if cpu_utilization_match else None
    )
    return wall_time, cpu_utilization


def generate_diff_html(
    old_content: str, new_content: str, from_desc: str, to_desc: str
) -> str:
    if not old_content or not new_content or old_content == new_content:
        return "<p>No changes detected between these attempts.</p>"

    differ = difflib.HtmlDiff(wrapcolumn=80)
    diff_html = differ.make_file(
        old_content.splitlines(),
        new_content.splitlines(),
        fromdesc=from_desc,
        todesc=to_desc,
    )
    return diff_html


def read_json(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    return data


def plot_to_base64(plt_figure) -> str:
    buf = BytesIO()
    plt_figure.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(plt_figure)
    return f"data:image/png;base64,{img_str}"


def process_results(directory: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Reads and processes all results-*.json files, creating a unique run_id.
    """
    steps = []
    logs = []

    if not os.path.exists(directory):
        print(f"Warning: results directory {directory} does not exist.")
        return pd.DataFrame(), pd.DataFrame()

    for app in os.listdir(directory):
        app_dir = os.path.join(directory, app)
        if not os.path.isdir(app_dir):
            continue

        result_files = [
            f
            for f in os.listdir(app_dir)
            if f.startswith("results-") and f.endswith(".json")
        ]

        for iteration, filename in enumerate(result_files):
            run_id = f"{app}-{iteration + 1}"
            filepath = os.path.join(app_dir, filename)
            data = read_json(filepath)

            for step in data:
                step_info = {
                    "application": app,
                    "run_id": run_id,
                    "agent": step.get("agent"),
                    "total_seconds": step.get("total_seconds"),
                    "attempts": step.get("attempts", 0) + 1,
                    "metadata": step.get("metadata", {}),
                }
                steps.append(step_info)

                if step.get("agent") == "kubernetes-job":
                    log_items = [
                        x
                        for x in step.get("metadata", {}).get("logs", [])
                        if x["type"] == "log"
                    ]
                    if not log_items:
                        continue

                    log = log_items[0]["item"]
                    wall_time, cpu_utilization = parse_lammps_log(log)
                    if wall_time is not None and cpu_utilization is not None:
                        logs.append(
                            {
                                "run_id": run_id,
                                "application": app,
                                "wall_time": wall_time,
                                "cpu_utilization": cpu_utilization,
                            }
                        )

    return pd.DataFrame(steps), pd.DataFrame(logs)


def generate_all_diffs_html(steps_df: pd.DataFrame) -> str:
    """
    Generates collapsible HTML diffs for every attempt in every run.
    """
    if steps_df.empty:
        return "<p>No data available to generate diffs.</p>"

    all_runs_html = ""
    for run_id, group in steps_df.groupby("run_id"):
        run_html = ""

        build_step = group[group["agent"] == "build"]
        if not build_step.empty:
            metadata = build_step.iloc[0]["metadata"]
            dockerfiles = sorted(
                [s for s in metadata.get("steps", []) if s.get("type") == "dockerfile"],
                key=lambda x: x.get("attempt", 0),
            )

            if len(dockerfiles) > 1:
                run_html += "<h4>Dockerfile Changes</h4>"
                for i in range(len(dockerfiles) - 1):
                    old = dockerfiles[i]
                    new = dockerfiles[i + 1]
                    from_desc = f"Attempt {old.get('attempt', 0)}"
                    to_desc = f"Attempt {new.get('attempt', 0)}"
                    diff = generate_diff_html(
                        old.get("item", ""), new.get("item", ""), from_desc, to_desc
                    )
                    run_html += f"<details><summary>{from_desc} vs. {to_desc}</summary><div class='diff-content'>{diff}</div></details>"

        k8s_step = group[group["agent"] == "kubernetes-job"]
        if not k8s_step.empty:
            metadata = k8s_step.iloc[0]["metadata"]
            crds = sorted(
                [s for s in metadata.get("steps", []) if s.get("type") == "crd"],
                key=lambda x: x.get("attempt", 0),
            )

            if len(crds) > 1:
                run_html += "<h4>Kubernetes Job YAML Changes</h4>"
                for i in range(len(crds) - 1):
                    old = crds[i]
                    new = crds[i + 1]
                    from_desc = f"Attempt {old.get('attempt', 0)}"
                    to_desc = f"Attempt {new.get('attempt', 0)}"
                    diff = generate_diff_html(
                        old.get("item", ""), new.get("item", ""), from_desc, to_desc
                    )
                    run_html += f"<details><summary>{from_desc} vs. {to_desc}</summary><div class='diff-content'>{diff}</div></details>"

        if run_html:
            all_runs_html += f"<details class='run-details'><summary>{run_id}</summary><div class='diff-container'>{run_html}</div></details>"

    if not all_runs_html:
        return "<p>No runs had multiple attempts to generate a diff.</p>"

    return all_runs_html


def create_report(
    steps_df: pd.DataFrame,
    lammps_df: pd.DataFrame,
    output_path="index.html",
):
    plot_b64 = {}

    fig = plt.figure(figsize=(10, 6))
    ax = sns.boxplot(x="application", y="attempts", hue="agent", data=steps_df)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.title("Attempts By Application", fontsize=16)
    plt.xlabel("")
    plt.ylabel("Count Attempts")
    plt.tight_layout()
    plot_b64["iterations"] = plot_to_base64(fig)

    fig = plt.figure(figsize=(10, 6))
    sns.boxplot(x="agent", y="total_seconds", data=steps_df)
    plt.title("Elapsed Time per Step", fontsize=16)
    plt.xlabel("Agent")
    plt.ylabel("Seconds")
    plt.tight_layout()
    plot_b64["elapsed_time"] = plot_to_base64(fig)

    # LAMMPS Wall Time Plot - Conditional check removed as requested
    fig = plt.figure(figsize=(10, 6))
    sns.boxplot(x="application", y="wall_time", data=lammps_df, palette="viridis")
    plt.title("LAMMPS Total Wall Time", fontsize=16)
    plt.ylabel("Seconds")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plot_b64["lammps_wall_time"] = plot_to_base64(fig)

    # LAMMPS CPU Utilization Plot - Conditional check removed as requested
    fig = plt.figure(figsize=(10, 6))
    sns.boxplot(x="application", y="cpu_utilization", data=lammps_df, palette="plasma")
    plt.title("LAMMPS CPU Utilization", fontsize=16)
    plt.xlabel("")
    plt.ylabel("CPU Utilization (%)")
    plt.ylim(0, 105)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plot_b64["lammps_cpu"] = plot_to_base64(fig)

    diff_html_content = generate_all_diffs_html(steps_df)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analysis Report</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
            h1, h2, h4 {{ color: #2c3e50; }}
            h1, h2 {{ border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }}
            .container {{ background-color: #fdfdfd; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 30px; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; padding: 5px; }}
            table.diff {{ font-family: "Courier New", Courier, monospace; border-collapse: collapse; width: 100%; margin-top: 10px; }}
            .diff_header {{ background-color: #e6e6e6; }}
            td.diff_header {{ text-align: center; font-weight: bold; }}
            .diff_next, .diff_add, .diff_chg, .diff_sub {{ font-size: 0.9em; }}
            .diff_add {{ background-color: #eaffea; }}
            .diff_sub {{ background-color: #ffecec; }}
            .diff_chg {{ background-color: #ffffd1; }}
            details.run-details {{ border: 1px solid #ccc; border-radius: 5px; margin-bottom: 1em; }}
            details.run-details > summary {{ font-weight: bold; font-size: 1.2em; cursor: pointer; padding: 10px; background-color: #f7f7f7; }}
            details.run-details[open] > summary {{ border-bottom: 1px solid #ccc; }}
            .diff-container {{ padding: 0 15px 15px 15px; }}
            .diff-container h4 {{ margin-top: 20px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .diff-container details {{ border: 1px solid #e0e0e0; border-radius: 4px; margin-bottom: 5px; }}
            .diff-container summary {{ font-weight: normal; cursor: pointer; padding: 8px; background-color: #fafafa; }}
            .diff-content {{ padding: 10px; }}
        </style>
    </head>
    <body>
        <h1>Fractale Agent Report</h1>
        <div class="container">
            <img src="{plot_b64.get('iterations', '')}" alt="Iterations Plot">
            <img src="{plot_b64.get('elapsed_time', '')}" alt="Elapsed Time Plot">
        </div>
        <div class="container">
            <h2>LAMMPS Logs</h2>
            {'<img src="' + plot_b64.get('lammps_wall_time', '') + '" alt="LAMMPS Wall Time Plot">' if 'lammps_wall_time' in plot_b64 else ''}
            {'<img src="' + plot_b64.get('lammps_cpu', '') + '" alt="LAMMPS CPU Plot">' if 'lammps_cpu' in plot_b64 else ''}
        </div>
        <div class="container">
            <h2>Incremental Change Log (Diffs)</h2>
            <p>Collapsible report of changes for each attempt within every run.</p>
            {diff_html_content}
        </div>
    </body>
    </html>
    """

    with open(output_path, "w") as f:
        f.write(html_template)
    print(f"Report successfully generated at: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()
