"""
CAM Validation Module
Extracted from run_gpqa_cam.py for modularity.
Handles JSON schema loading and response validation/normalization.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None

# Import normalization layer
try:
    from cam.adapters.gpqa.normalize_responses import (
        normalize_round1, normalize_round2c, normalize_final_commit,
        normalize_round3, normalize_auditor, normalize_grok_analyzer,
        normalize_synthesizer, normalize_r2d, normalize_r2d_tests
    )
    NORMALIZATION_AVAILABLE = True
except ImportError:
    NORMALIZATION_AVAILABLE = False
    # Dummy functions if not available
    def normalize_round1(x): return x
    def normalize_round2c(x): return x
    def normalize_final_commit(x): return x
    def normalize_round3(x): return x
    def normalize_auditor(x): return x
    def normalize_grok_analyzer(x): return x
    def normalize_synthesizer(x): return x
    def normalize_r2d(x): return x
    def normalize_r2d_tests(x): return x


def load_schema(schema_path: Path) -> dict:
    """Load JSON schema for validation."""
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_round1_response(response: dict, schema: dict) -> Tuple[bool, Optional[str]]:
    """Validate Round 1 evaluator response against schema."""
    if not JSONSCHEMA_AVAILABLE:
        return True, None
    
    try:
        jsonschema.validate(instance=response, schema=schema)
        
        # Additional constraints
        final_choice = response.get("final_choice")
        if final_choice not in ["A", "B", "C", "D", "ABSTAIN"]:
            return False, "final_choice must be A, B, C, D, or ABSTAIN"
        
        if not (0 <= response.get("confidence", -1) <= 100):
            return False, "confidence must be 0-100"
        
        # Validate why_others_wrong
        why_others = response.get("why_others_wrong", {})
        for key in ["A", "B", "C", "D"]:
            if key not in why_others:
                return False, f"why_others_wrong[{key}] is required"
        
        if "why_correct" not in response:
            return False, "why_correct is required"
        
        if "assumptions" not in response or not isinstance(response.get("assumptions"), list):
            return False, "assumptions must be an array"
        
        if "weakest_link" not in response:
            return False, "weakest_link is required"
        
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)


def validate_round2_response(response: dict, schema: dict, allow_abstain: bool) -> Tuple[bool, Optional[str]]:
    """Validate Round 2 evaluator response against schema."""
    if not JSONSCHEMA_AVAILABLE:
        return True, None
    
    try:
        jsonschema.validate(instance=response, schema=schema)
        
        # Additional constraints
        final_choice = response.get("final_choice")
        if not final_choice:
            return False, "final_choice is required"
        
        if not allow_abstain and final_choice == "ABSTAIN":
            return False, "ABSTAIN not allowed when allow_abstain=false"
        
        if not (0 <= response.get("confidence", -1) <= 100):
            return False, "confidence must be 0-100"
        
        if "changed" not in response:
            return False, "changed field is required"
        
        if "reason" not in response:
            return False, "reason field is required"
        
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)


def normalize_and_validate_round1(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize response then validate. Returns (normalized_response, is_valid, error_msg)."""
    normalized = normalize_round1(response)
    is_valid, error_msg = validate_round1_response(normalized, schema)
    return normalized, is_valid, error_msg


def normalize_and_validate_round2c(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize Round 2c response then validate."""
    normalized = normalize_round2c(response)
    if not JSONSCHEMA_AVAILABLE:
        return normalized, True, None
    try:
        jsonschema.validate(instance=normalized, schema=schema)
        return normalized, True, None
    except jsonschema.ValidationError as e:
        return normalized, False, str(e)


def normalize_and_validate_final_commit(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize Final Commit response then validate."""
    normalized = normalize_final_commit(response)
    if not JSONSCHEMA_AVAILABLE:
        return normalized, True, None
    try:
        jsonschema.validate(instance=normalized, schema=schema)
        return normalized, True, None
    except jsonschema.ValidationError as e:
        return normalized, False, str(e)


def normalize_and_validate_round3(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize Round 3 response then validate."""
    normalized = normalize_round3(response)
    if not JSONSCHEMA_AVAILABLE:
        return normalized, True, None
    try:
        jsonschema.validate(instance=normalized, schema=schema)
        return normalized, True, None
    except jsonschema.ValidationError as e:
        return normalized, False, str(e)


def normalize_and_validate_auditor(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize Auditor response then validate."""
    normalized = normalize_auditor(response)
    if not JSONSCHEMA_AVAILABLE:
        return normalized, True, None
    try:
        jsonschema.validate(instance=normalized, schema=schema)
        return normalized, True, None
    except jsonschema.ValidationError as e:
        return normalized, False, str(e)


def normalize_and_validate_grok(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize Grok Analyzer response then validate."""
    normalized = normalize_grok_analyzer(response)
    
    # DEFENSIVE: Backup filter for divergence_axes (in case normalize_responses has stale cache)
    # Grok sometimes returns verbose strings like 'other: minor variations...'
    VALID_AXES = {"mechanism", "math", "definition", "assumption", "scope", "other", "unknown"}
    if "divergence_axes" in normalized and isinstance(normalized["divergence_axes"], list):
        original_axes = normalized["divergence_axes"]
        fixed_axes = []
        for axis in original_axes:
            if not isinstance(axis, str):
                continue
            lower = axis.lower().strip()
            if lower in VALID_AXES:
                fixed_axes.append(lower)
            elif ":" in axis:
                # Extract prefix before colon (e.g., "other: ..." -> "other")
                prefix = axis.split(":")[0].strip().lower()
                if prefix in VALID_AXES:
                    fixed_axes.append(prefix)
                else:
                    fixed_axes.append("other")
            else:
                fixed_axes.append("other")
        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for ax in fixed_axes:
            if ax not in seen:
                seen.add(ax)
                deduped.append(ax)
        normalized["divergence_axes"] = deduped
    
    if not JSONSCHEMA_AVAILABLE:
        return normalized, True, None
    try:
        jsonschema.validate(instance=normalized, schema=schema)
        return normalized, True, None
    except jsonschema.ValidationError as e:
        return normalized, False, str(e)


def normalize_and_validate_r2d(response: dict, schema: dict) -> Tuple[dict, bool, Optional[str]]:
    """Normalize Round 2d (Resurrection) response then validate."""
    normalized = normalize_r2d(response)
    if not JSONSCHEMA_AVAILABLE:
        return normalized, True, None
    try:
        jsonschema.validate(instance=normalized, schema=schema)
        return normalized, True, None
    except jsonschema.ValidationError as e:
        return normalized, False, str(e)
