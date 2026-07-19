"""
Step 429 — Gate C re-run harness (N=10), same method as 428.

Same document (real Atreca lease), same canonical_v2 profile, same prompt,
same declared config. The ONLY difference from 428 is the 429 fix to target
resolution in extract_parameters(). Measurement only — this harness changes
no source file.

Per 428 Method:
  each run: extract_parameters() -> attach_parameters_to_lp_evidence()
  for LP-02 and LP-07 -> enforce_gate_b()
  plus config-integrity assertion (prompt_hash / config_hash / canonical /
  fallback_used identical across all runs).
"""

import json
import os
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")

sys.path.insert(0, "C:/Users/Owner/OneDrive/CAM")

from cam.adapters.lease_review.lease_evidence_spans import (  # noqa: E402
    NORMALIZATION_PROFILE_V2,
    build_canonical_source,
    VERIFIED,
)
from cam.adapters.lease_review.lease_parameter_block import (  # noqa: E402
    DEPENDENCY_MAP,
    attach_parameters_to_lp_evidence,
    enforce_gate_b,
    extract_parameters,
)
from cam.adapters.lease_review.lease_adapter import GateAbortError  # noqa: E402
from cam.adapters.lease_review.lease_element_elicitation import (  # noqa: E402
    UnresolvableTargetError,
)

DOC = Path("C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt")
N_RUNS = 10
OUT = Path("C:/Users/Owner/OneDrive/CAM/build_log/_429_gate_c_results.json")

PARAMS = ["tenant_share", "building_share", "rent_adjustment_pct", "base_rent"]


def main():
    tenant_text = DOC.read_text(encoding="utf-8")
    source = build_canonical_source(
        tenant_text,
        run_id="429-gate-c",
        normalization_profile=NORMALIZATION_PROFILE_V2,
    )
    print(f"source_document_hash = {source.source_document_hash}")
    print(f"canonical_text_hash  = {source.canonical_text_hash}")
    print(f"normalization_profile = {source.normalization_profile}")
    print(f"canonical_text length = {len(source.canonical_text)}\n")

    runs = []
    for i in range(1, N_RUNS + 1):
        record = {"run": i}
        try:
            result = extract_parameters(source, canonical=True)
            meta = result["meta"]
            params = result["parameters"]
            record["prompt_hash"] = meta.get("prompt_hash")
            record["config_hash"] = meta.get("config_hash")
            record["canonical"] = meta.get("canonical")
            record["fallback_used"] = meta.get("fallback_used")
            record["elapsed_sec"] = meta.get("elapsed_sec")
            record["degraded"] = meta.get("degraded")
            record["extracted"] = sorted(params.keys())
            record["parameters"] = {
                name: {
                    "status": p.span.verification_status,
                    "start_char": p.span.start_char,
                    "end_char": p.span.end_char,
                    "span_text": p.span.span_text,
                    "elicited_target": p.provenance.get("elicited_target"),
                }
                for name, p in params.items()
            }
            record["attachment"] = {
                lp: [p.name for p in attach_parameters_to_lp_evidence(params, lp)]
                for lp in DEPENDENCY_MAP
            }
            try:
                gate = enforce_gate_b(params, canonical=True)
                record["gate_b"] = gate["gate_status"]
                record["gate_b_failures"] = gate["failures"]
            except GateAbortError as e:
                record["gate_b"] = "abort"
                record["gate_b_error"] = str(e)
        except UnresolvableTargetError as e:
            record["error_type"] = "UnresolvableTargetError"
            record["error"] = str(e)
            record["gate_b"] = "not_reached"
        except Exception as e:  # noqa: BLE001
            record["error_type"] = type(e).__name__
            record["error"] = str(e)
            record["traceback"] = traceback.format_exc()
            record["gate_b"] = "not_reached"

        runs.append(record)
        print(f"run {i:2d}: extracted={record.get('extracted')} "
              f"gate_b={record.get('gate_b')} "
              f"elapsed={record.get('elapsed_sec')} "
              f"{record.get('error_type', '')}")

    out = {
        "n_runs": N_RUNS,
        "source_document_hash": source.source_document_hash,
        "canonical_text_hash": source.canonical_text_hash,
        "normalization_profile": source.normalization_profile,
        "runs": runs,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    # ── Config integrity (416 class) ──
    print("\n=== CONFIG INTEGRITY ===")
    for key in ("prompt_hash", "config_hash", "canonical", "fallback_used"):
        vals = {r.get(key) for r in runs if key in r}
        print(f"{key}: {vals}")

    # ── Per-parameter extraction rate / offset / text stability ──
    print("\n=== PER-PARAMETER (N=10) ===")
    for name in PARAMS:
        hits = [r for r in runs if name in r.get("parameters", {})]
        offsets = {(r["parameters"][name]["start_char"], r["parameters"][name]["end_char"]) for r in hits}
        texts = {r["parameters"][name]["span_text"] for r in hits}
        print(f"{name}: {len(hits)}/{N_RUNS} | offsets={offsets} | distinct_texts={len(texts)}")
        for t in texts:
            print(f"    span_text: {t!r}")

    print("\n=== GATE B ===")
    for r in runs:
        print(f"run {r['run']:2d}: {r.get('gate_b')}")

    print("\n=== ATTACHMENT ===")
    for r in runs:
        print(f"run {r['run']:2d}: {r.get('attachment')}")

    print(f"\nresults -> {OUT}")


if __name__ == "__main__":
    main()
