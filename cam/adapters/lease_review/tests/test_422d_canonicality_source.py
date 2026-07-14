"""
Step 422D — Extraction gate reads meta["canonical"], not fallback_used.

Tests cover:
1. canonical=True + fail_missing → GateAbortError (regression: still aborts)
2. canonical=False + fail_missing → degraded flags, NO abort (the bug fixed by 422D)
3. canonical=False + fallback_used=False → not misread as canonical (orthogonality)
4. canonical=True + fallback_used=True → still aborts on fail_missing
5. meta["canonical"] absent → treated as canonical (fail-safe)
6. Complete extraction, canonical=True → no abort
7. Complete extraction, canonical=False → no abort
8. meta["canonical"] recorded at extractor boundary (success path)
9. meta["canonical"] recorded at extractor boundary (stub/failure path)
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_extraction(provisions_list, canonical=True, fallback_used=False, deal_overview=None):
    return {
        "provisions": provisions_list,
        "contract_metadata": {},
        "deal_overview": deal_overview or {"property_type": "Industrial"},
        "discovered_provisions": [],
        "meta": {
            "model": "gemini-test",
            "provider": "google",
            "canonical": canonical,
            "fallback_used": fallback_used,
            "elapsed_sec": 0.1,
            "errors": [],
            "single_doc": True,
            "extraction_attempt_chain": [],
        },
    }


def _make_extraction_no_canonical_key(provisions_list, fallback_used=False):
    """Legacy artifact: meta without 'canonical' key."""
    d = _make_extraction(provisions_list, canonical=True, fallback_used=fallback_used)
    del d["meta"]["canonical"]
    return d


def _prov(pid, status, tenant_text=""):
    return {
        "provision_id": pid,
        "provision_name": f"{pid} Name",
        "template_text": "",
        "tenant_text": tenant_text,
        "template_section_ref": "",
        "tenant_section_ref": "",
        "status": status,
        "alignment_notes": "test",
        "definition_changes": "",
    }


def _make_tenant_file(content="This is a commercial lease."):
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    tf.write(content)
    tf.flush()
    tf.close()
    return tf.name


def _patch_pre_gate(extraction_result):
    """Patch up to and including extraction; return context manager."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        parse_mock = MagicMock(return_value="lease text for industrial sublease")
        gate_mock = MagicMock(return_value={"is_lease": True, "abort": False, "elapsed_sec": 0.01})
        extract_mock = MagicMock(return_value=extraction_result)
        cov_spy = MagicMock(return_value=[])

        with patch("cam.adapters.lease_review.lease_adapter.parse_document", parse_mock), \
             patch("cam.adapters.lease_review.lease_adapter.check_document_is_lease", gate_mock), \
             patch("cam.adapters.lease_review.lease_extract.extract_provisions_single_doc", extract_mock), \
             patch("cam.adapters.lease_review.lease_coverage.assess_coverage", cov_spy):
            yield {"parse": parse_mock, "gate": gate_mock, "extract": extract_mock, "assess_coverage": cov_spy}

    return _ctx()


def _patch_full_pipeline(extraction_result):
    """Patch full pipeline including Phase 5 downstream mocks."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        parse_mock = MagicMock(return_value="lease text for industrial sublease")
        gate_mock = MagicMock(return_value={"is_lease": True, "abort": False, "elapsed_sec": 0.01})
        extract_mock = MagicMock(return_value=extraction_result)
        cov_spy = MagicMock(return_value=[])
        ns_mock = MagicMock(return_value={})
        ns_summary_mock = MagicMock(return_value={})
        cov_summary_mock = MagicMock(return_value={"not_applicable_count": 0})
        validate_chains_mock = MagicMock(return_value={"run_config_degraded": False})

        with patch("cam.adapters.lease_review.lease_adapter.parse_document", parse_mock), \
             patch("cam.adapters.lease_review.lease_adapter.check_document_is_lease", gate_mock), \
             patch("cam.adapters.lease_review.lease_extract.extract_provisions_single_doc", extract_mock), \
             patch("cam.adapters.lease_review.lease_coverage.assess_coverage", cov_spy), \
             patch("cam.adapters.lease_review.lease_negative_space.detect_negative_space", ns_mock), \
             patch("cam.adapters.lease_review.lease_negative_space.summarize_negative_space", ns_summary_mock), \
             patch("cam.adapters.lease_review.lease_coverage.summarize_coverage", cov_summary_mock), \
             patch("cam.adapters.lease_review.lease_coverage_305.validate_evaluator_chains", validate_chains_mock):
            yield {"parse": parse_mock, "gate": gate_mock, "extract": extract_mock, "assess_coverage": cov_spy}

    return _ctx()


# ── Tests: canonicality derived from meta["canonical"], not fallback_used ─────

class TestCanonicalFieldGatesBehavior(unittest.TestCase):

    def test_canonical_true_fail_missing_aborts(self):
        """canonical=True + fail_missing → GateAbortError. Regression check."""
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "AMBIGUOUS", tenant_text="")]
        extraction = _make_extraction(provisions, canonical=True, fallback_used=False)
        tenant_file = _make_tenant_file()
        try:
            with _patch_pre_gate(extraction):
                with self.assertRaises(GateAbortError):
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
        finally:
            os.unlink(tenant_file)

    def test_canonical_false_fail_missing_does_not_abort(self):
        """
        canonical=False + fail_missing → degraded flags, NO abort.

        This is the bug fixed by 422D. Before the fix, the gate used
        `not meta.get("fallback_used", False)` which misread canonical=False +
        fallback_used=False as is_canonical=True and aborted instead of degrading.
        """
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "AMBIGUOUS", tenant_text="")]
        # canonical=False (non-canonical mode), fallback_used=False (primary succeeded)
        extraction = _make_extraction(provisions, canonical=False, fallback_used=False)
        tenant_file = _make_tenant_file()
        try:
            with _patch_full_pipeline(extraction):
                try:
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
                except GateAbortError as e:
                    self.fail(
                        f"GateAbortError raised for canonical=False run — "
                        f"non-canonical path was misread as canonical: {e}"
                    )
                except Exception:
                    pass  # other pipeline errors are fine; abort is the failure
        finally:
            os.unlink(tenant_file)

    def test_canonical_false_fallback_false_not_misread_as_canonical(self):
        """
        canonical=False + fallback_used=False must not abort.

        Orthogonality check: these are two independent booleans. The old code's
        `_is_canonical = not meta.get("fallback_used", False)` would read this
        combination as is_canonical=True. The new code reads meta["canonical"]
        directly and gets False → degraded path, not abort.
        """
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "AMBIGUOUS", tenant_text="")]
        extraction = _make_extraction(provisions, canonical=False, fallback_used=False)
        tenant_file = _make_tenant_file()
        try:
            with _patch_full_pipeline(extraction):
                aborted = False
                try:
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
                except GateAbortError:
                    aborted = True
                except Exception:
                    pass
            self.assertFalse(aborted, "canonical=False + fallback_used=False must not trigger abort")
        finally:
            os.unlink(tenant_file)

    def test_canonical_true_fallback_true_aborts(self):
        """
        canonical=True + fallback_used=True + fail_missing → still aborts.

        Old code: not fallback_used=True → is_canonical=False → no abort (wrong).
        New code: meta["canonical"]=True → is_canonical=True → aborts (correct).
        """
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "AMBIGUOUS", tenant_text="")]
        extraction = _make_extraction(provisions, canonical=True, fallback_used=True)
        tenant_file = _make_tenant_file()
        try:
            with _patch_pre_gate(extraction):
                with self.assertRaises(GateAbortError):
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
        finally:
            os.unlink(tenant_file)

    def test_canonical_absent_treated_as_canonical(self):
        """meta without 'canonical' key → fail-safe: treated as canonical → aborts."""
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "AMBIGUOUS", tenant_text="")]
        extraction = _make_extraction_no_canonical_key(provisions)
        tenant_file = _make_tenant_file()
        try:
            with _patch_pre_gate(extraction):
                with self.assertRaises(GateAbortError):
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
        finally:
            os.unlink(tenant_file)

    def test_complete_extraction_canonical_no_abort(self):
        """Complete extraction, canonical=True → gate passes, no abort."""
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "FOUND_BOTH", tenant_text="100% operating expenses.")]
        extraction = _make_extraction(provisions, canonical=True)
        tenant_file = _make_tenant_file()
        try:
            with _patch_full_pipeline(extraction):
                try:
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
                except GateAbortError:
                    self.fail("GateAbortError raised for complete extraction with canonical=True")
                except Exception:
                    pass
        finally:
            os.unlink(tenant_file)

    def test_complete_extraction_non_canonical_no_abort(self):
        """Complete extraction, canonical=False → gate passes, no abort."""
        from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only, GateAbortError
        provisions = [_prov("LP-07", "FOUND_BOTH", tenant_text="100% operating expenses.")]
        extraction = _make_extraction(provisions, canonical=False)
        tenant_file = _make_tenant_file()
        try:
            with _patch_full_pipeline(extraction):
                try:
                    run_lease_coverage_only(tenant_file, provisions=[], config={})
                except GateAbortError:
                    self.fail("GateAbortError raised for complete extraction with canonical=False")
                except Exception:
                    pass
        finally:
            os.unlink(tenant_file)


# ── Tests: extractor boundary records meta["canonical"] ───────────────────────

class TestExtractorRecordsCanonicalField(unittest.TestCase):
    """
    Unit-test that extract_provisions_single_doc() writes meta["canonical"] on both
    the success path and the stub/failure path.

    We patch only the inner model call (the adapter) so the function runs fully
    but never contacts a real model.
    """

    def _make_raw_response(self):
        """Minimal valid extraction JSON the function will accept (non-empty provisions)."""
        import json
        return json.dumps({
            "provisions": [
                {
                    "provision_id": "LP-01",
                    "provision_name": "Base Rent",
                    "template_text": "",
                    "tenant_text": "Tenant pays base rent of $10,000 per month.",
                    "template_section_ref": "",
                    "tenant_section_ref": "",
                    "status": "FOUND_BOTH",
                    "alignment_notes": "Rent found",
                    "definition_changes": "",
                }
            ],
            "contract_metadata": {"lease_type": "industrial"},
            "deal_overview": {"property_type": "Industrial"},
        })

    def _health_mock(self):
        """Return a health-tracker mock that reports all providers available."""
        h = MagicMock()
        h.is_available.return_value = True
        return h

    def test_success_path_records_canonical_true(self):
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        adapter_mock = MagicMock()
        adapter_mock.call.return_value = self._make_raw_response()

        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
                   return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_extract.get_health_tracker",
                   return_value=self._health_mock()), \
             patch("cam.adapters.lease_review.lease_adapter._check_cancel", return_value=None):
            result = extract_provisions_single_doc(
                tenant_text="This is a commercial lease.",
                provisions=[],
                config={},
                canonical=True,
            )

        self.assertIn("canonical", result["meta"])
        self.assertTrue(result["meta"]["canonical"])

    def test_success_path_records_canonical_false(self):
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        adapter_mock = MagicMock()
        adapter_mock.call.return_value = self._make_raw_response()

        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
                   return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_extract.get_health_tracker",
                   return_value=self._health_mock()), \
             patch("cam.adapters.lease_review.lease_adapter._check_cancel", return_value=None):
            result = extract_provisions_single_doc(
                tenant_text="This is a commercial lease.",
                provisions=[],
                config={},
                canonical=False,
            )

        self.assertIn("canonical", result["meta"])
        self.assertFalse(result["meta"]["canonical"])

    def test_stub_failure_path_records_canonical(self):
        """All models fail → stub return must still include meta['canonical']."""
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        adapter_mock = MagicMock()
        adapter_mock.call.side_effect = Exception("model unavailable")

        # canonical=False so the fail-closed guard doesn't raise; function reaches
        # full-chain exhaustion and returns the stub result
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
                   return_value=adapter_mock):
            result = extract_provisions_single_doc(
                tenant_text="This is a commercial lease.",
                provisions=[],
                config={},
                canonical=False,
            )

        self.assertIn("canonical", result["meta"])
        self.assertFalse(result["meta"]["canonical"])
        self.assertTrue(result["meta"].get("extraction_failed"))


if __name__ == "__main__":
    unittest.main()
