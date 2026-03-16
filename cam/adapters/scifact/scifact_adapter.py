"""
CAM SciFact Adapter — Dataset Loading and Claim Extraction
Phase 2: Scientific claim verification against evidence abstracts.

This module handles:
- Loading the allenai/scifact dataset (from S3 source archive)
- Building corpus lookup (doc_id -> abstract)
- Extracting and normalizing claim data
- Formatting abstracts for evaluator prompts

Note: The HuggingFace allenai/scifact dataset uses a deprecated loading
script, so we download the raw data directly from the S3 source archive
and parse the JSONL files ourselves. Data is cached locally after first
download.
"""

import json
import io
import os
import random
import sys
import tarfile
import time
import urllib.request
from collections import Counter
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

SCIFACT_DATA_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
SCIFACT_CACHE_DIR = CAM_ROOT / "03 SciFact" / "scifact_data"

# Compact example JSON for the evaluator prompt.
# We show an example instead of the full JSON Schema definition, because
# Gemini echoes the schema back and truncates its actual response.
EVALUATOR_EXAMPLE_JSON = """{
  "verdict": "SUPPORT",
  "confidence": "high",
  "cited_sentences": [2, 5],
  "reasoning": "Sentences 2 and 5 directly state that...",
  "scope_assessment": {
    "claim_scope": "Effect of X on Y in humans",
    "evidence_scope": "Study of X on Y in human subjects",
    "scope_match": "exact",
    "scope_notes": "The abstract directly addresses the claim."
  },
  "assumptions": ["Assuming the study population is representative."],
  "evidence_sufficiency": "sufficient",
  "key_evidence": "Sentence 5 states that X significantly increased Y (p<0.01)."
}"""

# Label mapping: raw data uses SUPPORTS/REFUTES, we normalize to SUPPORT/CONTRADICT
LABEL_MAP = {
    "SUPPORTS": "SUPPORT",
    "SUPPORT": "SUPPORT",
    "REFUTES": "CONTRADICT",
    "CONTRADICT": "CONTRADICT",
    "NOT_ENOUGH_INFO": "NOT_ENOUGH_INFO",
    "NEI": "NOT_ENOUGH_INFO",
}


# ============================================================
# Dataset Loading
# ============================================================

def _download_and_extract(cache_dir):
    """Download SciFact data.tar.gz and extract JSONL files to cache_dir."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check if already cached
    corpus_file = cache_dir / "corpus.jsonl"
    claims_train = cache_dir / "claims_train.jsonl"
    if corpus_file.exists() and claims_train.exists():
        log(f"  Using cached data from {cache_dir}")
        return

    log(f"  Downloading SciFact data from {SCIFACT_DATA_URL}...")
    response = urllib.request.urlopen(SCIFACT_DATA_URL)
    data = response.read()
    log(f"  Downloaded {len(data) / 1024 / 1024:.1f} MB")

    log("  Extracting JSONL files...")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".jsonl"):
                # Extract to cache_dir with flat filename
                filename = Path(member.name).name
                target_path = cache_dir / filename
                f = tar.extractfile(member)
                if f is not None:
                    target_path.write_bytes(f.read())
                    log(f"    Extracted: {filename}")

    log("  Extraction complete.")


def _load_jsonl(filepath):
    """Load a JSONL file, return list of dicts."""
    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _parse_claims(raw_claims):
    """
    Parse raw claim records into normalized format.

    Raw format has nested evidence:
      {"id": 1, "claim": "...", "evidence": {"doc_id": [{"sentences": [...], "label": "SUPPORTS"}]}, "cited_doc_ids": [...]}

    We flatten each claim-evidence pair into:
      {"id": 1, "claim": "...", "evidence_doc_id": doc_id, "evidence_label": "SUPPORT", "evidence_sentences": [...], "cited_doc_ids": [...]}

    Claims with empty evidence get evidence_doc_id=None, evidence_label=None.
    """
    parsed = []
    for raw in raw_claims:
        evidence = raw.get("evidence", {})
        cited_doc_ids = raw.get("cited_doc_ids", [])

        if not evidence:
            # No evidence annotations (e.g., test set, or NEI claims)
            parsed.append({
                "id": raw["id"],
                "claim": raw["claim"],
                "evidence_doc_id": None,
                "evidence_label": None,
                "evidence_sentences": [],
                "cited_doc_ids": cited_doc_ids,
            })
            continue

        # Each claim can have evidence from multiple docs;
        # flatten into one record per evidence doc
        for doc_id_str, annotations in evidence.items():
            doc_id = int(doc_id_str)
            for annotation in annotations:
                raw_label = annotation.get("label", "")
                label = LABEL_MAP.get(raw_label, raw_label)
                sentences = annotation.get("sentences", [])
                parsed.append({
                    "id": raw["id"],
                    "claim": raw["claim"],
                    "evidence_doc_id": doc_id,
                    "evidence_label": label,
                    "evidence_sentences": sentences,
                    "cited_doc_ids": cited_doc_ids,
                })

    return parsed


def load_scifact_dataset(cache_dir=None):
    """
    Load the SciFact dataset from S3 source archive.

    Downloads and caches the data locally on first call.

    Args:
        cache_dir: Path to cache directory (default: 03 SciFact/scifact_data/)

    Returns:
        claims_by_split: dict of split_name -> list of claim dicts
            Each claim dict has keys: id, claim, evidence_doc_id, evidence_label,
            evidence_sentences, cited_doc_ids
        corpus_lookup: dict mapping doc_id (int) -> {title, abstract, structured}
    """
    if cache_dir is None:
        cache_dir = SCIFACT_CACHE_DIR

    log("Loading SciFact dataset...")

    # Download if needed
    _download_and_extract(cache_dir)

    # Load corpus
    log("  Loading corpus...")
    corpus_raw = _load_jsonl(cache_dir / "corpus.jsonl")
    corpus_lookup = {}
    for doc in corpus_raw:
        corpus_lookup[doc["doc_id"]] = {
            "title": doc["title"],
            "abstract": doc["abstract"],
            "structured": doc["structured"],
        }
    log(f"  Corpus loaded: {len(corpus_lookup)} documents")

    # Load claims splits
    split_files = {
        "train": "claims_train.jsonl",
        "validation": "claims_dev.jsonl",
        "test": "claims_test.jsonl",
    }

    claims_by_split = {}
    for split_name, filename in split_files.items():
        filepath = cache_dir / filename
        if filepath.exists():
            raw = _load_jsonl(filepath)
            parsed = _parse_claims(raw)
            claims_by_split[split_name] = parsed
            log(f"  {split_name}: {len(parsed)} claim-evidence pairs (from {len(raw)} raw claims)")
        else:
            log(f"  {split_name}: file not found ({filename}), skipping")

    return claims_by_split, corpus_lookup


# ============================================================
# Claim Extraction
# ============================================================

def extract_claim_data(claim_record, corpus_lookup):
    """
    Extract and normalize a single claim record.

    Args:
        claim_record: A single parsed claim dict (from load_scifact_dataset).
        corpus_lookup: dict mapping doc_id (int) -> {title, abstract, structured}

    Returns:
        dict with normalized claim data.
    """
    evidence_doc_id = claim_record["evidence_doc_id"]

    # Claims without evidence
    if evidence_doc_id is None:
        return {
            "claim_id": claim_record["id"],
            "claim_text": claim_record["claim"],
            "evidence_doc_id": None,
            "evidence_label": claim_record["evidence_label"],
            "evidence_sentences": claim_record["evidence_sentences"],
            "cited_doc_ids": claim_record["cited_doc_ids"],
            "abstract_title": None,
            "abstract_sentences": None,
            "abstract_structured": None,
        }

    corpus_entry = corpus_lookup.get(evidence_doc_id)
    if corpus_entry is None:
        # Evidence doc_id doesn't match any corpus entry
        return {
            "claim_id": claim_record["id"],
            "claim_text": claim_record["claim"],
            "evidence_doc_id": evidence_doc_id,
            "evidence_label": claim_record["evidence_label"],
            "evidence_sentences": claim_record["evidence_sentences"],
            "cited_doc_ids": claim_record["cited_doc_ids"],
            "abstract_title": None,
            "abstract_sentences": None,
            "abstract_structured": None,
        }

    return {
        "claim_id": claim_record["id"],
        "claim_text": claim_record["claim"],
        "evidence_doc_id": evidence_doc_id,
        "evidence_label": claim_record["evidence_label"],
        "evidence_sentences": claim_record["evidence_sentences"],
        "cited_doc_ids": claim_record["cited_doc_ids"],
        "abstract_title": corpus_entry["title"],
        "abstract_sentences": corpus_entry["abstract"],
        "abstract_structured": corpus_entry["structured"],
    }


# ============================================================
# Abstract Formatting
# ============================================================

def format_abstract_for_prompt(abstract_sentences):
    """
    Format abstract sentences with numbered indices for evaluator prompts.

    Args:
        abstract_sentences: list of sentence strings from the corpus.

    Returns:
        Formatted string with numbered sentences, e.g.:
        [0] First sentence of the abstract.
        [1] Second sentence of the abstract.
    """
    if not abstract_sentences:
        return "[No abstract available]"

    lines = []
    for i, sentence in enumerate(abstract_sentences):
        lines.append(f"[{i}] {sentence}")
    return "\n".join(lines)


# ============================================================
# Evaluator Test (Step 008)
# ============================================================

def _pick_test_claims(val_split, corpus_lookup, n=3):
    """
    Pick deterministic test claims: first SUPPORT, first CONTRADICT,
    first NEI (no evidence) from validation split.
    """
    targets = {"SUPPORT": None, "CONTRADICT": None, "NEI": None}
    for record in val_split:
        label = record["evidence_label"]
        doc_id = record["evidence_doc_id"]
        if label == "SUPPORT" and targets["SUPPORT"] is None and doc_id is not None:
            targets["SUPPORT"] = record
        elif label == "CONTRADICT" and targets["CONTRADICT"] is None and doc_id is not None:
            targets["CONTRADICT"] = record
        elif label is None and targets["NEI"] is None:
            # NEI = no evidence annotation
            # For NEI, we still need an abstract to evaluate against.
            # Use the first cited_doc_id if available.
            cited = record.get("cited_doc_ids", [])
            if cited and cited[0] in corpus_lookup:
                targets["NEI"] = record
        if all(v is not None for v in targets.values()):
            break

    result = []
    for label_type in ["SUPPORT", "CONTRADICT", "NEI"]:
        if targets[label_type] is not None:
            result.append((label_type, targets[label_type]))
    return result[:n]


def test_single_evaluator(n_claims=3):
    """Test evaluator prompt with a single model on a few claims."""
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.scifact.scifact_normalize import normalize_evaluator_response

    # Load env for API keys
    find_and_load_env()

    # Load prompt template (uses compact example instead of full schema)
    prompt_path = Path(__file__).parent / "prompts" / "evaluator.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Load dataset
    claims_by_split, corpus_lookup = load_scifact_dataset()
    val_split = claims_by_split.get("validation", [])

    # Pick test claims
    test_claims = _pick_test_claims(val_split, corpus_lookup, n=n_claims)
    log(f"Selected {len(test_claims)} test claims")

    # Set up provider router with Claude Sonnet
    target = ModelTarget(
        name="anthropic:claude-sonnet-4-5",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        priority=1,
        max_output_tokens=1500,
        temperature=0.0,
        timeout_sec=60.0,
    )
    router = ProviderRouter(targets=[target])

    # Create test output directory
    test_dir = CAM_ROOT / "03 SciFact" / "Runs" / "test_008"
    test_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for i, (label_type, record) in enumerate(test_claims):
        claim_data = extract_claim_data(record, corpus_lookup)

        # For NEI claims without evidence_doc_id, use first cited doc
        if claim_data["abstract_sentences"] is None:
            cited = record.get("cited_doc_ids", [])
            if cited and cited[0] in corpus_lookup:
                corpus_entry = corpus_lookup[cited[0]]
                claim_data["abstract_title"] = corpus_entry["title"]
                claim_data["abstract_sentences"] = corpus_entry["abstract"]
                claim_data["abstract_structured"] = corpus_entry["structured"]
                claim_data["evidence_doc_id"] = cited[0]

        if claim_data["abstract_sentences"] is None:
            log(f"  Skipping claim {claim_data['claim_id']} — no abstract available")
            continue

        formatted_abstract = format_abstract_for_prompt(claim_data["abstract_sentences"])

        # Fill prompt template
        prompt = prompt_template.replace("{claim_text}", claim_data["claim_text"])
        prompt = prompt.replace("{abstract_title}", claim_data["abstract_title"] or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{example_json}", EVALUATOR_EXAMPLE_JSON)

        print()
        print("=" * 70)
        print(f"  Test {i+1}/{len(test_claims)}: Claim {claim_data['claim_id']} (gold: {label_type})")
        print("=" * 70)
        print(f"  Claim: {claim_data['claim_text']}")
        print(f"  Gold label: {claim_data['evidence_label']}")
        print()

        # Call model via provider router
        log(f"  Calling Claude Sonnet for claim {claim_data['claim_id']}...")
        try:
            raw_obj, meta = router.call_json(
                system_prompt="You are a scientific claim verification evaluator. Respond only with valid JSON.",
                user_prompt=prompt,
            )
            raw_response = json.dumps(raw_obj)
            log(f"  Response received from {meta['target']['name']}")
        except Exception as e:
            log(f"  ERROR: API call failed: {e}")
            raw_response = ""
            results.append({
                "claim_id": claim_data["claim_id"],
                "gold_label": label_type,
                "error": str(e),
            })
            continue

        # Normalize response
        normalized = normalize_evaluator_response(raw_response, f"Test-{i+1}")

        # Display results
        if "error" in normalized:
            print(f"  PARSE ERROR: {normalized['error']}")
        else:
            print(f"  Verdict: {normalized.get('verdict', '???')}")
            print(f"  Confidence: {normalized.get('confidence', '???')}")
            print(f"  Cited sentences: {normalized.get('cited_sentences', [])}")
            print(f"  Schema valid: {normalized.get('schema_valid', '???')}")
            if normalized.get("schema_error"):
                print(f"  Schema error: {normalized['schema_error']}")
            print(f"  Key evidence: {normalized.get('key_evidence', '')[:100]}")
            sa = normalized.get("scope_assessment", {})
            print(f"  Scope match: {sa.get('scope_match', '???')}")

        # Save raw response
        output_file = test_dir / f"claim_{claim_data['claim_id']}_{label_type}.json"
        output_data = {
            "claim_id": claim_data["claim_id"],
            "claim_text": claim_data["claim_text"],
            "gold_label": label_type,
            "evidence_doc_id": claim_data["evidence_doc_id"],
            "gold_sentences": claim_data["evidence_sentences"],
            "raw_response": raw_response,
            "normalized": normalized,
            "meta": meta,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, default=str)
        log(f"  Saved to {output_file.name}")

        results.append(output_data)

    # Summary
    print()
    print("=" * 70)
    print("  Test Summary")
    print("=" * 70)
    for r in results:
        if "error" in r and "normalized" not in r:
            print(f"  Claim {r['claim_id']} ({r['gold_label']}): ERROR — {r['error']}")
        else:
            n = r.get("normalized", {})
            verdict = n.get("verdict", "???")
            valid = n.get("schema_valid", False)
            match = "MATCH" if verdict == r["gold_label"] else "MISMATCH"
            print(f"  Claim {r['claim_id']} ({r['gold_label']}): verdict={verdict} schema_valid={valid} [{match}]")

    print()
    print(f"  Results saved to: {test_dir}")
    print("=" * 70)


# ============================================================
# Stage 1: Parallel Evaluation (Step 009)
# ============================================================

# Model roster for SciFact evaluators
SCIFACT_EVALUATORS = [
    {"label": "A", "name": "anthropic:claude-sonnet-4-5", "provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    {"label": "B", "name": "google:gemini-3-pro-preview", "provider": "google", "model": "gemini-3-pro-preview"},
    {"label": "C", "name": "xai:grok", "provider": "xai", "model": "grok-3"},
]


def _select_stage1_claims(val_split, corpus_lookup, n=5):
    """
    Select N claims deterministically for Stage 1 evaluation.
    Target: 2 SUPPORT, 2 CONTRADICT, 1 NEI.
    Skips claim_id 3 (tested in Step 008).
    """
    support_claims = []
    contradict_claims = []
    nei_claims = []

    seen_ids = set()
    for record in val_split:
        claim_id = record["id"]
        if claim_id == 3:
            continue  # Skip Step 008 test case
        if claim_id in seen_ids:
            continue  # Skip duplicate claim IDs (from flattening)
        seen_ids.add(claim_id)

        label = record["evidence_label"]
        doc_id = record["evidence_doc_id"]

        if label == "SUPPORT" and doc_id is not None and len(support_claims) < 2:
            support_claims.append(record)
        elif label == "CONTRADICT" and doc_id is not None and len(contradict_claims) < 2:
            contradict_claims.append(record)
        elif label is None and len(nei_claims) < 1:
            cited = record.get("cited_doc_ids", [])
            if cited and cited[0] in corpus_lookup:
                nei_claims.append(record)

        if len(support_claims) >= 2 and len(contradict_claims) >= 2 and len(nei_claims) >= 1:
            break

    selected = support_claims + contradict_claims + nei_claims
    return selected[:n]


def _select_production_claims(val_split, corpus_lookup, n=50, seed=1337):
    """
    Select N claims deterministically via random.sample with a fixed seed.
    Filters to claims with both evidence_doc_id AND a gold label,
    OR NEI claims with a usable cited doc.
    Deduplicates by claim_id (picks first record per id).
    """
    rng = random.Random(seed)

    # Deduplicate by claim_id
    seen_ids = set()
    valid = []
    for record in val_split:
        cid = record["id"]
        if cid in seen_ids:
            continue
        seen_ids.add(cid)

        label = record["evidence_label"]
        doc_id = record["evidence_doc_id"]

        # Case 1: Has evidence doc + gold label
        if doc_id is not None and label is not None and doc_id in corpus_lookup:
            valid.append(record)
            continue

        # Case 2: NEI (no evidence annotation) but has cited doc
        if label is None:
            cited = record.get("cited_doc_ids", [])
            if cited and cited[0] in corpus_lookup:
                valid.append(record)
                continue

    log(f"  Production sampling: {len(valid)} valid claims from {len(seen_ids)} unique claim IDs")

    if len(valid) <= n:
        log(f"  Using all {len(valid)} valid claims (fewer than requested {n})")
        return valid

    selected = rng.sample(valid, n)
    return selected


def _compute_agreement_pattern(evaluations):
    """
    Compute agreement pattern from evaluator verdicts.

    Returns:
        pattern: str, e.g. "3-0 SUPPORT", "2-1 SUPPORT/CONTRADICT", "1-1-1"
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
        # Unanimous
        verdict = most_common[0][0]
        return f"3-0 {verdict}", verdict
    elif most_common[0][1] >= 2:
        # Majority
        majority = most_common[0][0]
        minority = most_common[1][0]
        return f"2-1 {majority}/{minority}", majority
    else:
        # Full split
        return "1-1-1", None


def run_parallel_evaluation(claims, corpus_lookup, evaluators, run_dir):
    """
    Stage 1: Run all evaluators independently on each claim.

    Args:
        claims: list of claim records (raw from dataset)
        corpus_lookup: doc_id -> corpus entry
        evaluators: list of dicts with {label, name, provider, model}
        run_dir: path to save outputs

    Returns:
        list of result dicts, one per claim
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.scifact.scifact_normalize import normalize_evaluator_response

    find_and_load_env()

    # Load prompt template (uses compact example instead of full schema)
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
            timeout_sec=90.0,
        )
        routers[ev["label"]] = ProviderRouter(targets=[target])

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for claim_idx, record in enumerate(claims):
        claim_data = extract_claim_data(record, corpus_lookup)

        # For NEI claims without evidence_doc_id, use first cited doc
        if claim_data["abstract_sentences"] is None:
            cited = record.get("cited_doc_ids", [])
            if cited and cited[0] in corpus_lookup:
                corpus_entry = corpus_lookup[cited[0]]
                claim_data["abstract_title"] = corpus_entry["title"]
                claim_data["abstract_sentences"] = corpus_entry["abstract"]
                claim_data["abstract_structured"] = corpus_entry["structured"]
                claim_data["evidence_doc_id"] = cited[0]

        if claim_data["abstract_sentences"] is None:
            log(f"  Skipping claim {claim_data['claim_id']} — no abstract available")
            continue

        gold_label = claim_data["evidence_label"] or "NEI"
        formatted_abstract = format_abstract_for_prompt(claim_data["abstract_sentences"])

        # Fill prompt template
        prompt = prompt_template.replace("{claim_text}", claim_data["claim_text"])
        prompt = prompt.replace("{abstract_title}", claim_data["abstract_title"] or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{example_json}", EVALUATOR_EXAMPLE_JSON)

        print()
        print("=" * 70)
        print(f"  Claim {claim_idx+1}/{len(claims)}: ID={claim_data['claim_id']} (gold: {gold_label})")
        print("=" * 70)
        print(f"  Claim: {claim_data['claim_text'][:120]}...")
        print()

        # Create per-claim raw output directory
        claim_raw_dir = raw_dir / f"claim_{claim_data['claim_id']}_{gold_label}"
        claim_raw_dir.mkdir(parents=True, exist_ok=True)

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
                        system_prompt="You are a scientific claim verification evaluator. Respond only with valid JSON.",
                        user_prompt=prompt,
                    )
                    raw_response = json.dumps(raw_obj)
                    normalized = normalize_evaluator_response(raw_response, f"Evaluator {label}")
                    log(f"      Attempt {attempt}: verdict={normalized.get('verdict', '???')}, schema_valid={normalized.get('schema_valid')}")
                    break
                except Exception as e:
                    log(f"      Attempt {attempt} failed: {e}")
                    if attempt == 2:
                        normalized = {"error": f"API call failed after 2 attempts: {e}"}

            evaluations[label] = normalized

            # Save raw evaluator output
            eval_file = claim_raw_dir / f"evaluator_{label}.json"
            with open(eval_file, "w", encoding="utf-8") as f:
                json.dump({
                    "evaluator": ev,
                    "raw_response": raw_response,
                    "normalized": normalized,
                    "meta": meta,
                }, f, indent=2, default=str)

        # Compute agreement
        pattern, majority_verdict = _compute_agreement_pattern(evaluations)
        gold_match = (majority_verdict == gold_label) if majority_verdict else False

        # Print per-claim summary
        print(f"  Agreement: {pattern}")
        for label in sorted(evaluations.keys()):
            ev = evaluations[label]
            v = ev.get("verdict", "ERROR")
            c = ev.get("confidence", "?")
            cs = ev.get("cited_sentences", [])
            print(f"    {label}: {v} (confidence={c}, cited={cs})")
        print(f"  Gold match: {gold_match}")

        result = {
            "claim_id": claim_data["claim_id"],
            "claim_text": claim_data["claim_text"],
            "gold_label": gold_label,
            "evaluations": evaluations,
            "agreement_pattern": pattern,
            "majority_verdict": majority_verdict,
            "gold_match": gold_match,
        }
        results.append(result)

    return results


def run_stage1(n_claims=5):
    """Run Stage 1 parallel evaluation on N claims."""
    log("=" * 70)
    log("  CAM SciFact — Stage 1: Parallel Evaluation")
    log("=" * 70)

    # Load dataset
    claims_by_split, corpus_lookup = load_scifact_dataset()
    val_split = claims_by_split.get("validation", [])

    # Select claims
    selected = _select_stage1_claims(val_split, corpus_lookup, n=n_claims)
    log(f"Selected {len(selected)} claims for Stage 1")
    for i, record in enumerate(selected):
        label = record["evidence_label"] or "NEI"
        log(f"  [{i+1}] Claim {record['id']} — {label}")

    # Run evaluation
    run_dir = CAM_ROOT / "03 SciFact" / "Runs" / "test_009"
    results = run_parallel_evaluation(selected, corpus_lookup, SCIFACT_EVALUATORS, run_dir)

    # Save results as JSONL
    results_file = run_dir / "results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"Results saved to {results_file}")

    # Compute and print agreement summary
    unanimous = sum(1 for r in results if r["agreement_pattern"].startswith("3-0"))
    majority = sum(1 for r in results if r["agreement_pattern"].startswith("2-1"))
    split = sum(1 for r in results if r["agreement_pattern"].startswith("1-1-1"))
    gold_matches = sum(1 for r in results if r["gold_match"])

    summary_lines = [
        "",
        "=" * 70,
        "  Agreement Summary",
        "=" * 70,
        f"  Total claims: {len(results)}",
        f"  Unanimous (3-0): {unanimous}",
        f"  Majority  (2-1): {majority}",
        f"  Full split (1-1-1): {split}",
        "",
        f"  Gold label match (majority verdict = gold): {gold_matches}/{len(results)}",
        "=" * 70,
    ]

    for line in summary_lines:
        print(line)

    # Save summary
    summary_file = run_dir / "agreement_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    log(f"Summary saved to {summary_file}")

    # Print per-claim detail
    print()
    print("  Per-Claim Results:")
    print("  " + "-" * 66)
    for r in results:
        verdicts = []
        for label in sorted(r["evaluations"].keys()):
            v = r["evaluations"][label].get("verdict", "ERR")
            verdicts.append(f"{label}={v}")
        match_marker = "OK" if r["gold_match"] else "X"
        print(f"  Claim {r['claim_id']:>4} (gold={r['gold_label']:>12}): {', '.join(verdicts)} -> {r['agreement_pattern']} [{match_marker}]")


# ============================================================
# Stage 2: Evidence Challenge (Step 010)
# ============================================================

# Challenger model config
SCIFACT_CHALLENGER = {
    "label": "challenger",
    "name": "openai:gpt-4.1",
    "provider": "openai",
    "model": "gpt-4.1",
}


def run_stage2_challenge(stage1_results=None, challenger_config=None, run_dir=None):
    """
    Stage 2: Run evidence challenge on all claims from Stage 1.

    For each claim, sends all evaluator outputs to the challenger
    for grounding analysis.

    Args:
        stage1_results: list of Stage 1 result dicts. If None, loads from test_009.
        challenger_config: dict with challenger model config. Defaults to SCIFACT_CHALLENGER.
        run_dir: path to save outputs. Defaults to test_010.
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.scifact.scifact_challenge import (
        format_evaluator_outputs_for_challenge,
        normalize_challenge_response,
        CHALLENGER_EXAMPLE_JSON,
    )

    find_and_load_env()

    if challenger_config is None:
        challenger_config = SCIFACT_CHALLENGER
    if run_dir is None:
        run_dir = CAM_ROOT / "03 SciFact" / "Runs" / "test_010"

    # Load Stage 1 results if not provided
    if stage1_results is None:
        stage1_file = CAM_ROOT / "03 SciFact" / "Runs" / "test_009" / "results.jsonl"
        if not stage1_file.exists():
            log("ERROR: Stage 1 results not found at test_009/results.jsonl")
            log("Run --stage1 first, then --stage2")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results from {stage1_file}")

    # We need the corpus to format abstracts
    claims_by_split, corpus_lookup = load_scifact_dataset()

    # Load challenger prompt template
    prompt_path = Path(__file__).parent / "prompts" / "challenger.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Set up challenger router
    target = ModelTarget(
        name=challenger_config["name"],
        provider=challenger_config["provider"],
        model=challenger_config["model"],
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=120.0,
    )
    router = ProviderRouter(targets=[target])

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM SciFact -- Stage 2: Evidence Challenge")
    log("=" * 70)

    challenge_results = []

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        # Look up the abstract for this claim from the corpus
        # We need to find the claim record to get the evidence doc
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )

        if formatted_abstract is None:
            log(f"  Skipping claim {claim_id} -- could not find abstract")
            continue

        # Format evaluator outputs
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)

        # Fill prompt template
        prompt = prompt_template.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{abstract_title}", abstract_title or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{evaluator_outputs}", evaluator_outputs)
        prompt = prompt.replace("{example_json}", CHALLENGER_EXAMPLE_JSON)

        print()
        print("=" * 70)
        print(f"  Challenge {idx+1}/{len(stage1_results)}: Claim {claim_id} (gold: {gold_label}, agreement: {agreement})")
        print("=" * 70)
        print(f"  Claim: {claim_text[:120]}...")
        print()

        # Call challenger model
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a grounding auditor for scientific claim verification. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_challenge_response(raw_response, f"Claim {claim_id}")
                log(f"    Attempt {attempt}: overall_grounding={normalized.get('overall_grounding_quality', '???')}, schema_valid={normalized.get('schema_valid')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}

        # Display results
        if "error" in normalized and "grounding_analysis" not in normalized:
            print(f"  CHALLENGE ERROR: {normalized['error']}")
        else:
            # Grounding per evaluator
            ga_list = normalized.get("grounding_analysis", [])
            for ga in ga_list:
                ev_label = ga.get("evaluator", "?")
                gq = ga.get("grounding_quality", "?")
                missing = ga.get("missing_key_sentences", [])
                irrelevant = ga.get("cited_irrelevant", [])
                print(f"    Evaluator {ev_label}: grounding={gq}, irrelevant_cited={irrelevant}, missing={missing}")

            # Inference flags
            flags = normalized.get("inference_flags", [])
            if flags:
                print(f"    Inference flags: {len(flags)}")
                for flag in flags:
                    print(f"      {flag.get('evaluator', '?')}: {flag.get('inference_type', '?')} ({flag.get('severity', '?')}) - {flag.get('description', '')[:80]}")
            else:
                print(f"    Inference flags: none")

            # Verdict analysis
            va = normalized.get("verdict_analysis", {})
            print(f"    Unanimous: {va.get('unanimous', '?')}, disagreement_source: {va.get('disagreement_source', '?')}")

            # Overall
            print(f"    Overall grounding quality: {normalized.get('overall_grounding_quality', '?')}")
            print(f"    Schema valid: {normalized.get('schema_valid', '?')}")

        # Save raw output
        raw_file = raw_dir / f"claim_{claim_id}_challenge.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "challenger": challenger_config,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        challenge_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "challenge": normalized,
        })

    # Save results as JSONL
    results_file = run_dir / "challenge_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in challenge_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"Results saved to {results_file}")

    # Print summary
    _print_challenge_summary(challenge_results, run_dir)

    return challenge_results


def _lookup_abstract_for_claim(claim_id, gold_label, claims_by_split, corpus_lookup):
    """
    Look up the abstract for a given claim from the dataset.

    Returns:
        (abstract_title, formatted_abstract) or (None, None) if not found.
    """
    val_split = claims_by_split.get("validation", [])
    for record in val_split:
        if record["id"] == claim_id:
            claim_data = extract_claim_data(record, corpus_lookup)
            # For NEI claims without evidence_doc_id, use first cited doc
            if claim_data["abstract_sentences"] is None:
                cited = record.get("cited_doc_ids", [])
                if cited and cited[0] in corpus_lookup:
                    corpus_entry = corpus_lookup[cited[0]]
                    claim_data["abstract_title"] = corpus_entry["title"]
                    claim_data["abstract_sentences"] = corpus_entry["abstract"]
            if claim_data["abstract_sentences"] is not None:
                formatted = format_abstract_for_prompt(claim_data["abstract_sentences"])
                return claim_data["abstract_title"], formatted
            break
    return None, None


def _print_challenge_summary(challenge_results, run_dir):
    """Print and save challenge summary."""
    summary_lines = [
        "",
        "=" * 70,
        "  Stage 2: Evidence Challenge Summary",
        "=" * 70,
        f"  Total claims challenged: {len(challenge_results)}",
    ]

    # Grounding quality distribution
    quality_counts = Counter()
    total_flags = 0
    flag_details = []
    for r in challenge_results:
        ch = r.get("challenge", {})
        oq = ch.get("overall_grounding_quality", "unknown")
        quality_counts[oq] += 1
        flags = ch.get("inference_flags", [])
        total_flags += len(flags)
        for flag in flags:
            flag_details.append({
                "claim_id": r["claim_id"],
                "evaluator": flag.get("evaluator", "?"),
                "type": flag.get("inference_type", "?"),
                "severity": flag.get("severity", "?"),
            })

    summary_lines.append("")
    summary_lines.append("  Overall Grounding Quality:")
    for quality in ["strong", "adequate", "weak", "mixed"]:
        count = quality_counts.get(quality, 0)
        summary_lines.append(f"    {quality}: {count}")

    summary_lines.append("")
    summary_lines.append(f"  Total inference flags: {total_flags}")
    if flag_details:
        for fd in flag_details:
            summary_lines.append(f"    Claim {fd['claim_id']}, Eval {fd['evaluator']}: {fd['type']} ({fd['severity']})")

    summary_lines.append("")

    # Per-claim detail
    summary_lines.append("  Per-Claim Results:")
    summary_lines.append("  " + "-" * 66)
    for r in challenge_results:
        ch = r.get("challenge", {})
        oq = ch.get("overall_grounding_quality", "?")
        va = ch.get("verdict_analysis", {})
        ds = va.get("disagreement_source", "?")
        n_flags = len(ch.get("inference_flags", []))
        ga_list = ch.get("grounding_analysis", [])
        gq_list = []
        for ga in ga_list:
            gq_list.append(f"{ga.get('evaluator', '?')}={ga.get('grounding_quality', '?')}")
        summary_lines.append(
            f"  Claim {r['claim_id']:>4} (gold={r['gold_label']:>12}): "
            f"overall={oq}, disagreement={ds}, flags={n_flags}, "
            f"per_eval=[{', '.join(gq_list)}]"
        )

    summary_lines.append("=" * 70)

    for line in summary_lines:
        print(line)

    # Save summary
    summary_file = run_dir / "challenge_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    log(f"Summary saved to {summary_file}")


# ============================================================
# Stage 3: Auditor (Step 011)
# ============================================================

# Auditor model config — Mistral Large via direct API
# (OpenRouter dry-run mode is ON by default in provider_router, so we
# call Mistral directly via their OpenAI-compatible endpoint instead.)
SCIFACT_AUDITOR = {
    "label": "auditor",
    "name": "mistral:mistral-large-latest",
    "provider": "mistral",
    "model": "mistral-large-latest",
}


def _call_mistral_json(system_prompt, user_prompt, model="mistral-large-latest", max_tokens=8192, temperature=0.0):
    """
    Call Mistral API directly via their OpenAI-compatible endpoint.
    Returns (parsed_json_dict, meta_dict).
    Mistral's API is OpenAI-compatible, so we use the openai SDK.
    """
    import os
    from openai import OpenAI
    from cam.core.json_extract import safe_json_extract

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY not set")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
        timeout=120.0,
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw_text = (resp.choices[0].message.content or "").strip()
    parsed = safe_json_extract(raw_text)

    meta = {
        "target": {"name": f"mistral:{model}", "provider": "mistral", "model": model},
        "usage": {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
        },
    }

    return parsed, meta


def run_stage3_auditor(stage1_results=None, stage2_results=None, auditor_config=None, run_dir=None):
    """
    Stage 3: Run auditor on all claims from Stages 1+2.

    Validates reasoning process: constraint compliance, coherence,
    cross-evaluator analysis, fragile agreement detection.

    Args:
        stage1_results: list of Stage 1 result dicts. If None, loads from test_009.
        stage2_results: list of Stage 2 result dicts. If None, loads from test_010.
        auditor_config: dict with auditor model config. Defaults to SCIFACT_AUDITOR.
        run_dir: path to save outputs. Defaults to test_011.
    """
    from cam.core.config import find_and_load_env
    from cam.adapters.scifact.scifact_challenge import format_evaluator_outputs_for_challenge
    from cam.adapters.scifact.scifact_auditor import (
        format_challenge_for_auditor,
        normalize_auditor_response,
        AUDITOR_EXAMPLE_JSON,
    )

    find_and_load_env()

    if auditor_config is None:
        auditor_config = SCIFACT_AUDITOR
    if run_dir is None:
        run_dir = CAM_ROOT / "03 SciFact" / "Runs" / "test_011"

    # Load Stage 1 results if not provided
    if stage1_results is None:
        stage1_file = CAM_ROOT / "03 SciFact" / "Runs" / "test_009" / "results.jsonl"
        if not stage1_file.exists():
            log("ERROR: Stage 1 results not found at test_009/results.jsonl")
            log("Run --stage1 first")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results from {stage1_file}")

    # Load Stage 2 results if not provided
    if stage2_results is None:
        stage2_file = CAM_ROOT / "03 SciFact" / "Runs" / "test_010" / "challenge_results.jsonl"
        if not stage2_file.exists():
            log("ERROR: Stage 2 results not found at test_010/challenge_results.jsonl")
            log("Run --stage2 first")
            return []
        stage2_results = []
        with open(stage2_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage2_results.append(json.loads(line))
        log(f"Loaded {len(stage2_results)} Stage 2 results from {stage2_file}")

    # Build lookup: claim_id -> stage2 challenge result
    s2_lookup = {}
    for r in stage2_results:
        s2_lookup[r["claim_id"]] = r.get("challenge", {})

    # We need the corpus to format abstracts
    claims_by_split, corpus_lookup = load_scifact_dataset()

    # Load auditor prompt template
    prompt_path = Path(__file__).parent / "prompts" / "auditor.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Auditor uses direct Mistral API call (not ProviderRouter)
    # because OpenRouter dry-run mode is ON by default in provider_router
    auditor_model = auditor_config["model"]

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM SciFact -- Stage 3: Auditor")
    log("=" * 70)

    auditor_results = []

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"  Skipping claim {claim_id} -- could not find abstract")
            continue

        # Format evaluator outputs (reuse challenge module's formatter)
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)

        # Format challenge results for auditor
        challenge_result = s2_lookup.get(claim_id, {})
        challenge_summary = format_challenge_for_auditor(challenge_result)

        # Fill prompt template
        prompt = prompt_template.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{abstract_title}", abstract_title or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{evaluator_outputs}", evaluator_outputs)
        prompt = prompt.replace("{challenge_summary}", challenge_summary)
        prompt = prompt.replace("{example_json}", AUDITOR_EXAMPLE_JSON)

        print()
        print("=" * 70)
        print(f"  Audit {idx+1}/{len(stage1_results)}: Claim {claim_id} (gold: {gold_label}, agreement: {agreement})")
        print("=" * 70)
        print(f"  Claim: {claim_text[:120]}...")
        print()

        # Call auditor model
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = _call_mistral_json(
                    system_prompt="You are a structural auditor for scientific claim verification. Respond only with valid JSON.",
                    user_prompt=prompt,
                    model=auditor_model,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_auditor_response(raw_response, f"Claim {claim_id}")
                log(f"    Attempt {attempt}: overall={normalized.get('overall_assessment', '???')}, schema_valid={normalized.get('schema_valid')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}

        # Display results
        if "error" in normalized and "overall_assessment" not in normalized:
            print(f"  AUDITOR ERROR: {normalized['error']}")
        else:
            # Constraint compliance
            cc = normalized.get("constraint_compliance", {})
            violations = cc.get("violations", [])
            print(f"    Constraints: cited={cc.get('all_cited_sentences', '?')}, scope={cc.get('all_assessed_scope', '?')}, assumptions={cc.get('all_stated_assumptions', '?')}")
            if violations:
                for v in violations:
                    print(f"      Violation: {v.get('evaluator', '?')} - {v.get('violation', '')[:80]} ({v.get('severity', '?')})")

            # Reasoning coherence
            rc_list = normalized.get("reasoning_coherence", [])
            for rc in rc_list:
                coherent = "OK" if rc.get("coherent") else "ISSUE"
                print(f"    Evaluator {rc.get('evaluator', '?')}: coherent={coherent} - {rc.get('notes', '')[:60]}")

            # Cross-evaluator
            cea = normalized.get("cross_evaluator_analysis", {})
            print(f"    Sentence overlap: {cea.get('sentence_overlap', '?')}, reasoning alignment: {cea.get('reasoning_alignment', '?')}")

            # Fragile agreement
            fa = normalized.get("fragile_agreement", {})
            fa_status = "FRAGILE" if fa.get("detected") else "ROBUST"
            print(f"    Agreement: {fa_status} - {fa.get('details', '')[:80]}")

            # Structural issues
            si = normalized.get("structural_issues", [])
            if si:
                for issue in si:
                    print(f"    Structural issue: {issue[:80]}")

            # Overall
            print(f"    Overall assessment: {normalized.get('overall_assessment', '?')}")
            print(f"    Schema valid: {normalized.get('schema_valid', '?')}")

        # Save raw output
        raw_file = raw_dir / f"claim_{claim_id}_auditor.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "auditor": auditor_config,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        auditor_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "audit": normalized,
        })

    # Save results as JSONL
    results_file = run_dir / "auditor_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in auditor_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"Results saved to {results_file}")

    # Print summary
    _print_auditor_summary(auditor_results, run_dir)

    return auditor_results


def _print_auditor_summary(auditor_results, run_dir):
    """Print and save auditor summary."""
    summary_lines = [
        "",
        "=" * 70,
        "  Stage 3: Auditor Summary",
        "=" * 70,
        f"  Total claims audited: {len(auditor_results)}",
    ]

    # Assessment distribution
    assessment_counts = Counter()
    fragile_count = 0
    total_violations = 0
    for r in auditor_results:
        audit = r.get("audit", {})
        assessment = audit.get("overall_assessment", "unknown")
        assessment_counts[assessment] += 1
        if audit.get("fragile_agreement", {}).get("detected"):
            fragile_count += 1
        violations = audit.get("constraint_compliance", {}).get("violations", [])
        total_violations += len(violations)

    summary_lines.append("")
    summary_lines.append("  Overall Assessments:")
    for assessment in ["PASS", "FLAG", "FAIL"]:
        count = assessment_counts.get(assessment, 0)
        summary_lines.append(f"    {assessment}: {count}")

    summary_lines.append("")
    summary_lines.append(f"  Fragile agreements detected: {fragile_count}")
    summary_lines.append(f"  Total constraint violations: {total_violations}")

    summary_lines.append("")

    # Per-claim detail
    summary_lines.append("  Per-Claim Results:")
    summary_lines.append("  " + "-" * 66)
    for r in auditor_results:
        audit = r.get("audit", {})
        assessment = audit.get("overall_assessment", "?")
        fa = audit.get("fragile_agreement", {})
        fragile = "FRAGILE" if fa.get("detected") else "robust"
        cea = audit.get("cross_evaluator_analysis", {})
        overlap = cea.get("sentence_overlap", "?")
        alignment = cea.get("reasoning_alignment", "?")
        violations = len(audit.get("constraint_compliance", {}).get("violations", []))
        summary_lines.append(
            f"  Claim {r['claim_id']:>4} (gold={r['gold_label']:>12}): "
            f"assessment={assessment}, agreement={fragile}, "
            f"overlap={overlap}, alignment={alignment}, violations={violations}"
        )

    summary_lines.append("=" * 70)

    for line in summary_lines:
        print(line)

    # Save summary
    summary_file = run_dir / "auditor_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    log(f"Summary saved to {summary_file}")


# ============================================================
# Stage 4: Fragility Detection (Step 012)
# ============================================================

def run_stage4_fragility(stage1_results=None, stage2_results=None, stage3_results=None, run_dir=None):
    """
    Stage 4: Compute fragility profile for each claim.
    No API calls -- pure computation on Stages 1-3 outputs.
    """
    from cam.adapters.scifact.scifact_fragility import compute_fragility_profile

    if run_dir is None:
        run_dir = CAM_ROOT / "03 SciFact" / "Runs" / "test_012"

    # Load Stage 1 results if not provided
    if stage1_results is None:
        stage1_file = CAM_ROOT / "03 SciFact" / "Runs" / "test_009" / "results.jsonl"
        if not stage1_file.exists():
            log("ERROR: Stage 1 results not found at test_009/results.jsonl")
            return []
        stage1_results = []
        with open(stage1_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage1_results.append(json.loads(line))
        log(f"Loaded {len(stage1_results)} Stage 1 results")

    # Load Stage 2 results if not provided
    if stage2_results is None:
        stage2_file = CAM_ROOT / "03 SciFact" / "Runs" / "test_010" / "challenge_results.jsonl"
        if not stage2_file.exists():
            log("ERROR: Stage 2 results not found at test_010/challenge_results.jsonl")
            return []
        stage2_results = []
        with open(stage2_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage2_results.append(json.loads(line))
        log(f"Loaded {len(stage2_results)} Stage 2 results")

    # Load Stage 3 results if not provided
    if stage3_results is None:
        stage3_file = CAM_ROOT / "03 SciFact" / "Runs" / "test_011" / "auditor_results.jsonl"
        if not stage3_file.exists():
            log("ERROR: Stage 3 results not found at test_011/auditor_results.jsonl")
            return []
        stage3_results = []
        with open(stage3_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stage3_results.append(json.loads(line))
        log(f"Loaded {len(stage3_results)} Stage 3 results")

    # Build lookups: claim_id -> stage result
    s2_lookup = {}
    for r in stage2_results:
        s2_lookup[r["claim_id"]] = r.get("challenge", {})
    s3_lookup = {}
    for r in stage3_results:
        s3_lookup[r["claim_id"]] = r.get("audit", {})

    log("=" * 70)
    log("  CAM SciFact -- Stage 4: Fragility Detection")
    log("=" * 70)

    # Create output directories
    run_dir.mkdir(parents=True, exist_ok=True)

    fragility_results = []
    rule_fire_log = []

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})

        # Compute fragility profile
        claim_data = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "gold_label": gold_label,
        }
        profile = compute_fragility_profile(
            claim_data, evaluations, challenge_result, auditor_result
        )

        # Display
        print()
        print("-" * 70)
        status = "FRAGILE" if profile["fragile"] else "CLEAN"
        print(f"  Claim {claim_id} (gold={gold_label}, agreement={agreement}): {status}")
        if profile["fired_rules"]:
            print(f"    Rules fired: {', '.join(profile['fired_rules'])}")
        if profile["max_cap"]:
            print(f"    Cap: {profile['max_cap']}")
        print(f"    Signals: {profile['signal_count']}")
        for sig in profile["signals"]:
            print(f"      [{sig['source']}] {sig['signal_id']} ({sig['severity']}): {sig['description'][:80]}")
        print(f"    Summary: {profile['summary']}")

        # Log rule fires
        for rule_id in profile["fired_rules"]:
            rule_fire_log.append(f"Claim {claim_id}: {rule_id}")

        fragility_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "fragility": profile,
        })

    # Save results as JSONL
    results_file = run_dir / "fragility_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in fragility_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"Results saved to {results_file}")

    # Save rule fire log
    fire_log_file = run_dir / "rule_fire_log.txt"
    with open(fire_log_file, "w", encoding="utf-8") as f:
        if rule_fire_log:
            f.write("\n".join(rule_fire_log))
        else:
            f.write("No rules fired.")
    log(f"Rule fire log saved to {fire_log_file}")

    # Print and save summary
    _print_fragility_summary(fragility_results, run_dir)

    return fragility_results


def _print_fragility_summary(fragility_results, run_dir):
    """Print and save fragility summary."""
    fragile_count = sum(1 for r in fragility_results if r["fragility"]["fragile"])
    clean_count = len(fragility_results) - fragile_count

    # Count rules fired
    rule_counts = Counter()
    for r in fragility_results:
        for rule_id in r["fragility"]["fired_rules"]:
            rule_counts[rule_id] += 1

    # Cap distribution
    cap_counts = Counter()
    for r in fragility_results:
        cap = r["fragility"]["max_cap"]
        cap_counts[cap or "none"] += 1

    summary_lines = [
        "",
        "=" * 70,
        "  Stage 4: Fragility Detection Summary",
        "=" * 70,
        f"  Total claims: {len(fragility_results)}",
        f"  Fragile: {fragile_count}",
        f"  Clean: {clean_count}",
        "",
        "  Rules Fired:",
    ]

    if rule_counts:
        for rule_id, count in sorted(rule_counts.items()):
            summary_lines.append(f"    {rule_id}: {count} claim(s)")
    else:
        summary_lines.append("    (none)")

    summary_lines.append("")
    summary_lines.append("  Cap Distribution:")
    for cap in ["L1", "L2", "L3", "none"]:
        count = cap_counts.get(cap, 0)
        if count > 0:
            summary_lines.append(f"    {cap}: {count}")

    summary_lines.append("")
    summary_lines.append("  Per-Claim Results:")
    summary_lines.append("  " + "-" * 66)
    for r in fragility_results:
        frag = r["fragility"]
        status = "FRAGILE" if frag["fragile"] else "CLEAN"
        cap = frag["max_cap"] or "none"
        rules = ", ".join(frag["fired_rules"]) if frag["fired_rules"] else "none"
        summary_lines.append(
            f"  Claim {r['claim_id']:>4} (gold={r['gold_label']:>12}): "
            f"{status:>7}, cap={cap}, rules=[{rules}], signals={frag['signal_count']}"
        )

    summary_lines.append("=" * 70)

    for line in summary_lines:
        print(line)

    # Save summary
    summary_file = run_dir / "fragility_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    log(f"Summary saved to {summary_file}")


# ============================================================
# Stage 5: Disposition (Step 013)
# ============================================================

def run_stage5_disposition(stage1_results=None, stage2_results=None, stage3_results=None,
                           stage4_results=None, run_dir=None):
    """
    Stage 5: Compute terminal state and commitment level.
    No API calls -- pure computation.
    Also computes post-hoc gold comparison and CAM metrics.
    """
    from cam.adapters.scifact.scifact_disposition import (
        compute_disposition, compare_to_gold, compute_cam_metrics,
        format_pipeline_summary, TERMINAL_STATES, COMMITMENT_LEVELS,
    )

    if run_dir is None:
        run_dir = CAM_ROOT / "03 SciFact" / "Runs" / "test_013"

    # Load all stage results
    if stage1_results is None:
        stage1_results = _load_jsonl_results(CAM_ROOT / "03 SciFact" / "Runs" / "test_009" / "results.jsonl", "Stage 1")
    if stage2_results is None:
        stage2_results = _load_jsonl_results(CAM_ROOT / "03 SciFact" / "Runs" / "test_010" / "challenge_results.jsonl", "Stage 2")
    if stage3_results is None:
        stage3_results = _load_jsonl_results(CAM_ROOT / "03 SciFact" / "Runs" / "test_011" / "auditor_results.jsonl", "Stage 3")
    if stage4_results is None:
        stage4_results = _load_jsonl_results(CAM_ROOT / "03 SciFact" / "Runs" / "test_012" / "fragility_results.jsonl", "Stage 4")

    if not stage1_results:
        log("ERROR: No Stage 1 results. Run --stage1 first.")
        return []

    # Build lookups
    s2_lookup = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}
    s3_lookup = {r["claim_id"]: r.get("audit", {}) for r in stage3_results}
    s4_lookup = {r["claim_id"]: r.get("fragility", {}) for r in stage4_results}

    log("=" * 70)
    log("  CAM SciFact -- Stage 5: Disposition")
    log("=" * 70)

    # Create output directory
    run_dir.mkdir(parents=True, exist_ok=True)

    disposition_results = []
    pipeline_traces = []

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})
        fragility_profile = s4_lookup.get(claim_id, {})

        # Compute disposition
        disposition = compute_disposition(
            evaluations, challenge_result, auditor_result, fragility_profile
        )

        # Post-hoc gold comparison
        gold_comparison = compare_to_gold(disposition, gold_label)

        # Print
        print()
        print("-" * 70)
        match_str = "MATCH" if gold_comparison["gold_match"] else "MISMATCH"
        if gold_comparison["withheld"]:
            match_str = "WITHHELD"
        print(f"  Claim {claim_id} (gold={gold_label})")
        print(f"    Terminal state: {disposition['terminal_state']}")
        print(f"    Commitment: {disposition['commitment_level']}")
        print(f"    Path: agreement={disposition['agreement_pattern']} -> base={disposition['base_level']} -> cap={disposition['fragility_cap']} -> final={disposition['final_level']}")
        if disposition["conditions"]:
            for cond in disposition["conditions"]:
                print(f"    Condition: {cond}")
        print(f"    Gold: {match_str}")

        # Build pipeline trace
        trace = format_pipeline_summary(
            claim_id, claim_text, gold_label, evaluations,
            challenge_result, auditor_result, fragility_profile,
            disposition, gold_comparison,
        )
        pipeline_traces.append(trace)

        disposition_results.append({
            "claim_id": claim_id,
            "claim_text": claim_text,
            "disposition": disposition,
            "gold_comparison": gold_comparison,
            "fragility": fragility_profile,
        })

    # Save disposition results
    results_file = run_dir / "disposition_results.jsonl"
    with open(results_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"Results saved to {results_file}")

    # Compute and print metrics
    metrics = compute_cam_metrics(disposition_results)
    _print_disposition_summary(disposition_results, metrics, run_dir)
    _print_metrics(metrics, run_dir)

    # Save pipeline summary
    pipeline_file = run_dir / "pipeline_summary.txt"
    with open(pipeline_file, "w", encoding="utf-8") as f:
        f.write("\n".join(pipeline_traces))
    log(f"Pipeline summary saved to {pipeline_file}")

    return disposition_results


def _load_jsonl_results(filepath, label):
    """Load JSONL results from a file."""
    filepath = Path(filepath)
    if not filepath.exists():
        log(f"WARNING: {label} results not found at {filepath}")
        return []
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    log(f"Loaded {len(results)} {label} results")
    return results


def _print_disposition_summary(disposition_results, metrics, run_dir):
    """Print and save disposition summary."""
    summary_lines = [
        "",
        "=" * 70,
        "  Stage 5: Disposition Summary",
        "=" * 70,
        f"  Total claims: {len(disposition_results)}",
        "",
    ]

    # Terminal state distribution
    state_counts = Counter()
    level_counts = Counter()
    for r in disposition_results:
        d = r["disposition"]
        state_counts[d["terminal_state"]] += 1
        level_counts[d["commitment_level"]] += 1

    summary_lines.append("  Terminal States:")
    for state in ["ASSERT_SUPPORT", "ASSERT_CONTRADICT", "ASSERT_NEI", "WITHHOLD_ASSERTION"]:
        count = state_counts.get(state, 0)
        if count > 0:
            summary_lines.append(f"    {state}: {count}")

    summary_lines.append("")
    summary_lines.append("  Commitment Levels:")
    for level in ["L0_FULL_ASSERT", "L1_QUALIFIED", "L2_CONDITIONAL", "L3_LOW_CONFIDENCE", "L4_WITHHOLD"]:
        count = level_counts.get(level, 0)
        if count > 0:
            summary_lines.append(f"    {level}: {count}")

    summary_lines.append("")
    summary_lines.append("  Per-Claim Dispositions:")
    summary_lines.append("  " + "-" * 66)
    for r in disposition_results:
        d = r["disposition"]
        gc = r["gold_comparison"]
        match = "MATCH" if gc["gold_match"] else ("WITHHELD" if gc["withheld"] else "MISMATCH")
        summary_lines.append(
            f"  Claim {r['claim_id']:>4}: {d['terminal_state']:>20} @ {d['commitment_level']:>18} "
            f"(base={d['base_level']}, cap={d['fragility_cap'] or '-'}, final={d['final_level']}) "
            f"[{match}]"
        )

    summary_lines.append("=" * 70)

    for line in summary_lines:
        print(line)

    summary_file = run_dir / "disposition_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    log(f"Summary saved to {summary_file}")


def _print_metrics(metrics, run_dir):
    """Print and save CAM metrics."""
    lines = [
        "",
        "=" * 70,
        "  CAM Metrics",
        "=" * 70,
        "",
        f"  Commitment-Conditioned Accuracy (CCA): {metrics['correct_assertions']}/{metrics['total_assertions']} = {metrics['cca']:.1%}",
        f"  Abstention Rate: {metrics['abstention_count']}/{metrics['total_claims']} = {metrics['abstention_rate']:.1%}",
    ]

    if metrics["abstention_value"] is not None:
        lines.append(f"  Abstention Value: {metrics['abstention_value']:.1%} of withheld claims would have been wrong")
    else:
        lines.append(f"  Abstention Value: N/A (no withholds)")

    if metrics["fragility_prediction"] is not None:
        lines.append(
            f"  Fragility Prediction: {metrics['fragile_with_issues']}/{metrics['fragile_count']} = "
            f"{metrics['fragility_prediction']:.1%} of fragile claims had issues"
        )
    else:
        lines.append(f"  Fragility Prediction: N/A (no fragile claims)")

    lines.append("")
    lines.append("  Interpretation:")
    lines.append(f"    CCA measures accuracy AMONG asserted claims (excludes withholds)")
    lines.append(f"    Higher CCA = system is right when it speaks")
    lines.append(f"    Abstention Value = were withholds good decisions?")
    lines.append(f"    Fragility Prediction = does marking fragile correlate with actual issues?")
    lines.append("=" * 70)

    for line in lines:
        print(line)

    metrics_file = run_dir / "metrics.txt"
    with open(metrics_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"Metrics saved to {metrics_file}")


def run_full_pipeline(n_claims=50, seed=1337, resume_dir=None):
    """
    Run all 5 stages sequentially in a single run directory.
    Fresh API calls for Stages 1-3 with resume logic.
    Stages 4-5 always recompute (pure computation).

    Args:
        n_claims: number of claims to sample
        seed: random seed for deterministic sampling
        resume_dir: path to existing run directory to resume, or None for new run
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.scifact.scifact_normalize import normalize_evaluator_response
    from cam.adapters.scifact.scifact_challenge import (
        format_evaluator_outputs_for_challenge,
        normalize_challenge_response,
        CHALLENGER_EXAMPLE_JSON,
    )
    from cam.adapters.scifact.scifact_auditor import (
        format_challenge_for_auditor,
        normalize_auditor_response,
        AUDITOR_EXAMPLE_JSON,
    )
    from cam.adapters.scifact.scifact_fragility import compute_fragility_profile
    from cam.adapters.scifact.scifact_disposition import (
        compute_disposition, compare_to_gold, compute_cam_metrics,
        format_pipeline_summary,
    )

    find_and_load_env()

    log("=" * 70)
    log("  CAM SciFact -- Full Production Pipeline")
    log(f"  Claims: {n_claims}  |  Seed: {seed}")
    log("=" * 70)

    # ---- Setup run directory ----
    runs_root = CAM_ROOT / "03 SciFact" / "Runs"
    if resume_dir:
        run_dir = Path(resume_dir)
        log(f"  Resuming run from: {run_dir}")
    else:
        run_num = get_next_run_number(runs_root)
        run_dir = runs_root / f"{run_num} SciFact Run"
        log(f"  Creating new run: {run_dir}")

    run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Error log
    error_log = []

    # ---- Save config ----
    config = {
        "run_type": "scifact_full_pipeline",
        "n_claims": n_claims,
        "seed": seed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "2.5.3",
        "models": {
            "evaluator_A": {"provider": "anthropic", "model": SCIFACT_EVALUATORS[0]["model"]},
            "evaluator_B": {"provider": "google", "model": SCIFACT_EVALUATORS[1]["model"]},
            "evaluator_C": {"provider": "xai", "model": SCIFACT_EVALUATORS[2]["model"]},
            "challenger": {"provider": SCIFACT_CHALLENGER["provider"], "model": SCIFACT_CHALLENGER["model"]},
            "auditor": {"provider": SCIFACT_AUDITOR["provider"], "model": SCIFACT_AUDITOR["model"]},
        },
        "stages": ["evaluation", "challenge", "auditor", "fragility", "disposition"],
    }
    config_file = run_dir / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    log(f"  Config saved to {config_file.name}")

    # ---- Load dataset ----
    claims_by_split, corpus_lookup = load_scifact_dataset()
    val_split = claims_by_split.get("validation", [])

    # ---- Select claims ----
    selected = _select_production_claims(val_split, corpus_lookup, n=n_claims, seed=seed)
    log(f"  Selected {len(selected)} claims with seed {seed}")

    # ---- Prepare claim data ----
    claim_data_list = []
    for record in selected:
        cd = extract_claim_data(record, corpus_lookup)
        # For NEI claims without evidence_doc_id, use first cited doc
        if cd["abstract_sentences"] is None:
            cited = record.get("cited_doc_ids", [])
            if cited and cited[0] in corpus_lookup:
                corpus_entry = corpus_lookup[cited[0]]
                cd["abstract_title"] = corpus_entry["title"]
                cd["abstract_sentences"] = corpus_entry["abstract"]
                cd["abstract_structured"] = corpus_entry["structured"]
                cd["evidence_doc_id"] = cited[0]
        if cd["abstract_sentences"] is None:
            log(f"  Skipping claim {cd['claim_id']} -- no abstract available")
            continue
        claim_data_list.append(cd)

    total_claims = len(claim_data_list)
    log(f"  {total_claims} claims with valid abstracts")

    # ---- Load templates ----
    prompt_dir = Path(__file__).parent / "prompts"
    eval_template = (prompt_dir / "evaluator.txt").read_text(encoding="utf-8")
    challenge_template = (prompt_dir / "challenger.txt").read_text(encoding="utf-8")
    auditor_template = (prompt_dir / "auditor.txt").read_text(encoding="utf-8")

    # ---- Setup routers ----
    eval_routers = {}
    for ev in SCIFACT_EVALUATORS:
        target = ModelTarget(
            name=ev["name"], provider=ev["provider"], model=ev["model"],
            priority=1, max_output_tokens=8192, temperature=0.0, timeout_sec=90.0,
        )
        eval_routers[ev["label"]] = ProviderRouter(targets=[target])

    challenge_target = ModelTarget(
        name=SCIFACT_CHALLENGER["name"], provider=SCIFACT_CHALLENGER["provider"],
        model=SCIFACT_CHALLENGER["model"], priority=1,
        max_output_tokens=8192, temperature=0.0, timeout_sec=120.0,
    )
    challenge_router = ProviderRouter(targets=[challenge_target])

    # Auditor uses direct Mistral API (_call_mistral_json)
    auditor_model = SCIFACT_AUDITOR["model"]

    # ==================================================================
    #  STAGE 1: Parallel Evaluation
    # ==================================================================
    print()
    log("=" * 70)
    log("  STAGE 1: Parallel Evaluation")
    log(f"  {total_claims} claims x {len(SCIFACT_EVALUATORS)} evaluators = {total_claims * len(SCIFACT_EVALUATORS)} API calls")
    log("=" * 70)

    stage1_results = []
    stage1_start = time.time()

    for claim_idx, cd in enumerate(claim_data_list):
        claim_id = cd["claim_id"]
        gold_label = cd["evidence_label"] or "NEI"
        formatted_abstract = format_abstract_for_prompt(cd["abstract_sentences"])

        # Fill prompt template
        prompt = eval_template.replace("{claim_text}", cd["claim_text"])
        prompt = prompt.replace("{abstract_title}", cd["abstract_title"] or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{example_json}", EVALUATOR_EXAMPLE_JSON)

        # Per-claim raw directory
        claim_raw_dir = raw_dir / f"claim_{claim_id}"
        claim_raw_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n  Stage 1: Evaluating claim {claim_idx+1}/{total_claims} (id={claim_id})...")

        evaluations = {}

        for ev in SCIFACT_EVALUATORS:
            label = ev["label"]
            eval_file = claim_raw_dir / f"evaluator_{label}.json"

            # Resume logic: skip if already completed
            if eval_file.exists():
                try:
                    with open(eval_file, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    normalized = saved.get("normalized", {})
                    if "error" not in normalized or "verdict" in normalized:
                        evaluations[label] = normalized
                        v = normalized.get("verdict", "?")
                        print(f"    Evaluator {label} ({ev['name']}): {v} [resumed]")
                        continue
                except Exception:
                    pass  # Fall through to re-call

            # Make API call
            router = eval_routers[label]
            raw_response = ""
            normalized = None
            meta = None

            for attempt in range(1, 3):
                try:
                    raw_obj, meta = router.call_json(
                        system_prompt="You are a scientific claim verification evaluator. Respond only with valid JSON.",
                        user_prompt=prompt,
                    )
                    raw_response = json.dumps(raw_obj)
                    normalized = normalize_evaluator_response(raw_response, f"Evaluator {label}")
                    v = normalized.get("verdict", "???")
                    valid = normalized.get("schema_valid", "?")
                    print(f"    Evaluator {label} ({ev['name']}): {v} (valid={valid}) {'OK' if valid else 'WARN'}")
                    break
                except Exception as e:
                    log(f"      Attempt {attempt} failed: {e}")
                    if attempt == 2:
                        normalized = {"error": f"API call failed after 2 attempts: {e}"}
                        error_log.append(f"Stage 1: Claim {claim_id}, Evaluator {label}: {e}")
                        print(f"    Evaluator {label} ({ev['name']}): FAILED")

            evaluations[label] = normalized

            # Save raw output
            with open(eval_file, "w", encoding="utf-8") as f:
                json.dump({
                    "evaluator": ev,
                    "raw_response": raw_response,
                    "normalized": normalized,
                    "meta": meta,
                }, f, indent=2, default=str)

        # Check if claim has enough valid evaluator responses
        valid_evals = sum(1 for e in evaluations.values() if "error" not in e or "verdict" in e)
        if valid_evals < 2:
            log(f"    SKIP: Claim {claim_id} has only {valid_evals} valid evaluator responses")
            error_log.append(f"Stage 1: Claim {claim_id} skipped — only {valid_evals}/3 evaluators succeeded")
            continue

        # Compute agreement
        pattern, majority_verdict = _compute_agreement_pattern(evaluations)
        gold_match = (majority_verdict == gold_label) if majority_verdict else False

        stage1_results.append({
            "claim_id": claim_id,
            "claim_text": cd["claim_text"],
            "gold_label": gold_label,
            "evaluations": evaluations,
            "agreement_pattern": pattern,
            "majority_verdict": majority_verdict,
            "gold_match": gold_match,
        })

    stage1_elapsed = time.time() - stage1_start
    log(f"\n  Stage 1 complete: {len(stage1_results)}/{total_claims} claims evaluated ({stage1_elapsed:.0f}s)")

    # Save Stage 1 results
    s1_file = run_dir / "stage1_results.jsonl"
    with open(s1_file, "w", encoding="utf-8") as f:
        for r in stage1_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ==================================================================
    #  STAGE 2: Evidence Challenge
    # ==================================================================
    print()
    log("=" * 70)
    log("  STAGE 2: Evidence Challenge")
    log(f"  {len(stage1_results)} claims x 1 challenger = {len(stage1_results)} API calls")
    log("=" * 70)

    stage2_results = []
    stage2_start = time.time()

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        claim_raw_dir = raw_dir / f"claim_{claim_id}"
        claim_raw_dir.mkdir(parents=True, exist_ok=True)
        challenge_file = claim_raw_dir / "challenge.json"

        print(f"\n  Stage 2: Challenging claim {idx+1}/{len(stage1_results)} (id={claim_id})...")

        # Resume logic
        if challenge_file.exists():
            try:
                with open(challenge_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                normalized = saved.get("normalized", {})
                if "error" not in normalized or "overall_grounding_quality" in normalized:
                    oq = normalized.get("overall_grounding_quality", "?")
                    print(f"    Challenge complete: grounding={oq} [resumed]")
                    stage2_results.append({
                        "claim_id": claim_id,
                        "gold_label": gold_label,
                        "agreement_pattern": agreement,
                        "challenge": normalized,
                    })
                    continue
            except Exception:
                pass

        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"    Skipping claim {claim_id} -- no abstract")
            error_log.append(f"Stage 2: Claim {claim_id} skipped — no abstract found")
            stage2_results.append({
                "claim_id": claim_id,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "challenge": {"error": "no abstract found", "overall_grounding_quality": "unknown"},
            })
            continue

        # Format inputs
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)
        prompt = challenge_template.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{abstract_title}", abstract_title or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{evaluator_outputs}", evaluator_outputs)
        prompt = prompt.replace("{example_json}", CHALLENGER_EXAMPLE_JSON)

        # Call challenger
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = challenge_router.call_json(
                    system_prompt="You are a grounding auditor for scientific claim verification. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_challenge_response(raw_response, f"Claim {claim_id}")
                oq = normalized.get("overall_grounding_quality", "???")
                print(f"    Challenge complete: grounding={oq} {'OK' if normalized.get('schema_valid') else 'WARN'}")
                break
            except Exception as e:
                log(f"      Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}", "overall_grounding_quality": "unknown"}
                    error_log.append(f"Stage 2: Claim {claim_id}: {e}")
                    print(f"    Challenge FAILED")

        # Save raw
        with open(challenge_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "challenger": SCIFACT_CHALLENGER,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        stage2_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "challenge": normalized,
        })

    stage2_elapsed = time.time() - stage2_start
    log(f"\n  Stage 2 complete: {len(stage2_results)}/{len(stage1_results)} claims challenged ({stage2_elapsed:.0f}s)")

    # Save Stage 2 results
    s2_file = run_dir / "stage2_results.jsonl"
    with open(s2_file, "w", encoding="utf-8") as f:
        for r in stage2_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ==================================================================
    #  STAGE 3: Auditor
    # ==================================================================
    print()
    log("=" * 70)
    log("  STAGE 3: Auditor")
    log(f"  {len(stage1_results)} claims x 1 auditor = {len(stage1_results)} API calls")
    log("=" * 70)

    # Build lookup for Stage 2 challenge results
    s2_lookup = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}

    stage3_results = []
    stage3_start = time.time()

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        claim_raw_dir = raw_dir / f"claim_{claim_id}"
        claim_raw_dir.mkdir(parents=True, exist_ok=True)
        auditor_file = claim_raw_dir / "auditor.json"

        print(f"\n  Stage 3: Auditing claim {idx+1}/{len(stage1_results)} (id={claim_id})...")

        # Resume logic
        if auditor_file.exists():
            try:
                with open(auditor_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                normalized = saved.get("normalized", {})
                if "error" not in normalized or "overall_assessment" in normalized:
                    oa = normalized.get("overall_assessment", "?")
                    print(f"    Audit complete: assessment={oa} [resumed]")
                    stage3_results.append({
                        "claim_id": claim_id,
                        "gold_label": gold_label,
                        "agreement_pattern": agreement,
                        "audit": normalized,
                    })
                    continue
            except Exception:
                pass

        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"    Skipping claim {claim_id} -- no abstract")
            error_log.append(f"Stage 3: Claim {claim_id} skipped — no abstract found")
            stage3_results.append({
                "claim_id": claim_id,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "audit": {"error": "no abstract found", "overall_assessment": "FLAG"},
            })
            continue

        # Format inputs
        evaluator_outputs = format_evaluator_outputs_for_challenge(evaluations)
        challenge_result = s2_lookup.get(claim_id, {})
        challenge_summary = format_challenge_for_auditor(challenge_result)

        prompt = auditor_template.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{abstract_title}", abstract_title or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{evaluator_outputs}", evaluator_outputs)
        prompt = prompt.replace("{challenge_summary}", challenge_summary)
        prompt = prompt.replace("{example_json}", AUDITOR_EXAMPLE_JSON)

        # Call auditor via direct Mistral API
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = _call_mistral_json(
                    system_prompt="You are a structural auditor for scientific claim verification. Respond only with valid JSON.",
                    user_prompt=prompt,
                    model=auditor_model,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_auditor_response(raw_response, f"Claim {claim_id}")
                oa = normalized.get("overall_assessment", "???")
                print(f"    Audit complete: assessment={oa} {'OK' if normalized.get('schema_valid') else 'WARN'}")
                break
            except Exception as e:
                log(f"      Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}", "overall_assessment": "FLAG"}
                    error_log.append(f"Stage 3: Claim {claim_id}: {e}")
                    print(f"    Audit FAILED (defaulting to FLAG)")

        # Save raw
        with open(auditor_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "auditor": SCIFACT_AUDITOR,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        stage3_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "audit": normalized,
        })

    stage3_elapsed = time.time() - stage3_start
    log(f"\n  Stage 3 complete: {len(stage3_results)}/{len(stage1_results)} claims audited ({stage3_elapsed:.0f}s)")

    # Save Stage 3 results
    s3_file = run_dir / "stage3_results.jsonl"
    with open(s3_file, "w", encoding="utf-8") as f:
        for r in stage3_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ==================================================================
    #  STAGE 4: Fragility Detection (no API calls)
    # ==================================================================
    print()
    log("=" * 70)
    log(f"  STAGE 4: Computing fragility... ({len(stage1_results)} claims, 0 API calls)")
    log("=" * 70)

    s2_lookup_4 = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}
    s3_lookup_4 = {r["claim_id"]: r.get("audit", {}) for r in stage3_results}

    stage4_results = []

    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        evaluations = s1_result["evaluations"]
        gold_label = s1_result["gold_label"]
        agreement = s1_result["agreement_pattern"]

        challenge_result = s2_lookup_4.get(claim_id, {})
        auditor_result = s3_lookup_4.get(claim_id, {})

        claim_data = {
            "claim_id": claim_id,
            "claim_text": s1_result["claim_text"],
            "gold_label": gold_label,
        }
        profile = compute_fragility_profile(
            claim_data, evaluations, challenge_result, auditor_result
        )

        stage4_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "fragility": profile,
        })

    fragile_count = sum(1 for r in stage4_results if r["fragility"]["fragile"])
    clean_count = len(stage4_results) - fragile_count
    log(f"  Stage 4 complete: {fragile_count} fragile, {clean_count} clean")

    # Save Stage 4 results
    s4_file = run_dir / "stage4_results.jsonl"
    with open(s4_file, "w", encoding="utf-8") as f:
        for r in stage4_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ==================================================================
    #  STAGE 5: Disposition + Metrics (no API calls)
    # ==================================================================
    print()
    log("=" * 70)
    log(f"  STAGE 5: Computing dispositions... ({len(stage1_results)} claims, 0 API calls)")
    log("=" * 70)

    s4_lookup = {r["claim_id"]: r.get("fragility", {}) for r in stage4_results}

    disposition_results = []
    pipeline_traces = []

    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]

        challenge_result = s2_lookup_4.get(claim_id, {})
        auditor_result = s3_lookup_4.get(claim_id, {})
        fragility_profile = s4_lookup.get(claim_id, {})

        disposition = compute_disposition(
            evaluations, challenge_result, auditor_result, fragility_profile
        )
        gold_comparison = compare_to_gold(disposition, gold_label)

        trace = format_pipeline_summary(
            claim_id, claim_text, gold_label, evaluations,
            challenge_result, auditor_result, fragility_profile,
            disposition, gold_comparison,
        )
        pipeline_traces.append(trace)

        disposition_results.append({
            "claim_id": claim_id,
            "claim_text": claim_text,
            "disposition": disposition,
            "gold_comparison": gold_comparison,
            "fragility": fragility_profile,
        })

    log("  Stage 5 complete.")

    # Save Stage 5 results
    s5_file = run_dir / "stage5_results.jsonl"
    with open(s5_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(json.dumps(r, default=str) + "\n")

    # Compute and display metrics
    metrics = compute_cam_metrics(disposition_results)

    # ==================================================================
    #  OUTPUT: Summaries, Metrics, Pipeline Traces
    # ==================================================================

    _print_disposition_summary(disposition_results, metrics, run_dir)
    _print_metrics(metrics, run_dir)

    # Pipeline summary
    pipeline_file = run_dir / "pipeline_summary.txt"
    with open(pipeline_file, "w", encoding="utf-8") as f:
        f.write("\n".join(pipeline_traces))
    log(f"  Pipeline summary saved to {pipeline_file.name}")

    # ==================================================================
    #  SECONDARY ANALYSIS
    # ==================================================================

    _print_secondary_analysis(disposition_results, stage1_results, stage4_results, run_dir)

    # ==================================================================
    #  ERROR LOG
    # ==================================================================

    error_file = run_dir / "error_log.txt"
    with open(error_file, "w", encoding="utf-8") as f:
        if error_log:
            f.write("\n".join(error_log))
        else:
            f.write("No errors.")
    if error_log:
        print()
        log(f"  ERRORS ({len(error_log)}):")
        for err in error_log:
            log(f"    {err}")
    else:
        log(f"  No errors during pipeline execution.")
    log(f"  Error log saved to {error_file.name}")

    # Final summary
    total_elapsed = time.time() - stage1_start  # Approximate total
    print()
    log("=" * 70)
    log(f"  PIPELINE COMPLETE")
    log(f"  Run directory: {run_dir}")
    log(f"  Claims processed: {len(disposition_results)}/{total_claims}")
    log(f"  Errors: {len(error_log)}")
    log(f"  Elapsed: ~{total_elapsed:.0f}s")
    log("=" * 70)


def _print_secondary_analysis(disposition_results, stage1_results, stage4_results, run_dir):
    """
    Print secondary analysis for the technical report:
    - Commitment level distribution
    - Rule fire rates
    - Agreement pattern distribution
    - Mismatch analysis
    """
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  SECONDARY ANALYSIS")
    lines.append("=" * 70)

    # 1. Commitment level distribution
    level_counts = Counter()
    for r in disposition_results:
        level_counts[r["disposition"]["commitment_level"]] += 1
    lines.append("")
    lines.append("  Commitment Level Distribution:")
    for level in ["L0_FULL_ASSERT", "L1_QUALIFIED", "L2_CONDITIONAL", "L3_LOW_CONFIDENCE", "L4_WITHHOLD"]:
        count = level_counts.get(level, 0)
        if count > 0:
            pct = 100 * count / len(disposition_results)
            lines.append(f"    {level}: {count} ({pct:.1f}%)")

    # 2. Rule fire rates
    rule_counts = Counter()
    for r in stage4_results:
        for rule_id in r["fragility"]["fired_rules"]:
            rule_counts[rule_id] += 1
    lines.append("")
    lines.append("  Rule Fire Rates:")
    if rule_counts:
        for rule_id, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
            pct = 100 * count / len(stage4_results)
            lines.append(f"    {rule_id}: {count} ({pct:.1f}%)")
    else:
        lines.append("    (no rules fired)")

    # 3. Agreement patterns
    agreement_counts = Counter()
    for r in stage1_results:
        pat = r["agreement_pattern"]
        if pat.startswith("3-0"):
            agreement_counts["3-0 (unanimous)"] += 1
        elif pat.startswith("2-1"):
            agreement_counts["2-1 (majority)"] += 1
        elif pat.startswith("1-1-1"):
            agreement_counts["1-1-1 (full split)"] += 1
        else:
            agreement_counts["other"] += 1
    lines.append("")
    lines.append("  Agreement Patterns:")
    for pat in ["3-0 (unanimous)", "2-1 (majority)", "1-1-1 (full split)", "other"]:
        count = agreement_counts.get(pat, 0)
        if count > 0:
            pct = 100 * count / len(stage1_results)
            lines.append(f"    {pat}: {count} ({pct:.1f}%)")

    # 4. Mismatch analysis
    mismatches = [r for r in disposition_results if not r["gold_comparison"]["gold_match"] and not r["gold_comparison"]["withheld"]]
    withholds = [r for r in disposition_results if r["gold_comparison"]["withheld"]]
    lines.append("")
    lines.append(f"  Mismatch Analysis ({len(mismatches)} mismatches, {len(withholds)} withholds):")
    for r in mismatches:
        d = r["disposition"]
        gc = r["gold_comparison"]
        frag = r["fragility"]
        status = "FRAGILE" if frag.get("fragile") else "clean"
        rules = ", ".join(frag.get("fired_rules", [])) if frag.get("fired_rules") else "none"
        lines.append(
            f"    Claim {r['claim_id']}: predicted={gc['predicted']}, gold={gc['gold_label']}, "
            f"level={d['commitment_level']}, {status}, rules=[{rules}]"
        )

    lines.append("=" * 70)

    for line in lines:
        print(line)

    # Save
    analysis_file = run_dir / "secondary_analysis.txt"
    with open(analysis_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"  Secondary analysis saved to {analysis_file.name}")


# ============================================================
# Verdict Elimination Enhancement (Step 014b)
# ============================================================

# Eliminator model config — different from all evaluators
SCIFACT_ELIMINATOR = {
    "label": "eliminator",
    "name": "openai:gpt-4.1",
    "provider": "openai",
    "model": "gpt-4.1",
}


def run_elimination_on_existing_run(source_run_dir):
    """
    Run verdict elimination on an existing run's Stage 1 data.
    Then recompute Stages 4-5 incorporating elimination results.
    Saves to a new run directory.

    Args:
        source_run_dir: path to the source run directory (e.g., "1 SciFact Run")
    """
    from cam.core.config import find_and_load_env
    from cam.core.provider_router import ProviderRouter, ModelTarget
    from cam.adapters.scifact.scifact_verdict_elimination import (
        format_evaluator_verdicts_brief,
        normalize_verdict_elimination_response,
        ELIMINATION_EXAMPLE_JSON,
    )
    from cam.adapters.scifact.scifact_fragility import compute_fragility_profile
    from cam.adapters.scifact.scifact_disposition import (
        compute_disposition, compute_disposition_with_elimination,
        compare_to_gold, compute_cam_metrics, format_pipeline_summary,
    )

    find_and_load_env()

    source_dir = Path(source_run_dir)
    if not source_dir.is_absolute():
        source_dir = CAM_ROOT / "03 SciFact" / "Runs" / source_run_dir

    log("=" * 70)
    log("  CAM SciFact — Verdict Elimination Enhancement")
    log(f"  Source run: {source_dir.name}")
    log("=" * 70)

    # ---- Load existing stage results ----
    stage1_results = _load_jsonl_results(source_dir / "stage1_results.jsonl", "Stage 1")
    stage2_results = _load_jsonl_results(source_dir / "stage2_results.jsonl", "Stage 2")
    stage3_results = _load_jsonl_results(source_dir / "stage3_results.jsonl", "Stage 3")

    if not stage1_results:
        log("ERROR: No Stage 1 results found in source run.")
        return

    # Build lookups
    s2_lookup = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}
    s3_lookup = {r["claim_id"]: r.get("audit", {}) for r in stage3_results}

    # ---- Create new run directory ----
    runs_root = CAM_ROOT / "03 SciFact" / "Runs"
    # Name it based on source: "1b SciFact Run Enhanced"
    source_name = source_dir.name
    # Extract the number prefix
    num_prefix = ""
    for ch in source_name:
        if ch.isdigit():
            num_prefix += ch
        else:
            break
    new_run_name = f"{num_prefix}b SciFact Run Enhanced"
    new_run_dir = runs_root / new_run_name
    new_run_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = new_run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log(f"  New run directory: {new_run_dir.name}")

    # Save config
    config = {
        "run_type": "scifact_elimination_enhancement",
        "source_run": source_dir.name,
        "n_claims": len(stage1_results),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "2.6.0",
        "models": {
            "eliminator": {"provider": SCIFACT_ELIMINATOR["provider"], "model": SCIFACT_ELIMINATOR["model"]},
        },
        "stages": ["elimination", "fragility_recompute", "disposition_recompute"],
        "note": "Stages 1-3 from source run. Elimination added, Stages 4-5 recomputed.",
    }
    with open(new_run_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    # ---- Load dataset for abstract lookup ----
    claims_by_split, corpus_lookup = load_scifact_dataset()

    # ---- Load elimination prompt template ----
    prompt_path = Path(__file__).parent / "prompts" / "verdict_elimination.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # ---- Setup elimination router ----
    target = ModelTarget(
        name=SCIFACT_ELIMINATOR["name"],
        provider=SCIFACT_ELIMINATOR["provider"],
        model=SCIFACT_ELIMINATOR["model"],
        priority=1,
        max_output_tokens=8192,
        temperature=0.0,
        timeout_sec=120.0,
    )
    router = ProviderRouter(targets=[target])

    # ==================================================================
    #  STAGE 1b: Verdict Elimination
    # ==================================================================
    print()
    log("=" * 70)
    log("  STAGE 1b: Verdict Elimination")
    log(f"  {len(stage1_results)} claims x 1 eliminator = {len(stage1_results)} API calls")
    log("=" * 70)

    elimination_results = []
    error_log = []
    elim_start = time.time()

    for idx, s1_result in enumerate(stage1_results):
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]
        agreement = s1_result["agreement_pattern"]

        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"  Skipping claim {claim_id} -- no abstract")
            error_log.append(f"Elimination: Claim {claim_id} skipped — no abstract found")
            elimination_results.append({
                "claim_id": claim_id,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "elimination": {"error": "no abstract found"},
            })
            continue

        # Format evaluator verdicts (brief — just verdicts + cited sentences)
        evaluator_verdicts = format_evaluator_verdicts_brief(evaluations)

        # Fill prompt template
        prompt = prompt_template.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{abstract_title}", abstract_title or "Unknown")
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{evaluator_verdicts}", evaluator_verdicts)
        prompt = prompt.replace("{example_json}", ELIMINATION_EXAMPLE_JSON)

        print(f"\n  Elimination {idx+1}/{len(stage1_results)}: Claim {claim_id} (gold: {gold_label}, agreement: {agreement})")

        # Save per-claim raw output
        claim_raw_dir = raw_dir / f"claim_{claim_id}"
        claim_raw_dir.mkdir(parents=True, exist_ok=True)
        elim_file = claim_raw_dir / "elimination.json"

        # Resume logic
        if elim_file.exists():
            try:
                with open(elim_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                normalized = saved.get("normalized", {})
                if "error" not in normalized or "recommended_verdict" in normalized:
                    rec = normalized.get("recommended_verdict", "?")
                    survivors = normalized.get("survivors", [])
                    print(f"    Elimination: recommended={rec}, survivors={survivors} [resumed]")
                    elimination_results.append({
                        "claim_id": claim_id,
                        "gold_label": gold_label,
                        "agreement_pattern": agreement,
                        "elimination": normalized,
                    })
                    continue
            except Exception:
                pass

        # Call eliminator model
        raw_response = ""
        normalized = None
        meta = None

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt="You are a verdict stress tester for scientific claim verification. Respond only with valid JSON.",
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                normalized = normalize_verdict_elimination_response(raw_response, f"Claim {claim_id}")
                rec = normalized.get("recommended_verdict", "???")
                survivors = normalized.get("survivors", [])
                killed_list = [
                    e.get("target_verdict") for e in normalized.get("eliminations", [])
                    if e.get("killed")
                ]
                print(f"    Elimination: recommended={rec}, survivors={survivors}, killed={killed_list}")
                if normalized.get("schema_error"):
                    print(f"    Schema warning: {normalized['schema_error'][:80]}")
                break
            except Exception as e:
                log(f"      Attempt {attempt} failed: {e}")
                if attempt == 2:
                    normalized = {"error": f"API call failed after 2 attempts: {e}"}
                    error_log.append(f"Elimination: Claim {claim_id}: {e}")
                    print(f"    Elimination FAILED")

        # Save raw output
        with open(elim_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "gold_label": gold_label,
                "agreement_pattern": agreement,
                "eliminator": SCIFACT_ELIMINATOR,
                "raw_response": raw_response,
                "normalized": normalized,
                "meta": meta,
            }, f, indent=2, default=str)

        elimination_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "elimination": normalized,
        })

    elim_elapsed = time.time() - elim_start
    log(f"\n  Stage 1b complete: {len(elimination_results)} claims ({elim_elapsed:.0f}s)")

    # Save elimination results
    elim_file = new_run_dir / "elimination_results.jsonl"
    with open(elim_file, "w", encoding="utf-8") as f:
        for r in elimination_results:
            f.write(json.dumps(r, default=str) + "\n")

    # Build elimination lookup
    elim_lookup = {r["claim_id"]: r.get("elimination", {}) for r in elimination_results}

    # ==================================================================
    #  STAGE 4 (recompute): Fragility with elimination signals
    # ==================================================================
    print()
    log("=" * 70)
    log(f"  STAGE 4 (recompute): Fragility ({len(stage1_results)} claims, 0 API calls)")
    log("=" * 70)

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

        # Add elimination-based fragility signals
        elim = elim_lookup.get(claim_id, {})
        if elim and "error" not in elim:
            # Check if any verdict was killed
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

        stage4_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "agreement_pattern": agreement,
            "fragility": profile,
        })

    fragile_count = sum(1 for r in stage4_results if r["fragility"]["fragile"])
    log(f"  Stage 4 recompute: {fragile_count} fragile, {len(stage4_results) - fragile_count} clean")

    # Save Stage 4 results
    s4_file = new_run_dir / "stage4_results.jsonl"
    with open(s4_file, "w", encoding="utf-8") as f:
        for r in stage4_results:
            f.write(json.dumps(r, default=str) + "\n")

    # ==================================================================
    #  STAGE 5 (recompute): Disposition with elimination
    # ==================================================================
    print()
    log("=" * 70)
    log(f"  STAGE 5 (recompute): Disposition with elimination ({len(stage1_results)} claims)")
    log("=" * 70)

    s4_lookup = {r["claim_id"]: r.get("fragility", {}) for r in stage4_results}

    disposition_results = []
    pipeline_traces = []

    for s1_result in stage1_results:
        claim_id = s1_result["claim_id"]
        claim_text = s1_result["claim_text"]
        gold_label = s1_result["gold_label"]
        evaluations = s1_result["evaluations"]

        challenge_result = s2_lookup.get(claim_id, {})
        auditor_result = s3_lookup.get(claim_id, {})
        fragility_profile = s4_lookup.get(claim_id, {})
        elimination_result = elim_lookup.get(claim_id, {})

        # Use elimination-aware disposition
        disposition = compute_disposition_with_elimination(
            evaluations, challenge_result, auditor_result,
            fragility_profile, elimination_result,
        )
        gold_comparison = compare_to_gold(disposition, gold_label)

        # Print
        match_str = "MATCH" if gold_comparison["gold_match"] else "MISMATCH"
        if gold_comparison["withheld"]:
            match_str = "WITHHELD"
        elim_action = disposition.get("elimination_action", "none")
        print(f"    Claim {claim_id}: {disposition['terminal_state']} @ {disposition['commitment_level']} [{match_str}] (elim={elim_action})")

        trace = format_pipeline_summary(
            claim_id, claim_text, gold_label, evaluations,
            challenge_result, auditor_result, fragility_profile,
            disposition, gold_comparison,
        )
        pipeline_traces.append(trace)

        disposition_results.append({
            "claim_id": claim_id,
            "claim_text": claim_text,
            "disposition": disposition,
            "gold_comparison": gold_comparison,
            "fragility": fragility_profile,
        })

    # Save Stage 5 results
    s5_file = new_run_dir / "stage5_results.jsonl"
    with open(s5_file, "w", encoding="utf-8") as f:
        for r in disposition_results:
            f.write(json.dumps(r, default=str) + "\n")

    # Compute and display metrics
    metrics = compute_cam_metrics(disposition_results)
    _print_disposition_summary(disposition_results, metrics, new_run_dir)
    _print_metrics(metrics, new_run_dir)

    # Save pipeline summary
    pipeline_file = new_run_dir / "pipeline_summary.txt"
    with open(pipeline_file, "w", encoding="utf-8") as f:
        f.write("\n".join(pipeline_traces))
    log(f"  Pipeline summary saved to {pipeline_file.name}")

    # ==================================================================
    #  BEFORE/AFTER COMPARISON
    # ==================================================================

    # Load original disposition results
    original_s5 = _load_jsonl_results(source_dir / "stage5_results.jsonl", "Original Stage 5")
    original_metrics_raw = None
    original_disposition_lookup = {}
    for r in original_s5:
        original_disposition_lookup[r["claim_id"]] = r

    # Compute original metrics
    from cam.adapters.scifact.scifact_disposition import compute_cam_metrics as _compute_metrics
    original_metrics = _compute_metrics(original_s5)

    _print_comparison(original_metrics, metrics, original_disposition_lookup,
                      disposition_results, new_run_dir)

    # Save elimination results summary
    _print_elimination_summary(elimination_results, new_run_dir)

    # Error log
    error_file = new_run_dir / "error_log.txt"
    with open(error_file, "w", encoding="utf-8") as f:
        if error_log:
            f.write("\n".join(error_log))
        else:
            f.write("No errors.")

    log("")
    log("=" * 70)
    log(f"  ELIMINATION ENHANCEMENT COMPLETE")
    log(f"  Source: {source_dir.name}")
    log(f"  Output: {new_run_dir.name}")
    log(f"  Claims: {len(disposition_results)}")
    log(f"  Errors: {len(error_log)}")
    log("=" * 70)


def _print_comparison(original_metrics, new_metrics, original_lookup, new_results, run_dir):
    """Print before/after comparison table and per-claim change log."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  BEFORE/AFTER COMPARISON")
    lines.append("=" * 70)
    lines.append("")

    # Compute additional original stats
    orig_wrong = sum(
        1 for r in original_lookup.values()
        if not r["gold_comparison"]["gold_match"] and not r["gold_comparison"]["withheld"]
    )
    new_wrong = sum(
        1 for r in new_results
        if not r["gold_comparison"]["gold_match"] and not r["gold_comparison"]["withheld"]
    )

    # Total accuracy
    orig_total_correct = sum(1 for r in original_lookup.values() if r["gold_comparison"]["gold_match"])
    new_total_correct = sum(1 for r in new_results if r["gold_comparison"]["gold_match"])
    orig_total = len(original_lookup)
    new_total = len(new_results)

    def _fmt_pct(val):
        return f"{val:.1%}" if val is not None else "N/A"

    def _fmt_delta(old, new):
        if old is None or new is None:
            return "N/A"
        diff = new - old
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff:.1%}"

    def _fmt_delta_int(old, new):
        diff = new - old
        sign = "+" if diff > 0 else ""
        return f"{sign}{diff}"

    header = f"{'METRIC':<30} {'BEFORE':>12} {'AFTER':>12} {'DELTA':>12}"
    lines.append(header)
    lines.append("-" * 70)

    lines.append(
        f"{'CCA':<30} {_fmt_pct(original_metrics['cca']):>12} "
        f"{_fmt_pct(new_metrics['cca']):>12} "
        f"{_fmt_delta(original_metrics['cca'], new_metrics['cca']):>12}"
    )
    lines.append(
        f"{'Abstention Rate':<30} {_fmt_pct(original_metrics['abstention_rate']):>12} "
        f"{_fmt_pct(new_metrics['abstention_rate']):>12} "
        f"{_fmt_delta(original_metrics['abstention_rate'], new_metrics['abstention_rate']):>12}"
    )
    orig_total_acc = orig_total_correct / orig_total if orig_total else 0
    new_total_acc = new_total_correct / new_total if new_total else 0
    lines.append(
        f"{'Total Accuracy':<30} {_fmt_pct(orig_total_acc):>12} "
        f"{_fmt_pct(new_total_acc):>12} "
        f"{_fmt_delta(orig_total_acc, new_total_acc):>12}"
    )
    lines.append(
        f"{'Wrong Assertions':<30} {orig_wrong:>12} "
        f"{new_wrong:>12} "
        f"{_fmt_delta_int(orig_wrong, new_wrong):>12}"
    )
    lines.append(
        f"{'Withholds':<30} {original_metrics['abstention_count']:>12} "
        f"{new_metrics['abstention_count']:>12} "
        f"{_fmt_delta_int(original_metrics['abstention_count'], new_metrics['abstention_count']):>12}"
    )

    # Per-commitment-level accuracy
    lines.append("")
    lines.append("  Accuracy by Commitment Level:")
    for level in ["L0_FULL_ASSERT", "L1_QUALIFIED", "L2_CONDITIONAL"]:
        # Original
        orig_level = [r for r in original_lookup.values() if r["disposition"]["commitment_level"] == level]
        orig_correct = sum(1 for r in orig_level if r["gold_comparison"]["gold_match"])
        orig_acc = f"{orig_correct}/{len(orig_level)}" if orig_level else "N/A"

        # New
        new_level = [r for r in new_results if r["disposition"]["commitment_level"] == level]
        new_correct = sum(1 for r in new_level if r["gold_comparison"]["gold_match"])
        new_acc = f"{new_correct}/{len(new_level)}" if new_level else "N/A"

        lines.append(f"    {level}: {orig_acc} -> {new_acc}")

    # Per-claim change log
    lines.append("")
    lines.append("=" * 70)
    lines.append("  PER-CLAIM CHANGE LOG")
    lines.append("=" * 70)
    lines.append("")

    changes = []
    for new_r in new_results:
        cid = new_r["claim_id"]
        orig_r = original_lookup.get(cid)
        if orig_r is None:
            continue

        orig_d = orig_r["disposition"]
        new_d = new_r["disposition"]

        orig_state = f"{orig_d['terminal_state']}@{orig_d['final_level']}"
        new_state = f"{new_d['terminal_state']}@{new_d['final_level']}"

        if orig_state != new_state:
            elim_action = new_d.get("elimination_action", "")
            # Check what type of kill happened
            elim_type = ""
            for cond in new_d.get("conditions", []):
                if "killed" in cond.lower():
                    elim_type = cond
                    break
            changes.append(f"  Claim {cid}: {orig_state} -> {new_state}")
            if elim_type:
                changes.append(f"    Reason: {elim_type}")

            # Show gold comparison change
            orig_match = "MATCH" if orig_r["gold_comparison"]["gold_match"] else (
                "WITHHELD" if orig_r["gold_comparison"]["withheld"] else "MISMATCH"
            )
            new_match = "MATCH" if new_r["gold_comparison"]["gold_match"] else (
                "WITHHELD" if new_r["gold_comparison"]["withheld"] else "MISMATCH"
            )
            if orig_match != new_match:
                changes.append(f"    Gold: {orig_match} -> {new_match}")
            changes.append("")

    if changes:
        lines.extend(changes)
    else:
        lines.append("  No disposition changes detected.")

    lines.append("=" * 70)

    for line in lines:
        print(line)

    # Save
    comparison_file = run_dir / "comparison.txt"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"  Comparison saved to {comparison_file.name}")


def _print_elimination_summary(elimination_results, run_dir):
    """Print and save elimination summary."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("  Verdict Elimination Summary")
    lines.append("=" * 70)
    lines.append(f"  Total claims: {len(elimination_results)}")
    lines.append("")

    # Count kills and survivors
    total_kills = 0
    kill_type_counts = Counter()
    claims_with_kills = 0

    for r in elimination_results:
        elim = r.get("elimination", {})
        if "error" in elim:
            continue

        eliminations = elim.get("eliminations", [])
        claim_has_kill = False
        for e in eliminations:
            if e.get("killed"):
                total_kills += 1
                kill_type_counts[e.get("elimination_type", "unknown")] += 1
                claim_has_kill = True
        if claim_has_kill:
            claims_with_kills += 1

    lines.append(f"  Claims with at least one kill: {claims_with_kills}")
    lines.append(f"  Total verdicts killed: {total_kills}")
    lines.append("")
    lines.append("  Kill Types:")
    for kill_type, count in sorted(kill_type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {kill_type}: {count}")

    lines.append("")
    lines.append("  Per-Claim Detail:")
    lines.append("  " + "-" * 66)
    for r in elimination_results:
        cid = r["claim_id"]
        gold = r["gold_label"]
        elim = r.get("elimination", {})

        if "error" in elim:
            lines.append(f"  Claim {cid:>4} (gold={gold:>12}): ERROR - {elim['error'][:60]}")
            continue

        rec = elim.get("recommended_verdict", "?")
        survivors = elim.get("survivors", [])
        confidence = elim.get("confidence_after_elimination", "?")
        killed = [e.get("target_verdict") for e in elim.get("eliminations", []) if e.get("killed")]

        lines.append(
            f"  Claim {cid:>4} (gold={gold:>12}): "
            f"rec={rec}, survivors={survivors}, killed={killed}, conf={confidence}"
        )

    lines.append("=" * 70)

    for line in lines:
        print(line)

    summary_file = run_dir / "elimination_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log(f"  Elimination summary saved to {summary_file.name}")


# ============================================================
# Dataset Stats (Step 007)
# ============================================================

def show_dataset_stats():
    """Show dataset statistics and sample claims."""
    print("=" * 70)
    print("  CAM SciFact Adapter — Dataset Inspection")
    print("=" * 70)
    print()

    print(f"CAM_ROOT: {CAM_ROOT}")
    print()

    claims_by_split, corpus_lookup = load_scifact_dataset()
    print()

    print("=" * 70)
    print("  Dataset Statistics")
    print("=" * 70)
    for split_name, claims in claims_by_split.items():
        print(f"  {split_name}: {len(claims)} claim-evidence pairs")
    print(f"  Corpus: {len(corpus_lookup)} documents")
    print()

    print("=" * 70)
    print("  Label Distribution — Validation Split")
    print("=" * 70)
    val_split = claims_by_split.get("validation", [])
    label_counts = Counter()
    no_evidence_count = 0
    unmatched_doc_ids = []

    for record in val_split:
        label = record["evidence_label"]
        doc_id = record["evidence_doc_id"]
        if label is None or label == "":
            no_evidence_count += 1
        else:
            label_counts[label] += 1
        if doc_id is not None and doc_id not in corpus_lookup:
            unmatched_doc_ids.append((record["id"], doc_id))

    total_labeled = sum(label_counts.values()) + no_evidence_count
    for label, count in sorted(label_counts.items()):
        pct = 100 * count / total_labeled if total_labeled else 0
        print(f"  {label}: {count} ({pct:.1f}%)")
    if no_evidence_count > 0:
        pct = 100 * no_evidence_count / total_labeled if total_labeled else 0
        print(f"  [no label / no evidence]: {no_evidence_count} ({pct:.1f}%)")
    print()

    if unmatched_doc_ids:
        print("=" * 70)
        print("  WARNING: Claims with evidence_doc_id not in corpus")
        print("=" * 70)
        for claim_id, doc_id in unmatched_doc_ids:
            print(f"  Claim {claim_id} -> doc_id {doc_id} NOT FOUND in corpus")
        print()
    else:
        print("  All evidence_doc_ids in validation split match corpus entries.")
        print()

    print("=" * 70)
    print("  Sample Claims — Validation Split (3 samples)")
    print("=" * 70)
    samples_shown = 0
    for record in val_split:
        if samples_shown >= 3:
            break
        claim_data = extract_claim_data(record, corpus_lookup)
        if claim_data["abstract_sentences"] is None:
            continue
        samples_shown += 1
        print(f"\n  --- Sample {samples_shown} ---")
        print(f"  Claim ID: {claim_data['claim_id']}")
        print(f"  Claim: {claim_data['claim_text']}")
        print(f"  Label: {claim_data['evidence_label']}")
        print(f"  Gold rationale sentences: {claim_data['evidence_sentences']}")
        print(f"  Evidence doc ID: {claim_data['evidence_doc_id']}")
        print(f"  Abstract title: {claim_data['abstract_title']}")
        print(f"  Abstract ({len(claim_data['abstract_sentences'])} sentences):")
        print()
        formatted = format_abstract_for_prompt(claim_data["abstract_sentences"])
        for line in formatted.split("\n"):
            print(f"    {line}")
        print()

    print("=" * 70)
    print("  Dataset inspection complete.")
    print("=" * 70)


# ============================================================
# Main — CLI Entry Point
# ============================================================

if __name__ == "__main__":
    # Parse common arguments
    def _parse_arg(name, default=None, cast=None):
        for i, arg in enumerate(sys.argv):
            if arg == name and i + 1 < len(sys.argv):
                val = sys.argv[i + 1]
                return cast(val) if cast else val
        return default

    n = _parse_arg("--n", default=5, cast=int)
    seed = _parse_arg("--seed", default=1337, cast=int)
    resume = _parse_arg("--resume")

    run_name = _parse_arg("--run")

    if "--analyze-withholds" in sys.argv:
        # Withhold analysis: audit triggers, remediate, recompute, summarize
        from cam.adapters.scifact.scifact_withhold_analysis import run_withhold_analysis
        source = run_name or "1b SciFact Run Enhanced"
        run_withhold_analysis(source_run_name=source)
    elif "--convict-rescore" in sys.argv:
        # Rescore conviction with updated signal logic (no API calls)
        from cam.adapters.scifact.scifact_conviction import run_conviction_rescore
        source = run_name or "1 SciFact Run"
        run_conviction_rescore(source_run_name=source)
    elif "--convict-fix" in sys.argv:
        # Conviction integration: retry Gemini + integrate signals into Stages 4-5
        from cam.adapters.scifact.scifact_conviction import run_conviction_integration
        source = run_name or "1 SciFact Run"
        run_conviction_integration(source_run_name=source)
    elif "--convict" in sys.argv:
        # Run conviction test (gold label adjudication) on mismatched claims
        from cam.adapters.scifact.scifact_conviction import run_conviction_test
        source = run_name or "1 SciFact Run"
        run_conviction_test(source_run_name=source)
    elif "--eliminate" in sys.argv:
        # Run verdict elimination on an existing run
        source = run_name or "1 SciFact Run"
        run_elimination_on_existing_run(source)
    elif "--full" in sys.argv:
        run_full_pipeline(n_claims=n, seed=seed, resume_dir=resume)
    elif "--stage5" in sys.argv:
        run_stage5_disposition()
    elif "--stage4" in sys.argv:
        run_stage4_fragility()
    elif "--stage3" in sys.argv:
        run_stage3_auditor()
    elif "--stage2" in sys.argv:
        run_stage2_challenge()
    elif "--stage1" in sys.argv:
        run_stage1(n_claims=n)
    elif "--test" in sys.argv:
        test_single_evaluator(n_claims=3)
    else:
        show_dataset_stats()
