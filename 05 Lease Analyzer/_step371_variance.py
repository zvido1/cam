"""Step 371 — Stage 5 upstream variance characterization (read-only, no reruns).

Builds the per-LP Stage 5 variance matrix across the six matched 370c runs, classifies
each LP's variance (Class 1-4), and compares the collapsed run 222051 to the healthy
six-run envelope (Branch 0A). Maps to REAL JSON field names; flags absent fields.
"""
import json, hashlib
from collections import defaultdict

def _normalize_use_consequence(ui):
    """Read use_consequence; normalize legacy gap_impact for pre-375M artifacts."""
    if not ui: return None
    uc = ui.get("use_consequence")
    if uc is not None: return uc
    legacy = ui.get("gap_impact") or ""
    if legacy == "favorable": return "beneficial"
    if legacy == "adverse":   return "harmful"
    return legacy or None

LEASE = r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\results"

RUNS = {  # label -> run_id (the six matched 370c runs)
    "W1": "lease_review_20260531_031342_8ca215",
    "H1": "lease_review_20260530_231425_370c_H1",
    "H2": "lease_review_20260530_233514_370c_H2",
    "W2": "lease_review_20260531_033520_d117b6",
    "W3": "lease_review_20260531_035647_70f97d",
    "H3": "lease_review_20260530_235847_370c_H3",
}
COLLAPSED = "lease_review_20260529_222051_7c0d32"  # 222051 (Branch 0A)

FLAGGED_STATES = {"missing", "partial_material", "partial_typical", "review_needed"}

def load(rid):
    return json.load(open(f"{LEASE}/{rid}/tenant_0/pipeline_results.json", encoding="utf-8"))

def action_bucket(a):
    """Exact replica of app.js Mode-C bucket derivation (renderSidebar)."""
    ui = a.get("use_impact") or {}
    skip = (_normalize_use_consequence(ui) == "beneficial") or (ui.get("materiality") == "not_applicable")
    cs = a.get("coverage_state")
    pc = a.get("partial_class")
    if (not skip) and (cs in ("potentially_unenforceable", "covered_unfavorable", "missing", "review_needed")
                       or pc == "partial_material"):
        return "needs_attention"
    if pc == "partial_review":
        return "worth_reviewing"
    return "clean"

def stage7_included(a):
    """Replica of _collect_flagged_lps coverage branch (conflicts handled separately)."""
    cs = a.get("coverage_state", "")
    pc = a.get("partial_class", "")
    return (cs in FLAGGED_STATES) or (pc in ("partial_material", "partial_typical"))

def governed_fields(a):
    """Lawyer-visible / governance-determining fields (REAL names; () = mapping/absence note)."""
    ds = a.get("dispute_signal") or {}
    rp = a.get("review_priority_distance_signal") or {}
    vd = a.get("verdict_distance") or {}
    ui = a.get("use_impact") or {}
    return {
        "coverage_state": a.get("coverage_state"),
        "coverage_state_baseline": a.get("coverage_state_baseline"),
        "partial_class": a.get("partial_class"),
        "action_bucket": action_bucket(a),                       # derived (no stored field)
        "requires_attention": a.get("requires_attention"),
        "materiality": a.get("materiality"),
        "dispute_triggered": ds.get("triggered"),
        "dispute_critical_count": ds.get("critical_disputed_count"),
        "lp_confidence(cap)": a.get("lp_confidence"),            # confidence_cap -> lp_confidence
        "review_escalated": rp.get("escalated"),                 # review_priority -> review_priority_distance_signal
        "review_hard_flag": rp.get("hard_flag"),
        "stage7_included": stage7_included(a),                   # included_in_stage7_pass1_input (derived)
        "use_impact_present": bool(ui),
        "use_impact.use_consequence": _normalize_use_consequence(ui),
        "use_impact.materiality": ui.get("materiality"),
        "verdict_distance.severity": vd.get("severity"),
    }

# Governance-determining subset (changing any => lawyer-visible decision-surface change = Class 3)
GOVERNANCE_KEYS = [
    "coverage_state", "action_bucket", "materiality", "dispute_triggered",
    "lp_confidence(cap)", "review_escalated", "review_hard_flag", "stage7_included",
    "use_impact.use_consequence", "use_impact.materiality",
]
# Structural/supporting subset (changes here w/o governance change = Class 2)
STRUCTURAL_KEYS = [
    "coverage_state_baseline", "partial_class", "requires_attention",
    "dispute_critical_count", "use_impact_present", "verdict_distance.severity",
]

# ── Load runs ──
TEXT_KEYS = ["exposure_statement", "exposure_headline", "evidence_summary"]  # narrative, non-governing

data = {lbl: load(rid) for lbl, rid in RUNS.items()}
# Map: lp_id -> {label -> governed_fields}
lp_ids = sorted({a["issue_area_id"] for d in data.values() for a in d["coverage_assessment"]})

per_lp = defaultdict(dict)
per_lp_text = defaultdict(dict)
for lbl, d in data.items():
    by_id = {a["issue_area_id"]: a for a in d["coverage_assessment"]}
    for lp in lp_ids:
        per_lp[lp][lbl] = governed_fields(by_id[lp]) if lp in by_id else None
        per_lp_text[lp][lbl] = ({k: by_id[lp].get(k) for k in TEXT_KEYS} if lp in by_id else None)

# ── Variance + classification ──
class_counts = {1: 0, 2: 0, 3: 0, 4: 0, "stable": 0}
matrix_rows = []
bucket_change_lps = []
stage7_change_lps = []

for lp in lp_ids:
    rows = [per_lp[lp][lbl] for lbl in RUNS]
    present = [r for r in rows if r is not None]
    if len(present) < len(RUNS):
        # LP missing from some run = structural absence
        pass
    changed = []
    for key in (GOVERNANCE_KEYS + STRUCTURAL_KEYS):
        vals = set(json.dumps(r.get(key)) for r in present)
        if len(vals) > 1:
            changed.append(key)
    gov_changed = [k for k in changed if k in GOVERNANCE_KEYS]
    struct_changed = [k for k in changed if k in STRUCTURAL_KEYS]

    if "action_bucket" in gov_changed:
        bucket_change_lps.append(lp)
    if "stage7_included" in gov_changed:
        stage7_change_lps.append(lp)

    # Text-only variance check (for LPs with no governance/structural change)
    text_rows = [per_lp_text[lp][lbl] for lbl in RUNS if per_lp_text[lp][lbl] is not None]
    text_changed = any(
        len(set(json.dumps(r.get(k)) for r in text_rows)) > 1 for k in TEXT_KEYS
    )

    # Classify
    if gov_changed:
        cls = 3
    elif struct_changed:
        cls = 2
    elif text_changed:
        cls = 1
    else:
        cls = "stable"
    class_counts[cls] += 1

    # bucket sequence across runs for the matrix
    buckets = [r["action_bucket"] for r in present]
    cstates = [r["coverage_state"] for r in present]
    s7 = [r["stage7_included"] for r in present]
    matrix_rows.append((lp, cls, gov_changed, struct_changed,
                        "/".join(dict.fromkeys(buckets)), "/".join(dict.fromkeys(cstates)),
                        "/".join(dict.fromkeys(str(x) for x in s7))))

print("=" * 100)
print("PER-LP STAGE 5 VARIANCE MATRIX (six 370c runs)")
print("=" * 100)
print(f"{'LP':7} {'class':6} {'bucket(s)':28} {'coverage_state(s)':30} {'stage7':10} governance_changed")
print("-" * 100)
for lp, cls, gov, struct, buckets, cstates, s7 in matrix_rows:
    print(f"{lp:7} {str(cls):6} {buckets:28} {cstates:30} {s7:10} {gov if gov else ''}")

print("\n" + "=" * 60)
print("CLASS COUNTS:", {k: v for k, v in class_counts.items()})
print(f"Total LPs: {len(lp_ids)}")
print(f"Action bucket changed across identical runs? {'YES' if bucket_change_lps else 'NO'}  {bucket_change_lps}")
print(f"Stage7 inclusion changed across identical runs? {'YES' if stage7_change_lps else 'NO'}  {stage7_change_lps}")

# ── Stage 7 directional opportunity variance (aggregate) ──
print("\n" + "=" * 60)
print("STAGE 7 DIRECTIONAL OPPORTUNITY (per run):")
for lbl, d in data.items():
    sm = (d.get("_stage_data") or {}).get("synthesis_meta") or {}
    gd = sm.get("directional_guard") or {}
    cpfs = d.get("cross_provision_findings") or []
    s7count = sum(1 for a in d["coverage_assessment"] if stage7_included(a))
    print(f"  {lbl}: flagged_lp={sm.get('flagged_lp_count')} stage7_incl(computed)={s7count} "
          f"pass1_dir_cand={gd.get('pass1_directional_candidate_count')} "
          f"total_cpf={len(cpfs)} dir_final={sum(1 for f in cpfs if f.get('finding_type')=='directional_mismatch')}")

# ── Zero-total-CPF watch ──
print("\n" + "=" * 60)
print("ZERO-TOTAL-CPF WATCH:")
zero = [lbl for lbl, d in data.items() if len(d.get("cross_provision_findings") or []) == 0]
print(f"  runs with total_cpf==0: {zero if zero else 'NONE observed'}")

# ── Analysis C: 222051 vs healthy envelope ──
print("\n" + "=" * 60)
print("ANALYSIS C — 222051 vs healthy six-run envelope (Branch 0A):")
dc = load(COLLAPSED)
sm_c = (dc.get("_stage_data") or {}).get("synthesis_meta") or {}
gd_c = sm_c.get("directional_guard") or {}
cpfs_c = dc.get("cross_provision_findings") or []
s7_c = sum(1 for a in dc["coverage_assessment"] if stage7_included(a))
print(f"  222051: flagged_lp={sm_c.get('flagged_lp_count')} stage7_incl(computed)={s7_c} "
      f"pass1_dir_cand={gd_c.get('pass1_directional_candidate_count')} "
      f"total_cpf={len(cpfs_c)} dir_final={sum(1 for f in cpfs_c if f.get('finding_type')=='directional_mismatch')}")
# healthy envelope
heal_flagged = [((d.get('_stage_data') or {}).get('synthesis_meta') or {}).get('flagged_lp_count') for d in data.values()]
heal_s7 = [sum(1 for a in d['coverage_assessment'] if stage7_included(a)) for d in data.values()]
heal_cand = [((d.get('_stage_data') or {}).get('synthesis_meta') or {}).get('directional_guard',{}).get('pass1_directional_candidate_count') for d in data.values()]
print(f"  healthy flagged_lp range: {min(heal_flagged)}-{max(heal_flagged)}")
print(f"  healthy stage7_incl range: {min(heal_s7)}-{max(heal_s7)}")
print(f"  healthy pass1_dir_cand range: {min(heal_cand)}-{max(heal_cand)}")

# Compare 222051 governed fields to healthy per-LP
by_id_c = {a["issue_area_id"]: a for a in dc["coverage_assessment"]}
c_bucket_outliers = []
for lp in lp_ids:
    if lp not in by_id_c: continue
    cval = action_bucket(by_id_c[lp])
    healthy_buckets = set(per_lp[lp][lbl]["action_bucket"] for lbl in RUNS if per_lp[lp][lbl])
    if cval not in healthy_buckets:
        c_bucket_outliers.append((lp, cval, sorted(healthy_buckets)))
print(f"  222051 action-bucket OUTLIERS vs healthy: {c_bucket_outliers if c_bucket_outliers else 'NONE'}")
c_s7_outliers = []
for lp in lp_ids:
    if lp not in by_id_c: continue
    cval = stage7_included(by_id_c[lp])
    healthy = set(per_lp[lp][lbl]["stage7_included"] for lbl in RUNS if per_lp[lp][lbl])
    if cval not in healthy:
        c_s7_outliers.append((lp, cval, sorted(str(x) for x in healthy)))
print(f"  222051 stage7-inclusion OUTLIERS vs healthy: {c_s7_outliers if c_s7_outliers else 'NONE'}")
