# Step 374V — Status: not-assessed-consequence card copy (conditional) + reasoning un-clip (folds 374U)
**Date:** 2026-06-03  **Version:** v463 → **v464** (see version note below). **Scope:** display/copy only —
NO count / routing / classifier / hard_flag / logic change.

## ⚠️ Version note (root cause: 374U already shipped)
The instruction said "bump v462→v463", written as if 374U had not yet landed. **374U already shipped**
(commit `006331a`, v463) and already did the reasoning un-clip + the v463 bump. So:
- The **reasoning un-clip is already in place** (verified — see below); no re-edit needed.
- 374V adds NEW conditional copy on top of v463, so it needs its own cache-bust → bumped **v463 → v464**.
Following the literal "v463" would have served the new copy under the already-loaded v463 (no cache-bust).

---

## Change 1 — CONDITIONAL lawyer-facing copy on the not-assessed-consequence card
All three relabels are gated on a single flag computed per card:
```js
const _consNotAssessed374V = (_reviewSubtypeOf(a) === 'consequence_not_assessed');
```
**Why this gate (critical anti-blanket guard):** the instruction requires keying off "the same provenance
flag 374Q uses." 374Q does NOT apply the raw `consequenceDefaulted` flag directly — it applies it *within*
its hard_flag/review gate and surfaces it as the `consequence_not_assessed` Needs-Review subtype. The raw
flag is true for ~17 cards per run (most LPs lack `use_impact`); the subtype gate isolates exactly the
LP-06-style card. Measured:
- raw `consequenceDefaulted`: **17 cards** (030920) / **18** (181402) — would be a blanket-apply (forbidden).
- `_reviewSubtypeOf === 'consequence_not_assessed'`: **{LP-06}** on both runs — the intended card only.

Relabels (app.js, all conditional on `_consNotAssessed374V`):
1. **Badge** (`disagSeverityHtml`, ~16605): "derived review signal" → **"Consequence requires attorney judgment"**.
   (Icon/cssClass kept; assessed cards keep "derived review signal".)
2. **Header impact label** (`confidenceBadgeHtml`, ~16377-16382): "Impact Unclear" → **"Impact: attorney
   judgment required"** (dots/cssClass kept; `esc()` applied to the new label).
3. **Severe/derived banner** (`_sevHeaderHtml` severe branch, ~16543): →
   **"⚠ Attorney review recommended: potential exposure was identified; consequence requires your judgment.
   Element-level evidence appears below."** (The non-defaulted severe branch keeps the original
   derived-coverage-signals banner, incl. the 374Q tie-derived cap-note handling.)

Doctrine: CAM did not auto-assess LP-06's consequence (Stage 5e 50%-gate skip; the earlier defaulting is the
separately-contained bug). "Impact Unclear" falsely implies CAM assessed and reached uncertainty. The new
copy states the truth in the lawyer's voice — restraint (constrained assertion) routed to attorney judgment,
not a CAM shortfall. No logic/count/routing touched.

## Change 2 — reasoning un-clip (folds 374U; already present at v463)
Verified app.js:16475 renders the full reasoning: `+ (reasoning ? '<div class="cv-eval-reasoning">' +
esc(reasoning) + '</div>' : '')`; the 300-char `reasoningShort` slice is gone (0 grep hits). Reasoning stays
behind the per-element "2v1 Disagreement" expand toggle; `esc()` escaping preserved.
- **Sibling clip-site grep** (`slice(0, 297)` / `> 300`): no per-evaluator reasoning clip remains. Other
  `slice(0,…)` sites are citation-quote previews (8027/120, 17515/120) and a headline (8185/80) — NOT
  reasoning, out of scope, unchanged.
- **Max reasoning length observed:** **795 chars** (030920, LP-32 role A); 181402 max 480. **None > 1500**, so
  plain full flow — no max-height+scroll needed.

---

## Validation
- **LP-06 card (consequence-not-assessed, 030920 + 181402):** gate = TRUE → badge "Consequence requires
  attorney judgment", impact label "Impact: attorney judgment required", banner = the new attorney-review
  sentence. No "derived review signal" / "Impact Unclear" / old banner on this card.
- **Conditional discriminates (assessed-impact card keeps its real label):** **LP-16 (030920)** — same
  `vd.severity = severe` as LP-06 but `use_impact.materiality = high` (genuinely assessed) → gate = FALSE →
  keeps "derived review signal" badge, its real impact label, and the original derived-coverage-signals
  banner. (Also FALSE: LP-03 moderate/high, LP-20 severe/low — all keep existing labels.) Proves the relabel
  keys off consequence provenance, not severity.
- **Reasoning:** Claude's LP-06 HVAC reasoning renders in full, ends "…addresses this element." (no '…');
  still behind the disagreement expand; escaping intact. Max reasoning 795 (< 1500).
- `node --check "05 Lease Analyzer/static/app.js"` → clean. No count/routing change. `grep reasoningShort` → 0.

## Out of scope (not touched)
- No count / routing / classifier / hard_flag / logic change. Display + copy only.
- No relabel of cards outside the not-assessed-consequence provenance state (gate proven = {LP-06}).
- Disagreement expand gating preserved. Priority Risks (LP-28/32 basis) untouched (parked 374R-Q/374S).
- Citation-quote / headline preview clips left as-is.

## Decisions Needed
None. (Flagging the version reconciliation v463→v464 above for Chat's awareness — 374V's "v463" predated the
374U merge.)
