"""
Full 10-tenant validation runner for CAM Lease Analyzer pipeline.
Runs all tenants, compares against ground truth, computes precision/recall.
"""
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.adapters.lease_review.lease_adapter import run_lease_analysis

find_and_load_env()

TEST_DATA = CAM_ROOT / "05 Lease Analyzer" / "test_data"
TEMPLATE = str(TEST_DATA / "standard_template.txt")
GROUND_TRUTH_DIR = TEST_DATA / "ground_truth"
OUTPUT_DIR = CAM_ROOT / "05 Lease Analyzer" / "Runs" / "test_004"

TENANTS = [
    "T-01_clean.txt",
    "T-02_cosmetic.txt",
    "T-03_obvious.txt",
    "T-04_subtle.txt",
    "T-05_definition.txt",
    "T-06_caps.txt",
    "T-07_aggressive.txt",
    "T-08_force_majeure.txt",
    "T-09_mixed.txt",
    "T-10_sophisticated.txt",
]


def load_ground_truth(tenant_file: str) -> dict:
    """Load ground truth for a tenant. Returns {provision_id: verdict}.

    Supports ground truth format:
        {"deviations": [{provision_id, ...}], "non_deviations": ["LP-01", ...]}
    Also supports legacy format:
        {"provisions": [{provision_id, expected_verdict, ...}]}
    """
    prefix = tenant_file.split("_")[0]  # e.g. "T-01"
    truth_path = GROUND_TRUTH_DIR / f"{prefix}_truth.json"
    with open(truth_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    truth = {}
    # Primary format: deviations / non_deviations
    for d in data.get("deviations", []):
        truth[d["provision_id"]] = "DEVIATES"
    for pid in data.get("non_deviations", []):
        truth[pid] = "CONFORMS"
    # Cosmetic changes count as CONFORMS (not deviations)
    for item in data.get("cosmetic_changes", []):
        pid = item["provision_id"] if isinstance(item, dict) else item
        if pid not in truth:
            truth[pid] = "CONFORMS"
    # Legacy format: provisions array
    for p in data.get("provisions", []):
        pid = p["provision_id"]
        truth[pid] = p.get("expected_verdict", "CONFORMS")
    return truth


def compare_results(result: dict, ground_truth: dict) -> dict:
    """Compare pipeline results against ground truth."""
    tp = 0  # True positive: correctly detected DEVIATES
    fp = 0  # False positive: said DEVIATES but truth is CONFORMS
    fn = 0  # False negative: said CONFORMS but truth is DEVIATES
    tn = 0  # True negative: correctly detected CONFORMS

    details = []
    for prov in result["provisions"]:
        pid = prov["provision_id"]
        predicted = prov["final_verdict"]
        actual = ground_truth.get(pid, "CONFORMS")

        # UNCLEAR = not a deviation claim, exclude from confusion matrix
        pred_dev = predicted == "DEVIATES"
        pred_unclear = predicted == "UNCLEAR"
        actual_dev = actual == "DEVIATES"

        if pred_unclear:
            # UNCLEAR provisions don't count as TP/FP/FN/TN
            status = "UNCLEAR"
        elif pred_dev and actual_dev:
            tp += 1
            status = "TP"
        elif pred_dev and not actual_dev:
            fp += 1
            status = "FP"
        elif not pred_dev and actual_dev:
            fn += 1
            status = "FN"
        else:
            tn += 1
            status = "TN"

        details.append({
            "provision_id": pid,
            "predicted": predicted,
            "actual": actual,
            "status": status,
            "severity": prov.get("severity", ""),
            "challenge": prov.get("challenge_finding", ""),
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "details": details,
    }


def main():
    config = {"output_dir": str(OUTPUT_DIR)}

    all_results = {}
    total_tp = total_fp = total_fn = total_tn = 0
    total_api_calls = 0
    total_time = 0.0
    rule_fires = {}

    for tenant_idx, tenant_file in enumerate(TENANTS):
        tenant_id = tenant_file.split("_")[0]  # e.g. "T-04"
        run_id = tenant_file.replace(".txt", "")

        # Skip if already completed
        result_path = OUTPUT_DIR / run_id / "pipeline_results.json"
        if result_path.exists():
            print(f"\n{'='*60}", flush=True)
            print(f"LOADING CACHED: {tenant_file}", flush=True)
            with open(result_path, "r", encoding="utf-8") as f:
                result = json.load(f)
        else:
            # Cooldown between tenants to reduce Gemini rate limit pressure
            if tenant_idx > 0:
                print(f"\n[Cooldown] Waiting 15s before next tenant...", flush=True)
                time.sleep(15)
            print(f"\n{'='*60}", flush=True)
            print(f"RUNNING: {tenant_file}", flush=True)
            print(f"{'='*60}", flush=True)
            tenant_path = str(TEST_DATA / "tenants" / tenant_file)
            try:
                result = run_lease_analysis(
                    template_path=TEMPLATE,
                    tenant_path=tenant_path,
                    run_id=run_id,
                    config=config,
                )
            except Exception as e:
                print(f"FAILED: {tenant_file}: {e}", flush=True)
                all_results[tenant_id] = {"error": str(e)}
                continue

        # Load ground truth and compare
        ground_truth = load_ground_truth(tenant_file)
        comparison = compare_results(result, ground_truth)

        total_tp += comparison["tp"]
        total_fp += comparison["fp"]
        total_fn += comparison["fn"]
        total_tn += comparison["tn"]
        total_api_calls += result.get("api_calls_total", 0)
        total_time += result.get("elapsed_sec", 0)

        # Track rule fires
        for prov in result["provisions"]:
            for rule_id in prov.get("cam_metadata", {}).get("rules_fired", []):
                rule_fires[rule_id] = rule_fires.get(rule_id, 0) + 1

        # Print tenant summary
        s = result["summary"]
        print(f"\n{tenant_id} Results:", flush=True)
        print(f"  Verdicts: C={s['conforms']} D={s['deviates']} U={s['unclear']}", flush=True)
        print(f"  Severity: Cr={s['critical']} H={s['high']} M={s['medium']} L={s['low']}", flush=True)
        print(f"  Metrics: P={comparison['precision']:.2f} R={comparison['recall']:.2f} F1={comparison['f1']:.2f}", flush=True)
        print(f"  Confusion: TP={comparison['tp']} FP={comparison['fp']} FN={comparison['fn']} TN={comparison['tn']}", flush=True)
        print(f"  API calls: {result.get('api_calls_total', 0)} Time: {result.get('elapsed_sec', 0)}s", flush=True)

        # Show mismatches and unclear
        for d in comparison["details"]:
            if d["status"] in ("FP", "FN", "UNCLEAR"):
                print(f"  ** {d['status']}: {d['provision_id']} predicted={d['predicted']} actual={d['actual']} sev={d['severity']} challenge={d['challenge']}", flush=True)

        all_results[tenant_id] = {
            "summary": result["summary"],
            "comparison": comparison,
            "api_calls": result.get("api_calls_total", 0),
            "elapsed_sec": result.get("elapsed_sec", 0),
            "models": result.get("models_used", {}),
        }

    # Overall summary
    total_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    total_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    total_f1 = 2 * total_precision * total_recall / (total_precision + total_recall) if (total_precision + total_recall) > 0 else 0.0

    print(f"\n{'='*60}", flush=True)
    print("OVERALL VALIDATION RESULTS", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Tenants: {len(all_results)}", flush=True)
    print(f"Total provisions checked: {total_tp + total_fp + total_fn + total_tn}", flush=True)
    print(f"Confusion matrix: TP={total_tp} FP={total_fp} FN={total_fn} TN={total_tn}", flush=True)
    print(f"Precision: {total_precision:.4f}", flush=True)
    print(f"Recall: {total_recall:.4f}", flush=True)
    print(f"F1: {total_f1:.4f}", flush=True)
    print(f"Total API calls: {total_api_calls}", flush=True)
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f}min)", flush=True)
    print(f"\nRule fire summary:", flush=True)
    for rule_id, count in sorted(rule_fires.items()):
        print(f"  {rule_id}: {count} fires", flush=True)

    # Save validation summary
    summary_path = OUTPUT_DIR / "validation_summary.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "overall": {
                "tp": total_tp, "fp": total_fp, "fn": total_fn, "tn": total_tn,
                "precision": round(total_precision, 4),
                "recall": round(total_recall, 4),
                "f1": round(total_f1, 4),
                "total_api_calls": total_api_calls,
                "total_time_sec": round(total_time, 1),
                "rule_fires": rule_fires,
            },
            "per_tenant": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nValidation summary saved to {summary_path}", flush=True)


if __name__ == "__main__":
    main()
