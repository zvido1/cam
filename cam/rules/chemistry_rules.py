#!/usr/bin/env python3
"""
CAM Chemistry Rule Library v1.1

Implementation of the 5 Chemistry-derived rules from Chemistry_RuleCards_v1.1.docx

These rules:
- MAY downgrade HARD → SOFT kills
- MAY cap ladder levels  
- MAY mark fragility
- MAY NOT introduce new eliminations
- MAY NOT force answer selection
- MAY NOT inflate confidence

IMPORTANT: These rules do not encode chemistry knowledge.
They encode when chemistry reasoning is epistemically unsafe.
They exist to prevent false certainty, not to improve raw preference accuracy.

Rule evaluation is performed AFTER Biology rules and AFTER Physics rules.
Chemistry rules are FROZEN CANDIDATE (pending pilot validation).
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class RuleEffect(Enum):
    """Effects that rules can have"""
    DOWNGRADE_HARD_TO_SOFT = "downgrade_hard_to_soft"
    CAP_LADDER_LEVEL = "cap_ladder_level"
    MARK_FRAGILE = "mark_fragile"
    PROHIBIT_ASSERTION_LEVEL = "prohibit_assertion_level"
    BLOCK_HARD_KILLS = "block_hard_kills"
    NO_EFFECT = "no_effect"


@dataclass
class RuleResult:
    """Result of applying a single rule"""
    rule_id: str
    triggered: bool
    effect: RuleEffect
    description: str
    affected_kills: List[str] = field(default_factory=list)
    ladder_cap: Optional[int] = None
    fragility_note: Optional[str] = None


@dataclass 
class RuleLibraryResult:
    """Aggregate result of applying all rules"""
    rules_evaluated: int
    rules_triggered: int
    rule_results: List[RuleResult]
    downgraded_kills: Dict[str, str]  # {option: reason}
    ladder_cap: Optional[int]  # Maximum level that can be asserted
    fragility_markers: List[str]
    prohibitions: List[str]


# =============================================================================
# Chemistry Rule Detection Functions
# =============================================================================

def detect_stereochemistry_assignment_uncertainty(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-CHEM-001: Stereochemistry Assignment Uncertainty
    
    Triggers when:
    - Kill proof references R/S, E/Z, endo/exo, or stereodescriptors
    - WITHOUT explicitly tracing stereochemical fate through each reaction step
    
    This fires on unsupported stereochemical certainty, not mere disagreement.
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    
    # Stereodescriptor markers - FIXED v1.2: avoid false positives on lowercase 's'
    # Only match:
    #   - (R), (S), (R,S), etc. in parentheses
    #   - Uppercase R/S standalone (rare but valid)
    #   - E/Z descriptors
    #   - Named stereochemistry terms
    stereodescriptor_markers = [
        r"\([RSrs]\)",  # (R), (S) - parenthesized descriptors
        r"\([RSrs],[RSrs]\)",  # (R,R), (S,S), (R,S), (S,R)
        r"\b[RS]/[RS]\b",  # R/S paired notation
        r"\b[RS]-config",  # R-configuration, S-configuration
        r"[ezEZ]-\w+",  # E-alkene, Z-alkene
        r"\([ezEZ]\)",  # (E), (Z)
        "endo", "exo",
        "cis", "trans",
        "axial", "equatorial",
        "re face", "si face",
        "pro-r", "pro-s",
        "erythro", "threo",
        r"\bsyn\b", r"\banti\b",  # word boundaries to avoid 'synthesis', 'antibiotic'
        "meso",
        r"\bd-", r"\bl-",  # d- and l- prefixes
        "dextrorotatory", "levorotatory",
        "optical isomer", "stereoisomer", "enantiomer", "diastereomer",
        "stereocenter", "chiral center", "asymmetric carbon",
        "cip priority", "cahn-ingold-prelog",
    ]
    
    has_stereodescriptor = False
    for marker in stereodescriptor_markers:
        if re.search(marker, proof_lower):
            has_stereodescriptor = True
            break
    
    if not has_stereodescriptor:
        return False, None
    
    # Explicit step-by-step tracing markers
    explicit_tracing_markers = [
        "step 1", "step 2", "step 3",
        "first step", "second step", "third step",
        "inversion occurs at", "retention occurs at",
        "stereochemistry is preserved", "stereochemistry is inverted",
        "walden inversion", "backside attack",
        "front side attack", "frontside attack",
        "retention of configuration", "inversion of configuration",
        "at this step", "in this step",
        "tracking the stereochemistry",
        "following the stereochemistry",
        "each transformation",
    ]
    
    has_explicit_tracing = any(marker in proof_lower for marker in explicit_tracing_markers)
    
    if has_stereodescriptor and not has_explicit_tracing:
        return True, "Kill proof references stereodescriptors without explicit step-by-step stereochemical tracing"
    
    return False, None


def detect_nmr_coupling_pattern_unjustified(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-CHEM-002: NMR Coupling Pattern Validation
    
    Triggers when:
    - Kill proof relies solely on qualitative multiplicity labels (triplet, doublet, etc.)
    - WITHOUT explaining proton equivalence classes or molecular symmetry
    
    This is PROBATIONARY - monitor for over-firing.
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    
    # NMR multiplicity labels
    multiplicity_markers = [
        "singlet", "doublet", "triplet", "quartet", "quintet", "sextet", "septet",
        "multiplet", "broad singlet", "broad peak",
        "doublet of doublets", "dd", "dt", "dq",
        "triplet of doublets", "td",
        "splitting pattern", "coupling pattern",
        "j coupling", "j =", "j=", "coupling constant",
    ]
    
    has_multiplicity = any(marker in proof_lower for marker in multiplicity_markers)
    
    if not has_multiplicity:
        return False, None
    
    # Structural explanation markers
    structural_explanation_markers = [
        "equivalent protons", "equivalent hydrogens", "equivalence",
        "neighboring protons", "adjacent protons", "vicinal",
        "symmetry", "symmetric", "asymmetric",
        "c2 axis", "c2v", "cs", "mirror plane",
        "chemically equivalent", "magnetically equivalent",
        "homotopic", "enantiotopic", "diastereotopic",
        "proton environment", "chemical environment",
        "because the", "since the", "due to the",
        "n+1 rule", "pascal's triangle",
        "two neighboring", "three neighboring",
    ]
    
    has_structural_explanation = any(marker in proof_lower for marker in structural_explanation_markers)
    
    if has_multiplicity and not has_structural_explanation:
        return True, "Kill relies on NMR multiplicity labels without explaining proton equivalence or molecular symmetry"
    
    return False, None


def detect_multistep_synthesis_carbon_accounting(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-CHEM-003: Multi-Step Synthesis Carbon Accounting
    
    Triggers when:
    - Question involves multi-step synthesis (>3 steps)
    - Answer options involve counting atoms/groups in final product
    - Intermediate structures not explicitly provided
    
    This fires on count-based eliminations without explicit atom tracking.
    """
    combined = f"{kill_proof or ''} {question_text or ''}".lower()
    
    # Multi-step synthesis indicators
    multistep_markers = [
        "step", "steps", "reaction sequence", "synthesis", "synthetic route",
        "followed by", "then treated with", "subsequently",
        "first", "second", "third", "fourth", "final",
        "intermediate", "product", "starting material",
        "workup", "purification",
        "reflux", "heat", "room temperature", "rt",
    ]
    
    # Counting indicators
    counting_markers = [
        "count", "counting", "number of",
        "how many", "contains",
        "carbon atoms", "carbons", "ch2", "ch3", "ch",
        "hydrogen atoms", "hydrogens", "h atoms",
        "degree of unsaturation", "dbe", "ihu",
        "molecular formula", "formula",
        "functional groups",
    ]
    
    has_multistep = sum(1 for marker in multistep_markers if marker in combined) >= 3
    has_counting = any(marker in combined for marker in counting_markers)
    
    if not (has_multistep and has_counting):
        return False, None
    
    # Explicit tracking markers
    explicit_tracking_markers = [
        "tracking", "following the carbons", "atom by atom",
        "carbon 1", "carbon 2", "c1", "c2", "c3", "c4",
        "numbering", "labeled", "isotope label",
        "from the starting material", "in the product",
        "this carbon becomes", "these carbons become",
    ]
    
    has_explicit_tracking = any(marker in combined for marker in explicit_tracking_markers)
    
    if has_multistep and has_counting and not has_explicit_tracking:
        return True, "Multi-step synthesis with counting-based reasoning but no explicit atom-by-atom tracking"
    
    return False, None


def detect_symmetry_point_group_uncertainty(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-CHEM-004: Molecular Symmetry Point Group Uncertainty
    
    Triggers when:
    - Kill proof asserts point group assignment for a molecule with conformational flexibility
    - WITHOUT addressing whether claimed symmetry applies to actual vs idealized structure
    
    This rule does NOT apply when the molecule is rigid or symmetry is definitional.
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    question_lower = (question_text or "").lower()
    combined = f"{proof_lower} {question_lower}"
    
    # Point group markers
    point_group_markers = [
        "c1", "cs", "ci", "c2", "c3", "c4", "c5", "c6",
        "c2v", "c3v", "c4v", "c5v", "c6v",
        "c2h", "c3h", "c4h", "c5h", "c6h",
        "d2", "d3", "d4", "d5", "d6",
        "d2h", "d3h", "d4h", "d5h", "d6h",
        "d2d", "d3d", "d4d", "d5d", "d6d",
        "s2", "s4", "s6", "s8",
        "td", "oh", "ih", "kh",
        "point group", "symmetry point group",
        "symmetry element", "symmetry operation",
    ]
    
    has_point_group = any(marker in combined for marker in point_group_markers)
    
    if not has_point_group:
        return False, None
    
    # Conformational flexibility markers
    flexibility_markers = [
        "rotatable", "rotation about", "free rotation",
        "conformer", "conformation", "conformational",
        "gauche", "anti", "eclipsed", "staggered",
        "ring flip", "chair", "boat", "twist-boat",
        "axial", "equatorial",
        "flexible", "floppy",
        "barrier to rotation", "rotational barrier",
        "dihedral", "torsion", "torsional",
    ]
    
    # Rigid molecule markers - if present, rule does NOT fire
    rigid_markers = [
        "benzene", "naphthalene", "anthracene", "phenyl",
        "planar", "rigid", "locked",
        "aromatic ring", "fused ring",
        "adamantane", "cubane", "buckminster", "fullerene",
        "by definition", "definitionally",
    ]
    
    has_flexibility = any(marker in combined for marker in flexibility_markers)
    is_rigid = any(marker in combined for marker in rigid_markers)
    
    if is_rigid:
        return False, None  # Rule does not apply to rigid molecules
    
    # Conformer-addressing markers
    conformer_addressed_markers = [
        "in this conformer", "for this conformer",
        "equilibrium geometry", "optimized geometry",
        "idealized", "ideal geometry",
        "actual structure", "actual geometry",
        "average symmetry", "effective symmetry",
        "instantaneous symmetry", "time-averaged",
    ]
    
    has_conformer_addressed = any(marker in combined for marker in conformer_addressed_markers)
    
    if has_point_group and has_flexibility and not has_conformer_addressed:
        return True, "Point group assignment for flexible molecule without addressing actual vs idealized structure"
    
    return False, None


def detect_competing_mechanism_selectivity(kill_proof: str, round2_context: dict = None) -> Tuple[bool, Optional[str]]:
    """
    RULE-CHEM-005: Competing Mechanism Selectivity (CRITICAL)
    
    Triggers when:
    - Kill proof cites a specific reaction mechanism
    - Reasoning artifacts show models citing different plausible mechanisms for same transformation
    
    This is the HIGHEST PRIORITY Chemistry rule - triggered by unanimous wrong case.
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    
    # Competing mechanism pairs
    mechanism_pairs = [
        (["sn1", "unimolecular nucleophilic substitution", "carbocation intermediate"],
         ["sn2", "bimolecular nucleophilic substitution", "backside attack", "concerted"]),
        (["e1", "unimolecular elimination", "carbocation"],
         ["e2", "bimolecular elimination", "concerted elimination", "anti-periplanar"]),
        (["sn1", "e1"],
         ["sn2", "e2"]),
        (["radical", "homolytic", "free radical"],
         ["ionic", "heterolytic", "polar"]),
        (["kinetic control", "kinetic product", "faster"],
         ["thermodynamic control", "thermodynamic product", "more stable"]),
        (["1,2-addition", "direct addition", "1,2-adduct"],
         ["1,4-addition", "conjugate addition", "michael addition", "1,4-adduct"]),
        (["markovnikov", "markovnikov's rule", "markovnikov product"],
         ["anti-markovnikov", "anti-markovnikov product", "peroxide effect"]),
        (["endo", "endo selectivity", "endo product"],
         ["exo", "exo selectivity", "exo product"]),
        (["syn addition", "syn-addition", "cis addition"],
         ["anti addition", "anti-addition", "trans addition"]),
    ]
    
    # Check if proof mentions one mechanism from any pair
    proof_mechanisms = set()
    for pair_a, pair_b in mechanism_pairs:
        for marker in pair_a:
            if marker in proof_lower:
                proof_mechanisms.add(f"pair_a:{marker}")
        for marker in pair_b:
            if marker in proof_lower:
                proof_mechanisms.add(f"pair_b:{marker}")
    
    if not proof_mechanisms:
        return False, None
    
    # Check round2 context for conflicting mechanisms
    conflicting_mechanisms = False
    if round2_context:
        # Look for evidence of models citing different mechanisms
        evaluator_mechanisms = round2_context.get("evaluator_mechanisms", {})
        shared_assumptions = round2_context.get("shared_assumptions", [])
        incompatible_assumptions = round2_context.get("incompatible_assumptions", [])
        
        # Check shared assumptions for mechanism divergence
        shared_str = " ".join(str(s) for s in shared_assumptions).lower()
        incompatible_str = " ".join(str(s) for s in incompatible_assumptions).lower()
        
        for pair_a, pair_b in mechanism_pairs:
            a_in_shared = any(m in shared_str or m in incompatible_str for m in pair_a)
            b_in_shared = any(m in shared_str or m in incompatible_str for m in pair_b)
            if a_in_shared and b_in_shared:
                conflicting_mechanisms = True
                break
    
    # Explicit substrate/conditions analysis markers
    substrate_analysis_markers = [
        "substrate is", "substrate has", "substrate structure",
        "primary", "secondary", "tertiary", "quaternary",
        "steric hindrance", "steric bulk", "sterically",
        "solvent is", "in this solvent", "solvent polarity",
        "polar aprotic", "polar protic", "nonpolar",
        "nucleophile strength", "strong nucleophile", "weak nucleophile",
        "leaving group", "good leaving group", "poor leaving group",
        "temperature favors", "at this temperature",
        "because the conditions", "given these conditions",
    ]
    
    has_substrate_analysis = any(marker in proof_lower for marker in substrate_analysis_markers)
    
    # Trigger if mechanism cited but not justified by substrate/conditions analysis
    if proof_mechanisms and not has_substrate_analysis:
        return True, "Kill proof cites mechanism without explicit substrate/conditions analysis to justify mechanism selection"
    
    # Also trigger if we detect conflicting mechanisms in context
    if conflicting_mechanisms:
        return True, "Models cited competing mechanisms for the same transformation"
    
    return False, None


# =============================================================================
# Main Rule Application Function
# =============================================================================

def apply_chemistry_rules(
    kill_aggregation: dict,
    survivor_conditions: dict,
    question_text: str = "",
    round2a_result: dict = None,
    round2c_result: dict = None,
    ladder_level: int = None,
) -> RuleLibraryResult:
    """
    Apply all Chemistry rules to the evaluation results.
    
    Chemistry rules run AFTER Biology and Physics rules. Stricter constraint wins.
    
    Args:
        kill_aggregation: Output from aggregate_kill_shots()
        survivor_conditions: Conditions attached to surviving options
        question_text: The original question text
        round2a_result: Results from representation check (optional)
        round2c_result: Results from Round 2c (for mechanism context)
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
    
    # Build round2 context for mechanism detection
    round2_context = {}
    if round2c_result:
        round2_context["shared_assumptions"] = round2c_result.get("shared_assumptions", [])
        round2_context["incompatible_assumptions"] = round2c_result.get("incompatible_assumptions", [])
    
    # =================================================================
    # RULE-CHEM-001: Stereochemistry Assignment Uncertainty
    # =================================================================
    rule_chem001_triggered = False
    rule_chem001_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "") if isinstance(kill, dict) else ""
        option = kill.get("option", "") if isinstance(kill, dict) else kill
        
        triggered, reason = detect_stereochemistry_assignment_uncertainty(kill_proof, question_text)
        if triggered:
            rule_chem001_triggered = True
            rule_chem001_affected.append(option)
            downgraded_kills[option] = f"RULE-CHEM-001: {reason}"
            fragility_markers.append(f"stereochemistry_assignment_uncertain:{option}")
    
    if rule_chem001_triggered:
        # Cap at L3 (partial elimination)
        if ladder_cap is None or ladder_cap > 3:
            ladder_cap = 3
    
    rule_results.append(RuleResult(
        rule_id="RULE-CHEM-001",
        triggered=rule_chem001_triggered,
        effect=RuleEffect.CAP_LADDER_LEVEL if rule_chem001_triggered else RuleEffect.NO_EFFECT,
        description="Stereochemistry Assignment Uncertainty: Kill references stereodescriptors without explicit tracing",
        affected_kills=rule_chem001_affected,
        ladder_cap=3 if rule_chem001_triggered else None,
        fragility_note="Stereochemical certainty requires explicit mechanism tracing" if rule_chem001_triggered else None
    ))
    
    # =================================================================
    # RULE-CHEM-002: NMR Coupling Pattern Validation (PROBATIONARY)
    # =================================================================
    rule_chem002_triggered = False
    rule_chem002_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "") if isinstance(kill, dict) else ""
        option = kill.get("option", "") if isinstance(kill, dict) else kill
        
        triggered, reason = detect_nmr_coupling_pattern_unjustified(kill_proof, question_text)
        if triggered:
            rule_chem002_triggered = True
            rule_chem002_affected.append(option)
            downgraded_kills[option] = f"RULE-CHEM-002: {reason}"
            fragility_markers.append(f"nmr_pattern_unjustified:{option}")
    
    # CHEM-002 is probationary - only downgrades to soft, no ladder cap
    rule_results.append(RuleResult(
        rule_id="RULE-CHEM-002",
        triggered=rule_chem002_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule_chem002_triggered else RuleEffect.NO_EFFECT,
        description="NMR Coupling Pattern Validation: Kill relies on multiplicity without structural explanation",
        affected_kills=rule_chem002_affected,
        fragility_note="Multiplicity labels alone insufficient - PROBATIONARY" if rule_chem002_triggered else None
    ))
    
    # =================================================================
    # RULE-CHEM-003: Multi-Step Synthesis Carbon Accounting
    # =================================================================
    rule_chem003_triggered = False
    rule_chem003_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "") if isinstance(kill, dict) else ""
        option = kill.get("option", "") if isinstance(kill, dict) else kill
        
        triggered, reason = detect_multistep_synthesis_carbon_accounting(kill_proof, question_text)
        if triggered:
            rule_chem003_triggered = True
            rule_chem003_affected.append(option)
            downgraded_kills[option] = f"RULE-CHEM-003: {reason}"
            fragility_markers.append(f"carbon_accounting_unverified:{option}")
    
    rule_results.append(RuleResult(
        rule_id="RULE-CHEM-003",
        triggered=rule_chem003_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule_chem003_triggered else RuleEffect.NO_EFFECT,
        description="Multi-Step Synthesis Carbon Accounting: Counting-based elimination without atom tracking",
        affected_kills=rule_chem003_affected,
        fragility_note="Multi-step atom tracking is error-prone" if rule_chem003_triggered else None
    ))
    
    # =================================================================
    # RULE-CHEM-004: Molecular Symmetry Point Group Uncertainty
    # =================================================================
    rule_chem004_triggered = False
    rule_chem004_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "") if isinstance(kill, dict) else ""
        option = kill.get("option", "") if isinstance(kill, dict) else kill
        
        triggered, reason = detect_symmetry_point_group_uncertainty(kill_proof, question_text)
        if triggered:
            rule_chem004_triggered = True
            rule_chem004_affected.append(option)
            downgraded_kills[option] = f"RULE-CHEM-004: {reason}"
            fragility_markers.append(f"symmetry_assignment_uncertain:{option}")
    
    rule_results.append(RuleResult(
        rule_id="RULE-CHEM-004",
        triggered=rule_chem004_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule_chem004_triggered else RuleEffect.NO_EFFECT,
        description="Molecular Symmetry Point Group Uncertainty: Flexible molecule without conformer analysis",
        affected_kills=rule_chem004_affected,
        fragility_note="Conformational flexibility changes effective symmetry" if rule_chem004_triggered else None
    ))
    
    # =================================================================
    # RULE-CHEM-005: Competing Mechanism Selectivity (CRITICAL)
    # =================================================================
    rule_chem005_triggered = False
    rule_chem005_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "") if isinstance(kill, dict) else ""
        option = kill.get("option", "") if isinstance(kill, dict) else kill
        
        triggered, reason = detect_competing_mechanism_selectivity(kill_proof, round2_context)
        if triggered:
            rule_chem005_triggered = True
            rule_chem005_affected.append(option)
            downgraded_kills[option] = f"RULE-CHEM-005: {reason}"
            fragility_markers.append(f"mechanism_selectivity_uncertain:{option}")
    
    if rule_chem005_triggered:
        # This is CRITICAL - cap at L3 and add prohibition
        if ladder_cap is None or ladder_cap > 3:
            ladder_cap = 3
        prohibitions.append("RULE-CHEM-005: Mechanism-based elimination without substrate/conditions justification")
    
    rule_results.append(RuleResult(
        rule_id="RULE-CHEM-005",
        triggered=rule_chem005_triggered,
        effect=RuleEffect.BLOCK_HARD_KILLS if rule_chem005_triggered else RuleEffect.NO_EFFECT,
        description="Competing Mechanism Selectivity: Mechanism cited without substrate/conditions analysis (CRITICAL)",
        affected_kills=rule_chem005_affected,
        ladder_cap=3 if rule_chem005_triggered else None,
        fragility_note="Mechanism selectivity depends on factors models cannot reliably evaluate" if rule_chem005_triggered else None
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
        # Track rule library effects
        "chemistry_rule_library_applied": True,
        "chemistry_rule_library_result": {
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
        if isinstance(kill, dict):
            option = kill.get("option", "")
        else:
            option = kill
            
        if option in downgraded_options:
            # Downgrade: move to soft_conditions
            if isinstance(kill, dict):
                kill_copy = dict(kill)
                kill_copy["status"] = "soft_condition"
                kill_copy["downgrade_reason"] = rule_result.downgraded_kills[option]
            else:
                kill_copy = {
                    "option": option,
                    "status": "soft_condition",
                    "downgrade_reason": rule_result.downgraded_kills[option]
                }
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
# Convenience Functions
# =============================================================================

def is_chemistry_rule_library_enabled() -> bool:
    """Check if chemistry rule library should be applied."""
    return True  # FROZEN CANDIDATE - enabled for pilot validation


def get_chemistry_rule_library_version() -> str:
    """Return the version of the chemistry rule library."""
    return "v1.1-chemistry-FROZEN_CANDIDATE"


def get_chemistry_rule_descriptions() -> Dict[str, str]:
    """Return human-readable descriptions of all chemistry rules."""
    return {
        "RULE-CHEM-001": "Stereochemistry Assignment Uncertainty: Downgrade when stereodescriptors cited without explicit step-by-step tracing; cap L3",
        "RULE-CHEM-002": "NMR Coupling Pattern Validation: Downgrade when multiplicity cited without structural explanation; PROBATIONARY",
        "RULE-CHEM-003": "Multi-Step Synthesis Carbon Accounting: Downgrade count-based eliminations without atom tracking",
        "RULE-CHEM-004": "Molecular Symmetry Point Group Uncertainty: Downgrade for flexible molecules without conformer analysis",
        "RULE-CHEM-005": "Competing Mechanism Selectivity: Block kills citing mechanism without substrate/conditions analysis; CRITICAL (unanimous wrong trigger)",
    }


# Status flag
CHEMISTRY_RULES_STATUS = "FROZEN_CANDIDATE"


if __name__ == "__main__":
    # Test the module
    print(f"Chemistry Rule Library {get_chemistry_rule_library_version()}")
    print(f"Status: {CHEMISTRY_RULES_STATUS}")
    print("\nRules implemented:")
    for rule_id, desc in get_chemistry_rule_descriptions().items():
        print(f"  {rule_id}: {desc}")
    
    # Test CHEM-005 (critical rule)
    print("\n" + "="*60)
    print("Testing CHEM-005 (Competing Mechanism Selectivity)...")
    
    test_proof = "The reaction proceeds via SN2 mechanism, leading to inversion at the stereocenter"
    triggered, reason = detect_competing_mechanism_selectivity(test_proof, {})
    print(f"Test proof: '{test_proof[:60]}...'")
    print(f"Triggered: {triggered}")
    print(f"Reason: {reason}")
    
    # Test with substrate analysis (should NOT trigger)
    test_proof_2 = "The substrate is primary with no steric hindrance, and the solvent is polar aprotic DMSO, strongly favoring SN2"
    triggered_2, reason_2 = detect_competing_mechanism_selectivity(test_proof_2, {})
    print(f"\nTest proof 2: '{test_proof_2[:60]}...'")
    print(f"Triggered: {triggered_2}")
    print(f"Reason: {reason_2}")
