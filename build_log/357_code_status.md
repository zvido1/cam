# Step 357 Code Status — Phase 3 LPs Surface in Coverage & Gaps "Needs Attention"

**Date:** 2026-05-21
**SHA:** 3abae94
**Status:** COMPLETE

---

## Root Cause

`renderCoveragePanel()` in `app.js` categorizes LPs into sections with this filter:

```javascript
const problems = ca.filter(a =>
    !_isFavorable(a) && !_isUseImpactFavorable(a) &&
    (a.coverage_state === "covered_unfavorable" || a.partial_class === "partial_material" || a.coverage_state === "missing")
);
```

`review_needed` was not in the set of checked states, so Phase 3 LPs
(coverage_state = "review_needed") fell into `other` → "Adequately Covered."

---

## Was Change 1 (Python only) Sufficient?

**No. Both changes were required.**

`renderCoveragePanel()` does NOT read `requires_attention` from the CA entry.
It has its own explicit `coverage_state` check. Change 1 (`requires_attention`)
is consumed by server-side summary logic and `_log_coverage_summary()`, not by
the Coverage & Gaps panel renderer.

---

## Changes Made

### Change 1 — `lease_coverage.py` `_build_assessment()` (line 742)

```python
# Before:
"requires_attention": coverage_state in (
    "missing", "broken_xref", "covered_unfavorable",
    "partial", "potentially_unenforceable"
),

# After:
"requires_attention": coverage_state in (
    "missing", "broken_xref", "covered_unfavorable",
    "partial", "potentially_unenforceable", "review_needed"
),
```

Correct semantics: review_needed means CAM cannot assert a verdict — by
definition this requires human attention.

### Change 2 — `app.js` `renderCoveragePanel()` (line 15614-15617)

```javascript
// Before:
const problems = ca.filter(a =>
    !_isFavorable(a) && !_isUseImpactFavorable(a) &&
    (a.coverage_state === "covered_unfavorable" || a.partial_class === "partial_material" || a.coverage_state === "missing")
);

// After:
const problems = ca.filter(a =>
    !_isFavorable(a) && !_isUseImpactFavorable(a) &&
    (a.coverage_state === "covered_unfavorable" || a.partial_class === "partial_material"
        || a.coverage_state === "missing" || a.coverage_state === "review_needed")
);  // Step 357: review_needed added (Phase 3 LPs surface in Needs Attention)
```

The `_isUseImpactFavorable` guard is kept for `review_needed` for consistency:
if a LP is `review_needed` but also has `use_impact.gap_impact === 'favorable'`,
it appears in the Favorable section (which is the right call — use_impact
determination overrides the undecided classification). For LP-14/22/27/28 none
have favorable use_impact so this guard doesn't apply.

### Change 3 — `app.js` legacy sidebar `needsAttention` filter (line 16723-16728)

```javascript
// Added alongside existing checks:
|| a.coverage_state === "review_needed"   // Step 357: Phase 3 LPs
```

Keeps the sidebar consistent with the Coverage & Gaps panel.

---

## Condition Quoted

The Coverage & Gaps categorization condition that determined "Needs Attention"
before this step (line 15614–15617 in app.js v425):

```javascript
const problems = ca.filter(a =>
    !_isFavorable(a) && !_isUseImpactFavorable(a) &&
    (a.coverage_state === "covered_unfavorable" || a.partial_class === "partial_material" || a.coverage_state === "missing")
);
```

---

## Validation

No live re-run performed (as specified — use existing job
`lease_review_20260521_010256_e43bad`). The fix is a client-side filter change:
existing `pipeline_results.json` already has `coverage_state: "review_needed"`
for Phase 3 LPs. The Coverage & Gaps tab will re-categorize them on next load.

Expected result for Atlas Meridian:
- "Needs Attention" count: 1 → at least 5 (LP-14, LP-22, LP-27, LP-28 + LP-20)
- ⚑ Critical Dispute badge visible on those LPs without expanding "Adequately Covered"
- "Adequately Covered" count decreases by the number of Phase 3 LPs

---

## Decisions Needed

None.
