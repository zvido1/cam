"""
CAM Lease Review — Stage 7: Cross-Provision Coverage Review (Step 311)

Answers three questions against the full lease text for flagged LPs only:
  Q1: Cross-coverage check — is the missing substance actually elsewhere?
  Q2: Directionality check — does the found provision run the right way?
  Q3: Compound risk — do multiple flagged LPs combine into something worse?

Multi-model: same evaluator lineup as Stage 5.
Output: cross_provision_findings[] appended to pipeline_results.
Existing LP states are never mutated.

Four corners only — no external law, no common law.
"""

import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────────────
STAGE_7_ENABLED = True

# ── Coverage states that trigger Stage 7 ──────────────────────────────────────
_FLAGGED_STATES = frozenset({
    "missing",
    "partial_material",
    "partial_typical",
    "review_needed",
})
_FLAGGED_CONFLICT_SEVERITIES = frozenset({"HIGH", "MEDIUM"})

# ── Evaluator lineup (mirrors Stage 5) ────────────────────────────────────────
from cam.adapters.lease_review.model_config import (  # noqa: E402
    EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
    EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
    EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
    EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
    EVALUATOR_A_FALLBACK_LABEL, EVALUATOR_B_FALLBACK_LABEL, EVALUATOR_C_FALLBACK_LABEL,
)

EVALUATOR_LINEUP: Dict[str, dict] = {
    "A": {
        "provider": EVALUATOR_A_PRIMARY[0],
        "model":    EVALUATOR_A_PRIMARY[1],
        "label":    EVALUATOR_A_LABEL,
        "fallback": (EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], EVALUATOR_A_FALLBACK_LABEL),
        "max_output_tokens": 8000,  # raised from 6K — 28 LPs × ~300 tokens/entry ≈ 8.4K needed
        "temperature": 0.0,
        "timeout_sec": 300.0,
    },
    "B": {
        "provider": EVALUATOR_B_PRIMARY[0],
        "model":    EVALUATOR_B_PRIMARY[1],
        "label":    EVALUATOR_B_LABEL,
        "fallback": (EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], EVALUATOR_B_FALLBACK_LABEL),
        "max_output_tokens": 8000,  # raised from 6K — 28 LPs × ~300 tokens/entry ≈ 8.4K needed
        "temperature": 0.0,
        "timeout_sec": 300.0,
    },
    "C": {
        "provider": EVALUATOR_C_PRIMARY[0],
        "model":    EVALUATOR_C_PRIMARY[1],
        "label":    EVALUATOR_C_LABEL,
        "fallback": None,  # grok-3 retired 2026-05-15; no same-provider fallback
        "max_output_tokens": 8000,  # raised from 6K — 28 LPs × ~300 tokens/entry ≈ 8.4K needed
        "temperature": 0.0,
        "timeout_sec": 300.0,
    },
}

# ── Stage 7 model split — Pass 1 / consolidation use GPT-5.4 ──────────────────
# NOTE: GPT-5.5 fails with RuntimeError on long Stage 7 prompts (Pass 1 + consolidation).
# GPT-5.4 is the reliable model for long synthesis. GPT-5.5 is used for Pass 2 only
# (short cluster verification prompt, succeeds consistently).
# Re-test GPT-5.5 on Pass 1 after OpenAI stabilizes rate limits (post ~May 23, 2026).
_SYNTHESIS_PASS1_B_MODEL       = "gpt-5.4"   # long prompt — gpt-5.5 fails
_SYNTHESIS_CONSOLIDATION_MODEL = "gpt-5.4"   # long prompt — gpt-5.5 fails
# Pass 2 uses EVALUATOR_LINEUP["B"] directly (gpt-5.5, short prompt, succeeds)

_EVALUATOR_LINEUP_PASS1: Dict[str, dict] = {
    role: (
        cfg if role != "B" else {
            **cfg,
            "model": _SYNTHESIS_PASS1_B_MODEL,
            "label": "GPT-5.4",
        }
    )
    for role, cfg in EVALUATOR_LINEUP.items()
}

# ── Safe JSON parser ──────────────────────────────────────────────────────────

def _safe_parse_synthesis(text: str):
    """Parse a model response to a dict or list. Returns None on failure.

    Handles markdown code fences, trailing garbage, and malformed JSON that
    needs brute-force object/array extraction.
    """
    from cam.core.json_extract import safe_json_extract
    if not text or not text.strip():
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
        text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # Brute-force: find largest dict then largest array
    for pattern in [r'\{.*\}', r'\[.*\]']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except (json.JSONDecodeError, ValueError):
                pass
    result = safe_json_extract(text)
    return result if result else None


# ── System prompt ──────────────────────────────────────────────────────────────
_EVALUATOR_SYSTEM = """You are a commercial real estate attorney performing cross-provision analysis of a lease.

Your task: answer three questions about the lease using ONLY the four corners of the document.
No external law. No common law. No jurisdiction doctrine. No assumptions about standard practice.
If protection is absent from the lease text, the finding is: not found. Full stop.

You will receive:
1. A list of flagged issue areas (LPs) with their coverage states
2. A full matrix of all LP states
3. The full lease text

Return a JSON object with exactly two keys: "cross_coverage_findings" and "candidates".

--- QUESTION 1: CROSS-COVERAGE CHECK ---

For each flagged provision, determine whether its substance is supplied
by any other express provision in this lease.

OUTCOME A — cross_coverage_gap:
Absent or not meaningfully addressed elsewhere.
Return: final_verdict="no_coverage_found"

OUTCOME B — partial_cross_coverage:
Partially addressed elsewhere; material elements still unmet.
Return: final_verdict="partial_coverage_found"

OUTCOME C — cross_coverage_relief:
Another provision genuinely and substantially satisfies the substance
of the flagged LP. The concern is materially reduced or eliminated.
Return: final_verdict="cross_coverage_confirmed", relief_section="[exact section]"

Use Outcome C sparingly. When in doubt, return Outcome A or B.

HARD RULE FOR OUTCOME C:
Cross-coverage relief may not be credited unless the substitute provision
protects the same party, against the same risk, with a usable remedy or right.

Three conditions, all required:
1. Same party — the substitute provision protects the party who needs protection
   under the flagged LP, not the other party.
2. Same risk — the substitute provision addresses the same category of risk,
   not merely related or adjacent language.
3. Usable remedy or right — the substitute provision gives the party an
   actionable right, remedy, cure period, or comparable protection — not
   merely an acknowledgment, definition, or procedural requirement.

If any of the three conditions fails, do NOT return Outcome C.

Example: LP-27 (landlord default framework) is absent. Article 15 has
cure language. Condition 1 fails immediately — Article 15's cure runs
landlord-against-tenant (protects landlord from tenant default), not
tenant-against-landlord. Return Outcome A with reasoning noting the
directional mismatch. Do not evaluate conditions 2 and 3.

For each LP return one object in cross_coverage_findings[]:
{
  "lp_id": "LP-XX",
  "lp_name": "...",
  "q1_verdict": "no_coverage_found" | "partial_coverage_found" | "full_coverage_found" | "cross_coverage_confirmed",
  "q1_cited_sections": ["Article 15", ...],
  "q1_reasoning": "...",
  "relief_section": "Section Y.Y (only when Outcome C)",
  "q2_applicable": true | false,
  "q2_verdict": "directional_match" | "directional_mismatch" | null,
  "q2_direction_note": "...",
  "q2_cited_sections": ["Article 15", ...],
  "q2a_verdict": "yes | no | unclear",
  "q2b_verdict": "proportional | disproportionate | not_applicable",
  "mismatch_flag": true | false,
  "protected_party": "tenant | landlord | bilateral | none",
  "exposed_party": "tenant | landlord | bilateral | none",
  "opposing_framework_summary": "one sentence on the stronger party's framework",
  "weaker_framework_summary": "one sentence on the weaker party's framework",
  "why_mismatch_matters": "one sentence on practical consequence if mismatch flagged",
  "final_verdict": "no_coverage_found" | "partial_coverage_found" | "full_coverage_found" | "cross_coverage_confirmed",
  "directionality": "tenant_unprotected" | "landlord_unprotected" | "match" | null,
  "severity": "HIGH" | "MEDIUM" | "LOW"
}

--- QUESTION 2 — DIRECTIONAL MISMATCH CHECK ---

Answer TWO sequential questions for EACH flagged provision. Also populate
the q2_applicable/q2_verdict/q2_cited_sections fields in cross_coverage_findings.

Q2a — DIRECTION: Does a protection, remedy, or default framework exist,
and does it protect the correct party against the correct risk?
   yes     = protection exists and runs toward the right party
   no      = protection runs toward the wrong party, or is absent
   unclear = protection exists but scope or direction is ambiguous

Q2b — PROPORTIONALITY: If Q2a = yes, is the protection proportional to
the opposing party's protection, or is it materially narrower?
   proportional      = both parties have comparable remedial frameworks
   disproportionate  = protection exists but is materially narrower, nominal,
                       deposit-dependent, discretionary, delayed, or incomplete
                       relative to the opposing party's framework
   not_applicable    = Q2a was "no" or "unclear"

MISMATCH FLAG: Raise mismatch_flag = true when EITHER:
   - Q2a = "no"  (wrong direction or absent)
   - Q2b = "disproportionate"  (correct direction but not equivalent weight)

PROPORTIONALITY TEST:
   * Does one party have a multi-remedy framework (termination, re-entry, damages,
     self-help, acceleration, fees) while the other has a single narrow remedy?
   * Does one party's remedy require using their own funds (e.g. security deposit)?
   * Is one party's remedy conditional, discretionary, or procedurally demanding
     while the other party's is self-executing?

HARD CONSTRAINT: Do not treat this as "grade fairness" or "contract balance scoring."
Commercial leases are often intentionally asymmetrical. Surface asymmetry — do not
moralize. Directional mismatch exists when one side has a materially more complete
remedial framework than the other for comparable default/failure scenarios.

TEACHING EXAMPLE (Atlas/Meridian lease):
   Article 17 gives Landlord: events of default, cure periods, termination,
   re-entry, reletting, deficiency recovery, self-help cure reimbursement.
   Section 5.1 gives Tenant: notice/cure, security-deposit setoff, termination
   after continued failure, reservation of law/equity remedies.

   Correct answer:
   Q2a = "yes"  (tenant protection exists and runs the right direction)
   Q2b = "disproportionate"  (tenant framework is narrower and partly deposit-dependent)
   mismatch_flag = true  (triggered by Q2b, not Q2a)

   Do NOT say "tenant has nothing." Say "tenant has something, but not equivalent machinery."

All Q2 fields (q2_applicable, q2_verdict, q2a_verdict, q2b_verdict, mismatch_flag,
protected_party, exposed_party, opposing_framework_summary, weaker_framework_summary,
why_mismatch_matters) go DIRECTLY in each cross_coverage_findings entry for that LP.
Do NOT create a separate q2_results array. The candidates[] array is ONLY for Q3.

--- QUESTION 3: COMPOUND RISK ANALYSIS ---

A compound risk exists when two or more provisions interact to create exposure
that neither shows alone. Review the full LP matrix above. A compound risk
may involve provisions marked covered, partial, missing, or unfavorable.

COVERAGE STATE IS NOT RISK STATE. A covered provision may still participate
in compound risk through asymmetry, missing reciprocal rights, or removal of
practical enforcement mechanisms.

Do not merely ask whether any risks are obvious. Evaluate each of the five
compound risk patterns below independently and systematically. You must respond
to every pattern.

---

PATTERN 1 — DIRECTIONAL ASYMMETRY
One party has a full remedy, default, or control structure. The other party
lacks the reciprocal structure. The machinery works in one direction only.

Check: Does this lease have detailed protections for one party in any area
where the other party has no equivalent? Consider: default frameworks,
cure rights, notice requirements, remedy chains.

---

PATTERN 2 — LEVER ELIMINATION
A right technically exists, but the lease removes the practical tools needed
to enforce it. The right is present; the enforcement mechanism is not.

Check: Are there situations where a party has a nominal right but no audit
right, no offset right, no self-help right, and no default remedy to exercise
it? The right exists on paper. The levers to pull it are gone.

---

PATTERN 3 — SUBORDINATION / PRIORITY TRAP
A party gives up legal priority, control, or position without a matching
protection in return.

Check: Does the lease require automatic subordination, attornment, or
priority concession without a reciprocal non-disturbance covenant, cure
right, or comparable protection? Does a lender or successor acquire rights
the original tenant cannot enforce against?

---

PATTERN 4 — CASCADING NO-REMEDY SCENARIO
Multiple partial or missing provisions combine so that in a real-world
adverse event, the affected party has no cure, no offset, no exit, and
no meaningful remedy.

Check: Are there combinations of gaps where a landlord default, casualty,
taking, or other adverse event could leave a party liable for full performance
with no recourse? Trace the remedies available — if the chain reaches a dead
end, that is the finding.

IMPORTANT: Do not suppress a Pattern 4 candidate merely because one of its
component provisions is already identified as a directional mismatch under
Pattern 1 or Question 2. Directional asymmetry may be one ingredient in a
cascading no-remedy scenario. If a missing remedy framework (such as an absent
landlord-default article) combines with casualty, force majeure, access
restriction, utility interruption, or maintenance failure provisions to leave
a party with no cure, offset, abatement, termination right, or practical remedy
during a real-world adverse event — that is a Pattern 4 finding independent of
any directional mismatch finding.

Pattern 4 examples:
- LP-27 absent (no landlord-default remedies) + LP-14 partial (force majeure
  excludes rent, no abatement or termination right) + LP-24 partial (casualty,
  no landlord repair obligation, no abatement) = tenant pays full rent during
  prolonged disruption with no cure, no offset, no exit. Neither LP alone shows
  this. The combination does.
- LP-07 partial (uncapped CAM, no audit rights) + LP-27 absent (no landlord-
  default framework) = tenant has no way to challenge overcharges and no remedy
  if landlord refuses to adjust. The right is theoretical; all levers are gone.

---

PATTERN 5 — OPERATIONAL DEAD-END
The lease creates a scenario where operational performance is impaired or
impossible, but the affected party still owes full performance obligations.

Check: Do casualty, force majeure, access restrictions, maintenance failure,
or utility interruption provisions combine with no rent abatement, no
termination right, and no self-help to leave a party paying full rent while
unable to operate?

---

For each of the five patterns, return one structured object in candidates[]:

{
  "pattern_type": "directional_asymmetry | lever_elimination | subordination_trap | cascading_no_remedy | operational_dead_end",
  "present": "yes | no | unclear",
  "involved_lps": ["LP-XX", "LP-YY"],
  "affected_party": "tenant | landlord | both",
  "evidence_from_lease": "specific section, clause, or confirmed absence",
  "why_the_combination_matters": "what the practical consequence is",
  "why_not_visible_from_one_lp_alone": "why this only appears when provisions are read together",
  "confidence": "high | medium | low"
}

Return exactly five objects in candidates[] — one per pattern type.
If a pattern is not present, still return the object with present: "no" and a brief reason.
Do not skip any pattern.

--- HARD RULES ---
1. Four corners only. No external law citations.
2. Every cross-coverage credit must cite a specific article or section.
3. Every directional mismatch must explain which direction the found provision runs.
4. Do not modify or comment on LP coverage states — analyze only.
5. Your response must be valid JSON starting with { and ending with }. No markdown fences."""

# ── Consolidation system prompt ────────────────────────────────────────────────
_CONSOLIDATOR_SYSTEM = """You are a lead commercial real estate attorney reviewing three evaluator analyses of the same lease.

Your task: produce a final consolidated cross-provision review by comparing three evaluator outputs.
You are Evaluator B — the consolidator for this pass.

STEP 1 — RECONCILE cross_coverage_findings[]:
For each LP appearing in any evaluator's cross_coverage_findings:
- Compare Q1 verdicts across all three evaluators
- If 2 or 3 evaluators agree on the verdict, use that verdict
- If 1-2 split: use your own judgment, cite the disagreement in reasoning
- For Q2 (directionality): any directional_mismatch finding by any evaluator must be surfaced.
  If an evaluator flagged a directional_mismatch (even with final_verdict no_coverage_found),
  surface it as finding_type "directional_mismatch" with the cited sections and directionality field.

STEP 2 — INCLUDE PRE-VERIFIED COMPOUND FINDINGS:
Compound risk findings have been verified in a separate two-pass pipeline before this consolidation
call. They are provided to you below. Do NOT re-evaluate them. Include each pre-verified compound
finding verbatim in your cross_provision_findings[] output with finding_type "compound_risk".

Return a JSON object:
{
  "cross_provision_findings": [
    {
      "finding_id": "CPF-01",
      "finding_type": "cross_coverage_gap" | "directional_mismatch" | "compound_risk",
      "implicated_lps": ["LP-27"],
      "headline": "...",
      "detail": "...",
      "cited_sections": ["Article 15"],
      "verdict": "no_coverage_found" | "partial_coverage_found" | "full_coverage_found" | "compound_risk_confirmed",
      "directionality": "tenant_unprotected" | "landlord_unprotected" | "match" | null,
      "severity": "HIGH" | "MEDIUM" | "LOW",
      "evaluator_agreement": "3-0" | "2-1" | "1-2",
      "evaluator_verdicts": {
        "A": "no_coverage_found",
        "B": "no_coverage_found",
        "C": "partial_coverage_found"
      }
    }
  ]
}

Rules:
- finding_id: CPF-01, CPF-02, ... in order
- finding_type:
    "directional_mismatch" when Q2 found a mismatch
    "compound_risk" for pre-verified compound findings (include verbatim)
    "cross_coverage_gap" for all other gap findings
- Only emit findings where verdict is not "full_coverage_found" (unless directionality overrides it)
- Do not emit findings for LPs that are genuinely covered with no directional issues
- Four corners only — no external law
- Response must be valid JSON starting with { and ending with }. No markdown fences."""


def _build_evaluator_user_prompt(
    flagged_lps: List[dict],
    full_lease_text: str,
    perspective: str,
    coverage_assessment: List[dict] = None,
) -> str:
    """Build the per-evaluator user prompt."""
    lp_block = []
    for lp in flagged_lps:
        lp_block.append({
            "lp_id": lp["lp_id"],
            "lp_name": lp["lp_name"],
            "coverage_state": lp["coverage_state"],
            "partial_class": lp.get("partial_class", ""),
            "key_missing": lp.get("key_missing", []),
        })

    # Build full LP state matrix for compound risk pattern analysis (Q3).
    # One line per LP: ID, name, state, element fraction if Step 305 ran.
    _presence = {"explicitly_present", "implicitly_present", "covered_by_default_law", "covered_in_other_LP"}
    if coverage_assessment:
        matrix_rows = []
        for a in sorted(coverage_assessment,
                        key=lambda x: (x.get("issue_area_id") or x.get("provision_id") or "")):
            lp_id   = a.get("issue_area_id") or a.get("provision_id") or ""
            lp_name = a.get("issue_area_name") or a.get("provision_name") or lp_id
            state   = a.get("coverage_state", "unknown")
            ev = a.get("element_verdicts") or []
            if ev:
                n_present = sum(1 for e in ev if e.get("verdict") in _presence)
                matrix_rows.append(f"{lp_id}: {lp_name} — {state} ({n_present}/{len(ev)} elements)")
            else:
                matrix_rows.append(f"{lp_id}: {lp_name} — {state}")
        matrix_block = "FULL PROVISION MATRIX (all LPs — compound risk may involve any LP):\n" + "\n".join(matrix_rows)
    else:
        matrix_block = ""

    lines = [
        f"PERSPECTIVE: {perspective.upper()} (analyze from this party's point of view)",
        "",
        f"FLAGGED ISSUE AREAS ({len(flagged_lps)} total — only these need cross-provision analysis):",
        json.dumps(lp_block, indent=2),
        "",
    ]
    if matrix_block:
        lines += [matrix_block, ""]
    lines += [
        "FULL LEASE TEXT:",
        full_lease_text,
        "",
        "Return your JSON response now.",
    ]
    return "\n".join(lines)


def _build_consolidator_user_prompt(
    evaluator_results: Dict[str, Optional[dict]],
    flagged_lps: List[dict],
    perspective: str,
    verified_compound_findings: List[dict] = None,
    verified_relief_findings: List[dict] = None,
) -> str:
    """Build the consolidation pass user prompt."""
    lines = [
        f"PERSPECTIVE: {perspective.upper()}",
        "",
        f"FLAGGED LPs: {[lp['lp_id'] for lp in flagged_lps]}",
        "",
        "EVALUATOR A OUTPUT:",
        json.dumps(evaluator_results.get("A"), indent=2),
        "",
        "EVALUATOR B OUTPUT (yours — use your own judgment plus comparison):",
        json.dumps(evaluator_results.get("B"), indent=2),
        "",
        "EVALUATOR C OUTPUT:",
        json.dumps(evaluator_results.get("C"), indent=2),
        "",
    ]
    if verified_compound_findings:
        lines += [
            f"PRE-VERIFIED COMPOUND FINDINGS ({len(verified_compound_findings)} — include verbatim as compound_risk entries, do not re-evaluate):",
            json.dumps(verified_compound_findings, indent=2),
            "",
        ]
    else:
        lines += ["PRE-VERIFIED COMPOUND FINDINGS: none.", ""]
    if verified_relief_findings:
        lines += [
            f"PRE-VERIFIED CROSS-COVERAGE RELIEF FINDINGS ({len(verified_relief_findings)} — include verbatim as cross_coverage_relief entries, do not re-evaluate):",
            json.dumps(verified_relief_findings, indent=2),
            "",
        ]
    else:
        lines += ["PRE-VERIFIED RELIEF FINDINGS: none.", ""]
    lines += ["Produce the final consolidated cross_provision_findings[] now."]
    return "\n".join(lines)


def _call_single_evaluator(
    role: str,
    ev_cfg: dict,
    user_prompt: str,
) -> dict:
    """Call one evaluator and return its raw output dict."""
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.provider_health import get_health_tracker

    health = get_health_tracker()
    start_time = time.time()

    provider = ev_cfg["provider"]
    model    = ev_cfg["model"]
    fallback = ev_cfg.get("fallback")  # (provider, model, label) or None

    def _try_call(p: str, m: str) -> dict:
        if not health.is_available(p):
            raise RuntimeError(f"provider {p} degraded")
        target = ModelTarget(
            name=f"{p}:{m}-stage7-{role}",
            provider=p,
            model=m,
            max_output_tokens=ev_cfg["max_output_tokens"],
            temperature=ev_cfg["temperature"],
            timeout_sec=ev_cfg["timeout_sec"],
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(p)
        raw = adapter.call(_EVALUATOR_SYSTEM, user_prompt, target).strip()
        parsed = _safe_parse_synthesis(raw)
        if parsed is None:
            raise RuntimeError(f"evaluator {role} returned unparseable response")
        if not isinstance(parsed, dict):
            raise RuntimeError(f"evaluator {role} returned non-dict: {type(parsed)}")
        return parsed

    print(f"[lease_synthesis] Eval-{role}: calling {model} ({provider})...", flush=True)
    try:
        result = _try_call(provider, model)
        elapsed = time.time() - start_time
        print(f"[lease_synthesis] Eval-{role}: {model} succeeded in {round(elapsed, 1)}s", flush=True)
        return {"role": role, "model": model, "provider": provider,
                "label": ev_cfg["label"], "completed": True,
                "result": result, "error": None,
                "elapsed_sec": round(elapsed, 2)}
    except Exception as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ["503", "connection", "refused", "unavailable", "resource_exhausted"]):
            health.mark_degraded(provider, reason=str(e)[:100])
        print(f"[lease_synthesis] Eval-{role}: {model} FAILED ({type(e).__name__})", flush=True)

        if fallback:
            fb_provider, fb_model, fb_label = fallback
            print(f"[lease_synthesis] Eval-{role}: trying fallback {fb_model} ({fb_provider})...", flush=True)
            try:
                result = _try_call(fb_provider, fb_model)
                elapsed = time.time() - start_time
                print(f"[lease_synthesis] Eval-{role}: fallback succeeded in {round(elapsed, 1)}s", flush=True)
                return {"role": role, "model": fb_model, "provider": fb_provider,
                        "label": fb_label, "completed": True,
                        "result": result, "error": None,
                        "elapsed_sec": round(elapsed, 2), "fallback_used": True}
            except Exception as e2:
                print(f"[lease_synthesis] Eval-{role}: fallback FAILED ({type(e2).__name__})", flush=True)
                return {"role": role, "model": model, "completed": False,
                        "result": None, "error": str(e2),
                        "elapsed_sec": round(time.time() - start_time, 2)}

        return {"role": role, "model": model, "completed": False,
                "result": None, "error": str(e),
                "elapsed_sec": round(time.time() - start_time, 2)}


def _call_consolidator(
    evaluator_results: Dict[str, Optional[dict]],
    flagged_lps: List[dict],
    perspective: str,
    verified_compound_findings: List[dict] = None,
    verified_relief_findings: List[dict] = None,
) -> Optional[dict]:
    """Run consolidation pass using Evaluator B as consolidator."""
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.provider_health import get_health_tracker

    health = get_health_tracker()
    ev_cfg = EVALUATOR_LINEUP["B"]
    user_prompt = _build_consolidator_user_prompt(
        evaluator_results, flagged_lps, perspective,
        verified_compound_findings, verified_relief_findings
    )

    def _try_call(p: str, m: str) -> dict:
        if not health.is_available(p):
            raise RuntimeError(f"provider {p} degraded")
        target = ModelTarget(
            name=f"{p}:{m}-stage7-consolidator",
            provider=p,
            model=m,
            max_output_tokens=6000,
            temperature=0.0,
            timeout_sec=300.0,
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(p)
        raw = adapter.call(_CONSOLIDATOR_SYSTEM, user_prompt, target).strip()
        parsed = _safe_parse_synthesis(raw)
        if parsed is None:
            raise RuntimeError(f"consolidator returned unparseable response")
        if not isinstance(parsed, dict):
            raise RuntimeError(f"consolidator returned non-dict: {type(parsed)}")
        return parsed

    provider = ev_cfg["provider"]
    model    = _SYNTHESIS_CONSOLIDATION_MODEL  # gpt-5.4 — gpt-5.5 fails on long consolidation prompt
    fallback = ev_cfg.get("fallback")

    print(f"[lease_synthesis] Consolidation: calling {model} ({provider})...", flush=True)
    try:
        result = _try_call(provider, model)
        print(f"[lease_synthesis] Consolidation: succeeded", flush=True)
        return result
    except Exception as e:
        print(f"[lease_synthesis] Consolidation: primary FAILED ({type(e).__name__})", flush=True)
        if fallback:
            fb_provider, fb_model, _ = fallback
            try:
                result = _try_call(fb_provider, fb_model)
                print(f"[lease_synthesis] Consolidation: fallback succeeded", flush=True)
                return result
            except Exception as e2:
                print(f"[lease_synthesis] Consolidation: fallback FAILED ({type(e2).__name__})", flush=True)
        return None


def _collect_flagged_lps(
    coverage_assessment: List[dict],
    conflicts: List[dict],
) -> List[dict]:
    """Return LPs eligible for Stage 7 analysis.

    Includes LPs with flagged coverage states plus LPs implicated in
    HIGH/MEDIUM conflicts. Deduplicates by lp_id.
    """
    seen: set = set()
    flagged: List[dict] = []

    # From coverage assessment
    for a in coverage_assessment:
        lp_id = a.get("issue_area_id") or a.get("provision_id") or ""
        if not lp_id:
            continue
        state = a.get("coverage_state", "")
        pcls  = a.get("partial_class", "")
        if state in _FLAGGED_STATES or pcls in {"partial_material", "partial_typical"}:
            if lp_id not in seen:
                seen.add(lp_id)
                # Extract top missing elements for context
                missing = []
                for ev in (a.get("element_verdicts") or []):
                    if ev.get("verdict") == "missing":
                        missing.append(ev.get("element_label") or ev.get("element_id", ""))
                flagged.append({
                    "lp_id": lp_id,
                    "lp_name": a.get("issue_area_name") or a.get("provision_name") or lp_id,
                    "coverage_state": state,
                    "partial_class": pcls,
                    "key_missing": missing[:5],
                })

    # From conflicts — add any conflict-implicated LP not already in the list
    for c in conflicts:
        sev = (c.get("severity") or "").upper()
        if sev not in _FLAGGED_CONFLICT_SEVERITIES:
            continue
        for lp_id in (c.get("provision_ids") or []):
            if lp_id and lp_id not in seen:
                seen.add(lp_id)
                flagged.append({
                    "lp_id": lp_id,
                    "lp_name": lp_id,
                    "coverage_state": "conflict_implicated",
                    "partial_class": "",
                    "key_missing": [],
                })

    return flagged


# ── Compound risk two-pass pipeline ──────────────────────────────────────────

def _cluster_compound_candidates(evaluator_outputs: dict) -> list:
    """Group Pass 1 compound candidates by (pattern_type, frozenset(involved_lps)).

    Two candidates are the same cluster if both fields match exactly.
    Only `present: "yes"` objects are forwarded to Pass 2.
    """
    clusters: dict = {}
    for role, output in evaluator_outputs.items():
        for item in (output.get("candidates") or []):
            if (item.get("present") or "").lower() != "yes":
                continue
            pt  = item.get("pattern_type", "")
            lps = frozenset(item.get("involved_lps") or [])
            key = (pt, lps)
            if key not in clusters:
                clusters[key] = {
                    "pattern_type":    pt,
                    "involved_lps":    sorted(lps),
                    "found_by":        [],
                    "pass1_responses": {},
                }
            clusters[key]["found_by"].append(role)
            clusters[key]["pass1_responses"][role] = item

    result = []
    for i, (_, data) in enumerate(clusters.items()):
        data["candidate_id"] = f"CRX-{i + 1:02d}"
        result.append(data)
    return result


_PASS2_EVALUATOR_SYSTEM = """You are a commercial real estate attorney performing two verification tasks.

COVERAGE STATE IS NOT RISK STATE. A provision can be fully covered and still participate
in compound risk through asymmetry, missing reciprocal rights, or removal of practical
enforcement mechanisms.

SECTION 1 — COMPOUND RISK VERIFICATION
Compound risk candidates have been identified from a first-pass analysis. Evaluate every
candidate and return a verdict on whether the compound risk is real.

For each compound candidate, return one verdict object:
{
  "candidate_id": "CRX-01",
  "pattern_type": "...",
  "involved_lps": ["LP-XX", "LP-YY"],
  "verdict": "compound_risk_present | no_compound_risk | unclear",
  "reason": "...",
  "lease_evidence": "specific section or confirmed absence from lease text",
  "affected_party": "tenant | landlord | both",
  "confidence": "high | medium | low"
}

SECTION 2 — CROSS-COVERAGE RELIEF VERIFICATION
One or more evaluators identified potential cross-coverage relief in Pass 1 — a finding
that another provision substantially satisfies a flagged LP's substance. Verify each:

1. Does the cross-coverage genuinely exist?
2. Does it run in the correct direction for the party who needs protection?

For each relief candidate, return one verdict object:
{
  "candidate_type": "cross_coverage_relief",
  "candidate_id": "RLF-01",
  "lp_id": "LP-XX",
  "verdict": "cross_coverage_confirmed | no_coverage_found | directional_false_positive | unclear",
  "direction": "bilateral | tenant_only | landlord_only | other",
  "direction_adequate": true | false,
  "relief_section": "Section Y.Y (if confirmed)",
  "reason": "...",
  "confidence": "high | medium | low"
}

verdict "directional_false_positive": cross-coverage exists but runs the wrong direction.

SECTION 3 — DIRECTIONAL MISMATCH VERIFICATION
Evaluators flagged directional mismatch candidates in Pass 1 Q2. Verify each candidate
using the same Q2a / Q2b structure. Evaluate every candidate including those you did not
flag yourself.

Q2a = "yes" if protection exists and runs toward the right party.
Q2b = "disproportionate" if correct-direction protection exists but is materially
narrower than the opposing party's framework.

verdict = "mismatch_confirmed" if Q2a = "no" OR Q2b = "disproportionate"
verdict = "no_mismatch" if Q2a = "yes" AND Q2b in {proportional, not_applicable}

HARD CONSTRAINT: Surface asymmetry. Do not moralize about it. Directional mismatch
exists when one side has a materially more complete remedial framework than the other
for comparable default/failure scenarios — not merely because the lease is imperfect.

For each directional candidate, return one verdict object:
{
  "candidate_type": "directional_mismatch",
  "candidate_id": "Dir-01",
  "lp_ids": ["LP-XX"],
  "q2a_verdict": "yes | no | unclear",
  "q2b_verdict": "proportional | disproportionate | not_applicable",
  "verdict": "mismatch_confirmed | no_mismatch | unclear",
  "exposed_party": "tenant | landlord | bilateral",
  "disproportion_summary": "one sentence describing the imbalance if confirmed",
  "confidence": "high | medium | low"
}

Return a JSON array containing ALL verdict objects from ALL sections. Do not skip any candidate.
Response must start with [ and end with ]. No markdown fences."""


def _build_pass2_user_prompt(
    clusters: List[dict],
    relief_candidates: List[dict],
    directional_candidates: List[dict],
    flagged_lps: List[dict],
    perspective: str,
) -> str:
    """Build the Pass 2 combined compound + relief verification prompt."""
    lines = [f"PERSPECTIVE: {perspective.upper()}", ""]

    if clusters:
        lines += [
            f"SECTION 1 — COMPOUND RISK CANDIDATES ({len(clusters)} — evaluate every one, including those you did not flag in Pass 1).",
            "",
        ]
        for cluster in clusters:
            cid      = cluster["candidate_id"]
            pt       = cluster["pattern_type"]
            lps      = ", ".join(cluster["involved_lps"])
            found_by = ", ".join(f"Evaluator {r}" for r in cluster["found_by"])
            p1r      = cluster.get("pass1_responses", {})
            any_r    = next(iter(p1r.values()), {})
            desc     = any_r.get("why_the_combination_matters", "")
            evidence = any_r.get("evidence_from_lease", "")
            lines += [
                f"[{cid}] Pattern: {pt} | LPs: {lps}",
                f"Found by: {found_by}",
                f"Description: {desc}",
                f"Evidence: {evidence}",
                "",
            ]

    if relief_candidates:
        lines += [
            f"SECTION 2 — CROSS-COVERAGE RELIEF CANDIDATES ({len(relief_candidates)} — evaluate every one).",
            "Verify both: (1) does the cross-coverage exist? (2) does it run the correct direction?",
            "",
        ]
        for rc in relief_candidates:
            cid      = rc["candidate_id"]
            lp_id    = rc["lp_id"]
            lp_name  = rc["lp_name"]
            found_by = ", ".join(f"Evaluator {r}" for r in rc["found_by"])
            p1_any   = next(iter(rc.get("pass1_responses", {}).values()), {})
            section  = p1_any.get("relief_section", "")
            reason   = p1_any.get("q1_reasoning", "")
            lines += [
                f"[{cid}] LP: {lp_id} ({lp_name})",
                f"Found by: {found_by}",
                f"Proposed relief section: {section or '(see reasoning)'}",
                f"Pass 1 reasoning: {reason}",
                "",
            ]

    if directional_candidates:
        lines += [
            f"SECTION 3 — DIRECTIONAL MISMATCH CANDIDATES ({len(directional_candidates)} — evaluate every one).",
            "Use Q2a/Q2b structure. Do not assume the Pass 1 finding is correct.",
            "",
        ]
        for dc in directional_candidates:
            cid      = dc["candidate_id"]
            lp_ids   = ", ".join(dc["lp_ids"])
            found_by = ", ".join(f"Evaluator {r}" for r in dc["found_by"])
            p1_any   = next(iter(dc.get("pass1_responses", {}).values()), {})
            opp      = dc.get("opposing_framework_summary") or p1_any.get("opposing_framework_summary", "")
            weak     = dc.get("weaker_framework_summary") or p1_any.get("weaker_framework_summary", "")
            why      = dc.get("why_mismatch_matters") or p1_any.get("why_mismatch_matters", "")
            lines += [
                f"[{cid}] LPs: {lp_ids}",
                f"Found by: {found_by}",
                f"Stronger framework: {opp}",
                f"Weaker framework: {weak}",
                f"Why it matters: {why}",
                "",
            ]

    lines.append("Return a JSON array with one verdict object per candidate from ALL sections. Do not skip any.")
    return "\n".join(lines)


def _call_pass2_evaluator(
    role: str,
    ev_cfg: dict,
    user_prompt: str,
) -> dict:
    """Call one evaluator for Pass 2 compound risk verification.

    Returns: {role, model, provider, completed, verdicts (list), error, elapsed_sec}
    """
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.provider_health import get_health_tracker

    health     = get_health_tracker()
    start_time = time.time()
    provider   = ev_cfg["provider"]
    model      = ev_cfg["model"]
    fallback   = ev_cfg.get("fallback")

    def _try_call(p: str, m: str) -> list:
        if not health.is_available(p):
            raise RuntimeError(f"provider {p} degraded")
        target = ModelTarget(
            name=f"{p}:{m}-stage7-pass2-{role}",
            provider=p,
            model=m,
            max_output_tokens=ev_cfg["max_output_tokens"],
            temperature=ev_cfg["temperature"],
            timeout_sec=ev_cfg["timeout_sec"],
        )
        router  = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(p)
        raw     = adapter.call(_PASS2_EVALUATOR_SYSTEM, user_prompt, target).strip()
        parsed  = _safe_parse_synthesis(raw)
        if parsed is None:
            raise RuntimeError(f"Pass2 Eval-{role}: unparseable response")
        # Normalize to list (some models wrap in a dict)
        if isinstance(parsed, dict):
            for _val in parsed.values():
                if isinstance(_val, list):
                    parsed = _val
                    break
        if not isinstance(parsed, list):
            raise RuntimeError(f"Pass2 Eval-{role}: expected list, got {type(parsed)}")
        return parsed

    print(f"[lease_synthesis] Pass2 Eval-{role}: calling {model} ({provider})...", flush=True)
    try:
        verdicts = _try_call(provider, model)
        elapsed  = time.time() - start_time
        print(f"[lease_synthesis] Pass2 Eval-{role}: succeeded in {round(elapsed, 1)}s", flush=True)
        return {"role": role, "model": model, "provider": provider, "label": ev_cfg["label"],
                "completed": True, "verdicts": verdicts, "error": None,
                "elapsed_sec": round(elapsed, 2)}
    except Exception as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ["503", "connection", "refused", "unavailable", "resource_exhausted"]):
            health.mark_degraded(provider, reason=str(e)[:100])
        print(f"[lease_synthesis] Pass2 Eval-{role}: {model} FAILED ({type(e).__name__})", flush=True)
        if fallback:
            fb_provider, fb_model, fb_label = fallback
            print(f"[lease_synthesis] Pass2 Eval-{role}: trying fallback {fb_model}...", flush=True)
            try:
                verdicts = _try_call(fb_provider, fb_model)
                elapsed  = time.time() - start_time
                print(f"[lease_synthesis] Pass2 Eval-{role}: fallback succeeded in {round(elapsed, 1)}s", flush=True)
                return {"role": role, "model": fb_model, "provider": fb_provider, "label": fb_label,
                        "completed": True, "verdicts": verdicts, "error": None,
                        "elapsed_sec": round(elapsed, 2), "fallback_used": True}
            except Exception as e2:
                print(f"[lease_synthesis] Pass2 Eval-{role}: fallback FAILED ({type(e2).__name__})", flush=True)
                return {"role": role, "model": model, "completed": False,
                        "verdicts": [], "error": str(e2),
                        "elapsed_sec": round(time.time() - start_time, 2)}
        return {"role": role, "model": model, "completed": False,
                "verdicts": [], "error": str(e),
                "elapsed_sec": round(time.time() - start_time, 2)}


def _build_pass2_verified_findings(
    clusters: List[dict],
    pass2_outputs: Dict[str, dict],
) -> List[dict]:
    """Build verified compound findings from Pass 2 evaluator outputs.

    Agreement rules:
    - 3/3 compound_risk_present → HIGH severity, surface
    - 2/3 → surface at pattern base severity
    - 1/3 → surface LOW (minority signal — CAM never buries it)
    - 0/3 → drop
    """
    _severity_map = {
        "directional_asymmetry":  "HIGH",
        "lever_elimination":      "HIGH",
        "subordination_trap":     "MEDIUM",
        "cascading_no_remedy":    "HIGH",
        "operational_dead_end":   "MEDIUM",
    }

    # Index Pass 2 verdicts by candidate_id per role
    pass2_by_role: Dict[str, Dict[str, dict]] = {}
    for role, output in pass2_outputs.items():
        if not output.get("completed"):
            continue
        pass2_by_role[role] = {
            v.get("candidate_id", ""): v
            for v in (output.get("verdicts") or [])
            if v.get("candidate_id")
        }

    findings: List[dict] = []
    for cluster in clusters:
        cid          = cluster["candidate_id"]
        pattern_type = cluster["pattern_type"]
        involved_lps = cluster["involved_lps"]

        verdicts_by_role: Dict[str, str] = {}
        ev_details:        Dict[str, dict] = {}
        for role, by_cid in pass2_by_role.items():
            v = by_cid.get(cid, {})
            verdicts_by_role[role] = v.get("verdict", "unclear")
            ev_details[role] = v

        present_count    = sum(1 for v in verdicts_by_role.values() if v == "compound_risk_present")
        total_evaluators = len(pass2_by_role)

        if present_count == 0:
            # 0/3: either all said no, or Pass 2 failed entirely.
            # Either way — governed rejection, goes to audit trail only, not user output.
            continue

        # Best detail for headline/evidence: prefer a "present" response
        best = next((ev_details[r] for r in verdicts_by_role if verdicts_by_role[r] == "compound_risk_present"),
                    next(iter(ev_details.values()), {}))
        p1_any = next(iter(cluster.get("pass1_responses", {}).values()), {})

        headline = (best.get("reason") or p1_any.get("why_the_combination_matters") or "")[:160]
        detail   = best.get("lease_evidence") or p1_any.get("evidence_from_lease") or ""
        affected = best.get("affected_party") or p1_any.get("affected_party") or ""

        if present_count == 3:
            severity = "HIGH"
        elif present_count == 2:
            severity = _severity_map.get(pattern_type, "MEDIUM")
        else:
            severity = "LOW"

        ev_verdicts = {r: verdicts_by_role.get(r, "not_reported") for r in ("A", "B", "C")}
        agreement   = f"{present_count}-{3 - present_count}"

        findings.append({
            "finding_id":        cid,
            "finding_type":      "compound_risk",
            "implicated_lps":    involved_lps,
            "headline":          headline or f"Compound risk: {pattern_type.replace('_', ' ')}",
            "detail":            detail,
            "cited_sections":    [],
            "verdict":           "compound_risk_confirmed",
            "directionality":    None,
            "severity":          severity,
            "evaluator_agreement": agreement,
            "evaluator_verdicts":  ev_verdicts,
            "pattern_type":      pattern_type,
            "affected_party":    affected,
        })

    return findings


# ── Compound risk dedup helpers ───────────────────────────────────────────────

def _compound_signature(finding: dict) -> tuple:
    """Normalized identity key for compound risk dedup.

    Pass 2 CRX findings are canonical. If a consolidator CPF carries the same
    (sorted_lps, pattern_type, risk_mechanism, affected_party), the CPF is dropped.
    """
    lps = tuple(sorted(
        finding.get("involved_lps") or finding.get("implicated_lps") or []
    ))
    return (
        lps,
        finding.get("pattern_type", ""),
        finding.get("risk_mechanism", ""),
        finding.get("affected_party", ""),
    )


# ── Directionality normalization ───────────────────────────────────────────────

# Maps (lp_id, finding_type) → correct directionality label.
# Perspective must not flip the factual label of who is exposed.
_DIRECTIONALITY_MAP: Dict[tuple, str] = {
    ("LP-27", "directional_mismatch"): "tenant_unprotected",
}

# Maps (lp_id, finding_type) → correct affected_party label.
_AFFECTED_PARTY_MAP: Dict[tuple, str] = {
    ("LP-27", "directional_mismatch"): "tenant",
}


def _normalize_directionality(findings: List[dict]) -> List[dict]:
    """Enforce factually correct directionality and affected_party for known LP patterns."""
    for f in findings:
        ftype = f.get("finding_type", "")
        lps = tuple(sorted(f.get("implicated_lps") or []))
        for lp in lps:
            dir_key = (lp, ftype)
            if dir_key in _DIRECTIONALITY_MAP:
                f["directionality"] = _DIRECTIONALITY_MAP[dir_key]
            if dir_key in _AFFECTED_PARTY_MAP:
                f["affected_party"] = _AFFECTED_PARTY_MAP[dir_key]
    return findings


# ── Cross-coverage relief helpers ─────────────────────────────────────────────

def _collect_relief_candidates(evaluator_outputs: Dict[str, dict]) -> List[dict]:
    """Collect LP IDs where any Pass 1 evaluator returned cross_coverage_confirmed."""
    by_lp: Dict[str, dict] = {}
    for role, output in evaluator_outputs.items():
        if not output.get("completed"):
            continue
        result = output.get("result") or {}
        for cf in (result.get("cross_coverage_findings") or []):
            fv = cf.get("final_verdict") or cf.get("q1_verdict") or ""
            if fv != "cross_coverage_confirmed":
                continue
            lp_id = cf.get("lp_id", "")
            if not lp_id:
                continue
            if lp_id not in by_lp:
                by_lp[lp_id] = {
                    "lp_id":          lp_id,
                    "lp_name":        cf.get("lp_name", lp_id),
                    "found_by":       [],
                    "pass1_responses": {},
                }
            by_lp[lp_id]["found_by"].append(role)
            by_lp[lp_id]["pass1_responses"][role] = cf

    result: List[dict] = []
    for i, (_, data) in enumerate(by_lp.items()):
        data["candidate_id"] = f"RLF-{i + 1:02d}"
        result.append(data)
    return result


def _build_pass2_relief_findings(
    relief_candidates: List[dict],
    pass2_outputs: Dict[str, dict],
) -> List[dict]:
    """Build cross_coverage_relief findings from Pass 2 verdicts.

    Agreement rules (never suppress):
    - 3/3 or 2/3 confirmed + direction_adequate → full relief finding
    - 1/3 confirmed → minority relief finding (labelled)
    - 0/3 confirmed → drop
    - directional_false_positive by any evaluator → flag on finding
    """
    # Index relief verdicts by candidate_id per role
    p2_relief: Dict[str, Dict[str, dict]] = {}
    for role, output in pass2_outputs.items():
        if not output.get("completed"):
            continue
        p2_relief[role] = {}
        for v in (output.get("verdicts") or []):
            if v.get("candidate_type") == "cross_coverage_relief" or (
                v.get("candidate_id", "").startswith("RLF-")
            ):
                cid = v.get("candidate_id", "")
                if cid:
                    p2_relief[role][cid] = v

    findings: List[dict] = []
    for candidate in relief_candidates:
        cid     = candidate["candidate_id"]
        lp_id   = candidate["lp_id"]
        lp_name = candidate["lp_name"]

        verdicts_by_role: Dict[str, str] = {}
        details_by_role:  Dict[str, dict] = {}
        for role, by_cid in p2_relief.items():
            v = by_cid.get(cid, {})
            verdicts_by_role[role] = v.get("verdict", "unclear")
            details_by_role[role]  = v

        confirmed = sum(1 for v in verdicts_by_role.values() if v == "cross_coverage_confirmed")
        dfp_count = sum(1 for v in verdicts_by_role.values() if v == "directional_false_positive")
        total     = len(p2_relief)

        if confirmed == 0:
            # 0/3: either all said no, or Pass 2 failed entirely.
            # Governed rejection — do not surface in user output.
            continue

        # Best confirmed detail; fall back to any
        best = next(
            (details_by_role[r] for r in verdicts_by_role
             if verdicts_by_role[r] == "cross_coverage_confirmed" and details_by_role[r].get("direction_adequate")),
            next((details_by_role[r] for r in verdicts_by_role
                  if verdicts_by_role[r] == "cross_coverage_confirmed"), {})
        )
        p1_any = next(iter(candidate.get("pass1_responses", {}).values()), {})

        relief_section    = best.get("relief_section") or p1_any.get("relief_section", "")
        reason            = best.get("reason") or p1_any.get("q1_reasoning", "")
        direction         = best.get("direction", "")
        direction_adequate = best.get("direction_adequate", True)

        ev_verdicts = {r: verdicts_by_role.get(r, "not_reported") for r in ("A", "B", "C")}
        agreement   = f"{confirmed}-{3 - confirmed}"

        findings.append({
            "finding_id":        cid,
            "finding_type":      "cross_coverage_relief",
            "implicated_lps":    [lp_id],
            "headline":          f"Relief: {lp_name} substance found in {relief_section or 'another provision'}",
            "detail":            reason,
            "cited_sections":    [relief_section] if relief_section else [],
            "verdict":           "cross_coverage_confirmed",
            "directionality":    direction or None,
            "direction_adequate": direction_adequate,
            "relief_section":    relief_section,
            "severity":          "INFO",
            "evaluator_agreement": agreement,
            "evaluator_verdicts":  ev_verdicts,
            "directional_false_positive_count": dfp_count,
        })

    return findings


# ── Directional mismatch two-pass helpers ─────────────────────────────────────

def _collect_directional_candidates(evaluator_outputs: Dict[str, dict]) -> List[dict]:
    """Collect LPs where any Pass 1 evaluator raised mismatch_flag=True.

    Q2a/Q2b data is embedded in cross_coverage_findings entries (not a separate key).
    """
    by_sig: Dict[tuple, dict] = {}

    for role, output in evaluator_outputs.items():
        if not output.get("completed"):
            continue
        result = output.get("result") or {}
        # Q2a/Q2b fields are embedded directly in cross_coverage_findings entries
        for item in (result.get("cross_coverage_findings") or []):
            if item.get("mismatch_flag") is not True:
                continue
            lp_id  = item.get("lp_id", "")
            lp_ids = sorted(item.get("lp_ids", [lp_id] if lp_id else []))
            if not lp_ids:
                continue
            sig = tuple(lp_ids)
            if sig not in by_sig:
                by_sig[sig] = {
                    "lp_ids":                    lp_ids,
                    "found_by":                  [],
                    "pass1_responses":           {},
                    "exposed_party":             item.get("exposed_party", ""),
                    "opposing_framework_summary": item.get("opposing_framework_summary", ""),
                    "weaker_framework_summary":   item.get("weaker_framework_summary", ""),
                    "why_mismatch_matters":       item.get("why_mismatch_matters", ""),
                }
            by_sig[sig]["found_by"].append(role)
            by_sig[sig]["pass1_responses"][role] = item

    result: List[dict] = []
    for i, (_, data) in enumerate(by_sig.items()):
        data["candidate_id"] = f"Dir-{i + 1:02d}"
        result.append(data)
    return result


def _build_pass2_directional_findings(
    directional_candidates: List[dict],
    pass2_outputs: Dict[str, dict],
) -> List[dict]:
    """Build directional_mismatch findings from Pass 2 Q2 verdicts.

    Agreement: 3/3, 2/3, 1/3 mismatch_confirmed → surface.
    0/3 → governed rejection, suppress.
    """
    # Index directional verdicts by candidate_id per role
    p2_dir: Dict[str, Dict[str, dict]] = {}
    for role, output in pass2_outputs.items():
        if not output.get("completed"):
            continue
        p2_dir[role] = {}
        for v in (output.get("verdicts") or []):
            if v.get("candidate_type") == "directional_mismatch" or (
                (v.get("candidate_id") or "").startswith("Dir-")
            ):
                cid = v.get("candidate_id", "")
                if cid:
                    p2_dir[role][cid] = v

    findings: List[dict] = []
    for candidate in directional_candidates:
        cid    = candidate["candidate_id"]
        lp_ids = candidate["lp_ids"]

        verdicts_by_role: Dict[str, str] = {}
        details_by_role:  Dict[str, dict] = {}
        for role, by_cid in p2_dir.items():
            v = by_cid.get(cid, {})
            verdicts_by_role[role] = v.get("verdict", "unclear")
            details_by_role[role]  = v

        confirmed = sum(1 for v in verdicts_by_role.values() if v == "mismatch_confirmed")
        if confirmed == 0:
            continue  # Governed rejection

        best = next((details_by_role[r] for r in verdicts_by_role
                     if verdicts_by_role[r] == "mismatch_confirmed"), {})

        exposed_party = best.get("exposed_party") or candidate.get("exposed_party", "")
        disproportion = best.get("disproportion_summary") or candidate.get("why_mismatch_matters", "")
        headline      = (candidate.get("weaker_framework_summary") or
                         f"Directional mismatch: {', '.join(lp_ids)}")[:160]

        directionality = None
        ep = (exposed_party or "").lower()
        if "tenant" in ep:
            directionality = "tenant_unprotected"
        elif "landlord" in ep:
            directionality = "landlord_unprotected"

        ev_verdicts = {r: verdicts_by_role.get(r, "not_reported") for r in ("A", "B", "C")}
        agreement   = f"{confirmed}-{3 - confirmed}"
        severity    = "HIGH" if confirmed == 3 else "MEDIUM" if confirmed == 2 else "LOW"

        findings.append({
            "finding_id":          cid,
            "finding_type":        "directional_mismatch",
            "implicated_lps":      lp_ids,
            "headline":            headline,
            "detail":              disproportion,
            "cited_sections":      [],
            "verdict":             "directional_mismatch",
            "directionality":      directionality,
            "severity":            severity,
            "evaluator_agreement": agreement,
            "evaluator_verdicts":  ev_verdicts,
        })

    return _normalize_directionality(findings)


_NOT_REPORTED = frozenset({"not_reported", "not_identified", "none", "n/a", "", "unknown"})


def _compute_agreement(evaluator_verdicts: dict, final_verdict: str = "") -> str:
    """Count evaluators whose verdict matches the final verdict's semantic group.

    Semantic groups:
    - positive:  full_coverage_found, cross_coverage_confirmed
    - partial:   partial_coverage_found
    - negative:  no_coverage_found, directional_false_positive
    - compound:  compound_risk_present, compound_risk_confirmed

    Returns "X-Y" where X = matching final_group, Y = non-matching.
    Example: A=no_coverage, B=no_coverage, C=full_coverage, final=no_coverage → "2-1"
    """
    if not evaluator_verdicts:
        return "0-3"

    def _group(v: str) -> str:
        v = (v or "").lower()
        if v in _NOT_REPORTED:
            return "not_reported"
        if v in ("full_coverage_found", "cross_coverage_confirmed"):
            return "positive"
        if v in ("partial_coverage_found",):
            return "partial"
        if v in ("no_coverage_found", "directional_false_positive"):
            return "negative"
        if v in ("compound_risk_present", "compound_risk_confirmed"):
            return "compound"
        return "other"

    substantive = {role: v for role, v in evaluator_verdicts.items()
                   if _group(v) != "not_reported"}
    if not substantive:
        return "0-3"

    final_group = _group(final_verdict)
    if final_group in ("not_reported", "other"):
        # No meaningful final verdict — report substantive count only
        return f"{len(substantive)}-{max(0, 3 - len(substantive))}"

    matching = sum(1 for v in substantive.values() if _group(v) == final_group)
    return f"{matching}-{len(substantive) - matching}"


def _normalize_findings(
    consolidated: dict,
    evaluator_raw: Dict[str, Optional[dict]],
) -> List[dict]:
    """Extract and normalize cross_provision_findings from consolidator output."""
    raw_findings = consolidated.get("cross_provision_findings") or []
    if not isinstance(raw_findings, list):
        return []

    out = []
    for i, f in enumerate(raw_findings):
        if not isinstance(f, dict):
            continue
        finding_id = f.get("finding_id") or f"CPF-{i + 1:02d}"
        finding_type = f.get("finding_type") or "cross_coverage_gap"
        implicated = f.get("implicated_lps") or []
        headline = (f.get("headline") or "").strip()
        detail   = (f.get("detail") or "").strip()
        cited    = f.get("cited_sections") or []
        verdict  = f.get("verdict") or "no_coverage_found"
        direc    = f.get("directionality")
        severity = (f.get("severity") or "MEDIUM").upper()
        ev_ag    = f.get("evaluator_agreement") or ""
        ev_verd  = f.get("evaluator_verdicts") or {}

        # Rebuild evaluator_verdicts from raw if missing
        if not ev_verd:
            for role, raw in evaluator_raw.items():
                if not raw:
                    continue
                if finding_type == "compound_risk":
                    # Compound risk verdicts come from compound_risks[], not cross_coverage_findings[]
                    crs = raw.get("compound_risks") or []
                    for cr in crs:
                        cr_lps = set(cr.get("implicated_lp_ids") or [])
                        if cr_lps & set(implicated):
                            ev_verd[role] = "compound_risk_confirmed"
                            break
                else:
                    for lp_id in implicated:
                        for cf in (raw.get("cross_coverage_findings") or []):
                            if cf.get("lp_id") == lp_id:
                                ev_verd[role] = cf.get("final_verdict") or cf.get("q1_verdict", "unknown")
                                break

        # Recompute evaluator_agreement using semantic grouping against the final verdict.
        # _compute_agreement() is authoritative; discard whatever the consolidator reported.
        if ev_verd:
            ev_ag = _compute_agreement(ev_verd, verdict)

        out_f: dict = {
            "finding_id": finding_id,
            "finding_type": finding_type,
            "implicated_lps": implicated,
            "headline": headline,
            "detail": detail,
            "cited_sections": cited,
            "verdict": verdict,
            "directionality": direc,
            "severity": severity,
            "evaluator_agreement": ev_ag,
            "evaluator_verdicts": ev_verd,
        }
        # Pass through relief/compound-specific fields when present
        for _extra in ("relief_section", "direction_adequate", "pattern_type",
                       "affected_party", "directional_false_positive_count"):
            if f.get(_extra) is not None:
                out_f[_extra] = f[_extra]
        out.append(out_f)

    return out


def run_synthesis(
    full_tenant_text: str,
    coverage_assessment: List[dict],
    conflicts: List[dict],
    perspective: str = "tenant",
    cfg: dict = None,
) -> dict:
    """Run Stage 7 cross-provision synthesis.

    Args:
        full_tenant_text: Full lease text (already parsed).
        coverage_assessment: Output of lease_coverage.py (list of assessment dicts).
        conflicts: Output of lease_conflicts.py (list of conflict dicts).
        perspective: "tenant" | "landlord" | "neutral"
        cfg: Pipeline config dict (for cancel check, etc.)

    Returns:
        {
          "cross_provision_findings": [...],
          "meta": { ... timing, model info ... }
        }
    """
    start_time = time.time()

    # ── Identify flagged LPs ──
    flagged_lps = _collect_flagged_lps(coverage_assessment, conflicts)

    if not flagged_lps:
        print("[lease_synthesis] No flagged LPs — Stage 7 skipped", flush=True)
        return {
            "cross_provision_findings": [],
            "meta": {
                "skipped": True,
                "skip_reason": "no_flagged_lps",
                "elapsed_sec": round(time.time() - start_time, 2),
            },
        }

    print(f"[lease_synthesis] Stage 7: {len(flagged_lps)} flagged LPs, "
          f"running 3 evaluators in parallel...", flush=True)
    for lp in flagged_lps:
        print(f"[lease_synthesis]   {lp['lp_id']}: {lp['lp_name']} ({lp['coverage_state']})",
              flush=True)

    # ── Build user prompt (same for all evaluators) ──
    user_prompt = _build_evaluator_user_prompt(flagged_lps, full_tenant_text, perspective, coverage_assessment)

    # ── Run three evaluators in parallel (Pass 1) ──
    # Eval-B uses gpt-5.4 here — gpt-5.5 fails on long Pass 1 prompt.
    # Pass 2 uses EVALUATOR_LINEUP (gpt-5.5 succeeds on short cluster prompt).
    evaluator_outputs: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_call_single_evaluator, role, ev_cfg, user_prompt): role
            for role, ev_cfg in _EVALUATOR_LINEUP_PASS1.items()
        }
        for fut in as_completed(futures):
            role = futures[fut]
            try:
                evaluator_outputs[role] = fut.result()
            except Exception as e:
                evaluator_outputs[role] = {
                    "role": role, "completed": False,
                    "result": None, "error": str(e),
                }

    completed_count = sum(1 for v in evaluator_outputs.values() if v.get("completed"))
    print(f"[lease_synthesis] {completed_count}/3 evaluators completed", flush=True)
    _b = evaluator_outputs.get("B", {})
    print(f"[synth_debug] Eval-B: model={_b.get('model')}, elapsed={_b.get('elapsed_sec')}s, fallback={_b.get('fallback_used')}, error={_b.get('error')}", flush=True)

    if completed_count == 0:
        return {
            "cross_provision_findings": [],
            "meta": {
                "skipped": True,
                "skip_reason": "all_evaluators_failed",
                "elapsed_sec": round(time.time() - start_time, 2),
                "evaluator_errors": {
                    role: v.get("error") for role, v in evaluator_outputs.items()
                },
            },
        }

    # ── Pass 2: cluster compound candidates + collect relief candidates ──
    for role, v in evaluator_outputs.items():
        if v.get("completed"):
            n_cands = len((v.get("result") or {}).get("candidates") or [])
            print(f"[synth_debug] Eval-{role}: {n_cands} candidate(s) in candidates[]", flush=True)

    pass1_for_clustering = {
        role: {"candidates": (v.get("result") or {}).get("candidates", [])}
        for role, v in evaluator_outputs.items()
        if v.get("completed")
    }
    clusters               = _cluster_compound_candidates(pass1_for_clustering)
    relief_candidates      = _collect_relief_candidates(evaluator_outputs)
    directional_candidates = _collect_directional_candidates(evaluator_outputs)
    print(
        f"[lease_synthesis] Compound clusters: {len(clusters)}, "
        f"Relief candidates: {len(relief_candidates)}, "
        f"Directional candidates: {len(directional_candidates)}",
        flush=True,
    )

    verified_compound_findings:    List[dict] = []
    verified_relief_findings:      List[dict] = []
    verified_directional_findings: List[dict] = []
    pass2_outputs: Dict[str, dict] = {}

    if clusters or relief_candidates or directional_candidates:
        n_items = len(clusters) + len(relief_candidates) + len(directional_candidates)
        print(f"[lease_synthesis] Pass 2: {n_items} item(s), running 3 evaluators...", flush=True)
        pass2_prompt = _build_pass2_user_prompt(
            clusters, relief_candidates, directional_candidates, flagged_lps, perspective
        )
        with ThreadPoolExecutor(max_workers=3) as pool2:
            p2futures = {
                pool2.submit(_call_pass2_evaluator, role, ev_cfg, pass2_prompt): role
                for role, ev_cfg in EVALUATOR_LINEUP.items()
            }
            for fut in as_completed(p2futures):
                role = p2futures[fut]
                try:
                    pass2_outputs[role] = fut.result()
                except Exception as e:
                    pass2_outputs[role] = {"role": role, "completed": False, "verdicts": [], "error": str(e)}
        p2_done = sum(1 for v in pass2_outputs.values() if v.get("completed"))
        print(f"[lease_synthesis] Pass 2: {p2_done}/3 evaluators completed", flush=True)
        if clusters:
            verified_compound_findings = _build_pass2_verified_findings(clusters, pass2_outputs)
            print(f"[lease_synthesis] Pass 2: {len(verified_compound_findings)} verified compound finding(s)", flush=True)
        if relief_candidates:
            verified_relief_findings = _build_pass2_relief_findings(relief_candidates, pass2_outputs)
            print(f"[lease_synthesis] Pass 2: {len(verified_relief_findings)} verified relief finding(s)", flush=True)
        if directional_candidates:
            verified_directional_findings = _build_pass2_directional_findings(directional_candidates, pass2_outputs)
            print(f"[lease_synthesis] Pass 2: {len(verified_directional_findings)} verified directional finding(s)", flush=True)
    else:
        print("[lease_synthesis] No candidates — Pass 2 skipped", flush=True)

    # ── Consolidation pass ──
    evaluator_raw = {
        role: v.get("result") for role, v in evaluator_outputs.items()
    }

    print("[lease_synthesis] Running consolidation pass...", flush=True)
    consolidated = _call_consolidator(
        evaluator_raw, flagged_lps, perspective,
        verified_compound_findings, verified_relief_findings
        # Note: directional findings are added directly — consolidator handles Q1/Q2 only
    )

    if not consolidated:
        # Fallback: use Evaluator B's output directly if consolidation failed
        print("[lease_synthesis] Consolidation failed — falling back to Evaluator B output", flush=True)
        b_result = evaluator_raw.get("B") or {}
        # Build minimal findings from B's raw output
        findings = []
        for i, cf in enumerate((b_result.get("cross_coverage_findings") or [])[:20]):
            if not isinstance(cf, dict):
                continue
            final_v = cf.get("final_verdict") or cf.get("q1_verdict") or "no_coverage_found"
            if final_v == "full_coverage_found" and cf.get("q2_verdict") != "directional_mismatch":
                continue  # Skip fully-covered, correctly-directioned LPs
            ftype = "cross_coverage_gap"
            if cf.get("q2_verdict") == "directional_mismatch":
                ftype = "directional_mismatch"
            findings.append({
                "finding_id": f"CPF-{i + 1:02d}",
                "finding_type": ftype,
                "implicated_lps": [cf.get("lp_id", "")],
                "headline": cf.get("q1_reasoning", "")[:120],
                "detail": cf.get("q1_reasoning", ""),
                "cited_sections": cf.get("q2_cited_sections") or cf.get("q1_cited_sections") or [],
                "verdict": final_v,
                "directionality": None,
                "severity": cf.get("severity", "MEDIUM"),
                "evaluator_agreement": "1-2",
                "evaluator_verdicts": {"A": "unknown", "B": final_v, "C": "unknown"},
            })
        # Add pre-verified compound, relief, and directional findings from Pass 2
        for vcf in verified_compound_findings:
            findings.append(dict(vcf))
        for vrf in verified_relief_findings:
            findings.append(dict(vrf))
        for vdf in verified_directional_findings:
            findings.append(dict(vdf))
        consolidated = {"cross_provision_findings": findings}

    findings = _normalize_findings(consolidated, evaluator_raw)

    # Ensure all verified compound and relief findings appear in the final output.
    # The consolidator is instructed to include them verbatim, but may not always comply.
    existing_ids = {f.get("finding_id") for f in findings}
    for vcf in verified_compound_findings:
        if vcf.get("finding_id") not in existing_ids:
            findings.append(dict(vcf))
    for vrf in verified_relief_findings:
        if vrf.get("finding_id") not in existing_ids:
            findings.append(dict(vrf))
    for vdf in verified_directional_findings:
        if vdf.get("finding_id") not in existing_ids:
            findings.append(dict(vdf))

    # Dedup: CRX-prefixed Pass 2 findings are canonical compound risk output.
    # Drop any consolidator compound_risk entries that cover the same normalized signature.
    crx_signatures = {
        _compound_signature(f)
        for f in findings
        if (f.get("finding_id") or "").startswith("CRX-")
    }
    if crx_signatures:
        pre_dedup = len(findings)
        findings = [
            f for f in findings
            if not (
                f.get("finding_type") == "compound_risk"
                and not (f.get("finding_id") or "").startswith("CRX-")
                and _compound_signature(f) in crx_signatures
            )
        ]
        dropped = pre_dedup - len(findings)
        if dropped:
            print(f"[lease_synthesis] Dedup: dropped {dropped} consolidator compound duplicate(s)", flush=True)

    # Normalize directionality and affected_party for known LP-pattern combinations.
    # Perspective must not flip the factual label of who is exposed.
    findings = _normalize_directionality(findings)

    elapsed = time.time() - start_time
    print(f"[lease_synthesis] Stage 7 complete: {len(findings)} findings in {round(elapsed, 1)}s",
          flush=True)

    # Count actual model calls: each evaluator invocation is 1 call; fallback adds 1 more.
    def _call_count(outputs: dict) -> int:
        return sum(1 + (1 if v.get("fallback_used") else 0)
                   for v in outputs.values() if v.get("model"))

    _pass2_ran = bool(clusters or relief_candidates or directional_candidates)
    _synth_api_calls = (
        _call_count(evaluator_outputs)                         # Pass 1
        + (_call_count(pass2_outputs) if _pass2_ran else 0)   # Pass 2 if it ran
        + 1                                                    # consolidation minimum
    )

    return {
        "cross_provision_findings": findings,
        "meta": {
            "skipped": False,
            "flagged_lp_count": len(flagged_lps),
            "finding_count": len(findings),
            "evaluators_completed": completed_count,
            "elapsed_sec": round(elapsed, 2),
            "api_calls": _synth_api_calls,
            "models": {
                role: {
                    "model": v.get("model", ""),
                    "provider": v.get("provider", ""),
                    "completed": v.get("completed", False),
                    "elapsed_sec": v.get("elapsed_sec", 0),
                }
                for role, v in evaluator_outputs.items()
            },
        },
    }
