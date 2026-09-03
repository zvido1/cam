"""
CAM Lease Review — Report Generator / Output Coordinator

Coordinates all output generation after pipeline completes:
- Always: results JSON (for dashboard)
- DOCX input: annotated DOCX with Word comments
- PDF input: annotated PDF with highlights + sticky notes
- TXT input: converted to PDF, then annotated with highlights + sticky notes
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF


def _sanitize_for_pdf(text: str) -> str:
    """Replace Unicode characters unsupported by base-14 PDF fonts."""
    replacements = {
        '\u2014': '--',   # em-dash
        '\u2013': '-',    # en-dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u00a0': ' ',    # non-breaking space
        '\u2022': '*',    # bullet
        '\u00b7': '*',    # middle dot
        '\u2010': '-',    # hyphen
        '\u2011': '-',    # non-breaking hyphen
        '\u2012': '-',    # figure dash
        '\u00ae': '(R)',  # registered sign
        '\u00a9': '(c)',  # copyright sign
        '\u2122': '(TM)', # trademark
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Strip markdown bold/italic markers - Helvetica won't render them and they
    # leak through into the Findings section on the annotated PDF cover page.
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    return text


def _convert_txt_to_pdf(text_content: str, output_dir: str, base_filename: str) -> Optional[Path]:
    """Convert plain text to a clean, readable PDF for annotation.

    Returns path to the generated PDF, or None on failure.
    """
    try:
        text_content = _sanitize_for_pdf(text_content)
        doc = fitz.open()  # new empty PDF

        # Page setup — Letter size
        page_width = 612
        page_height = 792
        margin = 72  # 1 inch
        font_size = 10
        line_height = 14
        usable_width = page_width - 2 * margin

        page = doc.new_page(width=page_width, height=page_height)
        y = margin

        for line in text_content.split("\n"):
            # Estimate lines this text will take (word-wrapped)
            if line.strip():
                # Approximate character width for Helvetica at 10pt
                chars_per_line = int(usable_width / (font_size * 0.5))
                wrapped_lines = max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                needed_height = line_height * (wrapped_lines + 0.5)
            else:
                needed_height = line_height

            # New page if needed
            if y + needed_height > page_height - margin:
                page = doc.new_page(width=page_width, height=page_height)
                y = margin

            if line.strip():
                rect = fitz.Rect(margin, y, page_width - margin, y + needed_height + line_height)
                rc = page.insert_textbox(
                    rect, line,
                    fontsize=font_size,
                    fontname="helv",
                    align=0,
                )
                # rc < 0 means text didn't fit; use estimated height regardless
                y += needed_height
            else:
                y += line_height  # blank line

        # Save
        stem = Path(base_filename).stem
        pdf_path = Path(output_dir) / f"{stem}_converted.pdf"
        doc.save(str(pdf_path))
        doc.close()

        print(f"[report_generator] Converted TXT to PDF: {pdf_path}", flush=True)
        return pdf_path

    except Exception as e:
        print(f"[report_generator] TXT→PDF conversion failed: {e}", flush=True)
        return None


def _build_summary_cover_pdf(results: dict, output_dir: str) -> Optional[Path]:
    """Build PDF summary cover page(s) with structured findings.

    Returns path to a temporary PDF with summary pages, or None on failure.
    """
    try:
        # Page setup
        W, H = 612, 792
        M = 60  # margin
        UW = W - 2 * M
        doc = fitz.open()

        page = doc.new_page(width=W, height=H)
        y = M

        def s(text):
            return _sanitize_for_pdf(text)

        def add_text(pg, x, cy, text, size=10, bold=False, color=(0, 0, 0)):
            fn = "hebo" if bold else "helv"
            rect = fitz.Rect(x, cy, W - M, cy + size * 2.5)
            chars_per_line = max(1, int(UW / (size * 0.5)))
            lines_needed = max(1, (len(text) + chars_per_line - 1) // chars_per_line)
            rect = fitz.Rect(x, cy, W - M, cy + size * 1.4 * lines_needed + 4)
            pg.insert_textbox(rect, s(text), fontsize=size, fontname=fn, color=color, align=0)
            return cy + size * 1.4 * lines_needed + 4

        def new_page_if_needed(cy, needed=60):
            nonlocal page
            if cy + needed > H - M:
                page = doc.new_page(width=W, height=H)
                return M
            return cy

        # Mode detection (Step 254). Mode C produces a coverage-first cover page.
        is_mode_c = results.get("mode") == "analyze"

        # -- Header --
        header_title = "CAM Coverage Analysis" if is_mode_c else "CAM Lease Analysis Report"
        y = add_text(page, M, y, header_title, size=18, bold=True, color=(0.1, 0.2, 0.36))
        y += 4
        tenant_file = results.get("tenant_file", "")
        date_str = datetime.now().strftime("%B %d, %Y")
        y = add_text(page, M, y, f"{date_str}  |  {tenant_file}", size=9, color=(0.4, 0.45, 0.55))
        y += 12

        # -- Contract Summary --
        meta = results.get("contract_metadata", {})
        fields = []
        for label, key in [("Landlord", "landlord"), ("Property", "property_description"),
                           ("Term", "term_length"), ("Base Rent", "base_rent"),
                           ("Tenant", "tenant"), ("Governing Law", "governing_law")]:
            val = meta.get(key, "")
            if val and len(str(val).replace("_", "").replace("TBD", "").strip()) >= 5:
                fields.append((label, str(val)))

        if fields:
            y = add_text(page, M, y, "Contract Summary", size=13, bold=True, color=(0.1, 0.2, 0.36))
            y += 2
            for label, val in fields:
                y = new_page_if_needed(y, 20)
                y = add_text(page, M, y, f"{label}: {val}", size=9)
            y += 10

        # -- Provisions Traffic Light --
        provisions = results.get("provisions", [])
        if provisions:
            y = new_page_if_needed(y, 40)
            y = add_text(page, M, y, "Provisions Analyzed", size=13, bold=True, color=(0.1, 0.2, 0.36))
            y += 4

            # Group by severity (traffic light style)
            sev_groups = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "CONFORMS": []}
            for p in provisions:
                if p.get("final_verdict") == "DEVIATES":
                    sev = p.get("severity", "MEDIUM")
                    if sev in sev_groups:
                        sev_groups[sev].append(p)
                    else:
                        sev_groups["MEDIUM"].append(p)
                else:
                    sev_groups["CONFORMS"].append(p)

            sev_colors = {
                "CRITICAL": (0.86, 0.15, 0.15),
                "HIGH": (0.76, 0.27, 0.05),
                "MEDIUM": (0.65, 0.47, 0.02),
                "LOW": (0.4, 0.45, 0.55),
                "CONFORMS": (0.09, 0.64, 0.29),
            }
            sev_labels = {
                "CRITICAL": "[!] CRITICAL",
                "HIGH": "[!] HIGH",
                "MEDIUM": "[*] MEDIUM",
                "LOW": "[-] LOW",
                "CONFORMS": "[OK] CONFORMS",
            }

            for sev_key in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CONFORMS"]:
                items = sev_groups[sev_key]
                if not items:
                    continue
                y = new_page_if_needed(y, 22)
                clr = sev_colors[sev_key]
                label = sev_labels[sev_key]
                names = ", ".join(f"{p.get('provision_id', '')} {p.get('provision_name', '').split(' ', 1)[-1] if p.get('provision_name') else ''}" for p in items)
                y = add_text(page, M, y, f"  {label}: {names}", size=8.5, color=clr)

                # Cross-reference warnings for CONFORMS provisions (Step 115)
                if sev_key == "CONFORMS":
                    for p in items:
                        xref = p.get("cross_reference_links")
                        if xref and xref.get("linked_deviations"):
                            for ld in xref["linked_deviations"]:
                                y = new_page_if_needed(y, 14)
                                xref_text = (
                                    f"    \u26A0 {p.get('provision_id', '')} depends on "
                                    f"[{ld.get('defined_term', '')}] -- see "
                                    f"{ld.get('deviating_provision', '')} "
                                    f"({ld.get('severity', '')}): {ld.get('summary', '')[:80]}"
                                )
                                y = add_text(page, M + 10, y, xref_text, size=7.5, color=(0.76, 0.27, 0.05))
            y += 10

        # -- Findings (Mode C: coverage-first) --
        if is_mode_c:
            from cam.adapters.lease_review.lease_display import (
                _resolve_display, resolve_perspective, resolve_sections,
            )
            perspective = resolve_perspective(results)
            coverage_assessment = results.get("coverage_assessment", []) or []

            # Bucket counts (for the summary line) — kept at bucket level
            # because the line is a quick-scan summary. Section structure
            # below is independent.
            attention_items = []
            favorable_items = []
            asymmetric_items = []
            review_items = []
            covered_count = 0
            not_assessed_items = []
            minor_gap_items = []
            for item in coverage_assessment:
                bucket = _resolve_display(item, perspective)["bucket"]
                if bucket == "needs_attention":
                    attention_items.append(item)
                elif bucket == "favorable_to_your_side":
                    favorable_items.append(item)
                elif bucket == "asymmetric_terms":
                    asymmetric_items.append(item)
                elif bucket == "worth_reviewing":
                    review_items.append(item)
                elif bucket == "minor_gaps":
                    # Step 539: MUST be its own branch. Without it these land in
                    # the else and the report says "18 covered" about a lease
                    # with zero LPs in state `covered`.
                    minor_gap_items.append(item)
                elif bucket == "not_assessed":
                    # Step 522: MUST be its own branch. The pre-522 `else` swept
                    # this into covered_count, which is how Step 521 measured a
                    # withheld verdict being reported as "covered".
                    not_assessed_items.append(item)
                else:
                    covered_count += 1

            y = new_page_if_needed(y, 60)
            y = add_text(page, M, y, "Findings", size=13, bold=True, color=(0.1, 0.2, 0.36))
            y += 4
            summary_parts = [f"{len(attention_items)} issue area(s) require attention"]
            if favorable_items:
                summary_parts.append(f"{len(favorable_items)} favorable term(s)")
            if asymmetric_items:
                summary_parts.append(f"{len(asymmetric_items)} asymmetric term(s)")
            summary_parts.append(f"{len(review_items)} worth reviewing")
            # Step 522: counted separately and named, never merged into "covered".
            if minor_gap_items:
                summary_parts.append(f"{len(minor_gap_items)} substantially addressed with minor gaps")
            if not_assessed_items:
                summary_parts.append(f"{len(not_assessed_items)} NOT ASSESSED")
            # Step 543: if callouts could not be placed beside their clause, say
            # so. Every finding is still listed below, so nothing is lost -- but a
            # reader working through the marked-up document clause by clause would
            # otherwise never learn that some findings have no margin note. Only
            # rendered when it actually happened; silent otherwise.
            _ann = (results.get("annotation_reports") or {})
            _drops = []
            for _k in ("pdf", "docx"):
                for _d in (_ann.get(_k) or {}).get("anchor_drops", []):
                    if _d.get("lp_id") and _d["lp_id"] not in _drops:
                        _drops.append(_d["lp_id"])
            if _drops:
                y = new_page_if_needed(y, 26)
                y = add_text(
                    page, M, y,
                    "Note: %d finding(s) below could not be placed beside a clause in the "
                    "marked-up document and appear in this summary only: %s."
                    % (len(_drops), ", ".join(_drops)),
                    size=8.5, color=(0.28, 0.33, 0.40),
                )
            summary_parts.append(f"{covered_count} covered.")
            y = add_text(
                page, M, y,
                ", ".join(summary_parts),
                size=10, bold=True, color=(0.1, 0.2, 0.36),
            )
            y += 6

            mat_order = {"high": 0, "medium": 1, "low": 2}

            # Note: add_text is closed over `page`, not parameterised, so that
            # callers following new_page_if_needed (which rebinds `page` via
            # nonlocal) always write to the current page.
            def _render_coverage_item(cy, item, tier_color):
                from cam.adapters.lease_review.lease_display import extract_headline as _eh
                pid = item.get("issue_area_id", "")
                # Step 279: prefer issue_area_name over provision_name
                # (which is None in Mode C, used to fall through to
                # issue_area_id and produce a doubled LP id in the
                # header).
                pname = (item.get("provision_name")
                         or item.get("issue_area_name")
                         or pid)
                exposure = item.get("exposure_statement", "")
                missing_els = item.get("elements_missing", [])
                # Step 278: headline integrated into the header line.
                headline = (item.get("exposure_headline") or "").strip()
                if not headline and exposure:
                    headline = _eh(exposure)

                # Step 279: single-line item header. Marker carries
                # severity, the section bucket header above carries
                # category — so the per-item state label is dropped.
                #
                # Step 522 EXCEPTION: the "Not Assessed" section holds two
                # different facts — never judged, and judged-then-discarded — so
                # its header cannot carry the category for both. The per-item
                # label comes back for these, and ONLY these.
                _astatus = item.get("assessment_status") or "unset"
                if _astatus != "assessed":
                    _albl = {
                        "not_assessed": "NOT ASSESSED",
                        "suppressed":   "ASSESSMENT DISCARDED",
                    }.get(_astatus, "ASSESSMENT STATUS NOT RECORDED")
                    cy = new_page_if_needed(cy, 30)
                    cy = add_text(page, M, cy, f"{pid} {pname}  [{_albl}]",
                                  size=10, bold=True, color=tier_color)
                    # The schema's exposure prose and expected-element list are
                    # NOT printed here. On an entry nobody judged they are
                    # boilerplate, and printing "Missing: <six elements>" would
                    # assert a finding no evaluator produced -- the R4/R5 defect
                    # Step 521 named. The reason is printed instead.
                    _why = {
                        "not_assessed": "No evaluation was performed for this provision.",
                        "suppressed":   "An evaluation was attempted and its result was discarded; "
                                        "the state shown elsewhere does not rest on it.",
                    }.get(_astatus,
                          "The stage that produced this entry did not record whether it was evaluated.")
                    cy = new_page_if_needed(cy, 20)
                    cy = add_text(page, M + 10, cy, _why, size=8.5, color=(0.28, 0.33, 0.40))
                    return cy
                if headline:
                    header_text = f"{pid} {pname} — {headline}"
                else:
                    header_text = f"{pid} {pname}"
                cy = new_page_if_needed(cy, 30)
                cy = add_text(page, M, cy, header_text,
                              size=10, bold=True, color=tier_color)
                if missing_els:
                    missing_str = ", ".join(str(e) for e in missing_els[:5])
                    cy = new_page_if_needed(cy, 20)
                    cy = add_text(page, M + 10, cy, f"Missing: {missing_str}",
                                  size=8.5, color=(0.45, 0.47, 0.52))
                if exposure:
                    cy = new_page_if_needed(cy, 30)
                    cy = add_text(page, M + 10, cy, exposure, size=9)

                # ── Step 524: qualifier annotations ───────────────────────────
                # An ANNOTATION, not a verdict, and it has to read as one. Slate,
                # never a tier colour; prefixed "NOT WEIGHED"; and the sentence
                # says what the panel did NOT do. It asserts only that the clause
                # exists and was absent from this finding's evidence -- never that
                # it limits the finding, which nobody has judged.
                for _qa in (item.get("qualifier_annotations") or [])[:3]:
                    _ref = _qa.get("section_ref") or "elsewhere in the lease"
                    cy = new_page_if_needed(cy, 16)
                    cy = add_text(
                        page, M + 10, cy,
                        f"NOT WEIGHED - {_ref} was not part of the evidence for this "
                        f"finding and was not judged by the evaluators:",
                        size=8.5, bold=True, color=(0.28, 0.33, 0.40),
                    )
                    cy = new_page_if_needed(cy, 24)
                    cy = add_text(page, M + 20, cy, '"%s"' % _qa.get("quote", ""),
                                  size=8.5, color=(0.28, 0.33, 0.40))

                # Lawyer's coverage resolution (same lookup key as PDF annotator)
                cov_resolutions = results.get("cov_resolutions") or {}
                cov_res = (
                    cov_resolutions.get(f"cov:0:{pid}")
                    or cov_resolutions.get(f"cov:{pid}")
                    or {}
                )
                cov_notes = []
                for n in (cov_res.get("notes") or []):
                    text = n.get("text", "") if isinstance(n, dict) else str(n)
                    if text:
                        cov_notes.append(text)
                if cov_res.get("status") or cov_notes:
                    cy = new_page_if_needed(cy, 16)
                    status_labels = {
                        "accepted": "Accepted as-is",
                        "needs_negotiation": "Needs Negotiation",
                        "not_applicable": "Not Applicable",
                        "resolved": "Resolved",
                    }
                    status = cov_res.get("status", "")
                    if status:
                        cy = add_text(page, M + 10, cy,
                                      f"Attorney decision: {status_labels.get(status, status)}",
                                      size=8.5, color=(0.1, 0.2, 0.36))
                    for note_text in cov_notes:
                        cy = new_page_if_needed(cy, 16)
                        cy = add_text(page, M + 10, cy, f"Note: {note_text}",
                                      size=8.5, color=(0.1, 0.2, 0.36))

                return cy + 6

            # Step 275: section-level rendering via `resolve_sections`.
            # Tenant runs see "Coverage & Gaps" only (single section);
            # Landlord runs see "Asymmetric Provisions in Your Favor" then
            # "Coverage & Gaps"; Neutral runs see "Asymmetric Provisions"
            # then "Coverage & Gaps". Empty sections are filtered upstream.
            # The "Covered" tail is intentionally omitted from the cover
            # because the bucket-level summary line above already counts
            # covered items.
            sections = [
                s for s in resolve_sections(coverage_assessment, perspective)
                if s["key"] != "covered"
            ]
            section_colors = {
                "asymmetric_favor": (0.09, 0.64, 0.29),  # green
                "asymmetric":       (0.49, 0.23, 0.93),  # purple
                "coverage_gaps":    (0.76, 0.27, 0.05),  # red/orange
                # Step 522: slate, NOT the red/orange default. The PDF colours by
                # section tier; letting this fall through to the gaps colour would
                # render an unjudged entry as a finding, which is the opposite
                # error from rendering it as covered but still a false claim.
                "not_assessed":     (0.28, 0.33, 0.40),  # slate
                "minor_gaps":       (0.85, 0.47, 0.02),  # amber
            }
            for section in sections:
                tier_color = section_colors.get(section["key"], (0.76, 0.27, 0.05))
                y = new_page_if_needed(y, 30)
                y = add_text(page, M, y, section["title"], size=11, bold=True, color=tier_color)
                if section.get("intro"):
                    y = new_page_if_needed(y, 16)
                    y = add_text(page, M, y, section["intro"], size=8.5,
                                 color=(0.45, 0.47, 0.52))
                # Sort items inside the section: high materiality first
                section_items = sorted(
                    [pair[0] for pair in section["items"]],
                    key=lambda it: mat_order.get(it.get("materiality", "medium"), 1),
                )
                for item in section_items:
                    y = _render_coverage_item(y, item, tier_color)

            # Step 312: Contract Interaction Review section (Stage 7 findings)
            cpfs = results.get("cross_provision_findings") or []
            if cpfs:
                # Sort: directional_mismatch → compound_risk → cross_coverage_gap,
                # then within each type by agreement (3-0 first).
                _type_order = {"directional_mismatch": 0, "compound_risk": 1, "cross_coverage_gap": 2}
                def _agree_sort(f):
                    ag = f.get("evaluator_agreement", "")
                    if ag.startswith("3"):
                        return 0
                    if ag.startswith("2"):
                        return 1
                    return 2
                cpfs_sorted = sorted(cpfs, key=lambda f: (_type_order.get(f.get("finding_type", ""), 9), _agree_sort(f)))

                y = new_page_if_needed(y, 40)
                _syn_color = (0.11, 0.27, 0.53)  # dark indigo
                y = add_text(page, M, y, "CONTRACT INTERACTION REVIEW", size=11, bold=True, color=_syn_color)
                y += 2
                y = add_text(page, M, y,
                    "How provisions interact across the document — findings that only appear when the lease is read as a whole.",
                    size=8.5, color=(0.45, 0.47, 0.52))
                y += 6

                _ftype_labels = {
                    "directional_mismatch": "DIRECTIONAL MISMATCH",
                    "compound_risk":        "COMPOUND RISK",
                    "cross_coverage_gap":   "CROSS-COVERAGE GAP",
                }
                _ftype_colors = {
                    "directional_mismatch": (0.76, 0.10, 0.10),
                    "compound_risk":        (0.65, 0.30, 0.00),
                    "cross_coverage_gap":   (0.30, 0.32, 0.38),
                }
                for cpf in cpfs_sorted:
                    ftype   = cpf.get("finding_type", "cross_coverage_gap")
                    fcolor  = _ftype_colors.get(ftype, (0.30, 0.32, 0.38))
                    flabel  = _ftype_labels.get(ftype, ftype.upper())
                    lps     = ", ".join(cpf.get("implicated_lps") or [])
                    headline= (cpf.get("headline") or "").strip()
                    detail  = (cpf.get("detail") or "").strip()
                    cited   = ", ".join(cpf.get("cited_sections") or [])
                    direc   = cpf.get("directionality")
                    agree   = cpf.get("evaluator_agreement", "")
                    sev     = (cpf.get("severity") or "").upper()

                    y = new_page_if_needed(y, 30)
                    header_parts = [flabel]
                    if lps:
                        header_parts.append(f"[{lps}]")
                    if sev:
                        header_parts.append(f"[{sev}]")
                    y = add_text(page, M, y, "  ".join(header_parts), size=9, bold=True, color=fcolor)
                    if headline:
                        y = new_page_if_needed(y, 16)
                        y = add_text(page, M + 10, y, headline, size=9, bold=True)
                    if detail:
                        y = new_page_if_needed(y, 16)
                        y = add_text(page, M + 10, y, detail, size=8.5)
                    if ftype == "directional_mismatch" and direc:
                        y = new_page_if_needed(y, 14)
                        dir_note = direc.replace("_", " ").title()
                        y = add_text(page, M + 10, y, f"Directionality: {dir_note}", size=8, color=fcolor)
                    if cited:
                        y = new_page_if_needed(y, 14)
                        y = add_text(page, M + 10, y, f"Cited sections: {cited}", size=8, color=(0.45, 0.47, 0.52))
                    if agree:
                        parts = agree.split("-")
                        total = sum(int(p) for p in parts if p.isdigit())
                        majority = parts[0] if parts else agree
                        y = new_page_if_needed(y, 14)
                        y = add_text(page, M + 10, y, f"Evaluator agreement: {majority} of {total} evaluators identified this finding.", size=8, color=(0.45, 0.47, 0.52))
                    y += 5

            # Skip the deviation findings block below when Mode C
            deviations = []
        else:
            deviations = [p for p in provisions if p.get("final_verdict") == "DEVIATES"]
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        deviations.sort(key=lambda d: sev_order.get(d.get("severity", "LOW"), 99))

        if deviations:
            y = new_page_if_needed(y, 60)
            y = add_text(page, M, y, "Findings", size=13, bold=True, color=(0.1, 0.2, 0.36))
            y += 4

            for d in deviations:
                y = new_page_if_needed(y, 80)
                pid = d.get("provision_id", "")
                pname = d.get("provision_name", "")
                sev = d.get("severity", "")
                headline = d.get("risk_headline", "")
                what_changed = d.get("challenge_details", d.get("what_changed", ""))
                impact = d.get("severity_reasoning", "")
                financial = d.get("financial_impact", "")
                action = d.get("recommended_action", "")
                cascade_src = d.get("cascade_source")
                action_labels = {
                    "note_for_awareness": "Note for awareness",
                    "attorney_review_recommended": "Attorney review recommended",
                    "attorney_review_required": "Attorney review required",
                }
                action_text = action_labels.get(action, action)

                # Agreement line
                verdicts = d.get("evaluator_verdicts", {})
                agreeing = sum(1 for v in verdicts.values() if v == "DEVIATES")
                total = len(verdicts) or 3
                agreement = f"{agreeing}/{total} evaluators agree"

                # Severity color
                sev_clr = (0.86, 0.15, 0.15) if sev == "CRITICAL" else (0.76, 0.27, 0.05) if sev == "HIGH" else (0.65, 0.47, 0.02) if sev == "MEDIUM" else (0.4, 0.45, 0.55)

                # Render finding block
                y = add_text(page, M, y, f"{pid} {pname}  [{sev}]  ({agreement})", size=10, bold=True, color=sev_clr)

                # Cascade source (if present)
                if cascade_src and cascade_src.get("term"):
                    y = new_page_if_needed(y, 18)
                    cs_text = f"Definition cascade from: \"{cascade_src['term']}\""
                    if cascade_src.get("defined_in"):
                        cs_text += f" -- {cascade_src['defined_in']}"
                    y = add_text(page, M + 10, y, cs_text, size=8.5, color=(0.65, 0.47, 0.02))

                if headline:
                    y = new_page_if_needed(y, 20)
                    y = add_text(page, M + 10, y, headline, size=9, bold=True, color=sev_clr)
                if what_changed:
                    y = new_page_if_needed(y, 30)
                    y = add_text(page, M + 10, y, f"What Changed: {what_changed}", size=9)
                if impact:
                    y = new_page_if_needed(y, 30)
                    y = add_text(page, M + 10, y, f"Impact: {impact}", size=9)
                if financial:
                    y = new_page_if_needed(y, 30)
                    y = add_text(page, M + 10, y, f"Financial Impact: {financial}", size=9)
                if action_text and action_text != "no_action":
                    y = new_page_if_needed(y, 20)
                    y = add_text(page, M + 10, y, f"Recommended Action: {action_text}", size=9, color=(0.1, 0.2, 0.36))
                y += 8

        # -- Disclaimer --
        # Step 277: Mode A uses the multi-evaluator adjudication pipeline;
        # Mode C uses a single-model coverage layer. Pick the phrasing
        # that matches what actually generated this run.
        y = new_page_if_needed(y, 60)
        y += 10
        page.draw_line(fitz.Point(M, y), fitz.Point(W - M, y), color=(0.8, 0.82, 0.85))
        y += 8
        if is_mode_c:
            disclaimer = (
                "This analysis was generated by CAM's coverage analysis layer. "
                "It is intended as a review aid, not legal advice. All findings should "
                "be verified by qualified legal counsel before any action is taken."
            )
        else:
            disclaimer = (
                "This analysis was generated by the CAM (Constrained Assertion Method) system using multiple "
                "independent AI evaluators. It is intended as a review aid, not legal advice. All findings should "
                "be verified by qualified legal counsel before any action is taken."
            )
        y = add_text(page, M, y, disclaimer, size=7.5, color=(0.55, 0.58, 0.62))

        # Save temporary PDF
        cover_path = Path(output_dir) / "_summary_cover.pdf"
        doc.save(str(cover_path))
        doc.close()
        print(f"[report_generator] Summary cover page built: {cover_path}", flush=True)
        return cover_path

    except Exception as e:
        print(f"[report_generator] Summary cover page failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


def _prepend_cover_to_pdf(cover_path: str, annotated_path: str):
    """Prepend summary cover pages to the annotated PDF in-place."""
    try:
        cover_doc = fitz.open(cover_path)
        main_doc = fitz.open(annotated_path)
        cover_page_count = cover_doc.page_count

        # Insert cover pages at the beginning (start_at=0 means before page 0)
        main_doc.insert_pdf(cover_doc, start_at=0)

        main_doc.saveIncr()
        main_doc.close()
        cover_doc.close()
        print(f"[report_generator] Prepended {cover_page_count} cover page(s) to {annotated_path}", flush=True)
    except Exception as e:
        print(f"[report_generator] Failed to prepend cover: {e}", flush=True)


def generate_outputs(
    tenant_file_path: str,
    results: dict,
    output_dir: str,
) -> dict:
    """Generate all output files for a completed analysis.

    Args:
        tenant_file_path: Path to the original uploaded tenant file.
        results: Full pipeline results dict.
        output_dir: Directory to write output files into.

    Returns:
        Dict with paths and summary:
        {
            "dashboard_json": "path/to/results.json",
            "annotated_document": "path/to/annotated.docx or .pdf" or None,
            "annotation_method": "docx_comments" | "pdf_highlights" | "none",
            "summary": { ... summary stats ... }
        }
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Always produce the dashboard JSON
    json_path = os.path.join(output_dir, "pipeline_results.json")
    # (JSON is already saved by lease_adapter.py, but we track the path)

    output_info = {
        "dashboard_json": json_path,
        "annotated_document": None,
        "annotation_method": "none",
        "comparison_view_pdf": None,  # Step 255: Aligned Provision Comparison (Mode A only)
        "summary": results.get("summary", {}),
    }

    # Detect input format
    ext = Path(tenant_file_path).suffix.lower()

    # Coverage resolutions ride alongside results; mirror the cover-page lookup.
    cov_resolutions = results.get("cov_resolutions") or {}

    if ext == ".docx":
        try:
            from cam.adapters.lease_review.lease_docx_annotator import annotate_docx
            annotated_name = Path(tenant_file_path).stem + "_annotated.docx"
            annotated_path = os.path.join(output_dir, annotated_name)
            annotate_docx(tenant_file_path, results, annotated_path,
                          cov_resolutions=cov_resolutions)
            output_info["annotated_document"] = annotated_path
            output_info["annotation_method"] = "docx_comments"
        except Exception as e:
            print(f"[report_generator] DOCX annotation failed: {e}", flush=True)
            output_info["annotation_error"] = str(e)

    elif ext == ".pdf":
        try:
            from cam.adapters.lease_review.lease_pdf_annotator import annotate_pdf
            annotated_name = Path(tenant_file_path).stem + "_annotated.pdf"
            annotated_path = os.path.join(output_dir, annotated_name)
            annotate_pdf(tenant_file_path, results, annotated_path,
                         cov_resolutions=cov_resolutions)
            output_info["annotated_document"] = annotated_path
            output_info["annotation_method"] = "pdf_highlights"
        except Exception as e:
            print(f"[report_generator] PDF annotation failed: {e}", flush=True)
            output_info["annotation_error"] = str(e)

    elif ext == ".txt":
        try:
            print("[report_generator] TXT input — converting to PDF for annotation...", flush=True)
            # Read the original text
            txt_content = Path(tenant_file_path).read_text(encoding="utf-8", errors="replace")
            # Convert to a clean PDF
            converted_pdf = _convert_txt_to_pdf(txt_content, output_dir, Path(tenant_file_path).name)
            if converted_pdf:
                # Annotate the converted PDF using existing PDF annotator
                from cam.adapters.lease_review.lease_pdf_annotator import annotate_pdf
                annotated_name = Path(tenant_file_path).stem + "_annotated.pdf"
                annotated_path = os.path.join(output_dir, annotated_name)
                annotate_pdf(str(converted_pdf), results, annotated_path,
                             cov_resolutions=cov_resolutions)
                output_info["annotated_document"] = annotated_path
                output_info["annotation_method"] = "pdf_highlights"
                # Clean up intermediate converted PDF
                try:
                    converted_pdf.unlink()
                except Exception:
                    pass
        except Exception as e:
            print(f"[report_generator] TXT→PDF annotation failed: {e}", flush=True)
            output_info["annotation_error"] = str(e)

    else:
        print(f"[report_generator] Unsupported format '{ext}' — no document annotation", flush=True)

    # Prepend summary cover page(s) to PDF outputs
    annotated = output_info.get("annotated_document")
    if annotated and annotated.endswith(".pdf"):
        cover_path = _build_summary_cover_pdf(results, output_dir)
        if cover_path:
            _prepend_cover_to_pdf(str(cover_path), annotated)
            try:
                cover_path.unlink()
            except Exception:
                pass

    # ── Step 255: Aligned Provision Comparison View PDF (Mode A only) ──
    # Additive fourth Mode A artifact alongside Synopsis, annotated PDF, DOCX.
    # Skipped automatically for Mode C (build_aligned_comparison_pdf returns
    # None when results['mode'] == 'analyze'). Failure is non-fatal — the
    # other artifacts ship regardless.
    try:
        from cam.adapters.lease_review.lease_comparison_view import (
            build_aligned_comparison_pdf,
        )
        comparison_path = build_aligned_comparison_pdf(results, output_dir)
        if comparison_path:
            output_info["comparison_view_pdf"] = str(comparison_path)
    except Exception as e:
        print(
            f"[report_generator] Aligned Provision Comparison PDF failed (non-fatal): {e}",
            flush=True,
        )

    return output_info
