# Step 375N — COV Gate-Widening Diagnostic Results

**Date:** 2026-06-05  **Mode:** READ-ONLY / keyless. No model calls, no new 5e run.
**Artifact:** frozen run `lease_review_20260604_033046_52adbf` (52adbf), read through
`_normalize_use_consequence` (375M normalizer). Legacy `gap_impact` values normalized before
any comparison. n=1 lease (Atlas Meridian warehouse) — all counts are directional indicators
on this lease, not CAM metrics, not prevalence claims.
**External-use pause:** still in force. 375N does not lift it.

---

## 375M Write-Path Preflight

No fresh post-375M keyed run exists on disk. The newest artifact is the pre-deploy frozen 52adbf,
which carries legacy `gap_impact` in its `use_impact` fields. This is correct for 375N: all
use_impact values were read through the normalizer (not raw), so `gap_impact="favorable"` →
`"beneficial"`, `gap_impact="adverse"` → `"harmful"` before any question answer.

**The 375M write-path check is OWED on the next real keyed run** (see `375N_code_status.md`).

---

## Q1 — How many 375J directional Risk findings are NOT 5e-eligible today?

**PROVEN CLAIM: 18 of 26 directional Risk findings have LPs that never entered Stage 5e.**

All 18 have `materiality_source: "not_eligible"` in `375J_results.json` and `current_bucket: "risk"`.
Confirmed from 52adbf: all 18 LPs have `coverage_state = partial` with `< 50%` missing in
`element_verdicts`, so `_should_assess()` returns False. No `use_impact` key in their
coverage_assessment records (use_impact is None for all 18).

The 18 not-eligible directional LPs (element_verdicts missing %):

| LP | Name (abbrev.) | State | Missing% |
|---|---|---|---|
| LP-01 | Rent & Payment Terms | partial | 17% |
| LP-02 | Rent Escalation | partial | 25% |
| LP-04 | Security Deposit | partial | 40% |
| LP-06 | Maintenance & Repairs | partial | 40% |
| LP-07 | CAM | partial | 33% |
| LP-11 | Default & Remedies | partial | 12% |
| LP-15 | Signage Rights | partial | 33% |
| LP-17 | Dispute Resolution | partial | 33% |
| LP-18 | Holdover Provisions | partial | 20% |
| LP-19 | Utilities | partial | 33% |
| LP-21 | Guaranty of Lease | partial | 40% |
| LP-22 | SNDA | partial | 45% |
| LP-24 | Damage & Destruction | partial | 14% |
| LP-25 | Condemnation | partial | 14% |
| LP-27 | Landlord Default & Tenant Remedies | partial | 20% |
| LP-28 | Compliance with Laws | partial | 33% |
| LP-29 | Right of Entry / Landlord Access | partial | 33% |
| LP-30 | Estoppel Certificate | partial | 33% |

**Caveat:** n=1 lease. 18/26 not-eligible is a structural consequence of the 50% threshold applied
to this lease's element-verdicts distribution. A different lease with different schema element counts
per LP could produce a different ratio.

**Still-unmeasured:** Rate on lease #2+. Whether the 18 gap is typical or atypical requires a second
lease.

---

## Q2 — Of those not-eligible, how many are plausible candidates for assessed use-consequence?

**PROVEN CLAIM: All 18 not-eligible directional LPs have real provision content and a real gap —
all 18 are plausible 5e-assessable candidates. None qualify as "5e has no input."**

Every LP in the not-eligible list is `coverage_state=partial` with actual `tenant_text` content
and a measurable missing element count. Stage 5e assesses the consequence of a gap *given the
tenant's use profile*; the provision content exists for each LP. 5e's question ("is this gap
beneficial/harmful/neutral for a warehouse tenant?") is answerable for all 18.

**Sub-classification by gap thickness:**

*Strong-gap candidates (25–45% missing) — 14 LPs:*
LP-02 (25%), LP-04 (40%), LP-06 (40%), LP-07 (33%), LP-15 (33%), LP-17 (33%), LP-18 (20%),
LP-19 (33%), LP-21 (40%), LP-22 (45%), LP-27 (20%), LP-28 (33%), LP-29 (33%), LP-30 (33%)

*Thin-gap candidates (< 20% missing) — 4 LPs:*
LP-01 (17%), LP-11 (12%), LP-24 (14%), LP-25 (14%)

Thin-gap LPs have very high coverage (83–88% elements present). 5e can still assess the residual
gap consequence, but the input is marginal — these are the least likely to produce a decisive
(assert-strength) use_consequence assessment.

**No LP in the 18 falls into "5e has no input"** — that category applies to compound_risk findings
(CRX-01 through CRX-06), which span multiple LPs and have no single provision for 5e to assess.
The 18 not-eligible directional LPs are all single-LP directional findings with a discrete provision.

**Caveat:** Assessment quality is still-unmeasured for the thin-gap LPs. Whether 5e returns
`assert`, `assert_weak`, or `context_dependent` for LP-11/24/25 cannot be determined without a run.

**Still-unmeasured:** Post-widening 5e hit rate across all 18. No run data; prediction only.

---

## Q3 — Adverse vs favorable/neutral split among directional findings (flood check)

**PROVEN CLAIM: All 26 directional findings are adverse (tenant_unprotected). 0 are favorable or
neutral. On this lease, directional-adverse entry = "admit all 26 directionals."**

From 52adbf `cross_provision_findings`: all 26 `directional_mismatch` findings have
`directionality = "tenant_unprotected"`. Zero findings have `directionality = "landlord_unprotected"`
or `"match"`. The Atlas Meridian warehouse lease is one-sided adverse to the tenant on every
directional provision.

Breakdown:
- directional_mismatch findings: 26 — ALL adverse (tenant_unprotected)
- compound_risk findings: 6 — NOT directional (None/not_directional)
- Total findings: 32

**Consequence for Strategy B (directional-adverse entry as COV condition):**
Using Stage-7 `directionality=tenant_unprotected` as an entry condition admits **all 26 directional
LPs** into 5e on this artifact. Because there are no favorable or neutral directional findings,
the adverse gate is never a filtering mechanism — it is equivalent to "admit all directional
findings." This is the flood risk: B pushes 26 LPs into 5e vs the current 8.

**Caveat:** This is a property of THIS lease's extreme one-sidedness, not of the B gate design.
On a balanced lease where some directional findings are favorable, B would admit only adverse-direction
LPs (a bounded subset). The flood risk is specific to adversarial leases.

**Still-unmeasured:** What fraction of directional findings would be adverse on a typical balanced
commercial lease. The B gate may be proportionate on lease #2; it is a flood on this one.

---

## Q4 — Can present-hostile covered LPs be detected from stored artifacts without 375H-C?

**PROVEN CLAIM: NO — the current artifact provides no structural signal that LP-09 is
present-hostile. Detecting covered present-hostile LPs requires the 375H-C schema repair.**

LP-09 (Subletting & Assignment) artifact state in 52adbf:
- `coverage_state: "covered"` — system classifies as fully addressed
- `covered_unfavorable_adverse_to: null` — system did NOT flag it as covered-unfavorable
- `requires_attention: False` — system does NOT route it to attention
- `use_impact: null` — no 5e assessment ran
- `review_priority_distance_signal: {escalated: False, hard_flag: False}` — no escalation

The 4 missing elements in LP-09's `element_verdicts` (change_of_control, tenant_remains_liable,
transfer_profit_sharing, required_transfer_documentation) are ALL in
`favorable_or_non_adverse_absences` — all 4 are adverse to the landlord, not to the tenant. So the
system treats LP-09 as fully covered from the tenant's perspective, correctly.

**What IS in the artifact:**
- `caution_signals: ["common_dispute_area", "landlord_leverage_point"]` — a `landlord_leverage_point`
  caution signal is present.

This is the ONLY detectable signal. However:
1. `landlord_leverage_point` fires on other LPs too (e.g., LP-03) — it is not a present-hostile-specific flag.
2. `covered` + `landlord_leverage_point` is an unreliable proxy. Many covered LPs with landlord-favorable
   terms legitimately score covered (where the schema has protective-direction elements and they passed).
   LP-13 (Indemnification) is covered via schema polarity elements and is genuinely balanced.
3. The architectural reason LP-09 bypasses detection is that its schema has no element asking
   "consent may not be unreasonably withheld" — a topical-presence element satisfies when a one-sided
   clause appears (Part A of 375H). Without 375H-C adding protective-direction elements to the schema,
   there is no artifact field that distinguishes LP-09 from LP-13.

**Decision consequence:** Strategy C (present-hostile COV entry) CANNOT proceed reliably on current
artifacts. It is gated on 375H-C completing the schema repair. Any attempt to implement C now would
require the crude heuristic `covered` + `landlord_leverage_point` — a noisy proxy that would admit
legitimate balanced covered provisions and miss present-hostile ones where no leverage signal fires.

**Caveat:** A future hardened `covered_unfavorable_adverse_to` field (post-375H-C) would provide the
structural signal. That field exists in the schema (not null) for provisions where the 375H-C repair
detects polarity failure.

**Still-unmeasured:** How many other covered LPs on other leases are present-hostile. LP-09 is the
only confirmed case on 52adbf.

---

## Q5 — Is threshold-lowering sufficient to catch the 375H failure mode?

**PROVEN CLAIM: NO. LP-09 is `coverage_state = "covered"`. Threshold-lowering is
PROVABLY INSUFFICIENT — it cannot reach covered LPs regardless of threshold.**

LP-09 in 52adbf: `coverage_state = "covered"`. The `_should_assess()` gate:

```python
def _should_assess(a: dict) -> bool:
    state = a.get("coverage_state", "")
    if state == "missing":
        return True
    if state == "review_needed":
        return True
    if state == "partial":
        evs = a.get("element_verdicts") or []
        # ... threshold math only runs here ...
        return n_total > 0 and (n_total - n_present) / n_total >= 0.5
    return False   # ← covered falls here regardless of threshold
```

`covered` returns `False` at the final `return False`. The threshold math never executes for
`covered` LPs. Lowering the threshold from 50% to 33%, 25%, or 0% makes no difference for LP-09.

**Why LP-09 is covered despite 4 missing elements:** The 4 missing elements are all classified as
`adverse_to: "landlord"` → placed in `favorable_or_non_adverse_absences`. This removes them from
the coverage gap calculation. `elements_missing` = [] → 0% gap → `covered`. The coverage system is
CORRECTLY scoring LP-09 as covered from the tenant's gap perspective. The defect is not in the
coverage-state calculation; it is in the schema not asking about protective direction for the present
elements (Part A of 375H).

**Structural entry is required.** Threshold-lowering catches LPs that are `partial` with gaps above
a threshold. It does not and cannot catch LPs that score `covered` via topical satisfaction of
schema elements that lack polarity checks.

**Caveat:** If 375H-C adds a schema element that LP-09 then FAILS (e.g., "consent may not be
unreasonably withheld"), LP-09's `coverage_state` would change from `covered` to `partial` or
`review_needed`, and threshold-lowering would then reach it. The repair must happen first.

**Still-unmeasured:** Whether 375H-C changes LP-09's coverage_state classification (from `covered`
to `partial`/`review_needed`) or adds a separate `covered_unfavorable_adverse_to` signal. Either
path makes LP-09 reachable.

---

## Q6 — Projected volume under each widening strategy

All projections are on-this-lease estimates. n=1, directional only, not CAM metrics.

### Threshold-sensitivity table (not-eligible directional LPs only)

| LP | Name | missing% | +33% | +25% | +20% |
|---|---|---|---|---|---|
| LP-01 | Rent & Payment Terms | 17% | N | N | N |
| LP-02 | Rent Escalation | 25% | N | Y | Y |
| LP-04 | Security Deposit | 40% | Y | Y | Y |
| LP-06 | Maintenance & Repairs | 40% | Y | Y | Y |
| LP-07 | CAM | 33% | Y | Y | Y |
| LP-11 | Default & Remedies | 12% | N | N | N |
| LP-15 | Signage Rights | 33% | Y | Y | Y |
| LP-17 | Dispute Resolution | 33% | Y | Y | Y |
| LP-18 | Holdover Provisions | 20% | N | N | Y |
| LP-19 | Utilities | 33% | Y | Y | Y |
| LP-21 | Guaranty of Lease | 40% | Y | Y | Y |
| LP-22 | SNDA | 45% | Y | Y | Y |
| LP-24 | Damage & Destruction | 14% | N | N | N |
| LP-25 | Condemnation | 14% | N | N | N |
| LP-27 | Landlord Default | 20% | N | N | Y |
| LP-28 | Compliance with Laws | 33% | Y | Y | Y |
| LP-29 | Right of Entry | 33% | Y | Y | Y |
| LP-30 | Estoppel Certificate | 33% | Y | Y | Y |
| **New LPs admitted** | | | **11** | **12** | **14** |

### Strategy A — Threshold-lower (e.g., 50% → 33%)

**Volume into 5e:** 8 (current) + 11 (new) = **19 LPs** total eligible  
**Directional LPs still not eligible:** 7 (LP-01, LP-11, LP-18, LP-24, LP-25, LP-27 + LP-02 just below 33%)

Wait, LP-02 is 25% which is below 33%. So at 33%: LP-01 (17%), LP-02 (25%), LP-11 (12%), LP-18 (20%), LP-24 (14%), LP-25 (14%), LP-27 (20%) = 7 LPs still not eligible.

**Fog bank projection (consequence_unassessed under A):**
- Directional unassessed: ~7 (the 7 that remain not-eligible)
- Compound_risk unassessed: 6 (CRX-01 through CRX-06, not single-LP, 5e does not run)
- Total consequence_unassessed: ~13

13 is under the 18-acceptable threshold. If some of the 11 new LPs enter 5e but return
`context_dependent` or `no_evaluators`, the count rises slightly — still likely under 18 unless
most fail assessment.

**Does not reach:** LP-09 (covered), any other covered present-hostile LP.

At threshold 25%: 12 new LPs (+LP-02), 6 directional still not eligible, fog bank ~12 + 6 = ~18
(at the boundary of acceptable).

**Recommendation implication:** 33% is safer than 25% from the fog bank perspective. The 33%
cluster (11 LPs) is a natural boundary — all LPs with exactly 1/3 or 2/5 missing elements.

### Strategy B — Directional-adverse entry

**Volume into 5e:** 8 (current) + 18 (all not-eligible directional) = **26 LPs** — all directional  
**Directional LPs still not eligible:** 0

**Fog bank projection:**
- Directional unassessed: 0 (all 26 assessed, assuming no assessment failures)
- Compound_risk unassessed: 6 (unchanged — compound findings not single-LP)
- Total: ~6 — well under 18

**Flood risk (NOT fog bank):** If all 26 are assessed as harmful + high/medium materiality (likely
on this one-sided lease), output is ~26 `actionable_material_risk` findings. This is a large Risk
count but may be accurate for a landlord-heavy lease. The concern is that the adverse gate provides
no filtering on this artifact — all 26 directional LPs are adverse, so B ≈ "admit everything."

**Does not reach:** LP-09 (covered).

### Strategy C — Present-hostile schema entry (requires 375H-C)

**Volume into 5e without 375H-C:** 0 new LPs. Cannot detect present-hostile covered LPs from
current artifacts (Q4 confirmed).

**Volume into 5e after 375H-C:** LP-09 + any other LPs where 375H-C schema repair reveals
present-hostile coverage. On this lease: confirmed 1 LP (LP-09). Others are still-unmeasured
(depends on 375H-C fixture results and any additional covered-state LPs that fail the new
protective-direction elements).

**Fog bank projection (after 375H-C):** LP-09 enters 5e and gets assessed → net -1 from
consequence_unassessed (LP-09 moves to an assessed bucket). Minor improvement.

**C alone is insufficient** to fix the sparsity problem — it addresses only the covered-hostile
subset, not the partial-below-threshold subset (18 LPs).

### Strategy D — Hybrid (A + C)

**Volume into 5e:** 19 (from A at 33%) + LP-09 (from C, after 375H-C) = **20 LPs**  
**Directional LPs still not eligible:** 6 (same 7 as A minus LP-09 which is now assessed)

**Fog bank projection:**
- Directional unassessed: ~6 (the 6 remaining partial+<33% that aren't LP-09)
- Compound_risk unassessed: 6
- Total: ~12 — under 18, acceptable.

**D is the complete solution** — it fixes the threshold-gated sparsity AND the covered-hostile bypass.
But C component requires 375H-C to complete first.

### Summary table

| Strategy | New LPs | Total Eligible | Dir. Unassessed | CRX Unassessed | Total Unassessed | Fog bank? |
|---|---|---|---|---|---|---|
| Current | 0 | 8 | 18 | 6 | 24* | *(routed to Risk via floor) |
| A (33%) | +11 | 19 | 7 | 6 | ~13 | No (under 18) |
| A (25%) | +12 | 20 | 6 | 6 | ~12 | Borderline |
| B (dir-adverse) | +18 | 26 | 0 | 6 | ~6 | No (but flood risk) |
| C (now) | 0 | 8 | 18 | 6 | 24 | Same as current |
| C (after 375H-C) | +1 | 9 | 17 | 6 | ~23 | Minor improvement only |
| D (33% + 375H-C) | +12 | 20 | 6 | 6 | ~12 | No |

*Current 24 unassessed are silently routed to Risk via floor — not labeled as unassessed in UI.

---

## Sized A/B/C/D Recommendation

**Evidence-based recommendation: Strategy A (33%) now → Strategy D (A + C) after 375H-C.**

This is a staged recommendation, not a single-gate choice.

**Immediate (375E-COV): Implement Strategy A at 33% threshold.**

- Implementable now. No dependency on 375H-C.
- Adds 11 new LPs to 5e, all of which have real provision content (Q2: all plausible).
- Fog bank stays well within range (~13 total unassessed after assessment, under 18 acceptable).
- Bounded admission — filters by actual coverage gap rather than admitting all directionals.
- Does not flood: the 11 new LPs are all partial-state with real element gaps, not "admit everything."

**B is NOT recommended for production at this stage (on this lease):**
- On this artifact, B = "admit all 26 directionals" (Q3: 0 favorable/neutral findings → adverse gate
  never filters). The lease is too one-sided for B to be a bounded condition.
- Re-evaluate B on lease #2 where a favorable-direction finding exists and the adverse gate actually
  exercises.
- B remains valid as a diagnostic (as in 375J's Policy E).

**C cannot proceed now (gated on 375H-C):**
- Q4 and Q5 confirm: no structural present-hostile signal in current artifacts; LP-09 is `covered`
  and threshold-lowering provably cannot reach it.
- C is queued: implement after 375H-C adds the protective-direction schema element, which changes
  LP-09's classification.

**D is the long-term target:**
- A + C together covers both the threshold-gated and covered-hostile bypass paths.
- D(33%) produces fog bank of ~12 — acceptable.
- Phased: A ships with 375E-COV; C adds after 375H-C completes.

---

## Two COV Design Calls (framed with numbers — Tzvi decides)

### Design Call 1: Gate shape (what widens `_should_assess`)

The question is: which threshold value within Strategy A?

| Threshold | New directional LPs | Still not eligible | Notes |
|---|---|---|---|
| 33% | 11 | 7 | Natural cluster — all the 1/3 and 2/5 missing LPs |
| 25% | 12 | 6 | Adds LP-02 (Rent Escalation, 25%) |
| 20% | 14 | 4 | Adds LP-18 (Holdover), LP-27 (Landlord Default) |

**The numbers:** 33% is the natural cluster boundary. Moving from 33% to 25% adds LP-02 (Rent
Escalation) — a core commercial provision worth assessing. Moving to 20% adds LP-18 (Holdover)
and LP-27 (Landlord Default) — also significant. The 33% threshold admits all LPs with >= 2 of 5
or >= 2 of 6 elements missing.

The 7 LPs that remain not eligible at 33% (LP-01, LP-02, LP-11, LP-18, LP-24, LP-25, LP-27) include
LP-01 (Rent, 17%) and LP-11 (Default, 12%) — very high coverage, marginal gaps. LP-24 (Damage &
Destruction, 14%) and LP-25 (Condemnation, 14%) are also thin. These are the most defensible
exclusions at 33%.

**Tzvi decides:** 33% vs 25% is the primary call. 20% admits the thin-gap group (LP-18, LP-27)
but approaches "admit everything partial" for this lease (14 of 18 at 20%).

### Design Call 2: Landing bucket for consequence_unassessed directional findings

After 375E-COV, 5e will run on newly eligible LPs. But:
- Some may produce assessed results (beneficial/harmful/neutral) → routed by 375E-DIR
- Some may fail assessment (no_evaluators, context_dependent) → land somewhere
- LPs still below the threshold remain not_eligible → also unassessed

**The question:** Where do these unassessed directional findings land?

Current behavior: silently promoted to Risk via floor in `lease_adapter.py`. 375J proved this is
the core sparsity problem — 18 findings in Risk with no assessed materiality.

Options (not pre-picked here — 375N gives the numbers for Tzvi's call):
- **Option I (keep floor):** Unassessed directional findings continue routing to Risk. Status quo.
  After A(33%): ~7 directional findings still use floor → Risk. Simple but still opaque.
- **Option II (visible subtype):** Route unassessed directional to a distinct bucket
  (`consequence_unassessed` / Needs Review subtype). After A(33%): ~7 findings labeled explicitly
  as "Risk unconfirmed — consequence not assessed." Transparent; 7 is within the 18-acceptable range.
- **Option III (source-strict, 375J Policy C):** Unassessed directional goes to
  `consequence_unassessed_strict` — out of Risk entirely until assessed. 375J Q5 showed this
  removes 73% of directional findings from Risk (19/26), which is too aggressive without COV first.
  After A(33%): remaining 7 unassessed removed from Risk → only 7 directional findings leave Risk.
  Still a large change if 375E-DIR has not run.

**The numbers:** At A(33%), ~7 directional findings need a landing bucket decision.
- Option II keeps them in Risk but labels them visibly — 7 labeled findings, acceptable fog bank.
- Option III removes them from Risk — 7 findings disappear from Risk UI, lawyer sees less Risk.
  Depends on whether 375E-DIR is deployed simultaneously.

This is the critical sequencing call: 375E-COV + 375E-DIR should ship together or in immediate
succession, not independently, or Option III creates a visible gap.

---

## Scope guard confirmed

| Guard | Status |
|---|---|
| `_should_assess` unchanged | YES — no change |
| No routing changed | YES |
| No cam/core/ touched | YES |
| No model calls | YES — purely keyless artifact reads |
| External-use pause NOT lifted | YES |
| LP-20 jitter unresolved | YES — stays open |
| 375H-C keyed fixtures NOT implemented | YES — deferred |
| DEPLOYMENT TRAP (375H repair findings → Risk blocked) | YES — unchanged |
