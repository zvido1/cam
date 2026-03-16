#!/usr/bin/env python3
"""
CAM Core Rule Library v1.1

Domain-agnostic epistemic guards that apply to ALL question types.
These rules govern when assertions are epistemically unsafe regardless of domain.

Originally developed from Biology domain analysis but applicable universally.
Renamed from biology_rule_library.py to reflect domain-agnostic nature.

These rules:
- MAY downgrade HARD → SOFT kills
- MAY cap ladder levels  
- MAY prevent over-assertion
- MAY NOT introduce new eliminations
- MAY NOT force answer selection
- MAY NOT override break analysis

Rule evaluation is performed AFTER kill shot validation but BEFORE ladder determination.

Version History:
- v1.0: Initial implementation as biology_rule_library.py
- v1.1: Renamed to core_rule_library.py, clarified domain-agnostic nature
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


# Module status for logging
CORE_RULES_STATUS = "PERMANENTLY_ENABLED"


class RuleEffect(Enum):
    """Effects that rules can have"""
    DOWNGRADE_HARD_TO_SOFT = "downgrade_hard_to_soft"
    CAP_LADDER_LEVEL = "cap_ladder_level"
    MARK_FRAGILE = "mark_fragile"
    PROHIBIT_ASSERTION_LEVEL = "prohibit_assertion_level"
    INVALIDATE_ELIMINATION = "invalidate_elimination"
    NO_EFFECT = "no_effect"


@dataclass
class RuleResult:
    """Result of applying a single rule"""
    rule_id: str
    triggered: bool
    effect: RuleEffect
    description: str
    affected_kills: List[str] = field(default_factory=list)  # Options whose kills were affected
    ladder_cap: Optional[int] = None  # If effect is CAP_LADDER_LEVEL
    fragility_note: Optional[str] = None


@dataclass 
class RuleLibraryResult:
    """Aggregate result of applying all rules"""
    rules_evaluated: int
    rules_triggered: int
    rule_results: List[RuleResult]
    downgraded_kills: Dict[str, str]  # {option: reason}
    ladder_cap: Optional[int]  # Minimum level that can be asserted
    fragility_markers: List[str]
    prohibitions: List[str]  # List of prohibited actions


# =============================================================================
# Rule Detection Functions
# =============================================================================

def detect_proxy_indicators(kill_proof: str, kill_type: str) -> bool:
    """
    CORE-001: Detect if argument relies on proxy indicators rather than forced causality.
    
    Proxy indicators include:
    - Correlation-based arguments
    - "Typically associated with" language
    - Indirect evidence chains
    - Statistical tendencies without mechanism
    """
    if not kill_proof:
        return False
    
    proof_lower = kill_proof.lower()
    
    proxy_markers = [
        "typically", "usually", "often", "commonly", "tends to",
        "associated with", "correlated with", "linked to",
        "suggests", "indicates", "implies", "points to",
        "in most cases", "generally", "frequently",
        "characteristic of", "consistent with", "compatible with",
        "similar to", "resembles", "like", "analogous to",
        "expected in", "observed in", "found in",
        "pattern suggests", "trend indicates"
    ]
    
    for marker in proxy_markers:
        if marker in proof_lower:
            return True
    
    return False


def detect_underdetermination(kill_shots: List[dict], survivor_conditions: dict) -> bool:
    """
    CORE-002: Detect if multiple hypotheses fit all given data.
    
    Triggered when:
    - Multiple surviving options have overlapping conditions
    - Kill shots rely on choosing between equally valid interpretations
    - No unique identification without additional constraints
    """
    if not survivor_conditions:
        return False
    
    # Check for overlapping conditions among survivors
    all_conditions = []
    for opt, data in survivor_conditions.items():
        conditions = data.get("conditions", [])
        all_conditions.extend(conditions)
    
    if len(all_conditions) < 2:
        return False
    
    # Look for "could be either" / "depends on interpretation" markers
    underdetermination_markers = [
        "could be", "might be", "either", "both possible",
        "depends on", "interpretation", "ambiguous",
        "cannot distinguish", "indistinguishable", 
        "multiple valid", "several possible", "alternative explanation"
    ]
    
    for cond in all_conditions:
        cond_lower = cond.lower() if cond else ""
        for marker in underdetermination_markers:
            if marker in cond_lower:
                return True
    
    return False


def detect_unstated_convention(kill_proof: str, kill_target: str) -> bool:
    """
    CORE-003: Detect if correctness depends on unstated conventions.
    
    Conventions include:
    - Naming conventions
    - Standard assumptions
    - Field-specific defaults
    - Implicit domain knowledge
    """
    combined = f"{kill_proof or ''} {kill_target or ''}".lower()
    
    convention_markers = [
        "convention", "by convention", "conventionally",
        "standard", "by standard", "standard practice",
        "typically named", "commonly called", "usually referred to",
        "assumes", "assuming", "under the assumption",
        "in this context", "in this field", "in biology",
        "in physics", "in chemistry",  # Added for domain-agnostic
        "nomenclature", "terminology", "by definition",
        "implicit", "implicitly", "understood to",
        "default", "by default", "unless stated"
    ]
    
    for marker in convention_markers:
        if marker in combined:
            return True
    
    return False


def detect_gold_correct_fragility(r3_fragility_count: int, is_gold_correct: bool) -> bool:
    """
    CORE-004: Detect gold-correct but fragile assertions.
    
    Triggered when:
    - Answer matches gold label
    - BUT R3 stress testing revealed fragility
    """
    return is_gold_correct and r3_fragility_count > 0


def detect_single_interpretation_kill(kill_proof: str, support_count: int) -> bool:
    """
    CORE-005: Detect kills that depend on a single interpretation.
    
    Kills that could be "escaped" under alternative readings should be downgraded.
    Single evaluator support is a strong indicator.
    """
    if support_count <= 1:
        return True
    
    if not kill_proof:
        return False
    
    proof_lower = kill_proof.lower()
    
    interpretation_markers = [
        "interpreting", "if we interpret", "under this interpretation",
        "reading", "if we read", "one way to read",
        "assuming", "if we assume", "under the assumption",
        "could also mean", "alternatively", "another view"
    ]
    
    for marker in interpretation_markers:
        if marker in proof_lower:
            return True
    
    return False


def detect_representation_ambiguity(round2a_result: dict) -> bool:
    """
    CORE-006: Detect unresolved representation ambiguity.
    
    Checks if Round 2a flagged mapping issues that weren't resolved.
    """
    if not round2a_result:
        return False
    
    # Check for representation issues
    mapping_ok = round2a_result.get("mapping_validation_ok", True)
    if not mapping_ok:
        return True
    
    # Check for specific representation flags
    representation_issues = round2a_result.get("representation_issues", [])
    if representation_issues:
        return True
    
    # Check for ambiguity markers in any messages
    messages = round2a_result.get("messages", [])
    for msg in messages:
        msg_lower = str(msg).lower()
        if "ambiguous" in msg_lower or "unclear" in msg_lower:
            return True
    
    return False


def detect_elimination_by_comparison(kill_proof: str, kill_type: str) -> bool:
    """
    CORE-007: Detect eliminations by comparison rather than contradiction.
    
    "Weakness ≠ falsity" - an answer being less likely than another
    is not grounds for elimination.
    """
    if not kill_proof:
        return False
    
    proof_lower = kill_proof.lower()
    
    comparison_markers = [
        "less likely", "more likely", "better fit",
        "worse fit", "compared to", "relative to",
        "weaker than", "stronger than", "preferable",
        "not as good", "not as strong", "inferior",
        "superior", "ranks lower", "ranks higher",
        "less plausible", "more plausible",
        "less probable", "more probable"
    ]
    
    for marker in comparison_markers:
        if marker in proof_lower:
            return True
    
    return False


# =============================================================================
# Main Rule Application Function
# =============================================================================

def apply_core_rules(
    kill_aggregation: dict,
    survivor_conditions: dict,
    round2a_result: dict = None,
    r3_results: dict = None,
    gold_answer: str = None,
    final_answer: str = None,
    ladder_level: int = None,
) -> RuleLibraryResult:
    """
    Apply all Core epistemic rules to the evaluation results.
    
    These rules are domain-agnostic and apply to ALL question types.
    
    This function is called AFTER kill shot aggregation but BEFORE
    final ladder determination to allow rules to modify the process.
    
    Args:
        kill_aggregation: Output from aggregate_kill_shots()
        survivor_conditions: Conditions attached to surviving options
        round2a_result: Results from representation check (optional)
        r3_results: Results from stress testing (optional)
        gold_answer: The gold-standard correct answer (optional)
        final_answer: The system's final answer (optional)
        ladder_level: The pre-rule ladder level (optional)
    
    Returns:
        RuleLibraryResult with all rule effects
    """
    rule_results = []
    downgraded_kills = {}
    ladder_cap = None
    fragility_markers = []
    prohibitions = []
    
    confirmed_kills = kill_aggregation.get("confirmed_kills", [])
    attempted_kills = kill_aggregation.get("attempted_kills", [])
    soft_conditions = kill_aggregation.get("soft_conditions", [])
    survivors = kill_aggregation.get("survivors", [])
    
    # Compute R3 fragility count
    r3_fragility_count = 0
    if r3_results:
        fragility_signals = r3_results.get("fragility_signals", [])
        r3_fragility_count = len(fragility_signals)
    
    is_gold_correct = (final_answer == gold_answer) if gold_answer and final_answer else False
    
    # =================================================================
    # CORE-001: Proxy Misuse Guard
    # =================================================================
    rule001_triggered = False
    rule001_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        kill_type = kill.get("kill_type", "")
        option = kill.get("option", "")
        
        if detect_proxy_indicators(kill_proof, kill_type):
            rule001_triggered = True
            rule001_affected.append(option)
            downgraded_kills[option] = "CORE-001: Kill relies on proxy indicators"
    
    rule_results.append(RuleResult(
        rule_id="CORE-001",
        triggered=rule001_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule001_triggered else RuleEffect.NO_EFFECT,
        description="Proxy Misuse Guard: Argument relies on proxy indicators rather than forced causality",
        affected_kills=rule001_affected,
        fragility_note="Proxies admit alternative explanations" if rule001_triggered else None
    ))
    
    # =================================================================
    # CORE-002: Underdetermination Guard
    # =================================================================
    rule002_triggered = detect_underdetermination(confirmed_kills, survivor_conditions)
    
    if rule002_triggered:
        # Prohibit HARD kills, cap ladder at L3
        ladder_cap = max(ladder_cap or 0, 3)
        prohibitions.append("CORE-002: Prohibit HARD kills due to underdetermination")
    
    rule_results.append(RuleResult(
        rule_id="CORE-002",
        triggered=rule002_triggered,
        effect=RuleEffect.CAP_LADDER_LEVEL if rule002_triggered else RuleEffect.NO_EFFECT,
        description="Underdetermination Guard: Multiple hypotheses fit all given data",
        ladder_cap=3 if rule002_triggered else None,
        fragility_note="No unique identification without constraints" if rule002_triggered else None
    ))
    
    # =================================================================
    # CORE-003: Unstated Convention Flag
    # =================================================================
    rule003_triggered = False
    rule003_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        kill_target = kill.get("kill_target", "")
        option = kill.get("option", "")
        
        if detect_unstated_convention(kill_proof, kill_target):
            rule003_triggered = True
            rule003_affected.append(option)
            fragility_markers.append(f"Option {option}: correctness depends on unstated convention")
    
    if rule003_triggered:
        prohibitions.append("CORE-003: Prohibit L0 (convention ≠ logical necessity)")
        ladder_cap = max(ladder_cap or 0, 1)  # At minimum L1
    
    rule_results.append(RuleResult(
        rule_id="CORE-003",
        triggered=rule003_triggered,
        effect=RuleEffect.MARK_FRAGILE if rule003_triggered else RuleEffect.NO_EFFECT,
        description="Unstated Convention Flag: Correctness depends on unstated conventions",
        affected_kills=rule003_affected,
        ladder_cap=1 if rule003_triggered else None,
        fragility_note="Convention ≠ logical necessity" if rule003_triggered else None
    ))
    
    # =================================================================
    # CORE-004: Assertion Licensing
    # =================================================================
    rule004_triggered = detect_gold_correct_fragility(r3_fragility_count, is_gold_correct)
    
    if rule004_triggered:
        # ASSERT_QUALIFIED only - prohibit full assertion
        prohibitions.append("CORE-004: Gold-correct but fragile - ASSERT_QUALIFIED only")
        ladder_cap = max(ladder_cap or 0, 1)  # Force at least L1
        fragility_markers.append("Correctness does not license certainty")
    
    rule_results.append(RuleResult(
        rule_id="CORE-004",
        triggered=rule004_triggered,
        effect=RuleEffect.PROHIBIT_ASSERTION_LEVEL if rule004_triggered else RuleEffect.NO_EFFECT,
        description="Assertion Licensing: Gold-correct but R3 fragility exists",
        ladder_cap=1 if rule004_triggered else None,
        fragility_note="Correctness does not license certainty" if rule004_triggered else None
    ))
    
    # =================================================================
    # CORE-005: Overkill Suppression
    # =================================================================
    rule005_triggered = False
    rule005_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        support_count = kill.get("valid_support_count", 0)
        option = kill.get("option", "")
        
        if detect_single_interpretation_kill(kill_proof, support_count):
            rule005_triggered = True
            rule005_affected.append(option)
            downgraded_kills[option] = "CORE-005: Kill depends on single interpretation"
    
    rule_results.append(RuleResult(
        rule_id="CORE-005",
        triggered=rule005_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule005_triggered else RuleEffect.NO_EFFECT,
        description="Overkill Suppression: Kill depends on single interpretation",
        affected_kills=rule005_affected,
        fragility_note="Escapable kills are not definitive" if rule005_triggered else None
    ))
    
    # =================================================================
    # CORE-006: Representation Priority
    # =================================================================
    rule006_triggered = detect_representation_ambiguity(round2a_result)
    
    if rule006_triggered:
        # Block HARD kills downstream
        prohibitions.append("CORE-006: Block HARD kills - representation ambiguity unresolved")
        fragility_markers.append("Prevent garbage-in elimination")
        # Downgrade ALL confirmed kills if representation is ambiguous
        for kill in confirmed_kills:
            option = kill.get("option", "")
            if option not in downgraded_kills:
                downgraded_kills[option] = "CORE-006: Representation ambiguity blocks HARD kills"
    
    rule_results.append(RuleResult(
        rule_id="CORE-006",
        triggered=rule006_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule006_triggered else RuleEffect.NO_EFFECT,
        description="Representation Priority: Representation ambiguity unresolved",
        affected_kills=list(downgraded_kills.keys()) if rule006_triggered else [],
        fragility_note="Prevent garbage-in elimination" if rule006_triggered else None
    ))
    
    # =================================================================
    # CORE-007: Forced Elimination Guard
    # =================================================================
    rule007_triggered = False
    rule007_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        kill_type = kill.get("kill_type", "")
        option = kill.get("option", "")
        
        if detect_elimination_by_comparison(kill_proof, kill_type):
            rule007_triggered = True
            rule007_affected.append(option)
            downgraded_kills[option] = "CORE-007: Elimination by comparison, not contradiction"
    
    rule_results.append(RuleResult(
        rule_id="CORE-007",
        triggered=rule007_triggered,
        effect=RuleEffect.INVALIDATE_ELIMINATION if rule007_triggered else RuleEffect.NO_EFFECT,
        description="Forced Elimination Guard: Elimination by comparison, not contradiction",
        affected_kills=rule007_affected,
        fragility_note="Weakness ≠ falsity" if rule007_triggered else None
    ))
    
    # =================================================================
    # Aggregate Results
    # =================================================================
    rules_triggered = sum(1 for r in rule_results if r.triggered)
    
    return RuleLibraryResult(
        rules_evaluated=len(rule_results),
        rules_triggered=rules_triggered,
        rule_results=rule_results,
        downgraded_kills=downgraded_kills,
        ladder_cap=ladder_cap,
        fragility_markers=fragility_markers,
        prohibitions=prohibitions
    )


def apply_rule_effects_to_aggregation(
    kill_aggregation: dict,
    rule_result: RuleLibraryResult
) -> dict:
    """
    Apply rule effects to modify kill aggregation.
    
    This creates a MODIFIED version of kill_aggregation where:
    - Downgraded kills are moved from confirmed_kills to soft_conditions
    - Survivors list is updated to include resurrected options
    
    Returns a NEW dict (does not mutate input).
    """
    modified = {
        "kills_by_option": dict(kill_aggregation.get("kills_by_option", {})),
        "valid_kills_by_option": dict(kill_aggregation.get("valid_kills_by_option", {})),
        "invalid_kills_by_option": dict(kill_aggregation.get("invalid_kills_by_option", {})),
        "confirmed_kills": list(kill_aggregation.get("confirmed_kills", [])),
        "attempted_kills": list(kill_aggregation.get("attempted_kills", [])),
        "soft_conditions": list(kill_aggregation.get("soft_conditions", [])),
        "survivors": list(kill_aggregation.get("survivors", [])),
        "prior_eliminations": list(kill_aggregation.get("prior_eliminations", [])),
        "kill_consensus": dict(kill_aggregation.get("kill_consensus", {})),
        "valid_kill_consensus": dict(kill_aggregation.get("valid_kill_consensus", {})),
        "requires_resurrection": kill_aggregation.get("requires_resurrection", False),
        "resurrection_reason": kill_aggregation.get("resurrection_reason", ""),
        "excluded_evaluators": list(kill_aggregation.get("excluded_evaluators", [])),
        "included_evaluators": list(kill_aggregation.get("included_evaluators", [])),
        # NEW: Track rule library effects
        "rule_library_applied": True,
        "rule_library_result": {
            "rules_evaluated": rule_result.rules_evaluated,
            "rules_triggered": rule_result.rules_triggered,
            "downgraded_kills": rule_result.downgraded_kills,
            "ladder_cap": rule_result.ladder_cap,
            "fragility_markers": rule_result.fragility_markers,
            "prohibitions": rule_result.prohibitions,
        }
    }
    
    # Move downgraded kills from confirmed to soft_conditions
    downgraded_options = set(rule_result.downgraded_kills.keys())
    
    new_confirmed = []
    for kill in modified["confirmed_kills"]:
        option = kill.get("option", "")
        if option in downgraded_options:
            # Downgrade: move to soft_conditions
            kill_copy = dict(kill)
            kill_copy["status"] = "soft_condition"
            kill_copy["downgrade_reason"] = rule_result.downgraded_kills[option]
            modified["soft_conditions"].append(kill_copy)
            
            # Add option back to survivors if it was killed
            if option not in modified["survivors"]:
                modified["survivors"].append(option)
                modified["survivors"].sort()
        else:
            new_confirmed.append(kill)
    
    modified["confirmed_kills"] = new_confirmed
    modified["confirmed_killed_count"] = len(new_confirmed)
    modified["survivor_count"] = len(modified["survivors"])
    
    return modified


# =============================================================================
# Backward Compatibility Aliases
# =============================================================================
# These aliases allow existing code to continue working during transition

def apply_biology_rules(*args, **kwargs):
    """Backward compatibility alias for apply_core_rules."""
    return apply_core_rules(*args, **kwargs)


def is_rule_library_enabled() -> bool:
    """Check if rule library should be applied."""
    return True  # Always enabled when this module is imported


def get_rule_library_version() -> str:
    """Return the version of the rule library."""
    return "v1.1-core"


def get_core_rule_library_version() -> str:
    """Return the version of the core rule library."""
    return "v1.1-core"


def get_rule_descriptions() -> Dict[str, str]:
    """Return human-readable descriptions of all rules."""
    return {
        "CORE-001": "Proxy Misuse Guard: Downgrade HARD→SOFT when argument relies on proxy indicators",
        "CORE-002": "Underdetermination Guard: Cap ladder at L3 when multiple hypotheses fit data",
        "CORE-003": "Unstated Convention Flag: Mark fragile when correctness depends on conventions",
        "CORE-004": "Assertion Licensing: Force ASSERT_QUALIFIED when gold-correct but fragile",
        "CORE-005": "Overkill Suppression: Downgrade kills that depend on single interpretation",
        "CORE-006": "Representation Priority: Block HARD kills when representation is ambiguous",
        "CORE-007": "Forced Elimination Guard: Invalidate eliminations by comparison (weakness≠falsity)",
    }


if __name__ == "__main__":
    # Test the module
    print(f"Core Rule Library {get_core_rule_library_version()}")
    print(f"Status: {CORE_RULES_STATUS}")
    print("\nRules implemented (domain-agnostic):")
    for rule_id, desc in get_rule_descriptions().items():
        print(f"  {rule_id}: {desc}")
