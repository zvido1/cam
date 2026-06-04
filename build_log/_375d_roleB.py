"""Step 375D — Harness B: targeted Pass-2 role-B (gpt-5.4) reproducibility.

Goal: separate "GPT-5.4 broadly noisy" from "this finding is genuinely borderline". For a representative
set of persistent directional candidates (Risk-flippers / stable-unanimous / stable-2-1), call ONLY the
Pass-2 directional verification step for role B (gpt-5.4) K times each on the IDENTICAL candidate input
(the same prompt the pipeline builds), and tally verdict + integrity outcomes.

Calls the REAL pipeline code path (Pass-1 once to obtain the frozen candidate set, then
_build_pass2_user_prompt + _call_pass2_evaluator("B", ...) + _p2_lookup_directional). READ-ONLY w.r.t.
production: writes only build_log/375D_roleB.json; no code/prompt/severity/routing change.

RUN (on the keyed machine):
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375d_roleB.py"          # default 10 calls/candidate
    python "build_log\\_375d_roleB.py" 12        # optional: K calls/candidate

Cost: 1 Pass-1 (3 calls) + K * (selected candidates, <=12) role-B calls.
"""
import os, sys, json
from collections import Counter

# ── Keys (proven pattern from _step370c_headless.py) ──
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
try:
    for line in open(KEYS_ENV, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() in WANTED:
            os.environ[k.strip()] = v.strip().strip('"').strip("'")
except FileNotFoundError:
    print(f"[375D-B] WARNING: keys file not found at {KEYS_ENV} — provider calls will fail.", flush=True)
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

FROZEN_RUN = r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json"
RUN_030920 = r"05 Lease Analyzer\results\lease_review_20260602_030920_d0e19e\tenant_0\pipeline_results.json"
RUN_0604   = FROZEN_RUN
OUT = r"build_log\375D_roleB.json"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 10
PERSP = "tenant"

from cam.adapters.lease_review.lease_synthesis import (
    _collect_flagged_lps, _build_evaluator_user_prompt, _call_single_evaluator, _EVALUATOR_LINEUP_PASS1,
    _collect_directional_candidates, _build_pass2_user_prompt, _call_pass2_evaluator, _EVALUATOR_LINEUP_PASS2,
    _p2_build_directional_index, _p2_lookup_directional,
)

# ── 1. categorize persistent directional findings from the two stored current-code runs ──
def _dir_agreements(path):
    d = json.load(open(os.path.join(CAM_ROOT, path), encoding="utf-8"))
    out = {}
    for f in d.get("cross_provision_findings", []) or []:
        if f.get("finding_type") == "directional_mismatch":
            out[tuple(sorted(f.get("implicated_lps") or []))] = f.get("evaluator_agreement")
    return out

A = _dir_agreements(RUN_030920)
B = _dir_agreements(RUN_0604)
persist = sorted(set(A) & set(B))
flippers          = [k for k in persist if A[k] != B[k]]
stable_unanimous  = [k for k in persist if A[k] == "3-0" and B[k] == "3-0"]
stable_two_one    = [k for k in persist if A[k] == "2-1" and B[k] == "2-1"]
# representative spread, total <= 12
SELECT = (
    [("flipper", k) for k in flippers[:5]]
    + [("stable_unanimous", k) for k in stable_unanimous[:4]]
    + [("stable_2_1", k) for k in stable_two_one[:3]]
)
print(f"[375D-B] persistent={len(persist)} flippers={len(flippers)} "
      f"stable_unanimous={len(stable_unanimous)} stable_2_1={len(stable_two_one)} | selecting {len(SELECT)}", flush=True)

# ── 2. Pass-1 ONCE (real code path) to obtain the frozen directional candidate set ──
src = json.load(open(os.path.join(CAM_ROOT, FROZEN_RUN), encoding="utf-8"))
full_tenant_text    = src["full_tenant_text"]
coverage_assessment = src["coverage_assessment"]
conflicts           = src.get("conflicts", []) or []
flagged_lps = _collect_flagged_lps(coverage_assessment, conflicts)
print(f"[375D-B] flagged_lps={len(flagged_lps)} — running Pass-1 once for the candidate set...", flush=True)
p1_prompt = _build_evaluator_user_prompt(flagged_lps, full_tenant_text, PERSP, coverage_assessment)
evaluator_outputs = {}
for role, ev_cfg in _EVALUATOR_LINEUP_PASS1.items():
    try:
        evaluator_outputs[role] = _call_single_evaluator(role, ev_cfg, p1_prompt)
    except Exception as e:
        evaluator_outputs[role] = {"role": role, "completed": False, "result": None, "error": str(e)}
directional_candidates = _collect_directional_candidates(evaluator_outputs)
cand_by_lps = {tuple(sorted(c.get("lp_ids") or [])): c for c in directional_candidates}
print(f"[375D-B] Pass-1 produced {len(directional_candidates)} directional candidates", flush=True)

# ── 3. per selected candidate: call role B (gpt-5.4) K times on identical single-candidate input ──
roleB_cfg = _EVALUATOR_LINEUP_PASS2["B"]
print(f"[375D-B] role-B model = {roleB_cfg.get('model')} provider = {roleB_cfg.get('provider')} | K={K}", flush=True)
results = []
for category, lps in SELECT:
    cand = cand_by_lps.get(lps)
    lps_str = "|".join(lps)
    if cand is None:
        results.append({"lps": lps_str, "category": category, "skipped": "candidate not in live Pass-1 set"})
        print(f"[375D-B] {lps_str} [{category}] — SKIP (not in live candidate set)", flush=True)
        continue
    p2_prompt = _build_pass2_user_prompt([], [], [cand], flagged_lps, PERSP)
    tally = Counter()
    raw_verdicts = []
    for call in range(K):
        try:
            out = _call_pass2_evaluator("B", roleB_cfg, p2_prompt)
        except Exception as e:
            tally["n_integrity_fail"] += 1
            raw_verdicts.append({"call": call, "error": repr(e)})
            continue
        if not out.get("completed"):
            tally["n_integrity_fail"] += 1
            raw_verdicts.append({"call": call, "completed": False})
            continue
        by_id, by_lps = _p2_build_directional_index(out)
        v, matched = _p2_lookup_directional(by_id, by_lps, cand.get("candidate_id"), cand.get("lp_ids"))
        if not matched:
            tally["n_integrity_fail"] += 1            # _NO_OBJECT (empty/unmatched/truncated)
            raw_verdicts.append({"call": call, "verdict": "_NO_OBJECT", "n_objects": len(out.get("verdicts") or [])})
        else:
            verdict = (v.get("verdict") or "").strip()
            if verdict == "mismatch_confirmed":
                tally["n_confirmed"] += 1
            elif verdict == "no_mismatch":
                tally["n_no_mismatch"] += 1
            else:
                tally["n_unclear"] += 1
            raw_verdicts.append({"call": call, "verdict": verdict})
    rec = {
        "lps": lps_str, "category": category,
        "candidate_id": cand.get("candidate_id"),
        "stored_agreement_030920": A.get(lps), "stored_agreement_0604": B.get(lps),
        "K": K,
        "n_confirmed": tally["n_confirmed"], "n_no_mismatch": tally["n_no_mismatch"],
        "n_unclear": tally["n_unclear"], "n_integrity_fail": tally["n_integrity_fail"],
        "raw_verdicts": raw_verdicts,
    }
    results.append(rec)
    print(f"[375D-B] {lps_str:<12} [{category:<16}] confirmed={tally['n_confirmed']} "
          f"no_mismatch={tally['n_no_mismatch']} unclear={tally['n_unclear']} "
          f"integrity_fail={tally['n_integrity_fail']} (of {K})", flush=True)

summary = {
    "harness": "B_roleB_reproducibility",
    "frozen_run": "lease_review_20260604_033046_52adbf",
    "role": "B", "model": roleB_cfg.get("model"), "calls_per_candidate": K,
    "selection": {"flippers": len(flippers), "stable_unanimous": len(stable_unanimous), "stable_2_1": len(stable_two_one)},
    "candidates": results,
}
os.makedirs(os.path.join(CAM_ROOT, "build_log"), exist_ok=True)
with open(os.path.join(CAM_ROOT, OUT), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)

print("\n[375D-B] ===== SUMMARY (per candidate: confirmed/no_mismatch/unclear/integrity_fail of K) =====", flush=True)
for r in results:
    if r.get("skipped"):
        print(f"  {r['lps']:<12} [{r['category']:<16}] SKIPPED — {r['skipped']}", flush=True)
        continue
    print(f"  {r['lps']:<12} [{r['category']:<16}] {r['n_confirmed']}/{r['n_no_mismatch']}/{r['n_unclear']}/"
          f"{r['n_integrity_fail']}  (stored 030920={r['stored_agreement_030920']} 0604={r['stored_agreement_0604']})", flush=True)
print(f"\n[375D-B] wrote {OUT}", flush=True)
