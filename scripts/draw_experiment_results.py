"""Reproduce four experiment figures from the paper tables and checked JSON records.

Run from any directory: python scripts/draw_experiment_results.py
Original measurements/tables are never modified. PDF is for LaTeX; PNG is for review.
"""
from pathlib import Path
import json
import math
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import NullLocator, ScalarFormatter

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "sections/experiments.tex").read_text(encoding="utf-8")
OUT = ROOT / "pic"
APPS = ["plate_new", "recognition", "scan", "wami", "nightvision"]
BLUE, GRAY, ORANGE = "#226A9D", "#BBC3CC", "#B65B24"
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 8.5, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8.5,
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "savefig.facecolor": "white",
})


def table(label):
    start = TEXT.index(r"\label{" + label + "}")
    stop = TEXT.index(r"\end{table", start)
    return TEXT[start:stop]


def app_rows(label):
    return re.findall(
        r"\\texttt\{([^}]+)\}\s*&\s*(.*?)\\\\",
        table(label), flags=re.S,
    )


def name(raw):
    return raw.replace(r"\_", "_")


def number(cell):
    return float(cell.strip())


def save(fig, basename):
    fig.savefig(OUT / (basename + ".pdf"), bbox_inches="tight", pad_inches=0.04)
    fig.savefig(OUT / (basename + ".png"), dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(OUT / (basename + ".pdf"))


def read_pairs():
    pairs = {}
    for raw, cells in app_rows("tab:dse_fpga_latency_comparison"):
        fields = cells.split("&")
        if len(fields) != 6:
            raise ValueError("Unexpected latency table row: " + raw)
        d_cpu, d_hw, b_cpu, b_hw = map(number, [fields[0], fields[1], fields[3], fields[4]])
        assert min(d_cpu, d_hw, b_cpu, b_hw) > 0
        pairs[name(raw)] = dict(d_cpu=d_cpu, d_hw=d_hw, b_cpu=b_cpu, b_hw=b_hw)
    assert set(pairs) == set(APPS)
    # Cross-check board values against the independent measurement records.
    for app, filename in [("wami", "wami_ibex_results.json"),
                          ("nightvision", "nightvision_leon3_area04_results.json")]:
        record = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
        if app == "wami":
            board_cpu = record["board"]["cpu"]["total"]["ms"]
            board_hw = record["board"]["hw"]["total"]["ms"]
        else:
            board_cpu = record["board"]["cpu_total_ms"]
            board_hw = record["board"]["hw_total_ms"]
        assert math.isclose(pairs[app]["b_cpu"], board_cpu, abs_tol=0.0005)
        assert math.isclose(pairs[app]["b_hw"], board_hw, abs_tol=0.0005)
    return pairs


def plot_speedups(pairs):
    fig, ax = plt.subplots(figsize=(3.55, 2.65))
    y = np.arange(len(APPS))
    predicted = [pairs[a]["d_cpu"] / pairs[a]["d_hw"] for a in APPS]
    measured = [pairs[a]["b_cpu"] / pairs[a]["b_hw"] for a in APPS]
    bars_dse = ax.barh(y - 0.17, predicted, height=0.29, color=GRAY,
                       edgecolor="#67717C", linewidth=0.5, label="DSE estimate")
    bars_board = ax.barh(y + 0.17, measured, height=0.29, color=BLUE,
                         edgecolor=BLUE, linewidth=0.5, label="FPGA measured")
    for bars, vals in [(bars_dse, predicted), (bars_board, measured)]:
        for bar, val in zip(bars, vals):
            ax.text(val + 0.12, bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}", va="center", fontsize=8)
    ax.axvline(1, color="#4F5964", linestyle="--", linewidth=0.8, zorder=0)
    ax.set_yticks(y, APPS)
    ax.invert_yaxis()
    ax.set_xlim(0, 10.45)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_xlabel("Complete-application speedup (×)")
    ax.grid(axis="x", color="#E6E8EB", linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc="lower center", bbox_to_anchor=(0.43, 1.02), ncol=2,
              frameon=False, handlelength=1.1, columnspacing=1.0)
    fig.tight_layout(pad=0.25)
    save(fig, "e2e-speedup-comparison")
    return dict(board_geomean=math.prod(measured) ** (1 / len(measured)),
                predicted_speedups=dict(zip(APPS, predicted)),
                board_speedups=dict(zip(APPS, measured)))


def read_hotspots():
    pattern = (r"(?:\\texttt\{([^}]+)\})?\s*&\s*\\texttt\{([^}]+)\}\s*"
               r"&\s*([\d.]+)\s*&\s*([\d.]+)\s*&\s*([\d.]+)\s*"
               r"&\s*([\d.]+)\$\\times\$\s*\\\\")
    rows, app = [], None
    for raw_app, kernel, share, cpu, hw, rounded in re.findall(
            pattern, table("tab:hotspot_acceleration")):
        if raw_app:
            app = name(raw_app)
        assert app in APPS, "Missing application for hotspot row"
        cpu, hw = number(cpu), number(hw)
        assert cpu > 0 and hw > 0
        ratio = cpu / hw
        assert math.isclose(ratio, number(rounded), abs_tol=0.0051)
        rows.append(dict(application=app, kernel=name(kernel), cpu_ms=cpu,
                         hardware_ms=hw, speedup=ratio, cpu_share_pct=number(share)))
    assert [sum(r["application"] == app for r in rows) for app in APPS] == [2, 2, 1, 3, 1]
    wami = json.loads((ROOT / "data/wami_ibex_results.json").read_text(encoding="utf-8"))
    for row in rows:
        if row["application"] == "wami":
            for mode, field in [("cpu", "cpu_ms"), ("hw", "hardware_ms")]:
                assert math.isclose(row[field], wami["board"][mode][row["kernel"]]["ms"],
                                    abs_tol=0.0005)
    return rows


def plot_hotspots():
    rows = read_hotspots()
    fig, ax = plt.subplots(figsize=(7.05, 3.35))
    positions, groups, cursor = [], [], 0.0
    for app in APPS:
        group = [r for r in rows if r["application"] == app]
        start = cursor
        for row in group:
            positions.append(cursor)
            cursor += 1
        groups.append((app, start, cursor - 1))
        cursor += 0.55
    ax.set_xscale("log")
    ax.set_xlim(0.55, 4500)
    ax.set_ylim(cursor - 0.8, -1.1)
    ax.set_xticks([1, 10, 100, 1000])
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#E6E8EB", linewidth=0.5)
    ax.set_axisbelow(True)
    transform = ax.get_yaxis_transform()
    for i, (app, first, last) in enumerate(groups):
        if i % 2 == 0:
            ax.axhspan(first - 0.45, last + 0.45, color="#F5F7F9", zorder=0)
        ax.text(-0.65, (first + last) / 2, app, transform=transform,
                ha="left", va="center", fontsize=8.5)
    for row, y in zip(rows, positions):
        val = row["speedup"]
        color = BLUE if val >= 1 else ORANGE
        # Bars start at the meaningful 1x reference, never at zero on a log axis.
        ax.barh(y, val - 1, left=1, height=0.58, color=color, zorder=3)
        ax.text(-0.04, y, row["kernel"], transform=transform,
                ha="right", va="center", fontsize=8)
        ax.text(val * 1.13 if val >= 1 else 1.13, y, f"{val:.2f}\u00d7",
                ha="left", va="center", fontsize=8,
                color=ORANGE if val < 1 else "#17364D")
    ax.axvline(1, color="#4F5964", linestyle="--", linewidth=0.8, zorder=4)
    ax.text(-0.65, -0.9, "Application", transform=transform, fontsize=8.5,
            fontweight="bold", ha="left", va="center")
    ax.text(-0.04, -0.9, "Accelerator", transform=transform, fontsize=8.5,
            fontweight="bold", ha="right", va="center")
    ax.set_xlabel("Measured stage speedup (\u00d7, logarithmic scale)")
    fig.legend(handles=[Patch(facecolor=BLUE, label="Speedup"),
                        Patch(facecolor=ORANGE, label="Slowdown")],
               loc="upper right", bbox_to_anchor=(0.97, 0.99), frameon=False,
               ncol=2, handlelength=1.1, columnspacing=1.1)
    fig.subplots_adjust(left=0.42, right=0.98, bottom=0.14, top=0.88)
    save(fig, "hotspot-stage-speedups")
    return rows


def plot_board_applications(pairs):
    values = [pairs[app]["b_cpu"] / pairs[app]["b_hw"] for app in APPS]
    geomean = math.prod(values) ** (1 / len(values))
    assert math.isclose(geomean, 2.47, abs_tol=0.005)
    values.append(geomean)
    fig, ax = plt.subplots(figsize=(3.55, 2.55))
    y = np.asarray([0, 1, 2, 3, 4, 5.3])
    bars = ax.barh(y, values, height=0.58, color=[BLUE] * 5 + ["#67717C"])
    for bar, value in zip(bars, values):
        ax.text(value + 0.08, bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}×", ha="left", va="center", fontsize=8.5)
    ax.axhline(4.65, color="#CED3D9", linewidth=0.6)
    ax.axvline(1, color="#4F5964", linestyle="--", linewidth=0.8, zorder=0)
    ax.set_yticks(y, APPS + ["Geometric\nmean"])
    ax.invert_yaxis()
    ax.set_xlim(0, 5.2)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("Measured end-to-end speedup (×)")
    ax.grid(axis="x", color="#E6E8EB", linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=0.25)
    save(fig, "board-application-speedups")


def plot_agent_stages():
    # Read failure-stage names from the existing results table. FPGA is excluded
    # by --skip-fpga, not counted as a failed stage or an incomplete agent attempt.
    states, times = {}, {}
    for raw, cells in app_rows("tab:hscobench_results"):
        fields = cells.split("&")
        assert len(fields) == 5
        app = name(raw)
        if app == "plate_recognition":
            app = "plate_new"
        failure = fields[3].strip()
        if failure == "BEV-Sim compilation":
            values = [0, 1, 2, 2, 2, 3]
        elif failure == "BEV-Sim verification":
            values = [0, 0, 0, 1, 2, 3]
        elif failure == "Catapult HLS":
            values = [0, 0, 0, 0, 1, 3]
        else:
            raise ValueError("Unknown failure stage: " + failure)
        states[app] = values
        times[app] = number(fields[1])
    assert set(states) == set(APPS)
    values = np.asarray([states[a] for a in APPS])
    colors = ["#D9EAF5", "#F7DFCF", "#F0F1F3", "#FFFFFF"]
    labels = ["Pass", "Fail", "-", "N/E"]
    fig, ax = plt.subplots(figsize=(7.05, 2.30))
    ax.imshow(values, cmap=ListedColormap(colors), vmin=-0.5, vmax=3.5, aspect="auto")
    for row in range(5):
        for col in range(6):
            state = values[row, col]
            ax.text(col, row, labels[state], ha="center", va="center",
                    color=ORANGE if state == 1 else "#17364D" if state == 0 else "#69717A",
                    fontweight="bold" if state < 2 else "normal", fontsize=9)
    ax.set_xticks(range(6), ["Device-ID\ncheck", "BEV\ncompilation", "BEV\nexecution",
                           "BEV\nverification", "Catapult\nHLS", "FPGA / board\n(excluded)"])
    ax.xaxis.tick_top()
    ax.set_yticks(range(5), APPS)
    ax.set_xticks(np.arange(-0.5, 6, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2.5)
    ax.tick_params(which="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(handles=[Patch(facecolor=c, edgecolor="#D1D5DA", label=l)
                       for c, l in zip(colors, ["Passed", "Failed", "Not reached (-)", "Not evaluated (N/E)"])],
              loc="upper center", bbox_to_anchor=(0.5, -0.035), ncol=4,
              frameon=False, handlelength=1, columnspacing=1.5)
    fig.tight_layout(pad=0.3)
    save(fig, "hscobench-stage-outcomes")
    return dict(stages=states, agent_time_s=times)


def main():
    pairs = read_pairs()
    summary = plot_speedups(pairs)
    assert math.isclose(summary["board_geomean"], 2.47, abs_tol=0.01)
    plot_board_applications(pairs)
    summary["hotspots"] = plot_hotspots()
    summary.update(plot_agent_stages())
    summary["sources"] = ["sections/experiments.tex", "data/wami_ibex_results.json",
                          "data/nightvision_leon3_area04_results.json"]
    summary["limitations"] = [
        "WAMI and nightvision DSE/board implementations differ; no controlled prediction-error claim.",
        "Board logs report unchecked reference verification.",
        "HSCO-Bench FPGA/board stages were excluded by protocol, not failed.",
    ]
    audit = ROOT / "build" / "experiment-figures"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "verified_values.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Checked board geometric mean: {summary['board_geomean']:.6f}x")


if __name__ == "__main__":
    main()
