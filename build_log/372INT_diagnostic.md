# Diagnostic 372-INT — Clause text vs. model interpretation

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only text analysis over stored per-evaluator reasoning. No model calls, no code, no reruns.
**Base SHA:** `655c46d` (372WV).

---

## LP-22 — SNDA / `landlord_obligation_obtain_snda_existing_lenders`

### Verbatim lease clause (in prompt)

> **Section 19.2. Non-Disturbance.** Landlord shall obtain from each holder of a Superior Interest **existing as of the Commencement Date** a subordination, non-disturbance, and attornment agreement ("SNDA Agreement") in a form reasonably acceptable to Tenant, pursuant to which such holder agrees that, provided Tenant is not in default under this Lease beyond applicable notice and cure periods, such holder shall not disturb Tenant's quiet enjoyment and possession of the Demised Premises in the event of any foreclosure or other enforcement of such holder's remedies. Landlord shall use commercially reasonable efforts to obtain similar SNDA Agreements from holders of Superior Interests placed on the Building after the Commencement Date.

Full Section 19 text (19.1 and 19.3) is also in the prompt. Clause is in-context; no reference-only mechanism needed.

### Q1 — Genuinely ambiguous or clear?

**CLEAR-PRESENT on the obligation itself** — "Landlord shall obtain" is mandatory; "each holder of a Superior Interest existing as of the Commencement Date" clearly describes existing lenders.

**GENUINELY-AMBIGUOUS on the element sub-question.** The element label reads: *"Landlord obligated to obtain SNDA from existing lenders **before lease commencement**."* Section 19.2 says "existing **as of** the Commencement Date" (scope qualifier — which lenders) but does NOT state when the obligation must be performed. "Obtain from holders existing as of [date]" is not the same as "obtain [before] commencement." The timing qualifier in the element label is absent from the clause.

Operative words: `"shall obtain from each holder of a Superior Interest existing as of the Commencement Date"` — the obligation exists; the "before" timing is not stated.

### Q2 — Hallucination or genuine judgment?

**Neither hallucination nor attention failure — genuine rubric-strictness variation.**

**B "present" run reasoning (W1):** *"Section 19.2 expressly obligates Landlord to obtain an SNDA from each existing holder as of the Commencement Date. That directly covers the element regarding existing lenders."* — Correct description of the clause; does not notice the "before commencement" timing gap.

**B "missing" run reasoning (W3):** *"Section 19.2 requires Landlord to obtain SNDAs from holders of Superior Interests existing as of the Commencement Date, but it does not expressly require delivery before lease commencement or prior to the Commencement Date. The timing component of this expected element is therefore absent."*

**B "missing" run reasoning (H2):** *"The lease requires Landlord to obtain SNDAs from holders existing as of the Commencement Date, but it does not state that they must be obtained before lease commencement, nor does it represent that they have already been obtained or attached."*

Both "present" and "missing" B runs correctly describe the clause. In "present" runs, B ignores the "before commencement" timing in the element label. In "missing" runs, B applies that timing qualifier strictly and finds it absent from the clause. **Not hallucination — the clause IS correctly described in every run.** The instability is B inconsistently applying the element label's timing sub-requirement.

A and C are perfectly consistent at explicitly_present across all 6 runs. Both reason from "Landlord shall obtain" directly to presence without engaging the timing qualifier.

### Q3 — One model or all three?

**Model-specific: B (GPT) only.** A (6/6 EP) and C (6/6 EP) are self-consistent. B is exactly 50/50 (3 EP / 3 missing). The clause is identical; the element label is identical; only B's attention to the "before commencement" timing qualifier varies run-to-run.

### Q4 — Prompt/rubric issue?

**Yes — element label introduces a timing qualifier the clause does not satisfy literally.** The rubric asks for "before lease commencement"; Section 19.2 says "existing as of the Commencement Date." These are different legal concepts (scope of obligation vs. timing of performance). B is reading the element label more literally than A/C and finding the timing component absent — which is a legally correct observation. The element label's "before" qualifier is the rubric-level cause of B's instability.

---

## LP-32 — Environmental / `de_minimis_carveout`

### Verbatim lease clause (in prompt)

> **Section 12.1. Hazardous Materials Prohibition.** Tenant shall not bring, keep, store, use, or dispose of any Hazardous Materials in or about the Demised Premises or the Building, **except for standard cleaning and maintenance materials used in quantities customary for warehouse operations and stored in compliance with all applicable laws, and diesel fuel in reasonable quantities for Tenant's forklift equipment**, provided such fuel is stored in approved containers in compliance with all fire codes and environmental laws.

Clause is fully in-context in the prompt.

### Q1 — Genuinely ambiguous or clear?

**CLEAR-PRESENT.** The carve-out is explicit: "except for standard cleaning and maintenance materials used in quantities customary for warehouse operations." A warehouse tenant's standard cleaning supplies and forklift diesel are explicitly carved out. A competent lawyer would not call this missing.

Operative words: `"except for standard cleaning and maintenance materials used in quantities customary for warehouse operations"` — this IS a de minimis / customary-use carveout.

### Q2 — Hallucination or genuine judgment?

**A is applying a hyper-literal label-match test in the "missing" runs, not hallucinating.**

**A "present" run reasoning (W1):** *"Section 12.1 explicitly carves out standard cleaning and maintenance materials in customary quantities and diesel fuel in reasonable quantities, which constitutes a de minimis carve-out for ordinary course of business materials. Although implicit_coverage_acceptable is false, the carve-out is explicitly stated in the text."*

**A "missing" run reasoning (H1, H2, W2 — identical in all three):** *"Although Section 12.1 carves out standard cleaning/maintenance materials and diesel fuel, implicit_coverage_acceptable is false and must_be_explicit is false but implicit_coverage_acceptable is explicitly false, meaning implicitly_present is not valid. The carve-out language does not use 'de minimis' or equivalent explicit phrasing, and since implicit coverage is not acceptable, this element cannot..."* [truncated but the logic is clear]

Both runs cite and correctly describe Section 12.1. In "present" runs A reasons functionally: "standard cleaning and maintenance materials... constitutes a de minimis carve-out." In "missing" runs A reasons lexically: "the carve-out language does not use 'de minimis' or equivalent explicit phrasing." 

**This is rubric confusion, not hallucination.** A correctly reads the clause in every run. A's "missing" verdict comes from applying `implicit_coverage_acceptable=false` to conclude that a functional carve-out without the exact term "de minimis" is insufficient. In "present" runs, A recognizes that "explicitly stated" carve-outs using different wording still qualify. The instability is in whether A treats the element label's term ("de minimis") as requiring a literal phrase match.

**B and C are 100% stable at explicitly_present** in all 6 runs. Neither hesitates on the carve-out.

### Q3 — One model or all three?

**Model-specific: A (Sonnet) only.** B and C are self-consistent at EP. A flips between reasoning-by-function (EP) and reasoning-by-literal-label (missing). Three runs each way.

### Q4 — Prompt/rubric issue?

**Yes — element label uses "de minimis" but the clause does not.** The element rubric says *"Carve-out for de minimis quantities of customary business materials."* The clause says *"standard cleaning and maintenance materials used in quantities customary for warehouse operations."* With `implicit_coverage_acceptable=false` in the schema, A sometimes reads this as: "the rubric requires explicit 'de minimis' phrasing; the clause doesn't use that term; therefore implicitly_present is invalid; therefore missing." The rubric label introduces a legal term of art ("de minimis") that the clause satisfies functionally but not lexically. When A's attention lands on the `implicit_coverage_acceptable=false` flag alongside the label mismatch, it flips.

---

## LP-13 — Environmental / `negligence_carveouts`

### Verbatim lease clause (in prompt)

> **Section 11.1. Tenant's Indemnification.** Tenant shall defend, indemnify... arising from: (a) any breach or default by Tenant under this Lease; (b) any act, omission, **or negligence of Tenant** or Tenant's employees, agents, contractors, or invitees; or (c) Tenant's use and occupancy of the Demised Premises.
>
> **Section 11.2. Landlord's Indemnification.** Landlord shall defend, indemnify... arising from: (a) any breach or default by Landlord; (b) **any act, omission, or gross negligence of Landlord**; or (c) the condition of the Common Areas or Building structure **to the extent caused by Landlord's negligence or willful misconduct**.

Both sections are in-context in the prompt.

### Q1 — Genuinely ambiguous or clear?

**GENUINELY-AMBIGUOUS.** The element asks for "carve-outs for the indemnitee's own negligence" — a standard drafting concept where Tenant's indemnity obligation is expressly excepted when the protected party (Landlord) was negligent. Section 11.2 has a one-directional carve-out: Landlord indemnifies Tenant for things caused by Landlord's negligence. Section 11.1 ties Tenant's indemnity to Tenant's acts/negligence — but does NOT include a clause saying "except to the extent caused by Landlord's negligence."

Whether this satisfies "carve-outs for indemnitee's own negligence" is genuinely contestable:
- Yes: the overall scheme carves out each party's own fault from the other's indemnity
- No: there is no express "except for indemnitee's negligence" language in either party's indemnity

Operative words: `"to the extent caused by Landlord's negligence or willful misconduct"` (Section 11.2(c)) — clearly a negligence carve-out in Landlord's indemnity. Section 11.1 has no reciprocal carve-out.

### Q2 — Hallucination or genuine judgment?

**Genuine judgment — all models correctly identify the clause, differ on classification.**

**C "covered_by_default_law" (W1):** *"Lease text addresses negligence limitations only partially in 11.2(c); full carve-out for indemnitee's own negligence is supplied by default law per schema."* — C correctly notes the partial coverage and invokes default-law schema flag.

**C "explicitly_present" (H1, W2, W3, H3):** *"Section 11.2 expressly limits landlord indemnification to the extent caused by landlord's own negligence or willful misconduct."* — C focuses on Section 11.2(c) as explicit.

**C "implicitly_present" (H2):** *"Section 11.2 expressly limits landlord indemnity to its own negligence, satisfying the carve-out element via implicit coverage."* — C calls the same language implicit rather than explicit.

No run contains a misdescription of the clause. The instability is between sub-classes of presence (explicit/implicit/default-law), all of which result in presence-type verdicts. **There is no "missing" verdict from any model in any run — the instability is exclusively in sub-classification, not in whether the carve-out exists.**

**A "explicitly_present" (5/6) and "implicitly_present" (1/6)** — stable, all finding Section 11.2.
**B "implicitly_present" (5/6) and "covered_by_default_law" (1/6)** — stable, consistently treating coverage as functional rather than explicit.

### Q3 — One model or all three?

**Model-specific: C (Grok) is the most unstable** (4 EP / 1 IP / 1 covered_by_default_law). A is mostly stable. B is mostly stable. But the instability is sub-class only — no model produces a "missing" verdict. This is the softest instability in the set: the element IS present in every run; the dispute is whether it's explicit, implicit, or covered by default law.

### Q4 — Prompt/rubric issue?

**Yes — element rubric for a partial, one-directional carve-out.** The element asks for "carve-outs" (plural) "for the indemnitee's own negligence," implying a standard bilateral carve-out. Section 11.2 has a one-directional partial carve-out (Common Areas/Building structure, extent caused by Landlord). The rubric's `default_law_covers` flag appears to be set, which B invokes explicitly in one run. Whether a one-directional partial carve-out counts as "addressing" bilateral negligence carve-outs is the core ambiguity. The rubric definition for "addressed" is under-specified for this partial-coverage scenario.

---

## LP-29 — Right of Entry / `emergency_entry`

### Verbatim lease clause (in prompt)

> **Section 21.1. Landlord's Access.** Landlord and its authorized representatives shall have the right to enter the Demised Premises upon not less than forty-eight (48) hours' prior written notice **(except in the case of emergency)** for the purpose of: (a) inspecting the condition thereof; (b) making repairs, alterations, or improvements to the Building; (c) exhibiting the Demised Premises to prospective purchasers or lenders; or (d) during the last twelve (12) months of the Term, exhibiting the Demised Premises to prospective tenants.

Clause is fully in-context. The parenthetical "(except in the case of emergency)" is embedded mid-sentence.

### Q1 — Genuinely ambiguous or clear?

**CLEAR-PRESENT on permission; GENUINELY-AMBIGUOUS on the element's "AND defined" requirement.**

The element label reads: *"Emergency entry without advance notice is **permitted and defined**."* Section 21.1 plainly PERMITS emergency entry (the parenthetical carves out the notice requirement). But "emergency" is NOT defined anywhere in the provision.

Operative words: `"except in the case of emergency"` — unambiguously permits emergency entry; the term "emergency" is not defined.

### Q2 — Hallucination or genuine judgment?

**B is making a stable, correct, consistent legal observation — not hallucinating.**

**B across all 6 runs (identical reasoning):** *"The text expressly creates an emergency exception to the advance notice requirement, but it does not define what constitutes an emergency. Because the expected element requires emergency entry to be both permitted and defined, full coverage is unclear."* (W1/H1/H2) or *"The provision expressly allows an emergency exception to the advance notice requirement, but it does not define what constitutes an emergency. Because the expected element requires emergency entry to be both permitted and defined, coverage is incomplete."* (W2/W3/H3)

**A across all 6 runs:** *"The provision explicitly carves out emergency situations from the notice requirement, permitting entry without advance notice in such cases. While 'emergency' is not further defined, the exception is clearly stated."* — A acknowledges the undefined term but finds presence.

Both A and B correctly read Section 21.1. A reads the compound element as "permission is sufficient." B reads it as "both permission AND definition required." **This is not within-model instability — B is rock-consistent across 6 runs, as is A.** (Per 372WV, this was classified as cross-model; the WV analysis correctly identified LP-29 as a case where within-model was minimal.)

### Q3 — One model or all three?

**Cross-model disagreement (both stable), not within-model instability.** A is 6/6 EP. B is 6/6 unclear. C varies EP/IP but all find the clause. This is a genuine and consistent interpretive difference about whether a compound element ("permitted AND defined") requires both parts. **No model is halucinating; no model is flipping randomly.**

### Q4 — Prompt/rubric issue?

**Yes — compound element question creates a structural ambiguity.** The element label reads "permitted and defined." "Defined" means something. B applies the compound requirement literally and consistently. A reads "defined" as satisfied by the word "emergency" appearing in the text. The element rubric's compound phrasing directly drives this stable cross-model split: one reading produces "present" (the permission is clear), another produces "unclear" (the definition is absent). The element question is under-specified: does "defined" require a formal definition, or does it merely require the term to appear?

---

## LP-28 — Compliance / `grandfathering_pre_existing`

### Verbatim lease clause (in prompt)

> **Section 4.2. Compliance with Laws.** Tenant shall, at its sole cost and expense, comply with all applicable federal, state, and local laws relating to Tenant's use and occupancy of the Demised Premises. **Landlord shall be responsible for ensuring that the Building structure and base building systems comply with applicable law as of the Commencement Date** and during the Term to the extent not caused by Tenant's use or alterations.

Clause fully in-context in the prompt.

### Q1 — Genuinely ambiguous or clear?

**GENUINELY-AMBIGUOUS.** "Comply with applicable law **as of the Commencement Date**" admits two honest readings:

(a) **Retrospective / pre-existing coverage (C's reading):** Landlord is responsible for ensuring the building was already compliant on the day the lease began — i.e., Landlord bears responsibility for any pre-existing violations that existed before Tenant arrived. This IS grandfathering.

(b) **Forward-looking from commencement (A's reading):** The obligation begins running on the Commencement Date. It doesn't address what happened before; it just says from that date forward, Landlord is responsible for the structure.

Operative words: `"comply with applicable law as of the Commencement Date"` — "as of" is the ambiguous phrase. It can mean "starting at" or "retroactively covering the state of things at."

### Q2 — Hallucination or genuine judgment?

**Genuine legal interpretive disagreement — no hallucination.**

**C "explicitly_present" (W1, H2, W3, H3):** *"The text explicitly makes Landlord responsible for compliance of structure and systems as of the Commencement Date, covering pre-existing conditions."* — C reads "as of" as retrospective.

**C "missing" (H1, W2):** *"The Commencement Date compliance reference does not address grandfathering or pre-existing non-compliant conditions."* — C switches to A's reading.

**A "missing" across all 6 runs (consistent):** *"The Landlord's obligation is framed as ensuring compliance 'as of' but does not address grandfathering, pre-existing non-compliant conditions, or responsibility for pre-existing violations."* — A consistently reads "as of" as forward-looking.

**B "missing" runs:** *"The provision addresses Landlord's compliance responsibility as of the Commencement Date, but it does not address grandfathering, pre-existing non-compliant conditions, or responsibility for pre-existing violations."*

**B "explicitly_present" run (H3):** *"The provision addresses pre-commencement compliance responsibility by requiring Landlord to ensure Building structure and base building systems comply as of the Commencement Date. It does not use the term 'grandfathering,' but it expressly allocates responsibility for commencement-date compliance conditions."*

No model misdescribes the clause. Both "present" and "missing" runs cite Section 4.2 and correctly quote it. The split is a genuine legal interpretation of "as of." **This is the clearest case of authentic interpretive ambiguity in the set.**

### Q3 — One model or all three?

**C is model-specific unstable** (4 EP / 2 missing). A is self-consistent at missing (6/6). B is mostly stable at missing (5/6) with one EP in H3. The instability is in C — which sometimes reads "as of" retrospectively and sometimes forward-looking. A is consistently strict on the absence of explicit grandfathering language.

### Q4 — Prompt/rubric issue?

**Yes — element rubric uses "grandfathering" terminology, clause does not.** The element asks for "grandfathering for pre-existing non-compliant conditions." Section 4.2 says "comply... as of the Commencement Date" — never mentions grandfathering or pre-existing conditions. With `implicit_coverage_acceptable=false` (referenced by A in reasoning), the rubric seems to require explicit grandfathering language. C reads "as of" as functional equivalent; A and B say the functional equivalent isn't sufficient without explicit pre-existing-condition language. Same rubric-vs-function tension as LP-32.

---

## Synthesis

### How many clauses are CLEAR-PRESENT vs GENUINELY-AMBIGUOUS?

| LP/Element | Clause clarity | Specific sub-question clarity |
|---|---|---|
| LP-22 SNDA | CLEAR-PRESENT (obligation exists, mandatory "shall obtain") | GENUINELY-AMBIGUOUS (element label adds "before commencement" timing; clause says "as of" — scope, not timing) |
| LP-32 de_minimis | CLEAR-PRESENT (explicit functional carve-out in Sect. 12.1) | CLEAR-PRESENT (carve-out is explicit; A's "missing" is a label-match error) |
| LP-13 negligence | GENUINELY-AMBIGUOUS (one-directional partial carve-out) | ALL-PRESENCE (no missing verdicts — instability is sub-class only) |
| LP-29 emergency | GENUINELY-AMBIGUOUS (permission clear; "defined" is not) | COMPOUND AMBIGUITY (element label requires both "permitted" AND "defined") |
| LP-28 grandfathering | GENUINELY-AMBIGUOUS ("as of" admits two readings) | GENUINELY-AMBIGUOUS (no explicit "pre-existing conditions" language) |

**Summary: 1 clear-present defect (LP-32), 1 partial-clear-present (LP-22 obligation clear, element sub-question ambiguous), 3 genuinely-ambiguous (LP-13 sub-class, LP-29 compound, LP-28 interpretive).**

### What kind of failure?

| LP/Element | Failure type |
|---|---|
| LP-32 / A | **Rubric confusion** — A reads `implicit_coverage_acceptable=false` + absence of the term "de minimis" as requiring literal phrase match; the functional carve-out is plainly in-view and correctly described, but A sometimes refuses to call it explicitly_present without the exact label phrase |
| LP-22 / B | **Element-label inconsistency** — B correctly describes the clause in every run; in "missing" runs, B notices the element label's "before commencement" timing qualifier and applies it strictly; in "present" runs, B doesn't engage that qualifier. Both readings are legally arguable; neither is hallucination |
| LP-13 / C | **Sub-class noise** — all three models find the clause; C varies between explicit/implicit/default-law. No functional impact on whether protection exists |
| LP-29 / B | **Stable cross-model disagreement** — not within-model instability; B is consistent 6/6 unclear because it reads "permitted AND defined" literally |
| LP-28 / C | **Genuine legal ambiguity** — "as of the Commencement Date" admits two defensible readings; C switches between them |

### Is it hallucination?

**No hallucination observed in any of the five cases.** In every "missing" verdict, the model correctly quotes or describes the clause it is assessing. The failures are:
- (b-style near-miss) LP-32/A: correctly describes the clause but sometimes refuses to accept the functional equivalent as explicit coverage due to literal label-matching
- LP-22/B: correctly describes the clause and gives a legally-defensible reason for "missing" (timing qualifier absent); inconsistent only in whether it notices the timing sub-requirement
- LP-28/C: correctly describes the clause; genuine interpretive ambiguity between "as of" readings

### Is it concentrated in one model or systemic?

- **A (Sonnet):** unstable on LP-32 (rubric confusion with label-matching)
- **B (GPT):** unstable on LP-22 (element-label timing), stable-but-divergent on LP-29 (compound element)
- **C (Grok):** unstable on LP-13 (sub-class), LP-28 (interpretive ambiguity), and LP-05.co_tenancy (372WV)
- No model is unstable across all five; different models have different failure modes on different clause types

### Is there a prompt/rubric fix indicated?

**Yes, on three of the five cases:**
1. **LP-22:** Element label says "before lease commencement"; clause says "existing as of." The timing qualifier in the rubric is the cause. Whether the rubric should say "before" is a product decision, not a model problem.
2. **LP-32:** Element label says "de minimis"; clause says "customary quantities." A's interaction with `implicit_coverage_acceptable=false` plus label-mismatch creates the flip. The rubric should clarify whether named-concept functional equivalents satisfy explicit coverage when the exact phrase is absent.
3. **LP-29:** Element says "permitted AND defined." The compound requirement drives B's stable "unclear." If "defined" is genuinely required, B is right and the bucket flip is a feature, not a bug.

**LP-13 and LP-28 have no clear rubric fix** — LP-13 is sub-class noise (all presence verdicts); LP-28 is genuine legal ambiguity where both readings of "as of" are defensible.
