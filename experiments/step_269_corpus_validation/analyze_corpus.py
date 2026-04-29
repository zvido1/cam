"""Step 269 — Corpus validation analysis.

Reads:
  - experiments/step_269_corpus_validation/T-XX/pipeline_results.json
    (post-bump runs from run_corpus_validation.py)
  - experiments/step_269_corpus_validation/run_log.json
  - All cached pre-bump pipeline_results.json files in
    05 Lease Analyzer/results/ (these were produced before Step 268)

Writes:
  - experiments/step_269_corpus_validation/corpus_validation_matrix.json
  - experiments/step_269_corpus_validation/pre_bump_classifications.json
    (per-tenant cached classifications discovered during the search)
  - experiments/step_269_corpus_validation/headline.txt
"""

import glob
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(r"C:/Users/Owner/OneDrive/CAM")
OUT_DIR = PROJECT / "experiments" / "step_269_corpus_validation"
RESULTS_GLOB = str(PROJECT / "05 Lease Analyzer" / "results" / "**" / "pipeline_results.json")

# Load post-bump results that just ran
post_runs: dict[str, dict] = {}
for n in range(1, 17):
    name = f"T-{n:02d}"
    p = OUT_DIR / name / "pipeline_results.json"
    if p.exists():
        try:
            with open(p, encoding="utf-8") as f:
                post_runs[name] = json.load(f)
        except Exception as e:
            print(f"[warn] could not read {p}: {e}")

print(f"[analyze] post-bump runs loaded: {sorted(post_runs)}")

# Find pre-bump runs in cached production results.
# Strategy: for each pipeline_results.json under 05 Lease Analyzer/results/,
# check (a) tenant_file, (b) timestamp, (c) skip Step 269's own runs and
# obvious post-bump runs (run_id starts with 'step_268_' or 'step_269_').
# Only keep results whose timestamp is BEFORE 2026-04-28T12:00:00 UTC
# (Step 268 schema bump was applied around that time today).
import datetime as _dt
PRE_BUMP_CUTOFF = _dt.datetime(2026, 4, 28, 12, 0, 0, tzinfo=_dt.timezone.utc)


def to_dt(s: str) -> _dt.datetime | None:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return _dt.datetime.fromisoformat(s)
    except Exception:
        return None


# Collect all candidate cached runs, group by tenant_file, prefer most recent
# pre-bump per tenant_file.
pre_bump_per_file: dict[str, tuple[Path, dict]] = {}
candidates_inspected = 0
for path in glob.glob(RESULTS_GLOB, recursive=True):
    p = Path(path)
    parts = p.parts
    # Skip Step 268/269 fresh runs and our own output
    if any(seg.startswith(("step_268_", "step_269_", "lease_step_268", "lease_variance_2026_04_28_fresh")) for seg in parts):
        continue
    # Skip the experiments/ tree (we're only looking at production results dir)
    if "experiments" in parts:
        continue
    candidates_inspected += 1
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        continue
    tf = d.get("tenant_file") or ""
    if not tf:
        continue
    ts_str = d.get("timestamp", "")
    ts = to_dt(ts_str)
    if ts is None or ts >= PRE_BUMP_CUTOFF:
        continue
    # Keep most recent pre-bump per tenant_file
    prev = pre_bump_per_file.get(tf)
    if prev is None or to_dt(prev[1].get("timestamp", "")) < ts:
        pre_bump_per_file[tf] = (p, d)

print(f"[analyze] inspected {candidates_inspected} cached pipeline_results.json files; "
      f"found pre-bump runs for {len(pre_bump_per_file)} tenant_file values:")
for tf in sorted(pre_bump_per_file):
    p, d = pre_bump_per_file[tf]
    print(f"    {tf:<40} <- {Path(*p.parts[-3:])} ({d.get('timestamp','')})")


def coverage_states(d: dict) -> dict[str, str]:
    return {a["issue_area_id"]: a.get("coverage_state") for a in d.get("coverage_assessment", [])}


# Save discovered pre-bump classifications for later reference
pre_bump_summary = {}
for tf, (p, d) in pre_bump_per_file.items():
    pre_bump_summary[tf] = {
        "source_path": str(p.relative_to(PROJECT)),
        "timestamp": d.get("timestamp", ""),
        "coverage_states": coverage_states(d),
    }
with open(OUT_DIR / "pre_bump_classifications.json", "w", encoding="utf-8") as f:
    json.dump(pre_bump_summary, f, indent=2)


# Build the matrix
matrix: list[dict] = []
all_lp_ids = sorted({lp for d in post_runs.values() for lp in coverage_states(d)})
print(f"[analyze] LP coverage in post-bump runs: {all_lp_ids}")

run_log_path = OUT_DIR / "run_log.json"
run_log = {}
if run_log_path.exists():
    with open(run_log_path, encoding="utf-8") as f:
        run_log = json.load(f)
tenants_in_log = {r["tenant"]: r for r in run_log.get("tenants", [])}
failures = {f["tenant"]: f for f in run_log.get("failures", [])}

for n in range(1, 17):
    name = f"T-{n:02d}"
    log_entry = tenants_in_log.get(name, {})
    failure_entry = failures.get(name, {})

    row: dict = {"tenant": name, "file": log_entry.get("file") or failure_entry.get("file") or ""}

    if name in post_runs:
        post = post_runs[name]
        post_states = coverage_states(post)
        row["extraction_status"] = "success"
        row["extraction_error"] = None
        row["lp11_post_bump"] = post_states.get("LP-11")
        row["lp13_post_bump"] = post_states.get("LP-13")
        row["all_post_states"] = post_states
    else:
        post_states = {}
        err = failure_entry.get("error", "missing")
        row["extraction_status"] = "failed"
        row["extraction_error"] = err
        row["lp11_post_bump"] = None
        row["lp13_post_bump"] = None
        row["all_post_states"] = {}

    tenant_file = row["file"]
    pre = pre_bump_per_file.get(tenant_file)
    if pre:
        pre_states = coverage_states(pre[1])
        row["pre_bump_source"] = str(pre[0].relative_to(PROJECT))
        row["pre_bump_timestamp"] = pre[1].get("timestamp", "")
        row["lp11_pre_bump"] = pre_states.get("LP-11")
        row["lp13_pre_bump"] = pre_states.get("LP-13")
        row["all_pre_states"] = pre_states

        if row["extraction_status"] == "success":
            for lp_key, pre_v, post_v in (("lp11", row["lp11_pre_bump"], row["lp11_post_bump"]),
                                          ("lp13", row["lp13_pre_bump"], row["lp13_post_bump"])):
                if pre_v is None or post_v is None:
                    row[f"{lp_key}_flipped"] = None
                    row[f"{lp_key}_flip_direction"] = None
                else:
                    flipped = pre_v != post_v
                    row[f"{lp_key}_flipped"] = flipped
                    row[f"{lp_key}_flip_direction"] = f"{pre_v} -> {post_v}" if flipped else None

            # Cross-LP regression check: compare every LP that appears in BOTH pre and post,
            # excluding LP-11 / LP-13.
            other_lp_changes = []
            for lp_id in sorted(set(pre_states) & set(post_states)):
                if lp_id in ("LP-11", "LP-13"):
                    continue
                if pre_states[lp_id] != post_states[lp_id]:
                    other_lp_changes.append({
                        "lp": lp_id,
                        "pre_bump": pre_states[lp_id],
                        "post_bump": post_states[lp_id],
                    })
            row["other_lp_changes"] = other_lp_changes
        else:
            row["lp11_flipped"] = None
            row["lp11_flip_direction"] = None
            row["lp13_flipped"] = None
            row["lp13_flip_direction"] = None
            row["other_lp_changes"] = []
    else:
        row["pre_bump_source"] = None
        row["pre_bump_timestamp"] = None
        row["lp11_pre_bump"] = None
        row["lp13_pre_bump"] = None
        row["all_pre_states"] = {}
        row["lp11_flipped"] = None
        row["lp11_flip_direction"] = None
        row["lp13_flipped"] = None
        row["lp13_flip_direction"] = None
        row["other_lp_changes"] = []

    matrix.append(row)

with open(OUT_DIR / "corpus_validation_matrix.json", "w", encoding="utf-8") as f:
    json.dump(matrix, f, indent=2)


# Headline counts
def count_states(rows, key):
    c = Counter()
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        c[v] += 1
    return c


lp13_counter = count_states(matrix, "lp13_post_bump")
lp11_counter = count_states(matrix, "lp11_post_bump")

# Flip counters (only counts where pre-bump is known)
def flip_counter(rows, lp_key):
    c = Counter()
    no_compare = 0
    for r in rows:
        flip = r.get(f"{lp_key}_flipped")
        if flip is None:
            no_compare += 1
            continue
        if not flip:
            c["no_change"] += 1
        else:
            c[r[f"{lp_key}_flip_direction"]] += 1
    return c, no_compare


lp13_flips, lp13_no_compare = flip_counter(matrix, "lp13")
lp11_flips, lp11_no_compare = flip_counter(matrix, "lp11")

# Cross-LP regressions
cross_lp_changes = []
for r in matrix:
    for change in r.get("other_lp_changes") or []:
        cross_lp_changes.append((r["tenant"], change["lp"], change["pre_bump"], change["post_bump"]))

# Confirmed flips for the shortcut comparison
lp13_flipped_to_unfav = sum(
    1 for r in matrix
    if r.get("lp13_post_bump") == "covered_unfavorable"
    and r.get("extraction_status") == "success"
)
lp11_flipped_to_unfav = sum(
    1 for r in matrix
    if r.get("lp11_post_bump") == "covered_unfavorable"
    and r.get("extraction_status") == "success"
)
n_success = sum(1 for r in matrix if r["extraction_status"] == "success")
failed_tenants = [r["tenant"] for r in matrix if r["extraction_status"] != "success"]

# Build headline
lines = []
lines.append("Step 269 — Full Pipeline Corpus Validation Headline")
lines.append("")
lines.append(f"Tenants attempted: 16")
lines.append(f"Tenants extracted successfully: {n_success}")
lines.append(f"Tenants failed: {failed_tenants}")
lines.append("")
lines.append("LP-13 classifications (post-bump):")
for state in ("covered_unfavorable", "partial", "covered", "missing", "ambiguous", "broken_xref",
              "potentially_unenforceable", "review_needed", "not_applicable", "applicability_unclear"):
    if state in lp13_counter:
        lines.append(f"  - {state}: {lp13_counter[state]}")
other13 = sum(c for s, c in lp13_counter.items() if s not in (
    "covered_unfavorable", "partial", "covered", "missing", "ambiguous", "broken_xref",
    "potentially_unenforceable", "review_needed", "not_applicable", "applicability_unclear"))
if other13:
    lines.append(f"  - other: {other13}")
lines.append("")
lines.append("LP-11 classifications (post-bump):")
for state in ("covered_unfavorable", "partial", "covered", "missing", "ambiguous", "broken_xref",
              "potentially_unenforceable", "review_needed", "not_applicable", "applicability_unclear"):
    if state in lp11_counter:
        lines.append(f"  - {state}: {lp11_counter[state]}")
other11 = sum(c for s, c in lp11_counter.items() if s not in (
    "covered_unfavorable", "partial", "covered", "missing", "ambiguous", "broken_xref",
    "potentially_unenforceable", "review_needed", "not_applicable", "applicability_unclear"))
if other11:
    lines.append(f"  - other: {other11}")
lines.append("")

lines.append("LP-13 flips from cached pre-bump (where data available):")
for direction, count in sorted(lp13_flips.items()):
    marker = "  ← THIS IS THE FALSE POSITIVE NUMBER" if direction == "covered -> covered_unfavorable" else ""
    lines.append(f"  - {direction}: {count}{marker}")
lines.append(f"  - no comparison available: {lp13_no_compare}")
lines.append("")
lines.append("LP-11 flips from cached pre-bump (where data available):")
for direction, count in sorted(lp11_flips.items()):
    marker = "  ← THIS IS THE FALSE POSITIVE NUMBER" if direction == "covered -> covered_unfavorable" else ""
    lines.append(f"  - {direction}: {count}{marker}")
lines.append(f"  - no comparison available: {lp11_no_compare}")
lines.append("")

lines.append("Cross-LP regression check (pre-bump vs post-bump on cached tenants):")
if not cross_lp_changes:
    lines.append("  - Other LPs with classification changes: NONE")
else:
    lines.append(f"  - Other LPs with classification changes: {len(cross_lp_changes)}")
    for t, lp, pre, post in cross_lp_changes:
        lines.append(f"      {t}  {lp}: {pre} -> {post}")
n_unchanged_other_lp = sum(
    len(set(r["all_pre_states"]) & set(r["all_post_states"]) - {"LP-11", "LP-13"})
    - len(r.get("other_lp_changes") or [])
    for r in matrix if r.get("pre_bump_source")
)
lines.append(f"  - Other LPs unchanged: {n_unchanged_other_lp}")
lines.append("")

lines.append("Step 268 shortcut prediction vs full pipeline reality:")
lines.append(f"  - LP-13 shortcut said: 15/16 would flip")
lines.append(f"  - LP-13 actual full pipeline classified covered_unfavorable: {lp13_flipped_to_unfav}/{n_success}")
lines.append(f"  - LP-11 shortcut said: 13/16 would flip")
lines.append(f"  - LP-11 actual full pipeline classified covered_unfavorable: {lp11_flipped_to_unfav}/{n_success}")

# Anomalies: states that aren't partial / covered_unfavorable for LP-11 or LP-13
anomalies_lp13 = [r for r in matrix
                  if r.get("extraction_status") == "success"
                  and r.get("lp13_post_bump") not in ("covered_unfavorable", "partial", None)]
anomalies_lp11 = [r for r in matrix
                  if r.get("extraction_status") == "success"
                  and r.get("lp11_post_bump") not in ("covered_unfavorable", "partial", None)]
if anomalies_lp13 or anomalies_lp11:
    lines.append("")
    lines.append("Anomalies (LP-11/LP-13 unexpected classifications):")
    for r in anomalies_lp13:
        lines.append(f"  - {r['tenant']} LP-13 = {r['lp13_post_bump']}")
    for r in anomalies_lp11:
        lines.append(f"  - {r['tenant']} LP-11 = {r['lp11_post_bump']}")

with open(OUT_DIR / "headline.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print()
print("\n".join(lines))
