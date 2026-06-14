"""Closed-form directional prototype (Axes 1–4).

Step 389 introduced the prototype. Step 391 tightened Axis 2.

Runs ALONGSIDE existing Stage 7 freeform logic on a selected prototype LP set.
Does not modify any Stage 7 code.

Contamination guards enforced here
───────────────────────────────────
Guard 1 — Generic prompts only.
  _CLOSED_FORM_SYSTEM and _build_closed_form_user_prompt() contain NO
  canonical-case hints. No LP-specific section references, no Atlas/Meridian
  examples, no expected-finding language. Acceptance checks live ONLY in the
  results report for the human reviewer post-run.

Guard 3 — Prose cannot create findings.
  compute_axis_supported_candidate() reads ONLY axis_id, question_id, answer.
  It structurally cannot see 'reason' or 'citations' — those are display-only.

Guard 2 — Freeform baseline on same N.
  Enforced by _389_prototype_harness.py which references Step 386 N=10 data as
  the freeform baseline and runs N closed-form runs for comparison.

Step 391 — Axis-2 tightening (parallel to Step 388 Axis-1 tightening)
  Axis 2 may fire ONLY when the model names all four components: specific tenant
  obligation, specific landlord-side condition/failure (not a category), specific
  tenant consequence, and missing remedy. Enforced via a second closed-answer
  field axis2/q_a_confirmed. Routing requires q_a_confirmed == "yes" (or "unclear"
  for contested) before creating an Axis-2 candidate. Generic-category language
  ("conditions such as landlord maintenance may not be met") routes to no-candidate
  even when q_a == "yes".
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from cam.adapters.lease_review.model_config import (
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY,
    EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
    EVALUATOR_A_FALLBACK_LABEL,
)

# Eval-B uses gpt-5.4 for Stage 7 paths (gpt-5.5 has reliability issues on
# long lease prompts in Stage 7).  Stay consistent for the closed-form prototype.
_CF_B_MODEL = "gpt-5.4"
_CF_B_LABEL = "GPT-5.4"

_CF_MAX_OUTPUT_TOKENS = 2000  # Per-LP response: 6 axis answers + materiality
_CF_TEMPERATURE = 0.0
_CF_TIMEOUT_SEC = 120.0

_CF_EVALUATOR_LINEUP = {
    "A": {
        "provider": EVALUATOR_A_PRIMARY[0],
        "model":    EVALUATOR_A_PRIMARY[1],
        "label":    EVALUATOR_A_LABEL,
        "fallback": (EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], EVALUATOR_A_FALLBACK_LABEL),
        "max_output_tokens": _CF_MAX_OUTPUT_TOKENS,
        "temperature": _CF_TEMPERATURE,
        "timeout_sec": _CF_TIMEOUT_SEC,
    },
    "B": {
        "provider": EVALUATOR_B_FALLBACK[0],   # gpt-5.4 primary for this path
        "model":    _CF_B_MODEL,
        "label":    _CF_B_LABEL,
        "fallback": None,
        "max_output_tokens": _CF_MAX_OUTPUT_TOKENS,
        "temperature": _CF_TEMPERATURE,
        "timeout_sec": _CF_TIMEOUT_SEC,
    },
    "C": {
        "provider": EVALUATOR_C_PRIMARY[0],
        "model":    EVALUATOR_C_PRIMARY[1],
        "label":    EVALUATOR_C_LABEL,
        "fallback": None,
        "max_output_tokens": _CF_MAX_OUTPUT_TOKENS,
        "temperature": _CF_TEMPERATURE,
        "timeout_sec": _CF_TIMEOUT_SEC,
    },
}

# ── Guard 1: Generic system prompt — NO canonical case hints ──────────────────
_CLOSED_FORM_SYSTEM = """\
You are a commercial real estate attorney evaluating a single lease provision for
directional asymmetries that may disadvantage the tenant.

You will receive the name of one lease provision and the full lease text. Answer
four structured questions about that provision. Base every answer SOLELY on the
lease text — no external law, no common law, no assumptions about standard practice.

For each question return exactly one JSON object with:
  answer   — one of the exact allowed choices listed for that question
  citations — list of lease section identifiers that directly support your answer
              (e.g. ["§8.3", "Article 17"]) — empty list if none apply
  reason   — one sentence explaining why you chose that answer

Be precise:
  "yes"     — the described condition is expressly stated in the lease text
  "no"      — the described condition is expressly negated or clearly absent
  "unclear" — the lease text is genuinely ambiguous on this point
  "n.a."    — the question does not logically apply to this provision

Return your complete answer as a single valid JSON object. No markdown fences."""


# ── Guard 1: Generic per-LP user prompt — NO canonical case hints ─────────────
def _build_closed_form_user_prompt(lp_id: str, lp_name: str, lease_text: str) -> str:
    """Build the per-LP closed-form axis question prompt.

    Generic language only. No section references, no expected-finding hints,
    no Atlas/Meridian-specific examples. The model locates relevant sections
    from the LP name and lease text without guidance about what to find.
    """
    return f"""\
PROVISION BEING EVALUATED: {lp_id} — {lp_name}

FULL LEASE TEXT:
{lease_text}

─────────────────────────────────────────────────────────────────────────────
Answer the following four questions about the provision named above.
Read the full lease text carefully before answering.
─────────────────────────────────────────────────────────────────────────────

AXIS 2 — OBLIGATION WITHOUT REMEDY

Question A (axis2 / q_a):
Is the tenant obligated to perform, pay, accept risk, commence obligations,
lose rights, or continue performance in a scenario where a SPECIFIC, NAMED
landlord-side condition has not been met, is incomplete, or has failed?

To answer "yes" you must be able to name ALL FOUR of the following from the
lease text:
  1. The specific tenant obligation or exposure — the "what" (not just "tenant
     has ongoing obligations" or "tenant is required to continue performance")
  2. The SPECIFIC landlord-side condition, clause, or failure event — name the
     clause or event itself, not a category. "Conditions such as landlord
     maintenance" or "landlord-side conditions may not be met" do NOT satisfy
     this item. Name THE condition, not A type of condition.
  3. The SPECIFIC tenant consequence when that condition fails — what exactly
     must the tenant do or accept that becomes problematic as a result?
  4. The absence of a practical remedy responding to that specific failure

If you cannot name items 1–4 concretely from the lease text, answer "no" if
clearly absent, or "unclear" if a specific condition plausibly exists but
cannot be confirmed from the text alone.

The following answer patterns do NOT qualify for "yes":
  - "landlord-side conditions may not be met" (category, not a named condition)
  - "such as landlord maintenance" / "such as landlord insurance obligations"
    (hypothetical examples, not a specific named obligation in the lease)
  - "tenant obligations continue regardless" (describes item 1 only; item 2 absent)
  - "tenant lacks additional protection" (a conclusion, not a landlord-side failure)
  - "landlord has broader remedies generally" (Axis-1 territory, not Axis-2)

An UNCONDITIONAL tenant obligation (one with no linked landlord-side condition)
is NOT an Axis-2 issue — it is the normal structure of a covenant.
Allowed answers: yes / no / unclear / n.a.

Question A-confirmed (axis2 / q_a_confirmed):
Review your answer to Question A. Did you name a SPECIFIC landlord-side clause,
event, or named obligation in the lease text — not a hypothetical category of
conditions?
  "yes"     — a specific named clause or event was cited in Question A
  "no"      — Question A referred to a category, hypothetical, or general pattern,
               not a specific named item in this lease
  "unclear" — a specific condition seems plausible from the provision structure
               but cannot be confirmed as explicitly stated in the lease text
Allowed answers: yes / no / unclear
(Answer "n.a." if Question A is "no" or "n.a.")

Question B (axis2 / q_b):
If Question A is "yes" AND Question A-confirmed is "yes" or "unclear": does the
tenant have a PRACTICAL remedy that activates specifically when the landlord-side
condition fails? (A remedy is practical only if the lease text expressly gives
the tenant an actionable right — such as rent abatement, a delay right, a
termination trigger, a cure period, an offset right, or equivalent protection —
that responds to THIS specific landlord-side failure. A general default or
termination clause that requires a lengthy cure process and does not specifically
address this failure mode does NOT qualify.)
Allowed answers: yes / no / unclear / n.a.
(Answer n.a. if Question A is "no" or "n.a.", or if Question A-confirmed is "no")

─────────────────────────────────────────────────────────────────────────────

AXIS 3 — CONDITIONAL PROTECTION

Question A (axis3 / q_a):
Does the tenant have any protection, remedy, right, or limitation on landlord
action for this provision — even a limited or conditioned one?
Allowed answers: yes / no / unclear

Question B (axis3 / q_b):
If Question A is "yes": is that protection conditioned on specific, narrow, or
difficult-to-meet triggers — such as a landlord-negligence requirement, a minimum
duration threshold, a requirement that premises be untenantable, a landlord
subjective-determination gate, or a landlord-controlled prerequisite — such that
common or foreseeable failure cases would receive no protection?
Allowed answers: yes / no / unclear / n.a.
(Answer n.a. if Question A is "no")

─────────────────────────────────────────────────────────────────────────────

AXIS 4 — UNILATERAL CONTROL

Question (axis4 / standalone):
Can the landlord, or another non-tenant party, unilaterally alter, eliminate,
condition, or delay the tenant's protection for this provision — without requiring
tenant consent, without providing tenant a notice-and-cure right, and without
giving the tenant a meaningful remedy for that alteration?
Allowed answers: yes / no / unclear / n.a.

If you answer "yes" or "unclear": cite both the specific control mechanism AND
the tenant consequence.

─────────────────────────────────────────────────────────────────────────────

AXIS 1 — SAME-RISK PROPORTIONALITY

Question (axis1 / standalone):
For this specific provision, is there a SAME-RISK comparison where BOTH parties
face a structurally parallel event, obligation, or default scenario — AND the
tenant's remedy or protection for that SAME event is materially narrower than
the landlord's?

To answer "yes" you MUST satisfy ALL of the following:
  1. Name the specific parallel event that both parties face (not general
     characterizations about one party having broader remedies overall).
  2. Cite the tenant's specific remedy/protection for that event.
  3. Cite the landlord's specific remedy/protection for that SAME event.
  4. The two cited provisions must address the same triggering scenario.

Generic observations that one party has "a more complete default framework" or
"broader Article 17 remedies" do NOT qualify without the specific same-event
comparison. If you cannot name items 1–4 concretely from the lease text, answer
"no" or "unclear".
Allowed answers: yes / no / unclear / n.a.

─────────────────────────────────────────────────────────────────────────────

Return your answers as a single JSON object in this exact format:
{{
  "lp_id": "{lp_id}",
  "lp_name": "{lp_name}",
  "axis_results": [
    {{"axis_id": "axis2", "question_id": "q_a",          "answer": "<answer>", "citations": [], "reason": ""}},
    {{"axis_id": "axis2", "question_id": "q_a_confirmed", "answer": "<answer>", "citations": [], "reason": ""}},
    {{"axis_id": "axis2", "question_id": "q_b",          "answer": "<answer>", "citations": [], "reason": ""}},
    {{"axis_id": "axis3", "question_id": "q_a",          "answer": "<answer>", "citations": [], "reason": ""}},
    {{"axis_id": "axis3", "question_id": "q_b",          "answer": "<answer>", "citations": [], "reason": ""}},
    {{"axis_id": "axis4", "question_id": "standalone",   "answer": "<answer>", "citations": [], "reason": ""}},
    {{"axis_id": "axis1", "question_id": "standalone",   "answer": "<answer>", "citations": [], "reason": ""}}
  ],
  "materiality": "high|medium|low|unclear",
  "materiality_reason": "one sentence"
}}"""


# ── Guard 3: Routing reads ONLY closed answer fields ─────────────────────────
def compute_axis_supported_candidate(axis_results: List[dict]) -> dict:
    """Determine if this LP is an axis-supported directional candidate.

    GUARD 3 ENFORCEMENT: this function reads ONLY axis_id, question_id, answer
    from each axis_result entry. It structurally cannot see 'reason' or
    'citations' — those keys are never accessed here. A finding exists iff a
    closed answer supports it; prose cannot create a finding.

    Axis 1 is MODIFIER-ONLY: it cannot independently create a candidate. It only
    strengthens a finding already supported by Axis 2, 3, or 4.

    Returns dict with:
      axis_supported_candidate: bool
      contested:                bool
      contested_reason:         str | None
      proposed_bucket:          "Risk" | "Review Needed" | "Improvement" | "Addressed"
      supporting_axes:          list[str]
    """
    # Extract closed answers — read axis_id, question_id, answer ONLY
    # Step 391: axis2_qa_confirmed added (structural four-part specificity check)
    axis2_qa = axis2_qa_confirmed = axis2_qb = None
    axis3_qa = axis3_qb = axis4 = axis1 = None
    for r in axis_results:
        aid = r.get("axis_id")
        qid = r.get("question_id")
        ans = r.get("answer")
        # NOTE: r["reason"] and r["citations"] are intentionally never read here
        if aid == "axis2" and qid == "q_a":
            axis2_qa = ans
        elif aid == "axis2" and qid == "q_a_confirmed":
            axis2_qa_confirmed = ans
        elif aid == "axis2" and qid == "q_b":
            axis2_qb = ans
        elif aid == "axis3" and qid == "q_a":
            axis3_qa = ans
        elif aid == "axis3" and qid == "q_b":
            axis3_qb = ans
        elif aid == "axis4" and qid == "standalone":
            axis4 = ans
        elif aid == "axis1" and qid == "standalone":
            axis1 = ans

    supporting_axes: List[str] = []
    is_candidate = False
    contested = False
    proposed_bucket = "Addressed"

    # ── Axis 2: obligation without remedy ────────────────────────────────────
    # Step 391 tightening: q_a_confirmed must be "yes" or "unclear" before
    # q_b is consulted. If q_a_confirmed is "no", the finding is an over-fire
    # (generic category, not a named condition) — structural guard.
    _axis2_specific = axis2_qa == "yes" and axis2_qa_confirmed in ("yes", "unclear")
    _axis2_plausible = axis2_qa == "yes" and axis2_qa_confirmed == "unclear"

    if _axis2_specific and axis2_qb == "no":
        is_candidate = True
        if not _axis2_plausible:
            proposed_bucket = "Risk"
        else:
            proposed_bucket = "Review Needed"
            contested = True
        supporting_axes.append("axis2")
    elif _axis2_specific and axis2_qb == "unclear":
        is_candidate = True
        contested = True
        proposed_bucket = "Review Needed"
        supporting_axes.append("axis2")
    # axis2_qa == "yes" but q_a_confirmed == "no" → generic-category over-fire, no candidate

    # ── Axis 3: conditional protection ───────────────────────────────────────
    if axis3_qa == "yes" and axis3_qb == "yes":
        is_candidate = True
        if not contested and proposed_bucket == "Addressed":
            proposed_bucket = "Review Needed"
        supporting_axes.append("axis3")
    elif axis3_qa == "yes" and axis3_qb == "unclear":
        is_candidate = True
        contested = True
        if proposed_bucket == "Addressed":
            proposed_bucket = "Review Needed"
        if "axis3" not in supporting_axes:
            supporting_axes.append("axis3")

    # ── Axis 4: unilateral control ────────────────────────────────────────────
    if axis4 == "yes":
        is_candidate = True
        if proposed_bucket == "Addressed":
            proposed_bucket = "Review Needed"
        supporting_axes.append("axis4")
    elif axis4 == "unclear":
        is_candidate = True
        contested = True
        if proposed_bucket == "Addressed":
            proposed_bucket = "Review Needed"
        if "axis4" not in supporting_axes:
            supporting_axes.append("axis4")

    # ── Axis 1: modifier only — CANNOT standalone create a candidate ──────────
    # Applied only when at least one of Axis 2, 3, or 4 already fires.
    if axis1 == "yes" and supporting_axes:
        supporting_axes.append("axis1_modifier")
        # Modifier can upgrade uncertain Review Needed → Risk
        if proposed_bucket == "Review Needed" and not contested:
            proposed_bucket = "Risk"

    # Build contested reason from which axes are unclear (display-only string)
    contested_reason: Optional[str] = None
    if contested:
        parts = []
        if _axis2_specific and axis2_qb == "unclear":
            parts.append("Axis2-B unclear: remedy adequacy disputed")
        if axis3_qa == "yes" and axis3_qb == "unclear":
            parts.append("Axis3-B unclear: condition restrictiveness disputed")
        if axis4 == "unclear":
            parts.append("Axis4 unclear: unilateral control extent disputed")
        contested_reason = "; ".join(parts) or "Axes unclear — contested"

    return {
        "axis_supported_candidate": is_candidate,
        "contested": contested,
        "contested_reason": contested_reason,
        "proposed_bucket": proposed_bucket,
        "supporting_axes": supporting_axes,
    }


# ── JSON parser for closed-form responses ─────────────────────────────────────
def _parse_closed_form_response(text: str) -> Optional[dict]:
    """Extract the JSON object from an evaluator response."""
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract the outermost { ... } block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                return None
    return None


def _validate_closed_form_result(result: dict, lp_id: str) -> bool:
    """Check that the parsed result has the required fields."""
    if not isinstance(result, dict):
        return False
    if result.get("lp_id") != lp_id:
        return False
    axis_results = result.get("axis_results")
    if not isinstance(axis_results, list) or len(axis_results) < 5:
        return False
    required = {("axis2", "q_a"), ("axis2", "q_a_confirmed"), ("axis2", "q_b"),
                ("axis3", "q_a"), ("axis3", "q_b"),
                ("axis4", "standalone"), ("axis1", "standalone")}
    found = {(r.get("axis_id"), r.get("question_id")) for r in axis_results}
    return required.issubset(found)


# ── Single evaluator call (mirrors lease_synthesis._call_single_evaluator) ────
def _call_closed_form_evaluator(
    role: str,
    ev_cfg: dict,
    user_prompt: str,
    lp_id: str,
) -> dict:
    """Call one evaluator with the closed-form axis prompt for one LP."""
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.provider_health import get_health_tracker

    health = get_health_tracker()
    start_time = time.time()
    provider = ev_cfg["provider"]
    model = ev_cfg["model"]
    fallback = ev_cfg.get("fallback")

    def _try_call(p: str, m: str):
        if not health.is_available(p):
            raise RuntimeError(f"provider {p} degraded")
        target = ModelTarget(
            name=f"{p}:{m}-cf-{role}-{lp_id}",
            provider=p,
            model=m,
            max_output_tokens=ev_cfg["max_output_tokens"],
            temperature=ev_cfg["temperature"],
            timeout_sec=ev_cfg["timeout_sec"],
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(p)
        raw = adapter.call(_CLOSED_FORM_SYSTEM, user_prompt, target).strip()
        parsed = _parse_closed_form_response(raw)
        if parsed is None:
            raise RuntimeError(f"Eval-{role} {lp_id}: unparseable response")
        if not _validate_closed_form_result(parsed, lp_id):
            raise RuntimeError(f"Eval-{role} {lp_id}: invalid schema in response")
        return raw, parsed

    print(f"[cf_directional] Eval-{role} {lp_id}: calling {model}...", flush=True)
    try:
        raw_text, result = _try_call(provider, model)
        elapsed = round(time.time() - start_time, 2)
        print(f"[cf_directional] Eval-{role} {lp_id}: ok in {elapsed}s", flush=True)
        return {
            "role": role, "model": model, "provider": provider,
            "label": ev_cfg["label"], "completed": True,
            "result": result, "error": None, "elapsed_sec": elapsed,
        }
    except Exception as e:
        if fallback:
            fb_p, fb_m, fb_label = fallback
            print(f"[cf_directional] Eval-{role} {lp_id}: fallback {fb_m}...", flush=True)
            try:
                raw_text, result = _try_call(fb_p, fb_m)
                elapsed = round(time.time() - start_time, 2)
                print(f"[cf_directional] Eval-{role} {lp_id}: fallback ok in {elapsed}s", flush=True)
                return {
                    "role": role, "model": fb_m, "provider": fb_p,
                    "label": fb_label, "completed": True,
                    "result": result, "error": None, "elapsed_sec": elapsed,
                    "fallback_used": True,
                }
            except Exception as e2:
                pass
        elapsed = round(time.time() - start_time, 2)
        print(f"[cf_directional] Eval-{role} {lp_id}: FAILED — {e}", flush=True)
        return {
            "role": role, "model": model, "completed": False,
            "result": None, "error": str(e), "elapsed_sec": elapsed,
        }


# ── Run all 3 evaluators for one LP ──────────────────────────────────────────
def run_closed_form_lp(lp_id: str, lp_name: str, lease_text: str) -> dict:
    """Run all 3 closed-form evaluators for one LP.

    Returns a dict with:
      lp_id, lp_name
      evaluator_outputs: {role -> output_dict}
      routing: per-evaluator routing decision
      lp_is_candidate: bool — True if ANY evaluator returns axis_supported_candidate
      lp_contested:    bool — True if ANY evaluator returns contested
    """
    user_prompt = _build_closed_form_user_prompt(lp_id, lp_name, lease_text)

    evaluator_outputs: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_call_closed_form_evaluator, role, ev_cfg, user_prompt, lp_id): role
            for role, ev_cfg in _CF_EVALUATOR_LINEUP.items()
        }
        for fut in as_completed(futures):
            role = futures[fut]
            try:
                evaluator_outputs[role] = fut.result()
            except Exception as e:
                evaluator_outputs[role] = {
                    "role": role, "completed": False, "result": None, "error": str(e),
                }

    # Apply routing (Guard 3) per evaluator
    routing: Dict[str, dict] = {}
    any_candidate = False
    any_contested = False
    for role, output in evaluator_outputs.items():
        if not output.get("completed") or not output.get("result"):
            routing[role] = {"axis_supported_candidate": False, "error": "evaluator_failed"}
            continue
        axis_results = output["result"].get("axis_results", [])
        r = compute_axis_supported_candidate(axis_results)
        routing[role] = r
        if r["axis_supported_candidate"]:
            any_candidate = True
        if r["contested"]:
            any_contested = True

    return {
        "lp_id": lp_id,
        "lp_name": lp_name,
        "evaluator_outputs": evaluator_outputs,
        "routing": routing,
        "lp_is_candidate": any_candidate,
        "lp_contested": any_contested,
    }


# ── Run the full prototype pass ────────────────────────────────────────────────
def run_closed_form_prototype(
    prototype_lps: List[dict],
    lease_text: str,
) -> dict:
    """Run the closed-form axis prototype on the given LP list.

    Args:
        prototype_lps: list of {"lp_id": str, "lp_name": str}
        lease_text:    full lease text string

    Returns:
        dict with keys:
          lp_results: {lp_id -> run_closed_form_lp() output}
          candidate_lps: list of lp_ids where lp_is_candidate = True
          contested_lps: list of lp_ids where lp_contested = True
          elapsed_sec: float
    """
    start = time.time()
    lp_results: Dict[str, dict] = {}

    for lp in prototype_lps:
        lp_id = lp["lp_id"]
        lp_name = lp["lp_name"]
        print(f"[cf_directional] Running LP {lp_id} — {lp_name}", flush=True)
        lp_results[lp_id] = run_closed_form_lp(lp_id, lp_name, lease_text)

    candidate_lps = [lid for lid, r in lp_results.items() if r["lp_is_candidate"]]
    contested_lps = [lid for lid, r in lp_results.items() if r["lp_contested"]]
    elapsed = round(time.time() - start, 2)

    print(f"[cf_directional] Prototype done: {len(candidate_lps)}/{len(prototype_lps)} candidates "
          f"({len(contested_lps)} contested) in {elapsed}s", flush=True)

    return {
        "lp_results": lp_results,
        "candidate_lps": candidate_lps,
        "contested_lps": contested_lps,
        "elapsed_sec": elapsed,
    }
