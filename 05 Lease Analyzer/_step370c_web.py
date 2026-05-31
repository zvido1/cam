"""Step 370c web runner — submit one Atlas Meridian run through the live server.

Usage:
    python _step370c_web.py <run_label>
    e.g.  python _step370c_web.py 370c_W1

Submits via the /api/analyze POST endpoint (same path the browser uses), polls for
completion, then prints the same artifact summary as the headless runner.
Server must be running on localhost:8000 before calling this.
"""
import sys, json, time, hashlib, requests
from pathlib import Path

BASE   = "http://localhost:8000"
LABEL  = sys.argv[1] if len(sys.argv) > 1 else "370c_W_unlabeled"
TENANT = Path(r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\test_data\tenants\atlas_meridian_warehouse_lease.txt")

tenant_md5 = hashlib.md5(open(TENANT, "rb").read()).hexdigest()
print(f"[370c_web] label={LABEL} tenant_md5={tenant_md5}", flush=True)

# ── Submit job ──
with open(TENANT, "rb") as fh:
    resp = requests.post(
        f"{BASE}/api/jobs/lease",
        data={
            "access_code": "cam_demo_2026",
            "perspective": "tenant",
            "template_type": "blank_template",
            "identity_check": "landlord_property",
            "mode": "analyze",
            "email": "",
            "strictness": "standard",
        },
        files={"tenant_files": (TENANT.name, fh, "text/plain")},
        timeout=30,
    )

if resp.status_code not in (200, 201):
    print(f"[370c_web] SUBMIT FAILED: {resp.status_code} {resp.text[:300]}", flush=True)
    sys.exit(1)

job_id = resp.json().get("job_id")
print(f"[370c_web] submitted job_id={job_id}", flush=True)

# ── Poll until complete ──
MAX_WAIT = 1800  # 30 min
poll_interval = 15
waited = 0
while waited < MAX_WAIT:
    time.sleep(poll_interval)
    waited += poll_interval
    status_resp = requests.get(f"{BASE}/api/jobs/{job_id}", timeout=15)
    if status_resp.status_code != 200:
        print(f"[370c_web] poll error {status_resp.status_code}", flush=True)
        continue
    job = status_resp.json()
    status = job.get("status")
    tenants = job.get("input_config", {}).get("tenants", [])
    stage = tenants[0].get("stage") if tenants else "?"
    print(f"[370c_web] {waited}s: status={status} stage={stage}", flush=True)
    if status in ("completed", "failed", "cancelled"):
        break

# ── Fetch results and print artifact summary ──
results_resp = requests.get(f"{BASE}/api/jobs/{job_id}/results", timeout=30)
if results_resp.status_code != 200:
    print(f"[370c_web] RESULTS FETCH FAILED {results_resp.status_code}: {results_resp.text[:200]}", flush=True)
    sys.exit(1)

data   = results_resp.json()
tenant = data.get("tenants", [{}])[0]
pr     = tenant.get("results") or {}
cpfs   = pr.get("cross_provision_findings") or []
dirs   = [f for f in cpfs if f.get("finding_type") == "directional_mismatch"]
sd     = pr.get("_stage_data") or {}
sm     = sd.get("synthesis_meta") or {}
gd     = sm.get("directional_guard") or {}
integ  = sm.get("pass2_integrity") or {}

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

print(f"[370c_web] DONE {job_id} label={LABEL}", flush=True)
