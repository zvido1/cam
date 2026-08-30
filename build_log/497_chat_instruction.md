# Step 497 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 497. Disclose evaluator substitution. The markers exist; nothing
reads them for this case.

THE DEFECT, confirmed three times
Step 488 traced it, Step 491 evaluated the predicate against real data on
both configurations, Step 496 observed it on a benign fallback. A run with
run_degraded=True and degraded_reason='evaluator_fallback' shows
invalid_for_legal_analysis=False, so every disclosure surface stays silent.
Step 487's two deployed runs had role A substituted on 196 and 202 of 202
verdicts and told the user nothing, anywhere.

BUT — Step 488 item 4 GATES this. Fix the provenance first.
Element records in an all_failed stub carry actual_model='claude-sonnet-4-6'
and is_fallback=false — four fields naming Anthropic, one of them an
affirmative denial, on records that exist BECAUSE substitution failed.
Marking six surfaces from data known to misreport would compute disclosures
from wrong inputs.

PART A — provenance
Stop element records asserting a model that did not serve them. A stub
whose reasoning is "Evaluator A did not complete" must not carry
actual_model naming the requested model, and must not carry
is_fallback=false. State what it should carry instead and why.

Verify against the Step-487 stored results: the census must report role A
served 0, not 196 or 202, once stubs are correctly labelled.

PART B — disclosure
Surface evaluator substitution on the same six surfaces that carry
extraction incompleteness: the web banner, the job aggregate, both
annotators, the summary generator, and the batch summary.

It is NOT the same message. Extraction incompleteness means part of the
document was not analysed. Evaluator substitution means the panel that
analysed it was not the panel claimed. State both distinctly; do not
overload incomplete_statement.

Say plainly what threshold triggers it. One transient fallback on one LP
(Step 496: 11 records, claude-haiku-4-5, malformed_response) is not the
same as an entire seat substituted for a whole run (Step 487). Propose a
rule and defend it — do not just report any fallback, and do not
silently suppress small ones.

VERIFY BY ARTEFACT, not by code reading
Three steps running have caught defects a static read missed. Generate a
DOCX and PDF from: a Step-487 result (whole seat substituted), the Step-496
Atlas result (one LP, benign), and a clean Step-491 result. Quote what
appears on page one of each. Clean must be unchanged.

Do NOT deploy. Report and stop.
