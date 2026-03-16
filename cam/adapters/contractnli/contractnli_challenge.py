"""
ContractNLI Evidence Challenge (Stage 2)

Audits the grounding quality of Stage 1 evaluator verdicts with
legal-specific challenge probes: negation resolution, definition
resolution, span completeness, and cross-reference analysis.

This module handles:
- Formatting evaluator outputs for the challenger prompt
- Running the challenger model (GPT-5.2 reasoning_effort=high)
- Normalizing and validating challenge responses
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
# Compact example JSON for the challenger prompt
# ============================================================

CHALLENGER_EXAMPLE_JSON = """{
  "challenges": [
    {
      "challenge_type": "negation_resolution",
      "severity": "high",
      "affected_evaluators": ["C"],
      "description": "Evaluator C cited Span 8 (obligation to identify CI) but did not cite Span 11 which contains 'Notwithstanding the foregoing' -- an exception that deems System components as CI without express identification.",
      "missing_spans": [11]
    },
    {
      "challenge_type": "definition_resolution",
      "severity": "medium",
      "affected_evaluators": ["A", "B", "C"],
      "description": "All evaluators' reasoning depends on 'Proprietary Information' but only A and B cited Span 7 where it is defined. C assumed the definition without citing it.",
      "missing_spans": [7]
    },
    {
      "challenge_type": "span_completeness",
      "severity": "low",
      "affected_evaluators": ["B"],
      "description": "Evaluator B did not cite Span 15 (general provisions) which clarifies the scope of obligations under the agreement.",
      "missing_spans": [15]
    },
    {
      "challenge_type": "cross_reference",
      "severity": "medium",
      "affected_evaluators": ["C"],
      "description": "Evaluator C's cited spans are all in Section 2. Section 5 (termination) contains clauses that could modify the interpretation of the obligation.",
      "missing_spans": [42, 43]
    }
  ],
  "overall_grounding_assessment": "adequate",
  "reasoning": "Evaluators A and B are well-grounded with appropriate span citations. Evaluator C has a significant negation resolution gap (missed exception clause) that could affect verdict correctness."
}"""


# ============================================================
# Normalization Maps
# ============================================================

CHALLENGE_TYPE_MAP = {
    "negation_resolution": "negation_resolution",
    "definition_resolution": "definition_resolution",
    "span_completeness": "span_completeness",
    "cross_reference": "cross_reference",
    # Common variations
    "negation": "negation_resolution",
    "definition": "definition_resolution",
    "completeness": "span_completeness",
    "cross-reference": "cross_reference",
    "crossreference": "cross_reference",
    "cross_ref": "cross_reference",
}

SEVERITY_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "Low": "low",
    "Medium": "medium",
    "High": "high",
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    # Common variations
    "minor": "low",
    "moderate": "medium",
    "critical": "high",
}

OVERALL_ASSESSMENT_MAP = {
    "strong": "strong",
    "adequate": "adequate",
    "weak": "weak",
    "Strong": "strong",
    "Adequate": "adequate",
    "Weak": "weak",
    "STRONG": "strong",
    "ADEQUATE": "adequate",
    "WEAK": "weak",
    # Common variations
    "good": "strong",
    "fair": "adequate",
    "poor": "weak",
    "mixed": "adequate",
}


# ============================================================
# Schema Loading
# ============================================================

_SCHEMA_CACHE = {}


def _get_challenge_schema():
    """Load and cache the challenge schema."""
    if "challenge" not in _SCHEMA_CACHE:
        schema_path = Path(__file__).parent / "schemas" / "challenge_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE["challenge"] = json.load(f)
    return _SCHEMA_CACHE["challenge"]


# ============================================================
# Formatting Evaluator Outputs for Challenger
# ============================================================

def format_evaluator_outputs_for_challenge(evaluations):
    """
    Format evaluator outputs for the challenger prompt.

    Takes the dict of evaluator responses (keyed by label: A, B, C)
    and formats them for the challenger to analyze.

    Args:
        evaluations: dict of label -> normalized evaluator response

    Returns:
        Formatted string showing each evaluator's key outputs.
    """
    lines = []
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        if "error" in ev and "verdict" not in ev:
            lines.append(f"--- Evaluator {label} ---")
            lines.append(f"  [ERROR: {ev['error']}]")
            lines.append("")
            continue

        verdict = ev.get("verdict", "UNKNOWN")
        confidence = ev.get("confidence", "unknown")
        cited = ev.get("cited_spans", [])
        reasoning = ev.get("reasoning", "")
        reasoning_short = _truncate_to_sentences(reasoning, max_sentences=4)
        exception_clauses = ev.get("exception_clauses_noted", [])
        definitions = ev.get("definitions_traced", [])
        assumptions = ev.get("assumptions", [])
        key_evidence = ev.get("key_evidence", "")

        lines.append(f"--- Evaluator {label} ---")
        lines.append(f"  Verdict: {verdict}")
        lines.append(f"  Confidence: {confidence}")
        lines.append(f"  Cited spans: {cited}")
        lines.append(f"  Reasoning: {reasoning_short}")
        if exception_clauses:
            lines.append(f"  Exception clauses noted: {'; '.join(str(e) for e in exception_clauses)}")
        else:
            lines.append(f"  Exception clauses noted: none")
        if definitions:
            lines.append(f"  Definitions traced: {'; '.join(str(d) for d in definitions)}")
        else:
            lines.append(f"  Definitions traced: none")
        if assumptions:
            lines.append(f"  Assumptions: {'; '.join(str(a) for a in assumptions)}")
        if key_evidence:
            lines.append(f"  Key evidence: {key_evidence}")
        lines.append("")

    return "\n".join(lines)


def _truncate_to_sentences(text, max_sentences=4):
    """Truncate text to approximately max_sentences sentences."""
    if not text:
        return ""
    parts = text.replace(". ", ".\n").split("\n")
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= max_sentences:
        return text
    return " ".join(parts[:max_sentences]) + "..."


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


def _normalize_int_list(raw):
    """Normalize a value into a list of non-negative integers."""
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
    return cleaned


def _normalize_challenge_fields(parsed):
    """Normalize individual fields in the parsed challenge response."""

    # challenges -- list of challenge objects
    if "challenges" in parsed and isinstance(parsed["challenges"], list):
        for ch in parsed["challenges"]:
            if not isinstance(ch, dict):
                continue

            # Normalize challenge_type
            if "challenge_type" in ch:
                ch["challenge_type"] = _normalize_string(
                    ch["challenge_type"], CHALLENGE_TYPE_MAP, "span_completeness"
                )

            # Normalize severity
            if "severity" in ch:
                ch["severity"] = _normalize_string(
                    ch["severity"], SEVERITY_MAP, "medium"
                )

            # Ensure affected_evaluators is list of strings
            if "affected_evaluators" in ch:
                raw = ch["affected_evaluators"]
                if not isinstance(raw, list):
                    raw = [raw] if raw is not None else []
                ch["affected_evaluators"] = [str(e) for e in raw if e is not None]
            else:
                ch["affected_evaluators"] = []

            # Ensure description is string
            if "description" in ch:
                if ch["description"] is None:
                    ch["description"] = ""
                elif not isinstance(ch["description"], str):
                    ch["description"] = str(ch["description"])
            else:
                ch["description"] = ""

            # Normalize missing_spans
            if "missing_spans" in ch:
                ch["missing_spans"] = _normalize_int_list(ch["missing_spans"])
            else:
                ch["missing_spans"] = []

    # overall_grounding_assessment
    if "overall_grounding_assessment" in parsed:
        parsed["overall_grounding_assessment"] = _normalize_string(
            parsed["overall_grounding_assessment"], OVERALL_ASSESSMENT_MAP, "adequate"
        )

    # reasoning -- ensure string
    if "reasoning" in parsed:
        if parsed["reasoning"] is None:
            parsed["reasoning"] = ""
        elif not isinstance(parsed["reasoning"], str):
            parsed["reasoning"] = str(parsed["reasoning"])
    else:
        parsed["reasoning"] = ""

    return parsed


# ============================================================
# Public API
# ============================================================

def normalize_challenge_response(raw_response, label=""):
    """
    Parse, normalize, and validate a challenge response.

    Args:
        raw_response: Raw string from the model.
        label: Label for logging (e.g., "contract_478_nda-1").

    Returns:
        dict with either:
        - Normalized challenge fields + "schema_valid": True/False + "schema_error": str|None
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
    parsed = _normalize_challenge_fields(parsed)

    # Step 3: Validate against schema
    schema = _get_challenge_schema()
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
