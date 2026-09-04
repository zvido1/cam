# Step 561 — All three complete. And one headline is false: ncino says landlord entry needs prior notice; the report says "without notice, at any time, for any purpose."

**Date:** 2026-09-04 · **Instruction:** `build_log/561_chat_instruction.md`
**One constant changed. Tests: 445 passed, 3 skipped, 12 subtests. Not deployed.**
**Runs: `561A_albireo…`, `561B_everbridge…`, `561C_ncino…` — all persisted, all completed.**

---

# 0. THE INTERRUPT — ncino LP-29

**The brief names one thing worth interrupting for. This is it.**

**What the lease says**, verbatim:

> *"**ARTICLE 22. ACCESS BY LANDLORD.** Landlord shall retain duplicate keys to all of the doors of the
> Premises… Landlord or its agents shall have access to the … Premises **upon prior notice to Tenant
> during Normal Business Hours, except in cases of emergency** (when immediate access is necessary,
> Landlord will notify Tenant by the next business day after such access) in order to inspect, clean and
> make necessary or reasonable repairs to the Premises or the Building. During the final twelve (12)
> months of the Term, **upon prior notice**, … Landlord shall have the right to show the Premises at
> reasonable times to prospective tenants, but **Landlord shall endeavor to reduce disturbance to
> Tenant** during Normal Business Hours."*

**What the report says:**

> *"Landlord may enter premises **without notice, at any time, for any purpose** — disrupting tenant's
> business operations, exposing confidential business information, and interfering with customers"*

**False on all three counts, and produced from `tenant_text: 0` — zero extracted characters.** The
system did not read Article 22; it printed a canned sentence about a provision it never saw.

## This is a NEW route, and it is Cause B's first observation ever

```
LP-29  state=broken_xref  status=not_assessed  tenant_text=0  source=schema
       evidence_summary: "Provision not extracted; cross-reference or exhibit signals
                          suggest incomplete clause"
       signal: type='broken_xref'  evidence='Section 22'  severity=high
```

**Step 554 recorded Cause B — `lease_coverage.py:498`, no tenant text plus xref signals — as having
zero observations across six runs. It now has one.** Everything in Steps 555–557 addressed Cause A
(`reserved_or_omitted`); this is the other branch, and it reaches the same `risk_if_missing` string.

**Fourth route to this sentence:**

| # | route | status |
|---|---|---|
| 1 | `risk_if_missing` via Cause A `broken_xref` | fixed (555, 557) |
| 2 | `exposure_statement` via `partial`-with-a-gap | unfixed (549 Defect 2) |
| 3 | `exposure_statement` via `schema_fallback` on a model failure | found at 558 |
| 4 | **`risk_if_missing` via Cause B `broken_xref` on zero extracted text** | **found here** |

**And LP-29 is NOT in the degraded banner.** The banner lists `['LP-20','LP-21','LP-23','LP-31']` —
Cause B fires at the *coverage* stage, after the completeness gate has already partitioned. **A reader
told which four areas are unsupported is not told about the fifth.**

**Mitigation, measured:** LP-29 resolves to `not_assessed`, is not in `ANNOTATED_BUCKETS`, and Step 554
verified the exports print only `LP-id name [NOT ASSESSED]` for that bucket. **So the sentence does not
reach the DOCX or PDF reader — but it is on the persisted record, and `app.js` routes `not_assessed`
into the ordinary review bucket and renders `exposure_headline` (Step 554 §5).**

**The root cause is upstream of everything this arc has touched: extraction returned nothing for an
LP whose article is present, titled, and 1,100 characters long.**

---

# 1. THE CONSTANT, AND THE TRADE RECORDED WHERE IT WILL BE READ

```python
DEGRADABLE_APPLICABILITY = {"not_applicable", "unclear", "applicable"}
```

The comment above it now carries the trade in the brief's own terms — measured false-abort rate of 3 of
4 documents against an unmeasured true-abort rate of zero-so-far; defensible on the evidence and
indefensible in principle; the four false classifications that motivate it quoted verbatim; what it
gives up; that the degraded path from Steps 476–478 and 497 now carries the fact to the reader; and that
removing `"applicable"` is the whole rollback.

## A premise correction: LP-21 is NOT a required LP

```
LP-21: activation_clues=10 -> CONDITIONAL (matcher decides)
LP-20: activation_clues=8  -> CONDITIONAL
LP-17: activation_clues=0  -> REQUIRED
albireo    is_applicable(LP-21) = applicable
everbridge is_applicable(LP-21) = applicable
```

The brief expected everbridge and albireo to keep aborting on LP-21 because *"that is a required LP and
this change should not touch it."* **LP-21 is conditional and carries `applicable`, so this change does
touch it — and both documents completed.**

**`required` LPs are untouched**: the predicate is `ap not in DEGRADABLE_APPLICABILITY`, and `required`
is not in the set.

---

# 2. THE THREE RUNS

```
                    calls  elapsed   degraded  reason                          fallbacks
albireo               86   1343.2s   True      extraction_completeness_failed      0
everbridge            93   1694.8s   True      extraction_completeness_failed      0
ncino                 84   1757.5s   True      extraction_completeness_failed      2
```

**All three complete. None aborts.** All three are `invalid_for_legal_analysis: True` and carry the
degraded banner.

## 4. Top line, five categories

```
albireo      needs_attention 3   worth_reviewing 9   minor_gaps 12   not_assessed 5   covered 3   = 32
everbridge   needs_attention 5   worth_reviewing 3   minor_gaps 14   not_assessed 5   covered 5   = 32
ncino        needs_attention 6   worth_reviewing 7   minor_gaps  9   not_assessed 6   covered 4   = 32
```

## 5. `assessment_status` and `broken_xref`

```
albireo      assessed 27  not_assessed 5    broken_xref: none
everbridge   assessed 27  not_assessed 5    broken_xref: none
ncino        assessed 26  not_assessed 6    broken_xref: LP-04 (Cause A), LP-29 (Cause B)
```

**ncino LP-04 is Cause A and correct.** Its `tenant_text` is 109 characters, verbatim:

> *"Security Deposit. Not applicable\n\nARTICLE 7. SECURITY DEPOSIT. 7.01 Security Deposit .
> Intentionally omitted."*

`prose_outside_placeholders` returns `[]`, so Step 557's rule correctly short-circuits it, and the
headline is the hedged one — *"If deposit was negotiated, landlord has no documented…"*. **The lease
says both "Not applicable" and "Intentionally omitted". Correct on every axis.**

## 3. The four seamed LPs — all four reached the panel on all three documents

```
              LP-07                    LP-12                    LP-17                    LP-27
albireo       partial   10492ch  6el   review_needed 3595 5el   partial   1841ch  6el   partial 2019ch 10el
everbridge    missing    2590ch  6el   missing        760 5el   partial   3082ch  6el   partial 2565ch 10el
ncino         partial   15657ch  6el   review_needed 7474 5el   review_needed 360 6el   partial 4438ch 10el
```

**Every one carries element verdicts and `method=step_305_per_element`. No fallback to the extraction
bucket on any of the twelve.**

## 6. Locator

```
albireo      126 refs,  50 resolve = 39.7%
everbridge   127 refs,  33 resolve = 26.0%
ncino        123 refs,  30 resolve = 24.4%
```

Against the recorded range — atlas 83.8%, butler 45.0%, solidpower 16.5%, divall 2.5%. **All three sit
in the middle band.**

---

# 3. WHICH LPs NOW DEGRADE, AND WHAT EACH PRODUCES

```
albireo     LP-16, LP-20, LP-21, LP-23, LP-31   (was: abort on LP-20, LP-21)
everbridge  LP-20, LP-21, LP-23, LP-31          (was: abort on LP-20, LP-21, LP-23)
ncino       LP-20, LP-21, LP-23, LP-31          (was: abort on LP-20)
```

Every one produces `coverage_state: missing`, `assessment_status: not_assessed`, **0 element verdicts**,
and a headline. The previously-blocking ones:

```
albireo    LP-20  "No exclusive-use protection"          NOT ASSESSED / not_assessed
albireo    LP-21  "No stated guarantor exposure"         NOT ASSESSED / not_assessed
everbridge LP-20  "No exclusive-use protection"          NOT ASSESSED / not_assessed
everbridge LP-21  "No guaranty exposure identified"      NOT ASSESSED / not_assessed
everbridge LP-23  "No percentage rent obligation"        NOT ASSESSED / not_assessed
ncino      LP-20  "No protection from direct competitors" NOT ASSESSED / not_assessed
```

## Ground-truthed against the documents — all six are TRUE

| claim | the document |
|---|---|
| albireo has no exclusive use | only *"the general **non-exclusive use** and convenience of Tenant and other tenants"* |
| albireo has no guarantor | *"Security Deposit: $87,398.00 … **Guarantor: None**"* |
| everbridge has no percentage rent | only *"(xxxi) Fixed or **percentage rent** under any ground or underlying lease"* — an exclusions-list item |
| ncino has no exclusivity | only *"a **non-exclusive** right to the use of and access to areas … **not** regularly and customarily leased for the exclusive use of tenants"* and *"the right of **non-exclusive use**, in common with others, of parking decks"* |

**Six of six accurate.** These are the LPs the matcher falsely called applicable; with the LP released to
the coverage stage, the prose it produces about them is correct. **They are also `not_assessed`, which
is the honest label — nothing was evaluated, because extraction returned nothing.**

**None is annotated** (`not_assessed` is not in `ANNOTATED_BUCKETS`), so none gets a margin callout.

---

# 4. DOES THE BANNER NAME THEM, AND DOES A READER SEE IT?

```
INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. Extraction returned no text for 5 required
issue area(s): LP-16, LP-20, LP-21, LP-23, LP-31. Those areas were assessed with no evidence
and their findings are unsupported. The rest of this report was produced normally…
```

**It names them, by LP id, and `invalid_for_legal_analysis` is `True` on all three runs.**

**But it does not name LP-29 on ncino** (§0), because Cause B fires after the gate has partitioned.
**The banner's promise is "these are the areas with no evidence"; on ncino that list is incomplete by
one.**

---

# 5. READ AS A LAWYER WOULD — SUBSTANTIVE, WITH ONE PARAGRAPH THAT IS NOT

**Substantive.** Twenty-six or twenty-seven of thirty-two areas carry element-level verdicts from a
three-evaluator panel with citations, and the seamed LPs — CAM, early termination, dispute resolution,
landlord default — all produced spans rather than falling back. A reader gets a real reading of the
operative provisions.

**The five or six `not_assessed` areas are correctly labelled and correctly excluded from the findings**,
with a banner at the top saying the report is not valid for legal analysis and naming them.

**And one paragraph is worse than useless.** ncino's LP-29 tells a tenant that its landlord may enter
without notice at any time for any purpose, when Article 22 requires prior notice during normal business
hours except in emergencies, and obliges the landlord to reduce disturbance. **A lawyer acting on that
sentence would negotiate for a protection the lease already contains.** It does not reach the DOCX or
PDF, but it is on the record and on the web surface.

---

# WHAT IS NOT ESTABLISHED

- **The interrupt condition fired and I am reporting it rather than continuing.** No further documents
  were run; the brief's list was the three, and all three are done.
- **Why extraction returned nothing for ncino LP-29 was not investigated.** Article 22 is present,
  titled `ACCESS BY LANDLORD`, and ~1,100 characters. **That is an extraction routing failure and it is
  the root cause of §0** — the canned-prose problem is downstream of it.
- **Cause B has one observation.** Everything in §0 about it rests on ncino LP-29.
- **I ground-truthed six headlines by targeted search, not by reading three whole leases.** A provision
  phrased without any of the searched terms would not have appeared. The ncino Article 22 quote is
  verbatim and complete; the six absence claims rest on the absence of matching text.
- **The web surface was not opened.** §0's claim that `app.js` would render the false headline is the
  Step-554 code trace, not an observation.
- **ncino had 2 fallback events**; I did not examine which LPs or providers. albireo and everbridge had
  none.
- **`excluded` is still absent from `DEGRADABLE_APPLICABILITY`** — an LP whose exclusion clue fired and
  whose extraction came back empty would still abort, though consumer A short-circuits it exactly like
  `not_applicable`. Pre-existing, unobserved, out of scope.
