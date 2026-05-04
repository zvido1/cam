"""
CAM Lease Review — Pipeline Orchestrator

Runs the full lease deviation analysis pipeline (Stages 1-6 + cascade micro-stage).
Pipeline order: Stage 1 (extraction) -> Stage 4 (rules) -> Cascade (if RULE-LS-002)
                -> Stage 2 (evaluators) -> Triage -> Stage 3 (challenge)
                -> Stage 5 (severity) -> Stage 6 (disposition)
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.adapters.lease_review.lease_parser import parse_document
from cam.adapters.lease_review.lease_provision_taxonomy import (
    PROVISIONS,
    get_active_provisions,
)
from cam.adapters.lease_review.lease_extract import extract_provisions
from cam.adapters.lease_review.extraction_cache import load_cached_extraction
from cam.adapters.lease_review.lease_fragility import detect_fragility
from cam.adapters.lease_review.lease_evaluate import evaluate_provisions
from cam.adapters.lease_review.lease_disposition import (
    triage_provisions,
    compute_all_dispositions,
)
from cam.adapters.lease_review.lease_challenge import challenge_provisions
from cam.adapters.lease_review.lease_severity import assess_severity
from cam.adapters.lease_review.lease_cascade import evaluate_definition_cascades
from cam.adapters.lease_review.lease_report_generator import generate_outputs
from cam.adapters.lease_review.lease_gate import check_document_is_lease
from cam.adapters.lease_review.lease_coverage_audit import (
    audit_coverage,
    format_gap_report,
    gaps_to_custom_provisions,
    verify_all_extractions,
)
from cam.adapters.lease_review.lease_extract import targeted_reextract_section
from cam.adapters.lease_review.lease_scorer import score_all_provisions
from cam.adapters.lease_review.lease_interpretation import generate_interpretation_notes, generate_uncertainty_notes


# Default model configuration
DEFAULT_CONFIG = {
    # Stage 1: Extraction (Gemini — long-document comprehension)
    "extraction_model": "gemini-3.1-pro-preview",
    "extraction_fallback_model": "gemini-2.5-pro",
    "extraction_timeout": 300.0,
    "extraction_max_tokens": 65536,
    # Stage 2: Evaluators (configured in lease_evaluate.py)
    # Stage 3: Challenge
    "challenge_model": "gpt-5.5",
    "challenge_timeout": 180.0,
    "challenge_max_tokens": 6000,
    # Cascade micro-stage (definition cascades)
    "cascade_model": "gpt-5.5",
    "cascade_timeout": 120.0,
    "cascade_max_tokens": 3000,
    # Stage 5: Severity
    "severity_model": "gpt-5.5",
    "severity_timeout": 120.0,
    "severity_max_tokens": 4000,
    # Interpretation notes (ASSERT_REVIEW_SIGNAL provisions only)
    "interpretation_model": "gpt-5.5",
    "interpretation_timeout": 60.0,
    # Output
    "output_dir": str(CAM_ROOT / "05 Lease Analyzer" / "results"),
}


# ── Provision keyword sets for gap repair relevance check ──────────────────
# Before backfilling an extra_subsection gap to a conditional provision,
# the gap repair checks if the section content contains any of these keywords.
# This prevents LP-22 (SNDA) from claiming "21.1 Notices" just because Article 21
# contains a subordination clause in 21.9.
# Only needed for conditional provisions with distinctive vocabulary.
_PROVISION_REPAIR_KEYWORDS = {
    "LP-22": {"subordination", "snda", "non-disturbance", "non disturbance", "attornment", "mortgagee", "deed of trust"},
    "LP-23": {"percentage rent", "gross sales", "breakpoint", "overage rent"},
    "LP-31": {"co-tenancy", "co tenancy", "anchor tenant", "occupancy threshold"},
    "LP-32": {"hazardous", "environmental", "toxic", "contaminant", "remediation", "cercla"},
}


def _section_relevant_to_provision(pid: str, section_ref: str, doc_text: str) -> bool:
    """Return True if the section content plausibly belongs to the claiming provision.

    Only runs a keyword check for provisions in _PROVISION_REPAIR_KEYWORDS.
    All other provisions pass through unconditionally (existing behavior).
    """
    keywords = _PROVISION_REPAIR_KEYWORDS.get(pid)
    if not keywords:
        return True  # no filter defined — allow repair as before

    # Extract a 400-char preview of the section from the document
    import re as _re_local
    pattern = _re_local.compile(
        r"\bsection\s+" + _re_local.escape(section_ref) + r"\b",
        _re_local.IGNORECASE,
    )
    m = pattern.search(doc_text)
    if not m:
        return True  # can't find the section — allow and let targeted_reextract decide
    preview = doc_text[m.start():m.start() + 400].lower()
    return any(kw in preview for kw in keywords)


class PipelineCancelledError(Exception):
    """Raised when a pipeline run is cancelled by the user."""
    pass


class GateAbortError(Exception):
    """Raised when the document gate check fails — not a lease."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _check_cancel(config: dict) -> None:
    """Check if cancellation has been requested for this job.

    Reads the _job_id from config (set by job_manager) and checks
    the cancel flag. Raises PipelineCancelledError if cancel requested.
    """
    job_id = config.get("_job_id")
    if not job_id:
        return  # No job context (CLI mode) — skip cancel check
    try:
        from app.job_manager import is_cancel_requested
        if is_cancel_requested(job_id):
            raise PipelineCancelledError(f"Job {job_id} cancelled by user")
    except ImportError:
        pass  # Not running in web app context


def _resolve_discoveries(
    all_discoveries: dict,   # {"A": [...], "B": [...], "C": [...]}
    selected_provision_ids: set,
) -> dict:
    """Resolve per-evaluator discovery flags into folded and standalone groups.

    Logic:
    - Group flags across evaluators by clause_name (case-insensitive).
    - For each group:
        FOLD: all evaluators that found it suggest the SAME LP, and that LP
              is in selected_provision_ids → absorbed, no separate display.
        STANDALONE: everything else → surface as Additional Finding.

    Returns:
        {
            "folded":     [{"clause_name", "lp_id", "evaluators", "clause_text", ...}]
            "standalone": [{"clause_name", "clause_text", "evaluators_found",
                            "evaluator_details", "suggested_lps", "resolution_label"}]
        }
    """
    from collections import defaultdict

    # Collect all flags, keyed by lowercased clause_name
    groups = defaultdict(lambda: {"evaluators": [], "items": []})
    for evaluator_key, flags in all_discoveries.items():
        for flag in flags:
            name_key = flag.get("clause_name", "").lower().strip()
            if not name_key:
                continue
            groups[name_key]["evaluators"].append(evaluator_key)
            groups[name_key]["items"].append({**flag, "evaluator": evaluator_key})

    folded = []
    standalone = []

    for name_key, group in groups.items():
        items = group["items"]
        evaluators_found = group["evaluators"]

        # Pick the most detailed clause_text across all items
        clause_text = max((i.get("clause_text", "") for i in items), key=len, default="")
        clause_name = items[0].get("clause_name", name_key)
        section_ref = items[0].get("tenant_section_ref", "")

        # Collect suggested LPs from all evaluators that found this clause
        suggested_lps = [
            i.get("suggested_lp") for i in items if i.get("suggested_lp")
        ]

        # FOLD condition: all evaluators agree on the same LP, and it's selected
        unique_lps = set(suggested_lps)
        if (
            len(unique_lps) == 1
            and list(unique_lps)[0] in selected_provision_ids
            and len(evaluators_found) == len(all_discoveries)  # all evaluators found it
        ):
            folded.append({
                "clause_name": clause_name,
                "lp_id": list(unique_lps)[0],
                "evaluators": evaluators_found,
                "clause_text": clause_text,
                "tenant_section_ref": section_ref,
            })
            continue

        # STANDALONE: build resolution label
        if len(evaluators_found) == len(all_discoveries):
            if len(unique_lps) > 1:
                resolution_label = f"Flagged by all models — models disagree on classification"
            elif len(unique_lps) == 1 and list(unique_lps)[0] not in selected_provision_ids:
                lp = list(unique_lps)[0]
                resolution_label = f"Flagged — may relate to {lp} (not in scope)"
            else:
                resolution_label = "Flagged by all models — no standard provision match"
        else:
            n = len(evaluators_found)
            total = len(all_discoveries)
            resolution_label = f"Flagged by {n} of {total} models — lower confidence"

        standalone.append({
            "provision_id": f"DISC-{name_key[:20].upper().replace(' ', '_')}",
            "clause_name": clause_name,
            "clause_text": clause_text,
            "tenant_section_ref": section_ref,
            "evaluators_found": evaluators_found,
            "evaluator_details": {i["evaluator"]: i for i in items},
            "suggested_lps": suggested_lps,
            "unique_suggested_lps": list(unique_lps),
            "resolution_label": resolution_label,
        })

    return {"folded": folded, "standalone": standalone}


def run_lease_analysis(
    template_path: str,
    tenant_path: str,
    provisions: List[dict] = None,
    config: dict = None,
    run_id: str = None,
    progress_callback=None,
) -> dict:
    """Run the full lease deviation analysis pipeline (Stages 1-6).

    Args:
        template_path: Path to the standard lease template file.
        tenant_path: Path to the tenant lease file.
        provisions: List of provision dicts to analyze. If None, uses all 18 defaults.
        config: Configuration dict overriding DEFAULT_CONFIG values.
        run_id: Optional run identifier for output naming.

    Returns:
        Full pipeline results dict.
    """
    # Merge config
    cfg = {**DEFAULT_CONFIG}
    if config:
        cfg.update(config)

    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("lease_%Y%m%d_%H%M%S")

    if provisions is None:
        provisions = get_active_provisions()

    print(f"[lease_adapter] Starting analysis: run_id={run_id}", flush=True)
    print(f"[lease_adapter] Template: {os.path.basename(template_path)}", flush=True)
    print(f"[lease_adapter] Tenant: {os.path.basename(tenant_path)}", flush=True)
    print(f"[lease_adapter] Provisions: {len(provisions)}", flush=True)

    pipeline_start = time.time()
    total_api_calls = 0
    models_used = {}

    # ── Parse documents ──
    print("[lease_adapter] Parsing documents...", flush=True)
    reference_parse_start = time.time()
    template_text = parse_document(template_path)
    reference_parse_elapsed = time.time() - reference_parse_start
    print(f"[lease_adapter] Reference parse complete in {reference_parse_elapsed:.2f}s", flush=True)

    tenant_parse_start = time.time()
    tenant_text = parse_document(tenant_path)
    tenant_parse_elapsed = time.time() - tenant_parse_start
    print(f"[lease_adapter] Tenant parse complete in {tenant_parse_elapsed:.2f}s", flush=True)

    parse_elapsed_total = reference_parse_elapsed + tenant_parse_elapsed
    tenant_word_count = len(tenant_text.split())
    cfg["tenant_word_count"] = tenant_word_count
    print(
        f"[lease_adapter] Template: {len(template_text)} chars, Tenant: {len(tenant_text)} chars ({tenant_word_count} words) | total local parse {parse_elapsed_total:.2f}s",
        flush=True,
    )

    # ── Document Gate Check ──
    # Verify tenant document is a commercial lease before burning expensive API calls.
    # Skip if extraction cache exists (demo/sample files are pre-validated).
    _cached_extraction = load_cached_extraction(template_text, tenant_text)
    if _cached_extraction:
        print("[lease_adapter] Gate: skipped (extraction cache exists — pre-validated document)", flush=True)
    else:
        print("[lease_adapter] Gate: classifying tenant document...", flush=True)
        gate_result = check_document_is_lease(tenant_text, cfg)
        print(f"[lease_adapter] Gate: is_lease={gate_result['is_lease']} in {gate_result['elapsed_sec']}s", flush=True)
        if gate_result.get("abort"):
            raise GateAbortError(gate_result["abort_message"])

    # ── Stage 1: Provision Extraction & Alignment ──
    if progress_callback:
        progress_callback(1, 6, "Extracting and aligning provisions from the lease.")
    print("[lease_adapter] Stage 1: Provision extraction...", flush=True)

    # Reuse cache lookup from gate check, or try fresh
    extraction = _cached_extraction or load_cached_extraction(template_text, tenant_text)
    if extraction:
        print(f"[lease_adapter] Stage 1 loaded from cache: {len(extraction['provisions'])} provisions", flush=True)
        models_used["extractor"] = extraction["meta"].get("model", "cached")
        models_used["extractor_provider"] = extraction["meta"].get("provider", "cached")
        models_used["extractor_fallback_used"] = extraction["meta"].get("fallback_used", False)
    else:
        extraction = extract_provisions(template_text, tenant_text, provisions, cfg)
        total_api_calls += 1
        models_used["extractor"] = extraction["meta"]["model"]
        models_used["extractor_provider"] = extraction["meta"].get("provider", "google")
        models_used["extractor_fallback_used"] = extraction["meta"].get("fallback_used", False)
        if extraction["meta"].get("fallback_used"):
            print(f"[lease_adapter] Stage 1 complete (FALLBACK: {extraction['meta']['model']}): "
                  f"{len(extraction['provisions'])} provisions in {extraction['meta']['elapsed_sec']}s", flush=True)
        else:
            print(f"[lease_adapter] Stage 1 complete: {len(extraction['provisions'])} provisions in {extraction['meta']['elapsed_sec']}s", flush=True)

    _check_cancel(cfg)

    # ── Dedup extraction provisions (052) ──
    seen_pids = set()
    deduped_ext = []
    for p in extraction["provisions"]:
        epid = p.get("provision_id") or p.get("id")
        if epid in seen_pids:
            print(f"[052] Deduped duplicate provision in extraction: {epid}", flush=True)
            continue
        seen_pids.add(epid)
        deduped_ext.append(p)
    extraction["provisions"] = deduped_ext

    # ── Inject discovered provisions as CUSTOM-XX entries ──
    # Discovered provisions are non-standard articles found in the tenant lease
    # during extraction. Convert them to CUSTOM-XX provision entries so Stage 2
    # evaluators can assess them.
    raw_discoveries = extraction.get("discovered_provisions", [])
    raw_discoveries_before_dedup = len(raw_discoveries)

    # Deduplicate across chunks: each chunk independently discovers provisions,
    # so the same clause (e.g. "Relocation") can appear 3-4 times. Keep the
    # instance with the most clause_text content.
    if raw_discoveries:
        seen_names: dict = {}
        for disc in raw_discoveries:
            name_key = (disc.get("clause_name") or disc.get("article_label") or "").lower().strip()
            if not name_key:
                continue
            existing = seen_names.get(name_key)
            if existing is None or len(disc.get("clause_text", "")) > len(existing.get("clause_text", "")):
                seen_names[name_key] = disc
        deduped_discoveries = list(seen_names.values())
        if len(deduped_discoveries) < len(raw_discoveries):
            print(f"[lease_adapter] Deduped discovered provisions: {len(raw_discoveries)} → {len(deduped_discoveries)}", flush=True)
        raw_discoveries = deduped_discoveries

    if raw_discoveries:
        print(f"[lease_adapter] Injecting {len(raw_discoveries)} discovered provision(s) as CUSTOM-XX entries", flush=True)
        for idx, disc in enumerate(raw_discoveries, start=1):
            custom_id = f"CUSTOM-{idx:02d}"
            clause_name = disc.get("clause_name") or disc.get("article_label") or f"Non-Standard Clause {idx}"
            custom_entry = {
                "provision_id": custom_id,
                "provision_name": clause_name,
                "template_text": "",
                "tenant_text": disc.get("clause_text", ""),
                "template_section_ref": "[NOT PRESENT IN TEMPLATE]",
                "tenant_section_ref": disc.get("tenant_section_ref", disc.get("article_label", "")),
                "status": "TENANT_ONLY",
                "alignment_notes": f"Non-standard clause added by tenant ({disc.get('article_label', '')}). Not present in standard template.",
                "definition_changes": "",
            }
            extraction["provisions"].append(custom_entry)
            print(f"[lease_adapter]   Injected: {custom_id} — {clause_name}", flush=True)
    else:
        print("[lease_adapter] No discovered provisions to inject", flush=True)

    # ── Coverage Audit + Extraction Integrity (Step 192) ──
    print("[lease_adapter] Coverage audit: checking for uncaptured sections...", flush=True)
    coverage_gaps = audit_coverage(tenant_text, extraction, template_text=template_text)

    # Build integrity records for all provisions
    integrity_map = verify_all_extractions(
        extraction_provisions=extraction["provisions"],
        template_text=template_text,
        tenant_text=tenant_text,
    )

    gap_repair_start = time.time()
    gap_repair_call_count = 0

    if coverage_gaps:
        print(f"[lease_adapter] Coverage audit: {len(coverage_gaps)} gap(s) detected", flush=True)
        print(f"[lease_adapter] {format_gap_report(coverage_gaps)}", flush=True)

        # Repair extra_subsection gaps: targeted re-extraction
        repaired_sections = set()  # Track by section ref to avoid double-repair
        for gap in coverage_gaps:
            if gap["gap_type"] != "extra_subsection":
                continue
            section_ref = gap.get("section_ref")
            if section_ref in repaired_sections:
                print(f"[lease_adapter] Skipping duplicate repair: {section_ref} (already repaired)", flush=True)
                continue
            pid = gap["claimed_by"]
            if not pid:
                continue
            prov = next((p for p in extraction["provisions"]
                        if p.get("provision_id") == pid), None)
            if not prov:
                continue

            # Relevance check: skip repair if section content is off-topic for
            # this provision. Prevents LP-22 (SNDA) from claiming "21.1 Notices"
            # just because Article 21 contains a subordination clause in 21.9.
            if not _section_relevant_to_provision(pid, section_ref, tenant_text):
                print(f"[lease_adapter] Skipping off-topic gap repair: "
                      f"{section_ref} → {pid} (content not relevant)", flush=True)
                repaired_sections.add(section_ref)  # mark handled so it doesn't become CUSTOM
                continue

            print(f"[lease_adapter] Repairing gap: {gap['section_ref']} "
                  f"in {pid}...", flush=True)
            recovered = targeted_reextract_section(
                provision_id=pid,
                provision_name=prov.get("provision_name", pid),
                missing_section_ref=gap["section_ref"],
                tenant_text=tenant_text,
                config=cfg,
            )
            gap_repair_call_count += 1
            repaired_sections.add(section_ref)
            if recovered:
                prov["tenant_text"] = (prov.get("tenant_text", "") or "").rstrip()
                prov["tenant_text"] += f"\n\n{recovered}"
                # Update integrity record
                if pid in integrity_map:
                    integrity_map[pid]["repair_applied"] = True
                    integrity_map[pid]["repair_sections"].append(gap["section_ref"])
                print(f"[lease_adapter] Gap repaired: {gap['section_ref']} appended to {pid}", flush=True)

        # Inject unclaimed articles as CUSTOM provisions (existing behavior)
        existing_custom_count = len(raw_discoveries)
        gap_stubs = gaps_to_custom_provisions(coverage_gaps, tenant_text, existing_custom_count)
        if gap_stubs:
            print(f"[lease_adapter] Coverage audit: injecting {len(gap_stubs)} "
                  f"unclaimed article(s) as CUSTOM provisions", flush=True)
            for stub in gap_stubs:
                extraction["provisions"].append(stub)
                integrity_map[stub["provision_id"]] = {
                    "verification_status":    "injected",
                    "extraction_verified":    False,
                    "extraction_paraphrased": False,
                    "extraction_incomplete":  False,
                    "extraction_expanded":    False,
                    "repair_applied":         False,
                    "repair_sections":        [],
                    "input_frozen":           False,
                    "source_length_chars":    0,
                    "extracted_length_chars": len(stub.get("tenant_text", "")),
                    "length_ratio":           0.0,
                }
                print(f"[lease_adapter]   Injected: {stub['provision_id']} "
                      f"— {stub['provision_name']}", flush=True)
    else:
        print("[lease_adapter] Coverage audit: PASS — all sections accounted for", flush=True)

    extraction["coverage_gaps"] = coverage_gaps

    # ── Update extraction meta with telemetry sub-fields ──
    gap_repair_elapsed = time.time() - gap_repair_start
    extraction["meta"]["gap_repair_elapsed_sec"] = round(gap_repair_elapsed, 2)
    extraction["meta"]["gap_repair_calls"] = gap_repair_call_count
    extraction["meta"]["total_stage1_elapsed_sec"] = round(
        extraction["meta"].get("elapsed_sec", 0) + gap_repair_elapsed, 2)
    extraction["meta"]["discovered_raw_count"] = raw_discoveries_before_dedup
    extraction["meta"]["discovered_deduped_count"] = len(raw_discoveries)

    # ── Input Freeze (Step 192) ──
    # Mark all provisions as frozen. Evaluation must not run on non-frozen provisions.
    for prov in extraction["provisions"]:
        pid = prov.get("provision_id", "")
        if pid in integrity_map:
            integrity_map[pid]["input_frozen"] = True
        else:
            # Provision has no integrity record (edge case) — create minimal record
            integrity_map[pid] = {
                "verification_status": "unverifiable",
                "extraction_verified": False,
                "extraction_paraphrased": False,
                "extraction_incomplete": False,
                "extraction_expanded": False,
                "repair_applied": False,
                "repair_sections": [],
                "input_frozen": True,
                "source_length_chars": 0,
                "extracted_length_chars": len(prov.get("tenant_text", "")),
                "length_ratio": 0.0,
            }
        # Attach integrity record to provision for downstream use
        prov["_stage1_integrity"] = integrity_map[pid]

    print(f"[lease_adapter] Input frozen: {len(extraction['provisions'])} "
          f"provisions ready for evaluation", flush=True)

    # ── analysis_completeness (Step 192) ──
    total_sections = sum(
        len(set(re.findall(r'\d+\.\d+', (p.get("tenant_text", "") or "") +
                            (p.get("tenant_section_ref", "") or ""))))
        for p in extraction["provisions"]
    )
    gaps_found = len(coverage_gaps)
    extra_sub_gaps = len([g for g in coverage_gaps if g["gap_type"] == "extra_subsection"])
    unclaimed_gaps  = len([g for g in coverage_gaps if g["gap_type"] == "unclaimed_section"])
    # Count individual section repairs, not just provisions with any repair
    repaired = sum(
        len(v.get("repair_sections", []))
        for v in integrity_map.values()
        if v.get("repair_applied")
    )
    remaining = max(0, extra_sub_gaps - repaired)

    if gaps_found == 0:
        completeness_status = "COMPLETE"
    elif remaining == 0:
        completeness_status = "GAPS_RESOLVED"
    else:
        completeness_status = "GAPS_UNRESOLVED"

    analysis_completeness = {
        "status":                         completeness_status,
        "coverage_gaps_detected":         gaps_found,
        "extra_subsection_gaps":          extra_sub_gaps,
        "unclaimed_article_gaps":         unclaimed_gaps,
        "gaps_resolved_by_reextraction":  repaired,
        "gaps_remaining":                 remaining,
        "completeness_score":             round(1.0 - (remaining / max(1, gaps_found + 1)), 3),
    }
    print(f"[lease_adapter] analysis_completeness: {completeness_status} "
          f"(score: {analysis_completeness['completeness_score']})", flush=True)

    # ── LP-00 Configuration ──
    # Apply run_config settings to LP-00's evaluation context.
    # identity_check: what fields LP-00 should flag
    # template_type: blank form vs executed reference (affects what "deviation" means)
    identity_check = cfg.get("identity_check", "landlord_property")  # default: check landlord+property
    template_type = cfg.get("template_type", "blank_template")        # default: blank form

    lp00_entry = next(
        (p for p in extraction["provisions"] if p.get("provision_id") == "LP-00"),
        None,
    )
    if lp00_entry is not None:
        # Build the evaluator instruction based on run configuration
        if identity_check == "clauses_only":
            # User wants no identity check — LP-00 runs for metadata only
            # Mark it so disposition can skip surfacing a verdict
            lp00_entry["_identity_check_mode"] = "metadata_only"
            lp00_entry["definition_changes"] = (
                "EVALUATOR NOTE: This is a metadata-only pass. "
                "Do NOT evaluate for deviations. Return verdict CONFORMS regardless of content. "
                "LP-00 is being used solely to extract contract metadata for the report header."
            )
        else:
            # Build scoped instruction
            if identity_check == "landlord_property":
                scope = (
                    "Flag ONLY if: (1) the landlord entity name differs from the template, "
                    "or (2) the property name or address differs from the template. "
                    "Do NOT flag differences in tenant entity name, suite number, square footage, "
                    "or lease dates — these are expected per-tenant fills."
                )
            else:  # landlord_tenant
                scope = (
                    "Flag if: (1) the landlord entity name differs, "
                    "(2) the property name or address differs, "
                    "or (3) the tenant entity name differs from the reference. "
                    "Do NOT flag differences in suite number, square footage, or lease dates."
                )

            if template_type == "executed_reference":
                scope += (
                    " NOTE: The reference document is a previously executed lease — "
                    "its values are real deal terms, not placeholders."
                )

            # Append custom-article annotation if applicable
            custom_annotation = ""
            if raw_discoveries:
                custom_names = [
                    f"CUSTOM-{i+1:02d} ({disc.get('clause_name') or disc.get('article_label', 'Non-Standard Clause')})"
                    for i, disc in enumerate(raw_discoveries)
                ]
                custom_annotation = (
                    f" Additionally: this lease contains non-standard articles evaluated separately as: "
                    f"{', '.join(custom_names)}. Any new Article I definitions supporting those articles "
                    f"are fully accounted for in those CUSTOM evaluations — do NOT treat them as LP-00 deviations."
                )

            existing = lp00_entry.get("definition_changes", "").strip()
            full_note = f"EVALUATOR NOTE: {scope}{custom_annotation}"
            lp00_entry["definition_changes"] = (existing + "\n\n" + full_note).strip()
            lp00_entry["_identity_check_mode"] = identity_check

        print(f"[lease_adapter] LP-00 configured: mode={identity_check}, template_type={template_type}", flush=True)

    print(f"[lease_adapter] Provisions: all {len(extraction['provisions'])} in scope (no filtering)", flush=True)

    # ── Stage 4: Fragility Detection (pure Python, 0 API calls) ──
    # Run BEFORE evaluators — costs nothing and gives triage more info
    if progress_callback:
        progress_callback(2, 6, "Running detection rules...")
    print("[lease_adapter] Stage 4: Fragility detection...", flush=True)
    fragility = detect_fragility(extraction["provisions"], template_text, tenant_text)
    fragile_count = sum(1 for f in fragility if f["fragile"])
    print(f"[lease_adapter] Stage 4 complete: {fragile_count} fragile provisions detected", flush=True)

    # Store definitions for cascade + challenger definition-cascade injection
    from cam.adapters.lease_review.lease_fragility import _extract_definitions_section
    from cam.rules.lease_rules import identify_changed_definitions
    cfg["_template_definitions"] = _extract_definitions_section(template_text)
    cfg["_tenant_definitions"] = _extract_definitions_section(tenant_text)
    changed_terms = identify_changed_definitions(cfg["_template_definitions"], cfg["_tenant_definitions"])

    # ── Cascade Micro-Stage: Definition cascade evaluation (0-1 API calls) ──
    # Runs ONLY when RULE-LS-002 fired on at least one provision
    cascade_result = {"cascades": {}, "meta": {"skipped": True}}
    has_rule_ls_002 = any(
        any(r["rule_id"] == "RULE-LS-002" for r in f.get("rules_fired", []))
        for f in fragility if f.get("fragile")
    )
    if has_rule_ls_002:
        print("[lease_adapter] Cascade: Definition cascade evaluation...", flush=True)
        cascade_result = evaluate_definition_cascades(
            fragility, extraction["provisions"],
            cfg["_template_definitions"], cfg["_tenant_definitions"],
            changed_terms, cfg,
        )
        if not cascade_result["meta"].get("skipped"):
            total_api_calls += cascade_result["meta"].get("api_calls", 0)
            models_used["cascade"] = cascade_result["meta"].get("model", "gpt-5.2")
            material = sum(1 for c in cascade_result["cascades"].values() if c.get("verdict") == "CASCADE_MATERIAL")
            immaterial = sum(1 for c in cascade_result["cascades"].values() if c.get("verdict") == "CASCADE_IMMATERIAL")
            print(f"[lease_adapter] Cascade complete: {material} material, {immaterial} immaterial in {cascade_result['meta']['elapsed_sec']}s", flush=True)
    else:
        print("[lease_adapter] Cascade: Skipped (no RULE-LS-002 fires)", flush=True)

    # ── Cascade Context Injection ──
    # For CASCADE_MATERIAL provisions, inject the cascade finding into the
    # extraction provision so evaluators receive informed context.
    # Evaluators originally saw the provision text in isolation and said CONFORMS
    # because they didn't know a referenced definition had changed. With this
    # injection they can make an informed verdict. No extra API calls.
    cascade_map_pre = cascade_result.get("cascades", {})
    for prov in extraction["provisions"]:
        pid = prov.get("provision_id", "")
        c = cascade_map_pre.get(pid, {})
        if c.get("verdict") == "CASCADE_MATERIAL":
            cascade_summary = c.get("cascade_mechanism") or c.get("reasoning") or ""
            existing_note = prov.get("definition_changes", "").strip()
            injection = (
                f"DEFINITION CASCADE ALERT: A pre-analysis cascade check has determined "
                f"that a changed definition in this lease materially affects this provision. "
                f"Even if the provision text appears unchanged, evaluate it as DEVIATES and "
                f"explain the impact. Cascade finding: {cascade_summary[:500]}"
            )
            prov["definition_changes"] = (existing_note + "\n\n" + injection).strip() if existing_note else injection

    _check_cancel(cfg)

    # ── Stage 2: Multi-Evaluator Assessment (3 parallel API calls) ──
    if progress_callback:
        progress_callback(3, 6, "Evaluating independently with 3 AI models...")
    print("[lease_adapter] Stage 2: Evaluator assessment (3 models)...", flush=True)
    evaluation = evaluate_provisions(extraction["provisions"], cfg)
    total_api_calls += evaluation["meta"]["api_calls"]
    for key, ev in evaluation["evaluators"].items():
        models_used[f"evaluator_{key.lower()}"] = ev.get("model", "unknown")
        models_used[f"evaluator_{key.lower()}_provider"] = ev.get("provider", "unknown")
        models_used[f"evaluator_{key.lower()}_fallback"] = ev.get("fallback_used", False)
    eval_count = evaluation["meta"].get("evaluator_count", 3)
    degraded_note = " (DEGRADED: 2/3)" if evaluation["meta"].get("degraded") else ""
    print(f"[lease_adapter] Stage 2 complete: {eval_count}/3 evaluators in {evaluation['meta']['total_elapsed_sec']}s{degraded_note}", flush=True)

    # ── Discovery Resolution ──
    # Resolve flags from all evaluators into folded (absorbed by LP) or
    # standalone (surfaced as additional findings) discoveries.
    discoveries = _resolve_discoveries(
        evaluation.get("all_discoveries", {}),
        {p.get("id") or p.get("provision_id") for p in provisions},
    )
    print(f"[lease_adapter] Discovery: {len(discoveries['standalone'])} standalone, "
          f"{len(discoveries['folded'])} folded", flush=True)

    # ── Triage Gate ──
    if progress_callback:
        progress_callback(4, 6, "Analyzing evaluator agreement...")
    print("[lease_adapter] Triage gate...", flush=True)
    passed, flagged = triage_provisions(
        evaluation["aggregated"], fragility, extraction["provisions"],
        cascade_results=cascade_result.get("cascades", {}),
    )
    passed_ids = {p["provision_id"] for p in passed}
    flagged_ids = {f["provision_id"] for f in flagged}
    print(f"[lease_adapter] Triage: {len(passed)} passed, {len(flagged)} flagged", flush=True)
    if flagged:
        for f in flagged:
            reasons = ", ".join(f.get("flag_reasons", []))[:80]
            print(f"[lease_adapter]   Flagged: {f['provision_id']} ({reasons})", flush=True)

    # Build lookup maps for downstream stages
    ext_map = {p["provision_id"]: p for p in extraction["provisions"]}
    eval_agg_map = {a["provision_id"]: a for a in evaluation["aggregated"]}
    frag_map = {f["provision_id"]: f for f in fragility}

    _check_cancel(cfg)

    # ── Stage 3: Targeted Challenge (0-1 API calls) ──
    challenge_result = {"challenges": {}, "meta": {"skipped": True}}
    if flagged:
        print(f"[lease_adapter] Stage 3: Challenge ({len(flagged)} provisions)...", flush=True)
        challenge_result = challenge_provisions(flagged, ext_map, eval_agg_map, cfg)
        if not challenge_result["meta"].get("skipped"):
            total_api_calls += challenge_result["meta"].get("api_calls", 0)
            models_used["challenger"] = challenge_result["meta"].get("model") or cfg.get("challenge_model", "")
            print(f"[lease_adapter] Stage 3 complete in {challenge_result['meta']['elapsed_sec']}s", flush=True)
    else:
        print("[lease_adapter] Stage 3: Skipped (nothing flagged)", flush=True)

    # Identify confirmed deviations for severity assessment
    cascade_map = cascade_result.get("cascades", {})
    confirmed_deviations = []
    confirmed_pids = set()
    for f in flagged:
        pid = f["provision_id"]
        ch = challenge_result["challenges"].get(pid, {})
        if ch.get("challenge_verdict") in ("SUBSTANTIVE_DEVIATION", "NEEDS_EXPERT"):
            confirmed_deviations.append(f)
            confirmed_pids.add(pid)
        elif ext_map.get(pid, {}).get("status") == "TEMPLATE_ONLY":
            confirmed_deviations.append(f)
            confirmed_pids.add(pid)
        elif cascade_map.get(pid, {}).get("verdict") == "CASCADE_MATERIAL":
            # Cascade confirmed material impact — include for severity even if
            # challenger said COSMETIC (cascade overrides for definition changes)
            confirmed_deviations.append(f)
            confirmed_pids.add(pid)
        elif not ch:
            # No challenge result for this provision (possibly evaluator-only flag)
            # Still include if majority says DEVIATES
            if eval_agg_map.get(pid, {}).get("majority_verdict") == "DEVIATES":
                confirmed_deviations.append(f)
                confirmed_pids.add(pid)

    _check_cancel(cfg)

    # ── Stage 5: Severity Assessment (0-1 API calls) ──
    if progress_callback:
        detail = "Challenger AI probing flagged findings..." if flagged else "Assessing deviation severity and impact..."
        progress_callback(5, 6, detail)
    severity_result = {"severities": {}, "meta": {"skipped": True}}
    if confirmed_deviations:
        print(f"[lease_adapter] Stage 5: Severity assessment ({len(confirmed_deviations)} deviations)...", flush=True)
        severity_result = assess_severity(
            confirmed_deviations, ext_map, eval_agg_map,
            challenge_result["challenges"], frag_map, cfg
        )
        if not severity_result["meta"].get("skipped"):
            total_api_calls += severity_result["meta"].get("api_calls", 0)
            models_used["severity_assessor"] = severity_result["meta"].get("model", "gpt-5.2")
            print(f"[lease_adapter] Stage 5 complete in {severity_result['meta']['elapsed_sec']}s", flush=True)
    else:
        print("[lease_adapter] Stage 5: Skipped (no confirmed deviations)", flush=True)

    # ── Stage 6: Final Disposition (0 API calls) ──
    if progress_callback:
        progress_callback(6, 6, "Determining final verdicts...")
    print("[lease_adapter] Stage 6: Disposition...", flush=True)
    dispositions = compute_all_dispositions(
        extraction["provisions"],
        fragility,
        evaluation["aggregated"],
        challenge_result["challenges"],
        severity_result["severities"],
        passed_ids,
        flagged_ids,
        cascade_results=cascade_result.get("cascades", {}),
    )

    # ── Cross-Reference Linkage (Step 115) ──
    # Connect conforming fragile provisions to deviating definition changes.
    # Additive only — no verdicts or severities changed.
    from cam.adapters.lease_review.lease_crossref_linker import run as run_crossref_linker
    _xref_temp = {"provisions": dispositions, "summary": {}}
    _xref_temp = run_crossref_linker(_xref_temp)
    dispositions = _xref_temp["provisions"]
    crossref_warnings = _xref_temp.get("summary", {}).get("cross_reference_warnings", [])

    # ── CAM Scoring (0 API calls) ──
    # Attach cam_score to each provision and build contract-level summary.
    cam_contract_summary = score_all_provisions(dispositions)
    print(
        f"[lease_adapter] CAM scoring complete: "
        f"ASSERT={cam_contract_summary['governance_counts']['ASSERT_SIGNAL']} "
        f"ASSERT_REVIEW={cam_contract_summary['governance_counts']['ASSERT_REVIEW_SIGNAL']} "
        f"REVIEW={cam_contract_summary['governance_counts']['REVIEW_SIGNAL']} "
        f"WITHHOLD={cam_contract_summary['governance_counts']['WITHHOLD_SIGNAL']}",
        flush=True
    )

    # ── Coverage & Negative Space Assessment (Step 244 — shadow mode) ──
    # Runs after all core pipeline stages. Writes coverage outputs into results
    # without affecting disposition logic, scoring, or any existing pipeline behavior.
    # Non-fatal: failure here does not abort the pipeline.
    coverage_assessment = []
    coverage_summary = {}
    negative_space_by_provision = {}
    try:
        from cam.adapters.lease_review.lease_negative_space import (
            detect_negative_space, summarize_negative_space,
        )
        from cam.adapters.lease_review.lease_coverage import (
            assess_coverage, summarize_coverage,
        )
        negative_space_by_provision = detect_negative_space(dispositions, tenant_text)
        _job_id = cfg.get("_job_id")
        def _lp_progress_cb(lp_id, lp_name, state):
            if _job_id:
                try:
                    from app.job_manager import update_lp_progress
                    update_lp_progress(_job_id, lp_id, lp_name, state)
                except Exception:
                    pass
        coverage_assessment = assess_coverage(
            dispositions, tenant_text, negative_space_by_provision,
            lp_progress_callback=_lp_progress_cb,
        )
        coverage_summary = summarize_coverage(coverage_assessment)
        ns_summary = summarize_negative_space(negative_space_by_provision)
        print(
            f"[lease_adapter] Coverage assessment (shadow): "
            f"{coverage_summary.get('covered_count', 0)} covered, "
            f"{coverage_summary.get('attention_count', 0)} require attention, "
            f"{coverage_summary.get('not_applicable_count', 0)} not applicable | "
            f"neg-space: {ns_summary.get('total_signals', 0)} signals across "
            f"{ns_summary.get('provisions_with_signals', 0)} provisions",
            flush=True,
        )
    except Exception as e:
        print(
            f"[lease_adapter] Coverage assessment failed (non-fatal, shadow mode): {e}",
            flush=True,
        )
        coverage_assessment = []
        coverage_summary = {}
        negative_space_by_provision = {}

    # ── Stage 5b: Jurisdiction-aware escalation (Step 297a) ──
    governing_law = None
    escalation_log = []
    conflicts = []
    try:
        from cam.adapters.lease_review import lease_jurisdiction
        governing_law = lease_jurisdiction.extract_governing_law(
            coverage_assessment,
            provisions=extraction.get("provisions"),
            contract_metadata=extraction.get("contract_metadata")
        )
        if governing_law:
            print(f"[lease_adapter] Detected governing law: {governing_law}", flush=True)
            coverage_assessment, escalation_log = lease_jurisdiction.apply_jurisdiction_rules(
                coverage_assessment,
                governing_law=governing_law,
                provisions=extraction.get("provisions"),
                contract_metadata=extraction.get("contract_metadata")
            )
            if escalation_log:
                print(f"[lease_adapter] Applied {len(escalation_log)} jurisdiction escalation(s)", flush=True)
                for entry in escalation_log:
                    print(f"[lease_adapter]   {entry['lp_id']}: {entry['from']} -> {entry['to']}", flush=True)
            else:
                print(f"[lease_adapter] No escalations triggered for {governing_law}", flush=True)
        else:
            print("[lease_adapter] No governing law detected — skipping jurisdiction rules", flush=True)
    except Exception as e:
        print(f"[lease_adapter] Jurisdiction engine failed (non-fatal): {e}", flush=True)

    # Step 298c: Rebuild coverage_summary with post-escalation states.
    # summarize_coverage ran before Stage 5b; escalated LPs were bucketed
    # with their pre-escalation state. Re-running picks up the new states
    # (e.g. LP-09 covered_unfavorable → potentially_unenforceable under NY).
    # Only runs when escalations actually fired to keep non-escalated runs
    # byte-identical to their pre-298c output.
    if escalation_log:
        coverage_summary = summarize_coverage(coverage_assessment)
        _ATTN_SORT_298C = {
            "potentially_unenforceable": 0,
            "covered_unfavorable": 1,
            "missing": 2,
            "broken_xref": 3,
            "partial": 4,
            "ambiguous": 5,
            "review_needed": 6,
        }
        coverage_summary.get("attention_items", []).sort(
            key=lambda x: _ATTN_SORT_298C.get(x["state"], 99)
        )

    # ── Stage 5d: Use-Aware Coverage Classification (Step 301 / gated 301a) ──
    use_profile_data = None
    use_analysis_status = "disabled"
    use_adjustment_log: list = []
    from cam.adapters.lease_review.lease_use_aware_coverage import STAGE_5D_ENABLED
    if not STAGE_5D_ENABLED:
        print(
            "[lease_adapter] Stage 5d: gated (single-eval unstable; awaiting Step 302 multi-eval)",
            flush=True,
        )
    else:
        try:
            from cam.adapters.lease_review.lease_use_aware_coverage import (
                should_run_use_analysis, generate_use_profile, assess_use_aware_coverage,
            )
            _use_clause = (extraction.get("contract_metadata") or {}).get("permitted_use", "")
            if should_run_use_analysis(_use_clause):
                print(f"[lease_adapter] Stage 5d: generating use profile...", flush=True)
                use_profile_data = generate_use_profile(_use_clause)
                if use_profile_data:
                    coverage_assessment, use_adjustment_log = assess_use_aware_coverage(
                        use_profile_data, coverage_assessment, cfg
                    )
                    if use_adjustment_log:
                        coverage_summary = summarize_coverage(coverage_assessment)
                        _ATTN_SORT = {"potentially_unenforceable": 0, "covered_unfavorable": 1,
                                      "missing": 2, "broken_xref": 3, "partial": 4,
                                      "ambiguous": 5, "review_needed": 6}
                        coverage_summary.get("attention_items", []).sort(
                            key=lambda x: _ATTN_SORT.get(x["state"], 99)
                        )
                        print(
                            f"[lease_adapter] Stage 5d: {len(use_adjustment_log)} use-adjustment(s) applied",
                            flush=True,
                        )
                    else:
                        print("[lease_adapter] Stage 5d: no adjustments applied", flush=True)
                    use_analysis_status = "applied"
                else:
                    use_analysis_status = "skipped_call1_failed"
            else:
                print("[lease_adapter] Stage 5d: skipped (use clause absent or generic)", flush=True)
                use_analysis_status = "not_applicable"
        except Exception as e:
            print(f"[lease_adapter] Stage 5d failed (non-fatal): {e}", flush=True)

    # ── Stage 5c: Cross-provision conflict detection (Step 297a) ──
    try:
        from cam.adapters.lease_review import lease_conflicts
        conflicts = lease_conflicts.detect_conflicts(
            coverage_assessment,
            provisions=extraction.get("provisions"),
            perspective=cfg.get("perspective", "tenant")
        )
        print(f"[lease_conflicts] Detected {len(conflicts)} conflict(s)", flush=True)
        for c in conflicts:
            print(f"[lease_conflicts]   {c['id']}: {c['name']} ({c['severity']})", flush=True)
    except Exception as e:
        print(f"[lease_adapter] Conflict engine failed (non-fatal): {e}", flush=True)

    # ── Exposure Engine (Step 243) ──
    # Enriches coverage assessments with exposure statements.
    # Schema text by default; model only for high-materiality cases.
    # Adds exposure_statement, exposure_source, materiality, partial_class
    # to each issue area assessment. Non-fatal.
    exposure_summary = {}
    if coverage_assessment:
        try:
            from cam.adapters.lease_review.lease_exposure import (
                generate_exposure, summarize_exposure,
            )
            generate_exposure(coverage_assessment, cfg)
            exposure_summary = summarize_exposure(coverage_assessment)
            print(
                f"[lease_adapter] Exposure: "
                f"{exposure_summary.get('model_calls', 0)} model, "
                f"{exposure_summary.get('schema_only', 0)} schema | "
                f"material={exposure_summary.get('partial_material', 0)} "
                f"review={exposure_summary.get('partial_review', 0)} "
                f"typical={exposure_summary.get('partial_typical', 0)}",
                flush=True,
            )
        except Exception as e:
            print(f"[lease_adapter] Exposure engine failed (non-fatal): {e}", flush=True)
            exposure_summary = {}

    # ── Interpretation Notes (0-N API calls, ASSERT_REVIEW_SIGNAL only) ──
    # Generate specific clause-level interpretation notes for provisions
    # flagged as "Check Interpretation" (high confidence but interpretation-sensitive).
    # Non-fatal: if generation fails, provisions just won't have interpretation_note.
    try:
        interp_count = generate_interpretation_notes(dispositions, cfg)
        if interp_count > 0:
            total_api_calls += interp_count
            models_used["interpretation"] = cfg.get("interpretation_model", "gpt-5.2")
            print(f"[lease_adapter] Interpretation notes: {interp_count} generated",
                  flush=True)
    except Exception as e:
        print(f"[lease_adapter] Interpretation notes failed (non-fatal): {e}", flush=True)

    # ── Uncertainty Notes (0-N API calls, REVIEW_SIGNAL only) ──
    # Generate notes explaining evaluator disagreement for provisions where
    # the system is uncertain whether a real deviation exists.
    # Non-fatal: if generation fails, provisions just won't have the note.
    try:
        uncert_count = generate_uncertainty_notes(dispositions, cfg)
        if uncert_count > 0:
            total_api_calls += uncert_count
            print(f"[lease_adapter] Uncertainty notes: {uncert_count} generated",
                  flush=True)
    except Exception as e:
        print(f"[lease_adapter] Uncertainty notes failed (non-fatal): {e}", flush=True)

    # Add key aliases for frontend/PDF compatibility
    models_used["extraction"] = models_used.get("extractor", "")
    models_used["severity"] = models_used.get("severity_assessor", "")

    # ── Build summary ──
    pipeline_elapsed = time.time() - pipeline_start
    summary = _compute_summary(dispositions)
    if crossref_warnings:
        summary["cross_reference_warnings"] = crossref_warnings

    result = {
        "run_id": run_id,
        "template_file": os.path.basename(template_path),
        "tenant_file": os.path.basename(tenant_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "1.0.0",
        "pipeline_domain": "commercial_lease_review",
        "pipeline_domain_label": "Commercial Lease Analysis",
        "models_used": models_used,
        "api_calls_total": total_api_calls,
        "elapsed_sec": round(pipeline_elapsed, 2),
        "contract_metadata": extraction.get("contract_metadata", {}),
        "deal_overview": extraction.get("deal_overview", {}),
        "full_template_text": template_text,
        "full_tenant_text": tenant_text,
        "summary": summary,
        "provisions": dispositions,
        "discoveries": discoveries,  # {"folded": [...], "standalone": [...]}
        "cam_contract_summary": cam_contract_summary,
        "analysis_completeness": analysis_completeness,
        "human_feedback": [],
        "coverage_assessment": coverage_assessment,
        "coverage_summary": coverage_summary,
        "exposure_summary": exposure_summary,
        "conflicts": conflicts,
        "jurisdiction": {
            "governing_law": governing_law,
            "escalations": escalation_log
        },
        "use_profile": use_profile_data,
        "use_analysis_status": use_analysis_status,
        # Raw stage data for auditability
        "_stage_data": {
            "extraction_meta": extraction["meta"],
            "evaluation_meta": evaluation["meta"],
            "evaluator_raw": {k: v.get("raw_evaluations", []) for k, v in evaluation["evaluators"].items()},
            "evaluator_prompts": {k: v.get("prompts", {}) for k, v in evaluation["evaluators"].items()},
            "discovery_raw": {k: v for k, v in evaluation.get("all_discoveries", {}).items()},
            "cascade_meta": cascade_result["meta"],
            "cascade_raw": cascade_result.get("raw_cascades", []),
            "challenge_meta": challenge_result["meta"],
            "challenge_raw": challenge_result.get("raw_challenges", []),
            "challenge_prompts": challenge_result.get("prompts", {}),
            "severity_meta": severity_result["meta"],
            "severity_raw": severity_result.get("raw_severities", []),
            "severity_prompts": severity_result.get("prompts", {}),
            "fragility": fragility,
            "triage": {
                "passed": [p["provision_id"] for p in passed],
                "flagged": [f["provision_id"] for f in flagged],
                "flagged_reasons": {f["provision_id"]: f.get("flag_reasons", []) for f in flagged},
            },
        },
    }

    # ── Save output ──
    output_dir = Path(cfg["output_dir"]) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pipeline_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[lease_adapter] Results saved to {output_path}", flush=True)

    # ── Generate annotated document outputs ──
    print("[lease_adapter] Generating output files...", flush=True)
    try:
        outputs = generate_outputs(tenant_path, result, str(output_dir))
        result["output_files"] = outputs
        if outputs.get("annotated_document"):
            print(f"[lease_adapter] Annotated document: {outputs['annotated_document']}", flush=True)
        # Re-save with output_files included
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[lease_adapter] Report generation failed (non-fatal): {e}", flush=True)
        result["output_files"] = {"error": str(e)}

    print(f"[lease_adapter] Pipeline complete: {total_api_calls} API calls in {round(pipeline_elapsed, 1)}s", flush=True)

    # ── Telemetry ──
    try:
        from cam.adapters.lease_review.lease_telemetry import emit as emit_telemetry
        emit_telemetry(result, cfg)
    except Exception as e:
        print(f"[lease_adapter] Telemetry emit failed (non-fatal): {e}", flush=True)

    return result


def run_lease_coverage_only(
    tenant_path: str,
    provisions: List[dict] = None,
    config: dict = None,
    run_id: str = None,
    progress_callback=None,
) -> dict:
    """Mode C pipeline: single-document coverage analysis.

    Skips Stages 1 alignment, 2-7 (rules, cascade, evaluators, challenge,
    severity, disposition) and runs only the Phase 5 coverage layer
    (negative space → coverage assessor → exposure).

    Output shape matches Mode A's pipeline_results.json with deviation-shaped
    fields populated as empty arrays (not null, not missing) so downstream
    consumers can treat the record uniformly.

    Args:
        tenant_path: Path to the lease document to analyze.
        provisions: Provision/issue-area list (defaults to full 18 LPs).
        config: Pipeline config dict.
        run_id: Optional run identifier for output directory naming.

    Returns:
        Pipeline results dict with mode="analyze".
    """
    from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc

    cfg = {**DEFAULT_CONFIG}
    if config:
        cfg.update(config)

    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("lease_analyze_%Y%m%d_%H%M%S")

    if provisions is None:
        provisions = get_active_provisions()

    print(f"[lease_adapter:analyze] Starting Mode C coverage analysis: run_id={run_id}", flush=True)
    print(f"[lease_adapter:analyze] Document: {os.path.basename(tenant_path)}", flush=True)
    print(f"[lease_adapter:analyze] Issue areas: {len(provisions)}", flush=True)

    pipeline_start = time.time()
    total_api_calls = 0
    models_used = {}

    # ── Parse document ──
    if progress_callback:
        progress_callback(1, 3, "Parsing document.")
    print("[lease_adapter:analyze] Parsing document...", flush=True)
    parse_start = time.time()
    tenant_text = parse_document(tenant_path)
    parse_elapsed = time.time() - parse_start
    tenant_word_count = len(tenant_text.split())
    cfg["tenant_word_count"] = tenant_word_count
    print(
        f"[lease_adapter:analyze] Document: {len(tenant_text)} chars "
        f"({tenant_word_count} words) | parse {parse_elapsed:.2f}s",
        flush=True,
    )

    # ── Document Gate Check ──
    print("[lease_adapter:analyze] Gate: classifying document...", flush=True)
    gate_result = check_document_is_lease(tenant_text, cfg)
    print(f"[lease_adapter:analyze] Gate: is_lease={gate_result['is_lease']} in {gate_result['elapsed_sec']}s", flush=True)
    if gate_result.get("abort"):
        raise GateAbortError(gate_result["abort_message"])

    _check_cancel(cfg)

    # ── Single-document extraction ──
    if progress_callback:
        progress_callback(2, 3, "Extracting provisions.")
    print("[lease_adapter:analyze] Single-document extraction...", flush=True)
    extraction = extract_provisions_single_doc(tenant_text, provisions, cfg)
    total_api_calls += 1
    models_used["extractor"] = extraction["meta"]["model"]
    models_used["extractor_provider"] = extraction["meta"].get("provider", "")
    models_used["extractor_fallback_used"] = extraction["meta"].get("fallback_used", False)
    models_used["extraction"] = models_used["extractor"]
    print(
        f"[lease_adapter:analyze] Extraction complete: "
        f"{len(extraction['provisions'])} provisions in {extraction['meta']['elapsed_sec']}s",
        flush=True,
    )

    _check_cancel(cfg)

    # ── Phase 5: negative-space → coverage → exposure ──
    if progress_callback:
        progress_callback(3, 3, "Analyzing coverage.")
    coverage_assessment = []
    coverage_summary = {}
    negative_space_by_provision = {}
    exposure_summary = {}

    try:
        from cam.adapters.lease_review.lease_negative_space import (
            detect_negative_space, summarize_negative_space,
        )
        from cam.adapters.lease_review.lease_coverage import (
            assess_coverage, summarize_coverage,
        )
        negative_space_by_provision = detect_negative_space(
            extraction["provisions"], tenant_text,
        )
        _job_id_c = cfg.get("_job_id")
        def _lp_progress_cb_c(lp_id, lp_name, state):
            if _job_id_c:
                try:
                    from app.job_manager import update_lp_progress
                    update_lp_progress(_job_id_c, lp_id, lp_name, state)
                except Exception:
                    pass
        coverage_assessment = assess_coverage(
            extraction["provisions"], tenant_text, negative_space_by_provision,
            lp_progress_callback=_lp_progress_cb_c,
        )
        coverage_summary = summarize_coverage(coverage_assessment)
        ns_summary = summarize_negative_space(negative_space_by_provision)
        print(
            f"[lease_adapter:analyze] Coverage: "
            f"{coverage_summary.get('covered_count', 0)} covered, "
            f"{coverage_summary.get('attention_count', 0)} require attention, "
            f"{coverage_summary.get('not_applicable_count', 0)} not applicable | "
            f"neg-space: {ns_summary.get('total_signals', 0)} signals across "
            f"{ns_summary.get('provisions_with_signals', 0)} provisions",
            flush=True,
        )
    except Exception as e:
        print(f"[lease_adapter:analyze] Coverage assessment failed: {e}", flush=True)
        coverage_assessment = []
        coverage_summary = {}
        negative_space_by_provision = {}

    # ── Stage 5b: Jurisdiction-aware escalation (Step 297a) ──
    governing_law_c = None
    escalation_log_c = []
    conflicts_c = []
    try:
        from cam.adapters.lease_review import lease_jurisdiction
        governing_law_c = lease_jurisdiction.extract_governing_law(
            coverage_assessment,
            provisions=extraction.get("provisions"),
            contract_metadata=extraction.get("contract_metadata")
        )
        if governing_law_c:
            print(f"[lease_adapter:analyze] Detected governing law: {governing_law_c}", flush=True)
            coverage_assessment, escalation_log_c = lease_jurisdiction.apply_jurisdiction_rules(
                coverage_assessment,
                governing_law=governing_law_c,
                provisions=extraction.get("provisions"),
                contract_metadata=extraction.get("contract_metadata")
            )
            if escalation_log_c:
                print(f"[lease_adapter:analyze] Applied {len(escalation_log_c)} jurisdiction escalation(s)", flush=True)
                for entry in escalation_log_c:
                    print(f"[lease_adapter:analyze]   {entry['lp_id']}: {entry['from']} -> {entry['to']}", flush=True)
            else:
                print(f"[lease_adapter:analyze] No escalations triggered for {governing_law_c}", flush=True)
        else:
            print("[lease_adapter:analyze] No governing law detected — skipping jurisdiction rules", flush=True)
    except Exception as e:
        print(f"[lease_adapter:analyze] Jurisdiction engine failed (non-fatal): {e}", flush=True)

    # Step 298c: Rebuild coverage_summary with post-escalation states.
    if escalation_log_c:
        coverage_summary = summarize_coverage(coverage_assessment)
        _ATTN_SORT_298C = {
            "potentially_unenforceable": 0,
            "covered_unfavorable": 1,
            "missing": 2,
            "broken_xref": 3,
            "partial": 4,
            "ambiguous": 5,
            "review_needed": 6,
        }
        coverage_summary.get("attention_items", []).sort(
            key=lambda x: _ATTN_SORT_298C.get(x["state"], 99)
        )

    # ── Stage 5d: Use-Aware Coverage Classification (Step 301 / gated 301a) ──
    use_profile_data_c = None
    use_analysis_status_c = "disabled"
    use_adjustment_log_c: list = []
    from cam.adapters.lease_review.lease_use_aware_coverage import STAGE_5D_ENABLED
    if not STAGE_5D_ENABLED:
        print(
            "[lease_adapter:analyze] Stage 5d: gated (single-eval unstable; awaiting Step 302 multi-eval)",
            flush=True,
        )
    else:
        try:
            from cam.adapters.lease_review.lease_use_aware_coverage import (
                should_run_use_analysis, generate_use_profile, assess_use_aware_coverage,
            )
            _use_clause_c = (extraction.get("contract_metadata") or {}).get("permitted_use", "")
            if should_run_use_analysis(_use_clause_c):
                print(f"[lease_adapter:analyze] Stage 5d: generating use profile...", flush=True)
                use_profile_data_c = generate_use_profile(_use_clause_c)
                if use_profile_data_c:
                    coverage_assessment, use_adjustment_log_c = assess_use_aware_coverage(
                        use_profile_data_c, coverage_assessment, cfg
                    )
                    if use_adjustment_log_c:
                        coverage_summary = summarize_coverage(coverage_assessment)
                        _ATTN_SORT_C = {"potentially_unenforceable": 0, "covered_unfavorable": 1,
                                        "missing": 2, "broken_xref": 3, "partial": 4,
                                        "ambiguous": 5, "review_needed": 6}
                        coverage_summary.get("attention_items", []).sort(
                            key=lambda x: _ATTN_SORT_C.get(x["state"], 99)
                        )
                        print(
                            f"[lease_adapter:analyze] Stage 5d: "
                            f"{len(use_adjustment_log_c)} use-adjustment(s) applied",
                            flush=True,
                        )
                    else:
                        print("[lease_adapter:analyze] Stage 5d: no adjustments applied", flush=True)
                    use_analysis_status_c = "applied"
                else:
                    use_analysis_status_c = "skipped_call1_failed"
            else:
                print("[lease_adapter:analyze] Stage 5d: skipped (use clause absent or generic)",
                      flush=True)
                use_analysis_status_c = "not_applicable"
        except Exception as e:
            print(f"[lease_adapter:analyze] Stage 5d failed (non-fatal): {e}", flush=True)

    # ── Stage 5c: Cross-provision conflict detection (Step 297a) ──
    try:
        from cam.adapters.lease_review import lease_conflicts
        conflicts_c = lease_conflicts.detect_conflicts(
            coverage_assessment,
            provisions=extraction.get("provisions"),
            perspective=cfg.get("perspective", "tenant")
        )
        print(f"[lease_conflicts] Detected {len(conflicts_c)} conflict(s)", flush=True)
        for c in conflicts_c:
            print(f"[lease_conflicts]   {c['id']}: {c['name']} ({c['severity']})", flush=True)
    except Exception as e:
        print(f"[lease_adapter:analyze] Conflict engine failed (non-fatal): {e}", flush=True)

    if coverage_assessment:
        try:
            from cam.adapters.lease_review.lease_exposure import (
                generate_exposure, summarize_exposure,
            )
            exposure_calls_before = total_api_calls
            generate_exposure(coverage_assessment, cfg)
            exposure_summary = summarize_exposure(coverage_assessment)
            exposure_model_calls = exposure_summary.get("model_calls", 0)
            total_api_calls += exposure_model_calls
            if exposure_model_calls:
                models_used["exposure"] = cfg.get("exposure_model", "")
            print(
                f"[lease_adapter:analyze] Exposure: "
                f"{exposure_summary.get('model_calls', 0)} model, "
                f"{exposure_summary.get('schema_only', 0)} schema | "
                f"material={exposure_summary.get('partial_material', 0)} "
                f"review={exposure_summary.get('partial_review', 0)} "
                f"typical={exposure_summary.get('partial_typical', 0)}",
                flush=True,
            )
        except Exception as e:
            print(f"[lease_adapter:analyze] Exposure engine failed: {e}", flush=True)
            exposure_summary = {}

    pipeline_elapsed = time.time() - pipeline_start

    # ── Assemble result (deviation-shaped fields empty, not missing) ──
    result = {
        "run_id": run_id,
        "mode": "analyze",
        "template_file": "",
        "tenant_file": os.path.basename(tenant_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "1.0.0",
        "pipeline_domain": "commercial_lease_review",
        "pipeline_domain_label": "Commercial Lease Coverage Analysis",
        "models_used": models_used,
        "api_calls_total": total_api_calls,
        "elapsed_sec": round(pipeline_elapsed, 2),
        "contract_metadata": extraction.get("contract_metadata", {}),
        "deal_overview": extraction.get("deal_overview", {}),
        "full_template_text": "",
        "full_tenant_text": tenant_text,
        "summary": {
            "total_provisions_checked": len(extraction["provisions"]),
            "conforms": 0,
            "deviates": 0,
            "unclear": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        },
        "provisions": [],
        "deviations": [],
        "cascade_findings": [],
        "challenge_findings": [],
        "severity_assignments": [],
        "dispositions": [],
        "discoveries": {"folded": [], "standalone": []},
        "cam_contract_summary": {},
        "analysis_completeness": {},
        "human_feedback": [],
        "coverage_assessment": coverage_assessment,
        "coverage_summary": coverage_summary,
        "exposure_summary": exposure_summary,
        "conflicts": conflicts_c,
        "jurisdiction": {
            "governing_law": governing_law_c,
            "escalations": escalation_log_c
        },
        "use_profile": use_profile_data_c,
        "use_analysis_status": use_analysis_status_c,
        "_stage_data": {
            "extraction_meta": extraction["meta"],
            "negative_space": negative_space_by_provision,
        },
    }

    output_dir = Path(cfg["output_dir"]) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pipeline_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[lease_adapter:analyze] Results saved to {output_path}", flush=True)

    try:
        from cam.adapters.lease_review.lease_telemetry import emit as emit_telemetry
        emit_telemetry(result, cfg)
    except Exception as e:
        print(f"[lease_adapter:analyze] Telemetry emit failed (non-fatal): {e}", flush=True)

    print(
        f"[lease_adapter:analyze] Pipeline complete: "
        f"{total_api_calls} API call(s) in {round(pipeline_elapsed, 1)}s",
        flush=True,
    )

    return result


def _compute_summary(dispositions: List[dict]) -> dict:
    """Compute summary statistics from dispositions."""
    total = len(dispositions)
    conforms = sum(1 for d in dispositions if d["final_verdict"] == "CONFORMS")
    deviates = sum(1 for d in dispositions if d["final_verdict"] == "DEVIATES")
    unclear = sum(1 for d in dispositions if d["final_verdict"] == "UNCLEAR")

    critical = sum(1 for d in dispositions if d.get("severity") == "CRITICAL")
    high = sum(1 for d in dispositions if d.get("severity") == "HIGH")
    medium = sum(1 for d in dispositions if d.get("severity") == "MEDIUM")
    low = sum(1 for d in dispositions if d.get("severity") == "LOW")

    return {
        "total_provisions_checked": total,
        "conforms": conforms,
        "deviates": deviates,
        "unclear": unclear,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
    }


# ── CLI entry point ──
if __name__ == "__main__":
    import sys

    find_and_load_env()

    test_data_dir = CAM_ROOT / "05 Lease Analyzer" / "test_data"
    template = str(test_data_dir / "standard_template.txt")

    tenant_file = "T-04_subtle.txt"
    if len(sys.argv) > 1:
        tenant_file = sys.argv[1]

    tenant = str(test_data_dir / "tenants" / tenant_file)

    result = run_lease_analysis(
        template_path=template,
        tenant_path=tenant,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    s = result["summary"]
    print(f"Total: {s['total_provisions_checked']} | Conforms: {s['conforms']} | Deviates: {s['deviates']} | Unclear: {s['unclear']}")
    print(f"Critical: {s['critical']} | High: {s['high']} | Medium: {s['medium']} | Low: {s['low']}")
    print(f"\nAPI calls: {result['api_calls_total']} | Time: {result['elapsed_sec']}s")
    print(f"Models: {result['models_used']}")

    print("\nPER-PROVISION:")
    for d in result["provisions"]:
        triage = d["cam_metadata"]["triage_result"]
        verdict = d["final_verdict"]
        sev = d["severity"]
        pattern = d["agreement_pattern"]
        marker = ""
        if verdict == "DEVIATES":
            marker = f" [{sev}]"
        print(f"  {d['provision_id']} {d['provision_name']}: {verdict}{marker} ({pattern}) triage={triage}")
        if d.get("cascade_verdict"):
            print(f"    Cascade: {d['cascade_verdict']}")
        if d.get("challenge_finding"):
            print(f"    Challenge: {d['challenge_finding']}")
        if d["fragility"]["fragile"]:
            sigs = ", ".join(d["fragility"]["signals"])
            print(f"    Fragility: {sigs}")
