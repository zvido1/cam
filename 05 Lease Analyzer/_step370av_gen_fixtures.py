"""Step 370a-v fixture generator.

Creates two throwaway result dirs to exercise the Directional Synthesis Completeness
Guard through the real stored-run loading path:

  fixture_nonemp  — 28 directional findings + incomplete synthesis_meta (banner must
                    appear above the real findings, findings must remain visible)
  fixture_empty   — 0 directional findings + incomplete synthesis_meta (the truly
                    catastrophic case: banner must appear even with nothing beneath it)

Neither dir is touched again after creation; real run dirs are never modified.
Run from:  cd "05 Lease Analyzer"  then  python _step370av_gen_fixtures.py
"""
import json
import os
import shutil
from pathlib import Path

# ── Donor: s370r3 — 28 dirs, full integrity, clean data ──
LEASE_DIR = Path(__file__).parent
RESULTS   = LEASE_DIR / "results"
DONOR_PR  = RESULTS / "lease_review_20260529_195234_s370r3" / "tenant_0" / "pipeline_results.json"

assert DONOR_PR.exists(), f"Donor not found: {DONOR_PR}"

# ── Fixture IDs ──
IDS = {
    "nonemp": "lease_review_370av_fixture_nonemp",
    "empty":  "lease_review_370av_fixture_empty",
}

# ── Collapse-signature synthesis_meta patch ──
GUARD_BLOCK = {
    "triggered": True,
    "reason_code": "low_pass1_candidate_count_with_high_flagged_lp_volume",
    "flagged_lp_count": 28,
    "pass1_directional_candidate_count": 3,
    "candidate_density": 0.10714285714285714,
    "high_flagged_lp_threshold": 20,
    "low_candidate_threshold": 5,
    "execution_path": "unknown",
    "raw_response_paths": [],
    "request_hashes": [],
    "parse_status": [],
}

donor = json.loads(DONOR_PR.read_text(encoding="utf-8"))

for variant, fid in IDS.items():
    fixture_dir = RESULTS / fid / "tenant_0"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    pr = json.loads(json.dumps(donor))   # deep copy

    # Inject collapse signature into _stage_data.synthesis_meta
    if "_stage_data" not in pr or pr["_stage_data"] is None:
        pr["_stage_data"] = {}
    if "synthesis_meta" not in pr["_stage_data"] or pr["_stage_data"]["synthesis_meta"] is None:
        pr["_stage_data"]["synthesis_meta"] = {}
    sm = pr["_stage_data"]["synthesis_meta"]
    sm["directional_synthesis_status"] = "incomplete_low_candidate_anomaly"
    sm["directional_guard"] = GUARD_BLOCK

    if variant == "empty":
        # Emptied case: remove all directional_mismatch findings from cross_provision_findings
        before = len(pr.get("cross_provision_findings", []))
        pr["cross_provision_findings"] = [
            f for f in (pr.get("cross_provision_findings") or [])
            if f.get("finding_type") != "directional_mismatch"
        ]
        after = len(pr.get("cross_provision_findings", []))
        print(f"[{variant}] directional findings removed: {before - after} -> {after} total cpfs")

    pr_path = fixture_dir / "pipeline_results.json"
    pr_path.write_text(json.dumps(pr, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{variant}] pipeline_results.json written to {pr_path}")

    # ── Minimal job.json the server loader expects ──
    result_path = str(pr_path)
    job = {
        "job_id": fid,
        "domain": "lease_review",
        "status": "completed",
        "created_at": "2026-05-29T00:00:00+00:00",
        "started_at": "2026-05-29T00:00:00+00:00",
        "completed_at": "2026-05-29T00:01:00+00:00",
        "email": "",
        "estimated_minutes": 0,
        "feedback": [],
        "error": None,
        "expires_at": "2027-01-01T00:00:00+00:00",
        "input_config": {
            "template_file": "",
            "template_path": "",
            "tenants": [{
                "filename": "atlas_meridian_warehouse_lease.txt",
                "upload_path": "",
                "status": "completed",
                "stage": "done",
                "error": None,
                "result_path": result_path,
                "annotated_path": None,
                "comparison_view_path": None,
            }],
            "provisions": None,
            "custom_provisions": None,
            "custom_from_scan": [],
            "added_from_scan": [],
            "prescan_record": None,
            "strictness": "standard",
            "instructions": "",
            "template_type": "blank_template",
            "identity_check": "landlord_property",
            "access_code": "cam_demo_2026",
            "mode": "analyze",
            "perspective": "tenant",
        },
    }
    job_path = RESULTS / fid / "job.json"
    job_path.write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{variant}] job.json written: {job_path}")

print("\nFixtures ready. IDs:")
for variant, fid in IDS.items():
    print(f"  {variant}: {fid}")
print("\nRestart uvicorn (full restart, not reload) then open:")
for fid in IDS.values():
    print(f"  /?job={fid}")
