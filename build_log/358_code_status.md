# Step 358 — Code Status

**Status:** COMPLETE
**Date:** 2026-05-21
**SHA:** af7efab

---

## What Was Done

Supplement #21 Phase 4: Added `◈ Disputed` indicator chip to Risk bucket LP cards in the sidebar.

### Renderer found

**Function:** `_navBuildUnifiedItem` — `app.js` line 17120

This is the single card-builder for all unified sidebar items (Risk, Review Needed, Improvement). Items are assembled in `renderNavSidebar` (line 17184) from `coverage_assessment` objects and pushed into bucket arrays (`risk`, `reviewNeeded`, etc.).

### Was `elements_disputed` available directly?

No — it was on the `coverage_assessment` object (`a`) but was not being passed into the item dict. Added it explicitly in two places:

1. **Mode C path** (~line 17238): `pushItem` call for `ca.forEach` — added `elements_disputed: a.elements_disputed || 0` and `elements_disputed_critical: a.elements_disputed_critical || 0`
2. **Non-mode-C path** (~line 17289): `pushItem` call for `ca2.forEach` — same two fields added

### Indicator logic (in `_navBuildUnifiedItem`)

```js
const disputedHtml = item.elements_disputed_critical > 0
    ? '<span class="cv-disputed-indicator cv-disputed-indicator--critical">⚑ Critical Disputed</span>'
    : item.elements_disputed > 0
    ? '<span class="cv-disputed-indicator">◈ Disputed</span>'
    : '';
```

Rendered after the `nav-item-desc` div, inside the `<button>`. Because `_navBuildUnifiedItem` is called for ALL buckets (Risk, Review Needed, Improvement), but only Risk LPs that avoided Phase 3 will have `elements_disputed > 0` in practice — Phase 3 LPs (LP-14, LP-22, LP-27, LP-28) are already routed to Review Needed, so their `elements_disputed` may be > 0 but their cards are NOT in the Risk bucket.

### Files changed

| File | Change |
|------|--------|
| `app.js` | `_navBuildUnifiedItem`: add `disputedHtml` logic; both `pushItem` calls: pass `elements_disputed` + `elements_disputed_critical` |
| `style.css` | Added `.cv-disputed-indicator` and `.cv-disputed-indicator--critical` CSS |
| `index.html` | Bumped `app.js?v=427`, `style.css?v=380` |

---

## Expected LPs showing ◈ Disputed on Atlas Meridian

Risk LPs with `elements_disputed > 0` (Phase 3 LPs excluded):
LP-02, LP-09, LP-10, LP-16, LP-17, LP-19, LP-20, LP-21, LP-25, LP-26, LP-29, LP-30, LP-32

Phase 3 LPs (Review Needed — no indicator expected there): LP-14, LP-22, LP-27, LP-28

---

## Decisions Needed

None.
