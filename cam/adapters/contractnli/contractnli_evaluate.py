"""
ContractNLI Stage 1: Parallel Evaluation

Three evaluators independently assess each (contract, hypothesis) pair.
Each evaluator receives the full contract text with span markers and
a single hypothesis, then produces a structured verdict with cited spans.

Follows the same pattern as SciFact's parallel evaluation stage.
"""

import json
from collections import Counter
from pathlib import Path

from cam.core.config import find_and_load_env
from cam.core.provider_router import ProviderRouter, ModelTarget
from cam.core.utilities import log
from cam.adapters.contractnli.contractnli_normalize import normalize_evaluator_response
from cam.adapters.contractnli.contractnli_adapter import (
    format_contract_for_prompt,
    LABEL_MAP,
)

# ============================================================
# Evaluator Configuration
# ============================================================

# Compact example JSON for the evaluator prompt.
# We show an example instead of the full JSON Schema definition, because
# some models echo the schema back and truncate their actual response.
EVALUATOR_EXAMPLE_JSON = """{
  "verdict": "ENTAILMENT",
  "confidence": "high",
  "cited_spans": [12, 45, 46],
  "reasoning": "Span 12 defines Confidential Information broadly, and Spans 45-46 explicitly permit sharing with employees who have signed NDAs.",
  "exception_clauses_noted": ["Span 46 contains an exception: 'provided that such employees have signed a non-disclosure agreement'"],
  "definitions_traced": ["'Representatives' defined in Span 8 includes employees and advisors"],
  "assumptions": ["Assuming 'Representatives' as defined includes the employees referenced in the hypothesis."],
  "key_evidence": "Span 45 states: 'Receiving Party may disclose Confidential Information to its Representatives.'"
}"""

CONTRACTNLI_EVALUATORS = [
    {
        "label": "A",
        "name": "anthropic:claude-sonnet-4",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
    },
    {
        "label": "B",
        "name": "openai:gpt-5.2",
        "provider": "openai",
        "model": "gpt-5.2",
        "reasoning_effort": "medium",
    },
    {
        "label": "C",
        "name": "xai:grok-4-1-fast-reasoning",
        "provider": "xai",
        "model": "grok-4-1-fast-reasoning",
    },
]


# ============================================================
# Agreement Computation
# ============================================================

def compute_agreement_pattern(evaluations):
    """
    Compute agreement pattern from evaluator verdicts.

    Returns:
        pattern: str, e.g. "3-0 ENTAILMENT", "2-1 ENTAILMENT/CONTRADICTION", "1-1-1"
        majority_verdict: str or None
    """
    verdicts = []
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        if "error" not in ev and "verdict" in ev:
            verdicts.append(ev["verdict"])

    if len(verdicts) == 0:
        return "0-0-0 (all failed)", None

    counts = Counter(verdicts)
    most_common = counts.most_common()

    if len(most_common) == 1:
        verdict = most_common[0][0]
        return f"3-0 {verdict}", verdict
    elif most_common[0][1] >= 2:
        majority = most_common[0][0]
        minority = most_common[1][0]
        return f"2-1 {majority}/{minority}", majority
    else:
        return "1-1-1", None


# ============================================================
# Parallel Evaluation
# ============================================================

def run_parallel_evaluation(eval_items, evaluators, run_dir):
    """
    Stage 1: Run all evaluators independently on each evaluation item.

    Args:
        eval_items: list of evaluation item dicts (from build_evaluation_items)
        evaluators: list of dicts with {label, name, provider, model}
        run_dir: path to save outputs

    Returns:
        list of result dicts, one per evaluation item
    """
    find_and_load_env()

    # Load prompt template
    prompt_path = Path(__file__).parent / "prompts" / "evaluator.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Create one router per evaluator (each locked to a single provider)
    routers = {}
    for ev in evaluators:
        target = ModelTarget(
            name=ev["name"],
            provider=ev["provider"],
            model=ev["model"],
            priority=1,
            max_output_tokens=8192,
            temperature=0.0,
            timeout_sec=300.0,
            reasoning_effort=ev.get("reasoning_effort"),
        )
        routers[ev["label"]] = ProviderRouter(targets=[target])

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for item_idx, item in enumerate(eval_items):
        item_id = item["item_id"]
        hypothesis_text = item["claim"]
        hypothesis_id = item["hypothesis_id"]
        contract_text = item["evidence"]
        spans = item["evidence_spans"]
        gold_label = item["gold_label"]

        # Format contract with span markers
        formatted_contract = format_contract_for_prompt(contract_text, spans)

        # Fill prompt template
        prompt = prompt_template.replace("{hypothesis_text}", hypothesis_text)
        prompt = prompt.replace("{formatted_contract}", formatted_contract)
        prompt = prompt.replace("{example_json}", EVALUATOR_EXAMPLE_JSON)

        safe_hyp = hypothesis_text[:100].encode("ascii", errors="replace").decode("ascii")
        print()
        print("=" * 70)
        print(f"  Item {item_idx+1}/{len(eval_items)}: {item_id} (gold: {gold_label})")
        print(f"  Hypothesis [{hypothesis_id}]: {safe_hyp}...")
        print("=" * 70)

        # Create per-item raw output directory
        item_raw_dir = raw_dir / f"{item_id}"
        item_raw_dir.mkdir(parents=True, exist_ok=True)

        evaluations = {}

        # Call each evaluator sequentially
        for ev in evaluators:
            label = ev["label"]
            router = routers[label]
            log(f"    Evaluator {label} ({ev['name']})...")

            raw_response = ""
            normalized = None
            meta = None

            # Retry up to 2 times on failure
            for attempt in range(1, 3):
                try:
                    raw_obj, meta = router.call_json(
                        system_prompt="You are a legal contract entailment evaluator. Respond only with valid JSON.",
                        user_prompt=prompt,
                    )
                    raw_response = json.dumps(raw_obj)
                    normalized = normalize_evaluator_response(raw_response, f"Evaluator {label}")
                    log(f"      Attempt {attempt}: verdict={normalized.get('verdict', '???')}, "
                        f"confidence={normalized.get('confidence', '???')}, "
                        f"schema_valid={normalized.get('schema_valid')}")
                    break
                except Exception as e:
                    log(f"      Attempt {attempt} failed: {e}")
                    if attempt == 2:
                        normalized = {"error": f"API call failed after 2 attempts: {e}"}

            evaluations[label] = normalized

            # Save raw evaluator output
            eval_file = item_raw_dir / f"evaluator_{label}.json"
            with open(eval_file, "w", encoding="utf-8") as f:
                json.dump({
                    "evaluator": ev,
                    "raw_response": raw_response,
                    "normalized": normalized,
                    "meta": meta,
                }, f, indent=2, default=str)

        # Compute agreement
        pattern, majority_verdict = compute_agreement_pattern(evaluations)
        gold_match = (majority_verdict == gold_label) if majority_verdict else False

        # Print per-item summary
        print(f"  Agreement: {pattern}")
        for label in sorted(evaluations.keys()):
            ev = evaluations[label]
            v = ev.get("verdict", "ERROR")
            c = ev.get("confidence", "?")
            cs = ev.get("cited_spans", [])
            print(f"    {label}: {v} (confidence={c}, cited_spans={cs})")
        print(f"  Gold match: {gold_match}")

        result = {
            "item_id": item_id,
            "contract_id": item["contract_id"],
            "hypothesis_id": hypothesis_id,
            "hypothesis_text": hypothesis_text,
            "gold_label": gold_label,
            "gold_evidence_spans": item["gold_evidence_spans"],
            "evidence_word_count": item["evidence_word_count"],
            "evaluations": evaluations,
            "agreement_pattern": pattern,
            "majority_verdict": majority_verdict,
            "gold_match": gold_match,
        }
        results.append(result)

    return results
