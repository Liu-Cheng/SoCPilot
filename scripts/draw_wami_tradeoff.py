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
for source in D["provenance"]:
    assert hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest() == source["sha256"]


def tt(value):
    return r"\texttt{" + value.replace("_", r"\_") + "}"


def cache(params, prefix):
    return f"${params[prefix + '_sets']}\\times{params[prefix + '_ways']}$"


def write(name, lines):
    (GEN / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


lines = [r"\begin{table*}[t]", r"\centering",
    r"\caption{CPU, cache, and accelerator configurations selected under application-specific area budgets. DSE estimates and normalized post-synthesis cell areas are reported separately.}",
    r"\label{tab:selected_soc_configs}", r"\footnotesize",
    r"\renewcommand{\arraystretch}{1.15}", r"\setlength{\tabcolsep}{3pt}",
    r"\begin{tabularx}{\textwidth}{@{}llcccrrr>{\raggedright\arraybackslash}X@{}}", r"\toprule",
    r"\textbf{Application} & \textbf{CPU} & \shortstack{\textbf{L2}\\\textbf{sets$\times$ways}} & \shortstack{\textbf{LLC}\\\textbf{sets$\times$ways}} & \shortstack{\textbf{Line}\\\textbf{(B)}} & \shortstack{\textbf{Budget}\\\textbf{(mm$^2$)}} & \shortstack{\textbf{DSE area}\\\textbf{(mm$^2$)}} & \shortstack{\textbf{Synth. area}\\\textbf{(mm$^2$)}} & \textbf{Accelerator(s)} \\",
    r"\midrule"]
for r in D["selected_soc_configs"]:
    p = r["params"]
    lines.append(f"{tt(r['application'])} & {r['cpu']} & {cache(p, 'l2')} & {cache(p, 'llc')} & {p['cache_line_size']} & {r['budget_mm2']:g} & {r['dse_area_mm2']:.3f} & {r['synthesis_equivalent_mm2']:.3f} & " + ", ".join(tt(a) for a in r["accelerators"]) + r" \\")
lines += [r"\bottomrule", r"\end{tabularx}", r"\end{table*}"]
write("selected_soc_configs.tex", lines)

rows = D["wami_tradeoff"]
assert [r["constraint_mm2"] for r in rows] == [1.8, 2.2, 3, 4, 8, 9, 10]
baseline = next(r for r in rows if r["constraint_mm2"] == 1.8)
baseline_latency = baseline["times"]["WAMI_TIME:total"]["ms"]
baseline_area = baseline["synthesis_equivalent_mm2"]
lines = [r"\begin{table*}[t]", r"\centering",
    r"\caption{Selected WAMI area-budget points: architecture transitions, DSE and normalized synthesis areas (mm$^2$), board-measured application latencies (ms), relative speedups, and normalized performance per area.}",
    r"\label{tab:wami_budget_configs}", r"\footnotesize",
    r"\renewcommand{\arraystretch}{1.14}", r"\setlength{\tabcolsep}{3pt}",
    r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}rlcccrrrrrr@{}}", r"\toprule",
    r"\textbf{Budget} & \textbf{CPU} & \textbf{HW} & \shortstack{\textbf{L2}\\\textbf{sets$\times$ways}} & \shortstack{\textbf{LLC}\\\textbf{sets$\times$ways}} & \shortstack{\textbf{Line}\\\textbf{(B)}} & \shortstack{\textbf{DSE}\\\textbf{area}} & \shortstack{\textbf{Synth.}\\\textbf{area}} & \shortstack{\textbf{Latency}\\\textbf{(ms)}} & \shortstack{\textbf{Speedup}\\\textbf{vs. 1.8 mm$^2$}} & \shortstack{\textbf{Normalized}\\\textbf{perf./area}} \\", r"\midrule"]
for r in rows:
    p = r["params"]
    hw = "+".join(a for a, name in [("H", "hessian"), ("W", "warp_image"), ("S", "steepest_descent")] if name in r["accelerators"]) or "None"
    latency_ms = r["times"]["WAMI_TIME:total"]["ms"]
    speedup = baseline_latency / latency_ms
    normalized_perf_area = speedup / (r["synthesis_equivalent_mm2"] / baseline_area)
    lines.append(f"{r['constraint_mm2']:g} & {r['cpu']} & {hw} & {cache(p, 'l2')} & {cache(p, 'llc')} & {p['cache_line_size']} & {r['dse_area_mm2']:.3f} & {r['synthesis_equivalent_mm2']:.3f} & {latency_ms:,.3f} & {speedup:.2f}$\\times$ & {normalized_perf_area:.2f}" + r" \\")
lines += [r"\bottomrule", r"\end{tabular*}", r"\par\vspace{6pt}\noindent",
    r"\parbox{\textwidth}{\scriptsize H: \texttt{hessian}; W: \texttt{warp\_image}; S: \texttt{steepest\_descent}. Ibex/LEON3 use DMA32; Ariane uses DMA64. Speedup compares each complete configuration with the 1.8-mm$^2$ CPU-only configuration (44,161.522 ms). Normalized perf./area is $(T_0/T_i)/(A_i/A_0)$, using synthesis area; subscript 0 denotes the 1.8-mm$^2$ configuration, whose value is 1.00.}",
    r"\end{table*}"]
write("wami_budget_configs.tex", lines)

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
    fig.savefig(ROOT / f"pic/wami-area-budget-measured.{suffix}", dpi=300)
plt.close(fig)
print("Generated two tables and measured WAMI figure from seven selected points.")
