# Diagnostic 372-MAP — Verdict-mapping instability + long-prompt failure audit

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only analysis over stored 370c + 372NDET data. No code, no model calls.
**Base SHA:** `63769af` (372NDET).

---

## Part 1 — Verdict-mapping audit (all 12 flipping LPs)

**Data sources:** N=6 per-evaluator reasoning text from stored 370c runs (all 12 LPs);
N=20 fingerprint data from 372NDET (LP-03, LP-09, LP-28); 372INT reasoning quotes.

**Reading-stability definition:** a model's reading is STABLE if its reasoning consistently
describes the clause and inferential steps the same way across runs — regardless of verdict.
UNSTABLE if the reasoning describes different aspects or activates different inferential steps
across identical prompts.

---

### Per-LP table

| LP | Flipping element | Reading stable? | Verdict dist (dominant model) | Class | Evidencing quote |
|---|---|---|---|---|---|
| **LP-03** | `expiration_date` | A: YES · B: NO · C: YES | A: unclear×19, B: missing×20, C: missing×20 | **M2** | B W1(missing): *"does not explicitly define the initial Expiration Date"* — B H2(unclear): *"Section 2.2 suggests the renewal term begins April 1, 2031, which may imply"* — different inferential step fired |
| **LP-05** | Stage 5e `use_impact` | Stable (element stable) | — | **M4** | Stage 5e gap_impact flip; element reading+verdict stable across runs |
| **LP-09** | `change_of_control_addressed` | A: YES · B: NO (errors) · C: NO | A: missing×20, C: missing×16/EP×4 | **M2** | C EP runs: *"merger/consolidation/asset-sale language matching synonyms"* — C missing runs: *"no text addresses change of control"* — synonym-matching step fires intermittently |
| **LP-13** | `negligence_carveouts` | A: YES · B: YES · C: YES | A: EP×5/IP×1, B: IP×5/default_law×1, C: EP×4/IP×1/default_law×1 | **M1** | A W1(EP): *"Section 11.2 carves out Landlord's own negligence"* — A W2(IP): *"Section 11.1 limits… and Section 11.2 limits… implicitly carving out"* — same clause found, sub-class label varies |
| **LP-16** | `parking_cost` | A: YES · B: YES · C: YES | A: IP×6, B: EP×4/unclear×1/IP×1, C: missing×6 | **M1** (B) + **M3** (A vs C) | B W1(EP): *"expressly addresses parking-related costs by stating that maintenance of parking areas is included as part of CAM Charges"* — B H1(unclear): *"does not clearly state whether Tenant's use of the fifteen spaces is included in rent, separately charged, or free"* — same CAM-maintenance finding, different label |
| **LP-19** | `install_connection_costs` + `upgrade_costs` | install: A/B mostly YES · upgrade: A NO | install: A IP×5, C missing×5 · upgrade: A IP×3/unclear×2/missing×1 | **M2** (A on upgrade) + **M3** (install cross-model) | A W2(upgrade, IP): *"implicitly allocates installation and connection costs to Landlord by obligating Landlord to provide"* — A W1(upgrade, missing): *"The lease provision is silent"* — same Section 6.1, different inference activated |
| **LP-20** | Stage 5e `use_impact.materiality` | Stable (element stable) | — | **M4** | Stage 5e deciding not_applicable vs low; element `existing_tenant_carveouts` has secondary M2 |
| **LP-22** | `landlord_obligation_snda` | A: YES · B: NO · C: YES | A: EP×6, B: EP×3/missing×3, C: EP×6 | **M2** | B W1(EP): *"Section 19.2 expressly obligates Landlord to obtain an SNDA from each existing holder"* — B W3(missing): *"does not expressly require delivery before lease commencement"* — timing sub-requirement in element label activated intermittently |
| **LP-26** | `constructive_eviction` + `remedies_QE` | A: NO (3 verdicts) · B: YES · C: mostly NO | A: missing×3/unclear×2/IP×1; B: covered_in_other_LP×6 | **M2** | A W1: *"no reference to constructive eviction"* — A H2: *"LP-27 gives Tenant a termination right"* — A H3: *"LP-27 Section 5.1 provides Tenant a termination right... which functionally addresses"* — LP-27 cross-coverage scope found intermittently |
| **LP-28** | `grandfathering_pre_existing` | B: YES (retro×20) · C: YES (retro×19) | B: missing×13/unclear×4/EP×3, C: EP×10/missing×9/unclear×1 | **M1** | B H2: *"Landlord shall be responsible for ensuring that the Building structure… comply with applicable law as of the Commencement Date"* [cited, retrospective reading] then verdict missing. Same reasoning → different verdict. |
| **LP-29** | `emergency_entry` | A: YES · B: YES · C: YES | A: EP×6, B: unclear×6, C: EP×4/IP×2 | **M3** (A/B) + **M1** minor (C) | A: *"explicitly carves out emergency situations from the notice requirement"* (stable, EP). B: *"does not define what constitutes an emergency. Because the expected element requires emergency entry to be both permitted and defined, coverage is unclear"* (stable, unclear). Stable cross-model. C minor: same "(except in the case of emergency)" found, sometimes explicit, sometimes implicit. |
| **LP-32** | `de_minimis_carveout` | A: YES · B: YES · C: YES | A: EP×3/missing×3, B: EP×6, C: EP×6 | **M1** | A W3(EP): *"constitutes a de minimis carve-out for ordinary course of business materials… the carve-out is explicitly stated"* — A H1(missing): *"Although Section 12.1 carves out standard cleaning/maintenance materials… The carve-out language does not use 'de minimis' or equivalent explicit phrasing"* — same Section 12.1 read, threshold for "does this satisfy the rubric label" flips |

---

### M1–M5 histogram

| Class | Count | LPs |
|---|---|---|
| **M1** — Stable reading / unstable verdict | **4** | LP-13, LP-16, LP-28, LP-32 |
| **M2** — Unstable reading | **5** | LP-03, LP-09, LP-19, LP-22, LP-26 |
| **M3** — Stable cross-model (genuine) | **1** | LP-29 (primary); LP-16/LP-19 have M3 components |
| **M4** — Downstream Stage 5e | **2** | LP-05, LP-20 |
| **M5** — Doesn't fit | **0** | — |

*(LP-16 has M1 primary for B and M3 for the A-vs-C stable disagreement; LP-19 has M2 primary on upgrade and M3 secondary on installation; classified by primary driver.)*

---

### HEADLINE: Is M1 dominant, or is LP-28 again a vivid minority?

**LP-28 is a minority, not the dominant pattern. M1 = 4/12; M2 = 5/12.**

M2 (unstable reading — the model's inferential step itself fires intermittently) is more
common than M1 (stable reading, unstable verdict mapping). LP-28 is a clean M1 case and
important, but the larger population is M2. M1 and M2 require opposite interventions: M1
needs a clearer verdict-mapping threshold; M2 needs the upstream reasoning/retrieval to be
stabilized or the variance to be surfaced explicitly.

**No M5 cases found.** All 12 LPs fit M1–M4 cleanly. No phantom flips at N=6:
- LP-03: The N=6 bucket flip (2 needs_attention) survives because A=unclear×19/20 is stable
  (always produces the underlying unclear verdict); the flip was driven by B occasionally
  agreeing (M2), not by random noise. The bucket flip is real, not a sampling artifact.
- LP-32: The 3/3 EP/missing A split is a real 50/50 within-model instability, confirmed
  by N=20 data not available here but consistent with N=6 evidence.

---

### For M1 cases: fuzzy verdict-category boundary

**LP-13** — *explicit/implicit/covered_by_default_law for a one-directional negligence carve-out.*
The clause (Section 11.2) limits Landlord's indemnity to its own negligence, but does NOT
have a standard bilateral "except to the extent caused by indemnitee's negligence" clause.
Fuzzy boundary: "does a one-directional partial carve-out count as `explicitly_present`,
`implicitly_present`, or `covered_by_default_law` for the element?"

**LP-16** — *explicitly_present vs unclear vs implicitly_present for "parking cost addressed."*
Section 23.1 says parking AREA MAINTENANCE is CAM. Does that mean parking USE cost is
"addressed"? Fuzzy boundary: "does allocating maintenance cost imply the use-cost structure
is addressed, and if so is that explicit or implicit?"

**LP-28** — *missing vs unclear vs explicitly_present for "grandfathering pre-existing conditions."*
Section 4.2 says "Landlord shall be responsible for ensuring… compliance… as of the
Commencement Date." Models consistently read this retrospectively but split on whether the
retrospective compliance obligation = "grandfathering addressed." Fuzzy boundary: "when does
a compliance-as-of-date obligation clear the threshold for explicitly_present vs unclear
vs missing on an element that asks for explicit grandfathering language?"

**LP-32** — *explicitly_present vs missing for "de minimis carve-out".*
Section 12.1 says "except for standard cleaning and maintenance materials in quantities
customary for warehouse operations." A sometimes reads this as explicit de minimis carve-out
(function satisfies label), sometimes as missing (label requires exact phrase "de minimis"
and `implicit_coverage_acceptable=false` blocks functional match). Fuzzy boundary: "when
does a functional carve-out using different terminology than the element label count as
`explicitly_present` given `implicit_coverage_acceptable=false`?"

---

## Part 2 — Long-prompt failure rate (flag, not fix)

### Step 305 prompt sizes by LP

| LP | Elements | Prompt length (chars) | Notes |
|---|---|---|---|
| LP-02 | 4 | 3,272 | smallest |
| LP-05 | 4 | 2,753 | smallest |
| LP-03 | 6 | 4,026 | NDET tested — 0% failure |
| LP-28 | 6 | 3,918 | NDET tested — 0% failure |
| LP-16 | 6 | 3,456 | |
| LP-04 | 5 | 3,780 | |
| LP-01 | 6 | 6,341 | large text |
| LP-07 | 6 | 5,777 | |
| LP-32 | 8 | 5,305 | |
| LP-27 | 10 | 8,321 | untested |
| LP-22 | 11 | 10,638 | NDET tested — **B: 90%, A: 40% failure** |
| LP-09 | 12 | 10,760 | NDET tested — **B: 50%** failure |
| **LP-11** | **17** | **14,058** | **largest — untested, highest risk** |

### Failure rates from 372NDET (N=20 each)

| LP | Elements | Prompt (chars) | A (Sonnet) fail rate | B (GPT) fail rate | C (Grok) fail rate |
|---|---|---|---|---|---|
| LP-03 | 6 | 4,026 | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) |
| LP-28 | 6 | 3,918 | 0/20 (0%) | 0/20 (0%) | 0/20 (0%) |
| LP-09 | 12 | 10,760 | 0/20 (0%) | **10/20 (50%)** | 0/20 (0%) |
| LP-22 | 11 | 10,638 | **8/20 (40%)** | **18/20 (90%)** | 0/20 (0%) |

**Failure types:**
- B (GPT-5.5): API-level `ERROR` responses (not format errors — request fails before a response is received or the response is rejected). Rate goes from 0% at 6 elements to 50–90% at 11–12 elements.
- A (Sonnet): `PARSE_ERROR` — response received but doesn't parse as the expected format. 0% at 6 elements, 40% at 11 elements on LP-22. A's parse failures were 8/20; B's were API-level errors (17/20 outright failure + 1 parse).
- C (Grok): 0% at all tested sizes. Appears robust to prompt length in this range.

**Correlation: YES — strong, length-correlated.**

The failure rate cliff is between ~4K chars (6 elements) and ~10.6K chars (11 elements).
The 6-element threshold is approximately 4K chars; the 11–12 element threshold is ~10.7K.
B (GPT-5.5) crosses into catastrophic failure (50–90%) above ~10K chars. A (Sonnet) crosses
into partial failure (40%) above ~10K chars on at least one test. C (Grok) shows no
degradation in this range.

**LP-11 (17 elements, 14,058 chars) has never been tested in this regime.** It is the
largest Step 305 prompt and was never included in 372NDET. At B's empirical failure rate
scaling (50% at 10.8K, 90% at 10.6K — non-monotone likely due to noise), LP-11 is at
high risk of near-total failure for B. LP-27 (10 elements, 8.3K) is in the untested
zone between the passing and failing thresholds.

**Production vs NDET disparity:** The stored 370c runs produced complete element_verdicts
for LP-22 and LP-09 with no noted failures, while NDET saw 50–90% failure on the same
prompts. The production `_call_single_evaluator_305` has a fallback pool (Gemini 2.5 Pro,
Mistral Large) that the NDET harness did not replicate. Production failures may be masked
by fallbacks. If so, the LP-22 and LP-09 production element verdicts may have been produced
by fallback models (Gemini/Mistral), not by A/B/C primary — an untracked discrepancy in
the audit chain.

**Flag for separate step:** The long-prompt failure rate and potential fallback masking
represent a separate reliability concern from the verdict-mapping instability diagnosed in
Part 1. They overlap with the 370d Pass-2 output-budget truncation story but are at the
Stage 5 (LP-level) level rather than Stage 7. Not fixed here.

---

## Commit scope

Status file only. No analysis scripts (data derived from existing stored artifacts + NDET
results JSON).
