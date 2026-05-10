"""
Regression fixture for the six literal-marker detectors in lease_negative_space.py.
Step 305b — 2026-05-10.

Covers: reserved_or_omitted, broken_xref, missing_exhibit, blank_placeholder,
        truncated_list, undefined_term.

Three cases per detector: positive (fires), negative (clean), boundary (documented).

Run from 05 Lease Analyzer/:
    python -m pytest tests/test_negative_space_detectors.py -v
"""
import pytest
from cam.adapters.lease_review.lease_negative_space import detect_negative_space


# ── Helpers ────────────────────────────────────────────────────────────────────

def run(tenant_text: str, full_text: str = "", pid: str = "LP-T") -> list:
    """Run detect_negative_space on a single synthetic provision and return signals."""
    provision = {
        "provision_id": pid,
        "provision_name": "Test Provision",
        "tenant_text": tenant_text,
        "template_text": "",
    }
    results = detect_negative_space([provision], full_text)
    return results.get(pid, [])


def of_type(signals: list, signal_type: str) -> list:
    return [s for s in signals if s["signal_type"] == signal_type]


# ── 1. reserved_or_omitted ─────────────────────────────────────────────────────
#
# Pattern: \b(intentionally omitted|intentionally left blank|reserved|
#           this section intentionally|omitted intentionally)\b  IGNORECASE
# Entry: detect_negative_space → checks tenant_text via _RESERVED_PATTERN.search
# Return: signal with severity="high", evidence=matched text

class TestReservedOrOmitted:
    def test_positive_reserved_heading(self):
        sigs = run("Section 12. RESERVED.")
        hits = of_type(sigs, "reserved_or_omitted")
        assert hits, "Expected reserved_or_omitted signal for 'RESERVED'"
        assert hits[0]["severity"] == "high"
        assert "RESERVED" in hits[0]["evidence"].upper()

    def test_positive_intentionally_omitted(self):
        sigs = run("[Intentionally Omitted]")
        hits = of_type(sigs, "reserved_or_omitted")
        assert hits, "Expected reserved_or_omitted signal for 'Intentionally Omitted'"

    def test_negative_rent_escalation_clause(self):
        text = (
            "Base rent shall escalate by 3% annually on each anniversary of the "
            "Commencement Date, as set forth in Exhibit A."
        )
        sigs = run(text)
        assert not of_type(sigs, "reserved_or_omitted")

    def test_boundary_reserves_not_reserved(self):
        # "reserves" is NOT the word "reserved" — the word-boundary regex matches
        # the literal token "reserved", not inflected forms like "reserves".
        # BEHAVIORAL NOTE: "Landlord reserves the right" does NOT fire.
        text = "Landlord reserves the right to approve any proposed subtenant."
        sigs = run(text)
        assert not of_type(sigs, "reserved_or_omitted"), (
            "Boundary: 'reserves' (verb) should not match the 'reserved' pattern"
        )


# ── 2. broken_xref ─────────────────────────────────────────────────────────────
#
# Pattern: _SECTION_REF_PATTERN extracts section refs from tenant_text;
#          _extract_section_headers extracts actual headers from full_tenant_text.
#          Fires if ref exists in tenant_text but NOT in doc headers, AND
#          _is_meaningful_ref returns True.
# _is_meaningful_ref: suppresses single-digit refs AND refs with first part > 50.
# Entry: detect_negative_space
# Return: signal with severity="high", evidence="Section <ref>"

class TestBrokenXref:
    def test_positive_missing_section(self):
        # Section 22.4 referenced but document only has 9.1
        full_text = "\n9.1 Landlord Maintenance. Landlord shall maintain the roof.\n"
        sigs = run("Default remedies per Section 22.4.", full_text)
        hits = of_type(sigs, "broken_xref")
        assert hits, "Expected broken_xref for Section 22.4 missing from document"
        assert any("22.4" in h["evidence"] for h in hits)

    def test_negative_section_exists(self):
        # Section 9.1 is referenced and also present as a header
        full_text = "\n9.1 Landlord Maintenance. Landlord shall maintain the roof.\n"
        sigs = run("Landlord obligations per Section 9.1.", full_text)
        assert not of_type(sigs, "broken_xref"), (
            "Section 9.1 exists in full_text — should not fire"
        )

    def test_boundary_high_section_number_suppressed(self):
        # Section 1951.2 of California Civil Code: first part 1951 > 50.
        # _is_meaningful_ref returns False → signal suppressed.
        # BEHAVIORAL NOTE: External statutory references are silently dropped.
        full_text = ""
        sigs = run(
            "Remedies available pursuant to Section 1951.2 of the California Civil Code.",
            full_text,
        )
        hits = of_type(sigs, "broken_xref")
        assert not hits, (
            "Boundary: Section 1951.2 should be suppressed by _is_meaningful_ref "
            "(first part 1951 > 50). External statutory cites do NOT fire."
        )

    def test_boundary_section_99_suppressed(self):
        # Section 99 — first part 99 > 50 → suppressed.
        # BEHAVIORAL NOTE: The instruction's suggested positive example "Section 99"
        # does NOT fire because _is_meaningful_ref filters out first-part > 50.
        sigs = run("See Section 99 for additional terms.", "")
        hits = of_type(sigs, "broken_xref")
        assert not hits, (
            "Boundary: 'Section 99' suppressed by _is_meaningful_ref (99 > 50)"
        )


# ── 3. missing_exhibit ─────────────────────────────────────────────────────────
#
# Pattern: _EXHIBIT_REF_PATTERN extracts labels from tenant_text;
#          _extract_exhibit_labels extracts from full_tenant_text (line-start anchored).
# Fires if exhibit label in tenant_text is NOT present as a header in full_tenant_text.
# Entry: detect_negative_space
# Return: signal with severity="high", evidence="Exhibit <label>"

class TestMissingExhibit:
    def test_positive_exhibit_absent(self):
        full_text = "EXHIBIT A — RENT SCHEDULE\nBase Rent: $8,400/month.\n"
        sigs = run("Rent schedule per Exhibit Z.", full_text)
        hits = of_type(sigs, "missing_exhibit")
        assert hits, "Expected missing_exhibit for Exhibit Z not in document"
        assert any("Z" in h["evidence"] for h in hits)

    def test_negative_exhibit_present(self):
        # Exhibit A referenced AND present as a line-start header.
        # IMPORTANT: avoid the word "schedule" in tenant_text — it is itself a
        # keyword in _EXHIBIT_REF_PATTERN, so "schedule per" would be extracted
        # as a spurious label "PER" (see test_boundary_schedule_keyword_collision).
        full_text = "EXHIBIT A — RENT SCHEDULE\nBase Rent: $8,400/month.\n"
        sigs = run("See Exhibit A for rent amounts.", full_text)
        assert not of_type(sigs, "missing_exhibit"), (
            "Exhibit A is present as a header — should not fire"
        )

    def test_boundary_schedule_keyword_collision(self):
        # Step 305c fix: "schedule" was removed from _EXHIBIT_REF_PATTERN because
        # "rent schedule per Exhibit A" was extracting "PER" as a spurious exhibit
        # label. After the fix, "schedule" in prose does not trigger the pattern.
        # This test now asserts the CORRECT post-fix behavior: no "Exhibit PER" signal.
        # Note: "schedule" is still recognized in _extract_exhibit_labels (line-start
        # anchored) so "SCHEDULE A" document headers are still matched correctly.
        full_text = "EXHIBIT A — RENT SCHEDULE\nBase Rent: $8,400/month.\n"
        sigs = run("Rent schedule per Exhibit A.", full_text)
        per_hits = [s for s in of_type(sigs, "missing_exhibit") if "PER" in s["evidence"]]
        assert not per_hits, (
            "After Step 305c fix: 'schedule per' must NOT produce 'Exhibit PER'. "
            "If this fails, 'schedule' was re-added to _EXHIBIT_REF_PATTERN."
        )
        # Exhibit A itself should not fire because it is present in the corpus
        a_hits = [s for s in of_type(sigs, "missing_exhibit") if "A" in s["evidence"]]
        assert not a_hits, "Exhibit A is in the corpus — should not produce a signal"

    def test_boundary_reference_with_empty_corpus(self):
        # "attached hereto as Exhibit B" with no full_text at all.
        # BEHAVIORAL NOTE: With an empty corpus, _extract_exhibit_labels returns {}
        # so any exhibit reference fires. This is reference-without-corpus behavior.
        sigs = run("The floor plan is attached hereto as Exhibit B.", "")
        hits = of_type(sigs, "missing_exhibit")
        assert hits, (
            "Boundary: empty corpus → Exhibit B not in {} → fires. "
            "Detector fires on any reference when no corpus is provided."
        )


# ── 4. blank_placeholder ───────────────────────────────────────────────────────
#
# Two sub-patterns:
#   _BLANK_DOLLAR_PATTERN: \$\s*(?:_{2,}|\[[\s_]*\]|\[amount\]|\[to be determined\]|tbd\b|0\.00\b)
#   _BLANK_NUMBER_PATTERN: \b(?:_{2,}|\[___+\]|\[number\]|\[to be determined\]|tbd)\s*(?:days?|months?|years?|percent|%)
# Both are IGNORECASE.
# BEHAVIORAL NOTE: A bare "[____]" or "TBD" without a dollar-sign prefix (dollar
# pattern) or a time-unit suffix (number pattern) does NOT fire.

class TestBlankPlaceholder:
    def test_positive_blank_dollar(self):
        sigs = run("Base rent shall be $____ per month.")
        hits = of_type(sigs, "blank_placeholder")
        assert hits, "Expected blank_placeholder for '$____'"

    def test_positive_blank_number_days(self):
        sigs = run("Tenant shall have ___ days to cure any monetary default.")
        hits = of_type(sigs, "blank_placeholder")
        assert hits, "Expected blank_placeholder for '___ days'"

    def test_positive_tbd_days(self):
        sigs = run("The notice period shall be TBD days.")
        hits = of_type(sigs, "blank_placeholder")
        assert hits, "Expected blank_placeholder for 'TBD days'"

    def test_negative_filled_amounts(self):
        text = (
            "Base rent is $8,400 per month. The cure period is 30 days. "
            "The security deposit is $25,200."
        )
        sigs = run(text)
        assert not of_type(sigs, "blank_placeholder")

    def test_boundary_bare_underscores_in_signature_block(self):
        # "___" in a signature block with no dollar prefix and no time unit.
        # BEHAVIORAL NOTE: Does NOT fire because neither sub-pattern matches:
        #   - Dollar pattern requires $ prefix.
        #   - Number pattern requires days/months/years/percent suffix.
        text = "Landlord: _____________  Date: ___\nTenant: _____________   Date: ___"
        sigs = run(text)
        assert not of_type(sigs, "blank_placeholder"), (
            "Boundary: underscores in signature block without $ or time-unit context "
            "do NOT fire."
        )

    def test_boundary_bare_tbd_without_unit(self):
        # "TBD" alone (no time unit suffix) does NOT match _BLANK_NUMBER_PATTERN
        # and has no $ prefix for _BLANK_DOLLAR_PATTERN.
        # BEHAVIORAL NOTE: Standalone "TBD" is not detected.
        sigs = run("The effective date is TBD.")
        assert not of_type(sigs, "blank_placeholder"), (
            "Boundary: 'TBD' without time-unit suffix does NOT fire."
        )


# ── 5. truncated_list ──────────────────────────────────────────────────────────
#
# Pattern: including\s+(?:without\s+limitation|but\s+not\s+limited\s+to)[,\s]*[.;]
# BEHAVIORAL NOTE: This is narrower than "truncated list" suggests. It only fires
# on the specific phrase "including without limitation." or "including but not limited
# to." immediately ending a sentence. Numbered list truncation like "(i) heat, (ii)"
# does NOT fire.

class TestTruncatedList:
    def test_positive_including_without_limitation_period(self):
        sigs = run(
            "Force majeure events include acts of God, including without limitation."
        )
        hits = of_type(sigs, "truncated_list")
        assert hits, (
            "Expected truncated_list for 'including without limitation.' at sentence end"
        )
        assert hits[0]["severity"] == "low"

    def test_positive_including_but_not_limited_to_semicolon(self):
        sigs = run(
            "Operating expenses shall include, but not be limited to; insurance, taxes."
        )
        # Note: this won't fire — the phrase must be "including but not limited to"
        # at end. Let's use the correct positive form:
        sigs = run(
            "Permitted uses include retail operations, including but not limited to;"
        )
        hits = of_type(sigs, "truncated_list")
        assert hits, (
            "Expected truncated_list for 'including but not limited to;' at sentence end"
        )

    def test_negative_complete_list(self):
        text = (
            "Operating expenses include, without limitation, real estate taxes, "
            "insurance premiums, and maintenance costs."
        )
        sigs = run(text)
        assert not of_type(sigs, "truncated_list"), (
            "A complete list after 'including without limitation' should NOT fire"
        )

    def test_boundary_numbered_list_truncation_not_detected(self):
        # BEHAVIORAL NOTE: "(i) heat, (ii) hot water, (iii)" is a truncated numbered
        # list but does NOT match _TRUNCATED_LIST_PATTERN. The detector is specifically
        # scoped to the "including without limitation / but not limited to" construct.
        sigs = run("Services provided include (i) heat, (ii) hot water, (iii)")
        assert not of_type(sigs, "truncated_list"), (
            "Boundary: numbered list truncation is NOT detected by this pattern. "
            "Detector scope is limited to 'including without limitation' phrasings."
        )

    def test_boundary_and_other_reasonable_expenses(self):
        # "and other reasonable expenses" at list end — does not match the pattern.
        sigs = run(
            "Operating expenses include taxes, insurance, and other reasonable expenses."
        )
        assert not of_type(sigs, "truncated_list"), (
            "Boundary: 'and other reasonable expenses' does NOT trigger truncated_list"
        )


# ── 6. undefined_term ──────────────────────────────────────────────────────────
#
# Pattern: _DEFINED_TERM_REF_PATTERN:
#   "([A-Z][A-Za-z\s]+?)" \s+ (as defined herein|above|in Article/Section X|shall have the meaning)
# Compares against _extract_definitions from full_tenant_text:
#   "[Term]" means/shall mean/is defined as/refers to  → adds term.lower() to set
# Entry: detect_negative_space
# Return: signal with severity="medium", evidence='"<Term>"'
#
# BEHAVIORAL NOTE: The detector does NOT flag arbitrary capitalized terms used in
# body text. It fires ONLY when a term appears in the specific quoted+phrase form
# (e.g. "Permitted Use" as defined herein) AND that term has no corresponding
# definition in the full document text.

class TestUndefinedTerm:
    def test_positive_term_cited_as_defined_but_not_defined(self):
        # "Permitted Use" as defined herein, but no definition in full_text
        sigs = run(
            'The "Permitted Use" as defined herein shall be limited to retail pharmacy.',
            full_text="",
        )
        hits = of_type(sigs, "undefined_term")
        assert hits, (
            "Expected undefined_term for 'Permitted Use' cited as defined but absent "
            "from document definitions"
        )
        assert "Permitted Use" in hits[0]["evidence"]

    def test_negative_term_defined_in_document(self):
        # "Permitted Use" cited and also defined
        full_text = (
            '"Permitted Use" means the retail sale of pharmaceutical products '
            "and related health goods."
        )
        sigs = run(
            'The "Permitted Use" as defined herein shall be limited to retail pharmacy.',
            full_text=full_text,
        )
        assert not of_type(sigs, "undefined_term"), (
            "Term is defined in full_text — should not fire"
        )

    def test_boundary_bare_capitalized_terms_not_detected(self):
        # "Landlord" and "Tenant" used in prose without the quoted+phrase construct.
        # BEHAVIORAL NOTE: The pattern requires the term to be in double quotes AND
        # followed by "as defined herein" etc. Bare prose capitalization does NOT fire.
        sigs = run(
            "Landlord shall maintain the roof. Tenant shall pay rent monthly.",
            full_text="",
        )
        assert not of_type(sigs, "undefined_term"), (
            "Boundary: bare 'Landlord' / 'Tenant' without the as-defined phrasing "
            "do NOT trigger undefined_term."
        )

    def test_boundary_shall_have_the_meaning_phrasing(self):
        # Alternate trigger phrasing: "shall have the meaning"
        sigs = run(
            'The "Base Rent" shall have the meaning ascribed to it in this Lease.',
            full_text="",
        )
        hits = of_type(sigs, "undefined_term")
        assert hits, (
            "The 'shall have the meaning' alternate phrasing should also trigger "
            "undefined_term when the term is not defined in the document."
        )
