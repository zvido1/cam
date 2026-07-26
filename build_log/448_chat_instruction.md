Step 448. Read build_log/447_code_status.md first for context.

Before executing anything: write this instruction verbatim to
build_log/448_chat_instruction.md (Rule 7).

SCOPE: post-run audit of the Step 447 measurement. Audit only.
No harness edits. No rerun. No push. No remediation of any recorded debt.
Rule 6 applies throughout: every claim about code or document content
requires a verbatim quote plus location, or is marked
[UNVERIFIED - characterized, not read].

If any task cannot be completed as specified, halt and report.
Do not adjust the specification to make it completable.


TASK 0 - ARTIFACT IMMUTABILITY

Before any analysis: record SHA-256 of every Step 447 output artifact and
the sidecar into build_log/448_input_hashes.md. Re-record at end of step
and confirm identical. No audit operation may write to any run artifact.

Any script written for this step goes in build_log/, is labeled in its own
header as "independent post-run validation, not emitted by the sanctioned
harness," and is read-only against run outputs.


TASK 1 - PREREGISTERED 9.1 PREDICATE AUDIT

The table currently reported as 9.1 is not 9.1. Rename it in all outputs to
"Terminal certification-state distribution."

Then:

1. Quote verbatim, from the preregistration 9.1 text, the definition of each
   of the four predicates: grounding discipline, citation discipline,
   same-candidate discipline, disagreement preservation. Quote before
   evaluating. If the 9.1 text does not define a predicate operationally,
   say so and stop on that predicate.

2. Evaluate each predicate per series against the produced artifacts,
   applying only the preregistered definition.

3. If the produced artifacts do not contain sufficient information to
   evaluate a predicate, mark it NOT ESTABLISHED. Do not infer success from
   terminal states. Do not substitute a proxy criterion.

Constraint: no criterion may be authored or adjusted after seeing results.
If a definition requires interpretation, halt and report the ambiguity
rather than resolving it.


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


TASK 3 - SECTION 12 FIELD MAPPING

1. Quote verbatim lines 108 and 109 of the harness (VALIDATION_PATH,
   SEAM_CHECK_PATH) plus the search evidence establishing no write site for
   either. Record the exact search command and its output.

2. Enumerate, quoted verbatim from section 12, every field specified for
   431_validation.json and 431_repository_seam_check.json.

3. Assign each field to exactly one category:
   (a) PRESENT ELSEWHERE with equivalent content in the three produced
       artifacts or the sidecar. Cite location.
   (b) DETERMINISTICALLY DERIVABLE from immutable recorded fields.
   (c) ABSENT EVERYWHERE.

GUARD ON CATEGORY (b): the derivation rule for any field placed in (b) must
be written from section 12's own text and committed to build_log/ BEFORE the
field is computed. If section 12's text does not determine the derivation
without a judgment call, the field is (c), not (b). Do not derive under
discretion. Results are already visible; discretionary derivation is
post-hoc criteria construction.

Category (c) fields: the corresponding claims are unsupported and must be
marked not established in the report.


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
