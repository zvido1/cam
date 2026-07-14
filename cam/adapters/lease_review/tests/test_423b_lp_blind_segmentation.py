"""
Step 423B — LP-blind span proposal / segmentation tests.

Covers: Part 0 normalization-semantics safety tests, the LP-blind output
contract, the structural-only span taxonomy, neutral-label non-routing
provenance, proposal resolution through the 423A substrate, hints-not-
identity, sidecar artifact metadata, segmentation-call integrity, and the
pipeline seam (nothing live imports this module or its sidecar).

No network calls. All model calls are mocked — see test_423b (Part 6) smoke
script for the (separately run, not-part-of-pytest) live plumbing check.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from cam.adapters.lease_review.lease_evidence_spans import (
    build_canonical_source,
    resolve_span,
    VERIFIED,
    AMBIGUOUS,
    UNVERIFIED,
)
from cam.adapters.lease_review.lease_segmentation import (
    ALLOWED_SPAN_TYPES,
    SegmentationIntegrityError,
    build_span_universe_sidecar,
    propose_spans,
    resolve_proposed_spans,
    validate_segmentation_output,
)


SAMPLE_LEASE_TEXT = (
    "ARTICLE 1 - BASIC LEASE INFORMATION\n"
    "Tenant's Share of Operating Expenses of Building: 100%\n"
    "Building's Share of Project Operating Expenses: 45.79%\n"
    "Rent Adjustment Percentage: 3%\n\n"
    "ARTICLE 2 - OPERATING EXPENSES\n"
    "Controllable Operating Expenses shall not increase by more than 5% "
    "per year on a cumulative, compounded basis.\n\n"
    "ARTICLE 3 - INSURANCE\n"
    "Tenant shall maintain commercial general liability insurance.\n\n"
    "ARTICLE 4 - INSURANCE REPEATED\n"
    "Tenant shall maintain commercial general liability insurance.\n"
)


# ── Part 0 — normalization semantics safety tests ──────────────────────────────

class TestPart0NormalizationSafetyFollowOn(unittest.TestCase):
    """Required by the 423B brief's Part 0. These exercise EXISTING 423A
    resolver behavior — no resolver code changed, only its documentation
    (see lease_evidence_spans.py module docstring update). Listed here
    because 423B is the step that closed the documentation gap."""

    def test_changed_digit_is_unverified(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="p0-1")
        proposed = "Building's Share of Project Operating Expenses: 45.80%"
        span = resolve_span(source, proposed, "EV-P0-1")
        self.assertEqual(span.verification_status, UNVERIFIED)

    def test_whitespace_reflow_is_verified(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="p0-2")
        proposed = "Tenant's Share of Operating\n  Expenses of Building: 100%"
        span = resolve_span(source, proposed, "EV-P0-2")
        self.assertEqual(span.verification_status, VERIFIED)
        self.assertTrue(span.is_valid_invariant(source))

    def test_canonical_usability_false_for_changed_substantive_content(self):
        from cam.adapters.lease_review.lease_evidence_spans import is_usable_in_canonical_stage5
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="p0-3")
        proposed = "Rent Adjustment Percentage: 4%"  # source says 3%
        span = resolve_span(source, proposed, "EV-P0-3")
        self.assertEqual(span.verification_status, UNVERIFIED)
        self.assertFalse(is_usable_in_canonical_stage5(span))


# ── Part 7.1 — LP-blind output contract ─────────────────────────────────────────

class TestLPBlindOutputContract(unittest.TestCase):
    def test_well_formed_proposal_passes(self):
        obj = {"spans": [{"quote": "Tenant shall maintain insurance.", "span_type": "clause"}]}
        ok, why = validate_segmentation_output(obj)
        self.assertTrue(ok, why)

    def test_lp_id_field_rejected(self):
        obj = {"spans": [{"quote": "text", "span_type": "clause", "provision_id": "LP-07"}]}
        ok, why = validate_segmentation_output(obj)
        self.assertFalse(ok)

    def test_lp_assignment_field_rejected(self):
        obj = {"spans": [{"quote": "text", "span_type": "clause", "lp_id": "LP-07"}]}
        ok, why = validate_segmentation_output(obj)
        self.assertFalse(ok)

    def test_verdict_field_rejected(self):
        obj = {"spans": [{"quote": "text", "span_type": "clause", "coverage_verdict": "present"}]}
        ok, why = validate_segmentation_output(obj)
        self.assertFalse(ok)

    def test_risk_field_rejected(self):
        obj = {"spans": [{"quote": "text", "span_type": "clause", "risk": "Improvement"}]}
        ok, why = validate_segmentation_output(obj)
        self.assertFalse(ok)

    def test_favorability_field_rejected(self):
        obj = {"spans": [{"quote": "text", "span_type": "clause", "tenant_favorable": True}]}
        ok, why = validate_segmentation_output(obj)
        self.assertFalse(ok)


# ── Part 7.2 — structural span types only ───────────────────────────────────────

class TestStructuralSpanTypesOnly(unittest.TestCase):
    def test_all_four_allowed_types_pass(self):
        self.assertEqual(ALLOWED_SPAN_TYPES, frozenset({"clause", "table", "definition", "other"}))
        for t in ALLOWED_SPAN_TYPES:
            obj = {"spans": [{"quote": "text", "span_type": t}]}
            ok, why = validate_segmentation_output(obj)
            self.assertTrue(ok, f"{t}: {why}")

    def test_semantic_types_rejected(self):
        for bad_type in ("cap", "carveout", "condition", "exception", "remedy", "cross_reference", "key_term"):
            obj = {"spans": [{"quote": "text", "span_type": bad_type}]}
            ok, why = validate_segmentation_output(obj)
            self.assertFalse(ok, f"{bad_type} should have been rejected as a structural type")


# ── Part 7.3 — neutral label is non-routing provenance ──────────────────────────

class TestNeutralLabelNonRouting(unittest.TestCase):
    def test_neutral_label_may_be_present(self):
        obj = {"spans": [{"quote": "text", "span_type": "clause", "neutral_label": "insurance requirement"}]}
        ok, why = validate_segmentation_output(obj)
        self.assertTrue(ok, why)

    def test_neutral_label_does_not_affect_resolution_outcome(self):
        """Two proposals identical except neutral_label must resolve
        identically — the label carries no routing weight."""
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="neutral-test")
        proposals_a = [{"quote": "Tenant shall maintain commercial general liability insurance.",
                         "span_type": "clause", "neutral_label": "insurance clause A"}]
        proposals_b = [{"quote": "Tenant shall maintain commercial general liability insurance.",
                         "span_type": "clause", "neutral_label": "totally different label"}]
        # Both quotes are duplicated in SAMPLE_LEASE_TEXT (Article 3 and 4) with
        # no anchor, so both resolve identically (ambiguous) regardless of label.
        records_a = resolve_proposed_spans(source, proposals_a)
        records_b = resolve_proposed_spans(source, proposals_b)
        self.assertEqual(records_a[0]["verification_status"], records_b[0]["verification_status"])
        self.assertEqual(records_a[0]["start_char"], records_b[0]["start_char"])

    def test_no_downstream_branch_on_neutral_label(self):
        """Code-level check: resolve_proposed_spans must not contain a
        conditional keyed on neutral_label's value."""
        import inspect
        from cam.adapters.lease_review import lease_segmentation
        src = inspect.getsource(lease_segmentation.resolve_proposed_spans)
        # neutral_label is only ever read into the output record, never
        # compared/branched on.
        self.assertNotIn("neutral_label ==", src)
        self.assertNotIn("if neutral_label", src)


# ── Part 7.4 / 7.5 / 7.6 / 7.7 / 7.8 — resolution outcomes ──────────────────────

class TestProposalResolutionOutcomes(unittest.TestCase):
    def setUp(self):
        self.source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="resolution-test")

    def test_exact_quote_resolves_verified(self):
        proposals = [{"quote": "Rent Adjustment Percentage: 3%", "span_type": "table"}]
        records = resolve_proposed_spans(self.source, proposals)
        self.assertEqual(records[0]["verification_status"], VERIFIED)
        self.assertIsNotNone(records[0]["start_char"])
        self.assertTrue(records[0]["usable_in_canonical_stage5"])

    def test_whitespace_reflow_verified(self):
        proposals = [{
            "quote": "Controllable Operating Expenses shall not increase by more\n  than 5% per year",
            "span_type": "clause",
        }]
        records = resolve_proposed_spans(self.source, proposals)
        self.assertEqual(records[0]["verification_status"], VERIFIED)

    def test_changed_digit_fails(self):
        proposals = [{"quote": "Tenant's Share of Operating Expenses of Building: 99%", "span_type": "table"}]
        records = resolve_proposed_spans(self.source, proposals)
        self.assertEqual(records[0]["verification_status"], UNVERIFIED)
        self.assertFalse(records[0]["usable_in_canonical_stage5"])
        self.assertIsNotNone(records[0]["failure_reason"])

    def test_ambiguous_quote_not_verified(self):
        proposals = [{
            "quote": "Tenant shall maintain commercial general liability insurance.",
            "span_type": "clause",
        }]
        records = resolve_proposed_spans(self.source, proposals)
        self.assertEqual(records[0]["verification_status"], AMBIGUOUS)
        self.assertFalse(records[0]["usable_in_canonical_stage5"])

    def test_invented_quote_unverified(self):
        proposals = [{
            "quote": "This clause was invented and does not appear in the lease.",
            "span_type": "clause",
        }]
        records = resolve_proposed_spans(self.source, proposals)
        self.assertEqual(records[0]["verification_status"], UNVERIFIED)


# ── Part 7.9 — proposal hints are not canonical span identity ───────────────────

class TestHintsNotCanonicalIdentity(unittest.TestCase):
    def test_anchor_hint_disambiguates_but_is_not_persisted_on_evidence_span(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="hints-test")
        # Duplicate quote, disambiguated via table_hint mapped to source_anchor.
        proposals = [{
            "quote": "Tenant shall maintain commercial general liability insurance.",
            "span_type": "clause",
            "table_hint": "ARTICLE 4 - INSURANCE REPEATED",
        }]
        records = resolve_proposed_spans(source, proposals)
        self.assertEqual(records[0]["verification_status"], VERIFIED)
        # Resolved past ARTICLE 4's heading, not ARTICLE 3's.
        self.assertGreater(records[0]["start_char"], SAMPLE_LEASE_TEXT.index("ARTICLE 4"))

    def test_evidence_span_dataclass_has_no_page_ref_or_table_ref(self):
        from cam.adapters.lease_review.lease_evidence_spans import EvidenceSpan
        field_names = {f for f in EvidenceSpan.__dataclass_fields__.keys()}
        self.assertNotIn("page_ref", field_names)
        self.assertNotIn("table_ref", field_names)
        self.assertNotIn("page_hint", field_names)
        self.assertNotIn("table_hint", field_names)

    def test_persisted_identity_fields_are_offset_and_hash_based_only(self):
        from cam.adapters.lease_review.lease_evidence_spans import EvidenceSpan
        field_names = set(EvidenceSpan.__dataclass_fields__.keys())
        expected = {
            "evidence_span_id", "source_document_hash", "canonical_text_hash",
            "start_char", "end_char", "span_text", "span_text_hash",
            "normalization_profile", "verification_status", "section_ref", "source_anchor",
        }
        self.assertEqual(field_names, expected)


# ── Part 7.10 — sidecar artifact metadata ────────────────────────────────────────

class TestSidecarArtifactMetadata(unittest.TestCase):
    def test_sidecar_contains_required_metadata(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="sidecar-test")
        segmentation_result = {
            "spans": [],
            "meta": {
                "provider": "google", "model": "gemini-3.1-pro-preview",
                "primary_provider": "google", "primary_model": "gemini-3.1-pro-preview",
                "canonical": True, "fallback_used": False, "fallback_chain": [],
                "degraded": False, "parse_or_validation_failure_reason": None,
                "declared_generation_config": {"temperature": 0.0, "max_output_tokens": 16000},
                "integrity_metadata": {"transmitted": {"temperature": 0.0}},
                "prompt_hash": "abc123", "config_hash": "def456",
                "elapsed_sec": 1.2, "errors": [], "attempt_chain": [],
            },
        }
        proposals = [{"quote": "Rent Adjustment Percentage: 3%", "span_type": "table"}]
        records = resolve_proposed_spans(source, proposals)
        sidecar = build_span_universe_sidecar(source, segmentation_result, records)

        self.assertEqual(sidecar["source_document_hash"], source.source_document_hash)
        self.assertEqual(sidecar["canonical_text_hash"], source.canonical_text_hash)
        self.assertIn("prompt_hash", sidecar["segmentation_meta"])
        self.assertIn("config_hash", sidecar["segmentation_meta"])
        self.assertIn("canonical", sidecar["segmentation_meta"])
        self.assertEqual(sidecar["total_proposed_spans"], 1)
        self.assertEqual(sidecar["count_verified"], 1)
        self.assertEqual(sidecar["count_ambiguous"], 0)
        self.assertEqual(sidecar["count_unverified"], 0)
        self.assertTrue(sidecar["_not_live_pipeline_input"])
        self.assertTrue(sidecar["neutral_label_is_non_routing_provenance"])
        self.assertTrue(sidecar["hints_are_non_canonical_resolution_aids_only"])

    def test_sidecar_is_json_serializable(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="sidecar-json-test")
        segmentation_result = {"spans": [], "meta": {"canonical": True, "fallback_used": False,
                                                       "fallback_chain": [], "degraded": False}}
        records = resolve_proposed_spans(source, [{"quote": "Rent Adjustment Percentage: 3%", "span_type": "table"}])
        sidecar = build_span_universe_sidecar(source, segmentation_result, records)
        json.dumps(sidecar)  # must not raise


# ── Segmentation-call integrity ──────────────────────────────────────────────────

def _health_mock():
    h = MagicMock()
    h.is_available.return_value = True
    return h


def _valid_raw_response():
    return json.dumps({
        "spans": [
            {"quote": "Rent Adjustment Percentage: 3%", "span_type": "table"},
        ]
    })


class TestSegmentationCallIntegrity(unittest.TestCase):
    def test_declared_params_transmitted_and_checked(self):
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_segmentation.get_health_tracker", return_value=_health_mock()):
            result = propose_spans(SAMPLE_LEASE_TEXT, canonical=True)

        integrity = result["meta"]["integrity_metadata"]
        self.assertIsNotNone(integrity)
        self.assertEqual(integrity["transmitted"]["temperature"], 0.0)
        self.assertIn("max_tokens", integrity["transmitted"])

    def test_canonical_flag_recorded_explicitly_on_success(self):
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_segmentation.get_health_tracker", return_value=_health_mock()):
            result = propose_spans(SAMPLE_LEASE_TEXT, canonical=True)
        self.assertIn("canonical", result["meta"])
        self.assertTrue(result["meta"]["canonical"])

    def test_canonical_flag_recorded_explicitly_on_degraded_path(self):
        """The 422D bug class: canonical must be an explicit field, never
        inferred from fallback_used. Here fallback_used is False (there is
        no fallback provider) AND canonical is False (degraded/debug mode)
        AND the primary failed — canonical must still read as explicitly
        False, not be conflated with fallback_used's also-False value."""
        adapter_mock = MagicMock()
        adapter_mock.call.side_effect = Exception("model unavailable")
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_segmentation.get_health_tracker", return_value=_health_mock()):
            result = propose_spans(SAMPLE_LEASE_TEXT, canonical=False)

        self.assertIn("canonical", result["meta"])
        self.assertFalse(result["meta"]["canonical"])
        self.assertFalse(result["meta"]["fallback_used"])
        self.assertTrue(result["meta"]["degraded"])
        self.assertIsNotNone(result["meta"]["parse_or_validation_failure_reason"])

    def test_canonical_primary_failure_raises_segmentation_integrity_error(self):
        adapter_mock = MagicMock()
        adapter_mock.call.side_effect = Exception("model unavailable")
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_segmentation.get_health_tracker", return_value=_health_mock()):
            with self.assertRaises(SegmentationIntegrityError):
                propose_spans(SAMPLE_LEASE_TEXT, canonical=True)

    def test_fallback_chain_and_fallback_used_visible_in_metadata(self):
        """No real fallback provider exists in this slice; the fields must
        still be present and visible (never silently omitted)."""
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_segmentation.get_health_tracker", return_value=_health_mock()):
            result = propose_spans(SAMPLE_LEASE_TEXT, canonical=True)
        self.assertIn("fallback_used", result["meta"])
        self.assertIn("fallback_chain", result["meta"])
        self.assertEqual(result["meta"]["fallback_chain"], [])

    def test_sidecar_records_actual_provider_model_config(self):
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_segmentation.get_health_tracker", return_value=_health_mock()):
            result = propose_spans(SAMPLE_LEASE_TEXT, canonical=True)

        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="integrity-sidecar-test")
        records = resolve_proposed_spans(source, result["spans"])
        sidecar = build_span_universe_sidecar(source, result, records)

        meta = sidecar["segmentation_meta"]
        self.assertEqual(meta["provider"], "google")
        self.assertIn("model", meta)
        self.assertIn("declared_generation_config", meta)
        self.assertIn("prompt_hash", meta)
        self.assertIn("config_hash", meta)


# ── Part 7.11 — pipeline seam ─────────────────────────────────────────────────────

class TestPipelineSeam(unittest.TestCase):
    def test_no_live_pipeline_file_imports_segmentation_module(self):
        import inspect
        from cam.adapters.lease_review import lease_adapter, lease_extract, lease_coverage

        for mod in (lease_adapter, lease_extract, lease_coverage):
            src = inspect.getsource(mod)
            self.assertNotIn(
                "lease_segmentation", src,
                f"{mod.__name__} must not reference lease_segmentation in this slice",
            )

    def test_no_live_pipeline_file_reads_the_sidecar_artifact(self):
        import inspect
        from cam.adapters.lease_review import lease_adapter, lease_extract, lease_coverage

        for mod in (lease_adapter, lease_extract, lease_coverage):
            src = inspect.getsource(mod)
            self.assertNotIn("423B_span_universe_smoke_sidecar", src)

    def test_evidence_spans_module_does_not_import_segmentation(self):
        """Layering check: lease_segmentation depends on lease_evidence_spans,
        never the reverse."""
        import inspect
        from cam.adapters.lease_review import lease_evidence_spans
        src = inspect.getsource(lease_evidence_spans)
        self.assertNotIn("lease_segmentation", src)


if __name__ == "__main__":
    unittest.main()
