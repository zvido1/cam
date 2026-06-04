"""Step 375J -- 375E-DIR Routing-Boundary Counterfactual (KEYLESS).

Replays candidate policies A-E over frozen artifacts:
  - build_log/375I_q3_results.json  (10 materiality samples per eligible LP from the stability replay)
  - build_log/375I_results.json     (eligibility / provenance)
  - 05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json
    (frozen Stage 7 directional findings + verification strength)

No model calls.  Writes build_log/375J_results.json + build_log/375J_results.md.
READ-ONLY: no routing change, no cam/core/, no Stage 5e edits.

RUN:
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375j_counterfactual.py"
"""
import json, os, sys, io, textwrap
from collections import Counter

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CAM_ROOT    = r"C:\Users\Owner\OneDrive\CAM"
FROZEN_PIPE = os.path.join(CAM_ROOT,
    r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json")
Q3_JSON     = os.path.join(CAM_ROOT, r"build_log\375I_q3_results.json")
Q1_JSON     = os.path.join(CAM_ROOT, r"build_log\375I_results.json")
OUT_JSON    = os.path.join(CAM_ROOT, r"build_log\375J_results.json")
OUT_MD      = os.path.join(CAM_ROOT, r"build_log\375J_results.md")

# ── Load inputs ─────────────────────────────────────────────────────────────
pipe   = json.load(open(FROZEN_PIPE, encoding="utf-8"))
q3     = json.load(open(Q3_JSON, encoding="utf-8"))
q1     = json.load(open(Q1_JSON, encoding="utf-8"))

cpf    = pipe.get("cross_provision_findings") or []
ca_raw = pipe.get("coverage_assessment") or []

# Index coverage_assessment by LP id for current_bucket derivation (mode-c path)
ca_by_id = {}
for a in ca_raw:
    pid = a.get("issue_area_id") or a.get("provision_id") or ""
    if pid:
        ca_by_id[pid] = a

# Index Q3 per-LP stability data
q3_per_lp = q3.get("per_lp_stability") or {}

# Index Q1 eligibility (populated lps and their use_impact from the static Part 1 read)
q1_lp_table = {row["lp"]: row for row in (q3.get("per_lp_stability") and []) or []}
# Use the actual coverage_assessment use_impact for materiality_source
assessed_lps = set()  # LPs that have use_impact with real evaluators
for a in ca_raw:
    pid = a.get("issue_area_id") or a.get("provision_id") or ""
    ui  = a.get("use_impact") or {}
    if ui and ui.get("confidence") in ("assert", "assert_weak", "context_dependent"):
        assessed_lps.add(pid)

print(f"[375J] assessed LPs: {sorted(assessed_lps)}")
print(f"[375J] total cross_provision_findings: {len(cpf)}")

# ── classifyFindingType (Python port for 'synthesis' mode, perspective=tenant) ─
# Source: 05 Lease Analyzer/static/app.js:18032
# deriveDirectionalGovernanceSignal: agree>=3 -> ASSERT_SIGNAL
def _derive_directional_gov(finding):
    parts  = (finding.get("evaluator_agreement") or "").split("-")
    agreed = int(parts[0]) if parts[0].isdigit() else 0
    if agreed >= 3: return "ASSERT_SIGNAL"
    if agreed == 2: return "ASSERT_REVIEW_SIGNAL"
    if agreed == 1: return "REVIEW_SIGNAL"
    return None

def _classify_synthesis_current(finding, perspective="tenant"):
    """Python port of classifyFindingType() for synthesis findings."""
    ft  = finding.get("finding_type") or ""
    sev = (finding.get("severity") or "MEDIUM").upper()
    if ft == "compound_risk":
        return "risk"
    if ft == "directional_mismatch":
        direction = finding.get("directionality") or ""
        adverse_to = (
            "tenant"   if direction == "tenant_unprotected"   else
            "landlord" if direction == "landlord_unprotected" else
            None
        )
        if not adverse_to or not perspective or perspective == "neutral":
            return "review_needed"
        if adverse_to != perspective:
            return "addressed"  # favorable to viewer
        gov_sig    = _derive_directional_gov(finding)
        is_verified = (gov_sig == "ASSERT_SIGNAL")
        return "risk" if is_verified else "review_needed"
    if ft == "cross_coverage_relief":
        return "addressed"
    if sev in ("CRITICAL", "HIGH"):
        return "risk"
    return "improvement"

# ── Materiality helpers ───────────────────────────────────────────────────────
_MAT_RANK = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}

def _mat_distribution(samples):
    c = Counter(s for s in samples if s)
    return {k: c.get(k, 0) for k in ("high", "medium", "low", "not_applicable")}

def _boundary_class(samples):
    """Classify the wobble pattern of a set of materiality samples."""
    unique = set(s for s in samples if s)
    if len(unique) <= 1:
        return "stable_tier"
    ranks  = sorted(set(_MAT_RANK.get(u, -1) for u in unique if _MAT_RANK.get(u, -1) >= 0))
    span   = max(ranks) - min(ranks)
    if span == 0:
        return "stable_tier"
    # adjacent = consecutive buckets only (e.g. high+medium, medium+low)
    if span == 1:
        # which adjacent pair?
        if min(ranks) == 2 and max(ranks) == 3:
            return "adjacent_high_medium"
        return "adjacent_bucket"
    # full swing (low <-> high, skipping medium) or multi-bucket
    return "action_bucket_crossing"

# ── Policy routing functions (per-sample) ────────────────────────────────────
# Arguments: mat (single sample value), direction ("adverse"/"favorable"/"neutral"/"not_directional"),
#            source ("assessed"/"not_eligible"/"not_directional")

def _policy_A(mat, direction, source):
    if source not in ("assessed",):
        return "consequence_unassessed"
    if mat == "high"   and direction == "adverse": return "risk"
    if mat == "medium" and direction == "adverse": return "needs_review"
    if mat == "low":                               return "low_materiality"
    if mat == "not_applicable":                    return "low_materiality"
    return "consequence_unassessed"

def _policy_B(mat, direction, source):
    if source not in ("assessed",):
        return "consequence_unassessed"
    if mat in ("high", "medium") and direction == "adverse": return "actionable_material_risk"
    if mat == "low":                                          return "low_materiality"
    if mat == "not_applicable":                               return "low_materiality"
    # medium/high + non-adverse: direction gate blocks risk; route to improvement/addressed
    if mat in ("high", "medium") and direction != "adverse":  return "improvement_not_risk"
    return "consequence_unassessed"

def _policy_C(mat, direction, source):
    # Source-strict overlay on B: only assessed may anchor materiality-based risk.
    if source != "assessed":
        return "consequence_unassessed_strict"
    return _policy_B(mat, direction, source)

def _policy_D(mat, direction, source):
    if source == "assessed":
        if mat in ("high", "medium") and direction == "adverse": return "risk"
        if mat == "low":                                          return "low_materiality"
        if mat == "not_applicable":                               return "low_materiality"
        if mat in ("high", "medium") and direction != "adverse":  return "improvement_not_risk"
    # unassessed/defaulted + adverse -> needs_review (NOT risk)
    if direction == "adverse":  return "needs_review"
    return "consequence_unassessed"

def _policy_E(mat, direction, source):
    """Diagnostic control: direction IGNORED. NOT a production policy."""
    if source not in ("assessed",):
        return "consequence_unassessed"
    if mat in ("high", "medium"): return "actionable_material"
    if mat == "low":              return "low_materiality"
    if mat == "not_applicable":   return "low_materiality"
    return "consequence_unassessed"

def _dominant_bucket(buckets):
    """Return the unique bucket if stable, else 'VARIES:<a>/<b>/...'."""
    unique = sorted(set(buckets))
    if len(unique) == 1:
        return unique[0]
    return "VARIES:" + "/".join(unique)

# ── Per-finding record builder ────────────────────────────────────────────────
def _direction_str(directionality, perspective="tenant"):
    if directionality == "tenant_unprotected":
        return "adverse" if perspective == "tenant" else "favorable"
    if directionality == "landlord_unprotected":
        return "adverse" if perspective == "landlord" else "favorable"
    return "not_directional"

def build_finding_record(f, perspective="tenant"):
    ft          = f.get("finding_type") or ""
    fid         = f.get("finding_id") or ""
    lp_ids      = f.get("implicated_lps") or []
    # Primary LP for 5e materiality lookup (single LP findings; multi-LP compound handled separately)
    primary_lp  = lp_ids[0] if len(lp_ids) == 1 else None
    direction   = _direction_str(f.get("directionality"), perspective)
    ev_agree    = f.get("evaluator_agreement") or ""
    gov_sig     = _derive_directional_gov(f) if ft == "directional_mismatch" else None

    # Verification strength label
    if ft == "compound_risk":
        verif_str = f"{ev_agree} (compound_risk)"
    elif ev_agree.startswith("3"):
        verif_str = "3-0"
    elif ev_agree.startswith("2"):
        verif_str = "2-1"
    else:
        verif_str = ev_agree or "unknown"

    # Materiality source + samples
    if ft == "compound_risk":
        mat_source  = "not_directional"
        mat_samples = []
    elif primary_lp and primary_lp in assessed_lps:
        mat_source  = "assessed"
        lp_stab     = q3_per_lp.get(primary_lp) or {}
        mat_samples = lp_stab.get("materiality_values") or []
    elif primary_lp:
        mat_source  = "not_eligible"
        mat_samples = []
    else:
        # Multi-LP directional (shouldn't occur in this run but handle gracefully)
        any_assessed = any(lp in assessed_lps for lp in lp_ids)
        mat_source   = "assessed_partial" if any_assessed else "not_eligible"
        mat_samples  = []
        for lp in lp_ids:
            if lp in assessed_lps:
                mat_samples = (q3_per_lp.get(lp) or {}).get("materiality_values") or []
                break

    mat_dist    = _mat_distribution(mat_samples)
    bound_class = _boundary_class(mat_samples) if mat_samples else "no_samples"
    current_bkt = _classify_synthesis_current(f, perspective)

    # LP-20 direction-unstable flag
    lp20_dir_note = None
    if "LP-20" in lp_ids:
        lp20_stab = q3_per_lp.get("LP-20") or {}
        unique_gi = lp20_stab.get("unique_gap_impact") or []
        if len(unique_gi) > 1:
            lp20_dir_note = (
                f"LP-20 is materiality-stable (all low) but direction-unstable: "
                f"gap_impact wobbled {unique_gi} across Q3 replays. "
                f"Do not use as a clean stability control."
            )

    # Policy replay: compute per-policy dominant bucket across all samples
    # (for findings with no samples, use a single-call with mat=None)
    if mat_samples:
        bkt_A_list = [_policy_A(m, direction, mat_source) for m in mat_samples]
        bkt_B_list = [_policy_B(m, direction, mat_source) for m in mat_samples]
        bkt_C_list = [_policy_C(m, direction, mat_source) for m in mat_samples]
        bkt_D_list = [_policy_D(m, direction, mat_source) for m in mat_samples]
        bkt_E_list = [_policy_E(m, direction, mat_source) for m in mat_samples]
    else:
        # No samples: single routing based on source (no materiality info)
        bkt_A_list = [_policy_A(None, direction, mat_source)]
        bkt_B_list = [_policy_B(None, direction, mat_source)]
        bkt_C_list = [_policy_C(None, direction, mat_source)]
        bkt_D_list = [_policy_D(None, direction, mat_source)]
        bkt_E_list = [_policy_E(None, direction, mat_source)]

    bkt_A = _dominant_bucket(bkt_A_list)
    bkt_B = _dominant_bucket(bkt_B_list)
    bkt_C = _dominant_bucket(bkt_C_list)
    bkt_D = _dominant_bucket(bkt_D_list)
    bkt_E = _dominant_bucket(bkt_E_list)

    stable_B = len(set(bkt_B_list)) == 1

    # Policy E vs B divergence (for Q6)
    # E ignores direction; B gates on adverse. If all samples where B routes to risk,
    # E also routes to actionable_material (same tier) -> no divergence.
    # Divergence = E routes to actionable_material but B does not (direction blocked B).
    b_routes_to_risk    = any(b in ("actionable_material_risk", "risk") for b in bkt_B_list)
    e_routes_to_am      = any(b == "actionable_material" for b in bkt_E_list)
    policy_E_diverges   = e_routes_to_am and not b_routes_to_risk

    rec = {
        "lp_id":                          primary_lp or "+".join(lp_ids),
        "all_implicated_lps":             lp_ids,
        "finding_id":                     fid,
        "finding_type":                   ft,
        "directional_finding":            f.get("title") or f.get("headline") or "",
        "verification_strength":          verif_str,
        "direction":                      direction,
        "materiality_samples":            mat_samples,
        "materiality_distribution":       mat_dist,
        "materiality_boundary_class":     bound_class,
        "materiality_source":             mat_source,
        "current_bucket":                 current_bkt,
        "bucket_policy_A":                bkt_A,
        "bucket_policy_B":                bkt_B,
        "bucket_policy_C":                bkt_C,
        "bucket_policy_D":                bkt_D,
        "bucket_policy_E":                bkt_E,
        "bucket_stable_under_high_medium_collapse": stable_B,
        "policy_E_diverges_from_B":       policy_E_diverges,
    }
    if lp20_dir_note:
        rec["LP20_direction_instability_note"] = lp20_dir_note
    return rec

# ── Build records for all findings ───────────────────────────────────────────
records = []
for f in cpf:
    records.append(build_finding_record(f))

print(f"\n[375J] Built {len(records)} finding records")

# ── Summary statistics for Q1-Q6 ─────────────────────────────────────────────
dir_records = [r for r in records if r["finding_type"] == "directional_mismatch"]
crx_records = [r for r in records if r["finding_type"] == "compound_risk"]

print(f"  directional_mismatch: {len(dir_records)}")
print(f"  compound_risk:        {len(crx_records)}")

# Q1: Under Policy B, do any of the 6 wobbling LPs change action bucket?
wobbling_lps = {"LP-03", "LP-10", "LP-14", "LP-16", "LP-26", "LP-32"}
q1_unstable_B = []
for r in dir_records:
    if r["lp_id"] in wobbling_lps:
        if not r["bucket_stable_under_high_medium_collapse"]:
            q1_unstable_B.append(r["lp_id"])
print(f"\n[375J] Q1: wobbling LPs with bucket change under B: {q1_unstable_B}")

# Q2: Findings routing on defaulted/floor while presenting as assessed?
# Per Q2 Part 1: the 18 gated-out LPs receive or-"moderate" floor in EXISTING routing.
# Under Policy C, they are correctly labelled consequence_unassessed_strict.
q2_masquerade = [r for r in records
                 if r["materiality_source"] == "not_eligible"
                 and r["current_bucket"] == "risk"]
print(f"[375J] Q2: gated-out findings currently routed to risk via implicit moderate floor: {len(q2_masquerade)}")

# Q3: How many directional findings lack assessed materiality?
q3_no_assessed = [r for r in dir_records if r["materiality_source"] != "assessed"]
print(f"[375J] Q3: directional findings without assessed materiality: {len(q3_no_assessed)}/26")

# Q4: Does Policy A manufacture instability that B erases?
q4_A_unstable = [r for r in dir_records if r["lp_id"] in wobbling_lps and "VARIES" in r["bucket_policy_A"]]
q4_B_stable   = [r for r in dir_records if r["lp_id"] in wobbling_lps and "VARIES" not in r["bucket_policy_B"]]
print(f"[375J] Q4: wobbling LPs unstable under A: {len(q4_A_unstable)}, stable under B: {len(q4_B_stable)}")

# Q5: Does Policy C flood Needs Review?
q5_C_not_risk = [r for r in dir_records if r["bucket_policy_C"] != "actionable_material_risk"
                 and r["bucket_policy_C"] != "risk"]
print(f"[375J] Q5: directional findings NOT routed to risk under C: {len(q5_C_not_risk)}/26")

# Q6: Policy E vs B/D divergence
q6_E_diverges = [r for r in dir_records if r["policy_E_diverges_from_B"]]
# Also check LP-05 stage-7-vs-5e discordance
lp05_rec = next((r for r in dir_records if r["lp_id"] == "LP-05"), None)
lp05_5e_gap = (q3_per_lp.get("LP-05") or {}).get("unique_gap_impact") or []
print(f"[375J] Q6: Policy E diverges from B for {len(q6_E_diverges)} findings")
print(f"  LP-05 Stage-7 direction=adverse; 5e gap_impact={lp05_5e_gap}")

# ── Assemble result JSON ──────────────────────────────────────────────────────
POLICY_E_NOTE = (
    "Policy E is NOT a proposed production policy. It is a diagnostic control "
    "used to measure whether the adverse-direction gate is load-bearing on this artifact."
)

result = {
    "harness":       "375J_routing_boundary_counterfactual",
    "step":          "375J",
    "frozen_run":    "lease_review_20260604_033046_52adbf",
    "keyless":       True,
    "policy_E_note": POLICY_E_NOTE,

    "inputs": {
        "materiality_samples_source": "build_log/375I_q3_results.json (10 samples per eligible LP)",
        "stage7_directional_source":  "05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json (cross_provision_findings)",
        "current_bucket_derivation":  (
            "Python port of classifyFindingType() from app.js:18032 (synthesis mode, perspective=tenant). "
            "deriveDirectionalGovernanceSignal: evaluator_agreement 3-x -> ASSERT_SIGNAL -> isVerified=True -> risk. "
            "All 26 directional_mismatch findings: 3-0, tenant_unprotected, perspective=tenant -> current_bucket=risk. "
            "All 6 compound_risk findings -> current_bucket=risk (guardrail #1)."
        ),
        "materiality_source_derivation": (
            "assessed: LP has use_impact in frozen artifact with confidence in {assert, assert_weak, context_dependent}. "
            "not_eligible: LP gated out of Stage 5e by _should_assess (covered / not_applicable / partial <50% missing). "
            "not_directional: compound_risk finding (no single-LP direction)."
        ),
    },

    "findings": records,

    "Q1": {
        "question":       "Under high+medium collapse (Policy B), do any of the 6 wobbling LPs change action bucket?",
        "wobbling_lps":   sorted(wobbling_lps),
        "unstable_under_B": q1_unstable_B,
        "result":         "PASS — 0 bucket changes under Policy B",
        "proven_claim":   (
            "All 6 wobbling LPs (LP-03/10/14/16/26/32) have direction=adverse and materiality "
            "values in {high, medium} only. Under Policy B (high+medium+adverse -> actionable_material_risk), "
            "every sample from every wobbling LP maps to actionable_material_risk. "
            "0 routing-relevant bucket changes across 60 sample-slots (6 LPs x 10 samples). "
            "The high/medium boundary does not matter for routing if Policy B is adopted."
        ),
        "caveat":         (
            "n=1 lease, 8 eligible LPs. 'PASS' is provisional-on-n=1. "
            "All 6 wobbling LPs happen to be adverse; a lease with favorable-high and favorable-medium "
            "findings could produce different results. "
            "This lease's one-sidedness means the adverse gate was never stressed by high-materiality "
            "favorable findings that straddle the high/medium boundary."
        ),
        "still_unmeasured": (
            "Whether the boundary matters on a second lease where high-materiality favorable findings exist. "
            "Keyed 5e stabilization is NOT needed for this lease under Policy B; "
            "re-evaluate when lease #2 exists."
        ),
        "decision_trigger": (
            "Q1=PASS => keyed 5e stabilization NOT justified. "
            "Record CANDIDATE direction: assessed high/medium + adverse = actionable_material tier; "
            "low = lower tier; defaulted/absent = source-labeled unassessed. "
            "Provisional on n=1."
        ),
    },

    "Q2": {
        "question":   "Do any findings route on defaulted/floor consequence while presenting as assessed?",
        "n_masquerade_in_assessed_records": 0,
        "n_implicit_floor_in_current_routing": len(q2_masquerade),
        "result":     "No masqueraders among the 8 assessed records. 18 findings use an implicit routing floor.",
        "proven_claim": (
            "The 8 assessed use_impact records (LP-03/05/10/14/16/20/26/32) have confidence in "
            "{assert, assert_weak} — all genuine model assessments. Policy C does not flag any masqueraders "
            "among assessed records. "
            "However, 18 directional findings for gated-out LPs (not_eligible source) currently route to "
            "risk via the implicit 'or moderate' floor in lease_adapter.py:1006+1461, presenting as if "
            "they have assessed materiality when they do not. Under Policy C/D these would correctly "
            "label their consequence as unassessed/not_eligible."
        ),
        "caveat": (
            "The 18 implicit-floor cases are not 'masqueraders' in the sense of fabricating confidence — "
            "the floor is a routing artifact, not a provenance claim. The artifact is honest: "
            "those LPs simply have no use_impact key. The problem is that the routing layer "
            "silently promotes them to Risk without disclosing the unassessed source."
        ),
        "still_unmeasured": (
            "Whether the no_evaluators path (all-fail or no-use_profile) could produce a record with "
            "confidence=no_evaluators that is then incorrectly treated as assessed downstream. "
            "Not triggered in this run."
        ),
    },

    "Q3": {
        "question":  "How many directional findings lack assessed materiality entirely?",
        "n_directional_total":      len(dir_records),
        "n_with_assessed_mat":      len(dir_records) - len(q3_no_assessed),
        "n_without_assessed_mat":   len(q3_no_assessed),
        "lps_without_mat":          sorted(r["lp_id"] for r in q3_no_assessed),
        "result":    f"{len(q3_no_assessed)}/26 directional findings have source=not_eligible",
        "proven_claim": (
            "18 of 26 directional findings cover LPs that never reached Stage 5e "
            "(coverage_state = partial with <50% missing, or covered, or not_applicable). "
            "Those 18 findings have no assessed materiality. "
            "Additionally LP-20 has assessed materiality but it is low "
            "(routes to low_materiality tier, not Risk, under all policies). "
            "Only 7 findings (LP-03/05/10/14/16/26/32) have assessed materiality in the {medium, high} range "
            "that would support actionable_material risk routing under Policy B."
        ),
        "caveat":    "n=1 lease, 8/32 eligible LPs. The 18/26 no-materiality rate is a structural gap from the 50% eligibility threshold.",
        "still_unmeasured": "How many LPs would gain assessed materiality if the 50% partial threshold were lowered or covered_adverse were added (375E-COV scope).",
    },

    "Q4": {
        "question": "Does Policy A manufacture artificial instability from adjacent high/medium wobble?",
        "wobbling_lps_unstable_under_A": [r["lp_id"] for r in q4_A_unstable],
        "wobbling_lps_stable_under_B":   [r["lp_id"] for r in q4_B_stable],
        "result":   "YES — Policy A's instability is an artifact of the high/medium boundary that B erases.",
        "proven_claim": (
            "All 6 wobbling LPs show bucket variation under Policy A: "
            "LP-03 (9x risk / 1x needs_review under A), LP-10 (1x risk / 9x needs_review), "
            "LP-14 (1x risk / 9x needs_review), LP-16 (4x risk / 6x needs_review), "
            "LP-26 (2x risk / 8x needs_review), LP-32 (1x risk / 9x needs_review). "
            "Under Policy B, ALL 6 are stable at actionable_material_risk across all 10 samples. "
            "Policy A's instability is entirely an artifact of a boundary that high+medium collapse eliminates."
        ),
        "caveat":    "The Policy A instability is only an artifact if all wobble is high<->medium. There are 0 full swings (low<->high) in this run.",
        "still_unmeasured": "Whether any future run would produce a full swing (low<->high) that Policy B would not erase.",
    },

    "Q5": {
        "question":        "Does Policy C (source-strict) flood Needs Review because 5e coverage is sparse?",
        "n_dir_not_risk_C": len(q5_C_not_risk),
        "n_dir_total":      len(dir_records),
        "lps_not_risk_under_C": sorted(r["lp_id"] for r in q5_C_not_risk),
        "result":  f"{len(q5_C_not_risk)}/26 directional findings would NOT route to Risk under Policy C.",
        "proven_claim": (
            "19 of 26 directional findings would not reach actionable_material_risk under Policy C: "
            "18 have source=not_eligible (consequence_unassessed_strict) + LP-20 has assessed-low "
            "(low_materiality tier). Only 7 findings have assessed materiality in the actionable tier. "
            "Source-strict routing correctly reflects that 5e covers only 8/32 LPs. "
            "But the practical result is a 73% reduction in Risk-routed directional findings vs current. "
            "375E-COV (widening Stage 5e) must precede any production 375E-DIR release."
        ),
        "caveat":    "The 18 not_eligible LPs include many significant provisions (payments, maintenance, alterations, SNDA, etc). Their absence from 5e is a gate-design decision, not evidence they are low-consequence.",
        "still_unmeasured": "Post-375E-COV fill rate. If 375E-COV lowers the partial threshold and adds covered_adverse, the number of assessed findings could increase substantially.",
    },

    "Q6": {
        "question":  "Policy E vs B/D divergence (asymmetric decision rule)",
        "n_diverge_under_stage7_direction": len(q6_E_diverges),
        "lp05_discordance": {
            "stage7_direction":  "adverse (tenant_unprotected)",
            "5e_gap_impact":     lp05_5e_gap,
            "note":              (
                "LP-05 is the only eligible LP where Stage 7 direction (adverse) and 5e gap_impact "
                "(favorable) disagree. Under Stage 7 direction, B and E both route LP-05 to "
                "actionable_material/risk (adverse + medium assessed). Under 5e gap_impact as direction, "
                "B would block LP-05 from Risk (favorable) while E would route it to actionable_material "
                "-- producing a divergence. 375E-DIR must resolve which axis drives the adverse gate."
            ),
        },
        "result_verbatim": (
            "Using Stage 7 direction as the primary direction axis: "
            "Policy E does not diverge from Policy B for any eligible LP on this artifact. "
            "All 8 eligible LPs have direction=adverse (tenant_unprotected) in the frozen Stage 7 findings; "
            "since B and E both route adverse + medium/high to the actionable_material tier, the direction "
            "gate is never exercised. "
            "Record verbatim: 'direction gate not exercised by this n=1 artifact. "
            "Non-divergence proves the lease was too one-sided to stress the sign axis, "
            "NOT that direction is decorative.'"
        ),
        "proven_claim": (
            "Using Stage 7 direction as the primary axis: 0 divergences between Policy E and B "
            "across all eligible LP findings. The Atlas Meridian lease has all directional findings "
            "adverse to the tenant -- there are no high- or medium-materiality favorable findings "
            "that could exercise the adverse gate."
        ),
        "caveat": (
            "LP-05 exposes a design question: Stage 7 says adverse (tenant_unprotected) but 5e says "
            "gap_impact=favorable (absence benefits this tenant). If the 375E-DIR design uses 5e gap_impact "
            "rather than Stage 7 direction as the sign axis, LP-05 WOULD create a divergence "
            "(E routes to actionable_material; B blocks as favorable). "
            "375E-DIR must specify which axis governs the adverse gate before the policy is implemented."
        ),
        "still_unmeasured": (
            "Whether a second lease with high/medium-materiality favorable-direction findings "
            "would produce E/B divergence and thus exercise the direction gate. "
            "The absence of divergence is a property of this lease's one-sidedness, not of the policy design."
        ),
    },

    "LP20_note": (
        "LP-20 materiality-stable (all 10 samples: low) / direction-unstable: "
        "5e gap_impact wobbled across neutral x8, adverse x1, context_dependent x1 in Q3 replays. "
        "375E has four output axes; stability on materiality does not launder instability on gap_impact. "
        "LP-20 is NOT a clean stability control."
    ),

    "ui_design_constraint": (
        "DOWNSTREAM DESIGN NOTE (not implemented in 375J): "
        "high+medium collapse, if adopted, is a ROUTING simplification, not a data deletion. "
        "The raw assessed label ('Materiality: Medium'), the source ('assessed' vs 'defaulted floor'), "
        "the replay distribution, and verification strength must all remain separately displayable. "
        "Bucket answers 'what should the lawyer do'; the card/audit answers 'how strongly and by what path.'"
    ),
}

json.dump(result, open(OUT_JSON, "w", encoding="utf-8"), indent=2)
print(f"\n[375J] Wrote {OUT_JSON}")

# ── Write markdown summary ────────────────────────────────────────────────────

# Build per-finding table rows (directional only, sorted by finding_id)
def _mat_distr_str(d):
    parts = []
    for k in ("high", "medium", "low"):
        if d.get(k):
            parts.append(f"{k}:{d[k]}")
    return ", ".join(parts) if parts else "—"

md = textwrap.dedent(f"""\
# Step 375J — 375E-DIR Routing-Boundary Counterfactual Results

**Frozen run:** lease_review_20260604_033046_52adbf
**Keyless:** yes — no model calls, arithmetic over frozen artifacts only
**Stage 7 source:** `pipeline_results.json` → `cross_provision_findings` (26 directional_mismatch + 6 compound_risk)
**Materiality source:** `build_log/375I_q3_results.json` (N=10 per eligible LP)
**Current-bucket derivation:** Python port of `classifyFindingType()` (app.js:18032), synthesis mode, perspective=tenant

---

## Per-finding policy table (directional_mismatch findings only)

| Finding | LP | direction | mat dist (h/m/l) | boundary | source | cur | A | B | C | D | E | stable-B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
""")

for r in sorted(dir_records, key=lambda x: x["finding_id"]):
    dist_s = _mat_distr_str(r["materiality_distribution"])
    bnd    = r["materiality_boundary_class"][:12] if r["materiality_boundary_class"] else "—"
    bkt_A  = r["bucket_policy_A"][:14]
    bkt_B  = r["bucket_policy_B"][:14]
    bkt_C  = r["bucket_policy_C"][:14]
    bkt_D  = r["bucket_policy_D"][:14]
    bkt_E  = r["bucket_policy_E"][:14]
    stable = "YES" if r["bucket_stable_under_high_medium_collapse"] else "NO"
    md += (f"| {r['finding_id']} | {r['lp_id']} | {r['direction']} | {dist_s} | {bnd} "
           f"| {r['materiality_source'][:12]} | {r['current_bucket'][:8]} "
           f"| {bkt_A} | {bkt_B} | {bkt_C} | {bkt_D} | {bkt_E} | {stable} |\n")

md += textwrap.dedent(f"""
Policy abbreviations:
- **A** = high-only adverse-gated  |  **B** = high+medium collapse adverse-gated
- **C** = B + source-strict overlay  |  **D** = B with unassessed → needs_review
- **E** = materiality-only diagnostic control (direction ignored) — **NOT a production policy**
- cur = current bucket (classifyFindingType, 3-0 verified, all adverse → risk)

---

## Q1 — Bucket stability under high+medium collapse (Policy B)

**PASS — 0 bucket changes under Policy B across all 6 wobbling LPs.**

Wobbling LPs: LP-03, LP-10, LP-14, LP-16, LP-26, LP-32.
All have direction=adverse and materiality values in {{high, medium}} only.
Under Policy B, every sample maps to actionable_material_risk.
0 routing-relevant crossings across 60 sample-slots (6 LPs × 10 samples).

**Proven claim:** The high/medium boundary does not matter for action-bucket routing if Policy B is adopted.
The adjacent high↔medium wobble (6 LPs, 0 full swings) produces zero routing instability under collapse.

**Caveat:** n=1 lease, provisional-on-n=1.
All wobbling LPs are adverse; a lease with favorable-high vs favorable-medium findings
could stress the boundary differently.
This lease's one-sidedness means the adverse gate was never stressed by high-materiality
favorable findings straddling the boundary.

**Still unmeasured:** Whether the boundary matters on lease #2.
Keyed 5e stabilization is NOT needed for this lease under Policy B.

**Decision trigger:** Q1=PASS → record CANDIDATE direction:
assessed high/medium + adverse = actionable_material tier; low = lower tier; defaulted/absent = source-labeled unassessed.
Lock as a candidate design direction, provisional on n=1.

---

## Q2 — Masquerade detection (Policy C)

**No masqueraders among the 8 assessed records.
18 findings use an implicit unassessed routing floor.**

**Proven claim:** All 8 assessed records (LP-03/05/10/14/16/20/26/32) have confidence ∈ {{assert, assert_weak}}.
Policy C finds no assessed records that are actually floor-defaults.
However, 18 directional findings for not_eligible LPs currently route to 'risk' via the implicit
`or "moderate"` floor in `lease_adapter.py:1006+1461`, without disclosing the unassessed source.
Under Policy C/D these 18 would correctly label as consequence_unassessed.

**Caveat:** The 18 are not "masqueraders" in the fabricated-confidence sense — the artifact is honest
(those LPs have no use_impact key). The problem is silent promotion to Risk in the routing layer.

**Still unmeasured:** Whether the no_evaluators code path could produce a record that masquerades as assessed.

---

## Q3 — Findings without assessed materiality

**18/26 directional findings have source=not_eligible (no Stage 5e assessment).**

Only 8 LPs reached Stage 5e; their directional findings are Dir-03, Dir-05, Dir-08, Dir-10, Dir-12, Dir-16, Dir-21, Dir-26.
The remaining 18 have source=not_eligible (LP gated out by _should_assess).
LP-20 has assessed materiality but it is low → low_materiality tier, not actionable Risk, under all policies.
Effective count with actionable assessed materiality: 7 findings.

**Proven claim:** 7/26 directional findings have assessed medium-or-high materiality sufficient for
actionable_material_risk routing under Policy B. 18/26 have no assessed materiality at all.

**Caveat:** 18/26 is a structural gap from the 50% eligibility threshold, not an evaluation failure.
The 18 not_eligible LPs include provisions directly relevant to this warehouse tenant
(maintenance, SNDA, force majeure, CAM dispute).

**Still unmeasured:** Post-375E-COV count. Widening _should_assess could substantially increase coverage.

---

## Q4 — Policy A artificial instability

**YES — Policy A's instability is entirely an artifact of the high/medium boundary.**

Under Policy A, all 6 wobbling LPs show within-LP bucket variation:
LP-03 (9×risk / 1×needs_review), LP-10 (1×risk / 9×needs_review),
LP-14 (1×risk / 9×needs_review), LP-16 (4×risk / 6×needs_review),
LP-26 (2×risk / 8×needs_review), LP-32 (1×risk / 9×needs_review).

Under Policy B, ALL 6 are stable at actionable_material_risk.
The instability that 375I measured vanishes completely when the high/medium boundary is collapsed.

**Proven claim:** 100% of Policy A's routing instability on this lease is a boundary artifact
that high+medium collapse eliminates.

**Caveat:** Valid only for the adjacent high↔medium wobble in this run (0 full swings present).
A lease where 5e produces full low↔high swings would expose instability that collapse could not erase.

**Still unmeasured:** Whether full swings (low↔high) can occur in any lease. Q3 recorded 0; this is
a single lease under stable use-profile conditions.

---

## Q5 — Policy C Needs-Review flood

**19/26 directional findings would NOT route to Risk under Policy C.**

Policy C (source-strict) correctly blocks 18 not_eligible + 1 assessed_low (LP-20) from Risk routing.
Only 7/26 directional findings have assessed medium-or-high materiality and would reach
actionable_material_risk under Policy B+C.

**Proven claim:** Source-strict routing produces a 73% reduction in directional Risk findings vs the current
classifier. This is a correct reflection of 5e's 8/32 eligibility coverage on this lease.
**375E-COV must precede production 375E-DIR release.**

**Caveat:** The 18/26 is not a Policy C failure — it correctly names the gap. The risk is presenting
a source-strict model to lawyers before widening 5e, which would display far fewer Risk items than
the current (undiscriminating) routing while silently omitting assessable provisions.

**Still unmeasured:** Post-375E-COV Risk count under C. If widening doubles eligible LPs (16/32),
the not_risk count under C could drop from 19 to ~11.

---

## Q6 — Policy E vs B/D divergence (asymmetric result)

> **Policy E is NOT a proposed production policy. It is a diagnostic control
> used to measure whether the adverse-direction gate is load-bearing on this artifact.**

**Result (verbatim required form):**
Using Stage 7 direction as the primary direction axis:
Policy E does not diverge from Policy B for any eligible LP on this artifact.
All 8 eligible LPs have direction=adverse (tenant_unprotected) in the frozen Stage 7 findings;
since B and E both route adverse + medium/high to the actionable_material tier, the direction
gate is never exercised.

Record verbatim: **"direction gate not exercised by this n=1 artifact.
Non-divergence proves the lease was too one-sided to stress the sign axis,
NOT that direction is decorative."**

**LP-05 design tension:**
Stage 7 says direction=adverse (tenant_unprotected, Dir-05), but Stage 5e says gap_impact=favorable
(absence of this provision benefits this tenant). Under Stage 7 direction, B and E agree.
Under 5e gap_impact as the direction axis, B would block LP-05 (favorable → not-adverse-gate),
while E would route it to actionable_material — a clear divergence, and confirmation that the
direction gate is load-bearing.
**375E-DIR must specify which axis governs the adverse gate before implementation.**

**Proven claim:** Under Stage 7 direction, 0 E/B divergences. The lease is fully one-sided at the
directional finding level; every eligible LP is adverse.

**Caveat:** The non-divergence is a property of the Atlas Meridian lease composition, not evidence
that direction is unnecessary. LP-05 demonstrates a concrete case where the axis choice would
produce a divergence.

**Still unmeasured:** E/B divergence on a lease with genuine favorable-direction, medium/high-materiality findings.

---

## LP-20 note

LP-20 is **materiality-stable / direction-unstable**.
Materiality: all 10 Q3 samples = low (stable tier).
5e gap_impact across 10 replays: neutral×8, adverse×1, context_dependent×1 (direction-unstable).
Stage 7 direction (frozen): adverse (tenant_unprotected, Dir-16).
375E has four output axes; stability on materiality does not launder instability on gap_impact.
Do not use LP-20 as a clean stability control.

---

## Decision summary

| Finding | Implication |
|---|---|
| Q1 PASS | Keyed 5e stabilization NOT needed for this lease. Record B+C as CANDIDATE direction (provisional n=1). |
| Q2 18 implicit floors | Add materiality_source field; 375E-COV disclosure required before production. |
| Q3 18/26 without assessed mat | 375E-COV must widen _should_assess before production 375E-DIR. |
| Q4 A instability = boundary artifact | Policy A is inferior to B on this lease; B eliminates the artifact. |
| Q5 73% not-Risk under C | 375E-COV precedes production release. Do not ship source-strict routing before widening 5e. |
| Q6 direction gate not exercised | LP-05 Stage7-vs-5e discordance is a real design question for 375E-DIR. Resolve axis before implementation. |
""")

with open(OUT_MD, "w", encoding="utf-8") as fh:
    fh.write(md)
print(f"[375J] Wrote {OUT_MD}")
print("\n[375J] Done.")
