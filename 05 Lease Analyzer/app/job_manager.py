"""
CAM Lease Analyzer Web App — Job Manager

In-memory job queue with file persistence. Domain-agnostic job layer —
lease-specific pipeline calls are isolated to process_lease_job().
"""

import copy
import json
import logging
import os
import secrets
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.config import get_config

logger = logging.getLogger(__name__)

# ── In-memory job store ──
_jobs: dict = {}
_jobs_lock = threading.Lock()

PROVISION_FLAG_RATES = {
    "LP-01": 0.26, "LP-02": 0.11, "LP-03": 0.33, "LP-04": 0.09,
    "LP-05": 0.41, "LP-06": 0.27, "LP-07": 0.31, "LP-08": 0.30,
    "LP-09": 0.62, "LP-10": 0.38, "LP-11": 0.60, "LP-12": 0.46,
    "LP-13": 0.60, "LP-14": 0.26, "LP-15": 0.14, "LP-16": 0.32,
    "LP-17": 0.05, "LP-18": 0.22,
}
VARIABLE_COST_PER_FLAGGED = 29
EXTRACTION_BASE_SECS = 90


def estimate_job_minutes(input_config: dict) -> int:
    """Match the frontend's rough lease-timing model closely enough to avoid jarring ETA drift."""
    tenants = input_config.get("tenants", []) or []
    num_tenants = max(1, len(tenants))

    selected_ids = list(input_config.get("provisions") or [])
    custom_provisions = list(input_config.get("custom_provisions") or [])

    if selected_ids:
        provision_ids = selected_ids
        prov_count = len(selected_ids) + len(custom_provisions)
    else:
        # Full standard set is implied when no explicit subset is passed.
        provision_ids = list(PROVISION_FLAG_RATES.keys())
        prov_count = len(provision_ids) + len(custom_provisions)

    variable_secs = 0.0
    for pid in provision_ids:
        variable_secs += PROVISION_FLAG_RATES.get(pid, 0.85) * VARIABLE_COST_PER_FLAGGED
    variable_secs += len(custom_provisions) * 0.85 * VARIABLE_COST_PER_FLAGGED

    identity_check = input_config.get("identity_check", "landlord_property")
    id_check_count = {
        "clauses_only": 0,
        "landlord_property": 2,
        "landlord_tenant": 2,
    }.get(identity_check, 2)

    gap_repair_buffer = 120 if prov_count >= 12 else 60
    secs_per_lease = max(
        60,
        EXTRACTION_BASE_SECS + variable_secs + (id_check_count * 10) + gap_repair_buffer,
    )
    mins_per_lease = max(1, round(secs_per_lease / 60))
    return num_tenants * mins_per_lease


# ── Job ID generation ──

def _generate_job_id(domain: str) -> str:
    now = datetime.now(timezone.utc)
    suffix = secrets.token_hex(3)
    return f"{domain}_{now.strftime('%Y%m%d_%H%M%S')}_{suffix}"


# ── CRUD operations ──

def create_job(domain: str, email: str, input_config: dict, job_id: str = None) -> dict:
    """Create a new job, store in memory, return job dict."""
    if job_id is None:
        job_id = _generate_job_id(domain)
    num_tenants = len(input_config.get("tenants", []))
    estimated_minutes = estimate_job_minutes(input_config)

    job = {
        "job_id": job_id,
        "domain": domain,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "email": email,
        "estimated_minutes": estimated_minutes,
        "input_config": input_config,
        "feedback": [],
        "error": None,
    }

    with _jobs_lock:
        _jobs[job_id] = job

    logger.info(f"Job created: {job_id} ({domain}, {num_tenants} tenant(s))")
    return job


def get_job(job_id: str) -> Optional[dict]:
    """Retrieve job by ID. Returns live reference (for internal use)."""
    with _jobs_lock:
        return _jobs.get(job_id)


def get_job_snapshot(job_id: str) -> Optional[dict]:
    """Return a deep copy of the job dict, safe for API serialization.

    The live job dict is mutated by background threads (progress callbacks,
    status updates). Returning the live reference to FastAPI causes a race
    where the JSON serializer reads stale tenant states while the background
    thread holds the lock. Deep-copying under the lock gives a consistent
    point-in-time snapshot.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        # Log tenant statuses for debugging progress display
        tenants = job.get("input_config", {}).get("tenants", [])
        if job.get("status") == "processing":
            statuses = [(t.get("filename", "?"), t.get("status"), t.get("current_stage"), t.get("stage_detail", "")[:40]) for t in tenants]
            logger.debug(f"Snapshot {job_id}: {statuses}")
        return copy.deepcopy(job)


def list_jobs(email: str = None) -> list:
    """List all jobs, optionally filtered by email. Returns summaries."""
    with _jobs_lock:
        jobs = list(_jobs.values())

    if email:
        jobs = [j for j in jobs if j.get("email") == email]

    # Return summaries (not full input_config)
    summaries = []
    for j in jobs:
        tenants = j.get("input_config", {}).get("tenants", [])
        summaries.append({
            "job_id": j["job_id"],
            "domain": j["domain"],
            "status": j["status"],
            "created_at": j["created_at"],
            "completed_at": j.get("completed_at"),
            "expires_at": j.get("expires_at"),
            "email": j.get("email"),
            "tenant_count": len(tenants),
            "estimated_minutes": j.get("estimated_minutes"),
        })

    return summaries


def update_tenant_status(
    job_id: str,
    tenant_index: int,
    status: str,
    stage: str = None,
    error: str = None,
) -> None:
    """Update a specific tenant's processing status within a job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        tenants = job["input_config"].get("tenants", [])
        if 0 <= tenant_index < len(tenants):
            tenants[tenant_index]["status"] = status
            if stage is not None:
                tenants[tenant_index]["stage"] = stage
            if error is not None:
                tenants[tenant_index]["error"] = error


def mark_job_started(job_id: str) -> Optional[str]:
    """Set job status to processing and stamp a true processing start time."""
    started_at = datetime.now(timezone.utc).isoformat()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        job["status"] = "processing"
        job["started_at"] = started_at
        job["completed_at"] = None
        job.pop("cancelled_at", None)
        job.pop("expires_at", None)
        return started_at


def mark_job_completed(job_id: str) -> None:
    """Set job status to completed. Expiry starts immediately (15 min)."""
    config = get_config()
    expiry_minutes = config.get("JOB_EXPIRY_MINUTES", 1440)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expiry_minutes)

    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["status"] = "completed"
            job["completed_at"] = now.isoformat()
            job["expires_at"] = expires_at.isoformat()
    logger.info(f"Job completed: {job_id} (expires at {expires_at.isoformat()})")


def mark_job_failed(job_id: str, error: str) -> None:
    """Set job status to failed with error message."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["status"] = "failed"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["error"] = error
    logger.error(f"Job failed: {job_id} — {error}")


def request_cancel(job_id: str) -> None:
    """Set the cancel_requested flag on a processing job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["cancel_requested"] = True
    logger.info(f"Cancel requested: {job_id}")


def is_cancel_requested(job_id: str) -> bool:
    """Check if cancellation has been requested for this job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        return bool(job.get("cancel_requested"))


def mark_job_cancelled(job_id: str) -> None:
    """Set job status to cancelled. Expiry starts immediately."""
    config = get_config()
    expiry_minutes = config.get("JOB_EXPIRY_MINUTES", 1440)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expiry_minutes)

    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["status"] = "cancelled"
            job["cancelled_at"] = now.isoformat()
            job["completed_at"] = now.isoformat()
            job["expires_at"] = expires_at.isoformat()
    logger.info(f"Job cancelled: {job_id}")


def append_tenants(job_id: str, new_tenants: list) -> None:
    """Append new tenant entries to an existing job and reset to processing."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["input_config"]["tenants"].extend(new_tenants)
        job["status"] = "processing"
        job["started_at"] = None
        job["cancel_requested"] = False
    logger.info(f"Appended {len(new_tenants)} tenant(s) to job {job_id}")


def append_provisions(job_id: str, new_provision_ids: list) -> None:
    """Add new provision IDs to an existing job's provision list and reset to processing."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        existing = job["input_config"].get("provisions") or []
        job["input_config"]["provisions"] = existing + new_provision_ids
        job["status"] = "processing"
        job["started_at"] = None
        job["cancel_requested"] = False
    logger.info(f"Appended {len(new_provision_ids)} provision(s) to job {job_id}")


def start_incremental_processing(job_id: str, start_index: int) -> None:
    """Process only new tenants (from start_index onward) in a background thread."""
    mark_job_started(job_id)
    thread = threading.Thread(
        target=_run_incremental_tenants,
        args=(job_id, start_index),
        daemon=True,
        name=f"job-{job_id}-add",
    )
    thread.start()


def _run_incremental_tenants(job_id: str, start_index: int) -> None:
    """Process tenants starting from start_index (reuses existing pipeline config)."""
    from cam.adapters.lease_review.lease_adapter import run_lease_analysis
    from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions
    from app.notifications import send_job_complete_email

    job = get_job(job_id)
    if not job:
        return

    config = get_config()
    results_dir = Path(config["RESULTS_DIR"])
    input_cfg = job["input_config"]
    tenants = input_cfg.get("tenants", [])
    template_path = input_cfg.get("template_path")

    selected_ids = input_cfg.get("provisions")
    custom_provisions = input_cfg.get("custom_provisions")
    active_provisions = get_active_provisions(
        selected_ids=selected_ids,
        custom_provisions=custom_provisions,
    )

    any_failed = False

    for i in range(start_index, len(tenants)):
        if is_cancel_requested(job_id):
            for j in range(i, len(tenants)):
                update_tenant_status(job_id, j, "cancelled")
            mark_job_cancelled(job_id)
            save_job_results(job_id)
            return

        tenant = tenants[i]
        tenant_filename = tenant["filename"]
        run_id = f"tenant_{i}"

        update_tenant_status(job_id, i, "processing", stage="analysis")
        logger.info(f"Processing (incremental) {job_id} tenant {i}: {tenant_filename}")

        def _progress_cb(stage, total_stages, detail, _jid=job_id, _idx=i):
            with _jobs_lock:
                j = _jobs.get(_jid)
                if j:
                    t = j["input_config"]["tenants"][_idx]
                    t["current_stage"] = stage
                    t["total_stages"] = total_stages
                    t["stage_detail"] = detail

        try:
            pipeline_config = {
                "output_dir": str(results_dir / job_id),
                "_job_id": job_id,
                "custom_from_scan": input_cfg.get("custom_from_scan", []),
                "added_from_scan": input_cfg.get("added_from_scan", []),
                "template_type": input_cfg.get("template_type", "blank_template"),
                "identity_check": input_cfg.get("identity_check", "landlord_property"),
                "access_code": input_cfg.get("access_code", ""),  # Step 140: for user rules
            }

            result = run_lease_analysis(
                template_path=template_path,
                tenant_path=tenant["upload_path"],
                provisions=active_provisions,
                config=pipeline_config,
                run_id=run_id,
                progress_callback=_progress_cb,
            )

            result_path = str(results_dir / job_id / run_id / "pipeline_results.json")
            annotated_path = None
            output_files = result.get("output_files", {})
            if output_files.get("annotated_document"):
                annotated_path = output_files["annotated_document"]

            update_tenant_status(job_id, i, "completed", stage="done")
            with _jobs_lock:
                t = _jobs[job_id]["input_config"]["tenants"][i]
                t["result_path"] = result_path
                t["annotated_path"] = annotated_path

        except Exception as e:
            from cam.adapters.lease_review.lease_adapter import GateAbortError
            if isinstance(e, GateAbortError):
                update_tenant_status(job_id, i, "failed", error=f"GATE_ABORT: {e.message}")
                any_failed = True
                logger.warning(f"Gate abort (incremental) {job_id} tenant {i}: {e.message}")
                continue

            from cam.adapters.lease_review.lease_adapter import PipelineCancelledError
            if isinstance(e, PipelineCancelledError):
                for j in range(i, len(tenants)):
                    update_tenant_status(job_id, j, "cancelled")
                mark_job_cancelled(job_id)
                save_job_results(job_id)
                return

            error_msg = f"{type(e).__name__}: {e}"
            update_tenant_status(job_id, i, "failed", error=error_msg)
            any_failed = True
            logger.error(f"Failed (incremental) {job_id} tenant {i}: {error_msg}")

    mark_job_completed(job_id)
    save_job_results(job_id)


def start_provision_processing(job_id: str, new_provision_ids: list) -> None:
    """Re-run analysis with new provisions for all tenants in background."""
    mark_job_started(job_id)
    thread = threading.Thread(
        target=_run_provision_processing,
        args=(job_id, new_provision_ids),
        daemon=True,
        name=f"job-{job_id}-prov",
    )
    thread.start()


def _run_provision_processing(job_id: str, new_provision_ids: list) -> None:
    """Run pipeline on new provisions only for each tenant, merge into results."""
    from cam.adapters.lease_review.lease_adapter import run_lease_analysis
    from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions

    job = get_job(job_id)
    if not job:
        return

    config = get_config()
    results_dir = Path(config["RESULTS_DIR"])
    input_cfg = job["input_config"]
    tenants = input_cfg.get("tenants", [])
    template_path = input_cfg.get("template_path")

    new_provisions = get_active_provisions(selected_ids=new_provision_ids)

    for i, tenant in enumerate(tenants):
        if is_cancel_requested(job_id):
            mark_job_cancelled(job_id)
            save_job_results(job_id)
            return

        if tenant.get("status") != "completed":
            continue  # Skip tenants that didn't complete originally

        update_tenant_status(job_id, i, "processing", stage="re-analysis")
        logger.info(f"Processing new provisions for {job_id} tenant {i}")

        def _progress_cb(stage, total_stages, detail, _jid=job_id, _idx=i):
            with _jobs_lock:
                j = _jobs.get(_jid)
                if j:
                    t = j["input_config"]["tenants"][_idx]
                    t["current_stage"] = stage
                    t["total_stages"] = total_stages
                    t["stage_detail"] = f"(new provisions) {detail}"

        try:
            run_id = f"tenant_{i}_addprov"
            pipeline_config = {
                "output_dir": str(results_dir / job_id),
                "_job_id": job_id,
                "access_code": input_cfg.get("access_code", ""),  # Step 140: for user rules
            }

            result = run_lease_analysis(
                template_path=template_path,
                tenant_path=tenant["upload_path"],
                provisions=new_provisions,
                config=pipeline_config,
                run_id=run_id,
                progress_callback=_progress_cb,
            )

            # Merge new provision results into existing results
            new_result_path = str(results_dir / job_id / run_id / "pipeline_results.json")
            existing_result_path = tenant.get("result_path")

            if existing_result_path and Path(existing_result_path).exists():
                existing = json.loads(Path(existing_result_path).read_text(encoding="utf-8"))
                new_data = json.loads(Path(new_result_path).read_text(encoding="utf-8"))

                # Merge provisions
                existing_pids = {p["provision_id"] for p in existing.get("provisions", [])}
                for p in new_data.get("provisions", []):
                    if p["provision_id"] not in existing_pids:
                        existing["provisions"].append(p)

                # Update summary counts
                s = existing.get("summary", {})
                ns = new_data.get("summary", {})
                s["total_provisions_checked"] = len(existing["provisions"])
                s["deviates"] = sum(1 for p in existing["provisions"] if p.get("final_verdict") == "DEVIATES")
                s["conforms"] = sum(1 for p in existing["provisions"] if p.get("final_verdict") == "CONFORMS")
                s["unclear"] = sum(1 for p in existing["provisions"] if p.get("final_verdict") == "UNCLEAR")
                s["critical"] = sum(1 for p in existing["provisions"] if p.get("severity") == "CRITICAL" and p.get("final_verdict") == "DEVIATES")
                s["high"] = sum(1 for p in existing["provisions"] if p.get("severity") == "HIGH" and p.get("final_verdict") == "DEVIATES")
                s["medium"] = sum(1 for p in existing["provisions"] if p.get("severity") == "MEDIUM" and p.get("final_verdict") == "DEVIATES")
                s["low"] = sum(1 for p in existing["provisions"] if p.get("severity") == "LOW" and p.get("final_verdict") == "DEVIATES")
                existing["summary"] = s

                # Write merged results back
                Path(existing_result_path).write_text(
                    json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
                )

            update_tenant_status(job_id, i, "completed", stage="done")

        except Exception as e:
            from cam.adapters.lease_review.lease_adapter import PipelineCancelledError
            if isinstance(e, PipelineCancelledError):
                mark_job_cancelled(job_id)
                save_job_results(job_id)
                return

            error_msg = f"{type(e).__name__}: {e}"
            update_tenant_status(job_id, i, "completed", stage="done")  # Keep original results
            logger.error(f"Failed provision processing {job_id} tenant {i}: {error_msg}")

    mark_job_completed(job_id)
    save_job_results(job_id)


def add_feedback(
    job_id: str,
    tenant_index: int,
    provision_id: str,
    assessment: str,
    notes: str = None,
) -> bool:
    """Append a feedback entry to the job. Returns True if saved."""
    entry = {
        "tenant_index": tenant_index,
        "provision_id": provision_id,
        "assessment": assessment,
        "notes": notes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        job["feedback"].append(entry)

    # Persist feedback to disk
    config = get_config()
    feedback_dir = Path(config["RESULTS_DIR"]) / job_id
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_path = feedback_dir / "feedback.json"

    # Read existing, append, write back
    existing = []
    if feedback_path.exists():
        try:
            existing = json.loads(feedback_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.append(entry)
    feedback_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info(f"Feedback saved: {job_id} tenant={tenant_index} {provision_id}={assessment}")
    return True


# ── Persistence ──

def save_job_results(job_id: str) -> None:
    """Persist job metadata to results/{job_id}/job.json."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job_copy = json.loads(json.dumps(job))  # deep copy

    config = get_config()
    job_dir = Path(config["RESULTS_DIR"]) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    job_path = job_dir / "job.json"
    job_path.write_text(
        json.dumps(job_copy, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Job metadata saved: {job_path}")


def load_persisted_jobs() -> int:
    """On startup, scan results/ dir and reload completed jobs into memory.
    Returns count of jobs loaded."""
    config = get_config()
    results_dir = Path(config["RESULTS_DIR"])
    if not results_dir.exists():
        return 0

    loaded = 0
    for entry in results_dir.iterdir():
        if not entry.is_dir():
            continue
        job_path = entry / "job.json"
        if not job_path.exists():
            continue
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
            job_id = job.get("job_id")
            if job_id:
                with _jobs_lock:
                    _jobs[job_id] = job
                loaded += 1
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning(f"Failed to load persisted job from {job_path}: {e}")

    logger.info(f"Loaded {loaded} persisted job(s) from {results_dir}")
    return loaded


# ── Expiration & Cleanup ──

def is_job_expired(job: dict) -> bool:
    """Check if a job's results have expired.

    Expiry logic: expires_at is set at completion time. Check if past.
    """
    expires_at = job.get("expires_at")
    if expires_at:
        try:
            expiry_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > expiry_dt
        except (ValueError, AttributeError):
            return False

    return False


def _try_delete_dir(dir_path: Path) -> bool:
    """Try deleting individual files first, then the directory.
    Returns True if successful."""
    if not dir_path.exists():
        return True
    # Remove individual files first (sometimes helps release OneDrive directory lock)
    for f in list(dir_path.rglob("*")):
        if f.is_file():
            try:
                os.remove(str(f))
            except OSError:
                pass
    try:
        shutil.rmtree(str(dir_path))
        return True
    except OSError:
        return False


def delete_uploaded_files(job_id: str) -> None:
    """Delete the uploaded source files for a job.
    Handles OneDrive file locks: immediate attempt, then background retries."""
    config = get_config()
    upload_dir = Path(config["UPLOAD_DIR"]) / job_id
    if not upload_dir.exists():
        return

    # Immediate attempt
    if _try_delete_dir(upload_dir):
        logger.info(f"Deleted uploads for job {job_id}")
        return

    # If locked, schedule background retries
    def _retry():
        for delay in [30, 60]:
            time.sleep(delay)
            if _try_delete_dir(upload_dir):
                logger.info(f"Deleted uploads for job {job_id} (after retry)")
                return
        logger.info(f"Upload cleanup deferred for {job_id} (file locked by sync, periodic cleanup will handle)")

    threading.Thread(target=_retry, daemon=True, name=f"upload-cleanup-{job_id}").start()


def cleanup_expired_jobs() -> int:
    """Remove expired jobs from memory and delete their results directories.
    Returns count of jobs cleaned up."""
    config = get_config()
    results_dir = Path(config["RESULTS_DIR"])
    cleaned = 0

    with _jobs_lock:
        expired_ids = [
            jid for jid, job in _jobs.items()
            if job.get("status") in ("completed", "cancelled") and is_job_expired(job)
        ]

    for job_id in expired_ids:
        # Remove from memory
        with _jobs_lock:
            _jobs.pop(job_id, None)

        # Delete results directory
        job_dir = results_dir / job_id
        if job_dir.exists():
            try:
                shutil.rmtree(str(job_dir))
                logger.info(f"Cleaned up expired job: {job_id}")
            except OSError as e:
                logger.warning(f"Failed to cleanup {job_id}: {e}")

        # Delete uploads too (if not already deleted)
        delete_uploaded_files(job_id)
        cleaned += 1

    if cleaned:
        logger.info(f"Expired job cleanup: {cleaned} job(s) removed")
    return cleaned


def delete_job(job_id: str):
    """Delete a job and all associated files (results + uploads)."""
    config = get_config()
    with _jobs_lock:
        job = _jobs.pop(job_id, None)
    if not job:
        return

    # Delete results directory
    results_dir = Path(config["RESULTS_DIR"]) / job_id
    if results_dir.exists():
        shutil.rmtree(str(results_dir), ignore_errors=True)

    # Delete uploads
    upload_dir = Path(config["UPLOAD_DIR"]) / job_id
    if upload_dir.exists():
        shutil.rmtree(str(upload_dir), ignore_errors=True)

    logger.info(f"Job deleted by user: {job_id}")


# ── Background processing ──

def start_processing(job_id: str) -> None:
    """Start processing a job in a background thread."""
    mark_job_started(job_id)
    thread = threading.Thread(
        target=_run_job_processing,
        args=(job_id,),
        daemon=True,
        name=f"job-{job_id}",
    )
    thread.start()


def _run_job_processing(job_id: str) -> None:
    """Top-level processing dispatcher. Routes to domain-specific handler."""
    job = get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found for processing")
        return

    domain = job["domain"]
    if domain == "lease_review":
        _process_lease_job(job_id, job)
    else:
        mark_job_failed(job_id, f"Unknown domain: {domain}")
        save_job_results(job_id)


def _process_lease_job(job_id: str, job: dict) -> None:
    """Process a lease review job — runs each tenant through the pipeline."""
    from cam.adapters.lease_review.lease_adapter import run_lease_analysis
    from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions
    from app.notifications import send_job_complete_email, send_job_failed_email

    config = get_config()
    results_dir = Path(config["RESULTS_DIR"])
    input_cfg = job["input_config"]
    tenants = input_cfg.get("tenants", [])
    template_path = input_cfg.get("template_path")

    # Build provision list
    selected_ids = input_cfg.get("provisions")
    custom_provisions = input_cfg.get("custom_provisions")
    active_provisions = get_active_provisions(
        selected_ids=selected_ids,
        custom_provisions=custom_provisions,
    )

    # Update job status
    with _jobs_lock:
        job_ref = _jobs.get(job_id)
        if job_ref:
            job_ref["status"] = "processing"

    all_failed = True
    any_failed = False
    cancelled = False
    job_error = None

    for i, tenant in enumerate(tenants):
        # ── Check cancel between tenants ──
        if is_cancel_requested(job_id):
            logger.info(f"[job_manager] Job {job_id} cancelled by user after tenant {i - 1}")
            # Mark remaining tenants as cancelled
            for j in range(i, len(tenants)):
                update_tenant_status(job_id, j, "cancelled")
            cancelled = True
            break

        tenant_filename = tenant["filename"]
        tenant_path = tenant["upload_path"]
        run_id = f"tenant_{i}"

        update_tenant_status(job_id, i, "processing", stage="analysis")
        logger.info(f"Processing {job_id} tenant {i}: {tenant_filename}")

        # Progress callback — updates tenant status in real time
        # Also checks cancel between stages
        def _progress_cb(stage, total_stages, detail, _jid=job_id, _idx=i):
            with _jobs_lock:
                j = _jobs.get(_jid)
                if j:
                    t = j["input_config"]["tenants"][_idx]
                    t["current_stage"] = stage
                    t["total_stages"] = total_stages
                    t["stage_detail"] = detail
                    logger.info(f"Progress: {_jid} tenant {_idx} → stage {stage}/{total_stages}: {detail}")

        try:
            # Configure pipeline output to go into job results directory
            pipeline_config = {
                "output_dir": str(results_dir / job_id),
                "_job_id": job_id,  # For cancel checking within pipeline
                "custom_from_scan": input_cfg.get("custom_from_scan", []),
                "added_from_scan": input_cfg.get("added_from_scan", []),
                "template_type": input_cfg.get("template_type", "blank_template"),
                "identity_check": input_cfg.get("identity_check", "landlord_property"),
                "access_code": input_cfg.get("access_code", ""),  # Step 140: for user rules
            }

            result = run_lease_analysis(
                template_path=template_path,
                tenant_path=tenant_path,
                provisions=active_provisions,
                config=pipeline_config,
                run_id=run_id,
                progress_callback=_progress_cb,
            )

            # Store result paths
            result_path = str(results_dir / job_id / run_id / "pipeline_results.json")
            annotated_path = None
            output_files = result.get("output_files", {})
            if output_files.get("annotated_document"):
                annotated_path = output_files["annotated_document"]

            update_tenant_status(job_id, i, "completed", stage="done")
            with _jobs_lock:
                t = _jobs[job_id]["input_config"]["tenants"][i]
                t["result_path"] = result_path
                t["annotated_path"] = annotated_path

            all_failed = False
            logger.info(f"Completed {job_id} tenant {i}: {tenant_filename}")

        except Exception as e:
            # Check gate abort first
            from cam.adapters.lease_review.lease_adapter import GateAbortError
            if isinstance(e, GateAbortError):
                update_tenant_status(job_id, i, "failed", error=f"GATE_ABORT: {e.message}")
                any_failed = True
                job_error = e.message
                logger.warning(f"Gate abort {job_id} tenant {i}: {e.message}")
                continue

            # Check if this is a cancel (PipelineCancelledError)
            from cam.adapters.lease_review.lease_adapter import PipelineCancelledError
            if isinstance(e, PipelineCancelledError):
                logger.info(f"[job_manager] Job {job_id} tenant {i} cancelled mid-pipeline")
                update_tenant_status(job_id, i, "cancelled")
                # Mark remaining tenants as cancelled
                for j in range(i + 1, len(tenants)):
                    update_tenant_status(job_id, j, "cancelled")
                cancelled = True
                break

            error_msg = f"{type(e).__name__}: {e}"
            update_tenant_status(job_id, i, "failed", error=error_msg)
            any_failed = True
            job_error = error_msg
            logger.error(f"Failed {job_id} tenant {i}: {error_msg}")

    # Finalize job
    if cancelled:
        mark_job_cancelled(job_id)
    elif all_failed:
        mark_job_failed(job_id, job_error or "All tenants failed")
    else:
        mark_job_completed(job_id)

    save_job_results(job_id)

    # Send email notification (skip entirely for user-initiated cancels)
    job_url = f"{config['APP_BASE_URL']}/results/{job_id}"
    email = job.get("email")
    if email and not cancelled:
        if job.get("status") == "failed" or all_failed:
            send_job_failed_email(email, job_id, job_error or "Processing failed")
        else:
            # Aggregate summary stats across ALL tenants
            summary = {
                "total_provisions_checked": 0,
                "deviates": 0,
                "conforms": 0,
                "unclear": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
            for t in tenants:
                rp = t.get("result_path")
                if rp and Path(rp).exists():
                    try:
                        r = json.loads(Path(rp).read_text(encoding="utf-8"))
                        s = r.get("summary", {})
                        for key in summary:
                            summary[key] += s.get(key, 0)
                    except (json.JSONDecodeError, OSError):
                        pass

            # Generate attachments
            attachments, att_info = _generate_email_attachments(job_id, tenants, results_dir)
            send_job_complete_email(email, job_id, job_url, summary,
                                   attachments=attachments, attachment_info=att_info)


def _generate_email_attachments(
    job_id: str,
    tenants: list,
    results_dir: Path,
) -> tuple:
    """Generate combined summary PDF and collect annotated docs for email.

    Attachment strategy:
    1. One combined Lease_Analysis_Synopsis.pdf covering all tenants
    2. Per-tenant annotated documents (format matches upload: PDF→PDF, DOCX→DOCX)

    For large batches (>10 tenants), skip individual annotated docs to stay
    under Gmail's 25 MB attachment limit.

    Returns:
        (attachments, info) where info is a dict with:
        - summary_included: bool
        - annotated_tenants: list of filenames with annotated docs
        - unannotated_tenants: list of filenames without annotated docs
    """
    from app.summary_generator import generate_combined_summary_pdf

    attachments = []
    info = {"summary_included": False, "annotated_tenants": [], "unannotated_tenants": []}

    # Reload job to get current state (tenants may have updated result_path)
    job = get_job(job_id)
    if not job:
        return attachments, info
    current_tenants = job.get("input_config", {}).get("tenants", [])

    # Collect pipeline results for all tenants
    tenant_results = []
    for t in current_tenants:
        rp = t.get("result_path")
        if rp and Path(rp).exists():
            try:
                data = json.loads(Path(rp).read_text(encoding="utf-8"))
                tenant_results.append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load results for {t.get('filename')}: {e}")

    # 1. Generate combined summary PDF
    if tenant_results:
        try:
            summary_path = str(results_dir / job_id / "Lease_Analysis_Synopsis.pdf")
            generate_combined_summary_pdf(job, tenant_results, summary_path)
            attachments.append(summary_path)
            info["summary_included"] = True
            logger.info(f"Generated combined summary PDF for email: {summary_path}")
        except Exception as e:
            logger.error(f"Failed to generate combined summary PDF: {e}")

    # 2. Attach per-tenant annotated documents
    for t in current_tenants:
        annotated = t.get("annotated_path")
        fname = t.get("filename", "unknown")
        if annotated and Path(annotated).exists():
            info["annotated_tenants"].append(fname)
            if len(current_tenants) <= 10:
                attachments.append(annotated)
        else:
            info["unannotated_tenants"].append(fname)

    if len(current_tenants) > 10:
        logger.info(f"Skipping individual annotated docs for {len(current_tenants)} tenants (too many for email)")

    return attachments, info


# ── Resolution Workflow ──

def get_resolutions(job_id: str) -> dict:
    """Return the resolutions dict for a job. Keys are '{tenant_idx}:{provision_id}'."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return {}
        return dict(job.get("resolutions", {}))


def set_resolution(
    job_id: str,
    tenant_idx: int,
    provision_id: str,
    status: str = None,
    note: str = None,
    notes: list | None = None,
    concern_state: str | None = None,
    concern_reason: str | None = None,
) -> dict | None:
    """
    Update resolution status and/or append a note for a provision.
    Returns the updated resolution entry, or None if job not found.
    """
    from datetime import datetime, timezone
    key = f"{tenant_idx}:{provision_id}"
    now = datetime.now(timezone.utc).isoformat()

    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if "resolutions" not in job:
            job["resolutions"] = {}
        entry = job["resolutions"].setdefault(key, {
            "status": "open",
            "notes": [],
            "concern_state": "none",
            "concern_reason": "",
            "updated_at": now,
        })
        if status is not None:
            entry["status"] = status
            entry["updated_at"] = now
        if concern_state is not None:
            entry["concern_state"] = str(concern_state or "none").strip() or "none"
            if entry["concern_state"] == "concern":
                entry["concern_reason"] = ""
            elif entry["concern_state"] == "none":
                entry["concern_reason"] = ""
            else:
                entry["concern_reason"] = str(concern_reason or "").strip()
            entry["updated_at"] = now
        if notes is not None:
            normalized_notes = []
            for item in notes:
                if isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                    timestamp = str(item.get("timestamp", now))
                else:
                    text = str(item).strip()
                    timestamp = now
                if text:
                    normalized_notes.append({"text": text, "timestamp": timestamp})
            entry["notes"] = normalized_notes
            entry["updated_at"] = now
        if note and note.strip():
            entry["notes"].append({"text": note.strip(), "timestamp": now})
            entry["updated_at"] = now
        result = dict(entry)

    # Persist
    save_job_results(job_id)
    return result
