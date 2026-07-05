# 402 Code Status — Sidebar default-collapse + card title wrap (display-only)

**Date:** 2026-07-05
**Step type:** Display-layer only. No cam/core/ changes. No model call, prompt, or pipeline stage.

---

## Change 1 — Sidebar default-collapsed state

### Mechanism found

Two collapse systems exist side by side in `static/app.js`:

**Top-level sections** (`_navSectionWrap`, line 18339):
- `_navSectionCollapsed(sectionId, jobId)` at line 18324 reads localStorage key `cam_sidebar_<sectionId>[_<jobId>]`. Returns `true` (collapsed) if value is `'1'`. Returns `false` if the key is absent (first visit) — no default-state support. This is why all sections started expanded: no localStorage entry → `false` → expanded.

**Sub-groups** (`_navSubGroupWrap`, line 18217):
- `_navSubGroupCollapsed(sectionId, jobId)` at line 18208 already had a `_NAV_SUBGROUP_DEFAULT_COLLAPSED` dict and a default-lookup pattern. `risk_gaps` and `risk_compound` were `false` (open by default); `risk_directional` was already `true`.

### What the mechanism supported

The existing sub-group system already had the right pattern. The top-level section system needed the same treatment. Change: add a `_NAV_SECTION_DEFAULT_COLLAPSED` dict (same pattern) and extend `_navSectionCollapsed` to check it on first visit (no localStorage entry). This is a default-state change only — user toggles still write to localStorage and persist on revisit, unchanged.

**Interpretation**: Full spec achieved cleanly — RISK expands on load showing all three sub-section headers (Coverage Gaps, Cross-clause Risks, One-sided Terms) with counts, those sub-sections themselves collapsed; NEEDS REVIEW, IMPROVEMENT, ADDRESSED all start collapsed showing only their header + count.

### Exact edits

**`_NAV_SUBGROUP_DEFAULT_COLLAPSED`** — changed risk sub-groups to all-collapsed:

```javascript
// Before
var _NAV_SUBGROUP_DEFAULT_COLLAPSED = {
    risk_gaps: false, risk_compound: false, risk_directional: true,
    review_coverage: false, review_onesided: true, review_conflicting: false
};

// After
var _NAV_SUBGROUP_DEFAULT_COLLAPSED = {
    risk_gaps: true, risk_compound: true, risk_directional: true,
    review_coverage: true, review_onesided: true, review_conflicting: true,
    review_consnotassessed: true
};
```

**`_navSectionCollapsed`** — added default dict + lookup:

```javascript
// Before
function _navSectionCollapsed(sectionId, jobId) {
    return localStorage.getItem('cam_sidebar_' + sectionId + (jobId ? '_' + jobId : '')) === '1';
}

// After
var _NAV_SECTION_DEFAULT_COLLAPSED = {
    review: true, improvement: true, addressed: true
    // 'risk' absent → defaults to false (expanded)
};
function _navSectionCollapsed(sectionId, jobId) {
    var stored = localStorage.getItem('cam_sidebar_' + sectionId + (jobId ? '_' + jobId : ''));
    if (stored !== null) return stored === '1';
    var base = sectionId.replace(/_\d+$/, '');
    return _NAV_SECTION_DEFAULT_COLLAPSED[base] || false;
}
```

**Note on localStorage persistence:** If a user previously interacted with the sidebar, their localStorage keys may override the new defaults. They'll see the new defaults only for sections they haven't personally toggled. Fresh browser / incognito will always show the new defaults.

---

## Change 2 — Issue-card title wraps instead of clipping

### Selector found

`static/style.css` at `.nav-sidebar-content .nav-item-name` (line ~12859):

```css
/* Before */
.nav-sidebar-content .nav-item-name {
    flex: 1 1 auto;
    min-width: 0;
    font-weight: 600;
    font-size: 0.8125rem;
    color: var(--text, #1e293b);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* After */
.nav-sidebar-content .nav-item-name {
    flex: 1 1 auto;
    min-width: 0;
    font-weight: 600;
    font-size: 0.8125rem;
    color: var(--text, #1e293b);
    overflow: visible;
    white-space: normal;
}
```

**Approach used:** plain wrap (`white-space:normal; overflow:visible`), no `-webkit-line-clamp`. The flex parent (`nav-item-top`) naturally grows to fit multi-line title text; no fixed height existed on the card that would cause overlap. `min-width:0` retained (prevents flex blowout). `-webkit-line-clamp:2` was not needed — unbounded wrap is not a layout problem here because the sidebar card has no constrained height.

---

## Confirmed: no prohibited changes

- No `cam/core/` or `cam/adapters/` files touched
- No model call, prompt, or pipeline stage
- `classifyFindingType()` unchanged
- Routing/counts/ordering unchanged
- 400 provenance chips not regressed (no buildItem touch)
- 398/398b/399 Context Dependency strip not regressed
- Collapse interaction (click handler, localStorage write, toggle icon) unchanged

---

## Files changed

- `05 Lease Analyzer/static/app.js` — `_NAV_SUBGROUP_DEFAULT_COLLAPSED` + `_NAV_SECTION_DEFAULT_COLLAPSED` + `_navSectionCollapsed`
- `05 Lease Analyzer/static/style.css` — `.nav-sidebar-content .nav-item-name` white-space + overflow
- `05 Lease Analyzer/static/index.html` — cache-buster bumped `app.js?v=471` → `app.js?v=472`

---

## Commit SHA

`f52072e` — unpushed, local main.
