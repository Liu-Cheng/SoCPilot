"""Freeze checked board logs, selected DSE records, and synthesis-area provenance.

Run once with the local experiment archive available. Plotting thereafter only
uses the portable copies under data/board_20261031 and experiment_results.json.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = Path(r"D:\download\5.experiment")
WORK = Path(r"D:\work")
DEST = ROOT / "data/board_20261031"
DEST.mkdir(parents=True, exist_ok=True)
provenance = []


def freeze(path, name=None):
    path = Path(path)
    target = DEST / (name or path.name)
    shutil.copyfile(path, target)
    provenance.append(dict(file=str(target.relative_to(ROOT)).replace("\\", "/"),
                           original=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return target


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def times(path, prefix):
    text = Path(path).read_text(encoding="utf-8-sig")
    result = {}
    pattern = rf"^{prefix}_(TIME(?:_RAW|_INPUT_PACK|_QUANTIZATION)?) .*?mode=(\w+) stage=(\w+) cycles_lo=(0x[0-9a-f]+) cycles_hi=(0x[0-9a-f]+) ms=([0-9.]+) freq_khz=(\d+)"
    for tag, mode, stage, lo, hi, ms, freq in re.findall(pattern, text, re.M):
        cycles = int(hi, 16) * 2**32 + int(lo, 16)
        row = dict(cycles=cycles, ms=float(ms), frequency_khz=int(freq))
        assert 0 <= cycles / int(freq) - float(ms) < .00101
        key = f"{tag}:{mode}:{stage}"
        assert key not in result
        result[key] = row
    assert result
    for key, row in result.items():
        if key.startswith("TIME_RAW:"):
            tail = key.split(":", 1)[1]
            excluded = result.get("TIME_INPUT_PACK:" + tail, result.get("TIME_QUANTIZATION:" + tail))
            assert excluded is not None
            assert row["cycles"] - excluded["cycles"] == result["TIME:" + tail]["cycles"]
    return result


specs = [
    ("plate_recognition", "plate_result.DAT", "PLATE", "Ariane", ["morphology_close"],
     EXPERIMENT / "2.plate_ariane/plate_new/plate_new_img1_release/configs/best_dse_vivado.json",
     WORK / "plate_new_results_20261027/area_summary.json"),
    ("recognition", "recognition_leon3.DAT", "RECOGNITION", "LEON3", ["bgr_to_hsv", "dilate_mask"],
     EXPERIMENT / "4.wami_all_bits_20261030/board_files/batch_20261030/recognition_release/board_files/configs/best_dse_vivado.json",
     EXPERIMENT / "4.wami_all_bits_20261030/native90/recognition/area_summary.json"),
    ("scan", "scan_leon3.DAT", "SCAN", "LEON3", ["scan_adaptive_threshold"],
     EXPERIMENT / "3.scan_leon3/scan/scan_img1_release/configs/best_dse_vivado.json", None),
    ("wami", "wami_ibex.DAT", "WAMI", "Ibex", ["hessian", "warp_image"],
     EXPERIMENT / "4.wami_all_bits_20261030/board_files/p030/configs/best_dse_vivado.json", None),
    ("nightvision", "nightvision_ariane_new.DAT", "NIGHTVISION", "Ariane", ["conv2d"],
     EXPERIMENT / "1.nightvision_ariane/experiment_results/nightvision_img1_release/configs/best_dse_vivado.json",
     WORK / "nightvision_90nm_result_5b7585ef_20261026/area_summary.json"),
]
scan = load(WORK / "reports/Scan_DSE_FPGA_native90_20261027.json")
wami_areas_path = freeze(WORK / "reports/WAMI_all_area_tradeoff_20261030.json")
wami_areas = load(wami_areas_path)
wami3 = next(r for r in wami_areas["rows"] if r["point"] == "p030")
results = load(ROOT / "data/experiment_results.json")
results["source_note"] = "Updated from frozen 2026-10-31 board logs and exact selected DSE configurations; earlier automation/IP-selection records retained."
results["board_latencies"] = {}
results["hotspots"] = []
results["selected_soc_configs"] = []
stages = {"morphology_close": "close", "scan_adaptive_threshold": "adaptive_threshold"}
for app, filename, prefix, cpu, accelerators, best_path, area_path in specs:
    path = freeze(EXPERIMENT / "0.result" / filename)
    measurements = times(path, prefix)
    best = load(freeze(best_path, app + "_best_dse_vivado.json"))
    if area_path:
        area = load(freeze(area_path, app + "_area_summary.json"))
    elif app == "scan":
        area = scan["native90"]
        compact = DEST / "scan_area_summary.json"
        compact.write_text(json.dumps(area, indent=2), encoding="utf-8")
        provenance.append(dict(file=str(compact.relative_to(ROOT)).replace("\\", "/"),
                               original=str(WORK / "reports/Scan_DSE_FPGA_native90_20261027.json") + "#/native90",
                               sha256=hashlib.sha256(compact.read_bytes()).hexdigest()))
    else:
        area = dict(total_area_mm2=wami3["native90_mm2"])
    objective = best["best_objective"]
    params = best["params"]
    assert objective["Valid"]
    assert params["CPU_type"] == {"Ariane": 0, "Ibex": 1, "LEON3": 2}[cpu]
    dse_area = objective["total_area_um2"] / 1e6
    budget = objective["area_limit_um2"] / 1e6
    if app == "wami":
        assert math.isclose(dse_area, wami3["dse_area_45nm_mm2"])
        assert all(params[k] == v for k, v in wami3["params"].items())
    cpu_time = measurements["TIME:cpu:total"]["ms"]
    adjusted = measurements["TIME:hw:total"]["ms"]
    raw = measurements.get("TIME_RAW:hw:total", measurements["TIME:hw:total"])["ms"]
    results["board_latencies"][app] = dict(cpu_ms=cpu_time, accelerated_ms=adjusted,
        raw_accelerated_ms=raw, adjusted_speedup=cpu_time / adjusted, raw_speedup=cpu_time / raw,
        measurements=measurements, source=str(path.relative_to(ROOT)).replace("\\", "/"))
    for kernel in accelerators:
        stage = stages.get(kernel, kernel)
        sw, hw = measurements[f"TIME:cpu:{stage}"]["ms"], measurements[f"TIME:hw:{stage}"]["ms"]
        results["hotspots"].append(dict(application=app, kernel=kernel, cpu_ms=sw,
            hardware_ms=hw, speedup=sw / hw, cpu_share_pct=100 * sw / cpu_time))
    results["selected_soc_configs"].append(dict(application=app, cpu=cpu,
        budget_mm2=budget, dse_area_mm2=dse_area, synthesis_equivalent_mm2=area["total_area_mm2"] / 4,
        params=params, accelerators=accelerators, source_dse=app + "_best_dse_vivado.json"))

trade = load(freeze(EXPERIMENT / "0.result/trade_off_summary.json"))
for name in ["trade_off.txt", "trade_off_80_90.DAT"]:
    freeze(EXPERIMENT / "0.result" / name)
selected = [r for r in trade["rows"] if r["constraint_mm2"] in [1.8, 2.2, 3, 4, 8, 9, 10]]
assert len(selected) == 7
for row in selected:
    matching = next(r for r in wami_areas["rows"] if r["point"] == row["point"])
    row["dse_area_mm2"] = matching["dse_area_45nm_mm2"]
    row["synthesis_equivalent_mm2"] = matching["geometric45_mm2"]
    assert row["params"] == matching["params"]
    assert row["dse_area_mm2"] <= row["constraint_mm2"]
results["wami_tradeoff"] = selected
results["timing_scope"] = {"wami": "Input conversion/packing subtracted from primary time, retained in raw time; output unpack, cache synchronization, DMA and polling retained.",
    "nightvision": "Input quantization subtracted from primary time, retained in raw time; DMA packing, buffer clearing, output unpack and cache synchronization retained.",
    "other_applications": "Full elapsed time, including data preparation.",
    "verification": "All supplied board records report reference verification unchecked. Fixed-point output signatures do not establish original-float equivalence."}
results["area_scope"] = "Synthesis-derived cell area normalized to a common 45nm-equivalent basis, including standard cells and SRAM macros once; only 1000KiB application RAM excluded. Not actual 45nm synthesis or post-route die area."
results["provenance"] = provenance
(ROOT / "data/experiment_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
print("Board adjusted geometric mean", math.prod(r["adjusted_speedup"] for r in results["board_latencies"].values()) ** .2)
print("Board full-elapsed geometric mean", math.prod(r["raw_speedup"] for r in results["board_latencies"].values()) ** .2)
for row in results["selected_soc_configs"]:
    print(row["application"], row["cpu"], row["budget_mm2"], row["dse_area_mm2"], row["synthesis_equivalent_mm2"])
