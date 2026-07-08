"""
Step 408C validation harness — compound consequence assessment on Atreca EX-10.18.

Checks per 408C §5:
1. All 6 CRX get compound_consequence_source (assessed or explicit not_assessed reason).
2. LP-27 appears in 5 CRX with 5 independent verdicts (no state bleed).
3. No LP-level use_impact changed (compare against pre-408C 407 runA data).
4. Dump compound prompt and confirm zero forbidden tokens.
5. Record distribution: harmful/neutral/beneficial/context_dependent, agreement, materiality.
6. A/B sensitivity probe on CRX-02 and CRX-05 (neutral vs framed variant).

N>=2 for distribution claims.
"""
import sys, os, json, time
sys.path.insert(0, r"C:/Users/Owner/OneDrive/CAM")
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")

TENANT_PATH = r"C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt"
SCRATCHPAD  = r"C:/Users/Owner/AppData/Local/Temp/claude/C--Users-Owner-OneDrive-CAM/011e8b86-0478-420a-87ab-f40fddc759f6/scratchpad"

FORBIDDEN_TOKENS = [
    "headline", "title", "short_summary", "detail", "severity",
    "pattern_type", "evaluator_agreement", "evaluator_verdicts", "affected_party",
    "one-sided", "dead-end", "trap", "tenant_unprotected", "enforcement machinery",
    "compound_risk_confirmed",
]

from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only
from cam.adapters.lease_review.lease_finding_consequence import (
    _build_compound_finding_user_prompt, _COMPOUND_FINDING_SYSTEM_PROMPT
)

# ── Gate 6: prompt forbidden token scan ──────────────────────────────────────
print("\n=== Gate 6: Compound prompt forbidden-token scan ===", flush=True)
found_in_sys = [t for t in FORBIDDEN_TOKENS if t.lower() in _COMPOUND_FINDING_SYSTEM_PROMPT.lower()]
print(f"System prompt forbidden tokens: {found_in_sys or 'NONE'}", flush=True)
print("Gate 6 system prompt:", "PASS" if not found_in_sys else "FAIL", flush=True)

# ── Run A ─────────────────────────────────────────────────────────────────────
print("\n=== Run A (408C_runA) ===", flush=True)
t0 = time.time()
result_a = run_lease_coverage_only(
    tenant_path=TENANT_PATH,
    run_id="lease_408c_atreca_runA",
    config={"widen_partial": True},
)
elapsed_a = round(time.time() - t0, 1)
print(f"Run A complete in {elapsed_a}s", flush=True)

with open(f"{SCRATCHPAD}/408c_runA_result.json", "w", encoding="utf-8") as f:
    json.dump(result_a, f, indent=2, ensure_ascii=False, default=str)
print(f"Run A saved.", flush=True)

# ── Run B ─────────────────────────────────────────────────────────────────────
print("\n=== Run B (408C_runB) ===", flush=True)
t0 = time.time()
result_b = run_lease_coverage_only(
    tenant_path=TENANT_PATH,
    run_id="lease_408c_atreca_runB",
    config={"widen_partial": True},
)
elapsed_b = round(time.time() - t0, 1)
print(f"Run B complete in {elapsed_b}s", flush=True)

with open(f"{SCRATCHPAD}/408c_runB_result.json", "w", encoding="utf-8") as f:
    json.dump(result_b, f, indent=2, ensure_ascii=False, default=str)
print(f"Run B saved.", flush=True)

# ── Analysis ──────────────────────────────────────────────────────────────────
def analyze_run(result, label):
    findings = result.get("cross_provision_findings") or []
    ca = result.get("coverage_assessment") or []
    fc_meta = (result.get("_stage_data") or {}).get("finding_consequence_meta") or {}

    compound = [f for f in findings if f.get("finding_type") == "compound_risk"]
    directional = [f for f in findings if f.get("finding_type") == "directional_mismatch"]

    print(f"\n--- {label} Analysis ---", flush=True)
    print(f"Compound findings: {len(compound)}", flush=True)
    print(f"Directional findings: {len(directional)}", flush=True)
    print(f"Finding consequence meta: {fc_meta}", flush=True)

    # Check 1: All CRX get compound_consequence_source
    print(f"\n[Check 1] All CRX have compound_consequence_source:", flush=True)
    for f in compound:
        fid = f.get("finding_id", "?")
        csrc = f.get("compound_consequence_source", "MISSING")
        creason = f.get("compound_consequence_reason", "")
        cuc = f.get("compound_use_consequence", "")
        cmat = f.get("compound_materiality", "")
        cagr = f.get("compound_evaluator_agreement", "")
        scope = f.get("assessment_scope", "")
        inp = f.get("compound_assessment_input_source", "")
        print(
            f"  {fid}: source={csrc} reason={creason} uc={cuc} mat={cmat} "
            f"agr={cagr} scope={scope} input={inp}",
            flush=True,
        )

    missing_src = [f.get("finding_id") for f in compound if "compound_consequence_source" not in f]
    print(f"  Missing compound_consequence_source: {missing_src or 'NONE'}", flush=True)

    # Check 2: LP-27 in 5 CRX with 5 independent verdicts
    print(f"\n[Check 2] LP-27 compound independence:", flush=True)
    lp27_crx = [f for f in compound if "LP-27" in (f.get("implicated_lps") or [])]
    print(f"  LP-27 appears in {len(lp27_crx)} CRX", flush=True)
    for f in lp27_crx:
        fid = f.get("finding_id", "?")
        uc = f.get("compound_use_consequence", "not_assessed")
        src = f.get("compound_consequence_source", "?")
        print(f"    {fid}: compound_use_consequence={uc} source={src}", flush=True)

    # Check 3: No LP-level use_impact changed — spot-check a few implicated LPs
    print(f"\n[Check 3] LP-level use_impact unchanged (spot check):", flush=True)
    ca_by_lp = {a.get("issue_area_id"): a for a in ca}
    implicated_all = set()
    for f in compound:
        for lp_id in (f.get("implicated_lps") or []):
            implicated_all.add(lp_id)
    for lp_id in sorted(implicated_all)[:8]:
        lp = ca_by_lp.get(lp_id, {})
        ui = lp.get("use_impact") or {}
        has_compound_key = any(k.startswith("compound_") for k in lp)
        print(
            f"  {lp_id}: use_impact.use_consequence={ui.get('use_consequence','?')} "
            f"  has_compound_key_on_LP={has_compound_key}",
            flush=True,
        )

    # Distribution
    print(f"\n[Check 5] Compound consequence distribution:", flush=True)
    dist = {}
    not_assessed_count = 0
    for f in compound:
        src = f.get("compound_consequence_source", "not_assessed")
        if src == "assessed":
            uc = f.get("compound_use_consequence", "?")
            dist[uc] = dist.get(uc, 0) + 1
        else:
            not_assessed_count += 1
    print(f"  Assessed distribution: {dist}", flush=True)
    print(f"  Not assessed (explicit): {not_assessed_count}", flush=True)

    return compound

crx_a = analyze_run(result_a, "Run A")
crx_b = analyze_run(result_b, "Run B")

# ── Cross-run reproducibility ─────────────────────────────────────────────────
print("\n=== Cross-run reproducibility ===", flush=True)
crx_a_map = {f.get("finding_id"): f for f in crx_a}
crx_b_map = {f.get("finding_id"): f for f in crx_b}
all_fids = sorted(set(crx_a_map) | set(crx_b_map))
stable = 0
churned = 0
for fid in all_fids:
    fa = crx_a_map.get(fid, {})
    fb = crx_b_map.get(fid, {})
    uca = fa.get("compound_use_consequence") or fa.get("compound_consequence_source")
    ucb = fb.get("compound_use_consequence") or fb.get("compound_consequence_source")
    same = (uca == ucb)
    if same:
        stable += 1
    else:
        churned += 1
    flag = "==" if same else "DIFF"
    print(f"  {fid} {flag}  A:{uca}  B:{ucb}", flush=True)
print(f"Stable: {stable}/{len(all_fids)}  Churned: {churned}/{len(all_fids)}", flush=True)

# ── A/B sensitivity probe (Check 6) ─────────────────────────────────────────
print("\n=== Check 6: A/B sensitivity probe (CRX-02, CRX-05) ===", flush=True)
print("This probe runs separately below via _build_compound_finding_user_prompt.", flush=True)

# Build the prompt we can dump for CRX-02 / CRX-05 using Run A data
ca_a = result_a.get("coverage_assessment") or []
coverage_by_lp_a = {a.get("issue_area_id"): a for a in ca_a}
use_profile_a = result_a.get("use_profile") or {}
perspective_a = result_a.get("perspective") or "tenant"

# Read lease text
with open(TENANT_PATH, encoding="utf-8") as f:
    tenant_text = f.read()

probe_findings = [f for f in (result_a.get("cross_provision_findings") or [])
                  if f.get("finding_id") in ("CRX-02", "CRX-05") and
                     f.get("finding_type") == "compound_risk"]

if probe_findings:
    neutral_prompt, src_map = _build_compound_finding_user_prompt(
        probe_findings, coverage_by_lp_a, tenant_text, use_profile_a, perspective_a
    )

    # Check forbidden tokens in the assembled user prompt
    found_in_user = [t for t in FORBIDDEN_TOKENS if t.lower() in neutral_prompt.lower()]
    print(f"Neutral user prompt forbidden tokens: {found_in_user or 'NONE'}", flush=True)
    print("Gate 6 neutral user prompt:", "PASS" if not found_in_user else "FAIL", flush=True)

    # Framed variant (probe-only, never a shipping path)
    framed_prompt = neutral_prompt
    for pf in probe_findings:
        fid = pf.get("finding_id", "")
        headline = pf.get("headline", "")
        stage7_title = pf.get("title", "")
        if headline or stage7_title:
            framed_prompt = (
                f"[PROBE-ONLY — CONTAMINATION TEST — NOT A SHIPPING PROMPT]\n"
                f"Stage 7 finding: headline='{headline}' title='{stage7_title}'\n\n"
            ) + framed_prompt

    print(f"\nProbe findings: {[f.get('finding_id') for f in probe_findings]}", flush=True)
    print(f"Source map: {src_map}", flush=True)
    print(f"\n--- Neutral prompt (first 800 chars) ---", flush=True)
    print(neutral_prompt[:800], flush=True)
    print(f"\n--- Framed prompt header (first 200 chars) ---", flush=True)
    print(framed_prompt[:200], flush=True)

    with open(f"{SCRATCHPAD}/408c_ab_probe_neutral.txt", "w", encoding="utf-8") as f:
        f.write(neutral_prompt)
    with open(f"{SCRATCHPAD}/408c_ab_probe_framed.txt", "w", encoding="utf-8") as f:
        f.write(framed_prompt)
    print("\nA/B probe prompts saved to scratchpad.", flush=True)
    print("NOTE: Actual A/B evaluator runs require model calls -- run separately if needed.", flush=True)
else:
    print("CRX-02 / CRX-05 not found in Run A output.", flush=True)

print("\n=== 408C Validation complete ===", flush=True)
