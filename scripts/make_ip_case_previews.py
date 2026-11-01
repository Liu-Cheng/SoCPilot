"""Build five editable, single-column requirement-to-IP case previews.

The descriptions and structured requirements below are display summaries, not
verbatim agent transcripts. Selected IDs, gaps and resource totals are checked
against the archived manifests. The active manuscript is left unchanged while
the author selects a case.
"""

from pathlib import Path
import hashlib
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "previews/ip-selection"
OUTPUT = ROOT / "output/pdf"
SUMMARY = json.loads((ROOT / "data/requirement_ip_selection.json").read_text(encoding="utf-8"))
WIDTH = 48

DISPLAY = {
    "plate_recognition": {
        "title": "License-plate localization",
        "description": [
            '"Parking-entrance plate localization:',
            " one MIPI CSI-2 camera; I2C sensor setup;",
            ' Ethernet masks/regions to parking host."',
        ],
        "requirements": [
            "interfaces: CSI-2 pixels / I2C / Ethernet",
            "storage: ping-pong frames / local SRAM",
            "fabric: AXI burst / AXI-Lite control",
            "debug: cycle and transaction counters",
        ],
        "need": "camera pixels + frame markers",
        "example_id": "mipi_csi2",
        "features": "pixel stream / frame synchronization",
        "feature_checks": ["pixel stream", "frame synchronization"],
        "gaps": [],
    },
    "recognition": {
        "title": "Color-based object recognition",
        "description": [
            '"Industrial green-marker localization:',
            " BGR frames arrive over SPI; target",
            ' coordinates are reported over UART."',
        ],
        "requirements": [
            "interfaces: SPI slave input / UART output",
            "storage: 320x240 BGR frame / local SRAM",
            "control: AXI-Lite start / done / status",
            "debug: JTAG access",
        ],
        "need": "target coordinates + configuration",
        "example_id": "uart",
        "features": "serial / short-distance link",
        "feature_checks": ["serial", "short-distance"],
        "gaps": ["SPI slave frame ingress", "JTAG debug", "SRAM scratchpad access"],
    },
    "scan": {
        "title": "Document scanning",
        "description": [
            '"USB document-cleanup device: receive',
            " RGB pages from a host; return binary",
            ' masks and document bounding boxes."',
        ],
        "requirements": [
            "interfaces: USB device / page-transfer DMA",
            "storage: strided page buffers / local SRAM",
            "control: AXI-Lite start / done / status",
            "debug: cycle and transaction counters",
        ],
        "need": "page-processing latency measurement",
        "example_id": "performance_counter",
        "features": "cycle / transaction counters",
        "feature_checks": ["cycle counter", "transaction counter"],
        "gaps": ["USB device controller", "page-transfer DMA", "page/frame buffering"],
    },
    "wami": {
        "title": "Wide-area motion imagery",
        "description": [
            '"Airborne foreground-detection payload:',
            " raw CSI-2 camera input, I2C sensor setup,",
            ' Ethernet masks/status to mission host."',
        ],
        "requirements": [
            "I/O: raw CSI-2 / I2C / Ethernet",
            "storage: current/reference frames / DDR",
            "fabric: frame-ordered DMA / AXI / SRAM",
            "control/debug: AXI-Lite / event tracing",
        ],
        "need": "camera sensor-register control",
        "example_id": "camera_i2c_ctrl",
        "features": "I2C/SCCB / exposure control",
        "feature_checks": ["i2c", "sccb", "exposure control"],
        "gaps": ["raw MIPI CSI-2 receiver", "frame-ordered streaming DMA"],
    },
    "nightvision": {
        "title": "Night-vision enhancement",
        "description": [
            '"Dual-sensor night-viewing terminal:',
            " visible + IR frames over two CSI-2 inputs;",
            ' SPI panel commands; local fused display."',
        ],
        "requirements": [
            "interfaces: 2x CSI-2 / I2C / SPI panel",
            "video: paired frames / local display",
            "fabric: AXI burst / SRAM / AXI-Lite",
            "debug: fusion/display latency counters",
        ],
        "need": "sensor exposure/gain configuration",
        "example_id": "i2c",
        "features": "two-wire / multi-slave control",
        "feature_checks": ["two - wire", "multi - slave"],
        "gaps": ["dual MIPI CSI-2 reception", "SPI panel control", "paired-frame buffering"],
    },
}


def get_manifest(case):
    app = case["application"]
    cache = ROOT / "build/ip-case-source" / (app + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if app == "plate_recognition":
        return json.loads((ROOT / "data/ip_selection_case_study.json").read_text(encoding="utf-8"))["manifest"]
    source = SUMMARY["source"]
    command = ["ssh", "-p", "20024", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
               "huwanshan@" + source["host"],
               f"git -C {source['repository']} show {source['revision']}:{case['source_path']}"]
    raw = subprocess.check_output(command, timeout=45)
    assert hashlib.sha256(raw).hexdigest() == case["source_sha256"]
    return json.loads(raw)


def array_lines(key, values):
    # Wrap between complete entries so an IP/capability stays on one line.
    lines = []
    current = key + ": ["
    for index, value in enumerate(values):
        entry = value + ("," if index < len(values) - 1 else "]")
        separator = "" if current.endswith("[") else " "
        if len(current + separator + entry) > WIDTH:
            lines.append(current)
            current = "  " + entry
        else:
            current += separator + entry
    lines.append(current if values else current + "]")
    return lines


def listing(case, manifest):
    app = case["application"]
    display = DISPLAY[app]
    ips = manifest["selected_reusable_ips"]
    ids = [ip["id"] for ip in ips]
    assert ids == [ip["id"] for ip in case["selected_ips"]]
    unmatched = manifest["unmatched_requirements"]
    assert len(unmatched) == len(display["gaps"]) == len(case["missing_capabilities"])
    example = next(ip for ip in ips if ip["id"] == display["example_id"])
    assert all(feature in example["features"].lower() for feature in display["feature_checks"])
    assert all(ip["deployment_status"] == "recommendation_only" for ip in ips)
    area = manifest["area_accounting"]["reusable_ip_area_mm2"]
    power = manifest["power_accounting"]["reusable_ip_power_mw"]
    assert abs(area - sum(ip["area_mm2"] for ip in ips)) < 1e-9
    assert abs(power - sum(ip["power_mw"] for ip in ips)) < 1e-9
    area_limit = manifest["constraints"]["area_limit_mm2"]
    power_limit = manifest["constraints"]["power_limit_mw"]
    assert area <= area_limit and power <= power_limit
    lines = [
        "# 1. SoC description (abridged)",
        *display["description"],
        "technology: 28nm; clock target: 75 MHz", "",
        "# 2. Structured requirements (abridged)",
        *display["requirements"], "",
        "# 3. Library lookup (one example)",
        "need: " + display["need"],
        "category: " + example["category"],
        "IP: " + example["id"],
        "features: " + display["features"], "",
        "# 4. Exported recommendation (abridged)",
        *array_lines("selected", ids),
        *array_lines("unmatched", display["gaps"]),
        f"IP area: {area:g} mm2 (limit: {area_limit:g} mm2)",
        f"IP power: {power:g} mW (limit: {power_limit:g} mW)",
        "status: recommendation_only",
    ]
    assert max(map(len, lines)) <= WIDTH, (app, max(map(len, lines)))
    return "\n".join(lines) + "\n"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    archive_path = DEST / "source-manifests.json"
    if archive_path.exists():
        archive = json.loads(archive_path.read_text(encoding="utf-8"))
        manifests = archive["manifests"]
    else:
        manifests = {case["application"]: get_manifest(case) for case in SUMMARY["cases"]}
        archive = {"source": SUMMARY["source"],
                   "provenance": [{k: c[k] for k in ("application", "source_path", "source_sha256")}
                                  for c in SUMMARY["cases"]],
                   "manifests": manifests}
        archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pages = []
    for index, case in enumerate(SUMMARY["cases"], start=1):
        app = case["application"]
        text = listing(case, manifests[app])
        (DEST / (app + ".txt")).write_text(text, encoding="utf-8")
        title = app.replace("_", r"\_")
        page = rf"""\noindent{{\sffamily\color{{CaseBlue}}\bfseries\fontsize{{11}}{{13}}\selectfont {index:02d}\quad\texttt{{{title}}}}}\par
\vspace{{3pt}}
\noindent{{\small {DISPLAY[app]['title']}}}\par
\vspace{{7pt}}
\lstinputlisting[style=ipcase]{{previews/ip-selection/{app}.txt}}
\vspace{{5pt}}
\noindent{{\footnotesize\textbf{{Case {index}.}} An abridged view of the recorded SoC description, structured requirements, one selected library entry, and exported IP recommendations. Resource totals cover reusable IPs only.}}\par
\vspace{{9pt}}
\noindent{{\sffamily\fontsize{{7}}{{8.5}}\selectfont\color{{CaseGray}}Single-column preview: 3.5 in wide; code: 8 pt.}}
"""
        pages.append(page)
        print(f"{app}: {len(text.splitlines())} lines; {len(case['selected_ips'])} IPs; "
              f"{len(case['missing_capabilities'])} unmet capabilities")
    document = r"""\documentclass[10pt]{article}
\usepackage[T1]{fontenc}
\usepackage{times}
\usepackage[paperwidth=4.1in,paperheight=6.5in,textwidth=3.5in,top=0.25in,bottom=0.25in,centering]{geometry}
\usepackage{xcolor,listings}
\definecolor{CaseBlue}{HTML}{226A9D}
\definecolor{CaseGray}{HTML}{69717A}
\definecolor{CaseOrange}{HTML}{AD5C2D}
\lstdefinestyle{ipcase}{
  language={},
  morecomment={[l]{\#}},
  basicstyle=\ttfamily\fontsize{8}{9.2}\selectfont,
  commentstyle={\color{CaseBlue}\bfseries},
  emph={unmatched},emphstyle={\color{CaseOrange}\bfseries},
  numbers=none,columns=fullflexible,keepspaces=true,
  showstringspaces=false,breaklines=false,linewidth=\linewidth,
  frame=single,framerule=0.35pt,
  rulecolor={\color[HTML]{91AEC3}},
  backgroundcolor={\color[HTML]{F5F7F9}},
  xleftmargin=5pt,xrightmargin=5pt,framesep=4pt,
  aboveskip=0pt,belowskip=0pt
}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\begin{document}
""" + "\n\\newpage\n".join(pages) + "\n\\end{document}\n"
    (DEST / "ip-selection-single-column-previews.tex").write_text(document, encoding="utf-8")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                    "-output-directory=output/pdf", (DEST.relative_to(ROOT) / "ip-selection-single-column-previews.tex").as_posix()],
                   cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
