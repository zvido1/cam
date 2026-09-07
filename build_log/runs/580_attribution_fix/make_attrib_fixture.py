"""Step 580-2 — build the on-device verification fixture.

The stored Butler run predates 580-2(a), so its element_verdicts carry no absence_adverse_to.
This script injects it from the schema element -- which is EXACTLY what the backend change now
does at lease_coverage_305.py verdict_record: `element.get("absence_adverse_to")`, same source,
same field, no transformation. So what the browser then renders is the shape the pipeline now
produces, and the on-device check is a real check of the frontend against the new contract.

What this does NOT verify is the backend write itself. That is covered by
test_580_attribution.py::test_verdict_record_carries_absence_adverse_to and by reading the line.
Said plainly here so the status file does not have to overclaim.

Two jobs are written so both lenses can be looked at:
    attribcheck-tenant    perspective: tenant     -> expect "protects the landlord" notes
    attribcheck-landlord  perspective: landlord   -> expect "protects the tenant" notes, more of them
"""
import json
import os
import shutil
import sys
from pathlib import Path

CAM = Path("C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(CAM))
from cam.adapters.lease_review.lease_knowledge import get_schema

SRC = CAM / "build_log/runs/537_butler_crossing_outlot_lease.txt-modec_20260903_131050/run_01_full.json"
RESULTS = CAM / "05 Lease Analyzer" / "results"

POLARITY = {e["element_id"]: e.get("absence_adverse_to")
            for a in get_schema()["issue_areas"]
            for e in (a.get("expected_elements_305") or [])}

src = json.loads(SRC.read_text(encoding="utf-8"))
injected = 0
for item in src.get("coverage_assessment") or []:
    for ev in (item.get("element_verdicts") or []):
        if ev.get("element_id") in POLARITY:
            ev["absence_adverse_to"] = POLARITY[ev["element_id"]]
            injected += 1

for job_id, perspective in (("attribcheck-tenant", "tenant"), ("attribcheck-landlord", "landlord")):
    job_dir = RESULTS / job_id
    tenant_dir = job_dir / "tenant_0"
    if job_dir.exists():
        shutil.rmtree(job_dir)
    tenant_dir.mkdir(parents=True)
    result_path = tenant_dir / "pipeline_results.json"
    result_path.write_text(json.dumps(src), encoding="utf-8")
    job = {
        "job_id": job_id, "domain": "lease_review", "status": "completed",
        "created_at": "2026-09-06T00:00:00+00:00", "started_at": "2026-09-06T00:00:00+00:00",
        "completed_at": "2026-09-06T00:01:00+00:00", "email": "", "estimated_minutes": 0,
        "feedback": [], "error": None, "expires_at": "2027-06-01T00:00:00+00:00",
        "input_config": {
            "template_file": "", "template_path": "",
            "tenants": [{"filename": "butler_crossing_outlot_lease.txt", "upload_path": "",
                         "status": "completed", "stage": "done", "error": None,
                         "result_path": str(result_path), "annotated_path": None,
                         "comparison_view_path": None}],
            "provisions": None, "custom_provisions": None, "custom_from_scan": [],
            "added_from_scan": [], "prescan_record": None, "strictness": "standard",
            "instructions": "", "template_type": "blank_template",
            "identity_check": "landlord_property", "access_code": "cam_demo_2026",
            "mode": "analyze", "perspective": perspective,
        },
    }
    (job_dir / "job.json").write_text(json.dumps(job, indent=1), encoding="utf-8")
    print("wrote %s (perspective=%s)" % (job_id, perspective))

print("polarity values injected onto %d element verdicts" % injected)
