"""
SciFact Auditor (Stage 3)

Validates the reasoning process of Stage 1 evaluators and Stage 2 challenge.
Checks constraint compliance, reasoning coherence, cross-evaluator analysis,
and fragile agreement detection.

This module handles:
- Formatting challenge results for the auditor prompt
- Running the auditor model (Mistral Large via OpenRouter or direct)
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
  "constraint_compliance": {
    "all_cited_sentences": true,
    "all_assessed_scope": true,
    "all_stated_assumptions": true,
    "violations": [
      {
        "evaluator": "B",
        "violation": "Cited sentence [8] is irrelevant to the verdict.",
        "severity": "minor"
      }
    ]
  },
  "reasoning_coherence": [
    {"evaluator": "A", "coherent": true, "notes": "Reasoning directly supports the SUPPORT verdict."},
    {"evaluator": "B", "coherent": true, "notes": "Reasoning supports SUPPORT, though one cited sentence is tangential."},
    {"evaluator": "C", "coherent": true, "notes": "Reasoning is sound and well-grounded."}
  ],
  "cross_evaluator_analysis": {
    "sentence_overlap": "high",
    "reasoning_alignment": "aligned",
    "notes": "All three evaluators cite sentences [2] and [5] as primary evidence."
  },
  "fragile_agreement": {
    "detected": false,
    "details": "All evaluators cite overlapping sentences and reason along similar lines."
  },
  "structural_issues": [],
  "overall_assessment": "PASS"
}"""


# ============================================================
# Normalization Maps
# ============================================================

SEVERITY_MAP = {
    "minor": "minor", "moderate": "moderate", "critical": "critical",
    "Minor": "minor", "Moderate": "moderate", "Critical": "critical",
    "MINOR": "minor", "MODERATE": "moderate", "CRITICAL": "critical",
}

OVERLAP_MAP = {
    "high": "high", "partial": "partial", "none": "none",
    "High": "high", "Partial": "partial", "None": "none",
    "HIGH": "high", "PARTIAL": "partial", "NONE": "none",
    "significant": "high", "low": "none", "minimal": "none",
}

ALIGNMENT_MAP = {
    "aligned": "aligned", "partially_aligned": "partially_aligned", "divergent": "divergent",
    "Aligned": "aligned", "Partially_aligned": "partially_aligned", "Divergent": "divergent",
    "ALIGNED": "aligned", "PARTIALLY_ALIGNED": "partially_aligned", "DIVERGENT": "divergent",
    "partial": "partially_aligned", "mixed": "partially_aligned",
}

ASSESSMENT_MAP = {
    "PASS": "PASS", "FLAG": "FLAG", "FAIL": "FAIL",
    "pass": "PASS", "flag": "FLAG", "fail": "FAIL",
    "Pass": "PASS", "Flag": "FLAG", "Fail": "FAIL",
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
    if "error" in challenge_result and "grounding_analysis" not in challenge_result:
        return "[Challenge failed — no results available]"

    lines = []

    # Grounding analysis
    ga_list = challenge_result.get("grounding_analysis", [])
    if ga_list:
        lines.append("Grounding Analysis:")
        for ga in ga_list:
            ev = ga.get("evaluator", "?")
            gq = ga.get("grounding_quality", "?")
            relevant = ga.get("cited_relevant", [])
            irrelevant = ga.get("cited_irrelevant", [])
            missing = ga.get("missing_key_sentences", [])
            notes = ga.get("notes", "")
            lines.append(f"  Evaluator {ev}: grounding={gq}, relevant={relevant}, irrelevant={irrelevant}, missing={missing}")
            if notes:
                lines.append(f"    Notes: {notes}")
        lines.append("")

    # Scope consensus
    sc = challenge_result.get("scope_consensus", {})
    if sc:
        agree = sc.get("agree_on_scope", "?")
        issues = sc.get("scope_issues", [])
        notes = sc.get("notes", "")
        lines.append(f"Scope Consensus: agree={agree}")
        if issues:
            lines.append(f"  Issues: {'; '.join(issues)}")
        if notes:
            lines.append(f"  Notes: {notes}")
        lines.append("")

    # Inference flags
    flags = challenge_result.get("inference_flags", [])
    if flags:
        lines.append(f"Inference Flags ({len(flags)}):")
        for flag in flags:
            ev = flag.get("evaluator", "?")
            itype = flag.get("inference_type", "?")
            sev = flag.get("severity", "?")
            desc = flag.get("description", "")
            lines.append(f"  Evaluator {ev}: {itype} ({sev}) - {desc[:100]}")
        lines.append("")
    else:
        lines.append("Inference Flags: none")
        lines.append("")

    # Verdict analysis
    va = challenge_result.get("verdict_analysis", {})
    if va:
        unanimous = va.get("unanimous", "?")
        ds = va.get("disagreement_source", "?")
        notes = va.get("notes", "")
        lines.append(f"Verdict Analysis: unanimous={unanimous}, disagreement_source={ds}")
        if notes:
            lines.append(f"  Notes: {notes}")
        lines.append("")

    # Overall
    oq = challenge_result.get("overall_grounding_quality", "?")
    lines.append(f"Overall Grounding Quality: {oq}")

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

    # constraint_compliance
    if "constraint_compliance" in parsed and isinstance(parsed["constraint_compliance"], dict):
        cc = parsed["constraint_compliance"]
        for bool_field in ["all_cited_sentences", "all_assessed_scope", "all_stated_assumptions"]:
            if bool_field in cc:
                if isinstance(cc[bool_field], str):
                    cc[bool_field] = cc[bool_field].lower() in ("true", "yes", "1")
        if "violations" in cc and isinstance(cc["violations"], list):
            for v in cc["violations"]:
                if not isinstance(v, dict):
                    continue
                if "evaluator" in v and not isinstance(v["evaluator"], str):
                    v["evaluator"] = str(v["evaluator"])
                if "violation" in v:
                    if v["violation"] is None:
                        v["violation"] = ""
                    elif not isinstance(v["violation"], str):
                        v["violation"] = str(v["violation"])
                if "severity" in v:
                    v["severity"] = _normalize_string(v["severity"], SEVERITY_MAP, "minor")

    # reasoning_coherence — list of per-evaluator dicts
    if "reasoning_coherence" in parsed and isinstance(parsed["reasoning_coherence"], list):
        for rc in parsed["reasoning_coherence"]:
            if not isinstance(rc, dict):
                continue
            if "evaluator" in rc and not isinstance(rc["evaluator"], str):
                rc["evaluator"] = str(rc["evaluator"])
            if "coherent" in rc:
                if isinstance(rc["coherent"], str):
                    rc["coherent"] = rc["coherent"].lower() in ("true", "yes", "1")
            if "notes" in rc:
                if rc["notes"] is None:
                    rc["notes"] = ""
                elif not isinstance(rc["notes"], str):
                    rc["notes"] = str(rc["notes"])

    # cross_evaluator_analysis
    if "cross_evaluator_analysis" in parsed and isinstance(parsed["cross_evaluator_analysis"], dict):
        cea = parsed["cross_evaluator_analysis"]
        if "sentence_overlap" in cea:
            cea["sentence_overlap"] = _normalize_string(
                cea["sentence_overlap"], OVERLAP_MAP, "partial"
            )
        if "reasoning_alignment" in cea:
            cea["reasoning_alignment"] = _normalize_string(
                cea["reasoning_alignment"], ALIGNMENT_MAP, "partially_aligned"
            )
        if "notes" in cea:
            if cea["notes"] is None:
                cea["notes"] = ""
            elif not isinstance(cea["notes"], str):
                cea["notes"] = str(cea["notes"])

    # fragile_agreement
    if "fragile_agreement" in parsed and isinstance(parsed["fragile_agreement"], dict):
        fa = parsed["fragile_agreement"]
        if "detected" in fa:
            if isinstance(fa["detected"], str):
                fa["detected"] = fa["detected"].lower() in ("true", "yes", "1")
        if "details" in fa:
            if fa["details"] is None:
                fa["details"] = ""
            elif not isinstance(fa["details"], str):
                fa["details"] = str(fa["details"])

    # structural_issues — list of strings
    if "structural_issues" in parsed:
        if not isinstance(parsed["structural_issues"], list):
            parsed["structural_issues"] = [parsed["structural_issues"]] if parsed["structural_issues"] else []
        parsed["structural_issues"] = [str(s) for s in parsed["structural_issues"] if s is not None]

    # overall_assessment
    if "overall_assessment" in parsed:
        parsed["overall_assessment"] = _normalize_string(
            parsed["overall_assessment"], ASSESSMENT_MAP, "FLAG"
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
        label: Label for logging (e.g., "Claim 5").

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
