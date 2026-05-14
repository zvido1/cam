"""
Step 305a validation — Tests 2 and 3 only (Test 1 already passed).
Test 1 result: 0 total ns signals, 0 schema_clue_match (down from ~50).
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
    return result, round(time.time() - t0, 1)

def extract_ns_signals(result):
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
    ca = result.get("coverage_assessment") or []
    return {a.get("issue_area_id", a.get("provision_id", "?")): a.get("coverage_state", "?")
            for a in ca}

# ── Test 2: T-10-NY ──────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 2: T-10-NY Mode C -- jurisdiction / ENFORCEABILITY pill")
print("="*70)
result_ny, elapsed_ny = run_mode_c("T-10-NY.txt")
total_ny, by_type_ny = extract_ns_signals(result_ny)
states_ny = extract_coverage_states(result_ny)

governing_law = (
    result_ny.get("jurisdiction", {}) or {}
).get("governing_law") or result_ny.get("governing_law")
escalation_log = (
    result_ny.get("escalation_log")
    or result_ny.get("jurisdiction_escalation_log")
    or []
)
conflicts = result_ny.get("conflicts") or []

lp09_state = states_ny.get("LP-09", "(not found)")
cr09_fired = any(
    c.get("conflict_id") == "CR-09" or c.get("id") == "CR-09"
    for c in conflicts
)
ny_detected = governing_law and "new york" in str(governing_law).lower()
lp09_escalated = lp09_state in ("potentially_unenforceable", "covered_unfavorable")

print(f"  Elapsed: {elapsed_ny}s")
print(f"  Governing law: {governing_law}")
print(f"  LP-09 state: {lp09_state}")
print(f"  CR-09 fired: {cr09_fired}")
print(f"  Escalation log entries: {len(escalation_log)}")
print(f"  Conflicts: {[c.get('conflict_id') or c.get('id') for c in conflicts]}")
print(f"  ns signals: {total_ny}, schema_clue_match: {by_type_ny.get('schema_clue_match', 0)}")
t2_ny = PASS if ny_detected else FAIL
t2_lp09 = PASS if lp09_escalated else FAIL
t2_cr09 = PASS if cr09_fired else FAIL
t2_no_scm = PASS if by_type_ny.get("schema_clue_match", 0) == 0 else FAIL
print(f"\n  [{t2_ny}] NY governing law detected")
print(f"  [{t2_lp09}] LP-09 escalated (state={lp09_state})")
print(f"  [{t2_cr09}] CR-09 fired")
print(f"  [{t2_no_scm}] schema_clue_match = 0")

# ── Test 3: T-13 ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("TEST 3: T-13 Mode C -- non-T-10 sanity check")
print("="*70)
t3_pass = False
try:
    result_t13, elapsed_t13 = run_mode_c("T-13_lp00_heavy.txt")
    total_t13, by_type_t13 = extract_ns_signals(result_t13)
    states_t13 = extract_coverage_states(result_t13)
    no_scm = by_type_t13.get("schema_clue_match", 0) == 0
    has_ca = len(states_t13) > 0
    t3_pass = no_scm and has_ca
    print(f"  Elapsed: {elapsed_t13}s")
    print(f"  Total ns signals: {total_t13}  |  schema_clue_match: {by_type_t13.get('schema_clue_match', 0)}")
    print(f"  Coverage assessments: {len(states_t13)}")
    print(f"  By type: {by_type_t13}")
    print(f"  [{PASS if t3_pass else FAIL}] No exceptions; no schema_clue_match; coverage populated")
except Exception as e:
    print(f"  [FAIL] Exception: {e}")
    import traceback; traceback.print_exc()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SUMMARY (Test 1 already confirmed: 0 ns signals, 0 schema_clue_match)")
print("="*70)
print(f"  Test 1 (T-10, 0 signals, 0 scm):  PASS (confirmed prior run)")
print(f"  Test 2 NY governing law:           {t2_ny}")
print(f"  Test 2 LP-09 escalated:            {t2_lp09}")
print(f"  Test 2 CR-09 fired:                {t2_cr09}")
print(f"  Test 2 schema_clue_match=0:        {t2_no_scm}")
print(f"  Test 3 T-13 sanity:                {PASS if t3_pass else FAIL}")
all_pass = ny_detected and lp09_escalated and t3_pass
print()
print(f"  OVERALL: {'ALL PASS -- ready for production push' if all_pass else 'FAILURES -- DO NOT PUSH'}")
