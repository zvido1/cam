"""Unit tests for Step 389/391 closed-form routing logic.

Step 391 adds axis2/q_a_confirmed to the schema. All existing tests updated
to pass q_a_confirmed="yes" (the confirmed-specific default) so they remain
valid positive tests. New TestAxis2FourPartConfirmation class tests the
tightening logic specifically.

Tests compute_axis_supported_candidate() and _parse_closed_form_response().
No live model calls. All tests use mock axis_results dicts.

Guard 3 discipline: each test that exercises routing passes axis_results that
include 'reason' and 'citations' fields — these must NOT affect the routing
decision. Tests verify that routing is identical whether or not those fields
are present.
"""

import sys
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import unittest
from cam.adapters.lease_review.lease_closed_form_directional import (
    compute_axis_supported_candidate,
    _parse_closed_form_response,
)


def _make_axis(axis_id: str, question_id: str, answer: str,
               reason: str = "POISONED: this text should not affect routing",
               citations: list = None) -> dict:
    """Build a single axis_result entry with optionally poisoned reason/citations."""
    return {
        "axis_id":     axis_id,
        "question_id": question_id,
        "answer":      answer,
        "reason":      reason,
        "citations":   citations or ["POISON_CITATION"],
    }


def _all_axes(axis2_qa, axis2_qb, axis3_qa, axis3_qb, axis4, axis1,
              axis2_qa_confirmed: str = "yes",
              poison_prose: bool = True) -> list:
    """Build a full 7-element axis_results list (Step 391: includes q_a_confirmed).

    axis2_qa_confirmed defaults to 'yes' so all Step-389 positive tests remain
    valid without modification. Pass axis2_qa_confirmed='no' to test the
    Step-391 generic-category blocking logic.
    """
    r = "POISONED: presence must never create findings" if poison_prose else ""
    c = ["POISON"] if poison_prose else []
    return [
        _make_axis("axis2", "q_a",          axis2_qa,          r, c),
        _make_axis("axis2", "q_a_confirmed", axis2_qa_confirmed, r, c),
        _make_axis("axis2", "q_b",          axis2_qb,          r, c),
        _make_axis("axis3", "q_a",          axis3_qa,          r, c),
        _make_axis("axis3", "q_b",          axis3_qb,          r, c),
        _make_axis("axis4", "standalone",    axis4,             r, c),
        _make_axis("axis1", "standalone",  axis1,    r, c),
    ]


class TestAxis2Routing(unittest.TestCase):

    def test_axis2_yes_no_is_candidate_risk(self):
        """Axis 2 Q-A=yes Q-B=no → axis_supported_candidate, Risk bucket."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertEqual(result["proposed_bucket"], "Risk")
        self.assertIn("axis2", result["supporting_axes"])
        self.assertFalse(result["contested"])

    def test_axis2_yes_unclear_is_contested_review_needed(self):
        """Axis 2 Q-A=yes Q-B=unclear → contested, Review Needed."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "unclear", "no", "n.a.", "no", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertTrue(result["contested"])
        self.assertEqual(result["proposed_bucket"], "Review Needed")

    def test_axis2_yes_yes_no_candidate(self):
        """Axis 2 Q-A=yes Q-B=yes → no issue on Axis 2, no candidate alone."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "yes", "no", "n.a.", "no", "no")
        )
        self.assertFalse(result["axis_supported_candidate"])

    def test_axis2_no_no_candidate(self):
        """Axis 2 Q-A=no → no candidate regardless of Q-B."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "no", "no")
        )
        self.assertFalse(result["axis_supported_candidate"])


class TestAxis3Routing(unittest.TestCase):

    def test_axis3_yes_yes_candidate(self):
        """Axis 3 Q-A=yes Q-B=yes → candidate, Review Needed."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "yes", "yes", "no", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis3", result["supporting_axes"])

    def test_axis3_yes_unclear_contested(self):
        """Axis 3 Q-A=yes Q-B=unclear → contested Review Needed."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "yes", "unclear", "no", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertTrue(result["contested"])

    def test_axis3_yes_no_no_candidate(self):
        """Axis 3 Q-A=yes Q-B=no → no Axis 3 issue."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "yes", "no", "no", "no")
        )
        self.assertFalse(result["axis_supported_candidate"])

    def test_axis3_no_no_candidate(self):
        """Axis 3 Q-A=no → no candidate."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "no", "no")
        )
        self.assertFalse(result["axis_supported_candidate"])


class TestAxis4Routing(unittest.TestCase):

    def test_axis4_yes_candidate(self):
        """Axis 4=yes → candidate."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "yes", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis4", result["supporting_axes"])

    def test_axis4_unclear_contested(self):
        """Axis 4=unclear → contested Review Needed."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "unclear", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertTrue(result["contested"])

    def test_axis4_no_no_candidate(self):
        """Axis 4=no → no Axis 4 issue."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "no", "no")
        )
        self.assertFalse(result["axis_supported_candidate"])


class TestAxis1ModifierOnly(unittest.TestCase):
    """Guard 3 core: Axis 1 cannot standalone create a finding."""

    def test_axis1_yes_alone_no_candidate(self):
        """Axis 1=yes alone → NO candidate (modifier-only enforcement)."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "no", "yes")
        )
        self.assertFalse(result["axis_supported_candidate"],
                         "Axis 1 alone must NOT create a candidate")
        self.assertNotIn("axis1", result["supporting_axes"])
        self.assertNotIn("axis1_modifier", result["supporting_axes"])

    def test_axis1_yes_with_axis2_adds_modifier(self):
        """Axis 1=yes + Axis 2 fires → candidate with axis1_modifier tag."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "yes")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis2", result["supporting_axes"])
        self.assertIn("axis1_modifier", result["supporting_axes"])

    def test_axis1_yes_with_axis3_adds_modifier(self):
        """Axis 1=yes + Axis 3 fires → candidate with axis1_modifier."""
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "yes", "yes", "no", "yes")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis3", result["supporting_axes"])
        self.assertIn("axis1_modifier", result["supporting_axes"])

    def test_axis1_no_with_axis2_no_modifier_tag(self):
        """Axis 2 fires but Axis 1=no → no axis1_modifier in supporting_axes."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertNotIn("axis1_modifier", result["supporting_axes"])


class TestGuard3ProseCannotCreateFindings(unittest.TestCase):
    """Verify routing is identical whether reason/citations are empty or 'POISON'."""

    def _route_with_poison(self, axis2_qa, axis2_qb, axis3_qa, axis3_qb, axis4, axis1):
        return compute_axis_supported_candidate(
            _all_axes(axis2_qa, axis2_qb, axis3_qa, axis3_qb, axis4, axis1,
                      poison_prose=True)
        )

    def _route_without_prose(self, axis2_qa, axis2_qb, axis3_qa, axis3_qb, axis4, axis1):
        return compute_axis_supported_candidate(
            _all_axes(axis2_qa, axis2_qb, axis3_qa, axis3_qb, axis4, axis1,
                      poison_prose=False)
        )

    def test_poison_prose_does_not_change_no_candidate(self):
        """Poisoned reason/citations must not turn a non-finding into a finding."""
        with_poison    = self._route_with_poison("no", "n.a.", "no", "n.a.", "no", "no")
        without_poison = self._route_without_prose("no", "n.a.", "no", "n.a.", "no", "no")
        self.assertFalse(with_poison["axis_supported_candidate"])
        self.assertEqual(with_poison["axis_supported_candidate"],
                         without_poison["axis_supported_candidate"])

    def test_poison_prose_does_not_change_candidate(self):
        """Poisoned reason/citations must not change a real finding outcome."""
        with_poison    = self._route_with_poison("yes", "no", "no", "n.a.", "no", "no")
        without_poison = self._route_without_prose("yes", "no", "no", "n.a.", "no", "no")
        self.assertTrue(with_poison["axis_supported_candidate"])
        self.assertEqual(with_poison["axis_supported_candidate"],
                         without_poison["axis_supported_candidate"])
        self.assertEqual(with_poison["proposed_bucket"],
                         without_poison["proposed_bucket"])


class TestPrototypeLPScenarios(unittest.TestCase):
    """Scenario tests for the six prototype LPs (expected routing patterns)."""

    def test_lp03_axis2_obligation_without_remedy(self):
        """LP-03: tenant obligated at commencement even if Landlord's Work unfinished.
        Axis 2: Q-A=yes (tenant must commence) Q-B=no (no practical remedy).
        Expected: axis_supported_candidate=True, Risk, axis2 in supporting.
        """
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertEqual(result["proposed_bucket"], "Risk")
        self.assertIn("axis2", result["supporting_axes"])

    def test_lp19_contested_axis2_yes_axis3_yes(self):
        """LP-19: Axis 2 sees remedy exists (Q-B=yes), Axis 3 sees it is conditioned.
        Both axes fire → candidate. Axis 3 adds contested flag.
        """
        # Axis 2: Q-A=yes Q-B=yes → no Axis 2 issue
        # Axis 3: Q-A=yes Q-B=yes → Axis 3 candidate
        result = compute_axis_supported_candidate(
            _all_axes("yes", "yes", "yes", "yes", "no", "no")
        )
        # Axis 2 yes+yes doesn't trigger, Axis 3 yes+yes does
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis3", result["supporting_axes"])
        self.assertNotIn("axis2", result["supporting_axes"])

    def test_lp26_axis3_only_no_axis1_needed(self):
        """LP-26: Axis 3 alone surfaces conditional protection (§18.1 double-gated).
        Axis 1 must be 'no' or 'n.a.' — the generic Article-17 comparison is NOT valid.
        """
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "yes", "yes", "no", "no")  # axis1=no
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis3", result["supporting_axes"])
        self.assertNotIn("axis1_modifier", result["supporting_axes"])

    def test_lp27_axis1_plus_axis2_genuine_same_risk(self):
        """LP-27: Axis 2 fires (60-day wait, no interim remedy).
        Axis 1 fires (§5.1 vs Article 17 same-risk comparison is genuine).
        Expected: both axes contribute; axis1_modifier present.
        """
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "yes")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis2", result["supporting_axes"])
        self.assertIn("axis1_modifier", result["supporting_axes"])

    def test_lp11_negative_control_axis2_no_axis1_not_fired(self):
        """LP-11/LP-22 negative control: generic Article-17 comparison must NOT fire.
        Axis 1 = no (generic comparison disqualified). Axis 2 still supports.
        axis1_modifier must NOT be in supporting_axes.
        """
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no")  # axis1=no
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertIn("axis2", result["supporting_axes"])
        self.assertNotIn("axis1_modifier", result["supporting_axes"])

    def test_lp15_wishlist_control_no_candidate(self):
        """LP-15/LP-16 wish-list control: must NOT generate a candidate.
        All axes return 'no' or 'n.a.' → axis_supported_candidate=False.
        """
        result = compute_axis_supported_candidate(
            _all_axes("no", "n.a.", "no", "n.a.", "no", "no")
        )
        self.assertFalse(result["axis_supported_candidate"],
                         "Wish-list LP must not survive closed-form questions")
        self.assertEqual(result["supporting_axes"], [])
        self.assertEqual(result["proposed_bucket"], "Addressed")


class TestParseClosedFormResponse(unittest.TestCase):

    def test_plain_json(self):
        raw = """{
  "lp_id": "LP-03",
  "lp_name": "Lease Term & Renewal",
  "axis_results": [
    {"axis_id": "axis2", "question_id": "q_a",          "answer": "yes", "citations": [], "reason": "r"},
    {"axis_id": "axis2", "question_id": "q_a_confirmed", "answer": "yes", "citations": [], "reason": "r"},
    {"axis_id": "axis2", "question_id": "q_b",          "answer": "no",  "citations": [], "reason": "r"},
    {"axis_id": "axis3", "question_id": "q_a",          "answer": "no",  "citations": [], "reason": "r"},
    {"axis_id": "axis3", "question_id": "q_b",          "answer": "n.a.","citations": [], "reason": "r"},
    {"axis_id": "axis4", "question_id": "standalone",   "answer": "no",  "citations": [], "reason": "r"},
    {"axis_id": "axis1", "question_id": "standalone",   "answer": "no",  "citations": [], "reason": "r"}
  ],
  "materiality": "high",
  "materiality_reason": "tenant must commence obligations"
}"""
        result = _parse_closed_form_response(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["lp_id"], "LP-03")
        self.assertEqual(len(result["axis_results"]), 7)

    def test_fenced_json(self):
        raw = "```json\n{\"lp_id\": \"LP-27\", \"lp_name\": \"X\", \"axis_results\": [], \"materiality\": \"high\", \"materiality_reason\": \"\"}\n```"
        result = _parse_closed_form_response(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result["lp_id"], "LP-27")

    def test_invalid_json_returns_none(self):
        result = _parse_closed_form_response("not valid json at all")
        self.assertIsNone(result)

    def test_empty_string_returns_none(self):
        result = _parse_closed_form_response("")
        self.assertIsNone(result)




class TestAxis2FourPartConfirmation(unittest.TestCase):
    """Step 391: Tests for the q_a_confirmed tightening.

    Axis-2 may create a candidate ONLY when q_a_confirmed is 'yes' or 'unclear'.
    q_a=yes but q_a_confirmed=no blocks the generic-category over-fire (LP-15 fix).
    """

    def test_axis2_yes_confirmed_yes_is_candidate(self):
        """q_a=yes, q_a_confirmed=yes, q_b=no -> Risk candidate (LP-03 pattern)."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no",
                      axis2_qa_confirmed="yes")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertEqual(result["proposed_bucket"], "Risk")
        self.assertIn("axis2", result["supporting_axes"])

    def test_axis2_yes_confirmed_no_blocks_candidate(self):
        """q_a=yes but q_a_confirmed=no -> generic-category over-fire blocked (LP-15 fix)."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no",
                      axis2_qa_confirmed="no")
        )
        self.assertFalse(result["axis_supported_candidate"],
                         "q_a_confirmed=no must block even when q_a=yes")
        self.assertEqual(result["supporting_axes"], [])

    def test_axis2_yes_confirmed_unclear_is_review_needed(self):
        """q_a=yes, q_a_confirmed=unclear -> plausible but unconfirmed -> Review Needed."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no",
                      axis2_qa_confirmed="unclear")
        )
        self.assertTrue(result["axis_supported_candidate"])
        self.assertTrue(result["contested"])
        self.assertEqual(result["proposed_bucket"], "Review Needed")
        self.assertIn("axis2", result["supporting_axes"])

    def test_lp15_generic_category_drops_with_tightened_axis2(self):
        """LP-15 fix: axis2_qa=yes but q_a_confirmed=no drops the finding.

        In Step 389, LP-15 (Insurance Requirements) was flagged 5/5 because
        Eval-A returned axis2_qa=yes citing a hypothetical category. With the
        tightened q_a_confirmed gate, that returns q_a_confirmed=no -> no candidate.
        """
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no",
                      axis2_qa_confirmed="no",
                      poison_prose=True)
        )
        self.assertFalse(result["axis_supported_candidate"],
                         "LP-15-style generic-category must not survive tightened Axis 2")

    def test_axis2_no_makes_confirmed_irrelevant(self):
        """When q_a=no, q_a_confirmed=n.a. -- routing unaffected regardless of confirmed."""
        for confirmed in ("yes", "no", "unclear", "n.a."):
            result = compute_axis_supported_candidate(
                _all_axes("no", "n.a.", "no", "n.a.", "no", "no",
                          axis2_qa_confirmed=confirmed)
            )
            self.assertFalse(result["axis_supported_candidate"],
                             f"q_a=no with confirmed={confirmed} must not be candidate")

    def test_poison_prose_does_not_override_confirmed_no(self):
        """Guard 3 extended: poisoned reason cannot turn confirmed=no into a finding."""
        result = compute_axis_supported_candidate(
            _all_axes("yes", "no", "no", "n.a.", "no", "no",
                      axis2_qa_confirmed="no",
                      poison_prose=True)
        )
        self.assertFalse(result["axis_supported_candidate"],
                         "Poisoned prose with confirmed=no must not create a candidate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
