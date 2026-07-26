# Step 448 — Post-run audit — CODE STATUS: **HALTED**

**Status: HALTED at Task 1, per the brief's own directive** — *"If any task cannot be completed as
specified, halt and report. Do not adjust the specification to make it completable."*

**Two tasks rest on premises that the preregistration text contradicts.** Both are Rule 6 findings:
the claim about document content does not survive opening the document. Tasks 2, 4, 5 and 6 are
unblocked and not started, pending a ruling on 1 and 3.

No harness edit, no rerun, no push, no remediation. All audit operations were read-only.

---

## TASK 0 — ARTIFACT IMMUTABILITY — **COMPLETE**

Entry and exit records in [448_input_hashes.md](448_input_hashes.md); script
[448_hash_artifacts.py](448_hash_artifacts.py), headed *"independent post-run validation, not
emitted by the sanctioned harness"*, opens run outputs in binary read mode only.

| artifact | ENTRY | EXIT | identical |
|---|---|---|---|
| `431_selection_measurement_sidecar.json` (818,521 B) | `c44573cb56d990af…` | `c44573cb56d990af…` | **yes** |
| `431_runtime_seam_capture.json` (533 B) | `01e0427e187b658d…` | `01e0427e187b658d…` | **yes** |
| `431_selection_measurement.md` (5,298 B) | `8f469cec0d5d50fc…` | `8f469cec0d5d50fc…` | **yes** |
| `431_validation.json` | NOT PRODUCED | NOT PRODUCED | **yes** |
| `431_repository_seam_check.json` | NOT PRODUCED | NOT PRODUCED | **yes** |
| `431_fatal_run_error.json` | NOT PRODUCED | NOT PRODUCED | **yes** |

**All run artifacts unchanged across the audit: True.**

---

## TASK 1 — PREREGISTERED 9.1 PREDICATE AUDIT — **HALTED**

### Rename applied
The satisfied / review_needed_disagreement / review_needed_no_qualifying_candidate table is renamed
**"Terminal certification-state distribution"** in all Step-448 outputs. It is not §9.1. The Step-447
status mislabelled it; that mislabelling is recorded here and is not repeated.

### Why the predicate audit cannot proceed as specified

The brief instructs: *"Quote verbatim, from the preregistration 9.1 text, the definition of each of
the four predicates: grounding discipline, citation discipline, same-candidate discipline,
disagreement preservation."*

**None of those four names appears anywhere in the preregistration.** Search executed against
`build_log/431_partB_measurement_instruction.md` (v3.3, the authorizing document named in the
manifest as `authorizing_instruction.document`):

```
$ for t in "grounding discipline" "citation discipline" "same-candidate discipline" "disagreement preservation"; do grep -n -i "$t" build_log/431_partB_measurement_instruction.md; done
=== "grounding discipline" ===        NOT PRESENT in the preregistration
=== "citation discipline" ===         NOT PRESENT in the preregistration
=== "same-candidate discipline" ===   NOT PRESENT in the preregistration
=== "disagreement preservation" ===   NOT PRESENT in the preregistration
```

**What §9.1 actually contains — nine criteria, not four.** Verbatim, lines 225–234:

> ### 9.1 Mechanism success criteria (pass/fail — from `431_validation.json` + `431_repository_seam_check.json` per §8.2, answer-key-INDEPENDENT)
> - No unverified span or unresolved/empty-grounded cited quote entered selection.
> - No parameter certified by cross-candidate assembly (validator checks same-id property supply).
> - No property borrowed from a semantic-support span to cure a deficient primary.
> - Per-field disagreement preserved; non-unanimous certification blocked (no implicit majority).
> - No terminal `unsatisfied_*` emitted (completeness not_established).
> - Certified parameters (if any) carry materialized `semantic_support_spans`, not value-only.
> - Every result carries the completeness qualifier per §9.0.
> - Complete audit artifact reconstructs each decision (candidate vs context citations distinct; per-candidate comparisons visible; per-panelist reasons retained).
> - No live pipeline file consumes the harness output.

**Where the four words do occur** — as a four-word gloss inside the v3.1→v3.2 amendment record,
line 9, not as definitions:

> the mechanism still worked (grounded, cited, disagreement-preserved, same-candidate)

**And §8.2, which §9.1 delegates to, specifies five measurement-class criteria, not four.** Verbatim,
lines 190–195:

> ```
> measurement_validation  →  431_validation.json      (computed from the sidecar)
>   - citation grounding (every cited quote resolves; empty/failed grounding invalidated per §5)
>   - same-candidate certification (one candidate_id supplied every property; no cross-candidate assembly)
>   - disagreement handling (non-unanimous certification blocked; per-field agreement preserved)
>   - completeness-limited negatives (no terminal unsatisfied_*; completeness not_established)
>   - semantic-support-span behavior (materialized, not value-only; no borrowed property)
> ```

### The ambiguity, stated rather than resolved
There is no 1:1 mapping from the four named predicates onto either the nine §9.1 criteria or the five
§8.2 criteria. Specifically: §8.2 carries a **single** criterion, `citation grounding`, that spans
what the brief separates into *"grounding discipline"* and *"citation discipline"*; and both §9.1 and
§8.2 carry criteria (`semantic-support-span behavior`, `completeness-limited negatives`, the audit-
reconstruction and no-live-consumption criteria) with no counterpart among the four names.

Choosing a mapping would be authoring a criterion after seeing results — the exact act the brief
forbids: *"no criterion may be authored or adjusted after seeing results."* Halting is therefore the
specified behaviour, not a shortfall.

**Nothing was evaluated. No predicate is reported as passing, failing, or NOT ESTABLISHED**, because
evaluating against a criterion set I selected would be the defect this task exists to prevent.

### What a re-spec needs to decide
Which criterion set governs — the nine §9.1 criteria, the five §8.2 `measurement_validation`
criteria, or a four-predicate set to be defined explicitly and *quoted into* the re-spec so it is
pre-registered rather than back-fitted.

---

## TASK 3 — SECTION 12 FIELD MAPPING — **HALTED (same defect class)**

Task 3.1 is completable and its evidence is below. **Task 3.2 is not**: it instructs *"Enumerate,
quoted verbatim from section 12, every field specified for `431_validation.json` and
`431_repository_seam_check.json`."*

**§12 specifies no fields.** It is a one-paragraph file list. Verbatim, line 266, in full:

> ## 12. Files
> Stage 1 (build): `431_selector_prompt.txt`, `431_output_schema.json`, `431_requirement_profiles.json`, `431_measurement_config.json`, `run_431_selection_measurement.py` (+ optional `validate_431.py` and seam-checker), `431_fixture_preflight.json`, `431_config_manifest.json`. Stage 2 (run): `431_selection_measurement_sidecar.json`, `431_runtime_seam_capture.json` (§8.2, captured in-process), `431_validation.json` (§8.2 measurement class), `431_repository_seam_check.json` (§8.2 artifact/seam class), `431_selection_measurement.md` (report). All under `build_log/`. No `cam/` file touched.

The field/criterion specification lives in **§8.2**, quoted under Task 1 above, plus the record shape
at lines 205–207:

> Each criterion in either artifact is a record:
> ```
> { criterion_id, status, evidence_artifact, evidence_pointer, details }
> ```

Since §12 specifies no fields, the (a)/(b)/(c) categorisation has no defined input. Substituting §8.2
for §12 would be adjusting the specification to make it completable — forbidden. **Halted; nothing
categorised.**

### Task 3.1 — completable, and completed (evidence for the recorded debt)
Verbatim, `build_log/run_431_selection_measurement.py` at P4 `d679eec`, lines 108–109:

```
108:VALIDATION_PATH = BUILD_LOG / "431_validation.json"
109:SEAM_CHECK_PATH = BUILD_LOG / "431_repository_seam_check.json"
```

Search establishing no write site, command and complete output:

```
$ git show d679eec:build_log/run_431_selection_measurement.py | grep -n "VALIDATION_PATH\|SEAM_CHECK_PATH"
108:VALIDATION_PATH = BUILD_LOG / "431_validation.json"
109:SEAM_CHECK_PATH = BUILD_LOG / "431_repository_seam_check.json"
```

Both identifiers occur **exactly once each**, at their definitions. There is no assignment, no
`write_lf`, no `json.dump`, no read. They are inert. Confirmed against the same file at P4 that the
sanction tag binds.

**Consequence, unremediated per scope:** the §8.2 `measurement_validation` and
`artifact_and_seam_validation` classes were never computed by the sanctioned package. Per §9.1's own
header the pass/fail table is *"from `431_validation.json` + `431_repository_seam_check.json`"* — and
per line 209, *"The report's §9.1 pass/fail table is COPIED FROM `431_validation.json` +
`431_repository_seam_check.json`, never authored."* Neither file exists, so **no §9.1 pass/fail table
can be copied, and none was.** This is the mechanism-success debt recorded in Step 447, restated
here with its evidence and left unremediated as instructed.

---

## TASKS 2, 4, 5, 6 — NOT STARTED
Unblocked and independently specified; not begun because the brief directs a halt rather than
continuation. Available to run immediately on a ruling.

---

## Git
`448_chat_instruction.md` written verbatim before any execution (Rule 7). This status,
`448_input_hashes.md`, and `448_hash_artifacts.py` committed with `git add -f` explicit paths.
**NOT pushed.** No harness edit, no rerun, no remediation.
