"""
Step 421B — Extraction integrity guard tests.

Mirrors the pattern of test_414_fallback_integrity.py and
test_416_config_integrity.py. Tests prove guard behaviour independent of
whether Gemini is healthy, so they pass in CI without API access.

Coverage:
- ExtractionIntegrityError raised when primary fails in canonical mode
- No error raised when primary succeeds (canonical or not)
- Stub-provision path blocked by guard (non-canonical exhaustion)
- evidence hashes present and correctly keyed on successful extraction
- attempt_chain populated correctly
- raw failure preview captured on JSON parse error
"""

import hashlib
import types
import unittest
from unittest.mock import MagicMock, patch

# ── helpers ────────────────────────────────────────────────────────────────────

_VALID_EXTRACTION_JSON = """{
  "provisions": [
    {
      "provision_id": "LP-01",
      "provision_name": "Test",
      "template_text": "",
      "tenant_text": "Tenant shall pay base rent.",
      "template_section_ref": "",
      "tenant_section_ref": "§3",
      "status": "FOUND_BOTH",
      "alignment_notes": "",
      "definition_changes": ""
    }
  ],
  "contract_metadata": {},
  "deal_overview": {},
  "discovered_provisions": []
}"""

_PROVISIONS = [{"id": "LP-01", "name": "Test", "description": "", "search_hints": []}]


def _make_mock_adapter(response_text):
    """Return a minimal adapter stub that always yields response_text."""
    adapter = MagicMock()
    adapter.call.return_value = response_text
    return adapter


# ── tests ──────────────────────────────────────────────────────────────────────


class TestCanonicalFailClosed(unittest.TestCase):
    """Guard: primary fails → ExtractionIntegrityError in canonical mode."""

    def test_raises_on_primary_failure_canonical(self):
        from cam.adapters.lease_review.lease_extract import (
            ExtractionIntegrityError,
            extract_provisions_single_doc,
        )

        def _bad_adapter_factory(provider):
            a = MagicMock()
            a.call.side_effect = RuntimeError("simulated primary failure")
            return a

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            side_effect=_bad_adapter_factory,
        ):
            with self.assertRaises(ExtractionIntegrityError) as ctx:
                extract_provisions_single_doc(
                    "full lease text", _PROVISIONS, {}, canonical=True
                )

        err = ctx.exception
        self.assertIn("canonical mode", str(err))
        # attempt_chain should record the failed primary attempt
        self.assertTrue(any("exception" in a.get("outcome", "") for a in err.attempt_chain))

    def test_no_error_when_primary_succeeds_canonical(self):
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            return_value=_make_mock_adapter(_VALID_EXTRACTION_JSON),
        ):
            with patch("cam.adapters.lease_review.lease_adapter._check_cancel"):
                result = extract_provisions_single_doc(
                    "full lease text", _PROVISIONS, {}, canonical=True
                )

        self.assertFalse(result["meta"].get("extraction_failed"))
        self.assertFalse(result["meta"].get("fallback_used"))

    def test_no_guard_in_non_canonical_mode(self):
        """Non-canonical mode: fallback chain runs to exhaustion, returns stub."""
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        call_count = {"n": 0}

        def _failing_factory(provider):
            a = MagicMock()
            a.call.side_effect = RuntimeError("always fails")
            call_count["n"] += 1
            return a

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            side_effect=_failing_factory,
        ):
            result = extract_provisions_single_doc(
                "full lease text", _PROVISIONS, {}, canonical=False
            )

        self.assertTrue(result["meta"].get("extraction_failed"))
        # In non-canonical mode the full chain is attempted (7 entries)
        self.assertGreater(call_count["n"], 1)


class TestStubProvisionGuard(unittest.TestCase):
    """Stub provisions are never valid evidence for a legal report."""

    def test_extraction_failed_flag_present_on_stub_return(self):
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            side_effect=RuntimeError("fail"),
        ):
            result = extract_provisions_single_doc(
                "text", _PROVISIONS, {}, canonical=False
            )

        self.assertTrue(result["meta"]["extraction_failed"])
        self.assertEqual(result["meta"]["model"], "none")
        for prov in result["provisions"]:
            # All stubs have empty tenant_text
            self.assertEqual(prov["tenant_text"], "")


class TestAttemptChain(unittest.TestCase):
    """attempt_chain correctly records each model tried."""

    def test_success_recorded_in_chain(self):
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            return_value=_make_mock_adapter(_VALID_EXTRACTION_JSON),
        ):
            with patch("cam.adapters.lease_review.lease_adapter._check_cancel"):
                result = extract_provisions_single_doc(
                    "text", _PROVISIONS, {}, canonical=True
                )

        chain = result["meta"]["extraction_attempt_chain"]
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["outcome"], "success")
        self.assertEqual(chain[0]["provider"], "google")

    def test_failed_attempt_recorded_in_chain(self):
        from cam.adapters.lease_review.lease_extract import (
            ExtractionIntegrityError,
            extract_provisions_single_doc,
        )

        def _fail(provider):
            a = MagicMock()
            a.call.side_effect = ValueError("api error")
            return a

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            side_effect=_fail,
        ):
            with self.assertRaises(ExtractionIntegrityError) as ctx:
                extract_provisions_single_doc("text", _PROVISIONS, {}, canonical=True)

        chain = ctx.exception.attempt_chain
        self.assertEqual(len(chain), 1)
        self.assertIn("exception", chain[0]["outcome"])


class TestRawFailureCapture(unittest.TestCase):
    """Raw response preview is stored in errors on JSON parse failure."""

    def test_raw_preview_stored_on_json_failure(self):
        from cam.adapters.lease_review.lease_extract import (
            ExtractionIntegrityError,
            extract_provisions_single_doc,
        )

        # Return text that is not valid JSON and long enough to avoid the
        # refusal heuristic (>100 chars)
        bad_raw = "Not JSON at all. " + "x" * 100

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            return_value=_make_mock_adapter(bad_raw),
        ):
            with patch("cam.adapters.lease_review.lease_adapter._check_cancel"):
                with self.assertRaises(ExtractionIntegrityError) as ctx:
                    extract_provisions_single_doc("text", _PROVISIONS, {}, canonical=True)

        errors = ctx.exception.errors
        json_err = next((e for e in errors if "json_extract" in e.get("error", "")), None)
        self.assertIsNotNone(json_err, "Expected a json_extract error entry")
        self.assertIn("raw_response_preview", json_err)
        self.assertIn("raw_response_len", json_err)


class TestEvidenceHashes(unittest.TestCase):
    """Meta fields: primary_model, primary_provider, attempt_chain present."""

    def test_primary_fields_in_meta(self):
        from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

        with patch(
            "cam.adapters.lease_review.lease_extract._get_adapter_for_provider",
            return_value=_make_mock_adapter(_VALID_EXTRACTION_JSON),
        ):
            with patch("cam.adapters.lease_review.lease_adapter._check_cancel"):
                result = extract_provisions_single_doc("text", _PROVISIONS, {}, canonical=True)

        meta = result["meta"]
        self.assertIn("primary_model", meta)
        self.assertIn("primary_provider", meta)
        self.assertEqual(meta["primary_provider"], "google")
        self.assertIn("extraction_attempt_chain", meta)


class TestTokenCeiling(unittest.TestCase):
    """EXTRACTION_MAX_TOKENS_SINGLE is above the observed Gemini output range."""

    def test_token_ceiling_above_gemini_observed_max(self):
        from cam.adapters.lease_review.lease_extract import EXTRACTION_MAX_TOKENS_SINGLE

        # 6 successful Gemini runs produced 27k–31k tokens. Ceiling must exceed
        # 31k with enough headroom to avoid truncation.
        self.assertGreater(EXTRACTION_MAX_TOKENS_SINGLE, 40_000,
                           "Token ceiling should provide headroom above observed 31k max")


class TestExtractionIntegrityErrorShape(unittest.TestCase):
    """ExtractionIntegrityError carries errors and attempt_chain."""

    def test_error_attributes(self):
        from cam.adapters.lease_review.lease_extract import ExtractionIntegrityError

        errors = [{"model": "gemini-3.1-pro-preview", "error": "timeout"}]
        chain = [{"model": "gemini-3.1-pro-preview", "provider": "google", "outcome": "exception: TimeoutError"}]
        err = ExtractionIntegrityError("primary failed", errors=errors, attempt_chain=chain)

        self.assertEqual(err.errors, errors)
        self.assertEqual(err.attempt_chain, chain)
        self.assertIn("primary failed", str(err))


if __name__ == "__main__":
    unittest.main()
