"""
Step 423C — Element-guided, non-exclusive span elicitation tests.

Covers: cross-target dedup by offset, overlapping-but-distinct spans staying
distinct, LP-blind prompt text, span identity being offsets-only (never
elicited_by), unchanged 423A verification semantics, segmentation-call
integrity (canonical explicit, never inferred from fallback_used — the
422D bug class), and the pipeline seam.

No network calls. All model calls are mocked — see the Part 6 smoke script
(separately run, not part of pytest) for the one authorized live check.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from cam.adapters.lease_review.lease_evidence_spans import (
    build_canonical_source,
    VERIFIED,
    AMBIGUOUS,
    UNVERIFIED,
)
from cam.adapters.lease_review.lease_element_elicitation import (
    ElicitationIntegrityError,
    build_elicitation_sidecar,
    dedupe_elicited_spans,
    elicit_spans_for_targets,
    load_expected_elements_by_lp,
    resolve_elicited_spans,
    validate_elicitation_output,
    _build_target_list_text,
    _load_prompt_template,
)


SAMPLE_LEASE_TEXT = (
    "ARTICLE 1 - BASIC LEASE INFORMATION\n"
    "Tenant's Share of Operating Expenses of Building: 100%\n"
    "Building's Share of Project Operating Expenses: 45.79%\n"
    "Rent Adjustment Percentage: 3%\n\n"
    "ARTICLE 2 - OPERATING EXPENSES\n"
    "Tenant's Proportionate Share shall mean the percentage of total leasable "
    "area occupied by Tenant, as more particularly set forth in the Basic "
    "Lease Information.\n\n"
    "ARTICLE 3 - INSURANCE\n"
    "Tenant shall maintain commercial general liability insurance.\n\n"
    "ARTICLE 4 - INSURANCE REPEATED\n"
    "Tenant shall maintain commercial general liability insurance.\n"
)


def _elements_two(id_a="LP-07.proportionate_share_calculation", id_b="LP-02.calculation_methodology"):
    return [
        {"element_id": id_a, "element_label": "Share calc method", "synonyms": ["pro rata share"]},
        {"element_id": id_b, "element_label": "Escalation calc method", "synonyms": []},
    ]


# ── Dedup: same passage from two elements → one span, two elicited_by ──────────

class TestDedupSamePassageTwoElements(unittest.TestCase):
    def test_same_offsets_merge_into_one_span_with_two_provenance_entries(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="dedup-1")
        elements = _elements_two()
        elicitation_result = {
            "target_matches": [
                {"target": "Target 1", "quotes": ["Rent Adjustment Percentage: 3%"]},
                {"target": "Target 2", "quotes": ["Rent Adjustment Percentage: 3%"]},
            ]
        }
        raw = resolve_elicited_spans(source, elements, elicitation_result)
        self.assertEqual(len(raw), 2)  # two raw records before dedup

        deduped = dedupe_elicited_spans(raw)
        self.assertEqual(len(deduped), 1)
        span = deduped[0]
        self.assertEqual(span["verification_status"], VERIFIED)
        self.assertEqual(set(span["elicited_by"]), {"LP-07.proportionate_share_calculation", "LP-02.calculation_methodology"})
        self.assertEqual(len(span["elicited_by"]), 2)

    def test_quote_variants_preserved_on_merge(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="dedup-2")
        elements = _elements_two()
        # Same underlying offsets but two textually different quote strings
        # (e.g. one element quoted with slightly different whitespace).
        elicitation_result = {
            "target_matches": [
                {"target": "Target 1", "quotes": ["Rent Adjustment Percentage: 3%"]},
                {"target": "Target 2", "quotes": ["Rent Adjustment Percentage:\n  3%"]},
            ]
        }
        raw = resolve_elicited_spans(source, elements, elicitation_result)
        deduped = dedupe_elicited_spans(raw)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(len(deduped[0]["quote_variants"]), 2)


# ── Overlapping-but-distinct spans stay distinct ────────────────────────────────

class TestOverlappingNotMerged(unittest.TestCase):
    def test_overlapping_ranges_remain_separate_spans(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="overlap-1")
        elements = _elements_two()
        elicitation_result = {
            "target_matches": [
                {"target": "Target 1", "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"]},
                {"target": "Target 2", "quotes": [
                    "Tenant's Share of Operating Expenses of Building: 100%\n"
                    "Building's Share of Project Operating Expenses: 45.79%"
                ]},
            ]
        }
        raw = resolve_elicited_spans(source, elements, elicitation_result)
        deduped = dedupe_elicited_spans(raw)
        # Both verified, but at different (start, end) — must NOT collapse to one.
        self.assertEqual(len(deduped), 2)
        starts_ends = {(r["start_char"], r["end_char"]) for r in deduped}
        self.assertEqual(len(starts_ends), 2)


# ── LP-blind prompt ──────────────────────────────────────────────────────────────

class TestElicitationPromptIsLPBlind(unittest.TestCase):
    def test_rendered_prompt_contains_no_lp_ids(self):
        elements_by_lp = load_expected_elements_by_lp()
        lp07 = elements_by_lp["LP-07"]["elements"]
        target_list = _build_target_list_text(lp07)
        template = _load_prompt_template()
        rendered = template.replace("{tenant_text}", SAMPLE_LEASE_TEXT).replace("{target_list}", target_list)

        self.assertNotIn("LP-07", rendered)
        self.assertNotIn("LP-0", rendered)  # catches any LP-0X pattern
        self.assertNotIn("element_id", rendered)

    def test_prompt_contains_no_verdict_risk_favorability_vocabulary(self):
        elements_by_lp = load_expected_elements_by_lp()
        lp07 = elements_by_lp["LP-07"]["elements"]
        target_list = _build_target_list_text(lp07)
        template = _load_prompt_template()
        rendered = template.replace("{tenant_text}", SAMPLE_LEASE_TEXT).replace("{target_list}", target_list)

        rendered_lower = rendered.lower()
        # The instructions explicitly PROHIBIT these — the words appear as
        # negative instructions ("do not output risk labels"), which is
        # expected and fine. What must NOT appear is the vocabulary used as
        # a live output field name/directive to actually produce one. We
        # assert the prohibited concepts are only ever framed as "do not".
        for banned_phrase in ("tenant-favorable", "landlord-favorable", "coverage verdict"):
            if banned_phrase in rendered_lower:
                # must be part of a "do not" instruction, not a request
                idx = rendered_lower.index(banned_phrase)
                surrounding = rendered_lower[max(0, idx - 40):idx]
                self.assertIn("not", surrounding)

    def test_all_lp_elements_produce_lp_free_prompts(self):
        """Broader sweep: every LP's element batch renders to a prompt with
        no LP-id-shaped substring for that LP's own id."""
        elements_by_lp = load_expected_elements_by_lp()
        template = _load_prompt_template()
        for lp_id, entry in elements_by_lp.items():
            target_list = _build_target_list_text(entry["elements"])
            rendered = template.replace("{tenant_text}", "irrelevant").replace("{target_list}", target_list)
            self.assertNotIn(lp_id, rendered, f"{lp_id} leaked into its own prompt")


# ── Span identity is offsets; elicited_by never used as a key ───────────────────

class TestSpanIdentityOffsetsOnly(unittest.TestCase):
    def test_same_offset_different_elicited_by_merges(self):
        raw = [
            {
                "verification_status": VERIFIED, "start_char": 10, "end_char": 20,
                "span_text": "some text", "source_document_hash": "h1", "canonical_text_hash": "h1",
                "span_text_hash": "sh1", "elicited_by": ["A"], "quote_variants": ["some text"],
                "failure_reason": None, "usable_in_canonical_stage5": True,
            },
            {
                "verification_status": VERIFIED, "start_char": 10, "end_char": 20,
                "span_text": "some text", "source_document_hash": "h1", "canonical_text_hash": "h1",
                "span_text_hash": "sh1", "elicited_by": ["B"], "quote_variants": ["some text"],
                "failure_reason": None, "usable_in_canonical_stage5": True,
            },
        ]
        deduped = dedupe_elicited_spans(raw)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(set(deduped[0]["elicited_by"]), {"A", "B"})

    def test_different_offset_same_elicited_by_does_not_merge(self):
        """Proves the dedup key is (start_char, end_char), not elicited_by:
        identical elicited_by content at different offsets must NOT merge."""
        raw = [
            {
                "verification_status": VERIFIED, "start_char": 10, "end_char": 20,
                "span_text": "text one", "source_document_hash": "h1", "canonical_text_hash": "h1",
                "span_text_hash": "sh1", "elicited_by": ["A"], "quote_variants": ["text one"],
                "failure_reason": None, "usable_in_canonical_stage5": True,
            },
            {
                "verification_status": VERIFIED, "start_char": 30, "end_char": 40,
                "span_text": "text two", "source_document_hash": "h1", "canonical_text_hash": "h1",
                "span_text_hash": "sh2", "elicited_by": ["A"], "quote_variants": ["text two"],
                "failure_reason": None, "usable_in_canonical_stage5": True,
            },
        ]
        deduped = dedupe_elicited_spans(raw)
        self.assertEqual(len(deduped), 2)

    def test_ambiguous_records_never_merged_by_none_offset(self):
        """Two ambiguous records both have start_char=end_char=None. They
        must NOT collapse into one just because both keys are None."""
        raw = [
            {
                "verification_status": AMBIGUOUS, "start_char": None, "end_char": None,
                "span_text": "dup a", "source_document_hash": "h1", "canonical_text_hash": "h1",
                "span_text_hash": "sh1", "elicited_by": ["A"], "quote_variants": ["dup a"],
                "failure_reason": "ambiguous", "usable_in_canonical_stage5": False,
            },
            {
                "verification_status": AMBIGUOUS, "start_char": None, "end_char": None,
                "span_text": "dup b", "source_document_hash": "h1", "canonical_text_hash": "h1",
                "span_text_hash": "sh2", "elicited_by": ["B"], "quote_variants": ["dup b"],
                "failure_reason": "ambiguous", "usable_in_canonical_stage5": False,
            },
        ]
        deduped = dedupe_elicited_spans(raw)
        self.assertEqual(len(deduped), 2)

    def test_dedupe_source_contains_no_elicited_by_equality_check(self):
        """Code-level check: dedupe_elicited_spans keys strictly on
        (start_char, end_char) — never compares elicited_by for identity."""
        import inspect
        from cam.adapters.lease_review import lease_element_elicitation
        src = inspect.getsource(lease_element_elicitation.dedupe_elicited_spans)
        self.assertNotIn('r["elicited_by"] ==', src)
        self.assertNotIn("elicited_by ==", src)


# ── Verified / ambiguous / unverified semantics unchanged from 423A ─────────────

class TestVerificationSemanticsUnchanged(unittest.TestCase):
    def setUp(self):
        self.source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="semantics-test")
        self.elements = _elements_two()

    def test_unique_quote_verified(self):
        result = {"target_matches": [{"target": "Target 1", "quotes": ["Rent Adjustment Percentage: 3%"]}]}
        raw = resolve_elicited_spans(self.source, self.elements, result)
        self.assertEqual(raw[0]["verification_status"], VERIFIED)

    def test_duplicated_quote_ambiguous(self):
        result = {"target_matches": [{"target": "Target 1",
                                        "quotes": ["Tenant shall maintain commercial general liability insurance."]}]}
        raw = resolve_elicited_spans(self.source, self.elements, result)
        self.assertEqual(raw[0]["verification_status"], AMBIGUOUS)

    def test_invented_quote_unverified(self):
        result = {"target_matches": [{"target": "Target 1", "quotes": ["This text does not appear anywhere."]}]}
        raw = resolve_elicited_spans(self.source, self.elements, result)
        self.assertEqual(raw[0]["verification_status"], UNVERIFIED)

    def test_changed_digit_unverified(self):
        result = {"target_matches": [{"target": "Target 1", "quotes": ["Rent Adjustment Percentage: 4%"]}]}
        raw = resolve_elicited_spans(self.source, self.elements, result)
        self.assertEqual(raw[0]["verification_status"], UNVERIFIED)


# ── Output schema / LP-blind contract ────────────────────────────────────────────

class TestOutputContract(unittest.TestCase):
    def test_well_formed_output_passes(self):
        obj = {"target_matches": [{"target": "Target 1", "quotes": ["text"]}]}
        ok, why = validate_elicitation_output(obj)
        self.assertTrue(ok, why)

    def test_element_id_field_rejected(self):
        obj = {"target_matches": [{"target": "Target 1", "quotes": ["text"], "element_id": "LP-07.x"}]}
        ok, why = validate_elicitation_output(obj)
        self.assertFalse(ok)

    def test_verdict_field_rejected(self):
        obj = {"target_matches": [{"target": "Target 1", "quotes": ["text"], "coverage_verdict": "present"}]}
        ok, why = validate_elicitation_output(obj)
        self.assertFalse(ok)


# ── Element loading sanity ────────────────────────────────────────────────────────

class TestLoadExpectedElements(unittest.TestCase):
    def test_lp07_has_six_elements_including_cam_cap(self):
        elements_by_lp = load_expected_elements_by_lp()
        self.assertIn("LP-07", elements_by_lp)
        ids = [e["element_id"] for e in elements_by_lp["LP-07"]["elements"]]
        self.assertIn("LP-07.cam_cap", ids)
        self.assertEqual(len(ids), 6)

    def test_all_returned_lps_have_nonempty_elements(self):
        elements_by_lp = load_expected_elements_by_lp()
        self.assertGreater(len(elements_by_lp), 0)
        for lp_id, entry in elements_by_lp.items():
            self.assertGreater(len(entry["elements"]), 0, f"{lp_id} has no elements")


# ── Segmentation-call integrity (mirrors 423B, same doctrine) ───────────────────

def _health_mock():
    h = MagicMock()
    h.is_available.return_value = True
    return h


def _valid_raw_response(n_targets=2):
    return json.dumps({
        "target_matches": [
            {"target": f"Target {i}", "quotes": []} for i in range(1, n_targets + 1)
        ]
    })


class TestElicitationCallIntegrity(unittest.TestCase):
    def test_declared_params_transmitted_and_checked(self):
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
            result = elicit_spans_for_targets(SAMPLE_LEASE_TEXT, _elements_two(), canonical=True)

        integrity = result["meta"]["integrity_metadata"]
        self.assertIsNotNone(integrity)
        self.assertEqual(integrity["transmitted"]["temperature"], 0.0)
        self.assertIn("max_tokens", integrity["transmitted"])

    def test_canonical_flag_recorded_explicitly_on_success(self):
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
            result = elicit_spans_for_targets(SAMPLE_LEASE_TEXT, _elements_two(), canonical=True)
        self.assertIn("canonical", result["meta"])
        self.assertTrue(result["meta"]["canonical"])

    def test_canonical_flag_never_inferred_from_fallback_used(self):
        """422D bug class: fallback_used is False (no fallback provider
        exists) AND canonical is False (degraded/debug) AND the primary
        failed. canonical must read explicitly False, not be conflated
        with the also-False fallback_used."""
        adapter_mock = MagicMock()
        adapter_mock.call.side_effect = Exception("model unavailable")
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
            result = elicit_spans_for_targets(SAMPLE_LEASE_TEXT, _elements_two(), canonical=False)

        self.assertIn("canonical", result["meta"])
        self.assertFalse(result["meta"]["canonical"])
        self.assertFalse(result["meta"]["fallback_used"])
        self.assertTrue(result["meta"]["degraded"])

    def test_canonical_primary_failure_raises_elicitation_integrity_error(self):
        adapter_mock = MagicMock()
        adapter_mock.call.side_effect = Exception("model unavailable")
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
            with self.assertRaises(ElicitationIntegrityError):
                elicit_spans_for_targets(SAMPLE_LEASE_TEXT, _elements_two(), canonical=True)

    def test_fallback_fields_visible_in_metadata(self):
        adapter_mock = MagicMock()
        adapter_mock.call.return_value = _valid_raw_response()
        with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
             patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
            result = elicit_spans_for_targets(SAMPLE_LEASE_TEXT, _elements_two(), canonical=True)
        self.assertIn("fallback_used", result["meta"])
        self.assertIn("fallback_chain", result["meta"])
        self.assertEqual(result["meta"]["fallback_chain"], [])


# ── Sidecar metadata ──────────────────────────────────────────────────────────────

class TestSidecarMetadata(unittest.TestCase):
    def test_sidecar_contains_dedup_stats_and_batching_note(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="sidecar-test")
        elements = _elements_two()
        result = {"target_matches": [{"target": "Target 1", "quotes": ["Rent Adjustment Percentage: 3%"]},
                                       {"target": "Target 2", "quotes": ["Rent Adjustment Percentage: 3%"]}],
                  "meta": {"canonical": True, "fallback_used": False, "fallback_chain": [], "degraded": False}}
        raw = resolve_elicited_spans(source, elements, result)
        deduped = dedupe_elicited_spans(raw)
        sidecar = build_elicitation_sidecar(source, {"LP-TEST": result}, deduped, len(raw))

        self.assertEqual(sidecar["raw_elicited_span_count"], 2)
        self.assertEqual(sidecar["deduped_span_count"], 1)
        self.assertIn("dedup_ratio", sidecar)
        self.assertIn("batching", sidecar)
        self.assertTrue(sidecar["elicited_by_is_provenance_not_routing"])
        json.dumps(sidecar)  # must be JSON-serializable


# ── Pipeline seam ──────────────────────────────────────────────────────────────────

class TestPipelineSeam(unittest.TestCase):
    def test_no_live_pipeline_file_imports_elicitation_module(self):
        import inspect
        from cam.adapters.lease_review import lease_adapter, lease_extract, lease_coverage

        for mod in (lease_adapter, lease_extract, lease_coverage):
            src = inspect.getsource(mod)
            self.assertNotIn("lease_element_elicitation", src)

    def test_evidence_spans_module_not_modified_by_this_slice(self):
        """423C must not touch lease_evidence_spans.py — confirmed by import
        direction: it depends on lease_evidence_spans, never the reverse,
        and its source contains no reference to this new module."""
        import inspect
        from cam.adapters.lease_review import lease_evidence_spans
        src = inspect.getsource(lease_evidence_spans)
        self.assertNotIn("lease_element_elicitation", src)

    def test_no_live_pipeline_file_reads_the_sidecar_artifact(self):
        import inspect
        from cam.adapters.lease_review import lease_adapter, lease_extract, lease_coverage
        for mod in (lease_adapter, lease_extract, lease_coverage):
            src = inspect.getsource(mod)
            self.assertNotIn("423C_", src)


if __name__ == "__main__":
    unittest.main()
