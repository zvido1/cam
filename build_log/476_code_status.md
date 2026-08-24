# Step 476 — Degraded continuation instead of gate abort

**Date:** 2026-08-24 · **Instruction:** `build_log/476_chat_instruction.md`
**Implemented and tested locally. NOT deployed.** Flag `GATE_ABORT_RETURNS_DEGRADED = True`
(`lease_adapter.py`); set `False` to restore raise-on-abort — that one edit is the whole rollback.
Gate criteria unchanged, no retry added, no evidence substituted.
Tests: **354 passed** (352 + 2 new).
Runs: config as Step 468 — `SPAN_EVIDENCE_LPS {LP-07, LP-27}`, expansion off,
`ENTAILMENT_TEST_LPS {LP-27}`, clean panel (`gpt-5.5` 197/197 both runs).

| run | outcome | elapsed | calls |
|---|---|---|---|
| `s476_r1` | **clean** — gate passed | 1410s | 94 |
| `s476_r2` | **degraded** — gate would have aborted on LP-12 | 1369s | 93 |

Under the old behaviour `s476_r2` would have died at ~105s with no output.

---

## Found while wiring: the existing degraded path was itself inert

The non-canonical branch writes `cfg["_run_metadata"]` with `run_degraded`,
`extraction_completeness_failed` and friends. **Nothing reads that dict** — a grep for consumers
outside the setter returns none. Routing the canonical path into it would have continued the run with
**no marker anywhere in the output**. The failure is carried in a local and wired explicitly instead.
Same written-versus-wired shape as `FINDING_evidence_architecture_unwired.md`.

## 1. What the user sees — in the JSON, unmissable

Summary block, verbatim, degraded run. The markers **lead** the block:

```json
{
  "REPORT_INCOMPLETE": true,
  "invalid_for_legal_analysis": true,
  "incomplete_statement": "INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. Extraction returned no text for 1 required issue area(s): LP-12. Those areas were assessed with no evidence and their findings are unsupported. The rest of this report was produced normally, but the document has not been fully analysed.",
  "issue_areas_with_no_evidence": ["LP-12"],
  "mode": "analyze",
  "total_provisions_checked": 33,
  "issue_areas_assessed": 32,
  ...
}
```

Top level:

```
run_degraded                        = true
degraded_reason                     = "extraction_completeness_failed"
extraction_completeness_failed      = true
extraction_completeness_failed_lps  = ["LP-12"]
invalid_for_legal_analysis          = true
degraded_statement                  = "INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. …"
completeness_failures               = [{"provision_id": "LP-12", "tenant_text_len": 0,
                                        "extraction_status": "AMBIGUOUS",
                                        "gate_status": "fail_missing", "known_absent": false,
                                        "reason": "Required/applicable LP has empty tenant_text
                                                   and is not classified NOT_APPLICABLE"}]
```

**Is it obvious the report is incomplete? In the payload, yes. In the product, NO — see §4.**

## 2. LP-12 downstream: it produces a SPURIOUS verdict, and the marking is what saves it

```
issue_area_name    "Early Termination"
applicability      "not_applicable"
coverage_state     "not_applicable"
materiality        "low"
requires_attention false
evidence_summary   "No activation clues found; issue area absent by design"
element_verdicts   0
tenant_text        "" (0 chars)

evidence_missing           true          <- Step 476
invalid_for_legal_analysis true          <- Step 476
evidence_missing_note      "EVIDENCE MISSING — extraction returned no text for this issue
                            area. Any verdict below is not supported by extracted evidence
                            and must not be relied on."
```

It does not fail and it does not crash. **It produces `not_applicable` with
`requires_attention: false` — a substantive all-clear on Early Termination, for a lease that addresses
it at §13.2 and §13.3.** No 305 evaluator ran; there are zero element verdicts. Without the Step-476
markers this entry reads as "nothing to see here," which is precisely the false-affirmative class this
arc exists to stop.

**The marking works. The underlying verdict is wrong and would be dangerous unmarked.**

### And the gate is aborting on a distinction that makes no difference here

**LP-12's coverage entry is substantively identical on the clean run.** Every field matches except
`tenant_text_hash`:

```
clean     tenant_text=''  tenant_text_hash='402d88d913a277fc'
degraded  tenant_text=''  tenant_text_hash='e3b0c44298fc1c14'   <- sha256 of the empty string
```

`e3b0c44…` is the empty-string hash; `402d88d…` is not. So on the **clean** run extraction *did*
return text for LP-12 — which is why the gate passed — and the coverage layer discarded it, because
the applicability layer independently ruled the issue area `not_applicable`. Different extraction
inputs, **the same all-clear output**.

So on this fixture the gate rejects roughly three in five runs to prevent an LP-12 entry that is
indistinguishable from the one it permits in the other two. That does not make the gate wrong — the
extraction difference is real — but it does mean **the abort was not buying the protection it appears
to buy**, and `not_applicable`-with-no-evidence is a second defect the gate was masking.

Side effects worth recording: LP-12 inflates the summary's `not_applicable: 3` counter, and
`issue_areas_assessed: 32` counts an area that was never assessed.

## 3. LP-07 and LP-27 on the degraded run — the seam behaves exactly as in Step 468

**LP-07, the flip, holds:**

| run | found/missing | `22.4` present | state | confidence | `proportionate_share_calculation` in `elements_found` |
|---|---|---|---|---|---|
| 468-e1 | 5/1 | ✅ | partial | high | ✅ |
| 468-e2 | 5/1 | ✅ | partial | high | ✅ |
| 476-clean | 5/1 | ✅ | partial | high | ✅ |
| **476-DEGRADED** | **5/1** | **✅** | **partial** | **high** | **✅** |

**LP-27, all ten elements identical to e1/e2 on both runs:**

| element | e1 | e2 | clean | **DEGRADED** |
|---|---|---|---|---|
| 1 Landlord default defined | EXP | EXP | EXP | **EXP** |
| 2 Written notice | EXP | EXP | EXP | **EXP** |
| 3 Cure period | EXP | EXP | EXP | **EXP** |
| 4 Self-help / offset | MIS | MIS | MIS | **MIS** |
| 5 Right to terminate | EXP | EXP | EXP | **EXP** |
| 6 Monetary damages | EXP | EXP | EXP | **EXP** |
| 7 Specific performance | IMP | IMP | IMP | **IMP** |
| 8 Lender notice | MIS | MIS | MIS | **MIS** |
| 9 Common law remedies | EXP | EXP | EXP | **EXP** |
| 10 Remedies cumulative | IMP | IMP | IMP | **IMP** |

`partial` / confidence `high` / 8 found / 1 missing / 7 spans on both. **Zero movement.** An
incomplete extraction elsewhere in the document does not perturb the seamed LPs.

This is also the first time the seam has run on a document state that previously killed the pipeline —
and it is the first evidence that the LP-07 flip survives a degraded run.

## 4. Downstream — NOTHING reads the markers. This is the significant caveat.

References to any degraded marker (`run_degraded`, `invalid_for_legal_analysis`, `REPORT_INCOMPLETE`,
`incomplete_statement`, `evidence_missing`, `extraction_completeness_failed`):

```
static/index.html          0
app/job_manager.py         0
app/main.py                0
app/summary_generator.py   0
lease_contract_index.py    0
lease_telemetry.py         0
```

And `job_manager`'s own `has_any_degraded` is set **only** for `missing_results` / `unreadable_results`
— it never reads the result's `run_degraded` field.

**Consequence: a degraded run currently reports to the user as a normal completed job.** The markers
are in the payload, correct and unmissable to anything that looks — and nothing looks. Every consumer
was written on the assumption the gate never lets an incomplete extraction through, and that
assumption is now false.

**So this change converts a loud failure into a silent success, unless a consumer is taught to read the
markers.** That is a worse failure mode than the one it replaces if left as-is, and it is the reason
this is not deployed.

The minimum to make it safe to deploy: `job_manager` folds `run_degraded` /
`invalid_for_legal_analysis` into the job aggregate, and the frontend renders `incomplete_statement`
above the summary. Both are out of this step's scope.

## Tests

**354 passed.** Seven tests in `test_422c` / `test_422d` asserted the raise contract; rather than
delete or leave them red, the three affected classes are pinned to
`GATE_ABORT_RETURNS_DEGRADED=False` — they now test the **rollback** contract — and a new
`TestDegradedContinuation` covers the default path plus an explicit
`test_flag_off_restores_the_raise`. **Nothing deleted. This was a test change not asked for, and is
flagged as such.**

## What is NOT established

- Any deployed behaviour. Local only, not deployed.
- Whether `not_applicable` is the right verdict for a zero-evidence LP. This step marks it; it does not
  change it. That is a coverage-layer question.
- Whether the clean run's discarded LP-12 text was substantive. Only the hash mismatch is measured.
- Whether other fixtures degrade the same way. Atlas only; divall fails 6–7 LPs and is untested here.
- Two runs, one of each outcome.
