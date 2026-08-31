# Step 522 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 522. Build assessment_status. Design per Step 521.

Three values: assessed | not_assessed | suppressed. Orthogonal to
requires_attention, which keeps its boolean contract and its truthiness at
lease_exposure:523.

FAIL-CLOSED ON EMISSION, and this is the part that matters most.
A route that forgets to set it must NOT default to "assessed" — that is
the schema claiming a judgment nobody made, which is the defect this field
exists to prevent. State what the absent case does and defend it. Consider
whether the default should be a fourth value meaning "the emitting site
did not say", surfaced as loudly as not_assessed.

Emit at all four sites. Report each with its line, and prove by exercise
that each one sets it — not that the code appears to.

DISPLAY, per item 4:
  - the DOCX numbers requires_attention entries; not_assessed must not be
    absorbed into that numbering unnoticed
  - the PDF colours by coverage_state; not_assessed and suppressed need
    their own treatment, not the existing legend
  - the remaining seven surfaces per Step 521 item 3

VERIFY BY EXERCISE
Generate a DOCX and a PDF from a result carrying all four kinds —
assessed-and-clean, assessed-and-missing, not_assessed, suppressed — and
quote what appears for each. A reader must tell them apart without knowing
the schema.

Then one Atlas run. Expect 5 not_assessed of 33 and report which, against
Step 521's LP-12/16/23/29/31. Report any suppressed — Step 497 saw the
citation gate fire on LP-27, so the count may be non-zero.

Do NOT deploy.
