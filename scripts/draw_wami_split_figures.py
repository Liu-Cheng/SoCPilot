"""Regenerate current selection/measurement tables and the measured WAMI sweep.

Inputs are frozen in data/experiment_results.json; no remote service is used.
"""
from pathlib import Path
import hashlib
import json
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "data/experiment_results.json").read_text(encoding="utf-8"))
GEN = ROOT / "data/generated"
GEN.mkdir(exist_ok=True)
rows = D["wami_tradeoff"]
assert [r["constraint_mm2"] for r in rows] == [1.8, 2.2, 3, 4, 8, 9, 10]
baseline = next(r for r in rows if r["constraint_mm2"] == 1.8)
baseline_latency = baseline["times"]["WAMI_TIME:total"]["ms"]
baseline_area = baseline["synthesis_equivalent_mm2"]
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 8, "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": .6, "savefig.facecolor": "white"})
colors = {"Ibex": "#226A9D", "LEON3": "#B65B24", "Ariane": "#25806E"}
markers = {"Ibex": "o", "LEON3": "s", "Ariane": "^"}
x = np.arange(len(rows))
fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.8))
latency = [r["times"]["WAMI_TIME:total"]["ms"] for r in rows]
dse = [r["dse_area_mm2"] for r in rows]
synth = [r["synthesis_equivalent_mm2"] for r in rows]
axes[0].plot(x, latency, color="#4A5159", lw=1.1)
axes[0].set_yscale("log")
axes[0].set_ylim(650, 70000)
axes[0].set_yticks([1000, 3000, 10000, 30000])
axes[0].yaxis.set_major_formatter(ScalarFormatter())
axes[0].set_ylabel("Board application latency (ms, log scale)")
axes[0].set_title("(a) Measured latency", loc="left", fontsize=9)
axes[1].plot(x, [r["constraint_mm2"] for r in rows], "--", color="#A1A9B1", lw=1, label="Budget")
axes[1].plot(x, dse, color="#4A5159", lw=1.1, label="DSE estimate")
axes[1].plot(x, synth, "--", color="#6D7781", lw=1.1, marker="D", ms=3.5,
             markerfacecolor="white", label="Post-synthesis")
axes[1].set_ylabel("Area (mm²)")
axes[1].set_ylim(0, 12.1)
axes[1].set_title("(b) Estimated and synthesized area", loc="left", fontsize=9)
axes[1].legend(frameon=False, loc="upper left", fontsize=7, handlelength=1.6)
for i, r in enumerate(rows):
    cpu = r["cpu"]
    for ax, y in zip(axes, [latency[i], dse[i]]):
        ax.plot(i, y, marker=markers[cpu], color=colors[cpu], ms=5, zorder=4)
    # Keep the 3-mm2 label to the left of the steep segment toward 4 mm2.
    offset, alignment = ((-7, -13), "right") if r["constraint_mm2"] == 3 else ((0, -13), "center")
    axes[0].annotate(f"{latency[i]:,.0f}", (i, latency[i]), xytext=offset,
                     textcoords="offset points", ha=alignment, color=colors[cpu], fontsize=7)
    axes[1].annotate(f"{synth[i]:.2f}", (i, synth[i]), xytext=(0, -13),
                     textcoords="offset points", ha="center", fontsize=7)
for ax in axes:
    ax.set_xticks(x, [f"{r['constraint_mm2']:g}" for r in rows])
    ax.set_xlim(-.4, 6.4)
    ax.set_xlabel("Area budget (mm²; selected points)")
    ax.grid(axis="y", lw=.5, color="#E6E8EB")
    ax.set_axisbelow(True)
fig.legend(handles=[Line2D([], [], color=colors[cpu], marker=markers[cpu], ls="", label=cpu)
                    for cpu in colors], loc="lower center", ncol=3, frameon=False,
           bbox_to_anchor=(.5, -.005), fontsize=8)
fig.subplots_adjust(left=.10, right=.98, bottom=.23, top=.91, wspace=.29)
for suffix in ["pdf", "png"]:
    pass # Keep the original combined figure unchanged.

from matplotlib.transforms import Bbox
for index, name in enumerate(['wami-latency-budget', 'wami-area-prediction']):
    axes[index].set_title('', loc='left')
    other = axes[1-index]
    other.set_visible(False)
    for legend in fig.legends:
        legend.set_visible(False)
    legend = axes[index].legend(handles=[Line2D([], [], color=colors[cpu], marker=markers[cpu], ls='', label=cpu) for cpu in colors], loc='upper center', bbox_to_anchor=(.5, -.27), ncol=3, frameon=False, fontsize=8)
    if index == 1:
        axes[index].add_artist(legend)
        axes[index].legend(frameon=False, loc='upper left', fontsize=7)
    fig.canvas.draw()
    box = Bbox.union([axes[index].get_tightbbox(fig.canvas.get_renderer()), legend.get_window_extent(fig.canvas.get_renderer())]).transformed(fig.dpi_scale_trans.inverted()).expanded(1.04, 1.05)
    fig.savefig(ROOT / f'pic/{name}.pdf', bbox_inches=box)
    other.set_visible(True)
    legend.remove()
plt.close(fig)
print("Generated two tables and measured WAMI figure from seven selected points.")
