#!/usr/bin/env python3
"""
GPQA CAM Adapter — Multiple Choice Question Evaluation Pipeline
CAM v2.5.3 — 9-stage pipeline with kill shots, resurrection, and commitment ladder

This adapter runs the full GPQA pipeline using the shared CAM core.
All GPQA-specific logic lives here; shared infrastructure lives in cam/core/.
"""

import os
import json
import time
import sys
import argparse
import hashlib
import random
import re
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Set, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import jsonschema
from datasets import load_dataset

# ============================================================
# CAM Core Imports
# ============================================================
from cam.core.config import CAM_ROOT, find_and_load_env, setup_openrouter
from cam.core.run_manager import RunContext, get_next_run_number
from cam.core.provider_router import ProviderRouter, ModelTarget
from cam.core.utilities import log, get_hash, add_audit_entry, get_prompt_hash, check_quota_error, normalize_choice_text
from cam.core.schema_validator import (
    load_schema, validate_round1_response, validate_round2_response,
    normalize_and_validate_round1, normalize_and_validate_round2c,
    normalize_and_validate_final_commit, normalize_and_validate_round3,
    normalize_and_validate_auditor, normalize_and_validate_grok,
    normalize_and_validate_r2d,
)
from cam.core.metrics import compute_grok_metrics, compute_round1_metrics, compute_round2_metrics

# ============================================================
# GPQA Adapter Module Imports (sibling modules in this directory)
# ============================================================
from cam.adapters.gpqa.normalize_responses import (
    normalize_round1, normalize_round2c, normalize_final_commit,
    normalize_round3, normalize_auditor, normalize_grok_analyzer,
    normalize_synthesizer, normalize_r2d, normalize_r2d_tests,
)
from cam.adapters.gpqa.cam_v2_functions import (
    process_round2c_v2, process_round2d_resurrection,
    process_final_commit_v2, aggregate_kill_shots,
    aggregate_survivor_conditions, determine_ladder_level,
)
from cam.adapters.gpqa.layered_disposition import (
    compute_layered_disposition, LayeredDisposition,
    DispositionLevel, LAYERED_DISPOSITION_SCHEMA,
)
from cam.adapters.gpqa.auditor_terminal_states import (
    AuditorTerminalState, AuditorDecision, FragilityIndicators,
    determine_terminal_state, perform_fragile_unanimity_check,
    map_legacy_disposition, count_hard_kills, get_authoritative_survivors,
)
from cam.adapters.gpqa.pipeline_guards import (
    apply_pipeline_guards, check_evaluator_schema_failure,
    check_json_extraction_failure, check_quota_abort,
    get_pipeline_guards_version, PIPELINE_GUARDS_STATUS,
)

# ============================================================
# Rule Library Imports
# ============================================================
from cam.rules.core_rules import (
    apply_core_rules,
    apply_rule_effects_to_aggregation as apply_core_rule_effects,
    RuleLibraryResult as CoreRuleResult,
    is_rule_library_enabled as is_core_rules_enabled,
    get_core_rule_library_version, CORE_RULES_STATUS,
)
from cam.rules.physics_rules import (
    apply_physics_rules, get_physics_rule_library_version, PHYSICS_RULES_STATUS,
)
from cam.rules.chemistry_rules import (
    apply_chemistry_rules,
    apply_rule_effects_to_aggregation as apply_chem_rule_effects,
    get_chemistry_rule_library_version, CHEMISTRY_RULES_STATUS,
)

# ============================================================
# Adapter Paths
# ============================================================
ADAPTER_DIR = Path(__file__).parent.resolve()
GPQA_ROOT = CAM_ROOT / "02 GPQA"

# Load environment (API keys)
find_and_load_env()
setup_openrouter()

# Availability flags — all True since we import directly (no try/except fallbacks)
V2_AVAILABLE = True
LAYERED_DISPOSITION_AVAILABLE = True
AUDITOR_TERMINAL_STATES_AVAILABLE = True
CORE_RULES_AVAILABLE = True
PHYSICS_RULES_AVAILABLE = True
CHEMISTRY_RULES_AVAILABLE = True
PIPELINE_GUARDS_AVAILABLE = True
NORMALIZATION_AVAILABLE = True
CAM_UTILITIES_AVAILABLE = True
CAM_VALIDATION_AVAILABLE = True
CAM_METRICS_AVAILABLE = True

# Rule Library Configuration — ALL PERMANENTLY ENABLED
ENABLE_CORE_RULES = True
ENABLE_PHYSICS_RULES = True
ENABLE_CHEMISTRY_RULES = True

# ============================================================
# Constants
# ============================================================
TEMPERATURE = 0.0
MAX_OUTPUT_TOKENS = 65536  # Maximum for Gemini Pro models
MAX_OUTPUT_TOKENS_CLAUDE = 64000  # Maximum for Claude models
MAX_OUTPUT_TOKENS_OPENAI = 16384  # Maximum for OpenAI models (can be higher, but 16k is safe)
MAX_RETRIES = 3  # Standard retries
SLEEP_BETWEEN_CALLS = 0.1

# Model configuration
# Round 1 Evaluators (blind, forced choice)
# A=Claude Opus 4.5, B=Gemini 3 Pro Preview, C=GPT-5.2, D=Grok 4.1 fast reasoning
EVALUATOR_MODELS = [
    ModelTarget(
        name="anthropic:claude-opus-4-5",
        provider="anthropic",
        model="claude-opus-4-5",
        priority=10,
        max_retries=MAX_RETRIES,
        max_output_tokens=MAX_OUTPUT_TOKENS_CLAUDE,
        temperature=TEMPERATURE,
        reasoning_effort="medium",  # Enable extended thinking for Claude
        timeout_sec=600.0,  # 10 minutes for extended thinking
    ),
    ModelTarget(
        name="google:gemini-3-pro-preview",
        provider="google",
        model="gemini-3-pro-preview",
        priority=10,
        max_retries=1,  # Single attempt - CAM handles higher-level retries
        max_output_tokens=MAX_OUTPUT_TOKENS,
        temperature=TEMPERATURE,
        timeout_sec=600.0,  # 10 minutes - match Claude timeout
    ),
    ModelTarget(
        name="openai:gpt-5.2",
        provider="openai",
        model="gpt-5.2",
        priority=10,
        max_retries=MAX_RETRIES,
        max_output_tokens=MAX_OUTPUT_TOKENS_OPENAI,
        temperature=TEMPERATURE,
        reasoning_effort="medium",  # Evaluators use medium reasoning effort
        timeout_sec=600.0,  # 10 minutes for GPT-5.2 with reasoning_effort
    ),
    ModelTarget(
        name="xai:grok-4-1-fast-reasoning",
        provider="xai",
        model="grok-4-1-fast-reasoning",
        priority=10,
        max_retries=MAX_RETRIES,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        temperature=TEMPERATURE,
        timeout_sec=1800.0,  # 30 minutes (increased for Grok API reliability)
    ),
]

# Evaluator names (dynamic list - supports 4 evaluators)
EVALUATORS = ["A", "B", "C", "D"]

# Reasoning Analyzer (Round 1.5): Grok 4.1 Fast Reasoning
ANALYZER_MODEL = ModelTarget(
    name="xai:grok-4-1-fast-reasoning",
    provider="xai",
    model="grok-4-1-fast-reasoning",
    priority=10,
    max_retries=MAX_RETRIES,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    temperature=TEMPERATURE,
    timeout_sec=1800.0,  # 30 minutes (same as Evaluator D)
)

# Synthesizer (Round 2): GPT-5.2 with high reasoning effort
SYNTHESIZER_MODEL = ModelTarget(
    name="openai:gpt-5.2-thinking",
    provider="openai",
    model="gpt-5.2",
    priority=10,
    max_retries=MAX_RETRIES,
    max_output_tokens=MAX_OUTPUT_TOKENS_OPENAI,
    temperature=TEMPERATURE,
    reasoning_effort="high",  # Synthesizer uses high reasoning effort (OpenAI only supports low/medium/high)
    timeout_sec=600.0,  # 10 minutes for GPT-5.2 with reasoning_effort
)

# Auditor: GPT-5.2 with high reasoning effort (optional, for complex cases)
AUDITOR_MODEL = ModelTarget(
    name="openai:gpt-5.2",
    provider="openai",
    model="gpt-5.2",
    priority=10,
    max_retries=MAX_RETRIES,
    max_output_tokens=MAX_OUTPUT_TOKENS_OPENAI,
    temperature=TEMPERATURE,
    reasoning_effort="high",  # Auditor uses high reasoning effort (OpenAI only supports low/medium/high)
    timeout_sec=600.0,  # 10 minutes for GPT-5.2 with reasoning_effort
)

# ============================================================
# Rule Library Application
# ============================================================
def apply_all_rule_libraries(
    kill_aggregation: dict,
    survivor_conditions: dict,
    question_text: str,
    question_domain: str,  # For logging only - NOT used for rule gating
    round2a_result: dict = None,
    round2c_result: dict = None,
    ladder_level: int = None,
    log_handle = None,
) -> Tuple[dict, List[dict]]:
    """
    Apply all enabled rule libraries to kill aggregation.
    
    CRITICAL POLICY: Loaded ≠ Fired
    ================================
    All rule libraries are LOADED for every question regardless of domain.
    Rules FIRE only when their semantic trigger conditions are met.
    
    This is intentional and mandatory:
    - A physics question may trigger chemistry rules if stereochemistry terms appear
    - A chemistry question may trigger physics rules if undefined symbols appear
    - Rule activation is SEMANTIC (content-based), not TAXONOMIC (label-based)
    
    Rule priority order:
    1. Pipeline Guards (execution safety) - applied separately
    2. Core Epistemic Rules (generic, all domains)
    3. Physics Rules (semantic triggers)
    4. Chemistry Rules (semantic triggers)
    
    When rules conflict, stricter epistemic outcome wins.
    Confidence may only be downgraded or capped, never increased.
    
    Returns:
        - Modified kill_aggregation with rules applied
        - List of rule results for audit trail
    """
    modified_agg = dict(kill_aggregation)  # Shallow copy
    all_rule_results = []
    
    # Domain is logged for diagnostics but NOT used for rule gating
    domain = (question_domain or "").lower().strip()
    
    # =========================================================================
    # CORE RULES - Generic epistemic guards (always loaded, semantic triggers)
    # =========================================================================
    if CORE_RULES_AVAILABLE and ENABLE_CORE_RULES:
        try:
            core_result = apply_core_rules(
                kill_aggregation=modified_agg,
                survivor_conditions=survivor_conditions,
                round2a_result=round2a_result,
            )
            if core_result.rules_triggered > 0:
                modified_agg = apply_core_rule_effects(modified_agg, core_result)
                if log_handle:
                    log(f"        [CORE-RULES] {core_result.rules_triggered}/{core_result.rules_evaluated} rules triggered", log_handle)
            all_rule_results.append({
                "library": "core",
                "version": get_core_rule_library_version() if CORE_RULES_AVAILABLE else "unknown",
                "status": CORE_RULES_STATUS if CORE_RULES_AVAILABLE else "UNAVAILABLE",
                "domain_label": domain,  # Logged for diagnostics only
                "rules_evaluated": core_result.rules_evaluated,
                "rules_triggered": core_result.rules_triggered,
                "downgraded_kills": core_result.downgraded_kills,
                "ladder_cap": core_result.ladder_cap,
                "fragility_markers": core_result.fragility_markers,
                "prohibitions": core_result.prohibitions,
            })
        except Exception as e:
            if log_handle:
                log(f"        [CORE-RULES] ERROR: {e}", log_handle)
    
    # =========================================================================
    # PHYSICS RULES - Loaded for ALL questions, fires on semantic triggers
    # Example triggers: symbol overloading (γ, μ, λ), regime violations
    # =========================================================================
    if PHYSICS_RULES_AVAILABLE and ENABLE_PHYSICS_RULES:
        try:
            phys_result = apply_physics_rules(
                kill_aggregation=modified_agg,
                survivor_conditions=survivor_conditions,
                question_text=question_text,
                round2a_result=round2a_result,
                ladder_level=ladder_level,
            )
            if phys_result.rules_triggered > 0:
                # Apply physics effects - merge downgraded kills
                existing_downgraded = modified_agg.get("rule_library_result", {}).get("downgraded_kills", {})
                for opt, reason in phys_result.downgraded_kills.items():
                    if opt not in existing_downgraded:
                        existing_downgraded[opt] = reason
                if log_handle:
                    log(f"        [PHYS-RULES] {phys_result.rules_triggered}/{phys_result.rules_evaluated} rules triggered", log_handle)
            all_rule_results.append({
                "library": "physics",
                "version": get_physics_rule_library_version() if PHYSICS_RULES_AVAILABLE else "unknown",
                "status": PHYSICS_RULES_STATUS if PHYSICS_RULES_AVAILABLE else "UNAVAILABLE",
                "domain_label": domain,  # Logged for diagnostics only
                "rules_evaluated": phys_result.rules_evaluated,
                "rules_triggered": phys_result.rules_triggered,
                "downgraded_kills": phys_result.downgraded_kills,
                "ladder_cap": phys_result.ladder_cap,
                "fragility_markers": phys_result.fragility_markers,
                "prohibitions": phys_result.prohibitions,
            })
        except Exception as e:
            if log_handle:
                log(f"        [PHYS-RULES] ERROR: {e}", log_handle)
    
    # =========================================================================
    # CHEMISTRY RULES - Loaded for ALL questions, fires on semantic triggers
    # Example triggers: stereochemistry (R/S, E/Z), NMR patterns, mechanisms
    # =========================================================================
    if CHEMISTRY_RULES_AVAILABLE and ENABLE_CHEMISTRY_RULES:
        try:
            chem_result = apply_chemistry_rules(
                kill_aggregation=modified_agg,
                survivor_conditions=survivor_conditions,
                question_text=question_text,
                round2a_result=round2a_result,
                round2c_result=round2c_result,
                ladder_level=ladder_level,
            )
            if chem_result.rules_triggered > 0:
                modified_agg = apply_chem_rule_effects(modified_agg, chem_result)
                if log_handle:
                    log(f"        [CHEM-RULES] {chem_result.rules_triggered}/{chem_result.rules_evaluated} rules triggered", log_handle)
            all_rule_results.append({
                "library": "chemistry",
                "version": get_chemistry_rule_library_version() if CHEMISTRY_RULES_AVAILABLE else "unknown",
                "status": CHEMISTRY_RULES_STATUS if CHEMISTRY_RULES_AVAILABLE else "UNAVAILABLE",
                "domain_label": domain,  # Logged for diagnostics only
                "rules_evaluated": chem_result.rules_evaluated,
                "rules_triggered": chem_result.rules_triggered,
                "downgraded_kills": chem_result.downgraded_kills,
                "ladder_cap": chem_result.ladder_cap,
                "fragility_markers": chem_result.fragility_markers,
                "prohibitions": chem_result.prohibitions,
            })
        except Exception as e:
            if log_handle:
                log(f"        [CHEM-RULES] ERROR: {e}", log_handle)
    
    return modified_agg, all_rule_results


# ============================================================
# Helper Functions (log, get_hash, add_audit_entry, get_prompt_hash, check_quota_error
# are now imported from cam_utilities.py - see FUNCTION ASSIGNMENTS section above)
# ============================================================

# ============================================================
# Dataset Loading
# ============================================================
def load_gpqa_dataset(split: str = "train", allow_split_fallback: bool = True, log_handle=None):
    """
    Load GPQA dataset from Hugging Face.
    Primary: Idavidrein/gpqa (gated)
    Fallback: casimiir/gpqa
    
    Returns: (dataset, dataset_info_dict)
    where dataset_info_dict = {
        "dataset_name": str,
        "requested_split": str,
        "actual_split": str,
        "split_fallback_used": bool,
    }
    """
    log(f"Loading GPQA dataset (split: {split})...", log_handle)
    
    dataset_info = {
        "dataset_name": None,
        "requested_split": split,
        "actual_split": split,
        "split_fallback_used": False,
    }
    
    # Try primary first
    try:
        dataset = load_dataset("Idavidrein/gpqa", split=split)
        log(f"  Loaded from Idavidrein/gpqa (split: {split})", log_handle)
        dataset_info["dataset_name"] = "Idavidrein/gpqa"
        return dataset, dataset_info
    except Exception as e:
        log(f"  Primary dataset failed: {e}", log_handle)
        log("  Trying fallback: casimiir/gpqa", log_handle)
        try:
            # Check available splits in fallback
            fallback_info = load_dataset("casimiir/gpqa", split=None)
            available_splits = list(fallback_info.keys())
            log(f"  Fallback dataset has splits: {available_splits}", log_handle)
            
            # Use requested split if available
            if split in available_splits:
                dataset = fallback_info[split]
                log(f"  Loaded from casimiir/gpqa (split: {split})", log_handle)
                dataset_info["dataset_name"] = "casimiir/gpqa"
                return dataset, dataset_info
            elif available_splits:
                # Split not available - check if fallback is allowed
                if not allow_split_fallback:
                    log(f"  ERROR: Requested split '{split}' not available and --allow_split_fallback not set", log_handle)
                    log(f"  Available splits: {available_splits}", log_handle)
                    raise ValueError(f"Requested split '{split}' not available. Use --allow_split_fallback to use an alternative.")
                
                # Use first available split as fallback
                fallback_split = available_splits[0]
                log(f"  WARNING: Requested split '{split}' not available, using '{fallback_split}'", log_handle)
                dataset = fallback_info[fallback_split]
                log(f"  Loaded from casimiir/gpqa (split: {fallback_split})", log_handle)
                
                dataset_info["dataset_name"] = "casimiir/gpqa"
                dataset_info["actual_split"] = fallback_split
                dataset_info["split_fallback_used"] = True
                return dataset, dataset_info
            else:
                raise ValueError("No splits available in fallback dataset")
        except Exception as e2:
            log(f"ERROR: Both dataset sources failed", log_handle)
            log(f"  Primary error: {e}", log_handle)
            log(f"  Fallback error: {e2}", log_handle)
            log(f"\n  To access the primary dataset (Idavidrein/gpqa):", log_handle)
            log(f"    1. Visit https://huggingface.co/datasets/Idavidrein/gpqa", log_handle)
            log(f"    2. Accept the terms and authenticate", log_handle)
            log(f"    3. Run: huggingface-cli login", log_handle)
            sys.exit(1)

def extract_question_data(record: dict) -> dict:
    """
    Extract question data from dataset record.
    Returns: {question_id, question, choices, gold_answer, subject}
    """
    # Handle different dataset formats
    question_id = record.get("id") or record.get("question_id") or str(record.get("_id", ""))
    question = record.get("question") or record.get("Question", "")
    
    # Extract choices (A-D)
    choices = {}
    if "choices" in record:
        choices_raw = record["choices"]
        if isinstance(choices_raw, dict):
            choices = choices_raw
        elif isinstance(choices_raw, list):
            for i, choice in enumerate(choices_raw):
                choices[chr(65 + i)] = choice  # A, B, C, D
    elif "Answers" in record:
        # Alternative format
        answers = record["Answers"]
        if isinstance(answers, list):
            for i, ans in enumerate(answers):
                choices[chr(65 + i)] = ans
    
    # Extract gold answer
    gold_answer = record.get("correct_answer") or record.get("Correct Answer") or record.get("answer")
    if gold_answer and gold_answer not in ["A", "B", "C", "D"]:
        # Convert numeric or other formats
        if isinstance(gold_answer, int):
            gold_answer = chr(65 + gold_answer)  # 0->A, 1->B, etc.
        elif gold_answer in choices:
            # Find index
            for key, val in choices.items():
                if val == gold_answer:
                    gold_answer = key
                    break
    
    # Extract subject if available
    subject = record.get("subject") or record.get("Subject") or record.get("domain")
    
    # Build choice maps for referent anchoring (letter mapping drift fix)
    choice_map, reverse_choice_map = build_choice_maps(choices)
    
    return {
        "question_id": str(question_id),
        "question": question,
        "choices": choices,
        "choice_map": choice_map,
        "reverse_choice_map": reverse_choice_map,
        "gold_answer": gold_answer,
        "subject": subject,
    }

# ============================================================
# Letter Mapping Drift Fix - Referent Anchoring
# (normalize_choice_text is now imported from cam_utilities.py)
# ============================================================

def build_choice_maps(choices: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Build choice_map and reverse_choice_map for a question.
    
    Returns:
        choice_map: {"A": "<choice text>", "B": "...", ...}
        reverse_choice_map: {normalized_text: "A"|"B"|"C"|"D"}
    """
    choice_map = dict(choices)  # Already in {letter: text} format
    reverse_choice_map = {}
    
    for letter, text in choices.items():
        normalized = normalize_choice_text(text)
        if normalized:
            reverse_choice_map[normalized] = letter
            # Also store shorter versions for fuzzy matching
            # e.g., "Mutant 2" -> normalize to "2" as well
            words = normalized.split()
            if len(words) >= 1:
                # Store last word/number as additional key
                reverse_choice_map[words[-1]] = letter
    
    return choice_map, reverse_choice_map


def resolve_text_to_letter(text: str, reverse_choice_map: Dict[str, str], choice_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve a choice text to its canonical letter using the reverse map.
    Uses fuzzy matching if exact match fails.
    
    PRIORITY ORDER:
    1. Check for letter prefix (e.g., "B: some text" -> B)
    2. Exact normalized match
    3. Substring match
    4. Case-insensitive content match
    
    Returns: letter (A/B/C/D) or None if unresolvable
    """
    if not text:
        return None
    
    # PRIORITY 1: Check for letter prefix like "A:", "B:", "C:", "D:"
    # This handles GPT-5.2's tendency to prefix text with the letter
    text_stripped = text.strip()
    letter_prefix_match = re.match(r'^([A-Da-d])\s*[:\-\.\)]\s*', text_stripped)
    if letter_prefix_match:
        prefix_letter = letter_prefix_match.group(1).upper()
        if prefix_letter in choice_map:
            # Verify the rest of the text matches this choice
            rest_of_text = text_stripped[letter_prefix_match.end():].strip()
            choice_text = choice_map[prefix_letter]
            # Check if rest_of_text is a prefix of the choice text
            if rest_of_text and (rest_of_text.lower()[:30] in choice_text.lower()[:50] or 
                                  choice_text.lower()[:30] in rest_of_text.lower()[:50]):
                return prefix_letter
            # Even if text doesn't match perfectly, trust the explicit prefix
            # (model said "B: ..." so it meant B)
            return prefix_letter
    
    normalized = normalize_choice_text(text)
    
    # Exact match
    if normalized in reverse_choice_map:
        return reverse_choice_map[normalized]
    
    # Try substring match - find if normalized text is contained in any choice
    for choice_normalized, letter in reverse_choice_map.items():
        if normalized in choice_normalized or choice_normalized in normalized:
            return letter
    
    # Try matching against original choice text (case-insensitive)
    text_lower = text.lower().strip()
    for letter, choice_text in choice_map.items():
        if text_lower in choice_text.lower() or choice_text.lower() in text_lower:
            return letter
    
    return None


def validate_mapping_consistency(
    final_choice_letter: str,
    final_choice_text: str,
    choice_map: Dict[str, str],
    reverse_choice_map: Dict[str, str]
) -> Tuple[str, bool, Optional[str]]:
    """
    Validate that final_choice_letter matches the resolved letter from final_choice_text.
    
    Returns:
        (corrected_letter, drift_detected, drift_reason)
    """
    if not final_choice_text:
        # No text provided - can't validate, trust the letter
        return final_choice_letter, False, None
    
    resolved_letter = resolve_text_to_letter(final_choice_text, reverse_choice_map, choice_map)
    
    if resolved_letter is None:
        # Couldn't resolve text - trust the letter but flag it
        return final_choice_letter, False, f"unresolvable_text: {final_choice_text[:50]}"
    
    if resolved_letter != final_choice_letter:
        # DRIFT DETECTED - correct it
        return resolved_letter, True, f"letter_text_mismatch: letter={final_choice_letter}, text='{final_choice_text[:50]}' resolves to {resolved_letter}"
    
    return final_choice_letter, False, None


def apply_round1_unanimity_rail(
    round1_results: dict,
    final_commit_results: dict,
    choice_map: Dict[str, str],
    reverse_choice_map: Dict[str, str],
    evaluators: list
) -> Tuple[dict, bool, Optional[str]]:
    """
    If Round 1 was unanimous, ensure Final Commit preserves the same referent.
    
    If all evaluators' final_choice_text resolves to the same choice as Round 1,
    force the letter to match Round 1's letter.
    
    Returns:
        (updated_final_commit_results, rail_triggered, rail_reason)
    """
    r1_pattern = round1_results.get("agreement_pattern", "")
    
    # Only apply if Round 1 was unanimous
    if not r1_pattern.startswith("unanimous"):
        return final_commit_results, False, None
    
    r1_unanimous_letter = round1_results.get("unanimous_choice")
    if not r1_unanimous_letter or r1_unanimous_letter == "ABSTAIN":
        return final_commit_results, False, None
    
    r1_unanimous_text = choice_map.get(r1_unanimous_letter, "")
    r1_normalized = normalize_choice_text(r1_unanimous_text)
    
    # Check all final commit evaluators
    all_match_r1_referent = True
    mismatched_letters = []
    
    for eval_name in evaluators:
        fc_result = final_commit_results.get(f"evaluator_{eval_name}")
        if not fc_result:
            continue
        
        fc_letter = fc_result.get("final_choice")
        fc_text = fc_result.get("final_choice_text", "")
        
        if fc_letter == "ABSTAIN" or fc_letter is None:
            continue
        
        # Check if the referent matches R1
        fc_normalized = normalize_choice_text(fc_text) if fc_text else ""
        
        # Also check if fc_text resolves to R1's letter
        resolved = resolve_text_to_letter(fc_text, reverse_choice_map, choice_map) if fc_text else fc_letter
        
        if resolved and resolved != r1_unanimous_letter:
            all_match_r1_referent = False
            break
        
        if fc_letter != r1_unanimous_letter:
            mismatched_letters.append((eval_name, fc_letter))
    
    # If all referents match R1 but letters drifted, correct them
    if all_match_r1_referent and mismatched_letters:
        for eval_name, wrong_letter in mismatched_letters:
            fc_result = final_commit_results.get(f"evaluator_{eval_name}")
            if fc_result:
                fc_result["final_choice_letter_raw"] = wrong_letter
                fc_result["final_choice"] = r1_unanimous_letter
                fc_result["mapping_drift_detected"] = True
                fc_result["mapping_drift_reason"] = f"round1_unanimity_rail: R1={r1_unanimous_letter}, FC={wrong_letter}, referent preserved"
        
        final_commit_results["round1_unanimity_rail_triggered"] = True
        final_commit_results["round1_unanimity_rail_reason"] = f"Corrected {len(mismatched_letters)} evaluator(s) to match R1 letter {r1_unanimous_letter}"
        # SPEC: Add fragility marker and prohibit ladder improvement for drift
        final_commit_results["letter_mapping_drift_detected"] = True
        final_commit_results["ladder_improvement_prohibited"] = True  # Per CAM_Pipeline_Guards_v1
        
        return final_commit_results, True, f"LETTER_MAPPING_DRIFT: Corrected letters to {r1_unanimous_letter} (R1 unanimous referent preserved)"
    
    return final_commit_results, False, None


# ============================================================
# A) Cheap Eliminations from Round 1 (Always runs)
# ============================================================

def compute_eliminations_from_round1(
    round1_results: dict,
    choices: Dict[str, str],
    evaluators: List[str] = None
) -> dict:
    """
    Compute eliminations from Round 1 evaluator outputs based on why_others_wrong.
    
    An option is eliminated if ALL evaluators explicitly reject it.
    
    Returns:
    {
        "eliminated": {"A": "reason", "B": "reason"},
        "survivors": ["C", "D"],
        "confidence": "HIGH" | "MED" | "LOW",
        "elimination_votes": {"A": 4, "B": 3, ...},  # How many evals rejected each
        "evaluator_count": 4
    }
    """
    if evaluators is None:
        evaluators = ["A", "B", "C", "D"]
    
    all_options = ["A", "B", "C", "D"]
    
    # Track rejections per option
    rejection_reasons = {opt: [] for opt in all_options}
    rejection_counts = {opt: 0 for opt in all_options}
    valid_evaluator_count = 0
    
    for eval_name in evaluators:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if not eval_result:
            continue
        
        valid_evaluator_count += 1
        final_choice = eval_result.get("final_choice")
        why_others_wrong = eval_result.get("why_others_wrong", {})
        
        for opt in all_options:
            if opt == final_choice:
                # This is their chosen option, not rejected
                continue
            
            rejection = why_others_wrong.get(opt, "")
            if rejection and rejection.lower() != "chosen" and len(rejection) > 5:
                # This evaluator explicitly rejected this option
                rejection_counts[opt] += 1
                # Keep first 100 chars of reason
                reason_preview = rejection[:100] + "..." if len(rejection) > 100 else rejection
                rejection_reasons[opt].append(reason_preview)
    
    # Option is eliminated if ALL valid evaluators rejected it
    eliminated = {}
    survivors = []
    
    for opt in all_options:
        if valid_evaluator_count > 0 and rejection_counts[opt] == valid_evaluator_count:
            # Unanimous rejection
            # Use most common reason (first one for simplicity)
            reason = rejection_reasons[opt][0] if rejection_reasons[opt] else "All evaluators rejected this option"
            eliminated[opt] = reason
        else:
            survivors.append(opt)
    
    # Compute confidence based on consistency
    if valid_evaluator_count == 0:
        confidence = "LOW"
    elif len(eliminated) >= 3:
        confidence = "HIGH"  # Eliminated 3 of 4 options
    elif len(eliminated) >= 2:
        confidence = "MED"   # Eliminated 2 options
    else:
        confidence = "LOW"   # 0-1 eliminations
    
    return {
        "eliminated": eliminated,
        "survivors": survivors,
        "confidence": confidence,
        "elimination_votes": rejection_counts,
        "evaluator_count": valid_evaluator_count,
    }


def validate_choice_mapping_round1(
    eval_result: dict,
    choices: Dict[str, str],
    choice_map: Dict[str, str],
    reverse_choice_map: Dict[str, str]
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that final_choice matches final_choice_text in Round 1.
    
    Returns: (is_valid, error_message, corrected_letter)
    """
    final_choice = eval_result.get("final_choice")
    final_choice_text = eval_result.get("final_choice_text", "")
    
    if not final_choice:
        return False, "missing final_choice", None
    
    if final_choice not in ["A", "B", "C", "D"]:
        return False, f"invalid final_choice: {final_choice}", None
    
    if not final_choice_text:
        # No text provided - can't validate, but don't fail
        return True, None, None
    
    # Check if final_choice_text matches choices[final_choice]
    expected_text = choice_map.get(final_choice, "")
    
    # Normalize both for comparison
    normalized_expected = normalize_choice_text(expected_text)
    normalized_actual = normalize_choice_text(final_choice_text)
    
    # Check exact match first
    if normalized_expected == normalized_actual:
        return True, None, None
    
    # Check if the text resolves to a different letter
    resolved_letter = resolve_text_to_letter(final_choice_text, reverse_choice_map, choice_map)
    
    if resolved_letter and resolved_letter != final_choice:
        return False, f"mapping_mismatch: final_choice={final_choice} but final_choice_text='{final_choice_text[:50]}...' matches {resolved_letter}", resolved_letter
    
    # Text doesn't match but also doesn't resolve to different letter
    # This could be a paraphrase - allow with warning
    return True, None, None


# ============================================================
# B) Kill-Shot Gate (Conditional logic)
# ============================================================

def should_run_killshot(
    round1_results: dict,
    cheap_elimination: dict,
    grok_analysis: Optional[dict] = None,
    evaluators: List[str] = None
) -> Tuple[bool, List[str]]:
    """
    Determine if kill-shot round should run.
    
    Returns: (should_run, reasons)
    
    Triggers if ANY:
    1. Not unanimous (split)
    2. Unanimous but proofs diverge (different proof_attempt types)
    3. Unanimous but proof quality missing (schema failures)
    4. Unanimous but grok says INCOMPATIBLE
    5. Unanimous but mapping validation failed
    """
    if evaluators is None:
        evaluators = ["A", "B", "C", "D"]
    
    reasons = []
    
    # Check 1: Not unanimous
    pattern = round1_results.get("agreement_pattern", "")
    if not pattern.startswith("unanimous"):
        reasons.append("split_decision")
    
    # Check 2: Proofs diverge
    proof_types = set()
    for eval_name in evaluators:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if not eval_result:
            continue
        
        final_choice = eval_result.get("final_choice")
        proof_attempt = eval_result.get("proof_attempt", {})
        
        # Get proof type for chosen option
        if final_choice and final_choice in proof_attempt:
            proof_type = proof_attempt[final_choice].get("type", "unknown")
            proof_types.add(proof_type)
    
    if len(proof_types) > 1:
        reasons.append(f"proof_type_divergence: {proof_types}")
    
    # Check 3: Proof quality issues
    for eval_name in evaluators:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if not eval_result:
            reasons.append(f"missing_evaluator_{eval_name}")
            continue
        
        if eval_result.get("_schema_validation_failed"):
            reasons.append(f"schema_failure_{eval_name}")
        
        if eval_result.get("_repair_applied"):
            reasons.append(f"repair_applied_{eval_name}")
    
    # Check 4: Grok incompatibility
    if grok_analysis:
        if grok_analysis.get("incompatibility_detected"):
            reasons.append("grok_incompatible")
        if grok_analysis.get("reasoning_relation") == "INCOMPATIBLE":
            reasons.append("grok_reasoning_incompatible")
    
    # Check 5: Mapping validation failures
    for eval_name in evaluators:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and eval_result.get("mapping_validation_error"):
            reasons.append(f"mapping_error_{eval_name}")
    
    # Check 6: Multiple survivors in cheap elimination
    if cheap_elimination.get("confidence") == "LOW":
        reasons.append("weak_elimination_confidence")
    
    should_run = len(reasons) > 0
    return should_run, reasons


# ============================================================
# Epistemic Conflict Gate (per spec: elimination only on conflict)
# ============================================================

def epistemic_conflict_exists(
    round1_results: dict,
    round2a_results: Optional[dict] = None,
    round3_results: Optional[dict] = None,
    grok_analysis: Optional[dict] = None,
    candidate_options: Optional[List[str]] = None,
) -> Tuple[bool, List[str]]:
    """
    Determine if there is genuine epistemic conflict requiring Round 2c.
    
    CRITICAL: Round 2c MUST run when candidate_set.size >= 2, regardless of R1 unanimity.
    
    Returns: (conflict_exists, reasons)
    
    Conflict exists if ANY of:
    1. Round 1 was NOT unanimous
    2. Candidate set has >= 2 options (MANDATORY - cannot be bypassed)
    3. Grok similarity is not HIGH (invalidates "epistemic unanimity")
    4. Round 2a representation was contested
    5. Round 3 stress test broke unanimity  
    6. Grok detected INCOMPATIBLE reasoning
    """
    reasons = []
    
    # Case 1: Non-unanimous initial reasoning
    pattern = round1_results.get("agreement_pattern", "")
    is_unanimous = pattern.startswith("unanimous")
    
    if not is_unanimous:
        reasons.append(f"non_unanimous_r1: {pattern}")
        return True, reasons
    
    # Case 2: Multiple candidates after pruning (MANDATORY - per spec)
    # Round 2c MUST run whenever there is more than one candidate
    if candidate_options and len(candidate_options) >= 2:
        reasons.append(f"multiple_candidates: {len(candidate_options)}")
        return True, reasons
    
    # Case 3: Grok similarity not HIGH invalidates epistemic unanimity
    if grok_analysis:
        similarity = grok_analysis.get("similarity_level", "UNKNOWN")
        if similarity != "HIGH":
            reasons.append(f"grok_similarity_not_high: {similarity}")
            return True, reasons
        
        # Also check for incompatible reasoning
        relation = grok_analysis.get("reasoning_relation", "UNKNOWN")
        if relation == "INCOMPATIBLE":
            reasons.append("grok_incompatible_reasoning")
            return True, reasons
        if grok_analysis.get("incompatibility_detected", False):
            reasons.append("grok_incompatibility_detected")
            return True, reasons
    
    # Case 4: Representation disagreement (R2a)
    if round2a_results:
        if round2a_results.get("representation_contested", False):
            reasons.append("representation_contested")
            return True, reasons
        # Also check if any evaluator changed their answer
        if round2a_results.get("any_answer_changed", False):
            reasons.append("r2a_answer_changed")
            return True, reasons
    
    # Case 5: Stress test breaks unanimity (R3)
    if round3_results:
        if round3_results.get("stress_test_failed", False):
            reasons.append("stress_test_failed")
            return True, reasons
        if round3_results.get("any_can_break", False):
            reasons.append("stress_test_can_break")
            return True, reasons
    
    # No conflict - unanimous, single candidate, and uncontested
    return False, []

# ============================================================
# Schema Validation (load_schema, validate_round1_response, validate_round2_response,
# and all normalize_and_validate_* functions are now imported from cam_validation.py
# - see FUNCTION ASSIGNMENTS section above)
# ============================================================

# ============================================================
# Agreement Pattern Computation
# ============================================================
# Minimum valid evaluators required for agreement computation
MIN_VALID_EVALUATORS = 3


def compute_agreement_pattern(choices: Dict[str, Optional[str]], parse_ok: Dict[str, bool]) -> Tuple[str, Optional[str], Optional[str], int, dict]:
    """
    Compute agreement pattern from evaluator choices with parse_ok tracking.
    ONLY uses evaluators with parse_ok=True. Does NOT require all evaluators to be valid.
    
    Returns: (pattern, majority_choice, unanimous_choice, majority_size, metadata)
    
    metadata includes:
    - valid_evaluator_count: number of valid evaluators
    - total_evaluator_count: total evaluators configured
    - included_evaluators: list of evaluators included in computation
    - excluded_evaluators: list of evaluators excluded
    - pipeline_bug: True if < MIN_VALID_EVALUATORS
    
    Patterns:
    - INSUFFICIENT_EVALUATORS: < MIN_VALID_EVALUATORS valid (pipeline_bug=True)
    - unanimous_N: N/N valid and same answer (N = valid count)
    - split_X_Y: valid evaluators split X-Y
    """
    # Collect valid evaluators and their choices
    valid_evaluators = []
    excluded_evaluators = []
    valid_choices = []
    valid_choices_by_eval = {}
    
    for eval_name in EVALUATORS:
        if parse_ok.get(eval_name, False):
            choice = choices.get(eval_name)
            if choice is not None and choice != "ABSTAIN":
                valid_evaluators.append(eval_name)
                valid_choices.append(choice)
                valid_choices_by_eval[eval_name] = choice
            else:
                excluded_evaluators.append(eval_name)
        else:
            excluded_evaluators.append(eval_name)
    
    num_total = len(EVALUATORS)
    num_valid = len(valid_evaluators)
    
    metadata = {
        "valid_evaluator_count": num_valid,
        "total_evaluator_count": num_total,
        "included_evaluators": valid_evaluators,
        "excluded_evaluators": excluded_evaluators,
        "pipeline_bug": False,
    }
    
    # Check minimum threshold
    if num_valid < MIN_VALID_EVALUATORS:
        metadata["pipeline_bug"] = True
        return "INSUFFICIENT_EVALUATORS", None, None, 0, metadata
    
    # Compute pattern from VALID evaluators only
    choice_counts = Counter(valid_choices)
    unique_choices = len(choice_counts)
    counts_list = sorted(choice_counts.values(), reverse=True)
    
    if unique_choices == 1:
        # Unanimous among valid evaluators
        unanimous = list(choice_counts.keys())[0]
        # Pattern reflects actual valid count: unanimous_3, unanimous_4, etc.
        pattern = f"unanimous_{num_valid}"
        return pattern, unanimous, unanimous, num_valid, metadata
    
    # Not unanimous - compute split pattern
    majority = choice_counts.most_common(1)[0][0]
    majority_size = choice_counts.most_common(1)[0][1]
    
    # Build pattern string from counts (e.g., "split_3_1", "split_2_1")
    pattern = "split_" + "_".join(str(c) for c in counts_list)
    
    # Determine if there's a clear majority
    if counts_list[0] > counts_list[1]:
        return pattern, majority, None, majority_size, metadata
    else:
        # Tie (e.g., 2_2) - no clear majority
        return pattern, None, None, counts_list[0], metadata

# ============================================================
# check_quota_error is now imported from cam_utilities.py - see FUNCTION ASSIGNMENTS section above

# ============================================================
# Helper: Call Evaluator with Effort Override
# ============================================================
def call_evaluator_with_override(
    eval_name: str,
    router: ProviderRouter,
    system_prompt: str,
    user_prompt: str,
    log_handle,
    reasoning_effort_override: Optional[str] = None,
    timeout_override_sec: Optional[float] = None,
    audit_trail: list = None,
    round_name: str = None,
    role: str = "Evaluator"
) -> Tuple[Optional[dict], Optional[dict], dict]:
    """
    Call an evaluator with optional reasoning_effort and timeout overrides.
    Returns: (result_dict, meta_dict, call_settings_dict)
    """
    # Get the original target from router
    original_target = router.targets[0] if router.targets else None
    if not original_target:
        log(f"      [ERROR] No target available for {eval_name}", log_handle)
        return None, None, {}
    
    # Create override target if needed
    if reasoning_effort_override or timeout_override_sec:
        override_target = ModelTarget(
            name=original_target.name,
            provider=original_target.provider,
            model=original_target.model,
            priority=original_target.priority,
            enabled=original_target.enabled,
            max_retries=original_target.max_retries,
            timeout_sec=timeout_override_sec if timeout_override_sec else original_target.timeout_sec,
            max_output_tokens=original_target.max_output_tokens,
            temperature=original_target.temperature,
            reasoning_effort=reasoning_effort_override if reasoning_effort_override else original_target.reasoning_effort,
        )
        # Create temporary router with override target
        override_router = ProviderRouter([override_target])
    else:
        override_router = router
        override_target = original_target
    
    # Determine effort level for logging
    effort_level = override_target.reasoning_effort or "auto"
    timeout_used = override_target.timeout_sec
    
    call_settings = {
        "effort": effort_level,
        "timeout_sec": timeout_used,
        "model_name": override_target.name,
        "provider": override_target.provider,
        "model": override_target.model,
    }
    
    # Attribution logging (neutral, observational only)
    log(f"      [CALL] {eval_name} - model={override_target.name}, provider={override_target.provider}, effort={effort_level}, timeout={timeout_used}s", log_handle)
    
    try:
        result, meta = override_router.call_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_validate_fn=None,
        )
        
        # Record audit entry if requested
        if audit_trail is not None and round_name is not None:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry(audit_trail, round_name, override_target.name, role, user_prompt, raw_out)
            
        return result, meta, call_settings
    except Exception as e:
        error_msg = str(e)
        check_quota_error(error_msg, f"Evaluator {eval_name}", log_handle)
        log(f"      [ERROR] {eval_name} call failed: {e}", log_handle)
        return None, None, call_settings

# ============================================================
# Round 1 Processing
# ============================================================
def process_round1(
    question_data: dict,
    evaluator_routers: Dict[str, ProviderRouter],
    round1_prompt: str,
    round1_schema: dict,
    allow_abstain: bool,
    log_handle,
    audit_trail: list = None
) -> dict:
    """Process a single question through Round 1 (independent evaluation)."""
    question_id = question_data["question_id"]
    question = question_data["question"]
    choices = question_data["choices"]
    gold_answer = question_data["gold_answer"]
    
    log(f"  Processing Round 1 for question {question_id}", log_handle)
    
    # Build prompt with question and choices (new format)
    full_prompt = round1_prompt.format(
        question=question,
        choice_a=choices.get("A", ""),
        choice_b=choices.get("B", ""),
        choice_c=choices.get("C", ""),
        choice_d=choices.get("D", "")
    )
    
    round1_results = {
        "evaluator_A": None,
        "evaluator_B": None,
        "evaluator_C": None,
        "evaluator_D": None,
        "parse_ok_A": False,
        "parse_ok_B": False,
        "parse_ok_C": False,
        "parse_ok_D": False,
        "correct_A": False,
        "correct_B": False,
        "correct_C": False,
        "correct_D": False,
    }
    
    # Helper function to process a single evaluator (for parallel execution)
    def process_single_evaluator(eval_name: str, router: ProviderRouter) -> Tuple[str, Optional[dict], dict, bool]:
        """Process a single evaluator call. Returns (eval_name, response_json, call_settings, parse_ok)."""
        log(f"    Calling Evaluator {eval_name}...", log_handle)
        
        # Attribution logging (before call)
        target = router.targets[0] if router.targets else None
        if target:
            log(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, provider={target.provider}, round=R1, timeout_sec={target.timeout_sec}", log_handle)
        
        start_time = time.time()
        try:
            # Round 1: use default medium effort (no override)
            result, meta, call_settings = call_evaluator_with_override(
                eval_name, router, "", full_prompt, log_handle, None, None
            )
            
            # Record audit entry if requested
            if audit_trail is not None:
                raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                add_audit_entry(audit_trail, "Round 1", call_settings.get("model_name", eval_name), "Evaluator", full_prompt, raw_out)
            
            if result is None:
                # Check if the failure was due to quota (error might be in meta or exception message)
                if meta:
                    error_info = meta.get("error", "") or meta.get("raw", "") or str(meta)
                    # Also check for all_targets_failed format
                    if "all_targets_failed" in str(meta):
                        error_info = str(meta)
                    check_quota_error(error_info, f"Evaluator {eval_name}", log_handle)
                return (eval_name, None, call_settings, False)
            
            elapsed = time.time() - start_time
            log(f"      [TIMING] Evaluator {eval_name}: {elapsed:.1f}s", log_handle)
            
            # Parse JSON response
            response_json = None
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    # Try to extract from raw
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log(f"      [ERROR] Failed to parse JSON from {eval_name}: {e}", log_handle)
                return (eval_name, None, call_settings, False)
            
            # Store call settings in response
            response_json["call_settings"] = call_settings
            
            # Post-process: fill in missing why_others_wrong fields (BULLETPROOF REPAIR)
            # This must happen BEFORE schema validation to prevent failures
            if "why_others_wrong" not in response_json:
                response_json["why_others_wrong"] = {}
            
            why_others = response_json["why_others_wrong"]
            final_choice = response_json.get("final_choice")
            
            # Ensure all 4 keys exist
            for choice in ["A", "B", "C", "D"]:
                if choice not in why_others:
                    if choice == final_choice and final_choice != "ABSTAIN":
                        why_others[choice] = "chosen"  # Exact string as specified
                    else:
                        why_others[choice] = "No explanation provided."
                elif choice == final_choice and final_choice != "ABSTAIN" and why_others[choice] != "chosen":
                    # Fix if they wrote something else for chosen option
                    why_others[choice] = "chosen"
            
            # Check ABSTAIN if not allowed
            if not allow_abstain and response_json.get("final_choice") == "ABSTAIN":
                log(f"      [ERROR] Evaluator {eval_name} abstained but allow_abstain=false", log_handle)
                return (eval_name, None, call_settings, False)
            
            # Normalize and validate against schema
            raw_response_backup = json.dumps(response_json)  # Store original for failure tracking
            response_json, is_valid, error_msg = normalize_and_validate_round1(response_json, round1_schema)
            if not is_valid:
                log(f"      [ERROR] Schema validation failed for {eval_name}: {error_msg}", log_handle)
                # Try repair: ask model to output valid JSON with explicit instructions
                repair_prompt = f"""Your previous response had schema validation errors:
{error_msg}

Return ONLY valid JSON matching this schema. Include EVERY required key.
Required keys: final_choice, confidence, why_correct, why_others_wrong (with A,B,C,D), assumptions, weakest_link
If you don't know a value, use an empty string "" but INCLUDE the key.

Original question:
{full_prompt}"""
                try:
                    repair_result, repair_meta = router.call_json(
                        system_prompt="",
                        user_prompt=repair_prompt,
                        schema_validate_fn=None,
                    )
                    if isinstance(repair_result, dict):
                        response_json, is_valid, error_msg = normalize_and_validate_round1(repair_result, round1_schema)
                        if not is_valid:
                            log(f"      [ERROR] Repair attempt failed for {eval_name}: {error_msg}", log_handle)
                            # Return FAILED evaluator with metadata
                            failed_result = {
                                "_evaluator_status": "FAILED",
                                "_schema_error": error_msg,
                                "_raw_response": raw_response_backup[:2000],  # Truncate for storage
                                "_repair_attempted": True,
                                "call_settings": call_settings,
                            }
                            return (eval_name, failed_result, call_settings, False)
                    else:
                        failed_result = {
                            "_evaluator_status": "FAILED",
                            "_schema_error": "Repair returned non-dict",
                            "_raw_response": raw_response_backup[:2000],
                            "_repair_attempted": True,
                            "call_settings": call_settings,
                        }
                        return (eval_name, failed_result, call_settings, False)
                except Exception as e:
                    error_msg = str(e)
                    check_quota_error(error_msg, f"Evaluator {eval_name} (repair attempt)", log_handle)
                    log(f"      [ERROR] Repair attempt exception for {eval_name}: {e}", log_handle)
                    failed_result = {
                        "_evaluator_status": "FAILED",
                        "_schema_error": f"Repair exception: {str(e)[:200]}",
                        "_raw_response": raw_response_backup[:2000],
                        "_repair_attempted": True,
                        "call_settings": call_settings,
                    }
                    return (eval_name, failed_result, call_settings, False)
            
            return (eval_name, response_json, call_settings, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            
            # CRITICAL: Check for quota/funding errors - stop immediately
            check_quota_error(error_msg, f"Evaluator {eval_name}", log_handle)
            
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                log(f"      [ERROR] Evaluator {eval_name} timed out after {elapsed:.1f}s: {e}", log_handle)
            else:
                log(f"      [ERROR] Evaluator {eval_name} failed after {elapsed:.1f}s: {e}", log_handle)
            return (eval_name, None, {}, False)
    
    # Run all evaluators in parallel (Round 1 uses medium effort) - supports 4 evaluators
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        # Submit all evaluator tasks
        future_to_eval = {
            executor.submit(process_single_evaluator, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        # Collect results as they complete - WAIT FOR ALL TO FINISH
        completed_count = 0
        for future in as_completed(future_to_eval):
            eval_name, response_json, call_settings, parse_ok = future.result()
            completed_count += 1
            
            if not parse_ok or response_json is None:
                round1_results[f"parse_ok_{eval_name}"] = False
                # Store failed evaluator metadata if available
                if response_json and response_json.get("_evaluator_status") == "FAILED":
                    round1_results[f"evaluator_{eval_name}"] = response_json
                    log(f"      [AGENT_SCHEMA_FAIL] Evaluator {eval_name}: excluded for this question - {response_json.get('_schema_error', 'unknown')[:80]}", log_handle)
                else:
                    log(f"      [AGENT_SCHEMA_FAIL] Evaluator {eval_name}: no valid response - excluded for this question", log_handle)
                continue
    
            # Store results
            round1_results[f"evaluator_{eval_name}"] = response_json
            round1_results[f"parse_ok_{eval_name}"] = True
            final_choice = response_json.get("final_choice")
            # Only mark correct if not abstaining
            if final_choice != "ABSTAIN":
                round1_results[f"correct_{eval_name}"] = (final_choice == gold_answer)
            else:
                round1_results[f"correct_{eval_name}"] = False
            
            status = "CORRECT" if round1_results[f"correct_{eval_name}"] else "WRONG"
            if final_choice == "ABSTAIN":
                status = "ABSTAINED"
            log(f"      [OK] Evaluator {eval_name}: {final_choice} ({status})", log_handle)
        
        # Ensure all futures completed before continuing
        if completed_count < len(evaluator_routers):
            log(f"      [WARNING] Only {completed_count}/{len(evaluator_routers)} evaluators completed", log_handle)
    
    # Compute agreement pattern with parse_ok tracking (after all evaluators finish) - supports 4 evaluators
    eval_choices = {}
    parse_ok = {}
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        eval_choices[eval_name] = eval_result.get("final_choice") if eval_result else None
        parse_ok[eval_name] = round1_results.get(f"parse_ok_{eval_name}", False)
    
    pattern, majority, unanimous, majority_size, agreement_metadata = compute_agreement_pattern(eval_choices, parse_ok)
    
    round1_results["agreement_pattern"] = pattern
    round1_results["majority_choice"] = majority
    round1_results["unanimous_choice"] = unanimous
    round1_results["majority_size"] = majority_size
    round1_results["answers_by_model"] = eval_choices.copy()
    round1_results["agreement_metadata"] = agreement_metadata
    round1_results["included_evaluators"] = agreement_metadata["included_evaluators"]
    round1_results["excluded_evaluators"] = agreement_metadata["excluded_evaluators"]
    
    # ============================================================
    # A) Compute cheap eliminations (always runs)
    # ============================================================
    cheap_elimination = compute_eliminations_from_round1(
        round1_results, choices, EVALUATORS
    )
    round1_results["cheap_elimination"] = cheap_elimination
    
    log(f"      [CHEAP_ELIM] Eliminated: {list(cheap_elimination['eliminated'].keys())}, Survivors: {cheap_elimination['survivors']}, Confidence: {cheap_elimination['confidence']}", log_handle)
    
    # ============================================================
    # C) Validate choice mapping for each evaluator
    # ============================================================
    choice_map, reverse_choice_map = build_choice_maps(choices)
    mapping_validation = {"all_valid": True, "errors": [], "corrections": []}
    
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if not eval_result:
            continue
        
        is_valid, error_msg, corrected_letter = validate_choice_mapping_round1(
            eval_result, choices, choice_map, reverse_choice_map
        )
        
        if not is_valid:
            mapping_validation["all_valid"] = False
            mapping_validation["errors"].append({"evaluator": eval_name, "error": error_msg})
            eval_result["mapping_validation_error"] = error_msg
            
            if corrected_letter:
                mapping_validation["corrections"].append({
                    "evaluator": eval_name, 
                    "original": eval_result.get("final_choice"),
                    "corrected": corrected_letter
                })
                # Apply correction
                eval_result["final_choice_original"] = eval_result.get("final_choice")
                eval_result["final_choice"] = corrected_letter
                log(f"      [MAPPING] Corrected {eval_name}: {eval_result['final_choice_original']} -> {corrected_letter}", log_handle)
        else:
            eval_result["mapping_validation_ok"] = True
    
    round1_results["mapping_validation"] = mapping_validation
    
    if not mapping_validation["all_valid"]:
        log(f"      [WARNING] Mapping validation errors: {mapping_validation['errors']}", log_handle)
    
    # Log pipeline bug warning if insufficient evaluators
    if agreement_metadata.get("pipeline_bug"):
        log(f"      [WARNING] INSUFFICIENT_EVALUATORS: Only {agreement_metadata['valid_evaluator_count']} valid (need {MIN_VALID_EVALUATORS})", log_handle)
        round1_results["pipeline_bug"] = True
    
    return round1_results

# ============================================================
# Eliminated Options Detection
# ============================================================
def detect_pruned_options(round1_results: dict) -> Tuple[dict, dict]:
    """
    Detect options that all evaluators structurally rejected WITH PROOF UNITS.
    Returns: (pruned_dict, unfalsified_reject_dict)
    - pruned_dict: {"A": "reason summary"} - options that can be pruned (all reject + proof units)
    - unfalsified_reject_dict: {"B": "reason summary"} - options rejected but not falsified (keep in candidate set)
    
    Pruning rules:
    1. All evaluators must reject the option
    2. At least two evaluators must provide non-none proof units against it
    3. Those proof units must be structurally compatible (same contradiction family)
    """
    pruned = {}
    unfalsified_reject = {}
    
    # For each option A-D
    for option in ["A", "B", "C", "D"]:
        rejections = []
        proof_units = []  # List of (eval_name, proof_type, proof_text)
        all_reject = True
        
        # Check each evaluator's reasoning for this option
        for eval_name in EVALUATORS:
            eval_result = round1_results.get(f"evaluator_{eval_name}")
            if not eval_result or not round1_results.get(f"parse_ok_{eval_name}", False):
                all_reject = False
                break
            
            # Check if this evaluator chose this option (not eliminated)
            final_choice = eval_result.get("final_choice", "")
            if final_choice == option:
                all_reject = False
                break
            
            # Get why_others_wrong for this option
            why_others = eval_result.get("why_others_wrong", {})
            option_reason = why_others.get(option, "").lower()
            rejections.append(option_reason)
            
            # Get proof_attempt for this option
            proof_attempt = eval_result.get("proof_attempt", {})
            option_proof = proof_attempt.get(option, {})
            proof_type = option_proof.get("type", "cannot_falsify")
            proof_text = option_proof.get("text", "")
            
            # Only count non-cannot_falsify proof units
            if proof_type != "cannot_falsify" and proof_text:
                proof_units.append((eval_name, proof_type, proof_text))
        
        # If all evaluators rejected, check proof requirements
        if all_reject and len(rejections) == len(EVALUATORS):
            # Check if at least 2 evaluators provided non-cannot_falsify proof units
            if len(proof_units) >= 2:
                # Check if proof units are structurally compatible (same contradiction family)
                proof_types = [pt for _, pt, _ in proof_units]
                # Group by type: contradiction, impossibility, forced_implication
                type_counts = Counter(proof_types)
                
                # If at least 2 share the same type, consider them compatible
                max_type_count = max(type_counts.values()) if type_counts else 0
                
                if max_type_count >= 2:
                    # Compatible proof units - can prune
                    summary = "; ".join([r[:100] for r in rejections[:2]])  # First 2 reasons
                    pruned[option] = summary
                else:
                    # Incompatible proof units - mark as unfalsified_reject
                    summary = "; ".join([r[:100] for r in rejections[:2]])
                    unfalsified_reject[option] = summary
            else:
                # Not enough proof units - mark as unfalsified_reject
                summary = "; ".join([r[:100] for r in rejections[:2]])
                unfalsified_reject[option] = summary
    
    return pruned, unfalsified_reject

# ============================================================
# Grok Analyzer (Round 1.5 - Reasoning Analysis)
# ============================================================
def call_grok_analyzer(
    question_data: dict,
    round1_results: dict,
    analyzer_router: ProviderRouter,
    analyzer_prompt_template: str,
    analyzer_schema: dict,
    log_handle,
    audit_trail: list = None
) -> Optional[dict]:
    """Call Grok to analyze reasoning paths (NOT a tiebreaker - no answer decision)."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    # Collect evaluator JSON outputs (anonymized as A/B/C/D)
    eval_jsons = {}
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            eval_jsons[eval_name] = json.dumps(eval_result, indent=2)
        else:
            eval_jsons[eval_name] = "{}"
    
    # Build prompt from template
    full_prompt = analyzer_prompt_template.format(
        question=question,
        choice_a=choices.get("A", ""),
        choice_b=choices.get("B", ""),
        choice_c=choices.get("C", ""),
        choice_d=choices.get("D", ""),
        json_a=eval_jsons.get("A", "{}"),
        json_b=eval_jsons.get("B", "{}"),
        json_c=eval_jsons.get("C", "{}"),
        json_d=eval_jsons.get("D", "{}")
    )
    
    log("    Calling Grok Analyzer (Round 1.5)...", log_handle)
    start_time = time.time()
    
    # Attribution logging
    analyzer_target = analyzer_router.targets[0] if analyzer_router.targets else None
    if analyzer_target:
        log(f"      [ATTRIBUTION] Grok Analyzer - model={analyzer_target.name}, provider={analyzer_target.provider}, round=R1.5, timeout_sec={analyzer_target.timeout_sec}", log_handle)
    
    try:
        result, meta = analyzer_router.call_json(
            system_prompt="",
            user_prompt=full_prompt,
            schema_validate_fn=None,
        )
        
        # Record audit entry if requested
        if audit_trail is not None:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry(audit_trail, "Round 1.5", analyzer_target.name if analyzer_target else "Grok", "Analyzer", full_prompt, raw_out)
        
        elapsed = time.time() - start_time
        log(f"      [TIMING] Grok Analyzer: {elapsed:.1f}s", log_handle)
        
        # Parse JSON response
        analyzer_result = None
        try:
            if isinstance(result, dict):
                analyzer_result = result
            else:
                raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    analyzer_result = json.loads(json_match.group(1))
                else:
                    analyzer_result = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            elapsed = time.time() - start_time
            log(f"      [ERROR] Failed to parse Grok Analyzer JSON after {elapsed:.1f}s: {e}", log_handle)
            return None
        
        # Normalize and validate against schema
        analyzer_result, is_valid, schema_error = normalize_and_validate_grok(analyzer_result, analyzer_schema)
        if not is_valid:
            log(f"      [GROK_UNAVAILABLE] Grok Analyzer schema validation failed: {schema_error}", log_handle)
            log(f"      [GROK_UNAVAILABLE] Preserving R1 candidate set - analyzer is advisory only", log_handle)
            return None
        
        # Ensure no verdict fields exist (regression guard)
        forbidden_fields = ["verdict", "final_choice", "recommendation", "rank", "choice", "score"]
        found_forbidden = [f for f in forbidden_fields if f in analyzer_result]
        if found_forbidden:
            log(f"      [ERROR] Grok Analyzer output contains forbidden fields: {found_forbidden}", log_handle)
            raise ValueError(f"Grok Analyzer leaked verdicts: {found_forbidden}")
        
        # Validate logical consistency (Part B)
        grok_incompatibility_invalid = False
        
        # Rule: If incompatibility_detected=true, incompatible_assumptions must be non-empty
        if analyzer_result.get("incompatibility_detected", False):
            incompatible_assumptions = analyzer_result.get("incompatible_assumptions", [])
            if not incompatible_assumptions or len(incompatible_assumptions) == 0:
                log(f"      [WARNING] Grok flagged incompatibility but provided no incompatible_assumptions - forcing false", log_handle)
                analyzer_result["incompatibility_detected"] = False
                grok_incompatibility_invalid = True
        
        # Rule: If equivalence_detected=true and incompatibility_detected=true, both lists must be non-empty
        equivalence_detected = analyzer_result.get("equivalence_detected", False)
        incompatibility_detected = analyzer_result.get("incompatibility_detected", False)
        equivalent_methods = analyzer_result.get("equivalent_methods", [])
        incompatible_assumptions = analyzer_result.get("incompatible_assumptions", [])
        
        # Compute reasoning_relation
        if equivalence_detected and incompatibility_detected:
            if (equivalent_methods and len(equivalent_methods) > 0 and 
                incompatible_assumptions and len(incompatible_assumptions) > 0):
                reasoning_relation = "MIXED"
            else:
                # Downgrade to equivalence only
                log(f"      [WARNING] Grok flagged both equivalence and incompatibility but lists incomplete - downgrading to EQUIVALENT", log_handle)
                analyzer_result["incompatibility_detected"] = False
                reasoning_relation = "EQUIVALENT"
        elif equivalence_detected:
            reasoning_relation = "EQUIVALENT"
        elif incompatibility_detected:
            reasoning_relation = "INCOMPATIBLE"
        else:
            reasoning_relation = "UNKNOWN"
        
        analyzer_result["reasoning_relation"] = reasoning_relation
        analyzer_result["grok_incompatibility_invalid"] = grok_incompatibility_invalid
        
        log(f"      [OK] Grok Analyzer: {analyzer_result.get('similarity_level', 'unknown')} similarity, relation={reasoning_relation}", log_handle)
        return analyzer_result
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        check_quota_error(error_msg, "Grok Analyzer", log_handle)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            log(f"      [ERROR] Grok Analyzer timed out after {elapsed:.1f}s: {e}", log_handle)
        else:
            log(f"      [ERROR] Grok Analyzer failed after {elapsed:.1f}s: {e}", log_handle)
        return None
        
# ============================================================
# Escalation Decision Gate
# ============================================================
def should_escalate_thinking(
    round1_results: dict,
    grok_analysis: Optional[dict],
    synthesis_result: Optional[dict],
    candidate_options: list,
    question_data: dict,
    log_handle
) -> Tuple[bool, List[str]]:
    """
    Decide if we should upgrade evaluator thinking effort in Round 2c.
    Returns: (should_escalate, escalation_reasons)
    """
    escalation_reasons = []
    
    # Get Round 1 agreement pattern
    r1_pattern = round1_results.get("agreement_pattern", "unknown")
    
    # Get Grok analysis signals
    grok_similarity = "UNKNOWN"
    if grok_analysis:
        grok_similarity = grok_analysis.get("similarity_level", "UNKNOWN")
    
    # Get synthesis signals
    synth_incompatibility = False
    if synthesis_result:
        synth_incompatibility = synthesis_result.get("incompatibility_detected", False)
    
    # Get evaluator correctness and confidence
    eval_wrong = {}
    eval_high_confidence_wrong = {}
    gold_answer = question_data.get("gold_answer", "")
    
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            choice = eval_result.get("final_choice")
            confidence = eval_result.get("confidence", 0)
            is_wrong = (choice != gold_answer) if gold_answer else False
            eval_wrong[eval_name] = is_wrong
            eval_high_confidence_wrong[eval_name] = (is_wrong and confidence >= 80)
    
    # Escalate if any of these are true:
    # 1. agreement_pattern is not unanimous (unanimous_3, unanimous_4, etc.)
    if not r1_pattern.startswith("unanimous"):
        escalation_reasons.append(f"Round 1 disagreement ({r1_pattern})")
    
    # 2. grok_similarity in {"MEDIUM","LOW"} (changed from SURFACE/DIVERGENT to match new schema)
    if grok_similarity in ["MEDIUM", "LOW"]:
        escalation_reasons.append(f"Grok similarity {grok_similarity}")
    
    # 3. synth_incompatibility == True
    if synth_incompatibility:
        escalation_reasons.append("Synthesizer detected incompatibility")
    
    # 4. candidate_set_size == 2 AND at least one evaluator was wrong in Round 1
    if len(candidate_options) == 2 and any(eval_wrong.values()):
        wrong_evals = [name for name, wrong in eval_wrong.items() if wrong]
        escalation_reasons.append(f"Candidate set size 2 with wrong evaluators: {', '.join(wrong_evals)}")
    
    # 5. any evaluator confidence is high (>=80) but wrong vs gold
    if any(eval_high_confidence_wrong.values()):
        wrong_high = [name for name, wrong in eval_high_confidence_wrong.items() if wrong]
        escalation_reasons.append(f"High confidence wrong: {', '.join(wrong_high)}")
    
    # Do NOT escalate if: Round 1 unanimous AND grok_similarity == HIGH AND synth_incompatibility == False
    if r1_pattern.startswith("unanimous") and grok_similarity == "HIGH" and not synth_incompatibility:
        escalation_reasons = []  # Clear all reasons
        log(f"      [NOTE] Unanimous answer with HIGH similarity and no incompatibility - no escalation", log_handle)
    
    should_escalate = len(escalation_reasons) > 0
    
    if should_escalate:
        log(f"      [ESCALATE] Thinking upgrade triggered: {', '.join(escalation_reasons)}", log_handle)
    
    return should_escalate, escalation_reasons

# ============================================================
# Unanimity Robustness Classification
# ============================================================
def classify_unanimity_robustness(
    round1_results: dict,
    grok_analysis: Optional[dict],
    question_data: dict,
    log_handle
) -> Tuple[str, List[str]]:
    """
    Classify whether unanimity is ROBUST or FRAGILE.
    Returns: (robustness_level, fragility_reasons)
    robustness_level: "ROBUST" | "FRAGILE"
    fragility_reasons: List of reasons why unanimity is fragile (empty if robust)
    """
    fragility_reasons = []
    
    # Get Round 1 agreement pattern
    r1_pattern = round1_results.get("agreement_pattern", "unknown")
    if not r1_pattern.startswith("unanimous"):
        # Not unanimous, so robustness check doesn't apply
        return "N/A", []
    
    # Get unanimous choice
    unanimous_choice = round1_results.get("unanimous_choice")
    if not unanimous_choice:
        return "N/A", []
    
    # Trigger Condition 1: Proof Type Weakness
    # Check if all evaluators use weak proof types (forced_implication, heuristic_rule, naming_convention, typical_product)
    # AND no evaluator provides strong proof types (explicit construction, conservation argument, invariant-based contradiction)
    weak_proof_types = {"forced_implication", "heuristic_rule", "naming_convention", "typical_product"}
    strong_proof_types = {"contradiction", "impossibility"}  # These indicate explicit construction/conservation/invariant
    
    all_weak = True
    has_strong = False
    
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            proof_attempt = eval_result.get("proof_attempt", {})
            for opt, proof_unit in proof_attempt.items():
                if opt != unanimous_choice and isinstance(proof_unit, dict):
                    proof_type = proof_unit.get("type", "")
                    if proof_type in strong_proof_types:
                        has_strong = True
                    if proof_type not in weak_proof_types and proof_type != "cannot_falsify":
                        all_weak = False
    
    if all_weak and not has_strong:
        fragility_reasons.append("All evaluators use weak proof types (forced_implication/heuristic_rule/naming_convention) with no strong proofs (contradiction/impossibility)")
    
    # Trigger Condition 2: Shared Assumption Dependency
    # Check if all evaluators rely on identical unstated assumptions
    # This is detected by checking if all evaluators' assumptions lists are similar or if they all mention the same implicit concepts
    assumptions_by_eval = {}
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            assumptions = eval_result.get("assumptions", [])
            assumptions_by_eval[eval_name] = assumptions
    
    if len(assumptions_by_eval) >= 3:  # Need at least 3 evaluators to check
        # Check for common implicit assumptions (stereochemical mapping, sign conventions, labeling conventions)
        common_implicit_keywords = ["stereochem", "stereo", "R/S", "endo/exo", "convention", "sign", "labeling", "standard outcome"]
        all_share_implicit = True
        shared_keywords = set()
        
        for eval_name, assumptions in assumptions_by_eval.items():
            eval_keywords = set()
            for assumption in assumptions:
                assumption_lower = assumption.lower()
                for keyword in common_implicit_keywords:
                    if keyword in assumption_lower:
                        eval_keywords.add(keyword)
            
            if not shared_keywords:
                shared_keywords = eval_keywords
            else:
                shared_keywords &= eval_keywords
            
            if not eval_keywords:
                all_share_implicit = False
        
        if all_share_implicit and shared_keywords:
            fragility_reasons.append(f"All evaluators share implicit assumptions: {', '.join(shared_keywords)}")
    
    # Trigger Condition 3: Representation Ambiguity
    # Check if problem involves stereochemistry, orientation conventions, naming without structure, coordinate/frame choice
    # AND no explicit structural proof is given
    question = question_data.get("question", "").lower()
    representation_keywords = ["stereochem", "stereo", "chiral", "enantiomer", "diastereomer", "R/S", "D/L", "endo/exo", "conformation", "orientation", "naming", "coordinate"]
    has_representation_ambiguity = any(keyword in question for keyword in representation_keywords)
    
    if has_representation_ambiguity and not has_strong:
        fragility_reasons.append("Problem involves representation ambiguity (stereochemistry/orientation/naming) but no explicit structural proof provided")
    
    # Trigger Condition 4: Grok Advisory Flag
    # Grok reports EQUIVALENT but cannot enumerate independent logical commitments beyond shared heuristics
    if grok_analysis:
        reasoning_relation = grok_analysis.get("reasoning_relation", "UNKNOWN")
        equivalence_detected = grok_analysis.get("equivalence_detected", False)
        
        if reasoning_relation == "EQUIVALENT" and equivalence_detected:
            # Check if Grok notes mention only heuristics
            grok_notes = grok_analysis.get("notes", "").lower()
            heuristic_indicators = ["heuristic", "convention", "typical", "standard", "common approach"]
            if any(indicator in grok_notes for indicator in heuristic_indicators):
                fragility_reasons.append("Grok reports EQUIVALENT reasoning but only identifies shared heuristics, not independent logical commitments")
    
    # Determine robustness
    if len(fragility_reasons) > 0:
        robustness = "FRAGILE"
        log(f"      [UNANIMITY] Classified as FRAGILE: {', '.join(fragility_reasons)}", log_handle)
    else:
        robustness = "ROBUST"
        log(f"      [UNANIMITY] Classified as ROBUST (no fragility indicators)", log_handle)
    
    return robustness, fragility_reasons

# ============================================================
# Unanimity Challenge Round
# ============================================================
def process_unanimity_challenge(
    question_data: dict,
    round1_results: dict,
    unanimous_choice: str,
    evaluator_routers: Dict[str, ProviderRouter],
    challenge_prompt_template: str,
    challenge_schema: dict,
    log_handle
) -> dict:
    """
    Process Unanimity Challenge Round: Test if unanimous answer can survive falsification pressure.
    Returns: {
        "challenge_results": {
            "A": {"can_break": bool, "failure_mode": str, "argument": str},
            ...
        },
        "all_cannot_break": bool,
        "any_can_break": bool,
        "robustness_verdict": "ROBUST" | "FRAGILE"
    }
    """
    question = question_data["question"]
    choices = question_data["choices"]
    
    log("    Processing Unanimity Challenge Round...", log_handle)
    log(f"      [CHALLENGE] Testing unanimous answer: {unanimous_choice}", log_handle)
    
    # Build prompt from template
    full_prompt = challenge_prompt_template.format(
        question=question,
        choice_a=choices.get("A", ""),
        choice_b=choices.get("B", ""),
        choice_c=choices.get("C", ""),
        choice_d=choices.get("D", ""),
        unanimous_answer=unanimous_choice
    )
    
    challenge_results = {}
    start_times = {}
    
    # Call all evaluators in parallel
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        future_to_eval = {}
        
        for eval_name in EVALUATORS:
            router = evaluator_routers.get(eval_name)
            if not router:
                continue
            
            eval_result = round1_results.get(f"evaluator_{eval_name}")
            if not eval_result or not round1_results.get(f"parse_ok_{eval_name}", False):
                log(f"      [SKIP] Evaluator {eval_name} skipped (no valid Round 1 result)", log_handle)
                continue
            
            start_times[eval_name] = time.time()
            
            # Submit challenge task
            future = executor.submit(
                call_evaluator_with_override,
                eval_name, router, "", full_prompt, log_handle,
                None, None  # No effort override for challenge round
            )
            future_to_eval[future] = eval_name
        
        # Collect results
        for future in as_completed(future_to_eval):
            eval_name = future_to_eval[future]
            elapsed = time.time() - start_times.get(eval_name, time.time())
            
            try:
                result, meta, call_settings = future.result()
                
                # Parse and validate JSON
                try:
                    parsed = json.loads(result) if isinstance(result, str) else result
                    jsonschema.validate(instance=parsed, schema=challenge_schema)
                    
                    challenge_results[eval_name] = parsed
                    log(f"      [OK] Evaluator {eval_name} challenge: can_break={parsed.get('can_break')}, mode={parsed.get('failure_mode')} ({elapsed:.1f}s)", log_handle)
                    
                except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                    log(f"      [ERROR] Evaluator {eval_name} challenge parse failed: {e}", log_handle)
                    challenge_results[eval_name] = {
                        "can_break": None,
                        "failure_mode": "parse_error",
                        "argument": f"Parse error: {str(e)}"
                    }
                    
            except Exception as e:
                log(f"      [ERROR] Evaluator {eval_name} challenge failed: {e}", log_handle)
                challenge_results[eval_name] = {
                    "can_break": None,
                    "failure_mode": "call_error",
                    "argument": f"Call error: {str(e)}"
                }
    
    # Determine robustness verdict
    valid_results = {k: v for k, v in challenge_results.items() if v.get("can_break") is not None}
    
    if len(valid_results) == 0:
        log(f"      [WARNING] No valid challenge results - cannot determine robustness", log_handle)
        all_cannot_break = False
        any_can_break = True  # Conservative: assume fragile if we can't verify
    else:
        all_cannot_break = all(r.get("can_break") == False for r in valid_results.values())
        any_can_break = any(r.get("can_break") == True for r in valid_results.values())
    
    robustness_verdict = "ROBUST" if all_cannot_break else "FRAGILE"
    
    log(f"      [VERDICT] Unanimity robustness: {robustness_verdict} (all_cannot_break={all_cannot_break}, any_can_break={any_can_break})", log_handle)
    
    return {
        "challenge_results": challenge_results,
        "all_cannot_break": all_cannot_break,
        "any_can_break": any_can_break,
        "robustness_verdict": robustness_verdict,
        "valid_result_count": len(valid_results)
    }

# ============================================================
# Synthesizer (Round 2 - Candidate-Focused Synthesis)
# ============================================================
def call_synthesizer(
    question_data: dict,
    round1_results: dict,
    eliminated_options: dict,
    candidate_options: list,
    grok_analysis: dict,
    synthesizer_router: ProviderRouter,
    synthesizer_prompt_template: str,
    synthesizer_schema: dict,
    log_handle,
    audit_trail: list = None
) -> Optional[dict]:
    """Call GPT-5.2 Thinking to synthesize candidate-focused arguments (NOT a tiebreaker - no answer decision)."""
    # Round 2: Argument Reconstruction — No Verdicts
    question = question_data["question"]
    choices = question_data["choices"]
    
    # Collect evaluator JSON outputs (anonymized as A/B/C/D)
    eval_jsons = {}
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            eval_jsons[eval_name] = json.dumps(eval_result, indent=2)
        else:
            eval_jsons[eval_name] = "{}"
    
    # Build candidate choices text (only remaining options)
    # GUARDRAIL: Ensure no pruned options appear in synthesis
    pruned_set = set(eliminated_options.keys())
    candidate_set = set(candidate_options)
    if pruned_set & candidate_set:
        log(f"      [ERROR] Pruned options {pruned_set & candidate_set} appeared in candidate set - removing", log_handle)
        candidate_options = [opt for opt in candidate_options if opt not in pruned_set]
    candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
    
    # Build Grok analysis JSON string
    grok_analysis_json_str = json.dumps(grok_analysis, indent=2)
    
    # Build prompt from template
    full_prompt = synthesizer_prompt_template.format(
        question=question,
        candidate_choices_text=candidate_choices_text,
        json_a=eval_jsons.get("A", "{}"),
        json_b=eval_jsons.get("B", "{}"),
        json_c=eval_jsons.get("C", "{}"),
        json_d=eval_jsons.get("D", "{}"),
        grok_analysis_json=grok_analysis_json_str
    )
    
    log("    Calling Synthesizer (GPT-5.2 Thinking)...", log_handle)
    start_time = time.time()
    
    # Attribution logging
    synthesizer_target = synthesizer_router.targets[0] if synthesizer_router.targets else None
    if synthesizer_target:
        log(f"      [ATTRIBUTION] Synthesizer - model={synthesizer_target.name}, provider={synthesizer_target.provider}, round=R2, timeout_sec={synthesizer_target.timeout_sec}", log_handle)
    
    try:
        result, meta = synthesizer_router.call_json(
            system_prompt="",
            user_prompt=full_prompt,
            schema_validate_fn=None,
        )
        
        # Record audit entry if requested
        if audit_trail is not None:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry(audit_trail, "Round 2", synthesizer_target.name if synthesizer_target else "Synthesizer", "Synthesizer", full_prompt, raw_out)
        
        elapsed = time.time() - start_time
        log(f"      [TIMING] Synthesizer: {elapsed:.1f}s", log_handle)
        
        # Parse JSON response
        synthesis_result = None
        try:
            if isinstance(result, dict):
                synthesis_result = result
            else:
                raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    synthesis_result = json.loads(json_match.group(1))
                else:
                    synthesis_result = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            elapsed = time.time() - start_time
            log(f"      [ERROR] Failed to parse Synthesizer JSON after {elapsed:.1f}s: {e}", log_handle)
            return None
        
        # DEFENSIVE: Default abstain to false if missing (prevents schema if/then quirk)
        synth_repaired = False
        if "abstain" not in synthesis_result:
            log(f"      [REPAIR] Synthesizer response missing 'abstain' field - defaulting to false", log_handle)
            synthesis_result["abstain"] = False
            synth_repaired = True
        
        # Apply normalization BEFORE schema validation
        # This filters invalid options like 'E' from candidate_options
        synthesis_result = normalize_synthesizer(synthesis_result)
        
        # DEFENSIVE: Backup filter for candidate_options (in case normalize_responses has stale cache)
        # GPT-5.2 sometimes hallucinates 'E' as a valid option
        VALID_CHOICES = {"A", "B", "C", "D"}
        if "candidate_options" in synthesis_result:
            original_opts = synthesis_result["candidate_options"]
            filtered_opts = [opt for opt in original_opts if isinstance(opt, str) and opt.upper() in VALID_CHOICES]
            if len(filtered_opts) != len(original_opts):
                invalid_opts = [opt for opt in original_opts if opt not in filtered_opts]
                log(f"      [SYNTH_INVALID_OPTION] Discarding invalid options {invalid_opts} - falling back to deterministic set {filtered_opts}", log_handle)
                synthesis_result["candidate_options"] = filtered_opts
                synth_repaired = True
            # Ensure at least one valid option (fallback to all if all were invalid)
            if not synthesis_result["candidate_options"]:
                log(f"      [SYNTH_INVALID_OPTION] All candidate_options invalid - falling back to deterministic candidates from pruning: {list(candidate_options)}", log_handle)
                synthesis_result["candidate_options"] = list(candidate_options)
        
        # Validate against schema
        try:
            jsonschema.validate(instance=synthesis_result, schema=synthesizer_schema)
        except jsonschema.ValidationError as e:
            # Repair: If abstain=true but abstain_justification is missing, add default
            if "abstain_justification" in str(e) and synthesis_result.get("abstain", False):
                log(f"      [REPAIR] Synthesizer abstained but missing abstain_justification - adding default", log_handle)
                synthesis_result["abstain_justification"] = "Agreement exists without justification integrity - evaluators converge but reasoning paths are logically incompatible with no shared valid justification"
                synth_repaired = True
                # Re-validate after repair
                try:
                    jsonschema.validate(instance=synthesis_result, schema=synthesizer_schema)
                except jsonschema.ValidationError as e2:
                    log(f"      [ERROR] Synthesizer schema validation failed after repair: {e2}", log_handle)
                    return None
            else:
                log(f"      [ERROR] Synthesizer schema validation failed: {e}", log_handle)
                return None
        
        # Track if repair was applied
        if synth_repaired:
            synthesis_result["synth_repaired"] = True
        
        # Ensure no verdict fields exist (regression guard)
        forbidden_fields = ["verdict", "final_choice", "strongest_evaluator", "recommendation", "rank", "choice", "score"]
        found_forbidden = [f for f in forbidden_fields if f in synthesis_result]
        if found_forbidden:
            log(f"      [ERROR] Synthesizer output contains forbidden fields: {found_forbidden}", log_handle)
            raise ValueError(f"Synthesizer leaked verdicts: {found_forbidden}")
        
        # Check if Synthesizer abstained
        abstain = synthesis_result.get("abstain", False)
        if abstain:
            abstain_justification = synthesis_result.get("abstain_justification", "")
            log(f"      [ABSTAIN] Synthesizer abstained: {abstain_justification}", log_handle)
        else:
            log(f"      [OK] Synthesizer: incompatibility={synthesis_result.get('incompatibility_detected', 'unknown')}, equivalence={synthesis_result.get('equivalence_detected', 'unknown')}", log_handle)
        return synthesis_result
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        check_quota_error(error_msg, "Synthesizer", log_handle)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            log(f"      [ERROR] Synthesizer timed out after {elapsed:.1f}s: {e}", log_handle)
        else:
            log(f"      [ERROR] Synthesizer failed after {elapsed:.1f}s: {e}", log_handle)
        return None

# ============================================================
# Round 1.75: Representation Validation
# ============================================================
def process_round1_75_fidelity_check(
    question_data: dict,
    round1_results: dict,
    synthesis_result: dict,
    candidate_options: list,
    evaluator_routers: Dict[str, ProviderRouter],
    fidelity_prompt_template: str,
    fidelity_schema: dict,
    log_handle
) -> dict:
    """Process Round 1.75: Each evaluator validates ALL reconstructed arguments for epistemic integrity."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    log(f"  Processing Round 1.75 (Representation Validation)...", log_handle)
    
    validation_results = {
        "evaluator_A": None,
        "evaluator_B": None,
        "evaluator_C": None,
    }
    
    argument_reconstructions = synthesis_result.get("argument_reconstructions", {})
    cross_candidate_incompatibility = synthesis_result.get("cross_candidate_incompatibility", [])
    
    if not argument_reconstructions:
        log(f"      [SKIP] No argument reconstructions available for validation", log_handle)
        return validation_results
    
    # Helper function to process a single evaluator validation (for parallel execution)
    def process_single_evaluator_validation(eval_name: str, router: ProviderRouter) -> Tuple[str, Optional[dict], bool]:
        """Process a single evaluator validation. Returns (eval_name, response_json, success)."""
        log(f"    Validating arguments for Evaluator {eval_name}...", log_handle)
        
        # Attribution logging (before call)
        target = router.targets[0] if router.targets else None
        if target:
            log(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, provider={target.provider}, round=R1.75, timeout_sec={target.timeout_sec}", log_handle)
        
        # Get this evaluator's Round 1 result
        round1_result = round1_results.get(f"evaluator_{eval_name}")
        if not round1_result:
            log(f"      [SKIP] Evaluator {eval_name} had no Round 1 result", log_handle)
            return (eval_name, None, False)
        
        # Build prompt with ALL candidate arguments (no evaluator attribution)
        round1_json_str = json.dumps(round1_result, indent=2)
        choices_json_str = json.dumps(choices, indent=2)
        argument_reconstructions_json_str = json.dumps(argument_reconstructions, indent=2)
        cross_candidate_incompatibility_json_str = json.dumps(cross_candidate_incompatibility, indent=2)
        
        full_prompt = fidelity_prompt_template.format(
            question=question,
            choices_json=choices_json_str,
            round1_json=round1_json_str,
            argument_reconstructions_json=argument_reconstructions_json_str,
            cross_candidate_incompatibility_json=cross_candidate_incompatibility_json_str
        )
        
        start_time = time.time()
        try:
            result, meta = router.call_json(
                system_prompt="",
                user_prompt=full_prompt,
                schema_validate_fn=None,
            )
            elapsed = time.time() - start_time
            log(f"      [TIMING] Evaluator {eval_name} (Round 1.75): {elapsed:.1f}s", log_handle)
            
            # Parse JSON response
            response_json = None
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log(f"      [ERROR] Failed to parse validation JSON for {eval_name}: {e}", log_handle)
                return (eval_name, None, False)
            
            # Validate against schema
            try:
                jsonschema.validate(instance=response_json, schema=fidelity_schema)
            except jsonschema.ValidationError as e:
                log(f"      [ERROR] Validation schema validation failed for {eval_name}: {e}", log_handle)
                return (eval_name, None, False)
            
            # Log validation summary
            candidate_validations = response_json.get("candidate_validations", {})
            for candidate, validation in candidate_validations.items():
                if candidate in candidate_options:
                    accuracy = validation.get("representation_accuracy", "UNKNOWN")
                    strength = validation.get("strength_assessment", "UNKNOWN")
                    if accuracy != "YES":
                        correction = validation.get("correction", "")
                        log(f"      [VALIDATION] Evaluator {eval_name} - {candidate}: {accuracy} (correction: {correction[:50]}...)", log_handle)
                    else:
                        log(f"      [VALIDATION] Evaluator {eval_name} - {candidate}: {accuracy}, strength={strength}", log_handle)
            
            return (eval_name, response_json, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            check_quota_error(error_msg, f"Evaluator {eval_name} (Round 1.75 validation)", log_handle)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                log(f"      [ERROR] Evaluator {eval_name} validation timed out after {elapsed:.1f}s: {e}", log_handle)
            else:
                log(f"      [ERROR] Evaluator {eval_name} validation failed after {elapsed:.1f}s: {e}", log_handle)
            return (eval_name, None, False)
    
    # Process all evaluators in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(process_single_evaluator_validation, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        for future in as_completed(futures):
            eval_name, response_json, success = future.result()
            if success and response_json:
                validation_results[f"evaluator_{eval_name}"] = response_json
    
    return validation_results

# ============================================================
# Round 2a: Representation Check (NEW - Simpler than Round 1.75)
# ============================================================
def process_round2a_representation_check(
    question_data: dict,
    round1_results: dict,
    synthesis_result: dict,
    candidate_options: list,
    evaluator_routers: Dict[str, ProviderRouter],
    round2a_prompt_template: str,
    round2a_schema: dict,
    log_handle,
    audit_trail: list = None
) -> dict:
    """Process Round 2a: Each evaluator validates their own reconstruction (simpler than Round 1.75)."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    log(f"  Processing Round 2a (Representation Check)...", log_handle)
    
    representation_results = {}
    
    if not synthesis_result:
        log(f"      [SKIP] synthesis_result is None - skipping representation check", log_handle)
        return representation_results
        
    argument_reconstructions = synthesis_result.get("argument_reconstructions", {})
    if not argument_reconstructions:
        log(f"      [SKIP] No argument reconstructions available for representation check", log_handle)
        return representation_results
    
    # Helper function to format argument reconstruction as readable text
    def format_argument_reconstruction(arg_obj: dict) -> str:
        """Format argument_for or argument_against object as readable text."""
        if not arg_obj:
            return "No reconstruction available"
        
        parts = []
        premises = arg_obj.get("premises", [])
        if premises:
            parts.append("PREMISES:")
            for p in premises:
                parts.append(f"  - {p}")
        
        inference_steps = arg_obj.get("inference_steps", [])
        if inference_steps:
            parts.append("\nINFERENCE STEPS:")
            for i, step in enumerate(inference_steps, 1):
                parts.append(f"  {i}. {step}")
        
        conclusion = arg_obj.get("conclusion", "")
        if conclusion:
            parts.append(f"\nCONCLUSION: {conclusion}")
        
        return "\n".join(parts) if parts else "No reconstruction available"
    
    # Helper function to process a single evaluator representation check
    def process_single_evaluator_check(eval_name: str, router: ProviderRouter) -> Tuple[str, Optional[dict], bool]:
        """Process a single evaluator representation check. Returns (eval_name, response_json, success)."""
        log(f"    Checking representation for Evaluator {eval_name}...", log_handle)
        
        # Attribution logging (before call)
        target = router.targets[0] if router.targets else None
        if target:
            log(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, provider={target.provider}, round=R2a, timeout_sec={target.timeout_sec}", log_handle)
        
        # Get this evaluator's Round 1 result
        round1_result = round1_results.get(f"evaluator_{eval_name}")
        if not round1_result:
            log(f"      [SKIP] Evaluator {eval_name} had no Round 1 result", log_handle)
            return (eval_name, {"round2a_status": "skipped", "skip_reason": "no_round1_result"}, False)
        
        your_choice = round1_result.get("final_choice")
        if not your_choice or your_choice not in candidate_options:
            log(f"      [SKIP] Evaluator {eval_name} choice {your_choice} not in candidate options", log_handle)
            return (eval_name, {"round2a_status": "skipped", "skip_reason": "choice_not_in_candidates"}, False)
        
        # Get reconstructions for this evaluator's choice
        recon_for_candidate = argument_reconstructions.get(your_choice, {})
        reconstruction_for = format_argument_reconstruction(recon_for_candidate.get("argument_for", {}))
        commitments = recon_for_candidate.get("necessary_commitments", [])
        commitments_text = "\n".join([f"  - {c}" for c in commitments]) if commitments else "  (none listed)"
        
        # Build prompt
        full_prompt = round2a_prompt_template.format(
            question=question,
            choice_a=choices.get("A", ""),
            choice_b=choices.get("B", ""),
            choice_c=choices.get("C", ""),
            choice_d=choices.get("D", ""),
            your_choice=your_choice,
            reconstruction_for=reconstruction_for,
            commitments=commitments_text
        )
        
        start_time = time.time()
        try:
            result, meta = router.call_json(
                system_prompt="",
                user_prompt=full_prompt,
                schema_validate_fn=None,
            )
            
            # Record audit entry if requested
            if audit_trail is not None:
                raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                add_audit_entry(audit_trail, "Round 2a", target.name if target else eval_name, "Evaluator", full_prompt, raw_out)
            
            elapsed = time.time() - start_time
            log(f"      [TIMING] Evaluator {eval_name} (Round 2a): {elapsed:.1f}s", log_handle)
            
            # Parse JSON response
            response_json = None
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log(f"      [ERROR] Failed to parse representation check JSON for {eval_name}: {e}", log_handle)
                return (eval_name, {"round2a_status": "failed", "round2a_error": f"json_parse: {str(e)[:100]}"}, False)
            
            # Validate against schema
            try:
                jsonschema.validate(instance=response_json, schema=round2a_schema)
            except jsonschema.ValidationError as e:
                log(f"      [ERROR] Representation check schema validation failed for {eval_name}: {e}", log_handle)
                return (eval_name, {"round2a_status": "failed", "round2a_error": f"schema: {e.message[:100]}"}, False)
            
            # Mark status as ok and log representation check summary
            response_json["round2a_status"] = "ok"
            representation_ok = response_json.get("representation_ok", False)
            if representation_ok:
                log(f"      [REPRESENTATION] Evaluator {eval_name}: OK", log_handle)
            else:
                missing = response_json.get("missing_points")
                mischar = response_json.get("mischaracterizations")
                log(f"      [REPRESENTATION] Evaluator {eval_name}: NOT OK (missing={bool(missing)}, mischar={bool(mischar)})", log_handle)
            
            return (eval_name, response_json, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            check_quota_error(error_msg, f"Evaluator {eval_name} (Round 2a)", log_handle)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                log(f"      [ERROR] Evaluator {eval_name} representation check timed out after {elapsed:.1f}s: {e}", log_handle)
                return (eval_name, {"round2a_status": "failed", "round2a_error": "timeout"}, False)
            else:
                log(f"      [ERROR] Evaluator {eval_name} representation check failed after {elapsed:.1f}s: {e}", log_handle)
                return (eval_name, {"round2a_status": "failed", "round2a_error": f"exception: {str(e)[:100]}"}, False)
    
    # Process all evaluators in parallel
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        futures = {
            executor.submit(process_single_evaluator_check, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
            if eval_name in EVALUATORS
        }
        
        for future in as_completed(futures):
            eval_name, response_json, success = future.result()
            # Always store results, even for skipped/failed (they have round2a_status fields)
            if response_json:
                representation_results[f"evaluator_{eval_name}"] = response_json
    
    # Add overall round status
    any_failed = any(r.get("round2a_status") == "failed" for r in representation_results.values())
    any_skipped = any(r.get("round2a_status") == "skipped" for r in representation_results.values())
    if any_failed:
        representation_results["round_status"] = "partial_failure"
    elif any_skipped:
        representation_results["round_status"] = "partial_skip"
    else:
        representation_results["round_status"] = "ok"
    representation_results["round_executed"] = True
    
    return representation_results

# ============================================================
# Synthesizer Repair (After Round 2a Representation Check)
# ============================================================
def repair_synthesizer_after_round2a(
    question_data: dict,
    round1_results: dict,
    eliminated_options: dict,
    candidate_options: list,
    grok_analysis: dict,
    synthesis_result: dict,
    round2a_results: dict,
    synthesizer_router: ProviderRouter,
    synthesizer_prompt_template: str,
    synthesizer_schema: dict,
    log_handle,
    audit_trail: list = None
) -> Optional[dict]:
    """Repair argument reconstructions based on Round 2a corrections - ONE deterministic pass."""
    if not synthesis_result:
        log(f"      [REPAIR] synthesis_result is None - nothing to repair", log_handle)
        return None
        
    # Check if any repairs are needed
    needs_repair = False
    repair_requests = {}  # candidate -> list of corrections
    
    for eval_name in EVALUATORS:
        eval_check = round2a_results.get(f"evaluator_{eval_name}")
        if not eval_check:
            continue
        
        representation_ok = eval_check.get("representation_ok", True)
        if not representation_ok:
            needs_repair = True
            # Get the evaluator's choice to know which candidate needs repair
            eval_result = round1_results.get(f"evaluator_{eval_name}")
            if eval_result:
                your_choice = eval_result.get("final_choice")
                if your_choice and your_choice in candidate_options:
                    missing_points = eval_check.get("missing_points")
                    mischaracterizations = eval_check.get("mischaracterizations")
                    required_corrections = eval_check.get("required_corrections")
                    
                    if your_choice not in repair_requests:
                        repair_requests[your_choice] = []
                    
                    # Combine all correction sources
                    if missing_points:
                        repair_requests[your_choice].append(f"MISSING: {missing_points}")
                    if mischaracterizations:
                        repair_requests[your_choice].append(f"MISCHARACTERIZATION: {mischaracterizations}")
                    if required_corrections:
                        repair_requests[your_choice].append(f"REQUIRED: {required_corrections}")
    
    if not needs_repair:
        log(f"      [REPAIR] No repairs needed - all Round 2a checks passed", log_handle)
        return synthesis_result  # Return original, unchanged
    
    log(f"      [REPAIR] Repairing arguments based on Round 2a corrections", log_handle)
    log(f"      [REPAIR] Candidates needing repair: {list(repair_requests.keys())}", log_handle)
    
    # Build repair prompt - re-call synthesizer with repair instructions
    question = question_data["question"]
    choices = question_data["choices"]
    
    # Collect evaluator JSON outputs (same as original synthesis)
    eval_jsons = {}
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            eval_jsons[eval_name] = json.dumps(eval_result, indent=2)
        else:
            eval_jsons[eval_name] = "{}"
    
    candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
    grok_analysis_json_str = json.dumps(grok_analysis, indent=2)
    repair_requests_json_str = json.dumps(repair_requests, indent=2)
    
    # Build repair prompt (modify original template to include repair instructions)
    repair_prompt = synthesizer_prompt_template.format(
        question=question,
        candidate_choices_text=candidate_choices_text,
        json_a=eval_jsons.get("A", "{}"),
        json_b=eval_jsons.get("B", "{}"),
        json_c=eval_jsons.get("C", "{}"),
        json_d=eval_jsons.get("D", "{}"),
        grok_analysis_json=grok_analysis_json_str
    )
    
    # Prepend repair instructions
    repair_instructions = f"""REPAIR MODE: The following corrections were requested by evaluators during Round 2a representation check:

{repair_requests_json_str}

You must incorporate these corrections into your argument reconstructions. Do not add new facts - only fix missing points, mischaracterizations, and required corrections as specified above.

Original synthesis prompt follows:
---
"""
    full_repair_prompt = repair_instructions + repair_prompt
    
    log(f"      [REPAIR] Calling Synthesizer in repair mode...", log_handle)
    start_time = time.time()
    
    synthesizer_target = synthesizer_router.targets[0] if synthesizer_router.targets else None
    if synthesizer_target:
        log(f"      [ATTRIBUTION] Synthesizer (Repair) - model={synthesizer_target.name}, provider={synthesizer_target.provider}, round=R2a-repair, timeout_sec={synthesizer_target.timeout_sec}", log_handle)
    
    try:
        result, meta = synthesizer_router.call_json(
            system_prompt="",
            user_prompt=full_repair_prompt,
            schema_validate_fn=None,
        )
        
        # Record audit entry if requested
        if audit_trail is not None:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry(audit_trail, "Round 2 Repair", synthesizer_target.name if synthesizer_target else "Synthesizer", "Synthesizer", full_repair_prompt, raw_out)
            
        elapsed = time.time() - start_time
        log(f"      [TIMING] Synthesizer (Repair): {elapsed:.1f}s", log_handle)
        
        # Parse JSON response
        repaired_synthesis = None
        try:
            if isinstance(result, dict):
                repaired_synthesis = result
            else:
                raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    repaired_synthesis = json.loads(json_match.group(1))
                else:
                    repaired_synthesis = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            elapsed = time.time() - start_time
            log(f"      [ERROR] Failed to parse Synthesizer repair JSON after {elapsed:.1f}s: {e}", log_handle)
            return None
        
        # DEFENSIVE: Default abstain to false if missing (same as main synthesizer)
        if "abstain" not in repaired_synthesis:
            log(f"      [REPAIR] Synthesizer repair response missing 'abstain' field - defaulting to false", log_handle)
            repaired_synthesis["abstain"] = False
        
        # Validate against schema
        try:
            jsonschema.validate(instance=repaired_synthesis, schema=synthesizer_schema)
        except jsonschema.ValidationError as e:
            log(f"      [ERROR] Synthesizer repair schema validation failed: {e}", log_handle)
            return None
        
        # Ensure no verdict fields exist
        if "verdict" in repaired_synthesis or "final_choice" in repaired_synthesis or "strongest_evaluator" in repaired_synthesis:
            log(f"      [ERROR] Synthesizer repair output contains verdict fields (should not)", log_handle)
            return None
        
        log(f"      [REPAIR] Synthesizer repair completed successfully", log_handle)
        return repaired_synthesis
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        check_quota_error(error_msg, "Synthesizer (Repair)", log_handle)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            log(f"      [ERROR] Synthesizer repair timed out after {elapsed:.1f}s: {e}", log_handle)
        else:
            log(f"      [ERROR] Synthesizer repair failed after {elapsed:.1f}s: {e}", log_handle)
        return None

# ============================================================
# Synthesizer Repair (After Representation Validation) - LEGACY (Round 1.75)
# ============================================================
def repair_synthesizer_arguments(
    question_data: dict,
    round1_results: dict,
    eliminated_options: dict,
    candidate_options: list,
    grok_analysis: dict,
    synthesis_result: dict,
    validation_results: dict,
    synthesizer_router: ProviderRouter,
    synthesizer_prompt_template: str,
    synthesizer_schema: dict,
    log_handle
) -> Optional[dict]:
    """Repair argument reconstructions based on validation corrections - ONE deterministic pass."""
    
    # Check if any repairs are needed
    needs_repair = False
    repair_requests = {}  # candidate -> list of corrections
    
    for eval_name in EVALUATORS:
        eval_validation = validation_results.get(f"evaluator_{eval_name}")
        if not eval_validation:
            continue
        
        candidate_validations = eval_validation.get("candidate_validations", {})
        for candidate, validation in candidate_validations.items():
            if candidate not in candidate_options:
                continue
            
            accuracy = validation.get("representation_accuracy", "YES")
            if accuracy != "YES":
                needs_repair = True
                correction = validation.get("correction", "")
                if correction:
                    if candidate not in repair_requests:
                        repair_requests[candidate] = []
                    repair_requests[candidate].append(correction)
    
    if not needs_repair:
        log(f"      [REPAIR] No repairs needed - all validations passed", log_handle)
        return synthesis_result  # Return original, unchanged
    
    log(f"      [REPAIR] Repairing arguments based on validation corrections", log_handle)
    log(f"      [REPAIR] Candidates needing repair: {list(repair_requests.keys())}", log_handle)
    
    # Build repair prompt - re-call synthesizer with repair instructions
    question = question_data["question"]
    choices = question_data["choices"]
    
    # Collect evaluator JSON outputs (same as original synthesis) - supports 4 evaluators
    eval_jsons = {}
    for eval_name in EVALUATORS:
        eval_result = round1_results.get(f"evaluator_{eval_name}")
        if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
            eval_jsons[eval_name] = json.dumps(eval_result, indent=2)
        else:
            eval_jsons[eval_name] = "{}"
    
    candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
    grok_analysis_json_str = json.dumps(grok_analysis, indent=2)
    repair_requests_json_str = json.dumps(repair_requests, indent=2)
    
    # Build repair prompt (modify original template to include repair instructions)
    repair_prompt = synthesizer_prompt_template.format(
        question=question,
        candidate_choices_text=candidate_choices_text,
        json_a=eval_jsons.get("A", "{}"),
        json_b=eval_jsons.get("B", "{}"),
        json_c=eval_jsons.get("C", "{}"),
        json_d=eval_jsons.get("D", "{}"),
        grok_analysis_json=grok_analysis_json_str
    )
    
    # Prepend repair instructions
    repair_instructions = f"""
REPAIR REQUEST (MANDATORY):
The following corrections were requested by evaluators during representation validation.
You MUST incorporate these corrections into your argument reconstructions.

REPAIR REQUESTS BY CANDIDATE:
{repair_requests_json_str}

INSTRUCTIONS:
1. For each candidate listed above, incorporate the corrections into the argument_reconstructions
2. Do NOT add new facts - only structural repairs (missing assumptions, distorted logical structure, overstated claims)
3. Regenerate the argument_reconstructions incorporating these corrections
4. All other requirements (proof_ledger, cross_candidate_incompatibility, etc.) remain the same

ORIGINAL SYNTHESIS PROMPT:
"""
    
    full_repair_prompt = repair_instructions + repair_prompt
    
    log("    Calling Synthesizer (REPAIR PASS)...", log_handle)
    start_time = time.time()
    
    synthesizer_target = synthesizer_router.targets[0] if synthesizer_router.targets else None
    if synthesizer_target:
        log(f"      [ATTRIBUTION] Synthesizer (Repair) - model={synthesizer_target.name}, provider={synthesizer_target.provider}, round=R2-REPAIR, timeout_sec={synthesizer_target.timeout_sec}", log_handle)
    
    try:
        result, meta = synthesizer_router.call_json(
            system_prompt="",
            user_prompt=full_repair_prompt,
            schema_validate_fn=None,
        )
        
        # Record audit entry if requested
        if audit_trail is not None:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry(audit_trail, "Round 2 Repair", synthesizer_target.name if synthesizer_target else "Synthesizer", "Synthesizer", full_repair_prompt, raw_out)
            
        elapsed = time.time() - start_time
        log(f"      [TIMING] Synthesizer (Repair): {elapsed:.1f}s", log_handle)
        
        # Parse JSON response
        repaired_result = None
        try:
            if isinstance(result, dict):
                repaired_result = result
            else:
                raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    repaired_result = json.loads(json_match.group(1))
                else:
                    repaired_result = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            elapsed = time.time() - start_time
            log(f"      [ERROR] Failed to parse Synthesizer (Repair) JSON after {elapsed:.1f}s: {e}", log_handle)
            log(f"      [REPAIR] Repair failed - using original synthesis", log_handle)
            return synthesis_result  # Fallback to original
        
        # Validate against schema
        try:
            jsonschema.validate(instance=repaired_result, schema=synthesizer_schema)
        except jsonschema.ValidationError as e:
            log(f"      [ERROR] Synthesizer (Repair) schema validation failed: {e}", log_handle)
            log(f"      [REPAIR] Repair failed - using original synthesis", log_handle)
            return synthesis_result  # Fallback to original
        
        # Mark as repaired
        repaired_result["repair_applied"] = True
        repaired_result["repair_requests"] = repair_requests
        repaired_result["repair_note"] = "Arguments repaired based on validation corrections"
        
        log(f"      [REPAIR] Arguments successfully repaired and locked for Round 2", log_handle)
        return repaired_result
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        check_quota_error(error_msg, "Synthesizer (Repair)", log_handle)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            log(f"      [ERROR] Synthesizer (Repair) timed out after {elapsed:.1f}s: {e}", log_handle)
        else:
            log(f"      [ERROR] Synthesizer (Repair) failed after {elapsed:.1f}s: {e}", log_handle)
        log(f"      [REPAIR] Repair failed - using original synthesis", log_handle)
        return synthesis_result  # Fallback to original

# ============================================================
# Round 2c: Forced Defense Before Commit
# ============================================================

# ============================================================
# Round 2c: Forced Defense Before Commit
# ============================================================
def process_round2c_forced_defense(
    question_data: dict,
    round1_results: dict,
    eliminated_options: dict,
    candidate_options: list,
    synthesis_result: dict,
    evaluator_routers: Dict[str, ProviderRouter],
    round2c_prompt_template: str,
    round2c_schema: dict,
    effort_by_evaluator: Dict[str, str],
    log_handle,
    audit_trail: list = None
) -> dict:
    """Process Round 2c: evaluators must complete forced defense phase before final choice."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    log(f"  Processing Round 2c (Forced Defense) for question {question_data['question_id']} (candidate set: {candidate_options})", log_handle)
    
    round2c_results = {
        "evaluator_A": None,
        "evaluator_B": None,
        "evaluator_C": None,
        "evaluator_D": None,
    }
    
    if not synthesis_result:
        log(f"      [SKIP] synthesis_result is None - skipping Round 2c", log_handle)
        return round2c_results
        
    # Helper function to format argument reconstruction as readable text
    def format_argument_reconstruction(arg_obj: dict) -> str:
        if not arg_obj:
            return "No reconstruction available"
        parts = []
        premises = arg_obj.get("premises", [])
        if premises:
            parts.append("PREMISES:")
            for p in premises:
                parts.append(f"  - {p}")
        inference_steps = arg_obj.get("inference_steps", [])
        if inference_steps:
            parts.append("\nINFERENCE STEPS:")
            for i, step in enumerate(inference_steps, 1):
                parts.append(f"  {i}. {step}")
        conclusion = arg_obj.get("conclusion", "")
        if conclusion:
            parts.append(f"\nCONCLUSION: {conclusion}")
        return "\n".join(parts) if parts else "No reconstruction available"

    # Helper function to process a single evaluator in Round 2c (for parallel execution)
    def process_single_evaluator_round2c(eval_name: str, router: ProviderRouter) -> Tuple[str, Optional[dict], dict, bool]:
        """Process a single evaluator call in Round 2c. Returns (eval_name, response_json, call_settings, success)."""
        log(f"    Calling Evaluator {eval_name} (Round 2c)...", log_handle)
        
        # Attribution logging (before call)
        target = router.targets[0] if router.targets else None
        if target:
            log(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, provider={target.provider}, round=R2c, timeout_sec={target.timeout_sec}", log_handle)
        
        # Get this evaluator's Round 1 result
        round1_result = round1_results.get(f"evaluator_{eval_name}")
        if not round1_result:
            log(f"      [SKIP] Evaluator {eval_name} had no Round 1 result", log_handle)
            # Return a failure record instead of None
            return (eval_name, {"round2c_status": "skipped", "skip_reason": "no_round1_result"}, {}, False)
        
        your_choice = round1_result.get("final_choice")
        if not your_choice:
            log(f"      [SKIP] Evaluator {eval_name} had no valid Round 1 choice", log_handle)
            return (eval_name, {"round2c_status": "skipped", "skip_reason": "no_round1_choice"}, {}, False)

        # Build candidate choices text
        candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
        
        # Extract reconstructions and attacks from synthesis
        argument_reconstructions = synthesis_result.get("argument_reconstructions", {})
        recon_for_yours = argument_reconstructions.get(your_choice, {})
        reconstruction_for = format_argument_reconstruction(recon_for_yours.get("argument_for", {}))
        attack_on_yours = format_argument_reconstruction(recon_for_yours.get("argument_against", {}))
        
        # Identify strongest rival (first candidate option that isn't your_choice)
        rival_choice = "N/A"
        case_for_rival = "No rival case available"
        for opt in candidate_options:
            if opt != your_choice:
                rival_choice = opt
                recon_for_rival = argument_reconstructions.get(opt, {})
                case_for_rival = format_argument_reconstruction(recon_for_rival.get("argument_for", {}))
                break

        full_prompt = round2c_prompt_template.format(
            question=question,
            candidate_choices_text=candidate_choices_text,
            round1_choice=your_choice,
            reconstruction_for=reconstruction_for,
            attack_on_yours=attack_on_yours,
            rival_choice=rival_choice,
            case_for_rival=case_for_rival
        )
        
        # Get effort override for this evaluator
        effort_override = effort_by_evaluator.get(eval_name, "medium")
        if effort_override == "auto":
            effort_override = None  # Use default (for Gemini)
        elif effort_override == "medium":
            effort_override = None  # Keep medium (no override needed)
        
        # Helper to attempt one Round 2c call
        def attempt_round2c_call(prompt: str, is_repair: bool = False) -> Tuple[Optional[dict], dict, str]:
            """Returns (response_json, call_settings, error_msg). error_msg is empty on success."""
            start_time = time.time()
            try:
                result, meta, call_settings = call_evaluator_with_override(
                    eval_name, router, "", prompt, log_handle, effort_override, None
                )
                
                # Record audit entry if requested
                if audit_trail is not None:
                    raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                    audit_round = "Round 2c Repair" if is_repair else "Round 2c"
                    add_audit_entry(audit_trail, audit_round, call_settings.get("model_name", eval_name), "Evaluator", prompt, raw_out)
                
                if result is None:
                    if meta:
                        error_info = meta.get("error", "") or meta.get("raw", "") or str(meta)
                        check_quota_error(error_info, f"Evaluator {eval_name} (Round 2c)", log_handle)
                    return (None, call_settings, "api_returned_none")
                
                elapsed = time.time() - start_time
                log(f"      [TIMING] Evaluator {eval_name} (Round 2c{' repair' if is_repair else ''}): {elapsed:.1f}s", log_handle)
                
                # Parse JSON
                try:
                    if isinstance(result, dict):
                        response_json = result
                    else:
                        raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                        if json_match:
                            response_json = json.loads(json_match.group(1))
                        else:
                            response_json = json.loads(raw_response)
                except (json.JSONDecodeError, TypeError) as e:
                    return (None, call_settings, f"json_parse_error: {str(e)[:100]}")
                
                # Normalize and validate schema
                response_json, is_valid, schema_error = normalize_and_validate_round2c(response_json, round2c_schema)
                if not is_valid:
                    return (None, call_settings, f"schema_error: {schema_error[:100]}")
                
                return (response_json, call_settings, "")
                
            except Exception as e:
                elapsed = time.time() - start_time
                return (None, {}, f"exception: {str(e)[:100]}")
        
        # First attempt
        response_json, call_settings, error_msg = attempt_round2c_call(full_prompt, is_repair=False)
        
        # If schema/parse failure, retry ONCE with repair prompt
        if response_json is None and ("schema_error" in error_msg or "json_parse_error" in error_msg):
            log(f"      [REPAIR] Evaluator {eval_name} failed ({error_msg}) - retrying with repair prompt", log_handle)
            repair_prompt = full_prompt + f"\n\n[REPAIR]: Your previous response had errors: {error_msg}\nPlease output valid JSON matching the required schema, with non-empty defense.rebuttal and attack.counter fields."
            response_json, call_settings, error_msg = attempt_round2c_call(repair_prompt, is_repair=True)
        
        # If still failed, record failure status
        if response_json is None:
            log(f"      [FAILED] Evaluator {eval_name} Round 2c failed: {error_msg}", log_handle)
            return (eval_name, {
                "round2c_status": "failed",
                "round2c_error": error_msg,
                "call_settings": call_settings,
            }, call_settings, False)
        
        # Store call settings in response AFTER validation
        response_json["call_settings"] = call_settings
        
        # ============================================================
        # MANDATORY DEFENSE/ATTACK VALIDATION (NON-NEGOTIABLE)
        # "Consensus is only meaningful after confrontation."
        # ============================================================
        cross_exam = response_json.get("cross_examination", {})
        defense = cross_exam.get("attack_leading_choice", {})
        attack = cross_exam.get("attack_rival_choice", {})
        
        # Check defense is substantive (not just whitespace)
        defense_rebuttal = (defense.get("rebuttal", "") or "").strip()
        if not defense_rebuttal:
            log(f"      [DEFENSE FAIL] Evaluator {eval_name} provided empty rebuttal - schema requires defense", log_handle)
            response_json["round2c_status"] = "failed"
            response_json["round2c_error"] = "empty_defense_rebuttal"
            return (eval_name, response_json, call_settings, False)
        
        # Check attack is substantive (not just whitespace)
        attack_counter = (attack.get("counter", "") or "").strip()
        if not attack_counter:
            log(f"      [ATTACK FAIL] Evaluator {eval_name} provided empty counter-argument - schema requires attack", log_handle)
            response_json["round2c_status"] = "failed"
            response_json["round2c_error"] = "empty_attack_counter"
            return (eval_name, response_json, call_settings, False)
        
        # Success - mark status
        response_json["round2c_status"] = "ok"
        
        # Track participation flags for audit
        response_json["_participation"] = {
            "defense_provided": bool(defense_rebuttal),
            "attack_provided": bool(attack_counter),
            "defense_type": defense.get("rebuttal_type"),
            "attack_target": attack.get("strongest_rival_point_summary", "")[:50],
        }
        
        # NOTE: No final_commit in Round 2c - that comes in Final Commit phase
        leading_choice = response_json.get("best_current_case", {}).get("leading_choice")
        log(f"      [OK] Evaluator {eval_name}: leading={leading_choice} (defense={defense.get('rebuttal_type')}, attack_type={attack.get('counter_type')})", log_handle)
        return (eval_name, response_json, call_settings, True)
    
    # Run all evaluators in parallel for Round 2c
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        future_to_eval = {
            executor.submit(process_single_evaluator_round2c, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        completed_count = 0
        for future in as_completed(future_to_eval):
            eval_name, response_json, call_settings, success = future.result()
            completed_count += 1
            # Always store results, even for skipped/failed (they have round2c_status fields)
            if response_json:
                round2c_results[f"evaluator_{eval_name}"] = response_json
        
        if completed_count < len(evaluator_routers):
            log(f"      [WARNING] Only {completed_count}/{len(evaluator_routers)} evaluators completed in Round 2c", log_handle)
    
    # Compute Round 2c "leading choice" pattern (NOT final - that's in Final Commit phase)
    eval_leading_r2c = {}
    parse_ok_r2c = {}
    for eval_name in EVALUATORS:
        eval_result = round2c_results.get(f"evaluator_{eval_name}")
        if eval_result and eval_result.get("round2c_status") == "ok" and "best_current_case" in eval_result:
            eval_leading_r2c[eval_name] = eval_result["best_current_case"].get("leading_choice")
            parse_ok_r2c[eval_name] = True
        else:
            eval_leading_r2c[eval_name] = None
            parse_ok_r2c[eval_name] = False
    
    # Track leading choices for reference (but NOT final agreement - that comes after Final Commit)
    pattern_leading, majority_leading, unanimous_leading, majority_size_leading, r2c_agreement_metadata = compute_agreement_pattern(eval_leading_r2c, parse_ok_r2c)
    round2c_results["round2c_leading_pattern"] = pattern_leading
    round2c_results["round2c_leading_majority"] = majority_leading
    round2c_results["round2c_leading_unanimous"] = unanimous_leading
    round2c_results["round2c_agreement_metadata"] = r2c_agreement_metadata
    round2c_results["round2c_defense_complete"] = all(parse_ok_r2c.values())
    
    # Add overall round status (explicit, not inferred)
    any_failed = any(
        r.get("round2c_status") in ["failed", "skipped"] 
        for k, r in round2c_results.items() 
        if k.startswith("evaluator_") and isinstance(r, dict)
    )
    round2c_results["round_executed"] = True
    round2c_results["round_status"] = "partial_failure" if any_failed else "ok"
    
    return round2c_results


# ============================================================
# Final Commit Phase - Separate from Defense
# ============================================================
def process_final_commit(
    question_data: dict,
    round1_results: dict,
    round2c_results: dict,
    candidate_options: list,
    synthesis_result: dict,
    evaluator_routers: Dict[str, ProviderRouter],
    final_commit_prompt_template: str,
    final_commit_schema: dict,
    log_handle,
    audit_trail: list = None
) -> dict:
    """
    Process Final Commit Phase - AFTER defense/attack has been validated.
    
    This is the ONLY place where final_choice is determined.
    Epistemic guarantee: "Answer only accepted after surviving representation, attack, and defense."
    """
    question = question_data["question"]
    choices = question_data["choices"]
    
    log(f"  Processing Final Commit Phase for question {question_data['question_id']}", log_handle)
    
    final_commit_results = {
        "evaluator_A": None,
        "evaluator_B": None,
        "evaluator_C": None,
        "evaluator_D": None,
    }
    
    if not round2c_results:
        log(f"      [SKIP] round2c_results is None - cannot proceed to Final Commit", log_handle)
        return final_commit_results
    
    # Check that defense was completed
    if not round2c_results.get("round2c_defense_complete", False):
        log(f"      [SKIP] Defense phase incomplete - cannot proceed to Final Commit", log_handle)
        return final_commit_results
    
    # Build candidate choices text
    candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
    
    # Helper function to process a single evaluator Final Commit
    def process_single_evaluator_final_commit(eval_name: str, router: ProviderRouter) -> Tuple[str, Optional[dict], bool]:
        """Process a single evaluator's final commitment."""
        log(f"    Calling Evaluator {eval_name} (Final Commit)...", log_handle)
        
        # Get this evaluator's Round 2c result (defense phase)
        r2b_result = round2c_results.get(f"evaluator_{eval_name}")
        if not r2b_result:
            log(f"      [SKIP] Evaluator {eval_name} had no Round 2c result", log_handle)
            return (eval_name, None, False)
        
        # Get Round 1 choice
        round1_result = round1_results.get(f"evaluator_{eval_name}")
        round1_choice = round1_result.get("final_choice") if round1_result else "N/A"
        
        # Extract defense phase results (from cross_examination per schema)
        cross_exam = r2b_result.get("cross_examination", {})
        defense = cross_exam.get("attack_leading_choice", {})
        attack = cross_exam.get("attack_rival_choice", {})
        best_current_case = r2b_result.get("best_current_case", {})
        honesty_check = r2b_result.get("honesty_check", {})
        
        leading_choice = best_current_case.get("leading_choice", round1_choice)
        
        # Get attack on this choice from synthesis
        attack_on_yours = "No attack available"
        if synthesis_result:
            arg_recons = synthesis_result.get("argument_reconstructions", {})
            recon_for_choice = arg_recons.get(leading_choice, {})
            attack_arg = recon_for_choice.get("argument_against", {})
            if attack_arg:
                parts = []
                if attack_arg.get("premises"):
                    parts.append("Premises: " + "; ".join(attack_arg["premises"][:3]))
                if attack_arg.get("conclusion"):
                    parts.append("Conclusion: " + attack_arg["conclusion"])
                attack_on_yours = " | ".join(parts) if parts else "No attack available"
        
        full_prompt = final_commit_prompt_template.format(
            question=question,
            candidate_choices_text=candidate_choices_text,
            round1_choice=round1_choice,
            leading_choice_after_defense=leading_choice,
            your_defense_rebuttal=defense.get("rebuttal", "N/A"),
            defense_rebuttal_type=defense.get("rebuttal_type", "N/A"),
            attack_target="rival",  # Schema doesn't track target letter explicitly
            your_attack_counter=attack.get("counter", "N/A"),
            attack_counter_type=attack.get("counter_type", "N/A"),
            acknowledged_weakness=honesty_check.get("acknowledge_strongest_opponent_point", "N/A"),
            attack_on_yours=attack_on_yours
        )
        
        start_time = time.time()
        try:
            result, meta, call_settings = call_evaluator_with_override(
                eval_name, router, "", full_prompt, log_handle, None, None
            )
            
            if audit_trail is not None:
                raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                add_audit_entry(audit_trail, "Final Commit", call_settings.get("model_name", eval_name), "Evaluator", full_prompt, raw_out)
            
            if result is None:
                return (eval_name, None, False)
            
            elapsed = time.time() - start_time
            log(f"      [TIMING] Evaluator {eval_name} (Final Commit): {elapsed:.1f}s", log_handle)
            
            # Parse JSON
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log(f"      [ERROR] Failed to parse JSON from {eval_name}: {e}", log_handle)
                return (eval_name, None, False)
            
            # Normalize and validate schema
            response_json, is_valid, schema_error = normalize_and_validate_final_commit(response_json, final_commit_schema)
            if not is_valid:
                log(f"      [SCHEMA FAIL] Evaluator {eval_name} Final Commit schema validation failed: {schema_error}", log_handle)
                return (eval_name, None, False)
            
            final_choice = response_json.get("final_choice")
            confidence = response_json.get("confidence", 0)
            changed = response_json.get("choice_changed_after_defense", False)
            
            log(f"      [OK] Evaluator {eval_name}: FINAL={final_choice} (conf={confidence}, changed={changed})", log_handle)
            return (eval_name, response_json, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            log(f"      [ERROR] Evaluator {eval_name} Final Commit failed after {elapsed:.1f}s: {e}", log_handle)
            return (eval_name, None, False)
    
    # Run all evaluators in parallel for Final Commit
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        future_to_eval = {
            executor.submit(process_single_evaluator_final_commit, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        completed_count = 0
        for future in as_completed(future_to_eval):
            eval_name, response_json, success = future.result()
            completed_count += 1
            if success and response_json:
                final_commit_results[f"evaluator_{eval_name}"] = response_json
        
        if completed_count < len(evaluator_routers):
            log(f"      [WARNING] Only {completed_count}/{len(evaluator_routers)} evaluators completed Final Commit", log_handle)
    
    # NOW compute final agreement pattern (this is the REAL final choice)
    eval_choices_final = {}
    parse_ok_final = {}
    for eval_name in EVALUATORS:
        eval_result = final_commit_results.get(f"evaluator_{eval_name}")
        if eval_result and "final_choice" in eval_result:
            eval_choices_final[eval_name] = eval_result.get("final_choice")
        else:
            eval_choices_final[eval_name] = None
        parse_ok_final[eval_name] = eval_result is not None
    
    pattern_final, majority_final, unanimous_final, majority_size_final, final_agreement_metadata = compute_agreement_pattern(eval_choices_final, parse_ok_final)
    final_commit_results["final_agreement_pattern"] = pattern_final
    final_commit_results["final_majority_choice"] = majority_final
    final_commit_results["final_unanimous_choice"] = unanimous_final
    final_commit_results["final_majority_size"] = majority_size_final
    final_commit_results["final_agreement_metadata"] = final_agreement_metadata
    # converged if unanimous (any count: unanimous_3, unanimous_4, etc.)
    final_commit_results["converged"] = pattern_final.startswith("unanimous")
    
    # Track choice changes
    changes = 0
    for eval_name in EVALUATORS:
        eval_result = final_commit_results.get(f"evaluator_{eval_name}")
        if eval_result and eval_result.get("choice_changed_after_defense", False):
            changes += 1
    final_commit_results["evaluators_changed_after_defense"] = changes
    
    return final_commit_results


# ============================================================
# Round 3: Unanimous Stress Test
# ============================================================
def process_round3_stress_test(
    question_data: dict,
    round1_results: dict,
    unanimous_choice: str,
    synthesis_result: dict,
    evaluator_routers: Dict[str, ProviderRouter],
    stress_test_prompt_template: str,
    stress_test_schema: dict,
    log_handle,
    audit_trail: list = None
) -> dict:
    """Process Round 3: Unanimous Stress Test."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    log(f"  Processing Round 3 (Unanimous Stress Test) for choice {unanimous_choice}", log_handle)
    
    stress_test_results = {}
    
    if not synthesis_result:
        log(f"      [SKIP] synthesis_result is None - skipping Round 3", log_handle)
        return stress_test_results
        
    # Extract reconstructions and attacks from synthesis
    argument_reconstructions = synthesis_result.get("argument_reconstructions", {})
    recon_for_unanimous = argument_reconstructions.get(unanimous_choice, {})
    
    # Helper function to format argument reconstruction
    def format_argument_reconstruction(arg_obj: dict) -> str:
        if not arg_obj:
            return "No reconstruction available"
        parts = []
        premises = arg_obj.get("premises", [])
        if premises:
            parts.append("PREMISES:")
            for p in premises:
                parts.append(f"  - {p}")
        inference_steps = arg_obj.get("inference_steps", [])
        if inference_steps:
            parts.append("\nINFERENCE STEPS:")
            for i, step in enumerate(inference_steps, 1):
                parts.append(f"  {i}. {step}")
        conclusion = arg_obj.get("conclusion", "")
        if conclusion:
            parts.append(f"\nCONCLUSION: {conclusion}")
        return "\n".join(parts) if parts else "No reconstruction available"

    reconstruction_for = format_argument_reconstruction(recon_for_unanimous.get("argument_for", {}))
    attack_on_yours = format_argument_reconstruction(recon_for_unanimous.get("argument_against", {}))

    # Helper function to process a single evaluator stress test
    # Per spec: Stress test failures are DIAGNOSTIC ONLY - they don't corrupt the pipeline or change the final answer
    def process_single_evaluator_stress_test(eval_name: str, router: ProviderRouter) -> Tuple[str, dict, bool]:
        """Returns (eval_name, result_dict, success). result_dict always has stress_test_status."""
        log(f"    Stress testing for Evaluator {eval_name}...", log_handle)
        
        # Get target for attribution
        target = router.targets[0] if router.targets else None
        
        full_prompt = stress_test_prompt_template.format(
            question=question,
            choice_a=choices.get("A", ""),
            choice_b=choices.get("B", ""),
            choice_c=choices.get("C", ""),
            choice_d=choices.get("D", ""),
            unanimous_answer=unanimous_choice,
            reconstruction_for=reconstruction_for,
            attack_on_yours=attack_on_yours
        )
        
        start_time = time.time()
        try:
            result, meta = router.call_json(
                system_prompt="",
                user_prompt=full_prompt,
                schema_validate_fn=None,
            )
            
            # Record audit entry if requested
            if audit_trail is not None:
                raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                add_audit_entry(audit_trail, "Round 3", target.name if target else eval_name, "Evaluator", full_prompt, raw_out)
            
            elapsed = time.time() - start_time
            log(f"      [TIMING] Evaluator {eval_name} (Round 3 Stress Test): {elapsed:.1f}s", log_handle)
            
            # Check for empty output (e.g., google_empty_output)
            if result is None or (meta and meta.get("error")):
                error_type = "empty_output"
                if meta:
                    error_info = meta.get("error", "") or meta.get("raw", "")
                    if "empty" in str(error_info).lower() or not error_info:
                        error_type = f"{target.provider if target else 'unknown'}_empty_output"
                log(f"      [STRESS TEST FAIL] Evaluator {eval_name}: {error_type} (diagnostic only)", log_handle)
                return (eval_name, {
                    "stress_test_status": "failed",
                    "stress_test_error": error_type,
                    "can_break": None,  # Unknown due to failure
                    "failure_mode": None,
                    "minimal_premise_that_fails": None
                }, False)
            
            # Parse JSON response
            response_json = None
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log(f"      [STRESS TEST FAIL] Evaluator {eval_name}: json_parse_error (diagnostic only)", log_handle)
                return (eval_name, {
                    "stress_test_status": "failed",
                    "stress_test_error": f"json_parse_error: {str(e)[:100]}",
                    "can_break": None,
                    "failure_mode": None,
                    "minimal_premise_that_fails": None
                }, False)
            
            # DEFENSIVE: Normalize null values for optional fields
            # Models sometimes return null for failure_mode/minimal_premise_that_fails
            if response_json.get("failure_mode") is None:
                response_json["failure_mode"] = "none" if not response_json.get("can_break", False) else "unspecified"
            if response_json.get("minimal_premise_that_fails") is None:
                response_json["minimal_premise_that_fails"] = "N/A - cannot break" if not response_json.get("can_break", False) else "Not specified by model"
            
            # Normalize and validate against schema
            response_json, is_valid, schema_error = normalize_and_validate_round3(response_json, stress_test_schema)
            if not is_valid:
                log(f"      [STRESS TEST FAIL] Evaluator {eval_name}: schema_validation_error (diagnostic only)", log_handle)
                return (eval_name, {
                    "stress_test_status": "failed",
                    "stress_test_error": f"schema_validation_error: {schema_error[:100]}",
                    "can_break": None,
                    "failure_mode": None,
                    "minimal_premise_that_fails": None
                }, False)
            
            # Success - add status marker
            response_json["stress_test_status"] = "success"
            can_break = response_json.get("can_break", False)
            log(f"      [STRESS TEST] Evaluator {eval_name}: can_break={can_break}", log_handle)
            
            return (eval_name, response_json, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_str = str(e)
            # Classify error type for diagnostic
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                error_type = "timeout"
            elif "quota" in error_str.lower() or "rate" in error_str.lower():
                error_type = "rate_limit"
            else:
                error_type = f"exception: {error_str[:80]}"
            log(f"      [STRESS TEST FAIL] Evaluator {eval_name}: {error_type} (diagnostic only, {elapsed:.1f}s)", log_handle)
            return (eval_name, {
                "stress_test_status": "failed",
                "stress_test_error": error_type,
                "can_break": None,
                "failure_mode": None,
                "minimal_premise_that_fails": None
            }, False)
    
    # Process all evaluators in parallel
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        futures = {
            executor.submit(process_single_evaluator_stress_test, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        any_can_break = False
        successful_count = 0
        failed_count = 0
        for future in as_completed(futures):
            eval_name, response_dict, success = future.result()
            # ALWAYS store the result (success or failure) - per spec: failures are diagnostic
            stress_test_results[f"evaluator_{eval_name}"] = response_dict
            if success:
                successful_count += 1
                if response_dict.get("can_break", False):
                    any_can_break = True
            else:
                failed_count += 1
    
    # Track stress test metadata
    stress_test_results["successful_evaluators"] = successful_count
    stress_test_results["failed_evaluators"] = failed_count
    stress_test_results["any_can_break"] = any_can_break
    
    # Robustness classification (only based on successful evaluators)
    # Per spec: failures are diagnostic only - don't change final answer
    if failed_count == len(EVALUATORS):
        stress_test_results["robustness"] = "UNKNOWN"  # All failed - cannot determine
        stress_test_results["robustness_note"] = "All evaluators failed stress test - robustness undetermined"
    elif any_can_break:
        stress_test_results["robustness"] = "FRAGILE"
    else:
        stress_test_results["robustness"] = "ROBUST"
    
    return stress_test_results

# ============================================================
# Round 3: Proof Challenge Round (Surgical Attacks)
# ============================================================
def process_round3_proof_challenge(
    question_data: dict,
    round2c_results: dict,
    candidate_options: list,
    synthesis_result: dict,
    evaluator_routers: Dict[str, ProviderRouter],
    round3_prompt_template: str,
    round3_schema: dict,
    log_handle
) -> dict:
    """Process Round 3: Each evaluator provides one surgical kill-shot against one alternative."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    log(f"  Processing Round 3 (Proof Challenge Round)...", log_handle)
    
    round3_results = {
        "evaluator_A": None,
        "evaluator_B": None,
        "evaluator_C": None,
        "evaluator_D": None,
    }
    
    # Build candidate choices text
    candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
    
    # Get proof ledger from synthesis
    proof_ledger = synthesis_result.get("proof_ledger", {})
    proof_ledger_json = json.dumps(proof_ledger, indent=2)
    
    # Helper function to process a single evaluator Round 3 (for parallel execution)
    def process_single_evaluator_round3(eval_name: str, router: ProviderRouter) -> Tuple[str, Optional[dict], bool]:
        """Process a single evaluator Round 3. Returns (eval_name, response_json, success)."""
        log(f"    Calling Evaluator {eval_name} (Round 3)...", log_handle)
        
        # Attribution logging (before call)
        target = router.targets[0] if router.targets else None
        if target:
            log(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, provider={target.provider}, round=R3, timeout_sec={target.timeout_sec}", log_handle)
        
        # Get this evaluator's Round 2c result (or Round 1 if Round 2c didn't run)
        eval_result_r2c = round2c_results.get(f"evaluator_{eval_name}")
        if not eval_result_r2c:
            log(f"      [SKIP] Evaluator {eval_name} had no Round 2c result", log_handle)
            return (eval_name, None, False)
        
        # Extract final_choice from final_commit
        final_commit = eval_result_r2c.get("final_commit", {})
        current_choice = final_commit.get("final_choice", "")
        if not current_choice or current_choice == "ABSTAIN":
            log(f"      [SKIP] Evaluator {eval_name} had no valid choice", log_handle)
            return (eval_name, None, False)
        
        # Build prompt
        full_prompt = round3_prompt_template.format(
            question=question,
            candidate_choices_text=candidate_choices_text,
            current_choice=current_choice,
            proof_ledger_json=proof_ledger_json
        )
        
        start_time = time.time()
        try:
            result, meta = router.call_json(
                system_prompt="",
                user_prompt=full_prompt,
                schema_validate_fn=None,
            )
            elapsed = time.time() - start_time
            log(f"      [TIMING] Evaluator {eval_name} (Round 3): {elapsed:.1f}s", log_handle)
            
            # Parse JSON response
            response_json = None
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log(f"      [ERROR] Failed to parse Round 3 JSON for {eval_name}: {e}", log_handle)
                return (eval_name, None, False)
            
            # Normalize and validate against schema
            response_json, is_valid, schema_error = normalize_and_validate_round3(response_json, round3_schema)
            if not is_valid:
                log(f"      [ERROR] Round 3 schema validation failed for {eval_name}: {schema_error}", log_handle)
                return (eval_name, None, False)
            
            # Validate that target_alternative differs from current_choice
            target_alt = response_json.get("target_alternative", "")
            if target_alt == current_choice:
                log(f"      [ERROR] Evaluator {eval_name} attacked their own choice - invalid", log_handle)
                return (eval_name, None, False)
            
            kill_shot = response_json.get("kill_shot", {})
            kill_shot_type = kill_shot.get("type", "cannot_falsify")
            if kill_shot_type == "cannot_falsify":
                log(f"      [ERROR] Evaluator {eval_name} provided no kill-shot (type=none)", log_handle)
                return (eval_name, None, False)
            
            log(f"      [OK] Evaluator {eval_name} (Round 3): attacking {target_alt} with {kill_shot_type}", log_handle)
            return (eval_name, response_json, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            check_quota_error(error_msg, f"Evaluator {eval_name} (Round 3)", log_handle)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                log(f"      [ERROR] Evaluator {eval_name} (Round 3) timed out after {elapsed:.1f}s: {e}", log_handle)
            else:
                log(f"      [ERROR] Evaluator {eval_name} (Round 3) failed after {elapsed:.1f}s: {e}", log_handle)
            return (eval_name, None, False)
    
    # Process all evaluators in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(process_single_evaluator_round3, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        for future in as_completed(futures):
            eval_name, response_json, success = future.result()
            if success and response_json:
                round3_results[f"evaluator_{eval_name}"] = response_json
    
    return round3_results

# ============================================================
# Final Disposition Logic
# ============================================================
# ============================================================
# Auditor (Post-Round 2c Structural Check)
# ============================================================
def call_auditor(
    question_data: dict,
    round1_results: dict,
    round2c_results: Optional[dict],
    synthesis_result: Optional[dict],
    auditor_router: ProviderRouter,
    auditor_prompt_template: str,
    auditor_schema: dict,
    candidate_options: list,
    log_handle,
    final_commit_results: Optional[dict] = None,
    audit_trail: list = None
) -> Optional[dict]:
    """Call Auditor to validate logical consistency and detect incompatible reasoning."""
    question = question_data["question"]
    choices = question_data["choices"]
    
    # CRITICAL: Check if any evaluator failed - if so, Auditor must ABSTAIN
    if round2c_results:
        # Check Round 2c results
        eval_a = round2c_results.get("evaluator_A")
        eval_b = round2c_results.get("evaluator_B")
        eval_c = round2c_results.get("evaluator_C")
        eval_d = round2c_results.get("evaluator_D")
        if not eval_a or not eval_b or not eval_c or not eval_d:
            log(f"      [AUDITOR] One or more evaluators failed in Round 2c - automatically ABSTAIN", log_handle)
            return {
                "decision": "ABSTAIN",
                "justification": "One or more evaluators failed to provide a response in Round 2c. Cannot validate reasoning compatibility without all four evaluators.",
                "reasoning_compatibility": "unknown",
                "mutually_exclusive_assumptions": []
            }
    else:
        # Check Round 1 results
        parse_ok_a = round1_results.get("parse_ok_A", False)
        parse_ok_b = round1_results.get("parse_ok_B", False)
        parse_ok_c = round1_results.get("parse_ok_C", False)
        eval_a = round1_results.get("evaluator_A")
        eval_b = round1_results.get("evaluator_B")
        eval_c = round1_results.get("evaluator_C")
        
        if not parse_ok_a or not parse_ok_b or not parse_ok_c:
            failed_evals = []
            if not parse_ok_a or not eval_a:
                failed_evals.append("A")
            if not parse_ok_b or not eval_b:
                failed_evals.append("B")
            if not parse_ok_c or not eval_c:
                failed_evals.append("C")
            
            log(f"      [AUDITOR] Evaluator(s) {', '.join(failed_evals)} failed in Round 1 - automatically ABSTAIN", log_handle)
            return {
                "decision": "ABSTAIN",
                "justification": f"Evaluator(s) {', '.join(failed_evals)} failed to provide a valid response in Round 1. Cannot validate reasoning compatibility without all three evaluators.",
                "reasoning_compatibility": "unknown",
                "mutually_exclusive_assumptions": []
            }
    
    # Build candidate choices text
    candidate_choices_text = ""
    for opt in candidate_options:
        candidate_choices_text += f"{opt}: {choices.get(opt, '')}\n"
    
    # Get evaluator choices from Final Commit (or Round 1 if Final Commit didn't run)
    # Support 4 evaluators (A, B, C, D)
    choices_dict = {}
    
    if final_commit_results:
        # Use Final Commit results (post-defense commitments)
        for eval_name in EVALUATORS:
            eval_result = final_commit_results.get(f"evaluator_{eval_name}")
            if eval_result:
                choices_dict[eval_name] = eval_result.get("final_choice", "N/A")
            else:
                choices_dict[eval_name] = "N/A"
    elif round2c_results:
        # Legacy fallback: try to get choices from round2c if final_commit not available
        for eval_name in EVALUATORS:
            eval_result = round2c_results.get(f"evaluator_{eval_name}")
            if eval_result:
                if "final_commit" in eval_result:
                    # Old structure: final_commit was inside round2c
                    final_commit = eval_result.get("final_commit", {})
                    choices_dict[eval_name] = final_commit.get("final_choice", "N/A")
                else:
                    # Fallback for legacy data
                    choices_dict[eval_name] = eval_result.get("final_choice", "N/A")
            else:
                choices_dict[eval_name] = "N/A"
    else:
        for eval_name in EVALUATORS:
            eval_result = round1_results.get(f"evaluator_{eval_name}")
            if eval_result:
                choices_dict[eval_name] = eval_result.get("final_choice", "N/A")
            else:
                choices_dict[eval_name] = "N/A"
    
    # Extract choices for backward compatibility with prompt (A, B, C)
    choice_a = choices_dict.get("A", "N/A")
    choice_b = choices_dict.get("B", "N/A")
    choice_c = choices_dict.get("C", "N/A")
    choice_d = choices_dict.get("D", "N/A")
    
    # CRITICAL: Check for disagreement - if evaluators don't all agree, Auditor must ABSTAIN
    choices_set = set(choices_dict.values())
    choices_set.discard("N/A")  # Remove N/A if any evaluator failed
    choices_set.discard("ABSTAIN")  # Remove ABSTAIN from consideration
    
    if len(choices_set) > 1:
        # Disagreement detected - automatically ABSTAIN
        log(f"      [AUDITOR] Disagreement detected (choices: {choices_set}) - automatically ABSTAIN", log_handle)
        return {
            "decision": "ABSTAIN",
            "justification": f"Evaluators disagree on final answer (choices: {choices_dict}). Cannot validate reasoning compatibility without consensus.",
            "reasoning_compatibility": "unknown",
            "mutually_exclusive_assumptions": []
        }
    
    # Build synthesis JSON
    synthesis_json = "{}"
    if synthesis_result:
        synthesis_json = json.dumps(synthesis_result, indent=2)
    
    # Build prompt from template
    full_prompt = auditor_prompt_template.format(
        question=question,
        candidate_choices_text=candidate_choices_text.strip(),
        choice_a=choice_a,
        choice_b=choice_b,
        choice_c=choice_c,
        synthesis_json=synthesis_json
    )
    
    log("    Calling Auditor (post-Round 2c)...", log_handle)
    start_time = time.time()
    
    # Attribution logging
    auditor_target = auditor_router.targets[0] if auditor_router.targets else None
    if auditor_target:
        log(f"      [ATTRIBUTION] Auditor - model={auditor_target.name}, provider={auditor_target.provider}, round=Post-R2c, timeout_sec={auditor_target.timeout_sec}", log_handle)
    
    try:
        result, meta = auditor_router.call_json(
            system_prompt="",
            user_prompt=full_prompt,
            schema_validate_fn=None,
        )
        
        # Record audit entry if requested
        if audit_trail is not None:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry(audit_trail, "Auditor", auditor_target.name if auditor_target else "Auditor", "Auditor", full_prompt, raw_out)
            
        elapsed = time.time() - start_time
        log(f"      [TIMING] Auditor: {elapsed:.1f}s", log_handle)
        
        # Parse JSON response
        auditor_result = None
        try:
            if isinstance(result, dict):
                auditor_result = result
            else:
                raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    auditor_result = json.loads(json_match.group(1))
                else:
                    auditor_result = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            elapsed = time.time() - start_time
            log(f"      [ERROR] Failed to parse Auditor JSON after {elapsed:.1f}s: {e}", log_handle)
            return None
        
        # Normalize and validate against schema
        auditor_result, is_valid, schema_error = normalize_and_validate_auditor(auditor_result, auditor_schema)
        if not is_valid:
            log(f"      [ERROR] Auditor schema validation failed: {schema_error}", log_handle)
            return None
        
        log(f"      [OK] Auditor: {auditor_result.get('decision', 'UNKNOWN')} - {auditor_result.get('reasoning_compatibility', 'unknown')}", log_handle)
        return auditor_result
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        check_quota_error(error_msg, "Auditor", log_handle)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            log(f"      [ERROR] Auditor timed out after {elapsed:.1f}s: {e}", log_handle)
        else:
            log(f"      [ERROR] Auditor failed after {elapsed:.1f}s: {e}", log_handle)
        return None

def compute_final_disposition(
    round1_results: dict,
    round2c_results: Optional[dict],
    grok_analysis: Optional[dict],
    auditor_result: Optional[dict],
    synthesis_result: Optional[dict] = None,
    candidate_options: Optional[list] = None,
    unanimity_challenge_result: Optional[dict] = None,
    round3_results: Optional[dict] = None,
    final_commit_results: Optional[dict] = None
) -> str:
    """
    Compute final disposition after Final Commit phase, Round 3, and Auditor.
    Returns: AUTO_ACCEPT, ASSERT_QUALIFIED, FLAG_FALSE_CONSENSUS, FLAG_EPISTEMIC_BOUNDARY, UNPROVEN_CONVERGENCE, NEEDS_REVIEW, ABSTAIN
    """
    # Get agreement pattern from Final Commit (preferred) or Round 1
    if final_commit_results:
        r2_pattern = final_commit_results.get("final_agreement_pattern", "unknown")
        eval_results = {}
        for eval_name in EVALUATORS:
            eval_results[eval_name] = final_commit_results.get(f"evaluator_{eval_name}")
    else:
        r2_pattern = round1_results.get("agreement_pattern", "unknown")
        eval_results = {}
        for eval_name in EVALUATORS:
            eval_results[eval_name] = round1_results.get(f"evaluator_{eval_name}")
    
    # Check if all evaluators agree (supports 4 evaluators)
    choices = set()
    for eval_result in eval_results.values():
        if eval_result:
            # Extract final_choice from Final Commit results or Round 1
            final_choice = eval_result.get("final_choice")
            if final_choice and final_choice != "ABSTAIN":
                choices.add(final_choice)
    
    # Check agreement pattern (supports unanimous_N patterns)
    all_agree = len(choices) == 1 and r2_pattern.startswith("unanimous")
    unanimous_choice = list(choices)[0] if len(choices) == 1 else None
    
    # Check Auditor decision
    auditor_decision = auditor_result.get("decision", "ACCEPT") if auditor_result else "ACCEPT"
    reasoning_compatibility = auditor_result.get("reasoning_compatibility", "unknown") if auditor_result else "unknown"
    
    # Check Grok incompatibility
    incompatibility_detected = False
    if grok_analysis:
        incompatibility_detected = grok_analysis.get("incompatibility_detected", False)
        reasoning_relation = grok_analysis.get("reasoning_relation", "UNKNOWN")
        if reasoning_relation in ["INCOMPATIBLE", "MIXED"]:
            incompatibility_detected = True
    
    # Check Round 3 result (if present)
    stress_test_fragile = False
    if round3_results:
        if round3_results.get("robustness") == "FRAGILE" or round3_results.get("any_can_break", False):
            stress_test_fragile = True
    
    # Check for elimination evidence from Round 1 proof_attempts
    # If unanimous and all other options have elimination proofs, we have strong evidence
    has_elimination_evidence = False
    if unanimous_choice and round1_results:
        other_options = [opt for opt in ["A", "B", "C", "D"] if opt != unanimous_choice]
        eliminated_options = set()
        
        for eval_name in EVALUATORS:
            eval_data = round1_results.get(f"evaluator_{eval_name}", {})
            proof_attempt = eval_data.get("proof_attempt", {})
            for opt in other_options:
                if opt in proof_attempt:
                    proof = proof_attempt[opt]
                    # Check if it's an elimination-type proof
                    proof_type = proof.get("type", "")
                    if proof_type in ["contradiction", "impossibility", "constraint_violation", "mechanism_impossibility"]:
                        eliminated_options.add(opt)
        
        # If all other options have at least one elimination proof
        has_elimination_evidence = (eliminated_options == set(other_options))
    
    # Decision logic:
    
    # 0. CRITICAL: If Auditor abstained due to pipeline failure, treat as NEEDS_REVIEW not FLAG_FALSE_CONSENSUS
    #    This handles cases where Synthesizer failed (e.g., 'E' bug) and downstream rounds were skipped
    if auditor_decision == "ABSTAIN":
        auditor_justification = auditor_result.get("justification", "") if auditor_result else ""
        if "failed" in auditor_justification.lower() or "Round 2c" in auditor_justification:
            # Pipeline failure - don't use incompatibility_detected from Grok to determine disposition
            # because we couldn't verify it through the full pipeline
            if all_agree:
                # All evaluators agreed, but we couldn't verify reasoning compatibility
                # Use UNPROVEN_CONVERGENCE rather than FLAG_FALSE_CONSENSUS
                return "UNPROVEN_CONVERGENCE"
            else:
                return "NEEDS_REVIEW"
        else:
            # Auditor abstained for substantive reasons (not pipeline failure)
            return "FLAG_EPISTEMIC_BOUNDARY"
    
    # 1. If all agree AND reasoning is compatible AND Round 3 says ROBUST → AUTO_ACCEPT
    if all_agree and (reasoning_compatibility == "compatible" or not incompatibility_detected) and not stress_test_fragile:
        return "AUTO_ACCEPT"
    
    # 2. If all agree AND FRAGILE BUT has elimination evidence → ASSERT_QUALIFIED
    #    (Can assert with qualifications noting the fragility)
    if all_agree and stress_test_fragile and has_elimination_evidence:
        return "ASSERT_QUALIFIED"
    
    # 3. If all agree BUT Round 3 says FRAGILE and no elimination evidence → FLAG_EPISTEMIC_BOUNDARY
    if all_agree and stress_test_fragile:
        return "FLAG_EPISTEMIC_BOUNDARY"
    
    # 4. If all agree BUT reasoning is incompatible (and Auditor didn't abstain due to failure) → FLAG_FALSE_CONSENSUS
    if all_agree and (reasoning_compatibility == "incompatible" or incompatibility_detected):
        return "FLAG_FALSE_CONSENSUS"
    
    # 5. If disagreement persists after Round 2c → SPLIT_PERSISTS
    if not all_agree:
        if round2c_results:
            return "SPLIT_PERSISTS"
        else:
            return "NEEDS_REVIEW"
    
    # Fallback
    return "NEEDS_REVIEW"

# ============================================================
# Metrics — imported from cam.core.metrics (fallback definitions removed)
# ============================================================

# ============================================================
# Main Function
# ============================================================
def run():
    """Main runner function."""
    parser = argparse.ArgumentParser(description="GPQA CAM Runner")
    parser.add_argument("--dataset", type=str, default="gpqa", help="Dataset name (default: gpqa)")
    parser.add_argument("--split", type=str, default="train", help="Dataset split (train/test/val)")
    parser.add_argument("--n", type=int, default=None, help="Sample size (default: full if ≤500, else 500)")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed")
    parser.add_argument("--replay_ids", type=str, default=None, help="JSON file with question IDs to replay")
    parser.add_argument("--resume", type=int, default=None, help="Resume a specific run number")
    parser.add_argument("--round", type=str, choices=["1", "2", "both"], default="both", help="Which round to run")
    parser.add_argument("--allow_abstain", type=str, choices=["true", "false"], default="false", help="Allow evaluators to abstain (default: false)")
    parser.add_argument("--run_dir", type=str, default=None, help="Optional run directory (else infer from cwd/run numbering)")
    parser.add_argument("--models_config", type=str, default=None, help="Optional JSON file to override model configuration")
    parser.add_argument("--single_question_id", type=str, default=None, help="Run on a single question ID (overrides --n and --replay_ids)")
    parser.add_argument("--enable_unanimity_challenge", action="store_true", help="Enable conditional Unanimity Challenge Round for fragile unanimous agreements")
    parser.add_argument("--allow_split_fallback", action="store_true", help="Allow fallback to different split if requested split not available")
    
    # Rule Library flags (CAM v2.5.4) - ALL RULES ON BY DEFAULT
    parser.add_argument("--no-core-rules", action="store_true", help="Disable Core Rule Library (default: ON, applies to all domains)")
    parser.add_argument("--no-physics-rules", action="store_true", help="Disable Physics Rule Library (default: ON, physics domain only)")
    parser.add_argument("--no-chemistry-rules", action="store_true", help="Disable Chemistry Rule Library (default: ON, chemistry domain only)")

    args = parser.parse_args()

    # Process Rule Library flags (CAM v2.5.4) - ALL ON BY DEFAULT
    global ENABLE_CORE_RULES, ENABLE_PHYSICS_RULES, ENABLE_CHEMISTRY_RULES
    if args.no_core_rules:
        ENABLE_CORE_RULES = False
        print("[RULES] Core rules DISABLED via --no-core-rules")
    if args.no_physics_rules:
        ENABLE_PHYSICS_RULES = False
        print("[RULES] Physics rules DISABLED via --no-physics-rules")
    if args.no_chemistry_rules:
        ENABLE_CHEMISTRY_RULES = False
        print("[RULES] Chemistry rules DISABLED via --no-chemistry-rules")

    # Log which rules are enabled
    enabled_rules = []
    if ENABLE_CORE_RULES: enabled_rules.append("Core (all domains)")
    if ENABLE_PHYSICS_RULES: enabled_rules.append("Physics")
    if ENABLE_CHEMISTRY_RULES: enabled_rules.append("Chemistry")
    print(f"[RULES] Enabled rule libraries: {', '.join(enabled_rules) if enabled_rules else 'NONE'}")
    if PIPELINE_GUARDS_AVAILABLE:
        print(f"[GUARDS] Pipeline Guards: {PIPELINE_GUARDS_STATUS}")
    
    # Create run context
    ctx = RunContext(
        runs_dir=GPQA_ROOT / "Runs",
        run_label="GPQA Run",
        resume_run=args.resume,
    )
    # Adapter-level resource paths
    schemas_dir = ADAPTER_DIR / "schemas"
    prompts_dir = ADAPTER_DIR / "prompts"

    # Setup logging
    log_file = ctx.logs_dir / "run_log.txt"
    log_mode = "a" if args.resume else "w"
    log_handle = open(log_file, log_mode, encoding="utf-8")
    
    log("=" * 70, log_handle)
    log("GPQA CAM Runner", log_handle)
    log("=" * 70, log_handle)
    log(f"Run Number: {ctx.run_number}", log_handle)
    log(f"Run Directory: {ctx.run_dir}", log_handle)
    
    # Process allow_abstain argument
    allow_abstain = args.allow_abstain.lower() == "true"
    
    # Load prompts
    round1_prompt_path = prompts_dir / "round1_evaluator.txt"
    grok_analyzer_prompt_path = prompts_dir / "grok_analyzer.txt"
    synthesizer_prompt_path = prompts_dir / "synthesizer.txt"
    round1_75_fidelity_prompt_path = prompts_dir / "round1_75_fidelity_check.txt"
    round2a_prompt_path = prompts_dir / "round2a_representation_check.txt"
    round2c_prompt_path = prompts_dir / "round2c_evaluator.txt"
    final_commit_prompt_path = prompts_dir / "final_commit.txt"
    round3_prompt_path = prompts_dir / "round3_stress_test.txt"
    auditor_prompt_path = prompts_dir / "auditor.txt"
    unanimity_challenge_prompt_path = prompts_dir / "unanimity_challenge.txt"
    
    # Check if critical prompts exist
    critical_prompts = [
        (round1_prompt_path, "Round 1"),
        (grok_analyzer_prompt_path, "Grok analyzer"),
        (synthesizer_prompt_path, "Synthesizer"),
        (round2a_prompt_path, "Round 2a representation check"),
        (round2c_prompt_path, "Round 2c"),
        (final_commit_prompt_path, "Final Commit"),
        (round3_prompt_path, "Round 3 stress test"),
        (auditor_prompt_path, "Auditor"),
        (unanimity_challenge_prompt_path, "Unanimity challenge")
    ]
    
    for path, name in critical_prompts:
        if not path.exists():
            log(f"ERROR: {name} prompt not found at {path}", log_handle)
            sys.exit(1)
    
    round1_prompt = round1_prompt_path.read_text(encoding="utf-8")
    grok_analyzer_prompt = grok_analyzer_prompt_path.read_text(encoding="utf-8")
    synthesizer_prompt = synthesizer_prompt_path.read_text(encoding="utf-8")
    round1_75_fidelity_prompt = round1_75_fidelity_prompt_path.read_text(encoding="utf-8") if round1_75_fidelity_prompt_path.exists() else ""
    round2a_prompt = round2a_prompt_path.read_text(encoding="utf-8")
    round2c_prompt = round2c_prompt_path.read_text(encoding="utf-8")
    final_commit_prompt = final_commit_prompt_path.read_text(encoding="utf-8")
    round3_prompt = round3_prompt_path.read_text(encoding="utf-8")
    auditor_prompt = auditor_prompt_path.read_text(encoding="utf-8")
    unanimity_challenge_prompt = unanimity_challenge_prompt_path.read_text(encoding="utf-8")
    
    # Compute hashes
    round1_prompt_hash = get_prompt_hash(round1_prompt_path)
    grok_analyzer_prompt_hash = get_prompt_hash(grok_analyzer_prompt_path)
    synthesizer_prompt_hash = get_prompt_hash(synthesizer_prompt_path)
    round2a_prompt_hash = get_prompt_hash(round2a_prompt_path)
    round2c_prompt_hash = get_prompt_hash(round2c_prompt_path)
    final_commit_prompt_hash = get_prompt_hash(final_commit_prompt_path)
    round3_prompt_hash = get_prompt_hash(round3_prompt_path)
    auditor_prompt_hash = get_prompt_hash(auditor_prompt_path)
    unanimity_challenge_prompt_hash = get_prompt_hash(unanimity_challenge_prompt_path)
    
    log(f"Round 1 prompt: {round1_prompt_path.name} (SHA256: {round1_prompt_hash[:16]}...)", log_handle)
    log(f"Grok analyzer prompt: {grok_analyzer_prompt_path.name} (SHA256: {grok_analyzer_prompt_hash[:16]}...)", log_handle)
    log(f"Synthesizer prompt: {synthesizer_prompt_path.name} (SHA256: {synthesizer_prompt_hash[:16]}...)", log_handle)
    log(f"Round 2a representation check prompt: {round2a_prompt_path.name} (SHA256: {round2a_prompt_hash[:16]}...)", log_handle)
    log(f"Round 2c prompt: {round2c_prompt_path.name} (SHA256: {round2c_prompt_hash[:16]}...)", log_handle)
    log(f"Final Commit prompt: {final_commit_prompt_path.name} (SHA256: {final_commit_prompt_hash[:16]}...)", log_handle)
    log(f"Round 3 stress test prompt: {round3_prompt_path.name} (SHA256: {round3_prompt_hash[:16]}...)", log_handle)
    
    if args.enable_unanimity_challenge:
        log(f"Unanimity challenge prompt: {unanimity_challenge_prompt_path.name} (SHA256: {unanimity_challenge_prompt_hash[:16]}...) [ENABLED]", log_handle)
    
    # Load schemas
    round1_schema_path = schemas_dir / "round1_schema.json"
    grok_analyzer_schema_path = schemas_dir / "grok_analyzer_schema.json"
    synthesizer_schema_path = schemas_dir / "synthesizer_schema.json"
    round2a_schema_path = schemas_dir / "round2a_schema.json"
    round2c_schema_path = schemas_dir / "round2c_schema.json"
    final_commit_schema_path = schemas_dir / "final_commit_schema.json"
    round3_schema_path = schemas_dir / "round3_stress_test_schema.json"
    auditor_schema_path = schemas_dir / "auditor_schema.json"
    unanimity_challenge_schema_path = schemas_dir / "unanimity_challenge_schema.json"
    
    schema_paths = [
        (round1_schema_path, "Round 1"),
        (grok_analyzer_schema_path, "Grok analyzer"),
        (synthesizer_schema_path, "Synthesizer"),
        (round2a_schema_path, "Round 2a"),
        (round2c_schema_path, "Round 2c"),
        (final_commit_schema_path, "Final Commit"),
        (round3_schema_path, "Round 3"),
        (auditor_schema_path, "Auditor")
    ]
    
    for path, name in schema_paths:
        if not path.exists():
            log(f"ERROR: {name} schema not found at {path}", log_handle)
            sys.exit(1)
            
    round1_schema = load_schema(round1_schema_path)
    grok_analyzer_schema = load_schema(grok_analyzer_schema_path)
    synthesizer_schema = load_schema(synthesizer_schema_path)
    round2a_schema = load_schema(round2a_schema_path)
    round2c_schema = load_schema(round2c_schema_path)
    final_commit_schema = load_schema(final_commit_schema_path)
    round3_schema = load_schema(round3_schema_path)
    auditor_schema = load_schema(auditor_schema_path)

    # V2 Pipeline: Load v2 prompts and schemas if available
    use_v2_pipeline = V2_AVAILABLE
    round2c_v2_prompt = None
    round2d_prompt = None
    final_commit_v2_prompt = None
    round2c_v2_schema = None
    round2d_schema = None
    final_commit_v2_schema = None
    
    if use_v2_pipeline:
        round2c_v2_prompt_path = prompts_dir / "round2c_evaluator_v2.txt"
        round2d_prompt_path = prompts_dir / "round2d_resurrection.txt"
        final_commit_v2_prompt_path = prompts_dir / "final_commit_v2.txt"
        
        v2_prompts_exist = all(p.exists() for p in [round2c_v2_prompt_path, round2d_prompt_path, final_commit_v2_prompt_path])
        
        if v2_prompts_exist:
            round2c_v2_prompt = round2c_v2_prompt_path.read_text(encoding="utf-8")
            round2d_prompt = round2d_prompt_path.read_text(encoding="utf-8")
            final_commit_v2_prompt = final_commit_v2_prompt_path.read_text(encoding="utf-8")
            log(f"V2 prompts loaded: round2c_v2, round2d_resurrection, final_commit_v2", log_handle)
            
            round2c_v2_schema_path = schemas_dir / "round2c_schema_v2.json"
            round2d_schema_path = schemas_dir / "round2d_resurrection_schema.json"
            final_commit_v2_schema_path = schemas_dir / "final_commit_schema_v2.json"
            
            if all(p.exists() for p in [round2c_v2_schema_path, round2d_schema_path, final_commit_v2_schema_path]):
                round2c_v2_schema = load_schema(round2c_v2_schema_path)
                round2d_schema = load_schema(round2d_schema_path)
                final_commit_v2_schema = load_schema(final_commit_v2_schema_path)
                log(f"[V2 PIPELINE] ENABLED: Kill shots + Resurrection + Ladder logic", log_handle)
            else:
                log(f"[V2 PIPELINE] DISABLED: Missing v2 schemas", log_handle)
                use_v2_pipeline = False
        else:
            log(f"[V2 PIPELINE] DISABLED: Missing v2 prompts", log_handle)
            use_v2_pipeline = False
    unanimity_challenge_schema = load_schema(unanimity_challenge_schema_path) if unanimity_challenge_schema_path.exists() else None
    
    # Load dataset
    dataset, dataset_info = load_gpqa_dataset(
        split=args.split, 
        allow_split_fallback=args.allow_split_fallback,
        log_handle=log_handle
    )
    log(f"Dataset loaded: {len(dataset)} questions from {dataset_info['dataset_name']}", log_handle)
    if dataset_info["split_fallback_used"]:
        log(f"  WARNING: Split fallback used: requested '{dataset_info['requested_split']}' → actual '{dataset_info['actual_split']}'", log_handle)
    
    # Extract question data
    all_questions = []
    for record in dataset:
        q_data = extract_question_data(record)
        if q_data["question"] and q_data["gold_answer"]:
            all_questions.append(q_data)
    
    log(f"Extracted {len(all_questions)} valid questions", log_handle)
    
    # Sampling
    if args.single_question_id:
        # Single question mode (overrides --n and --replay_ids)
        selected_questions = [q for q in all_questions if q["question_id"] == args.single_question_id]
        if not selected_questions:
            log(f"ERROR: Question ID '{args.single_question_id}' not found in dataset", log_handle)
            sys.exit(1)
        log(f"Single question mode: {args.single_question_id}", log_handle)
    elif args.replay_ids:
        # Replay mode
        with open(args.replay_ids, "r", encoding="utf-8-sig") as f:
            replay_ids = set(json.load(f))
        selected_questions = [q for q in all_questions if q["question_id"] in replay_ids]
        log(f"Replay mode: {len(selected_questions)} questions from {args.replay_ids}", log_handle)
    else:
        # Normal sampling
        n = args.n if args.n is not None else (len(all_questions) if len(all_questions) <= 500 else 500)
        if n > len(all_questions):
            n = len(all_questions)
        
        random.seed(args.seed)
        selected_questions = random.sample(all_questions, n)
        log(f"Sampled {n} questions (seed: {args.seed})", log_handle)
    
    # Save selected IDs
    selected_ids = [q["question_id"] for q in selected_questions]
    with open(ctx.outputs_dir / "selected_ids.json", "w", encoding="utf-8") as f:
        json.dump(selected_ids, f, indent=2)
    
    # Initialize routers
    log("Initializing routers...", log_handle)
    evaluator_routers = {
        "A": ProviderRouter([EVALUATOR_MODELS[0]]),  # Claude 4.5 Opus
        "B": ProviderRouter([EVALUATOR_MODELS[1]]),  # Gemini 3 Pro Preview
        "C": ProviderRouter([EVALUATOR_MODELS[2]]),  # GPT-5.2
        "D": ProviderRouter([EVALUATOR_MODELS[3]]),  # Grok 4.1 Fast Reasoning
    }
    analyzer_router = ProviderRouter([ANALYZER_MODEL])  # Grok 4.1 Fast Reasoning
    synthesizer_router = ProviderRouter([SYNTHESIZER_MODEL])  # GPT-5.2 Thinking
    auditor_router = ProviderRouter([AUDITOR_MODEL])  # GPT-5.2 Thinking (optional)
    resurrection_router = ProviderRouter([ANALYZER_MODEL])  # Grok as adversarial scrutineer for v2
    
    # Round 1 Processing
    merged_output = ctx.outputs_dir / "merged_results.jsonl"  # Contains all rounds despite historical name
    round1_output = merged_output  # Alias for backwards compatibility
    grok_analysis_output = ctx.outputs_dir / "grok_analysis.jsonl"
    synthesis_output = ctx.outputs_dir / "synthesis.jsonl"
    round2c_output = ctx.outputs_dir / "round2_results.jsonl"
    processed_r1 = set()
    
    # Always check for existing results (resume mode) - load ALL existing records
    existing_r1_records = {}
    if round1_output.exists():
        # Load existing Round 1 results
        with open(round1_output, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    question_id = rec["question_id"]
                    processed_r1.add(question_id)
                    existing_r1_records[question_id] = rec
        if len(processed_r1) > 0:
            log(f"Found {len(processed_r1)} already processed questions in Round 1", log_handle)
    
    if args.round in ["1", "both"]:
        log("\n" + "=" * 70, log_handle)
        log("ROUND 1: Independent Blind Evaluation", log_handle)
        log("=" * 70, log_handle)
        
        # Process all selected questions (will skip Round 1 if already done)
        questions_to_process = selected_questions
        log(f"Processing {len(questions_to_process)} questions (will resume if Round 1 exists)", log_handle)
        
        round1_records = []
        for i, question_data in enumerate(questions_to_process, 1):
            log(f"\n[{i}/{len(questions_to_process)}] Question {question_data['question_id']}", log_handle)
            
            # Initialize Audit Trail and Participation Tracking
            audit_trail = []
            participation = {name: [] for name in EVALUATORS}
            
            # Check if we already have Round 1 results for this question
            question_id = question_data["question_id"]
            skip_round1 = False
            if question_id in existing_r1_records:
                log(f"      [RESUME] Loading existing Round 1 results for {question_id}", log_handle)
                record = existing_r1_records[question_id]
                round1_results = record.get("round1", {})
                audit_trail = record.get("audit_trail", [])
                participation = record.get("participation", participation)
                skip_round1 = True
            else:
                round1_results = process_round1(
                    question_data, evaluator_routers, round1_prompt, round1_schema, allow_abstain, log_handle,
                    audit_trail=audit_trail
                )
                skip_round1 = False
            
            # Record participation for Round 1
            for eval_name in EVALUATORS:
                if round1_results.get(f"parse_ok_{eval_name}", False):
                    participation[eval_name].append("Round 1")
            # If any evaluator failed, skip Round 2 entirely and mark as ABSTAIN
            parse_ok_dict = {}
            eval_dict = {}
            for eval_name in EVALUATORS:
                parse_ok_dict[eval_name] = round1_results.get(f"parse_ok_{eval_name}", False)
                eval_dict[eval_name] = round1_results.get(f"evaluator_{eval_name}")
                if not eval_dict[eval_name]:
                    parse_ok_dict[eval_name] = False
            
            if not all(parse_ok_dict.values()):
                failed_evals = [name for name in EVALUATORS if not parse_ok_dict[name]]
                
                log(f"      [ABSTAIN] Evaluator(s) {', '.join(failed_evals)} failed in Round 1 - skipping Round 2, marking as ABSTAIN", log_handle)
                
                # Skip all Round 2 processing
                grok_analysis = None
                synthesis_result = None
                round2c_results = None
                round3_results = None
                auditor_result = {
                    "decision": "ABSTAIN",
                    "justification": f"Evaluator(s) {', '.join(failed_evals)} failed to provide a valid response in Round 1. Cannot proceed to Round 2 without all evaluators.",
                    "reasoning_compatibility": "unknown",
                    "mutually_exclusive_assumptions": []
                }
                final_disposition = "ABSTAIN"
                round2c_escalated = False
                round2c_escalation_reason = []
                round2c_effort_by_evaluator = {eval_name: "medium" if eval_name != "B" else "auto" for eval_name in EVALUATORS}
                eliminated_options = {}
                candidate_options = ["A", "B", "C", "D"]  # Default to all options
                
                # Create minimal layered disposition for ABSTAIN case
                layered_disposition_dict = None
                if LAYERED_DISPOSITION_AVAILABLE:
                    layered_disposition_dict = {
                        "level": "abstain",
                        "eliminated": [],
                        "elimination_proofs": {},
                        "conditional_survivors": {},
                        "resolution_blockers": [],
                        "assertable_eliminations": "",
                        "assertable_preference": None,
                        "unconditional_assertion": None,
                        "confidence_summary": "No valid evaluator responses - cannot make any assertion",
                        "fragility_flags": ["all_evaluators_failed"],
                        "evaluator_agreement": {}
                    }
                
                # Build record and continue to next question
                record = {
                    "question_id": question_data["question_id"],
                    "question": question_data["question"],
                    "choices": question_data["choices"],
                    "gold_answer": question_data["gold_answer"],
                    "subject": question_data.get("subject"),
                    "round1": round1_results,
                    "candidate_answers": [],
                    "eliminated_options": eliminated_options,
                    "candidate_options": candidate_options,
                    "grok_analysis": None,
                    "synthesis": None,
                    "round2c": None,
                    "round2c_escalated": round2c_escalated,
                    "round2c_escalation_reason": round2c_escalation_reason,
                    "round2c_effort_by_evaluator": round2c_effort_by_evaluator,
                    "auditor_result": auditor_result,
                    "final_disposition": final_disposition,
                    "layered_disposition": layered_disposition_dict
                }
                
                # Write immediately
                with open(round1_output, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
                
                round1_records.append(record)
                continue  # Skip to next question
            
            # Identify candidate answers (all answers chosen by ≥1 evaluator)
            candidate_answers = set()
            for eval_name in EVALUATORS:
                eval_result = round1_results.get(f"evaluator_{eval_name}")
                if eval_result and round1_results.get(f"parse_ok_{eval_name}", False):
                    choice = eval_result.get("final_choice")
                    if choice and choice != "ABSTAIN":
                        candidate_answers.add(choice)
            
            # Round 1.5: Call Grok Analyzer (check if already exists in record)
            # NOTE: Grok ALWAYS runs, even on unanimity, to detect reasoning topology
            # Per spec: Grok classifies relations (EQUIVALENT/INCOMPATIBLE/UNCLEAR) even for unanimous cases
            # This enables stress test triggers when unanimity has incompatible assumptions
            r1_pattern = round1_results.get("agreement_pattern", "unknown")
            if question_id in existing_r1_records and "grok_analysis" in existing_r1_records[question_id]:
                log(f"      [RESUME] Loading existing Grok analysis for {question_id}", log_handle)
                grok_analysis = existing_r1_records[question_id]["grok_analysis"]
            else:
                # Grok runs for ALL cases (unanimous or split) to analyze reasoning topology
                if r1_pattern.startswith("unanimous"):
                    log(f"      [NOTE] Round 1 unanimous - Running Grok Analyzer to verify reasoning compatibility", log_handle)
                else:
                    log(f"      [NOTE] Running Grok Analyzer for split case ({r1_pattern})", log_handle)
                grok_analysis = call_grok_analyzer(
                    question_data, round1_results,
                    analyzer_router, grok_analyzer_prompt, grok_analyzer_schema, log_handle,
                    audit_trail=audit_trail
                )
                # Grok is advisory only - if it fails, continue with empty analysis (non-blocking)
                if not grok_analysis:
                    log(f"      [GROK_UNAVAILABLE] Grok Analyzer failed or returned None - preserving R1 candidate set (advisory only)", log_handle)
                    grok_analysis = {
                        "similarity_level": "UNKNOWN",
                        "reasoning_relation": "UNKNOWN",
                        "equivalence_detected": False,
                        "incompatibility_detected": False,
                        "shared_eliminations": {},
                        "divergence_axes": [],
                        "incompatible_assumptions": [],
                        "equivalent_methods": [],
                        "notes": "Grok analysis unavailable - advisory only",
                        "grok_unavailable": True  # Marker for downstream logic
                    }
            
            # Get eliminated options from Grok analyzer's shared_eliminations (advisory - not enforced)
            eliminated_options = {}
            if grok_analysis:
                eliminated_options = grok_analysis.get("shared_eliminations", {})
                # Note: Grok's shared_eliminations are advisory - structural pruning takes precedence
            
            # Also check detect_pruned_options for structural rejections (with proof requirements)
            structural_eliminated, unfalsified_rejects = detect_pruned_options(round1_results)
            # Merge both sources (only pruned options, not unfalsified_rejects)
            for opt, reason in structural_eliminated.items():
                if opt not in eliminated_options:
                    eliminated_options[opt] = reason
            
            # Store unfalsified_rejects for later use (these stay in candidate set)
            if unfalsified_rejects:
                log(f"      [PRUNING] Unfalsified rejects (kept in candidate set): {list(unfalsified_rejects.keys())}", log_handle)
            
            # Compute candidate set (all options minus eliminated)
            # PRUNING IS FINAL: Once an answer is pruned, it must not appear in synthesis, steelman, Round 2, or abstain consideration
            all_options = ["A", "B", "C", "D"]
            candidate_options = [opt for opt in all_options if opt not in eliminated_options.keys()]
            
            # Guardrail: Ensure pruned options are never included
            if len(candidate_options) == 0:
                log(f"      [ERROR] All options were pruned - this should not happen", log_handle)
                candidate_options = all_options  # Fallback to prevent crash
            
            # SPEC CHANGE: Grok Analyzer is ADVISORY ONLY per CAM_Pipeline_Guards_v1
            # Do NOT restore or prune candidates based on Grok results
            # Candidate set is determined by R1 evaluator agreement, not by analyzer
            # Grok's reasoning_relation informs fragility markers but does NOT change candidates
            
            grok_similarity = grok_analysis.get("similarity_level", "UNKNOWN") if grok_analysis else "UNKNOWN"
            grok_relation = grok_analysis.get("reasoning_relation", "UNKNOWN") if grok_analysis else "UNKNOWN"
            
            # Add fragility marker if Grok indicates non-equivalent reasoning (advisory only)
            if grok_relation not in ["EQUIVALENT", "IDENTICAL"]:
                round1_results["grok_fragility_marker"] = f"reasoning_relation={grok_relation}"
                log(f"      [GROK ADVISORY] Non-equivalent reasoning detected ({grok_relation}) - fragility marker added, candidates unchanged", log_handle)
            
            log(f"      [PRUNING] Candidate options after pruning: {candidate_options}, Eliminated: {list(eliminated_options.keys())}", log_handle)
            
            # ============================================================
            # A2) Prelim Disposition (always computed, never skipped)
            # ============================================================
            cheap_elimination = round1_results.get("cheap_elimination", {})
            cheap_survivors = cheap_elimination.get("survivors", candidate_options)
            
            if len(cheap_survivors) == 1:
                prelim_disposition = "ASSERT_BY_ELIMINATION"
                prelim_answer = cheap_survivors[0]
                log(f"      [PRELIM] Single survivor: {prelim_answer} -> ASSERT_BY_ELIMINATION", log_handle)
            elif len(cheap_survivors) == 0:
                prelim_disposition = "INVALID_QUESTION"
                prelim_answer = None
                log(f"      [PRELIM] No survivors -> INVALID_QUESTION", log_handle)
            elif len(cheap_survivors) == 4:
                prelim_disposition = "NO_ELIMINATION"
                prelim_answer = None
                log(f"      [PRELIM] All options survive -> NO_ELIMINATION", log_handle)
            else:
                prelim_disposition = "UNDERDETERMINED"
                prelim_answer = None
                log(f"      [PRELIM] {len(cheap_survivors)} survivors -> UNDERDETERMINED", log_handle)
            
            round1_results["prelim_disposition"] = prelim_disposition
            round1_results["prelim_answer"] = prelim_answer
            
            # CONDITIONAL UNANIMITY CHALLENGE ROUND (NEW - behind flag)
            # Only runs if: --enable_unanimity_challenge flag is set AND exactly one candidate remains (unanimous) AND unanimity is classified as FRAGILE
            unanimity_challenge_result = None
            r1_pattern = round1_results.get("agreement_pattern", "unknown")
            unanimous_choice = round1_results.get("unanimous_choice")
            
            if args.enable_unanimity_challenge and len(candidate_options) == 1 and r1_pattern.startswith("unanimous") and unanimous_choice:
                # Classify unanimity robustness
                robustness, fragility_reasons = classify_unanimity_robustness(
                    round1_results, grok_analysis, question_data, log_handle
                )
                
                if robustness == "FRAGILE":
                    log(f"      [CHALLENGE] Unanimity is FRAGILE - running Unanimity Challenge Round", log_handle)
                    log(f"      [CHALLENGE] Fragility reasons: {', '.join(fragility_reasons)}", log_handle)
                    
                    # Run challenge round
                    unanimity_challenge_result = process_unanimity_challenge(
                        question_data, round1_results, unanimous_choice,
                        evaluator_routers, unanimity_challenge_prompt, unanimity_challenge_schema, log_handle
                    )
                    
                    # If challenge round invalidates unanimity (any evaluator can break it), proceed to synthesis
                    if unanimity_challenge_result.get("any_can_break", False):
                        log(f"      [CHALLENGE] Unanimity invalidated - expanding candidate set and proceeding to synthesis", log_handle)
                        # Expand candidate set to include alternatives that were eliminated
                        # This allows synthesis to consider the full space
                        candidate_options = ["A", "B", "C", "D"]  # Reset to all options for synthesis
                        eliminated_options = {}  # Clear eliminations to allow full synthesis
                    else:
                        log(f"      [CHALLENGE] Unanimity survived challenge - robustness confirmed", log_handle)
                else:
                    log(f"      [CHALLENGE] Unanimity is ROBUST - skipping challenge round", log_handle)
            elif len(candidate_options) > 1:
                log(f"      [CHALLENGE] Multiple candidates ({len(candidate_options)}) - challenge round not applicable", log_handle)
            elif not args.enable_unanimity_challenge:
                log(f"      [CHALLENGE] Unanimity challenge disabled (use --enable_unanimity_challenge to enable)", log_handle)
            
            # Round 2: Call Synthesizer (ALWAYS run - even if unanimous - per spec requirement)
            synthesis_result = None
            r1_pattern = round1_results.get("agreement_pattern", "unknown")
            
            if question_id in existing_r1_records and "synthesis" in existing_r1_records[question_id]:
                log(f"      [RESUME] Loading existing synthesis for {question_id}", log_handle)
                synthesis_result = existing_r1_records[question_id]["synthesis"]
            else:
                # Synthesizer ALWAYS runs (even if unanimous) - per spec: "Unanimous does not auto-end"
                # Grok output is advisory only and must never gate synthesis
                log(f"      [NOTE] Synthesizer triggered: candidate_options={len(candidate_options)}, agreement_pattern={r1_pattern} (always runs per spec)", log_handle)
                synthesis_result = call_synthesizer(
                    question_data, round1_results, eliminated_options, candidate_options,
                    grok_analysis, synthesizer_router, synthesizer_prompt, synthesizer_schema, log_handle
                )
            
            # Round 2a: Representation Check (NEW - MANDATORY if Synthesizer ran and candidate_options >= 2)
            # Per spec: Each evaluator validates their own reconstruction before R2c can proceed
            round2a_results = None
            round2a_rerun_results = None  # Results after repair pass (if needed)
            synthesis_is_dirty = False
            arguments_lock_status = None  # "locked" (all OK) or "contested" (still failing after repair)
            
            if synthesis_result and len(candidate_options) >= 2:
                if question_id in existing_r1_records and "round2a" in existing_r1_records[question_id]:
                    log(f"      [RESUME] Loading existing Round 2a representation check results for {question_id}", log_handle)
                    round2a_results = existing_r1_records[question_id]["round2a"]
                    round2a_rerun_results = existing_r1_records[question_id].get("round2a_rerun")
                    synthesis_is_dirty = existing_r1_records[question_id].get("synthesis_is_dirty", False)
                    arguments_lock_status = existing_r1_records[question_id].get("arguments_lock_status", "locked")
                else:
                    # Initial R2a check
                    round2a_results = process_round2a_representation_check(
                        question_data, round1_results, synthesis_result, candidate_options,
                        evaluator_routers, round2a_prompt, round2a_schema, log_handle
                    )
                
                # Synthesizer Repair + Rerun Pass (per spec: ONE repair pass, then rerun R2a for ALL evaluators)
                if round2a_results and not round2a_rerun_results:
                    # Check if any evaluator has severity=major representation issue
                    needs_repair = False
                    has_major_issues = False
                    for eval_name in EVALUATORS:
                        eval_check = round2a_results.get(f"evaluator_{eval_name}")
                        if eval_check and not eval_check.get("representation_ok", True):
                            needs_repair = True
                            synthesis_is_dirty = True
                            if eval_check.get("severity") == "major":
                                has_major_issues = True
                    
                    if needs_repair and has_major_issues:
                        log(f"      [REPAIR] Major representation issues detected - triggering synthesizer repair", log_handle)
                        repaired_synthesis = repair_synthesizer_after_round2a(
                            question_data, round1_results, eliminated_options, candidate_options,
                            grok_analysis, synthesis_result, round2a_results,
                            synthesizer_router, synthesizer_prompt, synthesizer_schema, log_handle
                        )
                        if repaired_synthesis:
                            synthesis_result = repaired_synthesis
                            
                            # RERUN R2a for ALL evaluators after repair (per spec)
                            log(f"      [R2a-RERUN] Rerunning Round 2a for ALL evaluators after repair", log_handle)
                            round2a_rerun_results = process_round2a_representation_check(
                                question_data, round1_results, synthesis_result, candidate_options,
                                evaluator_routers, round2a_prompt, round2a_schema, log_handle
                            )
                            
                            # Check if issues persist after rerun
                            still_has_major_issues = False
                            if round2a_rerun_results:
                                for eval_name in EVALUATORS:
                                    eval_check = round2a_rerun_results.get(f"evaluator_{eval_name}")
                                    if eval_check and not eval_check.get("representation_ok", True):
                                        if eval_check.get("severity") == "major":
                                            still_has_major_issues = True
                                            break
                            
                            if still_has_major_issues:
                                arguments_lock_status = "contested"
                                log(f"      [CONTESTED] Representation still contested after repair - marking arguments_lock_status=contested", log_handle)
                            else:
                                arguments_lock_status = "locked"
                                log(f"      [LOCK] Arguments locked for Round 2c after successful R2a rerun", log_handle)
                        else:
                            arguments_lock_status = "contested"
                            log(f"      [CONTESTED] Synthesizer repair failed - marking arguments_lock_status=contested", log_handle)
                    elif needs_repair:
                        # Minor issues only - no repair needed, but mark as dirty
                        arguments_lock_status = "locked"
                        log(f"      [LOCK] Arguments locked for Round 2c (minor issues only - no repair needed)", log_handle)
                    else:
                        arguments_lock_status = "locked"
                        log(f"      [LOCK] Arguments locked for Round 2c (all Round 2a checks passed)", log_handle)
            
            # Round 2c: Forced Defense Before Commit
            round2c_results = None
            
            # CRITICAL: Round 2c is MANDATORY if multiple candidates survive pruning
            # This overrides: unanimity, Grok equivalence, any prior majority logic
            has_multiple_candidates = len(candidate_options) >= 2
            
            # Extract reasoning_relation early (needed later for disposition logic)
            reasoning_relation = grok_analysis.get("reasoning_relation", "UNKNOWN") if grok_analysis else "UNKNOWN"
            
            # V2 PIPELINE: ALWAYS run Round 2c for full audit trail
            # This ensures all cases (including unanimous single-candidate) get:
            # - R2c elimination audit with kill shots
            # - R2d resurrection testing  
            # - Final Commit with ladder logic
            # The v2 pipeline provides complete transparency even when answers seem certain
            
            # ============================================================
            # EPISTEMIC CONFLICT GATE (per spec: elimination only on conflict)
            # ============================================================
            # CRITICAL: Elimination/kill-shot logic should ONLY run when models
            # genuinely disagree about reality, NOT when they agree and we're
            # just adding bookkeeping noise.
            
            epistemic_conflict, conflict_reasons = epistemic_conflict_exists(
                round1_results,
                round2a_results,
                round3_results=None,  # R3 hasn't run yet
                grok_analysis=grok_analysis,
                candidate_options=candidate_options,  # CRITICAL: Check candidate set size
            )
            
            # Store gate result
            epistemic_gate = {
                "conflict_exists": epistemic_conflict,
                "reasons": conflict_reasons,
                "unanimous_choice": round1_results.get("unanimous_choice"),
            }
            
            if not epistemic_conflict:
                # NO CONFLICT: Skip elimination logic entirely
                # Use unanimous answer directly - this prevents 363-class bugs
                log(f"      [EPISTEMIC_GATE] NO CONFLICT - elimination logic DISABLED", log_handle)
                log(f"      [EPISTEMIC_GATE] Using unanimous answer: {round1_results.get('unanimous_choice')}", log_handle)
                
                should_run_round2c = False
                
                # Set final answer directly from R1 unanimous
                unanimous_pre_elimination_answer = round1_results.get("unanimous_choice")
                epistemic_gate["final_answer_source"] = "unanimous_pre_elimination"
                epistemic_gate["elimination_skipped"] = True
            else:
                # CONFLICT EXISTS: Run elimination logic
                log(f"      [EPISTEMIC_GATE] CONFLICT DETECTED: {conflict_reasons}", log_handle)
                should_run_round2c = True
                unanimous_pre_elimination_answer = None
                epistemic_gate["elimination_skipped"] = False
            
            # Log why we're running (or not running) R2c
            if should_run_round2c:
                if has_multiple_candidates:
                    log(f"      [R2c TRIGGER] Multiple candidates ({len(candidate_options)})", log_handle)
                else:
                    log(f"      [R2c TRIGGER] Epistemic conflict: {conflict_reasons}", log_handle)
            
            # Initialize escalation fields
            round2c_escalated = False
            round2c_escalation_reason = []
            round2c_effort_by_evaluator = {name: ("auto" if name == "B" else "medium") for name in EVALUATORS}


            # ============================================================
            # V2/V1 PIPELINE: Round 2c / 2d / Final Commit
            # ============================================================
            round2d_results = None
            final_commit_results = None  # Initialize before conditional branches
            
            if use_v2_pipeline and should_run_round2c:
                # V2 PIPELINE: Kill Shots + Resurrection + Ladder
                cached_r2c = existing_r1_records.get(question_id, {}).get("round2c")
                if cached_r2c and cached_r2c.get("pipeline_version") == "v2":
                    log(f"      [RESUME] Loading existing Round 2c v2 results", log_handle)
                    round2c_results = cached_r2c
                    round2c_effort_by_evaluator = existing_r1_records[question_id].get("round2c_effort_by_evaluator", round2c_effort_by_evaluator)
                else:
                    log(f"      [V2] Running Round 2c (Elimination Audit with Kill Shots)", log_handle)
                    round2c_results = process_round2c_v2(
                        question_data=question_data,
                        round1_results=round1_results,
                        eliminated_options=eliminated_options,
                        candidate_options=candidate_options,
                        synthesis_result=synthesis_result,
                        evaluator_routers=evaluator_routers,
                        round2c_prompt_template=round2c_v2_prompt,
                        round2c_schema=round2c_v2_schema,
                        effort_by_evaluator=round2c_effort_by_evaluator,
                        log_handle=log_handle,
                        audit_trail=audit_trail,
                        EVALUATORS=EVALUATORS,
                        log_fn=log,
                        call_evaluator_with_override_fn=call_evaluator_with_override,
                        add_audit_entry_fn=add_audit_entry,
                        check_quota_error_fn=check_quota_error,
                        jsonschema_module=jsonschema,
                    )
                
                # Round 2d: Resurrection Testing
                if round2c_results and round2c_results.get("round2c_defense_complete", False):
                    cached_r2d = existing_r1_records.get(question_id, {}).get("round2d")
                    if cached_r2d:
                        log(f"      [RESUME] Loading existing Round 2d results", log_handle)
                        round2d_results = cached_r2d
                    else:
                        log(f"      [V2] Running Round 2d (Resurrection Testing)", log_handle)
                        round2d_results = process_round2d_resurrection(
                            question_data=question_data,
                            round2c_results=round2c_results,
                            resurrection_router=resurrection_router,
                            resurrection_prompt_template=round2d_prompt,
                            resurrection_schema=round2d_schema,
                            log_handle=log_handle,
                            audit_trail=audit_trail,
                            log_fn=log,
                            add_audit_entry_fn=add_audit_entry,
                            jsonschema_module=jsonschema,
                        )
                
                # Final Commit v2: Ladder of Commitment
                if round2c_results and round2c_results.get("round2c_defense_complete", False):
                    cached_fc = existing_r1_records.get(question_id, {}).get("final_commit")
                    if cached_fc and cached_fc.get("pipeline_version") == "v2":
                        log(f"      [RESUME] Loading existing Final Commit v2 results", log_handle)
                        final_commit_results = cached_fc
                    else:
                        log(f"      [V2] Running Final Commit (Ladder Logic)", log_handle)
                        final_commit_results = process_final_commit_v2(
                            question_data=question_data,
                            round1_results=round1_results,
                            round2c_results=round2c_results,
                            round2d_results=round2d_results,
                            candidate_options=candidate_options,
                            synthesis_result=synthesis_result,
                            evaluator_routers=evaluator_routers,
                            final_commit_prompt_template=final_commit_v2_prompt,
                            final_commit_schema=final_commit_v2_schema,
                            log_handle=log_handle,
                            audit_trail=audit_trail,
                            EVALUATORS=EVALUATORS,
                            log_fn=log,
                            call_evaluator_with_override_fn=call_evaluator_with_override,
                            add_audit_entry_fn=add_audit_entry,
                            jsonschema_module=jsonschema,
                            compute_agreement_pattern_fn=compute_agreement_pattern,
                        )
            
            elif should_run_round2c:
                # V1 PIPELINE: Standard forced defense
                if question_id in existing_r1_records and "round2c" in existing_r1_records[question_id]:
                    log(f"      [RESUME] Loading existing Round 2c results for {question_id}", log_handle)
                    round2c_results = existing_r1_records[question_id]["round2c"]
                    round2c_effort_by_evaluator = existing_r1_records[question_id].get("round2c_effort_by_evaluator", round2c_effort_by_evaluator)
                else:
                    log(f"      [V1] Running Round 2c (Forced Defense)", log_handle)
                    round2c_results = process_round2c_forced_defense(
                        question_data, round1_results, eliminated_options, candidate_options,
                        synthesis_result, evaluator_routers, round2c_prompt, round2c_schema,
                        round2c_effort_by_evaluator, log_handle
                    )
                
                # V1 Final Commit
                if round2c_results and round2c_results.get("round2c_defense_complete", False):
                    if question_id in existing_r1_records and "final_commit" in existing_r1_records[question_id]:
                        log(f"      [RESUME] Loading existing Final Commit results for {question_id}", log_handle)
                        final_commit_results = existing_r1_records[question_id]["final_commit"]
                    else:
                        log(f"      [V1] Running Final Commit Phase", log_handle)
                        final_commit_results = process_final_commit(
                            question_data, round1_results, round2c_results, candidate_options,
                            synthesis_result, evaluator_routers, final_commit_prompt, final_commit_schema,
                            log_handle
                        )
            # Round 3: Mannerly Stress Test (Applies even under unanimity)
            # Per spec trigger PRIORITY:
            #   Run if: Unanimous R1 AND (weak proof OR incompatibility flags)
            #   Run if: Unanimous Final Commit with incompatible assumptions
            #   Run if: Grok indicates "equivalent conclusions with different commitments"
            #   Do NOT run if unanimity is strong and uncontested
            round3_results = None
            round3_trigger_reason = None  # Track why R3 was triggered
            
            # Determine if Round 3 should run - use FINAL COMMIT results, not Round 2c leading
            unanimous_now = False
            unanimous_choice = None
            if final_commit_results:
                final_pattern = final_commit_results.get("final_agreement_pattern")
                unanimous_now = final_pattern.startswith("unanimous") if final_pattern else False
                unanimous_choice = final_commit_results.get("final_unanimous_choice")
            else:
                unanimous_now = r1_pattern.startswith("unanimous") if r1_pattern else False
                unanimous_choice = round1_results.get("unanimous_choice")
            
            # Grok flags
            grok_incompatible = reasoning_relation in ["INCOMPATIBLE", "MIXED"]
            grok_fragile = grok_analysis.get("similarity_level") in ["LOW", "MEDIUM"] if grok_analysis else False
            grok_equivalent_diff_commitments = (
                reasoning_relation == "EQUIVALENT" and 
                grok_analysis and 
                len(grok_analysis.get("incompatible_assumptions", [])) > 0
            ) if grok_analysis else False
            
            # Proof strength check from synthesis
            weak_proof = False
            strong_proof = False
            if synthesis_result:
                proof_ledger = synthesis_result.get("proof_ledger", {})
                has_unfalsified = any(v.get("status") == "unfalsified" for v in proof_ledger.values())
                # Check proof_strength for unanimous choice
                arg_recons = synthesis_result.get("argument_reconstructions", {})
                if unanimous_choice and unanimous_choice in arg_recons:
                    proof_strength = arg_recons[unanimous_choice].get("proof_strength", 0)
                    weak_proof = proof_strength <= 1  # 0-1 is weak
                    strong_proof = proof_strength >= 3  # 3 is strong
                else:
                    weak_proof = has_unfalsified  # Fallback: unfalsified = weak
            
            # Confidence check
            max_confidence = 0
            for eval_name in EVALUATORS:
                res = round1_results.get(f"evaluator_{eval_name}")
                if res:
                    max_confidence = max(max_confidence, res.get("confidence", 0))
            high_confidence = max_confidence >= 80
            
            # Determine trigger conditions
            trigger_unanimous_weak_proof = unanimous_now and weak_proof
            trigger_unanimous_incompatible = unanimous_now and grok_incompatible
            trigger_equivalent_diff_commitments = grok_equivalent_diff_commitments
            
            # Override: Do NOT run if unanimity is strong and uncontested
            strong_and_uncontested = (
                unanimous_now and 
                strong_proof and 
                high_confidence and 
                reasoning_relation == "EQUIVALENT" and 
                not grok_incompatible and
                not grok_equivalent_diff_commitments
            )
            
            should_run_round3 = False
            if unanimous_choice is not None and not strong_and_uncontested:
                if trigger_unanimous_weak_proof:
                    should_run_round3 = True
                    round3_trigger_reason = "unanimous_weak_proof"
                elif trigger_unanimous_incompatible:
                    should_run_round3 = True
                    round3_trigger_reason = "unanimous_incompatible_reasoning"
                elif trigger_equivalent_diff_commitments:
                    should_run_round3 = True
                    round3_trigger_reason = "equivalent_with_different_commitments"
            
            if strong_and_uncontested:
                log(f"      [R3-SKIP] Unanimity is strong and uncontested - skipping stress test", log_handle)
            
            if should_run_round3:
                if question_id in existing_r1_records and "round3" in existing_r1_records[question_id]:
                    log(f"      [RESUME] Loading existing Round 3 results for {question_id}", log_handle)
                    round3_results = existing_r1_records[question_id]["round3"]
                    round3_trigger_reason = existing_r1_records[question_id].get("round3_trigger_reason", round3_trigger_reason)
                else:
                    log(f"      [NOTE] Running Round 3 (Unanimous Stress Test) - trigger: {round3_trigger_reason}", log_handle)
                    round3_results = process_round3_stress_test(
                        question_data, round1_results, unanimous_choice,
                        synthesis_result, evaluator_routers, round3_prompt, round3_schema, log_handle
                    )

            # Auditor: Post-Round 2c structural check
            auditor_result = None
            if question_id in existing_r1_records and "auditor_result" in existing_r1_records[question_id]:
                log(f"      [RESUME] Loading existing Auditor result for {question_id}", log_handle)
                auditor_result = existing_r1_records[question_id]["auditor_result"]
            else:
                # Always run Auditor if we have synthesis, but skip for simple unanimous cases
                is_unanimous_equivalent = (r1_pattern.startswith("unanimous") and reasoning_relation == "EQUIVALENT")
                
                # Check if Round 3 showed fragility - if so, don't skip Auditor
                round3_fragile = False
                if round3_results:
                    round3_fragile = round3_results.get("any_can_break", False) or round3_results.get("robustness") == "FRAGILE"
                    if round3_fragile:
                        log(f"      [R3-FLAG] Round 3 stress test showed fragility - Auditor will run", log_handle)
                
                if is_unanimous_equivalent and not should_run_round2c and not round3_fragile:
                    log(f"      [NOTE] Auditor skipped: unanimous + EQUIVALENT reasoning (auto-ACCEPT)", log_handle)
                    auditor_result = {
                        "decision": "ACCEPT",
                        "justification": "Unanimous Round 1 agreement with equivalent reasoning - no audit needed",
                        "reasoning_compatibility": "compatible",
                        "mutually_exclusive_assumptions": []
                    }
                else:
                    log(f"      [NOTE] Calling Auditor to validate final disposition", log_handle)
                    auditor_result = call_auditor(
                        question_data, round1_results, round2c_results, synthesis_result,
                        auditor_router, auditor_prompt, auditor_schema, candidate_options, log_handle,
                        final_commit_results
                    )
            
            # ============================================================
            # FINAL DISPOSITION COMPUTATION
            # ============================================================
            
            # CASE 1: Elimination was skipped (unanimous + no conflict)
            if unanimous_pre_elimination_answer:
                log(f"      [DISPOSITION] UNANIMOUS_ACCEPTED (elimination skipped)", log_handle)
                final_disposition = "UNANIMOUS_ACCEPTED"
                
                # Set system_ladder equivalent for unanimous case
                system_ladder = {
                    "level": 0,
                    "level_name": "unanimous_accepted",
                    "justification": f"Unanimous R1 agreement on {unanimous_pre_elimination_answer}, no epistemic conflict detected",
                    "confirmed_kills": [],
                    "attempted_kills": [],
                    "resurrected": [],
                    "survivors": [unanimous_pre_elimination_answer],
                    "prior_eliminations": [],
                    "domain_restricted": False,
                    "elimination_skipped": True,
                }
                
                # Layered disposition for skipped case
                layered_disposition = None
                if LAYERED_DISPOSITION_AVAILABLE:
                    try:
                        layered_disposition = LayeredDisposition(
                            level=DispositionLevel.FULL_ASSERTION,
                            confidence_summary=f"Unanimous R1 ({unanimous_pre_elimination_answer}), elimination skipped",
                            unconditional_assertion=unanimous_pre_elimination_answer,
                            assertable_preference=unanimous_pre_elimination_answer,
                            assertable_eliminations=[opt for opt in ["A", "B", "C", "D"] if opt != unanimous_pre_elimination_answer],
                            conditional_survivors={},
                        )
                    except Exception as e:
                        log(f"      [WARN] Layered disposition creation failed: {e}", log_handle)
            else:
                # CASE 2: Normal elimination path
                # Compute final disposition (legacy string-based)
                final_disposition = compute_final_disposition(
                    round1_results, round2c_results, grok_analysis, auditor_result, 
                    synthesis_result, candidate_options, unanimity_challenge_result, round3_results,
                    final_commit_results
                )
                log(f"      [DISPOSITION] {final_disposition}", log_handle)
                
                # Compute layered disposition (structured output with partial knowledge)
                layered_disposition = None
                if LAYERED_DISPOSITION_AVAILABLE:
                    try:
                        layered_disposition = compute_layered_disposition(
                            round1_results=round1_results,
                            round2c_results=round2c_results,
                            round2d_results=round2d_results,
                            final_commit_results=final_commit_results,
                            grok_analysis=grok_analysis,
                            synthesis_result=synthesis_result,
                            round3_results=round3_results,
                            auditor_result=auditor_result,
                            candidate_options=candidate_options,
                            EVALUATORS=EVALUATORS,
                        )
                        # Log the layered disposition summary
                        log(f"      [LAYERED] {layered_disposition.level.value.upper()}: {layered_disposition.confidence_summary}", log_handle)
                        if layered_disposition.assertable_eliminations:
                            log(f"      [ELIMINATED] {layered_disposition.assertable_eliminations}", log_handle)
                        if layered_disposition.conditional_survivors:
                            for opt, surv in layered_disposition.conditional_survivors.items():
                                if surv.conditions and surv.conditions[0] != "No explicit conditions identified":
                                    conds = "; ".join(surv.conditions[:2])
                                    log(f"      [CONDITIONAL] {opt} IF [{conds}]", log_handle)
                        if layered_disposition.assertable_preference:
                            log(f"      [PREFERENCE] {layered_disposition.assertable_preference}", log_handle)
                        if layered_disposition.unconditional_assertion:
                            log(f"      [ASSERTION] {layered_disposition.unconditional_assertion}", log_handle)
                    except Exception as e:
                        log(f"      [WARN] Layered disposition computation failed: {e}", log_handle)
                        layered_disposition = None
                
                system_ladder = None  # Will be populated from final_commit_results if available
            
            # Build record
            record = {
                "question_id": question_data["question_id"],
                "question": question_data["question"],
                "choices": question_data["choices"],
                "gold_answer": question_data["gold_answer"],
                "subject": question_data.get("subject"),
                "round1": round1_results,
                "candidate_answers": list(candidate_answers),
                "eliminated_options": eliminated_options,
                "candidate_options": candidate_options,
                # Explicit labels for clarity (per user request)
                "cheap_elim_survivors": candidate_options.copy() if isinstance(candidate_options, list) else list(candidate_options),
                "post_pruning_candidates": candidate_options.copy() if isinstance(candidate_options, list) else list(candidate_options),
            }
            
            if grok_analysis:
                record["grok_analysis"] = grok_analysis
                grok_record = {
                    "question_id": question_data["question_id"],
                    "grok_analysis": grok_analysis
                }
                with open(grok_analysis_output, "a", encoding="utf-8") as f:
                    f.write(json.dumps(grok_record) + "\n")
            
            if synthesis_result:
                record["synthesis"] = synthesis_result
                synthesis_record = {
                    "question_id": question_data["question_id"],
                    "synthesis": synthesis_result
                }
            
            # Always create round2a structure - derive from R1 mapping_validation_ok fields
            # (These are the actual representation check results, not candidate-dependent)
            round2a_structured = {
                "round_executed": False,  # Will set to True if any mapping_validation_ok found
                "all_passed": True,
            }
            
            # Check R1 evaluator blocks for mapping_validation_ok
            r1_data = round1_results or {}
            has_any_mapping_check = False
            for eval_name in EVALUATORS:
                eval_data = r1_data.get(f"evaluator_{eval_name}", {})
                if eval_data and "mapping_validation_ok" in eval_data:
                    has_any_mapping_check = True
                    ok = eval_data.get("mapping_validation_ok", False)
                    round2a_structured[f"evaluator_{eval_name}"] = {
                        "ok": ok,
                        "details": {"source": f"round1.evaluator_{eval_name}.mapping_validation_ok"}
                    }
                    if not ok:
                        round2a_structured["all_passed"] = False
                elif eval_data:
                    # Evaluator exists but no mapping_validation_ok field
                    round2a_structured[f"evaluator_{eval_name}"] = {
                        "ok": None,
                        "details": {"status": "field_missing"}
                    }
                else:
                    round2a_structured[f"evaluator_{eval_name}"] = {
                        "ok": None,
                        "details": {"status": "evaluator_missing"}
                    }
            
            # Also check round2a_results if they exist (representation_ok from actual R2a process)
            if round2a_results:
                has_any_mapping_check = True
                for eval_name in EVALUATORS:
                    eval_check = round2a_results.get(f"evaluator_{eval_name}")
                    if eval_check:
                        ok = eval_check.get("representation_ok", True)
                        # Prefer round2a_results over mapping_validation_ok if both exist
                        round2a_structured[f"evaluator_{eval_name}"] = {
                            "ok": ok,
                            "details": eval_check
                        }
                        if not ok:
                            round2a_structured["all_passed"] = False
            
            if has_any_mapping_check:
                round2a_structured["round_executed"] = True
            else:
                round2a_structured["skip_reason"] = "no_mapping_validation_data"
                round2a_structured["all_passed"] = None
            
            record["round2a"] = round2a_structured
            
            # Store new R2a fields (per spec: track rerun and lock status)
            if round2a_rerun_results:
                record["round2a_rerun"] = round2a_rerun_results
            if arguments_lock_status:
                record["arguments_lock_status"] = arguments_lock_status
            if synthesis_is_dirty:
                record["synthesis_is_dirty"] = synthesis_is_dirty
            
            # Round 1.75 fidelity check (legacy - only stored if it exists from resume/previous run)
            # Note: Round 2a replaces Round 1.75, but we keep this for backward compatibility
            if question_id in existing_r1_records and "fidelity_check" in existing_r1_records[question_id]:
                record["fidelity_check"] = existing_r1_records[question_id]["fidelity_check"]
            
            if unanimity_challenge_result:
                record["unanimity_challenge"] = unanimity_challenge_result
            
            if synthesis_result:
                with open(synthesis_output, "a", encoding="utf-8") as f:
                    f.write(json.dumps(synthesis_record) + "\n")
            
            # Always add escalation tracking fields (even if Round 2c wasn't run)
            record["round2c_escalated"] = round2c_escalated
            record["round2c_escalation_reason"] = round2c_escalation_reason
            record["round2c_effort_by_evaluator"] = round2c_effort_by_evaluator
            
            # Epistemic conflict gate result (always stored)
            record["epistemic_gate"] = epistemic_gate
            
            # A2) Prelim disposition (always computed)
            record["prelim_disposition"] = round1_results.get("prelim_disposition")
            record["prelim_answer"] = round1_results.get("prelim_answer")
            
            if auditor_result:
                record["auditor_result"] = auditor_result
            
            # Always store final_disposition (computed even when Round 2c is skipped)
            record["final_disposition"] = final_disposition
            
            # Store layered disposition (structured output)
            if layered_disposition:
                record["layered_disposition"] = layered_disposition.to_dict()
            
            # ========================================
            # CAM v2.5.3: Auditor Terminal State (three-valued outcome semantics)
            # ========================================
            if AUDITOR_TERMINAL_STATES_AVAILABLE:
                gold_answer_for_terminal = question_data.get("gold_answer", "")
                
                # Build kill_aggregation dict for terminal state computation
                # v2.5.3: ALWAYS ensure kill_agg has "survivors" field to prevent silent default to 4
                if round2c_results and round2c_results.get("kill_aggregation"):
                    kill_agg = round2c_results.get("kill_aggregation")
                    # Ensure survivors field exists (defensive)
                    if "survivors" not in kill_agg:
                        kill_agg["survivors"] = list(candidate_options)
                        log(f"      [WARN] kill_aggregation missing survivors, using candidate_options", log_handle)
                else:
                    # No R2c results or no kill_aggregation - create from scratch
                    # v2.5.3: Distinguish R1 unanimous (single survivor) from other fallback cases
                    if unanimous_pre_elimination_answer:
                        # R1 unanimous + elimination skipped: single survivor is the unanimous answer
                        kill_agg = {
                            "confirmed_kills": [],
                            "survivors": [unanimous_pre_elimination_answer],
                            "_source": "r1_unanimous",
                        }
                        log(f"      [KILL_AGG] R1 unanimous: survivors=[{unanimous_pre_elimination_answer}], source=r1_unanimous", log_handle)
                    else:
                        # Normal fallback: use post-pruning candidate_options
                        kill_agg = {
                            "confirmed_kills": [], 
                            "survivors": list(candidate_options),
                            "_source": "fallback_from_candidate_options",
                        }
                
                # Apply Rule Libraries (CAM v2.5 - domain-specific epistemic guards)
                question_domain = question_data.get("Subdomain", question_data.get("High-level domain", ""))
                survivor_conditions = round2c_results.get("survivor_conditions", {}) if round2c_results else {}
                
                kill_agg, rule_library_results = apply_all_rule_libraries(
                    kill_aggregation=kill_agg,
                    survivor_conditions=survivor_conditions,
                    question_text=question_data.get("Question", ""),
                    question_domain=question_domain,
                    round2a_result=round2a_results if 'round2a_results' in dir() else None,
                    round2c_result=round2c_results,
                    ladder_level=record.get("ladder_level", 3),
                    log_handle=log_handle,
                )
                
                # Store rule library results for audit trail
                if rule_library_results:
                    record["rule_library_results"] = rule_library_results
                    total_triggered = sum(r.get("rules_triggered", 0) for r in rule_library_results)
                    if total_triggered > 0:
                        log(f"      [RULES] {total_triggered} rules triggered across {len(rule_library_results)} libraries", log_handle)
                
                # Get ladder metadata from system_ladder if available
                ladder_meta = {}
                if final_commit_results and final_commit_results.get("system_ladder"):
                    sys_ladder = final_commit_results["system_ladder"]
                    ladder_meta = sys_ladder.get("metadata", {})
                
                # Determine terminal state (v2.5.3: pass candidate_options for authoritative survivor computation)
                auditor_decision = determine_terminal_state(
                    round1_results=round1_results,
                    round2c_results=round2c_results,
                    round2d_results=round2d_results,
                    final_commit_results=final_commit_results,
                    round3_results=round3_results,
                    auditor_result=auditor_result,
                    kill_aggregation=kill_agg,
                    gold_answer=gold_answer_for_terminal,
                    evaluators=EVALUATORS,
                    ladder_level=record.get("ladder_level", 3),
                    ladder_metadata=ladder_meta,
                    candidate_options=list(candidate_options) if candidate_options else None,
                )
                
                # Store the terminal state
                record["auditor_terminal_state"] = auditor_decision.terminal_state.value
                record["auditor_decision"] = auditor_decision.to_dict()
                
                # v2.5.3: Store kill_aggregation for audit trail (always written, even if empty)
                record["kill_aggregation"] = kill_agg
                
                log(f"      [TERMINAL STATE] {auditor_decision.terminal_state.value}: {auditor_decision.justification[:100]}...", log_handle)
                
                # Perform fragile unanimity check (auditor semantics, not a rule)
                should_withhold, withhold_reasons = perform_fragile_unanimity_check(
                    round1_results, round2c_results, final_commit_results, kill_agg, EVALUATORS
                )
                
                if should_withhold:
                    record["fragile_unanimity_detected"] = True
                    record["fragile_unanimity_reasons"] = withhold_reasons
                    log(f"      [FRAGILE UNANIMITY] Detected: {withhold_reasons}", log_handle)
            
            # Compute UNANIMOUS_WRONG (correctness-based, not disposition-based)
            # Check if final choice is wrong and unanimous
            gold_answer = question_data.get("gold_answer", "")
            if gold_answer:
                # Determine final choice from Final Commit (preferred) or Round 1
                if final_commit_results:
                    final_choice = final_commit_results.get("final_majority_choice") or final_commit_results.get("final_unanimous_choice")
                    final_pattern = final_commit_results.get("final_agreement_pattern", "")
                else:
                    final_choice = round1_results.get("majority_choice") or round1_results.get("unanimous_choice")
                    final_pattern = round1_results.get("agreement_pattern", "")
                
                if final_choice and final_choice != gold_answer:
                    # Check if unanimous (handles unanimous_3, unanimous_4, etc.)
                    if final_pattern.startswith("unanimous"):
                        record["unanimous_wrong"] = True
                        record["unanimous_wrong_choice"] = final_choice
                        # Extract count from pattern (unanimous_3 -> 3, unanimous_4 -> 4)
                        try:
                            count = int(final_pattern.split("_")[1])
                        except (IndexError, ValueError):
                            count = len(EVALUATORS)
                        record["unanimous_wrong_count"] = count
                    else:
                        record["unanimous_wrong"] = False
                else:
                    record["unanimous_wrong"] = False
            
            if round2c_results:
                record["round2c"] = round2c_results
            
            if final_commit_results:
                record["final_commit"] = final_commit_results
            
            if round3_results:
                record["round3"] = round3_results
            if round3_trigger_reason:
                record["round3_trigger_reason"] = round3_trigger_reason
            
            # V2 specific fields
            if round2d_results:
                record["round2d"] = round2d_results
            
            # Add system ladder and disposition from v2
            if final_commit_results and final_commit_results.get("system_ladder"):
                record["system_ladder"] = final_commit_results["system_ladder"]
                ladder_level = final_commit_results["system_ladder"]["level"]
                ladder_name = final_commit_results["system_ladder"]["level_name"]
                
                # SPEC: Prohibit ladder improvement when letter-mapping drift detected
                # If drift was detected, cap at Level 2 (CONDITIONAL_SET) or worse
                if final_commit_results.get("letter_mapping_drift_detected"):
                    original_level = ladder_level
                    if ladder_level < 2:  # 0 (full_assert) or 1 (assert_by_elimination)
                        ladder_level = 2
                        ladder_name = "conditional_set"
                        log(f"      [LETTER_MAPPING_DRIFT] Ladder capped at L{ladder_level} ({ladder_name}) - was L{original_level} before drift prohibition", log_handle)
                        record["system_ladder"]["level"] = ladder_level
                        record["system_ladder"]["level_name"] = ladder_name
                        record["system_ladder"]["drift_prohibition_applied"] = True
                    record["letter_mapping_drift"] = True
                    record["drift_fragility_marker"] = final_commit_results.get("round1_unanimity_rail_reason", "letter-mapping drift detected")
                
                record["ladder_level"] = ladder_level
                record["ladder_name"] = ladder_name
                
                # Update final disposition based on ladder level
                ladder_dispositions = {
                    0: "ASSERT_FULL",
                    1: "ASSERT_BY_ELIMINATION",
                    2: "CONDITIONAL_SET",
                    3: "PARTIAL_ELIMINATION",
                    4: "INVALID_QUESTION",
                }
                if ladder_level in ladder_dispositions:
                    final_disposition = ladder_dispositions[ladder_level]
                    record["final_disposition"] = final_disposition
            elif system_ladder:  # Unanimous case - elimination was skipped
                record["system_ladder"] = system_ladder
                record["ladder_level"] = system_ladder["level"]
                record["ladder_name"] = system_ladder["level_name"]
                record["elimination_skipped"] = True
            
            # Track pipeline version - use_v2_pipeline is the source of truth
            record["pipeline_version"] = "v2" if use_v2_pipeline else "v1"
            
            # Write immediately (append-only)
            with open(round1_output, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            
            round1_records.append(record)
            time.sleep(SLEEP_BETWEEN_CALLS)
        
        # Compute Round 1 metrics
        log("\nComputing Round 1 metrics...", log_handle)
        all_r1_records = []
        if round1_output.exists():
            with open(round1_output, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        all_r1_records.append(json.loads(line))
        
        r1_metrics = compute_round1_metrics(all_r1_records)
        
        # Compute Grok reliability metrics (Part D)
        grok_metrics = compute_grok_metrics(all_r1_records)
        r1_metrics["grok_reliability"] = grok_metrics
        
        with open(ctx.outputs_dir / "round1_metrics.json", "w", encoding="utf-8") as f:
            json.dump(r1_metrics, f, indent=2)
        
        log(f"Round 1 complete. Metrics saved to {ctx.outputs_dir / 'round1_metrics.json'}", log_handle)
        if grok_metrics["grok_incompatibility_invalid_count"] > 0:
            log(f"  [WARNING] Grok invalid incompatibility flags: {grok_metrics['grok_incompatibility_invalid_count']}", log_handle)
    
    # Round 2 is now Synthesizer + Auditor (no evaluator re-evaluation)
    # This happens automatically in Round 1 processing above
        
        # Generate dossier
        log("\nGenerating dossier...", log_handle)
        try:
            from cam.adapters.gpqa.build_gpqa_dossier import build_dossier
            dossier_path = ctx.run_dir / "dossier.html"
            # merged_output contains complete records with all rounds
            if not merged_output.exists():
                raise FileNotFoundError(f"Missing results file: {merged_output}. Run the pipeline first.")
            build_dossier(merged_output, dossier_path)
            log(f"Dossier generated: {dossier_path}", log_handle)
            log(f"  Data source: {merged_output}", log_handle)
        except Exception as e:
            log(f"WARNING: Dossier generation failed: {e}", log_handle)
        
        # Post-run validators (must fail loudly)
        log("\nRunning post-run validators...", log_handle)
        validator_failures = []
        
        # Validator 1: Evaluator count matches config
        expected_evaluator_count = len(EVALUATORS)
        for record in all_r1_records:
            question_id = record.get("question_id", "unknown")
            round1 = record.get("round1", {})
            parse_ok_count = sum(1 for eval_name in EVALUATORS if round1.get(f"parse_ok_{eval_name}", False))
            if parse_ok_count != expected_evaluator_count and record.get("final_disposition") != "ABSTAIN":
                # Only fail if not marked as ABSTAIN (ABSTAIN is expected when evaluators fail)
                validator_failures.append(f"Evaluator count mismatch for {question_id}: expected {expected_evaluator_count}, got {parse_ok_count}")
        
        # Validator 2: Dossier correctness consistency
        for record in all_r1_records:
            question_id = record.get("question_id", "unknown")
            gold_answer = record.get("gold_answer")
            final_disposition = record.get("final_disposition", "UNKNOWN")
            
            # Determine final choice from Final Commit (preferred) or Round 1
            final_commit = record.get("final_commit")
            if final_commit:
                # Use Final Commit majority or unanimous choice (post-defense commitment)
                final_choice = final_commit.get("final_majority_choice") or final_commit.get("final_unanimous_choice")
            else:
                # Fallback to Round 1 majority or unanimous choice
                round1 = record.get("round1", {})
                final_choice = round1.get("majority_choice") or round1.get("unanimous_choice")
            
            if final_choice and gold_answer:
                is_correct = (final_choice == gold_answer)
                # Check if final_disposition is consistent with correctness
                # If correct, should be AUTO_ACCEPT or similar
                # If wrong and unanimous, should be UNANIMOUS_WRONG or FLAG_FALSE_CONSENSUS
                if is_correct and final_disposition in ["FLAG_FALSE_CONSENSUS", "UNANIMOUS_WRONG"]:
                    validator_failures.append(f"Correctness inconsistency for {question_id}: correct but disposition={final_disposition}")
                elif not is_correct and final_disposition == "AUTO_ACCEPT":
                    validator_failures.append(f"Correctness inconsistency for {question_id}: wrong but disposition={final_disposition}")
        
        # Validator 3: Round 2a exists when reconstruction exists and Round 2c triggered
        for record in all_r1_records:
            question_id = record.get("question_id", "unknown")
            synthesis = record.get("synthesis")
            round2a = record.get("round2a")
            round2c = record.get("round2c") or record.get("round2c")  # Support legacy
            candidate_options = record.get("candidate_options", [])
            
            if synthesis and len(candidate_options) >= 2 and round2c:
                # Round 2c was triggered, so Round 2a should exist
                if not round2a:
                    validator_failures.append(f"Round 2a missing for {question_id}: synthesis exists, candidate_options={len(candidate_options)}, round2c exists")
        
        # Validator 4: Round 2c MUST exist if candidate_options >= 2 (MANDATORY - no exceptions)
        # Also triggers for incompatibility_detected or unanimity_challenge, but those are softer
        for record in all_r1_records:
            question_id = record.get("question_id", "unknown")
            candidate_options = record.get("candidate_options", [])
            grok_analysis = record.get("grok_analysis")
            unanimity_challenge = record.get("unanimity_challenge")
            round2c = record.get("round2c")
            
            # HARD REQUIREMENT: Multiple candidates = Round 2c MUST exist
            round2c_mandatory = len(candidate_options) >= 2
            
            # Soft triggers (for single candidate edge cases)
            incompatibility_detected = False
            if grok_analysis:
                incompatibility_detected = grok_analysis.get("incompatibility_detected", False)
                reasoning_relation = grok_analysis.get("reasoning_relation", "UNKNOWN")
                if reasoning_relation in ["INCOMPATIBLE", "MIXED"]:
                    incompatibility_detected = True
            
            should_have_round2c = round2c_mandatory or incompatibility_detected or (unanimity_challenge is not None)
            
            if should_have_round2c and not round2c and record.get("final_disposition") != "ABSTAIN":
                if round2c_mandatory:
                    # CRITICAL: Mark as PIPELINE_INVALID - mandatory round was skipped
                    record["pipeline_status"] = "PIPELINE_INVALID"
                    record["pipeline_error"] = f"Round 2c (forced defense) was MANDATORY but did not run: {len(candidate_options)} candidates"
                    validator_failures.append(f"[PIPELINE_INVALID] {question_id}: Round 2c mandatory but missing (candidates={len(candidate_options)})")
                else:
                    validator_failures.append(f"Round 2c missing for {question_id}: candidate_options={len(candidate_options)}, incompatibility={incompatibility_detected}, challenge={unanimity_challenge is not None}")
        
        # Report validator results
        if validator_failures:
            log(f"\n[FAILED] Post-run validators found {len(validator_failures)} violations:", log_handle)
            for failure in validator_failures:
                log(f"  [FAILED] {failure}", log_handle)
        else:
            log("  [OK] All post-run validators passed", log_handle)
    
    # Write run config
    run_config = {
        "run_number": ctx.run_number,
        "dataset": args.dataset,
        "dataset_name": dataset_info["dataset_name"],
        "requested_split": dataset_info["requested_split"],
        "actual_split": dataset_info["actual_split"],
        "split_fallback_used": dataset_info["split_fallback_used"],
        "sample_size": len(selected_questions),
        "seed": args.seed,
        "evaluators": list(EVALUATORS),  # ["A", "B", "C", "D"]
        "analyzers": ["grok_analyzer"],  # Non-evaluator roles
        "min_valid_evaluators": MIN_VALID_EVALUATORS,
        "evaluator_models": {
            "A": "anthropic:claude-opus-4-5",
            "B": "google:gemini-3-pro-preview",
            "C": "openai:gpt-5.2 (reasoning_effort=medium)",
            "D": "xai:grok-4-1-fast-reasoning",
        },
        "synthesizer_model": "openai:gpt-5.2 (reasoning_effort=high)",
        "auditor_model": "openai:gpt-5.2 (reasoning_effort=high)",
        "synthesizer_prompt_file": "prompts/synthesizer.txt",
        "synthesizer_prompt_sha256": synthesizer_prompt_hash,
        "auditor_prompt_file": "prompts/auditor.txt",
        "auditor_prompt_sha256": auditor_prompt_hash,
        "allow_abstain": allow_abstain,
        "round1_prompt_file": "prompts/round1_evaluator.txt",
        "round1_prompt_sha256": round1_prompt_hash,
        "timestamp": datetime.now().isoformat(),
        "run_directory": str(ctx.run_dir),
    }
    
    with open(ctx.outputs_dir / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(run_config, f, indent=2)
    
    # Acceptance checks (must print at end)
    log("\n" + "=" * 70, log_handle)
    log("ACCEPTANCE CHECKS", log_handle)
    log("=" * 70, log_handle)
    
    # Load all records for acceptance checks
    all_records = []
    if round1_output.exists():
        with open(round1_output, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    all_records.append(json.loads(line))
    
    total_questions = len(all_records)
    if total_questions > 0:
        # 1. Evaluator D included count
        r1_d_count = sum(1 for r in all_records if r.get("round1", {}).get("evaluator_D") is not None)
        r2c_d_count = sum(1 for r in all_records if (r.get("round2c") or r.get("round2c")) and (r.get("round2c") or r.get("round2c", {})).get("evaluator_D") is not None)
        log(f"1. Evaluator D included count:", log_handle)
        log(f"   Round 1: evaluator_D present for {r1_d_count}/{total_questions} questions", log_handle)
        log(f"   Round 2c: evaluator_D present for {r2c_d_count}/{total_questions} questions (if run)", log_handle)
        
        # 2. Agreement pattern distribution (with 4-eval patterns)
        pattern_counts = Counter()
        for r in all_records:
            r1_pattern = r.get("round1", {}).get("agreement_pattern", "unknown")
            pattern_counts[r1_pattern] += 1
        log(f"\n2. Agreement pattern distribution (Round 1):", log_handle)
        for pattern, count in sorted(pattern_counts.items()):
            log(f"   {pattern}: {count}", log_handle)
        
        # 3. Compare vs previous run (if available - placeholder for now)
        log(f"\n3. Comparison metrics (vs previous run):", log_handle)
        log(f"   (Previous run comparison requires manual analysis)", log_handle)
        # Count questions with specific patterns
        unanimous_4_count = pattern_counts.get("unanimous_4", 0)
        split_3_1_count = pattern_counts.get("split_3_1", 0)
        split_2_2_count = pattern_counts.get("split_2_2", 0)
        split_2_1_1_count = pattern_counts.get("split_2_1_1", 0)
        split_1_1_1_1_count = pattern_counts.get("split_1_1_1_1", 0)
        log(f"   unanimous_4: {unanimous_4_count}")
        log(f"   split_3_1: {split_3_1_count}")
        log(f"   split_2_2: {split_2_2_count}")
        log(f"   split_2_1_1: {split_2_1_1_count}")
        log(f"   split_1_1_1_1: {split_1_1_1_1_count}")
        
        # Count questions where D was the lone dissenter (split_3_1)
        d_lone_dissenter = 0
        for r in all_records:
            r1_pattern = r.get("round1", {}).get("agreement_pattern", "unknown")
            if r1_pattern == "split_3_1":
                # Check if D is the minority
                r1 = r.get("round1", {})
                choices = {}
                for eval_name in EVALUATORS:
                    eval_result = r1.get(f"evaluator_{eval_name}")
                    if eval_result:
                        choices[eval_name] = eval_result.get("final_choice")
                choice_counts = Counter(choices.values())
                if len(choice_counts) == 2:
                    majority_choice = choice_counts.most_common(1)[0][0]
                    if choices.get("D") != majority_choice:
                        d_lone_dissenter += 1
        log(f"   Questions where D was lone dissenter (split_3_1): {d_lone_dissenter}")
        
        # Count questions where D flipped in round2c
        d_flipped = 0
        for r in all_records:
            r1 = r.get("round1", {})
            final_commit = r.get("final_commit", {})  # Final Commit is separate from round2c
            if r1 and final_commit:
                r1_d_result = r1.get("evaluator_D")
                fc_d_result = final_commit.get("evaluator_D")
                if r1_d_result and fc_d_result:
                    r1_choice = r1_d_result.get("final_choice")
                    fc_choice = fc_d_result.get("final_choice")  # Final Commit has final_choice at top level
                    if r1_choice and fc_choice and r1_choice != fc_choice:
                        d_flipped += 1
        log(f"   Questions where D flipped after defense: {d_flipped}")
        
        # 4. Post-run sanity checks (forensic validation)
        log(f"\n4. Post-run Sanity Checks:", log_handle)
        validation_errors = []
        validation_warnings = []
        
        for r in all_records:
            qid = r.get("question_id", "unknown")
            round1 = r.get("round1", {})
            
            # Check 1: Agreement pattern matches actual choices
            stored_pattern = round1.get("agreement_pattern", "unknown")
            actual_choices = {}
            parse_ok = {}
            for eval_name in EVALUATORS:
                eval_result = round1.get(f"evaluator_{eval_name}")
                if eval_result:
                    actual_choices[eval_name] = eval_result.get("final_choice")
                    parse_ok[eval_name] = round1.get(f"parse_ok_{eval_name}", False)
                else:
                    actual_choices[eval_name] = None
                    parse_ok[eval_name] = False
            
            # Compute actual pattern from choices (use the function defined in this file)
            computed_pattern, _, _, _, _ = compute_agreement_pattern(actual_choices, parse_ok)
            
            if stored_pattern != computed_pattern:
                validation_errors.append(f"{qid}: Stored pattern '{stored_pattern}' != computed '{computed_pattern}'")
            
            # Check 2: Round 2c should exist if candidate_set >= 2
            candidate_options = r.get("candidate_options", [])
            has_round2c = bool(r.get("round2c") or r.get("round2c"))  # Support legacy
            final_disposition = r.get("final_disposition", "")
            
            if len(candidate_options) >= 2 and not has_round2c:
                # Check if it was explicitly skipped
                if final_disposition in ["ABSTAIN", "FLAG_EPISTEMIC_BOUNDARY"]:
                    # This is OK - evaluator failure caused skip
                    pass
                else:
                    validation_warnings.append(f"{qid}: candidate_set size {len(candidate_options)} but no Round 2c (disposition: {final_disposition})")
        
        if validation_errors:
            log(f"   ❌ VALIDATION ERRORS ({len(validation_errors)}):", log_handle)
            for err in validation_errors[:10]:  # Show first 10
                log(f"      {err}", log_handle)
            if len(validation_errors) > 10:
                log(f"      ... and {len(validation_errors) - 10} more", log_handle)
        else:
            log(f"   ✓ Agreement pattern validation: PASSED", log_handle)
        
        if validation_warnings:
            log(f"   ⚠ VALIDATION WARNINGS ({len(validation_warnings)}):", log_handle)
            for warn in validation_warnings[:10]:  # Show first 10
                log(f"      {warn}", log_handle)
            if len(validation_warnings) > 10:
                log(f"      ... and {len(validation_warnings) - 10} more", log_handle)
        else:
            log(f"   ✓ Round 2c trigger validation: PASSED", log_handle)
        
        # ============================================================
        # E) Post-run Validator (per spec)
        # ============================================================
        log(f"\n   E) Post-run Pipeline Integrity Check:", log_handle)
        pipeline_not_clean = False
        pipeline_issues = []
        
        for r in all_records:
            qid = r.get("question_id", "?")
            round1 = r.get("round1", {})
            
            # E1: Check cheap_elimination exists
            if "cheap_elimination" not in round1:
                pipeline_issues.append(f"{qid}: missing cheap_elimination")
            
            # E2: Check mapping_validation.all_valid == True for all evaluators
            mapping_val = round1.get("mapping_validation", {})
            if mapping_val and not mapping_val.get("all_valid", True):
                for err in mapping_val.get("errors", []):
                    pipeline_issues.append(f"{qid}: mapping error - {err.get('error', 'unknown')}")
            
            # E3: Check for evaluator failures
            for en in EVALUATORS:
                eval_r1 = round1.get(f"evaluator_{en}", {})
                if eval_r1.get("_schema_validation_failed") and not eval_r1.get("_repair_applied"):
                    pipeline_issues.append(f"{qid}: Eval {en} schema failure (not repaired)")
        
        if pipeline_issues:
            pipeline_not_clean = True
            log(f"   ❌ PIPELINE_NOT_CLEAN ({len(pipeline_issues)} issues):", log_handle)
            for issue in pipeline_issues[:15]:  # Show first 15
                log(f"      {issue}", log_handle)
            if len(pipeline_issues) > 15:
                log(f"      ... and {len(pipeline_issues) - 15} more", log_handle)
            
            # Write issues to a separate file
            issues_file = ctx.outputs_dir / "pipeline_issues.txt"
            with open(issues_file, "w", encoding="utf-8") as f:
                f.write(f"PIPELINE_NOT_CLEAN\n")
                f.write(f"Total issues: {len(pipeline_issues)}\n\n")
                for issue in pipeline_issues:
                    f.write(f"{issue}\n")
            log(f"   Issues written to: {issues_file}", log_handle)
        else:
            log(f"   ✓ Pipeline integrity check: CLEAN", log_handle)
    
    log("\n" + "=" * 70, log_handle)
    log("Run Complete", log_handle)
    log(f"Results: {ctx.outputs_dir}", log_handle)
    log("=" * 70, log_handle)
    
    log_handle.close()

if __name__ == "__main__":
    run()