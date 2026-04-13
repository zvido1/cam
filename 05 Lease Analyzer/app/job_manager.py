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

from app.config import get_config, APP_VERSION, GIT_SHA

logger = logging.getLogger(__name__)

# ── In-memory job store ──
_jobs: dict = {}
_jobs_lock = threading.Lock()
_job_runtime_meta: dict = {}

PROVISION_FLAG_RATES = {
    "LP-01": 0.26, "LP-02": 0.11, "LP-03": 0.33, "LP-04": 0.09,
    "LP-05": 0.41, "LP-06": 0.27, "LP-07": 0.31, "LP-08": 0.30,
    "LP-09": 0.62, "LP-10": 0.38, "LP-11": 0.60, "LP-12": 0.46,
    "LP-13": 0.60, "LP-14": 0.26, "LP-15": 0.14, "LP-16": 0.32,
    "LP-17": 0.05, "LP-18": 0.22,
}
VARIABLE_COST_PER_FLAGGED = 40
EXTRACTION_BASE_SECS = 180


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _safe_elapsed_seconds(started_at: Optional[str]) -> Optional[float]:
    started = _parse_iso(started_at)
    if not started:
        return None
    return max(0.0, (datetime.now(timezone.utc) - started).total_seconds())


def _job_events_path(job_id: str) -> Path:
    config = get_config()
    job_dir = Path(config["RESULTS_DIR"]) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir / "run_metadata.jsonl"


def _append_job_event(job_id: str, event_type: str, **fields) -> None:
    payload = {
        "timestamp": _utc_now_iso(),
        "job_id": job_id,
        "event_type": event_type,
        **fields,
    }
    path = _job_events_path(job_id)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning(f"Could not write run metadata for {job_id}: {e}")
    logger.info("run_metadata %s", json.dumps(payload, ensure_ascii=False))


def _identity_check_count(input_config: dict) -> int:
    identity_check = input_config.get("identity_check", "landlord_property")
    return {
        "clauses_only": 0,
        "landlord_property": 2,
        "landlord_tenant": 2,
    }.get(identity_check, 2)


def _selected_provision_count(input_config: dict) -> int:
    selected_ids = list(input_config.get("provisions") or [])
    custom_provisions = list(input_config.get("custom_provisions") or [])
    if selected_ids:
        return len(selected_ids) + len(custom_provisions)
    return len(PROVISION_FLAG_RATES) + len(custom_provisions)


def _track_stage_transition(job_id: str, tenant_index: int, stage: int, total_stages: int, detail: str) -> None:
    with _jobs_lock:
        runtime = _job_runtime_meta.setdefault(job_id, {"tenants": {}})
        tenant_rt = runtime["tenants"].setdefault(tenant_index, {})
        previous_stage = tenant_rt.get("last_stage")
        previous_stage_started_at = tenant_rt.get("last_stage_started_at")
        tenant_rt["last_stage"] = stage
        tenant_rt["last_stage_started_at"] = _utc_now_iso()

    stage_changed = previous_stage != stage
    if not stage_changed:
        return

    if previous_stage is not None and previous_stage_started_at:
        _append_job_event(
            job_id,
            "tenant_stage_completed",
            tenant_index=tenant_index,
            stage=previous_stage,
            elapsed_seconds=_safe_elapsed_seconds(previous_stage_started_at),
        )

    _append_job_event(
        job_id,
        "tenant_stage_started",
        tenant_index=tenant_index,
        stage=stage,
        total_stages=total_stages,
        detail=detail,
    )


def _mark_tenant_runtime_start(job_id: str, tenant_index: int) -> str:
    started_at = _utc_now_iso()
    with _jobs_lock:
        runtime = _job_runtime_meta.setdefault(job_id, {"tenants": {}})
        tenant_rt = runtime["tenants"].setdefault(tenant_index, {})
        tenant_rt["processing_started_at"] = started_at
        tenant_rt.pop("last_stage", None)
        tenant_rt.pop("last_stage_started_at", None)
    return started_at


def _finalize_tenant_runtime(job_id: str, tenant_index: int) -> dict:
    with _jobs_lock:
        runtime = _job_runtime_meta.setdefault(job_id, {"tenants": {}})
        tenant_rt = runtime["tenants"].setdefault(tenant_index, {})
        previous_stage = tenant_rt.get("last_stage")
        previous_stage_started_at = tenant_rt.get("last_stage_started_at")
        processing_started_at = tenant_rt.get("processing_started_at")
        tenant_rt.pop("last_stage", None)
        tenant_rt.pop("last_stage_started_at", None)
    if previous_stage is not None and previous_stage_started_at:
        _append_job_event(
            job_id,
            "tenant_stage_completed",
            tenant_index=tenant_index,
            stage=previous_stage,
            elapsed_seconds=_safe_elapsed_seconds(previous_stage_started_at),
        )
    return {
        "processing_started_at": processing_started_at,
        "elapsed_seconds": _safe_elapsed_seconds(processing_started_at),
    }


def _build_job_outcome(job_id: str, tenants: list, started_at: str) -> dict:
    """Build a self-contained outcome summary from result files.

    Reads each tenant's result JSON to produce:
    - Per-tenant outcome rows (severity + governance state counts)
    - Rolled-up job-level totals
    - Run quality marker (clean / degraded / partial)
    - Version metadata
    """
    per_tenant = []
    job_totals = {
        "deviates": 0, "conforms": 0, "unclear": 0,
        "critical": 0, "high": 0, "medium": 0, "low": 0,
        "total_provisions": 0,
        # Governance state counts
        "assert_signal": 0,
        "assert_review_signal": 0,
        "review_signal": 0,
        "withhold_signal": 0,
        # Pipeline quality
        "triage_skipped": 0,       # provisions that skipped challenge (conforms + no rules)
        "fallback_used": 0,        # tenants where any model fallback fired
        "gap_repairs": 0,          # re-extraction repair calls
        "api_calls_total": 0,
    }
    has_any_failure = False
    has_any_fallback = False
    has_any_degraded = False

    for i, t in enumerate(tenants):
        rp = t.get("result_path")
        status = t.get("status", "unknown")

        if status in ("failed", "cancelled"):
            has_any_failure = True
            per_tenant.append({
                "tenant_index": i,
                "filename": t.get("filename", ""),
                "input_type": Path(t.get("filename", "")).suffix.lower().lstrip(".") or "unknown",
                "status": status,
            })
            continue

        if not rp or not Path(rp).exists():
            has_any_degraded = True
            per_tenant.append({
                "tenant_index": i,
                "filename": t.get("filename", ""),
                "input_type": Path(t.get("filename", "")).suffix.lower().lstrip(".") or "unknown",
                "status": "missing_results",
            })
            continue

        try:
            r = json.loads(Path(rp).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            has_any_degraded = True
            per_tenant.append({
                "tenant_index": i,
                "filename": t.get("filename", ""),
                "input_type": Path(t.get("filename", "")).suffix.lower().lstrip(".") or "unknown",
                "status": "unreadable_results",
            })
            continue

        s = r.get("summary", {})
        provisions = r.get("provisions", [])
        models_used = r.get("models_used", {})

        # Governance state counts from individual provisions
        gov_counts = {"ASSERT_SIGNAL": 0, "ASSERT_REVIEW_SIGNAL": 0,
                      "REVIEW_SIGNAL": 0, "WITHHOLD_SIGNAL": 0}
        triage_skipped = 0
        for p in provisions:
            sig = (p.get("cam_score") or {}).get("governance_signal", "")
            if sig in gov_counts:
                gov_counts[sig] += 1
            # Triage gate: conforms + no rules fired = challenge skipped
            meta = p.get("cam_metadata") or {}
            if (p.get("final_verdict") == "CONFORMS"
                    and not meta.get("rules_fired")
                    and 3 not in (meta.get("stages_run") or [])):
                triage_skipped += 1

        fallback_used = any(
            models_used.get(k + "_fallback") for k in ("evaluator_a", "evaluator_b", "evaluator_c")
        )
        if fallback_used:
            has_any_fallback = True

        gap_repairs = r.get("analysis_completeness", {}).get("gaps_resolved_by_reextraction", 0)

        api_calls = r.get("api_calls_total", 0)

        tenant_row = {
            "tenant_index": i,
            "filename": t.get("filename", ""),
            "input_type": Path(t.get("filename", "")).suffix.lower().lstrip(".") or "unknown",
            "status": "completed",
            "deviates": s.get("deviates", 0),
            "conforms": s.get("conforms", 0),
            "unclear": s.get("unclear", 0),
            "critical": s.get("critical", 0),
            "high": s.get("high", 0),
            "medium": s.get("medium", 0),
            "low": s.get("low", 0),
            "total_provisions": s.get("total_provisions_checked", len(provisions)),
            "assert_signal": gov_counts["ASSERT_SIGNAL"],
            "assert_review_signal": gov_counts["ASSERT_REVIEW_SIGNAL"],
            "review_signal": gov_counts["REVIEW_SIGNAL"],
            "withhold_signal": gov_counts["WITHHOLD_SIGNAL"],
            "triage_skipped": triage_skipped,
            "fallback_used": fallback_used,
            "gap_repairs": gap_repairs,
            "api_calls": api_calls,
            "elapsed_seconds": r.get("elapsed_sec"),
        }
        per_tenant.append(tenant_row)

        # Roll up to job totals
        for k in ("deviates", "conforms", "unclear", "critical", "high", "medium", "low"):
            job_totals[k] += s.get(k, 0)
        job_totals["total_provisions"] += s.get("total_provisions_checked", len(provisions))
        job_totals["assert_signal"]        += gov_counts["ASSERT_SIGNAL"]
        job_totals["assert_review_signal"] += gov_counts["ASSERT_REVIEW_SIGNAL"]
        job_totals["review_signal"]        += gov_counts["REVIEW_SIGNAL"]
        job_totals["withhold_signal"]      += gov_counts["WITHHOLD_SIGNAL"]
        job_totals["triage_skipped"]       += triage_skipped
        job_totals["fallback_used"]        += int(fallback_used)
        job_totals["gap_repairs"]          += gap_repairs
        job_totals["api_calls_total"]      += api_calls

    # Run quality marker
    completed_count = sum(1 for t in per_tenant if t.get("status") == "completed")
    total_count = len(tenants)
    if has_any_failure or completed_count < total_count:
        run_quality = "partial"
    elif has_any_degraded or has_any_fallback:
        run_quality = "degraded"
    else:
        run_quality = "clean"

    return {
        "tenant_count": total_count,
        "completed_count": completed_count,
        "run_quality": run_quality,
        "totals": job_totals,
        "per_tenant": per_tenant,
        "elapsed_seconds": _safe_elapsed_seconds(started_at),
        "app_version": APP_VERSION,
        "git_sha": GIT_SHA,
    }


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

    gap_repair_buffer = 300 if prov_count >= 12 else 180
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
    _append_job_event(
        job_id,
        "job_created",
        domain=domain,
        tenant_count=num_tenants,
        estimated_minutes=estimated_minutes,
        selected_provision_count=_selected_provision_count(input_config),
        identity_check_count=_identity_check_count(input_config),
        identity_check_mode=input_config.get("identity_check", "landlord_property"),
    )
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
    estimated_minutes = None
    tenant_count = 0
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        job["status"] = "processing"
        job["started_at"] = started_at
        job["completed_at"] = None
        job.pop("cancelled_at", None)
        job.pop("expires_at", None)
        estimated_minutes = job.get("estimated_minutes")
        tenant_count = len(job.get("input_config", {}).get("tenants", []) or [])
        _job_runtime_meta[job_id] = {"started_at": started_at, "tenants": {}}
    _append_job_event(
        job_id,
        "job_started",
        started_at=started_at,
        estimated_minutes=estimated_minutes,
        tenant_count=tenant_count,
    )
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
        _job_runtime_meta.pop(job_id, None)
    logger.info(f"Job completed: {job_id} (expires at {expires_at.isoformat()})")
    started_at = get_job(job_id).get("started_at") if get_job(job_id) else None
    _append_job_event(
        job_id,
        "job_completed",
        completed_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        elapsed_seconds=_safe_elapsed_seconds(started_at),
    )


def mark_job_failed(job_id: str, error: str) -> None:
    """Set job status to failed with error message."""
    completed_at = datetime.now(timezone.utc).isoformat()
    started_at = None
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["status"] = "failed"
            job["completed_at"] = completed_at
            job["error"] = error
            started_at = job.get("started_at")
        _job_runtime_meta.pop(job_id, None)
    logger.error(f"Job failed: {job_id} — {error}")


    _append_job_event(
        job_id,
        "job_failed",
        completed_at=completed_at,
        elapsed_seconds=_safe_elapsed_seconds(started_at),
        error=error,
    )


def request_cancel(job_id: str) -> None:
    """Set the cancel_requested flag on a processing job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["cancel_requested"] = True
    logger.info(f"Cancel requested: {job_id}")
    _append_job_event(job_id, "job_cancel_requested")


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
        _job_runtime_meta.pop(job_id, None)
    logger.info(f"Job cancelled: {job_id}")
    started_at = get_job(job_id).get("started_at") if get_job(job_id) else None
    _append_job_event(
        job_id,
        "job_cancelled",
        cancelled_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        elapsed_seconds=_safe_elapsed_seconds(started_at),
    )


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
    _append_job_event(
        job_id,
        "tenants_appended",
        appended_tenant_count=len(new_tenants),
        total_tenant_count=len(get_job(job_id).get("input_config", {}).get("tenants", []) or []),
    )


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
    _append_job_event(
        job_id,
        "provisions_appended",
        appended_provision_count=len(new_provision_ids),
        appended_provisions=new_provision_ids,
    )


def start_incremental_processing(job_id: str, start_index: int) -> None:
    """Process only new tenants (from start_index onward) in a background thread."""
    mark_job_started(job_id)
    _append_job_event(job_id, "incremental_processing_started", start_index=start_index)
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
        _mark_tenant_runtime_start(job_id, i)
        _append_job_event(
            job_id,
            "tenant_started",
            tenant_index=i,
            tenant_filename=tenant_filename,
            run_id=run_id,
            mode="incremental_tenant",
        )

        def _progress_cb(stage, total_stages, detail, _jid=job_id, _idx=i):
            with _jobs_lock:
                j = _jobs.get(_jid)
                if j:
                    t = j["input_config"]["tenants"][_idx]
                    t["current_stage"] = stage
                    t["total_stages"] = total_stages
                    t["stage_detail"] = detail
            _track_stage_transition(_jid, _idx, stage, total_stages, detail)

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
            timing = _finalize_tenant_runtime(job_id, i)
            _append_job_event(
                job_id,
                "tenant_completed",
                tenant_index=i,
                tenant_filename=tenant_filename,
                run_id=run_id,
                mode="incremental_tenant",
                elapsed_seconds=timing["elapsed_seconds"],
            )

        except Exception as e:
            from cam.adapters.lease_review.lease_adapter import GateAbortError
            if isinstance(e, GateAbortError):
                update_tenant_status(job_id, i, "failed", error=f"GATE_ABORT: {e.message}")
                any_failed = True
                logger.warning(f"Gate abort (incremental) {job_id} tenant {i}: {e.message}")
                timing = _finalize_tenant_runtime(job_id, i)
                _append_job_event(
                    job_id,
                    "tenant_failed",
                    tenant_index=i,
                    tenant_filename=tenant_filename,
                    run_id=run_id,
                    mode="incremental_tenant",
                    failure_type="gate_abort",
                    error=e.message,
                    elapsed_seconds=timing["elapsed_seconds"],
                )
                continue

            from cam.adapters.lease_review.lease_adapter import PipelineCancelledError
            if isinstance(e, PipelineCancelledError):
                timing = _finalize_tenant_runtime(job_id, i)
                _append_job_event(
                    job_id,
                    "tenant_cancelled",
                    tenant_index=i,
                    tenant_filename=tenant_filename,
                    run_id=run_id,
                    mode="incremental_tenant",
                    elapsed_seconds=timing["elapsed_seconds"],
                )
                for j in range(i, len(tenants)):
                    update_tenant_status(job_id, j, "cancelled")
                mark_job_cancelled(job_id)
                save_job_results(job_id)
                return

            error_msg = f"{type(e).__name__}: {e}"
            update_tenant_status(job_id, i, "failed", error=error_msg)
            any_failed = True
            logger.error(f"Failed (incremental) {job_id} tenant {i}: {error_msg}")
            timing = _finalize_tenant_runtime(job_id, i)
            _append_job_event(
                job_id,
                "tenant_failed",
                tenant_index=i,
                tenant_filename=tenant_filename,
                run_id=run_id,
                mode="incremental_tenant",
                failure_type=type(e).__name__,
                error=error_msg,
                elapsed_seconds=timing["elapsed_seconds"],
            )

    mark_job_completed(job_id)
    save_job_results(job_id)


def start_provision_processing(job_id: str, new_provision_ids: list) -> None:
    """Re-run analysis with new provisions for all tenants in background."""
    mark_job_started(job_id)
    _append_job_event(
        job_id,
        "provision_processing_started",
        new_provision_count=len(new_provision_ids),
        new_provisions=new_provision_ids,
    )
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
        tenant_filename = tenant["filename"]
        _mark_tenant_runtime_start(job_id, i)
        _append_job_event(
            job_id,
            "tenant_started",
            tenant_index=i,
            tenant_filename=tenant_filename,
            run_id=f"tenant_{i}_addprov",
            mode="provision_processing",
            new_provision_count=len(new_provision_ids),
        )

        def _progress_cb(stage, total_stages, detail, _jid=job_id, _idx=i):
            with _jobs_lock:
                j = _jobs.get(_jid)
                if j:
                    t = j["input_config"]["tenants"][_idx]
                    t["current_stage"] = stage
                    t["total_stages"] = total_stages
                    t["stage_detail"] = f"(new provisions) {detail}"
            _track_stage_transition(_jid, _idx, stage, total_stages, f"(new provisions) {detail}")

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
            timing = _finalize_tenant_runtime(job_id, i)
            _append_job_event(
                job_id,
                "tenant_completed",
                tenant_index=i,
                tenant_filename=tenant_filename,
                run_id=run_id,
                mode="provision_processing",
                new_provision_count=len(new_provision_ids),
                elapsed_seconds=timing["elapsed_seconds"],
            )

        except Exception as e:
            from cam.adapters.lease_review.lease_adapter import PipelineCancelledError
            if isinstance(e, PipelineCancelledError):
                timing = _finalize_tenant_runtime(job_id, i)
                _append_job_event(
                    job_id,
                    "tenant_cancelled",
                    tenant_index=i,
                    tenant_filename=tenant_filename,
                    run_id=f"tenant_{i}_addprov",
                    mode="provision_processing",
                    new_provision_count=len(new_provision_ids),
                    elapsed_seconds=timing["elapsed_seconds"],
                )
                mark_job_cancelled(job_id)
                save_job_results(job_id)
                return

            error_msg = f"{type(e).__name__}: {e}"
            update_tenant_status(job_id, i, "completed", stage="done")  # Keep original results
            logger.error(f"Failed provision processing {job_id} tenant {i}: {error_msg}")
            timing = _finalize_tenant_runtime(job_id, i)
            _append_job_event(
                job_id,
                "tenant_failed",
                tenant_index=i,
                tenant_filename=tenant_filename,
                run_id=f"tenant_{i}_addprov",
                mode="provision_processing",
                new_provision_count=len(new_provision_ids),
                failure_type=type(e).__name__,
                error=error_msg,
                elapsed_seconds=timing["elapsed_seconds"],
            )

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



# ── Coverage Resolution Workflow ──

def get_cov_resolutions(job_id: str) -> dict:
    """Return the coverage resolutions dict. Keys are 'cov:{tenant_idx}:{provision_id}'."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return {}
        return dict(job.get("cov_resolutions", {}))


def set_cov_resolution(
    job_id: str,
    tenant_idx: int,
    provision_id: str,
    status: str,
) -> dict | None:
    """
    Set coverage workflow status for a provision.
    status: 'open' | 'reviewed' | 'flagged' | 'accepted'
    Returns the updated entry, or None if job not found.
    """
    from datetime import datetime, timezone
    key = f"cov:{tenant_idx}:{provision_id}"
    now = datetime.now(timezone.utc).isoformat()

    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if "cov_resolutions" not in job:
            job["cov_resolutions"] = {}
        entry = job["cov_resolutions"].setdefault(key, {
            "status": "open",
            "updated_at": now,
        })
        entry["status"] = status
        entry["updated_at"] = now
        result = dict(entry)

    save_job_results(job_id)
    return result


# ── Background processing ──

def start_processing(job_id: str) -> None:
    """Start processing a job in a background thread."""
    mark_job_started(job_id)
    _append_job_event(job_id, "full_processing_started")
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
        _mark_tenant_runtime_start(job_id, i)
        _append_job_event(
            job_id,
            "tenant_started",
            tenant_index=i,
            tenant_filename=tenant_filename,
            run_id=run_id,
            mode="full_processing",
        )

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

            def _progress_cb_with_tracking(stage, total_stages, detail):
                _progress_cb(stage, total_stages, detail)
                _track_stage_transition(job_id, i, stage, total_stages, detail)

            result = run_lease_analysis(
                template_path=template_path,
                tenant_path=tenant_path,
                provisions=active_provisions,
                config=pipeline_config,
                run_id=run_id,
                progress_callback=_progress_cb_with_tracking,
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
            timing = _finalize_tenant_runtime(job_id, i)
            _append_job_event(
                job_id,
                "tenant_completed",
                tenant_index=i,
                tenant_filename=tenant_filename,
                run_id=run_id,
                mode="full_processing",
                elapsed_seconds=timing["elapsed_seconds"],
            )

        except Exception as e:
            # Check gate abort first
            from cam.adapters.lease_review.lease_adapter import GateAbortError
            if isinstance(e, GateAbortError):
                update_tenant_status(job_id, i, "failed", error=f"GATE_ABORT: {e.message}")
                any_failed = True
                job_error = e.message
                logger.warning(f"Gate abort {job_id} tenant {i}: {e.message}")
                timing = _finalize_tenant_runtime(job_id, i)
                _append_job_event(
                    job_id,
                    "tenant_failed",
                    tenant_index=i,
                    tenant_filename=tenant_filename,
                    run_id=run_id,
                    mode="full_processing",
                    failure_type="gate_abort",
                    error=e.message,
                    elapsed_seconds=timing["elapsed_seconds"],
                )
                continue

            # Check if this is a cancel (PipelineCancelledError)
            from cam.adapters.lease_review.lease_adapter import PipelineCancelledError
            if isinstance(e, PipelineCancelledError):
                logger.info(f"[job_manager] Job {job_id} tenant {i} cancelled mid-pipeline")
                update_tenant_status(job_id, i, "cancelled")
                timing = _finalize_tenant_runtime(job_id, i)
                _append_job_event(
                    job_id,
                    "tenant_cancelled",
                    tenant_index=i,
                    tenant_filename=tenant_filename,
                    run_id=run_id,
                    mode="full_processing",
                    elapsed_seconds=timing["elapsed_seconds"],
                )
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
            timing = _finalize_tenant_runtime(job_id, i)
            _append_job_event(
                job_id,
                "tenant_failed",
                tenant_index=i,
                tenant_filename=tenant_filename,
                run_id=run_id,
                mode="full_processing",
                failure_type=type(e).__name__,
                error=error_msg,
                elapsed_seconds=timing["elapsed_seconds"],
            )

    # Finalize job
    if cancelled:
        mark_job_cancelled(job_id)
    elif all_failed:
        mark_job_failed(job_id, job_error or "All tenants failed")
    else:
        # Emit self-contained outcome event before completing
        # (result files still exist; mark_job_completed starts expiry clock)
        try:
            outcome = _build_job_outcome(job_id, tenants, job.get("started_at"))
            _append_job_event(job_id, "job_outcome", **outcome)
        except Exception as _oe:
            logger.warning(f"Could not build job outcome event: {_oe}")
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
            tenant_filenames = [t.get("filename", "") for t in tenants if t.get("filename")]
            send_job_complete_email(email, job_id, job_url, summary,
                                   attachments=attachments, attachment_info=att_info,
                                   tenant_names=tenant_filenames)


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


# ── Feedback ──

def add_feedback(
    job_id: str,
    tenant_index: int,
    provision_id: str,
    assessment: str,
    notes: str = None,
) -> bool:
    """Append user feedback (agree/disagree/unsure) for a provision finding.

    Stores in job['feedback'] list and logs a run_metadata event so it
    survives in Railway logs even after job expiry.
    """
    now = _utc_now_iso()
    entry = {
        "tenant_index": tenant_index,
        "provision_id": provision_id,
        "assessment": assessment,  # agree | disagree | unsure
        "notes": notes,
        "timestamp": now,
    }
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return False
        if "feedback" not in job:
            job["feedback"] = []
        # Overwrite existing entry for same tenant+provision (last click wins)
        job["feedback"] = [
            f for f in job["feedback"]
            if not (f.get("tenant_index") == tenant_index
                    and f.get("provision_id") == provision_id)
        ]
        job["feedback"].append(entry)

    # Log to Railway-persistent telemetry stream
    _append_job_event(
        job_id,
        "user_feedback",
        tenant_index=tenant_index,
        provision_id=provision_id,
        assessment=assessment,
    )

    save_job_results(job_id)
    return True


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
