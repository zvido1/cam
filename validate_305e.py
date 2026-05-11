"""
Step 305e: Targeted variance re-test for LP-09 and LP-22 only.

All 5 pilot LPs run through 305 (_ENABLED_305_LPS already expanded in lease_coverage.py).
Only LP-09 and LP-22 are evaluated for stability.
Acceptance criterion: LP-state stable across 3 runs for each LP.

Run: python validate_305e.py
"""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

find_and_load_env()

TENANT_PATH = str(CAM_ROOT / "05 Lease Analyzer" / "test_data" / "tenants" / "T-10_Negotiated_Tennant_Lease.docx")
OUT_DIR = CAM_ROOT / "experiments" / "validate_305e"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_LPS = ["LP-09", "LP-22"]
PASS = "PASS"
FAIL = "FAIL"


def run_pipeline(label):
    print(f"\n{'='*60}\nRun: {label}\n{'='*60}")
    t0 = time.time()
    result = run_lease_coverage_only(
        tenant_path=TENANT_PATH,
        config={"output_dir": str(OUT_DIR / label)},
    )
    elapsed = round(time.time() - t0, 1)
    print(f"  Elapsed: {elapsed}s")
    return result


def extract(result, pids):
    ca = result.get("coverage_assessment") or []
    return {
        e["issue_area_id"]: {
            "coverage_state": e.get("coverage_state"),
            "coverage_state_baseline": e.get("coverage_state_baseline"),
            "coverage_method": e.get("coverage_method", "legacy"),
            "element_verdicts": e.get("element_verdicts") or [],
        }
        for e in ca if e.get("issue_area_id") in pids
    }


def verdicts_map(ev):
    return {v.get("element_id", ""): v.get("verdict", "unclear") for v in ev}


# Three runs
runs = []
for i in range(1, 4):
    r = run_pipeline(f"run{i}")
    data = extract(r, TARGET_LPS)
    runs.append(data)
    with open(OUT_DIR / f"run{i}.json", "w") as f:
        json.dump(data, f, indent=2)

# Analysis
print("\n" + "="*70)
print("STABILITY ANALYSIS (LP-09 and LP-22)")
print("="*70)

results = {}
for pid in TARGET_LPS:
    print(f"\n  {pid}:")
    states = [r.get(pid, {}).get("coverage_state", "not_found") for r in runs]
    methods = [r.get(pid, {}).get("coverage_method", "?") for r in runs]
    ev_counts = [len(r.get(pid, {}).get("element_verdicts", [])) for r in runs]

    for i, (s, m, c) in enumerate(zip(states, methods, ev_counts), 1):
        print(f"    run{i}: method={m}, coverage_state={s}, element_count={c}")

    state_stable = len(set(states)) == 1
    print(f"    LP-state stability: {PASS if state_stable else FAIL} ({', '.join(states)})")

    # Element-level detail
    maps = [verdicts_map(r.get(pid, {}).get("element_verdicts", [])) for r in runs]
    all_ids = set()
    for m in maps: all_ids.update(m.keys())
    unstable = []
    for eid in sorted(all_ids):
        vs = [m.get(eid, "(missing)") for m in maps]
        if len(set(vs)) > 1:
            unstable.append(f"    {eid}: " + ", ".join(f"run{i+1}={v}" for i, v in enumerate(vs)))
    if unstable:
        print(f"    Unstable elements ({len(unstable)}):")
        for u in unstable:
            print(u)
    else:
        print(f"    Element stability: all {len(all_ids)} elements consistent")

    results[pid] = {"state_stable": state_stable, "states": states, "unstable_elements": unstable}

# Decision
print("\n" + "="*70)
lp09_pass = results["LP-09"]["state_stable"]
lp22_pass = results["LP-22"]["state_stable"]
print(f"LP-09 LP-state: {PASS if lp09_pass else FAIL}")
print(f"LP-22 LP-state: {PASS if lp22_pass else FAIL}")

if lp09_pass and lp22_pass:
    decision = "Both pass — _ENABLED_305_LPS stays at all 5 LPs."
elif lp09_pass:
    decision = "LP-09 passes, LP-22 fails — enable LP-09, revert LP-22 to legacy."
elif lp22_pass:
    decision = "LP-22 passes, LP-09 fails — enable LP-22, revert LP-09 to legacy."
else:
    decision = "Both fail — revert both to legacy path."
print(f"\nDecision: {decision}")

# Write status doc
with open(CAM_ROOT / "build_log" / "305e_code_status.md", "w", encoding="utf-8") as f:
    f.write("# Step 305e — Targeted Variance Re-test (LP-09, LP-22)\n\n")
    f.write(f"**Date:** 2026-05-11\n")
    f.write(f"**Fixture:** T-10_Negotiated_Tennant_Lease.docx (Mode C)\n\n")
    f.write("## Results\n\n")
    f.write("| LP | Run 1 state | Run 2 state | Run 3 state | LP-state stable | Decision |\n")
    f.write("|----|---------|---------|---------|----|----|\n")
    for pid in TARGET_LPS:
        st = results[pid]["states"]
        stable = results[pid]["state_stable"]
        dec = "Enable" if stable else "Keep on legacy"
        f.write(f"| {pid} | {st[0]} | {st[1]} | {st[2]} | {'Yes' if stable else 'No'} | {dec} |\n")
    f.write(f"\n## Decision\n\n{decision}\n\n")
    for pid in TARGET_LPS:
        f.write(f"### {pid} unstable elements\n\n")
        if results[pid]["unstable_elements"]:
            for u in results[pid]["unstable_elements"]:
                f.write(f"{u.strip()}\n\n")
        else:
            f.write("None — all elements consistent.\n\n")

print(f"\nStatus doc: build_log/305e_code_status.md")
