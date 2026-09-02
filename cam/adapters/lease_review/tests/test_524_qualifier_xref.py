"""Step 524: the qualifier cross-reference annotates and never touches evidence.

The first test is the one that matters. Everything else in this step rests on
the panel's input being byte-identical, and that is a property of the code, so it
is asserted rather than believed.
"""
import copy
import json
from pathlib import Path

import pytest

from cam.adapters.lease_review.lease_qualifier_xref import (
    annotate_assessments, detect_qualifiers,
)

ATLAS = Path("05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt")

# §11.3, verbatim. Offsets confirmed against the file in Step 523.
CAP = ("Neither party shall be liable to the other for any consequential, "
       "indirect, punitive, or special damages arising under this Lease.")


def _doc():
    if not ATLAS.exists():
        pytest.skip("atlas fixture not present")
    return ATLAS.read_text(encoding="utf-8")


def _lp(pid, name, labels, status="assessed", tenant_text="", recs=None):
    a = {
        "issue_area_id": pid, "issue_area_name": name,
        "assessment_status": status, "coverage_state": "covered",
        "requires_attention": False, "tenant_text": tenant_text,
        "element_verdicts": [{"element_label": L, "verdict": "explicitly_present"}
                             for L in labels],
        "elements_found": [], "elements_missing": [],
    }
    if recs:
        a["span_evidence_records"] = recs
    return a


# ── the invariant ────────────────────────────────────────────────────────────

def test_never_mutates_anything_the_panel_reasoned_over():
    doc = _doc()
    lps = [
        _lp("LP-27", "Landlord Default & Tenant Remedies",
            ["Tenant has right to monetary damages for landlord default"]),
        _lp("LP-13", "Indemnification & Liability", ["Indemnity is mutual"],
            tenant_text=CAP),
    ]
    before = copy.deepcopy(lps)
    annotate_assessments(lps, doc)
    GUARDED = ("tenant_text", "element_verdicts", "coverage_state",
               "requires_attention", "assessment_status", "elements_found",
               "elements_missing", "span_evidence_records")
    for b, a in zip(before, lps):
        for k in GUARDED:
            assert b.get(k) == a.get(k), (
                f"{a['issue_area_id']}.{k} was modified -- the byte-identical "
                f"guarantee that makes this pass safe is void"
            )
        assert set(a) - set(b) <= {"qualifier_annotations"}, (
            f"{a['issue_area_id']} gained keys beyond the annotation: "
            f"{set(a) - set(b)}"
        )


def test_annotation_never_claims_the_panel_weighed_it():
    doc = _doc()
    lps = [_lp("LP-27", "Landlord Default & Tenant Remedies",
               ["Tenant has right to monetary damages for landlord default"])]
    annotate_assessments(lps, doc)
    for note in lps[0]["qualifier_annotations"]:
        assert note["weighed_by_panel"] is False
        assert "quote" in note and note["quote"]
        # every annotation must be resolvable to the source, verbatim
        assert doc[note["start_char"]:note["end_char"]].strip() == note["quote"]


# ── detection ────────────────────────────────────────────────────────────────

def test_detects_the_atlas_cap_verbatim():
    quals = detect_qualifiers(_doc())
    assert quals, "no qualifier detected in atlas"
    joined = " ".join(q["quote"] for q in quals)
    assert "consequential, indirect, punitive, or special damages" in joined
    assert any(q["section_ref"] == "Section 11.3" for q in quals)


def test_lp27_is_annotated_on_the_real_corpus():
    doc = _doc()
    lps = [_lp("LP-27", "Landlord Default & Tenant Remedies",
               ["Tenant has right to monetary damages for landlord default",
                "Common law and equitable remedies are preserved"])]
    n = annotate_assessments(lps, doc)
    assert n == 1
    assert lps[0]["qualifier_annotations"]


# ── linking is by subject, not proximity ─────────────────────────────────────

def test_linking_is_not_proximity_based():
    """A remedies LP whose evidence sits at the far end of the document must
    still be annotated. Atlas's 239 characters are a fixture coincidence."""
    doc = _doc()
    far = doc[:400]
    lps = [_lp("LP-99", "Remote Remedies", ["Tenant remedies are specified"],
               tenant_text=far)]
    annotate_assessments(lps, doc)
    assert lps[0].get("qualifier_annotations"), (
        "a subject-matching LP far from the clause was not annotated -- linking "
        "has become proximity-dependent"
    )
    assert lps[0]["qualifier_annotations"][0]["link_basis"] == "subject"
    assert lps[0]["qualifier_annotations"][0]["distance_chars"] > 1000


def test_substring_collisions_do_not_link():
    """Both of these were real false positives on the first draft."""
    doc = _doc()
    lps = [
        _lp("LP-32", "Hazardous Materials",
            ["Tenant's remediation obligation for contamination"]),
        _lp("LP-08", "Insurance Requirements",
            ["Commercial general liability minimum coverage is specified"]),
    ]
    annotate_assessments(lps, doc)
    for a in lps:
        assert not a.get("qualifier_annotations"), (
            f"{a['issue_area_id']} linked on a substring collision "
            f"(remediation / general liability)"
        )


# ── containment ──────────────────────────────────────────────────────────────

def test_clause_inside_the_lp_own_evidence_is_not_annotated():
    """The panel saw it; there is nothing to disclose."""
    doc = _doc()
    start = doc.find(CAP)
    assert start > 0
    lps = [_lp("LP-13", "Indemnification & Liability",
               ["Tenant remedies for landlord default are preserved"],
               recs=[{"start_char": start - 500, "end_char": start + len(CAP) + 500}])]
    annotate_assessments(lps, doc)
    notes = lps[0].get("qualifier_annotations") or []
    assert not any(CAP[:40] in n["quote"] for n in notes), (
        "a clause inside the LP's own evidence was reported as not weighed"
    )


def test_also_retrieved_under_uses_real_intervals_not_a_hull():
    """Disjoint spans either side of the clause must NOT report containment."""
    doc = _doc()
    start = doc.find(CAP)
    lps = [
        _lp("LP-27", "Landlord Default & Tenant Remedies",
            ["Tenant has right to monetary damages for landlord default"]),
        _lp("LP-12", "Early Termination", ["Termination remedies"],
            recs=[{"start_char": start - 2000, "end_char": start - 1000},
                  {"start_char": start + 500, "end_char": start + 1500}]),
    ]
    annotate_assessments(lps, doc)
    for n in lps[0].get("qualifier_annotations") or []:
        assert "LP-12" not in n["also_retrieved_under"], (
            "hull containment reported LP-12 as having been judged on a clause "
            "that falls between two of its spans"
        )


def test_not_assessed_lps_are_skipped():
    doc = _doc()
    lps = [_lp("LP-27", "Landlord Default & Tenant Remedies",
               ["Tenant has right to monetary damages"], status="not_assessed")]
    annotate_assessments(lps, doc)
    assert not lps[0].get("qualifier_annotations"), (
        "an LP with no finding was given a qualifier for a finding"
    )


def test_deterministic():
    doc = _doc()
    assert detect_qualifiers(doc) == detect_qualifiers(doc)
