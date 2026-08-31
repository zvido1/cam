"""Step 522: assessment_status is emitted, fail-closed, at every route.

These exercise the real `assess_coverage` loop. The point is to prove the value
is SET by execution rather than by reading the call sites -- Step 521 was written
after six consecutive steps in which a static read missed the defect.
"""
import pytest

from cam.adapters.lease_review.lease_coverage import assess_coverage, _build_assessment
from cam.adapters.lease_review.lease_knowledge import get_issue_area


def _by_id(assessments):
    return {a["issue_area_id"]: a for a in assessments}


def test_default_is_unset_not_assessed():
    """FAIL-CLOSED: a caller that omits the argument must not get 'assessed'."""
    a = _build_assessment(
        pid="LP-07", area=get_issue_area("LP-07") or {}, coverage_state="covered",
        applicability="applicable", evidence_summary="", supporting_provisions=[],
        negative_space=[], elements_found=[], elements_missing=[],
    )
    assert a["assessment_status"] == "unset"
    assert a["assessment_status"] != "assessed"


def test_every_entry_carries_the_field():
    """No route may emit an assessment without the key present."""
    out = assess_coverage(provisions=[], full_tenant_text="a short document.")
    assert out, "expected assessments for the schema's issue areas"
    for a in out:
        assert "assessment_status" in a, f"{a['issue_area_id']} emitted without the field"
        assert a["assessment_status"] in ("assessed", "not_assessed", "suppressed", "unset")


def test_no_entry_is_silently_unset_in_a_real_pass():
    """`unset` means a route forgot. A full pass must not produce one."""
    out = assess_coverage(provisions=[], full_tenant_text="a short document.")
    unset = [a["issue_area_id"] for a in out if a["assessment_status"] == "unset"]
    assert not unset, f"routes emitted without saying: {unset}"


def test_R1_R2_applicability_routes_are_not_assessed():
    """No clues anywhere -> conditional/optional LPs route out before any judging."""
    out = _by_id(assess_coverage(provisions=[], full_tenant_text="zzz."))
    routed = [a for a in out.values() if not a.get("element_verdicts")]
    assert routed, "expected applicability-routed entries"
    for a in routed:
        assert a["assessment_status"] == "not_assessed", (
            f"{a['issue_area_id']} state={a['coverage_state']} "
            f"status={a['assessment_status']} -- an unjudged entry claimed a judgment"
        )


def test_R3_extraction_not_applicable_short_circuit():
    """Extraction-status short-circuit must report not_assessed."""
    pid = "LP-07"
    provs = [{"provision_id": pid, "status": "NOT_APPLICABLE",
              "tenant_text": "", "alignment_notes": "known absent"}]
    text = "tenant shall pay its proportionate share of operating expenses."
    a = _by_id(assess_coverage(provisions=provs, full_tenant_text=text))[pid]
    assert a["coverage_state"] == "not_applicable"
    assert a["assessment_status"] == "not_assessed"


def test_R5_missing_evidence_is_not_assessed_despite_asserting_elements():
    """R5 populates elements_missing with every expected element and no evaluator
    ran. That is the 'verdict nobody voted on' case from Step 521."""
    pid = "LP-07"
    text = "tenant shall pay its proportionate share of operating expenses."
    a = _by_id(assess_coverage(provisions=[], full_tenant_text=text))[pid]
    assert a["coverage_state"] in ("missing", "broken_xref")
    assert a["elements_missing"], "R5 asserts missing elements"
    assert a["assessment_status"] == "not_assessed"


def test_requires_attention_keeps_its_boolean_contract():
    """Step 470 / lease_exposure:523 truthiness must survive."""
    out = assess_coverage(provisions=[], full_tenant_text="zzz.")
    for a in out:
        assert isinstance(a["requires_attention"], bool), (
            f"{a['issue_area_id']} requires_attention is "
            f"{type(a['requires_attention']).__name__}, breaking the truthiness test"
        )


def test_R4_reserved_or_omitted_is_not_assessed():
    """A section marked [Reserved] yields broken_xref + every expected element
    listed as missing, with no evaluator involved."""
    pid = "LP-07"
    text = "tenant shall pay its proportionate share of operating expenses."
    ns = {pid: [{"signal_type": "reserved_or_omitted",
                 "detail": "Section 9.1 [Intentionally Omitted]"}]}
    provs = [{"provision_id": pid, "status": "OK", "tenant_text": "CAM article text here."}]
    a = _by_id(assess_coverage(provisions=provs, full_tenant_text=text,
                               negative_space_signals=ns))[pid]
    assert a["coverage_state"] == "broken_xref"
    assert a["assessment_status"] == "not_assessed"


def test_R8_panel_raising_is_suppressed_not_assessed(monkeypatch):
    """When the 305 panel raises, the legacy deterministic path substitutes.

    Before Step 522 nothing on the assessment recorded that a judgment had been
    attempted and thrown away -- the entry was indistinguishable from one the
    deterministic path had simply handled. It must now read `suppressed`.
    """
    import cam.adapters.lease_review.lease_coverage_305 as m305

    def _boom(*a, **k):
        raise RuntimeError("panel exploded")

    monkeypatch.setattr(m305, "assess_coverage_305", _boom)

    pid = None
    from cam.adapters.lease_review.lease_knowledge import get_all_issue_areas
    for area in get_all_issue_areas():
        if area.get("expected_elements_305"):
            pid = area["id"]
            break
    assert pid, "no 305-enabled LP in the schema"

    text = ("tenant shall pay its proportionate share of operating expenses, "
            "common area maintenance, taxes and insurance for the premises.")
    provs = [{"provision_id": pid, "status": "OK",
              "tenant_text": "The tenant shall pay all such amounts as additional rent."}]
    a = _by_id(assess_coverage(provisions=provs, full_tenant_text=text))[pid]
    assert a["assessment_status"] == "suppressed", (
        f"{pid} status={a['assessment_status']} -- a discarded panel result was "
        f"reported as though the deterministic path had simply assessed it"
    )


def test_summary_counts_not_assessed_fail_closed():
    """The API summary must expose the count, and count an ABSENT status as
    not-assessed. The Step-522 Atlas run predates this field, so it is proved
    here rather than by that run."""
    import inspect
    from cam.adapters.lease_review.lease_adapter import _compute_summary_analyze

    ca = [
        {"issue_area_id": "LP-01", "assessment_status": "assessed",
         "requires_attention": False, "coverage_state": "covered"},
        {"issue_area_id": "LP-02", "assessment_status": "not_assessed",
         "requires_attention": False, "coverage_state": "not_applicable"},
        {"issue_area_id": "LP-03", "assessment_status": "suppressed",
         "requires_attention": True, "coverage_state": "partial"},
        # no assessment_status at all -- must NOT be counted as assessed
        {"issue_area_id": "LP-04", "requires_attention": False,
         "coverage_state": "covered"},
    ]
    kw = {}
    for name, prm in inspect.signature(_compute_summary_analyze).parameters.items():
        if name in ("coverage_assessment", "coverage_assessments"):
            kw[name] = ca
        elif prm.default is not inspect.Parameter.empty:
            continue
        elif name in ("provisions_extracted", "provisions_checked"):
            kw[name] = 4
        else:
            kw[name] = [] if "finding" in name or "conflict" in name or "risk" in name else None
    out = _compute_summary_analyze(**kw)
    assert out["not_assessed"] == 3, (
        f"expected 3 (not_assessed + suppressed + absent), got {out['not_assessed']}"
    )
