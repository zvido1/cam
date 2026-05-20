# Step 354 Code Status

**Date:** 2026-05-20
**SHA:** b20bd90
**Status:** COMPLETE

---

## Root Cause

Two bugs in `jumpToCoverageProvision` in `app.js`:

### Bug 1 — `cv-section-favorable` uses `style="display:none"`, not class `hidden`

`renderCoveragePanel` renders the favorable section as:
```html
<div class="cv-section" id="cv-section-favorable" style="display:none">…</div>
```

The reveal logic used `el.closest('.hidden')` which searches for CSS class `hidden`. Since `cv-section-favorable` uses a `style` attribute instead of a class, `closest('.hidden')` returns `null`. The element is found by `waitForResultsTarget` (DOM presence ≠ display visibility), but `getBoundingClientRect()` returns zeros inside a `display:none` parent. The scroll computes to ~0 and silently jumps to the top of the container instead of the LP row.

**Affected LPs:** Any LP where `use_impact.gap_impact === 'favorable'` or `use_impact.materiality === 'not_applicable'` — these land in `cv-section-favorable`. LP-16 (Parking) on tenants where parking is not a material concern is a confirmed example.

### Bug 2 — `cv-ok-list` arrow never updates (secondary)

The original code ran `el.closest('.hidden')` FIRST, which removed `hidden` from `cv-ok-list`. Then the next check `okList.classList.contains('hidden')` was already `false`, so the `▶`→`▼` arrow update never fired. The section content was revealed correctly, but the section header arrow stayed collapsed (`▶`), which was visually confusing.

---

## IDs Involved

| Section | Hidden mechanism | Handled by |
|---------|-----------------|------------|
| `cv-section-favorable` | `style="display:none"` | New `favSection` check (explicit style reveal) |
| `cv-ok-list` | `class="hidden"` | Moved before `closest` call so arrow updates correctly |
| Other tier-filtered sections | `class="hidden"` | Existing `el.closest('.hidden')` fallback (else branch) |

---

## Fix Applied (`05 Lease Analyzer/static/app.js`, ~line 16161)

```javascript
// cv-section-favorable uses style="display:none" (not class), so closest('.hidden')
// misses it. Reveal it first so getBoundingClientRect() works in the scroll below.
const favSection = document.getElementById('cv-section-favorable');
if (favSection && favSection.contains(el) && favSection.style.display === 'none') {
    favSection.style.display = '';
    _cvShowFavorable = true;
    document.querySelectorAll('.cv-favorable-toggle-btn').forEach(function(btn) {
        btn.classList.add('cv-tier-btn-active');
    });
}
// cv-ok-list uses class hidden — reveal and update the section arrow.
// Must check this BEFORE the general closest('.hidden') call, otherwise
// closest removes hidden first and the okList.contains check becomes false.
const okList = document.getElementById('cv-ok-list');
if (okList && okList.classList.contains('hidden') && okList.contains(el)) {
    okList.classList.remove('hidden');
    const arrow = document.getElementById('cv-ok-arrow');
    if (arrow) arrow.textContent = '▼';
} else {
    // General: reveal any other class-hidden ancestor (e.g. tier-filtered section)
    const hiddenParent = el.closest('.hidden');
    if (hiddenParent) hiddenParent.classList.remove('hidden');
}
```

---

## Version Bump

- `app.js?v=423` → `?v=424`

---

## Validation

Static analysis: all three hidden-section paths now handled:
- LP in `cv-section-favorable` → `favSection.style.display = ''` → `getBoundingClientRect()` returns correct values → scroll works ✓
- LP in `cv-ok-list` → hidden removed, arrow updates to ▼ ✓
- LP in tier-filtered section (edge case after fresh render) → `closest('.hidden')` fallback ✓

Cannot validate live (no browser access), but the geometric failure case is mechanically fixed.
The two concrete test cases from the instruction:
- LP-16 (Parking, `review_needed`): if in favorable section → fixed by Bug 1 fix; if in cv-ok-list → arrow now correct too
- Any other LP with Coverage Gap link from Document View or Audit Trail toolbar → same fixes apply

---

## Decisions Needed

None.
