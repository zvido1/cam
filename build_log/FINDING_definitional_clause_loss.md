# Finding: a definitional clause is lost or sunk before assessment

**Date:** 2026-08-20
**Status:** RECORDED, NOT FIXED. No code, schema, or prompt changed.
**Severity:** The product emits a confident, evaluator-agreed finding about the lease that is
false, caused by evidence the extraction layer dropped. Nothing in the output marks it.
**Measurement:** six extraction-only runs, full output persisted at
`build_log/PSHARE_extraction_runs/` (`run_01_full.json` … `run_06_full.json`, `summary.json`,
`run_probe.py`, `probe.log`).

---

## The clause

Atlas lease, line 22 — the sole definition of the tenant's cost-allocation percentage:

> `"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area of the`
> `Demised Premises to the total rentable area of the Building.`

Referenced downstream by Section 3.2 (Additional Rent) and Section 3.3 (Real Estate Taxes and CAM
Charges). One clause, multiple dependents — the shape 421C names.

## Needles, verified by occurrence count before use

| needle | occurrences in the lease | used |
|---|---|---|
| `shall mean 22.4%` | 1 | yes |
| `ratio of the rentable area` | 1 | yes |
| `total rentable area of the Building` | 1 | yes |
| `22.4` | 1 | yes — tracked separately across every provision |
| `Proportionate Share` | 3 | **no** — a hit would not prove provenance |
| `Real Estate Taxes and CAM Charges` | 2 | **no** |

## The six runs

| run | LP-07 (CAM) | LP-02 (Escalation) | LP-00 (sink) | definition lands |
|---|---|---|---|---|
| 1 | `TENANT_ONLY` 2636, no 22.4 | `TENANT_ONLY` 1111, no | `TENANT_ONLY` 2236, **has 22.4** | `LP-00` |
| 2 | `TENANT_ONLY` 2636, no 22.4 | `TENANT_ONLY` 1111, no | `TENANT_ONLY` 2236, **has 22.4** | `LP-00` |
| 3 | `TENANT_ONLY` 2636, no 22.4 | `TENANT_ONLY` 1111, no | `TENANT_ONLY` 2236, **has 22.4** | `LP-00` |
| 4 | `TENANT_ONLY` 2636, no 22.4 | `TENANT_ONLY` 978, no | `TENANT_ONLY` 1175, no | **NOWHERE** |
| 5 | `TENANT_ONLY` 2636, no 22.4 | `TENANT_ONLY` 978, no | `TENANT_ONLY` 1175, no | **NOWHERE** |
| 6 | `TENANT_ONLY` 2636, no 22.4 | `TENANT_ONLY` 978, no | `TENANT_ONLY` 1175, no | **NOWHERE** |

Same model (`gemini-3.1-pro-preview`) on all six, no fallback on any. All three needles move
together on every run — one clause being placed, not fragments scattering.

## What the runs establish

- **0 of 6 reach LP-07 or LP-02**, the two issue areas the clause is material to. Both return
  substantial text on every run and **neither ever contains `22.4`**. There is no cross-filing here
  to be unstable; it never occurs.
- **3 of 6 land in LP-00**, the identity-check provision, which the pipeline does not score.
  Confirmed downstream: the full runs produce **32 coverage entries for 33 requested LPs, and LP-00
  is the one with no entry**. On these runs the clause is present in the extraction output and
  invisible to the analysis.
- **3 of 6 are absent from the output entirely.** `22.4` appears in no provision's `tenant_text`
  anywhere. The lease's only statement of the tenant's cost-allocation percentage is dropped.

**LP-00 length signature: 2236 characters when it holds the clause, 1175 when it does not.** A
clean ~1061-character presence/absence, not a boundary wobble. The clause is either wholly there or
wholly gone.

## Both outcomes are 421C's predicted failure modes

`build_log/421C_evidence_assignment_incident.md` §4, *Architectural Root Cause: Destructive
Exclusive Assignment*, predicts exactly these two.

**The sink:**

> LP-00 is a sink for identity-check content. When Gemini assigns the key-terms table to LP-00
> (Parties & Premises), it goes into a provision that is not evaluated for coverage. The content is
> not malformed or missing from the extraction — it is routed to a bucket that the pipeline does
> not score.

**The loss:**

> The assignment is also destructive: material not assigned to any LP bucket, or assigned to an
> unscored LP (like LP-00), is permanently [lost].

421C also names this precise clause:

> The key-terms table defines Tenant's Share (LP-07 relevance), the Rent Adjustment Percentage
> (LP-02 relevance), and the Base Term (LP-03 relevance) in one place. Assigning it to one bucket
> means the other buckets don't see it.

---

# THE CONSEQUENCE THAT MATTERS

**In the full Atlas run of 2026-08-20 (job `lease_review_20260820_023343_961518`), LP-07 returned
2636 characters and a `partial` coverage state. That assessment was made on text that never
contained `22.4%`.** The product produced a coverage judgment, a materiality rating and evaluator
agreement on a provision whose operative figure was absent from the evidence.

Verified on both full runs of that date — the deployed job and the local re-run — identically:

```
LP-07  coverage_state = partial   materiality = low   confidence = high
       partial_class  = partial_typical
       tenant_text    = 2636 chars, contains "Proportionate Share", does NOT contain "22.4"
       evidence       = "Step 305 per-element assessment (4 present, 2 missing, 0 unclear
                         of 6 elements; 3/3 evaluators)"
       LPs whose coverage tenant_text contains 22.4: NONE
```

**And it is sharper than "nothing indicated it".** LP-07's `elements_missing` reads:

> `"Tenant's proportionate share calculation method is defined"`

The evaluators marked that element **missing** — correctly, given the evidence they were handed,
which used the term `Proportionate Share` (from the §3.2 and §3.3 references) without ever defining
it. But the element **is** defined in the lease, at line 22, as 22.4%.

So the output does not merely omit the figure. It contains **an affirmative claim about the lease
that is false**, delivered at `confidence = high` with `3/3 evaluators` agreeing, and presented as a
finding about the document rather than as a gap in the evidence. A reader is told the lease does not
define the calculation method. The lease does.

The evaluators behaved correctly. Every layer downstream of extraction behaved correctly. The
failure is entirely upstream, and no downstream layer can detect it — because a clause the lease
never had and a clause the extractor dropped are indistinguishable once the evidence is fixed.

---

## Consequence for the fix directions

The three directions recorded in `FINDING_lease_term_years_contingent_term.md` §5 were written
against the LP-12 evidence. This result changes which survive.

**Direction 2 — make the completeness gate assignment-aware — is RULED OUT.** It proposed satisfying
an LP from text filed under a *related* LP. That cannot help here: on three runs the text is in an
unscored sink, on the other three it does not exist in the output at all. There is nothing for a
smarter gate to find.

The gate is also not the injured party in this case — **the gate passed.** LP-07 had 2636
characters, so no completeness check fired. The evidence was sufficient in volume and wrong in
content. A completeness gate measures presence, not correctness, and this defect is invisible to it
by construction.

**Direction 3 — extend 423C's non-exclusive evidence architecture upstream into extraction — is the
answer.** LP-12 argued for it; this result forces it:

- LP-12 was **over**-assignment with recall intact at 6/6. Bad, but **visible**: the gate caught it
  and aborted the run.
- This is **under**-assignment with recall failure, and it is **invisible**: the run completes, the
  report is produced, and the wrong finding is stated confidently.

A defect that stops the pipeline is a nuisance. A defect that lets the pipeline produce a confident
false statement about a legal document is the one that matters.

## Open question — NOT a claim

**Did the Step 447 measurement's `tenant_share` parameter and the `cand_04` forcing case see this
definition?**

Step 447's candidate provisioning is a different path from Mode C extraction, and that measurement
is L1 and frozen. **This finding does not alter it and must not be read as doing so.** But
`tenant_share` is the parameter family whose operative figure is 22.4%, and cand_04 is the 22.4%
forcing case, so whether the definition was present in the provisioned evidence bears on how those
results are read.

Deliberately unexamined here — checking it is a separate task against frozen artifacts, not a side
effect of this one.

## What is NOT established

- One fixture, one clause, six runs. Whether the 3/3 split is stable is unknown; **3/3 is an
  observation, not a rate.**
- Whether other definitional clauses behave this way. The Base Term (LP-03 relevance in 421C's list)
  was not measured.
- Whether LP-07's assessment would change if the definition were present. The element it marked
  missing would presumably flip, but the assessment was not re-run with the clause restored.
- Whether Mode A (compare) shows the same behaviour. Not run.
