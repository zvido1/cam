"""Step 269 — Full Pipeline Corpus Validation.

Runs the production Mode C pipeline on T-01 through T-16 against the
current v1.1.4 schema. Saves per-tenant pipeline_results.json to
experiments/step_269_corpus_validation/T-XX/.

Read-only on production code: schema and lease_coverage.py at v1.1.4 / Step 268
state, untouched. No cam/core/ changes.

Failure handling: extraction or classification failures are caught,
recorded in failures.json, and the next tenant is processed. A 14-of-16
partial result is more useful than a stuck script.

Comparison matrix and headline.txt are written by analyze_corpus.py
after this script completes.
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── 1. Load API keys (force-override harness Cowork proxy) ─────────────────
KEYS_ENV = Path(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")
with open(KEYS_ENV, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ[k.strip()] = v
for proxy in ("ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "XAI_BASE_URL"):
    os.environ.pop(proxy, None)
for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"):
    assert os.environ.get(var), f"{var} missing after load"

PROJECT = Path(r"C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "05 Lease Analyzer"))

OUT_DIR = PROJECT / "experiments" / "step_269_corpus_validation"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TENANT_DIR = PROJECT / "05 Lease Analyzer" / "test_data" / "tenants"

# Canonical T-NN file selection: prefer .docx, fall back to .txt.
# For T-NN_<descriptor> matches, take the alphabetically-first descriptor
# to keep selection deterministic across runs.
def pick_tenant_file(n: int) -> Path | None:
    base = f"T-{n:02d}"
    matches = sorted(TENANT_DIR.glob(f"{base}_*"))
    docx = [m for m in matches if m.suffix.lower() == ".docx"]
    txt = [m for m in matches if m.suffix.lower() == ".txt"]
    if docx:
        return docx[0]
    if txt:
        return txt[0]
    return None

from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only

# Verify schema version is v1.1.4 BEFORE doing anything expensive
schema_path = PROJECT / "cam" / "adapters" / "lease_review" / "schemas" / "retail_lease_knowledge.json"
with open(schema_path, encoding="utf-8") as f:
    schema = json.load(f)
assert schema["schema_version"] == "1.1.4", f"Expected schema v1.1.4; got {schema['schema_version']}"
print(f"[setup] Schema v1.1.4 confirmed.", flush=True)

# Resolve tenant files
tenant_plan: list[tuple[str, Path | None]] = []
for n in range(1, 17):
    tenant_plan.append((f"T-{n:02d}", pick_tenant_file(n)))

print(f"[setup] Tenant plan ({len(tenant_plan)}):", flush=True)
for name, path in tenant_plan:
    print(f"  {name}: {path.name if path else '(no file)'}", flush=True)

# Cost / time budget
HARD_TIME_LIMIT_SEC = 90 * 60  # 90 min
RUN_LOG: list[dict] = []
failures: list[dict] = []

t_start = time.time()

for name, path in tenant_plan:
    elapsed_so_far = time.time() - t_start
    if elapsed_so_far > HARD_TIME_LIMIT_SEC:
        print(f"\n[BUDGET] Hard 90-min wall-clock budget exceeded at {elapsed_so_far:.0f}s; stopping.", flush=True)
        failures.append({"tenant": name, "error": "skipped_due_to_budget", "elapsed_so_far_sec": elapsed_so_far})
        break

    tenant_out_dir = OUT_DIR / name
    tenant_out_dir.mkdir(exist_ok=True)
    results_path = tenant_out_dir / "pipeline_results.json"
    log_path = tenant_out_dir / "run_log.txt"

    if not path:
        msg = f"[{name}] No tenant file found — skipping."
        print(msg, flush=True)
        failures.append({"tenant": name, "error": "no_file_found"})
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(msg + "\n")
        continue

    print(f"\n[{name}] Running Mode C on {path.name}...", flush=True)
    t0 = time.time()
    try:
        result = run_lease_coverage_only(
            tenant_path=str(path),
            run_id=f"step_269_{name}",
        )
        elapsed = time.time() - t0
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        ca = {a["issue_area_id"]: a for a in result.get("coverage_assessment", [])}
        lp11 = ca.get("LP-11", {}).get("coverage_state")
        lp13 = ca.get("LP-13", {}).get("coverage_state")
        api_calls = result.get("api_calls_total", 0)
        print(f"[{name}] DONE  {elapsed:.1f}s  api_calls={api_calls}  LP-11={lp11}  LP-13={lp13}", flush=True)
        RUN_LOG.append({
            "tenant": name,
            "file": path.name,
            "status": "success",
            "elapsed_sec": round(elapsed, 1),
            "api_calls": api_calls,
            "lp11": lp11,
            "lp13": lp13,
        })
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"OK in {elapsed:.1f}s, api_calls={api_calls}, LP-11={lp11}, LP-13={lp13}\n")
    except Exception as e:
        elapsed = time.time() - t0
        tb = traceback.format_exc()
        print(f"[{name}] FAILED after {elapsed:.1f}s: {type(e).__name__}: {e}", flush=True)
        failures.append({
            "tenant": name,
            "file": path.name,
            "error": f"{type(e).__name__}: {e}",
            "elapsed_sec": round(elapsed, 1),
            "traceback": tb,
        })
        RUN_LOG.append({
            "tenant": name,
            "file": path.name,
            "status": "failed",
            "elapsed_sec": round(elapsed, 1),
            "error": f"{type(e).__name__}: {e}",
        })
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"FAILED in {elapsed:.1f}s: {type(e).__name__}: {e}\n\n{tb}\n")

t_total = time.time() - t_start

with open(OUT_DIR / "run_log.json", "w", encoding="utf-8") as f:
    json.dump({
        "started_at": datetime.fromtimestamp(t_start, timezone.utc).isoformat(),
        "total_elapsed_sec": round(t_total, 1),
        "tenants": RUN_LOG,
        "failures": failures,
    }, f, indent=2)

print(f"\n[total] {t_total:.0f}s elapsed across {len(RUN_LOG)} tenants. "
      f"Successes: {sum(1 for r in RUN_LOG if r['status']=='success')}, "
      f"Failures: {len(failures)}", flush=True)
