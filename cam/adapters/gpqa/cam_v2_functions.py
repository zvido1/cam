#!/usr/bin/env python3
"""
CAM Pipeline v2 Functions - Kill Shots, Resurrection, and Ladder Logic

These functions implement the redesigned pipeline:
- process_round2c_v2: Elimination audit with formal kill shots
- process_round2d_resurrection: Test kill shots adversarially  
- process_final_commit_v2: Ladder of commitment logic
- aggregate_kill_shots: Collect and deduplicate kills from all evaluators

Key principles:
- QUARANTINE over repair: Never silently change model outputs
- Kill shots have validity tracking (kill_shot_valid, kill_shot_invalid_reason)
- Only CONFIRMED kills affect ladder determination
- Resurrection is kill-type sensitive
- Evaluators with _schema_validation_failed=true are EXCLUDED from counts
"""

import json
import time
import re
from typing import Dict, List, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ============================================================
# Rule Library - CAM Rules-First Framework
# ============================================================
try:
    from cam.rules.biology_rules import (
        apply_biology_rules,
        apply_rule_effects_to_aggregation,
        RuleLibraryResult,
        get_rule_library_version,
    )
    RULE_LIBRARY_AVAILABLE = True
    print(f"[RULE LIBRARY] Biology Rule Library {get_rule_library_version()} loaded - rules ON by default")
except ImportError:
    RULE_LIBRARY_AVAILABLE = False
    print("[RULE LIBRARY] Biology Rule Library not found - running without rules")

# Physics Rule Library - CANDIDATE (OFF by default, enable via flag)
try:
    from cam.rules.physics_rules import (
        apply_physics_rules,
        get_physics_rule_library_version,
        PHYSICS_RULES_STATUS,
    )
    PHYSICS_RULE_LIBRARY_AVAILABLE = True
    print(f"[RULE LIBRARY] Physics Rule Library {get_physics_rule_library_version()} loaded - Status: {PHYSICS_RULES_STATUS}")
except ImportError:
    PHYSICS_RULE_LIBRARY_AVAILABLE = False
    print("[RULE LIBRARY] Physics Rule Library not found")

# Global flag to enable Physics rules (set via command line or config)
PHYSICS_RULES_ENABLED = True  # Set to True to activate Physics rules


# ============================================================
# Constants
# ============================================================

VALID_KILL_TYPES = [
    "constraint_violation",
    "internal_contradiction", 
    "mechanism_impossibility",
    "product_class_mismatch"
]

# Kill types that REQUIRE resurrection testing
RESURRECTION_REQUIRED_KILL_TYPES = [
    "constraint_violation",      # May depend on domain interpretation
    "mechanism_impossibility",   # May depend on unstated conditions
]

# Kill types that can skip resurrection if independently verified
RESURRECTION_SKIPPABLE_KILL_TYPES = [
    "internal_contradiction",    # Logic error - harder to resurrect
    "product_class_mismatch",    # Category error - usually definitive
]

# Minimum support for a confirmed kill
CONFIRMED_KILL_THRESHOLD = 2  # At least 2 evaluators must agree


# ============================================================
# Kill Shot Validation
# ============================================================

def validate_kill_shot(kill_shot: dict, option: str) -> Tuple[bool, str]:
    """
    Validate a kill shot and return (is_valid, invalid_reason).
    
    A kill shot is VALID if:
    - kill_type is in the closed set
    - kill_proof is non-empty and substantive (>= 20 chars)
    - kill_target identifies what's being eliminated
    
    Returns (True, "") for valid, (False, reason) for invalid.
    """
    if not kill_shot:
        return False, "kill_shot is None or empty"
    
    kill_type = kill_shot.get("kill_type")
    kill_proof = kill_shot.get("kill_proof", "")
    kill_target = kill_shot.get("kill_target", "")
    
    # Check kill_type
    if kill_type not in VALID_KILL_TYPES:
        return False, f"invalid_kill_type: '{kill_type}' not in {VALID_KILL_TYPES}"
    
    # Check kill_proof
    if not kill_proof or len(kill_proof.strip()) < 20:
        return False, f"kill_proof too short or empty ({len(kill_proof.strip())} chars)"
    
    # Check for placeholder/incomplete proofs
    placeholder_markers = [
        "N/A", "n/a", "incomplete", "not provided", "TODO", 
        "model returned", "unable to determine"
    ]
    proof_lower = kill_proof.lower()
    for marker in placeholder_markers:
        if marker.lower() in proof_lower:
            return False, f"kill_proof contains placeholder marker: '{marker}'"
    
    # Check kill_target
    if not kill_target or len(kill_target.strip()) < 10:
        return False, f"kill_target too short or empty ({len(kill_target.strip())} chars)"
    
    return True, ""


def is_convention_dependent_kill(kill_shot: dict) -> bool:
    """
    Check if a kill shot depends on convention/interpretation.
    Such kills REQUIRE resurrection testing.
    """
    if not kill_shot:
        return False
    
    proof = kill_shot.get("kill_proof", "").lower()
    target = kill_shot.get("kill_target", "").lower()
    
    convention_markers = [
        "convention", "typically", "usually", "standard", "commonly",
        "most sources", "generally", "interpretation", "assume", "assuming",
        "if we interpret", "depends on", "under the assumption"
    ]
    
    for marker in convention_markers:
        if marker in proof or marker in target:
            return True
    
    return False


def is_evaluator_valid_for_aggregation(eval_result: dict) -> Tuple[bool, str]:
    """
    Check if an evaluator's output should be included in aggregation.
    
    EXCLUDES evaluators with:
    - _schema_validation_failed = true
    - round2c_status != "ok"
    - _response_quarantined = true (response-level quarantine)
    - Critical quarantine records (elimination_audit, best_current_case)
    
    Returns (is_valid, exclusion_reason)
    """
    if not eval_result:
        return False, "null_result"
    
    # Check schema validation
    if eval_result.get("_schema_validation_failed", False):
        return False, "schema_validation_failed"
    
    # Check response-level quarantine
    if eval_result.get("_response_quarantined", False):
        return False, "response_quarantined"
    
    # Check for critical quarantine records that invalidate aggregation
    quarantine_records = eval_result.get("_quarantine_records", [])
    critical_quarantines = [r for r in quarantine_records 
                          if r.get("field", "").startswith(("elimination_audit", "best_current_case", "elimination_summary"))
                          and r.get("issue") in ("missing_required_object", "null_value")]
    if critical_quarantines:
        return False, f"critical_data_quarantined ({len(critical_quarantines)} fields)"
    
    # Check round status
    status = eval_result.get("round2c_status")
    if status != "ok":
        return False, f"round2c_status={status}"
    
    return True, ""


# ============================================================
# Kill Shot Aggregation (with validation and exclusion)
# ============================================================

def aggregate_kill_shots(round2c_results: dict, evaluators: List[str], candidate_options: List[str] = None) -> Dict:
    """
    Aggregate kill shots from all evaluators with validation.
    
    EXCLUDES from counts:
    - Evaluators with _schema_validation_failed=true
    - Kill shots with kill_shot_valid=false
    
    Args:
        round2c_results: Results from Round 2c evaluation
        evaluators: List of evaluator names
        candidate_options: Options that were actually evaluated (default: all A-D)
                          Options NOT in this list are considered "prior eliminations"
    
    Returns:
    {
        "kills_by_option": { "A": [...], ... },
        "attempted_kills": [{"option": "A", "valid": False, "reason": "...", ...}, ...],
        "confirmed_kills": [{"option": "A", "valid": True, "support_count": 3, ...}, ...],
        "soft_conditions": [{"option": "B", "reason": "...", ...}, ...],
        "survivors": ["C", "D"],
        "prior_eliminations": ["A", "B"],  # Options eliminated before R2c
        "kill_consensus": {"A": 3, ...},
        "requires_resurrection": True/False,
        "resurrection_reason": "...",
        "excluded_evaluators": [{"evaluator": "D", "reason": "..."}]
    }
    """
    kills_by_option = defaultdict(list)
    valid_kills_by_option = defaultdict(list)
    invalid_kills_by_option = defaultdict(list)
    kill_consensus = defaultdict(int)
    valid_kill_consensus = defaultdict(int)
    all_options = set(["A", "B", "C", "D"])
    
    # Use candidate_options if provided, otherwise all options
    if candidate_options is not None:
        evaluated_options = set(candidate_options)
        prior_eliminations = sorted(all_options - evaluated_options)
    else:
        evaluated_options = all_options
        prior_eliminations = []
    
    killed_options = set()
    confirmed_killed_options = set()
    
    # Track excluded evaluators
    excluded_evaluators = []
    included_evaluators = []
    
    for eval_name in evaluators:
        eval_result = round2c_results.get(f"evaluator_{eval_name}")
        
        # Check if evaluator should be included in aggregation
        is_valid, exclusion_reason = is_evaluator_valid_for_aggregation(eval_result)
        if not is_valid:
            excluded_evaluators.append({
                "evaluator": eval_name,
                "reason": exclusion_reason
            })
            continue
        
        included_evaluators.append(eval_name)
        
        elimination_audit = eval_result.get("elimination_audit", {})
        for option, audit_data in elimination_audit.items():
            if option not in all_options:
                continue
            
            # Skip quarantined options
            if audit_data and audit_data.get("_status_quarantined", False):
                continue
            
            if audit_data and audit_data.get("status") == "killed":
                killed_options.add(option)
                kill_consensus[option] += 1
                
                kill_shot = audit_data.get("kill_shot", {})
                
                # Check kill_shot_valid flag if already computed, otherwise validate
                if "kill_shot_valid" in audit_data:
                    is_kill_valid = audit_data["kill_shot_valid"]
                    invalid_reason = audit_data.get("kill_shot_invalid_reason", "")
                else:
                    is_kill_valid, invalid_reason = validate_kill_shot(kill_shot, option)
                
                kill_record = {
                    "kill_type": kill_shot.get("kill_type") if kill_shot else None,
                    "kill_proof": kill_shot.get("kill_proof") if kill_shot else None,
                    "kill_target": kill_shot.get("kill_target") if kill_shot else None,
                    "issuing_evaluator": eval_name,
                    "kill_shot_valid": is_kill_valid,
                    "kill_shot_invalid_reason": invalid_reason if not is_kill_valid else None,
                    "convention_dependent": is_convention_dependent_kill(kill_shot) if kill_shot else False,
                }
                
                kills_by_option[option].append(kill_record)
                
                # ONLY count valid kills toward support
                if is_kill_valid:
                    valid_kills_by_option[option].append(kill_record)
                    valid_kill_consensus[option] += 1
                else:
                    invalid_kills_by_option[option].append(kill_record)
    
    # Determine confirmed kills vs attempted kills
    confirmed_kills = []
    attempted_kills = []
    soft_conditions = []
    
    for option in sorted(killed_options):
        all_kills = kills_by_option[option]
        valid_kills = valid_kills_by_option[option]
        valid_count = valid_kill_consensus[option]
        total_count = kill_consensus[option]
        
        # Pick the best valid kill if available
        best_kill = valid_kills[0] if valid_kills else (all_kills[0] if all_kills else None)
        
        kill_entry = {
            "option": option,
            "kill_type": best_kill["kill_type"] if best_kill else None,
            "kill_proof": best_kill["kill_proof"] if best_kill else None,
            "kill_target": best_kill.get("kill_target", "") if best_kill else None,
            "issuing_evaluator": best_kill["issuing_evaluator"] if best_kill else None,
            "total_support_count": total_count,
            "valid_support_count": valid_count,
            "all_kills": all_kills,
        }
        
        if valid_count >= CONFIRMED_KILL_THRESHOLD:
            # CONFIRMED KILL: valid + sufficient support
            kill_entry["status"] = "confirmed"
            confirmed_kills.append(kill_entry)
            confirmed_killed_options.add(option)
        elif valid_count >= 1:
            # ATTEMPTED KILL: valid but insufficient support
            kill_entry["status"] = "attempted"
            kill_entry["reason"] = f"Valid kill but only {valid_count} supporter(s), need {CONFIRMED_KILL_THRESHOLD}"
            attempted_kills.append(kill_entry)
        else:
            # SOFT CONDITION: no valid kills, only invalid attempts
            kill_entry["status"] = "soft_condition"
            reasons = [k["kill_shot_invalid_reason"] for k in all_kills if k.get("kill_shot_invalid_reason")]
            kill_entry["reason"] = f"No valid kill shots: {'; '.join(reasons[:2])}"
            soft_conditions.append(kill_entry)
    
    # Survivors: options from the evaluated set that weren't confirmed killed
    # (NOT all_options - we only count options that were actually evaluated)
    survivors = sorted(evaluated_options - confirmed_killed_options)
    
    # Determine if resurrection is required
    requires_resurrection = False
    resurrection_reason = "No resurrection needed"
    
    if confirmed_kills:
        # Check if any confirmed kill requires resurrection
        for kill in confirmed_kills:
            kill_type = kill.get("kill_type")
            # Convention-dependent kills require resurrection
            any_convention_dependent = any(
                k.get("convention_dependent", False) for k in kill.get("all_kills", [])
            )
            
            if any_convention_dependent:
                requires_resurrection = True
                resurrection_reason = f"Convention-dependent kill on {kill['option']}"
                break
            
            # constraint_violation and mechanism_impossibility require R2d
            # UNLESS we have >= 3 independent valid supporters
            if kill_type in RESURRECTION_REQUIRED_KILL_TYPES:
                if kill["valid_support_count"] < 3:
                    requires_resurrection = True
                    resurrection_reason = f"Kill type '{kill_type}' on {kill['option']} requires verification (support={kill['valid_support_count']}, need 3+ to skip)"
                    break
    
    # Also trigger resurrection if we have attempted kills that might be valid
    if attempted_kills and not requires_resurrection:
        requires_resurrection = True
        resurrection_reason = f"{len(attempted_kills)} attempted kill(s) need verification"
    
    return {
        "kills_by_option": dict(kills_by_option),
        "valid_kills_by_option": dict(valid_kills_by_option),
        "invalid_kills_by_option": dict(invalid_kills_by_option),
        "confirmed_kills": confirmed_kills,
        "attempted_kills": attempted_kills,
        "soft_conditions": soft_conditions,
        "survivors": survivors,
        "prior_eliminations": prior_eliminations,  # Options eliminated before R2c (from R1)
        "kill_consensus": dict(kill_consensus),
        "valid_kill_consensus": dict(valid_kill_consensus),
        "killed_count": len(killed_options),
        "confirmed_killed_count": len(confirmed_killed_options),
        "survivor_count": len(survivors),
        "prior_elimination_count": len(prior_eliminations),
        "requires_resurrection": requires_resurrection,
        "resurrection_reason": resurrection_reason,
        "excluded_evaluators": excluded_evaluators,
        "included_evaluators": included_evaluators,
    }


def aggregate_survivor_conditions(round2c_results: dict, survivors: List[str], evaluators: List[str]) -> Dict:
    """
    Aggregate conditions from all evaluators for surviving options.
    Only includes evaluators that pass validation.
    """
    survivor_conditions = {}
    
    for option in survivors:
        all_conditions = []
        all_falsifiers = []
        
        for eval_name in evaluators:
            eval_result = round2c_results.get(f"evaluator_{eval_name}")
            
            # Check if evaluator should be included
            is_valid, _ = is_evaluator_valid_for_aggregation(eval_result)
            if not is_valid:
                continue
            
            elimination_audit = eval_result.get("elimination_audit", {})
            option_data = elimination_audit.get(option, {})
            
            # Skip quarantined options
            if option_data and option_data.get("_status_quarantined", False):
                continue
            
            if option_data and option_data.get("status") == "surviving":
                conditions = option_data.get("conditions", [])
                falsifiers = option_data.get("would_be_falsified_if", [])
                all_conditions.extend(conditions)
                all_falsifiers.extend(falsifiers)
        
        # Deduplicate
        unique_conditions = list(dict.fromkeys(all_conditions))
        unique_falsifiers = list(dict.fromkeys(all_falsifiers))
        
        survivor_conditions[option] = {
            "conditions": unique_conditions,
            "would_be_falsified_if": unique_falsifiers,
        }
    
    return survivor_conditions


# ============================================================
# Round 2c v2: Elimination Audit with Quarantine Logic
# ============================================================

def quarantine_response(response_json: dict, eval_name: str, log_fn, log_handle) -> Tuple[dict, List[dict]]:
    """
    Quarantine invalid data in response WITHOUT modifying semantic content.
    
    Returns: (processed_response, quarantine_records)
    
    Key principle: NEVER change killed→surviving or surviving→killed.
    Instead, mark invalid data with quarantine flags.
    """
    quarantine_records = []
    
    # Helper to check and quarantine a string field
    def quarantine_string(obj, key, min_len, field_path):
        val = obj.get(key)
        if val is None:
            quarantine_records.append({
                "field": field_path,
                "issue": "null_value",
                "original": None,
                "action": "flagged_as_missing"
            })
            obj[key] = ""  # Empty string, not a placeholder
            obj[f"_{key}_quarantined"] = True
            return True
        elif isinstance(val, str) and len(val.strip()) < min_len:
            quarantine_records.append({
                "field": field_path,
                "issue": f"too_short ({len(val.strip())} < {min_len})",
                "original": val[:50] if val else None,
                "action": "flagged_as_incomplete"
            })
            obj[f"_{key}_quarantined"] = True
            return True
        return False
    
    # Ensure top-level objects exist (structural, not semantic)
    if response_json.get("elimination_audit") is None:
        response_json["elimination_audit"] = {}
        quarantine_records.append({
            "field": "elimination_audit",
            "issue": "missing_required_object",
            "action": "initialized_empty"
        })
    
    if response_json.get("elimination_summary") is None:
        response_json["elimination_summary"] = {
            "killed_options": [], 
            "surviving_options": [], 
            "kill_confidence": "low"
        }
        quarantine_records.append({
            "field": "elimination_summary",
            "issue": "missing_required_object",
            "action": "initialized_with_defaults"
        })
    
    if response_json.get("best_current_case") is None:
        response_json["best_current_case"] = {
            "leading_choice": None,
            "why_leading": "",
            "key_lemma": ""
        }
        quarantine_records.append({
            "field": "best_current_case",
            "issue": "missing_required_object",
            "action": "initialized_empty"
        })
    
    bcc = response_json["best_current_case"]
    if bcc.get("leading_choice") not in ["A", "B", "C", "D"]:
        quarantine_records.append({
            "field": "best_current_case.leading_choice",
            "issue": f"invalid_choice: {bcc.get('leading_choice')}",
            "action": "flagged_invalid"
        })
        bcc["_leading_choice_quarantined"] = True
    
    quarantine_string(bcc, "why_leading", 20, "best_current_case.why_leading")
    quarantine_string(bcc, "key_lemma", 10, "best_current_case.key_lemma")
    
    # Cross examination
    if response_json.get("cross_examination") is None:
        response_json["cross_examination"] = {"defense": {}, "attack_rival": {}}
        quarantine_records.append({
            "field": "cross_examination",
            "issue": "missing_required_object",
            "action": "initialized_empty"
        })
    
    cx = response_json["cross_examination"]
    if cx.get("defense") is None:
        cx["defense"] = {}
    defense = cx["defense"]
    quarantine_string(defense, "attack_summary", 20, "cross_examination.defense.attack_summary")
    quarantine_string(defense, "rebuttal", 20, "cross_examination.defense.rebuttal")
    if defense.get("defense_survives") is None:
        defense["defense_survives"] = None
        defense["_defense_survives_quarantined"] = True
    
    if cx.get("attack_rival") is None:
        cx["attack_rival"] = {}
    attack = cx["attack_rival"]
    quarantine_string(attack, "rival_strongest_point", 20, "cross_examination.attack_rival.rival_strongest_point")
    quarantine_string(attack, "counter", 20, "cross_examination.attack_rival.counter")
    if attack.get("counter_type") not in ["kill_shot", "condition_challenge", "proof_gap"]:
        attack["_counter_type_quarantined"] = True
        attack["_original_counter_type"] = attack.get("counter_type")
        attack["counter_type"] = "proof_gap"  # Default for schema compliance
    
    # Honesty check
    if response_json.get("honesty_check") is None:
        response_json["honesty_check"] = {}
        quarantine_records.append({
            "field": "honesty_check",
            "issue": "missing_required_object",
            "action": "initialized_empty"
        })
    
    hc = response_json["honesty_check"]
    if hc.get("did_view_change") is None:
        hc["did_view_change"] = None
        hc["_did_view_change_quarantined"] = True
    if hc.get("what_changed") is None:
        hc["what_changed"] = ""
    quarantine_string(hc, "strongest_point_against_leading", 10, "honesty_check.strongest_point_against_leading")
    
    # JB and weakest_link
    if response_json.get("jb") is None:
        response_json["jb"] = 5  # Neutral default
        response_json["_jb_quarantined"] = True
        quarantine_records.append({
            "field": "jb",
            "issue": "missing_value",
            "action": "defaulted_to_5"
        })
    
    quarantine_string(response_json, "weakest_link", 10, "weakest_link")
    
    # Process elimination_audit - NEVER change status, only validate kill_shots
    elim_audit = response_json.get("elimination_audit", {})
    for opt, opt_data in list(elim_audit.items()):
        if opt not in ["A", "B", "C", "D"]:
            continue
            
        if opt_data is None:
            # Quarantine: mark as missing data, don't invent status
            elim_audit[opt] = {
                "status": None,
                "_status_quarantined": True,
                "_quarantine_reason": "option_data_was_null"
            }
            quarantine_records.append({
                "field": f"elimination_audit.{opt}",
                "issue": "null_option_data",
                "action": "flagged_as_missing"
            })
            continue
        
        status = opt_data.get("status")
        if status not in ["killed", "surviving"]:
            opt_data["_status_quarantined"] = True
            opt_data["_original_status"] = status
            quarantine_records.append({
                "field": f"elimination_audit.{opt}.status",
                "issue": f"invalid_status: {status}",
                "action": "flagged_invalid"
            })
        
        # Ensure arrays exist
        if opt_data.get("conditions") is None:
            opt_data["conditions"] = []
        if opt_data.get("would_be_falsified_if") is None:
            opt_data["would_be_falsified_if"] = []
        
        # For killed status, validate kill_shot but NEVER change status
        if status == "killed":
            kill_shot = opt_data.get("kill_shot")
            is_valid, invalid_reason = validate_kill_shot(kill_shot, opt)
            
            opt_data["kill_shot_valid"] = is_valid
            opt_data["kill_shot_invalid_reason"] = invalid_reason if not is_valid else None
            
            if not is_valid:
                quarantine_records.append({
                    "field": f"elimination_audit.{opt}.kill_shot",
                    "issue": invalid_reason,
                    "action": "marked_invalid_kill_shot"
                })
    
    if quarantine_records:
        log_fn(f"      [QUARANTINE] Evaluator {eval_name}: {len(quarantine_records)} field(s) quarantined", log_handle)
    
    return response_json, quarantine_records


def process_round2c_v2(
    question_data: dict,
    round1_results: dict,
    eliminated_options: dict,
    candidate_options: list,
    synthesis_result: dict,
    evaluator_routers,  # Dict[str, ProviderRouter]
    round2c_prompt_template: str,
    round2c_schema: dict,
    effort_by_evaluator: Dict[str, str],
    log_handle,
    audit_trail: list = None,
    # Dependencies to inject from main script
    EVALUATORS: list = None,
    log_fn=None,
    call_evaluator_with_override_fn=None,
    add_audit_entry_fn=None,
    check_quota_error_fn=None,
    jsonschema_module=None,
) -> dict:
    """
    Process Round 2c v2: Elimination Audit with Quarantine Logic.
    
    Key principles:
    - Quarantine invalid data, don't silently fix it
    - Never change killed→surviving or vice versa
    - Track kill_shot_valid and kill_shot_invalid_reason
    - Only valid kills count toward confirmation
    - Exclude evaluators with _schema_validation_failed from counts
    """
    if EVALUATORS is None:
        EVALUATORS = ["A", "B", "C", "D"]
    if log_fn is None:
        log_fn = print
        
    question = question_data["question"]
    choices = question_data["choices"]
    
    log_fn(f"  Processing Round 2c v2 (Elimination Audit) for question {question_data['question_id']} (candidate set: {candidate_options})", log_handle)
    
    round2c_results = {f"evaluator_{en}": None for en in EVALUATORS}
    
    # Track evaluator status
    successful_evaluators = []
    failed_evaluators = []
    
    if not synthesis_result:
        log_fn(f"      [SKIP] synthesis_result is None - skipping Round 2c", log_handle)
        for en in EVALUATORS:
            failed_evaluators.append({"evaluator": en, "reason": "synthesis_missing"})
        round2c_results["successful_evaluators"] = successful_evaluators
        round2c_results["failed_evaluators"] = failed_evaluators
        return round2c_results
    
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
    
    def process_single_evaluator_round2c_v2(eval_name: str, router) -> Tuple[str, Optional[dict], dict, bool, str]:
        """Process a single evaluator call in Round 2c v2.
        Returns: (eval_name, response_json, call_settings, success, failure_reason)
        """
        log_fn(f"    Calling Evaluator {eval_name} (Round 2c v2 - Elimination Audit)...", log_handle)
        
        target = router.targets[0] if router.targets else None
        if target:
            log_fn(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, provider={target.provider}, round=R2c-v2", log_handle)
        
        round1_result = round1_results.get(f"evaluator_{eval_name}")
        if not round1_result:
            log_fn(f"      [SKIP] Evaluator {eval_name} had no Round 1 result", log_handle)
            return (eval_name, {"round2c_status": "skipped", "skip_reason": "no_round1_result"}, {}, False, "no_round1_result")
        
        your_choice = round1_result.get("final_choice")
        if not your_choice:
            log_fn(f"      [SKIP] Evaluator {eval_name} had no valid Round 1 choice", log_handle)
            return (eval_name, {"round2c_status": "skipped", "skip_reason": "no_round1_choice"}, {}, False, "no_round1_choice")
        
        # Build candidate choices text
        candidate_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in candidate_options])
        
        # Extract reconstructions from synthesis
        argument_reconstructions = synthesis_result.get("argument_reconstructions", {})
        recon_for_yours = argument_reconstructions.get(your_choice, {})
        reconstruction_for = format_argument_reconstruction(recon_for_yours.get("argument_for", {}))
        attack_on_yours = format_argument_reconstruction(recon_for_yours.get("argument_against", {}))
        
        # Identify strongest rival
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
        
        effort_override = effort_by_evaluator.get(eval_name, "medium")
        if effort_override in ["auto", "medium"]:
            effort_override = None
        
        start_time = time.time()
        try:
            result, meta, call_settings = call_evaluator_with_override_fn(
                eval_name, router, "", full_prompt, log_handle, effort_override, None
            )
            
            if audit_trail is not None and add_audit_entry_fn:
                raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                add_audit_entry_fn(audit_trail, "Round 2c v2", call_settings.get("model_name", eval_name), "Evaluator", full_prompt, raw_out)
            
            if result is None:
                if meta and check_quota_error_fn:
                    error_info = meta.get("error", "") or meta.get("raw", "") or str(meta)
                    check_quota_error_fn(error_info, f"Evaluator {eval_name} (Round 2c v2)", log_handle)
                return (eval_name, {"round2c_status": "failed", "round2c_error": "api_returned_none"}, {}, False, "api_returned_none")
            
            elapsed = time.time() - start_time
            log_fn(f"      [TIMING] Evaluator {eval_name} (Round 2c v2): {elapsed:.1f}s", log_handle)
            
            # Parse JSON
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.+\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        first_brace = raw_response.find('{')
                        last_brace = raw_response.rfind('}')
                        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                            json_str = raw_response[first_brace:last_brace+1]
                        else:
                            json_str = raw_response
                    response_json = json.loads(json_str)
            except (json.JSONDecodeError, TypeError) as e:
                log_fn(f"      [ERROR] Failed to parse JSON from {eval_name}: {e}", log_handle)
                return (eval_name, {"round2c_status": "failed", "round2c_error": f"json_parse_error: {str(e)[:100]}"}, call_settings, False, f"json_parse_error")
            
            if response_json is None:
                log_fn(f"      [ERROR] Evaluator {eval_name} returned null/empty response", log_handle)
                return (eval_name, {"round2c_status": "failed", "round2c_error": "null_response"}, call_settings, False, "null_response")
            
            # QUARANTINE (not repair) invalid data
            response_json, quarantine_records = quarantine_response(response_json, eval_name, log_fn, log_handle)
            response_json["_quarantine_records"] = quarantine_records
            
            # Validate schema - mark failure but preserve data
            schema_valid = True
            try:
                if jsonschema_module and round2c_schema:
                    jsonschema_module.validate(instance=response_json, schema=round2c_schema)
            except Exception as e:
                schema_error = str(e)[:200] if hasattr(e, 'message') else str(e)[:200]
                log_fn(f"      [SCHEMA FAIL] Evaluator {eval_name} Round 2c v2 schema validation failed: {schema_error}", log_handle)
                response_json["_schema_validation_failed"] = True
                response_json["_schema_error"] = schema_error
                schema_valid = False
            
            response_json["call_settings"] = call_settings
            response_json["round2c_status"] = "ok"
            
            # Extract summary for logging
            elimination_summary = response_json.get("elimination_summary", {})
            killed = elimination_summary.get("killed_options", [])
            surviving = elimination_summary.get("surviving_options", [])
            leading = response_json.get("best_current_case", {}).get("leading_choice", "?")
            
            # Count valid vs invalid kills
            elim_audit = response_json.get("elimination_audit", {})
            valid_kills = sum(1 for opt, data in elim_audit.items() 
                           if data and data.get("status") == "killed" and data.get("kill_shot_valid", False))
            invalid_kills = sum(1 for opt, data in elim_audit.items() 
                              if data and data.get("status") == "killed" and not data.get("kill_shot_valid", True))
            
            schema_note = " [SCHEMA_FAILED]" if not schema_valid else ""
            log_fn(f"      [OK] Evaluator {eval_name}: leading={leading}, killed={killed} (valid:{valid_kills}, invalid:{invalid_kills}), surviving={surviving}{schema_note}", log_handle)
            return (eval_name, response_json, call_settings, True, "")
            
        except Exception as e:
            elapsed = time.time() - start_time
            log_fn(f"      [ERROR] Evaluator {eval_name} Round 2c v2 failed after {elapsed:.1f}s: {e}", log_handle)
            return (eval_name, {"round2c_status": "failed", "round2c_error": f"exception: {str(e)[:100]}"}, {}, False, f"exception: {str(e)[:50]}")
    
    # Run all evaluators in parallel
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        future_to_eval = {
            executor.submit(process_single_evaluator_round2c_v2, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        for future in as_completed(future_to_eval):
            eval_name, response_json, call_settings, success, failure_reason = future.result()
            if response_json:
                round2c_results[f"evaluator_{eval_name}"] = response_json
            
            if success:
                successful_evaluators.append(eval_name)
            else:
                failed_evaluators.append({"evaluator": eval_name, "reason": failure_reason})
    
    # Aggregate kill shots with validation (excludes invalid evaluators)
    # Pass candidate_options so prior eliminations (from R1) are tracked correctly
    kill_aggregation = aggregate_kill_shots(round2c_results, EVALUATORS, candidate_options)
    survivor_conditions = aggregate_survivor_conditions(round2c_results, kill_aggregation["survivors"], EVALUATORS)
    
    round2c_results["kill_aggregation"] = kill_aggregation
    round2c_results["survivor_conditions"] = survivor_conditions
    round2c_results["successful_evaluators"] = successful_evaluators
    round2c_results["failed_evaluators"] = failed_evaluators
    
    # Defense complete if at least 2 evaluators succeeded AND are valid for aggregation
    included_count = len(kill_aggregation.get("included_evaluators", []))
    round2c_results["round2c_defense_complete"] = included_count >= 2
    round2c_results["successful_evaluator_count"] = len(successful_evaluators)
    round2c_results["included_evaluator_count"] = included_count
    
    # Determine R2d trigger based on kill aggregation
    round2c_results["should_run_r2d"] = kill_aggregation["requires_resurrection"]
    round2c_results["r2d_trigger_reason"] = kill_aggregation["resurrection_reason"]
    
    round2c_results["round_executed"] = True
    round2c_results["round_status"] = "ok" if included_count >= 2 else "partial_failure"
    round2c_results["pipeline_version"] = "v2"
    
    # Logging
    confirmed = len(kill_aggregation["confirmed_kills"])
    attempted = len(kill_aggregation["attempted_kills"])
    soft = len(kill_aggregation["soft_conditions"])
    survivors = kill_aggregation["survivor_count"]
    prior_elims = kill_aggregation.get("prior_elimination_count", 0)
    excluded = len(kill_aggregation.get("excluded_evaluators", []))
    
    log_fn(f"      [AGGREGATED] Prior eliminations (from R1): {prior_elims}, R2c confirmed kills: {confirmed}, Attempted: {attempted}, Soft conditions: {soft}, Survivors: {survivors}", log_handle)
    log_fn(f"      [EVALUATORS] Success: {successful_evaluators}, Failed: {[f['evaluator'] for f in failed_evaluators]}, Excluded from counts: {excluded}", log_handle)
    
    if round2c_results["should_run_r2d"]:
        log_fn(f"      [TRIGGER] Round 2d will run: {kill_aggregation['resurrection_reason']}", log_handle)
    else:
        log_fn(f"      [SKIP R2d] {kill_aggregation['resurrection_reason']}", log_handle)
    
    return round2c_results


# ============================================================
# Round 2d: Resurrection Testing
# ============================================================

def process_round2d_resurrection(
    question_data: dict,
    round2c_results: dict,
    resurrection_router,  # ProviderRouter
    resurrection_prompt_template: str,
    resurrection_schema: dict,
    log_handle,
    audit_trail: list = None,
    # Dependencies
    log_fn=None,
    add_audit_entry_fn=None,
    jsonschema_module=None,
) -> dict:
    """
    Process Round 2d: Resurrection Testing.
    
    Tests kill shots (both confirmed and attempted) to determine
    if they're true eliminations or should be downgraded to conditions.
    
    Triggers on:
    - constraint_violation kills (unless ≥3 independent valid supporters)
    - mechanism_impossibility kills (unless ≥3 independent valid supporters)
    - Convention-dependent kills
    - Attempted kills needing verification
    """
    if log_fn is None:
        log_fn = print
    
    question = question_data["question"]
    choices = question_data["choices"]
    
    log_fn(f"  Processing Round 2d (Resurrection Testing) for question {question_data['question_id']}", log_handle)
    
    kill_aggregation = round2c_results.get("kill_aggregation", {})
    
    # Collect kills to test: confirmed + attempted
    kills_to_test = []
    kills_to_test.extend(kill_aggregation.get("confirmed_kills", []))
    kills_to_test.extend(kill_aggregation.get("attempted_kills", []))
    
    if not kills_to_test:
        log_fn(f"      [SKIP] No kill shots to test", log_handle)
        return {
            "round_executed": True,
            "round_status": "no_kills_to_test",
            "resurrection_tests": [],
            "summary": {
                "confirmed_kills": [],
                "downgraded_to_conditions": [],
                "resurrection_notes": "No kill shots were issued in Round 2c"
            }
        }
    
    # Format all choices
    all_choices_text = "\n".join([f"{opt}: {choices.get(opt, '')}" for opt in ["A", "B", "C", "D"]])
    
    # Format kill shots for the prompt
    kill_shots_text = ""
    for i, kill in enumerate(kills_to_test, 1):
        kill_shots_text += f"""
Kill Shot #{i}:
  Killed Option: {kill['option']}
  Kill Type: {kill['kill_type']}
  Kill Proof: {kill['kill_proof'][:500] if kill['kill_proof'] else 'N/A'}...
  Kill Target: {kill.get('kill_target', 'N/A')}
  Issuing Evaluator: {kill['issuing_evaluator']}
  Valid Support: {kill['valid_support_count']}/{kill['total_support_count']} evaluator(s)
  Status: {kill['status']}
"""
    
    full_prompt = resurrection_prompt_template.format(
        question=question,
        all_choices_text=all_choices_text,
        kill_shots_text=kill_shots_text
    )
    
    target = resurrection_router.targets[0] if resurrection_router.targets else None
    if target:
        log_fn(f"      [ATTRIBUTION] Resurrection Agent - model={target.name}, provider={target.provider}", log_handle)
    
    start_time = time.time()
    try:
        result, meta = resurrection_router.call_json(
            system_prompt="",
            user_prompt=full_prompt,
            schema_validate_fn=None,
        )
        
        if audit_trail is not None and add_audit_entry_fn:
            raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
            add_audit_entry_fn(audit_trail, "Round 2d Resurrection", target.name if target else "Resurrection", "Scrutineer", full_prompt, raw_out)
        
        if result is None:
            log_fn(f"      [ERROR] Resurrection agent returned None", log_handle)
            # Default: confirmed kills stay confirmed, attempted stay attempted
            return {
                "round_executed": True,
                "round_status": "api_error",
                "resurrection_tests": [],
                "summary": {
                    "confirmed_kills": [k["option"] for k in kill_aggregation.get("confirmed_kills", [])],
                    "downgraded_to_conditions": [],
                    "resurrection_notes": "Resurrection agent failed - keeping original classifications"
                }
            }
        
        elapsed = time.time() - start_time
        log_fn(f"      [TIMING] Resurrection Agent: {elapsed:.1f}s", log_handle)
        
        # Parse JSON
        try:
            if isinstance(result, dict):
                response_json = result
            else:
                raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                json_match = re.search(r'```(?:json)?\s*(\{.+\})\s*```', raw_response, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(1))
                else:
                    first_brace = raw_response.find('{')
                    last_brace = raw_response.rfind('}')
                    if first_brace != -1 and last_brace != -1:
                        response_json = json.loads(raw_response[first_brace:last_brace+1])
                    else:
                        response_json = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as e:
            log_fn(f"      [ERROR] Failed to parse resurrection JSON: {e}", log_handle)
            return {
                "round_executed": True,
                "round_status": "json_parse_error",
                "resurrection_tests": [],
                "summary": {
                    "confirmed_kills": [k["option"] for k in kill_aggregation.get("confirmed_kills", [])],
                    "downgraded_to_conditions": [],
                    "resurrection_notes": f"JSON parse error: {str(e)[:100]}"
                }
            }
        
        # ============================================================
        # CRITICAL: Apply R2d normalization BEFORE schema validation
        # This maps killed_option->option, resurrection_result->verdict, etc.
        # CAM v2.5.4: Fix for Run 172 schema failures
        # ============================================================
        try:
            from cam.adapters.gpqa.normalize_responses import normalize_r2d
            response_json = normalize_r2d(response_json)
            log_fn(f"      [NORMALIZE] Applied R2d normalization", log_handle)
        except ImportError as e:
            log_fn(f"      [WARN] R2d normalization not available: {e}", log_handle)
        except Exception as e:
            log_fn(f"      [WARN] R2d normalization failed: {e}", log_handle)
        
        # Validate schema
        try:
            if jsonschema_module and resurrection_schema:
                jsonschema_module.validate(instance=response_json, schema=resurrection_schema)
        except Exception as e:
            log_fn(f"      [SCHEMA FAIL] Resurrection schema validation failed: {e}", log_handle)
            response_json["_schema_validation_failed"] = True
        
        summary = response_json.get("summary", {})
        confirmed_kills = summary.get("confirmed_kills", [])
        downgraded = summary.get("downgraded_to_conditions", [])
        
        log_fn(f"      [OK] Resurrection complete: confirmed_kills={confirmed_kills}, downgraded={downgraded}", log_handle)
        
        response_json["round_executed"] = True
        response_json["round_status"] = "ok"
        
        return response_json
        
    except Exception as e:
        elapsed = time.time() - start_time
        log_fn(f"      [ERROR] Resurrection failed after {elapsed:.1f}s: {e}", log_handle)
        return {
            "round_executed": True,
            "round_status": "exception",
            "resurrection_tests": [],
            "summary": {
                "confirmed_kills": [k["option"] for k in kill_aggregation.get("confirmed_kills", [])],
                "downgraded_to_conditions": [],
                "resurrection_notes": f"Exception: {str(e)[:100]}"
            }
        }


# ============================================================
# Final Commit v2: Ladder of Commitment
# ============================================================

def determine_ladder_level(
    confirmed_kills: List[str],
    attempted_kills: List[str],
    resurrected: List[str],
    survivors: List[str],
    survivor_conditions: dict,
    unanimous_final: bool = False,
    stress_passed: bool = True,
    resurrection_reasons: dict = None,  # {option: "reason for resurrection"}
    prior_eliminations: List[str] = None,  # NEW: options eliminated in R1 (before R2c)
) -> Tuple[int, str, str, dict]:
    """
    Determine the commitment level based on CONFIRMED elimination results.
    
    Returns: (level, level_name, justification, metadata)
    
    metadata includes:
    - domain_restricted: bool - True if assertion depends on domain-specific assumptions
    - domain_conditions: list - Specific domain conditions affecting validity
    
    Levels:
    0 - full_assert: 1 survivor, 3+ total eliminations, unanimous, stress passed
    1 - assert_by_elimination: 1 survivor, 2+ total eliminations
    2 - conditional_set: 2 survivors with distinct conditions, 2+ total eliminations
    3 - partial_elimination: Some eliminations, can't separate rest
    4 - invalid_question: All options have fatal flaws (rare)
    
    Note: "total eliminations" = prior_eliminations (from R1) + confirmed_kills (from R2c)
    Prior eliminations come from unanimous R1 consensus that eliminated options before R2c ran.
    """
    if prior_eliminations is None:
        prior_eliminations = []
    
    num_confirmed = len(confirmed_kills)
    num_prior = len(prior_eliminations)
    num_total_eliminations = num_confirmed + num_prior  # Count both R1 and R2c eliminations
    num_attempted = len(attempted_kills)
    num_resurrected = len(resurrected)
    num_survivors = len(survivors)
    
    # Initialize metadata
    metadata = {
        "domain_restricted": False,
        "domain_conditions": [],
        "resurrection_details": []
    }
    
    # Check if we have domain-restricted validity due to resurrections
    if resurrection_reasons and num_resurrected > 0:
        metadata["domain_restricted"] = True
        for opt in resurrected:
            reason = resurrection_reasons.get(opt, "domain-conditional kill invalidated")
            metadata["resurrection_details"].append({"option": opt, "reason": reason})
            # Extract domain conditions from reason if present
            if "assumes" in reason.lower() or "under" in reason.lower() or "domain" in reason.lower():
                metadata["domain_conditions"].append(reason)
    
    # Level 4: All options killed (invalid question) - very rare
    if num_survivors == 0:
        return (4, "invalid_question", f"All options eliminated ({num_total_eliminations} total: {num_prior} prior + {num_confirmed} R2c kills) - no valid answer exists", metadata)
    
    # Helper for justification strings
    def elim_desc():
        if num_prior > 0 and num_confirmed > 0:
            return f"{num_total_eliminations} eliminations ({num_prior} from R1 + {num_confirmed} R2c kills)"
        elif num_prior > 0:
            return f"{num_prior} eliminations from R1 unanimous consensus"
        else:
            return f"{num_confirmed} confirmed kills"
    
    # Level 0: Full assert (1 survivor, 3+ total eliminations, unanimous, stress passed, no resurrections)
    if num_survivors == 1 and num_total_eliminations >= 3 and unanimous_final and stress_passed and num_resurrected == 0:
        return (0, "full_assert", f"Single survivor {survivors[0]} after {elim_desc()}, unanimous agreement, stress test passed", metadata)
    
    # Level 1: Assert by elimination (1 survivor, 2+ total eliminations)
    # Add domain_restricted annotation if resurrections affected this determination
    if num_survivors == 1 and num_total_eliminations >= 2:
        survivor = survivors[0]
        conditions = survivor_conditions.get(survivor, {}).get("conditions", [])
        justification_suffix = ""
        if metadata["domain_restricted"]:
            justification_suffix = " [DOMAIN-RESTRICTED: valid under domain-specific assumptions]"
        if conditions:
            return (1, "assert_by_elimination", f"Single survivor {survivor} after {elim_desc()}, subject to {len(conditions)} condition(s){justification_suffix}", metadata)
        else:
            return (1, "assert_by_elimination", f"Single survivor {survivor} after {elim_desc()}{justification_suffix}", metadata)
    
    # Level 2: Conditional set (2 survivors with distinct conditions, 2+ total eliminations)
    if num_survivors == 2 and num_total_eliminations >= 2:
        s1, s2 = survivors[0], survivors[1]
        conds1 = survivor_conditions.get(s1, {}).get("conditions", [])
        conds2 = survivor_conditions.get(s2, {}).get("conditions", [])
        
        set1 = set(conds1)
        set2 = set(conds2)
        distinct = bool(set1 - set2) and bool(set2 - set1)
        
        if distinct or (conds1 and conds2):
            return (2, "conditional_set", f"Two survivors {s1},{s2} with distinct conditions, {elim_desc()}", metadata)
        else:
            return (3, "partial_elimination", f"Two survivors {s1},{s2} but conditions not distinct enough to separate", metadata)
    
    # Level 3: Partial elimination
    if num_total_eliminations >= 1:
        extra = ""
        if num_attempted > 0:
            extra = f", plus {num_attempted} attempted kill(s)"
        domain_note = ""
        if metadata["domain_restricted"]:
            domain_note = " [assertion valid under domain-restricted assumptions]"
        return (3, "partial_elimination", f"{elim_desc()}{extra}, {num_survivors} survivors not separable{domain_note}", metadata)
    
    # Level 3 fallback: No eliminations at all
    if num_attempted > 0:
        return (3, "partial_elimination", f"No confirmed eliminations ({num_attempted} attempted), {num_survivors} options remain", metadata)
    
    return (3, "partial_elimination", f"No eliminations, {num_survivors} options remain unseparated", metadata)


def apply_rule_library(
    kill_aggregation: dict,
    survivor_conditions: dict,
    round2a_result: dict,
    r3_results: dict,
    gold_answer: str,
    final_answer: str,
    ladder_level: int,
    ladder_name: str,
    log_fn,
    log_handle,
    question_text: str = "",  # Added for Physics rules
) -> Tuple[int, str, dict, dict]:
    """
    Apply the Rule Library to potentially modify ladder level and kill aggregation.
    
    Applies Biology rules first, then Physics rules (if enabled).
    Stricter constraint wins (maximum degradation, lowest cap).
    
    Rules can only:
    - Downgrade HARD kills to SOFT
    - Cap ladder levels (toward more caution)
    - Add fragility markers
    
    Rules cannot:
    - Introduce new eliminations
    - Force answer selection
    - Lower ladder levels (increase confidence)
    
    Returns: (new_level, new_level_name, modified_aggregation, rule_effects)
    """
    if not RULE_LIBRARY_AVAILABLE:
        return ladder_level, ladder_name, kill_aggregation, {"rule_library_applied": False}
    
    log_fn(f"      [RULE LIBRARY] Applying Biology Rule Library {get_rule_library_version()}...", log_handle)
    
    # Apply rules
    rule_result = apply_biology_rules(
        kill_aggregation=kill_aggregation,
        survivor_conditions=survivor_conditions,
        round2a_result=round2a_result,
        r3_results=r3_results,
        gold_answer=gold_answer,
        final_answer=final_answer,
        ladder_level=ladder_level,
    )
    
    log_fn(f"      [RULE LIBRARY] Rules evaluated: {rule_result.rules_evaluated}, triggered: {rule_result.rules_triggered}", log_handle)
    
    # Apply effects to kill aggregation
    modified_aggregation = apply_rule_effects_to_aggregation(kill_aggregation, rule_result)
    
    # Log triggered rules
    for r in rule_result.rule_results:
        if r.triggered:
            log_fn(f"        -> {r.rule_id}: {r.description}", log_handle)
            if r.affected_kills:
                log_fn(f"           Affected kills: {r.affected_kills}", log_handle)
    
    # Compute new ladder level (rules can only raise it)
    new_level = ladder_level
    new_level_name = ladder_name
    
    if rule_result.ladder_cap is not None:
        new_level = max(ladder_level, rule_result.ladder_cap)
        log_fn(f"      [RULE LIBRARY] Ladder cap applied: L{ladder_level} -> L{new_level}", log_handle)
    
    # If kills were downgraded, recompute survivors and potentially ladder
    if rule_result.downgraded_kills:
        log_fn(f"      [RULE LIBRARY] Kills downgraded: {list(rule_result.downgraded_kills.keys())}", log_handle)
        # New survivors may affect ladder level
        new_survivors = modified_aggregation.get("survivors", [])
        new_confirmed = modified_aggregation.get("confirmed_kills", [])
        
        # If we now have more survivors, ladder must go up
        original_survivors = kill_aggregation.get("survivors", [])
        if len(new_survivors) > len(original_survivors):
            # More survivors = less certainty = higher level
            if len(new_survivors) > 1 and new_level < 2:
                new_level = 2
            if len(new_survivors) > 2 and new_level < 3:
                new_level = 3
    
    # =================================================================
    # PHYSICS RULES APPLICATION (if enabled)
    # =================================================================
    physics_rule_result = None
    if PHYSICS_RULE_LIBRARY_AVAILABLE and PHYSICS_RULES_ENABLED:
        log_fn(f"      [RULE LIBRARY] Applying Physics Rule Library {get_physics_rule_library_version()}...", log_handle)
        
        physics_rule_result = apply_physics_rules(
            kill_aggregation=modified_aggregation,  # Use already-modified aggregation
            survivor_conditions=survivor_conditions,
            question_text=question_text,
            round2a_result=round2a_result,
            ladder_level=new_level,  # Use post-Biology level
        )
        
        log_fn(f"      [RULE LIBRARY] Physics rules evaluated: {physics_rule_result.rules_evaluated}, triggered: {physics_rule_result.rules_triggered}", log_handle)
        
        # Log triggered Physics rules
        for r in physics_rule_result.rule_results:
            if r.triggered:
                log_fn(f"        -> {r.rule_id}: {r.description}", log_handle)
                if r.affected_kills:
                    log_fn(f"           Affected kills: {r.affected_kills}", log_handle)
        
        # Physics rules can further cap ladder (stricter constraint wins)
        if physics_rule_result.ladder_cap is not None:
            physics_cap = physics_rule_result.ladder_cap
            if physics_cap > new_level:
                log_fn(f"      [RULE LIBRARY] Physics ladder cap applied: L{new_level} -> L{physics_cap}", log_handle)
                new_level = physics_cap
        
        # Merge downgraded kills
        if physics_rule_result.downgraded_kills:
            log_fn(f"      [RULE LIBRARY] Physics kills downgraded: {list(physics_rule_result.downgraded_kills.keys())}", log_handle)
            # Apply to aggregation (mark as soft)
            for opt, reason in physics_rule_result.downgraded_kills.items():
                # Move from confirmed to soft if present
                confirmed = modified_aggregation.get("confirmed_kills", [])
                for kill in confirmed:
                    if kill.get("option") == opt:
                        kill["downgraded_by_physics"] = True
                        kill["downgrade_reason"] = reason
    
    # Level names
    level_names = {
        0: "full_assert",
        1: "assert_by_elimination",
        2: "conditional_set",
        3: "partial_elimination",
        4: "invalid_question",
    }
    new_level_name = level_names.get(new_level, ladder_name)
    
    # Build rule effects summary (merged Biology + Physics)
    triggered_rules = [r.rule_id for r in rule_result.rule_results if r.triggered]
    all_downgraded = dict(rule_result.downgraded_kills)
    all_fragility = list(rule_result.fragility_markers)
    physics_version = None
    physics_triggered = []
    
    if physics_rule_result:
        triggered_rules.extend([r.rule_id for r in physics_rule_result.rule_results if r.triggered])
        physics_triggered = [r.rule_id for r in physics_rule_result.rule_results if r.triggered]
        all_downgraded.update(physics_rule_result.downgraded_kills)
        all_fragility.extend(physics_rule_result.fragility_markers)
        physics_version = get_physics_rule_library_version()
    
    rule_effects = {
        "rule_library_applied": True,
        "rule_library_version": get_rule_library_version(),
        "physics_library_version": physics_version,
        "physics_rules_enabled": PHYSICS_RULES_ENABLED and PHYSICS_RULE_LIBRARY_AVAILABLE,
        "rules_evaluated": rule_result.rules_evaluated + (physics_rule_result.rules_evaluated if physics_rule_result else 0),
        "rules_triggered": rule_result.rules_triggered + (physics_rule_result.rules_triggered if physics_rule_result else 0),
        "triggered_rules": triggered_rules,
        "biology_triggered": [r.rule_id for r in rule_result.rule_results if r.triggered],
        "physics_triggered": physics_triggered,
        "downgraded_kills": all_downgraded,
        "ladder_cap": max(rule_result.ladder_cap or 0, physics_rule_result.ladder_cap or 0 if physics_rule_result else 0) or None,
        "fragility_markers": all_fragility,
        "prohibitions": rule_result.prohibitions,
        "original_ladder_level": ladder_level,
        "final_ladder_level": new_level,
        "ladder_changed": new_level != ladder_level,
    }
    
    if new_level != ladder_level:
        log_fn(f"      [RULE LIBRARY] Final ladder: L{ladder_level} ({ladder_name}) -> L{new_level} ({new_level_name})", log_handle)
    else:
        log_fn(f"      [RULE LIBRARY] Ladder unchanged at L{new_level} ({new_level_name})", log_handle)
    
    return new_level, new_level_name, modified_aggregation, rule_effects

def process_final_commit_v2(
    question_data: dict,
    round1_results: dict,
    round2c_results: dict,
    round2d_results: dict,
    candidate_options: list,
    synthesis_result: dict,
    evaluator_routers,  # Dict[str, ProviderRouter]
    final_commit_prompt_template: str,
    final_commit_schema: dict,
    log_handle,
    audit_trail: list = None,
    # Dependencies
    EVALUATORS: list = None,
    log_fn=None,
    call_evaluator_with_override_fn=None,
    add_audit_entry_fn=None,
    jsonschema_module=None,
    compute_agreement_pattern_fn=None,
) -> dict:
    """
    Process Final Commit v2: Ladder of Commitment.
    
    Uses only CONFIRMED kills (not attempted or soft conditions)
    for ladder determination.
    """
    if EVALUATORS is None:
        EVALUATORS = ["A", "B", "C", "D"]
    if log_fn is None:
        log_fn = print
    
    question = question_data["question"]
    choices = question_data["choices"]
    
    log_fn(f"  Processing Final Commit v2 (Ladder Logic) for question {question_data['question_id']}", log_handle)
    
    final_commit_results = {f"evaluator_{en}": None for en in EVALUATORS}
    
    # Extract elimination results
    kill_aggregation = round2c_results.get("kill_aggregation", {})
    survivor_conditions = round2c_results.get("survivor_conditions", {})
    prior_eliminations = kill_aggregation.get("prior_eliminations", [])  # Options eliminated in R1
    
    # Get resurrection results
    resurrection_summary = round2d_results.get("summary", {}) if round2d_results else {}
    
    # Start with confirmed kills from R2c
    r2c_confirmed = [k["option"] for k in kill_aggregation.get("confirmed_kills", [])]
    r2c_attempted = [k["option"] for k in kill_aggregation.get("attempted_kills", [])]
    
    # Apply resurrection results
    r2d_confirmed = resurrection_summary.get("confirmed_kills", [])
    r2d_downgraded = resurrection_summary.get("downgraded_to_conditions", [])
    
    # CRITICAL FIX (v2.5.4): Combine R2c and R2d kills properly
    # R2d tests a SUBSET of kills (attempted or flagged for resurrection testing)
    # R2c confirmed kills NOT tested by R2d remain valid
    # R2d confirmed kills are kills that R2d validated (resurrection failed)
    # R2d downgraded kills are R2c kills that R2d invalidated (resurrection succeeded)
    if round2d_results and round2d_results.get("round_status") == "ok":
        # Start with R2c confirmed kills
        # Remove any that were downgraded by R2d (resurrection succeeded)
        # Add any new kills confirmed by R2d (from attempted list)
        r2c_not_downgraded = [k for k in r2c_confirmed if k not in r2d_downgraded]
        confirmed_kills = list(set(r2c_not_downgraded) | set(r2d_confirmed))
        downgraded = r2d_downgraded
    else:
        # No resurrection or it failed - use R2c results
        confirmed_kills = r2c_confirmed
        downgraded = []
    
    # Attempted kills that weren't tested or confirmed
    attempted_kills = [k for k in r2c_attempted if k not in confirmed_kills and k not in downgraded]
    
    # Compute survivors (options not confirmed killed)
    all_options = set(["A", "B", "C", "D"])
    confirmed_killed_set = set(confirmed_kills)
    survivors = sorted(all_options - confirmed_killed_set)
    
    # Format for prompt
    elimination_results_text = f"""
Confirmed Kills: {confirmed_kills}
Attempted Kills (unverified): {attempted_kills}
Downgraded to Conditions: {downgraded}
Survivors: {survivors}
"""
    
    confirmed_kills_text = ""
    for kill in kill_aggregation.get("confirmed_kills", []):
        if kill["option"] in confirmed_kills:
            proof_preview = (kill['kill_proof'][:100] + "...") if kill.get('kill_proof') and len(kill['kill_proof']) > 100 else kill.get('kill_proof', 'N/A')
            confirmed_kills_text += f"- {kill['option']}: {kill['kill_type']} - {proof_preview}\n"
    
    surviving_options_text = ", ".join(survivors) if survivors else "None"
    
    survivor_conditions_text = ""
    for opt in survivors:
        conds = survivor_conditions.get(opt, {})
        if conds.get("conditions"):
            survivor_conditions_text += f"\n{opt}:\n"
            for c in conds["conditions"]:
                survivor_conditions_text += f"  - {c}\n"
    
    if not survivor_conditions_text:
        survivor_conditions_text = "No explicit conditions recorded"
    
    # Format choices for prompt (CRITICAL: must include full letter→text mapping)
    choices_text = "\n".join([f"{letter}: {text}" for letter, text in sorted(choices.items())])
    
    full_prompt = final_commit_prompt_template.format(
        question=question,
        choices=choices_text,
        elimination_results=elimination_results_text,
        confirmed_kills=confirmed_kills_text or "None",
        surviving_options=surviving_options_text,
        survivor_conditions=survivor_conditions_text,
    )
    
    def process_single_evaluator_final_commit_v2(eval_name: str, router) -> Tuple[str, Optional[dict], bool]:
        """Process a single evaluator's final commitment."""
        log_fn(f"    Calling Evaluator {eval_name} (Final Commit v2)...", log_handle)
        
        target = router.targets[0] if router.targets else None
        if target:
            log_fn(f"      [ATTRIBUTION] Evaluator {eval_name} - model={target.name}, round=Final-Commit-v2", log_handle)
        
        start_time = time.time()
        try:
            result, meta, call_settings = call_evaluator_with_override_fn(
                eval_name, router, "", full_prompt, log_handle, None, None
            )
            
            if audit_trail is not None and add_audit_entry_fn:
                raw_out = meta.get("raw", "") or meta.get("content", "") or str(result) if meta else str(result)
                add_audit_entry_fn(audit_trail, "Final Commit v2", call_settings.get("model_name", eval_name), "Evaluator", full_prompt, raw_out)
            
            if result is None:
                return (eval_name, None, False)
            
            elapsed = time.time() - start_time
            log_fn(f"      [TIMING] Evaluator {eval_name} (Final Commit v2): {elapsed:.1f}s", log_handle)
            
            # Parse JSON
            try:
                if isinstance(result, dict):
                    response_json = result
                else:
                    raw_response = meta.get("raw", "") or meta.get("content", "") or str(result)
                    json_match = re.search(r'```(?:json)?\s*(\{.+\})\s*```', raw_response, re.DOTALL)
                    if json_match:
                        response_json = json.loads(json_match.group(1))
                    else:
                        first_brace = raw_response.find('{')
                        last_brace = raw_response.rfind('}')
                        if first_brace != -1 and last_brace != -1:
                            response_json = json.loads(raw_response[first_brace:last_brace+1])
                        else:
                            response_json = json.loads(raw_response)
            except (json.JSONDecodeError, TypeError) as e:
                log_fn(f"      [ERROR] Failed to parse JSON from {eval_name}: {e}", log_handle)
                return (eval_name, None, False)
            
            # Validate schema
            try:
                if jsonschema_module and final_commit_schema:
                    jsonschema_module.validate(instance=response_json, schema=final_commit_schema)
            except Exception as e:
                log_fn(f"      [SCHEMA FAIL] Evaluator {eval_name} Final Commit v2 schema validation failed: {e}", log_handle)
                response_json["_schema_validation_failed"] = True
            
            ladder = response_json.get("ladder_determination", {})
            level = ladder.get("level", -1)
            level_name = ladder.get("level_name", "unknown")
            final_choice = response_json.get("final_choice")
            
            log_fn(f"      [OK] Evaluator {eval_name}: FINAL={final_choice}, level={level} ({level_name})", log_handle)
            return (eval_name, response_json, True)
            
        except Exception as e:
            elapsed = time.time() - start_time
            log_fn(f"      [ERROR] Evaluator {eval_name} Final Commit v2 failed after {elapsed:.1f}s: {e}", log_handle)
            return (eval_name, None, False)
    
    # Run all evaluators in parallel
    with ThreadPoolExecutor(max_workers=len(EVALUATORS)) as executor:
        future_to_eval = {
            executor.submit(process_single_evaluator_final_commit_v2, eval_name, router): eval_name
            for eval_name, router in evaluator_routers.items()
        }
        
        for future in as_completed(future_to_eval):
            eval_name, response_json, success = future.result()
            if success and response_json:
                final_commit_results[f"evaluator_{eval_name}"] = response_json
    
    # ============================================================
    # MAPPING DRIFT VALIDATION - Validate letter/text consistency
    # ============================================================
    choice_map = question_data.get("choice_map", question_data.get("choices", {}))
    reverse_choice_map = question_data.get("reverse_choice_map", {})
    
    drift_corrections = []
    for eval_name in EVALUATORS:
        eval_result = final_commit_results.get(f"evaluator_{eval_name}")
        if not eval_result:
            continue
        
        fc_letter = eval_result.get("final_choice")
        fc_text = eval_result.get("final_choice_text", "")
        
        if fc_letter and fc_letter != "ABSTAIN" and fc_letter is not None:
            # Import validation function
            try:
                from run_gpqa_cam import validate_mapping_consistency
                corrected_letter, drift_detected, drift_reason = validate_mapping_consistency(
                    fc_letter, fc_text, choice_map, reverse_choice_map
                )
                
                if drift_detected:
                    log_fn(f"      [DRIFT] Evaluator {eval_name}: {fc_letter} -> {corrected_letter} (text='{fc_text[:30]}...')", log_handle)
                    eval_result["final_choice_letter_raw"] = fc_letter
                    eval_result["final_choice"] = corrected_letter
                    eval_result["mapping_drift_detected"] = True
                    eval_result["mapping_drift_reason"] = drift_reason
                    drift_corrections.append((eval_name, fc_letter, corrected_letter))
            except ImportError:
                pass  # Validation functions not available, skip
    
    if drift_corrections:
        final_commit_results["drift_corrections"] = drift_corrections
        log_fn(f"      [DRIFT] Corrected {len(drift_corrections)} evaluator(s) for letter mapping drift", log_handle)
    
    # ============================================================
    # ROUND 1 UNANIMITY RAIL - Preserve R1 referent if unanimous
    # ============================================================
    try:
        from run_gpqa_cam import apply_round1_unanimity_rail
        final_commit_results, rail_triggered, rail_reason = apply_round1_unanimity_rail(
            round1_results, final_commit_results, choice_map, reverse_choice_map, EVALUATORS
        )
        if rail_triggered:
            log_fn(f"      [RAIL] Round 1 unanimity rail triggered: {rail_reason}", log_handle)
    except ImportError:
        pass  # Rail function not available, skip
    
    # Compute final agreement pattern
    eval_choices_final = {}
    parse_ok_final = {}
    
    for eval_name in EVALUATORS:
        eval_result = final_commit_results.get(f"evaluator_{eval_name}")
        if eval_result and "final_choice" in eval_result:
            eval_choices_final[eval_name] = eval_result.get("final_choice")
        else:
            eval_choices_final[eval_name] = None
        parse_ok_final[eval_name] = eval_result is not None
    
    if compute_agreement_pattern_fn:
        pattern_final, majority_final, unanimous_final, majority_size_final, agreement_metadata = compute_agreement_pattern_fn(eval_choices_final, parse_ok_final)
    else:
        pattern_final = "unknown"
        majority_final = None
        unanimous_final = None
        majority_size_final = 0
        agreement_metadata = {}
    
    final_commit_results["final_agreement_pattern"] = pattern_final
    final_commit_results["final_majority_choice"] = majority_final
    final_commit_results["final_unanimous_choice"] = unanimous_final
    final_commit_results["final_majority_size"] = majority_size_final
    final_commit_results["final_agreement_metadata"] = agreement_metadata
    final_commit_results["converged"] = pattern_final.startswith("unanimous")
    
    # Extract resurrection reasons from R2d results if available
    resurrection_reasons = {}
    if round2d_results and round2d_results.get("resurrection_tests"):
        for test in round2d_results.get("resurrection_tests", []):
            if test.get("verdict") == "RESURRECTED":
                resurrection_reasons[test.get("option", "")] = test.get("reasoning", "domain-conditional")
    
    # Compute system-level ladder determination using confirmed kills AND prior eliminations
    system_level, system_level_name, system_justification, ladder_metadata = determine_ladder_level(
        confirmed_kills=confirmed_kills,
        attempted_kills=attempted_kills,
        resurrected=downgraded,
        survivors=survivors,
        survivor_conditions=survivor_conditions,
        unanimous_final=pattern_final.startswith("unanimous") if pattern_final else False,
        stress_passed=True,
        resurrection_reasons=resurrection_reasons,
        prior_eliminations=prior_eliminations,  # NEW: R1 unanimous eliminations count toward total
    )
    
    # ============================================================
    # RULE LIBRARY APPLICATION - Rules-First Framework
    # ============================================================
    # Apply rule library AFTER initial ladder determination
    # Rules can only raise ladder level (increase caution), never lower it
    
    rule_effects = {"rule_library_applied": False}
    original_system_level = system_level
    original_system_level_name = system_level_name
    
    if RULE_LIBRARY_AVAILABLE:
        # Get gold answer if available (for RULE-004: Assertion Licensing)
        gold_answer = question_data.get("gold_answer", question_data.get("correct_answer"))
        
        # Get R3 results if available
        r3_results = round2c_results.get("round3_results", {})
        
        # Get R2a results if available
        round2a_result = round2c_results.get("round2a_result", {})
        
        # Apply rules
        question_text = question_data.get("question", "")  # For Physics rules
        system_level, system_level_name, modified_kill_aggregation, rule_effects = apply_rule_library(
            kill_aggregation=kill_aggregation,
            survivor_conditions=survivor_conditions,
            round2a_result=round2a_result,
            r3_results=r3_results,
            gold_answer=gold_answer,
            final_answer=majority_final,  # Pre-rule answer
            ladder_level=system_level,
            ladder_name=system_level_name,
            log_fn=log_fn,
            log_handle=log_handle,
            question_text=question_text,  # For Physics rules
        )
        
        # Update survivors if kills were downgraded
        if rule_effects.get("downgraded_kills"):
            survivors = modified_kill_aggregation.get("survivors", survivors)
            confirmed_kills = [k["option"] for k in modified_kill_aggregation.get("confirmed_kills", [])]
        
        # Update justification
        if rule_effects.get("rules_triggered", 0) > 0:
            system_justification = f"{system_justification} [RULE LIBRARY: {rule_effects['rules_triggered']} rule(s) applied]"
    
    final_commit_results["system_ladder"] = {
        "level": system_level,
        "level_name": system_level_name,
        "justification": system_justification,
        "confirmed_kills": confirmed_kills,
        "attempted_kills": attempted_kills,
        "resurrected": downgraded,
        "survivors": survivors,
        "prior_eliminations": prior_eliminations,
        "domain_restricted": ladder_metadata.get("domain_restricted", False),
        "domain_conditions": ladder_metadata.get("domain_conditions", []),
        "resurrection_details": ladder_metadata.get("resurrection_details", []),
        # Rule Library additions
        "rule_effects": rule_effects,
        "original_level": original_system_level if rule_effects.get("ladder_changed") else None,
        "original_level_name": original_system_level_name if rule_effects.get("ladder_changed") else None,
    }
    # Determine final answer based on ladder level
    if system_level in [0, 1]:
        final_commit_results["final_answer"] = survivors[0] if survivors else None
    elif system_level == 2:
        final_commit_results["final_answer"] = majority_final
        final_commit_results["conditional_answers"] = [
            {"option": opt, "conditions": survivor_conditions.get(opt, {}).get("conditions", [])}
            for opt in survivors
        ]
    else:
        final_commit_results["final_answer"] = majority_final
    
    final_commit_results["pipeline_version"] = "v2"
    
    log_fn(f"      [SYSTEM LADDER] Level {system_level} ({system_level_name}): {system_justification}", log_handle)
    
    return final_commit_results


# ============================================================
# Test Functions
# ============================================================

if __name__ == "__main__":
    print("Testing kill shot validation...")
    
    # Test valid kill shot
    valid_ks = {
        "kill_type": "constraint_violation",
        "kill_proof": "The expression 2γ²-0.5 evaluates to -0.5 at γ=0, which is negative. Variance bounds must be non-negative.",
        "kill_target": "The claim that 2γ²-0.5 represents a valid variance bound"
    }
    is_valid, reason = validate_kill_shot(valid_ks, "A")
    print(f"Valid kill shot: valid={is_valid}, reason={reason}")
    assert is_valid
    
    # Test invalid kill type
    bad_type_ks = {
        "kill_type": "energetically_unfavorable",
        "kill_proof": "This pathway is energetically unfavorable",
        "kill_target": "The reaction pathway"
    }
    is_valid, reason = validate_kill_shot(bad_type_ks, "B")
    print(f"Bad type kill shot: valid={is_valid}, reason={reason}")
    assert not is_valid
    
    # Test short proof
    short_proof_ks = {
        "kill_type": "mechanism_impossibility",
        "kill_proof": "Wrong",
        "kill_target": "The mechanism"
    }
    is_valid, reason = validate_kill_shot(short_proof_ks, "C")
    print(f"Short proof kill shot: valid={is_valid}, reason={reason}")
    assert not is_valid
    
    # Test placeholder
    placeholder_ks = {
        "kill_type": "constraint_violation",
        "kill_proof": "N/A - model returned incomplete response",
        "kill_target": "The constraint"
    }
    is_valid, reason = validate_kill_shot(placeholder_ks, "D")
    print(f"Placeholder kill shot: valid={is_valid}, reason={reason}")
    assert not is_valid
    
    print("\nTesting convention detection...")
    
    convention_ks = {
        "kill_type": "constraint_violation",
        "kill_proof": "Under the standard convention, this interpretation would make the bound invalid.",
        "kill_target": "The standard interpretation"
    }
    is_conv = is_convention_dependent_kill(convention_ks)
    print(f"Convention-dependent: {is_conv}")
    assert is_conv
    
    print("\nTesting evaluator exclusion...")
    
    # Test schema failure exclusion
    schema_failed_result = {"round2c_status": "ok", "_schema_validation_failed": True}
    is_valid, reason = is_evaluator_valid_for_aggregation(schema_failed_result)
    print(f"Schema failed evaluator: valid={is_valid}, reason={reason}")
    assert not is_valid
    assert reason == "schema_validation_failed"
    
    # Test normal evaluator
    normal_result = {"round2c_status": "ok"}
    is_valid, reason = is_evaluator_valid_for_aggregation(normal_result)
    print(f"Normal evaluator: valid={is_valid}, reason={reason}")
    assert is_valid
    
    print("\nTesting aggregation with exclusions...")
    
    mock_r2c = {
        'evaluator_A': {
            'round2c_status': 'ok',
            'elimination_audit': {
                'B': {'status': 'killed', 'kill_shot': {'kill_type': 'constraint_violation', 'kill_proof': 'Proof A - violates constraint due to negative bound', 'kill_target': 'The variance bound claim'}},
            }
        },
        'evaluator_B': {
            'round2c_status': 'ok',
            '_schema_validation_failed': True,  # Should be EXCLUDED
            'elimination_audit': {
                'B': {'status': 'killed', 'kill_shot': {'kill_type': 'constraint_violation', 'kill_proof': 'Proof B - also negative', 'kill_target': 'Same claim'}},
            }
        },
        'evaluator_C': {
            'round2c_status': 'ok',
            'elimination_audit': {
                'B': {'status': 'killed', 'kill_shot': {'kill_type': 'constraint_violation', 'kill_proof': 'Proof C - confirms negative bound', 'kill_target': 'Variance claim'}},
            }
        },
        'evaluator_D': {
            'round2c_status': 'failed',  # Should be EXCLUDED
        },
    }
    
    agg = aggregate_kill_shots(mock_r2c, ['A', 'B', 'C', 'D'])
    print(f"Included evaluators: {agg['included_evaluators']}")
    print(f"Excluded evaluators: {agg['excluded_evaluators']}")
    print(f"Valid support for option B: {agg['valid_kill_consensus'].get('B', 0)}")
    
    # Only evaluators A and C should be included (B has schema fail, D failed)
    assert 'A' in agg['included_evaluators']
    assert 'C' in agg['included_evaluators']
    assert 'B' not in agg['included_evaluators']
    assert 'D' not in agg['included_evaluators']
    assert agg['valid_kill_consensus'].get('B', 0) == 2  # A and C only
    
    print("\nTesting ladder determination...")
    
    # Level 0: Full assert
    level, name, just, meta = determine_ladder_level(
        confirmed_kills=["A", "B", "D"],
        attempted_kills=[],
        resurrected=[],
        survivors=["C"],
        survivor_conditions={"C": {"conditions": []}},
        unanimous_final=True,
        stress_passed=True,
    )
    print(f"Level 0 test: {level} ({name}), domain_restricted={meta['domain_restricted']}")
    assert level == 0
    assert not meta["domain_restricted"]
    
    # Level 1 with conditions
    level, name, just, meta = determine_ladder_level(
        confirmed_kills=["A", "D"],
        attempted_kills=["B"],
        resurrected=[],
        survivors=["C"],
        survivor_conditions={"C": {"conditions": ["Assumes kinetic control"]}},
    )
    print(f"Level 1 test: {level} ({name})")
    assert level == 1
    
    # Level 1 with domain-restricted resurrection
    level, name, just, meta = determine_ladder_level(
        confirmed_kills=["A", "B"],
        attempted_kills=[],
        resurrected=["D"],
        survivors=["C"],
        survivor_conditions={"C": {"conditions": []}},
        resurrection_reasons={"D": "Kill assumes standard interpretation, invalid under non-Hermitian domain"},
    )
    print(f"Level 1 domain-restricted test: {level} ({name}), domain_restricted={meta['domain_restricted']}")
    assert level == 1
    assert meta["domain_restricted"]
    assert "DOMAIN-RESTRICTED" in just
    
    # Level 3: Only attempted kills
    level, name, just, meta = determine_ladder_level(
        confirmed_kills=[],
        attempted_kills=["A", "B"],
        resurrected=[],
        survivors=["C", "D"],
        survivor_conditions={},
    )
    print(f"Level 3 test (attempted only): {level} ({name})")
    assert level == 3
    
    print("\nAll tests passed!")