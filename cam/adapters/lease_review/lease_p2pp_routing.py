"""
P2'' directional routing helper — Step 376h.

classify_directional_p2pp(finding) routes a directional_mismatch finding under P2'':
  consequence-anchored, support-gated, high/medium-collapsed, harmful-only Risk.
  Sign/directionality is diagnostic-only and must never affect the returned bucket.

apply_p2pp_routing(cross_provision_findings) batch-applies the helper, attaching
  "p2pp_routing" to each directional_mismatch finding in place.

Strict early-return precedence (rules 1 → 6):
  Rule 1a: consequence_source != "assessed"   → review_needed / consequence_not_assessed
  Rule 1b: mismatch_support not adequate       → review_needed / mismatch_support_insufficient
  Rule 2:  context_dependent consequence       → review_needed / context_dependent_consequence
  Rule 3:  harmful + high/medium               → risk          / assessed_harmful_material_consequence
  Rule 4:  beneficial                          → improvement   / assessed_beneficial_consequence
  Rule 5:  neutral                             → improvement   / assessed_neutral_consequence
  Rule 6:  harmful + low/not_applicable/other  → improvement   / harmful_but_not_actionably_material

Rules 3–6 are only reachable after rule 1 confirms assessed + adequate support.
Sign/directionality may be displayed and audited but must NOT appear in routing logic.

Authorized scope (Step 376h): directional_mismatch findings only.
Non-directional findings (compound_risk, cross_coverage_gap) are not touched.
"""

# ── Constants ──────────────────────────────────────────────────────────────────

_ADEQUATE_MISMATCH = frozenset({"unanimous", "majority", "adequate"})
_MATERIAL_HIGH_MED = frozenset({"high", "medium"})

# Legacy gap_impact → use_consequence mapping (pre-375M artifacts only).
# Only recognized when use_consequence is absent AND gap_impact is the confirmed
# Stage 5e field (spec §backward-compat).
_GAP_IMPACT_NORM = {"favorable": "beneficial", "adverse": "harmful"}


# ── Derivation helpers ─────────────────────────────────────────────────────────

def _derive_mismatch_support(finding: dict) -> str:
    """
    Derive mismatch_support from a stored field or from evaluator_agreement.

    Priority:
      1. finding["mismatch_support"] if already present (forward-compat)
      2. VERIFICATION_INCOMPLETE severity → "unknown"
      3. evaluator_agreement "N-M" → unanimous (3), majority (2), singleton (1), inadequate (0)
      4. Fallback: "unknown"
    """
    ms = (finding.get("mismatch_support") or "").lower().strip()
    if ms:
        return ms

    sev = (finding.get("severity") or "").upper()
    if sev == "VERIFICATION_INCOMPLETE":
        return "unknown"

    ea = finding.get("evaluator_agreement") or ""
    parts = ea.split("-")
    try:
        confirmed = int(parts[0])
    except (ValueError, IndexError):
        return "unknown"

    if confirmed >= 3:
        return "unanimous"
    if confirmed == 2:
        return "majority"
    if confirmed == 1:
        return "singleton"
    return "inadequate"


def _derive_consequence_source(finding: dict) -> str:
    """
    Derive consequence_source from use_consequence_source (written by Stage 5e-F).
    Returns normalized string or "unknown" if absent.
    """
    cs = (finding.get("consequence_source") or finding.get("use_consequence_source") or "").lower().strip()
    return cs if cs else "unknown"


def _normalize_use_consequence(finding: dict) -> str:
    """
    Return the use_consequence value, normalizing legacy gap_impact if needed.
    Returns lowercase value or empty string if absent.
    """
    uc = (finding.get("use_consequence") or "").lower().strip()
    if uc:
        return uc
    # Legacy gap_impact normalization (pre-375M artifacts)
    gi = (finding.get("gap_impact") or "").lower().strip()
    return _GAP_IMPACT_NORM.get(gi, gi) if gi else ""


def _derive_diagnostic_sign(finding: dict) -> str:
    """
    Return diagnostic_sign from directionality field.
    Display/audit only — must NOT be read by routing logic.
    """
    dir_val = (finding.get("directionality") or "").lower().strip()
    if dir_val in ("tenant_unprotected", "landlord_unprotected", "bilateral"):
        return dir_val
    return "unclear"


# ── Core routing helper ────────────────────────────────────────────────────────

def classify_directional_p2pp(finding: dict) -> dict:
    """
    Return action bucket + route reason for a directional finding under P2''.

    Precedence is strict early-return (rules 1 → 6). Once a rule fires, return
    immediately. Rules 3–6 are unreachable when rule 1 fails; they must NOT
    re-gate on consequence_source or mismatch_support.

    Sign/directionality is computed for diagnostic output but must never affect
    the returned bucket or routing_reason.

    Args:
        finding: a cross_provision_findings entry with finding_type == "directional_mismatch".
                 Requires consequence fields attached by lease_finding_consequence Stage 5e-F.

    Returns:
        dict: bucket, routing_policy, routing_reason, routing_inputs,
              diagnostic_sign, sign_support, routing_use.
    """
    uc   = _normalize_use_consequence(finding)
    mat  = (finding.get("materiality") or "").lower().strip()
    csrc = _derive_consequence_source(finding)
    ms   = _derive_mismatch_support(finding)
    diag = _derive_diagnostic_sign(finding)
    # sign_support: best available field; defaults to not_computed when per-evaluator
    # exposed_party data is not present at this layer.
    ss   = (finding.get("sign_support") or finding.get("sign_consensus") or "not_computed")

    routing_inputs = {
        "use_consequence":    uc or None,
        "materiality":        mat or None,
        "consequence_source": csrc or None,
        "mismatch_support":   ms,
    }

    def _result(bucket, reason, subtype=None):
        r = {
            "bucket":          bucket,
            "routing_policy":  "P2''",
            "routing_reason":  reason,
            "routing_inputs":  routing_inputs,
            "diagnostic_sign": diag,
            "sign_support":    ss,
            "routing_use":     "diagnostic_only",
        }
        if subtype:
            r["subtype"] = subtype
        return r

    # ── Rule 1a: consequence not assessed ─────────────────────────────────────
    # Includes: absent, defaulted_floor, not_eligible, unknown, null/missing.
    # This guardrail outranks ALL consequence labels including beneficial/neutral.
    if csrc != "assessed" or not uc:
        return _result("review_needed", "consequence_not_assessed")

    # ── Rule 1b: mismatch support not adequate ────────────────────────────────
    # Includes: weak, singleton, inadequate, unknown, null/missing.
    # This guardrail outranks ALL consequence labels.
    if ms not in _ADEQUATE_MISMATCH:
        return _result("review_needed", "mismatch_support_insufficient")

    # ── Rules 2–6: consequence_source == "assessed" AND mismatch_support adequate ──
    # (consequence_source and mismatch_support are guaranteed by rule 1 above)

    # ── Rule 2: context-dependent consequence ──────────────────────────────────
    if uc == "context_dependent":
        return _result("review_needed", "context_dependent_consequence")

    # ── Rule 3: harmful + material (high or medium) → Risk ────────────────────
    # High and medium are intentionally collapsed into one actionable-material tier.
    if uc == "harmful" and mat in _MATERIAL_HIGH_MED:
        return _result("risk", "assessed_harmful_material_consequence")

    # ── Rule 4: beneficial → Improvement (favorable position) ─────────────────
    if uc == "beneficial":
        return _result("improvement", "assessed_beneficial_consequence", "favorable_position")

    # ── Rule 5: neutral → Improvement (locked product convention) ─────────────
    # neutral → Improvement is LOCKED; do not reopen without explicit decision #6.
    if uc == "neutral":
        return _result("improvement", "assessed_neutral_consequence", "no_protective_action")

    # ── Rule 6: harmful + low/not_applicable/other materiality → Improvement ──
    # Low-materiality harmful directional issues are not actionably material Risk.
    # Sign adversity does NOT override this rule.
    if uc == "harmful":
        return _result("improvement", "harmful_but_not_actionably_material",
                       "low_materiality_directional_issue")

    # ── Fallthrough: unrecognized use_consequence with assessed source ─────────
    # Defensive; should not be reached for any valid use_consequence value.
    return _result("review_needed", "consequence_not_assessed")


# ── Batch application ─────────────────────────────────────────────────────────

def apply_p2pp_routing(cross_provision_findings: list) -> int:
    """
    Attach "p2pp_routing" to every directional_mismatch finding in place.

    Non-directional findings (compound_risk, cross_coverage_gap, cross_coverage_relief)
    are skipped — P2'' scope is directional_mismatch only.

    Args:
        cross_provision_findings: list of finding dicts (modified in place).

    Returns:
        Count of directional findings that received p2pp_routing.
    """
    n = 0
    for f in cross_provision_findings:
        if f.get("finding_type") == "directional_mismatch":
            f["p2pp_routing"] = classify_directional_p2pp(f)
            n += 1
    return n
