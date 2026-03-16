"""
SciFact Evidence Challenge (Stage 2)

Audits the grounding quality of Stage 1 evaluator verdicts.
A challenger model receives all evaluator outputs and probes whether
their cited evidence actually supports their verdicts.

This module handles:
- Formatting evaluator outputs for the challenger prompt
- Running the challenge model (GPT-4.1 via ProviderRouter)
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
# Compact example JSON for the challenger prompt.
# Same pattern as the evaluator: show an example, not the schema.
# ============================================================

CHALLENGER_EXAMPLE_JSON = """{
  "grounding_analysis": [
    {
      "evaluator": "A",
      "cited_relevant": [2, 5],
      "cited_irrelevant": [],
      "missing_key_sentences": [7],
      "grounding_quality": "adequate",
      "notes": "Cited sentences support the verdict but missed sentence 7."
    },
    {
      "evaluator": "B",
      "cited_relevant": [2],
      "cited_irrelevant": [3],
      "missing_key_sentences": [5],
      "grounding_quality": "weak",
      "notes": "Sentence 3 discusses a different population than the claim."
    },
    {
      "evaluator": "C",
      "cited_relevant": [2, 5, 7],
      "cited_irrelevant": [],
      "missing_key_sentences": [],
      "grounding_quality": "strong",
      "notes": "All cited sentences are directly relevant."
    }
  ],
  "scope_consensus": {
    "agree_on_scope": true,
    "scope_issues": [],
    "notes": "All evaluators agree the abstract directly addresses the claim."
  },
  "inference_flags": [
    {
      "evaluator": "B",
      "inference_type": "external_knowledge",
      "description": "Used population-level data not in the abstract.",
      "severity": "moderate"
    }
  ],
  "verdict_analysis": {
    "unanimous": false,
    "disagreement_source": "precision_tolerance",
    "notes": "Evaluators A and C accepted approximate match; B required exact numbers."
  },
  "overall_grounding_quality": "adequate"
}"""


# ============================================================
# Normalization Maps
# ============================================================

GROUNDING_QUALITY_MAP = {
    "strong": "strong",
    "adequate": "adequate",
    "weak": "weak",
    "ungrounded": "ungrounded",
    "Strong": "strong",
    "Adequate": "adequate",
    "Weak": "weak",
    "Ungrounded": "ungrounded",
    "STRONG": "strong",
    "ADEQUATE": "adequate",
    "WEAK": "weak",
    "UNGROUNDED": "ungrounded",
}

OVERALL_QUALITY_MAP = {
    "strong": "strong",
    "adequate": "adequate",
    "weak": "weak",
    "mixed": "mixed",
    "Strong": "strong",
    "Adequate": "adequate",
    "Weak": "weak",
    "Mixed": "mixed",
    "STRONG": "strong",
    "ADEQUATE": "adequate",
    "WEAK": "weak",
    "MIXED": "mixed",
}

INFERENCE_TYPE_MAP = {
    "external_knowledge": "external_knowledge",
    "correlation_causation": "correlation_causation",
    "overgeneralization": "overgeneralization",
    "unstated_assumption": "unstated_assumption",
    "scope_leap": "scope_leap",
    "other": "other",
}

SEVERITY_MAP = {
    "minor": "minor",
    "moderate": "moderate",
    "critical": "critical",
    "Minor": "minor",
    "Moderate": "moderate",
    "Critical": "critical",
    "MINOR": "minor",
    "MODERATE": "moderate",
    "CRITICAL": "critical",
}

DISAGREEMENT_SOURCE_MAP = {
    "none": "none",
    "scope_interpretation": "scope_interpretation",
    "evidence_selection": "evidence_selection",
    "inference_difference": "inference_difference",
    "precision_tolerance": "precision_tolerance",
    "mixed": "mixed",
    "None": "none",
    "NONE": "none",
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
    and formats them concisely for the challenger.

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
        cited = ev.get("cited_sentences", [])
        reasoning = ev.get("reasoning", "")
        # Truncate reasoning to ~3 sentences for conciseness
        reasoning_short = _truncate_to_sentences(reasoning, max_sentences=3)
        scope = ev.get("scope_assessment", {})
        scope_match = scope.get("scope_match", "unknown")
        scope_notes = scope.get("scope_notes", "")
        assumptions = ev.get("assumptions", [])
        sufficiency = ev.get("evidence_sufficiency", "unknown")
        key_evidence = ev.get("key_evidence", "")

        lines.append(f"--- Evaluator {label} ---")
        lines.append(f"  Verdict: {verdict}")
        lines.append(f"  Confidence: {confidence}")
        lines.append(f"  Cited sentences: {cited}")
        lines.append(f"  Reasoning: {reasoning_short}")
        lines.append(f"  Scope match: {scope_match}")
        if scope_notes:
            lines.append(f"  Scope notes: {scope_notes}")
        if assumptions:
            lines.append(f"  Assumptions: {'; '.join(assumptions)}")
        lines.append(f"  Evidence sufficiency: {sufficiency}")
        if key_evidence:
            lines.append(f"  Key evidence: {key_evidence}")
        lines.append("")

    return "\n".join(lines)


def _truncate_to_sentences(text, max_sentences=3):
    """Truncate text to approximately max_sentences sentences."""
    if not text:
        return ""
    # Split on sentence endings
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

    # grounding_analysis — list of per-evaluator assessments
    if "grounding_analysis" in parsed and isinstance(parsed["grounding_analysis"], list):
        for ga in parsed["grounding_analysis"]:
            if not isinstance(ga, dict):
                continue
            # Ensure evaluator label is a string
            if "evaluator" in ga and not isinstance(ga["evaluator"], str):
                ga["evaluator"] = str(ga["evaluator"])
            # Normalize integer lists
            for field in ["cited_relevant", "cited_irrelevant", "missing_key_sentences"]:
                if field in ga:
                    ga[field] = _normalize_int_list(ga[field])
            # Normalize grounding quality
            if "grounding_quality" in ga:
                ga["grounding_quality"] = _normalize_string(
                    ga["grounding_quality"], GROUNDING_QUALITY_MAP, "adequate"
                )
            # Ensure notes is string
            if "notes" in ga:
                if ga["notes"] is None:
                    ga["notes"] = ""
                elif not isinstance(ga["notes"], str):
                    ga["notes"] = str(ga["notes"])

    # scope_consensus
    if "scope_consensus" in parsed and isinstance(parsed["scope_consensus"], dict):
        sc = parsed["scope_consensus"]
        # agree_on_scope should be bool
        if "agree_on_scope" in sc:
            if isinstance(sc["agree_on_scope"], str):
                sc["agree_on_scope"] = sc["agree_on_scope"].lower() in ("true", "yes", "1")
        # scope_issues should be list of strings
        if "scope_issues" in sc:
            if not isinstance(sc["scope_issues"], list):
                sc["scope_issues"] = [sc["scope_issues"]] if sc["scope_issues"] else []
            sc["scope_issues"] = [str(s) for s in sc["scope_issues"] if s is not None]
        # notes should be string
        if "notes" in sc:
            if sc["notes"] is None:
                sc["notes"] = ""
            elif not isinstance(sc["notes"], str):
                sc["notes"] = str(sc["notes"])

    # inference_flags — list of flag objects
    if "inference_flags" in parsed and isinstance(parsed["inference_flags"], list):
        for flag in parsed["inference_flags"]:
            if not isinstance(flag, dict):
                continue
            if "evaluator" in flag and not isinstance(flag["evaluator"], str):
                flag["evaluator"] = str(flag["evaluator"])
            if "inference_type" in flag:
                flag["inference_type"] = _normalize_string(
                    flag["inference_type"], INFERENCE_TYPE_MAP, "other"
                )
            if "severity" in flag:
                flag["severity"] = _normalize_string(
                    flag["severity"], SEVERITY_MAP, "moderate"
                )
            if "description" in flag:
                if flag["description"] is None:
                    flag["description"] = ""
                elif not isinstance(flag["description"], str):
                    flag["description"] = str(flag["description"])

    # verdict_analysis
    if "verdict_analysis" in parsed and isinstance(parsed["verdict_analysis"], dict):
        va = parsed["verdict_analysis"]
        if "unanimous" in va:
            if isinstance(va["unanimous"], str):
                va["unanimous"] = va["unanimous"].lower() in ("true", "yes", "1")
        if "disagreement_source" in va:
            va["disagreement_source"] = _normalize_string(
                va["disagreement_source"], DISAGREEMENT_SOURCE_MAP, "none"
            )
        if "notes" in va:
            if va["notes"] is None:
                va["notes"] = ""
            elif not isinstance(va["notes"], str):
                va["notes"] = str(va["notes"])

    # overall_grounding_quality
    if "overall_grounding_quality" in parsed:
        parsed["overall_grounding_quality"] = _normalize_string(
            parsed["overall_grounding_quality"], OVERALL_QUALITY_MAP, "adequate"
        )

    return parsed


# ============================================================
# Public API
# ============================================================

def normalize_challenge_response(raw_response, label=""):
    """
    Parse, normalize, and validate a challenge response.

    Args:
        raw_response: Raw string from the model.
        label: Label for logging (e.g., "Claim 5").

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
