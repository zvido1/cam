# Diagnostic 372-AC — Per-evaluator instability contribution (A and C at temp=0)

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Part 1 re-analysis of N=20 NDET data + Part 2 keyed calls (60 calls on LP-32/LP-13).
**Base SHA:** `d20b800` (372V1). Status file + probe scripts only.
**Scope guard:** n=1 contract. Self-agreement rates do NOT generalize. Direction only.

---

## Contamination caveat (front-loaded)

The N=20 NDET data (Part 1) was confirmed clean for the short-prompt cells: LP-03/LP-28
(6 elements each, 0% truncation/fallback in harness), LP-09 (12 elements, B excluded).
**However**, the N=6 production run data includes fallback-substituted samples (372ID:
H1/LP-22/B was gpt-5.4, H2/LP-09/B was gpt-5.4) and web-run samples where fallback status
is unknown. **A and C were not contaminated in the logged headless runs** (no A or C
fallbacks confirmed in H1/H2/H3 logs). This diagnostic measures A/C intrinsic stability
with that caveat intact; 372a/c will make the count reliable when auditing is fixed.

---

## Part 1 — Per-evaluator self-agreement from N=20 NDET data (clean cells)

**Cells:** LP-03 (6 elems, budget=3000), LP-09 (12 elems, 4100), LP-28 (6 elems, 3000).
**Exclusions:** B on LP-09 = 10/20 excluded (reasoning exhaustion / empty output). All A/C
samples were clean (0% truncation/fallback at these prompt sizes).

| Cell | A verdicts | A agree% | B verdicts | B agree% | C verdicts | C agree% |
|---|---|---|---|---|---|---|
| LP-03 `expiration_date` (ambiguous) | unclear×19, EP×1 | **95%** | missing×20 | **100%** (but temp=1) | missing×20 | **100%** |
| LP-09 `change_of_control` (ambiguous) | missing×20 | **100%** | missing×8, EP×2 (10 excl) | 80% (unreliable) | missing×16, EP×4 | **80%** |
| LP-28 `grandfathering` (ambiguous) | missing×20 | **100%** | missing×13, unclear×4, EP×3 | **65%** | EP×10, missing×9, unclear×1 | **50%** |
| **Average** | | **98%** | | ~78%* | | **77%** |

*B's LP-09 average unreliable due to 50% exclusions; LP-03/LP-28 give 83% average for B.

**Fingerprint stability (reasoning-layer):**

| Cell | A fp stable? | B fp stable? | C fp stable? |
|---|---|---|---|
| LP-03 (derive S2.2 expiry) | Yes (True×19) | No (9Y/11N) | Yes (True×20) |
| LP-09 (merger=CoC synonym) | Yes (True×20) | No (5/5) | No (6Y/14N) |
| LP-28 (retrospective reading) | Yes (True×20) | Yes (True×20) | Yes (True×19) |

LP-28 fingerprint result: B and C have STABLE retrospective readings (both read "as of"
retrospectively in nearly all runs) but produce UNSTABLE verdict labels → the M1 pattern
(stable reading, unstable verdict mapping) is confirmed for B AND C.

---

## Part 2 — Clear-present cells (keyed calls, N=15, A and C only)

**Why needed:** All 3 NDET cells are genuinely ambiguous clauses where even a stable evaluator
may reach different defensible verdicts. To separate signal from noise, clear-present cells
(clause plainly exists) are required. At temp=0, a stable evaluator should be ~15/15 on clear text.

**Cells chosen:** LP-32 (8 elems, budget=3000, Section 12.1 explicit carve-out) and LP-13
(6 elems, budget=3000, Section 11.2 explicit negligence limitation). Both confirmed clean
(no truncation expected, no fallback observed).

| Cell | A verdicts (N=15) | A agree% | C verdicts (N=15) | C agree% |
|---|---|---|---|---|
| LP-32 `de_minimis_carveout` (clear-present) | EP×15 | **100%** | EP×15 | **100%** |
| LP-13 `negligence_carveouts` (mostly clear-present) | EP×14, IP×1 | **93%** | EP×8, IP×7 | **53%** |

**LP-32 finding — N=6 undersampling corrected:**
The 372WV N=6 data showed A=50/50 (EP×3/missing×3) on LP-32. At N=15, A is 100% EP — every
sample cites Section 12.1, every sample returns explicitly_present. **The 3 "missing" verdicts
in the N=6 production runs were low-frequency events, not representative of A's central
behavior on this cell.** The 372WV 50/50 was an N=6 undersampling artifact for LP-32/A.

**LP-13 finding — C's sub-class erratic behavior confirmed:**
Section 11.2 states *"the condition of the Common Areas or Building structure to the extent
caused by Landlord's negligence or willful misconduct."* This IS a negligence carve-out. C
finds Section 11.2 and cites it correctly in EVERY run (15/15 cited). Yet C alternates
between calling it `explicitly_present` (8/15) and `implicitly_present` (7/15) — nearly
50/50 on the SAME correctly-found text. A is 93% (14 EP, 1 IP).

C's "IP" reasoning: *"Section 11.2 expressly limits landlord indemnification to the extent
caused by landlord's own negligence, satisfying the carve-out element via implicit coverage."*
C's "EP" reasoning: *"Section 11.2 expressly limits landlord indemnification to the extent of
its own negligence or willful misconduct, satisfying the carve-out element."*

Both are the same clause, same citation, same finding. C cannot consistently decide which
presence sub-class to assign. **This is erratic sub-class labeling, not genuine legal
ambiguity** — both EP and IP indicate "present"; the instability is in the classification
label, not the legal judgment.

---

## World 1 vs World 2 — verdict

**Neither.** The data reveals a three-level stability structure:

| Evaluator | Overall self-agreement | Temp | Mechanism |
|---|---|---|---|
| **A (Sonnet)** | ~95% (N=20); 97% (N=15 clean cells) | 0.0 (honored) | Near-deterministic at temp=0; rare low-frequency rubric confusion on ambiguous rubric labels |
| **B (GPT-5.x)** | ~78-83% (with exclusions) | 1.0 (forced by model) | Structurally stochastic — temp=1 is a model constraint, not a code bug (372V1) |
| **C (Grok)** | ~70-77% (N=20); 53% on clear cell | 0.0 (honored) | Meaningfully unstable at temp=0; M1 mapping instability + sub-class erratic labeling on found clauses |

**World 1** (temp-independent instability, all three equally unstable): **WRONG** — A is clearly
more stable than B and C.

**World 2** (only B is the volatility amplifier): **WRONG** — C is also materially unstable
at temp=0. On LP-13 (clear text), C is 53% self-consistent while A is 93%.

**The actual finding:** A is near-deterministic at temp=0. B is structurally stochastic (temp=1
constraint, documented). **C has intrinsic temp=0 instability that is NOT fully explained by
genuine legal ambiguity.** C's LP-13 sub-class erratic behavior (50/50 EP/IP on correctly-found
text) is particularly notable because the text is clear-present and C finds it every time —
yet cannot stably label it.

---

## Part 3 — Signal vs noise classification per evaluator

**A's wobbles:**
- LP-03 (A: unclear×19/EP×1): GENUINE CLOSE CALL — "Expiration Date" undefined in Section 2.1;
  1 outlier EP out of 20. A's 95% agreement is stable by any practical standard.
- LP-26 (A: missing×3/unclear×2/IP×1, N=6): GENUINE CLOSE CALL — lease genuinely silent on
  constructive eviction. A's reasoning varies between "no CE language" and "LP-27 termination
  functionally covers it." Ambiguous cross-LP coverage, defensible either way.
- LP-32 (A: EP×15 at N=15): NOT ERRATIC — the N=6 50/50 was undersampling. A's central
  behavior is EP on clear text. Low-frequency rubric confusion occurs occasionally.

**A verdict: mostly GENUINE CLOSE CALL or low-frequency noise. A is a reliable temp=0 evaluator.**

**B's wobbles:**
- LP-28 (B: 65% stable despite stable retrospective reading): GENUINE + STRUCTURAL — the
  clause is genuinely ambiguous ("as of" interpretation) and B's temp=1 amplifies the mapping
  instability. Cannot separate genuine from structural with available data.
- LP-22 (B: 50/50 EP/missing, partially gpt-5.4 substitution per 372ID): CONTAMINATED —
  requires decontamination before further classification.

**B verdict: GENUINE + STRUCTURAL (cannot fully separate without decontamination). Known temp=1.**

**C's wobbles:**
- LP-28 (C: 50% EP/missing on stable retrospective reading): GENUINE CLOSE CALL — ambiguous
  clause, both readings defensible. Same M1 pattern as B.
- LP-09 (C: 80% missing, 20% EP — synonym scope): GENUINE CLOSE CALL — whether merger/
  consolidation covers change-of-control is a real legal question.
- LP-13 (C: 53% EP/47% IP on clear text): **ERRATIC** — both EP and IP mean "present"; C
  oscillates between classification labels on correctly-identified clause with no legal
  consequence. This is noise, not signal.
- LP-03 (C: 100% missing): STABLE ✓

**C verdict: MIXED — genuine close calls (LP-28, LP-09) PLUS erratic sub-class noise (LP-13).
C's instability is not entirely signal.**

---

## Exclusion summary

| Cell | A excl | B excl | C excl | Reason |
|---|---|---|---|---|
| LP-03 (N=20) | 0/20 | 0/20 | 0/20 | Short prompt, no issues |
| LP-09 (N=20) | 0/20 | 10/20 | 0/20 | B: reasoning exhaustion |
| LP-28 (N=20) | 0/20 | 0/20 | 0/20 | Short prompt, no issues |
| LP-32 (N=15) | 0/15 | n/a | 0/15 | Short prompt, no issues |
| LP-13 (N=15) | 0/15 | n/a | 0/15 | Short prompt, no issues |

Total excluded: **10 of 110 clean-cell samples** (B on LP-09 only). A and C: 0 exclusions on
all tested short-prompt cells.

---

## Recommendation (phrased as recommendation — NOT a swap/keep decision)

**This is a first read. It is refined after 372a/c (decontamination) and after re-running
with confirmed-clean web-run data.**

1. **A (Sonnet at temp=0) is the most reliable of the three evaluators** on the tested cells.
   Its rare wobbles are on genuinely ambiguous text. No architecture change is needed to
   address A's stability — it is already near-deterministic at temp=0. Monitor for rubric
   confusion on long elements where the label and clause language diverge.

2. **C (Grok at temp=0) warrants a closer look.** C shows sub-class erratic behavior on
   clear-present text (LP-13 EP/IP oscillation) that does not reflect legal ambiguity. At
   77% average self-agreement across the N=20 cells, C is meaningfully less stable than A (98%).
   Whether this justifies redesigning C's role in the three-evaluator structure is a
   separate decision; the data suggests C's vote is less reliably a legal-judgment signal
   than A's, at least on some element types.

3. **B (GPT-5.x at temp=1):** No architecture recommendation from this diagnostic. B's
   structural stochasticity is a model constraint (372V1). The question of whether to treat
   B as a sampling evaluator vs a governance voice is a design decision gated on what
   "three-evaluator governance" is trying to achieve. The data here adds: B's wobbles
   overlap with C's in similar cells (LP-28, LP-09), suggesting the observed B instability
   is not solely the temp=1 artifact — some of it is genuine ambiguity that C (at temp=0)
   also shows.

4. **The LP-13 erratic sub-class finding** (C oscillates EP/IP on clear text) points toward
   a specific fixable rubric issue: the element's definition may not clearly distinguish when
   "explicitly" vs "implicitly" present applies to a one-directional partial carve-out. This
   is separable from the broader evaluator-reliability question and could be a targeted rubric
   clarification rather than a model change.

---

## Commit scope

Part 2 probe script `_372ac_probe.py` + results `_372ac_results.json` (gitignored). Status
file only committed.
