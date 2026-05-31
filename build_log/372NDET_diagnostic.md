# Diagnostic 372-NDET — Separate genuine ambiguity from reasoning non-determinism (N=20)

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Diagnostic / build-decision gate. 240 keyed calls. No code change, no full pipeline.
**Base SHA:** `d41164c` (372RUB). Status file + harness script only.

---

## SCOPE GUARD (verbatim)

n=1 contract, a few cells. The variance RATES do NOT generalize and must never be cited
as a CAM metric or enter the patent record. What this gates: whether the R2 "genuine
ambiguity" cases are (mostly) genuine — stable, reasoned disagreement worth surfacing —
or are partly reasoning-non-determinism that should be stabilized. Direction only, not
magnitude.

---

## Method

Production prompt (`_build_user_prompt` from `lease_coverage_305.py`) built identically
to how the pipeline builds it: `expected_elements_305` from `get_all_issue_areas()`,
`tenant_text` and `negative_space_signals` from stored H2 run, `cross_lp_texts` from
H2's coverage_assessment. Temperature = 0.0 (production). N=20 per (cell, model).
240 total calls.

**Fingerprint flags (defined before running):**
- LP-03: `derive_from_s22` — did reasoning derive the initial-term expiry from the
  Section 2.2 renewal-start date (April 1, 2031)?
- LP-09: `merger_covers_coc` — did reasoning treat merger/consolidation/asset-sale
  language as synonymous with or satisfying "change of control"?
- LP-28: `retrospective_reading` — did reasoning read "as of the Commencement Date" as
  retrospectively covering pre-existing non-compliant conditions?
- LP-22: `timing_before_commencement` — did reasoning engage the "before commencement"
  timing sub-requirement in the element label?

**Data quality note:** LP-22 (11-element, ~10.6K char prompt) had heavy API errors —
B returned 17/20 ERROR, A returned 8/20 PARSE_ERROR. LP-09 (12-element, ~10.8K char) had
B returning 10/20 ERROR. The longer prompts hit a reliability wall on B. Results for
LP-22/B and LP-09/B are NOT usable; cells are reported with this caveat. LP-03 and LP-28
(shorter prompts, 4K chars) had clean runs.

---

## Per-cell N=20 results

### LP-03 — `expiration_date` (R2 breaker: B's S2.2 inference intermittent)

| Model | Verdicts (N=20) | Fingerprint `derive_from_s22` | Verdict tracks FP? |
|---|---|---|---|
| A (Sonnet) | unclear×19, EP×1 | True×19, False×1 | **Yes** (19/20 derive→unclear; 1/20 no-derive→EP — inverted but single outlier) |
| B (GPT) | **missing×20** | True×9, False×11 | **No** — both when-True and when-False → missing |
| C (Grok) | missing×20 | True×20 | No — C always derives but always returns missing |

**Analysis:**
- **A**: Stable and consistent — derives the S2.2 implication, returns `unclear` (the
  S2.2 inference is "a method exists but isn't stated") in 19/20 runs. Effectively
  self-consistent; the 1 EP outlier is a minor wobble.
- **B**: **REASONING NON-DETERMINISM** — B sometimes notices the S2.2 inference (9×)
  and sometimes doesn't (11×), yet returns `missing` either way. The reasoning step fires
  intermittently but doesn't actually change B's verdict. The N=6 "unclear↔missing" flip
  in stored runs was driven by B accidentally crossing to `unclear` in H2/H3 — at N=20
  B's stable verdict is `missing` (20/20). The fingerprint doesn't predict the verdict
  because both reasoning paths end at missing.
- **C**: Stable and consistent — always derives S2.2, always says missing (the datum is
  inferrable but C applies `must_be_explicit=true` strictly).

**Classification: MIXED.** A shows genuine reading-level stability (derives → unclear).
B shows reasoning non-determinism but the verdict is accidentally stable at N=20. The N=6
"unclear" verdicts from B were low-frequency events that fell outside this N=20 window.

---

### LP-09 — `change_of_control_addressed` (R2 breaker: C's synonym wobble)

| Model | Verdicts (N=20) | Fingerprint `merger_covers_coc` | Verdict tracks FP? |
|---|---|---|---|
| A (Sonnet) | missing×20 | True×20 | **No** — A consistently treats merger as covering CoC but returns missing anyway (applies implicit_coverage_acceptable=false override) |
| B (GPT) | **⚠ ERROR×10, EP×2, missing×8** | True×5, False×5 (usable 10 only) | Unusable (50% errors) |
| C (Grok) | missing×16, EP×4 | True×6, False×14 | **Partially** — when True: EP×3 (50%), missing×3 (50%); when False: mostly missing |

**Analysis:**
- **A**: **STABLE REASONING, STABLE VERDICT** — A consistently engages the merger/CoC
  synonym path (True×20) but overrides to `missing` via `implicit_coverage_acceptable=false`.
  A's "missing" is not a retrieval failure — it's a deliberate schema-rule application.
  A is NOT non-deterministic; the 372WV "missing×6" was accurate.
- **B**: Unusable data (50% API errors on the long prompt). No conclusion possible for B.
- **C**: **REASONING NON-DETERMINISM** — C's `merger_covers_coc` flag fires only 6/20
  times (30%). When it fires, EP is 3/6 (50%); when it doesn't, EP is 1/14 (7%). The
  fingerprint partially predicts the verdict but weakly. C inconsistently activates the
  synonym-matching step, and when it does, it still only converts to EP about half the time.

**Classification: REASONING NON-DETERMINISM (C); stable schema-override (A); B unusable.**

---

### LP-28 — `grandfathering_pre_existing` (R2 control: "as of" genuine ambiguity)

| Model | Verdicts (N=20) | Fingerprint `retrospective_reading` | Verdict tracks FP? |
|---|---|---|---|
| A (Sonnet) | missing×20 | True×20 | **No** — A consistently reads "as of" retrospectively but returns missing; schema override |
| B (GPT) | missing×13, unclear×4, EP×3 | True×20 | **No** — B always reads retrospectively but verdict varies (missing 65%, unclear 20%, EP 15%) |
| C (Grok) | EP×10, missing×9, unclear×1 | True×19, False×1 | **Partially** — when True (19): EP 47%, missing 47%, unclear 5%; when False (1): EP |

**Analysis:**
- **A**: Unexpected finding — A reads "as of" retrospectively in ALL 20 runs (True×20),
  yet returns `missing` every time. A's consistent reasoning is "I see the retrospective
  implication but it's not explicitly framed as grandfathering." This is NOT ambiguity
  producing variance — A is internally consistent, applying a schema rule that requires
  explicit grandfathering language even when the implication is present.
- **B**: **Pure verdict non-determinism** — B reads "as of" retrospectively in 100% of
  runs, yet its verdict scatters: missing×13, unclear×4, EP×3. The reasoning fingerprint
  is completely stable (always retrospective) but the verdict is unstable. This is NOT
  genuine legal ambiguity — it is B failing to consistently apply whatever threshold
  converts "retrospective reading" to a verdict.
- **C**: The retrospective reading fires in 19/20 runs, but the verdict is nearly 50/50
  EP vs missing even when the reading fires. C is literally coin-flipping between EP and
  missing on the same stable retrospective reading.

**Critical finding for LP-28:** The "as of" is NOT producing R2 genuine-ambiguity behavior
in the expected pattern. **Both B and C read the clause retrospectively in nearly every run
but cannot consistently convert that reading to a verdict.** This is not "two defensible
readings causing a split" — it's a single reading (retrospective) that produces an
unstable verdict. **LP-28 reclassifies from R2 → REASONING NON-DETERMINISM** (B and C
cannot stably map their consistent retrospective reading to a verdict; A is stable but via
schema override not clause reading).

---

### LP-22 — `landlord_obligation_obtain_snda` (R1 contrast: "before commencement" timing)

| Model | Verdicts (N=20) | Fingerprint `timing_before_commencement` | Verdict tracks FP? |
|---|---|---|---|
| A (Sonnet) | **⚠ PARSE_ERROR×8, EP×12** | True×1, False×11 (usable 12 only) | Partial (parse errors on 8) |
| B (GPT) | **⚠ ERROR×17, missing×2, PARSE_ERROR×1** | True×2 | Unusable (85% errors) |
| C (Grok) | EP×20 | True×16, False×4 | **No** — C returns EP regardless of timing flag |

**Analysis:**
LP-22's long 11-element prompt (~10.6K chars) caused heavy API failures; the LP-22 data
is too corrupted for firm conclusions. What is visible:
- C: stable EP×20 regardless of timing engagement — C never doubts the SNDA obligation.
- A: the 12 usable samples suggest mostly EP (A reads the obligation as present); the
  timing flag rarely fires (1/12), consistent with A not typically engaging the "before"
  sub-requirement.
- B: nearly all errors — the timing-based 50/50 flip seen in N=6 couldn't be replicated
  here due to API failures.

**Conclusion for LP-22: Inconclusive at N=20 due to API error rate.** The R1 vs genuine-
ambiguity question for the LP-22 B flip cannot be answered from this data.

---

## Per-cell classification

| Cell | N=20 Classification | Evidence |
|---|---|---|
| **LP-03** (R2 breaker) | **MIXED** | A: stable GENUINE AMBIGUITY (derives→unclear consistently). B: REASONING NON-DETERMINISM in reasoning, but verdict accidentally stable at N=20 (N=6 unclear was low-frequency noise). C: stable. |
| **LP-09** (R2 breaker) | **REASONING NON-DETERMINISM (C)** | A stable via schema override. C's synonym-matching fires in only 30% of runs; weakly predicts verdict. B unusable. |
| **LP-28** (R2 control) | **REASONING NON-DETERMINISM (B, C)** — **NOT genuine ambiguity** | Both B and C read "as of" retrospectively in ~100% of runs, yet produce unstable verdicts (B: 65/20/15 missing/unclear/EP; C: 50/50 EP/missing). The reading is stable; the verdict-mapping is not. |
| **LP-22** (R1 contrast) | **Inconclusive** | 85-40% API error rate on long prompt; insufficient usable data. |

---

## Headline

**Of the 3 R2 "breaker" cells with usable data, 0 showed clean GENUINE-AMBIGUITY behavior
and 2–3 showed REASONING NON-DETERMINISM in at least one model.**

The most important finding is **LP-28 (the designated R2 control)**: at N=20, B and C
read the clause consistently (retrospective) but cannot map it to a stable verdict. What
looks like "two defensible legal readings" from the outside is actually one reading
(retrospective) producing a non-deterministic verdict. This reclassifies LP-28 from R2
to reasoning non-determinism.

**LP-03 is the partial exception**: A shows genuine-ambiguity-like stability (derives S2.2
implication → consistently returns unclear). B shows non-deterministic reasoning but the
verdict is stable. The "A=unclear, C=missing" cross-model split on LP-03 appears to be
genuine (two stable, reasoned readings of the same clause).

---

## Does the verdict track the fingerprint?

| Cell/Model | FP stable? | Verdict stable? | FP predicts verdict? |
|---|---|---|---|
| LP-03/A | ✓ (True×19) | ✓ (unclear×19) | Yes |
| LP-03/B | **No** (9Y/11N) | ✓ (missing×20) | **No** — same verdict regardless |
| LP-03/C | ✓ (True×20) | ✓ (missing×20) | Trivially (one path) |
| LP-09/A | ✓ (True×20) | ✓ (missing×20) | Trivially (one path) |
| LP-09/C | **No** (6Y/14N) | Unstable (16/4) | Partially — when True: EP 50% vs 7% when False |
| LP-28/A | ✓ (True×20) | ✓ (missing×20) | Trivially |
| LP-28/B | ✓ (True×20) | **Unstable** (13/4/3) | **No** — stable reading, unstable verdict |
| LP-28/C | ✓ (True×19) | **Unstable** (10/9/1) | **No** — retrospective in 95%, but 50/50 EP/missing |

**Key pattern:** When a fingerprint flag is STABLE but the VERDICT is UNSTABLE (LP-28/B,
LP-28/C), the failure is not in "which reading" the model takes — it's in the threshold
that converts the reading into a verdict. The model consistently engages the inferential
step but inconsistently decides whether it "counts." This is a different failure mode from
reasoning non-determinism (where the step itself is intermittent).

---

## Implication for the R2 classification

The 372RUB R2 count of 6/12 appears inflated. LP-28 (one of the six) reclassifies to
reasoning non-determinism at N=20. Without the LP-22 data (inconclusive), the extent of
reclassification across the other R2 cases is unknown, but the LP-28 control result is a
warning: what appears as genuine ambiguity at N=6 can be unstable verdict-mapping on a
stable reading at N=20.

**Recommendation for Chat (stated as recommendation only):** the R2/non-determinism
distinction requires at minimum N=20 to be reliable. The 372RUB R2 count is a lower bound
on genuine ambiguity, not an upper bound; some R2 cases may be LP-28-like (stable reading,
unstable mapping). The GPT brief should treat R2 as "ambiguity or mapping instability,
needs N=20 to separate" rather than confirmed genuine ambiguity.

---

## Commit scope

- `_372ndet_harness.py` (runner script) + `_372ndet_results.json` (raw data, gitignored)
- Status file only committed.
