"""Step 370c headless runner — one Atlas Meridian Mode-C run.

Usage:
    python _step370c_headless.py <run_label>
    e.g.  python _step370c_headless.py 370c_H1

Replicates the exact pipeline_config the web server uses for Mode C / tenant /
landlord_property runs. Reads provider keys from the DoubleCheck .env file.
OpenRouter disabled per standing instruction.
"""
import os, sys, json, hashlib
from datetime import datetime
from pathlib import Path

# ── Keys ──
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
for line in open(KEYS_ENV, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k.strip() in WANTED:
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

label = sys.argv[1] if len(sys.argv) > 1 else "370c_H_unlabeled"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
job_id = f"lease_review_{stamp}_{label}"

LEASE_DIR = Path(CAM_ROOT) / "05 Lease Analyzer"
TENANT    = LEASE_DIR / "test_data" / "tenants" / "atlas_meridian_warehouse_lease.txt"
RESULTS   = LEASE_DIR / "results"

tenant_md5 = hashlib.md5(open(TENANT, "rb").read()).hexdigest()
print(f"[370c] label={label} job_id={job_id}", flush=True)
print(f"[370c] tenant md5={tenant_md5}", flush=True)

from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only
from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions

provisions = get_active_provisions(selected_ids=None, custom_provisions=None)
out_dir    = str(RESULTS / job_id)

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

print(f"[370c] starting headless run...", flush=True)
result = run_lease_coverage_only(
    tenant_path=str(TENANT),
    provisions=provisions,
    config=cfg,
    run_id="tenant_0",
    progress_callback=None,
)

pr_path = Path(out_dir) / "tenant_0" / "pipeline_results.json"
if pr_path.exists():
    pr = json.loads(pr_path.read_text(encoding="utf-8"))
    cpfs = pr.get("cross_provision_findings", [])
    dirs = [f for f in cpfs if f.get("finding_type") == "directional_mismatch"]
    sd   = pr.get("_stage_data", {}) or {}
    sm   = sd.get("synthesis_meta", {}) or {}
    gd   = sm.get("directional_guard") or {}
    integ = sm.get("pass2_integrity") or {}
    print(f"[370c_result] job_id={job_id}", flush=True)
    print(f"[370c_result] total_cpf={len(cpfs)}", flush=True)
    print(f"[370c_result] directional_final={len(dirs)}", flush=True)
    print(f"[370c_result] flagged_lp_count={sm.get('flagged_lp_count')}", flush=True)
    print(f"[370c_result] pass1_dir_candidates={gd.get('pass1_directional_candidate_count')}", flush=True)
    print(f"[370c_result] directional_synthesis_status={sm.get('directional_synthesis_status')}", flush=True)
    print(f"[370c_result] guard_triggered={gd.get('triggered')}", flush=True)
    print(f"[370c_result] candidate_density={gd.get('candidate_density')}", flush=True)
    evalA = integ.get("A") or {}
    print(f"[370c_result] evalA_n_objects={evalA.get('n_objects')}", flush=True)
    print(f"[370c_result] evalA_matched_directional={evalA.get('matched_directional')}", flush=True)
    print(f"[370c_result] evalA_all_lost={evalA.get('all_lost')}", flush=True)
    pr2raw = sm.get("pass2_raw") or {}
    for role, info in pr2raw.items():
        print(f"[370c_result] pass2_raw_{role}: n_objects={info.get('n_objects')} "
              f"dir_objects={info.get('dir_object_count')} "
              f"dir_verdicts={info.get('dir_verdicts')}", flush=True)
else:
    print(f"[370c_result] ERROR: pipeline_results.json not found at {pr_path}", flush=True)

print(f"[370c] DONE {job_id}", flush=True)
