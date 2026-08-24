# Step 471 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 471. Citation gate: presence versus meaning. DIAGNOSTIC.
No fix, no runs, no schema change.

Two independent measurements now show the citation gate satisfied by
strings that name no document location: 'Paragraph 1' / 'Proportionate
Share definition' (Step 460, before the locator prefix) and 'Default
statute of limitations law' / 'Default law; jurisdiction-dependent'
(Step 470). The gate tests non-nullity, never whether the value identifies
a location.

Establish, offline, across all four runs and all 33 LPs:

1. Of every non-null section_ref returned, how many RESOLVE against the
   canonical lease — i.e. name a heading that exists in the line-anchored
   heading index? Report resolving / non-resolving / unparseable, broken
   down by verdict class.

2. Of the non-resolving ones, categorise: prose restatement of the verdict,
   invented locator, cross-LP reference, other. Give examples of each.

3. For the LPs on the SPAN path (LP-07, LP-27), how many resolve? The
   locator prefix supplies real section names — does that population
   resolve at a materially higher rate than the bucket-path LPs?

4. Would a resolution check — section_ref must match a heading in the
   index — be computable deterministically at merge time? What does it
   need that the merge does not currently have?

5. If such a check were applied, how many merged verdicts change across
   the four runs? Report the count and the LPs. Do NOT implement it.

The question: is 'the citation must resolve' a deterministic constraint the
pipeline could enforce, and what would it cost?

Report. Change nothing.
