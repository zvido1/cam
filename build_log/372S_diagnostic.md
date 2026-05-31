# Diagnostic 372-S — Plain-English scope of the 12 bucket flips

**Date:** 2026-05-31  
**Author:** Claude Code  
**Type:** Read-only characterization over stored 370c artifacts. No code, no reruns.  
**Base SHA:** `edd018e` (372). Status file committed; no other changes.

---

## Per-LP substance table

For each LP: bucket split across 6 runs, the flipping element(s), the verdict each run gave, citations, and a characterization of whether the lease is SILENT, AMBIGUOUS, or PRESENT-BUT-CONTESTED.

---

### LP-03 — Lease Term & Renewal (4 clean / 2 needs_attention)
**Needs-attention runs:** H2, H3  
**Materiality:** high (all runs with use_impact)  
**Flipping element:** `LP-03.expiration_date` — "Expiration date or method to determine it is stated"

| Run | Verdict | Citation | Bucket |
|-----|---------|----------|--------|
| W1 | missing | none | clean |
| H1 | missing | none | clean |
| H2 | **unclear** | none | needs_attention |
| W2 | missing | none | clean |
| W3 | missing | none | clean |
| H3 | **unclear** | none | needs_attention |

**Lease status: SILENT.** The lease states initial term duration and start date but the expiration date is calculated (not stated), and 2/6 runs treat "calculable" as `unclear` rather than `missing`. No citation in any run.  
**Verdict range:** adjacent (`missing`↔`unclear`) — no run says `explicitly_present`.  
**Call type:** BORDERLINE. A reasonable reviewer can read either way: the date can be derived, but is it "stated"?

---

### LP-05 — Permitted Use (5 clean / 1 needs_attention)
**Needs-attention runs:** H3 only  
**Materiality:** high (H3) / medium (others)  
**Flipping elements:** `specific_permitted_use` (unclear↔missing), `prohibited_use_restrictions` (explicitly→implicitly), `co_tenancy_anchor_dependency` (missing↔disputed)

**The mechanism:** H3 flips because `use_impact.gap_impact` changes `favorable`→`adverse` (same coverage_state=missing in most runs; the Stage 5e model decides the missing use clause is favorable for this warehouse tenant in 5/6 runs but adverse in H3). The element-verdict differences are secondary.  
**Lease status: PARTIALLY PRESENT.** Section 4.1 states prohibited uses; specific permitted use (warehouse/distribution) is not separately defined.  
**Call type:** BORDERLINE on most elements; the H3 bucket flip is a Stage 5e outlier (E3-downstream per 372 classification).

---

### LP-09 — Subletting & Assignment (2 clean / 4 needs_attention)
**Needs-attention runs:** W1, H1, W2, H3  
**Materiality:** medium  
**Flipping elements:**

| Element | Question | W1 | H1 | H2 | W2 | W3 | H3 | Citation |
|---|---|---|---|---|---|---|---|---|
| `change_of_control_addressed` | Change of control addressed | disputed | missing | disputed | disputed | missing | missing | none |
| `use_restrictions_bind_transferee` | Use restrictions bind assignee | unclear | unclear | disputed | unclear | covered_in_other_LP | unclear | varies |

**Lease status: SILENT on change-of-control.** Section 15 covers assignment/subletting consent but does not explicitly address corporate change-of-control. Whether that gap is `missing` (no clause) or `disputed` (some evaluators find contextual arguments) is a real legal question.  
**Call type:** BORDERLINE. The `disputed`↔`missing` transition is adjacent. The lease is genuinely silent; evaluators disagree on whether the silence itself constitutes a gap.

---

### LP-13 — Environmental / Hazmat (4 clean / 2 needs_attention)
**Needs-attention runs:** W1, H2  
**Materiality:** medium  
**Flipping element:** `negligence_carveouts` — "Carve-outs for indemnitee's own negligence are addressed"

| Run | Verdict | Citation |
|-----|---------|----------|
| W1 | **unclear** | **none** |
| H1 | explicitly_present | Section 11.2: "to the extent caused by Landlord's negligence or willful misconduct" |
| H2 | **unclear** | **none** |
| W2 | implicitly_present | Sections 11.1 and 11.2: "any act, omission, or negligence of Tenant ... gross neg..." |
| W3 | explicitly_present | Section 11.2: same |
| H3 | explicitly_present | Section 11.2: same |

**Lease status: PRESENT — Section 11.2 contains a negligence carveout.** The language "to the extent caused by Landlord's negligence or willful misconduct" is a standard carve-out for the indemnitee's own fault. It EXISTS in the lease.  
**Call type:** ERRATIC (evaluator miss). 4/6 runs find the carveout; 2/6 say `unclear` with no citation. The two unclear runs did not cite any text. They appear to have missed Section 11.2, not made a different judgment about it.

---

### LP-16 — Parking & Access (1 clean / 5 needs_attention)
**Needs-attention runs:** W1, H1, W2, W3, H3  
**Materiality:** high (W1, W2, W3, H3) / medium (H1)  
**Flipping element:** `parking_cost` — "Parking cost is addressed (included in rent or separately charged)"

| Run | Verdict | Citation |
|-----|---------|----------|
| W1–H1–W2–W3–H3 | unclear | none |
| H2 | **disputed** | **none** |

**Lease status: SILENT.** The lease says tenant gets 10 parking spaces but does not state whether parking is included in rent or separately billed. Whether "no cost stated = included" or "no cost stated = unclear" is a real inference question.  
**Note:** The flip is minor — `unclear`↔`disputed` (adjacent) — and H2 is the *clean* outlier. The "clean" verdict in H2 comes from coverage_state=`partial` (partial_class=`partial_typical`) instead of `review_needed`. The parking-cost element going to `disputed` in H2 (vs `unclear` in all others) is likely what tilts the merge.  
**Call type:** BORDERLINE. Single-step adjacent verdict flip on genuinely silent text.

---

### LP-19 — Utilities (3 clean / 3 needs_attention)
**Needs-attention runs:** W1, W3, H3  
**Materiality:** high (W3, H3) / medium (W1)  
**Flipping elements:**

| Element | Question | W1 | H1 | H2 | W2 | W3 | H3 | Note |
|---|---|---|---|---|---|---|---|---|
| `installation_connection_costs` | Utility installation/connection cost responsibility | unclear | disputed | disputed | disputed | implicitly_present | unclear | W3 cites Section 6.1 |
| `utility_upgrade_costs` | Utility upgrade cost responsibility | missing | missing | missing | disputed | unclear | disputed | no citation |

**Lease status: MOSTLY SILENT.** Section 6.1 addresses separately metered service but doesn't explicitly allocate installation or upgrade costs. W3 infers a signal from Section 6.1; others don't.  
**Call type:** BORDERLINE. `missing`↔`unclear`↔`disputed` transitions; lease is genuinely ambiguous on who pays for upgrades.

---

### LP-20 — Exclusivity Protection (3 clean / 3 needs_attention)
**Needs-attention runs:** H2, W3, H3  
**The mechanism:** This is E3-downstream (Stage 5e). `coverage_state=missing` in all runs. Bucket is clean when `use_impact.materiality=not_applicable` (Stage 5e says exclusivity question doesn't apply to this tenant's warehouse use) — 3 runs (W1, H1, W2). Bucket is needs_attention when `use_impact.materiality=low` (Stage 5e says it does apply, weakly) — 3 runs (H2, W3, H3).  
**What differs:** Stage 5e disagrees run-to-run on whether this warehouse tenant has a stake in exclusivity protection. W1/H1/W2 say the warehouse/distribution use makes exclusivity a non-issue (`not_applicable`). H2/W3/H3 say it applies but only weakly (`low`).  
**Lease status:** Section 24.14 defines competing use (warehousing/distribution) — the clause EXISTS. The question is whether a warehouse tenant cares about exclusivity at all.  
**Call type:** BORDERLINE. Whether exclusivity "applies" to a warehouse tenant is a real use-profile question, not a text-presence question.

---

### LP-22 — SNDA (3 clean / 3 needs_attention) ← **THE REPRESENTATIVE EXAMPLE — see Q4**
**Needs-attention runs:** H2, W3, H3  
**Materiality:** high (H2) / medium (W3, H3)  
**Flipping elements (four, but two are the primary drivers):**

| Element | Question | W1 | H1 | H2 | W2 | W3 | H3 | Key citation |
|---|---|---|---|---|---|---|---|---|
| `landlord_obligation_obtain_snda_existing_lenders` | Landlord obligated to get SNDA from existing lenders | present | present | **disputed** | present | **disputed** | **disputed** | Sect. 19.2 (present) / none (disputed) |
| `non_disturbance_source_is_binding` | Non-disturbance is a binding agreement | present | present | present | present | **disputed** | present | Sect. 19.2 (present) / none (disputed) |
| `subordination_mechanism_self_executing` | Subordination is automatic | missing | **disputed** | missing | missing | missing | missing | no citation |
| `attornment_mechanism_self_executing` | Attornment is automatic | missing | missing | missing | missing | **disputed** | **disputed** | no citation |

**Lease status: PRESENT ON THE KEY ELEMENT.** Section 19.2 says "Landlord shall obtain from each holder of a Superior Interest [an SNDA]." That is the landlord's obligation. In 3/6 runs this is found; in 3/6 it is called `disputed` with no citation — the evaluators could not point to a clause they were disputing. The "disputed" verdict without citation is a flag that the evaluator is generating uncertainty without grounding.

---

### LP-26 — Quiet Enjoyment (1 clean / 5 needs_attention)
**Needs-attention runs:** W1, H1, W2, W3, H3  
**Materiality:** high (W1, W3) / medium (H1, W2, H3)  
**Flipping elements:**

| Element | W1 | H1 | H2 | W2 | W3 | H3 | Citation |
|---|---|---|---|---|---|---|---|
| `constructive_eviction_addressed` | missing | disputed | disputed | unclear | unclear | unclear | none |
| `remedies_for_breach_of_quiet_enjoyment` | unclear | unclear | **covered_in_other_LP** | unclear | covered_in_other_LP | covered_in_other_LP | H2/W3/H3 cross-ref LP-27 Sect. 5.1 |

**Lease status: SILENT ON CONSTRUCTIVE EVICTION; CROSS-COVERED ON REMEDIES.**  
The `remedies` element is interesting: 3 runs find a cross-reference (LP-27 Section 5.1: "in addition to any other remedies available to Tenant at law"), 3 don't. This is a retrieval/cross-LP coverage miss on the remedy side.  
**Call type:** MIXED — constructive eviction is BORDERLINE (lease doesn't address it); remedies are an ERRATIC partial miss (the cross-reference exists but is found only half the time).

---

### LP-28 — Compliance with Laws (2 clean / 4 needs_attention)
**Needs-attention runs:** W1, H2, W3, H3  
**Materiality:** high (W1, H2) / medium (W3, H3)  
**Flipping element:** `grandfathering_pre_existing` — "Grandfathering for pre-existing non-compliant conditions is addressed"

| Run | Verdict | Citation |
|-----|---------|----------|
| W1 | disputed | none |
| H1 | **missing** | none |
| H2 | disputed | none |
| W2 | **missing** | none |
| W3 | disputed | none |
| H3 | disputed | none |

**Lease status: SILENT.** The lease does not have an explicit grandfathering clause for pre-existing conditions. Whether to call that `missing` (no clause at all) or `disputed` (some ambiguity about what compliance-with-laws requires) is a judgment call with no text anchor.  
**Call type:** BORDERLINE. Adjacent `missing`↔`disputed` transition. No run ever finds the element present.

---

### LP-29 — Right of Entry (4 clean / 2 needs_attention)
**Needs-attention runs:** W1, H2  
**Materiality:** medium  
**Flipping element:** `emergency_entry` — "Emergency entry without advance notice is permitted and defined"

| Run | Verdict | Citation |
|-----|---------|----------|
| W1 | **unclear** | **none** |
| H1 | explicitly_present | Section 21.1: "(except in the case of emergency)" |
| H2 | **unclear** | **none** |
| W2 | explicitly_present | Section 21.1: same |
| W3 | explicitly_present | Section 21.1: same |
| H3 | explicitly_present | Section 21.1: same |

**Lease status: PRESENT — Section 21.1 contains a parenthetical emergency entry exception.** The phrase "(except in the case of emergency)" is embedded in the 24-hours-notice sentence.  
**Call type:** ERRATIC. 4/6 runs find it; 2/6 say `unclear` with no citation. The clause exists. The two unclear runs appear to have missed the embedded parenthetical — a classic retrieval miss, not a judgment call.

---

### LP-32 — Environmental Remediation (3 clean / 3 needs_attention)
**Needs-attention runs:** H1, H2, W2  
**Materiality:** medium  
**Flipping elements:**

| Element | W1 | H1 | H2 | W2 | W3 | H3 | Citation |
|---|---|---|---|---|---|---|---|
| `de_minimis_carveout` | **explicitly_present** | disputed | disputed | disputed | **explicitly_present** | **explicitly_present** | W1/W3/H3 cite Section 12.1 |
| `notification_requirement` | disputed | disputed | disputed | unclear | disputed | disputed | none |
| `survival_after_expiration` | disputed | disputed | disputed | unclear | disputed | disputed | none |

**Lease status on de_minimis_carveout: PRESENT.** Section 12.1 says "except for standard cleaning and maintenance materials used in the ordinary course." 3/6 runs find it (W1, W3, H3); 3/6 say `disputed` with no citation. The text exists.  
**On notification and survival: SILENT.** Neither element has a citation in any run.  
**Call type:** ERRATIC on de_minimis_carveout (text present, half the runs miss it); BORDERLINE on notification and survival (genuine silence).

---

## Q1: Is there a pattern?

**Yes — and it has two sub-patterns:**

**Pattern A — Silent/ambiguous lease, boundary-call verdict (7–8 LPs):**  
LP-03, LP-05, LP-09, LP-16, LP-19, LP-26, LP-28, and LP-20 (partial). The lease is genuinely silent on the specific element (no clause exists). Evaluators disagree on whether silence = `missing` or `unclear` or `disputed`. These are adjacent-verdict transitions with no citations. They represent real legal inference instability: is "no clause" a gap (missing) or an ambiguity (unclear/disputed)?

Dominant verdict transition: **`missing` ↔ `unclear`** (5 occurrences) and **`disputed` ↔ `missing`** (4 occurrences).

**Pattern B — Present text overlooked (4 LPs):**  
LP-13 (Section 11.2), LP-22 (Section 19.2), LP-29 (Section 21.1 parenthetical), LP-32 (Section 12.1). The clause EXISTS in the lease. Some runs find it and cite it; other runs say `unclear` or `disputed` with **no citation**. The "disputed without citation" pattern specifically flags an evaluator generating uncertainty without being able to point to the text it's uncertain about.

Dominant verdict transition: **`explicitly_present` ↔ `unclear`/`disputed` (no citation on the disputed side)** — 6+ occurrences across these 4 LPs.

**Are the same evaluators flipping each time?**  
Per-evaluator A/B/C splits are NOT separately persisted at the element-verdict level in the current stored artifacts — only the merged element verdict is stored. The `per_evaluator_lp_verdicts` (LP-level) shows A/B/C for the overall LP, but not for individual elements. So this cannot be answered from stored data alone. That is itself a finding: per-evaluator element-level accountability cannot be audited post-hoc with current persistence.

**Dominant pattern summary:**  
Pattern A (silent-lease boundary call): **~8 LPs**  
Pattern B (present text overlooked): **4 LPs**  
Stage 5e downstream: **1 LP**

---

## Q2: Severity — materiality breakdown

| LP | Materiality (dominant across runs) | Category |
|---|---|---|
| LP-03 | high | HIGH |
| LP-05 | medium (1 run: high) | MEDIUM |
| LP-09 | medium | MEDIUM |
| LP-13 | medium | MEDIUM |
| LP-16 | high (4/6 runs) | HIGH |
| LP-19 | medium–high (mixed) | HIGH/MEDIUM |
| LP-20 | not_applicable↔low (disputed applicability) | LOW / CONTESTED |
| LP-22 | high (H2) / medium (W3, H3) | HIGH |
| LP-26 | high (W1, W3) / medium (others) | HIGH |
| LP-28 | high (W1, H2) / medium (others) | HIGH |
| LP-29 | medium | MEDIUM |
| LP-32 | medium | MEDIUM |

**Count:**
- **HIGH materiality in at least one run:** LP-03, LP-16, LP-22, LP-26, LP-28 = **5 LPs**
- **HIGH/MEDIUM mixed:** LP-19 = **1 LP**
- **MEDIUM:** LP-05, LP-09, LP-13, LP-29, LP-32 = **5 LPs**
- **LOW/CONTESTED:** LP-20 = **1 LP**

**6 of 12 flipping LPs have high materiality in at least some runs.** A lawyer reading a "clean" run on LP-22 (SNDA) or LP-26 (Quiet Enjoyment) or LP-16 (Parking) is being told nothing to act on in a provision that other runs flag as high-consequence.

---

## Q3: Borderline vs. erratic

**Borderline — genuine close call (lease silent or legally ambiguous; both verdicts defensible):**  
LP-03, LP-05, LP-09, LP-16, LP-19, LP-26, LP-28, LP-32 (partially) = **~8 LPs**

These share: no citation on the flipping element in any run; adjacent verdict transitions (missing↔unclear, disputed↔missing); a lease genuinely silent on the specific sub-point. Two competent reviewers reading the same clause could reach either verdict. This is NOT evaluator error — it is genuine legal ambiguity being resolved differently run-to-run.

**Erratic — present text overlooked (clause exists, some runs miss it):**  
LP-13, LP-22, LP-29, LP-32 (partially) = **~4 LPs**

These share: a real clause EXISTS in the lease; some runs cite it and return `explicitly_present`; other runs return `unclear` or `disputed` with **no citation** (they cannot point to what they're uncertain about). The diagnostic signal is the **disputed/unclear verdict without citation**: an evaluator who has actually read the clause and found it contestable would normally cite the contested language. An evaluator who says `disputed` without a citation may simply not have found the clause.

LP-29 is the cleanest example: "(except in the case of emergency)" is in Section 21.1. 4/6 runs find it; 2/6 say `unclear` without citation. The parenthetical is a retrieval miss.

LP-22 is the most consequential: Section 19.2's "Landlord shall obtain" language is explicit. 3/6 runs miss it on one of the two key elements.

**Summary:**  
- Borderline (real ambiguity): ~**8 LPs** — not evaluator error, the text is genuinely silent/ambiguous  
- Erratic (retrieval miss): ~**4 LPs** — the text exists, some runs don't find it  
- The 4 erratic cases are concentrated in Pattern B; most of the 8 borderline cases are Pattern A

---

## Q4: One worked plain-English example

**LP-22 — SNDA (Subordination, Non-Disturbance and Attornment)**

**What the provision is about:**  
If the landlord borrowed money to buy the building, their lender has a mortgage on it. A tenant without an SNDA agreement is at risk: if the landlord defaults and the bank forecloses, the bank could terminate the lease and remove the tenant. The SNDA fixes this: the lender promises the tenant ("non-disturbance") that as long as the tenant pays rent, the lease survives foreclosure. This is a high-stakes provision for any tenant in a mortgaged building.

**What the lease says:**  
Section 19.1 makes the lease subordinate to all existing and future mortgages (standard landlord-favorable language). Section 19.2 says: *"Landlord shall obtain from each holder of a Superior Interest [an SNDA agreement]."* That phrase — "shall obtain" — is a mandatory obligation on the landlord to get the non-disturbance protection for the existing lenders.

**What the lawyer sees on a clean run (W1, H1, W2):**  
The SNDA provision is assessed as `coverage_state = partial`. It appears in the sidebar as a provision with some gaps but not as a priority flag. The lawyer sees: "The lease has SNDA provisions, some elements are partial, nothing urgent here."

**What the lawyer sees on a needs-attention run (H2, W3, H3):**  
The SNDA provision is in the Needs Attention bucket. Coverage_state = `review_needed`, materiality = high (H2) or medium (W3/H3). The lawyer sees: "This needs client attention — SNDA protection is contested or insufficient."

**Why the evaluators split:**  
The critical element is `landlord_obligation_obtain_snda_existing_lenders` — whether Section 19.2's "Landlord shall obtain" creates a binding obligation for existing lenders.

- W1, H1, W2: The evaluator cites Section 19.2 directly and marks it `explicitly_present`. The obligation is there.
- H2, W3, H3: The evaluator marks it `disputed` — **with no citation**. The evaluator cannot point to the text it is disputing.

A second element, `non_disturbance_source_is_binding`, shows the same pattern: W3 marks it `disputed` without citation while all other runs find it `explicitly_present` with the same Section 19.2 quote.

**Is this a real judgment call or a mistake?**  
Probably a **retrieval miss on some runs, combined with a genuine legal tension.**

The legal tension is real: Section 19.2 says "shall obtain" for existing lenders but "commercially reasonable efforts" for future lenders — that distinction matters, and a careful reader might dispute whether the "shall obtain" for existing lenders is as unconditional as it sounds. A judgment call about that distinction would be legitimate.

But a `disputed` verdict **with no citation** is a different thing. When the evaluator says the SNDA obligation is disputed but cannot cite the language being disputed, it looks less like a legal judgment and more like the evaluator did not fully locate Section 19.2. The runs that find the clause cite it consistently and identically ("Landlord shall obtain from each holder of a Superior Interest"). The runs that dispute it offer no counter-text.

**Bottom line for this example:** The split has both components. The legal ambiguity (shall-obtain vs. commercially-reasonable-efforts) is real and a competent reviewer could flag it. But 3/6 runs generating `disputed` without citation, while 3/6 find and cite the same sentence, suggests the evaluator is sometimes not finding the clause rather than reading it and deciding it's contested. The lawyer who gets a "clean" run has no reason to look at LP-22 again. The lawyer who gets a "needs-attention" run will spend time on a provision that another version of the same analysis said was fine.

---

## Key takeaways (characterization, no recommendation)

1. **The 12 flips are not uniform:** approximately 4 are retrieval/miss errors (present text not found); approximately 8 are genuine legal boundary calls (silence/ambiguity, adjacent verdicts). These may warrant different responses.

2. **6 of 12 high-materiality flips** involve provisions where a "clean" answer could meaningfully mislead a lawyer (SNDA, quiet enjoyment, parking rights, environmental, lease term, compliance).

3. **The "disputed without citation" pattern** is a specific signal worth isolating: an evaluator generating a `disputed` verdict that cannot point to the contested text. This appears on LP-13, LP-22, LP-29, LP-32, LP-28.

4. **Per-evaluator element-level accountability is not available** in current stored artifacts. `element_verdicts` stores the merged verdict, not the A/B/C split per element. This means it is impossible to determine from stored data whether the same evaluator (A/B/C) is consistently the one "missing" the clause across runs. That gap should be noted as a separate audit limitation.
