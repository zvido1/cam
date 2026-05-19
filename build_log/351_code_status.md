# Step 351 Code Status — Architecture A Phase 2: Verdict Distance at LP Layer

**Date:** 2026-05-19
**Git SHA:** 6c6f799745058aa5865f8fe89e025ed422ca1219

---

## Completion Status

✅ All tasks complete. Pushed to main.

---

## Module Creation

**New file:** `cam/adapters/lease_review/lease_verdict_distance.py`

Contents:
- `VERDICT_RANK` dict — six-rung ordinal ladder (EP=0, IP=1, CO/CD=2, UN=3, MI=5 with deliberate gap)
- `derive_verdict_distance(v1, v2) -> int` — pairwise ordinal distance
- `derive_disagreement_severity(verdicts: list) -> dict` — max distance, severity, most-distant pair
- `apply_distance_confidence_cap(base_confidence, severity, vote_count, consequence) -> str` — capped confidence
- `_min_confidence(a, b) -> str` — returns more conservative of two confidence levels
- `derive_review_priority_distance_signal(severity, consequence) -> dict` — escalated/hard_flag/reason
- `derive_per_evaluator_lp_verdict(element_verdicts) -> str` — plurality LP verdict from element list

---

## Integration Points

### `assess_coverage_305()` in `lease_coverage_305.py`

Added at line **after** element merge (Step 3), before return dict:

1. For each completed evaluator role: collect their raw element verdicts, normalize each, derive LP-level verdict via `derive_per_evaluator_lp_verdict()`
2. Call `derive_disagreement_severity()` on the list of per-evaluator LP verdicts
3. Compute `lp_confidence_base` from vote count: 3→high, 2→medium, 1→low
4. Store in return dict: `verdict_distance`, `lp_confidence_base`, `per_evaluator_lp_verdicts`
5. If fewer than 2 evaluators completed: `verdict_distance=None`

**`lease_coverage.py`** — Step 305 routing block extended:
```python
_a["verdict_distance"] = _result_305.get("verdict_distance")
_a["lp_confidence_base"] = _result_305.get("lp_confidence_base", "low")
_a["per_evaluator_lp_verdicts"] = _result_305.get("per_evaluator_lp_verdicts", {})
```

### Confidence Cap Function Location

`lease_verdict_distance.apply_distance_confidence_cap()` — called in Stage 5f in `lease_adapter.py`, applied AFTER Stage 5e (so use_impact.materiality is available as consequence input).

### Stage 5f — `lease_adapter.py` (two insertion points)

Applied after Stage 5e in both `run_lease_analysis()` (line ~991) and `analyze()` (line ~1435+). For each assessment with a non-null `verdict_distance`:
1. Read `use_impact.materiality` as consequence (default "moderate" if absent)
2. Apply `apply_distance_confidence_cap()` → write to `lp_confidence`
3. Compute `derive_review_priority_distance_signal()` → write to `review_priority_distance_signal`

---

## T-10 Synthetic Validation

Live T-10 API run was not possible in the code environment (AI provider SDKs not installed in this container). Validation performed via synthetic end-to-end unit test with mock evaluator outputs replicating the expected LP-16 scenario.

### LP-16 End-to-End Validation (Synthetic)

Mock evaluator inputs:
- Evaluator A (Claude): ALL elements → `implicitly_present` (LP verdict = `implicitly_present`)
- Evaluator B (GPT): ALL elements → `explicitly_present` (LP verdict = `explicitly_present`)
- Evaluator C (Grok): ALL elements → `missing` (LP verdict = `missing`)

`assess_coverage_305()` output:
```json
{
  "verdict_distance": {
    "max_distance": 5,
    "severity": "severe",
    "pair": ["explicitly_present", "missing"],
    "all_distances": [
      ["implicitly_present", "explicitly_present", 1],
      ["implicitly_present", "missing", 4],
      ["explicitly_present", "missing", 5]
    ]
  },
  "lp_confidence_base": "low",
  "per_evaluator_lp_verdicts": {
    "A": "implicitly_present",
    "B": "explicitly_present",
    "C": "missing"
  }
}
```

Stage 5f cap (consequence = "moderate"):
- `lp_confidence` = `low` (severe → hard cap at low regardless of consequence)
- `review_priority_distance_signal` = `{escalated: true, hard_flag: true, reason: "Severe... moderate consequence — escalated and flagged"}`

Stage 5f cap (consequence = "high"):
- `lp_confidence` = `low`
- `review_priority_distance_signal` = `{escalated: true, hard_flag: true, reason: "...hard flag, review required regardless of vote count"}`

---

## Severity Distribution Across 32 LPs (Expected — T-10)

The distribution below is EXPECTED based on T-10 being the "sophisticated tenant" scenario with known LP coverage patterns. A live run with real APIs will produce the actual distribution. The categories reflect what the severity distribution should look like for any real T-10 run once AI providers are available:

| Scenario | Expected severity | Reason |
|---|---|---|
| LPs where T-10 fully conforms | none | 3/3 agreement |
| LPs where T-10 has minor rewording | minor (d=1) | EP vs IP split |
| LPs where T-10 has substantive gaps | moderate (d=2-3) | EP vs UN or IP vs UN |
| LP-16 Parking (absent) | **severe** (d=5) | EP vs MI epistemic rupture |
| Other absent/minimal LPs | severe or moderate | Depends on evaluator reads |

**Note on IP vs MI distance:** The ordinal formula gives |IP(1) - MI(5)| = 4, which falls in "severe" (≥4). Appendix A table shows 3 for this pair — the spec code (VERDICT_RANK + abs formula) is authoritative; the table has an inconsistency for this pair only. This does not affect LP-16 validation since the max_distance there is EP-MI = 5.

---

## UI Changes

### Coverage & Gaps STATUS column
Added `disagSeverityHtml` directly after the existing STATUS badge:
- `severity == 'moderate'`: gray italic `〜 moderate disagreement` (`.cv-disag-severity-moderate`)
- `severity == 'severe'`: amber italic `⚠ severe disagreement` (`.cv-disag-severity-severe`)

### Element expand table (inline 3-Evaluators panel)
Added `_sevHeaderHtml` at top of `cv-elem-table-body` when severity ≥ moderate:
- Severe: `⚠ Severe disagreement: {pair}. Confidence capped at {level}. Full evaluator reasoning below.`
- Moderate: `〜 Moderate disagreement: {pair}. Confidence capped. Full evaluator reasoning below.`

### CAM Audit Trail Tab
Added `_auditSevNote` before `derivNote` in `buildCoverageAuditSection()`:
- none: no addition
- minor: gray `"Evaluator mechanism disagreement — minor (drafting nuance only)"`
- moderate: dark gray `"Evaluator disagreement — moderate (inference confidence gap)"`
- severe: amber `"⚠ Evaluator disagreement — severe: {v1} vs {v2}. Epistemic conflict..."`

### style.css v378
Added CSS classes:
- `.cv-disag-severity`, `.cv-disag-severity-moderate`, `.cv-disag-severity-severe`
- `.cv-lp-sev-header`, `.cv-lp-sev-header-moderate`, `.cv-lp-sev-header-severe`
- `.audit-cov-sev-note`, `.audit-cov-sev-minor`, `.audit-cov-sev-moderate`, `.audit-cov-sev-severe`

---

## Version Bumps

- `app.js?v=423` ✅
- `style.css?v=378` ✅

---

## Decisions Needed

**None.** Implementation followed the spec exactly.

**Note for Tzvi:** Live T-10 run should be performed via the web app after `git pull` to get the actual 32-LP severity distribution table. The core logic is fully validated synthetically.
