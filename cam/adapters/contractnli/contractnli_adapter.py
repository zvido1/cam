"""
CAM ContractNLI Adapter — Dataset Loading, Sampling, and Pipeline Entry Point
Phase 3: Legal contract entailment verification.

This module handles:
- Loading the ContractNLI dataset (dev.json from 04 ContractNLI/contractnli_data/)
- Contract text + span array extraction
- 17 hypotheses loading from the labels field
- Sampling logic: 10 contracts stratified by length and label diversity
- Internal representation mapping: (contract, hypothesis) -> CAM evaluation item
- --dry-run flag for data validation without model calls

Usage:
    python -m cam.adapters.contractnli.contractnli_adapter --dry-run
    python -m cam.adapters.contractnli.contractnli_adapter --dry-run --n 10 --seed 1337
"""

import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# CAM Core Imports — verify shared core is reachable
# ============================================================
from cam.core.config import CAM_ROOT, find_and_load_env
from cam.core.run_manager import RunContext, get_next_run_number
from cam.core.utilities import log

# ============================================================
# Constants
# ============================================================

CONTRACTNLI_DATA_DIR = CAM_ROOT / "04 ContractNLI" / "contractnli_data"

# Label mapping: ContractNLI uses Entailment/Contradiction/NotMentioned
# We normalize to uppercase for internal consistency with CAM pipeline.
LABEL_MAP = {
    "Entailment": "ENTAILMENT",
    "Contradiction": "CONTRADICTION",
    "NotMentioned": "NOT_MENTIONED",
}

# Length tercile boundaries (word count) for stratified sampling.
# These are computed dynamically from the dataset during sampling.


# ============================================================
# Dataset Loading
# ============================================================

def load_contractnli_dataset(data_dir=None, split="dev"):
    """
    Load a ContractNLI dataset split.

    Args:
        data_dir: Path to data directory (default: 04 ContractNLI/contractnli_data/)
        split: Which split to load ("train", "dev", "test")

    Returns:
        documents: list of document dicts, each with keys:
            id, file_name, text, spans, annotation_sets, document_type, url
        labels: dict mapping hypothesis_id -> {short_description, hypothesis}
    """
    if data_dir is None:
        data_dir = CONTRACTNLI_DATA_DIR

    data_dir = Path(data_dir)
    filepath = data_dir / f"{split}.json"

    if not filepath.exists():
        raise FileNotFoundError(
            f"ContractNLI {split}.json not found at {filepath}.\n"
            f"Run '04 ContractNLI/download_and_explore.py' first to download the dataset."
        )

    log(f"Loading ContractNLI {split} split from {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = data.get("documents", [])
    labels = data.get("labels", {})

    log(f"  Loaded: {len(documents)} contracts, {len(labels)} hypotheses")
    return documents, labels


# ============================================================
# Contract Data Extraction
# ============================================================

def extract_contract_data(document):
    """
    Extract normalized contract data from a raw document record.

    Args:
        document: A single document dict from the dataset.

    Returns:
        dict with keys: contract_id, file_name, text, spans, word_count,
                        document_type, annotations
        annotations is a dict: hypothesis_id -> {choice, spans}
    """
    text = document.get("text", "")
    spans = document.get("spans", [])

    # Get annotations from first annotation set
    annotations = {}
    ann_sets = document.get("annotation_sets", [])
    if ann_sets:
        raw_annotations = ann_sets[0].get("annotations", {})
        for hyp_id, ann in raw_annotations.items():
            annotations[hyp_id] = {
                "choice": ann.get("choice", ""),
                "spans": ann.get("spans", []),
            }

    return {
        "contract_id": document.get("id"),
        "file_name": document.get("file_name", ""),
        "text": text,
        "spans": spans,
        "word_count": len(text.split()),
        "document_type": document.get("document_type", ""),
        "url": document.get("url", ""),
        "annotations": annotations,
    }


def format_contract_for_prompt(text, spans):
    """
    Format contract text with span boundary markers for evaluator prompts.

    Inserts [SPAN N] markers at the start of each span so evaluators can
    reference specific spans by index in their citations.

    Args:
        text: Full contract text string.
        spans: List of [start, end] character offset pairs.

    Returns:
        Formatted string with span markers inserted.
    """
    if not spans:
        return text

    # Build a list of (position, marker) tuples, sorted by position descending
    # so insertions don't shift subsequent positions.
    markers = []
    for i, (start, end) in enumerate(spans):
        markers.append((start, f"[SPAN {i}] "))

    # Sort by position descending to insert from end to start
    markers.sort(key=lambda x: x[0], reverse=True)

    result = text
    for pos, marker in markers:
        result = result[:pos] + marker + result[pos:]

    return result


# ============================================================
# Evaluation Item Construction
# ============================================================

def build_evaluation_items(contract_data, labels):
    """
    Build CAM evaluation items from a contract and all 17 hypotheses.

    Each (contract, hypothesis) pair becomes one evaluation item.

    Args:
        contract_data: dict from extract_contract_data()
        labels: dict mapping hypothesis_id -> {short_description, hypothesis}

    Returns:
        list of evaluation item dicts, one per hypothesis.
    """
    items = []
    contract_id = contract_data["contract_id"]
    annotations = contract_data["annotations"]

    for hyp_id in sorted(labels.keys(), key=lambda x: int(x.split("-")[1])):
        hyp_info = labels[hyp_id]
        annotation = annotations.get(hyp_id, {})
        raw_label = annotation.get("choice", "")
        gold_label = LABEL_MAP.get(raw_label, raw_label)
        gold_spans = annotation.get("spans", [])

        item = {
            "item_id": f"contract_{contract_id}_{hyp_id}",
            "contract_id": contract_id,
            "hypothesis_id": hyp_id,
            "claim": hyp_info["hypothesis"],
            "claim_short": hyp_info.get("short_description", ""),
            "evidence": contract_data["text"],
            "evidence_spans": contract_data["spans"],
            "evidence_word_count": contract_data["word_count"],
            "candidate_options": ["ENTAILMENT", "CONTRADICTION", "NOT_MENTIONED"],
            "gold_label": gold_label,
            "gold_evidence_spans": gold_spans,
            "document_type": contract_data["document_type"],
            "file_name": contract_data["file_name"],
        }
        items.append(item)

    return items


# ============================================================
# Sampling Logic
# ============================================================

def _compute_label_diversity(contract_data):
    """
    Compute label diversity score for a contract.

    Higher score = more diverse labels across hypotheses.
    A contract with all-Entailment scores low; one with a mix of all
    three labels scores high.

    Returns:
        float: Shannon entropy of label distribution (0 to ~1.58)
    """
    import math

    annotations = contract_data["annotations"]
    if not annotations:
        return 0.0

    label_counts = Counter()
    for hyp_id, ann in annotations.items():
        label_counts[ann["choice"]] += 1

    total = sum(label_counts.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in label_counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    return entropy


def sample_contracts(documents, labels, n=10, seed=1337):
    """
    Select n contracts from the dataset, stratified by contract length
    (short/medium/long terciles) and label diversity.

    Strategy:
    1. Compute word count and label diversity for each contract
    2. Divide into 3 length terciles (short / medium / long)
    3. Within each tercile, sort by label diversity (descending)
    4. Pick top contracts from each tercile proportionally
       (aiming for ~3-4 from each tercile)
    5. If n isn't evenly divisible, extra picks go to medium tercile

    Args:
        documents: list of raw document dicts
        labels: hypothesis labels dict
        n: number of contracts to select
        seed: random seed for reproducibility

    Returns:
        list of selected document dicts (raw format)
    """
    random.seed(seed)

    # Extract contract data and compute metrics
    contract_metrics = []
    for doc in documents:
        cdata = extract_contract_data(doc)
        diversity = _compute_label_diversity(cdata)
        contract_metrics.append({
            "doc": doc,
            "contract_id": cdata["contract_id"],
            "word_count": cdata["word_count"],
            "diversity": diversity,
        })

    # Sort by word count to find tercile boundaries
    sorted_by_length = sorted(contract_metrics, key=lambda x: x["word_count"])
    total = len(sorted_by_length)
    t1 = total // 3
    t2 = 2 * total // 3

    terciles = {
        "short": sorted_by_length[:t1],
        "medium": sorted_by_length[t1:t2],
        "long": sorted_by_length[t2:],
    }

    # Determine how many from each tercile
    per_tercile = n // 3
    remainder = n - per_tercile * 3
    picks = {
        "short": per_tercile,
        "medium": per_tercile + remainder,  # extra goes to medium
        "long": per_tercile,
    }

    selected = []
    for tercile_name in ["short", "medium", "long"]:
        bucket = terciles[tercile_name]
        # Sort by diversity descending (prefer diverse label distributions)
        bucket_sorted = sorted(bucket, key=lambda x: x["diversity"], reverse=True)
        pick_count = min(picks[tercile_name], len(bucket_sorted))
        selected.extend(bucket_sorted[:pick_count])

    log(f"  Sampled {len(selected)} contracts: "
        f"{picks['short']} short, {picks['medium']} medium, {picks['long']} long")

    # Log tercile boundaries
    if sorted_by_length:
        short_max = sorted_by_length[t1 - 1]["word_count"] if t1 > 0 else 0
        long_min = sorted_by_length[t2]["word_count"] if t2 < total else 0
        log(f"  Length terciles: short <={short_max} words, "
            f"medium {short_max+1}-{long_min-1}, long >={long_min}")

    return [s["doc"] for s in selected]


# ============================================================
# Dry Run — Data Validation
# ============================================================

def dry_run(n=10, seed=1337):
    """
    Load data and print diagnostic stats without calling any models.

    Validates:
    - Dataset loads correctly
    - Contract count and hypothesis count
    - Label distribution (overall and per-hypothesis)
    - Sample contract stats (word count, span count, annotation count)
    - Sampling logic works correctly
    - Evaluation item construction
    """
    log("=" * 70)
    log("ContractNLI Adapter -- DRY RUN")
    log("=" * 70)

    # Load dataset
    documents, labels = load_contractnli_dataset(split="dev")

    # --- Contract Count ---
    log(f"\nContract count: {len(documents)}")
    log(f"Hypothesis count: {len(labels)}")
    log(f"Total evaluation pairs: {len(documents)} x {len(labels)} = "
        f"{len(documents) * len(labels)}")

    # --- Hypothesis List ---
    log(f"\nHypotheses ({len(labels)}):")
    for hyp_id in sorted(labels.keys(), key=lambda x: int(x.split("-")[1])):
        hyp = labels[hyp_id]
        log(f"  {hyp_id}: [{hyp.get('short_description', '')}] "
            f"{hyp['hypothesis'][:70]}{'...' if len(hyp['hypothesis']) > 70 else ''}")

    # --- Label Distribution ---
    overall_labels = Counter()
    per_hyp_labels = defaultdict(Counter)
    all_contracts = []

    for doc in documents:
        cdata = extract_contract_data(doc)
        all_contracts.append(cdata)
        for hyp_id, ann in cdata["annotations"].items():
            choice = ann["choice"]
            overall_labels[choice] += 1
            per_hyp_labels[hyp_id][choice] += 1

    total_annotations = sum(overall_labels.values())
    log(f"\nOverall label distribution ({total_annotations} annotations):")
    for label in ["Entailment", "Contradiction", "NotMentioned"]:
        count = overall_labels.get(label, 0)
        pct = count / total_annotations * 100 if total_annotations > 0 else 0
        log(f"  {label:<15} {count:>5} ({pct:.1f}%)")

    log(f"\nPer-hypothesis label distribution:")
    log(f"  {'Hypothesis':<10} {'Entail':>8} {'Contra':>8} {'NotMen':>8} {'Total':>8}")
    log(f"  {'-' * 46}")
    for hyp_id in sorted(per_hyp_labels.keys(), key=lambda x: int(x.split("-")[1])):
        counts = per_hyp_labels[hyp_id]
        total = sum(counts.values())
        e = counts.get("Entailment", 0)
        c = counts.get("Contradiction", 0)
        n_val = counts.get("NotMentioned", 0)
        log(f"  {hyp_id:<10} {e:>8} {c:>8} {n_val:>8} {total:>8}")

    # --- Document Statistics ---
    word_counts = [c["word_count"] for c in all_contracts]
    span_counts = [len(c["spans"]) for c in all_contracts]
    log(f"\nDocument statistics:")
    log(f"  Word count: min={min(word_counts)}, avg={sum(word_counts)/len(word_counts):.0f}, "
        f"max={max(word_counts)}")
    log(f"  Spans/doc:  min={min(span_counts)}, avg={sum(span_counts)/len(span_counts):.1f}, "
        f"max={max(span_counts)}")

    # --- Sampling ---
    log(f"\nSampling {n} contracts (seed={seed})...")
    sampled_docs = sample_contracts(documents, labels, n=n, seed=seed)

    log(f"\nSampled contracts ({len(sampled_docs)}):")
    log(f"  {'ID':>5} {'Words':>7} {'Spans':>7} {'Type':<12} {'Labels (E/C/N)'}")
    log(f"  {'-' * 55}")

    total_items = 0
    for doc in sampled_docs:
        cdata = extract_contract_data(doc)
        ann = cdata["annotations"]
        e = sum(1 for a in ann.values() if a["choice"] == "Entailment")
        c = sum(1 for a in ann.values() if a["choice"] == "Contradiction")
        nm = sum(1 for a in ann.values() if a["choice"] == "NotMentioned")
        log(f"  {cdata['contract_id']:>5} {cdata['word_count']:>7} "
            f"{len(cdata['spans']):>7} {cdata['document_type']:<12} "
            f"{e}/{c}/{nm}")
        total_items += len(labels)

    log(f"\n  Total evaluation items: {len(sampled_docs)} contracts x "
        f"{len(labels)} hypotheses = {total_items}")

    # --- Evaluation Item Construction Test ---
    log(f"\nEvaluation item construction test (first sampled contract):")
    first_cdata = extract_contract_data(sampled_docs[0])
    items = build_evaluation_items(first_cdata, labels)
    log(f"  Built {len(items)} evaluation items for contract {first_cdata['contract_id']}")

    # Show first 3 items
    for item in items[:3]:
        log(f"    {item['item_id']}:")
        log(f"      claim: {item['claim'][:60]}{'...' if len(item['claim']) > 60 else ''}")
        log(f"      gold:  {item['gold_label']}")
        log(f"      gold_spans: {item['gold_evidence_spans']}")
        log(f"      evidence_words: {item['evidence_word_count']}")

    # --- Contract text formatting test ---
    log(f"\nContract text formatting test (first 300 chars with span markers):")
    formatted = format_contract_for_prompt(first_cdata["text"], first_cdata["spans"])
    # Encode to ASCII for safe console output (legal texts may contain non-ASCII)
    safe_preview = formatted[:300].encode("ascii", errors="replace").decode("ascii")
    log(f"  {safe_preview}...")

    log(f"\n{'=' * 70}")
    log("DRY RUN COMPLETE -- all data loaded and validated successfully")
    log(f"{'=' * 70}")


# ============================================================
# Stage 1: Parallel Evaluation
# ============================================================

def run_stage1(n_contracts=10, seed=1337, test_mode=False, test_n_hyps=1, run_label=None):
    """
    Run Stage 1 parallel evaluation.

    Args:
        n_contracts: Number of contracts to sample.
        seed: Random seed.
        test_mode: If True, limit to 1 contract with test_n_hyps hypotheses.
        test_n_hyps: Number of hypotheses in test mode.
        run_label: Override for the run directory name.
    """
    from cam.adapters.contractnli.contractnli_evaluate import (
        run_parallel_evaluation,
        CONTRACTNLI_EVALUATORS,
        compute_agreement_pattern,
    )

    log("=" * 70)
    log("  CAM ContractNLI -- Stage 1: Parallel Evaluation")
    log("=" * 70)

    # Load dataset
    documents, labels = load_contractnli_dataset(split="dev")

    # Sample contracts
    if test_mode:
        sampled_docs = sample_contracts(documents, labels, n=1, seed=seed)
    else:
        sampled_docs = sample_contracts(documents, labels, n=n_contracts, seed=seed)

    # Build evaluation items
    all_items = []
    for doc in sampled_docs:
        cdata = extract_contract_data(doc)
        items = build_evaluation_items(cdata, labels)
        all_items.extend(items)

    if test_mode:
        # In test mode, limit to test_n_hyps hypotheses
        all_items = all_items[:test_n_hyps]

    log(f"\nTotal evaluation items: {len(all_items)}")
    log(f"  Contracts: {len(sampled_docs)}")
    log(f"  Hypotheses per contract: {len(labels)}")

    # Set up run directory
    if run_label is None:
        run_label = "test_017" if test_mode else "stage1"
    run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / run_label
    run_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluation
    results = run_parallel_evaluation(all_items, CONTRACTNLI_EVALUATORS, run_dir)

    # Save results as JSONL
    results_file = run_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\nResults saved to {results_file}")

    # Agreement summary
    unanimous = sum(1 for r in results if r["agreement_pattern"].startswith("3-0"))
    majority = sum(1 for r in results if r["agreement_pattern"].startswith("2-1"))
    split = sum(1 for r in results if r["agreement_pattern"].startswith("1-1-1"))
    gold_matches = sum(1 for r in results if r["gold_match"])

    log("")
    log("=" * 70)
    log("  Agreement Summary")
    log("=" * 70)
    log(f"  Total items: {len(results)}")
    log(f"  Unanimous (3-0): {unanimous}")
    log(f"  Majority  (2-1): {majority}")
    log(f"  Full split (1-1-1): {split}")
    log(f"  Gold match (majority = gold): {gold_matches}/{len(results)}")
    log("=" * 70)

    # Per-item detail
    log("")
    log("  Per-Item Results:")
    log("  " + "-" * 66)
    for r in results:
        verdicts = []
        for label in sorted(r["evaluations"].keys()):
            v = r["evaluations"][label].get("verdict", "ERR")
            verdicts.append(f"{label}={v}")
        match_marker = "OK" if r["gold_match"] else "X"
        hyp_id = r["hypothesis_id"]
        gold = r["gold_label"]
        safe_line = f"  {r['item_id']} (gold={gold}): {', '.join(verdicts)} -> {r['agreement_pattern']} [{match_marker}]"
        log(safe_line)

    # Save summary
    summary_file = run_dir / "agreement_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Total items: {len(results)}\n")
        f.write(f"Unanimous (3-0): {unanimous}\n")
        f.write(f"Majority  (2-1): {majority}\n")
        f.write(f"Full split (1-1-1): {split}\n")
        f.write(f"Gold match: {gold_matches}/{len(results)}\n")
    log(f"Summary saved to {summary_file}")

    return results


# ============================================================
# Stage 2: Evidence Challenge
# ============================================================

# Challenger model config
CONTRACTNLI_CHALLENGER = {
    "label": "challenger",
    "name": "google:gemini-3.1-pro-preview",
    "provider": "google",
    "model": "gemini-3.1-pro-preview",
}


def run_stage2_challenge(stage1_results=None, run_dir=None, stage1_dir=None):
    """
    Stage 2: Run evidence challenge on all items from Stage 1.

    For each evaluation item, sends all evaluator outputs + contract text
    to the challenger for legal-specific grounding analysis.

    Args:
        stage1_results: list of Stage 1 result dicts. If None, loads from stage1_dir.
        run_dir: path to save Stage 2 outputs.
        stage1_dir: path to load Stage 1 results from (if stage1_results is None).
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
        normalize_challenge_response,
        CHALLENGER_EXAMPLE_JSON,
    )

    find_and_load_env()

    if run_dir is None:
        run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018"
    if stage1_dir is None:
        stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_017"

    # Load Stage 1 results if not provided
    if stage1_results is None:
        stage1_file = stage1_dir / "results.jsonl"
        if not stage1_file.exists():
            log(f"ERROR: Stage 1 results not found at {stage1_file}")
            log("Run --stage1 or --test-eval first, then --stage2")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results from {stage1_file}")

    # We need the dataset to format contract text
    documents, labels = load_contractnli_dataset(split="dev")
    doc_lookup = {doc["id"]: doc for doc in documents}

    # Load challenger prompt template
    prompt_path = Path(__file__).parent / "prompts" / "evidence_challenge.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up challenger router
    challenger_config = CONTRACTNLI_CHALLENGER
    target = ModelTarget(
        name=challenger_config["name"],
        provider=challenger_config["provider"],
        model=challenger_config["model"],
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=180.0,
        reasoning_effort=challenger_config.get("reasoning_effort"),
    )
    router = ProviderRouter(targets=[target])

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI -- Stage 2: Evidence Challenge")
    log("=" * 70)

    challenge_results = []

    for idx, s1_result in enumerate(stage1_results):
        item_id = s1_result["item_id"]
        contract_id = s1_result["contract_id"]
        hypothesis_id = s1_result["hypothesis_id"]
        hypothesis_text = s1_result["hypothesis_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        # Look up contract for formatting
        doc = doc_lookup.get(contract_id)
        if doc is None:
            log(f"  Skipping {item_id} -- contract {contract_id} not found in dataset")
            continue

        contract_data = extract_contract_data(doc)
        formatted_contract = format_contract_for_prompt(
            contract_data["text"], contract_data["spans"]
        )

        # Format evaluator outputs
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)

        # Fill prompt template
        prompt = prompt_template.replace("{hypothesis_text}", hypothesis_text)
        prompt = prompt.replace("{formatted_contract}", formatted_contract)
        prompt = prompt.replace("{evaluator_outputs}", evaluator_outputs)
        prompt = prompt.replace("{example_json}", CHALLENGER_EXAMPLE_JSON)

        safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
        print()
        print("=" * 70)
        print(f"  Challenge {idx+1}/{len(stage1_results)}: {item_id}")
        print(f"  (gold: {gold_label}, agreement: {agreement})")
        print(f"  Hypothesis: {safe_hyp}...")
        print("=" * 70)

        # Call challenger model
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a grounding auditor for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_challenge_response(raw_response, item_id)
                log(f"    Attempt {attempt}: assessment={normalized.get('overall_grounding_assessment', '???')}, "
                    f"challenges={len(normalized.get('challenges', []))}, "
                    f"schema_valid={normalized.get('schema_valid')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}

        # Display results
        if "error" in normalized and "challenges" not in normalized:
            print(f"  CHALLENGE ERROR: {normalized['error']}")
        else:
            challenges = normalized.get("challenges", [])
            print(f"  Challenges found: {len(challenges)}")
            for ch in challenges:
                ch_type = ch.get("challenge_type", "?")
                severity = ch.get("severity", "?")
                affected = ch.get("affected_evaluators", [])
                desc = ch.get("description", "")[:120]
                missing = ch.get("missing_spans", [])
                print(f"    [{severity.upper()}] {ch_type}: affects {affected}")
                safe_desc = desc.encode("ascii", errors="replace").decode("ascii")
                print(f"      {safe_desc}")
                if missing:
                    print(f"      missing_spans: {missing}")

            reasoning = normalized.get("reasoning", "")[:150]
            safe_reasoning = reasoning.encode("ascii", errors="replace").decode("ascii")
            print(f"  Overall: {normalized.get('overall_grounding_assessment', '?')}")
            print(f"  Reasoning: {safe_reasoning}")
            print(f"  Schema valid: {normalized.get('schema_valid', '?')}")

        # Save raw output
        raw_file = raw_dir / f"{item_id}_challenge.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "item_id": item_id,
                "contract_id": contract_id,
                "hypothesis_id": hypothesis_id,
                "hypothesis_text": hypothesis_text,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "challenger": challenger_config,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        challenge_results.append({
            "item_id": item_id,
            "contract_id": contract_id,
            "hypothesis_id": hypothesis_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "challenge": normalized,
        })

    # Save all challenge results
    results_file = run_dir / "challenge_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in challenge_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\nChallenge results saved to {results_file}")

    # Summary
    total = len(challenge_results)
    strong = sum(1 for r in challenge_results
                 if r["challenge"].get("overall_grounding_assessment") == "strong")
    adequate = sum(1 for r in challenge_results
                   if r["challenge"].get("overall_grounding_assessment") == "adequate")
    weak = sum(1 for r in challenge_results
               if r["challenge"].get("overall_grounding_assessment") == "weak")
    total_challenges = sum(len(r["challenge"].get("challenges", []))
                          for r in challenge_results)

    # Count challenge types
    type_counts = {}
    severity_counts = {}
    for r in challenge_results:
        for ch in r["challenge"].get("challenges", []):
            ct = ch.get("challenge_type", "unknown")
            sv = ch.get("severity", "unknown")
            type_counts[ct] = type_counts.get(ct, 0) + 1
            severity_counts[sv] = severity_counts.get(sv, 0) + 1

    log("")
    log("=" * 70)
    log("  Challenge Summary")
    log("=" * 70)
    log(f"  Items challenged: {total}")
    log(f"  Total challenges fired: {total_challenges}")
    log(f"  Grounding: strong={strong}, adequate={adequate}, weak={weak}")
    if type_counts:
        log(f"  By type: {type_counts}")
    if severity_counts:
        log(f"  By severity: {severity_counts}")
    log("=" * 70)

    return challenge_results


# ============================================================
# Stage 3: Structural Audit
# ============================================================

# Auditor model config
CONTRACTNLI_AUDITOR = {
    "label": "auditor",
    "name": "google:gemini-3.1-pro-preview",
    "provider": "google",
    "model": "gemini-3.1-pro-preview",
}


def run_stage3_audit(stage1_results=None, challenge_results=None,
                     run_dir=None, stage1_dir=None, stage2_dir=None):
    """
    Stage 3: Run structural audit on all items from Stages 1-2.

    For each evaluation item, sends evaluator outputs + challenge results
    + contract text to the auditor for structural validation.

    Args:
        stage1_results: list of Stage 1 result dicts. If None, loads from stage1_dir.
        challenge_results: list of Stage 2 result dicts. If None, loads from stage2_dir.
        run_dir: path to save Stage 3 outputs.
        stage1_dir: path to load Stage 1 results from.
        stage2_dir: path to load Stage 2 results from.
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
    )
    from cam.adapters.contractnli.contractnli_auditor import (
        format_challenge_for_auditor,
        normalize_auditor_response,
        AUDITOR_EXAMPLE_JSON,
    )

    find_and_load_env()

    if run_dir is None:
        run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019"
    if stage1_dir is None:
        stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018_stage1"
    if stage2_dir is None:
        stage2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018"

    # Load Stage 1 results if not provided
    if stage1_results is None:
        stage1_file = stage1_dir / "results.jsonl"
        if not stage1_file.exists():
            log(f"ERROR: Stage 1 results not found at {stage1_file}")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results from {stage1_file}")

    # Load Stage 2 results if not provided
    if challenge_results is None:
        stage2_file = stage2_dir / "challenge_results.jsonl"
        if not stage2_file.exists():
            log(f"ERROR: Stage 2 results not found at {stage2_file}")
            return []
        challenge_results = []
        with open(stage2_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    challenge_results.append(json.loads(line))
        log(f"Loaded {len(challenge_results)} Stage 2 results from {stage2_file}")

    # Build lookup from item_id -> challenge result
    challenge_lookup = {r["item_id"]: r["challenge"] for r in challenge_results}

    # Load dataset for contract text
    documents, labels = load_contractnli_dataset(split="dev")
    doc_lookup = {doc["id"]: doc for doc in documents}

    # Load auditor prompt template
    prompt_path = Path(__file__).parent / "prompts" / "auditor.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up auditor router
    auditor_config = CONTRACTNLI_AUDITOR
    target = ModelTarget(
        name=auditor_config["name"],
        provider=auditor_config["provider"],
        model=auditor_config["model"],
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=180.0,
        reasoning_effort=auditor_config.get("reasoning_effort"),
    )
    router = ProviderRouter(targets=[target])

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI -- Stage 3: Structural Audit")
    log("=" * 70)

    audit_results = []

    for idx, s1_result in enumerate(stage1_results):
        item_id = s1_result["item_id"]
        contract_id = s1_result["contract_id"]
        hypothesis_id = s1_result["hypothesis_id"]
        hypothesis_text = s1_result["hypothesis_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        # Get challenge result for this item
        challenge_result = challenge_lookup.get(item_id, {"error": "No challenge result found"})

        # Look up contract for formatting
        doc = doc_lookup.get(contract_id)
        if doc is None:
            log(f"  Skipping {item_id} -- contract {contract_id} not found in dataset")
            continue

        contract_data = extract_contract_data(doc)
        formatted_contract = format_contract_for_prompt(
            contract_data["text"], contract_data["spans"]
        )

        # Format evaluator outputs and challenge summary
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)
        challenge_summary = format_challenge_for_auditor(challenge_result)

        # Fill prompt template
        prompt = prompt_template.replace("{hypothesis_text}", hypothesis_text)
        prompt = prompt.replace("{formatted_contract}", formatted_contract)
        prompt = prompt.replace("{evaluator_outputs}", evaluator_outputs)
        prompt = prompt.replace("{challenge_summary}", challenge_summary)
        prompt = prompt.replace("{example_json}", AUDITOR_EXAMPLE_JSON)

        safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
        print()
        print("=" * 70)
        print(f"  Audit {idx+1}/{len(stage1_results)}: {item_id}")
        print(f"  (gold: {gold_label}, agreement: {agreement})")
        print(f"  Hypothesis: {safe_hyp}...")
        print("=" * 70)

        # Call auditor model
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a structural auditor for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_auditor_response(raw_response, item_id)
                log(f"    Attempt {attempt}: recommendation={normalized.get('recommendation', '???')}, "
                    f"validity={normalized.get('structural_validity', '???')}, "
                    f"grounding={normalized.get('grounding_quality', '???')}, "
                    f"schema_valid={normalized.get('schema_valid')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}

        # Display results
        if "error" in normalized and "recommendation" not in normalized:
            print(f"  AUDIT ERROR: {normalized['error']}")
        else:
            print(f"  Structural validity: {normalized.get('structural_validity', '?')}")
            print(f"  Constraint compliance: {normalized.get('constraint_compliance', '?')}")
            print(f"  Grounding quality: {normalized.get('grounding_quality', '?')}")
            issues = normalized.get("consistency_issues", [])
            if issues:
                print(f"  Consistency issues ({len(issues)}):")
                for iss in issues:
                    safe_iss = str(iss)[:120].encode("ascii", errors="replace").decode("ascii")
                    print(f"    - {safe_iss}")
            else:
                print(f"  Consistency issues: none")
            survival = normalized.get("challenge_survival", "")[:150]
            safe_survival = survival.encode("ascii", errors="replace").decode("ascii")
            print(f"  Challenge survival: {safe_survival}")
            print(f"  Span overlap: {normalized.get('span_overlap_assessment', '?')}")
            print(f"  Recommendation: {normalized.get('recommendation', '?')}")
            print(f"  Schema valid: {normalized.get('schema_valid', '?')}")

        # Save raw output
        raw_file = raw_dir / f"{item_id}_audit.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "item_id": item_id,
                "contract_id": contract_id,
                "hypothesis_id": hypothesis_id,
                "hypothesis_text": hypothesis_text,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "auditor": auditor_config,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        audit_results.append({
            "item_id": item_id,
            "contract_id": contract_id,
            "hypothesis_id": hypothesis_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "audit": normalized,
        })

    # Save all audit results
    results_file = run_dir / "audit_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in audit_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\nAudit results saved to {results_file}")

    # Summary
    total = len(audit_results)
    proceed_count = sum(1 for r in audit_results
                        if r["audit"].get("recommendation") == "proceed")
    flag_count = sum(1 for r in audit_results
                     if r["audit"].get("recommendation") == "flag")
    escalate_count = sum(1 for r in audit_results
                         if r["audit"].get("recommendation") == "escalate")

    log("")
    log("=" * 70)
    log("  Audit Summary")
    log("=" * 70)
    log(f"  Items audited: {total}")
    log(f"  Proceed: {proceed_count}")
    log(f"  Flag: {flag_count}")
    log(f"  Escalate: {escalate_count}")
    log("=" * 70)

    return audit_results


# ============================================================
# Stage 4: Fragility Detection (programmatic — no LLM call)
# ============================================================

def run_stage4_fragility(stage1_results=None, challenge_results=None,
                         audit_results=None, run_dir=None,
                         stage1_dir=None, stage2_dir=None, stage3_dir=None):
    """
    Stage 4: Run fragility detection on all items from Stages 1-3.

    Programmatic — no API calls. Applies rule library and aggregates
    fragility signals from challenge and auditor outputs.

    Args:
        stage1_results: list of Stage 1 result dicts.
        challenge_results: list of Stage 2 result dicts.
        audit_results: list of Stage 3 result dicts.
        run_dir: path to save Stage 4 outputs.
        stage1_dir, stage2_dir, stage3_dir: paths to load from.
    """
    from cam.adapters.contractnli.contractnli_fragility import compute_fragility_profile

    if run_dir is None:
        run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019"
    if stage1_dir is None:
        stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018_stage1"
    if stage2_dir is None:
        stage2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018"
    if stage3_dir is None:
        stage3_dir = run_dir  # Stage 3 and 4 share the same run_dir by default

    # Load Stage 1 results if not provided
    if stage1_results is None:
        stage1_file = stage1_dir / "results.jsonl"
        if not stage1_file.exists():
            log(f"ERROR: Stage 1 results not found at {stage1_file}")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results from {stage1_file}")

    # Load Stage 2 results if not provided
    if challenge_results is None:
        stage2_file = stage2_dir / "challenge_results.jsonl"
        if not stage2_file.exists():
            log(f"ERROR: Stage 2 results not found at {stage2_file}")
            return []
        challenge_results = []
        with open(stage2_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    challenge_results.append(json.loads(line))
        log(f"Loaded {len(challenge_results)} Stage 2 results from {stage2_file}")

    # Load Stage 3 results if not provided
    if audit_results is None:
        stage3_file = stage3_dir / "audit_results.jsonl"
        if not stage3_file.exists():
            log(f"ERROR: Stage 3 results not found at {stage3_file}")
            return []
        audit_results = []
        with open(stage3_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    audit_results.append(json.loads(line))
        log(f"Loaded {len(audit_results)} Stage 3 results from {stage3_file}")

    # Build lookups
    challenge_lookup = {r["item_id"]: r["challenge"] for r in challenge_results}
    audit_lookup = {r["item_id"]: r["audit"] for r in audit_results}

    run_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI -- Stage 4: Fragility Detection")
    log("=" * 70)

    fragility_results = []

    for idx, s1_result in enumerate(stage1_results):
        item_id = s1_result["item_id"]
        evaluations = s1_result["evaluations"]
        gold_label = s1_result["gold_label"]
        agreement = s1_result["agreement_pattern"]

        challenge_result = challenge_lookup.get(item_id, {})
        auditor_result = audit_lookup.get(item_id, {})

        profile = compute_fragility_profile(evaluations, challenge_result, auditor_result)

        safe_summary = profile["summary"][:120].encode("ascii", errors="replace").decode("ascii")
        print(f"  {item_id} (gold={gold_label}, {agreement}): "
              f"fragile={profile['fragile']}, score={profile['fragility_score']:.2f}, "
              f"signals={profile['signal_count']}, cap={profile['max_cap']}")
        if profile["fired_rules"]:
            print(f"    Rules: {', '.join(profile['fired_rules'])}")
        if profile["signals"]:
            for sig in profile["signals"]:
                safe_desc = sig["description"][:100].encode("ascii", errors="replace").decode("ascii")
                print(f"    [{sig['severity'].upper()}] {sig['source']}: {safe_desc}")

        fragility_results.append({
            "item_id": item_id,
            "contract_id": s1_result["contract_id"],
            "hypothesis_id": s1_result["hypothesis_id"],
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "fragility": profile,
        })

    # Save all fragility results
    results_file = run_dir / "fragility_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in fragility_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\nFragility results saved to {results_file}")

    # Summary
    total = len(fragility_results)
    fragile_count = sum(1 for r in fragility_results if r["fragility"]["fragile"])
    capped = sum(1 for r in fragility_results if r["fragility"]["max_cap"] is not None)
    avg_score = (sum(r["fragility"]["fragility_score"] for r in fragility_results) / total
                 if total > 0 else 0.0)

    # Count rule fires
    rule_counts = {}
    for r in fragility_results:
        for rule_id in r["fragility"]["fired_rules"]:
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

    log("")
    log("=" * 70)
    log("  Fragility Summary")
    log("=" * 70)
    log(f"  Total items: {total}")
    log(f"  Fragile: {fragile_count}/{total}")
    log(f"  Capped: {capped}/{total}")
    log(f"  Avg fragility score: {avg_score:.3f}")
    if rule_counts:
        log(f"  Rule fires: {rule_counts}")
    log("=" * 70)

    return fragility_results


# ============================================================
# Stage 5: Verdict Elimination
# ============================================================

# Elimination model config
CONTRACTNLI_ELIMINATOR = {
    "label": "eliminator",
    "name": "google:gemini-3.1-pro-preview",
    "provider": "google",
    "model": "gemini-3.1-pro-preview",
}


def run_stage5_elimination(stage1_results=None, challenge_results=None,
                           audit_results=None, fragility_results=None,
                           run_dir=None, stage1_dir=None, stage2_dir=None,
                           stage3_dir=None, stage4_dir=None):
    """
    Stage 5: Run verdict elimination on all items from Stages 1-4.

    For each item, stress-tests all 3 possible verdicts and eliminates
    those with fatal flaws.

    Args:
        stage1_results: list of Stage 1 result dicts.
        challenge_results: list of Stage 2 result dicts.
        audit_results: list of Stage 3 result dicts.
        fragility_results: list of Stage 4 result dicts.
        run_dir: path to save Stage 5 outputs.
        stage1_dir..stage4_dir: paths to load from if not provided directly.
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
    )
    from cam.adapters.contractnli.contractnli_auditor import (
        format_challenge_for_auditor,
    )
    from cam.adapters.contractnli.contractnli_elimination import (
        format_evaluator_verdicts_brief,
        format_auditor_summary_brief,
        format_fragility_summary_brief,
        normalize_elimination_response,
        ELIMINATION_EXAMPLE_JSON,
    )

    find_and_load_env()

    if run_dir is None:
        run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_020"
    if stage1_dir is None:
        stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019_stage1"
    if stage2_dir is None:
        stage2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019_stage2"
    if stage3_dir is None:
        stage3_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019"
    if stage4_dir is None:
        stage4_dir = stage3_dir

    # Load all prior stage results if not provided
    if stage1_results is None:
        stage1_file = stage1_dir / "results.jsonl"
        if not stage1_file.exists():
            log(f"ERROR: Stage 1 results not found at {stage1_file}")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results")

    if challenge_results is None:
        stage2_file = stage2_dir / "challenge_results.jsonl"
        if not stage2_file.exists():
            log(f"ERROR: Stage 2 results not found at {stage2_file}")
            return []
        challenge_results = []
        with open(stage2_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    challenge_results.append(json.loads(line))
        log(f"Loaded {len(challenge_results)} Stage 2 results")

    if audit_results is None:
        stage3_file = stage3_dir / "audit_results.jsonl"
        if not stage3_file.exists():
            log(f"ERROR: Stage 3 results not found at {stage3_file}")
            return []
        audit_results = []
        with open(stage3_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    audit_results.append(json.loads(line))
        log(f"Loaded {len(audit_results)} Stage 3 results")

    if fragility_results is None:
        stage4_file = stage4_dir / "fragility_results.jsonl"
        if not stage4_file.exists():
            log(f"ERROR: Stage 4 results not found at {stage4_file}")
            return []
        fragility_results = []
        with open(stage4_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    fragility_results.append(json.loads(line))
        log(f"Loaded {len(fragility_results)} Stage 4 results")

    # Build lookups
    challenge_lookup = {r["item_id"]: r["challenge"] for r in challenge_results}
    audit_lookup = {r["item_id"]: r["audit"] for r in audit_results}
    fragility_lookup = {r["item_id"]: r["fragility"] for r in fragility_results}

    # Load dataset for contract text
    documents, labels = load_contractnli_dataset(split="dev")
    doc_lookup = {doc["id"]: doc for doc in documents}

    # Load elimination prompt template
    prompt_path = Path(__file__).parent / "prompts" / "verdict_elimination.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up elimination router
    elim_config = CONTRACTNLI_ELIMINATOR
    target = ModelTarget(
        name=elim_config["name"],
        provider=elim_config["provider"],
        model=elim_config["model"],
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=180.0,
        reasoning_effort=elim_config.get("reasoning_effort"),
    )
    router = ProviderRouter(targets=[target])

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI -- Stage 5: Verdict Elimination")
    log("=" * 70)

    elimination_results = []

    for idx, s1_result in enumerate(stage1_results):
        item_id = s1_result["item_id"]
        contract_id = s1_result["contract_id"]
        hypothesis_id = s1_result["hypothesis_id"]
        hypothesis_text = s1_result["hypothesis_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        challenge_result = challenge_lookup.get(item_id, {})
        auditor_result = audit_lookup.get(item_id, {})
        fragility_profile = fragility_lookup.get(item_id, {})

        # Look up contract for formatting
        doc = doc_lookup.get(contract_id)
        if doc is None:
            log(f"  Skipping {item_id} -- contract {contract_id} not found")
            continue

        contract_data = extract_contract_data(doc)
        formatted_contract = format_contract_for_prompt(
            contract_data["text"], contract_data["spans"]
        )

        # Format prompt sections
        evaluator_verdicts = format_evaluator_verdicts_brief(evaluations)
        challenge_summary = format_challenge_for_auditor(challenge_result)
        auditor_summary = format_auditor_summary_brief(auditor_result)
        fragility_summary = format_fragility_summary_brief(fragility_profile)

        # Fill prompt template
        prompt = prompt_template.replace("{hypothesis_text}", hypothesis_text)
        prompt = prompt.replace("{formatted_contract}", formatted_contract)
        prompt = prompt.replace("{evaluator_verdicts}", evaluator_verdicts)
        prompt = prompt.replace("{challenge_summary}", challenge_summary)
        prompt = prompt.replace("{auditor_summary}", auditor_summary)
        prompt = prompt.replace("{fragility_summary}", fragility_summary)
        prompt = prompt.replace("{example_json}", ELIMINATION_EXAMPLE_JSON)

        # Add agreement pattern and unanimous instruction
        prompt = prompt.replace("{agreement_pattern}", agreement)
        if "3-0" in agreement:
            unanimous_instruction = (
                "All three independent evaluators (using different AI providers) reached the same verdict. "
                "Unanimous agreement from independent models is a strong signal. To kill the unanimous verdict, "
                "you MUST identify a specific fatal flaw from the closed taxonomy above — not merely a concern, "
                "weakness, or technicality. If you cannot identify a clear fatal flaw with a specific span citation, "
                "the unanimous verdict SURVIVES."
            )
        elif "2-1" in agreement:
            unanimous_instruction = (
                "Two evaluators agreed on a majority verdict. The majority verdict carries weight "
                "but is not as strong as unanimity. Apply the standard kill criteria."
            )
        else:
            unanimous_instruction = (
                "No evaluator agreement — full three-way split. All verdicts should be evaluated "
                "equally with no presumption of correctness."
            )
        prompt = prompt.replace("{unanimous_instruction}", unanimous_instruction)

        safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
        print()
        print("=" * 70)
        print(f"  Elimination {idx+1}/{len(stage1_results)}: {item_id}")
        print(f"  (gold: {gold_label}, agreement: {agreement})")
        print(f"  Hypothesis: {safe_hyp}...")
        print("=" * 70)

        # Call elimination model
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a verdict stress tester for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_elimination_response(raw_response, item_id)
                surviving = normalized.get("surviving_verdicts", [])
                eliminated = normalized.get("eliminated_verdicts", [])
                recommended = normalized.get("recommended_verdict", "?")
                log(f"    Attempt {attempt}: surviving={surviving}, eliminated={eliminated}, "
                    f"recommended={recommended}, schema_valid={normalized.get('schema_valid')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}

        # Display results
        if "error" in normalized and "verdict_assessments" not in normalized:
            print(f"  ELIMINATION ERROR: {normalized['error']}")
        else:
            for va in normalized.get("verdict_assessments", []):
                if isinstance(va, dict):
                    v = va.get("verdict", "?")
                    surv = "SURVIVES" if va.get("survives") else "KILLED"
                    conf = va.get("confidence_if_selected", "?")
                    objection = va.get("strongest_objection", "")[:100]
                    safe_obj = objection.encode("ascii", errors="replace").decode("ascii")
                    print(f"    {v}: {surv} (confidence={conf})")
                    print(f"      Objection: {safe_obj}")
                    weakness = va.get("critical_weakness")
                    if weakness:
                        safe_weak = str(weakness)[:100].encode("ascii", errors="replace").decode("ascii")
                        print(f"      Weakness: {safe_weak}")
            print(f"  Recommended: {normalized.get('recommended_verdict', '?')}")
            print(f"  Schema valid: {normalized.get('schema_valid', '?')}")

        # Save raw output
        raw_file = raw_dir / f"{item_id}_elimination.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "item_id": item_id,
                "contract_id": contract_id,
                "hypothesis_id": hypothesis_id,
                "hypothesis_text": hypothesis_text,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "eliminator": elim_config,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        elimination_results.append({
            "item_id": item_id,
            "contract_id": contract_id,
            "hypothesis_id": hypothesis_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "elimination": normalized,
        })

    # Save all elimination results
    results_file = run_dir / "elimination_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in elimination_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\nElimination results saved to {results_file}")

    # Summary
    total = len(elimination_results)
    single_survivor = sum(
        1 for r in elimination_results
        if len(r["elimination"].get("surviving_verdicts", [])) == 1
    )
    multi_survivor = sum(
        1 for r in elimination_results
        if len(r["elimination"].get("surviving_verdicts", [])) >= 2
    )
    all_survive = sum(
        1 for r in elimination_results
        if len(r["elimination"].get("surviving_verdicts", [])) == 3
    )

    log("")
    log("=" * 70)
    log("  Elimination Summary")
    log("=" * 70)
    log(f"  Total items: {total}")
    log(f"  Single survivor: {single_survivor}")
    log(f"  Multiple survivors: {multi_survivor}")
    log(f"  All 3 survive: {all_survive}")
    log("=" * 70)

    return elimination_results


# ============================================================
# Stage 6: Disposition (programmatic — no LLM call)
# ============================================================

def run_stage6_disposition(stage1_results=None, challenge_results=None,
                           audit_results=None, fragility_results=None,
                           elimination_results=None, run_dir=None,
                           stage1_dir=None, stage2_dir=None,
                           stage3_dir=None, stage4_dir=None, stage5_dir=None):
    """
    Stage 6: Compute final disposition for all items.

    Programmatic — no API calls. Combines all prior stages into terminal
    state and commitment level.
    """
    from cam.adapters.contractnli.contractnli_disposition import (
        compute_disposition,
        compare_to_gold,
        format_pipeline_summary,
    )

    if run_dir is None:
        run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_020"
    if stage1_dir is None:
        stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019_stage1"
    if stage2_dir is None:
        stage2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019_stage2"
    if stage3_dir is None:
        stage3_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019"
    if stage4_dir is None:
        stage4_dir = stage3_dir
    if stage5_dir is None:
        stage5_dir = run_dir

    # Load all prior stage results if not provided
    def _load_jsonl(path, label):
        if not path.exists():
            log(f"ERROR: {label} not found at {path}")
            return None
        results = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
        log(f"Loaded {len(results)} {label}")
        return results

    if stage1_results is None:
        stage1_results = _load_jsonl(stage1_dir / "results.jsonl", "Stage 1 results")
        if stage1_results is None:
            return []
    if challenge_results is None:
        challenge_results = _load_jsonl(stage2_dir / "challenge_results.jsonl", "Stage 2 results")
        if challenge_results is None:
            return []
    if audit_results is None:
        audit_results = _load_jsonl(stage3_dir / "audit_results.jsonl", "Stage 3 results")
        if audit_results is None:
            return []
    if fragility_results is None:
        fragility_results = _load_jsonl(stage4_dir / "fragility_results.jsonl", "Stage 4 results")
        if fragility_results is None:
            return []
    if elimination_results is None:
        elimination_results = _load_jsonl(stage5_dir / "elimination_results.jsonl", "Stage 5 results")
        if elimination_results is None:
            return []

    # Build lookups
    challenge_lookup = {r["item_id"]: r["challenge"] for r in challenge_results}
    audit_lookup = {r["item_id"]: r["audit"] for r in audit_results}
    fragility_lookup = {r["item_id"]: r["fragility"] for r in fragility_results}
    elimination_lookup = {r["item_id"]: r["elimination"] for r in elimination_results}

    run_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI -- Stage 6: Disposition")
    log("=" * 70)

    disposition_results = []

    for idx, s1_result in enumerate(stage1_results):
        item_id = s1_result["item_id"]
        hypothesis_text = s1_result["hypothesis_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]

        challenge_result = challenge_lookup.get(item_id, {})
        auditor_result = audit_lookup.get(item_id, {})
        fragility_profile = fragility_lookup.get(item_id, {})
        elimination_result = elimination_lookup.get(item_id, {})

        # Compute disposition
        disposition = compute_disposition(
            evaluations, challenge_result, auditor_result,
            fragility_profile, elimination_result,
        )

        # Gold comparison (post-hoc)
        gold_comp = compare_to_gold(disposition, gold_label)

        # Display
        terminal = disposition["terminal_state"]
        level = disposition["commitment_level"]
        label = disposition["commitment_label"]
        selected = disposition.get("selected_verdict", "NONE")
        conviction = disposition.get("conviction_score", 0)
        match_marker = "OK" if gold_comp["gold_match"] else ("WH" if gold_comp["withheld"] else "X")

        print(f"  {item_id}: {terminal} ({level}, {label})")
        print(f"    selected={selected}, conviction={conviction:.3f}, gold={gold_label} [{match_marker}]")
        if disposition.get("downgrade_reasons"):
            for reason in disposition["downgrade_reasons"][:3]:
                safe_reason = str(reason)[:100].encode("ascii", errors="replace").decode("ascii")
                print(f"    downgrade: {safe_reason}")

        # Generate pipeline summary
        summary = format_pipeline_summary(
            item_id, hypothesis_text, gold_label, evaluations,
            challenge_result, auditor_result, fragility_profile,
            elimination_result, disposition, gold_comp,
        )

        disposition_results.append({
            "item_id": item_id,
            "contract_id": s1_result["contract_id"],
            "hypothesis_id": s1_result["hypothesis_id"],
            "gold_label": gold_label,
            "disposition": disposition,
            "gold_comparison": gold_comp,
            "pipeline_summary": summary,
        })

    # Save all disposition results
    results_file = run_dir / "disposition_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\nDisposition results saved to {results_file}")

    # Save pipeline summaries to a readable text file
    summary_file = run_dir / "pipeline_summaries.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(r["pipeline_summary"] + "\n\n")
    log(f"Pipeline summaries saved to {summary_file}")

    # Summary metrics
    total = len(disposition_results)
    asserted = [r for r in disposition_results if not r["gold_comparison"]["withheld"]]
    withheld = [r for r in disposition_results if r["gold_comparison"]["withheld"]]
    correct = sum(1 for r in asserted if r["gold_comparison"]["gold_match"])

    cca = correct / len(asserted) if asserted else 0.0
    abstention_rate = len(withheld) / total if total > 0 else 0.0

    # Commitment level distribution
    level_dist = Counter()
    for r in disposition_results:
        level_dist[r["disposition"]["commitment_level"]] += 1

    # Terminal state distribution
    state_dist = Counter()
    for r in disposition_results:
        state_dist[r["disposition"]["terminal_state"]] += 1

    log("")
    log("=" * 70)
    log("  Disposition Summary")
    log("=" * 70)
    log(f"  Total items: {total}")
    log(f"  Asserted: {len(asserted)}, Withheld: {len(withheld)}")
    log(f"  CCA (correct / asserted): {correct}/{len(asserted)} = {cca:.3f}")
    log(f"  Abstention rate: {abstention_rate:.3f}")
    log(f"  Terminal states: {dict(state_dist)}")
    log(f"  Commitment levels: {dict(level_dist)}")
    log("=" * 70)

    return disposition_results


# ============================================================
# Full Pipeline: Unified per-item orchestration (Step 021)
# ============================================================

def _load_completed_items(results_file):
    """Load item_ids already processed in a previous run (for resume support)."""
    completed = set()
    if results_file.exists():
        with open(results_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        completed.add(record["item_id"])
                    except (json.JSONDecodeError, KeyError):
                        pass
    return completed


def _run_single_item_pipeline(item, doc_lookup, labels, routers, challenger_router,
                              auditor_router, eliminator_router, run_dir, raw_dir,
                              prompt_templates, item_idx, total_items,
                              enrich=False):
    """
    Run the full 6-stage pipeline for a single (contract, hypothesis) pair.

    Args:
        enrich: If True, run legal context enrichment before the challenge stage.

    Returns a combined result dict with all stage outputs.
    """
    from cam.adapters.contractnli.contractnli_evaluate import compute_agreement_pattern
    from cam.adapters.contractnli.contractnli_normalize import normalize_evaluator_response
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
        normalize_challenge_response,
        CHALLENGER_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_auditor import (
        format_challenge_for_auditor,
        normalize_auditor_response,
        AUDITOR_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_elimination import (
        format_evaluator_verdicts_brief,
        format_auditor_summary_brief,
        format_fragility_summary_brief,
        normalize_elimination_response,
        ELIMINATION_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_fragility import compute_fragility_profile
    from cam.adapters.contractnli.contractnli_disposition import (
        compute_disposition,
        compare_to_gold,
        format_pipeline_summary,
    )

    item_id = item["item_id"]
    contract_id = item["contract_id"]
    hypothesis_id = item["hypothesis_id"]
    hypothesis_text = item["claim"]
    gold_label = item["gold_label"]

    doc = doc_lookup.get(contract_id)
    if doc is None:
        log(f"  Skipping {item_id} -- contract {contract_id} not found")
        return None

    contract_data = extract_contract_data(doc)
    formatted_contract = format_contract_for_prompt(contract_data["text"], contract_data["spans"])

    safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
    print()
    print("=" * 70)
    print(f"  [{item_idx}/{total_items}] {item_id} (gold: {gold_label})")
    print(f"  Hypothesis [{hypothesis_id}]: {safe_hyp}...")
    print("=" * 70)

    # Create per-item raw directory
    item_raw_dir = raw_dir / item_id
    item_raw_dir.mkdir(parents=True, exist_ok=True)

    # ---- STAGE 1: Parallel Evaluation ----
    log("  Stage 1: Parallel Evaluation")
    eval_prompt = prompt_templates["evaluator"]
    eval_prompt_filled = eval_prompt.replace("{hypothesis_text}", hypothesis_text)
    eval_prompt_filled = eval_prompt_filled.replace("{formatted_contract}", formatted_contract)
    from cam.adapters.contractnli.contractnli_evaluate import EVALUATOR_EXAMPLE_JSON
    eval_prompt_filled = eval_prompt_filled.replace("{example_json}", EVALUATOR_EXAMPLE_JSON)

    evaluations = {}
    for ev_label, router in routers.items():
        log(f"    Evaluator {ev_label}...")
        raw_response = ""
        normalized = None
        meta = None
        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a legal contract entailment evaluator. Respond only with valid JSON.",
                    user_prompt=eval_prompt_filled,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_evaluator_response(raw_response, f"Evaluator {ev_label}")
                log(f"      verdict={normalized.get('verdict', '???')}, confidence={normalized.get('confidence', '???')}")
                break
            except Exception as e:
                log(f"      Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}

        evaluations[ev_label] = normalized
        eval_file = item_raw_dir / f"evaluator_{ev_label}.json"
        with open(eval_file, "w", encoding="utf-8") as f:
            json.dump({"raw_response": raw_response, "normalized": normalized, "meta": meta}, f, indent=2, default=str)

    pattern, majority_verdict = compute_agreement_pattern(evaluations)
    gold_match_majority = (majority_verdict == gold_label) if majority_verdict else False
    log(f"    Agreement: {pattern}, gold_match={gold_match_majority}")

    # ---- STAGE 2a: Legal Context Enrichment (optional) ----
    enrichment_data = None
    enrichment_context_block = ""
    if enrich:
        log("  Stage 2a: Legal Context Enrichment")
        from cam.adapters.contractnli.contractnli_context_enrichment import (
            run_enrichment,
            format_enrichment_for_challenge,
        )
        enrichment_data = run_enrichment(evaluations, hypothesis_text, hypothesis_id)
        enrichment_context_block = format_enrichment_for_challenge(enrichment_data)

        # Save enrichment data
        enrichment_file = item_raw_dir / f"{item_id}_enrichment.json"
        with open(enrichment_file, "w", encoding="utf-8") as f:
            json.dump(enrichment_data, f, indent=2, default=str)

        n_found = len([c for c in enrichment_data.get("concepts_searched", []) if c.get("context_found")])
        n_total = len(enrichment_data.get("concepts_searched", []))
        log(f"    Enrichment: {n_found}/{n_total} concepts resolved")
    else:
        log("  Stage 2a: Enrichment SKIPPED (--enrich not set)")

    # ---- STAGE 2: Evidence Challenge ----
    log("  Stage 2: Evidence Challenge")
    evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)
    challenge_prompt = prompt_templates["challenge"]
    challenge_prompt = challenge_prompt.replace("{hypothesis_text}", hypothesis_text)
    challenge_prompt = challenge_prompt.replace("{formatted_contract}", formatted_contract)
    challenge_prompt = challenge_prompt.replace("{evaluator_outputs}", evaluator_outputs)
    challenge_prompt = challenge_prompt.replace("{example_json}", CHALLENGER_EXAMPLE_JSON)

    # Inject enrichment context into challenge prompt (if available)
    if enrichment_context_block:
        challenge_prompt = challenge_prompt + "\n" + enrichment_context_block

    challenge_normalized = None
    for attempt in range(1, 3):
        try:
            raw_obj, meta = challenger_router.call_json(
                system_prompt="You are a grounding auditor for legal contract entailment. Respond only with valid JSON.",
                user_prompt=challenge_prompt,
            )
            raw_response = json.dumps(raw_obj)
            challenge_normalized = normalize_challenge_response(raw_response, item_id)
            log(f"    grounding={challenge_normalized.get('overall_grounding_assessment', '???')}, "
                f"challenges={len(challenge_normalized.get('challenges', []))}")
            break
        except Exception as e:
            log(f"    Attempt {attempt} failed: {e}")
            if attempt == 2:
                challenge_normalized = {"error": f"API call failed after 2 attempts: {e}"}

    with open(item_raw_dir / f"{item_id}_challenge.json", "w", encoding="utf-8") as f:
        json.dump({"normalized": challenge_normalized}, f, indent=2, default=str)

    # ---- STAGE 3: Structural Audit ----
    log("  Stage 3: Structural Audit")
    challenge_summary = format_challenge_for_auditor(challenge_normalized)
    audit_prompt = prompt_templates["auditor"]
    audit_prompt = audit_prompt.replace("{hypothesis_text}", hypothesis_text)
    audit_prompt = audit_prompt.replace("{formatted_contract}", formatted_contract)
    audit_prompt = audit_prompt.replace("{evaluator_outputs}", evaluator_outputs)
    audit_prompt = audit_prompt.replace("{challenge_summary}", challenge_summary)
    audit_prompt = audit_prompt.replace("{example_json}", AUDITOR_EXAMPLE_JSON)

    audit_normalized = None
    for attempt in range(1, 3):
        try:
            raw_obj, meta = auditor_router.call_json(
                system_prompt="You are a structural auditor for legal contract entailment. Respond only with valid JSON.",
                user_prompt=audit_prompt,
            )
            raw_response = json.dumps(raw_obj)
            audit_normalized = normalize_auditor_response(raw_response, item_id)
            log(f"    recommendation={audit_normalized.get('recommendation', '???')}, "
                f"validity={audit_normalized.get('structural_validity', '???')}")
            break
        except Exception as e:
            log(f"    Attempt {attempt} failed: {e}")
            if attempt == 2:
                audit_normalized = {"error": f"API call failed after 2 attempts: {e}"}

    with open(item_raw_dir / f"{item_id}_audit.json", "w", encoding="utf-8") as f:
        json.dump({"normalized": audit_normalized}, f, indent=2, default=str)

    # ---- STAGE 4: Fragility Detection (programmatic) ----
    log("  Stage 4: Fragility Detection")
    fragility_profile = compute_fragility_profile(evaluations, challenge_normalized, audit_normalized)
    log(f"    fragile={fragility_profile['fragile']}, score={fragility_profile['fragility_score']:.2f}, "
        f"rules={fragility_profile['fired_rules']}")

    # ---- STAGE 5: Verdict Elimination ----
    log("  Stage 5: Verdict Elimination")
    evaluator_verdicts = format_evaluator_verdicts_brief(evaluations)
    auditor_summary = format_auditor_summary_brief(audit_normalized)
    fragility_summary = format_fragility_summary_brief(fragility_profile)
    elim_prompt = prompt_templates["elimination"]
    elim_prompt = elim_prompt.replace("{hypothesis_text}", hypothesis_text)
    elim_prompt = elim_prompt.replace("{formatted_contract}", formatted_contract)
    elim_prompt = elim_prompt.replace("{evaluator_verdicts}", evaluator_verdicts)
    elim_prompt = elim_prompt.replace("{challenge_summary}", challenge_summary)
    elim_prompt = elim_prompt.replace("{auditor_summary}", auditor_summary)
    elim_prompt = elim_prompt.replace("{fragility_summary}", fragility_summary)
    elim_prompt = elim_prompt.replace("{example_json}", ELIMINATION_EXAMPLE_JSON)

    # Add agreement pattern and unanimous instruction for elimination context
    elim_prompt = elim_prompt.replace("{agreement_pattern}", pattern)
    if "3-0" in pattern:
        unanimous_instruction = (
            "All three independent evaluators (using different AI providers) reached the same verdict. "
            "Unanimous agreement from independent models is a strong signal. To kill the unanimous verdict, "
            "you MUST identify a specific fatal flaw from the closed taxonomy above — not merely a concern, "
            "weakness, or technicality. If you cannot identify a clear fatal flaw with a specific span citation, "
            "the unanimous verdict SURVIVES."
        )
    elif "2-1" in pattern:
        unanimous_instruction = (
            "Two evaluators agreed on a majority verdict. The majority verdict carries weight "
            "but is not as strong as unanimity. Apply the standard kill criteria."
        )
    else:
        unanimous_instruction = (
            "No evaluator agreement — full three-way split. All verdicts should be evaluated "
            "equally with no presumption of correctness."
        )
    elim_prompt = elim_prompt.replace("{unanimous_instruction}", unanimous_instruction)

    elimination_normalized = None
    for attempt in range(1, 3):
        try:
            raw_obj, meta = eliminator_router.call_json(
                system_prompt="You are a verdict stress tester for legal contract entailment. Respond only with valid JSON.",
                user_prompt=elim_prompt,
            )
            raw_response = json.dumps(raw_obj)
            elimination_normalized = normalize_elimination_response(raw_response, item_id)
            log(f"    surviving={elimination_normalized.get('surviving_verdicts', [])}, "
                f"recommended={elimination_normalized.get('recommended_verdict', '?')}")
            break
        except Exception as e:
            log(f"    Attempt {attempt} failed: {e}")
            if attempt == 2:
                elimination_normalized = {"error": f"API call failed after 2 attempts: {e}"}

    with open(item_raw_dir / f"{item_id}_elimination.json", "w", encoding="utf-8") as f:
        json.dump({"normalized": elimination_normalized}, f, indent=2, default=str)

    # ---- STAGE 6: Disposition (programmatic) ----
    log("  Stage 6: Disposition")
    disposition = compute_disposition(
        evaluations, challenge_normalized, audit_normalized,
        fragility_profile, elimination_normalized,
    )
    gold_comp = compare_to_gold(disposition, gold_label)

    terminal = disposition["terminal_state"]
    level = disposition["commitment_level"]
    label = disposition["commitment_label"]
    conviction = disposition.get("conviction_score", 0)
    match_marker = "OK" if gold_comp["gold_match"] else ("WH" if gold_comp["withheld"] else "X")
    log(f"    -> {terminal} ({level}, {label}), conviction={conviction:.3f}, gold={gold_label} [{match_marker}]")

    # Generate pipeline summary
    summary = format_pipeline_summary(
        item_id, hypothesis_text, gold_label, evaluations,
        challenge_normalized, audit_normalized, fragility_profile,
        elimination_normalized, disposition, gold_comp,
    )

    # Build combined result record
    result = {
        "item_id": item_id,
        "contract_id": contract_id,
        "hypothesis_id": hypothesis_id,
        "hypothesis_text": hypothesis_text,
        "evaluator_verdicts": {
            lbl: {"verdict": ev.get("verdict"), "confidence": ev.get("confidence")}
            for lbl, ev in evaluations.items()
        },
        "cited_spans_per_evaluator": {
            lbl: ev.get("cited_spans", []) for lbl, ev in evaluations.items()
        },
        "agreement_pattern": pattern,
        "majority_verdict": majority_verdict,
        "challenge_summary": {
            "overall_grounding": challenge_normalized.get("overall_grounding_assessment"),
            "challenge_count": len(challenge_normalized.get("challenges", [])),
            "challenge_types": [ch.get("challenge_type") for ch in challenge_normalized.get("challenges", [])],
        },
        "auditor_assessment": {
            "structural_validity": audit_normalized.get("structural_validity"),
            "grounding_quality": audit_normalized.get("grounding_quality"),
            "recommendation": audit_normalized.get("recommendation"),
            "span_overlap": audit_normalized.get("span_overlap_assessment"),
        },
        "fragility_score": fragility_profile["fragility_score"],
        "triggered_rules": fragility_profile["fired_rules"],
        "fragile": fragility_profile["fragile"],
        "fragility_cap": fragility_profile["max_cap"],
        "verdict_elimination": {
            "surviving_verdicts": elimination_normalized.get("surviving_verdicts", []),
            "eliminated_verdicts": elimination_normalized.get("eliminated_verdicts", []),
            "recommended_verdict": elimination_normalized.get("recommended_verdict"),
        },
        "terminal_state": terminal,
        "commitment_level": level,
        "commitment_label": label,
        "conviction_score": conviction,
        "downgrade_reasons": disposition.get("downgrade_reasons", []),
        "gold_label": gold_label,
        "gold_match": gold_comp["gold_match"],
        "withheld": gold_comp["withheld"],
        "enrichment_performed": enrichment_data.get("enrichment_performed", False) if enrichment_data else False,
        "enrichment_summary": enrichment_data.get("enrichment_summary", "") if enrichment_data else "",
    }

    return result, summary


def run_full_pipeline(n_contracts=10, seed=1337, run_label="1 ContractNLI Run", enrich=False,
                      contract_ids=None):
    """
    Full pipeline: iterate over sampled contracts, run all 6 stages per item,
    save per-item results, then compute metrics and summaries.

    Args:
        enrich: If True, enable legal context enrichment before the challenge stage.
        contract_ids: If provided, filter to only these contract IDs (list of ints).

    Supports resume: if the run was interrupted, restarting picks up where it left off.
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.contractnli.contractnli_evaluate import CONTRACTNLI_EVALUATORS

    find_and_load_env()

    log("=" * 70)
    log("  CAM ContractNLI -- Full Pipeline")
    log(f"  Contracts: {n_contracts}, Seed: {seed}, Enrichment: {'ON' if enrich else 'OFF'}")
    if contract_ids:
        log(f"  Contract filter: {contract_ids}")
    log("=" * 70)

    # Load dataset
    documents, labels = load_contractnli_dataset(split="dev")
    sampled_docs = sample_contracts(documents, labels, n=n_contracts, seed=seed)

    # Apply contract ID filter if specified
    if contract_ids:
        sampled_docs = [doc for doc in sampled_docs if doc["id"] in contract_ids]
        log(f"  Filtered to {len(sampled_docs)} contracts matching --contracts filter")

    doc_lookup = {doc["id"]: doc for doc in documents}

    # Build all evaluation items
    all_items = []
    for doc in sampled_docs:
        cdata = extract_contract_data(doc)
        items = build_evaluation_items(cdata, labels)
        all_items.extend(items)

    total_items = len(all_items)
    log(f"  Total evaluation items: {total_items}")

    # Set up run directory
    run_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / run_label
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Check for resume
    results_file = run_dir / "results.jsonl"
    completed_ids = _load_completed_items(results_file)
    if completed_ids:
        log(f"  Resuming: {len(completed_ids)} items already completed, "
            f"{total_items - len(completed_ids)} remaining")

    # Set up model routers
    # Per-evaluator timeouts: GPT-5.2 (B) gets 180s, others get 300s
    evaluator_timeouts = {"B": 180.0}
    evaluator_routers = {}
    for ev in CONTRACTNLI_EVALUATORS:
        target = ModelTarget(
            name=ev["name"], provider=ev["provider"], model=ev["model"],
            priority=1, max_output_tokens=8192, temperature=0.0,
            timeout_sec=evaluator_timeouts.get(ev["label"], 300.0),
            reasoning_effort=ev.get("reasoning_effort"),
        )
        evaluator_routers[ev["label"]] = ProviderRouter(targets=[target])

    challenger_target = ModelTarget(
        name=CONTRACTNLI_CHALLENGER["name"], provider=CONTRACTNLI_CHALLENGER["provider"],
        model=CONTRACTNLI_CHALLENGER["model"], priority=1, max_output_tokens=8192,
        temperature=0.0, timeout_sec=300.0,
        reasoning_effort=CONTRACTNLI_CHALLENGER.get("reasoning_effort"),
    )
    challenger_router = ProviderRouter(targets=[challenger_target])

    auditor_target = ModelTarget(
        name=CONTRACTNLI_AUDITOR["name"], provider=CONTRACTNLI_AUDITOR["provider"],
        model=CONTRACTNLI_AUDITOR["model"], priority=1, max_output_tokens=8192,
        temperature=0.0, timeout_sec=300.0,
        reasoning_effort=CONTRACTNLI_AUDITOR.get("reasoning_effort"),
    )
    auditor_router = ProviderRouter(targets=[auditor_target])

    eliminator_target = ModelTarget(
        name=CONTRACTNLI_ELIMINATOR["name"], provider=CONTRACTNLI_ELIMINATOR["provider"],
        model=CONTRACTNLI_ELIMINATOR["model"], priority=1, max_output_tokens=8192,
        temperature=0.0, timeout_sec=300.0,
        reasoning_effort=CONTRACTNLI_ELIMINATOR.get("reasoning_effort"),
    )
    eliminator_router = ProviderRouter(targets=[eliminator_target])

    # Load prompt templates
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_templates = {
        "evaluator": (prompts_dir / "evaluator.txt").read_text(encoding="utf-8"),
        "challenge": (prompts_dir / "evidence_challenge.txt").read_text(encoding="utf-8"),
        "auditor": (prompts_dir / "auditor.txt").read_text(encoding="utf-8"),
        "elimination": (prompts_dir / "verdict_elimination.txt").read_text(encoding="utf-8"),
    }

    # Write run manifest
    manifest = {
        "run_label": run_label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "n_contracts": n_contracts,
        "total_items": total_items,
        "sampled_contract_ids": [doc["id"] for doc in sampled_docs],
        "models": {
            "evaluator_A": CONTRACTNLI_EVALUATORS[0]["name"],
            "evaluator_B": CONTRACTNLI_EVALUATORS[1]["name"],
            "evaluator_C": CONTRACTNLI_EVALUATORS[2]["name"],
            "challenger": CONTRACTNLI_CHALLENGER["name"],
            "auditor": CONTRACTNLI_AUDITOR["name"],
            "eliminator": CONTRACTNLI_ELIMINATOR["name"],
        },
        "pipeline_version": "6-stage (eval, challenge, audit, fragility, elimination, disposition)",
        "enrichment_enabled": enrich,
        "enrichment_model": "gemini-3.1-pro-preview (with google_search)" if enrich else None,
    }
    manifest_file = run_dir / "run_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log(f"  Manifest saved to {manifest_file}")

    # ---- Main evaluation loop ----
    all_results = []
    all_summaries = []
    current_contract_id = None
    contract_counter = 0

    for item_idx, item in enumerate(all_items):
        # Track contract progress
        if item["contract_id"] != current_contract_id:
            contract_counter += 1
            current_contract_id = item["contract_id"]
            log(f"\n--- Contract {contract_counter}/{n_contracts} (id={current_contract_id}) ---")

        # Skip already-completed items (resume)
        if item["item_id"] in completed_ids:
            log(f"  [{item_idx+1}/{total_items}] {item['item_id']} -- SKIP (already completed)")
            # Reload the result from file for metrics
            with open(results_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rec = json.loads(line)
                        if rec["item_id"] == item["item_id"]:
                            all_results.append(rec)
                            break
            continue

        try:
            result, summary = _run_single_item_pipeline(
                item, doc_lookup, labels,
                evaluator_routers, challenger_router, auditor_router, eliminator_router,
                run_dir, raw_dir, prompt_templates,
                item_idx + 1, total_items,
                enrich=enrich,
            )
        except Exception as e:
            log(f"  FATAL ERROR on {item['item_id']}: {e}")
            log(f"  Saving progress and stopping. Resume with the same command.")
            import traceback
            traceback.print_exc()
            break

        if result is None:
            continue

        all_results.append(result)
        all_summaries.append(summary)

        # Append to results file (for resume support)
        with open(results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, default=str) + "\n")

        # Append to summaries file
        summaries_file = run_dir / "pipeline_summaries.txt"
        with open(summaries_file, "a", encoding="utf-8") as f:
            f.write(summary + "\n\n")

    log(f"\n  Pipeline complete: {len(all_results)}/{total_items} items processed.")

    if not all_results:
        log("  No results to compute metrics on.")
        return

    # ---- Contract-level summaries ----
    log("\n  Computing contract-level summaries...")
    contract_summaries = _compute_contract_summaries(all_results, sampled_docs)
    summaries_out = run_dir / "contract_summaries.jsonl"
    with open(summaries_out, "w", encoding="utf-8") as f:
        for cs in contract_summaries:
            f.write(json.dumps(cs, default=str) + "\n")
    log(f"  Contract summaries saved to {summaries_out}")

    # ---- Metrics ----
    log("\n  Computing metrics...")
    metrics = compute_contractnli_metrics(all_results, labels)
    metrics_file = run_dir / "metrics_summary.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    log(f"  Metrics saved to {metrics_file}")

    # ---- Post-run summary ----
    _print_post_run_summary(all_results, metrics, labels)

    return all_results


# ============================================================
# Contract-Level Summaries
# ============================================================

def _compute_contract_summaries(results, sampled_docs):
    """Compute per-contract summary statistics."""
    # Group results by contract_id
    by_contract = defaultdict(list)
    for r in results:
        by_contract[r["contract_id"]].append(r)

    summaries = []
    for doc in sampled_docs:
        cid = doc["id"]
        items = by_contract.get(cid, [])
        if not items:
            continue

        cdata = extract_contract_data(doc)
        contract_length = cdata["word_count"]

        per_hyp = []
        assert_count = 0
        withhold_count = 0
        fragility_scores = []
        fragility_types = Counter()

        for r in items:
            per_hyp.append({
                "hypothesis_id": r["hypothesis_id"],
                "verdict": r.get("terminal_state", ""),
                "commitment_level": r.get("commitment_level", ""),
                "fragile": r.get("fragile", False),
            })

            if r.get("withheld"):
                withhold_count += 1
            else:
                assert_count += 1

            fragility_scores.append(r.get("fragility_score", 0.0))
            for rule in r.get("triggered_rules", []):
                fragility_types[rule] += 1

        total = len(items)
        avg_frag = sum(fragility_scores) / total if total > 0 else 0.0
        dominant_type = fragility_types.most_common(1)[0][0] if fragility_types else None

        summaries.append({
            "contract_id": cid,
            "contract_length": contract_length,
            "hypotheses_evaluated": total,
            "per_hypothesis": per_hyp,
            "assert_rate": assert_count / total if total > 0 else 0.0,
            "withhold_rate": withhold_count / total if total > 0 else 0.0,
            "avg_fragility": round(avg_frag, 3),
            "dominant_fragility_type": dominant_type,
            "fragility_type_counts": dict(fragility_types),
        })

    return summaries


# ============================================================
# Metrics Computation (ContractNLI-specific)
# ============================================================

def compute_contractnli_metrics(results, labels):
    """
    Compute all metrics required by Step 021.

    Metrics:
    - CCA (Commitment-Conditioned Accuracy)
    - Abstention rate
    - Abstention value
    - False assertion rate
    - Per-hypothesis CCA and abstention rate
    - Fragility type distribution
    - Majority vote baseline
    """
    total = len(results)
    if total == 0:
        return {"error": "No results"}

    asserted = [r for r in results if not r.get("withheld")]
    withheld = [r for r in results if r.get("withheld")]

    correct_asserted = sum(1 for r in asserted if r.get("gold_match"))
    wrong_asserted = len(asserted) - correct_asserted
    wrong_withheld = sum(1 for r in withheld
                         if r.get("majority_verdict") != r.get("gold_label"))

    cca = correct_asserted / len(asserted) if asserted else 0.0
    abstention_rate = len(withheld) / total
    abstention_value = wrong_withheld / len(withheld) if withheld else 0.0
    false_assertion_rate = wrong_asserted / len(asserted) if asserted else 0.0

    # Per-hypothesis metrics
    by_hyp = defaultdict(list)
    for r in results:
        by_hyp[r["hypothesis_id"]].append(r)

    per_hyp_cca = {}
    per_hyp_abstention = {}
    for hyp_id in sorted(by_hyp.keys(), key=lambda x: int(x.split("-")[1])):
        hyp_results = by_hyp[hyp_id]
        hyp_asserted = [r for r in hyp_results if not r.get("withheld")]
        hyp_withheld = [r for r in hyp_results if r.get("withheld")]
        hyp_correct = sum(1 for r in hyp_asserted if r.get("gold_match"))
        per_hyp_cca[hyp_id] = round(hyp_correct / len(hyp_asserted), 3) if hyp_asserted else None
        per_hyp_abstention[hyp_id] = round(len(hyp_withheld) / len(hyp_results), 3) if hyp_results else 0.0

    # Fragility type distribution
    frag_dist = Counter()
    for r in results:
        for rule in r.get("triggered_rules", []):
            frag_dist[rule] += 1

    # Commitment level distribution
    level_dist = Counter()
    for r in results:
        level_dist[r.get("commitment_level", "unknown")] += 1

    # Terminal state distribution
    state_dist = Counter()
    for r in results:
        state_dist[r.get("terminal_state", "unknown")] += 1

    # Majority vote baseline: what 3 evaluators get without CAM governance
    baseline_correct = 0
    for r in results:
        majority = r.get("majority_verdict")
        gold = r.get("gold_label")
        if majority and majority == gold:
            baseline_correct += 1
    majority_baseline = baseline_correct / total if total > 0 else 0.0

    return {
        "total_evaluations": total,
        "asserted_count": len(asserted),
        "withheld_count": len(withheld),
        "CCA": round(cca, 4),
        "abstention_rate": round(abstention_rate, 4),
        "abstention_value": round(abstention_value, 4),
        "false_assertion_rate": round(false_assertion_rate, 4),
        "per_hypothesis_CCA": per_hyp_cca,
        "per_hypothesis_abstention": per_hyp_abstention,
        "fragility_type_distribution": dict(frag_dist),
        "commitment_level_distribution": dict(level_dist),
        "terminal_state_distribution": dict(state_dist),
        "majority_vote_baseline_accuracy": round(majority_baseline, 4),
    }


# ============================================================
# Post-Run Console Summary
# ============================================================

def _print_post_run_summary(results, metrics, labels):
    """Print the post-run inspection summary to console."""
    log("")
    log("=" * 70)
    log("  POST-RUN SUMMARY")
    log("=" * 70)

    total = metrics["total_evaluations"]
    assert_count = metrics["asserted_count"]
    withhold_count = metrics["withheld_count"]

    log(f"  Total evaluations: {total}")
    log(f"  Asserted: {assert_count}  |  Withheld: {withhold_count}")
    log(f"  CCA (correct / asserted): {metrics['CCA']:.4f}")
    log(f"  Abstention rate: {metrics['abstention_rate']:.4f}")
    log(f"  Abstention value (wrong if not withheld): {metrics['abstention_value']:.4f}")
    log(f"  False assertion rate: {metrics['false_assertion_rate']:.4f}")

    log("")
    log("  Majority vote baseline accuracy: "
        f"{metrics['majority_vote_baseline_accuracy']:.4f}")
    baseline = metrics['majority_vote_baseline_accuracy']
    cca = metrics['CCA']
    if cca > baseline:
        log(f"  CAM CCA vs baseline: +{(cca - baseline):.4f} improvement")
    else:
        log(f"  CAM CCA vs baseline: {(cca - baseline):.4f} (baseline higher)")

    # Top 3 fragility rules
    frag_dist = metrics.get("fragility_type_distribution", {})
    if frag_dist:
        log("")
        log("  Top fragility rules:")
        sorted_rules = sorted(frag_dist.items(), key=lambda x: x[1], reverse=True)
        for rule, count in sorted_rules[:3]:
            log(f"    {rule}: {count} fires")

    # Terminal state distribution
    state_dist = metrics.get("terminal_state_distribution", {})
    if state_dist:
        log("")
        log("  Terminal states:")
        for state, count in sorted(state_dist.items()):
            log(f"    {state}: {count}")

    # Commitment level distribution
    level_dist = metrics.get("commitment_level_distribution", {})
    if level_dist:
        log("")
        log("  Commitment levels:")
        for level, count in sorted(level_dist.items()):
            log(f"    {level}: {count}")

    # Per-hypothesis analysis
    per_hyp_cca = metrics.get("per_hypothesis_CCA", {})
    per_hyp_abs = metrics.get("per_hypothesis_abstention", {})

    # Hypotheses with 0% or 100% abstention
    zero_abs = [h for h, a in per_hyp_abs.items() if a == 0.0]
    full_abs = [h for h, a in per_hyp_abs.items() if a == 1.0]
    if zero_abs:
        log("")
        log(f"  Hypotheses with 0% abstention (always asserted): {', '.join(zero_abs)}")
    if full_abs:
        log(f"  Hypotheses with 100% abstention (always withheld): {', '.join(full_abs)}")

    # Worst-performing hypotheses by CCA
    valid_cca = {h: c for h, c in per_hyp_cca.items() if c is not None}
    if valid_cca:
        worst = sorted(valid_cca.items(), key=lambda x: x[1])[:3]
        log("")
        log("  Worst-performing hypotheses by CCA:")
        for hyp_id, cca_val in worst:
            abs_val = per_hyp_abs.get(hyp_id, 0)
            hyp_text = labels.get(hyp_id, {}).get("short_description", "")
            log(f"    {hyp_id} [{hyp_text}]: CCA={cca_val:.3f}, abstention={abs_val:.3f}")

    log("")
    log("=" * 70)
    log("  RUN COMPLETE")
    log("=" * 70)


# ============================================================
# Rerun Audit with Alternative Provider
# ============================================================

def run_rerun_audit(source_run_label, target_run_label, audit_model="mistral"):
    """
    Re-run ONLY the audit stage with an alternative model provider,
    then recompute fragility and disposition from the new auditor output.
    Everything else (evaluator verdicts, challenge, elimination) stays from source run.

    Args:
        source_run_label: Name of completed source run (e.g., "4 ContractNLI Full")
        target_run_label: Name for new run directory (e.g., "4a ContractNLI Mistral Audit")
        audit_model: "mistral" (default) — uses mistral-large-latest via direct API
    """
    from cam.core.config import find_and_load_env
    from cam.core.json_extract import safe_json_extract
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
    )
    from cam.adapters.contractnli.contractnli_auditor import (
        format_challenge_for_auditor,
        normalize_auditor_response,
        AUDITOR_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_fragility import compute_fragility_profile
    from cam.adapters.contractnli.contractnli_disposition import (
        compute_disposition,
        compare_to_gold,
    )

    find_and_load_env()

    source_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / source_run_label
    target_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / target_run_label

    if not source_dir.exists():
        log(f"ERROR: Source run not found: {source_dir}")
        return

    # Load source results
    source_results_file = source_dir / "results.jsonl"
    source_results = []
    with open(source_results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                source_results.append(json.loads(line))
    log(f"Loaded {len(source_results)} items from {source_results_file}")

    # Load dataset for contract text (needed for audit prompt)
    documents, labels = load_contractnli_dataset(split="dev")
    doc_lookup = {doc["id"]: doc for doc in documents}

    # Load auditor prompt template
    prompt_path = Path(__file__).parent / "prompts" / "auditor.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up Mistral direct API caller (same pattern as SciFact)
    import os
    from openai import OpenAI

    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        log("ERROR: MISTRAL_API_KEY not set")
        return

    mistral_client = OpenAI(
        api_key=mistral_key,
        base_url="https://api.mistral.ai/v1",
        timeout=180.0,
    )
    mistral_model = "mistral-large-latest"

    def call_mistral_json(system_prompt, user_prompt):
        """Call Mistral API directly via OpenAI-compatible endpoint."""
        resp = mistral_client.chat.completions.create(
            model=mistral_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=8192,
        )
        raw_text = (resp.choices[0].message.content or "").strip()
        parsed = safe_json_extract(raw_text)
        meta = {
            "target": {"name": f"mistral:{mistral_model}", "provider": "mistral", "model": mistral_model},
            "usage": {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            },
        }
        return parsed, meta

    # Create target run directory
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = target_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI — RERUN AUDIT")
    log(f"  Source: {source_run_label}")
    log(f"  Target: {target_run_label}")
    log(f"  Auditor: mistral:{mistral_model}")
    log("=" * 70)

    # Track comparison data
    source_audits = []
    target_audits = []
    source_terminals = []
    target_terminals = []
    source_levels = []
    target_levels = []

    new_results = []
    summaries = []
    contract_text_cache = {}

    for idx, src in enumerate(source_results, 1):
        item_id = src["item_id"]
        contract_id = src["contract_id"]
        hypothesis_id = src["hypothesis_id"]
        hypothesis_text = src["hypothesis_text"]
        gold_label = src["gold_label"]

        safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
        log(f"  [{idx}/{len(source_results)}] {item_id}")

        # Load raw evaluator files to reconstruct full evaluations dict
        item_raw_dir_src = source_dir / "raw" / item_id
        evaluations = {}
        for ev_label in ["A", "B", "C"]:
            ev_file = item_raw_dir_src / f"evaluator_{ev_label}.json"
            if ev_file.exists():
                with open(ev_file, "r", encoding="utf-8") as f:
                    ev_data = json.load(f)
                evaluations[ev_label] = ev_data.get("normalized", {})
            else:
                evaluations[ev_label] = {"error": f"Raw file not found: {ev_file}"}

        # Load raw challenge result
        challenge_file = item_raw_dir_src / f"{item_id}_challenge.json"
        if challenge_file.exists():
            with open(challenge_file, "r", encoding="utf-8") as f:
                ch_data = json.load(f)
            challenge_normalized = ch_data.get("normalized", {})
        else:
            challenge_normalized = {"error": "Challenge file not found"}

        # Load raw elimination result
        elim_file = item_raw_dir_src / f"{item_id}_elimination.json"
        if elim_file.exists():
            with open(elim_file, "r", encoding="utf-8") as f:
                el_data = json.load(f)
            elimination_normalized = el_data.get("normalized", {})
        else:
            elimination_normalized = {"error": "Elimination file not found"}

        # Get contract text for audit prompt
        if contract_id not in contract_text_cache:
            doc = doc_lookup.get(contract_id)
            if doc:
                contract_data = extract_contract_data(doc)
                contract_text_cache[contract_id] = format_contract_for_prompt(
                    contract_data["text"], contract_data["spans"]
                )
            else:
                contract_text_cache[contract_id] = "[Contract text unavailable]"
        formatted_contract = contract_text_cache[contract_id]

        # Build audit prompt (same as original pipeline)
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)
        challenge_summary = format_challenge_for_auditor(challenge_normalized)
        audit_prompt = prompt_template.replace("{hypothesis_text}", hypothesis_text)
        audit_prompt = audit_prompt.replace("{formatted_contract}", formatted_contract)
        audit_prompt = audit_prompt.replace("{evaluator_outputs}", evaluator_outputs)
        audit_prompt = audit_prompt.replace("{challenge_summary}", challenge_summary)
        audit_prompt = audit_prompt.replace("{example_json}", AUDITOR_EXAMPLE_JSON)

        # Call Mistral auditor
        audit_normalized = None
        for attempt in range(1, 3):
            try:
                raw_obj, meta = call_mistral_json(
                    system_prompt="You are a structural auditor for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=audit_prompt,
                )
                raw_response = json.dumps(raw_obj)
                audit_normalized = normalize_auditor_response(raw_response, item_id)
                log(f"    audit: recommendation={audit_normalized.get('recommendation', '???')}, "
                    f"validity={audit_normalized.get('structural_validity', '???')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    audit_normalized = {"error": f"Mistral API call failed after 2 attempts: {e}"}

        # Save raw audit
        item_raw_dir_tgt = raw_dir / item_id
        item_raw_dir_tgt.mkdir(parents=True, exist_ok=True)
        with open(item_raw_dir_tgt / f"{item_id}_audit.json", "w", encoding="utf-8") as f:
            json.dump({"normalized": audit_normalized, "meta": meta if audit_normalized and "error" not in audit_normalized else None}, f, indent=2, default=str)

        # Recompute fragility with new auditor output
        fragility_profile = compute_fragility_profile(evaluations, challenge_normalized, audit_normalized)

        # Recompute disposition with new auditor + fragility (elimination unchanged)
        disposition = compute_disposition(
            evaluations, challenge_normalized, audit_normalized,
            fragility_profile, elimination_normalized,
        )
        gold_comp = compare_to_gold(disposition, gold_label)

        terminal = disposition["terminal_state"]
        level = disposition["commitment_level"]
        label = disposition["commitment_label"]
        conviction = disposition.get("conviction_score", 0)
        match_marker = "OK" if gold_comp["gold_match"] else ("WH" if gold_comp["withheld"] else "X")
        log(f"    -> {terminal} ({level}), conviction={conviction:.3f}, gold={gold_label} [{match_marker}]")

        # Track source vs target for comparison
        src_rec = src.get("auditor_assessment", {}).get("recommendation", "???")
        tgt_rec = audit_normalized.get("recommendation", "???") if audit_normalized else "error"
        source_audits.append(src_rec)
        target_audits.append(tgt_rec)
        source_terminals.append(src.get("terminal_state", "???"))
        target_terminals.append(terminal)
        source_levels.append(src.get("commitment_level", "???"))
        target_levels.append(level)

        # Build result record (same schema as original, updated with new audit/fragility/disposition)
        result = {
            "item_id": item_id,
            "contract_id": contract_id,
            "hypothesis_id": hypothesis_id,
            "hypothesis_text": hypothesis_text,
            "evaluator_verdicts": src.get("evaluator_verdicts", {}),
            "cited_spans_per_evaluator": src.get("cited_spans_per_evaluator", {}),
            "agreement_pattern": src.get("agreement_pattern", ""),
            "majority_verdict": src.get("majority_verdict"),
            "challenge_summary": src.get("challenge_summary", {}),
            "auditor_assessment": {
                "structural_validity": audit_normalized.get("structural_validity") if audit_normalized else None,
                "grounding_quality": audit_normalized.get("grounding_quality") if audit_normalized else None,
                "recommendation": audit_normalized.get("recommendation") if audit_normalized else None,
                "span_overlap": audit_normalized.get("span_overlap_assessment") if audit_normalized else None,
            },
            "fragility_score": fragility_profile["fragility_score"],
            "triggered_rules": fragility_profile["fired_rules"],
            "fragile": fragility_profile["fragile"],
            "fragility_cap": fragility_profile["max_cap"],
            "verdict_elimination": src.get("verdict_elimination", {}),
            "terminal_state": terminal,
            "commitment_level": level,
            "commitment_label": label,
            "conviction_score": conviction,
            "downgrade_reasons": disposition.get("downgrade_reasons", []),
            "gold_label": gold_label,
            "gold_match": gold_comp["gold_match"],
            "withheld": gold_comp["withheld"],
            "enrichment_performed": src.get("enrichment_performed", False),
            "enrichment_summary": src.get("enrichment_summary", ""),
            "source_run": source_run_label,
            "audit_provider": f"mistral:{mistral_model}",
        }
        new_results.append(result)

    # Write results.jsonl
    results_file = target_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in new_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\n  Results saved: {results_file} ({len(new_results)} items)")

    # Compute metrics
    total = len(new_results)
    asserted = sum(1 for r in new_results if not r.get("withheld", True))
    correct = sum(1 for r in new_results if r.get("gold_match", False) and not r.get("withheld", True))
    withheld = sum(1 for r in new_results if r.get("withheld", False))
    cca = (correct / asserted * 100) if asserted > 0 else 0.0

    # Source run metrics
    src_asserted = sum(1 for r in source_results if not r.get("withheld", True))
    src_correct = sum(1 for r in source_results if r.get("gold_match", False) and not r.get("withheld", True))
    src_cca = (src_correct / src_asserted * 100) if src_asserted > 0 else 0.0

    # Comparison stats
    # Map recommendations to PASS/FLAG for comparison
    def rec_to_passflag(rec):
        if rec == "proceed":
            return "PASS"
        elif rec in ("flag", "escalate"):
            return "FLAG"
        return "???"

    pp, pf, fp, ff = 0, 0, 0, 0
    for s, t in zip(source_audits, target_audits):
        sp = rec_to_passflag(s)
        tp = rec_to_passflag(t)
        if sp == "PASS" and tp == "PASS":
            pp += 1
        elif sp == "PASS" and tp == "FLAG":
            pf += 1
        elif sp == "FLAG" and tp == "PASS":
            fp += 1
        elif sp == "FLAG" and tp == "FLAG":
            ff += 1

    agreement_rate = ((pp + ff) / total * 100) if total > 0 else 0.0

    terminal_changes = sum(1 for s, t in zip(source_terminals, target_terminals) if s != t)
    level_changes = sum(1 for s, t in zip(source_levels, target_levels) if s != t)

    # Count ASSERT↔WITHHOLD flips
    aw_flips = 0
    for s, t in zip(source_terminals, target_terminals):
        s_is_assert = s.startswith("ASSERT_")
        t_is_assert = t.startswith("ASSERT_")
        if s_is_assert != t_is_assert:
            aw_flips += 1

    # Write audit_comparison.txt
    comparison_lines = []
    comparison_lines.append("=" * 64)
    comparison_lines.append("AUDIT PROVIDER COMPARISON")
    comparison_lines.append(f"Source run: {source_run_label} (Gemini 3.1 Pro)")
    comparison_lines.append(f"Comparison run: {target_run_label} (Mistral Large)")
    comparison_lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    comparison_lines.append("=" * 64)
    comparison_lines.append("")
    comparison_lines.append("AUDIT OUTCOMES:")
    comparison_lines.append(f"  Gemini PASS / Mistral PASS: {pp}")
    comparison_lines.append(f"  Gemini PASS / Mistral FLAG: {pf}")
    comparison_lines.append(f"  Gemini FLAG / Mistral PASS: {fp}")
    comparison_lines.append(f"  Gemini FLAG / Mistral FLAG: {ff}")
    comparison_lines.append(f"  Agreement rate: {agreement_rate:.1f}%")
    comparison_lines.append("")
    comparison_lines.append("DISPOSITION CHANGES:")
    comparison_lines.append(f"  Terminal state changes: {terminal_changes}/{total}")
    comparison_lines.append(f"  Commitment level changes: {level_changes}/{total}")
    comparison_lines.append(f"  Items that changed ASSERT<->WITHHOLD: {aw_flips}")
    comparison_lines.append("")
    comparison_lines.append("METRICS COMPARISON:")
    comparison_lines.append(f"  Run 4 CCA: {src_cca:.1f}% ({src_correct}/{src_asserted} asserted)")
    comparison_lines.append(f"  Run 4a CCA: {cca:.1f}% ({correct}/{asserted} asserted)")
    comparison_lines.append(f"  Delta: {cca - src_cca:+.1f}%")
    comparison_lines.append(f"  Run 4 withheld: {sum(1 for r in source_results if r.get('withheld', False))}")
    comparison_lines.append(f"  Run 4a withheld: {withheld}")
    comparison_lines.append("")

    # Detail: items where terminal state changed
    if terminal_changes > 0:
        comparison_lines.append("=" * 64)
        comparison_lines.append("TERMINAL STATE CHANGES (detail)")
        comparison_lines.append("=" * 64)
        comparison_lines.append("")
        for i, (s, t) in enumerate(zip(source_terminals, target_terminals)):
            if s != t:
                item = new_results[i]
                src_rec = rec_to_passflag(source_audits[i])
                tgt_rec = rec_to_passflag(target_audits[i])
                comparison_lines.append(f"  {item['item_id']}: {s} -> {t}")
                comparison_lines.append(f"    Audit: Gemini {src_rec} -> Mistral {tgt_rec}")
                comparison_lines.append(f"    Level: {source_levels[i]} -> {target_levels[i]}")
                comparison_lines.append(f"    Gold: {item['gold_label']}")
                comparison_lines.append("")

    comparison_text = "\n".join(comparison_lines)
    comparison_file = target_dir / "audit_comparison.txt"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write(comparison_text)

    # Print summary
    log("")
    log(comparison_text)
    log(f"\n  Comparison saved: {comparison_file}")

    # Write run manifest
    manifest = {
        "run_label": target_run_label,
        "source_run": source_run_label,
        "type": "rerun-audit",
        "audit_provider": f"mistral:{mistral_model}",
        "source_audit_provider": "google:gemini-3.1-pro-preview",
        "total_items": total,
        "asserted": asserted,
        "withheld": withheld,
        "cca": round(cca, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(target_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log(f"\n  Run manifest saved: {target_dir / 'run_manifest.json'}")
    log("=" * 70)
    log("  RERUN AUDIT COMPLETE")
    log("=" * 70)


# ============================================================
# Rerun Elimination with Alternative Provider
# ============================================================

def run_rerun_elimination(source_run_label, target_run_label, elim_model="claude"):
    """
    Re-run ONLY the elimination stage (Stage 5) with an alternative model provider,
    then recompute disposition from the new elimination output.
    Everything else (evaluator verdicts, challenge, audit, fragility) stays from source run.

    Args:
        source_run_label: Name of completed source run (e.g., "4 ContractNLI Full")
        target_run_label: Name for new run directory (e.g., "4b ContractNLI Claude Elimination")
        elim_model: "claude" (default) — uses Claude Sonnet 4 via ProviderRouter
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.core.json_extract import safe_json_extract
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
    )
    from cam.adapters.contractnli.contractnli_auditor import (
        format_challenge_for_auditor,
    )
    from cam.adapters.contractnli.contractnli_elimination import (
        format_evaluator_verdicts_brief,
        format_auditor_summary_brief,
        format_fragility_summary_brief,
        normalize_elimination_response,
        ELIMINATION_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_fragility import compute_fragility_profile
    from cam.adapters.contractnli.contractnli_disposition import (
        compute_disposition,
        compare_to_gold,
    )

    find_and_load_env()

    source_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / source_run_label
    target_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / target_run_label

    if not source_dir.exists():
        log(f"ERROR: Source run not found: {source_dir}")
        return

    # Load source results
    source_results_file = source_dir / "results.jsonl"
    source_results = []
    with open(source_results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                source_results.append(json.loads(line))
    log(f"Loaded {len(source_results)} items from {source_results_file}")

    # Load dataset for contract text (needed for elimination prompt)
    documents, labels = load_contractnli_dataset(split="dev")
    doc_lookup = {doc["id"]: doc for doc in documents}

    # Load elimination prompt template
    prompt_path = Path(__file__).parent / "prompts" / "verdict_elimination.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up Claude Sonnet 4 via ProviderRouter
    claude_model = "claude-sonnet-4-20250514"
    target = ModelTarget(
        name=f"anthropic:{claude_model}",
        provider="anthropic",
        model=claude_model,
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=180.0,
    )
    router = ProviderRouter(targets=[target])

    # Create target run directory
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = target_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI — RERUN ELIMINATION")
    log(f"  Source: {source_run_label}")
    log(f"  Target: {target_run_label}")
    log(f"  Eliminator: anthropic:{claude_model}")
    log("=" * 70)

    # Track comparison data
    source_surviving = []
    target_surviving = []
    source_eliminated = []
    target_eliminated = []
    source_terminals = []
    target_terminals = []
    source_levels = []
    target_levels = []
    source_recommended = []
    target_recommended = []

    new_results = []
    contract_text_cache = {}

    for idx, src in enumerate(source_results, 1):
        item_id = src["item_id"]
        contract_id = src["contract_id"]
        hypothesis_id = src["hypothesis_id"]
        hypothesis_text = src["hypothesis_text"]
        gold_label = src["gold_label"]
        agreement = src.get("agreement_pattern", "")

        safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
        log(f"  [{idx}/{len(source_results)}] {item_id}")

        # Load raw evaluator files to reconstruct full evaluations dict
        item_raw_dir_src = source_dir / "raw" / item_id
        evaluations = {}
        for ev_label in ["A", "B", "C"]:
            ev_file = item_raw_dir_src / f"evaluator_{ev_label}.json"
            if ev_file.exists():
                with open(ev_file, "r", encoding="utf-8") as f:
                    ev_data = json.load(f)
                evaluations[ev_label] = ev_data.get("normalized", {})
            else:
                evaluations[ev_label] = {"error": f"Raw file not found: {ev_file}"}

        # Load raw challenge result
        challenge_file = item_raw_dir_src / f"{item_id}_challenge.json"
        if challenge_file.exists():
            with open(challenge_file, "r", encoding="utf-8") as f:
                ch_data = json.load(f)
            challenge_normalized = ch_data.get("normalized", {})
        else:
            challenge_normalized = {"error": "Challenge file not found"}

        # Load raw audit result (from source run = Gemini audit, NOT Run 4a Mistral)
        audit_file = item_raw_dir_src / f"{item_id}_audit.json"
        if audit_file.exists():
            with open(audit_file, "r", encoding="utf-8") as f:
                au_data = json.load(f)
            audit_normalized = au_data.get("normalized", {})
        else:
            audit_normalized = {"error": "Audit file not found"}

        # Get contract text for elimination prompt
        if contract_id not in contract_text_cache:
            doc = doc_lookup.get(contract_id)
            if doc:
                contract_data = extract_contract_data(doc)
                contract_text_cache[contract_id] = format_contract_for_prompt(
                    contract_data["text"], contract_data["spans"]
                )
            else:
                contract_text_cache[contract_id] = "[Contract text unavailable]"
        formatted_contract = contract_text_cache[contract_id]

        # Recompute fragility from source data (unchanged — does not depend on elimination)
        fragility_profile = compute_fragility_profile(evaluations, challenge_normalized, audit_normalized)

        # Format prompt sections (same as Stage 5 pipeline)
        evaluator_verdicts = format_evaluator_verdicts_brief(evaluations)
        challenge_summary = format_challenge_for_auditor(challenge_normalized)
        auditor_summary = format_auditor_summary_brief(audit_normalized)
        fragility_summary = format_fragility_summary_brief(fragility_profile)

        # Fill prompt template
        prompt = prompt_template.replace("{hypothesis_text}", hypothesis_text)
        prompt = prompt.replace("{formatted_contract}", formatted_contract)
        prompt = prompt.replace("{evaluator_verdicts}", evaluator_verdicts)
        prompt = prompt.replace("{challenge_summary}", challenge_summary)
        prompt = prompt.replace("{auditor_summary}", auditor_summary)
        prompt = prompt.replace("{fragility_summary}", fragility_summary)
        prompt = prompt.replace("{example_json}", ELIMINATION_EXAMPLE_JSON)

        # Add agreement pattern and unanimous instruction
        prompt = prompt.replace("{agreement_pattern}", agreement)
        if "3-0" in agreement:
            unanimous_instruction = (
                "All three independent evaluators (using different AI providers) reached the same verdict. "
                "Unanimous agreement from independent models is a strong signal. To kill the unanimous verdict, "
                "you MUST identify a specific fatal flaw from the closed taxonomy above — not merely a concern, "
                "weakness, or technicality. If you cannot identify a clear fatal flaw with a specific span citation, "
                "the unanimous verdict SURVIVES."
            )
        elif "2-1" in agreement:
            unanimous_instruction = (
                "Two evaluators agreed on a majority verdict. The majority verdict carries weight "
                "but is not as strong as unanimity. Apply the standard kill criteria."
            )
        else:
            unanimous_instruction = (
                "No evaluator agreement — full three-way split. All verdicts should be evaluated "
                "equally with no presumption of correctness."
            )
        prompt = prompt.replace("{unanimous_instruction}", unanimous_instruction)

        # Call Claude eliminator
        elimination_normalized = None
        meta = None
        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a verdict stress tester for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                elimination_normalized = normalize_elimination_response(raw_response, item_id)
                surviving = elimination_normalized.get("surviving_verdicts", [])
                eliminated = elimination_normalized.get("eliminated_verdicts", [])
                recommended = elimination_normalized.get("recommended_verdict", "?")
                log(f"    surviving={surviving}, eliminated={eliminated}, "
                    f"recommended={recommended}, schema_valid={elimination_normalized.get('schema_valid')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    elimination_normalized = {"error": f"Claude API call failed after 2 attempts: {e}"}

        # Save raw elimination output
        item_raw_dir_tgt = raw_dir / item_id
        item_raw_dir_tgt.mkdir(parents=True, exist_ok=True)
        with open(item_raw_dir_tgt / f"{item_id}_elimination.json", "w", encoding="utf-8") as f:
            json.dump({
                "normalized": elimination_normalized,
                "meta": meta if elimination_normalized and "error" not in elimination_normalized else None,
            }, f, indent=2, default=str)

        # Recompute disposition with new elimination (audit + fragility unchanged from source)
        disposition = compute_disposition(
            evaluations, challenge_normalized, audit_normalized,
            fragility_profile, elimination_normalized,
        )
        gold_comp = compare_to_gold(disposition, gold_label)

        terminal = disposition["terminal_state"]
        level = disposition["commitment_level"]
        label = disposition["commitment_label"]
        conviction = disposition.get("conviction_score", 0)
        match_marker = "OK" if gold_comp["gold_match"] else ("WH" if gold_comp["withheld"] else "X")
        log(f"    -> {terminal} ({level}), conviction={conviction:.3f}, gold={gold_label} [{match_marker}]")

        # Track source vs target for comparison
        src_surv = src.get("verdict_elimination", {}).get("surviving_verdicts", [])
        tgt_surv = elimination_normalized.get("surviving_verdicts", []) if elimination_normalized else []
        src_elim = src.get("verdict_elimination", {}).get("eliminated_verdicts", [])
        tgt_elim = elimination_normalized.get("eliminated_verdicts", []) if elimination_normalized else []
        src_rec = src.get("verdict_elimination", {}).get("recommended_verdict", "???")
        tgt_rec = elimination_normalized.get("recommended_verdict", "???") if elimination_normalized else "error"

        source_surviving.append(sorted(src_surv))
        target_surviving.append(sorted(tgt_surv))
        source_eliminated.append(sorted(src_elim))
        target_eliminated.append(sorted(tgt_elim))
        source_recommended.append(src_rec)
        target_recommended.append(tgt_rec)
        source_terminals.append(src.get("terminal_state", "???"))
        target_terminals.append(terminal)
        source_levels.append(src.get("commitment_level", "???"))
        target_levels.append(level)

        # Build result record (same schema as original, updated with new elimination/disposition)
        result = {
            "item_id": item_id,
            "contract_id": contract_id,
            "hypothesis_id": hypothesis_id,
            "hypothesis_text": hypothesis_text,
            "evaluator_verdicts": src.get("evaluator_verdicts", {}),
            "cited_spans_per_evaluator": src.get("cited_spans_per_evaluator", {}),
            "agreement_pattern": agreement,
            "majority_verdict": src.get("majority_verdict"),
            "challenge_summary": src.get("challenge_summary", {}),
            "auditor_assessment": src.get("auditor_assessment", {}),
            "fragility_score": fragility_profile["fragility_score"],
            "triggered_rules": fragility_profile["fired_rules"],
            "fragile": fragility_profile["fragile"],
            "fragility_cap": fragility_profile["max_cap"],
            "verdict_elimination": {
                "surviving_verdicts": elimination_normalized.get("surviving_verdicts", []) if elimination_normalized else [],
                "eliminated_verdicts": elimination_normalized.get("eliminated_verdicts", []) if elimination_normalized else [],
                "recommended_verdict": elimination_normalized.get("recommended_verdict") if elimination_normalized else None,
            },
            "terminal_state": terminal,
            "commitment_level": level,
            "commitment_label": label,
            "conviction_score": conviction,
            "downgrade_reasons": disposition.get("downgrade_reasons", []),
            "gold_label": gold_label,
            "gold_match": gold_comp["gold_match"],
            "withheld": gold_comp["withheld"],
            "enrichment_performed": src.get("enrichment_performed", False),
            "enrichment_summary": src.get("enrichment_summary", ""),
            "source_run": source_run_label,
            "elimination_provider": f"anthropic:{claude_model}",
        }
        new_results.append(result)

    # Write results.jsonl
    results_file = target_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in new_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\n  Results saved: {results_file} ({len(new_results)} items)")

    # Compute metrics
    total = len(new_results)
    asserted = sum(1 for r in new_results if not r.get("withheld", True))
    correct = sum(1 for r in new_results if r.get("gold_match", False) and not r.get("withheld", True))
    withheld_count = sum(1 for r in new_results if r.get("withheld", False))
    cca = (correct / asserted * 100) if asserted > 0 else 0.0

    # Source run metrics
    src_asserted = sum(1 for r in source_results if not r.get("withheld", True))
    src_correct = sum(1 for r in source_results if r.get("gold_match", False) and not r.get("withheld", True))
    src_cca = (src_correct / src_asserted * 100) if src_asserted > 0 else 0.0
    src_withheld = sum(1 for r in source_results if r.get("withheld", False))
    src_errors = src_asserted - src_correct

    # Comparison stats
    identical_surviving = sum(1 for s, t in zip(source_surviving, target_surviving) if s == t)
    different_surviving = total - identical_surviving

    # Count total kills per provider
    src_total_kills = sum(len(e) for e in source_eliminated)
    tgt_total_kills = sum(len(e) for e in target_eliminated)

    # Items where one provider killed more
    src_killed_more = sum(1 for s, t in zip(source_eliminated, target_eliminated) if len(s) > len(t))
    tgt_killed_more = sum(1 for s, t in zip(source_eliminated, target_eliminated) if len(t) > len(s))

    surviving_agreement_rate = (identical_surviving / total * 100) if total > 0 else 0.0

    terminal_changes = sum(1 for s, t in zip(source_terminals, target_terminals) if s != t)
    level_changes = sum(1 for s, t in zip(source_levels, target_levels) if s != t)

    # Count ASSERT<->WITHHOLD flips
    aw_flips = 0
    for s, t in zip(source_terminals, target_terminals):
        s_is_assert = s.startswith("ASSERT_")
        t_is_assert = t.startswith("ASSERT_")
        if s_is_assert != t_is_assert:
            aw_flips += 1

    # Count verdict changes (terminal state changes to a different verdict, not just assert/withhold)
    verdict_changes = 0
    for s, t in zip(source_terminals, target_terminals):
        # Extract verdict from terminal state (e.g., ASSERT_ENTAILMENT -> ENTAILMENT)
        s_verdict = s.replace("ASSERT_", "").replace("WITHHOLD_", "").replace("WITHHOLD_ASSERTION", "")
        t_verdict = t.replace("ASSERT_", "").replace("WITHHOLD_", "").replace("WITHHOLD_ASSERTION", "")
        if s_verdict != t_verdict and s_verdict and t_verdict:
            verdict_changes += 1

    # Error analysis
    tgt_errors = asserted - correct
    # Identify which items are errors in each run
    src_error_items = set()
    tgt_error_items = set()
    for i, (sr, tr) in enumerate(zip(source_results, new_results)):
        sr_is_error = not sr.get("withheld", True) and not sr.get("gold_match", False)
        tr_is_error = not tr.get("withheld", True) and not tr.get("gold_match", False)
        if sr_is_error:
            src_error_items.add(i)
        if tr_is_error:
            tgt_error_items.add(i)

    shared_errors = len(src_error_items & tgt_error_items)
    src_only_errors = len(src_error_items - tgt_error_items)
    tgt_only_errors = len(tgt_error_items - src_error_items)

    # Write elimination_comparison.txt
    comparison_lines = []
    comparison_lines.append("=" * 64)
    comparison_lines.append("ELIMINATION PROVIDER COMPARISON")
    comparison_lines.append(f"Source run: {source_run_label} (Gemini 3.1 Pro)")
    comparison_lines.append(f"Comparison run: {target_run_label} (Claude Sonnet 4)")
    comparison_lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    comparison_lines.append("=" * 64)
    comparison_lines.append("")
    comparison_lines.append("ELIMINATION OUTCOMES:")
    comparison_lines.append(f"  Items with identical surviving verdicts: {identical_surviving}/{total}")
    comparison_lines.append(f"  Items with different surviving verdicts: {different_surviving}/{total}")
    comparison_lines.append(f"  Agreement rate: {surviving_agreement_rate:.1f}%")
    comparison_lines.append("")
    comparison_lines.append(f"  Gemini kills / Claude kills: {src_total_kills} / {tgt_total_kills} (total kill actions)")
    comparison_lines.append(f"  Items where Gemini killed more verdicts: {src_killed_more}")
    comparison_lines.append(f"  Items where Claude killed more verdicts: {tgt_killed_more}")
    comparison_lines.append("")
    comparison_lines.append("DISPOSITION CHANGES:")
    comparison_lines.append(f"  Terminal state changes: {terminal_changes}/{total}")
    comparison_lines.append(f"  Commitment level changes: {level_changes}/{total}")
    comparison_lines.append(f"  Items that changed ASSERT<->WITHHOLD: {aw_flips}")
    comparison_lines.append(f"  Items that changed to a DIFFERENT verdict: {verdict_changes}")
    comparison_lines.append("")
    comparison_lines.append("METRICS COMPARISON:")
    comparison_lines.append(f"  Run 4 CCA: {src_cca:.1f}% ({src_correct}/{src_asserted})")
    comparison_lines.append(f"  Run 4b CCA: {cca:.1f}% ({correct}/{asserted})")
    comparison_lines.append(f"  Delta: {cca - src_cca:+.1f}%")
    comparison_lines.append(f"  Run 4 withheld: {src_withheld}")
    comparison_lines.append(f"  Run 4b withheld: {withheld_count}")
    comparison_lines.append("")
    comparison_lines.append("ERROR ANALYSIS:")
    comparison_lines.append(f"  Run 4 errors (vs gold): {src_errors}")
    comparison_lines.append(f"  Run 4b errors (vs gold): {tgt_errors}")
    comparison_lines.append(f"  Shared errors: {shared_errors}")
    comparison_lines.append(f"  Run 4 only errors: {src_only_errors}")
    comparison_lines.append(f"  Run 4b only errors: {tgt_only_errors}")
    comparison_lines.append("")

    # Detail: items where terminal state changed
    if terminal_changes > 0:
        comparison_lines.append("=" * 64)
        comparison_lines.append("TERMINAL STATE CHANGES (detail)")
        comparison_lines.append("=" * 64)
        comparison_lines.append("")
        for i, (s, t) in enumerate(zip(source_terminals, target_terminals)):
            if s != t:
                item = new_results[i]
                s_surv = source_surviving[i]
                t_surv = target_surviving[i]
                comparison_lines.append(f"  {item['item_id']}: {s} -> {t}")
                comparison_lines.append(f"    Surviving: Gemini {s_surv} -> Claude {t_surv}")
                comparison_lines.append(f"    Recommended: {source_recommended[i]} -> {target_recommended[i]}")
                comparison_lines.append(f"    Level: {source_levels[i]} -> {target_levels[i]}")
                comparison_lines.append(f"    Gold: {item['gold_label']}")
                comparison_lines.append("")

    comparison_text = "\n".join(comparison_lines)
    comparison_file = target_dir / "elimination_comparison.txt"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write(comparison_text)

    # Print summary
    log("")
    log(comparison_text)
    log(f"\n  Comparison saved: {comparison_file}")

    # Write run manifest
    manifest = {
        "run_label": target_run_label,
        "source_run": source_run_label,
        "type": "rerun-elimination",
        "elimination_provider": f"anthropic:{claude_model}",
        "source_elimination_provider": "google:gemini-3.1-pro-preview",
        "total_items": total,
        "asserted": asserted,
        "withheld": withheld_count,
        "cca": round(cca, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(target_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log(f"\n  Run manifest saved: {target_dir / 'run_manifest.json'}")
    log("=" * 70)
    log("  RERUN ELIMINATION COMPLETE")
    log("=" * 70)


# ============================================================
# Recompute Disposition from Combined Governance Swaps
# ============================================================

def run_recompute_disposition(audit_run_label, elim_run_label, baseline_run_label, target_run_label):
    """
    Recompute disposition by combining audit from one run and elimination from another.
    Zero API calls — pure local recomputation.

    Args:
        audit_run_label: Run with alternative auditor (e.g., "4a ContractNLI Mistral Audit")
        elim_run_label: Run with alternative eliminator (e.g., "4b ContractNLI Claude Elimination")
        baseline_run_label: Original baseline run (e.g., "4 ContractNLI Full")
        target_run_label: Output run directory (e.g., "4c ContractNLI Combined Governance")
    """
    from cam.adapters.contractnli.contractnli_fragility import compute_fragility_profile
    from cam.adapters.contractnli.contractnli_disposition import (
        compute_disposition,
        compare_to_gold,
    )

    runs_root = CAM_ROOT / "04 ContractNLI" / "Runs"
    audit_dir = runs_root / audit_run_label
    elim_dir = runs_root / elim_run_label
    baseline_dir = runs_root / baseline_run_label
    target_dir = runs_root / target_run_label

    for d, label in [(audit_dir, "Audit run"), (elim_dir, "Elimination run"), (baseline_dir, "Baseline run")]:
        if not d.exists():
            log(f"ERROR: {label} not found: {d}")
            return

    # Load all three results files
    def load_results(path):
        results = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
        return results

    baseline_results = load_results(baseline_dir / "results.jsonl")
    audit_results = load_results(audit_dir / "results.jsonl")
    elim_results = load_results(elim_dir / "results.jsonl")

    log(f"Loaded baseline: {len(baseline_results)} items from {baseline_run_label}")
    log(f"Loaded audit run: {len(audit_results)} items from {audit_run_label}")
    log(f"Loaded elim run: {len(elim_results)} items from {elim_run_label}")

    # Index by item_id for lookup
    audit_by_id = {r["item_id"]: r for r in audit_results}
    elim_by_id = {r["item_id"]: r for r in elim_results}

    target_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = target_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI — RECOMPUTE DISPOSITION (Combined Governance)")
    log(f"  Baseline: {baseline_run_label}")
    log(f"  Audit from: {audit_run_label}")
    log(f"  Elimination from: {elim_run_label}")
    log(f"  Target: {target_run_label}")
    log("=" * 70)

    new_results = []
    baseline_terminals = []
    target_terminals = []
    baseline_levels = []
    target_levels = []

    for idx, base in enumerate(baseline_results, 1):
        item_id = base["item_id"]
        gold_label = base["gold_label"]

        audit_item = audit_by_id.get(item_id)
        elim_item = elim_by_id.get(item_id)

        if not audit_item or not elim_item:
            log(f"  [{idx}/{len(baseline_results)}] {item_id} — SKIP (missing in audit or elim run)")
            continue

        # Load raw evaluator files from baseline for full evaluations dict
        item_raw_dir = baseline_dir / "raw" / item_id
        evaluations = {}
        for ev_label in ["A", "B", "C"]:
            ev_file = item_raw_dir / f"evaluator_{ev_label}.json"
            if ev_file.exists():
                with open(ev_file, "r", encoding="utf-8") as f:
                    ev_data = json.load(f)
                evaluations[ev_label] = ev_data.get("normalized", {})
            else:
                evaluations[ev_label] = {"error": f"Raw file not found: {ev_file}"}

        # Load raw challenge from baseline
        challenge_file = item_raw_dir / f"{item_id}_challenge.json"
        if challenge_file.exists():
            with open(challenge_file, "r", encoding="utf-8") as f:
                ch_data = json.load(f)
            challenge_normalized = ch_data.get("normalized", {})
        else:
            challenge_normalized = {"error": "Challenge file not found"}

        # Load raw audit from AUDIT RUN (4a = Mistral)
        audit_raw_dir = audit_dir / "raw" / item_id
        audit_file = audit_raw_dir / f"{item_id}_audit.json"
        if audit_file.exists():
            with open(audit_file, "r", encoding="utf-8") as f:
                au_data = json.load(f)
            audit_normalized = au_data.get("normalized", {})
        else:
            audit_normalized = {"error": "Audit file not found"}

        # Load raw elimination from ELIM RUN (4b = Claude)
        elim_raw_dir = elim_dir / "raw" / item_id
        elim_file = elim_raw_dir / f"{item_id}_elimination.json"
        if elim_file.exists():
            with open(elim_file, "r", encoding="utf-8") as f:
                el_data = json.load(f)
            elimination_normalized = el_data.get("normalized", {})
        else:
            elimination_normalized = {"error": "Elimination file not found"}

        # Recompute fragility from Mistral audit + baseline evaluations/challenge
        fragility_profile = compute_fragility_profile(evaluations, challenge_normalized, audit_normalized)

        # Recompute disposition with Mistral audit + Claude elimination
        disposition = compute_disposition(
            evaluations, challenge_normalized, audit_normalized,
            fragility_profile, elimination_normalized,
        )
        gold_comp = compare_to_gold(disposition, gold_label)

        terminal = disposition["terminal_state"]
        level = disposition["commitment_level"]
        label = disposition["commitment_label"]
        conviction = disposition.get("conviction_score", 0)
        match_marker = "OK" if gold_comp["gold_match"] else ("WH" if gold_comp["withheld"] else "X")
        log(f"  [{idx}/{len(baseline_results)}] {item_id} -> {terminal} ({level}), "
            f"conviction={conviction:.3f}, gold={gold_label} [{match_marker}]")

        baseline_terminals.append(base.get("terminal_state", "???"))
        target_terminals.append(terminal)
        baseline_levels.append(base.get("commitment_level", "???"))
        target_levels.append(level)

        result = {
            "item_id": item_id,
            "contract_id": base["contract_id"],
            "hypothesis_id": base["hypothesis_id"],
            "hypothesis_text": base["hypothesis_text"],
            "evaluator_verdicts": base.get("evaluator_verdicts", {}),
            "cited_spans_per_evaluator": base.get("cited_spans_per_evaluator", {}),
            "agreement_pattern": base.get("agreement_pattern", ""),
            "majority_verdict": base.get("majority_verdict"),
            "challenge_summary": base.get("challenge_summary", {}),
            "auditor_assessment": audit_item.get("auditor_assessment", {}),
            "fragility_score": fragility_profile["fragility_score"],
            "triggered_rules": fragility_profile["fired_rules"],
            "fragile": fragility_profile["fragile"],
            "fragility_cap": fragility_profile["max_cap"],
            "verdict_elimination": {
                "surviving_verdicts": elimination_normalized.get("surviving_verdicts", []) if elimination_normalized else [],
                "eliminated_verdicts": elimination_normalized.get("eliminated_verdicts", []) if elimination_normalized else [],
                "recommended_verdict": elimination_normalized.get("recommended_verdict") if elimination_normalized else None,
            },
            "terminal_state": terminal,
            "commitment_level": level,
            "commitment_label": label,
            "conviction_score": conviction,
            "downgrade_reasons": disposition.get("downgrade_reasons", []),
            "gold_label": gold_label,
            "gold_match": gold_comp["gold_match"],
            "withheld": gold_comp["withheld"],
            "enrichment_performed": base.get("enrichment_performed", False),
            "enrichment_summary": base.get("enrichment_summary", ""),
            "source_runs": {
                "baseline": baseline_run_label,
                "audit": audit_run_label,
                "elimination": elim_run_label,
            },
            "audit_provider": audit_item.get("audit_provider", "mistral:mistral-large-latest"),
            "elimination_provider": elim_item.get("elimination_provider", "anthropic:claude-sonnet-4-20250514"),
        }
        new_results.append(result)

    # Write results.jsonl
    results_file = target_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in new_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\n  Results saved: {results_file} ({len(new_results)} items)")

    # Compute metrics for all 4 runs
    def run_metrics(results):
        total = len(results)
        asserted = sum(1 for r in results if not r.get("withheld", True))
        correct = sum(1 for r in results if r.get("gold_match", False) and not r.get("withheld", True))
        withheld = sum(1 for r in results if r.get("withheld", False))
        errors = asserted - correct
        cca = (correct / asserted * 100) if asserted > 0 else 0.0
        return {"total": total, "asserted": asserted, "correct": correct, "withheld": withheld, "errors": errors, "cca": cca}

    m_base = run_metrics(baseline_results)
    m_4a = run_metrics(audit_results)
    m_4b = run_metrics(elim_results)
    m_4c = run_metrics(new_results)

    # Terminal state changes vs baseline for each run
    def count_terminal_changes(source_results, target_results):
        changes = 0
        for s, t in zip(source_results, target_results):
            if s.get("terminal_state") != t.get("terminal_state"):
                changes += 1
        return changes

    tc_4a = count_terminal_changes(baseline_results, audit_results)
    tc_4b = count_terminal_changes(baseline_results, elim_results)
    tc_4c = count_terminal_changes(baseline_results, new_results)

    # ASSERT<->WITHHOLD flips vs baseline for 4c
    aw_flips_4c = 0
    for base, new in zip(baseline_results, new_results):
        s = base.get("terminal_state", "")
        t = new.get("terminal_state", "")
        s_assert = s.startswith("ASSERT_")
        t_assert = t.startswith("ASSERT_")
        if s_assert != t_assert:
            aw_flips_4c += 1

    # Error overlap analysis: which errors are shared across all 4 runs
    def error_set(results):
        return {r["item_id"] for r in results if not r.get("withheld", True) and not r.get("gold_match", False)}

    err_base = error_set(baseline_results)
    err_4a = error_set(audit_results)
    err_4b = error_set(elim_results)
    err_4c = error_set(new_results)
    shared_all = err_base & err_4a & err_4b & err_4c

    # Build comparison output
    lines = []
    lines.append("=" * 70)
    lines.append("COMBINED GOVERNANCE COMPARISON")
    lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Run 4:  Gemini audit + Gemini elimination (baseline)")
    lines.append("Run 4a: Mistral audit + Gemini elimination")
    lines.append("Run 4b: Gemini audit + Claude elimination")
    lines.append("Run 4c: Mistral audit + Claude elimination (both swapped)")
    lines.append("")
    lines.append(f"{'':20s} {'Run 4':>10s} {'Run 4a':>10s} {'Run 4b':>10s} {'Run 4c':>10s}")
    lines.append("-" * 62)
    lines.append(f"{'Asserted':20s} {m_base['asserted']:>10d} {m_4a['asserted']:>10d} {m_4b['asserted']:>10d} {m_4c['asserted']:>10d}")
    lines.append(f"{'Withheld':20s} {m_base['withheld']:>10d} {m_4a['withheld']:>10d} {m_4b['withheld']:>10d} {m_4c['withheld']:>10d}")
    lines.append(f"{'Correct (asserted)':20s} {m_base['correct']:>10d} {m_4a['correct']:>10d} {m_4b['correct']:>10d} {m_4c['correct']:>10d}")
    lines.append(f"{'CCA':20s} {m_base['cca']:>9.1f}% {m_4a['cca']:>9.1f}% {m_4b['cca']:>9.1f}% {m_4c['cca']:>9.1f}%")
    lines.append(f"{'Errors (vs gold)':20s} {m_base['errors']:>10d} {m_4a['errors']:>10d} {m_4b['errors']:>10d} {m_4c['errors']:>10d}")
    lines.append("")
    lines.append(f"{'Terminal changes':20s} {'—':>10s} {tc_4a:>10d} {tc_4b:>10d} {tc_4c:>10d}")
    lines.append(f"  (vs Run 4 baseline)")
    lines.append("")
    lines.append("ERROR OVERLAP:")
    lines.append(f"  Errors shared by ALL 4 runs: {len(shared_all)}")
    lines.append(f"  Run 4 only errors: {len(err_base - err_4a - err_4b - err_4c)}")
    lines.append(f"  Run 4c only errors: {len(err_4c - err_base - err_4a - err_4b)}")
    lines.append("")

    # Detail: Run 4c terminal state changes vs baseline
    lines.append("=" * 70)
    lines.append("RUN 4c TERMINAL STATE CHANGES vs BASELINE")
    lines.append("=" * 70)
    lines.append("")
    for base, new in zip(baseline_results, new_results):
        s = base.get("terminal_state", "???")
        t = new.get("terminal_state", "???")
        if s != t:
            lines.append(f"  {new['item_id']}: {s} -> {t}")
            lines.append(f"    Gold: {new['gold_label']}")
            s_match = "OK" if base.get("gold_match") and not base.get("withheld") else ("WH" if base.get("withheld") else "X")
            t_match = "OK" if new.get("gold_match") and not new.get("withheld") else ("WH" if new.get("withheld") else "X")
            lines.append(f"    Baseline: [{s_match}]  Combined: [{t_match}]")
            lines.append("")

    if tc_4c == 0:
        lines.append("  (none)")
        lines.append("")

    comparison_text = "\n".join(lines)
    comparison_file = target_dir / "governance_comparison.txt"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write(comparison_text)

    log("")
    log(comparison_text)
    log(f"\n  Comparison saved: {comparison_file}")

    # Write run manifest
    manifest = {
        "run_label": target_run_label,
        "type": "recompute-disposition",
        "source_runs": {
            "baseline": baseline_run_label,
            "audit": audit_run_label,
            "elimination": elim_run_label,
        },
        "audit_provider": "mistral:mistral-large-latest",
        "elimination_provider": "anthropic:claude-sonnet-4-20250514",
        "total_items": len(new_results),
        "asserted": m_4c["asserted"],
        "withheld": m_4c["withheld"],
        "cca": round(m_4c["cca"], 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(target_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log(f"\n  Run manifest saved: {target_dir / 'run_manifest.json'}")
    log("=" * 70)
    log("  RECOMPUTE DISPOSITION COMPLETE")
    log("=" * 70)


# ============================================================
# Diversified Governance: Re-run Stages 2, 3, 5 with Alternative Providers
# ============================================================

def run_diversified_governance(source_run_label, target_run_label,
                                challenge_model="grok", audit_model="mistral",
                                elim_model="claude"):
    """
    Full diversified governance run: re-run challenge (Stage 2), audit (Stage 3),
    and elimination (Stage 5) with alternative providers. Recompute fragility (Stage 4)
    and disposition (Stage 6) from new outputs.

    Evaluator verdicts (Stage 1) and enrichment (Stage 0) are kept from the source run.

    Args:
        source_run_label: Name of completed source run (e.g., "4 ContractNLI Full")
        target_run_label: Name for new run directory (e.g., "4d ContractNLI Diversified Governance")
        challenge_model: "grok" (default) — uses Grok via ProviderRouter
        audit_model: "mistral" (default) — uses Mistral Large via direct API
        elim_model: "claude" (default) — uses Claude Sonnet 4 via ProviderRouter
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.core.json_extract import safe_json_extract
    from cam.adapters.contractnli.contractnli_challenge import (
        format_evaluator_outputs_for_challenge,
        normalize_challenge_response,
        CHALLENGER_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_auditor import (
        format_challenge_for_auditor,
        normalize_auditor_response,
        AUDITOR_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_elimination import (
        format_evaluator_verdicts_brief,
        format_auditor_summary_brief,
        format_fragility_summary_brief,
        normalize_elimination_response,
        ELIMINATION_EXAMPLE_JSON,
    )
    from cam.adapters.contractnli.contractnli_fragility import compute_fragility_profile
    from cam.adapters.contractnli.contractnli_disposition import (
        compute_disposition,
        compare_to_gold,
    )

    find_and_load_env()

    source_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / source_run_label
    target_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / target_run_label

    if not source_dir.exists():
        log(f"ERROR: Source run not found: {source_dir}")
        return

    # Load source results
    source_results_file = source_dir / "results.jsonl"
    source_results = []
    with open(source_results_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                source_results.append(json.loads(line))
    log(f"Loaded {len(source_results)} items from {source_results_file}")

    # Load dataset for contract text
    documents, labels = load_contractnli_dataset(split="dev")
    doc_lookup = {doc["id"]: doc for doc in documents}

    # Load prompt templates
    challenge_prompt_path = Path(__file__).parent / "prompts" / "evidence_challenge.txt"
    challenge_prompt_template = challenge_prompt_path.read_text(encoding="utf-8")

    audit_prompt_path = Path(__file__).parent / "prompts" / "auditor.txt"
    audit_prompt_template = audit_prompt_path.read_text(encoding="utf-8")

    elim_prompt_path = Path(__file__).parent / "prompts" / "verdict_elimination.txt"
    elim_prompt_template = elim_prompt_path.read_text(encoding="utf-8")

    # ---- Set up Grok challenger via ProviderRouter ----
    grok_model = "grok-4-1-fast-reasoning"
    challenger_target = ModelTarget(
        name=f"xai:{grok_model}",
        provider="xai",
        model=grok_model,
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=180.0,
    )
    challenger_router = ProviderRouter(targets=[challenger_target])

    # ---- Set up Mistral auditor via direct API (same pattern as rerun_audit) ----
    import os
    from openai import OpenAI

    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        log("ERROR: MISTRAL_API_KEY not set")
        return

    mistral_client = OpenAI(
        api_key=mistral_key,
        base_url="https://api.mistral.ai/v1",
        timeout=180.0,
    )
    mistral_model = "mistral-large-latest"

    def call_mistral_json(system_prompt, user_prompt):
        """Call Mistral API directly via OpenAI-compatible endpoint."""
        resp = mistral_client.chat.completions.create(
            model=mistral_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=8192,
        )
        raw_text = (resp.choices[0].message.content or "").strip()
        parsed = safe_json_extract(raw_text)
        meta = {
            "target": {"name": f"mistral:{mistral_model}", "provider": "mistral", "model": mistral_model},
            "usage": {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            },
        }
        return parsed, meta

    # ---- Set up Claude eliminator via ProviderRouter ----
    claude_model = "claude-sonnet-4-20250514"
    elim_target = ModelTarget(
        name=f"anthropic:{claude_model}",
        provider="anthropic",
        model=claude_model,
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=180.0,
    )
    elim_router = ProviderRouter(targets=[elim_target])

    # Create target run directory
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = target_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM ContractNLI — DIVERSIFIED GOVERNANCE RUN")
    log(f"  Source: {source_run_label}")
    log(f"  Target: {target_run_label}")
    log(f"  Challenger: xai:{grok_model}")
    log(f"  Auditor: mistral:{mistral_model}")
    log(f"  Eliminator: anthropic:{claude_model}")
    log("=" * 70)

    # Track comparison data
    source_terminals = []
    target_terminals = []
    source_levels = []
    target_levels = []

    new_results = []
    contract_text_cache = {}

    stage_errors = {"challenge": 0, "audit": 0, "elimination": 0}

    for idx, src in enumerate(source_results, 1):
        item_id = src["item_id"]
        contract_id = src["contract_id"]
        hypothesis_id = src["hypothesis_id"]
        hypothesis_text = src["hypothesis_text"]
        gold_label = src["gold_label"]
        agreement = src.get("agreement_pattern", "")

        safe_hyp = hypothesis_text[:80].encode("ascii", errors="replace").decode("ascii")
        log(f"\n  [{idx}/{len(source_results)}] {item_id}")
        log(f"    hypothesis: {safe_hyp}")

        # Load raw evaluator files from source for full evaluations dict
        item_raw_dir_src = source_dir / "raw" / item_id
        evaluations = {}
        for ev_label in ["A", "B", "C"]:
            ev_file = item_raw_dir_src / f"evaluator_{ev_label}.json"
            if ev_file.exists():
                with open(ev_file, "r", encoding="utf-8") as f:
                    ev_data = json.load(f)
                evaluations[ev_label] = ev_data.get("normalized", {})
            else:
                evaluations[ev_label] = {"error": f"Raw file not found: {ev_file}"}

        # Get contract text (cached)
        if contract_id not in contract_text_cache:
            doc = doc_lookup.get(contract_id)
            if doc:
                contract_data = extract_contract_data(doc)
                contract_text_cache[contract_id] = format_contract_for_prompt(
                    contract_data["text"], contract_data["spans"]
                )
            else:
                contract_text_cache[contract_id] = "[Contract text unavailable]"
        formatted_contract = contract_text_cache[contract_id]

        # Create item raw dir
        item_raw_dir_tgt = raw_dir / item_id
        item_raw_dir_tgt.mkdir(parents=True, exist_ok=True)

        # ================================================================
        # STAGE 2: Challenge with Grok
        # ================================================================
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)
        challenge_prompt = challenge_prompt_template.replace("{hypothesis_text}", hypothesis_text)
        challenge_prompt = challenge_prompt.replace("{formatted_contract}", formatted_contract)
        challenge_prompt = challenge_prompt.replace("{evaluator_outputs}", evaluator_outputs)
        challenge_prompt = challenge_prompt.replace("{example_json}", CHALLENGER_EXAMPLE_JSON)

        challenge_normalized = None
        challenge_meta = None
        for attempt in range(1, 3):
            try:
                raw_obj, challenge_meta = challenger_router.call_json(
                    system_prompt="You are a grounding auditor for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=challenge_prompt,
                )
                raw_response = json.dumps(raw_obj)
                challenge_normalized = normalize_challenge_response(raw_response, item_id)
                log(f"    [CHALLENGE] assessment={challenge_normalized.get('overall_grounding_assessment', '???')}, "
                    f"challenges={len(challenge_normalized.get('challenges', []))}")
                break
            except Exception as e:
                log(f"    [CHALLENGE] Attempt {attempt} failed: {e}")
                if attempt == 2:
                    challenge_normalized = {"error": f"Grok challenge failed after 2 attempts: {e}"}
                    stage_errors["challenge"] += 1

        # Save raw challenge
        with open(item_raw_dir_tgt / f"{item_id}_challenge.json", "w", encoding="utf-8") as f:
            json.dump({
                "item_id": item_id,
                "challenger": {"name": f"xai:{grok_model}", "provider": "xai", "model": grok_model},
                "normalized": challenge_normalized,
                "meta": challenge_meta,
            }, f, indent=2, default=str)

        # ================================================================
        # STAGE 3: Audit with Mistral
        # ================================================================
        challenge_summary_for_audit = format_challenge_for_auditor(challenge_normalized)
        audit_prompt = audit_prompt_template.replace("{hypothesis_text}", hypothesis_text)
        audit_prompt = audit_prompt.replace("{formatted_contract}", formatted_contract)
        audit_prompt = audit_prompt.replace("{evaluator_outputs}", evaluator_outputs)
        audit_prompt = audit_prompt.replace("{challenge_summary}", challenge_summary_for_audit)
        audit_prompt = audit_prompt.replace("{example_json}", AUDITOR_EXAMPLE_JSON)

        audit_normalized = None
        audit_meta = None
        for attempt in range(1, 3):
            try:
                raw_obj, audit_meta = call_mistral_json(
                    system_prompt="You are a structural auditor for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=audit_prompt,
                )
                raw_response = json.dumps(raw_obj)
                audit_normalized = normalize_auditor_response(raw_response, item_id)
                log(f"    [AUDIT] recommendation={audit_normalized.get('recommendation', '???')}, "
                    f"validity={audit_normalized.get('structural_validity', '???')}")
                break
            except Exception as e:
                log(f"    [AUDIT] Attempt {attempt} failed: {e}")
                if attempt == 2:
                    audit_normalized = {"error": f"Mistral audit failed after 2 attempts: {e}"}
                    stage_errors["audit"] += 1

        # Save raw audit
        with open(item_raw_dir_tgt / f"{item_id}_audit.json", "w", encoding="utf-8") as f:
            json.dump({
                "normalized": audit_normalized,
                "meta": audit_meta if audit_normalized and "error" not in audit_normalized else None,
            }, f, indent=2, default=str)

        # ================================================================
        # STAGE 4: Fragility (recompute — no LLM call)
        # ================================================================
        fragility_profile = compute_fragility_profile(evaluations, challenge_normalized, audit_normalized)

        # ================================================================
        # STAGE 5: Elimination with Claude
        # ================================================================
        evaluator_verdicts = format_evaluator_verdicts_brief(evaluations)
        auditor_summary = format_auditor_summary_brief(audit_normalized)
        fragility_summary = format_fragility_summary_brief(fragility_profile)

        elim_prompt = elim_prompt_template.replace("{hypothesis_text}", hypothesis_text)
        elim_prompt = elim_prompt.replace("{formatted_contract}", formatted_contract)
        elim_prompt = elim_prompt.replace("{evaluator_verdicts}", evaluator_verdicts)
        elim_prompt = elim_prompt.replace("{challenge_summary}", challenge_summary_for_audit)
        elim_prompt = elim_prompt.replace("{auditor_summary}", auditor_summary)
        elim_prompt = elim_prompt.replace("{fragility_summary}", fragility_summary)
        elim_prompt = elim_prompt.replace("{example_json}", ELIMINATION_EXAMPLE_JSON)

        # Add agreement pattern and unanimous instruction
        elim_prompt = elim_prompt.replace("{agreement_pattern}", agreement)
        if "3-0" in agreement:
            unanimous_instruction = (
                "All three independent evaluators (using different AI providers) reached the same verdict. "
                "Unanimous agreement from independent models is a strong signal. To kill the unanimous verdict, "
                "you MUST identify a specific fatal flaw from the closed taxonomy above — not merely a concern, "
                "weakness, or technicality. If you cannot identify a clear fatal flaw with a specific span citation, "
                "the unanimous verdict SURVIVES."
            )
        elif "2-1" in agreement:
            unanimous_instruction = (
                "Two evaluators agreed on a majority verdict. The majority verdict carries weight "
                "but is not as strong as unanimity. Apply the standard kill criteria."
            )
        else:
            unanimous_instruction = (
                "No evaluator agreement — full three-way split. All verdicts should be evaluated "
                "equally with no presumption of correctness."
            )
        elim_prompt = elim_prompt.replace("{unanimous_instruction}", unanimous_instruction)

        elimination_normalized = None
        elim_meta = None
        for attempt in range(1, 3):
            try:
                raw_obj, elim_meta = elim_router.call_json(
                    system_prompt="You are a verdict stress tester for legal contract entailment. Respond only with valid JSON.",
                    user_prompt=elim_prompt,
                )
                raw_response = json.dumps(raw_obj)
                elimination_normalized = normalize_elimination_response(raw_response, item_id)
                surviving = elimination_normalized.get("surviving_verdicts", [])
                eliminated = elimination_normalized.get("eliminated_verdicts", [])
                recommended = elimination_normalized.get("recommended_verdict", "?")
                log(f"    [ELIM] surviving={surviving}, eliminated={eliminated}, recommended={recommended}")
                break
            except Exception as e:
                log(f"    [ELIM] Attempt {attempt} failed: {e}")
                if attempt == 2:
                    elimination_normalized = {"error": f"Claude elimination failed after 2 attempts: {e}"}
                    stage_errors["elimination"] += 1

        # Save raw elimination
        with open(item_raw_dir_tgt / f"{item_id}_elimination.json", "w", encoding="utf-8") as f:
            json.dump({
                "normalized": elimination_normalized,
                "meta": elim_meta if elimination_normalized and "error" not in elimination_normalized else None,
            }, f, indent=2, default=str)

        # ================================================================
        # STAGE 6: Disposition (recompute — no LLM call)
        # ================================================================
        disposition = compute_disposition(
            evaluations, challenge_normalized, audit_normalized,
            fragility_profile, elimination_normalized,
        )
        gold_comp = compare_to_gold(disposition, gold_label)

        terminal = disposition["terminal_state"]
        level = disposition["commitment_level"]
        label = disposition["commitment_label"]
        conviction = disposition.get("conviction_score", 0)
        match_marker = "OK" if gold_comp["gold_match"] else ("WH" if gold_comp["withheld"] else "X")
        log(f"    -> {terminal} ({level}), conviction={conviction:.3f}, gold={gold_label} [{match_marker}]")

        # Track comparison
        source_terminals.append(src.get("terminal_state", "???"))
        target_terminals.append(terminal)
        source_levels.append(src.get("commitment_level", "???"))
        target_levels.append(level)

        # Build result record
        result = {
            "item_id": item_id,
            "contract_id": contract_id,
            "hypothesis_id": hypothesis_id,
            "hypothesis_text": hypothesis_text,
            "evaluator_verdicts": src.get("evaluator_verdicts", {}),
            "cited_spans_per_evaluator": src.get("cited_spans_per_evaluator", {}),
            "agreement_pattern": agreement,
            "majority_verdict": src.get("majority_verdict"),
            "challenge_summary": {
                "overall_grounding_assessment": challenge_normalized.get("overall_grounding_assessment") if challenge_normalized else None,
                "total_challenges": len(challenge_normalized.get("challenges", [])) if challenge_normalized else 0,
            },
            "auditor_assessment": {
                "structural_validity": audit_normalized.get("structural_validity") if audit_normalized else None,
                "grounding_quality": audit_normalized.get("grounding_quality") if audit_normalized else None,
                "recommendation": audit_normalized.get("recommendation") if audit_normalized else None,
                "span_overlap": audit_normalized.get("span_overlap_assessment") if audit_normalized else None,
            },
            "fragility_score": fragility_profile["fragility_score"],
            "triggered_rules": fragility_profile["fired_rules"],
            "fragile": fragility_profile["fragile"],
            "fragility_cap": fragility_profile["max_cap"],
            "verdict_elimination": {
                "surviving_verdicts": elimination_normalized.get("surviving_verdicts", []) if elimination_normalized else [],
                "eliminated_verdicts": elimination_normalized.get("eliminated_verdicts", []) if elimination_normalized else [],
                "recommended_verdict": elimination_normalized.get("recommended_verdict") if elimination_normalized else None,
            },
            "terminal_state": terminal,
            "commitment_level": level,
            "commitment_label": label,
            "conviction_score": conviction,
            "downgrade_reasons": disposition.get("downgrade_reasons", []),
            "gold_label": gold_label,
            "gold_match": gold_comp["gold_match"],
            "withheld": gold_comp["withheld"],
            "enrichment_performed": src.get("enrichment_performed", False),
            "enrichment_summary": src.get("enrichment_summary", ""),
            "source_run": source_run_label,
            "challenge_provider": f"xai:{grok_model}",
            "audit_provider": f"mistral:{mistral_model}",
            "elimination_provider": f"anthropic:{claude_model}",
        }
        new_results.append(result)

    # Write results.jsonl
    results_file = target_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in new_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"\n  Results saved: {results_file} ({len(new_results)} items)")

    # Compute metrics
    total = len(new_results)
    asserted = sum(1 for r in new_results if not r.get("withheld", True))
    correct = sum(1 for r in new_results if r.get("gold_match", False) and not r.get("withheld", True))
    withheld_count = sum(1 for r in new_results if r.get("withheld", False))
    cca = (correct / asserted * 100) if asserted > 0 else 0.0

    # Source run metrics
    src_asserted = sum(1 for r in source_results if not r.get("withheld", True))
    src_correct = sum(1 for r in source_results if r.get("gold_match", False) and not r.get("withheld", True))
    src_cca = (src_correct / src_asserted * 100) if src_asserted > 0 else 0.0
    src_withheld = sum(1 for r in source_results if r.get("withheld", False))
    src_errors = src_asserted - src_correct
    tgt_errors = asserted - correct

    terminal_changes = sum(1 for s, t in zip(source_terminals, target_terminals) if s != t)
    level_changes = sum(1 for s, t in zip(source_levels, target_levels) if s != t)

    # Count ASSERT<->WITHHOLD flips
    aw_flips = 0
    for s, t in zip(source_terminals, target_terminals):
        s_is_assert = s.startswith("ASSERT_")
        t_is_assert = t.startswith("ASSERT_")
        if s_is_assert != t_is_assert:
            aw_flips += 1

    # Count verdict changes
    verdict_changes = 0
    for s, t in zip(source_terminals, target_terminals):
        s_verdict = s.replace("ASSERT_", "").replace("WITHHOLD_", "").replace("WITHHOLD_ASSERTION", "")
        t_verdict = t.replace("ASSERT_", "").replace("WITHHOLD_", "").replace("WITHHOLD_ASSERTION", "")
        if s_verdict != t_verdict and s_verdict and t_verdict:
            verdict_changes += 1

    # Error analysis
    src_error_items = set()
    tgt_error_items = set()
    for i, (sr, tr) in enumerate(zip(source_results, new_results)):
        sr_is_error = not sr.get("withheld", True) and not sr.get("gold_match", False)
        tr_is_error = not tr.get("withheld", True) and not tr.get("gold_match", False)
        if sr_is_error:
            src_error_items.add(i)
        if tr_is_error:
            tgt_error_items.add(i)

    shared_errors = len(src_error_items & tgt_error_items)
    src_only_errors = len(src_error_items - tgt_error_items)
    tgt_only_errors = len(tgt_error_items - src_error_items)

    # Write governance_comparison.txt
    comparison_lines = []
    comparison_lines.append("=" * 64)
    comparison_lines.append("FULLY DIVERSIFIED GOVERNANCE COMPARISON")
    comparison_lines.append(f"Run 4:  All Gemini governance (baseline)")
    comparison_lines.append(f"Run 4d: Grok challenger + Mistral auditor + Claude eliminator")
    comparison_lines.append(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    comparison_lines.append("=" * 64)
    comparison_lines.append("")
    comparison_lines.append("MODEL ROSTER:")
    comparison_lines.append(f"  Evaluator A:    Claude Sonnet 4      (unchanged)")
    comparison_lines.append(f"  Evaluator B:    GPT-5.2              (unchanged)")
    comparison_lines.append(f"  Evaluator C:    Grok 3               (unchanged)")
    comparison_lines.append(f"  Enrichment:     Gemini 3.1 Pro       (unchanged — preprocessing)")
    comparison_lines.append(f"  Challenger:     {grok_model}    (NEW — was Gemini)")
    comparison_lines.append(f"  Auditor:        {mistral_model}  (NEW — was Gemini)")
    comparison_lines.append(f"  Eliminator:     {claude_model}  (NEW — was Gemini)")
    comparison_lines.append(f"  Providers: 5 (Anthropic, OpenAI, xAI, Google, Mistral)")
    comparison_lines.append(f"  Gemini-only role: Enrichment (preprocessing)")
    comparison_lines.append("")
    comparison_lines.append("METRICS COMPARISON:")
    comparison_lines.append(f"                        Run 4       Run 4d      Delta")
    comparison_lines.append(f"  Asserted:             {src_asserted:<12}{asserted:<12}{asserted - src_asserted:+d}")
    comparison_lines.append(f"  Withheld:             {src_withheld:<12}{withheld_count:<12}{withheld_count - src_withheld:+d}")
    comparison_lines.append(f"  Correct (asserted):   {src_correct:<12}{correct:<12}{correct - src_correct:+d}")
    src_cca_s = f"{src_cca:.1f}%"
    tgt_cca_s = f"{cca:.1f}%"
    delta_cca_s = f"{cca - src_cca:+.1f}%"
    comparison_lines.append(f"  CCA:                  {src_cca_s:<12}{tgt_cca_s:<12}{delta_cca_s}")
    comparison_lines.append(f"  Errors (vs gold):     {src_errors:<12}{tgt_errors:<12}{tgt_errors - src_errors:+d}")
    comparison_lines.append("")
    comparison_lines.append("DISPOSITION CHANGES vs Run 4:")
    comparison_lines.append(f"  Terminal state changes: {terminal_changes}/{total}")
    comparison_lines.append(f"  Commitment level changes: {level_changes}/{total}")
    comparison_lines.append(f"  ASSERT<->WITHHOLD flips: {aw_flips}")
    comparison_lines.append(f"  Verdict changes: {verdict_changes}")
    comparison_lines.append("")
    comparison_lines.append("ERROR ANALYSIS:")
    comparison_lines.append(f"  Run 4 errors: {src_errors}")
    comparison_lines.append(f"  Run 4d errors: {tgt_errors}")
    comparison_lines.append(f"  Shared errors: {shared_errors}")
    comparison_lines.append(f"  Run 4 only errors: {src_only_errors}")
    comparison_lines.append(f"  Run 4d only errors: {tgt_only_errors}")
    comparison_lines.append("")
    if any(v > 0 for v in stage_errors.values()):
        comparison_lines.append("STAGE ERRORS:")
        for stage, count in stage_errors.items():
            if count > 0:
                comparison_lines.append(f"  {stage}: {count} items failed")
        comparison_lines.append("")

    # Detail: items where terminal state changed
    if terminal_changes > 0:
        comparison_lines.append("=" * 64)
        comparison_lines.append("TERMINAL STATE CHANGES (detail)")
        comparison_lines.append("=" * 64)
        comparison_lines.append("")
        for i, (s, t) in enumerate(zip(source_terminals, target_terminals)):
            if s != t:
                item = new_results[i]
                src_gold_match = source_results[i].get("gold_match", False)
                tgt_gold_match = item.get("gold_match", False)
                src_withheld_flag = source_results[i].get("withheld", False)
                tgt_withheld_flag = item.get("withheld", False)

                # Classify the change
                if src_gold_match and not src_withheld_flag:
                    src_status = "OK"
                elif src_withheld_flag:
                    src_status = "WH"
                else:
                    src_status = "X"

                if tgt_gold_match and not tgt_withheld_flag:
                    tgt_status = "OK"
                elif tgt_withheld_flag:
                    tgt_status = "WH"
                else:
                    tgt_status = "X"

                comparison_lines.append(f"  {item['item_id']}: {s} -> {t}")
                comparison_lines.append(f"    Level: {source_levels[i]} -> {target_levels[i]}")
                comparison_lines.append(f"    Gold: {item['gold_label']}, outcome: {src_status} -> {tgt_status}")
                comparison_lines.append("")

    comparison_text = "\n".join(comparison_lines)
    comparison_file = target_dir / "governance_comparison.txt"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write(comparison_text)

    # Print summary
    log("")
    log(comparison_text)
    log(f"\n  Comparison saved: {comparison_file}")

    # Write run manifest
    manifest = {
        "run_label": target_run_label,
        "source_run": source_run_label,
        "type": "diversified-governance",
        "challenge_provider": f"xai:{grok_model}",
        "audit_provider": f"mistral:{mistral_model}",
        "elimination_provider": f"anthropic:{claude_model}",
        "source_challenge_provider": "google:gemini-3.1-pro-preview",
        "source_audit_provider": "google:gemini-3.1-pro-preview",
        "source_elimination_provider": "google:gemini-3.1-pro-preview",
        "total_items": total,
        "asserted": asserted,
        "withheld": withheld_count,
        "cca": round(cca, 1),
        "errors": tgt_errors,
        "stage_errors": stage_errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(target_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log(f"\n  Run manifest saved: {target_dir / 'run_manifest.json'}")
    log("=" * 70)
    log("  DIVERSIFIED GOVERNANCE RUN COMPLETE")
    log("=" * 70)


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    # Parse common arguments
    def _parse_arg(name, default=None, cast=None):
        for i, arg in enumerate(sys.argv):
            if arg == name and i + 1 < len(sys.argv):
                val = sys.argv[i + 1]
                return cast(val) if cast else val
        return default

    n = _parse_arg("--n", default=10, cast=int)
    seed = _parse_arg("--seed", default=1337, cast=int)
    resume = _parse_arg("--resume")
    run_name = _parse_arg("--run")
    contracts_filter = _parse_arg("--contracts")

    enrich = "--enrich" in sys.argv

    source_run = _parse_arg("--source-run")
    audit_model_arg = _parse_arg("--audit-model", default="mistral")
    elim_model_arg = _parse_arg("--elim-model", default="claude")
    challenge_model_arg = _parse_arg("--challenge-model", default="grok")
    adjudication_model_arg = _parse_arg("--adjudication-model", default="gemini")

    if "--rerun-governance" in sys.argv:
        # Full diversified governance: re-run challenge + audit + elimination with alt providers
        src = source_run if source_run else "4 ContractNLI Full"
        tgt = run_name if run_name else "4d ContractNLI Diversified Governance"
        run_diversified_governance(
            source_run_label=src, target_run_label=tgt,
            challenge_model=challenge_model_arg,
            audit_model=audit_model_arg,
            elim_model=elim_model_arg,
        )
    elif "--recompute-disposition" in sys.argv:
        # Combine audit from one run + elimination from another, recompute disposition
        audit_run = _parse_arg("--audit-run", default="4a ContractNLI Mistral Audit")
        elim_run = _parse_arg("--elim-run", default="4b ContractNLI Claude Elimination")
        baseline = source_run if source_run else "4 ContractNLI Full"
        tgt = run_name if run_name else "4c ContractNLI Combined Governance"
        run_recompute_disposition(
            audit_run_label=audit_run, elim_run_label=elim_run,
            baseline_run_label=baseline, target_run_label=tgt,
        )
    elif "--rerun-elimination" in sys.argv:
        # Re-run elimination stage with alternative provider, recompute disposition
        src = source_run if source_run else "4 ContractNLI Full"
        tgt = run_name if run_name else "4b ContractNLI Claude Elimination"
        run_rerun_elimination(source_run_label=src, target_run_label=tgt, elim_model=elim_model_arg)
    elif "--rerun-audit" in sys.argv:
        # Re-run audit stage with alternative provider, recompute disposition
        src = source_run if source_run else "4 ContractNLI Full"
        tgt = run_name if run_name else "4a ContractNLI Mistral Audit"
        run_rerun_audit(source_run_label=src, target_run_label=tgt, audit_model=audit_model_arg)
    elif "--adjudicate" in sys.argv:
        # Post-hoc adjudication of gold mismatches
        from cam.adapters.contractnli.contractnli_adjudicate import run_adjudication
        run_label = run_name if run_name else "3a ContractNLI Targeted"
        run_adjudication(run_label, adjudication_model=adjudication_model_arg)
    elif "--run-full" in sys.argv:
        # Full pipeline: all 6 stages, all items, with resume
        run_label = run_name if run_name else "1 ContractNLI Run"
        contract_ids = None
        if contracts_filter:
            contract_ids = [int(c.strip()) for c in contracts_filter.split(",")]
        run_full_pipeline(n_contracts=n, seed=seed, run_label=run_label, enrich=enrich,
                          contract_ids=contract_ids)
    elif "--smoke-test" in sys.argv:
        # Smoke test: 1 contract × 17 hypotheses (full pipeline)
        run_label = run_name if run_name else "smoke_test_021"
        run_full_pipeline(n_contracts=1, seed=seed, run_label=run_label, enrich=enrich)
    elif "--dry-run" in sys.argv:
        dry_run(n=n, seed=seed)
    elif "--stage2" in sys.argv:
        # Stage 2 reads Stage 1 results
        stage1_dir = None
        if run_name:
            stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / run_name
        run_stage2_challenge(stage1_dir=stage1_dir)
    elif "--stage3" in sys.argv:
        # Stage 3 reads Stages 1-2 results
        stage1_dir = None
        stage2_dir = None
        if run_name:
            stage1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / run_name
            stage2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / run_name
        run_stage3_audit(stage1_dir=stage1_dir, stage2_dir=stage2_dir)
    elif "--stage4" in sys.argv:
        # Stage 4 reads Stages 1-3 results (programmatic, no LLM)
        stage1_dir = None
        stage2_dir = None
        stage3_dir = None
        if run_name:
            base = CAM_ROOT / "04 ContractNLI" / "Runs" / run_name
            stage1_dir = base
            stage2_dir = base
            stage3_dir = base
        run_stage4_fragility(stage1_dir=stage1_dir, stage2_dir=stage2_dir,
                             stage3_dir=stage3_dir)
    elif "--stage5" in sys.argv:
        # Stage 5 reads Stages 1-4 results
        if run_name:
            base = CAM_ROOT / "04 ContractNLI" / "Runs" / run_name
            run_stage5_elimination(stage1_dir=base, stage2_dir=base,
                                   stage3_dir=base, stage4_dir=base)
        else:
            run_stage5_elimination()
    elif "--stage6" in sys.argv:
        # Stage 6 reads Stages 1-5 results (programmatic, no LLM)
        if run_name:
            base = CAM_ROOT / "04 ContractNLI" / "Runs" / run_name
            run_stage6_disposition(stage1_dir=base, stage2_dir=base,
                                   stage3_dir=base, stage4_dir=base,
                                   stage5_dir=base)
        else:
            run_stage6_disposition()
    elif "--stage1" in sys.argv:
        run_stage1(n_contracts=n, seed=seed)
    elif "--test-eval" in sys.argv:
        # Quick test: 1 contract x 1 hypothesis
        run_stage1(n_contracts=1, seed=seed, test_mode=True)
    elif "--test-challenge" in sys.argv:
        # Combined test: Stage 1 (1 contract x 3 hypotheses) + Stage 2 challenge
        test_s1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018_stage1"
        test_s2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_018"
        stage1_results = run_stage1(
            n_contracts=1, seed=seed, test_mode=True,
            test_n_hyps=3, run_label="test_018_stage1"
        )
        run_stage2_challenge(
            stage1_results=stage1_results,
            run_dir=test_s2_dir,
            stage1_dir=test_s1_dir,
        )
    elif "--test-audit" in sys.argv:
        # Combined test: Stages 1-4 (1 contract x 3-4 hypotheses)
        test_s1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019_stage1"
        test_s2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019_stage2"
        test_s34_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_019"
        test_n_hyps = _parse_arg("--hyps", default=4, cast=int)
        # Stage 1
        stage1_results = run_stage1(
            n_contracts=1, seed=seed, test_mode=True,
            test_n_hyps=test_n_hyps, run_label="test_019_stage1"
        )
        # Stage 2
        challenge_results = run_stage2_challenge(
            stage1_results=stage1_results,
            run_dir=test_s2_dir,
            stage1_dir=test_s1_dir,
        )
        # Stage 3
        audit_results = run_stage3_audit(
            stage1_results=stage1_results,
            challenge_results=challenge_results,
            run_dir=test_s34_dir,
            stage1_dir=test_s1_dir,
            stage2_dir=test_s2_dir,
        )
        # Stage 4
        run_stage4_fragility(
            stage1_results=stage1_results,
            challenge_results=challenge_results,
            audit_results=audit_results,
            run_dir=test_s34_dir,
            stage1_dir=test_s1_dir,
            stage2_dir=test_s2_dir,
            stage3_dir=test_s34_dir,
        )
    elif "--test-pipeline" in sys.argv:
        # Full 6-stage pipeline test (1 contract x 3-4 hypotheses)
        test_n_hyps = _parse_arg("--hyps", default=4, cast=int)
        test_s1_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_020_stage1"
        test_s2_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_020_stage2"
        test_s34_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_020_stage34"
        test_s56_dir = CAM_ROOT / "04 ContractNLI" / "Runs" / "test_020"
        # Stage 1
        stage1_results = run_stage1(
            n_contracts=1, seed=seed, test_mode=True,
            test_n_hyps=test_n_hyps, run_label="test_020_stage1"
        )
        # Stage 2
        challenge_results = run_stage2_challenge(
            stage1_results=stage1_results,
            run_dir=test_s2_dir,
            stage1_dir=test_s1_dir,
        )
        # Stage 3
        audit_results = run_stage3_audit(
            stage1_results=stage1_results,
            challenge_results=challenge_results,
            run_dir=test_s34_dir,
            stage1_dir=test_s1_dir,
            stage2_dir=test_s2_dir,
        )
        # Stage 4
        fragility_results = run_stage4_fragility(
            stage1_results=stage1_results,
            challenge_results=challenge_results,
            audit_results=audit_results,
            run_dir=test_s34_dir,
            stage1_dir=test_s1_dir,
            stage2_dir=test_s2_dir,
            stage3_dir=test_s34_dir,
        )
        # Stage 5
        elimination_results = run_stage5_elimination(
            stage1_results=stage1_results,
            challenge_results=challenge_results,
            audit_results=audit_results,
            fragility_results=fragility_results,
            run_dir=test_s56_dir,
            stage1_dir=test_s1_dir,
            stage2_dir=test_s2_dir,
            stage3_dir=test_s34_dir,
            stage4_dir=test_s34_dir,
        )
        # Stage 6
        run_stage6_disposition(
            stage1_results=stage1_results,
            challenge_results=challenge_results,
            audit_results=audit_results,
            fragility_results=fragility_results,
            elimination_results=elimination_results,
            run_dir=test_s56_dir,
            stage1_dir=test_s1_dir,
            stage2_dir=test_s2_dir,
            stage3_dir=test_s34_dir,
            stage4_dir=test_s34_dir,
            stage5_dir=test_s56_dir,
        )
    else:
        log("ContractNLI Adapter -- no action specified.")
        log("Available flags:")
        log("  --run-full         Full pipeline: all 6 stages, all items, with resume")
        log("  --smoke-test       Smoke test: 1 contract x 17 hypotheses (full pipeline)")
        log("  --dry-run          Load data and print stats (no model calls)")
        log("  --stage1           Run Stage 1 parallel evaluation")
        log("  --stage2           Run Stage 2 evidence challenge")
        log("  --stage3           Run Stage 3 structural audit")
        log("  --stage4           Run Stage 4 fragility detection (no LLM)")
        log("  --stage5           Run Stage 5 verdict elimination")
        log("  --stage6           Run Stage 6 disposition (no LLM)")
        log("  --test-eval        Test: 1 contract x 1 hypothesis (quick API test)")
        log("  --test-challenge   Test: Stages 1-2 on 1 contract x 3 hypotheses")
        log("  --test-audit       Test: Stages 1-4 on 1 contract x 3-4 hypotheses")
        log("  --test-pipeline    Test: Full 6-stage pipeline on 1 contract x 3-4 hyps")
        log("  --enrich           Enable legal context enrichment (web search before challenge)")
        log("  --run NAME         Specify run directory name (default varies by mode)")
        log("  --n N              Number of contracts to sample (default: 10)")
        log("  --hyps N           Number of hypotheses in test modes (default: 4)")
        log("  --seed N           Random seed (default: 1337)")
        log("  --contracts N,M    Filter to specific contract IDs")
        log("  --adjudicate       Post-hoc adjudication of gold mismatches")
        log("  --adjudication-model NAME  Adjudication model: 'gemini' (default) or 'gpt'")
        log("  --rerun-governance Full diversified governance run (challenge+audit+elimination)")
        log("  --rerun-audit      Re-run audit stage with alternative provider")
        log("  --rerun-elimination Re-run elimination stage with alternative provider")
        log("  --recompute-disposition Recompute disposition from combined governance swaps")
        log("  --source-run NAME  Source run (default: '4 ContractNLI Full')")
        log("  --challenge-model NAME Challenge model (default: 'grok')")
        log("  --audit-model NAME Audit model (default: 'mistral')")
        log("  --elim-model NAME  Elimination model (default: 'claude')")
