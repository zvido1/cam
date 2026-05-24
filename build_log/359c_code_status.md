# Step 359c Code Status

**Date:** 2026-05-24
**Status:** ✅ Complete
**Git SHA:** `e6c3587`
**Version:** `app.js?v=430`

---

## Bug 1 — Article ordering

**Root cause:** `idx` (contract_section_index) arrives from the backend sorted by
`source_order` (first citation appearance in pipeline output). The grouping loop
preserved that order for both `articleOrder` and each article's `sections[]`.
Section 3.1 had citations early in the pipeline, so Article 3 appeared before
Article 2 even though Article 2 comes first in the contract.

**Fix:** After building `articleMap` and `articleOrder`:

1. Sort `articleOrder` numerically by `parseInt(article_key, 10)`.
2. Sort each article's `sections[]` by `compareSectionKeys(a.section_key, b.section_key)` — a numeric part-by-part comparator that handles "3.1", "3.2", "3.10", "15.1(a)".

`source_order` is preserved in the data (still useful metadata) but no longer drives display order.

---

## Bug 2 — Filter bar bleed

**Root cause:** `contract-clause-filter-bar` is a **shared element** in the
`contract-detail-sticky-shell` div — outside all tab panels (`findings-tab`,
`coverage-tab`, `contractview-tab`, etc.). It is unhidden by
`renderContractSelectorBar()` whenever a contract detail is opened and stays
visible across all tab switches. The `switchResultsTab('contractview')` case
added in step 359 did not hide it.

**Fix:** Added a two-line explicit hide in the `contractview` switch case:

```js
var _cvFilterBar = document.getElementById('contract-clause-filter-bar');
if (_cvFilterBar) _cvFilterBar.classList.add('hidden');
```

When the user switches back to Contract Interaction (synthesis), the existing
`renderContractClauseFilterBar()` call (triggered elsewhere) re-shows the bar.
No other tab's show/hide logic was changed.

---

## Validation checklist (Tzvi — hard-refresh + open `lease_review_20260524_130101_563fc0`)

- [ ] Article 2 appears before Article 3
- [ ] Article 3 appears before Article 4
- [ ] Articles in ascending numeric order throughout
- [ ] Sections within each article in ascending numeric order (3.1, 3.2, 3.3...)
- [ ] No filter bar (Severity/Read/Notes/Reset) visible in Contract View
- [ ] No "Download Working Draft" button in Contract View
- [ ] Contract Interaction tab still works (filters + download still appear when active)
- [ ] All existing tabs unaffected
