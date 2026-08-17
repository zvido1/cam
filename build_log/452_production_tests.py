"""452 Stage-1A test suite — §7.5.

ALL FIXTURES ARE SYNTHETIC LITERALS EMBEDDED BELOW. This suite reads NO L1 run artifact
(§2 Stage-1A constraint) and makes no provider call. Producer of
build_log/452_stage1_test_results.json.

Coverage is reported honestly in three states:
  PASS            — assertion executed and held
  FAIL            — assertion executed and did not hold
  NOT_EXERCISED   — the behaviour requires a Stage-2 production run, which
                    452_ratification_record.md does not authorize. Recorded with the
                    reason, never as a pass.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CAM_ROOT = Path(__file__).resolve().parent.parent
BUILD_LOG = CAM_ROOT / "build_log"

spec = importlib.util.spec_from_file_location("p452", str(BUILD_LOG / "452_production_script.py"))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

# The suite exercises guard behaviour, so the guard must be armed in THIS process too.
# main() arms it in a real invocation; importing the module does not.
P.install_network_guard()

RESULTS = []


def check(area, name, fn, adverse=False):
    try:
        fn()
        RESULTS.append({"area": area, "test": name, "kind": "adverse" if adverse else "positive",
                        "status": "PASS"})
    except AssertionError as e:
        RESULTS.append({"area": area, "test": name, "kind": "adverse" if adverse else "positive",
                        "status": "FAIL", "detail": str(e)[:400]})
    except Exception as e:                                    # noqa: BLE001
        RESULTS.append({"area": area, "test": name, "kind": "adverse" if adverse else "positive",
                        "status": "FAIL", "detail": f"{type(e).__name__}: {e}"[:400]})


def not_exercised(area, name, reason, adverse=True):
    RESULTS.append({"area": area, "test": name, "kind": "adverse" if adverse else "positive",
                    "status": "NOT_EXERCISED", "reason": reason})


def expect_halt(fn, fragment=""):
    try:
        fn()
    except P.ProductionHalt as e:
        assert fragment in str(e), f"halted, but not on {fragment!r}: {e}"
        return
    raise AssertionError("expected ProductionHalt, none raised")


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC FIXTURES — literals only
# ══════════════════════════════════════════════════════════════════════════════

SYN_TEXT = (
    "ARTICLE 1. Base Rent: $10.00 per rentable square foot per annum. "          # 0-62
    "ARTICLE 2. Tenant's Proportionate Share shall mean 40.0%. "                  # 62-119
    "ARTICLE 3. Tenant shall pay Operating Expenses. "                            # 119-166
    "ARTICLE 4. Base Rent: $10.00 per rentable square foot per annum."            # 166-229 (duplicate!)
)
# Offsets COMPUTED against the imported matcher, not hand-counted:
#   base-rent quote  -> [(11, 63), (182, 234)]   duplicated document-wide
#   "Proportionate Share" -> [(85, 104)]
#   "Operating Expenses"  -> [(151, 169)]
CAND_WINDOW = (64, 121)          # ARTICLE 2 — the Proportionate Share sentence
CTX_WINDOW = (0, 172)            # ARTICLES 1-3, excluding the duplicate in ARTICLE 4
BASE_RENT_WINDOW = (0, 64)       # ARTICLE 1 only — where the duplicated quote is unique

def _j(**kw):
    base = {"lease_id": "synth", "parameter": "tenant_share", "candidate_id": "cand_x",
            "series_index": 1, "role": "A", "candidate_citations": [], "context_citations": [],
            "field_support": {}}
    base.update(kw)
    base["judgment_id"] = P.judgment_id(base["lease_id"], base["parameter"],
                                        base["candidate_id"], base["series_index"], base["role"])
    return base


# ══════════════════════════════════════════════════════════════════════════════
# POSITIVE COVERAGE — §7.5
# ══════════════════════════════════════════════════════════════════════════════

def t_identity_formulas():
    a = P.judgment_id("L", "p", "c", 1, "A")
    b = P.judgment_id("L", "p", "c", 1, "B")
    assert a != b, "role must change the id"
    assert a.startswith("J-") and len(a) == 18
    # collision resistance across component boundaries: ["ab","c"] != ["a","bc"]
    assert P._mkid("X-", ["ab", "c"]) != P._mkid("X-", ["a", "bc"]), \
        "canonical JSON must not be ambiguous across component boundaries"
    assert P.support_span_id("h", 1, 2) != P.support_span_id("h", 12, "")


def t_two_window_split():
    """The whole point of R5: a quote duplicated document-wide but unique in-window."""
    q = "Base Rent: $10.00 per rentable square foot per annum"
    doc_wide, _ = P.classify_in_window(SYN_TEXT, q, (0, len(SYN_TEXT)))
    in_window, _ = P.classify_in_window(SYN_TEXT, q, BASE_RENT_WINDOW)
    assert doc_wide == "AMBIGUOUS", f"document-wide should be AMBIGUOUS, got {doc_wide}"
    assert in_window == "VERIFIED", f"window-local should be VERIFIED, got {in_window}"


def t_classification_0_1_2():
    assert P.classify_in_window(SYN_TEXT, "Proportionate Share", CAND_WINDOW)[0] == "VERIFIED"
    assert P.classify_in_window(SYN_TEXT, "no such text anywhere", CAND_WINDOW)[0] == "UNVERIFIED"
    assert P.classify_in_window(SYN_TEXT, "Base Rent: $10.00 per rentable square foot per annum",
                                (0, len(SYN_TEXT)))[0] == "AMBIGUOUS"


def t_empty_support_missing_trace():
    j = _j(field_support={f: {} for f in P.SEMANTIC_FIELDS})
    rec = P.enforce_grounding(j, CAND_WINDOW, CTX_WINDOW, SYN_TEXT, set())
    assert len(rec["missing_support_traces"]) == len(P.SEMANTIC_FIELDS)
    assert all(t["missing_trace_id"].startswith("MT-") for t in rec["missing_support_traces"])
    assert all(f["omitted_from_substantive_aggregation"] for f in rec["per_field"])


def t_invalidation_yields_not_assessable():
    """R7 rules 2+4 — the corrected semantics. NOT `unclear` in the tally, and NOT
    majority_with_dissent."""
    merged, agree = P.merge_agreement(["relevant", "relevant", "relevant"], [False, False, True])
    assert agree == "not_assessable", f"expected not_assessable, got {agree}"
    assert agree != "majority_with_dissent", "invalidation must not manufacture a majority"


def t_two_survivors_not_unanimous():
    """R7 rule 3 — 2/2 is not unanimity by deletion."""
    _, agree = P.merge_agreement(["relevant", "relevant", "not_relevant"], [False, False, True])
    assert agree == "not_assessable"


def t_contested_is_split_not_majority():
    """PA-04 constraint: §5.1's named cases resolve to split."""
    _, a1 = P.merge_agreement(["relevant", "not_relevant", "not_relevant"], [False] * 3)
    _, a2 = P.merge_agreement(["relevant", "relevant", "not_relevant"], [False] * 3)
    assert a1 == "split" and a2 == "split", f"got {a1}, {a2}"
    _, a3 = P.merge_agreement(["relevant", "relevant", "unclear"], [False] * 3)
    assert a3 == "majority_with_dissent", "abstention dissent is the majority_with_dissent case"


def t_failed_trace_boundary():
    j = _j(context_citations=[{"citation_id": "xc1", "quote": "no such text anywhere"}],
           field_support={"text_role": {"context_citation_ids": ["xc1"]}})
    rec = P.enforce_grounding(j, CAND_WINDOW, CTX_WINDOW, SYN_TEXT, set())
    ft = rec["failed_support_traces"]
    assert len(ft) == 1 and ft[0]["failed_trace_id"].startswith("FT-")
    assert ft[0]["classification"] == "UNVERIFIED"


def t_basis_ok_both_branches():
    assert P.basis_ok("tenant_share", "match", ["operating_expenses"], False) is True
    assert P.basis_ok("tenant_share", "mismatch", ["taxes"], False) is False
    assert P.basis_ok("base_rent", None, "not_applicable", True) is True
    assert P.basis_ok("base_rent", None, ["taxes"], True) is False


def t_anti_borrowing_dataflow():
    ok, prov = P.value_ok_dataflow(True, "self_contained")
    assert ok is True and prov["support_span_inputs"] == []
    assert prov["anti_borrowing_dataflow_verified"] is True
    # a support span containing the value cannot rescue a deficient primary
    ok2, _ = P.value_ok_dataflow(False, "cross_reference_only")
    assert ok2 is False, "a deficient primary must stay deficient"


def t_certify_no_implicit_majority():
    pc = [{"candidate_qualification": "not_qualified", "applicability_match": "not_assessable",
           "agreement_by_field": {"text_role": "split"}}]
    assert P.certify(pc, False) == "review_needed_disagreement"
    pc2 = [{"candidate_qualification": "qualified", "applicability_match": "applicable",
            "agreement_by_field": {"text_role": "unanimous"}}]
    assert P.certify(pc2, False) == "satisfied"
    pc3 = [{"candidate_qualification": "not_qualified", "applicability_match": "not_assessable",
            "agreement_by_field": {"text_role": "unanimous"}}]
    assert P.certify(pc3, False) == "review_needed_no_qualifying_candidate"


def t_not_assessable_blocks_satisfied():
    """R7 rule 5."""
    pc = [{"candidate_qualification": "not_qualified", "applicability_match": "applicable",
           "agreement_by_field": {"parameter_family_relevance": "not_assessable"}}]
    assert P.certify(pc, False) == "review_needed_disagreement"


def t_schema_fixed_exempt_from_missing_support():
    j = _j(parameter="base_rent", field_support={})
    j["value_applies_to_charge_basis_components"] = "not_applicable"
    j["charge_scope"] = "not_applicable"
    rec = P.enforce_grounding(j, CAND_WINDOW, CTX_WINDOW, SYN_TEXT,
                              {"value_applies_to_charge_basis_components", "charge_scope"})
    exempt = [f for f in rec["per_field"] if f["classification"] == "EXEMPT_SCHEMA_FIXED"]
    assert len(exempt) == 2, f"expected 2 exempt fields, got {len(exempt)}"


def t_set_a_closure_definition():
    assert len(P.SET_A_FILES) == 18, "§3.3 declares exactly eighteen Set-A files"
    assert len(set(P.SET_A_FILES)) == 18


# ══════════════════════════════════════════════════════════════════════════════
# ADVERSE COVERAGE — §7.5. Each must HALT.
# ══════════════════════════════════════════════════════════════════════════════

def _staging(names):
    d = Path(tempfile.mkdtemp(prefix="t452-", dir=str(BUILD_LOG)))
    for n in names:
        (d / n).write_text("{}", encoding="utf-8")
    return d


def _rm(d):
    for p in sorted(d.rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    d.rmdir()


def t_adv_unexpected_staged_output():
    d = _staging(P.SET_A_FILES + ["surprise.json"])
    try:
        expect_halt(lambda: P.verify_set_a_closure(d), "unexpected")
    finally:
        _rm(d)


def t_adv_missing_staged_output():
    d = _staging(P.SET_A_FILES[:-1])
    try:
        expect_halt(lambda: P.verify_set_a_closure(d), "missing")
    finally:
        _rm(d)


def t_adv_preexisting_target_directory():
    d = _staging(P.SET_A_FILES)
    fake_target = P.TARGET_DIR
    created = False
    try:
        if not fake_target.exists():
            fake_target.mkdir()
            created = True
        expect_halt(lambda: P.promote(d), "already exists")
    finally:
        if created:
            fake_target.rmdir()
        _rm(d)


def t_adv_subprocess_outside_allowlist():
    expect_halt(lambda: P.guarded_git("push", "origin", "main"), "allowlist")


def t_adv_outbound_connection_blocked():
    import socket as _s
    before = P._GUARD["outbound_attempts"]
    try:
        _s.create_connection(("example.invalid", 443), timeout=1)
        raise AssertionError("connection was not blocked")
    except P.ProductionHalt:
        pass
    assert P._GUARD["outbound_attempts"] == before + 1, "attempt must be counted"


def t_adv_failed_primary_pin_mismatch():
    class _CS:
        canonical_text = SYN_TEXT
        source_document_hash = "h"
        canonical_text_hash = "h"
    cand = {"candidate_id": "cand_x", "candidate_start_char": 62, "candidate_end_char": 119,
            "expected_quote": "THIS IS NOT THE PINNED SLICE"}
    expect_halt(lambda: P.build_primary_span("synth", cand, _CS()), "pinned slice")


def t_adv_hash_mismatch_halts_package():
    class _CS:
        canonical_text = SYN_TEXT
        source_document_hash = "h1"
        canonical_text_hash = "h2"
    cand = {"candidate_id": "cand_x", "candidate_start_char": 62, "candidate_end_char": 119}
    expect_halt(lambda: P.build_primary_span("synth", cand, _CS()), "canonical_text_hash")


def t_adv_production_refuses_without_stage2_sanction():
    """The package is built and wired but refuses to produce under a Stage-1-only
    ratification. This is the authorization boundary, tested."""
    rc = P.cmd_produce("any-token")
    assert rc == 2, f"expected refusal exit 2, got {rc}"
    assert P.FAILURE_RECORD.exists(), "failure path must emit a failure record"
    rec = json.loads(P.FAILURE_RECORD.read_text(encoding="utf-8"))
    assert rec["l3_authority"] is False, "failure record must carry no L3 authority"
    assert not P.TARGET_DIR.exists(), "no final-named L3 product may be left behind"
    P.FAILURE_RECORD.unlink()


def t_adv_finalize_refuses():
    assert P.cmd_finalize_record("any-token") == 2


# ══════════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════════

def run():
    check("identity", "frozen identity formulas + collision resistance", t_identity_formulas)
    check("resolution", "two-window split (doc-wide AMBIGUOUS, window VERIFIED)", t_two_window_split)
    check("resolution", "0/1/2+ classification", t_classification_0_1_2)
    check("grounding", "empty field_support -> missing_support_trace", t_empty_support_missing_trace)
    check("grounding", "invalidation -> not_assessable (R7 rules 2,4)", t_invalidation_yields_not_assessable)
    check("grounding", "two survivors are not unanimous (R7 rule 3)", t_two_survivors_not_unanimous)
    check("grounding", "contested = split, not majority_with_dissent (PA-04)", t_contested_is_split_not_majority)
    check("grounding", "failed-trace boundary", t_failed_trace_boundary)
    check("grounding", "schema-fixed not_applicable exempt from missing-support", t_schema_fixed_exempt_from_missing_support)
    check("certification", "parameter-aware basis_ok, both branches", t_basis_ok_both_branches)
    check("certification", "no implicit majority; satisfied requires one qualified id", t_certify_no_implicit_majority)
    check("certification", "not_assessable cannot support satisfied (R7 rule 5)", t_not_assessable_blocks_satisfied)
    check("anti_borrowing", "value_ok dataflow excludes support spans", t_anti_borrowing_dataflow)
    check("closure", "Set-A is exactly eighteen files", t_set_a_closure_definition)

    check("adverse", "unexpected staged output halts", t_adv_unexpected_staged_output, True)
    check("adverse", "missing staged output halts", t_adv_missing_staged_output, True)
    check("adverse", "pre-existing target directory halts", t_adv_preexisting_target_directory, True)
    check("adverse", "subprocess outside allowlist halts", t_adv_subprocess_outside_allowlist, True)
    check("adverse", "outbound connection blocked and counted", t_adv_outbound_connection_blocked, True)
    check("adverse", "failed primary pin halts the package", t_adv_failed_primary_pin_mismatch, True)
    check("adverse", "source/canonical hash mismatch halts", t_adv_hash_mismatch_halts_package, True)
    check("adverse", "production refuses without Stage-2 sanction; failure record carries no authority",
          t_adv_production_refuses_without_stage2_sanction, True)
    check("adverse", "finalize-record refuses", t_adv_finalize_refuses, True)

    # Adverse cases that require an authorized Stage-2 run. Recorded, never passed.
    for name, reason in [
        ("edited working-tree manifest", "requires the Stage-2 runtime gate over a real P452 manifest"),
        ("manifest binding omission", "same"),
        ("manifest binding addition", "same"),
        ("stale CLI token", "requires a minted P452 token"),
        ("stale signed-tag token", "requires a signed P452 tag, which does not exist"),
        ("modified repository-local imported module", "requires the Stage-2 whole-tree gate"),
        ("missing gate record", "gate records are produced by this step; the check runs at Stage 2 (§7.1)"),
        ("gate record marked pass carrying stale input hashes", "same"),
        ("modified L1 input", "requires the Stage-2 before/after input hash comparison"),
        ("output-manifest omission", "requires a produced Set A"),
        ("Set-A file altered between production and finalize-record", "requires both invocations"),
        ("charge_scope determination unresolved", "the determination is a Stage-1B product (§5.0.3)"),
        ("invocation-record write/rename failing after Set-A promotion", "requires a promoted Set A"),
        ("each execution_integrity_status conjunct failing individually", "requires a produced Set A and Set B"),
    ]:
        not_exercised("adverse", name, reason + " — Stage 2 is not authorized by 452_ratification_record.md")

    counts = {}
    for r in RESULTS:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    non_gate = {}
    for rel in ["452_production_script.py", "452_production_tests.py",
                "452_deterministic_rules.json", "452_output_schema.json",
                "452_required_product_inventory.json", "452_ambiguity_ruling.md",
                "452_production_package_instruction_v8.md", "452_ratification_record.md"]:
        p = BUILD_LOG / rel
        if p.exists():
            non_gate["build_log/" + rel] = P.sha256_lf(p)
    out = {
        "_artifact": "452_stage1_test_results.json",
        "_producer": "build_log/452_production_tests.py",
        "_stage": "1A",
        "_fixtures": "SYNTHETIC LITERALS ONLY — no L1 run artifact was read",
        "_generated_utc": datetime.now(timezone.utc).isoformat(),
        # ONE declaration only. This record previously emitted the same 8-entry set twice —
        # once as `non_gate_stage1_artifact_hashes` and once as `input_hashes`. §7.1 has Stage 2
        # recompute "every gate record's declared input hashes"; with two blocks, an edit to one
        # leaves the other stale and the outcome depends on which key the checker reads. A check
        # whose result depends on parse order is the same family as a check that cannot fail.
        # Deduplicated 2026-08-16, before the step-4 freeze.
        "input_hashes": non_gate,
        "results": RESULTS,
        "counts": counts,
        "passed": counts.get("FAIL", 0) == 0,
        "_passed_definition": ("True iff zero FAIL. NOT_EXERCISED entries are reported, never "
                               "counted as passes; each names the Stage-2 authorization it needs."),
    }
    path = BUILD_LOG / "452_stage1_test_results.json"
    path.write_bytes((json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    for r in RESULTS:
        mark = {"PASS": "  ok  ", "FAIL": " FAIL ", "NOT_EXERCISED": " n/e  "}[r["status"]]
        print(f"{mark} [{r['kind']:8}] {r['area']:<14} {r['test']}")
        if r["status"] == "FAIL":
            print("        ", r.get("detail"))
    print()
    print("counts:", counts, " passed:", out["passed"])
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
