#!/usr/bin/env python3
"""
375E-COV-A Keyed Validation Script

Implements all checks from build_log/375E-COV-A_keyed_validation_protocol.md:
  A. 375M write-path closure (use_consequence written, gap_impact absent from LP use_impact)
  B. COV-A field population (all 26 directional + 6 CRX annotated)
  C. Empirical routing-drift check (routing fields unchanged vs frozen 52adbf baseline)
  D. Yield table -- four groups: already-assessed-8 / newly-admitted-18 / thin-gap-subset / compound-6
  E. Thin-gap diagnostic (LP-01/11/24/25 and any <20% missing -- decisive vs abstain signal)
  F. LP-05 sanity (adverse direction + beneficial consequence -- direction not re-litigated)
  G. LP-20 stability watch (record use_consequence value -- do NOT resolve)
  H. PUSH-OK / HOLD verdict against six explicit criteria

Usage:
  # Auto-discover freshest COV-A artifact:
  python build_log/_375ecova_keyed_validate.py

  # Run against a specific artifact:
  python build_log/_375ecova_keyed_validate.py <path/to/pipeline_results.json>

  # Baseline mode against frozen 52adbf (pre-COV-A):
  python build_log/_375ecova_keyed_validate.py --baseline

Output: writes build_log/375E_COV_A_keyed_validation.md and .json
"""

import json
import os
import sys
import glob
from datetime import datetime

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(REPO_ROOT, "05 Lease Analyzer", "results")
FROZEN_PATH = os.path.join(
    RESULTS_DIR,
    "lease_review_20260604_033046_52adbf",
    "tenant_0", "pipeline_results.json",
)
FROZEN_RUN_ID = "lease_review_20260604_033046_52adbf"

THIN_GAP_LPS = {"LP-01", "LP-11", "LP-24", "LP-25"}   # <20% missing, from 375N Q2

# Criteria for PUSH-OK
PUSH_CRITERIA = [
    "(1) use_consequence write-path correct (new LP use_impact has use_consequence key)",
    "(2) gap_impact absent from new LP use_impact records",
    "(3) COV-A fields populated on all directional findings (use_consequence_source present)",
    "(4) routing/buckets do not empirically drift (routing fields unchanged on all 32 findings)",
    "(5) no major parse/no_evaluators failure across the 18 newly-admitted findings (>= 14/18 decisive)",
    "(6) CRX not falsely treated as LP-level assessed (compound_consequence_source = not_assessed only)",
]


# ---- Helpers ----------------------------------------------------------------

def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize(use_impact):
    if not use_impact:
        return {}
    d = dict(use_impact)
    if "use_consequence" not in d and "gap_impact" in d:
        gi = d.pop("gap_impact", "") or ""
        d["use_consequence"] = {"favorable": "beneficial", "adverse": "harmful"}.get(gi.lower(), gi)
    return d


def _find_freshest_cova_artifact():
    """Find the most recently-modified pipeline_results.json that has COV-A fields."""
    candidates = glob.glob(
        os.path.join(RESULTS_DIR, "lease_review_*", "tenant_0", "pipeline_results.json")
    )
    cova_artifacts = []
    for p in candidates:
        try:
            data = _load(p)
            cpf = data.get("cross_provision_findings", [])
            # COV-A artifacts have compound_consequence_source or use_consequence_source on findings
            has_cova = any(
                "compound_consequence_source" in f or "use_consequence_source" in f
                for f in cpf
            )
            if has_cova:
                cova_artifacts.append((os.path.getmtime(p), p))
        except Exception:
            pass
    if not cova_artifacts:
        return None
    cova_artifacts.sort(reverse=True)
    return cova_artifacts[0][1]


def _run_id_from_path(path):
    parts = os.path.normpath(path).split(os.sep)
    for i, p in enumerate(parts):
        if p.startswith("lease_review_"):
            return p
    return os.path.basename(os.path.dirname(os.path.dirname(path)))


# ---- Check implementations --------------------------------------------------

def check_a_write_path(artifact, is_baseline=False):
    """A: 375M write-path closure -- use_consequence written, gap_impact absent."""
    ca = artifact.get("coverage_assessment", [])
    lps_with_ui = [(a.get("issue_area_id", "?"), a.get("use_impact", {}))
                   for a in ca if a.get("use_impact")]

    if is_baseline:
        # Frozen 52adbf uses gap_impact (pre-375M write path)
        has_gap_impact = [(pid, ui) for pid, ui in lps_with_ui if "gap_impact" in ui]
        has_use_consequence = [(pid, ui) for pid, ui in lps_with_ui if "use_consequence" in ui]
        return {
            "mode": "baseline_pre375M",
            "lps_with_use_impact": len(lps_with_ui),
            "has_gap_impact_key": len(has_gap_impact),
            "has_use_consequence_key": len(has_use_consequence),
            "note": "EXPECTED: frozen 52adbf artifact pre-dates a939b01 (375M deploy). "
                    "gap_impact present is correct for this artifact. "
                    "Fresh post-a939b01 artifact should have use_consequence only.",
            "pass": None,  # N/A for baseline
        }
    else:
        # Fresh artifact: must have use_consequence, must NOT have gap_impact
        has_gap_impact = [(pid, list(ui.keys())) for pid, ui in lps_with_ui if "gap_impact" in ui]
        missing_use_consequence = [(pid, list(ui.keys())) for pid, ui in lps_with_ui if "use_consequence" not in ui]
        bad_values = [
            (pid, ui.get("use_consequence"))
            for pid, ui in lps_with_ui
            if "use_consequence" in ui
            and ui["use_consequence"] not in {"beneficial", "neutral", "harmful", "context_dependent"}
        ]
        passed = (not has_gap_impact) and (not missing_use_consequence) and (not bad_values)
        return {
            "mode": "keyed_post375M",
            "lps_with_use_impact": len(lps_with_ui),
            "gap_impact_present_count": len(has_gap_impact),
            "gap_impact_present_lps": [pid for pid, _ in has_gap_impact],
            "missing_use_consequence_count": len(missing_use_consequence),
            "missing_use_consequence_lps": [pid for pid, _ in missing_use_consequence],
            "invalid_value_count": len(bad_values),
            "pass": passed,
        }


def check_b_field_population(artifact, is_baseline=False):
    """B: COV-A field population on all directional + CRX findings."""
    cpf = artifact.get("cross_provision_findings", [])
    ca = artifact.get("coverage_assessment", [])
    ca_by_lp = {a.get("issue_area_id", ""): a for a in ca}

    dir_findings = [f for f in cpf if f.get("finding_type") == "directional_mismatch"]
    cxr_findings = [f for f in cpf if f.get("finding_type") == "compound_risk"]

    REQUIRED_DIR_FIELDS = [
        "stage7_direction", "use_consequence", "materiality",
        "use_consequence_source", "materiality_source", "assessment_scope",
    ]

    dir_records = []
    for f in dir_findings:
        fid = f.get("finding_id", "?")
        lp_ids = f.get("implicated_lps") or []
        lp_id = lp_ids[0] if lp_ids else "?"
        lp = ca_by_lp.get(lp_id, {})
        has_lp_ui = "use_impact" in lp

        if is_baseline:
            dir_records.append({
                "finding_id": fid,
                "lp_id": lp_id,
                "has_cova_fields": False,
                "missing_fields": REQUIRED_DIR_FIELDS,
                "note": "pre-COV-A artifact",
            })
        else:
            missing = [field for field in REQUIRED_DIR_FIELDS if field not in f]
            src = f.get("use_consequence_source")
            already_assessed = has_lp_ui
            record = {
                "finding_id": fid,
                "lp_id": lp_id,
                "already_assessed_lp": already_assessed,
                "use_consequence": f.get("use_consequence"),
                "materiality": f.get("materiality"),
                "use_consequence_source": src,
                "materiality_source": f.get("materiality_source"),
                "assessment_scope": f.get("assessment_scope"),
                "stage7_direction": f.get("stage7_direction"),
                "directionality": f.get("directionality"),
                "missing_fields": missing,
                "has_cova_fields": len(missing) == 0,
                "thin_gap": lp_id in THIN_GAP_LPS,
            }
            dir_records.append(record)

    crx_records = []
    for f in cxr_findings:
        fid = f.get("finding_id", "?")
        crx_src = f.get("compound_consequence_source")
        crx_records.append({
            "finding_id": fid,
            "compound_consequence_source": crx_src,
            "has_cova_field": crx_src == "not_assessed",
            "has_lp_consequence_wrongly": "use_consequence" in f,
        })

    dir_populated = sum(1 for r in dir_records if r.get("has_cova_fields"))
    crx_correct = sum(1 for r in crx_records if r.get("has_cova_field") and not r.get("has_lp_consequence_wrongly"))

    passed = (not is_baseline) and (dir_populated == len(dir_findings)) and (crx_correct == len(cxr_findings))

    return {
        "total_directional": len(dir_findings),
        "total_compound": len(cxr_findings),
        "directional_populated": dir_populated,
        "compound_correct": crx_correct,
        "directional_records": dir_records,
        "compound_records": crx_records,
        "pass": passed,
    }


def check_c_routing_drift(artifact, baseline_artifact, is_baseline=False):
    """C: Empirical routing-drift check vs frozen 52adbf baseline."""
    ROUTING_FIELDS = ["finding_id", "finding_type", "directionality", "severity", "verdict"]

    fresh_cpf = artifact.get("cross_provision_findings", [])
    baseline_cpf = baseline_artifact.get("cross_provision_findings", [])

    if is_baseline:
        return {
            "mode": "baseline_self_comparison",
            "note": "Baseline artifact -- no drift check applicable (comparing artifact to itself).",
            "drift_count": 0,
            "pass": None,
        }

    # Index by finding_id
    baseline_by_id = {f.get("finding_id"): f for f in baseline_cpf}
    fresh_by_id = {f.get("finding_id"): f for f in fresh_cpf}

    drifts = []
    for fid, fresh in fresh_by_id.items():
        baseline = baseline_by_id.get(fid)
        if baseline is None:
            drifts.append({"finding_id": fid, "issue": "finding present in keyed run but not in baseline"})
            continue
        for field in ROUTING_FIELDS:
            bv = baseline.get(field)
            fv = fresh.get(field)
            if bv != fv:
                drifts.append({
                    "finding_id": fid, "field": field,
                    "baseline": bv, "fresh": fv,
                })

    # Check for findings in baseline but missing from fresh (unexpected removal)
    for fid in baseline_by_id:
        if fid not in fresh_by_id:
            drifts.append({"finding_id": fid, "issue": "finding in baseline but missing from fresh run"})

    # Check that COV-A fields are NOT in the routing path
    # (i.e., the existing routing logic doesn't read use_consequence_source to determine bucket)
    # This is structural -- we note it as confirmed if routing fields match
    routing_match = len(drifts) == 0

    return {
        "mode": "empirical_vs_baseline",
        "note": (
            "FRAMING: keyless 0-drift was structural (additive-only writes). "
            "This is the empirical confirmation -- routing fields compared "
            "field-by-field between fresh keyed artifact and frozen 52adbf baseline."
        ),
        "baseline_finding_count": len(baseline_cpf),
        "fresh_finding_count": len(fresh_cpf),
        "drift_count": len(drifts),
        "drifts": drifts,
        "cova_fields_not_in_routing_path": routing_match,
        "pass": routing_match,
    }


def check_d_yield_table(artifact, is_baseline=False):
    """D: Yield table -- four groups."""
    cpf = artifact.get("cross_provision_findings", [])
    ca = artifact.get("coverage_assessment", [])
    ca_by_lp = {a.get("issue_area_id", ""): a for a in ca}

    dir_findings = [f for f in cpf if f.get("finding_type") == "directional_mismatch"]
    crx_findings = [f for f in cpf if f.get("finding_type") == "compound_risk"]

    if is_baseline:
        # No COV-A fields -- show LP-scope use_impact for already-assessed 8 only
        already_assessed = []
        for f in dir_findings:
            lp_ids = f.get("implicated_lps") or []
            lp_id = lp_ids[0] if lp_ids else ""
            lp = ca_by_lp.get(lp_id, {})
            if "use_impact" in lp:
                ui = _normalize(lp.get("use_impact", {}))
                already_assessed.append({
                    "finding_id": f.get("finding_id"),
                    "lp_id": lp_id,
                    "use_consequence": ui.get("use_consequence"),
                    "materiality": ui.get("materiality"),
                    "confidence": ui.get("confidence"),
                    "source": "lp_scope_pre_cova",
                })
        return {
            "mode": "baseline_lp_scope_only",
            "note": "Pre-COV-A artifact -- no finding-scope COV-A fields. Showing LP-scope use_impact for 8 already-assessed LPs only.",
            "group1_already_assessed_8": already_assessed,
            "group2_newly_admitted_18": "PENDING -- keyed run required",
            "group3_thin_gap_subset": "PENDING -- keyed run required",
            "group4_compound_6": [{"finding_id": f.get("finding_id"), "compound_consequence_source": f.get("compound_consequence_source", "ABSENT-pre-COV-A")} for f in crx_findings],
        }

    # Full yield table from fresh artifact
    group1 = []  # already-assessed 8 (source=assessed, had LP use_impact)
    group2 = []  # newly-admitted 18 (source=assessed or absent, no prior LP use_impact)
    group3 = []  # thin-gap subset (LP-01/11/24/25 from group2)

    for f in dir_findings:
        lp_ids = f.get("implicated_lps") or []
        lp_id = lp_ids[0] if lp_ids else ""
        lp = ca_by_lp.get(lp_id, {})
        had_lp_ui = "use_impact" in lp

        record = {
            "finding_id": f.get("finding_id"),
            "lp_id": lp_id,
            "use_consequence": f.get("use_consequence"),
            "materiality": f.get("materiality"),
            "use_consequence_source": f.get("use_consequence_source"),
            "assessment_scope": f.get("assessment_scope"),
            "directionality": f.get("directionality"),
        }

        if had_lp_ui:
            group1.append(record)
        else:
            group2.append(record)
            if lp_id in THIN_GAP_LPS:
                group3.append(record)

    def _tally(records):
        decisive = [r for r in records if r.get("use_consequence_source") == "assessed"
                    and r.get("use_consequence") in {"beneficial", "neutral", "harmful"}]
        ctx_dep = [r for r in records if r.get("use_consequence") == "context_dependent"]
        absent = [r for r in records if r.get("use_consequence_source") == "absent"]
        harmful = [r for r in records if r.get("use_consequence") == "harmful"]
        neutral = [r for r in records if r.get("use_consequence") == "neutral"]
        beneficial = [r for r in records if r.get("use_consequence") == "beneficial"]
        high = [r for r in records if r.get("materiality") == "high"]
        medium = [r for r in records if r.get("materiality") == "medium"]
        low = [r for r in records if r.get("materiality") == "low"]
        return {
            "count": len(records),
            "decisive": len(decisive),
            "harmful": len(harmful), "neutral": len(neutral), "beneficial": len(beneficial),
            "context_dependent": len(ctx_dep),
            "absent": len(absent),
            "high": len(high), "medium": len(medium), "low": len(low),
        }

    g4 = [{"finding_id": f.get("finding_id"),
            "compound_consequence_source": f.get("compound_consequence_source"),
            "wrongly_has_use_consequence": "use_consequence" in f}
           for f in crx_findings]

    return {
        "mode": "keyed_full",
        "group1_already_assessed_8": {"tally": _tally(group1), "records": group1},
        "group2_newly_admitted_18": {"tally": _tally(group2), "records": group2},
        "group3_thin_gap_subset": {"tally": _tally(group3), "records": group3},
        "group4_compound_6": g4,
    }


def check_e_thin_gap_diagnostic(d_result, is_baseline=False):
    """E: Thin-gap diagnostic (LP-01/11/24/25) -- decisive vs abstain signal."""
    if is_baseline:
        return {
            "mode": "baseline",
            "note": "PENDING -- keyed run required. Thin-gap LPs are LP-01/11/24/25 (<20% missing). "
                    "Decisive = design signal that G-cand works on mostly-complete LPs. "
                    "Abstain = evidence base for shelved A-rail and COV-B Needs-Review landing.",
        }

    g3 = d_result.get("group3_thin_gap_subset", {})
    records = g3.get("records", []) if isinstance(g3, dict) else []
    tally = g3.get("tally", {}) if isinstance(g3, dict) else {}

    decisive_records = [r for r in records if r.get("use_consequence_source") == "assessed"
                        and r.get("use_consequence") in {"beneficial", "neutral", "harmful"}]
    abstain_records = [r for r in records
                       if r.get("use_consequence") == "context_dependent"
                       or r.get("use_consequence_source") == "absent"]

    if not records:
        interpretation = "No thin-gap findings in this artifact -- cannot assess."
    elif len(decisive_records) == len(records):
        interpretation = (
            "ALL DECISIVE: G-cand finding-trigger works even on mostly-complete LPs. "
            "Strong signal that consequence IS assessable from finding-level context "
            "without requiring high element-gap %. A-rail may not be needed for this LP class."
        )
    elif len(abstain_records) > len(decisive_records):
        interpretation = (
            "MOSTLY ABSTAIN: thin-gap LPs are not well-assessed by finding-scope 5e. "
            "Signal for COV-B: needs 'directional concern + consequence not assessable -> Needs Review' landing. "
            "Also supports evidence-based case for shelved A-rail (a class 5e can't assess)."
        )
    else:
        interpretation = (
            "MIXED: %d decisive, %d abstain/context_dependent. "
            "COV-B should handle both decisive and unassessable landings."
        ) % (len(decisive_records), len(abstain_records))

    return {
        "mode": "keyed",
        "thin_gap_lps": list(THIN_GAP_LPS),
        "count_found": len(records),
        "decisive_count": len(decisive_records),
        "abstain_count": len(abstain_records),
        "records": records,
        "interpretation": interpretation,
        "design_signal": "decisive" if len(decisive_records) >= len(abstain_records) else "abstain",
    }


def check_f_lp05_sanity(artifact, is_baseline=False):
    """F: LP-05 sanity check."""
    cpf = artifact.get("cross_provision_findings", [])
    ca = artifact.get("coverage_assessment", [])

    dir05 = next((f for f in cpf if f.get("finding_id") == "Dir-05"), None)
    lp05_ca = next((a for a in ca if a.get("issue_area_id") == "LP-05"), None)

    if is_baseline:
        lp05_ui = _normalize(lp05_ca.get("use_impact", {}) if lp05_ca else {})
        return {
            "mode": "baseline",
            "lp05_use_impact": lp05_ui,
            "dir05_directionality": dir05.get("directionality") if dir05 else None,
            "note": "Pre-COV-A: no finding-level use_consequence on Dir-05. "
                    "LP-05 use_impact shows beneficial from LP-scope 5e. "
                    "Fresh keyed artifact should show Dir-05 use_consequence=beneficial, "
                    "stage7_direction=tenant_unprotected, no sign_conflict field.",
        }

    if not dir05:
        return {"pass": False, "note": "Dir-05 not found in cross_provision_findings"}

    directionality = dir05.get("directionality")
    use_consequence = dir05.get("use_consequence")
    stage7_dir = dir05.get("stage7_direction")
    has_sign_conflict = "sign_conflict" in dir05

    passed = (
        directionality == "tenant_unprotected"
        and use_consequence == "beneficial"
        and stage7_dir == "tenant_unprotected"
        and not has_sign_conflict
    )

    return {
        "mode": "keyed",
        "finding_id": "Dir-05",
        "lp_id": "LP-05",
        "directionality": directionality,
        "stage7_direction": stage7_dir,
        "use_consequence": use_consequence,
        "materiality": dir05.get("materiality"),
        "use_consequence_source": dir05.get("use_consequence_source"),
        "sign_conflict_field_present": has_sign_conflict,
        "doctrine_holds": (directionality == "tenant_unprotected" and use_consequence == "beneficial"),
        "note": (
            "Doctrine: Stage 7 owns direction sign (tenant_unprotected/adverse); "
            "5e owns consequence magnitude. Adverse directional + beneficial use_consequence is "
            "architecturally correct -- absence of use restriction = operational flexibility."
        ),
        "pass": passed,
    }


def check_g_lp20_watch(artifact, is_baseline=False):
    """G: LP-20 stability watch -- record, do NOT resolve."""
    cpf = artifact.get("cross_provision_findings", [])
    ca = artifact.get("coverage_assessment", [])

    dir16 = next((f for f in cpf if f.get("finding_id") == "Dir-16"), None)
    lp20_ca = next((a for a in ca if a.get("issue_area_id") == "LP-20"), None)

    lp20_ui_raw = lp20_ca.get("use_impact", {}) if lp20_ca else {}
    lp20_ui = _normalize(lp20_ui_raw)

    result = {
        "lp_id": "LP-20",
        "finding_id": "Dir-16",
        "lp_scope_use_impact": lp20_ui,
        "lp_scope_raw_keys": list(lp20_ui_raw.keys()),
        "note": (
            "LP-20 is a WATCH item, not a pass/fail gate. "
            "Known: 2-1 assert_weak in frozen 52adbf. "
            "Record this run's value without resolving stability -- "
            "single keyed result does not prove stability."
        ),
    }

    if not is_baseline and dir16:
        result["finding_use_consequence"] = dir16.get("use_consequence")
        result["finding_materiality"] = dir16.get("materiality")
        result["finding_use_consequence_source"] = dir16.get("use_consequence_source")
        result["finding_stage7_direction"] = dir16.get("stage7_direction")
        result["finding_has_use_consequence_key"] = "use_consequence" in dir16

    if is_baseline:
        result["mode"] = "baseline"
        result["baseline_value"] = lp20_ui.get("use_consequence", "ABSENT")
        result["baseline_confidence"] = lp20_ui.get("confidence", "ABSENT")
    else:
        result["mode"] = "keyed"
        result["keyed_value"] = dir16.get("use_consequence") if dir16 else "NOT FOUND"

    return result


def check_h_verdict(checks, is_baseline=False):
    """H: PUSH-OK / HOLD verdict."""
    if is_baseline:
        return {
            "verdict": "HOLD",
            "note": "Baseline mode: running against pre-COV-A frozen artifact (52adbf). "
                    "COV-A fields are absent by design -- this artifact predates commit 771f1ef. "
                    "HOLD PUSH until fresh post-771f1ef keyed artifact is validated.",
            "criteria_results": {c: "N/A (baseline artifact)" for c in PUSH_CRITERIA},
            "failed_criteria": [],
        }

    criteria_results = {}
    c_a = checks.get("a", {})
    c_b = checks.get("b", {})
    c_c = checks.get("c", {})
    c_d = checks.get("d", {})
    c_f = checks.get("f", {})

    # Criterion 1: use_consequence write-path correct
    c1_pass = c_a.get("pass", False)
    criteria_results[PUSH_CRITERIA[0]] = "PASS" if c1_pass else "FAIL"

    # Criterion 2: gap_impact absent from new LP use_impact
    c2_pass = c_a.get("gap_impact_present_count", 1) == 0
    criteria_results[PUSH_CRITERIA[1]] = "PASS" if c2_pass else "FAIL"

    # Criterion 3: COV-A fields populated on all directional findings
    b_pass = c_b.get("pass", False)
    criteria_results[PUSH_CRITERIA[2]] = "PASS" if b_pass else "FAIL"

    # Criterion 4: routing does not empirically drift
    c_pass = c_c.get("pass", False)
    criteria_results[PUSH_CRITERIA[3]] = "PASS" if c_pass else "FAIL"

    # Criterion 5: >= 14/18 decisive across newly-admitted 18
    g2 = c_d.get("group2_newly_admitted_18", {})
    if isinstance(g2, dict):
        decisive = g2.get("tally", {}).get("decisive", 0)
        total_g2 = g2.get("tally", {}).get("count", 0)
        c5_pass = decisive >= 14 if total_g2 == 18 else decisive >= (total_g2 * 0.75)
    else:
        decisive = 0
        c5_pass = False
    criteria_results[PUSH_CRITERIA[4]] = "PASS (%d/%d decisive)" % (decisive, 18) if c5_pass else "FAIL (%d decisive)" % decisive

    # Criterion 6: CRX not falsely treated as LP-level assessed
    g4 = c_d.get("group4_compound_6", [])
    crx_wrong = [r for r in g4 if r.get("wrongly_has_use_consequence")]
    c6_pass = len(crx_wrong) == 0
    criteria_results[PUSH_CRITERIA[5]] = "PASS" if c6_pass else "FAIL (%d CRX wrongly have use_consequence)" % len(crx_wrong)

    all_pass = c1_pass and c2_pass and b_pass and c_pass and c5_pass and c6_pass
    failed = [c for c, r in criteria_results.items() if r.startswith("FAIL")]

    return {
        "verdict": "PUSH-OK" if all_pass else "HOLD",
        "all_criteria_passed": all_pass,
        "criteria_results": criteria_results,
        "failed_criteria": failed,
        "note": (
            "PUSH-OK is Tzvi's call after reviewing this report. "
            "All criteria met." if all_pass
            else "HOLD: %d criterion/criteria failed. Do not push until resolved." % len(failed)
        ),
    }


# ---- Report writers ---------------------------------------------------------

def write_md(run_id, artifact_path, checks, is_baseline):
    lines = [
        "# 375E-COV-A Keyed Validation Report",
        "",
        "**Date:** 2026-06-05",
        "**Run ID:** " + run_id,
        "**Artifact path:** " + artifact_path,
        "**Mode:** " + ("PRE-COV-A BASELINE (52adbf, pre-771f1ef)" if is_baseline else "KEYED POST-COV-A"),
        "",
    ]

    if is_baseline:
        lines += [
            "> **BASELINE NOTICE:** This report was run against the frozen pre-COV-A artifact",
            "> (52adbf, last modified 2026-06-03). COV-A fields are ABSENT by design -- this",
            "> artifact predates commit 771f1ef. Sections below show the pre-COV-A state for",
            "> context. **Verdict is HOLD until a fresh post-771f1ef keyed artifact is validated.**",
            "",
            "> **Re-run command** (after Tzvi's local pipeline completes):",
            "> ```",
            "> python build_log/_375ecova_keyed_validate.py <path/to/fresh/pipeline_results.json>",
            "> ```",
            "",
        ]

    # Verdict first (most important)
    h = checks.get("h", {})
    verdict = h.get("verdict", "UNKNOWN")
    lines += [
        "## Verdict: " + verdict,
        "",
        h.get("note", ""),
        "",
        "### Six Push Criteria",
        "",
    ]
    for c, r in h.get("criteria_results", {}).items():
        tag = "PASS" if r.startswith("PASS") else ("N/A" if r.startswith("N/A") else "FAIL")
        prefix = "[+]" if tag == "PASS" else ("[~]" if tag == "N/A" else "[-]")
        lines.append(f"  {prefix} {c}: {r}")
    lines.append("")

    # Check A
    a = checks.get("a", {})
    lines += [
        "---",
        "",
        "## A. 375M Write-Path Closure",
        "",
    ]
    if is_baseline:
        lines += [
            "**Mode:** baseline (pre-375M artifact -- gap_impact present is EXPECTED)",
            "",
            "- LPs with use_impact: %d" % a.get("lps_with_use_impact", 0),
            "- Has gap_impact key: %d (expected for pre-375M artifact)" % a.get("has_gap_impact_key", 0),
            "- Has use_consequence key: %d (expected: 0 for pre-375M artifact)" % a.get("has_use_consequence_key", 0),
            "",
            a.get("note", ""),
            "",
        ]
    else:
        p = "[PASS]" if a.get("pass") else "[FAIL]"
        lines += [
            f"**Result:** {p}",
            "",
            "- LPs with use_impact: %d" % a.get("lps_with_use_impact", 0),
            "- gap_impact keys present (must be 0): %d %s" % (
                a.get("gap_impact_present_count", 0),
                str(a.get("gap_impact_present_lps", []))
            ),
            "- missing use_consequence keys (must be 0): %d %s" % (
                a.get("missing_use_consequence_count", 0),
                str(a.get("missing_use_consequence_lps", []))
            ),
            "- invalid use_consequence values (must be 0): %d" % a.get("invalid_value_count", 0),
            "",
        ]

    # Check B
    b = checks.get("b", {})
    lines += [
        "---",
        "",
        "## B. COV-A Field Population",
        "",
    ]
    if is_baseline:
        lines += [
            "**Mode:** baseline -- COV-A fields ABSENT (expected for pre-COV-A artifact)",
            "",
            "Directional findings: %d (none have COV-A fields)" % b.get("total_directional", 0),
            "Compound findings: %d (no compound_consequence_source yet)" % b.get("total_compound", 0),
            "",
        ]
    else:
        p = "[PASS]" if b.get("pass") else "[FAIL]"
        lines += [
            f"**Result:** {p}",
            "",
            "- Total directional: %d, COV-A fields populated: %d" % (b.get("total_directional", 0), b.get("directional_populated", 0)),
            "- Total compound: %d, compound_consequence_source correct: %d" % (b.get("total_compound", 0), b.get("compound_correct", 0)),
            "",
            "### Per-finding detail (directional)",
            "",
            "| Finding | LP | Already-Assessed | use_consequence | materiality | source | OK |",
            "|---------|-----|------------------|-----------------|-------------|--------|----|",
        ]
        for r in b.get("directional_records", []):
            aa = "Y" if r.get("already_assessed_lp") else "N"
            ok = "[+]" if r.get("has_cova_fields") else "[-]"
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                r.get("finding_id", "?"),
                r.get("lp_id", "?"),
                aa,
                r.get("use_consequence", "ABSENT"),
                r.get("materiality", "ABSENT"),
                r.get("use_consequence_source", "ABSENT"),
                ok,
            ))
        lines.append("")
        lines += ["### Compound findings", ""]
        for r in b.get("compound_records", []):
            ok = "[+]" if r.get("has_cova_field") else "[-]"
            lines.append("- %s: compound_consequence_source=%s %s" % (
                r.get("finding_id"), r.get("compound_consequence_source"), ok
            ))
        lines.append("")

    # Check C
    c = checks.get("c", {})
    lines += [
        "---",
        "",
        "## C. Empirical Routing-Drift Check",
        "",
        "> **FRAMING:** The keyless 0-drift check was STRUCTURAL (additive-only field writes, ",
        "> routing drift structurally impossible). This is the EMPIRICAL confirmation --",
        "> routing fields compared field-by-field between fresh artifact and frozen 52adbf baseline.",
        "> These are different claims; the structural argument does not prove empirical 0-drift.",
        "",
    ]
    if is_baseline:
        lines += [
            "**Mode:** baseline -- not applicable (no fresh artifact to compare against).",
            "",
        ]
    else:
        p = "[PASS]" if c.get("pass") else "[FAIL]"
        lines += [
            f"**Result:** {p}",
            "",
            "- Baseline finding count: %d" % c.get("baseline_finding_count", 0),
            "- Fresh finding count: %d" % c.get("fresh_finding_count", 0),
            "- Routing field drift count (must be 0): %d" % c.get("drift_count", 0),
        ]
        if c.get("drifts"):
            for d in c["drifts"]:
                lines.append("  - [%s] %s: %r -> %r" % (
                    d.get("finding_id"), d.get("field"), d.get("baseline"), d.get("fresh")
                ))
        lines.append("")

    # Check D
    d = checks.get("d", {})
    lines += [
        "---",
        "",
        "## D. Yield Table (Four Groups)",
        "",
    ]
    if is_baseline:
        g1 = d.get("group1_already_assessed_8", [])
        lines += [
            "**Mode:** baseline -- only LP-scope use_impact shown for 8 already-assessed LPs.",
            "",
            "### Group 1: Already-assessed 8 (LP-scope use_impact, copied in COV-A)",
            "",
            "| Finding | LP | use_consequence | materiality | confidence |",
            "|---------|-----|-----------------|-------------|------------|",
        ]
        for r in g1:
            lines.append("| %s | %s | %s | %s | %s |" % (
                r.get("finding_id"), r.get("lp_id"),
                r.get("use_consequence"), r.get("materiality"), r.get("confidence")
            ))
        lines += [
            "",
            "### Groups 2, 3, 4: PENDING -- keyed run required",
            "",
        ]
    else:
        def _tally_line(tally):
            return ("count=%d | decisive=%d | harmful=%d neutral=%d beneficial=%d ctx_dep=%d absent=%d | "
                    "high=%d med=%d low=%d") % (
                tally.get("count", 0), tally.get("decisive", 0),
                tally.get("harmful", 0), tally.get("neutral", 0),
                tally.get("beneficial", 0), tally.get("context_dependent", 0),
                tally.get("absent", 0),
                tally.get("high", 0), tally.get("medium", 0), tally.get("low", 0),
            )

        g1 = d.get("group1_already_assessed_8", {})
        g2 = d.get("group2_newly_admitted_18", {})
        g3 = d.get("group3_thin_gap_subset", {})
        g4 = d.get("group4_compound_6", [])

        lines += [
            "### Group 1: Already-assessed 8 (copied from LP-scope use_impact)",
            "",
            _tally_line(g1.get("tally", {})),
            "",
            "| Finding | LP | use_consequence | materiality | source |",
            "|---------|-----|-----------------|-------------|--------|",
        ]
        for r in g1.get("records", []):
            lines.append("| %s | %s | %s | %s | %s |" % (
                r.get("finding_id"), r.get("lp_id"),
                r.get("use_consequence"), r.get("materiality"), r.get("use_consequence_source")
            ))

        lines += [
            "",
            "### Group 2: Newly-admitted 18 (G-cand, finding-scope 5e)",
            "",
            _tally_line(g2.get("tally", {})),
            "",
            "| Finding | LP | use_consequence | materiality | source | thin-gap |",
            "|---------|-----|-----------------|-------------|--------|----------|",
        ]
        for r in g2.get("records", []):
            tg = "Y" if r.get("thin_gap") else "N"
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                r.get("finding_id"), r.get("lp_id"),
                r.get("use_consequence"), r.get("materiality"),
                r.get("use_consequence_source"), tg
            ))

        lines += [
            "",
            "### Group 3: Thin-gap subset (LP-01/11/24/25 and <20% missing)",
            "",
            _tally_line(g3.get("tally", {})),
            "",
        ]

        lines += [
            "",
            "### Group 4: Compound findings (CRX-01 through CRX-06)",
            "",
        ]
        for r in g4:
            ok = "[+]" if r.get("compound_consequence_source") == "not_assessed" and not r.get("wrongly_has_use_consequence") else "[-]"
            lines.append("- %s: compound_consequence_source=%s %s" % (
                r.get("finding_id"), r.get("compound_consequence_source"), ok
            ))
        lines.append("")

    # Check E
    e = checks.get("e", {})
    lines += [
        "---",
        "",
        "## E. Thin-Gap Diagnostic (Design Signal)",
        "",
        "> Thin-gap LPs: LP-01/11/24/25 (<20% element-gap %). These are admitted by G-cand",
        "> (finding-triggered) but NOT by A33 threshold. Whether they assess DECISIVELY is a",
        "> design signal for COV-B and the shelved A-rail, not a pass/fail gate.",
        "",
    ]
    if is_baseline:
        lines += [e.get("note", ""), ""]
    else:
        lines += [
            "**Design signal:** " + e.get("design_signal", "UNKNOWN").upper(),
            "",
            "- Thin-gap LPs found: %d of %d expected" % (e.get("count_found", 0), len(THIN_GAP_LPS)),
            "- Decisive (assessed, non-context_dependent): %d" % e.get("decisive_count", 0),
            "- Abstain/context_dependent: %d" % e.get("abstain_count", 0),
            "",
            "**Interpretation:** " + e.get("interpretation", ""),
            "",
        ]

    # Check F
    f = checks.get("f", {})
    lines += [
        "---",
        "",
        "## F. LP-05 Sanity Check",
        "",
    ]
    if is_baseline:
        lines += [
            "**Mode:** baseline",
            "",
            "LP-05 LP-scope use_impact: use_consequence=%s, materiality=%s" % (
                f.get("lp05_use_impact", {}).get("use_consequence", "ABSENT"),
                f.get("lp05_use_impact", {}).get("materiality", "ABSENT"),
            ),
            "Dir-05 directionality: %s" % f.get("dir05_directionality"),
            "",
            f.get("note", ""),
            "",
        ]
    else:
        p = "[PASS]" if f.get("pass") else "[FAIL]"
        lines += [
            f"**Result:** {p}",
            "",
            "- directionality: %s (expected: tenant_unprotected)" % f.get("directionality"),
            "- stage7_direction: %s (expected: tenant_unprotected)" % f.get("stage7_direction"),
            "- use_consequence: %s (expected: beneficial)" % f.get("use_consequence"),
            "- materiality: %s" % f.get("materiality"),
            "- sign_conflict field present: %s (expected: False)" % f.get("sign_conflict_field_present"),
            "- Doctrine holds (adverse direction + beneficial consequence): %s" % f.get("doctrine_holds"),
            "",
            f.get("note", ""),
            "",
        ]

    # Check G
    g = checks.get("g", {})
    lines += [
        "---",
        "",
        "## G. LP-20 Stability Watch (Record Only)",
        "",
        "> LP-20 is a WATCH item, not a gate. Single run result does not prove stability.",
        "",
        "- LP-scope use_impact: use_consequence=%s, confidence=%s" % (
            g.get("lp_scope_use_impact", {}).get("use_consequence", "ABSENT"),
            g.get("lp_scope_use_impact", {}).get("confidence", "ABSENT"),
        ),
        "- LP-scope raw keys: %s" % str(g.get("lp_scope_raw_keys", [])),
    ]
    if not is_baseline:
        lines += [
            "- Finding Dir-16 use_consequence (fresh keyed): %s" % g.get("keyed_value", "NOT FOUND"),
            "- Finding Dir-16 use_consequence_source: %s" % g.get("finding_use_consequence_source"),
            "- use_consequence key present on finding: %s" % g.get("finding_has_use_consequence_key"),
        ]
    lines += [
        "",
        g.get("note", ""),
        "",
    ]

    # Closing
    lines += [
        "---",
        "",
        "## Summary Verdict: " + h.get("verdict", "UNKNOWN"),
        "",
        h.get("note", ""),
        "",
    ]
    if not is_baseline and h.get("failed_criteria"):
        lines += ["**Failed criteria:**", ""]
        for c in h["failed_criteria"]:
            lines.append("- " + c)
        lines.append("")

    return "\n".join(lines)


def write_json(run_id, artifact_path, checks, is_baseline):
    return {
        "schema": "375E-COV-A-keyed-validation-v1",
        "date": "2026-06-05",
        "run_id": run_id,
        "artifact_path": artifact_path,
        "mode": "baseline_pre_cova" if is_baseline else "keyed_post_cova",
        "verdict": checks.get("h", {}).get("verdict", "UNKNOWN"),
        "checks": checks,
    }


# ---- Main -------------------------------------------------------------------

def main():
    baseline_mode = "--baseline" in sys.argv
    explicit_path = next((a for a in sys.argv[1:] if not a.startswith("--")), None)

    if baseline_mode or explicit_path is None:
        # Try to find fresh COV-A artifact first
        if not baseline_mode:
            fresh = _find_freshest_cova_artifact()
            if fresh:
                artifact_path = fresh
                is_baseline = False
                print("Auto-discovered COV-A artifact: " + artifact_path)
            else:
                print("No post-COV-A artifact found. Running in BASELINE mode against frozen 52adbf.")
                print("(Run again with the path to the fresh artifact once your pipeline completes)")
                artifact_path = FROZEN_PATH
                is_baseline = True
        else:
            artifact_path = FROZEN_PATH
            is_baseline = True
    else:
        artifact_path = explicit_path
        is_baseline = False

    artifact = _load(artifact_path)
    baseline_artifact = _load(FROZEN_PATH)
    run_id = _run_id_from_path(artifact_path)

    print("Run ID: " + run_id)
    print("Mode: " + ("BASELINE (pre-COV-A)" if is_baseline else "KEYED (post-COV-A)"))
    print("")

    checks = {}
    print("Running check A (375M write-path)...")
    checks["a"] = check_a_write_path(artifact, is_baseline)

    print("Running check B (COV-A field population)...")
    checks["b"] = check_b_field_population(artifact, is_baseline)

    print("Running check C (empirical routing drift)...")
    checks["c"] = check_c_routing_drift(artifact, baseline_artifact, is_baseline)

    print("Running check D (yield table)...")
    checks["d"] = check_d_yield_table(artifact, is_baseline)

    print("Running check E (thin-gap diagnostic)...")
    checks["e"] = check_e_thin_gap_diagnostic(checks["d"], is_baseline)

    print("Running check F (LP-05 sanity)...")
    checks["f"] = check_f_lp05_sanity(artifact, is_baseline)

    print("Running check G (LP-20 watch)...")
    checks["g"] = check_g_lp20_watch(artifact, is_baseline)

    print("Running check H (verdict)...")
    checks["h"] = check_h_verdict(checks, is_baseline)

    # Write outputs
    out_dir = os.path.join(REPO_ROOT, "build_log")

    md_path = os.path.join(out_dir, "375E_COV_A_keyed_validation.md")
    json_path = os.path.join(out_dir, "375E_COV_A_keyed_validation.json")

    md_content = write_md(run_id, artifact_path, checks, is_baseline)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    json_content = write_json(run_id, artifact_path, checks, is_baseline)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_content, f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 60)
    print("VERDICT: " + checks["h"]["verdict"])
    print(checks["h"]["note"])
    print("=" * 60)
    print("")
    print("Outputs written:")
    print("  " + md_path)
    print("  " + json_path)

    if is_baseline:
        print("")
        print("Re-run against fresh artifact after your local pipeline completes:")
        print("  python build_log/_375ecova_keyed_validate.py <path/to/fresh/pipeline_results.json>")


if __name__ == "__main__":
    main()
