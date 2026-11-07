# Single-column requirement-to-IP alternatives

Five alternatives for the paper's requirement-to-IP case study, in application
order: plate_roi, color_target, scan, wami, nightvision. Each PDF page
contains a 3.5-inch-wide figure with 8 pt monospaced text. Preview titles and the
width note sit outside the proposed figure.

The active manuscript uses alternative 1 (plate_roi) as a single-column
figure. The remaining alternatives are retained for later selection. The figures
are editable LaTeX listings, with no rasterized text.

Rebuild from the repository root:

```powershell
python scripts/make_ip_case_previews.py
```

Output: `output/pdf/ip-selection-single-column-previews.pdf`.

The accompanying source-manifests.json preserves all five manifests from the
same archived revision; source paths and original byte hashes are recorded.
The displayed descriptions, requirements, feature labels, and missing-capability
labels are abbreviated summaries. They are not verbatim execution logs. One
selected entry illustrates retrieval; no unrecorded candidate counts or rejected
entries are introduced. Selected IDs, gap counts and resource totals are checked
against the archived manifest during generation. Resource totals cover reusable
IP recommendations, not the complete deployed SoC. Requirement-analysis limits
are those in these manifests, distinct from the final DSE area budgets.
