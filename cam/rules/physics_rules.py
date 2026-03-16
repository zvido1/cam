#!/usr/bin/env python3
"""
CAM Physics Rule Library v1.3

Implementation of the 6 Physics-derived rules from CAM_Physics_RuleCards_v1_2.docx

These rules:
- MAY downgrade HARD → SOFT kills
- MAY cap ladder levels  
- MAY mark fragility
- MAY NOT introduce new eliminations
- MAY NOT force answer selection
- MAY NOT inflate confidence

IMPORTANT CLARIFICATION (v1.3):
These rules cap confidence under ambiguity. This does NOT prevent assertion by
decisive elimination if three alternatives are independently HARD-killed under
shared assumptions. The elimination-dominance path remains open.

Rule evaluation is performed AFTER Biology rules (stricter constraint wins).
Physics rules are OFF by default (pending validation).
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
    ladder_cap: Optional[int]  # Minimum level that can be asserted
    fragility_markers: List[str]
    prohibitions: List[str]


# =============================================================================
# Physics Rule Detection Functions
# =============================================================================

def detect_regime_violation(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-P001: Detect if elimination applies reasoning outside operational regime.
    
    Triggers when:
    - Non-relativistic formulas used for relativistic scenarios
    - Quantum effects ignored in quantum regime
    - Classical approximations in quantum contexts
    - Thermodynamic reasoning in non-equilibrium contexts
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    question_lower = (question_text or "").lower()
    
    # Regime mismatch patterns
    regime_conflicts = [
        # Relativistic vs non-relativistic
        (["relativistic", "lorentz", "gamma factor", "β = v/c", "time dilation", "length contraction"],
         ["newtonian", "classical mechanics", "v << c", "non-relativistic"]),
        # Quantum vs classical
        (["quantum", "wave function", "uncertainty principle", "planck", "ħ"],
         ["classical", "deterministic", "continuous spectrum"]),
        # Thermodynamic equilibrium
        (["equilibrium", "reversible", "quasi-static"],
         ["non-equilibrium", "irreversible", "far from equilibrium"]),
    ]
    
    # Check for explicit regime markers in proof that conflict with question context
    for regime_a, regime_b in regime_conflicts:
        proof_has_a = any(marker in proof_lower for marker in regime_a)
        proof_has_b = any(marker in proof_lower for marker in regime_b)
        question_has_a = any(marker in question_lower for marker in regime_a)
        question_has_b = any(marker in question_lower for marker in regime_b)
        
        # Conflict: proof uses regime A, question implies regime B
        if proof_has_a and question_has_b:
            return True, f"Proof uses {regime_a[0]} reasoning but question implies {regime_b[0]} context"
        if proof_has_b and question_has_a:
            return True, f"Proof uses {regime_b[0]} reasoning but question implies {regime_a[0]} context"
    
    # Explicit regime assumption markers
    regime_assumption_markers = [
        "assuming classical", "in the non-relativistic limit",
        "ignoring quantum effects", "treating classically",
        "in the newtonian regime", "for v << c",
        "assuming equilibrium", "at thermodynamic equilibrium"
    ]
    
    for marker in regime_assumption_markers:
        if marker in proof_lower:
            return True, f"Proof makes explicit regime assumption: '{marker}'"
    
    return False, None


def detect_math_physical_disconnect(kill_proof: str, kill_type: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-P002: Detect if option is mathematically valid but physically irrelevant.
    
    Triggers when:
    - Solution satisfies equations but may not match physical scenario
    - Mathematical existence doesn't imply physical relevance
    - Dimensional analysis correct but physical meaning unclear
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    
    # Patterns suggesting math-physics disconnect
    disconnect_markers = [
        "mathematically valid", "mathematically correct", "satisfies the equation",
        "solution exists", "formal solution", "analytical solution",
        "dimensionally correct", "units check out",
        "technically correct", "in principle",
        "mathematical possibility", "mathematically possible"
    ]
    
    # Patterns suggesting physical irrelevance
    irrelevance_markers = [
        "physically unrealistic", "unphysical", "non-physical",
        "not physically meaningful", "lacks physical significance",
        "doesn't correspond to", "doesn't apply to",
        "not relevant to", "outside the scope",
        "idealized", "in the limit", "as a limiting case"
    ]
    
    has_math_ok = any(marker in proof_lower for marker in disconnect_markers)
    has_physical_doubt = any(marker in proof_lower for marker in irrelevance_markers)
    
    if has_math_ok and has_physical_doubt:
        return True, "Kill argues mathematical validity but questions physical relevance"
    
    # Also check for explicit contradiction language (which should NOT trigger this rule)
    explicit_contradiction_markers = [
        "directly contradicts", "explicitly states", "violates conservation",
        "impossible because", "cannot be because", "forbidden by"
    ]
    
    if any(marker in proof_lower for marker in explicit_contradiction_markers):
        return False, None  # Explicit contradiction is valid, don't trigger
    
    # Check for "could be valid under different assumptions" patterns
    conditional_validity = [
        "would be correct if", "valid only if", "depends on whether",
        "correct under", "assuming", "if we interpret"
    ]
    
    if any(marker in proof_lower for marker in conditional_validity):
        return True, "Kill validity depends on unstated interpretive assumptions"
    
    return False, None


def detect_approximation_sensitivity(kill_proof: str) -> Tuple[bool, Optional[str]]:
    """
    RULE-P003: Detect if correctness depends on unstated ordering of limits/approximations.
    
    Triggers when:
    - Taylor expansion order matters
    - Small-angle vs exact treatment
    - First-order vs higher-order corrections
    - Order of limits affects result
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    
    # Approximation-sensitive patterns
    approximation_markers = [
        "taylor expansion", "taylor series", "first order", "first-order",
        "second order", "second-order", "higher order", "higher-order",
        "small angle", "small-angle", "sin θ ≈ θ", "cos θ ≈ 1",
        "to leading order", "lowest order", "dominant term",
        "lineariz", "perturbat", "expand around", "expansion around",
        "in the limit", "limiting case", "asymptotic",
        "truncat", "neglect", "ignoring higher", "dropping terms",
        "≈", "approximately", "roughly", "about"
    ]
    
    # Strong approximation sensitivity
    sensitivity_markers = [
        "depends on order", "order of approximation", "which order",
        "first vs second", "linear vs quadratic",
        "exact vs approximate", "exact calculation",
        "discrepancy", "differs by", "off by",
        "order matters", "sensitive to", "depends on which"
    ]
    
    has_approximation = any(marker in proof_lower for marker in approximation_markers)
    has_sensitivity = any(marker in proof_lower for marker in sensitivity_markers)
    
    if has_approximation and has_sensitivity:
        return True, "Kill depends on specific approximation order"
    
    # Check for numerical precision issues
    precision_markers = [
        "exact calculation yields", "precise value", "numerical value",
        "3 significant figures", "significant figures",
        "closest value", "nearest option", "rounding"
    ]
    
    if any(marker in proof_lower for marker in precision_markers):
        return True, "Kill depends on numerical precision or rounding"
    
    return False, None


def detect_symbol_overloading(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-P004: Detect if symbol/term has multiple standard meanings.
    
    Triggers when:
    - γ used without specifying Lorentz factor vs heat capacity ratio
    - β used without specifying v/c vs thermodynamic beta
    - Other overloaded physics symbols
    
    v1.4 FIX: Do NOT trigger if:
    - Symbol is explicitly defined in the question text
    - Only one possible meaning appears in context
    - Clear contextual anchors disambiguate the symbol
    """
    combined = f"{kill_proof or ''} {question_text or ''}".lower()
    question_lower = (question_text or "").lower()
    
    # Common overloaded physics symbols with their meanings AND contextual anchors
    overloaded_symbols = {
        "gamma": {
            "meanings": ["lorentz factor", "heat capacity ratio", "photon", "gamma ray", "euler", "gamma function"],
            "anchors": {
                "lorentz factor": ["lorentz", "relativistic", "time dilation", "length contraction", "β = v/c", "v/c"],
                "heat capacity ratio": ["heat capacity", "adiabatic", "cp/cv", "specific heat", "thermodynamic"],
                "gamma ray": ["radiation", "decay", "mev", "nuclear", "radioactive"],
            }
        },
        "β": {
            "meanings": ["v/c", "beta particle", "thermodynamic beta", "1/kt", "beta decay"],
            "anchors": {
                "v/c": ["relativistic", "lorentz", "velocity", "speed of light"],
                "thermodynamic beta": ["temperature", "boltzmann", "thermal", "1/kt"],
            }
        },
        "alpha": {
            "meanings": ["fine structure", "alpha particle", "angular acceleration", "thermal expansion"],
            "anchors": {
                "fine structure": ["fine structure", "1/137", "qed", "electromagnetic"],
                "alpha particle": ["decay", "helium", "nuclear", "radioactive"],
            }
        },
        "λ": {
            "meanings": ["wavelength", "decay constant", "eigenvalue", "mean free path"],
            "anchors": {
                "wavelength": ["wave", "frequency", "light", "photon", "nm", "spectrum"],
                "decay constant": ["decay", "half-life", "radioactive", "exponential"],
            }
        },
        "σ": {
            "meanings": ["cross section", "conductivity", "stefan-boltzmann", "stress", "standard deviation"],
            "anchors": {
                "cross section": ["scattering", "barn", "collision", "target"],
                "stefan-boltzmann": ["blackbody", "radiation", "t^4", "thermal emission"],
            }
        },
        "τ": {
            "meanings": ["proper time", "torque", "shear stress", "time constant", "lifetime"],
            "anchors": {
                "proper time": ["relativistic", "worldline", "lorentz"],
                "torque": ["rotation", "angular", "moment", "force"],
            }
        },
        "ω": {
            "meanings": ["angular frequency", "angular velocity", "solid angle"],
            "anchors": {
                "angular frequency": ["oscillation", "2πf", "frequency", "rad/s"],
                "solid angle": ["steradian", "sphere", "sr"],
            }
        },
        "μ": {
            "meanings": ["reduced mass", "magnetic moment", "coefficient of friction", "permeability", "micro"],
            "anchors": {
                "reduced mass": ["two-body", "m1*m2", "orbital"],
                "magnetic moment": ["magnetic", "spin", "bohr magneton"],
            }
        },
        "ε": {
            "meanings": ["permittivity", "emissivity", "strain", "small parameter"],
            "anchors": {
                "permittivity": ["dielectric", "electric field", "ε₀", "capacitor"],
                "emissivity": ["blackbody", "radiation", "thermal"],
            }
        },
    }
    
    # Definition markers that indicate explicit definition
    def has_explicit_definition(symbol: str, text: str) -> bool:
        """Check if symbol is explicitly defined in text."""
        patterns = [
            f"{symbol} =", f"{symbol}=",
            f"{symbol} is ", f"{symbol} is the",
            f"define {symbol}", f"where {symbol}",
            f"let {symbol}", f"denote {symbol}",
            f"{symbol} represents", f"{symbol} denotes",
        ]
        return any(p in text for p in patterns)
    
    def count_contextual_anchors(symbol_data: dict, text: str) -> Tuple[int, List[str]]:
        """Count how many distinct meanings have contextual anchors in the text."""
        found_meanings = []
        anchors = symbol_data.get("anchors", {})
        for meaning, anchor_terms in anchors.items():
            if any(term in text for term in anchor_terms):
                found_meanings.append(meaning)
        return len(found_meanings), found_meanings
    
    # Check each overloaded symbol
    for symbol, symbol_data in overloaded_symbols.items():
        if symbol not in combined:
            continue
        
        # FIRST: If symbol is explicitly defined in question, do NOT trigger
        if has_explicit_definition(symbol, question_lower):
            continue  # Question defines the symbol - no ambiguity
        
        # SECOND: Count contextual anchors
        n_anchored, anchored_meanings = count_contextual_anchors(symbol_data, combined)
        
        # If exactly one meaning is anchored by context, no ambiguity
        if n_anchored == 1:
            continue
        
        # If multiple meanings are anchored, that's ambiguous
        if n_anchored >= 2:
            return True, f"Symbol '{symbol}' has multiple anchored meanings in context: {anchored_meanings}"
        
        # If no anchors found but symbol is highly overloaded AND not defined anywhere
        meanings = symbol_data.get("meanings", [])
        if n_anchored == 0 and len(meanings) > 3:
            if not has_explicit_definition(symbol, combined):
                return True, f"Symbol '{symbol}' used without definition or contextual anchors (has {len(meanings)} common meanings)"
    
    return False, None


def detect_interpretive_frame_lock(kill_proof: str, question_text: str = "", round2_context: dict = None) -> Tuple[bool, Optional[str]]:
    """
    RULE-P005: Interpretive Frame Lock Guard
    
    Triggers when:
    - Early round commits to a physical interpretation (regime, frame, instrument model)
    - That interpretation is later shown to be convention-dependent or ambiguous
    - e.g., gpqa_343 pattern: lab frame vs CM frame ambiguity
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    question_lower = (question_text or "").lower()
    
    # Reference frame ambiguity patterns
    frame_markers = [
        "lab frame", "laboratory frame", "rest frame", "center of mass", "cm frame",
        "moving frame", "inertial frame", "non-inertial frame", "rotating frame",
        "reference frame", "observer frame", "detector frame",
        "earth frame", "rocket frame", "train frame"
    ]
    
    # Convention-dependent patterns
    convention_markers = [
        "by convention", "conventionally", "standard convention",
        "sign convention", "choosing", "we define", "define as",
        "adopting", "in our convention", "assuming the convention",
        "positive direction", "taking clockwise", "taking counterclockwise"
    ]
    
    # Interpretation-dependent patterns  
    interpretation_markers = [
        "one interpretation", "another interpretation", "could be interpreted",
        "depending on interpretation", "interpretive choice",
        "if we assume", "if we take", "under the assumption",
        "from the perspective of", "viewed from", "as seen by"
    ]
    
    has_frame = any(marker in proof_lower for marker in frame_markers)
    has_convention = any(marker in proof_lower for marker in convention_markers)
    has_interpretation = any(marker in proof_lower for marker in interpretation_markers)
    
    # Multiple frames mentioned suggests frame-dependence
    frames_mentioned = sum(1 for marker in frame_markers if marker in proof_lower)
    
    if frames_mentioned >= 2:
        return True, "Kill proof references multiple reference frames - result may be frame-dependent"
    
    if has_frame and (has_convention or has_interpretation):
        return True, "Kill depends on choice of reference frame or convention"
    
    if has_interpretation and "ambiguous" in proof_lower:
        return True, "Kill proof acknowledges interpretive ambiguity"
    
    # Check for explicit "depends on" language
    if "depends on which" in proof_lower or "depends on the choice" in proof_lower:
        return True, "Kill validity explicitly depends on interpretive choice"
    
    return False, None


def detect_instrument_assumption(kill_proof: str, question_text: str = "") -> Tuple[bool, Optional[str]]:
    """
    RULE-P006: Instrument Assumption Disclosure
    
    Triggers when:
    - Elimination relies on assumed observational capability
    - Resolution, detector class, bandwidth, sensitivity not stated in prompt
    - Separates physical law from measurement assumptions
    """
    if not kill_proof:
        return False, None
    
    proof_lower = kill_proof.lower()
    question_lower = (question_text or "").lower()
    
    # Instrument/measurement capability markers
    instrument_markers = [
        "detector", "instrument", "measurement", "observable", "observe",
        "resolution", "sensitivity", "precision", "accuracy",
        "bandwidth", "frequency response", "dynamic range",
        "signal-to-noise", "snr", "noise floor", "detection limit",
        "telescope", "spectrometer", "interferometer", "sensor",
        "camera", "ccd", "photomultiplier", "bolometer",
        "angular resolution", "spectral resolution", "temporal resolution"
    ]
    
    # Assumption language
    assumption_markers = [
        "assuming we can", "if we can detect", "if we can measure",
        "assuming sufficient", "with enough", "given adequate",
        "in principle", "ideally", "with perfect", "with ideal",
        "would require", "would need", "requires measuring",
        "not observable", "cannot observe", "undetectable",
        "below detection", "above threshold", "within sensitivity"
    ]
    
    # Check if question explicitly states instrument capabilities
    explicit_instrument_in_question = any(marker in question_lower for marker in [
        "detector has", "instrument with", "using a", "measurement with",
        "resolution of", "sensitivity of", "precision of"
    ])
    
    has_instrument = any(marker in proof_lower for marker in instrument_markers)
    has_assumption = any(marker in proof_lower for marker in assumption_markers)
    
    # Trigger if proof assumes instrument capability not stated in question
    if has_instrument and has_assumption and not explicit_instrument_in_question:
        return True, "Kill assumes observational capability not stated in question"
    
    # Specific patterns that strongly indicate instrument assumptions
    strong_assumption_patterns = [
        "would be detectable", "would be observable", "could be measured",
        "can be resolved", "can be distinguished", "separable",
        "assuming infinite resolution", "with sufficient statistics",
        "integrating for long enough", "with enough exposure"
    ]
    
    for pattern in strong_assumption_patterns:
        if pattern in proof_lower and not explicit_instrument_in_question:
            return True, f"Kill assumes '{pattern}' without instrument specification"
    
    return False, None


# =============================================================================
# Main Rule Application Function
# =============================================================================

def apply_physics_rules(
    kill_aggregation: dict,
    survivor_conditions: dict,
    question_text: str = "",
    round2a_result: dict = None,
    ladder_level: int = None,
) -> RuleLibraryResult:
    """
    Apply all Physics rules to the evaluation results.
    
    Physics rules run AFTER Biology rules. Stricter constraint wins.
    
    Args:
        kill_aggregation: Output from aggregate_kill_shots()
        survivor_conditions: Conditions attached to surviving options
        question_text: The original question text
        round2a_result: Results from representation check (optional)
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
    
    # =================================================================
    # RULE-P001: Regime Validity Guard
    # =================================================================
    rule_p001_triggered = False
    rule_p001_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        option = kill.get("option", "")
        
        triggered, reason = detect_regime_violation(kill_proof, question_text)
        if triggered:
            rule_p001_triggered = True
            rule_p001_affected.append(option)
            downgraded_kills[option] = f"RULE-P001: {reason}"
            fragility_markers.append(f"Regime-dependent reasoning for option {option}")
    
    if rule_p001_triggered:
        # Cap at L2
        if ladder_cap is None or ladder_cap > 2:
            ladder_cap = 2
    
    rule_results.append(RuleResult(
        rule_id="RULE-P001",
        triggered=rule_p001_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule_p001_triggered else RuleEffect.NO_EFFECT,
        description="Regime Validity Guard: Elimination applies reasoning outside operational regime",
        affected_kills=rule_p001_affected,
        ladder_cap=2 if rule_p001_triggered else None,
        fragility_note="Physical laws have validity domains" if rule_p001_triggered else None
    ))
    
    # =================================================================
    # RULE-P002: Mathematical Sufficiency Guard  
    # =================================================================
    rule_p002_triggered = False
    rule_p002_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        kill_type = kill.get("kill_type", "")
        option = kill.get("option", "")
        
        triggered, reason = detect_math_physical_disconnect(kill_proof, kill_type)
        if triggered:
            rule_p002_triggered = True
            rule_p002_affected.append(option)
            downgraded_kills[option] = f"RULE-P002: {reason}"
            fragility_markers.append(f"Math-physics disconnect for option {option}")
    
    if rule_p002_triggered:
        # Cap at L3 (less restrictive than P001)
        if ladder_cap is None or ladder_cap > 3:
            ladder_cap = 3
    
    rule_results.append(RuleResult(
        rule_id="RULE-P002",
        triggered=rule_p002_triggered,
        effect=RuleEffect.BLOCK_HARD_KILLS if rule_p002_triggered else RuleEffect.NO_EFFECT,
        description="Mathematical Sufficiency Guard: Option is mathematically valid but may be physically irrelevant",
        affected_kills=rule_p002_affected,
        ladder_cap=3 if rule_p002_triggered else None,
        fragility_note="Mathematical validity ≠ physical relevance" if rule_p002_triggered else None
    ))
    
    # =================================================================
    # RULE-P003: Limit/Approximation Ordering Guard
    # =================================================================
    rule_p003_triggered = False
    rule_p003_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        option = kill.get("option", "")
        
        triggered, reason = detect_approximation_sensitivity(kill_proof)
        if triggered:
            rule_p003_triggered = True
            rule_p003_affected.append(option)
            downgraded_kills[option] = f"RULE-P003: {reason}"
            fragility_markers.append(f"Approximation-sensitive for option {option}")
    
    if rule_p003_triggered:
        # Cap at L2
        if ladder_cap is None or ladder_cap > 2:
            ladder_cap = 2
    
    rule_results.append(RuleResult(
        rule_id="RULE-P003",
        triggered=rule_p003_triggered,
        effect=RuleEffect.BLOCK_HARD_KILLS if rule_p003_triggered else RuleEffect.NO_EFFECT,
        description="Limit/Approximation Ordering Guard: Correctness depends on unstated approximation ordering",
        affected_kills=rule_p003_affected,
        ladder_cap=2 if rule_p003_triggered else None,
        fragility_note="Different approximation orders yield different results" if rule_p003_triggered else None
    ))
    
    # =================================================================
    # RULE-P004: Symbol Overloading Guard
    # =================================================================
    rule_p004_triggered = False
    rule_p004_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        option = kill.get("option", "")
        
        triggered, reason = detect_symbol_overloading(kill_proof, question_text)
        if triggered:
            rule_p004_triggered = True
            rule_p004_affected.append(option)
            downgraded_kills[option] = f"RULE-P004: {reason}"
            fragility_markers.append(f"Symbol ambiguity for option {option}")
    
    # P004 defers to Biology RULE-006 for ladder cap (representation ambiguity)
    # So we don't set ladder_cap here, but we do mark fragility
    
    rule_results.append(RuleResult(
        rule_id="RULE-P004",
        triggered=rule_p004_triggered,
        effect=RuleEffect.BLOCK_HARD_KILLS if rule_p004_triggered else RuleEffect.NO_EFFECT,
        description="Symbol Overloading Guard: Symbol/term has multiple standard meanings",
        affected_kills=rule_p004_affected,
        fragility_note="Symbol overloading is endemic in physics" if rule_p004_triggered else None
    ))
    
    # =================================================================
    # RULE-P005: Interpretive Frame Lock Guard (NEW)
    # =================================================================
    rule_p005_triggered = False
    rule_p005_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        option = kill.get("option", "")
        
        triggered, reason = detect_interpretive_frame_lock(kill_proof, question_text, round2a_result)
        if triggered:
            rule_p005_triggered = True
            rule_p005_affected.append(option)
            downgraded_kills[option] = f"RULE-P005: {reason}"
            fragility_markers.append(f"Interpretive frame dependence for option {option}")
    
    if rule_p005_triggered:
        # Cap at L2 or worse per spec
        if ladder_cap is None or ladder_cap > 2:
            ladder_cap = 2
    
    rule_results.append(RuleResult(
        rule_id="RULE-P005",
        triggered=rule_p005_triggered,
        effect=RuleEffect.DOWNGRADE_HARD_TO_SOFT if rule_p005_triggered else RuleEffect.NO_EFFECT,
        description="Interpretive Frame Lock Guard: Early commitment to convention-dependent interpretation",
        affected_kills=rule_p005_affected,
        ladder_cap=2 if rule_p005_triggered else None,
        fragility_note="Interpretive frame dependence - contradiction under latent ambiguity" if rule_p005_triggered else None
    ))
    
    # =================================================================
    # RULE-P006: Instrument Assumption Disclosure (NEW)
    # =================================================================
    rule_p006_triggered = False
    rule_p006_affected = []
    
    for kill in confirmed_kills:
        kill_proof = kill.get("kill_proof", "")
        option = kill.get("option", "")
        
        triggered, reason = detect_instrument_assumption(kill_proof, question_text)
        if triggered:
            rule_p006_triggered = True
            rule_p006_affected.append(option)
            downgraded_kills[option] = f"RULE-P006: {reason}"
            fragility_markers.append(f"Instrument assumption for option {option}")
    
    if rule_p006_triggered:
        # Prohibit FULL_ASSERT and ASSERT_BY_ELIMINATION (levels 0 and 1)
        # So cap at L2 minimum
        if ladder_cap is None or ladder_cap > 2:
            ladder_cap = 2
        # Also add prohibition marker
        prohibitions.append("PROHIBIT_FULL_ASSERT")
        prohibitions.append("PROHIBIT_ASSERT_BY_ELIMINATION")
    
    rule_results.append(RuleResult(
        rule_id="RULE-P006",
        triggered=rule_p006_triggered,
        effect=RuleEffect.PROHIBIT_ASSERTION_LEVEL if rule_p006_triggered else RuleEffect.NO_EFFECT,
        description="Instrument Assumption Disclosure: Kill relies on unstated observational capability",
        affected_kills=rule_p006_affected,
        ladder_cap=2 if rule_p006_triggered else None,
        fragility_note="Separates physical law from measurement assumptions" if rule_p006_triggered else None
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


def get_physics_rule_library_version() -> str:
    """Return the version of the physics rule library."""
    return "v1.3-physics-CANDIDATE"


def get_physics_rule_descriptions() -> Dict[str, str]:
    """Return human-readable descriptions of all physics rules.
    
    NOTE (v1.3): These rules cap confidence under ambiguity. This does not prevent
    assertion by decisive elimination if three alternatives are independently 
    HARD-killed under shared assumptions.
    """
    return {
        "RULE-P001": "Regime Validity Guard: Downgrade HARD→SOFT when reasoning outside operational regime; cap L2. (Does not prevent assertion by decisive elimination if 3+ alternatives independently HARD-killed under shared assumptions)",
        "RULE-P002": "Mathematical Sufficiency Guard: Block HARD kills when math valid but physically irrelevant; cap L3. (Does not prevent assertion by decisive elimination if 3+ alternatives independently HARD-killed under shared assumptions)",
        "RULE-P003": "Limit/Approximation Ordering Guard: Block HARD kills when approximation order unstated; cap L2. (Does not prevent assertion by decisive elimination if 3+ alternatives independently HARD-killed under shared assumptions)",
        "RULE-P004": "Symbol Overloading Guard: Block HARD kills when symbols have multiple meanings",
        "RULE-P005": "Interpretive Frame Lock Guard: Downgrade when early interpretation is convention-dependent; cap L2. (Does not prevent assertion by decisive elimination if 3+ alternatives independently HARD-killed under shared assumptions)",
        "RULE-P006": "Instrument Assumption Disclosure: Convert HARD→conditional when assuming unstated instrument capability; prohibit L0/L1. (Does not prevent assertion by decisive elimination if 3+ alternatives independently HARD-killed under shared assumptions)",
    }


# Flag indicating this is a CANDIDATE library (not yet frozen)
PHYSICS_RULES_STATUS = "CANDIDATE"


if __name__ == "__main__":
    # Test the module
    print(f"Physics Rule Library {get_physics_rule_library_version()}")
    print(f"Status: {PHYSICS_RULES_STATUS}")
    print("\nRules implemented:")
    for rule_id, desc in get_physics_rule_descriptions().items():
        print(f"  {rule_id}: {desc}")