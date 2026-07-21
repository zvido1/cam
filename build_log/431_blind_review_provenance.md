# 431 Blind Review Provenance — what each reviewer received, what was withheld, and why

**Date:** 2026-07-19
**Package under review:** Stage-1 rebuild committed `65556ee` (Part B v3.3, RATIFIED; token `47cb312a`).
**Author:** Chat instance. This note records the construction of the two blind-review payloads so a
later reader can verify the reviews were *genuinely blind* and not quietly informed. The evidential
value of a clean blind review depends entirely on the reviewer not holding the answer key or the
finding it is being asked to independently reproduce; an unrecorded stripping decision is
indistinguishable from an accidentally-incomplete payload, so the withholding is documented here
before the reviews run.

## Why two isolated conversations, not one
Review A (prompt-distribution leakage) and Review B (profile circularity) run in SEPARATE fresh
conversations. If the requirement profiles appear in the same conversation as the prompt, the
prompt reviewer learns which classifications the downstream code rewards and can no longer judge
prompt leakage honestly. Splitting them keeps each reviewer holding only half.

## Why these are RE-RUNS (not reuse of the prior clean results)
The prior blind reviews were of package `5954e6e`. v3.3 changed the model-facing contract:
- the selector prompt changed (relation-bearing read rule on item 3; abstention rebalance; a
  "should be" -> "must be" grounding-line wording fix) -> Review A must re-run;
- the output schema + the profiles' basis field changed (`charge_basis_components` ->
  `value_applies_to_charge_basis_components`, relation-bearing) -> Review B must re-run.
No prior review result carries over.

## Review A payload (prompt-distribution leakage) — CONTENTS
Fresh conversation. Contains ONLY:
- `431_selector_prompt.txt` (verbatim, `65556ee`)
- `431_output_schema.json` (verbatim, `65556ee`) — MINUS the schema's `_artifact` / `_authority` /
  `_notes` metadata keys (these name the instruction version and internal design rationale, e.g.
  the 423C reference; they would signal to the reviewer that this is a scrutinized artifact with
  known forcing cases). The model-facing schema body (types, enums, descriptions) is preserved
  verbatim.
- the four `parameter_family_label` values and the two applicability-flag values per family
  (from `431_measurement_config.json`, `parameter_family_labels` block)
- a generic statement that the task classifies commercial-lease passages.
EXCLUDED: requirement profiles, parameter requirement definitions, fixtures, candidate IDs beyond
opaque runtime placeholders, expected outcomes, amendment/build history.

## Review B payload (profile circularity) — CONTENTS and STRIPPING SPEC
Fresh conversation, SEPARATE from Review A. Contains ONLY:
- `431_requirement_profiles.json` (`65556ee`), **stripped** of the fields listed below
- neutral general definitions of the four parameters (base_rent, tenant_share, building_share,
  rent_adjustment_pct) as a commercial-lease glossary would give them — NOT as the fixtures
  instantiate them.
EXCLUDED entirely: the prompt, the schema, any fixture, any candidate discussion, any expected
outcome, Review A's contents.

### What is STRIPPED from the profiles for Review B, and why (the load-bearing discipline)
Review B's evidential value comes from a reviewer INDEPENDENTLY not finding a co-occurrence defect
in the *fixed* contract — NOT from confirming a fix it was told about. The prior Review B is what
*found* the co-occurrence defect; re-running it against the fixed contract only means something if
the reviewer is not handed the finding. Therefore the following fields are removed from the profile
JSON before pasting, because each would leak either the finding, the fix, or the existence of
fixtures/expected-outcomes:

- `_amendment` (every occurrence) — narrates "renamed ... to close the co-occurrence-false-match
  defect (blind Review B + GPT informed audit)"; hands the reviewer the exact finding.
- `_relation_bearing_note` — explains the co-location-vs-application distinction as the point of
  the fix; hands the reviewer the fix.
- `_why_this_is_the_general_requirement_not_an_answer_key` (every occurrence) — states the profile's
  own defense; a circularity reviewer told the rule's justification grades the justification instead
  of independently deriving legitimacy from the definition.
- `_authority` — names the instruction version (v3.3); signals a scrutinized artifact.
- `_declaration_of_independence_from_fixtures` block — names "cand_0N" and "seeded candidates";
  tells the reviewer that specific fixtures with expected outcomes EXIST, which a blind circularity
  reviewer must not know.

What REMAINS for Review B: the rules themselves (the `basis_match` / `text_role_ok` / `value_ok` /
`support_ok` / `relevance_ok` / `applicability_match` computations), the `_evaluation_semantics`
operator definitions, the `_qualification_rule`, and the neutral `_requirement_in_one_line` per
parameter. The reviewer is asked to derive each rule's legitimacy from the general parameter
definition alone and to attack `tenant_share.basis_match` with constructed cases — the SAME task as
the prior Review B, now against the fixed contract, WITHOUT being told it is the fixed version.

The asymmetry between Review A (schema metadata stripped) and Review B (much more stripped) is
deliberate and is the point: Review B is being asked to independently *not* reproduce a specific
finding, so it must not carry any trace of that finding.

## Known, deliberate property flagged for both reviews (esp. the informed audit)
The co-location-vs-application distinction appears THREE times in the model-facing artifacts:
selector-prompt item 3, the `value_applies_to_charge_basis_components` field description, and the
`field_support` entry. This concentration of instructional weight on ONE dimension is a direct
consequence of the v3.3 fix — the emphasis is what closes the co-occurrence laundering. A blind
prompt reviewer may correctly call this **borderline response-shape pressure** ("this is the
dimension that matters"), even though every word is definitional rather than answer-keyed. This is
recorded as a KNOWN, DELIBERATE property, not a latent surprise: the fix required the emphasis; the
emphasis directs attention to a *distinction* (does the value apply to a base?), not toward any
particular *value* (opex / taxes / none / unclear). Whether that emphasis crosses from
attention-direction into distribution-shaping is a legitimate question for the informed audit to
weigh; a "borderline on item-3 weight" verdict from Review A is an expected and acceptable outcome,
not a failure.

## Sequence (unchanged from GPT's informed-audit required next action)
1. Review A (this note's payload) — fresh conversation. [running]
2. Review B (this note's payload, stripped per spec) — separate fresh conversation.
3. GPT informed audit of both reports — now ALSO checks the four relationship tests' expected
   outcomes are correct (not just green), against ratified §5, and weighs the item-3 weight caveat.
4. Separate explicit Stage-2 sanction of token `47cb312a`. Not before.

All prior packages (`4386d95`, `5954e6e`) and tokens (`9e7a2d1c`, `5ed0c5cc`, `ecbf512d`,
`0ebb93ba`, `ccf03284`) remain VOID for execution.
