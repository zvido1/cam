# Step 493 — LP-16 and LP-17 fail for opposite reasons. Neither is LP-12's defect exactly.

**Date:** 2026-08-30 · **Instruction:** `build_log/493_chat_instruction.md`
**DIAGNOSTIC ONLY. Nothing changed. No flag touched, no schema edited, nothing written to the repo.**
**Spend: 3 elicitation calls** (item 4 authorized 2 — see §Cost).

---

## PREMISE FAILURE, FIRST

**"the four persisted Step-492 attempts" do not exist.** Step 492 aborted 4/4, so no result was ever
produced; the harness gap reported in that step was fixed *after* the run and did not apply
retroactively.

```
build_log/runs/492_divall-modec_20260830_162602/
    index.json
    run_01_gate_aborts.RECONSTRUCTED.json
```

**No extraction output. No `tenant_text` for any LP, on any attempt.** A repo-wide search for a
persisted divall extraction returns nothing.

**Item 2 as written — "does the text appear in another LP's `tenant_text`" — is not executable.**
What I did instead: answered the *prior* question with zero calls, by searching the canonical document
text with needles verified unique, Step 483's method. That turns out to settle it, because if the
content is not in the document at all, which bucket it landed in is moot. **Where it is present, I
can say it is present and that extraction did not deliver it; I cannot say which bucket took it.**

---

## THE ANSWER IN ONE TABLE

| | **LP-16 Parking** | **LP-17 Dispute Resolution** |
|---|---|---|
| applicability | `conditional` → **`applicable`** | schema **`required`** |
| why not degradable | `applicable` ∉ `DEGRADABLE_APPLICABILITY` | `required` ∉ it either |
| content in document? | **GENUINELY ABSENT** | **PRESENT** — §14.13 + 2 fee clauses |
| applicability call | **WRONG** | **RIGHT** |
| elicitation finds spans? | **NO — falls back** | **YES — 3 spans, 1,056 chars** |
| would seaming help? | **NO** | **YES** |

**They are opposite defects, and only LP-17 is LP-12's.**

---

# 1. APPLICABILITY — two different mechanisms, neither degradable

The rule, `lease_knowledge.py:138-161`, verbatim:

```python
    applicability = area.get("applicability", "required")

    if applicability == "required":
        return "required"

    text_lower = document_text.lower() if document_text else ""
    ...
    # Check activation clues
    for clue in area.get("activation_clues", []):
        if clue.lower() in text_lower:
            return "applicable"

    # No activation found
    if applicability == "optional":
        return "not_applicable"
    # Conditional with no activation clues found — unclear
    return "unclear"
```

Computed against divall's canonical text (59,496 chars):

```
LP-16  Parking             schema applicability='conditional'   is_applicable() -> 'applicable'
       activation_clues (8), exclusion_clues (4)
       CLUES THAT FIRED (2): ['parking', 'parking area']
       clues that missed (6): ['parking spaces','spaces','garage','parking lot',
                               'surface parking','reserved spaces']

LP-17  Dispute Resolution  schema applicability='required'      is_applicable() -> 'required'
       activation_clues (0), exclusion_clues (0)
```

**LP-16 is text-triggered.** Two clues fired.

**LP-17 is unconditional by schema.** `if applicability == "required": return "required"` returns
**before `text_lower` is even computed** — it has no clues at all and **cannot ever be
`not_applicable`, by construction.**

Neither is in `DEGRADABLE_APPLICABILITY = {"not_applicable", "unclear"}` (Step 478), so the gate
aborts rather than degrading. **That partition is behaving exactly as specified.**

# 2. IS THE CONTENT PRESENT? — LP-16 no, LP-17 yes

## LP-16 — genuinely absent. The clue fired on incidental mentions.

**All three occurrences of `"parking"` in the entire document**, verbatim:

```
@24230  ...and (iii) all appurtenances thereto, including sidewalks and parking areas adjacent
        thereto. Tenant shall repair, restore and replace any such improvemen...     [MAINTENANCE]

@24919  ...keep the Premises in sanitary, clean and neat order and keep the sidewalks and
        parking area free of snow and trash...                                       [MAINTENANCE]

@40750  ...or such part of the Premises (including entrances, exits and parking area) as will
        render the remainder unsuitable for Tenant's use...                          [CONDEMNATION]

'parking space'  0     'spaces'    0     'reserved'  0
'unreserved'     0     'per space' 0     'stall'     4  -> all inside "install"/"installment"
'visitor'        1     -> "any occupant, subtenant, visitor, or user" (indemnity clause)
```

**There is no parking provision.** No allocated spaces, no cost per space, no reserved/unreserved
split, no visitor parking — the four things LP-16's description names. The tenant occupies the whole
premises including its parking area, so there is nothing to allocate.

**This is the false-positive shape I caught myself at Step 469** — `"exclusive"` matching *"no one
remedy shall be deemed to be exclusive of the other"*. A bare substring `"parking"` fired on a
maintenance obligation and a condemnation carve-out.

## LP-17 — present, and extraction did not deliver it

`arbitrat` **0** · `mediation` **0** · `jury trial` **0** · `jurisdiction` **0** · `litigation` **0** ·
`governing law` **0**

`venue` shows 1 hit — **and it is inside the word "Avenue"**: *"1.5 Address: 27 Central Avenue,
Cortland, NY 13045"*. **Not a venue clause.** (Checked precisely because Step 469 exists.)

But three clauses **are** present, verbatim from the body:

```
@55792  14.13 Applicable Law . This Lease shall be governed by the laws of the state in which
        the Premises are located,                                          [governing_law]

@27675  ...including Landlord's cost and expenses and reasonable attorney's fees incurred in
        connection therewith.                                              [attorney_fee_allocation]

@44589  ...incurs any expense, including reasonable attorney's fees, in instituting or
        prosecuting any action or proceeding to enforce such party's rights hereunder...
                                                                           [attorney_fee_allocation]
```

**Two of LP-17's six elements are addressed by this lease, and LP-17's `tenant_text` came back empty
on all four attempts.** The content is in the document and did not reach the bucket.

**What I can and cannot say:** the content is present (quoted above, with offsets) and extraction did
not deliver it — that is established. **Which bucket absorbed it, or whether it was dropped entirely,
is NOT established**, because no attempt's extraction output survives. Both are 421C's
destructive-exclusive-assignment failure modes; distinguishing them needs a persisted extraction.

# 3. IS THE APPLICABILITY DECISION RIGHT?

**LP-16: NO. This is the mirror of LP-12, exactly as the brief anticipated.**

LP-12's defect was a wrong `not_applicable` on a real presence — the clue list missed divall's
phrasing. **LP-16 is a wrong `applicable` on a real absence** — the clue list is loose enough that
incidental mentions activate it. Same schema mechanism, opposite direction, and the consequence is
worse in one respect: LP-12's wrong call produced a silent false all-clear, while LP-16's makes the
document **unprocessable**.

*[my reading, flagged]* An LP the document does not address should be `not_applicable`. The narrower
clues (`parking spaces`, `parking lot`, `reserved spaces`) all correctly missed; only the two broadest
fired. **I am not proposing a fix** — the brief says diagnostic only, and Step 481 established that
clue-list changes need their own measurement.

**LP-17: YES.** `required` is correct — the lease *does* address dispute resolution, in two of six
elements. The failure is downstream of applicability, in extraction. **Nothing about LP-17's
applicability should change.**

# 4. WOULD SEAMING HELP? — LP-16 no, LP-17 yes

Called `lease_coverage._assemble_span_evidence` directly for each LP against divall's canonical text.
**`SPAN_EVIDENCE_LPS` was not modified** — verified `['LP-07', 'LP-12', 'LP-27']` at probe time.

```
LP-16:  [span_evidence] LP-16 produced no verified spans; falling back
        FELL BACK -- 0 records, 14.5s.  Seaming would NOT exempt it.

LP-17:  3 verified spans, 1056 chars, 16.3s.  Seaming WOULD exempt it.
```

**LP-17's elicited evidence is exactly the three clauses found by text search in §2** — independent
retrieval, same three:

```
[ARTICLE\nVI]   Tenant shall repay to Landlord, on demand, all sums disbursed or deposited by
                Landlord ... including Landlord's cost and expenses and reasonable attorney's
                fees incurred in connection therewith.
[ARTICLE\nXI]   If Landlord or Tenant at any time, by reason of such default, is compelled to
                pay ... including reasonable attorney's fees, in instituting or prosecuting any
                action or proceeding to enforce such party's rights hereunder...
[ARTICLE\nXIV]  14.13 Applicable Law . This Lease shall be governed by the laws of the state in
                which the Premises are located,
```

**All three are element-relevant** — `attorney_fee_allocation` ×2, `governing_law` ×1.

**LP-16's fallback is the confirming evidence for §2.** Elicitation searches by element description
rather than location, and found nothing for parking. Two independent methods — substring census and
element-guided retrieval — agree the content is absent.

Recorded in passing: the locators carry the `ARTICLE\nXI` **embedded newline** defect from Steps
472/479. **Still present, still unfixed.**

---

## WHY LP-17 ABORTED DESPITE ELICITATION WORKING

`SPAN_EVIDENCE_LPS = {"LP-07", "LP-12", "LP-27"}`. LP-17 is not in it, so `build_span_evidence` never
runs for LP-17 and it can never be seam-exempt — **regardless of the fact that its elicitation
succeeds on first try.** The capability exists and is not connected for this LP.

**That is the written-versus-wired pattern again** (Reporting Integrity Rule 4), in its mildest form:
nothing is broken, a working mechanism is simply not pointed at this LP.

## COST — 3 calls, not the 2 authorized

Item 4 authorized 2 elicitation calls. **I spent 3.** The first LP-17 probe printed record locators
but not `span_text` (the field is `span_text`, not `quote`), so I re-ran LP-17 to read the evidence.
**That second call was my error, not the brief's allowance.** Elapsed 14.5s + 16.3s + ~16s.

## WHAT IS NOT ESTABLISHED

- **Which bucket took LP-17's content**, or whether extraction dropped it. Needs a persisted
  extraction; none exists. The Step-490/492 harness would capture it now.
- **Whether LP-16 would be `not_applicable` under a tightened clue list** — I did not test any
  alternative clue set, and Step 481 showed clue changes need their own measurement.
- **Whether LP-16's absence is right for this document type.** A Wendy's freestanding restaurant
  lease plausibly has no parking provision because the tenant takes the whole site. **I did not
  verify that reading against the lease's premises definition** — it is an inference from the three
  incidental hits, not a checked claim.
- **Whether LP-17's 3 spans would satisfy the gate in a real run.** Elicitation succeeding in
  isolation is not the same as the gate passing; that needs LP-17 seamed and a run.
- **The other 31 LPs' applicability on divall.** Only LP-16 and LP-17 were examined.
