"""
CAM Lease Review — Perspective-Aware Display Resolution (Step 273)

The classifier in `lease_coverage.py` is perspective-blind: every rule in
`_UNFAVORABLE_PATTERNS` and `_UNENFORCEABLE_PATTERNS` matches a tenant-disfavor
pattern (audited 2026-04-29 — see Step 273 status file). The state value
`covered_unfavorable` therefore means "asymmetric tilt detected against
tenant" regardless of which perspective the user selected for the run.

This module is the interpretation layer that sits between the classifier
and the Synopsis / annotated-document presentation. `_resolve_display`
maps a coverage-assessment item plus the run's perspective to a display
bucket, label, tone, and marker. Tenant rendering preserves the
pre-Step-273 labels (MISSING / INCOMPLETE / UNFAVORABLE TERMS) byte-for-
byte. Landlord and Neutral runs reframe `covered_unfavorable` and
`potentially_unenforceable` items so the Synopsis reads with one
consistent voice instead of contradicting itself.
"""

from typing import Optional


BUCKET_SECTION_HEADERS = {
    "needs_attention":         "Needs Attention",
    "favorable_to_your_side":  "Favorable Terms to Preserve",
    "asymmetric_terms":        "Asymmetric Terms",
    "worth_reviewing":         "Worth Reviewing",
    "covered":                 "Covered",
}

BUCKET_ORDER_BY_PERSPECTIVE = {
    "tenant":   ["needs_attention", "worth_reviewing", "covered"],
    "landlord": ["needs_attention", "favorable_to_your_side", "worth_reviewing", "covered"],
    "neutral":  ["needs_attention", "asymmetric_terms", "worth_reviewing", "covered"],
}

BUCKET_COLORS_HEX = {
    "needs_attention":         "#dc2626",
    "favorable_to_your_side":  "#16a34a",
    "asymmetric_terms":        "#7c3aed",
    "worth_reviewing":         "#d97706",
    "covered":                 "#16a34a",
}

# Buckets whose items get a coverage callout in the annotated PDF/DOCX
# (`[GAP]` stickies for Tenant/Neutral and the same-anchor callout block
# in Landlord runs). `missing` items have no anchor in the document body
# and are excluded by the annotator regardless of bucket.
ANNOTATED_BUCKETS = {
    "needs_attention",
    "favorable_to_your_side",
    "asymmetric_terms",
    "worth_reviewing",
}


def resolve_perspective(result: dict) -> str:
    """Determine the document-level perspective from a pipeline result dict.

    Order of precedence: top-level "perspective" -> coverage_assessment[].
    exposure_perspective (most common non-empty value, with first-seen as
    tiebreak) -> "tenant".
    """
    top_level = (result.get("perspective") or "").strip().lower()
    if top_level:
        return top_level
    counts = {}
    order = []
    for item in result.get("coverage_assessment", []) or []:
        val = (item.get("exposure_perspective") or "").strip().lower()
        if not val:
            continue
        if val not in counts:
            order.append(val)
        counts[val] = counts.get(val, 0) + 1
    if not counts:
        return "tenant"
    best = order[0]
    for val in order:
        if counts[val] > counts[best]:
            best = val
    return best


def _resolve_display(coverage_item: dict, perspective: Optional[str]) -> dict:
    """Map a coverage-assessment item to perspective-aware display attributes.

    Returns a dict with keys:
      - bucket: "needs_attention" | "favorable_to_your_side" |
                "asymmetric_terms" | "worth_reviewing" | "covered"
      - label:  per-item state-label string for the Coverage & Gaps row
                (e.g. "UNFAVORABLE TERMS", "FAVORABLE TERMS", "INCOMPLETE")
      - tone:   "warning" | "positive" | "informational" | "review" | "covered"
      - marker: single-character prefix for the Provision Checklist line
                (e.g. "✕", "✚", "≠", "○", "✓")

    Tenant labels match the pre-Step-273 state_labels mapping byte-for-byte
    (MISSING / INCOMPLETE / UNFAVORABLE TERMS) so the post-Step-272 Tenant
    rendering remains identical at the prose layer.
    """
    state = coverage_item.get("coverage_state", "")
    pcls = coverage_item.get("partial_class", "")
    p = (perspective or "tenant").lower()
    if p not in ("tenant", "landlord", "neutral"):
        p = "tenant"

    if state == "covered_unfavorable":
        if p == "landlord":
            return {"bucket": "favorable_to_your_side",
                    "label":  "FAVORABLE TERMS",
                    "tone":   "positive",
                    "marker": "✚"}  # heavy plus
        if p == "neutral":
            return {"bucket": "asymmetric_terms",
                    "label":  "TILTS TOWARD LANDLORD",
                    "tone":   "informational",
                    "marker": "≠"}  # not-equal
        return {"bucket": "needs_attention",
                "label":  "UNFAVORABLE TERMS",
                "tone":   "warning",
                "marker": "✕"}

    if state == "potentially_unenforceable":
        if p == "landlord":
            return {"bucket": "favorable_to_your_side",
                    "label":  "AGGRESSIVE — ENFORCEABILITY UNCERTAIN",
                    "tone":   "positive",
                    "marker": "✚"}
        if p == "neutral":
            return {"bucket": "asymmetric_terms",
                    "label":  "TILTS TOWARD LANDLORD — ENFORCEABILITY UNCERTAIN",
                    "tone":   "informational",
                    "marker": "≠"}
        return {"bucket": "needs_attention",
                "label":  "POTENTIALLY UNENFORCEABLE",
                "tone":   "warning",
                "marker": "✕"}

    if state == "missing":
        return {"bucket": "needs_attention",
                "label":  "MISSING",
                "tone":   "warning",
                "marker": "✕"}

    if pcls == "partial_material":
        return {"bucket": "needs_attention",
                "label":  "INCOMPLETE",
                "tone":   "warning",
                "marker": "✕"}

    if pcls == "partial_review":
        return {"bucket": "worth_reviewing",
                "label":  "INCOMPLETE",
                "tone":   "review",
                "marker": "○"}

    if state == "broken_xref":
        return {"bucket": "needs_attention",
                "label":  "BROKEN_XREF",
                "tone":   "warning",
                "marker": "✕"}

    return {"bucket": "covered",
            "label":  "COVERED",
            "tone":   "covered",
            "marker": "✓"}


# ── Step 275: Section-grouping logic ──
#
# Step 273 settled the item-level question (which label and bucket each
# item gets). Step 275 settles the section-level question (which section
# frame contains the items). The classifier detects tenant-disfavor
# asymmetry only — that fact propagates into the section disclosures so
# the limitation is visible to the lawyer reading the Synopsis instead
# of hidden inside the bucketing.

# Per-perspective scope disclosure shown beneath the perspective
# declaration on the Synopsis cover.
PERSPECTIVE_SCOPE_DISCLOSURE = {
    "tenant":   "Detection focuses on tenant-disfavor asymmetry.",
    "landlord": "Detection focuses on tenant-disfavor asymmetry; tenant-favorable asymmetry is not yet separately surfaced.",
    "neutral":  "Detection focuses on landlord-favorable asymmetry.",
}


def resolve_sections(coverage_items: list, perspective: str) -> list:
    """Group coverage items into perspective-aware Synopsis sections.

    Returns a list of section dicts in display order. Each section has:
      - key:   stable identifier ("asymmetric_favor" | "asymmetric" |
               "coverage_gaps" | "covered")
      - title: section header text (e.g. "Coverage & Gaps")
      - intro: one-sentence intro string (or "" for none)
      - items: ordered list of (item, display) tuples where `display` is
               the `_resolve_display(item, perspective)` dict

    Empty sections are filtered out — callers can iterate the returned
    list and render each section unconditionally.
    """
    p = (perspective or "tenant").lower()
    if p not in ("tenant", "landlord", "neutral"):
        p = "tenant"

    # Bucket each item via the existing helper.
    grouped = {
        "needs_attention":         [],
        "favorable_to_your_side":  [],
        "asymmetric_terms":        [],
        "worth_reviewing":         [],
        "covered":                 [],
    }
    for item in coverage_items or []:
        disp = _resolve_display(item, p)
        grouped.setdefault(disp["bucket"], []).append((item, disp))

    coverage_gaps_items = grouped["needs_attention"] + grouped["worth_reviewing"]
    covered_items = grouped["covered"]

    sections = []

    if p == "landlord":
        if grouped["favorable_to_your_side"]:
            sections.append({
                "key":   "asymmetric_favor",
                "title": "Asymmetric Provisions in Your Favor",
                "intro": (
                    "The following provisions tilt in the landlord's favor "
                    "based on detected patterns. Provisions that tilt in the "
                    "tenant's favor are not yet separately surfaced."
                ),
                "items": grouped["favorable_to_your_side"],
            })
        if coverage_gaps_items:
            sections.append({
                "key":   "coverage_gaps",
                "title": "Coverage & Gaps",
                "intro": (
                    "The following provisions are incomplete, missing, or have "
                    "integrity issues that warrant attention regardless of "
                    "perspective."
                ),
                "items": coverage_gaps_items,
            })
    elif p == "neutral":
        if grouped["asymmetric_terms"]:
            sections.append({
                "key":   "asymmetric",
                "title": "Asymmetric Provisions",
                "intro": (
                    "The following provisions tilt toward one party based on "
                    "detected patterns. Detection focuses on landlord-favorable "
                    "asymmetry."
                ),
                "items": grouped["asymmetric_terms"],
            })
        if coverage_gaps_items:
            sections.append({
                "key":   "coverage_gaps",
                "title": "Coverage & Gaps",
                "intro": (
                    "The following provisions are incomplete, missing, or have "
                    "integrity issues that warrant attention regardless of "
                    "perspective."
                ),
                "items": coverage_gaps_items,
            })
    else:  # tenant — byte-identical to pre-Step-275 layout
        if coverage_gaps_items:
            sections.append({
                "key":   "coverage_gaps",
                "title": "Coverage & Gaps",
                "intro": (
                    "The following provisions were present but incomplete, "
                    "unfavorable, or missing entirely."
                ),
                "items": coverage_gaps_items,
            })

    if covered_items:
        sections.append({
            "key":   "covered",
            "title": "Covered",
            "intro": "Provisions adequately addressed.",
            "items": covered_items,
        })

    return sections
