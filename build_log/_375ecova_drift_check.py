#!/usr/bin/env python3
"""
375E-COV-A Keyless 0-Drift Harness

Asserts that assess_finding_consequence() adds provenance fields to
cross_provision_findings WITHOUT mutating any routing-relevant field.

Routing fields checked (must be identical before and after):
  finding_id, finding_type, directionality, severity, verdict

Also asserts:
  - Every directional_mismatch finding gains all required provenance fields
    (stage7_direction, use_consequence, use_consequence_source,
     materiality, materiality_source, assessment_scope)
  - Every compound_risk finding gains compound_consequence_source = "not_assessed"
  - Finding counts match 375J expectations (26 directional, 6 compound)

Mode: KEYLESS -- no model calls. use_profile=None triggers absent-marking
for unassessed findings. Already-assessed LP use_impact is copied directly.

Run from the repo root:
  python build_log/_375ecova_drift_check.py

Expected output:
  [PASS] 0 routing drift across all 32 findings
  [PASS] Provenance fields present on all 26 directional findings
  [PASS] compound_consequence_source on all 6 compound findings
  [PASS] Finding counts verified (26 directional, 6 compound)

Any [FAIL] line means COV-A has a routing side-effect and must be fixed before deploy.
"""

import json
import copy
import sys
import os

# ---- Paths -------------------------------------------------------------------
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
FROZEN_ARTIFACT = os.path.join(
    REPO_ROOT,
    "05 Lease Analyzer", "results",
    "lease_review_20260604_033046_52adbf",
    "tenant_0", "pipeline_results.json",
)
RESULTS_375J = os.path.join(REPO_ROOT, "build_log", "375J_results.json")

# ---- Routing fields that must NOT change -------------------------------------
# Note: "current_bucket" is NOT stored on findings in pipeline_results.json;
# it is a derived field computed downstream. Only fields present on raw findings
# are checked here.
ROUTING_FIELDS = ["finding_id", "finding_type", "directionality", "severity", "verdict"]

# ---- Expected counts from 375J (ground truth) --------------------------------
EXPECTED_DIRECTIONAL_COUNT = 26
EXPECTED_COMPOUND_COUNT = 6

# ---- Required provenance fields on directional findings ----------------------
REQUIRED_DIRECTIONAL_FIELDS = [
    "stage7_direction",
    "use_consequence",
    "materiality",
    "use_consequence_source",
    "materiality_source",
    "assessment_scope",
]


def _snapshot_routing(findings):
    return [
        {field: f.get(field) for field in ROUTING_FIELDS}
        for f in findings
    ]


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _pass(msg):
    print("[PASS] " + msg)


def _fail(msg):
    print("[FAIL] " + msg)


def run_drift_check():
    print("=" * 70)
    print("375E-COV-A Keyless 0-Drift Harness")
    print("=" * 70)

    # ---- Load frozen artifact ------------------------------------------------
    print("\nLoading frozen artifact: " + os.path.basename(FROZEN_ARTIFACT))
    artifact = _load_json(FROZEN_ARTIFACT)

    cross_provision_findings_raw = artifact.get("cross_provision_findings", [])
    coverage_assessment = artifact.get("coverage_assessment", [])
    # Note: use_profile IS present in the frozen artifact (real run had one).
    # We pass use_profile=None to the harness to force keyless mode.
    use_profile_in_artifact = artifact.get("use_profile")

    print("  cross_provision_findings: %d finding(s)" % len(cross_provision_findings_raw))
    print("  coverage_assessment: %d LP(s)" % len(coverage_assessment))
    print("  use_profile in artifact: %s" % ("present" if use_profile_in_artifact else "absent"))
    print("  Harness forces use_profile=None for keyless (no model calls)")

    # ---- Deep-copy findings before running -----------------------------------
    findings_to_test = copy.deepcopy(cross_provision_findings_raw)

    # ---- Snapshot routing BEFORE ---------------------------------------------
    before_snapshot = _snapshot_routing(findings_to_test)
    print("\nRouting snapshot BEFORE: %d entries" % len(before_snapshot))

    # ---- Import and run assess_finding_consequence ---------------------------
    print("\nRunning assess_finding_consequence (use_profile=None - keyless)...")
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)

    try:
        from cam.adapters.lease_review.lease_finding_consequence import assess_finding_consequence
    except ImportError as e:
        _fail("Could not import assess_finding_consequence: " + str(e))
        sys.exit(1)

    try:
        findings_after, meta = assess_finding_consequence(
            cross_provision_findings=findings_to_test,
            coverage_assessment=coverage_assessment,
            use_profile=None,   # keyless -- no model calls
            perspective="tenant",
            cfg={},
        )
    except Exception as e:
        _fail("assess_finding_consequence raised an exception: " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("  Meta: " + str(meta))

    # ---- Snapshot routing AFTER ----------------------------------------------
    after_snapshot = _snapshot_routing(findings_after)
    print("\nRouting snapshot AFTER: %d entries" % len(after_snapshot))

    # ---- CHECK 1: Routing drift ----------------------------------------------
    drift_failures = []
    for i, (before, after) in enumerate(zip(before_snapshot, after_snapshot)):
        for field in ROUTING_FIELDS:
            if before.get(field) != after.get(field):
                drift_failures.append({
                    "index": i,
                    "finding_id": before.get("finding_id") or after.get("finding_id"),
                    "field": field,
                    "before": before.get(field),
                    "after": after.get(field),
                })

    if drift_failures:
        _fail("%d routing drift(s) detected:" % len(drift_failures))
        for d in drift_failures:
            print("  [%s] %s: %r -> %r" % (d["finding_id"], d["field"], d["before"], d["after"]))
        check1_pass = False
    else:
        _pass("0 routing drift across all %d findings" % len(findings_after))
        check1_pass = True

    # ---- CHECK 2: Provenance fields on directional findings ------------------
    directional_findings = [f for f in findings_after if f.get("finding_type") == "directional_mismatch"]
    provenance_failures = []
    for f in directional_findings:
        fid = f.get("finding_id", "?")
        for field in REQUIRED_DIRECTIONAL_FIELDS:
            if field not in f:
                provenance_failures.append("%s missing field %r" % (fid, field))
        if f.get("assessment_scope") != "finding_linked_lp":
            provenance_failures.append(
                "%s assessment_scope=%r (expected 'finding_linked_lp')" % (fid, f.get("assessment_scope"))
            )
        if f.get("stage7_direction") != "tenant_unprotected":
            provenance_failures.append(
                "%s stage7_direction=%r (expected 'tenant_unprotected')" % (fid, f.get("stage7_direction"))
            )
        src = f.get("use_consequence_source")
        if src not in {"assessed", "absent"}:
            provenance_failures.append(
                "%s use_consequence_source=%r (expected 'assessed' or 'absent')" % (fid, src)
            )

    if provenance_failures:
        _fail("Provenance field issues on directional findings:")
        for msg in provenance_failures:
            print("  " + msg)
        check2_pass = False
    else:
        _pass("Provenance fields present on all %d directional findings" % len(directional_findings))
        check2_pass = True

    # ---- CHECK 3: compound_consequence_source on compound findings -----------
    compound_findings = [f for f in findings_after if f.get("finding_type") == "compound_risk"]
    compound_failures = []
    for f in compound_findings:
        fid = f.get("finding_id", "?")
        if f.get("compound_consequence_source") != "not_assessed":
            compound_failures.append(
                "%s compound_consequence_source=%r (expected 'not_assessed')" % (
                    fid, f.get("compound_consequence_source")
                )
            )

    if compound_failures:
        _fail("compound_consequence_source issues:")
        for msg in compound_failures:
            print("  " + msg)
        check3_pass = False
    else:
        _pass(
            "compound_consequence_source='not_assessed' on all %d compound findings" % len(compound_findings)
        )
        check3_pass = True

    # ---- CHECK 4: Finding counts vs 375J expectations ------------------------
    n_dir = len(directional_findings)
    n_cmp = len(compound_findings)
    count_failures = []
    if n_dir != EXPECTED_DIRECTIONAL_COUNT:
        count_failures.append(
            "Directional finding count: got %d, expected %d" % (n_dir, EXPECTED_DIRECTIONAL_COUNT)
        )
    if n_cmp != EXPECTED_COMPOUND_COUNT:
        count_failures.append(
            "Compound finding count: got %d, expected %d" % (n_cmp, EXPECTED_COMPOUND_COUNT)
        )

    if count_failures:
        _fail("Finding count mismatch vs 375J:")
        for msg in count_failures:
            print("  " + msg)
        check4_pass = False
    else:
        _pass(
            "Finding counts verified: %d directional, %d compound (matches 375J)" % (n_dir, n_cmp)
        )
        check4_pass = True

    # ---- Provenance distribution summary (for results.md) --------------------
    print("\n---- Provenance distribution (keyless run) ----")
    assessed_dir = [f for f in directional_findings if f.get("use_consequence_source") == "assessed"]
    absent_dir = [f for f in directional_findings if f.get("use_consequence_source") == "absent"]
    print("  source=assessed (LP already had use_impact, copied): %d" % len(assessed_dir))
    print("  source=absent   (no use_profile, keyless mode):      %d" % len(absent_dir))
    print("  compound not_assessed:                               %d" % n_cmp)
    print("")
    print("  Already-assessed findings (source=assessed in keyless run):")
    for f in sorted(assessed_dir, key=lambda x: x.get("finding_id", "")):
        lp_ids = f.get("implicated_lps") or []
        lp_id = lp_ids[0] if lp_ids else "?"
        print("    %s [%s]: use_consequence=%s, materiality=%s" % (
            f.get("finding_id"), lp_id,
            f.get("use_consequence"), f.get("materiality")
        ))

    # ---- SUMMARY -------------------------------------------------------------
    print("\n" + "=" * 70)
    all_pass = check1_pass and check2_pass and check3_pass and check4_pass
    if all_pass:
        print("[PASS] 375E-COV-A DRIFT CHECK: ALL PASS -- safe to proceed with keyed run")
    else:
        print("[FAIL] 375E-COV-A DRIFT CHECK: FAILURES DETECTED -- fix before keyed run")
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    run_drift_check()
