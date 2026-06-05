#!/usr/bin/env python3
"""
375E-COV-A1 Consequence-Independence Diagnostic Harness
Step 375E-COV-A1 — Tests whether the COV-A finding-scoped 5e prompt contaminates
consequence assessment by handing over adversarial framing (tenant_unprotected,
adverse, exposure-flavored titles) to evaluators.

Panel: 4 findings x 3 prompt variants x 3 evaluators = 36 evaluator calls.

Findings:
  Dir-05 / LP-05  Permitted Use        (regenerated -- was beneficial, now harmful)
  Dir-12 / LP-15  Signage Rights       (lone neutral -- calibrates bias strength)
  Dir-15 / LP-20  Exclusivity          (known wobbler -- separates bias from instability)
  Dir-10 / LP-11  Default & Remedies   (thin-gap harmful -- 15/17 elements present)

Variants:
  A  Current COV-A prompt: hands over Stage 7 title/direction/tenant_unprotected/detail
  B  Direction-redacted: clause facts + use profile only; no adverse framing
  C  Explicit-independence: include finding but instruct not to infer harm from direction

Read:
  B/C yield neutral/beneficial where A is harmful -> CONTAMINATION CONFIRMED -> fix prompt before push
  All variants stay harmful                       -> Genuine; distribution is the lease, not the prompt
  Chaotic across variants                         -> Unstable per-finding; bigger finding needed

Usage (Tzvi runs):
  python build_log/_375ecova1_diagnostic.py

Writes:
  build_log/375E-COV-A1_results.md
  build_log/375E-COV-A1_raw_results.json
"""

import json
import os
import sys
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
ARTIFACT_PATH = os.path.join(
    REPO_ROOT,
    "05 Lease Analyzer", "results",
    "lease_review_20260605_174504_19f9a7",
    "tenant_0", "pipeline_results.json",
)

# Panel: (finding_id, lp_id, lp_name)
PANEL = [
    ("Dir-05", "LP-05", "Permitted Use"),
    ("Dir-12", "LP-15", "Signage Rights"),
    ("Dir-15", "LP-20", "Exclusivity"),
    ("Dir-10", "LP-11", "Default & Remedies"),
]

VALID_UC = {"beneficial", "neutral", "harmful", "context_dependent"}
VALID_MAT = {"high", "medium", "low", "not_applicable"}


# ── System prompts ────────────────────────────────────────────────────────────

# Variant A: current COV-A prompt (as shipped in lease_finding_consequence.py)
SYSTEM_PROMPT_A = """You are a commercial real estate attorney assessing how a lease provision directional finding affects a specific tenant's operations.

Stage 7 cross-provision analysis has already established that a directional mismatch exists -- the landlord's lease terms are adverse to the tenant's protected position on each listed provision. The finding direction is FIXED. DO NOT reassess whether each finding is valid or whether the direction is correct. Accept the adverse direction as a settled fact.

Your role is to assess ONLY:
1. use_consequence: given THIS tenant's specific use of the space, how consequential is the adverse direction in practice?
2. materiality: how significant is this finding for THIS tenant's core business operations?

Return a JSON object with one key per LP ID (e.g. "LP-05", "LP-15"):
{
  "LP-XX": {
    "use_consequence": "beneficial" | "neutral" | "harmful" | "context_dependent",
    "materiality": "high" | "medium" | "low" | "not_applicable",
    "use_reasoning": "One sentence grounding the assessment in the tenant's specific use -- not generic lease risk."
  }
}

Definitions:
  use_consequence:
    harmful:           The adverse finding creates meaningful practical risk or cost for this tenant given their use
    neutral:           The finding has little practical effect on this tenant's operations despite the adverse direction
    beneficial:        Despite the adverse direction in the abstract, the finding is net-positive for this tenant
                       given their specific use (requires a concrete operational justification)
    context_dependent: Cannot determine without more information about this tenant's specific situation

  materiality:
    high:           Directly affects the tenant's core business operations or creates significant financial exposure
    medium:         Relevant but not operationally critical for this specific tenant
    low:            Minor relevance to this tenant's use case
    not_applicable: This provision is irrelevant to this tenant's specific use and operations

Rules:
  - DO NOT question or re-examine the directional finding -- accept it as given
  - "harmful because the direction is adverse" is not sufficient -- ground the answer in what this means for THIS tenant's specific use type
  - Must return a verdict for every LP ID listed -- no omissions
  - Return only the JSON object, no markdown fences"""


# Variant B: direction-redacted -- clause facts + use profile only, no adverse framing
SYSTEM_PROMPT_B = """You are a commercial real estate attorney assessing how specific lease provision gaps affect a tenant's day-to-day operations.

For each listed provision, assess:
1. use_consequence: given THIS tenant's specific business and operational context, what is the practical consequence of this gap or uncertainty?
2. materiality: how significant is this for THIS tenant's core business operations?

Return a JSON object with one key per LP ID:
{
  "LP-XX": {
    "use_consequence": "beneficial" | "neutral" | "harmful" | "context_dependent",
    "materiality": "high" | "medium" | "low" | "not_applicable",
    "use_reasoning": "One sentence grounding the assessment in the tenant's specific use -- not generic lease risk."
  }
}

Definitions:
  use_consequence:
    beneficial:        The gap or uncertainty is net-positive for this tenant given their use
                       (e.g., absence of a restriction gives MORE operational freedom)
    neutral:           The gap has little practical effect on this tenant's operations
    harmful:           The gap creates meaningful risk, cost, or constraint for this tenant given their use
    context_dependent: Cannot determine without more information about this tenant's specific situation

  materiality:
    high:           Directly affects the tenant's core business operations or creates significant financial exposure
    medium:         Relevant but not operationally critical for this specific tenant
    low:            Minor relevance to this tenant's use case
    not_applicable: This provision is irrelevant to this tenant's specific use and operations

Rules:
  - Absence does NOT equal adverse by default. Ask: does this gap give the tenant MORE freedom or MORE exposure?
  - For an operational tenant (warehousing, distribution, light assembly): a missing restriction may mean
    the landlord CANNOT restrict the tenant's activities -- that is favorable, not adverse
  - Ground every answer in THIS tenant's specific business type and operational dependencies
  - Must return a verdict for every LP ID listed -- no omissions
  - Return only the JSON object, no markdown fences"""


# Variant C: explicit-independence -- finding included but independence instruction added
SYSTEM_PROMPT_C = """You are a commercial real estate attorney assessing how a lease provision finding affects a specific tenant's operations.

Stage 7 cross-provision analysis has flagged a structural concern for each listed provision. Your role is to assess use_consequence and materiality.

INDEPENDENCE REQUIREMENT: Do NOT infer harmfulness from the fact that a directional concern was flagged.
A structurally adverse gap may have beneficial, neutral, or harmful use consequence for this specific tenant.
The adverse direction is a structural observation about the lease; whether that structure actually harms THIS
tenant's operations is a separate question that depends on their specific use. Assess consequence independently
of the direction label.

Return a JSON object with one key per LP ID:
{
  "LP-XX": {
    "use_consequence": "beneficial" | "neutral" | "harmful" | "context_dependent",
    "materiality": "high" | "medium" | "low" | "not_applicable",
    "use_reasoning": "One sentence grounding the assessment in the tenant's specific use -- not generic lease risk."
  }
}

Definitions:
  use_consequence:
    beneficial:        The gap or concern is net-positive for this tenant given their specific use
    neutral:           The concern has little practical effect on this tenant's operations
    harmful:           The concern creates meaningful practical risk or cost for this tenant given their use
    context_dependent: Cannot determine without more information

  materiality:
    high:           Directly affects the tenant's core business operations or creates significant financial exposure
    medium:         Relevant but not operationally critical for this specific tenant
    low:            Minor relevance to this tenant's use case
    not_applicable: This provision is irrelevant to this tenant's specific use and operations

Rules:
  - Independently assess each provision: a finding that is structurally adverse may still be neutral or beneficial
    for THIS tenant's specific use case
  - "harmful because a concern was found" is NOT acceptable reasoning -- ground the answer in operational impact
  - Must return a verdict for every LP ID listed -- no omissions
  - Return only the JSON object, no markdown fences"""


# ── User prompt builders ──────────────────────────────────────────────────────

def _use_profile_context(use_profile: dict) -> str:
    biz = use_profile.get("business_type") or "unspecified"
    deps = use_profile.get("operational_dependencies") or []
    other = use_profile.get("other_use_risk_factors") or []
    lines = [
        "TENANT USE CONTEXT:",
        "  Business type: %s" % biz,
    ]
    if deps:
        lines.append("  Key operational dependencies: " + "; ".join(str(d) for d in deps))
    if other:
        lines.append("  Other risk factors: " + "; ".join(str(r) for r in other))
    return "\n".join(lines)


def build_variant_a_prompt(panel_data: list, use_profile: dict) -> str:
    """Variant A: current COV-A finding-scoped prompt with direction FIXED."""
    lines = [
        "PERSPECTIVE: TENANT",
        "",
        _use_profile_context(use_profile),
        "",
        "DIRECTIONAL FINDINGS TO ASSESS:",
        "(Direction is FIXED as adverse/tenant_unprotected per Stage 7 analysis. "
        "DO NOT re-examine direction.)",
        "",
    ]
    for fid, lp_id, lp_name, finding, lp in panel_data:
        headline = (finding.get("headline") or "").strip()
        detail = (finding.get("detail") or "").strip()
        title = (finding.get("title") or "").strip()
        lines.append("  %s [LP: %s -- %s]" % (lp_id, lp_id, lp_name))
        lines.append("    Finding title: %s" % title)
        lines.append("    Stage 7 finding (FIXED direction -- adverse/tenant_unprotected): %s" % headline)
        if detail and detail != headline:
            lines.append("    Detail: %s" % detail[:300])
        lines.append("    Direction: ADVERSE (tenant_unprotected) -- FIXED, do not reassess")
        lines.append("")
    lines.append("Return JSON keyed by LP ID (LP-05, LP-15, LP-20, LP-11) with use_consequence, materiality, use_reasoning.")
    return "\n".join(lines)


def build_variant_b_prompt(panel_data: list, use_profile: dict) -> str:
    """Variant B: direction-redacted -- clause facts + use profile only, strip adverse framing."""
    lines = [
        "PERSPECTIVE: TENANT",
        "",
        _use_profile_context(use_profile),
        "",
        "LEASE PROVISIONS TO ASSESS (clause facts only):",
        "",
    ]
    for fid, lp_id, lp_name, finding, lp in panel_data:
        coverage_state = lp.get("coverage_state", "")
        evs = lp.get("element_verdicts") or []
        present_verdicts = {"explicitly_present", "implicitly_present", "covered_by_default_law", "covered_in_other_LP"}
        found_labels = []
        missing_labels = []
        for ev in evs:
            label = None
            # Try to get human-readable element label
            if isinstance(ev, dict):
                label = ev.get("element_label") or ev.get("element_name") or ev.get("description")
                if not label:
                    eid = ev.get("element_id") or ""
                    # Convert element_id to readable: strip prefix, replace underscores
                    label = eid.split(".")[-1].replace("_", " ") if eid else None
                verdict = ev.get("verdict", "")
                if verdict in present_verdicts:
                    if label:
                        found_labels.append(label)
                elif verdict in {"missing", "unclear"}:
                    if label:
                        missing_labels.append(label)

        # Coverage state in neutral language
        if coverage_state == "review_needed":
            cov_desc = "uncertain coverage -- evaluators could not reach agreement on whether this provision adequately protects the tenant"
        elif coverage_state == "partial":
            cov_desc = "partially addressed -- %d element(s) confirmed in lease text, %d element(s) not confirmed" % (len(found_labels), len(missing_labels))
        elif coverage_state == "missing":
            cov_desc = "partially addressed -- some elements present but key elements not confirmed"
        else:
            cov_desc = coverage_state

        # Clause text (neutral -- no finding framing)
        tenant_text = (lp.get("tenant_text") or "")[:500]

        lines.append("  %s [%s]" % (lp_id, lp_name))
        lines.append("    Coverage: %s" % cov_desc)
        if found_labels:
            lines.append("    Elements confirmed in lease: %s" % "; ".join(found_labels[:6]))
        if missing_labels:
            lines.append("    Elements not confirmed in lease: %s" % "; ".join(missing_labels[:4]))
        if tenant_text:
            lines.append("    Relevant lease language: %s..." % tenant_text[:400])
        lines.append("")
    lines.append("Return JSON keyed by LP ID (LP-05, LP-15, LP-20, LP-11) with use_consequence, materiality, use_reasoning.")
    return "\n".join(lines)


def build_variant_c_prompt(panel_data: list, use_profile: dict) -> str:
    """Variant C: finding included but explicit independence instruction per finding."""
    lines = [
        "PERSPECTIVE: TENANT",
        "",
        _use_profile_context(use_profile),
        "",
        "STRUCTURAL FINDINGS TO ASSESS:",
        "(For each: Stage 7 found a structural concern. INDEPENDENCE RULE: do NOT infer ",
        " harmfulness from the direction label alone. Assess consequence from the clause ",
        " facts and this tenant's specific use.)",
        "",
    ]
    for fid, lp_id, lp_name, finding, lp in panel_data:
        headline = (finding.get("headline") or "").strip()
        detail = (finding.get("detail") or "").strip()
        # Include the finding but NOT the adversarial title framing
        # Strip exposure-flavored title; keep factual headline + detail
        evs = lp.get("element_verdicts") or []
        present_verdicts = {"explicitly_present", "implicitly_present", "covered_by_default_law", "covered_in_other_LP"}
        missing_labels = []
        for ev in evs:
            if isinstance(ev, dict) and ev.get("verdict") in {"missing", "unclear"}:
                eid = ev.get("element_id") or ""
                label = eid.split(".")[-1].replace("_", " ") if eid else None
                if label:
                    missing_labels.append(label)

        lines.append("  %s [%s]" % (lp_id, lp_name))
        lines.append("    Stage 7 structural finding: %s" % headline)
        if detail and detail != headline:
            lines.append("    Factual detail: %s" % detail[:250])
        if missing_labels:
            lines.append("    Elements not confirmed in lease: %s" % "; ".join(missing_labels[:3]))
        lines.append("    INDEPENDENCE: This finding is flagged as structurally adverse.")
        lines.append("    Assess whether this structure is ACTUALLY harmful, neutral, or beneficial")
        lines.append("    for THIS warehousing/distribution tenant. Do not ratify the label.")
        lines.append("")
    lines.append("Return JSON keyed by LP ID (LP-05, LP-15, LP-20, LP-11) with use_consequence, materiality, use_reasoning.")
    return "\n".join(lines)


# ── Evaluator call ────────────────────────────────────────────────────────────

def _call_panel_evaluator(
    role: str,
    ev_cfg: dict,
    system_prompt: str,
    user_prompt: str,
    claimed_providers: set,
    claimed_lock: threading.Lock,
    variant_label: str,
) -> dict:
    """Call one evaluator for one prompt variant."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    from cam.core.json_extract import safe_json_extract

    start = time.time()

    def _try(provider, model, label):
        with claimed_lock:
            if provider in claimed_providers:
                return None
            claimed_providers.add(provider)
        try:
            target = ModelTarget(
                name="%s:%s-cova1diag-%s-%s" % (provider, model, variant_label, role),
                provider=provider, model=model,
                max_output_tokens=2000, temperature=0.0, timeout_sec=240.0,
            )
            router = ProviderRouter([target], RouterConfig())
            adapter = router._get_adapter(provider)
            raw = adapter.call(system_prompt, user_prompt, target).strip()
            parsed = safe_json_extract(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Not a dict: %s" % type(parsed).__name__)
            if parsed:
                return {
                    "role": role, "label": label, "lp_output": parsed,
                    "completed": True, "elapsed_sec": round(time.time() - start, 2),
                    "error": None,
                }
        except Exception as e:
            logger.warning("[diagnostic] Eval-%s %s failed: %s" % (role, label, e))
        return None

    res = _try(ev_cfg["provider"], ev_cfg["model"], ev_cfg["label"])
    if res:
        return res
    for fb_p, fb_m, fb_l in ev_cfg.get("own_chain", []):
        res = _try(fb_p, fb_m, fb_l)
        if res:
            return res

    return {
        "role": role, "label": ev_cfg["label"], "lp_output": None,
        "completed": False, "elapsed_sec": round(time.time() - start, 2),
        "error": "all attempts failed",
    }


# ── Governance merge ──────────────────────────────────────────────────────────

def _merge(results: list, lp_ids: list) -> dict:
    """Merge 3 evaluator outputs into one verdict per LP. Same logic as lease_use_impact."""
    from collections import Counter
    completed = [r for r in results if r.get("completed") and r.get("lp_output")]
    n_ok = len(completed)

    if n_ok == 0:
        return {
            lp_id: {"use_consequence": "context_dependent", "materiality": "low",
                    "use_reasoning": "No evaluators available.",
                    "confidence": "no_evaluators", "evaluator_agreement": None,
                    "n_evaluators": 0}
            for lp_id in lp_ids
        }

    merged = {}
    for lp_id in lp_ids:
        consequences, mats, reasonings = [], [], []
        for r in completed:
            out = r["lp_output"].get(lp_id) or {}
            uc = (out.get("use_consequence") or "").lower().strip()
            mt = (out.get("materiality") or "").lower().strip()
            rs = (out.get("use_reasoning") or "").strip()
            if uc in VALID_UC:
                consequences.append(uc)
            if mt in VALID_MAT:
                mats.append(mt)
            if rs:
                reasonings.append(rs)

        if not consequences:
            merged[lp_id] = {"use_consequence": "context_dependent", "materiality": "low",
                              "use_reasoning": "No valid verdict.", "confidence": "no_evaluators",
                              "evaluator_agreement": None, "n_evaluators": n_ok,
                              "per_evaluator": [r["lp_output"].get(lp_id) for r in completed]}
            continue

        uc_counts = Counter(consequences)
        top_uc, top_count = uc_counts.most_common(1)[0]
        if top_count == len(consequences):
            final_uc, confidence, agree_str = top_uc, "assert", "%d-0" % len(consequences)
        elif top_count >= 2:
            final_uc, confidence, agree_str = top_uc, "assert_weak", "2-1"
        else:
            final_uc, confidence, agree_str = "context_dependent", "context_dependent", "1-1-1"

        MRANK = {"not_applicable": 0, "low": 1, "medium": 2, "high": 3}
        mat = min(mats, key=lambda m: MRANK.get(m, 1)) if mats else "low"

        reasoning = reasonings[0] if reasonings else ""
        for r in completed:
            out = r["lp_output"].get(lp_id) or {}
            if (out.get("use_consequence") or "").lower().strip() == final_uc:
                cand = (out.get("use_reasoning") or "").strip()
                if cand:
                    reasoning = cand
                    break

        merged[lp_id] = {
            "use_consequence": final_uc, "materiality": mat,
            "use_reasoning": reasoning, "confidence": confidence,
            "evaluator_agreement": agree_str, "n_evaluators": n_ok,
            "per_evaluator": {
                r["label"]: r["lp_output"].get(lp_id) for r in completed
            },
        }
    return merged


# ── Main runner ───────────────────────────────────────────────────────────────

def run_diagnostic():
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)

    # Load artifact
    print("Loading artifact: lease_review_20260605_174504_19f9a7")
    with open(ARTIFACT_PATH, encoding="utf-8") as f:
        artifact = json.load(f)

    cpf = artifact.get("cross_provision_findings", [])
    ca = artifact.get("coverage_assessment", [])
    use_profile = artifact.get("use_profile", {})

    ca_by_lp = {a.get("issue_area_id", ""): a for a in ca}
    cpf_by_id = {f.get("finding_id", ""): f for f in cpf}

    # Build panel data: [(fid, lp_id, lp_name, finding, lp), ...]
    panel_data = []
    for fid, lp_id, lp_name in PANEL:
        finding = cpf_by_id.get(fid, {})
        lp = ca_by_lp.get(lp_id, {})
        panel_data.append((fid, lp_id, lp_name, finding, lp))
        print("  Panel: %s / %s -- use_consequence=%s (source=%s)" % (
            fid, lp_id,
            finding.get("use_consequence", "ABSENT"),
            finding.get("use_consequence_source", "ABSENT"),
        ))

    # Load evaluator lineup
    from cam.adapters.lease_review.model_config import (
        EVALUATOR_A_PRIMARY, EVALUATOR_A_FALLBACK,
        EVALUATOR_B_PRIMARY, EVALUATOR_B_FALLBACK,
        EVALUATOR_C_PRIMARY, EVALUATOR_C_FALLBACK,
        EVALUATOR_A_LABEL, EVALUATOR_B_LABEL, EVALUATOR_C_LABEL,
        EVALUATOR_A_FALLBACK_LABEL, EVALUATOR_B_FALLBACK_LABEL, EVALUATOR_C_FALLBACK_LABEL,
    )
    EVALUATOR_LINEUP = {
        "A": {"provider": EVALUATOR_A_PRIMARY[0], "model": EVALUATOR_A_PRIMARY[1],
              "label": EVALUATOR_A_LABEL,
              "own_chain": [(EVALUATOR_A_FALLBACK[0], EVALUATOR_A_FALLBACK[1], EVALUATOR_A_FALLBACK_LABEL)]},
        "B": {"provider": EVALUATOR_B_PRIMARY[0], "model": EVALUATOR_B_PRIMARY[1],
              "label": EVALUATOR_B_LABEL,
              "own_chain": [(EVALUATOR_B_FALLBACK[0], EVALUATOR_B_FALLBACK[1], EVALUATOR_B_FALLBACK_LABEL)]},
        "C": {"provider": EVALUATOR_C_PRIMARY[0], "model": EVALUATOR_C_PRIMARY[1],
              "label": EVALUATOR_C_LABEL,
              "own_chain": [(EVALUATOR_C_FALLBACK[0], EVALUATOR_C_FALLBACK[1], EVALUATOR_C_FALLBACK_LABEL)]},
    }

    lp_ids = [lp_id for _, lp_id, _, _, _ in panel_data]

    # Build prompts
    prompts = {
        "A": (SYSTEM_PROMPT_A, build_variant_a_prompt(panel_data, use_profile)),
        "B": (SYSTEM_PROMPT_B, build_variant_b_prompt(panel_data, use_profile)),
        "C": (SYSTEM_PROMPT_C, build_variant_c_prompt(panel_data, use_profile)),
    }

    raw_results = {}   # variant -> list of evaluator results
    merged_results = {}  # variant -> lp_id -> verdict

    for variant_label, (sys_p, user_p) in prompts.items():
        print("\nRunning variant %s (%s)..." % (variant_label, {
            "A": "current COV-A prompt",
            "B": "direction-redacted",
            "C": "explicit-independence",
        }[variant_label]))

        claimed_providers = set()
        claimed_lock = threading.Lock()
        evaluator_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    _call_panel_evaluator,
                    role, ev_cfg, sys_p, user_p,
                    claimed_providers, claimed_lock, variant_label,
                ): role
                for role, ev_cfg in EVALUATOR_LINEUP.items()
            }
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    evaluator_results.append(res)
                    role = futures[fut]
                    completed = res.get("completed", False)
                    if completed:
                        out = res.get("lp_output", {})
                        summaries = {
                            lp: (out.get(lp) or {}).get("use_consequence", "?")
                            for lp in lp_ids
                        }
                        print("  Eval-%s (%s): %s" % (role, res.get("label", "?"), summaries))
                    else:
                        print("  Eval-%s FAILED: %s" % (role, res.get("error")))
                except Exception as e:
                    role = futures[fut]
                    print("  Eval-%s raised: %s" % (role, e))
                    evaluator_results.append({
                        "role": role, "lp_output": None, "completed": False, "error": str(e)
                    })

        raw_results[variant_label] = evaluator_results
        merged_results[variant_label] = _merge(evaluator_results, lp_ids)

        # Print merged summary
        for lp_id in lp_ids:
            v = merged_results[variant_label].get(lp_id, {})
            print("    -> %s: %s / %s [%s, %s eval]" % (
                lp_id,
                v.get("use_consequence", "?"), v.get("materiality", "?"),
                v.get("confidence", "?"), v.get("n_evaluators", 0),
            ))

    # Save raw results
    raw_path = os.path.join(REPO_ROOT, "build_log", "375E-COV-A1_raw_results.json")
    raw_out = {
        "artifact": "lease_review_20260605_174504_19f9a7",
        "panel": [{"finding_id": fid, "lp_id": lp_id, "lp_name": lp_name,
                   "cova_result": cpf_by_id.get(fid, {}).get("use_consequence"),
                   "cova_materiality": cpf_by_id.get(fid, {}).get("materiality")}
                  for fid, lp_id, lp_name in PANEL],
        "variants": {vl: {lp_id: merged_results[vl].get(lp_id) for lp_id in lp_ids}
                     for vl in ["A", "B", "C"]},
        "raw": {vl: [{"role": r.get("role"), "label": r.get("label"),
                      "completed": r.get("completed"), "lp_output": r.get("lp_output"),
                      "error": r.get("error")}
                     for r in raw_results[vl]]
                for vl in ["A", "B", "C"]},
    }
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_out, f, indent=2, ensure_ascii=False)
    print("\nRaw results: " + raw_path)

    # Write results.md
    md_path = os.path.join(REPO_ROOT, "build_log", "375E-COV-A1_results.md")
    _write_results_md(md_path, panel_data, merged_results, cpf_by_id, lp_ids)
    print("Results: " + md_path)


def _write_results_md(path: str, panel_data, merged_results, cpf_by_id, lp_ids):
    """Write the results.md with table + read + push recommendation."""

    def _row(variant, lp_id, r, cova_uc, cova_mat):
        uc = r.get("use_consequence", "?")
        mat = r.get("materiality", "?")
        conf = r.get("confidence", "?")
        reason = (r.get("use_reasoning") or "")[:120]
        flip = ""
        if variant != "A" and uc != cova_uc:
            flip = " *FLIP*"
        return "| %s | %s | %s | %s | %s | %s%s |" % (
            lp_id, variant, uc, mat, conf, reason, flip
        )

    lines = [
        "# 375E-COV-A1 Consequence-Independence Diagnostic Results",
        "",
        "**Date:** 2026-06-05",
        "**Run artifact:** lease_review_20260605_174504_19f9a7",
        "**Panel:** Dir-05/LP-05 (Permitted Use), Dir-12/LP-15 (Signage Rights),",
        "          Dir-15/LP-20 (Exclusivity), Dir-10/LP-11 (Default & Remedies)",
        "",
        "**COV-A distribution in 19f9a7 run:** 24 harmful / 1 neutral / 0 beneficial (25 directional findings)",
        "",
        "**Concern being tested:** Does the COV-A finding-scoped 5e prompt contaminate consequence",
        "assessment by handing 5e an adversarially-framed finding (tenant_unprotected, no relief,",
        "uncapped, risk) and asking 'how bad is it'? If so, 5e ratifies the framing instead of",
        "independently assessing consequence -- defeating Stage-7-owns-sign / 5e-owns-consequence.",
        "",
        "## Prompt Variants",
        "",
        "- **A (current COV-A):** as shipped. Hands over Stage 7 title + direction (tenant_unprotected/adverse/FIXED)",
        "- **B (direction-redacted):** clause facts + use profile only. No adverse framing, no direction label.",
        "- **C (explicit-independence):** finding included but instructs: do not infer harmfulness from direction.",
        "",
        "## Results Table",
        "",
        "| LP | Variant | use_consequence | materiality | confidence | reasoning (truncated) |",
        "|----|---------|-----------------|-------------|------------|----------------------|",
    ]

    # Per-LP rows with COV-A run value
    for fid, lp_id, lp_name in PANEL:
        f = cpf_by_id.get(fid, {})
        cova_uc = f.get("use_consequence", "ABSENT")
        cova_mat = f.get("materiality", "ABSENT")
        cova_conf = (f.get("use_impact", {}) or {}).get("confidence", "n/a") if f else "n/a"

        # COV-A run row (reference)
        lines.append("| %s/%s | A-RUN (19f9a7) | %s | %s | (from pipeline) |" % (
            lp_id, lp_name, cova_uc, cova_mat
        ))

        for variant in ["A", "B", "C"]:
            r = merged_results.get(variant, {}).get(lp_id, {})
            lines.append(_row(variant, lp_id, r, cova_uc, cova_mat))
        lines.append("| | | | | | |")  # separator

    lines += [
        "",
        "Rows marked *FLIP* indicate Variant B or C diverged from Variant A.",
        "",
        "## Per-Finding Detail",
        "",
    ]

    for fid, lp_id, lp_name in PANEL:
        f = cpf_by_id.get(fid, {})
        cova_uc = f.get("use_consequence", "ABSENT")
        lines.append("### %s / %s -- %s" % (fid, lp_id, lp_name))
        lines.append("")
        lines.append("**COV-A run result:** use_consequence=%s, materiality=%s" % (
            cova_uc, f.get("materiality", "ABSENT")))
        lines.append("")
        for variant in ["A", "B", "C"]:
            r = merged_results.get(variant, {}).get(lp_id, {})
            uc = r.get("use_consequence", "?")
            mat = r.get("materiality", "?")
            conf = r.get("confidence", "?")
            agree = r.get("evaluator_agreement", "?")
            n_ev = r.get("n_evaluators", 0)
            reason = (r.get("use_reasoning") or "")
            vname = {"A": "A (current COV-A)", "B": "B (direction-redacted)", "C": "C (explicit-independence)"}[variant]
            lines.append("**Variant %s:**" % vname)
            lines.append("  use_consequence=%s, materiality=%s, confidence=%s (%s, %d evaluators)" % (
                uc, mat, conf, agree, n_ev))
            lines.append("  Reasoning: %s" % reason)
            lines.append("")
        lines.append("")

    # Read section
    lines += [
        "## Read: Contamination / Genuine / Chaotic",
        "",
    ]

    # Compute signal
    flips = {}  # lp_id -> {B: True/False, C: True/False}
    for fid, lp_id, lp_name in PANEL:
        f = cpf_by_id.get(fid, {})
        cova_uc = f.get("use_consequence", "ABSENT")
        r_a = merged_results.get("A", {}).get(lp_id, {})
        r_b = merged_results.get("B", {}).get(lp_id, {})
        r_c = merged_results.get("C", {}).get(lp_id, {})
        a_uc = r_a.get("use_consequence", "?")
        b_uc = r_b.get("use_consequence", "?")
        c_uc = r_c.get("use_consequence", "?")
        b_flip = (a_uc == "harmful" and b_uc in {"neutral", "beneficial", "context_dependent"})
        c_flip = (a_uc == "harmful" and c_uc in {"neutral", "beneficial", "context_dependent"})
        flips[lp_id] = {"A": a_uc, "B": b_uc, "C": c_uc, "b_flip": b_flip, "c_flip": c_flip}

    n_flips_b = sum(1 for lp_id, v in flips.items() if v["b_flip"])
    n_flips_c = sum(1 for lp_id, v in flips.items() if v["c_flip"])

    # Chaotic: any finding where A, B, C all differ from each other
    n_chaotic = sum(
        1 for lp_id, v in flips.items()
        if len({v["A"], v["B"], v["C"]}) == 3
    )

    lines.append("### Signal summary")
    lines.append("")
    for lp_id, v in flips.items():
        b_tag = "FLIP" if v["b_flip"] else "same"
        c_tag = "FLIP" if v["c_flip"] else "same"
        lines.append("  %s: A=%s | B=%s (%s) | C=%s (%s)" % (
            lp_id, v["A"], v["B"], b_tag, v["C"], c_tag
        ))
    lines.append("")
    lines.append("Variant B flips: %d of %d findings" % (n_flips_b, len(PANEL)))
    lines.append("Variant C flips: %d of %d findings" % (n_flips_c, len(PANEL)))
    lines.append("Chaotic (A/B/C all differ): %d of %d findings" % (n_chaotic, len(PANEL)))
    lines.append("")

    # Determine read
    if n_flips_b >= 2 or n_flips_c >= 2:
        read = "CONTAMINATION CONFIRMED"
        read_detail = (
            "Variant B (direction-redacted) and/or Variant C (explicit-independence) diverge from "
            "Variant A on %d+ findings. 5e is ratifying the adversarial framing from COV-A's "
            "finding-scoped prompt (tenant_unprotected / exposure-flavored titles) rather than "
            "independently assessing consequence. The monochrome 24-harmful distribution is "
            "prompt-driven, not purely lease-driven. Fix COV-A's finding-scoped prompt before push."
        )
    elif n_chaotic >= 2:
        read = "CHAOTIC"
        read_detail = (
            "Variants diverge inconsistently across findings. The consequence axis is unstable "
            "per-finding and the panel is too small to characterize. COV-B cannot route on "
            "single-sample consequence. Larger diagnostic panel needed before push."
        )
    elif n_flips_b == 0 and n_flips_c == 0:
        read = "GENUINE (tentative)"
        read_detail = (
            "All three prompt variants agree. The 24-harmful distribution appears to reflect the "
            "lease (genuinely one-sided adversarial terms) rather than prompt contamination. "
            "The COV-A prompt is tentatively vindicated. Push becomes defensible once "
            "criterion (4) confound is demoted (cross-run synthesis wobble, not COV-A drift)."
        )
    else:
        read = "MIXED (1 flip)"
        read_detail = (
            "One finding flips between direction-redacted and current prompt. "
            "Directional evidence of some framing effect but below the contamination threshold. "
            "Flag and monitor; single flip may be genuine instability (see LP-20 wobbler). "
            "Push defensible with explicit caveat."
        )

    lines += [
        "### Read: **%s**" % read,
        "",
        read_detail,
        "",
    ]

    # Key calibration observations
    lines += [
        "### Calibration observations",
        "",
        "**LP-15 (Signage -- lone neutral):** This is the most important calibration point. ",
        "If LP-15 stays neutral across all variants, it shows clause facts CAN overpower ",
        "framing on some provisions -- bias exists but is not total. If LP-15 flips to harmful ",
        "in Variant A but neutral in B/C, that is direct contamination evidence.",
        "",
        "**LP-11 (Default & Remedies -- thin-gap):** 15 of 17 elements present. The only gaps ",
        "are rent_acceleration_remedy and mortgagee_guarantor_cure_right. The COV-A finding ",
        "title is 'Accelerated liability without limits' -- adversarially framed for a mostly-",
        "complete provision. If B/C return neutral or low-materiality, that confirms the ",
        "thin-gap framing problem specifically.",
        "",
        "**LP-20 (Exclusivity -- known wobbler):** assert_weak 2-1 in frozen 52adbf. If ",
        "variants diverge here, separate from contamination -- this LP has genuine instability.",
        "",
        "**LP-05 (Permitted Use -- regenerated):** Fresh Dir-05 is about co-tenancy risk ",
        "(no anchor-tenant protections). For a warehouse/distribution tenant, co-tenancy ",
        "dependency is operationally significant. If all variants return harmful, that is ",
        "genuine -- this is a different semantic test than the frozen 'absence of use restriction' case.",
        "",
    ]

    # Push recommendation
    lines += [
        "## Push Recommendation",
        "",
    ]
    if "CONTAMINATION" in read:
        lines += [
            "**HOLD PUSH.**",
            "",
            "Prompt contamination confirmed. COV-A's finding-scoped 5e prompt hands 5e an ",
            "adversarially-framed finding (tenant_unprotected / no relief / uncapped / Risk) ",
            "and asks 'how consequential is this adverse finding' -- 5e ratifies the framing.",
            "",
            "Fix direction (spec in 375E-COV-A1 instruction, do NOT build in this step):",
            "Pass CLAUSE FACTS + use profile to 5e. Store stage7_direction on the finding ",
            "(provenance only). Do NOT feed the adversarial title/direction as a leading frame.",
            "5e assesses consequence from the clause; Stage 7 owns the sign. Re-validate after fix.",
            "",
            "Criterion (4) confound (cross-run synthesis wobble) remains demoted -- it measured",
            "Stage-7 instability, not COV-A drift. Push remains gated on prompt fix, not on (4).",
        ]
    elif "GENUINE" in read:
        lines += [
            "**PUSH-OK (conditional).**",
            "",
            "All variants agree -- the 24-harmful distribution reflects the lease, not prompt framing.",
            "COV-A prompt is tentatively vindicated.",
            "",
            "Condition: criterion (4) confound must be formally demoted in the keyed validation report",
            "before push. The routing drift (Dir-03, CRX severity flips) is cross-run Stage-7",
            "synthesis instability (375-R), not COV-A. Demote criterion (4) to 'known-confounded'",
            "and re-score the push verdict in 375E_COV_A_keyed_validation.md.",
            "",
            "Caveat (n=1, small panel): this is directional evidence on a 4-finding panel. ",
            "The lease appears genuinely one-sided; the distribution may be correct.",
        ]
    else:
        lines += [
            "**HOLD PUSH -- investigate further.**",
            "",
            read_detail,
        ]

    lines += [
        "",
        "---",
        "",
        "**Proven:** Results from this diagnostic run (3 evaluators per variant, governance-merged).",
        "**Caveat:** n=1 lease, 4-finding panel. Directional evidence, not a CAM metric.",
        "**Still-unmeasured:** Whether prompt fix changes the overall distribution enough to matter",
        "for COV-B routing (e.g., if 8 of 24 harmful flip to neutral, the routing formula changes).",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    run_diagnostic()
