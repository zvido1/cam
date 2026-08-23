"""
Step 423A — Verified evidence-span substrate tests.

Covers: canonical source construction, span resolution (verified / ambiguous /
unverified), anchor disambiguation, normalization-profile behavior, hash-drift
invalidation, and the seam proving this module is standalone (not wired into
the live Mode C / Stage 5 pipeline).
"""

import unittest

from cam.adapters.lease_review.lease_evidence_spans import (
    CanonicalSource,
    EvidenceSpan,
    NORMALIZATION_PROFILE_V1,
    VERIFIED,
    AMBIGUOUS,
    UNVERIFIED,
    build_canonical_source,
    is_usable_in_canonical_stage5,
    normalize,
    resolve_span,
    resolve_spans,
    validate_span_against_source,
)


SAMPLE_LEASE_TEXT = (
    "ARTICLE 1 - BASIC LEASE INFORMATION\n"
    "This Lease is entered into between Landlord and Tenant.\n\n"
    "Tenant's Share of Operating Expenses of Building: 100%\n"
    "Building's Share of Project Operating Expenses: 45.79%\n"
    "Rent Adjustment Percentage: 3%\n\n"
    "ARTICLE 2 - PREMISES\n"
    "Landlord leases to Tenant the Premises described in Exhibit A.\n\n"
    "ARTICLE 3 - TERM\n"
    "The term of this Lease shall commence on the Commencement Date.\n"
)


# ── Test 1: unique quote → verified; slice equals span_text ───────────────────

class TestUniqueQuoteVerified(unittest.TestCase):
    def test_unique_quote_resolves_verified(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="test-run-1")
        quote = "Tenant's Share of Operating Expenses of Building: 100%"
        span = resolve_span(source, quote, "EV-000001")

        self.assertEqual(span.verification_status, VERIFIED)
        self.assertIsNotNone(span.start_char)
        self.assertIsNotNone(span.end_char)
        slice_text = source.canonical_text[span.start_char:span.end_char]
        self.assertEqual(slice_text, span.span_text)
        self.assertTrue(span.is_valid_invariant(source))

    def test_unique_quote_usable_in_canonical_stage5(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="test-run-1")
        span = resolve_span(source, "ARTICLE 2 - PREMISES", "EV-000002")
        self.assertTrue(is_usable_in_canonical_stage5(span))


# ── Test 2: absent quote → unverified; canonical use fails closed ─────────────

class TestAbsentQuoteUnverified(unittest.TestCase):
    def test_absent_quote_resolves_unverified(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="test-run-1")
        quote = "This exact sentence does not appear anywhere in the lease."
        span = resolve_span(source, quote, "EV-000003")

        self.assertEqual(span.verification_status, UNVERIFIED)
        self.assertIsNone(span.start_char)
        self.assertIsNone(span.end_char)

    def test_unverified_span_fails_closed_for_canonical_use(self):
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="test-run-1")
        span = resolve_span(source, "not in the document at all", "EV-000004")
        self.assertFalse(is_usable_in_canonical_stage5(span))
        self.assertFalse(span.is_valid_invariant(source))


# ── Test 3: duplicated quote → ambiguous; no silent acceptance ────────────────

class TestDuplicatedQuoteAmbiguous(unittest.TestCase):
    DUPLICATE_TEXT = (
        "SECTION A. Tenant shall maintain insurance in commercially reasonable amounts.\n\n"
        "SECTION B. Landlord's obligations are separately stated.\n\n"
        "SECTION C. Tenant shall maintain insurance in commercially reasonable amounts.\n"
    )

    def test_duplicate_quote_no_anchor_is_ambiguous(self):
        source = build_canonical_source(self.DUPLICATE_TEXT, run_id="test-run-2")
        quote = "Tenant shall maintain insurance in commercially reasonable amounts."
        span = resolve_span(source, quote, "EV-000005")

        self.assertEqual(span.verification_status, AMBIGUOUS)
        self.assertIsNone(span.start_char)
        self.assertIsNone(span.end_char)
        self.assertFalse(is_usable_in_canonical_stage5(span))

    def test_ambiguous_span_never_silently_verified(self):
        source = build_canonical_source(self.DUPLICATE_TEXT, run_id="test-run-2")
        quote = "Tenant shall maintain insurance in commercially reasonable amounts."
        # No anchor supplied at all — must not guess.
        span = resolve_span(source, quote, "EV-000006")
        self.assertNotEqual(span.verification_status, VERIFIED)


# ── Test 4: anchor disambiguation → duplicate + source_anchor → verified ──────

class TestAnchorDisambiguation(unittest.TestCase):
    DUPLICATE_TEXT = (
        "SECTION A. Tenant shall maintain insurance in commercially reasonable amounts.\n\n"
        "SECTION B. Landlord's obligations are separately stated.\n\n"
        "SECTION C. Tenant shall maintain insurance in commercially reasonable amounts.\n"
    )

    def test_source_anchor_resolves_duplicate_to_verified(self):
        source = build_canonical_source(self.DUPLICATE_TEXT, run_id="test-run-2")
        quote = "Tenant shall maintain insurance in commercially reasonable amounts."
        span = resolve_span(
            source, quote, "EV-000007", source_anchor="SECTION C."
        )

        self.assertEqual(span.verification_status, VERIFIED)
        self.assertIsNotNone(span.start_char)
        slice_text = source.canonical_text[span.start_char:span.end_char]
        self.assertEqual(slice_text, quote)
        # The resolved location must be the SECTION C occurrence, not SECTION A.
        self.assertGreater(span.start_char, self.DUPLICATE_TEXT.index("SECTION C."))

    def test_ambiguous_anchor_still_ambiguous_if_it_matches_both(self):
        source = build_canonical_source(self.DUPLICATE_TEXT, run_id="test-run-2")
        quote = "Tenant shall maintain insurance in commercially reasonable amounts."
        # "SECTION" alone doesn't disambiguate — appears before both occurrences.
        span = resolve_span(source, quote, "EV-000008", source_anchor="SECTION")
        self.assertEqual(span.verification_status, AMBIGUOUS)


# ── Test 5: normalization profile behaves as declared ─────────────────────────

class TestNormalizationProfile(unittest.TestCase):
    def test_whitespace_only_differences_normalize_equal(self):
        a = "Tenant's   Share:  100%"
        b = "Tenant's Share: 100%"
        self.assertEqual(normalize(a), normalize(b))

    def test_reflowed_newlines_normalize_equal(self):
        a = "Tenant's Share\nof Operating\n  Expenses: 100%"
        b = "Tenant's Share of Operating Expenses: 100%"
        self.assertEqual(normalize(a), normalize(b))

    def test_substantive_difference_not_masked(self):
        a = "Tenant's Share of Operating Expenses: 100%"
        b = "Tenant's Share of Operating Expenses: 45.79%"
        self.assertNotEqual(normalize(a), normalize(b))

    def test_substantive_word_difference_not_masked(self):
        a = "Landlord shall repair the roof."
        b = "Tenant shall repair the roof."
        self.assertNotEqual(normalize(a), normalize(b))

    def test_reflowed_quote_still_resolves_verified_without_masking_substance(self):
        # Model reflows whitespace but copies the substance verbatim -> verified.
        source = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="test-run-1")
        reflowed_quote = "Tenant's Share of Operating\n  Expenses of Building: 100%"
        span = resolve_span(source, reflowed_quote, "EV-000009")
        self.assertEqual(span.verification_status, VERIFIED)
        self.assertTrue(span.is_valid_invariant(source))

        # But a quote that changes the substantive figure must NOT resolve.
        wrong_quote = "Tenant's Share of Operating\n  Expenses of Building: 45.79%"
        span2 = resolve_span(source, wrong_quote, "EV-000010")
        self.assertEqual(span2.verification_status, UNVERIFIED)


# ── Test 6: hash drift → source hash mismatch invalidates spans ───────────────

class TestHashDriftInvalidation(unittest.TestCase):
    def test_span_invalid_against_different_source(self):
        source_a = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="run-a")
        span = resolve_span(source_a, "ARTICLE 2 - PREMISES", "EV-000011")
        self.assertEqual(span.verification_status, VERIFIED)

        # Different text -> different hash, even though it happens to be
        # a variant of the same document.
        drifted_text = SAMPLE_LEASE_TEXT + "\nARTICLE 4 - ADDED LATER\n"
        source_b = build_canonical_source(drifted_text, run_id="run-b")

        self.assertNotEqual(source_a.source_document_hash, source_b.source_document_hash)
        self.assertFalse(validate_span_against_source(span, source_b))
        self.assertFalse(span.is_valid_invariant(source_b))

    def test_span_still_valid_against_its_own_source(self):
        source_a = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="run-a")
        span = resolve_span(source_a, "ARTICLE 2 - PREMISES", "EV-000012")
        self.assertTrue(validate_span_against_source(span, source_a))

    def test_hash_mismatch_is_never_silently_re_resolved(self):
        """validate_span_against_source only compares hashes; it must not
        attempt to re-locate the span in the new source."""
        source_a = build_canonical_source(SAMPLE_LEASE_TEXT, run_id="run-a")
        span = resolve_span(source_a, "ARTICLE 3 - TERM", "EV-000013")
        original_start, original_end = span.start_char, span.end_char

        source_b = build_canonical_source("completely different document text", run_id="run-b")
        result = validate_span_against_source(span, source_b)

        self.assertFalse(result)
        # Span object itself is untouched — no silent re-resolution occurred.
        self.assertEqual(span.start_char, original_start)
        self.assertEqual(span.end_char, original_end)
        self.assertEqual(span.source_document_hash, source_a.source_document_hash)


# ── Test 7: seam — span layer produced/inspectable; Stage 5 unchanged ─────────

class TestSeamStandaloneAndUninvasive(unittest.TestCase):
    def test_span_layer_is_produced_and_inspectable(self):
        """Exercise the module end-to-end on realistic lease text: build a
        canonical source, propose several quotes, resolve them, and confirm
        the result is a structured, inspectable span universe."""
        source = build_canonical_source(SAMPLE_LEASE_TEXT, source_type="lease_tenant_document", run_id="seam-test")
        proposals = [
            {"quote": "Tenant's Share of Operating Expenses of Building: 100%"},
            {"quote": "Building's Share of Project Operating Expenses: 45.79%"},
            {"quote": "Rent Adjustment Percentage: 3%"},
            {"quote": "This text is not in the lease at all."},
        ]
        spans = resolve_spans(source, proposals)

        self.assertEqual(len(spans), 4)
        self.assertTrue(all(isinstance(s, EvidenceSpan) for s in spans))
        statuses = [s.verification_status for s in spans]
        self.assertEqual(statuses.count(VERIFIED), 3)
        self.assertEqual(statuses.count(UNVERIFIED), 1)
        # Inspectable: every field is a plain value, not an opaque object.
        for s in spans:
            self.assertIsInstance(s.evidence_span_id, str)
            self.assertIsInstance(s.source_document_hash, str)
            self.assertIsInstance(s.span_text_hash, str)
            self.assertIn(s.verification_status, {VERIFIED, AMBIGUOUS, UNVERIFIED})

    def test_only_the_seam_imports_the_span_substrate(self):
        """RETIRED AND REWRITTEN, Step 461. See build_log/461_chat_instruction.md.

        The predecessor asserted that lease_adapter, lease_extract AND
        lease_coverage all contain no reference to this module. That encoded a
        *not-yet-connected precondition*, correct while 423A was a standalone
        slice, and it stopped being true the moment the seam was wired
        (Step 458, commit 134998b) -- the stack now has a production caller by
        design.

        It was never a direction constraint. Direction is asserted by
        test_no_lp_taxonomy_leakage_into_span_resolution and, in the 423C
        suite, test_evidence_spans_module_not_modified_by_this_slice; both are
        untouched and still pass.

        What current doctrine actually requires is narrower: the SEAM, and only
        the seam, reaches the span substrate.
          - lease_adapter and lease_extract must not reference it at all.
          - lease_coverage may, but every reference must sit inside
            _assemble_span_evidence. A reference anywhere else in that module
            would mean a second, unreviewed entry point.

        Setting SPAN_EVIDENCE_LPS empty, or rolling the seam back entirely,
        leaves this test passing -- it constrains where the coupling may live,
        not whether it exists.
        """
        import inspect
        from cam.adapters.lease_review import lease_adapter, lease_extract, lease_coverage

        for mod in (lease_adapter, lease_extract):
            self.assertNotIn(
                "lease_evidence_spans", inspect.getsource(mod),
                f"{mod.__name__} must not reference lease_evidence_spans -- "
                "the seam belongs in lease_coverage._assemble_span_evidence",
            )

        module_src = inspect.getsource(lease_coverage)
        seam_src = inspect.getsource(lease_coverage._assemble_span_evidence)
        self.assertEqual(
            module_src.count("lease_evidence_spans"),
            seam_src.count("lease_evidence_spans"),
            "every lease_evidence_spans reference in lease_coverage must be inside "
            "_assemble_span_evidence; one outside means a second entry point",
        )

    def test_no_lp_taxonomy_leakage_into_span_resolution(self):
        """Doctrine check: span resolution takes no LP id, no provision
        list, no taxonomy of any kind — only canonical source + quote."""
        import inspect
        sig = inspect.signature(resolve_span)
        param_names = set(sig.parameters.keys())
        for forbidden in ("provision_id", "lp_id", "provisions", "lp"):
            self.assertNotIn(forbidden, param_names)


if __name__ == "__main__":
    unittest.main()
