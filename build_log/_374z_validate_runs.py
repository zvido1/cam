"""Step 374Z exit-criteria validation: recompute 030920 + 181402 with the REAL post-374Z production
functions (derive_lp_state, _classify_materiality, _classify_partial) and confirm the 374Y-Q C3
prediction (LP-08 Improvement->Addressed; LP-27 stays Risk; nothing else moves; dRisk=dPriority=0;
no genuine adverse finding lost). READ-ONLY over stored run JSONs + schema."""
import json
from cam.adapters.lease_review.lease_coverage_305 import derive_lp_state, _OPPOSITE_PARTY
from cam.adapters.lease_review.lease_exposure import _classify_materiality, _classify_partial

SCHEMA = json.load(open("cam/adapters/lease_review/schemas/retail_lease_knowledge.json", encoding="utf-8"))
ELS_BY_LP = {ia["id"]: (ia.get("expected_elements_305") or []) for ia in SCHEMA["issue_areas"]}
POL_BY_ID = {e["element_id"]: e.get("absence_adverse_to")
             for ia in SCHEMA["issue_areas"] for e in (ia.get("expected_elements_305") or []) if isinstance(e, dict)}
PERSP = "tenant"
OPP = _OPPOSITE_PARTY[PERSP]
RUNS = {"030920": "05 Lease Analyzer/results/lease_review_20260602_030920_d0e19e/tenant_0/pipeline_results.json",
        "181402": "05 Lease Analyzer/results/lease_review_20260601_181402_2d1700/tenant_0/pipeline_results.json"}
PRESENCE = {"explicitly_present", "implicitly_present", "covered_by_default_law", "covered_in_other_LP"}


def old_derive(merged, els):
    """Pre-374Z derive_lp_state (polarity-blind) for the governance gate / baseline."""
    if not merged:
        return "review_needed"
    high = {e["element_id"] for e in els if e.get("absence_severity") == "high"}
    if any(r["verdict"] == "unclear" for r in merged):
        return "review_needed"
    if all(r["verdict"] in PRESENCE for r in merged):
        return "covered"
    miss = [r for r in merged if r["verdict"] in ("missing", "disputed")]
    hsm = any(r["element_id"] in high for r in miss)
    total, n = len(merged), len(miss)
    if hsm:
        return "missing" if n > total // 2 else "partial"
    return "partial" if n > 0 else "covered"


def bucket(state, pcls, mat):
    if state in ("covered", "covered_typical", "not_applicable"):
        return "addressed"
    if state == "potentially_unenforceable":
        return "risk"
    ih = (pcls == "partial_material") or (mat == "high")
    sv = "risk" if ih else "improvement"
    if state == "covered_unfavorable":
        return sv
    if state == "missing":
        return sv
    if state == "partial":
        return "improvement" if pcls == "partial_review" else sv
    return "review_needed"


for lbl, path in RUNS.items():
    d = json.load(open("" + path, encoding="utf-8"))
    print("================ RUN %s ================" % lbl)
    flips, lost = [], []
    d_risk = d_pri = 0
    for a in d["coverage_assessment"]:
        pid = a.get("issue_area_id")
        if a.get("coverage_state") == "not_applicable":
            continue
        els = ELS_BY_LP.get(pid, [])
        merged = [{"element_id": e.get("element_id"), "verdict": e.get("verdict"),
                   "label": e.get("element_label")} for e in (a.get("element_verdicts") or [])]
        prod_state = a.get("coverage_state")
        governed = (old_derive(merged, els) == prod_state)
        if not governed:
            continue  # state set by override path (dispute/unclear/unenforceable) — 374Z doesn't move it
        # baseline (pre-374Z): old derive + full missing labels
        old_missing = [e["label"] for e in merged if e["verdict"] in ("missing", "disputed")]
        old_mat = _classify_materiality({"coverage_state": prod_state, "issue_area_id": pid,
                                         "elements_missing": old_missing}, PERSP)
        old_b = bucket(prod_state, _classify_partial({"coverage_state": prod_state}, old_mat), old_mat)
        # post-374Z: new derive + stripped (adverse-only) missing labels
        new_state = derive_lp_state(merged, els, PERSP)
        new_missing = [e["label"] for e in merged
                       if e["verdict"] in ("missing", "disputed") and not (e["verdict"] == "missing" and POL_BY_ID.get(e["element_id"]) == OPP)]
        new_mat = _classify_materiality({"coverage_state": new_state, "issue_area_id": pid,
                                        "elements_missing": new_missing}, PERSP)
        new_b = bucket(new_state, _classify_partial({"coverage_state": new_state}, new_mat), new_mat)
        if new_state != prod_state or new_b != old_b:
            flips.append((pid, prod_state, new_state, old_b, new_b))
            if old_b == "risk":
                d_risk -= 1
                if old_mat == "high":
                    d_pri -= 1
            if new_b == "risk" and old_b != "risk":
                d_risk += 1
            if old_b == "risk" and new_b != "risk":
                lost.append(pid)
    print("  dRisk=%+d  dPriority=%+d  | genuine-adverse-LP-leaving-Risk=%s" % (d_risk, d_pri, lost or "NONE"))
    for f in flips:
        print("    %-7s state %-10s->%-10s | bucket %-11s->%-11s" % f)
    # explicit LP-08 / LP-27 confirmation
    for tgt in ("LP-08", "LP-27"):
        a = next((x for x in d["coverage_assessment"] if x.get("issue_area_id") == tgt), None)
        if not a:
            continue
        els = ELS_BY_LP.get(tgt, [])
        merged = [{"element_id": e.get("element_id"), "verdict": e.get("verdict")} for e in (a.get("element_verdicts") or [])]
        print("    %s: production=%s  new_derive=%s" % (tgt, a.get("coverage_state"), derive_lp_state(merged, els, PERSP)))
    print()
