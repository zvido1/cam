Step 547. The same catch-all defect on `partial`. 19 LPs.

Step 546 fixed review_needed; the identical defect survives on partial.
`if state == "partial" and missing:` means a partial with an empty
adverse-missing list falls through to the canned absence prose. Measured:
ex6-4 LP-05 "Use restrictions absent or undefined", solidpower LP-17
"Dispute framework absent", Atlas LP-09, divall LP-10.

1. Report all 19 across the six runs, with present/total counts and
   whether elements_missing is empty. Is the shape the same as
   review_needed's, or does partial have cases the review_needed branch
   would handle wrongly?

2. Apply the same treatment. Same guard: a headline must not assert
   absence when the adverse-missing list is empty, and must not fire when
   settled_present is zero.

3. Watch the polarity trap you found in Step 546. Partial is more exposed
   to it than review_needed — partial means SOME elements missing, so the
   favourable-absence case is more common. Use the perspective-adverse
   list, and report any LP where the raw and adverse counts differ.

4. Verify by artefact across all four named LPs, before and after, DOCX
   and PDF. Confirm the review_needed fix is unchanged and LP-20 still
   reads as genuinely absent.

Do NOT change derive_lp_state. Do NOT add a coverage_state. Do NOT widen
beyond partial — if a third state has the same defect, report it and stop.
