# Step 532 — Coverage never runs. There is no size boundary. divall at 59KB has the same 5 empty provisions as everbridge at 294KB.

**Date:** 2026-09-03 · **Instruction:** `build_log/532_chat_instruction.md`
**DIAGNOSTIC ONLY. No provider calls, nothing changed, not deployed.**
**Items 1 and 2 cannot be run as instructed — and the reason makes them unnecessary.**

---

# 0. THE FRAMING IS WRONG IN THREE WAYS, AND THE THIRD ONE ANSWERS THE STEP

## 0.1 Coverage does not fail. Coverage never runs.

`lease_adapter.py`, in execution order:

```
1387   check_document_is_lease(...)          <- the document classifier
1403   extract_provisions_single_doc(...)    <- extraction, 33/33 on both
1430   # ── Extraction completeness gate (422C) ──
1521       raise GateAbortError(...)         <- everbridge and ncino STOP HERE
1619   coverage_assessment = assess_coverage(...)   <- NEVER REACHED
```

**The abort is at 1521. `assess_coverage` is at 1619, ninety-eight lines later, and is never called.**
There is no coverage failure to diagnose, no coverage stage to locate, and no LP that failed inside
coverage. The failure is the 422C completeness gate, which sits *between* extraction and coverage.

## 0.2 There is no ~225KB boundary, because quanterix has never been run

**quanterix has never been through the gate.** `ls build_log/runs/*quanterix*` returns nothing, and
Step 531 said so explicitly: *"quanterix, bokf, albireo and atreca_industrial have never been through
the gate, so their accept/reject is predicted, not observed."*

**The "clean boundary, no exceptions" has no measurement on the passing side of the boundary.**

## 0.3 And the size hypothesis is refuted by data already on disk

From the Step-529 persisted survey — no new calls:

```
fixture                          emitted nonempty  EMPTY   doc_ch    gate outcome
everbridge_northlake_pasadena        33       28      5   294492    ABORT
ncino_parkerfarm_wilmington          33       28      5   230269    ABORT
quanterix_crosby_bedford             33       29      4   224528    never run
solidpower_thornton_industrial       33       29      4   211735    COMPLETED
divall_wendys_mtpleasant             33       28      5    59496    COMPLETED
```

**divall is 59 KB — one fifth of everbridge — and has exactly the same profile: 33 emitted, 28
non-empty, 5 empty. It completed.**

**So neither document size nor the number of empty provisions determines the outcome.** What determines
it is *which* LPs are empty and what the applicability matcher says about those specific LPs — which is
what Step 531 measured and quoted.

---

# 1 & 2. WHY THE RUNS CANNOT BE DONE AS INSTRUCTED — AND MY ERROR IN IT

> *"Run coverage ONLY on ncino... with the extraction result from the Step-529 persisted run. Do not
> re-extract."*

**The Step-529 runs do not contain the extraction result.** Keys persisted per row:

```
attempt_chain, bytes_discarded, doc_chars, doc_kb, elapsed_sec, extraction_errors,
fallback_used, finish_reason, fixture, model, outcome, parse_path, parse_repair_kinds,
parse_repaired, provisions_emitted, provisions_non_empty, provisions_recovered,
provisions_requested, raw_char_len, usage
```

**`provisions` is not among them.** My Step-529 harness recorded *counts* of provisions, not the
provisions themselves. **That is my error** — a survey harness that measures extraction and discards
its output makes exactly this follow-up impossible, and I did not anticipate it.

The instruction forbids re-extraction, so items 1 and 2 have no input. **I did not re-extract.**

**They are also moot.** Both documents' failures are already recorded, at the same stage, with the same
mechanism, quoted verbatim in Step 531:

| lease | aborts on | the clue that fired, and the text it fired inside |
|---|---|---|
| ncino | LP-20 ×4 | `exclusive use` inside *"non-exclusive right... not regularly and customarily leased for the exclusive use of tenants"* |
| everbridge | LP-20, LP-21, LP-23 ×4 | `exclusive use` inside the Common Areas definition; `guarantor` inside *"a release of Tenant or any guarantor"*; `percentage rent` inside *"(xxxi) Fixed or percentage rent under any ground or underlying lease"* — item xxxi of an **exclusions list** |

**Same stage, same operator, same failure shape. It is a wall, and the wall is the matcher, not the
size.** everbridge fails on more LPs than ncino because it happens to contain more of the trigger
phrases — not because it is bigger.

---

# 3. THE MESSAGE — LINE 1057 IS NOT IT, AND THE PIPELINE SAYS THE OPPOSITE

**`lease_extract.py:1057` is not that message.** It is a field inside the all-extractors-failed meta
block:

```python
            "meta": {
                "model": "none",
                "provider": "none",
                ...
                "extraction_failed": True,
```

**There is no "may not be a lease" string in `lease_extract.py`.** Every place the claim can reach a
user:

| # | site | text | can it legitimately mean it? |
|---|---|---|---|
| 1 | `lease_gate.py:100` | *"The uploaded document does not appear to be a commercial lease agreement. Please check your file and upload a valid commercial lease."* | **YES** — this is the classifier's own verdict, `is_lease=False`, the one case where the system actually judged document identity |
| 2 | `app.js:5489` | `t.error.startsWith("GATE_ABORT:") ? "Not a commercial lease"` | **NO** |
| 3 | `app.js:14393` | identical | **NO** |

Sites 2 and 3 fire for **all four** `GateAbortError` causes (Step 519): the classifier, extraction
integrity failure, all-extractors-unparseable, and 422C completeness. **Three of those four are
statements about our pipeline, not about the document.** Two of them mean *our own extractor broke*.

## The pipeline explicitly disagrees with what the user is told

From the everbridge run log, four times:

```
Gate: is_lease=True in 0.82s
Gate: is_lease=True in 1.25s
Gate: is_lease=True in 0.9s
Gate: is_lease=True in 1.13s
```

**The document classifier ran on everbridge four times and returned `is_lease=True` every time.** The
system determined it *is* a commercial lease, proceeded to extract 33 of 33 provisions from it, aborted
at a later gate for an unrelated reason — and then told the user it is not a commercial lease.

**The one component qualified to answer that question answered it, in the affirmative, and its answer is
discarded by a frontend ternary.**

---

# 4. WHAT SURVIVES TO COVERAGE: ZERO

```
provisions emitted by extraction   33  (everbridge)   33  (ncino)
provisions with content            28                 28
provisions empty                    5                  5
provisions reaching assess_coverage  0                  0
```

**Nothing is dropped between stages. All 33 survive extraction intact.** They never reach
`assess_coverage` because `GateAbortError` is raised 98 lines before it.

**The 5 empty provisions are not a loss** — Step 527's shape test and Step 531's reading established
that empty buckets on these documents correspond to provisions the leases genuinely lack (Exclusivity,
Guaranty, Percentage Rent, Co-Tenancy — retail terms in office and lab leases). **The extraction is
right. The gate's interpretation of it is wrong.**

**The finding is therefore neither size nor dropped provisions.** It is that five correct empty buckets
are fatal on one document and harmless on another, decided entirely by whether the substring matcher
found a trigger phrase somewhere in the text — including inside negations, disclaimers, conditionals and
exclusion lists.

---

# WHAT IS NOT ESTABLISHED

- **No coverage stage was exercised on any real lease in this step**, because none could be reached and
  no stored extraction exists to replay.
- **quanterix, bokf, albireo and atreca_industrial remain unrun through the gate.** Their outcomes are
  predicted from the matcher's offline verdicts, not observed.
- **Whether coverage itself would succeed on a 230-290 KB document is completely unknown.** It has never
  run on one. If the gate were fixed tomorrow, the next failure could be in coverage and nothing here
  would have predicted it.
- **The 5-empty/4-empty counts come from Step 529's survey**, which recorded counts only — I could not
  enumerate *which* provisions were empty except for the ones the gate itself named.
- **The `is_lease=True` readings are from everbridge's log only.** ncino's full log was not retained at
  that granularity.
- **Nothing was fixed and nothing was re-extracted.**
