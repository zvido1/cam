"""
CAM Lease Analyzer Web App — FastAPI Application

Domain-agnostic routes + lease-specific routes, static file serving, CORS.
"""

import hashlib
import json
import logging
import os
import shutil
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.staticfiles import NotModifiedResponse
from starlette.responses import Response

# config.py sets up sys.path for cam imports
from app.config import get_config, email_configured, LEASE_DIR
from app import job_manager

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── CAM Knowledge Base — loaded once at startup, injected into all chat prompts ──
_KNOWLEDGE_PATH = Path(__file__).parent / "cam_knowledge.txt"
CAM_KNOWLEDGE = _KNOWLEDGE_PATH.read_text(encoding="utf-8") if _KNOWLEDGE_PATH.exists() else ""

# ── FastAPI app ──
app = FastAPI(
    title="CAM Lease Analyzer",
    description="Commercial lease deviation analysis powered by CAM",
    version="0.1.0",
)

# ── CORS (open for MVP) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ──

@app.on_event("startup")
def startup():
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}", flush=True)
    print(f"  CAM LEASE ANALYZER — SERVER STARTED", flush=True)
    print(f"  {now}", flush=True)
    print(f"{'='*60}\n", flush=True)

    config = get_config()

    # Load API keys for pipeline
    from cam.core.config import find_and_load_env
    find_and_load_env()

    # Ensure directories exist
    Path(config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(config["RESULTS_DIR"]).mkdir(parents=True, exist_ok=True)

    # Load any persisted completed jobs
    loaded = job_manager.load_persisted_jobs()
    logger.info(f"Startup: {loaded} persisted job(s) loaded")

    # Clean up any expired jobs from previous runs
    cleaned = job_manager.cleanup_expired_jobs()
    if cleaned:
        logger.info(f"Startup cleanup: removed {cleaned} expired job(s)")

    # Start periodic cleanup thread (every 30 minutes)
    def _periodic_cleanup():
        while True:
            time.sleep(1800)
            try:
                job_manager.cleanup_expired_jobs()
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")

    cleanup_thread = threading.Thread(target=_periodic_cleanup, daemon=True, name="job-cleanup")
    cleanup_thread.start()
    expiry_min = config.get('JOB_EXPIRY_MINUTES', 1440)
    expiry_display = f"{expiry_min // 60}h" if expiry_min >= 60 else f"{expiry_min}min"
    logger.info(f"Job expiry: {expiry_display} from completion, cleanup every 30 min")

    # Log email status
    if email_configured(config):
        logger.info("Email notifications: CONFIGURED")
    else:
        logger.info(
            "Email notifications: NOT CONFIGURED. "
            "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD env vars. See .env.example."
        )

    # Validate access code
    if not config["ACCESS_CODE"]:
        logger.warning("ACCESS_CODE not set — access gate disabled")
    else:
        logger.info(f"Access code: configured ({len(config['ACCESS_CODE'])} chars)")


# ── Static files — no-cache for JS/CSS so version bumps take effect immediately ──
static_dir = LEASE_DIR / "static"
if static_dir.exists():
    class NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if path.endswith(('.js', '.css')):
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            return response
    app.mount("/static", NoCacheStaticFiles(directory=str(static_dir)), name="static")


# ══════════════════════════════════════════════════════════════════════════════
# GENERIC ROUTES (domain-agnostic — work for any CAM adapter)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def serve_index():
    """Serve the frontend index.html."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(
            str(index_path),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return JSONResponse({"message": "CAM Lease Analyzer — frontend not yet built"})


@app.post("/api/auth/verify")
def verify_access_code(body: dict):
    """Verify the shared access code."""
    config = get_config()
    submitted = body.get("access_code", "")

    if not config["ACCESS_CODE"]:
        # No access code configured — allow all
        return {"valid": True}

    if submitted == config["ACCESS_CODE"]:
        return {"valid": True}

    raise HTTPException(status_code=401, detail="Invalid access code")


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    """Return job status dict. Returns 410 Gone if expired.
    Uses get_job_snapshot() for thread-safe serialization — the live
    job dict is mutated by background threads during processing."""
    job = job_manager.get_job_snapshot(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check expiration
    if job.get("status") == "completed" and job_manager.is_job_expired(job):
        job_manager.cleanup_expired_jobs()
        return JSONResponse(
            status_code=410,
            content={"detail": "This analysis has expired. Results are no longer available."},
        )

    # Prevent browser from caching poll responses
    return JSONResponse(
        content=json.loads(json.dumps(job, default=str)),
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """Request cancellation of a running job.

    Only valid when job status is 'processing'. The pipeline will stop
    between stages/tenants. Any completed tenant results are preserved.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "processing":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.get('status')}'. Only 'processing' jobs can be cancelled.",
        )

    job_manager.request_cancel(job_id)
    return {"status": "cancel_requested"}


@app.patch("/api/jobs/{job_id}/email")
async def update_job_email(job_id: str, body: dict):
    """Update the notification email for a running or completed job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    email = body.get("email", "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email address required")

    with job_manager._jobs_lock:
        if job_id in job_manager._jobs:
            job_manager._jobs[job_id]["email"] = email

    job_manager.save_job_results(job_id)
    return {"ok": True, "email": email}


@app.get("/api/jobs/{job_id}/results")
def get_job_results(job_id: str):
    """Return full results JSON for all tenants. 404 if not complete/cancelled. 410 if expired."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check expiration
    if job.get("status") == "completed" and job_manager.is_job_expired(job):
        job_manager.cleanup_expired_jobs()
        return JSONResponse(
            status_code=410,
            content={"detail": "This analysis has expired. Results are no longer available."},
        )

    if job["status"] not in ("completed", "cancelled"):
        raise HTTPException(status_code=404, detail="Job not yet complete")

    tenants = job.get("input_config", {}).get("tenants", [])
    results = []
    for i, tenant in enumerate(tenants):
        result_path = tenant.get("result_path")
        if result_path and Path(result_path).exists():
            try:
                data = json.loads(Path(result_path).read_text(encoding="utf-8"))
                annotated = tenant.get("annotated_path")
                results.append({
                    "tenant_index": i,
                    "filename": tenant["filename"],
                    "status": tenant["status"],
                    "results": data,
                    "has_annotated": bool(annotated and Path(annotated).exists()),
                })
            except (json.JSONDecodeError, OSError) as e:
                results.append({
                    "tenant_index": i,
                    "filename": tenant["filename"],
                    "status": "error",
                    "error": str(e),
                })
        else:
            results.append({
                "tenant_index": i,
                "filename": tenant["filename"],
                "status": tenant.get("status", "unknown"),
                "error": tenant.get("error"),
            })

    return {"job_id": job_id, "tenants": results}


@app.get("/api/jobs")
def list_jobs(email: Optional[str] = None):
    """List all jobs, optionally filtered by email."""
    return job_manager.list_jobs(email=email)


@app.post("/api/jobs/{job_id}/feedback")
def submit_feedback(job_id: str, body: dict):
    """Append feedback for a specific finding."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tenant_index = body.get("tenant_index")
    provision_id = body.get("provision_id")
    assessment = body.get("assessment")

    if tenant_index is None or not provision_id or not assessment:
        raise HTTPException(
            status_code=400,
            detail="Required fields: tenant_index, provision_id, assessment",
        )

    if assessment not in ("agree", "disagree", "unsure"):
        raise HTTPException(
            status_code=400,
            detail="assessment must be 'agree', 'disagree', or 'unsure'",
        )

    saved = job_manager.add_feedback(
        job_id=job_id,
        tenant_index=tenant_index,
        provision_id=provision_id,
        assessment=assessment,
        notes=body.get("notes"),
    )

    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save feedback")

    return {"saved": True}


# ══════════════════════════════════════════════════════════════════════════════
# RESOLUTION WORKFLOW (079)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/jobs/{job_id}/resolutions")
def get_resolutions(job_id: str):
    """Return all resolution states for a job."""
    resolutions = job_manager.get_resolutions(job_id)
    return {"ok": True, "resolutions": resolutions}


@app.post("/api/jobs/{job_id}/resolution")
async def update_resolution(job_id: str, request: Request):
    """Set resolution status and/or append a note for one provision."""
    body = await request.json()
    tenant_idx = body.get("tenant_idx")
    provision_id = body.get("provision_id")
    status = body.get("status")          # optional
    note = body.get("note")              # optional
    notes = body.get("notes")            # optional full note list

    if tenant_idx is None or not provision_id:
        raise HTTPException(status_code=400, detail="tenant_idx and provision_id required")

    result = job_manager.set_resolution(job_id, int(tenant_idx), provision_id, status, note, notes)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "resolution": result}


# ══════════════════════════════════════════════════════════════════════════════
# PRE-SCAN ENDPOINTS (050)
# ══════════════════════════════════════════════════════════════════════════════

# ── Prescan endpoints removed in step 112 (discovery moved into pipeline) ──
# @app.post("/api/prescan/template")
# Prescan replaced by in-pipeline discovery during Stage 2 evaluation.


# @app.post("/api/prescan/tenants")
# Prescan replaced by in-pipeline discovery during Stage 2 evaluation.



# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE SUMMARY ENDPOINT (Step 138)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/template/summary")
async def get_template_summary(
    template_file: UploadFile = File(...),
    access_code: str = Form(""),
):
    """Read a template file, run gate check, extract summary fields."""
    from cam.adapters.lease_review.lease_parser import parse_document
    from cam.adapters.lease_review.lease_gate import check_document_is_lease
    from cam.adapters.lease_review.lease_template_reader import read_template_summary
    from cam.core.config import find_and_load_env
    import tempfile

    find_and_load_env()
    config = get_config()

    # Validate access code if configured
    if config["ACCESS_CODE"] and access_code != config["ACCESS_CODE"]:
        raise HTTPException(status_code=401, detail="Invalid access code")

    # Save to temp file for parsing
    suffix = Path(template_file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await template_file.read())
        tmp_path = tmp.name

    try:
        text = parse_document(tmp_path)

        # Gate check
        gate = check_document_is_lease(text, {})
        if not gate["is_lease"]:
            return {
                "gate_passed": False,
                "gate_message": gate["abort_message"],
                "landlord": "", "property": "",
                "base_rent": "", "lease_term": "", "governing_law": ""
            }

        # Extract summary
        summary = read_template_summary(text)
        summary["gate_passed"] = True
        summary["gate_message"] = ""
        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read template: {e}")
    finally:
        os.unlink(tmp_path)


# ══════════════════════════════════════════════════════════════════════════════
# USER RULES ENDPOINTS (Step 140)
# ══════════════════════════════════════════════════════════════════════════════

def _get_user_rules_path() -> Path:
    """Path to the user rules JSON file."""
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "user_rules.json"


def _verify_access(access_code: str):
    """Verify access code or raise 401."""
    config = get_config()
    if not config["ACCESS_CODE"]:
        return  # No code configured — allow all
    if access_code == config["ACCESS_CODE"]:
        return
    raise HTTPException(status_code=401, detail="Invalid access code")


def _load_user_rules(access_code: str) -> list:
    """Load rules for a given access code. Returns list."""
    code_hash = hashlib.sha256(access_code.encode()).hexdigest()
    path = _get_user_rules_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get(code_hash, [])
    except Exception:
        return []


def _save_user_rules(access_code: str, rules: list) -> None:
    """Save rules for a given access code."""
    code_hash = hashlib.sha256(access_code.encode()).hexdigest()
    path = _get_user_rules_path()
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        data = {}
    data[code_hash] = rules
    path.write_text(json.dumps(data, indent=2))


@app.get("/api/rules")
async def get_rules(access_code: str = Query(...)):
    """Get all user rules for this access code."""
    _verify_access(access_code)
    rules = _load_user_rules(access_code)
    return {"rules": rules}


@app.post("/api/rules")
async def add_rule(request: Request):
    """Add a new user rule."""
    body = await request.json()
    access_code = body.get("access_code", "")
    rule_text = (body.get("text") or "").strip()
    provision_hint = body.get("provision_hint", "")

    _verify_access(access_code)
    if not rule_text:
        raise HTTPException(status_code=400, detail="Rule text is required")
    if len(rule_text) > 500:
        raise HTTPException(status_code=400, detail="Rule text too long (max 500 chars)")

    rules = _load_user_rules(access_code)
    if len(rules) >= 20:
        raise HTTPException(status_code=400, detail="Maximum 20 rules allowed")

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rule_id = f"rule_{now[:10].replace('-','')}_{len(rules)+1:03d}"
    new_rule = {
        "id": rule_id,
        "text": rule_text,
        "provision_hint": provision_hint,
        "created_at": now,
        "enabled": True,
    }
    rules.append(new_rule)
    _save_user_rules(access_code, rules)
    return {"rule": new_rule}


@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: str, access_code: str = Query(...)):
    """Delete a user rule by ID."""
    _verify_access(access_code)
    rules = _load_user_rules(access_code)
    rules = [r for r in rules if r["id"] != rule_id]
    _save_user_rules(access_code, rules)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# AI SUMMARY ENDPOINT (048)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/ai-summary")
async def ai_summary(request_body: dict):
    """Generate AI summary paragraph for results dashboard."""
    prompt = request_body.get("prompt", "")
    if not prompt:
        return {"summary": ""}

    try:
        from cam.adapters.lease_review.lease_prescan import _call_gemini_sync
        import asyncio
        text = await asyncio.to_thread(_call_gemini_sync, prompt)
        return {"summary": text}
    except Exception as e:
        logger.error(f"AI summary error: {e}")
        return {"summary": ""}


# ══════════════════════════════════════════════════════════════════════════════
# FINAL DRAFT ENDPOINT (144)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/final-draft")
async def final_draft(request_body: dict):
    """Generate a Final Draft DOCX from per-provision decisions."""
    import io
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    job_id = request_body.get("job_id", "")
    decisions = request_body.get("decisions", {})  # {pid: {choice, text, provision_name, final_verdict, severity}}

    doc = Document()

    # Title
    title = doc.add_heading("Final Draft — Negotiated Lease Terms", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Subtitle
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(f"Generated {datetime.now().strftime('%B %d, %Y')}  \u00b7  CAM\u2122 Patent Pending")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

    doc.add_paragraph()  # spacer

    # Summary
    kept_template = [pid for pid, d in decisions.items() if d.get("choice") == "template"]
    kept_tenant   = [pid for pid, d in decisions.items() if d.get("choice") == "tenant" and d.get("final_verdict") == "DEVIATES"]
    custom        = [pid for pid, d in decisions.items() if d.get("choice") == "custom"]
    conforms      = [pid for pid, d in decisions.items() if d.get("final_verdict") == "CONFORMS"]

    summary_lines = [
        f"Provisions restored to template: {len(kept_template)}",
        f"Tenant language accepted: {len(kept_tenant)}",
        f"Custom compromise language: {len(custom)}",
        f"Conforming (no change): {len(conforms)}",
    ]
    for line in summary_lines:
        doc.add_paragraph(line)

    doc.add_page_break()

    # ── Per-provision sections ──
    SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    # Sort: DEVIATES first (by severity), then CONFORMS
    def sort_key(item):
        pid, d = item
        if d.get("final_verdict") == "CONFORMS":
            return (99, pid)
        sev = d.get("severity", "")
        idx = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else 10
        return (idx, pid)

    sorted_decisions = sorted(decisions.items(), key=sort_key)

    for pid, d in sorted_decisions:
        choice = d.get("choice", "tenant")
        pname = d.get("provision_name", pid)
        verdict = d.get("final_verdict", "")
        severity = d.get("severity", "")
        text = d.get("text", "").strip()

        # Section heading
        heading_text = f"{pid}  {pname}"
        if severity:
            heading_text += f"  \u2014  {severity}"
        doc.add_heading(heading_text, level=2)

        # Decision badge
        badge_map = {
            "template": "\u2713 Restored to standard template",
            "tenant":   "\u2192 Tenant language accepted" if verdict == "DEVIATES" else "\u2713 Conforms \u2014 no change",
            "custom":   "\u26a1 Custom compromise language",
        }
        badge_text = badge_map.get(choice, "")
        badge_para = doc.add_paragraph()
        badge_run = badge_para.add_run(badge_text)
        badge_run.font.size = Pt(9)
        if choice == "template":
            badge_run.font.color.rgb = RGBColor(0x16, 0xa3, 0x4a)
        elif choice == "custom":
            badge_run.font.color.rgb = RGBColor(0x7c, 0x3a, 0xed)
        else:
            badge_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)

        # Clause text
        if text:
            clause_para = doc.add_paragraph(text)
            clause_para.style = "Normal"
        else:
            doc.add_paragraph("(No clause text recorded)")

        doc.add_paragraph()  # spacer

    # Disclaimer
    doc.add_page_break()
    disc = doc.add_paragraph(
        "Generated by CAM\u2122 \u00b7 Patent Pending \u00b7 "
        "This document is a drafting aid and does not constitute legal advice. "
        "All provisions should be reviewed by qualified legal counsel before execution."
    )
    disc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in disc.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    # Return as file download
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    from fastapi.responses import StreamingResponse
    filename = f"final_draft_{job_id or 'lease'}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/final-draft")
async def final_draft(request_body: dict):
    """Generate a Final Draft DOCX from per-provision decisions."""
    import io
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from datetime import datetime
    from fastapi.responses import StreamingResponse

    job_id = request_body.get("job_id", "")
    decisions = request_body.get("decisions", {})

    doc = Document()

    # Title
    title = doc.add_heading("Final Draft \u2014 Negotiated Lease Terms", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(f"Generated {datetime.now().strftime('%B %d, %Y')}  \u00b7  CAM\u2122 Patent Pending")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x64, 0x74, 0x8b)
    doc.add_paragraph()

    # Summary counts
    kept_template = [pid for pid, d in decisions.items() if d.get("choice") == "template"]
    kept_tenant   = [pid for pid, d in decisions.items() if d.get("choice") == "tenant" and d.get("final_verdict") == "DEVIATES"]
    custom        = [pid for pid, d in decisions.items() if d.get("choice") == "custom"]
    conforms      = [pid for pid, d in decisions.items() if d.get("final_verdict") == "CONFORMS"]

    for line in [
        f"Provisions restored to template: {len(kept_template)}",
        f"Tenant language accepted: {len(kept_tenant)}",
        f"Custom compromise language: {len(custom)}",
        f"Conforming (no change): {len(conforms)}",
    ]:
        doc.add_paragraph(line)

    doc.add_page_break()

    SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

    def sort_key(item):
        pid, d = item
        if d.get("final_verdict") == "CONFORMS":
            return (99, pid)
        sev = d.get("severity", "")
        idx = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else 10
        return (idx, pid)

    for pid, d in sorted(decisions.items(), key=sort_key):
        choice = d.get("choice", "tenant")
        pname = d.get("provision_name", pid)
        verdict = d.get("final_verdict", "")
        severity = d.get("severity", "")
        text = d.get("text", "").strip()

        heading_text = f"{pid}  {pname}"
        if severity:
            heading_text += f"  \u2014  {severity}"
        doc.add_heading(heading_text, level=2)

        badge_map = {
            "template": "\u2713 Restored to standard template",
            "tenant":   "\u2192 Tenant language accepted" if verdict == "DEVIATES" else "\u2713 Conforms \u2014 no change",
            "custom":   "\u26a1 Custom compromise language",
        }
        badge_para = doc.add_paragraph()
        badge_run = badge_para.add_run(badge_map.get(choice, ""))
        badge_run.font.size = Pt(9)
        badge_run.font.color.rgb = (
            RGBColor(0x16, 0xa3, 0x4a) if choice == "template" else
            RGBColor(0x7c, 0x3a, 0xed) if choice == "custom" else
            RGBColor(0x64, 0x74, 0x8b)
        )

        doc.add_paragraph(text if text else "(No clause text recorded)")
        doc.add_paragraph()

    doc.add_page_break()
    disc = doc.add_paragraph(
        "Generated by CAM\u2122 \u00b7 Patent Pending \u00b7 "
        "This document is a drafting aid and does not constitute legal advice. "
        "All provisions should be reviewed by qualified legal counsel before execution."
    )
    disc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in disc.runs:
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    filename = f"final_draft_{job_id or 'lease'}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# LEASE-SPECIFIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/jobs/lease")
async def create_lease_job(
    access_code: str = Form(...),
    email: Optional[str] = Form(None),
    template_file: UploadFile = File(...),
    tenant_files: List[UploadFile] = File(...),
    provisions: Optional[str] = Form(None),
    custom_provisions: Optional[str] = Form(None),
    custom_from_scan: Optional[str] = Form(None),
    added_from_scan: Optional[str] = Form(None),
    prescan_record: Optional[str] = Form(None),
    instructions: Optional[str] = Form(None),
    strictness: Optional[str] = Form("standard"),
    template_type: Optional[str] = Form("blank_template"),
    identity_check: Optional[str] = Form("landlord_property"),
):
    """Create a lease analysis job with file uploads."""
    config = get_config()

    # Validate access code
    if config["ACCESS_CODE"] and access_code != config["ACCESS_CODE"]:
        raise HTTPException(status_code=401, detail="Invalid access code")

    # Validate strictness
    if strictness not in ("permissive", "standard", "strict"):
        raise HTTPException(status_code=400, detail="strictness must be permissive, standard, or strict")

    # Validate template_type
    if template_type not in ("blank_template", "executed_reference"):
        template_type = "blank_template"

    # Validate identity_check
    if identity_check not in ("clauses_only", "landlord_property", "landlord_tenant"):
        identity_check = "landlord_property"

    # Parse provisions JSON (if provided)
    selected_ids = None
    if provisions:
        try:
            selected_ids = json.loads(provisions)
            if not isinstance(selected_ids, list):
                raise ValueError("provisions must be a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid provisions JSON: {e}")

    # Parse custom provisions JSON (if provided)
    custom_provisions_list = None
    if custom_provisions:
        try:
            custom_provisions_list = json.loads(custom_provisions)
            if not isinstance(custom_provisions_list, list):
                raise ValueError("custom_provisions must be a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid custom_provisions JSON: {e}")

    # Parse pre-scan provisions (050)
    custom_from_scan_list = []
    if custom_from_scan:
        try:
            custom_from_scan_list = json.loads(custom_from_scan)
        except (json.JSONDecodeError, ValueError):
            custom_from_scan_list = []

    # Parse prescan record (092)
    prescan_record_parsed = None
    if prescan_record:
        try:
            prescan_record_parsed = json.loads(prescan_record)
        except (json.JSONDecodeError, ValueError):
            prescan_record_parsed = None

    added_from_scan_list = []
    if added_from_scan:
        try:
            added_from_scan_list = json.loads(added_from_scan)
        except (json.JSONDecodeError, ValueError):
            added_from_scan_list = []

    # Generate job ID early so we can use it for upload directory
    job_id = job_manager._generate_job_id("lease_review")

    # Save uploaded files
    upload_dir = Path(config["UPLOAD_DIR"]) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save template
    template_save_path = upload_dir / template_file.filename
    content = await template_file.read()
    template_save_path.write_bytes(content)

    # Save tenant files and build tenant list (with ZIP extraction)
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
    tenants = []
    for tf in tenant_files:
        tenant_save_path = upload_dir / tf.filename
        content = await tf.read()
        tenant_save_path.write_bytes(content)

        if tenant_save_path.suffix.lower() == ".zip":
            # Extract supported files from ZIP
            try:
                with zipfile.ZipFile(str(tenant_save_path), "r") as zf:
                    for name in zf.namelist():
                        # Skip directories and hidden files
                        if name.endswith("/") or name.startswith("__") or "/." in name:
                            continue
                        ext = Path(name).suffix.lower()
                        if ext not in ALLOWED_EXTENSIONS:
                            continue
                        # Extract to upload dir
                        extracted_name = Path(name).name  # strip subdirectories
                        extracted_path = upload_dir / extracted_name
                        with zf.open(name) as src:
                            extracted_path.write_bytes(src.read())
                        tenants.append({
                            "filename": extracted_name,
                            "upload_path": str(extracted_path),
                            "status": "queued",
                            "stage": None,
                            "error": None,
                            "result_path": None,
                            "annotated_path": None,
                        })
                # Remove the ZIP after extraction
                tenant_save_path.unlink(missing_ok=True)
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid ZIP file: {tf.filename}",
                )
        else:
            tenants.append({
                "filename": tf.filename,
                "upload_path": str(tenant_save_path),
                "status": "queued",
                "stage": None,
                "error": None,
                "result_path": None,
                "annotated_path": None,
            })

    if not tenants:
        raise HTTPException(
            status_code=400,
            detail="No valid tenant files found. Supported formats: PDF, DOCX, TXT (or ZIP containing these).",
        )

    # Build input config
    input_config = {
        "template_file": template_file.filename,
        "template_path": str(template_save_path),
        "tenants": tenants,
        "provisions": selected_ids,
        "custom_provisions": custom_provisions_list,
        "custom_from_scan": custom_from_scan_list,
        "added_from_scan": added_from_scan_list,
        "prescan_record": prescan_record_parsed,
        "strictness": strictness,
        "instructions": instructions or "",
        "template_type": template_type,
        "identity_check": identity_check,
        "access_code": access_code,  # Step 140: for user rules injection
    }

    # Create job with the pre-generated ID (matches upload directory)
    job = job_manager.create_job("lease_review", email, input_config, job_id=job_id)

    # Start background processing
    job_manager.start_processing(job_id)

    return {
        "job_id": job_id,
        "status": "queued",
        "estimated_minutes": job["estimated_minutes"],
        "results_url": f"{config['APP_BASE_URL']}/results/{job_id}",
    }


@app.get("/api/jobs/{job_id}/results/{tenant_index}/annotated")
def download_annotated(job_id: str, tenant_index: int):
    """Download the annotated document (DOCX or PDF) for a tenant."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") == "completed" and job_manager.is_job_expired(job):
        return JSONResponse(status_code=410, content={"detail": "This analysis has expired."})

    tenants = job.get("input_config", {}).get("tenants", [])
    if tenant_index < 0 or tenant_index >= len(tenants):
        raise HTTPException(status_code=404, detail="Invalid tenant index")

    tenant = tenants[tenant_index]
    annotated_path = tenant.get("annotated_path")

    if not annotated_path or not Path(annotated_path).exists():
        raise HTTPException(status_code=404, detail="Annotated document not available")

    filename = f"annotated_{tenant['filename']}"
    # Match the extension of the annotated file
    ext = Path(annotated_path).suffix
    if not filename.endswith(ext):
        filename = Path(filename).stem + ext

    return FileResponse(
        path=annotated_path,
        filename=filename,
        media_type="application/octet-stream",
    )


@app.post("/api/jobs/{job_id}/add-tenants")
async def add_tenants_to_job(
    job_id: str,
    tenant_files: List[UploadFile] = File(...),
    add_provisions: Optional[str] = Form(None),
):
    """Add more tenant leases to an existing completed job.

    Reuses the cached standard template from the original analysis.
    New tenants are processed and appended to the existing job's results.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") not in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Job must be completed before adding tenants")

    if job_manager.is_job_expired(job):
        return JSONResponse(status_code=410, content={"detail": "This analysis has expired."})

    config = get_config()
    input_cfg = job["input_config"]
    template_path = input_cfg.get("template_path")

    if not template_path or not Path(template_path).exists():
        # Template was already deleted — need to re-upload
        raise HTTPException(
            status_code=400,
            detail="Template file no longer available. Please start a new analysis.",
        )

    # Save new tenant files
    upload_dir = Path(config["UPLOAD_DIR"]) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
    new_tenants = []
    for tf in tenant_files:
        tenant_save_path = upload_dir / tf.filename
        content = await tf.read()
        tenant_save_path.write_bytes(content)

        if tenant_save_path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(str(tenant_save_path), "r") as zf:
                    for name in zf.namelist():
                        if name.endswith("/") or name.startswith("__") or "/." in name:
                            continue
                        ext = Path(name).suffix.lower()
                        if ext not in ALLOWED_EXTENSIONS:
                            continue
                        extracted_name = Path(name).name
                        extracted_path = upload_dir / extracted_name
                        with zf.open(name) as src:
                            extracted_path.write_bytes(src.read())
                        new_tenants.append({
                            "filename": extracted_name,
                            "upload_path": str(extracted_path),
                            "status": "queued",
                            "stage": None,
                            "error": None,
                            "result_path": None,
                            "annotated_path": None,
                        })
                tenant_save_path.unlink(missing_ok=True)
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail=f"Invalid ZIP file: {tf.filename}")
        else:
            new_tenants.append({
                "filename": tf.filename,
                "upload_path": str(tenant_save_path),
                "status": "queued",
                "stage": None,
                "error": None,
                "result_path": None,
                "annotated_path": None,
            })

    if not new_tenants:
        raise HTTPException(status_code=400, detail="No valid tenant files found.")

    # If caller also wants new provisions added in the same pass, apply them first
    # so that incremental processing picks them up for the new tenants.
    # (Existing tenants do NOT get re-run here — user can do a separate add-provisions
    #  run for existing tenants once this completes.)
    new_provision_ids = []
    if add_provisions:
        try:
            parsed = json.loads(add_provisions)
            if isinstance(parsed, list):
                existing_ids = set(input_cfg.get("provisions") or [])
                new_provision_ids = [p for p in parsed if p not in existing_ids]
                if new_provision_ids:
                    job_manager.append_provisions(job_id, new_provision_ids)
        except (json.JSONDecodeError, TypeError):
            pass  # Ignore malformed field — proceed with tenants only

    # Append new tenants to the job and set back to processing
    job_manager.append_tenants(job_id, new_tenants)

    # Start background processing for new tenants only
    job_manager.start_incremental_processing(job_id, len(input_cfg["tenants"]) - len(new_tenants))

    return {
        "job_id": job_id,
        "status": "processing",
        "new_tenants": len(new_tenants),
        "new_provisions_added": new_provision_ids,
        "total_tenants": len(input_cfg["tenants"]),
    }


@app.post("/api/jobs/{job_id}/add-provisions")
async def add_provisions_to_job(
    job_id: str,
    body: dict,
):
    """Add more provisions to an existing completed job.

    Runs the analysis pipeline on new provisions only for each tenant,
    using cached tenant text and standard provisions.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") not in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Job must be completed before adding provisions")

    if job_manager.is_job_expired(job):
        return JSONResponse(status_code=410, content={"detail": "This analysis has expired."})

    new_provision_ids = body.get("provisions", [])
    if not new_provision_ids or not isinstance(new_provision_ids, list):
        raise HTTPException(status_code=400, detail="Required: provisions (list of provision IDs)")

    config = get_config()
    input_cfg = job["input_config"]
    template_path = input_cfg.get("template_path")

    if not template_path or not Path(template_path).exists():
        raise HTTPException(
            status_code=400,
            detail="Template file no longer available. Please start a new analysis.",
        )

    # Get existing provision IDs to avoid re-running
    existing_ids = set(input_cfg.get("provisions") or [])
    truly_new = [pid for pid in new_provision_ids if pid not in existing_ids]

    if not truly_new:
        raise HTTPException(status_code=400, detail="All requested provisions were already analyzed.")

    # Update job's provision list and set back to processing
    job_manager.append_provisions(job_id, truly_new)

    # Start background processing for new provisions
    job_manager.start_provision_processing(job_id, truly_new)

    return {
        "job_id": job_id,
        "status": "processing",
        "new_provisions": truly_new,
        "total_provisions": len(existing_ids | set(truly_new)),
    }


@app.post("/api/jobs/{job_id}/chat")
async def chat_with_analysis(job_id: str, body: dict):
    """Ask follow-up questions about the analysis results.

    Supports single-model (default) and multi-model modes.
    Full analysis context is included in the system prompt.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") not in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Job must be completed to chat")

    if job_manager.is_job_expired(job):
        return JSONResponse(status_code=410, content={"detail": "This analysis has expired."})

    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    mode = body.get("mode", "single")  # "single" or "multi"
    models = body.get("models", ["claude"])
    synthesize = body.get("synthesize", False)
    synthesizer = body.get("synthesizer", "claude")
    provision_id = body.get("provision_id")  # optional scope
    tenant_idx = body.get("tenant_idx")  # optional int — scope to one tenant
    history = body.get("history", [])

    # Load tenant results for context
    domain_label = "Document Analysis"  # safe default
    tenants = job.get("input_config", {}).get("tenants", [])
    context_parts = []
    for i, tenant in enumerate(tenants):
        # If tenant_idx specified, only include that tenant
        if tenant_idx is not None and i != int(tenant_idx):
            continue
        result_path = tenant.get("result_path")
        if result_path and Path(result_path).exists():
            try:
                data = json.loads(Path(result_path).read_text(encoding="utf-8"))
                # Read domain label from first result (pipeline-agnostic)
                if i == 0:
                    domain_label = data.get("pipeline_domain_label", domain_label)
                tenant_file = data.get("tenant_file", tenant.get("filename", ""))
                context_parts.append(f"\n--- Tenant: {tenant_file} ---")

                if provision_id:
                    # Scope to specific provision
                    for p in data.get("provisions", []):
                        if p.get("provision_id") == provision_id:
                            context_parts.append(json.dumps(p, indent=2, default=str))
                            break
                else:
                    # Include all provisions summary
                    for p in data.get("provisions", []):
                        pid = p.get("provision_id", "")
                        verdict = p.get("final_verdict", "")
                        sev = p.get("severity", "")
                        headline = p.get("risk_headline", "")
                        details = p.get("challenge_details", "")
                        action = p.get("recommended_action", "")
                        agreement = p.get("agreement_pattern", "")
                        ev_verdicts = p.get("evaluator_verdicts", {})
                        ev_summary = ", ".join(f"{k}: {v}" for k, v in ev_verdicts.items()) if ev_verdicts else ""
                        context_parts.append(
                            f"  {pid}: {verdict} ({sev}) - {headline}\n"
                            f"    Evaluator agreement: {agreement}{(' (' + ev_summary + ')') if ev_summary else ''}\n"
                            f"    Details: {details}\n"
                            f"    Action: {action}"
                        )

                    # Include key text excerpts
                    meta = data.get("contract_metadata", {})
                    if meta:
                        context_parts.append(f"  Contract: {json.dumps(meta, default=str)}")
            except (json.JSONDecodeError, OSError):
                pass

    analysis_context = "\n".join(context_parts)

    system_prompt = (
        f"You are a specialized assistant for {domain_label}. "
        f"You have access to the structured analysis findings for the document(s) in this session, "
        f"provided below as ANALYSIS CONTEXT.\n\n"

        "SCOPE:\n"
        "Answer questions about the documents, findings, provisions, deviations, risk implications, "
        "negotiation strategy, and legal concepts relevant to this analysis. "
        "If asked whether to sign, proceed, or how to approach a negotiation, engage fully — "
        "use the actual findings to give a substantive answer. "
        "You are not a licensed attorney and this is not legal advice; say so naturally at the end "
        "when your answer touches on decisions or professional judgment, not as an upfront disclaimer. "
        "If a question is clearly unrelated to this analysis or its subject matter, redirect warmly: "
        f"'I'm focused on your {domain_label.lower()} — happy to dig into any of the findings "
        "or documents in this session. Is there something specific you would like to explore?'\n\n"

        "RESPONSE GUIDELINES:\n"
        "- Be specific: reference actual provisions, findings, and severity levels from the analysis.\n"
        "- Plain language. This is a conversation, not a memo.\n"
        "- 200-300 words unless the user asks for more detail.\n"
        "- No markdown code blocks or code fences. Use quotation marks for contract language.\n"
        "- In multi-model responses, refer to models by name (Claude, GPT-5.2, Grok, Gemini).\n"
        "- When disclaiming, do it once, briefly, at the end — not at the start, not repeatedly.\n\n"

        f"CAM KNOWLEDGE BASE (use this to answer any questions about CAM, scores, signals, pipeline stages, or provisions):\n{CAM_KNOWLEDGE}\n\n"

        f"ANALYSIS CONTEXT:\n{analysis_context}"
    )

    # Build conversation context from history (Part 4: memory fix)
    conversation_context = ""
    if history:
        recent = history[-10:]  # Last 10 turns (5 exchanges)
        for h in recent:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role == "user":
                conversation_context += f"\nUser asked: {content}\n"
            else:
                # Check if this is a multi-model response (contains [Model]: labels)
                if content.startswith("[") and "]:" in content:
                    conversation_context += f"\nMultiple AI models responded:\n{content}\n"
                else:
                    conversation_context += f"\nAI responded: {content}\n"

    # Build the full user prompt with history
    if conversation_context:
        full_prompt = (
            f"CONVERSATION HISTORY:\n{conversation_context}\n"
            f"---\n"
            f"CURRENT QUESTION:\n{question}"
        )
    else:
        full_prompt = question

    # Route to model(s)
    model_map = {
        "claude": "claude",
        "gpt": "openai",
        "grok": "xai",
        "gemini": "google",
    }
    model_labels = {"claude": "Claude", "openai": "GPT-5.2", "xai": "Grok", "google": "Gemini"}

    _FRIENDLY_MODEL_NAMES = {
        "claude-sonnet-4-20250514": "Claude Sonnet 4",
        "claude-opus-4-5-20250514": "Claude Opus 4.5",
        "gpt-5.2": "GPT-5.2",
        "grok-3": "Grok 3",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
        "mistral-large-latest": "Mistral Large",
    }

    def _friendly_model_label(model_str: str, fallback_key: str) -> str:
        """Return friendly display name for a model string."""
        return _FRIENDLY_MODEL_NAMES.get(model_str, model_labels.get(fallback_key, fallback_key))

    try:
        from cam.core.llm import call_llm
        import concurrent.futures

        if mode == "multi":
            # Multi-model: parallel calls
            responses = {}
            actual_models = {}
            selected_models = [m for m in models if m in model_map]
            if not selected_models:
                selected_models = ["claude"]

            def _call_model(model_key):
                provider = model_map[model_key]
                try:
                    result = call_llm(
                        provider=provider,
                        system_prompt=system_prompt,
                        user_prompt=full_prompt,
                        temperature=0.3,
                    )
                    actual_model = result.get("model", "")
                    return model_key, result.get("content", ""), actual_model
                except Exception as e:
                    return model_key, f"Error: {e}", ""

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(_call_model, m): m for m in selected_models}
                for future in concurrent.futures.as_completed(futures):
                    model_key, response, actual_model = future.result()
                    responses[model_key] = response
                    actual_models[model_key] = actual_model

            if synthesize and len(responses) > 1:
                # Build synthesis prompt with all model responses
                model_responses_text = "\n\n".join(
                    f"[{k.upper()}]: {v}" for k, v in responses.items()
                )
                synthesis_prompt = (
                    f"The following question was asked:\n{question}\n\n"
                    f"These AI models responded:\n\n{model_responses_text}\n\n"
                    f"Synthesize these responses into one clear, unified answer. "
                    f"Note where models agreed and where they differed. "
                    f"Attribute specific insights to the model that provided them. "
                    f"Be concise (200-300 words)."
                )
                synthesizer_provider = model_map.get(synthesizer, "anthropic")
                model_labels_display = {"claude": "Claude", "gpt": "GPT-5.2", "grok": "Grok", "gemini": "Gemini"}
                try:
                    synthesis_result = call_llm(
                        provider=synthesizer_provider,
                        system_prompt=system_prompt,
                        user_prompt=synthesis_prompt,
                        temperature=0.3,
                    )
                    return {
                        "synthesized_response": synthesis_result.get("content", ""),
                        "synthesized_by": model_labels_display.get(synthesizer, synthesizer),
                        "mode": "multi",
                        "individual_responses": responses,
                        "actual_models": actual_models,
                    }
                except Exception as e:
                    # Fall back to individual if synthesis fails
                    logger.warning(f"Synthesis failed, falling back to individual: {e}")
                    return {"responses": responses, "actual_models": actual_models, "mode": "multi"}
            else:
                return {"responses": responses, "actual_models": actual_models, "mode": "multi"}

        else:
            # Single model — use selected model from picker (default: Claude)
            selected_model = body.get("model", "claude")
            provider = model_map.get(selected_model, "claude")
            result = call_llm(
                provider=provider,
                system_prompt=system_prompt,
                user_prompt=full_prompt,
                temperature=0.3,
            )

            return {
                "response": result.get("content", ""),
                "mode": "single",
                "model_label": _friendly_model_label(result.get("model", ""), selected_model),
                "model_key": selected_model,
                "actual_model": result.get("model", ""),
            }

    except Exception as e:
        logger.error(f"Chat error for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {e}")


@app.post("/api/chat/general")
async def chat_general(request: Request):
    """General lease guidance chat — no job required.

    For pre-analysis questions about provisions, lease concepts,
    and what to look for.
    """
    body = await request.json()
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    context = body.get("context", {})
    history = body.get("history", [])

    system_prompt = (
        "You are a lease analysis guidance assistant for CAM, a commercial lease "
        "deviation analyzer. The user is on the upload page preparing to analyze "
        "one or more tenant leases against a standard reference contract.\n\n"

        "THE CURRENT UI FLOW (describe this accurately when asked how to get started):\n"
        "Step 1 — Upload two things:\n"
        "  - LEFT zone: the Standard / Reference Contract (their ideal template lease, single file)\n"
        "  - RIGHT zone: one or more Tenant Leases to compare against the template\n\n"
        "Step 2 — Provision Checklist (right panel):\n"
        "  LP-01 through LP-18 are checked by default. "
        "The user can uncheck provisions they don't want analyzed, or add custom provisions.\n"
        "  CAM will also automatically flag any other substantive clauses it notices during "
        "analysis — these appear as 'Additional Findings' in the results.\n\n"
        "Step 3 — Click 'Analyze Leases'.\n\n"

        "WHAT YOU HELP WITH:\n"
        "- Walking users through the steps above when they ask how to get started\n"
        "- Explaining what each provision means and why it matters\n"
        "- Advising which provisions to check for specific lease types\n"
        "- Explaining that CAM automatically discovers additional substantive clauses "
        "during analysis and surfaces them as Additional Findings\n"
        "- Answering general commercial lease questions\n\n"

        "WHAT YOU CAN AND CANNOT SEE:\n"
        "You CAN see (when provided in context):\n"
        "- The list of standard provisions (LP-01 to LP-18) the user has selected.\n"
        "- The filenames of uploaded documents.\n"
        "- Any custom provisions the user has added.\n\n"
        "You CANNOT see:\n"
        "- The raw text of the uploaded lease documents.\n"
        "- The full analysis results (those are only available after analysis is complete).\n\n"
        "When asked about the specific text of a clause:\n"
        "- Explain that the actual clause text will be visible in the findings cards once "
        "they run the full analysis — each finding card shows the extracted provision text "
        "from both the template and the tenant lease side by side.\n"
        "- Do NOT say 'I don't have access to your documents' as the only answer — that's "
        "unhelpful. Tell them what you DO know and what they'll see after analysis.\n\n"
        "CRITICAL — UI ACCURACY:\n"
        "- Never reference buttons, links, icons, or interface elements that you are not "
        "certain exist. Do not invent 'View Source', 'See Context', 'Expand', or any "
        "other UI element to direct the user to.\n"
        "- The real UI elements you can reference:\n"
        "  - LP-01 through LP-18 checkboxes in the Standard Provisions list\n"
        "  - The 'Analyze Leases' button\n"
        "  - The 'Add custom provision' field at the bottom of the Provisions panel\n"
        "  - The chat panel (where the user is currently talking to you)\n"
        "- If you are not sure whether a UI element exists, describe the concept "
        "(e.g., 'once you run the analysis, each finding will show the extracted text') "
        "rather than naming a specific button or link.\n\n"

        "WHAT MAKES CAM UNIQUE (use this when asked 'why is CAM unique' or similar):\n"
        "CAM stands for Constrained Assertion Method. Most AI tools produce a single "
        "confident answer even when the evidence is weak or ambiguous — they are "
        "architected to always give you something. CAM is built differently.\n\n"
        "CAM's core approach:\n"
        "1. Multiple independent AI models (Gemini, Claude, GPT, Grok) each evaluate "
        "every provision separately, without seeing each other's answers.\n"
        "2. CAM preserves disagreement rather than hiding it. If models split on whether "
        "a clause is a deviation, that split is surfaced — not collapsed into a majority vote.\n"
        "3. CAM withholds assertions when confidence is insufficient. If the evidence "
        "does not support a clear finding, CAM says so rather than guessing.\n"
        "4. Every finding is backed by a structured reasoning chain — you can see why "
        "a deviation was flagged, not just that it was flagged.\n"
        "5. Severity (Critical, High, Medium, Low) is assessed separately from detection — "
        "a provision can be flagged as a deviation but assessed as low risk in context.\n\n"
        "In practice: CAM catches subtle deviations that single-model tools miss "
        "(like a word change that shifts the legal threshold), flags findings where "
        "models genuinely disagree so a lawyer can make the call, and never gives "
        "false certainty. The goal is to surface what matters, not to fill a report.\n\n"
        "CAM has been validated across scientific fact verification, legal contract "
        "entailment, and commercial lease analysis — the same multi-model disagreement "
        "framework runs underneath all of them.\n\n"

        f"CAM KNOWLEDGE BASE (use this to answer any questions about CAM, scores, signals, pipeline stages, or provisions):\n{CAM_KNOWLEDGE}\n\n"
    )

    # Add upload context if available
    selected = context.get("selected_provisions", [])
    if selected:
        system_prompt += f"USER'S SELECTED PROVISIONS: {', '.join(selected)}\n"
    uploaded = context.get("uploaded_files", [])
    if uploaded:
        system_prompt += f"UPLOADED FILES: {', '.join(uploaded)}\n"
    custom = context.get("custom_provisions", [])
    if custom:
        system_prompt += f"CUSTOM PROVISIONS ADDED: {', '.join(custom)}\n"

    system_prompt += (
        "\nRESPONSE GUIDELINES:\n"
        "- Be helpful and conversational. This is a guidance tool, not legal advice.\n"
        "- When asked 'how do I get started' or similar, describe the actual flow above concisely.\n"
        "- 100-200 words unless more detail is requested.\n"
        "- Reference provision IDs (LP-XX) when relevant.\n"
        "- No markdown code blocks or code fences. Use plain text formatting.\n"
        "- One brief disclaimer at the end if relevant — never at the start.\n"
        "- Never start with 'That's a great question' or similar affirmations.\n"
        "- When asked why CAM is unique, explain the multi-model disagreement approach "
        "in plain language. Do NOT describe it as just 'deviation analysis'.\n"
    )

    # Build conversation context from history
    conversation_context = ""
    if history:
        recent = history[-10:]
        for h in recent:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role == "user":
                conversation_context += f"\nUser asked: {content}\n"
            else:
                conversation_context += f"\nAI responded: {content}\n"

    if conversation_context:
        full_prompt = (
            f"CONVERSATION HISTORY:\n{conversation_context}\n"
            f"---\n"
            f"CURRENT QUESTION:\n{question}"
        )
    else:
        full_prompt = question

    try:
        from cam.core.llm import call_llm
        result = call_llm(
            provider="google",
            system_prompt=system_prompt,
            user_prompt=full_prompt,
            temperature=0.3,
        )
        return {
            "response": result.get("content", ""),
            "model": result.get("model", ""),
        }
    except Exception as e:
        logger.error(f"General chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {e}")


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Manually delete a job and all its results/uploads."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_manager.delete_job(job_id)
    return {"status": "deleted", "job_id": job_id}


@app.get("/api/provisions")
def get_provisions():
    """Return the 18 default provisions for the frontend checklist."""
    from cam.adapters.lease_review.lease_provision_taxonomy import PROVISIONS
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "default_enabled": p.get("default_enabled", True),
            "always_on": p.get("always_on", False),
            "identity_check": p.get("identity_check", False),
        }
        for p in PROVISIONS
    ]


# ── Summary document generation endpoints ──

@app.get("/api/jobs/{job_id}/results/{tenant_index}/summary")
def download_tenant_summary(job_id: str, tenant_index: int):
    """Generate and download a per-tenant summary DOCX document."""
    from app.summary_generator import generate_tenant_summary

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") == "completed" and job_manager.is_job_expired(job):
        return JSONResponse(status_code=410, content={"detail": "This analysis has expired."})

    if job["status"] != "completed":
        raise HTTPException(status_code=404, detail="Job not yet complete")

    tenants = job.get("input_config", {}).get("tenants", [])
    if tenant_index < 0 or tenant_index >= len(tenants):
        raise HTTPException(status_code=404, detail="Invalid tenant index")

    tenant = tenants[tenant_index]
    result_path = tenant.get("result_path")
    if not result_path or not Path(result_path).exists():
        raise HTTPException(status_code=404, detail="Results not available for this tenant")

    try:
        pipeline_results = json.loads(Path(result_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read results: {e}")

    config = get_config()
    output_dir = Path(config["RESULTS_DIR"]) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    tenant_name = Path(tenant["filename"]).stem
    output_path = str(output_dir / f"Summary_{tenant_name}.docx")

    try:
        generate_tenant_summary(
            pipeline_results,
            output_path,
            resolutions=job.get("resolutions", {}),
            tenant_idx=tenant_index,
        )
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e}")

    return FileResponse(
        path=output_path,
        filename=f"Summary_{tenant_name}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/jobs/{job_id}/summary")
def download_batch_summary(job_id: str):
    """Generate and download a combined summary PDF covering all tenants."""
    from app.summary_generator import generate_combined_summary_pdf

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") == "completed" and job_manager.is_job_expired(job):
        return JSONResponse(status_code=410, content={"detail": "This analysis has expired."})

    if job["status"] != "completed":
        raise HTTPException(status_code=404, detail="Job not yet complete")

    tenants = job.get("input_config", {}).get("tenants", [])
    tenant_results = []
    for tenant in tenants:
        result_path = tenant.get("result_path")
        if result_path and Path(result_path).exists():
            try:
                data = json.loads(Path(result_path).read_text(encoding="utf-8"))
                tenant_results.append(data)
            except (json.JSONDecodeError, OSError):
                pass

    if not tenant_results:
        raise HTTPException(status_code=404, detail="No tenant results available")

    config = get_config()
    output_dir = Path(config["RESULTS_DIR"]) / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "Lease_Analysis_Synopsis.pdf")

    try:
        generate_combined_summary_pdf(job, tenant_results, output_path)
    except Exception as e:
        logger.error(f"Summary PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e}")

    return FileResponse(
        path=output_path,
        filename="Lease_Analysis_Synopsis.pdf",
        media_type="application/pdf",
    )


# ── Results page route (frontend will handle rendering) ──

@app.get("/results/{job_id}")
def serve_results_page(job_id: str):
    """Serve the frontend for viewing results (same index.html, JS handles routing)."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(
            str(index_path),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return JSONResponse({"message": "Results page — frontend not yet built", "job_id": job_id})
