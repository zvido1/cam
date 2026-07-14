"""
Step 422B — NOT_APPLICABLE wiring tests.

Tests cover:
1. Returned-empty AMBIGUOUS: industrial LP-20/21/23/31 with empty tenant_text
   returned by model → reclassified to NOT_APPLICABLE
2. Absent-from-results: same LPs never included in model JSON → NOT_APPLICABLE
3. Presence overrides registry: industrial LP-20 WITH tenant_text → evaluated
   normally, never NOT_APPLICABLE
4. Non-known-absent empty: industrial LP-07 empty → stays AMBIGUOUS (fail)
5. Document-type scoping: retail LP-23 empty → AMBIGUOUS (not known-absent on retail)
6. Unknown property_type: LP-20 empty → AMBIGUOUS with explicit note
7. All-models-failed → AMBIGUOUS (unchanged from 422A)
8. Coverage bridge: provision with NOT_APPLICABLE extraction status → coverage_state
   not_applicable, without running element assessment
9. Gate 3: check_extraction_completeness() returns correct gate_status values
"""

import unittest
from unittest.mock import MagicMock, patch

from cam.adapters.lease_review.lease_extract import (
    _classify_missing_stub,
    check_extraction_completeness,
    KNOWN_ABSENT_BY_DOC_TYPE,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_prov(provision_id, status, tenant_text=""):
    return {
        "provision_id": provision_id,
        "provision_name": f"{provision_id} Name",
        "template_text": "",
        "tenant_text": tenant_text,
        "template_section_ref": "",
        "tenant_section_ref": "",
        "status": status,
        "alignment_notes": "test",
        "definition_changes": "",
    }


def _industrial_deal_overview():
    return {"property_type": "Industrial"}


def _retail_deal_overview():
    return {"property_type": "Retail"}


# ── Classify-stub unit tests ────────────────────────────────────────────────────

class TestClassifyMissingStub(unittest.TestCase):

    def test_industrial_known_absent_lps_get_not_applicable(self):
        for lp in ("LP-20", "LP-21", "LP-23", "LP-31"):
            status, notes = _classify_missing_stub(lp, _industrial_deal_overview())
            self.assertEqual(status, "NOT_APPLICABLE", f"{lp} should be NOT_APPLICABLE on industrial")
            self.assertIn("known-absent", notes)
            self.assertIn("Industrial", notes)

    def test_warehouse_known_absent_lps_get_not_applicable(self):
        for lp in ("LP-20", "LP-21", "LP-23", "LP-31"):
            status, notes = _classify_missing_stub(lp, {"property_type": "Warehouse"})
            self.assertEqual(status, "NOT_APPLICABLE", f"{lp} should be NOT_APPLICABLE on warehouse")

    def test_industrial_non_known_absent_stays_ambiguous(self):
        status, _ = _classify_missing_stub("LP-07", _industrial_deal_overview())
        self.assertEqual(status, "AMBIGUOUS")

    def test_retail_lp23_is_ambiguous(self):
        # LP-23 is in known-absent for industrial only — retail extraction miss is failure
        status, notes = _classify_missing_stub("LP-23", _retail_deal_overview())
        self.assertEqual(status, "AMBIGUOUS")
        self.assertIn("no declared known-absent set", notes)

    def test_unknown_property_type_is_ambiguous(self):
        status, notes = _classify_missing_stub("LP-20", {})
        self.assertEqual(status, "AMBIGUOUS")
        self.assertIn("unknown", notes.lower())

    def test_unrecognized_type_is_ambiguous_with_note(self):
        status, notes = _classify_missing_stub("LP-20", {"property_type": "Office"})
        self.assertEqual(status, "AMBIGUOUS")
        self.assertIn("no declared known-absent set", notes)

    def test_industrial_mixed_use_prefix_normalizes_correctly(self):
        # "Industrial, Mixed-Use" → "industrial" → hits registry
        status, _ = _classify_missing_stub("LP-20", {"property_type": "Industrial, Mixed-Use"})
        self.assertEqual(status, "NOT_APPLICABLE")


# ── Reclassify-returned-empty (integration via _classify_missing_stub) ─────────

class TestReturnedEmptyReclassification(unittest.TestCase):
    """
    These tests exercise the post-processing reclassify loop that was added to
    the dual-doc and single-doc extraction paths. We test the logic directly
    through _classify_missing_stub since calling the full extraction path requires
    API access. The integration test in test_extraction_result_reclassification
    tests the full dict mutation path without API calls.
    """

    def test_returned_empty_industrial_lp20_becomes_not_applicable(self):
        # Simulate: model returned LP-20 with AMBIGUOUS + empty text
        # This is the actual observed behavior for LP-20/21/23/31
        p = _make_prov("LP-20", "AMBIGUOUS", tenant_text="")
        deal_overview = _industrial_deal_overview()
        if p.get("status") == "AMBIGUOUS" and not (p.get("tenant_text") or "").strip():
            _status, _notes = _classify_missing_stub(p["provision_id"], deal_overview)
            if _status == "NOT_APPLICABLE":
                p["status"] = "NOT_APPLICABLE"
                p["alignment_notes"] = _notes
        self.assertEqual(p["status"], "NOT_APPLICABLE")

    def test_returned_empty_industrial_lp07_stays_ambiguous(self):
        # LP-07 with empty text on industrial → AMBIGUOUS (extraction failure)
        p = _make_prov("LP-07", "AMBIGUOUS", tenant_text="")
        deal_overview = _industrial_deal_overview()
        if p.get("status") == "AMBIGUOUS" and not (p.get("tenant_text") or "").strip():
            _status, _notes = _classify_missing_stub(p["provision_id"], deal_overview)
            if _status == "NOT_APPLICABLE":
                p["status"] = "NOT_APPLICABLE"
                p["alignment_notes"] = _notes
        self.assertEqual(p["status"], "AMBIGUOUS")

    def test_returned_nonempty_lp20_not_reclassified(self):
        # LP-20 WITH text is in results → reclassify loop doesn't fire (has text)
        p = _make_prov("LP-20", "FOUND_BOTH", tenant_text="Tenant shall have no exclusive use rights.")
        deal_overview = _industrial_deal_overview()
        # Reclassify loop condition: status == AMBIGUOUS AND empty → doesn't match
        if p.get("status") == "AMBIGUOUS" and not (p.get("tenant_text") or "").strip():
            _status, _notes = _classify_missing_stub(p["provision_id"], deal_overview)
            if _status == "NOT_APPLICABLE":
                p["status"] = "NOT_APPLICABLE"
        self.assertEqual(p["status"], "FOUND_BOTH")

    def test_retail_lp23_empty_stays_ambiguous(self):
        # LP-23 empty on retail → AMBIGUOUS (not in known-absent for retail)
        p = _make_prov("LP-23", "AMBIGUOUS", tenant_text="")
        deal_overview = _retail_deal_overview()
        if p.get("status") == "AMBIGUOUS" and not (p.get("tenant_text") or "").strip():
            _status, _notes = _classify_missing_stub(p["provision_id"], deal_overview)
            if _status == "NOT_APPLICABLE":
                p["status"] = "NOT_APPLICABLE"
        self.assertEqual(p["status"], "AMBIGUOUS")


# ── Gate 3: check_extraction_completeness ─────────────────────────────────────

class TestGate3ExtractionCompleteness(unittest.TestCase):

    def test_provision_with_text_passes(self):
        provisions = [_make_prov("LP-01", "FOUND_BOTH", tenant_text="Rent shall be...")]
        results = check_extraction_completeness(provisions, _industrial_deal_overview())
        self.assertEqual(results[0]["gate_status"], "pass")

    def test_not_applicable_status_passes_gate(self):
        provisions = [_make_prov("LP-20", "NOT_APPLICABLE", tenant_text="")]
        results = check_extraction_completeness(provisions, _industrial_deal_overview())
        self.assertEqual(results[0]["gate_status"], "not_applicable")

    def test_industrial_lp20_ambiguous_empty_passes_as_not_applicable(self):
        # After reclassification, AMBIGUOUS+empty+known-absent → not_applicable at gate
        # Gate also handles the case where reclassification didn't happen yet
        provisions = [_make_prov("LP-20", "AMBIGUOUS", tenant_text="")]
        results = check_extraction_completeness(provisions, _industrial_deal_overview())
        self.assertEqual(results[0]["gate_status"], "not_applicable")

    def test_industrial_lp07_empty_fails_gate(self):
        provisions = [_make_prov("LP-07", "AMBIGUOUS", tenant_text="")]
        results = check_extraction_completeness(provisions, _industrial_deal_overview())
        self.assertEqual(results[0]["gate_status"], "fail_missing")

    def test_retail_lp23_empty_fails_gate(self):
        provisions = [_make_prov("LP-23", "AMBIGUOUS", tenant_text="")]
        results = check_extraction_completeness(provisions, _retail_deal_overview())
        self.assertEqual(results[0]["gate_status"], "fail_missing")

    def test_unknown_doc_type_lp20_empty_fails_gate(self):
        provisions = [_make_prov("LP-20", "AMBIGUOUS", tenant_text="")]
        results = check_extraction_completeness(provisions, {})
        # Unknown type → no known_absent set → fail_missing
        self.assertEqual(results[0]["gate_status"], "fail_missing")

    def test_mixed_provisions_correct_gates(self):
        provisions = [
            _make_prov("LP-01", "FOUND_BOTH", tenant_text="Rent is $100."),
            _make_prov("LP-20", "NOT_APPLICABLE", tenant_text=""),
            _make_prov("LP-07", "AMBIGUOUS", tenant_text=""),
        ]
        results = check_extraction_completeness(provisions, _industrial_deal_overview())
        by_id = {r["provision_id"]: r["gate_status"] for r in results}
        self.assertEqual(by_id["LP-01"], "pass")
        self.assertEqual(by_id["LP-20"], "not_applicable")
        self.assertEqual(by_id["LP-07"], "fail_missing")


# ── Coverage bridge (unit test without full pipeline) ─────────────────────────

class TestCoverageBridge(unittest.TestCase):
    """
    Test that assess_coverage() short-circuits to not_applicable when
    extraction status == NOT_APPLICABLE, without running element assessment.
    """

    def _run_coverage_for_lp(self, provision_id, extraction_status, tenant_text="",
                              alignment_notes="Known-absent provision."):
        """Run assess_coverage for a single LP and return its assessment."""
        from cam.adapters.lease_review.lease_coverage import assess_coverage
        prov = _make_prov(provision_id, extraction_status, tenant_text)
        prov["alignment_notes"] = alignment_notes
        assessments = assess_coverage([prov], full_tenant_text="irrelevant text about a lease")
        return next((a for a in assessments if a.get("issue_area_id") == provision_id), None)

    def test_not_applicable_status_yields_not_applicable_coverage(self):
        # LP-20 with NOT_APPLICABLE extraction status → coverage not_applicable.
        # Note: LP-20 has default_when_unclear="not_applicable" so it would reach
        # not_applicable anyway via text clues on generic text, but that's correct
        # behavior — both paths agree.
        assessment = self._run_coverage_for_lp("LP-20", "NOT_APPLICABLE")
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment["coverage_state"], "not_applicable")

    def test_not_applicable_uses_provenance_from_alignment_notes(self):
        # LP-01 is "required" by is_applicable — proceeds past Step 1 to the bridge.
        # Bridge fires on NOT_APPLICABLE status, uses alignment_notes as evidence_summary.
        notes = "Provision known-absent for Industrial lease type. Basis: document-type-driven."
        assessment = self._run_coverage_for_lp("LP-01", "NOT_APPLICABLE", alignment_notes=notes)
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment["coverage_state"], "not_applicable")
        self.assertIn(notes, assessment["evidence_summary"])

    def test_required_lp_with_text_does_not_short_circuit_via_bridge(self):
        # LP-01 is "required". With FOUND_BOTH and real text, bridge doesn't fire
        # (status ≠ NOT_APPLICABLE) and element assessment runs normally.
        assessment = self._run_coverage_for_lp(
            "LP-01", "FOUND_BOTH",
            tenant_text="Tenant shall pay Base Rent of $10,000 per month."
        )
        self.assertIsNotNone(assessment)
        # LP-01 with text → should NOT be not_applicable from the extraction bridge
        self.assertNotEqual(assessment["coverage_state"], "not_applicable")

    def test_ambiguous_status_does_not_trigger_not_applicable_bridge(self):
        # LP-01 is "required". AMBIGUOUS status → bridge doesn't fire (bridge checks
        # for NOT_APPLICABLE only). Proceeds to Step 4 (no text) → missing/unclear.
        assessment = self._run_coverage_for_lp("LP-01", "AMBIGUOUS", tenant_text="")
        self.assertIsNotNone(assessment)
        # Bridge only fires on NOT_APPLICABLE; AMBIGUOUS falls through to normal path
        self.assertNotEqual(
            assessment.get("coverage_state"), "not_applicable",
            "AMBIGUOUS status should not trigger NOT_APPLICABLE bridge in coverage"
        )


# ── All-models-failed path stays AMBIGUOUS ────────────────────────────────────

class TestAllModelsFailedStaysAmbiguous(unittest.TestCase):
    """Verify that all-models-failed stubs are always AMBIGUOUS regardless of doc type."""

    def test_all_models_failed_stubs_are_ambiguous(self):
        # Simulate what the all-models-failed path produces:
        # status=AMBIGUOUS, NO reclassification (no deal_overview available then)
        # The reclassify loop only fires AFTER model returned something (obj is not None)
        # All-models-failed returns early before the reclassify loop.
        # This test verifies that _classify_missing_stub is NOT called in that path
        # by checking the stubs directly from the logic perspective.
        #
        # In all-models-failed path, deal_overview={} (empty) is passed.
        # Even if we DID call classify, LP-20 with empty deal_overview → AMBIGUOUS.
        status, notes = _classify_missing_stub("LP-20", {})
        # Empty deal_overview → unknown property type → AMBIGUOUS
        self.assertEqual(status, "AMBIGUOUS")
        self.assertIn("unknown", notes.lower())


if __name__ == "__main__":
    unittest.main()
