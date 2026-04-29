"""Cross-Model Coverage CLASSIFICATION Audit — execution harness.

Methodology: Docs/Cross_Model_Coverage_Classification_Audit.md (pre-registered 2026-04-28).

This is the successor to the original Cross-Model Coverage Audit, which was
superseded due to a methodology error (the original gave each model the
deterministic classification fields as fixed inputs and asked only for prose
— so the models could not diverge on classification by construction).

This script asks each model to make the same classification decision the
regex classifier in `lease_coverage.py` makes, given the same raw inputs:
  - The schema definition for the issue area (expected_elements, coverage
    state rules, vocabulary).
  - The lease clause text the regex classifier saw.

For each of 5 LPs × 3 models, we save the model's structured JSON
classification, then mechanically compare:
  1. Cross-model agreement on `coverage_state`.
  2. Model consensus vs regex classifier output.
  3. Element-level overlap.

Out-of-vocabulary `coverage_state` values are recorded verbatim; never
silently corrected (they are themselves a finding).

Hard constraints honored:
  - No cam/core/ modifications.
  - No lease_coverage.py / lease_exposure.py / lease_negative_space.py
    modifications.
  - No retail_lease_knowledge.json modifications.
  - Identical prompt across all 3 providers (modulo provider-router message
    wrapping).
"""

import io
import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

# ── 1. Load API keys (force-override harness Cowork proxy) ─────────────────
KEYS_ENV = Path(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")
with open(KEYS_ENV, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ[k.strip()] = v
for proxy_var in ("ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "XAI_BASE_URL"):
    os.environ.pop(proxy_var, None)
for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"):
    assert os.environ.get(var), f"{var} missing after load"
print("[setup] API keys loaded for openai/anthropic/xai/gemini (proxy URLs cleared)", flush=True)

# ── Paths / sys.path ───────────────────────────────────────────────────────
PROJECT_ROOT = Path(r"C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "05 Lease Analyzer"))

OUT_DIR = PROJECT_ROOT / "experiments" / "cross_model_coverage_classification_audit_2026_04_28"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_PATH = (
    PROJECT_ROOT / "cam" / "adapters" / "lease_review" / "schemas"
    / "retail_lease_knowledge.json"
)
VARIANCE_FRESH_RUN = (
    PROJECT_ROOT / "experiments" / "coverage_variance_2026_04_28"
    / "00_fresh_run_pipeline_results.json"
)
DEMO_LEASE = (
    PROJECT_ROOT / "05 Lease Analyzer" / "test_data" / "tenants"
    / "T-10_Negotiated_Tennant_Lease.docx"
)
INPUTS_FILE = OUT_DIR / "00_audit_inputs.json"

assert SCHEMA_PATH.exists(), SCHEMA_PATH
assert VARIANCE_FRESH_RUN.exists(), VARIANCE_FRESH_RUN
assert DEMO_LEASE.exists(), DEMO_LEASE

TARGET_LPS = ["LP-07", "LP-09", "LP-11", "LP-13", "LP-14"]

# ── 2. Load schema + variance fresh-run regex output ───────────────────────
with open(SCHEMA_PATH, encoding="utf-8") as f:
    schema = json.load(f)

coverage_states_vocab = schema["coverage_states"]  # dict: state -> definition

issue_areas_by_id = {ia["id"]: ia for ia in schema["issue_areas"]}
for lp in TARGET_LPS:
    assert lp in issue_areas_by_id, f"Schema missing {lp}"

with open(VARIANCE_FRESH_RUN, encoding="utf-8") as f:
    fresh = json.load(f)

regex_assessments_by_id = {a["issue_area_id"]: a for a in fresh.get("coverage_assessment", [])}
for lp in TARGET_LPS:
    assert lp in regex_assessments_by_id, f"Variance run missing regex output for {lp}"

# ── 3. Get tenant_text per LP ──────────────────────────────────────────────
# The variance fresh run used Mode C; Mode C does NOT save the extracted
# `provisions` array to pipeline_results.json. We need the same tenant_text
# the regex classifier in `lease_coverage.py` saw, so we run
# `extract_provisions_single_doc` once on the same lease and save the result
# to 00_audit_inputs.json. Subsequent invocations reuse the saved extraction.
def load_or_run_extraction() -> dict:
    if INPUTS_FILE.exists():
        with open(INPUTS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        if saved.get("extraction", {}).get("provisions"):
            print(f"[setup] Reusing saved extraction from {INPUTS_FILE.name}", flush=True)
            return saved["extraction"]
    print("[setup] No saved extraction found — running extract_provisions_single_doc...", flush=True)
    from cam.adapters.lease_review.lease_parser import parse_document
    from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc
    from cam.adapters.lease_review.lease_provision_taxonomy import get_active_provisions
    tenant_text = parse_document(str(DEMO_LEASE))
    provisions = get_active_provisions()
    t0 = time.time()
    extraction = extract_provisions_single_doc(tenant_text, provisions, {})
    elapsed = time.time() - t0
    print(f"[setup] extraction complete in {elapsed:.1f}s — "
          f"{len(extraction['provisions'])} provisions", flush=True)
    return extraction


extraction = load_or_run_extraction()
provisions_by_id = {p["provision_id"]: p for p in extraction["provisions"]}
for lp in TARGET_LPS:
    assert lp in provisions_by_id, (
        f"Extraction missing tenant_text for {lp}; got {list(provisions_by_id)}"
    )
    assert (provisions_by_id[lp].get("tenant_text") or "").strip(), (
        f"Empty tenant_text for {lp}"
    )

# ── 4. Build 00_audit_inputs.json ──────────────────────────────────────────
audit_inputs = {
    "experiment": "cross_model_coverage_classification_audit_2026_04_28",
    "lease": "T-10_Negotiated_Tennant_Lease.docx",
    "schema_version": schema.get("schema_version"),
    "coverage_states_vocab": coverage_states_vocab,
    "target_lps": TARGET_LPS,
    "extraction": extraction,
    "regex_outputs_by_lp": {},
    "schema_inputs_by_lp": {},
}

for lp in TARGET_LPS:
    ia = issue_areas_by_id[lp]
    reg = regex_assessments_by_id[lp]

    audit_inputs["schema_inputs_by_lp"][lp] = {
        "id": ia["id"],
        "name": ia.get("name", ""),
        "applicability": ia.get("applicability", ""),
        "activation_clues": ia.get("activation_clues", []),
        "exclusion_clues": ia.get("exclusion_clues", []),
        "notes": ia.get("notes", ""),
        "expected_elements": ia.get("expected_elements", []),
        "coverage_state_rules": ia.get("coverage_state_rules", {}),
        "risk_if_missing": ia.get("risk_if_missing", ""),
    }

    audit_inputs["regex_outputs_by_lp"][lp] = {
        "coverage_state": reg.get("coverage_state"),
        "elements_found": reg.get("elements_found", []),
        "elements_missing": reg.get("elements_missing", []),
        "evidence_summary": reg.get("evidence_summary", ""),
        "partial_class": reg.get("partial_class"),
        "materiality": reg.get("materiality"),
    }

with open(INPUTS_FILE, "w", encoding="utf-8") as f:
    json.dump(audit_inputs, f, indent=2, ensure_ascii=False)
print(f"[setup] Saved audit inputs to {INPUTS_FILE.name}", flush=True)

# ── 5. Construct the IDENTICAL-ACROSS-MODELS prompt template ───────────────
def render_numbered(items: list) -> str:
    return "\n".join(f"  {i}. {item}" for i, item in enumerate(items, 1))


def render_dict_bullets(d: dict) -> str:
    if not d:
        return "  (none)"
    return "\n".join(f"  - {k}: {v}" for k, v in d.items())


def build_prompt(lp_id: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given LP.

    Identical across all 3 providers — only the LP-specific schema fields
    and clause text vary between LPs, never between models.
    """
    si = audit_inputs["schema_inputs_by_lp"][lp_id]
    tenant_text = provisions_by_id[lp_id].get("tenant_text", "")

    notes_line = f"- Notes: {si['notes']}" if si.get("notes") else ""

    sys_prompt = (
        "You are a careful commercial-lease reviewer. You classify a single "
        "issue area against a schema definition and the lease's actual clause "
        "text. You answer ONLY in JSON, no preamble or commentary."
    )

    user_prompt = (
        "You are reviewing a commercial lease provision from the TENANT'S perspective.\n"
        "\n"
        "## ISSUE AREA\n"
        f"- ID: {si['id']}\n"
        f"- Name: {si['name']}\n"
        f"- Applicability: {si['applicability']}\n"
        f"- Activation clues (signals issue area is in scope): {si['activation_clues']}\n"
        f"- Exclusion clues (signals issue area does NOT apply): {si['exclusion_clues']}\n"
        f"{notes_line}\n"
        "\n"
        "## EXPECTED ELEMENTS (what the schema says should be addressed)\n"
        f"{render_numbered(si['expected_elements'])}\n"
        "\n"
        "## COVERAGE STATE RULES (schema's guidance)\n"
        f"{render_dict_bullets(si['coverage_state_rules'])}\n"
        "\n"
        "## COVERAGE STATE VOCABULARY (permitted values for `coverage_state`)\n"
        f"{render_dict_bullets(coverage_states_vocab)}\n"
        "\n"
        "## RISK IF MISSING\n"
        f"{si['risk_if_missing']}\n"
        "\n"
        "## LEASE CLAUSE TEXT\n"
        f"{tenant_text}\n"
        "\n"
        "## YOUR TASK\n"
        "\n"
        "Independently classify this issue area for this lease. Identify which "
        "expected elements are addressed in the clause text, which are missing, "
        "and what the practical exposure to the tenant is.\n"
        "\n"
        "Respond ONLY in JSON, no preamble or commentary outside the JSON object:\n"
        "\n"
        "{\n"
        '  "coverage_state": "<one of the values from the COVERAGE STATE VOCABULARY above>",\n'
        '  "elements_present": ["<expected_element string>", ...],\n'
        '  "elements_missing": ["<expected_element string>", ...],\n'
        '  "justification": "<1-3 sentences citing specific lease language for the classification>",\n'
        '  "tenant_concern_summary": "<1 sentence: practical exposure from tenant perspective>"\n'
        "}\n"
    )
    return sys_prompt, user_prompt


# ── 6. Define the three model targets ──────────────────────────────────────
from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig

MODEL_TARGETS = [
    ("claude", ModelTarget(
        name="anthropic:claude-sonnet-4-20250514",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        max_output_tokens=1500,
        temperature=0.0,
        timeout_sec=180.0,
    )),
    ("gpt", ModelTarget(
        name="openai:gpt-5.2",
        provider="openai",
        model="gpt-5.2",
        max_output_tokens=1500,
        timeout_sec=180.0,
    )),
    ("grok", ModelTarget(
        name="xai:grok-4",
        provider="xai",
        model="grok-4",
        max_output_tokens=1500,
        temperature=0.0,
        timeout_sec=180.0,
    )),
]

PERMITTED_STATES = set(coverage_states_vocab.keys())


def parse_model_json(raw: str) -> tuple[dict | None, str | None]:
    """Best-effort JSON parse of a model response. Returns (parsed, error)."""
    if not raw:
        return None, "empty_response"
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        # remove leading ```json or ```
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
        text = text.strip()
    # Find first { and last } for resilience
    if not text.startswith("{"):
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            text = text[first : last + 1]
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"json_decode_error: {e}"


def call_one(target: ModelTarget, system_prompt: str, user_prompt: str) -> dict:
    out = {
        "model_label": target.name,
        "provider": target.provider,
        "model": target.model,
        "raw_response": None,
        "parsed": None,
        "json_parse_error": None,
        "out_of_vocab_state": None,  # populated if coverage_state not in PERMITTED_STATES
        "call_error": None,
        "elapsed_sec": None,
    }
    t0 = time.time()
    try:
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(target.provider)
        raw = adapter.call(system_prompt, user_prompt, target).strip()
        out["raw_response"] = raw
        parsed, err = parse_model_json(raw)
        out["parsed"] = parsed
        out["json_parse_error"] = err
        if parsed and isinstance(parsed, dict):
            cs = parsed.get("coverage_state")
            if cs is not None and cs not in PERMITTED_STATES:
                out["out_of_vocab_state"] = cs
    except Exception as e:
        out["call_error"] = f"{type(e).__name__}: {e}"
        print(f"  [{target.name}] CALL ERROR: {out['call_error']}", flush=True)
    out["elapsed_sec"] = round(time.time() - t0, 2)
    return out


# ── 7. Execute 5 × 3 = 15 calls ────────────────────────────────────────────
print(f"\n[execute] {len(TARGET_LPS)} LPs × {len(MODEL_TARGETS)} models = "
      f"{len(TARGET_LPS) * len(MODEL_TARGETS)} model calls\n", flush=True)

all_responses: dict[str, dict] = {}

for lp in TARGET_LPS:
    sys_prompt, user_prompt = build_prompt(lp)
    per_lp = {
        "lp_id": lp,
        "lp_name": audit_inputs["schema_inputs_by_lp"][lp]["name"],
        "system_prompt": sys_prompt,
        "user_prompt": user_prompt,
        "regex_classification": audit_inputs["regex_outputs_by_lp"][lp],
        "responses": {},
    }

    print(f"--- {lp} ({per_lp['lp_name']}) ---", flush=True)
    print(f"  regex_state={per_lp['regex_classification']['coverage_state']}", flush=True)

    for label, target in MODEL_TARGETS:
        result = call_one(target, sys_prompt, user_prompt)
        per_lp["responses"][label] = result

        with open(OUT_DIR / f"{lp}_{label}.json", "w", encoding="utf-8") as f:
            json.dump({
                "lp_id": lp,
                "model_label": label,
                "model_target": result["model_label"],
                "system_prompt": sys_prompt,
                "user_prompt": user_prompt,
                "regex_classification": per_lp["regex_classification"],
                "response": result,
            }, f, indent=2, ensure_ascii=False)

        if result["call_error"]:
            print(f"  [{label:<6}] {result['elapsed_sec']:>5.1f}s  ERROR: {result['call_error']}", flush=True)
        elif result["json_parse_error"]:
            print(f"  [{label:<6}] {result['elapsed_sec']:>5.1f}s  JSON PARSE ERROR: {result['json_parse_error']}", flush=True)
        else:
            cs = (result["parsed"] or {}).get("coverage_state")
            oov = " [OUT-OF-VOCAB]" if result["out_of_vocab_state"] else ""
            print(f"  [{label:<6}] {result['elapsed_sec']:>5.1f}s  state={cs}{oov}", flush=True)

    all_responses[lp] = per_lp
    print()

with open(OUT_DIR / "all_responses.json", "w", encoding="utf-8") as f:
    json.dump(all_responses, f, indent=2, ensure_ascii=False)

# ── 8. Build summary.json + report.txt ─────────────────────────────────────
def get_state(r: dict) -> str | None:
    p = r.get("parsed")
    if not p or not isinstance(p, dict):
        return None
    return p.get("coverage_state")


def get_list(r: dict, key: str) -> list:
    p = r.get("parsed")
    if not p or not isinstance(p, dict):
        return []
    v = p.get(key) or []
    return v if isinstance(v, list) else []


def get_just(r: dict) -> str:
    p = r.get("parsed")
    if not p or not isinstance(p, dict):
        return ""
    return str(p.get("justification") or "")


summary_per_lp = {}
for lp, per_lp in all_responses.items():
    responses = per_lp["responses"]
    regex_state = per_lp["regex_classification"]["coverage_state"]

    model_states = {label: get_state(r) for label, r in responses.items()}
    elements_present = {label: get_list(r, "elements_present") for label, r in responses.items()}
    elements_missing = {label: get_list(r, "elements_missing") for label, r in responses.items()}
    justifications = {label: get_just(r) for label, r in responses.items()}
    tenant_concern = {
        label: ((r.get("parsed") or {}).get("tenant_concern_summary") or "")
        for label, r in responses.items()
    }

    valid_states = [s for s in model_states.values() if s is not None]
    cross_model_agreement = (len(set(valid_states)) == 1 and len(valid_states) == 3)

    # Consensus: 3-way agreement → that value; 2-1 split → majority; all-3-different → null
    state_counts: dict[str, int] = {}
    for s in valid_states:
        state_counts[s] = state_counts.get(s, 0) + 1
    if not state_counts:
        consensus_classification = None
    else:
        max_count = max(state_counts.values())
        winners = [s for s, c in state_counts.items() if c == max_count]
        if max_count >= 2 and len(winners) == 1:
            consensus_classification = winners[0]
        elif max_count == 3:
            consensus_classification = winners[0]
        else:
            consensus_classification = None

    if consensus_classification is None:
        consensus_vs_regex = "no_consensus"
    elif consensus_classification == regex_state:
        consensus_vs_regex = "match"
    else:
        consensus_vs_regex = "mismatch"

    out_of_vocab = []
    for label, r in responses.items():
        if r.get("out_of_vocab_state"):
            out_of_vocab.append([label, r["out_of_vocab_state"]])

    json_errors = []
    for label, r in responses.items():
        if r.get("json_parse_error") or r.get("call_error"):
            json_errors.append([label, r.get("call_error") or r.get("json_parse_error")])

    summary_per_lp[lp] = {
        "lp_id": lp,
        "lp_name": per_lp["lp_name"],
        "regex_classification": per_lp["regex_classification"],
        "model_classifications": model_states,
        "cross_model_agreement": cross_model_agreement,
        "consensus_classification": consensus_classification,
        "consensus_vs_regex": consensus_vs_regex,
        "elements_present_per_model": elements_present,
        "elements_missing_per_model": elements_missing,
        "justifications": justifications,
        "tenant_concern_per_model": tenant_concern,
        "out_of_vocab_responses": out_of_vocab,
        "errors": json_errors,
        "elapsed_sec": {label: r.get("elapsed_sec") for label, r in responses.items()},
    }

summary = {
    "experiment": "cross_model_coverage_classification_audit_2026_04_28",
    "lease": "T-10_Negotiated_Tennant_Lease.docx",
    "schema_version": schema.get("schema_version"),
    "target_lps": TARGET_LPS,
    "models": [
        {"label": label, "name": tgt.name, "provider": tgt.provider, "model": tgt.model}
        for label, tgt in MODEL_TARGETS
    ],
    "n_calls_attempted": len(TARGET_LPS) * len(MODEL_TARGETS),
    "n_call_errors": sum(
        1 for d in all_responses.values()
        for r in d["responses"].values()
        if r.get("call_error")
    ),
    "n_json_parse_errors": sum(
        1 for d in all_responses.values()
        for r in d["responses"].values()
        if r.get("json_parse_error") and not r.get("call_error")
    ),
    "n_out_of_vocab": sum(
        1 for d in all_responses.values()
        for r in d["responses"].values()
        if r.get("out_of_vocab_state")
    ),
    "per_lp": summary_per_lp,
    "total_elapsed_sec_per_model": {
        label: round(sum(
            (d["responses"].get(label, {}).get("elapsed_sec") or 0)
            for d in all_responses.values()
        ), 2)
        for label, _ in MODEL_TARGETS
    },
}

with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

# report.txt
lines: list[str] = []
lines.append("Cross-Model Coverage Classification Audit — Mechanical Diff Report")
lines.append("Date: 2026-04-28")
lines.append(f"Lease: {summary['lease']}")
lines.append(f"Schema version: {summary['schema_version']}")
lines.append("")
lines.append("Models:")
for m in summary["models"]:
    lines.append(f"  - {m['label']:<6} → {m['name']}")
lines.append("")
lines.append(f"Calls attempted: {summary['n_calls_attempted']}")
lines.append(f"Call errors    : {summary['n_call_errors']}")
lines.append(f"JSON parse errs: {summary['n_json_parse_errors']}")
lines.append(f"Out-of-vocab   : {summary['n_out_of_vocab']}")
lines.append(f"Elapsed/model  : {summary['total_elapsed_sec_per_model']}")
lines.append("")
lines.append("Per-LP breakdown:")
lines.append("")

for lp in TARGET_LPS:
    info = summary_per_lp[lp]
    reg = info["regex_classification"]
    lines.append(f"=== {lp} — {info['lp_name']} ===")
    lines.append(f"  regex_state             : {reg['coverage_state']}")
    lines.append(f"  regex_partial_class     : {reg.get('partial_class')}")
    lines.append(f"  regex_materiality       : {reg.get('materiality')}")
    lines.append(f"  regex_elements_found    : {reg.get('elements_found')}")
    lines.append(f"  regex_elements_missing  : {reg.get('elements_missing')}")
    lines.append("")
    lines.append(f"  model_classifications   :")
    for label in ("claude", "gpt", "grok"):
        s = info["model_classifications"].get(label)
        oov_marker = ""
        for ml, val in info["out_of_vocab_responses"]:
            if ml == label:
                oov_marker = " [OUT-OF-VOCAB]"
                break
        err_marker = ""
        for ml, val in info["errors"]:
            if ml == label:
                err_marker = f" [ERROR: {val}]"
                break
        lines.append(f"    {label:<6} : {s}{oov_marker}{err_marker}")
    lines.append(f"  cross_model_agreement   : {info['cross_model_agreement']}")
    lines.append(f"  consensus_classification: {info['consensus_classification']}")
    lines.append(f"  consensus_vs_regex      : {info['consensus_vs_regex']}")
    lines.append("")
    lines.append(f"  elements_present per model:")
    for label in ("claude", "gpt", "grok"):
        ep = info["elements_present_per_model"].get(label, [])
        lines.append(f"    {label:<6}: {ep}")
    lines.append(f"  elements_missing per model:")
    for label in ("claude", "gpt", "grok"):
        em = info["elements_missing_per_model"].get(label, [])
        lines.append(f"    {label:<6}: {em}")
    lines.append("")
    lines.append(f"  justifications:")
    for label in ("claude", "gpt", "grok"):
        j = info["justifications"].get(label, "")
        lines.append(f"    [{label.upper()}] {j}")
    lines.append("")
    lines.append(f"  tenant_concern_summary:")
    for label in ("claude", "gpt", "grok"):
        c = info["tenant_concern_per_model"].get(label, "")
        lines.append(f"    [{label.upper()}] {c}")
    lines.append("")

# Headline
lines.append("=" * 70)
lines.append("HEADLINE COUNTS (no outcome assigned — that is chat-side analysis)")
lines.append("=" * 70)
lp_with_cross_model_agreement = [lp for lp, info in summary_per_lp.items() if info["cross_model_agreement"]]
lp_consensus_match_regex = [lp for lp, info in summary_per_lp.items() if info["consensus_vs_regex"] == "match"]
lp_consensus_mismatch_regex = [lp for lp, info in summary_per_lp.items() if info["consensus_vs_regex"] == "mismatch"]
lp_no_consensus = [lp for lp, info in summary_per_lp.items() if info["consensus_vs_regex"] == "no_consensus"]
lines.append(f"  LPs with full 3-way model agreement     : {lp_with_cross_model_agreement}")
lines.append(f"  LPs where consensus matches regex       : {lp_consensus_match_regex}")
lines.append(f"  LPs where consensus mismatches regex    : {lp_consensus_mismatch_regex}")
lines.append(f"  LPs with no model consensus (3 splits)  : {lp_no_consensus}")

with open(OUT_DIR / "report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# ── 9. Final print (wrapped against console codec failure) ────────────────
try:
    print("\n" + "=" * 70, flush=True)
    print("CLASSIFICATION AUDIT COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"  Elapsed per model       : {summary['total_elapsed_sec_per_model']}", flush=True)
    print(f"  Call errors             : {summary['n_call_errors']}", flush=True)
    print(f"  JSON parse errors       : {summary['n_json_parse_errors']}", flush=True)
    print(f"  Out-of-vocab responses  : {summary['n_out_of_vocab']}", flush=True)
    print(f"  Cross-model agreement   : {len(lp_with_cross_model_agreement)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"  Consensus matches regex : {len(lp_consensus_match_regex)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"  Consensus != regex      : {len(lp_consensus_mismatch_regex)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"  No consensus (3 splits) : {len(lp_no_consensus)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"\nArtifacts: {OUT_DIR}", flush=True)
except Exception as e:
    sys.stderr.write(f"[final-print] suppressed console encoding error: {e!r}\n")
