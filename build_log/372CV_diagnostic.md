# Diagnostic 372-CV — C (Grok) dissent validity: PRELIMINARY CONTAMINATED PEEK

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only over stored 370c runs + 372NDET N=20 data. No model calls, no reruns.
**Base SHA:** `9cf3a72` (372AC).

---

## ⚠️ HARD LABEL — EVERY NUMBER IN THIS FILE

**PRELIMINARY — CONTAMINATED — NOT A DECISION INPUT.**

This is a directional peek at data we know is contaminated (372ID, 372MAP). The clean
version must run post-372a (evaluator identity surfaced) + 372c (long-prompt budget fixed,
truncation reduced). Do not act on any number here. Do not crown any pattern as a finding.

---

## Data sources and contamination map

| Source | C identity | A/B identity | Contamination |
|---|---|---|---|
| 370c headless H1/H2/H3 | C = grok-4.3 (no fallbacks logged for C) | A = Sonnet (no fallbacks for A/C logged); B contaminated H1-LP22/H2-LP09 | H1/H2 specific B contaminations; C appears clean in logs |
| 370c web W1/W2/W3 | Unknown (no server logs) | Unknown | Full contamination — fallback status unknown |
| 372NDET N=20 (LP-03/09/28) | C = grok-4.3 direct call | A = Sonnet direct call; B excluded on LP-09 | Clean short-prompt cells; LP-09 B excluded |

**Summary:** 35 lone-C-dissent cases from 370c runs (headless H-runs partially verifiable;
W-runs fully contaminated for identity). 6 additional from NDET N=20. **All 41 cases labeled
PRELIMINARY — CONTAMINATED.** The W-run cases (19 of 35) must be excluded from any clean
analysis.

---

## Count summary (PRELIMINARY — CONTAMINATED)

| | Count | Notes |
|---|---|---|
| Total lone-C-dissent cases (A==B, C differs) | **35** (370c) + **6** (NDET) = **41** | PRELIMINARY |
| Excluded: W-run cases (identity unverifiable) | **~19** (estimate) | Contaminated |
| Excluded: B contaminated cells (H1/LP-22/B, H2/LP-09/B) | **2** | Contaminated |
| H-run cases partially usable (C identity likely clean) | **~16** (370c) + 6 (NDET) ≈ **22** | PRELIMINARY, C identity unconfirmed pre-372a |
| NDET cases (cleanest data — direct call, short prompt) | **6** | PRELIMINARY |

---

## Four-way classification (PRELIMINARY — CONTAMINATED)

Classification based on: does C cite text that exists in the lease and contains the quoted
words? (mechanical) vs. is the legal interpretation defensible? (interpretive).

| Class | Count (PRELIMINARY) | Notes |
|---|---|---|
| **GROUNDED SPLIT** | **~21–22** | Real text; genuine legal either/or; C not wrong |
| **UNGROUNDED** | **~7** | No cite, or cite=LP-ID with no content, or consequence-free sub-label |
| **GROUNDED CATCH (tentative)** | **~2–3** | C may be more legally precise than A/B |
| **C WRONG** | **0 confirmed** | No clear confirmed cases |

**Grounding check methodology:** For C-cited cases, verified whether (a) the cited section
exists in the full lease text and (b) the quoted text appears verbatim. For C-uncited cases,
verified whether the element is genuinely absent from the tenant text. All classifications
are marked PRELIMINARY.

---

## Examples per category (PRELIMINARY — CONTAMINATED)

### GROUNDED SPLIT (~21–22 cases — the majority)

**Example 1 — LP-28 `grandfathering_pre_existing` (multiple runs):**
Section 4.2: *"Landlord shall be responsible for ensuring that the Building structure and
base building systems comply with applicable law as of the Commencement Date."*
C: `explicitly_present` — *"text places responsibility on landlord for compliance status
existing at commencement, covering pre-existing conditions."*
A/B: `missing` — *"does not address pre-existing non-compliant conditions, grandfathered
conditions, or Landlord's responsibility for pre-existing violations."*
**Both read the same clause correctly. The dispute is whether "comply as of Commencement
Date" retroactively covers pre-existing violations. This is a real legal interpretive
question. C is not wrong; A is not wrong.** (Confirmed across 8 instances in 370c + 5
in NDET — the most consistent lone-C pattern.)

**Example 2 — LP-09 `change_of_control_addressed` (H2, W1, NDET):**
Section 15.2 (confirmed in lease): *"any entity resulting from a merger or consolidation
with Tenant; or (c) any purchaser of all or substantially all of Tenant's assets."*
C: `explicitly_present` — *"Section 15.2 directly addresses change-of-control events via
explicit merger/consolidation/asset-sale language matching synonyms."*
A: `missing` — *"covers mergers and asset sales but does not address a direct or indirect
transfer of controlling ownership interest."*
**C cites real text and makes a defensible legal argument (merger language = CoC coverage).
A makes the opposite defensible argument (stock sale ≠ merger). Neither contradicts the
text.** The legal question (does merger/consolidation cover a pure stock-sale CoC?) is
genuinely contestable.

**Example 3 — LP-22 `non_disturbance_obligation_for_future_lenders` (H3/W3):**
Section 19.2 (confirmed): *"Landlord shall use commercially reasonable efforts to obtain
similar SNDA Agreements from holders of Superior Interests placed on the Building after the
Commencement Date."*
C: `missing` — *"Section 19.2 requires only 'commercially reasonable efforts' for future
lenders, not a firm obligation to obtain SNDAs."*
A/B: `explicitly_present`.
**C correctly identifies that commercially reasonable efforts ≠ absolute obligation.
Whether "efforts obligation" counts as a "non-disturbance obligation for future lenders" is
a genuine either/or. C's stricter reading is legally defensible.** (Also: this is the famous
SNDA tension — Section 19.2 protects existing lenders with a "shall obtain" but only
"commercially reasonable efforts" for future ones. C appears to be catching that distinction.)

### UNGROUNDED (~7 cases — the noise cases)

**Example 1 — LP-05 `co_tenancy_anchor_dependency` (H1/W2/W3):**
C: `covered_in_other_LP`, citing "LP-31" with an **empty quote**.
C reason: *"Element is absent from this LP but cross_LP_coverage lists LP-31."*
**C is mechanically applying the schema's cross_LP_coverage field (LP-31 listed) without
verifying that LP-31 actually contains the element. A/B correctly say missing. C is using
a schema pointer as substantive coverage — this is not grounded in lease text.**

**Example 2 — LP-11 `mortgagee_guarantor_cure_right` (W3):**
C: `covered_in_other_LP`, citing "LP-22" with empty quote.
C reason: *"schema permits covered_in_other_LP when cross-coverage listed LP-22"* AND admits
*"does not contain an express cure-right clause."* — C is acknowledging the absence while
still returning covered_in_other_LP. Self-contradictory and ungrounded.

**Example 3 — LP-13 sub-label flips (multiple):**
C: `explicitly_present`, A/B: `implicitly_present` (or vice versa).
Section 11.2 cited in all cases. **Both EP and IP indicate "present" for coverage purposes.
C oscillates between these labels on the same correctly-found text.** This is the sub-class
erratic behavior confirmed in 372AC. Consequence-free noise.

### GROUNDED CATCH (tentative — ~2–3 cases; most uncertain)

**Example 1 — LP-10 `landlord_contribution` (H3/W1/W3/W4; C=missing, A/B=EP):**
Section 8.3: *"Prior to the Commencement Date, Landlord shall complete the improvements to
the Demised Premises described in Exhibit B at Landlord's sole cost and expense."*
Section 8.4 separately covers Tenant's Alterations (consent required, no contribution).
C: `missing` — *"Section 8.3 addresses only Landlord's pre-commencement work at its own
cost; no contribution or allowance for Tenant's alterations is mentioned."*
A/B: `explicitly_present` — citing Section 8.3 as "Landlord's contribution to tenant
improvements."
**Tentative: C appears to be making a legally precise distinction that Section 8.3 describes
Landlord's Work (pre-commencement buildout per Exhibit B) ≠ a Tenant Improvement (TI)
allowance or Landlord's contribution to Tenant's alterations. Commercial leases distinguish
these. Section 8.3 is Landlord's obligation to build out the space; it is NOT a TI allowance
for Tenant's alterations (governed by Section 8.4, which requires consent and has no
allowance). C may be reading the element's intent more precisely.**
*[INTERPRETIVE — cannot confirm without the full element rubric definition.]*

**Example 2 — LP-22 `non_disturbance_source_is_binding` (W3; C=missing, A/B=EP):**
Section 19.2 (confirmed): Landlord "shall obtain" SNDAs from existing holders.
C (W3): `missing` — *"Section 19.2 creates a future obligation to obtain SNDAs rather than
stating a presently binding agreement from existing lenders."*
A/B: `explicitly_present`.
**Tentative: C distinguishes between "obligation to obtain an SNDA" and "SNDA is a presently
binding agreement." As of lease execution, the SNDAs may not yet exist. If the element asks
whether the non-disturbance source IS (presently) binding, C's reading has merit. However,
C also says EP on this element in other runs (e.g. H2), so this is also within-model variance.
Filed as GROUNDED CATCH tentatively but consistency problem undermines the catch signal.**

### C WRONG (0 confirmed)

No case was found where C's cited text clearly does not exist or C's claim directly
contradicts plain, unambiguous lease text that A/B correctly read. The LP-11 mortgagee case
is close (C claims cross-LP coverage while admitting the clause isn't there) but C is applying
schema logic, not hallucinating text.

---

## Rough directional impression (PRELIMINARY — CONTAMINATED — DO NOT ACT ON)

> *"Preliminary impression only, not a finding, must be re-run clean."*

The dominant pattern (~21/41 cases) is **GROUNDED SPLIT** — C cites real text and makes a
legally defensible reading that A/B don't take. C is not fabricating; it is reading the same
clauses through a stricter interpretive lens. The LP-28 grandfathering pattern (8+ instances
of C finding retrospective coverage that A/B deny) is the most repeated single pattern, and
the legal question is genuinely contestable.

The second pattern (~7 cases) is **UNGROUNDED sub-label noise** — mostly schema-pointer abuse
(claiming cross_LP_coverage from a provision that doesn't have the content) and EP/IP sub-class
flip. This is noise, not legal judgment.

The GROUNDED CATCH cases (~2–3) are tentative and undermined by within-model variance (C says
the opposite in other runs). The directional read doesn't support "C catches things A/B miss
reliably" — the catches are inconsistent.

**No C WRONG cases found.** C does not appear to be affirmatively hallucinating text or
contradicting clear provisions in these cells.

**Bottom line impression (PRELIMINARY):** C's lone dissents are mostly grounded in real text
with a stricter reading lens, not noise. The sub-label flips and schema-pointer cases are the
main noise. The signal-value of C's dissents is highest when C declines to find coverage
that A/B infer — C appears to be the most restrictive reader when coverage depends on
implication rather than explicit statement.

---

## What the clean post-372a/372c version must add

1. **Per-run evaluator identity confirmation** — which model actually answered C. Currently
   assumed grok-4.3 for H-runs but unconfirmed pre-372a. W-runs fully unverifiable.

2. **Exclude truncated A/B verdicts** — any cell where A or B might have been truncated
   (long-prompt LPs ≥10 elements). Post-372c: truncation frequency drops; clean runs
   identifiable.

3. **Include all elements, not just flipping LPs** — this peek only found lone-C cases on
   elements that were already identified as unstable. A clean run should sweep all elements
   to find lone-C dissents including on stable-verdict elements (which may show C catching
   things no one else noticed or vice versa).

4. **Ground-truth the GROUNDED CATCH cases** — LP-10 `landlord_contribution` and LP-22
   `non_disturbance_source_is_binding` need the full element rubric definition to determine
   whether C's strict reading matches what the element is actually asking.

5. **Full-lease text search for quoted text** — the mechanical grounding check here used the
   first 30 chars of C's quote. Full-lease match would catch cases where a short partial quote
   exists in the lease but the full context contradicts C's framing.

6. **N large enough to distinguish consistent from inconsistent catches** — with N=6, a
   single consistent C-catch (like LP-28 grandfathering appearing in 8 runs) is visible; but
   the tentative LP-22 catch is undermined by C saying the opposite in H2. Post-372c with
   clean N=20+, the consistency of each catch pattern can be measured.

---

## Commit scope

Status file only. No probe scripts (analysis used existing stored data).
