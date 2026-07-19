"""
Step 427 — Named parameter block + declared dependency map.

Doctrine (423 spec §5): key terms are not one LP's clause text — they are
document parameters that many provisions depend on. The key-terms table is
not "LP-00's content." It is the document's quantitative spine.

This module extracts a NAMED, DOCUMENT-LEVEL parameter set (never a
provision, never an LP), attaches each parameter's verified span to every
LP that declares a dependency on it — deterministically, by dict lookup,
with zero model discretion — and enforces Gate B: every declared
dependency must be satisfied by a verified span, or the extraction is
rejected before Stage 5.

Attachment is deterministic. The model is never asked to include a
parameter in a dependent LP and therefore cannot forget to.

Gate B is keyed to declared dependencies, never to literal values, and
never to evaluator agreement. Agreement is not sufficiency.

This step does not build the selector panel. Span-to-LP relevance beyond
the declared parameter dependencies remains ungoverned.

Not wired into the live Mode C / Stage 5 pipeline in this slice — per 423
spec §8, no Stage 5 work proceeds until Gates A-D pass together, and Gate
C (assignment stability across runs) has not been measured for this
substrate (424/426 found real offset drift on several targets). This
module is built and tested standalone; the wiring decision is a later,
separately authorized step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cam.adapters.lease_review.lease_evidence_spans import (
    CanonicalSource,
    EvidenceSpan,
    VERIFIED,
    resolve_span,
)


# ── Parameter targets (elicitation-side; document-level, LP-unassigned) ────────
# Deliberately narrow — 423 spec §5.1 "start with exactly these four", per
# the 427 brief. Adding a parameter here does NOT attach it to any LP;
# that requires a corresponding DEPENDENCY_MAP entry, added separately and
# only when justified by a measured, verified span (see module docstring).
#
# NOTE: no lease-specific VALUE (a percentage, a dollar figure) appears
# anywhere in this file — only LABELS/synonyms describing what to look
# for. Gate B's completeness check (see check_gate_b/enforce_gate_b below)
# reads parameter NAMES and verification status only.
PARAMETER_TARGETS: List[Dict[str, Any]] = [
    {
        "param_name": "tenant_share",
        "element_label": "Tenant's Share of Operating Expenses percentage",
        "synonyms": ["Tenant's Share of Operating Expenses of Building", "tenant's proportionate share percentage"],
    },
    {
        "param_name": "building_share",
        "element_label": "Building's Share of Project Operating Expenses percentage",
        "synonyms": ["Building's Share of Project"],
    },
    {
        "param_name": "rent_adjustment_pct",
        "element_label": "Rent Adjustment Percentage (annual escalation rate)",
        "synonyms": ["Rent Adjustment Percentage", "annual rent increase percentage"],
    },
    {
        "param_name": "base_rent",
        "element_label": "Base Rent amount stated in the key-terms block",
        "synonyms": ["Base Rent", "per rentable square foot"],
    },
]

PARAMETER_NAMES = frozenset(t["param_name"] for t in PARAMETER_TARGETS)


# ── Declared dependency map ───────────────────────────────────────────────────
# Per-LP, in code, explicit. Start with exactly these two LPs and these
# four parameters (427 brief). Every entry here must be justifiable from a
# measured, verified span — per Step 426, all four parameters verified at
# 5/5 with byte-stable offsets under canonical_v2. Do not add a dependency
# without a corresponding measurement.
DEPENDENCY_MAP: Dict[str, List[str]] = {
    "LP-02": ["base_rent", "rent_adjustment_pct"],
    "LP-07": ["tenant_share", "building_share"],
}


# ── Parameter ────────────────────────────────────────────────────────────────

@dataclass
class Parameter:
    """A named, document-level parameter carrying a verified EvidenceSpan
    and provenance. Never a provision, never an LP."""
    name: str
    span: EvidenceSpan
    provenance: Dict[str, Any] = field(default_factory=dict)


# ── Extraction (model proposes via elicitation; code resolves via 423A) ────────

def extract_parameters(
    canonical_source: CanonicalSource,
    canonical: bool = True,
) -> Dict[str, Any]:
    """Elicit the named parameter set via the SAME element-guided
    elicitation call path as LP elements (lease_element_elicitation.py) —
    same prompt, same schema, same resolver, no prompt/resolver change.
    The target list is document-level (PARAMETER_TARGETS), entirely
    separate from any LP's expected_elements_305 — this is what makes
    extraction "document parameters," not "one provision's clause text."

    Returns {"parameters": {param_name: Parameter, ...}, "meta": {...}}.
    Only VERIFIED quotes become Parameters. A parameter with no verified
    quote is simply absent from the returned dict — Gate B (below) is what
    turns that absence into a hard failure for a dependent LP; this
    function itself never raises for a missing parameter.
    """
    from cam.adapters.lease_review.lease_element_elicitation import (
        elicit_spans_for_targets,
        resolve_target_ordinal,
    )

    elements = [
        {"element_id": t["param_name"], "element_label": t["element_label"], "synonyms": t.get("synonyms", [])}
        for t in PARAMETER_TARGETS
    ]
    elicitation_result = elicit_spans_for_targets(
        canonical_source.canonical_text, elements, canonical=canonical
    )

    parameters: Dict[str, Parameter] = {}

    for match in elicitation_result.get("target_matches", []):
        param_name = resolve_target_ordinal(match.get("target", ""), elements)
        if param_name in parameters:
            continue  # first verified quote wins; a parameter is one value, not a list
        for i, quote in enumerate(match.get("quotes", []), start=1):
            span = resolve_span(
                canonical_source, quote, evidence_span_id=f"PARAM-{param_name}-{i:02d}"
            )
            if span.verification_status == VERIFIED:
                parameters[param_name] = Parameter(
                    name=param_name,
                    span=span,
                    provenance={
                        "elicited_target": match.get("target"),
                        "quote_index": i,
                        "source_document_hash": canonical_source.source_document_hash,
                    },
                )
                break

    return {"parameters": parameters, "meta": elicitation_result["meta"]}


# ── Deterministic attachment ─────────────────────────────────────────────────

def attach_parameters_to_lp_evidence(
    parameters: Dict[str, Parameter],
    lp_id: str,
    dependency_map: Optional[Dict[str, List[str]]] = None,
) -> List[Parameter]:
    """Deterministic attachment: return the Parameter objects LP `lp_id`'s
    DECLARED dependencies point to, in declared order.

    Purely a dict lookup against `dependency_map` (defaults to the module
    DEPENDENCY_MAP) — no model call, no discretion, no randomness. The
    model is never asked to remember to include a parameter in a
    dependent LP and therefore cannot forget to.

    Non-destructive: `parameters` is read, never mutated. The same
    Parameter object (same span, same offsets, same identity) is returned
    to every LP that declares a dependency on it — attaching a parameter
    to one LP does not remove or alter it for any other LP or for a
    second call with the same arguments.
    """
    dep_map = dependency_map if dependency_map is not None else DEPENDENCY_MAP
    dep_names = dep_map.get(lp_id, [])
    return [parameters[name] for name in dep_names if name in parameters]


# ── Gate B — completeness on declared dependencies ──────────────────────────────

def check_gate_b(
    parameters: Dict[str, Parameter],
    lp_ids: Optional[List[str]] = None,
    dependency_map: Optional[Dict[str, List[str]]] = None,
) -> List[Dict[str, str]]:
    """Gate B: for every (lp_id, dependency) pair in `dependency_map`,
    check whether `parameters` contains a VERIFIED Parameter of that name.

    Keyed to declared dependency NAMES only — this function reads
    parameter names and `span.verification_status`, never a span's text
    or value, and never any evaluator output. It generalizes to any
    lease because it never contains a lease-specific literal.

    Returns one record per (lp_id, dependency): {"lp_id", "dependency",
    "gate_status": "pass" | "fail"}.
    """
    dep_map = dependency_map if dependency_map is not None else DEPENDENCY_MAP
    lps = lp_ids if lp_ids is not None else list(dep_map.keys())

    results = []
    for lp_id in lps:
        for dep_name in dep_map.get(lp_id, []):
            param = parameters.get(dep_name)
            satisfied = param is not None and param.span.verification_status == VERIFIED
            results.append({
                "lp_id": lp_id,
                "dependency": dep_name,
                "gate_status": "pass" if satisfied else "fail",
            })
    return results


def enforce_gate_b(
    parameters: Dict[str, Parameter],
    canonical: bool = True,
    lp_ids: Optional[List[str]] = None,
    dependency_map: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Enforce Gate B. In canonical mode, any unsatisfied declared
    dependency raises GateAbortError (imported from lease_adapter — same
    exception type and same fail-closed doctrine as the 422C extraction
    completeness gate) before Stage 5 would run. In non-canonical mode,
    returns a degraded result instead of raising.

    `canonical` is an explicit parameter, read directly — never inferred
    from `fallback_used` or any other flag (422D doctrine).
    """
    results = check_gate_b(parameters, lp_ids=lp_ids, dependency_map=dependency_map)
    failures = [r for r in results if r["gate_status"] == "fail"]

    if not failures:
        return {"gate_status": "pass", "failures": []}

    if canonical:
        from cam.adapters.lease_review.lease_adapter import GateAbortError
        raise GateAbortError(
            f"Gate B failure: {len(failures)} declared parameter dependency(ies) unsatisfied: "
            f"{[(f['lp_id'], f['dependency']) for f in failures]}. "
            "Cannot produce a valid legal analysis without required parameters. "
            "Agreement among evaluators cannot substitute for a satisfied dependency."
        )

    return {"gate_status": "degraded", "failures": failures}
