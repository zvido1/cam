#!/usr/bin/env python3
"""
Auditor Terminal States Module - CAM v2.5.6

PATCH v2.5.6 (2026-01-25): UWEB Ladder Remap
- UWEB no longer forces WITHHOLD - instead downgrades to L1_ASSERT_QUALIFIED
- UWEB detects weak consensus, not unknowability
- Weak consensus lowers commitment; only true ambiguity withholds
- Added ladder_level and confidence_qualifier fields to AuditorDecision
- Terminal states remain: ASSERTED, WITHHELD, ERROR (no new states)
- WITHHOLD reserved for: n_survivors>=2, unanimity_contradicted, representation_contested, etc.

PATCH v2.5.5 (2026-01-25): UWEB refinements
- Added alternative pathway for independent evidence: early-stage pruning (candidate_options source)
- repair_applied alone no longer triggers UWEB (only diagnostic unless → representation_contested)
- "kill_aggregation" alone does NOT count as decisive pruning (too loose)
- Prevents unnecessary abstention on clean early-stage deterministic pruning

PATCH v2.5.4 (2026-01-25): UWEB - Unanimous Without Evidence Block
- Added UNANIMOUS_WITHOUT_INDEPENDENT_EVIDENCE rule (now downgrades, doesn't block)
- Based on empirical evidence from Run 180: 7/7 asserted-wrong had this pattern

PATCH v2.5.3 (2026-01-23): Authoritative survivor computation
- Added get_authoritative_survivors() function with priority order
- n_survivors now computed from canonical survivor set
- Added survivor_source field to AuditorDecision for audit trail

PATCH v2.5.2 (2026-01-23): Diagnostic vs Blocking separation hardening
- Added representation_contested as BLOCKING flag
- Strict separation: diagnostics NEVER block assertion

PATCH v2.5.1 (2026-01-23): Fixed commit eligibility math
- Assert if len(final_survivors) == 1 (and no blocking flags)
- hard_kill_count remains as diagnostic/audit trail only

Implements three-valued auditor outcome semantics per updated specification:
1. ASSERT_CORRECT - One option survives decisive elimination OR epistemic unanimity
2. ASSERT_INCORRECT - A non-gold option is decisively asserted
3. WITHHOLD_ASSERTION - True underdetermination (multiple survivors, blocking flags)

LADDER LEVELS (v2.5.6):
- L0_FULL_ASSERT: Strong independent evidence (2+ hard kills or clean decisive pruning)
- L1_ASSERT_QUALIFIED: Unanimous consensus without independent eliminative evidence (UWEB)
- L2_ASSERT_CONDITIONAL: Reserved for future use (conditional assertions)
- L3_UNCERTAIN: Reserved for future use (preference without commitment)
- L4_ABSTAIN: True underdetermination or blocking conditions

INVARIANTS:
- Models must always commit to an answer (A/B/C/D) - models never abstain
- Auditor alone decides final assertion AND commitment level
- WITHHOLD_ASSERTION is NOT a model action - it is an auditor decision only
- UWEB detects weak consensus, not ignorance - weak consensus lowers commitment
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import json

# Number of initial options (A, B, C, D)
N_INITIAL_OPTIONS = 4


class AuditorTerminalState(Enum):
    """
    Three-valued auditor outcome semantics.
    
    This is the final disposition as determined by the auditor layer.
    Models always commit; the auditor decides whether that commitment
    earns an assertion.
    """
    ASSERT_CORRECT = "ASSERT_CORRECT"           # Decisive elimination OR epistemic unanimity
    ASSERT_INCORRECT = "ASSERT_INCORRECT"       # Non-gold option decisively asserted
    WITHHOLD_ASSERTION = "WITHHOLD_ASSERTION"   # True underdetermination (multiple survivors, blocking flags)


class LadderLevel(Enum):
    """
    Ladder of commitment levels (v2.5.6).
    
    These express confidence/commitment alongside terminal state.
    L0-L1 are ASSERTED states with varying confidence.
    L4 is WITHHELD state.
    """
    L0_FULL_ASSERT = 0          # Strong independent evidence
    L1_ASSERT_QUALIFIED = 1     # Unanimous consensus without independent evidence (UWEB)
    L2_ASSERT_CONDITIONAL = 2   # Reserved: conditional assertion
    L3_UNCERTAIN = 3            # Reserved: preference without commitment
    L4_ABSTAIN = 4              # True underdetermination / blocking conditions


# Human-readable ladder level names for dossier
LADDER_LEVEL_NAMES = {
    LadderLevel.L0_FULL_ASSERT: "FULL_ASSERT",
    LadderLevel.L1_ASSERT_QUALIFIED: "ASSERT_QUALIFIED",
    LadderLevel.L2_ASSERT_CONDITIONAL: "ASSERT_CONDITIONAL",
    LadderLevel.L3_UNCERTAIN: "UNCERTAIN",
    LadderLevel.L4_ABSTAIN: "ABSTAIN",
}


class SurvivorConsistencyError(Exception):
    """Raised when alternatives_remain_viable is inconsistent with n_survivors."""
    pass


@dataclass
class FragilityIndicators:
    """
    Fragility indicators for auditor decision-making.
    
    v2.5.2: STRICT SEPARATION between BLOCKING and DIAGNOSTIC indicators.
    
    BLOCKING indicators (can prevent assertion when n_survivors == 1):
    - unanimity_contradicted
    - unstable_unanimity  
    - representation_contested
    - alternatives_remain_viable (derived from n_survivors, not set independently)
    
    DIAGNOSTIC indicators (NEVER block assertion, audit/dossier only):
    - fewer_than_three_hard_kills
    - assumption_dependent
    - domain_restricted
    - no_late_recovery
    - heavy_pruning_occurred
    - late_convergence
    - repair_applied
    """
    # === BLOCKING INDICATORS ===
    unanimity_contradicted: bool = False        # Models agreed but later reasoning contradicted
    unstable_unanimity: bool = False            # Unanimity changed across rounds
    representation_contested: bool = False      # Option labels remapped, schema repair altered identity
    alternatives_remain_viable: bool = False    # Derived: n_survivors >= 2 (DO NOT SET DIRECTLY)
    
    # === DIAGNOSTIC INDICATORS (never block assertion) ===
    fewer_than_three_hard_kills: bool = False   # <3 decisive HARD kills (DIAGNOSTIC ONLY)
    assumption_dependent: bool = False          # Agreement depends on unstated assumptions
    domain_restricted: bool = False             # Validity depends on domain assumptions
    no_late_recovery: bool = False              # No epistemic recovery after contradiction
    heavy_pruning_occurred: bool = False        # Significant pruning in early rounds
    late_convergence: bool = False              # Models converged late in pipeline
    repair_applied: bool = False                # Schema or mapping repair was applied
    
    def blocking_list(self) -> List[str]:
        """Return list of BLOCKING indicators only."""
        indicators = []
        if self.unanimity_contradicted:
            indicators.append("unanimity_contradicted")
        if self.unstable_unanimity:
            indicators.append("unstable_unanimity")
        if self.representation_contested:
            indicators.append("representation_contested")
        if self.alternatives_remain_viable:
            indicators.append("alternatives_remain_viable")
        return indicators
    
    def any_blocking_triggered(self) -> bool:
        """Check if any BLOCKING fragility indicator is triggered."""
        return len(self.blocking_list()) > 0
    
    def diagnostic_list(self) -> List[str]:
        """Return list of DIAGNOSTIC indicators only."""
        indicators = []
        if self.fewer_than_three_hard_kills:
            indicators.append("fewer_than_three_hard_kills")
        if self.assumption_dependent:
            indicators.append("assumption_dependent")
        if self.domain_restricted:
            indicators.append("domain_restricted")
        if self.no_late_recovery:
            indicators.append("no_late_recovery")
        if self.heavy_pruning_occurred:
            indicators.append("heavy_pruning_occurred")
        if self.late_convergence:
            indicators.append("late_convergence")
        if self.repair_applied:
            indicators.append("repair_applied")
        return indicators
    
    def triggered_list(self) -> List[str]:
        """Return list of ALL triggered indicators (blocking + diagnostic)."""
        return self.blocking_list() + self.diagnostic_list()
    
    def any_triggered(self) -> bool:
        """Check if any fragility indicator is triggered (for diagnostic/audit purposes)."""
        return len(self.triggered_list()) > 0


@dataclass
class AuditorDecision:
    """
    Complete auditor decision with terminal state, ladder level, and metadata.
    
    v2.5.6: Added ladder_level and confidence_qualifier fields.
    """
    terminal_state: AuditorTerminalState
    asserted_answer: Optional[str]              # The answer being asserted (if any)
    gold_answer: str                            # For classification as CORRECT vs INCORRECT
    justification: str                          # Why this terminal state was chosen
    hard_kill_count: int                        # Number of decisive HARD kills (diagnostic)
    survivors: List[str]                        # Options that survived elimination
    fragility: FragilityIndicators              # Fragility indicator breakdown
    
    # v2.5.1: Fields for improved accounting
    n_survivors: int = 0                        # Count of survivors
    decisive_eliminations: int = 0              # N_INITIAL - n_survivors
    
    # v2.5.3: Track source of authoritative survivors
    survivor_source: str = "unknown"            # Source: post_r2d, kill_aggregation, etc.
    
    # v2.5.6: Ladder level and confidence qualifier
    ladder_level: LadderLevel = LadderLevel.L0_FULL_ASSERT
    confidence_qualifier: Optional[str] = None  # e.g., "unanimous_without_independent_evidence"
    uweb_triggered: bool = False                # Whether UWEB fired (for dossier display)
    
    # Audit trail
    unanimity_at_r1: Optional[str] = None       # What was unanimous at R1 (if any)
    unanimity_at_final: Optional[str] = None    # What was unanimous at Final Commit
    contradiction_detected: bool = False         # Did later reasoning contradict R1?
    resurrection_occurred: bool = False          # Did resurrection testing revive kills?
    
    # v2.5.4: Hard-stop diagnostic flags
    empty_survivors_detected: bool = False       # All options killed → ERROR_EMPTY_SURVIVORS
    asserted_not_in_survivors: bool = False      # Asserted answer not in survivors → WITHHOLD
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        d = {
            "terminal_state": self.terminal_state.value,
            "asserted_answer": self.asserted_answer,
            "gold_answer": self.gold_answer,
            "justification": self.justification,
            "hard_kill_count": self.hard_kill_count,
            "n_survivors": self.n_survivors,
            "decisive_eliminations": self.decisive_eliminations,
            "survivors": self.survivors,
            "survivor_source": self.survivor_source,
            # v2.5.6: Ladder level fields
            "ladder_level": self.ladder_level.value,
            "ladder_level_name": LADDER_LEVEL_NAMES.get(self.ladder_level, "UNKNOWN"),
            "confidence_qualifier": self.confidence_qualifier,
            "uweb_triggered": self.uweb_triggered,
            # Fragility breakdown
            "blocking_indicators": self.fragility.blocking_list(),
            "diagnostic_indicators": self.fragility.diagnostic_list(),
            "fragility_indicators": self.fragility.triggered_list(),  # All (backward compat)
            # Audit trail
            "unanimity_at_r1": self.unanimity_at_r1,
            "unanimity_at_final": self.unanimity_at_final,
            "contradiction_detected": self.contradiction_detected,
            "resurrection_occurred": self.resurrection_occurred,
            "empty_survivors_detected": self.empty_survivors_detected,
            "asserted_not_in_survivors": self.asserted_not_in_survivors,
        }
        return d
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def plain_english_interpretation(self) -> str:
        """
        Generate plain-English interpretation for dossier display.
        
        v2.5.6: Required for paper readability.
        """
        level_name = LADDER_LEVEL_NAMES.get(self.ladder_level, "UNKNOWN")
        
        if self.ladder_level == LadderLevel.L0_FULL_ASSERT:
            return (
                f"FULL_ASSERT: Strong independent evidence supports {self.asserted_answer}. "
                f"Multiple evaluators independently eliminated alternatives through rigorous analysis."
            )
        elif self.ladder_level == LadderLevel.L1_ASSERT_QUALIFIED:
            return (
                f"ASSERT_QUALIFIED: All evaluators agreed on {self.asserted_answer}, but the "
                f"elimination process lacked independent corroborating evidence (e.g., hard kills). "
                f"The consensus may reflect shared reasoning patterns rather than independent verification. "
                f"Assertion made with reduced confidence."
            )
        elif self.ladder_level == LadderLevel.L4_ABSTAIN:
            if self.n_survivors >= 2:
                return (
                    f"WITHHELD: Multiple viable alternatives remain ({self.survivors}). "
                    f"Insufficient evidence to decisively select one answer."
                )
            else:
                blocking = self.fragility.blocking_list()
                return (
                    f"WITHHELD: Structural issues prevent confident assertion: {', '.join(blocking)}. "
                    f"Even with a single survivor, the reasoning process showed instability."
                )
        else:
            return f"{level_name}: {self.justification}"


def count_hard_kills(kill_aggregation: dict) -> int:
    """
    Count the number of HARD (decisive) kills.
    
    A HARD kill is:
    - Confirmed by 2+ evaluators
    - Not downgraded by resurrection
    - Not invalidated by rule library
    
    NOTE (v2.5.1): This count is now DIAGNOSTIC ONLY.
    It does NOT gate assertion eligibility. Use n_survivors instead.
    """
    if not kill_aggregation:
        return 0
    
    confirmed_kills = kill_aggregation.get("confirmed_kills", [])
    downgraded = set(kill_aggregation.get("downgraded_kills", {}).keys())
    invalidated = set(kill_aggregation.get("invalidated_kills", []))
    
    hard_kill_count = 0
    for k in confirmed_kills:
        if isinstance(k, dict):
            option = k.get("option", "")
        else:
            option = k
        
        if option and option not in downgraded and option not in invalidated:
            hard_kill_count += 1
    
    return hard_kill_count


def get_authoritative_survivors(
    kill_aggregation: Optional[dict],
    round2d_results: Optional[dict] = None,
    round2c_results: Optional[dict] = None,
    candidate_options: Optional[List[str]] = None,
) -> Tuple[List[str], str]:
    """
    Get authoritative survivor list in priority order.
    
    v2.5.3: Prevents silent default to 4 survivors by using explicit priority:
    1. Post-R2d survivors (if resurrection modified kill validity)
    2. Post-R2c survivors from kill_aggregation (if R2c ran)
    3. Post-pruning candidate_options (if early rounds narrowed options)
    4. Fallback to ["A", "B", "C", "D"] (only if nothing else available)
    
    Returns:
        (survivors: List[str], source: str)
    """
    # Priority 1: Post-R2d survivors
    if round2d_results:
        summary = round2d_results.get("summary", {})
        downgraded_options = summary.get("downgraded_to_conditions", [])
        confirmed_kills_r2d = summary.get("confirmed_kills", [])
        
        if confirmed_kills_r2d or downgraded_options:
            pre_r2d_survivors = []
            if kill_aggregation:
                pre_r2d_survivors = kill_aggregation.get("survivors", [])
            
            post_r2d_survivors = (set(pre_r2d_survivors) | set(downgraded_options)) - set(confirmed_kills_r2d)
            return sorted(post_r2d_survivors), "post_r2d"
    
    # Priority 2: kill_aggregation survivors
    if kill_aggregation:
        survivors = kill_aggregation.get("survivors")
        if survivors is not None and len(survivors) > 0:
            return list(survivors), "kill_aggregation"
        
        confirmed_kills = kill_aggregation.get("confirmed_kills", [])
        if confirmed_kills:
            all_opts = set(["A", "B", "C", "D"])
            killed_opts = set()
            for k in confirmed_kills:
                if isinstance(k, dict):
                    opt = k.get("option", "")
                else:
                    opt = k
                if opt:
                    killed_opts.add(opt)
            computed_survivors = sorted(all_opts - killed_opts)
            return computed_survivors, "computed_from_kills"
    
    # Priority 3: candidate_options
    if candidate_options and len(candidate_options) > 0:
        return list(candidate_options), "candidate_options"
    
    # Priority 4: Fallback
    return ["A", "B", "C", "D"], "fallback_all"


def validate_survivor_consistency(n_survivors: int, alternatives_remain_viable: bool) -> None:
    """INVARIANT: alternatives_remain_viable == (n_survivors >= 2)"""
    expected = (n_survivors >= 2)
    if alternatives_remain_viable != expected:
        raise SurvivorConsistencyError(
            f"Survivor consistency invariant violated: "
            f"n_survivors={n_survivors}, alternatives_remain_viable={alternatives_remain_viable}"
        )


def check_representation_contested(
    round1_results: dict,
    round2a_results: Optional[dict],
    synthesis_result: Optional[dict],
    ladder_metadata: Optional[dict],
) -> bool:
    """Check if representation was contested during pipeline execution."""
    if ladder_metadata is None:
        ladder_metadata = {}
    
    if ladder_metadata.get("letter_mapping_drift", False):
        return True
    if ladder_metadata.get("drift_prohibition_applied", False):
        return True
    
    if round1_results:
        mapping_val = round1_results.get("mapping_validation", {})
        if mapping_val and not mapping_val.get("all_valid", True):
            return True
    
    if synthesis_result:
        if synthesis_result.get("schema_repair_applied", False):
            if synthesis_result.get("option_remapped", False):
                return True
    
    if round2a_results:
        if round2a_results.get("representation_mismatch", False):
            return True
        if round2a_results.get("rerun_required", False):
            return True
    
    return False


def check_unanimity_stability(
    round1_results: dict,
    final_commit_results: Optional[dict],
    round2c_results: Optional[dict],
    evaluators: List[str]
) -> Tuple[bool, Optional[str], Optional[str], bool]:
    """Check if unanimity existed and whether it remained stable."""
    r1_choices = []
    for eval_name in evaluators:
        eval_result = round1_results.get(f"evaluator_{eval_name}", {})
        choice = eval_result.get("final_choice")
        if choice and choice != "ABSTAIN":
            r1_choices.append(choice)
    
    r1_unanimous = None
    if len(set(r1_choices)) == 1 and len(r1_choices) == len(evaluators):
        r1_unanimous = r1_choices[0]
    
    final_choices = []
    source_results = final_commit_results or round2c_results or round1_results
    
    for eval_name in evaluators:
        eval_result = source_results.get(f"evaluator_{eval_name}", {})
        choice = eval_result.get("final_choice")
        if choice and choice != "ABSTAIN":
            final_choices.append(choice)
    
    final_unanimous = None
    if len(set(final_choices)) == 1 and len(final_choices) == len(evaluators):
        final_unanimous = final_choices[0]
    
    had_unanimity = r1_unanimous is not None or final_unanimous is not None
    stable = r1_unanimous == final_unanimous if r1_unanimous and final_unanimous else True
    
    return had_unanimity, r1_unanimous, final_unanimous, stable


def check_contradiction_in_reasoning(
    round1_results: dict,
    round2c_results: Optional[dict],
    final_commit_results: Optional[dict],
    evaluators: List[str],
    unanimous_choice: Optional[str]
) -> bool:
    """Check if later reasoning contradicted the unanimous choice."""
    if not unanimous_choice:
        return False
    
    if round2c_results:
        kill_aggregation = round2c_results.get("kill_aggregation", {})
        all_kills = kill_aggregation.get("unique_kills", [])
        
        for kill in all_kills:
            if kill.get("option") == unanimous_choice:
                return True
    
    return False


def determine_terminal_state(
    round1_results: dict,
    round2c_results: Optional[dict],
    round2d_results: Optional[dict],
    final_commit_results: Optional[dict],
    round3_results: Optional[dict],
    auditor_result: Optional[dict],
    kill_aggregation: dict,
    gold_answer: str,
    evaluators: List[str],
    ladder_level: int = 3,
    ladder_metadata: dict = None,
    round2a_results: dict = None,
    synthesis_result: dict = None,
    candidate_options: List[str] = None,
) -> AuditorDecision:
    """
    Determine the auditor terminal state based on pipeline results.
    
    v2.5.6 Decision Logic:
    
    CASE A - Strong Evidence:
        n_survivors == 1 AND hard_kill_count >= 2 AND no blocking flags
        → ASSERTED + L0_FULL_ASSERT
    
    CASE B - UWEB Pattern (Weak Consensus):
        R1 unanimous AND n_survivors == 1 AND hard_kill_count < 2 AND fragility present AND no blocking flags
        → ASSERTED + L1_ASSERT_QUALIFIED (not WITHHELD!)
        confidence_qualifier = "unanimous_without_independent_evidence"
    
    CASE C - True Abstention:
        n_survivors >= 2 OR blocking flags (unanimity_contradicted, representation_contested, etc.)
        → WITHHELD + L4_ABSTAIN
    """
    if ladder_metadata is None:
        ladder_metadata = {}
    
    # Initialize fragility indicators
    fragility = FragilityIndicators()
    
    # === DIAGNOSTIC INDICATORS ===
    hard_kill_count = count_hard_kills(kill_aggregation)
    fragility.fewer_than_three_hard_kills = (hard_kill_count < 3)
    
    if ladder_metadata.get("domain_restricted", False):
        fragility.domain_restricted = True
        fragility.assumption_dependent = True
    
    resurrection_occurred = False
    if round2d_results:
        summary = round2d_results.get("summary", {})
        downgraded = summary.get("downgraded_to_conditions", [])
        if downgraded:
            resurrection_occurred = True
            fragility.assumption_dependent = True
    
    if synthesis_result and synthesis_result.get("repair_applied", False):
        fragility.repair_applied = True
    
    # === SURVIVOR COUNT ===
    survivors, survivor_source = get_authoritative_survivors(
        kill_aggregation=kill_aggregation,
        round2d_results=round2d_results,
        round2c_results=round2c_results,
        candidate_options=candidate_options,
    )
    n_survivors = len(survivors)
    decisive_eliminations = N_INITIAL_OPTIONS - n_survivors
    
    fragility.alternatives_remain_viable = (n_survivors >= 2)
    validate_survivor_consistency(n_survivors, fragility.alternatives_remain_viable)
    
    # === BLOCKING INDICATORS ===
    had_unanimity, r1_unanimous, final_unanimous, stability = check_unanimity_stability(
        round1_results, final_commit_results, round2c_results, evaluators
    )
    
    if not stability:
        fragility.unstable_unanimity = True
    
    unanimous_choice = final_unanimous or r1_unanimous
    contradiction_detected = check_contradiction_in_reasoning(
        round1_results, round2c_results, final_commit_results, evaluators, unanimous_choice
    )
    fragility.unanimity_contradicted = contradiction_detected
    
    fragility.representation_contested = check_representation_contested(
        round1_results, round2a_results, synthesis_result, ladder_metadata
    )
    
    # === DETERMINE ASSERTED ANSWER ===
    asserted_answer = None
    if n_survivors == 1:
        asserted_answer = survivors[0]
    elif unanimous_choice:
        asserted_answer = unanimous_choice
    
    # ================================================================
    # TERMINAL STATE DECISION LOGIC (v2.5.6)
    # ================================================================
    
    # CASE 0: Empty survivor set → WITHHOLD with error
    if n_survivors == 0:
        return AuditorDecision(
            terminal_state=AuditorTerminalState.WITHHOLD_ASSERTION,
            asserted_answer=None,
            gold_answer=gold_answer,
            justification="WITHHOLD: ERROR_EMPTY_SURVIVOR_SET - all options eliminated, possible invalid question",
            hard_kill_count=hard_kill_count,
            survivors=[],
            fragility=fragility,
            n_survivors=0,
            decisive_eliminations=N_INITIAL_OPTIONS,
            survivor_source=survivor_source,
            ladder_level=LadderLevel.L4_ABSTAIN,
            confidence_qualifier="error_empty_survivors",
            unanimity_at_r1=r1_unanimous,
            unanimity_at_final=final_unanimous,
            contradiction_detected=contradiction_detected,
            resurrection_occurred=resurrection_occurred,
            empty_survivors_detected=True,
        )
    
    # CASE 0.5: Asserted answer not in survivors → WITHHOLD
    if asserted_answer and asserted_answer not in survivors:
        return AuditorDecision(
            terminal_state=AuditorTerminalState.WITHHOLD_ASSERTION,
            asserted_answer=None,
            gold_answer=gold_answer,
            justification=f"WITHHOLD: ASSERTED_NOT_IN_SURVIVORS - {asserted_answer} not in authoritative survivors {survivors}",
            hard_kill_count=hard_kill_count,
            survivors=survivors,
            fragility=fragility,
            n_survivors=n_survivors,
            decisive_eliminations=decisive_eliminations,
            survivor_source=survivor_source,
            ladder_level=LadderLevel.L4_ABSTAIN,
            confidence_qualifier="asserted_not_in_survivors",
            unanimity_at_r1=r1_unanimous,
            unanimity_at_final=final_unanimous,
            contradiction_detected=contradiction_detected,
            resurrection_occurred=resurrection_occurred,
            asserted_not_in_survivors=True,
        )
    
    # CASE 1: Single survivor
    if n_survivors == 1:
        asserted_answer = survivors[0]
        
        # Check BLOCKING flags (not diagnostics)
        blocking_flags = []
        if fragility.unanimity_contradicted:
            blocking_flags.append("unanimity_contradicted")
        if fragility.unstable_unanimity:
            blocking_flags.append("unstable_unanimity")
        if fragility.representation_contested:
            blocking_flags.append("representation_contested")
        
        # If blocking flags → TRUE ABSTENTION (Case C)
        if blocking_flags:
            return AuditorDecision(
                terminal_state=AuditorTerminalState.WITHHOLD_ASSERTION,
                asserted_answer=asserted_answer,  # Still record preference
                gold_answer=gold_answer,
                justification=f"WITHHOLD: single survivor {asserted_answer} blocked by: {', '.join(blocking_flags)}",
                hard_kill_count=hard_kill_count,
                survivors=survivors,
                fragility=fragility,
                n_survivors=n_survivors,
                decisive_eliminations=decisive_eliminations,
                survivor_source=survivor_source,
                ladder_level=LadderLevel.L4_ABSTAIN,
                confidence_qualifier="blocking_flags_present",
                unanimity_at_r1=r1_unanimous,
                unanimity_at_final=final_unanimous,
                contradiction_detected=contradiction_detected,
                resurrection_occurred=resurrection_occurred,
            )
        
        # ================================================================
        # UWEB CHECK (v2.5.6): Now DOWNGRADES instead of BLOCKING
        # ================================================================
        # UWEB detects weak consensus, not unknowability.
        # Weak consensus lowers commitment; only true ambiguity withholds.
        # ================================================================
        
        uweb_triggered = False
        uweb_reason = None
        
        if r1_unanimous is not None:  # R1 was unanimous
            # Check for INDEPENDENT EVIDENCE
            has_hard_kill_evidence = (hard_kill_count >= 2)
            
            early_pruning_sources = {"candidate_options"}
            has_decisive_pruning_evidence = (
                decisive_eliminations == 3 and
                survivor_source in early_pruning_sources and
                not fragility.representation_contested and
                not fragility.unanimity_contradicted
            )
            
            has_independent_evidence = has_hard_kill_evidence or has_decisive_pruning_evidence
            
            if not has_independent_evidence:
                # Check for fragility indicators (excluding repair_applied alone)
                fragility_present = (
                    fragility.fewer_than_three_hard_kills or
                    fragility.assumption_dependent or
                    fragility.domain_restricted
                )
                if fragility_present:
                    uweb_triggered = True
                    uweb_reason = f"R1 unanimous on {r1_unanimous}, sole survivor {asserted_answer}, but only {hard_kill_count} hard kills"
        
        # Determine ladder level and terminal state
        if uweb_triggered:
            # ================================================================
            # v2.5.6: UWEB → ASSERT_QUALIFIED (not WITHHOLD!)
            # ================================================================
            ladder = LadderLevel.L1_ASSERT_QUALIFIED
            qualifier = "unanimous_without_independent_evidence"
            justification = (
                f"ASSERT_QUALIFIED: unanimous R1 consensus on {asserted_answer}, sole survivor after elimination, "
                f"but no independent eliminative evidence ({hard_kill_count} hard kills). "
                f"Assertion made with reduced confidence."
            )
        else:
            # Strong evidence → FULL_ASSERT
            ladder = LadderLevel.L0_FULL_ASSERT
            qualifier = None
            justification = (
                f"Decisive elimination: {decisive_eliminations} options eliminated, "
                f"sole survivor {asserted_answer} (hard_kills={hard_kill_count}, source={survivor_source})"
            )
        
        # Determine CORRECT vs INCORRECT
        if asserted_answer == gold_answer:
            return AuditorDecision(
                terminal_state=AuditorTerminalState.ASSERT_CORRECT,
                asserted_answer=asserted_answer,
                gold_answer=gold_answer,
                justification=justification,
                hard_kill_count=hard_kill_count,
                survivors=survivors,
                fragility=fragility,
                n_survivors=n_survivors,
                decisive_eliminations=decisive_eliminations,
                survivor_source=survivor_source,
                ladder_level=ladder,
                confidence_qualifier=qualifier,
                uweb_triggered=uweb_triggered,
                unanimity_at_r1=r1_unanimous,
                unanimity_at_final=final_unanimous,
                contradiction_detected=contradiction_detected,
                resurrection_occurred=resurrection_occurred,
            )
        else:
            return AuditorDecision(
                terminal_state=AuditorTerminalState.ASSERT_INCORRECT,
                asserted_answer=asserted_answer,
                gold_answer=gold_answer,
                justification=justification + f" (≠ gold {gold_answer})",
                hard_kill_count=hard_kill_count,
                survivors=survivors,
                fragility=fragility,
                n_survivors=n_survivors,
                decisive_eliminations=decisive_eliminations,
                survivor_source=survivor_source,
                ladder_level=ladder,
                confidence_qualifier=qualifier,
                uweb_triggered=uweb_triggered,
                unanimity_at_r1=r1_unanimous,
                unanimity_at_final=final_unanimous,
                contradiction_detected=contradiction_detected,
                resurrection_occurred=resurrection_occurred,
            )
    
    # CASE 2: Multiple survivors but epistemic unanimity without BLOCKING fragility
    # (Rare case - alternatives_remain_viable is blocking when n_survivors > 1)
    if n_survivors > 1 and unanimous_choice and not fragility.any_blocking_triggered():
        ladder = LadderLevel.L1_ASSERT_QUALIFIED
        if unanimous_choice == gold_answer:
            return AuditorDecision(
                terminal_state=AuditorTerminalState.ASSERT_CORRECT,
                asserted_answer=unanimous_choice,
                gold_answer=gold_answer,
                justification=f"Epistemic unanimity: {unanimous_choice} matches gold ({n_survivors} survivors)",
                hard_kill_count=hard_kill_count,
                survivors=survivors,
                fragility=fragility,
                n_survivors=n_survivors,
                decisive_eliminations=decisive_eliminations,
                survivor_source=survivor_source,
                ladder_level=ladder,
                unanimity_at_r1=r1_unanimous,
                unanimity_at_final=final_unanimous,
                contradiction_detected=contradiction_detected,
                resurrection_occurred=resurrection_occurred,
            )
        else:
            return AuditorDecision(
                terminal_state=AuditorTerminalState.ASSERT_INCORRECT,
                asserted_answer=unanimous_choice,
                gold_answer=gold_answer,
                justification=f"Epistemic unanimity: {unanimous_choice} ≠ gold {gold_answer}",
                hard_kill_count=hard_kill_count,
                survivors=survivors,
                fragility=fragility,
                n_survivors=n_survivors,
                decisive_eliminations=decisive_eliminations,
                survivor_source=survivor_source,
                ladder_level=ladder,
                unanimity_at_r1=r1_unanimous,
                unanimity_at_final=final_unanimous,
                contradiction_detected=contradiction_detected,
                resurrection_occurred=resurrection_occurred,
            )
    
    # CASE 3: TRUE ABSTENTION - multiple survivors or blocking fragility
    blocking_parts = fragility.blocking_list()
    diagnostic_parts = fragility.diagnostic_list()
    
    justification_parts = []
    if blocking_parts:
        justification_parts.append(f"blocking: {', '.join(blocking_parts)}")
    if diagnostic_parts:
        justification_parts.append(f"diagnostic: {', '.join(diagnostic_parts)}")
    
    if not justification_parts:
        justification_parts.append("epistemic conditions for assertion not met")
    
    return AuditorDecision(
        terminal_state=AuditorTerminalState.WITHHOLD_ASSERTION,
        asserted_answer=asserted_answer,  # Record preference even when withholding
        gold_answer=gold_answer,
        justification="WITHHOLD: " + "; ".join(justification_parts),
        hard_kill_count=hard_kill_count,
        survivors=survivors,
        fragility=fragility,
        n_survivors=n_survivors,
        decisive_eliminations=decisive_eliminations,
        survivor_source=survivor_source,
        ladder_level=LadderLevel.L4_ABSTAIN,
        confidence_qualifier="alternatives_remain_viable" if n_survivors >= 2 else "blocking_conditions",
        unanimity_at_r1=r1_unanimous,
        unanimity_at_final=final_unanimous,
        contradiction_detected=contradiction_detected,
        resurrection_occurred=resurrection_occurred,
    )


def perform_fragile_unanimity_check(
    round1_results: dict,
    round2c_results: Optional[dict],
    final_commit_results: Optional[dict],
    kill_aggregation: dict,
    evaluators: List[str],
) -> Tuple[bool, List[str]]:
    """
    Fragile Unanimity Abstention Check (Auditor Semantics).
    
    v2.5.2: This check uses BLOCKING indicators only.
    """
    survivors = kill_aggregation.get("survivors", ["A", "B", "C", "D"])
    n_survivors = len(survivors)
    
    if n_survivors == 1:
        return False, ["single_survivor_overrides_fragility"]
    
    had_unanimity, r1_unanimous, final_unanimous, stable = check_unanimity_stability(
        round1_results, final_commit_results, round2c_results, evaluators
    )
    
    if not had_unanimity:
        return False, []
    
    unanimous_choice = final_unanimous or r1_unanimous
    blocking_reasons = []
    
    contradiction = check_contradiction_in_reasoning(
        round1_results, round2c_results, final_commit_results, evaluators, unanimous_choice
    )
    if contradiction:
        blocking_reasons.append("unanimity_contradicted")
    
    if not stable:
        blocking_reasons.append("unstable_unanimity")
    
    if n_survivors >= 2:
        blocking_reasons.append("alternatives_remain_viable")
    
    if blocking_reasons:
        return True, blocking_reasons
    
    return False, []


# ============================================================
# Legacy Mapping (for backward compatibility)
# ============================================================

LEGACY_DISPOSITION_MAPPING = {
    "AUTO_ACCEPT": lambda gold, choice: AuditorTerminalState.ASSERT_CORRECT if choice == gold else AuditorTerminalState.ASSERT_INCORRECT,
    "ASSERT_QUALIFIED": lambda gold, choice: AuditorTerminalState.ASSERT_CORRECT if choice == gold else AuditorTerminalState.ASSERT_INCORRECT,
    "FLAG_FALSE_CONSENSUS": lambda gold, choice: AuditorTerminalState.WITHHOLD_ASSERTION,
    "FLAG_EPISTEMIC_BOUNDARY": lambda gold, choice: AuditorTerminalState.WITHHOLD_ASSERTION,
    "UNPROVEN_CONVERGENCE": lambda gold, choice: AuditorTerminalState.WITHHOLD_ASSERTION,
    "NEEDS_REVIEW": lambda gold, choice: AuditorTerminalState.WITHHOLD_ASSERTION,
    "ABSTAIN": lambda gold, choice: AuditorTerminalState.WITHHOLD_ASSERTION,
    "SPLIT_PERSISTS": lambda gold, choice: AuditorTerminalState.WITHHOLD_ASSERTION,
}


def map_legacy_disposition(legacy_disposition: str, gold_answer: str, asserted_answer: Optional[str]) -> AuditorTerminalState:
    """Map legacy disposition strings to new terminal states."""
    mapper = LEGACY_DISPOSITION_MAPPING.get(legacy_disposition)
    if mapper:
        return mapper(gold_answer, asserted_answer)
    return AuditorTerminalState.WITHHOLD_ASSERTION


# ============================================================
# Test / Validation
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("CAM Auditor Terminal States v2.5.6 - Ladder Remap Validation")
    print("=" * 70)
    
    # Test 1: Single survivor with strong evidence (2+ hard kills) -> L0_FULL_ASSERT
    print("\nTest 1: Single survivor with 2+ hard kills -> L0_FULL_ASSERT")
    print("-" * 50)
    
    test_r1 = {
        "evaluator_A": {"final_choice": "C"},
        "evaluator_B": {"final_choice": "C"},
        "evaluator_C": {"final_choice": "C"},
        "evaluator_D": {"final_choice": "C"},
    }
    
    test_kill_agg = {
        "confirmed_kills": ["A", "B"],
        "survivors": ["C"],
    }
    
    decision = determine_terminal_state(
        round1_results=test_r1,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation=test_kill_agg,
        gold_answer="C",
        evaluators=["A", "B", "C", "D"],
    )
    
    print(f"Terminal State: {decision.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision.ladder_level]}")
    print(f"UWEB Triggered: {decision.uweb_triggered}")
    print(f"Confidence Qualifier: {decision.confidence_qualifier}")
    assert decision.terminal_state == AuditorTerminalState.ASSERT_CORRECT
    assert decision.ladder_level == LadderLevel.L0_FULL_ASSERT
    assert decision.uweb_triggered == False
    print("✓ PASS: Strong evidence -> L0_FULL_ASSERT")
    
    # Test 2: UWEB pattern -> L1_ASSERT_QUALIFIED (NOT WITHHOLD!)
    print("\nTest 2: UWEB pattern -> L1_ASSERT_QUALIFIED (not WITHHOLD)")
    print("-" * 50)
    
    test_kill_agg_uweb = {
        "confirmed_kills": [{"option": "A"}],
        "survivors": ["C"],
    }
    
    decision_uweb = determine_terminal_state(
        round1_results=test_r1,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation=test_kill_agg_uweb,
        gold_answer="C",
        evaluators=["A", "B", "C", "D"],
    )
    
    print(f"Terminal State: {decision_uweb.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision_uweb.ladder_level]}")
    print(f"UWEB Triggered: {decision_uweb.uweb_triggered}")
    print(f"Confidence Qualifier: {decision_uweb.confidence_qualifier}")
    print(f"Justification: {decision_uweb.justification}")
    
    # KEY ASSERTION: UWEB now produces ASSERT_CORRECT, not WITHHOLD!
    assert decision_uweb.terminal_state == AuditorTerminalState.ASSERT_CORRECT, \
        f"Expected ASSERT_CORRECT, got {decision_uweb.terminal_state.value}"
    assert decision_uweb.ladder_level == LadderLevel.L1_ASSERT_QUALIFIED
    assert decision_uweb.uweb_triggered == True
    assert decision_uweb.confidence_qualifier == "unanimous_without_independent_evidence"
    assert decision_uweb.asserted_answer == "C"
    print("✓ PASS: UWEB pattern -> L1_ASSERT_QUALIFIED (ASSERTED, not WITHHELD)")
    
    # Test 3: UWEB with wrong answer -> L1_ASSERT_INCORRECT
    print("\nTest 3: UWEB with wrong answer -> L1_ASSERT_INCORRECT")
    print("-" * 50)
    
    decision_uweb_wrong = determine_terminal_state(
        round1_results=test_r1,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation=test_kill_agg_uweb,
        gold_answer="D",  # Gold is D, asserted is C
        evaluators=["A", "B", "C", "D"],
    )
    
    print(f"Terminal State: {decision_uweb_wrong.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision_uweb_wrong.ladder_level]}")
    print(f"UWEB Triggered: {decision_uweb_wrong.uweb_triggered}")
    
    assert decision_uweb_wrong.terminal_state == AuditorTerminalState.ASSERT_INCORRECT
    assert decision_uweb_wrong.ladder_level == LadderLevel.L1_ASSERT_QUALIFIED
    assert decision_uweb_wrong.uweb_triggered == True
    print("✓ PASS: UWEB wrong -> L1_ASSERT_INCORRECT (flagged as qualified)")
    
    # Test 4: True abstention (blocking flag) -> L4_ABSTAIN
    print("\nTest 4: Blocking flag -> L4_ABSTAIN (WITHHOLD)")
    print("-" * 50)
    
    decision_blocked = determine_terminal_state(
        round1_results=test_r1,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation=test_kill_agg,
        gold_answer="C",
        evaluators=["A", "B", "C", "D"],
        ladder_metadata={"letter_mapping_drift": True},  # Triggers representation_contested
    )
    
    print(f"Terminal State: {decision_blocked.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision_blocked.ladder_level]}")
    print(f"Blocking Indicators: {decision_blocked.fragility.blocking_list()}")
    
    assert decision_blocked.terminal_state == AuditorTerminalState.WITHHOLD_ASSERTION
    assert decision_blocked.ladder_level == LadderLevel.L4_ABSTAIN
    assert "representation_contested" in decision_blocked.fragility.blocking_list()
    print("✓ PASS: Blocking flag -> L4_ABSTAIN (WITHHELD)")
    
    # Test 5: Multiple survivors -> L4_ABSTAIN
    print("\nTest 5: Multiple survivors -> L4_ABSTAIN (WITHHOLD)")
    print("-" * 50)
    
    test_kill_agg_multi = {
        "confirmed_kills": ["A"],
        "survivors": ["B", "C", "D"],
    }
    
    decision_multi = determine_terminal_state(
        round1_results=test_r1,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation=test_kill_agg_multi,
        gold_answer="C",
        evaluators=["A", "B", "C", "D"],
    )
    
    print(f"Terminal State: {decision_multi.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision_multi.ladder_level]}")
    print(f"n_survivors: {decision_multi.n_survivors}")
    
    assert decision_multi.terminal_state == AuditorTerminalState.WITHHOLD_ASSERTION
    assert decision_multi.ladder_level == LadderLevel.L4_ABSTAIN
    assert decision_multi.n_survivors == 3
    print("✓ PASS: Multiple survivors -> L4_ABSTAIN (WITHHELD)")
    
    # Test 6: Split R1 (not unanimous) bypasses UWEB -> L0_FULL_ASSERT
    print("\nTest 6: Split R1 bypasses UWEB -> L0_FULL_ASSERT")
    print("-" * 50)
    
    test_r1_split = {
        "evaluator_A": {"final_choice": "C"},
        "evaluator_B": {"final_choice": "C"},
        "evaluator_C": {"final_choice": "C"},
        "evaluator_D": {"final_choice": "B"},  # Dissenter
    }
    
    decision_split = determine_terminal_state(
        round1_results=test_r1_split,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation=test_kill_agg_uweb,  # Only 1 hard kill
        gold_answer="C",
        evaluators=["A", "B", "C", "D"],
    )
    
    print(f"Terminal State: {decision_split.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision_split.ladder_level]}")
    print(f"UWEB Triggered: {decision_split.uweb_triggered}")
    print(f"R1 Unanimous: {decision_split.unanimity_at_r1}")
    
    assert decision_split.terminal_state == AuditorTerminalState.ASSERT_CORRECT
    assert decision_split.ladder_level == LadderLevel.L0_FULL_ASSERT
    assert decision_split.uweb_triggered == False
    assert decision_split.unanimity_at_r1 is None
    print("✓ PASS: Split R1 bypasses UWEB -> L0_FULL_ASSERT")
    
    # Test 7: Early pruning (candidate_options) bypasses UWEB -> L0_FULL_ASSERT
    print("\nTest 7: Early pruning bypasses UWEB -> L0_FULL_ASSERT")
    print("-" * 50)
    
    decision_pruned = determine_terminal_state(
        round1_results=test_r1,
        round2c_results=None,
        round2d_results=None,
        final_commit_results=None,
        round3_results=None,
        auditor_result=None,
        kill_aggregation={},  # Empty
        gold_answer="C",
        evaluators=["A", "B", "C", "D"],
        candidate_options=["C"],  # Early pruning to single candidate
    )
    
    print(f"Terminal State: {decision_pruned.terminal_state.value}")
    print(f"Ladder Level: {LADDER_LEVEL_NAMES[decision_pruned.ladder_level]}")
    print(f"UWEB Triggered: {decision_pruned.uweb_triggered}")
    print(f"Survivor Source: {decision_pruned.survivor_source}")
    
    assert decision_pruned.terminal_state == AuditorTerminalState.ASSERT_CORRECT
    assert decision_pruned.ladder_level == LadderLevel.L0_FULL_ASSERT
    assert decision_pruned.uweb_triggered == False
    assert decision_pruned.survivor_source == "candidate_options"
    print("✓ PASS: Early pruning bypasses UWEB -> L0_FULL_ASSERT")
    
    # Test 8: Plain English interpretation
    print("\nTest 8: Plain English interpretation")
    print("-" * 50)
    
    print("\nL0_FULL_ASSERT interpretation:")
    print(decision.plain_english_interpretation())
    
    print("\nL1_ASSERT_QUALIFIED interpretation:")
    print(decision_uweb.plain_english_interpretation())
    
    print("\nL4_ABSTAIN interpretation (multi-survivor):")
    print(decision_multi.plain_english_interpretation())
    
    # Test 9: to_dict includes ladder fields
    print("\nTest 9: to_dict includes ladder fields")
    print("-" * 50)
    
    d = decision_uweb.to_dict()
    assert "ladder_level" in d
    assert "ladder_level_name" in d
    assert "confidence_qualifier" in d
    assert "uweb_triggered" in d
    assert d["ladder_level"] == 1
    assert d["ladder_level_name"] == "ASSERT_QUALIFIED"
    assert d["uweb_triggered"] == True
    print(f"ladder_level: {d['ladder_level']}")
    print(f"ladder_level_name: {d['ladder_level_name']}")
    print(f"confidence_qualifier: {d['confidence_qualifier']}")
    print(f"uweb_triggered: {d['uweb_triggered']}")
    print("✓ PASS: to_dict includes all ladder fields")
    
    print("\n" + "=" * 70)
    print("All v2.5.6 tests passed!")
    print("=" * 70)
    print("\nKEY CHANGE SUMMARY:")
    print("- UWEB no longer forces WITHHOLD")
    print("- UWEB now produces ASSERT + L1_ASSERT_QUALIFIED")
    print("- WITHHOLD reserved for true underdetermination (blocking flags, multiple survivors)")
    print("- Ladder level clearly distinguishes confidence in dossier")
