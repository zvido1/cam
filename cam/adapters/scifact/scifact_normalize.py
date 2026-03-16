"""
SciFact Response Normalization Layer

Normalizes model responses to canonical values before schema validation.
Follows the same pattern as cam/adapters/gpqa/normalize_responses.py.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None

from cam.core.json_extract import safe_json_extract

logger = logging.getLogger(__name__)

# ============================================================
# Verdict Normalization
# ============================================================

VERDICT_MAP = {
    # Standard values
    "SUPPORT": "SUPPORT",
    "CONTRADICT": "CONTRADICT",
    "NOT_ENOUGH_INFO": "NOT_ENOUGH_INFO",
    # Case variations
    "support": "SUPPORT",
    "Support": "SUPPORT",
    "contradict": "CONTRADICT",
    "Contradict": "CONTRADICT",
    "not_enough_info": "NOT_ENOUGH_INFO",
    "Not_Enough_Info": "NOT_ENOUGH_INFO",
    "NEI": "NOT_ENOUGH_INFO",
    "nei": "NOT_ENOUGH_INFO",
    # Common model outputs (raw SciFact labels)
    "SUPPORTS": "SUPPORT",
    "supports": "SUPPORT",
    "Supports": "SUPPORT",
    "REFUTES": "CONTRADICT",
    "refutes": "CONTRADICT",
    "Refutes": "CONTRADICT",
    "REFUTE": "CONTRADICT",
    "refute": "CONTRADICT",
    # Variations
    "SUPPORTED": "SUPPORT",
    "CONTRADICTED": "CONTRADICT",
    "INSUFFICIENT": "NOT_ENOUGH_INFO",
    "INSUFFICIENT_INFO": "NOT_ENOUGH_INFO",
    "NOT ENOUGH INFO": "NOT_ENOUGH_INFO",
    "Not Enough Info": "NOT_ENOUGH_INFO",
    "not enough info": "NOT_ENOUGH_INFO",
    "NOT_ENOUGH_INFORMATION": "NOT_ENOUGH_INFO",
    "INCONCLUSIVE": "NOT_ENOUGH_INFO",
}

CONFIDENCE_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
}

SCOPE_MATCH_MAP = {
    "exact": "exact",
    "partial": "partial",
    "mismatch": "mismatch",
    "Exact": "exact",
    "Partial": "partial",
    "Mismatch": "mismatch",
    "EXACT": "exact",
    "PARTIAL": "partial",
    "MISMATCH": "mismatch",
    "full": "exact",
    "close": "partial",
    "tangential": "mismatch",
}

SUFFICIENCY_MAP = {
    "sufficient": "sufficient",
    "partial": "partial",
    "insufficient": "insufficient",
    "Sufficient": "sufficient",
    "Partial": "partial",
    "Insufficient": "insufficient",
    "SUFFICIENT": "sufficient",
    "PARTIAL": "partial",
    "INSUFFICIENT": "insufficient",
}


# ============================================================
# Schema Loading
# ============================================================

_SCHEMA_CACHE = {}

def _get_evaluator_schema():
    """Load and cache the evaluator schema."""
    if "evaluator" not in _SCHEMA_CACHE:
        schema_path = Path(__file__).parent / "schemas" / "evaluator_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE["evaluator"] = json.load(f)
    return _SCHEMA_CACHE["evaluator"]


# ============================================================
# Normalization
# ============================================================

def _normalize_string(value, mapping, default):
    """Normalize a string value using a mapping."""
    if value is None:
        return default
    if isinstance(value, str):
        if value in mapping:
            return mapping[value]
        stripped = value.strip()
        if stripped in mapping:
            return mapping[stripped]
    return default


def _normalize_evaluator_fields(parsed):
    """Normalize individual fields in the parsed evaluator response."""
    # Verdict
    if "verdict" in parsed:
        raw_verdict = parsed["verdict"]
        normalized = _normalize_string(raw_verdict, VERDICT_MAP, None)
        if normalized is None:
            logger.warning(f"Unknown verdict '{raw_verdict}', keeping as-is")
        else:
            parsed["verdict"] = normalized

    # Confidence
    if "confidence" in parsed:
        parsed["confidence"] = _normalize_string(
            parsed["confidence"], CONFIDENCE_MAP, "medium"
        )

    # Cited sentences — ensure list of non-negative integers
    if "cited_sentences" in parsed:
        raw = parsed["cited_sentences"]
        if not isinstance(raw, list):
            raw = [raw] if raw is not None else []
        cleaned = []
        for item in raw:
            try:
                val = int(item)
                if val >= 0:
                    cleaned.append(val)
            except (ValueError, TypeError):
                pass
        parsed["cited_sentences"] = cleaned

    # Scope assessment
    if "scope_assessment" in parsed and isinstance(parsed["scope_assessment"], dict):
        sa = parsed["scope_assessment"]
        if "scope_match" in sa:
            sa["scope_match"] = _normalize_string(
                sa["scope_match"], SCOPE_MATCH_MAP, "partial"
            )
        # Ensure string fields exist
        for field in ["claim_scope", "evidence_scope", "scope_notes"]:
            if field not in sa or sa[field] is None:
                sa[field] = ""
            elif not isinstance(sa[field], str):
                sa[field] = str(sa[field])

    # Assumptions — ensure list of strings
    if "assumptions" in parsed:
        raw = parsed["assumptions"]
        if not isinstance(raw, list):
            raw = [raw] if raw is not None else []
        parsed["assumptions"] = [str(a) for a in raw if a is not None]

    # Evidence sufficiency
    if "evidence_sufficiency" in parsed:
        parsed["evidence_sufficiency"] = _normalize_string(
            parsed["evidence_sufficiency"], SUFFICIENCY_MAP, "partial"
        )

    # Reasoning — ensure string
    if "reasoning" in parsed:
        if parsed["reasoning"] is None:
            parsed["reasoning"] = ""
        elif not isinstance(parsed["reasoning"], str):
            parsed["reasoning"] = str(parsed["reasoning"])

    # Key evidence — ensure string
    if "key_evidence" in parsed:
        if parsed["key_evidence"] is None:
            parsed["key_evidence"] = ""
        elif not isinstance(parsed["key_evidence"], str):
            parsed["key_evidence"] = str(parsed["key_evidence"])

    return parsed


# ============================================================
# Public API
# ============================================================

def normalize_evaluator_response(raw_response, evaluator_label=""):
    """
    Parse, normalize, and validate an evaluator response.

    Args:
        raw_response: Raw string from the model.
        evaluator_label: Label for logging (e.g., "Evaluator A").

    Returns:
        dict with either:
        - Normalized evaluator fields + "schema_valid": True/False + "schema_error": str|None
        - {"error": "description"} if parsing completely fails
    """
    if not raw_response or not raw_response.strip():
        return {"error": f"[{evaluator_label}] Empty response"}

    # Step 1: Extract JSON from response
    try:
        parsed = safe_json_extract(raw_response)
    except ValueError as e:
        return {"error": f"[{evaluator_label}] JSON extraction failed: {e}"}

    if not isinstance(parsed, dict):
        return {"error": f"[{evaluator_label}] Extracted JSON is not a dict: {type(parsed)}"}

    # Step 2: Normalize fields
    parsed = _normalize_evaluator_fields(parsed)

    # Step 3: Validate against schema
    schema = _get_evaluator_schema()
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
