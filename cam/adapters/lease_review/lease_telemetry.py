"""
CAM Lease Analyzer — Telemetry Emitter

Writes one structured record per completed tenant run to:
  C:\\Users\\Owner\\OneDrive\\CAM\\telemetry\\runs.jsonl   (local)
  /app/telemetry/runs.jsonl                                (Railway)

Append-only. Fire-and-forget — never raises, never blocks pipeline.
Schema version: "1.0"
"""

import hashlib
import json
import os
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def emit(
    result: dict,           # full pipeline_results dict from lease_adapter
    config: dict,           # pipeline cfg dict (has _job_id, strictness, etc.)
    job: dict = None,       # job dict from job_manager (has resolutions, email, etc.)
) -> bool:
    """Emit telemetry record. Returns True on success, False on any error."""
    try:
        if job is None:
            job = {}

        stage_data = result.get("_stage_data", {})
        provisions = result.get("provisions", [])
        summary = result.get("summary", {})
        models_used = result.get("models_used", {})
        completeness = result.get("analysis_completeness", {})
        cam_summary = result.get("cam_contract_summary", {})

        # Count governance signals
        gov_counts = {}
        for p in provisions:
            sig = (p.get("cam_score") or {}).get("governance_signal", "")
            if sig:
                gov_counts[sig] = gov_counts.get(sig, 0) + 1

        record = {
            # ── Identity ──────────────────────────────────────────────────
            "schema_version": "1.0",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "job_id": config.get("_job_id", ""),
            "tenant_index": config.get("_tenant_index", 0),
            "run_id": result.get("run_id", ""),
            "pipeline_version": result.get("pipeline_version", ""),
            "app_version": _get_app_version(),
            "git_sha": _get_git_sha(),

            # ── Document ──────────────────────────────────────────────────
            "template_filename": result.get("template_file", ""),
            "tenant_filename": result.get("tenant_file", ""),
            "tenant_format": _get_format(result.get("tenant_file", "")),
            "tenant_word_count": config.get("tenant_word_count", 0),
            "tenant_char_count": len(result.get("full_tenant_text", "") or ""),
            "template_word_count": len((result.get("full_template_text", "") or "").split()),
            "extraction_path": _get_extraction_path(stage_data),
            "extraction_chunks": stage_data.get("extraction_meta", {}).get("num_chunks", 1),

            # ── Timing (seconds) ──────────────────────────────────────────
            "timing": {
                "total_elapsed_sec": round(result.get("elapsed_sec", 0), 2),
                "stage_1_extraction_sec": round(
                    stage_data.get("extraction_meta", {}).get("elapsed_sec", 0), 2),
                "stage_1_gap_repair_sec": round(
                    stage_data.get("extraction_meta", {}).get("gap_repair_elapsed_sec", 0), 2),
                "stage_1_total_sec": round(
                    stage_data.get("extraction_meta", {}).get("total_stage1_elapsed_sec", 0), 2),
                "stage_2_rules_sec": round(
                    stage_data.get("evaluation_meta", {}).get("rules_elapsed_sec", 0), 2),
                "stage_3_evaluation_sec": round(
                    stage_data.get("evaluation_meta", {}).get("total_elapsed_sec", 0), 2),
                "stage_3_evaluator_a_sec": round(
                    stage_data.get("evaluation_meta", {}).get("evaluator_a_elapsed_sec", 0), 2),
                "stage_3_evaluator_b_sec": round(
                    stage_data.get("evaluation_meta", {}).get("evaluator_b_elapsed_sec", 0), 2),
                "stage_3_evaluator_c_sec": round(
                    stage_data.get("evaluation_meta", {}).get("evaluator_c_elapsed_sec", 0), 2),
                "stage_5_challenge_sec": round(
                    stage_data.get("challenge_meta", {}).get("elapsed_sec", 0), 2),
                "stage_6_severity_sec": round(
                    stage_data.get("severity_meta", {}).get("elapsed_sec", 0), 2),
                "annotation_sec": 0,  # populated by job_manager after annotation
            },

            # ── API Calls ─────────────────────────────────────────────────
            "api_calls": {
                "total": result.get("api_calls_total", 0),
                "stage_1_extraction": stage_data.get("extraction_meta", {}).get("num_chunks", 1),
                "stage_1_gap_repair": stage_data.get("extraction_meta", {}).get("gap_repair_calls", 0),
                "stage_1_fallbacks": stage_data.get("extraction_meta", {}).get("fallback_chunk_count", 0),
                "stage_3_evaluation": stage_data.get("evaluation_meta", {}).get("api_calls", 3),
                "stage_5_challenge": stage_data.get("challenge_meta", {}).get("api_calls", 0),
                "stage_6_severity": stage_data.get("severity_meta", {}).get("api_calls", 0),
                "gate_check": 1,
                "other": 0,
            },

            # ── Models ────────────────────────────────────────────────────
            "models": {
                "extractor_primary": models_used.get("extractor", ""),
                "extractor_fallback_used": models_used.get("extractor_fallback_used", False),
                "extractor_fallback_model": stage_data.get("extraction_meta", {}).get("fallback_model", ""),
                "extractor_fallback_chunks": stage_data.get("extraction_meta", {}).get("fallback_chunk_count", 0),
                "evaluator_a": models_used.get("evaluator_a", ""),
                "evaluator_a_fallback_used": models_used.get("evaluator_a_fallback", False),
                "evaluator_b": models_used.get("evaluator_b", ""),
                "evaluator_b_fallback_used": models_used.get("evaluator_b_fallback", False),
                "evaluator_c": models_used.get("evaluator_c", ""),
                "evaluator_c_fallback_used": models_used.get("evaluator_c_fallback", False),
                "challenger": models_used.get("challenger", ""),
                "challenger_fallback_used": False,
                "severity": models_used.get("severity_assessor", ""),
                "severity_fallback_used": stage_data.get("severity_meta", {}).get("fallback_used", False),
                "severity_chunks": stage_data.get("severity_meta", {}).get("chunks", 1),
            },

            # ── Provisions ────────────────────────────────────────────────
            "provisions": {
                "selected_count": len(config.get("provisions", [])) or 18,
                "custom_discovered_raw": stage_data.get("extraction_meta", {}).get("discovered_raw_count", 0),
                "custom_discovered_deduped": stage_data.get("extraction_meta", {}).get("discovered_deduped_count", 0),
                "gap_repairs": completeness.get("gaps_resolved_by_reextraction", 0),
                "unclaimed_articles_injected": completeness.get("unclaimed_article_gaps", 0),
                "total_evaluated": len(provisions),
                "completeness_score": completeness.get("completeness_score", 0),
                "completeness_status": completeness.get("status", ""),
            },

            # ── Results Summary ───────────────────────────────────────────
            "results": {
                "total_provisions_checked": summary.get("total_provisions_checked", 0),
                "deviates": summary.get("deviates", 0),
                "conforms": summary.get("conforms", 0),
                "unclear": summary.get("unclear", 0),
                "critical": summary.get("critical", 0),
                "high": summary.get("high", 0),
                "medium": summary.get("medium", 0),
                "low": summary.get("low", 0),
                "deviation_rate": round(summary.get("deviates", 0) / max(1, len(provisions)), 3),
                "triage_passed": len(stage_data.get("triage", {}).get("passed", [])),
                "triage_flagged": len(stage_data.get("triage", {}).get("flagged", [])),
                "challenge_confirmed": sum(
                    1 for c in stage_data.get("challenge_raw", [])
                    if isinstance(c, dict) and c.get("challenge_verdict") == "SUBSTANTIVE_DEVIATION"
                ),
                "challenge_cosmetic": sum(
                    1 for c in stage_data.get("challenge_raw", [])
                    if isinstance(c, dict) and c.get("challenge_verdict") == "COSMETIC_DIFFERENCE"
                ),
                "challenge_expert_only": sum(
                    1 for c in stage_data.get("challenge_raw", [])
                    if isinstance(c, dict) and c.get("challenge_verdict") == "NEEDS_EXPERT"
                ),
            },

            # ── CAM Governance ────────────────────────────────────────────
            "governance": {
                "ASSERT_SIGNAL": gov_counts.get("ASSERT_SIGNAL", 0),
                "ASSERT_REVIEW_SIGNAL": gov_counts.get("ASSERT_REVIEW_SIGNAL", 0),
                "REVIEW_SIGNAL": gov_counts.get("REVIEW_SIGNAL", 0),
                "WITHHOLD_SIGNAL": gov_counts.get("WITHHOLD_SIGNAL", 0),
                "withhold_no_baseline": cam_summary.get("withhold_no_baseline", 0),
                "fragile_count": sum(1 for p in provisions if (p.get("fragility") or {}).get("fragile")),
                "abstention_rate": round(gov_counts.get("WITHHOLD_SIGNAL", 0) / max(1, len(provisions)), 3),
            },

            # ── Per-Provision Records ─────────────────────────────────────
            "provision_records": [
                {
                    "provision_id": p.get("provision_id", ""),
                    "provision_name": p.get("provision_name", ""),
                    "is_custom": p.get("provision_id", "").startswith("CUSTOM"),
                    "is_discovered": bool(p.get("discovered")),
                    "final_verdict": p.get("final_verdict", ""),
                    "severity": p.get("severity", ""),
                    "governance_signal": (p.get("cam_score") or {}).get("governance_signal", ""),
                    "agreement_pattern": p.get("agreement_pattern", ""),
                    "evaluator_a_verdict": (p.get("evaluator_verdicts") or {}).get("A", ""),
                    "evaluator_b_verdict": (p.get("evaluator_verdicts") or {}).get("B", ""),
                    "evaluator_c_verdict": (p.get("evaluator_verdicts") or {}).get("C", ""),
                    "evaluator_a_confidence": round((p.get("evaluator_confidences") or {}).get("A", 0) or 0, 3),
                    "evaluator_b_confidence": round((p.get("evaluator_confidences") or {}).get("B", 0) or 0, 3),
                    "evaluator_c_confidence": round((p.get("evaluator_confidences") or {}).get("C", 0) or 0, 3),
                    "challenge_verdict": p.get("challenge_finding", ""),
                    "cam_perm": round((p.get("cam_score") or {}).get("CAM_perm", 0) or 0, 2),
                    "cam_strict": round((p.get("cam_score") or {}).get("CAM_strict", 0) or 0, 2),
                    "asg": round((p.get("cam_score") or {}).get("ASG", 0) or 0, 2),
                    "fragile": bool((p.get("fragility") or {}).get("fragile")),
                    "fragility_signals": (p.get("fragility") or {}).get("signals", []),
                    "rules_fired": (p.get("cam_metadata") or {}).get("rules_fired", []),
                    "triage_result": (p.get("cam_metadata") or {}).get("triage_result", ""),
                    "severity_floor_applied": bool(p.get("severity_floor_applied")),
                    "cascade_verdict": p.get("cascade_verdict", ""),
                    "template_text_chars": len(p.get("template_text", "") or ""),
                    "tenant_text_chars": len(p.get("tenant_text", "") or ""),
                    "has_interpretation_note": bool(p.get("interpretation_note")),
                    "has_uncertainty_note": bool(p.get("uncertainty_note")),
                }
                for p in provisions
            ],

            # ── Evaluator Agreement ───────────────────────────────────────
            "evaluator_agreement": {
                "unanimous_deviates": sum(
                    1 for p in provisions
                    if list((p.get("evaluator_verdicts") or {}).values()).count("DEVIATES") == 3
                ),
                "unanimous_conforms": sum(
                    1 for p in provisions
                    if list((p.get("evaluator_verdicts") or {}).values()).count("CONFORMS") == 3
                ),
                "split_2_1_deviates": sum(
                    1 for p in provisions
                    if list((p.get("evaluator_verdicts") or {}).values()).count("DEVIATES") == 2
                ),
                "split_2_1_conforms": sum(
                    1 for p in provisions
                    if list((p.get("evaluator_verdicts") or {}).values()).count("CONFORMS") == 2
                ),
                "evaluator_a_deviates_rate": round(
                    sum(1 for p in provisions if (p.get("evaluator_verdicts") or {}).get("A") == "DEVIATES")
                    / max(1, len(provisions)), 3),
                "evaluator_b_deviates_rate": round(
                    sum(1 for p in provisions if (p.get("evaluator_verdicts") or {}).get("B") == "DEVIATES")
                    / max(1, len(provisions)), 3),
                "evaluator_c_deviates_rate": round(
                    sum(1 for p in provisions if (p.get("evaluator_verdicts") or {}).get("C") == "DEVIATES")
                    / max(1, len(provisions)), 3),
            },

            # ── Fragility Summary ─────────────────────────────────────────
            "fragility_summary": {
                "total_fragile": sum(1 for p in provisions if (p.get("fragility") or {}).get("fragile")),
                "fragility_rate": round(
                    sum(1 for p in provisions if (p.get("fragility") or {}).get("fragile"))
                    / max(1, len(provisions)), 3),
                "signal_counts": _count_fragility_signals(provisions),
            },

            # ── Rules Summary ─────────────────────────────────────────────
            "rules_summary": {
                "total_fires": sum(
                    len((p.get("cam_metadata") or {}).get("rules_fired", []))
                    for p in provisions
                ),
                "rule_counts": _count_rule_fires(provisions),
                "cascade_fired": not stage_data.get("cascade_meta", {}).get("skipped", True),
                "cascade_material_count": sum(
                    1 for p in provisions if p.get("cascade_verdict") == "CASCADE_MATERIAL"
                ),
            },

            # ── Session ───────────────────────────────────────────────────
            "session": {
                "strictness": config.get("strictness", "standard"),
                "template_type": config.get("template_type", "blank_template"),
                "identity_check": config.get("identity_check", "clauses_only"),
                "user_custom_provisions": len(config.get("custom_provisions") or []),
                "user_rules_injected": len(config.get("_user_rules") or []),
                "email_provided": bool(job.get("email") if job else False),
                "access_code_hash": _hash_access_code(config.get("access_code", "")),
            },
        }

        # Write to file
        telemetry_path = _get_telemetry_path()
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))

        try:
            telemetry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(telemetry_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            print(f"[telemetry] Record written to {telemetry_path}", flush=True)
            return True
        except Exception as file_err:
            # Fallback: log to stdout for Railway log scraping
            print(f"[TELEMETRY] {line}", flush=True)
            print(f"[telemetry] File write failed ({file_err}), logged to stdout", flush=True)
            return True

    except Exception as e:
        print(f"[telemetry] Emit failed (non-fatal): {e}", flush=True)
        traceback.print_exc()
        return False


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_format(filename: str) -> str:
    ext = Path(filename).suffix.lower() if filename else ""
    return ext.lstrip(".") or "unknown"


def _get_extraction_path(stage_data: dict) -> str:
    chunks = stage_data.get("extraction_meta", {}).get("num_chunks", 1)
    if chunks >= 4:
        return "4-chunk"
    if chunks == 2:
        return "2-chunk"
    return "single"


def _get_app_version() -> str:
    try:
        from app.config import APP_VERSION
        return APP_VERSION
    except Exception:
        return os.environ.get("APP_VERSION", "unknown")


def _get_git_sha() -> str:
    try:
        from app.config import GIT_SHA
        return GIT_SHA
    except Exception:
        return os.environ.get("GIT_SHA", "local")


def _hash_access_code(code: str) -> str:
    """Hash access code — lets us group by user without exposing the code."""
    return hashlib.sha256(code.encode()).hexdigest()[:12] if code else ""


def _count_fragility_signals(provisions: list) -> dict:
    counter = Counter()
    for p in provisions:
        counter.update((p.get("fragility") or {}).get("signals", []))
    return dict(counter)


def _count_rule_fires(provisions: list) -> dict:
    counter = Counter()
    for p in provisions:
        counter.update((p.get("cam_metadata") or {}).get("rules_fired", []))
    return dict(counter)


def _get_telemetry_path() -> Path:
    """Find the telemetry file — works locally and on Railway."""
    # Try Railway app path first
    railway_path = Path("/app/telemetry/runs.jsonl")
    if railway_path.parent.exists():
        railway_path.parent.mkdir(parents=True, exist_ok=True)
        return railway_path
    # Fall back to local CAM root
    try:
        from cam.core.config import CAM_ROOT
        local_path = CAM_ROOT / "telemetry" / "runs.jsonl"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return local_path
    except Exception:
        return Path("telemetry/runs.jsonl")
