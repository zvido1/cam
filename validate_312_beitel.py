"""
Step 312 Validation: Re-run Stage 7 only on the Beitel lease using the fixed
lease_synthesis.py prompts.

Loads coverage_assessment + full_tenant_text from the prior Beitel run and
calls run_synthesis() directly. Writes results to experiments/validate_312/.

Run: python validate_312_beitel.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import CAM_ROOT, find_and_load_env

find_and_load_env()

PRIOR_RUN = CAM_ROOT / "05 Lease Analyzer" / "results" / "lease_review_20260513_015449_81f298" / "tenant_0" / "pipeline_results.json"
OUT_DIR = CAM_ROOT / "experiments" / "validate_312"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Step 312 — Stage 7 Beitel Re-run")
print("=" * 60)

# Load prior run data
prior = json.loads(PRIOR_RUN.read_text(encoding="utf-8"))
coverage_assessment = prior["coverage_assessment"]
conflicts = prior.get("conflicts", [])
full_tenant_text = prior["full_tenant_text"]

print(f"Loaded {len(coverage_assessment)} coverage assessments, {len(conflicts)} conflicts")

# Run Stage 7 with fixed prompts
from cam.adapters.lease_review.lease_synthesis import run_synthesis

t0 = time.time()
result = run_synthesis(
    full_tenant_text=full_tenant_text,
    coverage_assessment=coverage_assessment,
    conflicts=conflicts,
    perspective="tenant",
)
elapsed = round(time.time() - t0, 1)

findings = result.get("cross_provision_findings", [])
out_path = OUT_DIR / "pipeline_results_312.json"
out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"\nStage 7 complete: {len(findings)} findings in {elapsed}s")
print(f"Results written to: {out_path}")
print()

# ── Acceptance criteria checks ──
PASS = "PASS"
FAIL = "FAIL"
checks = []

# Find LP-27 finding
lp27 = next((f for f in findings if "LP-27" in (f.get("implicated_lps") or [])
             and f.get("finding_type") != "compound_risk"), None)

if lp27:
    print(f"LP-27 finding: {json.dumps(lp27, indent=2)}")
else:
    print("WARNING: No LP-27 non-compound finding found")

# Check 1: LP-27 finding_type is directional_mismatch
c1 = PASS if (lp27 and lp27.get("finding_type") == "directional_mismatch") else FAIL
checks.append(("LP-27 finding_type == directional_mismatch", c1))

# Check 2: LP-27 cites Article 15
c2_sections = lp27.get("cited_sections", []) if lp27 else []
c2 = PASS if any("15" in s for s in c2_sections) else FAIL
checks.append(("LP-27 cites Article 15", c2))

# Check 3: LP-27 directionality == tenant_unprotected
c3 = PASS if (lp27 and lp27.get("directionality") == "tenant_unprotected") else FAIL
checks.append(("LP-27 directionality == tenant_unprotected", c3))

# Find compound risk finding for LP-27
cr27 = next((f for f in findings
             if f.get("finding_type") == "compound_risk"
             and "LP-27" in (f.get("implicated_lps") or [])), None)

if cr27:
    print(f"\nCompound risk finding: {json.dumps(cr27, indent=2)}")
else:
    print("\nWARNING: No compound risk finding with LP-27 found")

# Check 4: Compound risk has 2-1 or 3-0 evaluator agreement
c4_ag = cr27.get("evaluator_agreement", "") if cr27 else ""
c4 = PASS if c4_ag in ("2-1", "3-0") else FAIL
checks.append((f"Compound risk evaluator_agreement is 2-1 or 3-0 (got: {c4_ag})", c4))

# Check 5: CPF-16 LP-22 directional mismatch still fires
lp22 = next((f for f in findings
             if "LP-22" in (f.get("implicated_lps") or [])
             and f.get("finding_type") == "directional_mismatch"), None)
c5 = PASS if (lp22 and lp22.get("directionality") == "tenant_unprotected") else FAIL
checks.append(("CPF-16 LP-22 directional_mismatch still fires (no regression)", c5))

# Check 6: LP-27 verdict still no_coverage_found
c6 = PASS if (lp27 and lp27.get("verdict") == "no_coverage_found") else FAIL
checks.append(("LP-27 verdict still no_coverage_found", c6))

# Check 7: Stage 7 completed without error
meta = result.get("meta", {})
c7 = PASS if not meta.get("skipped") else FAIL
checks.append(("Stage 7 completed without error", c7))

print("\n" + "=" * 60)
print("ACCEPTANCE CRITERIA RESULTS")
print("=" * 60)
passed = 0
for label, status in checks:
    icon = "✅" if status == PASS else "❌"
    print(f"  {icon} {status}  {label}")
    if status == PASS:
        passed += 1

print(f"\n{passed}/{len(checks)} checks passed")
overall = "PASS" if passed == len(checks) else "FAIL"
print(f"\nOverall: {overall}")
print(f"Results: {out_path}")
