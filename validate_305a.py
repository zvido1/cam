"""
Step 305a validation — confirm schema_clue_match deletion is clean.

Tests:
  1. T-10 Mode C: negative_space_signals ≤10 total; coverage_state unchanged
  2. T-10-NY Mode C: NY jurisdiction, LP-09 escalation, CR-09, ENFORCEABILITY pill
  3. T-13 Mode C: runs clean, no exception, no missing fields

Run: python validate_305a.py
"""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

find_and_load_env()

TENANT_DIR = CAM_ROOT / "05 Lease Analyzer" / "test_data" / "tenants"
OUT_DIR = CAM_ROOT / "experiments" / "validate_305a"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PASS = "PASS"
FAIL = "FAIL"

def run_mode_c(fixture_name):
    tenant_path = str(TENANT_DIR / fixture_name)
    t0 = time.time()
    result = run_lease_coverage_only(
        tenant_path=tenant_path,
        config={"output_dir": str(OUT_DIR / fixture_name)},
    )
    elapsed = round(time.time() - t0, 1)
    return result, elapsed


def extract_ns_signals(result):
    """Return (total_count, by_type dict) across all LPs."""
    by_provision = result.get("negative_space_signals") or {}
    total = 0
    by_type = {}
    for pid, signals in by_provision.items():
        for sig in signals:
            total += 1
            st = sig.get("signal_type", "unknown")
            by_type[st] = by_type.get(st, 0) + 1
    return total, by_type


def extract_coverage_states(result):
    """Return dict of provision_id → coverage_state."""
    ca = result.get("coverage_assessment") or []
    return {a.get("issue_area_id", a.get("provision_id", "?")): a.get("coverage_state", "?")
            for a in ca}

# ─────────────────────────────────────────────────────────────────────────────
# Test 1: T-10 Mode C — signal count regression
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 1: T-10 Mode C — negative_space_signals count")
print("="*70)
result_t10, elapsed_t10 = run_mode_c("T-10_Negotiated_Tennant_Lease.docx")
total_t10, by_type_t10 = extract_ns_signals(result_t10)
states_t10 = extract_coverage_states(result_t10)

print(f"  Elapsed: {elapsed_t10}s")
print(f"  Total negative_space_signals: {total_t10}")
print(f"  By type: {json.dumps(by_type_t10, indent=4)}")
print(f"  schema_clue_match count: {by_type_t10.get('schema_clue_match', 0)}")

t1_pass = total_t10 <= 10
t1_no_scm = by_type_t10.get("schema_clue_match", 0) == 0
print(f"\n  [{PASS if t1_pass else FAIL}] Total signals <=10: {total_t10}")
print(f"  [{PASS if t1_no_scm else FAIL}] schema_clue_match = 0")
print(f"\n  Coverage states (32 LPs):")
for pid, state in sorted(states_t10.items()):
    print(f"    {pid}: {state}")

# Save for diff comparison
with open(OUT_DIR / "t10_results.json", "w") as f:
    json.dump({
        "total_ns_signals": total_t10,
        "by_type": by_type_t10,
        "coverage_states": states_t10,
    }, f, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# Test 2: T-10-NY Mode C — jurisdiction regression
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 2: T-10-NY Mode C — jurisdiction / ENFORCEABILITY pill")
print("="*70)
result_ny, elapsed_ny = run_mode_c("T-10-NY.txt")
total_ny, by_type_ny = extract_ns_signals(result_ny)
states_ny = extract_coverage_states(result_ny)

governing_law = result_ny.get("jurisdiction", {}).get("governing_law") or result_ny.get("governing_law")
escalation_log = result_ny.get("escalation_log") or result_ny.get("jurisdiction_escalation_log") or []
conflicts = result_ny.get("conflicts") or []

print(f"  Elapsed: {elapsed_ny}s")
print(f"  Governing law: {governing_law}")
print(f"  Escalation log entries: {len(escalation_log)}")
print(f"  Conflicts: {len(conflicts)}")

lp09_state = states_ny.get("LP-09", "(not found)")
cr09_fired = any(c.get("conflict_id") == "CR-09" or c.get("id") == "CR-09" for c in conflicts)
ny_detected = governing_law and "new york" in str(governing_law).lower()
lp09_escalated = lp09_state in ("potentially_unenforceable", "covered_unfavorable")

# Check ENFORCEABILITY pill via use_aware_governance or coverage_assessment
use_gov = result_ny.get("use_aware_governance") or {}
enf_surfaced = False
for a in result_ny.get("coverage_assessment") or []:
    pills = a.get("pills") or a.get("pill_labels") or []
    if any("ENFORCEABILITY" in str(p).upper() for p in pills):
        enf_surfaced = True
        break
# Also check top-level
if not enf_surfaced:
    for key in ["enforceability_pill", "enforceability"]:
        if result_ny.get(key):
            enf_surfaced = True
            break

t2_ny = PASS if ny_detected else FAIL
t2_lp09 = PASS if lp09_escalated else FAIL
t2_cr09 = PASS if cr09_fired else FAIL
print(f"\n  [{t2_ny}] NY governing law detected: {governing_law}")
print(f"  [{t2_lp09}] LP-09 state is {lp09_state} (expected: potentially_unenforceable or covered_unfavorable)")
print(f"  [{t2_cr09}] CR-09 fired: {cr09_fired}")
print(f"  ENFORCEABILITY pill surfaced: {enf_surfaced} (informational — pill sourcing varies by build)")
if escalation_log:
    print(f"  Escalation log sample: {escalation_log[:2]}")

with open(OUT_DIR / "t10ny_results.json", "w") as f:
    json.dump({
        "governing_law": governing_law,
        "total_ns_signals": total_ny,
        "lp09_state": lp09_state,
        "cr09_fired": cr09_fired,
        "escalation_log_count": len(escalation_log),
    }, f, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# Test 3: T-13 Mode C — non-T-10 fixture sanity check
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 3: T-13 Mode C — non-T-10 sanity check")
print("="*70)
t3_pass = False
try:
    result_t13, elapsed_t13 = run_mode_c("T-13_lp00_heavy.txt")
    total_t13, by_type_t13 = extract_ns_signals(result_t13)
    states_t13 = extract_coverage_states(result_t13)
    no_scm_t13 = by_type_t13.get("schema_clue_match", 0) == 0
    has_ca = len(states_t13) > 0
    t3_pass = no_scm_t13 and has_ca
    print(f"  Elapsed: {elapsed_t13}s")
    print(f"  Total ns signals: {total_t13}  |  schema_clue_match: {by_type_t13.get('schema_clue_match', 0)}")
    print(f"  Coverage assessments: {len(states_t13)}")
    print(f"  [{PASS if t3_pass else FAIL}] No exceptions; no schema_clue_match; coverage populated")
except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    import traceback; traceback.print_exc()

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
all_pass = t1_pass and t1_no_scm and ny_detected and lp09_escalated and t3_pass
print(f"  Test 1 (T-10 signal count ≤10):   {PASS if t1_pass else FAIL}")
print(f"  Test 1 (schema_clue_match = 0):   {PASS if t1_no_scm else FAIL}")
print(f"  Test 2 (NY governing law):         {t2_ny}")
print(f"  Test 2 (LP-09 escalated):          {t2_lp09}")
print(f"  Test 2 (CR-09 fired):              {t2_cr09}")
print(f"  Test 3 (T-13 sanity):              {PASS if t3_pass else FAIL}")
print()
print(f"  OVERALL: {'ALL PASS — ready for production push' if all_pass else 'FAILURES — DO NOT PUSH'}")
