"""
CAM SciFact -- Conviction Test (Step 014c)

Gold label adjudication: re-query evaluators whose Stage 1 verdict
disagrees with the gold label. Show them their original verdict plus
the gold label (called "reference label"), and ask whether they
MAINTAIN or REVISE.

Anti-sycophancy measures:
- Reference label is explicitly described as potentially wrong.
- MAINTAIN is option A (psychologically easier to pick first).
- REVISE requires admitting a specific analytical error.
- Scoring framing ("you earn a point") discourages deference.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.core.utilities import log
from cam.core.json_extract import safe_json_extract


# ============================================================
# The 5 mismatched claims and their gold labels
# ============================================================

CONVICTION_CLAIMS = {
    1132: "SUPPORT",
    236:  "SUPPORT",
    847:  "CONTRADICT",
    1020: "SUPPORT",
    415:  "SUPPORT",
}

# Evaluator labels
EVALUATOR_LABELS = ["A", "B", "C"]

# Evaluator model configs (same as SCIFACT_EVALUATORS in scifact_adapter.py)
EVALUATOR_CONFIGS = {
    "A": {"name": "anthropic:claude-sonnet-4-5", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    "B": {"name": "google:gemini-3-pro-preview", "provider": "google", "model": "gemini-3-pro-preview"},
    "C": {"name": "xai:grok", "provider": "xai", "model": "grok-3"},
}


def _load_stage1_evaluator(source_run_dir, claim_id, evaluator_label):
    """
    Load a single evaluator's Stage 1 JSON from the source run.
    Returns the full JSON dict or None.
    """
    path = Path(source_run_dir) / "raw" / f"claim_{claim_id}" / f"evaluator_{evaluator_label}.json"
    if not path.exists():
        log(f"  WARNING: evaluator file not found: {path}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _should_test(evaluator_verdict, gold_label):
    """Return True if this evaluator's original verdict disagrees with gold."""
    return evaluator_verdict != gold_label


def run_conviction_test(source_run_name="1 SciFact Run"):
    """
    Run conviction test on the 5 mismatched claims.

    For each claim, loads each evaluator's Stage 1 verdict and reasoning.
    Only tests evaluators whose original verdict disagrees with gold.
    Calls each evaluator with the conviction prompt + their original reasoning.
    Records MAINTAIN/REVISE decisions.

    Args:
        source_run_name: Name of the source run directory containing Stage 1 raw data.
    """
    from cam.core.provider_router import ProviderRouter, ModelTarget

    find_and_load_env()

    source_dir = CAM_ROOT / "03 SciFact" / "Runs" / source_run_name

    # Load conviction prompt template
    prompt_path = Path(__file__).parent / "prompts" / "conviction_test.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Load dataset for abstract + claim text lookup
    from cam.adapters.scifact.scifact_adapter import (
        load_scifact_dataset,
        extract_claim_data,
        _lookup_abstract_for_claim,
    )
    claims_by_split, corpus_lookup = load_scifact_dataset()

    # Build claim text lookup for the 5 claims
    claim_text_lookup = {}
    val_split = claims_by_split.get("validation", [])
    for record in val_split:
        cid = record["id"]
        if cid in CONVICTION_CLAIMS:
            cdata = extract_claim_data(record, corpus_lookup)
            claim_text_lookup[cid] = cdata["claim_text"]

    # Create output directory
    out_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1c SciFact Adjudication"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM SciFact -- Conviction Test (Gold Label Adjudication)")
    log("=" * 70)
    log(f"  Source run: {source_dir.name}")
    log(f"  Claims to test: {list(CONVICTION_CLAIMS.keys())}")
    log("")

    # Build evaluator routers (one per evaluator for provider isolation)
    routers = {}
    for label, config in EVALUATOR_CONFIGS.items():
        target = ModelTarget(
            name=config["name"],
            provider=config["provider"],
            model=config["model"],
            priority=1,
            max_output_tokens=4096,
            temperature=0.0,
            timeout_sec=120.0,
        )
        routers[label] = ProviderRouter(targets=[target])

    # ---- Run conviction tests ----
    all_results = []
    api_call_count = 0
    skipped_count = 0

    for claim_id, gold_label in CONVICTION_CLAIMS.items():
        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"  ERROR: Could not find abstract for claim {claim_id}")
            continue

        print()
        print("=" * 70)
        print(f"  Conviction Test: Claim {claim_id} (gold: {gold_label})")
        print("=" * 70)

        # Get claim text
        claim_text = claim_text_lookup.get(claim_id, f"[Claim {claim_id}]")
        print(f"  Claim: {claim_text[:120]}...")

        for evaluator_label in EVALUATOR_LABELS:
            # Load this evaluator's Stage 1 data
            eval_data = _load_stage1_evaluator(source_dir, claim_id, evaluator_label)
            if eval_data is None:
                continue

            normalized = eval_data.get("normalized", {})
            original_verdict = normalized.get("verdict", "UNKNOWN")
            original_reasoning = normalized.get("reasoning", "No reasoning available.")

            # Only test evaluators whose verdict disagrees with gold
            if not _should_test(original_verdict, gold_label):
                print(f"    Evaluator {evaluator_label}: {original_verdict} matches gold ({gold_label}) -- skipping")
                skipped_count += 1
                continue

            # Build conviction prompt
            prompt = prompt_template.replace("{claim_text}", claim_text)
            prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
            prompt = prompt.replace("{evaluator_verdict}", original_verdict)
            prompt = prompt.replace("{evaluator_reasoning}", original_reasoning)
            prompt = prompt.replace("{gold_label}", gold_label)

            print(f"    Evaluator {evaluator_label} ({EVALUATOR_CONFIGS[evaluator_label]['name']}): "
                  f"original={original_verdict}, gold={gold_label}")

            # Call evaluator
            router = routers[evaluator_label]
            conviction_result = None
            meta = None
            raw_response = ""

            for attempt in range(1, 3):
                try:
                    raw_obj, meta = router.call_json(
                        system_prompt="You are a scientific claim verification evaluator. Respond only with valid JSON.",
                        user_prompt=prompt,
                    )
                    raw_response = json.dumps(raw_obj)
                    conviction_result = _normalize_conviction_response(raw_obj)
                    api_call_count += 1
                    log(f"      Attempt {attempt}: decision={conviction_result.get('decision', '???')}, "
                        f"confidence={conviction_result.get('confidence', '???')}")
                    break
                except Exception as e:
                    log(f"      Attempt {attempt} failed: {e}")
                    if attempt == 2:
                        conviction_result = {"error": f"API call failed after 2 attempts: {e}"}
                        api_call_count += 1

            # Display result
            if conviction_result and "decision" in conviction_result:
                decision = conviction_result["decision"]
                confidence = conviction_result.get("confidence", "?")
                marker = "HOLD" if decision == "MAINTAIN" else "CAVE"
                print(f"      -> {decision} ({confidence}) [{marker}]")
                reasoning_preview = conviction_result.get("reasoning", "")[:100]
                print(f"         {reasoning_preview}...")
            else:
                print(f"      -> ERROR: {conviction_result}")

            # Save raw output
            raw_file = raw_dir / f"claim_{claim_id}_conviction_{evaluator_label}.json"
            with open(raw_file, "w", encoding="utf-8") as f:
                json.dump({
                    "claim_id": claim_id,
                    "gold_label": gold_label,
                    "evaluator_label": evaluator_label,
                    "evaluator_config": EVALUATOR_CONFIGS[evaluator_label],
                    "original_verdict": original_verdict,
                    "original_reasoning": original_reasoning,
                    "conviction_result": conviction_result,
                    "raw_response": raw_response,
                    "meta": meta,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, f, indent=2, default=str)

            # Collect for summary
            all_results.append({
                "claim_id": claim_id,
                "gold_label": gold_label,
                "evaluator_label": evaluator_label,
                "original_verdict": original_verdict,
                "decision": conviction_result.get("decision", "ERROR") if conviction_result else "ERROR",
                "confidence": conviction_result.get("confidence", "?") if conviction_result else "?",
                "reasoning": conviction_result.get("reasoning", "") if conviction_result else "",
                "reference_label_assessment": conviction_result.get("reference_label_assessment", "") if conviction_result else "",
                "specific_textual_basis": conviction_result.get("specific_textual_basis", "") if conviction_result else "",
            })

    log("")
    log(f"  Total API calls: {api_call_count}")
    log(f"  Skipped (matched gold): {skipped_count}")

    # ---- Save JSONL results ----
    results_file = out_dir / "conviction_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"  Results saved to {results_file}")

    # ---- Compute per-claim tally and three-tier metrics ----
    _compute_and_save_summary(all_results, out_dir)
    _compute_three_tier_metrics(all_results, out_dir)

    return all_results


def _normalize_conviction_response(raw_obj):
    """Normalize conviction test response. Validate required fields."""
    if isinstance(raw_obj, str):
        raw_obj = safe_json_extract(raw_obj)

    result = {}

    # Decision
    decision = raw_obj.get("decision", "")
    if isinstance(decision, str):
        decision = decision.upper().strip()
    if decision in ("MAINTAIN", "A"):
        result["decision"] = "MAINTAIN"
    elif decision in ("REVISE", "B"):
        result["decision"] = "REVISE"
    else:
        result["decision"] = decision  # keep raw for debugging

    # Other fields
    result["reasoning"] = raw_obj.get("reasoning", "")
    result["specific_textual_basis"] = raw_obj.get("specific_textual_basis", "")
    result["reference_label_assessment"] = raw_obj.get("reference_label_assessment", "")

    confidence = raw_obj.get("confidence", "")
    if isinstance(confidence, str):
        confidence = confidence.lower().strip()
    result["confidence"] = confidence if confidence in ("high", "medium", "low") else "unknown"

    return result


def _compute_and_save_summary(all_results, out_dir):
    """Compute per-claim tally and save conviction_summary.txt.

    Uses no-majority-vote scoring:
    - reinforced:         all MAINTAIN -> no cap
    - fragile_conviction: any REVISE present -> cap L2
    - weak_conviction:    majority REVISE -> cap L3
    - collapse:           all REVISE -> WITHHOLD
    """
    from collections import defaultdict

    # Group by claim_id
    by_claim = defaultdict(list)
    for r in all_results:
        by_claim[r["claim_id"]].append(r)

    lines = [
        "",
        "=" * 70,
        "  Conviction Test Summary (no majority vote)",
        "=" * 70,
        "",
        "  Scoring: any single REVISE triggers a fragility signal.",
        "  Only unanimous MAINTAIN = reinforced. No majority vote.",
        "",
        "  Signal categories:",
        "    reinforced         = all MAINTAIN -> no cap",
        "    fragile_conviction = any REVISE present -> cap L2",
        "    weak_conviction    = majority REVISE -> cap L3",
        "    collapse           = all REVISE -> WITHHOLD",
        "",
    ]

    for claim_id in CONVICTION_CLAIMS:
        gold = CONVICTION_CLAIMS[claim_id]
        entries = by_claim.get(claim_id, [])
        valid = [e for e in entries if e.get("decision") in ("MAINTAIN", "REVISE")]
        n_maintain = sum(1 for e in valid if e["decision"] == "MAINTAIN")
        n_revise = sum(1 for e in valid if e["decision"] == "REVISE")
        n_total = len(valid)
        n_error = len(entries) - n_total

        # Compute signal using the actual function
        sig = compute_conviction_signal(claim_id, entries)
        signal_type = sig["signal_type"] if sig else "no_data"
        cap_effect = sig["cap_effect"] if sig else None
        cap_str = f" -> {cap_effect}" if cap_effect else " -> no cap"

        lines.append(f"  Claim {claim_id} (gold={gold}):")
        lines.append(f"    Tested: {n_total} valid, {n_error} errors")
        lines.append(f"    MAINTAIN: {n_maintain}, REVISE: {n_revise}")
        lines.append(f"    Signal: {signal_type}{cap_str}")

        # Detail per evaluator
        for e in entries:
            conf = e.get("confidence", "?")
            decision = e.get("decision", "ERROR")
            lines.append(f"      Eval {e['evaluator_label']}: {decision} (confidence={conf})")
            # Show reasoning preview
            reasoning = e.get("reasoning", "")[:120]
            if reasoning:
                lines.append(f"        {reasoning}...")
            ref_assessment = e.get("reference_label_assessment", "")[:120]
            if ref_assessment:
                lines.append(f"        Ref label: {ref_assessment}...")

        lines.append("")

    lines.append("=" * 70)

    summary_text = "\n".join(lines)
    print(summary_text)

    summary_file = out_dir / "conviction_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_text)
    log(f"  Summary saved to {summary_file}")


def _compute_three_tier_metrics(all_results, out_dir):
    """
    Compute three-tier CCA metrics and save three_tier_metrics.txt.

    CCA-gold: 38/43 = 88.4% (from the 50-claim run, 43 evaluable, 5 mismatches)
    CCA-AI-adjudicated: Reclassify ONLY claims where ALL tested evaluators
        MAINTAIN (unanimous). Any single REVISE disqualifies reclassification.
        No majority vote -- consistent with CAM philosophy.
    CCA-human-adjudicated: Placeholder for Tzvi
    """
    from collections import defaultdict

    # Group by claim_id
    by_claim = defaultdict(list)
    for r in all_results:
        by_claim[r["claim_id"]].append(r)

    # Base numbers from 50-claim run
    total_evaluable = 43
    base_matches = 38  # 38/43 matched gold before adjudication

    # Count reclassifications (unanimous MAINTAIN only -> CAM correct)
    reclassified = 0
    reclassification_detail = []

    for claim_id in CONVICTION_CLAIMS:
        entries = by_claim.get(claim_id, [])
        valid = [e for e in entries if e.get("decision") in ("MAINTAIN", "REVISE")]
        n_maintain = sum(1 for e in valid if e["decision"] == "MAINTAIN")
        n_revise = sum(1 for e in valid if e["decision"] == "REVISE")

        if n_revise == 0 and n_maintain > 0:
            # All tested evaluators MAINTAIN -- reclassify as CAM correct
            reclassified += 1
            reclassification_detail.append(
                f"  Claim {claim_id}: ALL MAINTAIN ({n_maintain}-{n_revise}) "
                f"-> reclassified as CAM correct"
            )
        elif n_revise > 0:
            reclassification_detail.append(
                f"  Claim {claim_id}: has REVISE ({n_maintain}-{n_revise}) "
                f"-> remains mismatch (any REVISE disqualifies)"
            )
        else:
            reclassification_detail.append(
                f"  Claim {claim_id}: no valid responses -> remains mismatch"
            )

    ai_adjudicated_matches = base_matches + reclassified
    cca_gold = base_matches / total_evaluable * 100
    cca_ai = ai_adjudicated_matches / total_evaluable * 100

    lines = [
        "",
        "=" * 70,
        "  Three-Tier CCA Metrics (no majority vote)",
        "=" * 70,
        "",
        f"  Total evaluable claims: {total_evaluable}",
        f"  Gold label mismatches: {total_evaluable - base_matches}",
        "",
        f"  Reclassification rule: only unanimous MAINTAIN (no majority vote)",
        "",
        f"  CCA-gold:            {base_matches}/{total_evaluable} = {cca_gold:.1f}%",
        f"  CCA-AI-adjudicated:  {ai_adjudicated_matches}/{total_evaluable} = {cca_ai:.1f}%",
        f"  CCA-human-adjudicated: [PLACEHOLDER -- Tzvi to fill in after review]",
        "",
        "  AI Adjudication Detail:",
    ]

    lines.extend(reclassification_detail)

    lines.append("")
    lines.append(f"  Claims reclassified by AI conviction: {reclassified}/{total_evaluable - base_matches}")
    lines.append(f"  Remaining mismatches after AI adjudication: {(total_evaluable - base_matches) - reclassified}")
    lines.append("")
    lines.append("=" * 70)

    metrics_text = "\n".join(lines)
    print(metrics_text)

    metrics_file = out_dir / "three_tier_metrics.txt"
    with open(metrics_file, "w", encoding="utf-8") as f:
        f.write(metrics_text)
    log(f"  Metrics saved to {metrics_file}")


# ============================================================
# Step 014c-fix: Gemini Retry + Conviction Integration
# ============================================================

# Shorter conviction prompt for Gemini (trimmed reasoning, fewer fields)
GEMINI_CONVICTION_PROMPT = """You previously evaluated the following scientific claim against an abstract.

CLAIM: {claim_text}

ABSTRACT:
{formatted_abstract}

YOUR ORIGINAL VERDICT: {evaluator_verdict}
YOUR ORIGINAL REASONING (excerpt): {evaluator_reasoning}

A reference label from a separate annotation process indicates the verdict should be: {gold_label}

This reference label may or may not be correct. Reference annotations can contain errors.

Based strictly on what the abstract states, do you:

(A) MAINTAIN your original verdict -- explain why your reading is correct and the reference label is wrong.

(B) REVISE to the reference label -- explain what you missed or got wrong.

You must choose A or B. Your response will be scored for accuracy.

IMPORTANT: Your response must be a single valid JSON object. Keep your reasoning concise (2-3 sentences per field). Do not write anything before or after the JSON.

{{"decision": "MAINTAIN or REVISE", "reasoning": "Why (2-3 sentences)", "reference_label_assessment": "Why reference is wrong/right (1-2 sentences)", "confidence": "high/medium/low"}}"""


def run_gemini_conviction_retry(source_run_name="1 SciFact Run"):
    """
    Retry conviction test for Gemini only (all 5 claims).
    Uses shorter prompt + trimmed reasoning to avoid JSON truncation.

    Returns list of Gemini conviction results.
    """
    from cam.core.provider_router import ProviderRouter, ModelTarget

    find_and_load_env()

    source_dir = CAM_ROOT / "03 SciFact" / "Runs" / source_run_name

    # Load dataset for abstract + claim text lookup
    from cam.adapters.scifact.scifact_adapter import (
        load_scifact_dataset,
        extract_claim_data,
        _lookup_abstract_for_claim,
    )
    claims_by_split, corpus_lookup = load_scifact_dataset()

    # Build claim text lookup
    claim_text_lookup = {}
    val_split = claims_by_split.get("validation", [])
    for record in val_split:
        cid = record["id"]
        if cid in CONVICTION_CLAIMS:
            cdata = extract_claim_data(record, corpus_lookup)
            claim_text_lookup[cid] = cdata["claim_text"]

    # Output directory
    out_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1d SciFact Conviction-Integrated"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM SciFact -- Gemini Conviction Retry")
    log("=" * 70)

    # Setup Gemini router with lower max_output_tokens
    gemini_config = EVALUATOR_CONFIGS["B"]
    target = ModelTarget(
        name=gemini_config["name"],
        provider=gemini_config["provider"],
        model=gemini_config["model"],
        priority=1,
        max_output_tokens=2048,  # Lower to prevent truncation
        temperature=0.0,
        timeout_sec=120.0,
    )
    router = ProviderRouter(targets=[target])

    gemini_results = []
    api_call_count = 0

    for claim_id, gold_label in CONVICTION_CLAIMS.items():
        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"  ERROR: Could not find abstract for claim {claim_id}")
            continue

        # Load Gemini's Stage 1 data
        eval_data = _load_stage1_evaluator(source_dir, claim_id, "B")
        if eval_data is None:
            log(f"  ERROR: No Gemini evaluator file for claim {claim_id}")
            continue

        normalized = eval_data.get("normalized", {})
        original_verdict = normalized.get("verdict", "UNKNOWN")
        original_reasoning = normalized.get("reasoning", "No reasoning available.")

        # Skip if Gemini's verdict matches gold (same logic as original)
        if not _should_test(original_verdict, gold_label):
            log(f"  Claim {claim_id}: Gemini verdict {original_verdict} matches gold -- skipping")
            continue

        # Trim reasoning to 500 chars max
        trimmed_reasoning = original_reasoning[:500]
        if len(original_reasoning) > 500:
            trimmed_reasoning += "..."

        # Build shorter prompt
        claim_text = claim_text_lookup.get(claim_id, f"[Claim {claim_id}]")
        prompt = GEMINI_CONVICTION_PROMPT.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{evaluator_verdict}", original_verdict)
        prompt = prompt.replace("{evaluator_reasoning}", trimmed_reasoning)
        prompt = prompt.replace("{gold_label}", gold_label)

        print(f"\n  Gemini retry: Claim {claim_id} (original={original_verdict}, gold={gold_label})")

        # Call Gemini
        conviction_result = None
        meta = None
        raw_response = ""

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a scientific claim verification evaluator. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                conviction_result = _normalize_conviction_response(raw_obj)
                api_call_count += 1
                log(f"    Attempt {attempt}: decision={conviction_result.get('decision', '???')}, "
                    f"confidence={conviction_result.get('confidence', '???')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    conviction_result = {"error": f"API call failed after 2 attempts: {e}"}
                    api_call_count += 1

        # Display result
        if conviction_result and "decision" in conviction_result:
            decision = conviction_result["decision"]
            confidence = conviction_result.get("confidence", "?")
            marker = "HOLD" if decision == "MAINTAIN" else "CAVE"
            print(f"    -> {decision} ({confidence}) [{marker}]")
        else:
            print(f"    -> ERROR: {conviction_result}")

        # Save raw
        raw_file = raw_dir / f"claim_{claim_id}_conviction_gemini_retry.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "gold_label": gold_label,
                "evaluator_label": "B",
                "evaluator_config": gemini_config,
                "original_verdict": original_verdict,
                "original_reasoning": trimmed_reasoning,
                "conviction_result": conviction_result,
                "raw_response": raw_response,
                "meta": meta,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry": True,
            }, f, indent=2, default=str)

        gemini_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "evaluator_label": "B",
            "original_verdict": original_verdict,
            "decision": conviction_result.get("decision", "ERROR") if conviction_result else "ERROR",
            "confidence": conviction_result.get("confidence", "?") if conviction_result else "?",
            "reasoning": conviction_result.get("reasoning", "") if conviction_result else "",
            "reference_label_assessment": conviction_result.get("reference_label_assessment", "") if conviction_result else "",
        })

    log(f"\n  Gemini retry: {api_call_count} API calls")

    # Save Gemini retry results
    gemini_file = out_dir / "gemini_retry_results.jsonl"
    with open(gemini_file, "w", encoding="utf-8") as f:
        for r in gemini_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"  Gemini retry results saved to {gemini_file}")

    return gemini_results


def _merge_conviction_results(original_results_path, gemini_retry_results):
    """
    Merge original conviction results with Gemini retry results.
    Replaces ERROR entries for evaluator B with retry results.
    Returns merged list.
    """
    originals = []
    with open(original_results_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                originals.append(json.loads(line))

    # Build Gemini retry lookup
    retry_lookup = {}
    for r in gemini_retry_results:
        retry_lookup[r["claim_id"]] = r

    merged = []
    for orig in originals:
        cid = orig["claim_id"]
        label = orig["evaluator_label"]
        # Replace Gemini ERROR entries with retry
        if label == "B" and orig.get("decision") == "ERROR" and cid in retry_lookup:
            retry = retry_lookup[cid]
            merged.append(retry)
        else:
            merged.append(orig)

    return merged


# ============================================================
# Conviction signal for fragility integration
# ============================================================

# Conviction signal -> fragility effect mapping
# No majority vote. Any REVISE is a fragility signal. Disagreement is preserved.
CONVICTION_SIGNAL_MAP = {
    "reinforced":         None,      # All available MAINTAIN -> no cap change
    "fragile_conviction": "cap_L2",  # Any REVISE present -> cap at L2
    "weak_conviction":    "cap_L3",  # Majority REVISE -> cap at L3
    "collapse":           "cap_L4",  # All REVISE -> WITHHOLD
}


def compute_conviction_signal(claim_id, conviction_entries):
    """
    Compute a conviction fragility signal for a single claim.

    No majority vote. Any single REVISE triggers a fragility signal,
    consistent with CAM's core philosophy of preserving disagreement.

    Signal categories:
        reinforced:         all available evaluators MAINTAIN -> no cap
        fragile_conviction: any REVISE present (but not majority) -> cap L2
        weak_conviction:    majority REVISE -> cap L3
        collapse:           all REVISE -> WITHHOLD (cap L4)

    Args:
        claim_id: the claim ID
        conviction_entries: list of conviction result dicts for this claim

    Returns:
        dict with: tally, signal_type, cap_effect, signal (for Stage 4 integration)
        Or None if no valid conviction data.
    """
    valid = [e for e in conviction_entries if e.get("decision") in ("MAINTAIN", "REVISE")]
    if not valid:
        return None

    n_maintain = sum(1 for e in valid if e["decision"] == "MAINTAIN")
    n_revise = sum(1 for e in valid if e["decision"] == "REVISE")
    n_total = len(valid)
    tally = f"{n_maintain}-{n_revise}"

    # Determine signal type -- no majority vote
    if n_revise == 0:
        # All available evaluators held -> reinforced
        signal_type = "reinforced"
    elif n_revise == n_total and n_total >= 2:
        # All evaluators caved (2+ evaluators) -> collapse
        signal_type = "collapse"
    elif n_revise > n_maintain:
        # Majority revised (or single evaluator caved) -> weak conviction
        signal_type = "weak_conviction"
    else:
        # Any REVISE present (minority or split) -> fragile conviction
        signal_type = "fragile_conviction"

    cap_effect = CONVICTION_SIGNAL_MAP.get(signal_type)

    # Build fragility signal for Stage 4 integration
    signal = None
    if cap_effect:
        signal = {
            "source": "conviction_test",
            "signal_id": f"conviction:{signal_type}",
            "description": (
                f"Conviction test {tally} ({signal_type}): "
                f"{'any' if signal_type == 'fragile_conviction' else 'majority'} "
                f"evaluator(s) revised under gold label pressure"
            ),
            "severity": "moderate" if signal_type == "fragile_conviction" else "critical",
            "effect": cap_effect,
        }

    return {
        "claim_id": claim_id,
        "tally": tally,
        "signal_type": signal_type,
        "cap_effect": cap_effect,
        "n_maintain": n_maintain,
        "n_revise": n_revise,
        "n_total": n_total,
        "signal": signal,
    }


def run_conviction_integration(source_run_name="1 SciFact Run"):
    """
    Full conviction integration pipeline:
    1. Retry Gemini on all 5 claims
    2. Merge with existing Sonnet/Grok results
    3. Recompute conviction tallies
    4. Integrate conviction signals into Stage 4 fragility
    5. Recompute Stage 5 dispositions
    6. Compute three-tier metrics + comparison table

    Saves to: 03 SciFact/Runs/1d SciFact Conviction-Integrated/
    """
    from cam.adapters.scifact.scifact_adapter import _load_jsonl_results
    from cam.adapters.scifact.scifact_fragility import compute_fragility_profile
    from cam.adapters.scifact.scifact_disposition import (
        compute_disposition_with_elimination,
        compare_to_gold,
        compute_cam_metrics,
    )
    from collections import defaultdict

    find_and_load_env()

    source_dir = CAM_ROOT / "03 SciFact" / "Runs" / source_run_name
    enhanced_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1b SciFact Run Enhanced"
    adjudication_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1c SciFact Adjudication"
    out_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1d SciFact Conviction-Integrated"
    out_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM SciFact -- Conviction Integration Pipeline")
    log("=" * 70)

    # ---- Step 1: Retry Gemini ----
    gemini_results = run_gemini_conviction_retry(source_run_name)

    # ---- Step 2: Merge results ----
    log("")
    log("=" * 70)
    log("  Merging conviction results (Sonnet/Grok from 1c + Gemini retry)")
    log("=" * 70)

    original_results_path = adjudication_dir / "conviction_results.jsonl"
    merged_results = _merge_conviction_results(original_results_path, gemini_results)

    # Save merged results
    merged_file = out_dir / "conviction_results_full.jsonl"
    with open(merged_file, "w", encoding="utf-8") as f:
        for r in merged_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"  Merged {len(merged_results)} conviction results")

    # ---- Step 3: Recompute conviction tallies ----
    log("")
    log("=" * 70)
    log("  Recomputing conviction tallies with all 3 evaluators")
    log("=" * 70)

    by_claim = defaultdict(list)
    for r in merged_results:
        by_claim[r["claim_id"]].append(r)

    conviction_signals = {}
    for claim_id in CONVICTION_CLAIMS:
        entries = by_claim.get(claim_id, [])
        sig = compute_conviction_signal(claim_id, entries)
        conviction_signals[claim_id] = sig
        if sig:
            log(f"  Claim {claim_id}: tally={sig['tally']}, type={sig['signal_type']}, cap={sig['cap_effect']}")
        else:
            log(f"  Claim {claim_id}: no valid conviction data")

    # Save conviction summary
    _compute_and_save_summary(merged_results, out_dir)

    # ---- Step 4: Recompute fragility with conviction signals ----
    log("")
    log("=" * 70)
    log("  STAGE 4 (recompute): Fragility with conviction signals")
    log("=" * 70)

    # Load all stage results from the source runs
    stage1_results = _load_jsonl_results(source_dir / "stage1_results.jsonl", "Stage 1")
    stage2_results = _load_jsonl_results(source_dir / "stage2_results.jsonl", "Stage 2")
    stage3_results = _load_jsonl_results(source_dir / "stage3_results.jsonl", "Stage 3")
    elimination_results = _load_jsonl_results(enhanced_dir / "elimination_results.jsonl", "Elimination")

    if not stage1_results:
        log("ERROR: No Stage 1 results found.")
        return

    # Build lookups
    s2_lookup = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}
    s3_lookup = {r["claim_id"]: r.get("audit", {}) for r in stage3_results}
    elim_lookup = {r["claim_id"]: r.get("elimination", {}) for r in elimination_results}

    stage4_results = []
    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        evaluations = s1_result["evaluations"]
        gold_label = s1_result["gold_label"]
        agreement = s1_result["agreement_pattern"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})

        claim_data = {
            "claim_id": claim_id,
            "claim_text": s1_result["claim_text"],
            "gold_label": gold_label,
        }
        profile = compute_fragility_profile(
            claim_data, evaluations, challenge_result, auditor_result
        )

        # Add elimination-based fragility signals (same as 1b)
        # NOTE: Match 1b behavior -- elimination signals are informational
        # markers. They do NOT affect max_cap. The disposition module
        # handles elimination effects separately via
        # compute_disposition_with_elimination().
        elim = elim_lookup.get(claim_id, {})
        if elim and "error" not in elim:
            killed_verdicts = [
                e for e in elim.get("eliminations", []) if e.get("killed")
            ]
            if killed_verdicts:
                for kv in killed_verdicts:
                    profile["signals"].append({
                        "source": "elimination",
                        "signal_id": f"verdict_killed:{kv.get('target_verdict', '?')}",
                        "description": (
                            f"Verdict {kv.get('target_verdict', '?')} killed by elimination "
                            f"({kv.get('elimination_type', '?')}): "
                            f"{kv.get('reasoning', '')[:120]}"
                        ),
                        "severity": "moderate",
                        "effect": "cap_L2",
                    })
                profile["signal_count"] = len(profile["signals"])
                profile["fragile"] = True

        # Add conviction-based fragility signals (NEW in 1d)
        # Conviction signals DO affect max_cap -- they represent
        # epistemic instability revealed by the conviction test.
        conv_sig = conviction_signals.get(claim_id)
        if conv_sig and conv_sig.get("signal"):
            profile["signals"].append(conv_sig["signal"])
            profile["signal_count"] = len(profile["signals"])
            profile["fragile"] = True
            # Recompute max_cap with conviction signal factored in
            # Only use non-elimination signals for cap computation
            # to match 1b behavior for elimination signals
            from cam.adapters.scifact.scifact_fragility import _compute_max_cap
            non_elim_signals = [
                s for s in profile["signals"] if s.get("source") != "elimination"
            ]
            profile["max_cap"] = _compute_max_cap(non_elim_signals)

        stage4_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "fragility": profile,
        })

    fragile_count = sum(1 for r in stage4_results if r["fragility"]["fragile"])
    log(f"  Stage 4: {fragile_count} fragile, {len(stage4_results) - fragile_count} clean")

    # Save Stage 4
    s4_file = out_dir / "stage4_results.jsonl"
    with open(s4_file, "w", encoding="utf-8") as f:
        for r in stage4_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ---- Step 5: Recompute dispositions with conviction caps ----
    log("")
    log("=" * 70)
    log("  STAGE 5 (recompute): Disposition with conviction caps")
    log("=" * 70)

    s4_lookup = {r["claim_id"]: r.get("fragility", {}) for r in stage4_results}

    disposition_results = []
    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})
        fragility_profile = s4_lookup.get(claim_id, {})
        elimination_result = elim_lookup.get(claim_id, {})

        disposition = compute_disposition_with_elimination(
            evaluations, challenge_result, auditor_result,
            fragility_profile, elimination_result,
        )
        gold_comparison = compare_to_gold(disposition, gold_label)

        match_str = "MATCH" if gold_comparison["gold_match"] else "MISMATCH"
        if gold_comparison["withheld"]:
            match_str = "WITHHELD"
        elim_action = disposition.get("elimination_action", "none")
        conv_sig = conviction_signals.get(claim_id)
        conv_str = f", conv={conv_sig['signal_type']}" if conv_sig else ""

        print(f"    Claim {claim_id}: {disposition['terminal_state']} @ "
              f"{disposition['commitment_level']} [{match_str}] "
              f"(elim={elim_action}{conv_str})")

        disposition_results.append({
            "claim_id": claim_id,
            "claim_text": claim_text,
            "disposition": disposition,
            "gold_comparison": gold_comparison,
            "fragility": fragility_profile,
        })

    # Save Stage 5
    s5_file = out_dir / "stage5_results.jsonl"
    with open(s5_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ---- Step 6: Compute metrics + comparison ----
    log("")
    log("=" * 70)
    log("  Computing metrics and comparison")
    log("=" * 70)

    new_metrics = compute_cam_metrics(disposition_results)

    # Three-tier CCA with full conviction data
    _compute_three_tier_metrics(merged_results, out_dir)

    # Load 1b metrics for comparison
    enhanced_s5 = _load_jsonl_results(enhanced_dir / "stage5_results.jsonl", "1b Stage 5")
    enhanced_metrics = compute_cam_metrics(enhanced_s5)

    # Load original (1) metrics for 3-way comparison
    original_s5 = _load_jsonl_results(source_dir / "stage5_results.jsonl", "Original Stage 5")
    original_metrics = compute_cam_metrics(original_s5) if original_s5 else None

    # Build comparison table
    _build_comparison_table(
        original_metrics, enhanced_metrics, new_metrics,
        original_s5, enhanced_s5, disposition_results, out_dir,
    )

    # Save metrics
    _save_metrics(new_metrics, out_dir)

    log("")
    log("=" * 70)
    log("  CONVICTION INTEGRATION COMPLETE")
    log(f"  Output: {out_dir.name}")
    log(f"  Claims: {len(disposition_results)}")
    log("=" * 70)

    return disposition_results


def _build_comparison_table(orig_metrics, enhanced_metrics, conv_metrics,
                            orig_results, enhanced_results, conv_results, out_dir):
    """Build the 3-way comparison table: Base(1) vs +Elim(1b) vs +Conv(1d)."""

    def _fmt_pct(val):
        return f"{val:.1%}" if val is not None else "N/A"

    def _count_wrong(results):
        return sum(
            1 for r in results
            if not r["gold_comparison"]["gold_match"] and not r["gold_comparison"]["withheld"]
        )

    def _count_withheld(results):
        return sum(1 for r in results if r["gold_comparison"]["withheld"])

    def _level_accuracy(results, level):
        level_results = [r for r in results if r["disposition"]["commitment_level"] == level]
        if not level_results:
            return "N/A"
        correct = sum(1 for r in level_results if r["gold_comparison"]["gold_match"])
        return f"{correct}/{len(level_results)}"

    lines = [
        "",
        "=" * 70,
        "  PIPELINE COMPARISON: Base vs +Elimination vs +Conviction",
        "=" * 70,
        "",
    ]

    header = f"{'METRIC':<25} {'Base(1)':>12} {'+Elim(1b)':>12} {'+Conv(1d)':>12}"
    lines.append(header)
    lines.append("-" * 65)

    # CCA
    orig_cca = _fmt_pct(orig_metrics["cca"]) if orig_metrics else "N/A"
    enh_cca = _fmt_pct(enhanced_metrics["cca"]) if enhanced_metrics else "N/A"
    conv_cca = _fmt_pct(conv_metrics["cca"])
    lines.append(f"{'CCA':<25} {orig_cca:>12} {enh_cca:>12} {conv_cca:>12}")

    # Abstention rate
    orig_abs = _fmt_pct(orig_metrics["abstention_rate"]) if orig_metrics else "N/A"
    enh_abs = _fmt_pct(enhanced_metrics["abstention_rate"]) if enhanced_metrics else "N/A"
    conv_abs = _fmt_pct(conv_metrics["abstention_rate"])
    lines.append(f"{'Abstention Rate':<25} {orig_abs:>12} {enh_abs:>12} {conv_abs:>12}")

    # Wrong assertions
    orig_wrong = _count_wrong(orig_results) if orig_results else "N/A"
    enh_wrong = _count_wrong(enhanced_results) if enhanced_results else "N/A"
    conv_wrong = _count_wrong(conv_results)
    lines.append(f"{'Wrong Assertions':<25} {str(orig_wrong):>12} {str(enh_wrong):>12} {str(conv_wrong):>12}")

    # Withholds
    orig_with = _count_withheld(orig_results) if orig_results else "N/A"
    enh_with = _count_withheld(enhanced_results) if enhanced_results else "N/A"
    conv_with = _count_withheld(conv_results)
    lines.append(f"{'Withholds':<25} {str(orig_with):>12} {str(enh_with):>12} {str(conv_with):>12}")

    lines.append("")
    lines.append("  Accuracy by Commitment Level:")

    for level in ["L0_FULL_ASSERT", "L1_QUALIFIED", "L2_CONDITIONAL", "L3_LOW_CONFIDENCE"]:
        short = level.split("_")[0]
        orig_la = _level_accuracy(orig_results, level) if orig_results else "N/A"
        enh_la = _level_accuracy(enhanced_results, level) if enhanced_results else "N/A"
        conv_la = _level_accuracy(conv_results, level)
        lines.append(f"    {short:<21} {orig_la:>12} {enh_la:>12} {conv_la:>12}")

    lines.append("")
    lines.append("=" * 70)

    comparison_text = "\n".join(lines)
    print(comparison_text)

    comp_file = out_dir / "comparison.txt"
    with open(comp_file, "w", encoding="utf-8") as f:
        f.write(comparison_text)
    log(f"  Comparison saved to {comp_file}")


def run_conviction_rescore(source_run_name="1 SciFact Run"):
    """
    Rescore conviction results with updated signal logic (no API calls).

    Reads existing conviction_results_full.jsonl from the 1d directory,
    recomputes conviction signals with the current scoring logic,
    then recomputes Stages 4-5 and metrics.

    This is for rescoring after changing the signal logic without
    re-running any API calls.

    Saves to: 03 SciFact/Runs/1d SciFact Conviction-Integrated/ (overwrite)
    """
    from cam.adapters.scifact.scifact_adapter import _load_jsonl_results
    from cam.adapters.scifact.scifact_fragility import compute_fragility_profile
    from cam.adapters.scifact.scifact_disposition import (
        compute_disposition_with_elimination,
        compare_to_gold,
        compute_cam_metrics,
    )
    from collections import defaultdict

    find_and_load_env()

    source_dir = CAM_ROOT / "03 SciFact" / "Runs" / source_run_name
    enhanced_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1b SciFact Run Enhanced"
    out_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1d SciFact Conviction-Integrated"

    log("=" * 70)
    log("  CAM SciFact -- Conviction Rescore (no API calls)")
    log("=" * 70)

    # ---- Load existing merged conviction results ----
    merged_file = out_dir / "conviction_results_full.jsonl"
    if not merged_file.exists():
        log(f"ERROR: {merged_file} not found. Run --convict-fix first.")
        return

    merged_results = []
    with open(merged_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                merged_results.append(json.loads(line))
    log(f"  Loaded {len(merged_results)} existing conviction results")

    # ---- Recompute conviction tallies with new signal logic ----
    log("")
    log("=" * 70)
    log("  Recomputing conviction signals (no majority vote)")
    log("=" * 70)

    by_claim = defaultdict(list)
    for r in merged_results:
        by_claim[r["claim_id"]].append(r)

    conviction_signals = {}
    for claim_id in CONVICTION_CLAIMS:
        entries = by_claim.get(claim_id, [])
        sig = compute_conviction_signal(claim_id, entries)
        conviction_signals[claim_id] = sig
        if sig:
            log(f"  Claim {claim_id}: tally={sig['tally']}, "
                f"type={sig['signal_type']}, cap={sig['cap_effect']}")
        else:
            log(f"  Claim {claim_id}: no valid conviction data")

    # Save updated conviction summary
    _compute_and_save_summary(merged_results, out_dir)

    # ---- Recompute Stage 4 fragility ----
    log("")
    log("=" * 70)
    log("  STAGE 4 (rescore): Fragility with updated conviction signals")
    log("=" * 70)

    stage1_results = _load_jsonl_results(source_dir / "stage1_results.jsonl", "Stage 1")
    stage2_results = _load_jsonl_results(source_dir / "stage2_results.jsonl", "Stage 2")
    stage3_results = _load_jsonl_results(source_dir / "stage3_results.jsonl", "Stage 3")
    elimination_results = _load_jsonl_results(
        enhanced_dir / "elimination_results.jsonl", "Elimination"
    )

    if not stage1_results:
        log("ERROR: No Stage 1 results found.")
        return

    s2_lookup = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}
    s3_lookup = {r["claim_id"]: r.get("audit", {}) for r in stage3_results}
    elim_lookup = {r["claim_id"]: r.get("elimination", {}) for r in elimination_results}

    stage4_results = []
    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        evaluations = s1_result["evaluations"]
        gold_label = s1_result["gold_label"]
        agreement = s1_result["agreement_pattern"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})

        claim_data = {
            "claim_id": claim_id,
            "claim_text": s1_result["claim_text"],
            "gold_label": gold_label,
        }
        profile = compute_fragility_profile(
            claim_data, evaluations, challenge_result, auditor_result
        )

        # Add elimination-based fragility signals (same as 1b)
        elim = elim_lookup.get(claim_id, {})
        if elim and "error" not in elim:
            killed_verdicts = [
                e for e in elim.get("eliminations", []) if e.get("killed")
            ]
            if killed_verdicts:
                for kv in killed_verdicts:
                    profile["signals"].append({
                        "source": "elimination",
                        "signal_id": f"verdict_killed:{kv.get('target_verdict', '?')}",
                        "description": (
                            f"Verdict {kv.get('target_verdict', '?')} killed by elimination "
                            f"({kv.get('elimination_type', '?')}): "
                            f"{kv.get('reasoning', '')[:120]}"
                        ),
                        "severity": "moderate",
                        "effect": "cap_L2",
                    })
                profile["signal_count"] = len(profile["signals"])
                profile["fragile"] = True

        # Add conviction-based fragility signals
        conv_sig = conviction_signals.get(claim_id)
        if conv_sig and conv_sig.get("signal"):
            profile["signals"].append(conv_sig["signal"])
            profile["signal_count"] = len(profile["signals"])
            profile["fragile"] = True
            from cam.adapters.scifact.scifact_fragility import _compute_max_cap
            non_elim_signals = [
                s for s in profile["signals"] if s.get("source") != "elimination"
            ]
            profile["max_cap"] = _compute_max_cap(non_elim_signals)

        stage4_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "fragility": profile,
        })

    fragile_count = sum(1 for r in stage4_results if r["fragility"]["fragile"])
    log(f"  Stage 4: {fragile_count} fragile, {len(stage4_results) - fragile_count} clean")

    # Save Stage 4
    s4_file = out_dir / "stage4_results.jsonl"
    with open(s4_file, "w", encoding="utf-8") as f:
        for r in stage4_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ---- Recompute Stage 5 dispositions ----
    log("")
    log("=" * 70)
    log("  STAGE 5 (rescore): Disposition with updated conviction caps")
    log("=" * 70)

    s4_lookup = {r["claim_id"]: r.get("fragility", {}) for r in stage4_results}

    disposition_results = []
    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})
        fragility_profile = s4_lookup.get(claim_id, {})
        elimination_result = elim_lookup.get(claim_id, {})

        disposition = compute_disposition_with_elimination(
            evaluations, challenge_result, auditor_result,
            fragility_profile, elimination_result,
        )
        gold_comparison = compare_to_gold(disposition, gold_label)

        match_str = "MATCH" if gold_comparison["gold_match"] else "MISMATCH"
        if gold_comparison["withheld"]:
            match_str = "WITHHELD"
        elim_action = disposition.get("elimination_action", "none")
        conv_sig = conviction_signals.get(claim_id)
        conv_str = f", conv={conv_sig['signal_type']}" if conv_sig else ""

        print(f"    Claim {claim_id}: {disposition['terminal_state']} @ "
              f"{disposition['commitment_level']} [{match_str}] "
              f"(elim={elim_action}{conv_str})")

        disposition_results.append({
            "claim_id": claim_id,
            "claim_text": claim_text,
            "disposition": disposition,
            "gold_comparison": gold_comparison,
            "fragility": fragility_profile,
        })

    # Save Stage 5
    s5_file = out_dir / "stage5_results.jsonl"
    with open(s5_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ---- Compute metrics + comparison ----
    log("")
    log("=" * 70)
    log("  Computing metrics and comparison")
    log("=" * 70)

    new_metrics = compute_cam_metrics(disposition_results)

    _compute_three_tier_metrics(merged_results, out_dir)

    enhanced_s5 = _load_jsonl_results(enhanced_dir / "stage5_results.jsonl", "1b Stage 5")
    enhanced_metrics = compute_cam_metrics(enhanced_s5)

    original_s5 = _load_jsonl_results(source_dir / "stage5_results.jsonl", "Original Stage 5")
    original_metrics = compute_cam_metrics(original_s5) if original_s5 else None

    _build_comparison_table(
        original_metrics, enhanced_metrics, new_metrics,
        original_s5, enhanced_s5, disposition_results, out_dir,
    )

    _save_metrics(new_metrics, out_dir)

    log("")
    log("=" * 70)
    log("  CONVICTION RESCORE COMPLETE")
    log(f"  Output: {out_dir.name}")
    log(f"  Claims: {len(disposition_results)}")
    log("=" * 70)

    return disposition_results


def _save_metrics(metrics, out_dir):
    """Save metrics in human-readable format."""
    lines = [
        "",
        "=" * 70,
        "  CAM Metrics (with Conviction Integration)",
        "=" * 70,
        "",
        f"  CCA: {metrics['correct_assertions']}/{metrics['total_assertions']} = {metrics['cca']:.1%}",
        f"  Abstention Rate: {metrics['abstention_count']}/{metrics['total_claims']} = {metrics['abstention_rate']:.1%}",
        f"  Abstention Value: {metrics.get('abstention_value', 'N/A')}",
        f"  Fragility Prediction: {metrics.get('fragility_prediction', 'N/A')}",
        f"  Total Claims: {metrics['total_claims']}",
        "",
        "=" * 70,
    ]

    metrics_text = "\n".join(lines)
    print(metrics_text)

    metrics_file = out_dir / "metrics.txt"
    with open(metrics_file, "w", encoding="utf-8") as f:
        f.write(metrics_text)
    log(f"  Metrics saved to {metrics_file}")
