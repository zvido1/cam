"""Step 372 — Action-Bucket Stability Decomposition (read-only, no reruns).

For each of the 12 bucket-flipping LPs identified in Step 371, traces the causal chain,
identifies the first divergent layer, classifies evidence behavior (E1/E2/E3), and tiers
the flip (1/2/3). Maps to REAL JSON field names; flags absent layers.
"""
import json, hashlib, re
from collections import defaultdict, Counter

LEASE = r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\results"

RUNS = {
    "W1": "lease_review_20260531_031342_8ca215",
    "H1": "lease_review_20260530_231425_370c_H1",
    "H2": "lease_review_20260530_233514_370c_H2",
    "W2": "lease_review_20260531_033520_d117b6",
    "W3": "lease_review_20260531_035647_70f97d",
    "H3": "lease_review_20260530_235847_370c_H3",
}
FLIP_LPS = ['LP-03','LP-05','LP-09','LP-13','LP-16','LP-19',
            'LP-20','LP-22','LP-26','LP-28','LP-29','LP-32']

LP_NAMES = {
    'LP-03':'Lease Term & Renewal','LP-05':'Permitted Use','LP-09':'Subletting & Assignment',
    'LP-13':'Environmental/Hazmat','LP-16':'Parking & Access','LP-19':'Utilities',
    'LP-20':'Exclusivity Protection','LP-22':'SNDA','LP-26':'Quiet Enjoyment',
    'LP-28':'Compliance with Laws','LP-29':'Right of Entry','LP-32':'Environmental Remediation',
}

def load(rid):
    return json.load(open(f"{LEASE}/{rid}/tenant_0/pipeline_results.json", encoding="utf-8"))

def action_bucket(a):
    """Exact replica of app.js Mode-C bucket logic."""
    ui = a.get("use_impact") or {}
    skip = (ui.get("gap_impact") == "favorable") or (ui.get("materiality") == "not_applicable")
    cs = a.get("coverage_state")
    pc = a.get("partial_class")
    if (not skip) and (cs in ("potentially_unenforceable","covered_unfavorable","missing","review_needed")
                       or pc == "partial_material"):
        return "needs_attention"
    if pc == "partial_review":
        return "worth_reviewing"
    return "clean"

def norm_section(ref):
    """Normalise whitespace/punctuation conservatively (do NOT strip legal terms)."""
    if ref is None: return None
    return re.sub(r'\s+', ' ', str(ref).strip())

def quote_hash(q):
    """MD5 of quote (preserves legal language — 'not' matters)."""
    if q is None: return None
    return hashlib.md5(q.strip().encode("utf-8")).hexdigest()[:12]

def get_citation_set(a):
    """All (norm_section, quote_hash) pairs from element_verdicts citations."""
    pairs = set()
    for ev in (a.get("element_verdicts") or []):
        c = ev.get("citation") or {}
        if c:
            pairs.add((norm_section(c.get("section_ref")), quote_hash(c.get("quote"))))
    return pairs

def get_ev_verdicts_key(a):
    """Tuple of (element_id, verdict) for all element_verdicts."""
    return tuple(sorted((ev.get("element_id",""), ev.get("verdict","")) for ev in (a.get("element_verdicts") or [])))

def tier_flip(buckets):
    """Tier the flip type. buckets = set of bucket values observed."""
    has_clean = "clean" in buckets
    has_attn  = "needs_attention" in buckets
    has_rev   = "worth_reviewing" in buckets
    if has_clean and has_attn:
        return 1, "clean vs needs_attention"
    if has_rev and has_attn:
        return 3, "worth_reviewing vs needs_attention"
    if has_clean and has_rev:
        return 3, "clean vs worth_reviewing"
    return 0, "?"

# ── Load data ──
data = {lbl: load(rid) for lbl, rid in RUNS.items()}

# Chain layers in order (with REAL field names):
# 1. per_evaluator_lp_verdicts  (LP-level aggregate per evaluator)
# 2. element_verdicts            (per-element, includes citations)
# 3. coverage_state_baseline     (merged element → baseline, no dispute override)
# 4. coverage_state              (post-dispute/override)
# 5. use_impact.{gap_impact,materiality}  (Stage 5e — persisted in use_impact dict)
# 6. lp_confidence               (= confidence cap — persisted as lp_confidence vs lp_confidence_base)
# 7. review_priority_distance_signal  (escalated/hard_flag)
# 8. action_bucket               (DERIVED — not stored; recomputed from above)

# Layer NOT separately persisted (this is a finding):
#   • element_verdicts merging logic (what turns per-element → coverage_state_baseline)
#   • dispute_signal application (what turns baseline → coverage_state)
#   • use_impact computation (Stage 5e internal model call outputs beyond what's in use_impact dict)
#   — only the final output of each is stored, not the per-sub-step inputs

CHAIN_LAYERS = [
    ("per_evaluator_lp_verdicts", lambda a: json.dumps(sorted((a.get("per_evaluator_lp_verdicts") or {}).items()), sort_keys=True)),
    ("element_verdicts",          lambda a: get_ev_verdicts_key(a)),
    ("coverage_state_baseline",   lambda a: a.get("coverage_state_baseline")),
    ("coverage_state",            lambda a: a.get("coverage_state")),
    ("use_impact.gap_impact",     lambda a: (a.get("use_impact") or {}).get("gap_impact")),
    ("use_impact.materiality",    lambda a: (a.get("use_impact") or {}).get("materiality")),
    ("lp_confidence(cap)",        lambda a: a.get("lp_confidence")),
    ("review_escalated",          lambda a: (a.get("review_priority_distance_signal") or {}).get("escalated")),
    ("review_hard_flag",          lambda a: (a.get("review_priority_distance_signal") or {}).get("hard_flag")),
    ("action_bucket",             lambda a: action_bucket(a)),
]

results = []

for lp in FLIP_LPS:
    rows = {}
    for lbl, d in data.items():
        by_id = {a["issue_area_id"]: a for a in d["coverage_assessment"]}
        rows[lbl] = by_id.get(lp)

    # First divergent layer
    first_div = None
    for layer_name, extractor in CHAIN_LAYERS:
        vals = set()
        for lbl, a in rows.items():
            if a: vals.add(json.dumps(extractor(a)))
        if len(vals) > 1:
            first_div = layer_name
            break

    # Buckets across runs
    buckets = {lbl: action_bucket(a) for lbl, a in rows.items() if a}
    bucket_set = set(buckets.values())
    tier, flip_desc = tier_flip(bucket_set)

    # Evidence classification (E1/E2/E3)
    citation_sets = {lbl: get_citation_set(a) for lbl, a in rows.items() if a}
    ev_verdict_keys = {lbl: get_ev_verdicts_key(a) for lbl, a in rows.items() if a}
    cov_states = {lbl: a.get("coverage_state") for lbl, a in rows.items() if a}

    all_cit_same = (len(set(frozenset(s) for s in citation_sets.values())) == 1)
    any_cit = any(len(s) > 0 for s in citation_sets.values())
    ev_stable = (len(set(ev_verdict_keys.values())) == 1)
    cov_stable = (len(set(cov_states.values())) == 1)

    if not all_cit_same and any_cit:
        evidence_class = "E1"
        evidence_note = "Different section_ref/quote sets cited across runs"
    elif all_cit_same and not ev_stable:
        evidence_class = "E2"
        evidence_note = "Same citations, different element verdicts"
    elif ev_stable and not cov_stable:
        evidence_class = "E3-merge"
        evidence_note = "Same element verdicts, different coverage_state (merge/baseline flip)"
    elif ev_stable and cov_stable:
        evidence_class = "E3-downstream"
        evidence_note = "Same evidence+coverage_state, bucket flips downstream (use_impact/confidence/review)"
    else:
        # Mixed — some E1, some E2 elements
        evidence_class = "E1+E2"
        evidence_note = "Mixed: citation differences AND verdict differences present"

    # citation quality check — is evidence anchoring present but insufficient?
    pres_and_insuf = False
    for lbl, a in rows.items():
        if not a: continue
        for ev in (a.get("element_verdicts") or []):
            if ev.get("verdict") == "explicitly_present" and not ev.get("citation"):
                pres_and_insuf = True  # verdict asserted without citation = present-but-unevidenced

    # bucket-by-run string
    run_buckets = " | ".join(f"{l}:{buckets.get(l,'?')[:5]}" for l in RUNS)

    results.append({
        "lp": lp, "name": LP_NAMES.get(lp, lp),
        "tier": tier, "flip_desc": flip_desc,
        "first_div": first_div,
        "evidence_class": evidence_class,
        "evidence_note": evidence_note,
        "anchor_present_insuf": pres_and_insuf,
        "buckets": run_buckets,
        "bucket_set": bucket_set,
    })

# ── Print per-LP table ──
print("=" * 120)
print("PER-LP DECOMPOSITION TABLE (12 flipping LPs)")
print("=" * 120)
print(f"{'LP':7} {'Tier':5} {'Flip':30} {'First-divergence':28} {'Evid':8} {'Anchor?':9}")
print("-" * 120)
for r in results:
    print(f"{r['lp']:7} T{r['tier']}    {r['flip_desc']:30} {r['first_div']:28} {r['evidence_class']:8} {str(r['anchor_present_insuf']):9}")
print()

print("Bucket-by-run detail:")
for r in results:
    print(f"  {r['lp']:7} {r['buckets']}")
print()

# ── First-divergence histogram ──
fdiv_counts = Counter(r["first_div"] for r in results)
print("FIRST-DIVERGENCE HISTOGRAM:")
for layer, n in sorted(fdiv_counts.items(), key=lambda x: -x[1]):
    print(f"  {layer:28}: {n}")
print()

# ── E1/E2/E3 counts ──
eclass_counts = Counter(r["evidence_class"] for r in results)
print("EVIDENCE CLASS COUNTS (E1/E2/E3):")
for cls, n in sorted(eclass_counts.items(), key=lambda x: -x[1]):
    note = [rr["evidence_note"] for rr in results if rr["evidence_class"]==cls]
    print(f"  {cls}: {n}  — {note[0] if note else ''}")
print()

# ── Tier counts ──
tier_counts = Counter(r["tier"] for r in results)
print("TIER COUNTS:")
for t in [1, 2, 3, 0]:
    print(f"  Tier {t}: {tier_counts.get(t,0)}")
print()

# ── Evidence anchoring ──
n_anchor_insuf = sum(1 for r in results if r["anchor_present_insuf"])
print(f"EVIDENCE ANCHORING PRESENT-BUT-INSUFFICIENT: {n_anchor_insuf}/{len(results)} LPs have 'explicitly_present' verdict with no citation")
print()

# ── Unpersisted layers ──
print("UNPERSISTED CHAIN LAYERS (cannot be audited for stability):")
print("  1. element_verdicts MERGE LOGIC — the rule that maps per-element verdicts to")
print("     coverage_state_baseline is not separately persisted; only the output is stored.")
print("  2. dispute_signal APPLICATION — the override that coverage_state_baseline -> coverage_state")
print("     is computable but the intermediate 'pre-dispute state' is not separately stored.")
print("  3. Stage 5e COMPUTATION — use_impact is persisted as a dict, but the model call")
print("     that produced it (prompt, raw response, chain-of-thought) is not stored.")
print("  4. ACTION BUCKET — not stored at all; re-derived from coverage_state + partial_class + use_impact.")
