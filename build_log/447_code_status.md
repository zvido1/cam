# Step 447 — Stage-2 execution — CODE STATUS

**Status:** COMPLETE — the measurement ran to completion under the verified sanction. **108 primary
provider calls**, the first of the entire arc. No fatal, no halt, no retry-shopping, no silent
substitution. **Two of the five §12 artifacts do not exist and cannot be produced by the sanctioned
package — see "Deferred/blocked" below (top, per Rule 5).**

## DEFERRED / BLOCKED (stated first)
`431_validation.json` and `431_repository_seam_check.json` were **NOT produced**. This is not a run
failure: at P4 the constants `VALIDATION_PATH` (line 108) and `SEAM_CHECK_PATH` (line 109) are
**defined and never written** — they appear nowhere else in the harness. They are inert. The §12
deliverable list names five artifacts; the sanctioned package can only ever emit three (plus
`431_fatal_run_error.json` on a fatal path, correctly absent here).

I did **not** fix this: the harness bytes are token-bound, so editing it would void the sanction that
was just audited and signed. **Needs a ruling** — either the §12 list is wrong, or a future package
must implement the two writers (new P/T/tag/message).

## Execution environment
Fresh detached worktree at **P4 `d679eec8525fa672724a012f7d1fac0d0d8e7620`**; HEAD == P4, detached,
`git status --porcelain --untracked-files=all` **empty**, both leases present, sanction tag verifies
from inside the worktree.

**Gate output (before the first call):**
```
[443] repository execution identity verified: 11 artifacts; HEAD=d679eec8525f
      token=ef1a7af7f77d (recomputed from HEAD blobs)
      commit_bound_via_signed_tag=stage2-sanction-431-ef1a7af7
```

**Key handling:** the harness reads `os.getenv` directly and does not call `load_dotenv`. It could
not be modified (token-bound), so keys were injected via the process environment by an external
launcher. Env vars are not part of the package; the worktree stayed clean. No key value was printed.

## Call count and panel-identity provenance
**108 role-calls** = 36 panels x 3 roles (35 canonical + 1 degraded); 36 raw attempts.

| role | provider/model | is_fallback | canonical | calls |
|---|---|---|---|---|
| A | anthropic/claude-sonnet-4-6 | no | yes | 36 |
| B | openai/gpt-5.5 | no | yes | 35 |
| B | openai/**gpt-5.4** | **yes** | **no** | **1** |
| C | xai/grok-4.3 | no | yes | 36 |

**The single substitution** — cand_04, raw attempt 4, role B fell back `gpt-5.5 -> gpt-5.4`,
`fallback_reason: reasoning_exhaustion`. Recorded as **degraded**, `canonical: false`
(*"actual openai/gpt-5.4 != frozen primary openai/gpt-5.5 - degraded substitution, excluded from
canonical N"*), and **excluded from canonical N**. The series took a 6th raw attempt to reach
canonical_N=5. Degraded was never promoted. **No canonical shortfall on any candidate (5/5 x 7).**

Role B's temperature omission fired as documented (`TEMPERATURE_ONLY_DEFAULT_MODELS`: gpt-5.5 accepts
only provider-default temperature; declared 0.0 omitted). Roles A and C transmitted `temperature=0`.

## §9.1 mechanism-success — COPIED from validator `final_certification_state`, not authored
| parameter | lease | series | satisfied | review_needed_disagreement | review_needed_no_qualifying_candidate |
|---|---|---|---|---|---|
| tenant_share | atreca | 5 | 4 | 1 | 0 |
| base_rent | atreca | 5 | 5 | 0 | 0 |
| rent_adjustment_pct | atreca | 5 | 0 | 5 | 0 |
| tenant_share | atlas | 5 | 0 | 5 | 0 |
| base_rent | atlas | 5 | 5 | 0 | 0 |
| rent_adjustment_pct | atlas | 5 | 0 | 0 | 5 |
| **TOTAL** | | **30** | **14** | **11** | **5** |

`completeness` = `not_established` for all 30 series (no terminal `unsatisfied_*` emitted, §8.3).

Agreement by field across the 35 certified candidate records:
`parameter_family_relevance` 35 unanimous · `charge_scope` 35 unanimous · `value_completeness` 35
unanimous · `candidate_support_state` 29 unanimous / 6 split · `text_role` 29 unanimous / 6 split ·
`value_applies_to_charge_basis_components` 30 unanimous / 4 majority_with_dissent / 1 split.

The 11 `review_needed_disagreement` outcomes are an **observed result**, not a mechanism failure. The
frozen unanimity threshold was not touched.

## §9.2 — cand_04 (the pre-registered question)
Candidate text: `"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area
of the Demised Premises to the total rentable area of the Building.`

**No panelist grounded `operating_expenses` as applying to the 22.4% value. Count: 0 of 18
role-judgments** (5 canonical panels x 3 roles, plus the degraded panel's 3).

| panel | role A (sonnet-4-6) | role B (gpt-5.5) | role C (grok-4.3) |
|---|---|---|---|
| canonical 1 | `unclear` | `none` | `none` |
| canonical 2 | `unclear` | `none` | `none` |
| canonical 3 | `unclear` | `none` | `none` |
| canonical 4 | `unclear` | `none` | `unclear` |
| canonical 5 | `unclear` | `none` | `none` |
| degraded raw4 | `unclear` | `unclear` (gpt-5.4) | `none` |

Because no panelist asserted `operating_expenses`, **there is no value-to-basis citation to examine**.
All 5 cand_04 series certified `review_needed_disagreement`; **cand_04 was not `satisfied`.** The
brief's caution about a satisfied cand_04 being a grounded panel assertion rather than truth
therefore did not arise — and nothing here should be read as evidence about whether the Atlas lease
does or does not contain a genuine opex share. That question was not answered by this measurement.

## Runtime seam (in-process)
| phase | timestamp (UTC) | `cam_clean` | commit |
|---|---|---|---|
| before_first_model_call | 2026-07-26T17:16:45Z | **true** | d679eec8525f… |
| after_last_model_call | 2026-07-26T17:37:50Z | **true** | d679eec8525f… |

Elapsed ~21 minutes. `cam/` clean before and after; commit unchanged across the run.

## Integrity after the run
All eleven package artifacts **and** the manifest are byte-unchanged in the run worktree
(`git status --porcelain` over those paths: empty). No `431_fatal_run_error.json` was written — no
terminal fatal occurred. Nothing was wired into `cam/`. No interpretation beyond §9.

## Git
Stage-2 outputs committed with `git add -f` explicit paths: `431_selection_measurement_sidecar.json`
(818,521 B), `431_runtime_seam_capture.json`, `431_selection_measurement.md`. Copies verified
byte-identical to the worktree originals. **NOT pushed.**
