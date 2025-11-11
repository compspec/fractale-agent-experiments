#!/usr/bin/env python3

import os
import json
import re
from collections import defaultdict

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.font_manager import FontProperties

here = os.path.dirname(os.path.abspath(__file__))

import matplotlib.patches as patches
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import sys

def plot_binding_maps_grid(binding_layouts: dict, filename: str):
    """
    Creates a grid of intuitive, diagram-style plots showing the binding for each experiment.
    This is a corrected version designed for clarity and accuracy.
    """
    # --- Hardcoded Topology for c4-standard-96 ---
    NUM_CORES = 48
    CORES_PER_NUMA = 24
    PUS_PER_CORE = 2
    NUM_NUMA_NODES = 2
    CORE_MAP = {i: [i, i + NUM_CORES] for i in range(NUM_CORES)}
    PU_TO_CORE_MAP = {pu: core for core, pus in CORE_MAP.items() for pu in pus}

    num_plots = len(binding_layouts)
    if num_plots == 0:
        print("No binding layouts found to plot."); return
        
    ncols = 3
    nrows = (num_plots + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(24, 8 * nrows), squeeze=False)
    axes = axes.flatten()

    max_rank_overall = max(max(b.keys()) for b in binding_layouts.values() if b) if any(binding_layouts.values()) else 1
    cmap = plt.get_cmap('viridis')

    for i, (exp_name, all_bindings) in enumerate(binding_layouts.items()):
        ax = axes[i]
        
        if not all_bindings:
            ax.set_title(f"{exp_name}\n(No binding data found)", fontsize=10); ax.axis('off'); continue
            
        total_ranks = max(all_bindings.keys()) + 1
        num_nodes_in_job = 4 if total_ranks > (NUM_CORES * PUS_PER_CORE) else 1
        tasks_per_node = total_ranks // num_nodes_in_job if num_nodes_in_job > 0 else 0
        
        node_bindings = {rank: binding_str for rank, binding_str in all_bindings.items() if 0 <= rank < tasks_per_node}
        
        ax.set_title(f"{exp_name}\n(Node 0 View)", fontsize=12, pad=20)
        ax.set_aspect('equal')
        ax.invert_yaxis()

        # --- NEW AND CORRECTED BINDING RESOLVER ---
        def resolve_binding_to_pus(binding_str: str) -> list:
            """
            Correctly parses a binding string into a definitive list of PU indices.
            """
            pus_to_fill = set()
            try:
                # Case 1: Hierarchical binding (e.g., numa:0.core:12 or core:7.pu:1)
                if '.' in binding_str:
                    parts = binding_str.split('.')
                    # We assume the last part is the finest grain
                    final_part = parts[-1]
                    obj_type, index_str = final_part.split(':')
                    index = int(index_str)
                    
                    if obj_type == 'pu':
                        # Find which core this PU belongs to
                        if len(parts) > 1 and parts[0].startswith('core'):
                            core_id = int(parts[0].split(':')[1])
                            # Get the PUs for this core and select the correct one
                            if index < len(CORE_MAP.get(core_id, [])):
                                pus_to_fill.add(CORE_MAP[core_id][index])
                    # Extend this for numa.core if needed
                    elif obj_type == 'core':
                        if len(parts) > 1 and parts[0].startswith('numa'):
                             numa_id = int(parts[0].split(':')[1])
                             global_core_id = numa_id * CORES_PER_NUMA + index
                             pus_to_fill.update(CORE_MAP.get(global_core_id, []))
                
                # Case 2: Simple binding (e.g., core:5, pu:10, numa:1)
                elif ':' in binding_str:
                    obj_type, index_str = binding_str.split(":")
                    index = int(index_str)
                    if obj_type == "core":
                        # CRITICAL FIX: Binding to a core means ALL PUs on that core.
                        pus_to_fill.update(CORE_MAP.get(index, []))
                    elif obj_type == "pu":
                        # Binding to a PU is just that single PU.
                        pus_to_fill.add(index)
                    elif obj_type == "numa":
                        # Binding to NUMA means all PUs in all cores on that NUMA.
                        start_core = index * CORES_PER_NUMA
                        end_core = start_core + CORES_PER_NUMA
                        for core_id in range(start_core, end_core):
                            pus_to_fill.update(CORE_MAP.get(core_id, []))
            except (ValueError, IndexError):
                 print(f"Warning: Could not parse binding string '{binding_str}'", file=sys.stderr)
            return list(pus_to_fill)

        # --- Drawing Logic (now receives correct PU lists) ---
        core_width, core_height = 2.0, 1.2
        pu_width = core_width / PUS_PER_CORE
        core_h_spacing, core_v_spacing = 0.2, 0.4
        numa_padding = 1.0
        cores_per_row = 12
        
        pu_placements = defaultdict(list)
        is_numa_level_binding = False
        for rank, binding_str in node_bindings.items():
            if binding_str.lower() == "unbound": continue
            if binding_str.startswith("numa:") and '.' not in binding_str:
                is_numa_level_binding = True
            
            pus_for_rank = resolve_binding_to_pus(binding_str)
            for pu_id in pus_for_rank:
                pu_placements[pu_id].append(rank)

        for numa_id in range(NUM_NUMA_NODES):
            numa_y_start = numa_id * ((core_height + core_v_spacing) * (CORES_PER_NUMA / cores_per_row) + numa_padding)
            
            if is_numa_level_binding:
                numa_ranks = [r for r, b_str in node_bindings.items() if f"numa:{numa_id}" in b_str]
                if numa_ranks:
                    numa_width = cores_per_row * (core_width + core_h_spacing) - core_h_spacing
                    numa_height = (CORES_PER_NUMA / cores_per_row) * (core_height + core_v_spacing) - core_v_spacing
                    rank_color = cmap(min(numa_ranks) / max_rank_overall if max_rank_overall > 0 else 0.5)
                    numa_rect = patches.Rectangle((0, numa_y_start), numa_width, numa_height, linewidth=2, edgecolor='black', facecolor=rank_color, alpha=0.7)
                    ax.add_patch(numa_rect)
                    ax.text(numa_width / 2, numa_y_start + numa_height / 2, f"{len(numa_ranks)} Ranks", ha='center', va='center', fontsize=12, color='white', weight='bold')
            else:
                for core_idx_on_numa in range(CORES_PER_NUMA):
                    global_core_id = numa_id * CORES_PER_NUMA + core_idx_on_numa
                    
                    row = core_idx_on_numa // cores_per_row
                    col = core_idx_on_numa % cores_per_row
                    x_pos = col * (core_width + core_h_spacing)
                    y_pos = numa_y_start + row * (core_height + core_v_spacing)

                    core_rect = patches.Rectangle((x_pos, y_pos), core_width, core_height, linewidth=0.5, edgecolor='black', facecolor='#EAEAF2')
                    ax.add_patch(core_rect)
                    ax.text(x_pos + core_width / 2, y_pos - 0.1, f"C{global_core_id}", ha='center', va='top', fontsize=6, color='gray')

                    for pu_slot, pu_id in enumerate(CORE_MAP[global_core_id]):
                        pu_x = x_pos + pu_slot * pu_width
                        ranks_on_pu = pu_placements.get(pu_id, [])
                        if ranks_on_pu:
                            rank_color = cmap(min(ranks_on_pu) / max_rank_overall if max_rank_overall > 0 else 0.5)
                            pu_rect = patches.Rectangle((pu_x, y_pos), pu_width, core_height, facecolor=rank_color, alpha=0.9)
                            ax.add_patch(pu_rect)
                            annot = str(ranks_on_pu[0]) if len(ranks_on_pu) == 1 else f"{len(ranks_on_pu)}+"
                            ax.text(pu_x + 0.5, y_pos + 0.6, annot, ha='center', va='center', fontsize=5, color='white', weight='bold')

            label_y = numa_y_start + ((CORES_PER_NUMA / cores_per_row) * (core_height + core_v_spacing) - core_v_spacing) / 2
            ax.text(-2.5, label_y, f"NUMA\n{numa_id}", ha='center', va='center', fontsize=10, weight='bold')

        ax.autoscale_view()
        ax.axis('off')

    for i in range(num_plots, len(axes)):
        axes[i].axis("off")

    plt.suptitle("Binding Layout Visualization per Experiment (Single Node View)", fontsize=20)
    plt.tight_layout(rect=[0.02, 0.02, 1, 0.97])
    plt.savefig(filename)
    print(f"Saved binding visualization to {filename}")
    plt.close()

def parse_kripke_foms(item):
    """
    Figures of Merit
    ================

      Throughput:         2.683674e+10 [unknowns/(second/iteration)]
      Grind time :        3.726235e-11 [(seconds/iteration)/unknowns]
      Sweep efficiency :  17.43900 [100.0 * SweepSubdomain time / SweepSolver time]
      Number of unknowns: 4932501504
    """
    for line in item.split("\n"):
        if "Grind time" in line:
            parts = [x for x in line.replace(":", "").split(" ") if x]
            return float(parts[2])


def parse_results(results_dir, app):
    """
    Walks through the results directory, parsing each log file for performance
    and binding information.

    Returns:
        A tuple containing:
        - A pandas DataFrame with performance metrics (duration, fom).
        - A dictionary of binding layouts {experiment_name: {rank: binding_str}}.
    """
    all_data = []
    binding_layouts = {}

    if not os.path.isdir(results_dir):
        print(f"Error: Results directory '{results_dir}' not found.")
        return pd.DataFrame(), {}

    for experiment_name in sorted(os.listdir(results_dir)):
        exp_dir = os.path.join(results_dir, experiment_name)
        if not os.path.isdir(exp_dir):
            continue

        binding_layouts[experiment_name] = {}

        for iteration_file in sorted(os.listdir(exp_dir)):
            if not iteration_file.endswith(".out"):
                continue

            filepath = os.path.join(exp_dir, iteration_file)
            iteration_id = int(os.path.splitext(iteration_file)[0])

            with open(filepath, "r") as f:
                content = f.read()

            # --- Extract Metrics ---
            duration = [x for x in content.split("\n") if "fluxtime duration" in x]
            if duration:
                duration = float(duration[0].split(":")[-1].strip().rsplit(" ")[0])

            duration = duration or None
            print(duration)
            if app == "kripke":
                fom = parse_kripke_foms(content)
            elif app == "lammps":
                fom = float([x for x in content.split('\n') if "Matom" in x][0].split(' ')[-2])                
                duration = float([x for x in content.split('\n') if "wall time" in x][0].split(':')[-1])
                print(duration)
            all_data.append(
                {
                    "experiment": experiment_name,
                    "iteration": iteration_id,
                    "duration_s": duration,
                    "fom": fom,
                }
            )

            # --- Extract Bindings (only needed once per experiment type) ---
            if iteration_id == 0:
                # Format: fluxbind: Rank 190 is bound to core:46 to execute...
                binding_matches = re.findall(
                    r"fluxbind: Rank\s+(\d+)\s+is bound to\s+([^\s]+)", content
                )
                for rank, binding in binding_matches:
                    binding_layouts[experiment_name][int(rank)] = binding

    return pd.DataFrame(all_data), binding_layouts


def plot_performance(
    df: pd.DataFrame,
    metric: str,
    title: str,
    ylabel: str,
    filename: str,
    lower_is_better: bool = True,
    log=False,
    plot_type=None,
):
    """
    Creates a boxplot comparing a performance metric across all experiments.
    """
    if metric not in df.columns or df[metric].isnull().all():
        print(f"Warning: Metric '{metric}' not found in data. Skipping plot '{title}'.")
        return

    # Order experiments by the median performance
    order = (
        df.groupby("experiment")[metric]
        .median()
        .sort_values(ascending=lower_is_better)
        .index
    )

    plt.figure(figsize=(14, 8))
    if plot_type == "bar":
        sns.barplot(data=df, x="experiment", y=metric, order=order, palette="viridis")
    else:
        sns.boxplot(data=df, x="experiment", y=metric, order=order, palette="viridis")
        sns.stripplot(data=df, x="experiment", y=metric, order=order, color="0.25", size=4)
    if log:
        plt.yscale('log') 

    plt.title(title, fontsize=16)
    plt.ylabel(ylabel)
    plt.xlabel("Experiment")
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(here, "img", filename))
    print(f"Saved performance plot to {filename}")
    plt.close()


import matplotlib.patches as patches
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import sys

def plot_binding_maps(binding_layouts: dict, filename: str):
    """
    Creates a grid of annotated heatmap plots showing the binding for each experiment.
    This corrected version properly filters for a single node and distinguishes
    between core-level and pu-level bindings.
    """
    # --- Hardcoded Topology for c4-standard-96 ---
    NUM_CORES = 48
    CORES_PER_NUMA = 24
    PUS_PER_CORE = 2
    NUM_NUMA_NODES = NUM_CORES // CORES_PER_NUMA
    core_map = {i: [i, i + NUM_CORES] for i in range(NUM_CORES)}
    pu_to_core_map = {pu: core for core, pus in core_map.items() for pu in pus}

    num_plots = len(binding_layouts)
    if num_plots == 0:
        print("No binding layouts found to plot.")
        return
        
    ncols = 3
    nrows = (num_plots + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(22, 6 * nrows), squeeze=False)
    axes = axes.flatten()

    max_rank_overall = 0
    if any(binding_layouts.values()):
        # Ensure we don't crash if a binding dict is empty
        max_rank_overall = max(max(b.keys()) for b in binding_layouts.values() if b)
    cmap = plt.get_cmap('viridis')

    for i, (exp_name, all_bindings) in enumerate(binding_layouts.items()):
        ax = axes[i]
        
        # --- Filter for a representative node using arithmetic ---
        if not all_bindings:
            ax.set_title(f"{exp_name}\n(No binding data found)", fontsize=10)
            ax.axis('off')
            continue
            
        total_ranks = max(all_bindings.keys()) + 1
        # Heuristic to determine if this was a multi-node job
        num_nodes_in_job = 4 if total_ranks > 96 else 1
        tasks_per_node = total_ranks // num_nodes_in_job
        
        node_bindings = {
            rank: binding_str
            for rank, binding_str in all_bindings.items()
            if 0 <= rank < tasks_per_node
        }
        
        ax.set_title(f"{exp_name}\n(Node 0 View)", fontsize=10)

        # --- DEFINITIVELY CORRECTED BINDING RESOLVER ---
        def resolve_binding_to_pus(binding_str: str) -> list:
            """
            Correctly parses any binding string into a definitive list of PU indices.
            """
            pus_to_fill = set()
            try:
                # Case 1: Hierarchical binding (e.g., "core:5.pu:1")
                if '.' in binding_str:
                    parts = binding_str.split('.')
                    core_part = next((p for p in parts if p.startswith('core:')), None)
                    pu_part = next((p for p in parts if p.startswith('pu:')), None)
                    numa_part = next((p for p in parts if p.startswith('numa:')), None)

                    if core_part and pu_part:
                        core_id = int(core_part.split(':')[1])
                        pu_index_on_core = int(pu_part.split(':')[1])
                        core_pus = core_map.get(core_id, [])
                        if pu_index_on_core < len(core_pus):
                            pus_to_fill.add(core_pus[pu_index_on_core])
                    elif numa_part and core_part:
                        numa_id = int(numa_part.split(':')[1])
                        core_on_numa_id = int(core_part.split(':')[1])
                        global_core_id = numa_id * CORES_PER_NUMA + core_on_numa_id
                        pus_to_fill.update(core_map.get(global_core_id, []))
                
                # Case 2: Simple binding (e.g., "core:5", "pu:10", "numa:1")
                elif ':' in binding_str:
                    obj_type, index_str = binding_str.split(":")
                    index = int(index_str)
                    if obj_type == "core":
                        # CRITICAL FIX: Binding to a core means ALL PUs on that core.
                        pus_to_fill.update(core_map.get(index, []))
                    elif obj_type == "pu":
                        # Binding to a PU is just that single PU.
                        pus_to_fill.add(index)
                    elif obj_type == "numa":
                        # Binding to NUMA means all PUs in all cores on that NUMA.
                        start_core = index * CORES_PER_NUMA
                        end_core = start_core + CORES_PER_NUMA
                        for core_id in range(start_core, end_core):
                            pus_to_fill.update(core_map.get(core_id, []))
            except (ValueError, IndexError):
                 print(f"Warning: Could not parse binding string '{binding_str}'", file=sys.stderr)
            return list(pus_to_fill)

        # Build arrays for heatmap value AND annotation
        plot_array_values = np.full((NUM_NUMA_NODES * PUS_PER_CORE, CORES_PER_NUMA), np.nan)
        plot_array_annot = np.full((NUM_NUMA_NODES * PUS_PER_CORE, CORES_PER_NUMA), "", dtype=object)
        
        pu_to_plot_coords = {}
        for core_id, pus in core_map.items():
            for pu_id in pus:
                numa_id = core_id // CORES_PER_NUMA
                core_on_numa = core_id % CORES_PER_NUMA
                pu_on_core = core_map[core_id].index(pu_id)
                row, col = numa_id * PUS_PER_CORE + pu_on_core, core_on_numa
                pu_to_plot_coords[pu_id] = (row, col)

        pu_placements = defaultdict(list)
        for rank, binding_str in node_bindings.items():
            if binding_str.lower() == "unbound": continue
            pus_for_rank = resolve_binding_to_pus(binding_str)
            for pu_id in pus_for_rank:
                pu_placements[pu_id].append(rank)

        for pu_id, ranks in pu_placements.items():
            if pu_id not in pu_to_plot_coords: continue
            row, col = pu_to_plot_coords[pu_id]
            
            plot_array_values[row, col] = min(ranks)
            plot_array_annot[row, col] = str(ranks[0]) if len(ranks) == 1 else f"{len(ranks)}+"

        # Draw the heatmap
        sns.heatmap(plot_array_values, ax=ax, cmap='viridis', cbar=False, 
                    linewidths=.5, linecolor='white', 
                    annot=plot_array_annot,
                    fmt="s",
                    annot_kws={"size": 6, "color": "white", "ha": "center", "va": "center"})
        
        # Configure labels and titles
        ax.set_xlabel("Core Index (within NUMA node)")
        ax.set_xticks(np.arange(CORES_PER_NUMA) + 0.5)
        ax.set_xticklabels(np.arange(CORES_PER_NUMA), rotation=0, size=7)
        
        yticks = [i + 0.5 for i in range(NUM_NUMA_NODES * PUS_PER_CORE)]
        yticklabels = [f"N{i//PUS_PER_CORE} P{i%PUS_PER_CORE}" for i in range(NUM_NUMA_NODES * PUS_PER_CORE)]
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, rotation=0, size=8)
        
        for numa_boundary in range(1, NUM_NUMA_NODES):
            ax.axhline(y=numa_boundary * PUS_PER_CORE, color='white', linewidth=3)


    # Hide any unused subplots
    for i in range(num_plots, len(axes)):
        axes[i].axis("off")

    plt.suptitle("Binding Layout Visualization per Experiment (Single Node View)", fontsize=18)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(filename)
    print(f"Saved binding visualization to {filename}")
    plt.close()

def plot_text_binding_maps(binding_layouts: dict, filename: str):
    """
    Creates a grid of TEXT-BASED plots showing the binding for each experiment.
    This function is self-contained and does not require hwloc to be installed.
    """
    # --- Hardcoded Topology for c4-standard-96 ---
    NUM_CORES = 48
    CORES_PER_NUMA = 24
    PUS_PER_CORE = 2
    NUM_NUMA_NODES = NUM_CORES // CORES_PER_NUMA
    core_map = {i: [i, i + NUM_CORES] for i in range(NUM_CORES)}
    pu_to_core_map = {pu: core for core, pus in core_map.items() for pu in pus}

    num_plots = len(binding_layouts)
    if num_plots == 0:
        print("No binding layouts found to plot.")
        return
        
    ncols = 3
    nrows = (num_plots + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(22, 6 * nrows), squeeze=False)
    axes = axes.flatten()

    for i, (exp_name, all_bindings) in enumerate(binding_layouts.items()):
        ax = axes[i]
        
        # --- NEW LOGIC: Determine per-node bindings arithmetically ---
        
        # Find the total number of ranks in this experiment
        if not all_bindings:
            ax.set_title(f"{exp_name}\n(No binding data found)", fontsize=10)
            ax.axis('off')
            continue
        
        total_ranks = len(all_bindings)
        
        # Assuming a 4-node job, calculate tasks per node
        tasks_per_node = total_ranks // 4

        # Filter the bindings to include only ranks that belong to the first node (ranks 0 to tasks_per_node - 1)
        node_bindings = {
            rank: binding_str
            for rank, binding_str in all_bindings.items()
            if 0 <= rank < tasks_per_node
        }
        
        # --- End of new logic ---

        # The rest of the function remains the same, operating on 'node_bindings'
        # ... (Robust Binding String Resolver) ...
        def resolve_binding_to_pus(binding_str: str) -> list:
            # ... (this helper is unchanged)
            pus_to_fill = set()
            if '.' in binding_str:
                parts = binding_str.split('.')
                numa_part, core_part = parts[0], parts[1]
                numa_id = int(numa_part.split(':')[1])
                core_on_numa_id = int(core_part.split(':')[1])
                global_core_id = numa_id * CORES_PER_NUMA + core_on_numa_id
                pus_to_fill.update(core_map.get(global_core_id, []))
            elif ':' in binding_str:
                obj_type, index_str = binding_str.split(":")
                index = int(index_str)
                if obj_type == "core": pus_to_fill.update(core_map.get(index, []))
                elif obj_type == "pu": pus_to_fill.add(index)
                elif obj_type == "numa":
                    start_core = index * CORES_PER_NUMA
                    end_core = start_core + CORES_PER_NUMA
                    for core_id in range(start_core, end_core):
                        pus_to_fill.update(core_map.get(core_id, []))
            return list(pus_to_fill)

        plot_array_values = np.full((NUM_NUMA_NODES * PUS_PER_CORE, CORES_PER_NUMA), np.nan)
        plot_array_annot = np.full((NUM_NUMA_NODES * PUS_PER_CORE, CORES_PER_NUMA), "", dtype=object)
        
        pu_to_plot_coords = {}
        for core_id, pus in core_map.items():
            for pu_id in pus:
                numa_id = core_id // CORES_PER_NUMA
                core_on_numa = core_id % CORES_PER_NUMA
                pu_on_core = core_map[core_id].index(pu_id)
                row, col = numa_id * PUS_PER_CORE + pu_on_core, core_on_numa
                pu_to_plot_coords[pu_id] = (row, col)

        pu_placements = defaultdict(list)
        for rank, binding_str in node_bindings.items():
            if binding_str.lower() == "unbound": continue
            pus_for_rank = resolve_binding_to_pus(binding_str)
            for pu_id in pus_for_rank:
                pu_placements[pu_id].append(rank)

        for pu_id, ranks in pu_placements.items():
            if pu_id not in pu_to_plot_coords: continue
            row, col = pu_to_plot_coords[pu_id]
            plot_array_values[row, col] = min(ranks)
            if len(ranks) == 1:
                plot_array_annot[row, col] = str(ranks[0])
            else:
                plot_array_annot[row, col] = f"{len(ranks)}+"

        sns.heatmap(plot_array_values, ax=ax, cmap='viridis', cbar=False, 
                    linewidths=.5, linecolor='white', 
                    annot=plot_array_annot,
                    fmt="s",
                    annot_kws={"size": 6, "color": "white", "ha": "center", "va": "center"})
        
        ax.set_title(f"{exp_name}\n(Node 0 View)", fontsize=10)
        # ... (rest of the plotting aesthetics are the same)
        ax.set_xlabel("Core Index (within NUMA node)")
        ax.set_xticks(np.arange(CORES_PER_NUMA) + 0.5)
        ax.set_xticklabels(np.arange(CORES_PER_NUMA), rotation=0, size=7)
        yticks = [i + 0.5 for i in range(NUM_NUMA_NODES * PUS_PER_CORE)]
        yticklabels = [f"N{i//PUS_PER_CORE} P{i%PUS_PER_CORE}" for i in range(NUM_NUMA_NODES * PUS_PER_CORE)]
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, rotation=0, size=8)
        for numa_boundary in range(1, NUM_NUMA_NODES):
            ax.axhline(y=numa_boundary * PUS_PER_CORE, color='white', linewidth=3)


    for i in range(num_plots, len(axes)):
        axes[i].axis("off")

    plt.suptitle("Binding Layout Visualization per Experiment (Single Node View)", fontsize=18)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(filename)
    print(f"Saved binding visualization to {filename}")
    plt.close()    
def main():
    """
    Main entry point for the script.
    """
    results_dir = os.path.join(here, "results")

    # We can parse apps separately
    for app in os.listdir(results_dir):
        df, bindings = parse_results(os.path.join(results_dir, app), app)
        idx = df.shape[0]

        # Need to add the raw times for no affinity
        if app == "kripke":
            no_affinity_logs = os.path.join(
                results_dir, app, "192ranks_no-affinity", "logs"
            )
            for i, logfile in enumerate(os.listdir(no_affinity_logs)):
                logfile = os.path.join(no_affinity_logs, logfile)
                with open(logfile, "r") as f:
                    content = f.read()
                complete_line = [x for x in content.split("\n") if "complete" in x][0]
                start_line = [x for x in content.split("\n") if "shell.start" in x][0]
                start_ts = json.loads(start_line)["timestamp"]
                end_ts = json.loads(complete_line)["timestamp"]
                duration = end_ts - start_ts
                df.loc[idx, :] = ["192ranks_no-affinity", i, duration, None]

        summary = (
            df.groupby("experiment")
            .agg(
                median_duration_s=("duration_s", "median"),
                median_grind_time_ms=("fom", "median"),
                std_dev_duration_s=("duration_s", "std"),
            )
            .sort_values("median_duration_s")
        )
        print(summary)
        print("\n--- Generating Plots ---")
        plot_performance(
            df,
            metric="duration_s",
            plot_type="bar",
            title=f"{app.upper()} Performance: Total Job Duration",
            ylabel="Total Duration (seconds)",
            filename=f"{app}_duration_comparison.png",
            lower_is_better=True,
        )
        if app == "kripke":
            title = f"{app.upper()} Figure of Merit: Grind Time"
        elif app == "lammps":
            title = f"{app.upper()} Figure of Merit: M-atom steps/s"
        plot_performance(
            df,
            metric="fom",
            title=title,
            ylabel="Grind Time (milliseconds)",
            filename=f"{app}_fom_comparison.png",
            lower_is_better=True,
        )
        plot_binding_maps_grid(
           binding_layouts=bindings,
           filename=os.path.join(here, "img", f"{app}_binding_grid_layouts.png")
        )
        plot_binding_maps(
           binding_layouts=bindings,
           filename=os.path.join(here, "img", f"{app}_binding_layouts.png")
        )
        plot_text_binding_maps(
           binding_layouts=bindings,
           filename=os.path.join(here, "img", f"{app}_text_binding_layouts.png")
        )
    

if __name__ == "__main__":
    main()
