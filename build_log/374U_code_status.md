# Step 374U — Status: remove 300-char clip on expanded evaluator reasoning (DISPLAY FIX ONLY)
**Date:** 2026-06-03  **Version:** app.js v462 → **v463** (index.html `?v=463`).
**Scope:** display only. NO logic / count / routing / classifier / escaping change.

---

## The change (`05 Lease Analyzer/static/app.js`, ~16454-16469)
The per-evaluator reasoning in the element disagreement panel was hard-clipped at 300 chars:
```js
const reasoning = (evi.reasoning || '').trim();
const reasoningShort = reasoning.length > 300 ? reasoning.slice(0, 297) + '…' : reasoning;
...
+ (reasoningShort ? '<div class="cv-eval-reasoning">' + esc(reasoningShort) + '</div>' : '')
```
Fixed to render the FULL reasoning:
- Removed the `reasoningShort` slice line (kept `const reasoning = (evi.reasoning || '').trim();`).
- Render site now uses `reasoning`: `(reasoning ? '<div class="cv-eval-reasoning">' + esc(reasoning) + '</div>' : '')`.
- **Escaping preserved** — still `esc(reasoning)` (same encoder the short var used); no raw interpolation.
- **Expand gating preserved** — reasoning still lives inside the `panelRow` (`display:none`) revealed only by
  the per-element "2v1 Disagreement" / "N Evaluators" toggle. Not shown by default; only the WITHIN-expand
  clip was removed.

## Sibling clip-site grep
`grep "slice(0, 297)"` and `"> 300"` → the reasoning clip at 16455 was the ONLY per-evaluator reasoning
clip, now removed. Other `slice(0, …)` sites found are NOT evaluator reasoning and are OUT OF SCOPE:
- `app.js:8027` — citation quote preview (120 chars)
- `app.js:8185` — cross-provision headline (80 chars)
- `app.js:17515` — citation quote preview (120 chars)
These are short-preview UI for quotes/headlines, not lawyer-facing reasoning evidence; left unchanged.

## Length guard (max-height + scroll edge case)
Measured every `evaluator_verdicts[].reasoning` across both runs:
- **030920**: max = **795** chars (LP-32, role A).
- **181402**: max = **480** chars (LP-27, role A).
- **OVERALL MAX = 795 chars. NONE > 1500.**

Below the ~1500 threshold → plain full flow is fine; no max-height+scroll applied (per instruction). If a
future run carries multi-paragraph reasoning >~1500, revisit with a scroll container.

## Validation
- **LP-06 HVAC, Claude (role A):** stored reasoning is 325 chars, ends `"…and no other provision in the LP
  text addresses this element."` — confirmed **no ellipsis**, no clip. The expanded panel now renders the
  full sentence (render uses full `esc(reasoning)`; `reasoningShort` removed).
- Grok (153) / GPT (268) reasoning unchanged (were already < 300; still full).
- Reasoning still gated behind the disagreement expand toggle (not shown by default). HTML escaping preserved.
- Max observed reasoning length = 795 (< 1500) → plain full display, no scroll guard needed.
- `node --check "05 Lease Analyzer/static/app.js"` → clean. No count / routing / classifier change.
- `grep reasoningShort` → 0 hits (fully removed).

## Out of scope (not touched)
- No logic/count/routing/classifier change. No 374Q surfaces touched.
- Expand gating NOT removed. Citation-quote / headline preview clips (8027/8185/17515) left as-is.

## Decisions Needed
None.
