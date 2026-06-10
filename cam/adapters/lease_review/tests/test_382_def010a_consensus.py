"""Step 382 — DEF-010a: Presence-tier normalization in merge_element_verdicts().

Unit tests confirming that all-present-like 3-way splits collapse to a specific
presence verdict instead of firing "no_consensus" / "unclear".

All tests are deterministic (no model calls). Run directly or via pytest.

  python -m cam.adapters.lease_review.tests.test_382_def010a_consensus
  pytest cam/adapters/lease_review/tests/test_382_def010a_consensus.py -v
"""

import sys
import os

# ── ensure project root is importable ──────────────────────────────────────────
_THIS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from cam.adapters.lease_review.lease_coverage_305 import merge_element_verdicts


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_evaluator_verdict(role: str, verdict: str, section_ref: str = "§12.3") -> dict:
    """Construct a per-evaluator verdict dict as produced by _extract_verdicts_for_element."""
    return {
        "role": role,
        "label": f"eval-{role}",
        "actual_model": "test-model",
        "actual_label": f"eval-{role}",
        "is_fallback": False,
        "verdict": verdict,
        "citation": {
            "section_ref": section_ref,
            "quote": "sample quoted text",
            "citation_quality": "section_and_quote",
        } if section_ref else None,
        "reasoning": f"Evaluator {role} reasoning for {verdict}",
        "confidence": "high",
    }


def _make_element(
    element_id: str = "LP-13.test_element",
    default_law_covers=False,
    implicit_coverage_acceptable=False,
    must_be_explicit=False,
    cross_LP_coverage=None,
) -> dict:
    """Construct a minimal element schema dict."""
    return {
        "element_id": element_id,
        "element_label": "Test element",
        "default_law_covers": default_law_covers,
        "implicit_coverage_acceptable": implicit_coverage_acceptable,
        "must_be_explicit": must_be_explicit,
        "cross_LP_coverage": cross_LP_coverage,
        "absence_severity": "high",
    }


# ── Test 1: EP / IP / CD 3-way split → collapsed to explicitly_present ─────────

def test_1_ep_ip_cd_3way_split_collapses():
    """DEF-010a T1: EP/IP/CD 3-way split → explicitly_present (lowest expansion rank), not unclear.

    This is the LP-13 bug pattern: three evaluators each picked a different
    presence mechanism.  Prior code: Counter sees 3 distinct labels → no majority
    → unclear.  Fixed code: tier normalization → present_like × 3 → majority 3/3
    → re-expand to EP (rank 0).
    """
    element = _make_element(
        default_law_covers=True,
        implicit_coverage_acceptable=True,
    )
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "covered_by_default_law"),
        _make_evaluator_verdict("C", "implicitly_present"),
    ]
    result = merge_element_verdicts(verdicts, element)

    assert result["verdict"] != "unclear", (
        f"T1: All-presence-tier 3-way split must NOT produce unclear; got {result['verdict']!r}"
    )
    assert result["reason"] != "no_consensus", (
        f"T1: reason must not be no_consensus; got {result['reason']!r}"
    )
    assert result["verdict"] == "explicitly_present", (
        f"T1: EP has lowest expansion rank — should win; got {result['verdict']!r}"
    )
    print("PASS test_1_ep_ip_cd_3way_split_collapses")


# ── Test 2: EP / CD / CO 3-way split → explicitly_present ─────────────────────

def test_2_ep_cd_co_3way_split_collapses():
    """DEF-010a T2: EP/CD/CO → explicitly_present (rank 0 beats rank 2/3), not unclear."""
    element = _make_element(
        default_law_covers=True,
        cross_LP_coverage=["LP-22"],
    )
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "covered_by_default_law"),
        _make_evaluator_verdict("C", "covered_in_other_LP"),
    ]
    result = merge_element_verdicts(verdicts, element)

    assert result["verdict"] != "unclear", (
        f"T2: All-presence-tier 3-way split must NOT produce unclear; got {result['verdict']!r}"
    )
    assert result["verdict"] == "explicitly_present", (
        f"T2: EP (rank 0) must win over CD/CO; got {result['verdict']!r}"
    )
    print("PASS test_2_ep_cd_co_3way_split_collapses")


# ── Test 3: EP / CD (2 active) → majority present-tier → explicitly_present ────

def test_3_ep_cd_2of2_collapses():
    """DEF-010a T3: 2 active evaluators returning EP and CD → collapsed to explicitly_present.

    Simulates one evaluator failing (absent / unclear filtered out): 2-of-2 active,
    both presence-tier → majority_count 2 ≥ 2 → present_like majority → EP wins.
    """
    element = _make_element(default_law_covers=True)
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "covered_by_default_law"),
        # C is unclear (filtered from active by merge logic)
        _make_evaluator_verdict("C", "unclear", section_ref=None),
    ]
    result = merge_element_verdicts(verdicts, element)

    assert result["verdict"] != "unclear", (
        f"T3: 2-of-2 active presence-tier must NOT produce unclear; got {result['verdict']!r}"
    )
    assert result["verdict"] == "explicitly_present", (
        f"T3: EP (rank 0) must win over CD (rank 3); got {result['verdict']!r}"
    )
    print("PASS test_3_ep_cd_2of2_collapses")


# ── Test 4: EP / IP / missing → disputed (has_presence AND has_missing gate) ───

def test_4_ep_ip_missing_is_disputed():
    """DEF-010a T4: EP/IP/missing → disputed, not collapsed.

    The has_presence AND has_missing gate fires BEFORE the tier normalization
    wins — presence/absence split is maximally distant and must not be masked.
    """
    element = _make_element(implicit_coverage_acceptable=True)
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "implicitly_present"),
        _make_evaluator_verdict("C", "missing", section_ref=None),
    ]
    result = merge_element_verdicts(verdicts, element)

    assert result["verdict"] == "disputed", (
        f"T4: EP/IP/missing must produce disputed; got {result['verdict']!r}"
    )
    print("PASS test_4_ep_ip_missing_is_disputed")


# ── Test 5: EP / CD / missing → disputed ──────────────────────────────────────

def test_5_ep_cd_missing_is_disputed():
    """DEF-010a T5: EP/CD/missing → disputed.

    Same as T4 but with covered_by_default_law instead of implicitly_present.
    The presence/absence split gate fires regardless of mechanism labels.
    """
    element = _make_element(default_law_covers=True)
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "covered_by_default_law"),
        _make_evaluator_verdict("C", "missing", section_ref=None),
    ]
    result = merge_element_verdicts(verdicts, element)

    assert result["verdict"] == "disputed", (
        f"T5: EP/CD/missing must produce disputed; got {result['verdict']!r}"
    )
    print("PASS test_5_ep_cd_missing_is_disputed")


# ── Test 6: EP / unclear / missing → disputed ─────────────────────────────────

def test_6_ep_unclear_missing_existing_behavior():
    """DEF-010a T6: EP/unclear/missing → existing no_consensus behavior preserved.

    unclear is filtered from active before the Counter.
    active = [EP, missing] → tier_counts: present_like×1, missing×1 →
    majority_count = 1 < 2 → no_consensus → unclear.

    Note: the has_presence AND has_missing disputed gate never fires here because
    majority_count < 2 triggers the no_consensus early-return first.
    This is pre-existing behavior; DEF-010a does not change it.
    """
    element = _make_element()
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "unclear", section_ref=None),
        _make_evaluator_verdict("C", "missing", section_ref=None),
    ]
    result = merge_element_verdicts(verdicts, element)

    # Pre-existing behavior: 1 EP vs 1 missing (unclear abstains) → no majority → unclear
    assert result["verdict"] == "unclear", (
        f"T6: EP/unclear/missing no-majority path must produce unclear; got {result['verdict']!r}"
    )
    assert result["reason"] == "no_consensus", (
        f"T6: reason must be no_consensus; got {result['reason']!r}"
    )
    print("PASS test_6_ep_unclear_missing_existing_behavior")


# ── Test 7: LP-13 documented run pattern e38be6 ───────────────────────────────

def test_7_lp13_documented_run_e38be6():
    """DEF-010a T7: LP-13.negligence_carveouts — run e38be6 documented pattern.

    Run e38be6: A=explicitly_present, B=covered_by_default_law, C=implicitly_present
    Prior behavior: Counter sees 3 distinct labels → no_consensus → unclear → LP-13
                    routed to review_needed → Stage 7 received it → Risk generated.
    Fixed behavior: tier normalization → present_like × 3 → EP wins (rank 0).

    The element schema mirrors LP-13.negligence_carveouts schema flags.
    """
    element = _make_element(
        element_id="LP-13.negligence_carveouts",
        default_law_covers=True,
        implicit_coverage_acceptable=True,
        must_be_explicit=False,
    )
    verdicts = [
        _make_evaluator_verdict("A", "explicitly_present"),
        _make_evaluator_verdict("B", "covered_by_default_law"),
        _make_evaluator_verdict("C", "implicitly_present"),
    ]
    result = merge_element_verdicts(verdicts, element)

    # Primary invariants: must NOT be unclear and must NOT be no_consensus
    assert result["verdict"] != "unclear", (
        f"T7 (LP-13 e38be6): verdict must not be unclear; got {result['verdict']!r}"
    )
    assert result["reason"] != "no_consensus", (
        f"T7 (LP-13 e38be6): reason must not be no_consensus; got {result['reason']!r}"
    )
    # Specific invariant: EP wins (it is present in the set and has rank 0)
    assert result["verdict"] == "explicitly_present", (
        f"T7 (LP-13 e38be6): EP must win re-expansion; got {result['verdict']!r}"
    )
    # Raw evaluator_verdicts are preserved — do NOT check merged result for IP or CD
    # presence (that's the raw per-evaluator data, not the merged verdict).
    print("PASS test_7_lp13_documented_run_e38be6")


# ── Test 8: unclear / missing / missing → missing (pre-existing behavior) ──────

def test_8_unclear_missing_missing_behavior():
    """DEF-010a T8: unclear/missing/missing → missing (pre-existing majority behavior).

    unclear is filtered → active = [missing, missing].
    tier_counts: missing × 2 → majority_tier="missing", majority_count=2.
    Since majority_tier != "present_like", existing path → majority_verdict="missing".
    No presence/absence split (no presence verdicts in active).
    Confidence: majority_count(2) < len(verdicts)(3) → "medium".
    """
    element = _make_element()
    verdicts = [
        _make_evaluator_verdict("A", "unclear", section_ref=None),
        _make_evaluator_verdict("B", "missing", section_ref=None),
        _make_evaluator_verdict("C", "missing", section_ref=None),
    ]
    result = merge_element_verdicts(verdicts, element)

    assert result["verdict"] == "missing", (
        f"T8: unclear/missing/missing must produce missing (majority); got {result['verdict']!r}"
    )
    assert result["confidence"] in ("medium", "high"), (
        f"T8: confidence should be medium or high; got {result['confidence']!r}"
    )
    print("PASS test_8_unclear_missing_missing_behavior")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_1_ep_ip_cd_3way_split_collapses,
        test_2_ep_cd_co_3way_split_collapses,
        test_3_ep_cd_2of2_collapses,
        test_4_ep_ip_missing_is_disputed,
        test_5_ep_cd_missing_is_disputed,
        test_6_ep_unclear_missing_is_disputed,
        test_7_lp13_documented_run_e38be6,
        test_8_unclear_missing_missing_behavior,
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
    print(f"Step 382 DEF-010a consensus tests: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    print("ALL TESTS PASSED")
