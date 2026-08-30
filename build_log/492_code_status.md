# Step 492 — divall aborts 4/4, and the cause is LP-16/LP-17, not LP-12

**Date:** 2026-08-30 · **Instruction:** `build_log/492_chat_instruction.md`
**Panel verified intact before spending.** **1 run, 4 attempts, 4 aborts, 0 completions.**
**Nothing tuned. Not deployed.** Tests **359 passed**.
**A harness gap was exposed by this run and fixed within it.**

---

## THE ANSWER: a second, deterministic abort cause exists, and it is not the one that was fixed

| LP | failed on | verdict |
|---|---|---|
| **LP-16** | **4 of 4 attempts** | **DETERMINISTIC** |
| **LP-17** | **4 of 4 attempts** | **DETERMINISTIC** |
| LP-07 | 2 of 4 attempts | shape-variant |
| **LP-12** | **0 of 4 attempts** | **seam exemption held** |

**LP-12 — the cause of every Atlas abort and the whole target of Steps 481–484 — did not cause a
single abort here.** It was seam-exempt on 3 of 4 attempts and absent from the failure set on the
fourth. **That fix works and this run confirms it on the harder fixture.**

**But divall has a different abort cause that retrying cannot clear.** LP-16 and LP-17 failed on
every attempt. That is not extraction shape variance — four independent extractions produced the same
two failures.

**The four-attempt allowance was the right test and it settled the question:** the earlier divall
result (Step 484: abort on attempt 1, completion on attempt 2) was **luck**, not a rate. With four
attempts we can now say the deterministic residue is LP-16 + LP-17.

## 1. Completions vs aborts, and on which LPs

**0 completions / 4 attempts.** Per attempt, from the gate's own log lines:

```
attempt 1  must_abort=['LP-07','LP-16','LP-17']  seam_exempt=['LP-12']  degradable=['LP-30','LP-31','LP-32']
attempt 2  must_abort=['LP-16','LP-17']          seam_exempt=['LP-12']  degradable=['LP-30','LP-31','LP-32']
attempt 3  must_abort=['LP-16','LP-17']          seam_exempt=[]         degradable=['LP-30','LP-31','LP-32']
attempt 4  must_abort=['LP-07','LP-16','LP-17']  seam_exempt=['LP-12']  degradable=['LP-30','LP-31','LP-32']
```

Applicability, unchanged across attempts: **`LP-16: applicable`, `LP-17: required`** — neither is in
`DEGRADABLE_APPLICABILITY = {not_applicable, unclear}`, so neither can degrade. **LP-30/31/32 are
`unclear` and degrade correctly on all four.**

**The seam-aware gate behaved exactly as designed on every attempt.** On attempt 3 `seam_exempt=[]`
because LP-12's elicitation produced no spans that time — and LP-12 correctly did **not** appear in
`must_abort` either, because its bucket was non-empty. The Step-484 design point (exemption is
conditional on *production*, not membership) held under four independent draws.

**`[span_evidence] LP-07 produced no verified spans; falling back` on all four attempts.** LP-07's
elicitation fails on divall every time — consistent with Steps 478 and 484 — so it is never exempt.
It reaches `must_abort` only when its extraction bucket is *also* empty, which happened on 2 of 4.

## 2. Provenance census

**None. The run produced no result, so there is nothing to census.** `run_01_census.json` does not
exist; the index row is `outcome: EXCEPTION`.

The panel was verified intact immediately before the run:

```
role A  anthropic  OK  claude-sonnet-4-6  2.51s
role B  openai     OK  gpt-5.5            3.78s
role C  xai        OK  grok-4.3           1.60s
PANEL INTACT
```

**No claim is made about panel behaviour during the run** — the abort happens at the extraction gate,
before the 305 evaluator layer, so no evaluator records were produced on any attempt.

## 3. Seam LPs vs prior divall observations

**Not comparable — there is no coverage result.** The gate aborts before coverage runs.

Prior divall observations, for the record (from `478_code_status.md` / `484_code_status.md`; **those
runs are not persisted**, so these are status-file figures, not re-derivable data):

| | 478-divall | 484-divall (attempt 2) | **492-divall** |
|---|---|---|---|
| LP-07 | `missing` 0/6, 0 spans (fell back) | `missing` 0/6, 0 spans (fell back) | **no result** |
| LP-12 | `not_applicable` "absent by design" | `partial` 2 found, 4 spans | **no result** |
| LP-27 | `partial` 8/0, 3 spans | `partial` 6/0, 3 spans | **no result** |

## 4. Degraded markers and user surfaces

**Not applicable, and that is itself the point.** A `GateAbortError` that exhausts its attempts
produces **no result at all** — not a degraded one. So:

- there is no `run_degraded` flag, no `degraded_reason`, no `invalid_for_legal_analysis`;
- `incomplete_report_lines()` is never called, because there is no result to pass it;
- in the deployed app this path is what Step 476 converted to a *degraded continuation* — but only
  for LPs whose applicability permits degrading. **LP-16 (`applicable`) and LP-17 (`required`) do not
  qualify, so the deployed app would fail this job too**, not mark it incomplete.

**Consequence worth stating: divall is currently unprocessable, locally or deployed.** Step 476's
degraded-continuation work does not rescue it, because the failing LPs are precisely the
non-degradable ones.

## 5. Calls and elapsed

**869.3s wall across four attempts. `api_calls_total` is unavailable** — the counter lives on the
result, which never existed. The calls spent were extraction plus span elicitation for the seamed LPs
on each attempt, discarded four times.

**This is the ordering cost Step 484 named and measured once (257s on one aborted attempt); here it
compounds ×4.** Elicitation runs *before* the gate, so every aborted attempt pays for spans it throws
away.

## 6. Persistence — and the gap this run exposed

```
build_log/runs/492_divall-modec_20260830_162602/
    index.json                              (3,386 bytes -- outcome EXCEPTION + traceback)
    run_01_gate_aborts.RECONSTRUCTED.json   (backfilled, see below)
```

**The harness persisted no result, correctly — there was none.** But it also persisted **only the
final attempt's error.** The per-attempt history (`_harness_gate_aborts`) is attached to the
*result*, so on a total abort it had nowhere to live and **survived only in stdout.**

**That is the Step 489/490 failure class recurring inside the fix for it.** Attempts 1–3 — including
the fact that LP-16/LP-17 failed on every one, which is the entire finding of this step — would have
been lost the moment the console scrolled.

### Fixed within this step

- `run_store.run_and_persist` gained an `on_dir` callback, invoked as soon as the run directory
  exists, so a harness can write failure evidence when no result will ever be produced.
- `run_mode_c` now writes `run_NN_gate_aborts.json` with every attempt's message **and a parsed
  `failed_lps` list** before re-raising.
- **Verified without spending:** a fake always-aborting `fn` produced
  `files written: ['index.json', 'run_01_gate_aborts.json']` with both attempts recorded.

### The backfill is marked as reconstructed

`run_01_gate_aborts.RECONSTRUCTED.json` carries the four attempts recovered from stdout, with a
`_provenance` field saying so verbatim. **It was not produced by the harness at run time.** Attempt
4's message independently survives in `index.json`; attempts 1–3 rest on the console log.

---

## WHAT THIS CHANGES ABOUT THE ABORT PICTURE

| fixture | observations | aborts |
|---|---|---|
| **Atlas** | 3 local (Step 491) + 2 deployed (Step 487) | **0 of 5** |
| **divall** | 1 run × 4 attempts (Step 492) | **4 of 4** |

**The two fixtures are not converging.** Atlas's sole abort cause was LP-12 and it is gone. divall
has LP-16/LP-17 failing deterministically, and nothing in Steps 476–484 addresses them: they are not
seamed, not degradable, and not shape-variant.

**Step 491's "0 of 5" was correctly bounded as an Atlas result. This step shows why that bound
mattered** — five Atlas runs said nothing about a document whose failing LPs are different ones.

## WHAT IS NOT ESTABLISHED

- **Why LP-16 and LP-17 extract empty on divall.** Not investigated. Whether the lease genuinely
  lacks that content, whether extraction mis-assigns it, or whether their `activation_clues` miss
  divall's phrasing (the LP-12 defect Step 481 fixed) is **unknown and untested.**
- **Whether LP-16/LP-17 should be degradable.** That is an applicability question, not a bug report.
  `LP-17: required` in particular is a deliberate classification.
- **divall's abort rate as a rate.** One run of four attempts. The 4/4 is strong for
  *this* extraction distribution but rests on a single session.
- **Whether any other fixture behaves like divall.** Only Atlas and divall have been run under this
  configuration. `atreca` has not.
- **divall deployed.** Not authorized this step, not attempted, still never completed deployed.
