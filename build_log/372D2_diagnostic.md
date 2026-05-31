# Diagnostic 372-D2 — Pattern A silence type + Pattern B per-evaluator splits

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only over stored 370c artifacts. No code, no reruns. Status file only.
**Base SHA:** `df650e6` (372S).

---

## Data Point 1 — Pattern A: plain absence vs. consequential silence

Sources: `element_verdicts[].evaluator_verdicts[].reasoning` + `use_impact.use_reasoning`.
Classification basis is ONE-LINE per LP from the stored reasoning text. `(?)` = cannot determine.

| LP | Silence type | One-line basis |
|---|---|---|
| LP-03 Lease Term | **CONSEQUENTIAL SILENCE** | Lease says "expire on the Expiration Date" — a defined term with no definition supplied. Eval-B (all runs): "Section 2.2 suggests the renewal term begins April 1, 2031, which may imply the initial term expires March 31, 2031, but that method is not expressly stated." The date is derivable from context but not stated; some evaluators apply a must-be-explicit rubric (→ missing), others allow the inference (→ unclear). |
| LP-05 Permitted Use | **CONSEQUENTIAL SILENCE** | Section 4.1 says "Permitted Use" but does not define it. use_impact.use_reasoning (most runs): "absence of a permitted-use clause... preventing landlord from restricting the tenant's listed warehouse activities." Evaluators explicitly flag the legal consequence of the undefined term — landlord's restriction power is limited. |
| LP-09 Subletting (change_of_control) | **CONSEQUENTIAL SILENCE** | Section 15.2 addresses affiliates/mergers/asset sales but not pure stock sale / change of controlling ownership interest. Eval-A (all runs): "covers mergers and asset sales but does not address a direct or indirect transfer of controlling ownership interest." Eval-C reads merger/consolidation as covering change-of-control; A and B say it doesn't reach stock sale. Consequence: whether a corporate restructuring triggers landlord consent rights is a legal question. |
| LP-16 Parking cost | **CONSEQUENTIAL SILENCE** | Lease allocates 10 spaces, CAM Charges cover parking maintenance, but no separate parking fee is stated. Eval-A: "the provision implicitly addresses parking cost by folding parking area maintenance into CAM Charges, suggesting parking use itself is included without a separate charge." Eval-C: "silent on whether parking use itself is included in rent or separately charged." Consequence: unexpected separate parking charge vs. included. |
| LP-19 Utilities (installation_connection) | **CONSEQUENTIAL SILENCE** | Section 6.1 requires Landlord to provide separately metered electrical service but does not state who pays hook-up/connection costs. Eval-B: "functionally allocates utility service setup responsibilities: Tenant must arrange and pay for utilities." Eval-A: "may implicitly cover initial installation, but does not explicitly... address who bears the cost." Consequence: allocation of infrastructure cost on a warehouse with high electrical demand. |
| LP-19 Utilities (upgrade_costs) | **PLAIN ABSENCE** | No text in any evaluated provision addresses future utility upgrade or increased capacity costs. All three evaluators across all runs: "The lease specifies Landlord's obligation to provide baseline electrical capacity, but it does not allocate costs for upgrades, increased capacity, panel upgrades, or other utility improvements beyond the initial provision" (no citation, all agree on absence). No legal machinery invoked — the gap is complete. |
| LP-26 Quiet Enjoyment (constructive_eviction) | **CONSEQUENTIAL SILENCE** | Lease has a quiet enjoyment covenant (Section 18.1) and a termination remedy (LP-27 Section 5.1) but does not mention constructive eviction. Eval-B (H2): "LP-27 gives Tenant a termination right for uncured material Landlord defaults, which would address a material breach of Landlord's quiet enjoyment obligation. This is cross-provisioned." Constructive eviction is a common-law doctrine that attaches to quiet enjoyment covenants; whether LP-27's remedy satisfies or displaces it is a legal question evaluators split on. |
| LP-28 Compliance (grandfathering) | **CONSEQUENTIAL SILENCE** | Section 4.2 obligates Landlord to ensure compliance "as of" the Commencement Date. Eval-C (W1, H2, W3, H3): "explicitly makes Landlord responsible for compliance of structure and systems as of the Commencement Date, covering pre-existing conditions." Eval-A: "Landlord's obligation is framed as ensuring compliance 'as of' but does not address grandfathering, pre-existing non-compliant conditions, or responsibility for pre-existing violations." Consequence: who bears cost of violations found post-commencement. |

**Count:**
| Class | LPs |
|---|---|
| CONSEQUENTIAL SILENCE | **7** (LP-03, LP-05, LP-09, LP-16, LP-19[install], LP-26, LP-28) |
| PLAIN ABSENCE | **1** (LP-19[upgrade_costs] — the one sub-element) |
| Indeterminate | 0 |

LP-19 straddles both: one flipping element (installation_connection_costs) is consequential silence; the other (utility_upgrade_costs) is plain absence. No LP is purely plain absence.

---

## Data Point 2 — Pattern B: per-evaluator A/B/C splits

Per run/element where the merged verdict was disputed/unclear/missing on the flipping element. "Grounded" = cited a section_ref or quote in that evaluator's individual record. "Ungrounded" = no citation in that evaluator's individual record.

**Note on LP-09 and LP-28 (Pattern A disputed):** these were included because the merged verdict appears "disputed/missing" without a merged citation. However, the individual evaluator reasoning text for A and B on BOTH these LPs DOES reference the relevant section (Section 15.2 for LP-09; Section 4.2 for LP-28) — they found and read the clause and judged it insufficient. The citation field is empty because their verdict is "missing" (convention: no citation on a negative finding). These are INTERPRETATION SPLITS over scope, not retrieval misses. They are separated below.

---

### Pattern B (LP-13, LP-22, LP-29, LP-32) — clause exists, evaluator-level splits

| LP / Element | Run | Merged verdict | Grounded evaluators | Ungrounded evaluators | Lone dissent? |
|---|---|---|---|---|---|
| LP-13 `negligence_carveouts` | W1 | unclear | A: explicitly_present (S11.2), B: implicitly_present (S11.1+11.2) | **C: covered_by_default_law (no section cite)** | **YES — C lone** |
| LP-13 `negligence_carveouts` | H2 | unclear | A: explicitly_present (S11.2), B: covered_by_default_law (cites Default law + Ss 11.1/11.2), C: implicitly_present (11.2) | none | no (all grounded) |
| LP-22 `landlord_obligation_obtain_snda` | H2 | disputed | A: explicitly_present (S19.2), C: explicitly_present (S19.2), B: missing (cites S19.2) | none | no (all grounded; B found clause but ruled missing) |
| LP-22 `landlord_obligation_obtain_snda` | W3 | disputed | A: explicitly_present (S19.2), C: explicitly_present (19.2) | **B: missing (no citation)** | **YES — B lone** |
| LP-22 `landlord_obligation_obtain_snda` | H3 | disputed | A: explicitly_present (S19.2), C: explicitly_present (19.2) | **B: missing (no citation)** | **YES — B lone** |
| LP-22 `non_disturbance_source_is_binding` | W3 | disputed | A: explicitly_present (S19.2), B: explicitly_present (S19.2) | **C: missing (no citation)** | **YES — C lone** |
| LP-29 `emergency_entry` | W1 | unclear | A: explicitly_present (S21.1), C: implicitly_present (S21.1), **B: unclear (cites S21.1)** | none | no (all grounded; B found clause but returned unclear) |
| LP-29 `emergency_entry` | H2 | unclear | A: explicitly_present (S21.1), C: implicitly_present (S21.1), **B: unclear (cites S21.1)** | none | no (all grounded; B found clause but returned unclear) |
| LP-32 `de_minimis_carveout` | H1 | disputed | C: explicitly_present (S12.1), B: explicitly_present (S12.1), **A: missing (cites S12.1)** | none | no (all grounded; A found clause but ruled missing) |
| LP-32 `de_minimis_carveout` | H2 | disputed | C: explicitly_present (S12.1), B: explicitly_present (S12.1), **A: missing (cites S12.1)** | none | no (all grounded; A found clause but ruled missing) |
| LP-32 `de_minimis_carveout` | W2 | disputed | C: explicitly_present (S12.1), B: explicitly_present (S12.1), **A: missing (cites S12.1)** | none | no (all grounded; A found clause but ruled missing) |

**Pattern B aggregation:**

| Metric | Count |
|---|---|
| Run/element instances inspected (Pattern B, merged disputed/unclear) | 11 |
| Instances with a truly ungrounded (no-citation) evaluator | **4** |
| — Lone dissent (1 ungrounded, 2 grounded) | **4** |
| — Multi-ungrounded (2+ no citation) | **0** |
| Instances where merged was disputed but ALL evaluators cited the clause | **7** |

**Which evaluator is ungrounded in Pattern B:**

| Evaluator | Ungrounded (no cite) | Grounded |
|---|---|---|
| A (claude-sonnet-4-6) | 0 | 4 (found clause every time; verdict varies) |
| B (gpt-5.5) | **2** (LP-22 W3, LP-22 H3 — misses Section 19.2) | 9 |
| C (grok-4.3) | **2** (LP-13 W1 — uses default-law; LP-22 W3 non-disturbance) | 8 |

**Clarifications on non-ungrounded but contested verdicts (Pattern B):**
- **LP-22 H2:** B cites Section 19.2 but returns `missing` — B read the SNDA obligation and judged it insufficient, not a retrieval miss.
- **LP-29 W1/H2:** B cites Section 21.1 but returns `unclear` — B found the emergency parenthetical but judged it unclear. Not a retrieval miss.
- **LP-32 H1/H2/W2:** A cites Section 12.1 but returns `missing` — A found the de minimis carveout and judged it insufficient. Not a retrieval miss.

---

### Pattern A disputed (LP-09, LP-28) — interpretation splits, NOT retrieval misses

These appear as "ungrounded" by the citation-field criterion but are actually grounded in the text (evaluators reference the relevant section in their reasoning even when the citation field is empty because the verdict is "missing").

| LP / Element | Run | Merged | Eval-C | Eval-A | Eval-B | Type |
|---|---|---|---|---|---|---|
| LP-09 `change_of_control` | W1 | disputed | EP (cites S15.2) | missing (references S15.2 in reasoning) | missing (references S15.2 in reasoning) | Interpretation split: C reads CoC as covered by merger/consolidation language; A+B say stock sale not addressed |
| LP-09 `change_of_control` | H1 | missing | missing (refs S15.2) | missing (refs S15.2) | missing (refs S15.2) | All three agree |
| LP-09 `change_of_control` | H2 | disputed | EP (cites S15.2) | missing (refs S15.2) | missing (refs S15.2) | Interpretation split |
| LP-09 `change_of_control` | W2 | disputed | missing (refs S15.2) | missing (refs S15.2) | EP (cites S15.2) | Interpretation split; this run B finds it, A+C don't |
| LP-09 `change_of_control` | W3/H3 | missing | missing | missing | missing | All three agree |
| LP-28 `grandfathering` | W1/H2/W3 | disputed | EP (cites S4.2) | missing (refs S4.2) | missing (refs S4.2) | Interpretation split: C reads "as of Commencement Date" as grandfathering; A+B say it doesn't address pre-existing conditions |
| LP-28 `grandfathering` | H1 | missing | missing | missing | missing | All three agree |
| LP-28 `grandfathering` | W2 | missing | missing (B cites S4.2 for missing) | missing | missing | B finds S4.2 but still says missing |
| LP-28 `grandfathering` | H3 | disputed | EP (cites S4.2) | missing (refs S4.2) | EP (cites S4.2) | A lone dissenter; B+C find and cite coverage |

**LP-09/LP-28 pattern:** The same clause (S15.2 / S4.2) is read and judged differently per evaluator — this is an interpretation split, not a citation miss. Evaluator-C most often finds coverage; Evaluators A and B most often say the scope doesn't reach the specific element. In LP-09 W2 and LP-28 H3, B finds coverage; in all other runs, C is the sole finder.

---

## Summary counts

**Data Point 1:**
- CONSEQUENTIAL SILENCE: **7** LPs (all but one sub-element of LP-19)
- PLAIN ABSENCE: **1** element (LP-19 utility_upgrade_costs)
- Indeterminate: **0**

**Data Point 2 (Pattern B — true ungrounded dissents):**
- Lone dissent (1 ungrounded, 2 found clause): **4 instances**
- Multi-ungrounded (2+ missed clause): **0 instances**
- Most ungrounded evaluator in Pattern B: **B** (LP-22 W3/H3, misses S19.2) and **C** (LP-13 W1 default-law; LP-22 W3 non-disturbance) — tied at 2 each; **A is never ungrounded in Pattern B**

**Data Point 2 (Pattern A disputed — interpretation splits):**
- C most often finds coverage alone (LP-09 W1/H2, LP-28 W1/H2/W3)
- A never independently finds coverage on these elements
- Not counted as "ungrounded" because evaluators reference the relevant section in reasoning text despite no element-level citation

---

## Audit gap noted (no interpretation)

`element_verdicts[].evaluator_verdicts[].reasoning` is persisted and contains per-evaluator referenced sections. The merged `element_verdicts[].citation` is NULL when evaluators disagree — which suppresses the cited text from the merged record even when all evaluators found the section. This made the 372S Pattern B characterization ("disputed without citation") accurate at the merged level but misleading at the evaluator level: LP-29 and LP-32 have all-evaluators-found-the-clause cases that look like retrieval misses from the merged record.
