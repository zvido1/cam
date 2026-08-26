# Step 489 — Do `all_failed` stubs appear in the frozen record? No. But the arc cannot be checked.

**Date:** 2026-08-26 · **Instruction:** `build_log/489_chat_instruction.md`
**READ-ONLY.** Every file opened in mode `'r'`. No runs, no fix, **no frozen artifact modified.**
Scanner: `scan489b.py`, written to the session scratchpad, not to the repo.

---

## THE ANSWERS, UP FRONT

| source | stubs | misreporting stubs | verdict |
|---|---|---|---|
| **1. Frozen 431/447 artifacts** | **0** | **0** | **CLEAN — the defect is not in the patent record** |
| **2. Arc local runs 457–484** | — | — | **UNANSWERABLE — not persisted** |
| **2b. Arc extraction runs 463/464, LP12, PSHARE** | **0** | **0** | clean (no evaluator layer) |
| **3. Deployed atlas_1** | 6 | **6** | the only misreporting stubs found anywhere |
| **3. Deployed atlas_2** | 0 | 0 | clean |
| **Historical corpus, 149 files, 38,145 evaluator records** | 139 | **0** | stubs present, but they make **no** provenance claim |

**Is the defect new? No — the latent defect dates to 2026-05-31. Has it ever fired before? Not in any
artifact that exists. The one place it could have fired unobserved is the one place with no artifacts:
this arc's own local runs.**

---

## The mechanism, quoted — and why it is deterministic, not a race

Two failure-path return sites build the evaluator result with the **requested** model in the `model`
field. `lease_coverage_305.py:696-699`:

```python
    return {
        "role": role, "model": evaluator_cfg["model"], "provider": evaluator_cfg["provider"],
        "label": evaluator_cfg["label"],
        "completed": False, "elapsed_sec": round(elapsed, 2),
```

and again at `:785-790` for the exception path. Then `:848-863` derives the provenance fields from
that dict:

```python
        _primary_model = EVALUATOR_LINEUP_305.get(role, {}).get("model")
        _actual_model = result.get("model")
        _actual_label = result.get("label")
        _is_fallback = bool(_actual_model) and _actual_model != _primary_model
        _real_label = _actual_label or EVALUATOR_LINEUP_305.get(role, {}).get("label", f"Evaluator {role}")

        if not result.get("completed") or not result.get("element_verdicts"):
            verdicts.append({
                "role": role,
                "label": _real_label,
                "actual_model": _actual_model,
                "actual_label": _actual_label,
                "is_fallback": _is_fallback,
```

On a total failure `_actual_model` is the requested model, so `_is_fallback` evaluates
`True and (requested != requested)` → **False**, and `_real_label` is the primary's label.

**This is not a race and not intermittent. Any total failure of any evaluator produces this shape,
every time.**

Note the comment sitting directly above it at `:842-847`, from Step 372a:

> *"The displayed `label` is now the real one, not the static lineup label — this is the line that was
> previously laundering a fallback's verdict under the primary's name ("GPT-5.5")."*

**372a fixed the fallback case and left the total-failure case behind.** The stub path reads the same
`result` dict, but on that path the dict never held an answering model to begin with.

## Dating it — `git log -S`

| commit | date | what it introduced |
|---|---|---|
| `5b139e3` | **2026-05-11** | Step 305. The failure path already returned `"model": evaluator_cfg["model"]`, and the `"Evaluator {role} did not complete"` stub already existed. **No `actual_model` field existed yet.** |
| `5611fd8` | **2026-05-31** | **Step 372a.** Added `actual_model` / `actual_label` / `is_fallback`, derived from `result.get("model")`. **This is the commit that created the misreport** — before it there was no provenance claim to be false. |

**The defect has been latent for 87 days, since 2026-05-31.**

---

# 1. THE FROZEN 431/447 ARTIFACTS — CLEAN

**Read-only. File unmodified: `431_selection_measurement_sidecar.json`, 818,521 bytes, SHA-256
`c44573cb56d990afe7818dbdbfc3aa1e9586e51331a86b348b97f0e55967a9e7`,
`sanction_token = ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca`.**

Full census over `series` → `canonical_panels` + `degraded_panels` → `per_role`:

```
panels total: 36    degraded_panels total: 1        (36 x 3 = 108 role-judgments)

('canonical_panels', 'A', completed=True, is_fallback=False, canonical=True, abstained=False) -> 35
('canonical_panels', 'B', completed=True, is_fallback=False, canonical=True, abstained=False) -> 35
('canonical_panels', 'C', completed=True, is_fallback=False, canonical=True, abstained=False) -> 35
('degraded_panels',  'A', completed=True, is_fallback=False, canonical=True,  abstained=False) -> 1
('degraded_panels',  'B', completed=True, is_fallback=True,  canonical=False, abstained=False) -> 1
('degraded_panels',  'C', completed=True, is_fallback=False, canonical=True,  abstained=False) -> 1
```

Literal-string scan of all 818,521 bytes:

```
'did not complete'    -> 0 occurrences
'all_failed'          -> 0 occurrences
'"completed": false'  -> 0 occurrences
'"is_fallback": true' -> 1 occurrence
```

**`completed: true` on all 108 role-judgments. Zero stubs. Zero `all_failed`. Zero abstains.** The
other eight `431_*.json` artifacts, plus `430_gate_b_cross_lease_sidecar.json` and the two `423B/C`
smoke sidecars: **0 occurrences** of the stub signature in each.

## 1.1 The one non-canonical panel is labelled correctly — and richly

`cand_04`, role B:

```json
{
  "role": "B",
  "requested_provider": "openai", "requested_model": "gpt-5.5",
  "actual_provider": "openai",    "actual_model": "gpt-5.4",
  "actual_label": "GPT-5.4",
  "is_fallback": true,
  "canonical": false,
  "canonical_reason": "actual_provider+model==frozen_primary AND config_hash==reviewed",
  "completed": true,
  "fallback_reason": "reasoning_exhaustion"
}
```

**It names the substitute accurately (`gpt-5.4`, not `gpt-5.5`), flags `is_fallback: true`, marks
`canonical: false`, and is segregated into `degraded_panels` rather than `canonical_panels`.**

**The frozen artifact records exactly what the 305 element record fails to record.** Its `per_role`
block carries `completed`, `abstained`, `canonical`, `canonical_reason`, `fallback_reason`, and
`requested_*` separated from `actual_*` — six provenance fields the 305 element record does not have.
**A census over the frozen sidecar cannot be fooled the way the Step-487 census was.**

## 1.2 Two observations recorded, no remedy proposed

Per the instruction, neither is a proposal — both are facts a future reader should have:

- **The single fallback carries `fallback_reason: "reasoning_exhaustion"`** — the exact label Step 449
  flagged as asserting a cause the classifier does not observe. **That labelling question does touch
  the frozen record, on one of 108 judgments.** It is a *labelling* question, not a provenance or stub
  question: the panel is correctly marked non-canonical and quarantined regardless of why it fell back.
- **The one degraded panel is on `cand_04`** — the same candidate the 2026-08-20 §1 bound in
  `Docs/Patent_Current_State.md` concerns.

**Stated plainly, as instructed: the frozen artifacts are NOT affected by the stub defect.**

---

# 2. THE ARC'S LOCAL RUNS — NOT PERSISTED, THEREFORE UNANSWERABLE

**This is the finding I did not expect and the one that matters most.**

**No completed local coverage run from Steps 457–484 exists on disk.** I searched every `*.json`
modified since 2026-08-01 outside `.git` and the stale worktrees.

The only August artifacts carrying coverage data are the **26** `05 Lease Analyzer/results/lease_analyze_202608*`
directories, and every one of them is an empty fixture stub:

```
run                                    bytes n_cov  calls
lease_analyze_20260823_013009           3574     0      2
...  (26 rows, all identical in shape)
lease_analyze_20260826_032608           3766     0      2

runs with non-empty coverage_assessment: 0
```

**All 26 have `coverage_assessment: []` and `api_calls_total: 2`** — they are the two-call fixtures
generated during the Step 485/486 export verification, not analysis runs.

**Consequence: for Steps 457, 466, 468, 476, 478, 482 and 484 the question cannot be answered.** Those
runs were inspected in memory and reported in status files; their results were never written to a file
that survives. **Every claim in this arc about panel cleanliness on a local run rests on a census that
can no longer be re-executed against its own data.**

I am not asserting those runs contained stubs. I am asserting that **nothing establishes they did
not**, and that the brief's hypothesis — that clean-panel reports may have counted stubs — **remains
open for exactly the runs the arc's conclusions rest on.**

## 2b. The extraction runs — clean, and structurally so

`build_log/464_shape_runs/` (12 files), `build_log/LP12_extraction_runs/`,
`build_log/PSHARE_extraction_runs/`: **0 occurrences** of `evaluator_verdicts`, `is_fallback`, or
`did not complete` in any. These are extraction-stage artifacts and contain no evaluator layer, so the
defect class does not apply. Recorded for completeness, not as evidence of anything.

---

# 3. THE DEPLOYED RUNS

| run | evaluator records | stubs | roles | LPs | misreporting |
|---|---|---|---|---|---|
| **atlas_1** | 606 | **6** | A | **LP-17** | **6** |
| **atlas_2** | 606 | 0 | — | — | 0 |

atlas_1, the six records, verbatim field values:

```
role=A  lp=LP-17  actual_model='claude-sonnet-4-6'  actual_label='Claude Sonnet 4.6'
        label='Claude Sonnet 4.6'  is_fallback=False  verdict='unclear'  citation=None
        reasoning='Evaluator A did not complete'
```

**Contradiction with the role-level record, in the same file:** `fallback_events` carries
`{"event_type": "all_failed", "lp_id": "LP-17", "role": "A", "actual_model": null}`, and
`per_evaluator_lp_verdicts` is `{"C": ..., "B": ...}` — role A absent.

**atlas_2 is clean because nothing totally failed on it.** All 30 of its role-A failures obtained a
substitute (`gemini-2.5-pro`) and are recorded as honest `fallback` events with `is_fallback: true` on
every element record. **The 202 substituted records on atlas_2 are correctly labelled.** The defect
requires the fallback chain itself to come up empty, which happened once, on one LP, in one run.

---

# 4. THE HISTORICAL CORPUS — 139 stubs, none of them misreporting

149 files scanned, **38,145** `evaluator_verdicts` records, **139** stubs. All in five files, all
**before** Step 372a:

| file | run timestamp | stubs | role | LPs |
|---|---|---|---|---|
| `experiments/validate_305e/run1/…` | 2026-05-11 | 17 | B | LP-11 |
| `experiments/validate_305_full/…` | 2026-05-12 | 86 | C | LP-03, 09, 11, 13, 14, 15, 16, 17, 22, 27 |
| `results/lease_review_20260529_195234_s370r3/…` | 2026-05-30 | 12 | B | LP-09 |
| `results/lease_review_370av_fixture_empty/…` | 2026-05-30 | 12 | B | LP-09 |
| `results/lease_review_370av_fixture_nonemp/…` | 2026-05-30 | 12 | B | LP-09 |

**The three 2026-05-30 files carry an identical `timestamp` field (`2026-05-30T00:07:21`), identical
role, LP and stub count, but three different SHA-256s.** They are near-certainly fixture variants of
one underlying run, not three independent runs. **Do not read that table as five independent
occurrences.**

## 4.1 Why none of them misreports — and why that is not reassurance

A pre-372a stub, verbatim:

```json
{
  "role": "B",
  "label": "GPT-5.5",
  "verdict": "unclear",
  "citation": null,
  "reasoning": "Evaluator B did not complete",
  "confidence": "low"
}
```

**`actual_model`, `actual_label` and `is_fallback` are absent entirely.** There is no provenance claim,
so there is no false one. A census over `actual_model` simply does not see these records — it
under-counts rather than mis-attributes.

**But `label` says `"GPT-5.5"`,** which is precisely the *"laundering a fallback's verdict under the
primary's name"* that 372a's own comment describes. **A census keyed on `label` would be wrong on
these 139 records.** Different field, same class of error, three weeks earlier.

---

# 5. WHAT THIS ANSWERS, AND WHAT IT DOES NOT

**Answered:**

- **The defect is not new.** It has been latent since `5611fd8`, 2026-05-31.
- **It is not in the frozen record.** 431/447 is clean, and structurally better instrumented than the
  305 path. **This does not go to the bound** — there is nothing here to bound.
- **It has fired exactly once in every artifact that exists:** atlas_1, LP-17, role A, six records.
- **The historical corpus is not silently corrupted** in the `actual_model` sense.

**Not answered, and the gap is where the arc's own conclusions live:**

- **Steps 457–484.** Not persisted. Cannot be checked. **The brief's hypothesis stands open for
  precisely these runs.**
- **Whether the 139 pre-372a stubs affected any conclusion drawn at the time.** I counted them; I did
  not trace whether any merged verdict rested on one. Out of scope here.
- **Whether other artifact families carry the shape.** I scanned files containing `evaluator_verdicts`
  plus the named 431/430/423 sidecars. Telemetry (`runs.jsonl`) and the job-event streams were **not**
  scanned — the deployed ones live on Railway ephemeral storage.
- **Whether `label` being wrong on 139 pre-372a records matters to anything cited.** Not traced.

---

## Provenance of this report

Scanner run over 149 files + 12 sidecars, all opened `'r'`. Counts are machine-produced; the quoted
JSON and code are verbatim from the files named. **No file in the repository was modified by this
step** other than `build_log/489_chat_instruction.md` and this status file.
