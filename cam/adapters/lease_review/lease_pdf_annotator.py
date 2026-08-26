import re
"""
CAM Lease Review — PDF Annotator

Adds highlights and sticky note annotations on deviating/unclear provisions
in a tenant PDF file. Uses PyMuPDF (fitz) for PDF manipulation.
"""

from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF

from cam.adapters.lease_review.lease_report_generator import _sanitize_for_pdf


def _format_annotation_text(provision: dict, resolution: dict = None) -> str:
    """Format the sticky note text for a PDF provision finding."""
    pid = provision.get("provision_id", "?")
    pname = provision.get("provision_name", "")
    severity = provision.get("severity", "")
    pattern = provision.get("agreement_pattern", "")
    risk_headline = provision.get("risk_headline", "")

    sev_markers = {
        "CRITICAL": "\u2715 CRITICAL",
        "HIGH": "\u25cf HIGH",
        "MEDIUM": "\u25cb MEDIUM",
        "LOW": "\u2013 LOW",
    }
    sev_label = sev_markers.get(severity, severity)

    lines = [f"CAM \u2014 {pid} {pname} [{sev_label}]"]
    if pattern:
        lines.append(f"Evaluators: {pattern}")
    lines.append("")

    # Lead with risk headline if available
    if risk_headline:
        lines.append(risk_headline)
        lines.append("")

    # Challenge details or cascade mechanism
    if provision.get("cascade_verdict") == "CASCADE_MATERIAL":
        cascade_src = provision.get("cascade_source", {})
        if cascade_src and cascade_src.get("term"):
            lines.append(f"Definition cascade from: \"{cascade_src['term']}\"")
        lines.append(provision.get("cascade_mechanism", ""))
        lines.append(f"Impact: {provision.get('cascade_impact', '')}")
    elif provision.get("challenge_details"):
        lines.append(provision["challenge_details"])
    elif provision.get("severity_reasoning"):
        lines.append(provision["severity_reasoning"])

    # Recommended action
    action = provision.get("recommended_action", "")
    if action and action != "no_action":
        action_labels = {
            "note_for_awareness": "Note for awareness",
            "attorney_review_recommended": "\u2192 Attorney review recommended",
            "attorney_review_required": "\u2192 Attorney review required",
        }
        lines.append("")
        lines.append(action_labels.get(action, action))

    # Lawyer's resolutions from CAM review session
    if resolution:
        lines.append("")
        lines.append("\u2014 Lawyer's Review \u2014")
        status = resolution.get("status", "")
        status_labels = {
            "accepted": "Accepted as-is",
            "needs_negotiation": "Needs Negotiation",
            "not_applicable": "Not Applicable",
            "resolved": "Resolved",
        }
        if status:
            lines.append(f"Decision: {status_labels.get(status, status)}")
        concern = resolution.get("concern_state", "")
        concern_reason = resolution.get("concern_reason", "")
        if concern == "flagged" and concern_reason:
            lines.append(f"Concern: {concern_reason}")
        notes = resolution.get("notes", [])
        for note in notes:
            text = note.get("text", "") if isinstance(note, dict) else str(note)
            if text:
                lines.append(f"Note: {text}")

    result = "\n".join(line for line in lines if line is not None)
    # Strip markdown bold/italic markers
    result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)
    result = re.sub(r'\*(.+?)\*', r'\1', result)
    return result


def _severity_color(severity: str) -> tuple:
    """Return highlight color based on severity."""
    colors = {
        "CRITICAL": (1.0, 0.7, 0.7),    # Light red
        "HIGH": (1.0, 0.85, 0.6),        # Light orange
        "MEDIUM": (1.0, 0.95, 0.6),      # Yellow
        "LOW": (0.9, 1.0, 0.8),          # Light green-yellow
        "REVIEW": (0.8, 0.9, 1.0),       # Light blue
    }
    return colors.get(severity, (1.0, 0.9, 0.0))  # Default yellow


def _format_coverage_annotation_text(coverage_item: dict, cov_resolution: dict = None,
                                     perspective: str = "tenant") -> str:
    """Format the sticky note text for a coverage gap finding.

    Step 273: state_label is now perspective-aware (Landlord runs render
    `covered_unfavorable` items as "FAVORABLE TERMS"; Neutral runs as
    "TILTS TOWARD LANDLORD"). Tenant labels match the pre-Step-273 mapping
    byte-for-byte.
    """
    from cam.adapters.lease_review.lease_display import extract_headline

    pid = coverage_item.get("issue_area_id", "?")
    # Step 279: prefer issue_area_name over provision_name (which is
    # None in Mode C and was creating doubled-LP-id headers).
    pname = (coverage_item.get("provision_name")
             or coverage_item.get("issue_area_name")
             or "")
    materiality = coverage_item.get("materiality", "medium")
    exposure = coverage_item.get("exposure_statement", "")
    elements_missing = coverage_item.get("elements_missing", [])
    # Step 278: integrate headline into the header line.
    headline = (coverage_item.get("exposure_headline") or "").strip()
    if not headline and exposure:
        headline = extract_headline(exposure)

    mat_labels = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
    mat_label = mat_labels.get(materiality, materiality.upper())

    # Step 279: single-line header. State label dropped; materiality
    # parenthetical kept at the end.
    if headline:
        lines = [f"[GAP] {pid} {pname} \u2014 {headline} ({mat_label} materiality)"]
    else:
        lines = [f"[GAP] {pid} {pname} ({mat_label} materiality)"]
    lines.append("")

    if elements_missing:
        missing_str = ", ".join(str(e) for e in elements_missing[:5])
        lines.append(f"Missing: {missing_str}")
        lines.append("")

    if exposure:
        lines.append(exposure)

    # Lawyer's coverage resolution
    if cov_resolution:
        status = cov_resolution.get("status", "")
        status_labels = {
            "reviewed": "Reviewed",
            "flagged": "Flagged for follow-up",
            "accepted": "Risk accepted",
        }
        if status and status != "open":
            lines.append("")
            lines.append("\u2014 Lawyer's Review \u2014")
            lines.append(f"Decision: {status_labels.get(status, status)}")

    result = "\n".join(line for line in lines if line is not None)
    # Strip markdown bold/italic markers (mirrors deviation annotation handling)
    result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)
    result = re.sub(r'\*(.+?)\*', r'\1', result)
    return result


def _coverage_color() -> tuple:
    """Distinct purple highlight for coverage gaps - visually separate from severity reds/oranges."""
    return (0.88, 0.80, 1.0)  # Light purple



def _wrap_pdf_text(text: str, width: int):
    """Step 485: naive word wrap for the banner page. PyMuPDF insert_text does not
    wrap, and an unwrapped statement would run off the page edge unread."""
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out or [""]

def annotate_pdf(
    original_pdf_path: str,
    results: dict,
    output_path: str,
    resolutions: dict = None,
    cov_resolutions: dict = None,
) -> str:
    """Add highlights and sticky notes on deviating provisions in tenant PDF.

    Args:
        original_pdf_path: Path to the original tenant PDF file.
        results: Pipeline results dict (with "provisions" list).
        output_path: Path for the annotated output PDF.
        resolutions: Optional job resolutions dict with lawyer decisions/notes.

    Returns:
        Path to the annotated PDF file.
    """
    doc = fitz.open(original_pdf_path)

    annotations_added = 0
    text_not_found = 0

    # Step 297c: Conflict sticky notes at top of page 1
    conflicts = results.get("conflicts", []) or []
    if conflicts and len(doc) > 0:
        page = doc[0]
        page_rect = page.rect
        conflict_sev_colors = {
            "high":   (0.725, 0.106, 0.106),   # red
            "medium": (0.851, 0.467, 0.024),   # amber
            "low":    (0.420, 0.447, 0.502),   # grey
        }
        for i, c in enumerate(conflicts):
            cid = c.get("id", "")
            cname = c.get("name", "")
            sev = c.get("severity", "medium")
            lps = ", ".join(c.get("lps_implicated", []) or [])
            desc = c.get("description", "")
            sev_label = sev.upper()
            lines = [f"[CONFLICT — {sev_label}] {cid}: {cname}"]
            if lps:
                lines.append(f"Implicates {lps}.")
            if desc:
                lines.append(desc)
            note_text = "\n".join(lines)
            note_point = fitz.Point(
                page_rect.width - 30,
                20 + i * 20,
            )
            annot = page.add_text_annot(note_point, note_text)
            annot.set_info(title="CAM — Provision Conflict")
            clr = conflict_sev_colors.get(sev, conflict_sev_colors["low"])
            annot.set_colors(stroke=clr)
            annot.update()
        print(f"[pdf_annotator] Added {len(conflicts)} conflict note(s) to page 1", flush=True)

    for provision in results.get("provisions", []):
        if provision.get("final_verdict") not in ("DEVIATES", "UNCLEAR"):
            continue

        pid = provision.get("provision_id", "?")
        severity = provision.get("severity", "MEDIUM")

        # Look up resolution for this provision
        resolution = None
        if resolutions:
            resolution = resolutions.get(f"0:{pid}") or resolutions.get(pid)

        comment_text = _sanitize_for_pdf(_format_annotation_text(provision, resolution))
        highlight_color = _severity_color(severity)

        # Build search text — use first ~80 chars of tenant text
        search_text = provision.get("tenant_text", "").strip()
        if not search_text:
            search_text = provision.get("provision_name", "")

        # Try progressively shorter search strings
        found = False
        for search_len in [80, 50, 30]:
            if found:
                break
            search_key = search_text[:search_len].strip()
            if not search_key or len(search_key) < 10:
                continue

            for page in doc:
                text_instances = page.search_for(search_key)
                if text_instances:
                    # Highlight the found text
                    highlight = page.add_highlight_annot(text_instances)
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()

                    # Add sticky note near the highlight
                    note_point = fitz.Point(
                        text_instances[0].x0,
                        max(0, text_instances[0].y0 - 5),
                    )
                    annot = page.add_text_annot(note_point, comment_text)
                    annot.set_info(title="CAM Lease Analyzer")
                    annot.update()

                    annotations_added += 1
                    found = True
                    break

        if not found:
            # Fallback: try section reference
            section_ref = provision.get("tenant_section_ref", "")
            if section_ref:
                # Try to find the section reference text
                for ref_len in [30, 15]:
                    if found:
                        break
                    ref_key = section_ref[:ref_len].strip()
                    if not ref_key:
                        continue
                    for page in doc:
                        text_instances = page.search_for(ref_key)
                        if text_instances:
                            note_point = fitz.Point(
                                text_instances[0].x0,
                                max(0, text_instances[0].y0 - 5),
                            )
                            fallback_text = _sanitize_for_pdf(
                                f"CAM could not locate exact text \u2014 "
                                f"finding applies to {section_ref}.\n\n{comment_text}"
                            )
                            annot = page.add_text_annot(note_point, fallback_text)
                            annot.set_info(title="CAM Lease Analyzer")
                            annot.update()
                            annotations_added += 1
                            found = True
                            break

            if not found:
                text_not_found += 1
                print(f"[pdf_annotator] Could not locate text for {pid}", flush=True)

    # === Coverage gap annotations ===
    # Drop [GAP] sticky notes on provisions whose display bucket is one of
    # the surfaced annotation buckets (Step 273 — needs_attention,
    # favorable_to_your_side, asymmetric_terms, worth_reviewing). Items
    # that are entirely missing have no anchor in the PDF body and are
    # skipped (they still appear in the Synopsis).
    from cam.adapters.lease_review.lease_display import (
        _resolve_display, ANNOTATED_BUCKETS, resolve_perspective,
    )

    perspective = resolve_perspective(results)
    coverage_assessment = results.get("coverage_assessment", []) or []
    provisions_by_id = {p.get("provision_id"): p for p in results.get("provisions", [])}

    cov_annotations_added = 0
    cov_not_found = 0
    cov_color = _coverage_color()

    for cov in coverage_assessment:
        disp = _resolve_display(cov, perspective)
        if disp["bucket"] not in ANNOTATED_BUCKETS:
            continue
        state = cov.get("coverage_state", "covered")
        if state == "missing":
            continue

        pid = cov.get("issue_area_id", "")
        if not pid:
            continue

        # Look up the provision so we can anchor on its tenant text / section ref
        prov = provisions_by_id.get(pid, {})
        anchor_text = (prov.get("tenant_text", "") or "").strip()
        section_ref = (prov.get("tenant_section_ref", "") or "").strip()
        # Step 254: Mode C runs without per-provision extraction in results[],
        # so fall back to the issue-area name and id. The name (e.g. "Force
        # Majeure", "Common Area Maintenance") and id (e.g. "LP-07") are
        # usually in section headers and readily anchor-able.
        issue_area_name = (cov.get("issue_area_name") or cov.get("provision_name") or "").strip()

        # Coverage resolution lookup mirrors the deviation pattern (tenant_idx 0)
        cov_resolution = None
        if cov_resolutions:
            cov_resolution = (
                cov_resolutions.get(f"cov:0:{pid}")
                or cov_resolutions.get(f"cov:{pid}")
            )

        comment_text = _sanitize_for_pdf(_format_coverage_annotation_text(cov, cov_resolution, perspective))

        # Try anchor text first, then section reference, then issue-area name, then id.
        # Mode A typically resolves on anchor_text; Mode C falls through to name/id.
        found = False
        fallback_candidates = [
            (anchor_text,       [80, 50, 30], 10),
            (section_ref,       [80, 50, 30], 10),
            (issue_area_name,   [60, 40, 20], 5),
            (pid,               [10],         3),
        ]
        for search_text, search_lengths, min_len in fallback_candidates:
            if found or not search_text:
                continue
            for search_len in search_lengths:
                if found:
                    break
                search_key = search_text[:search_len].strip()
                if not search_key or len(search_key) < min_len:
                    continue
                for page in doc:
                    text_instances = page.search_for(search_key)
                    if text_instances:
                        highlight = page.add_highlight_annot(text_instances)
                        highlight.set_colors(stroke=cov_color)
                        highlight.update()
                        note_point = fitz.Point(
                            text_instances[0].x0,
                            max(0, text_instances[0].y0 - 5),
                        )
                        annot = page.add_text_annot(note_point, comment_text)
                        annot.set_info(title="CAM \u2014 Coverage Gap")
                        annot.update()
                        cov_annotations_added += 1
                        found = True
                        break

        if not found:
            cov_not_found += 1
            print(f"[pdf_annotator] Could not anchor coverage gap for {pid}", flush=True)

    # Save annotated PDF
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # Step 485: incompleteness statement on a NEW PAGE ONE, inserted after all
    # annotation work so page indices used above (doc[0] for conflict notes, and the
    # `for page in doc` search loops) are untouched. A lawyer handed this PDF never
    # sees the web banner, so the artefact carries it.
    try:
        from cam.adapters.lease_review.lease_display import incomplete_report_lines
        _inc = incomplete_report_lines(results)
        if _inc:
            _bp = doc.new_page(0)
            _r = _bp.rect
            _bp.draw_rect(fitz.Rect(40, 40, _r.width - 40, 200),
                          color=(0.706, 0.137, 0.094), fill=(0.996, 0.953, 0.949), width=2)
            _y = 70
            _bp.insert_text(fitz.Point(56, _y), _sanitize_for_pdf(_inc[0]),
                            fontsize=15, fontname="hebo", color=(0.706, 0.137, 0.094))
            _y += 26
            for _line in _inc[1:]:
                for _chunk in _wrap_pdf_text(_sanitize_for_pdf(_line), 95):
                    _bp.insert_text(fitz.Point(56, _y), _chunk,
                                    fontsize=10, fontname="helv", color=(0.478, 0.153, 0.102))
                    _y += 14
                _y += 4
            print("[pdf_annotator] Inserted incomplete-report banner page", flush=True)
    except Exception as _be:
        print(f"[pdf_annotator] Banner page insertion failed (non-fatal): {_be}", flush=True)

    doc.save(output_path)
    doc.close()

    print(
        f"[pdf_annotator] Saved {output_path} "
        f"({annotations_added} deviations, {cov_annotations_added} coverage gaps, "
        f"{text_not_found + cov_not_found} not found)",
        flush=True,
    )

    return output_path
