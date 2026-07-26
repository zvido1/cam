Step 450. Read build_log/449_code_status.md. Rule 6, Rule 7 in force.
Audit only. No harness edits. No rerun. No push. No remediation.

TASK A - REPLAY FEASIBILITY (decides cheap-vs-paid)

Against the immutable sidecar, establish from the data whether the raw
per-panelist judgments carry the §4.1 `field_support` mapping, and whether
context citations carry resolvable verbatim quotes plus ids.

Report, per candidate and role:
  - is `field_support` present, and does it map each semantic field to
    citation ids
  - do context_citations carry id + verbatim quote
  - does each quote resolve against the frozen canonical source hash

Then state whether a deterministic materialization of semantic_support_spans
is constructible from the sidecar alone, WITHOUT semantic invention.
If any required element is missing, name it. Do not attempt the
materialization in this step.

TASK B - POST-RUN VALIDATOR, SEVEN CRITERIA + TWO DERIVED RESULTS

Write build_log/431_postrun_partial_validation.json via a script in
build_log/, header declaring it an independent post-run audit artifact
written after outcomes were visible, NOT the preregistered §8.2 validator.
Read-only against run artifacts; hash before and after.

Compute the seven testable §9.1 criteria per the preregistered definitions
quoted verbatim in 448. No criterion may be reinterpreted.

Emit #6 as: status derived from two established facts (the required field
was never written; fourteen certifications met the "if any" antecedent).
Emit #3 as: not_established_at_package_layer, with the enforcement half
(#2 same-candidate supply, and primary-supplies-value_ok per §4) reported
separately as a distinct trace-level result.

Every record carries the artifact's post-run derived status. The conjunction
result is emitted by the validator, not written in prose in the status file.

TASK C - RULE 8

Add to CLAUDE.md:
  Rule 8 - Producer-consumer census. Before any preregistration package is
  sanctioned, every specified product must be traced: producing function ->
  write site -> validator consumer -> report consumer. A product with no
  producer, or a producer marked optional whose product is mandatory, halts
  the sanction.

TASK D - STATE RECORDS

Update Docs/CAM_Current_State.md and Docs/Patent_Current_State.md with the
claim boundary: what 431/447 supports, and what it does not (emitted
certified evidence packages with materialized support spans; recorded
anti-borrowing at the support-span layer; Gate-B handoff). Note that
anti-borrowing enforcement at the value layer IS exercised and
trace-visible, and is a separate finding from package materialization.

Commit. Do not push.
