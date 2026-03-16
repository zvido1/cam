"""
ContractNLI Verdict Elimination (Stage 5)

Stress-tests all three possible verdicts for each (contract, hypothesis) pair
by building the best case for each and attempting to eliminate fatally flawed ones.

This module handles:
- Formatting prior stage outputs for the elimination prompt (brief, minimal anchoring)
- Running the elimination model (GPT-5.2 reasoning_effort=high)
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
  "verdict_assessments": [
    {
      "verdict": "ENTAILMENT",
      "survives": true,
      "strongest_objection": "Span 11 contains a 'notwithstanding' exception that could override the general obligation in Span 3.",
      "critical_weakness": null,
      "confidence_if_selected": "medium",
      "kill_category": null
    },
    {
      "verdict": "CONTRADICTION",
      "survives": false,
      "strongest_objection": "No span in the contract explicitly negates or prohibits the obligation described in the hypothesis.",
      "critical_weakness": "Span 7 states 'The Receiving Party agrees to hold and maintain all Confidential Information in strict confidence' — this affirms the obligation rather than negating it, making CONTRADICTION logically impossible. The case relies on absence, not contradiction.",
      "confidence_if_selected": "low",
      "kill_category": "direct_textual_contradiction"
    },
    {
      "verdict": "NOT_MENTIONED",
      "survives": true,
      "strongest_objection": "Spans 3 and 5 do address the general topic, so the contract is not entirely silent.",
      "critical_weakness": null,
      "confidence_if_selected": "medium",
      "kill_category": null
    }
  ],
  "eliminated_verdicts": ["CONTRADICTION"],
  "surviving_verdicts": ["ENTAILMENT", "NOT_MENTIONED"],
  "recommended_verdict": "ENTAILMENT",
  "reasoning": "ENTAILMENT survives because Spans 3 and 5 explicitly establish the obligation. The exception in Span 11 is noted but does not negate the general rule. CONTRADICTION is eliminated because no span directly contradicts the hypothesis. NOT_MENTIONED survives weakly because the contract's coverage of the specific scenario is arguably incomplete."
}"""


# ============================================================
# Normalization Maps
# ============================================================

VERDICT_MAP = {
    "ENTAILMENT": "ENTAILMENT",
    "CONTRADICTION": "CONTRADICTION",
    "NOT_MENTIONED": "NOT_MENTIONED",
    "Entailment": "ENTAILMENT",
    "Contradiction": "CONTRADICTION",
    "NotMentioned": "NOT_MENTIONED",
    "Not_Mentioned": "NOT_MENTIONED",
    "not_mentioned": "NOT_MENTIONED",
    "entailment": "ENTAILMENT",
    "contradiction": "CONTRADICTION",
}

CONFIDENCE_MAP = {
    "high": "high", "medium": "medium", "low": "low",
    "High": "high", "Medium": "medium", "Low": "low",
    "HIGH": "high", "MEDIUM": "medium", "LOW": "low",
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
# Formatting for Elimination Prompt
# ============================================================

def format_evaluator_verdicts_brief(evaluations):
    """
    Format evaluator verdicts for the elimination prompt.
    Deliberately minimal: just verdicts + cited spans.
    We want fresh analysis, not anchoring on evaluator reasoning.

    Args:
        evaluations: dict of evaluator label -> normalized response

    Returns:
        Formatted string showing each evaluator's verdict and cited spans only.
    """
    lines = []
    for label in sorted(evaluations.keys()):
        ev = evaluations[label]
        if "error" in ev and "verdict" not in ev:
            lines.append(f"Evaluator {label}: ERROR (no verdict)")
            continue

        verdict = ev.get("verdict", "UNKNOWN")
        cited = ev.get("cited_spans", [])
        lines.append(f"Evaluator {label}: {verdict} (cited spans: {cited})")

    return "\n".join(lines)


def format_auditor_summary_brief(auditor_result):
    """Format auditor results briefly for the elimination prompt."""
    if "error" in auditor_result and "recommendation" not in auditor_result:
        return "[Auditor failed -- no results available]"

    validity = auditor_result.get("structural_validity", "?")
    grounding = auditor_result.get("grounding_quality", "?")
    recommendation = auditor_result.get("recommendation", "?")
    overlap = auditor_result.get("span_overlap_assessment", "?")
    issues = auditor_result.get("consistency_issues", [])

    lines = [
        f"Structural validity: {validity}",
        f"Grounding quality: {grounding}",
        f"Span overlap: {overlap}",
        f"Recommendation: {recommendation}",
    ]
    if issues:
        lines.append(f"Consistency issues: {'; '.join(str(i)[:80] for i in issues)}")

    return "\n".join(lines)


def format_fragility_summary_brief(fragility_profile):
    """Format fragility profile briefly for the elimination prompt."""
    fragile = fragility_profile.get("fragile", False)
    score = fragility_profile.get("fragility_score", 0.0)
    cap = fragility_profile.get("max_cap")
    fired = fragility_profile.get("fired_rules", [])
    signal_count = fragility_profile.get("signal_count", 0)

    if not fragile:
        return "No fragility detected."

    lines = [
        f"Fragile: YES (score={score:.2f}, {signal_count} signals)",
    ]
    if fired:
        lines.append(f"Rules fired: {', '.join(fired)}")
    if cap:
        lines.append(f"Commitment cap: {cap}")

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


def _normalize_elimination_fields(parsed):
    """Normalize individual fields in the parsed elimination response."""

    # verdict_assessments -- array of 3 verdict assessment objects
    if "verdict_assessments" in parsed and isinstance(parsed["verdict_assessments"], list):
        for va in parsed["verdict_assessments"]:
            if not isinstance(va, dict):
                continue
            if "verdict" in va:
                va["verdict"] = _normalize_string(va["verdict"], VERDICT_MAP, va.get("verdict", "UNKNOWN"))
            if "survives" in va:
                if isinstance(va["survives"], str):
                    va["survives"] = va["survives"].lower() in ("true", "yes", "1")
            if "strongest_objection" in va:
                if va["strongest_objection"] is None:
                    va["strongest_objection"] = ""
                elif not isinstance(va["strongest_objection"], str):
                    va["strongest_objection"] = str(va["strongest_objection"])
            if "critical_weakness" in va:
                if va["critical_weakness"] is not None and not isinstance(va["critical_weakness"], str):
                    va["critical_weakness"] = str(va["critical_weakness"])
            else:
                va["critical_weakness"] = None
            if "confidence_if_selected" in va:
                va["confidence_if_selected"] = _normalize_string(
                    va["confidence_if_selected"], CONFIDENCE_MAP, "medium"
                )
            # Normalize kill_category to closed set or null
            VALID_KILL_CATEGORIES = {
                "direct_textual_contradiction",
                "definitional_exclusion",
                "logical_impossibility",
                "complete_scope_absence",
            }
            if "kill_category" in va:
                if va["kill_category"] not in VALID_KILL_CATEGORIES:
                    va["kill_category"] = None
                    # Invalid kill category means the kill doesn't count
                    if not va.get("survives"):
                        va["survives"] = True
                        va["critical_weakness"] = None
            else:
                va["kill_category"] = None

    # eliminated_verdicts -- array of verdict strings
    if "eliminated_verdicts" in parsed and isinstance(parsed["eliminated_verdicts"], list):
        parsed["eliminated_verdicts"] = [
            _normalize_string(v, VERDICT_MAP, v) for v in parsed["eliminated_verdicts"]
            if isinstance(v, str)
        ]
    else:
        parsed["eliminated_verdicts"] = []

    # surviving_verdicts -- array of verdict strings
    if "surviving_verdicts" in parsed and isinstance(parsed["surviving_verdicts"], list):
        parsed["surviving_verdicts"] = [
            _normalize_string(v, VERDICT_MAP, v) for v in parsed["surviving_verdicts"]
            if isinstance(v, str)
        ]
    else:
        parsed["surviving_verdicts"] = []

    # recommended_verdict
    if "recommended_verdict" in parsed:
        parsed["recommended_verdict"] = _normalize_string(
            parsed["recommended_verdict"], VERDICT_MAP,
            parsed.get("recommended_verdict", "NOT_MENTIONED")
        )

    # reasoning -- string
    if "reasoning" in parsed:
        if parsed["reasoning"] is None:
            parsed["reasoning"] = ""
        elif not isinstance(parsed["reasoning"], str):
            parsed["reasoning"] = str(parsed["reasoning"])
    else:
        parsed["reasoning"] = ""

    # Auto-derive eliminated/surviving from verdict_assessments if missing
    if "verdict_assessments" in parsed and isinstance(parsed["verdict_assessments"], list):
        if not parsed.get("eliminated_verdicts") and not parsed.get("surviving_verdicts"):
            eliminated = []
            surviving = []
            for va in parsed["verdict_assessments"]:
                if isinstance(va, dict):
                    verdict = va.get("verdict", "UNKNOWN")
                    if va.get("survives"):
                        surviving.append(verdict)
                    else:
                        eliminated.append(verdict)
            parsed["eliminated_verdicts"] = eliminated
            parsed["surviving_verdicts"] = surviving

    return parsed


# ============================================================
# Public API
# ============================================================

def normalize_elimination_response(raw_response, label=""):
    """
    Parse, normalize, and validate a verdict elimination response.

    Args:
        raw_response: Raw string from the model.
        label: Label for logging (e.g., "contract_478_nda-1").

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
