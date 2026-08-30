# Step 491 — Abort rate: 0 of 5. Panel intact. Harness proven on its first real invocation.

**Date:** 2026-08-30 · **Instruction:** `build_log/491_chat_instruction.md`
**Panel verified BEFORE spending. 3/3 runs completed, 0 aborts, 0 gate retries, 0 degradation.**
**Nothing tuned.** All three results persisted with censuses. **Not deployed.**

---

## PRE-FLIGHT — the panel is intact, all three roles

One call per role through the real path — `ModelTarget` → `ProviderRouter([target], RouterConfig())`
→ `router._get_adapter(provider)` → `adapter.call(...)`, mirroring
`lease_coverage_305._do_single_call`:

```
  role A  anthropic  OK  claude-sonnet-4-6   2.77s  usage={'output_tokens': 4, 'input_tokens': 27}
  role B  openai     OK  gpt-5.5             3.01s  usage={'output_tokens': 17, 'reasoning_tokens': 7}
  role C  xai        OK  grok-4.3            1.41s  usage={'output_tokens': 1, 'reasoning_tokens': 156}

PANEL INTACT -- all three roles served by their primary model.
```

**No role fell back. No HALT.** The Anthropic condition that substituted role A on both Step-487
deployed runs has cleared. **This does not date its onset or name its cause** — Step 488 Correction 3
established no onset is recoverable, and `_classify_failure` never persisted the raw error. It
establishes only that Anthropic served at 2026-08-30 ~15:10 UTC.

Recorded because it is checkable and was not obvious: **role A's declared own-chain fallback is
`anthropic:claude-haiku-4-5`, not `gemini-2.5-pro`.** The substitution seen in Step 487 therefore came
from a shared pool beyond `own_chain` (`lease_coverage_305:690`, `"pool/{model}"`), not from role A's
declared chain. Not investigated further.

---

# 1. COMPLETIONS VS ABORTS — 0 aborts in 5 observations

| observation | source | result | gate attempts | aborts |
|---|---|---|---|---|
| local_01 | Step 491 | **completed** | 1 | 0 |
| local_02 | Step 491 | **completed** | 1 | 0 |
| local_03 | Step 491 | **completed** | 1 | 0 |
| dep_atlas_1 | Step 487 | completed | n/a | 0 |
| dep_atlas_2 | Step 487 | completed | n/a | 0 |

**5 of 5 completed. 0 aborted. No LP triggered the extraction-completeness gate on any run —
`extraction_completeness_failed_lps: []` and `completeness_failures: []` on all five.**

**Every local run completed on its first attempt.** The four-attempt allowance was never used; the
retry path added to the harness this step is therefore **untested against a real abort**.

**Against the pre-seam prediction of ~72%** (Step 484: LP-12's extraction bucket empty in 13 of 18
extractions), this is the measurement that was missing. Step 484 argued the mechanism was structural
rather than probabilistic — LP-12's bucket emptiness became irrelevant to the gate once the seam
exemption landed. **Five observations are consistent with that and do not prove it.** A 0/5 result
bounds the true rate loosely: the upper 95% bound on an unobserved event in 5 trials is about 45%.
**This is not "the abort rate is zero." It is "no abort was observed in five runs."**

# 2. PROVENANCE CENSUS — clean on all three, computed automatically at write time

```
run 01: records=606 stubs=0 contra=0 events=0 distinct_ts=0 degraded=False calls=96
    role A: [('claude-sonnet-4-6', 202)]  fallback_records=0
    role B: [('gpt-5.5', 202)]            fallback_records=0
    role C: [('grok-4.3', 202)]           fallback_records=0
run 02: records=606 stubs=0 contra=0 events=0 distinct_ts=0 degraded=False calls=99
    (same three roles, same 202/202/202, 0 fallbacks)
run 03: records=606 stubs=0 contra=0 events=0 distinct_ts=0 degraded=False calls=97
    (same three roles, same 202/202/202, 0 fallbacks)
```

**Zero stubs, zero provenance contradictions, zero fallback events across 1,818 evaluator records.**
`fallback_event_kinds` is `{}` on all three — nothing to timestamp, hence `distinct_ts=0`.

**These are the first three runs in this arc measured on the actual frozen three-model panel.** Every
prior observation — both Step-487 deployed runs, and every local run of Steps 457–484 whose data no
longer exists — is either known to have run a substituted role A or cannot be checked.

**The census that misled me in Step 487 now runs automatically and returns the right answer.** No
manual census was written for this step.

# 3. SEAM LPs — LP-07 and LP-27 hold; LP-12 moves, but within its own noise

`found:IDENTICAL` compares the `elements_found` list element-by-element against local_01.

### LP-07 — byte-identical across all five observations

```
local_01/02/03, dep_atlas_1, dep_atlas_2:
  partial  5/1  spans=5  tenant_text=1957 chars  applicable  attn=True   found: IDENTICAL
```

**Five observations, two panel configurations, local and deployed: identical.**

### LP-27 — found list identical across all five; evidence volume varies

```
local_01  partial 8/1  spans=7  len= 976   found: IDENTICAL
local_02  partial 8/1  spans=9  len=1243   found: IDENTICAL
local_03  partial 8/1  spans=7  len= 976   found: IDENTICAL
dep_1     partial 8/1  spans=7  len= 976   found: IDENTICAL
dep_2     partial 8/1  spans=8  len=1043   found: IDENTICAL
```

**The verdict is stable at 8/1 on all five while the elicited evidence ranges 7–9 spans (976–1,243
chars).** More evidence did not change the outcome — including, note, the two false positives
(elements 6 and 7) which remain found on all five.

### LP-12 — the one that moves

```
local_01  review_needed  1/0  spans=13 len=2605 13.2=True   found: ['Triggering conditions for early termination right are defined']
local_02  review_needed  1/1  spans=13 len=2605 13.2=True   found: ['Triggering conditions...']  missing: ['Co-tenancy termination trigger...']
local_03  review_needed  0/0  spans=13 len=2605 13.2=True   found: []
dep_1     review_needed  0/0  spans=13 len=2605 13.2=True   found: []
dep_2     review_needed  0/0  spans=13 len=2605 13.2=True   found: []
```

**The evidence is byte-identical on all five — 13 spans, 2,605 chars, §13.2 present.** Only the
verdict moves.

*[my reading, flagged as such]* It is tempting to read 1,1,0 on the real panel against 0,0 on the
substituted one as the real Claude voting where `gemini-2.5-pro` stood in. **I am not claiming that.**
LP-12 is itself one of the 13 LPs that vary *among the three real-panel runs* — it produced 1/0, 1/1
and 0/0 on three runs of the same configuration. **Its own run-to-run variance covers the whole
difference,** and 3-vs-2 observations cannot separate a panel effect from it. The honest statement is:
**LP-12's element count is unstable at 0–1 regardless of panel, on identical evidence, and the LP-level
state is `review_needed` in all five.**

### All-LP variance across the three real-panel runs

**13 of 32 LPs differ** on `(state, found, missing)`: LP-05, 06, 09, 12, 14, 17, 19, 20, 21, 22, 24,
26, 30. Step 487 recorded 8 of 32 across two deployed runs. **These are not comparable** — three runs
give three pairwise chances to differ where two give one, so the higher count is expected and is not
evidence that the real panel is noisier.

# 4. DEGRADED MARKERS — none locally, and the Step-488 gap reconfirmed on the deployed pair

```
local_01/02/03  run_degraded=False  reason=None               invalid=False  failed_lps=[]
                banner predicate = False        (correctly -- nothing to report)

dep_atlas_1/2   run_degraded=True   reason=evaluator_fallback invalid=False  failed_lps=[]
                banner predicate = False        (INCORRECTLY -- a substituted panel, unmarked)
```

**No local run was degraded, so nothing should be shown and nothing is.** The clean path is confirmed
non-noisy: `incomplete_report_lines()` returns `None` and the web banner stays hidden.

**The same predicate, evaluated against the two deployed runs, is still False on runs that carry
`run_degraded=True`.** Step 488 §2.4 established this by tracing the consumers; this step confirms it
by evaluating the predicate against real data on both configurations side by side. **The open item
stands unchanged and unfixed.**

# 5. COST

| run | calls | pipeline elapsed | wall elapsed |
|---|---|---|---|
| local_01 | **96** | 745.6s | 1238.4s |
| local_02 | **99** | 743.5s | — |
| local_03 | **97** | 787.5s | — |
| dep_atlas_1 | 98 | 944.3s | — |
| dep_atlas_2 | 98 | 902.3s | — |

**Total spend this step: 292 pipeline calls + 3 probe calls = 295.**

Call count varies 96–99 across runs of identical configuration. Local pipeline time (743–788s) is
consistently **~150–200s faster than deployed** (902–944s).

**`elapsed_sec` (745.6s) and harness wall time (1238.4s) differ by ~493s on run 01.** `elapsed_sec` is
the adapter's own pipeline timer and excludes the document gate and single-doc extraction (86.9s
observed for extraction alone on run 1). **The remainder is not accounted for by anything I measured**
— recorded as an open discrepancy, not explained.

# 6. PERSISTENCE — all three, with censuses

```
build_log/runs/491_atlas-modec_20260830_151208/
    index.json            git HEAD 0fb6c06fd8db, all six flags, per-run rows
    run_01_full.json      1,348,026 bytes
    run_01_census.json
    run_02_full.json
    run_02_census.json
    run_03_full.json      1,344,916 bytes
    run_03_census.json
```

**This was `run_mode_c.py`'s first real invocation and it worked.** Full results persisted, censuses
computed automatically, `index.json` carrying git HEAD and all six flags
(`SPAN_EVIDENCE_ENABLED=true`, `SPAN_EVIDENCE_LPS=[LP-07,LP-12,LP-27]`,
`SECTION_EXPANDED_SPAN_LPS=[]`, `GATE_ABORT_RETURNS_DEGRADED=true`,
`DEGRADABLE_APPLICABILITY=[not_applicable,unclear]`, `ENTAILMENT_TEST_LPS=[LP-27]`).

**Payloads are not committed** (~1.35 MB each) per `build_log/runs/README.md`. They are on disk and
re-auditable — which is the whole point of Step 490, and the thing Steps 457–484 cannot offer.

The adapter also wrote its own copies to `05 Lease Analyzer/results/s491_atlas_r0N_a1/` and appended to
`telemetry/runs.jsonl`. Not staged.

---

## FOUND EN ROUTE — a dead model id in a live path

Three times, once per run:

```
[lease_gate] Gate check failed (non-fatal): anthropic_error: NotFoundError: Error code: 404 -
  {'type': 'not_found_error', 'message': 'model: claude-sonnet-4-20250514'}
```

`cam/adapters/lease_review/lease_gate.py:49`:

```python
        gate_model = cfg.get("gate_model", "claude-sonnet-4-20250514")
```

**The document-classifier gate's default model no longer exists at Anthropic.** It is non-fatal —
`is_lease=True` still returned in 0.2–0.87s — so the gate is running on its fallback on every single
run, and has been for as long as that id has been retired.

`model_config.py:68` compounds it: `"claude-sonnet-4-20250514": "Claude Sonnet 4.6"` — **a label map
that names a current model for a retired id.** Same class as the Step 488 §1 defect: a field asserting
an identity that does not hold.

**Not fixed.** It is outside this step's brief and touches `cfg` defaults. Recorded as an open item.

---

## WHAT IS NOT ESTABLISHED

- **The abort rate.** 0 of 5 is an observation, not a rate. Upper 95% bound ≈45%.
- **The gate-retry path.** Added this step, never exercised — no run aborted.
- **Any panel effect on LP-12.** Confounded by LP-12's own 0–1 instability across identical-evidence
  runs of the same configuration.
- **divall.** Not run this step. Still never completed deployed.
- **Whether the ~493s wall/pipeline gap is gate+extraction alone.** Unexplained.
- **Why role A fell back to `gemini-2.5-pro`** in Step 487 when its own chain declares
  `claude-haiku-4-5`. Shared-pool path not traced.
- **Deployed behaviour on the intact panel.** These three runs are local. The deployed service has
  never been observed running the frozen panel.
