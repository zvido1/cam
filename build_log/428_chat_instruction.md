CAM — Step 428: Gate C — parameter assignment stability. Measurement only. No baseline. No push.

## Part 0 — MANDATORY, BEFORE ANY OTHER WORK

Per CLAUDE.md Rule 7: write this brief VERBATIM to `build_log/428_chat_instruction.md` before doing anything else. Do not paraphrase, summarize, or improve it. It is the document you will be audited against.

## Purpose

Step 427 built the parameter block, the declared dependency map, deterministic attachment, and Gate B. It proved on ONE run that LP-07's evidence context contains the 100% tenant share.

One run is not stability. 424 and 426 both found that elicitation is NOT deterministic at temperature 0 — verified span counts swung ~9% across identical inputs, and several targets showed offset drift across runs even when hit 5/5.

Gate C asks the question that must be answered before this substrate is wired into the live pipeline:

> Do the same four parameters extract to the same verified spans, at the same offsets, and attach to the same LPs, on EVERY run?

If they do not, the parameter block is not a foundation — it is another nondeterministic layer, and wiring it in would import that nondeterminism into every downstream evaluation.

This step MEASURES. It does not fix. If the measurement is bad, do not repair it in this step — report it and stop.

## Read

- `build_log/427_parameter_block_dependency_map.md`
- `build_log/426_recall_remeasurement_canonical_v2.md`
- `build_log/424_segmentation_recall_measurement.md` (the instrument this reuses)
- `cam/adapters/lease_review/lease_parameter_block.py`
- `build_log/423_evidence_assignment_architecture_spec.md` §8 (Gates A–D)

## Method

- **N = 10 runs.** Not 5. The parameter block is the layer everything downstream will stand on, and 5 was already too few to distinguish noise from effect on the Condition Precedent target in 426.
- Real Atreca document, `canonical_v2`, same prompt, same declared config.
- Each run: `extract_parameters()` → `attach_parameters_to_lp_evidence()` for LP-02 and LP-07 → `enforce_gate_b()`.
- **Config-integrity assertion (416 class):** assert identical `prompt_hash` and `config_hash` across all runs, `canonical=True`, `fallback_used=False`. If they drift, the measurement is void — say so and stop.

## What to measure

For each of the four parameters (`tenant_share`, `building_share`, `rent_adjustment_pct`, `base_rent`), across all 10 runs:

1. **Extraction rate** — how many of 10 runs produced a VERIFIED span? (Expect 10/10. Report what actually happened.)
2. **Offset stability** — are `(start_char, end_char)` IDENTICAL across all runs? Report the exact offsets per run. Any variation is a finding, however small.
3. **Span text stability** — is `span_text` byte-identical across runs? A span can resolve to the same offsets from a differently-worded quote; check the text, not just the numbers.
4. **Gate B outcome** — pass on all 10? Any abort?
5. **Attachment correctness** — does LP-07 receive exactly `[tenant_share, building_share]` and LP-02 exactly `[base_rent, rent_adjustment_pct]`, every run?

## Verify the matched text — do not trust the check

424 produced a false positive because a locator reported a hit by landing inside an adjacent span. For every parameter scored as extracted, PRINT the actual `span_text` and confirm it is the parameter — not a nearby row, not the label without the value.

Specifically confirm the span contains the VALUE, not just the label. A span reading `"Tenant's Share of Operating Expenses of Building:"` without `100%` is a FAILURE dressed as a success, and it is exactly the kind of thing that would pass a naive check.

## Do NOT

- Change `lease_parameter_block.py`, the prompt, the resolver, or the normalization profile — WHATEVER the results show
- Wire anything into `lease_adapter.py` or `lease_coverage.py`
- Build the selector panel, cited union, or trace validation
- Build structural addressing
- Run a baseline. No baseline exists and none may be cited.
- Touch `cam/core/`, evaluator identities, Stage 5 stabilization, or Priority Exposure
- Push

## Report — `build_log/428_gate_c_parameter_assignment_stability.md`

- Config-integrity assertion result
- **Per-parameter table: extraction rate (n/10), offsets per run, span text stability.** This is the headline.
- Gate B outcome per run
- Attachment correctness per run
- **A plain verdict: is the parameter block stable enough to wire into the live pipeline, or not?** State it as a yes or a no, with the evidence. Do not hedge into "mostly stable."
- If ANY parameter shows offset or text instability, say explicitly what that means for the dependency map: an unstable parameter span means the evidence LP-07 sees differs between runs, which is the same class of defect 421C documented, one layer up.

Required statements, verbatim:

> This measures parameter assignment stability on ONE document. It does not validate the architecture and does not measure stability on unseen documents.

> Gate C is a measurement, not a fix. No code was changed in this step regardless of the result.

## Git

Stage explicit paths only. No `git add .`. `git add -f` for `build_log/` (gitignored). Do not stage result directories. No push.

Commit message:
`428 Gate C parameter assignment stability measurement`
