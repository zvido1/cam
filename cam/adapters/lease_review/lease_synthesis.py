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
        "max_output_tokens": 4000,
        "temperature": 0.0,
        "timeout_sec": 300.0,
    },
    "B": {
        "provider": EVALUATOR_B_PRIMARY[0],
        "model":    EVALUATOR_B_PRIMARY[1],
        "label":    EVALUATOR_B_LABEL,
        "fallback": (EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], EVALUATOR_B_FALLBACK_LABEL),
        "max_output_tokens": 4000,
        "temperature": 0.0,
        "timeout_sec": 300.0,
    },
    "C": {
        "provider": EVALUATOR_C_PRIMARY[0],
        "model":    EVALUATOR_C_PRIMARY[1],
        "label":    EVALUATOR_C_LABEL,
        "fallback": None,  # grok-3 retired 2026-05-15; no same-provider fallback
        "max_output_tokens": 4000,
        "temperature": 0.0,
        "timeout_sec": 300.0,
    },
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
For each flagged LP: is this protection actually supplied elsewhere in the lease, in a
different article or section not captured by the LP's primary coverage area?

For each LP return one object in cross_coverage_findings[]:
{
  "lp_id": "LP-XX",
  "lp_name": "...",
  "q1_verdict": "no_coverage_found" | "partial_coverage_found" | "full_coverage_found",
  "q1_cited_sections": ["Article 15", ...],  // empty only if no relevant language found anywhere
  "q1_reasoning": "...",
  "q2_applicable": true | false,  // true if q1_verdict is partial or full, OR if you found relevant language but ultimately rejected it
  "q2_verdict": "directional_match" | "directional_mismatch" | null,
  "q2_direction_note": "...",  // explain which direction the found provision runs
  "q2_cited_sections": ["Article 15", ...],
  "final_verdict": "no_coverage_found" | "partial_coverage_found" | "full_coverage_found",
  "directionality": "tenant_unprotected" | "landlord_unprotected" | "match" | null,
  "severity": "HIGH" | "MEDIUM" | "LOW"
}

--- QUESTION 2: DIRECTIONALITY CHECK ---
Apply the directionality check whenever you locate relevant language — even if you
ultimately conclude it does not satisfy the LP. If you found language that superficially
resembles the missing provision but runs in the wrong direction for the party who needs
protection, return:
  q2_applicable: true
  q2_verdict: "directional_mismatch"
  final_verdict: "no_coverage_found"
  directionality: "[party]_unprotected"
and cite the misdirected language specifically in q2_cited_sections.

For each LP where Q1 found coverage (partial or full):
Does the provision found actually protect the implicated party in the correct direction?

Example: Article 15 may contain cure language. Q1 finds it.
Q2 asks: does this cure period protect the TENANT against LANDLORD default,
or does it protect the LANDLORD against TENANT default?
If directional mismatch: override final_verdict to "no_coverage_found".

CURE PERIOD AND REMEDY LP GUIDANCE:
For LP-27 (Landlord Default) and any LP involving cure periods, notice requirements,
or remedies: if you find such language elsewhere in the lease but conclude it does not
cover this LP, explicitly state whether it runs in favor of Landlord (against Tenant)
or Tenant (against Landlord). If it runs in the wrong direction, set q2_applicable true,
q2_verdict "directional_mismatch", directionality "[party]_unprotected", and cite the
misdirected sections — even when final_verdict is "no_coverage_found". Do NOT leave
directionality null when you located cure or remedy language in the wrong direction.

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
            f"PRE-VERIFIED COMPOUND FINDINGS ({len(verified_compound_findings)} — include these verbatim as compound_risk entries, do not re-evaluate):",
            json.dumps(verified_compound_findings, indent=2),
            "",
        ]
    else:
        lines += ["PRE-VERIFIED COMPOUND FINDINGS: none (no compound risk clusters confirmed in Pass 2).", ""]
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
) -> Optional[dict]:
    """Run consolidation pass using Evaluator B as consolidator."""
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.provider_health import get_health_tracker

    health = get_health_tracker()
    ev_cfg = EVALUATOR_LINEUP["B"]
    user_prompt = _build_consolidator_user_prompt(
        evaluator_results, flagged_lps, perspective, verified_compound_findings
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
    model    = ev_cfg["model"]
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


_PASS2_EVALUATOR_SYSTEM = """You are a commercial real estate attorney verifying compound risk findings.

Compound risk candidates have been identified from a first-pass analysis. Your task:
evaluate every candidate and return a verdict on whether the compound risk is real.

COVERAGE STATE IS NOT RISK STATE. A provision can be fully covered and still participate
in compound risk through asymmetry, missing reciprocal rights, or removal of practical
enforcement mechanisms.

For each candidate, return one verdict object:
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

Return a JSON array — one object per candidate. Do not skip any candidate.
Response must start with [ and end with ]. No markdown fences."""


def _build_pass2_user_prompt(
    clusters: List[dict],
    flagged_lps: List[dict],
    perspective: str,
) -> str:
    """Build the Pass 2 compound risk verification prompt."""
    lines = [
        f"PERSPECTIVE: {perspective.upper()}",
        "",
        f"COMPOUND RISK CANDIDATES ({len(clusters)} — evaluate every one, including those you did not flag in Pass 1).",
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
    lines.append("Return a JSON array with one verdict object per candidate. Do not skip any.")
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

        if total_evaluators > 0 and present_count == 0:
            continue  # All three looked at it and said no — drop

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


_NOT_REPORTED = frozenset({"not_reported", "not_identified", "none", "n/a", "", "unknown"})


def _compute_agreement(evaluator_verdicts: dict) -> str:
    """Count evaluators who produced a substantive finding (not a not_reported variant)."""
    if not evaluator_verdicts:
        return "0-3"
    reported = sum(
        1 for v in evaluator_verdicts.values()
        if v and str(v).lower() not in _NOT_REPORTED
    )
    not_reported = max(0, 3 - reported)
    return f"{reported}-{not_reported}"


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

        # Recompute evaluator_agreement by counting substantive (non-not_reported) verdicts.
        # _compute_agreement() is authoritative; discard whatever the consolidator reported.
        if ev_verd:
            ev_ag = _compute_agreement(ev_verd)

        out.append({
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
        })

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

    # ── Run three evaluators in parallel ──
    evaluator_outputs: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_call_single_evaluator, role, ev_cfg, user_prompt): role
            for role, ev_cfg in EVALUATOR_LINEUP.items()
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

    # ── Pass 2: cluster compound candidates and verify ──
    pass1_for_clustering = {
        role: {"candidates": (v.get("result") or {}).get("candidates", [])}
        for role, v in evaluator_outputs.items()
        if v.get("completed")
    }
    clusters = _cluster_compound_candidates(pass1_for_clustering)
    print(f"[lease_synthesis] Compound clusters: {len(clusters)}", flush=True)

    verified_compound_findings: List[dict] = []
    if clusters:
        print(f"[lease_synthesis] Pass 2: {len(clusters)} cluster(s), running 3 evaluators...", flush=True)
        pass2_prompt = _build_pass2_user_prompt(clusters, flagged_lps, perspective)
        pass2_outputs: Dict[str, dict] = {}
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
        verified_compound_findings = _build_pass2_verified_findings(clusters, pass2_outputs)
        print(f"[lease_synthesis] Pass 2: {len(verified_compound_findings)} verified compound finding(s)", flush=True)
    else:
        print("[lease_synthesis] No compound clusters — Pass 2 skipped", flush=True)

    # ── Consolidation pass ──
    evaluator_raw = {
        role: v.get("result") for role, v in evaluator_outputs.items()
    }

    print("[lease_synthesis] Running consolidation pass...", flush=True)
    consolidated = _call_consolidator(evaluator_raw, flagged_lps, perspective, verified_compound_findings)

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
        # Add pre-verified compound findings from Pass 2
        for vcf in verified_compound_findings:
            findings.append(dict(vcf))
        consolidated = {"cross_provision_findings": findings}

    findings = _normalize_findings(consolidated, evaluator_raw)

    # Ensure all verified compound findings appear in the final output.
    # The consolidator is instructed to include them verbatim, but may not always comply.
    existing_ids = {f.get("finding_id") for f in findings}
    for vcf in verified_compound_findings:
        if vcf.get("finding_id") not in existing_ids:
            findings.append(dict(vcf))

    elapsed = time.time() - start_time
    print(f"[lease_synthesis] Stage 7 complete: {len(findings)} findings in {round(elapsed, 1)}s",
          flush=True)

    return {
        "cross_provision_findings": findings,
        "meta": {
            "skipped": False,
            "flagged_lp_count": len(flagged_lps),
            "finding_count": len(findings),
            "evaluators_completed": completed_count,
            "elapsed_sec": round(elapsed, 2),
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
