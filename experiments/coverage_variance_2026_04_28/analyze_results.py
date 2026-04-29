"""Analyze the saved replay JSONs and produce the diff report + outcome.

Reads experiments/coverage_variance_2026_04_28/all_replays.json and writes
report.txt + summary.json + diff_per_call/*.txt with full statement text
(UTF-8) so we never hit Windows cp1255 console limits again.
"""

import json
import os
import sys
from pathlib import Path

# Force stdout to UTF-8 so Windows consoles don't choke on non-breaking hyphens.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OUT_DIR = Path(r"C:/Users/Owner/OneDrive/CAM/experiments/coverage_variance_2026_04_28")
with open(OUT_DIR / "all_replays.json", encoding="utf-8") as f:
    all_replays = json.load(f)

per_call_dir = OUT_DIR / "diff_per_call"
per_call_dir.mkdir(exist_ok=True)


def normalize_text(s: str) -> str:
    return " ".join((s or "").lower().split())


report_lines = []
classification_variance_calls = []
evidence_variance_calls = []
wording_variance_calls = []
no_variance_calls = []

for pid, data in all_replays.items():
    repeats = data["repeats"]
    inp = data["input"]

    sources = [r.get("exposure_source") for r in repeats]
    reasons = [r.get("exposure_reason_code") for r in repeats]
    confs = [r.get("exposure_confidence_note") for r in repeats]
    elements = [tuple(r.get("exposure_elements_used") or []) for r in repeats]
    statements = [r.get("exposure_statement", "") for r in repeats]
    statements_norm = [normalize_text(s) for s in statements]

    classification_diff = len(set(sources)) > 1 or len(set(reasons)) > 1
    evidence_diff = len(set(elements)) > 1
    wording_diff = len(set(statements_norm)) > 1

    if classification_diff:
        classification_variance_calls.append(pid)
    elif evidence_diff:
        evidence_variance_calls.append(pid)
    elif wording_diff:
        wording_variance_calls.append(pid)
    else:
        no_variance_calls.append(pid)

    block = []
    block.append(f"=== {pid} ===")
    block.append(f"  input.coverage_state    : {inp.get('coverage_state')}")
    block.append(f"  input.materiality       : {inp.get('materiality')}")
    block.append(f"  input.elements_missing  : {inp.get('elements_missing')}")
    block.append(f"  input.elements_found    : {inp.get('elements_found')}")
    block.append(f"  exposure_source(s)      : {sources}")
    block.append(f"  exposure_reason_code(s) : {reasons}")
    block.append(f"  elements_used per repeat:")
    for i, e in enumerate(elements):
        block.append(f"    repeat[{i}] = {list(e)}")
    block.append(f"  classification_diff     : {classification_diff}")
    block.append(f"  evidence_diff           : {evidence_diff}")
    block.append(f"  wording_diff            : {wording_diff}")
    block.append("")
    for i, stmt in enumerate(statements):
        block.append(f"  repeat[{i}]:")
        block.append(f"    {stmt}")
    block.append("")

    block_text = "\n".join(block)
    report_lines.append(block_text)

    with open(per_call_dir / f"{pid}.txt", "w", encoding="utf-8") as f:
        f.write(block_text)

# Outcome
if classification_variance_calls:
    outcome = "D"
    justification = (
        f"At least one call ({', '.join(classification_variance_calls)}) produced "
        "different exposure_source / exposure_reason_code across repeats."
    )
elif evidence_variance_calls:
    outcome = "C"
    justification = (
        f"No classification variance, but {len(evidence_variance_calls)} call(s) "
        f"({', '.join(evidence_variance_calls)}) cited different elements_used "
        "across repeats."
    )
elif wording_variance_calls:
    outcome = "B"
    justification = (
        f"No classification or evidence variance; {len(wording_variance_calls)} call(s) "
        "differed only in exposure_statement phrasing."
    )
else:
    outcome = "A"
    justification = "All 3 repeats produced identical classifications, evidence, and statements across all calls."

summary = {
    "outcome": outcome,
    "justification": justification,
    "model_path_calls": list(all_replays.keys()),
    "n_calls": len(all_replays),
    "n_repeats_per_call": 3,
    "n_total_replays": len(all_replays) * 3,
    "classification_variance_calls": classification_variance_calls,
    "evidence_variance_calls": evidence_variance_calls,
    "wording_variance_calls": wording_variance_calls,
    "no_variance_calls": no_variance_calls,
}

with open(OUT_DIR / "summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

with open(OUT_DIR / "report.txt", "w", encoding="utf-8") as f:
    f.write("Coverage Exposure Variance Experiment - Mechanical Diff Report\n")
    f.write("Date: 2026-04-28\n")
    f.write("Lease: T-10_Negotiated_Tennant_Lease.docx (fresh Mode C run)\n")
    f.write("Model: openai:gpt-5.2 (production exposure-layer config)\n")
    f.write(f"Calls: {len(all_replays)} model-path x 3 repeats = {len(all_replays) * 3}\n\n")
    f.write("\n".join(report_lines))
    f.write("\n\nOUTCOME: " + outcome + "\n")
    f.write(justification + "\n")

print("=" * 70)
print("OUTCOME:", outcome)
print("=" * 70)
print("Justification:", justification)
print()
print("Per-call breakdown:")
print(f"  Classification variance: {classification_variance_calls or 'none'}")
print(f"  Evidence variance      : {evidence_variance_calls or 'none'}")
print(f"  Wording variance only  : {wording_variance_calls or 'none'}")
print(f"  No variance            : {no_variance_calls or 'none'}")
print()
print(f"Full statements per call: {per_call_dir}")
print(f"Summary JSON           : {OUT_DIR / 'summary.json'}")
print(f"Report TXT             : {OUT_DIR / 'report.txt'}")
