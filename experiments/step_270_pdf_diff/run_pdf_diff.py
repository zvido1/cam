"""Step 270 — Generate parallel artifact sets for v1.1.3 vs v1.1.4 visual diff.

Reads two existing pipeline_results.json files (one pre-bump, one post-bump)
and runs the production report generator + Synopsis PDF generator on each,
writing artifacts to:
  experiments/step_270_pdf_diff/pre_v1.1.3/
  experiments/step_270_pdf_diff/post_v1.1.4/

Read-only on production code. No pipeline re-runs. No API calls.
"""

import json
import os
import sys
from pathlib import Path

PROJECT = Path(r"C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "05 Lease Analyzer"))

# ── Inputs ────────────────────────────────────────────────────────────────
PRE_JSON = PROJECT / "experiments" / "coverage_variance_2026_04_28" / "00_fresh_run_pipeline_results.json"
POST_JSON = PROJECT / "experiments" / "step_268_t10_post_bump" / "pipeline_results.json"
TENANT_FILE = PROJECT / "05 Lease Analyzer" / "test_data" / "tenants" / "T-10_Negotiated_Tennant_Lease.docx"

assert PRE_JSON.exists(), PRE_JSON
assert POST_JSON.exists(), POST_JSON
assert TENANT_FILE.exists(), TENANT_FILE

# ── Outputs ───────────────────────────────────────────────────────────────
OUT_BASE = PROJECT / "experiments" / "step_270_pdf_diff"
PRE_OUT = OUT_BASE / "pre_v1.1.3"
POST_OUT = OUT_BASE / "post_v1.1.4"
PRE_OUT.mkdir(parents=True, exist_ok=True)
POST_OUT.mkdir(parents=True, exist_ok=True)

# Load both JSONs
with open(PRE_JSON, encoding="utf-8") as f:
    pre_results = json.load(f)
with open(POST_JSON, encoding="utf-8") as f:
    post_results = json.load(f)


def report_label(results: dict) -> str:
    return (
        f"mode={results.get('mode')!r} "
        f"run_id={results.get('run_id')!r} "
        f"tenant_file={results.get('tenant_file')!r}"
    )


print(f"[setup] PRE  : {report_label(pre_results)}")
print(f"[setup] POST : {report_label(post_results)}")
print(f"[setup] tenant file: {TENANT_FILE.name}")
print()

# ── Imports ───────────────────────────────────────────────────────────────
from cam.adapters.lease_review.lease_report_generator import generate_outputs
from app.summary_generator import generate_combined_summary_pdf  # type: ignore[import]


def run_one(label: str, results: dict, out_dir: Path) -> dict:
    print(f"=== {label} ===", flush=True)
    print(f"[{label}] generate_outputs(...) → {out_dir}", flush=True)
    info = generate_outputs(
        tenant_file_path=str(TENANT_FILE),
        results=results,
        output_dir=str(out_dir),
    )
    # Save the dashboard JSON alongside the artifacts so the directory is
    # self-contained for visual diffing.
    with open(out_dir / "pipeline_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    # Synopsis PDF (Mode A's lawyer-facing combined report).
    # Mode C results don't have provisions[] / deviations[], but the
    # Synopsis generator handles that — it iterates the tenant_results
    # list and surfaces what's there. For Mode C runs the deviations
    # section is empty; for Mode A the full layout populates.
    synopsis_path = out_dir / "Lease_Analysis_Synopsis.pdf"
    minimal_job = {
        "job_id": f"step_270_{label}",
        "created_at": results.get("timestamp", ""),
        "resolutions": {},
    }
    print(f"[{label}] generate_combined_summary_pdf(...) → {synopsis_path.name}", flush=True)
    try:
        out_path = generate_combined_summary_pdf(
            job=minimal_job,
            tenant_results=[results],
            output_path=str(synopsis_path),
        )
        info["synopsis_pdf"] = out_path
        print(f"[{label}] Synopsis PDF: {out_path}", flush=True)
    except Exception as e:
        print(f"[{label}] Synopsis PDF FAILED: {type(e).__name__}: {e}", flush=True)
        info["synopsis_pdf_error"] = f"{type(e).__name__}: {e}"

    print(f"[{label}] info: {json.dumps(info, indent=2, default=str)}", flush=True)
    print(flush=True)
    return info


pre_info = run_one("PRE  v1.1.3", pre_results, PRE_OUT)
post_info = run_one("POST v1.1.4", post_results, POST_OUT)

# ── Final listing ─────────────────────────────────────────────────────────
def list_dir(d: Path) -> list[tuple[str, int]]:
    return sorted([(p.name, p.stat().st_size) for p in d.iterdir() if p.is_file()])


print("=" * 70)
print("FILE LISTINGS")
print("=" * 70)
for label, d in (("PRE  v1.1.3", PRE_OUT), ("POST v1.1.4", POST_OUT)):
    print(f"\n[{label}]  {d}")
    for name, size in list_dir(d):
        print(f"  {size:>10}  {name}")

# Save manifest
manifest = {
    "pre_v1.1.3": {
        "out_dir": str(PRE_OUT.relative_to(PROJECT)),
        "source_pipeline_results": str(PRE_JSON.relative_to(PROJECT)),
        "files": list_dir(PRE_OUT),
        "report_info": pre_info,
    },
    "post_v1.1.4": {
        "out_dir": str(POST_OUT.relative_to(PROJECT)),
        "source_pipeline_results": str(POST_JSON.relative_to(PROJECT)),
        "files": list_dir(POST_OUT),
        "report_info": post_info,
    },
    "tenant_file": str(TENANT_FILE.relative_to(PROJECT)),
}
with open(OUT_BASE / "manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, default=str)

print(f"\nManifest written to {OUT_BASE / 'manifest.json'}", flush=True)
