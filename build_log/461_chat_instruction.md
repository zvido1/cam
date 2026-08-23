# Step 461 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 461. Record the precision answer, then clear the mechanical items.
No runs. No seam behaviour change.

PART A — update the 08-23 block's STILL OPEN item 1

It says precision is unasked. Step 460 asked it. Replace with the answer:

MEASURED, and the seam is NOT vindicated wholesale — 6 of 8 clean, 2 not.

  - Element 6, "right to monetary damages for landlord default": FALSE
    PRESENT. Five of six judgments rest on Section 11.2, an indemnity
    clause. No span before the panel grants Tenant damages for landlord
    default because none exists. Merged explicitly_present, both runs.
  - Element 7, specific performance / injunctive relief: FALSE PRESENT,
    weaker still. Rests on a 91-character savings clause, "in addition to
    any other remedies available to Tenant at law or in equity". A clause
    preserving unspecified remedies read as evidence a specific remedy
    exists. The two runs disagree, EXP vs IMP — the instability signal you
    expect on thin evidence. Document-level check: "specific performance",
    "injuncti", "equitable relief" have ZERO hits in the lease. The
    elicitor did not miss better evidence; there is none.
  - The diagnostic asymmetry: on element 4, evaluator B quoted "draw upon
    the Security Deposit as a setoff against damages" and voted MISSING
    anyway, because the element asks for offset against rent. A near-miss
    correctly rejected, same panel, same run, while a further miss was
    accepted at explicitly_present on element 6. This is not general panel
    laxity — GENERIC, TOPICALLY ADJACENT evidence is what gets waved
    through, and span elicitation surfaces more of it than buckets did
    because it searches by description rather than location.

Then record the §11.3 finding as its own item, because it is structural and
larger than the two false positives:

  Span elicitation UNDER-INCLUDES ACROSS SECTIONS, the mirror of bucket
  assignment OVER-INCLUDING WITHIN one. Section 11.3, Limitation of
  Liability, sits at offsets 15490-15748: "Neither party shall be liable to
  the other for any consequential, indirect, punitive, or special
  damages... Landlord's liability shall be limited to Landlord's interest
  in the Building and Land." Span 7 ends at 15251. The panel was handed the
  indemnity and stopped 239 characters short of the clause that limits it.
  This is not a bad span: the elicitor retrieves clauses matching an
  element's description, and the qualifier matches no LP-27 element, so it
  is structurally unreachable. A QUALIFIER THE PANEL CANNOT SEE CANNOT BE
  WEIGHED, AND NOTHING IN THE OUTPUT MARKS ITS ABSENCE. A lawyer reading
  "monetary damages: explicitly present, high confidence" is not told the
  lease caps landlord liability at its equity in the building.

  Two candidate directions, neither chosen: co-retrieval of adjacent text
  around any returned span, or a "limitations and carve-outs" retrieval
  pass that is not element-driven.

State plainly: DO NOT EXTEND THE SEAM to the remaining 31 LPs until this is
addressed. Every LP has elements whose evidence is generic or topically
adjacent, and the exposure concentrates exactly there.

PART B — item 4, the mechanical ones

Revive span_evidence_records: persist the elicitor's own span-to-element
attribution (elicited_by) into the coverage result so the span-to-element
mapping is a measurement rather than a reconstruction. Step 460 had to
reconstruct it from what each evaluator quoted, because the field is
assigned twice and read nowhere.

Fix the two stale comments: "EXPERIMENT, LP-07 ONLY" and "that one edit is
the whole rollback".

No behaviour change. Report the diff.

PART C — item 3, the layering tests

Retire the two deliberately. Replace each with the check that actually
encodes current doctrine: the seam, and ONLY the seam, imports the 423
stack — i.e. lease_adapter and lease_extract must not import it, while
lease_coverage may. Leave the genuine direction checks untouched.

Suite should return to full green with no test deleted, only rewritten.

Leave item 2 (LP-12) and item 5 (extension) open. Commit. Do NOT push.

---

## Found during execution: four Docs files modified outside this session

`git status` at the start of Step 461 showed changes I did not make, establishing an **ACTIVE
DECISION REGIME 2026-08-23 → 2026-11-11** and referencing `Docs/CAM_Patent_Go_No_Go_Plan_2026.md`
(a file this session has never read):

- `Docs/NEW_THREAD_PROMPT.md` — new 2026-08-23 frontier block, engineering scope limit
- `Docs/Attorney_Question_Bundle.md` — August overlay, new starred questions A0/A9/A10/B3/B4/B5
- `Docs/Patent_Current_State.md` — ACTIVE DECISION REGIME + FILED-BASELINE CONTROL blocks,
  added *after* the Step-459 commit of that file
- `Docs/CAM_Current_State.md` — ACTIVE PROJECT REGIME block prepended, in the same file this step
  edits

**Not committed by this step**, except `CAM_Current_State.md`, which cannot be separated from this
step's own edits to the same file. Flagged to Tzvi rather than absorbed.

**Two of them assert things Step 460 has already falsified**, and one is bound for counsel:

- `NEW_THREAD_PROMPT.md`: *"span precision remains unmeasured"*; *"the relevance of §11.2 to the
  asserted monetary-damages element has not been tested"*; *"Do not extend the seam broadly until a
  bounded precision test can detect irrelevant evidence producing false `explicitly_present`
  verdicts."*
- `Attorney_Question_Bundle.md` question **B5**: *"The current seam fixes lost evidence and missing
  citations but has not yet measured whether irrelevant spans can cause false presence findings."*

Step 460 ran that test. §11.2 **is** the basis for element 6 in five of six judgments, and it **is** a
false `explicitly_present`. The precision test exists, it detected exactly the failure B5 describes as
unmeasured, and `build_log/460_LP27_precision_evidence.md` records it. **Not corrected here — those are
not this step's files.**
