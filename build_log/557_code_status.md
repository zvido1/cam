# Step 557 — The panel got all six LP-29 elements right, and the headline the lease contradicted three times over is gone.

**Date:** 2026-09-04 · **Instruction:** `build_log/557_chat_instruction.md`
**Tests: 445 passed, 3 skipped, 12 subtests (437 → 445; 8 new). `_RESERVED_PATTERN` untouched. No schema string hedged. Not deployed.**

---

# 0. THE RESULT

```
                         BEFORE                              AFTER (557)
solidpower broken_xref   ['LP-07', 'LP-29']                  []
divall     broken_xref   ['LP-01', 'LP-02', 'LP-21']         ['LP-02', 'LP-21']
```

**solidpower LP-29, the case that named this arc:**

> **was:** *"Landlord may enter premises without notice, at any time, for any purpose"* —
> `broken_xref`, `not_assessed`, 0 element verdicts
>
> **now:** *"Landlord access can disrupt operations"* —
> `covered_unfavorable`, `assessed`, **6 element verdicts, 5 present**

---

# 1. THE TEST, AND WHAT IT MOVES

```
placeholder : \b(intentionally\s+omitted|this\s+section\s+intentionally|omitted\s+intentionally)\b
              |[\[\(]\s*reserved\s*[\]\)]                                    (unchanged, Step 555)
label bdry  : \n | \d+\.\d+(\.\d+)* | \(\s*[A-Za-z0-9]{1,3}\s*\)
              | (section|article|addendum|exhibit|schedule|paragraph)\s*[A-Z0-9IVXL.-]*
prose       : a remaining segment of >= 6 words containing a finite verb
```

**Prose is identified positively and scaffolding by elimination**, because labels are open-ended and
prose is not. Empty prose list ⇒ the placeholder is the provision.

## Across all 45 corpus files

```
placeholders surviving the Step-555 pattern : 38
   placeholder ALONE in its clause  -> short-circuits : 23
   prose BESIDE it -> released to the panel           : 15
```

**Nothing is newly short-circuited.** The rule only ever *releases* — it adds a condition to an
existing branch and never creates one. The 15 released, judged in the clause each sits in:

```
albireo     "18.2 Landlord's Options . Except in the event of a Permitted Transfer..."   20 prose segs
albireo     "25.1 Events of Default . The occurrence of any one or more of the foll..."  10
atreca x2   "22. Assignment and Subletting . (a) General Prohibition . Without Land..."  28, 26
butler      "5. RENT (a) Minimum Rent : Tenant shall pay Landlord, at Landlord's ad..."  15
ncino x2    "ARTICLE 2. LEASE OF PREMISES QUIET ENJOYMENT. 2.01 Premises ..."            61
quanterix   "ARTICLE VIII. MISCELLANEOUS 8.1. Security Deposit . Simultaneous with..."  215
T-12 x3     "Section 13.3. Landlord Default. Landlord shall be in default under thi..."   2
```

**The largest released block is 49,351 characters with 210 prose segments.** Under the old rule a
single `Intentionally Omitted` inside it marked every expected element of that LP missing.

## Rejected first, recorded in-comment

- **Residue ratio** — separates 92–96.5% from 32.7–49.4% cleanly, but ex6-4 LP-23 is a **true** absence
  at 94.0%. Any threshold loses it.
- **Elements-not-found** — FN=2. `_assess_elements` matched three LP-21 elements off the single word
  **GUARANTY in the title of the clause that was omitted**. A keyword matcher cannot decide whether a
  clause exists: its name survives it.

---

# 2. THE PANEL SEES IT. PROVEN BY BUILDING THE PROMPT.

The guard clears a **local filtered list**; `ns` is untouched, and `_ns_candidates =
ns_signals.get(pid, [])` is what reaches the evaluators. Built for divall LP-01:

```
NEGATIVE SPACE CANDIDATES (candidate evidence only -- verify against lease text):
[
  {
    "signal_type": "reserved_or_omitted",
    "evidence": "Intentionally Omitted"
  }
]

LEASE PROVISION TEXT:
3.1 One Time Fixed Rental Charge . Intentionally Omitted .
3.2 Base Rent . During the Term, Tenant covenants and agrees to pay to Landlord, in advance
on the first day of each month at Landlord's address, without demand or offset whatsoever...
```

**The prompt's own caveat is *"candidate evidence only — verify against lease text"*.** That is
`lease_negative_space`'s contract, honoured: evidence to the layer that can judge it.

**Confirmed on the live run** — divall LP-01's persisted assessment carries
`negative_space_signals: ['Intentionally Omitted']` alongside six element verdicts.
`test_the_signal_is_not_removed_from_the_evidence_list` pins that clearing the filtered list cannot
empty `ns`.

---

# 3. LP-23 RELEASES. NOT TUNED AROUND.

```
ex6-4 LP-23  TRUE absence  prose=2  ->  RELEASED to the panel
   first prose: "Financial Statements : Tenant shall, within Ten (10) days..."
```

**Its only prose is Section 26(q), misrouted into LP-23's block** — a routing error, exactly as the
brief anticipated. **The rule was not adjusted to rescue it.** What the panel then makes of a block
still containing `(b) Percentage Rent : [intentionally omitted]` is unmeasured: ex6-4 was not re-run
this step, and I am not predicting it.

**The two genuine absences still short-circuit**, on the live divall run:

```
LP-02 Rent Escalation   broken_xref  not_assessed  0 elements   "Rent frozen at initial amount..."
LP-21 Guaranty of Lease broken_xref  not_assessed  0 elements   "If a guaranty was negotiated..."
```

Both unchanged, both correct. **Step 495's first rule holds.**

---

# 4. THE RE-RUNS

## solidpower LP-29 — the panel got all six elements right

```
LP-29.notice_period                   explicitly_present
LP-29.emergency_entry                 explicitly_present
LP-29.minimize_interference           explicitly_present
LP-29.permitted_purposes              explicitly_present
LP-29.tenant_representative_present   missing
LP-29.entry_frequency_timing          explicitly_present
```

Against the lease, verbatim:

| element | verdict | the text |
|---|---|---|
| notice_period | present | *"after giving Tenant reasonable notice thereof, which may be oral notice"* |
| emergency_entry | present | *"except in cases of real or apparent emergency, in which case no notice shall be required"* |
| minimize_interference | present | *"Provided that such actions shall not materially interfere with Tenant's use and quiet enjoyment"* |
| permitted_purposes | present | five enumerated: Building Operations, Security, Repairs, Prospective Purchasers, Prospective Tenants |
| tenant_representative_present | **missing** | **correct — the lease grants no such right** |
| entry_frequency_timing | present | *"at all reasonable hours"*, *"with one (1) days prior notice"* |

**Six of six correct, including the one absence.** State `covered_unfavorable`, display
`UNFAVORABLE TERMS / needs_attention`, headline **"Landlord access can disrupt operations"** with the
statement *"Landlord can enter the premises, including without advance notice in defined emergencies,
creating business interruption risk…"* — **"in defined emergencies" is the qualification the old
sentence flatly denied.**

`covered_unfavorable` is in `_MODEL_STATES`, so this headline is model-written against the record
rather than drawn from the canned schema string.

## solidpower LP-07 — reaches the panel, 4 of 6

```
proportionate_share_calculation  explicitly_present     cam_cap             missing
included_expense_categories      explicitly_present     tenant_audit_rights missing
excluded_expense_categories      explicitly_present     reconciliation_timeline explicitly_present
```

`partial`, headline **"CAM exposure uncapped and unauditable"** — which is precisely what the two
missing elements say. **Accurate.**

## divall LP-01 — reaches the panel, and base rent is found

```
BEFORE  broken_xref  status=None        0 elements   "No enforceable rent obligation"
AFTER   partial      status=assessed    6 elements   3 present, 1 unresolved, 1 missing
        LP-01.base_rent_amount           explicitly_present
        LP-01.additional_rent_definition explicitly_present
```

**`base_rent_amount: explicitly_present` is the fix landing.** The provision the old report called
non-existent is found by the panel.

**But the headline is still wrong in kind**, and it is not this step's defect:

> *"Tenant's payment obligation and enforcement timeline undefined; creates ambiguity in default
> proceedings"*

State is now `partial` with **one** adverse missing element, so it matches
`if state == "partial" and missing:` — **the half of `partial` Step 547 deliberately left alone and
Step 549 measured as still broken.** Reaching the panel fixed the verdict; the prose layer still
describes a 6-element provision with 3 present as "undefined".

## Run health

```
557 solidpower  degraded=True  reason=evaluator_fallback
   LP-24 role B: gpt-5.5 -> gpt-5.4, "reasoning_exhaustion", class=hard
557 divall      degraded=True  reason=extraction_completeness_failed
   failed LPs ['LP-30','LP-31','LP-32'] -- IDENTICAL to the 496 BEFORE run
```

**Neither is caused by this change.** divall's extraction failure is byte-identical to the pre-change
run. solidpower's fallback is a provider event on LP-24, an LP this change does not touch — and the
pattern-only Step-555 run of the same document had zero fallbacks, so it is run-to-run provider
variance.

---

# WHAT IS NOT ESTABLISHED

- **ex6-4 was not re-run.** §3's release is measured on the stored block; what the panel concludes for
  LP-23 is unknown.
- **divall LP-01's headline is still wrong** — `partial`-with-a-gap still emits the canned schema
  string. That is Step 549's Defect 2, unfixed, and out of this brief.
- **The prose test is a heuristic.** The six-word floor and the verb list are measured on this corpus
  and nothing else. When it is wrong the cost is now an extra panel call rather than a false sentence,
  which is why a heuristic is tolerable here — but it is a heuristic.
- **The corpus-wide §1 figures use a proxy block** — text between section headings — because Mode C
  does not persist the extraction `provisions` the detector actually runs on. The seven signalled
  blocks in §3 are the real thing; the 38/23/15 split is an approximation.
- **One run per document.** LP-29's six correct verdicts are one observation; Step 491 measured 13 of
  32 LPs moving across identical-configuration runs, so a repeat could differ.
- **`covered_unfavorable` on LP-29 was not audited beyond its six elements.** Whether "unfavourable" is
  the right characterisation of a clause with a non-interference proviso is a judgement I did not test.
- **Two runs were spent, ~169 provider calls.** ex6-4 and Atlas were not re-run, so the 15 released
  placeholders elsewhere in the corpus remain untested end to end.
