"""
lease_scorer.py — CAM Reliability Score & ASG, inline pipeline integration.

Contains the same scoring logic as cam_scorer.py (standalone batch tool),
adapted for inline use within the lease pipeline.

Called by lease_adapter.py after Stage 6 dispositions are finalized.
Mutates dispositions in place: attaches cam_score dict to each provision.
Returns cam_contract_summary for top-level result.

cam_scorer.py (standalone) remains unchanged for batch/audit use.
"""

# ---------------------------------------------------------------------------
# Signal weights — lease domain
# ---------------------------------------------------------------------------

SIGNAL_WEIGHTS_PERMISSIVE = {
    "cross_reference_dependency": 0.04,  # fires on provision anatomy (mentions other sections), not on whether
                                          # the deviation itself depends on those sections — nearly irrelevant
                                          # for ASG; real cross-ref sensitivity comes from co-firing signals
    "negation_pattern":           0.30,  # obligation direction shift — moderately interpretation-sensitive
    "quantitative_deviation":     0.08,  # explicit number — least interpretation-sensitive deviation type
    "_unknown":                   0.20,
}

SIGNAL_WEIGHTS_STRICT = {
    "cross_reference_dependency": 0.30,
    "negation_pattern":           0.55,
    "quantitative_deviation":     0.62,
    "_unknown":                   0.35,
}

SIGNAL_E_PENALTIES_STRICT = {
    "cross_reference_dependency": 0.98,  # near-neutral: provision having cross-references doesn't itself
                                          # reduce epistemic confidence in an identified deviation
    "negation_pattern":           0.80,  # direction change has some scope ambiguity
    "quantitative_deviation":     0.93,  # explicit number — near-certain in strict mode too
}

CHALLENGE_CONFIRMATION_F_BOOST = 0.10

# Evidence basis multipliers for E component (Step 189)
# Reflects how well-grounded the evaluator's reasoning is.
# Applied on top of self-reported confidence and challenge factor.
EVIDENCE_BASIS_FACTORS_PERMISSIVE = {
    "explicit_text":        1.00,  # Full face value — reasoning grounded in text
    "structural_inference": 0.93,  # Slight discount — reasoning from context
    "absence":              0.90,  # Reasoning from what's not there — harder to verify
    "ambiguous":            0.82,  # Model unsure of its own basis
    "unverified_citation":  0.78,  # Cited a section that doesn't exist — meaningful discount
    None:                   0.93,  # Missing field — treat as structural_inference
}

EVIDENCE_BASIS_FACTORS_STRICT = {
    "explicit_text":        1.00,
    "structural_inference": 0.87,
    "absence":              0.83,
    "ambiguous":            0.72,
    "unverified_citation":  0.65,  # Fabricated citation — significant strict penalty
    None:                   0.87,
}

CHALLENGE_FACTORS_PERMISSIVE = {
    None:                    1.00,
    "SUBSTANTIVE_DEVIATION": 1.05,
    "COSMETIC_ONLY":         0.92,
    "NEEDS_EXPERT":          0.78,
}

CHALLENGE_FACTORS_STRICT = {
    None:                    0.97,
    "SUBSTANTIVE_DEVIATION": 1.00,
    "COSMETIC_ONLY":         0.85,
    "NEEDS_EXPERT":          0.65,
}

# ---------------------------------------------------------------------------
# Agreement (A)
# ---------------------------------------------------------------------------

def _parse_agreement(agreement_pattern: str) -> float:
    if not agreement_pattern:
        return 0.75
    parts = agreement_pattern.split()
    if not parts:
        return 0.75
    vote_part = parts[0]
    try:
        majority, minority = [int(x) for x in vote_part.split("-")]
    except (ValueError, AttributeError):
        return 0.75
    total = majority + minority
    if total == 0:
        return 0.75
    if minority == 0:
        return 1.00
    elif majority / total >= 0.6:
        return 0.75
    else:
        return 0.50

def _parse_agreement_strict(a_perm: float) -> float:
    if a_perm >= 1.0:
        return 1.0
    elif a_perm >= 0.75:
        return a_perm * 0.90
    else:
        return a_perm * 0.80

# ---------------------------------------------------------------------------
# Evidence alignment (E)
# ---------------------------------------------------------------------------

def _compute_e(provision: dict, strict: bool = False) -> float:
    confs = provision.get("evaluator_confidences", {})
    avg_conf = sum(confs.values()) / len(confs) if confs else 0.85
    challenge = provision.get("challenge_finding")
    factors = CHALLENGE_FACTORS_STRICT if strict else CHALLENGE_FACTORS_PERMISSIVE
    challenge_factor = factors.get(challenge, 0.88)
    e = min(1.0, avg_conf * challenge_factor)

    # Step 189: evidence basis multiplier
    # Use consensus basis (most conservative across evaluators) if available,
    # fall back to structural_inference if field not present (older pipeline runs)
    basis = provision.get("evidence_basis_consensus", None)
    basis_factors = EVIDENCE_BASIS_FACTORS_STRICT if strict else EVIDENCE_BASIS_FACTORS_PERMISSIVE
    basis_factor = basis_factors.get(basis, basis_factors[None])
    e = e * basis_factor

    if strict:
        signals = provision.get("fragility", {}).get("signals", [])
        for sig in signals:
            penalty = SIGNAL_E_PENALTIES_STRICT.get(sig, 0.90)
            e *= penalty
        e = max(0.10, e)
    return e

# ---------------------------------------------------------------------------
# Reasoning validity (R)
# ---------------------------------------------------------------------------

def _r_base_from_stages(stages_run: list, challenge_finding) -> float:
    stages_set = set(stages_run)
    if 5 in stages_set and 3 in stages_set:
        return 1.00
    elif 3 in stages_set and 5 not in stages_set:
        return 0.88
    elif 3 not in stages_set:
        return 0.85
    return 0.90

def _r_hidden_penalty(hidden_deps: list, strict: bool) -> float:
    n = len(hidden_deps)
    if n == 0:
        return 1.00
    elif n <= 2:
        return 0.95 if not strict else 0.92
    elif n <= 4:
        return 0.90 if not strict else 0.85
    else:
        return 0.85 if not strict else 0.78

def _compute_r(provision: dict, strict: bool = False) -> float:
    cam_meta = provision.get("cam_metadata", {})
    stages_run = cam_meta.get("stages_run", [])
    challenge = provision.get("challenge_finding")
    hidden = provision.get("hidden_dependencies", [])
    r_base = _r_base_from_stages(stages_run, challenge)
    if strict and challenge == "NEEDS_EXPERT":
        r_base *= 0.72
    r_hidden = _r_hidden_penalty(hidden, strict)
    return r_base * r_hidden

# ---------------------------------------------------------------------------
# Structural fragility (F_structural)
# ---------------------------------------------------------------------------

def _compute_f_structural(provision: dict) -> float:
    """
    Compute structural fragility (F_structural).
    This measures how complex/interpretation-sensitive the clause is.
    Used ONLY to compute CAM_strict (and thus ASG).
    Does NOT reduce CAM_perm — structural complexity is not the same as uncertainty.
    """
    signals = provision.get("fragility", {}).get("signals", [])
    weights = SIGNAL_WEIGHTS_PERMISSIVE  # use permissive weights for gap computation

    total_weight = 0.0
    for sig in signals:
        total_weight += weights.get(sig, weights["_unknown"])
    f = 1.0 - min(1.0, total_weight)
    f = max(0.08, f)

    # Challenge confirmation boosts: if challenger confirmed SUBSTANTIVE,
    # slightly reduce fragility gap (the finding held up under adversarial scrutiny)
    challenge = provision.get("challenge_finding")
    if challenge == "SUBSTANTIVE_DEVIATION":
        f = min(1.0, f + CHALLENGE_CONFIRMATION_F_BOOST)

    return f

# ---------------------------------------------------------------------------
# Governance signal
# ---------------------------------------------------------------------------

def _governance_signal(cam_perm: float, asg: float) -> str:
    if cam_perm < 50:
        return "WITHHOLD_SIGNAL"
    elif cam_perm < 70:
        return "REVIEW_SIGNAL"
    elif asg >= 28:
        return "ASSERT_REVIEW_SIGNAL"
    else:
        return "ASSERT_SIGNAL"

# ---------------------------------------------------------------------------
# Pattern classification
# ---------------------------------------------------------------------------

def _classify_pattern(cam_perm: float, asg: float, verdict: str) -> str:
    if cam_perm >= 70 and asg < 28:
        return "PATTERN_1_RELIABLE"
    elif cam_perm >= 70 and asg >= 28:
        return "PATTERN_2_FRAGILE_PERSUASIVE"
    elif cam_perm < 50 and verdict == "UNCLEAR":
        return "PATTERN_3_WEAK_UNCLEAR"
    elif cam_perm < 50:
        return "PATTERN_3_WEAK"
    elif cam_perm >= 50 and verdict == "UNCLEAR":
        return "PATTERN_4_MISSED_WEAKNESS"
    else:
        return "PATTERN_REVIEW"

# ---------------------------------------------------------------------------
# Per-provision score
# ---------------------------------------------------------------------------

def compute_cam_score(provision: dict) -> dict:
    """
    Compute CAM scores using the split F architecture:
    - CAM_perm = A × E × R × 100  (uncertainty-only factors)
    - CAM_strict = A_strict × E_strict × R_strict × F_structural × 100
      (structural fragility widens the gap)
    - ASG = CAM_perm − CAM_strict
    """
    verdict = provision.get("final_verdict", "?")

    # Permissive path: uncertainty factors only (A, E, R)
    A_perm   = _parse_agreement(provision.get("agreement_pattern", ""))
    E_perm   = _compute_e(provision, strict=False)
    R_perm   = _compute_r(provision, strict=False)
    CAM_perm = round(100.0 * A_perm * E_perm * R_perm, 2)

    # Structural fragility: only affects the strict→permissive gap
    F_structural = _compute_f_structural(provision)

    # Strict path: apply strict E/R and structural fragility
    A_strict   = _parse_agreement_strict(A_perm)
    E_strict   = _compute_e(provision, strict=True)
    R_strict   = _compute_r(provision, strict=True)
    CAM_strict = round(100.0 * A_strict * E_strict * R_strict * F_structural, 2)

    ASG = round(CAM_perm - CAM_strict, 2)
    gov = _governance_signal(CAM_perm, ASG)
    pat = _classify_pattern(CAM_perm, ASG, verdict)

    return {
        "CAM_perm":          CAM_perm,
        "CAM_strict":        CAM_strict,
        "ASG":               ASG,
        "governance_signal": gov,
        "pattern":           pat,
        "fragility_signals": provision.get("fragility", {}).get("signals", []),
        "A":                 round(A_perm, 4),
        "E_perm":            round(E_perm, 4),
        "R_perm":            round(R_perm, 4),
        "F_perm":            round(F_structural, 4),   # kept as F_perm for backward compat
        "evidence_basis":    provision.get("evidence_basis_consensus", None),
    }

# ---------------------------------------------------------------------------
# Batch — mutates dispositions in place, returns contract summary
# ---------------------------------------------------------------------------

def score_all_provisions(dispositions: list) -> dict:
    """
    Score all provisions and attach cam_score to each in place.
    Returns a cam_contract_summary dict for top-level result.

    Usage in lease_adapter.py:
        cam_contract_summary = score_all_provisions(dispositions)
    """
    gov_counts = {
        "ASSERT_SIGNAL": 0,
        "ASSERT_REVIEW_SIGNAL": 0,
        "REVIEW_SIGNAL": 0,
        "WITHHOLD_SIGNAL": 0,
    }
    fragile_persuasive = []

    for prov in dispositions:
        score = compute_cam_score(prov)
        prov["cam_score"] = score                    # attach in place
        g = score["governance_signal"]
        gov_counts[g] = gov_counts.get(g, 0) + 1
        if score["pattern"] == "PATTERN_2_FRAGILE_PERSUASIVE":
            fragile_persuasive.append(prov["provision_id"])

    total = len(dispositions)
    asserted = gov_counts["ASSERT_SIGNAL"] + gov_counts["ASSERT_REVIEW_SIGNAL"]
    withheld = gov_counts["WITHHOLD_SIGNAL"]

    # Separate withholds with no template baseline (tenant-added clauses, no comparison possible)
    # from withholds due to genuine evaluator uncertainty
    withhold_no_baseline = sum(
        1 for p in dispositions
        if (p.get("cam_score", {}).get("governance_signal") == "WITHHOLD_SIGNAL"
            and not (p.get("template_text") or "").strip())
    )
    withhold_uncertain = withheld - withhold_no_baseline

    # Averages over all scored provisions
    perm_vals  = [p["cam_score"]["CAM_perm"]  for p in dispositions if "cam_score" in p]
    strict_vals = [p["cam_score"]["CAM_strict"] for p in dispositions if "cam_score" in p]
    asg_vals   = [p["cam_score"]["ASG"]        for p in dispositions if "cam_score" in p]
    avg_perm   = round(sum(perm_vals)  / len(perm_vals),  2) if perm_vals  else None
    avg_strict = round(sum(strict_vals) / len(strict_vals), 2) if strict_vals else None
    avg_asg    = round(sum(asg_vals)   / len(asg_vals),   2) if asg_vals   else None

    return {
        "governance_counts":      gov_counts,
        "fragile_persuasive":     fragile_persuasive,
        "provisions_scored":      total,
        "analysis_completeness":  round(asserted / total, 3) if total else 0.0,
        "withhold_count":         withheld,
        "withhold_no_baseline":   withhold_no_baseline,
        "withhold_uncertain":     withhold_uncertain,
        "avg_cam_permissive":     avg_perm,
        "avg_cam_strict":         avg_strict,
        "avg_asg":                avg_asg,
    }
