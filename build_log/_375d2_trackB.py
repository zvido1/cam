"""Step 375D-2 — Track B: candidate-generation / retention variance (SEPARATE from Track A).

Audits why one full Stage-7 replay produced 20 directionals not 26 — i.e. the fate of the six LPs that
vanished from that pass: LP-03, LP-06, LP-11, LP-17, LP-18, LP-24. Re-runs the REAL Pass-1 -> candidate
collection -> Pass-2 path N times and, per run, classifies each target LP:
  never_generated         — no Pass-1 evaluator set mismatch_flag for it,
  generated_not_candidate — flagged in Pass-1 but dropped before Pass-2 (would reveal a hidden filter),
  generated_pass2_rejected— entered Pass-2 but suppressed (confirmed==0) / verification_incomplete,
  in_final                — survived to a final directional finding.
This isolates candidate-SET variance from the Pass-2 VERIFICATION variance Track A measures — never blurred.

READ-ONLY: writes only build_log/375D2_trackB.json; no code/prompt/severity/routing change. Code WRITES; Tzvi RUNS.

RUN (keyed machine):
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375d2_trackB.py"        # default N=5 runs
    python "build_log\\_375d2_trackB.py" 8       # optional N runs

Cost: N x (3 Pass-1 + 3 Pass-2) calls (default 30). No upstream coverage/extraction re-run (frozen input).
"""
import os, sys, json
from collections import Counter, defaultdict

# ── Keys ──
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
try:
    for line in open(KEYS_ENV, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() in WANTED:
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
except FileNotFoundError:
    print(f"[375D2-B] WARNING: keys file not found at {KEYS_ENV} — provider calls will fail.", flush=True)
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

FROZEN_RUN = r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json"
OUT = os.path.join(CAM_ROOT, r"build_log\375D2_trackB.json")
PERSP = "tenant"
N = int(sys.argv[1]) if (len(sys.argv) > 1 and sys.argv[1].isdigit()) else 5
TARGETS = ["LP-03", "LP-06", "LP-11", "LP-17", "LP-18", "LP-24"]   # the six vanished in pass 4

from cam.adapters.lease_review.lease_synthesis import (
    _collect_flagged_lps, _build_evaluator_user_prompt, _call_single_evaluator, _EVALUATOR_LINEUP_PASS1,
    _collect_directional_candidates, _build_pass2_user_prompt, _call_pass2_evaluator, _EVALUATOR_LINEUP_PASS2,
    _build_pass2_directional_findings,
)

src = json.load(open(os.path.join(CAM_ROOT, FROZEN_RUN), encoding="utf-8"))
full_tenant_text = src["full_tenant_text"]
coverage_assessment = src["coverage_assessment"]
conflicts = src.get("conflicts", []) or []
flagged = _collect_flagged_lps(coverage_assessment, conflicts)
print(f"[375D2-B] frozen input | flagged_lps={len(flagged)} | runs={N} | targets={TARGETS}", flush=True)


def lp_in(target, lp_ids):
    return target in (lp_ids or [])


def pass1_flag_counts(evout, target):
    """How many Pass-1 evaluators set mismatch_flag=True for this target LP (candidate-generation signal)."""
    n = 0
    for role, out in evout.items():
        if not out.get("completed"):
            continue
        for item in ((out.get("result") or {}).get("cross_coverage_findings") or []):
            ids = item.get("lp_ids") or ([item.get("lp_id")] if item.get("lp_id") else [])
            if lp_in(target, ids) and item.get("mismatch_flag") is True:
                n += 1
                break
    return n


runs = []
fate_tally = {t: Counter() for t in TARGETS}
for run_i in range(1, N + 1):
    print(f"\n[375D2-B] ===== RUN {run_i}/{N} — Pass-1 + collect + Pass-2 =====", flush=True)
    # Pass-1 (real)
    prompt = _build_evaluator_user_prompt(flagged, full_tenant_text, PERSP, coverage_assessment)
    evout = {}
    for role, cfg in _EVALUATOR_LINEUP_PASS1.items():
        try:
            evout[role] = _call_single_evaluator(role, cfg, prompt)
        except Exception as e:
            evout[role] = {"role": role, "completed": False, "result": None, "error": str(e)}
    cands = _collect_directional_candidates(evout)
    cand_lpsets = [tuple(sorted(c.get("lp_ids") or [])) for c in cands]
    # Pass-2 (real) on the candidate set
    p2_prompt = _build_pass2_user_prompt([], [], cands, flagged, PERSP)
    p2out = {}
    for role, cfg in _EVALUATOR_LINEUP_PASS2.items():
        try:
            p2out[role] = _call_pass2_evaluator(role, cfg, p2_prompt)
        except Exception as e:
            p2out[role] = {"role": role, "completed": False, "verdicts": [], "error": str(e)}
    final = _build_pass2_directional_findings(cands, p2out)
    final_lps = {tuple(sorted(f.get("implicated_lps") or [])): f for f in final}

    per_target = {}
    for t in TARGETS:
        flags = pass1_flag_counts(evout, t)
        in_cand = any(lp_in(t, list(s)) for s in cand_lpsets)
        in_final = any(lp_in(t, list(k)) for k in final_lps)
        if not in_cand and flags == 0:
            fate = "never_generated"
        elif not in_cand and flags > 0:
            fate = "generated_not_candidate"     # flagged but dropped before Pass-2 (hidden filter?)
        elif in_cand and not in_final:
            fate = "generated_pass2_rejected"     # entered Pass-2, suppressed (confirmed==0 / incomplete)
        else:
            fate = "in_final"
        # if in final, record its severity/agreement + verification_incomplete (375C)
        fin = next((final_lps[k] for k in final_lps if lp_in(t, list(k))), None)
        per_target[t] = {"pass1_mismatch_flag_evaluators": flags, "in_candidate_set": in_cand,
                         "in_final": in_final, "fate": fate,
                         "final_agreement": (fin or {}).get("evaluator_agreement"),
                         "final_severity": (fin or {}).get("severity"),
                         "final_verification_incomplete": bool((fin or {}).get("verification_incomplete"))}
        fate_tally[t][fate] += 1

    runs.append({"run": run_i, "n_candidates": len(cands), "n_final_directional": len(final),
                 "pass1_completed": {r: bool(evout[r].get("completed")) for r in evout},
                 "pass2_completed": {r: bool(p2out[r].get("completed")) for r in p2out},
                 "targets": per_target})
    print("[375D2-B] RUN %d: candidates=%d final_directional=%d" % (run_i, len(cands), len(final)), flush=True)
    for t in TARGETS:
        pt = per_target[t]
        print("    %-7s flags=%d in_cand=%s in_final=%s -> %s" % (t, pt["pass1_mismatch_flag_evaluators"],
              pt["in_candidate_set"], pt["in_final"], pt["fate"]), flush=True)

result = {
    "harness": "375D2_trackB_candidate_generation_variance",
    "frozen_run": "lease_review_20260604_033046_52adbf",
    "n_runs": N, "targets": TARGETS,
    "n_candidates_per_run": [r["n_candidates"] for r in runs],
    "fate_tally_per_target": {t: dict(fate_tally[t]) for t in TARGETS},
    "runs": runs,
}
json.dump(result, open(OUT, "w", encoding="utf-8"), indent=2)
print("\n[375D2-B] ===== FATE SUMMARY (across %d runs) =====" % N, flush=True)
print("  candidate counts per run:", [r["n_candidates"] for r in runs], flush=True)
for t in TARGETS:
    print("  %-7s %s" % (t, dict(fate_tally[t])), flush=True)
print(f"\n[375D2-B] wrote {OUT}", flush=True)
