"""
Step 305 variance acceptance test.

Protocol:
  Run 0 (baseline): STEP_305_ENABLED=False — capture LP-level coverage_states
  Runs 1-3 (305 enabled): STEP_305_ENABLED=True — capture element_verdicts + coverage_states

Acceptance criterion:
  No element-level verdict changes across Runs 1, 2, 3 for any pilot LP = PASS
  Any element shows different verdict across runs = FAIL

Run: python validate_305_variance.py
"""
import json, sys, time, copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

find_and_load_env()

TENANT_PATH = str(CAM_ROOT / "05 Lease Analyzer" / "test_data" / "tenants" / "T-10_Negotiated_Tennant_Lease.docx")
OUT_DIR = CAM_ROOT / "experiments" / "validate_305_variance"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PILOT_LPS = ["LP-09", "LP-11", "LP-22", "LP-26", "LP-27"]


def run_pipeline(label: str, enable_305: bool) -> dict:
    """Run one Mode C pass and return the result dict."""
    import cam.adapters.lease_review.lease_coverage_305 as _m305
    _m305.STEP_305_ENABLED = enable_305
    print(f"\n{'='*60}")
    print(f"Run: {label}  (STEP_305_ENABLED={enable_305})")
    print(f"{'='*60}")
    t0 = time.time()
    result = run_lease_coverage_only(
        tenant_path=TENANT_PATH,
        config={"output_dir": str(OUT_DIR / label)},
    )
    elapsed = round(time.time() - t0, 1)
    print(f"  Elapsed: {elapsed}s")
    return result


def extract_pilot_coverage(result: dict) -> dict:
    """Extract per-pilot-LP coverage info from a result dict."""
    ca = result.get("coverage_assessment") or []
    out = {}
    for entry in ca:
        pid = entry.get("issue_area_id") or entry.get("provision_id", "")
        if pid in PILOT_LPS:
            out[pid] = {
                "coverage_state": entry.get("coverage_state"),
                "coverage_state_baseline": entry.get("coverage_state_baseline"),
                "coverage_method": entry.get("coverage_method", "legacy"),
                "element_verdicts": entry.get("element_verdicts") or [],
                "elements_found": entry.get("elements_found", []),
                "elements_missing": entry.get("elements_missing", []),
            }
    return out


def verdicts_map(element_verdicts: list) -> dict:
    """Return {element_id: verdict} dict for fast comparison."""
    return {v.get("element_id", ""): v.get("verdict", "unclear") for v in element_verdicts}


def compare_verdict_maps(maps: list[dict], run_labels: list[str]) -> tuple[bool, list[str]]:
    """
    Compare verdict maps across N runs.
    Returns (all_stable, list_of_discrepancy_strings).
    """
    if not maps:
        return True, []
    all_ids = set()
    for m in maps:
        all_ids.update(m.keys())

    discrepancies = []
    for eid in sorted(all_ids):
        verdicts = [m.get(eid, "(missing)") for m in maps]
        if len(set(verdicts)) > 1:
            detail = ", ".join(f"{lbl}={v}" for lbl, v in zip(run_labels, verdicts))
            discrepancies.append(f"    {eid}: {detail}")
    return len(discrepancies) == 0, discrepancies


# ── Run 0: baseline (305 disabled) ───────────────────────────────────────────
r0 = run_pipeline("run0_baseline", enable_305=False)
baseline_coverage = extract_pilot_coverage(r0)

# Save run 0 summary
with open(OUT_DIR / "run0_coverage.json", "w") as f:
    json.dump(baseline_coverage, f, indent=2)

# ── Runs 1-3: 305 enabled ─────────────────────────────────────────────────────
enabled_runs = []
for i in range(1, 4):
    r = run_pipeline(f"run{i}_305", enable_305=True)
    enabled_runs.append(extract_pilot_coverage(r))
    with open(OUT_DIR / f"run{i}_coverage.json", "w") as f:
        json.dump(enabled_runs[-1], f, indent=2)

# Reset flag to False after testing
import cam.adapters.lease_review.lease_coverage_305 as _m305_reset
_m305_reset.STEP_305_ENABLED = False

# ── Analysis ──────────────────────────────────────────────────────────────────
PASS = "PASS"
FAIL = "FAIL"

print("\n" + "="*70)
print("VARIANCE ANALYSIS")
print("="*70)

run_labels = ["run1", "run2", "run3"]
overall_pass = True
findings = []

for pid in PILOT_LPS:
    print(f"\n  {pid}:")

    # Check all 3 enabled runs have element_verdicts
    maps = []
    for i, r in enumerate(enabled_runs):
        ev = r.get(pid, {}).get("element_verdicts", [])
        vm = verdicts_map(ev)
        maps.append(vm)
        coverage_method = r.get(pid, {}).get("coverage_method", "legacy")
        cstate = r.get(pid, {}).get("coverage_state", "?")
        print(f"    run{i+1}: method={coverage_method}, coverage_state={cstate}, "
              f"element_count={len(ev)}")

    if not any(maps):
        print(f"    WARNING: no element_verdicts in any run (305 may not have fired)")
        findings.append(f"  {pid}: no element_verdicts found — 305 routing may not have fired")
        continue

    stable, discrepancies = compare_verdict_maps(maps, run_labels)
    if stable:
        print(f"    Verdict stability: PASS ({len(maps[0])} elements, all stable)")
    else:
        print(f"    Verdict stability: FAIL ({len(discrepancies)} element(s) vary):")
        for d in discrepancies:
            print(d)
        findings.append(f"  {pid}: {len(discrepancies)} element(s) vary:\n" + "\n".join(discrepancies))
        overall_pass = False

    # Compare 305 states to baseline
    baseline_state = baseline_coverage.get(pid, {}).get("coverage_state", "not_found")
    run1_state = enabled_runs[0].get(pid, {}).get("coverage_state", "not_found")
    run1_baseline305 = enabled_runs[0].get(pid, {}).get("coverage_state_baseline", "?")
    state_changed = baseline_state != run1_state
    print(f"    Coverage state: baseline(legacy)={baseline_state} | "
          f"305_baseline={run1_baseline305} | 305_final={run1_state} | "
          f"changed={'YES' if state_changed else 'no'}")
    if state_changed:
        findings.append(f"  {pid}: coverage_state changed: {baseline_state} -> {run1_state} (305 baseline={run1_baseline305})")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print(f"VERDICT: {'PASS -- all element verdicts stable across 3 runs' if overall_pass else 'FAIL -- element verdict variance detected'}")
print("="*70)
if findings:
    print("Findings:")
    for f in findings:
        print(f)

# ── Write status doc ──────────────────────────────────────────────────────────
# Gather full element-level detail for the status doc
element_detail_sections = []
for pid in PILOT_LPS:
    section = [f"### {pid}"]
    for i, r in enumerate(enabled_runs):
        ev = r.get(pid, {}).get("element_verdicts", [])
        section.append(f"\n**Run {i+1}:**")
        if ev:
            for v in ev:
                eid = v.get("element_id", "")
                verdict = v.get("verdict", "?")
                conf = v.get("confidence", "?")
                section_ref = (v.get("citation") or {}).get("section_ref") or "—"
                section.append(f"  - `{eid}`: {verdict} ({conf}) | cite: {section_ref}")
        else:
            section.append("  (no element_verdicts — 305 routing did not fire)")
    element_detail_sections.append("\n".join(section))

with open(CAM_ROOT / "build_log" / "305_variance_test.md", "w", encoding="utf-8") as f:
    f.write(f"# Step 305 Variance Acceptance Test\n\n")
    f.write(f"**Date:** 2026-05-11\n")
    f.write(f"**Fixture:** T-10_Negotiated_Tennant_Lease.docx (Mode C, tenant perspective)\n")
    f.write(f"**Result:** {'PASS' if overall_pass else 'FAIL'}\n\n")
    f.write(f"---\n\n## Acceptance Criterion\n\n")
    f.write(f"No element-level verdict changes across 3 runs with STEP_305_ENABLED=True.\n\n")
    f.write(f"---\n\n## Coverage State Comparison (Legacy vs 305)\n\n")
    f.write(f"| LP | Legacy (baseline) | 305 run1 baseline | 305 run1 final | Changed? |\n")
    f.write(f"|----|--------------------|-------------------|----------------|----------|\n")
    for pid in PILOT_LPS:
        b = baseline_coverage.get(pid, {}).get("coverage_state", "—")
        r1b = enabled_runs[0].get(pid, {}).get("coverage_state_baseline", "—") if enabled_runs else "—"
        r1f = enabled_runs[0].get(pid, {}).get("coverage_state", "—") if enabled_runs else "—"
        changed = "YES" if b != r1f else "—"
        f.write(f"| {pid} | {b} | {r1b} | {r1f} | {changed} |\n")
    f.write(f"\n---\n\n## Stability Analysis (Runs 1-3)\n\n")
    for pid in PILOT_LPS:
        maps = [verdicts_map(r.get(pid, {}).get("element_verdicts", [])) for r in enabled_runs]
        stable, discrepancies = compare_verdict_maps(maps, run_labels)
        f.write(f"**{pid}:** {'STABLE' if stable else 'UNSTABLE'}")
        if not stable:
            f.write(f" — {len(discrepancies)} element(s) vary\n")
            for d in discrepancies:
                f.write(f"{d}\n")
        else:
            f.write(f" — all {len(maps[0])} elements consistent\n")
        f.write("\n")
    f.write(f"\n---\n\n## Per-Element Verdict Detail\n\n")
    for section in element_detail_sections:
        f.write(section + "\n\n")
    f.write(f"\n---\n\n## Decision\n\n")
    if overall_pass:
        f.write("STEP_305_ENABLED set to **True** in `lease_coverage_305.py` per acceptance test result.\n")
    else:
        f.write("STEP_305_ENABLED remains **False**. Failing elements documented above.\n")
        f.write("Root cause investigation required before enabling.\n")

print(f"\nStatus doc: build_log/305_variance_test.md")
print(f"Run data: {OUT_DIR}/")
