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


def _normalize_canonical_whitespace_v1(text: str) -> str:
    """Collapse whitespace runs to a single space and strip leading/trailing.

    Touches ONLY whitespace layout. Case, punctuation, digits, and word
    content are untouched, so this profile cannot mask a substantive text
    difference (a different number, a different word) as a match.
    """
    return re.sub(r"\s+", " ", text).strip()


_NORMALIZERS = {
    NORMALIZATION_PROFILE_V1: _normalize_canonical_whitespace_v1,
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


def build_canonical_source(
    tenant_text: str,
    source_type: str = "lease_tenant_document",
    run_id: str = "",
    normalization_profile: str = NORMALIZATION_PROFILE_V1,
) -> CanonicalSource:
    """Wrap the deterministic parser's output as the canonical, hashed,
    offset-addressable source.

    `canonical_text` is the parser's output verbatim — no transformation is
    applied at the text level. Normalization (see `normalize`) is used only
    to compare a proposed quote against a candidate slice, never to alter
    the addressable text itself, so the same start_char/end_char always
    point at the same characters regardless of which quote proposed them.

    `source_document_hash` and `canonical_text_hash` are identical by
    construction in this slice (canonical_text IS the parser's output,
    unmodified). The schema keeps them as separate fields because a future
    parser stage (e.g. PDF layout reconstruction) could legitimately
    produce a canonical_text that differs from the raw parse; this split
    gives that a place to land without a schema change. Not exercised here
    — the current corpus is EDGAR .txt (423 spec §3.1).
    """
    digest = hashlib.sha256(tenant_text.encode("utf-8")).hexdigest()
    return CanonicalSource(
        source_document_hash=digest,
        canonical_text=tenant_text,
        canonical_text_hash=digest,
        text_length=len(tenant_text),
        normalization_profile=normalization_profile,
        source_type=source_type,
        run_id=run_id,
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


def _find_normalized_matches(canonical_text: str, quote: str) -> List[Tuple[int, int]]:
    """Locate every position in canonical_text that matches `quote`.

    Exact substring matches are tried first (fast path — the common case of
    a model copying text byte-for-byte). If none are found, falls back to a
    whitespace-flexible search: literal characters in the quote must match
    exactly, but any run of whitespace in the quote may match any run of
    whitespace in the source. This tolerates a model reflowing internal
    line breaks/spacing without ever tolerating a substantive text change —
    every non-whitespace character in the quote must appear literally.

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

    tokens = re.split(r"(\s+)", quote)
    pattern_parts = []
    for tok in tokens:
        if tok == "":
            continue
        if tok.strip() == "":
            pattern_parts.append(r"\s+")
        else:
            pattern_parts.append(re.escape(tok))
    if not pattern_parts:
        return []
    pattern = "".join(pattern_parts)
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
    matches = _find_normalized_matches(canonical_source.canonical_text, quote)

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
