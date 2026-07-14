"""
Step 423A — Verified evidence-span substrate.

Canonical, hashed source + offset-addressed evidence spans, resolved and
verified by deterministic code — never by model-emitted offsets.

Doctrine (423 spec §2): evidence belongs to the lease; LPs cite into it.
This module is the addressable substrate that later 423 layers (parameter
attachment, panel selection) will cite into. It does not select evidence,
does not assign LPs, and — deliberately, in this slice — is not wired into
the live Mode C pipeline. See build_log/423A_verified_evidence_span_substrate.md
for the full list of what is deferred to later slices.

One address space. Flat character offsets. No page_ref, no table_ref (423
spec §3.2) — PDF/OCR addressing is a noted extension point, not designed
here; an optional field nobody populates becomes a second address space by
accident later.

MATCHING SEMANTICS (423B Part 0 — declared explicitly; behavior unchanged
from 423A, this is documentation closing a gap, not a code change):

  - The canonical source text (`CanonicalSource.canonical_text`) is NEVER
    rewritten or normalized. It is always the parser's raw output. Offsets
    (`start_char`/`end_char`) always index this raw, unmodified text.
  - The `canonical_whitespace_v1` normalization profile permits ONLY
    whitespace-run equivalence for the purpose of *matching* a proposed
    quote against a location in the canonical source (e.g. a quote that
    reflows a line break or collapses a double space still resolves). It
    is never used to rewrite the canonical source itself.
  - Every non-whitespace character in a proposed quote must match the
    canonical source LITERALLY for a match to be found. There is no
    paraphrase matching, no fuzzy/edit-distance matching, and no numeric,
    date, or word substitution of any kind. "45.79%" and "45.80%" are
    different strings under this profile and will never resolve to the
    same location — see `resolve_span`'s exact-then-whitespace-flexible
    search in `_find_normalized_matches`.
  - A span is `verified` only if `is_valid_invariant()` holds: the raw
    source slice at the resolved offsets, normalized, equals the proposed
    quote, normalized. This invariant is re-checked (not merely assumed)
    before a span is returned as `verified` — see `resolve_span`'s
    defence-in-depth check.

CANONICAL SOURCE NORMALIZATION V2 (Step 425):

  Step 424 measured that 55% of unverified spans traced not to the model
  or the resolver but to typographic artifacts in the parser's raw output
  — chiefly bare page-number lines injected mid-sentence by the source SEC
  filing's pagination (e.g. "...renovation;\n4\n(b) capital..."), plus
  spurious spacing around punctuation and quoted defined terms.

  The governing rule, and the line that must never be crossed:

    Strip what is not in the document. Never rewrite what is.

  Page-number lines are filing furniture, not lease content — removing
  them makes canonical_text MORE faithful to the lease, so they are
  stripped from the text itself (`canonical_whitespace_v2` /
  `_strip_page_number_lines`). Everything else observed in 424 — spacing
  around punctuation, spacing inside quote marks — IS lease content
  (those characters are genuinely in the document). Rewriting them to
  match a model's quote would be editing the evidence to fit the claim,
  which is exactly what this substrate exists to prevent. Those are
  instead tolerated ONLY in the declared matching profile
  (`canonical_whitespace_v2`'s pattern builder and normalizer) — the text
  in `canonical_text` is never touched for this reason.

  `raw_source_text` / `raw_source_text_hash` preserve the parser's
  completely untouched output alongside `canonical_text` for both
  profiles. A CanonicalSource built with `canonical_whitespace_v2` has a
  DIFFERENT `canonical_text` (and therefore a different
  `canonical_text_hash` / `source_document_hash`) than one built with
  `canonical_whitespace_v1` from the same raw text — spans resolved
  against one are invalid against the other, by the same hash-drift rule
  that has applied since 423A. That is the substrate working as designed,
  not a regression.

  `canonical_whitespace_v2` still never tolerates a substantive character
  difference: no fuzzy matching, no edit distance, no paraphrase. "45.79%"
  and "45.80%" are still, and will always be, different strings.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ── Normalization profiles ──────────────────────────────────────────────────
# Declared and versioned (423 spec §3.1). Normalization is used ONLY to
# compare a proposed quote against a candidate slice of the canonical text —
# it never alters canonical_text itself, so offsets stay exact.

NORMALIZATION_PROFILE_V1 = "canonical_whitespace_v1"
NORMALIZATION_PROFILE_V2 = "canonical_whitespace_v2"

# Punctuation characters that tolerate adjacent whitespace differences
# under v2 (Step 425 Task 2). Deliberately narrow — comma, period,
# semicolon, colon, close-paren, and the quote character (which gets
# tolerance on BOTH sides — see _build_flexible_pattern). No other
# character, and no digit ever, is treated as whitespace-adjacent-tolerant.
_V2_TOLERANT_CHARS = frozenset(',.;:)"')
_V2_QUOTE_CHAR = '"'


def _normalize_canonical_whitespace_v1(text: str) -> str:
    """Collapse whitespace runs to a single space and strip leading/trailing.

    Touches ONLY whitespace layout. Case, punctuation, digits, and word
    content are untouched, so this profile cannot mask a substantive text
    difference (a different number, a different word) as a match.
    """
    return re.sub(r"\s+", " ", text).strip()


def _normalize_canonical_whitespace_v2(text: str) -> str:
    """v1's whitespace-run collapse, PLUS two additional declared
    tolerances (Step 425 Task 2):

      - whitespace immediately before a tolerated punctuation character
        (`,.;:)"`) is removed: "word ;" normalizes the same as "word;".
      - whitespace immediately after/before a quote mark (`"`) is removed:
        '" Term "' normalizes the same as '"Term"'.

    Still touches ONLY whitespace. No digit, letter, or any other
    character is ever removed or substituted — "45.79%" and "45.80%"
    normalize to themselves, unchanged, and remain unequal.
    """
    t = re.sub(r"\s+", " ", text).strip()
    t = re.sub(r'\s+([,.;:)])', r"\1", t)
    t = re.sub(r'"\s+', '"', t)
    t = re.sub(r'\s+"', '"', t)
    return t


_NORMALIZERS = {
    NORMALIZATION_PROFILE_V1: _normalize_canonical_whitespace_v1,
    NORMALIZATION_PROFILE_V2: _normalize_canonical_whitespace_v2,
}


def normalize(text: str, profile: str = NORMALIZATION_PROFILE_V1) -> str:
    """Apply the named, versioned normalization profile."""
    try:
        fn = _NORMALIZERS[profile]
    except KeyError:
        raise ValueError(f"Unknown normalization profile: {profile!r}")
    return fn(text)


# ── Canonical source ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CanonicalSource:
    """The hashed, offset-addressable output of the deterministic parser
    (`lease_parser.parse_document`). One address space; flat character
    offsets into `canonical_text`.
    """
    source_document_hash: str
    canonical_text: str
    canonical_text_hash: str
    text_length: int
    normalization_profile: str
    source_type: str
    run_id: str
    # Step 425: the parser's completely untouched output, preserved
    # alongside canonical_text. Diagnostic provenance ONLY — never used
    # for span validity (that stays keyed to canonical_text_hash /
    # source_document_hash, which DOES differ between v1 and v2 of the
    # same raw text; see module docstring).
    raw_source_text: str = ""
    raw_source_text_hash: str = ""
    # Diagnostic transformation count — how many bare page-number lines
    # _strip_page_number_lines removed. Always 0 for v1.
    page_number_lines_stripped: int = 0


# Step 425 Task 1: a line is stripped ONLY if, after trimming leading/
# trailing spaces/tabs, its entire content is digits and nothing else.
# "Section 4", "4. Operating Expenses", "(4)", "4%", "$4", "4 days", and
# "Page 4 of 20" all keep the digit adjacent to non-whitespace content on
# the same line and are therefore never touched — the regex requires the
# digit run to reach the line-ending newline with only space/tab padding
# in between. A false strip is worse than a missed one; this rule is kept
# as narrow as it can possibly be.
_PAGE_NUMBER_LINE_RE = re.compile(r"^[ \t]*\d+[ \t]*\n", re.MULTILINE)


def _strip_page_number_lines(text: str) -> Tuple[str, int]:
    """Remove bare page-number lines from `text` (Step 425 Task 1).

    Only a line whose ENTIRE content, after trimming spaces/tabs, is one
    or more digits is removed — nothing else about the text changes. This
    is the only transformation `canonical_whitespace_v2` applies to the
    addressable text itself; every other tolerance (punctuation/quote
    spacing) lives in the matching profile, not here — see module
    docstring "the line that must never be crossed."

    Returns (stripped_text, count_of_lines_removed).
    """
    return _PAGE_NUMBER_LINE_RE.subn("", text)


def build_canonical_source(
    tenant_text: str,
    source_type: str = "lease_tenant_document",
    run_id: str = "",
    normalization_profile: str = NORMALIZATION_PROFILE_V1,
) -> CanonicalSource:
    """Wrap the deterministic parser's output as the canonical, hashed,
    offset-addressable source.

    Under `canonical_whitespace_v1` (default), `canonical_text` is the
    parser's output verbatim — no transformation is applied at the text
    level.

    Under `canonical_whitespace_v2` (Step 425), `canonical_text` is the
    parser's output with bare page-number lines removed
    (`_strip_page_number_lines`) — the one text-level transformation this
    substrate performs, because page numbers are filing furniture, not
    lease content (see module docstring). Every other tolerance (spacing
    around punctuation/quote marks) lives in the matching profile, never
    in the text.

    `raw_source_text` / `raw_source_text_hash` always preserve the
    parser's completely untouched output, regardless of profile, as
    diagnostic provenance.

    `source_document_hash` and `canonical_text_hash` are identical by
    construction (both hash `canonical_text`) — under v1 that equals
    `raw_source_text_hash`; under v2 it does not, because `canonical_text`
    has had page-number lines removed. This is deliberate: span validity
    (`EvidenceSpan.source_document_hash`) must be keyed to the exact text
    offsets are resolved against, so a v1-resolved span is correctly
    invalid against a v2 source of the same document, and vice versa.
    """
    raw_source_text = tenant_text
    raw_source_text_hash = hashlib.sha256(raw_source_text.encode("utf-8")).hexdigest()

    if normalization_profile == NORMALIZATION_PROFILE_V2:
        canonical_text, page_number_lines_stripped = _strip_page_number_lines(raw_source_text)
    else:
        canonical_text, page_number_lines_stripped = raw_source_text, 0

    canonical_digest = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
    return CanonicalSource(
        source_document_hash=canonical_digest,
        canonical_text=canonical_text,
        canonical_text_hash=canonical_digest,
        text_length=len(canonical_text),
        normalization_profile=normalization_profile,
        source_type=source_type,
        run_id=run_id,
        raw_source_text=raw_source_text,
        raw_source_text_hash=raw_source_text_hash,
        page_number_lines_stripped=page_number_lines_stripped,
    )


# ── Evidence span ────────────────────────────────────────────────────────────

VERIFIED = "verified"
AMBIGUOUS = "ambiguous"
UNVERIFIED = "unverified"

_VALID_VERIFICATION_STATUSES = frozenset({VERIFIED, AMBIGUOUS, UNVERIFIED})


@dataclass
class EvidenceSpan:
    """An offset-addressed, code-verified quote from a CanonicalSource.

    No page_ref, no table_ref — deliberate (see module docstring).
    """
    evidence_span_id: str
    source_document_hash: str
    canonical_text_hash: str
    start_char: Optional[int]
    end_char: Optional[int]
    span_text: str
    span_text_hash: str
    normalization_profile: str
    verification_status: str
    section_ref: Optional[str] = None
    source_anchor: Optional[str] = None

    def __post_init__(self):
        if self.verification_status not in _VALID_VERIFICATION_STATUSES:
            raise ValueError(f"Invalid verification_status: {self.verification_status!r}")

    def is_valid_invariant(self, canonical_source: "CanonicalSource") -> bool:
        """423 spec §3.2 hard invariant:
        normalize(canonical_text[start_char:end_char]) == normalize(span_text)

        Only meaningful for a `verified` span whose hash matches the given
        source. Returns False (never raises) for anything else, so callers
        can use this as a pure boolean gate rather than a try/except.
        """
        if self.verification_status != VERIFIED:
            return False
        if self.source_document_hash != canonical_source.source_document_hash:
            return False
        if self.start_char is None or self.end_char is None:
            return False
        slice_text = canonical_source.canonical_text[self.start_char:self.end_char]
        return normalize(slice_text, self.normalization_profile) == normalize(
            self.span_text, self.normalization_profile
        )


def _span_text_hash(span_text: str) -> str:
    return hashlib.sha256(span_text.encode("utf-8")).hexdigest()[:16]


def _build_flexible_pattern(quote: str, normalization_profile: str) -> str:
    """Build the whitespace-flexible fallback regex for `quote`.

    v1 (default): a run of whitespace in the QUOTE becomes `\\s+` in the
    pattern; every other character is escaped literally. This only
    tolerates whitespace where the quote itself already has whitespace.

    v2 (Step 425 Task 2, on top of v1): additionally inserts an OPTIONAL
    `\\s*` immediately before every tolerated punctuation character
    (`,.;:)"`) and immediately after every quote character (`"`) —
    regardless of whether the quote's own text has whitespace there. This
    tolerates a source that has extra spacing the quote lacks (or vice
    versa) ONLY at those specific punctuation/quote-mark boundaries.
    `\\s*` never requires whitespace to be present, so a quote/source pair
    with no whitespace there at all still matches identically to v1.

    Every other character — every letter, every digit, every punctuation
    character not in the tolerated set — is escaped literally in both
    profiles and must match exactly. No fuzzy matching, no edit distance,
    no paraphrase, under either profile.
    """
    tokens = re.split(r"(\s+)", quote)
    parts = []
    for tok in tokens:
        if tok == "":
            continue
        if tok.strip() == "":
            parts.append(r"\s+")
            continue
        if normalization_profile != NORMALIZATION_PROFILE_V2:
            parts.append(re.escape(tok))
            continue
        for ch in tok:
            if ch in _V2_TOLERANT_CHARS:
                parts.append(r"\s*")
            parts.append(re.escape(ch))
            if ch == _V2_QUOTE_CHAR:
                parts.append(r"\s*")
    return "".join(parts)


def _find_normalized_matches(
    canonical_text: str,
    quote: str,
    normalization_profile: str = NORMALIZATION_PROFILE_V1,
) -> List[Tuple[int, int]]:
    """Locate every position in canonical_text that matches `quote`.

    Exact substring matches are tried first (fast path — the common case of
    a model copying text byte-for-byte), identically under every profile.
    If none are found, falls back to the whitespace-flexible search built
    by `_build_flexible_pattern` for the given `normalization_profile` —
    see that function for exactly what each profile tolerates. Under every
    profile, every non-whitespace, non-punctuation-adjacent character in
    the quote must appear literally; a digit is never treated as
    whitespace, and no substantive text change is ever tolerated.

    Returns (start_char, end_char) tuples in source order. Boundaries are
    always the exact underlying characters in canonical_text, never
    positions implied by the quote.
    """
    if not quote:
        return []

    exact_matches = []
    start = 0
    while True:
        idx = canonical_text.find(quote, start)
        if idx == -1:
            break
        exact_matches.append((idx, idx + len(quote)))
        start = idx + 1
    if exact_matches:
        return exact_matches

    pattern = _build_flexible_pattern(quote, normalization_profile)
    if not pattern:
        return []
    try:
        return [(m.start(), m.end()) for m in re.finditer(pattern, canonical_text)]
    except re.error:
        return []


def _anchor_window_matches(canonical_text: str, anchor: str, start_char: int, window: int = 500) -> bool:
    """True if `anchor` appears as a substring within `window` characters
    immediately preceding `start_char` in canonical_text."""
    if not anchor:
        return False
    window_start = max(0, start_char - window)
    return anchor in canonical_text[window_start:start_char]


def resolve_span(
    canonical_source: CanonicalSource,
    quote: str,
    evidence_span_id: str,
    section_ref: Optional[str] = None,
    source_anchor: Optional[str] = None,
) -> EvidenceSpan:
    """Resolve a model-proposed verbatim quote into an EvidenceSpan.

    The model NEVER supplies offsets (423 spec §4 — models cannot count
    characters; asked for an offset, a model produces a plausible number
    that points nowhere). This function is the only place offsets are
    assigned, and it assigns them by finding `quote` in
    `canonical_source.canonical_text`.

    Outcomes (423 spec §4 table):
      - exactly one location                          -> verified
      - >1 location, resolved via source_anchor/section_ref -> verified
      - >1 location, unresolved                        -> ambiguous (never
        silently promoted to verified)
      - no location                                    -> unverified (fail-
        closed; not usable in canonical Stage 5)
    """
    matches = _find_normalized_matches(
        canonical_source.canonical_text, quote, canonical_source.normalization_profile
    )

    def _make(start_char, end_char, status):
        span = EvidenceSpan(
            evidence_span_id=evidence_span_id,
            source_document_hash=canonical_source.source_document_hash,
            canonical_text_hash=canonical_source.canonical_text_hash,
            start_char=start_char,
            end_char=end_char,
            span_text=quote,
            span_text_hash=_span_text_hash(quote),
            normalization_profile=canonical_source.normalization_profile,
            verification_status=status,
            section_ref=section_ref,
            source_anchor=source_anchor,
        )
        # Defence-in-depth: a "verified" span must satisfy the hard
        # invariant. If a resolver bug ever produced a bad match, fail
        # closed to unverified rather than emit a falsely-verified span.
        if status == VERIFIED and not span.is_valid_invariant(canonical_source):
            span.verification_status = UNVERIFIED
            span.start_char = None
            span.end_char = None
        return span

    if len(matches) == 0:
        return _make(None, None, UNVERIFIED)

    if len(matches) == 1:
        start_char, end_char = matches[0]
        return _make(start_char, end_char, VERIFIED)

    # Multiple matches: try to disambiguate by source_anchor, then section_ref.
    for anchor in (source_anchor, section_ref):
        if not anchor:
            continue
        anchored = [
            (s, e) for (s, e) in matches
            if _anchor_window_matches(canonical_source.canonical_text, anchor, s)
        ]
        if len(anchored) == 1:
            start_char, end_char = anchored[0]
            return _make(start_char, end_char, VERIFIED)

    # Unresolved ambiguity: never silently promoted to verified.
    return _make(None, None, AMBIGUOUS)


def resolve_spans(
    canonical_source: CanonicalSource,
    proposed_quotes: List[dict],
    id_prefix: str = "EV",
) -> List[EvidenceSpan]:
    """Batch-resolve proposed quotes into the span universe for a canonical
    source. This is the code side of Layer 1 (423 spec §4). The model side
    (an actual segmentation call proposing quotes) is NOT implemented in
    this slice — see the 423A report's deferred-items list.

    Each proposal: {"quote": str, "section_ref"?: str, "source_anchor"?: str,
    "evidence_span_id"?: str}. IDs are auto-assigned (EV-000001, ...) when
    not supplied.
    """
    spans = []
    for i, proposal in enumerate(proposed_quotes, start=1):
        span_id = proposal.get("evidence_span_id") or f"{id_prefix}-{i:06d}"
        spans.append(
            resolve_span(
                canonical_source,
                quote=proposal["quote"],
                evidence_span_id=span_id,
                section_ref=proposal.get("section_ref"),
                source_anchor=proposal.get("source_anchor"),
            )
        )
    return spans


def is_usable_in_canonical_stage5(span: EvidenceSpan) -> bool:
    """423 spec §4: only `verified` spans may reach canonical Stage 5.
    `unverified` is fail-closed; `ambiguous` is recorded but not used
    canonically (whether it may serve as degraded diagnostic evidence is an
    explicitly later decision — 423 spec §4). This predicate is the single
    place that doctrine lives; nothing else should inline a status-string
    comparison for this purpose.
    """
    return span.verification_status == VERIFIED


def validate_span_against_source(span: EvidenceSpan, canonical_source: CanonicalSource) -> bool:
    """423 spec §3.2 / §7.1: a span whose source_document_hash does not
    match the current parse is invalid, and must never be silently
    re-resolved. This function only compares hashes — it never re-runs
    resolution and never mutates the span.
    """
    return span.source_document_hash == canonical_source.source_document_hash
