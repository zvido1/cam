# 398 Code Status — Context Dependency UI Visibility (Part 1)

**Date:** 2026-07-05
**Step type:** Display-layer only. No cam/core/ changes. No new model call, prompt, or pipeline stage.

---

## Step 1 finding: Was use_impact already present at the render point?

**YES — present, and partially rendered (Step 375G).**

### Render path
`renderCoveragePanel()` (line ~16275) → `buildItem(a, tier)` (line ~16346) → return template (line ~16670+).

`buildItem` is the Mode C coverage finding card builder. It is called once per `coverage_assessment[]` item in the "Coverage & Gaps" tab. `a` is the raw coverage_assessment dict from the pipeline results.

### use_impact at the render point
At line 16658 (Step 375G), `a.use_impact` is already accessed:
```js
const _ciUi = a.use_impact;
const _ciReason = (_ciUi && _ciUi.use_reasoning) ? String(_ciUi.use_reasoning).trim() : '';
const _ciGap = normalizeUseConsequence(_ciUi) || '';
```
The 375G block renders `use_impact.use_reasoning` as a "Client Impact" div (indigo left-border box) and `exposure_statement` below it. It does NOT:
- Filter out fallback strings
- Show `use_consequence` value
- Show `evaluator_agreement` split note
- Label anything "Context Dependency"

The STOP condition (use_impact not reaching coverage items) did NOT fire. The data is already at the render point.

---

## What was added

### app.js — Context Dependency block in `buildItem`
**Insertion point:** immediately after the existing `clientImpactHtml` construction (after Step 375G block, before the return template). Lines ~16669–16703 (new code).

**Logic:**
- Reads `a.use_impact.use_consequence` via `normalizeUseConsequence()` (the existing normalizer from Step 375M).
- Reads `a.use_impact.use_reasoning`, filtered against known fallback strings:
  - `"No use profile available — cannot assess tenant-specific impact."`
  - `"Evaluators unavailable — cannot assess use impact."`
  - `"No reasoning provided."`
  - `"No valid evaluator verdict."`
- Fires (`_cdShow = true`) when:
  - `use_consequence === "context_dependent"` (primary trigger), OR
  - `use_reasoning` is substantive AND `use_consequence` is absent (secondary, for incomplete use_impact data)
- Renders:
  - Label: **"Context Dependency"** (uppercase, amber/ochre)
  - `use_reasoning` div (`cv-cd-reason`) when present and substantive
  - When `use_consequence === "context_dependent"` AND `evaluator_agreement === "1-1-1"`: purple italic split note ("Evaluators split 1-1-1 — no consensus on use impact; answer depends on tenant's specific use.")
  - When `use_consequence === "context_dependent"` without 1-1-1 split: amber italic tag ("Use impact: context-dependent")
- Does NOT render when: no real data (both triggers false), or reasoning is a fallback string.

**Template:** `${contextDepHtml}` inserted into the return template between `${clientImpactHtml}` and `${leaseTextHtml}`.

### style.css — Step 398 CSS block
Added ~36 lines of CSS after the Step 375G `.cv-ci-exposure` block (before Step 342). Classes:
- `.cv-context-dep` — amber/ochre box (background #fffbeb, left-border #d97706)
- `.cv-context-dep-label` — small caps amber label
- `.cv-cd-reason` — body text (0.875rem, dark gray)
- `.cv-cd-consequence` — italic amber tag for non-split context_dependent
- `.cv-cd-split-note` — italic purple note for 1-1-1 split

---

## Relationship to Step 375G (Client Impact)

Step 375G already renders `use_impact.use_reasoning` as "Client Impact" (indigo box) for ALL items that have non-empty reasoning. For items where `use_consequence === "context_dependent"`, the reasoning will appear in BOTH "Client Impact" and "Context Dependency." This is intentional:
- "Client Impact" = why this provision matters in dollar/risk terms
- "Context Dependency" = specifically that the outcome depends on the use profile, plus the evaluator-agreement signal

The 375G block was NOT modified (freeze behavior).

---

## Confirmed: no prohibited changes

- ❌ No `cam/core/` files touched
- ❌ No new model call, prompt, or pipeline stage
- ❌ No hardcoded clause content
- ❌ No strictness/visibility toggle added
- ✅ Label is "Context Dependency" (not "bucket")
- ✅ Source is traceable to Stage 5e `use_impact` (not relabeled)
- ✅ Renders existing data only

---

## How to view it

1. Open the CAM lease analyzer (hard-refresh after git pull — `Ctrl+Shift+R`).
2. Run a **Mode C (Analyze)** job on any lease that has Stage 5e output (any run using `lease_use_impact.py`).
3. Switch to the **Coverage & Gaps** tab.
4. Open a finding card where `use_impact.use_consequence === "context_dependent"`.
5. Immediately below the "Client Impact" indigo box, an amber/ochre **"Context Dependency"** box will appear with the model-authored use_reasoning and (if evaluator_agreement is "1-1-1") a purple italic split note.

**Fallback rendering:** if a run has no `context_dependent` items but has items with `use_reasoning` and no `use_consequence` (incomplete use_impact), the block also fires with the reasoning only.

**No new toggle required** — the block renders whenever real data exists.

---

## Files changed

- `05 Lease Analyzer/static/app.js` — Context Dependency block in `buildItem()`
- `05 Lease Analyzer/static/style.css` — CSS for `.cv-context-dep`, `.cv-context-dep-label`, `.cv-cd-reason`, `.cv-cd-consequence`, `.cv-cd-split-note`

No `cam/core/`, no `summary_generator.py` (synopsis parity deferred per spec — not trivial to add without knowing which rendering path covers Mode C in the PDF).
