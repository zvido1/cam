"""
Step 425 — Canonical source normalization v2 tests.

Covers: page-number-line stripping (narrow, testable), the v2 matching
profile's punctuation/quote-mark whitespace tolerance, the invariant that
canonical_text is never rewritten for anything but page-number lines, the
non-negotiable refusal of substantive differences (45.79% vs 45.80%), and
hash-drift invalidation across v1/v2 of the same document.
"""

import unittest

from cam.adapters.lease_review.lease_evidence_spans import (
    NORMALIZATION_PROFILE_V1,
    NORMALIZATION_PROFILE_V2,
    VERIFIED,
    AMBIGUOUS,
    UNVERIFIED,
    build_canonical_source,
    normalize,
    resolve_span,
    validate_span_against_source,
    _strip_page_number_lines,
)


# Real text from the Atreca fixture (05 Lease Analyzer/test_data/tenants/
# atreca_eastjamie_southsf_lease.txt) — the exact page-number-artifact case
# that produced 0/5 recall on the Operating Expense exclusions list in 424.
EXCLUSIONS_LIST_FIXTURE = (
    "Landlord shall furnish an itemized statement of Operating Expenses "
    "excluding only:\n"
    "(a) the original construction costs of the Project and renovation "
    "prior to the date of this Lease and costs of correcting defects in "
    "such original construction or renovation;\n"
    "4\n"
    "(b) capital expenditures for expansion of the Project;\n"
    "(c) interest, principal payments of Mortgage debts of Landlord.\n"
)

# The exact quote a model would faithfully produce, quoting straight
# through the page break as if it weren't there (no ellipsis, no elision —
# this is what 424 observed: the model quoted it correctly; the resolver
# correctly refused because the "4" is not whitespace).
EXCLUSIONS_LIST_QUOTE = (
    "(a) the original construction costs of the Project and renovation "
    "prior to the date of this Lease and costs of correcting defects in "
    "such original construction or renovation;\n"
    "(b) capital expenditures for expansion of the Project;"
)


# ── Test 1: page-number line stripped; exclusions-list quote now resolves ──────

class TestPageNumberStripResolvesExclusionsList(unittest.TestCase):
    def test_unverified_under_v1(self):
        source_v1 = build_canonical_source(
            EXCLUSIONS_LIST_FIXTURE, run_id="425-v1", normalization_profile=NORMALIZATION_PROFILE_V1
        )
        span = resolve_span(source_v1, EXCLUSIONS_LIST_QUOTE, "EV-425-1")
        self.assertEqual(span.verification_status, UNVERIFIED, "v1 must still fail — this is the 424 finding")

    def test_verified_under_v2(self):
        source_v2 = build_canonical_source(
            EXCLUSIONS_LIST_FIXTURE, run_id="425-v2", normalization_profile=NORMALIZATION_PROFILE_V2
        )
        span = resolve_span(source_v2, EXCLUSIONS_LIST_QUOTE, "EV-425-2")
        self.assertEqual(span.verification_status, VERIFIED, "v2 must resolve this — the page-number strip is the fix")
        self.assertTrue(span.is_valid_invariant(source_v2))

    def test_stripped_text_has_page_number_removed(self):
        source_v2 = build_canonical_source(
            EXCLUSIONS_LIST_FIXTURE, run_id="425-v2b", normalization_profile=NORMALIZATION_PROFILE_V2
        )
        self.assertNotIn("\n4\n", source_v2.canonical_text)
        self.assertEqual(source_v2.page_number_lines_stripped, 1)


# ── Test 2: digit-adjacent-to-content lines must survive ───────────────────────

class TestNarrowStripRule(unittest.TestCase):
    SURVIVORS = [
        "Section 4",
        "4. Operating Expenses",
        "(4)",
        "4%",
        "$4",
        "4 days",
        "Page 4 of 20",
    ]

    def test_all_survivors_kept_verbatim(self):
        for line in self.SURVIVORS:
            text = f"Some text before.\n{line}\nSome text after.\n"
            stripped, count = _strip_page_number_lines(text)
            self.assertEqual(count, 0, f"{line!r} must not be stripped")
            self.assertEqual(stripped, text, f"{line!r} line must be byte-identical")
            self.assertIn(line, stripped)

    def test_bare_digit_line_is_stripped(self):
        text = "before.\n4\nafter.\n"
        stripped, count = _strip_page_number_lines(text)
        self.assertEqual(count, 1)
        self.assertEqual(stripped, "before.\nafter.\n")

    def test_whitespace_padded_digit_line_is_stripped(self):
        text = "before.\n 12 \nafter.\n"
        stripped, count = _strip_page_number_lines(text)
        self.assertEqual(count, 1)
        self.assertEqual(stripped, "before.\nafter.\n")

    def test_multiple_bare_digit_lines_all_stripped(self):
        text = "one.\n4\ntwo.\n5\nthree.\n"
        stripped, count = _strip_page_number_lines(text)
        self.assertEqual(count, 2)
        self.assertEqual(stripped, "one.\ntwo.\nthree.\n")

    def test_mixed_survivors_and_strips_in_one_document(self):
        text = (
            "Intro.\n"
            "4\n"
            "Section 4 discusses rent.\n"
            "12\n"
            "The cap is 4% and the fee is $4.\n"
            "(4) is a subsection.\n"
            "Tenant has 4 days to respond.\n"
            "Page 4 of 20\n"
            "7\n"
            "End.\n"
        )
        stripped, count = _strip_page_number_lines(text)
        self.assertEqual(count, 3)  # the "4", the "12", and the "7"
        for survivor in ("Section 4 discusses rent.", "The cap is 4% and the fee is $4.",
                          "(4) is a subsection.", "Tenant has 4 days to respond.", "Page 4 of 20"):
            self.assertIn(survivor, stripped)
        self.assertNotIn("\n4\n", stripped)
        self.assertNotIn("\n12\n", stripped)
        self.assertNotIn("\n7\n", stripped)


# ── Test 3: canonical text unchanged except for stripped page lines ────────────

class TestCanonicalTextByteIdenticalExceptPageLines(unittest.TestCase):
    def test_v2_canonical_text_equals_raw_minus_page_lines_only(self):
        source_v2 = build_canonical_source(
            EXCLUSIONS_LIST_FIXTURE, run_id="425-byte-check", normalization_profile=NORMALIZATION_PROFILE_V2
        )
        expected, _ = _strip_page_number_lines(EXCLUSIONS_LIST_FIXTURE)
        self.assertEqual(source_v2.canonical_text, expected)
        # raw_source_text is preserved completely untouched
        self.assertEqual(source_v2.raw_source_text, EXCLUSIONS_LIST_FIXTURE)

    def test_punctuation_and_quote_spacing_never_rewritten_in_text(self):
        """The ugly source spacing (space before punctuation, space inside
        quote marks) is genuinely in the document — it must survive in
        canonical_text untouched. Only matching tolerates it; the text
        itself is never edited for this reason."""
        text_with_spacing = (
            'Without Landlord\'s prior written consent subject to and on the '
            'conditions described in this Section 22 , Tenant shall not '
            'assign (an " Assignment Termination ").\n'
        )
        source_v2 = build_canonical_source(
            text_with_spacing, run_id="425-spacing-check", normalization_profile=NORMALIZATION_PROFILE_V2
        )
        self.assertIn("Section 22 , Tenant", source_v2.canonical_text)
        self.assertIn('" Assignment Termination "', source_v2.canonical_text)
        self.assertEqual(source_v2.canonical_text, text_with_spacing)


# ── Test 4: matching tolerates space-before-punctuation and quote-padding ──────

class TestV2MatchingTolerance(unittest.TestCase):
    def test_space_before_punctuation_tolerated(self):
        text = 'Without consent described in this Section 22 , Tenant shall not assign.\n'
        source = build_canonical_source(text, run_id="425-punct", normalization_profile=NORMALIZATION_PROFILE_V2)
        quote = "described in this Section 22, Tenant shall not assign."
        span = resolve_span(source, quote, "EV-425-punct")
        self.assertEqual(span.verification_status, VERIFIED)
        self.assertTrue(span.is_valid_invariant(source))

    def test_space_before_punctuation_unverified_under_v1(self):
        text = 'Without consent described in this Section 22 , Tenant shall not assign.\n'
        source = build_canonical_source(text, run_id="425-punct-v1", normalization_profile=NORMALIZATION_PROFILE_V1)
        quote = "described in this Section 22, Tenant shall not assign."
        span = resolve_span(source, quote, "EV-425-punct-v1")
        self.assertEqual(span.verification_status, UNVERIFIED)

    def test_quote_mark_padding_tolerated(self):
        text = 'Landlord\'s consent to (a " Control Permitted Assignment ") shall not be required.\n'
        source = build_canonical_source(text, run_id="425-quote", normalization_profile=NORMALIZATION_PROFILE_V2)
        quote = 'Landlord\'s consent to (a "Control Permitted Assignment") shall not be required.'
        span = resolve_span(source, quote, "EV-425-quote")
        self.assertEqual(span.verification_status, VERIFIED)
        self.assertTrue(span.is_valid_invariant(source))

    def test_quote_mark_padding_unverified_under_v1(self):
        text = 'Landlord\'s consent to (a " Control Permitted Assignment ") shall not be required.\n'
        source = build_canonical_source(text, run_id="425-quote-v1", normalization_profile=NORMALIZATION_PROFILE_V1)
        quote = 'Landlord\'s consent to (a "Control Permitted Assignment") shall not be required.'
        span = resolve_span(source, quote, "EV-425-quote-v1")
        self.assertEqual(span.verification_status, UNVERIFIED)


# ── Test 5: 45.79% vs 45.80% — non-negotiable, both profiles ────────────────────

class TestSubstantiveDifferenceNeverTolerated(unittest.TestCase):
    def test_v2_still_refuses_changed_digit(self):
        text = "Building's Share of Project Operating Expenses: 45.79%\n"
        source = build_canonical_source(text, run_id="425-digit", normalization_profile=NORMALIZATION_PROFILE_V2)
        quote = "Building's Share of Project Operating Expenses: 45.80%"
        span = resolve_span(source, quote, "EV-425-digit")
        self.assertEqual(span.verification_status, UNVERIFIED)

    def test_v2_normalize_does_not_mask_digit_change(self):
        self.assertNotEqual(
            normalize("45.79%", NORMALIZATION_PROFILE_V2),
            normalize("45.80%", NORMALIZATION_PROFILE_V2),
        )

    def test_v2_normalize_does_not_mask_word_change(self):
        self.assertNotEqual(
            normalize("Landlord shall repair the roof.", NORMALIZATION_PROFILE_V2),
            normalize("Tenant shall repair the roof.", NORMALIZATION_PROFILE_V2),
        )

    def test_punctuation_tolerance_does_not_bridge_a_real_gap(self):
        """A quote missing an entire clause must not spuriously match just
        because \\s* is permissive around punctuation."""
        text = "Rent Adjustment Percentage: 3%, subject to annual review.\n"
        source = build_canonical_source(text, run_id="425-gap", normalization_profile=NORMALIZATION_PROFILE_V2)
        quote = "Rent Adjustment Percentage: 3%, subject to biennial review."
        span = resolve_span(source, quote, "EV-425-gap")
        self.assertEqual(span.verification_status, UNVERIFIED)


# ── Test 6: hash drift — v1-resolved span invalid against v2 ────────────────────

class TestHashDriftAcrossProfiles(unittest.TestCase):
    def test_span_resolved_against_v1_invalid_against_v2(self):
        # Fixture MUST contain a page-number line so v1/v2 canonical_text
        # genuinely differ — otherwise there is nothing for v2 to strip and
        # the hashes are (correctly) identical, which is a different test.
        text = "Intro.\n4\nRent Adjustment Percentage: 3%\n"
        source_v1 = build_canonical_source(text, run_id="425-hd-v1", normalization_profile=NORMALIZATION_PROFILE_V1)
        span = resolve_span(source_v1, "Rent Adjustment Percentage: 3%", "EV-425-hd")
        self.assertEqual(span.verification_status, VERIFIED)

        source_v2 = build_canonical_source(text, run_id="425-hd-v2", normalization_profile=NORMALIZATION_PROFILE_V2)
        self.assertNotEqual(source_v1.canonical_text_hash, source_v2.canonical_text_hash)
        self.assertFalse(validate_span_against_source(span, source_v2))
        self.assertFalse(span.is_valid_invariant(source_v2))

    def test_v1_and_v2_hashes_differ_when_page_lines_present(self):
        source_v1 = build_canonical_source(
            EXCLUSIONS_LIST_FIXTURE, run_id="425-hashcheck-v1", normalization_profile=NORMALIZATION_PROFILE_V1
        )
        source_v2 = build_canonical_source(
            EXCLUSIONS_LIST_FIXTURE, run_id="425-hashcheck-v2", normalization_profile=NORMALIZATION_PROFILE_V2
        )
        self.assertNotEqual(source_v1.canonical_text_hash, source_v2.canonical_text_hash)
        self.assertNotEqual(source_v1.source_document_hash, source_v2.source_document_hash)
        # raw_source_text_hash is identical regardless of profile — same underlying document.
        self.assertEqual(source_v1.raw_source_text_hash, source_v2.raw_source_text_hash)

    def test_v1_hashes_equal_raw_hash_when_no_page_lines(self):
        """When there's nothing to strip, v1 behavior is provably unchanged:
        canonical_text_hash == raw_source_text_hash."""
        text = "No page numbers in this text at all.\n"
        source_v1 = build_canonical_source(text, run_id="425-nopage", normalization_profile=NORMALIZATION_PROFILE_V1)
        self.assertEqual(source_v1.canonical_text_hash, source_v1.raw_source_text_hash)
        self.assertEqual(source_v1.page_number_lines_stripped, 0)


# ── Backward compatibility: v1 default behavior provably unchanged ─────────────

class TestV1BackwardCompatibility(unittest.TestCase):
    def test_default_profile_is_still_v1(self):
        source = build_canonical_source("Some lease text.\n4\nMore text.\n", run_id="425-default")
        self.assertEqual(source.normalization_profile, NORMALIZATION_PROFILE_V1)
        # v1 never strips — page-number line survives untouched.
        self.assertIn("\n4\n", source.canonical_text)
        self.assertEqual(source.page_number_lines_stripped, 0)
        self.assertEqual(source.canonical_text, source.raw_source_text)


if __name__ == "__main__":
    unittest.main()
