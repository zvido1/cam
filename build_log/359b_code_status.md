# Step 359b Code Status

**Date:** 2026-05-24
**Status:** ✅ Complete
**Git SHA:** `558c5a9`
**Version:** `app.js?v=429`

---

## Root Cause

`renderContractViewPanel()` read `contract_section_index` from the tenant
wrapper object rather than the tenant results object.

```js
// BEFORE (bug):
var data = currentResults && currentResults.tenants && currentResults.tenants[currentTenantIndex];
var idx = data.contract_section_index;  // undefined — data is tenant envelope, not results
```

`currentResults.tenants[i]` is the tenant envelope `{ filename, results, ... }`.
The pipeline fields (`coverage_assessment`, `cross_provision_findings`,
`contract_section_index`, etc.) live at `tenant.results`. So
`data.contract_section_index` was always `undefined`, triggering the no-data
branch unconditionally.

## Fix

Applied the same `tenant → pr` pattern used by `renderCoveragePanel` and
`renderSynthesisPanel`:

```js
// AFTER (fixed):
var tenantIdx = currentTenantIndex;
var tenant = (currentResults && currentResults.tenants) ? currentResults.tenants[tenantIdx] : null;
var pr = tenant && tenant.results ? tenant.results : null;
if (!pr) return;
var idx = pr.contract_section_index;
```

**Diff:** 4 lines changed in `renderContractViewPanel`, version bump to v429.

## Files changed

- `05 Lease Analyzer/static/app.js` — data path fix + v429 bump
- `05 Lease Analyzer/static/index.html` — version reference `app.js?v=429`

## Validation

Browser validation (Tzvi — hard-refresh, then open `lease_review_20260524_130101_563fc0`):
- [ ] Contract View tab renders article groups (expected ~20+ articles, Atlas Meridian)
- [ ] Section rows show bucket icons and finding counts
- [ ] Clicking a section row expands to show findings
- [ ] LP chips visible on section rows
- [ ] All other tabs still function (Key Issues, Contract Interaction, Evidence, Audit)
