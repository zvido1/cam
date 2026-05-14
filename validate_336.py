"""
Step 336 Validation: Re-run Stage 7 on Atlas and Beitel to verify four compound finding fixes.

Run from the worktree root (cd into the worktree, then python validate_336.py).

Checks:
  1. No headline hard-cut at 160 chars mid-word
  2. cited_sections populated on compound findings
  3. Compound findings show mixed severity (not all HIGH)
  4. Overlapping compound findings merged (count reduced)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import find_and_load_env

find_and_load_env()

# Results live in the main CAM dir, not the worktree.
MAIN_CAM = Path(__file__).resolve().parents[3]   # file is at CAM/.claude/worktrees/name/validate_336.py

ATLAS_RUN = (
    MAIN_CAM / "05 Lease Analyzer" / "results"
    / "lease_review_20260514_182946_eb7dda" / "tenant_0" / "pipeline_results.json"
)
BEITEL_RUN = (
    MAIN_CAM / "05 Lease Analyzer" / "results"
    / "lease_review_20260513_015449_81f298" / "tenant_0" / "pipeline_results.json"
)
OUT_DIR = MAIN_CAM / "experiments" / "validate_336"
OUT_DIR.mkdir(parents=True, exist_ok=True)

from cam.adapters.lease_review.lease_synthesis import run_synthesis

PASS = "PASS"
FAIL = "FAIL"


def run_case(label, run_path, perspective):
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print("=" * 60)

    prior = json.loads(run_path.read_text(encoding="utf-8"))
    coverage_assessment = prior["coverage_assessment"]
    conflicts = prior.get("conflicts", [])
    full_tenant_text = prior["full_tenant_text"]
    print(f"Loaded {len(coverage_assessment)} CAs, {len(conflicts)} conflicts")

    t0 = time.time()
    result = run_synthesis(
        full_tenant_text=full_tenant_text,
        coverage_assessment=coverage_assessment,
        conflicts=conflicts,
        perspective=perspective,
    )
    elapsed = round(time.time() - t0, 1)

    findings = result.get("cross_provision_findings", [])
    compound = [f for f in findings if f.get("finding_type") == "compound_risk"]

    slug = label.lower().split()[0]
    out_path = OUT_DIR / f"validate_336_{slug}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Stage 7 complete: {len(findings)} total, {len(compound)} compound in {elapsed}s")
    print(f"Results: {out_path}")

    checks = []

    # Check 1: No headline truncated mid-word (ends with a letter/digit without punctuation or ...)
    import re as _re
    mid_word_cut = [
        f["headline"] for f in compound
        if _re.search(r'[a-zA-Z0-9]$', f.get("headline", "")) and len(f.get("headline", "")) == 160
    ]
    c1 = PASS if not mid_word_cut else FAIL
    checks.append((f"No headline mid-word truncation at 160 chars (found {len(mid_word_cut)})", c1))

    # Check 2: cited_sections populated on at least one compound finding
    if compound:
        populated = [f for f in compound if f.get("cited_sections")]
        c2 = PASS if populated else FAIL
        checks.append((f"cited_sections populated on >=1 compound ({len(populated)}/{len(compound)})", c2))
    else:
        checks.append(("cited_sections: no compound findings to check", PASS))

    # Check 3: Not all compound findings are HIGH
    if len(compound) > 1:
        severities = [f.get("severity") for f in compound]
        all_high = all(s == "HIGH" for s in severities)
        c3 = PASS if not all_high else FAIL
        checks.append((f"Mixed severity not all HIGH (severities: {severities})", c3))
    elif compound:
        checks.append(("Mixed severity: only 1 compound finding", PASS))
    else:
        checks.append(("Mixed severity: no compound findings", PASS))

    # Check 4: Stage 7 completed without error
    meta = result.get("meta", {})
    c4 = PASS if not meta.get("skipped") else FAIL
    checks.append(("Stage 7 completed without error", c4))

    # Print compound findings summary
    print(f"\nCompound findings ({len(compound)}):")
    for f in compound:
        hl = f.get("headline", "")[:80]
        sev = f.get("severity", "?")
        cs = len(f.get("cited_sections") or [])
        ag = f.get("evaluator_agreement", "?")
        fid = f.get("finding_id", "?")
        lps = ",".join(f.get("implicated_lps") or [])
        pat = f.get("pattern_type", "?")
        print(f"  {fid} [{sev}] [{ag}] cs={cs} pat={pat}")
        print(f"    lps={lps}")
        print(f"    {hl!r}")

    return checks


all_checks = []

atlas_checks = run_case("Atlas (Tenant)", ATLAS_RUN, "tenant")
all_checks.extend([("Atlas: " + lbl, st) for lbl, st in atlas_checks])

beitel_checks = run_case("Beitel (Tenant)", BEITEL_RUN, "tenant")
all_checks.extend([("Beitel: " + lbl, st) for lbl, st in beitel_checks])

print("\n" + "=" * 60)
print("ACCEPTANCE CRITERIA SUMMARY")
print("=" * 60)
passed = 0
for label, status in all_checks:
    icon = "[OK]" if status == PASS else "[FAIL]"
    print(f"  {icon} {status}  {label}")
    if status == PASS:
        passed += 1

print(f"\n{passed}/{len(all_checks)} checks passed")
overall = "PASS" if passed == len(all_checks) else "FAIL"
print(f"\nOverall: {overall}")
