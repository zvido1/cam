#!/usr/bin/env python3
"""
Build GPQA Dossier v3 - Forensic HTML report for GPQA evaluation results

CRITICAL UPDATE (v3): Terminal State Semantics
- Correctly distinguishes ASSERTED vs WITHHELD vs ERROR terminal states
- Only counts Correct/Wrong for ASSERTED outcomes
- WITHHELD outcomes counted separately (not as correct/wrong)
- Shows both "Asserted Accuracy" and "Preference Accuracy (diagnostic)"
- R2d schema adapter (killed_option -> option mapping)

Supports both v1 and v2 pipeline outputs.
"""

import json
import html as html_lib
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Optional, Dict, Tuple, List

# Import authoritative survivor computation for consistency with auditor
try:
    from cam.adapters.gpqa.auditor_terminal_states import get_authoritative_survivors
    AUDITOR_SURVIVORS_AVAILABLE = True
except ImportError:
    AUDITOR_SURVIVORS_AVAILABLE = False
    get_authoritative_survivors = None

DEFAULT_EVALUATORS = ["A", "B", "C", "D"]
MIN_VALID_EVALUATORS = 3

# =============================================================================
# R2d Resurrection Result Semantics (CRITICAL - DO NOT INVERT)
# =============================================================================
# The resurrection_result field indicates whether the RESURRECTION ATTEMPT succeeded:
#   - "failure" = Resurrection FAILED → Kill is CONFIRMED (option stays dead)
#   - "success" = Resurrection SUCCEEDED → Kill is DOWNGRADED to soft condition (option revived)
#
# Think of it as: "Did the defense attorney succeed in saving the condemned?"
#   - failure = defense failed, execution proceeds (confirmed_kill)
#   - success = defense succeeded, sentence commuted (downgraded_to_condition)
# =============================================================================
R2D_RESURRECTION_FAILED = "failure"    # Kill confirmed - option eliminated
R2D_RESURRECTION_SUCCESS = "success"   # Kill downgraded - option revived

# =============================================================================
# Canonical Candidate Sets (per pipeline stage)
# =============================================================================
def extract_candidate_sets(record: dict) -> dict:
    """
    Extract canonical candidate sets at each pipeline stage.
    Returns dict with keys:
      - initial: always A,B,C,D
      - post_pruning: after R1.5 cheap elimination
      - post_r2c: after R2c kill shots (survivors)
      - post_r2d: after R2d resurrection testing
      - final: what the system preference is based on
    """
    sets = {
        "initial": ["A", "B", "C", "D"],
        "post_pruning": None,
        "post_r2c": None,
        "post_r2d": None,
        "final": None,
    }
    
    # Post-pruning (R1.5)
    sets["post_pruning"] = (
        record.get("post_pruning_candidates") or
        record.get("candidate_options") or
        record.get("cheap_elim_survivors") or
        sets["initial"]
    )
    
    # Post-R2c and Post-R2d: Use authoritative survivor computation for consistency
    r2c = record.get("round2c", {})
    r2d = record.get("round2d", {})
    ka = r2c.get("kill_aggregation", {}) if r2c else record.get("kill_aggregation", {})
    
    # Use unified get_authoritative_survivors if available
    if AUDITOR_SURVIVORS_AVAILABLE and get_authoritative_survivors:
        # Get authoritative survivors (same function used by auditor terminal state)
        authoritative_survivors, survivor_source = get_authoritative_survivors(
            kill_aggregation=ka,
            round2d_results=r2d if r2d else None,
            round2c_results=r2c if r2c else None,
            candidate_options=sets["post_pruning"]
        )
        
        # For post_r2c, we need survivors BEFORE r2d resurrection
        if ka.get("survivors"):
            sets["post_r2c"] = ka["survivors"]
        else:
            sets["post_r2c"] = sets["post_pruning"]
        
        # For post_r2d, use the authoritative computation
        sets["post_r2d"] = authoritative_survivors
        sets["_survivor_source"] = survivor_source  # Track provenance for debugging
    else:
        # Fallback: manual computation (legacy behavior)
        if r2c:
            if ka.get("survivors"):
                sets["post_r2c"] = ka["survivors"]
            else:
                sets["post_r2c"] = sets["post_pruning"]
        else:
            sets["post_r2c"] = sets["post_pruning"]
        
        if r2d:
            summary = r2d.get("summary", {})
            confirmed_kills = summary.get("confirmed_kills", [])
            downgraded = summary.get("downgraded_to_conditions", [])
            post_r2d = [opt for opt in sets["post_r2c"] if opt not in confirmed_kills]
            for opt in downgraded:
                if opt not in post_r2d:
                    post_r2d.append(opt)
            sets["post_r2d"] = sorted(post_r2d)
        else:
            sets["post_r2d"] = sets["post_r2c"]
        sets["_survivor_source"] = "legacy_fallback"
    
    # Final set (what preference is drawn from)
    sets["final"] = sets["post_r2d"]
    
    return sets


def get_ladder_display_sets(record: dict) -> Tuple[List[str], str]:
    """
    Get authoritative survivors/kills for ladder display.
    Priority: auditor_decision.survivors > computed post_r2d fields
    Returns (authoritative_survivors, source_description)
    """
    # Priority 1: auditor_decision (same source terminal state uses)
    auditor_decision = record.get("auditor_decision", {})
    if auditor_decision:
        auth_survivors = auditor_decision.get("survivors")
        auth_source = auditor_decision.get("survivor_source", "auditor_decision")
        if auth_survivors is not None:  # Could be empty list, which is valid
            return auth_survivors, f"auditor ({auth_source})"
    
    # Priority 2: Computed fields in record
    for field in ["post_r2d_survivors", "post_r2c_survivors", "kill_aggregation"]:
        if field == "kill_aggregation":
            ka = record.get("kill_aggregation", {}) or record.get("round2c", {}).get("kill_aggregation", {})
            if ka and "survivors" in ka:
                return ka["survivors"], "kill_aggregation"
        else:
            val = record.get(field)
            if val is not None:
                return val, field
    
    # Priority 3: Fallback to ladder's own survivors (last resort)
    ladder = record.get("system_ladder", {}) or record.get("final_commit", {}).get("system_ladder", {})
    if ladder and "survivors" in ladder:
        return ladder["survivors"], "ladder_fallback"
    
    return [], "none_found"


def check_ladder_consistency(record: dict, candidate_sets: dict) -> dict:
    """
    Check if system_ladder survivors match the authoritative survivors.
    Returns dict with 'consistent' bool, 'details' string, and override info.
    """
    ladder = record.get("system_ladder", {}) or record.get("final_commit", {}).get("system_ladder", {})
    if not ladder:
        return {"consistent": True, "details": "No ladder present", "overridden": False}
    
    ladder_survivors = set(ladder.get("survivors", []))
    
    # Get authoritative survivors (same as what auditor uses)
    auth_survivors, auth_source = get_ladder_display_sets(record)
    auth_survivors_set = set(auth_survivors)
    
    if ladder_survivors == auth_survivors_set:
        return {
            "consistent": True, 
            "details": "Ladder matches authoritative survivors",
            "overridden": False,
            "authoritative_survivors": auth_survivors,
            "authoritative_source": auth_source,
        }
    
    # Mismatch - ladder will be overridden
    return {
        "consistent": False,
        "details": f"Ladder internal survivors overridden by authoritative survivors (source: {auth_source})",
        "overridden": True,
        "ladder_survivors": list(ladder_survivors),
        "authoritative_survivors": auth_survivors,
        "authoritative_source": auth_source,
    }


# =============================================================================
# PART A: Canonical Terminal States
# =============================================================================
def get_canonical_terminal_state(record: dict) -> str:
    """Extract canonical terminal state: ASSERTED, WITHHELD, or ERROR"""
    auditor_ts = record.get("auditor_terminal_state")
    if auditor_ts:
        if auditor_ts in ("WITHHOLD_ASSERTION", "WITHHELD"):
            return "WITHHELD"
        elif auditor_ts in ("ASSERT_CORRECT", "ASSERT_INCORRECT", "ASSERTED"):
            return "ASSERTED"
        elif auditor_ts in ("ERROR", "INVALID"):
            return "ERROR"
    
    auditor_decision = record.get("auditor_decision", {})
    if auditor_decision:
        ts = auditor_decision.get("terminal_state")
        if ts:
            if ts in ("WITHHOLD_ASSERTION", "WITHHELD"):
                return "WITHHELD"
            elif ts in ("ASSERT_CORRECT", "ASSERT_INCORRECT", "ASSERTED"):
                return "ASSERTED"
    
    auditor_result = record.get("auditor_result", {})
    if auditor_result and auditor_result.get("decision") == "ABSTAIN":
        return "WITHHELD"
    
    if record.get("_schema_validation_failed") or record.get("pipeline_error"):
        return "ERROR"
    
    disp = record.get("final_disposition", "")
    if disp in ("ABSTAIN", "INVALID_QUESTION", "FLAG_EPISTEMIC_BOUNDARY"):
        return "WITHHELD"
    elif disp:
        return "ASSERTED"
    
    return "UNKNOWN"


def get_system_preference(record: dict) -> Optional[str]:
    """Get what the system would have chosen (preference), for diagnostic display only."""
    fc = record.get("final_commit", {})
    if fc:
        answer = fc.get("final_answer") or fc.get("final_unanimous_choice") or fc.get("final_majority_choice")
        if answer:
            return answer
    
    auditor_decision = record.get("auditor_decision", {})
    if auditor_decision:
        answer = auditor_decision.get("asserted_answer")
        if answer:
            return answer
    
    r1 = record.get("round1", {})
    choices = []
    for key, value in r1.items():
        if key.startswith("evaluator_") and isinstance(value, dict):
            choice = value.get("final_choice")
            if choice and choice != "ABSTAIN":
                choices.append(choice)
    if choices:
        counts = Counter(choices)
        if counts:
            return counts.most_common(1)[0][0]
    return None


# =============================================================================
# Utility Functions
# =============================================================================
def escape_html(text: str) -> str:
    if not text:
        return ""
    return html_lib.escape(str(text))

def truncate(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) > max_len:
        return escape_html(text[:max_len]) + "..."
    return escape_html(text)

def detect_evaluators_from_records(records: List[dict]) -> List[str]:
    evaluator_set = set()
    for record in records:
        round1 = record.get("round1", {})
        round2c = record.get("round2c") or {}
        for key in list(round1.keys()) + list(round2c.keys()):
            if key.startswith("evaluator_"):
                eval_id = key.replace("evaluator_", "")
                if eval_id in ["A", "B", "C", "D"]:
                    evaluator_set.add(eval_id)
    return sorted(evaluator_set) if evaluator_set else DEFAULT_EVALUATORS


def compute_agreement_pattern_from_choices(choices: Dict[str, Optional[str]], parse_ok: Dict[str, bool], evaluators: List[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
    if evaluators is None:
        evaluators = DEFAULT_EVALUATORS
    valid_choices = [choices[en] for en in evaluators if parse_ok.get(en, False) and choices.get(en) and choices[en] != "ABSTAIN"]
    num_valid = len(valid_choices)
    
    if num_valid < MIN_VALID_EVALUATORS:
        return "INSUFFICIENT_EVALUATORS", None, None
    
    choice_counts = Counter(valid_choices)
    unique_choices = len(choice_counts)
    if unique_choices == 1:
        unanimous = list(choice_counts.keys())[0]
        return f"unanimous_{num_valid}", unanimous, unanimous
    
    majority = choice_counts.most_common(1)[0][0] if choice_counts else None
    counts_list = sorted(choice_counts.values(), reverse=True)
    pattern = "split_" + "_".join(str(c) for c in counts_list)
    
    if len(counts_list) >= 2 and counts_list[0] > counts_list[1]:
        return pattern, majority, None
    else:
        return pattern, None, None


def is_evaluator_quarantined(eval_result: dict) -> bool:
    if not eval_result:
        return True
    if eval_result.get("_response_quarantined", False):
        return True
    if eval_result.get("_schema_validation_failed", False):
        return True
    quarantine_records = eval_result.get("_quarantine_records", [])
    critical_quarantines = [r for r in quarantine_records 
                          if r.get("field", "").startswith(("elimination_audit", "best_current_case", "final_choice"))
                          and r.get("issue") in ("missing_required_object", "null_value", "invalid_choice")]
    return bool(critical_quarantines)


def compute_round_correctness(round_data: dict, gold_answer: str, round_name: str = "round1", evaluators: List[str] = None) -> Dict:
    if evaluators is None:
        evaluators = DEFAULT_EVALUATORS
    choices, parse_ok, correctness, quarantined = {}, {}, {}, {}
    correct_count = 0
    included_evaluators = []
    excluded_evaluators = []
    
    for eval_name in evaluators:
        eval_result = round_data.get(f"evaluator_{eval_name}")
        choice = eval_result.get("final_choice") if eval_result else None
        choices[eval_name] = choice
        
        is_quarantined = is_evaluator_quarantined(eval_result)
        quarantined[eval_name] = is_quarantined
        
        is_failed = False
        if eval_result and eval_result.get("_evaluator_status") == "FAILED":
            is_failed = True
        
        stored_parse_ok = round_data.get(f"parse_ok_{eval_name}")
        if stored_parse_ok is not None:
            parse_ok[eval_name] = stored_parse_ok
        else:
            parse_ok[eval_name] = (choice is not None) and (not is_quarantined) and (not is_failed)
        
        if not parse_ok[eval_name]:
            excluded_evaluators.append(eval_name)
        else:
            included_evaluators.append(eval_name)
        
        is_correct = (choice == gold_answer) if choice and gold_answer else False
        correctness[eval_name] = is_correct
        if is_correct and parse_ok[eval_name]:
            correct_count += 1
    
    pattern, majority, unanimous = compute_agreement_pattern_from_choices(choices, parse_ok, evaluators)
    return {
        "choices": choices, "parse_ok": parse_ok, "quarantined": quarantined,
        "correctness": correctness, "correct_count": correct_count, 
        "agreement_pattern": pattern, "majority_choice": majority, 
        "unanimous_choice": unanimous, "included_evaluators": included_evaluators,
        "excluded_evaluators": excluded_evaluators,
    }


# =============================================================================
# Three-State Round Status
# =============================================================================
def get_round2c_status(record: dict) -> str:
    r2c = record.get("round2c")
    if r2c:
        return "EXECUTED"
    candidates = record.get("post_pruning_candidates") or record.get("candidate_options", [])
    if len(candidates) >= 2:
        return "MISSING_ERROR"
    return "NOT_TRIGGERED"

def get_final_commit_status(record: dict) -> str:
    fc = record.get("final_commit") or record.get("final_commit_v2")
    if fc:
        return "EXECUTED"
    r2c = record.get("round2c")
    r2d = record.get("round2d")
    if r2c or r2d:
        return "MISSING_ERROR"
    return "NOT_TRIGGERED"


# =============================================================================
# PART C: R2d Schema Adapter
# =============================================================================
def adapt_r2d_test_item(test: dict) -> dict:
    """Adapter for R2d resurrection test items - maps killed_option -> option."""
    adapted = dict(test)
    if not adapted.get("option") and adapted.get("killed_option"):
        adapted["option"] = adapted["killed_option"]
    if not adapted.get("original_kill_type") and adapted.get("original_kill_shot"):
        kill_shot = adapted["original_kill_shot"]
        if isinstance(kill_shot, dict):
            adapted["original_kill_type"] = kill_shot.get("kill_type", "unknown")
        else:
            adapted["original_kill_type"] = str(kill_shot)[:50]
    if not adapted.get("verdict") and adapted.get("resurrection_result"):
        result = adapted["resurrection_result"].lower()
        # CRITICAL SEMANTICS (see R2D constants above):
        #   "failure" = Resurrection attempt FAILED → Kill CONFIRMED (option stays dead)
        #   "success" = Resurrection attempt SUCCEEDED → Kill DOWNGRADED (option revived)
        if result == R2D_RESURRECTION_FAILED or "confirmed" in result or ("kill" in result and "downgrad" not in result):
            adapted["verdict"] = "confirmed_kill"
        elif result == R2D_RESURRECTION_SUCCESS or "downgrad" in result or "resurrect" in result or "condition" in result:
            adapted["verdict"] = "downgraded_to_condition"
        else:
            adapted["verdict"] = "unknown"
    if not adapted.get("reasoning") and adapted.get("result_explanation"):
        adapted["reasoning"] = adapted["result_explanation"]
    return adapted


# =============================================================================
# Render Functions
# =============================================================================
def render_terminal_state_banner(record: dict, gold: str) -> str:
    """PART D: Render terminal state banner showing ASSERTED vs WITHHELD vs ERROR."""
    terminal_state = get_canonical_terminal_state(record)
    preference = get_system_preference(record)
    preference_correct = (preference == gold) if preference and gold else None
    
    auditor_decision = record.get("auditor_decision", {})
    justification = auditor_decision.get("justification", "")
    fragility = auditor_decision.get("fragility_indicators", [])
    
    if terminal_state == "WITHHELD":
        html = '<div style="background: #e2e3e5; border: 2px solid #6c757d; border-radius: 6px; padding: 12px; margin: 10px 0;">'
        html += '<div style="display: flex; justify-content: space-between; align-items: center;">'
        html += '<div>'
        html += '<span style="background: #6c757d; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 1.1em;">⏸ WITHHELD</span>'
        html += '<span style="margin-left: 10px; color: #495057;">System declined to assert an answer</span>'
        html += '</div>'
        html += f'<div style="text-align: right;"><strong>Gold:</strong> {gold}</div>'
        html += '</div>'
        
        if preference:
            pref_color = "#28a745" if preference_correct else "#dc3545"
            pref_icon = "✓" if preference_correct else "✗"
            html += f'<div style="margin-top: 8px; padding: 8px; background: white; border-radius: 4px;">'
            html += f'<span style="color: #6c757d;">Preference (diagnostic only):</span> '
            html += f'<strong style="color: {pref_color};">{preference}</strong> '
            html += f'<span style="color: {pref_color};">{pref_icon} {"matches" if preference_correct else "does not match"} gold</span>'
            html += '</div>'
        
        if justification:
            html += f'<div style="margin-top: 8px; font-size: 0.9em; color: #666;"><strong>Reason:</strong> {escape_html(justification[:200])}</div>'
        if fragility:
            html += f'<div style="margin-top: 4px; font-size: 0.85em; color: #856404;"><strong>Fragility indicators:</strong> {", ".join(fragility[:3])}</div>'
        html += '</div>'
        return html
    
    elif terminal_state == "ASSERTED":
        is_correct = preference_correct
        if is_correct:
            html = '<div style="background: #d4edda; border: 2px solid #28a745; border-radius: 6px; padding: 12px; margin: 10px 0;">'
            html += '<div style="display: flex; justify-content: space-between; align-items: center;"><div>'
            html += '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 1.1em;">✓ ASSERTED CORRECT</span>'
            html += f'<span style="margin-left: 10px; color: #155724;"><strong>{preference}</strong></span>'
            html += f'</div><div style="text-align: right;"><strong>Gold:</strong> {gold}</div></div></div>'
        else:
            html = '<div style="background: #f8d7da; border: 2px solid #dc3545; border-radius: 6px; padding: 12px; margin: 10px 0;">'
            html += '<div style="display: flex; justify-content: space-between; align-items: center;"><div>'
            html += '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 1.1em;">✗ ASSERTED WRONG</span>'
            html += f'<span style="margin-left: 10px; color: #721c24;"><strong>{preference}</strong> (should be {gold})</span>'
            html += f'</div><div style="text-align: right;"><strong>Gold:</strong> {gold}</div></div></div>'
        return html
    
    elif terminal_state == "ERROR":
        return '<div style="background: #f8d7da; border: 2px solid #dc3545; border-radius: 6px; padding: 12px; margin: 10px 0;"><span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;">⚠ ERROR</span><span style="margin-left: 10px; color: #721c24;">Pipeline or schema error</span></div>'
    
    return f'<div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 6px; padding: 12px; margin: 10px 0;"><span style="background: #ffc107; color: black; padding: 4px 10px; border-radius: 4px; font-weight: bold;">? UNKNOWN</span><span style="margin-left: 10px;"><strong>Gold:</strong> {gold}</span></div>'


def render_resurrection_section(round2d: dict) -> str:
    """Render R2d with schema adaptation."""
    if not round2d:
        return ""
    
    status = round2d.get("round_status", "")
    if status == "no_kills_to_test":
        return '<div class="round-section" style="background: #e9ecef; border-left: 4px solid #6c757d;"><strong>🔄 Resurrection (R2d)</strong><div style="margin-top: 10px; color: #666;">No kills to test</div></div>'
    
    summary = round2d.get("summary", {})
    confirmed = summary.get("confirmed_kills", [])
    downgraded = summary.get("downgraded_to_conditions", [])
    
    html = '<div class="round-section" style="background: #fff3cd; border-left: 4px solid #ffc107;"><strong>🔄 Resurrection (R2d)</strong><div style="margin-top: 10px;">'
    
    if confirmed:
        html += f"<div style='margin-bottom: 8px;'><span style='background:#dc3545; color:white; padding:3px 8px; border-radius:3px;'>☠ Confirmed Dead:</span> <strong>{', '.join(confirmed)}</strong></div>"
    if downgraded:
        html += f"<div style='margin-bottom: 8px;'><span style='background:#28a745; color:white; padding:3px 8px; border-radius:3px;'>🔙 Resurrected:</span> <strong>{', '.join(downgraded)}</strong></div>"
    
    tests = round2d.get("resurrection_tests", [])
    if tests:
        html += "<div style='margin-top: 10px;'><strong>Test Details:</strong>"
        html += "<table style='width:100%; font-size: 0.85em; margin-top: 5px;'><tr style='background:#eee;'><th>Option</th><th>Verdict</th><th>Reasoning</th></tr>"
        for test in tests:
            adapted = adapt_r2d_test_item(test)
            option = adapted.get("option", "?")
            verdict = adapted.get("verdict", "?")
            verdict_color = "#dc3545" if verdict == "confirmed_kill" else "#28a745" if verdict == "downgraded_to_condition" else "#6c757d"
            reasoning = truncate(adapted.get("reasoning", "N/A"), 60)
            html += f"<tr><td><strong>{option}</strong></td><td style='color:{verdict_color};'>{escape_html(verdict)}</td><td>{reasoning}</td></tr>"
        html += "</table></div>"
    
    html += "</div></div>"
    return html


def render_ladder_section(record: dict) -> str:
    """Original ladder section without consistency check - kept for backwards compatibility."""
    system_ladder = record.get("system_ladder")
    if not system_ladder:
        return ""
    
    level = system_ladder.get("level", -1)
    level_name = system_ladder.get("level_name", "unknown")
    justification = system_ladder.get("justification", "")
    confirmed_kills = system_ladder.get("confirmed_kills", [])
    survivors = system_ladder.get("survivors", [])
    
    colors = {0: "#28a745", 1: "#17a2b8", 2: "#ffc107", 3: "#fd7e14", 4: "#dc3545"}
    color = colors.get(level, "#6c757d")
    
    html = f'<div class="round-section" style="background: linear-gradient(to right, {color}22, white); border-left: 4px solid {color};"><strong>🪜 Ladder of Commitment</strong>'
    html += f'<div style="margin-top: 10px;"><div style="font-size: 1.3em; font-weight: bold; color: {color};">Level {level}: {level_name.upper().replace("_", " ")}</div>'
    html += f'<div style="font-size: 0.95em; margin-top: 8px; padding: 8px; background: white; border-radius: 4px;">{escape_html(justification)}</div>'
    
    if confirmed_kills:
        html += f"<div style='margin-top: 8px;'><span style='background:#dc3545; color:white; padding:2px 6px; border-radius:3px; font-size:0.85em;'>Kills</span> {', '.join(confirmed_kills)}</div>"
    if survivors:
        html += f"<div style='margin-top: 4px;'><span style='background:#17a2b8; color:white; padding:2px 6px; border-radius:3px; font-size:0.85em;'>Survivors</span> {', '.join(survivors)}</div>"
    
    html += '</div></div>'
    return html


def render_ladder_section_with_check(record: dict, candidate_sets: dict, ladder_check: dict) -> str:
    """
    Render ladder section using AUTHORITATIVE survivors (not ladder's internal state).
    
    KEY BEHAVIOR (v2.5.4):
    - Ladder Survivors badge shows authoritative survivors from auditor_decision
    - Ladder Kills badge shows all eliminated options (ABCD - authoritative survivors)
    - If ladder internal state differs, show info message (not scary warning)
    - Empty survivors shown as ∅ with "non-assertable" flag
    """
    system_ladder = record.get("system_ladder") or record.get("final_commit", {}).get("system_ladder", {})
    if not system_ladder:
        return ""
    
    level = system_ladder.get("level", -1)
    level_name = system_ladder.get("level_name", "unknown")
    justification = system_ladder.get("justification", "")
    
    # Get AUTHORITATIVE survivors (same as auditor uses)
    auth_survivors = ladder_check.get("authoritative_survivors", [])
    auth_source = ladder_check.get("authoritative_source", "unknown")
    was_overridden = ladder_check.get("overridden", False)
    
    # Compute authoritative kills (everything not in survivors)
    all_options = set(["A", "B", "C", "D"])
    auth_kills = sorted(all_options - set(auth_survivors))
    
    colors = {0: "#28a745", 1: "#17a2b8", 2: "#ffc107", 3: "#fd7e14", 4: "#dc3545"}
    color = colors.get(level, "#6c757d")
    
    html = f'<div class="round-section" style="background: linear-gradient(to right, {color}22, white); border-left: 4px solid {color};"><strong>🪜 Ladder of Commitment</strong>'
    html += f'<div style="margin-top: 10px;"><div style="font-size: 1.3em; font-weight: bold; color: {color};">Level {level}: {level_name.upper().replace("_", " ")}</div>'
    
    # Show justification, with non-assertable flag if empty survivors
    if not auth_survivors:
        html += f'<div style="font-size: 0.95em; margin-top: 8px; padding: 8px; background: #f8d7da; border: 1px solid #dc3545; border-radius: 4px;">'
        html += f'<span style="color: #721c24;">⚠️ Non-assertable: empty survivor set</span><br>'
        html += f'<span style="color: #666;">{escape_html(justification)}</span></div>'
    else:
        html += f'<div style="font-size: 0.95em; margin-top: 8px; padding: 8px; background: white; border-radius: 4px;">{escape_html(justification)}</div>'
    
    # Show AUTHORITATIVE kills (not ladder's internal kills)
    if auth_kills:
        html += f"<div style='margin-top: 8px;'><span style='background:#dc3545; color:white; padding:2px 6px; border-radius:3px; font-size:0.85em;'>Eliminated</span> {', '.join(auth_kills)}</div>"
    
    # Show AUTHORITATIVE survivors (not ladder's internal survivors)
    if auth_survivors:
        html += f"<div style='margin-top: 4px;'><span style='background:#17a2b8; color:white; padding:2px 6px; border-radius:3px; font-size:0.85em;'>Survivors</span> {', '.join(auth_survivors)}</div>"
    else:
        html += f"<div style='margin-top: 4px;'><span style='background:#6c757d; color:white; padding:2px 6px; border-radius:3px; font-size:0.85em;'>Survivors</span> ∅ (empty)</div>"
    
    # Show info message if ladder was overridden (not a scary warning)
    if was_overridden:
        ladder_survivors = ladder_check.get("ladder_survivors", [])
        ladder_str = ", ".join(ladder_survivors) if ladder_survivors else "∅"
        html += '<div style="margin-top: 10px; padding: 8px; background: #e7f3ff; border: 1px solid #17a2b8; border-radius: 4px; font-size: 0.85em;">'
        html += '<span style="color: #0c5460;">ℹ️ <strong>Ladder Override:</strong> '
        html += f'Ladder internal state ({ladder_str}) '
        html += f'overridden by authoritative survivors (source: {auth_source})</span>'
        html += '</div>'
    
    html += '</div></div>'
    return html


def render_kill_shots_section(round2c: dict, evaluators: List[str], candidate_sets: dict) -> str:
    """Render R2c with explicit candidate set labeling."""
    kill_aggregation = round2c.get("kill_aggregation", {})
    if not kill_aggregation:
        return ""
    
    confirmed_kills = kill_aggregation.get("confirmed_kills", [])
    r2c_survivors = kill_aggregation.get("survivors", [])
    input_candidates = candidate_sets.get("post_pruning", [])
    
    html = '<div class="round-section" style="background: #f8f9fa; border-left: 4px solid #dc3545;">'
    html += '<strong>🎯 Kill Analysis (R2c)</strong>'
    html += '<div style="font-size: 0.8em; color: #666; margin-top: 4px;">Input candidates: ' + ", ".join(input_candidates) + '</div>'
    html += '<div style="margin-top: 10px;">'
    
    if confirmed_kills:
        html += '<div style="margin-bottom: 12px;"><strong style="color: #dc3545;">⚫ CONFIRMED KILLS</strong>'
        html += "<table style='width:100%; font-size: 0.9em; margin-top: 5px;'><tr style='background:#f8d7da;'><th>Option</th><th>Kill Type</th><th>Proof</th></tr>"
        for kill in confirmed_kills:
            proof = truncate(kill.get("kill_proof", "N/A"), 80)
            html += f"<tr><td><strong>{kill.get('option', '?')}</strong></td><td><code>{escape_html(kill.get('kill_type', '?'))}</code></td><td>{proof}</td></tr>"
        html += "</table></div>"
    else:
        html += "<div style='color:#666;'>No confirmed kills</div>"
    
    if r2c_survivors:
        html += f"<div style='margin-top: 10px; padding: 8px; background: #d4edda; border-radius: 4px;'>"
        html += f"<strong>✓ Survivors (post-R2c):</strong> {', '.join(r2c_survivors)}</div>"
    
    html += "</div></div>"
    return html


def render_candidate_flow_timeline(record: dict, candidate_sets: dict, ladder_check: dict) -> str:
    """Render a timeline showing candidate set evolution through pipeline stages."""
    html = '<div class="round-section" style="background: #f0f4f8; border-left: 4px solid #17a2b8;">'
    html += '<strong>📊 Candidate Flow</strong>'
    html += '<div style="margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">'
    
    # Initial
    html += '<div style="text-align: center; padding: 8px; background: white; border-radius: 4px; min-width: 80px;">'
    html += '<div style="font-size: 0.75em; color: #666;">Initial</div>'
    html += '<div style="font-weight: bold;">' + ", ".join(candidate_sets["initial"]) + '</div>'
    html += '</div>'
    html += '<span style="color: #aaa;">→</span>'
    
    # Post-pruning
    post_pruning = candidate_sets.get("post_pruning", [])
    pruned_count = 4 - len(post_pruning)
    html += '<div style="text-align: center; padding: 8px; background: white; border-radius: 4px; min-width: 80px;">'
    html += '<div style="font-size: 0.75em; color: #666;">Post-R1.5</div>'
    html += '<div style="font-weight: bold;">' + (", ".join(post_pruning) if post_pruning else "∅") + '</div>'
    if pruned_count > 0:
        html += f'<div style="font-size: 0.7em; color: #dc3545;">({pruned_count} pruned)</div>'
    html += '</div>'
    html += '<span style="color: #aaa;">→</span>'
    
    # Post-R2c
    post_r2c = candidate_sets.get("post_r2c", [])
    r2c_killed = len(post_pruning) - len(post_r2c)
    html += '<div style="text-align: center; padding: 8px; background: white; border-radius: 4px; min-width: 80px;">'
    html += '<div style="font-size: 0.75em; color: #666;">Post-R2c</div>'
    html += '<div style="font-weight: bold;">' + (", ".join(post_r2c) if post_r2c else "∅") + '</div>'
    if r2c_killed > 0:
        html += f'<div style="font-size: 0.7em; color: #dc3545;">({r2c_killed} killed)</div>'
    html += '</div>'
    html += '<span style="color: #aaa;">→</span>'
    
    # Post-R2d (final)
    post_r2d = candidate_sets.get("post_r2d", [])
    r2d_killed = len(post_r2c) - len(post_r2d)
    final_color = "#28a745" if len(post_r2d) == 1 else "#ffc107" if len(post_r2d) > 1 else "#dc3545"
    html += f'<div style="text-align: center; padding: 8px; background: {final_color}22; border: 2px solid {final_color}; border-radius: 4px; min-width: 80px;">'
    html += '<div style="font-size: 0.75em; color: #666;">Final</div>'
    html += '<div style="font-weight: bold;">' + (", ".join(post_r2d) if post_r2d else "∅") + '</div>'
    if r2d_killed > 0:
        html += f'<div style="font-size: 0.7em; color: #dc3545;">({r2d_killed} killed)</div>'
    html += '</div>'
    
    html += '</div>'  # end flex row
    
    # Note if ladder was overridden (info, not warning)
    if ladder_check.get("overridden", False):
        html += '<div style="margin-top: 10px; padding: 8px; background: #e7f3ff; border: 1px solid #17a2b8; border-radius: 4px; font-size: 0.85em;">'
        html += '<span style="color: #0c5460;">ℹ️ Ladder internal state adjusted to match authoritative survivors</span>'
        html += '</div>'
    
    html += '</div>'
    return html


def render_disposition_section(record: dict) -> str:
    """Render disposition with clear pre-auditor vs terminal state labeling."""
    terminal_state = get_canonical_terminal_state(record)
    final_disposition = record.get("final_disposition", "UNKNOWN")
    prelim_disposition = record.get("prelim_disposition", "")
    
    html = '<div style="margin-top: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;">'
    
    # Pre-auditor disposition
    if prelim_disposition and prelim_disposition != final_disposition:
        html += f'<div style="margin-bottom: 8px;"><span style="color: #6c757d;">Pre-auditor disposition:</span> '
        html += f'<code>{escape_html(prelim_disposition)}</code></div>'
    
    # Final disposition (pipeline's "would choose")
    html += f'<div><span style="color: #495057;"><strong>Final Disposition (pre-auditor):</strong></span> '
    html += f'<code>{escape_html(final_disposition)}</code></div>'
    
    # Terminal state (what actually happened)
    ts_color = {"ASSERTED": "#28a745", "WITHHELD": "#6c757d", "ERROR": "#dc3545"}.get(terminal_state, "#ffc107")
    html += f'<div style="margin-top: 8px;"><span style="color: #495057;"><strong>Terminal State:</strong></span> '
    html += f'<span style="background: {ts_color}; color: white; padding: 2px 8px; border-radius: 3px;">{terminal_state}</span></div>'
    
    html += '</div>'
    return html


def render_what_happened_section(record: dict, candidate_sets: dict) -> str:
    """
    Generate a plain English narrative of what happened during evaluation.
    No technical jargon - just a readable story.
    """
    qid = record.get("question_id", "?")
    gold = record.get("gold_answer", "?")
    
    # Get key data
    r1 = record.get("_forensic_r1", {})
    r2c = record.get("round2c", {})
    r2d = record.get("round2d", {})
    final_commit = record.get("final_commit", {})
    auditor_decision = record.get("auditor_decision", {})
    system_ladder = final_commit.get("system_ladder", {})
    
    # Terminal state
    terminal_state = get_canonical_terminal_state(record)
    asserted_answer = auditor_decision.get("asserted_answer")
    
    # Build narrative
    paragraphs = []
    
    # === Round 1 summary ===
    r1_pattern = r1.get("agreement_pattern", "unknown")
    r1_majority = r1.get("majority_choice")
    r1_unanimous = r1.get("unanimous_choice")
    
    if r1_unanimous:
        paragraphs.append(f"All four evaluators independently chose <strong>{r1_unanimous}</strong> in Round 1.")
    elif r1_majority:
        correct_count = r1.get("correct_count", 0)
        paragraphs.append(f"In Round 1, {correct_count} of 4 evaluators favored <strong>{r1_majority}</strong>, but they didn't all agree.")
    else:
        paragraphs.append("Round 1 showed significant disagreement among evaluators.")
    
    # === Kill shot summary ===
    kill_agg = r2c.get("kill_aggregation", {})
    confirmed_kills = kill_agg.get("confirmed_kills", [])
    attempted_kills = kill_agg.get("attempted_kills", [])
    post_r2c = candidate_sets.get("post_r2c", [])
    
    if confirmed_kills:
        killed_opts = [k.get("option", k) if isinstance(k, dict) else k for k in confirmed_kills]
        if len(killed_opts) == 1:
            paragraphs.append(f"Kill shot analysis eliminated option <strong>{killed_opts[0]}</strong> with high confidence.")
        elif len(killed_opts) == 2:
            paragraphs.append(f"Kill shot analysis eliminated options <strong>{killed_opts[0]}</strong> and <strong>{killed_opts[1]}</strong>.")
        elif len(killed_opts) == 3:
            paragraphs.append(f"Kill shot analysis eliminated <strong>{', '.join(killed_opts)}</strong>, leaving only one survivor.")
        elif len(killed_opts) == 4:
            paragraphs.append(f"Kill shot analysis eliminated <strong>all four options</strong> — this suggests an invalid or highly ambiguous question.")
    elif attempted_kills:
        paragraphs.append(f"Kill shot analysis found potential issues with {len(attempted_kills)} option(s), but couldn't confirm eliminations.")
    else:
        paragraphs.append("No options were eliminated by kill shot analysis.")
    
    # === Resurrection summary ===
    if r2d and r2d.get("round_status") == "ok":
        r2d_summary = r2d.get("summary", {})
        confirmed_r2d = r2d_summary.get("confirmed_kills", [])
        downgraded = r2d_summary.get("downgraded_to_conditions", [])
        
        if downgraded:
            paragraphs.append(f"Resurrection testing revived option(s) <strong>{', '.join(downgraded)}</strong> — the original kill shots were found to be domain-dependent.")
        if confirmed_r2d:
            paragraphs.append(f"Resurrection testing confirmed that <strong>{', '.join(confirmed_r2d)}</strong> should remain eliminated.")
        if not downgraded and not confirmed_r2d:
            paragraphs.append("Resurrection testing ran but made no changes.")
    
    # === Final survivors ===
    final_survivors = candidate_sets.get("post_r2d", candidate_sets.get("final", []))
    n_survivors = len(final_survivors) if final_survivors else 0
    
    if n_survivors == 0:
        paragraphs.append("<strong>No valid options remained</strong> after all analysis.")
    elif n_survivors == 1:
        paragraphs.append(f"After all analysis, <strong>{final_survivors[0]}</strong> was the sole survivor.")
    elif n_survivors == 2:
        paragraphs.append(f"After all analysis, <strong>{final_survivors[0]}</strong> and <strong>{final_survivors[1]}</strong> both remained viable.")
    else:
        paragraphs.append(f"After all analysis, {n_survivors} options remained viable: <strong>{', '.join(final_survivors)}</strong>.")
    
    # === Final outcome ===
    if terminal_state == "ASSERTED":
        if asserted_answer == gold:
            paragraphs.append(f"<span style='color: #28a745;'>✓ CAM asserted <strong>{asserted_answer}</strong>, which matches the gold answer.</span>")
        else:
            paragraphs.append(f"<span style='color: #dc3545;'>✗ CAM asserted <strong>{asserted_answer}</strong>, but the gold answer is <strong>{gold}</strong>.</span>")
    elif terminal_state == "WITHHELD":
        justification = auditor_decision.get("justification", "")
        if "EMPTY_SURVIVOR" in justification:
            paragraphs.append("<span style='color: #6c757d;'>⊘ CAM withheld assertion because no valid options survived.</span>")
        elif "ASSERTED_NOT_IN_SURVIVORS" in justification:
            paragraphs.append("<span style='color: #6c757d;'>⊘ CAM withheld assertion because the preferred answer was eliminated.</span>")
        elif "alternatives_remain_viable" in justification or n_survivors > 1:
            paragraphs.append(f"<span style='color: #6c757d;'>⊘ CAM withheld assertion because {n_survivors} options remained viable — not enough certainty to commit.</span>")
        else:
            paragraphs.append("<span style='color: #6c757d;'>⊘ CAM withheld assertion due to insufficient confidence.</span>")
    else:
        paragraphs.append(f"<span style='color: #ffc107;'>⚠ Evaluation ended with status: {terminal_state}</span>")
    
    # === Assemble HTML ===
    html = '<div style="margin-top: 15px; padding: 12px; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 6px; border-left: 4px solid #6c757d;">'
    html += '<div style="font-weight: 600; margin-bottom: 8px; color: #495057;">📖 What Happened</div>'
    html += '<div style="font-size: 0.95em; line-height: 1.6; color: #333;">'
    html += ' '.join(paragraphs)
    html += '</div></div>'
    
    return html


def build_dossier(merged_results_path: Path, output_path: Path, selected_ids_path: Optional[Path] = None, filter_type: str = "all"):
    """
    Build forensic HTML dossier with correct terminal state semantics.
    
    Args:
        merged_results_path: Path to merged_results.jsonl
        output_path: Output HTML path
        selected_ids_path: Optional path to JSON file with question IDs to include
        filter_type: Filter by terminal state outcome:
            - "all": No filtering (default)
            - "asserted_correct": Only questions where system asserted correctly
            - "asserted_wrong": Only questions where system asserted incorrectly  
            - "asserted": All asserted questions (correct + wrong)
            - "withheld": Only questions where system withheld
            - "error": Only questions with pipeline errors
    """
    if not merged_results_path.exists():
        raise FileNotFoundError(f"ERROR: Missing results file: {merged_results_path}")
    
    records = []
    with open(merged_results_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    if not records:
        raise ValueError(f"ERROR: Results file is empty: {merged_results_path}")
    
    EVALUATORS = detect_evaluators_from_records(records)
    total_cases = len(records)
    
    # ==========================================================================
    # QUESTION TYPE DETECTION (DIAMOND vs MAIN)
    # ==========================================================================
    # Try to load manifest for type info
    manifest_types = {}
    
    # Check for manifest files (multiple naming patterns)
    manifest_candidates = [
        merged_results_path.parent / "manifest.json",
        merged_results_path.parent / f"run_{merged_results_path.parent.parent.name.split()[0]}_manifest.json",
    ]
    # Also check for run_XXX_manifest.json pattern
    for f in merged_results_path.parent.glob("run_*_manifest.json"):
        manifest_candidates.append(f)
    
    for manifest_path in manifest_candidates:
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    
                    # Format 1: main_ids / diamond_ids arrays
                    if "main_ids" in manifest or "diamond_ids" in manifest:
                        for qid in manifest.get("main_ids", []):
                            manifest_types[qid] = "MAIN"
                        for qid in manifest.get("diamond_ids", []):
                            manifest_types[qid] = "DIAMOND"
                        print(f"  Loaded question types from {manifest_path.name}: {len(manifest.get('main_ids', []))} MAIN, {len(manifest.get('diamond_ids', []))} DIAMOND")
                        break
                    
                    # Format 2: questions array with question_type field
                    if "questions" in manifest:
                        for q in manifest.get("questions", []):
                            qid = q.get("question_id")
                            qtype = q.get("question_type", q.get("dataset_source", "unknown"))
                            if qid:
                                manifest_types[qid] = qtype.upper() if qtype else "unknown"
                        print(f"  Loaded question types from {manifest_path.name}: {len(manifest_types)} questions")
                        break
                        
            except Exception as e:
                print(f"  Warning: Could not load manifest {manifest_path}: {e}")
    
    if not manifest_types:
        print("  Warning: No manifest found with question type info")
    
    # Assign question types to records and count
    diamond_count = 0
    main_count = 0
    for record in records:
        qid = record.get("question_id", "")
        # Priority: manifest > record field > qid pattern
        qtype = manifest_types.get(qid)
        if not qtype:
            qtype = record.get("question_type", record.get("dataset_source", ""))
        if not qtype:
            # Guess from question_id pattern (gpqa_diamond_xxx vs gpqa_main_xxx)
            if "diamond" in qid.lower():
                qtype = "DIAMOND"
            elif "main" in qid.lower():
                qtype = "MAIN"
            else:
                qtype = "unknown"
        qtype = qtype.upper() if qtype else "unknown"
        record["_question_type"] = qtype
        if qtype == "DIAMOND":
            diamond_count += 1
        elif qtype == "MAIN":
            main_count += 1
    
    # PART B: Correct counting with terminal state semantics
    asserted_correct = asserted_wrong = 0
    withheld_count = withheld_preference_correct = withheld_preference_wrong = 0
    error_count = pipeline_bug_count = v2_count = quarantine_count = 0
    ladder_counts = defaultdict(int)
    # Ladder counts with correctness breakdown for filtering
    ladder_correct_counts = defaultdict(int)  # L0✓, L1✓, etc.
    ladder_wrong_counts = defaultdict(int)    # L0✗, L1✗, etc.
    
    rounds_present = {"round1": 0, "grok_analysis": 0, "synthesis": 0, "round2a": 0, "round2c": 0, "round2d": 0, "round3": 0, "final_commit": 0, "auditor": 0}
    
    for record in records:
        gold = record.get("gold_answer", "")
        r1_stats = compute_round_correctness(record.get("round1", {}), gold, "round1", EVALUATORS)
        record["_forensic_r1"] = r1_stats
        
        # Count rounds present
        if record.get("round1"): rounds_present["round1"] += 1
        if record.get("grok_analysis"): rounds_present["grok_analysis"] += 1
        if record.get("synthesis") or record.get("synthesis_result"): rounds_present["synthesis"] += 1
        r2a = record.get("round2a")
        if r2a and r2a.get("round_executed", False): rounds_present["round2a"] += 1
        if record.get("round2c"): rounds_present["round2c"] += 1
        if record.get("round2d"): rounds_present["round2d"] += 1
        if record.get("round3"): rounds_present["round3"] += 1
        if record.get("final_commit"): rounds_present["final_commit"] += 1
        if record.get("auditor_result") or record.get("auditor_decision"): rounds_present["auditor"] += 1
        
        if record.get("pipeline_version") == "v2": v2_count += 1
        if record.get("ladder_level") is not None: ladder_counts[record["ladder_level"]] += 1
        
        r2c = record.get("round2c", {})
        for key, value in r2c.items():
            if key.startswith("evaluator_") and value:
                if value.get("_quarantine_records") or value.get("_schema_validation_failed"):
                    quarantine_count += 1
                    break
        
        # CRITICAL: Use terminal state for counting
        terminal_state = get_canonical_terminal_state(record)
        preference = get_system_preference(record)
        preference_matches_gold = (preference == gold) if preference and gold else False
        
        record["_terminal_state"] = terminal_state
        record["_preference"] = preference
        
        # Extract ladder level for filtering
        ladder_level = record.get("auditor_decision", {}).get("ladder_level")
        if ladder_level is None:
            ladder_level = record.get("ladder_level")
        record["_ladder_level"] = ladder_level if ladder_level is not None else -1
        
        if terminal_state == "ASSERTED":
            if preference_matches_gold:
                asserted_correct += 1
            else:
                asserted_wrong += 1
        elif terminal_state == "WITHHELD":
            withheld_count += 1
            if preference:
                if preference_matches_gold:
                    withheld_preference_correct += 1
                else:
                    withheld_preference_wrong += 1
        elif terminal_state == "ERROR":
            error_count += 1
        else:
            withheld_count += 1
        
        # Count ladder levels with correctness for filter buttons
        ll = record.get("_ladder_level", -1)
        if ll >= 0:
            ladder_counts[ll] += 1
            if preference_matches_gold:
                ladder_correct_counts[ll] += 1
            else:
                ladder_wrong_counts[ll] += 1
        
        r2c_status = get_round2c_status(record)
        fc_status = get_final_commit_status(record)
        if r2c_status == "MISSING_ERROR" or fc_status == "MISSING_ERROR":
            pipeline_bug_count += 1
    
    # =========================================================================
    # FILTERING: Apply filter_type to select subset of records
    # =========================================================================
    original_count = len(records)
    filter_description = "All questions"
    
    if filter_type != "all":
        filtered_records = []
        for record in records:
            terminal_state = record.get("_terminal_state", "")
            preference = record.get("_preference", "")
            gold = record.get("gold_answer", "")
            preference_correct = (preference == gold) if preference and gold else False
            
            include = False
            if filter_type == "asserted_correct":
                include = (terminal_state == "ASSERTED" and preference_correct)
            elif filter_type == "asserted_wrong":
                include = (terminal_state == "ASSERTED" and not preference_correct)
            elif filter_type == "asserted":
                include = (terminal_state == "ASSERTED")
            elif filter_type == "withheld":
                include = (terminal_state == "WITHHELD")
            elif filter_type == "error":
                include = (terminal_state == "ERROR")
            
            if include:
                filtered_records.append(record)
        
        records = filtered_records
        filter_labels = {
            "asserted_correct": "Asserted Correct only",
            "asserted_wrong": "Asserted Wrong only",
            "asserted": "All Asserted (correct + wrong)",
            "withheld": "Withheld only",
            "error": "Errors only",
        }
        filter_description = f"{filter_labels.get(filter_type, filter_type)} ({len(records)}/{original_count})"
        print(f"  Filter applied: {filter_type} → {len(records)} of {original_count} records")
    
    # Calculate metrics
    total_asserted = asserted_correct + asserted_wrong
    asserted_accuracy = (asserted_correct / total_asserted * 100) if total_asserted > 0 else 0
    total_with_preference = total_asserted + withheld_preference_correct + withheld_preference_wrong
    preference_correct_total = asserted_correct + withheld_preference_correct
    preference_accuracy = (preference_correct_total / total_with_preference * 100) if total_with_preference > 0 else 0
    
    def round_status(name, count, total):
        if count == total: return f'<span style="color: #28a745;">✓ {name}</span>'
        elif count > 0: return f'<span style="color: #ffc107;">⚠ {name} ({count}/{total})</span>'
        else: return f'<span style="color: #dc3545;">✗ {name}</span>'
    
    rounds_html = " | ".join([round_status(n, rounds_present[k], total_cases) for n, k in [("R1", "round1"), ("Grok", "grok_analysis"), ("Synth", "synthesis"), ("R2c", "round2c"), ("R2d", "round2d"), ("R3", "round3"), ("FC", "final_commit"), ("Audit", "auditor")]])
    # Generate filter banner HTML if filter is active
    filter_banner = ""
    if filter_type != "all":
        filter_colors = {
            "asserted_correct": ("#28a745", "#d4edda"),
            "asserted_wrong": ("#dc3545", "#f8d7da"),
            "asserted": ("#17a2b8", "#d1ecf1"),
            "withheld": ("#6c757d", "#e2e3e5"),
            "error": ("#dc3545", "#f8d7da"),
        }
        border_color, bg_color = filter_colors.get(filter_type, ("#007bff", "#e7f3ff"))
        filter_banner = f'''<div style="background: {bg_color}; border: 3px solid {border_color}; border-radius: 6px; padding: 15px; margin-bottom: 15px;">
<div style="font-size: 1.3em; font-weight: bold; color: {border_color};">🔍 FILTERED VIEW: {filter_description}</div>
<div style="margin-top: 5px; font-size: 0.9em;">Showing {len(records)} of {original_count} questions | Filter: <code>--filter {filter_type}</code></div>
</div>'''
    
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>GPQA CAM Dossier v3</title>
<style>
body {{ font-family: sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
.header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.stats {{ display: flex; gap: 20px; margin-top: 15px; flex-wrap: wrap; }}
.stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; flex: 1; min-width: 100px; }}
.question-card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
.round-section {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 6px; border-left: 4px solid #007bff; }}
.evaluator {{ display: inline-block; padding: 8px; margin: 5px; background: #e9ecef; border-radius: 4px; }}
.evaluator.correct {{ background: #d4edda; border: 1px solid #28a745; }}
.evaluator.incorrect {{ background: #f8d7da; border: 1px solid #dc3545; }}
.choice {{ padding: 8px; margin: 4px 0; border: 1px solid #eee; border-radius: 4px; }}
.choice.correct {{ background: #d4edda; border-color: #28a745; }}
table {{ border-collapse: collapse; }} th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid #ddd; }}
.filter-btn {{ padding: 8px 16px; margin: 4px; border: 2px solid #ccc; border-radius: 6px; cursor: pointer; font-weight: bold; background: white; transition: all 0.2s; }}
.filter-btn:hover {{ background: #f0f0f0; }}
.filter-btn.active {{ border-color: #007bff; background: #e7f3ff; }}
.filter-btn.all {{ border-color: #007bff; }}
.filter-btn.asserted-correct {{ border-color: #28a745; }}
.filter-btn.asserted-wrong {{ border-color: #dc3545; }}
.filter-btn.withheld {{ border-color: #6c757d; }}
.hidden {{ display: none !important; }}
#filterStatus {{ margin-top: 10px; padding: 8px 12px; background: #e7f3ff; border-radius: 4px; font-size: 0.9em; }}
</style>
<script>
// Export data for JSON export
const questionData = QUESTION_DATA_PLACEHOLDER;

let currentFilter = 'all';
let currentTypeFilter = 'all';
let currentLadderFilter = 'all';

function filterQuestions(filterType) {{
    if (filterType) currentFilter = filterType;
    applyFilters();
}}

function filterByType(typeFilter) {{
    currentTypeFilter = typeFilter;
    applyFilters();
}}

function filterByLadder(ladderFilter) {{
    currentLadderFilter = ladderFilter;
    applyFilters();
}}

function applyFilters() {{
    const cards = document.querySelectorAll('.question-card');
    let shown = 0;
    let correctCount = 0;
    let assertedCount = 0;
    let withheldCount = 0;
    
    cards.forEach(card => {{
        const state = card.dataset.state;
        const correct = card.dataset.correct === 'true';
        const qtype = card.dataset.qtype || 'unknown';
        const ladder = card.dataset.ladder || '-1';
        
        // Terminal state filter
        let stateMatch = false;
        if (currentFilter === 'all') stateMatch = true;
        else if (currentFilter === 'asserted_correct') stateMatch = (state === 'ASSERTED' && correct);
        else if (currentFilter === 'asserted_wrong') stateMatch = (state === 'ASSERTED' && !correct);
        else if (currentFilter === 'asserted') stateMatch = (state === 'ASSERTED');
        else if (currentFilter === 'withheld') stateMatch = (state === 'WITHHELD');
        else if (currentFilter === 'error') stateMatch = (state === 'ERROR');
        
        // Type filter
        let typeMatch = (currentTypeFilter === 'all') || (qtype === currentTypeFilter);
        
        // Ladder filter
        let ladderMatch = false;
        if (currentLadderFilter === 'all') ladderMatch = true;
        else if (currentLadderFilter === '1_correct') ladderMatch = (ladder === '1' && correct);
        else if (currentLadderFilter === '1_wrong') ladderMatch = (ladder === '1' && !correct);
        else ladderMatch = (ladder === currentLadderFilter);
        
        const show = stateMatch && typeMatch && ladderMatch;
        card.classList.toggle('hidden', !show);
        
        if (show) {{
            shown++;
            if (state === 'ASSERTED') {{
                assertedCount++;
                if (correct) correctCount++;
            }} else if (state === 'WITHHELD') {{
                withheldCount++;
            }}
        }}
    }});
    
    // Update active buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.filter === currentFilter);
    }});
    document.querySelectorAll('.type-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.type === currentTypeFilter);
    }});
    document.querySelectorAll('.ladder-btn').forEach(btn => {{
        btn.classList.toggle('active', btn.dataset.ladder === currentLadderFilter);
    }});
    
    // Update status with dynamic metrics
    const total = cards.length;
    const accuracy = assertedCount > 0 ? (correctCount / assertedCount * 100).toFixed(1) : 0;
    const coverage = shown > 0 ? (assertedCount / shown * 100).toFixed(1) : 0;
    
    const labels = {{
        'all': 'All questions',
        'asserted_correct': 'Asserted Correct',
        'asserted_wrong': 'Asserted Wrong',
        'asserted': 'All Asserted',
        'withheld': 'Withheld',
        'error': 'Errors'
    }};
    const typeLabels = {{'all': 'All Types', 'DIAMOND': 'Diamond', 'MAIN': 'Main'}};
    const ladderLabels = {{'all': 'All', '0': 'L0', '1_correct': 'L1✓', '1_wrong': 'L1✗', '2': 'L2', '3': 'L3', '4': 'L4'}};
    
    document.getElementById('filterStatus').innerHTML = 
        `<strong>🔍 ${{labels[currentFilter]}} | ${{typeLabels[currentTypeFilter]}} | ${{ladderLabels[currentLadderFilter] || currentLadderFilter}}:</strong> Showing ${{shown}} of ${{total}} | ` +
        `<span style="color:#28a745;">Accuracy: ${{accuracy}}%</span> (${{correctCount}}/${{assertedCount}}) | ` +
        `<span style="color:#17a2b8;">Coverage: ${{coverage}}%</span> | ` +
        `<span style="color:#6c757d;">Withheld: ${{withheldCount}}</span>`;
    
    // Update stat boxes
    const wrongCount = assertedCount - correctCount;
    const abstentionRate = shown > 0 ? (withheldCount / shown * 100).toFixed(1) : 0;
    
    // Count withheld preferences from questionData for filtered view
    const visibleIds = Array.from(document.querySelectorAll('.question-card:not(.hidden)')).map(c => c.dataset.qid);
    const visibleData = questionData.filter(q => visibleIds.includes(q.question_id));
    let withheldPrefCorrect = 0, withheldPrefWrong = 0;
    visibleData.forEach(q => {{
        if (q.terminal_state === 'WITHHELD' && q.preference) {{
            if (q.correct) withheldPrefCorrect++;
            else withheldPrefWrong++;
        }}
    }});
    
    // Preference accuracy includes withheld
    const prefTotal = assertedCount + withheldPrefCorrect + withheldPrefWrong;
    const prefCorrect = correctCount + withheldPrefCorrect;
    const prefAccuracy = prefTotal > 0 ? (prefCorrect / prefTotal * 100).toFixed(1) : 0;
    
    // Update stat box values
    document.getElementById('stat-total').textContent = `Total: ${{shown}}`;
    document.getElementById('stat-correct').textContent = `Asserted Correct: ${{correctCount}}`;
    document.getElementById('stat-wrong').textContent = `Asserted Wrong: ${{wrongCount}}`;
    document.getElementById('stat-withheld').textContent = `Withheld: ${{withheldCount}}`;
    
    document.getElementById('metric-accuracy').textContent = `${{accuracy}}%`;
    document.getElementById('metric-accuracy-detail').textContent = `${{correctCount}} correct / ${{assertedCount}} asserted`;
    document.getElementById('metric-pref-accuracy').textContent = `${{prefAccuracy}}%`;
    document.getElementById('metric-pref-detail').textContent = `${{prefCorrect}} correct / ${{prefTotal}} with preference`;
    
    document.getElementById('metric-coverage').textContent = `${{coverage}}%`;
    document.getElementById('metric-coverage-detail').textContent = `${{assertedCount}} asserted / ${{shown}} total`;
    document.getElementById('metric-abstention').textContent = `${{abstentionRate}}%`;
    document.getElementById('metric-abstention-detail').textContent = `${{withheldCount}} withheld / ${{shown}} total`;
    document.getElementById('metric-withheld-correct').textContent = withheldPrefCorrect;
    document.getElementById('metric-withheld-wrong').textContent = withheldPrefWrong;
}}

function exportJSON() {{
    const cards = document.querySelectorAll('.question-card:not(.hidden)');
    const visibleIds = Array.from(cards).map(c => c.dataset.qid);
    const exported = questionData.filter(q => visibleIds.includes(q.question_id));
    
    const blob = new Blob([JSON.stringify(exported, null, 2)], {{type: 'application/json'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dossier_export_${{currentFilter}}_${{currentTypeFilter}}_${{new Date().toISOString().slice(0,10)}}.json`;
    a.click();
    URL.revokeObjectURL(url);
}}

window.onload = () => applyFilters();
</script>
</head><body>
<div class="header">
<h1>GPQA CAM Dossier <span style="font-size: 0.6em; color: #6c757d;">v3 - Terminal State Semantics</span></h1>
<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div style="background: #f0f4f8; border: 2px solid #17a2b8; border-radius: 8px; padding: 15px; margin: 15px 0;">
<div style="font-weight: bold; margin-bottom: 10px;">🔍 Filter Questions</div>
<button class="filter-btn all active" data-filter="all" onclick="filterQuestions('all')">All ({total_cases})</button>
<button class="filter-btn asserted-correct" data-filter="asserted_correct" onclick="filterQuestions('asserted_correct')" style="color: #28a745;">✓ Asserted Correct ({asserted_correct})</button>
<button class="filter-btn asserted-wrong" data-filter="asserted_wrong" onclick="filterQuestions('asserted_wrong')" style="color: #dc3545;">✗ Asserted Wrong ({asserted_wrong})</button>
<button class="filter-btn withheld" data-filter="withheld" onclick="filterQuestions('withheld')" style="color: #6c757d;">⏸ Withheld ({withheld_count})</button>
<button class="filter-btn" data-filter="asserted" onclick="filterQuestions('asserted')" style="color: #17a2b8;">All Asserted ({total_asserted})</button>
<span style="margin-left: 20px; border-left: 2px solid #ccc; padding-left: 15px;">
<button class="filter-btn type-btn active" data-type="all" onclick="filterByType('all')" style="background: #f8f9fa;">All Types</button>
<button class="filter-btn type-btn" data-type="DIAMOND" onclick="filterByType('DIAMOND')" style="color: #9c27b0;">💎 Diamond ({diamond_count})</button>
<button class="filter-btn type-btn" data-type="MAIN" onclick="filterByType('MAIN')" style="color: #ff9800;">📋 Main ({main_count})</button>
</span>
<br style="margin-top: 8px;">
<div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ccc;">
<span style="font-weight: bold; margin-right: 10px;">🪜 Ladder Level:</span>
<button class="filter-btn ladder-btn active" data-ladder="all" onclick="filterByLadder('all')" style="background: #f8f9fa;">All</button>
<button class="filter-btn ladder-btn" data-ladder="0" onclick="filterByLadder('0')" style="color: #28a745; border-color: #28a745;">L0 Full ({ladder_counts.get(0, 0)})</button>
<button class="filter-btn ladder-btn" data-ladder="1_correct" onclick="filterByLadder('1_correct')" style="color: #17a2b8; border-color: #17a2b8;">L1 ✓ ({ladder_correct_counts.get(1, 0)})</button>
<button class="filter-btn ladder-btn" data-ladder="1_wrong" onclick="filterByLadder('1_wrong')" style="color: #dc3545; border-color: #dc3545;">L1 ✗ ({ladder_wrong_counts.get(1, 0)})</button>
<button class="filter-btn ladder-btn" data-ladder="4" onclick="filterByLadder('4')" style="color: #6c757d; border-color: #6c757d;">L4 Withheld ({ladder_counts.get(4, 0)})</button>
<button class="filter-btn ladder-btn" data-ladder="2" onclick="filterByLadder('2')" style="color: #ffc107; border-color: #ffc107;">L2 ({ladder_counts.get(2, 0)})</button>
<button class="filter-btn ladder-btn" data-ladder="3" onclick="filterByLadder('3')" style="color: #fd7e14; border-color: #fd7e14;">L3 ({ladder_counts.get(3, 0)})</button>
</div>
<button class="filter-btn" onclick="exportJSON()" style="margin-left: 20px; background: #28a745; color: white; border-color: #28a745;">📥 Export JSON</button>
<div id="filterStatus"></div>
</div>

{filter_banner}
<div class="stats">
<div class="stat-box" id="stat-total">Total: {total_cases}</div>
<div class="stat-box" style="border-left-color: #28a745;" id="stat-correct">Asserted Correct: {asserted_correct}</div>
<div class="stat-box" style="border-left-color: #dc3545;" id="stat-wrong">Asserted Wrong: {asserted_wrong}</div>
<div class="stat-box" style="border-left-color: #6c757d;" id="stat-withheld">Withheld: {withheld_count}</div>
<div class="stat-box" style="border-left-color: {'#dc3545' if pipeline_bug_count else '#28a745'};">Bugs: {pipeline_bug_count}</div>
</div>
<div style="background: #f8f9fa; border: 2px solid #495057; border-radius: 6px; padding: 15px; margin: 15px 0;">
<div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">📊 Accuracy Metrics</div>
<div style="display: flex; gap: 30px; flex-wrap: wrap;">
<div style="flex: 1; min-width: 200px; padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #28a745;">
<div style="font-weight: bold; color: #155724;">Asserted Accuracy</div>
<div style="font-size: 1.5em; color: #28a745;" id="metric-accuracy">{asserted_accuracy:.1f}%</div>
<div style="font-size: 0.85em; color: #666;" id="metric-accuracy-detail">{asserted_correct} correct / {total_asserted} asserted</div>
</div>
<div style="flex: 1; min-width: 200px; padding: 10px; background: white; border-radius: 4px; border-left: 4px solid #6c757d;">
<div style="font-weight: bold; color: #495057;">Preference Accuracy <span style="font-weight: normal; font-size: 0.8em;">(diagnostic)</span></div>
<div style="font-size: 1.5em; color: #6c757d;" id="metric-pref-accuracy">{preference_accuracy:.1f}%</div>
<div style="font-size: 0.85em; color: #666;" id="metric-pref-detail">{preference_correct_total} correct / {total_with_preference} with preference</div>
</div>
</div>
<div style="margin-top: 10px; font-size: 0.85em; color: #666;"><strong>Note:</strong> Asserted Accuracy counts only cases where the system committed. Preference Accuracy (diagnostic) includes withheld cases.</div>
</div>
<div style="background: #e9ecef; border: 2px solid #6c757d; border-radius: 6px; padding: 15px; margin: 15px 0;">
<div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">📈 Coverage Metrics</div>
<div style="display: flex; gap: 20px; flex-wrap: wrap;">
<div style="flex: 1; min-width: 120px; padding: 10px; background: white; border-radius: 4px;">
<div style="font-weight: bold; color: #495057;">Coverage</div>
<div style="font-size: 1.3em; color: #17a2b8;" id="metric-coverage">{total_asserted / total_cases * 100 if total_cases else 0:.1f}%</div>
<div style="font-size: 0.85em; color: #666;" id="metric-coverage-detail">{total_asserted} asserted / {total_cases} total</div>
</div>
<div style="flex: 1; min-width: 120px; padding: 10px; background: white; border-radius: 4px;">
<div style="font-weight: bold; color: #495057;">Abstention Rate</div>
<div style="font-size: 1.3em; color: #6c757d;" id="metric-abstention">{withheld_count / total_cases * 100 if total_cases else 0:.1f}%</div>
<div style="font-size: 0.85em; color: #666;" id="metric-abstention-detail">{withheld_count} withheld / {total_cases} total</div>
</div>
<div style="flex: 1; min-width: 120px; padding: 10px; background: white; border-radius: 4px;">
<div style="font-weight: bold; color: #495057;">Withheld Pref ✓</div>
<div style="font-size: 1.3em; color: #28a745;" id="metric-withheld-correct">{withheld_preference_correct}</div>
<div style="font-size: 0.85em; color: #666;">Would have been correct</div>
</div>
<div style="flex: 1; min-width: 120px; padding: 10px; background: white; border-radius: 4px;">
<div style="font-weight: bold; color: #495057;">Withheld Pref ✗</div>
<div style="font-size: 1.3em; color: #dc3545;" id="metric-withheld-wrong">{withheld_preference_wrong}</div>
<div style="font-size: 0.85em; color: #666;">Would have been wrong</div>
</div>
</div>
<div style="margin-top: 10px; font-size: 0.85em; color: #666;"><strong>Interpretation:</strong> Coverage = % of questions where system committed. Of the {withheld_count} withheld: {withheld_preference_correct} had correct preference (saved errors), {withheld_preference_wrong} had wrong preference (correctly abstained).</div>
</div>
<div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 6px; padding: 12px; margin-bottom: 15px;">
<strong>📁 Data Provenance</strong><br><code style="font-size: 0.9em;">{merged_results_path.name}</code> | Records: {total_cases}<br>
<div style="margin-top: 8px; font-size: 0.9em;">Rounds: {rounds_html}</div>
</div>
</div>
<div id="questionsContainer">
'''
    
    for idx, record in enumerate(records):
        qid = record["question_id"]
        gold = record.get("gold_answer", "")
        r1_stats = record["_forensic_r1"]
        r2c = record.get("round2c")
        r2d = record.get("round2d")
        
        # CRITICAL: Compute canonical candidate sets for this question
        candidate_sets = extract_candidate_sets(record)
        ladder_check = check_ladder_consistency(record, candidate_sets)
        
        # Compute correctness for data attribute
        preference = record.get("_preference", "")
        preference_correct = (preference == gold) if preference and gold else False
        terminal_state = record.get("_terminal_state", "UNKNOWN")
        
        question_type = record.get("_question_type", "unknown")
        ladder_level = record.get("_ladder_level", -1)
        html += f'<div class="question-card" data-state="{terminal_state}" data-correct="{str(preference_correct).lower()}" data-qtype="{question_type}" data-qid="{qid}" data-ladder="{ladder_level}"><h3>Question {qid} <span style="font-size: 0.7em; padding: 2px 6px; border-radius: 3px; background: {"#9c27b0" if question_type == "DIAMOND" else "#ff9800" if question_type == "MAIN" else "#6c757d"}; color: white;">{"💎" if question_type == "DIAMOND" else "📋" if question_type == "MAIN" else "?"} {question_type}</span></h3><p>{escape_html(record["question"][:500])}{"..." if len(record["question"]) > 500 else ""}</p>'
        
        # Terminal state banner
        html += render_terminal_state_banner(record, gold)
        
        # Choices
        html += '<div>'
        for k, v in record['choices'].items():
            html += f'<div class="choice {"correct" if k == gold else ""}"><strong>{k}:</strong> {escape_html(v)}</div>'
        html += f'</div><div class="round-section"><strong>Round 1:</strong> {r1_stats["agreement_pattern"]} | Correct: {r1_stats["correct_count"]}<div>'
        for en in EVALUATORS:
            choice = r1_stats['choices'].get(en, "N/A")
            parse_ok = r1_stats.get('parse_ok', {}).get(en, True)
            if not parse_ok:
                html += f'<div class="evaluator" style="background: #f8d7da;">Eval {en}: <span style="color: #dc3545;">FAILED</span></div>'
            else:
                cls = "correct" if choice == gold else ("incorrect" if choice else "")
                html += f'<div class="evaluator {cls}">Eval {en}: {choice}</div>'
        html += '</div></div>'
        
        # Candidate Flow Timeline (shows evolution through pipeline stages)
        html += render_candidate_flow_timeline(record, candidate_sets, ladder_check)
        
        # R2c - pass candidate_sets for proper labeling
        if r2c:
            html += render_kill_shots_section(r2c, EVALUATORS, candidate_sets)
        
        # R2d
        if r2d:
            html += render_resurrection_section(r2d)
        
        # Ladder (with consistency warning if mismatched)
        html += render_ladder_section_with_check(record, candidate_sets, ladder_check)
        
        # Disposition section (pre-auditor vs terminal state)
        html += render_disposition_section(record)
        
        # Plain English narrative of what happened
        html += render_what_happened_section(record, candidate_sets)
        
        html += '</div>'
    
    html += '</div></body></html>'
    
    # Build JSON export data
    export_data = []
    for record in records:
        export_data.append({
            "question_id": record.get("question_id"),
            "terminal_state": record.get("_terminal_state"),
            "preference": record.get("_preference"),
            "gold_answer": record.get("gold_answer"),
            "correct": (record.get("_preference") == record.get("gold_answer")) if record.get("_preference") and record.get("gold_answer") else False,
            "question_type": record.get("_question_type", "unknown"),
            "ladder_level": record.get("auditor_decision", {}).get("ladder_level") or record.get("ladder_level"),
        })
    
    # Replace placeholder with actual JSON data
    html = html.replace("QUESTION_DATA_PLACEHOLDER", json.dumps(export_data))
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Dossier written to {output_path}")
    print(f"  Terminal states: Asserted={total_asserted} (Correct={asserted_correct}, Wrong={asserted_wrong}), Withheld={withheld_count}, Error={error_count}")
    print(f"  Asserted Accuracy: {asserted_accuracy:.1f}%")
    print(f"  Preference Accuracy (diagnostic): {preference_accuracy:.1f}%")
    return output_path


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Build GPQA CAM Dossier with optional filtering")
    parser.add_argument("merged_results", help="Path to merged_results.jsonl")
    parser.add_argument("output", nargs="?", help="Output HTML path (default: dossier.html in same directory)")
    parser.add_argument("--filter", "-f", choices=["asserted_correct", "asserted_wrong", "withheld", "error", "asserted", "all"],
                        default="all", help="Filter questions by terminal state outcome")
    
    args = parser.parse_args()
    
    merged_path = Path(args.merged_results)
    
    # Default output name based on filter
    if args.output:
        output_path = Path(args.output)
    else:
        if args.filter == "all":
            output_path = merged_path.parent / "dossier.html"
        else:
            output_path = merged_path.parent / f"dossier_{args.filter}.html"
    
    build_dossier(merged_path, output_path, filter_type=args.filter)