"""
Stage 5d: Use-Aware Coverage Classification (Steps 301–302a)

Adjusts coverage states based on the tenant's stated permitted use, providing the
third declared-external-context dimension in CAM's compositional governance architecture
(after jurisdiction / Stage 5b and perspective / exposure layer).

Architecture (post-call merge, Step 302a):
  - Substep 1: Model inference — _call_model_for_profile() produces text-inferred profile
  - Substep 2: Archetype match — match_archetypes() against retail_use_archetypes.json
  - Substep 3: Multi-archetype merge — merge_archetype_results() unions matched archetypes
  - Substep 4: Composition — compose_profile_with_archetypes() applies text-wins-on-conflict;
               archetype fills gaps; lp_sensitivities always archetype-sourced
  - Call 2:  batched use-aware classification (Step 303 adds multi-eval governance)
  - Never touches potentially_unenforceable, missing, not_applicable, or broken_xref
  - No downgrades in v1 — only escalates or holds

Composition rules (Substep 4, locked):
  - Text wins on conflict: non-empty/non-null/non-"None"/non-[] text field is preserved.
  - Archetype fills gaps: None / "" / "None" / [] text field is replaced by archetype value.
  - Severity bands follow scalar text-wins (no max-of-text-and-archetype in composition).
  - List fields: text list wins entirely when non-empty; no item-by-item union with text.
  - lp_sensitivities is purely archetype-sourced (no model equivalent).
  - _archetype_metadata block records matched_archetypes, field_provenance,
    fields_overridden_by_text, would_have_contributed, archetype_schema_version.

Baseline preservation:
  Every CA entry gets `coverage_state_baseline` at initial assessment time (set in
  lease_coverage._build_assessment). Stage 5d sets `use_adjusted` and
  `use_adjustment_reason` on each entry it touches.

Usage:
    from cam.adapters.lease_review.lease_use_aware_coverage import (
        should_run_use_analysis,
        match_archetypes,
        merge_archetype_results,
        compose_profile_with_archetypes,
        generate_use_profile,
        assess_use_aware_coverage,
    )
"""

import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────────────

# Step 301a: Gated pending multi-evaluator replacement (Step 302).
# Single-evaluator Stage 5d showed unacceptable variance during 2026-05-04 testing
# (3/4/0 adjustments across runs of identical file). Re-enable when Step 302 ships.
STAGE_5D_ENABLED = True  # Step 303: variance acceptance test passed 2026-05-04 (5 runs, ±1 stable)

# ── Archetype schema path ──────────────────────────────────────────────────────

_ARCHETYPES_PATH = Path(__file__).parent / "schemas" / "retail_use_archetypes.json"
_archetypes_cache: dict | None = None

# ── Severity ordering for union merge ─────────────────────────────────────────

_SEVERITY_RANK: dict[str, int] = {"None": 0, "Low": 1, "Moderate": 2, "High": 3}

# ── Stage 5d Call 2 evaluator lineup (Step 303) ───────────────────────────────
# Mirrors lease_evaluate.py's EVALUATORS dict structure exactly.
# To change a model, edit model_config.py — constants propagate here automatically.

from cam.adapters.lease_review.model_config import (  # noqa: E402
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
    SINGLE_STAGE_CHAIN,
    EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
    EVALUATOR_A_FALLBACK_LABEL, EVALUATOR_B_FALLBACK_LABEL, EVALUATOR_C_FALLBACK_LABEL,
)

EVALUATOR_LINEUP: dict[str, dict] = {
    "A": {
        "name": f"{EVALUATOR_A_PRIMARY[0]}:{EVALUATOR_A_PRIMARY[1]}",
        "provider": EVALUATOR_A_PRIMARY[0],
        "model": EVALUATOR_A_PRIMARY[1],
        "label": EVALUATOR_A_LABEL,
        "max_output_tokens": 2500,
        "temperature": 0.0,
        "timeout_sec": 300.0,
        "own_chain": [(EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], EVALUATOR_A_FALLBACK_LABEL)],
    },
    "B": {
        "name": f"{EVALUATOR_B_PRIMARY[0]}:{EVALUATOR_B_PRIMARY[1]}",
        "provider": EVALUATOR_B_PRIMARY[0],
        "model": EVALUATOR_B_PRIMARY[1],
        "label": EVALUATOR_B_LABEL,
        "max_output_tokens": 2500,
        "temperature": 0.0,
        "timeout_sec": 300.0,
        "own_chain": [(EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], EVALUATOR_B_FALLBACK_LABEL)],
    },
    "C": {
        "name": f"{EVALUATOR_C_PRIMARY[0]}:{EVALUATOR_C_PRIMARY[1]}",
        "provider": EVALUATOR_C_PRIMARY[0],
        "model": EVALUATOR_C_PRIMARY[1],
        "label": EVALUATOR_C_LABEL,
        "max_output_tokens": 2500,
        "temperature": 0.0,
        "timeout_sec": 300.0,
        "own_chain": [(EVALUATOR_C_FALLBACK[0], EVALUATOR_C_FALLBACK[1], EVALUATOR_C_FALLBACK_LABEL)],
    },
}

# Shared fallback pool — claimed dynamically across evaluators (same pattern as lease_evaluate.py)
_5D_SHARED_FALLBACK_POOL = [
    ("google",  "gemini-2.5-pro",       "Gemini 2.5 Pro"),
    ("mistral", "mistral-large-latest", "Mistral Large"),
]

# ── Constants ──────────────────────────────────────────────────────────────────

# States Stage 5d never touches — already at top of severity stack or absent
_SKIP_STATES = frozenset({
    "potentially_unenforceable", "missing", "not_applicable", "broken_xref",
})

# Allowed target states per source state. Empty set = reason only, no state change.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "covered":             {"covered_unfavorable"},
    "partial":             {"covered_unfavorable"},
    "covered_unfavorable": set(),   # reason recorded; state unchanged
    "review_needed":       {"covered_unfavorable"},
    "ambiguous":           set(),
}

# Generic / non-specific use phrases that don't justify a use analysis
_GENERIC_PATTERNS = (
    r"^any lawful (purpose|use|retail use|business)\b",
    r"^retail sales?$",
    r"^general retail\b",
    r"^any (retail|commercial|permitted) use\b",
    r"^any legal purpose\b",
)


# ── Gating logic ──────────────────────────────────────────────────────────────

def should_run_use_analysis(permitted_use: str | None) -> bool:
    """Return True iff the permitted_use clause is specific enough to warrant Stage 5d.

    Skips when:
    - permitted_use is absent or blank
    - fewer than 8 substantive words (too generic)
    - matches known generic patterns ("any lawful purpose" etc.)
    """
    if not permitted_use or not permitted_use.strip():
        return False
    cleaned = permitted_use.strip()
    words = [w for w in re.split(r"\s+", cleaned) if len(w) >= 3]
    if len(words) < 8:
        return False
    lower = cleaned.lower()
    for pattern in _GENERIC_PATTERNS:
        if re.match(pattern, lower):
            return False
    return True


# ── Archetype functions (Substeps 2 & 3) ─────────────────────────────────────


def _load_archetypes(path: Path | None = None) -> dict:
    """Load and cache retail_use_archetypes.json. Mirrors lease_knowledge.get_schema()."""
    global _archetypes_cache
    if _archetypes_cache is not None and path is None:
        return _archetypes_cache
    target = path or _ARCHETYPES_PATH
    schema = json.loads(target.read_text(encoding="utf-8"))
    if path is None:
        _archetypes_cache = schema
    logger.info(
        f"[lease_use_aware] Loaded archetype schema v{schema.get('schema_version', '?')} "
        f"({len(schema.get('archetypes', []))} archetypes)"
    )
    return schema


def match_archetypes(permitted_use: str, schema: dict | None = None) -> list[dict]:
    """Match permitted_use against retail_use_archetypes.json.

    Pure pattern matching — no LLM. Mirrors extract_governing_law() in lease_jurisdiction.py.

    Multi-match: all archetypes where any keyword appears in the permitted_use are returned.
    Returns an empty list when no archetype matches or permitted_use is blank.

    Args:
        permitted_use: raw permitted use clause string from extraction
        schema: optional pre-loaded archetype schema (for testing); loads from disk if None
    """
    if not permitted_use or not permitted_use.strip():
        return []
    schema = schema or _load_archetypes()
    text_lower = permitted_use.lower()
    matched = []
    for archetype in schema.get("archetypes", []):
        keywords = archetype.get("match_keywords", [])
        if any(kw.lower() in text_lower for kw in keywords):
            matched.append(archetype)
    logger.info(
        f"[lease_use_aware] Archetype match: {[a.get('archetype_id') for a in matched] or 'none'}"
    )
    return matched


def merge_archetype_results(matched: list[dict]) -> tuple[dict, list[dict]]:
    """Union-merge matched archetype results. Mirrors apply_jurisdiction_rules() pattern.

    For lp_sensitivities: union by lp_id, taking highest severity on conflict.
    For use_context scalar fields: first non-null wins.
    For use_context list fields: union with deduplication.
    Attribution preserved: each merged sensitivity records contributing archetype IDs.

    Args:
        matched: list of archetype dicts from match_archetypes()

    Returns:
        (merged_context, attribution_log)
        merged_context keys:
            archetype_ids         — list of matched archetype IDs
            use_context           — merged use_context dict
            lp_sensitivities      — list of merged sensitivity dicts (sorted by lp_id)
        attribution_log: list of {lp_id, severity, archetypes} for audit trail
    """
    if not matched:
        return {}, []

    merged_lp: dict[str, dict] = {}
    merged_uc: dict = {
        "business_type": None,
        "regulated_activity": None,
        "refrigeration_perishables": None,
        "hazardous_material_sensitivity": "None",
        "hours_access_sensitivity": None,
        "operational_dependencies": [],
        "other_use_risk_factors": [],
    }
    archetype_ids: list[str] = []

    for archetype in matched:
        aid = archetype.get("archetype_id", "")
        archetype_ids.append(aid)

        uc = archetype.get("use_context", {})

        # Scalar fields: first non-null wins
        for field in ("business_type", "regulated_activity", "refrigeration_perishables",
                      "hours_access_sensitivity"):
            if merged_uc[field] is None and uc.get(field):
                merged_uc[field] = uc[field]

        # hazardous_material_sensitivity: take highest severity
        new_hz = uc.get("hazardous_material_sensitivity", "None")
        if _SEVERITY_RANK.get(new_hz, 0) > _SEVERITY_RANK.get(merged_uc["hazardous_material_sensitivity"], 0):
            merged_uc["hazardous_material_sensitivity"] = new_hz

        # List fields: union with deduplication (order-preserving)
        for dep in uc.get("operational_dependencies", []):
            if dep not in merged_uc["operational_dependencies"]:
                merged_uc["operational_dependencies"].append(dep)
        for rf in uc.get("other_use_risk_factors", []):
            if rf not in merged_uc["other_use_risk_factors"]:
                merged_uc["other_use_risk_factors"].append(rf)

        # LP sensitivities: union by lp_id, highest severity wins
        for sens in archetype.get("lp_sensitivities", []):
            lp_id = sens.get("lp_id", "")
            severity = sens.get("severity", "None")
            if lp_id not in merged_lp:
                merged_lp[lp_id] = {
                    "lp_id": lp_id,
                    "severity": severity,
                    "rationale": sens.get("rationale", ""),
                    "source": sens.get("source", ""),
                    "archetypes": [aid],
                }
            else:
                existing = merged_lp[lp_id]
                if _SEVERITY_RANK.get(severity, 0) > _SEVERITY_RANK.get(existing["severity"], 0):
                    existing["severity"] = severity
                    existing["rationale"] = sens.get("rationale", "")
                    existing["source"] = sens.get("source", "")
                if aid not in existing["archetypes"]:
                    existing["archetypes"].append(aid)

    lp_sensitivities = sorted(merged_lp.values(), key=lambda x: x["lp_id"])
    attribution_log = [
        {"lp_id": s["lp_id"], "severity": s["severity"], "archetypes": s["archetypes"]}
        for s in lp_sensitivities
    ]

    merged_context = {
        "archetype_ids": archetype_ids,
        "use_context": merged_uc,
        "lp_sensitivities": lp_sensitivities,
    }
    logger.info(
        f"[lease_use_aware] Archetype merge: {len(lp_sensitivities)} LP sensitivities "
        f"from {len(archetype_ids)} archetype(s)"
    )
    return merged_context, attribution_log


# ── Substep 1: Model inference ────────────────────────────────────────────────

_PROFILE_SYSTEM = """You extract structured use profile information from commercial lease permitted use clauses.
Return a single JSON object with exactly these fields. Infer from the clause text; do not hallucinate.
If a field is not evident from the clause, use null or an empty list.

Fields:
- business_type: short description of the business
- operational_dependencies: list of key operational requirements (max 5)
- refrigeration_perishables: null | "None" | short description of criticality
- regulated_activity: null | description of applicable regulation (DEA, FDA, liquor board, health dept, etc.)
- hazardous_material_sensitivity: "None" | "Low" | "Moderate" | "High"
- hours_access_sensitivity: "Standard" | "Extended" | "24-hour" | description
- other_use_risk_factors: list of other lease-relevant risk factors (max 3)

Return only the JSON object, no markdown, no commentary."""


def _try_model_call(provider: str, model: str, system_prompt: str, user_prompt: str) -> dict:
    """Attempt one model call for Call 1 profile generation.

    Extracted from _call_model_for_profile to allow test mocking of individual
    chain entries without mocking the entire chain-iteration function.

    Returns parsed profile dict on success. Raises on any failure (empty output,
    parse failure, network error, auth error) — caller iterates to next chain entry.
    """
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract

    target = ModelTarget(
        name=f"{provider}:{model}-call1-profile",
        provider=provider,
        model=model,
        max_output_tokens=600,
        temperature=0.0,
        timeout_sec=120.0,
    )
    router = ProviderRouter([target], RouterConfig())
    adapter = router._get_adapter(provider)
    raw = adapter.call(system_prompt, user_prompt, target).strip()

    if not raw:
        raise ValueError("empty_output")

    profile = safe_json_extract(raw)
    if not isinstance(profile, dict):
        raise ValueError(f"response is not a dict (got {type(profile).__name__})")
    return profile


def _call_model_for_profile(permitted_use: str) -> dict | None:
    """Substep 1 — chain-based model inference for Call 1 use profile.

    Step 304a: iterates SINGLE_STAGE_CHAIN (mirrors _call_single_evaluator's pattern).
    Returns parsed profile dict on first successful model call.
    Returns None (chain-exhausted sentinel) only when every chain entry fails.

    Individual model failures are transient (empty_output, parse_failure, timeout,
    auth). The chain exhausts when all 7 models across 4 providers have failed.
    """
    user_prompt = f"Permitted use clause:\n\n{permitted_use.strip()}"
    errors: list[str] = []

    for provider, model in SINGLE_STAGE_CHAIN:
        try:
            profile = _try_model_call(provider, model, _PROFILE_SYSTEM, user_prompt)
            logger.info(
                f"[lease_use_aware] Call 1 succeeded via {model}: "
                f"business_type={profile.get('business_type')}"
            )
            return profile
        except Exception as e:
            errors.append(f"{model}: {e}")
            logger.warning(f"[lease_use_aware] Call 1 {model} ({provider}) failed: {e}")

    logger.warning(
        f"[lease_use_aware] Call 1 chain exhausted ({len(SINGLE_STAGE_CHAIN)} models tried): "
        + "; ".join(errors)
    )
    return None  # chain-exhausted sentinel


# ── Substep 4: Profile-archetype composition ──────────────────────────────────


def compose_profile_with_archetypes(
    text_profile: dict,
    archetype_context: dict,
    archetype_log: list[dict],
    matched: list[dict],
    permitted_use: str = "",
) -> dict:
    """Substep 4 — merge text-inferred profile with archetype context.

    Composition rules (locked, Step 302a):
    - Text wins on conflict: non-empty/non-null/non-"None"/non-[] text field is preserved.
    - Archetype fills gaps: None / "" / "None" / [] text field gets archetype value.
    - Severity bands (hazardous_material_sensitivity) follow scalar text-wins rule.
      No max-of-text-and-archetype — max rule applies only within merge_archetype_results().
    - List fields: text list wins entirely when non-empty; no item-by-item union with text.
    - lp_sensitivities is purely archetype-sourced; added directly from archetype_context.

    Override event: text won AND archetype had a non-empty value → field added to
    fields_overridden_by_text and archetype's value recorded in would_have_contributed.

    Args:
        text_profile: dict from _call_model_for_profile()
        archetype_context: merged context from merge_archetype_results() (may be {})
        archetype_log: attribution log from merge_archetype_results() (may be [])
        matched: raw list of archetype dicts from match_archetypes()
        permitted_use: original clause string (used to compute match_keywords_hit)

    Returns:
        final profile dict with _archetype_metadata block embedded
    """
    uc = archetype_context.get("use_context", {})
    archetype_ids: list[str] = archetype_context.get("archetype_ids", [])
    n_matched = len(matched)

    final: dict = {}
    field_provenance: dict[str, str] = {}
    fields_overridden_by_text: list[str] = []
    would_have_contributed: dict[str, dict] = {}

    def _is_empty(val) -> bool:
        """True iff value is absent / blank / the sentinel "None" / empty list."""
        if val is None:
            return True
        if isinstance(val, str) and val.strip() in ("", "None"):
            return True
        if isinstance(val, list) and len(val) == 0:
            return True
        return False

    def _arch_val(field: str, archetype: dict):
        return archetype.get("use_context", {}).get(field)

    def _provenance_label_gap(contributing_aids: list[str], list_field: bool = False) -> str:
        """Build provenance label string for an archetype-filled gap."""
        if not contributing_aids:
            return "not_available"
        if len(contributing_aids) == 1:
            return f"from_archetype:{contributing_aids[0]}"
        tag = "from_archetypes_union" if list_field else "from_archetypes"
        return f"{tag}:{contributing_aids}"

    # ── Scalar fields (text-wins-on-conflict) ─────────────────────────────────
    SCALAR_FIELDS = [
        "business_type",
        "refrigeration_perishables",
        "regulated_activity",
        "hours_access_sensitivity",
    ]

    for field in SCALAR_FIELDS:
        text_val = text_profile.get(field)
        arch_val = uc.get(field)

        if not _is_empty(text_val):
            final[field] = text_val
            field_provenance[field] = "from_text"
            # Override event: archetype also had a non-empty value
            arch_contributors = {
                a.get("archetype_id"): _arch_val(field, a)
                for a in matched
                if not _is_empty(_arch_val(field, a))
            }
            if arch_contributors:
                fields_overridden_by_text.append(field)
                would_have_contributed[field] = arch_contributors
        else:
            if not _is_empty(arch_val):
                final[field] = arch_val
                contributing_aids = [
                    a.get("archetype_id") for a in matched
                    if not _is_empty(_arch_val(field, a))
                ]
                field_provenance[field] = _provenance_label_gap(contributing_aids)
            else:
                final[field] = None
                field_provenance[field] = "not_available"

    # ── hazardous_material_sensitivity (severity band; scalar text-wins rule) ──
    _HZ = "hazardous_material_sensitivity"
    text_hz = text_profile.get(_HZ) or "None"
    arch_hz = uc.get(_HZ, "None") or "None"

    if not _is_empty(text_hz):
        final[_HZ] = text_hz
        field_provenance[_HZ] = "from_text"
        arch_contributors = {
            a.get("archetype_id"): _arch_val(_HZ, a)
            for a in matched
            if not _is_empty(_arch_val(_HZ, a))
        }
        if arch_contributors:
            fields_overridden_by_text.append(_HZ)
            would_have_contributed[_HZ] = arch_contributors
    else:
        if not _is_empty(arch_hz):
            final[_HZ] = arch_hz
            # List only the archetype(s) that provided the max-severity value
            max_aids = [
                a.get("archetype_id") for a in matched
                if _arch_val(_HZ, a) == arch_hz
            ]
            field_provenance[_HZ] = f"from_archetypes_max:{max_aids}"
        else:
            final[_HZ] = "None"
            field_provenance[_HZ] = "not_available"

    # ── List fields (text wins entirely when non-empty) ────────────────────────
    LIST_FIELDS = ["operational_dependencies", "other_use_risk_factors"]

    for field in LIST_FIELDS:
        text_list = text_profile.get(field) or []
        arch_list = uc.get(field) or []

        if not _is_empty(text_list):
            final[field] = text_list
            field_provenance[field] = "from_text"
            arch_contributors = {
                a.get("archetype_id"): _arch_val(field, a)
                for a in matched
                if not _is_empty(_arch_val(field, a))
            }
            if arch_contributors:
                fields_overridden_by_text.append(field)
                would_have_contributed[field] = arch_contributors
        else:
            if not _is_empty(arch_list):
                final[field] = arch_list
                contributing_aids = [
                    a.get("archetype_id") for a in matched
                    if not _is_empty(_arch_val(field, a))
                ]
                field_provenance[field] = _provenance_label_gap(contributing_aids, list_field=True)
            else:
                final[field] = []
                field_provenance[field] = "not_available"

    # ── lp_sensitivities (purely archetype-sourced) ────────────────────────────
    lp_sensitivities = archetype_context.get("lp_sensitivities", [])
    final["lp_sensitivities"] = lp_sensitivities
    if lp_sensitivities:
        field_provenance["lp_sensitivities"] = (
            f"from_archetype:{archetype_ids[0]}" if n_matched == 1
            else f"from_archetypes:{archetype_ids}"
        )
    else:
        field_provenance["lp_sensitivities"] = "not_available"

    # ── _archetype_metadata block ──────────────────────────────────────────────
    text_lower = permitted_use.lower() if permitted_use else ""
    matched_archetypes_info = [
        {
            "archetype_id": a.get("archetype_id"),
            "match_keywords_hit": [
                kw for kw in a.get("match_keywords", []) if kw.lower() in text_lower
            ],
        }
        for a in matched
    ]

    try:
        schema_ver = _load_archetypes().get("schema_version", "unknown")
    except Exception:
        schema_ver = "unknown"

    final["_archetype_metadata"] = {
        "matched_archetypes": matched_archetypes_info,
        "field_provenance": field_provenance,
        "fields_overridden_by_text": fields_overridden_by_text,
        "would_have_contributed": would_have_contributed,
        "archetype_schema_version": schema_ver,
    }

    # profile_source: "composed" if any archetype matched, else "text_only"
    final["profile_source"] = "composed" if matched else "text_only"

    logger.info(
        f"[lease_use_aware] Composed profile: source={final['profile_source']}, "
        f"{len(fields_overridden_by_text)} text-override(s), "
        f"{sum(1 for v in field_provenance.values() if 'archetype' in v)} archetype-fill(s)"
    )
    return final


# ── Substep 1–4 orchestration ─────────────────────────────────────────────────


def generate_use_profile(permitted_use: str) -> dict | None:
    """Generate a composed use profile from the permitted use clause.

    Orchestration (Step 304a — fallback chain + unconditional archetype match):
      Substep 0 — Archetype match: runs first, independent of model pipeline.
                  Archetype matching is a structural property of the input string;
                  it is not contingent on model availability.
      Substep 1 — Model inference: chain-based via SINGLE_STAGE_CHAIN.
                  Returns None (chain-exhausted) if all models fail.
      Substep 2 — Archetype merge: if ≥1 archetype matched, produce archetype context.
      Substep 3 — Composition: text-wins-on-conflict; archetype fills gaps.

    Three outcomes:
      applied           — Call 1 succeeded (any chain entry). text_inference_status="success".
      applied_archetype_only — Call 1 chain exhausted AND archetype matched.
                               compose_profile_with_archetypes called with {} as text_profile;
                               302a composition logic fills all fields from archetype.
                               text_inference_status="chain_exhausted".
      None (skipped_no_evidence) — Call 1 chain exhausted AND no archetype matched.
                               No Call 2 input available; Stage 5d aborts gracefully.

    Returns:
        dict: profile with text_inference_status in _archetype_metadata.
        None: hard abort when chain exhausted and no archetype matched.
    """
    # Substep 0: Archetype match (unconditional — runs before any model call)
    try:
        matched = match_archetypes(permitted_use)
    except Exception as e:
        logger.warning(f"[lease_use_aware] Archetype match failed (non-fatal): {e}")
        matched = []

    logger.info(
        f"[lease_use_aware] Substep 0 — archetype match: "
        f"{[a.get('archetype_id') for a in matched] or 'none'}"
    )

    # Substep 1: Model inference (chain-based; may return None on exhaustion)
    text_profile = _call_model_for_profile(permitted_use)
    text_inference_status = "success" if text_profile is not None else "chain_exhausted"

    # Chain-exhausted + no archetype → nothing to work with; abort Stage 5d
    if text_profile is None and not matched:
        logger.warning(
            f"[lease_use_aware] Call 1 chain exhausted AND no archetype matched "
            f"for {permitted_use[:80]!r} — Stage 5d aborting (skipped_no_evidence)"
        )
        return None

    # For the archetype-only degrade path, compose with an empty text profile.
    # 302a composition logic already handles this: all fields empty → archetype fills all.
    effective_text_profile = text_profile if text_profile is not None else {}

    if text_profile is None:
        logger.info(
            f"[lease_use_aware] Call 1 chain exhausted — degrading to archetype-only path "
            f"(matched: {[a.get('archetype_id') for a in matched]})"
        )

    # Substep 2: Multi-archetype merge (only if ≥1 matched)
    if matched:
        archetype_context, archetype_log = merge_archetype_results(matched)
    else:
        archetype_context = {}
        archetype_log = []

    # Substep 3: Profile-archetype composition (text-wins-on-conflict)
    profile = compose_profile_with_archetypes(
        effective_text_profile, archetype_context, archetype_log, matched, permitted_use
    )

    # Embed text_inference_status into _archetype_metadata for caller status mapping
    if "_archetype_metadata" not in profile:
        profile["_archetype_metadata"] = {}
    profile["_archetype_metadata"]["text_inference_status"] = text_inference_status

    return profile


# ── Call 2: Three-Evaluator Use-Aware Classification (Step 303) ───────────────

_CLASSIFY_SYSTEM = """You are a commercial real estate attorney assessing whether a tenant's specific business use
creates material legal or operational risk under each lease provision, given the current coverage classification.

CRITICAL DEFAULT: Most provisions are NOT materially affected by the tenant's specific use.
Return "none" for at least 25 of 32 provisions on most leases.
Return a non-none adjustment ONLY when the use creates a *concrete, substantial* change in
the legal or business consequence of the current coverage state — not based on generic claims
that "this type of business needs X." The adjustment must be tied to specific clause language
or missing elements described in the LP data, and specific to the actual use profile.

Do NOT invent use-sensitivity. Do NOT adjust based on speculative or attenuated reasoning.
Returning "none" for 28–32 LPs is the expected and correct outcome on most leases.

Allowed adjustments (v1):
  covered → covered_unfavorable   (provision exists but becomes actively adverse given use)
  partial → covered_unfavorable   (partial provision becomes actively harmful given use)
  covered_unfavorable → covered_unfavorable  (state unchanged; omit or set adjustment="none")

No downgrades. Do not change potentially_unenforceable, missing, or not_applicable items.
Do not invent coverage improvements.

You MUST commit a verdict for every LP — no abstaining at the per-LP level.
If you are uncertain, return "none". Genuine uncertainty is captured by the downstream
consensus governance layer, not by hedging in individual evaluator output.

Return a JSON object with one key per LP, exactly like this example:
{
  "LP-01": {"adjustment": "none"},
  "LP-19": {"adjustment": "covered_unfavorable", "reason": "Specific reason tied to this clause and this use..."},
  "LP-32": {"adjustment": "covered_unfavorable", "reason": "Specific reason..."}
}

Rules for a valid "reason" string:
- Must reference the specific clause deficiency (e.g. "no outage abatement", "no DEA-specific carve-out")
- Must explain why this particular use makes the deficiency materially worse
- Must be 1–3 sentences. No generic boilerplate.
- If adjustment is "none", reason may be omitted.

Return only the JSON object."""


def _build_lp_summary(ca: list) -> str:
    """Serialize CA entries to a compact string for the Call 2 prompt."""
    lines = []
    for a in ca:
        pid = a.get("issue_area_id", "")
        state = a.get("coverage_state", "")
        if state in _SKIP_STATES:
            lines.append(f"{pid}: SKIP (state={state})")
            continue
        name = a.get("issue_area_name", pid)
        found = a.get("elements_found", [])[:3]
        missing = a.get("elements_missing", [])[:3]
        evidence = (a.get("evidence_summary") or "")[:150]
        lines.append(
            f"{pid} [{name}] state={state} | "
            f"found=[{', '.join(found)}] | missing=[{', '.join(missing)}] | evidence: {evidence}"
        )
    return "\n".join(lines)


def _build_lp_sensitivity_section(use_profile: dict) -> str:
    """Format lp_sensitivities from use_profile into a labeled evaluator-context section.

    Returns empty string when lp_sensitivities is absent or empty.
    The section informs evaluators of archetype-sourced LP priors but does NOT
    determine their verdict — each evaluator must still commit per-LP based on
    actual coverage state and clause content.
    """
    lp_sens = use_profile.get("lp_sensitivities", [])
    if not lp_sens:
        return ""
    lines = [
        "ARCHETYPE-FLAGGED LP SENSITIVITIES (declared from authoritative sources;",
        "informs but does not determine your classification — you must still commit",
        "per-LP based on the actual coverage state and clause content):",
        "",
    ]
    for s in lp_sens:
        lp_id = s.get("lp_id", "")
        severity = s.get("severity", "")
        rationale = (s.get("rationale") or "")[:200]
        source = (s.get("source") or "")[:120]
        archetypes = ", ".join(s.get("archetypes", []))
        lines.append(f"  {lp_id}: {severity.upper()} severity (per {archetypes} archetype).")
        if rationale:
            lines.append(f"    Rationale: {rationale}")
        if source:
            lines.append(f"    Source: {source}")
    return "\n".join(lines)


def _call_single_evaluator(
    role: str,
    evaluator_cfg: dict,
    use_profile: dict,
    ca: list,
    cfg: dict,
    claimed_providers: set,
    claimed_lock: threading.Lock,
    pool_claimed: list,
    pool_lock: threading.Lock,
) -> dict:
    """Call one Stage 5d evaluator with own-chain fallback and shared-pool fallback.

    Mirrors lease_evaluate.py's _call_evaluator pattern.

    Returns result dict:
        role, model, provider, label, completed, elapsed_sec,
        lp_output (dict LP→{adjustment,reason} | None), error (str | None)
    """
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract
    from cam.core.provider_health import get_health_tracker

    health = get_health_tracker()
    start_time = time.time()
    errors: list[str] = []

    # Build user prompt (same for all attempts)
    profile_str = json.dumps(use_profile, indent=2)
    lp_summary = _build_lp_summary(ca)
    lp_sens_section = _build_lp_sensitivity_section(use_profile)
    user_prompt = f"USE PROFILE (text-inference + archetype-composed):\n{profile_str}\n\n"
    if lp_sens_section:
        user_prompt += f"{lp_sens_section}\n\n"
    user_prompt += f"LEASE PROVISION COVERAGE (32 LPs):\n{lp_summary}"

    def _try_claim(provider: str) -> bool:
        with claimed_lock:
            if provider in claimed_providers:
                return False
            claimed_providers.add(provider)
            return True

    def _release_claim(provider: str) -> None:
        with claimed_lock:
            claimed_providers.discard(provider)

    def _try_call(provider: str, model: str, label: str) -> dict | None:
        """Attempt one model call. Returns parsed LP dict on success, raises on failure."""
        if not health.is_available(provider):
            raise RuntimeError(f"provider {provider} degraded")
        if not _try_claim(provider):
            raise RuntimeError(f"provider {provider} already claimed")
        print(f"[lease_use_aware] Eval-{role}: calling {model} ({provider})...", flush=True)
        try:
            if provider == "mistral":
                raw = _call_mistral_direct_5d(model, _CLASSIFY_SYSTEM, user_prompt,
                                               evaluator_cfg.get("max_output_tokens", 2500),
                                               evaluator_cfg.get("timeout_sec", 300.0))
            else:
                target = ModelTarget(
                    name=f"{provider}:{model}-use5d-{role}",
                    provider=provider,
                    model=model,
                    max_output_tokens=evaluator_cfg.get("max_output_tokens", 2500),
                    temperature=evaluator_cfg.get("temperature", 0.0),
                    timeout_sec=evaluator_cfg.get("timeout_sec", 300.0),
                )
                router = ProviderRouter([target], RouterConfig())
                adapter = router._get_adapter(provider)
                raw = adapter.call(_CLASSIFY_SYSTEM, user_prompt, target).strip()

            parsed = safe_json_extract(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a dict")
            return parsed
        except Exception:
            _release_claim(provider)
            raise

    # Phase 1: own-provider chain (primary + fallback)
    own_candidates = [(evaluator_cfg["provider"], evaluator_cfg["model"], evaluator_cfg["label"])]
    for entry in evaluator_cfg.get("own_chain", []):
        own_candidates.append(entry)

    for provider, model, label in own_candidates:
        try:
            lp_output = _try_call(provider, model, label)
            elapsed = time.time() - start_time
            logger.info(f"[lease_use_aware] Eval-{role} ({label}) succeeded in {elapsed:.1f}s")
            return {
                "role": role, "model": model, "provider": provider, "label": label,
                "completed": True, "elapsed_sec": round(elapsed, 2),
                "lp_output": lp_output, "error": None,
            }
        except Exception as e:
            errors.append(f"{model}: {e}")
            print(f"[lease_use_aware] Eval-{role}: {model} FAILED: {e}", flush=True)

    # Phase 2: shared fallback pool
    print(f"[lease_use_aware] Eval-{role}: own chain exhausted, trying shared pool", flush=True)
    while True:
        pool_entry = None
        with pool_lock:
            for entry in _5D_SHARED_FALLBACK_POOL:
                if entry[0] not in pool_claimed:
                    pool_claimed.append(entry[0])
                    pool_entry = entry
                    break
        if pool_entry is None:
            break
        provider, model, label = pool_entry
        try:
            lp_output = _try_call(provider, model, label)
            elapsed = time.time() - start_time
            logger.info(f"[lease_use_aware] Eval-{role} ({label}) via pool in {elapsed:.1f}s")
            return {
                "role": role, "model": model, "provider": provider, "label": label,
                "completed": True, "elapsed_sec": round(elapsed, 2),
                "lp_output": lp_output, "error": None,
            }
        except Exception as e:
            errors.append(f"{model}: {e}")
            with pool_lock:
                if provider in pool_claimed:
                    pool_claimed.remove(provider)
            print(f"[lease_use_aware] Eval-{role}: pool {model} FAILED: {e}", flush=True)

    # All paths exhausted
    elapsed = time.time() - start_time
    error_summary = "; ".join(errors)
    logger.warning(f"[lease_use_aware] Eval-{role} failed all candidates: {error_summary}")
    return {
        "role": role,
        "model": evaluator_cfg["model"], "provider": evaluator_cfg["provider"],
        "label": evaluator_cfg["label"],
        "completed": False, "elapsed_sec": round(elapsed, 2),
        "lp_output": None, "error": error_summary,
    }


def _call_mistral_direct_5d(
    model_name: str, system_prompt: str, user_prompt: str,
    max_output_tokens: int, timeout_sec: float,
) -> str:
    """Call Mistral via OpenAI-compatible API (mirrors lease_evaluate._call_mistral_direct)."""
    from cam.core.provider_router import ProviderError
    from openai import OpenAI
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ProviderError("MISTRAL_API_KEY not set")
    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1", timeout=timeout_sec)
    resp = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0.0, max_tokens=max_output_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def _run_three_evaluators(
    use_profile: dict,
    ca: list,
    cfg: dict,
) -> dict[str, dict]:
    """Run three Stage 5d evaluators in parallel (mirrors lease_evaluate.evaluate_provisions).

    Returns dict keyed by role ("A", "B", "C"), each value is the result dict from
    _call_single_evaluator: {role, model, provider, label, completed, elapsed_sec,
    lp_output, error}.
    """
    claimed_providers: set = set()
    claimed_lock = threading.Lock()
    pool_claimed: list = []
    pool_lock = threading.Lock()

    results: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                _call_single_evaluator,
                role, cfg_ev, use_profile, ca, cfg,
                claimed_providers, claimed_lock, pool_claimed, pool_lock,
            ): role
            for role, cfg_ev in EVALUATOR_LINEUP.items()
        }
        for future in as_completed(futures):
            role = futures[future]
            try:
                results[role] = future.result()
            except Exception as e:
                results[role] = {
                    "role": role, "model": EVALUATOR_LINEUP[role]["model"],
                    "provider": EVALUATOR_LINEUP[role]["provider"],
                    "label": EVALUATOR_LINEUP[role]["label"],
                    "completed": False, "elapsed_sec": 0.0,
                    "lp_output": None, "error": str(e),
                }

    succeeded = sum(1 for r in results.values() if r["completed"])
    logger.info(f"[lease_use_aware] Three-evaluator run: {succeeded}/3 completed")
    return results


def _merge_evaluator_verdicts(
    evaluator_results: dict[str, dict],
    coverage_assessment: list,
) -> tuple[list, dict]:
    """Deterministic merge of three-evaluator verdicts per LP. No model calls.

    For each LP any evaluator flagged, determines one of four outcomes:
      assert_strong — all active evaluators agree on same target_state
      assert_weak   — 2 of N active evaluators agree on same target_state
      abstain       — no 2-of-N agreement; do not modify CA entry
      rejected      — 0 evaluators flagged (implicit; not in per_lp_records)

    Returns (updated_coverage_assessment, governance_record).
    """
    ca_by_pid = {a["issue_area_id"]: a for a in coverage_assessment}
    active_roles = [r for r, res in evaluator_results.items() if res.get("completed")]
    n_active = len(active_roles)

    # Thresholds: strong = all active agree; weak = majority (≥2, or all if n_active<3)
    strong_threshold = n_active
    weak_threshold = 2 if n_active >= 2 else n_active

    # Collect all LPs flagged by any evaluator (adj != "none" AND valid transition)
    flagged_lps: dict[str, dict[str, dict]] = {}   # lp_id → {role → {adj, reason}}
    for role in active_roles:
        lp_output = evaluator_results[role].get("lp_output") or {}
        for pid, entry in lp_output.items():
            if not isinstance(entry, dict):
                continue
            adj = (entry.get("adjustment") or "none").strip()
            if adj == "none":
                continue
            assessment = ca_by_pid.get(pid)
            if not assessment:
                continue
            current_state = assessment.get("coverage_state", "")
            if current_state in _SKIP_STATES:
                continue
            allowed = _ALLOWED_TRANSITIONS.get(current_state, set())
            if adj not in allowed and adj != "none":
                # If evaluator proposed an invalid transition, treat as no_change
                continue
            if pid not in flagged_lps:
                flagged_lps[pid] = {}
            reason = (entry.get("reason") or "").strip()
            flagged_lps[pid][role] = {"to_state": adj, "reason": reason}

    per_lp_records: dict = {}
    disagreements: list = []
    n_assert_strong = 0
    n_assert_weak = 0
    n_abstained = 0

    for pid, role_verdicts in flagged_lps.items():
        assessment = ca_by_pid[pid]
        current_state = assessment.get("coverage_state", "")

        # Build per-evaluator verdict records
        evaluator_verdicts: dict = {}
        for role in ["A", "B", "C"]:
            if role in role_verdicts:
                v = role_verdicts[role]
                evaluator_verdicts[role] = {
                    "verdict": "escalate",
                    "to_state": v["to_state"],
                    "reason": v["reason"],
                }
            elif evaluator_results.get(role, {}).get("completed"):
                evaluator_verdicts[role] = {"verdict": "no_change"}
            else:
                evaluator_verdicts[role] = {"verdict": "unavailable"}

        # Tally target_state votes among active roles that escalated
        target_votes: dict[str, list[str]] = {}  # target_state → [roles that agree]
        for role in active_roles:
            if role in role_verdicts:
                ts = role_verdicts[role]["to_state"]
                target_votes.setdefault(ts, []).append(role)

        # Find best agreement
        best_ts = None
        best_roles: list[str] = []
        for ts, roles in target_votes.items():
            if len(roles) > len(best_roles):
                best_ts = ts
                best_roles = roles

        n_agree = len(best_roles)
        consensus_label = f"{n_agree}_of_{n_active}"

        if n_agree >= strong_threshold and n_agree >= 3:
            outcome = "assert_strong"
        elif n_agree >= strong_threshold and n_active < 3:
            # All active (degraded) agree → record as strong
            outcome = "assert_strong"
            consensus_label = f"{n_agree}_of_{n_active}"
        elif n_agree >= weak_threshold and n_agree >= 2:
            outcome = "assert_weak"
        else:
            outcome = "abstain"

        applied = outcome in ("assert_strong", "assert_weak")

        if applied and best_ts:
            # Select best reason: longest among agreeing evaluators that has clause reference
            agreeing_reasons = [
                role_verdicts[r]["reason"] for r in best_roles
                if role_verdicts[r].get("reason")
            ]
            best_reason = max(agreeing_reasons, key=len) if agreeing_reasons else ""

            assessment["coverage_state"] = best_ts
            assessment["use_adjusted"] = True
            assessment["use_adjustment_reason"] = best_reason
            assessment["use_aware_consensus"] = consensus_label
            if best_ts == "covered_unfavorable" and not assessment.get("covered_unfavorable_adverse_to"):
                assessment["covered_unfavorable_adverse_to"] = "tenant"

            if outcome == "assert_strong":
                n_assert_strong += 1
            else:
                n_assert_weak += 1

            logger.info(f"[lease_use_aware] {pid}: {outcome} ({consensus_label}) → {best_ts}")
        else:
            # Abstain — preserve CA entry unchanged, set governance flags
            assessment["use_aware_consensus"] = consensus_label
            assessment["use_aware_abstained"] = True
            n_abstained += 1
            disagreement_record = {
                "lp_id": pid,
                "summary": (
                    f"Evaluator(s) {list(role_verdicts.keys())} flagged use-driven exposure; "
                    f"no {weak_threshold}-of-{n_active} consensus reached"
                ),
                "evaluator_views": [
                    {
                        "role": r,
                        "model": evaluator_results[r]["model"],
                        **evaluator_verdicts[r],
                    }
                    for r in ["A", "B", "C"] if r in evaluator_verdicts
                ],
            }
            disagreements.append(disagreement_record)
            logger.info(f"[lease_use_aware] {pid}: abstain ({consensus_label}) — no consensus")

        per_lp_records[pid] = {
            "evaluator_verdicts": evaluator_verdicts,
            "merge_decision": outcome,
            "consensus": consensus_label,
            "applied_to_ca": applied,
        }

    n_total = len(coverage_assessment)
    n_rejected = n_total - n_assert_strong - n_assert_weak - n_abstained

    # Step 372b: stage-level fallback visibility (admin observability; metadata only).
    # The merged governance output records no per-LP model identity; this flags whether
    # any evaluator answered with a non-primary (fallback) model for this stage.
    _stage5d_fallbacks = [
        {"role": r, "model": evaluator_results[r].get("model"), "label": evaluator_results[r].get("label")}
        for r in ["A", "B", "C"]
        if evaluator_results[r].get("model")
        and evaluator_results[r].get("model") != EVALUATOR_LINEUP.get(r, {}).get("model")
    ]

    governance_record = {
        "status": "applied",
        "fallback_used": bool(_stage5d_fallbacks),   # Step 372b
        "fallbacks": _stage5d_fallbacks or None,      # Step 372b
        "evaluators": [
            {
                "role": r,
                "model": evaluator_results[r]["model"],
                "provider": evaluator_results[r]["provider"],
                "label": evaluator_results[r]["label"],
                "completed": evaluator_results[r]["completed"],
                "elapsed_sec": evaluator_results[r]["elapsed_sec"],
            }
            for r in ["A", "B", "C"]
        ],
        "per_lp_records": per_lp_records,
        "disagreements": disagreements,
        "summary": {
            "lps_evaluated": n_total,
            "asserted_strong": n_assert_strong,
            "asserted_weak": n_assert_weak,
            "abstained": n_abstained,
            "rejected": n_rejected,
        },
    }

    logger.info(
        f"[lease_use_aware] Merge complete: "
        f"strong={n_assert_strong}, weak={n_assert_weak}, "
        f"abstained={n_abstained}, rejected={n_rejected}"
    )
    return coverage_assessment, governance_record


def assess_use_aware_coverage(
    use_profile: dict,
    coverage_assessment: list,
    cfg: dict | None = None,
) -> tuple[list, dict]:
    """Call 2 — three-evaluator use-aware coverage classification (Step 303).

    Runs three independent evaluators in parallel, then merges verdicts with
    structured abstention. Mirrors lease_evaluate.py's parallel-evaluator pattern.

    Returns:
        (updated_coverage_assessment, governance_record)
        governance_record: dict written to pipeline_results["use_aware_governance"]
    """
    cfg = cfg or {}

    # Run three evaluators in parallel
    evaluator_results = _run_three_evaluators(use_profile, coverage_assessment, cfg)

    succeeded = sum(1 for r in evaluator_results.values() if r["completed"])
    if succeeded == 0:
        logger.warning("[lease_use_aware] All three evaluators failed — skipping Stage 5d")
        return coverage_assessment, {
            "status": "skipped_all_evaluators_failed",
            "fallback_used": False,   # Step 372b: all failed → no model answered
            "fallbacks": None,        # Step 372b
            "evaluators": [
                {"role": r, **{k: evaluator_results[r][k]
                               for k in ("model", "provider", "label", "completed", "elapsed_sec")}}
                for r in ["A", "B", "C"]
            ],
            "per_lp_records": {},
            "disagreements": [],
            "summary": {"lps_evaluated": len(coverage_assessment),
                        "asserted_strong": 0, "asserted_weak": 0,
                        "abstained": 0, "rejected": len(coverage_assessment)},
        }

    if succeeded < 3:
        logger.warning(f"[lease_use_aware] Degraded mode: {succeeded}/3 evaluators completed")

    # Deterministic merge
    coverage_assessment, governance_record = _merge_evaluator_verdicts(
        evaluator_results, coverage_assessment
    )
    return coverage_assessment, governance_record


# ── Step 302 / 302a Validation Tests (no API calls) ──────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING)  # suppress INFO noise during tests

    failures: list[str] = []

    def _fail(label: str, detail: str) -> None:
        msg = f"FAIL [{label}]: {detail}"
        failures.append(msg)
        print(msg)

    def _pass(label: str) -> None:
        print(f"PASS [{label}]")

    # ════════════════════════════════════════════════════════════════════════════
    # T1–T6c: Step 302 regression — match_archetypes() and merge_archetype_results()
    # These tests exercise the archetype functions only (no model calls).
    # ════════════════════════════════════════════════════════════════════════════

    # ── T1: Pharmacy keyword match ────────────────────────────────────────────
    use1 = "licensed pharmacy dispensing prescription medications and compounding services"
    m1 = match_archetypes(use1)
    ids1 = [a.get("archetype_id") for a in m1]
    if "pharmacy" in ids1:
        _pass("T1: pharmacy keyword match")
    else:
        _fail("T1: pharmacy keyword match", f"expected pharmacy in {ids1}")

    # ── T2: Coffee shop / food service match ──────────────────────────────────
    use2 = "coffee shop, café and prepared food service operation"
    m2 = match_archetypes(use2)
    ids2 = [a.get("archetype_id") for a in m2]
    if "coffee_shop_food_service" in ids2:
        _pass("T2: coffee_shop_food_service keyword match")
    else:
        _fail("T2: coffee_shop_food_service keyword match", f"expected coffee_shop_food_service in {ids2}")

    # ── T3: General retail match ──────────────────────────────────────────────
    use3 = "specialty retail clothing and accessories boutique"
    m3 = match_archetypes(use3)
    ids3 = [a.get("archetype_id") for a in m3]
    if "general_retail" in ids3:
        _pass("T3: general_retail keyword match")
    else:
        _fail("T3: general_retail keyword match", f"expected general_retail in {ids3}")

    # ── T4: Multi-match — pharmacy + coffee_shop_food_service ─────────────────
    use4 = "retail pharmacy with food service café and espresso bar"
    m4 = match_archetypes(use4)
    ids4 = [a.get("archetype_id") for a in m4]
    if "pharmacy" in ids4 and "coffee_shop_food_service" in ids4:
        _pass("T4: multi-match pharmacy + coffee_shop_food_service")
    else:
        _fail("T4: multi-match", f"expected both pharmacy and coffee_shop_food_service in {ids4}")

    # ── T5: No-match ──────────────────────────────────────────────────────────
    use5 = "nail salon, manicure and pedicure spa services with waxing and beauty treatments"
    m5 = match_archetypes(use5)
    ids5 = [a.get("archetype_id") for a in m5]
    if len(m5) == 0:
        _pass("T5: no-match for non-archetype use clause")
    else:
        _fail("T5: no-match", f"expected empty list, got {ids5}")

    if match_archetypes("") == []:
        _pass("T5b: empty permitted_use returns []")
    else:
        _fail("T5b: empty permitted_use", "expected []")

    # ── T6: Union merge — multi-match attribution and highest-severity rule ────
    merged6, log6 = merge_archetype_results(m4)  # m4 = pharmacy + coffee_shop_food_service
    lp_by_id6 = {s["lp_id"]: s for s in merged6.get("lp_sensitivities", [])}

    lp32 = lp_by_id6.get("LP-32")
    if lp32 is None:
        _fail("T6a: LP-32 in merged sensitivities", "LP-32 not found in merged result")
    elif lp32["severity"] != "Moderate":
        _fail("T6a: LP-32 severity union", f"expected Moderate (pharmacy wins), got {lp32['severity']}")
    elif "pharmacy" not in lp32.get("archetypes", []):
        _fail("T6a: LP-32 attribution", f"pharmacy not in archetypes: {lp32.get('archetypes')}")
    else:
        _pass("T6a: LP-32 union — Moderate (pharmacy) beats Low (food service), attribution preserved")

    lp19 = lp_by_id6.get("LP-19")
    if lp19 is None:
        _fail("T6b: LP-19 in merged sensitivities", "LP-19 not found in merged result")
    elif lp19["severity"] != "High":
        _fail("T6b: LP-19 severity", f"expected High, got {lp19['severity']}")
    elif not ({"pharmacy", "coffee_shop_food_service"} <= set(lp19.get("archetypes", []))):
        _fail("T6b: LP-19 attribution both archetypes", f"got {lp19.get('archetypes')}")
    else:
        _pass("T6b: LP-19 union — High from both archetypes, both attributed")

    log_ok = all(
        "lp_id" in e and "severity" in e and isinstance(e.get("archetypes"), list)
        for e in log6
    )
    if log_ok:
        _pass("T6c: attribution_log structure valid")
    else:
        _fail("T6c: attribution_log structure", f"malformed entries in {log6}")

    # ════════════════════════════════════════════════════════════════════════════
    # T7–T10: Step 302a — compose_profile_with_archetypes() with mocked model output
    # _call_model_for_profile is monkey-patched at module scope for each test.
    # ════════════════════════════════════════════════════════════════════════════

    _saved_call_model = _call_model_for_profile  # noqa: F821 (defined at module scope)

    # ── T7: Text-wins-on-conflict (mandatory) ─────────────────────────────────
    # pharmacy archetype matches. Model returns partial profile:
    #   - business_type, regulated_activity, hazardous_material_sensitivity,
    #     hours_access_sensitivity, operational_dependencies: non-empty (text wins)
    #   - refrigeration_perishables: None (archetype fills)
    #   - other_use_risk_factors: [] (archetype fills)
    # Pharmacy archetype has Moderate for hazmat; text says Low → text wins.
    _T7_MODEL_OUT = {
        "business_type": "Retail pharmacy with limited OTC inventory",
        "operational_dependencies": ["pharmacist on premises"],
        "refrigeration_perishables": None,
        "regulated_activity": "State pharmacy board licensing",
        "hazardous_material_sensitivity": "Low",
        "hours_access_sensitivity": "Standard",
        "other_use_risk_factors": [],
    }
    _call_model_for_profile = lambda _u: _T7_MODEL_OUT  # noqa: E731

    use_t7 = "pharmacy operating with non-refrigerated OTC products only, no biologics or insulin"
    prof7 = generate_use_profile(use_t7)
    _call_model_for_profile = _saved_call_model  # restore immediately

    if prof7 is None:
        _fail("T7: profile returned None", "generate_use_profile returned None")
    else:
        meta7 = prof7.get("_archetype_metadata", {})
        prov7 = meta7.get("field_provenance", {})
        override7 = meta7.get("fields_overridden_by_text", [])
        whc7 = meta7.get("would_have_contributed", {})

        if prof7.get("business_type") != "Retail pharmacy with limited OTC inventory":
            _fail("T7a: business_type text wins",
                  f"got {prof7.get('business_type')!r}")
        else:
            _pass("T7a: business_type — text wins over archetype")

        if prof7.get("hazardous_material_sensitivity") != "Low":
            _fail("T7b: hazmat text wins (Low beats archetype Moderate)",
                  f"got {prof7.get('hazardous_material_sensitivity')!r}")
        else:
            _pass("T7b: hazardous_material_sensitivity — text Low wins over archetype Moderate")

        if "hazardous_material_sensitivity" not in override7:
            _fail("T7c: hazmat in fields_overridden_by_text", f"override list: {override7}")
        else:
            _pass("T7c: hazardous_material_sensitivity in fields_overridden_by_text")

        arch_hz7 = whc7.get("hazardous_material_sensitivity", {})
        if arch_hz7.get("pharmacy") != "Moderate":
            _fail("T7d: would_have_contributed records pharmacy Moderate",
                  f"got {arch_hz7}")
        else:
            _pass("T7d: would_have_contributed['hazardous_material_sensitivity']['pharmacy'] == 'Moderate'")

        refrig7 = prof7.get("refrigeration_perichables") or prof7.get("refrigeration_perishables")
        if refrig7 is None:
            _fail("T7e: refrigeration_perishables filled from archetype", "still None")
        else:
            _pass(f"T7e: refrigeration_perishables filled from archetype ({refrig7!r})")

        if "refrigeration_perishables" not in override7:
            _pass("T7f: refrigeration_perishables NOT in fields_overridden_by_text (archetype filled gap)")
        else:
            _fail("T7f: refrigeration_perishables should not be an override (text was None)",
                  f"override list: {override7}")

        lp_sens7 = prof7.get("lp_sensitivities", [])
        if len(lp_sens7) > 0:
            _pass(f"T7g: lp_sensitivities populated from pharmacy archetype ({len(lp_sens7)} entries)")
        else:
            _fail("T7g: lp_sensitivities should be populated from pharmacy archetype", "empty")

        matched_arches7 = meta7.get("matched_archetypes", [])
        if any(a.get("archetype_id") == "pharmacy" for a in matched_arches7):
            _pass("T7h: _archetype_metadata.matched_archetypes includes pharmacy")
        else:
            _fail("T7h: matched_archetypes missing pharmacy", f"{matched_arches7}")

        if prof7.get("profile_source") == "composed":
            _pass("T7i: profile_source == 'composed'")
        else:
            _fail("T7i: profile_source", f"expected 'composed', got {prof7.get('profile_source')!r}")

    # ── T8: Composition with no archetype match ───────────────────────────────
    _T8_MODEL_OUT = {
        "business_type": "nail salon and day spa",
        "operational_dependencies": ["licensed nail technicians", "ventilation for acetone fumes"],
        "refrigeration_perishables": None,
        "regulated_activity": "State cosmetology board license",
        "hazardous_material_sensitivity": "Low",
        "hours_access_sensitivity": "Standard",
        "other_use_risk_factors": ["chemical disposal for acetone and acrylic products"],
    }
    _call_model_for_profile = lambda _u: _T8_MODEL_OUT  # noqa: E731

    use_t8 = "nail salon, manicure and pedicure spa services with waxing and beauty treatments"
    prof8 = generate_use_profile(use_t8)
    _call_model_for_profile = _saved_call_model

    if prof8 is None:
        _fail("T8: profile returned None", "generate_use_profile returned None")
    else:
        meta8 = prof8.get("_archetype_metadata", {})
        prov8 = meta8.get("field_provenance", {})
        override8 = meta8.get("fields_overridden_by_text", [])
        whc8 = meta8.get("would_have_contributed", {})

        if meta8.get("matched_archetypes") != []:
            _fail("T8a: matched_archetypes is []", f"got {meta8.get('matched_archetypes')}")
        else:
            _pass("T8a: matched_archetypes == [] (no archetype match)")

        from_text_fields8 = [f for f, p in prov8.items() if p == "from_text"]
        non_text_prov8 = {f: p for f, p in prov8.items()
                         if p not in ("from_text", "not_available")
                         and "lp_sensitivities" not in f}
        if non_text_prov8:
            _fail("T8b: all non-lp fields from_text", f"archetype-sourced: {non_text_prov8}")
        else:
            _pass("T8b: all profile fields from_text (no archetype match)")

        if prof8.get("lp_sensitivities") == []:
            _pass("T8c: lp_sensitivities is [] (no archetype)")
        else:
            _fail("T8c: lp_sensitivities should be []", f"got {prof8.get('lp_sensitivities')}")

        if override8 == [] and whc8 == {}:
            _pass("T8d: no override events, would_have_contributed empty")
        else:
            _fail("T8d: no overrides expected", f"override={override8}, whc={whc8}")

        if prof8.get("profile_source") == "text_only":
            _pass("T8e: profile_source == 'text_only'")
        else:
            _fail("T8e: profile_source", f"expected 'text_only', got {prof8.get('profile_source')!r}")

    # ── T9: Single archetype match, model returns partial profile ─────────────
    # Fields non-empty in model: business_type, regulated_activity
    # Fields empty in model: refrigeration_perishables, hazardous_material_sensitivity,
    #                         hours_access_sensitivity, operational_dependencies,
    #                         other_use_risk_factors
    # Only fields where BOTH text and archetype had values → override events.
    # business_type: text non-empty, pharmacy archetype non-empty → override
    # regulated_activity: text non-empty, pharmacy archetype non-empty → override
    # refrigeration_perishables: text empty → archetype fills → NOT override
    _T9_MODEL_OUT = {
        "business_type": "specialty compounding pharmacy",
        "operational_dependencies": [],
        "refrigeration_perishables": None,
        "regulated_activity": "DEA Schedule II registration required",
        "hazardous_material_sensitivity": "None",
        "hours_access_sensitivity": None,
        "other_use_risk_factors": [],
    }
    _call_model_for_profile = lambda _u: _T9_MODEL_OUT  # noqa: E731

    use_t9 = "licensed pharmacy dispensing prescription medications and compounding services"
    prof9 = generate_use_profile(use_t9)
    _call_model_for_profile = _saved_call_model

    if prof9 is None:
        _fail("T9: profile returned None", "")
    else:
        meta9 = prof9.get("_archetype_metadata", {})
        override9 = meta9.get("fields_overridden_by_text", [])
        prov9 = meta9.get("field_provenance", {})

        # business_type: text non-empty, archetype non-empty → override event
        if "business_type" in override9:
            _pass("T9a: business_type in fields_overridden_by_text (text won, archetype had value)")
        else:
            _fail("T9a: business_type override event", f"override list: {override9}")

        # regulated_activity: text non-empty, archetype non-empty → override event
        if "regulated_activity" in override9:
            _pass("T9b: regulated_activity in fields_overridden_by_text")
        else:
            _fail("T9b: regulated_activity override event", f"override list: {override9}")

        # refrigeration_perishables: text empty → archetype fills → NOT override
        if "refrigeration_perishables" not in override9:
            _pass("T9c: refrigeration_perishables NOT in overrides (archetype filled gap)")
        else:
            _fail("T9c: refrigeration_perishables should not be override (text was None)", "")

        # refrigeration_perishables provenance should be from_archetype
        prov_refrig9 = prov9.get("refrigeration_perishables", "")
        if "archetype" in prov_refrig9:
            _pass(f"T9d: refrigeration_perishables provenance = {prov_refrig9!r}")
        else:
            _fail("T9d: refrigeration_perishables provenance not from archetype",
                  f"got {prov_refrig9!r}")

    # ── T10: Multi-archetype match, model returns fully empty/None profile ─────
    # Both pharmacy and coffee_shop_food_service match.
    # All fields None/empty from model → archetype fills everything.
    # lp_sensitivities must reflect union from both archetypes (regresses T6).
    _T10_MODEL_OUT = {
        "business_type": None,
        "operational_dependencies": [],
        "refrigeration_perishables": None,
        "regulated_activity": None,
        "hazardous_material_sensitivity": "None",
        "hours_access_sensitivity": None,
        "other_use_risk_factors": [],
    }
    _call_model_for_profile = lambda _u: _T10_MODEL_OUT  # noqa: E731

    use_t10 = "retail pharmacy with food service café and espresso bar"
    prof10 = generate_use_profile(use_t10)
    _call_model_for_profile = _saved_call_model

    if prof10 is None:
        _fail("T10: profile returned None", "")
    else:
        meta10 = prof10.get("_archetype_metadata", {})
        prov10 = meta10.get("field_provenance", {})
        override10 = meta10.get("fields_overridden_by_text", [])

        # No override events — all text fields were empty
        if override10 == []:
            _pass("T10a: no override events (all model fields empty)")
        else:
            _fail("T10a: expected no overrides", f"override list: {override10}")

        # All non-lp provenance from archetype
        non_arch_prov10 = {
            f: p for f, p in prov10.items()
            if "from_text" in p and f != "lp_sensitivities"
        }
        if not non_arch_prov10:
            _pass("T10b: all profile fields filled from archetypes")
        else:
            _fail("T10b: unexpected from_text fields when model returned empty",
                  f"{non_arch_prov10}")

        # lp_sensitivities union from both archetypes (regression against T6)
        lp_by_id10 = {s["lp_id"]: s for s in prof10.get("lp_sensitivities", [])}
        lp19_10 = lp_by_id10.get("LP-19")
        lp32_10 = lp_by_id10.get("LP-32")

        if lp19_10 and lp19_10.get("severity") == "High":
            _pass("T10c: LP-19 High in composed profile from multi-archetype union")
        else:
            _fail("T10c: LP-19 High expected in lp_sensitivities",
                  f"got {lp19_10}")

        if lp32_10 and lp32_10.get("severity") == "Moderate":
            _pass("T10d: LP-32 Moderate (pharmacy wins over food service Low)")
        else:
            _fail("T10d: LP-32 Moderate expected",
                  f"got {lp32_10}")

        matched10 = meta10.get("matched_archetypes", [])
        matched_ids10 = [a.get("archetype_id") for a in matched10]
        if "pharmacy" in matched_ids10 and "coffee_shop_food_service" in matched_ids10:
            _pass("T10e: matched_archetypes records both pharmacy and coffee_shop_food_service")
        else:
            _fail("T10e: matched_archetypes missing expected archetypes", f"{matched_ids10}")

        if prof10.get("profile_source") == "composed":
            _pass("T10f: profile_source == 'composed'")
        else:
            _fail("T10f: profile_source", f"expected 'composed', got {prof10.get('profile_source')!r}")

    # ════════════════════════════════════════════════════════════════════════════
    # T11–T13: Step 304a — generate_use_profile() fallback chain + degrade path
    # _try_model_call is monkey-patched at module scope for each test.
    # These tests exercise generate_use_profile() without any real API calls.
    # ════════════════════════════════════════════════════════════════════════════

    _saved_try_model_call = _try_model_call  # noqa: F821

    # ── T11: Q1 single-failure — first chain entry fails, fallback succeeds ───
    # Simulates: gpt-5.5 returns empty_output; fallback model succeeds.
    # Expected: generate_use_profile returns applied profile, text_inference_status="success"
    _t11_calls = [0]
    _T11_MOCK_PROFILE = {
        "business_type": "retail pharmacy (fallback model)",
        "operational_dependencies": ["pharmacist on premises"],
        "refrigeration_perishables": None,
        "regulated_activity": "DEA registration",
        "hazardous_material_sensitivity": "Low",
        "hours_access_sensitivity": "Standard",
        "other_use_risk_factors": [],
    }

    def _mock_try_t11(provider, model, system_prompt, user_prompt):
        _t11_calls[0] += 1
        if _t11_calls[0] == 1:
            raise ValueError("empty_output")  # first chain entry fails
        return dict(_T11_MOCK_PROFILE)  # fallback succeeds

    globals()["_try_model_call"] = _mock_try_t11
    use_t11 = "licensed pharmacy dispensing prescription medications and compounding sterile injectables"
    prof11 = generate_use_profile(use_t11)
    globals()["_try_model_call"] = _saved_try_model_call

    if prof11 is None:
        _fail("T11: Q1 single-failure", "generate_use_profile returned None; fallback did not engage")
    elif prof11.get("_archetype_metadata", {}).get("text_inference_status") != "success":
        _fail("T11a: text_inference_status", f"expected 'success', got {prof11.get('_archetype_metadata', {}).get('text_inference_status')!r}")
    elif prof11.get("business_type") != "retail pharmacy (fallback model)":
        _fail("T11b: text wins (fallback model output)", f"got {prof11.get('business_type')!r}")
    elif _t11_calls[0] < 2:
        _fail("T11c: chain iterated", f"_try_model_call called {_t11_calls[0]}× (expected ≥2)")
    else:
        _pass("T11: Q1 single-failure — first chain entry failed, fallback engaged, profile='applied'")

    # ── T12: Q2 chain-exhaustion with archetype match — degrade-to-archetype-only ──
    # Simulates: all chain entries fail; pharmacy archetype matches.
    # Expected: applied_archetype_only path; all fields from_archetype; lp_sensitivities populated.
    def _mock_try_t12_always_fail(provider, model, system_prompt, user_prompt):
        raise ValueError("empty_output")

    globals()["_try_model_call"] = _mock_try_t12_always_fail
    use_t12 = "retail pharmacy with food service café and espresso bar"  # matches pharmacy + food service + general_retail
    prof12 = generate_use_profile(use_t12)
    globals()["_try_model_call"] = _saved_try_model_call

    if prof12 is None:
        _fail("T12: Q2 chain-exhaustion+archetype", "returned None; expected archetype-only profile")
    else:
        meta12 = prof12.get("_archetype_metadata", {})
        prov12 = meta12.get("field_provenance", {})

        if meta12.get("text_inference_status") != "chain_exhausted":
            _fail("T12a: text_inference_status", f"expected 'chain_exhausted', got {meta12.get('text_inference_status')!r}")
        else:
            _pass("T12a: text_inference_status == 'chain_exhausted'")

        # All non-lp fields should be from_archetype (no from_text since text was empty)
        text_fields12 = [f for f, p in prov12.items() if p == "from_text"]
        if text_fields12:
            _fail("T12b: no from_text provenance", f"unexpected from_text fields: {text_fields12}")
        else:
            _pass("T12b: no from_text fields (all archetype-filled)")

        if meta12.get("fields_overridden_by_text"):
            _fail("T12c: fields_overridden_by_text empty", f"got {meta12.get('fields_overridden_by_text')}")
        else:
            _pass("T12c: fields_overridden_by_text is empty")

        lp_sens12 = prof12.get("lp_sensitivities", [])
        if len(lp_sens12) > 0:
            _pass(f"T12d: lp_sensitivities populated ({len(lp_sens12)} entries from archetype(s))")
        else:
            _fail("T12d: lp_sensitivities empty", "expected archetype-sourced LP sensitivities")

        matched12 = meta12.get("matched_archetypes", [])
        if any(a.get("archetype_id") == "pharmacy" for a in matched12):
            _pass("T12e: pharmacy archetype recorded in matched_archetypes")
        else:
            _fail("T12e: pharmacy in matched_archetypes", f"got {[a.get('archetype_id') for a in matched12]}")

    # ── T13: skip-no-evidence — chain exhausted, no archetype matches ─────────
    # Simulates: all chain entries fail; use clause matches no archetype.
    # Expected: None returned (Stage 5d aborts, caller sets skipped_no_evidence).
    def _mock_try_t13_always_fail(provider, model, system_prompt, user_prompt):
        raise ValueError("empty_output")

    globals()["_try_model_call"] = _mock_try_t13_always_fail
    # Tattoo studio — passes should_run_use_analysis (≥8 words, not generic)
    # but matches no archetype keywords (not pharmacy, not food service, not retail/boutique/etc.)
    use_t13 = "tattoo studio and body piercing services with custom artwork design consultation"
    prof13 = generate_use_profile(use_t13)
    globals()["_try_model_call"] = _saved_try_model_call

    if prof13 is not None:
        _fail("T13: skip-no-evidence", f"expected None, got profile with source={prof13.get('profile_source')!r}")
    else:
        _pass("T13: skip-no-evidence — chain exhausted + no archetype match => None (Stage 5d aborts)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if failures:
        print(f"FAILED — {len(failures)} test(s) failed")
        sys.exit(1)
    else:
        print("All Step 302 / 302a / 304a validation tests PASSED")
