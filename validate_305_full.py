"""
Step 305 full-schema smoke test.
One Mode C run on T-10. Verifies all 32 LPs route through 305 without
crashing and produce element_verdicts. LP-state stability not required.
"""
import json, sys, time, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cam.core.config import CAM_ROOT, find_and_load_env
from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

find_and_load_env()

TENANT_PATH = str(CAM_ROOT / "05 Lease Analyzer" / "test_data" / "tenants" / "T-10_Negotiated_Tennant_Lease.docx")
OUT_DIR = CAM_ROOT / "experiments" / "validate_305_full"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Running T-10 Mode C (single pass, all 32 LPs)...")
t0 = time.time()
result = run_lease_coverage_only(
    tenant_path=TENANT_PATH,
    config={"output_dir": str(OUT_DIR)},
)
elapsed = round(time.time() - t0, 1)
print(f"Elapsed: {elapsed}s")

ca = result.get("coverage_assessment") or []
print(f"\n{'LP':8} {'Method':28} {'State':22} {'Elements':8}")
print("-" * 72)

ok_305 = []
legacy = []
errors = []

for a in ca:
    pid = a.get("issue_area_id", "?")
    method = a.get("coverage_method", "legacy")
    state = a.get("coverage_state", "?")
    evs = a.get("element_verdicts") or []
    n = len(evs)
    print(f"{pid:8} {method:28} {state:22} {n}")
    if method == "step_305_per_element":
        if n > 0:
            ok_305.append(pid)
        else:
            errors.append(f"{pid}: 305 path but 0 element_verdicts")
    else:
        legacy.append(pid)

print(f"\n{'='*72}")
print(f"305 path with verdicts : {len(ok_305):2}  {ok_305}")
print(f"Legacy path            : {len(legacy):2}  {legacy}")
if errors:
    print(f"ERRORS                 : {len(errors)}")
    for e in errors:
        print(f"  {e}")
else:
    print("No errors.")

with open(OUT_DIR / "summary.json", "w") as f:
    json.dump({"ok_305": ok_305, "legacy": legacy, "errors": errors, "elapsed": elapsed}, f, indent=2)

print(f"\nSummary: {OUT_DIR / 'summary.json'}")
if errors or len(ok_305) < 32:
    print("\nSMOKE TEST: PARTIAL — some LPs on legacy path (check above)")
    sys.exit(1)
else:
    print("\nSMOKE TEST: PASS — all 32 LPs on 305 path with element verdicts")
