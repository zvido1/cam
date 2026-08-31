"""
CAM Lease Review — Perspective-Aware Display Resolution (Step 273)

Step 278 also hosts `extract_headline`, the deterministic short-summary
extractor used by both the model-path exposure engine (as a fallback if
the model omits its headline field) and the schema-path branch (always,
since v1.1.5 schema strings have no headline field).

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
    # Step 522: entries that were never judged, or whose judgment was discarded.
    # Deliberately NOT folded into "Covered" -- Step 521 measured that fall-through
    # and found a withheld verdict rendering as a checkmark.
    "not_assessed":            "Not Assessed",
}

BUCKET_ORDER_BY_PERSPECTIVE = {
    "tenant":   ["needs_attention", "worth_reviewing", "not_assessed", "covered"],
    "landlord": ["needs_attention", "favorable_to_your_side", "worth_reviewing", "not_assessed", "covered"],
    "neutral":  ["needs_attention", "asymmetric_terms", "worth_reviewing", "not_assessed", "covered"],
}

BUCKET_COLORS_HEX = {
    "needs_attention":         "#dc2626",
    "favorable_to_your_side":  "#16a34a",
    "asymmetric_terms":        "#7c3aed",
    "worth_reviewing":         "#d97706",
    "covered":                 "#16a34a",
    # Slate, not amber and not green: this is an absence of information, not a
    # risk grade. It must not read as either "fine" or "bad".
    "not_assessed":            "#475569",
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

    # ── Step 522: assessment_status outranks coverage_state ───────────────────
    # An entry nobody judged has a coverage_state anyway -- `not_applicable`,
    # `review_needed`, whatever `default_when_unclear` resolved to -- and Step 521
    # measured every one of those falling through to COVERED. The state describes
    # WHAT was concluded; this describes WHETHER anything was. Whether must win,
    # because a conclusion nobody reached is not a conclusion.
    #
    # Absent field -> treated as "unset", NOT as assessed. Fail-closed: a result
    # produced before this field existed, or by a route that forgets it, is shown
    # as unrecorded rather than silently promoted to a clean verdict.
    status = coverage_item.get("assessment_status") or "unset"
    if status != "assessed":
        _lbl = {
            "not_assessed": "NOT ASSESSED",
            "suppressed":   "ASSESSMENT DISCARDED",
        }.get(status, "ASSESSMENT STATUS NOT RECORDED")
        return {"bucket": "not_assessed",
                "label":  _lbl,
                "tone":   "not_assessed",
                "marker": "?",
                "assessment_status": status}

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
        "not_assessed":            [],
    }
    for item in coverage_items or []:
        disp = _resolve_display(item, p)
        grouped.setdefault(disp["bucket"], []).append((item, disp))

    coverage_gaps_items = grouped["needs_attention"] + grouped["worth_reviewing"]
    covered_items = grouped["covered"]
    # Step 522: kept OUT of coverage_gaps_items and OUT of covered_items. It is
    # neither a finding nor a clean bill, and folding it into either is the defect.
    not_assessed_items = grouped["not_assessed"]

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

    # Step 522: emitted for all three perspectives, and placed BEFORE "Covered"
    # so a reader scanning downward meets the unjudged entries before the clean
    # ones. Every perspective shares this tail; the bucket is perspective-blind
    # because "nobody judged it" is not a matter of viewpoint.
    if not_assessed_items:
        sections.append({
            "key":   "not_assessed",
            "title": "Not Assessed",
            "intro": (
                "The following provisions were NOT evaluated. They are not "
                "findings and they are not clean bills of health -- no judgment "
                "was reached about them, so their absence from the sections above "
                "means nothing was checked, not that nothing was wrong."
            ),
            "items": not_assessed_items,
        })

    if covered_items:
        sections.append({
            "key":   "covered",
            "title": "Covered",
            "intro": "Provisions adequately addressed.",
            "items": covered_items,
        })

    return sections


# ── Step 278: Deterministic headline extraction ──
#
# Joshua flagged the Synopsis as too verbose — 11 items × 3-4 sentences
# of exposure prose meant a lawyer scanning the Coverage & Gaps section
# had to read 15-20 sentences before deciding whether anything mattered.
# `extract_headline` produces a short scannable summary from any
# exposure string, used uniformly across model-path and schema-path
# items so the Synopsis renders one consistent shape.
#
# Schema-path strings in v1.1.5 were written by Tzvi in Step 272 with a
# semicolon-separated structure ("summary; detail"). The first clause
# is already a natural headline. The deterministic extractor leverages
# this structure rather than introducing a new field.

import re as _re


def extract_headline(text: str, max_chars: int = 60) -> str:
    """Extract a short scannable headline from an exposure prose string.

    Priority order:
      1. Text before first semicolon (covers schema-path "summary; detail").
      2. First sentence (text up to first sentence-ending punctuation
         followed by whitespace or end-of-string).
      3. First `max_chars` (fallback).

    The result is capped at `max_chars`. If trimming is needed, the
    extractor truncates at the last word boundary before `max_chars`
    and appends "...".
    """
    if not text:
        return ""

    text = str(text).strip()
    if not text:
        return ""

    # 1. Semicolon split — schema-path strings are "summary; detail".
    if ";" in text:
        candidate = text.split(";", 1)[0].strip()
        if candidate and len(candidate) <= max_chars:
            return candidate

    # 2. First-sentence split — handles model-generated prose where the
    #    opening sentence already names the risk concisely.
    sentences = _re.split(r'(?<=[.!?])\s+', text, maxsplit=1)
    if sentences and sentences[0]:
        candidate = sentences[0].rstrip('.!?').strip()
        if candidate and len(candidate) <= max_chars:
            return candidate

    # 3. Fallback: word-boundary truncate at `max_chars`.
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0].rstrip('.,;:!?-')
    if not truncated:
        truncated = text[:max_chars].rstrip()
    return truncated + "..."


# ── Step 485: incompleteness statement, shared by every export surface ────────
# One source of wording for the DOCX annotator, the PDF annotator and the
# summary generator. Steps 476/477 made the pipeline continue past an
# extraction-completeness failure and mark the result invalid_for_legal_analysis;
# Step 477 closed the web surfaces but left the exported artefacts carrying no
# statement at all -- a lawyer handed a DOCX or PDF never sees the web banner.
#
# This module is a formatting helper, not a display surface: it imports nothing
# from the consumers, so every export can share it without an import cycle.

INCOMPLETE_TITLE = "INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS"


def incomplete_report_lines(results: dict):
    """Return the banner lines for an incomplete result, or None if complete.

    None means "say nothing" -- a complete report must be byte-identical to what
    it produced before this step.
    """
    if not isinstance(results, dict):
        return None
    summary = results.get("summary") or {}
    incomplete = bool(
        results.get("invalid_for_legal_analysis")
        or results.get("extraction_completeness_failed")
        or summary.get("REPORT_INCOMPLETE")
    )
    if not incomplete:
        return None
    statement = (
        results.get("degraded_statement")
        or summary.get("incomplete_statement")
        or ""
    ).strip()
    lps = (results.get("extraction_completeness_failed_lps")
           or summary.get("issue_areas_with_no_evidence") or [])
    lines = [INCOMPLETE_TITLE]
    if statement:
        lines.append(statement)
    if lps:
        lines.append("Issue areas with no evidence: " + ", ".join(str(x) for x in lps))
    return lines


PANEL_SUBSTITUTED_TITLE = "PANEL SUBSTITUTED - NOT THE EVALUATOR PANEL THIS REPORT NAMES"


def panel_substitution(results: dict):
    """Step 497: what actually served each evaluator seat, and whether that matters.

    Returns None when every seat was served by its own primary model. Otherwise a
    dict with `tier`, per-role service counts, and the affected issue areas.

    WHY THIS IS SEPARATE FROM incomplete_report_lines():
    extraction incompleteness means part of the DOCUMENT was not analysed; panel
    substitution means the PANEL that analysed it was not the panel claimed. They
    are different facts about different things and a reader needs both, so they do
    not share a statement. Step 487's two deployed runs had role A substituted on
    196 and 202 of 202 verdicts and every disclosure surface stayed silent, because
    all six keyed on `invalid_for_legal_analysis`, which is False for this case.

    THE THRESHOLD, and why it is this one:

      tier "substituted"  -- disclosed prominently. Either
          (a) some issue area lost a seat entirely (a role produced no verdict at
              all there), so that area was decided by two evaluators, not three --
              a different instrument, not a different model; or
          (b) some role's own primary served FEWER THAN HALF of that role's
              element verdicts, i.e. the model the report names did a minority of
              its own seat's work.

      tier "noted"        -- recorded in detail, no prominent banner: any
          substitution that clears both bars.

    50% is a majority, not a tuned constant: it is the point at which the named
    model stops being the one that mostly did the work. Step 487 fires (a) and (b);
    Step 496's single transient fallback (11 of 202 records on one issue area,
    claude-haiku-4-5, malformed_response) fires neither and is reported as "noted".
    Nothing is silently suppressed and a one-LP retry is not called a substitution.
    """
    if not isinstance(results, dict):
        return None
    served, lost_areas, subs = {}, [], {}
    for lp in (results.get("coverage_assessment") or []):
        area = lp.get("issue_area_id")
        roles_here = {}
        for ev in (lp.get("element_verdicts") or []):
            for e in (ev.get("evaluator_verdicts") or []):
                role = e.get("role")
                if not role:
                    continue
                slot = served.setdefault(role, {})
                # Step 497: a stub asserts no model. Old results (pre-497) encode
                # that only in `reasoning`; new ones carry served=False. Honour both,
                # or a census reads a stub as service -- the Step 487/489 defect.
                stub = (e.get("served") is False) or (
                    str(e.get("reasoning") or "").strip() == "Evaluator %s did not complete" % role)
                model = None if stub else e.get("actual_model")
                slot[model] = slot.get(model, 0) + 1
                roles_here.setdefault(role, set()).add(model)
                if model and e.get("is_fallback"):
                    subs.setdefault(model, set()).add(area)
        for role, models in roles_here.items():
            if models == {None}:
                lost_areas.append((area, role))

    if not subs and not lost_areas:
        return None

    primary = {}
    for role, counts in served.items():
        real = {m: n for m, n in counts.items() if m}
        primary[role] = max(real, key=real.get) if real else None

    minority = []
    for role, counts in served.items():
        total = sum(counts.values())
        # The named primary is whichever model is NOT flagged is_fallback; when a
        # role fell back everywhere there is no such model, which is exactly case (b).
        non_fb = sum(n for m, n in counts.items() if m and m not in subs)
        if total and non_fb * 2 < total:
            minority.append(role)

    tier = "substituted" if (lost_areas or minority) else "noted"
    return {
        "tier": tier,
        "served": {r: {(m or "(no model)"): n for m, n in c.items()} for r, c in served.items()},
        "substitute_models": {m: sorted(a) for m, a in subs.items()},
        "seats_lost": sorted(set(lost_areas)),
        "minority_roles": sorted(minority),
        "primary_by_role": primary,
    }


def panel_substitution_lines(results: dict):
    """Banner lines for a substituted panel, or None to say nothing.

    Returns lines only for tier "substituted". Tier "noted" is real and is carried
    in the structured `panel_substitution` dict for the job aggregate and the report
    body -- it is not suppressed, it is just not a banner.
    """
    ps = panel_substitution(results)
    if not ps or ps.get("tier") != "substituted":
        return None
    lines = [PANEL_SUBSTITUTED_TITLE]
    bits = []
    for model, areas in sorted(ps.get("substitute_models", {}).items()):
        bits.append("%s stood in on %d issue area(s)" % (model, len(areas)))
    if bits:
        lines.append("This document was evaluated by a substituted panel: "
                     + "; ".join(bits) + ".")
    if ps.get("minority_roles"):
        lines.append("Evaluator seat(s) %s were served mostly by a model other than the one named."
                     % ", ".join(ps["minority_roles"]))
    if ps.get("seats_lost"):
        areas = sorted({a for a, _ in ps["seats_lost"]})
        lines.append("Decided by two evaluators rather than three: " + ", ".join(areas) + ".")
    lines.append("Findings are not invalid, but the evaluator panel is not the one this report names.")
    return lines


def incomplete_tenants(tenant_results):
    """Step 485/486: [(tenant_file, lines)] for every incomplete result in a batch.

    The batch case needs something the single case does not: a reader must see
    WHICH tenant's report is incomplete, not merely that one of them is. This
    returns the affected tenants paired with their own statement, so a caller can
    both list them up front and mark each tenant's own section.
    """
    out = []
    for tr in (tenant_results or []):
        lines = incomplete_report_lines(tr)
        if lines:
            out.append(((tr or {}).get("tenant_file") or "Unknown", lines))
    return out
