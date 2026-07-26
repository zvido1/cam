# Step 448 REVISED — post-run audit — CODE STATUS

Audit only. No harness edit, no rerun, no push, no remediation. All operations read-only against run
outputs. Rule 6 applied throughout.

**Terminology correction carried throughout:** the satisfied / review_needed_disagreement /
review_needed_no_qualifying_candidate table is the **Terminal certification-state distribution**. It
is not §9.1. The Step-447 status mislabelled it.

---

## RULING ON THE HALT (recorded verbatim as directed)

> Your halt was correct on both tasks. The "four predicates" were authored by
> Chat from a parenthetical gloss in the v3.2 amendment record and were never
> preregistered. Withdrawn.
>
> Governing criterion set: the NINE criteria in §9.1. §8.2 is not a rival set;
> it is the evidence decomposition of §9.1 into a measurement class (5,
> sidecar-computed, -> 431_validation.json) and an artifact/seam class (5,
> repo/manifest/report-computed, -> 431_repository_seam_check.json), per §8.2's
> own words: "Not every §9.1 criterion is a sidecar property. Some are
> repository/manifest/report facts."
>
> ROOT-CAUSE FINDING (supersedes the "inert constants" framing):
> §12 marks `validate_431.py` and the seam-checker as "(+ optional)" Stage-1
> artifacts while listing `431_validation.json` and `431_repository_seam_check.json`
> as unconditional Stage-2 outputs. §1 omits the validators entirely. The
> manifest's eleven token-bound artifacts include neither. The optional
> producers were not built; the mandatory products therefore cannot exist; and
> §8.2 forbids authoring the table in their place. Lines 108-109 are the
> symptom, not the cause.
>
> CONSEQUENCE: §9.1 is UNPRODUCIBLE under package P4. Not merely unevaluated.
> Nothing in this step or any report may be labeled §9.1 for this run.

---

## TASK 0 — ARTIFACT IMMUTABILITY — COMPLETE

Records in [448_input_hashes.md](448_input_hashes.md). Scripts
[448_hash_artifacts.py](448_hash_artifacts.py) and [448_survey_91.py](448_survey_91.py) each carry
the header *"independent post-run validation, not emitted by the sanctioned harness"* and open run
outputs in read mode only.

| artifact | bytes | SHA-256 (entry, revised-entry, exit — all identical) |
|---|---|---|
| `431_selection_measurement_sidecar.json` | 818,521 | `c44573cb56d990afe7818dbdbfc3aa1e9586e51331a86b348b97f0e55967a9e7` |
| `431_runtime_seam_capture.json` | 533 | `01e0427e187b658d07947978b30e6bb8a78b9e2f0551180d00cde364d10ec981` |
| `431_selection_measurement.md` | 5,298 | `8f469cec0d5d50fcfbfdaf65b4c53c1034640e58b0cf07092b4fb8d47bfe3603` |
| `431_validation.json` | — | NOT PRODUCED |
| `431_repository_seam_check.json` | — | NOT PRODUCED |
| `431_fatal_run_error.json` | — | NOT PRODUCED |

**All run artifacts unchanged across the audit.**

---

## TASK 1-REVISED — §9.1 COMPUTABILITY SURVEY (NOT an evaluation)

**No status, pass, fail, satisfied or not-established judgment is emitted on any criterion below.**
PRESENT / PARTIAL / ABSENT describe *data availability only* — whether a future validator could
compute the criterion. Producing a §9.1 verdict here would be the prohibited authorship.

Each criterion quoted verbatim from `build_log/431_partB_measurement_instruction.md` lines 226–234.

| # | §9.1 criterion (verbatim) | data | evidence pointer |
|---|---|---|---|
| 1 | "No unverified span or unresolved/empty-grounded cited quote entered selection." | **PRESENT** | sidecar `series[*].{canonical,degraded}_panels[*].per_role[*].judgment._unverified_quote_traces` (entries carry `{field, citation_id, quote, class, resolved}`; 1 of 108 judgments non-empty) and `._invalidated_fields` (7 of 108 non-empty); citation text in `.candidate_citations[]` / `.context_citations[]`; per-field linkage in `.field_support` |
| 2 | "No parameter certified by cross-candidate assembly (validator checks same-id property supply)." | **PRESENT** | sidecar `certification_traces[*].per_candidate[*].candidate_id` (one record per supplying candidate per series) |
| 3 | "No property borrowed from a semantic-support span to cure a deficient primary." | **PARTIAL** | The candidate/context distinction exists — `judgment.candidate_citations` vs `judgment.context_citations`, and `field_support.{candidate_citation_ids, context_citation_ids}` per field. **Missing:** no field named or typed as a *semantic-support span* is recorded (`grep semantic_support_span` over the sidecar → **0 occurrences**), so whether "context citation" is the recorded form of "semantic-support span" is not established by the artifacts. Naming that equivalence would be interpretation and is not made here. |
| 4 | "Per-field disagreement preserved; non-unanimous certification blocked (no implicit majority)." | **PRESENT** | sidecar `certification_traces[*].per_candidate[*].agreement_by_field` (six fields, values `unanimous` / `majority_with_dissent` / `split` / `not_assessable`) with `final_certification_state` on the same trace |
| 5 | "No terminal `unsatisfied_*` emitted (completeness not_established)." | **PRESENT** | sidecar `certification_traces[*].final_certification_state` and `.completeness_provenance.status`; mirrored in the report's 30 result lines |
| 6 | "Certified parameters (if any) carry materialized `semantic_support_spans`, not value-only." | **ABSENT** | `semantic_support_spans` appears **0 times** in the sidecar (literal string search over all 818,521 bytes). The criterion names the field explicitly; the run recorded no field under that name. Certified series exist (14 `satisfied`), so the criterion's antecedent is met and its required data was never recorded. |
| 7 | "Every result carries the completeness qualifier per §9.0." | **PRESENT** | `431_selection_measurement.md` — 30 result lines, 31 occurrences of `completeness: not_established` (the 31st is the document-level `- completeness:` header line) |
| 8 | "Complete audit artifact reconstructs each decision (candidate vs context citations distinct; per-candidate comparisons visible; per-panelist reasons retained)." | **PRESENT** | distinct citation arrays (`candidate_citations` / `context_citations`); per-candidate comparisons at `certification_traces[*].per_candidate[*]` (`relevance_ok`, `basis_match`, `text_role_ok`, `value_ok`, `support_ok`, `applicability_match`, `candidate_qualification`); per-panelist prose at `judgment.reason`; per-attempt provenance at `per_role[*].attempts[]` |
| 9 | "No live pipeline file consumes the harness output." | **PRESENT** (repository fact) | computable from the repo: `grep -rln "431_selection_measurement_sidecar\|431_selection_measurement\.md\|431_runtime_seam_capture" --include=*.py --include=*.json --include=*.ts --include=*.js .` excluding `build_log/` returns an empty list |

### §9.1 ↔ §8.2 mapping
§8.2 measurement class (lines 190–195) and artifact/seam class (lines 197–202):

| §8.2 criterion | class | maps to §9.1 |
|---|---|---|
| citation grounding | measurement | #1 |
| same-candidate certification | measurement | #2 |
| disagreement handling | measurement | #4 |
| completeness-limited negatives | measurement | #5 |
| semantic-support-span behavior | measurement | **#3 and #6 (one §8.2 criterion spans two §9.1 criteria)** |
| reviewed hashes equal run hashes | artifact/seam | **no §9.1 counterpart** |
| pre/post `cam/` git status clean | artifact/seam | **no §9.1 counterpart** |
| no live import/consumption seam | artifact/seam | #9 |
| report completeness qualifiers present | artifact/seam | #7 |
| report pass/fail values equal validator output | artifact/seam | **no §9.1 counterpart** |

**§9.1 criterion with no §8.2 counterpart:** #8 ("Complete audit artifact reconstructs each
decision…") is not decomposed into either evidence class.

**§8.2 criteria with no §9.1 counterpart:** three — *reviewed hashes equal run hashes*, *pre/post
`cam/` git status clean*, and *report pass/fail values equal validator output*.

### The self-referential seam criterion
§8.2 requires (line 202): *"report pass/fail values equal validator output (the §9.1 table was
copied, not authored)"*. **This criterion is not satisfiable in principle when no validator output
exists.** It is a comparison between two operands; with `431_validation.json` absent, one operand
does not exist, and the report correspondingly contains no §9.1 pass/fail table to serve as the
other. The criterion has no defined referent for this run. This is a structural observation about
the criterion's inputs, not a verdict on the criterion.

---

## TASK 2 — CAND_04 TERMINAL-STATE DERIVATION

### 2.1 The policy code, quoted — routing confirmed from code, not inference
`build_log/run_431_selection_measurement.py` at P4, `merge_panel()` — how three role values become
one per-field agreement label:

```python
    for field in SEMANTIC_FIELDS:
        vals = [norm(j.get(field)) for j in judgments]
        substantive = [v for v in vals if v not in ("unclear", "not_assessable", None)]
        distinct = set(vals)
        if not substantive:
            merged[field], agreement[field] = "unclear", "not_assessable"
        elif len(distinct) == 1:
            merged[field], agreement[field] = vals[0], "unanimous"
        elif len(set(substantive)) == 1 and len(substantive) >= 2:
            merged[field], agreement[field] = substantive[0], "majority_with_dissent"
        else:
            merged[field], agreement[field] = "DISPUTED", "split"
```

`certify()` — the terminal-state selection, with the disagreement branch **preceding** the
no-qualifying-candidate branch:

```python
    for c in per_candidate:
        if (c["candidate_qualification"] == "qualified"
                and c["applicability_match"] == "applicable"):
            return "satisfied"

    # No implicit majority: any non-unanimous relevant field routes to disagreement.
    for c in per_candidate:
        for field, state in c["agreement_by_field"].items():
            if state in ("majority_with_dissent", "split"):
                return "review_needed_disagreement"

    if any(c["applicability_match"] == "applicable" for c in per_candidate):
        return "applicable_no_supplied_candidate_qualified"
    if not completeness_established:
        return "review_needed_no_qualifying_candidate"
    return "review_needed_no_qualifying_candidate"
```

**Derivation for `unclear` + `none` + `none`:** `substantive` excludes `"unclear"`, leaving
`["none","none"]`; `distinct` = {`unclear`,`none`} so the `unanimous` branch is not taken;
`len(set(substantive)) == 1 and len(substantive) >= 2` holds → **`majority_with_dissent`**. In
`certify()`, that value is caught by the disagreement loop, which returns before either
`no_qualifying_candidate` return is reachable. For `unclear` + `none` + `unclear`, `substantive` =
`["none"]` — length 1 — so the final `else` applies → **`split`**, also caught by the same loop.

**This is why cand_04 routed to `review_needed_disagreement` and not
`review_needed_no_qualifying_candidate`: the routing is decided by the agreement label, and the
disagreement branch is evaluated first.** Confirmed against recorded data — 4 series
`majority_with_dissent`, 1 series `split`, all 5 → `review_needed_disagreement`.

### 2.2 Role-B across the canonical series, including the sixth (replacement) attempt
| canonical panel | raw attempt | role A | **role B** | role C |
|---|---|---|---|---|
| 1 | 1 | `unclear` | **`none`** | `none` |
| 2 | 2 | `unclear` | **`none`** | `none` |
| 3 | 3 | `unclear` | **`none`** | `none` |
| 4 | 5 | `unclear` | **`none`** | `unclear` |
| **5** | **6 (replacement)** | `unclear` | **`none`** | `none` |

The replacement attempt's role-B judgment is `none` — **identical to the other four canonical
role-B judgments. The canonical series is visibly consistent: 5/5 role-B = `none`.**

### 2.3 Degraded-attempt disclosure
The single degraded attempt of the entire run occurred **on cand_04 — the forcing candidate** — at
**raw attempt 4**, cause **`reasoning_exhaustion`**, substitution **`gpt-5.5` → `gpt-5.4`**. Its
role-B judgment was **`unclear`** — the one role-B judgment in the whole cand_04 set that was not
`none`. It was **excluded from canonical N** (`canonical: false`,
`canonical_attempt_index: None`).

**The exclusion is why the result is unaffected:** the degraded panel is never an input to
`certify()`, which consumes canonical panels only; and the canonical series that replaced it
(raw attempt 6) returned role-B `none`, matching the other four. Had the degraded attempt been
counted, it would have been the sole dissenting role-B value in the set.

### 2.4 Finding (recorded verbatim as directed)

> "Under the v3.3 relation-bearing representation, the live panel emitted no
> false operating-expense linkage and the system produced no false
> certification. The run did not isolate whether that outcome was caused by
> the prompt/schema representation, evaluator behavior, or their interaction.
> The policy-layer rejection of a positively asserted but false value-to-basis
> linkage remains unexercised."

> "cand_04's five review_needed_disagreement outcomes arose from `unclear`
> versus `none`, not from competing substantive assertions about the basis."

---

## TASK 3-REVISED — DEPENDENCY-CHAIN FINDING

### §12 in full (line 266, verbatim)
> ## 12. Files
> Stage 1 (build): `431_selector_prompt.txt`, `431_output_schema.json`, `431_requirement_profiles.json`, `431_measurement_config.json`, `run_431_selection_measurement.py` (+ optional `validate_431.py` and seam-checker), `431_fixture_preflight.json`, `431_config_manifest.json`. Stage 2 (run): `431_selection_measurement_sidecar.json`, `431_runtime_seam_capture.json` (§8.2, captured in-process), `431_validation.json` (§8.2 measurement class), `431_repository_seam_check.json` (§8.2 artifact/seam class), `431_selection_measurement.md` (report). All under `build_log/`. No `cam/` file touched.

### §9.1 header line (line 225, verbatim)
> ### 9.1 Mechanism success criteria (pass/fail — from `431_validation.json` + `431_repository_seam_check.json` per §8.2, answer-key-INDEPENDENT)

### §8.2 "COPIED FROM … never authored" sentence (line 209, verbatim)
> **The report's §9.1 pass/fail table is COPIED FROM `431_validation.json` + `431_repository_seam_check.json`, never authored.**

### §1 Stage-1 artifact list (lines 28–35, verbatim)
> **Stage 1 — ratifying THIS document authorizes BUILD ONLY, zero model calls.** Claude Code produces, and commits to `build_log/`, these artifacts:
> - `431_selector_prompt.txt` — the exact selector prompt (§5), model-facing text, no fixture labels/hints.
> - `431_output_schema.json` — the exact JSON output schema for a panelist judgment (§5).
> - `431_requirement_profiles.json` — the versioned per-parameter requirement profiles (§4), declared independent of fixtures.
> - `431_measurement_config.json` — every frozen deterministic value (§3): envelope algorithm + budget + allocation + `context_policy_version`, `value_token_detector` + version, attempt ceiling, `certification_policy_version`.
> - `run_431_selection_measurement.py` — the harness (builds against the above; makes NO calls at build stage).
> - `431_fixture_preflight.json` — the fixture-preflight result (§6): full source hashes, per-candidate quote resolution, unique-resolution check.
> - `431_config_manifest.json` — the hash of each artifact above, so the reviewed config is the run config.

**§1 lists seven artifacts and names neither `validate_431.py` nor a seam-checker.**

### Harness lines 108–109 and the no-write-site evidence (carried forward from 3.1)
```
108:VALIDATION_PATH = BUILD_LOG / "431_validation.json"
109:SEAM_CHECK_PATH = BUILD_LOG / "431_repository_seam_check.json"
```
```
$ git show d679eec:build_log/run_431_selection_measurement.py | grep -n "VALIDATION_PATH\|SEAM_CHECK_PATH"
108:VALIDATION_PATH = BUILD_LOG / "431_validation.json"
109:SEAM_CHECK_PATH = BUILD_LOG / "431_repository_seam_check.json"
```
Each identifier occurs **exactly once, at its definition**. No assignment, no `write_lf`, no
`json.dump`, no read.

### No validator or seam-checker among the eleven token-bound artifacts
From `431_config_manifest.json` at P4 — `artifact_hashes` / `committed_blob_binding`, eleven entries:

```
431_measurement_config.json          431_sanction_allowed_signers
431_requirement_profiles.json        431_sanction_key.pub
431_output_schema.json               431_sanction_policy.json
431_selector_prompt.txt              atreca_eastjamie_southsf_lease.txt
431_fixture_preflight.json           atlas_meridian_warehouse_lease.txt
run_431_selection_measurement.py
```

**Neither `validate_431.py` nor any seam-checker is present.** They are not token-bound, not
sanctioned, and were never built.

### Root cause (recorded, not remediated)
§12 marks the producers *"(+ optional `validate_431.py` and seam-checker)"* while listing their
outputs `431_validation.json` and `431_repository_seam_check.json` as unconditional Stage-2 files.
§1 omits the producers entirely, so nothing in the Stage-1 authorization required them. The manifest
binds eleven artifacts, none of which is a validator. **Optional producers, mandatory products.** The
producers were not built; the products therefore cannot exist; and §8.2 line 209 forbids authoring
the table in their place. Lines 108–109 are the symptom, not the cause.

**No remediation attempted and no corrected package proposed, per scope.**

---

## TASK 4 — COUNT RECONCILIATION

### 109 router initializations vs 108 role-calls — the extra one, named
Per-key comparison of log initializations against sidecar role-calls shows exactly one row with a
delta:

```
key                | log inits | sidecar calls | delta
openai B cand_04   |     7     |       6       |  +1
```

**The extra initialization is the own-chain fallback inside the single degraded role-call** —
cand_04, raw attempt 4, role B. That one role-call made two provider attempts, each initializing the
router:

```
attempt 1: provider=openai model=gpt-5.5 parse_ok=False error=empty_content: model returned no output
attempt 2: provider=openai model=gpt-5.4 parse_ok=True  error=None
recorded actual_model: gpt-5.4  is_fallback: True  fallback_reason: reasoning_exhaustion
```

109 = 108 role-calls + 1 fallback re-initialization. **Note for precision:** the recorded
`fallback_reason` is `reasoning_exhaustion`, while the underlying attempt error string is
`empty_content: model returned no output`. Both are recorded; they are not the same string.

### 36 raw attempts vs 35 canonical panels — explicit arithmetic
| candidate | raw | canonical | degraded |
|---|---|---|---|
| cand_01 | 5 | 5 | 0 |
| cand_02 | 5 | 5 | 0 |
| cand_03 | 5 | 5 | 0 |
| **cand_04** | **6** | **5** | **1** |
| cand_05 | 5 | 5 | 0 |
| cand_06 | 5 | 5 | 0 |
| cand_07 | 5 | 5 | 0 |
| **TOTAL** | **36** | **35** | **1** |

35 + 1 = 36. Role-calls = 36 raw attempts × 3 roles = **108**.

### Seven candidates → 30 parameter-lease series
| lease | parameter | candidate(s) | series | terminal states |
|---|---|---|---|---|
| atreca | tenant_share | cand_01 | 5 | satisfied 4, review_needed_disagreement 1 |
| atreca | base_rent | cand_02 | 5 | satisfied 5 |
| atreca | rent_adjustment_pct | cand_03 | 5 | review_needed_disagreement 5 |
| atlas | tenant_share | cand_04 | 5 | review_needed_disagreement 5 |
| atlas | base_rent | **cand_05 + cand_06** | 5 | satisfied 5 |
| atlas | rent_adjustment_pct | cand_07 | 5 | review_needed_no_qualifying_candidate 5 |

**Seven candidates map to six parameter-lease combinations** — `cand_05` (definition stub) and
`cand_06` (operative schedule) both supply `atlas / base_rent` and are compared within the same
series. 6 combinations × 5 series = **30**.

### Recorded as directed
**Atreca is the known-good foil** and returned `tenant_share` 4/5 and `rent_adjustment_pct` 0/5 with
five disagreements. This is replicate variance on the control and constrains all reproducibility
language: the control did not reproduce identically across replicates.

**`completeness: not_established` on all 30 series bounds every negative outcome.** Atlas's five
`review_needed_no_qualifying_candidate` outcomes **do not establish document-level absence of a rent
adjustment**.

---

## TASK 5 — EXECUTION-PREREQUISITES CONTRACT

Authored at [448_execution_prerequisites.md](448_execution_prerequisites.md), recorded as **a
post-run artifact documenting an undeclared package requirement**, not a restatement of a package
declaration. Evidence that the package declares nothing: `grep -c "getenv\|environ\|dotenv"` over the
sanctioned harness returns **0**; the manifest returns **0** for `env|api_key`. The `os.getenv` call
sites are in `cam/core/provider_router.py` lines 319, 431, 738 (quoted in the contract). Names only —
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY` — no value appears. Log scan: 0 `sk-`/`xai-`
matches; the single long token is the public sanction token T4.

> "Package identity is repository-reproducible; successful live execution additionally requires a
> declared external environment."

---

## TASK 6 — PANEL-IDENTITY WORDING

All frozen-panel language is replaced by, and this wording governs going forward:

> "The canonical panel identity was enforced through provenance, exclusion, and retry. One gpt-5.5
> failure triggered an own-chain gpt-5.4 substitution; that attempt was marked noncanonical,
> excluded from canonical N, and replaced by an additional attempt."

**Detection-and-exclusion, not prevention.** The substitution was not prevented from occurring; it
was detected, labelled, excluded, and compensated.

---

## DELIVERABLE ADDITION — is the 108-call run salvageable?

**Partially. A validator-only package could compute seven of the nine §9.1 criteria over the
immutable sidecar with zero model calls. It could not compute all nine, because criterion 6's
required data was never recorded.**

This follows from the survey, not from a prior decision:

- **Computable with zero model calls (7):** criteria 1, 2, 4, 5, 7, 8, 9 — all PRESENT, each with a
  cited artifact and pointer. Criteria 7 and 9 are report/repository facts, not sidecar facts, and
  need the artifact/seam-class producer rather than the measurement-class one.
- **Not computable (1):** criterion 6 names `semantic_support_spans`; that string occurs **0 times**
  in the sidecar. Certified series exist, so the criterion's antecedent is met and its evidence is
  absent. **No re-run can be avoided for this criterion by any amount of post-hoc computation** —
  the data was not recorded at call time.
- **Blocked pending a definition, not pending data (1):** criterion 3 is PARTIAL. The
  candidate/context citation distinction is fully recorded; what is missing is whether a "context
  citation" *is* the recorded form of a "semantic-support span". That is a definitional question for
  the preregistration, not a data question. If §8.2's `semantic-support-span behavior` is defined to
  operate on `context_citations`, criterion 3 becomes computable from existing data; criterion 6
  would still require a materialized-span record that does not exist.

**Consequence, stated plainly:** the 108 calls are not wasted — the great majority of the mechanism
evidence survives in the immutable sidecar and is recomputable without spending another call. But
**§9.1 as a whole cannot be completed from the Step-447 outputs.** A complete §9.1 requires a
corrected package that records materialized semantic-support spans, and therefore a re-run. Whether
a seven-of-nine partial computation is worth publishing under a name other than §9.1 is a ruling for
Chat/GPT, not a decision taken here.

---

## Git
`448_chat_instruction.md` rewritten to the revised text verbatim before execution, with the false-
premise note (Rule 7). This status, `448_input_hashes.md`, `448_execution_prerequisites.md`,
`448_hash_artifacts.py` and `448_survey_91.py` committed with `git add -f` explicit paths.
**NOT pushed.** No harness edit, no rerun, no remediation.
