# Step 371 — Stage 5 Upstream Variance Characterization

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Diagnostic only — read-only analysis over stored 370c artifacts. No code, no reruns.
**Base SHA:** `b18b58a` (370d). Analysis script `_step371_variance.py`. No `cam/core/`.

---

## BLUF (recommendation, not conclusion)

Two independent findings:

1. **Stage 5 is NOT a stable governed layer on identical input.** Across six matched 370c
   runs, **16 / 32 LPs show Class 3 (material governance) variance**, including **12 LPs
   that flip the lawyer-visible action bucket** (`clean` ↔ `needs_attention`) and **2 LPs
   that flip Stage 7 inclusion** — on byte-identical fixture and config.

2. **Stage 5 variance did NOT cause the 222051 collapse (Scenario B).** 222051's upstream
   was *within the healthy envelope* (flagged_lp=28, Stage 7 inclusion=28, zero action-bucket
   or inclusion outliers vs the six healthy runs), yet its directional output collapsed
   (7 final / 3 candidates per 370b) far below the healthy 22–28 candidate range. The
   collapse is a **downstream Pass-1 reliability defect**, not an upstream impoverishment.

The locked opening proposition holds and is now resolved: inherited downstream input
variance **exists and is material (Class 3)**, but was **not causally sufficient** for the
222051 collapse.

---

## 1. Step 0 result — Branch **0A** (snapshot survives)

`results/lease_review_20260529_222051_7c0d32/tenant_0/pipeline_results.json` present and
complete: `coverage_assessment` (32 LPs) with `coverage_state` + `coverage_state_baseline`,
`dispute_signal`, `materiality`, `use_impact` (on flagged LPs), `review_priority_distance_signal`,
`verdict_distance`, `lp_confidence`, plus `_stage_data.synthesis_meta`. Full causal
decomposition (Analysis A + B + **C**) available. **No reconstruction from final findings was
performed.**

### Field-name mapping (instruction field → REAL JSON field; absences flagged)
| Instruction field | Real JSON field | Note |
|---|---|---|
| lp_id | `issue_area_id` | |
| coverage_state | `coverage_state` | present |
| coverage_state_baseline | `coverage_state_baseline` | present |
| action_bucket | *(derived)* | **no stored field** — replicated app.js Mode-C bucket logic exactly (coverage_state/partial_class + use_impact gap/materiality skip) |
| use_impact.gap_impact / materiality / confidence | `use_impact.{gap_impact,materiality,confidence}` | present **only on flagged LPs** (11–14 of 32 per run) |
| materiality | `materiality` | top-level, present |
| dispute_signal.triggered | `dispute_signal.triggered` | present |
| elements_disputed / _critical | `elements_disputed_critical`, `elements_disputed_important` | present |
| verdict_distance | `verdict_distance.{max_distance,severity}` | present |
| confidence_cap | `lp_confidence` (vs `lp_confidence_base`) | **no field named confidence_cap**; lp_confidence is the governed value |
| review_priority | `review_priority_distance_signal.{escalated,hard_flag}` | **no plain review_priority field** |
| included_in_stage7_pass1_input | *(derived)* | replicated `_collect_flagged_lps`: coverage_state ∈ {missing, partial_material, partial_typical, review_needed} OR partial_class ∈ {partial_material, partial_typical} |
| stage7_pass1_serialized_content_hash | **absent** | per-LP serialized contribution not persisted; whole-prompt hash only (and only for 370c headless runs, not 222051) |

---

## 2. Six-run per-LP Stage 5 variance matrix

`class` column: 1=text-only · 2=structural-non-material · 3=material-governance · stable=identical on all governed+structural+text fields. `bucket(s)`/`coverage_state(s)`/`stage7` show the distinct values observed across the six runs.

```
LP      class  bucket(s)                 coverage_state(s)        stage7      governance_changed
LP-01   1      clean                     partial                  True
LP-02   3      clean                     partial                  True        lp_confidence, review_escalated, review_hard_flag, use_impact.gap_impact/materiality
LP-03   3      clean/needs_attention     partial/review_needed    True        coverage_state, action_bucket, review_hard_flag, use_impact.materiality
LP-04   1      clean                     partial                  True
LP-05   3      clean/needs_attention     review_needed/missing    True        coverage_state, action_bucket, materiality, use_impact.gap_impact/materiality
LP-06   3      clean                     partial                  True        lp_confidence, review_escalated, review_hard_flag
LP-07   1      clean                     partial                  True
LP-08   1      clean                     partial                  True
LP-09   3      needs_attention/clean     review_needed/partial    True        coverage_state, action_bucket, use_impact.gap_impact/materiality
LP-10   3      clean                     partial                  True        use_impact.materiality
LP-11   1      clean                     partial                  True
LP-12   stable clean                     not_applicable           False
LP-13   3      needs_attention/clean     review_needed/covered    True/False  coverage_state, action_bucket, STAGE7_INCLUDED, use_impact.gap_impact/materiality
LP-14   1      needs_attention           review_needed            True
LP-15   1      clean                     partial                  True
LP-16   3      needs_attention/clean     review_needed/partial    True        coverage_state, action_bucket, use_impact.materiality
LP-17   3      clean                     covered/partial          False/True  coverage_state, STAGE7_INCLUDED
LP-18   1      clean                     partial                  True
LP-19   3      needs_attention/clean     review_needed/partial    True        coverage_state, action_bucket, use_impact.gap_impact/materiality
LP-20   3      clean/needs_attention     missing                  True        action_bucket, review_hard_flag, use_impact.gap_impact/materiality
LP-21   1      clean                     partial                  True
LP-22   3      clean/needs_attention     partial/review_needed    True        coverage_state, action_bucket, dispute_triggered, lp_confidence, review_escalated/hard_flag, use_impact.gap_impact/materiality
LP-23   stable clean                     not_applicable           False
LP-24   1      clean                     partial                  True
LP-25   1      clean                     partial                  True
LP-26   3      needs_attention/clean     review_needed/partial    True        coverage_state, action_bucket, use_impact.gap_impact/materiality
LP-27   1      needs_attention           partial                  True
LP-28   3      needs_attention/clean     review_needed/partial    True        coverage_state, action_bucket, dispute_triggered, use_impact.gap_impact/materiality
LP-29   3      needs_attention/clean     review_needed/partial    True        coverage_state, action_bucket, use_impact.gap_impact/materiality
LP-30   1      clean                     partial                  True
LP-31   stable clean                     not_applicable           False
LP-32   3      clean/needs_attention     partial/review_needed    True        coverage_state, action_bucket, dispute_triggered
```

**Discipline applied — decision surface vs bytes:** an LP is Class 3 only if a *governed /
lawyer-visible decision field* changed (coverage_state, action_bucket, materiality,
dispute_triggered, lp_confidence cap, review escalation, Stage 7 inclusion, or the
use_impact gap/materiality that drive the bucket). LPs where only narrative text differs
(exposure_statement / headline / evidence_summary) are Class 1 — bytes changed, decision
surface did not. There were **zero Class 2** (no LP had a structural-only change without a
governance change) and **3 truly-identical** LPs (LP-12/23/31 — `not_applicable`, never in
Stage 7).

---

## 3. Class counts

| Class | Definition | Count |
|---|---|---|
| **1** — text-only | narrative differs; no governed/structural change | **13** |
| **2** — structural non-material | supporting fields/ordering differ, bucket+Stage7 equivalent | **0** |
| **3** — material governance | coverage_state / action_bucket / materiality / dispute / cap / review / Stage7-eligibility differ | **16** |
| **4** — catastrophic downstream-enabling | Stage 5 variance plausibly *causes* incomplete/false-clean Stage 7 | **0** (see §6) |
| identical | no variance on any tracked field | **3** |
| | **Total** | **32** |

---

## 4. Did any lawyer-visible action bucket change across identical runs?

**YES — 12 LPs:** LP-03, LP-05, LP-09, LP-13, LP-16, LP-19, LP-20, LP-22, LP-26, LP-28,
LP-29, LP-32. Each flips between `clean` and `needs_attention` on byte-identical input —
i.e. a provision a lawyer is told to attend to in one run is shown as clean in another. The
dominant drivers are `coverage_state` flipping `review_needed ↔ partial` and the Stage 5e
`use_impact` (gap_impact/materiality) being present/absent or differing (use_impact appears
on 11/13/14 LPs across runs — itself non-deterministic).

---

## 5. Did any Stage 7 inclusion / content change materially?

**YES — 2 LPs flip inclusion:** LP-13 (`review_needed` ↔ `covered`) and LP-17 (`covered` ↔
`partial`) move in/out of the Stage 7 eligible set. Notably the **count** stays 28 in all
six runs while **set membership varies** — so directional opportunity *content* is not
identical across runs even at constant count. Downstream, **directional Pass-1 candidate
counts varied 22 / 24 / 26 / 28 / 28 / 28** and directional findings 22–28 across the six —
confirming Stage 7 output is sensitive to this upstream variance, but within a non-collapsed
band.

---

## 6. 222051 causal decomposition — **Scenario B** (Branch 0A)

| Metric | 222051 (collapsed) | Healthy six-run envelope |
|---|---|---|
| flagged_lp_count | 28 | 28–28 |
| Stage 7 inclusion (computed) | 28 | 28–28 |
| action-bucket outliers vs healthy | **NONE** | — |
| Stage 7-inclusion outliers vs healthy | **NONE** | — |
| pass1 directional candidates | 3 (per 370b; field not stored in 222051) | 22–28 |
| directional findings (final) | **7** | 22–28 |
| total_cpf | 23 | 30–34 |

222051's **upstream Stage 5 state was within the healthy envelope** — same flagged-LP
volume, same Stage 7 inclusion count, and *no* per-LP action-bucket or inclusion value that
falls outside what the six healthy runs themselves produced. Its **directional output
collapsed downstream** (3 candidates vs healthy 22–28).

→ **Scenario B — Normal upstream, collapsed downstream.** Pass-1 has an independent
reliability defect; **Stage 5 variance does NOT explain the 222051 collapse.** (Consistent
with 370b/c/d: the directional collapse traces to Pass-1 candidate generation and Eval
output behavior, not to upstream coverage.)

Class 4 = 0 follows: no six-run LP variance reached "catastrophic downstream-enabling," and
the one real collapse (222051) was not upstream-driven.

---

## 7. Zero-total-CPF watch (carried, NOT fixed)

`total_cpf == 0` observed in **NO** inspected run. Minimum total_cpf = **23** (222051);
six 370c runs were 30–34. The zero-CPF early-bail path (370a-v's known blind spot, where
`renderSynthesisPanel` returns before the completeness banner) remains a **known but
unobserved** blind spot. No fix here; flagged for a SEPARATE completeness-guard extension
step if it is ever observed.

---

## 8. Recommended next step (RECOMMENDATION — not a conclusion, not a spec)

Routed to Chat for review before any remediation. Phrased as options, not decisions:

1. **Class 3 present (16 LPs, 12 bucket flips) → recommend Chat consider speccing a Stage 5
   governance-stability track.** The lawyer-visible instability (a provision flagged in one
   run, clean in the next, same input) is a product-credibility issue independent of the
   directional saga. The dominant lever appears to be Stage 5e `use_impact` non-determinism
   and `review_needed ↔ partial` coverage_state flips. *Recommendation only — I did not spec
   or scope a fix.*

2. **222051 = Scenario B → recommend treating Pass-1 directional determinism as a SEPARATE
   track from Stage 5.** Stage 5 stabilization (item 1) will not, on this evidence, fix the
   directional collapse; conversely the 370a guard + 370d budget address the downstream
   symptom. The two should not be conflated.

3. **Per the instruction's own decision gate**, "Any Class 3 → spec Stage 5 determinism /
   governance-stability remediation" — surfaced here for Chat to apply; I have **not**
   started it. No Class 4 → no urgent upstream-stabilization / 371b-replay trigger fired on
   this evidence.

**Not claimed:** that Stage 5 variance caused 222051 (Scenario B says it did not); any root
cause of the Stage 5 variance itself (not investigated — characterization only).

---

## Scope / commit

- Read-only analysis; no code changes, no model calls, no reruns. No `cam/core/`.
- Committed: `_step371_variance.py` (analysis script) + this status file (force-add past
  gitignore). Pre-existing uncommitted `app/config.py` left untouched.
