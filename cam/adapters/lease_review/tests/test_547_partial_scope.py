"""Step 547: `partial` with an empty adverse-missing list gets the Step-546 treatment.

Step 546 fixed `review_needed`. The identical catch-all defect survived on
`partial`, because `_build_schema_exposure`'s partial branch is
`if state == "partial" and missing:` -- so a partial whose perspective-adverse
missing list is empty fell past it to the canned absence prose. Measured on 19
LPs across six runs, e.g. ex6-4 LP-05 "Use restrictions absent or undefined"
beside 3 of 4 elements confirmed present.

The polarity trap is sharper here than on review_needed: `partial` means some
element is not present, so favourable absences are more common. Step 547 measured
17 of 99 `partial` LPs where the raw non-present count differs from the
perspective-adverse one -- three of them inside the 19 this branch serves. The
prose must use the adverse list; `test_favorable_absences_are_not_narrated`
fails if a later change reaches for the raw count.

Deterministic, no provider calls, no network.
"""
import unittest

from cam.adapters.lease_review.lease_exposure import _build_schema_exposure
from cam.adapters.lease_review.lease_docx_annotator import _format_coverage_callout_text
from cam.adapters.lease_review.lease_pdf_annotator import _format_coverage_annotation_text


def _ev(eid, label, verdict, reason=None):
    return {"element_id": eid, "element_label": label,
            "verdict": verdict, "reason": reason}


def _partial(pid, name, evs, missing=None):
    return {
        "issue_area_id": pid,
        "issue_area_name": name,
        "coverage_state": "partial",
        "partial_class": "partial_typical",
        "assessment_status": "assessed",
        "element_verdicts": evs,
        "elements_missing": list(missing or []),
        "elements_found": [],
        "materiality": "low",
    }


# 3 present, 1 disputed, no adverse missing -- the ex6-4 LP-05 shape.
# `disputed`, not `unclear`: any unclear element would have made the LP
# review_needed via derive_lp_state's first branch, so every one of the 19
# carries disputed elements only (28 of 28 measured).
PARTIAL_NO_GAP = _partial(
    "LP-05", "Permitted Use",
    [_ev(f"LP-05.e{i}", f"Element {i}", "explicitly_present") for i in range(3)]
    + [_ev("LP-05.ct", "Co-tenancy or anchor tenant dependency is addressed",
           "disputed", "distant_split_presence_missing")],
)

# Same, but two elements carry a `missing` verdict that Step 374Z strips as
# favourable to this perspective -- `elements_missing` is correctly empty.
PARTIAL_FAVORABLE_ABSENCE = _partial(
    "LP-09", "Subletting & Assignment",
    [_ev(f"LP-09.e{i}", f"Element {i}", "explicitly_present") for i in range(8)]
    + [_ev("LP-09.f1", "Landlord recapture right", "missing"),
       _ev("LP-09.f2", "Profit sharing on sublet", "missing"),
       _ev("LP-09.coc", "Change of control is addressed",
           "disputed", "distant_split_presence_missing"),
       _ev("LP-09.lia", "Original tenant remains liable after assignment",
           "disputed", "distant_split_presence_missing")],
)

# A partial with a real adverse gap: must keep the pre-existing partial branch.
PARTIAL_WITH_GAP = _partial(
    "LP-06", "Maintenance & Repairs",
    [_ev(f"LP-06.e{i}", f"Element {i}", "explicitly_present") for i in range(3)]
    + [_ev("LP-06.hv", "HVAC replacement responsibility", "missing")],
    missing=["HVAC replacement responsibility"],
)

# Nothing confirmed present: absence is the true reading, branch must decline.
PARTIAL_NOTHING_PRESENT = _partial(
    "LP-13", "Indemnification",
    [_ev("LP-13.a", "Element A", "missing"),
     _ev("LP-13.b", "Element B", "disputed", "distant_split_presence_missing")],
    missing=["Element A"],
)


class TestPartialHeadline(unittest.TestCase):

    def test_headline_does_not_assert_absence_when_nothing_is_missing(self):
        out = _build_schema_exposure(PARTIAL_NO_GAP, "tenant")
        self.assertEqual(out["exposure_reason_code"], "partial_scope")
        self.assertEqual(out["exposure_headline"], "1 of 4 elements unresolved")
        for word in ("absent", "undefined"):
            self.assertNotIn(word, out["exposure_headline"].lower())
        self.assertIn("3 of 4 expected elements are confirmed present",
                      out["exposure_statement"])

    def test_favorable_absences_are_not_narrated(self):
        """Step 374Z: the adverse list is empty, so the prose must claim no gap.

        The raw non-present count here is 2. Reaching for it would render
        "8 of 12 expected elements are confirmed present and 2 absent" about two
        absences that favour this perspective.
        """
        out = _build_schema_exposure(PARTIAL_FAVORABLE_ABSENCE, "tenant")
        self.assertEqual(out["exposure_reason_code"], "partial_scope")
        self.assertIn("8 of 12 expected elements are confirmed present.",
                      out["exposure_statement"])
        self.assertNotIn("absent", out["exposure_statement"].lower())

    def test_partial_with_a_real_gap_is_untouched(self):
        out = _build_schema_exposure(PARTIAL_WITH_GAP, "tenant")
        self.assertEqual(out["exposure_reason_code"], "schema_default")
        self.assertNotIn("unresolved", out["exposure_headline"].lower())

    def test_branch_declines_when_nothing_is_present(self):
        out = _build_schema_exposure(PARTIAL_NOTHING_PRESENT, "tenant")
        self.assertEqual(out["exposure_reason_code"], "schema_default")


class TestPartialMarker(unittest.TestCase):

    def test_marker_is_review_when_record_holds_no_gap(self):
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(PARTIAL_NO_GAP, None, "tenant")
            self.assertTrue(text.startswith("[REVIEW]"), fmt.__name__ + ": " + text[:60])

    def test_marker_stays_gap_when_something_is_missing(self):
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(PARTIAL_WITH_GAP, None, "tenant")
            self.assertTrue(text.startswith("[GAP]"), fmt.__name__ + ": " + text[:60])

    def test_scope_reaches_both_exports(self):
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            text = fmt(PARTIAL_NO_GAP, None, "tenant")
            self.assertIn("Resolved: 3 of 4 expected elements confirmed present", text)
            self.assertIn("Unresolved (1): Co-tenancy or anchor tenant dependency", text)


class TestScopeIsNotWidened(unittest.TestCase):

    def test_broken_xref_still_falls_through(self):
        """7 LPs carry the same defect on broken_xref. Reported at Step 547, NOT fixed.

        All seven carry zero element verdicts, so the scope branch would decline
        even if `broken_xref` were added to it. Their defect is a different one --
        a canned assertion with no record at all, rather than one contradicting
        the record -- and it needs its own step.
        """
        item = dict(PARTIAL_NO_GAP, coverage_state="broken_xref",
                    partial_class=None, element_verdicts=[])
        out = _build_schema_exposure(item, "tenant")
        self.assertEqual(out["exposure_reason_code"], "schema_default")

    def test_covered_unfavorable_keeps_its_marker(self):
        item = dict(PARTIAL_NO_GAP, coverage_state="covered_unfavorable",
                    partial_class=None)
        for fmt in (_format_coverage_callout_text, _format_coverage_annotation_text):
            self.assertTrue(fmt(item, None, "tenant").startswith("[GAP]"))


if __name__ == "__main__":
    unittest.main()
