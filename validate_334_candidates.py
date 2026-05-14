"""
Step 334 Variance Test: verify candidates[] count > 0 for all three evaluators
after the prompt reorder.

Run Atlas + Beitel fixtures THREE times each. Pass if ALL evaluators produce
candidates[] with count > 0 on every run.

Usage:
  cd "C:\Users\Owner\OneDrive\CAM"
  python validate_334_candidates.py

Results written to experiments/validate_334/
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import CAM_ROOT, find_and_load_env
find_and_load_env()

# ── Fixture paths (latest run that has both fixtures) ──
ATLAS_RUN  = CAM_ROOT / "05 Lease Analyzer" / "results" / "lease_review_20260514_041331_d168ba" / "tenant_0" / "pipeline_results.json"
BEITEL_RUN = CAM_ROOT / "05 Lease Analyzer" / "results" / "lease_review_20260514_041331_d168ba" / "tenant_1" / "pipeline_results.json"

OUT_DIR = CAM_ROOT / "experiments" / "validate_334"
OUT_DIR.mkdir(parents=True, exist_ok=True)

from cam.adapters.lease_review.lease_synthesis import run_synthesis

FIXTURES = {
    "Atlas":  ATLAS_RUN,
    "Beitel": BEITEL_RUN,
}

N_RUNS = 3

print("=" * 70)
print("Step 334 — candidates[] Variance Test (prompt reorder Option A)")
print(f"Fixtures: Atlas + Beitel, {N_RUNS} runs each")
print("=" * 70)

all_pass = True
summary_rows = []

for fixture_name, run_path in FIXTURES.items():
    print(f"\n{'='*30} {fixture_name} {'='*30}")
    prior = json.loads(run_path.read_text(encoding="utf-8"))
    coverage_assessment = prior["coverage_assessment"]
    conflicts = prior.get("conflicts", [])
    full_tenant_text = prior["full_tenant_text"]
    print(f"Loaded: {len(coverage_assessment)} assessments, {len(conflicts)} conflicts")

    for run_idx in range(1, N_RUNS + 1):
        print(f"\n--- {fixture_name} Run {run_idx}/{N_RUNS} ---")
        t0 = time.time()

        # Monkey-patch run_synthesis to capture per-evaluator candidate counts
        # by reading stdout via the existing [synth_debug] log lines.
        # We capture them by redirecting and then running directly.
        import io
        from contextlib import redirect_stdout

        log_capture = io.StringIO()
        try:
            with redirect_stdout(log_capture):
                result = run_synthesis(
                    full_tenant_text=full_tenant_text,
                    coverage_assessment=coverage_assessment,
                    conflicts=conflicts,
                    perspective="tenant",
                )
        except Exception as e:
            print(f"  ERROR: run_synthesis raised {type(e).__name__}: {e}")
            all_pass = False
            summary_rows.append(f"  {fixture_name} Run {run_idx}: EXCEPTION {e}")
            continue

        elapsed = round(time.time() - t0, 1)
        log_text = log_capture.getvalue()

        # Print captured output to real stdout so it's visible
        print(log_text, end="")

        # Parse [synth_debug] candidate counts
        import re
        debug_lines = re.findall(r'\[synth_debug\] Eval-([ABC]): (\d+) candidate\(s\)', log_text)
        counts = {role: int(n) for role, n in debug_lines}

        # Also count findings
        findings = result.get("cross_provision_findings", [])
        compounds = [f for f in findings if f.get("finding_type") == "compound_risk"]
        print(f"  Elapsed: {elapsed}s | Findings: {len(findings)} | Compound: {len(compounds)}")

        run_pass = True
        for role in ("A", "B", "C"):
            n = counts.get(role, -1)
            status = "OK" if n > 0 else "FAIL"
            if n == 0:
                run_pass = False
                all_pass = False
            print(f"  [synth_debug] Eval-{role}: {n} candidate(s) in candidates[]  [{status}]")

        row_status = "PASS" if run_pass else "FAIL"
        summary_rows.append(f"  {fixture_name} Run {run_idx}: {row_status} — A={counts.get('A','?')} B={counts.get('B','?')} C={counts.get('C','?')}")

        # Save result
        out_path = OUT_DIR / f"{fixture_name.lower()}_run{run_idx}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
for row in summary_rows:
    print(row)

overall = "ALL PASS" if all_pass else "SOME RUNS FAILED"
print(f"\nOption A result: {overall}")
print("=" * 70)

if not all_pass:
    print("\nOption A has failed — at least one evaluator returned 0 candidates.")
    print("Report this to Chat before implementing Option B.")
    sys.exit(1)
else:
    print("\nOption A passed: all evaluators produced candidates[] > 0 on all runs.")
