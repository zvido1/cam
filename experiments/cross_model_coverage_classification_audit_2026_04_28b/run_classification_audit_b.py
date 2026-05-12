"""Cross-Model Coverage CLASSIFICATION Audit — RE-RUN against schema v1.1.4.

This is the Step 268 re-audit. Same methodology as the original
run_classification_audit.py (Step 267), but:
  1. Reads the post-bump T-10 fresh-run pipeline JSON from
     experiments/step_268_t10_post_bump/pipeline_results.json so the
     regex baseline reflects v1.1.4.
  2. Loads the post-bump schema v1.1.4 — so the prompts shown to all 3
     models include the updated coverage_state_rules text for LP-11 and
     LP-13 and the new LP-11 notes field.
  3. Reuses the cached extraction from
     experiments/cross_model_coverage_classification_audit_2026_04_28/00_audit_inputs.json
     (extraction is non-deterministic and we want apples-to-apples
     vs the original audit, so we keep the same tenant_text per LP).
  4. Writes outputs to the *_audit_2026_04_28b/ directory to preserve
     the original audit's artifacts.

Constraint: same as original — no cam/core/ modifications, no production
module modifications. Re-uses ProviderRouter + the existing models /
prompt-construction logic already shipped in the original audit script.
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
for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"):
    assert os.environ.get(var), f"{var} missing after load"
print("[setup] API keys loaded for openai/anthropic/xai (proxy URLs cleared)", flush=True)

PROJECT_ROOT = Path(r"C:/Users/Owner/OneDrive/CAM")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "05 Lease Analyzer"))

OUT_DIR = PROJECT_ROOT / "experiments" / "cross_model_coverage_classification_audit_2026_04_28b"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_PATH = (
    PROJECT_ROOT / "cam" / "adapters" / "lease_review" / "schemas"
    / "retail_lease_knowledge.json"
)
POST_BUMP_RUN = (
    PROJECT_ROOT / "experiments" / "step_268_t10_post_bump"
    / "pipeline_results.json"
)
ORIGINAL_INPUTS = (
    PROJECT_ROOT / "experiments" / "cross_model_coverage_coverage_audit_2026_04_28"
    / "00_audit_inputs.json"
)
# fix: the original audit dir is …classification_audit_…
ORIGINAL_INPUTS = (
    PROJECT_ROOT / "experiments" / "cross_model_coverage_classification_audit_2026_04_28"
    / "00_audit_inputs.json"
)
INPUTS_FILE = OUT_DIR / "00_audit_inputs.json"

assert SCHEMA_PATH.exists(), SCHEMA_PATH
assert POST_BUMP_RUN.exists(), POST_BUMP_RUN
assert ORIGINAL_INPUTS.exists(), ORIGINAL_INPUTS

TARGET_LPS = ["LP-07", "LP-09", "LP-11", "LP-13", "LP-14"]

# ── 2. Load schema v1.1.4 ─────────────────────────────────────────────────
with open(SCHEMA_PATH, encoding="utf-8") as f:
    schema = json.load(f)

assert schema["schema_version"] == "1.1.4", (
    f"Expected schema v1.1.4 for re-audit; got {schema['schema_version']}"
)
print(f"[setup] Schema version: {schema['schema_version']}", flush=True)

coverage_states_vocab = schema["coverage_states"]
issue_areas_by_id = {ia["id"]: ia for ia in schema["issue_areas"]}

# ── 3. Load post-bump regex output ─────────────────────────────────────────
with open(POST_BUMP_RUN, encoding="utf-8") as f:
    post = json.load(f)

regex_assessments_by_id = {a["issue_area_id"]: a for a in post.get("coverage_assessment", [])}
for lp in TARGET_LPS:
    assert lp in regex_assessments_by_id, f"Post-bump run missing regex output for {lp}"

# ── 4. Reuse the original audit's saved extraction (same tenant_text) ──────
with open(ORIGINAL_INPUTS, encoding="utf-8") as f:
    original_inputs = json.load(f)

extraction = original_inputs["extraction"]
provisions_by_id = {p["provision_id"]: p for p in extraction["provisions"]}
for lp in TARGET_LPS:
    assert lp in provisions_by_id, f"Extraction missing tenant_text for {lp}"

# ── 5. Build 00_audit_inputs.json for the re-audit ────────────────────────
audit_inputs = {
    "experiment": "cross_model_coverage_classification_audit_2026_04_28b",
    "predecessor": "cross_model_coverage_classification_audit_2026_04_28",
    "lease": "T-10_Negotiated_Tennant_Lease.docx",
    "schema_version": schema.get("schema_version"),
    "coverage_states_vocab": coverage_states_vocab,
    "target_lps": TARGET_LPS,
    "extraction": extraction,
    "regex_outputs_by_lp": {},
    "schema_inputs_by_lp": {},
    "post_bump_pipeline_results_path": str(POST_BUMP_RUN.relative_to(PROJECT_ROOT)),
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
print(f"[setup] Saved re-audit inputs to {INPUTS_FILE.name}", flush=True)


# ── 6. IDENTICAL prompt template (matches original audit script) ──────────
def render_numbered(items: list) -> str:
    return "\n".join(f"  {i}. {item}" for i, item in enumerate(items, 1))


def render_dict_bullets(d: dict) -> str:
    if not d:
        return "  (none)"
    return "\n".join(f"  - {k}: {v}" for k, v in d.items())


def build_prompt(lp_id: str) -> tuple[str, str]:
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


# ── 7. Models ─────────────────────────────────────────────────────────────
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
        name="xai:grok-4.3",
        provider="xai",
        model="grok-4.3",
        max_output_tokens=1500,
        temperature=0.0,
        timeout_sec=180.0,
    )),
]

PERMITTED_STATES = set(coverage_states_vocab.keys())


def parse_model_json(raw: str) -> tuple[dict | None, str | None]:
    if not raw:
        return None, "empty_response"
    text = raw.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
        text = text.strip()
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
        "model_label": target.name, "provider": target.provider, "model": target.model,
        "raw_response": None, "parsed": None, "json_parse_error": None,
        "out_of_vocab_state": None, "call_error": None, "elapsed_sec": None,
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


# ── 8. Execute 5 × 3 = 15 calls ───────────────────────────────────────────
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
    print(f"  regex_state(post-bump)={per_lp['regex_classification']['coverage_state']}", flush=True)

    for label, target in MODEL_TARGETS:
        result = call_one(target, sys_prompt, user_prompt)
        per_lp["responses"][label] = result
        with open(OUT_DIR / f"{lp}_{label}.json", "w", encoding="utf-8") as f:
            json.dump({
                "lp_id": lp, "model_label": label, "model_target": result["model_label"],
                "system_prompt": sys_prompt, "user_prompt": user_prompt,
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


# ── 9. summary.json + report.txt ──────────────────────────────────────────
def get_state(r):
    p = r.get("parsed")
    return p.get("coverage_state") if isinstance(p, dict) else None
def get_list(r, key):
    p = r.get("parsed")
    v = p.get(key) if isinstance(p, dict) else None
    return v if isinstance(v, list) else []
def get_just(r):
    p = r.get("parsed")
    return str((p or {}).get("justification") or "")

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
    state_counts = {}
    for s in valid_states:
        state_counts[s] = state_counts.get(s, 0) + 1
    if not state_counts:
        consensus = None
    else:
        max_count = max(state_counts.values())
        winners = [s for s, c in state_counts.items() if c == max_count]
        if max_count >= 2 and len(winners) == 1:
            consensus = winners[0]
        elif max_count == 3:
            consensus = winners[0]
        else:
            consensus = None
    if consensus is None:
        cvr = "no_consensus"
    elif consensus == regex_state:
        cvr = "match"
    else:
        cvr = "mismatch"
    out_of_vocab = [[label, r["out_of_vocab_state"]] for label, r in responses.items() if r.get("out_of_vocab_state")]
    errors = [[label, r.get("call_error") or r.get("json_parse_error")] for label, r in responses.items() if r.get("call_error") or r.get("json_parse_error")]
    summary_per_lp[lp] = {
        "lp_id": lp, "lp_name": per_lp["lp_name"],
        "regex_classification": per_lp["regex_classification"],
        "model_classifications": model_states,
        "cross_model_agreement": cross_model_agreement,
        "consensus_classification": consensus,
        "consensus_vs_regex": cvr,
        "elements_present_per_model": elements_present,
        "elements_missing_per_model": elements_missing,
        "justifications": justifications,
        "tenant_concern_per_model": tenant_concern,
        "out_of_vocab_responses": out_of_vocab,
        "errors": errors,
        "elapsed_sec": {label: r.get("elapsed_sec") for label, r in responses.items()},
    }

summary = {
    "experiment": "cross_model_coverage_classification_audit_2026_04_28b",
    "predecessor": "cross_model_coverage_classification_audit_2026_04_28",
    "lease": "T-10_Negotiated_Tennant_Lease.docx",
    "schema_version": schema.get("schema_version"),
    "target_lps": TARGET_LPS,
    "models": [{"label": l, "name": t.name, "provider": t.provider, "model": t.model} for l, t in MODEL_TARGETS],
    "n_calls_attempted": len(TARGET_LPS) * len(MODEL_TARGETS),
    "n_call_errors": sum(1 for d in all_responses.values() for r in d["responses"].values() if r.get("call_error")),
    "n_json_parse_errors": sum(1 for d in all_responses.values() for r in d["responses"].values() if r.get("json_parse_error") and not r.get("call_error")),
    "n_out_of_vocab": sum(1 for d in all_responses.values() for r in d["responses"].values() if r.get("out_of_vocab_state")),
    "per_lp": summary_per_lp,
    "total_elapsed_sec_per_model": {l: round(sum((d["responses"].get(l,{}).get("elapsed_sec") or 0) for d in all_responses.values()), 2) for l, _ in MODEL_TARGETS},
}
with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

lines: list[str] = []
lines.append("Cross-Model Coverage Classification Audit — RE-RUN against schema v1.1.4")
lines.append("Date: 2026-04-28")
lines.append(f"Lease: {summary['lease']}")
lines.append(f"Schema version: {summary['schema_version']}")
lines.append(f"Predecessor audit: {summary['predecessor']}")
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
    lines.append(f"  regex_state (v1.1.4)    : {reg['coverage_state']}")
    lines.append(f"  regex_partial_class     : {reg.get('partial_class')}")
    lines.append(f"  regex_materiality       : {reg.get('materiality')}")
    lines.append(f"  regex_evidence_summary  : {reg.get('evidence_summary','')}")
    lines.append(f"  regex_elements_found    : {reg.get('elements_found')}")
    lines.append(f"  regex_elements_missing  : {reg.get('elements_missing')}")
    lines.append("")
    lines.append(f"  model_classifications   :")
    for label in ("claude", "gpt", "grok"):
        s = info["model_classifications"].get(label)
        oov = ""
        for ml, val in info["out_of_vocab_responses"]:
            if ml == label: oov = " [OUT-OF-VOCAB]"; break
        err = ""
        for ml, val in info["errors"]:
            if ml == label: err = f" [ERROR: {val}]"; break
        lines.append(f"    {label:<6} : {s}{oov}{err}")
    lines.append(f"  cross_model_agreement   : {info['cross_model_agreement']}")
    lines.append(f"  consensus_classification: {info['consensus_classification']}")
    lines.append(f"  consensus_vs_regex      : {info['consensus_vs_regex']}")
    lines.append("")
    lines.append(f"  elements_present per model:")
    for label in ("claude","gpt","grok"):
        lines.append(f"    {label:<6}: {info['elements_present_per_model'].get(label, [])}")
    lines.append(f"  elements_missing per model:")
    for label in ("claude","gpt","grok"):
        lines.append(f"    {label:<6}: {info['elements_missing_per_model'].get(label, [])}")
    lines.append("")
    lines.append(f"  justifications:")
    for label in ("claude","gpt","grok"):
        lines.append(f"    [{label.upper()}] {info['justifications'].get(label,'')}")
    lines.append("")
    lines.append(f"  tenant_concern_summary:")
    for label in ("claude","gpt","grok"):
        lines.append(f"    [{label.upper()}] {info['tenant_concern_per_model'].get(label,'')}")
    lines.append("")

lines.append("=" * 70)
lines.append("HEADLINE COUNTS (no outcome assigned — that is chat-side analysis)")
lines.append("=" * 70)
lp_full = [lp for lp, info in summary_per_lp.items() if info["cross_model_agreement"]]
lp_match = [lp for lp, info in summary_per_lp.items() if info["consensus_vs_regex"] == "match"]
lp_mismatch = [lp for lp, info in summary_per_lp.items() if info["consensus_vs_regex"] == "mismatch"]
lp_none = [lp for lp, info in summary_per_lp.items() if info["consensus_vs_regex"] == "no_consensus"]
lines.append(f"  LPs with full 3-way model agreement     : {lp_full}")
lines.append(f"  LPs where consensus matches regex       : {lp_match}")
lines.append(f"  LPs where consensus mismatches regex    : {lp_mismatch}")
lines.append(f"  LPs with no model consensus (3 splits)  : {lp_none}")

with open(OUT_DIR / "report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

try:
    print("\n" + "=" * 70, flush=True)
    print("RE-AUDIT COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"  Elapsed per model       : {summary['total_elapsed_sec_per_model']}", flush=True)
    print(f"  Call errors             : {summary['n_call_errors']}", flush=True)
    print(f"  JSON parse errors       : {summary['n_json_parse_errors']}", flush=True)
    print(f"  Out-of-vocab            : {summary['n_out_of_vocab']}", flush=True)
    print(f"  3-way model agreement   : {len(lp_full)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"  Consensus matches regex : {len(lp_match)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"  Consensus != regex      : {len(lp_mismatch)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"  No consensus            : {len(lp_none)} / {len(TARGET_LPS)} LPs", flush=True)
    print(f"\nArtifacts: {OUT_DIR}", flush=True)
except Exception as e:
    sys.stderr.write(f"[final-print] suppressed console encoding error: {e!r}\n")
