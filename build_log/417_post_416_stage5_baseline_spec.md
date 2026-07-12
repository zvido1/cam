# 417 — Post-416 Stage 5 Baseline Measurement Spec

**Date:** 2026-07-12
**Type:** Measurement spec only. No model swap. No push.
**Purpose:** Establish the post-414/416 residual Stage 5 wobble rate of the current frozen evaluator panel, with silent fallback blocked (414) and declared config integrity enforced (416). This is the baseline against which Stage 5 stabilization work is measured.

---

## Context

Steps 414 and 416 closed two invariants in sequence:

- **414 (fallback integrity):** Identity-frozen stack. Silent cross-provider substitution raises FatalProviderError. Fallback events are logged to `is_fallback`/`actual_model`/`fallback_reason`. No degraded run can masquerade as a canonical frozen-panel run.
- **416 (config integrity):** Declared generation parameters must match the outbound provider payload, or the mismatch must be backed by a documented capability exception. Undocumented omissions raise FatalProviderError. Scope: temperature, max_tokens, reasoning_effort across OpenAI/Anthropic/xAI adapters.

**What is not fixed:** Role B primary (gpt-5.5) operates at provider-default temperature=1. The model rejects temperature=0 at the API level. This is a provider capability constraint, not an adapter defect. The 416 fix documents the exception and hard-fails on any undocumented omission — it does not and cannot change gpt-5.5's behavior.

**Why this baseline matters:** Step 411 measured ~31% LP wobble rate across two Atreca runs (Run A/Run B artifact pair). That measurement predates both 414 and 416. The wobble has at least three possible sources — silent fallback (now blocked by 414), config mismatch (now asserted by 416), and genuine evaluator-output variance (still present, extent unknown). The 417 baseline measures the residual after the first two sources are removed.

---

## Part 1 — Current Panel (Do Not Swap)

Use the frozen evaluator panel as configured after 416. The panel is:

| Role | Provider | Model | Temperature | Notes |
|------|----------|-------|-------------|-------|
| A | anthropic | claude-sonnet-4-6 | 0 (transmitted) | No reasoning_effort |
| B | openai | gpt-5.5 | 1 (provider default) | Model rejects temp=0; documented exception in TEMPERATURE_ONLY_DEFAULT_MODELS |
| C | xai | grok-4.3 | 0 (transmitted) | |

**Do not:**
- Swap Role B primary to gpt-5.4
- Force temperature override on gpt-5.5
- Alter fallback chain except as enforced by 414/416
- Change prompts, merge logic, or any `cam/core/` path

---

## Part 2 — Lease Fixture

**Preferred fixture:** The same Atreca lease used in the 411 wobble measurement (Atreca EX-10.18, 450 East Jamie Ct, South SF). Using the same lease makes the pre/post-416 comparison meaningful.

- Fixture file: `05 Lease Analyzer/test_data/tenants/atreca_ex10_18_lease.txt` (confirm exact path before running)
- Artifact path from Step 411 Atreca runs: confirm from `build_log/411_stage5_coverage_reproducibility_trace.md`
- Run command: standard Mode C pipeline invocation. Record exact command used.
- Record: fixture path, lease identity, job ID of every run, wall-clock time per run, total cost.

If the Atreca fixture is unavailable or the pipeline cannot reach it, fall back to the Atlas fixture (`atlas_meridian_warehouse_lease.txt`) with an explicit note that the pre/post comparison is then cross-fixture and less clean.

---

## Part 3 — N-Run Design

**Minimum N=10. N=10 is the floor, not the preference.**

All runs:
- Same input lease
- Same config
- Same code (no changes between runs)
- Same frozen stack (414/416 enforced)

**Before running, record estimated cost and wall-clock:**
- A full Mode C Atlas run is ~17–25 min and costs real tokens (CLAUDE.md).
- A full Mode C Atreca run from Step 407 was ~23 min for a single run.
- N=10 × 23 min ≈ 230 min (≈ 4 hours) wall-clock. Record actual.
- Token cost: the 407 run consumed approximately 2–3M tokens/run (check cost from model billing if tracked). N=10 = 20–30M tokens. Record actual.

**If N=10 is determined to be prohibitive by explicit instruction, the report must:**
- Label every number as a "limited lower-confidence measurement (N=<actual>)"
- Carry an explicit N-caveat on every variance rate stated
- Not be used as a canonical patent/reliability number without that caveat
- Not be promoted without the user's explicit authorization

Do not let N=5 silently become the patent variance number.

---

## Part 4 — What to Measure (Stage 5 Coverage Assessment)

For every run, for every LP in the Stage 5 output, collect:

**LP-level fields:**
- `coverage_state`
- `requires_attention`
- `coverage_state_baseline` (if present — the pre-dispute-propagation state)
- `verdict_distance`
- Materiality/default fields if present

**Element-level fields (for every element within each LP):**
- Per-element verdicts per evaluator role (A, B, C)
- Merged verdict
- `element_verdicts` / `disputed` flags if present

**Evaluator-output metadata per run per role:**
- `is_fallback` — should be False for all; flag any True immediately as a 414 regression
- `actual_model` — confirm matches expected model for each role
- `fallback_reason` — should be absent; any presence is a regression signal
- `reasoning_effort` — for Role B: confirm "medium" transmitted
- `last_integrity` dict from each adapter — temperature/max_tokens/reasoning_effort transmitted/omitted/omission_reasons

**Stage 5e / use_impact fields (if present on LP):**
- `use_consequence`
- `use_consequence_source`
- `use_impact` dict contents
- `use_reasoning`
- `materiality`
- `consequence_confidence`

---

## Part 5 — Per-LP Frequency Distribution (Not Binary)

For each LP, after N=10 runs, report:

| Field | What to report |
|-------|----------------|
| `coverage_state` values observed | All distinct values across N runs, e.g. `{partial: 8, review_needed: 2}` |
| Frequency per state | `partial 8/10`, `review_needed 2/10` |
| Most frequent state | The modal state |
| Minority states | States with <50% frequency |
| State entropy / instability score | Simple: `1 - max_freq/N`. Optional: Shannon entropy if easy. |
| Boundary characterization | Is churn between adjacent states (e.g. partial↔review_needed) or distant states (e.g. covered↔missing)? |
| Element-level verdict frequencies | For elements that changed: which element, which values, how often |
| Final-state stability despite element churn | Does element-level variance cancel out at the LP level? |

**Distinguish four churn categories:**
1. **10/10 or 9/10 stable** — effectively deterministic; boundary noise is 1 minority instance
2. **9/1 or 8/2** — boundary noise; minor instability; one evaluator run moved
3. **6/4 or 7/3** — directional preference with meaningful variance
4. **5/5 or 6/4 at genuine split** — evaluator panel genuinely divided; no mode dominates

Do not collapse all non-10/10 LPs into a single "churn" category.

---

## Part 6 — Per-Role Variance and Flip Counts

Measure each evaluator role separately. This table is required.

For each role (A, B, C), across all N runs:

| Metric | How to compute |
|--------|----------------|
| Raw verdict flips per LP/element | Count how many LP/element verdicts changed across runs for that role's output |
| Own-answer change rate | For each LP/element, how often did that role's verdict differ from its own median/mode |
| LPs/elements each role flipped on | Identify which specific LPs and elements had role-level variance |
| Provider/model/config per role per run | Record `actual_model`, `is_fallback`, integrity metadata |
| Fallback events | Any is_fallback=True is a 414 regression; report prominently |

**Answer these questions explicitly in the report:**

1. Is Role B primary (gpt-5.5, temperature=1) a disproportionate source of raw verdict flips compared to Role A (Claude, temperature=0) and Role C (Grok, temperature=0)?
2. Are Role A and Role C producing same-model, same-config variance at temperature=0 — i.e. variance not attributable to temperature freedom?
3. Does Role B's temperature=1 explain most of the observed instability, or only part of it?

These three answers determine the framing for Stage 5 stabilization. Do not infer Role B's contribution from aggregate panel churn — measure each role's flip count separately.

---

## Part 7 — Classify Variance Sources

Separate observed variance into these source categories:

| Source | Description | Expected status after 414/416 |
|--------|-------------|-------------------------------|
| Fallback/substitution variance | A non-primary model answered for a role | Should be zero after 414; any instance is a regression |
| Config mismatch variance | Undocumented parameter omission reached the provider | Should be zero after 416 for OpenAI/Anthropic/xAI; any undocumented omission is a regression |
| Role B temperature variance | gpt-5.5 at temperature=1 produces non-deterministic output | Expected; quantify |
| Role A/C same-model variance | Claude/Grok at temperature=0 still produces run-to-run variance | Measure; may be non-zero |
| Panel-aggregation variance | Role-level variance that alters merged LP outcome after majority/distance merge | Measure separately from raw role variance |
| Upstream parsing/document variance | Input extraction differs between runs | Should be zero (same fixture); flag if not |
| Consequence/value churn | `use_consequence`, `materiality` values change without `coverage_state` change | Measure as a distinct category |
| Eligibility churn | LP crosses in/out of `_should_assess()` gate | Should be zero on N=10 of the same lease; flag if not |

If the baseline shows:
- Any fallback event with `is_fallback=True` → treat as 414 regression, report prominently
- Any config mismatch without a documented exception → treat as 416 regression, report prominently

---

## Part 8 — Output Tables Required

The Step 417 measurement report (`build_log/417_post_416_stage5_baseline.md`) must include:

1. **Run inventory table** — run N, job ID, timestamp, wall-clock time, cost (if tracked)
2. **Per-run LP summary** — count of LPs by coverage_state per run (to catch per-run outliers)
3. **Per-LP coverage-state frequency table** — N=10 rows, all states with frequencies
4. **Per-LP element-verdict frequency table** — for LPs with any churn, all element-level changes
5. **LPs with 10/10 stability** — list
6. **LPs with 9/1 or 8/2 boundary noise** — list with modal state and minority state
7. **LPs with 6/4 or 7/3 directional preference** — list
8. **LPs with 5/5 genuine split** — list (high-priority stabilization targets)
9. **LPs with element-level churn but stable final state** — list (these are lower-priority; final state is stable)
10. **LPs with use_impact / consequence churn** — if consequence values change independently of coverage_state
11. **Per-role raw verdict flip table** — Role A / B / C, LP/element flip counts, which LPs each role moved on
12. **Per-role contribution to merged-state churn** — what fraction of panel-level coverage_state changes are attributable to each role's flip
13. **Fallback/config-integrity audit table** — every run's `is_fallback` and integrity metadata, confirming no regressions
14. **Overall variance rate** — e.g. `X of 32 LPs showed any coverage_state change across N=10 runs` — stated with N=10 denominator explicitly
15. **Cost/time table** — actual wall-clock and token cost per run and total

---

## Part 9 — Decision Standard

The measurement report must answer:

1. What is the post-414/416 irreducible Stage 5 wobble rate? (N=10, same fixture, frozen stack)
2. How much of the pre-416 ~31% wobble rate (from Step 411) remains?
3. Is the remaining wobble concentrated near known boundary cases (9/1 type) or genuine 5/5 splits?
4. Is Role B primary a disproportionate contributor?
5. Are Claude/Grok still producing temperature=0 same-model variance?
6. Is Stage 5 stabilization best framed as:
   - **Boundary/hysteresis problem** — most churn is 9/1 type; stabilization means nudging borderline LPs toward consistent classification
   - **N-of-M sampling problem** — panel disagrees and the merge is statistically uncertain; stabilization means increasing N or using majority-of-many
   - **Prompt/spec problem** — evaluators are receiving ambiguous task definitions; stabilization means tightening the prompt
   - **Role-weighting problem** — one role (likely B at temperature=1) is disproportionately noisy; stabilization means downweighting or replacing that role's influence
   - **Model-panel problem** — Role B primary cannot be temperature-pinned; the panel as configured cannot achieve deterministic Stage 5 output
   - Or some combination — name the mix and the proportion

The answer determines what gets built next. Do not recommend a stabilization approach before this measurement answers which framing dominates.

---

## Part 10 — Optional Shadow Diagnostic (Not Part of Baseline)

This section may be executed ONLY AFTER the N=10 current-panel baseline is complete, and only with separate authorization.

**Purpose:** Estimate how much variance would decrease if Role B were temporarily forced to gpt-5.4 (which accepts temperature=0).

**Rules:**
- Select a small subset of LPs (5–10) that showed instability in the baseline
- Re-run those LPs only with Role B primary temporarily set to gpt-5.4
- Label every output: `COUNTERFACTUAL / SHADOW / NOT FROZEN PANEL`
- Do not mix shadow outputs with baseline outputs
- Do not commit any Role B swap to config
- Do not alter frozen-panel state
- Do not use shadow numbers for canonical metrics or patent claims
- Use only to answer: "how much of the instability is temperature-attributable?"

**Do not start the shadow diagnostic before the baseline is complete.** The baseline is the load-bearing measurement. The shadow diagnostic is context only.

---

## Part 11 — Output Files

**This step writes (spec only):**
`build_log/417_post_416_stage5_baseline_spec.md` ← this file

**The measurement step writes:**
`build_log/417_post_416_stage5_baseline.md`

The measurement step is not authorized in this step. When authorized, the measurement step should:
1. Run N=10 on the Atreca fixture
2. Collect all fields in Part 4
3. Produce all tables in Part 8
4. Answer all questions in Part 9
5. Write `build_log/417_post_416_stage5_baseline.md`

---

## Git

Stage explicit paths only. No `git add .`. Do not stage result directories.

Suggested commit message: `417 scope post-416 stage5 baseline`

*Step 417 spec. Documentation only. No run authorized. No push.*
