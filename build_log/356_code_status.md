# Step 356 Code Status — Supplement #21 Phase 3: dispute_signal → Review Needed

**Date:** 2026-05-20
**SHA:** 4988746
**Status:** COMPLETE (no live run — Railway deploy required)

---

## Changes Made

### `cam/adapters/lease_review/lease_coverage.py`

**Change A — Phase 3 block in Step 305 (lines 262–314)**

Between `_state_305 = _result_305["coverage_state_baseline"]` and the unenforceable check:

```python
# ── Supplement #21 Phase 3: dispute_signal propagation ──────────
_disputed_critical = _result_305.get("elements_disputed_critical", 0)
_dispute_signal = {"triggered": False, "critical_disputed_count": _disputed_critical, "reason": None}
if _disputed_critical > 0 and _state_305 != "not_applicable":
    _state_305 = "review_needed"
    _dispute_signal = {
        "triggered": True,
        "critical_disputed_count": _disputed_critical,
        "reason": f"{_disputed_critical} critical rubric element(s) disputed — majority verdict withheld, human review required",
    }
    logger.info(f"[lease_coverage] {pid}: Phase 3 dispute_signal triggered — {_disputed_critical} critical disputed element(s); state → review_needed")

# Unenforceable override runs after Phase 3
# (potentially_unenforceable is more specific than review_needed)
_text_lower_305 = tenant_text.lower()
_unenforceable_305 = _check_unenforceable_patterns(pid, _text_lower_305)
if _unenforceable_305:
    _state_305 = "potentially_unenforceable"
```

Three new fields appended to `_a` after the existing Step 351 fields:
```python
_a["elements_disputed_critical"] = _disputed_critical
_a["elements_disputed_important"] = _result_305.get("elements_disputed_important", 0)
_a["dispute_signal"] = _dispute_signal
```

**Change B — `_build_assessment()` defaults (lines ~734-747)**

Three new default fields so every CA entry carries them even when Stage 305 doesn't run:
```python
"elements_disputed_critical": 0,
"elements_disputed_important": 0,
"dispute_signal": {
    "triggered": False,
    "critical_disputed_count": 0,
    "reason": None,
},
```

### `05 Lease Analyzer/static/app.js` — v424 → v425

**Change C — `⚑ Critical Dispute` badge in Coverage & Gaps `buildItem`**

Inserted after `disagSeverityHtml` block:
```javascript
const _dispCrit = a.elements_disputed_critical || 0;
const _dispImp  = a.elements_disputed_important || 0;
const disputeSignalHtml = _dispCrit > 0
    ? '<span class="cv-dispute-signal cv-dispute-signal-critical" title="...">&#x2691; Critical Dispute</span>'
    : (_dispImp > 0
        ? '<span class="cv-dispute-signal cv-dispute-signal-important" title="...">Disputed</span>'
        : '');
```

Badge renders in `cv-item-header` after the status badge and severity label.

**Change D — dispute_signal note in Audit Trail `buildCoverageAuditSection`**

After `_auditSevNote` construction, new `_auditDisputeNote` block:
- Fires when `a.dispute_signal.triggered === true`
- Shows ⚑ + count + baseline verdict
- Injected into LP body BEFORE `_auditSevNote` (appears at top of audit section)

### `05 Lease Analyzer/static/style.css` — v378 → v379

New classes:
- `.cv-dispute-signal` / `.cv-dispute-signal-critical` / `.cv-dispute-signal-important` — amber/grey badge variants
- `.audit-cov-dispute-signal` / `.audit-cov-dispute-baseline` — audit trail note styling

---

## Phase 3 Firing LPs

### Live run validation
**Not performed** — requires Railway deploy + T-10 and Atlas Meridian runs. Phase 3 fires when `elements_disputed_critical > 0` in a live evaluation. The specific LPs that fire depend on which critical elements produce evaluator disagreement on those runs.

### Predicted Phase 3 candidates (from prior run data)

Based on prior Atlas Meridian run data cited in the instruction (LP-09 had 3 disputed, LP-20 had 3 disputed, LP-32 had 3 disputed):

**LP-09** (Assignment & Subletting) critical elements:
- LP-09 has 12 elements. The elements with `absence_severity=high` and `not_law_covers` would be critical. Based on schema, LP-09 assignment/subletting elements that are critical include: `no_recapture_right`, `no_profit_sharing_obligation`. If any of these were in the 3 disputed, Phase 3 would fire.

**LP-20** (Exclusivity) — specific disputed elements would need to be checked against schema.

**LP-32** (Hazardous Materials) critical elements: `hazmat_definition`, `de_minimis_carveout`, `landlord_pre_existing_representations`. If LP-32 had 3 disputed and any matched these critical elements, Phase 3 fires on LP-32.

Run T-10 and Atlas Meridian after Railway deploy and check `pipeline_results.json`:
```python
import json
data = json.load(open('pipeline_results.json'))
for lp in data['coverage_assessment']:
    ds = lp.get('dispute_signal', {})
    if ds.get('triggered'):
        print(f"{lp['issue_area_id']}: baseline={lp.get('coverage_state_baseline')} → final={lp.get('coverage_state')} | {ds['critical_disputed_count']} critical disputed")
```

---

## Correctness Verification (static)

- `coverage_state_baseline` is set from `_result_305["coverage_state_baseline"]` BEFORE Phase 3 runs → preserved as majority verdict ✓
- `coverage_state` (via `_state_305`) is set to `review_needed` by Phase 3 → what the lawyer sees ✓
- `potentially_unenforceable` overrides `review_needed` (unenforceable check runs after Phase 3) ✓
- `not_applicable` LPs are excluded from Phase 3 firing (`_state_305 != "not_applicable"` guard) ✓
- Supplementary-only disputes don't fire Phase 3 (counter tracks critical+important only) ✓
- Syntax check: PASSED ✓

---

## Decisions Needed

None. Phase 4 (UI indicator for dispute_signal in sidebar / expanded detail) is a separate step.
