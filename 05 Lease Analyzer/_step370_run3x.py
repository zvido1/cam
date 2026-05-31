"""Step 370 driver — run Atlas Meridian 3x on identical input (Mode C, tenant).

Diagnostic only. No code change to detection logic. Replicates the exact config
of reference run lease_review_20260529_222051 (Mode C / analyze, perspective=tenant,
identity_check=landlord_property, blank_template, 33 active provisions).

Provider keys loaded from the DoubleCheck keys file. OpenRouter disabled per
instruction (lease evaluators use anthropic / openai / xai directly).
"""
import os
import sys
from datetime import datetime

# ── Inject provider keys (direct providers only; NO OpenRouter) ──
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
loaded = []
for line in open(KEYS_ENV, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    k = k.strip()
    if k in WANTED:
        os.environ[k] = v.strip().strip('"').strip("'")
        loaded.append(k)
# Hard-disable OpenRouter so nothing routes through it.
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)
print(f"[step370] provider keys loaded: {sorted(loaded)}", flush=True)
print(f"[step370] DISABLE_OPENROUTER={os.environ['DISABLE_OPENROUTER']}", flush=True)

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only
from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions

LEASE_DIR = os.path.join(CAM_ROOT, "05 Lease Analyzer")
TENANT = os.path.join(LEASE_DIR, "test_data", "tenants", "atlas_meridian_warehouse_lease.txt")
RESULTS = os.path.join(LEASE_DIR, "results")

provisions = get_active_provisions(selected_ids=None, custom_provisions=None)
print(f"[step370] active provisions: {len(provisions)}", flush=True)

N = 3
for i in range(1, N + 1):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_id = f"lease_review_{stamp}_s370r{i}"
    out_dir = os.path.join(RESULTS, job_id)
    cfg = {
        "output_dir": out_dir,
        "_job_id": job_id,
        "custom_from_scan": [],
        "added_from_scan": [],
        "template_type": "blank_template",
        "identity_check": "landlord_property",
        "access_code": "cam_demo_2026",
        "perspective": "tenant",
    }
    print(f"\n========== STEP370 RUN {i}/{N} START job_id={job_id} ==========", flush=True)
    try:
        run_lease_coverage_only(
            tenant_path=TENANT,
            provisions=provisions,
            config=cfg,
            run_id="tenant_0",
            progress_callback=None,
        )
        print(f"========== STEP370 RUN {i}/{N} DONE  job_id={job_id} ==========", flush=True)
    except Exception as e:
        import traceback
        print(f"========== STEP370 RUN {i}/{N} FAILED job_id={job_id}: {type(e).__name__}: {e} ==========", flush=True)
        traceback.print_exc()

print("\n[step370] all runs attempted.", flush=True)
