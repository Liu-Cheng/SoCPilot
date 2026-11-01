"""Reproduce experiment plots and the IP-selection case listing from checked JSON.

Run from any directory: python scripts/draw_experiment_results.py
Original measurement records are never modified. PDF is for LaTeX; PNG is for review.
"""
from pathlib import Path
import json
import math
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import NullLocator, ScalarFormatter
from matplotlib.transforms import blended_transform_factory

ROOT = Path(__file__).resolve().parents[1]
RESULTS = json.loads((ROOT / "data/experiment_results.json").read_text(encoding="utf-8"))
OUT = ROOT / "pic"
APPS = ["plate_recognition", "recognition", "scan", "wami", "nightvision"]
BLUE, GRAY, ORANGE = "#226A9D", "#BBC3CC", "#B65B24"
BLUE_FILL, ORANGE_FILL, GRAY_FILL = "#D9EAF5", "#F7DFCF", "#F0F1F3"
BLUE_EDGE, ORANGE_EDGE, GRAY_EDGE = "#91AEC3", "#CEA88E", "#ABB1BA"
COLUMN_FIGURE_WIDTH = 3.5
COLUMN_FONT_SIZE = 8
WIDE_FIGURE_WIDTH = 7.16
WIDE_FONT_SIZE = 8.5
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 8.5, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8.5,
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.6, "savefig.facecolor": "white",
})


def save(fig, basename, *, tight=True):
    options = dict(bbox_inches="tight", pad_inches=0.04) if tight else {}
    fig.savefig(OUT / (basename + ".pdf"), **options)
    fig.savefig(OUT / (basename + ".png"), dpi=300, **options)
    plt.close(fig)
    print(OUT / (basename + ".pdf"))


def read_pairs():
    pairs = {app: dict(b_cpu=row["cpu_ms"], b_hw=row["accelerated_ms"])
             for app, row in RESULTS["board_latencies"].items()}
    assert set(pairs) == set(APPS)
    assert all(min(v.values()) > 0 for v in pairs.values())
    for app, record in RESULTS["board_latencies"].items():
        assert math.isclose(pairs[app]["b_cpu"], record["measurements"]["TIME:cpu:total"]["ms"])
        assert math.isclose(pairs[app]["b_hw"], record["measurements"]["TIME:hw:total"]["ms"])
    return pairs


def read_hotspots():
    rows = RESULTS["hotspots"]
    assert [sum(r["application"] == app for r in rows) for app in APPS] == [1, 2, 1, 2, 1]
    for row in rows:
        assert row["cpu_ms"] > 0 and row["hardware_ms"] > 0
        assert math.isclose(row["speedup"], row["cpu_ms"] / row["hardware_ms"])
    return rows


def plot_hotspots():
    rows = read_hotspots()
    fig, ax = plt.subplots(figsize=(WIDE_FIGURE_WIDTH, 2.95))
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
    ax.set_xlim(0.75, 1600)
    ax.set_ylim(cursor - 0.8, -1.1)
    ax.set_xticks([1, 10, 100, 1000])
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", color="#E6E8EB", linewidth=0.5)
    ax.set_axisbelow(True)
    # Label columns use fixed figure positions, leaving a small, consistent gap.
    transform = blended_transform_factory(fig.transFigure, ax.transData)
    for i, (app, first, last) in enumerate(groups):
        if i % 2 == 0:
            ax.axhspan(first - 0.45, last + 0.45, color="#F5F7F9", zorder=0)
        ax.text(0.15, (first + last) / 2, app, transform=transform,
                ha="right", va="center", fontsize=WIDE_FONT_SIZE)
    for row, y in zip(rows, positions):
        val = row["speedup"]
        color = BLUE_FILL if val >= 1 else ORANGE_FILL
        edge = BLUE_EDGE if val >= 1 else ORANGE_EDGE
        # Bars start at the meaningful 1x reference, never at zero on a log axis.
        ax.barh(y, val - 1, left=1, height=0.58, color=color,
                edgecolor=edge, linewidth=0.6, zorder=3)
        ax.text(0.162, y, row["kernel"], transform=transform,
                ha="left", va="center", fontsize=WIDE_FONT_SIZE)
        ax.text(val * 1.13 if val >= 1 else 1.13, y, f"{val:.2f}\u00d7",
                ha="left", va="center", fontsize=WIDE_FONT_SIZE,
                color=ORANGE if val < 1 else "#17364D")
    ax.axvline(1, color="#4F5964", linestyle="--", linewidth=0.8, zorder=4)
    ax.text(0.15, -0.9, "Application", transform=transform, fontsize=WIDE_FONT_SIZE,
            fontweight="bold", ha="right", va="center")
    ax.text(0.162, -0.9, "Accelerator", transform=transform, fontsize=WIDE_FONT_SIZE,
            fontweight="bold", ha="left", va="center")
    ax.set_xlabel("Measured stage speedup (\u00d7, logarithmic scale)", fontsize=WIDE_FONT_SIZE)
    ax.tick_params(axis="x", labelsize=WIDE_FONT_SIZE)
    fig.legend(handles=[Patch(facecolor=BLUE_FILL, edgecolor=BLUE_EDGE, label="Speedup")],
               loc="upper right", bbox_to_anchor=(0.97, 0.99), frameon=False,
               ncol=2, handlelength=1.1, columnspacing=1.1, fontsize=WIDE_FONT_SIZE)
    fig.subplots_adjust(left=0.335, right=0.98, bottom=0.17, top=0.88)
    save(fig, "hotspot-stage-speedups", tight=False)
    return rows


def plot_board_applications(pairs):
    values = [pairs[app]["b_cpu"] / pairs[app]["b_hw"] for app in APPS]
    geomean = math.prod(values) ** (1 / len(values))
    values.append(geomean)
    fig, ax = plt.subplots(figsize=(3.55, 2.55))
    y = np.asarray([0, 1, 2, 3, 4, 5.3])
    bars = ax.barh(y, values, height=.58, color=[BLUE_FILL] * 5 + [GRAY_FILL],
                   edgecolor=[BLUE_EDGE] * 5 + [GRAY_EDGE], linewidth=.6)
    for bar, value in zip(bars, values):
        ax.text(value + .07, bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}×", ha="left", va="center", fontsize=8.5)
    ax.axhline(4.65, color="#CED3D9", linewidth=0.6)
    ax.axvline(1, color="#4F5964", linestyle="--", linewidth=0.8, zorder=0)
    ax.set_yticks(y, APPS + ["Geometric\nmean"])
    ax.invert_yaxis()
    ax.set_xlim(0, 5.55)
    ax.set_xticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("Measured application speedup (×)")
    ax.grid(axis="x", color="#E6E8EB", linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=0.25)
    save(fig, "board-application-speedups")


def plot_agent_stages():
    # Display the five stages represented by the recorded agent outcomes.
    states, times = {}, {}
    for case in RESULTS["general_agent"]:
        app = case["application"]
        failure = case["failure_stage"]
        if failure == "BEV-Sim compilation":
            values = [0, 1, 2, 2, 2]
        elif failure == "BEV-Sim verification":
            values = [0, 0, 0, 1, 2]
        elif failure == "Catapult HLS":
            values = [0, 0, 0, 0, 1]
        else:
            raise ValueError("Unknown failure stage: " + failure)
        states[app] = values
        times[app] = case["agent_time_s"]
    assert set(states) == set(APPS)
    values = np.asarray([states[a] for a in APPS])
    colors = ["#D9EAF5", "#F7DFCF", "#F0F1F3"]
    labels = ["Pass", "Fail", "-"]
    fig, ax = plt.subplots(figsize=(COLUMN_FIGURE_WIDTH, 1.95))
    ax.imshow(values, cmap=ListedColormap(colors), vmin=-0.5, vmax=2.5, aspect="auto")
    for row in range(5):
        for col in range(5):
            state = values[row, col]
            ax.text(col, row, labels[state], ha="center", va="center",
                    color=ORANGE if state == 1 else "#17364D" if state == 0 else "#69717A",
                    fontweight="bold" if state < 2 else "normal", fontsize=COLUMN_FONT_SIZE)
    ax.set_xticks(range(5), ["Device-ID\ncheck", "BEV\ncompile", "BEV\nexecute",
                           "BEV\nverify", "Catapult\nHLS"])
    ax.xaxis.tick_top()
    ax.set_yticks(range(5), APPS)
    ax.set_xticks(np.arange(-0.5, 5, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2.5)
    ax.tick_params(which="both", length=0, labelsize=COLUMN_FONT_SIZE)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(handles=[Patch(facecolor=c, edgecolor="#D1D5DA", label=l)
                       for c, l in zip(colors, ["Passed", "Failed", "Not reached (-)"])],
              loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3,
              frameon=False, handlelength=0.9, columnspacing=0.8, fontsize=COLUMN_FONT_SIZE)
    fig.subplots_adjust(left=0.25, right=0.99, bottom=0.23, top=0.76)
    save(fig, "hscobench-stage-outcomes", tight=False)
    return dict(stages=states, agent_time_s=times)


def write_ip_selection_case():
    case = json.loads((ROOT / "data/ip_selection_case_study.json").read_text(encoding="utf-8"))
    manifest = case["manifest"]
    demand = manifest["structured_requirement"]
    ids = [ip["id"] for ip in manifest["selected_reusable_ips"]]
    assert len(ids) == 8 and not manifest["unmatched_requirements"]
    receiver = next(ip for ip in manifest["selected_reusable_ips"] if ip["id"] == "mipi_csi2")
    assert receiver["category"] == "communication"
    assert "pixel stream" in receiver["features"] and "frame synchronization" in receiver["features"]
    limits = manifest["constraints"]
    area = manifest["area_accounting"]["reusable_ip_area_mm2"]
    power = manifest["power_accounting"]["reusable_ip_power_mw"]
    assert area <= limits["area_limit_mm2"] and power <= limits["power_limit_mw"]
    description = demand["description"].split(" The application", 1)[0]
    description_lines = textwrap.wrap('description: "' + description + '"', width=98,
                                     subsequent_indent="  ", break_long_words=False,
                                     break_on_hyphens=False)
    id_lines = textwrap.wrap("selected_reusable_ips: [" + ", ".join(ids) + "]", width=98,
                            subsequent_indent="  ", break_long_words=False,
                            break_on_hyphens=False)
    # Display summaries of recorded fields, not a fabricated verbatim execution log.
    lines = ["# 1. SoC description (excerpt)", *description_lines,
             "constraints: [28nm, 75 MHz target, area < 13 mm2, power < 1.5 W]", "",
             "# 2. Structured functional requirements (abridged)",
             "communication: [camera pixel ingress, sensor control, parking-host network]",
             "video: [ping-pong buffers, row stride]   debug: [cycle / transaction counters]",
             "bus: [SRAM working memory, AXI burst transfers, AXI-Lite start/done registers]", "",
             "# 3. Library retrieval and functional check (camera input shown)",
             f"category: {receiver['category']}   technology: {demand['technology']}",
             "need: one CSI-2 receiver with pixel-stream input and frame markers",
             f"selected_ip: {receiver['id']}   features: [pixel stream input, frame synchronization]", "",
             "# 4. Resource check and exported manifest (excerpt)",
             f"reusable_ip_area_mm2: {area:g} <= {limits['area_limit_mm2']:g}   "
             f"reusable_ip_power_mw: {power:g} <= {limits['power_limit_mw']:g}",
             *id_lines, "unmatched_requirements: []",
             "deployment_status: recommendation_only"]
    assert max(map(len, lines)) <= 98
    destination = ROOT / "data/ip-selection-case.txt"
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(destination)
    return case


def main():
    pairs = read_pairs()
    speedups = {app: pairs[app]["b_cpu"] / pairs[app]["b_hw"] for app in APPS}
    geomean = math.prod(speedups.values()) ** (1 / len(APPS))
    summary = dict(board_geomean=geomean, board_speedups=speedups,
                   full_elapsed_geomean=math.prod(r["raw_speedup"] for r in RESULTS["board_latencies"].values()) ** .2)
    plot_board_applications(pairs)
    summary["hotspots"] = plot_hotspots()
    summary.update(plot_agent_stages())
    summary["ip_selection_case"] = write_ip_selection_case()
    summary["sources"] = ["data/experiment_results.json", "data/board_20261031/",
                          "data/ip_selection_case_study.json"]
    summary["limitations"] = [
        "Board logs report unchecked reference verification.",
    ]
    audit = ROOT / "build" / "experiment-figures"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "verified_values.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Checked board geometric mean: {geomean:.6f}x")


if __name__ == "__main__":
    main()
