# 400 Code Status — Coverage Card Provenance Visibility (display-only)

**Date:** 2026-07-05
**Step type:** Display-layer only. No cam/core/ changes. No new model call, prompt, or pipeline stage.

---

## Badge trace result (mandatory gate — reported BEFORE editing)

Traced "Priority Review" render path:

- Line 18276: `'<span class="nav-priority-chip" ...>&#9888; Priority Review</span>'`
  rendered when `item._priority` is truthy.
- `item._priority` is set at:
  - **Coverage LP cards** (line 18414): `_priority: !!(_tri && _tri.priority)` where `_tri = _navCoverageTriageFields(a)` → `priority: isPriorityReview(a)` → `return !!(rpds && rpds.hard_flag === true)` (line ~18057-18065). Driver: `review_priority_distance_signal.hard_flag` (verdict_distance severity). NOT evaluator outcome disagreement.
  - **Synthesis cards** (line 18443): `_priority: !!(_tris && _tris.priority)` where `_tris = _navSynthTriageFields(f)` → `isPriorityReview(f)` checks `severity === "HIGH"`. Driver: synthesis `severity` field. Entirely different condition.

**Conclusion: MIXED path.** The same HTML chip fires for coverage LPs (hard_flag/verdict_distance) AND synthesis cards (HIGH severity) through the same `priorityChipHtml` render at line 18275-18276. Renaming to "Verdict Spread" would be semantically wrong for synthesis cards — HIGH severity ≠ verdict spread.

**Decision: DO NOT rename.** Per the Step 400 spec gate: "If it's driven by anything else... STOP, do NOT rename, flag it for Tzvi."

**Flag for Tzvi:** If you want to rename the badge, it needs to be a TYPE-CONDITIONAL rename — different text for coverage LP cards vs synthesis cards. That requires a more targeted change (pass card type through to the nav-panel renderer and branch the chip text). Alternatively, define a separate `priorityChipHtml` for each card type. Either way: separate step, separate decision. Not done here.

---

## What was built

### 1. Exposure provenance chip (app.js)

Replaced `srcNote` (line ~16384) with a 3-state `expProvenanceChip` variable:

```javascript
const _expSrc = src || (a.exposure_reason_code || "");
const expProvenanceChip = _expSrc === "model"
    ? '<span class="cv-exp-provenance-chip">Lease-specific exposure</span>'
    : (_expSrc === "schema" || _expSrc === "schema_default")
        ? '<span class="cv-exp-provenance-chip cv-exp-default">Default exposure</span>'
        : '<span class="cv-exp-provenance-chip cv-exp-unknown">Exposure source unknown</span>';
```

Chip is appended inline to the `cv-ci-exposure` div (inside `clientImpactHtml`, only when `stmt` is present). On the frozen 2026-06-11 Atlas run: 30 cards show "Default exposure," 2 show "Lease-specific exposure." The old "AI assessed" label (model-only, no label for schema) is replaced.

### 2. Materiality provenance block (app.js)

New block inserted after `contextDepHtml` construction, before the `return` template:

```javascript
var _matDefault = a.materiality || "";
var _matAssessed = (a.use_impact && a.use_impact.materiality) || "";
var matProvHtml = "";
if (_matAssessed) {
    matProvHtml = '<div class="cv-mat-prov"><span class="cv-mat-prov-chip">Assessed materiality: ' + _matAssessed + '</span>';
    if (_matDefault && _matDefault !== _matAssessed) {
        matProvHtml += ' <span class="cv-mat-prov-chip cv-mat-default">Default: ' + _matDefault + '</span>';
    }
    matProvHtml += '</div>';
} else if (_matDefault) {
    matProvHtml = '<div class="cv-mat-prov"><span class="cv-mat-prov-chip cv-mat-default">Default materiality: ' + _matDefault + '</span></div>';
}
```

`${matProvHtml}` inserted in the return template between `${clientImpactHtml}` and `${contextDepHtml}`.

On the frozen 2026-06-11 Atlas run:
- 7 assessed cards: show purple "Assessed materiality: X" chip; LP-03/05/14/16 also show grey "Default: low" because `use_impact.materiality` differs from `a.materiality`.
- 25 unassessed cards: show grey "Default materiality: low" (or high for LP-14/20/xx).

**Product-tone note (per spec):** This puts a visible "Default materiality" line on ~25 of 32 cards, making the tool's schema-default reliance visible on first view. Intended — honest provenance. If Tzvi wants it softened (hover-only, or only when assessed-vs-default conflict), that's a tuning step.

### 3. Context Dependency strip — NOT regressed

398/398b/399 block untouched. Firing logic unchanged. Wording unchanged ("Depends on your use" / "Genuinely unsettled" / "Impact depends on your specific operations").

### 4. Badge rename — NOT done (MIXED path, see trace above)

### 5. Sorting — explicitly DEFERRED (not forgotten)

Sorting was explicitly out of scope for Step 400, by Tzvi's call. Cards render in pipeline order. Reason: sorting is a product-judgment decision and should wait until the provenance chips are visible in the real UI. Step 400 builds the honest mess first; a separate authorized step will organize it.

---

## Render path touched

| Change | Location | Lines |
|--------|----------|-------|
| `expProvenanceChip` declaration | `buildItem()` | ~16384-16389 (replaced `srcNote`) |
| `expProvenanceChip` usage | `buildItem()` / `cv-ci-exposure` push | ~16665 |
| `matProvHtml` block | `buildItem()` | after contextDepHtml, before return |
| `${matProvHtml}` in template | `buildItem()` return | after `${clientImpactHtml}` |

---

## Confirmed: no prohibited changes

- No `cam/core/` or `cam/adapters/` files touched
- No model call, prompt, or pipeline stage
- No hardcoded clause content
- `classifyFindingType()` semantics unchanged
- Risk not redefined
- `hard_flag` logic and routing unchanged
- Context Dependency strip (398/398b/399) not regressed

---

## How to view

1. Hard-refresh browser after `git pull` (Ctrl+Shift+R).
2. Run a **Mode C (Analyze)** job (or load the frozen 2026-06-11 run).
3. Switch to **Coverage & Gaps** tab.
4. Any card with an exposure statement: small grey chip ("Default exposure" or "Lease-specific exposure") appears inline after the exposure text.
5. Below the Client Impact block: grey "Default materiality: low" row (unassessed cards) OR purple "Assessed materiality: medium/high" chip (7 assessed cards — LP-03/05/10/14/16/20/32).

---

## Files changed

- `05 Lease Analyzer/static/app.js` — exposure chip, materiality provenance, no other logic
- `05 Lease Analyzer/static/style.css` — Step 400 CSS block: `.cv-exp-provenance-chip`, `.cv-exp-default`, `.cv-exp-unknown`, `.cv-mat-prov`, `.cv-mat-prov-chip`, `.cv-mat-default`
- `05 Lease Analyzer/static/index.html` — cache-buster bumped `app.js?v=470` → `app.js?v=471`

---

## Commit SHA

`282abb9` — unpushed, local main.
