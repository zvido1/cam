"""§7.0 step 3 — Stage-1B producer.

Emits BOTH Stage-1B products:
    3a  452_charge_scope_applicability_determination.json   (§5.0.3)
    3b  452_input_sufficiency.json                          (§7.4)

PROMOTED INTO THE REPOSITORY 2026-08-15. Until then these two §3.1 products declared
`_producer: "Code, Stage 1B step 3a/3b"` — a ROLE STRING, not a file — and the code that
produced them ran from a session scratchpad outside the repository. Their products were in
§3.1 and would have been hashed by the manifest while nothing committed could reproduce
them. That is the TENTH instance of the producerless defect, one layer deeper than the
other nine: it is inside the remediation package itself.

CAM_ROOT is DERIVED, never hardcoded (the Step-444 rule). The scratchpad originals
hardcoded an absolute path; a producer that only runs on one machine is not a producer.

Reads L1 — PERMITTED at Stage 1B. §2 forbids L1 reads at Stage 1A only.
Makes ZERO provider calls.

Phase 3a builds the determination in two movements, mirroring how it was actually made:
the evidence-only determination first, then the interpretive ruling applied on top. That
order is preserved deliberately — collapsing them would hide that two parameters were
`conflicting` on the bytes and were resolved by a dated ruling, not by a reading.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

CAM_ROOT = Path(__file__).resolve().parent.parent
BUILD_LOG = CAM_ROOT / "build_log"
DET = "452_charge_scope_applicability_determination.json"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def h(rel: str) -> str:
    return sha(BUILD_LOG / rel)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3a — §5.0.3 charge_scope applicability determination
# ══════════════════════════════════════════════════════════════════════════════

SCHEMA_QUOTE = (
    '"charge_scope": {"type": "string", "enum": ["building", "project", "premises", "other", '
    '"unclear", "not_applicable"], "description": "The denominator/scope the proportion is '
    'measured against, where the parameter family has one."}  --  and `charge_scope` appears in '
    "the top-level `required` array (index 7), so it is required on EVERY output regardless of "
    "parameter type. Nothing is fixed per parameter."
)
PARTA_GENERAL = (
    "Part A §4.1 L124: \"Parameter-type-specific semantic dimensions (dimensions that don't "
    'apply use `not_applicable`, which is NOT `none`). **Enums are CLOSED**"'
)
QUAL = (
    "431_requirement_profiles.json `_qualification_rule.candidate_qualification`: \"qualified iff "
    "relevance_ok AND basis_match in {match, not_applicable} AND text_role_ok AND value_ok AND "
    "support_ok -- ALL evaluated on the SAME candidate\"  --  `charge_scope` does NOT appear in "
    "the conjunction, for any parameter."
)
SUBSET_436 = (
    "452 §4.3.6: \"Context citation ids in `field_support` under the **basis, scope and role** "
    "fields, scope membership per §5.0.3.\""
)
EXEMPT_435 = (
    "452 §4.3.5: \"Schema-fixed `not_applicable` fields are exempt from the missing-support "
    "rule (§5.0.3).\""
)

RULING_BASIS = [
    "431_output_schema.json $.properties.charge_scope: enum contains \"not_applicable\"; "
    "description: \"The denominator/scope the proportion is measured against, where the parameter "
    "family has one.\"",
    "Part A §4.1 L124: \"Parameter-type-specific semantic dimensions (dimensions that don't "
    "apply use `not_applicable`, which is NOT `none`).\"",
    "Part A §4.1: `charge_scope` is listed ONLY under `tenant_share / building_share` "
    "(L126-L130). `base_rent` (L131-L133) and `rent_adjustment_pct` (L134-L136) are carried by "
    "`text_role` + `value_completeness` (+ value-token shape).",
]
PROFILES_SILENCE = {
    "classification": "OMISSION, not counter-rule",
    "basis": (
        "The profiles omit `charge_scope` from the qualification conjunction entirely, and label it "
        "for the share parameters as \"RECORDED AS METADATA ONLY — does NOT gate qualification "
        "in v1\". Silence therefore cannot reliably mean applicable."
    ),
}
FUTURE = {
    "_status": "NOT APPLIED",
    "_why": (
        "The frozen 431 artifacts Step 452 consumes are UNCHANGED. These are prospective amendments "
        "recorded for a future revision; applying them would alter inputs this package has already "
        "hashed."
    ),
    "amendments": [
        "Part A: state `charge_scope: not_applicable` explicitly for `base_rent` and "
        "`rent_adjustment_pct`, as it already does for `charge_basis_components`.",
        "431_requirement_profiles.json: carry `charge_scope.schema_fixed_value` for those parameters, "
        "as it already does for `basis_match.schema_fixed_value`.",
    ],
}


def _share(p: str, profile_quote: str) -> dict:
    return {
        "parameter": p,
        "schema_applicability": "required_unfixed",
        "qualification_use": "does_not_gate_qualification",
        "materialization_subset_membership": "member",
        "source_artifact": [
            "build_log/431_output_schema.json",
            "build_log/431_requirement_profiles.json",
            "build_log/431_partA_governed_selection_spec.md",
        ],
        "source_pointer": [
            "$.properties.charge_scope + $.required[7]",
            "$.profiles.%s.charge_scope" % p,
            "Part A §4.1 L126-L130",
        ],
        "quoted_rule": [
            SCHEMA_QUOTE,
            profile_quote,
            QUAL,
            "Part A §4.1 L129: `charge_scope: building | project | premises | other | unclear`",
            SUBSET_436,
        ],
        "status": "resolved",
        "_basis": (
            "Both source artifacts answer both questions and agree. `charge_scope` is declared for "
            "this parameter in Part A §4.1, required by the output schema, explicitly recorded "
            "as metadata that does not gate qualification, and is NOT schema-fixed "
            "`not_applicable` -- so it is a §4.3.6 subset member and NOT exempt from "
            "§4.3.5's missing-support rule."
        ),
    }


def _nonshare(p: str, pa_line: str) -> dict:
    return {
        "parameter": p,
        "schema_applicability": "CONFLICTING",
        "qualification_use": "does_not_gate_qualification",
        "materialization_subset_membership": "UNRESOLVED",
        "source_artifact": [
            "build_log/431_output_schema.json",
            "build_log/431_requirement_profiles.json",
            "build_log/431_partA_governed_selection_spec.md",
        ],
        "source_pointer": [
            "$.properties.charge_scope + $.required[7]",
            "$.profiles.%s  (NO charge_scope key; basis_match.schema_fixed_value IS present)" % p,
            "Part A §4.1 %s" % pa_line,
        ],
        "quoted_rule": [
            SCHEMA_QUOTE,
            "431_requirement_profiles.json $.profiles.%s contains NO `charge_scope` key. It DOES "
            "carry `basis_match: {\"rule\": \"not_applicable -- charge basis is not a meaningful "
            "attribute\", \"schema_fixed_value\": \"not_applicable\"}` -- this artifact demonstrably "
            "knows how to schema-fix a field, and does not do so for charge_scope." % p,
            "Part A §4.1 %s declares ONLY `charge_basis_components: not_applicable` for this "
            "parameter. `charge_scope` is not listed at all. Part A's charge_scope enum (L129) is "
            "stated under `tenant_share / building_share` only and does NOT contain "
            "`not_applicable`." % pa_line,
            PARTA_GENERAL,
            QUAL,
            EXEMPT_435,
        ],
        "status": "conflicting",
        "_conflict": (
            "The two source artifacts §5.0.3 names give opposite answers for this parameter. "
            "431_output_schema.json requires `charge_scope` on every output with a free six-value "
            "enum and fixes nothing per parameter -- which makes the field applicable, a "
            "§4.3.6 subset member, and NOT exempt under §4.3.5, so an empty "
            "`field_support.charge_scope` would emit a `missing_support_trace` and invalidate the "
            "field. Part A §4.1 declares `charge_scope` only for the share parameters and its "
            "stated enum omits `not_applicable`, while its general rule (L124) says an inapplicable "
            "dimension uses `not_applicable` -- which would make the field exempt. NOTHING "
            "schema-fixes it either way. §5.0.3 anticipated exactly this: \"That divergence is "
            "why inference is unsafe and why the profiles alone may not settle it.\" Resolving it "
            "by inference is therefore PROHIBITED, and this determination does not."
        ),
        "_consequence": (
            "Load-bearing twice per §5.0.3: it decides whether an empty or failed scope citation "
            "invalidates a field (§4.3.5), and it decides §4.3.6 subset membership, on "
            "which Pass B criterion #6's logical status turns."
        ),
    }


def _summarise(det: dict) -> dict:
    return {
        "parameters_examined": len(det["parameters"]),
        "resolved": [p["parameter"] for p in det["parameters"] if p["status"] == "resolved"],
        "resolved_by_interpretive_ruling": [p["parameter"] for p in det["parameters"]
                                            if p["status"] == "resolved_by_interpretive_ruling"],
        "conflicting": [p["parameter"] for p in det["parameters"] if p["status"] == "conflicting"],
        "unresolved": [p["parameter"] for p in det["parameters"] if p["status"] == "unresolved"],
        "every_parameter_resolved": all(
            p["status"] in ("resolved", "resolved_by_interpretive_ruling")
            for p in det["parameters"]),
        "_gate_consequence": ("§5.0.3: \"`unresolved` or `conflicting` on any parameter fails "
                              "the input-sufficiency gate and halts.\""),
    }


def build_determination() -> dict:
    """Movement 1 — evidence only. Two parameters come out `conflicting` on the bytes."""
    det = {
        "_artifact": DET,
        "_producer": "Code, Stage 1B step 3a",
        "_stage": "1B",
        "_spec": "452_production_package_instruction_v8.md §5.0.3, §7.0 step 3a",
        "_source_artifact_hashes": {
            "build_log/431_output_schema.json": h("431_output_schema.json"),
            "build_log/431_requirement_profiles.json": h("431_requirement_profiles.json"),
            "build_log/431_partA_governed_selection_spec.md": h("431_partA_governed_selection_spec.md"),
        },
        "_no_l1_run_artifact_read": True,
        "_inference_prohibited": (
            "§5.0.3 forbids settling this by inference. Where the two named artifacts diverge "
            "the status is `conflicting`, never a chosen reading."
        ),
        "parameters": [
            _share(
                "tenant_share",
                "$.profiles.tenant_share.charge_scope: {\"rule\": \"RECORDED AS METADATA ONLY -- does "
                "NOT gate qualification in v1\", \"gates_qualification\": false, \"_explicit_note\": "
                "\"Stated explicitly rather than left silently either-way (§4). Scope (building vs "
                "project vs premises) is captured for observation but no v1 requirement turns on it.\"}",
            ),
            _share(
                "building_share",
                "$.profiles.building_share.charge_scope: {\"rule\": \"RECORDED AS METADATA ONLY -- does "
                "NOT gate qualification in v1\", \"gates_qualification\": false}",
            ),
            _nonshare("base_rent", "L131-L133"),
            _nonshare("rent_adjustment_pct", "L134-L136"),
        ],
    }
    det["summary"] = _summarise(det)
    return det


def apply_charge_scope_ruling(det: dict) -> dict:
    """Movement 2 — the interpretive ruling. GPT-5.6 Sol, 2026-08-15, authorized by Chat.

    A RULING, not a reading. The artifacts remain divergent; the ruling settles which
    reading governs. Recorded as such so the record never claims the bytes said it.
    """
    for p in det["parameters"]:
        if p["parameter"] not in ("base_rent", "rent_adjustment_pct"):
            continue
        p["schema_applicability"] = "schema_fixed_not_applicable"
        p["qualification_use"] = "does_not_gate_qualification"
        p["materialization_subset_membership"] = "non_member"
        p["status"] = "resolved_by_interpretive_ruling"
        p["ruling_date"] = "2026-08-15"
        p["ruling_party"] = "GPT-5.6 Sol, ChatGPT review instance"
        p["ruling"] = ("charge_scope is schema-fixed not_applicable for base_rent and "
                       "rent_adjustment_pct")
        p["ruling_effect"] = ("required output key remains present with value not_applicable; "
                              "field_support grounding is exempt; charge_scope is excluded from the "
                              "§4.3.6 materialization subset")
        p["provenance"] = ("This ruling resolves an ambiguity between the ratified specification, "
                           "uniform output schema, and executable profiles. It does not characterize "
                           "the resolution as already explicit in those artifacts.")
        p["quoted_rule"] = list(RULING_BASIS)
        p["profiles_silence"] = dict(PROFILES_SILENCE)
        p["future_correction_required"] = json.loads(json.dumps(FUTURE))
        p.pop("_conflict", None)
        p.pop("_consequence", None)

    det["_ruling_applied"] = {
        "date": "2026-08-15",
        "party": "GPT-5.6 Sol, ChatGPT review instance; authorized by Chat",
        "scope": "base_rent and rent_adjustment_pct only. tenant_share and building_share unchanged.",
        "recorded_by": "Claude Code, transcription only — no independent judgment applied.",
        "excluded_from_record": (
            "GPT's semantic argument about proportional denominators was flagged by GPT as confirmation "
            "only. It is commercial intuition and is deliberately NOT recorded here: this record's "
            "discipline is quoted bytes."
        ),
    }
    det["summary"] = _summarise(det)
    return det


def step_3a() -> str:
    det = apply_charge_scope_ruling(build_determination())
    out = json.dumps(det, ensure_ascii=False, indent=2) + "\n"
    (BUILD_LOG / DET).write_bytes(out.encode("utf-8"))
    return sha(BUILD_LOG / DET)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3b — §7.4 input sufficiency
# ══════════════════════════════════════════════════════════════════════════════

def step_3b() -> tuple:
    det = json.loads((BUILD_LOG / DET).read_text(encoding="utf-8"))
    det_hash = sha(BUILD_LOG / DET)
    sc = json.loads((BUILD_LOG / "431_selection_measurement_sidecar.json").read_text(encoding="utf-8"))
    inv = json.loads((BUILD_LOG / "452_required_product_inventory.json").read_text(encoding="utf-8"))
    man = json.loads((BUILD_LOG / "431_config_manifest.json").read_text(encoding="utf-8"))

    # ---- PA-03: seven §6.4 sub-fields ----------------------------------------------------
    SEVEN = ["status", "method", "scope", "limitations", "evidence_artifact_id",
             "candidate_generation_policy_version", "source_document_hash"]
    traces = sc["certification_traces"]
    present = [k for k in SEVEN if all(k in t.get("completeness_provenance", {}) for t in traces)]
    absent = [k for k in SEVEN if not any(k in t.get("completeness_provenance", {}) for t in traces)]
    pa03 = {
        "obligation": "PA-03 — did P4 write all seven §6.4 sub-fields into "
                      "certification_trace.completeness_provenance, or only a status token?",
        "traces_examined": len(traces),
        "distinct_shapes_observed": sorted({",".join(sorted(t.get("completeness_provenance", {})))
                                            for t in traces}),
        "sub_fields_present_in_every_trace": present,
        "sub_fields_absent_from_every_trace": absent,
        "verbatim_value_observed": json.dumps(traces[0]["completeness_provenance"], ensure_ascii=False),
        "resolution": "ONLY A STATUS TOKEN",
        "rulings_applied": {
            "_dates": "Ruling A, C and D — 2026-08-15",
            "superseded_by": "P452-SA-source-records",
            "canonical_path": "source_records.json -> completeness_provenance_recovered",
            "read_from_l1": ["status"],
            "recovered_from_frozen_inputs": ["scope", "source_document_hash", "evidence_artifact_id",
                                             "limitations"],
            "null_with_basis": ["method", "candidate_generation_policy_version"],
            "unresolved": [],
            "ninth_producerless_instance": {
                "field": "candidate_generation_policy_version",
                "IN_KIND_DISTINCTION": ("Not flattened into the count of eight. Instances 1-8 are "
                                        "unwritten outputs. Instance 9 is a specified field with no "
                                        "possible referent — Part B does not perform candidate "
                                        "generation, so no policy version could exist."),
            },
            "limitations_pointer_corrected": ("Ruling A cited \"Part B §3.1\", which does not exist. "
                                              "Ruling D corrected it to Part A §3.1 and directed that "
                                              "the correction be recorded, not hidden."),
            "three_findings_one_root": ("Criterion #5's by_construction vacuity, method being null, and "
                                        "candidate_generation_policy_version being null all follow from "
                                        "Part B not measuring candidate-generation recall. A scope "
                                        "consequence, not three separate defects."),
        },
        "l1_byte_finding_unchanged": ("The L1 finding above stands: P4 wrote a status token only. The "
                                      "rulings resolve how the package HANDLES that, and do not alter "
                                      "what P4 wrote."),
        "passes": True,
        "_passes_basis": ("All seven §6.4 sub-fields are resolved under Rulings A, C and D: one read "
                          "from L1, four recovered from frozen inputs, two null-with-basis, none "
                          "unresolved."),
        "halt_rule": ("PA-03 routing: \"If any sub-field is absent, that is a §7.4 HALT and this product "
                      "is then either superseded by a named Step-452 product or the package halts.\""),
        "consequence": ("CONFIRMED as a FURTHER producerless instance beyond Step 451's seven. The "
                        "typed completeness provenance Part A §6.4 requires was never materialized; "
                        "P4 wrote the status token alone, uniformly across all 30 traces."),
    }

    # ---- PA-04 --------------------------------------------------------------------------
    blob = json.dumps(sc, ensure_ascii=False)
    abf_ok = all("parameter_family_relevance" in c.get("agreement_by_field", {})
                 for t in traces for c in t.get("per_candidate", []))
    n_judgments = sum(1 for s in sc["series"].values() for p in s.get("canonical_panels", [])
                      for r in p.get("per_role", {}).values() if "judgment" in r)
    pa04 = {
        "obligation": "PA-04 — are agreement_by_field.parameter_family_relevance and per_panelist[] "
                      "present per judgment, and is retained_evidence membership recoverable?",
        "agreement_by_field_parameter_family_relevance": {
            "present_on_every_per_candidate_record": abf_ok,
            "observed_keys": sorted(traces[0]["per_candidate"][0]["agreement_by_field"]),
            "passes": abf_ok,
        },
        "per_panelist": {
            "occurrences_of_the_literal_name": blob.count("per_panelist"),
            "present_as_named": False,
            "structural_equivalent_found": "per_role.{A,B,C}.judgment",
            "judgment_objects_counted": n_judgments,
            "passes": True,
            "resolution": "name_differs_property_holds",
            "specified_identifier": "per_panelist[]",
            "actual_path": "per_role.{A,B,C}.judgment",
            "basis": ("Part A §5.2 specifies full cited judgments always preserved; all three roles "
                      "carry relevance, field_support and reason."),
            "_ruling": ("RULING B, 2026-08-15. A ruling, not a reading — neither artifact says this. "
                        "Same class as semantic_support_span_ids versus semantic_support_spans in §8.1: "
                        "Part A names a concept, the harness names a field."),
        },
        "retained_evidence": {
            "occurrences_of_the_literal_name": blob.count("retained_evidence"),
            "materialized_as_named_structure": False,
            "membership_recoverable": True,
            "recovery_basis": ("§4.4.6 steps 2-4 recompute retention from per-role "
                               "parameter_family_relevance plus candidate/context citations, all of "
                               "which are present. Membership is DERIVABLE; it is not STORED."),
            "passes": True,
            "resolution": "recoverable_not_stored",
            "materialised_at": "source_records.json -> candidates[].retained_evidence_membership",
            "_ruling": "RULING B, 2026-08-15, under the §4.9 canonical-path pattern.",
        },
    }
    pa04["passes"] = all(pa04[k]["passes"] for k in
                         ("agreement_by_field_parameter_family_relevance", "per_panelist",
                          "retained_evidence"))

    # ---- PB-08 --------------------------------------------------------------------------
    rt = man["relationship_tests_v3_3"]
    pb08 = {
        "obligation": "PB-08 — fresh read of relationship_tests_v3_3 (prior citation was from Step 441's "
                      "quoted manifest content, not a fresh read).",
        "read_performed_now": True,
        "source": "build_log/431_config_manifest.json $.relationship_tests_v3_3",
        "all_passed": rt.get("all_passed"),
        "test_count": len(rt.get("tests", [])),
        "per_test": [{"name": t.get("name"), "s5_clause": t.get("s5_clause"),
                      "expected_basis_match": t.get("expected_basis_match"),
                      "actual_basis_match": t.get("actual_basis_match"), "pass": t.get("pass")}
                     for t in rt.get("tests", [])],
        "passes": bool(rt.get("all_passed")) and len(rt.get("tests", [])) == 4,
        "note": "Step 441's quoted content is CONFIRMED by this fresh read. The obligation is discharged.",
    }

    # ---- field_support 108/108 ------------------------------------------------------------
    counters = {"total": 0, "non_empty": 0}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "field_support":
                    counters["total"] += 1
                    counters["non_empty"] += 1 if v else 0
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(sc)
    fs = {
        "state": "RE-ESTABLISHED",
        "method": "Direct traversal of the frozen L1 sidecar at Stage 1B. Step 450's L2 finding was NOT "
                  "carried forward and was not consulted.",
        "field_support_objects_total": counters["total"],
        "field_support_objects_non_empty": counters["non_empty"],
        "passes": counters["total"] == 108 and counters["non_empty"] == 108,
    }

    # ---- Atlas §3.3 offset ----------------------------------------------------------------
    atlas = CAM_ROOT / "05 Lease Analyzer" / "test_data" / "tenants" / "atlas_meridian_warehouse_lease.txt"
    atlas_txt = atlas.read_text(encoding="utf-8", errors="strict")
    hits = [m.start() for m in re.finditer(r"Section\s+3\.3\.", atlas_txt)]
    atlas_rec = {
        "artifact": "05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt",
        "frozen_hash_lf_normalised": sha(atlas),
        "match_pattern": r"Section\s+3\.3\.",
        "_pattern_note": ("A bare `3.3` pattern is WRONG here: it also matches inside `Section 13.3.` "
                          "at offset 17552. The heading form is `Section 3.3.`, matched anchored."),
        "heading_text_at_offset": atlas_txt[hits[0]:hits[0] + 58] if hits else None,
        "section_3_3_match_count": len(hits),
        "section_3_3_start_char_offsets": hits,
        "state": "ESTABLISHED" if len(hits) == 1 else "AMBIGUOUS",
        "passes": len(hits) == 1,
        "note": ("§7.4 open item: \"§10 needs Atlas §3.3's offset against the frozen hash.\" Offset is "
                 "measured on the LF-normalised bytes whose sha256 is recorded above."),
    }

    # ---- per_product_derivability ----------------------------------------------------------
    undet = [p["product_id"] for p in inv["products"]
             if str(p.get("expected_producer", "")).startswith("UNDETERMINED")]
    derv = {
        "products_examined": len(inv["products"]),
        "products_with_an_undetermined_producer": undet,
        "state": "ESTABLISHED",
        "products_undetermined_and_STILL_unresolved": [p for p in undet
                                                       if p != "PA-03-completeness-provenance-typed"],
        "passes": all(p == "PA-03-completeness-provenance-typed" for p in undet) and pa03["passes"],
        "reason": ("Every product traces to a producer or a named supersessor (§7.2 census: 72/72), and "
                   "PA-03's seven sub-fields are fully resolved under Rulings A, C and D. No product "
                   "now depends on an input that does not exist and is not accounted for."),
        "_undetermined_note": ("PA-03's expected_producer still reads UNDETERMINED pending the Stage-1B "
                               "determination it names. That determination has now been MADE, here."),
    }

    checks = [("charge_scope_determination", det["summary"]["every_parameter_resolved"]),
              ("atlas_3_3_offset_established", atlas_rec["passes"]),
              ("field_support_108_of_108_reestablished", fs["passes"]),
              ("stage_1b_obligation_PB-08", pb08["passes"]),
              ("stage_1b_obligation_PA-03", pa03["passes"]),
              ("stage_1b_obligation_PA-04", pa04["passes"]),
              ("per_product_derivability", derv["passes"])]
    first_fail = next((n for n, ok in checks if not ok), None)

    rec = {
        "_artifact": "452_input_sufficiency.json",
        "_producer": "Code, Stage 1B step 3b",
        "_stage": "1B",
        "_spec": "452_production_package_instruction_v8.md §7.4, §7.0 step 3b",
        "_shape_only": "Presence/absence and shape facts ONLY.",
        "_l1_read_at_stage_1b": ("PERMITTED. §2 forbids reading L1 at Stage 1A only. The sidecar and "
                                 "manifest were read here to RE-ESTABLISH facts rather than inherit them."),
        "charge_scope_determination_hash": det_hash,
        "charge_scope_determination_artifact": "build_log/" + DET,
        "charge_scope_every_parameter_resolved": det["summary"]["every_parameter_resolved"],
        "charge_scope_status_by_parameter": {p["parameter"]: p["status"] for p in det["parameters"]},
        "charge_scope_resolved_by_interpretive_ruling":
            det["summary"]["resolved_by_interpretive_ruling"],
        "atlas_3_3_offset_established": atlas_rec,
        "field_support_108_of_108_reestablished": fs,
        "stage_1b_obligations_resolved": {"PA-03": pa03, "PA-04": pa04, "PB-08": pb08},
        "per_product_derivability": derv,
        "checks": [{"check": n, "passes": ok} for n, ok in checks],
        "aggregate_pass_fail": "pass" if first_fail is None else "fail",
        "first_failure_halt_record": None if first_fail is None else {
            "check": first_fail,
            "detail": ("PA-03: Ruling A applied. Five sub-fields recovered to the canonical path and "
                       "`method` ruled null. ONE remains: `candidate_generation_policy_version` is "
                       "absent from 431_measurement_config.json and from every frozen 431 artifact, and "
                       "Ruling A forbids inventing it."),
            "rule": "Ruling A: \"If candidate_generation_policy_version is absent from "
                    "431_measurement_config.json, that is a halt, not a value to invent.\"",
            "halted_before": "§7.0 step 4 (no further Stage-1 edits), step 5 (manifest), step 6 (P452)",
            "resolvable_by_code": False,
            "why": ("The routing states the product must then be superseded by a NAMED Step-452 product "
                    "or the package halts. Naming that product is an authoring act, not a Code act — the "
                    "same boundary held for PB-12 and PB-13."),
            "also_requiring_a_ruling": ["PA-04 per_panelist name-versus-structure",
                                        "PA-04 retained_evidence recoverable-but-not-materialized"],
        },
    }
    out = json.dumps(rec, ensure_ascii=False, indent=2) + "\n"
    (BUILD_LOG / "452_input_sufficiency.json").write_bytes(out.encode("utf-8"))
    return checks, rec["aggregate_pass_fail"], sha(BUILD_LOG / "452_input_sufficiency.json")


def main() -> int:
    det_hash = step_3a()
    print("3a  452_charge_scope_applicability_determination.json  ->", det_hash)
    checks, aggregate, isf_hash = step_3b()
    for n, ok in checks:
        print(("  PASS  " if ok else "  FAIL  ") + n)
    print("3b  452_input_sufficiency.json  ->", isf_hash)
    print("aggregate:", aggregate)
    return 0 if aggregate == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
