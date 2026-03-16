"""
ContractNLI Adjudication Tool (Post-Hoc Analysis)

Independent AI review of gold mismatches. Not a pipeline stage.
Runs on a completed run's results to determine whether mismatches
are genuine system errors or debatable gold labels.

Usage:
    python -m cam.adapters.contractnli.contractnli_adapter --adjudicate --run "3a ContractNLI Targeted"
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.core.json_extract import safe_json_extract
from cam.core.provider_router import ProviderRouter, ModelTarget
from cam.core.utilities import log

logger = logging.getLogger(__name__)

# ============================================================
# Adjudicator Model Config
# ============================================================

CONTRACTNLI_ADJUDICATOR = {
    "label": "adjudicator",
    "name": "google:gemini-3.1-pro-preview",
    "provider": "google",
    "model": "gemini-3.1-pro-preview",
}

# ============================================================
# Schema Loading
# ============================================================

_SCHEMA_CACHE = {}


def _get_adjudication_schema():
    """Load and cache the adjudication schema."""
    if "adjudication" not in _SCHEMA_CACHE:
        schema_path = Path(__file__).parent / "schemas" / "adjudication_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE["adjudication"] = json.load(f)
    return _SCHEMA_CACHE["adjudication"]


# ============================================================
# Data Loading
# ============================================================

def _load_results(run_dir: Path) -> List[Dict]:
    """Load results.jsonl from a completed run."""
    results_file = run_dir / "results.jsonl"
    if not results_file.exists():
        raise FileNotFoundError(f"results.jsonl not found in {run_dir}")

    results = []
    with open(results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def _find_disputed_items(results: List[Dict]) -> List[Dict]:
    """Find items where gold_match == false and withheld == false."""
    disputed = []
    for r in results:
        if not r.get("gold_match", True) and not r.get("withheld", True):
            disputed.append(r)
    return disputed


def _load_evaluator_raw(raw_dir: Path, item_id: str) -> Dict[str, Dict]:
    """Load all 3 evaluator raw responses for an item."""
    item_dir = raw_dir / item_id
    evaluators = {}
    for label in ["A", "B", "C"]:
        eval_file = item_dir / f"evaluator_{label}.json"
        if eval_file.exists():
            with open(eval_file, "r", encoding="utf-8") as f:
                evaluators[label] = json.load(f)
        else:
            evaluators[label] = {"error": f"File not found: {eval_file}"}
    return evaluators


def _load_elimination_raw(raw_dir: Path, item_id: str) -> Optional[Dict]:
    """Load elimination result for an item."""
    item_dir = raw_dir / item_id
    elim_file = item_dir / f"{item_id}_elimination.json"
    if elim_file.exists():
        with open(elim_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _load_contract_text(item_id: str) -> Optional[str]:
    """Load and format contract text for an item from the dataset."""
    from cam.adapters.contractnli.contractnli_adapter import (
        load_contractnli_dataset,
        extract_contract_data,
        format_contract_for_prompt,
    )

    # Extract contract_id from item_id (e.g., "contract_547_nda-1" -> 547)
    parts = item_id.split("_")
    try:
        contract_id = int(parts[1])
    except (IndexError, ValueError):
        return None

    documents, _ = load_contractnli_dataset(split="dev")
    for doc in documents:
        if doc.get("id") == contract_id:
            cdata = extract_contract_data(doc)
            return format_contract_for_prompt(cdata["text"], cdata["spans"])
    return None


# ============================================================
# Evaluator Summary Formatting
# ============================================================

def _format_evaluator_summaries(evaluator_raw: Dict[str, Dict]) -> str:
    """Format evaluator responses into a summary for the adjudicator."""
    lines = []
    for label in sorted(evaluator_raw.keys()):
        data = evaluator_raw[label]
        if "error" in data and "normalized" not in data:
            lines.append(f"Evaluator {label}: ERROR — {data['error']}")
            continue

        norm = data.get("normalized", data)
        verdict = norm.get("verdict", "UNKNOWN")
        confidence = norm.get("confidence", "?")
        cited = norm.get("cited_spans", [])
        reasoning = norm.get("reasoning", "")
        key_evidence = norm.get("key_evidence", "")

        lines.append(f"Evaluator {label}: {verdict} (confidence={confidence})")
        lines.append(f"  Cited spans: {cited}")
        if reasoning:
            # Truncate long reasoning
            r = reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
            lines.append(f"  Reasoning: {r}")
        if key_evidence:
            e = key_evidence[:200] + "..." if len(key_evidence) > 200 else key_evidence
            lines.append(f"  Key evidence: {e}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# Response Normalization
# ============================================================

ADJUDICATION_MAP = {
    "SYSTEM_CORRECT": "SYSTEM_CORRECT",
    "GOLD_CORRECT": "GOLD_CORRECT",
    "GENUINELY_AMBIGUOUS": "GENUINELY_AMBIGUOUS",
    "system_correct": "SYSTEM_CORRECT",
    "gold_correct": "GOLD_CORRECT",
    "genuinely_ambiguous": "GENUINELY_AMBIGUOUS",
}

VERDICT_MAP = {
    "ENTAILMENT": "ENTAILMENT",
    "CONTRADICTION": "CONTRADICTION",
    "NOT_MENTIONED": "NOT_MENTIONED",
    "entailment": "ENTAILMENT",
    "contradiction": "CONTRADICTION",
    "not_mentioned": "NOT_MENTIONED",
    "NotMentioned": "NOT_MENTIONED",
    "Not_Mentioned": "NOT_MENTIONED",
}

CONFIDENCE_MAP = {
    "high": "high", "medium": "medium", "low": "low",
    "High": "high", "Medium": "medium", "Low": "low",
}


def _normalize_adjudication_response(raw_response: str, label: str = "") -> Dict:
    """Parse, normalize, and validate an adjudication response."""
    if not raw_response or not raw_response.strip():
        return {"error": f"[{label}] Empty response"}

    try:
        parsed = safe_json_extract(raw_response)
    except ValueError as e:
        return {"error": f"[{label}] JSON extraction failed: {e}"}

    if not isinstance(parsed, dict):
        return {"error": f"[{label}] Extracted JSON is not a dict: {type(parsed)}"}

    # Normalize fields
    if "adjudication" in parsed:
        parsed["adjudication"] = ADJUDICATION_MAP.get(
            parsed["adjudication"], parsed["adjudication"]
        )

    if "own_verdict" in parsed:
        parsed["own_verdict"] = VERDICT_MAP.get(
            parsed["own_verdict"], parsed["own_verdict"]
        )

    if "confidence" in parsed:
        parsed["confidence"] = CONFIDENCE_MAP.get(
            parsed["confidence"], parsed["confidence"]
        )

    if "key_spans" not in parsed:
        parsed["key_spans"] = []
    elif not isinstance(parsed["key_spans"], list):
        parsed["key_spans"] = []

    if "ambiguity_source" not in parsed:
        parsed["ambiguity_source"] = None

    if "human_review_recommended" not in parsed:
        parsed["human_review_recommended"] = False

    if "reasoning" not in parsed:
        parsed["reasoning"] = ""

    # Validate against schema
    schema = _get_adjudication_schema()
    if JSONSCHEMA_AVAILABLE:
        try:
            jsonschema.validate(instance=parsed, schema=schema)
            parsed["schema_valid"] = True
            parsed["schema_error"] = None
        except jsonschema.ValidationError as e:
            parsed["schema_valid"] = False
            parsed["schema_error"] = str(e.message)
    else:
        parsed["schema_valid"] = True
        parsed["schema_error"] = None

    return parsed


# ============================================================
# Adjudication Runner
# ============================================================

ADJUDICATION_EXAMPLE_JSON = """{
  "adjudication": "SYSTEM_CORRECT",
  "own_verdict": "CONTRADICTION",
  "confidence": "high",
  "reasoning": "The contract's broad definition in Span 8 uses open-ended language that encompasses the specific scenario without requiring express identification, making the system's CONTRADICTION verdict defensible.",
  "key_spans": [6, 7, 8],
  "ambiguity_source": null,
  "human_review_recommended": false
}"""


def run_adjudication(run_label: str, adjudication_model: str = "gemini"):
    """
    Run post-hoc adjudication on all gold mismatches in a completed run.

    Args:
        run_label: Name of the run directory (e.g., "3a ContractNLI Targeted")
        adjudication_model: "gemini" (default) or "gpt" for GPT-5.2
    """
    find_and_load_env()

    run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / run_label
    if not run_dir.exists():
        log(f"ERROR: Run directory not found: {run_dir}")
        return

    raw_dir = run_dir / "raw"

    # Select adjudicator model
    if adjudication_model == "gpt":
        adjudicator_config = {
            "label": "adjudicator",
            "name": "openai:gpt-5.2",
            "provider": "openai",
            "model": "gpt-5.2",
            "reasoning_effort": "medium",
        }
    else:
        adjudicator_config = CONTRACTNLI_ADJUDICATOR

    log("=" * 70)
    log("  CAM ContractNLI — ADJUDICATION")
    log(f"  Run: {run_label}")
    log(f"  Adjudicator: {adjudicator_config['name']}")
    log("=" * 70)

    # Load results and find disputed items
    results = _load_results(run_dir)
    disputed = _find_disputed_items(results)

    total_asserted = sum(1 for r in results if not r.get("withheld", True))
    total_items = len(results)

    log(f"  Total items: {total_items}")
    log(f"  Asserted: {total_asserted}")
    log(f"  Gold mismatches (disputed): {len(disputed)}")
    log("")

    if not disputed:
        log("  No disputed items to adjudicate.")
        return

    # Load prompt template
    prompt_path = Path(__file__).parent / "prompts" / "adjudication.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up adjudicator router
    target = ModelTarget(
        name=adjudicator_config["name"],
        provider=adjudicator_config["provider"],
        model=adjudicator_config["model"],
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=300.0,
        reasoning_effort=adjudicator_config.get("reasoning_effort"),
    )
    router = ProviderRouter(targets=[target])

    # Cache contract texts to avoid reloading
    contract_text_cache = {}

    # Run adjudication on each disputed item
    adjudication_results = []

    for i, item in enumerate(disputed, 1):
        item_id = item["item_id"]
        hypothesis_text = item.get("hypothesis_text", "")
        cam_verdict = item.get("terminal_state", "").replace("ASSERT_", "")
        if cam_verdict == "WITHHOLD_ASSERTION":
            cam_verdict = "WITHHELD"
        gold_label = item.get("gold_label", "")

        log(f"  [{i}/{len(disputed)}] Adjudicating {item_id}...")
        log(f"    CAM: {cam_verdict} vs Gold: {gold_label}")

        # Load contract text (cached)
        contract_id = item.get("contract_id")
        if contract_id not in contract_text_cache:
            contract_text_cache[contract_id] = _load_contract_text(item_id)
        formatted_contract = contract_text_cache.get(contract_id, "[Contract text unavailable]")

        # Load evaluator raw files
        evaluator_raw = _load_evaluator_raw(raw_dir, item_id)
        evaluator_summaries = _format_evaluator_summaries(evaluator_raw)

        # Build prompt
        prompt = prompt_template.format(
            hypothesis_text=hypothesis_text,
            formatted_contract=formatted_contract,
            evaluator_summaries=evaluator_summaries,
            cam_verdict=cam_verdict,
            gold_label=gold_label,
        )

        # Add response format instruction
        prompt += (
            "\n\nRespond with a single JSON object matching this example structure. "
            "Do NOT include any schema definitions, comments, or extra text — just the JSON object.\n\n"
            f"{ADJUDICATION_EXAMPLE_JSON}"
        )

        # Call adjudicator
        try:
            raw_obj, meta = router.call_json(
                system_prompt="You are an independent legal adjudicator. Respond only with valid JSON.",
                user_prompt=prompt,
            )
            raw_text = json.dumps(raw_obj)
            result = _normalize_adjudication_response(raw_text, label=item_id)
        except Exception as e:
            logger.error(f"Adjudication failed for {item_id}: {e}")
            result = {"error": str(e)}

        # Attach item metadata
        result["item_id"] = item_id
        result["contract_id"] = contract_id
        result["hypothesis_text"] = hypothesis_text
        result["cam_verdict"] = cam_verdict
        result["gold_label"] = gold_label

        adjudication_results.append(result)

        adj = result.get("adjudication", "ERROR")
        conf = result.get("confidence", "?")
        log(f"    -> {adj} (confidence={conf})")

    # Write adjudication_report.jsonl
    report_file = run_dir / "adjudication_report.jsonl"
    with open(report_file, "w", encoding="utf-8") as f:
        for r in adjudication_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\n  Report saved: {report_file}")

    # Compute summary stats
    counts = {"SYSTEM_CORRECT": 0, "GOLD_CORRECT": 0, "GENUINELY_AMBIGUOUS": 0, "ERROR": 0}
    for r in adjudication_results:
        adj = r.get("adjudication", "ERROR")
        if adj in counts:
            counts[adj] += 1
        else:
            counts["ERROR"] += 1

    # Compute raw and adjusted CCA
    total_correct_raw = sum(1 for r in results if r.get("gold_match", False) and not r.get("withheld", False))
    raw_cca = (total_correct_raw / total_asserted * 100) if total_asserted > 0 else 0.0

    # Adjusted: exclude SYSTEM_CORRECT and GENUINELY_AMBIGUOUS from error count
    adjusted_errors = counts["GOLD_CORRECT"]
    adjusted_correct = total_asserted - adjusted_errors
    adjusted_cca = (adjusted_correct / total_asserted * 100) if total_asserted > 0 else 0.0

    # Write adjudication_summary.txt
    summary_lines = []
    summary_lines.append("=" * 64)
    summary_lines.append("CONTRACTNLI ADJUDICATION REPORT")
    summary_lines.append(f"Run: {run_label}")
    summary_lines.append(f"Adjudicator: {adjudicator_config['name']}")
    summary_lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    summary_lines.append("=" * 64)
    summary_lines.append("")
    summary_lines.append("SUMMARY")
    summary_lines.append(f"  Total items: {total_items}")
    summary_lines.append(f"  Asserted: {total_asserted}")
    summary_lines.append(f"  Gold mismatches reviewed: {len(disputed)}")
    summary_lines.append("")
    summary_lines.append(f"  SYSTEM_CORRECT: {counts['SYSTEM_CORRECT']}  (gold label is wrong/debatable)")
    summary_lines.append(f"  GOLD_CORRECT: {counts['GOLD_CORRECT']}    (CAM got it wrong)")
    summary_lines.append(f"  GENUINELY_AMBIGUOUS: {counts['GENUINELY_AMBIGUOUS']}")
    if counts["ERROR"] > 0:
        summary_lines.append(f"  ERRORS: {counts['ERROR']}")
    summary_lines.append("")
    summary_lines.append(f"  Raw CCA: {raw_cca:.1f}% ({total_correct_raw}/{total_asserted} asserted correct vs gold)")
    summary_lines.append(f"  Adjusted CCA: {adjusted_cca:.1f}% (excluding SYSTEM_CORRECT + GENUINELY_AMBIGUOUS from errors)")
    summary_lines.append("")

    # Disputed cases
    summary_lines.append("=" * 64)
    summary_lines.append("DISPUTED CASES")
    summary_lines.append("=" * 64)
    summary_lines.append("")

    for r in adjudication_results:
        summary_lines.append(f"--- {r.get('item_id', '?')} ---")
        hyp = r.get("hypothesis_text", "?")
        safe_hyp = hyp[:120].encode("ascii", errors="replace").decode("ascii")
        summary_lines.append(f"  Hypothesis: {safe_hyp}")
        summary_lines.append(f"  CAM verdict: {r.get('cam_verdict', '?')}")
        summary_lines.append(f"  Gold label: {r.get('gold_label', '?')}")
        summary_lines.append(f"  Adjudication: {r.get('adjudication', '?')}")
        summary_lines.append(f"  Adjudicator's own verdict: {r.get('own_verdict', '?')}")
        summary_lines.append(f"  Confidence: {r.get('confidence', '?')}")
        reasoning = r.get("reasoning", "")
        safe_reasoning = reasoning[:300].encode("ascii", errors="replace").decode("ascii")
        summary_lines.append(f"  Reasoning: {safe_reasoning}")
        summary_lines.append(f"  Key spans: {r.get('key_spans', [])}")
        if r.get("ambiguity_source"):
            summary_lines.append(f"  Ambiguity source: {r['ambiguity_source']}")
        summary_lines.append("")

    # Human review section
    summary_lines.append("=" * 64)
    summary_lines.append("HUMAN REVIEW SECTION")
    summary_lines.append("=" * 64)
    summary_lines.append("The following cases are flagged for human review.")
    summary_lines.append("All GENUINELY_AMBIGUOUS cases plus any where adjudicator")
    summary_lines.append("confidence is \"low\" are listed here.")
    summary_lines.append("")

    human_review = [
        r for r in adjudication_results
        if r.get("adjudication") == "GENUINELY_AMBIGUOUS"
        or r.get("confidence") == "low"
        or r.get("human_review_recommended", False)
    ]

    if human_review:
        for r in human_review:
            summary_lines.append(f"--- {r.get('item_id', '?')} ---")
            hyp = r.get("hypothesis_text", "?")
            safe_hyp = hyp[:120].encode("ascii", errors="replace").decode("ascii")
            summary_lines.append(f"  Hypothesis: {safe_hyp}")
            summary_lines.append(f"  CAM says: {r.get('cam_verdict', '?')}")
            summary_lines.append(f"  Gold says: {r.get('gold_label', '?')}")
            summary_lines.append(f"  Adjudicator says: {r.get('own_verdict', '?')} (confidence: {r.get('confidence', '?')})")
            reasoning = r.get("reasoning", "")
            safe_reasoning = reasoning[:300].encode("ascii", errors="replace").decode("ascii")
            summary_lines.append(f"  Adjudicator notes: {safe_reasoning}")
            if r.get("ambiguity_source"):
                summary_lines.append(f"  Ambiguity: {r['ambiguity_source']}")
            summary_lines.append("")
            summary_lines.append(f"  HUMAN DETERMINATION: ________________")
            summary_lines.append(f"  REVIEWER: ________________")
            summary_lines.append(f"  DATE: ________________")
            summary_lines.append("")
    else:
        summary_lines.append("  No cases flagged for human review.")
        summary_lines.append("")

    summary_text = "\n".join(summary_lines)
    summary_file = run_dir / "adjudication_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_text)
    log(f"  Summary saved: {summary_file}")

    # Print summary to console
    log("")
    log(summary_text)

    return {
        "total_items": total_items,
        "total_asserted": total_asserted,
        "disputed": len(disputed),
        "system_correct": counts["SYSTEM_CORRECT"],
        "gold_correct": counts["GOLD_CORRECT"],
        "genuinely_ambiguous": counts["GENUINELY_AMBIGUOUS"],
        "raw_cca": raw_cca,
        "adjusted_cca": adjusted_cca,
        "results": adjudication_results,
    }
