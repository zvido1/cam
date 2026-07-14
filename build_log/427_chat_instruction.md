CAM — Step 427: parameter block + declared dependency map. No baseline. No push.

## Part 0 — MANDATORY, BEFORE ANY OTHER WORK

Per CLAUDE.md Rule 7: write this brief VERBATIM to `build_log/427_chat_instruction.md` before doing anything else. Do not paraphrase, summarize, or improve it. It is the document you will be audited against.

## Purpose

This is the fix. Everything since 421C has been building ground to stand on.

LP-07's evaluators have never seen the 100% tenant share — not in 101 Gemini-primary runs, not in the Atlas validation corpus, not once. Step 427 is the step where that changes.

The substrate is ready. Under `canonical_v2`, across N=5 × 32 LPs (Step 426), these four parameters verify at 5/5 with byte-stable offsets:

| Parameter            | Verified span text                                      |
|----------------------|---------------------------------------------------------|
| `tenant_share`       | `Tenant's Share of Operating Expenses of Building: 100%` |
| `building_share`     | `Building's Share of Project: 45.79%`                    |
| `rent_adjustment_pct`| `Rent Adjustment Percentage: 3%`                         |
| `base_rent`          | `Base Rent: $3.75 per rentable square foot`              |

They are short, discrete, labelled rows — the cleanest objects in the corpus, and entirely untouched by the ellipsis-elision class that accounts for 100% of remaining unverified spans.

## Read

- `build_log/423_evidence_assignment_architecture_spec.md` (§5 is the authority for this step)
- `build_log/421C_evidence_assignment_incident.md`
- `build_log/426_recall_remeasurement_canonical_v2.md`
- `build_log/422C_wire_extraction_completeness_gate.md` (the fail-closed gate pattern to follow)
- `build_log/422D_fix_canonicality_source.md` (canonicality is read explicitly, never inferred)
- `cam/adapters/lease_review/lease_evidence_spans.py`
- `cam/adapters/lease_review/lease_element_elicitation.py`
- `Docs/Design_Note_Structural_Addressing_2026_07_14.md` (context for what is deliberately NOT being built)

## Task

### 1. Named parameter set

A first-class structure — NEVER a provision, NEVER an LP.

Each parameter carries: a name, a verified `EvidenceSpan`, and provenance.

Parameters are extracted as DOCUMENT parameters, not as one provision's clause text. This is the architectural point: the key-terms table is not "LP-00's content." It is the document's quantitative spine, on which many provisions depend.

Start with exactly these four: `tenant_share`, `building_share`, `rent_adjustment_pct`, `base_rent`.

### 2. Declared dependency map

Per-LP, in code, explicit:

```

LP-02 (Rent / Escalation)   depends_on: [base_rent, rent_adjustment_pct]
LP-07 (Operating Expenses)  depends_on: [tenant_share, building_share]

```

Start with exactly these two LPs and these four parameters. DO NOT speculate additional dependencies. Every entry must be justifiable from a measured, verified span. A dependency map with unmeasured entries is a gate that will fail for reasons unrelated to the architecture.

### 3. Deterministic attachment

Code attaches the parameter's verified span to every dependent LP's evidence context.

The model is NEVER asked to remember to include the tenant share in LP-07 — and therefore cannot forget to. No model discretion at any point in this step.

### 4. Gate B — completeness on declared dependencies

Every declared dependency must be satisfied by a VERIFIED span in the dependent LP's evidence context, or the extraction is rejected and no analysis is produced.

Two properties are load-bearing and must be implemented as stated:

- **Keyed to declared dependencies, NOT to literal values.** The gate must never search for the string `"45.79%"`. That figure is specific to one lease and worthless on the next. The rule is: every declared dependency has a verified span. That generalizes.
- **Orthogonal to evaluator agreement.** The gate checks dependencies, never votes. Three evaluators agreeing does not satisfy a dependency. AGREEMENT IS NOT SUFFICIENCY.

Gate B fails closed in canonical mode (`GateAbortError`, before Stage 5 — same pattern as 422C). Read `meta["canonical"]` explicitly per 422D; never infer canonicality from `fallback_used`.

## Do NOT

- Build the selector panel, cited union, or trace validation (later slices)
- Build structural addressing (see the design note — deliberately deferred)
- Change the prompt, the resolver, or the normalization profile
- Touch `cam/core/`, evaluator identities, Stage 5 stabilization, or Priority Exposure
- Run a baseline. No baseline exists and none may be cited.
- Push

## Tests

- Each of the four parameters extracts to a verified span with correct offsets
- Attachment is deterministic: LP-07's evidence context contains `tenant_share` and `building_share` on EVERY run; LP-02 contains `base_rent` and `rent_adjustment_pct`
- The same span attaches to MULTIPLE LPs without being consumed — non-destructive assignment, the property the old extractor structurally could not have
- Gate B passes when all declared dependencies are satisfied
- Gate B ABORTS (canonical) when a declared dependency has no verified span — test by removing one
- Gate B is keyed to dependency names, not literal values: a test asserting the gate contains no lease-specific string constants
- Gate B does not consult evaluator votes (spy test, or source inspection)
- `canonical=False` + missing dependency → degraded, NOT abort
- Full regression green

## Report — `build_log/427_parameter_block_dependency_map.md`

State plainly whether LP-07's evidence context now contains the 100% tenant share. That is the question this step exists to answer.

QUOTE the attached span text and its offsets. Do not characterize — quote (CLAUDE.md Rule 6).

Include: the parameter schema, the dependency map as implemented, the attachment mechanism, Gate B's behavior, tests EXECUTED with pasted output, and what remains unwired.

Required statements, verbatim:

> Attachment is deterministic. The model is never asked to include a parameter in a dependent LP and therefore cannot forget to.

> Gate B is keyed to declared dependencies, never to literal values, and never to evaluator agreement. Agreement is not sufficiency.

> This step does not build the selector panel. Span-to-LP relevance beyond the declared parameter dependencies remains ungoverned.

## Docs

Update if appropriate:
- `Docs/CAM_Current_State.md`
- `Docs/Patent_Current_State.md`

## Git

Stage explicit paths only. No `git add .`. `git add -f` for `build_log/` and `Docs/` (both gitignored).

Also stage the already-written, currently-unstaged design note:
- `Docs/Design_Note_Structural_Addressing_2026_07_14.md`

Do not stage result directories. No push.

Commit message:
`427 parameter block and declared dependency map`
