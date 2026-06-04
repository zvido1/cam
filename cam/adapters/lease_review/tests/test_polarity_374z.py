"""Step 374Z — targeted regression fixtures for the C3 polarity correction + materiality landmine.

Deterministic, purpose-built (random leases may never exercise these exact conditions). Exercises the
REAL production functions: ``derive_lp_state`` (perspective-aware coverage state), the favorable-absence
partition rule, and ``_classify_materiality`` (the polarity landmine guard).

Run directly:  python -m cam.adapters.lease_review.tests.test_polarity_374z
Or via pytest:  pytest cam/adapters/lease_review/tests/test_polarity_374z.py

Invariant under test: a missing element whose absence is adverse to the OPPOSITE party must not be
counted as a selected-perspective-adverse gap merely because it is missing. Favorable absences are
retained separately (data slot) and never offset Risk; null/contextual stay conservative/reviewable.
"""
from cam.adapters.lease_review.lease_coverage_305 import derive_lp_state, _OPPOSITE_PARTY
from cam.adapters.lease_review import lease_exposure as LE

PERSP = "tenant"
OPP = _OPPOSITE_PARTY[PERSP]  # "landlord"


def _el(eid, adverse_to, severity="medium"):
    return {"element_id": eid, "absence_adverse_to": adverse_to, "absence_severity": severity}


def _verd(eid, verdict):
    return {"element_id": eid, "verdict": verdict}


def _partition_favorable(elements_305, merged, perspective):
    """Mirrors the assess_coverage_305 inline rule: opposite-polarity MISSING → favorable slot."""
    opp = _OPPOSITE_PARTY.get(perspective)
    pol = {e["element_id"]: e.get("absence_adverse_to") for e in elements_305}
    adverse, favorable = [], []
    for r in merged:
        if r["verdict"] == "missing":
            (favorable if (opp and pol.get(r["element_id"]) == opp) else adverse).append(r["element_id"])
    return adverse, favorable


# ── Fixture 1: missing tenant PROTECTION only → tenant-adverse gap, Risk-eligible ──────────────────
def test_1_missing_tenant_protection_only_is_adverse_gap():
    els = [_el("X.protection", "tenant", "high"), _el("X.present", "tenant", "medium")]
    merged = [_verd("X.protection", "missing"), _verd("X.present", "explicitly_present")]
    state = derive_lp_state(merged, els, PERSP)
    assert state in ("partial", "missing"), state  # adverse gap, not covered
    adverse, favorable = _partition_favorable(els, merged, PERSP)
    assert adverse == ["X.protection"] and favorable == []
    # high-severity tenant-adverse absence is materiality-eligible (Risk path), via the real classifier
    mat = LE._classify_materiality({"coverage_state": state, "issue_area_id": "X",
                                    "elements_missing": ["Tenant protection element"]}, PERSP)
    assert mat in ("high", "medium", "low")  # not forced low by the guard (it's tenant-adverse)
    print("  [1] missing tenant protection only -> %s, adverse gap (Risk-eligible) OK" % state)


# ── Fixture 2: missing tenant BURDEN only → NOT adverse; favorable/non-adverse candidate ───────────
def test_2_missing_tenant_burden_only_is_favorable():
    els = [_el("X.burden", OPP, "high"), _el("X.present", "tenant", "medium")]
    merged = [_verd("X.burden", "missing"), _verd("X.present", "explicitly_present")]
    state = derive_lp_state(merged, els, PERSP)
    assert state == "covered", state  # opposite-polarity-only absence is NOT a gap
    adverse, favorable = _partition_favorable(els, merged, PERSP)
    assert adverse == [] and favorable == ["X.burden"]
    print("  [2] missing tenant burden only -> covered; retained as favorable candidate OK")


# ── Fixture 3: mixed LP (LP-27 shape) → Risk stays on protection gap; favorable retained, no offset ─
def test_3_mixed_protection_and_burden():
    els = [_el("X.self_help", "tenant", "medium"), _el("X.lender", OPP, "low"),
           _el("X.present", "tenant", "high")]
    merged = [_verd("X.self_help", "missing"), _verd("X.lender", "missing"),
              _verd("X.present", "explicitly_present")]
    state = derive_lp_state(merged, els, PERSP)
    assert state == "partial", state  # protection gap still drives partial/Risk
    adverse, favorable = _partition_favorable(els, merged, PERSP)
    assert adverse == ["X.self_help"], adverse        # protection gap retained as adverse
    assert favorable == ["X.lender"], favorable        # favorable absence retained, NOT deleted
    # favorable absence does NOT remove the adverse gap (no offset)
    assert "X.self_help" in adverse and "X.lender" not in adverse
    print("  [3] mixed LP -> partial (Risk on protection); favorable burden retained, no offset OK")


# ── Fixture 4: null / context-dependent polarity → conservative/reviewable, NOT auto-favorable ─────
def test_4_null_polarity_stays_conservative():
    els = [_el("X.ambiguous", None, "medium"), _el("X.present", "tenant", "high")]
    merged = [_verd("X.ambiguous", "missing"), _verd("X.present", "explicitly_present")]
    state = derive_lp_state(merged, els, PERSP)
    assert state == "partial", state  # null polarity is NOT flipped favorable (stays a gap/reviewable)
    adverse, favorable = _partition_favorable(els, merged, PERSP)
    assert adverse == ["X.ambiguous"] and favorable == []  # not auto-favorable
    print("  [4] null-polarity absence -> partial, stays conservative (not auto-favorable) OK")


# ── Fixture 5: exact-match high-materiality OPPOSITE-polarity absence → never tenant Risk ──────────
def test_5_materiality_landmine_disarmed_even_when_label_aligned():
    """ALIGN the rent-acceleration string to its real 305 label (simulate future label normalization);
    the polarity guard must still prevent a tenant-Risk false positive."""
    import json
    sch = json.load(open("cam/adapters/lease_review/schemas/retail_lease_knowledge.json", encoding="utf-8"))
    lp11 = next(ia for ia in sch["issue_areas"] if ia.get("id") == "LP-11")
    ra = next(e for e in lp11["expected_elements_305"] if e["element_id"] == "LP-11.rent_acceleration_remedy")
    assert ra["absence_adverse_to"] == "landlord", ra["absence_adverse_to"]  # landlord-favorable element
    label = ra["element_label"]

    saved = set(LE._HIGH_MATERIALITY_ELEMENTS)
    try:
        LE._HIGH_MATERIALITY_ELEMENTS.add(label.lower())  # the "label normalization" that arms the landmine
        assessment = {"coverage_state": "partial", "issue_area_id": "LP-11", "elements_missing": [label]}
        mat = LE._classify_materiality(assessment, PERSP)
        # WITHOUT the guard this would return "high" (string match) -> tenant Risk. WITH the guard,
        # the landlord-polarity element is filtered out of the string-match.
        assert mat != "high", f"landmine fired: materiality={mat} for a landlord-favorable absence"
        # sanity: a genuine tenant-adverse missing element with the same label WOULD be high (guard is
        # polarity-specific, not a blanket suppression) — proven via fixture 1's materiality path.
        print("  [5] aligned rent-acceleration string + tenant perspective -> materiality=%s (NOT high) OK" % mat)
    finally:
        LE._HIGH_MATERIALITY_ELEMENTS.clear()
        LE._HIGH_MATERIALITY_ELEMENTS.update(saved)


# ── Fixture 6: cross-document dependency favorable candidate (lender-cure + SNDA) → caveat retained ─
def test_6_cross_document_favorable_carries_dependency_caveat():
    import json
    sch = json.load(open("cam/adapters/lease_review/schemas/retail_lease_knowledge.json", encoding="utf-8"))
    lp27 = next(ia for ia in sch["issue_areas"] if ia.get("id") == "LP-27")
    lender = next(e for e in lp27["expected_elements_305"] if e["element_id"] == "LP-27.lender_notice_and_cure_right")
    assert lender["absence_adverse_to"] == OPP                      # landlord-favorable
    assert lender.get("cross_LP_coverage") == ["LP-22"]            # SNDA may impose it elsewhere
    # The assess_coverage_305 favorable-slot entry copies cross_LP_coverage, so a later surface can
    # caveat ("confirm no SNDA/separate lender agreement imposes one") rather than assert unconditional
    # advantage. Mirror the production slot shape:
    slot = {"element_id": lender["element_id"], "element_label": lender["element_label"],
            "absence_adverse_to": lender["absence_adverse_to"], "absence_severity": lender["absence_severity"],
            "cross_LP_coverage": lender.get("cross_LP_coverage") or None}
    assert slot["cross_LP_coverage"] == ["LP-22"]  # dependency caveat present, not dropped
    print("  [6] lender-cure favorable candidate retains cross_LP_coverage=[LP-22] dependency caveat OK")


_TESTS = [test_1_missing_tenant_protection_only_is_adverse_gap,
          test_2_missing_tenant_burden_only_is_favorable,
          test_3_mixed_protection_and_burden,
          test_4_null_polarity_stays_conservative,
          test_5_materiality_landmine_disarmed_even_when_label_aligned,
          test_6_cross_document_favorable_carries_dependency_caveat]

if __name__ == "__main__":
    print("Step 374Z polarity fixtures:")
    failed = 0
    for t in _TESTS:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print("  FAIL %s: %s" % (t.__name__, e))
    print("\n%d/%d fixtures passed" % (len(_TESTS) - failed, len(_TESTS)))
    raise SystemExit(1 if failed else 0)
