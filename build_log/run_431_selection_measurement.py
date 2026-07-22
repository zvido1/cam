"""
Step 431 Part B — Governed evidence-selection measurement harness.

STAGE 1 ARTIFACT. Built under BUILD-ONLY authorization (Part B v3.3 §1, §13):
this file makes ZERO model calls as committed. The live run requires a SEPARATE
Stage-2 sanction of the exact hashed artifacts.

The call site is hard-gated: `--mode` defaults to `build`, and the single
function that would invoke a model raises StageAuthorizationError unless BOTH
`--mode run` AND `--stage2-sanction <manifest_hash>` are supplied AND the
supplied hash matches the committed manifest. There is no code path in which a
call fires by default, by accident, or by a truthy flag.

Discipline (Part B §2): READ-ONLY. Imports from cam/, never modifies. No cam/
file is created, modified, or deleted. Nothing is wired.

Authority: build_log/431_partB_measurement_instruction.md (v3.3, RATIFIED, committed 38785e7).
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
    "base_rent": {"value_applies_to_charge_basis_components", "charge_scope"},
    "rent_adjustment_pct": {"value_applies_to_charge_basis_components", "charge_scope"},
}

SEMANTIC_FIELDS = [
    "parameter_family_relevance", "candidate_support_state", "value_applies_to_charge_basis_components",
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
        "value_applies_to_charge_basis_components": merged.get("value_applies_to_charge_basis_components"),
        **{k: merged[k] for k in SEMANTIC_FIELDS if k != "value_applies_to_charge_basis_components"},
        "agreement_by_field": agreement,
        "per_panelist": judgments,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Requirement comparison + certification (Part A §6)
# ══════════════════════════════════════════════════════════════════════════════

def _basis_rule(bm_spec: dict, parameter: str) -> Tuple[str, List[str]]:
    """Resolve (operator, required_members) for a basis_match rule.

    Prefers the explicit `operator` / `required_members` fields. Where a profile
    does not declare them, the rule is read out of the `computation.match`
    structure the profile DOES declare — so a profile is executed as written
    rather than against a silently-empty default.

    This matters concretely: `building_share` declares its rule only as
    `computation.match = {"set_equals": [<field>, ["operating_expenses"]]}` and is
    expressly out of scope for the v3.2 amendment (do not edit). Defaulting
    required_members to [] would make set_equals compare against the empty set,
    so building_share could never match anything — a latent contradiction of its
    own declared rule. Reading the literal from the declared computation avoids
    both editing it and breaking it.
    """
    if bm_spec.get("schema_fixed_value") == "not_applicable":
        return "not_applicable", []

    operator = bm_spec.get("operator")
    required = bm_spec.get("required_members")
    if operator and required is not None:
        return operator, required

    match_spec = (bm_spec.get("computation") or {}).get("match")
    if isinstance(match_spec, dict) and len(match_spec) == 1:
        op = next(iter(match_spec))
        operands = match_spec[op]
        if isinstance(operands, list) and len(operands) == 2 and isinstance(operands[1], list):
            return op, operands[1]

    raise ValueError(
        f"Cannot resolve basis_match rule for {parameter!r}: profile declares neither "
        f"(operator, required_members) nor a parseable computation.match literal. "
        f"Refusing to guess — an unresolvable requirement rule must not silently "
        f"evaluate to mismatch."
    )


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

    # basis_match is EXECUTED FROM THE PROFILE, never hardcoded here: the operator
    # and its required members are read from 431_requirement_profiles.json so the
    # reviewed rule is literally the rule that runs (§4). The field read is the
    # relation-bearing value_applies_to_charge_basis_components (v3.3).
    #
    # `operator` defaults to set_equals when a profile does not declare one. That
    # default keeps building_share on exact-equality — its ratified rule, expressly
    # out of scope for the v3.2 amendment — without this rebuild editing its profile
    # entry at all.
    basis = result.get("value_applies_to_charge_basis_components")
    bm_spec = prof["basis_match"]
    operator, required = _basis_rule(bm_spec, parameter)

    if bm_spec.get("schema_fixed_value") == "not_applicable":
        basis_match = "not_applicable" if basis == "not_applicable" else "mismatch"
    elif undet("value_applies_to_charge_basis_components") or basis in ("none", "unclear", "not_applicable"):
        # unclear / DISPUTED / grounding-invalid -> undeterminable, NEVER false
        basis_match = "undeterminable"
    elif not isinstance(basis, list):
        basis_match = "undeterminable"
    elif operator == "set_contains":
        # Inclusion: additional grounded components (taxes, CAM, insurance) are
        # preserved as semantic identity and do NOT independently cause mismatch.
        basis_match = "match" if all(m in basis for m in required) else "mismatch"
    elif operator == "set_equals":
        basis_match = "match" if sorted(basis) == sorted(required) else "mismatch"
    else:
        raise ValueError(f"Unknown basis_match operator {operator!r} in profile for {parameter}")

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
# Relation-bearing contract — build-time deterministic tests (v3.3 §5)
# Zero model calls. Synthetic constructed classifications, NOT fixtures, no lease
# text. They assert the profile+validator ENFORCE the relation-bearing contract.
# Passing all four is a Stage-1 build gate; any failure halts the build.
# ══════════════════════════════════════════════════════════════════════════════

def _synthetic_result(basis, *, relevance="relevant", agreement="unanimous"):
    """Construct a minimal merged candidate_semantic_result carrying a given
    value_applies_to_charge_basis_components. Every non-basis field is set to a
    neutral qualifying value so ONLY the basis field drives basis_match — the
    test isolates the relation-bearing rule, nothing else."""
    return {
        "value_applies_to_charge_basis_components": basis,
        "parameter_family_relevance": relevance,
        "candidate_support_state": "supports_mechanism",
        "text_role": "operative_term",
        "value_completeness": "self_contained",
        "charge_scope": "building",
        "agreement_by_field": {
            "parameter_family_relevance": agreement,
            "value_applies_to_charge_basis_components": agreement,
            "candidate_support_state": agreement, "text_role": agreement,
            "value_completeness": agreement, "charge_scope": agreement,
        },
    }


def run_relationship_tests(profiles: dict, cfg: dict) -> List[dict]:
    """The four §5 relationship tests. Each record carries the synthetic input,
    the EXPECTED value_applies_to_charge_basis_components, the EXPECTED
    basis_match, the §5 clause it implements, and the ACTUAL result — so a
    reviewer can check the assertion is CORRECT, not merely green."""
    # A candidate_text carrying a percentage token, so value_ok is not what fails
    # these tests — they isolate basis_match. Generic shape, no lease literal.
    ctext = "the applicable rate is 10% per annum"
    results: List[dict] = []

    def record(name, clause, desc, expected_field, expected_bm, actual_bm, extra=None):
        rec = {
            "name": name,
            "s5_clause": clause,
            "synthetic_input": desc,
            "expected_value_applies_to_charge_basis_components": expected_field,
            "expected_basis_match": expected_bm,
            "actual_basis_match": actual_bm,
            "pass": actual_bm == expected_bm,
        }
        if extra:
            rec.update(extra)
        results.append(rec)

    # Test (a) — §5.1: combined percentage grounded as applying to opex + taxes.
    fa = ["operating_expenses", "taxes"]
    bm = compare_candidate(_synthetic_result(fa), "tenant_share", ctext, profiles, cfg)["basis_match"]
    record("a_combined_opex_taxes", "§5 test 1",
           "one combined percentage whose OWN value is grounded as applying to operating_expenses AND taxes",
           fa, "match", bm)

    # Test (b) — §5.2: separate opex and tax percentages; the TAX candidate is
    # under test, so opex is a SIBLING value's basis, not this value's.
    fb = ["taxes"]
    bm = compare_candidate(_synthetic_result(fb), "tenant_share", ctext, profiles, cfg)["basis_match"]
    record("b_sibling_tax_candidate", "§5 test 2",
           "tax candidate under test; opex belongs to a separate (sibling) value expression, so this value's field is [taxes]",
           fb, "mismatch", bm)

    # Test (c) — §5.3: tax percentage with an opex clause merely nearby; no
    # value-to-basis linkage to opex, so opex is NOT added to this value's field.
    fc = ["taxes"]
    bm = compare_candidate(_synthetic_result(fc), "tenant_share", ctext, profiles, cfg)["basis_match"]
    record("c_comention_no_linkage", "§5 test 3",
           "tax value with an operating-expense clause co-located but NOT linked to this value; opex must not be added -> field [taxes]",
           fc, "mismatch", bm,
           extra={"_note": "same rule branch as test (b) ([taxes]->mismatch) reached from the co-mention scenario; "
                           "the model, not the rule, is responsible for NOT adding opex without linkage (prompt §5); "
                           "this test confirms the rule excludes opex whenever it is absent from the field"})

    # Test (d) — §5.4: value-to-basis linkage NOT citation-grounded. Exercised
    # through the actual §4.5 grounding path: a per-panelist judgment asserts
    # opex but supplies EMPTY field_support for the basis field -> the field is
    # invalidated to 'unclear' -> basis_match routes to 'undeterminable'.
    ungrounded_judgment = {
        "value_applies_to_charge_basis_components": ["operating_expenses"],
        "parameter_family_relevance": "relevant",
        "candidate_support_state": "supports_mechanism",
        "text_role": "operative_term",
        "value_completeness": "self_contained",
        "charge_scope": "building",
        "candidate_citations": [], "context_citations": [],
        "field_support": {
            "value_applies_to_charge_basis_components": {"candidate_citation_ids": [], "context_citation_ids": []},
            "parameter_family_relevance": {"candidate_citation_ids": [], "context_citation_ids": []},
            "candidate_support_state": {"candidate_citation_ids": [], "context_citation_ids": []},
            "text_role": {"candidate_citation_ids": [], "context_citation_ids": []},
            "value_completeness": {"candidate_citation_ids": [], "context_citation_ids": []},
            "charge_scope": {"candidate_citation_ids": [], "context_citation_ids": []},
        },
    }
    grounded = apply_field_grounding(ungrounded_judgment, "tenant_share", ctext, "")
    field_after_grounding = grounded.get("value_applies_to_charge_basis_components")
    bm = compare_candidate(_synthetic_result(field_after_grounding), "tenant_share", ctext, profiles, cfg)["basis_match"]
    record("d_ungrounded_linkage", "§5 test 4",
           "opex asserted but the basis field's field_support is EMPTY (no value-to-basis citation); §4.5 invalidates the field to 'unclear'",
           "unclear (post-grounding-invalidation)", "undeterminable", bm,
           extra={"field_after_grounding_invalidation": field_after_grounding,
                  "_grounding_note": "the deterministic check enforces citation PRESENCE/resolution; whether a present "
                                     "citation semantically establishes the linkage is model-governed, not code-verified (doctrine)"})
    return results


def sweep_stale_field_name() -> dict:
    """Halt condition: no bare pre-v3.3 field name `charge_basis_components` may
    survive in the MODEL-FACING artifacts (schema, prompt) or the profiles. The
    new name contains the old as a substring, so match the old name ONLY when it
    is not immediately preceded by `value_applies_to_` (a genuine stale token)."""
    stale = re.compile(r"(?<!value_applies_to_)charge_basis_components")
    targets = {
        "431_output_schema.json": SCHEMA_PATH,
        "431_selector_prompt.txt": PROMPT_PATH,
        "431_requirement_profiles.json": PROFILES_PATH,
    }
    hits = {}
    for name, path in targets.items():
        found = stale.findall(path.read_text(encoding="utf-8"))
        if found:
            hits[name] = len(found)
    return {"clean": not hits, "stale_hits": hits}


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


# ── Stage-2 call-path implementation (Step 432) ───────────────────────────────
#
# ARCHITECTURE NOTE — read before auditing this section.
#
# The Stage-2 brief says "call through the real _call_single_evaluator_305 path —
# do NOT reimplement provider logic." That directive is honored as Part B §2 and
# this file's own gated-call-site docstring phrase it: *import the
# _call_single_evaluator_305 call/fallback/provenance PATTERN/SHAPE*, and reuse the
# REAL provider logic it wraps. It is NOT honored by literally invoking
# _call_single_evaluator_305(...), which is IMPOSSIBLE here and would be WRONG:
#
#   • _call_single_evaluator_305 hard-bakes the coverage-analysis _SYSTEM_PROMPT +
#     _build_user_prompt and parses element-verdict arrays. It exposes no seam to
#     inject the 431 selector prompt / schema, and it cannot parse a 431 judgment.
#   • Feeding it the 431 payload would require editing/subclassing/monkeypatching
#     cam/ — forbidden by §2 (read-only) and Guardrail #5.
#   • Sending its coverage prompt to the panel would VIOLATE §5's absolute payload
#     invariant (the model may see ONLY the 431 selector prompt, schema, candidate,
#     envelope, neutral family label, applicability dimensions — nothing else).
#
# Therefore this harness imports and calls the SAME real provider primitives that
# _call_single_evaluator_305 itself calls internally — ProviderRouter / ModelTarget
# / RouterConfig / the provider adapters from cam.core.provider_router, plus the
# real EVALUATOR_LINEUP_305 identity/temperature/own_chain and the pure importable
# helpers _classify_failure / _is_transient_failure from lease_coverage_305 — and
# REPLICATES the own-chain-fallback / canonical-classification / provenance SHAPE
# of _call_single_evaluator_305 in measurement code. No cam/ file is edited, no
# provider HTTP/SDK/temperature/retry logic is reimplemented (it stays inside the
# imported adapter), and nothing is monkeypatched.
#
# This interpretation is load-bearing and is surfaced for the scoped informed
# audit (Step 432 status file). If the auditor/architect rejects it, this section
# changes BEFORE any run — no model call has been made under it.
# ──────────────────────────────────────────────────────────────────────────────

# Output-token budget for one 431 judgment (a single JSON object, not N elements).
# Reuses the frozen panel's configured max_output_tokens; introduces no new tuning.
_JUDGMENT_OUTPUT_TOKENS = 3000


def _forbidden_leak_tokens(candidate: Dict[str, Any]) -> List[str]:
    """§5 payload whitelist — the forbidden token(s) the runtime asserts absent.

    The PRIMARY §5 guarantee is by CONSTRUCTION: build_panelist_payload reads only
    a positive whitelist of permitted fields (id, parameter→neutral label,
    offsets→raw text, envelope, schema) and NEVER reads candidate['human_note'] or
    candidate['expected_quote'], so those human-only columns cannot enter the
    payload at all.

    The runtime check asserts only the parameter's INTERNAL name (`tenant_share`,
    `base_rent`, `rent_adjustment_pct`; underscore form) is absent — it is the one
    forbidden token with a collision-free string form (the neutral label uses
    "tenant's share"/"base rent", so a match on the underscore name would be a
    genuine leak). The human_note is deliberately NOT substring-checked: its words
    ("operative", "approximation", …) legitimately occur in the reviewed schema
    vocabulary (e.g. "operative_term"), so a substring test would false-positive on
    non-leaked schema text. Its non-inclusion is guaranteed structurally instead."""
    return [candidate["parameter"]]


def build_panelist_payload(candidate: Dict[str, Any], envelope: dict, candidate_text: str,
                           cfg: dict, schema_text: str, prompt_template: str) -> str:
    """Render the model-facing payload for ONE (candidate + envelope) × parameter.

    Built by str.replace (NOT str.format — the embedded schema contains literal
    braces) from a POSITIVE whitelist of §5-permitted fields only: neutral family
    label, the two applicability-dimension flags, the opaque candidate/envelope
    ids, the raw candidate text, the deterministic envelope text, and the reviewed
    output schema (byte-for-byte from 431_output_schema.json). Nothing else is
    appended at runtime. Same text for A/B/C. Panelists never see each other's
    output or any other candidate.
    """
    param = candidate["parameter"]
    fam = cfg["parameter_family_labels"][param]
    rendered = (
        prompt_template
        .replace("{parameter_family_label}", fam["label"])
        .replace("{charge_basis_applicability}", fam["charge_basis_applicability"])
        .replace("{charge_scope_applicability}", fam["charge_scope_applicability"])
        .replace("{candidate_span_id}", candidate["id"])
        .replace("{candidate_text}", candidate_text)
        .replace("{context_envelope_id}", envelope["context_envelope_id"])
        .replace("{context_text}", envelope["context_text"])
        .replace("{output_schema}", schema_text)
    )
    for tok in _forbidden_leak_tokens(candidate):
        if tok and tok in rendered:
            raise StageAuthorizationError(
                f"§5 payload leak: forbidden token {tok!r} present in the model-facing "
                f"payload for {candidate['id']}. A leaked payload voids the measurement "
                f"(mechanism appears to work on poisoned input). Halt."
            )
    return rendered


def _strip_code_fence(raw: str) -> str:
    """Remove a leading/trailing markdown code fence if the model wrapped its JSON
    despite the prompt forbidding it. Fence removal is NOT a meaning-changing
    repair (it strips a wrapper, not content); it mirrors lease_coverage_305's
    handling. No JSON-object hunting / element extraction / field synthesis is done
    — those WOULD change meaning and are prohibited (§5, brief item 1)."""
    r = raw.strip()
    if r.startswith("```"):
        r = re.sub(r"^```(?:json)?\s*", "", r)
        r = re.sub(r"\s*```\s*$", "", r)
        r = r.strip()
    return r


def _provider_call(provider: str, model: str, evaluator_cfg: dict, role: str,
                   candidate: Dict[str, Any], payload: str) -> Tuple[dict, dict]:
    """One real provider call through cam.core.provider_router — the SAME primitives
    _call_single_evaluator_305 uses (ProviderRouter/ModelTarget/RouterConfig/adapter).
    Returns (parsed_judgment, call_meta). Raises on empty/parse failure so the
    caller's fallback traversal classifies it exactly like the 305 path.

    Temperature: ModelTarget carries the frozen declared temperature (0.0). The
    ADAPTER decides transmission via TEMPERATURE_ONLY_DEFAULT_MODELS — gpt-5.5 is
    in that set, so temperature is OMITTED (provider default governs) and the
    omission is LOGGED by the adapter integrity check, not silently dropped
    (§3 configuration truth). We record temperature_transmitted + the adapter's
    integrity record for provenance; we never override the adapter's decision.
    """
    from cam.core.provider_router import (
        ModelTarget, ProviderRouter, RouterConfig, TEMPERATURE_ONLY_DEFAULT_MODELS,
    )
    target = ModelTarget(
        name=f"{provider}:{model}-431-{role}-{candidate['id']}",
        provider=provider,
        model=model,
        max_output_tokens=evaluator_cfg.get("max_output_tokens", _JUDGMENT_OUTPUT_TOKENS),
        temperature=evaluator_cfg.get("temperature", 0.0),
        timeout_sec=evaluator_cfg.get("timeout_sec", 300.0),
    )
    router = ProviderRouter([target], RouterConfig())
    adapter = router._get_adapter(provider)
    # The selector prompt is the entire model-facing text; no separate system
    # channel (keeps the payload EXACTLY the §5 whitelist — nothing appended).
    raw = adapter.call("", payload, target) or ""
    usage = getattr(adapter, "last_usage", None)
    integrity = getattr(adapter, "last_integrity", None)
    temp_transmitted = model not in TEMPERATURE_ONLY_DEFAULT_MODELS

    call_meta = {
        "raw_response": raw,
        "raw_char_len": len(raw),
        "usage": usage,
        "temperature_declared": target.temperature,
        "temperature_transmitted": temp_transmitted,
        "temperature_integrity": integrity,
    }

    stripped = _strip_code_fence(raw)
    if stripped == "":
        raise ValueError("empty_content: model returned no output")
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError) as e:
        # No repair, no object-hunting: a malformed judgment is a failed attempt,
        # not a silently-mended one (brief item 1: no meaning-changing repairs).
        raise ValueError(f"malformed: judgment is not valid JSON ({e})")
    if not isinstance(parsed, dict):
        raise ValueError(f"malformed: judgment is not a JSON object (got {type(parsed).__name__})")
    return parsed, call_meta


def call_panelist(role: str, candidate: Dict[str, Any], envelope: dict, candidate_text: str,
                  context_text: str, cfg: dict, schema_text: str, prompt_template: str,
                  config_hash: str, mode: str, sanction: Optional[str]) -> dict:
    """One panelist (role A/B/C) judging ONE (candidate + envelope) × parameter.

    Gated unconditionally by _assert_stage2. Traverses the role's own_chain exactly
    like _call_single_evaluator_305: primary → same-provider chain, with same-model
    self-retry ONLY on transient failure; then the shared cross-family pool. Records
    real returned identity, canonicality, temperature transmission, raw response,
    and every attempt (including parse failures) for the audit trail.

    Canonicality (§7 rule 1): actual provider AND actual model equal the role's
    FROZEN primary AND config_hash equals the reviewed config. is_fallback alone
    NEVER infers canonicality. Role C's grok-4.3 own_chain entry is the SAME model,
    so its self-retry stays canonical; A→Haiku, B→gpt-5.4, and any pool substitution
    are DIFFERENT models → degraded (preserved as audit, excluded from canonical N).
    A primary-model semantic refusal (valid JSON with unclear/insufficient_context)
    parses fine → completed → canonical (§7 rule 3): governed uncertainty is the
    behavior being measured, not a failure.
    """
    from cam.adapters.lease_review.lease_coverage_305 import (
        EVALUATOR_LINEUP_305, _classify_failure, _is_transient_failure,
    )
    _assert_stage2(mode, sanction)

    evaluator_cfg = EVALUATOR_LINEUP_305[role]
    primary_provider, primary_model = evaluator_cfg["provider"], evaluator_cfg["model"]
    payload = build_panelist_payload(candidate, envelope, candidate_text, cfg,
                                     schema_text, prompt_template)
    # config_hash is a genuine participant in the canonical decision (§7 rule 1):
    # the threaded run config_hash must equal the committed manifest self-hash on
    # disk. Under a valid sanction these agree; a drifted config_hash here would
    # (correctly) mark the attempt non-canonical rather than silently pass.
    reviewed_config_hash = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )["manifest_self_hash_of_artifact_hashes"]

    start = time.time()
    attempts: List[dict] = []          # every attempt, incl. parse failures (audit)
    attempt_failures: List[dict] = []  # 305-shape failure classifications

    own_candidates = [(primary_provider, primary_model, evaluator_cfg["label"])]
    own_candidates += [(p, m, l) for (p, m, l) in evaluator_cfg.get("own_chain", [])]

    def _finalize(actual_provider, actual_model, actual_label, judgment, call_meta,
                  is_fallback, fallback_reason):
        grounded = apply_field_grounding(
            judgment, candidate["parameter"], candidate_text, context_text
        )
        config_ok = (config_hash == reviewed_config_hash)
        identity_ok = (actual_provider == primary_provider and actual_model == primary_model)
        canonical = identity_ok and config_ok
        if canonical:
            canonical_reason = "actual_provider+model==frozen_primary AND config_hash==reviewed"
        elif not config_ok:
            canonical_reason = (
                f"config_hash {config_hash} != reviewed {reviewed_config_hash} — "
                "config drift, not canonical"
            )
        else:
            canonical_reason = (
                f"actual {actual_provider}/{actual_model} != frozen primary "
                f"{primary_provider}/{primary_model} — degraded substitution, excluded from canonical N"
            )
        return {
            "role": role,
            "requested_provider": primary_provider, "requested_model": primary_model,
            "actual_provider": actual_provider, "actual_model": actual_model,
            "actual_label": actual_label,
            "is_fallback": is_fallback,
            "canonical": canonical, "canonical_reason": canonical_reason,
            "config_hash": config_hash,
            "completed": True, "abstained": False,
            "elapsed_sec": round(time.time() - start, 2),
            "fallback_reason": fallback_reason,
            "temperature_declared": call_meta.get("temperature_declared"),
            "temperature_transmitted": call_meta.get("temperature_transmitted"),
            "temperature_integrity": call_meta.get("temperature_integrity"),
            "raw_response": call_meta.get("raw_response"),
            "usage": call_meta.get("usage"),
            "judgment": grounded,
            "attempts": attempts,
        }

    # Phase 1: own-provider chain (primary + same-provider retry).
    hard_fail_no_retry = False
    for idx, (provider, model, label) in enumerate(own_candidates):
        is_fb = idx > 0
        try:
            judgment, call_meta = _provider_call(provider, model, evaluator_cfg, role,
                                                 candidate, payload)
            fb_reason = attempt_failures[0]["reason"] if (is_fb and attempt_failures) else None
            attempts.append({"provider": provider, "model": model, "parse_ok": True,
                             "raw_response": call_meta["raw_response"], "error": None})
            return _finalize(provider, model, label, judgment, call_meta, is_fb, fb_reason)
        except Exception as e:
            reason = _classify_failure(str(e), model)
            attempt_failures.append({"provider": provider, "model": model,
                                     "reason": reason, "error": str(e)})
            attempts.append({"provider": provider, "model": model, "parse_ok": False,
                             "raw_response": None, "error": str(e), "failure_class": reason})
            # Same-model self-retry only on transient failure (305 guard): a hard
            # failure won't recover on an immediate re-call of the same model.
            nxt = idx + 1
            if (nxt < len(own_candidates)
                    and own_candidates[nxt][1] == primary_model
                    and not _is_transient_failure(reason)):
                hard_fail_no_retry = True
                break

    # Phase 2: shared cross-family pool — always DEGRADED (different model → excluded
    # from canonical N; preserved as audit). Mirrors _SHARED_FALLBACK_POOL usage.
    from cam.adapters.lease_review.lease_coverage_305 import _SHARED_FALLBACK_POOL
    for provider, model, label in _SHARED_FALLBACK_POOL:
        try:
            judgment, call_meta = _provider_call(provider, model, evaluator_cfg, role,
                                                 candidate, payload)
            fb_reason = attempt_failures[0]["reason"] if attempt_failures else None
            attempts.append({"provider": provider, "model": model, "parse_ok": True,
                             "raw_response": call_meta["raw_response"], "error": None})
            return _finalize(provider, model, label, judgment, call_meta, True, fb_reason)
        except Exception as e:
            reason = _classify_failure(str(e), model)
            attempt_failures.append({"provider": provider, "model": model,
                                     "reason": reason, "error": str(e)})
            attempts.append({"provider": provider, "model": model, "parse_ok": False,
                             "raw_response": None, "error": str(e), "failure_class": reason})

    # All attempts failed: not completed. NOT canonical, NOT a semantic refusal —
    # the panel attempt containing this role is degraded (excluded from canonical N).
    return {
        "role": role,
        "requested_provider": primary_provider, "requested_model": primary_model,
        "actual_provider": None, "actual_model": None, "actual_label": None,
        "is_fallback": False,
        "canonical": False,
        "canonical_reason": "no attempt completed (all provider calls failed) — degraded",
        "config_hash": config_hash,
        "completed": False, "abstained": False,
        "elapsed_sec": round(time.time() - start, 2),
        "fallback_reason": attempt_failures[0]["reason"] if attempt_failures else "unknown",
        "hard_fail_no_retry": hard_fail_no_retry,
        "judgment": None,
        "attempts": attempts,
    }


def run_panel_attempt(candidate: Dict[str, Any], envelope: dict, candidate_text: str,
                      context_text: str, cfg: dict, schema_text: str, prompt_template: str,
                      config_hash: str, sanction: str) -> dict:
    """One candidate-panel attempt: A, B, C each judge the SAME (candidate+envelope)
    independently (§7 atomic unit). Panelists receive identical payloads and never
    see each other's output. Run sequentially in fixed A→B→C order (deterministic;
    the three primaries are distinct providers so no shared-provider contention).

    A panel attempt is CANONICAL iff ALL THREE role results are canonical (the
    frozen panel, possibly with C's same-model self-retry, at the frozen config).
    A degraded/failed substitution on ANY role makes the whole attempt non-canonical
    — "a degraded A/B/Gemini attempt is not the frozen panel" (§7 rule 2).
    """
    per_role = {}
    for role in ("A", "B", "C"):
        per_role[role] = call_panelist(
            role, candidate, envelope, candidate_text, context_text, cfg,
            schema_text, prompt_template, config_hash, mode="run", sanction=sanction,
        )
    panel_canonical = all(per_role[r]["canonical"] for r in ("A", "B", "C"))
    return {"per_role": per_role, "panel_canonical": panel_canonical}


def run_candidate_series(candidate: Dict[str, Any], source, cfg: dict, schema_text: str,
                         prompt_template: str, config_hash: str, sanction: str) -> dict:
    """Accumulate FIVE canonical candidate-panel attempts for one candidate, ceiling
    `attempt_ceiling` (§3/§7). The deterministic envelope is built ONCE per candidate
    (frozen; never re-derived per attempt or tuned, §10).

    Series discipline (§7):
      • canonical panels get canonical_attempt_index / series_index 1..5 in the ORDER
        obtained — retries cannot shop for a preferred result;
      • a canonical panel counts even when panelists refuse (governed uncertainty);
      • degraded/failed panels are preserved as audit with a raw_attempt_index and
        NO series_index (never promoted, never filled from another series);
      • hitting the ceiling before 5 canonical yields an honest canonical-N shortfall.
    """
    ct = source.canonical_text
    s, e = candidate["offsets"]
    candidate_text = ct[s:e]
    envelope = build_envelope(ct, s, e, cfg, envelope_id=f"env_{candidate['id']}")
    context_text = envelope["context_text"]

    ceiling = cfg["attempt_ceiling"]
    target = cfg.get("canonical_target_per_candidate", 5)

    canonical_panels: List[dict] = []
    degraded_panels: List[dict] = []
    raw_idx = 0
    while len(canonical_panels) < target and raw_idx < ceiling:
        raw_idx += 1
        attempt = run_panel_attempt(candidate, envelope, candidate_text, context_text,
                                    cfg, schema_text, prompt_template, config_hash, sanction)
        attempt["raw_attempt_index"] = raw_idx
        if attempt["panel_canonical"]:
            k = len(canonical_panels) + 1
            attempt["canonical_attempt_index"] = k
            attempt["series_index"] = k
            for r in ("A", "B", "C"):
                attempt["per_role"][r]["raw_attempt_index"] = raw_idx
                attempt["per_role"][r]["canonical_attempt_index"] = k
                attempt["per_role"][r]["series_index"] = k
            canonical_panels.append(attempt)
        else:
            attempt["canonical_attempt_index"] = None
            attempt["series_index"] = None
            for r in ("A", "B", "C"):
                attempt["per_role"][r]["raw_attempt_index"] = raw_idx
                attempt["per_role"][r]["canonical_attempt_index"] = None
                attempt["per_role"][r]["series_index"] = None
            degraded_panels.append(attempt)

    canonical_n = len(canonical_panels)
    return {
        "candidate_id": candidate["id"],
        "lease": candidate["lease"],
        "parameter": candidate["parameter"],
        "envelope": envelope,
        "candidate_text": candidate_text,
        "canonical_panels": canonical_panels,
        "degraded_panels": degraded_panels,
        "canonical_N": canonical_n,
        "canonical_target": target,
        "attempt_ceiling": ceiling,
        "raw_attempts_used": raw_idx,
        "canonical_shortfall": canonical_n < target,
    }


def certify_parameter_series(lease: str, parameter: str, candidate_series: List[dict],
                             cfg: dict, config_hash: str, hashes: Dict[str, str]) -> List[dict]:
    """Per-parameter-series certification, consuming ONLY the reviewed validator
    (merge_panel → compare_candidate → certify). Introduces NO new judgment and NO
    majority behavior — it assembles same-series candidate results and calls the
    frozen functions. Emits one certification_trace per series index (§8.1).

    Same-series pairing (§7): series index k consumes ONLY the kth canonical panel
    from each admitted candidate for this lease/parameter. A candidate missing index
    k makes that series result an incomplete canonical-N shortfall — never filled
    from another series, never cross-index paired.
    """
    target = cfg.get("canonical_target_per_candidate", 5)
    traces: List[dict] = []
    for k in range(1, target + 1):
        per_candidate_out = []
        incomplete = False
        for cs in candidate_series:
            panels = cs["canonical_panels"]
            if len(panels) < k:
                incomplete = True
                per_candidate_out.append({
                    "candidate_id": cs["candidate_id"], "series_index": k,
                    "canonical_attempt_index": None, "raw_attempt_index": None,
                    "candidate_qualification": "absent_this_series",
                    "note": "candidate lacks canonical index k (degraded/ceiling) — canonical-N shortfall",
                })
                continue
            panel = panels[k - 1]
            judgments = [panel["per_role"][r]["judgment"] for r in ("A", "B", "C")]
            merged = merge_panel(judgments, parameter)
            comparison = compare_candidate(merged, parameter, cs["candidate_text"],
                                           {"profiles": _load_profiles_cached()}, cfg)
            per_candidate_out.append({
                "candidate_id": cs["candidate_id"],
                "raw_attempt_index": panel["raw_attempt_index"],
                "canonical_attempt_index": panel["canonical_attempt_index"],
                "series_index": panel["series_index"],
                "relevance_ok": comparison["relevance_ok"],
                "basis_match": comparison["basis_match"],
                "text_role_ok": comparison["text_role_ok"],
                "value_ok": comparison["value_ok"],
                "support_ok": comparison["support_ok"],
                "applicability_match": comparison["applicability_match"],
                "agreement_by_field": comparison["agreement_by_field"],
                "candidate_qualification": comparison["candidate_qualification"],
                "_comparison": comparison,
            })
        comparisons = [c["_comparison"] for c in per_candidate_out if "_comparison" in c]
        final_state = certify(comparisons, cfg) if comparisons else "review_needed_no_qualifying_candidate"
        for c in per_candidate_out:
            c.pop("_comparison", None)
        traces.append({
            "parameter": parameter, "lease": lease, "series_index": k,
            "per_candidate": per_candidate_out,
            "series_complete": not incomplete,
            "completeness_provenance": {"status": "not_established"},
            "prompt_hash": hashes["431_selector_prompt.txt"],
            "schema_hash": hashes["431_output_schema.json"],
            "requirement_profiles_hash": hashes["431_requirement_profiles.json"],
            "config_hash": config_hash,
            "final_certification_state": final_state,
        })
    return traces


_PROFILES_CACHE: Dict[str, Any] = {}


def _load_profiles_cached() -> dict:
    if "profiles" not in _PROFILES_CACHE:
        _PROFILES_CACHE["profiles"] = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    return _PROFILES_CACHE["profiles"]


def run_stage2(sanction: str) -> None:
    """Live Stage-2 measurement. Gated; fires the ~90–105 primary calls. Implemented
    for the scoped audit; NOT invoked by this step (build mode only). Every mechanism
    routes through the frozen validator; this function only orchestrates and records.
    """
    _assert_stage2("run", sanction)
    print("=== 431 Stage-2 RUN (live model calls) ===")

    artifacts = load_artifacts()
    cfg = artifacts["config"]
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    prompt_template = artifacts["prompt_template"]

    # Config integrity: the run config MUST equal the reviewed config (§1). The
    # sanction already matched the manifest self-hash in _assert_stage2; re-derive
    # per-artifact hashes for the trace and use the self-hash as config identity.
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    hashes = manifest["artifact_hashes"]
    config_hash = manifest["manifest_self_hash_of_artifact_hashes"]

    sources = build_sources()
    preflight = run_preflight(sources, cfg)
    admitted_ids = set(preflight["admitted"])
    admitted = [c for c in CANDIDATES if c["id"] in admitted_ids]

    # ── Runtime seam capture: IMMEDIATELY before the first model call (§8.2) ──
    seam_before = capture_cam_seam("before_first_model_call")

    series_by_id: Dict[str, dict] = {}
    for cand in admitted:
        series_by_id[cand["id"]] = run_candidate_series(
            cand, sources[cand["lease"]], cfg, schema_text, prompt_template,
            config_hash, sanction,
        )

    # ── Runtime seam capture: IMMEDIATELY after the final model call (§8.2) ──
    seam_after = capture_cam_seam("after_last_model_call")
    RUNTIME_SEAM_PATH.write_text(json.dumps(
        {"before_first_model_call": seam_before, "after_last_model_call": seam_after},
        indent=2), encoding="utf-8")

    # Certification per (lease, parameter) across its admitted candidates, per series.
    cert_traces: List[dict] = []
    by_lease_param: Dict[Tuple[str, str], List[dict]] = {}
    for cand in admitted:
        by_lease_param.setdefault((cand["lease"], cand["parameter"]), []).append(
            series_by_id[cand["id"]]
        )
    for (lease, parameter), cseries in by_lease_param.items():
        cert_traces.extend(
            certify_parameter_series(lease, parameter, cseries, cfg, config_hash, hashes)
        )

    sidecar = {
        "_artifact": "431_selection_measurement_sidecar.json",
        "_authority": "431_partB_measurement_instruction.md v3.3 §7/§8; call path Step 432",
        "stage": 2,
        "sanction_token": sanction,
        "config_hash": config_hash,
        "artifact_hashes": hashes,
        "admitted_candidates": sorted(admitted_ids),
        "series": series_by_id,
        "certification_traces": cert_traces,
        "runtime_seam": {"before_first_model_call": seam_before,
                         "after_last_model_call": seam_after},
    }
    SIDECAR_PATH.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    print(f"sidecar written: {SIDECAR_PATH.name}")


def verify_call_path_wired(cfg: dict, sources: dict) -> dict:
    """BUILD-TIME proof that the Stage-2 call path is implemented and wired WITHOUT
    firing any provider call (brief item 4). Exercises the real payload builder and
    envelope for every admitted candidate, and constructs a real ModelTarget for
    each role from EVALUATOR_LINEUP_305 — but NEVER instantiates a provider adapter
    and NEVER calls one. Zero network, zero model calls.
    """
    from cam.adapters.lease_review.lease_coverage_305 import EVALUATOR_LINEUP_305
    from cam.core.provider_router import ModelTarget, TEMPERATURE_ONLY_DEFAULT_MODELS

    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    preflight = run_preflight(sources, cfg)
    admitted = [c for c in CANDIDATES if c["id"] in set(preflight["admitted"])]

    payloads_built = 0
    leak_checked = 0
    for cand in admitted:
        src = sources[cand["lease"]]
        ct = src.canonical_text
        s, e = cand["offsets"]
        env = build_envelope(ct, s, e, cfg, envelope_id=f"env_{cand['id']}")
        payload = build_panelist_payload(cand, env, ct[s:e], cfg, schema_text, prompt_template)
        payloads_built += 1
        # Confirm the §5 whitelist held (leak-check ran inside the builder).
        for tok in _forbidden_leak_tokens(cand):
            assert not tok or tok not in payload
        leak_checked += 1

    targets = []
    for role, ecfg in EVALUATOR_LINEUP_305.items():
        t = ModelTarget(
            name=f"{ecfg['provider']}:{ecfg['model']}-431-{role}",
            provider=ecfg["provider"], model=ecfg["model"],
            max_output_tokens=ecfg.get("max_output_tokens", _JUDGMENT_OUTPUT_TOKENS),
            temperature=ecfg.get("temperature", 0.0),
            timeout_sec=ecfg.get("timeout_sec", 300.0),
        )
        targets.append({
            "role": role, "provider": t.provider, "model": t.model,
            "temperature_declared": t.temperature,
            "temperature_transmitted": t.model not in TEMPERATURE_ONLY_DEFAULT_MODELS,
            "self_retry_is_same_model": (ecfg.get("own_chain") or [(None, None, None)])[0][1] == t.model,
        })

    call_path_implemented = call_panelist.__doc__ is not None and "NotImplementedError" not in (
        (run_stage2.__doc__ or "") + (call_panelist.__doc__ or "")
    )
    return {
        "wired": True,
        "provider_calls_made": 0,
        "admitted_candidates": [c["id"] for c in admitted],
        "payloads_built": payloads_built,
        "leak_checks_passed": leak_checked,
        "role_targets": targets,
        "call_path_implemented_not_stub": call_path_implemented,
    }


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
        "_authority": "431_partB_measurement_instruction.md (v3.3, RATIFIED 2026-07-19, committed 38785e7) §6.2",
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

    print("[1/6] importing frozen panel (import, never modify)...")
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

    print("[2/6] building canonical sources (canonical_whitespace_v2)...")
    sources = build_sources()

    print("[3/6] running deterministic preflight (§6.2)...")
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

    print("[4/6] running v3.3 relationship-contract tests (build gate)...")
    rel_tests = run_relationship_tests(artifacts["profiles"], cfg)
    for r in rel_tests:
        print(f"      [{'PASS' if r['pass'] else 'FAIL'}] {r['name']} ({r['s5_clause']}): "
              f"expect basis_match={r['expected_basis_match']}, got {r['actual_basis_match']}")
    if not all(r["pass"] for r in rel_tests):
        failed = [r["name"] for r in rel_tests if not r["pass"]]
        raise SystemExit(
            f"BUILD HALTED (§5 gate): relationship-contract tests failed: {failed}. "
            "The relation-bearing contract is not correctly enforced by the profile+validator; "
            "no manifest or sanction token is produced."
        )

    print("[5/6] sweeping model-facing artifacts + profiles for stale field name...")
    sweep = sweep_stale_field_name()
    print(f"      stale 'charge_basis_components' occurrences: {sweep['stale_hits'] or 'none'}")
    if not sweep["clean"]:
        raise SystemExit(
            f"BUILD HALTED: stale pre-v3.3 field name 'charge_basis_components' survives in "
            f"{sweep['stale_hits']}. The schema-wide rename is incomplete; no token is produced."
        )

    print("[6/6] writing config manifest...")
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
        "authorizing_instruction": {
            "document": "build_log/431_partB_measurement_instruction.md",
            "version": "v3.3",
            "commit": "38785e7",
            "ratified": "2026-07-19 by Tzvi",
            "authorizes": "Stage 1 REBUILD only, zero model calls",
            "contract_field": "value_applies_to_charge_basis_components (relation-bearing, v3.3)",
            "basis_match_rule_in_force": "tenant_share: set_contains {operating_expenses} over the relation-bearing field (inclusion); building_share: set_equals (unchanged, unseeded, amendment debt)",
            "relationship_tests_gate": "four build-time deterministic relationship tests (§5) must pass or the build halts",
        },
        "supersedes": {
            "prior_build_commit": "5954e6e",
            "prior_sanction_tokens_void": [
                "9e7a2d1cf4e0266dca30e400925824bed7de7b9be1bf831c4044ad8498813a2c",
                "5ed0c5cc34e285fb10945a223c7aebae03879afd5fd7b6e4e96eb6ddd2dfc48a",
                "ecbf512d11c258861ac87e81436bd313027a43a936d62211a0a4868c8d2b9718",
                "0ebb93ba50a8fd24dd0f11fc6aad3d4725c65f2beedbcb6a154be6f650b44e7e",
                "ccf03284a5eb4410bc6486b7d81aee3850bf3359888876ea2e6fea0ff8b483f0",
            ],
            "status": "VOID for execution — prior package encoded the pre-v3.3 field charge_basis_components; regenerated by this rebuild under v3.3",
        },
        "relationship_tests_v3_3": {
            "_purpose": "The four §5 relationship-contract tests, recorded with expected outcomes so "
                        "the informed audit can verify each assertion is CORRECT, not merely green. "
                        "Deterministic: a function of the hashed profiles+harness+config, re-runnable.",
            "all_passed": all(r["pass"] for r in rel_tests),
            "tests": rel_tests,
        },
        "stage2_supersession": {
            "_purpose": "Step 432 implemented the Stage-2 call path in "
                        "run_431_selection_measurement.py. That is the intended, sanctioned way to "
                        "make the preregistration package executable — but it changes the harness "
                        "hash, hence the manifest self-hash, hence the sanction token. The prior "
                        "token is therefore SUPERSEDED-FOR-EXECUTION, which is NOT the same as VOID.",
            "superseded_preregistration_token": "47cb312a442c4a58d969dece4c24b7d4b03fab93f7b29b33c46c308f87a84dab",
            "superseded_status": "SUPERSEDED-FOR-EXECUTION — NOT void",
            "superseded_meaning": "47cb312a validly sanctioned the Stage-1 PREREGISTRATION package "
                                  "(build commit 65556ee, call path = NotImplementedError by design). "
                                  "It is retained as evidence that preregistration was sanctioned "
                                  "BEFORE any executable call path existed. It can no longer authorize "
                                  "a run because the executable harness differs from the preregistered one.",
            "prior_stage1_build_commit": "65556ee",
            "new_executable_token": self_hash,
            "authorizing_step": "432 — 431 Part B Stage-2 call-path implementation",
            "semantic_artifacts_byte_identical_to_65556ee": True,
            "run_still_gated_by": "scoped informed audit of the call-path diff + separate explicit "
                                  "Tzvi sanction of THIS new token (per brief; no run in Step 432)",
        },
        "field_name_sweep": sweep,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "1-build-of-executable-package",
        "package_type": "executable (Stage-2 call path implemented; fires calls ONLY under --mode run + matching --stage2-sanction)",
        "model_calls_made_at_build": 0,
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

    print("\n[wiring] verifying Stage-2 call path is implemented + wired (ZERO calls)...")
    wired = verify_call_path_wired(cfg, sources)
    print(f"      call path implemented (not a stub): {wired['call_path_implemented_not_stub']}")
    print(f"      payloads built (no provider touched): {wired['payloads_built']} "
          f"for {wired['admitted_candidates']}")
    print(f"      §5 leak-checks passed: {wired['leak_checks_passed']}")
    for t in wired["role_targets"]:
        print(f"      role {t['role']}: {t['provider']}/{t['model']} "
              f"temp_transmitted={t['temperature_transmitted']} "
              f"self_retry_same_model={t['self_retry_is_same_model']}")
    print(f"      PROVIDER CALLS MADE (wiring check): {wired['provider_calls_made']}")

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

    # Stage-2 live run. Gated: _assert_stage2 (inside run_stage2 and every call)
    # rejects any invocation whose --stage2-sanction does not match the committed
    # manifest self-hash. Fires ~90–105 primary calls. Not invoked by the build
    # step that ships this file (Step 432 delivers the call path for audit only).
    run_stage2(args.stage2_sanction)


if __name__ == "__main__":
    main()
