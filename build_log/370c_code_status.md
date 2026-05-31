# Step 370c — Execution-path correlation triage (directional collapse)

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Diagnostic only. No fixes, no behavior changes.
**Git SHA:** `eaf130f` (logging add + runner scripts) on base `f6fb800` (370a-v)
**Frontend:** `app.js?v=445`
**Pipeline version:** 1.0.0 (all 6 runs)

---

## BLUF

**Outcome 4** — No directional collapse in six matched interleaved runs. Known collapse
remains instrumented but unreproduced. No path correlation evidence. Guard remains live.
→ Proceed to 370b using captured Eval-A artifacts.

**Outcome 5** — NOT triggered. Minimum total CPF across all runs was 30. Zero-CPF path
not observed.

No screenshots required (no guard-triggered run, no zero-CPF run).

---

## Run design confirmation

Six runs, Atlas Meridian warehouse lease, Mode C / analyze / tenant / landlord_property /
blank_template, all on SHA `eaf130f`, all identical file (md5 `d679f2c303f8dd6334b207f106b125f0`).
Interleaved per instruction (W→H, H→W, W→H).

**One permitted add (logging only, no behavior change):** `[pass2_raw_dump]` print of
Eval-A's raw Pass-2 response (first 3000 chars, raw_len, md5) and `[pass1_prompt_hash]`
md5 of the Stage 7 Pass-1 user prompt — both in `lease_synthesis.py`, stdout only,
zero logic change.

---

## Full per-run artifact table

| Field | W1 | H1 | H2 | W2 | W3 | H3 |
|---|---|---|---|---|---|---|
| **run_id** | `8ca215` | `370c_H1` | `370c_H2` | `d117b6` | `70f97d` | `370c_H3` |
| **execution_path** | web | headless | headless | web | web | headless |
| **pair / order** | 1-1 | 1-2 | 2-1 | 2-2 | 3-1 | 3-2 |
| **git_sha** | eaf130f | eaf130f | eaf130f | eaf130f | eaf130f | eaf130f |
| **frontend_version** | v=445 | n/a | n/a | v=445 | v=445 | n/a |
| **pipeline_version** | 1.0.0 | 1.0.0 | 1.0.0 | 1.0.0 | 1.0.0 | 1.0.0 |
| **fixture md5** | d679f2c3 | d679f2c3 | d679f2c3 | d679f2c3 | d679f2c3 | d679f2c3 |
| **perspective** | tenant | tenant | tenant | tenant | tenant | tenant |
| **stage7_models** | A=claude-sonnet-4-6, B=gpt-5.4, C=grok-4.3 | same | same | same | same | same |
| **pass1_prompt_hash** | (server log) | dcf54a2c | e0a0aafcb | (server log) | (server log) | 7575f8cf |
| **pass1_prompt_len** | (server log) | 42392 | 42274 | (server log) | (server log) | 42105 |
| **flagged_lp_count** | 28 | 28 | 28 | 28 | 28 | 28 |
| **directional_pass1_candidate_count** | 28 | 28 | 28 | 22 | 26 | 24 |
| **directional_pass2_matched_count (B+C)** | 28 | 28 | 28 | 22 | 26 | 24 |
| **directional_final_count** | 28 | 28 | 28 | 22 | 26 | 24 |
| **candidate_density** | 1.0 | 1.0 | 1.0 | 0.786 | 0.929 | 0.857 |
| **total_cpf_count** | 34 | 34 | 33 | 30 | 33 | 34 |
| **compound_cpf_count** | 6 | 6 | 5 | 8 | 7 | 10 |
| **directional_synthesis_status** | complete | complete | complete | complete | complete | complete |
| **directional_guard.triggered** | False | False | False | False | False | False |
| **directional_guard.reason_code** | null | null | null | null | null | null |
| **banner_rendered** | n/a | n/a | n/a | n/a | n/a | n/a |
| **evalA_returned_object_count** | 1 | 1 | 36 | 31 | 1 | 1 |
| **evalA_matched_item_count** | 0 | 0 | 28 | 22 | 0 | 0 |
| **evalA_all_lost** | True | True | **False** | **False** | True | True |
| **pass2_raw_A dir_verdicts** | {} | {} | {confirmed:28} | {confirmed:20, no_mm:2} | {} | {} |
| **pass2_raw_B dir_verdicts** | {no_mm:16,conf:8,unc:4} | {conf:18,no_mm:6,unc:4} | {unc:5,conf:22,no_mm:1} | {conf:14,unc:8} | {no_mm:13,conf:8,unc:5} | {conf:23,unc:1} |
| **pass2_raw_C dir_verdicts** | {confirmed:28} | {confirmed:28} | {confirmed:28} | {confirmed:22} | {confirmed:26} | {confirmed:24} |
| **INTEGRITY WARNING** | (server log) | **present** | absent | (server log) | (server log) | **present** |

`run_id` column shows last 6 chars of job ID; full IDs: W1=`lease_review_20260531_031342_8ca215`, H1=`lease_review_20260530_231425_370c_H1`, H2=`lease_review_20260530_233514_370c_H2`, W2=`lease_review_20260531_033520_d117b6`, W3=`lease_review_20260531_035647_70f97d`, H3=`lease_review_20260530_235847_370c_H3`.

**Hash/path columns not captured:** `raw_response_path_per_evaluator`, `request_hashes`,
`retry/fallback/exception_per_evaluator`. Raw Eval-A responses are in the headless run
logs as `[pass2_raw_dump] Eval-A` lines (first 3000 chars + md5). Web-run Pass-2 raws
go to server stdout, which was not piped to a log in this session. No retries or
fallbacks fired in any run (all evaluators completed on primary model).

---

## Outcome determination (applied mechanically)

**Outcome 1 (collapse in both paths):** NO — no collapse in any run (minimum Pass-1
candidates = 22, well above guard threshold of 5).

**Outcome 2 (collapse only in web runs):** NO.

**Outcome 3 (collapse once in one path):** NO.

**Outcome 4 — TRIGGERED — No collapse in six runs.**
Known collapse remains instrumented but unreproduced under six matched runs. No path
correlation evidence. NO claim of stability or remediation.
→ Proceed to 370b using captured Eval-A artifacts. Keep 370a guard live.

**Outcome 5 (zero total CPFs):** NOT triggered. Minimum total CPF = 30 (W2). No
zero-CPF early-bail path observed. No screenshots required.

---

## Eval-A raw behavior — VARIES

**Answer to the 370c gating question: Eval-A malformation is INCONSISTENT / VARIES.**

| Run | Path | evalA_n_obj | evalA_matched | all_lost |
|---|---|---|---|---|
| W1 | web | 1 | 0 | **True** |
| H1 | headless | 1 | 0 | **True** |
| H2 | headless | 36 | 28 | False |
| W2 | web | 31 | 22 | False |
| W3 | web | 1 | 0 | **True** |
| H3 | headless | 1 | 0 | **True** |

- 4/6 runs: all_lost=True (1 object returned, 0 Dir- matched)
- 2/6 runs: all_lost=False (correct — 31–36 objects, all Dir- matched)
- **No path correlation:** web = 2/3 all_lost, headless = 2/3 all_lost. Symmetric.
- **No candidate-count correlation:** all_lost=True appears at 28 (W1, H1), 26 (W3),
  24 (H3); all_lost=False at 28 (H2) and 22 (W2). Count is not the driver.

**Malformation characterisation (from `[pass2_raw_dump]` headless logs):**

When all_lost=True (H1, H3):
- Raw response starts identically to the working case: `[\n  {\n    "candidate_id": "CRX-01"...`
- raw_len = 28–29K chars (not empty, not truncated — same order of magnitude as working runs)
- `synth_debug` shows: `1 objects | by candidate_type={}`
- The `by candidate_type={}` is significant: it means the single parsed item is **NOT a
  dict** (Counter only counts dicts). The `n_objects=1` comes from `len(verdicts)` where
  `verdicts` is the list returned by `_try_call`.
- Inference: `_safe_parse_synthesis` extracts a list whose single element is itself a
  list (nested-array wrapping). Candidate mechanism: claude-sonnet-4-6 occasionally wraps
  its JSON array in an outer array `[[{...}, ...]]`. `json.loads` then returns `[inner_list]`
  — a 1-element list of a list, not a list of dicts. The inner list is the actual content.
  **This hypothesis requires full-response inspection to confirm (370b scope).**

When all_lost=False (H2, W2): raw_preview starts identically, but the parsed result is a
proper flat list of dicts (36 or 31 objects). The `_safe_parse_synthesis` path succeeds
without the wrapping artifact.

**Raw Eval-A Pass-2 evidence artifacts for 370b:**
- H1: `[pass2_raw_dump] Eval-A ... md5=b6f76e88 raw_len=29177` in `_370c_H1.log`
- H2: `[pass2_raw_dump] Eval-A ... md5=346500bf raw_len=27087` in `_370c_H2.log`
- H3: `[pass2_raw_dump] Eval-A ... md5=2eda0840 raw_len=28531` in `_370c_H3.log`
- All headless logs preserved under `05 Lease Analyzer/`.
- Web runs: Pass-2 raw in server stdout (not captured to file in this session).

---

## Key additional finding — Pass-1 prompt is NOT identical across runs

The `[pass1_prompt_hash]` logging reveals Stage 7's Pass-1 user prompt varies run-to-run
despite identical input file:

| Run | Pass-1 md5 | len |
|---|---|---|
| H1 | dcf54a2c | 42,392 |
| H2 | e0a0aafcb | 42,274 |
| H3 | 7575f8cf | 42,105 |

The prompt includes Stage 5 coverage assessment output (LP states, element details, partial
coverage reasoning). Stage 5 is non-deterministic — each run produces slightly different
element verdicts and reasoning text, which propagates into the Stage 7 prompt. **This means
Stage 7 is NOT receiving identical inputs across runs.** The Pass-1 candidate count
variation (22 / 24 / 26 / 28 / 28 / 28) is partly or wholly explained by different Stage 5
outputs feeding different Pass-1 prompts. This is an independent finding from the
directional collapse question — upstream non-determinism is present and must be factored
into any root-cause analysis of Pass-1 variance.

---

## Guard live-system behaviour

The 370a guard was LIVE in all six runs (confirmed by `directional_guard` present in every
`synthesis_meta`). The guard correctly evaluated to `complete` / `triggered=False` in all
runs — because no run had Pass-1 candidates ≤ 5. The guard has not produced a false
positive in six runs on a realistic Atlas Meridian run. Low-candidate case (22) was
correctly classified as `complete` (22 > 5).

---

## Integrity WARNING pattern

In all 4 all_lost=True runs, the INTEGRITY WARNING message fired:
> `INTEGRITY WARNING: Pass2 Eval-A returned 1 objects but 0 matched N directional
> candidates — all defaulted to 'unclear'. Possible format drift; votes lost.`

In the 2 all_lost=False runs, no INTEGRITY WARNING. The guard is working as designed —
it fires exactly when Eval-A's votes are lost and is silent when they aren't.

---

## Scope confirmation

**IN:** six matched runs, full artifact capture, guard live observation, path-correlation
read, Eval-A raw collection, zero-CPF watch.

**OUT:** No threshold/prompt/routing changes, no Eval-A normalization, no early-bail fix,
no auto-rerun, no behavior change. The `[pass2_raw_dump]` / `[pass1_prompt_hash]` adds
are logging-only stdout prints (committed as `eaf130f`, clearly marked `Step 370c`).

No `cam/core/` changes. No version bump.

**Do not start 370b** — this status file and table must be pasted to Chat first. Chat
applies the locked outcome rule (Outcome 4) and decides next step.

---

## Files committed under this step

- `cam/adapters/lease_review/lease_synthesis.py` — logging add only
- `05 Lease Analyzer/_step370c_headless.py` — runner (diagnostic artifact)
- `05 Lease Analyzer/_step370c_web.py` — runner (diagnostic artifact)

Run logs (gitignored, local only):
- `_370c_W1.log`, `_370c_H1.log`, `_370c_H2.log`, `_370c_W2.log`, `_370c_W3.log`,
  `_370c_H3.log` in `05 Lease Analyzer/`
