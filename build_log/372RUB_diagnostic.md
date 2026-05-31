# Diagnostic 372-RUB — Rubric-cause audit across all 12 flipping LPs

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only classification audit. No model calls, no code, no reruns.
**Base SHA:** `93a8ac4` (372INT). Status file only.

---

## HEADLINE FINDING FIRST

**R1 (rubric sub-requirement mismatch) is NOT dominant. R2 (genuine legal ambiguity) is.**

R1: **2/12** — LP-22, LP-32 only.
R2: **6/12** — LP-03, LP-09, LP-16, LP-19, LP-26, LP-28.
R3: **1/12** — LP-13.
R4: **1/12** — LP-29.
R5: **0/12** — no hallucinations confirmed across all 12.
R6: **2/12** — LP-05, LP-20 (bucket flip Stage 5e, not element-level).
R7: **0/12** — no non-fitters, but see HYPOTHESIS-BREAKERS section.

The 372INT analysis of 5 vivid cases found 2 clear R1 and 2 R2 and 1 R3; the full 12 confirm that the R2 (genuine legal ambiguity) pattern is the majority, not R1. Most instability is not about rubric wording — it is about clause text that is genuinely ambiguous or genuinely silent, and evaluators reasoning correctly but reaching different conclusions.

---

## Per-LP classification table

| LP | Primary flipping element | Bucket | Clause operative words | Rubric label words (if R1) | Bucket-flip cause | Evidence quote |
|---|---|---|---|---|---|---|
| **LP-03** | `expiration_date` | missing ↔ unclear | "expire on the Expiration Date" (S2.1); "commencing on April 1, 2031" (S2.2) | "Expiration date or method to determine it is stated" | **R2** | B (H2): *"Section 2.2 suggests the renewal term begins April 1, 2031, which may imply the initial term expires March 31, 2031, but that method is not expressly stated."* |
| **LP-05** | Stage 5e `use_impact.gap_impact` | clean ↔ needs_attention | "solely for the Permitted Use" (S4.1) — undefined term | (Stage 5e) | **R6** | Stage 5e deciding use_impact.gap_impact=favorable vs adverse; element level is stable cross-model A=unclear, B/C=missing |
| **LP-09** | `change_of_control_addressed` | partial ↔ review_needed | "merger or consolidation," "purchaser of all or substantially all assets" (S15.2) — no stock-sale language | "Change of control is addressed" | **R2** | C (EP): *"Section 15.2 directly addresses change-of-control events via explicit merger/consolidation/asset-sale language matching synonyms."* — A/B (missing): *"does not address a direct or indirect transfer of controlling ownership interests"* |
| **LP-13** | `negligence_carveouts` | *(no missing in any run)* | "to the extent caused by Landlord's negligence or willful misconduct" (S11.2) | n/a | **R3** | All runs: all three models return presence verdicts; flip is sub-class only (explicit/implicit/default-law). No present↔missing flip; 372WV confirmed |
| **LP-16** | `parking_cost` | needs_attention ↔ partial | "Landlord shall maintain all parking areas in good condition... as part of CAM Charges" (S23.1) — no use-cost statement | "Parking cost is addressed (included in rent or separately charged)" | **R2** | C (all runs): *"The provision mentions only maintenance via CAM Charges and is silent on whether parking use itself is included in rent or separately charged."* A (all runs): *"implicitly addresses parking cost by folding parking area maintenance into CAM Charges"* |
| **LP-19** | `installation_connection_costs` + `utility_upgrade_costs` | partial ↔ review_needed | "Landlord shall provide separately metered electrical service with sufficient capacity" (S6.1) — no cost allocation | "Responsibility for utility installation/upgrade costs is defined" | **R2** | A (W1, upgrade): *"The lease provision is silent on who bears costs."* A (W2, upgrade): *"implicitly addresses upgrade costs by establishing that Landlord bears responsibility for providing... baseline capacity"* — same clause, different inference across runs |
| **LP-20** | Stage 5e `use_impact.materiality` | clean ↔ needs_attention | "no other tenant... currently operates a warehousing and logistics business" (S24.14) | (Stage 5e) | **R6** | Stage 5e deciding use_impact.materiality=not_applicable vs low; element variant (`existing_tenant_carveouts`) has R2 secondary: B/C each 4/2 on representation vs carve-out distinction |
| **LP-22** | `landlord_obligation_obtain_snda` | partial ↔ review_needed | "Landlord shall obtain from each holder of a Superior Interest **existing as of the Commencement Date**" (S19.2) | "Landlord obligated to obtain SNDA from existing lenders **before lease commencement**" | **R1** | B (W3/H3 missing): *"Section 19.2 requires Landlord to obtain SNDAs from holders existing as of the Commencement Date, but it does not expressly require delivery **before lease commencement**."* B (W1 EP): *"Section 19.2 expressly obligates Landlord to obtain an SNDA from each existing holder as of the Commencement Date."* |
| **LP-26** | `constructive_eviction` + `remedies_for_QE` | partial ↔ review_needed | S18.1 quiet enjoyment covenant; LP-27 S5.1 general termination right — no CE language | "Constructive eviction is acknowledged or addressed" | **R2** | A (all runs): *"Neither Section 18.1 nor LP-27... expressly or implicitly addresses constructive eviction."* B (H2): *"LP-27 gives Tenant a termination right for uncured material Landlord defaults, which would address a material breach of Landlord's quiet enjoyment obligation."* |
| **LP-28** | `grandfathering_pre_existing` | partial ↔ review_needed | "Landlord shall be responsible for ensuring that the Building structure and base building systems comply with applicable law **as of the Commencement Date**" (S4.2) | "Grandfathering for pre-existing non-compliant conditions is addressed" | **R2** | C (EP): *"The text explicitly makes Landlord responsible for compliance... covering pre-existing conditions."* A (missing): *"Landlord's obligation is framed as ensuring compliance 'as of' but does not address grandfathering"* |
| **LP-29** | `emergency_entry` | partial ↔ review_needed | "(except in the case of emergency)" (S21.1 parenthetical) | "Emergency entry without advance notice is **permitted and defined**" | **R4** | B (stable unclear ×6): *"The text expressly creates an emergency exception... but it does not define what constitutes an emergency. Because the expected element requires emergency entry to be both **permitted and defined**, full coverage is unclear."* A stable EP×6. Each model self-consistent; stable cross-model |
| **LP-32** | `de_minimis_carveout` | partial ↔ review_needed | "except for standard cleaning and maintenance materials used in quantities customary for warehouse operations" (S12.1) | "Carve-out for **de minimis** quantities of customary business materials" | **R1** | A (H1/H2/W2 missing): *"The carve-out language does not use 'de minimis' or equivalent explicit phrasing."* A (W1/W3/H3 EP): *"constitutes a de minimis carve-out for ordinary course of business materials... the carve-out is explicitly stated in the text."* |

---

## Bucket histogram

| Bucket | Count | LPs |
|---|---|---|
| **R1** — Rubric sub-requirement mismatch | **2** | LP-22, LP-32 |
| **R2** — Genuine legal ambiguity | **6** | LP-03, LP-09, LP-16, LP-19, LP-26, LP-28 |
| **R3** — Sub-class-only noise | **1** | LP-13 |
| **R4** — Stable cross-model | **1** | LP-29 |
| **R5** — Hallucination / misread | **0** | — |
| **R6** — Downstream (Stage 5e) | **2** | LP-05, LP-20 |
| **R7** — Other / doesn't fit | **0** | — |

R1 is NOT dominant. R2 is dominant at 6/12 (50%). The 372INT sample of 5 vivid cases found 2 R1 (the clearest cases) and 2 R2 and 1 R3, which over-represented R1.

---

## Is R1 dominant? Plain count.

**No.** 2 of 12 flipping LPs trace to a rubric sub-requirement mismatch where a tightened element label would plausibly remove the flip. 6 of 12 trace to genuine legal ambiguity where the clause itself is contestable and two competent readers can reach different verdicts. The rubric-label story from 372INT is real but narrow.

---

## R5 (hallucination) — actively hunted, zero found

372INT found zero hallucinations in 5 cells. This audit confirms zero across all 12 LPs:

In every "missing" or "unclear" verdict across all 12 LPs and all 6 runs, the model correctly describes the clause text it assessed. No model claims text is present that isn't, and no model denies text that is. The closest case is flagged below (LP-05 C W1) but is anomalous within one model and does not constitute a claim of non-existent text.

---

## R7 (doesn't fit) — zero formal R7, but three hypothesis-breaker observations

### 1. LP-05 / C W1: anomalous explicitly_present on empty text

C's verdict in W1 on `specific_permitted_use` is `explicitly_present` with reasoning: *"The text contains near-literal phrasing matching the element's synonyms and must_be_explicit requirement."* But Section 4.1 says only "solely for the Permitted Use" — it contains no specific use description. In all 5 other runs, C correctly says "references 'the Permitted Use' without stating any specific description."

C's W1 reasoning is internally inconsistent with the clause: it claims "near-literal phrasing matching synonyms" but cannot cite a synonym because none is in the clause text. This is not R5 (the text is correctly found) but it IS an anomalous case where C's reasoning appears to confuse its element synonym list with the clause content — possibly matching the element rubric's own synonym list against the phrase "Permitted Use" as though it were a use description. This is the closest observation to model internal confusion (not hallucination, but schema-vs-text conflation) in the full set.

It is a single run of one model and doesn't drive the LP-05 bucket flip (which is Stage 5e driven). Noted as a flag for 372b if it recurs in other data.

### 2. LP-03 / B: reasoning varies with verdict, on identical prompt

B's reasoning changes substantially across runs, and the reasoning change drives the verdict change:
- W1, H1, W2 (verdict: missing): "The initial term expiration is stated only by reference to an undefined 'Expiration Date.'... Section 2.2... does not explicitly define the initial Expiration Date."
- H2, H3 (verdict: unclear): *"Section 2.2 suggests the renewal term begins April 1, 2031, which may imply the initial term expires March 31, 2031, but that method is not expressly stated."*

In the "missing" runs, B doesn't articulate the April 1, 2031 implication. In the "unclear" runs, B explicitly develops the inference and finds the element unclear rather than missing. **The reasoning itself is non-deterministic across identical prompts** — not just the verdict label. B is sometimes noticing a piece of contextual reasoning that changes its conclusion. This is not hallucination (both readings are correct) but it does reintroduce the non-determinism story: the model inconsistently activates an inferential step on the same prompt.

This is classified R2 (the underlying ambiguity is genuine), but the mechanism is *within-model reasoning variance on identical context*, not rubric mismatch and not retrieval failure.

### 3. LP-09 / C: interpretation scope varies across runs (R2 confirmed, but note the pattern)

C says `explicitly_present` in W1/H2 (citing Section 15.2 merger/consolidation as covering change-of-control via synonyms), `missing` in H1/W3/H3 (denying those same synonyms apply), and `missing` (not citing anything) in W2. C's own reasoning in H1: *"No text addresses change of control, transfer of controlling interest, or stock/membership sales as assignments or exceptions."* — which correctly describes the clause. C in W1: *"Section 15.2 addresses change-of-control events via explicit merger/consolidation/asset-sale language matching synonyms."*

The clause text is identical; C's assessment of whether merger/consolidation = change-of-control varies. This is genuine legal ambiguity, but note: C's synonym-matching behavior (is "merger" a synonym for "change of control"?) is inconsistent across runs, and the element's synonym list appears to be doing interpretive work that varies.

---

## R1 cases: would a specific label fix remove the flip?

### LP-22 — proposed fix

**Current label:** "Landlord obligated to obtain SNDA from existing lenders **before lease commencement**"
**Clause text:** "...from each holder of a Superior Interest **existing as of the Commencement Date**"
**The gap:** "before" (timing of performance) vs "as of" (scope of which lenders qualify).
**Proposed label change:** Remove or replace "before lease commencement" — e.g.: *"Landlord obligated to obtain SNDA from each Superior Interest holder existing as of the Commencement Date."* This mirrors the clause wording and removes the timing sub-requirement B fastens onto in the "missing" runs.

**Would it fix the flip?** Plausibly yes — B's stated reason for "missing" in all three missing runs is exclusively the "before commencement" timing qualifier. Removing it removes B's stated basis. Caveat: B's underlying 50/50 non-determinism may surface a different aspect of the element on the next run; there is no guarantee the fix holds under continued API non-determinism.

### LP-32 — proposed fix

**Current label:** "Carve-out for **de minimis** quantities of customary business materials is included"
**Clause text:** "except for standard cleaning and maintenance materials used in quantities **customary for warehouse operations**"
**The gap:** "de minimis" (legal term of art not in the clause) vs "customary quantities" (functional equivalent in the clause).
**Proposed label change:** *"Carve-out for customary quantities of standard operational or maintenance materials is included"* — replacing the "de minimis" legal label with the functional language from the clause.

**Would it fix the flip?** Plausibly yes — A's "missing" reasoning in all three missing runs cites the absence of "de minimis or equivalent explicit phrasing." Matching the label to the clause language removes the literal-match failure condition. Caveat: A's engagement with `implicit_coverage_acceptable=false` might still introduce complications if A reads "customary quantities" as requiring proof of quantity level.

---

## Confirming 372INT findings

The five 372INT cells are confirmed by this audit:
- LP-22: R1 ✓ (confirmed dominant mechanism)
- LP-32: R1 ✓ (confirmed)
- LP-13: R3 ✓ (confirmed — no missing verdicts in any run)
- LP-29: R4 ✓ (confirmed — stable cross-model, not within-model instability)
- LP-28: R2 ✓ (confirmed)

The over-generalization from 372INT was taking LP-22 and LP-32 (the two clearest R1 cases, also the vivid ones) as indicative of the full set. The full set shows R2 is dominant.

---

## Commit

Status file only. No code. No model calls.
