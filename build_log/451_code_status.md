# Step 451 — Rule 8 companion clause + retroactive producer/predicate censuses — CODE STATUS

Audit and `CLAUDE.md` only. No harness edit, no rerun, no push, **no remediation of anything the
census found**. Rule 6 throughout: every claim below carries a verbatim quote and a location, or is
marked `[UNVERIFIED]`.

**Headline: the census found FOUR further instances beyond the three known ones.** They are reported
prominently in Task B under "FOURTH AND FURTHER INSTANCES".

---

## TASK A — RULE 8 COMPANION CLAUSE — DONE

Added to `CLAUDE.md` immediately after the Step-450 producer-consumer census, verbatim:

> **Companion clause — predicate reachability.** Every specified predicate must be traced to a
> reachable satisfying assignment under the package's own declared field values. A predicate that
> cannot be satisfied by any conforming input halts the sanction.

Reason recorded with it, including the quoted conflict and the observation that no hash, signature,
scope, or cleanliness gate asks whether a specified success state is reachable — and that a census of
*products* (Rule 8) would not have caught this; only a census of *predicates* does.

---

## TASK B — PRODUCER-CONSUMER CENSUS, RETROACTIVE

Trace format: **specified product → producing function → write site → validator consumer → report
consumer.** Every `write_lf` site in the sanctioned harness (the complete persistence surface):

```
1302:    write_lf(REPORT_PATH, "\n".join(lines) + "\n")
1889:        write_lf(FATAL_PATH, json.dumps(terminal, indent=2))
1895:        write_lf(RUNTIME_SEAM_PATH, json.dumps(
1900:            write_lf(SIDECAR_PATH, json.dumps({
1937:    write_lf(SIDECAR_PATH, json.dumps(sidecar, indent=2))
2151:    write_lf(PREFLIGHT_PATH, json.dumps(preflight, indent=2))
2401:    write_lf(MANIFEST_PATH, json.dumps(manifest, indent=2))
```

**Seven write sites. No `431_validation.json`, no `431_repository_seam_check.json`.**

### §1 Stage-1 artifacts (seven)
| product | producer → write site | validator consumer | report consumer | verdict |
|---|---|---|---|---|
| `431_selector_prompt.txt` | authored artifact; hashed by `build_stage1` | *missing (no validator)* | `prompt_hash` in every trace | **producer COMPLETE; first missing link = validator consumer** |
| `431_output_schema.json` | authored; hashed | *missing* | `schema_hash` in every trace | same |
| `431_requirement_profiles.json` | authored; hashed | *missing* | `requirement_profiles_hash` | same |
| `431_measurement_config.json` | authored; hashed | *missing* | `config_hash` | same |
| `run_431_selection_measurement.py` | the harness itself | *missing* | — | same |
| `431_fixture_preflight.json` | `run_preflight()` → `write_lf(PREFLIGHT_PATH…)` line 2151 | *missing* | not surfaced in the report | **COMPLETE to write site; missing validator + report consumer** |
| `431_config_manifest.json` | `build_stage1()` → `write_lf(MANIFEST_PATH…)` line 2401 | consumed by the **runtime gate** and `_assert_stage2` | `config_hash` | **COMPLETE** |

### §8.1 `certification_trace` fields
Producer `certify_parameter_series()`; write site is the sidecar at line 1937.

| §8.1 field | written? | evidence |
|---|---|---|
| `parameter`, `lease`, `series_index` | ✅ | `traces.append({"parameter": parameter, "lease": lease, "series_index": k, …})` |
| `per_candidate{candidate_id, raw_attempt_index, canonical_attempt_index, series_index, relevance_ok, basis_match, text_role_ok, value_ok, support_ok, applicability_match, agreement_by_field, candidate_qualification}` | ✅ | `per_candidate_out.append({…})` |
| **`per_candidate.field_support_citation_ids`** | ❌ **NO WRITE SITE** | absent from the `per_candidate_out.append` literal (known instance 3) |
| **`semantic_support_span_ids`** | ❌ **NO WRITE SITE** | absent from the `traces.append` literal (known instance 2) |
| `completeness_provenance`, `prompt_hash`, `schema_hash`, `requirement_profiles_hash`, `config_hash`, `final_certification_state` | ✅ | in the `traces.append` literal |

**Validator consumer for every one of these fields — including the written ones — is MISSING**, because `431_validation.json` has no producer.

### §8.2 validation criteria and their two artifacts
Ten criteria across two artifacts (five `measurement_validation`, five `artifact_and_seam_validation`).
**First missing link = PRODUCER, for all ten** (known instance 1). §12 marks the producers
"(+ optional `validate_431.py` and seam-checker)"; §1 omits them; the eleven token-bound artifacts
contain neither.

### §9 report contents and §12 file lists — see below

---

## ⚠️ FOURTH AND FURTHER INSTANCES (reported separately and prominently)

### FOURTH — §9's per-evaluator × candidate report content has no producer
§9 line 220, verbatim:

> Per evaluator × candidate: all §5 fields, `field_support`, cited reason, confidence, real provider/model/fallback metadata, per-quote source-verification, `value_token_present`.

`render_report()` writes only: title, `config_hash`, admitted candidates, the completeness line, two
provenance paragraphs, the panel-integrity section, the Role-C note, and a flat per-trace list of
terminal states. **None of the line-220 content is emitted.** Occurrence counts in the produced
report:

```
confidence: 0    field_support: 0    value_token_present: 0    citation: 0
claude-sonnet: 0   gpt-5: 0    (grok: 2 — only inside the Role-C integrity note)
```

The data mostly exists in the sidecar; the **report producer never renders it**.

### FIFTH — §9.2's enumerated observations have no producer
§9.2 specifies six observation classes (cand_04 grounded components *and the citations establishing
value-to-basis linkage*; `basis_match` vs the opex requirement; cand_05 vs cand_06 distinguished by
`value_completeness`; cand_07 vs cand_03 `text_role`; whether Atreca certified; envelope sufficiency).
The report's only §9.2-labelled section is `## §9.1 / §9.2 per-parameter results`, which contains
**terminal states only**. `cand_04` appears in the report exactly once — in the admitted-candidates
list on line 4. **No §9.2 observation is rendered.**

### SIXTH — §10's envelope-sufficiency measurement has no producer
§10, verbatim: *"**Measure, do not assume, whether the frozen envelope from cand_04 reaches §3.3.**
Report char distance and inclusion."* Occurrence counts:

```
term                  harness  sidecar  report
char_distance            0        0        0
distance                 0        0        0
envelope_sufficiency     0        0        0
```

The envelope object records `context_start_char`, `context_end_char`, `boundary_method`,
`truncated_left/right` — but **no distance to §3.3 and no inclusion determination**. The §10
measurement was specified and never implemented, in the harness, the sidecar, or the report.

### SEVENTH — `value_token_present` is computed at certification time and then DISCARDED
A distinct category: not "never produced" but **produced and dropped before persistence**.

```
490:    vtp, vtp_hits = value_token_present(candidate_text, cfg)
513:        "value_token_present": vtp,
514:        "value_token_hits": vtp_hits,
```

Those land in the `comparison` dict, which `certify_parameter_series` attaches as `_comparison`
(line 1210) and then **removes before the trace is persisted**:

```
1215:            c.pop("_comparison", None)
```

Sidecar occurrences of `value_token_present`: **0**. It survives only in
`431_fixture_preflight.json` (line 2095, a Stage-1 preflight record) — which is not the
per-evaluator × candidate report content §9 requires. §9's requirement for it is therefore
unsatisfiable from the persisted run record.

---

## TASK C — PREDICATE-REACHABILITY CENSUS, RETROACTIVE

### §4 requirement profiles, per parameter
| parameter | `basis_match` rule (verbatim, from `431_requirement_profiles.json`) | reachable? |
|---|---|---|
| `tenant_share` | `"match iff \"operating_expenses\" is a MEMBER of the grounded value_applies_to_charge_basis_components…"` | **YES** — exercised; cand_01 reached `basis_match='match'` |
| `building_share` | `"match iff value_applies_to_charge_basis_components set_equals exactly {operating_expenses}"` | **reachable in principle; NOT EXERCISED** — no candidate provisioned (recorded amendment debt, unseeded) |
| `base_rent` | `"not_applicable — charge basis is not a meaningful attribute of base rent"` | **`match` UNREACHABLE** |
| `rent_adjustment_pct` | `"not_applicable — charge basis is not a meaningful attribute of a rent adjustment rate"` | **`match` UNREACHABLE** |

`text_role_ok`, `value_ok`, `support_ok`, `relevance_ok`, `applicability_match` are reachable for all
four parameters and were exercised.

### §8.1's certification conjunction — UNSATISFIABLE for two of four parameter types
**Clause 1**, §8.1 verbatim:

> For any `satisfied` result, the trace MUST mechanically show ONE candidate_id supplied every required property (relevance_ok ∧ basis_match=match ∧ text_role_ok ∧ value_ok ∧ support_ok ∧ applicability_match=applicable, all on that same id).

**Clause 2**, the harness's schema-fixed assignment, verbatim:

```python
SCHEMA_FIXED_NOT_APPLICABLE = {
    "base_rent": {"value_applies_to_charge_basis_components", "charge_scope"},
    "rent_adjustment_pct": {"value_applies_to_charge_basis_components", "charge_scope"},
}
```

together with §4's declaration that `basis_match` for those parameters is
`"not_applicable — charge basis is not a meaningful attribute…"`.

**These two clauses conflict.** For `base_rent` and `rent_adjustment_pct`, `basis_match` can only
ever take the value `not_applicable`; the conjunction requires `match`; therefore **no conforming
input satisfies §8.1's conjunction for those parameter types.** This is the empirical shape of the
Step-450 finding: 4 of 14 satisfied traces meet the literal conjunction, 14 of 14 meet it when
`not_applicable` is admitted. Which reading §8.1 intends is a preregistration question and is **not
decided here**.

### §9.1's nine criteria
| # | reachable under the package's own field values? | subject produced by the Part B harness? |
|---|---|---|
| 1 | yes | yes (`_unverified_quote_traces`, `_invalidated_fields`) — see note |
| 2 | **inherits §8.1's unsatisfiable conjunction for `base_rent` / `rent_adjustment_pct`** | yes (`per_candidate.candidate_id`) |
| 3 | n/a — empty domain | **NO** |
| 4 | yes | yes (`agreement_by_field`) |
| 5 | yes | yes |
| 6 | n/a — required field never written | **NO** |
| 7 | yes | yes (report) |
| 8 | yes | yes |
| 9 | yes | **subject is repository state, not a harness product** — a third category, distinct from both |

**Criteria whose subject the harness does not produce: #3 and #6 — the known instances. No further
instance of that kind was found.** Two adjacent findings, distinguished rather than merged:
- **#2 is not "subject not produced" — it is the one that inherits an unsatisfiable predicate.** Its
  subject is produced; its success state is unreachable for half the parameter types.
- **#9's subject is produced by neither harness nor run** — it is a property of the repository. It is
  checkable, but by a seam-checker that was never built.
- *Note on #1:* the criterion says "no unverified **span**"; the harness records unverified **quotes**
  (`_unverified_quote_traces`). Span verification happens at preflight (`431_fixture_preflight.json`).
  Whether "span" and "quote" are the same subject here is **[UNVERIFIED — not resolved by the
  preregistration text]** and is not resolved by me.

---

## TASK D — PROVENANCE OF THE §9.1 CRITERIA

Part A §11.1 (`431_partA_governed_selection_spec.md` line 330) contains **eight** criteria; Part B
§9.1 contains **nine**.

| Part B §9.1 | carried from Part A §11.1? | Part B harness produces its subject? |
|---|---|---|
| #1 no unverified span / unresolved quote | **YES** — A "No unverified span or unresolved cited quote ever enters selection." (Part B adds "empty-grounded") | yes |
| #2 no cross-candidate assembly | **YES** — A "No parameter is certified by cross-candidate attribute assembly (no laundering)." | yes |
| #3 no property borrowed from a semantic-support span | **YES** — A "…(§7.1)" | **NO** |
| #4 disagreement preserved, non-unanimous blocked | **YES** | yes |
| #5 no terminal `unsatisfied_*` | **YES, PARTIALLY** — Part A also required *"Incomplete candidate scope blocks certification"*; Part B §9.1 #5 **drops that clause** | yes (for the retained clause) |
| #6 certified package carries materialized `semantic_support_spans` | **YES** — A "The certified package carries materialized semantic-support spans, not a value-only parameter (§7.1)." | **NO** |
| #7 every result carries the completeness qualifier per §9.0 | **NO — Part-B-native**, added with the §9.0 report-format rule | yes |
| #8 complete audit artifact reconstructs each decision | **YES** | yes |
| #9 no live pipeline file consumes the harness output | **YES** | subject is repository state |

**Count established: eight of the nine §9.1 criteria were carried over from Part A §11.1; one (#7) is
Part-B-native. Of the eight carried over, TWO — #3 and #6 — name a subject (`semantic-support spans`,
§7.1 of Part A) that Part B's instrument never materializes.** Both entered Part B by copy without an
instrument check. A third carried-over criterion, #5, was copied with a clause silently dropped.

---

## Scope compliance
Nothing was remediated. No corrected package is proposed. The harness, the manifest, the eleven
token-bound artifacts, the signed tag and all run outputs are untouched; run-artifact hashes are
unchanged (sidecar `c44573cb…`, seam `01e0427e…`, report `8f469cec…`).

## Git
`451_chat_instruction.md` written verbatim before execution (Rule 7). This status and `CLAUDE.md`
committed with `git add -f` explicit paths. **NOT pushed.**
