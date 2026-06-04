"""Step 375D-2 — Track A: Role-B (gpt-5.4) Pass-2 context-sensitivity on a FROZEN candidate set.

Settles whether the directional verification variance seen in the full Stage-7 replay (21->12->7->15->13)
is driven by batch SIZE / ORDER / NEIGHBOR-SET / PROMPT-MISMATCH — by holding the candidate set CONSTANT
and varying only the Pass-2 batching context around each target. Calls the REAL pipeline code path
(_build_pass2_user_prompt + _call_pass2_evaluator + _p2_lookup_directional). READ-ONLY: writes only
build_log/375D2_*.json; no code/prompt/severity/routing change. Code WRITES this; Tzvi RUNS it (keyed).

DESIGN GUARANTEE (the critical constraint): candidate generation is run ONCE and FROZEN to
build_log/375D2_canonical_candidates.json. Every condition below re-uses that frozen set — candidate-set
variance can NOT leak into the Pass-2 sensitivity measurement (that is Track B's job, separately).

RUN (keyed machine):
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375d2_trackA.py" --freeze     # step 1: run Pass-1 once, freeze the canonical set
    python "build_log\\_375d2_trackA.py"               # step 2: run the 5 conditions vs the frozen set
    # optional: --k 10 --perms 3 --neighbor-groups 2 --neighbor-repeats 5   (defaults shown)
    # --refreeze re-runs Pass-1 (only if the frozen set's flipper coverage is poor; documents coverage)
"""
import os, sys, json, hashlib

# ── Keys (proven pattern from _step370c_headless.py / _375d_*.py) ──
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
    print(f"[375D2-A] WARNING: keys file not found at {KEYS_ENV} — provider calls will fail.", flush=True)
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

FROZEN_RUN = r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json"
RUN_030920 = r"05 Lease Analyzer\results\lease_review_20260602_030920_d0e19e\tenant_0\pipeline_results.json"
CANON = os.path.join(CAM_ROOT, r"build_log\375D2_canonical_candidates.json")
OUT = os.path.join(CAM_ROOT, r"build_log\375D2_trackA.json")
PERSP = "tenant"

# knobs (parameterized so Tzvi can size cost)
def _argint(flag, default):
    return int(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default
K = _argint("--k", 10)                 # repeats per condition
PERMS = _argint("--perms", 3)          # shuffle: number of fixed permutations
NB_GROUPS = _argint("--neighbor-groups", 2)
NB_REPEATS = _argint("--neighbor-repeats", 5)
SMALL = 5                              # small-batch size

from cam.adapters.lease_review.lease_synthesis import (
    _collect_flagged_lps, _build_evaluator_user_prompt, _call_single_evaluator, _EVALUATOR_LINEUP_PASS1,
    _collect_directional_candidates, _build_pass2_user_prompt, _call_pass2_evaluator, _EVALUATOR_LINEUP_PASS2,
    _p2_build_directional_index, _p2_lookup_directional,
)


def _dir_agreements(path):
    d = json.load(open(os.path.join(CAM_ROOT, path), encoding="utf-8"))
    return {tuple(sorted(f.get("implicated_lps") or [])): f.get("evaluator_agreement")
            for f in (d.get("cross_provision_findings") or []) if f.get("finding_type") == "directional_mismatch"}


def freeze_canonical():
    """Run Pass-1 ONCE on the frozen pre-Stage-7 input, persist the directional candidate set + flagged_lps."""
    src = json.load(open(os.path.join(CAM_ROOT, FROZEN_RUN), encoding="utf-8"))
    flagged = _collect_flagged_lps(src["coverage_assessment"], src.get("conflicts", []) or [])
    prompt = _build_evaluator_user_prompt(flagged, src["full_tenant_text"], PERSP, src["coverage_assessment"])
    evout = {}
    for role, cfg in _EVALUATOR_LINEUP_PASS1.items():
        try:
            evout[role] = _call_single_evaluator(role, cfg, prompt)
        except Exception as e:
            evout[role] = {"role": role, "completed": False, "result": None, "error": str(e)}
    cands = _collect_directional_candidates(evout)
    json.dump({"flagged_lps": flagged, "directional_candidates": cands,
               "pass1_completed": {r: bool(evout[r].get("completed")) for r in evout}},
              open(CANON, "w", encoding="utf-8"), indent=1)
    print(f"[375D2-A] FROZEN canonical set: {len(cands)} directional candidates -> {CANON}", flush=True)
    return flagged, cands


# ── conditions plumbing ──────────────────────────────────────────────────────
roleB_cfg = _EVALUATOR_LINEUP_PASS2["B"]


def call_batch(batch, flagged):
    """One real Role-B Pass-2 call on a batch (list of candidate dicts). Returns (out, prompt_md5)."""
    prompt = _build_pass2_user_prompt([], [], batch, flagged, PERSP)
    md5 = hashlib.md5(prompt.encode("utf-8", "replace")).hexdigest()[:12]
    try:
        out = _call_pass2_evaluator("B", roleB_cfg, prompt)
    except Exception as e:
        out = {"completed": False, "verdicts": [], "error": repr(e)}
    return out, md5


def verdict_for(out, cand):
    """Classify Role-B's verdict for one candidate in a batch output (real lookup path)."""
    if not out.get("completed"):
        return "integrity_fail", {"reason": "not_completed"}
    by_id, by_lps = _p2_build_directional_index(out)
    v, matched = _p2_lookup_directional(by_id, by_lps, cand.get("candidate_id"), cand.get("lp_ids"))
    if not matched:
        return "integrity_fail", {"reason": "_NO_OBJECT", "n_objects": len(out.get("verdicts") or [])}
    return (v.get("verdict") or "").strip() or "unclear", {"n_objects": len(out.get("verdicts") or [])}


def hyp_tally(verdict):
    """Verification-strength the CURRENT rule (line 1936) would assign IF A=C=mismatch_confirmed (observed
    stable) and B=<verdict>. Reports the routing consequence of B's vote under the current vote==severity map."""
    if verdict == "mismatch_confirmed":
        return "3-0 -> HIGH -> Risk"
    if verdict == "no_mismatch":
        return "2-1 -> MEDIUM -> not-Risk"
    if verdict == "integrity_fail":
        return "verification_incomplete (375C)"
    return "2-1/unclear -> MEDIUM/incomplete"


def record(rows, cond, batch_id, batch, target, out, md5):
    verdict, integ = verdict_for(out, target)
    pos = next((i for i, c in enumerate(batch) if c.get("candidate_id") == target.get("candidate_id")), -1)
    rows.append({
        "candidate_id": target.get("candidate_id"), "lp": "|".join(target.get("lp_ids") or []),
        "condition": cond, "batch_id": batch_id, "batch_size": len(batch), "position": pos,
        "neighbor_ids": [c.get("candidate_id") for c in batch if c is not target],
        "prompt_md5": md5, "role": "B", "model": roleB_cfg.get("model"),
        "verdict": verdict, "integrity": integ, "hypothetical_tally": hyp_tally(verdict),
    })


# ── main ─────────────────────────────────────────────────────────────────────
_want_freeze = ("--freeze" in sys.argv) or ("--refreeze" in sys.argv)
if not os.path.exists(CANON) and "--dry" in sys.argv:
    print("[375D2-A] no frozen canonical set yet. Run `--freeze` first (needs keys), then `--dry` for cost.", flush=True)
    sys.exit(0)
if _want_freeze or not os.path.exists(CANON):
    freeze_canonical()                                  # Pass-1 once (real); writes CANON
    if "--freeze" in sys.argv and "--refreeze" not in sys.argv:
        print("[375D2-A] freeze complete. Re-run WITHOUT --freeze to run the 5 conditions.", flush=True)
        sys.exit(0)
_c = json.load(open(CANON, encoding="utf-8"))
flagged, cands = _c["flagged_lps"], _c["directional_candidates"]
print(f"[375D2-A] frozen canonical set: {len(cands)} directional candidates (from {CANON})", flush=True)

by_lps = {tuple(sorted(c.get("lp_ids") or [])): c for c in cands}

# target categories from the two stored current-code runs (ALL flippers, not a sample)
A030, B0604 = _dir_agreements(RUN_030920), _dir_agreements(FROZEN_RUN)
persist = set(A030) & set(B0604)
flippers   = sorted(k for k in persist if A030[k] != B0604[k])
stable_uni = sorted(k for k in persist if A030[k] == "3-0" and B0604[k] == "3-0")
stable_21  = sorted(k for k in persist if A030[k] == "2-1" and B0604[k] == "2-1")

def present(catlist):
    return [(lps, by_lps[lps]) for lps in catlist if lps in by_lps]

tgt_flip = present(flippers); tgt_uni = present(stable_uni); tgt_21 = present(stable_21)
targets = tgt_flip + tgt_uni + tgt_21
missing_flip = [("|".join(k)) for k in flippers if k not in by_lps]
print("[375D2-A] flippers total=%d in-canonical=%d (MISSING from frozen set: %s)" % (
    len(flippers), len(tgt_flip), missing_flip or "none"))
print("[375D2-A] stable-unanimous in-canonical=%d | stable-2-1 in-canonical=%d" % (len(tgt_uni), len(tgt_21)))

# ── COST ESTIMATE (print before the loop so Tzvi can size it) ──
n_small_groups = (len(cands) + SMALL - 1) // SMALL
est = (K * len(targets)                 # isolation (per target)
       + K                              # full batch (covers all in K calls)
       + K * n_small_groups             # small batches (each covers ~5)
       + PERMS * K                      # shuffled full
       + NB_GROUPS * NB_REPEATS * len(tgt_flip))   # neighbor perturbation (flippers only)
print("\n[375D2-A] ===== COST ESTIMATE =====", flush=True)
print("  targets=%d (flippers=%d, unanimous=%d, 2-1=%d) | canonical=%d | small-groups=%d" % (
    len(targets), len(tgt_flip), len(tgt_uni), len(tgt_21), len(cands), n_small_groups))
print("  K=%d PERMS=%d NEIGHBOR=%dx%d" % (K, PERMS, NB_GROUPS, NB_REPEATS))
print("  ESTIMATED Role-B (gpt-5.4) calls: ~%d" % est)
print("  (lower with e.g. --k 6 --perms 2 --neighbor-groups 2 --neighbor-repeats 3)\n", flush=True)
if "--dry" in sys.argv:
    print("[375D2-A] --dry: cost estimate only, no calls made.", flush=True)
    sys.exit(0)

rows = []

# Condition 1 — SINGLE-candidate isolation (per target)
for lps, cand in targets:
    for i in range(K):
        out, md5 = call_batch([cand], flagged)
        record(rows, "isolation", "iso:%s" % cand["candidate_id"], [cand], cand, out, md5)
print("[375D2-A] condition 1 (isolation) done: %d targets x %d" % (len(targets), K), flush=True)

# Condition 2 — ORIGINAL full fixed batch (one batch covers ALL candidates)
for i in range(K):
    out, md5 = call_batch(cands, flagged)
    for lps, cand in targets:
        record(rows, "full_batch", "full#%d" % i, cands, cand, out, md5)
print("[375D2-A] condition 2 (full batch) done: %d calls" % K, flush=True)

# Condition 3 — FIXED SMALL batches (~5); each chunk covers its members
small_groups = [cands[i:i + SMALL] for i in range(0, len(cands), SMALL)]
tgt_ids = {c["candidate_id"] for _, c in targets}
for gi, group in enumerate(small_groups):
    if not any(c["candidate_id"] in tgt_ids for c in group):
        continue
    for i in range(K):
        out, md5 = call_batch(group, flagged)
        for cand in group:
            if cand["candidate_id"] in tgt_ids:
                record(rows, "small_batch", "small:g%d#%d" % (gi, i), group, cand, out, md5)
print("[375D2-A] condition 3 (small batches) done: %d groups" % len(small_groups), flush=True)

# Condition 4 — SAME full batch, SHUFFLED order (fixed deterministic permutations)
def _perm(seq, seed):
    # deterministic permutation (no RNG — vary by a fixed rotation+stride per seed)
    n = len(seq); stride = (seed * 7 + 3) % n or 1
    idx = [(stride * i + seed) % n for i in range(n)]
    seen, order = set(), []
    for j in idx:
        while j in seen:
            j = (j + 1) % n
        seen.add(j); order.append(seq[j])
    return order
for p in range(PERMS):
    perm = _perm(cands, p + 1)
    for i in range(K):
        out, md5 = call_batch(perm, flagged)
        for lps, cand in targets:
            record(rows, "shuffled", "shuf:p%d#%d" % (p, i), perm, cand, out, md5)
print("[375D2-A] condition 4 (shuffled) done: %d perms x %d" % (PERMS, K), flush=True)

# Condition 5 — NEIGHBOR-SET perturbation (flippers only): target in different fixed groups
pool = [c for c in cands]
for lps, cand in tgt_flip:
    others = [c for c in pool if c["candidate_id"] != cand["candidate_id"]]
    for g in range(NB_GROUPS):
        # deterministic distinct neighbor slice per group
        start = (g * (SMALL - 1)) % max(1, len(others))
        neighbors = (others[start:start + (SMALL - 1)] or others[:SMALL - 1])
        group = [cand] + neighbors
        for i in range(NB_REPEATS):
            out, md5 = call_batch(group, flagged)
            record(rows, "neighbor", "nbr:%s:g%d#%d" % (cand["candidate_id"], g, i), group, cand, out, md5)
print("[375D2-A] condition 5 (neighbor) done: %d flippers x %dx%d" % (len(tgt_flip), NB_GROUPS, NB_REPEATS), flush=True)

# ── per-candidate stability summary ──
from collections import Counter, defaultdict
by_cand = defaultdict(lambda: defaultdict(Counter))
for r in rows:
    by_cand[r["lp"]][r["condition"]][r["verdict"]] += 1
summary = {}
for lp, conds in by_cand.items():
    summary[lp] = {cond: dict(c) for cond, c in conds.items()}

result = {
    "harness": "375D2_trackA_roleB_context_sensitivity",
    "frozen_run": "lease_review_20260604_033046_52adbf",
    "model": roleB_cfg.get("model"), "knobs": {"K": K, "PERMS": PERMS, "NB_GROUPS": NB_GROUPS, "NB_REPEATS": NB_REPEATS},
    "canonical_count": len(cands),
    "flippers_total": len(flippers), "flippers_in_canonical": len(tgt_flip), "flippers_missing": missing_flip,
    "stable_unanimous_in_canonical": [ "|".join(k) for k,_ in tgt_uni ],
    "stable_2_1_in_canonical": [ "|".join(k) for k,_ in tgt_21 ],
    "per_candidate_verdict_by_condition": summary,
    "calls": rows,
}
json.dump(result, open(OUT, "w", encoding="utf-8"), indent=2)
print("\n[375D2-A] ===== PER-CANDIDATE STABILITY (verdict counts by condition) =====", flush=True)
for lp in sorted(summary):
    print("  %-10s %s" % (lp, summary[lp]))
print(f"\n[375D2-A] wrote {OUT}", flush=True)
