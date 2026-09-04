Step 557. Honour the detector's own contract. Signals are evidence.

lease_negative_space.py:7 states signals are evidence, not verdicts, and
that the coverage assessor makes the determination. lease_coverage.py:465
short-circuits past the panel on any signal. The producer says "section or
subsection"; the consumer treats every match as the whole provision.

Implement Step 556's rule: short-circuit only when the block contains no
prose outside labels and placeholders. Otherwise pass the signal through
as evidence and let the panel decide.

1. Report the prose test precisely -- what counts as a label, what counts
   as a placeholder, and what remains. Measure it across all 45 corpus
   files, not just the seven, and report anything it would newly
   short-circuit or newly release.

2. When the signal passes through, does the panel SEE it? Evidence that
   reaches no evaluator is the same defect one layer over. Report where
   it lands and whether the 305 prompt carries it.

3. ex6-4 LP-23 is the known FN -- a true absence at 94% residue, inflated
   by misrouted Financial Statements text. Confirm it still short-
   circuits under the new rule, or report what it produces instead. Do
   not tune the rule to rescue it; a routing error is a routing error.

4. Verify by re-run: solidpower and divall. LP-29, LP-01 and LP-21 are
   the three cases. Report each verdict and headline, and whether the
   panel gets the provision right -- reaching the panel is the fix, not
   the outcome.

Do NOT change _RESERVED_PATTERN. Do NOT hedge any schema string -- that is
a separate decision and Step 556 established it is only a partial remedy.
