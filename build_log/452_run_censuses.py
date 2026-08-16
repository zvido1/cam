"""Producer of the two Stage-1A census gate records (§7.2, §7.3).

Reads NO L1 run artifact. Traces the inventory PER REQUIRED FIELD against the Stage-1A
artifacts and the ratified instruction. Each record hashes the NON-GATE Stage-1 artifacts
(§7.0 step 2) — gate records cannot hash themselves.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

CAM_ROOT = Path(__file__).resolve().parent.parent
BUILD_LOG = CAM_ROOT / "build_log"

NON_GATE_STAGE1 = [
    "build_log/452_production_package_instruction_v8.md",
    "build_log/452_ratification_record.md",
    "build_log/452_production_script.py",
    "build_log/452_production_tests.py",
    "build_log/452_output_schema.json",
    "build_log/452_deterministic_rules.json",
    "build_log/452_required_product_inventory.json",
    "build_log/452_ambiguity_ruling.md",
]
GATE_RECORDS = {"452_stage1_test_results.json", "452_producer_consumer_census.json",
                "452_predicate_reachability_census.json", "452_input_sufficiency.json"}


def sha256_lf(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def non_gate_hashes():
    return {rel: sha256_lf(CAM_ROOT / rel) for rel in NON_GATE_STAGE1 if (CAM_ROOT / rel).exists()}


def script_symbols():
    src = (BUILD_LOG / "452_production_script.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}, src


# ══════════════════════════════════════════════════════════════════════════════
# §7.2 PRODUCER-CONSUMER CENSUS — PER REQUIRED FIELD
# ══════════════════════════════════════════════════════════════════════════════

def producer_head(decl: str) -> str:
    """The producer identity at the head of a declaration, before any commentary."""
    return (decl or "").split("—")[0].split("(")[0].strip().rstrip(",.")


def producer_file(decl: str):
    """The .py file a declaration names, or None if it names no file."""
    m = re.match(r"^([\w./-]+\.py)", producer_head(decl))
    return m.group(1) if m else None


def classify_producer(decl: str) -> str:
    """NONE / UNDETERMINED / PARTIAL / DECLARED / ROLE_STRING.

    §7.2: a path constant, a planned section, or a derivable-later note is not a
    producer. FIXED 2026-08-15 (R21): this previously returned DECLARED for a ROLE
    STRING such as `Code, Stage 1B step 3a`, which is the same category error. That
    bug is why the census passed 72/72 while two §3.1 products had no producing file
    anywhere in the repository.
    """
    d = (decl or "").strip()
    if not d:
        return "ABSENT"
    if d.startswith("NONE"):
        return "NONE"
    if d.startswith("UNDETERMINED"):
        return "UNDETERMINED"
    if "PARTIAL" in d or "ONLY" in d:
        return "PARTIAL"
    return "DECLARED" if producer_file(d) else "ROLE_STRING"


def load_exemptions():
    """R21's CLOSED exemption list, read from the rules file — never compiled in."""
    rules = json.loads((BUILD_LOG / "452_deterministic_rules.json").read_text(encoding="utf-8"))
    ex = rules["R21_producer_binding"]["exemptions"]
    out = {}
    for cls, body in ex.items():
        if not isinstance(body, dict) or "entries" not in body:
            continue  # commentary keys sit alongside the class bodies
        for e in body["entries"]:
            out[e] = cls
    return out


def check_producer_binding(p, exemptions, s31_block):
    """R21 clause 1 then clause 2. Order matters: clause 2 cannot see a role string."""
    decl = str(p.get("expected_producer", ""))
    if decl.startswith("NONE") or decl.startswith("UNDETERMINED"):
        return True, "handled by the supersession / Stage-1B-routing clauses"
    head = producer_head(decl)
    pf = producer_file(decl)
    if pf is None:
        # CLAUSE 1 — the producer is not a file at all.
        if head in exemptions:
            return True, f"clause 1 EXEMPT ({exemptions[head]})"
        return False, (f"CLAUSE 1 VIOLATION: producer {head!r} is not a file and is not in R21's "
                       f"closed exemption list")
    if head in exemptions or pf in exemptions:
        return True, f"clause 2 EXEMPT ({exemptions.get(head) or exemptions.get(pf)})"
    if not (BUILD_LOG / pf).exists() and not (CAM_ROOT / pf).exists():
        return False, f"CLAUSE 1 VIOLATION: producer file {pf!r} does not exist in the repository"
    # CLAUSE 2 — the producer file must itself be a §3.1 artifact.
    if pf not in s31_block:
        return False, (f"CLAUSE 2 VIOLATION: producer {pf!r} exists but is NOT a §3.1 "
                       f"EXPECTED_PACKAGE_ARTIFACTS entry — product bound, producer unbound")
    return True, f"clause 1+2 OK: {pf} is a §3.1 artifact"


def resolve_supersessor(p, by_path, by_section):
    """A NONE product passes iff its own note names the Step-452 product that
    supersedes it. Resolved from the inventory's declared bytes only — never authored
    here. Matches an explicit output path first, then a 452 section reference."""
    text = " ".join(str(p.get(k, "")) for k in ("note", "expected_producer"))
    for path, pid in by_path.items():
        if path in text or path.split("/")[-1] in text and "452_stage2_results" in text:
            return pid, f"names output path `{path}`"
    for sec, pid in by_section.items():
        if f"452 {sec}" in text or f"452 §{sec.lstrip('§')}" in text:
            return pid, f"names section `{sec}`"
    return None, None


def census_producer_consumer():
    inv = json.loads((BUILD_LOG / "452_required_product_inventory.json").read_text(encoding="utf-8"))

    by_path, by_section = {}, {}
    for q in inv["products"]:
        if not q["product_id"].startswith("P452"):
            continue
        if q.get("expected_output_path"):
            by_path[q["expected_output_path"].replace("build_log/", "")] = q["product_id"]
        for sec in str(q.get("source_section", "")).split(","):
            sec = sec.strip()
            if sec.startswith("§") and sec not in ("§3.3",) and sec not in by_section:
                by_section[sec] = q["product_id"]

    # Pass 1 — per-field tracing against the DECLARED SPECIFICATION CHAIN.
    # Byte-presence inside an L1 artifact is §7.4's job at Stage 1B; §2 forbids
    # reading L1 here, so this census must not attempt it.
    prelim = {}
    for p in inv["products"]:
        cls = classify_producer(str(p.get("expected_producer", "")))
        decl = str(p.get("expected_producer", ""))
        fields = []
        for f in p.get("required_fields", []):
            # ROLE_STRING traces here exactly as DECLARED does. Whether a role string is a
            # LEGITIMATE producer is R21 clause 1's question, enforced separately below; a
            # non-exempt role string fails there. Conflating the two made every exempt
            # authoring act (ratifications, rulings, L1-era producers) untraced.
            if cls in ("DECLARED", "ROLE_STRING"):
                traced, why = True, f"declared producer: {decl[:60]}"
            elif cls == "PARTIAL":
                # The entry itself testifies that specific named fields were never written.
                named_absent = f in decl
                traced = not named_absent
                why = (f"declared producer, field not excepted: {decl[:60]}" if traced
                       else "producer entry names THIS FIELD as never written")
            else:  # NONE / UNDETERMINED / ABSENT
                traced, why = False, None
            fields.append({"field": f, "field_producer_traced": bool(traced),
                           "producer_class": cls,
                           "persisted_location": p.get("expected_output_path"),
                           "consuming_check_or_reader": [c["consumer"] for c in p.get("consumers", [])],
                           "traced_in": why})
        prelim[p["product_id"]] = (p, cls, fields)

    # Pass 2 — supersession. A NONE/PARTIAL-gap product passes iff its note names the
    # superseding Step-452 product AND that product itself passes.
    # §7.2 amended clause (2026-08-15): a product whose expected_producer is UNDETERMINED
    # pending a Stage-1B determination passes the Stage-1A census IFF its entry NAMES the
    # Stage-1B check that will resolve it. Stage 1B has exactly two checks (§7.0 step 3).
    # Naming the STAGE is not naming the CHECK.
    STAGE_1B_CHECKS = ["452_input_sufficiency.json", "§7.4",
                       "452_charge_scope_applicability_determination.json"]

    # R21 — producer binding. Read the CLOSED exemption list and §3.1 from the artifacts.
    exemptions = load_exemptions()
    _instr = (BUILD_LOG / "452_production_package_instruction_v8.md").read_text(encoding="utf-8")
    s31_block = _instr[_instr.find("EXPECTED_PACKAGE_ARTIFACTS"):][:4000]

    products, first_missing = [], None
    for p in inv["products"]:
        _, cls, fields = prelim[p["product_id"]]
        pb_ok, pb_why = check_producer_binding(p, exemptions, s31_block)
        has_consumer = bool(p.get("consumers"))
        untraced = [x["field"] for x in fields if not x["field_producer_traced"]]
        entry_text = " ".join(str(p.get(k, "")) for k in ("note", "expected_producer"))
        named_1b = [c for c in STAGE_1B_CHECKS if c in entry_text]
        sup_id, sup_why, sup_passes = None, None, None
        if untraced:
            sup_id, sup_why = resolve_supersessor(p, by_path, by_section)
            if sup_id:
                sp, scls, sfields = prelim[sup_id]
                sup_passes = (scls in ("DECLARED", "ROLE_STRING")
                              and all(x["field_producer_traced"] for x in sfields)
                              and bool(sp.get("consumers")))
        remediated = bool(sup_id) and bool(sup_passes)
        routed_to_1b = cls == "UNDETERMINED" and bool(named_1b)
        all_ok = (not untraced) or remediated or routed_to_1b
        rec = {"product_id": p["product_id"], "temporal_layer": p.get("temporal_layer"),
               "producer_class": cls, "field_count": len(fields),
               "untraced_field_count": len(untraced),
               "superseded_by": sup_id, "supersession_basis": sup_why,
               "superseding_product_passes": sup_passes,
               "stage_1b_check_named": named_1b or None,
               "routed_to_stage_1b": routed_to_1b,
               "all_required_fields_traced": all_ok,
               "has_declared_applicable_consumer": has_consumer,
               "producer_binding_r21_passes": pb_ok,
               "producer_binding_r21_basis": pb_why,
               "product_passes": all_ok and has_consumer and pb_ok, "fields": fields}
        if not rec["product_passes"] and first_missing is None:
            if not pb_ok:
                reason = pb_why
            elif not has_consumer:
                reason = "no declared applicable consumer"
            elif cls == "UNDETERMINED":
                reason = ("producer UNDETERMINED and the entry does NOT name the Stage-1B "
                          "check that will resolve it. The amended clause requires naming the "
                          f"CHECK; naming the STAGE is not enough. Expected one of "
                          f"{STAGE_1B_CHECKS}. Untraced: {untraced[:7]}")
            elif sup_id is None:
                reason = (f"producer class {cls}; note names NO superseding Step-452 "
                          f"product. Untraced: {untraced[:6]}")
            else:
                reason = f"superseding product {sup_id} does not itself pass"
            first_missing = {"product_id": p["product_id"], "first_missing_link": reason}
        products.append(rec)

    passed = first_missing is None
    return {
        "_artifact": "452_producer_consumer_census.json",
        "_producer": "build_log/452_run_censuses.py",
        "_stage": "1A", "_granularity": "PER REQUIRED FIELD, not per product",
        "_tracing_rule": (
            "§7.2 traces the DECLARED SPECIFICATION CHAIN: is a producer named, and is "
            "it a real producer rather than a path constant, a planned section or a "
            "derivable-later note. It does NOT verify that a field's bytes exist inside "
            "an L1 artifact — that is §7.4's job at Stage 1B, and §2 forbids reading L1 "
            "at Stage 1A."),
        "_supersession_rule": (
            "A product whose expected_producer is a declared NONE passes iff its note "
            "names the Step-452 product that supersedes it AND that superseding product "
            "itself passes. Otherwise it halts. Without this rule the census would halt "
            "on the very absences the package exists to remediate."),
        "_generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_hashes": non_gate_hashes(),
        "_gate_records_excluded_from_own_hashing": sorted(GATE_RECORDS),
        "products_examined": len(products),
        "required_fields_examined": sum(x["field_count"] for x in products),
        "products_passing": sum(1 for x in products if x["product_passes"]),
        "first_missing_link": first_missing,
        "passed": passed,
        "eighth_producerless_instance": {
            "_recorded": "2026-08-15, Stage 1B",
            "product_id": "PA-03-completeness-provenance-typed",
            "ordinal": 8,
            "beyond": "Step 451's seven producerless instances",
            "finding": ("P4 wrote completeness_provenance as a STATUS TOKEN ONLY. All 30 "
                        "certification traces carry {\"status\": \"not_established\"} and nothing "
                        "else. Six of the seven Part A §6.4 sub-fields — method, scope, limitations, "
                        "evidence_artifact_id, candidate_generation_policy_version, "
                        "source_document_hash — are absent from EVERY trace."),
            "why_a_product_level_census_missed_it": ("The seeder carried completeness_provenance as "
                                                     "one opaque field inside PB-14. A product-level "
                                                     "census sees a present field; only a per-field "
                                                     "census sees six absent sub-fields inside it."),
            "established_by": "Stage-1B read of build_log/431_selection_measurement_sidecar.json",
        },
        "ninth_producerless_instance": {
            "_recorded": "2026-08-15, Ruling C",
            "field": "candidate_generation_policy_version",
            "inside_product": "PA-03-completeness-provenance-typed",
            "ordinal": 9,
            "IN_KIND_DISTINCTION": ("DO NOT flatten into the count of eight. Instances 1-8 are "
                                    "UNWRITTEN OUTPUTS: a producer should have written them and did "
                                    "not. Instance 9 is a SPECIFIED FIELD WITH NO POSSIBLE REFERENT: "
                                    "Part B expressly does not perform candidate generation, so no "
                                    "candidate-generation policy version could exist to be written. "
                                    "The producer could not exist; it did not merely fail to run."),
            "specified_at": "Part A §6.4, unconditionally, inside a record Part B must emit with "
                            "status: not_established",
            "resolution": "null_with_basis (Ruling C)",
        },
        "products": products,
    }


# ══════════════════════════════════════════════════════════════════════════════
# §7.3 PREDICATE-REACHABILITY CENSUS
# ══════════════════════════════════════════════════════════════════════════════

def census_predicate_reachability():
    rules = json.loads((BUILD_LOG / "452_deterministic_rules.json").read_text(encoding="utf-8"))
    frozen = {(r["criterion"], r["pass"]) for r in rules["R10_logical_exercise_status_split"]["frozen_treatment"]}

    predicates = [
        {"predicate": "basis_ok — basis-bearing branch", "source": "R3",
         "satisfying_assignment": "parameter=tenant_share, basis_match=match", "reachable": True},
        {"predicate": "basis_ok — schema-fixed not_applicable branch", "source": "R3",
         "satisfying_assignment": "parameter=base_rent, basis field=not_applicable, profile declares it",
         "reachable": True,
         "note": "Resolves Part A §6.3's conjunction, which is UNSATISFIABLE as literally written for base_rent and rent_adjustment_pct."},
        {"predicate": "pass_a_l1_fidelity == pass", "source": "§4.2.1",
         "satisfying_assignment": "every L1 judgment represented once, payload unreinterpreted", "reachable": True},
        {"predicate": "incomplete-scope rejection", "source": "R16 tenth check",
         "satisfying_assignment": "no candidate with candidate_support_state==insufficient_context certified", "reachable": True},
        {"predicate": "grounding invalidation -> not_assessable", "source": "R7 rules 2,4",
         "satisfying_assignment": "one role's field invalidated; token becomes not_assessable", "reachable": True},
        {"predicate": "missing-support path", "source": "R6 EMPTY",
         "satisfying_assignment": "field_support empty for a non-exempt field", "reachable": True},
        {"predicate": "materialization_status == complete", "source": "R12",
         "satisfying_assignment": "primary verifies and every subset citation resolves uniquely", "reachable": True},
        {"predicate": "materialization_status == blocked", "source": "R12",
         "satisfying_assignment": "a subset citation is UNVERIFIED/ambiguous/missing", "reachable": True},
        {"predicate": "envelope categories (five)", "source": "§4.8",
         "satisfying_assignment": "each of in_candidate/in_envelope/outside_envelope/unresolvable/empty", "reachable": True},
        {"predicate": "mechanism_disposition axis", "source": "R15", "satisfying_assignment": "all logical_status pass", "reachable": True},
        {"predicate": "execution_integrity axis", "source": "§4.12", "satisfying_assignment": "all eleven conjuncts hold", "reachable": True},
    ]

    # Criteria with a possibly-empty domain — identified, not assumed to be #3 and #6 only.
    empty_domain = [
        {"criterion": "#3", "subject": "semantic-support spans", "why_possibly_empty":
         "P4 never materialized any; a complete package may legitimately carry semantic_support_spans: []",
         "carries_logical_status": True, "carries_exercise_status": True,
         "frozen_treatment_present": ("#3", "Pass A package layer") in frozen or any(c == "#3" for c, _ in frozen)},
        {"criterion": "#6", "subject": "certified packages", "why_possibly_empty":
         "Pass B may produce zero post-enforcement satisfied states (the unseating clause anticipates zero)",
         "carries_logical_status": True, "carries_exercise_status": True,
         "frozen_treatment_present": any(c == "#6" for c, _ in frozen)},
        {"criterion": "#1", "subject": "unverified spans / unresolved cited quotes",
         "why_possibly_empty": "a run in which every cited quote resolves has an empty subject set",
         "carries_logical_status": True, "carries_exercise_status": True,
         "frozen_treatment_present": any(c == "#1" for c, _ in frozen),
         "vacuity_basis": "contingent",
         "RESOLVED": "Table added to R10 under the §7.3 census ruling. EXERCISED in Pass A: Step 450 recorded a non-resolving context citation (cand_03, panel 4, role C, `xc1`), so the domain is non-empty for this run."},
        {"criterion": "#2", "subject": "certified parameters (cross-candidate assembly check)",
         "why_possibly_empty": "if Pass B certifies nothing, there is no certification to check for assembly",
         "carries_logical_status": True, "carries_exercise_status": True,
         "frozen_treatment_present": any(c == "#2" for c, _ in frozen),
         "vacuity_basis": "contingent",
         "RESOLVED": "Table added to R10 under the §7.3 census ruling. EXERCISED in Pass A: fourteen certifications give the same-id check a non-empty domain. Vacuous only under a zero Pass-B count, which the unseating clause anticipates."},
        {"criterion": "#5", "subject": "terminal unsatisfied_* emissions",
         "why_possibly_empty": "completeness is not_established throughout, so the domain is empty BY CONSTRUCTION",
         "carries_logical_status": True, "carries_exercise_status": True,
         "frozen_treatment_present": any(c == "#5" for c, _ in frozen),
         "vacuity_basis": "by_construction",
         "FINDING_STANDS": "Table added to R10, but the finding is NOT closed by the table. Part A §6.4 locks Part B to `status: not_established`, so no terminal `unsatisfied_*` can be emitted by ANY conforming run of this package. #5 is PERMANENTLY UNEXERCISABLE: `pass`/`vacuous` in every conforming execution, with no reachable exercised row.",
         "claim_consequence": "Part A §10's scope fence lists 'completeness-gated terminal negatives (§6.3, all four)' as IN SCOPE. That item is NOT demonstrated by Step 431, Step 447 or Step 452. #5 is the THIRD Part A in-scope item this instrument cannot reach, joining #3 and #6. Must appear in §11's 'established only if exercised' list via the exercise fields, and in the patent supplement's boundary statement.",
         "boundary_rule_check": "Permitted `vacuous`, not laundered: the criterion's own antecedent — `(completeness not_established)` — is what empties the domain, which is exactly the case §4.2.2 allows."},
    ]

    unreachable = [p for p in predicates if not p["reachable"]]
    missing_treatment = [c for c in empty_domain if not c["frozen_treatment_present"]]
    passed = not unreachable and not missing_treatment

    return {
        "_artifact": "452_predicate_reachability_census.json",
        "_producer": "build_log/452_run_censuses.py",
        "_stage": "1A",
        "_generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_hashes": non_gate_hashes(),
        "_gate_records_excluded_from_own_hashing": sorted(GATE_RECORDS),
        "predicates_examined": len(predicates),
        "unreachable_predicates": unreachable,
        "possibly_empty_domain_criteria": empty_domain,
        "_not_asserted_complete": "#3 and #6 are named instances in §4.2.2; this census identified #1, #2 and #5 additionally.",
        "criteria_missing_a_frozen_treatment_table": [c["criterion"] for c in missing_treatment],
        "passed": passed,
        "_passed_definition": "True iff no predicate is unreachable AND every possibly-empty-domain criterion carries both statuses and a frozen treatment table (§4.2.2).",
    }


def main():
    for fn, name in ((census_producer_consumer, "452_producer_consumer_census.json"),
                     (census_predicate_reachability, "452_predicate_reachability_census.json")):
        rec = fn()
        (BUILD_LOG / name).write_bytes(
            (json.dumps(rec, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(f"{name}: passed={rec['passed']}")
        if name.startswith("452_producer"):
            print(f"   products {rec['products_passing']}/{rec['products_examined']}, "
                  f"required fields {rec['required_fields_examined']}")
            if rec["first_missing_link"]:
                print("   FIRST MISSING LINK:", json.dumps(rec["first_missing_link"])[:300])
        else:
            print(f"   predicates {rec['predicates_examined']}, unreachable {len(rec['unreachable_predicates'])}")
            print(f"   possibly-empty-domain criteria: {[c['criterion'] for c in rec['possibly_empty_domain_criteria']]}")
            print(f"   MISSING frozen treatment: {rec['criteria_missing_a_frozen_treatment_table']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
