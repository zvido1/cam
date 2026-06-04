"""Step 375I — Part 2 (KEYED): Stage 5e materiality stability replay.

Answers Q3: does `materiality` stay constant across N re-runs of Stage 5e on byte-identical
frozen input, or does it flip buckets?  Points the 375D-2 Track-B scaffold at lease_use_impact.py
instead of Stage 7.

READ-ONLY: writes only build_log/375I_q3_results.json; no edits to lease_use_impact.py or any
production path.  Code WRITES; Tzvi RUNS.

RUN (keyed machine):
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    git pull
    python "build_log\\_375i_part2.py"        # N=10 (matches 375D-2 Track-A K=10)
    python "build_log\\_375i_part2.py" 5      # lighter N if cost is a concern

Keys:  C:\\Users\\Owner\\OneDrive\\DoubleCheck\\doublecheck-api\\api_keys\\.env
Env:   DISABLE_OPENROUTER=1  (set below automatically)

Execution path: DIRECT ADAPTER — calls assess_use_impact() from cam.adapters.lease_review.lease_use_impact
directly; does NOT go through the Flask server.  Set PYTHONPATH to CAM root (done automatically below).

Cost: N × 3 evaluator calls (one batch per evaluator, each covering all 8 eligible LPs).
Default N=10 → 30 evaluator calls total.  Use N=5 for a lighter run.
"""
import os, sys, json
from collections import Counter, defaultdict

# ── Keys ──────────────────────────────────────────────────────────────────────
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED   = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
try:
    for line in open(KEYS_ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() in WANTED:
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
except FileNotFoundError:
    print(f"[375I-P2] WARNING: keys file not found at {KEYS_ENV} — evaluator calls will fail.", flush=True)

os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)

# ── Paths ──────────────────────────────────────────────────────────────────────
CAM_ROOT   = r"C:\Users\Owner\OneDrive\CAM"
FROZEN_RUN = os.path.join(
    CAM_ROOT,
    r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json",
)
OUT_JSON = os.path.join(CAM_ROOT, r"build_log\375I_q3_results.json")

if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

N = int(sys.argv[1]) if (len(sys.argv) > 1 and sys.argv[1].isdigit()) else 10

# ── Load frozen artifact ───────────────────────────────────────────────────────
with open(FROZEN_RUN, encoding="utf-8") as fh:
    data = json.load(fh)

use_profile       = data.get("use_profile")
perspective       = "tenant"

# Deep-copy the coverage_assessment once so each run starts from identical input.
import copy
base_coverage = data.get("coverage_assessment", [])

from cam.adapters.lease_review.lease_use_impact import _should_assess

eligible_ids = [
    (a.get("issue_area_id") or a.get("provision_id") or "?")
    for a in base_coverage
    if _should_assess(a)
]
print(f"[375I-P2] frozen run | eligible_lps={len(eligible_ids)} | N={N}", flush=True)
print(f"[375I-P2] eligible: {eligible_ids}", flush=True)

# ── Routing-relevance under the 375E design ────────────────────────────────────
# Under the 375E redesign the materiality bucket governs Risk routing.
# A "routing-relevant crossing" is one where materiality changes in a way
# that would change the routing outcome:
#   low  ↔ medium  — crosses into/out of the "medium+" tier
#   medium ↔ high  — crosses into/out of the "high" tier
#   not_applicable is its own tier
# Bucket-internal wobble (same bucket across runs) is lower-stakes.
_MAT_ORDER = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}

def _routing_bucket(mat):
    """Map materiality to a routing tier for the 375E anchor role."""
    return _MAT_ORDER.get((mat or "").lower(), -1)

def _crossing_type(vals):
    """Given a list of materiality values across runs, classify variance."""
    unique = set(v for v in vals if v)
    if len(unique) <= 1:
        return "stable"
    buckets = sorted(set(_routing_bucket(v) for v in unique))
    if max(buckets) - min(buckets) == 0:
        return "stable"
    # Any move across a tier boundary is routing-relevant
    if min(buckets) < 0:
        return "parse_error"
    # Is there a full swing (low↔high, skipping medium)?
    if min(buckets) == 1 and max(buckets) == 3:
        return "full_swing"
    return "routing_relevant_crossing"

# ── Replay loop ────────────────────────────────────────────────────────────────
from cam.adapters.lease_review.lease_use_impact import assess_use_impact

runs = []
per_lp_materiality = defaultdict(list)   # pid → [mat_run1, mat_run2, ...]
per_lp_confidence  = defaultdict(list)
per_lp_gap_impact  = defaultdict(list)

for run_i in range(1, N + 1):
    print(f"\n[375I-P2] ===== RUN {run_i}/{N} =====", flush=True)
    # Deep-copy so 5e can write use_impact onto the dicts without contaminating the next run
    ca_copy = copy.deepcopy(base_coverage)
    try:
        ca_out, meta = assess_use_impact(ca_copy, use_profile, perspective)
        status = "ok"
        stage_meta = meta
    except Exception as e:
        print(f"[375I-P2] assess_use_impact raised: {e}", flush=True)
        ca_out = ca_copy
        status = f"error: {e}"
        stage_meta = {}

    run_verdicts = {}
    for a in ca_out:
        pid = a.get("issue_area_id") or a.get("provision_id") or "?"
        if pid not in eligible_ids:
            continue
        ui = a.get("use_impact") or {}
        mat  = ui.get("materiality")
        conf = ui.get("confidence")
        gi   = ui.get("gap_impact")
        per_lp_materiality[pid].append(mat)
        per_lp_confidence[pid].append(conf)
        per_lp_gap_impact[pid].append(gi)
        run_verdicts[pid] = {"materiality": mat, "confidence": conf, "gap_impact": gi}

    runs.append({
        "run":          run_i,
        "status":       status,
        "stage_meta":   stage_meta,
        "verdicts":     run_verdicts,
    })
    print(f"[375I-P2] RUN {run_i} verdicts:", flush=True)
    for pid, v in run_verdicts.items():
        print(f"    {pid}: mat={v['materiality']}, conf={v['confidence']}, gi={v['gap_impact']}", flush=True)

# ── Stability analysis ─────────────────────────────────────────────────────────
print(f"\n[375I-P2] ===== STABILITY SUMMARY (across {N} runs) =====", flush=True)

per_lp_stability = {}
n_stable = 0
n_routing_crossing = 0
n_full_swing = 0

for pid in eligible_ids:
    mats  = per_lp_materiality[pid]
    confs = per_lp_confidence[pid]
    gis   = per_lp_gap_impact[pid]
    unique_mats  = set(m for m in mats if m)
    unique_confs = set(c for c in confs if c)
    unique_gis   = set(g for g in gis if g)
    crossing     = _crossing_type(mats)
    if crossing == "stable":
        n_stable += 1
    elif crossing == "full_swing":
        n_full_swing += 1
    else:
        n_routing_crossing += 1

    per_lp_stability[pid] = {
        "materiality_values":     mats,
        "unique_materiality":     sorted(unique_mats),
        "materiality_crossing":   crossing,
        "confidence_values":      confs,
        "unique_confidence":      sorted(unique_confs),
        "gap_impact_values":      gis,
        "unique_gap_impact":      sorted(unique_gis),
        "routing_relevant":       (crossing != "stable"),
    }
    flag = "  " if crossing == "stable" else "!!"
    print(f"  {flag} {pid}: materiality={sorted(unique_mats)} → {crossing}", flush=True)

# Key metric: analogue of 375D-2's "0 present↔absent crossings"
# Here: 0 routing-relevant materiality crossings = materiality is stable enough to anchor 375E
print(f"\n  Stable:                    {n_stable}/{len(eligible_ids)}")
print(f"  Routing-relevant crossing: {n_routing_crossing}/{len(eligible_ids)}")
print(f"  Full swing (low↔high):     {n_full_swing}/{len(eligible_ids)}")

result = {
    "harness":         "375I_part2_keyed_stability_replay",
    "step":            "375I",
    "frozen_run":      "lease_review_20260604_033046_52adbf",
    "N":               N,
    "execution_path":  "direct_adapter (assess_use_impact called directly, no Flask server)",
    "eligible_lps":    eligible_ids,
    "n_eligible":      len(eligible_ids),
    "stability_metric": (
        "routing-relevant materiality crossings: "
        f"{n_routing_crossing}/{len(eligible_ids)} — "
        "analogue of 375D-2's 'present↔absent crossings' metric"
    ),
    "summary": {
        "n_stable":            n_stable,
        "n_routing_crossing":  n_routing_crossing,
        "n_full_swing":        n_full_swing,
    },
    "per_lp_stability":   per_lp_stability,
    "runs":               runs,
    "Q3_verdict_template": (
        "FILL AFTER RUN: stable (n_routing_crossing=0) → materiality can anchor 375E; "
        "unstable → redesign must not rely on 5e materiality as-is"
    ),
}

json.dump(result, open(OUT_JSON, "w", encoding="utf-8"), indent=2)
print(f"\n[375I-P2] wrote {OUT_JSON}")
print("[375I-P2] Part 2 complete.")
