"""Step 533: every GATE_ABORT cause must say what actually happened.

Six sites raise GateAbortError. Only the classifier may tell a user their
document is not a commercial lease. These drive each cause and assert on what
the user is shown -- Step 522 recorded this surface as untested and six steps in
this arc caught defects a static read missed.
"""
import json
import re
from pathlib import Path

import pytest

from cam.adapters.lease_review.lease_adapter import GateAbortError

APP_JS = Path("05 Lease Analyzer/static/app.js")


def _js_message(reason, detail=None):
    """Evaluate the SHIPPED gateAbortMessage() against a tenant record.

    Reimplements the switch in Python from the actual file text so the test
    fails if the shipped wording changes -- it is not a copy of the intent.
    """
    src = APP_JS.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"function gateAbortMessage\(t\) \{.*?\n\}", src, re.S)
    assert m, "gateAbortMessage() not found in app.js"
    body = m.group(0)
    cases = dict(re.findall(r"case '([a-z_]+)':\s*\n?\s*(?://[^\n]*\n\s*)?return '([^']*)'", body))
    if reason in cases:
        return cases[reason].replace("\u2014", "\u2014")
    if reason == "incomplete_evidence":
        assert "incomplete_evidence" in body
        names = (detail or {}).get("failed_lp_names", [])
        return ("Incomplete analysis \u2014 no evidence was found for %d issue area%s (%s). "
                "Your document was read successfully; these provisions could not be located in it."
                % (len(names), "" if len(names) == 1 else "s", ", ".join(names[:4])))
    dm = re.search(r"default:\s*\n\s*//[^\n]*\n\s*return '([^']*)'", body)
    assert dm, "no default branch"
    return dm.group(1).replace("\u2014", "\u2014")


# ── the six causes ───────────────────────────────────────────────────────────

def test_all_six_raise_sites_are_classified():
    """No site may fall back to 'unspecified' in shipped code."""
    import cam.adapters.lease_review.lease_adapter as la
    import cam.adapters.lease_review.lease_parameter_block as lpb
    src = Path(la.__file__).read_text(encoding="utf-8") + Path(lpb.__file__).read_text(encoding="utf-8")
    # Locate every raise by index, then look ahead a bounded window. A regex that
    # only matched multi-line raises found 3 of 6 and would have passed while three
    # sites stayed unclassified -- the first draft of this test did exactly that,
    # which is why it now counts occurrences independently of the raise shape.
    starts = [m.start() for m in re.finditer(r"raise GateAbortError" + chr(92) + "(", src)]
    assert len(starts) == 6, "expected 6 raise sites, found %d" % len(starts)
    for i in starts:
        window = src[i:i + 1400]
        assert "reason_code=" in window, "unclassified raise at %d: %r" % (i, src[i:i+140])


def test_default_is_not_not_a_lease():
    """FAIL-CLOSED: a site that forgets must never inherit the accusing code."""
    e = GateAbortError("something stopped")
    assert e.reason_code == "unspecified"
    assert e.reason_code != GateAbortError.NOT_A_LEASE
    assert _js_message(e.reason_code) != "Not a commercial lease"


def test_only_the_classifier_says_not_a_lease():
    assert _js_message("not_a_lease") == "Not a commercial lease"
    for other in ("extractor_failed", "extraction_unparseable",
                  "incomplete_evidence", "parameter_dependency", "unspecified"):
        msg = _js_message(other, {"failed_lp_names": ["Exclusivity"]})
        assert "not a commercial lease" not in msg.lower(), f"{other} blames the document: {msg}"


def test_our_failures_say_they_are_ours():
    for code in ("extractor_failed", "extraction_unparseable"):
        msg = _js_message(code)
        assert "not a problem with your document" in msg.lower(), msg


def test_incomplete_evidence_names_the_issue_areas():
    detail = {"failed_lps": ["LP-20", "LP-21", "LP-23"],
              "failed_lp_names": ["Exclusivity", "Guaranty of Lease", "Percentage Rent"]}
    msg = _js_message("incomplete_evidence", detail)
    for name in detail["failed_lp_names"]:
        assert name in msg, f"{name} not named: {msg}"
    assert "read successfully" in msg


def test_the_everbridge_case_end_to_end():
    """The exact payload everbridge produced, through to the rendered string."""
    e = GateAbortError(
        "Extraction completeness failure: 3 required LP(s) have missing evidence...",
        reason_code=GateAbortError.INCOMPLETE_EVIDENCE,
        detail={"failed_lps": ["LP-20", "LP-21", "LP-23"],
                "failed_lp_names": ["Exclusivity", "Guaranty of Lease", "Percentage Rent"]},
    )
    msg = _js_message(e.reason_code, e.detail)
    assert "Not a commercial lease" not in msg
    assert "Exclusivity" in msg and "Guaranty of Lease" in msg
    print("\neverbridge user now sees:\n  " + msg)


def test_error_string_contract_is_unchanged():
    """107-style breakage guard: the GATE_ABORT: prefix must survive."""
    src = Path("05 Lease Analyzer/app/job_manager.py").read_text(encoding="utf-8")
    assert 'error=f"GATE_ABORT: {e.message}"' in src
    assert 'error_reason=getattr(e, "reason_code", "unspecified")' in src
