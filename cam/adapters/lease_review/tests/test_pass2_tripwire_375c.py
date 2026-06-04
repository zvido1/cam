"""Step 375C — Pass-2 integrity tripwire validation. Drives the REAL builder
`_build_pass2_directional_findings` with each run's stored `pass2_raw` as `pass2_outputs`, so it
validates the deployed detection logic against the historical failure mode WITHOUT re-running the
pipeline (no provider keys needed). Plus a synthetic per-finding unit test.

Run:  python -m cam.adapters.lease_review.tests.test_pass2_tripwire_375c
"""
import json
from cam.adapters.lease_review.lease_synthesis import _build_pass2_directional_findings as build

RUNS = {  # label -> (run dir, expectation)
    "030920 (current, clean)": ("lease_review_20260602_030920_d0e19e", "no_fire"),
    "0604 (current, clean)":   ("lease_review_20260604_033046_52adbf", "no_fire"),
    "s370r1 (historical, A-empty)":  ("lease_review_20260529_191130_s370r1", "fire"),
    "370c_H1 (historical, A-empty)": ("lease_review_20260530_231425_370c_H1", "fire"),
}


def _load_pass2(run):
    d = json.load(open("05 Lease Analyzer/results/%s/tenant_0/pipeline_results.json" % run, encoding="utf-8"))
    pr = d["_stage_data"]["synthesis_meta"]["pass2_raw"]
    # pass2_outputs shape the builder reads: {role: {"verdicts": [...], "completed":bool, "model":str}}
    pass2_outputs = {r: {"verdicts": pr[r].get("verdicts") or [], "completed": pr[r].get("completed", False),
                         "model": pr[r].get("model", "")} for r in pr}
    # reconstruct directional candidates from the union of Dir-XX objects across roles
    cands = {}
    for r in pr:
        for v in (pr[r].get("verdicts") or []):
            if isinstance(v, dict) and str(v.get("candidate_id", "")).startswith("Dir-"):
                cid = v["candidate_id"]
                lp_ids = v.get("lp_ids") or v.get("involved_lps") or []
                if isinstance(lp_ids, str):
                    lp_ids = [lp_ids]
                cands.setdefault(cid, {"candidate_id": cid, "lp_ids": lp_ids})
    return list(cands.values()), pass2_outputs


def run_real_builder_tests():
    print("== REAL builder over stored runs ==")
    ok = True
    for label, (run, expect) in RUNS.items():
        cands, p2 = _load_pass2(run)
        findings = build(cands, p2)
        n_inc = sum(1 for f in findings if f.get("verification_incomplete"))
        n_total = len(findings)
        # any incomplete finding must NOT carry HIGH/MED/LOW and must mark its dead role not_assessed
        bad = [f for f in findings if f.get("verification_incomplete")
               and (f.get("severity") != "VERIFICATION_INCOMPLETE"
                    or "not_assessed" not in (f.get("evaluator_verdicts") or {}).values())]
        fired = n_inc > 0
        want = (expect == "fire")
        status = "OK" if fired == want else "FAIL"
        if fired != want or bad:
            ok = False
        cause = ""
        if fired:
            ex = next(f for f in findings if f.get("verification_incomplete"))
            cause = " | sample roles=%s cause_empty_dir=%s sev=%s agree=%s ev=%s" % (
                ex.get("verification_incomplete_roles"),
                {r: c.get("empty_directional_output") for r, c in (ex.get("verification_incomplete_cause") or {}).items()},
                ex.get("severity"), ex.get("evaluator_agreement"), ex.get("evaluator_verdicts"))
        print("  [%s] %-32s findings=%2d verification_incomplete=%2d (expect %s)%s"
              % (status, label, n_total, n_inc, expect, cause))
    return ok


def synthetic_unit_test():
    print("== synthetic per-finding unit test ==")
    # Role A returns EMPTY directional output; B and C both confirm the same candidate.
    cands = [{"candidate_id": "Dir-01", "lp_ids": ["LP-05", "LP-11"]}]
    p2 = {
        "A": {"completed": True, "model": "claude-sonnet-4-6", "verdicts": []},  # empty -> _NO_OBJECT
        "B": {"completed": True, "model": "gpt-5.4", "verdicts": [
            {"candidate_id": "Dir-01", "candidate_type": "directional_mismatch", "lp_ids": ["LP-05", "LP-11"],
             "verdict": "mismatch_confirmed", "exposed_party": "tenant"}]},
        "C": {"completed": True, "model": "grok-4.3", "verdicts": [
            {"candidate_id": "Dir-01", "candidate_type": "directional_mismatch", "lp_ids": ["LP-05", "LP-11"],
             "verdict": "mismatch_confirmed"}]},
    }
    findings = build(cands, p2)
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["verification_incomplete"] is True
    assert f["verification_incomplete_roles"] == ["A"]
    assert f["severity"] == "VERIFICATION_INCOMPLETE", f["severity"]
    assert f["evaluator_verdicts"]["A"] == "not_assessed", f["evaluator_verdicts"]
    assert f["evaluator_verdicts"]["B"] == "mismatch_confirmed"
    assert f["evaluator_agreement"] == "2-0", f["evaluator_agreement"]  # 2 usable confirmed, 0 disagreed (NOT "2-1")
    assert f["verification_incomplete_cause"]["A"]["empty_directional_output"] is True
    print("  [OK] A-empty + B,C confirm -> verification_incomplete; A=not_assessed; sev=VERIFICATION_INCOMPLETE; agree=2-0 (not 2-1)")

    # CONTROL: all three usable and confirm -> NOT incomplete, normal HIGH 3-0 (line-1936 map untouched)
    p2b = {r: {"completed": True, "model": "m", "verdicts": [
        {"candidate_id": "Dir-01", "candidate_type": "directional_mismatch", "lp_ids": ["LP-05", "LP-11"],
         "verdict": "mismatch_confirmed", "exposed_party": "tenant"}]} for r in ("A", "B", "C")}
    g = build(cands, p2b)[0]
    assert g["verification_incomplete"] is False
    assert g["severity"] == "HIGH" and g["evaluator_agreement"] == "3-0", (g["severity"], g["evaluator_agreement"])
    print("  [OK] all-usable 3-0 -> severity HIGH, agree 3-0, verification_incomplete=False (clean path untouched)")

    # CONTROL: clean valid 2-1 semantic split (all usable, one no_mismatch) -> stays 2-1 MEDIUM, NOT incomplete
    p2c = {
        "A": {"completed": True, "model": "m", "verdicts": [{"candidate_id": "Dir-01", "candidate_type": "directional_mismatch", "lp_ids": ["LP-05", "LP-11"], "verdict": "mismatch_confirmed", "exposed_party": "tenant"}]},
        "B": {"completed": True, "model": "m", "verdicts": [{"candidate_id": "Dir-01", "candidate_type": "directional_mismatch", "lp_ids": ["LP-05", "LP-11"], "verdict": "no_mismatch"}]},
        "C": {"completed": True, "model": "m", "verdicts": [{"candidate_id": "Dir-01", "candidate_type": "directional_mismatch", "lp_ids": ["LP-05", "LP-11"], "verdict": "mismatch_confirmed"}]},
    }
    h = build(cands, p2c)[0]
    assert h["verification_incomplete"] is False, "clean 2-1 must NOT trip the wire"
    assert h["severity"] == "MEDIUM" and h["evaluator_agreement"] == "2-1"
    print("  [OK] clean valid 2-1 (B=no_mismatch, all usable) -> stays MEDIUM 2-1, verification_incomplete=False")
    return True


if __name__ == "__main__":
    a = run_real_builder_tests()
    b = synthetic_unit_test()
    print("\n%s" % ("ALL 375C VALIDATIONS PASSED" if (a and b) else "SOME 375C VALIDATIONS FAILED"))
    raise SystemExit(0 if (a and b) else 1)
