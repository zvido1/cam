"""Step 498 Part B: exercise the code that EMITS a provenance stub.

Step 497 verified its rule by applying it to stored Step-487 results. That
proves the rule, not the emitter. A stub is only produced when an evaluator
totally fails, which needs a provider outage -- so every run since the fix has
left the emitting path unexercised, and saying otherwise would be the
written-vs-wired claim CLAUDE.md Rule 4 exists to stop.

These tests drive `_extract_verdicts_for_element` directly with a failed
evaluator result, which is exactly the shape both failure-path returns in
`_call_evaluator_305` produce (`lease_coverage_305.py:696` and `:785`): they set
`model`/`label` from `evaluator_cfg` -- the REQUESTED model -- and `completed:
False`. That combination is what used to make a stub claim Anthropic served it.

Deterministic, no provider calls, no network.
"""
import unittest

from cam.adapters.lease_review.lease_coverage_305 import (
    _extract_verdicts_for_element,
    EVALUATOR_LINEUP_305,
)

ELEMENT = {"element_id": "LP-99.test_element", "criticality": "important"}


def _failed_result(role):
    """Byte-shape of a totally-failed evaluator, per the two failure-path returns."""
    cfg = EVALUATOR_LINEUP_305[role]
    return {
        "role": role,
        "model": cfg["model"],          # the REQUESTED model -- the whole trap
        "provider": cfg["provider"],
        "label": cfg["label"],
        "completed": False,
        "elapsed_sec": 0.0,
        "element_verdicts": None,
        "error": "simulated total failure",
    }


def _served_result(role, model=None, label=None):
    m = model or EVALUATOR_LINEUP_305[role]["model"]
    return {
        "role": role,
        "model": m,
        "provider": EVALUATOR_LINEUP_305[role]["provider"],
        "label": label or EVALUATOR_LINEUP_305[role]["label"],
        "completed": True,
        "elapsed_sec": 1.0,
        "element_verdicts": [{
            "element_id": ELEMENT["element_id"],
            "verdict": "explicitly_present",
            "citation": {"section_ref": "Section 1.1", "quote": "q",
                         "citation_quality": "section_and_quote"},
            "reasoning": "served",
            "confidence": "high",
        }],
    }


class TestStubProvenanceEmitted(unittest.TestCase):
    """The emitting path, driven directly."""

    def _stub_for(self, role):
        out = _extract_verdicts_for_element(
            {role: _failed_result(role)}, ELEMENT["element_id"], ELEMENT)
        self.assertEqual(len(out), 1)
        return out[0]

    def test_stub_names_no_model(self):
        """actual_model must NOT name the requested model. Step 487 read 6 as service."""
        for role in ("A", "B", "C"):
            with self.subTest(role=role):
                v = self._stub_for(role)
                self.assertIsNone(v["actual_model"])
                self.assertIsNone(v["actual_label"])
                self.assertNotEqual(v.get("label"), EVALUATOR_LINEUP_305[role]["label"])

    def test_stub_does_not_deny_substitution(self):
        """is_fallback must not be False -- that is an affirmative denial."""
        for role in ("A", "B", "C"):
            with self.subTest(role=role):
                self.assertIsNone(self._stub_for(role)["is_fallback"])

    def test_stub_is_structurally_queryable(self):
        """served=False, so a census need not parse prose."""
        for role in ("A", "B", "C"):
            with self.subTest(role=role):
                v = self._stub_for(role)
                self.assertIs(v["served"], False)
                self.assertEqual(v["reasoning"], "Evaluator %s did not complete" % role)

    def test_stub_keeps_the_request_under_a_true_name(self):
        for role in ("A", "B", "C"):
            with self.subTest(role=role):
                self.assertEqual(self._stub_for(role)["requested_model"],
                                 EVALUATOR_LINEUP_305[role]["model"])

    def test_a_census_over_actual_model_counts_zero(self):
        """The Step-487 defect, reproduced against the emitter: 6 -> 0."""
        results = {r: _failed_result(r) for r in ("A", "B", "C")}
        verdicts = _extract_verdicts_for_element(results, ELEMENT["element_id"], ELEMENT)
        served = [v["actual_model"] for v in verdicts if v["actual_model"]]
        self.assertEqual(served, [], "a stub must not appear as provider service")


class TestServedRecordsUnaffected(unittest.TestCase):
    """The fix must not touch records a model actually produced."""

    def test_primary_service_still_named(self):
        v = _extract_verdicts_for_element(
            {"A": _served_result("A")}, ELEMENT["element_id"], ELEMENT)[0]
        self.assertEqual(v["actual_model"], EVALUATOR_LINEUP_305["A"]["model"])
        self.assertFalse(v["is_fallback"])
        self.assertNotIn("served", v)          # only stubs carry it

    def test_real_fallback_still_flagged(self):
        """Step 496's benign case: a substitute that DID serve stays labelled."""
        v = _extract_verdicts_for_element(
            {"A": _served_result("A", model="claude-haiku-4-5-20251001", label="Claude Haiku 4.5")},
            ELEMENT["element_id"], ELEMENT)[0]
        self.assertEqual(v["actual_model"], "claude-haiku-4-5-20251001")
        self.assertTrue(v["is_fallback"])

    def test_missing_element_is_not_a_stub(self):
        """`match is None` means the evaluator SERVED and omitted one element."""
        r = _served_result("A")
        r["element_verdicts"] = [{"element_id": "LP-99.other", "verdict": "missing"}]
        v = _extract_verdicts_for_element({"A": r}, ELEMENT["element_id"], ELEMENT)[0]
        self.assertEqual(v["actual_model"], EVALUATOR_LINEUP_305["A"]["model"])
        self.assertIn("did not include verdict", v["reasoning"])


if __name__ == "__main__":
    unittest.main()
