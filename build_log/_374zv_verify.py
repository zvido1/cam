"""Step 374Z-V READ-ONLY verification of the fresh post-deploy run vs the 374Y-Q C3 prediction.
Reuses the 374P bucket logic (which reproduced production counts on 030920). No production change."""
import json, os

# Load the proven bucket functions from _374p_recompute.py WITHOUT running its main loop.
_src = open("build_log/_374p_recompute.py", encoding="utf-8").read()
_src = _src[:_src.index("RUNS =")]
_ns = {}
exec(compile(_src, "_374p_recompute_funcs", "exec"), _ns)
action_counts = _ns["action_counts"]; cons_bucket = _ns["cons_bucket"]; hf = _ns["hf"]

FRESH = "05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json"
BASE = "05 Lease Analyzer/results/lease_review_20260602_030920_d0e19e/tenant_0/pipeline_results.json"
P = "tenant"


def load(p):
    d = json.load(open(p, encoding="utf-8"))
    return d.get("coverage_assessment", []), (d.get("cross_provision_findings", []) or []), d


def per_lp_bucket(ca):
    """Per-LP coverage bucket with the same hard_flag flooring action_counts uses."""
    out = {}
    for a in ca:
        st = a.get("coverage_state") or ""
        if st == "not_applicable":
            continue
        b = cons_bucket(a, P)
        if hf(a) and b in ("improvement", "addressed"):
            b = "review_needed"
        out[a.get("issue_area_id")] = b
    return out


ca_f, cpf_f, d_f = load(FRESH)
ca_b, cpf_b, d_b = load(BASE)

print("================ ACTION SUMMARY COUNTS ================")
cf = action_counts(ca_f, cpf_f, P, "current")
cb = action_counts(ca_b, cpf_b, P, "current")
print("  %-14s %6s %6s %6s %6s %6s %6s" % ("run", "Risk", "NeedsRev", "Improve", "Addr", "PriRisk", "Conflict"))
for lbl, c in [("030920 baseline", cb), ("0604 FRESH", cf)]:
    print("  %-14s %6d %6d %6d %6d %6d %6d" % (lbl, c["Risk"], c["NeedsReview"], c["Improvement"],
                                               c["Addressed"], c["PriorityRisks"], c["conflicting_reading"]))
print("  PREDICTED fresh: Risk 20, NeedsReview 24, Improvement 15, Addressed 2 (LP-08 Improve->Addr)")

print("\n================ LP-08 / LP-27 ================")
for tgt in ("LP-08", "LP-27"):
    a = next((x for x in ca_f if x.get("issue_area_id") == tgt), None)
    bb = per_lp_bucket(ca_f).get(tgt)
    print("  %s: state=%s partial_class=%s materiality=%s -> bucket=%s" % (
        tgt, a.get("coverage_state"), a.get("partial_class"), a.get("materiality"), bb))
    print("       elements_missing=%s" % json.dumps(a.get("elements_missing")))
    print("       favorable=%s" % json.dumps(a.get("favorable_or_non_adverse_absences")))
    print("       exposure_headline=%r" % a.get("exposure_headline"))

print("\n================ FAVORABLE-SLOT INVENTORY (fresh run) ================")
n_lp = 0; n_el = 0
for a in ca_f:
    fav = a.get("favorable_or_non_adverse_absences") or []
    if fav:
        n_lp += 1
        for e in fav:
            n_el += 1
            print("  %-7s %-46s adv=%-9s sev=%-7s cross_LP=%s" % (
                a.get("issue_area_id"), (e.get("element_id") or "")[-46:],
                e.get("absence_adverse_to"), e.get("absence_severity"), e.get("cross_LP_coverage")))
print("  -> %d LPs carry favorable absences, %d elements total" % (n_lp, n_el))

print("\n================ RISK-DROP SANITY (no genuine adverse finding lost) ================")
bk_f = per_lp_bucket(ca_f); bk_b = per_lp_bucket(ca_b)
base_risk = {lp for lp, b in bk_b.items() if b == "risk"}
fresh_risk = {lp for lp, b in bk_f.items() if b == "risk"}
dropped = sorted(base_risk - fresh_risk)
added = sorted(fresh_risk - base_risk)
print("  030920 coverage-Risk LPs (%d): %s" % (len(base_risk), sorted(base_risk)))
print("  fresh  coverage-Risk LPs (%d): %s" % (len(fresh_risk), sorted(fresh_risk)))
print("  DROPPED out of Risk (was Risk@030920, not Risk@fresh): %s" % (dropped or "NONE"))
print("  ADDED to Risk (new): %s" % (added or "NONE"))
for lp in dropped:
    a = next((x for x in ca_f if x.get("issue_area_id") == lp), None)
    ab = next((x for x in ca_b if x.get("issue_area_id") == lp), None)
    print("    DROP %s: 030920 state=%s -> fresh state=%s | fresh bucket=%s | favorable=%s" % (
        lp, ab.get("coverage_state"), a.get("coverage_state"), bk_f.get(lp),
        json.dumps(a.get("favorable_or_non_adverse_absences"))))
