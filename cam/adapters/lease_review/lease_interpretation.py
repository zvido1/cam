"""
CAM Lease Review — Interpretation Notes

Generates specific, clause-level interpretation notes for provisions
that scored ASSERT_REVIEW_SIGNAL (Check Interpretation).

Called by lease_adapter.py after score_all_provisions() has attached
cam_score to each provision. Mutates provisions in place by adding
an `interpretation_note` field.

Only runs for DEVIATES provisions with ASSERT_REVIEW_SIGNAL — typically
2-5 provisions per lease.
"""

import time
from typing import Any, Dict, List

from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig


INTERPRETATION_SYSTEM_PROMPT = """You are a legal analyst reviewing a commercial lease deviation.

A multi-model AI system (CAM) has flagged this provision as "Check Interpretation" —
meaning the system found a real deviation with high confidence, but the practical
impact depends on how specific terms, definitions, or cross-referenced sections are read.

Your job is to write a structured interpretation note explaining the interpretive risks.

FORMATTING RULES:
- Write 2-4 SHORT paragraphs. Each paragraph MUST be separated by TWO newlines (a blank line between them). This is critical for rendering.
- Start each paragraph with a **bold topic phrase** followed by a colon, e.g. **Subordination conditionality:** The tenant...
- Use **double asterisks** around: section numbers (e.g. **Section 11.1**), article
  references (e.g. **Article XI**), and quoted defined terms or key phrases
  (e.g. **"complete assignment"**, **"freely assign"**)
- Each paragraph should be 2-4 sentences
- Do NOT write one continuous block — you MUST break into separate paragraphs
- Do NOT use bullet points, headers, or numbered lists
- Do NOT summarize what changed (the system already shows that)
- Do NOT give legal advice or recommend action
- Write for a commercial real estate attorney — use precise legal language

CONTENT RULES:
- Name the specific section numbers, defined terms, and actual quoted language
  that create the interpretive uncertainty
- For each issue, explain how different readings lead to different practical outcomes
- Do NOT be generic — "the interpretation depends on how terms are read" is useless
- Be specific about which party benefits from each reading

Output: just the formatted paragraphs, nothing else."""


def _build_interpretation_prompt(provision: dict) -> str:
    """Build the user prompt for a single provision."""
    pid = provision.get("provision_id", "")
    pname = provision.get("provision_name", pid)
    template_text = (provision.get("template_text") or "").strip()[:2000]
    tenant_text = (provision.get("tenant_text") or "").strip()[:2000]

    # Fragility signals that fired
    fragility = provision.get("fragility", {})
    signals = fragility.get("signals", [])
    signal_descriptions = {
        "definition_override":        "a key term is defined differently in the tenant version",
        "cross_reference_dependency": "the provision cross-references other sections that may differ",
        "qualifier_shift":            "obligation strength has changed (e.g., 'shall' to 'may')",
        "quantitative_deviation":     "a numerical threshold or amount has changed",
        "negation_pattern":           "new limiting or negating language has been added",
        "exception_clause":           "a new exception or carve-out has been added",
        "omission":                   "template language has been removed",
        "obligation_swap":            "responsibility has shifted between landlord and tenant",
    }
    signal_notes = []
    for s in signals:
        desc = signal_descriptions.get(s, s)
        signal_notes.append(f"- {s}: {desc}")

    # Evaluator reasoning summaries (first 300 chars each)
    ev_reasoning = provision.get("evaluator_reasoning", {}) or {}
    ev_lines = []
    for ev_key, reasoning in ev_reasoning.items():
        if isinstance(reasoning, str) and reasoning.strip():
            ev_lines.append(f"  Evaluator {ev_key}: {reasoning.strip()[:300]}")

    # Challenge details
    challenge_details = (provision.get("challenge_details") or "").strip()[:500]
    challenge_finding = provision.get("challenge_finding", "")

    # ASG and fragility score for context
    cam_score = provision.get("cam_score", {})
    asg = cam_score.get("ASG", "")
    cam_perm = cam_score.get("CAM_perm", "")

    lines = [
        f"PROVISION: {pid} — {pname}",
        "",
        "STANDARD TEMPLATE TEXT:",
        template_text or "[not provided]",
        "",
        "TENANT LEASE TEXT:",
        tenant_text or "[not provided]",
        "",
        "FRAGILITY SIGNALS DETECTED:",
        "\n".join(signal_notes) if signal_notes else "  (none logged)",
        "",
    ]

    if ev_lines:
        lines += [
            "EVALUATOR REASONING SUMMARIES:",
            "\n".join(ev_lines),
            "",
        ]

    if challenge_details:
        lines += [
            f"CHALLENGE RESULT: {challenge_finding}",
            f"CHALLENGE DETAILS: {challenge_details}",
            "",
        ]

    lines += [
        "TASK: Write a 2-3 sentence interpretation note as described in the system prompt.",
        "Name the specific terms, section numbers, or language that create the interpretive risk.",
    ]

    return "\n".join(lines)


def generate_interpretation_notes(
    dispositions: list,
    config: dict,
) -> int:
    """Generate interpretation notes for ASSERT_REVIEW_SIGNAL provisions.

    Mutates provisions in place by adding `interpretation_note` field.
    Returns count of notes generated.

    Args:
        dispositions: List of provision dicts (already scored with cam_score).
        config: Pipeline config dict with model settings.
    """
    # Select qualifying provisions
    qualifying = [
        p for p in dispositions
        if (
            p.get("final_verdict") == "DEVIATES"
            and p.get("provision_id") != "LP-00"
            and (p.get("cam_score") or {}).get("governance_signal") == "ASSERT_REVIEW_SIGNAL"
        )
    ]

    if not qualifying:
        return 0

    print(f"[lease_interpretation] Generating notes for {len(qualifying)} provisions...",
          flush=True)

    # Model config — use GPT-5.2 (same as challenger and severity)
    model_name = config.get("interpretation_model", config.get("challenge_model", "gpt-5.2"))
    timeout = config.get("interpretation_timeout", config.get("challenge_timeout", 60.0))
    provider = "openai"

    target = ModelTarget(
        name=f"{provider}:{model_name}",
        provider=provider,
        model=model_name,
        max_output_tokens=800,
        temperature=0.0,
        timeout_sec=timeout,
    )
    router = ProviderRouter([target], RouterConfig())

    generated = 0
    for prov in qualifying:
        pid = prov.get("provision_id", "?")
        try:
            # Use adapter.call() directly for plain-text output
            # (router.call_json expects JSON; interpretation notes are plain text)
            adapter = router._get_adapter(provider)
            user_prompt = _build_interpretation_prompt(prov)
            raw = adapter.call(INTERPRETATION_SYSTEM_PROMPT, user_prompt, target)
            note = raw.strip() if raw else ""
            if note:
                prov["interpretation_note"] = note
                generated += 1
                print(f"[lease_interpretation]   {pid}: note generated ({len(note)} chars)",
                      flush=True)
            else:
                print(f"[lease_interpretation]   {pid}: empty response, skipping",
                      flush=True)
        except Exception as e:
            print(f"[lease_interpretation]   {pid}: FAILED ({e}), skipping", flush=True)
            # Non-fatal — provision just won't have interpretation_note

    print(f"[lease_interpretation] Complete: {generated}/{len(qualifying)} notes generated",
          flush=True)
    return generated


# ── Uncertainty Notes (REVIEW_SIGNAL provisions) ──

UNCERTAINTY_SYSTEM_PROMPT = """You are a legal analyst reviewing a commercial lease provision where an AI system's evaluators disagreed on whether a real deviation exists.

A multi-model AI system (CAM) had multiple evaluators independently review this provision. They split on whether this constitutes a deviation from the standard template. Your job is NOT to decide who is right — it is to explain what the disagreement appears to hinge on, so a human reviewer knows exactly what to check.

FORMATTING RULES:
- Write exactly one short paragraph (2-4 sentences)
- Start with a **bold topic phrase** followed by a colon, e.g. **Assignment scope ambiguity:** The evaluators...
- Use **double asterisks** around: section numbers (e.g. **Section 5.2**), article references (e.g. **Article V**), and quoted key phrases (e.g. **"no material impairment"**)
- Do NOT use bullet points, headers, or numbered lists
- Do NOT claim this IS a deviation — the system is uncertain
- Do NOT give legal advice or recommend action
- Write for a commercial real estate attorney

CONTENT RULES:
- Identify the specific language, term, or structural difference that likely caused the evaluator split
- Explain why reasonable readers could disagree about whether this constitutes a material change
- Tell the reviewer what specific thing to check or compare to resolve the uncertainty
- Be specific — name actual sections, terms, and language from the clauses provided

Output: just the paragraph, nothing else."""


def _build_uncertainty_prompt(provision: dict) -> str:
    """Build the user prompt for an uncertainty note."""
    pid = provision.get("provision_id", "")
    pname = provision.get("provision_name", pid)
    template_text = (provision.get("template_text") or "").strip()[:2000]
    tenant_text = (provision.get("tenant_text") or "").strip()[:2000]

    # Evaluator verdicts — the core of the disagreement
    ev_verdicts = provision.get("evaluator_verdicts", {}) or {}
    ev_reasoning = provision.get("evaluator_reasoning", {}) or {}
    verdict_lines = []
    for ev_key, verdict in ev_verdicts.items():
        reasoning = ev_reasoning.get(ev_key, "")
        if isinstance(reasoning, str) and reasoning.strip():
            verdict_lines.append(f"  {ev_key}: {verdict} — {reasoning.strip()[:300]}")
        else:
            verdict_lines.append(f"  {ev_key}: {verdict}")

    # Fragility signals
    fragility = provision.get("fragility", {})
    signals = fragility.get("signals", [])
    signal_lines = [f"  - {s}" for s in signals] if signals else ["  (none)"]

    lines = [
        f"PROVISION: {pid} — {pname}",
        "",
        "STANDARD TEMPLATE TEXT:",
        template_text or "[not provided]",
        "",
        "TENANT LEASE TEXT:",
        tenant_text or "[not provided]",
        "",
        "EVALUATOR VERDICTS (these evaluators disagreed):",
        "\n".join(verdict_lines) if verdict_lines else "  (no verdicts available)",
        "",
        "FRAGILITY SIGNALS:",
        "\n".join(signal_lines),
        "",
        "TASK: Write a 1-paragraph uncertainty note as described in the system prompt.",
        "Explain what the disagreement likely hinges on and what the reviewer should check.",
    ]

    return "\n".join(lines)


def generate_uncertainty_notes(
    dispositions: list,
    config: dict,
) -> int:
    """Generate uncertainty notes for REVIEW_SIGNAL provisions.

    Mutates provisions in place by adding `interpretation_note` field.
    Uses the same field as interpretation notes so the UI renders them
    identically — the prompt ensures appropriate tone.

    Returns count of notes generated.

    Args:
        dispositions: List of provision dicts (already scored with cam_score).
        config: Pipeline config dict with model settings.
    """
    # Select qualifying provisions: DEVIATES + REVIEW_SIGNAL
    qualifying = [
        p for p in dispositions
        if (
            p.get("final_verdict") == "DEVIATES"
            and p.get("provision_id") != "LP-00"
            and (p.get("cam_score") or {}).get("governance_signal") == "REVIEW_SIGNAL"
            and not p.get("interpretation_note")  # don't overwrite existing notes
        )
    ]

    if not qualifying:
        return 0

    print(f"[lease_interpretation] Generating uncertainty notes for {len(qualifying)} provisions...",
          flush=True)

    model_name = config.get("interpretation_model", config.get("challenge_model", "gpt-5.2"))
    timeout = config.get("interpretation_timeout", config.get("challenge_timeout", 60.0))
    provider = "openai"

    target = ModelTarget(
        name=f"{provider}:{model_name}",
        provider=provider,
        model=model_name,
        max_output_tokens=400,  # 1 paragraph — less tokens needed
        temperature=0.0,
        timeout_sec=timeout,
    )
    router = ProviderRouter([target], RouterConfig())

    generated = 0
    for prov in qualifying:
        pid = prov.get("provision_id", "?")
        try:
            adapter = router._get_adapter(provider)
            user_prompt = _build_uncertainty_prompt(prov)
            raw = adapter.call(UNCERTAINTY_SYSTEM_PROMPT, user_prompt, target)
            note = raw.strip() if raw else ""
            if note:
                prov["interpretation_note"] = note
                generated += 1
                print(f"[lease_interpretation]   {pid}: uncertainty note generated ({len(note)} chars)",
                      flush=True)
            else:
                print(f"[lease_interpretation]   {pid}: empty response, skipping",
                      flush=True)
        except Exception as e:
            print(f"[lease_interpretation]   {pid}: FAILED ({e}), skipping", flush=True)

    print(f"[lease_interpretation] Uncertainty notes: {generated}/{len(qualifying)} generated",
          flush=True)
    return generated
