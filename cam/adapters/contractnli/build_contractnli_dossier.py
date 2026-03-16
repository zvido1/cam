#!/usr/bin/env python3
"""
Build ContractNLI Forensic Dossier — HTML reports for ContractNLI evaluation results.

Generates:
  - index.html: Overview of all contracts with metrics and click-through
  - contract_NNN.html: Per-contract dossier showing all 17 hypotheses

Adapted from cam/adapters/gpqa/build_gpqa_dossier.py for legal contract domain.
Key differences from GPQA dossier:
  - Contract-level organization (not question-level)
  - Span highlighting from contract text
  - 3-label verdict space (ENTAILMENT/CONTRADICTION/NOT_MENTIONED)
  - Error spotlight boxes for false assertions
"""

import json
import html as html_lib
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Optional, Dict, List, Tuple
import argparse


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


# =============================================================================
# Data Loading
# =============================================================================
def load_results(run_dir: Path) -> List[dict]:
    """Load per-hypothesis results from results.jsonl."""
    results_path = run_dir / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"Missing results file: {results_path}")
    records = []
    with open(results_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_contract_summaries(run_dir: Path) -> Dict[int, dict]:
    """Load contract-level summaries keyed by contract_id."""
    path = run_dir / "contract_summaries.jsonl"
    summaries = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    summaries[obj["contract_id"]] = obj
    return summaries


def load_metrics(run_dir: Path) -> dict:
    """Load aggregate metrics."""
    path = run_dir / "metrics_summary.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_contracts(data_dir: Path) -> Dict[int, dict]:
    """Load contract texts and spans from dev.json."""
    path = data_dir / "dev.json"
    contracts = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for doc in data.get("documents", []):
            contracts[doc["id"]] = {
                "text": doc.get("text", ""),
                "spans": doc.get("spans", []),
                "file_name": doc.get("file_name", ""),
            }
    return contracts


def load_error_analyses(build_log_dir: Path) -> Dict[str, str]:
    """Load error analysis files for nda-15, nda-16, nda-20."""
    analyses = {}
    for hyp_num in ["15", "16", "20"]:
        path = build_log_dir / f"022_nda{hyp_num}_analysis.txt"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                analyses[f"nda-{hyp_num}"] = f.read()
    return analyses


# =============================================================================
# Span Text Extraction
# =============================================================================
def get_span_text(contract: dict, span_idx: int) -> str:
    """Extract text for a given span index from contract."""
    spans = contract.get("spans", [])
    text = contract.get("text", "")
    if span_idx < 0 or span_idx >= len(spans):
        return f"[span {span_idx} out of range]"
    start, end = spans[span_idx]
    return text[start:end].strip()


def get_cited_spans_html(contract: dict, cited_spans: Dict[str, List[int]]) -> str:
    """Build HTML showing cited spans with multi-evaluator overlap highlighting."""
    if not contract or not cited_spans:
        return ""

    # Count how many evaluators cited each span
    span_counts = Counter()
    for eval_id, indices in cited_spans.items():
        for idx in indices:
            span_counts[idx] += 1

    # Get unique spans sorted by index
    all_span_indices = sorted(set(
        idx for indices in cited_spans.values() for idx in indices
    ))

    if not all_span_indices:
        return ""

    html = '<div style="margin-top: 10px;">'
    html += '<div style="font-weight: bold; margin-bottom: 6px;">Cited Contract Spans:</div>'

    for idx in all_span_indices:
        count = span_counts[idx]
        span_text = get_span_text(contract, idx)
        # Color by citation count
        if count >= 3:
            bg = "#d4edda"
            border = "#28a745"
            badge = f'<span style="background: #28a745; color: white; padding: 1px 6px; border-radius: 3px; font-size: 0.75em; margin-left: 6px;">All {count} evaluators</span>'
        elif count == 2:
            bg = "#fff3cd"
            border = "#ffc107"
            badge = '<span style="background: #ffc107; color: black; padding: 1px 6px; border-radius: 3px; font-size: 0.75em; margin-left: 6px;">2 evaluators</span>'
        else:
            bg = "#f8f9fa"
            border = "#dee2e6"
            cited_by = [eid for eid, indices in cited_spans.items() if idx in indices]
            badge = f'<span style="background: #6c757d; color: white; padding: 1px 6px; border-radius: 3px; font-size: 0.75em; margin-left: 6px;">Eval {", ".join(cited_by)}</span>'

        html += f'<div style="margin: 4px 0; padding: 8px; background: {bg}; border-left: 3px solid {border}; border-radius: 3px; font-family: monospace; font-size: 0.85em; white-space: pre-wrap; word-wrap: break-word;">'
        html += f'<span style="color: #6c757d; font-size: 0.8em;">[Span {idx}]</span>{badge}<br>'
        html += escape_html(span_text[:500])
        if len(span_text) > 500:
            html += "..."
        html += '</div>'

    html += '</div>'
    return html


# =============================================================================
# Color and Status Helpers
# =============================================================================
VERDICT_COLORS = {
    "ENTAILMENT": "#28a745",
    "CONTRADICTION": "#dc3545",
    "NOT_MENTIONED": "#6c757d",
}

COMMITMENT_COLORS = {
    "L1_QUALIFIED": "#28a745",
    "L2_CONDITIONAL": "#17a2b8",
    "L3_LOW_CONFIDENCE": "#ffc107",
    "L4_WITHHOLD": "#6c757d",
}

TERMINAL_STATE_STYLES = {
    "ASSERT_ENTAILMENT": ("Asserted: ENTAILMENT", "#28a745", "#d4edda"),
    "ASSERT_CONTRADICTION": ("Asserted: CONTRADICTION", "#dc3545", "#f8d7da"),
    "ASSERT_NOT_MENTIONED": ("Asserted: NOT MENTIONED", "#17a2b8", "#d1ecf1"),
    "WITHHOLD_ASSERTION": ("WITHHELD", "#6c757d", "#e2e3e5"),
}


def terminal_state_badge(state: str) -> str:
    label, color, bg = TERMINAL_STATE_STYLES.get(
        state, (state, "#6c757d", "#e2e3e5")
    )
    return f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em;">{escape_html(label)}</span>'


def commitment_badge(level: str) -> str:
    color = COMMITMENT_COLORS.get(level, "#6c757d")
    label = level.replace("_", " ")
    return f'<span style="background: {color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{escape_html(label)}</span>'


def gold_match_icon(match: bool, withheld: bool) -> str:
    if withheld:
        return '<span style="color: #ffc107;" title="Withheld">--</span>'
    if match:
        return '<span style="color: #28a745; font-weight: bold;" title="Correct">&#10003;</span>'
    return '<span style="color: #dc3545; font-weight: bold;" title="Wrong">&#10007;</span>'


# =============================================================================
# CSS Styles (shared across all pages)
# =============================================================================
SHARED_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       max-width: 1400px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
.header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.stats { display: flex; gap: 15px; margin-top: 15px; flex-wrap: wrap; }
.stat-box { background: #f8f9fa; padding: 12px; border-radius: 6px;
             border-left: 4px solid #007bff; flex: 1; min-width: 120px; }
.hypothesis-card { background: white; padding: 15px; border-radius: 8px;
                    margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
details { margin: 8px 0; }
summary { cursor: pointer; padding: 8px; background: #f8f9fa; border-radius: 4px;
           font-weight: bold; }
summary:hover { background: #e9ecef; }
.verdict-box { display: inline-block; padding: 6px 10px; margin: 4px;
                border-radius: 4px; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }
th { background: #f8f9fa; font-weight: bold; }
.error-spotlight { background: #f8d7da; border: 2px solid #dc3545; border-radius: 8px;
                    padding: 15px; margin-bottom: 15px; }
.error-spotlight h4 { color: #721c24; margin-top: 0; }
a { color: #007bff; text-decoration: none; }
a:hover { text-decoration: underline; }
"""


# =============================================================================
# Render: Hypothesis Section (for contract dossier)
# =============================================================================
def render_hypothesis_section(
    record: dict,
    contract: Optional[dict],
    error_analyses: Dict[str, str],
) -> str:
    """Render a single hypothesis evaluation as a collapsible section."""
    hyp_id = record["hypothesis_id"]
    hyp_text = record["hypothesis_text"]
    terminal = record["terminal_state"]
    gold = record["gold_label"]
    gold_match = record.get("gold_match", False)
    withheld = record.get("withheld", False)
    commitment = record.get("commitment_level", "")
    conviction = record.get("conviction_score", 0)

    # Determine outcome color for the summary bar
    if withheld:
        summary_color = "#ffc107"
        outcome_icon = "&#9679;"  # yellow dot
    elif gold_match:
        summary_color = "#28a745"
        outcome_icon = "&#10003;"
    else:
        summary_color = "#dc3545"
        outcome_icon = "&#10007;"

    # Error spotlight for false assertions
    error_html = ""
    is_false_assert = not withheld and not gold_match
    if is_false_assert:
        error_html = '<div class="error-spotlight">'
        error_html += '<h4>&#9888; ERROR ANALYSIS</h4>'
        error_html += f'<p><strong>What went wrong:</strong> System asserted <code>{escape_html(terminal.replace("ASSERT_", ""))}</code> but gold is <code>{escape_html(gold)}</code>.</p>'
        error_html += f'<p><strong>Commitment level:</strong> {commitment_badge(commitment)} — conviction score {conviction:.2f}</p>'

        # Check evaluator verdicts to see who got it wrong
        verdicts = record.get("evaluator_verdicts", {})
        wrong_evals = []
        right_evals = []
        for eid, v in verdicts.items():
            if v.get("verdict") == gold:
                right_evals.append(eid)
            else:
                wrong_evals.append(eid)
        if wrong_evals:
            error_html += f'<p><strong>Wrong evaluators:</strong> {", ".join(wrong_evals)}'
            if right_evals:
                error_html += f' | <strong>Correct evaluator(s):</strong> {", ".join(right_evals)}'
            error_html += '</p>'

        # Inject analysis from 022 files if available
        analysis = error_analyses.get(hyp_id)
        if analysis:
            # Pull root cause line
            for line in analysis.split("\n"):
                if line.startswith("ROOT CAUSE:") or line.startswith("CLASSIFICATION:"):
                    error_html += f'<p style="margin-top: 8px;"><strong>{escape_html(line)}</strong></p>'

        error_html += '</div>'

    # Build the collapsible section
    html = f'<details {"open" if is_false_assert else ""}>'
    html += f'<summary style="border-left: 4px solid {summary_color}; padding-left: 12px;">'
    html += f'<span style="font-size: 1.1em;">{outcome_icon} {escape_html(hyp_id)}</span>'
    html += f' — <span style="color: #666;">{escape_html(hyp_text[:100])}{"..." if len(hyp_text) > 100 else ""}</span>'
    html += f' {terminal_state_badge(terminal)}'
    html += f' <span style="margin-left: 8px;">Gold: <code style="color: {VERDICT_COLORS.get(gold, "#000")};">{escape_html(gold)}</code></span>'
    html += f' {gold_match_icon(gold_match, withheld)}'
    html += '</summary>'

    html += '<div style="padding: 12px; border-left: 4px solid #dee2e6; margin-left: 8px;">'

    # Error spotlight (if false assertion)
    html += error_html

    # Hypothesis text
    html += f'<div style="margin-bottom: 12px; padding: 10px; background: #f0f4f8; border-radius: 4px;"><strong>Hypothesis:</strong> {escape_html(hyp_text)}</div>'

    # === Evaluator Verdicts ===
    verdicts = record.get("evaluator_verdicts", {})
    cited_spans = record.get("cited_spans_per_evaluator", {})
    agreement = record.get("agreement_pattern", "")
    majority = record.get("majority_verdict", "")

    html += '<div style="margin-bottom: 12px;">'
    html += f'<strong>Evaluator Verdicts</strong> — <span style="color: #666;">{escape_html(agreement)}</span>'
    html += f' | Majority: <code style="color: {VERDICT_COLORS.get(majority, "#000")};">{escape_html(majority)}</code>'
    html += '<div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;">'

    for eval_id in sorted(verdicts.keys()):
        v = verdicts[eval_id]
        verdict = v.get("verdict", "?")
        confidence = v.get("confidence", "?")
        vcolor = VERDICT_COLORS.get(verdict, "#6c757d")
        is_correct = (verdict == gold)
        border = f"2px solid {vcolor}"
        bg = "#d4edda" if is_correct else "#f8f9fa"
        spans_str = ", ".join(str(s) for s in cited_spans.get(eval_id, []))

        html += f'<div style="padding: 8px; border: {border}; border-radius: 6px; background: {bg}; min-width: 180px; flex: 1;">'
        html += f'<div style="font-weight: bold;">Evaluator {escape_html(eval_id)} {"&#10003;" if is_correct else "&#10007;" if not is_correct else ""}</div>'
        html += f'<div style="color: {vcolor}; font-weight: bold; font-size: 1.1em;">{escape_html(verdict)}</div>'
        html += f'<div style="font-size: 0.85em; color: #666;">Confidence: {escape_html(confidence)}</div>'
        if spans_str:
            html += f'<div style="font-size: 0.8em; color: #999;">Spans: [{spans_str}]</div>'
        html += '</div>'

    html += '</div></div>'

    # === Cited Spans (actual text) ===
    if contract:
        html += get_cited_spans_html(contract, cited_spans)

    # === Evidence Challenge ===
    challenge = record.get("challenge_summary", {})
    if challenge:
        grounding = challenge.get("overall_grounding", "?")
        count = challenge.get("challenge_count", 0)
        types = challenge.get("challenge_types", [])
        grounding_color = "#28a745" if grounding == "adequate" else "#dc3545" if grounding == "weak" else "#ffc107"

        html += '<details style="margin-top: 10px;">'
        html += f'<summary>Evidence Challenge — <span style="color: {grounding_color};">{escape_html(grounding)}</span> ({count} challenges)</summary>'
        html += '<div style="padding: 8px;">'
        if types:
            type_counts = Counter(types)
            html += '<div style="margin-top: 6px;">'
            for ctype, cnt in type_counts.most_common():
                html += f'<span style="display: inline-block; background: #e9ecef; padding: 2px 8px; margin: 2px; border-radius: 3px; font-size: 0.85em;">{escape_html(ctype)} ({cnt})</span>'
            html += '</div>'
        html += '</div></details>'

    # === Auditor Assessment ===
    auditor = record.get("auditor_assessment", {})
    if auditor:
        validity = auditor.get("structural_validity", "?")
        grounding_q = auditor.get("grounding_quality", "?")
        recommendation = auditor.get("recommendation", "?")
        span_overlap = auditor.get("span_overlap", "?")

        rec_color = "#dc3545" if recommendation == "escalate" else "#ffc107" if recommendation == "flag" else "#28a745"

        html += '<details style="margin-top: 10px;">'
        html += f'<summary>Auditor — <span style="color: {rec_color};">{escape_html(recommendation)}</span></summary>'
        html += '<div style="padding: 8px;">'
        html += f'<table><tr><th>Structural Validity</th><th>Grounding Quality</th><th>Recommendation</th><th>Span Overlap</th></tr>'
        html += f'<tr><td>{escape_html(validity)}</td><td>{escape_html(grounding_q)}</td>'
        html += f'<td style="color: {rec_color}; font-weight: bold;">{escape_html(recommendation)}</td>'
        html += f'<td>{escape_html(span_overlap)}</td></tr></table>'
        html += '</div></details>'

    # === Fragility ===
    fragility = record.get("fragility_score", 0)
    rules = record.get("triggered_rules", [])
    cap = record.get("fragility_cap", "")

    if rules:
        html += '<details style="margin-top: 10px;">'
        html += f'<summary>Fragility — Score: {fragility:.2f} | Cap: {escape_html(cap)} | {len(rules)} rules fired</summary>'
        html += '<div style="padding: 8px;">'
        for rule in rules:
            html += f'<span style="display: inline-block; background: #fff3cd; padding: 2px 8px; margin: 2px; border-radius: 3px; font-size: 0.85em; border: 1px solid #ffc107;">{escape_html(rule)}</span>'
        html += '</div></details>'

    # === Verdict Elimination ===
    ve = record.get("verdict_elimination", {})
    if ve:
        surviving = ve.get("surviving_verdicts", [])
        eliminated = ve.get("eliminated_verdicts", [])
        recommended = ve.get("recommended_verdict", "?")

        html += '<details style="margin-top: 10px;">'
        html += f'<summary>Verdict Elimination &rarr; {escape_html(recommended)}</summary>'
        html += '<div style="padding: 8px; display: flex; gap: 10px;">'
        html += '<div style="flex: 1;"><strong style="color: #28a745;">Surviving:</strong> '
        for v in surviving:
            html += f'<span style="color: {VERDICT_COLORS.get(v, "#000")}; font-weight: bold;">{escape_html(v)}</span> '
        html += '</div>'
        html += '<div style="flex: 1;"><strong style="color: #dc3545;">Eliminated:</strong> '
        for v in eliminated:
            html += f'<span style="color: #999; text-decoration: line-through;">{escape_html(v)}</span> '
        html += '</div>'
        html += '</div></details>'

    # === Disposition ===
    html += '<div style="margin-top: 12px; padding: 10px; background: #f8f9fa; border-radius: 4px;">'
    html += f'<strong>Disposition:</strong> {terminal_state_badge(terminal)} '
    html += f'{commitment_badge(commitment)} '
    html += f'<span style="color: #666;">Conviction: {conviction:.3f}</span>'

    downgrade_reasons = record.get("downgrade_reasons", [])
    if downgrade_reasons:
        html += '<div style="margin-top: 6px; font-size: 0.85em; color: #666;">'
        for reason in downgrade_reasons:
            html += f'<div>&#8226; {escape_html(reason)}</div>'
        html += '</div>'

    html += '</div>'

    html += '</div>'  # end inner section
    html += '</details>'

    return html


# =============================================================================
# Build: Contract-Level Dossier
# =============================================================================
def build_contract_dossier(
    contract_id: int,
    records: List[dict],
    contract: Optional[dict],
    summary: Optional[dict],
    error_analyses: Dict[str, str],
    output_path: Path,
):
    """Build HTML dossier for a single contract."""
    # Compute per-contract stats
    total = len(records)
    asserted = [r for r in records if not r.get("withheld", False)]
    withheld = [r for r in records if r.get("withheld", False)]
    correct = [r for r in asserted if r.get("gold_match", False)]
    wrong = [r for r in asserted if not r.get("gold_match", False)]
    cca = (len(correct) / len(asserted) * 100) if asserted else 0

    contract_text = contract.get("text", "") if contract else ""
    contract_len = len(contract_text)
    file_name = contract.get("file_name", "") if contract else ""

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>ContractNLI Dossier — Contract {contract_id}</title>
<style>{SHARED_CSS}</style>
</head><body>
<div class="header">
<h1>Contract {contract_id} <span style="font-size: 0.6em; color: #6c757d;">ContractNLI Forensic Dossier</span></h1>
<p><a href="index.html">&larr; Back to Index</a></p>
<div style="font-size: 0.9em; color: #666;">
  Source: <code>{escape_html(file_name)}</code> | Length: {contract_len:,} chars | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>

<div class="stats">
<div class="stat-box">Total: {total}</div>
<div class="stat-box" style="border-left-color: #28a745;">Correct: {len(correct)}</div>
<div class="stat-box" style="border-left-color: #dc3545;">Wrong: {len(wrong)}</div>
<div class="stat-box" style="border-left-color: #ffc107;">Withheld: {len(withheld)}</div>
<div class="stat-box" style="border-left-color: {"#28a745" if cca >= 90 else "#ffc107" if cca >= 70 else "#dc3545"};">CCA: {cca:.1f}%</div>
</div>

<details style="margin-top: 15px;">
<summary>Contract Text (first 500 chars)</summary>
<div style="padding: 10px; background: #f8f9fa; border-radius: 4px; font-family: monospace; font-size: 0.85em; white-space: pre-wrap; word-wrap: break-word; max-height: 400px; overflow-y: auto;">
{escape_html(contract_text[:500])}{"..." if len(contract_text) > 500 else ""}
</div>
</details>
</div>
'''

    # Render each hypothesis
    for record in records:
        html += render_hypothesis_section(record, contract, error_analyses)

    html += '</body></html>'

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# =============================================================================
# Build: Index Page
# =============================================================================
def build_index_page(
    contract_ids: List[int],
    records_by_contract: Dict[int, List[dict]],
    contract_summaries: Dict[int, dict],
    contracts: Dict[int, dict],
    metrics: dict,
    error_analyses: Dict[str, str],
    output_dir: Path,
):
    """Build the index.html overview page."""

    total_eval = metrics.get("total_evaluations", 0)
    total_asserted = metrics.get("asserted_count", 0)
    total_withheld = metrics.get("withheld_count", 0)
    cca = metrics.get("CCA", 0)
    abstention_rate = metrics.get("abstention_rate", 0)
    false_assert_rate = metrics.get("false_assertion_rate", 0)
    baseline = metrics.get("majority_vote_baseline_accuracy", 0)

    # Compute false assertions count
    total_false = 0
    for cid, recs in records_by_contract.items():
        for r in recs:
            if not r.get("withheld", False) and not r.get("gold_match", False):
                total_false += 1

    # Per-hypothesis stats
    per_hyp_cca = metrics.get("per_hypothesis_CCA", {})
    per_hyp_abstention = metrics.get("per_hypothesis_abstention", {})

    # Terminal state distribution
    ts_dist = metrics.get("terminal_state_distribution", {})
    commitment_dist = metrics.get("commitment_level_distribution", {})
    fragility_dist = metrics.get("fragility_type_distribution", {})

    # Find worst hypotheses
    worst_hyps = sorted(per_hyp_cca.items(), key=lambda x: x[1])[:5]

    # Build false assertion details for error summary
    false_assertions = []
    for cid in sorted(records_by_contract.keys()):
        for r in records_by_contract[cid]:
            if not r.get("withheld", False) and not r.get("gold_match", False):
                false_assertions.append({
                    "contract_id": cid,
                    "hypothesis_id": r["hypothesis_id"],
                    "terminal_state": r["terminal_state"],
                    "gold_label": r["gold_label"],
                    "commitment_level": r.get("commitment_level", ""),
                    "conviction_score": r.get("conviction_score", 0),
                })

    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>ContractNLI Forensic Dossier — Index</title>
<style>{SHARED_CSS}
.contract-row {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;
                 box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 15px; }}
.contract-row:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
.metric-bar {{ height: 8px; border-radius: 4px; background: #e9ecef; overflow: hidden; }}
.metric-fill {{ height: 100%; border-radius: 4px; }}
</style>
</head><body>
<div class="header">
<h1>ContractNLI Forensic Dossier <span style="font-size: 0.6em; color: #6c757d;">Run 1 — Index</span></h1>
<p style="color: #666;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div style="background: #f0f4f8; border: 2px solid #17a2b8; border-radius: 8px; padding: 15px; margin: 15px 0;">
<div style="font-size: 1.2em; font-weight: bold; margin-bottom: 10px;">Aggregate Metrics</div>
<div class="stats">
<div class="stat-box">
  <div style="font-size: 0.85em; color: #666;">Total Evaluations</div>
  <div style="font-size: 1.5em; font-weight: bold;">{total_eval}</div>
  <div style="font-size: 0.8em; color: #666;">{len(contract_ids)} contracts &times; 17 hypotheses</div>
</div>
<div class="stat-box" style="border-left-color: #28a745;">
  <div style="font-size: 0.85em; color: #666;">CCA (Credal Coverage Accuracy)</div>
  <div style="font-size: 1.5em; font-weight: bold; color: #28a745;">{cca*100:.1f}%</div>
  <div style="font-size: 0.8em; color: #666;">{total_asserted - total_false} correct / {total_asserted} asserted</div>
</div>
<div class="stat-box" style="border-left-color: #dc3545;">
  <div style="font-size: 0.85em; color: #666;">False Assertions</div>
  <div style="font-size: 1.5em; font-weight: bold; color: #dc3545;">{total_false}</div>
  <div style="font-size: 0.8em; color: #666;">Rate: {false_assert_rate*100:.1f}%</div>
</div>
<div class="stat-box" style="border-left-color: #ffc107;">
  <div style="font-size: 0.85em; color: #666;">Abstention Rate</div>
  <div style="font-size: 1.5em; font-weight: bold; color: #6c757d;">{abstention_rate*100:.1f}%</div>
  <div style="font-size: 0.8em; color: #666;">{total_withheld} withheld</div>
</div>
<div class="stat-box" style="border-left-color: #6c757d;">
  <div style="font-size: 0.85em; color: #666;">Majority Vote Baseline</div>
  <div style="font-size: 1.5em; font-weight: bold; color: #6c757d;">{baseline*100:.1f}%</div>
  <div style="font-size: 0.8em; color: #666;">CAM lift: +{(cca - baseline)*100:.1f}pp</div>
</div>
</div>
</div>

<div style="display: flex; gap: 15px; flex-wrap: wrap; margin: 15px 0;">
<div style="flex: 1; min-width: 300px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
<div style="font-weight: bold; margin-bottom: 10px;">Terminal State Distribution</div>
<table>
<tr><th>State</th><th>Count</th><th>%</th></tr>
'''

    for state, count in sorted(ts_dist.items(), key=lambda x: -x[1]):
        pct = count / total_eval * 100 if total_eval else 0
        color = TERMINAL_STATE_STYLES.get(state, ("", "#6c757d", ""))[1]
        html += f'<tr><td style="color: {color}; font-weight: bold;">{escape_html(state)}</td><td>{count}</td><td>{pct:.1f}%</td></tr>'

    html += '''</table>
</div>
<div style="flex: 1; min-width: 300px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
<div style="font-weight: bold; margin-bottom: 10px;">Commitment Level Distribution</div>
<table>
<tr><th>Level</th><th>Count</th><th>%</th></tr>
'''

    for level, count in sorted(commitment_dist.items()):
        pct = count / total_eval * 100 if total_eval else 0
        color = COMMITMENT_COLORS.get(level, "#6c757d")
        html += f'<tr><td>{commitment_badge(level)}</td><td>{count}</td><td>{pct:.1f}%</td></tr>'

    html += '''</table>
</div>
</div>
'''

    # Fragility rules section
    html += '<div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
    html += '<div style="font-weight: bold; margin-bottom: 10px;">Fragility Rule Distribution</div>'
    html += '<div style="display: flex; gap: 8px; flex-wrap: wrap;">'
    for rule, count in sorted(fragility_dist.items(), key=lambda x: -x[1]):
        pct = count / total_eval * 100 if total_eval else 0
        html += f'<div style="padding: 8px 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;">'
        html += f'<div style="font-weight: bold;">{escape_html(rule)}</div>'
        html += f'<div style="font-size: 0.85em; color: #666;">{count} ({pct:.0f}%)</div>'
        html += '</div>'
    html += '</div></div>'

    # Worst hypotheses section
    html += '<div style="background: white; padding: 15px; border-radius: 8px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
    html += '<div style="font-weight: bold; margin-bottom: 10px;">Worst Hypotheses by CCA</div>'
    html += '<table><tr><th>Hypothesis</th><th>CCA</th><th>Abstention</th></tr>'
    for hyp_id, hyp_cca in worst_hyps:
        abs_rate = per_hyp_abstention.get(hyp_id, 0)
        cca_color = "#28a745" if hyp_cca >= 0.9 else "#ffc107" if hyp_cca >= 0.7 else "#dc3545"
        html += f'<tr><td><strong>{escape_html(hyp_id)}</strong></td>'
        html += f'<td style="color: {cca_color}; font-weight: bold;">{hyp_cca*100:.1f}%</td>'
        html += f'<td>{abs_rate*100:.0f}%</td></tr>'
    html += '</table></div>'

    # False assertions summary
    if false_assertions:
        html += '<div style="background: #f8d7da; border: 2px solid #dc3545; border-radius: 8px; padding: 15px; margin: 15px 0;">'
        html += f'<div style="font-weight: bold; color: #721c24; margin-bottom: 10px;">&#9888; {len(false_assertions)} False Assertions</div>'
        html += '<table><tr><th>Contract</th><th>Hypothesis</th><th>Asserted</th><th>Gold</th><th>Commitment</th><th>Conviction</th></tr>'
        for fa in false_assertions:
            asserted_v = fa["terminal_state"].replace("ASSERT_", "")
            html += f'<tr>'
            html += f'<td><a href="contract_{fa["contract_id"]}.html">{fa["contract_id"]}</a></td>'
            html += f'<td><strong>{escape_html(fa["hypothesis_id"])}</strong></td>'
            html += f'<td style="color: #dc3545;">{escape_html(asserted_v)}</td>'
            html += f'<td style="color: {VERDICT_COLORS.get(fa["gold_label"], "#000")};">{escape_html(fa["gold_label"])}</td>'
            html += f'<td>{commitment_badge(fa["commitment_level"])}</td>'
            html += f'<td>{fa["conviction_score"]:.2f}</td>'
            html += '</tr>'
        html += '</table></div>'

    # Contract list
    html += '<h2 style="margin-top: 30px;">Contracts</h2>'

    for cid in sorted(contract_ids):
        recs = records_by_contract.get(cid, [])
        summary = contract_summaries.get(cid, {})
        contract = contracts.get(cid, {})

        n_total = len(recs)
        n_asserted = sum(1 for r in recs if not r.get("withheld", False))
        n_correct = sum(1 for r in recs if not r.get("withheld", False) and r.get("gold_match", False))
        n_wrong = sum(1 for r in recs if not r.get("withheld", False) and not r.get("gold_match", False))
        n_withheld = sum(1 for r in recs if r.get("withheld", False))
        contract_cca = (n_correct / n_asserted * 100) if n_asserted else 0
        assert_rate = summary.get("assert_rate", n_asserted / n_total if n_total else 0)

        cca_color = "#28a745" if contract_cca >= 90 else "#ffc107" if contract_cca >= 70 else "#dc3545"
        contract_len = summary.get("contract_length", len(contract.get("text", "")))

        html += f'<div class="contract-row">'
        html += f'<div style="min-width: 80px; text-align: center;">'
        html += f'<a href="contract_{cid}.html" style="font-size: 1.3em; font-weight: bold;">#{cid}</a>'
        html += f'<div style="font-size: 0.75em; color: #666;">{contract_len:,} chars</div>'
        html += '</div>'

        # CCA bar
        html += f'<div style="flex: 1; min-width: 150px;">'
        html += f'<div style="font-weight: bold; color: {cca_color};">CCA: {contract_cca:.1f}%</div>'
        html += f'<div class="metric-bar" style="margin-top: 4px;">'
        html += f'<div class="metric-fill" style="width: {contract_cca}%; background: {cca_color};"></div>'
        html += '</div></div>'

        # Counts
        html += f'<div style="display: flex; gap: 15px; font-size: 0.9em;">'
        html += f'<div style="text-align: center;"><div style="color: #28a745; font-weight: bold;">{n_correct}</div><div style="font-size: 0.8em; color: #666;">correct</div></div>'
        html += f'<div style="text-align: center;"><div style="color: #dc3545; font-weight: bold;">{n_wrong}</div><div style="font-size: 0.8em; color: #666;">wrong</div></div>'
        html += f'<div style="text-align: center;"><div style="color: #ffc107; font-weight: bold;">{n_withheld}</div><div style="font-size: 0.8em; color: #666;">withheld</div></div>'
        html += '</div>'

        # Assert rate
        html += f'<div style="min-width: 80px; text-align: center;">'
        html += f'<div style="font-size: 0.85em; color: #666;">Assert</div>'
        html += f'<div style="font-weight: bold;">{assert_rate*100:.0f}%</div>'
        html += '</div>'

        # Verdict mini-grid (17 colored squares)
        html += '<div style="display: flex; gap: 2px; flex-wrap: wrap; max-width: 200px;">'
        for r in recs:
            w = r.get("withheld", False)
            m = r.get("gold_match", False)
            if w:
                sq_color = "#ffc107"
                title = f'{r["hypothesis_id"]}: Withheld'
            elif m:
                sq_color = "#28a745"
                title = f'{r["hypothesis_id"]}: Correct'
            else:
                sq_color = "#dc3545"
                title = f'{r["hypothesis_id"]}: Wrong'
            html += f'<div style="width: 10px; height: 10px; background: {sq_color}; border-radius: 2px;" title="{title}"></div>'
        html += '</div>'

        html += '</div>'  # end contract-row

    html += '</body></html>'

    output_path = output_dir / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# =============================================================================
# Main Entry Point
# =============================================================================
def build_dossier(run_name: str = "1 ContractNLI Run"):
    """Build all dossier files for a ContractNLI run."""
    # Resolve paths
    base_dir = Path(__file__).resolve().parent.parent.parent.parent  # CAM root
    run_dir = base_dir / "04 ContractNLI" / "Runs" / run_name
    data_dir = base_dir / "04 ContractNLI" / "contractnli_data"
    build_log_dir = base_dir / "build_log"
    output_dir = run_dir / "dossiers"

    print(f"Building ContractNLI dossier...")
    print(f"  Run dir:    {run_dir}")
    print(f"  Data dir:   {data_dir}")
    print(f"  Output dir: {output_dir}")

    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("  Loading results...")
    records = load_results(run_dir)
    print(f"    {len(records)} hypothesis evaluations")

    print("  Loading contract summaries...")
    contract_summaries = load_contract_summaries(run_dir)
    print(f"    {len(contract_summaries)} contracts")

    print("  Loading metrics...")
    metrics = load_metrics(run_dir)

    print("  Loading contract texts...")
    contracts = load_contracts(data_dir)
    print(f"    {len(contracts)} contracts with text")

    print("  Loading error analyses...")
    error_analyses = load_error_analyses(build_log_dir)
    print(f"    {len(error_analyses)} analyses loaded")

    # Group records by contract_id
    records_by_contract: Dict[int, List[dict]] = defaultdict(list)
    for r in records:
        records_by_contract[r["contract_id"]].append(r)

    contract_ids = sorted(records_by_contract.keys())
    print(f"\n  Contracts: {contract_ids}")

    # Build contract dossiers
    print("\n  Generating contract dossiers...")
    for cid in contract_ids:
        recs = records_by_contract[cid]
        contract = contracts.get(cid)
        summary = contract_summaries.get(cid)
        out_path = output_dir / f"contract_{cid}.html"
        build_contract_dossier(cid, recs, contract, summary, error_analyses, out_path)
        n_correct = sum(1 for r in recs if not r.get("withheld") and r.get("gold_match"))
        n_asserted = sum(1 for r in recs if not r.get("withheld"))
        cca = n_correct / n_asserted * 100 if n_asserted else 0
        print(f"    contract_{cid}.html — {len(recs)} hyps, CCA {cca:.1f}%")

    # Build index page
    print("\n  Generating index page...")
    build_index_page(
        contract_ids, records_by_contract, contract_summaries,
        contracts, metrics, error_analyses, output_dir
    )

    print(f"\nDossier complete!")
    print(f"  Index:     {output_dir / 'index.html'}")
    print(f"  Contracts: {len(contract_ids)} files")
    print(f"  Open {output_dir / 'index.html'} in a browser to view.")

    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build ContractNLI forensic HTML dossiers"
    )
    parser.add_argument(
        "--run", default="1 ContractNLI Run",
        help="Run name (default: '1 ContractNLI Run')"
    )
    args = parser.parse_args()

    build_dossier(run_name=args.run)
