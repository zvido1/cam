# Finding: the 423 stack works on a real lease

**Date:** 2026-08-20
**Status:** VERIFIED LIVE, standalone. Nothing wired, no pipeline module touched.
**Method:** `build_log/423_stack_smoke.py`, output persisted at `build_log/423_stack_smoke_out/`.

---

## Why this was needed

`build_log/FINDING_evidence_architecture_unwired.md` established that the whole 423/425/427 stack
has **no production caller** and has only ever run against test fixtures. Before anyone builds a
seam to it, the question had to be answered: **does it do the thing it was built to do, on a real
document?**

If it could not find the clauses extraction loses, wiring it would change nothing and the problem
would be recall in the elicitor — a different project.

## Setup

```
lease              05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt
canonical source   31,755 chars | hash da9b5655... | profile canonical_whitespace_v2
elicitor           google:gemini-3.1-pro-preview  (ELICITATION_PRIMARY, unmodified)
elements           expected_elements_305 from retail_lease_knowledge.json via
                   load_expected_elements_by_lp() -- the SAME file lease_coverage_305 reads.
                   Not fixtures.
entry point        elicit_and_resolve_for_lp(), called exactly as defined
```

Sanity check before calling: both needles confirmed present in the canonical text.

## LP-07 — the definitional clause IS found

```
6 elements | 1 provider call | 23.1s | raw 5 -> deduped 5 | all verified

NEEDLE "shall mean 22.4%" found in a VERIFIED span: TRUE

span [1738,1889]  elicited_by = ['LP-07.proportionate_share_calculation']
  "Proportionate Share" shall mean 22.4%, representing the ratio of the rentable
  area of the Demised Premises to the total rentable area of the Building.
```

**This is the exact clause Mode C extraction delivers to LP-07 in 0 of 6 runs**
(`FINDING_definitional_clause_loss.md`). The elicitor found it on the first call, resolved it to
verified offsets through the unmodified 423A resolver, and attributed it to
`LP-07.proportionate_share_calculation` — **the same element the panel unanimously reported as
undefined** at `confidence = high`, `3/3` agreement.

## LP-12 — also found. A correction to this test's own first result.

The first pass of this smoke test reported `found=False` for LP-12. **That was a defect in the
test, not in the elicitor**, and it is recorded here rather than quietly fixed.

The needle used was `"Termination Right"`. That is the section **heading**. The elicitor quotes
clause **bodies**: the returned span begins at char 17183, and the heading sits at 17150 — it
started 33 characters after the heading.

```
lease[17150:] = 'Section 13.2. Termination Right. If the damage cannot be restored within...'
span [17183,17541] = 'If the damage cannot be restored within two hundred forty (240) days, or if
                      the damage occurs during the last twelve (12) months of the Term and the
                      cost of restoration exceeds fifty percent (50%) of the replacement value
                      of the Building...'
```

Re-tested against body needles verified unique in the lease:

| needle | what it is | verified spans containing it |
|---|---|---|
| `replacement value of the Building` | §13.2 body | 1 — `[17183,17541]` |
| `two hundred forty (240) days` | §13.2 and §13.3 | 2 — `[17183,17541]`, `[17812,18035]` |
| `Termination Right` | §13.2 **heading** | 0 — the wrong needle |

**§13.2 is found. So is §13.3.** Plus five more termination triggers — landlord-default
termination, eminent-domain total taking, 20% partial taking, recapture on assignment, and default
remedies. **7 verified spans**, where extraction cross-files §13.2 to LP-12 in only 2 of 6 runs and
finds none of the others.

**Lesson for future probes:** needle on clause bodies, not headings. A heading-word needle tests
whether the extractor copied the heading, which is not the question.

## Two things the run demonstrated incidentally

- **`elicited_by` came back as a union on live data** — `['LP-12.triggering_conditions',
  'LP-12.notice_period']` on five of seven spans. The multi-source provenance design works outside
  its tests.
- **Dedupe collapsed 13 raw records to 7** on real offsets.

## Conclusion

**The architecture does the thing it was built to do.** On a real lease, with the real elements, in
one call per LP, it located both clauses extraction loses — including the definitional clause that
caused the false LP-07 finding.

**This is not a recall problem in the elicitor. Wiring it is not futile.** The condition for
abandoning the direction is not met.

## What is NOT established

- Two LPs, one lease, one call each. **Not a recall measurement.**
- **Precision was not assessed.** Only the needle question was asked. Several of LP-12's 7 spans
  are arguably other LPs' territory; whether the returned set is the *right* evidence for an LP's
  elements is a separate question this test does not touch.
- LP-07 returned 5 spans for 6 elements. Which element went unserved was not checked.
- **Cost.** `elicit_and_resolve_for_lp` is one call per LP. At 33 LPs that is 33 calls against
  extraction's 1 — a cost any seam work must reckon with.
