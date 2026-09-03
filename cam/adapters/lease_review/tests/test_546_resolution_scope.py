"""Step 546: the headline must consult the record, and the bottom of the range must survive.

Step 545 measured `_build_schema_exposure`'s catch-all emitting an LP's STATIC
schema `exposure_statement` for every `review_needed` item -- prose written for
the absent case, keyed to the LP id, never reading the assessment. Atlas LP-26
and ex6-4 LP-25 rendered "absent or undefined" with `elements_missing: []`.

The risk in fixing it is the opposite error: softening the LPs where absence is
the TRUE reading. ex6-4 LP-20 (0 of 7 elements present) and LP-02 (0 of 4) are
correct as they stand, and `test_absent_lp_keeps_schema_statement` exists to
fail if a later change starts narrating them as merely unresolved.

Deterministic, no provider calls, no network.
"""
import unittest

from cam.adapters.lease_review.lease_display import (
    _resolve_display,
    summarize_resolution,
    resolution_scope_phrase,
)
from cam.adapters.lease_review.lease_exposure import _build_schema_exposure
from cam.adapters.lease_review.lease_docx_annotator import _format_coverage_callout_text
from cam.adapters.lease_review.lease_pdf_annotator import _format_coverage_annotation_text


def _ev(eid, label, verdict, reason=None):
    return {"element_id": eid, "element_label": label,
            "verdict": verdict, "reason": reason}


def _item(pid, name, state, evs, missing=None):
    return {
        "issue_area_id": pid,
        "issue_area_name": name,
        "coverage_state": state,
        "assessment_status": "assessed",
        "element_verdicts": evs,
        "elements_missing": list(missing or []),
        "elements_found": [],
        "materiality": "low",
    }


# 6 present, 1 unresolved, 0 missing -- the Atlas LP-26 / ex6-4 LP-25 shape.
MOSTLY_PRESENT = _item(
    "LP-26", "Quiet Enjoyment", "review_needed",
    [_ev(f"LP-26.e{i}", f"Element {i}", "explicitly_present") for i in range(6)]
    + [_ev("LP-26.ce", "Constructive eviction is addressed", "unclear", "no_consensus")],
)

# 0 present -- the ex6-4 LP-20 shape. Absence is the true reading here.
NOTHING_PRESENT = _item(
    "LP-20", "Exclusivity", "review_needed",
    [_ev(f"LP-20.e{i}", f"Element {i}", "missing") for i in range(5)]
    + [_ev("LP-20.rr", "Radius restriction", "unclear", "no_consensus"),
       _ev("LP-20.cu", "Competing use definition", "disputed",
           "distant_split_presence_missing")],
    missing=[f"Element {i}" for i in range(5)],
)


class TestSummarizeResolution(unittest.TestCase):

    def test_partitions_present_absent_unresolved(self):
        res = summarize_resolution(MOSTLY_PRESENT)
        self.assertEqual(res["total_elements"], 7)
        self.assertEqual(res["settled_present"], 6)
        self.assertEqual(res["settled_absent"], 0)
        self.assertEqual(res["unresolved_elements"], 1)
        self.assertEqual(res["unresolved_reasons"], {"no_consensus": 1})

    def test_disputed_counts_as_unresolved_not_absent(self):
        """`derive_lp_state` folds disputed in with missing; this does not.

        11 of the 32 review_needed LPs measured at Step 545 reach that state
        through the Phase-3 disputed-critical override with NO unclear element.
        Counting disputed as settled would report "0 of N unresolved" on them.
        """
        res = summarize_resolution(NOTHING_PRESENT)
        self.assertEqual(res["unresolved_elements"], 2)
        self.assertEqual(res["settled_absent"], 5)

    def test_no_element_verdicts_yields_no_scope(self):
        res = summarize_resolution(_item("LP-29", "Right of Entry", "review_needed", []))
        self.assertEqual(res["total_elements"], 0)
        self.assertEqual(resolution_scope_phrase(res), "")


class TestHeadline(unittest.TestCase):

    def test_headline_does_not_assert_absence_when_nothing_is_missing(self):
        out = _build_schema_exposure(MOSTLY_PRESENT, "tenant")
        self.assertEqual(out["exposure_reason_code"], "review_needed_scope")
        self.assertEqual(out["exposure_headline"], "1 of 7 elements unresolved")
        for word in ("absent", "undefined"):
            self.assertNotIn(word, out["exposure_headline"].lower())
        self.assertIn("6 of 7 expected elements are confirmed present",
                      out["exposure_statement"])

    def test_absent_lp_keeps_schema_statement(self):
        """The bottom of the range is CORRECT and must not be softened.

        Zero elements confirmed present means the provision really is absent.
        This LP must keep the schema prose and must NOT gain a scope headline.
        """
        out = _build_schema_exposure(NOTHING_PRESENT, "tenant")
        self.assertEqual(out["exposure_reason_code"], "schema_default")
        self.assertNotIn("unresolved", out["exposure_headline"].lower())


class TestAnnotatorMarkerAndScope(unittest.TestCase):

    def test_marker_is_review_when_record_holds_no_gap(self):
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(MOSTLY_PRESENT, None, "tenant")
            self.assertTrue(text.startswith("[REVIEW]"), fmt.__name__ + ": " + text[:60])

    def test_marker_stays_gap_when_something_is_missing(self):
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(NOTHING_PRESENT, None, "tenant")
            self.assertTrue(text.startswith("[GAP]"), fmt.__name__ + ": " + text[:60])

    def test_scope_reaches_both_exports(self):
        """element_verdicts appeared ZERO times in either annotator before this."""
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(MOSTLY_PRESENT, None, "tenant")
            self.assertIn("Resolved: 6 of 7 expected elements confirmed present", text)
            self.assertIn("Unresolved (1): Constructive eviction is addressed", text)

    def test_lp_level_roll_up_is_not_surfaced(self):
        """Step_305_Architecture.md:39 -- state is "not from a direct LP-state vote"."""
        item = dict(MOSTLY_PRESENT,
                    per_evaluator_lp_verdicts={"A": "explicitly_present",
                                               "B": "explicitly_present",
                                               "C": "explicitly_present"})
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(item, None, "tenant")
            self.assertNotIn("explicitly_present", text)


class TestDisplayLabel(unittest.TestCase):

    def test_label_carries_scope(self):
        d = _resolve_display(MOSTLY_PRESENT, "tenant")
        self.assertEqual(d["bucket"], "worth_reviewing")
        self.assertEqual(d["label"], "REVIEW NEEDED — 1 OF 7 ELEMENTS UNRESOLVED")

    def test_zero_elements_guard_still_outranks_the_scope_label(self):
        """Step 538's guard runs first; LP-20 must keep NO ELEMENTS FOUND."""
        d = _resolve_display(NOTHING_PRESENT, "tenant")
        self.assertEqual(d["bucket"], "needs_attention")
        self.assertEqual(d["label"], "NO ELEMENTS FOUND")

    def test_degraded_item_keeps_the_bare_label(self):
        d = _resolve_display(_item("LP-29", "Right of Entry", "review_needed", []), "tenant")
        self.assertEqual(d["label"], "REVIEW NEEDED")


if __name__ == "__main__":
    unittest.main()
