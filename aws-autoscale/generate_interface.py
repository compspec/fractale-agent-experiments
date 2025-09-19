#!/usr/bin/env python3

import argparse
import base64
import difflib
import io
import json
import yaml
import os
import re
import shutil
import pandas
from collections import defaultdict
from datetime import datetime

import jinja2
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name


# Being lazy - let's create a global data frame of key/value pairs we can set for different metrics to plot.
# Each app has a different set of runs - "vanilla" and then with a function.
df = pandas.DataFrame(
    columns=[
        "app",
        "path",
        "experiment",
        "experiment_type",
        "metric_name",
        "direction",
        "metric",
        "value",
        "unit",
        "agent",
    ]
)
df_idx = 0
commands = {}

# Gemini df
gemini_df = pandas.DataFrame(
    columns=["Application", "Experiment", "Agent", "Attempt", "Prompt Tokens", "Candidate Tokens", "Total Tokens"]
)

# Don't include non experiment runs
experiment_runs = [
    "kripke",
    "amg2023",
    "laghos",
    "lammps-max-fom",
    "lammps-decision-function",
    "laghos-decision-function",
    "lammps-decision-fom",
    "amg2023-function",
    "amg2023-decision-function",
    "kripke-decision-function",
]

# Instance metadata to help us summarize choices
instances = {
    "t3.medium": {
        "memory": 4,
        "cores": 2,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "c7a.12xlarge": {
        "memory": 96,
        "cores": 48,
        "platform": "AMD",
        "architecture": "amd64",
    },
    "hpc7g.16xlarge": {
        "memory": 128,
        "cores": 64,
        "platform": "ARM (Graviton3)",
        "architecture": "arm64",
    },
    "c6in.12xlarge": {
        "memory": 96,
        "cores": 24,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "r7iz.8xlarge": {
        "memory": 256,
        "cores": 16,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "m6g.12xlarge": {
        "memory": 192,
        "cores": 48,
        "platform": "ARM (Graviton2)",
        "architecture": "arm64",
    },
    "t3a.2xlarge": {
        "memory": 32,
        "cores": 4,
        "platform": "AMD",
        "architecture": "amd64",
    },
    "t3.2xlarge": {
        "memory": 32,
        "cores": 4,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "m6id.12xlarge": {
        "memory": 192,
        "cores": 24,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "c6id.12xlarge": {
        "memory": 96,
        "cores": 24,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "t4g.2xlarge": {
        "memory": 32,
        "cores": 8,
        "platform": "ARM (Graviton2)",
        "architecture": "arm64",
    },
    "m6i.12xlarge": {
        "memory": 192,
        "cores": 24,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "m6a.12xlarge": {
        "memory": 192,
        "cores": 24,
        "platform": "AMD",
        "architecture": "amd64",
    },
    "m7g.16xlarge": {
        "memory": 256,
        "cores": 64,
        "platform": "ARM (Graviton3)",
        "architecture": "arm64",
    },
    "c6i.16xlarge": {
        "memory": 128,
        "cores": 32,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "c6a.16xlarge": {
        "memory": 128,
        "cores": 32,
        "platform": "AMD",
        "architecture": "amd64",
    },
    "c7g.16xlarge": {
        "memory": 128,
        "cores": 64,
        "platform": "ARM (Graviton3)",
        "architecture": "arm64",
    },
    "r6i.8xlarge": {
        "memory": 256,
        "cores": 16,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "r6a.12xlarge": {
        "memory": 384,
        "cores": 24,
        "platform": "AMD",
        "architecture": "amd64",
    },
    "r7g.12xlarge": {
        "memory": 384,
        "cores": 48,
        "platform": "ARM (Graviton3)",
        "architecture": "arm64",
    },
    "i4i.8xlarge": {
        "memory": 256,
        "cores": 16,
        "platform": "Intel",
        "architecture": "amd64",
    },
    "d3.4xlarge": {
        "memory": 128,
        "cores": 8,
        "platform": "Intel",
        "architecture": "amd64",
    },
}

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} | Fractale Agent Results</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css"/>
    <style>
        :root { --pico-font-size: 90%; }
        body { padding: 2rem 3rem; }
        nav { margin-bottom: 2rem; }
        nav ol { margin-bottom: 0; }
        .grid { grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); }
        .card { text-align: center; }
        .card-header { font-weight: bold; font-size: 1.1em; }
        .card-footer { font-size: 0.9em; }
        .status { padding: 0.2rem 0.6rem; border-radius: var(--pico-border-radius); color: white; }
        .status-succeeded { background-color: green; }
        .status-failed { background-color: red; }
        .tab-nav a { cursor: pointer; padding: 0.5rem 1rem; border-radius: var(--pico-border-radius); transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out; }
        .tab-nav a.active { background-color: var(--pico-primary); color: var(--pico-primary-inverse); font-weight: bold; }
        .tab-content { display: none; padding-top: 1rem; border-top: 1px solid var(--pico-muted-border-color); }
        .tab-content.active { display: block; }
        .asset-version-btn { margin-right: 0.5rem; margin-bottom: 0.5rem; }
        .asset-content { display: none; }
        .asset-content.active { display: block; }
        pre, code { white-space: pre-wrap; word-wrap: break-word; }
        .decision-retry { color: green; }
        .decision-stop { color: red; } 

        .diff-toggle-btn { float: right; margin-bottom: 1rem; --pico-font-size: 0.8em; }
        .diff-content { display: none; clear: both; }

        .diff-table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        .diff-table th { background-color: var(--pico-card-background-color); padding: 0.5rem; text-align: center; font-weight: bold; }
        .diff-table td { border: 1px solid var(--pico-muted-border-color); padding: 5px; font-family: monospace; vertical-align: top; }
        .diff_add { background-color: #1c3c1c; color: #a8dba8; }
        .diff_sub { background-color: #4d1f1f; color: #e0a3a3; }
        .diff_chg { background-color: #4a4a22; color: #f1f1b0; }
        
        {{ pygments_css }}
    </style>
</head>
<body>
    <nav aria-label="breadcrumb">
        <ul>
            {% for crumb in breadcrumbs %}
                <li><a href="{{ crumb.url }}">{{ crumb.text }}</a></li>
            {% endfor %}
            {# The title is always the last, unlinked item #}
            <li>{{ title }}</li>
        </ul>
    </nav>
    <main class="container">
        {% block content %}{% endblock %}
    </main>

     <footer class="container" style="margin-top: 4rem;">
        <hr>
        <p style="text-align: center; color: var(--pico-muted-color);">
            Made with ❤️ by <a href="https://github.com/vsoch">@vsoch</a>
        </p>
    </footer>

</body>
</html>
"""

INDEX_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
    <header style="text-align: center; margin-bottom: 3rem;">
        <h1>🤖 Fractale Agent Experiments</h1>
        <p>A central dashboard for Fractale Agent experiments.</p>
        <a href="summary.html" role="button" class="contrast outline">View Overall Summary</a>
    </header>

    <div class="grid">
        {% for app_name, data in apps.items() %}
        <article class="card">
            <div class="card-header">{{ app_name }}</div>
            <p>
                <span class="status status-succeeded">{{ data.summary.succeeded }} Succeeded</span>
                <span class="status status-failed">{{ data.summary.failed }} Failed</span>
            </p>
            {% if data.summary.best_fom is not none %}
            <p><strong>Best Result:</strong> {{ data.summary.best_fom }} FOM</p>
            {% endif %}
            <div class="card-footer">
                <a href="{{ app_name }}/index.html" role="button">View {{ data.runs|length }} Runs</a>
            </div>
        </article>
        {% endfor %}
    </div>
{% endblock %}
"""

SUMMARY_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
    <header>
        <h1 style="text-align: center;">Overall Summary</h1>
    </header>

    <nav class="tab-nav">
        <ul>
            <li><a class="tab-link active" onclick="showTab('summary-stats', this)">Summary Stats</a></li>
            <li><a class="tab-link" onclick="showTab('gemini-analysis', this)">Gemini Analysis</a></li>
        </ul>
    </nav>

    <section id="summary-stats" class="tab-content active">
        <article>
            <h4>Run Status Counts</h4>
            <p>A breakdown of succeeded vs. failed runs for each application.</p>
            <img src="data:image/png;base64,{{ status_plot }}" alt="Run Status Counts" style="width: 100%; height: auto;">
        </article>
        <article>
            <h4>Agent Attempts</h4>
            <p>Distribution of the number of attempts each agent took to succeed, grouped by application.</p>
            <img src="data:image/png;base64,{{ attempts_plot }}" alt="Agent Attempts" style="width: 100%; height: auto;">
        </article>
    </section>

    <section id="gemini-analysis" class="tab-content">
        <article>
            <h4>Token Counts vs. API Time</h4>
            <p>This scatterplot shows the relationship between the number of tokens (for prompt, candidates, and total) and the wall time for each call to the Gemini API across all experiments.</p>
            <img src="data:image/png;base64,{{ gemini_summary_plot }}" alt="Gemini Summary Plot" style="width: 100%; height: auto;">
        </article>
    </section>

<script>
    function showTab(tabId, element) {
        document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        element.classList.add('active');
    }
    function toggleDiff(elementId) {
        const el = document.getElementById(elementId);
        const btn = event.target;
        if (el.style.display === 'none' || el.style.display === '') {
            el.style.display = 'block';
            btn.textContent = 'Hide Diff';
        } else {
            el.style.display = 'none';
            btn.textContent = 'Show Diff';
        }
    }
</script>
{% endblock %}
"""

APP_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
    <h1>Runs for: {{ app_name }}</h1>
    <table>
        <thead>
            <tr>
                <th>Run ID</th>
                <th>Status</th>
                <th>Best FOM</th>
                <th>Timestamp</th>
            </tr>
        </thead>
        <tbody>
            {% for run in runs %}
            <tr>
                <td><a href="{{ run.id }}.html">{{ run.id }}</a></td>
                <td><span class="status status-{{ run.status|lower }}">{{ run.status }}</span></td>
                <td>{{ run.best_fom if run.best_fom is not none else 'N/A' }}</td>
                <td>{{ run.timestamp }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{% endblock %}
"""

RUN_TEMPLATE = """
{% extends "base.html" %}
{% block content %}
    <header>
        <h2>{{ run_data.manager.name }}</h2>
        <p>{{ run_data.manager.description }}</p>
        <p><strong>Status:</strong> <span class="status status-{{ run_data.status|lower }}">{{ run_data.status }}</span></p>
    </header>

    <nav class="tab-nav">
        <ul>
            <li><a class="tab-link active" onclick="showTab('plan', this)">Plan</a></li>
            <li><a class="tab-link" onclick="showTab('plots', this)">Plots</a></li>
            <li><a class="tab-link" onclick="showTab('assets', this)">Files</a></li>
            <li><a class="tab-link" onclick="showTab('optimize', this)">Optimize</a></li>
            {% if gemini_plot_data %}
            <li><a class="tab-link" onclick="showTab('gemini', this)">Gemini</a></li>
            {% endif %}
        </ul>
    </nav>

    <section id="plan" class="tab-content active">
        <h3>Execution Plan</h3>
        {% for step in run_data.manager.plan %}
            <article>
                <h4>Step: <code>{{ step.agent }}</code></h4>
                <details>
                    <summary>View Context</summary>
                    {{ highlight_code(step.context, 'json') | safe }}
                </details>
            </article>
        {% endfor %}
    </section>

    <section id="plots" class="tab-content">
        <h3>Timing Plots</h3>
        {% for plot in plots %}
            <article>
                <h4>{{ plot.title }}</h4>
                <img src="data:image/png;base64,{{ plot.data }}" alt="{{ plot.title }}" style="width: 100%; height: auto;">
            </article>
        {% endfor %}
    </section>
    
   <section id="assets" class="tab-content">
        <h3>Agent Assets</h3>
        {% for agent_name, assets in assets_data.items() %}
        <details open>
            <summary><h4>Assets for <code>{{ agent_name }}</code> Agent</h4></summary>
            {% for asset_name, versions in assets.items() %}
                <article>
                    <h5>{{ asset_name }}</h5>
                    <div>
                        {% for i in range(versions|length) %}
                            <button class="asset-version-btn" onclick="showAsset('{{ agent_name }}-{{ asset_name }}', {{ i }})">
                                Attempt {{ i + 1 }}
                            </button>
                        {% endfor %}
                    </div>
                    {% for version in versions %}
                        <div id="{{ agent_name }}-{{ asset_name }}-{{ loop.index0 }}" class="asset-content">
                            {% if loop.index0 > 0 and version.diff %}
                            <button class="contrast outline diff-toggle-btn" onclick="toggleDiff('{{ agent_name }}-{{ asset_name }}-{{ loop.index0 }}-diff', this)">Show Diff</button>
                            <div id="{{ agent_name }}-{{ asset_name }}-{{ loop.index0 }}-diff" class="diff-content">
                                {{ version.diff | safe }}
                            </div>
                            {% endif %}
                            {{ version.highlighted_code | safe }}
                        </div>
                    {% endfor %}
                </article>
            {% endfor %}
        </details>
        {% endfor %}
    </section>

    <section id="optimize" class="tab-content">
        <h3>Optimization Analysis</h3>
        <article>
            <h4>Figure of Merit (FOM) Progression</h4>
            <p>Lower is better. A value of 0.0 indicates a failed run for that attempt.</p>
            <canvas id="fomChart"></canvas>
        </article>
        
        <h4>Optimization Decisions</h4>
        {% for update in optimization_data.updates %}
        <details style="margin-bottom: 1rem;">
            <summary>
                <strong class="decision-{{ update.decision|lower }}">Decision {{ loop.index }}: {{ update.decision }}</strong>
            </summary>
            <article style="margin-top: 1rem;">
                <p><strong>Agent's Rationale:</strong> {{ update.reason }}</p>
                <details>
                    <summary>View Full State Diff</summary>
                    <p>This shows the diff of the entire update object, including the decision and reason, to see the complete state change.</p>
                    {{ update.diff | safe }}
                </details>
            </article>
        </details>
        {% endfor %}
    </section>

    {% if gemini_plot_data %}
    <section id="gemini" class="tab-content">
        <h3>Gemini API Usage</h3>
        <article>
            <p>This plot shows the relationship between input (prompt) and output (candidate) token counts for each call to the Gemini API. The size of each point corresponds to the total tokens used in that call.</p>
            <img src="data:image/png;base64,{{ gemini_plot_data }}" alt="Gemini Token Usage Plot" style="width: 100%; height: auto;">
        </article>
    </section>
    {% endif %}

<script>
    function showTab(tabId, element) {
        document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        element.classList.add('active');
    }

    function showAsset(assetPrefix, index) {
        document.querySelectorAll(`[id^="${assetPrefix}-"]`).forEach(content => content.classList.remove('active'));
        const activeContent = document.getElementById(`${assetPrefix}-${index}`);
        if (activeContent) {
            activeContent.classList.add('active');
        }
    }
    
    function toggleDiff(elementId, btn) {
        const el = document.getElementById(elementId);
        if (el.style.display === 'none' || el.style.display === '') {
            el.style.display = 'block';
            btn.textContent = 'Hide Diff';
        } else {
            el.style.display = 'none';
            btn.textContent = 'Show Diff';
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.asset-content').forEach(el => {
            const idParts = el.id.split('-');
            if (parseInt(idParts[idParts.length - 1]) === 0) {
                el.classList.add('active');
            }
        });

        {% if optimization_data and optimization_data.foms %}
        const ctx = document.getElementById('fomChart').getContext('2d');
        const fomData = {{ optimization_data.foms | tojson }};
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: fomData.length}, (_, i) => `Attempt ${i + 1}`),
                datasets: [{
                    label: 'Figure of Merit (Wall Time)',
                    data: fomData,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true,
                }]
            },
            options: { scales: { y: { beginAtZero: true, title: { display: true, text: 'Time (seconds)' } } } }
        });
        {% endif %}
    });
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}
"""


def highlight_code(code_str, language, style="monokai"):
    """
    Highlights a code string using Pygments.
    """
    try:
        lexer = get_lexer_by_name(language, stripall=True)
    except:
        lexer = get_lexer_by_name("text", stripall=True)
    formatter = HtmlFormatter(
        style=style, cssclass="highlight", wrapcode=True, noclasses=False
    )
    return highlight(code_str, lexer, formatter)


def generate_diff_html(text1, text2, from_label="Previous", to_label="Current"):
    """
    Generates a side-by-side HTML diff table.
    """
    differ = difflib.HtmlDiff(wrapcolumn=80)
    diff = differ.make_table(
        text1.splitlines(keepends=True),
        text2.splitlines(keepends=True),
        fromdesc=from_label,
        todesc=to_label,
    )
    return diff


def gather_all_run_data(results_dir):
    """
    Gather detailed data from all JSON files across all applications.
    """
    all_runs = []
    for app_name in os.listdir(results_dir):
        app_name = filter_apps(app_name)
        if not app_name:
            continue
        app_path = os.path.join(results_dir, app_name)
        if not os.path.isdir(app_path):
            continue
        for filename in os.listdir(app_path):
            if filename.endswith(".json"):
                file_path = os.path.join(app_path, filename)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    data["app_name"] = app_name  # Inject app name for grouping
                    all_runs.append(data)
                except Exception as e:
                    print(f"Warning: Could not load {file_path}. Error: {e}")
    return all_runs


def generate_attempts_boxplot(all_runs_data):
    """
    Generates a boxplot of agent attempts per application.
    """
    df_data = []
    for run in all_runs_data:
        app_name = run.get("app_name", "Unknown")
        for step in run.get("steps", []):
            df_data.append(
                {
                    "Application": app_name,
                    "Agent": step.get("agent", "unknown").title(),
                    "Attempts": step.get("attempts", 0),
                }
            )

    if not df_data:
        return None
    df = pd.DataFrame(df_data)

    plt.figure(figsize=(10, 7))
    sns.set_theme(style="whitegrid")
    plot = sns.boxplot(
        data=df, x="Application", y="Attempts", hue="Agent", palette="muted"
    )
    plot.set_title("Agent Attempts per Application", fontsize=16)
    plot.set_xlabel("Application")
    plot.set_ylabel("Number of Attempts")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_status_countplot(all_runs_data):
    """
    Generate a stacked bar chart of run statuses per application.
    """
    df_data = [
        {
            "Application": run.get("app_name", "Unknown"),
            "Status": run.get("status", "Failed"),
        }
        for run in all_runs_data
    ]
    if not df_data:
        return None
    df = pd.DataFrame(df_data)

    plt.figure(figsize=(10, 7))
    sns.set_theme(style="whitegrid")
    plot = sns.histplot(
        data=df,
        x="Application",
        hue="Status",
        multiple="stack",
        shrink=0.8,
        palette={"Succeeded": "seagreen", "Failed": "indianred"},
    )
    plot.set_title("Run Status Counts per Application", fontsize=16)
    plot.set_xlabel("Application")
    plot.set_ylabel("Total Runs")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_timing_plot(times_data, title):
    """
    Generates a Seaborn boxplot and returns it as a base64 encoded string.
    """
    df_data = []
    for category, values in times_data.items():
        # Prettify the category names for the plot labels
        pretty_category = category.replace("_seconds", "").replace("_", " ").title()
        for value in values:
            df_data.append({"Category": pretty_category, "Time (s)": value})

    if not df_data:
        return None

    df = pd.DataFrame(df_data)

    # Adjust figure size for better label spacing
    plt.figure(figsize=(10, 7))
    sns.set_theme(style="whitegrid")

    # --- THE KEY CHANGE: Use boxplot instead of lineplot ---
    plot = sns.boxplot(
        data=df, x="Category", hue="Category", y="Time (s)", palette="viridis"
    )

    plot.set_title(title, fontsize=16)
    plot.set_xlabel("")  # The category labels are self-explanatory
    plot.set_ylabel("Time (seconds)")

    # Rotate x-axis labels for readability if they are long
    plt.xticks(rotation=45, ha="right")

    # Ensure all elements fit within the figure
    legend = plot.get_legend()
    if legend:
        legend.set_title("")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def parse_wall_time(time_string: str) -> float:
    """
    Parses a time string in [HH:]MM:SS[.ms] format into total seconds.

    Args:
        time_string: A string representing the wall time, e.g., "1:23:45", "12:34", "59.5".

    Returns:
        The total time in seconds as a float.
    """
    parts = time_string.strip().split(":")
    time_in_seconds = 0.0

    # The last part is always seconds
    time_in_seconds += float(parts[-1])

    # If there are two parts, the first is minutes
    if len(parts) > 1:
        time_in_seconds += int(parts[-2]) * 60

    # If there are three parts, the first is hours
    if len(parts) > 2:
        time_in_seconds += int(parts[-3]) * 3600

    return time_in_seconds


def get_language_for_asset(asset_name):
    """
    Guess the language for syntax highlighting based on asset name.
    """
    if "dockerfile" in asset_name.lower():
        return "docker"
    if "manifest" in asset_name.lower() or "minicluster" in asset_name.lower():
        return "yaml"
    if "log" in asset_name.lower():
        return "log"
    return "text"


def get_foms(foms_raw, app_name):
    """
    Process foms - we often have strings that need parsing!
    """
    if "kripke" in app_name:
        foms_raw = [float(x) for x in foms_raw]
    elif foms_raw and ":" in foms_raw[0]:
        foms_raw = [parse_wall_time(x) for x in foms_raw]
    foms = []
    if foms_raw:
        try:
            foms = [float(fom) for fom in foms_raw if fom and str(fom) != "00"]
        except (ValueError, TypeError) as e:
            print(
                f"Warning: Could not convert all FOMs to float for {json_path}. Error: {e}"
            )
    return foms


def process_run_data(json_path, app_name):
    """
    Loads and processes a single JSON result file for template rendering.
    """
    global df
    global df_idx
    global commands
    with open(json_path, "r") as f:
        data = json.load(f)
    application = get_application_name(app_name)
    experiment = app_name
    direction, metric_name, unit = get_direction_unit(experiment)
    experiment_type = get_experiment_type(experiment)

    # Pre-format the manager plan's context dictionaries into JSON strings
    if "manager" in data and "plan" in data["manager"]:
        for step in data["manager"]["plan"]:
            if "context" in step and isinstance(step["context"], dict):
                step["context"] = json.dumps(step["context"], indent=4)

    # Process timing plots
    plots = []
    for step in data.get("steps", []):
        agent_name = step.get("agent")
        if not agent_name:
            continue
        times = step.get("metadata", {}).get("times", {})
        if times:
            title = f"Timing Breakdown for {agent_name.capitalize()} Agent"
            plot_b64 = generate_timing_plot(times, title)
            if plot_b64:
                plots.append({"title": title, "data": plot_b64})

    gemini_plot_data = generate_gemini_plot(
        data.get("steps", []), application, experiment
    )

    # 1. Process all regular assets first with robust type checking
    assets_data = {}
    for step in data.get("steps", []):
        agent_name = step.get("agent", "unknown")
        assets = step.get("metadata", {}).get("assets", {})
        if not assets:
            continue
        if agent_name not in assets_data:
            assets_data[agent_name] = {}

        attempts = step.get("attempts")
        agent = step.get("agent")

        # This goes into dockerfile, minicluster log, etc.
        for asset_name, versions in assets.items():
            # This loop now ONLY handles regular assets. 'optimize' is not an asset.
            processed_versions = []
            lang = get_language_for_asset(asset_name)

            # Ensure 'versions' is iterable (it should be a list)
            if not isinstance(versions, list):
                continue

            if asset_name not in assets_data[agent_name]:
                assets_data[agent_name][asset_name] = []
            for i, version_data in enumerate(versions):
                item = ""
                if isinstance(version_data, dict):
                    item = version_data.get("item", "")
                elif isinstance(version_data, str):
                    item = version_data

                # If we have a minicluster, parse attributes. We want to know:
                # instance type
                # architecture (arm or x86)
                # cpu
                # memory
                # Question: do we include the first attempt?
                if "minicluster" in asset_name:
                    try:
                        mc = yaml.load(item, Loader=yaml.SafeLoader)
                    except:
                        break

                    try:
                        command = mc["spec"]["containers"][0]["command"]

                        # Testing instance is t3.medium
                        instance_type = (
                            mc["spec"]
                            .get("pod", {})
                            .get("nodeSelector", {})
                            .get("node.kubernetes.io/instance-type")
                        )
                    except:
                        print(f"Issue with loaded yaml:\n{mc}")
                        continue

                    # Testing
                    if instance_type is None:
                        continue

                    # Save final command
                    if application not in commands:
                        commands[application] = {}
                    if experiment_type not in commands[application]:
                        commands[application][experiment_type] = []
                    commands[application][experiment_type].append(command)

                    # This was an accident
                    if instance_type == "c7a.32xlarge":
                        print(mc)
                        continue
                    arch = instances[instance_type]["architecture"]
                    platform = instances[instance_type]["platform"]
                    cores = instances[instance_type]["cores"]
                    memory = instances[instance_type]["memory"]
                    for pair in [
                        [instance_type, "instance-type"],
                        [arch, "arch"],
                        [platform, "platform"],
                        [cores, "cores"],
                        [memory, "memory"],
                    ]:
                        df.loc[df_idx, :] = [
                            application,
                            json_path,
                            experiment,
                            experiment_type,
                            metric_name,
                            direction,
                            pair[1],
                            pair[0],
                            unit,
                            agent,
                        ]
                        df_idx += 1

                prev_item = ""
                if i > 0:
                    prev_version_data = versions[i - 1]
                    if isinstance(prev_version_data, dict):
                        prev_item = prev_version_data.get("item", "")
                    elif isinstance(prev_version_data, str):
                        prev_item = prev_version_data

                diff_html = generate_diff_html(prev_item, item)
                assets_data[agent_name][asset_name].append(
                    {"highlighted_code": highlight_code(item, lang), "diff": diff_html}
                )

    # 2. Separately, find and process the unique 'optimize' block from metadata
    optimization_data = None
    for step in data.get("steps", []):
        # The 'optimize' block is under metadata, not assets
        optimize_meta = step.get("metadata", {}).get("assets").get("optimize")
        if optimize_meta and optimization_data is None:
            updates = optimize_meta.get("assets", {}).get("updates", [])
            processed_updates = []
            for i, update in enumerate(updates):
                update_str = json.dumps(update, indent=2)
                prev_update_str = ""
                if i > 0:
                    prev_update_str = json.dumps(updates[i - 1], indent=2)

                processed_updates.append(
                    {
                        "decision": update.get("decision", "N/A"),
                        "reason": update.get("reason", "N/A"),
                        "diff": generate_diff_html(
                            prev_update_str,
                            update_str,
                            "Previous State",
                            "Updated State",
                        ),
                    }
                )

            foms_raw = optimize_meta.get("foms", [])
            optimization_data = {
                "foms": get_foms(foms_raw, app_name),
                "updates": processed_updates,
            }
            break

    return {
        "run_data": data,
        "plots": plots,
        "assets_data": assets_data,
        "optimization_data": optimization_data,
        "gemini_plot_data": gemini_plot_data,
    }


def generate_gemini_plot(steps_data, app, experiment):
    """
    Generate scatterplot for Gemini token usage.
    """
    global gemini_df
    df_data = []
    for step in steps_data:
        agent_name = step.get("agent", "unknown_agent").title()
        gemini_calls = step.get("metadata", {}).get("ask_gemini", [])
        for i, call in enumerate(gemini_calls):
            df_data.append(
                {
                    "Application": app,
                    "Experiment": experiment,  # experiment_type
                    "Agent": agent_name,
                    "Attempt": i + 1,
                    "Prompt Tokens": call.get("prompt_token_count", 0),
                    "Candidate Tokens": call.get("candidates_token_count", 0),
                    "Total Tokens": call.get("total_token_count", 0),
                }
            )

    if not df_data:
        return None

    gdf = pd.DataFrame(df_data)
    gemini_df = pandas.concat([gemini_df, gdf])
    plt.figure(figsize=(10, 7))
    sns.set_theme(style="whitegrid")

    # Create a colorful scatterplot
    # Hue distinguishes agents by color
    # Size represents the total token cost of the call
    plot = sns.scatterplot(
        data=gdf,
        x="Prompt Tokens",
        y="Candidate Tokens",
        hue="Agent",
        size="Total Tokens",
        sizes=(50, 500),  # Range of bubble sizes
        palette="deep",
        alpha=0.7,
    )

    plot.set_title("Gemini API Token Usage per Call", fontsize=16)
    plot.set_xlabel("Prompt Token Count (Input)")
    plot.set_ylabel("Candidate Token Count (Output)")
    plt.legend(title="Agent")
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.savefig(os.path.join("data", "img", "gemini-queries.svg"))
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def generate_gemini_summary_plot(all_runs_data):
    """
    Generate a scatterplot of Gemini token counts vs. time across all runs.
    """
    df_data = []
    for run in all_runs_data:
        for step in run.get("steps", []):
            for call in step.get("metadata", {}).get("ask_gemini", []):
                time_sec = call.get("time_seconds", 0)
                # Reshape data from a "wide" format to a "long" format for Seaborn's hue
                # This creates a separate row for each type of token count
                df_data.append(
                    {
                        "Seconds": time_sec,
                        "Token Count": call.get("prompt_token_count"),
                        "Token Scope": "prompt_token_count",
                    }
                )
                df_data.append(
                    {
                        "Seconds": time_sec,
                        "Token Count": call.get("candidates_token_count"),
                        "Token Scope": "candidates_token_count",
                    }
                )
                df_data.append(
                    {
                        "Seconds": time_sec,
                        "Token Count": call.get("total_token_count"),
                        "Token Scope": "total_token_count",
                    }
                )

    if not df_data:
        return None

    df = pd.DataFrame(df_data).dropna()
    plt.figure(figsize=(12, 7))
    sns.set_theme(style="whitegrid")

    # Create the scatterplot with hue based on the 'Token Scope'
    plot = sns.scatterplot(
        data=df,
        x="Token Count",
        y="Seconds",
        hue="Token Scope",
        palette="muted",
        alpha=0.8,
    )

    plot.set_title("Gemini Token Counts vs. Total Time", fontsize=16)
    plot.set_xlabel("Token Count")
    plot.set_ylabel("Seconds")

    handles, labels = plot.get_legend_handles_labels()
    labels = [" ".join(x.split("_")) for x in labels]
    plot.legend(handles, labels)
    plt.tight_layout()

    # Convert plot to base64 for embedding in HTML
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    plt.savefig(os.path.join("data", "img", "gemini-summary-plot.svg"))
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def filter_apps(app_name):
    # This was asking to minimize time
    if "lammps-test" in app_name:
        return
    return app_name


def get_application_name(app_name):
    if "lammps" in app_name:
        application = "lammps"
    elif "kripke" in app_name:
        application = "kripke"
    elif "laghos" in app_name:
        application = "laghos"
    elif "amg" in app_name:
        application = "amg2023"
    return application


def get_experiment_type(experiment):
    # Save FOM to data frame based on app, experiment, etc.
    # These are the "raw" runs where we let the LLM decide
    if experiment in [
        "kripke",
        "amg2023",
        "laghos",
        "lammps-max-fom",
    ]:
        experiment_type = "llm-decision"
    # These are controlled user decision - we provide a function that explicitly
    # instructs for next resources and setup
    elif experiment in ["lammps-decision-function", "amg2023-decision-function"]:
        experiment_type = "user-provided-function"
    # This is a user guided decision - give the agent information about scaling
    # and still allow it to decide resources, etc.
    elif experiment in [
        "laghos-decision-function",
        "lammps-decision-fom",
        "amg2023-function",
        "kripke-decision-function",
    ]:
        experiment_type = "user-guided-function"
    else:
        experiment_type = "test"
    return experiment_type


def get_direction_unit(experiment):
    direction = "maximize"
    if "lammps-wall-time" in experiment:
        direction = "minimize"
        metric_name = "wall_time_seconds"
        unit = "(seconds)"
    elif "lammps" in experiment:
        metric_name = "katom_steps"
        unit = "(atom-steps/second)"
    elif "kripke" in experiment:
        metric_name = "grind_time"
        unit = "(iterations/second)"
    elif "amg" in experiment:
        metric_name = "figure_of_merit"
        unit = "(nnz/s)"
    elif "laghos" in experiment:
        metric_name = "major_kernels_total_rate"
        unit = "(megadofs x time steps / second)"
    else:
        import IPython

        IPython.embed()
    return direction, metric_name, unit


def scan_results(results_dir):
    """
    Parse results directory to gather data for the index pages.
    """
    global df
    global df_idx
    apps = defaultdict(
        lambda: {"summary": {"succeeded": 0, "failed": 0, "best_fom": None}, "runs": []}
    )

    for app_name in os.listdir(results_dir):
        app_name = filter_apps(app_name)
        if not app_name or app_name not in experiment_runs:
            continue
        app_path = os.path.join(results_dir, app_name)
        if not os.path.isdir(app_path):
            continue

        # We need to save max foms ACROSS runs
        for filename in os.listdir(app_path):
            if filename.endswith(".json"):
                file_path = os.path.join(app_path, filename)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)

                    status = data.get("status", "Failed")
                    run_id = os.path.splitext(filename)[0]
                    match = re.search(
                        r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", filename
                    )
                    timestamp = match.group(1).replace("_", " ") if match else "N/A"

                    best_fom = None
                    for step in data.get("steps", []):
                        instruction = data["manager"]["name"].lower()
                        opt_meta = (
                            step.get("metadata", {})
                            .get("assets", {})
                            .get("optimize", {})
                        )

                        # Application
                        application = get_application_name(app_name)

                        # Add attempts (this is on the level of a step)
                        experiment = os.path.basename(app_path)
                        attempts = step.get("attempts")
                        direction, metric_name, unit = get_direction_unit(experiment)
                        agent = step.get("agent")
                        experiment_type = get_experiment_type(experiment)
                        if attempts is not None:
                            df.loc[df_idx, :] = [
                                application,
                                file_path,
                                experiment,
                                experiment_type,
                                "attempts",
                                None,
                                "attempts",
                                attempts,
                                "count",
                                agent,
                            ]
                            df_idx += 1

                        if not opt_meta:
                            continue
                        foms = get_foms(opt_meta.get("foms", []), app_name)
                        if not foms:
                            continue
                        best_fom = max(foms)

                        # The first fom is from the deployment agent, and we explicitly ask for a small problem size
                        for fom in foms:
                            # for fom in foms[1:]:
                            df.loc[df_idx, :] = [
                                application,
                                file_path,
                                experiment,
                                experiment_type,
                                metric_name,
                                direction,
                                "fom",
                                fom,
                                unit,
                                agent,
                            ]
                            df_idx += 1
                        break

                    if status == "Succeeded":
                        apps[app_name]["summary"]["succeeded"] += 1
                        current_best = apps[app_name]["summary"]["best_fom"]
                        if best_fom and (
                            current_best is None or best_fom > current_best
                        ):
                            apps[app_name]["summary"]["best_fom"] = best_fom
                    else:
                        apps[app_name]["summary"]["failed"] += 1

                    # add the status (this is across agents)
                    df.loc[df_idx, :] = [
                        application,
                        file_path,
                        experiment,
                        experiment_type,
                        "status",
                        None,
                        "status",
                        status.lower(),
                        "status",
                        None,
                    ]
                    df_idx += 1

                    apps[app_name]["runs"].append(
                        {
                            "id": run_id,
                            "status": status,
                            "best_fom": best_fom,
                            "timestamp": timestamp,
                        }
                    )
                except Exception as e:
                    print(f"Warning: Could not process {file_path}. Error: {e}")

    # Sort runs by timestamp descending
    for app_name in apps:
        apps[app_name]["runs"].sort(key=lambda x: x["timestamp"], reverse=True)

    return apps


def main():
    """Main function to generate the static HTML report."""
    parser = argparse.ArgumentParser(
        description="Generate a static HTML report from experiment result JSON files."
    )
    parser.add_argument(
        "--results_dir",
        default="./results",
        help="Path to the root directory containing application result folders.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./report",
        help="Directory to save the generated HTML files.",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.results_dir):
        print(f"Error: Input directory '{args.results_dir}' not found.")
        return

    # Setup Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.DictLoader(
            {
                "base.html": BASE_TEMPLATE,
                "index.html": INDEX_TEMPLATE,
                "app.html": APP_TEMPLATE,
                "run.html": RUN_TEMPLATE,
                "summary.html": SUMMARY_TEMPLATE,
            }
        )
    )
    env.globals["highlight_code"] = highlight_code

    if os.path.exists(args.output_dir):
        shutil.rmtree(args.output_dir)
    os.makedirs(args.output_dir)

    print("Scanning results directory...")
    apps_data = scan_results(args.results_dir)
    all_runs_data = gather_all_run_data(args.results_dir)

    pygments_css = HtmlFormatter(style="monokai").get_style_defs(".highlight")

    # 1. Generate main index.html (the portal)
    print("Generating main portal page...")
    template = env.get_template("index.html")
    html_content = template.render(
        title="Home", apps=apps_data, pygments_css=pygments_css, breadcrumbs=[]
    )
    with open(os.path.join(args.output_dir, "index.html"), "w") as f:
        f.write(html_content)

    # 2. Generate the summary.html page
    print("Generating overall summary page...")
    template = env.get_template("summary.html")
    html_content = template.render(
        title="Overall Summary",
        pygments_css=pygments_css,
        breadcrumbs=[{"text": "Home", "url": "index.html"}],
        attempts_plot=generate_attempts_boxplot(all_runs_data),
        status_plot=generate_status_countplot(all_runs_data),
        gemini_summary_plot=generate_gemini_summary_plot(all_runs_data),
    )
    with open(os.path.join(args.output_dir, "summary.html"), "w") as f:
        f.write(html_content)

    # 3. Generate pages for each application
    for app_name, data in apps_data.items():
        app_output_dir = os.path.join(args.output_dir, app_name)
        os.makedirs(app_output_dir, exist_ok=True)

        print(f"Generating summary page for '{app_name}'...")
        template = env.get_template("app.html")
        html_content = template.render(
            title=app_name,
            app_name=app_name,
            runs=data["runs"],
            pygments_css=pygments_css,
            breadcrumbs=[{"text": "Home", "url": "../index.html"}],
        )
        with open(os.path.join(app_output_dir, "index.html"), "w") as f:
            f.write(html_content)

        # 4. Generate detailed page for each run
        for run in data["runs"]:
            print(f"  - Generating report for run '{run['id']}'...")
            json_path = os.path.join(args.results_dir, app_name, f"{run['id']}.json")

            try:
                processed_data = process_run_data(json_path, app_name)
                template = env.get_template("run.html")
                html_content = template.render(
                    title=run["id"],
                    pygments_css=pygments_css,
                    breadcrumbs=[
                        {"text": "Home", "url": "../index.html"},
                        {"text": app_name, "url": "index.html"},
                    ],
                    **processed_data,
                )
                with open(os.path.join(app_output_dir, f"{run['id']}.html"), "w") as f:
                    f.write(html_content)
            except Exception as e:
                print(
                    f"    ERROR: Failed to generate report for {run['id']}. Error: {e}"
                )
                import IPython

                IPython.embed()

    print(
        f"\n✅ Report generation complete! View the results at:\nfile://{os.path.abspath(args.output_dir)}/index.html"
    )

    # Finish up with plots for the data!
    global df
    global df_idx

    df.to_csv(os.path.join("data", "foms-results.csv"))
    img_outdir = os.path.join("data", "img")
    if not os.path.exists(img_outdir):
        os.makedirs(img_outdir)

    # Filter out test data
    fom_df = df[df.experiment_type != "test"]
    fom_df = fom_df[fom_df.metric == "fom"]
    for app in fom_df.app.unique():
        subset = fom_df[fom_df.app == app]
        fig = plt.figure(figsize=(6, 3.3))
        gs = plt.GridSpec(1, 1, width_ratios=[2])
        axes = []
        cpu_ax = fig.add_subplot(gs[0, 0])
        axes.append(cpu_ax)
        # axes.append(fig.add_subplot(gs[0, 1], sharey=cpu_ax))
        # axes.append(fig.add_subplot(gs[0, 2]))
        unit = subset.unit.unique()[0]

        # fig, axes = plt.subplots(1, 2, sharey=True, figsize=(18, 3.3))
        sns.set_style("whitegrid")
        sns.barplot(
            subset,
            ax=axes[0],
            x="experiment_type",
            y="value",
            hue="experiment_type",
            err_kws={"color": "darkred"},
            # palette=cloud_colors,
        )
        metric_name = " ".join(
            [x.capitalize() for x in subset.metric_name.unique()[0].split("_")]
        )
        title = app.upper() + " " + metric_name
        axes[0].set_title(title, fontsize=14)
        axes[0].set_ylabel(unit, fontsize=14)
        axes[0].set_xlabel("", fontsize=14)
        # handles, labels = axes[1].get_legend_handles_labels()
        # axes[0].set_xticklabels(axes[0].get_xticklabels(), rotation=45, horizontalalignment='right')
        labels = axes[0].get_xticklabels()
        labels = ["\n".join(x._text.split("-")) for x in labels]
        axes[0].set_xticklabels(labels)
        plt.tight_layout()
        plt.savefig(os.path.join(img_outdir, f"{app}.svg"))
        plt.clf()

    # Attempts plot
    subset = df[df.metric == "attempts"]
    plt.figure(figsize=(10, 7))
    sns.set_theme(style="whitegrid")
    plot = sns.boxplot(subset, x="app", y="value", hue="agent", palette="muted")
    plot.set_title("Agent Attempts per Application", fontsize=16)
    plot.set_xlabel("Application")
    plot.set_ylabel("Number of Attempts")
    plot.legend().set_title(None)
    plt.tight_layout()
    plt.savefig(os.path.join("data", "img", "application-attempts.svg"))
    plt.close()

    subset = df[df.metric == "status"]
    plt.figure(figsize=(10, 7))
    sns.set_theme(style="whitegrid")
    plot = sns.histplot(
        data=subset,
        x="app",
        hue="value",
        multiple="stack",
        shrink=0.8,
        palette={"succeeded": "seagreen", "failed": "indianred"},
    )
    plot.set_title("Run Status Counts per Application", fontsize=16)
    plot.set_xlabel("Application")
    plot.set_ylabel("Total Runs")
    # plot.legend().set_title("Status")
    plt.tight_layout()
    plt.savefig(os.path.join("data", "img", "application-status.svg"))
    plt.close()

    with open(os.path.join("data", "commands.json"), "w") as fd:
        fd.write(json.dumps(commands, indent=4))

    filtered = df[df.value != "t3.medium"]

    # TODO: memory per core?
    for value in ["platform", "memory", "cores", "instance-type"]:
        subset = filtered[filtered.metric == value]
        # Don't count test instance
        plt.figure(figsize=(10, 7))
        sns.set_theme(style="whitegrid")
        plot = sns.histplot(
            data=subset,
            x="app",
            multiple="dodge",
            hue="value",
            palette="muted",
            shrink=0.8,
        )
        title = " ".join([x.capitalize() for x in value.split("-")])
        plot.set_title(f"{title} Selection", fontsize=16)
        plot.set_xlabel("")
        plot.set_ylabel(title)
        plt.tight_layout()
        plt.savefig(os.path.join("data", "img", f"{value}.svg"))
        plt.close()

    gemini_df.to_csv(os.path.join("data", "gemini-results.csv"))

    for agent in gemini_df.Agent.unique():
        subset = gemini_df[gemini_df.Agent == agent]
        plt.figure(figsize=(10, 7))
        sns.set_theme(style="whitegrid")
        plot = sns.scatterplot(
          data=subset,
          x="Prompt Tokens",
          y="Candidate Tokens",
          hue="Application",
          size="Total Tokens",
          sizes=(50, 500),  # Range of bubble sizes
          palette="deep",
          alpha=0.7,
        )
        plot.set_title(f"Gemini API Token Usage per Call ({agent} Agent)", fontsize=16)
        plot.set_xlabel("Prompt Token Count (Input)")
        plot.set_ylabel("Candidate Token Count (Output)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join("data", "img", f"gemini-queries-{agent}.svg"))
        plt.close()
   


if __name__ == "__main__":
    main()

# constrain instance types
# build for multiple nodes on AWS.
# size 4 is the max.
# lammps amg osu laghos
