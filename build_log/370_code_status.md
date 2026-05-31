# Step 370 — Stage 7 directional output stability check (variance diagnostic)

**Date:** 2026-05-29
**Author:** Claude Code
**Type:** Diagnostic only. No change to detection logic.
**Server SHA:** `5f6fc35` (Step 369) — confirmed; all runs below carry `pass2_integrity`.

---

## BLUF (verdict)

**High-variance — intermittent — localized to Stage 7 Pass-1 directional candidate
generation.** NOT Stage 3 (flagged-LP set is stable), NOT Pass-2 matching (the Step 369
fix is working). NOT bucket migration (the directional+compound *sum* swings too).

- Three back-to-back fresh runs on identical input + identical code are **tight**:
  directional findings **28 / 28 / 28**, sum **36 / 37 / 34**, candidates **28 / 26 / 28**.
- But a fourth run on the **same code and same config** (the Step 369 validation run
  `222051`) is a severe low outlier: **7 findings / 3 candidates / sum 18**.
- `flagged_lp_count` is stable across all four (28 / 29 / 28 / 28), so the *input set*
  Stage 7 works from is deterministic. The swing is in how Pass-1 clusters that stable
  set into directional candidates: usually ~28, but capable of collapsing to ~3.

A Needs Review bucket built on this would usually hold ~28 directional items but
occasionally ~7 — a ~4× user-visible swing on identical input. **Per the Step 370
decision rule, this outranks the Overview/UI work and becomes its own remediation
track.** The good news: the fix surface is now precise (Pass-1 directional clustering),
and Pass-2 + the integrity guard are validated.

---

## Method (apples-to-apples — confounds removed before running)

The runs already on disk from earlier today were **not** a clean determinism test, and I
removed two confounds before measuring:

1. `183933` (the cited "27" run) used `identity_check=clauses_only`, **not**
   `landlord_property` — different input. Excluded from the determinism comparison.
2. Of the three `landlord_property` runs on disk, **only `222051` carried
   `pass2_integrity`** — i.e. only it ran on the full Step 369 synthesis path. `211254`
   and `214047` predate that instrumentation (empty `pass2_integrity`; `211254` lacks
   `pass2_raw` entirely). Comparing them to `222051` would compare across a **code
   change**, not run-to-run noise.

To get a clean test I generated **3 fresh runs on `5f6fc35`**, replicating the exact
persisted config of `222051` (read from its `job.json`):

- entry point: `run_lease_coverage_only` (Mode C / `analyze`) — the same function the web
  app's `_process_lease_job` calls for this job type
- input: `test_data/tenants/atlas_meridian_warehouse_lease.txt` (md5 `d679f2c3`, identical
  to `222051`)
- config: `perspective=tenant`, `template_type=blank_template`,
  `identity_check=landlord_property`, `access_code=cam_demo_2026`, 33 active provisions
  (`get_active_provisions(None, None)`), `run_id=tenant_0`
- providers: `anthropic` / `openai` / `xai` (direct) + `gemini` extraction. **OpenRouter
  disabled** (`DISABLE_OPENROUTER=1`) per instruction; lease evaluators don't use it.
- temperature 0.0 on all Stage 7 evaluators (so any variance is *despite* temp 0).

Driver: `05 Lease Analyzer/_step370_run3x.py`. Audit: `05 Lease Analyzer/_step370_audit.py`
(adds `flagged_lp_count` and the `directional+compound` sum to Chat's script).
Methodological note: `222051` was produced via the live uvicorn server; the 3 fresh runs
via a direct call to the same entry point with the byte-verified config. Same pipeline
logic, same models, same temp — invocation harness only.

---

## Results — four runs, all on `5f6fc35`, identical input

| Run | dir FINDINGS | dir CANDIDATES (Pass-1) | compound | **dir+comp SUM** | flagged_lp | INTEGRITY WARNING | Eval-A Pass-2 |
|-----|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `222051` (web) | **7** | **3** | 11 | **18** | 28 | absent | matched 3 ✓ (`all_lost` C/B/A = F/F/F) |
| `s370r1` (fresh) | 28 | 28 | 8 | **36** | 29 | **present** | `all_lost=True`, matched 0 (B/C matched 28) |
| `s370r2` (fresh) | 28 | 26 | 9 | **37** | 28 | **present** | `all_lost=True`, matched 0 (B/C matched 26) |
| `s370r3` (fresh) | 28 | 28 | 6 | **34** | 28 | **present** | `all_lost=True`, matched 0 (B/C matched 28) |

Pass-1 directional candidate count is confirmed directly from the synthesis log
(`[lease_synthesis] ... Directional candidates: N`): **28 / 26 / 28** for the three fresh
runs; the `3` for `222051` is derived from its `pass2_raw` (only `Dir-01/02/03` present).

Directional agreement / severity splits (fresh runs):
- `s370r1`: agreement `{1-2:20, 2-1:8}`, severity `{LOW:20, MED:8}`
- `s370r2`: agreement `{2-1:25, 1-2:3}`, severity `{MED:23, LOW:4, HIGH:1}`
- `s370r3`: agreement `{1-2:14, 2-1:14}`, severity `{LOW:14, MED:14}`
- `222051`: agreement `{3-0:6, 2-1:1}`, severity `{MED:3, LOW:2, HIGH:2}`

Note the agreement/severity *distribution* shifts run-to-run even when the **count** is
constant at 28 — consistent with Eval-A's votes being lost (B+C carry the count, but the
mix changes).

### Confounded context runs (NOT part of the verdict — different code and/or config)

| Run | identity_check | pass2_integrity | dir FINDINGS | compound | flagged_lp |
|-----|---|:---:|:---:|:---:|:---:|
| `183933` | `clauses_only` ⚠ different input | absent | 27 | 6 | 27 |
| `211254` | `landlord_property` | **absent** ⚠ pre-369 | 28 | 6 | 28 |
| `214047` | `landlord_property` | **absent** ⚠ pre-369 | 27 | 6 | 28 |

---

## Three-way analysis (per the sharpened decision logic)

1. **Determinism (directional findings across runs).** Among the 3 controlled fresh runs:
   **stable (28/28/28).** Including the 4th same-code run: **7/28/28/28 — not stable.**
   The system *can* produce 7 or 28 on identical input/code.

2. **Bucket migration (directional + compound sum).** Sum = **18 / 36 / 37 / 34.** The
   three fresh runs are tight (±~1.5), but `222051` is half. **This rules out the "369 is
   just consolidating directionals into compounds" hypothesis** — if findings had merely
   migrated dir→compound, the sum would hold. It doesn't. In `222051` the findings are
   *absent*, not relocated. So `222051`'s low directional count is real under-production,
   not a tidy reclassification.

3. **`flagged_lp_count` (Stage 3 control).** **28 / 29 / 28 / 28 — stable.** Stage 3 LP
   flagging is deterministic. Whatever varies operates on a stable input set. ⇒ variance
   is in the synthesis layer's *clustering* of a stable set, exactly as the control was
   designed to show.

**Localization:** the variance is upstream of Pass-2, in **Pass-1 directional candidate
generation** (28/26/28 vs 3 on a stable ~28 flagged-LP set). Pass-2 matching faithfully
processed whatever Pass-1 produced in every run, so the Step 369 fix is not the cause and
is not implicated.

---

## Secondary finding (reproducible, not yet user-visible) — Eval-A Pass-2 format drift

In **all three** fresh runs, Eval-A's Pass-2 returned a single object and matched **0**
directional candidates → `all_lost=True`; the Step 369 integrity guard fired each time
(`INTEGRITY WARNING ... Possible format drift; votes lost`). Eval-B and Eval-C matched the
full 26–28, so the directional **count held at 28** and no data was lost — the guard +
B/C redundancy did their job. But one of three evaluators is silently contributing **zero**
directional votes whenever the candidate set is large (it did *not* drift in `222051`,
where there were only 3 candidates). This is a real degradation of the 3-evaluator design
(it shifts agreement splits and removes a vote) even though the final count survives.
Likely the same "long Pass-2 prompt → format drift" failure mode the `gpt-5.4` notes in
`model_config.py` allude to, but here on Eval-A's model. Worth its own fix; flagged so it
isn't lost.

---

## INTEGRITY WARNING per run

- `222051`: **absent** (only 3 candidates; all matched; guard correctly silent).
- `s370r1`: **present** — Eval-A 1 object / 0 of 28 matched.
- `s370r2`: **present** — Eval-A 1 object / 0 of 26 matched.
- `s370r3`: **present** — Eval-A 1 object / 0 of 28 matched.

All `all_lost` flags for Eval-B and Eval-C were `False` in every run. The guard behaved
exactly as Step 369 intended (it fires only when an evaluator genuinely drifts).

---

## Decision (for Chat)

Per the Step 370 rule, this is the **high-variance** branch → **directional determinism
remediation becomes its own track and outranks the Overview/UI work.** A Needs Review
bucket whose directional contents range from ~7 to ~28 on identical input is not
shippable.

Recommended remediation scope (Chat to spec — **do not fix in this step**):
1. **Primary — Pass-1 directional clustering determinism.** Why does Pass-1 emit ~28
   candidates most of the time but ~3 occasionally on a stable flagged-LP set? Suspects:
   evaluator non-determinism despite temp 0, a clustering threshold sensitive to small
   wording differences, or a single evaluator's Pass-1 round occasionally under-returning.
2. **Secondary — Eval-A Pass-2 format drift.** Reproducible in the high-candidate regime;
   currently masked by the guard + B/C. Fix the prompt/parse so A's votes survive.

Open question worth one more cheap measurement before locking the spec: **n is small (3
fresh + 1 outlier).** If Chat wants the outlier *frequency* characterized, a handful more
runs would tell us whether the ~3-candidate collapse is ~1-in-4 or rarer. My read: the
outlier is severe enough (sum halved) to justify the track regardless of frequency.

Architecture-doc note (Chat's call): the directional/compound split is matching-dependent,
and Pass-1 candidate count — not Pass-2 — is the determinism-critical step.

---

## Scope / git

- No changes to any pipeline or detection code. Diagnostic scripts + 3 keyed runs + this
  status file only.
- Pre-existing uncommitted change `05 Lease Analyzer/app/config.py` (a Step 369
  reload-trigger comment, `# Step 369: trigger uvicorn --reload ...`) was **left
  untouched** — not mine, out of scope.
- Artifacts: `05 Lease Analyzer/_step370_run3x.py` (driver),
  `05 Lease Analyzer/_step370_audit.py` (audit), `05 Lease Analyzer/_step370_run.log`
  (full stdout of the 3 runs). Fresh run dirs: `results/lease_review_*_s370r{1,2,3}`.
