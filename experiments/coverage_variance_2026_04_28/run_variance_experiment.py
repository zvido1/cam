"""Coverage Exposure Variance Experiment — execution harness.

Methodology: Docs/Coverage_Variance_Experiment.md (pre-registered 2026-04-28).

Steps performed by this script:
  1. Load API keys from C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env
  2. Trigger a fresh Mode C local run on T-10_Negotiated_Tennant_Lease.docx.
  3. Identify model-path coverage assessments (exposure_source == "model").
  4. For each model-path assessment, replay the EXACT same exposure call 3 times.
  5. Save all outputs (fresh run + 3 repeats per call) under
     experiments/coverage_variance_2026_04_28/.
  6. Run mechanical diff: classification / evidence / wording variance.
  7. Print outcome (A / B / C / D) with justification.

This script does NOT modify cam/core/. It does not modify production code.
It only invokes existing public adapter entry points.
"""

import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

# ── 1. Load API keys ───────────────────────────────────────────────────────
KEYS_ENV = Path(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")
with open(KEYS_ENV, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

assert os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY missing after load"
print(f"[setup] API keys loaded. OPENAI key length: {len(os.environ['OPENAI_API_KEY'])}", flush=True)

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(r"C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "05 Lease Analyzer"))

OUT_DIR = PROJECT_ROOT / "experiments" / "coverage_variance_2026_04_28"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEMO_LEASE = PROJECT_ROOT / "05 Lease Analyzer" / "test_data" / "tenants" / "T-10_Negotiated_Tennant_Lease.docx"
assert DEMO_LEASE.exists(), f"Demo lease not found: {DEMO_LEASE}"

# ── 2. Fresh Mode C run ────────────────────────────────────────────────────
from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

print("\n[step 2] Triggering fresh Mode C run on T-10...", flush=True)
fresh_start = time.time()
fresh_result = run_lease_coverage_only(
    tenant_path=str(DEMO_LEASE),
    run_id="lease_variance_2026_04_28_fresh",
)
fresh_elapsed = time.time() - fresh_start
print(f"[step 2] Fresh run complete in {fresh_elapsed:.1f}s", flush=True)

# Persist the full fresh result for audit
with open(OUT_DIR / "00_fresh_run_pipeline_results.json", "w", encoding="utf-8") as f:
    json.dump(fresh_result, f, indent=2, default=str)

coverage_assessment = fresh_result.get("coverage_assessment", [])
print(f"[step 2] coverage_assessment has {len(coverage_assessment)} entries", flush=True)

# ── 3. Identify model-path calls ───────────────────────────────────────────
model_path_calls = [a for a in coverage_assessment if a.get("exposure_source") == "model"]
print(f"\n[step 3] Model-path calls: {len(model_path_calls)}", flush=True)
for a in model_path_calls:
    print(
        f"  - {a.get('issue_area_id')} | state={a.get('coverage_state')} "
        f"| mat={a.get('materiality')} | reason={a.get('exposure_reason_code')}",
        flush=True,
    )

# Save the original model-path inputs (the assessment dicts BEFORE exposure was added)
# We need the pre-exposure dicts to replay. Reconstruct them by stripping exposure_* fields.
EXPOSURE_FIELDS = {
    "exposure_statement",
    "exposure_source",
    "exposure_reason_code",
    "exposure_confidence_note",
    "exposure_elements_used",
    "exposure_perspective",
}


def strip_exposure(a: dict) -> dict:
    return {k: v for k, v in a.items() if k not in EXPOSURE_FIELDS}


# ── 4. Replay each model-path call 3× ──────────────────────────────────────
from cam.adapters.lease_review.lease_exposure import _build_model_exposure

REPEATS = 3
all_replays = {}  # {issue_area_id: [repeat0, repeat1, repeat2]}

print(f"\n[step 4] Replaying each model-path call {REPEATS}× (total {len(model_path_calls) * REPEATS} calls)...", flush=True)

cfg = {"perspective": "tenant"}  # match production default

for assessment in model_path_calls:
    pid = assessment.get("issue_area_id", "UNKNOWN")
    reason_code = assessment.get("exposure_reason_code", "high_materiality")

    # Capture the EXACT input dict that the model call sees.
    pre_exposure = strip_exposure(assessment)

    repeats = []
    for i in range(REPEATS):
        # Pass a deep copy so the function can't mutate the canonical input.
        input_copy = deepcopy(pre_exposure)
        t0 = time.time()
        out = _build_model_exposure(input_copy, cfg, reason_code)
        dt = time.time() - t0
        out["_replay_index"] = i
        out["_replay_elapsed_sec"] = round(dt, 3)
        repeats.append(out)
        print(
            f"  [{pid} repeat {i}] source={out.get('exposure_source')} "
            f"len={len(out.get('exposure_statement',''))} {dt:.1f}s",
            flush=True,
        )

    all_replays[pid] = {
        "input": pre_exposure,
        "repeats": repeats,
    }

    # Per-call file dump
    with open(OUT_DIR / f"replay_{pid}.json", "w", encoding="utf-8") as f:
        json.dump(all_replays[pid], f, indent=2, default=str)

# Combined dump
with open(OUT_DIR / "all_replays.json", "w", encoding="utf-8") as f:
    json.dump(all_replays, f, indent=2, default=str)

# ── 5. Mechanical diff ─────────────────────────────────────────────────────
print("\n[step 5] Mechanical diff per call:\n", flush=True)


def normalize_text(s: str) -> str:
    return " ".join((s or "").lower().split())


report_lines = []
classification_variance_calls = []
evidence_variance_calls = []
wording_variance_calls = []
no_variance_calls = []

for pid, data in all_replays.items():
    repeats = data["repeats"]
    inp = data["input"]

    # Classification variance: did exposure_source change? (e.g. one repeat fell back to schema)
    sources = [r.get("exposure_source") for r in repeats]
    # The exposure layer doesn't re-classify coverage_state from inside _build_model_exposure;
    # coverage_state and materiality are inputs. The classification axis at the exposure-layer
    # boundary is exposure_source (model vs schema_fallback) and exposure_reason_code.
    reasons = [r.get("exposure_reason_code") for r in repeats]
    confs = [r.get("exposure_confidence_note") for r in repeats]

    # Evidence/element variance: same elements_used picked across repeats?
    elements = [tuple(r.get("exposure_elements_used") or []) for r in repeats]

    # Wording variance: exposure_statement text differs?
    statements = [r.get("exposure_statement", "") for r in repeats]
    statements_norm = [normalize_text(s) for s in statements]

    classification_diff = len(set(sources)) > 1 or len(set(reasons)) > 1
    evidence_diff = len(set(elements)) > 1
    wording_diff = len(set(statements_norm)) > 1

    if classification_diff:
        classification_variance_calls.append(pid)
    elif evidence_diff:
        evidence_variance_calls.append(pid)
    elif wording_diff:
        wording_variance_calls.append(pid)
    else:
        no_variance_calls.append(pid)

    report_lines.append(f"=== {pid} ===")
    report_lines.append(f"  input.coverage_state    : {inp.get('coverage_state')}")
    report_lines.append(f"  input.materiality       : {inp.get('materiality')}")
    report_lines.append(f"  input.elements_missing  : {inp.get('elements_missing')}")
    report_lines.append(f"  input.elements_found    : {inp.get('elements_found')}")
    report_lines.append(f"  exposure_source(s)      : {sources}")
    report_lines.append(f"  exposure_reason_code(s) : {reasons}")
    report_lines.append(f"  elements_used per repeat: {elements}")
    report_lines.append(f"  classification_diff     : {classification_diff}")
    report_lines.append(f"  evidence_diff           : {evidence_diff}")
    report_lines.append(f"  wording_diff            : {wording_diff}")
    for i, stmt in enumerate(statements):
        report_lines.append(f"  repeat[{i}]: {stmt!r}")
    report_lines.append("")

print("\n".join(report_lines))

# ── 6. Outcome determination ───────────────────────────────────────────────
print("\n" + "=" * 70, flush=True)
print("OUTCOME DETERMINATION", flush=True)
print("=" * 70, flush=True)

if classification_variance_calls:
    outcome = "D"
    justification = (
        f"At least one call ({', '.join(classification_variance_calls)}) produced "
        "different exposure_source / exposure_reason_code across repeats — i.e. the "
        "system classified the same input differently on different runs."
    )
elif evidence_variance_calls:
    outcome = "C"
    justification = (
        f"No classification variance, but {len(evidence_variance_calls)} call(s) "
        f"({', '.join(evidence_variance_calls)}) cited different elements_used "
        "across repeats — same conclusion via different evidence."
    )
elif wording_variance_calls:
    outcome = "B"
    justification = (
        f"No classification or evidence variance; {len(wording_variance_calls)} call(s) "
        "differed only in exposure_statement phrasing."
    )
else:
    outcome = "A"
    justification = (
        "All 3 repeats produced identical classifications, identical evidence, "
        "and substantively identical statements across all calls."
    )

summary = {
    "outcome": outcome,
    "justification": justification,
    "model_path_calls": [a.get("issue_area_id") for a in model_path_calls],
    "n_calls": len(model_path_calls),
    "n_repeats_per_call": REPEATS,
    "n_total_replays": len(model_path_calls) * REPEATS,
    "classification_variance_calls": classification_variance_calls,
    "evidence_variance_calls": evidence_variance_calls,
    "wording_variance_calls": wording_variance_calls,
    "no_variance_calls": no_variance_calls,
}

with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

with open(OUT_DIR / "report.txt", "w", encoding="utf-8") as f:
    f.write("Coverage Exposure Variance Experiment — Mechanical Diff Report\n")
    f.write("Date: 2026-04-28\n")
    f.write("Lease: T-10_Negotiated_Tennant_Lease.docx (fresh Mode C run)\n")
    f.write(f"Model: openai:gpt-5.2 (production exposure-layer config)\n")
    f.write(f"Calls: {len(model_path_calls)} model-path × {REPEATS} repeats = "
            f"{len(model_path_calls) * REPEATS}\n\n")
    f.write("\n".join(report_lines))
    f.write("\n\nOUTCOME: " + outcome + "\n")
    f.write(justification + "\n")

print(f"\nOutcome: {outcome}", flush=True)
print(f"Justification: {justification}", flush=True)
print(f"\nFull artifacts in: {OUT_DIR}", flush=True)
