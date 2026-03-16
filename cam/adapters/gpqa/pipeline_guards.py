#!/usr/bin/env python3
"""
CAM Pipeline Guards v1.1

Implementation of GUARD-001 through GUARD-006 from CAM_Pipeline_Guards_v1_1.docx

These are IMPLEMENTATION GUARDS, not epistemic rules.
They govern execution flow, not confidence or assertion levels.
They must never affect ladder semantics directly.

Key Principle: Agent/system failure ≠ epistemic uncertainty.
A broken component provides no epistemic signal.

Version History:
- v1.0 (2026-01-20): Initial documentation based on Physics probe runs
- v1.1 (2026-01-21): GUARD-001 clarified; GUARD-004 requires fragility propagation
- v1.2 (2026-01-25): Implemented as dedicated module
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# Module status
PIPELINE_GUARDS_VERSION = "v1.2"
PIPELINE_GUARDS_STATUS = "ENABLED"


class GuardAction(Enum):
    """Actions that guards can take"""
    EXCLUDE_FROM_AGGREGATION = "exclude_from_aggregation"
    MARK_UNAVAILABLE = "mark_unavailable"
    DISCARD_OUTPUT = "discard_output"
    FALLBACK_TO_DETERMINISTIC = "fallback_to_deterministic"
    ADD_FRAGILITY_MARKER = "add_fragility_marker"
    PRESERVE_DATA = "preserve_data"
    LOG_ERROR = "log_error"
    NO_ACTION = "no_action"


@dataclass
class GuardResult:
    """Result of applying a single guard"""
    guard_id: str
    triggered: bool
    action: GuardAction
    description: str
    affected_component: Optional[str] = None
    error_code: Optional[str] = None
    details: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PipelineGuardResults:
    """Aggregate result of all pipeline guards"""
    guards_evaluated: int
    guards_triggered: int
    guard_results: List[GuardResult]
    excluded_evaluators: List[str]
    unavailable_components: List[str]
    fragility_markers: List[str]
    fallback_applied: bool
    errors_logged: List[str]


# =============================================================================
# GUARD-001: Evaluator Schema Failure
# =============================================================================

def check_evaluator_schema_failure(
    evaluator_output: dict,
    evaluator_id: str,
    required_fields: List[str] = None
) -> GuardResult:
    """
    GUARD-001: Evaluator Schema Failure
    
    Triggered when: Evaluator returns incomplete output (missing final_choice, 
    missing proof_attempt, etc.)
    
    Implementation:
    1. Exclude from aggregation for this question only
    2. Evaluator remains available for subsequent questions
    3. Log AGENT_SCHEMA_FAIL with evaluator ID
    4. Do NOT treat as epistemic uncertainty or abstention trigger
    
    Principle: Agent failure ≠ disagreement. A broken evaluator provides no 
    epistemic signal.
    """
    if required_fields is None:
        required_fields = ["final_choice"]
    
    if not evaluator_output:
        return GuardResult(
            guard_id="GUARD-001",
            triggered=True,
            action=GuardAction.EXCLUDE_FROM_AGGREGATION,
            description="Evaluator Schema Failure: No output returned",
            affected_component=evaluator_id,
            error_code="AGENT_SCHEMA_FAIL",
            details="Evaluator returned None or empty output"
        )
    
    missing_fields = []
    for field in required_fields:
        if field not in evaluator_output or evaluator_output[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        return GuardResult(
            guard_id="GUARD-001",
            triggered=True,
            action=GuardAction.EXCLUDE_FROM_AGGREGATION,
            description=f"Evaluator Schema Failure: Missing required fields",
            affected_component=evaluator_id,
            error_code="AGENT_SCHEMA_FAIL",
            details=f"Missing fields: {', '.join(missing_fields)}"
        )
    
    # Check for schema validation failure flag
    if evaluator_output.get("_schema_validation_failed") and not evaluator_output.get("_repair_applied"):
        return GuardResult(
            guard_id="GUARD-001",
            triggered=True,
            action=GuardAction.EXCLUDE_FROM_AGGREGATION,
            description="Evaluator Schema Failure: Schema validation failed (not repaired)",
            affected_component=evaluator_id,
            error_code="AGENT_SCHEMA_FAIL",
            details="Schema validation failed and repair was not applied"
        )
    
    return GuardResult(
        guard_id="GUARD-001",
        triggered=False,
        action=GuardAction.NO_ACTION,
        description="Evaluator schema check passed",
        affected_component=evaluator_id
    )


# =============================================================================
# GUARD-002: Analyzer Schema Failure
# =============================================================================

def check_analyzer_schema_failure(
    analyzer_output: dict,
    analyzer_id: str = "grok_analyzer",
    required_fields: List[str] = None
) -> GuardResult:
    """
    GUARD-002: Analyzer Schema Failure
    
    Triggered when: Grok Analyzer (R1.5) returns missing required fields 
    (e.g., similarity_level). May cause false candidate restoration.
    
    Implementation:
    1. Mark analyzer as UNAVAILABLE
    2. Preserve R1 unanimity if it exists
    3. Do NOT restore or prune candidates based on failed analyzer output
    
    Principle: Analyzer failure ≠ epistemic conflict. Absence of analysis 
    is not evidence of disagreement.
    """
    if required_fields is None:
        required_fields = ["similarity_level", "reasoning_alignment"]
    
    if not analyzer_output:
        return GuardResult(
            guard_id="GUARD-002",
            triggered=True,
            action=GuardAction.MARK_UNAVAILABLE,
            description="Analyzer Schema Failure: No output returned",
            affected_component=analyzer_id,
            error_code="ANALYZER_UNAVAILABLE",
            details="Analyzer returned None or empty output"
        )
    
    missing_fields = []
    for field in required_fields:
        if field not in analyzer_output or analyzer_output[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        return GuardResult(
            guard_id="GUARD-002",
            triggered=True,
            action=GuardAction.MARK_UNAVAILABLE,
            description=f"Analyzer Schema Failure: Missing required fields",
            affected_component=analyzer_id,
            error_code="ANALYZER_UNAVAILABLE",
            details=f"Missing fields: {', '.join(missing_fields)}"
        )
    
    return GuardResult(
        guard_id="GUARD-002",
        triggered=False,
        action=GuardAction.NO_ACTION,
        description="Analyzer schema check passed",
        affected_component=analyzer_id
    )


# =============================================================================
# GUARD-003: Synthesizer Candidate Corruption
# =============================================================================

def check_synthesizer_candidate_corruption(
    synthesizer_output: dict,
    valid_options: Set[str] = None
) -> GuardResult:
    """
    GUARD-003: Synthesizer Candidate Corruption
    
    Triggered when: Synthesizer outputs invalid option labels (e.g., 'E' when 
    only A-D exist).
    
    Implementation:
    1. Discard synthesizer candidate list entirely
    2. Fall back to deterministic candidate set from R1
    3. Log SYNTH_INVALID_OPTION
    
    Principle: Corrupted synthesis must never affect epistemic state.
    Garbage in → fallback, not garbage through.
    """
    if valid_options is None:
        valid_options = {"A", "B", "C", "D"}
    
    if not synthesizer_output:
        return GuardResult(
            guard_id="GUARD-003",
            triggered=False,
            action=GuardAction.NO_ACTION,
            description="No synthesizer output to check",
            affected_component="synthesizer"
        )
    
    # Check candidate_options field
    candidates = synthesizer_output.get("candidate_options", [])
    if not candidates:
        candidates = synthesizer_output.get("candidates", [])
    
    invalid_options = []
    for candidate in candidates:
        opt = candidate if isinstance(candidate, str) else candidate.get("option", "")
        if opt and opt.upper() not in valid_options:
            invalid_options.append(opt)
    
    # Also check final_choice if present
    final_choice = synthesizer_output.get("final_choice", "")
    if final_choice and final_choice.upper() not in valid_options:
        invalid_options.append(f"final_choice={final_choice}")
    
    if invalid_options:
        return GuardResult(
            guard_id="GUARD-003",
            triggered=True,
            action=GuardAction.FALLBACK_TO_DETERMINISTIC,
            description="Synthesizer Candidate Corruption: Invalid option labels detected",
            affected_component="synthesizer",
            error_code="SYNTH_INVALID_OPTION",
            details=f"Invalid options: {', '.join(invalid_options)}"
        )
    
    return GuardResult(
        guard_id="GUARD-003",
        triggered=False,
        action=GuardAction.NO_ACTION,
        description="Synthesizer candidate check passed",
        affected_component="synthesizer"
    )


# =============================================================================
# GUARD-004: Letter Mapping Drift
# =============================================================================

def check_letter_mapping_drift(
    evaluator_output: dict,
    evaluator_id: str,
    question_options: Dict[str, str] = None
) -> GuardResult:
    """
    GUARD-004: Letter Mapping Drift
    
    Triggered when: Evaluator outputs letter X but text corresponds to letter Y.
    System corrects via referent anchoring.
    
    Implementation:
    1. Allow correction for answer alignment
    2. Mark LETTER_MAPPING_DRIFT in result
    3. Add fragility marker — drift is epistemically relevant even after correction
    
    Principle: Drift is a stability failure even when correctable.
    Corrected ≠ confident. The fact that correction was needed is a fragility 
    signal, not an elimination trigger.
    """
    if not evaluator_output:
        return GuardResult(
            guard_id="GUARD-004",
            triggered=False,
            action=GuardAction.NO_ACTION,
            description="No evaluator output to check for drift",
            affected_component=evaluator_id
        )
    
    # Check for drift detection flag
    drift_detected = evaluator_output.get("mapping_drift_detected", False)
    drift_corrected = evaluator_output.get("drift_corrected", False)
    original_choice = evaluator_output.get("original_choice", "")
    corrected_choice = evaluator_output.get("corrected_choice", "")
    
    if drift_detected:
        details = f"Original: {original_choice}, Corrected: {corrected_choice}" if original_choice else "Drift detected"
        return GuardResult(
            guard_id="GUARD-004",
            triggered=True,
            action=GuardAction.ADD_FRAGILITY_MARKER,
            description="Letter Mapping Drift: Evaluator output required correction",
            affected_component=evaluator_id,
            error_code="LETTER_MAPPING_DRIFT",
            details=details
        )
    
    return GuardResult(
        guard_id="GUARD-004",
        triggered=False,
        action=GuardAction.NO_ACTION,
        description="No letter mapping drift detected",
        affected_component=evaluator_id
    )


# =============================================================================
# GUARD-005: Quota/Funding Abort
# =============================================================================

def check_quota_abort(
    error_message: str,
    component_name: str = "unknown"
) -> GuardResult:
    """
    GUARD-005: Quota/Funding Abort
    
    Triggered when: Run terminates mid-batch due to quota exhaustion.
    
    Implementation:
    1. Finalize all completed questions
    2. Mark incomplete questions as NOT_RUN
    3. Preserve completed data in merged_results.jsonl
    
    Principle: Do not discard usable epistemic data. Partial runs have value.
    """
    if not error_message:
        return GuardResult(
            guard_id="GUARD-005",
            triggered=False,
            action=GuardAction.NO_ACTION,
            description="No error message to check",
            affected_component=component_name
        )
    
    error_lower = error_message.lower()
    
    # Quota/rate limit indicators
    quota_indicators = [
        "quota", "rate limit", "rate_limit", "ratelimit",
        "429", "too many requests", "resource exhausted",
        "billing", "insufficient funds", "payment required",
        "limit exceeded", "capacity", "throttl"
    ]
    
    # Explicitly NOT quota errors (GUARD-006 handles these)
    not_quota_indicators = [
        "json_extraction_failed", "json_parse_failed",
        "invalid json", "parse error", "syntax error"
    ]
    
    # Check for explicit non-quota errors first
    for indicator in not_quota_indicators:
        if indicator in error_lower:
            return GuardResult(
                guard_id="GUARD-005",
                triggered=False,
                action=GuardAction.NO_ACTION,
                description="Error is not quota-related (likely JSON parsing)",
                affected_component=component_name
            )
    
    # Check for quota indicators
    for indicator in quota_indicators:
        if indicator in error_lower:
            return GuardResult(
                guard_id="GUARD-005",
                triggered=True,
                action=GuardAction.PRESERVE_DATA,
                description="Quota/Funding Abort: Resource limit reached",
                affected_component=component_name,
                error_code="QUOTA_ABORT",
                details=f"Quota indicator found: '{indicator}'"
            )
    
    return GuardResult(
        guard_id="GUARD-005",
        triggered=False,
        action=GuardAction.NO_ACTION,
        description="No quota/funding abort detected",
        affected_component=component_name
    )


# =============================================================================
# GUARD-006: JSON Extraction Failure
# =============================================================================

def check_json_extraction_failure(
    raw_content: str,
    error_message: str = None
) -> Tuple[GuardResult, Optional[str]]:
    """
    GUARD-006: JSON Extraction Failure
    
    Triggered when: Model returns content with LaTeX math notation that contains
    invalid JSON escape sequences (e.g., \\gamma, \\beta).
    
    Implementation:
    1. Pre-process JSON strings to fix invalid LaTeX escapes
    2. Retry parsing with fixed content
    3. Never misclassify as quota error
    
    Principle: Parsing failure ≠ quota failure. Fix extractable content,
    don't abort the run.
    
    Returns:
        Tuple of (GuardResult, fixed_content or None)
    """
    if not raw_content:
        return GuardResult(
            guard_id="GUARD-006",
            triggered=False,
            action=GuardAction.NO_ACTION,
            description="No content to check for JSON extraction",
            affected_component="json_parser"
        ), None
    
    # Try to parse as-is first
    try:
        json.loads(raw_content)
        return GuardResult(
            guard_id="GUARD-006",
            triggered=False,
            action=GuardAction.NO_ACTION,
            description="JSON parsing succeeded without fixes",
            affected_component="json_parser"
        ), raw_content
    except json.JSONDecodeError:
        pass
    
    # Apply LaTeX escape fixes
    fixed_content = _fix_latex_escapes(raw_content)
    
    try:
        json.loads(fixed_content)
        return GuardResult(
            guard_id="GUARD-006",
            triggered=True,
            action=GuardAction.LOG_ERROR,
            description="JSON Extraction Failure: Fixed LaTeX escapes",
            affected_component="json_parser",
            error_code="JSON_LATEX_FIX",
            details="Applied LaTeX escape fixes to enable parsing"
        ), fixed_content
    except json.JSONDecodeError as e:
        return GuardResult(
            guard_id="GUARD-006",
            triggered=True,
            action=GuardAction.LOG_ERROR,
            description="JSON Extraction Failure: Could not fix content",
            affected_component="json_parser",
            error_code="JSON_PARSE_FAILED",
            details=f"Parse error after fixes: {str(e)[:100]}"
        ), None


def _fix_latex_escapes(content: str) -> str:
    """
    Fix common LaTeX escape sequences that break JSON parsing.
    
    Converts invalid escapes like \\gamma to \\\\gamma for JSON compatibility.
    """
    # Common LaTeX commands that appear in physics/math content
    latex_commands = [
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
        "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
        "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
        "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
        "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho",
        "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
        "partial", "nabla", "infty", "sum", "prod", "int", "oint",
        "sqrt", "frac", "vec", "hat", "bar", "dot", "ddot",
        "sin", "cos", "tan", "log", "ln", "exp", "lim",
        "cdot", "times", "div", "pm", "mp", "leq", "geq", "neq",
        "approx", "equiv", "propto", "sim", "simeq",
        "left", "right", "big", "Big", "bigg", "Bigg",
        "text", "mathrm", "mathbf", "mathit", "mathcal",
        "hbar", "ell", "Re", "Im"
    ]
    
    fixed = content
    for cmd in latex_commands:
        # Replace \cmd with \\cmd (escape the backslash for JSON)
        # But only if not already escaped
        pattern = r'(?<!\\)\\' + cmd + r'(?![a-zA-Z])'
        replacement = r'\\\\' + cmd
        fixed = re.sub(pattern, replacement, fixed)
    
    return fixed


# =============================================================================
# Main Guard Application Function
# =============================================================================

def apply_pipeline_guards(
    evaluator_outputs: Dict[str, dict] = None,
    analyzer_output: dict = None,
    synthesizer_output: dict = None,
    error_messages: List[str] = None,
    valid_options: Set[str] = None,
) -> PipelineGuardResults:
    """
    Apply all pipeline guards and collect results.
    
    Args:
        evaluator_outputs: Dict mapping evaluator_id to output dict
        analyzer_output: Output from Grok analyzer (R1.5)
        synthesizer_output: Output from synthesizer
        error_messages: List of error messages encountered
        valid_options: Set of valid option letters (default: A, B, C, D)
    
    Returns:
        PipelineGuardResults with all guard outcomes
    """
    if valid_options is None:
        valid_options = {"A", "B", "C", "D"}
    
    guard_results = []
    excluded_evaluators = []
    unavailable_components = []
    fragility_markers = []
    fallback_applied = False
    errors_logged = []
    
    # GUARD-001: Check each evaluator for schema failures
    if evaluator_outputs:
        for eval_id, eval_output in evaluator_outputs.items():
            result = check_evaluator_schema_failure(eval_output, eval_id)
            guard_results.append(result)
            if result.triggered:
                excluded_evaluators.append(eval_id)
                errors_logged.append(f"{result.error_code}: {eval_id}")
    
    # GUARD-002: Check analyzer schema
    if analyzer_output is not None:
        result = check_analyzer_schema_failure(analyzer_output)
        guard_results.append(result)
        if result.triggered:
            unavailable_components.append("grok_analyzer")
            errors_logged.append(f"{result.error_code}: grok_analyzer")
    
    # GUARD-003: Check synthesizer for invalid options
    if synthesizer_output:
        result = check_synthesizer_candidate_corruption(synthesizer_output, valid_options)
        guard_results.append(result)
        if result.triggered:
            fallback_applied = True
            errors_logged.append(f"{result.error_code}: {result.details}")
    
    # GUARD-004: Check for letter mapping drift in evaluators
    if evaluator_outputs:
        for eval_id, eval_output in evaluator_outputs.items():
            result = check_letter_mapping_drift(eval_output, eval_id)
            guard_results.append(result)
            if result.triggered:
                fragility_markers.append(f"{eval_id}: {result.error_code}")
    
    # GUARD-005 & GUARD-006: Check error messages
    if error_messages:
        for error_msg in error_messages:
            # Check quota first
            quota_result = check_quota_abort(error_msg)
            guard_results.append(quota_result)
            if quota_result.triggered:
                errors_logged.append(f"{quota_result.error_code}: {quota_result.details}")
            
            # Check JSON extraction
            json_result, _ = check_json_extraction_failure(error_msg)
            guard_results.append(json_result)
            if json_result.triggered:
                errors_logged.append(f"{json_result.error_code}: {json_result.details}")
    
    guards_triggered = sum(1 for r in guard_results if r.triggered)
    
    return PipelineGuardResults(
        guards_evaluated=len(guard_results),
        guards_triggered=guards_triggered,
        guard_results=guard_results,
        excluded_evaluators=excluded_evaluators,
        unavailable_components=unavailable_components,
        fragility_markers=fragility_markers,
        fallback_applied=fallback_applied,
        errors_logged=errors_logged
    )


# =============================================================================
# Convenience Functions
# =============================================================================

def get_pipeline_guards_version() -> str:
    """Return the version of the pipeline guards module."""
    return PIPELINE_GUARDS_VERSION


def get_guard_descriptions() -> Dict[str, str]:
    """Return human-readable descriptions of all guards."""
    return {
        "GUARD-001": "Evaluator Schema Failure: Exclude broken evaluator from aggregation (agent failure ≠ disagreement)",
        "GUARD-002": "Analyzer Schema Failure: Mark analyzer unavailable, preserve R1 unanimity",
        "GUARD-003": "Synthesizer Candidate Corruption: Discard invalid options, fallback to deterministic",
        "GUARD-004": "Letter Mapping Drift: Mark corrected drift as fragility signal",
        "GUARD-005": "Quota/Funding Abort: Preserve completed data, mark incomplete as NOT_RUN",
        "GUARD-006": "JSON Extraction Failure: Fix LaTeX escapes, never misclassify as quota error",
    }


if __name__ == "__main__":
    # Test the module
    print(f"Pipeline Guards {get_pipeline_guards_version()}")
    print(f"Status: {PIPELINE_GUARDS_STATUS}")
    print("\nGuards implemented:")
    for guard_id, desc in get_guard_descriptions().items():
        print(f"  {guard_id}: {desc}")
    
    # Test GUARD-006 LaTeX fix
    print("\n--- Testing GUARD-006 LaTeX fix ---")
    test_content = '{"formula": "E = mc^2, where \\gamma is the Lorentz factor"}'
    result, fixed = check_json_extraction_failure(test_content)
    print(f"Triggered: {result.triggered}")
    print(f"Action: {result.action}")
    if fixed:
        print(f"Fixed content parseable: {True}")
