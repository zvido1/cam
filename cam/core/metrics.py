"""
CAM Metrics Module
Extracted from run_gpqa_cam.py for modularity.
Computes evaluation metrics for GPQA CAM runs.
"""

from collections import Counter, defaultdict
from typing import Dict, List

# Default evaluator names - can be overridden
DEFAULT_EVALUATORS = ["A", "B", "C", "D"]


def compute_grok_metrics(round1_records: List[dict], evaluators: List[str] = None) -> dict:
    """Compute Grok Analyzer reliability metrics (Part D)."""
    metrics = {
        "grok_incompatibility_true_count": 0,
        "grok_incompatibility_invalid_count": 0,  # true but empty list
        "grok_equivalence_true_count": 0,
        "grok_mixed_count": 0,
        "grok_reasoning_relation_distribution": Counter(),
    }
    
    for record in round1_records:
        grok_analysis = record.get("grok_analysis")
        if not grok_analysis:
            continue
        
        incompatibility_detected = grok_analysis.get("incompatibility_detected", False)
        equivalence_detected = grok_analysis.get("equivalence_detected", False)
        reasoning_relation = grok_analysis.get("reasoning_relation", "UNKNOWN")
        grok_incompatibility_invalid = grok_analysis.get("grok_incompatibility_invalid", False)
        
        if incompatibility_detected:
            metrics["grok_incompatibility_true_count"] += 1
        if grok_incompatibility_invalid:
            metrics["grok_incompatibility_invalid_count"] += 1
        if equivalence_detected:
            metrics["grok_equivalence_true_count"] += 1
        if reasoning_relation == "MIXED":
            metrics["grok_mixed_count"] += 1
        
        metrics["grok_reasoning_relation_distribution"][reasoning_relation] += 1
    
    # Convert Counter to dict for JSON serialization
    metrics["grok_reasoning_relation_distribution"] = dict(metrics["grok_reasoning_relation_distribution"])
    
    return metrics


def compute_round1_metrics(round1_records: List[dict], evaluators: List[str] = None) -> dict:
    """Compute Round 1 metrics."""
    if evaluators is None:
        evaluators = DEFAULT_EVALUATORS
    
    metrics = {
        "total_questions": len(round1_records),
        "evaluator_accuracy": {eval_name: 0 for eval_name in evaluators},
        "evaluator_failed": {eval_name: 0 for eval_name in evaluators},  # Track failures separately
        "evaluator_total": {eval_name: 0 for eval_name in evaluators},  # Total successful calls
        "majority_accuracy": 0,
        "unanimous_accuracy": 0,
        "unanimous_coverage": 0,
        "agreement_patterns": Counter(),
        "subject_accuracy": defaultdict(lambda: {eval_name: 0 for eval_name in evaluators} | {"total": 0}),
        "confidence_stats": {"correct": [], "incorrect": []},
        "jb_distribution": Counter(),
        "jb_vs_error": {"0": {"correct": 0, "incorrect": 0}, "1": {"correct": 0, "incorrect": 0}, "2": {"correct": 0, "incorrect": 0}, "3": {"correct": 0, "incorrect": 0}},
    }
    
    correct_by_eval = {eval_name: 0 for eval_name in evaluators}
    correct_majority = 0
    correct_unanimous = 0
    unanimous_count = 0
    
    for record in round1_records:
        round1 = record.get("round1", {})
        
        # Track failures and successes separately
        for eval_name in evaluators:
            parse_ok = round1.get(f"parse_ok_{eval_name}", False)
            if parse_ok:
                metrics["evaluator_total"][eval_name] += 1
                if round1.get(f"correct_{eval_name}"):
                    correct_by_eval[eval_name] += 1
            else:
                metrics["evaluator_failed"][eval_name] += 1
        
        # Agreement pattern
        pattern = round1.get("agreement_pattern", "unknown")
        metrics["agreement_patterns"][pattern] += 1
        
        # Majority accuracy
        majority = round1.get("majority_choice")
        gold = record.get("gold_answer")
        if majority and majority == gold:
            correct_majority += 1
        
        # Unanimous accuracy (only count if pattern is actually unanimous, not incomplete/insufficient)
        pattern = round1.get("agreement_pattern", "unknown")
        unanimous = round1.get("unanimous_choice")
        if pattern.startswith("unanimous") and unanimous:  # Only count true unanimity
            unanimous_count += 1
            if unanimous == gold:
                correct_unanimous += 1
        
        # Subject breakdown
        subject = record.get("subject")
        if subject:
            metrics["subject_accuracy"][subject]["total"] += 1
            for eval_name in evaluators:
                if round1.get(f"correct_{eval_name}"):
                    metrics["subject_accuracy"][subject][eval_name] += 1
        
        # Confidence stats
        for eval_name in evaluators:
            eval_result = round1.get(f"evaluator_{eval_name}")
            if eval_result:
                conf = eval_result.get("confidence", 0)
                is_correct = round1.get(f"correct_{eval_name}", False)
                if is_correct:
                    metrics["confidence_stats"]["correct"].append(conf)
                else:
                    metrics["confidence_stats"]["incorrect"].append(conf)
                
                # JB distribution
                jb = eval_result.get("jb", 0)
                metrics["jb_distribution"][jb] += 1
                metrics["jb_vs_error"][str(jb)]["correct" if is_correct else "incorrect"] += 1
    
    total = metrics["total_questions"]
    if total > 0:
        # Calculate accuracy only over successful calls (not failures)
        for eval_name in evaluators:
            total_successful = metrics["evaluator_total"][eval_name]
            if total_successful > 0:
                metrics["evaluator_accuracy"][eval_name] = round(correct_by_eval[eval_name] / total_successful, 4)
            else:
                metrics["evaluator_accuracy"][eval_name] = 0.0
        
        metrics["majority_accuracy"] = round(correct_majority / total, 4)
        metrics["unanimous_accuracy"] = round(correct_unanimous / unanimous_count, 4) if unanimous_count > 0 else 0
        metrics["unanimous_coverage"] = round(unanimous_count / total, 4)
    
    # Mean confidence
    metrics["mean_confidence_correct"] = round(sum(metrics["confidence_stats"]["correct"]) / len(metrics["confidence_stats"]["correct"]), 2) if metrics["confidence_stats"]["correct"] else 0
    metrics["mean_confidence_incorrect"] = round(sum(metrics["confidence_stats"]["incorrect"]) / len(metrics["confidence_stats"]["incorrect"]), 2) if metrics["confidence_stats"]["incorrect"] else 0
    
    # Convert Counter to dict
    metrics["agreement_patterns"] = dict(metrics["agreement_patterns"])
    metrics["jb_distribution"] = dict(metrics["jb_distribution"])
    metrics["subject_accuracy"] = {k: dict(v) for k, v in metrics["subject_accuracy"].items()}
    
    return metrics


def compute_round2_metrics(round2_records: List[dict], evaluators: List[str] = None) -> dict:
    """Compute Round 2 metrics."""
    if evaluators is None:
        evaluators = DEFAULT_EVALUATORS
    
    metrics = {
        "total_split_questions": len(round2_records),
        "convergence_rate": 0,
        "accuracy_before": {k: 0 for k in ["A", "B", "C", "majority"]},
        "accuracy_after": {k: 0 for k in ["A", "B", "C", "majority"]},
        "false_consensus_rate": 0,
        "net_error_change": 0,
        "cost_proxy": 0,
    }
    
    converged_count = 0
    false_consensus_count = 0
    errors_before = 0
    errors_after = 0
    corrected_count = 0
    
    # Use first 3 evaluators for R2 (legacy behavior)
    r2_evaluators = evaluators[:3] if len(evaluators) >= 3 else evaluators
    
    for record in round2_records:
        round1 = record.get("round1", {})
        round2 = record.get("round2", {})
        gold = record.get("gold_answer")
        
        # Convergence
        if round2.get("converged"):
            converged_count += 1
            # Check if converged to wrong answer
            unanimous_r2 = round2.get("unanimous_choice")
            if unanimous_r2 and unanimous_r2 != gold:
                false_consensus_count += 1
        
        # Accuracy before/after
        for eval_name in r2_evaluators:
            correct_before = round1.get(f"correct_{eval_name}", False)
            if not correct_before:
                errors_before += 1
            
            eval_result_r2 = round2.get(f"evaluator_{eval_name}")
            if eval_result_r2:
                choice_r2 = eval_result_r2.get("final_choice")
                correct_after = (choice_r2 == gold)
                if correct_after:
                    metrics["accuracy_after"][eval_name] += 1
                    if not correct_before:
                        corrected_count += 1
                else:
                    errors_after += 1
                if correct_before:
                    metrics["accuracy_before"][eval_name] += 1
    
    total = metrics["total_split_questions"]
    if total > 0:
        metrics["convergence_rate"] = round(converged_count / total, 4)
        metrics["false_consensus_rate"] = round(false_consensus_count / converged_count, 4) if converged_count > 0 else 0
        metrics["net_error_change"] = errors_after - errors_before
        metrics["cost_proxy"] = round(total * 3 / corrected_count, 2) if corrected_count > 0 else 0  # 3 calls per question
        
        for eval_name in r2_evaluators:
            metrics["accuracy_before"][eval_name] = round(metrics["accuracy_before"][eval_name] / total, 4)
            metrics["accuracy_after"][eval_name] = round(metrics["accuracy_after"][eval_name] / total, 4)
    
    return metrics
