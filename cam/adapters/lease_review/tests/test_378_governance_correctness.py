"""Step 378 — Governance-correctness batch: unit tests for DEF-003 through DEF-006 + F8.

Numbered tests match the acceptance criteria in the step 378 brief.
All tests are deterministic (no model calls). Run directly or via pytest.

  python -m cam.adapters.lease_review.tests.test_378_governance_correctness
  pytest cam/adapters/lease_review/tests/test_378_governance_correctness.py -v
"""

import sys
import os

# ── ensure project root is importable ──────────────────────────────────────────
_THIS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from cam.adapters.lease_review.lease_finding_consequence import _merge_finding_verdicts
from cam.adapters.lease_review.lease_verdict_distance import derive_verdict_distance
from cam.adapters.lease_review.lease_p2pp_routing import classify_directional_p2pp

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_result(role, uc, mat, reasoning="test reasoning", completed=True):
    """Make a fake evaluator result for a single finding 'Dir-01'."""
    return {
        "role": role,
        "label": f"eval-{role}",
        "completed": completed,
        "finding_output": {
            "Dir-01": {
                "use_consequence": uc,
                "materiality": mat,
                "use_reasoning": reasoning,
            }
        } if completed else None,
        "error": None if completed else "simulated failure",
    }

def _make_finding(fid="Dir-01"):
    return {"finding_id": fid, "finding_type": "directional_mismatch"}


# ── Test 1: One valid evaluator → insufficient support; must NOT assert, NOT route Risk ──

def test_1_single_evaluator_insufficient_support():
    """DEF-003/F1: 1 valid evaluator cannot assert and cannot route Risk on consequence alone.

    Scenario: 2 of 3 evaluators fail; 1 returns harmful/high.
    Expected: consequence_support_label = "insufficient_support"; use_consequence_source
              will be "insufficient_consequence_support" (not "assessed"); P2'' Rule 1a fires.
    """
    results = [
        _make_result("A", "harmful", "high"),
        _make_result("B", None, None, completed=False),
        _make_result("C", None, None, completed=False),
    ]
    # Remove completed=False from finding_output so _merge sees 0 valid for B, C
    # Simulate: A completes with valid verdict; B, C fail
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    # Must NOT be labeled "assert" or "full_assert"
    assert v["consequence_support_label"] == "insufficient_support", (
        f"Expected insufficient_support, got {v['consequence_support_label']!r}"
    )
    assert v["confidence"] == "insufficient_support", (
        f"Expected confidence=insufficient_support, got {v['confidence']!r}"
    )
    # 1 valid evaluator, 2 failed (invalid/no output)
    assert v["valid_evaluator_count"] == 1, (
        f"Expected 1 valid evaluator, got {v['valid_evaluator_count']}"
    )
    assert v["expected_evaluator_count"] == 3, (
        f"Expected expected_evaluator_count=3, got {v['expected_evaluator_count']}"
    )
    # The agree_str must NOT masquerade as 3-0 or 2-0 (old behavior)
    assert v["evaluator_agreement"] not in ("3-0", "2-0", "assert"), (
        f"evaluator_agreement {v['evaluator_agreement']!r} must not masquerade as full assertion"
    )

    # Now test that the attach path produces insufficient_consequence_support source,
    # which causes P2'' Rule 1a to fire (not "assessed")
    # Simulate what the attach loop does (directly test P2'' routing with the resulting source)
    finding_with_insufficient = {
        "finding_id": "Dir-01",
        "finding_type": "directional_mismatch",
        "use_consequence": "harmful",
        "use_consequence_source": "insufficient_consequence_support",  # NOT "assessed"
        "materiality": "high",
        "materiality_source": "assessed",
        "evaluator_agreement": "3-0",  # even if mismatch_support is adequate
        "mismatch_support": "unanimous",
    }
    routing = classify_directional_p2pp(finding_with_insufficient)
    assert routing["bucket"] == "review_needed", (
        f"1-evaluator insufficient support should route review_needed, got {routing['bucket']!r}"
    )
    assert routing["routing_reason"] == "consequence_not_assessed", (
        f"Expected consequence_not_assessed reason, got {routing['routing_reason']!r}"
    )
    print("PASS test_1_single_evaluator_insufficient_support")


# ── Test 2: Two valid agreeing evaluators → NOT mislabeled 3/3 ───────────────

def test_2_two_valid_evaluators_not_mislabeled_3of3():
    """DEF-003/F1: 2 valid evaluators both agree → 'assert_duo', NOT 'assert' (3/3).

    Provenance records valid_evaluator_count = 2, expected = 3.
    """
    results = [
        _make_result("A", "harmful", "high"),
        _make_result("B", "harmful", "medium"),
        _make_result("C", None, None, completed=False),
    ]
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    assert v["consequence_support_label"] == "duo_assert", (
        f"Expected duo_assert (2 valid agree), got {v['consequence_support_label']!r}"
    )
    assert v["confidence"] == "assert_duo", (
        f"Expected confidence=assert_duo, got {v['confidence']!r}"
    )
    assert v["valid_evaluator_count"] == 2, (
        f"Expected 2 valid evaluators, got {v['valid_evaluator_count']}"
    )
    assert v["expected_evaluator_count"] == 3, (
        f"Expected expected_evaluator_count=3"
    )
    # NOT full assert
    assert v["consequence_support_label"] != "full_assert", "2-of-3 must not be labeled full_assert"
    assert v["evaluator_agreement"] != "3-0", "2 evaluators must not show 3-0 agreement"
    print("PASS test_2_two_valid_evaluators_not_mislabeled_3of3")


# ── Test 3: {high,high,low} materiality → merged = high (majority), not low ──

def test_3_materiality_high_high_low_majority_wins():
    """DEF-004/F2: {high,high,low} materiality → merged = high (2/3 majority), not low.

    Minority (low) preserved in materiality_votes.
    high↔low spread → materiality_disputed = True.
    """
    results = [
        _make_result("A", "harmful", "high"),
        _make_result("B", "harmful", "high"),
        _make_result("C", "harmful", "low"),
    ]
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    assert v["materiality"] == "high", (
        f"Expected majority high materiality, got {v['materiality']!r} (DEF-004: strict-min rejected)"
    )
    assert "low" in v["materiality_votes"], (
        f"Minority 'low' vote must be preserved in materiality_votes: {v['materiality_votes']}"
    )
    assert v["materiality_disputed"] is True, (
        f"high↔low spread must set materiality_disputed=True, got {v['materiality_disputed']}"
    )
    assert v["materiality_agreement"] is not None, "materiality_agreement must be recorded"
    print("PASS test_3_materiality_high_high_low_majority_wins")


# ── Test 4: {high,medium,low} materiality → routes Review Needed, not minimum ──

def test_4_materiality_no_majority_routes_review_needed():
    """DEF-004/F2 PINNED: {high,medium,low} → no majority → route_to_review_needed=True.

    The minimum (low) must NOT be silently selected.
    P2'' must route review_needed (via non-"assessed" source) when no-majority fires.
    """
    results = [
        _make_result("A", "harmful", "high"),
        _make_result("B", "harmful", "medium"),
        _make_result("C", "harmful", "low"),
    ]
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    assert v["materiality_source"] == "no_majority", (
        f"Expected materiality_source=no_majority, got {v['materiality_source']!r}"
    )
    assert v["route_to_review_needed"] is True, (
        f"Expected route_to_review_needed=True for no-majority materiality"
    )
    # The materiality value stored is defensive "low", but routing must be Review Needed
    # Test via the attach path: when route_to_review_needed fires, source becomes
    # "no_majority_materiality" which is not "assessed" → P2'' Rule 1a → review_needed
    finding_no_majority = {
        "finding_id": "Dir-01",
        "finding_type": "directional_mismatch",
        "use_consequence": "harmful",
        "use_consequence_source": "no_majority_materiality",  # set by attach path
        "materiality": "low",
        "materiality_source": "no_majority",
        "evaluator_agreement": "3-0",
        "mismatch_support": "unanimous",
    }
    routing = classify_directional_p2pp(finding_no_majority)
    assert routing["bucket"] == "review_needed", (
        f"No-majority materiality should route review_needed, got {routing['bucket']!r}"
    )
    print("PASS test_4_materiality_no_majority_routes_review_needed")


# ── Test 5: No valid materiality values → materiality_source is NOT "assessed" ──

def test_5_no_valid_materiality_not_assessed():
    """DEF-005/F3: Zero valid materiality returns → materiality_source must NOT be "assessed".

    Scenario: all evaluators return invalid/absent materiality values.
    """
    # Evaluators return valid use_consequence but invalid materiality
    results = [
        {
            "role": "A", "label": "eval-A", "completed": True,
            "finding_output": {"Dir-01": {"use_consequence": "harmful", "materiality": "INVALID_VALUE", "use_reasoning": "r"}},
            "error": None,
        },
        {
            "role": "B", "label": "eval-B", "completed": True,
            "finding_output": {"Dir-01": {"use_consequence": "harmful", "materiality": "", "use_reasoning": "r"}},
            "error": None,
        },
        {
            "role": "C", "label": "eval-C", "completed": True,
            "finding_output": {"Dir-01": {"use_consequence": "harmful", "materiality": None, "use_reasoning": "r"}},
            "error": None,
        },
    ]
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    assert v["materiality_source"] != "assessed", (
        f"materiality_source must NOT be 'assessed' when no valid materiality returned; got {v['materiality_source']!r}"
    )
    assert v["materiality_source"] in ("no_valid_materiality", "no_majority"), (
        f"Expected no_valid_materiality or no_majority, got {v['materiality_source']!r}"
    )
    print("PASS test_5_no_valid_materiality_not_assessed")


# ── Test 6: Unknown verdict string → NOT distance 0 / perfect agreement ──────

def test_6_unknown_verdict_not_distance_zero():
    """DEF-006/F4: Unknown verdict string resolves to 'unclear' (rank 3), NOT 0.

    Previously returned 0 (silent distance-0 = apparent perfect agreement).
    Now returns abs(0 - 3) = 3 when paired with "explicitly_present" (rank 0).
    """
    # Unknown verdict paired with explicitly_present (rank 0): should be distance 3, not 0
    dist = derive_verdict_distance("explicitly_present", "UNKNOWN_VERDICT_XYZ")
    assert dist != 0, (
        f"Unknown verdict must NOT return distance 0 (DEF-006); got {dist}"
    )
    assert dist == 3, (
        f"Unknown verdict treated as 'unclear' (rank 3); distance from explicitly_present (rank 0) = 3; got {dist}"
    )

    # Unknown verdict paired with unknown verdict: both unclear (rank 3 vs 3) = distance 0
    dist2 = derive_verdict_distance("UNKNOWN_A", "UNKNOWN_B")
    assert dist2 == 0, (
        f"Two unknown verdicts (both unclear rank 3) should have distance 0; got {dist2}"
    )

    # Unknown paired with missing (rank 5): should be abs(3-5) = 2
    dist3 = derive_verdict_distance("TYPO_VERDICT", "missing")
    assert dist3 == 2, (
        f"Unknown (rank 3) vs missing (rank 5) should be distance 2; got {dist3}"
    )
    print("PASS test_6_unknown_verdict_not_distance_zero")


# ── Test 7: P2'' fail-safe paths still go Review Needed, not Risk ─────────────

def test_7_p2pp_failsafe_paths_review_needed():
    """P2'' fail-safe: insufficient/unparseable/missing consequence → Review Needed, never Risk.

    Verified against: absent, unknown, insufficient_consequence_support,
    no_majority_materiality source strings.
    """
    # 7a: consequence_source = "absent"
    f_absent = {
        "finding_id": "Dir-01", "finding_type": "directional_mismatch",
        "use_consequence": "harmful", "use_consequence_source": "absent",
        "materiality": "high", "evaluator_agreement": "3-0", "mismatch_support": "unanimous",
    }
    r = classify_directional_p2pp(f_absent)
    assert r["bucket"] == "review_needed", f"absent source should be review_needed, got {r['bucket']}"

    # 7b: consequence_source = "unknown"
    f_unknown = {**f_absent, "use_consequence_source": "unknown"}
    r = classify_directional_p2pp(f_unknown)
    assert r["bucket"] == "review_needed", f"unknown source should be review_needed, got {r['bucket']}"

    # 7c: consequence_source = "insufficient_consequence_support" (DEF-003)
    f_insuff = {**f_absent, "use_consequence_source": "insufficient_consequence_support"}
    r = classify_directional_p2pp(f_insuff)
    assert r["bucket"] == "review_needed", f"insufficient_support should be review_needed, got {r['bucket']}"

    # 7d: consequence_source = "no_majority_materiality" (DEF-004 no-majority path)
    f_no_maj = {**f_absent, "use_consequence_source": "no_majority_materiality"}
    r = classify_directional_p2pp(f_no_maj)
    assert r["bucket"] == "review_needed", f"no_majority_materiality should be review_needed, got {r['bucket']}"

    # 7e: no consequence fields at all (missing)
    f_bare = {"finding_id": "Dir-01", "finding_type": "directional_mismatch"}
    r = classify_directional_p2pp(f_bare)
    assert r["bucket"] == "review_needed", f"bare finding should be review_needed, got {r['bucket']}"

    # 7f: properly assessed, mismatch adequate, harmful + high → Risk (positive control)
    f_risk = {
        "finding_id": "Dir-01", "finding_type": "directional_mismatch",
        "use_consequence": "harmful", "use_consequence_source": "assessed",
        "materiality": "high", "evaluator_agreement": "3-0", "mismatch_support": "unanimous",
    }
    r = classify_directional_p2pp(f_risk)
    assert r["bucket"] == "risk", f"properly assessed harmful+high should be risk, got {r['bucket']}"

    print("PASS test_7_p2pp_failsafe_paths_review_needed")


# ── Bonus: F8a regression — unrecognized consequence value uses correct reason string ──

def test_bonus_f8a_unrecognized_consequence_reason():
    """F8a: assessed source + unrecognized use_consequence → reason is 'unrecognized_consequence_value'."""
    f_unrec = {
        "finding_id": "Dir-01", "finding_type": "directional_mismatch",
        "use_consequence": "TOTALLY_UNKNOWN_VALUE",
        "use_consequence_source": "assessed",
        "materiality": "high",
        "evaluator_agreement": "3-0",
        "mismatch_support": "unanimous",
    }
    r = classify_directional_p2pp(f_unrec)
    assert r["bucket"] == "review_needed", f"unrecognized value should be review_needed, got {r['bucket']}"
    assert r["routing_reason"] == "unrecognized_consequence_value", (
        f"Expected 'unrecognized_consequence_value', got {r['routing_reason']!r}"
    )
    print("PASS test_bonus_f8a_unrecognized_consequence_reason")


# ── Bonus: True 3/3 unanimous → still works as before ────────────────────────

def test_bonus_true_3of3_assert():
    """DEF-003: True 3/3 unanimous → confidence='assert', support_label='full_assert', agree_str='3-0'."""
    results = [
        _make_result("A", "harmful", "high"),
        _make_result("B", "harmful", "high"),
        _make_result("C", "harmful", "high"),
    ]
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    assert v["confidence"] == "assert", f"3/3 unanimous should be assert, got {v['confidence']!r}"
    assert v["consequence_support_label"] == "full_assert", f"Expected full_assert, got {v['consequence_support_label']!r}"
    assert v["evaluator_agreement"] == "3-0", f"Expected 3-0, got {v['evaluator_agreement']!r}"
    assert v["valid_evaluator_count"] == 3
    assert v["expected_evaluator_count"] == 3
    print("PASS test_bonus_true_3of3_assert")


# ── Bonus: F8c — 1-1-1 split stores null reasoning, not misattributed ────────

def test_bonus_f8c_split_reasoning_null():
    """F8c: 1-1-1 split → use_consequence_reasoning = None (not misattributed to evaluator[0])."""
    results = [
        _make_result("A", "harmful", "high", reasoning="A says harmful"),
        _make_result("B", "neutral", "low", reasoning="B says neutral"),
        _make_result("C", "beneficial", "not_applicable", reasoning="C says beneficial"),
    ]
    findings = [_make_finding()]
    merged = _merge_finding_verdicts(results, findings)
    v = merged["Dir-01"]

    assert v["use_consequence"] == "context_dependent", (
        f"1-1-1 split should synthesize context_dependent, got {v['use_consequence']!r}"
    )
    assert v["use_reasoning"] is None, (
        f"F8c: 1-1-1 split should store null reasoning (no adopter), got {v['use_reasoning']!r}"
    )
    print("PASS test_bonus_f8c_split_reasoning_null")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_1_single_evaluator_insufficient_support,
        test_2_two_valid_evaluators_not_mislabeled_3of3,
        test_3_materiality_high_high_low_majority_wins,
        test_4_materiality_no_majority_routes_review_needed,
        test_5_no_valid_materiality_not_assessed,
        test_6_unknown_verdict_not_distance_zero,
        test_7_p2pp_failsafe_paths_review_needed,
        test_bonus_f8a_unrecognized_consequence_reason,
        test_bonus_true_3of3_assert,
        test_bonus_f8c_split_reasoning_null,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Step 378 governance-correctness tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("ALL TESTS PASSED")
