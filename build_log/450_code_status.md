# Step 450 — replay feasibility, post-run validator, Rule 8, state records — CODE STATUS

Audit only. No harness edit, no rerun, no push, no remediation. Rule 6 throughout.
Run artifacts hashed before and after: **unchanged** (sidecar `c44573cb…`, seam `01e0427e…`,
report `8f469cec…`).

---

## TASK A — REPLAY FEASIBILITY

Script: [450_replay_feasibility.py](450_replay_feasibility.py), headed *"independent post-run
validation, not emitted by the sanctioned harness"*. Canonical sources rebuilt deterministically
from the token-bound fixtures; both `source_document_hash` values equal `FROZEN_LEASE_HASHES`
(`7118cc6d…`, `da9b5655…`). Zero model calls.

### Per candidate and role — all 108 judgments

| element | result |
|---|---|
| `field_support` present | **108 / 108** |
| `field_support` covers all six semantic fields | **108 / 108** |
| `field_support` maps each field → citation ids (`candidate_citation_ids` / `context_citation_ids`) | **108 / 108** |
| judgments carrying `context_citations` | 44 / 108 (68 context quotes) |
| context citations carrying **both** `citation_id` and a non-empty `quote` | **68 / 68** |
| candidate citations | 124 quotes across 108 judgments |

Per-candidate/per-role breakdown is in the script output; every one of the 21 (candidate × role)
cells shows `fs_present = fs_covers_6 = fs_maps_ids = n_judgments`.

### Quote resolution — and a correction to my own first pass
My initial check normalized whitespace/case and resolved **all** quotes against the whole canonical
document. It returned 0 unresolved — **contradicting the sidecar's own single `resolved: false`
trace.** The contradiction was the signal, and the harness settles it:

```python
def quote_resolves(quote: str, haystack: str) -> bool:
    """A cited quote resolves iff it appears verbatim in the supplied text."""
    return quote in haystack
```

`apply_field_grounding` passes **`candidate_text`** for candidate citations and **`context_text`
(the frozen envelope)** for context citations. Exact substring, no normalization, and the envelope —
not the document — is the haystack for context. My first pass was more permissive on both counts and
was therefore measuring a different thing.

Re-run under the harness's exact semantics:

| | quotes | resolved |
|---|---|---|
| candidate → `candidate_text` | 124 | **124** |
| context → envelope `context_text` | 68 | **67** |

The single unresolved quote is **cand_03, canonical panel 4, role C (grok-4.3), `xc1`,
`"Base Rent: $3.75 per rentable square foot of the P…"`** — which **exactly reproduces the harness's
own recorded `_unverified_quote_traces` entry** `('cand_03','C','xc1','context',False)`. Independent
recomputation now agrees with the run record.

**Note on the brief's phrasing:** it asks whether each quote resolves "against the frozen canonical
source hash." The preregistered mechanism does **not** resolve context citations against the
canonical source — it resolves them against the bounded envelope. Against the full canonical
document all 192 quotes resolve; against the envelope, 67 of 68 context quotes do. Both numbers are
reported rather than collapsed, because the difference *is* the §10 envelope-sufficiency question.

### Is a deterministic materialization of `semantic_support_spans` constructible from the sidecar alone, without semantic invention?

**No.** Three elements are missing, named:

1. **No preregistered schema for the span object.** The preregistration mentions the concept three
   times and never defines its shape: `start_char` → **0 occurrences**, `end_char` → **0
   occurrences**; the single `span_id` hit is `candidate_span_id`, a different field. Constructing a
   span object would require inventing its fields.
2. **No preregistered rule for which citations become spans.** Nothing states whether spans derive
   from candidate citations, context citations, only resolving ones, or only those supporting
   certified fields. Choosing is semantic invention.
3. **One offset is genuinely ambiguous.** 190 of 192 quotes occur exactly once in their haystack
   (offset deterministic); **one context quote — cand_02 role B `xc1`, `"LEASE AGREEMENT"` — occurs
   twice** in its envelope. Resolving that to a single span would require a tie-break rule that is
   not preregistered.

The *raw material* (verbatim quotes, citation ids, complete field→citation mapping, envelope
offsets, resolution status) is fully present. What is absent is the **specification**. Materialization
was not attempted, per instruction.

---

## TASK B — POST-RUN VALIDATOR

Generator [450_postrun_validator.py](450_postrun_validator.py) → **[431_postrun_partial_validation.json](431_postrun_partial_validation.json)**.
Its header and its `_status` / `_not` fields declare it an independent post-run audit artifact
written after outcomes were visible, **not** `431_validation.json` and **not** the preregistered
§8.2 validator; every record carries `artifact_status:
post_run_derived__not_preregistered_validator_output`. Criterion texts are embedded verbatim.

**Seven criteria computed** (`9.1#1, #2, #4, #5, #7, #8, #9`), **#6 derived**, **#3
not_established_at_package_layer**. The conjunction is emitted **by the validator** — and it is
deliberately `null`, with the validator's own note explaining that a seven-of-nine conjunction would
not be §9.1 and is not reported under that name. **No conjunction verdict is written in prose here.**

### Two computations I corrected before publishing
Both first-pass numbers looked like findings and were defects in *my* computation. Both are now
reported under **two scopings** rather than one, because collapsing them would have decided a
question the preregistration leaves open:

- **#2.** The literal §8.1 conjunction requires `basis_match=match`. But
  `SCHEMA_FIXED_NOT_APPLICABLE` exempts the basis field for `base_rent` and `rent_adjustment_pct`,
  so those candidates record `basis_match='not_applicable'` and **can never satisfy the literal
  text**. Literal reading: **4 of 14** satisfied traces have a single id supplying every property.
  Including `not_applicable`: **14 of 14**. Harness's own `candidate_qualification == 'qualified'`
  marker: **14 of 14**. The artifact records all three and states that **which reading §8.1 intends
  is a preregistration question, not decided here.**
- **#4.** First pass counted *any* candidate in a satisfied trace carrying a non-unanimous field → 5.
  Those are all `atlas/base_rent`, where the **losing stub cand_05** carries a non-unanimous
  `candidate_support_state` while the **certifying cand_06** is unanimous. Scoped to the qualifying
  candidate: **0 of 14**. Both counts are recorded with an explicit scope note.

### Computed values (from the artifact, not re-typed conclusions)
`#1` 1 unresolved-quote trace; 7 fields invalidated, all `empty_field_support`; **0** invalidated
fields still carrying a substantive value. `#5` terminal states `{satisfied 14,
review_needed_disagreement 11, review_needed_no_qualifying_candidate 5}`; **0** states matching
`unsatisfied*`; **0** traces whose completeness ≠ `not_established`. `#7` 30 result lines, **30**
carrying the qualifier. `#8` 108 judgments, **108** with distinct candidate/context citation keys,
**0** missing a non-empty `reason`, 35 per-candidate records carrying all comparison fields. `#9`
empty result set. `#6` derived from prefix-occurrence 0 + 14 satisfied traces. `#3` package layer
not established; **value-layer enforcement half reported separately** (literal `False`, inclusive
`True`, with per-certified-candidate detail).

---

## TASK C — RULE 8

Added to `CLAUDE.md` under REPORTING INTEGRITY as **§8 Producer-consumer census**, verbatim as
directed, with a short *why this exists* citing 447/448: the §9.1 producers were optional, their
products mandatory, and the inconsistency survived every hash/signature/scope/cleanliness gate
because none of them asks whether a specified output has a producer.

---

## TASK D — STATE RECORDS

**Scope note:** the project `CLAUDE.md` says *"Never modify the architecture plan or current state
docs — those are Chat's domain."* Task D explicitly directs these edits, so the instruction
overrides the default; recorded here rather than assumed.

- **`Docs/CAM_Current_State.md`** — new dated top block (2026-07-26) recording the run, the
  **terminal certification-state distribution** under its correct name, the cand_04 §9.2 result, the
  §9.1 unproducibility, the salvage position, and the claim boundary. The 07-24 block is retained
  and relabelled as the sanction record, superseded only as to execution status. The stale
  "NEXT: read the run" paragraph — which anticipated five artifacts — is marked superseded and
  corrected to three.
- **`Docs/Patent_Current_State.md`** — new dated top block (2026-07-26) stating what is now
  demonstrated, the **value-layer anti-borrowing finding as a finding separate from package
  materialization**, and the explicit do-not-claim list: emitted certified evidence packages with
  materialized support spans; recorded anti-borrowing at the support-span layer; Gate-B handoff; any
  §9.1 result. Adds the method contribution: that a preregistration can be internally inconsistent
  in a way surviving cryptographic sanction, and Rule 8 as the corrective. The 07-24 status-
  discipline paragraph is marked superseded rather than deleted.

Both edits use the directed vacuity language: any affirmative reading of the support-span
prohibition would be **vacuously true** — true because nothing of the quantified kind exists, not
because a mechanism declined to borrow.

---

## Git
`450_chat_instruction.md` written verbatim before execution (Rule 7). Committed with `git add -f`
explicit paths: this status, the instruction, both scripts, the post-run artifact, `CLAUDE.md`, and
both state docs. **NOT pushed.**
