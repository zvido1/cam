# Step 375E-PRE-Q — Status: what stamps LP-16 Parking "High / Risk"? (READ-ONLY trace)
**Date:** 2026-06-03  **Run:** `lease_review_20260604_033046_52adbf` (0604; 030920 for contrast). **NO
production change.** Verdict up front: **LP-16's High/Risk is REASONED (use-aware), NOT mechanism-stamped —
the OPPOSITE of LP-27.**

## 1. "Consequence: High" — SOURCE = a genuine Stage-5e `use_impact` assessment (NOT floor/table/default)
Three candidate sources, checked against code + data:
- **Floor? NO.** `_HIGH_MATERIALITY_LPS = {"LP-27"}` (lease_exposure.py:76). **LP-16 is not in it** — no per-LP
  floor stamp (unlike LP-27).
- **Table (`_classify_materiality`)? It said LOW.** The 0604 assessment carries `materiality: "low"`,
  `partial_class: "partial_typical"`. LP-16's missing labels ("Landlord's right to modify parking area",
  "Visitor and customer parking access") match none of `_HIGH/_MEDIUM_MATERIALITY_ELEMENTS`, state is
  `partial`, and it's not in the floor → the table path returns **low**. So the table did NOT produce "High."
- **Default? NO.** `use_impact` is present and assessed, not the `… or "moderate"` fallback.
- **Stage-5e `use_impact` — YES, this is the source.** LP-16 0604:
  ```json
  {"gap_impact": "adverse", "materiality": "high", "confidence": "assert",
   "evaluator_agreement": "3-0",
   "use_reasoning": "Incomplete parking provisions risk inadequate secured truck and trailer staging
                     areas critical for daily loading and distribution efficiency."}
  ```
  This is a **reasoned, per-tenant assessment**: unanimous (`3-0`), `confidence:"assert"` (not
  `no_evaluators`), `gap_impact:"adverse"`, and use_reasoning **specific to a warehouse/logistics tenant**
  (truck/trailer staging). The card's "Consequence" badge reads exactly this field —
  `app.js:8068: matVal = (lp.use_impact && lp.use_impact.materiality) || lp.lp_confidence`.

**Plain answer:** "High" is a **REASONED per-tenant Stage-5e assessment**, not a table/floor/default stamp.
The card prose about truck/trailer staging **IS** the assessment's `use_reasoning` (reasoned INTO the
consequence) — not narration generated after a table already decided. (Note: the table independently said
*low*; the assessment correctly OVERRODE it.)

## 2. "severe disagreement" — GENUINE on the 0604 screenshot run (tie-break artifact only on 030920)
374P provenance recompute (per-evaluator LP verdict, pessimistic vs optimistic rollup):

| run | A | B | C | derivation | severity_production | severity_if_tie_optimistic | **tie_derived_severe** |
|---|---|---|---|---|---|---|---|
| **0604** | present | present | **missing** | all **unique_plurality** | severe | **severe** | **FALSE (genuine)** |
| 030920 | present | present | missing | C via **pessimistic_tie_break** (3-3 tie) | severe | none | TRUE (artifact) |

- **On 0604 the severe is GENUINE.** Evaluator **C** genuinely rolls to `missing` (its elements: present 2 /
  implicitly_present 1 / **missing 3** — a clean unique plurality, no tie), while **A and B** roll to
  `explicitly_present`. The LP-level `missing` vs `explicitly_present` (distance 5 → severe) is a real 1-vs-2
  evaluator divergence, **not** the 374K tie-break artifact. The element "Parking cost is addressed" shows a
  genuine 2v1 element dispute (C=missing vs A/B=implicitly_present), consistent with C being the pessimistic
  voice.
- **On 030920 it WAS an artifact** (C reached `missing` via a 3-3 pessimistic tie-break;
  `severity_if_tie_optimistic = none`). So the "severe" label's legitimacy is **run-dependent** —
  coverage-verdict variance on the parking-cost element — but on the run in the screenshot (0604) it is real.

## 3. Risk routing — driven by genuine coverage gap + ASSESSED consequence; NOT floor, NOT tie-artifact
0604 LP-16: `coverage_state = partial` (from genuine misses: "modify parking area" [important] missing,
"visitor parking" missing, "parking cost" [important] disputed), `partial_class = partial_typical`,
`use_impact.materiality = "high"`. The coverage action bucket routes **partial + use_impact.materiality=="high"
→ Risk** (the assessed-consequence path; `partial_typical` alone would be Improvement — so the **assessment**,
not the table, is what elevates it). `rpds.hard_flag = True` → PRIORITY REVIEW, genuinely earned here (severe
is genuine + consequence assessed high).

**Would LP-16 still be Risk without the floor and the tie-artifact?** **YES.**
- Floor: N/A (LP-16 not in `_HIGH_MATERIALITY_LPS`) — removing it changes nothing.
- Tie-artifact: on 0604 the severe is **not** an artifact, so there is nothing to remove; and the Risk
  routing comes from `use_impact.materiality=high` on a genuine `partial`, which does not depend on the
  severe/hard_flag at all.
- LP-16 remains Risk on its **genuine basis**: real missing parking-control elements **+** a genuine
  use-aware high-consequence assessment for a logistics tenant.

## One-line verdict
**LP-16 Parking "High / Risk" is REASONED (use-aware), not mechanism-stamped:** Stage-5e genuinely assessed
(3-0, assert) that parking/truck-staging is materially high for THIS warehouse/logistics tenant, the missing
elements are real, and on the 0604 run the "severe" is a genuine evaluator divergence — not a floor, not a
tie-break artifact. (Contrast LP-27: there `use_impact` was absent → the `_HIGH_MATERIALITY_LPS` floor
stamped it.)

## Implication for 375E (does coverage-materiality share the directional table-instead-of-reasoning defect?)
**Not on LP-16 — LP-16 is the positive control that the assessment path works.** Here the reasoned `use_impact`
(high) correctly **overrode** the table's `low` and drove Risk. The coverage-materiality "stamp not reason"
defect manifests **only when Stage-5e produces no assessment** (use_impact absent/defaulted), at which point
the `_HIGH_MATERIALITY_LPS` floor / `… or "moderate"` default substitutes a table value for reasoning (LP-27).
So 375E's principle "consequence must be assessed, not stamped" should target the **fallback path** (floor +
defaulted use_impact), not the assessed path — and a useful guardrail is: **prefer the assessed `use_impact`
over the table whenever a real Stage-5e assessment exists** (LP-16 shows this already happening for routing).

## Caveat (honest)
The same card also reads "Confidence: low · severe disagreement · PRIORITY REVIEW." On 0604 those are
defensible (consequence genuinely assessed high; severe genuine; hard_flag earned). But the **severe label is
run-fragile** — it was a tie artifact on 030920 — so the *disagreement* framing (not the consequence) is the
part that can wobble run-to-run, the same coverage-verdict-variance family as the directional Pass-2 issue.

## Files referenced (read-only)
- `cam/adapters/lease_review/lease_exposure.py:76` (`_HIGH_MATERIALITY_LPS`), `:87-126` (`_classify_materiality`).
- `05 Lease Analyzer/static/app.js:8068` (Consequence badge ← `use_impact.materiality`).
- Data: LP-16 in `lease_review_20260604_033046_52adbf` (and `…030920…`) `coverage_assessment`.

## Decisions Needed
None (diagnosis). Feeds 375E: scope the "assess don't stamp" principle to the **fallback** (floor/default)
path; LP-16 demonstrates the assessed path is already reasoned.
