Step 451. Read build_log/450_code_status.md. Rule 6, Rule 7 in force.
Audit and CLAUDE.md only. No harness edits. No rerun. No push. No
remediation of anything the census finds.

If any task cannot be completed as specified, halt and report. Do not
adjust the specification to make it completable.


TASK A - RULE 8 COMPANION CLAUSE

Add to CLAUDE.md, alongside the producer-consumer census added in Step 450:

  Every specified predicate must be traced to a reachable satisfying
  assignment under the package's own declared field values. A predicate
  that cannot be satisfied by any conforming input halts the sanction.

Record the reason: Part B §8.1 requires basis_match=match on the qualifying
candidate, while Part B §4 declares value_applies_to_charge_basis_components
= not_applicable for base_rent and rent_adjustment_pct, making the §8.1
conjunction unsatisfiable for those parameter types. No hash, signature,
scope, or cleanliness gate asks whether a specified success state is
reachable.


TASK B - PRODUCER-CONSUMER CENSUS, RETROACTIVE

Enumerate every product specified anywhere in
build_log/431_partB_measurement_instruction.md: §1 Stage-1 artifacts,
§8.1 certification_trace fields, §8.2 validation criteria and their two
artifacts, §9 report contents, §12 file lists.

For each, trace:
  specified product -> producing function -> write site -> validator
  consumer -> report consumer

Report each as COMPLETE, or name the first missing link. Quote the
producing/write site where one exists, or the search evidence where none
does. Known instances, for comparison, not as the expected total:
  - 431_validation.json and 431_repository_seam_check.json: no producer
    (§12 marks the producers optional, the products mandatory)
  - §8.1 semantic_support_span_ids: no write site
  - §8.1 field_support_citation_ids: no write site

Report any FOURTH or further instance separately and prominently.


TASK C - PREDICATE-REACHABILITY CENSUS, RETROACTIVE

Enumerate every predicate the package evaluates or requires: §4 requirement
profiles per parameter, §8.1's certification conjunction, §9.1's nine
criteria.

For each, state whether a conforming input exists that satisfies it, given
the package's own declared field values and schema-fixed not_applicable
assignments. Where unsatisfiable, name the two clauses that conflict and
quote both.

Also flag any §9.1 criterion whose subject the Part B harness does not
produce, distinguishing that from unsatisfiable. #3 and #6 are the known
instances; report any others.


TASK D - PROVENANCE OF THE §9.1 CRITERIA

For each of the nine §9.1 criteria, identify whether it was carried over
from Part A §11.1, and whether Part B's harness produces its subject. This
establishes how many criteria entered Part B by copy without an
instrument check.


DELIVERABLE

build_log/451_code_status.md with all four tasks. Do not remediate any
finding. Do not propose a corrected package. Commit. Do not push.
