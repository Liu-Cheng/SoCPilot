"""Check the frozen evidence and current paper's timing/area arithmetic."""
from pathlib import Path
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/experiment_results.json").read_text(encoding="utf-8"))
for source in DATA["provenance"]:
    assert hashlib.sha256((ROOT / source["file"]).read_bytes()).hexdigest() == source["sha256"]
for row in DATA["selected_soc_configs"]:
    best = json.loads((ROOT / "data/board_20261031" / row["source_dse"]).read_text(encoding="utf-8"))
    assert best["params"] == row["params"]
    assert best["best_objective"]["Valid"]
    assert math.isclose(best["best_objective"]["total_area_um2"] / 1e6, row["dse_area_mm2"])
    assert math.isclose(best["best_objective"]["area_limit_um2"] / 1e6, row["budget_mm2"])
    assert row["dse_area_mm2"] <= row["budget_mm2"]
    assert row["synthesis_equivalent_mm2"] <= row["budget_mm2"]

for app, row in DATA["board_latencies"].items():
    text = (ROOT / row["source"]).read_text(encoding="utf-8-sig")
    # Re-read both timer halves directly from each selected original log.
    lines = re.findall(r"_(TIME(?:_RAW|_INPUT_PACK|_QUANTIZATION)?) .*?mode=(\w+) stage=(\w+) cycles_lo=(0x[0-9a-f]+) cycles_hi=(0x[0-9a-f]+) ms=([0-9.]+) freq_khz=(\d+)", text)
    assert len(lines) == len(row["measurements"])
    for tag, mode, stage, lo, hi, ms, frequency in lines:
        key = f"{tag}:{mode}:{stage}"
        cycles = int(hi, 16) * 2**32 + int(lo, 16)
        assert row["measurements"][key]["cycles"] == cycles
        assert row["measurements"][key]["ms"] == float(ms)
        assert 0 <= cycles / int(frequency) - float(ms) < .00101
    measured = row["measurements"]
    for key, value in measured.items():
        if key.startswith("TIME_RAW:"):
            suffix = key[len("TIME_RAW:"):]
            excluded = measured.get("TIME_INPUT_PACK:" + suffix, measured.get("TIME_QUANTIZATION:" + suffix))
            assert value["cycles"] - excluded["cycles"] == measured["TIME:" + suffix]["cycles"]
    assert measured["TIME:hw:total"]["cycles"] >= sum(v["cycles"] for k, v in measured.items() if k.startswith("TIME:hw:") and k != "TIME:hw:total")

rows = DATA["wami_tradeoff"]
assert [r["constraint_mm2"] for r in rows] == [1.8, 2.2, 3, 4, 8, 9, 10]
for row in rows:
    times = row["times"]
    for stage in ["total", "warp_image", "steepest_descent", "hessian"]:
        assert times["WAMI_TIME_RAW:" + stage]["cycles"] - times["WAMI_TIME_INPUT_PACK:" + stage]["cycles"] == times["WAMI_TIME:" + stage]["cycles"]
by_budget = {r["constraint_mm2"]: r for r in rows}


def total(row):
    return row["times"]["WAMI_TIME:total"]["ms"]


def residual(row):
    return total(row) - sum(row["times"]["WAMI_TIME:" + stage]["ms"] for stage in ["warp_image", "steepest_descent", "hessian"])


summary = dict(success=True, source_files_checked=len(DATA["provenance"]),
    paired_applications_checked=5, selected_tradeoff_points_checked=7,
    full_64bit_timer_arithmetic_checked=True,
    preparation_excluded_geomean=math.prod(r["adjusted_speedup"] for r in DATA["board_latencies"].values()) ** .2,
    full_elapsed_geomean=math.prod(r["raw_speedup"] for r in DATA["board_latencies"].values()) ** .2,
    wami_8_vs_4_slowdown_pct=100 * (total(by_budget[8]) / total(by_budget[4]) - 1),
    wami_10_vs_4_improvement_pct=100 * (1 - total(by_budget[10]) / total(by_budget[4])),
    wami_8_to_10_residual_improvement_ms=residual(by_budget[8]) - residual(by_budget[10]),
    limitations=DATA["timing_scope"], area_scope=DATA["area_scope"])
(ROOT / "data/board_20261031/validation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k not in ["limitations", "area_scope"]}, indent=2))
