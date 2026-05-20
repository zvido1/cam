"""
Step 351 — Architecture A Phase 2: Verdict Distance at LP Layer.

Computes semantic distance between evaluator LP-level verdicts on a six-rung
ordinal ladder and derives disagreement severity, confidence capping, and
review priority escalation from that distance combined with Stage 5e consequence.

Two independent signals:
  - Verdict distance: epistemic uncertainty about the evaluation itself (tenant-agnostic)
  - Consequence: use-aware risk if protection is actually missing (from Stage 5e)

These are consumed independently to govern confidence ceiling and review priority.
"""

from collections import Counter


# ── Sentinel for LPs that never entered Stage 305 ─────────────────────────────
# Distinct from severity="none" (evaluators agreed) and from bare null (error).
NOT_ASSESSED_SENTINEL = {
    "max_distance": None,
    "severity": "not_assessed",
    "pair": [],
    "all_distances": [],
    "reason": "stage_305_not_run",
}


# ── Six-rung ordinal ladder ────────────────────────────────────────────────────

VERDICT_RANK = {
    "explicitly_present":    0,
    "implicitly_present":    1,
    "covered_in_other_lp":   2,
    "covered_in_other_LP":   2,    # case variant
    "covered_by_default_law": 2,   # same ordinal tier as cross-LP
    "unclear":               3,
    "missing":               5,    # deliberate gap — epistemic rupture weighting
}

_SEVERITY_ORDER = ["high", "medium", "low"]


def derive_verdict_distance(v1: str, v2: str) -> int:
    """Return ordinal distance between two verdict states on the six-rung ladder.

    Returns 0 for identical verdicts or unknown verdicts (fail-safe).
    """
    r1 = VERDICT_RANK.get(v1)
    r2 = VERDICT_RANK.get(v2)
    if r1 is None or r2 is None:
        return 0
    return abs(r1 - r2)


def derive_disagreement_severity(verdicts: list) -> dict:
    """Given a list of LP-level verdict strings from all evaluators, return a
    disagreement severity dict.

    Returns:
        {
            "max_distance": int,
            "severity": "none" | "minor" | "moderate" | "severe",
            "pair": [v_high, v_low],
            "all_distances": [(vi, vj, dist), ...]
        }

    Severity thresholds:
        distance 0       → "none"
        distance 1       → "minor"
        distance 2–3     → "moderate"
        distance ≥ 4     → "severe"  (only EP ↔ MI = 5 reaches this)
    """
    if not verdicts:
        return dict(NOT_ASSESSED_SENTINEL)
    pairs = [
        (verdicts[i], verdicts[j])
        for i in range(len(verdicts))
        for j in range(i + 1, len(verdicts))
    ]
    distances = [(v1, v2, derive_verdict_distance(v1, v2)) for v1, v2 in pairs]
    if not distances:
        return {"max_distance": 0, "severity": "none", "pair": [], "all_distances": []}

    max_dist = max(d for _, _, d in distances)
    max_pair = max(distances, key=lambda x: x[2])

    if max_dist == 0:
        severity = "none"
    elif max_dist == 1:
        severity = "minor"
    elif max_dist <= 3:
        severity = "moderate"
    else:
        severity = "severe"

    return {
        "max_distance": max_dist,
        "severity": severity,
        "pair": [max_pair[0], max_pair[1]],
        "all_distances": [[v1, v2, d] for v1, v2, d in distances],
    }


def _min_confidence(a: str, b: str) -> str:
    """Return the more conservative (lower) of two confidence levels."""
    order = ["high", "medium", "low"]
    ia = order.index(a) if a in order else 2
    ib = order.index(b) if b in order else 2
    return order[max(ia, ib)]


def apply_distance_confidence_cap(
    base_confidence: str,
    severity: str,
    vote_count: int,
    consequence: str,
) -> str:
    """Apply distance-based confidence cap to base LP-level confidence.

    Args:
        base_confidence: "high" | "medium" | "low" — from vote count
        severity:        "none" | "minor" | "moderate" | "severe"
        vote_count:      number of evaluators in agreement with majority
        consequence:     "low" | "medium" | "moderate" | "high" — Stage 5e materiality
                         ("medium" and "moderate" are treated identically)

    Returns capped confidence string.
    """
    if severity in ("none", "not_assessed") or vote_count == 3:
        return base_confidence
    # Normalize "medium" → "moderate" for matrix lookup
    _con = "moderate" if consequence in ("medium", "moderate") else consequence
    if severity == "minor":
        return _min_confidence(base_confidence, "medium")
    if severity == "moderate":
        if _con == "low":
            return _min_confidence(base_confidence, "medium")
        else:
            return _min_confidence(base_confidence, "low")
    if severity == "severe":
        return "low"
    return base_confidence


def derive_review_priority_distance_signal(severity: str, consequence: str) -> dict:
    """Derive review priority escalation signal from severity × consequence matrix.

    Args:
        severity:    "none" | "minor" | "moderate" | "severe"
        consequence: "low" | "medium" | "moderate" | "high" — Stage 5e materiality

    Returns:
        {
            "escalated": bool,
            "hard_flag": bool,
            "reason": str | None
        }
    """
    _con = "moderate" if consequence in ("medium", "moderate") else consequence
    no_change = {"escalated": False, "hard_flag": False, "reason": None}

    if severity in ("none", "minor", "not_assessed"):
        return no_change
    if severity == "moderate":
        if _con == "low":
            return no_change
        if _con == "moderate":
            return {
                "escalated": True,
                "hard_flag": False,
                "reason": f"Moderate disagreement severity combined with {consequence} consequence — soft escalation",
            }
        # high
        return {
            "escalated": True,
            "hard_flag": False,
            "reason": f"Moderate disagreement severity (inference confidence gap) combined with high consequence — escalated one level",
        }
    if severity == "severe":
        if _con == "low":
            return {
                "escalated": True,
                "hard_flag": False,
                "reason": "Severe disagreement (epistemic conflict) — escalated one level despite low consequence",
            }
        if _con == "moderate":
            return {
                "escalated": True,
                "hard_flag": True,
                "reason": "Severe disagreement (epistemic conflict) combined with moderate consequence — escalated and flagged",
            }
        # high
        return {
            "escalated": True,
            "hard_flag": True,
            "reason": "Severe disagreement (epistemic conflict) combined with high consequence — hard flag, review required regardless of vote count",
        }
    return no_change


def derive_per_evaluator_lp_verdict(element_verdicts_for_evaluator: list) -> str:
    """Derive a single LP-level verdict for one evaluator from their element verdicts.

    Takes the plurality verdict; on tie, picks the more pessimistic (higher rank)
    verdict. Returns "unclear" if the list is empty.
    """
    if not element_verdicts_for_evaluator:
        return "unclear"
    counts = Counter(element_verdicts_for_evaluator)
    max_count = max(counts.values())
    candidates = [v for v, c in counts.items() if c == max_count]
    if len(candidates) == 1:
        return candidates[0]
    # Tie-break: most pessimistic (highest rank on ladder)
    # "missing" (5) > "unclear" (3) > presence verdicts
    best = candidates[0]
    best_rank = VERDICT_RANK.get(best, 3)
    for v in candidates[1:]:
        r = VERDICT_RANK.get(v, 3)
        if r > best_rank:
            best = v
            best_rank = r
    return best
