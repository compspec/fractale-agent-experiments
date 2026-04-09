import os

here = os.path.dirname(os.path.abspath(__file__))

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json

kripke_results = {
    "1": 4.781227e-09,
    "2": 2.236082e-09,
    "3": 1.409729e-09,
    "4": 9.656174e-10,
    "5": 6.012693e-10,
}

amg_results = {
    "1": 1693481000.0,
    "2": 3329466000.0,
    "3": 4848684000.0,
    "4": 6424653000.0,
    "5": 7831979000.0,
}

lammps_results = {
    "1": "743.061 katom-step/s",
    "2": "1.416 Matom-step/s",
    "3": "2.024 Matom-step/s",
    "4": "2.587 Matom-step/s",
    "5": "3.159 Matom-step/s",
}


def parse_lammps_perf(perf_str):
    """Converts performance strings like '743.1 k' or '1.4 M' to a float in M-atom-steps/s."""
    value_str, unit_str = perf_str.split(" ")
    value = float(value_str)
    unit = unit_str.lower()
    if "katom" in unit:
        return value / 1000.0  # Convert from k to M
    elif "matom" in unit:
        return value  # Already in M
    else:
        return value  # Assume M if no unit


def plot_kripke(ax1):
    nodes = sorted([int(n) for n in kripke_results.keys()])
    best_times = [kripke_results[str(n)] for n in nodes]
    time_at_one_node = best_times[0]
    ideal_times = [time_at_one_node / n for n in nodes]
    scaling_efficiency = [
        (ideal_times[i] / best_times[i]) * 100 for i in range(len(nodes))
    ]

    color1 = "tab:blue"
    ax1.set_xlabel("Number of Nodes", fontsize=20)
    ax1.set_ylabel("Time per Figure of Merit (s)", fontsize=20, color=color1)
    ax1.set_yscale("log")
    sns.lineplot(
        x=nodes,
        y=best_times,
        marker="o",
        markersize=8,
        label="Measured Performance",
        ax=ax1,
        color=color1,
        legend=False,
    )
    sns.lineplot(
        x=nodes,
        y=ideal_times,
        linestyle="--",
        label="Ideal Linear Scaling",
        ax=ax1,
        color="tab:orange",
        legend=False,
    )
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.set_xticks(nodes)
    ax1.set_title("Kripke", fontsize=18)

    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Scaling Efficiency (%)", fontsize=20, color=color2)
    sns.lineplot(
        x=nodes,
        y=scaling_efficiency,
        marker="s",
        markersize=8,
        linestyle=":",
        label="Measured Efficiency",
        ax=ax2,
        color=color2,
        legend=False,
    )
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.set_ylim(0, 110)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    return lines1 + lines2, labels1 + labels2


def plot_amg(ax1):
    nodes = sorted([int(n) for n in amg_results.keys()])
    best_foms = [amg_results[str(n)] for n in nodes]
    fom_at_one_node = best_foms[0]
    ideal_foms = [fom_at_one_node * n for n in nodes]
    scaling_efficiency = [
        (best_foms[i] / ideal_foms[i]) * 100 for i in range(len(nodes))
    ]

    color1 = "tab:blue"
    ax1.set_xlabel("Number of Nodes", fontsize=20)
    ax1.set_ylabel("Figure of Merit (FOM)", fontsize=20, color=color1)
    sns.lineplot(
        x=nodes,
        y=best_foms,
        marker="o",
        markersize=8,
        label="Measured Performance",
        ax=ax1,
        color=color1,
        legend=False,
    )
    sns.lineplot(
        x=nodes,
        y=ideal_foms,
        linestyle="--",
        label="Ideal Linear Scaling",
        ax=ax1,
        color="tab:orange",
        legend=False,
    )
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.set_xticks(nodes)
    ax1.set_title("AMG", fontsize=18)
    ax1.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))

    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Scaling Efficiency (%)", fontsize=20, color=color2)
    sns.lineplot(
        x=nodes,
        y=scaling_efficiency,
        marker="s",
        markersize=8,
        linestyle=":",
        label="Measured Efficiency",
        ax=ax2,
        color=color2,
        legend=False,
    )
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.set_ylim(0, 110)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=16)


def plot_lammps(ax1):
    parsed_results = {
        key: parse_lammps_perf(val) for key, val in lammps_results.items()
    }

    nodes = sorted([int(n) for n in parsed_results.keys()])
    best_perfs = [parsed_results[str(n)] for n in nodes]
    perf_at_one_node = best_perfs[0]
    ideal_perfs = [perf_at_one_node * n for n in nodes]
    scaling_efficiency = [
        (best_perfs[i] / ideal_perfs[i]) * 100 if ideal_perfs[i] > 0 else 0
        for i in range(len(nodes))
    ]

    color1 = "tab:blue"
    ax1.set_xlabel("Number of Nodes", fontsize=20)
    ax1.set_ylabel("Performance (M-atom steps/s)", fontsize=20, color=color1)
    sns.lineplot(
        x=nodes,
        y=best_perfs,
        marker="o",
        markersize=8,
        label="Measured Performance",
        ax=ax1,
        color=color1,
        legend=False,
    )
    sns.lineplot(
        x=nodes,
        y=ideal_perfs,
        linestyle="--",
        label="Ideal Linear Scaling",
        ax=ax1,
        color="tab:orange",
        legend=False,
    )
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.set_xticks(nodes)
    ax1.set_title("LAMMPS", fontsize=18)

    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel("Scaling Efficiency (%)", fontsize=20, color=color2)
    sns.lineplot(
        x=nodes,
        y=scaling_efficiency,
        marker="s",
        markersize=8,
        linestyle=":",
        label="Measured Efficiency",
        ax=ax2,
        color=color2,
        legend=False,
    )
    ax2.tick_params(axis="y", labelcolor=color2)
    ax2.set_ylim(0, 110)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=16)


sns.set_theme(style="whitegrid", context="talk")
fig, axes = plt.subplots(3, 1, figsize=(10, 20))  # 1 row, 3 columns, wider figure

# Call the functions to draw on all three axes
lines, labels = plot_kripke(axes[0])
plot_amg(axes[1])
plot_lammps(axes[2])

# Turn off the axis for the empty subplot where the legend will go
# axes[1, 1].set_axis_off()

# Optional: Add a title to the whole figure if desired
# Add a main title for the entire figure
fig.suptitle(
    "Scaling Efficiency on hpc7g.16xlarge Instances",
    fontsize=22,
)

# Adjust layout to prevent titles/labels from overlapping
fig.tight_layout()

# Save and show
plt.savefig(os.path.join(here, "data", "img", "combined_scaling_long.svg"), dpi=300)
