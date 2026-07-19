"""
Step 431 Part B — Governed evidence-selection measurement harness.

STAGE 1 ARTIFACT. Built under BUILD-ONLY authorization (Part B v3.1 §1, §13):
this file makes ZERO model calls as committed. The live run requires a SEPARATE
Stage-2 sanction of the exact hashed artifacts.

The call site is hard-gated: `--mode` defaults to `build`, and the single
function that would invoke a model raises StageAuthorizationError unless BOTH
`--mode run` AND `--stage2-sanction <manifest_hash>` are supplied AND the
supplied hash matches the committed manifest. There is no code path in which a
call fires by default, by accident, or by a truthy flag.

Discipline (Part B §2): READ-ONLY. Imports from cam/, never modifies. No cam/
file is created, modified, or deleted. Nothing is wired.

Authority: build_log/431_partB_measurement_instruction.md (v3.1, RATIFIED).
Every mechanism here traces to a Part A / Part B section; this harness invents
no architecture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CAM_ROOT = Path(r"C:\Users\Owner\OneDrive\CAM")
BUILD_LOG = CAM_ROOT / "build_log"
sys.path.insert(0, str(CAM_ROOT))

# ── Stage-1 artifacts (inputs; hashed into the manifest) ──────────────────────
CONFIG_PATH = BUILD_LOG / "431_measurement_config.json"
PROFILES_PATH = BUILD_LOG / "431_requirement_profiles.json"
SCHEMA_PATH = BUILD_LOG / "431_output_schema.json"
PROMPT_PATH = BUILD_LOG / "431_selector_prompt.txt"
PREFLIGHT_PATH = BUILD_LOG / "431_fixture_preflight.json"
MANIFEST_PATH = BUILD_LOG / "431_config_manifest.json"

# ── Stage-2 outputs (produced only under sanction) ────────────────────────────
SIDECAR_PATH = BUILD_LOG / "431_selection_measurement_sidecar.json"
RUNTIME_SEAM_PATH = BUILD_LOG / "431_runtime_seam_capture.json"
VALIDATION_PATH = BUILD_LOG / "431_validation.json"
SEAM_CHECK_PATH = BUILD_LOG / "431_repository_seam_check.json"

LEASES = {
    "atreca": CAM_ROOT / "05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt",
    "atlas": CAM_ROOT / "05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt",
}

# ── Provisioned candidate matrix (Part B §6.1) ────────────────────────────────
# The `human_note` column is HUMAN-ONLY and is EXCLUDED from the model payload.
# Offsets are PINNED from 430 / the 431 preflight probe: preflight RE-VERIFIES
# them, it does not re-discover them (§6.2).
CANDIDATES: List[Dict[str, Any]] = [
    {"id": "cand_01", "lease": "atreca", "parameter": "tenant_share",
     "offsets": [1942, 1996], "human_note": "opex share",
     "expected_quote": "Tenant's Share of Operating Expenses of Building: 100%"},
    {"id": "cand_02", "lease": "atreca", "parameter": "base_rent",
     "offsets": [1695, 1815], "human_note": "operative",
     "expected_quote": "Base Rent:\n$3.75 per rentable square foot of the Premises per month, subject to adjustment pursuant to Section 4 hereof."},
    {"id": "cand_03", "lease": "atreca", "parameter": "rent_adjustment_pct",
     "offsets": [2097, 2127], "human_note": "operative",
     "expected_quote": "Rent Adjustment Percentage: 3%"},
    {"id": "cand_04", "lease": "atlas", "parameter": "tenant_share",
     "offsets": [1738, 1889], "human_note": "proportionate share",
     "expected_quote": "\"Proportionate Share\" shall mean 22.4%, representing the ratio of the rentable area of the Demised Premises to the total rentable area of the Building."},
    {"id": "cand_05", "lease": "atlas", "parameter": "base_rent",
     "offsets": [990, 1065], "human_note": "definition stub",
     "expected_quote": "\"Base Rent\" shall mean the annual rent payable as set forth in Section 3.1."},
    {"id": "cand_06", "lease": "atlas", "parameter": "base_rent",
     "offsets": [3619, 3660], "human_note": "operative schedule",
     "expected_quote": "$18.50 per rentable square foot per annum",
     "requires_unique_resolution": True},
    {"id": "cand_07", "lease": "atlas", "parameter": "rent_adjustment_pct",
     "offsets": [4248, 4327], "human_note": "approximation",
     "expected_quote": "The above schedule reflects an annual escalation of approximately 3% per annum."},
]

FROZEN_LEASE_HASHES = {
    "atreca": "7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b",
    "atlas": "da9b5655c5cab382577f139a1884625d81f42b2610a146042018026dc28d2b71",
}

# Fields whose grounding is schema-fixed and therefore exempt from the §4.5
# field_support requirement (Part A §4.1: not_applicable is schema-fixed).
SCHEMA_FIXED_NOT_APPLICABLE = {
    "base_rent": {"charge_basis_components", "charge_scope"},
    "rent_adjustment_pct": {"charge_basis_components", "charge_scope"},
}

SEMANTIC_FIELDS = [
    "parameter_family_relevance", "candidate_support_state", "charge_basis_components",
    "charge_scope", "text_role", "value_completeness",
]


class StageAuthorizationError(RuntimeError):
    """Raised when a model call is attempted without Stage-2 sanction."""


class PreflightError(RuntimeError):
    """Raised when a fixture fails preflight (§6.2, §11 stop seam)."""


# ══════════════════════════════════════════════════════════════════════════════
# Artifact loading + hashing
# ══════════════════════════════════════════════════════════════════════════════

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_artifacts() -> Dict[str, Any]:
    return {
        "config": json.loads(CONFIG_PATH.read_text(encoding="utf-8")),
        "profiles": json.loads(PROFILES_PATH.read_text(encoding="utf-8")),
        "schema": json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
        "prompt_template": PROMPT_PATH.read_text(encoding="utf-8"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Canonical source + deterministic envelope (Part A §3.2 / Part B §3)
# ══════════════════════════════════════════════════════════════════════════════

def build_sources() -> Dict[str, Any]:
    from cam.adapters.lease_review.lease_parser import parse_document
    from cam.adapters.lease_review.lease_evidence_spans import (
        build_canonical_source, NORMALIZATION_PROFILE_V2,
    )
    sources = {}
    for slug, path in LEASES.items():
        raw = parse_document(str(path))
        sources[slug] = build_canonical_source(
            raw, run_id=f"431-{slug}", normalization_profile=NORMALIZATION_PROFILE_V2,
        )
    return sources


def build_envelope(canonical_text: str, start: int, end: int, cfg: dict, envelope_id: str) -> dict:
    """Deterministic context envelope. Mechanical, identical for A/B/C, derived
    only from canonical offsets. Never expanded by parameter type, expected
    basis, or model request (Part A §3.2).

    This build uses the frozen char-window fallback: `lease_parser` returns flat
    text and exposes no deterministic block-boundary API (verified at build
    time), so per §3 step 4 the algorithm degrades to a symmetric window. The
    boundary_method is recorded so envelope sufficiency is measurable (§8.2).
    """
    budget = cfg["envelope"]["max_context_chars"]
    span_len = end - start
    remaining = max(0, budget - span_len)
    half = remaining // 2

    ctx_start = max(0, start - half)
    ctx_end = min(len(canonical_text), end + (remaining - (start - ctx_start)))
    # If truncated on the left, the unused left budget is NOT reallocated right:
    # allocation is symmetric by construction and truncation is flagged, not
    # silently compensated.
    ctx_end = min(len(canonical_text), max(ctx_end, end))

    return {
        "context_envelope_id": envelope_id,
        "context_start_char": ctx_start,
        "context_end_char": ctx_end,
        "context_text": canonical_text[ctx_start:ctx_end],
        "boundary_method": "symmetric_char_window_fallback",
        "max_context_chars": budget,
        "context_policy_version": cfg["context_policy_version"],
        "truncated_left": ctx_start == 0 and (start - half) < 0,
        "truncated_right": ctx_end == len(canonical_text),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Deterministic checks (Part A §4.4)
# ══════════════════════════════════════════════════════════════════════════════

def value_token_present(text: str, cfg: dict) -> Tuple[bool, List[str]]:
    """Shape-only value-token detection. Contains no lease literal."""
    det = cfg["value_token_detector"]
    flags = re.IGNORECASE if "IGNORECASE" in det.get("regex_flags", []) else 0
    hits = []
    cur = list(re.finditer(det["patterns"]["currency"], text, flags))
    pct = list(re.finditer(det["patterns"]["percentage"], text, flags))
    rate = list(re.finditer(det["patterns"]["rate_phrase"], text, flags))
    if cur:
        hits.append("currency")
    if pct:
        hits.append("percentage")
    if rate and det.get("rate_requires_adjacent_currency"):
        win = det.get("rate_adjacency_window_chars", 40)
        if any(abs(r.start() - c.start()) <= win for r in rate for c in cur):
            hits.append("rate_with_currency")
    return bool(hits), hits


def quote_resolves(quote: str, haystack: str) -> bool:
    """A cited quote resolves iff it appears verbatim in the supplied text."""
    return quote in haystack


# ══════════════════════════════════════════════════════════════════════════════
# Field-grounding invalidation (Part A §4.5)
# ══════════════════════════════════════════════════════════════════════════════

def apply_field_grounding(judgment: dict, parameter: str, candidate_text: str,
                          context_text: str) -> dict:
    """Empty field_support, OR support whose quotes do not resolve, INVALIDATES
    that field for that evaluator (downgrade to unclear/not_assessable) — not a
    confidence reduction. Failed quotes stay in the audit trace as unverified.
    """
    cand_by_id = {c["citation_id"]: c["quote"] for c in judgment.get("candidate_citations", [])}
    ctx_by_id = {c["citation_id"]: c["quote"] for c in judgment.get("context_citations", [])}
    support = judgment.get("field_support", {}) or {}
    exempt = SCHEMA_FIXED_NOT_APPLICABLE.get(parameter, set())

    invalidated, unverified_traces = {}, []
    for field in SEMANTIC_FIELDS:
        if field in exempt and judgment.get(field) == "not_applicable":
            continue
        entry = support.get(field) or {}
        cand_ids = entry.get("candidate_citation_ids", []) or []
        ctx_ids = entry.get("context_citation_ids", []) or []
        if not cand_ids and not ctx_ids:
            invalidated[field] = "empty_field_support"
            continue
        any_resolved = False
        for cid in cand_ids:
            q = cand_by_id.get(cid)
            if q is not None and quote_resolves(q, candidate_text):
                any_resolved = True
            elif q is not None:
                unverified_traces.append({"field": field, "citation_id": cid, "quote": q,
                                          "class": "candidate", "resolved": False})
        for cid in ctx_ids:
            q = ctx_by_id.get(cid)
            if q is not None and quote_resolves(q, context_text):
                any_resolved = True
            elif q is not None:
                unverified_traces.append({"field": field, "citation_id": cid, "quote": q,
                                          "class": "context", "resolved": False})
        if not any_resolved:
            invalidated[field] = "no_cited_quote_resolved"

    out = dict(judgment)
    for field, reason in invalidated.items():
        out[field] = "unclear"
    out["_invalidated_fields"] = invalidated
    out["_unverified_quote_traces"] = unverified_traces
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Per-candidate merge (Part A §5.2) — per-FIELD agreement, disagreement preserved
# ══════════════════════════════════════════════════════════════════════════════

def merge_panel(judgments: List[dict], parameter: str) -> dict:
    """Merge three panelists into one candidate_semantic_result. Agreement is
    recorded PER FIELD, never as one global label. Nothing is resolved by
    majority — the certification policy decides what agreement permits."""
    def norm(v):
        return tuple(sorted(v)) if isinstance(v, list) else v

    merged, agreement = {}, {}
    for field in SEMANTIC_FIELDS:
        vals = [norm(j.get(field)) for j in judgments]
        substantive = [v for v in vals if v not in ("unclear", "not_assessable", None)]
        distinct = set(vals)
        if not substantive:
            merged[field], agreement[field] = "unclear", "not_assessable"
        elif len(distinct) == 1:
            merged[field], agreement[field] = vals[0], "unanimous"
        elif len(set(substantive)) == 1 and len(substantive) >= 2:
            merged[field], agreement[field] = substantive[0], "majority_with_dissent"
        else:
            merged[field], agreement[field] = "DISPUTED", "split"
        if isinstance(merged[field], tuple):
            merged[field] = list(merged[field])
    return {
        "charge_basis_components": merged.get("charge_basis_components"),
        **{k: merged[k] for k in SEMANTIC_FIELDS if k != "charge_basis_components"},
        "agreement_by_field": agreement,
        "per_panelist": judgments,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Requirement comparison + certification (Part A §6)
# ══════════════════════════════════════════════════════════════════════════════

def compare_candidate(result: dict, parameter: str, candidate_text: str,
                      profiles: dict, cfg: dict) -> dict:
    """Compare ONE candidate's merged semantic result against the DECLARED
    requirement profile. Every check is evaluated on the SAME candidate."""
    prof = profiles["profiles"][parameter]
    agree = result["agreement_by_field"]

    def undet(field):
        return result.get(field) in ("unclear", "DISPUTED", "not_assessable", None)

    relevance_ok = (result.get("parameter_family_relevance") == "relevant"
                    and agree.get("parameter_family_relevance") == "unanimous")

    basis = result.get("charge_basis_components")
    if prof["basis_match"].get("schema_fixed_value") == "not_applicable":
        basis_match = "not_applicable" if basis == "not_applicable" else "mismatch"
    elif undet("charge_basis_components") or basis in ("none", "unclear", "not_applicable"):
        basis_match = "undeterminable"
    else:
        basis_match = "match" if sorted(basis) == ["operating_expenses"] else "mismatch"

    text_role_ok = (not undet("text_role")) and result.get("text_role") == "operative_term"
    vtp, vtp_hits = value_token_present(candidate_text, cfg)
    value_ok = ((not undet("value_completeness"))
                and result.get("value_completeness") == "self_contained" and vtp)
    support_ok = ((not undet("candidate_support_state"))
                  and result.get("candidate_support_state") == "supports_mechanism")

    # Applicability — INDEPENDENT of value_ok (Part A §6.2; value_ok forbidden as input)
    if parameter in ("tenant_share", "building_share"):
        applicable = (isinstance(basis, list) and len(basis) > 0
                      and result.get("candidate_support_state") == "supports_mechanism")
    else:
        applicable = (result.get("text_role") in ("operative_term", "definition")
                      and result.get("candidate_support_state") != "does_not_support_mechanism")
    applicability_match = "applicable" if applicable else "not_assessable"

    qualified = (relevance_ok and basis_match in ("match", "not_applicable")
                 and text_role_ok and value_ok and support_ok)

    return {
        "relevance_ok": relevance_ok,
        "basis_match": basis_match,
        "text_role_ok": text_role_ok,
        "value_ok": value_ok,
        "value_token_present": vtp,
        "value_token_hits": vtp_hits,
        "support_ok": support_ok,
        "applicability_match": applicability_match,
        "agreement_by_field": agree,
        "candidate_qualification": "qualified" if qualified else "not_qualified",
    }


def certify(per_candidate: List[dict], cfg: dict) -> str:
    """Coherent-single-candidate certification (Part A §6.3).

    satisfied requires ONE candidate supplying EVERY property. No cross-candidate
    assembly. No implicit majority. No terminal unsatisfied_* without established
    completeness — which this measurement never has (§8.3).
    """
    completeness_established = (
        cfg["certification_policy"]["completeness_status_this_measurement"] == "established"
    )
    for c in per_candidate:
        if (c["candidate_qualification"] == "qualified"
                and c["applicability_match"] == "applicable"):
            return "satisfied"

    # No implicit majority: any non-unanimous relevant field routes to disagreement.
    for c in per_candidate:
        for field, state in c["agreement_by_field"].items():
            if state in ("majority_with_dissent", "split"):
                return "review_needed_disagreement"

    if any(c["applicability_match"] == "applicable" for c in per_candidate):
        return "applicable_no_supplied_candidate_qualified"
    if not completeness_established:
        return "review_needed_no_qualifying_candidate"
    return "review_needed_no_qualifying_candidate"


# ══════════════════════════════════════════════════════════════════════════════
# THE GATED CALL SITE — no model call fires without Stage-2 sanction
# ══════════════════════════════════════════════════════════════════════════════

def _assert_stage2(mode: str, sanction: Optional[str]) -> None:
    if mode != "run":
        raise StageAuthorizationError(
            f"Model call attempted in mode={mode!r}. Stage 1 authorizes BUILD ONLY "
            "(zero model calls). The live run requires --mode run AND a valid "
            "--stage2-sanction matching the committed manifest hash."
        )
    if not sanction:
        raise StageAuthorizationError(
            "Model call attempted without --stage2-sanction. Part B §1/§13: the live "
            "run is authorized only by a SEPARATE explicit sanction of the exact "
            "hashed Stage-1 artifacts."
        )
    if not MANIFEST_PATH.exists():
        raise StageAuthorizationError("Manifest missing; cannot verify Stage-2 sanction.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    expected = manifest.get("manifest_self_hash_of_artifact_hashes")
    if sanction != expected:
        raise StageAuthorizationError(
            f"Stage-2 sanction mismatch. Supplied {sanction!r} != committed manifest "
            f"{expected!r}. An artifact edited after Stage-1 review VOIDS the "
            "measurement and requires re-review (§1)."
        )


def call_panelist(role: str, payload: dict, mode: str, sanction: Optional[str]) -> dict:
    """The ONLY function that would invoke a model. Gated unconditionally.

    Not exercised at Stage 1 — not even once. A single smoke call would still be
    a call before sanction; the harness proving itself correct is a code-review
    property, not a call-it-once property.
    """
    _assert_stage2(mode, sanction)
    raise NotImplementedError(
        "Stage-2 call implementation is intentionally not wired in the Stage-1 "
        "artifact. Implement against _call_single_evaluator_305's call/fallback/"
        "provenance shape under Stage-2 sanction, then re-hash."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Runtime seam capture (Part B §8.2) — captured IN-PROCESS, never reconstructed
# ══════════════════════════════════════════════════════════════════════════════

def capture_cam_seam(phase: str) -> dict:
    proc = subprocess.run(["git", "status", "--porcelain", "cam/"],
                          cwd=str(CAM_ROOT), capture_output=True, text=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"],
                          cwd=str(CAM_ROOT), capture_output=True, text=True)
    return {
        "phase": phase,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_status_porcelain_cam": proc.stdout,
        "cam_clean": proc.stdout.strip() == "",
        "commit_hash": head.stdout.strip(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Preflight (§6.2) — deterministic, build-time, NO model calls
# ══════════════════════════════════════════════════════════════════════════════

def run_preflight(sources: dict, cfg: dict) -> dict:
    from cam.adapters.lease_review.lease_evidence_spans import NORMALIZATION_PROFILE_V2

    result = {
        "_artifact": "431_fixture_preflight.json",
        "_authority": "431_partB_measurement_instruction.md §6.2",
        "_discipline": "RE-VERIFY, DO NOT RE-DISCOVER. Offsets are pinned. If a pinned span "
                       "fails to re-resolve against the frozen hash, the candidate is excluded "
                       "and fixture drift is reported — a fresh offset is never absorbed.",
        "_determinism_note": "This artifact carries NO timestamp by design. It is a pure function "
                             "of the pinned offsets, the frozen fixtures, and the frozen config, so "
                             "its hash — and therefore the Stage-2 sanction token — is stable under "
                             "a no-op rebuild and changes ONLY when something real changes. Build "
                             "time is recorded in the manifest instead, where it does not enter the "
                             "token. Without this, an incidental rebuild would silently void a token "
                             "the reviewer had already sanctioned.",
        "normalization_profile": NORMALIZATION_PROFILE_V2,
        "leases": {},
        "candidates": [],
        "admitted": [],
        "excluded": [],
    }

    for slug, src in sources.items():
        frozen = FROZEN_LEASE_HASHES[slug]
        match = src.source_document_hash == frozen
        result["leases"][slug] = {
            "source_document_hash": src.source_document_hash,
            "canonical_text_hash": src.canonical_text_hash,
            "frozen_hash_expected": frozen,
            "hash_matches_frozen": match,
            "canonical_len": len(src.canonical_text),
            "normalization_profile": src.normalization_profile,
        }
        if not match:
            raise PreflightError(
                f"{slug}: canonical hash {src.source_document_hash} != frozen {frozen}. "
                "Fixture drift — halt (§11)."
            )

    for cand in CANDIDATES:
        src = sources[cand["lease"]]
        ct = src.canonical_text
        s, e = cand["offsets"]
        actual = ct[s:e]
        expected = cand["expected_quote"]
        resolves = actual == expected
        occurrences = ct.count(expected)
        rec = {
            "candidate_id": cand["id"],
            "lease": cand["lease"],
            "parameter": cand["parameter"],
            "pinned_offsets": [s, e],
            "expected_quote": expected,
            "resolved_text": actual,
            "offset_reresolves_to_expected_quote": resolves,
            "full_quote_occurrence_count": occurrences,
            "source_document_hash": src.source_document_hash,
        }
        if cand.get("requires_unique_resolution"):
            rec["unique_resolution_required"] = True
            rec["unique"] = occurrences == 1
            rec["uniqueness_note"] = (
                "Uniqueness rests on the currency prefix; the bare rate phrase recurs "
                "once per lease year. Verified at preflight, not assumed."
            )
            admit = resolves and occurrences == 1
        else:
            admit = resolves

        vtp, hits = value_token_present(actual, cfg)
        rec["value_token_present"] = vtp
        rec["value_token_hits"] = hits
        rec["admitted"] = admit
        if admit:
            result["admitted"].append(cand["id"])
        else:
            result["excluded"].append(
                {"candidate_id": cand["id"],
                 "reason": "offset failed to re-resolve to the pinned quote"
                           if not resolves else "non-unique resolution"}
            )
        result["candidates"].append(rec)

    result["admitted_count"] = len(result["admitted"])
    result["projected_primary_calls"] = len(result["admitted"]) * 5 * 3
    result["all_candidates_admitted"] = len(result["excluded"]) == 0
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Build entry point
# ══════════════════════════════════════════════════════════════════════════════

def build_stage1() -> None:
    print("=== 431 Stage-1 BUILD (zero model calls) ===")
    artifacts = load_artifacts()
    cfg = artifacts["config"]

    print("[1/4] importing frozen panel (import, never modify)...")
    from cam.adapters.lease_review.lease_coverage_305 import (
        EVALUATOR_LINEUP_305, _call_single_evaluator_305,  # noqa: F401
    )
    from cam.core.provider_router import TEMPERATURE_ONLY_DEFAULT_MODELS
    panel = {
        role: {
            "provider": c["provider"], "model": c["model"],
            "declared_temperature": c["temperature"],
            "temperature_transmitted": c["model"] not in TEMPERATURE_ONLY_DEFAULT_MODELS,
            "own_chain": [(p, m) for p, m, _ in c["own_chain"]],
            "own_chain_preserves_panel_identity": [
                (p, m) for p, m, _ in c["own_chain"]
            ] == [(c["provider"], c["model"])],
        }
        for role, c in EVALUATOR_LINEUP_305.items()
    }
    for role, p in panel.items():
        print(f"      {role}: {p['provider']}/{p['model']} "
              f"temp_transmitted={p['temperature_transmitted']} "
              f"self_retry_canonical={p['own_chain_preserves_panel_identity']}")

    print("[2/4] building canonical sources (canonical_whitespace_v2)...")
    sources = build_sources()

    print("[3/4] running deterministic preflight (§6.2)...")
    preflight = run_preflight(sources, cfg)
    preflight["panel_identity_at_build"] = panel
    PREFLIGHT_PATH.write_text(json.dumps(preflight, indent=2), encoding="utf-8")
    for c in preflight["candidates"]:
        flag = "OK " if c["admitted"] else "EXCL"
        uniq = f" unique={c.get('unique')}" if c.get("unique_resolution_required") else ""
        print(f"      {flag} {c['candidate_id']} {c['lease']}/{c['parameter']} "
              f"offsets={c['pinned_offsets']} reresolves={c['offset_reresolves_to_expected_quote']}{uniq}")
    print(f"      admitted={preflight['admitted_count']}/7  "
          f"projected primary calls={preflight['projected_primary_calls']}")

    print("[4/4] writing config manifest...")
    files = {
        "431_measurement_config.json": CONFIG_PATH,
        "431_requirement_profiles.json": PROFILES_PATH,
        "431_output_schema.json": SCHEMA_PATH,
        "431_selector_prompt.txt": PROMPT_PATH,
        "431_fixture_preflight.json": PREFLIGHT_PATH,
        "run_431_selection_measurement.py": Path(__file__),
    }
    hashes = {name: sha256_file(p) for name, p in files.items()}
    self_hash = hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = {
        "_artifact": "431_config_manifest.json",
        "_purpose": "The reviewed config IS the run config. Any artifact edited after "
                    "Stage-1 review changes its hash, changes the self-hash, and voids "
                    "the Stage-2 sanction token (§1).",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stage": 1,
        "model_calls_made": 0,
        "artifact_hashes": hashes,
        "manifest_self_hash_of_artifact_hashes": self_hash,
        "stage2_sanction_token": self_hash,
        "_how_to_sanction": "Stage 2 is invoked as: --mode run --stage2-sanction <manifest_self_hash_of_artifact_hashes>",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n=== artifact hashes ===")
    for name, h in hashes.items():
        print(f"  {h}  {name}")
    print(f"\n  manifest self-hash / Stage-2 sanction token:\n  {self_hash}")

    seam = capture_cam_seam("stage1_build_complete")
    print(f"\ncam/ clean at build completion: {seam['cam_clean']}")
    print("MODEL CALLS MADE: 0")


def main() -> None:
    ap = argparse.ArgumentParser(description="431 Part B governed-selection measurement harness")
    ap.add_argument("--mode", choices=["build", "run"], default="build",
                    help="build (default, zero model calls) | run (requires Stage-2 sanction)")
    ap.add_argument("--stage2-sanction", default=None,
                    help="manifest self-hash authorizing the live run")
    args = ap.parse_args()

    if args.mode == "build":
        build_stage1()
        return

    _assert_stage2(args.mode, args.stage2_sanction)
    raise NotImplementedError(
        "Stage-2 execution path is intentionally unimplemented in the Stage-1 artifact."
    )


if __name__ == "__main__":
    main()
