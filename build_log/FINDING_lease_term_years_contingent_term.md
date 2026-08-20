# Finding: `lease_term_years` cannot express a contingent lease term

**Date:** 2026-08-18
**Status:** **FIXED 2026-08-19** (schema + Mode C prompt). Verified locally on Atlas; the abort no longer occurs on Atreca. NOT DEPLOYED.
**Severity:** Blocks Mode C extraction entirely for affected leases. Aborts before any output is produced.
**Found:** while smoke-testing the deployed app after the 2026-08-18 push of eleven adapter commits (422A-429, 445).

---

## The observed failure

Two attempts, same result, on `05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt`:

```
primary extractor gemini-3.1-pro-preview: validation_failed
  '' is not of type 'number'
  schema.properties.deal_overview.properties.lease_term_years: {'type': 'number'}
  instance: ''
CANONICAL FAIL-CLOSED: fallback suppressed in canonical mode
```

Extraction aborts. No provisions are extracted, no statuses are produced, the completeness gate is never reached. The Atreca fixture cannot complete Mode C at all.

---

## The correct diagnosis, and it is not "the model returned a bad value"

**The Atreca lease has no term expressible in years.** From the lease's own Base Term definition, verbatim:

> Beginning on the Commencement Date and ending on the earliest of (i) the date that is 90 days after the date that the Tenant Improvements are Substantially Completed (as such terms are defined in the 835 Industrial Lease), (ii) if the Tenant Improvements have not been Substantially Completed (as such terms are defined in the 835 Industrial Lease) by the Rent Commencement Date (as defined in the 835 Industrial Lease) for any reason other than delays caused solely by Affiliate, the date that is 90 days' written notice from Landlord to Tenant, and (iii) if the 835 Industrial Lease terminates prior to the Rent Commencement Date (as defined in the 835 Industrial Lease) thereof, the date that is 90 days after the termination of the 835 Lease.

The term:

- **starts** on the Commencement Date, which is when Landlord Delivers the Premises — not a calendar date;
- **ends** on the earliest of three contingent events, none of which is a date;
- defines all three by reference to a **different lease** (the 835 Industrial Lease, on a to-be-constructed building in San Carlos) that had not been performed at execution;
- is further subject to a Condition Precedent that could terminate the lease automatically before it began.

`lease_term_years` has no correct numeric value for this document. The extractor returning `""` is the **right answer to a question with no answer**. The schema requires a number and rejects it, so the run dies.

---

## Why this is not an edge case

This is a **real executed commercial lease**, filed with the SEC as EX-10.18 (Atreca, Inc. / ARE-East Jamie Court LLC, accession `0001104659-19-041460`), imported for the EDGAR mini-corpus as a Tier-1 external validation fixture. It is not synthetic and it was not constructed to break anything.

Commercial leases routinely have terms that are not numbers: bridge and swing-space leases, leases tied to a build-out elsewhere, holdover arrangements, condition-precedent structures, month-to-month conversions, terms measured from an event rather than a date. Any such lease crashes Mode C extraction before producing anything.

---

## The defect shape, which is familiar

This is the same class as the `NOT_APPLICABLE` gap fixed on 2026-08-18 in `provision_extraction_single_doc.txt`:

> **The vocabulary cannot express the true state, so the true state becomes an error.**

There, absence and extraction-failure collapsed into one token because the prompt permitted only two of the schema's five values. Here, "this lease has no term in years" has no representation at all, so it arrives as a type violation.

It is worse than the `NOT_APPLICABLE` gap in one respect: that one failed a gate *after* extraction ran, leaving a diagnosable partial result. This one aborts before any output exists.

---

## What has NOT been established

- Whether other real leases in the EDGAR corpus hit the same field. Not surveyed.
- Whether other `deal_overview` fields have the same rigidity (e.g. a required numeric where a lease legitimately has none). Not surveyed.
- Whether the non-canonical fallback path would have produced usable output. Fallback is suppressed in canonical mode by design; not tested.
- Whether Atreca clears LP-20, LP-21, LP-23, LP-31 under the new three-value extraction prompt. **This is the open question the crash blocks** — Atreca failed on exactly those four before the prompt fix, and the fix has only ever been verified on Atlas.

---

## Fix direction, not a fix

Permit the schema to represent a term that is not a number. Candidates, in rough order of preference:

1. **Allow `null`** on `lease_term_years`, with a companion field recording why — e.g. `lease_term_basis: fixed_years | contingent | event_triggered | month_to_month | undetermined`. Puts the judgment where the document is, same correction as the `NOT_APPLICABLE` fix.
2. Allow a union type (`number` or `string`) — cheaper, but loses the distinction between "contingent" and "the model gave up," which is exactly the distinction that mattered last time.
3. Relax canonical fail-closed for `deal_overview` type violations only — treats a modelling gap as a strictness problem and is the wrong lever.

**Option 1 is the one consistent with the correction already made.**

---

## Why it matters for what happens next

Atreca is the known-good foil. Until this is fixed there is exactly one testable fixture (Atlas), and Atlas cannot answer the `NOT_APPLICABLE` question because its two structurally-absent LPs are rescued by the gate's registry branch regardless of what the extractor returns.

So: **this blocks verification of the fix that was just deployed.**

---

## Related open defects, recorded elsewhere but listed here for continuity

1. **Atlas LP-12** — genuine extraction miss. `Section 13.2. Termination Right` exists in the lease and is not found. Search hints include `termination right`; the article-heading grouping rule in the extraction prompt is the suspected cause, unverified. This is a recall problem, not a vocabulary problem, and needs measurement rather than a patch.
2. **Compare-mode gate exposure** — `check_extraction_completeness` is wired unconditionally in `lease_adapter.py`, governed by `meta.get("canonical", True)` rather than by mode. In compare mode a provision absent from the tenant lease yields `TEMPLATE_ONLY` with empty `tenant_text`, which the gate would score `fail_missing` unless the LP is in the known-absent set. Inspection only; compare mode has not been run since the 422C deploy.

---

# UPDATE 2026-08-19 — fix applied, and two things it did not fix

## 1. `lease_term_years` — FIXED

Option 1 implemented, two files:

- **`schemas/extraction_schema.json`** — `lease_term_years` is now `["number", "null"]`. New sibling
  `lease_term_basis`, enum `fixed_years | contingent | event_triggered | month_to_month |
  undetermined`. The rule *"`lease_term_years` MUST be null whenever `lease_term_basis` is anything
  other than `fixed_years`"* is **enforced** by a draft-07 `if/then`, not merely described.
- **`prompts/provision_extraction_single_doc.txt`** — also the file that populates `deal_overview`
  for Mode C, so it was the only prompt changed. Sets the basis first, emits a number only for
  `fixed_years`, and states the bias: if a term looks fixed but the document is unclear, use
  `undetermined` rather than guessing, because a wrong term length is worse than an admitted unknown.

Descriptions carry the distinction the finding called for: `contingent` / `event_triggered` /
`month_to_month` are **properties of the lease**; `undetermined` is a **failure to determine** —
the same shape as `NOT_APPLICABLE` vs `AMBIGUOUS`.

**Schema unit-checked before spending provider calls:**

```
contingent + null      VALID       contingent + 5      REJECTED
fixed_years + 5        VALID       month_to_month + 1  REJECTED
undetermined + null    VALID       bad enum            REJECTED
empty string ""        REJECTED    no basis (legacy)   VALID
```

`""` is still rejected, deliberately: `null` is the representation, not empty string.

**Verified on Atlas (2026-08-19 22:16 EDT):** `lease_term_basis: 'fixed_years'`,
`lease_term_years: 5`. No regression.

**Atreca:** the `'' is not of type 'number'` abort **did not recur**. Extraction still does not
complete, but for a different reason — see §3. The defect recorded in this document is fixed;
the fixture is still blocked.

**Untouched, as scoped:** `provision_extraction.txt` (compare mode), `lease_adapter.py`, the
completeness gate, `KNOWN_ABSENT_BY_DOC_TYPE` (0 diff lines), `cam/core/`. No union type.
Canonical fail-closed intact.

**Noticed, not changed:** every other `deal_overview` field is `{"type": "string"}` with
"use empty string if not determinable", so none can crash the way `lease_term_years` did. The
rigidity was specific to the single numeric field.

## 2. Atlas LP-12 — RECHARACTERISED: intermittent, not a consistent miss

The "Related open defects" entry below describes LP-12 as a genuine extraction miss. **That is
now known to be wrong as stated.** Three observations of the same lease and the same LP:

| # | when | surface | LP-12 status | chars | gate |
|---|---|---|---|---|---|
| 1 | 2026-08-17 23:29 EDT | local | `AMBIGUOUS` | 0 | FAIL on LP-12 |
| 2 | 2026-08-17 23:42 EDT | deployed | `AMBIGUOUS` | 0 | FAIL on LP-12 |
| 3 | 2026-08-19 22:16 EDT | local | `TENANT_ONLY` | 767 | **PASS** |

**Intermittent is worse than consistent.** A consistent miss is a bug you can find and fix. This
gate passes or fails non-deterministically on the same lease: the same document submitted twice
can yield a report once and a refusal the next time, with no input change to explain it. For a
tool whose output is legal analysis, "sometimes produces a report" is a worse property than
"never does".

**Two caveats, recorded so this is not over-claimed:**

- The gap between observation 1 and observation 3 is **~2 days**, not minutes.
- The code path was **not byte-identical**. `provision_extraction_single_doc.txt` was edited
  twice between obs 1 and obs 3 — the `NOT_APPLICABLE` vocabulary fix (`f893286`, committed
  2026-08-17) and this document's `lease_term_basis` change (2026-08-19). Neither edit touches the
  provision-location or article-heading instructions that govern LP-12 recall, and there is no
  mechanism by which a `deal_overview` field change would improve it — but the file did change,
  so a perturbation cannot be *excluded*, only judged implausible.

Observations 1 and 2 bracket a deploy and are 13 minutes apart with the same prompt bytes; those
two agreeing does not establish stability, it establishes only that the miss reproduced twice.

**This still needs measurement, not a patch.** N=3 across two code states is not a rate.

## 3. NEW DEFECT — Atreca router timeout

```
google_error: TimeoutError: Router timeout exceeded: 308.8s > 300.0s
CANONICAL FAIL-CLOSED: primary extractor failed; fallback suppressed in canonical mode
```

Atreca is **160,244 characters** (Atlas: 31,755 — 5×). The extraction call exceeded the 300s
router ceiling by 8.8s.

**Not touched.** Raising a timeout to make a test pass is the wrong lever, and it is the same
class of error as relaxing canonical fail-closed.

**Unestablished:** whether the 300s ceiling is too low for genuinely large documents, or whether
this document is pathologically slow for a reason worth finding (size alone, or something about
its structure). One observation. The margin — 8.8s over — means it may well be marginal rather
than structural, which would make it intermittent too.

**Consequence:** the open question this document names as blocked is **still blocked**. Whether
Atreca clears LP-20/21/23/31 under the three-value vocabulary remains unverified, and the
`NOT_APPLICABLE` fix deployed on 2026-08-17 is still confirmed only on Atlas — which, as recorded
below, cannot answer it.

## 4. The pattern worth naming

Two independent pipeline stages are now known to be non-deterministic on identical input:

- **Coverage evaluation** — the grok-4.3 spot check (2026-08-17, 10 calls, temp 0, identical
  evidence): on `LP-28.grandfathering_pre_existing` evaluator C returned
  `explicitly_present` ×2, `unclear` ×2, `missing` ×1 — three different downstream action classes
  from one document. Evaluators A and B were stable on the same cell.
- **Extraction** — Atlas LP-12 above.

These are different stages with different models and different prompts. The common property is
that **a stability percentage would mislead in both cases**: 40% EP reads as "mostly present", and
2-of-3 AMBIGUOUS reads as "usually fails", when the honest statement is that the mechanism does
not settle. Any future stability claim about this pipeline should say which stage, at what N, and
under which code state.

