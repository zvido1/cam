"""
SciFact Verdict Elimination (Stage 1b)

Stress-tests all three possible verdicts for each claim by building
the best case for each and attempting to eliminate fatally flawed ones.
Inspired by GPQA's elimination-based approach.

This module handles:
- Formatting evaluator verdicts for the elimination prompt (brief, no anchoring)
- Running the elimination model (GPT-4.1 via ProviderRouter)
- Normalizing and validating elimination responses
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
# Compact example JSON for the elimination prompt
# ============================================================

ELIMINATION_EXAMPLE_JSON = """{
  "verdict_cases": [
    {
      "verdict": "SUPPORT",
      "best_case": "Sentences 2 and 5 directly state that X increases Y (p<0.01), supporting the claim.",
      "key_sentences": [2, 5],
      "strength": "strong"
    },
    {
      "verdict": "CONTRADICT",
      "best_case": "Sentence 3 mentions a decrease in a related measure, which could imply contradiction.",
      "key_sentences": [3],
      "strength": "weak"
    },
    {
      "verdict": "NOT_ENOUGH_INFO",
      "best_case": "The abstract tests X on Y in mice, but the claim is about humans. The species gap means the abstract doesn't address the exact claim.",
      "key_sentences": [1, 2],
      "strength": "moderate"
    }
  ],
  "eliminations": [
    {
      "target_verdict": "SUPPORT",
      "elimination_type": "none",
      "reasoning": "The evidence directly addresses the claim with statistical significance. No fatal flaw.",
      "killed": false
    },
    {
      "target_verdict": "CONTRADICT",
      "elimination_type": "insufficient_evidence",
      "reasoning": "Sentence 3 discusses a different measure than the claim. The contradiction case requires inferring that a decrease in Z implies a decrease in Y, which is not stated.",
      "killed": true
    },
    {
      "target_verdict": "NOT_ENOUGH_INFO",
      "elimination_type": "none",
      "reasoning": "The species gap is real but the NEI case is moderate at best since the abstract directly studies X on Y.",
      "killed": false
    }
  ],
  "survivors": ["SUPPORT", "NOT_ENOUGH_INFO"],
  "recommended_verdict": "SUPPORT",
  "confidence_after_elimination": "high"
}"""


# ============================================================
# Normalization Maps
# ============================================================

VERDICT_MAP = {
    "SUPPORT": "SUPPORT",
    "SUPPORTS": "SUPPORT",
    "CONTRADICT": "CONTRADICT",
    "CONTRADICTS": "CONTRADICT",
    "REFUTES": "CONTRADICT",
    "NOT_ENOUGH_INFO": "NOT_ENOUGH_INFO",
    "NEI": "NOT_ENOUGH_INFO",
    "INSUFFICIENT": "NOT_ENOUGH_INFO",
}

STRENGTH_MAP = {
    "strong": "strong",
    "moderate": "moderate",
    "weak": "weak",
    "no_case": "no_case",
    "Strong": "strong",
    "Moderate": "moderate",
    "Weak": "weak",
    "No_case": "no_case",
    "STRONG": "strong",
    "MODERATE": "moderate",
    "WEAK": "weak",
    "NO_CASE": "no_case",
    "none": "no_case",
}

ELIMINATION_TYPE_MAP = {
    "scope_gap": "scope_gap",
    "precision_mismatch": "precision_mismatch",
    "insufficient_evidence": "insufficient_evidence",
    "logical_gap": "logical_gap",
    "direct_contradiction": "direct_contradiction",
    "none": "none",
    "None": "none",
    "NONE": "none",
}

CONFIDENCE_MAP = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "High": "high",
    "Medium": "medium",
    "Low": "low",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}


# ============================================================
# Schema Loading
# ============================================================

_SCHEMA_CACHE = {}

def _get_elimination_schema():
    """Load and cache the verdict elimination schema."""
    if "verdict_elimination" not in _SCHEMA_CACHE:
        schema_path = Path(__file__).parent / "schemas" / "verdict_elimination_schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE["verdict_elimination"] = json.load(f)
    return _SCHEMA_CACHE["verdict_elimination"]


# ============================================================
# Formatting Evaluator Verdicts (Brief — minimal anchoring)
# ============================================================

def format_evaluator_verdicts_brief(evaluations):
    """
    Format evaluator verdicts for the elimination prompt.
    Deliberately minimal: just verdicts + cited sentences.
    We want fresh analysis, not anchoring on evaluator reasoning.

    Args:
        evaluations: dict of evaluator label -> normalized response

    Returns:
        Formatted string showing each evaluator's verdict and cited sentences only.
    """
    lines = []
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        if "error" in ev and "verdict" not in ev:
            lines.append(f"Evaluator {label}: ERROR (no verdict)")
            continue

        verdict = ev.get("verdict", "UNKNOWN")
        cited = ev.get("cited_sentences", [])
        lines.append(f"Evaluator {label}: {verdict} (cited sentences: {cited})")

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


def _normalize_elimination_fields(parsed):
    """Normalize individual fields in the parsed elimination response."""

    # verdict_cases — array of 3 verdict case objects
    if "verdict_cases" in parsed and isinstance(parsed["verdict_cases"], list):
        for vc in parsed["verdict_cases"]:
            if not isinstance(vc, dict):
                continue
            if "verdict" in vc:
                vc["verdict"] = _normalize_string(vc["verdict"], VERDICT_MAP, vc.get("verdict", "UNKNOWN"))
            if "key_sentences" in vc:
                vc["key_sentences"] = _normalize_int_list(vc["key_sentences"])
            if "strength" in vc:
                vc["strength"] = _normalize_string(vc["strength"], STRENGTH_MAP, "moderate")
            if "best_case" in vc:
                if vc["best_case"] is None:
                    vc["best_case"] = ""
                elif not isinstance(vc["best_case"], str):
                    vc["best_case"] = str(vc["best_case"])

    # eliminations — array of elimination attempt objects
    if "eliminations" in parsed and isinstance(parsed["eliminations"], list):
        for elim in parsed["eliminations"]:
            if not isinstance(elim, dict):
                continue
            if "target_verdict" in elim:
                elim["target_verdict"] = _normalize_string(
                    elim["target_verdict"], VERDICT_MAP, elim.get("target_verdict", "UNKNOWN")
                )
            if "elimination_type" in elim:
                elim["elimination_type"] = _normalize_string(
                    elim["elimination_type"], ELIMINATION_TYPE_MAP, "none"
                )
            if "reasoning" in elim:
                if elim["reasoning"] is None:
                    elim["reasoning"] = ""
                elif not isinstance(elim["reasoning"], str):
                    elim["reasoning"] = str(elim["reasoning"])
            if "killed" in elim:
                if isinstance(elim["killed"], str):
                    elim["killed"] = elim["killed"].lower() in ("true", "yes", "1")

    # survivors — array of verdict strings
    if "survivors" in parsed and isinstance(parsed["survivors"], list):
        parsed["survivors"] = [
            _normalize_string(v, VERDICT_MAP, v) for v in parsed["survivors"]
            if isinstance(v, str)
        ]

    # recommended_verdict
    if "recommended_verdict" in parsed:
        parsed["recommended_verdict"] = _normalize_string(
            parsed["recommended_verdict"], VERDICT_MAP,
            parsed.get("recommended_verdict", "NOT_ENOUGH_INFO")
        )

    # confidence_after_elimination
    if "confidence_after_elimination" in parsed:
        parsed["confidence_after_elimination"] = _normalize_string(
            parsed["confidence_after_elimination"], CONFIDENCE_MAP, "medium"
        )

    return parsed


# ============================================================
# Public API
# ============================================================

def normalize_verdict_elimination_response(raw_response, label=""):
    """
    Parse, normalize, and validate a verdict elimination response.

    Args:
        raw_response: Raw string from the model.
        label: Label for logging (e.g., "Claim 847").

    Returns:
        dict with either:
        - Normalized elimination fields + "schema_valid": True/False + "schema_error": str|None
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
    parsed = _normalize_elimination_fields(parsed)

    # Step 3: Validate against schema
    schema = _get_elimination_schema()
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
