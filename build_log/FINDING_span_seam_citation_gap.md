# Finding: the span seam's citation gap

**Date:** 2026-08-22
**Status:** PARKED. Recorded, not resolved. No design decision taken.
**Instruction:** `build_log/456_chat_instruction.md`
**Evidence:** two completed full 33-LP Atlas Mode C runs, `SPAN_EVIDENCE_LPS = {"LP-07", "LP-27"}`
— `seam2lp_r4/`, `seam2lp_r5/`. Four extraction-path runs for comparison: `rerun_out/`, `seam_out/`,
`seam_out_r2/`, `seam_out_r3/`.
**Companion:** `FINDING_span_evidence_not_citable.md` (the same two runs, measurement detail).

---

## The finding

**Span evidence improved what the evaluators could see and degraded whether they were permitted to
report it.**

On LP-27, evaluators A and C independently returned `explicitly_present` at `confidence=high`.
Consensus was reached: B abstained and was dropped from the count, `majority_count = 2`, and the
`no_consensus` branch did **not** fire. The citation check then replaced the presence verdict with
`unclear`, because the assembled evidence supplied no usable `section_ref`.

**The failure occurred after correct semantic evaluation.** Nothing misread the lease.

### The three raw verdicts

LP-27, element `Landlord default is defined (what triggers landlord default)`. **Identical in both
runs:**

| role | model | fallback | verdict | confidence | section_ref | citation_quality |
|---|---|---|---|---|---|---|
| A | claude-sonnet-4-6 | False | `explicitly_present` | high | `None` | `section_only` |
| B | gemini-2.5-pro | True | `unclear` | high | `None` | `none` |
| C | grok-4.3 | False | `explicitly_present` | high | `None` | `section_and_quote` |

Merged: `verdict='unclear'`, `confidence='low'`, `reason='citation_required_but_absent'`,
`citation=None`.

Their reasoning was not in doubt:

- **A:** "The lease explicitly defines landlord default as failure to perform any material obligation
  under the Lease, which directly satisfies the element. The quote is drawn from the LP text itself,
  though no section number is provided."
- **C:** "The text directly defines landlord default by failure to perform material obligations."
- **B:** "...as no section reference is available in the provided text, a verdict of 'unclear' is
  required per instruction rule #5, which mandates a section reference for any presence verdict."

### Code site 1 — unclear is an abstention, `lease_coverage_305.py:907`

```python
# Filter out unclear for consensus calculation (unclear = abstain from consensus)
active = [v for v in verdicts if v["verdict"] != "unclear"]
```

B is removed. `active = [A, C]`, both presence-tier, so `majority_count = 2`, clearing the
`majority_count < 2` guard that returns `no_consensus`.

### Code site 2 — the citation check, `lease_coverage_305.py:991`

```python
# Citation-or-it-didn't-happen check (architecture spec §6)
if majority_verdict in PRESENCE_VERDICTS:
    valid_citations = [
        c for c in majority_citations
        if c and c.get("section_ref")
    ]
    if not valid_citations:
        return {
            "verdict": "unclear",
            "confidence": "low",
            "citation": None,
            "reason": "citation_required_but_absent",
            "disagreements": verdicts,
            "disagreement_citations": _collect_disagreement_citations(verdicts),
        }
```

`majority_citations` holds A's and C's citation objects — both non-null dicts carrying
`section_ref=None` — so `valid_citations` is empty. The `reason` recorded in the results confirms
which branch executed: `citation_required_but_absent`, **not** `all_evaluators_unclear` and **not**
`no_consensus`.

**B's vote is not load-bearing.** Had B also voted `explicitly_present`, the outcome would be
unchanged unless B supplied a `section_ref`.

## Mechanism

The seam assembles verified clause bodies and strips source-location metadata. This was deliberate,
and the reason is in the seam's own comment:

```python
# Ascending offset order, blank-line separated. No span markers: the 305 prompt
# has no vocabulary for them, and inventing one would change what the evaluators
# read in a way this experiment has not tested.
```

That conflicts with the 305 contract, `lease_coverage_305.py:243`:

> `5. Any presence verdict (explicitly_present, implicitly_present, covered_by_default_law, covered_in_other_LP) requires section_ref in the citation. If section_ref is null, use unclear instead.`

Extraction buckets retain section headings — LP-27's bucket opens `Section 5.1. Security Deposit.`
Span evidence is frequently mid-section fragments with nothing truthfully nameable:

```
[1] if Landlord fails to perform any material obligation under this Lease
[2] such failure continues uncured for thirty (30) days after written notice from Tenant
    specifying the nature of such failure
[3] written notice from Tenant specifying the nature of such failure
```

**Result: 8 of 10 LP-27 elements suppressed to `unclear` with `citation_required_but_absent`.**
Across LP-27's span-path runs, 0 of 30 evaluator citations carried a `section_ref`, against 23–25 of
30 on the extraction path. LP-level: `partial` / confidence `high` → `review_needed` / confidence
`low`.

## LP-07 caveat — the earlier explanation was wrong

LP-07 survived the same gate in all five span-path runs. **The earlier explanation for why — that
LP-07's span was a self-contained definitional sentence the evaluators could anchor to — is WRONG,
and is withdrawn here rather than smoothed over.**

LP-07 survived because its evaluators supplied locator-shaped strings that are not genuine section
references. `section_ref` on the Proportionate Share element, every run:

| run | A | B | C |
|---|---|---|---|
| seam_out | `None` | `'LP-07 CAM provision, paragraph 1'` | `'"Proportionate Share" shall mean'` |
| seam_out_r2 | `None` | `'LP-07 CAM Provision, paragraph 1'` | `None` |
| seam_out_r3 | `None` | `'Proportionate Share paragraph'` | `None` |
| seam2lp_r4 | `None` | `'Paragraph 1'` | `'Proportionate Share definition'` |
| seam2lp_r5 | `None` | `'Para. 1'` | `None` |

Not one is a section reference. `'Paragraph 1'` indexes the assembled prompt block, not the lease.
The clause in fact sits in **Section 1.2 (Definitions)** — a locator no evaluator produced in any run.

**LP-07 does not demonstrate that span assembly satisfies the citation contract.** It demonstrates
that some evaluators manufacture plausible locator labels while others honestly return `None`, and
that the check tests only non-nullity. On the span path the gate is currently selecting for
fabrication: LP-27's panel was penalised for candour.

## Separate defect class — model-authored quality fields describing properties the object lacks

A returned `citation_quality='section_only'` and C returned `'section_and_quote'`. **Both returned
`section_ref=None`.** Each self-description positively asserts a section reference that the citation
object does not contain.

The deterministic check consulted the object (`c.get("section_ref")`) rather than the description,
and was therefore correct. Had it trusted `citation_quality`, both evaluators would have passed a
gate they did not satisfy.

This is a distinct failure from the citation gap and is recorded separately: **a model-authored
metadata field characterised the evidence as having properties it does not have.** Any future code
that reads `citation_quality` as authoritative inherits the defect.

## Provider confound

OpenAI credits were exhausted six verdicts into each run:

```
openai_error: RateLimitError: Error code: 429 - 'You have no credits remaining...'
code: 'credit_balance_exhausted'
```

Role-B model census across all 33 LPs:

```
seam2lp_r4    gemini-2.5-pro: 191, gpt-5.5: 6   | is_fallback True: 191, False: 6
seam2lp_r5    gemini-2.5-pro: 191, gpt-5.5: 6   | is_fallback True: 191, False: 6
seam_out_r2   gpt-5.5: 197                       | is_fallback False: 197
seam_out_r3   gpt-5.5: 197                       | is_fallback False: 197
```

**~97% of role-B verdicts came from a substituted model.**

- **Does NOT explain the LP-27 mechanism.** A and C alone produced the majority that was discarded;
  the merge outcome does not depend on B's vote.
- **DOES contaminate every comparative quantity** — the 8-of-32 moved-set count, and LP-07's
  stability *relative to baseline*. LP-07's internal consistency across r4/r5 is real but compares
  two equally degraded runs. **No comparative run is interpretable until the intended evaluator is
  available.**

**Operational observation:** the router substituted another provider's model for nearly an entire
run, recorded the degradation faithfully in `is_fallback` and `actual_model`, and allowed the run to
complete and report. Nothing halted, and nothing in the output summary surfaces that the panel was
not the specified panel.

## Open design question — three options, none chosen

1. Derive a section locator deterministically from each verified span's canonical offsets.
2. Expose span identity / source metadata to the evaluator in a citable form.
3. Recognise that offset-resolved evidence already carries stronger source verification than a
   model-supplied `section_ref`, and modify the citation requirement accordingly.

**No decision is taken here.** Note for whoever decides: option 3 is the only one that addresses the
`citation_quality` defect above, since options 1 and 2 both continue to route trust through a field
the model can also populate. Note also that a naive form of option 1 fabricates deterministically —
an unanchored backward scan for `Section N.N.` tags the Proportionate Share definition as
`Section 8.3`, because offset 1613 is an inline cross-reference
(`"Landlord's Work" shall have the meaning set forth in Section 8.3.`) and not a heading.

## Park state

**The seam is NOT rejected.** It exposed a precise interface mismatch: the upstream evidence layer
knows exactly where the evidence came from; the downstream evaluator is handed prose that has
forgotten it, and is then penalised for being unable to reconstruct it.

**Working-tree state — two corrections to the brief's description, recorded rather than resolved:**

- `cam/adapters/lease_review/lease_coverage.py` is uncommitted with **141 insertions**, not one flag
  line. Rollback is `git checkout -- cam/adapters/lease_review/lease_coverage.py`, not a single edit.
- **Option 1 above is already implemented** in that uncommitted diff by Step 455 (`_HEADING_RE`,
  `_build_heading_index`, `_locator_for_offset`, and a `[<locator>]` prefix in
  `_assemble_span_evidence`). It was verified offline — all stored span sets resolve, 0 bare, all 5
  inline cross-references excluded, the Proportionate Share definition resolving to `Section 1.2` —
  and **has never been run through the pipeline.** It is implemented-and-unmeasured, not
  open-and-untouched.

`SPAN_EVIDENCE_ENABLED = True`, `SPAN_EVIDENCE_LPS = {"LP-07", "LP-27"}`.

Two tests fail with the seam in place —
`test_423a_...::test_module_not_imported_by_live_stage5_pipeline_files` and
`test_423c_...::test_no_live_pipeline_file_imports_elicitation_module` — both asserting the 423 stack
is *not* wired into the pipeline. They must be rewritten from "nothing imports this" to "the seam,
and only the seam, imports this" before the seam can be committed. Suite otherwise: 350 passed.

## Extraction completeness gate — blocking

**10 aborts / 12 attempts this session.** Two full runs (6 and 7) exhausted four attempts each and
produced nothing, blocking a third replicate. Message:
`Extraction completeness failure: 1 required LP(s) have missing evidence and are not classi...`

**Which LP trips it is NOT established for these runs** — the harness truncated the exception at 90
characters. LP-12 is the historical intermittent aborter (prior tally: 6 aborts across 13
observations) and is the likely candidate, but that is an inherited attribution, not a measurement
from this session.

This blocker is independent of the OpenAI credit state and will dominate the cost of any rerun.

## What is NOT established

- Whether any of the three options restores LP-27's presence verdicts. Nothing was run.
- Whether LP-07's result survives once its evaluators receive a real locator instead of inventing one.
- Whether the two-run identity holds at three runs. The third replicate failed twice, 4/4 aborts each.
- Precision of the span sets — only stability and citability were measured.
- Whether `citation_quality` is consumed anywhere else in the pipeline as if authoritative. Not
  audited.
