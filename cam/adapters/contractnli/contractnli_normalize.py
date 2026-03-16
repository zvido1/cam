"""
ContractNLI Response Normalization Layer

Normalizes model responses to canonical values before schema validation.
Follows the same pattern as cam/adapters/scifact/scifact_normalize.py.
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
    "ENTAILMENT": "ENTAILMENT",
    "CONTRADICTION": "CONTRADICTION",
    "NOT_MENTIONED": "NOT_MENTIONED",
    # Case variations
    "entailment": "ENTAILMENT",
    "Entailment": "ENTAILMENT",
    "contradiction": "CONTRADICTION",
    "Contradiction": "CONTRADICTION",
    "not_mentioned": "NOT_MENTIONED",
    "Not_Mentioned": "NOT_MENTIONED",
    "NotMentioned": "NOT_MENTIONED",
    "notmentioned": "NOT_MENTIONED",
    # Common model outputs
    "ENTAILED": "ENTAILMENT",
    "entailed": "ENTAILMENT",
    "CONTRADICTED": "CONTRADICTION",
    "contradicted": "CONTRADICTION",
    "NOT MENTIONED": "NOT_MENTIONED",
    "Not Mentioned": "NOT_MENTIONED",
    "not mentioned": "NOT_MENTIONED",
    # Potential crossover from SciFact-style labels
    "SUPPORT": "ENTAILMENT",
    "SUPPORTS": "ENTAILMENT",
    "CONTRADICT": "CONTRADICTION",
    "REFUTES": "CONTRADICTION",
    "NOT_ENOUGH_INFO": "NOT_MENTIONED",
    "NEI": "NOT_MENTIONED",
    # More variations
    "NEUTRAL": "NOT_MENTIONED",
    "neutral": "NOT_MENTIONED",
    "NONE": "NOT_MENTIONED",
    "none": "NOT_MENTIONED",
    "N/A": "NOT_MENTIONED",
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

    # Cited spans -- ensure list of non-negative integers
    if "cited_spans" in parsed:
        raw = parsed["cited_spans"]
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
        parsed["cited_spans"] = cleaned

    # Exception clauses noted -- ensure list of strings
    if "exception_clauses_noted" in parsed:
        raw = parsed["exception_clauses_noted"]
        if isinstance(raw, bool):
            raw = ["Exception clause noted"] if raw else []
        elif not isinstance(raw, list):
            raw = [raw] if raw is not None else []
        parsed["exception_clauses_noted"] = [str(a) for a in raw if a is not None]
    else:
        parsed["exception_clauses_noted"] = []

    # Definitions traced -- ensure list of strings
    if "definitions_traced" in parsed:
        raw = parsed["definitions_traced"]
        if isinstance(raw, bool):
            raw = ["Definition traced"] if raw else []
        elif not isinstance(raw, list):
            raw = [raw] if raw is not None else []
        parsed["definitions_traced"] = [str(a) for a in raw if a is not None]
    else:
        parsed["definitions_traced"] = []

    # Assumptions -- ensure list of strings
    if "assumptions" in parsed:
        raw = parsed["assumptions"]
        if not isinstance(raw, list):
            raw = [raw] if raw is not None else []
        parsed["assumptions"] = [str(a) for a in raw if a is not None]
    else:
        parsed["assumptions"] = []

    # Reasoning -- ensure string
    if "reasoning" in parsed:
        if parsed["reasoning"] is None:
            parsed["reasoning"] = ""
        elif not isinstance(parsed["reasoning"], str):
            parsed["reasoning"] = str(parsed["reasoning"])
    else:
        parsed["reasoning"] = ""

    # Key evidence -- ensure string
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
