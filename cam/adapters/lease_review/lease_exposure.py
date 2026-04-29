"""
CAM Lease Review — Exposure Engine (Step 243)

Turns already-determined coverage state + missing elements into a concise,
attorney-readable exposure statement per issue area.

This module is a TRANSLATOR, not a reasoner.
  - It does NOT decide coverage state
  - It does NOT decide missingness
  - It does NOT reinterpret evidence
  - It does NOT do law
  - It turns upstream state + elements into a 1-2 sentence product sentence

Architecture:
  - Schema text by default (zero API cost)
  - Model call (GPT-5.2) only for high-materiality cases
  - Materiality gate prevents over-writing low-risk gaps

Output fields per assessment:
  - exposure_statement:       final human-readable sentence
  - exposure_source:          "schema" | "model"
  - exposure_reason_code:     why model was invoked (or "schema_default")
  - exposure_confidence_note: optional short qualifier for ambiguous states
  - exposure_elements_used:   list of missing/unfavorable elements referenced
  - materiality:              "low" | "medium" | "high"
  - partial_class:            "partial_typical" | "partial_material" | "partial_review" | None

Usage:
    from cam.adapters.lease_review.lease_exposure import generate_exposure

    enriched = generate_exposure(coverage_assessment, cfg)
    # Returns list of assessment dicts with exposure_* fields added in-place
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_HIGH_MATERIALITY_ELEMENTS = {
    "cap on liability (if any)",
    "excluded expense categories",
    "assignment in connection with sale of business",
    "landlord indemnification of tenant scope",
    "rent abatement during force majeure period",
    "termination right if force majeure exceeds threshold period",
    "grounds for withholding consent (reasonableness standard)",
    "tenant's right to cure third-party defaults",
    "rent acceleration on default",
    "recapture right (landlord can terminate and lease directly)",
}

_MEDIUM_MATERIALITY_ELEMENTS = {
    "escalation cap or ceiling",
    "calculation methodology",
    "affiliate exception (no consent required for related entities)",
    "profit sharing on sublet above base rent",
    "removal obligation at lease expiration",
    "lien discharge or bond requirement",
    "annual CAM increase cap",
    "waiver of subrogation",
    "landlord contribution to tenant improvements (if any)",
    "unamortized tenant improvement cost recovery",
    "co-tenancy termination trigger (if applicable)",
    "time limit for bringing claims",
    "renewal option count and duration",
    "rent at renewal (formula or fair market value mechanism)",
}

_MODEL_STATES = {"covered_unfavorable", "ambiguous", "potentially_unenforceable"}

_REASON_CODES = {
    "covered_unfavorable": "unfavorable_provision",
    "ambiguous":           "ambiguous_provision",
    "potentially_unenforceable": "enforceability_concern",
    "high_materiality_partial": "high_materiality_missing_element",
    "mixed_signal":        "mixed_signal_partial",
}


def _classify_materiality(assessment: dict) -> str:
    state = assessment.get("coverage_state", "")
    missing = assessment.get("elements_missing", [])

    if state in _MODEL_STATES:
        return "high"
    if state == "missing":
        return "high"
    if state == "broken_xref":
        return "medium"
    if state in ("covered", "not_applicable"):
        return "low"

    missing_set = {e.lower() for e in missing}
    for element in _HIGH_MATERIALITY_ELEMENTS:
        if element in missing_set:
            return "high"
    for element in _MEDIUM_MATERIALITY_ELEMENTS:
        if element in missing_set:
            return "medium"
    return "low"


def _classify_partial(assessment: dict, materiality: str) -> Optional[str]:
    if assessment.get("coverage_state") != "partial":
        return None
    if materiality == "high":
        return "partial_material"
    if materiality == "medium":
        return "partial_review"
    return "partial_typical"


def _get_exposure_statement(issue_area_def, perspective):
    """Return the perspective-appropriate exposure statement.

    Schema v1.1.5 supports object form for perspective variants. Falls back
    to the tenant variant if the perspective key is missing. Falls back to
    the raw string if the field is still string-shaped (older LPs that
    haven't been extended yet).
    """
    stmt = issue_area_def.get("exposure_statement", "")
    if isinstance(stmt, dict):
        return stmt.get(perspective) or stmt.get("tenant") or ""
    return stmt


def _build_schema_exposure(assessment: dict, perspective: str = "tenant") -> dict:
    """Build a schema-path exposure result.

    Step 278: every schema-path output now also carries an
    `exposure_headline` field derived deterministically from the prose
    via `extract_headline` (mirrors the model-path output shape so the
    Synopsis can render one consistent presentation across both paths).
    """
    from cam.adapters.lease_review.lease_display import extract_headline

    state = assessment.get("coverage_state", "")
    missing = assessment.get("elements_missing", [])
    schema_statement = _get_exposure_statement(assessment, perspective)
    pid = assessment.get("issue_area_id", "")
    name = assessment.get("issue_area_name", pid)

    def _shape(stmt, elements_used):
        return {
            "exposure_statement": stmt,
            "exposure_headline":  extract_headline(stmt),
            "exposure_source":    "schema",
            "exposure_reason_code": "schema_default",
            "exposure_confidence_note": None,
            "exposure_elements_used": elements_used,
        }

    if state == "covered":
        return _shape(f"{name} is addressed and consistent with standard form.", [])
    if state == "not_applicable":
        return _shape(f"{name} does not apply to this lease.", [])
    if state == "partial" and missing:
        stmt = schema_statement or f"{name} is present but {missing[0]} is absent."
        return _shape(stmt, missing[:2])
    if state == "missing":
        stmt = schema_statement or f"{name} is absent from this lease."
        return _shape(stmt, [])
    stmt = schema_statement or f"{name}: {state}."
    return _shape(stmt, missing[:2])


_EXPOSURE_SYSTEM_PROMPT_TENANT = """You write concise, practical exposure assessments for commercial lease provisions.

Rules:
- Exactly 1-2 sentences. No more.
- Plain English. No legal citations. No case law. No jurisdiction references.
- Describe practical TENANT exposure -- what can go wrong, who bears the risk.
- Do not restate the clause mechanically.
- Do not speculate beyond the evidence supplied.
- Do not use "may or may not" or similar hedge phrases unless state is explicitly ambiguous.
- Focus on the business/legal consequence of what is absent or unfavorable.
- Tone: direct and specific. "Tenant has no protection against X" not "This provision appears to potentially suggest..."
- Never start with "This provision" or "The clause".
- Start with the risk actor: "Tenant", "Landlord", or the specific consequence.
"""

_EXPOSURE_SYSTEM_PROMPT_LANDLORD = """You write concise, practical exposure assessments for commercial lease provisions.

Rules:
- Exactly 1-2 sentences. No more.
- Plain English. No legal citations. No case law. No jurisdiction references.
- Describe practical LANDLORD exposure -- what can go wrong for the landlord, what enforcement, collection, recovery, or operational risk the landlord bears.
- Do not restate the clause mechanically.
- Do not speculate beyond the evidence supplied.
- Do not use "may or may not" or similar hedge phrases unless state is explicitly ambiguous.
- Focus on the business/legal consequence to the landlord of what is absent or unfavorable.
- Tone: direct and specific. "Landlord has no recourse if X" not "This provision appears to potentially suggest..."
- Never start with "This provision" or "The clause".
- Start with the risk actor: "Landlord", "Tenant", or the specific consequence to the landlord.
- Important: the input below was classified using rules that lean tenant-protective. A clause flagged as "unfavorable" may actually be favorable to the landlord (e.g. waived audit rights, sole-discretion consent). When that is the case, describe the landlord's UPSIDE plainly -- but if the absent or unfavorable element instead exposes the landlord (e.g. no late-fee mechanism, no acceleration on default, no removal obligation at expiration), describe that landlord-side risk directly.
"""

_EXPOSURE_SYSTEM_PROMPT_NEUTRAL = """You write concise, practical exposure assessments for commercial lease provisions.

Rules:
- Exactly 1-2 sentences. No more.
- Plain English. No legal citations. No case law. No jurisdiction references.
- Describe the practical exposure NEUTRALLY -- name whichever party bears the risk. Do not advocate for either side.
- If the clause is one-sided, say so and identify which party benefits and which is exposed.
- If the clause is mutual or balanced, describe the shared risk plainly.
- Do not restate the clause mechanically.
- Do not speculate beyond the evidence supplied.
- Do not use "may or may not" or similar hedge phrases unless state is explicitly ambiguous.
- Tone: direct, specific, and even-handed. "The clause shifts X risk to tenant; landlord retains Y" not "This provision appears to potentially suggest..."
- Never start with "This provision" or "The clause".
- Start with the risk actor or with the imbalance itself.
"""

# Step 262: pick a perspective-specific system prompt. Default tenant for
# backward compatibility with cfg dicts that don't carry the field.
_EXPOSURE_SYSTEM_PROMPTS = {
    "tenant":   _EXPOSURE_SYSTEM_PROMPT_TENANT,
    "landlord": _EXPOSURE_SYSTEM_PROMPT_LANDLORD,
    "neutral":  _EXPOSURE_SYSTEM_PROMPT_NEUTRAL,
}

# Backward-compat alias — some external callers may import this name directly.
_EXPOSURE_SYSTEM_PROMPT = _EXPOSURE_SYSTEM_PROMPT_TENANT

# Step 262: perspective-aware closing line for the user template. The body of
# the prompt (provision name, state, elements, evidence) stays identical so
# we can diff outputs across perspectives apples-to-apples.
_EXPOSURE_USER_TEMPLATE_TAIL = {
    "tenant":   "Write a 1-2 sentence exposure statement describing the practical risk to the tenant.",
    "landlord": "Write a 1-2 sentence exposure statement describing the practical risk or consequence to the landlord. If the clause is favorable to the landlord, describe that posture; if it exposes the landlord, describe that exposure.",
    "neutral":  "Write a 1-2 sentence exposure statement describing which party bears the risk and how. Be even-handed and name the parties explicitly.",
}

_EXPOSURE_USER_TEMPLATE = """Provision: {name}
Coverage state: {state}
Missing or unfavorable elements: {elements}
Evidence note: {evidence}
Fallback schema statement: {fallback}

{tail}

Step 278: respond as a JSON object with two fields:
- "headline": a short scannable summary (maximum 60 characters, ideally
  4-8 words). Name the core risk/benefit concisely. Examples:
  "Uncapped CAM, no audit rights", "Asymmetric indemnification",
  "Aggressive default remedies, short cure". No trailing period.
- "full": the 1-2 sentence exposure prose described above.

Return only the JSON object, no surrounding markdown or commentary."""


def _build_model_exposure(assessment: dict, cfg: dict, reason_code: str) -> dict:
    """Build exposure output using GPT-5.2 via ProviderRouter. One API call per assessment."""
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig

    pid = assessment.get("issue_area_id", "")
    name = assessment.get("issue_area_name", pid)
    state = assessment.get("coverage_state", "")
    missing = assessment.get("elements_missing", [])
    found = assessment.get("elements_found", [])
    evidence = assessment.get("evidence_summary", "")
    # Step 262: pick prompt + tail by perspective. Unknown values fall back to tenant.
    perspective = ((cfg or {}).get("perspective") or "tenant").lower()
    if perspective not in _EXPOSURE_SYSTEM_PROMPTS:
        perspective = "tenant"
    system_prompt = _EXPOSURE_SYSTEM_PROMPTS[perspective]
    user_tail = _EXPOSURE_USER_TEMPLATE_TAIL[perspective]

    # Step 272: schema-path fallback string is now perspective-aware for the
    # six v1.1.5 LPs. Older string-shaped LPs continue to return the same
    # static string for any perspective.
    fallback = _get_exposure_statement(assessment, perspective)

    if state == "covered_unfavorable":
        elements_used = found[:3]
        elements_str = f"Provision present but unfavorable: {', '.join(elements_used)}"
    else:
        elements_used = missing[:4]
        elements_str = ", ".join(elements_used) if elements_used else "see evidence note"

    user_prompt = _EXPOSURE_USER_TEMPLATE.format(
        name=name,
        state=state,
        elements=elements_str,
        evidence=evidence[:200] if evidence else "none",
        fallback=fallback[:200] if fallback else "none",
        tail=user_tail,
    )

    try:
        target = ModelTarget(
            name="openai:gpt-5.2",
            provider="openai",
            model="gpt-5.2",
            # Step 278: bumped from 150 to 220 to make room for the JSON
            # envelope ({"headline": "...", "full": "..."}) without
            # truncating the prose body. The body itself is still capped
            # by the 1-2-sentence rule in the system prompt.
            max_output_tokens=220,
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter("openai")
        raw = adapter.call(system_prompt, user_prompt, target).strip()

        # Step 278: parse {headline, full} JSON. Fall back deterministically
        # to extract_headline(full) if the model omits the headline field
        # or returns malformed JSON. The full prose is what populates
        # exposure_statement (preserves backward compatibility).
        statement, headline = _parse_headline_envelope(raw, perspective)

        if not statement or len(statement) < 20:
            logger.warning(f"[lease_exposure] Short response for {pid}, using schema fallback")
            result = _build_schema_exposure(assessment, perspective)
            result["exposure_source"] = "schema_fallback"
            result["exposure_reason_code"] = reason_code
            result["exposure_perspective"] = perspective
            return result

        return {
            "exposure_statement": statement,
            "exposure_headline":  headline,
            "exposure_source":    "model",
            "exposure_reason_code": reason_code,
            "exposure_confidence_note": "Ambiguous -- outcome depends on lease interpretation" if state == "ambiguous" else None,
            "exposure_elements_used": elements_used,
            "exposure_perspective": perspective,
        }

    except Exception as e:
        logger.warning(f"[lease_exposure] Model call failed for {pid}: {e}, using schema fallback")
        result = _build_schema_exposure(assessment, perspective)
        result["exposure_source"] = "schema_fallback"
        result["exposure_reason_code"] = reason_code
        result["exposure_perspective"] = perspective
        return result


def _parse_headline_envelope(raw: str, perspective: str) -> tuple:
    """Parse the model's `{headline, full}` JSON envelope.

    Returns (full_prose, headline). Falls back to deterministic headline
    extraction (`extract_headline`) when the model returns plain prose
    or malformed JSON. Always returns a usable (full, headline) pair —
    never raises.
    """
    import json
    from cam.adapters.lease_review.lease_display import extract_headline

    # Strip common wrapper artifacts (markdown fences, leading/trailing
    # backticks). Model is instructed to emit raw JSON but be defensive.
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").lstrip("json").strip()

    full, headline = "", ""
    parsed_ok = False
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            full = (obj.get("full") or "").strip()
            headline = (obj.get("headline") or "").strip()
            parsed_ok = True
    except (ValueError, TypeError):
        pass

    # If JSON parse failed entirely, treat the input as plain prose —
    # but only if it doesn't look like a malformed JSON fragment (in
    # which case we'd surface "{...broken" to users). The heuristic
    # "starts with '{' but didn't parse" catches the malformed case.
    if not parsed_ok:
        if cleaned.lstrip().startswith("{"):
            # Malformed JSON — strip braces / quotes and salvage what we can.
            stripped = _re.sub(r'[{}"]', "", cleaned).strip()
            full = stripped
        else:
            full = cleaned

    if not full:
        full = cleaned

    # Headline fallback: derive deterministically from full prose when
    # the model omits it. Cap at 60 chars per spec.
    if not headline:
        headline = extract_headline(full)
    elif len(headline) > 60:
        headline = extract_headline(headline)

    return full, headline


# Local re-import for the salvage path above; keeps the import next to
# the only call site without polluting the module top-level.
import re as _re  # noqa: E402


def generate_exposure(coverage_assessment: list, cfg: dict) -> list:
    """Enrich coverage assessments with exposure statements. Mutates in place."""
    if not coverage_assessment:
        return coverage_assessment

    # Step 262: log the perspective once per run so downstream debugging has a
    # quick anchor for which prompt set generated this batch of statements.
    perspective = ((cfg or {}).get("perspective") or "tenant").lower()
    if perspective not in _EXPOSURE_SYSTEM_PROMPTS:
        perspective = "tenant"
    print(
        f"[lease_exposure] Perspective: {perspective}",
        flush=True,
    )

    model_calls = 0
    schema_calls = 0
    start = time.time()

    for assessment in coverage_assessment:
        state = assessment.get("coverage_state", "")

        materiality = _classify_materiality(assessment)
        partial_class = _classify_partial(assessment, materiality)
        assessment["materiality"] = materiality
        assessment["partial_class"] = partial_class

        use_model = False
        reason_code = "schema_default"

        if state in _MODEL_STATES:
            use_model = True
            reason_code = _REASON_CODES.get(state, "high_materiality")
        elif materiality == "high" and state in ("partial", "missing"):
            use_model = True
            reason_code = _REASON_CODES["high_materiality_partial"]

        if use_model:
            exposure = _build_model_exposure(assessment, cfg, reason_code)
            model_calls += 1
        else:
            # Step 272: schema-path now reads the perspective-aware variant
            # for the six v1.1.5 LPs (object-shaped exposure_statement). All
            # other LPs continue to return their single string regardless of
            # perspective.
            exposure = _build_schema_exposure(assessment, perspective)
            # Step 262: tag schema-only outputs with perspective too so downstream
            # consumers can audit which lens this run was rendered under.
            exposure["exposure_perspective"] = perspective
            schema_calls += 1

        assessment.update(exposure)

    elapsed = round(time.time() - start, 2)
    logger.info(f"[lease_exposure] Complete: {model_calls} model, {schema_calls} schema, {elapsed}s")
    print(
        f"[lease_exposure] Exposure: {model_calls} model call(s) + "
        f"{schema_calls} schema-only in {elapsed}s",
        flush=True,
    )

    return coverage_assessment


def summarize_exposure(coverage_assessment: list) -> dict:
    model_count = sum(1 for a in coverage_assessment if a.get("exposure_source") == "model")
    schema_count = sum(1 for a in coverage_assessment if a.get("exposure_source") in ("schema", "schema_fallback"))
    high_mat = sum(1 for a in coverage_assessment if a.get("materiality") == "high")
    med_mat = sum(1 for a in coverage_assessment if a.get("materiality") == "medium")
    partial_typical = sum(1 for a in coverage_assessment if a.get("partial_class") == "partial_typical")
    partial_material = sum(1 for a in coverage_assessment if a.get("partial_class") == "partial_material")
    partial_review = sum(1 for a in coverage_assessment if a.get("partial_class") == "partial_review")

    return {
        "model_calls": model_count,
        "schema_only": schema_count,
        "high_materiality": high_mat,
        "medium_materiality": med_mat,
        "partial_typical": partial_typical,
        "partial_material": partial_material,
        "partial_review": partial_review,
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    _project_root = Path(__file__).parents[3]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

    import json, glob, os

    results_dir = _project_root / "05 Lease Analyzer" / "results"
    result_files = sorted(
        glob.glob(str(results_dir / "*/tenant_*/pipeline_results.json")),
        key=os.path.getmtime,
    )

    if not result_files:
        print("No pipeline results found -- run a lease first.")
        sys.exit(0)

    latest = result_files[-1]
    print(f"Testing against: {Path(latest).parent.parent.name}")

    with open(latest, encoding="utf-8") as f:
        r = json.load(f)

    ca = r.get("coverage_assessment", [])
    if not ca:
        print("No coverage_assessment in results -- run Step 244 first.")
        sys.exit(0)

    print(f"\nDry-run (schema only) -- {len(ca)} issue areas:\n")

    model_would_fire = 0
    for assessment in ca:
        mat = _classify_materiality(assessment)
        pcls = _classify_partial(assessment, mat)
        state = assessment.get("coverage_state", "")
        pid = assessment.get("issue_area_id", "")
        name = assessment.get("issue_area_name", pid)

        would_use_model = (state in _MODEL_STATES or (mat == "high" and state in ("partial", "missing")))
        if would_use_model:
            model_would_fire += 1

        exposure = _build_schema_exposure(assessment, "tenant")
        stmt = exposure["exposure_statement"]

        source_marker = "[MODEL]" if would_use_model else "[schema]"
        mat_marker = {"high": "[H]", "medium": "[M]", "low": "[L]"}.get(mat, "?")
        print(f"  {mat_marker} {source_marker} {pid} {name[:28]}: {state}")
        if would_use_model or mat != "low":
            print(f"    -> {stmt[:90]}{'...' if len(stmt) > 90 else ''}")
        if pcls:
            print(f"    partial_class: {pcls}")

    print(f"\nSummary: {model_would_fire} would invoke model, {len(ca) - model_would_fire} schema-only")
    print("(Dry-run complete -- no API calls made)")
