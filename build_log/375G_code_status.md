# Step 375G — Status: Client Impact block (promote use_reasoning; keep evidence visible)
**Date:** 2026-06-03  **Version:** app.js v465→**v466**, style.css v399→**v400**. **Scope:** layout / information
hierarchy + footnote relocation ONLY. **NO change to counts, routing, classifier, or any computed value** —
pure presentation; no new prose; no model call.

## What changed — `05 Lease Analyzer/static/app.js` (`buildItem`, the `coverage`="Key Issues" card)
Built a bounded **CLIENT IMPACT** block by PROMOTING two existing fields and moving them to the TOP of the
card (under the title/badges, ABOVE the element evidence table):
- `use_impact.use_reasoning` (when present) — the tenant-specific reason it matters, rendered prominently
  (`.cv-ci-reason`, 0.92rem, polarity-colored class `cv-ci-reason-{adverse|favorable|neutral}`).
- the existing `exposure_statement` (consequence-of-inaction prose) directly beneath it (`.cv-ci-exposure`).
- Wrapped under a `Client Impact` label only when ≥1 part exists.

Card body order is now: header → escalation → **Client Impact block** → lease text → element evidence table →
notes. **Removed** (no duplication):
- the bottom `⚠ Tenant-specific concern — …` footnote (old `cv-use-impact-note` IIFE, ex-app.js:16660), and
- the below-table `cv-item-stmt` (exposure_statement) — relocated into the block so it shows once.

`style.css`: added `.cv-client-impact` (indigo "insight" accent, prominent — not footnote-sized) +
`.cv-ci-reason{,-favorable,-adverse,-neutral}` + `.cv-ci-exposure`.

## Hard constraints — honored
1. **Promote/organize existing fields ONLY.** The block renders `esc(use_impact.use_reasoning)` and
   `esc(exposure_statement)` verbatim — no synthesized prose, no model call. (The illustrative two-sentence
   text in the brief is layout guidance; the live block shows the raw stored fields.)
2. **No fabrication when use_reasoning is absent (the 72%).** If `use_impact.use_reasoning` is empty the block
   shows ONLY the existing `exposure_statement`; no "for this tenant…" sentence is invented.
3. **Element evidence table + lease text stay VISIBLE.** `leaseTextHtml` and `elementDetailHtml` remain in the
   template, directly below the block — NOT collapsed, NOT behind a new expand. Emphasis re-ordered, mechanism
   not hidden.
4. **No computed value touched.** No edit to any classifier / count / routing / materiality / severity logic.

## Validation (logic simulation of the exact block code against the 0604 run + node --check)
- **LP-16** (`use_reasoning` present): block = `Client Impact` → reason "Incomplete parking provisions risk
  inadequate secured truck and trailer staging areas critical for daily loading and distribution efficiency."
  (class `cv-ci-reason-adverse`) → exposure "Parking rights undefined or unprotected; tenant customers and
  employees may face parking restrictions without recourse." Rendered ABOVE the element table; bottom footnote
  GONE. ✓
- **LP-27** (no `use_reasoning`, one of the 72%): block shows ONLY the generic exposure_statement ("Tenant has
  no right to perform Landlord's obligations… bears the cash-flow and operational risk…") — **no fabricated
  tenant-specific sentence.** ✓
- **LP-08** (covered, no use_reasoning): block shows only the existing exposure_statement; no fabrication. ✓
- **Element table + lease text:** `${leaseTextHtml}` + `${elementDetailHtml}` confirmed still present in the
  template, immediately below `${clientImpactHtml}` — fully visible, not collapsed (verified by reading the
  template). ✓
- **No duplication / footnote gone:** grep — `cv-use-impact-note` and `cv-item-stmt` no longer appear in
  app.js. ✓
- `node --check "05 Lease Analyzer/static/app.js"` → clean. Versions bumped (app.js v466, style.css v400).

### Validation method note
The card renders only inside the live app with a loaded run (backend + result JSON), so visual confirmation
happens on the next loaded run; here I validated **deterministically** by simulating the exact block-building
code against the stored LP-16/LP-27/LP-08 `use_impact` + `exposure_statement` (content correct), confirming
the template order (block above the still-present table) by reading the template, and `node --check`.

## Out of scope (per instruction)
- This is the IA/hierarchy fix only. The **compute gap** (only 28% of LPs have `use_reasoning`) is the
  separate Stage-5e widening (375E) — done deliberately AFTER this so widening doesn't generate more insight
  into a buried slot.
- No "tenant-specific impact: not assessed" fallback wording (that awaits the 375E Stage-5e decision).
- Element evidence intentionally NOT collapsed (still auditing tie-break / directional / per-evaluator
  defects).

## Decisions Needed
None. (Next: 375E Stage-5e `use_impact` coverage widening — now that the block surfaces it prominently.)
