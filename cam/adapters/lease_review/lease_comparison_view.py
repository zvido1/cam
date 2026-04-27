"""
CAM Lease Review — Aligned Provision Comparison View Renderer (Step 255)

Builds a Mode A PDF artifact that presents template clause text and tenant
clause text in sequential alternating blocks, per provision. Consumes the
existing pipeline output (results dict) without modifying any pipeline stage.

Four content rules enforced:
  1. Multi-segment concatenation with visible dividers
  2. Missing-side handling (italic, labeled, visually distinct)
  3. Pagination continuation with `(continued)` provision headers
  4. CUSTOM placement using existing discovery metadata or a catch-all section

Output filename: Aligned_Provision_Comparison.pdf

Forward-compatibility: the renderer takes an internally-built list of dicts of
shape {provision_id, name, template_text, tenant_text, template_section_ref,
tenant_section_ref, is_custom}. A future column-variant function could consume
the same intermediate list and emit columns instead of blocks.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF


# ── Page geometry (US Letter) ──
W, H = 612, 792
M = 60                          # outer margin
UW = W - 2 * M                  # usable width
INDENT = 14                     # subblock indent

# ── Colors ──
HEADER_COLOR = (0.10, 0.20, 0.36)
SUBLABEL_COLOR = (0.20, 0.28, 0.40)
BODY_COLOR = (0.12, 0.14, 0.18)
RULE_COLOR = (0.78, 0.80, 0.84)
DIVIDER_COLOR = (0.55, 0.58, 0.62)
SECTION_LABEL_COLOR = (0.40, 0.45, 0.55)

MISSING_BG = (1.000, 0.965, 0.870)        # warm tint
MISSING_BORDER = (0.85, 0.55, 0.05)
MISSING_TEXT = (0.55, 0.35, 0.02)

# ── Fonts (PyMuPDF base-14) ──
FONT_REG = "helv"
FONT_BOLD = "hebo"
FONT_ITALIC = "heit"
FONT_BOLD_ITALIC = "hebi"

# ── Sizes ──
SIZE_DOC_TITLE = 16
SIZE_DOC_SUB = 9
SIZE_PROV_HEADER = 13
SIZE_SUBLABEL = 10
SIZE_BODY = 9.5
SIZE_DIVIDER = 8.5
LINE_GAP = 1.35                 # multiplier on font size for line height


def _sanitize(text: str) -> str:
    """Replace Unicode characters unsupported by base-14 PDF fonts."""
    if not text:
        return ""
    replacements = {
        '—': '--', '–': '-', '‘': "'", '’': "'",
        '“': '"', '”': '"', '…': '...', ' ': ' ',
        '•': '*', '·': '*', '‐': '-', '‑': '-',
        '‒': '-', '®': '(R)', '©': '(c)', '™': '(TM)',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    return text


def _wrap_text(text: str, font_size: float, usable_width: float) -> List[str]:
    """Hard-wrap text into a list of lines, preserving paragraph breaks.

    Uses a simple greedy word-fill. Empty input lines become empty output
    lines (paragraph spacing).
    """
    max_chars = max(20, int(usable_width / (font_size * 0.50)))
    out: List[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            out.append("")
            continue
        words = line.split(" ")
        cur = ""
        for w in words:
            if len(w) > max_chars:
                if cur:
                    out.append(cur)
                    cur = ""
                while len(w) > max_chars:
                    out.append(w[:max_chars])
                    w = w[max_chars:]
                cur = w
                continue
            candidate = (cur + " " + w).strip() if cur else w
            if len(candidate) <= max_chars:
                cur = candidate
            else:
                if cur:
                    out.append(cur)
                cur = w
        if cur:
            out.append(cur)
    return out


def _has_text(s: Optional[str]) -> bool:
    return bool(s and re.sub(r'\s+', '', s))


# ── Multi-segment detection ──

_SECTION_HEADER_RE = re.compile(
    r'^\s*[\[\(]?\s*'
    r'(?:section|sec\.?|article|art\.?)\s+'
    r'([0-9IVX]+(?:\.[0-9A-Za-z\-]+)*)'
    r'\s*[\)\]]?\s*[:\-—]?\s*$',
    re.IGNORECASE,
)


def _split_into_segments(text: str) -> List[Tuple[Optional[str], str]]:
    """Detect explicit segment boundaries inside a body string.

    Recognized boundaries: lines that look like section headers (e.g.,
    'Section 8.2:', '[Section 8.2]', 'Article XII'). Returns
    [(section_ref_or_None, body_text), ...]. If no boundaries are found,
    returns [(None, text)] — i.e., a single segment.

    This is conservative: it only splits when an explicit divider is present
    in the extracted text. We never invent segment boundaries from paragraph
    breaks alone, because those are already part of legitimate clause prose.
    """
    if not text:
        return []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments: List[Tuple[Optional[str], List[str]]] = []
    current_ref: Optional[str] = None
    current_lines: List[str] = []
    found_any_divider = False

    for line in lines:
        m = _SECTION_HEADER_RE.match(line)
        if m and (current_lines or segments):
            found_any_divider = True
            if any(s.strip() for s in current_lines):
                segments.append((current_ref, current_lines))
            current_ref = m.group(1)
            current_lines = []
        else:
            current_lines.append(line)
    if any(s.strip() for s in current_lines):
        segments.append((current_ref, current_lines))

    if not found_any_divider:
        return [(None, text.strip())]

    return [(ref, "\n".join(ls).strip()) for ref, ls in segments if any(s.strip() for s in ls)]


# ── Layout primitives ──

class _Layout:
    """Mutable layout state. Owns the doc, current page, and y cursor."""

    def __init__(self):
        self.doc = fitz.open()
        self.page = self.doc.new_page(width=W, height=H)
        self.y = M
        self._continuation_header: Optional[str] = None  # provision header text for `(continued)` repeat

    # Each *time we start a new page mid-provision* we want a continuation
    # header at the top. set_continuation() arms that; clear_continuation()
    # disarms once the provision finishes.
    def set_continuation(self, header_text: str):
        self._continuation_header = header_text

    def clear_continuation(self):
        self._continuation_header = None

    def _new_page(self):
        self.page = self.doc.new_page(width=W, height=H)
        self.y = M
        if self._continuation_header:
            self._render_continuation_header(self._continuation_header)

    def _render_continuation_header(self, text: str):
        body = f"{text} (continued)"
        rect = fitz.Rect(
            M, self.y, W - M,
            self.y + SIZE_PROV_HEADER * LINE_GAP + SIZE_PROV_HEADER + 4,
        )
        self.page.insert_textbox(
            rect, _sanitize(body),
            fontsize=SIZE_PROV_HEADER, fontname=FONT_BOLD,
            color=HEADER_COLOR, align=0,
        )
        self.y += SIZE_PROV_HEADER * LINE_GAP + 2
        # Thin rule under the continuation header
        self.page.draw_line(
            fitz.Point(M, self.y),
            fitz.Point(W - M, self.y),
            color=RULE_COLOR, width=0.6,
        )
        self.y += 8

    def need(self, required: float, allow_break: bool = True):
        """Ensure `required` points of vertical room. New page if needed."""
        if self.y + required > H - M:
            if allow_break:
                self._new_page()

    def y_remaining(self) -> float:
        return (H - M) - self.y

    # ── Drawing helpers ──

    def draw_line(self, color=RULE_COLOR, width: float = 0.6, gap_above: float = 4, gap_below: float = 6):
        self.y += gap_above
        self.need(2)
        self.page.draw_line(
            fitz.Point(M, self.y), fitz.Point(W - M, self.y),
            color=color, width=width,
        )
        self.y += gap_below

    def draw_text(
        self,
        text: str,
        size: float = SIZE_BODY,
        font: str = FONT_REG,
        color=BODY_COLOR,
        x: float = M,
        right: float = W - M,
        align: int = 0,
    ):
        """Render a single short text snippet (no wrapping). Caller controls
        sizing via `need(...)` ahead of time. The rect is intentionally given
        ~size points of slack — PyMuPDF's insert_textbox returns a negative
        value (drops the text) when the rect height is too tight relative to
        font size. Slack is wasted whitespace, dropped text is silent failure;
        we pick the safe direction."""
        if not text:
            return
        line_h = size * LINE_GAP
        rect = fitz.Rect(x, self.y, right, self.y + line_h + size + 4)
        self.page.insert_textbox(
            rect, _sanitize(text),
            fontsize=size, fontname=font, color=color, align=align,
        )
        self.y += line_h

    def draw_wrapped_body(
        self,
        text: str,
        size: float = SIZE_BODY,
        font: str = FONT_REG,
        color=BODY_COLOR,
        x: float = M + INDENT,
        right: float = W - M,
        bottom_margin: float = 4,
    ):
        """Render long body text, wrapping line-by-line and paginating with the
        continuation header at the top of each new page."""
        if not text:
            return
        usable = right - x
        lines = _wrap_text(_sanitize(text), size, usable)
        line_h = size * LINE_GAP
        for line in lines:
            if self.y + line_h > H - M - bottom_margin:
                self._new_page()
                # On the new page, leave indent in place; continuation header
                # has already been rendered by _new_page().
            if line == "":
                # Paragraph spacing — half a line of empty space.
                self.y += line_h * 0.55
                continue
            rect = fitz.Rect(x, self.y, right, self.y + line_h + size + 2)
            self.page.insert_textbox(
                rect, line,
                fontsize=size, fontname=font, color=color, align=0,
            )
            self.y += line_h

    def draw_missing_block(self, side_label: str, body: str):
        """Render a visually-distinct missing-side block.

        Layout: warm-tint background rect with a thicker left border, italic
        text inside, bold-italic prefix ('Missing in X:'), followed by a short
        factual statement. Wraps and paginates correctly.
        """
        size = SIZE_BODY
        line_h = size * LINE_GAP
        x_left = M + INDENT
        x_right = W - M
        text_x = x_left + 10
        usable = x_right - text_x - 6

        # Combine prefix + body into one logical paragraph for wrapping.
        prefix = f"{side_label}: "
        sanitized_body = _sanitize(body)
        wrapped = _wrap_text(prefix + sanitized_body, size, usable)

        # Pre-compute total height so we can draw a fitting background even
        # if it overflows to a new page (we'll draw per-segment per-page).
        i = 0
        n = len(wrapped)
        while i < n:
            # How many lines fit on the current page?
            available = max(0, (H - M) - self.y - 6)
            max_lines_here = max(1, int(available // line_h))
            chunk = wrapped[i: i + max_lines_here]
            if not chunk:
                self._new_page()
                continue

            block_h = line_h * len(chunk) + 8
            top = self.y
            bg_rect = fitz.Rect(x_left, top, x_right, top + block_h)
            # Background tint
            self.page.draw_rect(bg_rect, color=None, fill=MISSING_BG, width=0)
            # Left border accent
            self.page.draw_line(
                fitz.Point(x_left, top + 2),
                fitz.Point(x_left, top + block_h - 2),
                color=MISSING_BORDER, width=2.4,
            )

            # Render text — first chunk gets bold-italic prefix; rest is italic.
            cursor_y = top + 4
            for k, line in enumerate(chunk):
                rect = fitz.Rect(
                    text_x, cursor_y, x_right - 6,
                    cursor_y + line_h + size + 2,
                )
                if i == 0 and k == 0 and line.startswith(side_label):
                    # Split the line into bold prefix + italic remainder
                    self.page.insert_textbox(
                        rect, side_label + ":",
                        fontsize=size, fontname=FONT_BOLD_ITALIC,
                        color=MISSING_TEXT, align=0,
                    )
                    # Approximate width of the prefix to position the remainder
                    # next to it. base-14 Helvetica ~0.5 char width.
                    prefix_text = side_label + ": "
                    prefix_width = len(prefix_text) * size * 0.50
                    rest = line[len(side_label) + 1:].lstrip()
                    if rest:
                        rect2 = fitz.Rect(
                            text_x + prefix_width, cursor_y,
                            x_right - 6, cursor_y + line_h + size + 2,
                        )
                        self.page.insert_textbox(
                            rect2, rest,
                            fontsize=size, fontname=FONT_ITALIC,
                            color=MISSING_TEXT, align=0,
                        )
                else:
                    self.page.insert_textbox(
                        rect, line,
                        fontsize=size, fontname=FONT_ITALIC,
                        color=MISSING_TEXT, align=0,
                    )
                cursor_y += line_h

            self.y = top + block_h
            i += len(chunk)
            if i < n:
                self._new_page()

    def draw_segment_divider(self, label: Optional[str]):
        """Render a centered divider between concatenated segments."""
        size = SIZE_DIVIDER
        self.need(size * LINE_GAP * 1.6 + 4)
        text = "[ ... ]" if not label else f"[ ... {label} ... ]"
        line_h = size * LINE_GAP
        # Spacer before
        self.y += line_h * 0.4
        rect = fitz.Rect(M + INDENT, self.y, W - M, self.y + line_h + size + 2)
        self.page.insert_textbox(
            rect, _sanitize(text),
            fontsize=size, fontname=FONT_ITALIC, color=DIVIDER_COLOR, align=1,
        )
        self.y += line_h
        # Spacer after
        self.y += line_h * 0.4


# ── Per-provision rendering ──

def _render_provision(layout: _Layout, item: Dict):
    """Render one provision block (template + tenant in alternating blocks).

    `item` is a dict shaped like:
      {
        "provision_id":         str,
        "provision_name":       str,
        "template_text":        str,
        "tenant_text":          str,
        "template_section_ref": str,
        "tenant_section_ref":   str,
        "is_custom":            bool,
      }
    """
    pid = item.get("provision_id", "")
    pname = item.get("provision_name", "")
    template_text = item.get("template_text", "") or ""
    tenant_text = item.get("tenant_text", "") or ""
    tpl_ref = item.get("template_section_ref", "") or ""
    tnt_ref = item.get("tenant_section_ref", "") or ""
    is_custom = bool(item.get("is_custom"))

    header_text = f"{pid}. {pname}".strip(". ")

    # Disarm continuation while we draw the *initial* header (the continuation
    # header is only for subsequent pages of the same provision body). Then
    # ensure enough room — if we break now, no continuation has been armed,
    # so the new page comes up clean.
    layout.clear_continuation()
    layout.need(SIZE_PROV_HEADER * LINE_GAP + SIZE_SUBLABEL * LINE_GAP + 36, allow_break=True)

    rect = fitz.Rect(
        M, layout.y, W - M,
        layout.y + SIZE_PROV_HEADER * LINE_GAP + SIZE_PROV_HEADER + 4,
    )
    layout.page.insert_textbox(
        rect, _sanitize(header_text),
        fontsize=SIZE_PROV_HEADER, fontname=FONT_BOLD,
        color=HEADER_COLOR, align=0,
    )
    layout.y += SIZE_PROV_HEADER * LINE_GAP + 2
    layout.page.draw_line(
        fitz.Point(M, layout.y), fitz.Point(W - M, layout.y),
        color=RULE_COLOR, width=0.7,
    )
    layout.y += 8

    # Now arm the continuation header so any later page break inside this
    # provision repeats `<header_text> (continued)` at the top.
    layout.set_continuation(header_text)

    # ── Template subblock ──
    if is_custom or not _has_text(template_text):
        # CUSTOM provisions and no-counterpart cases: missing-side template.
        if is_custom:
            tpl_label = "Template"
            sub_ref = "(no counterpart in standard template)"
        else:
            tpl_label = "Template"
            sub_ref = tpl_ref or "(no section reference)"
        layout.need(SIZE_SUBLABEL * LINE_GAP + 8)
        layout.draw_text(
            f"{tpl_label}:",
            size=SIZE_SUBLABEL, font=FONT_BOLD,
            color=SUBLABEL_COLOR, x=M, right=W - M,
        )
        if not is_custom:
            layout.draw_text(
                f"  {sub_ref}",
                size=SIZE_BODY - 1, font=FONT_REG,
                color=SECTION_LABEL_COLOR, x=M, right=W - M,
            )
        layout.draw_missing_block(
            "Missing in Template",
            "this issue area has no counterpart in the standard template.",
        )
    else:
        _render_aligned_subblock(
            layout,
            label="Template",
            section_ref=tpl_ref,
            body=template_text,
        )

    layout.y += 6  # spacing between subblocks

    # ── Tenant subblock ──
    if not _has_text(tenant_text):
        layout.need(SIZE_SUBLABEL * LINE_GAP + 8)
        layout.draw_text(
            "Tenant Lease:",
            size=SIZE_SUBLABEL, font=FONT_BOLD,
            color=SUBLABEL_COLOR, x=M, right=W - M,
        )
        layout.draw_missing_block(
            "Missing in Tenant Lease",
            "this issue area is not addressed in the document.",
        )
    else:
        _render_aligned_subblock(
            layout,
            label="Tenant Lease",
            section_ref=tnt_ref,
            body=tenant_text,
        )

    # ── Block separator ──
    layout.clear_continuation()
    layout.draw_line(color=RULE_COLOR, width=0.5, gap_above=10, gap_below=14)


def _render_aligned_subblock(
    layout: _Layout,
    label: str,
    section_ref: str,
    body: str,
):
    """Render a Template or Tenant subblock with multi-segment support."""
    section_ref = (section_ref or "").strip()

    if not section_ref:
        sublabel_text = f"{label} (no section reference):"
    elif section_ref.lower().startswith(("section", "article", "sec.", "art.", "preamble", "recital")):
        sublabel_text = f"{label} ({section_ref}):"
    else:
        sublabel_text = f"{label} (Section {section_ref}):"

    layout.need(SIZE_SUBLABEL * LINE_GAP + 8)
    # Subblock label + section ref — keep on the same page as the first
    # segment of body if at all possible.
    layout.draw_text(
        sublabel_text,
        size=SIZE_SUBLABEL, font=FONT_BOLD,
        color=SUBLABEL_COLOR, x=M, right=W - M,
    )
    layout.y += 2

    segments = _split_into_segments(body)
    if not segments:
        return

    if len(segments) == 1:
        _, seg_body = segments[0]
        layout.draw_wrapped_body(seg_body)
        return

    # Multi-segment: concatenate ALL with visible dividers in document order.
    for idx, (seg_ref, seg_body) in enumerate(segments):
        if idx > 0:
            divider_label = f"from Section {seg_ref}" if seg_ref else "next segment"
            layout.draw_segment_divider(divider_label)
        elif seg_ref:
            # First segment carries an explicit section header — surface it.
            layout.draw_text(
                f"  Section {seg_ref}",
                size=SIZE_BODY - 1, font=FONT_BOLD,
                color=SECTION_LABEL_COLOR, x=M + INDENT, right=W - M,
            )
        layout.draw_wrapped_body(seg_body)


# ── CUSTOM placement ──

_RELATED_LP_FIELDS = (
    "related_lp_id",
    "related_lp",
    "parent_lp",
    "attached_lp",
    "suggested_lp",
)


def _custom_related_lp(custom_provision: Dict, discoveries: Dict) -> Optional[str]:
    """Return the LP id this CUSTOM is attached to, if any.

    Looks at well-known fields on the CUSTOM provision itself, and at the
    discoveries.folded list (which already maps clauses to LPs by name).
    Never invents a similarity heuristic — only uses metadata that already
    exists on the pipeline output.
    """
    # 1. Direct fields on the CUSTOM provision dict.
    for f in _RELATED_LP_FIELDS:
        v = custom_provision.get(f)
        if v and isinstance(v, str) and v.strip():
            return v.strip()

    # 2. discoveries.folded entries that match this CUSTOM by clause name.
    folded = (discoveries or {}).get("folded") or []
    name = (custom_provision.get("provision_name") or "").strip().lower()
    if name and folded:
        for f in folded:
            if (f.get("clause_name") or "").strip().lower() == name:
                lp = f.get("lp_id")
                if lp and isinstance(lp, str):
                    return lp.strip()
    return None


def _organize_provisions(results: Dict) -> Tuple[List[Dict], Dict[str, List[Dict]], List[Dict]]:
    """Build the render order from results['provisions'].

    Returns:
      (lp_items, custom_after_lp, catchall_customs) where
        lp_items is the list of standard LP-XX items in original order,
        custom_after_lp maps lp_id -> list of CUSTOM items to render right
            after that LP block,
        catchall_customs is the list of unattached CUSTOM items grouped at end.
    """
    provisions = results.get("provisions") or []
    discoveries = results.get("discoveries") or {}

    lp_items: List[Dict] = []
    custom_after_lp: Dict[str, List[Dict]] = {}
    catchall: List[Dict] = []

    customs: List[Dict] = []
    for p in provisions:
        pid = (p.get("provision_id") or "").strip()
        is_custom = pid.upper().startswith("CUSTOM") or pid.upper().startswith("DISC-")
        normalized = {
            "provision_id":         pid,
            "provision_name":       p.get("provision_name") or pid,
            "template_text":        p.get("template_text") or "",
            "tenant_text":          p.get("tenant_text") or "",
            "template_section_ref": p.get("template_section_ref") or "",
            "tenant_section_ref":   p.get("tenant_section_ref") or "",
            "is_custom":            is_custom,
            "_raw":                 p,
        }
        if is_custom:
            customs.append(normalized)
        else:
            lp_items.append(normalized)

    for c in customs:
        related = _custom_related_lp(c["_raw"], discoveries)
        if related and any(lp["provision_id"] == related for lp in lp_items):
            custom_after_lp.setdefault(related, []).append(c)
        else:
            catchall.append(c)

    return lp_items, custom_after_lp, catchall


# ── Cover page ──

def _render_cover(layout: _Layout, results: Dict):
    title = "Aligned Provision Comparison"
    subtitle_pieces = []
    template_file = results.get("template_file") or ""
    tenant_file = results.get("tenant_file") or ""
    if template_file or tenant_file:
        if template_file:
            subtitle_pieces.append(f"Template: {template_file}")
        if tenant_file:
            subtitle_pieces.append(f"Tenant: {tenant_file}")

    layout.y = M + 80

    rect = fitz.Rect(
        M, layout.y, W - M,
        layout.y + SIZE_DOC_TITLE * LINE_GAP + SIZE_DOC_TITLE + 8,
    )
    layout.page.insert_textbox(
        rect, _sanitize(title),
        fontsize=SIZE_DOC_TITLE, fontname=FONT_BOLD,
        color=HEADER_COLOR, align=0,
    )
    layout.y += SIZE_DOC_TITLE * LINE_GAP + 4

    # Subtitle (date + filenames)
    from datetime import datetime
    date_str = datetime.now().strftime("%B %d, %Y")
    subtitle_line1 = date_str
    layout.draw_text(
        subtitle_line1, size=SIZE_DOC_SUB, font=FONT_REG,
        color=SECTION_LABEL_COLOR, x=M, right=W - M,
    )
    for piece in subtitle_pieces:
        layout.draw_text(
            piece, size=SIZE_DOC_SUB, font=FONT_REG,
            color=SECTION_LABEL_COLOR, x=M, right=W - M,
        )

    layout.y += 14

    # Explanatory paragraph
    intro = (
        "This document presents the standard template clause and the corresponding "
        "tenant lease clause for each provision in scope, in alternating blocks. "
        "The intent is to support clause-by-clause reading without flipping between "
        "documents. CAM's substantive analysis lives in the Synopsis and annotated "
        "PDFs; this artifact contains the underlying text only."
    )
    layout.draw_wrapped_body(
        intro, size=SIZE_BODY, font=FONT_REG, color=BODY_COLOR,
        x=M, right=W - M, bottom_margin=4,
    )

    layout.y += 10
    layout.page.draw_line(
        fitz.Point(M, layout.y), fitz.Point(W - M, layout.y),
        color=RULE_COLOR, width=0.6,
    )
    layout.y += 18


# ── Public entry point ──

def build_aligned_comparison_pdf(results: Dict, output_dir: str) -> Optional[Path]:
    """Build the Aligned Provision Comparison View PDF.

    Skips Mode C (mode == 'analyze'); returns None in that case.

    Args:
        results:   Pipeline results dict (Mode A shape).
        output_dir: Directory to write the PDF into.

    Returns:
        Path to the generated PDF, or None on skip / failure.
    """
    if (results or {}).get("mode") == "analyze":
        return None

    try:
        layout = _Layout()

        _render_cover(layout, results)

        lp_items, custom_after_lp, catchall = _organize_provisions(results)

        if not lp_items and not catchall:
            # No content to render — emit a placeholder paragraph rather than
            # producing an empty PDF.
            layout.draw_wrapped_body(
                "No provisions were available to render.",
                size=SIZE_BODY, font=FONT_ITALIC, color=SECTION_LABEL_COLOR,
                x=M, right=W - M,
            )
        else:
            for lp in lp_items:
                _render_provision(layout, lp)
                # Render any CUSTOM provisions explicitly attached to this LP.
                for c in custom_after_lp.get(lp["provision_id"], []):
                    _render_provision(layout, c)

            if catchall:
                # Section header for unattached CUSTOMs.
                layout.need(SIZE_PROV_HEADER * LINE_GAP + 30)
                layout.y += 8
                rect = fitz.Rect(
                    M, layout.y, W - M,
                    layout.y + SIZE_PROV_HEADER * LINE_GAP + SIZE_PROV_HEADER + 6,
                )
                layout.page.insert_textbox(
                    rect, _sanitize("Additional Provisions (No Template Counterpart)"),
                    fontsize=SIZE_PROV_HEADER, fontname=FONT_BOLD,
                    color=HEADER_COLOR, align=0,
                )
                layout.y += SIZE_PROV_HEADER * LINE_GAP + 2
                layout.page.draw_line(
                    fitz.Point(M, layout.y), fitz.Point(W - M, layout.y),
                    color=RULE_COLOR, width=0.7,
                )
                layout.y += 8
                layout.draw_text(
                    "These clauses appear in the tenant lease but have no corresponding "
                    "section in the standard template.",
                    size=SIZE_BODY, font=FONT_ITALIC, color=SECTION_LABEL_COLOR,
                    x=M, right=W - M,
                )
                layout.y += 6
                for c in catchall:
                    _render_provision(layout, c)

        out_path = Path(output_dir) / "Aligned_Provision_Comparison.pdf"
        layout.doc.save(str(out_path))
        layout.doc.close()
        print(
            f"[comparison_view] Built Aligned Provision Comparison PDF: {out_path}",
            flush=True,
        )
        return out_path

    except Exception as e:
        print(f"[comparison_view] Failed to build comparison PDF: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None
