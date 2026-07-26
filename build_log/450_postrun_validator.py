"""INDEPENDENT POST-RUN AUDIT ARTIFACT GENERATOR -- NOT the preregistered §8.2 validator.

Written AFTER the Step-447 outcomes were visible. It is therefore NOT `validate_431.py`, does
NOT produce `431_validation.json`, and its output may NOT be labelled §9.1 for this run: the
preregistered producers were never built (Step 448 root cause), and §8.2 line 209 requires the
§9.1 table to be COPIED FROM those artifacts, never authored.

Read-only against run artifacts. Emits build_log/431_postrun_partial_validation.json.

Criterion texts are quoted verbatim from build_log/431_partB_measurement_instruction.md lines
226-234 and are NOT reinterpreted. Seven criteria are computed. #6 is emitted as a status DERIVED
from two established facts. #3 is emitted as not_established_at_package_layer with the
enforcement half reported separately as a distinct trace-level result.
"""
import hashlib
import json
from datetime import datetime, timezone

SIDECAR = "build_log/431_selection_measurement_sidecar.json"
REPORT = "build_log/431_selection_measurement.md"
OUT = "build_log/431_postrun_partial_validation.json"
SEM = ["parameter_family_relevance", "candidate_support_state",
       "value_applies_to_charge_basis_components", "charge_scope", "text_role",
       "value_completeness"]
DERIVED = "post_run_derived__not_preregistered_validator_output"

d = json.load(open(SIDECAR, encoding="utf-8"))
report = open(REPORT, encoding="utf-8").read()


def judgments():
    for cid, s in d["series"].items():
        for kind in ("canonical_panels", "degraded_panels"):
            for p in s[kind]:
                for role in ("A", "B", "C"):
                    yield cid, s, kind, p, role, p["per_role"][role]


def rec(cid, text, status, details, evidence_artifact, evidence_pointer):
    return {"criterion_id": cid, "criterion_text_verbatim": text, "status": status,
            "artifact_status": DERIVED, "evidence_artifact": evidence_artifact,
            "evidence_pointer": evidence_pointer, "details": details}


records = []

# ---- #1 -------------------------------------------------------------------
unresolved_traces, fields_invalidated, substantive_after_invalidation = 0, 0, 0
inval_reasons = {}
for cid, s, kind, p, role, r in judgments():
    j = r.get("judgment") or {}
    unresolved_traces += len(j.get("_unverified_quote_traces") or [])
    for f, reason in (j.get("_invalidated_fields") or {}).items():
        fields_invalidated += 1
        inval_reasons[reason] = inval_reasons.get(reason, 0) + 1
        if j.get(f) not in ("unclear", "not_assessable", None):
            substantive_after_invalidation += 1
records.append(rec(
    "9.1#1", "No unverified span or unresolved/empty-grounded cited quote entered selection.",
    "computed", {
        "unresolved_quote_traces_recorded": unresolved_traces,
        "fields_invalidated_total": fields_invalidated,
        "invalidation_reasons": inval_reasons,
        "invalidated_fields_still_carrying_a_substantive_value": substantive_after_invalidation,
        "interpretation_note": ("'entered selection' is computed as: an invalidated field still "
                                "carrying a substantive (non-unclear/not_assessable) value. No "
                                "other reading is applied."),
    }, SIDECAR, "series[*].{canonical,degraded}_panels[*].per_role[*].judgment.{_unverified_quote_traces,_invalidated_fields}"))

# ---- #2 -------------------------------------------------------------------
sat, sat_single_id_ok, sat_detail = 0, 0, []
for t in d["certification_traces"]:
    if t["final_certification_state"] != "satisfied":
        continue
    sat += 1
    # (i) the LITERAL §8.1 conjunction, applied without reinterpretation
    ok_ids = [c["candidate_id"] for c in t["per_candidate"]
              if c.get("relevance_ok") and c.get("basis_match") == "match"
              and c.get("text_role_ok") and c.get("value_ok") and c.get("support_ok")
              and c.get("applicability_match") == "applicable"]
    # (ii) the same conjunction with basis_match in {match, not_applicable}. Recorded ONLY as a
    # separate column because SCHEMA_FIXED_NOT_APPLICABLE exempts the basis field for base_rent
    # and rent_adjustment_pct, so no candidate for those parameters can ever satisfy the literal
    # text. Which reading §8.1 intends is NOT decided here.
    ok_ids_incl_na = [c["candidate_id"] for c in t["per_candidate"]
                      if c.get("relevance_ok") and c.get("basis_match") in ("match", "not_applicable")
                      and c.get("text_role_ok") and c.get("value_ok") and c.get("support_ok")
                      and c.get("applicability_match") == "applicable"]
    # (iii) the harness's own marker
    qualified_ids = [c["candidate_id"] for c in t["per_candidate"]
                     if c.get("candidate_qualification") == "qualified"]
    if len(ok_ids) >= 1:
        sat_single_id_ok += 1
    sat_detail.append({"lease": t["lease"], "parameter": t["parameter"],
                       "series_index": t["series_index"],
                       "candidate_ids_supplying_every_property_literal_8_1": ok_ids,
                       "candidate_ids_supplying_every_property_basis_match_or_not_applicable": ok_ids_incl_na,
                       "candidate_ids_marked_qualified_by_harness": qualified_ids,
                       "n_candidates_in_trace": len(t["per_candidate"])})
records.append(rec(
    "9.1#2", "No parameter certified by cross-candidate assembly (validator checks same-id property supply).",
    "computed", {
        "satisfied_traces": sat,
        "satisfied_traces_with_a_single_id_supplying_every_property_LITERAL_8_1": sat_single_id_ok,
        "satisfied_traces_with_a_single_id_under_basis_match_or_not_applicable": sum(
            1 for x in sat_detail if x["candidate_ids_supplying_every_property_basis_match_or_not_applicable"]),
        "satisfied_traces_with_a_harness_qualified_candidate": sum(
            1 for x in sat_detail if x["candidate_ids_marked_qualified_by_harness"]),
        "definitional_gap_not_resolved_here": (
            "§8.1's conjunction names basis_match=match. SCHEMA_FIXED_NOT_APPLICABLE exempts the "
            "basis field for base_rent and rent_adjustment_pct, so those candidates record "
            "basis_match='not_applicable' and CANNOT satisfy the literal text. The literal count "
            "and the not_applicable-inclusive count are both reported; which reading §8.1 intends "
            "is a preregistration question and is NOT decided by this artifact."),
        "per_trace": sat_detail,
        "required_property_conjunction_per_8.1": ("relevance_ok AND basis_match=match AND "
                                                  "text_role_ok AND value_ok AND support_ok AND "
                                                  "applicability_match=applicable, all on one candidate_id"),
    }, SIDECAR, "certification_traces[*].per_candidate[*]"))

# ---- #4 -------------------------------------------------------------------
missing_agreement, sat_with_nonunanimous = 0, 0
sat_certifying_nonunanimous = []
agreement_hist = {}
for t in d["certification_traces"]:
    for c in t["per_candidate"]:
        ab = c.get("agreement_by_field")
        if ab is None:
            if c.get("candidate_qualification") != "absent_this_series":
                missing_agreement += 1
            continue
        for f, st in ab.items():
            agreement_hist[st] = agreement_hist.get(st, 0) + 1
        if t["final_certification_state"] == "satisfied" and any(
                st in ("majority_with_dissent", "split") for st in ab.values()):
            sat_with_nonunanimous += 1
            if c.get("candidate_qualification") == "qualified":
                sat_certifying_nonunanimous.append(
                    {"lease": t["lease"], "parameter": t["parameter"],
                     "series_index": t["series_index"], "candidate_id": c["candidate_id"],
                     "non_unanimous_fields": [f for f, st in ab.items()
                                              if st in ("majority_with_dissent", "split")]})
records.append(rec(
    "9.1#4", "Per-field disagreement preserved; non-unanimous certification blocked (no implicit majority).",
    "computed", {
        "per_candidate_records_missing_agreement_by_field": missing_agreement,
        "agreement_state_histogram": agreement_hist,
        "per_candidate_records_in_satisfied_traces_with_a_non_unanimous_field": sat_with_nonunanimous,
        "QUALIFYING_candidates_in_satisfied_traces_with_a_non_unanimous_field": len(sat_certifying_nonunanimous),
        "qualifying_candidate_non_unanimous_detail": sat_certifying_nonunanimous,
        "scope_note": (
            "Two scopings are reported. The broad count includes NON-certifying candidates in the "
            "same trace (e.g. atlas/base_rent cand_05, the losing stub, carries a non-unanimous "
            "candidate_support_state while the certifying cand_06 is unanimous). The criterion "
            "speaks of non-unanimous CERTIFICATION, so the qualifying-candidate count is reported "
            "separately rather than collapsing the two."),
    }, SIDECAR, "certification_traces[*].per_candidate[*].agreement_by_field"))

# ---- #5 -------------------------------------------------------------------
states, non_notestablished = {}, 0
for t in d["certification_traces"]:
    states[t["final_certification_state"]] = states.get(t["final_certification_state"], 0) + 1
    if (t.get("completeness_provenance") or {}).get("status") != "not_established":
        non_notestablished += 1
records.append(rec(
    "9.1#5", "No terminal `unsatisfied_*` emitted (completeness not_established).",
    "computed", {
        "terminal_state_histogram": states,
        "states_matching_unsatisfied_prefix": [s for s in states if s.startswith("unsatisfied")],
        "traces_whose_completeness_status_is_not_not_established": non_notestablished,
        "total_traces": len(d["certification_traces"]),
    }, SIDECAR, "certification_traces[*].{final_certification_state,completeness_provenance}"))

# ---- #7 -------------------------------------------------------------------
result_lines = [ln for ln in report.splitlines()
                if ln.startswith("- ") and "), series " in ln and ": " in ln]
lines_with_qualifier = [ln for ln in result_lines if "(completeness:" in ln]
records.append(rec(
    "9.1#7", "Every result carries the completeness qualifier per §9.0.",
    "computed", {
        "result_lines_detected": len(result_lines),
        "result_lines_carrying_completeness_qualifier": len(lines_with_qualifier),
        "result_lines_missing_qualifier": [ln for ln in result_lines if "(completeness:" not in ln],
    }, REPORT, "per-result lines"))

# ---- #8 -------------------------------------------------------------------
missing_reason, both_citation_keys, comparison_fields_present = 0, 0, 0
COMP = ["relevance_ok", "basis_match", "text_role_ok", "value_ok", "support_ok",
        "applicability_match", "candidate_qualification"]
njudg = 0
for cid, s, kind, p, role, r in judgments():
    njudg += 1
    j = r.get("judgment") or {}
    if not (j.get("reason") or "").strip():
        missing_reason += 1
    if "candidate_citations" in j and "context_citations" in j:
        both_citation_keys += 1
for t in d["certification_traces"]:
    for c in t["per_candidate"]:
        if c.get("candidate_qualification") == "absent_this_series":
            continue
        if all(k in c for k in COMP):
            comparison_fields_present += 1
records.append(rec(
    "9.1#8", "Complete audit artifact reconstructs each decision (candidate vs context citations distinct; per-candidate comparisons visible; per-panelist reasons retained).",
    "computed", {
        "judgments_total": njudg,
        "judgments_with_distinct_candidate_and_context_citation_keys": both_citation_keys,
        "judgments_missing_a_non_empty_reason": missing_reason,
        "per_candidate_records_carrying_all_comparison_fields": comparison_fields_present,
    }, SIDECAR, "judgment.{candidate_citations,context_citations,reason}; certification_traces[*].per_candidate[*]"))

# ---- #9 -------------------------------------------------------------------
records.append(rec(
    "9.1#9", "No live pipeline file consumes the harness output.",
    "computed", {
        "search": ("grep -rln '431_selection_measurement_sidecar|431_selection_measurement.md|"
                   "431_runtime_seam_capture' --include=*.py --include=*.json --include=*.ts "
                   "--include=*.js . , excluding build_log/"),
        "non_build_log_files_referencing_harness_outputs": [],
        "note": "Search executed in Step 448 and re-executed for this artifact; empty result set.",
    }, "repository", "working tree outside build_log/"))

# ---- #6 : DERIVED from two established facts ------------------------------
sidecar_raw = open(SIDECAR, encoding="utf-8").read()
records.append(rec(
    "9.1#6", "Certified parameters (if any) carry materialized `semantic_support_spans`, not value-only.",
    "derived_from_established_facts", {
        "fact_1_required_field_never_written": {
            "statement": ("No identifier with the prefix 'semantic_support_span' is constructed, "
                          "populated or emitted anywhere in the sanctioned package."),
            "prefix_occurrences_in_sidecar": sidecar_raw.count("semantic_support_span"),
            "prefix_occurrences_in_harness_source": 0,
            "prefix_occurrences_in_output_schema": 0,
            "prefix_occurrences_in_selector_prompt": 0,
            "evidence": "Step 449 Task A.1/A.2",
        },
        "fact_2_antecedent_met": {
            "statement": "The criterion's 'if any' antecedent is satisfied: certifications exist.",
            "satisfied_traces": sum(1 for t in d["certification_traces"]
                                    if t["final_certification_state"] == "satisfied"),
        },
        "derivation": ("The criterion predicates a property of certified parameters on a field the "
                       "package never materialized, while certifications exist. The property is "
                       "therefore not exhibited by the run outputs. This is a derivation from the "
                       "two facts above, not a measurement of the criterion."),
    }, "derived", "Step 449 Task A + certification_traces"))

# ---- #3 : package layer not established; enforcement half reported separately
value_layer = []
for t in d["certification_traces"]:
    if t["final_certification_state"] != "satisfied":
        continue
    for c in t["per_candidate"]:
        if c.get("candidate_qualification") == "absent_this_series":
            continue
        value_layer.append({
            "lease": t["lease"], "parameter": t["parameter"], "series_index": t["series_index"],
            "candidate_id": c["candidate_id"], "value_ok": c.get("value_ok"),
            "support_ok": c.get("support_ok"), "basis_match": c.get("basis_match"),
            "applicability_match": c.get("applicability_match"),
            "candidate_qualification": c.get("candidate_qualification"),
        })
same_id_literal = all(x["candidate_ids_supplying_every_property_literal_8_1"] for x in sat_detail) if sat_detail else None
same_id_incl_na = all(x["candidate_ids_supplying_every_property_basis_match_or_not_applicable"] for x in sat_detail) if sat_detail else None
records.append(rec(
    "9.1#3", "No property borrowed from a semantic-support span to cure a deficient primary.",
    "not_established_at_package_layer", {
        "package_layer": ("The quantification domain is empty: no semantic-support span was ever "
                          "materialized by this package (Step 449 Task A.3, option (c)). The "
                          "prohibition therefore has no domain over which to have been enforced, "
                          "and no package-layer result is emitted."),
        "enforcement_half_reported_separately": {
            "trace_level_result_id": "value_layer_anti_borrowing",
            "note": ("Distinct from the package layer. Reports whether the value supplied for each "
                     "certification came from the same candidate that supplied every other required "
                     "property (§8.1 same-id conjunction, §4 value_ok on the primary)."),
            "satisfied_traces_examined": sat,
            "every_satisfied_trace_has_a_single_id_supplying_all_properties_LITERAL_8_1": same_id_literal,
            "every_satisfied_trace_has_a_single_id_under_basis_match_or_not_applicable": same_id_incl_na,
            "per_certified_candidate_value_layer": value_layer,
        },
    }, SIDECAR, "certification_traces[*].per_candidate[*]; Step 449 Task A.3"))

computed = [r for r in records if r["status"] == "computed"]
artifact = {
    "_artifact": "431_postrun_partial_validation.json",
    "_status": DERIVED,
    "_not": ("This is NOT 431_validation.json and NOT the preregistered §8.2 validator output. It "
             "was produced after the outcomes were visible. Its contents may not be labelled §9.1 "
             "for this run."),
    "_generator": "build_log/450_postrun_validator.py",
    "_generated_utc": datetime.now(timezone.utc).isoformat(),
    "_inputs": {
        "sidecar_sha256": hashlib.sha256(open(SIDECAR, "rb").read()).hexdigest(),
        "report_sha256": hashlib.sha256(open(REPORT, "rb").read()).hexdigest(),
    },
    "package_commit": "d679eec8525fa672724a012f7d1fac0d0d8e7620",
    "package_token": "ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca",
    "criteria": records,
    "conjunction": {
        "_emitted_by": "validator",
        "criteria_computed": len(computed),
        "criteria_derived": 1,
        "criteria_not_established_at_package_layer": 1,
        "total_criteria_in_9_1": 9,
        "computed_criterion_ids": [r["criterion_id"] for r in computed],
        "conjunction_over_computed_criteria_only": True,
        "conjunction_result": None,
        "conjunction_result_note": (
            "No conjunction verdict is emitted. Two of the nine criteria (#3, #6) yield no "
            "measured result, so the nine-way conjunction §9.1 defines is not computable from "
            "these outputs. A conjunction over the seven computed criteria alone would not be "
            "§9.1 and is deliberately left null rather than reported under a name it does not have."
        ),
    },
}
with open(OUT, "w", newline="\n", encoding="utf-8") as f:
    json.dump(artifact, f, indent=2)
print("wrote", OUT)
print("criteria computed:", len(computed), [r["criterion_id"] for r in computed])
print("derived:", [r["criterion_id"] for r in records if r["status"] == "derived_from_established_facts"])
print("not_established_at_package_layer:",
      [r["criterion_id"] for r in records if r["status"] == "not_established_at_package_layer"])
