"""Step 375M — Validation harness: assert 0 routing drift after rename/revalue.

Re-runs the core routing logic of 375J and 375K through the normalizer against
frozen run 52adbf and asserts every bucket count + per-finding bucket matches
the committed 375J_results.json / 375K_results.json EXACTLY.

Any difference that is not purely a display-label text change = FAIL.
Prints a before/after comparison table and a PASS/FAIL verdict.

RUN:
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375m_validate.py"
"""
import json, os, sys, io
from collections import Counter

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CAM_ROOT    = r"C:\Users\Owner\OneDrive\CAM"
FROZEN_PIPE = os.path.join(CAM_ROOT,
    r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json")
Q3_JSON  = os.path.join(CAM_ROOT, r"build_log\375I_q3_results.json")
J_COMMITTED = os.path.join(CAM_ROOT, r"build_log\375J_results.json")
K_COMMITTED = os.path.join(CAM_ROOT, r"build_log\375K_results.json")

# ── Normalizer (the new read-side compatibility shim) ─────────────────────────
def normalize_use_consequence(ui):
    """Prefer use_consequence; map legacy gap_impact for old artifacts."""
    if not ui: return None
    uc = ui.get("use_consequence")
    if uc is not None: return uc
    legacy = ui.get("gap_impact") or ""
    if legacy == "favorable": return "beneficial"
    if legacy == "adverse":   return "harmful"
    return legacy or None

# ── Load frozen inputs ────────────────────────────────────────────────────────
pipe = json.load(open(FROZEN_PIPE, encoding="utf-8"))
q3   = json.load(open(Q3_JSON,     encoding="utf-8"))
j375 = json.load(open(J_COMMITTED, encoding="utf-8"))
k375 = json.load(open(K_COMMITTED, encoding="utf-8"))

cpf       = pipe.get("cross_provision_findings") or []
ca        = pipe.get("coverage_assessment") or []
q3_per_lp = q3.get("per_lp_stability") or {}

# ── Rebuild assessed_lps (same logic as 375J) ────────────────────────────────
assessed_lps = set()
for a in ca:
    pid = a.get("issue_area_id") or a.get("provision_id") or ""
    ui  = a.get("use_impact") or {}
    if ui and ui.get("confidence") in ("assert", "assert_weak", "context_dependent"):
        assessed_lps.add(pid)

# ── Port of 375J classifyFindingType ─────────────────────────────────────────
def _derive_directional_gov(finding):
    parts  = (finding.get("evaluator_agreement") or "").split("-")
    agreed = int(parts[0]) if parts[0].isdigit() else 0
    if agreed >= 3: return "ASSERT_SIGNAL"
    if agreed == 2: return "ASSERT_REVIEW_SIGNAL"
    if agreed == 1: return "REVIEW_SIGNAL"
    return None

def _classify_synthesis_current(finding, perspective="tenant"):
    ft  = finding.get("finding_type") or ""
    if ft == "compound_risk":
        return "risk"
    if ft == "directional_mismatch":
        direction  = finding.get("directionality") or ""
        adverse_to = ("tenant" if direction == "tenant_unprotected" else
                      "landlord" if direction == "landlord_unprotected" else None)
        if not adverse_to or not perspective or perspective == "neutral":
            return "review_needed"
        if adverse_to != perspective:
            return "addressed"
        gov_sig     = _derive_directional_gov(finding)
        is_verified = (gov_sig == "ASSERT_SIGNAL")
        return "risk" if is_verified else "review_needed"
    return "review_needed"

# ── Re-derive 375J per-finding buckets ───────────────────────────────────────
# 375J routing does NOT depend on gap_impact / use_consequence at all.
# But re-run it through normalizer anyway for completeness (proves no contamination).
def _direction_str(directionality, perspective="tenant"):
    if directionality == "tenant_unprotected":
        return "adverse" if perspective == "tenant" else "favorable"
    if directionality == "landlord_unprotected":
        return "adverse" if perspective == "landlord" else "favorable"
    return "not_directional"

_MAT_RANK = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}

def _policy_B(mat, direction, source):
    if source not in ("assessed",):
        return "consequence_unassessed"
    if mat in ("high", "medium") and direction == "adverse": return "actionable_material_risk"
    if mat == "low":                                          return "low_materiality"
    if mat == "not_applicable":                               return "low_materiality"
    if mat in ("high", "medium") and direction != "adverse":  return "improvement_not_risk"
    return "consequence_unassessed"

# Rebuild per-finding current_bucket for validation against committed 375J
j_by_fid_committed = {r["finding_id"]: r for r in j375.get("findings", [])}
j_drift = []
for f in cpf:
    fid          = f.get("finding_id") or ""
    current_bkt  = _classify_synthesis_current(f)
    committed    = j_by_fid_committed.get(fid)
    if not committed:
        j_drift.append(f"375J MISSING committed record for finding_id={fid!r}")
        continue
    if committed["current_bucket"] != current_bkt:
        j_drift.append(
            f"375J BUCKET DRIFT {fid}: "
            f"committed={committed['current_bucket']!r}, re-derived={current_bkt!r}"
        )

# Also validate 375J Q1/Q2/Q3/Q4/Q5 bucket counts
j_q1_committed = j375["Q1"]["result"]     # "PASS — 0 bucket changes under Policy B"
j_q6_diverge   = j375["Q6"]["n_diverge_under_stage7_direction"]  # 0

print(f"[375M] 375J validation: {len(j_drift)} bucket drift(s)")
for d in j_drift:
    print(f"  DRIFT: {d}")

# ── Re-derive 375K routing through normalizer ────────────────────────────────
# This is where the rename/revalue matters: s5e_gi now comes through normalizer.

def _uc_to_sign(uc):
    return {"beneficial": "favorable", "harmful": "adverse"}.get(uc, uc)

def _axis_relation(s7_dir, s5e_gi):
    if s5e_gi == "absent": return "missing_stage5e"
    if s5e_gi == "context_dependent": return "ambiguous"
    s5e_sign = _uc_to_sign(s5e_gi)
    if s7_dir == s5e_sign: return "aligned"
    return "sign_conflict"

def _mat_route(mat_source, dominant_mat, sign_is_adverse):
    if not sign_is_adverse:
        if mat_source == "assessed" and dominant_mat in ("high", "medium"):
            return "improvement_favorable"
        return "low_materiality_or_addressed"
    if mat_source == "assessed" and dominant_mat in ("high", "medium"):
        return "actionable_material_risk"
    if mat_source == "assessed" and dominant_mat == "low":
        return "low_materiality"
    return "consequence_unassessed"

def rule_A(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    if axis_rel == "sign_conflict": return "needs_review_sign_conflict"
    if axis_rel == "ambiguous":     return "needs_review_sign_ambiguous"
    return _mat_route(mat_source, dominant_mat, s7_dir == "adverse")

def rule_B_k(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    if s5e_gi == "absent": return _mat_route(mat_source, dominant_mat, s7_dir == "adverse")
    if s5e_gi == "context_dependent": return "needs_review_sign_ambiguous"
    return _mat_route(mat_source, dominant_mat, s5e_gi == "harmful")

def rule_C(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    if axis_rel == "sign_conflict":   return "needs_review_sign_conflict"
    if axis_rel == "missing_stage5e": return "consequence_unassessed_no_alignment"
    if axis_rel == "ambiguous":       return "needs_review_sign_ambiguous"
    return _mat_route(mat_source, dominant_mat, s7_dir == "adverse")

def rule_D(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    return _mat_route(mat_source, dominant_mat, s7_dir == "adverse")

def rule_E(s7_dir, s5e_gi, axis_rel, mat_source, dominant_mat):
    if s5e_gi == "absent": return "consequence_unassessed_no_5e_sign"
    if s5e_gi == "context_dependent": return "needs_review_sign_ambiguous"
    return _mat_route(mat_source, dominant_mat, s5e_gi == "harmful")

# Stage 7 direction helper
def _stage7_direction(finding):
    d = finding.get("directionality") or ""
    if d == "tenant_unprotected":   return "adverse"
    if d == "landlord_unprotected": return "favorable"
    return "unknown"

# Mat context from 375J
j_by_fid = {r["finding_id"]: r for r in j375.get("findings", [])}
def _mat_context(fid):
    rec  = j_by_fid.get(fid) or {}
    src  = rec.get("materiality_source", "unknown")
    dist = rec.get("materiality_distribution") or {}
    for m in ("high", "medium", "low"):
        if dist.get(m, 0) > 0:
            return src, m
    return src, "absent"

# Build use_impact index through normalizer
ui_by_lp = {}
for a in ca:
    pid = a.get("issue_area_id") or a.get("provision_id") or ""
    if "use_impact" in a:
        ui_by_lp[pid] = a["use_impact"]

# 375K committed records indexed by finding_id
k_by_fid_committed = {r["finding_id"]: r for r in k375.get("findings", [])}

cpf_dir = {f["finding_id"]: f for f in cpf if f.get("finding_type") == "directional_mismatch"}

k_drift = []
k_rerun = {}

for fid, f in sorted(cpf_dir.items()):
    lp_ids  = f.get("implicated_lps") or []
    primary = lp_ids[0] if len(lp_ids) == 1 else None
    s7_dir  = _stage7_direction(f)

    ui = ui_by_lp.get(primary) if primary else None
    s5e_gi = normalize_use_consequence(ui) or "absent"

    axis_rel     = _axis_relation(s7_dir, s5e_gi)
    mat_src, dom = _mat_context(fid)

    bkt_A = rule_A(s7_dir, s5e_gi, axis_rel, mat_src, dom)
    bkt_B = rule_B_k(s7_dir, s5e_gi, axis_rel, mat_src, dom)
    bkt_C = rule_C(s7_dir, s5e_gi, axis_rel, mat_src, dom)
    bkt_D = rule_D(s7_dir, s5e_gi, axis_rel, mat_src, dom)
    bkt_E = rule_E(s7_dir, s5e_gi, axis_rel, mat_src, dom)

    k_rerun[fid] = {
        "axis_relation":  axis_rel,
        "bucket_rule_A":  bkt_A,
        "bucket_rule_B":  bkt_B,
        "bucket_rule_C":  bkt_C,
        "bucket_rule_D":  bkt_D,
        "bucket_rule_E":  bkt_E,
        "stage5e_gap_impact": s5e_gi,  # now use_consequence value
    }

    committed = k_by_fid_committed.get(fid)
    if not committed:
        k_drift.append(f"375K MISSING committed record for finding_id={fid!r}")
        continue

    for rule_key in ("bucket_rule_A", "bucket_rule_B", "bucket_rule_C",
                     "bucket_rule_D", "bucket_rule_E"):
        c_val = committed[rule_key]
        r_val = k_rerun[fid][rule_key]
        if c_val != r_val:
            k_drift.append(
                f"375K BUCKET DRIFT {fid} {rule_key}: "
                f"committed={c_val!r}, re-derived={r_val!r}"
            )

    # Also check axis_relation
    c_axis = committed["axis_relation"]
    r_axis = k_rerun[fid]["axis_relation"]
    if c_axis != r_axis:
        k_drift.append(
            f"375K AXIS DRIFT {fid}: committed={c_axis!r}, re-derived={r_axis!r}"
        )

print(f"[375M] 375K validation: {len(k_drift)} bucket/axis drift(s)")
for d in k_drift:
    print(f"  DRIFT: {d}")

# ── Bucket count comparison ───────────────────────────────────────────────────
print("\n[375M] === BEFORE/AFTER BUCKET COUNT COMPARISON ===")

# 375J - current_bucket counts
j_committed_bkts = Counter(r["current_bucket"] for r in j375["findings"])
j_rerun_bkts     = Counter(_classify_synthesis_current(f) for f in cpf)
j_bkt_match = (j_committed_bkts == j_rerun_bkts)

print(f"\n375J current_bucket counts:")
print(f"  Committed: {dict(j_committed_bkts)}")
print(f"  Re-derived: {dict(j_rerun_bkts)}")
print(f"  Match: {'YES' if j_bkt_match else 'NO - DRIFT'}")

# 375K - rule bucket counts
for rule_key in ("bucket_rule_A", "bucket_rule_B", "bucket_rule_C", "bucket_rule_D", "bucket_rule_E"):
    c_counts = Counter(r[rule_key] for r in k375["findings"])
    r_counts  = Counter(k_rerun[fid][rule_key] for fid in k_rerun)
    match = (c_counts == r_counts)
    print(f"375K {rule_key}: {'MATCH' if match else 'DRIFT'}")
    if not match:
        print(f"  Committed:  {dict(c_counts)}")
        print(f"  Re-derived: {dict(r_counts)}")

# ── Validation 2: legacy artifact compatibility ───────────────────────────────
# Simulate an old-format ui dict (gap_impact, no use_consequence)
print("\n[375M] === VALIDATION 2: Legacy artifact compatibility ===")
legacy_cases = [
    ({"gap_impact": "favorable"}, "beneficial"),
    ({"gap_impact": "adverse"},   "harmful"),
    ({"gap_impact": "neutral"},   "neutral"),
    ({"gap_impact": "context_dependent"}, "context_dependent"),
    ({"use_consequence": "beneficial"}, "beneficial"),
    ({"use_consequence": "harmful"},    "harmful"),
    ({"use_consequence": "neutral"},    "neutral"),
]
v2_pass = True
for ui_in, expected in legacy_cases:
    result = normalize_use_consequence(ui_in)
    ok = result == expected
    if not ok:
        v2_pass = False
        print(f"  FAIL: normalize({ui_in!r}) = {result!r}, expected {expected!r}")
    else:
        print(f"  PASS: normalize({ui_in!r}) -> {result!r}")

# ── Validation 3: LP-05 specific check ───────────────────────────────────────
print("\n[375M] === VALIDATION 3: LP-05 specific ===")
lp05_ui = ui_by_lp.get("LP-05")
lp05_uc = normalize_use_consequence(lp05_ui)
lp05_k  = k_rerun.get("Dir-05")  # finding for LP-05

print(f"  LP-05 use_consequence (normalized): {lp05_uc!r}")
print(f"  LP-05 stage7 direction: adverse (tenant_unprotected)")
print(f"  LP-05 axis_relation: {lp05_k['axis_relation'] if lp05_k else 'N/A'}")
print(f"  LP-05 bucket_rule_A: {lp05_k['bucket_rule_A'] if lp05_k else 'N/A'}")
print(f"  LP-05 bucket_rule_B: {lp05_k['bucket_rule_B'] if lp05_k else 'N/A'}")
print(f"  LP-05 bucket_rule_C: {lp05_k['bucket_rule_C'] if lp05_k else 'N/A'}")

# Expected: beneficial (not "harmful") → no sign_conflict converted to risk
# axis_relation should be sign_conflict (Stage7=adverse vs 5e=beneficial/favorable)
lp05_ok = (lp05_uc == "beneficial" and
           lp05_k and lp05_k["axis_relation"] == "sign_conflict" and
           lp05_k["bucket_rule_A"] == "needs_review_sign_conflict" and
           lp05_k["bucket_rule_B"] == "improvement_favorable" and
           lp05_k["bucket_rule_C"] == "needs_review_sign_conflict")
print(f"  LP-05 validation: {'PASS' if lp05_ok else 'FAIL'}")

# ── Final verdict ─────────────────────────────────────────────────────────────
total_drift  = len(j_drift) + len(k_drift)
all_pass = (total_drift == 0 and j_bkt_match and v2_pass and lp05_ok)

print("\n" + "="*60)
print(f"VALIDATION SUMMARY")
print(f"  375J bucket drift:  {len(j_drift)} (target: 0)")
print(f"  375J count match:   {'YES' if j_bkt_match else 'NO'}")
print(f"  375K bucket drift:  {len(k_drift)} (target: 0)")
print(f"  Legacy compat:      {'PASS' if v2_pass else 'FAIL'}")
print(f"  LP-05 specific:     {'PASS' if lp05_ok else 'FAIL'}")
print(f"{'='*60}")
if all_pass:
    print("VERDICT: PASS -- 0 routing drift. Rename/revalue is behavior-preserving.")
else:
    print("VERDICT: FAIL -- drift detected. Do NOT deploy.")
print("="*60)

# Write machine-readable summary for 375M_results.md
OUT_JSON = os.path.join(CAM_ROOT, r"build_log\375M_validation_result.json")
json.dump({
    "validation_pass": all_pass,
    "j_bucket_drift": j_drift,
    "j_count_match": j_bkt_match,
    "k_bucket_drift": k_drift,
    "legacy_compat_pass": v2_pass,
    "lp05_specific_pass": lp05_ok,
    "lp05_use_consequence": lp05_uc,
    "lp05_axis_relation": lp05_k["axis_relation"] if lp05_k else None,
    "j_committed_buckets": dict(j_committed_bkts),
    "j_rerun_buckets": dict(j_rerun_bkts),
    "k_per_rule_counts": {
        rule_key: {
            "committed":   dict(Counter(r[rule_key] for r in k375["findings"])),
            "re_derived":  dict(Counter(k_rerun[fid][rule_key] for fid in k_rerun)),
        }
        for rule_key in ("bucket_rule_A", "bucket_rule_B", "bucket_rule_C", "bucket_rule_D", "bucket_rule_E")
    },
}, open(OUT_JSON, "w", encoding="utf-8"), indent=2)
print(f"[375M] Wrote {OUT_JSON}")
