# Step 540 — The helper was built at Step 539. All six sites proven identical. The briefed numbers do not match anything measured.

**Date:** 2026-09-03 · **Instruction:** `build_log/540_chat_instruction.md`
**No new code. Verification only. Tests: 406 passed, 3 skipped. Not deployed.**

---

# 0. FOUR PREMISE CORRECTIONS

**"Per Step 539's design: three categories — conforming, unfavorable_or_conditional, deviating."**
Step 539's design is **five** categories, and none carries those names:

```
needs_attention | worth_reviewing | minor_gaps | not_assessed | covered
```

The strings `conforming`, `unfavorable_or_conditional` and `deviating` appear nowhere in the Step-539
status or in the code it shipped.

**"Expected: 27 covered becomes 3 conforming, 13 unfavorable_or_conditional, 6 deviating, 11
not_assessed — confirm the arithmetic sums to 33."** Three problems:

- **The total is 32, not 33.** `butler_crossing` has 32 coverage entries. 3+13+6+11 = 33 cannot be a
  partition of it.
- **"27 covered" is two steps stale.** It was 27 as shipped at Step 537, 18 after Step 538, and **0
  after Step 539**.
- **The measured distribution is** `needs_attention 4, worth_reviewing 8, minor_gaps 18,
  not_assessed 2, covered 0` = **32**.

**"ONE helper. Six call sites, each replaced."** **Already done at Step 539.**
`lease_display.summarize_display_buckets` exists at `lease_display.py:312` and
`lease_coverage.py:1157-1158` delegates to it. There was nothing left to build.

**"Do NOT change export_findings."** `export_findings` does not exist. `grep -rn "export_findings"`
across `cam/` and `05 Lease Analyzer/` returns **nothing**. Noted here because Step 541 is built on it.

---

# 1. THE SIX SITES, PROVEN BY EXERCISE

Run against the Step-537 result, zero-count buckets normalised out:

```
helper              {'needs_attention': 4, 'worth_reviewing': 8, 'minor_gaps': 18, 'not_assessed': 2}
1 summarize_coverage {'needs_attention': 4, 'worth_reviewing': 8, 'minor_gaps': 18, 'not_assessed': 2}   covered_count=0
2 report_gen loop    {'needs_attention': 4, 'worth_reviewing': 8, 'minor_gaps': 18, 'not_assessed': 2}
4 batch counts       {'needs_attention': 4, 'worth_reviewing': 8, 'minor_gaps': 18, 'not_assessed': 2}
6 sections           {'coverage_gaps': 12, 'minor_gaps': 18, 'not_assessed': 2}

sites 1,2,4 identical to helper : True
sections consistent             : True   (coverage_gaps 12 = needs_attention 4 + worth_reviewing 8)
every LP accounted for          : True   (sum = 32 = len(coverage_assessment))
```

| # | site | status |
|---|---|---|
| 1 | `lease_coverage.summarize_coverage:1157` | delegates to the helper |
| 2 | `lease_report_generator:256` | bucket loop, explicit branch per bucket |
| 3 | `lease_report_generator:422` | `resolve_sections` |
| 4 | `summary_generator:1179` | `bucket_counts` over `BUCKET_SECTION_HEADERS` |
| 5 | `summary_generator:1241` | section tiers over `BUCKET_ORDER_BY_PERSPECTIVE` |
| 6 | `summary_generator:1524` | `resolve_sections` |

**None computes a variant afterwards.** Sites 3 and 6 return `coverage_gaps: 12` rather than the two
component buckets — **that is by design, not drift**: `resolve_sections` merges `needs_attention` and
`worth_reviewing` into one rendered section, and the merge is arithmetically exact.

## A false alarm in my own first comparison, recorded

My first equality check printed `ALL SIX IDENTICAL: False`. **That was my comparison, not a
disagreement** — `collections.Counter` omits zero-count keys while the helper's dict includes all
seven. Normalising zero keys showed exact agreement. **I checked before reporting a discrepancy that
did not exist.**

---

# 2. THE TOP LINE

No artefact changed in this step, because no code changed. For the record, the progression:

```
Step 537 (shipped): 3 require attention, 0 worth reviewing, 2 NOT ASSESSED, 27 covered.
after Step 538:     4 require attention, 8 worth reviewing, 2 NOT ASSESSED, 18 covered.
after Step 539:     4 require attention, 8 worth reviewing,
                    18 substantially addressed with minor gaps, 2 NOT ASSESSED, 0 covered.
```

**`not_assessed` is already reported beside the top line and never inside it** — that was Step 522's
bucket and Step 539 confirmed it. The brief's requirement on this point was already satisfied.

---

# WHAT IS NOT ESTABLISHED

- **No code was written in this step.** Everything reported is verification of what Step 539 shipped.
- **The three-category scheme in the brief was not built**, because it conflicts with the five-category
  scheme measured and shipped at Step 539 and its expected numbers do not partition 32. **If
  `conforming` / `unfavorable_or_conditional` / `deviating` is genuinely wanted as the top line, that
  is a rename plus a re-grouping and needs its own brief with numbers that reconcile.**
- **Verified on one result file.** The six-site agreement is exact on butler_crossing; Atlas and
  solidpower were not re-checked.
- **`resolve_sections`' merge is consistent but not identical in shape** to the other four sites, so a
  future reader comparing raw dicts will see a difference that is legitimate.
