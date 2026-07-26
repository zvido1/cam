Step 449. Read build_log/448_code_status.md. Rule 6 and Rule 7 in force.
Audit only. No harness edits. No rerun. No push. No remediation.

TASK A - SEMANTIC SUPPORT SPAN, RESOLVED FROM CODE

1. Re-search the sidecar and all Step 447 outputs on the PREFIX
   `semantic_support_span` (not the exact string `semantic_support_spans`).
   §8.1 names the trace field `semantic_support_span_ids`; §9.1/§5/§8.2 use
   `semantic_support_spans`. Report occurrence counts for every distinct
   matching identifier found.

2. From the harness source, quote: every site that constructs, populates,
   or emits a semantic support span or its ids; the certification_trace
   emission code showing which §8.1 fields are written and which are not.
   If no such site exists, quote the search evidence establishing that.

3. State which of these holds, from code, not inference:
   (a) materialized and recorded under a different name
   (b) materialized and not recorded
   (c) never materialized by this harness
   If (c), state whether §9.1 #3 is thereby vacuous rather than satisfied,
   and do not classify it as either without quoting the basis.

4. Report the effect on the survey: does #6 remain ABSENT, and does #3
   remain PARTIAL, under the corrected search.

TASK B - DEGRADATION-REASON CLASSIFICATION

Quote the provider_router code that assigns `fallback_reason`. Establish
from code whether `reasoning_exhaustion` is a classification of an
`empty_content` error for reasoning models, or whether the two fields
disagree. Do not resolve by inference. If the code does not settle it,
record the field as unreliable-pending-verification.

TASK C - CORRECTIONS TO THE RECORD

Record in 449_code_status.md: the 447 and 448 statements of the cand_04
degradation cause are superseded pending Task B; Chat's 448 brief
propagated the unverified `reasoning_exhaustion` cause and Code correctly
declined to assert it.

DO NOT compute any §9.1 criterion in this step. The partial computation is
authorized only after Task A resolves. Commit. Do not push.
