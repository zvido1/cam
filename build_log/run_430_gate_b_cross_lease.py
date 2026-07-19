"""
Step 430 — Gate B cross-lease measurement (Atreca + Atlas). READ-ONLY.

Runs the 427/429 parameter block through its declared Gate B on the lease it
was built from (Atreca) and a lease it has never seen (Atlas), N=5 each, and
classifies every unsatisfied dependency as absent_by_structure /
present_variant / present_but_missed.

This script modifies NO source module. It imports the parameter block and the
423A substrate and calls them. `enforce_gate_b` is called in canonical=False
(report) mode ONLY — canonical mode raises on the first unsatisfied
dependency and would hide the full failure structure, which is the wrong mode
for a measurement.

The classification probe is HARNESS-SIDE DIAGNOSTIC SCAFFOLDING. It reads
PARAMETER_TARGETS for declared labels/synonyms and does deterministic
substring probes against the canonical text. It imports no decision logic and
changes no gate. The alias list below is likewise harness-side only and never
enters the source module.
"""

import json
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env")

sys.path.insert(0, r"C:\Users\Owner\OneDrive\CAM")

from cam.adapters.lease_review.lease_parser import parse_document  # noqa: E402
from cam.adapters.lease_review.lease_evidence_spans import (  # noqa: E402
    NORMALIZATION_PROFILE_V2,
    build_canonical_source,
    VERIFIED,
)
from cam.adapters.lease_review.lease_parameter_block import (  # noqa: E402
    DEPENDENCY_MAP,
    PARAMETER_TARGETS,
    check_gate_b,
    enforce_gate_b,
    extract_parameters,
)

CAM = Path(r"C:\Users\Owner\OneDrive\CAM")
LEASES = [
    ("atreca", CAM / "05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt"),
    ("atlas", CAM / "05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt"),
]
N_RUNS = 5
OUT_JSON = CAM / "build_log/430_gate_b_cross_lease_sidecar.json"
PARAM_ORDER = [t["param_name"] for t in PARAMETER_TARGETS]

# ── HARNESS-SIDE ONLY: near-label aliases for present_variant tagging ──────────
# Explicit, hardcoded, no fuzzy matching. These are NOT declared parameter
# synonyms and are NEVER written back into PARAMETER_TARGETS. They exist so a
# concept present under a different name is not silently reported as absent.
HARNESS_ALIASES = {
    "tenant_share": ["Proportionate Share", "Tenant's Proportionate Share", "Tenant's Share"],
    "building_share": ["Building's Share", "Project Operating Expenses", "Building's Proportionate Share"],
    "rent_adjustment_pct": ["annual escalation", "escalation of approximately", "Rent Adjustment", "increase in Base Rent"],
    "base_rent": ["Base Rent", "annual rent", "per rentable square foot"],
}


def _norm(s: str) -> str:
    """Deterministic probe normalization: unify curly quotes/apostrophes and
    case. NOT fuzzy matching — a fixed character mapping plus casefold, so a
    straight-vs-curly apostrophe cannot produce a false 'absent_by_structure'.
    (Both fixtures in fact use straight quotes only; this is defensive.)"""
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), (" ", " ")):
        s = s.replace(a, b)
    return s.casefold()


def probe(canonical_text: str, needle: str):
    """Deterministic substring probe. Returns (found, offset, excerpt)."""
    hay, ndl = _norm(canonical_text), _norm(needle)
    idx = hay.find(ndl)
    if idx < 0:
        return False, None, None
    start = max(0, idx - 60)
    end = min(len(canonical_text), idx + len(ndl) + 90)
    return True, idx, canonical_text[start:end]


def classify_miss(param_name: str, canonical_text: str) -> dict:
    """Classify an unresolved parameter. Declared labels/synonyms first
    (a hit there = present_but_missed = genuine defect), then harness-side
    aliases (present_variant), else absent_by_structure."""
    target = next(t for t in PARAMETER_TARGETS if t["param_name"] == param_name)
    declared = [target["element_label"]] + list(target.get("synonyms", []))

    declared_hits = []
    for needle in declared:
        found, off, exc = probe(canonical_text, needle)
        if found:
            declared_hits.append({"needle": needle, "offset": off, "excerpt": exc})

    alias_hits = []
    for needle in HARNESS_ALIASES.get(param_name, []):
        found, off, exc = probe(canonical_text, needle)
        if found:
            alias_hits.append({"needle": needle, "offset": off, "excerpt": exc})

    if declared_hits:
        classification = "present_but_missed"
    elif alias_hits:
        classification = "present_variant"
    else:
        classification = "absent_by_structure"

    return {
        "classification": classification,
        "declared_needles_probed": declared,
        "declared_hits": declared_hits,
        "alias_needles_probed": HARNESS_ALIASES.get(param_name, []),
        "alias_hits": alias_hits,
    }


def run_lease(slug: str, path: Path) -> dict:
    print(f"\n{'='*70}\n{slug.upper()}  {path.name}\n{'='*70}")
    raw_text = parse_document(str(path))
    print(f"parsed raw chars = {len(raw_text)}")

    runs = []
    canonical_text_ref = None
    for i in range(1, N_RUNS + 1):
        rec = {"run": i}
        try:
            source = build_canonical_source(
                raw_text,
                run_id=f"430-{slug}-{i}",
                normalization_profile=NORMALIZATION_PROFILE_V2,
            )
            canonical_text_ref = source.canonical_text
            rec["source_document_hash"] = source.source_document_hash
            rec["canonical_text_hash"] = source.canonical_text_hash
            rec["canonical_len"] = len(source.canonical_text)

            result = extract_parameters(source, canonical=True)
            meta, params = result["meta"], result["parameters"]
            rec["prompt_hash"] = meta.get("prompt_hash")
            rec["config_hash"] = meta.get("config_hash")
            rec["canonical"] = meta.get("canonical")
            rec["fallback_used"] = meta.get("fallback_used")
            rec["elapsed_sec"] = meta.get("elapsed_sec")
            rec["parameters"] = {
                name: {
                    "status": p.span.verification_status,
                    "start_char": p.span.start_char,
                    "end_char": p.span.end_char,
                    "span_text": p.span.span_text,
                    "elicited_target": p.provenance.get("elicited_target"),
                }
                for name, p in params.items()
                if p.span.verification_status == VERIFIED
            }
            rec["check_gate_b"] = check_gate_b(params)
            rec["enforce_gate_b_report_mode"] = enforce_gate_b(params, canonical=False)
        except Exception as e:  # noqa: BLE001
            rec["error_type"] = type(e).__name__
            rec["error"] = str(e)
            rec["traceback"] = traceback.format_exc()
        runs.append(rec)
        print(f"  run {i}: resolved={sorted(rec.get('parameters', {}).keys())} "
              f"gate={rec.get('enforce_gate_b_report_mode', {}).get('gate_status', rec.get('error_type'))} "
              f"elapsed={rec.get('elapsed_sec')}")

    # ── Per-parameter aggregation across the 5 runs ──
    per_param = {}
    for name in PARAM_ORDER:
        hits = [r for r in runs if name in r.get("parameters", {})]
        offsets = sorted({(r["parameters"][name]["start_char"], r["parameters"][name]["end_char"]) for r in hits})
        texts = sorted({r["parameters"][name]["span_text"] for r in hits})
        targets = sorted({r["parameters"][name]["elicited_target"] for r in hits})
        entry = {
            "resolution_rate": f"{len(hits)}/{N_RUNS}",
            "resolved_runs": len(hits),
            "offsets": [list(o) for o in offsets],
            "offset_stable": len(offsets) <= 1,
            "distinct_span_texts": len(texts),
            "span_texts": texts,
            "elicited_targets": targets,
        }
        if len(hits) < N_RUNS and canonical_text_ref is not None:
            entry["miss_classification"] = classify_miss(name, canonical_text_ref)
        per_param[name] = entry

    return {"slug": slug, "path": str(path), "raw_chars": len(raw_text), "runs": runs, "per_parameter": per_param}


def main():
    results = {"n_runs": N_RUNS, "dependency_map": DEPENDENCY_MAP, "leases": {}}
    for slug, path in LEASES:
        results["leases"][slug] = run_lease(slug, path)

    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")

    for slug in results["leases"]:
        L = results["leases"][slug]
        print(f"\n{'='*70}\nSUMMARY — {slug.upper()}\n{'='*70}")
        for key in ("prompt_hash", "config_hash", "canonical", "fallback_used",
                    "source_document_hash", "canonical_text_hash"):
            vals = {r.get(key) for r in L["runs"] if key in r}
            print(f"  {key}: {vals}")
        print("  --- per parameter (N=5) ---")
        for name in PARAM_ORDER:
            e = L["per_parameter"][name]
            line = f"  {name:22s} {e['resolution_rate']}  offsets={e['offsets']}  texts={e['distinct_span_texts']}"
            if "miss_classification" in e:
                line += f"  [{e['miss_classification']['classification']}]"
            print(line)
            for t in e["span_texts"]:
                print(f"      span_text: {t!r}")
            mc = e.get("miss_classification")
            if mc:
                print(f"      declared probed: {mc['declared_needles_probed']}")
                print(f"      declared hits:   {[h['needle'] for h in mc['declared_hits']]}")
                print(f"      alias hits:      {[h['needle'] for h in mc['alias_hits']]}")
                for h in mc["alias_hits"]:
                    print(f"        @{h['offset']}: {h['excerpt']!r}")
        print("  --- gate b (report mode) per run ---")
        for r in L["runs"]:
            g = r.get("enforce_gate_b_report_mode", {})
            fails = [(f["lp_id"], f["dependency"]) for f in g.get("failures", [])]
            print(f"    run {r['run']}: {g.get('gate_status', r.get('error_type'))}  failures={fails}")

    print(f"\nsidecar -> {OUT_JSON}")


if __name__ == "__main__":
    main()
