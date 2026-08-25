# Step 480 — LP-12 applicability: why the false all-clear reproduces

**Date:** 2026-08-24 · **Instruction:** `build_log/480_chat_instruction.md`
**DIAGNOSTIC ONLY.** No fix, no runs, nothing changed. Computed offline from the schema, the two
canonical documents, and nine persisted runs (eight Atlas, one divall).

---

## Q1 — The rule, quoted

`lease_knowledge.py:119-161`, the whole decision:

```python
def is_applicable(provision_id: str, document_text: str) -> str:
    area = get_issue_area(provision_id)
    if not area:
        return "unclear"

    applicability = area.get("applicability", "required")

    if applicability == "required":
        return "required"

    text_lower = document_text.lower() if document_text else ""

    # Check exclusion clues first — if present, issue area does not apply
    for clue in area.get("exclusion_clues", []):
        if clue.lower() in text_lower:
            return "excluded"

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

**It keys on literal case-insensitive substring matching of a fixed phrase list.** No parsing, no
model, no structure — `clue.lower() in text_lower`.

LP-12's rule, verbatim from `retail_lease_knowledge.json`:

```json
"applicability": "optional",
"default_when_unclear": "not_applicable",
"activation_clues": [
    "early termination right", "early termination option", "right to terminate early",
    "break option", "break clause", "kick-out clause", "co-tenancy termination",
    "go dark", "termination option", "termination fee"
],
"exclusion_clues": [
    "no right to terminate prior to expiration", "tenant may not terminate early",
    "no early termination"
]
```

**Every one of the ten activation clues is negotiated-option market vocabulary** — the language of a
bargained-for exit right in a term sheet.

## Q2 — The decision path, both documents

Identical on both. No exclusion clue hit; **all ten activation clues absent**; `applicability ==
"optional"` → `return "not_applicable"`.

| clue | Atlas | divall |
|---|---|---|
| all 10 (`break clause`, `kick-out clause`, `go dark`, `termination option`, `termination fee`, …) | **absent** | **absent** |

What the documents *do* contain:

| phrase | Atlas | divall |
|---|---|---|
| `right to terminate` | 1 | 1 |
| `terminate this Lease` | 5 | 1 |
| `Termination Right` | 2 | 0 |
| `shall terminate and expire` | 0 | 1 |

Atlas: *"…neither party has exercised a termination right, Tenant shall have the right to terminate
this Lease upon thirty (30) days' written notice to Landlord."*
divall: *"…if a Total Destruction of the Premises occurs during the last five (5) Lease Years of the
Term, Tenant will have the right to terminate the Lease…"*

**The clue list looks for how a termination right is *negotiated*; both leases express one in ordinary
operative language, embedded in casualty and condemnation articles.** `"termination option"` does not
substring-match `"the right to terminate this Lease"`. Nothing in the rule can bridge that.

## Q3 — LP-12 is the only `optional` LP, but the exposure is wider

Across the 33 enabled LPs: **21 `required`, 11 `conditional`, 1 `optional`.**

**LP-12 is the sole `optional` issue area** — the only one where a clue miss returns `not_applicable`
*directly*, with no `unclear` step.

But 10 of the 11 `conditional` LPs carry `default_when_unclear: "not_applicable"`, so a clue miss
lands them in the **same coverage state** by a different route:

| LP | name | act. clues | default_when_unclear |
|---|---|---|---|
| LP-04 | Security Deposit | 5 | not_applicable |
| **LP-07** | **CAM** | 9 | **applicability_unclear** ← the only exception |
| LP-15 | Signage Rights | 8 | not_applicable |
| LP-16 | Parking | 8 | not_applicable |
| LP-20 | Exclusivity | 8 | not_applicable |
| LP-21 | Guaranty of Lease | 10 | not_applicable |
| LP-22 | SNDA | 10 | not_applicable |
| LP-23 | Percentage Rent | 8 | not_applicable |
| LP-30 | Estoppel Certificate | 7 | not_applicable |
| LP-31 | Co-Tenancy | 10 | not_applicable |
| LP-32 | Hazardous Materials | 15 | not_applicable |

**So 11 of 33 LPs can reach `not_applicable` purely because a phrase list missed.** The difference is
only in what the entry *says*: LP-12 asserts *"No activation clues found; issue area absent by
design"*, while the conditional ten say *"Cannot determine whether this issue area applies; defaulting
to 'not_applicable'"* — which at least admits the uncertainty. **LP-12's phrasing is the most
confident and its rule is the least defended.**

## Q4 — Widened audit: 2 false all-clears in 8, both LP-12

`not_applicable` was perfectly stable across all eight Atlas runs — `LP-12, LP-23, LP-31` every time.

| doc | LP | applicability | document check | verdict |
|---|---|---|---|---|
| **Atlas** | **LP-12** | `not_applicable` | `right to terminate` 1, `terminate this Lease` 5, `Termination Right` 2 | **FALSE ALL-CLEAR** |
| Atlas | LP-23 Percentage Rent | unclear | `percentage rent` 0, `gross sales` 0, `breakpoint` 0 | correct |
| Atlas | LP-31 Co-Tenancy | unclear | `co-tenancy` 0, `anchor tenant` 0 | correct |
| **divall** | **LP-12** | `not_applicable` | `right to terminate` 1, `terminate this Lease` 1, `shall terminate and expire` 1 | **FALSE ALL-CLEAR** |
| divall | LP-20 Exclusivity | unclear | see correction below | **correct** |
| divall | LP-30 Estoppel | unclear | `estoppel` 0, `certificate stating` 0 | correct |
| divall | LP-31 Co-Tenancy | unclear | `co-tenancy` 0, `anchor tenant` 0 | correct |
| divall | LP-32 Hazardous | unclear | `hazardous` 0, `environmental` 0, `contaminat` 0 | correct |

**Correction to my own probe.** My first pass flagged divall LP-20 as a false all-clear because
`"exclusive"` returned a hit. Reading the hit: *"…no one remedy shall be deemed to be **exclusive** of
the other or of any other remedy conferred by law or equity."* That is a **remedies-cumulative
clause**, not an exclusivity provision. **LP-20 is correct**, and my probe committed exactly the
topical-proximity error this arc exists to catch — a keyword match standing in for the concept. Recorded
rather than quietly dropped.

**Result: 2 false all-clears of 8 `not_applicable` determinations, and both are LP-12.** The other six
are right, on two structurally different leases. **The defect is not "applicability is broadly
unreliable" — it is LP-12 specifically.**

## Q5 — `requires_attention` is derived, not decided

`lease_coverage.py:1006-1009`:

```python
        "requires_attention": coverage_state in (
            "missing", "broken_xref", "covered_unfavorable",
            "partial", "potentially_unenforceable", "review_needed"
        ),
```

**It is a pure membership test on `coverage_state`, computed inside `_build_assessment` with no
independent input.** `not_applicable` is absent from the tuple, so `requires_attention: False` follows
automatically and unconditionally.

**Answering the question behind the question:** the set conflates two different things. `missing` and
`review_needed` are *assessed* outcomes; `not_applicable` is reached on the short-circuit branch
*before any assessment happens*. There is no state meaning "not assessed" — an LP the system could not
evaluate and an LP with genuinely nothing to report both emit `requires_attention: False`, and the
reader cannot distinguish them. Note `unclear`-routed LPs land here too: their entry says the system
could not determine applicability, and it is still marked as needing no attention.

Step 476/477's `evidence_missing` marker is the only field that distinguishes "not assessed" — and it
is set only for extraction-completeness failures, not for clue-list misses.

## Summary

LP-12 reproduces because **a ten-phrase list of negotiated-option jargon is asked to detect a concept
that both leases express in ordinary operative language inside casualty and condemnation articles**,
and because LP-12 alone is `optional`, so the miss becomes a confident assertion —
*"absent by design"* — rather than an admission of uncertainty. `requires_attention: False` then
follows mechanically from the coverage state, with no check that anything was actually assessed.

## What is NOT established

- Whether widening LP-12's clue list would fix it without over-triggering. Not attempted — that is a fix.
- Whether the 10 conditional LPs with `default_when_unclear: not_applicable` produce false all-clears
  on *other* documents. Two fixtures only; on these two they were all correct.
- Whether `requires_attention`'s conflation has caused a real miss beyond LP-12. Not traced.
- Why LP-12 is `optional` while every comparable area is `conditional`. Schema history not examined.
