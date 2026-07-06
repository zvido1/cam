# 403 Code Status — Land on Overview + all buckets collapsed (display-only)

**Date:** 2026-07-05
**Step type:** Display-layer only. No cam/core/ changes. No model call, prompt, or pipeline stage.

---

## Change 1 — Landing tab after run loads

**Finding: already Overview. No code change made.**

`activeTopTab` is initialized to `"overview"` at line 286:
```javascript
let activeTopTab = "overview";
```
It is explicitly reset to `"overview"` on every new run at lines 865 and 2868/2889 (run-completion handlers). When `renderResults()` calls `switchTopTab(activeTopTab)` at line 3300, it always passes `"overview"` for a fresh run. The Results view already lands on the Overview tab by default.

---

## Change 2 — All top-level sidebar sections start collapsed (revises 402)

### Edit made

Added `risk: true` to `_NAV_SECTION_DEFAULT_COLLAPSED` (added by 402 at line ~18325):

```javascript
// Before (402 state)
var _NAV_SECTION_DEFAULT_COLLAPSED = {
    review: true, improvement: true, addressed: true
};

// After (403)
var _NAV_SECTION_DEFAULT_COLLAPSED = {
    risk: true, review: true, improvement: true, addressed: true
};
```

### How RISK is rendered

`_navSectionWrap('risk_' + tIdx, ...)` at line ~18581 calls `_navSectionCollapsed('risk_0', jobId)`. That function strips `_0` → base `risk` → looks up `_NAV_SECTION_DEFAULT_COLLAPSED['risk']` → `true` → collapsed. The RISK section body renders with `style="display:none"` on first visit.

### Nothing forces RISK open

Scanned for any code path that could open RISK independently:
- `_navSectionWrap` only reads `_navSectionCollapsed` — no override logic.
- The sub-group defaults (`risk_gaps: true` etc., set in 402) are now irrelevant on first visit since RISK's own body is hidden; they remain correct for when the user manually expands RISK.
- No `localStorage.setItem` call writes a `cam_sidebar_risk_*` key at render time.
- No startup code calls `_navSectionToggle` for RISK.

### localStorage caveat

If a user (or prior testing session) previously toggled the RISK section, their localStorage key `cam_sidebar_risk_<jobId>` holds `'0'` (open) and will OVERRIDE the new default. The new default `risk: true` only fires when `localStorage.getItem(key) === null` (key absent). To see the new default: open in a fresh browser window (no prior localStorage) or clear `cam_sidebar_risk_*` entries in DevTools → Application → Local Storage.

---

## Confirmed: no prohibited changes

- No `cam/core/` or `cam/adapters/` files touched
- No model call, prompt, or pipeline stage
- `classifyFindingType()` unchanged; counts/routing/ordering unchanged
- 400 provenance chips not regressed
- 398/398b/399 Context Dependency strip not regressed
- 402 title-wrap (`.nav-item-name` CSS) not regressed
- Collapse/expand interaction unchanged

---

## Files changed

- `05 Lease Analyzer/static/app.js` — `risk: true` added to `_NAV_SECTION_DEFAULT_COLLAPSED`
- `05 Lease Analyzer/static/index.html` — cache-buster bumped `app.js?v=472` → `app.js?v=473`
- `static/style.css` — not touched

---

## Commit SHA

(pending)
