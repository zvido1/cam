#!/usr/bin/env python3
"""
Layered Disposition Schema and Computation for CAM v2

Instead of binary ASSERT/ABSTAIN, this produces structured outputs:
- What's definitively eliminated (with proofs)
- What survives conditionally (with conditions)
- What would resolve remaining ambiguity
- What can be asserted unconditionally

Aligns with Patent Claim 4: "qualified assertion with disclosed uncertainty"
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class DispositionLevel(Enum):
    """Hierarchy of disposition outcomes, from strongest to weakest."""
    FULL_ASSERTION = "full_assertion"           # Single answer, high confidence, no unresolved conditions
    PARTIAL_ELIMINATION = "partial_elimination"  # Some killed, survivors conditional
    CONDITIONAL_PREFERENCE = "conditional_preference"  # No kills, but clear conditional ranking
    UNDERDETERMINED = "underdetermined"          # Multiple survivors, conditions don't separate them
    EPISTEMIC_BOUNDARY = "epistemic_boundary"    # Stress test shows fundamental fragility
    ABSTAIN = "abstain"                          # Cannot make any useful assertion


@dataclass
class EliminationProof:
    """Proof that an option is definitively ruled out."""
    option: str
    kill_type: str  # constraint_violation, internal_contradiction, mechanism_impossibility, product_class_mismatch
    kill_proof: str
    kill_target: str
    consensus_count: int  # How many evaluators agreed on this kill
    issuing_evaluators: List[str]


@dataclass
class ConditionalSurvivor:
    """An option that survives only under stated conditions."""
    option: str
    conditions: List[str]
    would_be_falsified_if: List[str]
    supporting_evaluators: List[str]
    condition_confidence: str  # high, medium, low


@dataclass 
class ResolutionPath:
    """What information or clarification would resolve remaining ambiguity."""
    blocker_type: str  # mutual_exclusivity, missing_parameter, ambiguous_reference, unstated_convention
    description: str
    would_resolve: List[str]  # Which options this would disambiguate
    suggested_clarification: Optional[str] = None


@dataclass
class LayeredDisposition:
    """
    The full structured output replacing binary assert/abstain.
    
    This captures:
    - Definitive eliminations (with proofs)
    - Conditional survivors (with conditions)
    - Resolution paths (what would disambiguate)
    - Assertable knowledge (what we CAN say definitively)
    """
    # Core classification
    level: DispositionLevel
    
    # Elimination layer
    eliminated: List[str] = field(default_factory=list)
    elimination_proofs: Dict[str, EliminationProof] = field(default_factory=dict)
    
    # Conditional layer
    conditional_survivors: Dict[str, ConditionalSurvivor] = field(default_factory=dict)
    
    # Resolution layer
    resolution_blockers: List[ResolutionPath] = field(default_factory=list)
    
    # Assertion layer - what we CAN say
    assertable_eliminations: str = ""  # e.g., "NOT A, NOT B"
    assertable_preference: Optional[str] = None  # e.g., "C preferred over D if kinetic control"
    unconditional_assertion: Optional[str] = None  # e.g., "C" (only if truly unconditional)
    
    # Metadata
    confidence_summary: str = ""
    fragility_flags: List[str] = field(default_factory=list)
    evaluator_agreement: Dict[str, int] = field(default_factory=dict)  # option -> count
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        d = {
            "level": self.level.value,
            "eliminated": self.eliminated,
            "elimination_proofs": {k: asdict(v) for k, v in self.elimination_proofs.items()},
            "conditional_survivors": {k: asdict(v) for k, v in self.conditional_survivors.items()},
            "resolution_blockers": [asdict(r) for r in self.resolution_blockers],
            "assertable_eliminations": self.assertable_eliminations,
            "assertable_preference": self.assertable_preference,
            "unconditional_assertion": self.unconditional_assertion,
            "confidence_summary": self.confidence_summary,
            "fragility_flags": self.fragility_flags,
            "evaluator_agreement": self.evaluator_agreement,
        }
        return d
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def human_readable(self) -> str:
        """Generate human-readable summary."""
        lines = []
        lines.append(f"=== DISPOSITION: {self.level.value.upper()} ===")
        lines.append("")
        
        if self.unconditional_assertion:
            lines.append(f"ASSERTION: {self.unconditional_assertion}")
        
        if self.eliminated:
            lines.append(f"ELIMINATED: {', '.join(self.eliminated)}")
            for opt, proof in self.elimination_proofs.items():
                lines.append(f"  {opt}: {proof.kill_type} - {proof.kill_proof[:100]}...")
        
        if self.conditional_survivors:
            lines.append("")
            lines.append("CONDITIONAL SURVIVORS:")
            for opt, survivor in self.conditional_survivors.items():
                conds = "; ".join(survivor.conditions[:2])
                lines.append(f"  {opt} IF [{conds}]")
        
        if self.resolution_blockers:
            lines.append("")
            lines.append("RESOLUTION BLOCKERS:")
            for blocker in self.resolution_blockers:
                lines.append(f"  - {blocker.blocker_type}: {blocker.description}")
        
        if self.assertable_eliminations:
            lines.append("")
            lines.append(f"ASSERTABLE: {self.assertable_eliminations}")
        
        if self.fragility_flags:
            lines.append("")
            lines.append(f"FRAGILITY FLAGS: {', '.join(self.fragility_flags)}")
        
        return "\n".join(lines)


def compute_layered_disposition(
    round1_results: dict,
    round2c_results: Optional[dict],
    round2d_results: Optional[dict],  # Resurrection results
    final_commit_results: Optional[dict],
    grok_analysis: Optional[dict],
    synthesis_result: Optional[dict],
    round3_results: Optional[dict],
    auditor_result: Optional[dict],
    candidate_options: List[str],
    EVALUATORS: List[str] = None,
) -> LayeredDisposition:
    """
    Compute the layered disposition from all pipeline results.
    
    This replaces the old compute_final_disposition() binary logic.
    """
    if EVALUATORS is None:
        EVALUATORS = ["A", "B", "C", "D"]
    
    disposition = LayeredDisposition(level=DispositionLevel.UNDERDETERMINED)
    
    # ========================================
    # LAYER 1: Extract eliminations
    # ========================================
    eliminated = set()
    elimination_proofs = {}
    
    if round2c_results:
        kill_aggregation = round2c_results.get("kill_aggregation", {})
        unique_kills = kill_aggregation.get("unique_kills", [])
        
        for kill in unique_kills:
            opt = kill.get("option")
            if opt:
                eliminated.add(opt)
                
                # Check if resurrection overturned this kill
                resurrection_overturned = False
                if round2d_results:
                    summary = round2d_results.get("summary", {})
                    downgraded = summary.get("downgraded_to_conditions", [])
                    if opt in downgraded:
                        resurrection_overturned = True
                
                if not resurrection_overturned:
                    elimination_proofs[opt] = EliminationProof(
                        option=opt,
                        kill_type=kill.get("kill_type", "unknown"),
                        kill_proof=kill.get("kill_proof", ""),
                        kill_target=kill.get("kill_target", ""),
                        consensus_count=kill.get("consensus_count", 1),
                        issuing_evaluators=[kill.get("issuing_evaluator", "unknown")],
                    )
    
    disposition.eliminated = sorted(eliminated)
    disposition.elimination_proofs = elimination_proofs
    
    # Build assertable eliminations string
    if eliminated:
        disposition.assertable_eliminations = "NOT " + ", NOT ".join(sorted(eliminated))
    
    # ========================================
    # LAYER 2: Extract conditional survivors
    # ========================================
    all_options = set(["A", "B", "C", "D"])
    survivors = all_options - eliminated
    
    if round2c_results:
        survivor_conditions = round2c_results.get("survivor_conditions", {})
        
        for opt in survivors:
            opt_conditions = survivor_conditions.get(opt, {})
            conditions = opt_conditions.get("conditions", [])
            falsifiers = opt_conditions.get("would_be_falsified_if", [])
            
            # Find supporting evaluators
            supporting = []
            if final_commit_results:
                for eval_name in EVALUATORS:
                    eval_result = final_commit_results.get(f"evaluator_{eval_name}", {})
                    if eval_result.get("final_choice") == opt:
                        supporting.append(eval_name)
            elif round1_results:
                for eval_name in EVALUATORS:
                    eval_result = round1_results.get(f"evaluator_{eval_name}", {})
                    if eval_result.get("final_choice") == opt:
                        supporting.append(eval_name)
            
            # Determine condition confidence
            if len(conditions) == 0:
                cond_confidence = "high"  # No conditions = unconditional
            elif len(conditions) <= 2:
                cond_confidence = "medium"
            else:
                cond_confidence = "low"
            
            disposition.conditional_survivors[opt] = ConditionalSurvivor(
                option=opt,
                conditions=conditions,
                would_be_falsified_if=falsifiers,
                supporting_evaluators=supporting,
                condition_confidence=cond_confidence,
            )
    else:
        # No Round 2c - just mark survivors as unconditional
        for opt in survivors:
            supporting = []
            for eval_name in EVALUATORS:
                eval_result = round1_results.get(f"evaluator_{eval_name}", {})
                if eval_result.get("final_choice") == opt:
                    supporting.append(eval_name)
            
            disposition.conditional_survivors[opt] = ConditionalSurvivor(
                option=opt,
                conditions=[],
                would_be_falsified_if=[],
                supporting_evaluators=supporting,
                condition_confidence="high" if len(supporting) >= 3 else "medium",
            )
    
    # ========================================
    # LAYER 3: Identify resolution blockers
    # ========================================
    resolution_blockers = []
    
    # Check for mutual exclusivity between survivors
    if len(survivors) >= 2:
        survivor_list = sorted(survivors)
        conditions_by_opt = {
            opt: set(disposition.conditional_survivors.get(opt, ConditionalSurvivor(opt, [], [], [], "low")).conditions)
            for opt in survivor_list
        }
        
        # Look for mutually exclusive conditions
        for i, opt1 in enumerate(survivor_list):
            for opt2 in survivor_list[i+1:]:
                conds1 = conditions_by_opt.get(opt1, set())
                conds2 = conditions_by_opt.get(opt2, set())
                
                # Check for obvious exclusivity keywords
                exclusivity_pairs = [
                    ("kinetic", "thermodynamic"),
                    ("fast", "slow"),
                    ("low temperature", "high temperature"),
                    ("acidic", "basic"),
                ]
                
                for kw1, kw2 in exclusivity_pairs:
                    conds1_str = " ".join(conds1).lower()
                    conds2_str = " ".join(conds2).lower()
                    if (kw1 in conds1_str and kw2 in conds2_str) or (kw2 in conds1_str and kw1 in conds2_str):
                        resolution_blockers.append(ResolutionPath(
                            blocker_type="mutual_exclusivity",
                            description=f"{opt1} and {opt2} depend on mutually exclusive conditions ({kw1} vs {kw2})",
                            would_resolve=[opt1, opt2],
                            suggested_clarification=f"Specify whether {kw1} or {kw2} conditions apply",
                        ))
    
    # Check Grok analysis for incompatibility flags
    if grok_analysis:
        reasoning_relation = grok_analysis.get("reasoning_relation", "UNKNOWN")
        if reasoning_relation in ["INCOMPATIBLE", "MIXED"]:
            incompatible_assumptions = grok_analysis.get("incompatible_assumptions", [])
            if incompatible_assumptions:
                resolution_blockers.append(ResolutionPath(
                    blocker_type="incompatible_reasoning",
                    description=f"Evaluators used incompatible reasoning frameworks",
                    would_resolve=list(survivors),
                    suggested_clarification=f"Clarify: {incompatible_assumptions[0][:100]}" if incompatible_assumptions else None,
                ))
    
    # Check synthesis for ambiguous references
    if synthesis_result:
        # Look for "ambiguous" or "unclear" in proof ledger
        proof_ledger = synthesis_result.get("proof_ledger", {})
        for opt, ledger in proof_ledger.items():
            gaps = ledger.get("gaps", [])
            for gap in gaps:
                if "ambiguous" in gap.lower() or "unclear" in gap.lower():
                    resolution_blockers.append(ResolutionPath(
                        blocker_type="ambiguous_reference",
                        description=f"Option {opt}: {gap[:100]}",
                        would_resolve=[opt],
                    ))
    
    disposition.resolution_blockers = resolution_blockers
    
    # ========================================
    # LAYER 4: Check fragility from Round 3
    # ========================================
    fragility_flags = []
    
    if round3_results:
        any_can_break = round3_results.get("any_can_break", False)
        robustness = round3_results.get("robustness", "UNKNOWN")
        
        if any_can_break or robustness == "FRAGILE":
            fragility_flags.append("stress_test_fragile")
            
            # Extract specific fragility reasons
            for eval_name in EVALUATORS:
                eval_result = round3_results.get(f"evaluator_{eval_name}", {})
                if eval_result.get("can_break", False):
                    failure_mode = eval_result.get("failure_mode", "")
                    minimal_premise = eval_result.get("minimal_premise_that_fails", "")
                    if failure_mode and failure_mode != "none":
                        fragility_flags.append(f"{eval_name}:{failure_mode}")
    
    disposition.fragility_flags = fragility_flags
    
    # ========================================
    # LAYER 5: Compute evaluator agreement
    # ========================================
    evaluator_agreement = {}
    source_results = final_commit_results or round1_results
    
    if source_results:
        for eval_name in EVALUATORS:
            eval_result = source_results.get(f"evaluator_{eval_name}", {})
            choice = eval_result.get("final_choice")
            if choice and choice != "ABSTAIN":
                evaluator_agreement[choice] = evaluator_agreement.get(choice, 0) + 1
    
    disposition.evaluator_agreement = evaluator_agreement
    
    # ========================================
    # LAYER 6: Determine final level and assertions
    # ========================================
    
    # Count survivors with no conditions (truly unconditional)
    unconditional_survivors = [
        opt for opt, survivor in disposition.conditional_survivors.items()
        if len(survivor.conditions) == 0 and opt not in eliminated
    ]
    
    # Check for unanimous agreement
    max_agreement = max(evaluator_agreement.values()) if evaluator_agreement else 0
    unanimous_choice = None
    if max_agreement == len(EVALUATORS):
        unanimous_choice = [opt for opt, count in evaluator_agreement.items() if count == max_agreement][0]
    
    # Determine disposition level
    if unanimous_choice and not fragility_flags and len(survivors) == 1:
        # FULL ASSERTION: Single survivor, unanimous, not fragile
        disposition.level = DispositionLevel.FULL_ASSERTION
        disposition.unconditional_assertion = unanimous_choice
        disposition.confidence_summary = "High confidence unconditional assertion"
    
    elif len(eliminated) > 0 and len(survivors) >= 1:
        # PARTIAL ELIMINATION: We killed some options
        if len(survivors) == 1:
            # Only one survivor after elimination
            sole_survivor = list(survivors)[0]
            survivor_data = disposition.conditional_survivors.get(sole_survivor)
            
            if survivor_data and len(survivor_data.conditions) == 0 and not fragility_flags:
                # Unconditional sole survivor
                disposition.level = DispositionLevel.FULL_ASSERTION
                disposition.unconditional_assertion = sole_survivor
                disposition.confidence_summary = "Sole survivor after elimination, no conditions"
            else:
                disposition.level = DispositionLevel.PARTIAL_ELIMINATION
                disposition.assertable_preference = f"{sole_survivor} (sole survivor, conditional)"
                disposition.confidence_summary = f"Eliminated {len(eliminated)}, 1 conditional survivor"
        else:
            # Multiple survivors
            disposition.level = DispositionLevel.PARTIAL_ELIMINATION
            if max_agreement >= 3:
                preferred = [opt for opt, count in evaluator_agreement.items() if count == max_agreement][0]
                disposition.assertable_preference = f"{preferred} preferred ({max_agreement}/{len(EVALUATORS)} evaluators)"
            disposition.confidence_summary = f"Eliminated {len(eliminated)}, {len(survivors)} survivors"
    
    elif len(survivors) > 1 and max_agreement >= 3:
        # CONDITIONAL PREFERENCE: No kills, but clear preference
        preferred = [opt for opt, count in evaluator_agreement.items() if count == max_agreement][0]
        disposition.level = DispositionLevel.CONDITIONAL_PREFERENCE
        disposition.assertable_preference = f"{preferred} ({max_agreement}/{len(EVALUATORS)} evaluators)"
        disposition.confidence_summary = f"No eliminations, majority preference for {preferred}"
    
    elif fragility_flags:
        # EPISTEMIC BOUNDARY: Stress test showed fragility
        disposition.level = DispositionLevel.EPISTEMIC_BOUNDARY
        disposition.confidence_summary = f"Fragile: {', '.join(fragility_flags[:3])}"
    
    else:
        # UNDERDETERMINED: Can't separate survivors
        disposition.level = DispositionLevel.UNDERDETERMINED
        disposition.confidence_summary = f"{len(survivors)} options remain, insufficient separation"
    
    return disposition


# ========================================
# Schema for JSON serialization
# ========================================

LAYERED_DISPOSITION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Layered Disposition Schema",
    "description": "Structured disposition output with eliminations, conditions, and resolution paths",
    "type": "object",
    "required": ["level", "eliminated", "conditional_survivors", "assertable_eliminations"],
    "properties": {
        "level": {
            "type": "string",
            "enum": ["full_assertion", "partial_elimination", "conditional_preference", 
                     "underdetermined", "epistemic_boundary", "abstain"],
            "description": "Disposition level from strongest to weakest"
        },
        "eliminated": {
            "type": "array",
            "items": {"type": "string", "enum": ["A", "B", "C", "D"]},
            "description": "Options definitively ruled out"
        },
        "elimination_proofs": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "option": {"type": "string"},
                    "kill_type": {"type": "string"},
                    "kill_proof": {"type": "string"},
                    "kill_target": {"type": "string"},
                    "consensus_count": {"type": "integer"},
                    "issuing_evaluators": {"type": "array", "items": {"type": "string"}}
                }
            },
            "description": "Proofs for each elimination"
        },
        "conditional_survivors": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "option": {"type": "string"},
                    "conditions": {"type": "array", "items": {"type": "string"}},
                    "would_be_falsified_if": {"type": "array", "items": {"type": "string"}},
                    "supporting_evaluators": {"type": "array", "items": {"type": "string"}},
                    "condition_confidence": {"type": "string", "enum": ["high", "medium", "low"]}
                }
            },
            "description": "Surviving options with their conditions"
        },
        "resolution_blockers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "blocker_type": {"type": "string"},
                    "description": {"type": "string"},
                    "would_resolve": {"type": "array", "items": {"type": "string"}},
                    "suggested_clarification": {"type": ["string", "null"]}
                }
            },
            "description": "What information would resolve remaining ambiguity"
        },
        "assertable_eliminations": {
            "type": "string",
            "description": "What we can definitively assert about eliminations (e.g., 'NOT A, NOT B')"
        },
        "assertable_preference": {
            "type": ["string", "null"],
            "description": "Conditional preference statement if applicable"
        },
        "unconditional_assertion": {
            "type": ["string", "null"],
            "description": "Single answer assertion if fully justified"
        },
        "confidence_summary": {
            "type": "string",
            "description": "Human-readable confidence summary"
        },
        "fragility_flags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Flags from stress testing indicating fragile assumptions"
        },
        "evaluator_agreement": {
            "type": "object",
            "additionalProperties": {"type": "integer"},
            "description": "Count of evaluators supporting each option"
        }
    }
}


# ========================================
# Example usage and test
# ========================================

if __name__ == "__main__":
    # Example: Partial elimination scenario
    example_disposition = LayeredDisposition(
        level=DispositionLevel.PARTIAL_ELIMINATION,
        eliminated=["A", "B"],
        elimination_proofs={
            "A": EliminationProof(
                option="A",
                kill_type="constraint_violation",
                kill_proof="Expression yields negative value at γ=0, but variance bounds must be non-negative",
                kill_target="Claim that 2γ-0.5 is a valid variance bound",
                consensus_count=3,
                issuing_evaluators=["A", "C", "D"]
            ),
            "B": EliminationProof(
                option="B",
                kill_type="mechanism_impossibility",
                kill_proof="Requires SN2 at tertiary carbon, which is sterically blocked",
                kill_target="Proposed reaction mechanism",
                consensus_count=4,
                issuing_evaluators=["A", "B", "C", "D"]
            ),
        },
        conditional_survivors={
            "C": ConditionalSurvivor(
                option="C",
                conditions=["Assumes kinetic control (fast quenching)", "T < 0°C"],
                would_be_falsified_if=["Thermodynamic equilibrium reached", "Extended reaction time"],
                supporting_evaluators=["A", "B"],
                condition_confidence="medium"
            ),
            "D": ConditionalSurvivor(
                option="D",
                conditions=["Assumes thermodynamic control", "Equilibrium conditions"],
                would_be_falsified_if=["Kinetic trapping occurs", "Low temperature"],
                supporting_evaluators=["C", "D"],
                condition_confidence="medium"
            ),
        },
        resolution_blockers=[
            ResolutionPath(
                blocker_type="mutual_exclusivity",
                description="C and D depend on mutually exclusive conditions (kinetic vs thermodynamic)",
                would_resolve=["C", "D"],
                suggested_clarification="Specify reaction conditions: quenching rate and temperature"
            )
        ],
        assertable_eliminations="NOT A, NOT B",
        assertable_preference="C preferred if kinetic control; D preferred if thermodynamic control",
        unconditional_assertion=None,
        confidence_summary="Eliminated 2 options, 2 conditional survivors with mutual exclusivity",
        fragility_flags=[],
        evaluator_agreement={"C": 2, "D": 2}
    )
    
    print(example_disposition.human_readable())
    print("\n" + "="*60 + "\n")
    print("JSON output:")
    print(example_disposition.to_json())
