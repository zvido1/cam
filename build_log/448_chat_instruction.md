Step 448 REVISED — post-run audit of the Step 447 measurement.

REVISION NOTE (recorded per Rule 7): this file replaces an earlier version of the Step 448
instruction. That version's TASK 1 and TASK 3 rested on a FALSE PREMISE AUTHORED BY CHAT — it
asserted that §9.1 defines "four preregistered predicates" (grounding discipline, citation
discipline, same-candidate discipline, disagreement preservation) and that §12 specifies fields
for `431_validation.json` and `431_repository_seam_check.json`. Neither is true of the
preregistration text: the four names appear nowhere in it (they were authored from a
parenthetical gloss in the v3.2 amendment record, line 9), §9.1 defines NINE criteria, and §12
is a file list that specifies no fields. Claude Code halted on both tasks rather than resolving
the ambiguity; the halt was ruled correct and the four predicates are WITHDRAWN. Tasks 0, 2, 4,
5 and 6 are unchanged from the prior version and are carried verbatim below.

Read build_log/447_code_status.md first for context.

SCOPE: post-run audit of the Step 447 measurement. Audit only.
No harness edits. No rerun. No push. No remediation of any recorded debt.
Rule 6 applies throughout: every claim about code or document content
requires a verbatim quote plus location, or is marked
[UNVERIFIED - characterized, not read].

If any task cannot be completed as specified, halt and report.
Do not adjust the specification to make it completable.


RULING ON THE HALT (record verbatim in 448_code_status.md):

Your halt was correct on both tasks. The "four predicates" were authored by
Chat from a parenthetical gloss in the v3.2 amendment record and were never
preregistered. Withdrawn.

Governing criterion set: the NINE criteria in §9.1. §8.2 is not a rival set;
it is the evidence decomposition of §9.1 into a measurement class (5,
sidecar-computed, -> 431_validation.json) and an artifact/seam class (5,
repo/manifest/report-computed, -> 431_repository_seam_check.json), per §8.2's
own words: "Not every §9.1 criterion is a sidecar property. Some are
repository/manifest/report facts."

ROOT-CAUSE FINDING (supersedes the "inert constants" framing):
§12 marks `validate_431.py` and the seam-checker as "(+ optional)" Stage-1
artifacts while listing `431_validation.json` and `431_repository_seam_check.json`
as unconditional Stage-2 outputs. §1 omits the validators entirely. The
manifest's eleven token-bound artifacts include neither. The optional
producers were not built; the mandatory products therefore cannot exist; and
§8.2 forbids authoring the table in their place. Lines 108-109 are the
symptom, not the cause.

CONSEQUENCE: §9.1 is UNPRODUCIBLE under package P4. Not merely unevaluated.
Nothing in this step or any report may be labeled §9.1 for this run.


TASK 0 - ARTIFACT IMMUTABILITY

Before any analysis: record SHA-256 of every Step 447 output artifact and
the sidecar into build_log/448_input_hashes.md. Re-record at end of step
and confirm identical. No audit operation may write to any run artifact.

Any script written for this step goes in build_log/, is labeled in its own
header as "independent post-run validation, not emitted by the sanctioned
harness," and is read-only against run outputs.


TASK 1-REVISED - §9.1 COMPUTABILITY SURVEY (NOT an evaluation)

Quote each of the nine §9.1 criteria verbatim. For each, determine whether
the required data EXISTS in the immutable Step 447 outputs, the repository,
or the manifest:
  PRESENT  - all required fields exist; cite artifact + pointer
  PARTIAL  - some exist; name what is missing
  ABSENT   - the data was never recorded

Also map each §9.1 criterion to its §8.2 evidence-class counterpart, and
report any §9.1 criterion with no §8.2 counterpart, and any §8.2 criterion
with no §9.1 counterpart.

HARD CONSTRAINT: emit NO status, pass, fail, satisfied, or not-established
judgment on any criterion. This survey establishes only whether a future
validator COULD compute it. Producing a §9.1 verdict is the prohibited
authorship.

Note explicitly whether §8.2's seam criterion "report pass/fail values equal
validator output" is satisfiable in principle when no validator output exists.


TASK 2 - CAND_04 TERMINAL-STATE DERIVATION

1. Quote the policy code that maps role-judgment combinations to terminal
   states. Confirm from the code, not from inference, that a combination of
   `unclear` and `none` on `value_applies_to_charge_basis_components` routes
   to review_needed_disagreement rather than review_needed_no_qualifying_candidate.

2. Report the role-B judgment from the sixth (replacement) attempt alongside
   the other four canonical role-B judgments, so the canonical series is
   visibly consistent.

3. Disclose explicitly: the single degraded attempt of the run occurred on
   cand_04, the forcing candidate, at raw attempt 4, cause
   reasoning_exhaustion, substitution to gpt-5.4, and it was the one role-B
   judgment returning `unclear` rather than `none`. Excluded from canonical N.
   State that the exclusion is why the result is unaffected.

Report language for the finding, use as written:

"Under the v3.3 relation-bearing representation, the live panel emitted no
false operating-expense linkage and the system produced no false
certification. The run did not isolate whether that outcome was caused by
the prompt/schema representation, evaluator behavior, or their interaction.
The policy-layer rejection of a positively asserted but false value-to-basis
linkage remains unexercised."

"cand_04's five review_needed_disagreement outcomes arose from `unclear`
versus `none`, not from competing substantive assertions about the basis."


TASK 3-REVISED - DEPENDENCY-CHAIN FINDING

Quote verbatim: §12 in full; §9.1's header line; §8.2's "COPIED FROM ...
never authored" sentence; §1's Stage-1 artifact list; lines 108-109 of the
harness plus the no-write-site search evidence (already done as 3.1, carry
forward). Show from 431_config_manifest.json that no validator or
seam-checker is among the eleven token-bound artifacts.

Record the optional-producer / mandatory-product inconsistency as the root
cause. Record. Do not remediate, do not propose a corrected package.


TASK 4 - COUNT RECONCILIATION

Resolve from logs, not from plausible explanation:

- 109 router initializations against 108 role-calls. Name the extra
  initialization.
- 36 raw attempts against 35 canonical panels. Show the arithmetic
  explicitly.
- Seven provisioned candidates against 30 parameter-lease series. Produce
  the candidate -> parameter/lease-series mapping. The claim bound is over
  the seven candidates; a reader must be able to reconstruct which candidate
  produced which certification.

Record, in the report:

- Atreca is the known-good foil and returned tenant_share 4/5 and
  rent_adjustment_pct 0/5 with five disagreements. This is replicate
  variance on the control and constrains all reproducibility language.
- completeness: not_established on all 30 series bounds every negative
  outcome. Atlas's five no_qualifying_candidate outcomes do not establish
  document-level absence of a rent adjustment.


TASK 5 - EXECUTION-PREREQUISITES CONTRACT

Author build_log/448_execution_prerequisites.md containing: required
environment-variable NAMES only, never values; provider connectivity
requirements; sanctioned model identities; external-launcher responsibility;
statement that environment injection does not modify token-bound package
bytes; confirmation that no secret value was captured in any log.

Record it as A POST-RUN ARTIFACT DOCUMENTING AN UNDECLARED PACKAGE
REQUIREMENT, not as a restatement of a declaration the package carries. The
harness reads os.getenv directly and the package names no required variables
and defines no failure mode for their absence; the requirement was
established by inspection before launch. Quote the os.getenv call site.

Wording for the reproducibility statement, use as written:

"Package identity is repository-reproducible; successful live execution
additionally requires a declared external environment."


TASK 6 - PANEL-IDENTITY WORDING

Replace any frozen-panel language with:

"The canonical panel identity was enforced through provenance, exclusion,
and retry. One gpt-5.5 failure triggered an own-chain gpt-5.4 substitution;
that attempt was marked noncanonical, excluded from canonical N, and
replaced by an additional attempt."

Detection-and-exclusion, not prevention.


DELIVERABLES

build_log/448_code_status.md reporting all six tasks, plus the input/output
hash record, the section 12 mapping table, any committed derivation rules,
and the prerequisites contract. Commit. Do not push.

DELIVERABLE ADDITION

State plainly whether the 108-call run is salvageable by a validator-only
package computing §9.1 over the immutable sidecar with zero model calls, or
whether required data is absent and a re-run under a corrected package is
the only path. This follows from the survey; do not decide it in advance.
