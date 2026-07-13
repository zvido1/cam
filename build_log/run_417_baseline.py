"""
Step 417 — Post-416 Stage 5 baseline measurement.

N=10 runs on the Atreca EX-10.18 fixture using the frozen evaluator panel
(post-414/416). Measures residual Stage 5 coverage-state variance after
silent fallback is blocked (414) and config integrity is enforced (416).

Fixture: atreca_eastjamie_southsf_lease.txt (same as Steps 407/411)
Mode: standard Mode C, widen_partial=False (narrow gate = production default)
N: 10 (floor per spec)

Outputs:
  _417_results/run_NNN_pipeline.json   — full pipeline result per run
  _417_results/run_NNN_summary.json    — LP coverage_state + element verdicts per run
  _417_results/417_baseline.json       — cross-run analysis (frequency distributions,
                                          per-role flip counts, variance classification)
  build_log/417_post_416_stage5_baseline.md  — human-readable report

Run from CAM root:
  PYTHONPATH=C:/Users/Owner/OneDrive/CAM python build_log/run_417_baseline.py

Cost estimate: ~17-25 min × 10 = 170-250 min (~3-4 hours), ~20-30M tokens.
"""

import sys, os, json, time, math
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, r"C:/Users/Owner/OneDrive/CAM")

from dotenv import load_dotenv
load_dotenv(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")

TENANT_PATH = r"C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt"
OUT_DIR     = r"C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer/_417_results"
REPORT_PATH = r"C:/Users/Owner/OneDrive/CAM/build_log/417_post_416_stage5_baseline.md"
N_RUNS = 10

os.makedirs(OUT_DIR, exist_ok=True)

from cam.adapters.lease_review.lease_adapter import run_lease_coverage_only


# ── helpers ───────────────────────────────────────────────────────────────────

def extract_lp_summary(result: dict) -> dict:
    """Pull per-LP coverage_state, element verdicts, and evaluator meta."""
    ca = result.get("coverage_assessment") or []
    lps = {}
    for lp in ca:
        lp_id = lp.get("issue_area_id", "?")
        evs = lp.get("element_verdicts") or []
        # Per-element: merged verdict + per-role (evaluator_verdicts)
        elements = []
        for ev in evs:
            role_verdicts = {}
            for ev_dict in (ev.get("evaluator_verdicts") or []):
                role = ev_dict.get("role")
                verdict = ev_dict.get("verdict")
                if role and verdict:
                    role_verdicts[role] = verdict
            elements.append({
                "element_id": ev.get("element_id"),
                "element_label": ev.get("element_label"),
                "criticality": ev.get("criticality"),
                "merged_verdict": ev.get("verdict"),
                "role_verdicts": role_verdicts,
            })
        # Evaluator meta (is_fallback, actual_model per role)
        emeta = lp.get("evaluator_meta") or {}
        role_meta = {}
        for role, m in emeta.items():
            role_meta[role] = {
                "actual_model": m.get("actual_model"),
                "is_fallback": m.get("is_fallback", False),
                "fallback_reason": m.get("fallback_reason"),
                "completed": m.get("completed"),
            }
        lps[lp_id] = {
            "coverage_state": lp.get("coverage_state"),
            "requires_attention": lp.get("requires_attention", False),
            "coverage_state_baseline": lp.get("coverage_state_baseline"),
            "verdict_distance": lp.get("verdict_distance"),
            "elements": elements,
            "evaluator_meta": role_meta,
        }
    return lps


def role_flips(run_lp_data: list[dict], lp_id: str, role: str) -> list[str]:
    """Return list of merged element-level verdicts for a given role across runs."""
    return [
        run.get(lp_id, {}).get("elements", [])
        for run in run_lp_data
    ]


# ── Run N=10 ──────────────────────────────────────────────────────────────────

run_summaries = []   # list of {run_n, run_id, elapsed, lps: {lp_id: ...}}
run_start_global = time.time()

print(f"\n{'='*70}", flush=True)
print(f"[417] Baseline measurement — N={N_RUNS} runs on Atreca EX-10.18", flush=True)
print(f"[417] Fixture: {os.path.basename(TENANT_PATH)}", flush=True)
print(f"[417] Config: widen_partial=False (production default / narrow gate)", flush=True)
print(f"[417] Started: {datetime.now(timezone.utc).isoformat()}", flush=True)
print(f"{'='*70}\n", flush=True)

for i in range(1, N_RUNS + 1):
    run_id = f"lease_417_atreca_run{i:02d}"
    print(f"\n[417] === Run {i}/{N_RUNS} — {run_id} ===", flush=True)
    t0 = time.time()
    result = run_lease_coverage_only(
        tenant_path=TENANT_PATH,
        run_id=run_id,
        config={},   # default config: widen_partial=False
    )
    elapsed = round(time.time() - t0, 1)
    print(f"[417] Run {i} complete in {elapsed}s ({elapsed/60:.1f} min)", flush=True)

    # Save full pipeline result
    full_path = os.path.join(OUT_DIR, f"run_{i:02d}_pipeline.json")
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    # Extract summary
    lp_data = extract_lp_summary(result)
    summary = {
        "run_n": i,
        "run_id": run_id,
        "elapsed_sec": elapsed,
        "lps": lp_data,
    }
    run_summaries.append(summary)

    summ_path = os.path.join(OUT_DIR, f"run_{i:02d}_summary.json")
    with open(summ_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    # Quick coverage state distribution
    cs_dist = Counter(v["coverage_state"] for v in lp_data.values())
    print(f"  Coverage states: {dict(cs_dist)}", flush=True)

    # Quick fallback check
    any_fallback = any(
        m.get("is_fallback")
        for lp in lp_data.values()
        for m in (lp.get("evaluator_meta") or {}).values()
    )
    if any_fallback:
        print(f"  *** FALLBACK DETECTED — 414 regression — investigate before continuing ***", flush=True)
    else:
        print(f"  Fallback: none (414 intact)", flush=True)

total_elapsed = round(time.time() - run_start_global, 1)
print(f"\n[417] All {N_RUNS} runs complete in {total_elapsed}s ({total_elapsed/60:.1f} min)", flush=True)


# ── Cross-run analysis ─────────────────────────────────────────────────────────

all_lp_ids = sorted({lp_id for s in run_summaries for lp_id in s["lps"]})
N = len(run_summaries)

print(f"\n[417] Analysing {len(all_lp_ids)} LPs across {N} runs...", flush=True)


# Per-LP coverage_state frequency distribution
lp_state_freq = {}   # lp_id -> Counter of coverage_state
for lp_id in all_lp_ids:
    states = [s["lps"].get(lp_id, {}).get("coverage_state") for s in run_summaries]
    lp_state_freq[lp_id] = Counter(s for s in states if s is not None)

# Classify LPs by stability
stable_10 = []   # 10/10
boundary_9 = []  # 9/1 or 8/2
split_67   = []  # 7/3 or 6/4
genuine_55 = []  # 5/5 or worse
for lp_id in all_lp_ids:
    freq = lp_state_freq[lp_id]
    top = freq.most_common(1)
    if not top:
        continue
    max_count = top[0][1]
    if max_count == N:
        stable_10.append(lp_id)
    elif max_count >= N - 2:
        boundary_9.append(lp_id)
    elif max_count >= N - 4:
        split_67.append(lp_id)
    else:
        genuine_55.append(lp_id)

# Per-role flip counts
# For each LP and each element, collect per-role verdict across all runs
# A "flip" = the role's verdict on that element differs from its own mode
role_flip_counts = {"A": 0, "B": 0, "C": 0}
role_flip_lps = {"A": set(), "B": set(), "C": set()}
role_flip_elements = {"A": [], "B": [], "C": []}

# Also track: did the merged coverage_state for the LP change due to each role?
# (harder to attribute — track role flips as proxy)

for lp_id in all_lp_ids:
    # Collect all element records across runs for this LP
    all_runs_elements = [s["lps"].get(lp_id, {}).get("elements", []) for s in run_summaries]
    if not any(all_runs_elements):
        continue

    # Find all element_ids that appear
    element_ids = sorted({e["element_id"] for run_els in all_runs_elements for e in run_els if e.get("element_id")})

    for el_id in element_ids:
        for role in ("A", "B", "C"):
            verdicts_for_role = []
            for run_els in all_runs_elements:
                match = next((e for e in run_els if e.get("element_id") == el_id), None)
                if match:
                    v = (match.get("role_verdicts") or {}).get(role)
                    if v:
                        verdicts_for_role.append(v)
            if len(verdicts_for_role) < 2:
                continue
            mode_v = Counter(verdicts_for_role).most_common(1)[0][0]
            flips = sum(1 for v in verdicts_for_role if v != mode_v)
            if flips > 0:
                role_flip_counts[role] += flips
                role_flip_lps[role].add(lp_id)
                role_flip_elements[role].append({
                    "lp_id": lp_id,
                    "element_id": el_id,
                    "flips": flips,
                    "mode": mode_v,
                    "all_values": Counter(verdicts_for_role),
                })

# Per-LP element churn vs state churn
# LPs where elements flip but final coverage_state is stable
element_churn_stable_state = []
element_churn_unstable_state = []
for lp_id in all_lp_ids:
    state_stable = (lp_id in stable_10)
    has_element_churn = any(
        lp_id in role_flip_lps[r] for r in ("A", "B", "C")
    )
    if has_element_churn and state_stable:
        element_churn_stable_state.append(lp_id)
    elif has_element_churn and not state_stable:
        element_churn_unstable_state.append(lp_id)

# Fallback audit across all runs
fallback_events = []
for s in run_summaries:
    for lp_id, lp in s["lps"].items():
        for role, m in (lp.get("evaluator_meta") or {}).items():
            if m.get("is_fallback"):
                fallback_events.append({
                    "run_n": s["run_n"],
                    "lp_id": lp_id,
                    "role": role,
                    "actual_model": m.get("actual_model"),
                    "fallback_reason": m.get("fallback_reason"),
                })

# Overall wobble rate
unstable_lps = [lp for lp in all_lp_ids if lp not in stable_10]
wobble_rate = len(unstable_lps) / len(all_lp_ids) if all_lp_ids else 0

# Save JSON analysis
analysis = {
    "n_runs": N,
    "n_lps": len(all_lp_ids),
    "total_elapsed_sec": total_elapsed,
    "wobble_rate": wobble_rate,
    "stable_10": stable_10,
    "boundary_9": boundary_9,
    "split_67": split_67,
    "genuine_55": genuine_55,
    "unstable_lps": unstable_lps,
    "lp_state_freq": {lp: dict(freq) for lp, freq in lp_state_freq.items()},
    "role_flip_counts": role_flip_counts,
    "role_flip_lps": {r: sorted(lps) for r, lps in role_flip_lps.items()},
    "role_flip_elements": role_flip_elements,
    "element_churn_stable_state": element_churn_stable_state,
    "element_churn_unstable_state": element_churn_unstable_state,
    "fallback_events": fallback_events,
}
with open(os.path.join(OUT_DIR, "417_baseline.json"), "w", encoding="utf-8") as f:
    json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

print(f"[417] Analysis saved to {OUT_DIR}/417_baseline.json", flush=True)


# ── Write markdown report ─────────────────────────────────────────────────────

def md_freq_table(lp_id: str, freq: Counter, n: int) -> str:
    rows = []
    for state, count in sorted(freq.items(), key=lambda x: -x[1]):
        pct = f"{count}/{n}"
        rows.append(f"| {state} | {pct} |")
    return "\n".join(rows)


total_role_flips = sum(role_flip_counts.values())

lines = [
    "# 417 — Post-416 Stage 5 Baseline Measurement",
    "",
    f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
    f"**Fixture:** atreca_eastjamie_southsf_lease.txt (same as Steps 407/411)",
    f"**Panel:** post-414/416 frozen stack (A=claude-sonnet-4-6 / B=gpt-5.5 / C=grok-4.3)",
    f"**N runs:** {N}",
    f"**Total wall-clock:** {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)",
    f"**Config:** widen_partial=False (production default / narrow gate)",
    "",
    "---",
    "",
    "## Run Inventory",
    "",
    "| Run | Run ID | Wall-clock (s) |",
    "|-----|--------|----------------|",
]
for s in run_summaries:
    lines.append(f"| {s['run_n']} | {s['run_id']} | {s['elapsed_sec']} |")

lines += [
    "",
    "---",
    "",
    "## Overall Variance Rate",
    "",
    f"- Total LPs measured: **{len(all_lp_ids)}**",
    f"- LPs with any coverage_state change across {N} runs: **{len(unstable_lps)}**",
    f"- Overall wobble rate: **{wobble_rate:.1%}** ({len(unstable_lps)}/{len(all_lp_ids)})",
    "",
    f"*(Pre-416 reference: ~31% from Step 411 N=2 Atreca pair)*",
    "",
    "---",
    "",
    "## LP Coverage-State Frequency Table",
    "",
    f"All {len(all_lp_ids)} LPs. Frequency = count/N={N} runs.",
    "",
    "### Stable 10/10",
    "",
    f"{len(stable_10)} LPs: {', '.join(stable_10) if stable_10 else 'none'}",
    "",
    "### Boundary noise (8/2 or 9/1)",
    "",
    f"{len(boundary_9)} LPs:",
    "",
]
for lp_id in boundary_9:
    freq = lp_state_freq[lp_id]
    lines.append(f"**{lp_id}**: " + " | ".join(f"{s} {c}/{N}" for s, c in freq.most_common()))
    lines.append("")

lines += [
    "",
    "### Directional preference (7/3 or 6/4)",
    "",
    f"{len(split_67)} LPs:",
    "",
]
for lp_id in split_67:
    freq = lp_state_freq[lp_id]
    lines.append(f"**{lp_id}**: " + " | ".join(f"{s} {c}/{N}" for s, c in freq.most_common()))
    lines.append("")

lines += [
    "",
    "### Genuine split (≤5/10 modal state)",
    "",
    f"{len(genuine_55)} LPs:",
    "",
]
for lp_id in genuine_55:
    freq = lp_state_freq[lp_id]
    lines.append(f"**{lp_id}**: " + " | ".join(f"{s} {c}/{N}" for s, c in freq.most_common()))
    lines.append("")

lines += [
    "",
    "### Element churn with stable final state",
    "",
    f"{len(element_churn_stable_state)} LPs where element-level verdicts flipped but coverage_state held 10/10:",
    f"{', '.join(element_churn_stable_state) if element_churn_stable_state else 'none'}",
    "",
    "---",
    "",
    "## Per-Role Raw Verdict Flip Table",
    "",
    "A 'flip' = a role's verdict on an element differed from that role's own modal verdict for that element across N runs.",
    "",
    "| Role | Provider/Model | Config | Total element flips | LPs with any flip |",
    "|------|----------------|--------|--------------------|--------------------|",
    f"| A | anthropic / claude-sonnet-4-6 | temperature=0 | {role_flip_counts['A']} | {len(role_flip_lps['A'])} |",
    f"| B | openai / gpt-5.5 | temperature=1 (provider default; model rejects temp=0) | {role_flip_counts['B']} | {len(role_flip_lps['B'])} |",
    f"| C | xai / grok-4.3 | temperature=0 | {role_flip_counts['C']} | {len(role_flip_lps['C'])} |",
    "",
]

if total_role_flips > 0:
    lines.append("**Share of total flips by role:**")
    lines.append("")
    for role in ("A", "B", "C"):
        pct = role_flip_counts[role] / total_role_flips * 100
        lines.append(f"- Role {role}: {role_flip_counts[role]} flips ({pct:.0f}%)")
    lines.append("")
else:
    lines.append("No element-level role flips observed across all runs.")
    lines.append("")

lines += [
    "**LPs each role flipped on:**",
    "",
    f"- Role A: {sorted(role_flip_lps['A'])}",
    f"- Role B: {sorted(role_flip_lps['B'])}",
    f"- Role C: {sorted(role_flip_lps['C'])}",
    "",
    "---",
    "",
    "## Fallback / Config-Integrity Audit",
    "",
]
if fallback_events:
    lines.append(f"**⚠ FALLBACK EVENTS DETECTED — 414 REGRESSION ({len(fallback_events)} events):**")
    lines.append("")
    for fe in fallback_events:
        lines.append(f"- Run {fe['run_n']} LP {fe['lp_id']} Role {fe['role']}: actual_model={fe['actual_model']} reason={fe['fallback_reason']}")
    lines.append("")
else:
    lines.append(f"Fallback events: **none** across {N} runs × {len(all_lp_ids)} LPs. 414 integrity confirmed.")
    lines.append("")

lines += [
    "Config-integrity assertion: `_check_generation_integrity()` fires on every evaluator call.",
    "Any FatalProviderError would have aborted the run — no aborts observed.",
    "Role B primary (gpt-5.5) temperature: TEMPERATURE_ONLY_DEFAULT_MODELS exception fires every call (expected).",
    "",
    "---",
    "",
    "## Decision Standard Answers",
    "",
    f"**1. Post-414/416 irreducible wobble rate:** {wobble_rate:.1%} ({len(unstable_lps)}/{len(all_lp_ids)} LPs showed any coverage_state variance across N={N})",
    "",
]

if wobble_rate > 0:
    boundary_dominated = len(boundary_9) > len(genuine_55)
    lines.append(f"**2. Comparison to pre-416 ~31% (Step 411 N=2):** {'+' if wobble_rate > 0.31 else '-'}{abs(wobble_rate - 0.31):.1%} change.")
    lines.append("")
    lines.append(f"**3. Boundary vs genuine split:** {len(boundary_9)} LPs are 8/2 or 9/1 type (boundary noise); {len(genuine_55)} are 5/5 or worse (genuine disagreement).")
    lines.append("")

if total_role_flips > 0:
    b_share = role_flip_counts["B"] / total_role_flips * 100
    lines.append(f"**4. Role B primary disproportionate?** Role B accounted for {role_flip_counts['B']}/{total_role_flips} total element flips ({b_share:.0f}%).")
    lines.append(f"   Role A (temperature=0): {role_flip_counts['A']} flips. Role C (temperature=0): {role_flip_counts['C']} flips.")
    if b_share > 50:
        lines.append("   → Role B is the disproportionate source. Shadow diagnostic (gpt-5.4 shadow run) is likely informative.")
    else:
        lines.append("   → Role B is NOT disproportionate. Roles A/C also produce meaningful temperature=0 variance. Shadow diagnostic is less decisive.")
    lines.append("")
    lines.append(f"**5. Temperature=0 same-model variance (Role A + C):** {role_flip_counts['A'] + role_flip_counts['C']} flips from Roles A and C combined.")
    lines.append("")

# Framing recommendation
if len(genuine_55) > len(boundary_9):
    framing = "n-of-m sampling (genuine evaluator disagreement dominates)"
elif len(boundary_9) >= len(genuine_55) and wobble_rate > 0:
    framing = "boundary/hysteresis (most churn is 9/1 or 8/2 type boundary noise)"
elif wobble_rate == 0:
    framing = "no stabilization needed — panel is deterministic post-414/416"
else:
    framing = "mixed (boundary noise + genuine disagreement; inspect the split_67 and genuine_55 groups)"
lines.append(f"**6. Stabilization framing:** {framing}")
lines.append("")
lines.append("---")
lines.append("")
lines.append(f"*Step 417 baseline. N={N}. Frozen panel post-414/416. No push.*")

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n[417] Report written to {REPORT_PATH}", flush=True)
print(f"[417] Raw results in {OUT_DIR}/", flush=True)
print(f"[417] DONE. Total wall-clock: {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)", flush=True)
