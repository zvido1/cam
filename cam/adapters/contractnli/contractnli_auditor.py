"""
ContractNLI Auditor (Stage 3)

Validates the reasoning process of Stage 1 evaluators and Stage 2 challenge.
Checks structural validity, constraint compliance, grounding quality,
consistency, challenge survival, and span overlap.

This module handles:
- Formatting challenge results for the auditor prompt
- Running the auditor model (GPT-5.2 reasoning_effort=high)
- Normalizing and validating auditor responses
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None

from cam.core.json_extract import safe_json_extract

logger = logging.getLogger(__name__)

# ============================================================
# Compact example JSON for the auditor prompt.
# ============================================================

AUDITOR_EXAMPLE_JSON = """{
  "structural_validity": "concerns",
  "constraint_compliance": true,
  "grounding_quality": "adequate",
  "consistency_issues": [
    "Evaluator C cites Span 11 (exception clause) but does not account for it in the ENTAILMENT verdict."
  ],
  "challenge_survival": "Evaluators A and B survive challenge. Evaluator C's reasoning is weakened by the missed exception clause in Span 11 flagged by the challenger.",
  "span_overlap_assessment": "partial",
  "reasoning": "Two of three evaluators are well-grounded with overlapping span citations. Evaluator C has a consistency gap between cited evidence and verdict. The challenger's negation resolution finding is material.",
  "recommendation": "flag"
}"""


# ============================================================
# Normalization Maps
# ============================================================

VALIDITY_MAP = {
    "valid": "valid", "concerns": "concerns", "invalid": "invalid",
    "Valid": "valid", "Concerns": "concerns", "Invalid": "invalid",
    "VALID": "valid", "CONCERNS": "concerns", "INVALID": "invalid",
    "sound": "valid", "problematic": "concerns",
}

GROUNDING_MAP = {
    "strong": "strong", "adequate": "adequate", "weak": "weak", "ungrounded": "ungrounded",
    "Strong": "strong", "Adequate": "adequate", "Weak": "weak", "Ungrounded": "ungrounded",
    "STRONG": "strong", "ADEQUATE": "adequate", "WEAK": "weak", "UNGROUNDED": "ungrounded",
    "good": "strong", "fair": "adequate", "poor": "weak",
}

OVERLAP_MAP = {
    "high": "high", "partial": "partial", "none": "none",
    "High": "high", "Partial": "partial", "None": "none",
    "HIGH": "high", "PARTIAL": "partial", "NONE": "none",
    "significant": "high", "low": "none", "minimal": "none",
}

RECOMMENDATION_MAP = {
    "proceed": "proceed", "flag": "flag", "escalate": "escalate",
    "Proceed": "proceed", "Flag": "flag", "Escalate": "escalate",
    "PROCEED": "proceed", "FLAG": "flag", "ESCALATE": "escalate",
    "pass": "proceed", "PASS": "proceed",
}


# ============================================================
# Schema Loading
# ============================================================

_SCHEMA_CACHE = {}


def _get_auditor_schema():
    """Load and cache the auditor schema."""
    if "auditor" not in _SCHEMA_CACHE:
        schema_path = Path(__file__).parent / "schemas" / "auditor_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE["auditor"] = json.load(f)
    return _SCHEMA_CACHE["auditor"]


# ============================================================
# Formatting Challenge Results for Auditor
# ============================================================

def format_challenge_for_auditor(challenge_result):
    """
    Format Stage 2 challenge results for the auditor prompt.

    Args:
        challenge_result: normalized challenge response dict

    Returns:
        Formatted string summarizing key challenge findings.
    """
    if "error" in challenge_result and "challenges" not in challenge_result:
        return "[Challenge failed -- no results available]"

    lines = []

    # Challenges list
    challenges = challenge_result.get("challenges", [])
    if challenges:
        lines.append(f"Challenges Found ({len(challenges)}):")
        for ch in challenges:
            ch_type = ch.get("challenge_type", "?")
            severity = ch.get("severity", "?")
            affected = ch.get("affected_evaluators", [])
            desc = ch.get("description", "")[:200]
            missing = ch.get("missing_spans", [])
            lines.append(f"  [{severity.upper()}] {ch_type}: affects evaluator(s) {', '.join(affected)}")
            lines.append(f"    {desc}")
            if missing:
                lines.append(f"    Missing spans: {missing}")
        lines.append("")
    else:
        lines.append("Challenges Found: none")
        lines.append("")

    # Overall assessment
    overall = challenge_result.get("overall_grounding_assessment", "?")
    lines.append(f"Overall Grounding Assessment: {overall}")

    # Reasoning
    reasoning = challenge_result.get("reasoning", "")
    if reasoning:
        lines.append(f"Challenger Reasoning: {reasoning[:300]}")

    return "\n".join(lines)


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


def _normalize_auditor_fields(parsed):
    """Normalize individual fields in the parsed auditor response."""

    # structural_validity
    if "structural_validity" in parsed:
        parsed["structural_validity"] = _normalize_string(
            parsed["structural_validity"], VALIDITY_MAP, "concerns"
        )

    # constraint_compliance -- boolean
    if "constraint_compliance" in parsed:
        val = parsed["constraint_compliance"]
        if isinstance(val, str):
            parsed["constraint_compliance"] = val.lower() in ("true", "yes", "1")

    # grounding_quality
    if "grounding_quality" in parsed:
        parsed["grounding_quality"] = _normalize_string(
            parsed["grounding_quality"], GROUNDING_MAP, "adequate"
        )

    # consistency_issues -- list of strings
    if "consistency_issues" in parsed:
        if not isinstance(parsed["consistency_issues"], list):
            ci = parsed["consistency_issues"]
            parsed["consistency_issues"] = [ci] if ci else []
        parsed["consistency_issues"] = [
            str(s) for s in parsed["consistency_issues"] if s is not None
        ]
    else:
        parsed["consistency_issues"] = []

    # challenge_survival -- string
    if "challenge_survival" in parsed:
        if parsed["challenge_survival"] is None:
            parsed["challenge_survival"] = ""
        elif not isinstance(parsed["challenge_survival"], str):
            parsed["challenge_survival"] = str(parsed["challenge_survival"])
    else:
        parsed["challenge_survival"] = ""

    # span_overlap_assessment
    if "span_overlap_assessment" in parsed:
        parsed["span_overlap_assessment"] = _normalize_string(
            parsed["span_overlap_assessment"], OVERLAP_MAP, "partial"
        )

    # reasoning -- string
    if "reasoning" in parsed:
        if parsed["reasoning"] is None:
            parsed["reasoning"] = ""
        elif not isinstance(parsed["reasoning"], str):
            parsed["reasoning"] = str(parsed["reasoning"])
    else:
        parsed["reasoning"] = ""

    # recommendation
    if "recommendation" in parsed:
        parsed["recommendation"] = _normalize_string(
            parsed["recommendation"], RECOMMENDATION_MAP, "flag"
        )

    return parsed


# ============================================================
# Public API
# ============================================================

def normalize_auditor_response(raw_response, label=""):
    """
    Parse, normalize, and validate an auditor response.

    Args:
        raw_response: Raw string from the model.
        label: Label for logging (e.g., "contract_478_nda-1").

    Returns:
        dict with either:
        - Normalized auditor fields + "schema_valid": True/False + "schema_error": str|None
        - {"error": "description"} if parsing completely fails
    """
    if not raw_response or not raw_response.strip():
        return {"error": f"[{label}] Empty response"}

    # Step 1: Extract JSON from response
    try:
        parsed = safe_json_extract(raw_response)
    except ValueError as e:
        return {"error": f"[{label}] JSON extraction failed: {e}"}

    if not isinstance(parsed, dict):
        return {"error": f"[{label}] Extracted JSON is not a dict: {type(parsed)}"}

    # Step 2: Normalize fields
    parsed = _normalize_auditor_fields(parsed)

    # Step 3: Validate against schema
    schema = _get_auditor_schema()
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
