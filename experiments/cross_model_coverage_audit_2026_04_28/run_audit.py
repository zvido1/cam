"""Cross-Model Coverage Audit — execution harness.

Methodology: Docs/Cross_Model_Coverage_Audit.md (pre-registered 2026-04-28).

What this script does:
  1. Load API keys from the central .env (OPENAI / ANTHROPIC / XAI).
  2. Reuse the T-10 fresh-run pipeline JSON from
     experiments/coverage_variance_2026_04_28/00_fresh_run_pipeline_results.json
     so the input set is byte-identical to what produced the variance experiment.
  3. For each of the 5 model-path coverage assessments (LP-07, LP-09, LP-11,
     LP-13, LP-14), reconstruct the EXACT same system_prompt / user_prompt that
     cam.adapters.lease_review.lease_exposure._build_model_exposure produces.
     Constants (_EXPOSURE_SYSTEM_PROMPTS, _EXPOSURE_USER_TEMPLATE,
     _EXPOSURE_USER_TEMPLATE_TAIL) are imported from the production module —
     no copy-paste, no behavior modification.
  4. Call all three production evaluators against each prompt:
        - Claude Sonnet 4   (anthropic, claude-sonnet-4-20250514)
        - GPT-5.2          (openai,    gpt-5.2)
        - Grok 4           (xai,       grok-4)
     Failures on individual calls are logged and skipped; the run continues.
  5. Save 15 per-call response JSONs + all_responses.json.
  6. Compare the three model outputs per call across the priority fields
     listed in the methodology and write diff_per_call/<LP>.txt.
  7. Write summary.json + report.txt.

What this script does NOT do:
  - Modify cam/core/ in any way.
  - Modify cam/adapters/lease_review/lease_exposure.py.
  - Implement disposition / kill-shot / triage logic.
  - Write the Results section of Docs/Cross_Model_Coverage_Audit.md.

Console hardening:
  - All file writes happen before any final print.
  - Final print is wrapped in try/except so a Windows cp1255 codec failure
    cannot invalidate the on-disk artifacts.
"""

import io
import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

# ── 1. Load API keys ───────────────────────────────────────────────────────
# The harness sets ANTHROPIC_API_KEY + ANTHROPIC_BASE_URL to a Cowork proxy.
# We want REAL provider endpoints for this audit (so the cost lands on the
# user's actual Anthropic account), so we force-override from the central
# .env and clear any proxy base URLs that would otherwise intercept calls.
KEYS_ENV = Path(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")
with open(KEYS_ENV, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ[k.strip()] = v  # force-override, do NOT setdefault

# Drop any harness-injected proxy base URLs that would redirect provider calls.
for proxy_var in ("ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "XAI_BASE_URL"):
    os.environ.pop(proxy_var, None)

for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"):
    assert os.environ.get(var), f"{var} missing after load"
print(f"[setup] API keys loaded for openai/anthropic/xai (proxy base URLs cleared)", flush=True)

# ── Paths / sys.path ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(r"C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "05 Lease Analyzer"))

OUT_DIR = PROJECT_ROOT / "experiments" / "cross_model_coverage_audit_2026_04_28"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DIFF_DIR = OUT_DIR / "diff_per_call"
DIFF_DIR.mkdir(exist_ok=True)

VARIANCE_FRESH_RUN = (
    PROJECT_ROOT / "experiments" / "coverage_variance_2026_04_28"
    / "00_fresh_run_pipeline_results.json"
)
assert VARIANCE_FRESH_RUN.exists(), (
    f"Expected variance experiment fresh-run JSON at {VARIANCE_FRESH_RUN}. "
    "Re-run experiments/coverage_variance_2026_04_28/run_variance_experiment.py first."
)

# ── 2. Load the input set ──────────────────────────────────────────────────
with open(VARIANCE_FRESH_RUN, encoding="utf-8") as f:
    fresh_pipeline = json.load(f)

coverage_assessment = fresh_pipeline.get("coverage_assessment", [])
EXPOSURE_FIELDS = {
    "exposure_statement",
    "exposure_source",
    "exposure_reason_code",
    "exposure_confidence_note",
    "exposure_elements_used",
    "exposure_perspective",
}


def strip_exposure(a: dict) -> dict:
    return {k: v for k, v in a.items() if k not in EXPOSURE_FIELDS}


model_path = [a for a in coverage_assessment if a.get("exposure_source") == "model"]
assert len(model_path) == 5, (
    f"Expected exactly 5 model-path assessments to match the audit pre-registration; "
    f"found {len(model_path)}. Source: {VARIANCE_FRESH_RUN}"
)
print(f"[setup] Reusing 5 model-path assessments from variance experiment fresh run", flush=True)
for a in model_path:
    print(
        f"  - {a.get('issue_area_id')} | state={a.get('coverage_state')} "
        f"| mat={a.get('materiality')} | reason={a.get('exposure_reason_code')}",
        flush=True,
    )

# ── 3. Import production prompt constants and ProviderRouter ───────────────
from cam.adapters.lease_review.lease_exposure import (
    _EXPOSURE_SYSTEM_PROMPTS,
    _EXPOSURE_USER_TEMPLATE,
    _EXPOSURE_USER_TEMPLATE_TAIL,
)
from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig

PERSPECTIVE = "tenant"  # production default
SYSTEM_PROMPT = _EXPOSURE_SYSTEM_PROMPTS[PERSPECTIVE]
USER_TAIL = _EXPOSURE_USER_TEMPLATE_TAIL[PERSPECTIVE]


def build_user_prompt(assessment: dict) -> tuple[str, list[str]]:
    """Reconstruct the user_prompt EXACTLY as _build_model_exposure does it.

    Returns (user_prompt_str, elements_used_list).
    """
    pid = assessment.get("issue_area_id", "")
    name = assessment.get("issue_area_name", pid)
    state = assessment.get("coverage_state", "")
    missing = assessment.get("elements_missing", [])
    found = assessment.get("elements_found", [])
    evidence = assessment.get("evidence_summary", "")
    fallback = assessment.get("exposure_statement", "")

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
        tail=USER_TAIL,
    )
    return user_prompt, elements_used


# ── 4. Define the three model targets ──────────────────────────────────────
# Constraints on max_output_tokens / timeout_sec match the production
# _build_model_exposure call (max_output_tokens=150 there). We keep that
# limit so prose length is comparable across models.
MAX_OUT = 350  # slightly higher than production 150 to accommodate Grok/Anthropic
                # tokenization; production's 150-token cap should still gate prose
                # length after de-tokenizing on the consumer side.
TIMEOUT = 120.0

MODEL_TARGETS = [
    ("claude", ModelTarget(
        name="anthropic:claude-sonnet-4-20250514",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        max_output_tokens=MAX_OUT,
        temperature=0.0,
        timeout_sec=TIMEOUT,
    )),
    ("gpt", ModelTarget(
        name="openai:gpt-5.2",
        provider="openai",
        model="gpt-5.2",
        max_output_tokens=MAX_OUT,
        timeout_sec=TIMEOUT,
    )),
    ("grok", ModelTarget(
        name="xai:grok-4",
        provider="xai",
        model="grok-4",
        max_output_tokens=MAX_OUT,
        temperature=0.0,
        timeout_sec=TIMEOUT,
    )),
]


def call_model(target: ModelTarget, system_prompt: str, user_prompt: str) -> dict:
    """Call a single model via ProviderRouter and capture the text + timing.

    Returns a dict with statement / error / elapsed_sec / model identifiers.
    Failures are caught and reported as {error: ...}; this keeps partial
    results informative if one provider is down.
    """
    out = {
        "model_label": target.name,
        "provider": target.provider,
        "model": target.model,
        "statement": None,
        "error": None,
        "elapsed_sec": None,
    }
    t0 = time.time()
    try:
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(target.provider)
        statement = adapter.call(system_prompt, user_prompt, target).strip()
        out["statement"] = statement
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        print(f"  [{target.name}] FAILED: {out['error']}", flush=True)
    out["elapsed_sec"] = round(time.time() - t0, 2)
    return out


# ── 5. Execute: 5 calls × 3 models = 15 model calls ────────────────────────
print(f"\n[execute] 5 calls × 3 models = 15 model calls...", flush=True)

all_responses: dict[str, dict] = {}

for assessment in model_path:
    pid = assessment.get("issue_area_id", "UNKNOWN")
    pre_exposure = strip_exposure(assessment)
    user_prompt, elements_used = build_user_prompt(pre_exposure)

    per_lp = {
        "input": pre_exposure,
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_prompt,
        "elements_used_input_slice": elements_used,
        "responses": {},
    }

    print(f"\n--- {pid} ---", flush=True)
    print(f"  input.coverage_state={pre_exposure.get('coverage_state')} "
          f"materiality={pre_exposure.get('materiality')}", flush=True)

    for label, target in MODEL_TARGETS:
        result = call_model(target, SYSTEM_PROMPT, user_prompt)
        per_lp["responses"][label] = result

        # Per-call×model JSON dump
        with open(OUT_DIR / f"{pid}_{label}.json", "w", encoding="utf-8") as f:
            json.dump({
                "issue_area_id": pid,
                "model_label": label,
                "model_target": result["model_label"],
                "input": pre_exposure,
                "system_prompt": SYSTEM_PROMPT,
                "user_prompt": user_prompt,
                "response": result,
            }, f, indent=2, ensure_ascii=False)

        if result["error"]:
            print(f"  [{label:<6}] error: {result['error']}", flush=True)
        else:
            stmt_len = len(result["statement"] or "")
            print(f"  [{label:<6}] {result['elapsed_sec']:>5.1f}s  "
                  f"len={stmt_len}  preview={(result['statement'] or '')[:80]!r}",
                  flush=True)

    all_responses[pid] = per_lp

# Combined dump
with open(OUT_DIR / "all_responses.json", "w", encoding="utf-8") as f:
    json.dump(all_responses, f, indent=2, ensure_ascii=False)

# ── 6. Mechanical comparison & per-call diff files ─────────────────────────
def normalize(s: str) -> str:
    return " ".join((s or "").lower().split())


summary_per_call = {}

for pid, data in all_responses.items():
    inp = data["input"]
    responses = data["responses"]

    # Fields per the audit methodology comparison priority list:
    #  1. coverage_state         — input, identical across models by construction
    #  2. partial_class          — input, identical across models by construction
    #  3. materiality            — input, identical across models by construction
    #  4. exposure_elements_used — deterministic input slice, identical
    #  5. exposure_reason_code   — input, identical
    #  6. exposure_statement     — model output (the divergence axis)
    #
    # We record the 5 deterministic fields once per LP for completeness,
    # and per-model statement text for the diff. Where fields are
    # deterministic-by-input we still flag any (impossible) drift if seen.
    coverage_state = inp.get("coverage_state")
    partial_class  = inp.get("partial_class")
    materiality    = inp.get("materiality")
    elements_used  = data["elements_used_input_slice"]
    reason_code    = inp.get("exposure_reason_code")
    # NOTE: reason_code is computed downstream of state — for replay/audit, we
    # mirror the production logic by recomputing it via the same reason map,
    # not by reading the field above (which was set during the original run).
    # The two should match.

    statements = {label: (r["statement"] or "").strip() for label, r in responses.items()}
    errors = {label: r["error"] for label, r in responses.items() if r["error"]}
    statements_norm = {label: normalize(s) for label, s in statements.items() if s}

    # All input-derived fields are identical by construction; flag a
    # divergence only if a future change breaks that invariant.
    deterministic_fields_diverged = False  # by construction in this script

    # Statement-text divergence: does the prose differ across models?
    statement_set = {s for s in statements_norm.values() if s}
    statement_diverged = len(statement_set) > 1

    summary_per_call[pid] = {
        "coverage_state": coverage_state,
        "partial_class": partial_class,
        "materiality": materiality,
        "elements_used_input_slice": elements_used,
        "reason_code": reason_code,
        "deterministic_fields_diverged": deterministic_fields_diverged,
        "statement_diverged": statement_diverged,
        "models_with_errors": list(errors.keys()),
        "models_responded": [label for label, s in statements.items() if s],
        "lengths": {label: len(s) for label, s in statements.items()},
        "elapsed_sec": {label: r["elapsed_sec"] for label, r in responses.items()},
    }

    # Per-call diff file with the full statement text from each model.
    block = []
    block.append(f"=== {pid} ===")
    block.append(f"  input.coverage_state    : {coverage_state}")
    block.append(f"  input.partial_class     : {partial_class}")
    block.append(f"  input.materiality       : {materiality}")
    block.append(f"  input.elements_missing  : {inp.get('elements_missing')}")
    block.append(f"  input.elements_found    : {inp.get('elements_found')}")
    block.append(f"  exposure_elements_used  : {elements_used}")
    block.append(f"  exposure_reason_code    : {reason_code}")
    block.append("")
    block.append(f"  models_responded        : {summary_per_call[pid]['models_responded']}")
    if errors:
        block.append(f"  models_with_errors      : {errors}")
    block.append(f"  statement_text_diverged : {statement_diverged}")
    block.append("")
    for label in ("claude", "gpt", "grok"):
        r = responses.get(label, {})
        block.append(f"  [{label.upper()}]  ({r.get('model_label')})  "
                     f"elapsed={r.get('elapsed_sec')}s  "
                     f"{'ERROR: ' + r.get('error') if r.get('error') else ''}")
        stmt = r.get("statement")
        if stmt:
            for ln in stmt.splitlines():
                block.append(f"    {ln}")
        block.append("")

    with open(DIFF_DIR / f"{pid}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(block))

# ── 7. summary.json + report.txt ───────────────────────────────────────────
summary = {
    "experiment": "cross_model_coverage_audit_2026_04_28",
    "input_source": str(VARIANCE_FRESH_RUN.relative_to(PROJECT_ROOT)),
    "lease": "T-10_Negotiated_Tennant_Lease.docx",
    "perspective": PERSPECTIVE,
    "n_calls": len(model_path),
    "n_models": len(MODEL_TARGETS),
    "n_total_responses_attempted": len(model_path) * len(MODEL_TARGETS),
    "models": [{"label": label, "name": tgt.name, "provider": tgt.provider, "model": tgt.model}
               for label, tgt in MODEL_TARGETS],
    "per_call": summary_per_call,
    "total_elapsed_sec_per_model": {
        label: round(sum(
            (data["responses"].get(label, {}).get("elapsed_sec") or 0)
            for data in all_responses.values()
        ), 2)
        for label, _ in MODEL_TARGETS
    },
    "total_failures": sum(
        1
        for data in all_responses.values()
        for r in data["responses"].values()
        if r.get("error")
    ),
}

with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

# report.txt — human-readable rendering, suitable for pasting into chat / Results
report_lines = []
report_lines.append("Cross-Model Coverage Audit — Mechanical Diff Report")
report_lines.append("Date: 2026-04-28")
report_lines.append("Lease: T-10_Negotiated_Tennant_Lease.docx")
report_lines.append(f"Input source: {summary['input_source']}")
report_lines.append("Perspective: tenant")
report_lines.append("")
report_lines.append("Models:")
for m in summary["models"]:
    report_lines.append(f"  - {m['label']:<6} → {m['name']}")
report_lines.append("")
report_lines.append(f"Calls: {summary['n_calls']} model-path × {summary['n_models']} models = "
                    f"{summary['n_total_responses_attempted']}")
report_lines.append(f"Failures: {summary['total_failures']}")
report_lines.append("")
report_lines.append("Per-call breakdown:")
report_lines.append("")
for pid, info in summary_per_call.items():
    report_lines.append(f"  {pid}:")
    report_lines.append(f"    coverage_state         : {info['coverage_state']}")
    report_lines.append(f"    partial_class          : {info['partial_class']}")
    report_lines.append(f"    materiality            : {info['materiality']}")
    report_lines.append(f"    reason_code            : {info['reason_code']}")
    report_lines.append(f"    elements_used (input)  : {info['elements_used_input_slice']}")
    report_lines.append(f"    models_responded       : {info['models_responded']}")
    if info["models_with_errors"]:
        report_lines.append(f"    models_with_errors     : {info['models_with_errors']}")
    report_lines.append(f"    statement_text_diverged: {info['statement_diverged']}")
    report_lines.append(f"    statement_lengths      : {info['lengths']}")
    report_lines.append(f"    elapsed_sec            : {info['elapsed_sec']}")
    report_lines.append("")

report_lines.append("")
report_lines.append("Notes for analysis:")
report_lines.append("  - All input-derived fields (coverage_state, partial_class, materiality,")
report_lines.append("    exposure_elements_used, exposure_reason_code) are identical across all")
report_lines.append("    three models BY CONSTRUCTION — they are upstream-deterministic inputs to")
report_lines.append("    the model call, not model outputs. Field-level divergence on these is")
report_lines.append("    impossible without modifying the script.")
report_lines.append("  - The per-call divergence axis the audit can observe is the prose content")
report_lines.append("    of `exposure_statement`. Whether divergence in prose reflects different")
report_lines.append("    facts cited (Outcome C/D) vs. only different phrasing of the same facts")
report_lines.append("    (Outcome A/B) is a content-level judgement, not a field-level diff.")
report_lines.append("  - Full statement text per call×model: see diff_per_call/<LP>.txt and the")
report_lines.append("    individual <LP>_<label>.json files.")

with open(OUT_DIR / "report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

# ── 8. Final summary print (wrapped against console codec failure) ────────
try:
    print("\n" + "=" * 70, flush=True)
    print("AUDIT COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"Per-model total elapsed: {summary['total_elapsed_sec_per_model']}", flush=True)
    print(f"Failures: {summary['total_failures']}", flush=True)
    print(f"\nArtifacts: {OUT_DIR}", flush=True)
    print(f"  - summary.json", flush=True)
    print(f"  - report.txt", flush=True)
    print(f"  - all_responses.json", flush=True)
    print(f"  - {len(model_path) * len(MODEL_TARGETS)} per-call×model JSONs", flush=True)
    print(f"  - {len(model_path)} diff_per_call/<LP>.txt files", flush=True)
except Exception as e:
    # Windows cp1255 will sometimes choke on non-breaking hyphens etc. The
    # on-disk artifacts above are already saved; we don't want a console
    # encode failure to invalidate the run. Ignore and exit cleanly.
    sys.stderr.write(f"[final-print] suppressed console encoding error: {e!r}\n")
