Step 544. The citation gate overwrites earned verdicts. DIAGNOSTIC, no fix.

Step 537: LP-20's covered_favorable was replaced with review_needed by
_apply_citation_gate because a citation lacked a section_ref. Step 522
named that state suppressed. On ex6-4 the locator resolves 45%, so the
gate is firing on a document where more than half of all citations cannot
carry a resolvable reference.

1. How many verdicts did the gate overwrite across ex6-4, quanterix,
   solidpower and Atlas? Report per document: overwrites, which LPs, and
   the original verdict in each case.

2. What is the gate protecting against? Quote its rationale if recorded.
   A verdict without a citation is unverifiable — but a verdict whose
   citation names a section the heading index cannot parse is a different
   failure, and the gate may not distinguish them.

3. Does the overwrite correlate with locator resolution rate? Atlas
   resolves 99%, ex6-4 45%, quanterix 0.6%. If overwrites track the
   locator rather than citation quality, the gate is measuring our parser,
   not the panel.

4. What does the reader see? On ex6-4, LP-20 reads as review_needed —
   flagged, but as a citation artefact rather than as the substantive
   finding. Report whether the original verdict survives anywhere in the
   result.

Do NOT fix. Report the measurement.
