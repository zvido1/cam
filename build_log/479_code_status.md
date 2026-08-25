# Step 479 — The divall coverage result, examined

**Date:** 2026-08-24 · **Instruction:** `build_log/479_chat_instruction.md`
**INSPECTION ONLY.** Nothing changed, nothing re-run, nothing deployed. Source: the completed divall
run of Step 478 (`s478_divall`) — the **first non-Atlas coverage result in the project**.
Atlas comparator: `s478_atlas_r2`, same run batch, same configuration.

**Convention:** *[M]* = measured from the artifact or the document. *[R]* = my reading.

---

## 1. The headline read

**Deal overview — accurate, specific, unmistakably this lease** *[M]*:

```
landlord      DiVall Insured Income Properties 2 Limited Partnership
tenant        WENDCHARLES I, LLC
property      361 Highway 17 Bypass, Mt. Pleasant, South Carolina
property_type Restaurant / Retail        term  Twenty (20) Years, fixed_years
governing law South Carolina             rent  $146,520.00 annually / $12,210.00 monthly
cam_structure Absolutely Net Lease (NNN) deposit $5,600.00
escalation    "Intentionally Omitted"    renewals None
permitted_use Nationally recognized Franchise Restaurant
```

**Coverage distribution** *[M]*: 32 entries — 12 `partial`, 8 `review_needed`, 5 `not_applicable`,
3 `missing`, 3 `broken_xref`, 1 `covered`. 26 require attention. Materiality: 5 high, 3 medium,
24 low.

**High-materiality items** *[M]*: LP-07 CAM (`missing`), LP-14 Force Majeure (`review_needed`),
LP-19 Utilities (`missing`), LP-27 Landlord Default (`partial`), LP-28 Compliance with Laws
(`missing`).

**Compound risks, verbatim** *[M]*:

> - Tenant has notice obligations before asserting Landlord default but lacks a comparably detailed set
>   of escalation remedies if Landlord fails to perform.
> - Tenant may owe broad pass-through amounts yet lacks the practical tools to verify or challenge them
>   inside the lease.
> - Tenant automatically subordinates to any future mortgage without a standalone, self-executing
>   non-disturbance agreement.
> - Tenant can end up in a real disruption scenario where operations are impaired, rebuilding is
>   Tenant's burden, and taxes/insurance/utilities continue even during repair.
> - If a force majeure event renders the Premises operationally impossible, Tenant still owes full Base
>   Monthly Rent, taxes, and insurance premiums with no abatement or exit.

**Is it coherent? Does it read like a review of THIS lease?** *[R]* **Yes, and convincingly.** Every
compound risk is specific to a 20-year absolutely-net single-tenant restaurant lease: rebuilding as
the tenant's burden, taxes/insurance/utilities continuing through repair, no rent abatement on force
majeure, subordination without a standalone SNDA. None of it would transfer to Atlas, a
multi-tenant warehouse with a CAM regime and a §19.2 SNDA covenant. **It does not read as a template
filled in.** The high-materiality selection is also defensible on its face — CAM, utilities and
compliance being flagged `missing` on an NNN lease is exactly where a tenant-side reviewer would look.

## 2. The locator damage — Step 472's prediction confirmed verbatim

**LP-07: FELL BACK** *[M]*. `span_evidence_records = 0`; it used the 1,260-char extraction bucket,
which opens `6.1 Maintenance and Repair by Tenant`. The seam degraded exactly as designed — logged,
not silent.

**LP-27: SPAN PATH, 3 records** *[M]*, and the assembled text is **malformed as predicted**:

```
'[ARTICLE\nXI]\nLandlord shall not be deemed to be in default hereunder with respect to any of the
terms, covenants or conditions of this Lease unless Tenant shall first give written notice to
Landlord and Landlord fails within thirty (30) days of receipt thereof to cure said default...'
```

Rendered, the block a reader or evaluator sees is:

```
[ARTICLE
XI]
Landlord shall not be deemed to be in default hereunder...
```

**The `[locator]` marker is split across two lines.** Step 472 predicted this from the heading index
returning `'ARTICLE\nXI'`; it is now observed in a live coverage run.

### Resolution rate: 7.2%, against Atlas's 99.0%

*[M]*, 305 non-null `section_ref` values across all 32 LPs:

| | divall | Atlas (Step 471) |
|---|---|---|
| resolves | **22 (7.2%)** | 1,758 (99.0%) |
| non-resolving | 219 (71.8%) | 0 |
| unparseable | 64 (21.0%) | 17 (1.0%) |

The mechanism is exact. Most-cited refs *[M]*: `'14.15'` ×25, `'11.1'` ×16, `'Section 6.1(a)'` ×15,
`'14.10'` ×10, `'14.4'` ×9 — **the document's real numbering**, which the heading index does not
contain because divall numbers sections as bare `10.1` at line start.

**The only refs that resolve are `Article XI` / `ARTICLE XI` — all from LP-27, the span-path LP.**
Span-path citations: **20 of 30 resolve (67%)** against the ~7% document-wide baseline.

*[R]* **So the malformed prefix still worked.** Evaluators read across the embedded newline and cited
`Article XI` — the locator they were given. The malformation is cosmetic, not comprehension-breaking:
it cost granularity (article rather than section) but it is the single thing lifting resolution above
the floor on this document. That is a genuinely mixed result and I would not present it as a failure.

## 3. False all-clears — 1 of 4, and it is LP-12 again

| LP | reported *[M]* | does the document address it? *[M]* | verdict |
|---|---|---|---|
| **LP-12 Early Termination** | `not_applicable` / attn `False` / *"absent by design"* | **YES** | **FALSE ALL-CLEAR** |
| LP-30 Estoppel Certificate | `unclear` → `not_applicable` / attn `False` | `"estoppel"` **0 hits**; attornment present at §14.15 | defensible |
| LP-31 Co-Tenancy | `unclear` → `not_applicable` / attn `False` | `co-tenancy`/`cotenancy`/`anchor tenant` **0 hits** | correct |
| LP-32 Hazardous Materials | `unclear` → `not_applicable` / attn `False` | `hazardous`/`environmental`/`contaminat`/`toxic` **0 hits** | correct |

**LP-12, quoted from the lease** *[M]* — reported as "absent by design":

> *"(d) Provided Tenant has paid Percentage Rent with respect to at least one of the two (2) full Lease
> Years preceding the Total Destruction of the Premises, if a Total Destruction of the Premises occurs
> during the last five (5) Lease Years of the Term, **Tenant will have the right to terminate the Lease**
> as of the date of such Total Destruction by written notice to Landlord within thirty (30) days
> following the Total Destruction."*

Plus *[M]*: a mutual termination right on casualty (*"Landlord and Tenant may mutually agree to
terminate this Lease"*) and automatic termination on total condemnation (*"this Lease shall terminate
and expire as of the date of taking"*).

*[R]* **This is the identical defect Atlas produced, on the identical LP.** Atlas: `not_applicable` /
"absent by design" on a lease with §13.2 and §13.3 termination rights. Divall: the same output on a
lease with casualty, condemnation and total-destruction termination rights. **Two documents, two
false all-clears, same issue area.** That LP-12 is also the perennial gate-failure LP is unlikely to
be coincidence, though the causal link is not established here.

**The other three are sound** *[R]*, and worth saying plainly: 3 of 4 `not_applicable` calls on a
single-tenant freestanding restaurant are correct. Co-tenancy and hazardous materials genuinely are
not in this lease. The degrade path did not manufacture those.

## 4. Spot-check — three findings, evidence verified against the document

**COVERED — LP-09 Subletting & Assignment**, element *"Assignment requires landlord consent"* →
`explicitly_present`, 3/3, confidence high. All three quote *"Tenant shall have the right to assign
this Lease or sublet the Premises only with Landlord's prior written consent."* Refs `12.1(a)` /
`Section 12.1(a)` — **non-resolving against the index**, but the quote is **verbatim in the lease at
§12.1(a)** *[M]*. *[R]* Finding supported; the citation is right and the index is wrong.

**PARTIAL — LP-04 Security Deposit**, element *"Deposit amount is stated"* → `explicitly_present`,
3/3. Quote *"a Security Deposit in the amount of $5,600.00 is held by Landlord"* — **verbatim in the
lease** *[M]*, and consistent with `deal_overview.security_deposit = "$5,600.00"`. *[R]* Supported.

**MISSING — LP-07 CAM**, element *"Tenant's proportionate share calculation method is defined"* →
`missing`, 3/3, confidence high, materiality high. B cites §6.1(a): *"In the event the Premises are or
become subject to the common area maintenance charges, or other third party billings, Tenant shall be
responsible therefor"* — **verbatim in the lease** *[M]*. Document-wide *[M]*: `"proportionate share"`
**0 hits**, `"tenant's share"` **0 hits**, `"percentage of the total"` **0 hits**.

*[R]* **`missing` is correct, and this is the sharpest contrast in the report.** On Atlas the same
element was the arc's founding false negative — the lease defined it at 22.4% and extraction lost it.
Here the lease genuinely contains no share formula: it makes CAM a conditional pass-through with no
allocation method. **Same element, opposite documents, and the pipeline got both right — Atlas only
after the seam, divall first time.**

## 5. Shape comparison

| | Atlas (`s478_atlas_r2`) | divall (`s478_divall`) |
|---|---|---|
| entries | 32 | 32 |
| requires_attention | 27 | 26 |
| high materiality | 4 | 5 |
| compound risks confirmed | 7 | 5 |
| cross-provision findings | 34 | 28 |
| API calls | 94 | **73** |
| coverage states | partial 20, review_needed 5, not_applicable 3, missing 2, covered 2 | partial 12, review_needed 8, not_applicable 5, missing 3, **broken_xref 3**, covered 1 |
| document size | 31,755 | 59,255 |

**The distributions are not wildly different — they are strikingly similar** *[M]*: same entry count,
attention counts within one, high-materiality within one. On a document 1.9× the size.

Two real differences *[M]*: divall shows **`broken_xref` ×3**, a state Atlas never produced; and
divall used **73 calls against Atlas's 94** — 22% fewer, consistent with 4 LPs short-circuiting before
the evaluator plus LP-07 falling back off the span path.

**Speculation, flagged as such** *[R]*: the similarity is probably structural rather than substantive
— the taxonomy fixes 33 LPs and most elements resolve to `partial` on any real lease, so the shape may
be driven by the schema more than by the document. If so, distribution similarity is **not** evidence
the analysis generalises; it may be evidence the output shape is insensitive to the input. Divall's
shift toward `review_needed` (5→8) and away from `partial` (20→12) is the part that looks
document-driven, and `broken_xref` is worth a look on its own — **none of this is established.**

## Overall *[R]*

The report is coherent, specific and mostly defensible. It is not a template. The largest problems are
**(a)** citations that do not resolve on 93% of the document, which breaks the audit trail even where
the underlying quotes are verbatim-correct; **(b)** one false all-clear on LP-12, the same LP that
failed on Atlas; and **(c)** a malformed but still-functional locator that, on this fixture, is the
only thing keeping resolution off the floor.

## What is NOT established

- Whether the 32 verdicts are *correct* beyond the three spot-checked. Three of ~200 elements.
- Whether `broken_xref` is a defect or a legitimate state. Not investigated.
- Whether LP-12's repeat false all-clear shares a cause with its repeat gate failures. Correlation only.
- Whether the shape similarity is schema-driven. Explicitly speculation.
- Anything about deployed behaviour. One local run, not re-run, not deployed.
