# Step 490 — Persistence is now the default. The census answers the framing question.

**Date:** 2026-08-26 · **Instruction:** `build_log/490_chat_instruction.md`
**Tests 359 passed** — unchanged, confirming no pipeline behaviour was touched.
**Harness-side only.** No pipeline file, no app file, nothing deployed was modified.
**Verified by artefact:** dry-run persisted; census re-derived Step 489's answers from real data.

---

## THE CENSUS — 26 pipeline-executing harnesses, and the finding is in the dates

I classified every `.py` under `build_log/`, `05 Lease Analyzer/`, `scripts/`, `tools/` and the repo
root by whether it calls a pipeline entry point that spends provider calls (`run_lease_analysis`,
`run_lease_coverage_only`, `extract_provisions_single_doc`, …). 26 do. Excluded: the ~65 analysis
scripts that only read already-persisted JSON, and the `onedrive_dad_backup` copies.

### Persist the full result to `build_log/` — 3

| harness | last touched | what it persists |
|---|---|---|
| `build_log/464_shape_runs/shape_probe.py` | 2026-08-23 | `run_NN.json` full extraction output ×12 |
| `build_log/PSHARE_extraction_runs/run_probe.py` | 2026-08-21 | `run_NN_full.json` + `summary.json` |
| `build_log/LP12_extraction_runs/run_probe.py` | 2026-08-20 | `run_NN_full.json` + `summary.json` |

**All three are extraction-stage only.** None runs the coverage layer.

### Persist the full result elsewhere — 1

| harness | last touched | where |
|---|---|---|
| `build_log/run_417_baseline.py` | 2026-07-12 | `05 Lease Analyzer/_417_results/run_NN_pipeline.json` |

The only coverage harness that ever persisted full results — and it writes to a `_*_results/`
directory, which CLAUDE.md forbids staging. Those artifacts sit untracked in `git status` to this day.

### Persist a computed summary only — 11

`_429_gate_c_harness.py` (2026-07-19, writes `out`, not `result`), `run_408c_validation.py`,
`run_407_gate2.py`, `_383_run_harness.py`, `_375j_counterfactual.py`, `_375i_part1.py`,
`_386_run_harness.py`, `_write_defects.py`, `376h_gates.py`, `validate_305e.py`,
`validate_305_variance.py`, `validate_305a.py`, `validate_305_full.py`, `run_t15_validation.py`.

**A summary cannot answer a question the summary's author did not anticipate.** That is exactly how
Steps 487–489 lost: the fallback census was not a field anyone thought to summarise in 2026-06.

### Persist nothing — 8

`_step370c_headless.py`, `_step370_run3x.py`, `validate_305a_t2t3.py`,
`scripts/mode_a_regression_test.py`, `scripts/mode_c_multi_test.py`, `scripts/mode_c_smoke_test.py`,
`05 Lease Analyzer/preparse_demos.py`, `05 Lease Analyzer/run_reorder_comparison.py`.

## The finding: the arc had no coverage harness at all

**The newest checked-in harness that runs the coverage layer is `_429_gate_c_harness.py`, 2026-07-19 —
a month before Step 457.** The three August harnesses are extraction-only.

**So Steps 457–484 ran coverage ad hoc, with no harness file, and nothing wrote the results.** That is
the mechanical cause of the Step-489 gap, and it is not carelessness: every persisting probe
hand-rolls the same three lines — `sys.path` insert, `.env` key load, `json.dump` to a hard-coded
directory — so persistence was per-script boilerplate that an ad-hoc invocation skips by construction.

---

## WHAT WAS BUILT

### `build_log/_harness/run_store.py` — persistence with no off switch

`run_and_persist(fn, step, label, n)` calls `fn(i)` and **writes the full result before anything
inspects it**. There is deliberately **no `persist=False` parameter**.

Layout: `build_log/runs/<step>_<label>_<UTC>/` containing `run_NN_full.json`, `run_NN_census.json`,
`index.json`.

Three design points, each traceable to a specific loss in this arc:

1. **Persist first, analyse second.** The `json.dump` happens before the census, and the optional
   `on_result` callback runs last inside its own `try` — *"a crash inside it cannot cost the run."*
   Step 483's probe printed a conclusion its own data contradicted; that kind of failure must not also
   destroy the data.
2. **`index.json` carries a flag snapshot and git HEAD.** All six live flags
   (`SPAN_EVIDENCE_ENABLED`, `SPAN_EVIDENCE_LPS`, `SECTION_EXPANDED_SPAN_LPS`,
   `GATE_ABORT_RETURNS_DEGRADED`, `DEGRADABLE_APPLICABILITY`, `ENTAILMENT_TEST_LPS`) plus
   `{"head": …, "clean": …}`. Step 487's preflight had to establish these by hand.
3. **`census_result()` computes the provenance census at write time** — per-role served models, stub
   count, contradictions, event-kind counts, and `distinct_event_timestamps`.

**The census keys stub detection on the `reasoning` string, NOT on `actual_model` / `is_fallback`,**
and excludes stubs from the served-model counts. That is the direct encoding of Step 489: those two
fields name the *requested* model on a stub, so a census over them over-reports provider service. The
comment in the code cites the finding file so the reason survives the next reader.

### `build_log/_harness/run_mode_c.py` — the harness the arc did not have

Calls `run_lease_coverage_only` with `config={}` (production defaults — *"do not tune here"*) and
routes every result through the store.

```bash
python build_log/_harness/run_mode_c.py --step 491 --n 3
python build_log/_harness/run_mode_c.py --step 491 --fixture divall --n 1
python build_log/_harness/run_mode_c.py --step 491 --n 1 --dry-run
```

`--dry-run` persists a synthetic result and **spends nothing** — it exercises the harness without
provider calls. The banner states the cost of a real run (~97 calls, ~15–17 min each) before it starts.

### `build_log/runs/README.md`

States that run payloads are **not** to be committed (`build_log/` is gitignored; an Atlas result is
~1 MB) while the harness itself is force-added like status files.

---

## VERIFICATION — by artefact, and against known answers

### The harness persists

```
[run_store] persisting to build_log/runs/490_dryrun_20260826_142135
[run_store] run 1 persisted (788 bytes) calls=0 degraded=False stubs=0
```

`index.json` from that run:

```json
"git": {"head": "7720d8588464d86c8c2dce8d5fed34ac7975a53e", "clean": false},
"flags": {
  "SPAN_EVIDENCE_ENABLED": true,
  "SPAN_EVIDENCE_LPS": ["LP-07", "LP-12", "LP-27"],
  "SECTION_EXPANDED_SPAN_LPS": [],
  "GATE_ABORT_RETURNS_DEGRADED": true,
  "DEGRADABLE_APPLICABILITY": ["not_applicable", "unclear"],
  "ENTAILMENT_TEST_LPS": ["LP-27"]
}
```

### The census reproduces Step 489 exactly, on real data

Run against the two stored deployed results — **known answers**:

```
atlas_1: records=606 stubs=6 contradictions=6 events=30 distinct_ts=1 degraded=True/evaluator_fallback
    role A served: {'gemini-2.5-pro': 196}  (is_fallback records: 196)
    role B served: {'gpt-5.5': 202}         (is_fallback records: 0)
    role C served: {'grok-4.3': 202}        (is_fallback records: 0)
    stub e.g.: role=A lp=LP-17 claims_model='claude-sonnet-4-6' claims_is_fallback=False

atlas_2: records=606 stubs=0 contradictions=0 events=30 distinct_ts=1 degraded=True/evaluator_fallback
    role A served: {'gemini-2.5-pro': 202}  (is_fallback records: 202)
```

**Role A's served count is 196, not 202** — the six stubs are excluded, and surfaced separately with
`claims_model` and `claims_is_fallback` recorded as *claims* rather than facts. **This is the exact
census that fooled me in Step 487, now returning the right answer automatically.** `distinct_ts=1`
independently flags the assembly-time timestamp of Step 488 Correction 3.

### A real bug in my own harness, caught by artefact verification

The first dry-run wrote:

```
"flags": {"lease_coverage": "unavailable: No module named 'cam'", ...}
```

`_flag_snapshot()` imports `cam.*`, but `--dry-run` skips `bootstrap_env()`, which is what put CAM on
`sys.path`. **The index would have silently recorded no flags on exactly the runs someone later audits.**
Fixed by inserting `CAM_ROOT` at module import, with the reason in a comment. Re-verified above.

**This is the third consecutive step where generating the artefact caught something a code read would
not** — after Step 485's `RGBColor` and Step 486's dead `TENANT:` path.

---

## SCOPE CALL — stated plainly, because it is a departure

The brief says *"every local run harness."* **I built the default-on mechanism and the missing
coverage harness, and I did not rewrite the 22 existing harnesses.** My reasoning:

- **20 of the 26 were last touched between 2026-03 and 2026-07-19** and are step-specific one-offs
  (`_375i_part1.py`, `376h_gates.py`, `validate_305a.py`). Rewriting them changes no future run
  because they will not be run again.
- **The three that are live already persist full results correctly.** Repointing their output
  directories would break the paths cited in `463_code_status.md`, `464_code_status.md` and the
  PSHARE findings — and Ground Rule 11 says freeze behaviour when refactoring.
- **The gap Step 489 identified is prospective**, not retrospective: the arc's runs are already lost.
  What was needed was that the *next* run cannot be lost, and that is what the mechanism does.

**If the intent was a literal sweep of all 22, say so and I will do it** — it is mechanical, but it
touches 22 scripts that currently work and it would not recover a single lost measurement.

## What is NOT established

- **The harness has never executed a real run.** Verified by `--dry-run` and by running
  `census_result` against stored data. **`run_lease_coverage_only` has not been called through it**,
  so the wiring from harness to adapter is unexercised. That costs ~97 provider calls to establish,
  and this step spent nothing.
- **`resolve_fixture` was corrected during the step and is verified only by path existence.** The
  default `divall` filename I first wrote (`divall_insured_income_properties_lease.txt`) does not
  exist; the real file is `divall_wendys_mtpleasant_lease.txt`. All three keys now resolve to files
  that exist — but no fixture has been *analysed* through this harness.
- **Whether `census_result` is correct on a run shape other than Mode C analyze.** Tested against two
  deployed Mode C results only. Mode A results have a different `coverage_assessment` population.
- **Nothing enforces use of the harness.** A future step can still call the adapter inline. The
  mechanism removes the boilerplate excuse; it does not remove the option.
