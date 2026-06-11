"""
383 mid-run companion analysis.
Reads 383_run_log_temp.txt checkpoint + each result JSON and prints:
  - LP-13 coverage state + element verdict per run
  - Per-finding LP appearance table across completed runs
  - Material-risk disappearances so far
Run at any time while (or after) the harness is running.
Usage: python build_log/_383_midrun_analysis.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

CAM_ROOT = Path(__file__).parent.parent.resolve()
CHECKPOINT_FILE = CAM_ROOT / "build_log" / "383_run_log_temp.txt"
OUT_MD = CAM_ROOT / "build_log" / "383_midrun_snapshot.md"

PRESENCE_TIER = frozenset({
    "explicitly_present",
    "implicitly_present",
    "covered_by_default_law",
    "covered_in_other_LP",
})


def derive_run_quality(result: dict) -> str:
    """Derive quality from _stage_data (checkpoint's run_quality may be stale 'unknown')."""
    if not result:
        return "unknown"
    sd = result.get("_stage_data", {}) or {}
    sm = sd.get("synthesis_meta", {}) or {}
    fcm = sd.get("finding_consequence_meta", {}) or {}
    em = sd.get("extraction_meta", {}) or {}
    synthesis_complete = sm.get("directional_synthesis_status") == "complete"
    evaluators_complete = sm.get("evaluators_completed", 0) == 3
    consequence_ok = fcm.get("absent", 0) == 0 and fcm.get("status") == "applied"
    no_fallbacks = not em.get("fallback_used", False) and not fcm.get("fallback_used", False)
    if synthesis_complete and evaluators_complete and consequence_ok and no_fallbacks:
        return "clean"
    if synthesis_complete and evaluators_complete:
        return "degraded"
    return "incomplete"


def load_checkpoint():
    if not CHECKPOINT_FILE.exists():
        print(f"No checkpoint yet: {CHECKPOINT_FILE}")
        return []
    entries = []
    for line in CHECKPOINT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return [e for e in entries if e.get("status") == "completed"]


def load_result(result_path):
    p = Path(result_path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_hard_case(per_eval_verdicts: list) -> bool:
    """True when all evaluators gave presence-tier labels but all distinct
    (no majority — pre-DEF-010a would have produced 'unclear' via Counter split)."""
    if len(per_eval_verdicts) < 2:
        return False
    return (
        all(v in PRESENCE_TIER for v in per_eval_verdicts)
        and len(set(per_eval_verdicts)) == len(per_eval_verdicts)
    )


def get_lp13_coverage(result):
    """Extract LP-13 coverage + element verdicts from pipeline_results."""
    if not result:
        return {}

    # coverage_assessment is a list of LP dicts keyed by issue_area_id
    ca = result.get("coverage_assessment", []) or []
    lp13 = next((x for x in ca if x.get("issue_area_id") == "LP-13"), {})

    # Check Stage 7 attention items via coverage_summary
    cs = result.get("coverage_summary", {}) or {}
    attention = cs.get("attention_items", []) or []
    in_attention = any(
        a.get("id") == "LP-13" or a.get("issue_area_id") == "LP-13"
        or a.get("lp_id") == "LP-13"
        or "LP-13" in str(a.get("lp_ids", ""))
        for a in attention
    )

    # Final cross-provision findings implicating LP-13
    cpfs = result.get("cross_provision_findings", []) or []
    lp13_findings = [
        f for f in cpfs
        if "LP-13" in (f.get("implicated_lps") or [])
    ]

    # LP-13.negligence_carveouts element verdicts (list structure)
    ev_list = lp13.get("element_verdicts", []) or []
    carveout_elem = next(
        (e for e in ev_list
         if "negligence" in (e.get("element_id") or "").lower()
         or "carveout" in (e.get("element_id") or "").lower()),
        {}
    )
    per_eval_verdicts = [
        v.get("verdict") for v in (carveout_elem.get("evaluator_verdicts") or [])
    ]
    carveout_merged = carveout_elem.get("verdict")
    hard_case = is_hard_case(per_eval_verdicts)

    return {
        "coverage_state": lp13.get("coverage_state"),
        "coverage_state_baseline": lp13.get("coverage_state_baseline"),
        "requires_attention": lp13.get("requires_attention"),
        "in_attention_items": in_attention,
        "coverage_method": lp13.get("coverage_method"),
        "fallback_used": lp13.get("fallback_used"),
        "negligence_carveouts_per_eval": per_eval_verdicts,
        "negligence_carveouts_merged": carveout_merged,
        "hard_case_this_run": hard_case,
        "final_findings_count": len(lp13_findings),
        "final_findings": [
            {
                "title": f.get("title"),
                "type": f.get("finding_type"),
                "bucket": (f.get("p2pp_routing") or {}).get("bucket"),
                "consequence": f.get("use_consequence"),
                "materiality": f.get("materiality"),
            }
            for f in lp13_findings
        ],
    }


def get_dir_findings(result):
    if not result:
        return []
    cpfs = result.get("cross_provision_findings", []) or []
    return [f for f in cpfs if f.get("finding_type") == "directional_mismatch"]


def normalize_lp(finding):
    lps = finding.get("implicated_lps") or []
    return tuple(sorted(lps))


def main():
    runs = load_checkpoint()
    if not runs:
        print("No completed runs yet.")
        return

    n = len(runs)
    print(f"\n=== 383 Mid-Run Snapshot | {n} completed runs ===\n")

    lines = [f"# 383 Mid-Run Snapshot\n\n**Completed runs:** {n}  \n"]

    # ── Per-run table ──────────────────────────────────────────────────────
    lines.append("## Run Log\n")
    lines.append("| # | Job ID | Quality | API | Elapsed | Dir | Risk | RN | Imp |")
    lines.append("|---|--------|---------|-----|---------|-----|------|----|-----|")
    for r in runs:
        result = load_result(r.get("result_path"))
        quality = derive_run_quality(result)
        lines.append(
            f"| {r['run_number']} | {r['job_id'][-6:]} | {quality} "
            f"| {r.get('api_calls',0)} | {r.get('elapsed_sec',0):.0f}s "
            f"| {r.get('dir_findings',0)} | {r.get('risk_bucket',0)} "
            f"| {r.get('review_bucket',0)} | {r.get('improvement_bucket',0)} |"
        )
    lines.append("")

    # ── LP-13 spotlight ────────────────────────────────────────────────────
    lines.append("## LP-13 Spotlight\n")
    lines.append("| Run | Job | coverage_state | in_Stage7 | Per-eval labels (negligence_carveouts) | Merged | Hard case? |")
    lines.append("|-----|-----|---------------|-----------|---------------------------------------|--------|------------|")
    lp13_states = []
    hard_case_seen = False
    all_covered = True
    none_forwarded = True
    for r in runs:
        result = load_result(r.get("result_path"))
        cov = get_lp13_coverage(result)
        state = cov.get("coverage_state") or "?"
        lp13_states.append(state)
        if state != "covered":
            all_covered = False
        in_att = cov.get("in_attention_items", False)
        if in_att:
            none_forwarded = False
        per_eval = cov.get("negligence_carveouts_per_eval") or []
        merged = cov.get("negligence_carveouts_merged") or "?"
        hard = cov.get("hard_case_this_run", False)
        if hard:
            hard_case_seen = True
        labels_str = " / ".join(per_eval) if per_eval else "?"
        ff_count = cov.get("final_findings_count", 0)
        lines.append(
            f"| {r['run_number']} | {r['job_id'][-6:]} | `{state}` "
            f"| {'YES' if in_att else 'no'} | `{labels_str}` | `{merged}` "
            f"| {'YES' if hard else 'no'} |"
        )
    lines.append("")

    observed_stable = all_covered and none_forwarded and n > 0
    lines.append(f"**observed_stable_covered_across_runs:** `{observed_stable}`  ")
    lines.append(f"**hard_case_seen:** `{hard_case_seen}`\n")

    # LP-13 verdict
    unique_states = set(lp13_states)
    if observed_stable:
        if hard_case_seen:
            lp13_verdict = "LP-13 deterministically covered — hard case recurred and was corrected by DEF-010a"
        else:
            lp13_verdict = "LP-13 deterministically covered — hard case NOT observed in this sample (no EP/CD/IP scatter)"
    elif "review_needed" in unique_states and "covered" in unique_states:
        lp13_verdict = "LP-13 still flickers"
    elif all(s == "review_needed" for s in lp13_states):
        lp13_verdict = "LP-13 appears as review_needed consistently — check Stage 7 forwarding"
    else:
        lp13_verdict = f"LP-13 behavior mixed: {unique_states}"
    lines.append(f"**LP-13 verdict (N={n}):** `{lp13_verdict}`\n")

    # ── Finding stability across runs ──────────────────────────────────────
    lines.append("## Finding Stability (by LP id)\n")
    lp_appearances = defaultdict(list)   # lp_key -> list of (run#, bucket, consequence, materiality)
    for r in runs:
        result = load_result(r.get("result_path"))
        findings = get_dir_findings(result)
        seen_lps = set()
        for f in findings:
            lp_key = normalize_lp(f)
            if lp_key in seen_lps:
                continue
            seen_lps.add(lp_key)
            bucket = (f.get("p2pp_routing") or {}).get("bucket", "?")
            consequence = f.get("use_consequence", "?")
            materiality = f.get("materiality", "?")
            lp_appearances[lp_key].append((r["run_number"], bucket, consequence, materiality))

    # Material-risk disappearances
    disappearances = []
    lines.append("| LP | Appearances | Buckets | Consequence | Materiality | Stable? | Material Risk? |")
    lines.append("|----|-------------|---------|-------------|-------------|---------|----------------|")
    for lp_key in sorted(lp_appearances.keys()):
        rows = lp_appearances[lp_key]
        app_runs = [x[0] for x in rows]
        buckets = sorted(set(x[1] for x in rows))
        consequences = sorted(set(x[2] for x in rows))
        materialities = sorted(set(x[3] for x in rows))
        stable = len(buckets) == 1 and len(app_runs) == n
        ever_risk = "risk" in buckets
        harmful_highmid = (
            any(c == "harmful" for c in consequences) and
            any(m in ("high", "medium") for m in materialities)
        )
        if harmful_highmid and ever_risk and len(app_runs) < n:
            disappearances.append({
                "lp": lp_key,
                "appearance_rate": f"{len(app_runs)}/{n}",
                "buckets": buckets,
                "consequences": consequences,
                "materialities": materialities,
            })
        lines.append(
            f"| {','.join(lp_key)} | {len(app_runs)}/{n} | {'/'.join(buckets)} "
            f"| {'/'.join(consequences)} | {'/'.join(materialities)} "
            f"| {'yes' if stable else 'NO'} | {'YES' if harmful_highmid else 'no'} |"
        )
    lines.append("")

    # ── Material-risk disappearances ───────────────────────────────────────
    lines.append("## Material-Risk Disappearances\n")
    if disappearances:
        lines.append(f"**{len(disappearances)} finding(s) are harmful + high/medium + ever Risk but absent in some runs:**\n")
        for d in disappearances:
            lines.append(f"- **{','.join(d['lp'])}**: rate={d['appearance_rate']} | "
                        f"buckets={d['buckets']} | consequence={d['consequences']} | materiality={d['materialities']}")
    else:
        lines.append(f"None detected across {n} completed runs.")
    lines.append("")

    # ── Write markdown ─────────────────────────────────────────────────────
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSnapshot written to: {OUT_MD}")


if __name__ == "__main__":
    main()
