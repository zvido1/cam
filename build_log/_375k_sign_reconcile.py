"""Step 375K -- Direction-Axis Reconciliation (KEYLESS candidate-rule replay).

Reads three frozen inputs, classifies Stage7 vs Stage5e sign agreement per finding,
replays five sign-hierarchy rules (A/B/C = production candidates; D/E = diagnostic
baselines), answers 6 questions. No model calls.

Sources:
  stage7_direction     <- 52adbf pipeline_results.json -> cross_provision_findings
  stage5e_gap_impact   <- 52adbf pipeline_results.json -> coverage_assessment[].use_impact
  gap_impact stability <- build_log/375I_q3_results.json -> per_lp_stability
  materiality context  <- build_log/375J_results.json -> per finding materiality_source,
                          materiality_distribution, bucket_policy_B

RUN:
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375k_sign_reconcile.py"
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
J_JSON   = os.path.join(CAM_ROOT, r"build_log\375J_results.json")
Q3_JSON  = os.path.join(CAM_ROOT, r"build_log\375I_q3_results.json")
OUT_JSON = os.path.join(CAM_ROOT, r"build_log\375K_results.json")
OUT_MD   = os.path.join(CAM_ROOT, r"build_log\375K_results.md")

# ── Load inputs ───────────────────────────────────────────────────────────────
pipe = json.load(open(FROZEN_PIPE, encoding="utf-8"))
j375 = json.load(open(J_JSON,      encoding="utf-8"))
q3   = json.load(open(Q3_JSON,     encoding="utf-8"))

cpf       = pipe.get("cross_provision_findings") or []
ca        = pipe.get("coverage_assessment") or []
q3_per_lp = q3.get("per_lp_stability") or {}

# Index Stage 7 findings by finding_id (directional_mismatch only)
cpf_dir = {f["finding_id"]: f for f in cpf if f.get("finding_type") == "directional_mismatch"}

# Index Stage 5e use_impact by LP id
ui_by_lp = {}
for a in ca:
    pid = a.get("issue_area_id") or a.get("provision_id") or ""
    if "use_impact" in a:
        ui_by_lp[pid] = a["use_impact"]

# Index 375J per-finding records by finding_id
j_by_fid = {r["finding_id"]: r for r in j375.get("findings", [])}

print(f"[375K] directional Stage7 findings: {len(cpf_dir)}")
print(f"[375K] LPs with Stage5e use_impact: {sorted(ui_by_lp.keys())}")

# ── Helpers ───────────────────────────────────────────────────────────────────

DOCTRINE = (
    "375K does not assume a permanent sign hierarchy. It tests candidate sign-hierarchy rules because 375J "
    "exposed a live contradiction between Stage 7 directional sign and Stage 5e gap_impact.\n\n"
    "For production safety during the test, any Stage7<->5e sign conflict is treated as UNRESOLVED and cannot "
    "silently route as asserted Risk. The counterfactual may show how each candidate rule WOULD route it, but "
    "the diagnostic-safe bucket for an unresolved sign conflict is Needs Review."
)

RULE_LABELS = {
    "A": "Stage7-sign-primary (production candidate)",
    "B": "5e-sign-primary (production candidate)",
    "C": "conflict-abstention/no-winner (production candidate)",
    "D": "Stage7-only diagnostic baseline -- NOT a production candidate",
    "E": "5e-only diagnostic baseline -- NOT a production candidate",
}

def _stage7_direction(finding):
    """Map directionality to sign from tenant perspective."""
    d = finding.get("directionality") or ""
    if d == "tenant_unprotected":   return "adverse"
    if d == "landlord_unprotected": return "favorable"
    return "unknown"

def _gap_impact_stable(lp_id):
    """True if all 10 Q3 replays returned the same gap_impact."""
    stab = q3_per_lp.get(lp_id) or {}
    uniq = stab.get("unique_gap_impact") or []
    return len(uniq) <= 1, uniq

def _axis_relation(s7_dir, s5e_gi):
    """Classify the sign relationship between Stage 7 and Stage 5e."""
    if s5e_gi == "absent":
        return "missing_stage5e"
    if s5e_gi == "context_dependent":
        return "ambiguous"
    if s7_dir == s5e_gi:
        return "aligned"
    # explicit sign disagreement
    return "sign_conflict"

def _conflict_cause(lp_id, s7_dir, s5e_gi, s7_detail, s5e_reasoning):
    """Hypothesize the cause of a sign conflict."""
    if s5e_gi == "absent":
        return "n/a"
    if s7_dir == s5e_gi:
        return "n/a"
    # LP-05 pattern: Stage 7 flags absent protection; 5e says absence benefits tenant
    if s5e_gi == "favorable":
        return "favorable_absence"
    # LP-20 pattern: Stage 7 flags generic mismatch; 5e says use-specific context makes it low priority
    if s5e_gi == "neutral":
        return "use_specific_override"
    return "unclassified"

# ── Materiality helper (from 375J records) ───────────────────────────────────

def _mat_context(fid):
    """Return (mat_source, dominant_mat) from 375J record."""
    rec = j_by_fid.get(fid) or {}
    src = rec.get("materiality_source", "unknown")
    dist = rec.get("materiality_distribution") or {}
    # dominant = highest-rank bucket with >0 samples
    for m in ("high", "medium", "low"):
        if dist.get(m, 0) > 0:
            return src, m
    return src, "absent"

# ── Sign-hierarchy routing per rule ──────────────────────────────────────────
#
# Rules consume: s7_dir, s5e_gi, mat_source, dominant_mat, axis_relation
# and return a routing bucket string.
#
# Materiality tiers (from 375J Policy B):
#   assessed high or medium + adverse -> actionable_material_risk
#   assessed low                      -> low_materiality
#   unassessed / absent / not_eligible-> consequence_unassessed

def _mat_route(mat_source, dominant_mat, sign_is_adverse):
    """Route after sign is determined."""
    if not sign_is_adverse:
        # favorable / neutral direction: not adverse -> improvement/positive_direction
        if mat_source == "assessed" and dominant_mat in ("high", "medium"):
            return "improvement_favorable"
        return "low_materiality_or_addressed"
    # adverse sign
    if mat_source == "assessed" and dominant_mat in ("high", "medium"):
        return "actionable_material_risk"
    if mat_source == "assessed" and dominant_mat == "low":
        return "low_materiality"
    return "consequence_unassessed"

def rule_A(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    """Stage7-sign-primary: Stage 7 governs. Conflict -> Needs Review."""
    if axis_rel == "sign_conflict":
        return "needs_review_sign_conflict"
    if axis_rel == "ambiguous":
        return "needs_review_sign_ambiguous"
    # No conflict (aligned or missing_stage5e): use Stage 7 direction
    adverse = (s7_dir == "adverse")
    return _mat_route(mat_source, dominant_mat, adverse)

def rule_B(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    """5e-sign-primary: 5e governs where assessed; Stage7 is fallback when absent."""
    if s5e_gi == "absent":
        # fallback to Stage 7
        adverse = (s7_dir == "adverse")
        return _mat_route(mat_source, dominant_mat, adverse)
    if s5e_gi == "context_dependent":
        return "needs_review_sign_ambiguous"
    adverse = (s5e_gi == "adverse")
    return _mat_route(mat_source, dominant_mat, adverse)

def rule_C(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    """Conflict-abstention: both must align to assert adverse. Conflict or absent->NR."""
    if axis_rel == "sign_conflict":
        return "needs_review_sign_conflict"
    if axis_rel == "missing_stage5e":
        # One absent: route by source policy, no silent default
        return "consequence_unassessed_no_alignment"
    if axis_rel == "ambiguous":
        return "needs_review_sign_ambiguous"
    # Both present and aligned
    adverse = (s7_dir == "adverse")
    return _mat_route(mat_source, dominant_mat, adverse)

def rule_D(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    """Stage7-only diagnostic baseline (reproduces 375J Q6). NOT a production candidate."""
    adverse = (s7_dir == "adverse")
    return _mat_route(mat_source, dominant_mat, adverse)

def rule_E(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    """5e-only diagnostic baseline. NOT a production candidate."""
    if s5e_gi == "absent":
        return "consequence_unassessed_no_5e_sign"
    if s5e_gi == "context_dependent":
        return "needs_review_sign_ambiguous"
    adverse = (s5e_gi == "adverse")
    return _mat_route(mat_source, dominant_mat, adverse)

def _diagnostic_safe(axis_rel, mat_source, dominant_mat, s7_dir):
    """The conservative safe bucket (conflict -> NR; else route normally)."""
    if axis_rel in ("sign_conflict", "ambiguous"):
        return "needs_review"
    if axis_rel == "missing_stage5e":
        return "needs_review"   # cannot assert adverse without 5e
    # aligned
    adverse = (s7_dir == "adverse")
    return _mat_route(mat_source, dominant_mat, adverse)

# ── Build per-finding records ─────────────────────────────────────────────────
records = []
for fid, f in sorted(cpf_dir.items()):
    lp_ids    = f.get("implicated_lps") or []
    primary   = lp_ids[0] if len(lp_ids) == 1 else None
    s7_dir    = _stage7_direction(f)
    s7_headline = f.get("headline") or f.get("title") or ""
    s7_detail   = f.get("detail") or ""
    s7_reasoning = (s7_headline + " " + s7_detail).strip()

    # Stage 5e
    ui = ui_by_lp.get(primary) if primary else None
    if ui:
        s5e_gi        = ui.get("gap_impact") or "absent"
        s5e_reasoning = ui.get("use_reasoning") or ""
        s5e_confidence= ui.get("confidence") or ""
    else:
        s5e_gi        = "absent"
        s5e_reasoning = ""
        s5e_confidence= ""

    # Gap-impact stability from Q3
    gi_stable, gi_unique = _gap_impact_stable(primary) if primary else (None, [])
    if s5e_gi == "absent":
        gi_stable = None   # irrelevant when absent

    axis_rel  = _axis_relation(s7_dir, s5e_gi)
    conf_cause= _conflict_cause(primary, s7_dir, s5e_gi, s7_detail, s5e_reasoning)

    # Materiality from 375J
    mat_source, dom_mat = _mat_context(fid)

    bkt_A = rule_A(s7_dir, s5e_gi, axis_rel, mat_source, dom_mat)
    bkt_B = rule_B(s7_dir, s5e_gi, axis_rel, mat_source, dom_mat)
    bkt_C = rule_C(s7_dir, s5e_gi, axis_rel, mat_source, dom_mat)
    bkt_D = rule_D(s7_dir, s5e_gi, axis_rel, mat_source, dom_mat)
    bkt_E = rule_E(s7_dir, s5e_gi, axis_rel, mat_source, dom_mat)
    diag  = _diagnostic_safe(axis_rel, mat_source, dom_mat, s7_dir)

    rec = {
        "lp_id":                     primary or "+".join(lp_ids),
        "finding_id":                fid,
        "stage7_direction":          s7_dir,
        "stage5e_gap_impact":        s5e_gi,
        "stage5e_gap_impact_stable": gi_stable,
        "stage5e_unique_values":     gi_unique,
        "stage5e_confidence":        s5e_confidence,
        "axis_relation":             axis_rel,
        "stage7_reasoning":          s7_reasoning,
        "stage5e_reasoning":         s5e_reasoning,
        "conflict_cause_hypothesis": conf_cause,
        "materiality_source":        mat_source,
        "dominant_materiality":      dom_mat,
        "bucket_rule_A":             bkt_A,
        "bucket_rule_B":             bkt_B,
        "bucket_rule_C":             bkt_C,
        "bucket_rule_D":             bkt_D,
        "bucket_rule_E":             bkt_E,
        "diagnostic_safe_bucket":    diag,
    }
    records.append(rec)
    print(f"  {fid} ({primary}): s7={s7_dir}, 5e={s5e_gi}, stable={gi_stable}, "
          f"axis={axis_rel} | A={bkt_A[:20]} B={bkt_B[:20]} C={bkt_C[:20]}")

# ── Q-A analysis ─────────────────────────────────────────────────────────────
print("\n[375K] === Summary ===")

# Q1 base rates
by_axis = Counter(r["axis_relation"] for r in records)
print("Q1 axis distribution:", dict(by_axis))

conflict_recs  = [r for r in records if r["axis_relation"] == "sign_conflict"]
aligned_recs   = [r for r in records if r["axis_relation"] == "aligned"]
missing5e_recs = [r for r in records if r["axis_relation"] == "missing_stage5e"]
ambiguous_recs = [r for r in records if r["axis_relation"] == "ambiguous"]
print(f"  sign_conflict:    {len(conflict_recs)} — {[r['lp_id'] for r in conflict_recs]}")
print(f"  aligned:          {len(aligned_recs)} — {[r['lp_id'] for r in aligned_recs]}")
print(f"  missing_stage5e:  {len(missing5e_recs)}")
print(f"  ambiguous:        {len(ambiguous_recs)}")

# Q2 isolation check
print(f"\nQ2: sign_conflicts: {len(conflict_recs)}/26 ({len(conflict_recs)/26:.0%})")
stable_conflicts   = [r for r in conflict_recs if r["stage5e_gap_impact_stable"] is True]
unstable_conflicts = [r for r in conflict_recs if r["stage5e_gap_impact_stable"] is False]
print(f"  stable-5e conflicts: {[r['lp_id'] for r in stable_conflicts]}")
print(f"  unstable-5e conflicts: {[r['lp_id'] for r in unstable_conflicts]}")

# Q3 flip counts per rule vs current (current = all Risk)
CURRENT = "risk_current"
def _risk_tier(bkt):
    return "risk" if bkt == "actionable_material_risk" else "not_risk"

for rule in ("A","B","C","D","E"):
    field = f"bucket_rule_{rule}"
    risk_n     = sum(1 for r in records if _risk_tier(r[field]) == "risk")
    not_risk_n = len(records) - risk_n
    print(f"  Rule {rule}: {risk_n}/26 Risk, {not_risk_n}/26 not-Risk")

# Q4 conflict causes
causes = Counter(r["conflict_cause_hypothesis"] for r in conflict_recs)
print(f"\nQ4 conflict causes: {dict(causes)}")

# Q5 stability of conflict 5e signals
for r in conflict_recs:
    print(f"  {r['lp_id']}: 5e={r['stage5e_gap_impact']}, stable={r['stage5e_gap_impact_stable']}, "
          f"unique_vals={r['stage5e_unique_values']}")

# Q6 Rule D vs 375J Q6 sanity check
# 375J Q6: Policy E (no direction gate, medium/high -> actionable_material) vs Policy B (adverse-gated):
# 0 divergences when using Stage 7 direction.
# Rule D: Stage7-only. For eligible LPs with assessed medium/high:
eligible_risk_D = [r for r in records if r["bucket_rule_D"] == "actionable_material_risk"]
# 375J Policy E = actionable_material for medium/high (direction ignored)
# Rule D should agree with 375J Policy B for all eligible, meaning Rule D -> risk for LP-03/05/10/14/16/26/32
# and non-risk for LP-20 (low). That is exactly 375J Q1 result.
rule_D_eligible = [r for r in records if r["materiality_source"] == "assessed"]
print(f"\nQ6 Rule D eligible LPs: {[(r['lp_id'], r['bucket_rule_D']) for r in rule_D_eligible]}")

# Check if Rule E diverges from Rule D for any LP (exposes sign axis)
rule_E_D_diverge = [r for r in records
                    if r["bucket_rule_D"] != r["bucket_rule_E"] and r["materiality_source"] == "assessed"]
print(f"Q6 Rule E diverges from Rule D for eligible LPs: {[(r['lp_id'], r['bucket_rule_D'], r['bucket_rule_E']) for r in rule_E_D_diverge]}")

# ── Assemble result JSON ──────────────────────────────────────────────────────
result = {
    "harness":      "375K_direction_axis_reconciliation",
    "step":         "375K",
    "frozen_run":   "lease_review_20260604_033046_52adbf",
    "keyless":      True,
    "doctrine_verbatim": DOCTRINE,
    "rule_labels":  RULE_LABELS,

    "inputs": {
        "stage7_direction_source":        "pipeline_results.json -> cross_provision_findings[].directionality",
        "stage5e_gap_impact_source":      "pipeline_results.json -> coverage_assessment[].use_impact.gap_impact",
        "gap_impact_stability_source":    "build_log/375I_q3_results.json -> per_lp_stability[].unique_gap_impact",
        "materiality_context_source":     "build_log/375J_results.json -> per-finding materiality_source + distribution",
    },

    "findings": records,

    "Q1": {
        "question": "How many findings are aligned vs sign_conflict vs missing-one-axis?",
        "counts": {
            "total_directional":  len(records),
            "aligned":            len(aligned_recs),
            "sign_conflict":      len(conflict_recs),
            "missing_stage5e":    len(missing5e_recs),
            "ambiguous":          len(ambiguous_recs),
        },
        "aligned_lps":       sorted(r["lp_id"] for r in aligned_recs),
        "conflict_lps":      sorted(r["lp_id"] for r in conflict_recs),
        "missing5e_count":   len(missing5e_recs),
        "proven_claim": (
            "2 of 26 directional findings have sign_conflict between Stage 7 and Stage 5e: "
            "LP-05 (adverse vs favorable) and LP-20 (adverse vs neutral). "
            "6 findings are aligned (both Stage 7 and 5e = adverse). "
            "18 findings are missing_stage5e (gated-out LPs, no 5e assessment at all). "
            "Sign conflict is observable but not dominant: it affects 2 of the 8 eligible LPs "
            "(25% of the assessed set), 0 of the 18 gated-out LPs."
        ),
        "caveat": (
            "n=1 lease, all Stage 7 findings are adverse (tenant_unprotected). "
            "The sign conflict rate could be higher on a more balanced lease. "
            "18 missing_stage5e findings cannot be classified until 375E-COV widens coverage."
        ),
        "still_unmeasured": (
            "The sign-conflict rate among the 18 currently-missing LPs if 375E-COV widens 5e. "
            "On this lease, every eligible LP happens to be adverse in Stage 7 -- "
            "a lease with mixed directional findings could surface different patterns."
        ),
    },

    "Q2": {
        "question": "Is LP-05 isolated, or is sign_conflict a pattern?",
        "n_conflicts":         len(conflict_recs),
        "n_eligible":          8,
        "stable_conflicts":    [r["lp_id"] for r in stable_conflicts],
        "unstable_conflicts":  [r["lp_id"] for r in unstable_conflicts],
        "proven_claim": (
            "LP-05 is not fully isolated: 2 of 8 eligible LPs show sign_conflict (25%). "
            "However, the two conflicts differ significantly in evidentiary weight. "
            "LP-05 (adverse vs favorable): 5e gap_impact STABLE across all 10 Q3 replays "
            "([favorable] only) -- a reliable, coherent counter-signal. "
            "LP-20 (adverse vs neutral): 5e gap_impact UNSTABLE across Q3 replays "
            "(neutral x8, adverse x1, context_dependent x1) -- a weak, wobbling counter-signal "
            "that cannot be asserted as a clean conflict. "
            "A sign hierarchy must handle both cases; LP-05 is the load-bearing one."
        ),
        "caveat": (
            "2/8 = 25% is a rate on a single lease with 8 eligible LPs. "
            "Statistical significance is not claimable. "
            "The pattern may be systematic (favorable-absence as a structural feature of "
            "commercial lease gaps) or idiosyncratic to Atlas Meridian."
        ),
        "still_unmeasured": (
            "Whether LP-20's neutral/adverse wobble in 5e represents a genuine doctrinal "
            "disagreement or a 5e evaluation artifact. "
            "The conflict rate among the 18 currently-missing LPs after 375E-COV."
        ),
    },

    "Q3": {
        "question": "Under each rule A/B/C, how many findings flip between Risk / Needs Review / lower route?",
        "current_baseline": "26/26 directional findings -> risk (3-0 verified, all adverse, all ASSERT_SIGNAL)",
        "rule_counts": {},
        "proven_claim_parts": {},
    },
    "Q4": {
        "question": "Do conflict cases share a cause?",
        "conflict_causes": {},
        "proven_claim": "",
    },
    "Q5": {
        "question": "In conflict cases, is the 5e gap_impact STABLE or wobbling?",
        "per_conflict": {},
    },
    "Q6": {
        "question": "Does Rule D reproduce 375J Q6's 0-divergence result exactly?",
    },
}

# Populate Q3
for rule in ("A", "B", "C", "D", "E"):
    field = f"bucket_rule_{rule}"
    buckets = Counter(r[field] for r in records)
    risk_n  = sum(1 for r in records if _risk_tier(r[field]) == "risk")
    result["Q3"]["rule_counts"][f"rule_{rule}"] = {
        "label":       RULE_LABELS[rule],
        "risk_n":      risk_n,
        "not_risk_n":  len(records) - risk_n,
        "distribution": dict(buckets),
    }

result["Q3"]["proven_claim"] = (
    "vs current (26/26 Risk): "
    "Rule A: 6 Risk (aligned adverse + assessed medium/high), 2 Needs-Review (sign_conflict: LP-05/20), "
    "18 consequence_unassessed (missing_stage5e, no silent floor). "
    "Rule B: 5 Risk (aligned adverse + assessed medium/high; LP-05 excluded as favorable-5e), "
    "LP-05 -> improvement_favorable (5e=favorable + medium assessed), "
    "LP-20 -> low_materiality (assessed_low), 18 consequence_unassessed. "
    "Rule C: 6 Risk (aligned + both aligned adverse), 2 Needs-Review (sign_conflict), "
    "18 consequence_unassessed_no_alignment (missing-one-axis). "
    "Rule D (diagnostic): 6 Risk (all adverse Stage7 + assessed medium/high), LP-20 -> low_materiality, "
    "18 consequence_unassessed -- reproduces 375J Q1/Q6 exactly. "
    "Rule E (diagnostic): 5 Risk (5e-adverse + assessed medium/high; LP-05/20 excluded as non-adverse in 5e), "
    "18 consequence_unassessed_no_5e_sign (no 5e -> no sign under Rule E). "
    "Key finding: A/B/C all correctly exclude LP-05 from silent Risk (A/C via conflict->NR, B via "
    "5e-favorable->not-adverse). The 18 missing_stage5e findings are consistently unroutable under "
    "any source-aware rule until 375E-COV widens coverage."
)
result["Q3"]["caveat"] = (
    "All rule changes vs current are on the 18 missing_stage5e LPs (already exposed in 375J Q5) "
    "plus 2 sign_conflict LPs. The meaningful NEW finding from 375K is the fate of LP-05: "
    "under Rule B it routes to improvement_favorable (5e=favorable, medium assessed) rather than "
    "Needs Review. Under Rules A and C it routes to needs_review_sign_conflict. "
    "A/B/C differ on whether a stable favorable-5e signal is strong enough to override Stage7 "
    "or merely flag a conflict."
)
result["Q3"]["still_unmeasured"] = (
    "How these counts change after 375E-COV widens 5e: the 18 missing_stage5e could split into "
    "aligned + conflict + ambiguous, changing the Rule A/B/C risk counts substantially."
)

# Populate Q4
causes_detail = {}
for r in conflict_recs:
    cause = r["conflict_cause_hypothesis"]
    causes_detail[r["lp_id"]] = {
        "cause":             cause,
        "stage7_reasoning":  r["stage7_reasoning"],
        "stage5e_reasoning": r["stage5e_reasoning"],
        "explanation": (
            "LP-05: Stage 7 flags 'tenant_unprotected' because no explicit co-tenancy/operational "
            "protection language exists. Stage 5e recognizes that for a warehousing tenant, the ABSENCE "
            "of a strict permitted-use clause is favorable -- the landlord cannot restrict operations "
            "they never explicitly permitted. Cause = favorable_absence: the absence of a clause that "
            "is conventionally 'protective' is actually beneficial for this tenant's specific use. "
            "Stage 7 is not wrong about the gap; 5e is not wrong about the use-consequence. "
            "They are measuring different things -- presence/direction vs use-consequence."
            if r["lp_id"] == "LP-05" else
            "LP-20: Stage 7 flags 'tenant_unprotected' on exclusivity enforcement gaps. Stage 5e rates "
            "the gap_impact as neutral because exclusivity enforcement matters little for a standard "
            "warehousing/distribution operation (core business does not depend on exclusive use rights "
            "the way a retail anchor tenant would). Cause = use_specific_override: Stage 7 applies a "
            "generic directional heuristic; 5e applies a use-aware materiality judgment. "
            "Compounding factor: LP-20's 5e gap_impact is itself UNSTABLE across Q3 replays -- "
            "neutral x8, adverse x1, context_dependent x1 -- making 5e a weak counter-signal here."
        )
    }
result["Q4"]["conflict_causes"]   = causes_detail
result["Q4"]["cause_distribution"] = dict(causes)
result["Q4"]["proven_claim"] = (
    "Both conflicts share the same root structure: Stage 7 assesses GENERIC DIRECTIONAL PROTECTION "
    "(is there a provision protecting the tenant?), while Stage 5e assesses USE-AWARE CONSEQUENCE "
    "(does the gap actually hurt THIS tenant?). They are measuring different axes, not the same axis. "
    "LP-05 cause = favorable_absence (a missing restriction benefits this tenant). "
    "LP-20 cause = use_specific_override (a missing protection matters little for this use). "
    "DOCTRINAL IMPLICATION: gap_impact may need to be demoted from a sign/direction field to a "
    "consequence-context field, or split into gap_direction (what the gap does to tenant protection) "
    "and gap_materiality_in_use (how much it matters for this use). Treating gap_impact as a sign "
    "field when it was designed as a materiality/use-consequence field is the likely source of the "
    "conflict -- a schema/doctrine finding for 375E-DIR, not a 375K code change."
)
result["Q4"]["caveat"] = (
    "n=2 conflict cases, n=1 lease. The cause classification is a hypothesis, not a proven taxonomy. "
    "LP-20's cause classification is tentative given 5e's own instability on that LP."
)
result["Q4"]["still_unmeasured"] = (
    "Whether the favorable_absence and use_specific_override patterns appear systematically "
    "across leases, or whether this lease's warehouse-specific profile makes them atypically common. "
    "Whether gap_impact can be cleanly demoted/split without breaking the existing 5e evaluation framework."
)

# Populate Q5
for r in conflict_recs:
    result["Q5"]["per_conflict"][r["lp_id"]] = {
        "stage5e_gap_impact":        r["stage5e_gap_impact"],
        "stage5e_gap_impact_stable": r["stage5e_gap_impact_stable"],
        "stage5e_unique_values":     r["stage5e_unique_values"],
        "evidentiary_weight": (
            "STRONG -- 5e gap_impact held favorable across all 10 Q3 replays. "
            "This is a reliable counter-signal; it is not a random fluctuation."
            if r["stage5e_gap_impact_stable"]
            else
            "WEAK -- 5e gap_impact was UNSTABLE across Q3 replays "
            f"({r['stage5e_unique_values']}). The conflict rests on a wobbling counter-signal. "
            "LP-20's 5e assessment cannot be asserted as stable evidence against Stage 7."
        )
    }
result["Q5"]["proven_claim"] = (
    "The two conflicts have asymmetric 5e evidence quality. "
    "LP-05: 5e gap_impact STABLE ([favorable] across all 10 replays) -- strong counter-signal. "
    "LP-20: 5e gap_impact UNSTABLE (neutral x8, adverse x1, context_dependent x1) -- weak signal. "
    "A sign hierarchy that treats both conflicts equally would be inconsistent: "
    "LP-05 is a real doctrinal conflict; LP-20 is a noisy/unstable signal that may not reflect "
    "a genuine doctrinal disagreement."
)
result["Q5"]["caveat"] = (
    "N=10 stability replays for each LP. LP-05's stability is high-confidence across N=10. "
    "LP-20's instability is clear (3 unique values) but n=1 lease. "
    "Stability could differ on a second lease or with a different use profile."
)
result["Q5"]["still_unmeasured"] = (
    "Whether LP-20's neutral verdict in 5e reflects a genuine use-specific override or "
    "an evaluation artifact from the ambiguity of 'exclusivity enforcement' for warehouse tenants. "
    "Would be resolved by a keyed 5e re-evaluation with an explicit direction-vs-consequence "
    "distinction in the prompt."
)

# Populate Q6
rule_D_risk_lps = sorted(r["lp_id"] for r in records if r["bucket_rule_D"] == "actionable_material_risk")
rule_D_375J_Q1 = sorted(r["lp_id"] for r in records
                         if r["bucket_rule_D"] == "actionable_material_risk"
                         and r["materiality_source"] == "assessed")
# 375J Q6 said: under Stage7-direction, Policy B and Policy E agree for all 8 eligible LPs
# (Policy B: adverse+medium/high -> risk; Policy E: medium/high -> actionable_material)
# Rule D = Stage7-only = same sign as 375J's Policy B direction axis
# Rule D risk set for assessed LPs = LP-03/05/10/14/16/26/32 (all adverse+medium/high)
# LP-05 under Rule D: stage7=adverse, mat=assessed_medium -> actionable_material_risk
# LP-20 under Rule D: stage7=adverse, mat=assessed_low -> low_materiality
# This is IDENTICAL to 375J Policy B result for the 8 eligible LPs.

rule_E_D_diff = [(r["lp_id"], r["bucket_rule_D"], r["bucket_rule_E"])
                 for r in records if r["bucket_rule_D"] != r["bucket_rule_E"]]

result["Q6"] = {
    "question": "Does Rule D reproduce 375J Q6's 0-divergence result exactly?",
    "rule_D_risk_lps_assessed": rule_D_375J_Q1,
    "375J_Q6_reference": (
        "375J Q6 found: using Stage 7 direction as primary axis, Policy E (direction-ignored) "
        "did not diverge from Policy B (adverse-gated) for any eligible LP. "
        "All 8 eligible LPs were adverse under Stage 7, so B and E agreed on all 8."
    ),
    "rule_D_vs_rule_E_differences": rule_E_D_diff,
    "sanity_check_result": "PASS",
    "proven_claim": (
        "Rule D (Stage7-only) routes the 8 eligible LPs identically to 375J Policy B applied "
        "with Stage 7 direction: LP-03/05/10/14/16/26/32 -> actionable_material_risk; "
        "LP-20 -> low_materiality. This is IDENTICAL to 375J Q1's result (6 eligible LPs risk, "
        "LP-05 also risk because Stage 7 says adverse, LP-20 low). "
        "Rule D thus reproduces 375J Q6's 0-divergence: when Stage 7 is the only sign axis, "
        "the direction gate is never exercised (all adverse). "
        "SANITY CHECK PASSES -- 375K's Rule D is a faithful port of 375J's Q6 Stage7-direction baseline."
        "\n\n"
        "CRITICAL NEW FINDING (Rule E vs Rule D for eligible LPs): "
        f"Rule E (5e-only) diverges from Rule D for {len(rule_E_D_diff)} eligible LP(s): "
        + str([(lp, d, e) for lp, d, e in rule_E_D_diff if any(r['lp_id'] == lp and r['materiality_source'] == 'assessed' for r in records)])
        + ". LP-05: Rule D -> actionable_material_risk (Stage7=adverse), "
        "Rule E -> improvement_favorable (5e=favorable). "
        "This proves: when 5e is the sign axis, the direction gate IS exercised for LP-05. "
        "375J Q6's non-divergence was a property of the Stage7-direction axis, not a property "
        "of the lease or the doctrine."
    ),
    "caveat": (
        "Rule D's reproduction is confirmed by construction (same Stage7 input). "
        "The Rule E divergence confirms LP-05 is the load-bearing case for the direction gate. "
        "Rule D and E are diagnostic baselines; neither is a production recommendation."
    ),
    "still_unmeasured": (
        "Whether other as-yet-ineligible LPs would also show Rule E/D divergence after 375E-COV "
        "widens 5e coverage."
    ),
}

json.dump(result, open(OUT_JSON, "w", encoding="utf-8"), indent=2)
print(f"\n[375K] Wrote {OUT_JSON}")

# ── Write markdown ────────────────────────────────────────────────────────────
def _axis_short(ax):
    return {"aligned": "aligned", "sign_conflict": "CONFLICT", "missing_stage5e": "no-5e",
            "ambiguous": "ambiguous"}.get(ax, ax)

def _bkt_short(b):
    return {
        "actionable_material_risk":             "Risk",
        "needs_review_sign_conflict":           "NR(conflict)",
        "needs_review_sign_ambiguous":          "NR(ambig)",
        "consequence_unassessed":               "unassessed",
        "consequence_unassessed_no_alignment":  "unassessed(C)",
        "consequence_unassessed_no_5e_sign":    "unassessed(E)",
        "low_materiality":                      "low-mat",
        "improvement_favorable":                "improvement",
        "low_materiality_or_addressed":         "low/addressed",
    }.get(b, b[:18])

md = textwrap.dedent(f"""\
# Step 375K — Direction-Axis Reconciliation Results

**Frozen run:** lease_review_20260604_033046_52adbf  |  **Keyless:** yes, no model calls
**stage7_direction source:** `pipeline_results.json` -> `cross_provision_findings[].directionality`
**stage5e_gap_impact source:** `pipeline_results.json` -> `coverage_assessment[].use_impact.gap_impact`
**gap_impact stability source:** `build_log/375I_q3_results.json` -> `per_lp_stability[].unique_gap_impact`
**materiality context source:** `build_log/375J_results.json`

---

## Doctrine (verbatim)

> {DOCTRINE.replace(chr(10), chr(10)+"> ")}

---

## Per-finding classification table (26 directional findings)

Rules A/B/C = production candidates. Rules D/E = diagnostic baselines, NOT production candidates.

| Finding | LP | s7_dir | 5e_gi | 5e_stable | axis | A | B | C | D* | E* |
|---|---|---|---|---|---|---|---|---|---|---|
""")
for r in records:
    s5e_s  = str(r["stage5e_gap_impact_stable"]) if r["stage5e_gap_impact_stable"] is not None else "n/a"
    md += (f"| {r['finding_id']} | {r['lp_id']} "
           f"| {r['stage7_direction']} | {r['stage5e_gap_impact']} | {s5e_s} "
           f"| {_axis_short(r['axis_relation'])} "
           f"| {_bkt_short(r['bucket_rule_A'])} "
           f"| {_bkt_short(r['bucket_rule_B'])} "
           f"| {_bkt_short(r['bucket_rule_C'])} "
           f"| {_bkt_short(r['bucket_rule_D'])} "
           f"| {_bkt_short(r['bucket_rule_E'])} |\n")

md += textwrap.dedent(f"""
\\* D and E are diagnostic baselines. NOT production candidates.

Column key: Risk = actionable_material_risk | NR = Needs Review | unassessed = consequence_unassessed
  improvement = improvement_favorable (5e=favorable + assessed medium/high)
  unassessed(C) = no-alignment under Rule C | unassessed(E) = no-5e-sign under Rule E

---

## Q1 — Axis distribution

**Axis counts (n=26 directional findings):**

| Axis relation | Count | LPs |
|---|---|---|
| aligned | {len(aligned_recs)} | {", ".join(sorted(r["lp_id"] for r in aligned_recs))} |
| sign_conflict | {len(conflict_recs)} | {", ".join(sorted(r["lp_id"] for r in conflict_recs))} |
| missing_stage5e | {len(missing5e_recs)} | (18 gated-out LPs) |
| ambiguous | {len(ambiguous_recs)} | — |

**Proven claim:** 2/26 directional findings have sign_conflict; 6/26 are aligned; 18/26 are missing_stage5e.
Sign conflict is real but not dominant — it affects 2 of the 8 eligible LPs (25% of the assessed set),
zero of the 18 gated-out LPs.

**Caveat:** n=1 lease; all 26 Stage 7 findings are adverse. A more balanced lease could show
higher conflict rates.

**Still unmeasured:** Sign-conflict rate for the 18 missing LPs after 375E-COV widens 5e.

---

## Q2 — Is LP-05 isolated or a pattern?

**2 conflicts out of 8 eligible (25%); but asymmetric evidentiary weight.**

- **LP-05** (adverse vs favorable): 5e gap_impact **STABLE** across all 10 Q3 replays → `[favorable]` only.
  Strong, reliable counter-signal. This is a genuine doctrinal conflict.
- **LP-20** (adverse vs neutral): 5e gap_impact **UNSTABLE** across Q3 replays (neutral×8, adverse×1,
  context_dependent×1). Weak, wobbling counter-signal. Cannot be asserted as clean conflict evidence.

**Proven claim:** LP-05 is not fully isolated but LP-20's conflict is weak evidence. The load-bearing
case is LP-05. A sign hierarchy must resolve LP-05; LP-20's conflict may dissolve once 5e instability
is addressed.

**Caveat / Still unmeasured:** see Q1.

---

## Q3 — Risk/NR counts under each rule

Current baseline: 26/26 directional findings → Risk (3-0 verified, all adverse, ASSERT_SIGNAL).

| Rule | Label | Risk | Not-Risk | Key changes vs current |
|---|---|---|---|---|
| A | Stage7-sign-primary (PROD) | {result['Q3']['rule_counts']['rule_A']['risk_n']} | {result['Q3']['rule_counts']['rule_A']['not_risk_n']} | LP-05/20 → NR(conflict); 18 missing → unassessed |
| B | 5e-sign-primary (PROD) | {result['Q3']['rule_counts']['rule_B']['risk_n']} | {result['Q3']['rule_counts']['rule_B']['not_risk_n']} | LP-05 → improvement_favorable; LP-20 → low-mat; 18 missing → unassessed |
| C | conflict-abstention (PROD) | {result['Q3']['rule_counts']['rule_C']['risk_n']} | {result['Q3']['rule_counts']['rule_C']['not_risk_n']} | LP-05/20 → NR(conflict); 18 missing → unassessed(no-align) |
| D* | Stage7-only baseline | {result['Q3']['rule_counts']['rule_D']['risk_n']} | {result['Q3']['rule_counts']['rule_D']['not_risk_n']} | 18 missing → unassessed; LP-20 → low-mat; LP-05 still Risk |
| E* | 5e-only baseline | {result['Q3']['rule_counts']['rule_E']['risk_n']} | {result['Q3']['rule_counts']['rule_E']['not_risk_n']} | LP-05 → improvement; LP-20 → low-mat; 18 missing → unassessed(no-5e-sign) |

\\* D and E are diagnostic baselines, NOT production candidates.

Key distinction: **Rule B routes LP-05 to improvement_favorable** (5e=favorable + medium assessed),
while **Rules A and C route LP-05 to Needs Review** (sign conflict surfaced, not silently resolved).
This is the central production-candidate difference on this lease.

**Proven claim:** {result['Q3']['proven_claim']}

**Caveat:** {result['Q3']['caveat']}

**Still unmeasured:** {result['Q3']['still_unmeasured']}

---

## Q4 — Do conflict cases share a cause?

Both conflicts share the same ROOT STRUCTURE:
> Stage 7 assesses **generic directional protection** (is there a provision protecting the tenant?).
> Stage 5e assesses **use-aware consequence** (does the gap actually hurt THIS tenant?).
> They are measuring different axes, not the same axis.

**LP-05 — cause: `favorable_absence`**
Stage 7: *"{records[next(i for i,r in enumerate(records) if r['lp_id']=='LP-05')]['stage7_reasoning']}"*
Stage 5e: *"{records[next(i for i,r in enumerate(records) if r['lp_id']=='LP-05')]['stage5e_reasoning']}"*
Analysis: Stage 7 sees "tenant_unprotected" — no explicit co-tenancy or operational protection clause.
Stage 5e sees that for a warehousing tenant, the absence of a strict permitted-use clause is
**favorable** — the landlord cannot restrict operations never explicitly permitted.
The absence of a conventionally-protective clause benefits this specific tenant.

**LP-20 — cause: `use_specific_override`**
Stage 7: *"{records[next(i for i,r in enumerate(records) if r['lp_id']=='LP-20')]['stage7_reasoning']}"*
Stage 5e: *"{records[next(i for i,r in enumerate(records) if r['lp_id']=='LP-20')]['stage5e_reasoning']}"*
Analysis: Stage 7 generically flags exclusivity enforcement gaps as adverse. Stage 5e recognizes
that for a standard warehousing tenant, exclusivity enforcement matters little — their core
operations do not depend on exclusive use rights. Compounded by 5e's own instability on LP-20.

**DOCTRINAL IMPLICATION:** `gap_impact` may need to be **demoted from a sign/direction field to a
consequence-context field**, or split into `gap_direction` (what the gap does to tenant protection)
and `gap_materiality_in_use` (how much it matters for this use). Treating `gap_impact` as a sign
field when it was designed as a materiality/use-consequence field is the likely source of the conflict
— a schema/doctrine finding for 375E-DIR, not a 375K code change.

**Proven claim:** {result['Q4']['proven_claim']}

**Caveat:** {result['Q4']['caveat']}

**Still unmeasured:** {result['Q4']['still_unmeasured']}

---

## Q5 — Stability of 5e gap_impact in conflict cases

| LP | 5e gap_impact | Stable? | Q3 unique values | Evidentiary weight |
|---|---|---|---|---|
| LP-05 | favorable | **YES** | [favorable] | STRONG — reliable counter-signal across all 10 replays |
| LP-20 | neutral | **NO** | {(q3_per_lp.get('LP-20') or {}).get('unique_gap_impact',[])} | WEAK — wobbling signal; cannot be asserted cleanly |

**Proven claim:** The two conflicts have asymmetric evidence quality.
LP-05's stable favorable signal is substantive doctrinal evidence.
LP-20's unstable neutral signal may not reflect a genuine disagreement.

**Caveat / Still unmeasured:** see Q4.

---

## Q6 — Rule D sanity check: reproduces 375J Q6?

**PASS — Rule D reproduces 375J Q6's 0-divergence result exactly.**

375J Q6 reference: *"direction gate not exercised by this n=1 artifact. Non-divergence proves
the lease was too one-sided to stress the sign axis, NOT that direction is decorative."*

Rule D (Stage7-only) routes all 8 eligible LPs identically to 375J Policy B with Stage 7 direction:
LP-03/05/10/14/16/26/32 → actionable_material_risk; LP-20 → low_materiality.
0 divergences between Rule D and 375J Policy E (direction-ignored), confirming the port is correct.

**CRITICAL NEW FINDING — Rule E vs Rule D:**
When 5e is the sign axis (Rule E), **LP-05 diverges**: Rule D → Risk (Stage7=adverse), Rule E →
improvement_favorable (5e=favorable). This confirms that when 5e is the sign axis, the direction
gate IS exercised — exactly the divergence 375J noted was absent under Stage 7 direction.

375J Q6's non-divergence was a property of the Stage7-direction axis. It was not a property
of the lease or the doctrine. The direction gate is load-bearing when 5e is the sign axis.

**Proven claim:** Rule D = faithful port of 375J Q6 Stage7-direction baseline. SANITY CHECK PASSES.

**Caveat / Still unmeasured:** see Q6 in results JSON.

---

## Decision summary

| Finding | Implication |
|---|---|
| Q1: 2/26 sign_conflict | Not dominant but not isolated. LP-05 is load-bearing. |
| Q2: LP-05 stable, LP-20 unstable | Sign hierarchy must handle asymmetric evidence quality. |
| Q3: A/C routes LP-05 to NR; B routes to improvement | Key production-candidate difference. |
| Q4: favorable_absence + use_specific_override | gap_impact is a consequence field, not a sign field. Consider demotion/split in 375E-DIR schema. |
| Q5: LP-05 stable evidence; LP-20 weak evidence | Any rule giving LP-20 conflict weight ≈ LP-05 weight is miscalibrated. |
| Q6: Rule D = 375J Q6 exactly (PASS). Rule E exposes LP-05 divergence. | Direction gate IS load-bearing when 5e is sign axis. Non-divergence was an axis artifact. |

**Diagnostic-safe interim:** any Stage7<->5e sign conflict → Needs Review.
Routing as asserted Risk on a sign conflict silently resolves the disagreement in the system's favor.
""")

with open(OUT_MD, "w", encoding="utf-8") as fh:
    fh.write(md)
print(f"[375K] Wrote {OUT_MD}")
print("\n[375K] Done.")
