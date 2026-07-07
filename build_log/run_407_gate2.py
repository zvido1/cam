"""
Step 407 Gate 2 harness — full Mode C pipeline on Atreca EX-10.18 (East Jamie,
South SF) with widen_partial=True, N>=2 runs.

Fixture: atreca_eastjamie_southsf_lease.txt
Property type: lab/office (vs Atlas warehouse/industrial)
EDGAR exhibit: EX-10.18, 450 East Jamie Court, South San Francisco, CA
Work scope: populated (Landlord's Work -- private offices per attached plan)

Each run invokes run_lease_coverage_only with cfg={"widen_partial": True}.
Saves pipeline_results.json per run + cross-run analysis output.

Run time: ~17-25 min per run; two runs = ~40-50 min total.
"""
import sys, os, json, time, copy
sys.path.insert(0, r"C:/Users/Owner/OneDrive/CAM")

from dotenv import load_dotenv
load_dotenv(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")

from cam.adapters.lease_review.lease_use_impact import _should_assess, _CHUNK_SIZE

TENANT_PATH = r"C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt"
OUT_DIR = r"C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer/results"
SCRATCHPAD = r"C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-OneDrive-CAM/011e8b86-0478-420a-87ab-f40fddc759f6/scratchpad"

RUNS = [
    ("Run-A", "lease_407_atreca_runA"),
    ("Run-B", "lease_407_atreca_runB"),
]

from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

run_results = {}

for run_label, run_id in RUNS:
    print(f"\n{'='*60}", flush=True)
    print(f"[407 Gate 2] {run_label} — {run_id}", flush=True)
    print(f"{'='*60}", flush=True)

    t0 = time.time()
    result = run_lease_coverage_only(
        tenant_path=TENANT_PATH,
        run_id=run_id,
        config={"widen_partial": True},
    )
    elapsed = round(time.time() - t0, 1)
    print(f"\n[407] {run_label} complete in {elapsed}s", flush=True)

    # Extract key fields
    ca = result.get("coverage_assessment") or []
    use_profile = result.get("use_profile") or {}
    perspective = result.get("perspective") or "tenant"

    narrow_ids = sorted({a["issue_area_id"] for a in ca if _should_assess(a, widen_partial=False)})
    wide_ids   = sorted({a["issue_area_id"] for a in ca if _should_assess(a, widen_partial=True)})
    newly_ids  = sorted(set(wide_ids) - set(narrow_ids))

    assessed = {a["issue_area_id"]: a.get("use_impact")
                for a in ca if a.get("use_impact")}
    unassessed = sorted(a["issue_area_id"] for a in ca if not a.get("use_impact"))

    print(f"  Narrow eligible: {len(narrow_ids)} {narrow_ids}", flush=True)
    print(f"  Wide eligible:   {len(wide_ids)} {wide_ids}", flush=True)
    print(f"  Newly admitted:  {len(newly_ids)} {newly_ids}", flush=True)
    print(f"  Assessed: {len(assessed)} | Unassessed: {len(unassessed)} {unassessed}", flush=True)

    # Coverage state distribution
    from collections import Counter
    cs_dist = Counter(a.get("coverage_state") for a in ca)
    print(f"  Coverage states: {dict(cs_dist)}", flush=True)

    # Verdict distribution
    by_consequence = {}
    for pid, ui in assessed.items():
        c = ui.get("use_consequence", "?")
        by_consequence.setdefault(c, []).append(pid)
    for c, pids in sorted(by_consequence.items()):
        print(f"    {c}: {len(pids)} {sorted(pids)}", flush=True)

    # Multi-finding check: any LP appearing more than once in coverage_assessment?
    id_counts = Counter(a.get("issue_area_id") for a in ca)
    dupes = {k: v for k, v in id_counts.items() if v > 1}
    if dupes:
        print(f"  MULTI-FINDING LPs: {dupes}", flush=True)
    else:
        print(f"  1:1 LP<->card confirmed (N={len(id_counts)})", flush=True)

    # Use profile summary
    print(f"  Use profile: {use_profile.get('business_type','?')} | perspective={perspective}", flush=True)
    print(f"  use_impact_meta: {result.get('use_impact_meta')}", flush=True)

    run_results[run_label] = {
        "run_id": run_id,
        "elapsed_sec": elapsed,
        "narrow_ids": narrow_ids,
        "wide_ids": wide_ids,
        "newly_ids": newly_ids,
        "assessed": assessed,
        "unassessed": unassessed,
        "coverage_state_dist": dict(cs_dist),
        "use_profile": use_profile,
        "perspective": perspective,
        "use_impact_meta": result.get("use_impact_meta"),
        "multi_finding_dupes": dupes,
    }

    out_path = f"{SCRATCHPAD}/407_run_{run_label.lower().replace('-','_')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(run_results[run_label], f, indent=2, ensure_ascii=False)
    print(f"  Saved scratch: {out_path}", flush=True)

# ── Cross-run analysis ─────────────────────────────────────────────────────────
print(f"\n{'='*60}", flush=True)
print("[407 Gate 2] Cross-run analysis", flush=True)
print(f"{'='*60}", flush=True)

ra = run_results.get("Run-A", {})
rb = run_results.get("Run-B", {})
assessed_a = ra.get("assessed", {})
assessed_b = rb.get("assessed", {})

wide_a = set(ra.get("wide_ids", []))
wide_b = set(rb.get("wide_ids", []))
stable_wide = wide_a & wide_b
only_a_wide = wide_a - wide_b
only_b_wide = wide_b - wide_a

print(f"\nEligibility churn (wide gate):")
print(f"  Stable both runs: {len(stable_wide)} {sorted(stable_wide)}", flush=True)
print(f"  Only Run-A: {len(only_a_wide)} {sorted(only_a_wide)}", flush=True)
print(f"  Only Run-B: {len(only_b_wide)} {sorted(only_b_wide)}", flush=True)

assessed_both = set(assessed_a.keys()) & set(assessed_b.keys())
print(f"\nAssessed both runs: {len(assessed_both)}", flush=True)

print(f"\nValue churn (N={len(assessed_both)}):", flush=True)
matches, mismatches = [], []
for pid in sorted(assessed_both):
    ua = assessed_a[pid]; ub = assessed_b[pid]
    ca_cons = ua.get("use_consequence"); cb_cons = ub.get("use_consequence")
    ca_mat  = ua.get("materiality");     cb_mat  = ub.get("materiality")
    ca_agr  = ua.get("evaluator_agreement"); cb_agr = ub.get("evaluator_agreement")
    same = (ca_cons == cb_cons)
    row = (pid, ca_cons, cb_cons, ca_mat, cb_mat, ca_agr, cb_agr)
    (matches if same else mismatches).append(row)
    flag = "==" if same else "DIFF"
    print(f"  {pid:8s} {flag}  A:{ca_cons}/{ca_mat}/{ca_agr}  B:{cb_cons}/{cb_mat}/{cb_agr}", flush=True)

print(f"\n  Stable consequence: {len(matches)}/{len(assessed_both)}", flush=True)
print(f"  Value-churn:        {len(mismatches)}/{len(assessed_both)}", flush=True)
if mismatches:
    print(f"  Mismatches: {[r[0] for r in mismatches]}", flush=True)

# Yield on newly-admitted
newly_a = set(ra.get("newly_ids", []))
newly_b = set(rb.get("newly_ids", []))
newly_union = newly_a | newly_b
print(f"\nYield (newly-admitted union, N={len(newly_union)}):", flush=True)
decisive, ctx_dep, abstain = [], [], []
for pid in sorted(newly_union):
    va = assessed_a.get(pid) or {}
    vb = assessed_b.get(pid) or {}
    v = va if va else vb
    agr = v.get("evaluator_agreement")
    cons = v.get("use_consequence", "?")
    if agr in ("3-0", "2-1"):
        decisive.append((pid, cons, agr))
    elif cons == "context_dependent" or agr == "1-1-1":
        ctx_dep.append((pid, cons, agr))
    else:
        abstain.append((pid, cons, agr))
print(f"  Decisive (3-0/2-1 stable): {len(decisive)}", flush=True)
for r in decisive: print(f"    {r[0]}: {r[1]}/{r[2]}", flush=True)
print(f"  Context-dependent/1-1-1: {len(ctx_dep)}", flush=True)
for r in ctx_dep: print(f"    {r[0]}: {r[1]}/{r[2]}", flush=True)
print(f"  Abstain/no-verdict: {len(abstain)}", flush=True)
for r in abstain: print(f"    {r[0]}: {r[1]}/{r[2]}", flush=True)

# Multi-finding summary
dupes_a = ra.get("multi_finding_dupes", {})
dupes_b = rb.get("multi_finding_dupes", {})
print(f"\nMulti-finding check:", flush=True)
if not dupes_a and not dupes_b:
    print(f"  1:1 confirmed both runs — no LP appears more than once.", flush=True)
else:
    print(f"  Run-A dupes: {dupes_a}", flush=True)
    print(f"  Run-B dupes: {dupes_b}", flush=True)

print(f"\n[407 Gate 2] COMPLETE", flush=True)

# Save cross-run summary
summary = {
    "stable_wide": sorted(stable_wide),
    "only_a_wide": sorted(only_a_wide),
    "only_b_wide": sorted(only_b_wide),
    "assessed_both": sorted(assessed_both),
    "stable_consequence_n": len(matches),
    "value_churn_n": len(mismatches),
    "value_churn_lps": [r[0] for r in mismatches],
    "newly_union": sorted(newly_union),
    "decisive": decisive,
    "ctx_dep": ctx_dep,
    "abstain": abstain,
}
with open(f"{SCRATCHPAD}/407_cross_run_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"\nCross-run summary saved.", flush=True)
