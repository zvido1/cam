# Step 537 — butler_crossing COMPLETED. 4 of 4 correct on the four concepts. And LP-20 at 0/7 elements renders as COVERED.

**Date:** 2026-09-03 · **Instruction:** `build_log/537_chat_instruction.md`
**COMPLETED: 2833.0s wall / 2339.3s pipeline, 90 calls, gate passed attempt 1, no truncation.**
**Second real lease ever to complete. Nothing tuned. Not deployed.**

---

# 0. TWO PREMISE CORRECTIONS, AND ONE OF THEM IS MINE

**"82 headings"** — ex6-4 has **8**. `carothers_bakers_bridge` has **213**, the highest in the corpus
and above Atlas's 89. **At 8 headings the locator claim was not testable on this document**; carothers
remains the document for that question.

**"all four previously absent concepts present in genuine non-negated context"** — **wrong, and the
error originated in my own Step 536 status.** I reported A.13 *"Landlord shall not lease... for the
operation of a single price point variety retail store"* as this document's exclusivity covenant. **It
is Dollar Tree's**, quoted inside a 23-page *Existing Exclusives* schedule running from index 129,852
to 242,026. A.13 sits at 144,073, immediately after `DOLLAR TREE (12-10-2008)`.

**The tell was in the text and I missed it:** an exclusive protecting a *single price point variety
retail store* cannot belong to Independent Taco, a fast-casual restaurant. **I quoted a clause without
establishing whose lease it came from — the exact Rule 6 failure the reporting rules exist to prevent.**

**"quanterix 0.6%"** has no source. quanterix has never been run through the pipeline (Steps 531, 532);
`ls build_log/runs/*quanterix*` returns nothing.

## Corrected ground truth, from the main lease body (chars 0–129,852)

| concept | truth | evidence |
|---|---|---|
| LP-20 Exclusivity | **ABSENT for this tenant** | §10(b) *"Restrictions, Prohibitions, Exclusives: Tenant expressly acknowledges that, from time to time, restrictions or prohibitions... may be"* — the tenant is **subject to** others' exclusives. Exhibit E is *"Existing Permitted, Exclusive, and Prohibited Uses"*. |
| LP-21 Guaranty | **PRESENT** | §(w) *"Guaranty: Landlord's obligations hereunder are conditioned upon the execution of a Guaranty of Full Performance by **Tim Sievers**"* + *"Guarantor hereby guarantees the full and prompt payment of rent"* |
| LP-23 Percentage Rent | **ABSENT** | §5(b) *"Percentage Rent: **[intentionally omitted]**"* — a third distinct absence shape, neither negated nor struck through |
| LP-12 Early Termination | **ABSENT** | zero option-to-terminate hits in the main body |

---

# 1. IT COMPLETED

```
wall 2833.0s | pipeline 2339.3s | calls 90 (97 logged) | gate attempts 1 | aborts 0
extraction_parse_repaired False | finish_reason FinishReason.STOP
usage: output 20,630 + reasoning 4,853 = 25,483 of 65,000 = 39% of the ceiling
completeness_failed False | degraded False | invalid_for_legal_analysis False
```

**No abort. The question of what an abort here would have meant does not arise.**

Note the usage: **output tokens 20,630 on a 242,900-char document**, against divall's 14,663 on 59,496
chars. That is far below the Step-530 linear fit's prediction (~44,000) — **a third data point that
weakens the fit further.** Reasoning tokens 4,853, again roughly flat.

---

# 2. THE FOUR CONCEPTS — 4 OF 4 CORRECT, AND THE ATTRIBUTION TEST PASSED

| LP | ground truth | verdict | elements | correct? |
|---|---|---|---|---|
| **LP-21** Guaranty | **PRESENT** | `partial` | **3/5 explicitly_present** | **YES** |
| **LP-20** Exclusivity | **ABSENT** for this tenant | `review_needed` | **0/7 present**, 5 missing, 1 disputed, 1 unclear | **YES** |
| **LP-23** Percentage Rent | ABSENT `[intentionally omitted]` | `broken_xref` | 0/0 | **YES** |
| **LP-12** Early Termination | ABSENT | `not_applicable` | 0/0 | **YES** |

## LP-21 — the first genuine presence the pipeline has ever been tested on

```
Guarantor identity is specified                       explicitly_present
Scope of guarantee is defined (full lease or limited) explicitly_present
Duration of guarantee is stated                       explicitly_present
```

**The panel found a real provision, and found it for the right reasons** — it identified the guarantor,
the scope and the duration, which is exactly what §(w) and Exhibit D contain. **Every prior measurement
in this project tested whether the pipeline was right about an absence. This is the first test of
presence, and it passed.**

## LP-20 — the attribution test, and this is the notable result

**The document contains 23 pages of genuine exclusivity covenants belonging to Dollar Tree, Michaels,
Applebee's, Dunkin' Donuts and others.** The panel returned **0 of 7 elements present** for this
tenant.

**It did not attribute another party's exclusive to Independent Taco.** Given Step 531 measured the
*applicability matcher* firing on `exclusive use` inside `non-exclusive`, and Step 534 found 4 of 4
abort-causing calls false, the panel doing better than the matcher on the same phrase in the same
document is worth recording.

## LP-23 — the negative-space detector earned its keep

`[intentionally omitted]` → `broken_xref` → *"Section or subsection explicitly marked as omitted or
reserved"* → `assessment_status: not_assessed`. **Correctly identified as an omission rather than an
absence or a gap.**

---

# 3. LOCATOR — 45.0%, AND HEADING COUNT IS NOT THE WHOLE STORY

```
butler_crossing   120 refs, 54 resolve = 45.0%    8 headings
atlas              83.8%                          89 headings
solidpower         17.5%                           1 heading
divall              2.5%                           0 headings
```

Same method as Steps 525 and 530 — **not Step 479's, whose 99%/7.2% I have never been able to
reproduce.** Comparable only to each other.

**45% at 8 headings against 17.5% at 1 heading breaks the monotonic story.** Something other than raw
heading count is driving resolution — plausibly that this document's evaluators cite `Section 16.4`,
`Section 20.1`, `Section 3.2` style refs that the index can match even when few headings parse. **Not
established; worth its own measurement.**

---

# 4. SEAMED LPs — AND THE FIRST SEAM FALLBACK ON A COMPLETING REAL LEASE

```
LP-07   5 spans   tenant_text 2285   partial
LP-12  12 spans   tenant_text    0   not_applicable   (routed out before the spans were used)
LP-17   0 spans   tenant_text 1904   partial          <- ELICITATION RETURNED NOTHING; fell back to the bucket
LP-27   6 spans   tenant_text 1722   review_needed
fallback_events: 0
```

**LP-17 got zero verified spans and fell back to the extraction bucket.** On solidpower all four seams
held. This is the first completing real lease where one did not — and it fell back silently, exactly as
the Step-484 design allows.

---

# 5. assessment_status

```
{'assessed': 30, 'not_assessed': 2}
  LP-12  Early Termination   not_applicable
  LP-23  Percentage Rent     broken_xref
```

Both `not_assessed` entries are correct: neither provision exists.

---

# 6. THE QUALIFIER PASS — IT FIRES, CONTRADICTING THE BRIEF, AND TWO LINKS ARE WRONG

**14 LPs annotated.** The brief expected Atlas-derived patterns to find nothing on a shopping-centre
lease; they found plenty. **`section_ref` also resolves here** (`Section 20.1`, `Section 16.4`,
`Section 3.2`), unlike solidpower where every one was `None`.

**But the subject-linking produces two clear errors:**

> **LP-31 Co-Tenancy** annotated with *"(c) Landlord shall not be liable to Tenant in damages or
> otherwise if any one or more of said utility"* — a **utility-interruption** liability limit. It has
> nothing to do with co-tenancy.

> **LP-14 Force Majeure** annotated with *"Tenant that Landlord has unreasonably withheld, conditioned
> or delayed any consent or approval, but Tenant's sole remedy"* — a **consent** clause, not a
> force-majeure qualifier. It is also a mid-sentence fragment.

**And the `in no event shall` false positive from Step 525 recurs heavily** — 6 of the LP-09
annotations are `in no event shall` matches on assignment, security-deposit and memorandum-of-lease
clauses.

**A further concern specific to this document:** several annotations quote text from the *Existing
Exclusives* schedule — *"as defined in the Lease with Michaels Stores, inc."*, *"such lessee's Leasable
Square Feet"*. **The qualifier pass is attributing other parties' lease language to this document's
findings**, which is the same attribution error the panel avoided.

---

# 7. AS A LAWYER WOULD READ IT

```
Findings
3 issue area(s) require attention, 0 worth reviewing, 2 NOT ASSESSED, 27 covered.
```

## The three findings are substantive

**LP-31 Co-Tenancy** is the best of them, and it is genuinely good for this document:
> *"No co-tenancy protection... Tenant can be stuck paying full rent and operating even if an anchor
> tenant closes or occupancy drops and customer traffic falls. Tenant has no defined rent reduction,
> closure right, or exit remedy tied to loss of key co-tenants."*

**For a fast-casual restaurant on an outlot of a shopping centre anchored by Dollar Tree and Michaels,
that is exactly the risk a tenant's lawyer would flag.** It names four specific missing elements. It is
not generic.

**LP-28 Compliance with Laws** is specific and actionable: *"Tenant may be required to fund expensive
structural compliance (ADA ramps, fire suppression upgrades) that should be landlord's
responsibility."*

**LP-14 Force Majeure** names four missing elements correctly, though its exposure line — *"common law
impossibility doctrine rarely applies to commercial leases"* — is a general statement of law rather
than an observation about this lease.

## But the headline number is wrong, and this is the serious finding

```
LP      name                  state            requires_attention  DISPLAYED AS   elements
LP-20   Exclusivity           review_needed    True                COVERED        0/7 present
LP-21   Guaranty of Lease     partial          True                COVERED        3/5 present
LP-27   Landlord Default      review_needed    True                COVERED        3/10 present
```

**LP-20 Exclusivity has ZERO of seven elements present, a withheld verdict, `requires_attention:
True` — and the report shows it inside the 27 "covered".**

**A tenant on a shopping-centre outlot with no exclusivity protection whatsoever is told that
provision is covered.** For this document type that is the single most consequential omission a
retail tenant faces, and the report buries it in the clean bucket.

**This is Step 521's defect, unfixed, now observed on a real lease where it materially misleads.** Step
521 measured 24 of 32 such LPs on Atlas and recorded the `partial_typical` / `review_needed` →
`COVERED` fall-through as an open question. **On a synthetic warehouse lease it was an arithmetic
inconsistency. Here it is a lawyer reading "covered" about the protection their client does not have.**

**The qualifier annotations are noise on this report** — *"NOT WEIGHED — elsewhere in the lease"* with
mid-sentence fragments, twice attached to the wrong subject. They would cost a reader time and give
nothing back.

---

# WHAT IS NOT ESTABLISHED

- **The locator was not tested at high heading count.** ex6-4 has 8. carothers (213) remains unrun.
- **Ground truth covers the four named concepts only.** The other 29 LPs' verdicts on this document
  were not read — including LP-27's `review_needed` and LP-31's `missing`, which I judged plausible
  from the document type rather than by reading the relevant sections.
- **LP-21 being "right for the right reasons" rests on the three element labels**, not on reading the
  evaluators' citations against §(w) and Exhibit D.
- **One run.** Extraction and coverage are both non-deterministic (Steps 464, 517).
- **The 45% locator figure is my metric**, not Step 479's.
- **Whether the panel would have attributed Dollar Tree's exclusive to this tenant under a different
  extraction shape is unknown** — one sample.
- **Nothing was tuned, no clue list was touched, nothing was deployed.**
