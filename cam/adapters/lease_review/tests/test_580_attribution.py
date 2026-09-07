"""Step 580-2 — guards for the coverage-attribution fix.

WHAT THESE PROTECT

Step 579 measured that the per-LP string "N of M elements covered" counted 38 landlord-protective
elements out of 120 on a tenant-lens run (31.7%), with nothing on any surface saying so. LP-11 read
"16 of 17 elements covered" where 11 of the 16 were the landlord's remedies against the reader.

The fix ANNOTATES the count and does NOT filter it. That distinction is the thing most likely to be
undone by a later well-meaning change, because filtering looks like the more decisive fix. It is
not: 3 of those 38 are genuinely dual (payment due date, late fee, CGL minimum), so subtracting
would make the number wrong in a new way. `test_count_is_annotated_not_filtered` exists to fail if
someone subtracts.

These are source-level guards, in the style of test_571_iife_scope_guard.py and
test_550_asset_versions.py. A behavioural test would need a live panel run; what actually broke
before was the wiring, and wiring is what these check.
"""
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_APP_JS = _ROOT / "05 Lease Analyzer" / "static" / "app.js"
_COV305 = _ROOT / "cam" / "adapters" / "lease_review" / "lease_coverage_305.py"
_STYLE = _ROOT / "05 Lease Analyzer" / "static" / "style.css"


@pytest.fixture(scope="module")
def app_js():
    return _APP_JS.read_text(encoding="utf-8", errors="replace")


@pytest.fixture(scope="module")
def cov305():
    return _COV305.read_text(encoding="utf-8", errors="replace")


# ── 580-2(a): the polarity field reaches the verdict record ───────────────────

def test_verdict_record_carries_absence_adverse_to(cov305):
    """Without this, no surface can attribute anything -- the field stopped at the schema."""
    m = re.search(r"verdict_record = \{(.*?)\n        \}", cov305, re.S)
    assert m, "verdict_record literal not found -- did the builder move?"
    body = m.group(1)
    assert '"absence_adverse_to": element.get("absence_adverse_to")' in body, (
        "verdict_record must carry absence_adverse_to. Step 579: 38 of 120 elements counted as "
        "covered on a tenant-lens run protect the landlord, and nothing downstream could say so "
        "because this field stopped at the schema element."
    )


def test_polarity_is_read_outside_the_missing_branch(cov305):
    """374Z read absence_adverse_to only when the verdict was `missing`. 579 measured that this
    sees 6 of 50 cases. The verdict_record read must not be inside that branch."""
    idx = cov305.index('"absence_adverse_to": element.get("absence_adverse_to")')
    window = cov305[max(0, idx - 1500):idx]
    # the verdict_record assignment must be the nearest enclosing statement, not a missing-branch if
    assert "verdict_record = {" in window, "the polarity read drifted out of verdict_record"
    tail = window[window.rindex("verdict_record = {"):]
    assert 'verdict == "missing"' not in tail, (
        "absence_adverse_to must be recorded for EVERY element, not only missing ones"
    )


# ── 580-2(b): annotate, do not filter ────────────────────────────────────────

def test_count_is_annotated_not_filtered(app_js):
    """THE load-bearing guard. coveredCount must stay a plain count of positive verdicts.

    If a later change filters polarity out of it, three genuinely-dual elements get silently
    dropped from the count and the number becomes wrong in a new way. Step 579 §6 recorded the
    decision; this is the thing that enforces it.
    """
    m = re.search(r"const coveredCount = ([^;]+);", app_js)
    assert m, "coveredCount assignment not found"
    expr = m.group(1)
    assert "_POSITIVE_VERDICTS.has(e.verdict)" in expr, "coveredCount must count positive verdicts"
    for forbidden in ("absence_adverse_to", "_protectsOtherParty", "_oppositeParty"):
        assert forbidden not in expr, (
            "coveredCount must NOT be filtered by polarity -- annotate the count, do not subtract "
            "from it. 3 of the 38 elements this would remove are genuinely dual (payment due date, "
            "late fee, CGL minimum). See Step 579 and build_log/580-2_code_status.md."
        )


def test_count_carries_the_attribution_note(app_js):
    assert "_otherPartyCovered" in app_js, "the count's attribution note is gone"
    assert "cv-elem-attrib-note" in app_js
    m = re.search(r"const _otherPartyCovered = ([^;]+);", app_js, re.S)
    assert m and "_protectsOtherParty" in m.group(1), (
        "the note must be computed from the polarity helper"
    )


def test_element_rows_are_attributed(app_js):
    assert "_attribTag" in app_js, "per-row attribution tag is gone"
    assert "cv-ev-attrib" in app_js
    # the tag must be gated on a PRESENT verdict. On a `missing` row the polarity means the
    # opposite thing -- the ABSENCE is adverse to the other party -- so "protects landlord" beside
    # a Missing badge is false on its face. Caught on the first on-device pass of 580-2.
    m_tag = re.search(r"const _attribTag = (.+)", app_js)
    assert m_tag and "_POSITIVE_VERDICTS.has(ev.verdict)" in m_tag.group(1), (
        "the row tag must only appear on present-tier rows"
    )
    # the tag must be attached to the label cell of the main element row
    m = re.search(r"const mainRow = .*?cv-ev-label.*?\n", app_js, re.S)
    assert m and "_attribTag" in m.group(0), "the tag is not on the element row's label cell"


# ── 580-2(c): the Covered: list exists ───────────────────────────────────────

def test_covered_list_is_rendered(app_js):
    """`Missing:` was itemised in three places and the present elements nowhere -- gaps were named
    and coverage was a bare number nobody could open."""
    assert "coveredHtml" in app_js, "the Covered: list is gone"
    assert "cv-covered-elements" in app_js
    assert "${coveredHtml}" in app_js, "coveredHtml is built but never emitted into the card"
    # emitted next to the Missing: list, not somewhere a reader would not look
    i_missing = app_js.index("${missingHtml}")
    i_covered = app_js.index("${coveredHtml}")
    assert 0 < (i_covered - i_missing) < 200, "Covered: should be rendered beside Missing:"


def test_covered_list_built_from_verdicts_not_elements_present(app_js):
    """elements_present carries no polarity; element_verdicts does, after 580-2(a)."""
    m = re.search(r"const _coveredEvs = ([^;]+);", app_js)
    assert m, "_coveredEvs not found"
    assert "element_verdicts" in m.group(1), (
        "the Covered: list must come from element_verdicts -- elements_present has no polarity "
        "field and cannot be attributed"
    )


# ── styling exists, so the markup is not invisible ───────────────────────────

def test_new_classes_have_styles():
    css = _STYLE.read_text(encoding="utf-8", errors="replace")
    for cls in ("cv-covered-elements", "cv-covered-item", "cv-covered-item-other",
                "cv-elem-attrib-note", "cv-ev-attrib"):
        assert "." + cls in css, f"{cls} is rendered but has no style rule"


# ── the helpers are inside the IIFE, per the 571 regression ──────────────────

def test_helpers_are_declared_before_use(app_js):
    """The Step-571 render regression was an IIFE-scope mistake of exactly this shape: a helper
    used by a render path that had not been declared where the path could see it."""
    decl = app_js.index("const _protectsOtherParty = function")
    for use in [m.start() for m in re.finditer(r"_protectsOtherParty\(", app_js)]:
        assert use > decl, "_protectsOtherParty used before its declaration"
    decl_op = app_js.index("const _oppositeParty =")
    assert decl_op < decl, "_oppositeParty must be declared before the helper that closes over it"
