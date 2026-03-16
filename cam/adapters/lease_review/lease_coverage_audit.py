"""
CAM Lease Review — Coverage Audit

Post-extraction audit that verifies every article and section in the
tenant lease was captured by either:
  (a) a named provision extraction (LP-01 through LP-18), or
  (b) a discovered provision

Any section found in the tenant lease text but absent from all extracted
content is flagged as a coverage gap. Coverage gaps are surfaced as warnings
and optionally injected into the pipeline as CUSTOM provisions for evaluation.

This module adds zero API calls. It operates entirely on text already in memory.

Usage:
    from cam.adapters.lease_review.lease_coverage_audit import audit_coverage

    gaps = audit_coverage(
        tenant_text=tenant_text,
        extraction_result=extraction_result,   # dict from lease_extract.py
    )
    # gaps is a list of CoverageGap dicts
"""

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Section / Article parsing
# ---------------------------------------------------------------------------

# Matches: "Section 9.5", "Section 15.5", "SECTION 9.5"
_SECTION_RE = re.compile(
    r"\bsection\s+(\d{1,3}\.\d{1,3}(?:\.\d{1,3})?)\b",
    re.IGNORECASE,
)

# Matches article headers on their own line:
# "ARTICLE XV — INDEMNIFICATION"  or  "Article 15."  or  "ARTICLE XV"
_ARTICLE_HEADER_RE = re.compile(
    r"^\s*article\s+([IVXLCDM]+|\d+)\b",
    re.IGNORECASE | re.MULTILINE,
)

# Numeric Roman → int (for sorting/comparison; not needed for gap detection)
_ROMAN = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}


def _roman_to_int(s: str) -> int:
    s = s.upper()
    total, prev = 0, 0
    for ch in reversed(s):
        val = _ROMAN.get(ch, 0)
        total += val if val >= prev else -val
        prev = val
    return total


def _parse_sections_from_text(text: str) -> set:
    """Return the set of 'X.Y' section numbers present in text."""
    return set(_SECTION_RE.findall(text))


def _parse_article_headers_from_text(text: str) -> set:
    """Return set of article identifiers (e.g. 'XV', '15') from headers."""
    return {m.group(1).upper() for m in _ARTICLE_HEADER_RE.finditer(text)}


# ---------------------------------------------------------------------------
# Coverage audit
# ---------------------------------------------------------------------------

def audit_coverage(
    tenant_text: str,
    extraction_result: Dict[str, Any],
    template_text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compare what sections exist in both documents against what was extracted.

    Audits coverage in both directions:
    - Tenant side: every Section X.Y in the tenant lease must appear in at
      least one extracted tenant_text field or discovered provision.
    - Template/reference side (optional): every Section X.Y in the reference
      document must appear in at least one extracted template_text field.
      Pass template_text to enable this check (important in comparison mode
      where the reference is an unknown executed lease, not a controlled template).

    Args:
        tenant_text: Full raw text of the tenant lease.
        extraction_result: Dict returned by lease_extract.extract_provisions(),
            containing keys: 'provisions', 'discovered_provisions'.
        template_text: Full raw text of the reference/template document.
            If provided, template-side coverage is also audited.

    Returns:
        List of CoverageGap dicts, each with:
            section_ref:    e.g. "15.5" or "21.1"
            side:           "tenant" | "template"
            claimed_by:     provision_id that claimed the article, or None
            gap_type:       "extra_subsection" | "unclaimed_section"
            article_num:    the article number (e.g. "15") or None
            warning:        human-readable description
    """
    # ── Build the full picture of what was extracted (both sides) ──
    # section_ref → provision_id, for all refs seen in ANY extracted field
    all_extracted: Dict[str, str] = {}
    tenant_extracted: Dict[str, str] = {}   # tenant_text fields only
    template_extracted: Dict[str, str] = {} # template_text fields only

    for prov in extraction_result.get("provisions", []):
        pid = prov.get("provision_id", "")

        for sec in _parse_sections_from_text(prov.get("tenant_text") or ""):
            tenant_extracted.setdefault(sec, pid)
            all_extracted.setdefault(sec, pid)
        for sec in _parse_sections_from_text(prov.get("tenant_section_ref") or ""):
            tenant_extracted.setdefault(sec, pid)
            all_extracted.setdefault(sec, pid)

        for sec in _parse_sections_from_text(prov.get("template_text") or ""):
            template_extracted.setdefault(sec, pid)
            all_extracted.setdefault(sec, pid)
        for sec in _parse_sections_from_text(prov.get("template_section_ref") or ""):
            template_extracted.setdefault(sec, pid)
            all_extracted.setdefault(sec, pid)

    for disc in extraction_result.get("discovered_provisions", []):
        for sec in _parse_sections_from_text(disc.get("clause_text") or ""):
            tenant_extracted.setdefault(sec, "DISCOVERED")
            all_extracted.setdefault(sec, "DISCOVERED")
        for sec in _parse_sections_from_text(disc.get("tenant_section_ref") or ""):
            tenant_extracted.setdefault(sec, "DISCOVERED")
            all_extracted.setdefault(sec, "DISCOVERED")

    # article → provision_id (for gap classification)
    article_to_provision: Dict[str, str] = {}
    for sec_ref, pid in all_extracted.items():
        article_to_provision.setdefault(sec_ref.split(".")[0], pid)

    gaps = []

    def _find_gaps_for_doc(
        doc_text: str,
        extracted_map: Dict[str, str],
        side: str,
    ) -> None:
        """Append gaps found in doc_text to the outer gaps list."""
        doc_sections = _parse_sections_from_text(doc_text)
        for sec_ref in sorted(doc_sections, key=lambda s: [int(x) for x in s.split(".")]):
            if sec_ref in extracted_map:
                continue  # accounted for

            article = sec_ref.split(".")[0]
            claimed_by = article_to_provision.get(article)

            if claimed_by:
                gap_type = "extra_subsection"
                warning = (
                    f"[{side}] Section {sec_ref} is present in the {side} document "
                    f"but was not captured in the extraction for {claimed_by} "
                    f"(article {article} was claimed by {claimed_by}). "
                    f"This subsection may be material."
                )
            else:
                gap_type = "unclaimed_section"
                warning = (
                    f"[{side}] Section {sec_ref} (article {article}) is present in "
                    f"the {side} document but was not captured by any named provision "
                    f"or discovered provision. This section may have been silently skipped."
                )

            gaps.append({
                "section_ref": sec_ref,
                "side": side,
                "article_num": article,
                "claimed_by": claimed_by,
                "gap_type": gap_type,
                "warning": warning,
            })

    # Audit tenant side (always)
    _find_gaps_for_doc(tenant_text, tenant_extracted, "tenant")

    # Audit template/reference side (when provided)
    if template_text:
        _find_gaps_for_doc(template_text, template_extracted, "template")

    return gaps


def format_gap_report(gaps: List[Dict[str, Any]]) -> str:
    """Return a human-readable summary of coverage gaps."""
    if not gaps:
        return "Coverage audit: PASS — all sections accounted for."

    tenant_gaps = [g for g in gaps if g.get("side", "tenant") == "tenant"]
    template_gaps = [g for g in gaps if g.get("side") == "template"]

    lines = [f"Coverage audit: {len(gaps)} gap(s) detected "
             f"(tenant: {len(tenant_gaps)}, template/reference: {len(template_gaps)})"]
    for g in gaps:
        side = g.get("side", "tenant")
        lines.append(
            f"  [{side}][{g['gap_type']}] Section {g['section_ref']} "
            f"(article {g['article_num']}, claimed by {g['claimed_by'] or 'none'})"
        )
    return "\n".join(lines)


def gaps_to_custom_provisions(
    gaps: List[Dict[str, Any]],
    tenant_text: str,
    existing_custom_count: int = 0,
) -> List[Dict[str, Any]]:
    """Convert unclaimed-section gaps into lightweight CUSTOM provision stubs.

    Only creates stubs for 'unclaimed_section' gaps (articles not claimed by
    any LP-XX or discovered provision). 'extra_subsection' gaps are handled
    by the prompt fix — they should be re-extracted by Gemini as part of the
    owning provision.

    Args:
        gaps: List of gap dicts from audit_coverage().
        tenant_text: Full tenant lease text (used to extract section content).
        existing_custom_count: How many CUSTOM provisions already exist,
            so new ones get non-conflicting IDs.

    Returns:
        List of CUSTOM provision dicts ready for evaluation, or empty list.
    """
    unclaimed = [g for g in gaps if g["gap_type"] == "unclaimed_section"]
    if not unclaimed:
        return []

    # Group by article so we create one stub per article, not per section
    by_article: Dict[str, List] = {}
    for g in unclaimed:
        by_article.setdefault(g["article_num"], []).append(g)

    stubs = []
    for i, (article_num, article_gaps) in enumerate(sorted(by_article.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)):
        cid = f"CUSTOM-{existing_custom_count + i + 1:02d}"
        section_refs = sorted(
            {g["section_ref"] for g in article_gaps},
            key=lambda s: [int(x) for x in s.split(".")]
        )
        # Extract text for these sections from the tenant lease
        clause_text = _extract_article_text(tenant_text, article_num, section_refs)

        stubs.append({
            "provision_id": cid,
            "provision_name": f"Unaccounted Article {article_num}",
            "tenant_text": clause_text,
            "template_text": "",
            "status": "TENANT_ONLY",
            "alignment_notes": (
                f"Sections {', '.join(section_refs)} were present in the tenant "
                f"lease but not captured by any named or discovered provision. "
                f"Flagged by coverage audit."
            ),
            "definition_changes": "",
            "template_section_ref": "",
            "tenant_section_ref": f"Article {article_num}, Sections {', '.join(section_refs)}",
            "coverage_gap": True,
        })

    return stubs


def _extract_article_text(tenant_text: str, article_num: str, section_refs: List[str]) -> str:
    """Extract the text of an article from the tenant lease by section refs.

    Falls back to a window around the first matching section number.
    """
    if not section_refs:
        return ""

    first_ref = section_refs[0]
    # Find "Section X.Y" in the text
    pattern = re.compile(
        r"\bsection\s+" + re.escape(first_ref) + r"\b",
        re.IGNORECASE,
    )
    m = pattern.search(tenant_text)
    if not m:
        return ""

    # Extract from this section to the next article boundary or 3000 chars
    start = m.start()
    # Look for next article header after start
    next_article = re.search(
        r"\n\s*(?:={5,}|article\s+[IVXLCDM\d]+\b)",
        tenant_text[start + 50:],
        re.IGNORECASE,
    )
    if next_article:
        end = start + 50 + next_article.start()
    else:
        end = min(start + 3000, len(tenant_text))

    return tenant_text[start:end].strip()


# ---------------------------------------------------------------------------
# Extraction integrity verification (Step 192)
# ---------------------------------------------------------------------------

import re as _re


def _normalize_for_verification(text: str) -> str:
    """Normalize text for substring matching.

    Handles OCR artifacts, smart quotes, varying whitespace, and
    bullet normalization to avoid false positives on valid extractions.
    """
    if not text:
        return ""
    # Normalize whitespace and line breaks
    text = _re.sub(r'\s+', ' ', text.strip())
    # Normalize smart quotes to straight quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    # Normalize dashes
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    # Normalize bullets
    text = text.replace('\u2022', '-').replace('\u00b7', '-')
    return text.lower()


def _locate_section_in_source(section_ref: str, source_text: str) -> str:
    """Locate a section in source text and return its approximate text span.

    Used for length ratio calculations. Returns empty string if not found.
    """
    if not section_ref or not source_text:
        return ""

    # Extract first section number from ref (e.g. "15.1" from "Section 15.1-15.4")
    m = _re.search(r'(\d+\.\d+)', section_ref)
    if not m:
        return ""

    first_num = m.group(1)
    pattern = _re.compile(
        r'\bsection\s+' + _re.escape(first_num) + r'\b',
        _re.IGNORECASE
    )
    match = pattern.search(source_text)
    if not match:
        return ""

    start = match.start()
    # Find the next section/article boundary
    next_boundary = _re.search(
        r'\n\s*(?:={5,}|section\s+\d+\.\d+|article\s+[IVXLCDM\d]+)\b',
        source_text[start + 50:],
        _re.IGNORECASE
    )
    end = start + 50 + next_boundary.start() if next_boundary else min(start + 5000, len(source_text))
    return source_text[start:end]


def verify_extraction(
    provision_id: str,
    extracted_text: str,
    section_ref: str,
    source_document: str,
    other_provision_headers: List[str] = None,
) -> Dict[str, Any]:
    """Verify extraction integrity for a single provision side (template or tenant).

    Returns a dict with four boolean signals and measurement data.

    Thresholds (see docs/extraction_reliability_memo_v4.md appendix):
        incomplete: extracted < 60% of source section length, or < 50 chars
        expanded:   extracted > 140% of source section length, OR contains
                    a section header from a different provision
    """
    other_provision_headers = other_provision_headers or []

    # Handle legitimately empty extractions (TEMPLATE_ONLY, etc.)
    if not extracted_text or not extracted_text.strip():
        return {
            "verification_status":    "empty",
            "extraction_verified":    False,
            "extraction_paraphrased": False,
            "extraction_incomplete":  False,
            "extraction_expanded":    False,
            "source_length_chars":    0,
            "extracted_length_chars": 0,
            "length_ratio":           0.0,
        }

    extracted_norm = _normalize_for_verification(extracted_text)
    source_norm    = _normalize_for_verification(source_document)

    extracted_len = len(extracted_text.strip())
    source_section = _locate_section_in_source(section_ref, source_document)
    source_len = len(source_section.strip()) if source_section else 0

    # Signal: paraphrased — extracted text not found verbatim in source
    is_paraphrased = bool(extracted_norm) and (extracted_norm not in source_norm)

    # Signal: incomplete — extracted text too short relative to source section
    if extracted_len < 50:
        is_incomplete = True
    elif source_len > 0:
        ratio = extracted_len / source_len
        is_incomplete = ratio < 0.60
    else:
        is_incomplete = False  # Can't determine without source section

    # Signal: expanded — extracted text too long, or contains adjacent provision header
    if source_len > 0:
        ratio = extracted_len / source_len
        length_expanded = ratio > 1.40
    else:
        length_expanded = False
        ratio = 1.0

    header_contaminated = any(
        h.lower() in extracted_text.lower()
        for h in other_provision_headers
        if h and len(h) > 10  # avoid matching very short strings
    )
    is_expanded = length_expanded or header_contaminated

    # Signal: verified — not paraphrased and not expanded and not incomplete
    is_verified = not is_paraphrased and not is_expanded and not is_incomplete

    # Summary status
    if is_verified:
        status = "verified"
    elif is_paraphrased:
        status = "paraphrased"
    elif is_incomplete:
        status = "incomplete"
    elif is_expanded:
        status = "expanded"
    else:
        status = "unverifiable"

    return {
        "verification_status":    status,
        "extraction_verified":    is_verified,
        "extraction_paraphrased": is_paraphrased,
        "extraction_incomplete":  is_incomplete,
        "extraction_expanded":    is_expanded,
        "source_length_chars":    source_len,
        "extracted_length_chars": extracted_len,
        "length_ratio":           round(ratio, 3),
    }


def verify_all_extractions(
    extraction_provisions: List[Dict[str, Any]],
    template_text: str,
    tenant_text: str,
    provision_name_map: Dict[str, str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Run extraction verification for all provisions.

    Returns a dict: provision_id -> stage1_integrity dict.
    """
    provision_name_map = provision_name_map or {}

    # Build set of provision section headers for contamination detection
    # (used to detect if adjacent provision text leaked into this extraction)
    all_section_patterns = []
    for p in extraction_provisions:
        ref = p.get("template_section_ref", "") or p.get("tenant_section_ref", "")
        if ref:
            all_section_patterns.append(ref)

    results = {}
    for p in extraction_provisions:
        pid = p.get("provision_id", "")

        # Other provision headers = all section refs except this one's
        this_ref = p.get("tenant_section_ref", "") or p.get("template_section_ref", "")
        other_headers = [r for r in all_section_patterns if r != this_ref]

        # Verify tenant side
        tenant_integrity = verify_extraction(
            provision_id=pid,
            extracted_text=p.get("tenant_text", ""),
            section_ref=p.get("tenant_section_ref", ""),
            source_document=tenant_text,
            other_provision_headers=other_headers,
        )

        results[pid] = {
            "verification_status":    tenant_integrity["verification_status"],
            "extraction_verified":    tenant_integrity["extraction_verified"],
            "extraction_paraphrased": tenant_integrity["extraction_paraphrased"],
            "extraction_incomplete":  tenant_integrity["extraction_incomplete"],
            "extraction_expanded":    tenant_integrity["extraction_expanded"],
            "repair_applied":         False,   # set by adapter after repair
            "repair_sections":        [],      # set by adapter after repair
            "input_frozen":           False,   # set by adapter after freeze
            "source_length_chars":    tenant_integrity["source_length_chars"],
            "extracted_length_chars": tenant_integrity["extracted_length_chars"],
            "length_ratio":           tenant_integrity["length_ratio"],
        }

    return results
