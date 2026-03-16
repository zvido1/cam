"""
Response Normalization Layer for CAM Pipeline

Normalizes model responses to canonical values before schema validation.
This prevents validation failures from legitimate edge-case responses.

Usage:
    from normalize_responses import (
        normalize_round1, normalize_round2c, normalize_final_commit,
        normalize_round3, normalize_auditor, normalize_grok_analyzer,
        normalize_synthesizer
    )

    # Before validation
    response = normalize_round2c(raw_response)
    is_valid, error = validate_response(response, schema)
    
    # Synthesizer - filters invalid options like 'E'
    response = normalize_synthesizer(raw_response)
    
    # Grok Analyzer - normalizes verbose divergence_axes strings
    response = normalize_grok_analyzer(raw_response)
"""

from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Canonical Value Mappings
# ============================================================

# String confidence to numeric (0-100) for Round 1
CONFIDENCE_NUMERIC_MAP = {
    "high": 85,
    "medium": 60,
    "low": 35,
    "none": 0,
    "very high": 95,
    "very low": 15,
    "uncertain": 40,
    "unknown": 50,
    # Capitalizations
    "HIGH": 85,
    "MEDIUM": 60,
    "LOW": 35,
    "NONE": 0,
    "High": 85,
    "Medium": 60,
    "Low": 35,
    "None": 0,
}

CONFIDENCE_MAP = {
    # Standard values
    "high": "high",
    "medium": "medium",
    "low": "low",
    "none": "none",
    # Edge cases
    "": "none",
    "n/a": "none",
    "na": "none",
    "null": "none",
    "undefined": "none",
    "unknown": "low",
    "uncertain": "low",
    # Capitalizations
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "NONE": "none",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "None": "none",
}

KILL_TYPE_MAP = {
    # Standard values
    "constraint_violation": "constraint_violation",
    "internal_contradiction": "internal_contradiction",
    "mechanism_impossibility": "mechanism_impossibility",
    "product_class_mismatch": "product_class_mismatch",
    # Common variations
    "contradiction": "internal_contradiction",
    "impossibility": "mechanism_impossibility",
    "constraint": "constraint_violation",
    "mismatch": "product_class_mismatch",
    # With spaces/underscores
    "constraint violation": "constraint_violation",
    "internal contradiction": "internal_contradiction",
    "mechanism impossibility": "mechanism_impossibility",
    "product class mismatch": "product_class_mismatch",
}

STATUS_MAP = {
    "killed": "killed",
    "surviving": "surviving",
    "alive": "surviving",
    "dead": "killed",
    "eliminated": "killed",
    "KILLED": "killed",
    "SURVIVING": "surviving",
}

LADDER_LEVEL_NAME_MAP = {
    "full_assert": "full_assert",
    "assert_by_elimination": "assert_by_elimination",
    "conditional_set": "conditional_set",
    "partial_elimination": "partial_elimination",
    "invalid_question": "invalid_question",
    # Variations
    "full assert": "full_assert",
    "assert by elimination": "assert_by_elimination",
    "conditional set": "conditional_set",
    "partial elimination": "partial_elimination",
    "invalid question": "invalid_question",
    "FULL_ASSERT": "full_assert",
    "fullassert": "full_assert",
    "level_0": "full_assert",
    "level_1": "assert_by_elimination",
    "level_2": "conditional_set",
    "level_3": "partial_elimination",
    "level_4": "invalid_question",
}

PROOF_TYPE_MAP = {
    "contradiction": "contradiction",
    "impossibility": "impossibility",
    "forced_implication": "forced_implication",
    "constraint_violation": "contradiction",
    "mechanism_impossibility": "impossibility",
    "internal_contradiction": "contradiction",
    # Variations
    "CONTRADICTION": "contradiction",
    "IMPOSSIBILITY": "impossibility",
}

CHOICE_MAP = {
    "A": "A", "B": "B", "C": "C", "D": "D",
    "a": "A", "b": "B", "c": "C", "d": "D",
    "(A)": "A", "(B)": "B", "(C)": "C", "(D)": "D",
    "Option A": "A", "Option B": "B", "Option C": "C", "Option D": "D",
    "option A": "A", "option B": "B", "option C": "C", "option D": "D",
    "ABSTAIN": "ABSTAIN",
    "abstain": "ABSTAIN",
    "Abstain": "ABSTAIN",
    None: None,
    "": None,
    "null": None,
    "none": None,
}

# Valid option letters for GPQA (4-option MCQ)
VALID_OPTIONS = {"A", "B", "C", "D"}

# Divergence axis mappings for Grok Analyzer
# The schema expects simple enum values, but models often return verbose descriptions
DIVERGENCE_AXIS_MAP = {
    "mechanism": "mechanism",
    "math": "math",
    "definition": "definition",
    "assumption": "assumption",
    "scope": "scope",
    "other": "other",
    "unknown": "unknown",
    # Common variations
    "mathematical": "math",
    "mathematics": "math",
    "mechanistic": "mechanism",
    "definitional": "definition",
    "assumptions": "assumption",
    "scoping": "scope",
}


# ============================================================
# Helper Functions
# ============================================================

def safe_get(d: Any, key: str, default: Any = None) -> Any:
    """Safely get a value from a dict-like object."""
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def normalize_string(value: Any, mapping: Dict[str, str], default: str) -> str:
    """Normalize a string value using a mapping."""
    if value is None:
        return default
    if isinstance(value, str):
        # Try exact match first
        if value in mapping:
            return mapping[value]
        # Try lowercase
        lower = value.lower().strip()
        if lower in mapping:
            return mapping[lower]
        # Try with underscores converted to spaces
        with_spaces = lower.replace("_", " ")
        if with_spaces in mapping:
            return mapping[with_spaces]
    # Return default if no match
    logger.debug(f"Normalizing unknown value '{value}' to default '{default}'")
    return default


def ensure_string(value: Any, default: str = "") -> str:
    """Ensure a value is a non-null string."""
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def ensure_list(value: Any) -> List:
    """Ensure a value is a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def ensure_bool(value: Any, default: bool = False) -> bool:
    """Ensure a value is a boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value)


def ensure_int(value: Any, default: int = 0, min_val: int = None, max_val: int = None) -> int:
    """Ensure a value is an integer within bounds."""
    try:
        result = int(value) if value is not None else default
    except (ValueError, TypeError):
        result = default
    
    if min_val is not None:
        result = max(result, min_val)
    if max_val is not None:
        result = min(result, max_val)
    return result


def extract_divergence_axis(value: str) -> str:
    """
    Extract a valid divergence axis from a verbose string.
    
    Grok sometimes returns strings like:
    'other: minor variations in proof examples (e.g., quasielastic peak shift)'
    
    This extracts the base axis from the prefix before any colon.
    """
    if not isinstance(value, str):
        return "unknown"
    
    # Check if it's already a valid axis
    lower = value.lower().strip()
    if lower in DIVERGENCE_AXIS_MAP:
        return DIVERGENCE_AXIS_MAP[lower]
    
    # Try to extract from prefix (before colon)
    if ":" in value:
        prefix = value.split(":")[0].strip().lower()
        if prefix in DIVERGENCE_AXIS_MAP:
            return DIVERGENCE_AXIS_MAP[prefix]
    
    # Try to find any valid axis keyword in the string
    for axis in ["mechanism", "math", "definition", "assumption", "scope"]:
        if axis in lower:
            return axis
    
    # Default to 'other' for unrecognized but non-empty strings
    return "other" if value.strip() else "unknown"


def filter_valid_options(options: List[str]) -> List[str]:
    """
    Filter a list of option letters to only include valid A-D options.
    
    GPT-5.2 Synthesizer sometimes outputs 'E' or other invalid options.
    This removes them to prevent schema validation failures.
    """
    if not options:
        return []
    
    valid = []
    for opt in options:
        if isinstance(opt, str):
            normalized = opt.upper().strip()
            if normalized in VALID_OPTIONS:
                valid.append(normalized)
            else:
                logger.warning(f"Filtering invalid option '{opt}' - not in A-D")
    
    return valid


# ============================================================
# Round 1 Normalization
# ============================================================

def normalize_round1(response: Dict) -> Dict:
    """Normalize Round 1 evaluator response."""
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # Normalize final_choice
    if "final_choice" in normalized:
        normalized["final_choice"] = normalize_string(
            normalized["final_choice"], CHOICE_MAP, None
        )
    
    # Normalize proof_attempt
    if "proof_attempt" in normalized and isinstance(normalized["proof_attempt"], dict):
        for opt, proof in normalized["proof_attempt"].items():
            if isinstance(proof, dict):
                if "type" in proof:
                    proof["type"] = normalize_string(
                        proof["type"], PROOF_TYPE_MAP, "forced_implication"
                    )
                if "text" in proof:
                    proof["text"] = ensure_string(proof["text"], "No proof provided")
    
    # Normalize confidence fields - Round 1 expects integer 0-100
    for field in ["answer_confidence", "confidence"]:
        if field in normalized:
            value = normalized[field]
            # If already an integer in valid range, keep it
            if isinstance(value, int) and 0 <= value <= 100:
                continue
            # If it's a string, convert to numeric
            if isinstance(value, str):
                lower_val = value.lower().strip()
                if lower_val in CONFIDENCE_NUMERIC_MAP:
                    normalized[field] = CONFIDENCE_NUMERIC_MAP[lower_val]
                else:
                    # Try to parse as int
                    try:
                        normalized[field] = max(0, min(100, int(value)))
                    except ValueError:
                        normalized[field] = 50  # Default to medium
            elif value is None:
                normalized[field] = 50
            else:
                # Try to convert to int
                try:
                    normalized[field] = max(0, min(100, int(value)))
                except (ValueError, TypeError):
                    normalized[field] = 50
    
    return normalized


# ============================================================
# Round 2c Normalization
# ============================================================

def normalize_kill_shot(kill_shot: Any) -> Optional[Dict]:
    """Normalize a kill shot object."""
    if kill_shot is None:
        return None
    if not isinstance(kill_shot, dict):
        return None
    
    normalized = kill_shot.copy()
    
    # Normalize kill_type
    if "kill_type" in normalized:
        normalized["kill_type"] = normalize_string(
            normalized["kill_type"], KILL_TYPE_MAP, "internal_contradiction"
        )
    
    # Ensure strings for proof fields (allow empty)
    normalized["kill_proof"] = ensure_string(normalized.get("kill_proof"), "")
    normalized["kill_target"] = ensure_string(normalized.get("kill_target"), "")
    
    return normalized


def normalize_round2c(response: Dict) -> Dict:
    """Normalize Round 2c elimination audit response."""
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # Normalize elimination_audit
    if "elimination_audit" in normalized and isinstance(normalized["elimination_audit"], dict):
        for opt, audit in normalized["elimination_audit"].items():
            if isinstance(audit, dict) and not audit.get("_status_quarantined"):
                # Normalize status
                if "status" in audit:
                    audit["status"] = normalize_string(
                        audit["status"], STATUS_MAP, "surviving"
                    )
                
                # Normalize kill_shot
                if "kill_shot" in audit:
                    audit["kill_shot"] = normalize_kill_shot(audit["kill_shot"])
                
                # Ensure arrays
                audit["conditions"] = ensure_list(audit.get("conditions"))
                audit["would_be_falsified_if"] = ensure_list(audit.get("would_be_falsified_if"))
    
    # Normalize elimination_summary
    if "elimination_summary" in normalized and isinstance(normalized["elimination_summary"], dict):
        summary = normalized["elimination_summary"]
        
        # Normalize kill_confidence
        summary["kill_confidence"] = normalize_string(
            summary.get("kill_confidence"), CONFIDENCE_MAP, "none"
        )
        
        # Ensure arrays
        summary["killed_options"] = ensure_list(summary.get("killed_options"))
        summary["surviving_options"] = ensure_list(summary.get("surviving_options"))
        
        # Normalize option letters in arrays
        summary["killed_options"] = [
            normalize_string(opt, CHOICE_MAP, opt) 
            for opt in summary["killed_options"] 
            if opt
        ]
        summary["surviving_options"] = [
            normalize_string(opt, CHOICE_MAP, opt) 
            for opt in summary["surviving_options"] 
            if opt
        ]
    
    # Normalize best_current_case
    if "best_current_case" in normalized and isinstance(normalized["best_current_case"], dict):
        bcc = normalized["best_current_case"]
        if "leading_choice" in bcc:
            bcc["leading_choice"] = normalize_string(
                bcc["leading_choice"], CHOICE_MAP, None
            )
        bcc["why_leading"] = ensure_string(bcc.get("why_leading"), "")
        bcc["key_lemma"] = ensure_string(bcc.get("key_lemma"), "")
    
    # Normalize jb (justification burden)
    if "jb" in normalized:
        normalized["jb"] = ensure_int(normalized["jb"], default=5, min_val=0, max_val=10)
    
    # Ensure weakest_link is string
    normalized["weakest_link"] = ensure_string(normalized.get("weakest_link"), "")
    
    return normalized


# ============================================================
# Final Commit Normalization
# ============================================================

def normalize_final_commit(response: Dict) -> Dict:
    """Normalize Final Commit response."""
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # Normalize final_choice
    if "final_choice" in normalized:
        normalized["final_choice"] = normalize_string(
            normalized["final_choice"], CHOICE_MAP, None
        )
    
    # Normalize ladder_determination
    if "ladder_determination" in normalized and isinstance(normalized["ladder_determination"], dict):
        ladder = normalized["ladder_determination"]
        
        # Normalize level (integer 0-4)
        if "level" in ladder:
            ladder["level"] = ensure_int(ladder["level"], default=3, min_val=0, max_val=4)
        
        # Normalize level_name
        if "level_name" in ladder:
            ladder["level_name"] = normalize_string(
                ladder["level_name"], LADDER_LEVEL_NAME_MAP, "partial_elimination"
            )
        
        # Ensure justification strings (allow empty)
        ladder["justification"] = ensure_string(ladder.get("justification"), "")
        ladder["level_justification"] = ensure_string(ladder.get("level_justification"), "")
        
        # Ensure arrays for acknowledged kills/survivors
        ladder["confirmed_kills_acknowledged"] = ensure_list(
            ladder.get("confirmed_kills_acknowledged")
        )
        ladder["survivors_acknowledged"] = ensure_list(
            ladder.get("survivors_acknowledged")
        )
    
    # Ensure confidence_statement
    normalized["confidence_statement"] = ensure_string(
        normalized.get("confidence_statement"), ""
    )
    
    # Normalize epistemic_status
    if "epistemic_status" in normalized and isinstance(normalized["epistemic_status"], dict):
        es = normalized["epistemic_status"]
        es["confidence"] = ensure_string(es.get("confidence"), "uncertain")
        es["remaining_uncertainty"] = ensure_string(es.get("remaining_uncertainty"), "")
        es["would_change_if"] = ensure_string(es.get("would_change_if"), "")
    
    # Ensure arrays
    normalized["conditions_if_any"] = ensure_list(normalized.get("conditions_if_any"))
    normalized["would_change_if"] = ensure_list(normalized.get("would_change_if"))
    
    return normalized


# ============================================================
# Round 3 (Stress Test) Normalization
# ============================================================

def normalize_round3(response: Dict) -> Dict:
    """Normalize Round 3 stress test response."""
    if not isinstance(response, dict):
        return response
    
    # The schema has additionalProperties: false, so only keep allowed fields
    normalized = {}
    
    # Normalize can_break (required)
    can_break_raw = response.get("can_break")
    if can_break_raw is None:
        normalized["can_break"] = False
    elif isinstance(can_break_raw, bool):
        normalized["can_break"] = can_break_raw
    elif isinstance(can_break_raw, str):
        normalized["can_break"] = can_break_raw.lower() in ("true", "yes", "1")
    else:
        normalized["can_break"] = bool(can_break_raw)
    
    # Normalize failure_mode (required, string or null)
    failure_mode = response.get("failure_mode")
    if failure_mode is None or failure_mode == "":
        normalized["failure_mode"] = None if not normalized["can_break"] else "unspecified"
    else:
        normalized["failure_mode"] = str(failure_mode)
    
    # Normalize minimal_premise_that_fails (required, string or null)
    premise = response.get("minimal_premise_that_fails")
    if premise is None or premise == "":
        normalized["minimal_premise_that_fails"] = None if not normalized["can_break"] else "unspecified"
    else:
        normalized["minimal_premise_that_fails"] = str(premise)
    
    return normalized


# ============================================================
# Auditor Normalization
# ============================================================

def normalize_auditor(response: Dict) -> Dict:
    """Normalize Auditor response."""
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # Normalize decision
    decision_map = {
        "ACCEPT": "ACCEPT",
        "ABSTAIN": "ABSTAIN",
        "accept": "ACCEPT",
        "abstain": "ABSTAIN",
        "Accept": "ACCEPT",
        "Abstain": "ABSTAIN",
        "": "ABSTAIN",
        None: "ABSTAIN",
    }
    normalized["decision"] = normalize_string(
        normalized.get("decision"), decision_map, "ABSTAIN"
    )
    
    # Normalize reasoning_compatibility
    compat_map = {
        "compatible": "compatible",
        "incompatible": "incompatible",
        "unknown": "unknown",
        "COMPATIBLE": "compatible",
        "INCOMPATIBLE": "incompatible",
        "": "unknown",
        None: "unknown",
    }
    normalized["reasoning_compatibility"] = normalize_string(
        normalized.get("reasoning_compatibility"), compat_map, "unknown"
    )
    
    # Ensure strings
    normalized["justification"] = ensure_string(normalized.get("justification"), "")
    
    # Ensure arrays
    normalized["mutually_exclusive_assumptions"] = ensure_list(
        normalized.get("mutually_exclusive_assumptions")
    )
    
    return normalized


# ============================================================
# Grok Analyzer Normalization
# ============================================================

def normalize_grok_analyzer(response: Dict) -> Dict:
    """Normalize Grok Analyzer response."""
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # Normalize reasoning_relation
    relation_map = {
        "IDENTICAL": "IDENTICAL",
        "EQUIVALENT": "IDENTICAL",  # Common synonym
        "COMPATIBLE": "COMPATIBLE",
        "MIXED": "MIXED",
        "INCOMPATIBLE": "INCOMPATIBLE",
        "identical": "IDENTICAL",
        "equivalent": "IDENTICAL",
        "compatible": "COMPATIBLE",
        "mixed": "MIXED",
        "incompatible": "INCOMPATIBLE",
        "": "MIXED",
        None: "MIXED",
    }
    normalized["reasoning_relation"] = normalize_string(
        normalized.get("reasoning_relation"), relation_map, "MIXED"
    )
    
    # Normalize similarity_level (schema uses this, not grok_similarity)
    similarity_map = {
        "HIGH": "HIGH",
        "MEDIUM": "MEDIUM",
        "LOW": "LOW",
        "UNKNOWN": "UNKNOWN",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "unknown": "UNKNOWN",
        "": "MEDIUM",
        None: "MEDIUM",
    }
    if "similarity_level" in normalized:
        normalized["similarity_level"] = normalize_string(
            normalized["similarity_level"], similarity_map, "MEDIUM"
        )
    # Also handle legacy field name
    if "grok_similarity" in normalized:
        normalized["grok_similarity"] = normalize_string(
            normalized["grok_similarity"], similarity_map, "MEDIUM"
        )
    
    # Ensure booleans
    normalized["incompatibility_detected"] = ensure_bool(
        normalized.get("incompatibility_detected"), False
    )
    normalized["equivalence_detected"] = ensure_bool(
        normalized.get("equivalence_detected"), False
    )
    
    # CRITICAL: Normalize divergence_axes - Grok returns verbose strings
    # Schema expects: ["mechanism", "math", "definition", "assumption", "scope", "other", "unknown"]
    if "divergence_axes" in normalized:
        raw_axes = ensure_list(normalized["divergence_axes"])
        normalized["divergence_axes"] = [
            extract_divergence_axis(axis) for axis in raw_axes
        ]
        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for axis in normalized["divergence_axes"]:
            if axis not in seen:
                seen.add(axis)
                deduped.append(axis)
        normalized["divergence_axes"] = deduped
    
    # Ensure arrays
    normalized["shared_assumptions"] = ensure_list(normalized.get("shared_assumptions"))
    normalized["incompatible_assumptions"] = ensure_list(normalized.get("incompatible_assumptions"))
    normalized["equivalent_methods"] = ensure_list(normalized.get("equivalent_methods"))
    
    # Ensure shared_eliminations is a dict
    if "shared_eliminations" not in normalized or not isinstance(normalized["shared_eliminations"], dict):
        normalized["shared_eliminations"] = {}
    
    # Ensure notes is a string
    normalized["notes"] = ensure_string(normalized.get("notes"), "")
    
    return normalized


# ============================================================
# Synthesizer Normalization
# ============================================================

def normalize_synthesizer(response: Dict) -> Dict:
    """
    Normalize Synthesizer response.
    
    Key fixes:
    - Filters invalid options from candidate_options (GPT-5.2 sometimes outputs 'E')
    - Normalizes proof_ledger status values
    - Ensures required arrays exist
    """
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # CRITICAL: Filter candidate_options to only valid A-D
    # GPT-5.2 sometimes hallucinates 'E' as an option
    if "candidate_options" in normalized:
        raw_options = ensure_list(normalized["candidate_options"])
        filtered_options = filter_valid_options(raw_options)
        
        # v2.5.4 FIX: Do NOT silently default to ABCD - this hides synthesizer failures
        # If all options were invalid, flag it as an error condition
        if raw_options and not filtered_options:
            invalid_options = [opt for opt in raw_options if opt.upper().strip() not in VALID_OPTIONS]
            logger.error(f"SYNTH_INVALID_OPTIONS: All candidate_options were invalid: {invalid_options}")
            normalized["candidate_options"] = []  # Keep empty - let downstream handle
            normalized["_synth_invalid_options"] = invalid_options
            normalized["_synth_error"] = "All candidate options were invalid (e.g., 'E')"
        else:
            normalized["candidate_options"] = filtered_options
    
    # Normalize proof_ledger status values
    status_map = {
        "killed": "killed",
        "unfalsified": "unfalsified",
        "supported": "supported",
        "unknown": "unknown",
        "KILLED": "killed",
        "UNFALSIFIED": "unfalsified",
        "SUPPORTED": "supported",
        "alive": "unfalsified",
        "surviving": "unfalsified",
    }
    if "proof_ledger" in normalized and isinstance(normalized["proof_ledger"], dict):
        for opt, ledger in normalized["proof_ledger"].items():
            if isinstance(ledger, dict) and "status" in ledger:
                ledger["status"] = normalize_string(
                    ledger["status"], status_map, "unknown"
                )
                # Ensure arrays
                ledger["kill_shots_against"] = ensure_list(ledger.get("kill_shots_against"))
                ledger["unfalsified_claims"] = ensure_list(ledger.get("unfalsified_claims"))
    
    # Ensure booleans
    normalized["equivalence_detected"] = ensure_bool(
        normalized.get("equivalence_detected"), False
    )
    normalized["incompatibility_detected"] = ensure_bool(
        normalized.get("incompatibility_detected"), False
    )
    normalized["abstain"] = ensure_bool(
        normalized.get("abstain"), False
    )
    
    # Ensure strings
    normalized["synthesis_notes"] = ensure_string(normalized.get("synthesis_notes"), "")
    if normalized["abstain"]:
        normalized["abstain_justification"] = ensure_string(
            normalized.get("abstain_justification"), "No justification provided"
        )
    
    # Ensure cross_candidate_incompatibility is an array
    normalized["cross_candidate_incompatibility"] = ensure_list(
        normalized.get("cross_candidate_incompatibility")
    )
    
    return normalized


# ============================================================
# Round 2d (Resurrection) Normalization
# ============================================================

# Constants for resurrection result semantics (CRITICAL - DO NOT INVERT)
# The resurrection_result field indicates whether the RESURRECTION ATTEMPT succeeded:
#   - "failure" = Resurrection FAILED → Kill is CONFIRMED (option stays dead)
#   - "success" = Resurrection SUCCEEDED → Kill is DOWNGRADED to soft condition (option revived)
R2D_RESULT_TO_VERDICT = {
    # Standard values
    "failure": "confirmed_kill",
    "success": "downgraded_to_condition",
    # Alternative phrasings
    "confirmed": "confirmed_kill",
    "confirmed_kill": "confirmed_kill",
    "downgraded": "downgraded_to_condition",
    "downgraded_to_condition": "downgraded_to_condition",
    "resurrection_failed": "confirmed_kill",
    "resurrected": "downgraded_to_condition",
    # Unknown/fallback
    "unknown": "confirmed_kill",  # Conservative: treat unknown as confirmed kill
}


def normalize_r2d_test_item(test: Dict) -> Dict:
    """
    Normalize a single R2d resurrection test item.
    
    Maps agent output format to schema-expected format:
    - killed_option → option
    - resurrection_result → verdict (with semantic mapping)
    - result_explanation → reasoning
    - original_kill_shot.kill_type → original_kill_type
    """
    if not isinstance(test, dict):
        return test
    
    normalized = test.copy()
    
    # Map killed_option → option
    if "option" not in normalized and "killed_option" in normalized:
        normalized["option"] = normalized["killed_option"]
    
    # Normalize option to uppercase letter
    if "option" in normalized:
        normalized["option"] = normalize_string(
            normalized["option"], CHOICE_MAP, normalized.get("option")
        )
    
    # Map original_kill_shot.kill_type → original_kill_type
    if "original_kill_type" not in normalized:
        kill_shot = normalized.get("original_kill_shot")
        if isinstance(kill_shot, dict):
            normalized["original_kill_type"] = kill_shot.get("kill_type", "unknown")
        elif kill_shot:
            normalized["original_kill_type"] = str(kill_shot)[:50]
        else:
            normalized["original_kill_type"] = "unknown"
    
    # Map resurrection_result → verdict (with semantic conversion)
    if "verdict" not in normalized:
        result = normalized.get("resurrection_result", "")
        if isinstance(result, str):
            result_lower = result.lower().strip()
            # Check direct mapping first
            if result_lower in R2D_RESULT_TO_VERDICT:
                normalized["verdict"] = R2D_RESULT_TO_VERDICT[result_lower]
            # Keyword-based fallback
            elif "confirmed" in result_lower or ("kill" in result_lower and "downgrad" not in result_lower):
                normalized["verdict"] = "confirmed_kill"
            elif "downgrad" in result_lower or "resurrect" in result_lower or "condition" in result_lower or "success" in result_lower:
                normalized["verdict"] = "downgraded_to_condition"
            elif "fail" in result_lower:
                normalized["verdict"] = "confirmed_kill"  # Resurrection failed = kill confirmed
            else:
                normalized["verdict"] = "confirmed_kill"  # Conservative default
        else:
            normalized["verdict"] = "confirmed_kill"
    
    # Map result_explanation → reasoning
    if "reasoning" not in normalized or not normalized.get("reasoning"):
        if "result_explanation" in normalized:
            normalized["reasoning"] = normalized["result_explanation"]
        elif "resurrection_attempt" in normalized and isinstance(normalized["resurrection_attempt"], dict):
            # Try to extract from resurrection_attempt object
            attempt = normalized["resurrection_attempt"]
            normalized["reasoning"] = attempt.get("argument", "") or attempt.get("strategy", "")
    
    # Ensure reasoning meets minimum length requirement (20 chars)
    reasoning = normalized.get("reasoning", "")
    if len(reasoning) < 20:
        # Try to pad with available information
        extra_info = []
        if normalized.get("result_explanation"):
            extra_info.append(normalized["result_explanation"])
        if normalized.get("if_resurrected") and isinstance(normalized["if_resurrected"], dict):
            note = normalized["if_resurrected"].get("note", "")
            if note:
                extra_info.append(note)
        if extra_info:
            normalized["reasoning"] = " ".join([reasoning] + extra_info).strip()
        if len(normalized.get("reasoning", "")) < 20:
            # Final fallback: use verdict as context
            verdict = normalized.get("verdict", "unknown")
            normalized["reasoning"] = f"Resurrection test result: {verdict}. {reasoning}" if reasoning else f"Resurrection test resulted in: {verdict}"
    
    # Ensure confidence is valid enum
    if "confidence" in normalized:
        conf_map = {"high": "high", "medium": "medium", "low": "low"}
        normalized["confidence"] = normalize_string(
            normalized.get("confidence"), conf_map, "medium"
        )
    
    # Ensure convention_dependent is boolean
    if "convention_dependent" in normalized:
        normalized["convention_dependent"] = ensure_bool(
            normalized["convention_dependent"], False
        )
    
    return normalized


def normalize_r2d_tests(resurrection_tests: list) -> list:
    """
    Normalize a list of R2d resurrection test items.
    
    This is the main entry point for R2d normalization.
    Apply BEFORE schema validation and BEFORE writing to merged_results.
    
    Args:
        resurrection_tests: List of raw test items from resurrection agent
        
    Returns:
        List of normalized test items with schema-compliant field names
    """
    if not resurrection_tests:
        return []
    
    return [normalize_r2d_test_item(test) for test in resurrection_tests]


def normalize_r2d(response: Dict) -> Dict:
    """
    Normalize complete R2d resurrection response.
    
    Applies normalization to:
    - resurrection_tests array (killed_option→option, etc.)
    - summary.confirmed_kills and downgraded_to_conditions arrays
    """
    if not isinstance(response, dict):
        return response
    
    normalized = response.copy()
    
    # Normalize resurrection_tests array
    if "resurrection_tests" in normalized:
        normalized["resurrection_tests"] = normalize_r2d_tests(
            normalized.get("resurrection_tests", [])
        )
    
    # Ensure summary exists and has required fields
    if "summary" not in normalized or not isinstance(normalized.get("summary"), dict):
        normalized["summary"] = {
            "confirmed_kills": [],
            "downgraded_to_conditions": [],
            "resurrection_notes": ""
        }
    
    summary = normalized["summary"]
    
    # Ensure confirmed_kills is a list of valid options
    summary["confirmed_kills"] = filter_valid_options(
        ensure_list(summary.get("confirmed_kills"))
    )
    
    # Ensure downgraded_to_conditions is a list of valid options
    summary["downgraded_to_conditions"] = filter_valid_options(
        ensure_list(summary.get("downgraded_to_conditions"))
    )
    
    # Ensure resurrection_notes is a string
    summary["resurrection_notes"] = ensure_string(
        summary.get("resurrection_notes"), ""
    )
    
    return normalized


# ============================================================
# Master Normalization Function
# ============================================================

def normalize_response(response: Dict, response_type: str) -> Dict:
    """
    Normalize a response based on its type.
    
    Args:
        response: Raw response dict from model
        response_type: One of 'round1', 'round2c', 'final_commit', 'round3', 'auditor', 'grok', 'synthesizer'
    
    Returns:
        Normalized response dict
    """
    normalizers = {
        "round1": normalize_round1,
        "round2c": normalize_round2c,
        "round2d": normalize_r2d,
        "resurrection": normalize_r2d,  # Alias
        "final_commit": normalize_final_commit,
        "round3": normalize_round3,
        "auditor": normalize_auditor,
        "grok": normalize_grok_analyzer,
        "grok_analyzer": normalize_grok_analyzer,  # Alias
        "synthesizer": normalize_synthesizer,
    }
    
    normalizer = normalizers.get(response_type)
    if normalizer:
        return normalizer(response)
    
    logger.warning(f"Unknown response type '{response_type}', returning unchanged")
    return response
