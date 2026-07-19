# Step 431 Part B — Preregistration Package BUILD Instruction (Governed Evidence-Selection Measurement, real frozen panel) — two-stage authorization

**Author:** Chat instance
**Date:** 2026-07-19
**Type:** PREREGISTRATION PACKAGE BUILD INSTRUCTION for Claude Code (Part B of 2). **RATIFIED 2026-07-19 by Tzvi — authorizes Stage 1 build only, zero model calls. Live execution remains unauthorized pending separate sanction of the reviewed and hashed Stage-1 artifacts.** (Closing read of committed v3.1 `8755119` passed: series-index invariant machine-detectable, validation split computable, runtime seam capture in-process, selector-prompt build boundary correct, cand_06 pinned, disagreement framed as measured result.) The live run is authorized by a SEPARATE sanction after the built Stage-1 artifacts are reviewed and hashed. [v3.1 — v3 + four micro-edits: §0 section refs, series indices in the §8.1 trace schema, runtime seam capture + validation-artifact inventory, cand_06 offset pinned `[3619,3660)`; plus the disagreement-is-not-failure note.]
**Built against:** `build_log/431_partA_governed_selection_spec.md` (v5-final, RATIFIED 2026-07-19, committed `e702bf0`/`f6a362b`). Every mechanism traces to a Part A section; Part B invents no architecture — it builds a preregistration package so no configuration is improvised by the system being measured.
**Fixture ground truth:** `build_log/430_gate_b_cross_lease.md` §1/§2/§3/§5.
**Discipline:** read-only; imports, never modifies; no `cam/` file touched; pre-registered series, not massaged.

---

## 0. What this measures, and why it is pre-registered

Whether the **real frozen A/B/C panel**, governed by the Part A mechanism, produces judgments that are grounded, disagreement-preserving, and completeness-limited on the four forcing cases 430 exposed. Mechanism measurement over a **provisioned** candidate set — NOT a benchmark, NOT recall, NOT a test of whether the panel reached the answer we expect (Part A §3.1, §11).

**Status (accurate):** This document, once ratified, authorizes construction of the **preregistration package** (the Stage-1 artifacts, §1). **The measurement becomes preregistered only after those Stage-1 artifacts are reviewed, hashed, and SEPARATELY sanctioned for execution.** This instruction pins the deterministic knobs it can pin now (§3: `max_context_chars`, `attempt_ceiling`, versions, the envelope algorithm, the executable matching rules); the exact regex patterns, selector prompt, and output schema are produced as reviewable Stage-1 artifacts and hashed before any run. Ratifying this authorizes **BUILD ONLY, zero model calls** — see §1.

**Mechanism success (§9.1) is answer-key-independent.** If all three models reach the same honest-but-unexpected answer, the mechanism still succeeded provided the judgment was grounded and governed. Whether any parameter certifies — Atreca's included — is an OUTCOME OBSERVATION (§9.2), never pass/fail.

---

## 1. TWO-STAGE AUTHORIZATION (the hard gate)

**Stage 1 — ratifying THIS document authorizes BUILD ONLY, zero model calls.** Claude Code produces, and commits to `build_log/`, these artifacts:
- `431_selector_prompt.txt` — the exact selector prompt (§5), model-facing text, no fixture labels/hints.
- `431_output_schema.json` — the exact JSON output schema for a panelist judgment (§5).
- `431_requirement_profiles.json` — the versioned per-parameter requirement profiles (§4), declared independent of fixtures.
- `431_measurement_config.json` — every frozen deterministic value (§3): envelope algorithm + budget + allocation + `context_policy_version`, `value_token_detector` + version, attempt ceiling, `certification_policy_version`.
- `run_431_selection_measurement.py` — the harness (builds against the above; makes NO calls at build stage).
- `431_fixture_preflight.json` — the fixture-preflight result (§6): full source hashes, per-candidate quote resolution, unique-resolution check.
- `431_config_manifest.json` — the hash of each artifact above, so the reviewed config is the run config.

**Between stages:** these artifacts are adversarially reviewed (prompt for leakage; profiles for answer-key circularity; preflight for fixture integrity) and their hashes recorded.

**Stage 2 — a SEPARATE explicit sanction authorizes the live run**, and only of the exact hashed artifacts. **A prompt, schema, profile, config, or fixture edited after Stage-1 review voids the measurement** and requires re-review. No model call occurs under Stage-1 authorization.

---

## 2. Absolute scope constraints

- **Read-only. No `cam/` file created, modified, or deleted.** `git status --porcelain cam/` empty before staging and after.
- **Imports, never modifies.** Import `EVALUATOR_LINEUP_305`, the `_call_single_evaluator_305` call/fallback/provenance pattern, the canonical-source builder, the span resolver. No edit/subclass-override/monkeypatch. Not cleanly importable → stop and report; do not copy `cam/` logic into the harness.
- **Nothing wired.** No dependency map, `PARAMETER_TARGETS`, prompt, schema, resolver, normalization profile, or gate function edited. No live pipeline file consumes harness output.
- **`cam/core/` untouched** (Guardrail #5). **Gate B untouched** (Part A §2, §7).
- All new files under `build_log/`. Own `load_dotenv` (`C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env`), `PYTHONPATH` = CAM root.

---

## 3. Frozen deterministic configuration (`431_measurement_config.json` — pin ALL to concrete values at build)

`selector_config_hash` is meaningful only if it hashes concrete values. These are FROZEN by this instruction (not left for Claude Code to choose after seeing fixtures):

- **`context_policy_version`**: `"431_envelope_v1"`.
- **`max_context_chars`**: **`2000`** (frozen here; the config artifact records this exact integer and hashes it).
- **Envelope algorithm**: expand from candidate span → containing deterministic block (if the parser yields one) → adjacent complete blocks until the budget is reached; ELSE (no reliable block boundary) a fixed character window of `max_context_chars` centered on the candidate. Left/right allocation on the char-window fallback: **symmetric** (half each side, truncated at document bounds, truncation flagged per side). No expansion by parameter type, expected basis, or model request.
- **`attempt_ceiling`**: **`10`** per candidate (frozen here).
- **`value_token_detector` + version** (`"431_valuetok_v1"`): frozen generic regex patterns for token SHAPE only — a currency pattern (a currency sign followed by digits, optional decimals and thousands separators), a rate pattern (`per rentable square foot` / `per annum` / `per month` adjacent to a currency token), and a percentage pattern (digits followed by a percent sign). **Never a specific value; never a lease literal such as the Atlas or Atreca figures.** The exact patterns live in the config artifact and are reviewed at Stage 1.
- **`certification_policy_version`**: `"431_certpolicy_v1"`, with the deferred agreement threshold set to **unanimous-required** for this measurement (Part A §6.3 no-implicit-majority; a stricter-than-final threshold is safe and avoids preloading a majority default). This choice is recorded, not silently defaulted.

Config integrity: capture `prompt_hash`, `schema_hash`, `requirement_profiles_hash`, `config_hash` per run; single-valued across runs is the healthy result.

**Configuration truth (Part A §4):** identity-frozen, config-integrity-asserted, **NOT uniformly temperature-zero.** A and C transmit temperature 0; **B (gpt-5.5) runs at provider-default temperature 1** (415/416 exception). No deterministic-sampling claim; reproducibility = "identity-frozen panel over N=5," not "temp 0 → identical."

---

## 4. Requirement profiles (`431_requirement_profiles.json` — declared INDEPENDENT of fixtures; not inferred from labels or expected outcomes)

Code compares each returned classification against a DECLARED requirement, never one inferred from the fixture or the answer everyone expects (that would be an answer key in schema form). `431_requirement_profiles.json` (`"431_reqprofiles_v1"`) must **encode each rule as a deterministic, inspectable computation**, not describe it in prose — the Stage-1 reviewer inspects an executable rule, not an interpretation of "fit the concept":

- **`tenant_share`**: `basis_match = match iff returned charge_basis_components equals exactly {"operating_expenses"}` (a superset containing taxes/CAM, or any set lacking operating_expenses, is `mismatch`). `charge_scope`: recorded metadata only — **does NOT gate qualification in v1** (explicit, not silently either-way). `text_role_ok = (text_role == operative_term)`. `value_ok = (value_completeness == self_contained AND value_token_present)`. **`applicability_match`**: encoded as a deterministic predicate over the candidate's basis/scope/support fields (a candidate whose basis/scope/support fit the share concept — the exact field predicate is written in the profile JSON, e.g. `charge_basis_components is non-empty AND resolves AND support_ok`), independent of value.
- **`building_share`**: not seeded (§6); profile declared but unexercised.
- **`base_rent`**: `charge_basis_components` = `not_applicable` (Part A §4.1). `text_role_ok = (text_role == operative_term)`. `value_ok = (value_completeness == self_contained AND value_token_present)`. A `definition`/`cross_reference_only` candidate is `not_qualified` by the value_ok predicate.
- **`rent_adjustment_pct`**: `charge_basis_components` = `not_applicable`. `text_role_ok = (text_role == operative_term)` (a `narrative` role fails this predicate — the case-4 discriminator, encoded as a rule, not an expected outcome). `value_ok = (value_completeness == self_contained AND value_token_present)`.

Each predicate above is written in `431_requirement_profiles.json` as a computation the validator executes, not prose it interprets. These profiles are reviewed at Stage 1 for answer-key circularity: does any requirement encode the expected fixture outcome rather than the genuine commercial requirement? If a reviewer cannot tell the two apart, the profile is wrong.

---

## 5. The per-candidate judgment and the selector prompt (`431_selector_prompt.txt` + `431_output_schema.json`)

Each panelist, per (candidate + envelope) × parameter, returns the Part A §4.1 contract: `parameter_family_relevance` (`relevant`|`not_relevant`|`unclear`), `candidate_support_state` (`supports_mechanism`|`does_not_support_mechanism`|`insufficient_context`|`unclear`), `text_role`, `value_completeness`, parameter-type-specific `charge_basis_components`/`charge_scope` (closed enums + `other`/free-text), `candidate_citations[]`, `context_citations[]` (id + verbatim quote), **`field_support`** (citation ids per field), `reason`, `confidence`.

**Prompt-design invariants (Part A §4.2) — a leaked prompt voids the measurement and §7 would NOT catch it (the mechanism works perfectly on poisoned input). The model-facing payload contains ONLY:** opaque candidate ID, raw candidate text, the deterministic envelope text, the neutral parameter-family name, and the output schema. It contains **NONE** of: the desired basis, a template value, "find an operating-expense share," any statement of a correct answer, any forcing-case label, any fixture description, any expected role, any correctness hint.
- The prompt names the concept-family **neutrally** ("classify what charge basis, if any, this span establishes, and its contractual role").
- `charge_basis_components` read from cited text; uncited basis → `unclear`.
- `does_not_support_mechanism` and `insufficient_context` are first-class permitted answers (Part A §4.3); the panelist may not infer document-level absence from bounded context.
- Independent judgment: panelists never see each other's answers or other parameters' resolutions.
- Requirement comparison happens in CODE after classification (Part A §4.2 part 2), never in the prompt.

The exact prompt and schema are Stage-1 artifacts, adversarially read for leakage before Stage 2, and hashed.

**Deterministic checks (code — Part A §4.4):** span + every cited quote resolves verbatim to the hashed canonical source; `value_token_present` per the frozen §3 detector; reason present where required.

**Field-grounding (Part A §4.5):** a substantive field with **empty `field_support`** OR whose cited quote does not resolve → invalidated to `unclear`/`not_assessable` for that evaluator (not reduced confidence). Failed quote stays in audit trace, never enters `semantic_support_spans`.

---

## 6. Fixtures and preflight (`431_fixture_preflight.json` — verify ALL before any call)

### 6.1 The provisioned candidate matrix (human metadata; labels are NOT model-facing)
The `forcing case`/description column below is HUMAN-ONLY. It is excluded from the model payload (§5). Panelists receive opaque IDs (`cand_01`…`cand_07`) and raw text only.

| ID | Lease | Parameter | Candidate (human note) | Expected quote (verbatim, verify at preflight) |
|---|---|---|---|---|
| cand_01 | Atreca | `tenant_share` | opex share | `Tenant's Share of Operating Expenses of Building: 100%` |
| cand_02 | Atreca | `base_rent` | operative | `Base Rent:\n$3.75 per rentable square foot of the Premises per month, subject to adjustment pursuant to Section 4 hereof.` |
| cand_03 | Atreca | `rent_adjustment_pct` | operative | `Rent Adjustment Percentage: 3%` |
| cand_04 | Atlas | `tenant_share` | proportionate share | `"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area of the Demised Premises to the total rentable area of the Building.` |
| cand_05 | Atlas | `base_rent` | definition stub | `"Base Rent" shall mean the annual rent payable as set forth in Section 3.1.` |
| cand_06 | Atlas | `base_rent` | operative schedule | `[3619,3660)` — `$18.50 per rentable square foot per annum` (offset established by Claude Code; re-verify at preflight, §6.2) |
| cand_07 | Atlas | `rent_adjustment_pct` | approximation | `The above schedule reflects an annual escalation of approximately 3% per annum.` |

**7 candidates. Candidates are lease-specific — NOT multiplied across leases.**

**cand_04 completeness note (fact about provisioning, not a document claim):** No genuine operating-expense-share candidate is provisioned for Atlas `tenant_share`; the prior literal search (430 §3) found no "Operating Expenses" occurrence in the Atlas canonical text; candidate-universe completeness remains **not established** (§8.3). This is a fact about what was provisioned and searched, NOT a claim that the Atlas lease semantically lacks an operating-expense share. (What this implies for the *outcome* is an OUTCOME HYPOTHESIS, stated in §9.2 — not here, so fixture preparation carries no expected-answer note.)

**Deliberate scope (stated, not silent):** Atreca `building_share` (`[1997,2032)` "Building's Share of Project: 45.79%") is NOT seeded — no forcing case exercises it. Including it would test nothing the four cases require (Part A stop-test). Inclusion would be a scope change to ratify, not a silent omission.

### 6.2 Preflight (before ANY model call — a fixture failure here is pre-call, not an approximation license)
Record in `431_fixture_preflight.json`:
- **Full canonical source hash for each lease** (not truncated): Atlas `da9b5655c5cab382577f139a1884625d81f42b2610a146042018026dc28d2b71`; Atreca `7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b` (430 §1).
- **Canonicalization/normalization profile version**: `canonical_whitespace_v2` (430 §1) — confirmed for both.
- For **every** candidate (not only cand_06): the exact expected quote, and verification that its offset resolves to that quote against that hash. cand_01–05, 07 offsets from 430 (`[1942,1996)`,`[1695,1815)`,`[2097,2127)`,`[1738,1889)`,`[990,1065)`,`[4248,4327)`) must each re-resolve to the expected quote or the fixture fails.
- **cand_06 (now resolved; re-verify, do not re-discover):** offset `[3619,3660)`, full quote `$18.50 per rentable square foot per annum`, full-quote resolution count = 1 (UNIQUE); the bare phrase `per rentable square foot per annum` resolves 5 times (once per lease year), so uniqueness rests entirely on the `$18.50` prefix. Preflight **re-verifies** that `[3619,3660)` resolves to the full quote against the frozen Atlas hash. **If the pinned span fails to re-resolve against the frozen source hash, exclude cand_06 and report fixture drift** (case 3 reported stub-only, still a valid observation); run the other six.

---

## 7. The atomic unit, the series, and continuation (Part A §9)

**Atomic unit = candidate-panel attempt**: A/B/C judging ONE candidate under the frozen prompt/config. A run is a set of candidate-panel attempts.

**Series:** five **canonical** candidate-panel attempts PER ADMITTED candidate, ceiling `attempt_ceiling` (§3) per candidate. A degraded attempt on one candidate does NOT invalidate clean results for the others.
- All seven admitted → `7 × 5 × 3 = 105` primary calls.
- cand_06 excluded → `6 × 5 × 3 = 90` primary calls.
- Retry/fallback calls are additional and reported separately.

**Series alignment — the locked rule (N=5 is five independent panel decisions, NOT a fifteen-member panel):**
- Each candidate's canonical outputs are assigned **canonical series indices 1–5 in the order they were obtained.** (`raw_attempt_index` = wall-clock attempt number; `canonical_attempt_index` = index among that candidate's canonical attempts; `series_index` = 1..5, the aligned position. All three are recorded in the sidecar and `certification_trace`.)
- **Parameter certification for series index `k` uses ONLY the `k`th canonical panel result from each admitted candidate for that lease/parameter.** For Atlas `base_rent`, series-`k` certification consumes cand_05's series-`k` result and cand_06's series-`k` result — same index, never a cross-index pairing.
- **Evaluator votes merge ONLY within the same candidate AND the same series index. Votes are NEVER pooled across the five series**, and never pooled across candidates except as the certification policy combines same-series candidate results.
- If a required candidate lacks canonical index `k` (degraded out, ceiling hit), that **parameter-series result is incomplete and reported as a canonical-N shortfall** for that series — not silently filled from another series.

**"First pre-registered measurement series is the result."** (Replaces "first run is the result," which conflicts with N=5.) Retries occur ONLY under the degraded-attempt rule below; no re-run to obtain a cleaner number.

**Canonical / degraded / refusal — three distinct rules (Part A §9), do not collapse:**
1. **Panel identity from real provider/model/config metadata, NOT `is_fallback`.** Canonical requires the actual provider AND model AND **frozen configuration identity** (`config_hash` matching the reviewed config) — not provider/model alone; a run on the right models with drifted config is not canonical. A same-model self-retry (Role C grok-4.3 own-chain) at the frozen config stays canonical.
2. **Operational abstention / cross-family substitution EXCLUDED** from canonical (preserved as audit). A degraded A/B/Gemini attempt is not the frozen panel.
3. **Semantic refusal (`unclear`/`insufficient_context`/`not_assessable`) on a PRIMARY model STAYS canonical** — governed uncertainty is the behavior being measured.

Per candidate: continue attempts until 5 canonical or the ceiling; if the ceiling is hit first, report a per-candidate canonical-N shortfall (honest partial), never pad with degraded runs.

---

## 8. Output contract, the certification_trace, and the deterministic validator

### 8.1 Per-parameter `certification_trace` (makes §7-criteria machine-checkable, not author-asserted)
Emit, per parameter result, into the sidecar:
```
certification_trace:
  parameter, lease
  series_index                       # 1..5 — this trace certifies ONE parameter-series
  per_candidate: [ { candidate_id, raw_attempt_index, canonical_attempt_index, series_index,
                     relevance_ok, basis_match, text_role_ok,
                     value_ok, support_ok, applicability_match,
                     agreement_by_field, field_support_citation_ids,
                     candidate_qualification } ]
  semantic_support_span_ids
  completeness_provenance            # status: not_established (§9)
  prompt_hash, schema_hash, requirement_profiles_hash, config_hash
  final_certification_state
```
**Every candidate contributing to one parameter-series trace MUST carry the same `series_index`** (the trace's top-level `series_index` equals each `per_candidate.series_index`); a mismatch is a cross-series pooling defect and fails validation.
For any `satisfied` result, the trace MUST mechanically show ONE candidate_id supplied every required property (relevance_ok ∧ basis_match=match ∧ text_role_ok ∧ value_ok ∧ support_ok ∧ applicability_match=applicable, all on that same id). Cross-candidate satisfaction is thereby detectable by inspection of the trace, not by trust.

### 8.2 Validation is split into two evidence classes (so "independently recomputable" is true, not ceremonial)
Not every §9.1 criterion is a sidecar property. Some are repository/manifest/report facts. Validation is therefore two artifacts, and each criterion carries a pointer to the evidence that establishes it:

```
measurement_validation  →  431_validation.json      (computed from the sidecar)
  - citation grounding (every cited quote resolves; empty/failed grounding invalidated per §5)
  - same-candidate certification (one candidate_id supplied every property; no cross-candidate assembly)
  - disagreement handling (non-unanimous certification blocked; per-field agreement preserved)
  - completeness-limited negatives (no terminal unsatisfied_*; completeness not_established)
  - semantic-support-span behavior (materialized, not value-only; no borrowed property)

artifact_and_seam_validation  →  431_repository_seam_check.json  (computed from repo + manifest + report)
  - reviewed hashes equal run hashes (431_config_manifest.json vs the run's prompt/schema/profiles/config hashes)
  - pre/post `cam/` git status clean (git status --porcelain cam/ empty before and after)
  - no live import/consumption seam (no live pipeline file imports or consumes the harness output)
  - report completeness qualifiers present (every result cell carries the completeness status, §9.0)
  - report pass/fail values equal validator output (the §9.1 table was copied, not authored)
```

Each criterion in either artifact is a record:
```
{ criterion_id, status, evidence_artifact, evidence_pointer, details }
```
`evidence_artifact` names where the evidence lives (the sidecar, the manifest, the git status capture, the rendered report); `evidence_pointer` locates it within that artifact. **The report's §9.1 pass/fail table is COPIED FROM `431_validation.json` + `431_repository_seam_check.json`, never authored.** `run_431_selection_measurement.py` (or `validate_431.py`) computes the measurement class; a small seam-checker computes the artifact/seam class from the repo, manifest, and rendered report. Both are reviewable code.

**Runtime seam capture (reconstruction proves nothing).** The harness captures `git status --porcelain cam/` **inside the measurement process, immediately before the first model call and immediately after the final model call**, together with timestamps and the repository commit hash, into a runtime capture record (`431_runtime_seam_capture.json`). The seam checker CONSUMES these captured records; it **may not reconstruct the pre-run `cam/` state after execution** — a clean tree observed afterward is not evidence the tree was clean during the run.

### 8.3 `completeness_provenance` is set to `status: not_established` (Part A §6.4)
Part B cannot measure recall, so it cannot establish document completeness. **Therefore NO terminal `unsatisfied_*` may be emitted.** Every no-qualifying-candidate outcome is `review_needed_no_qualifying_candidate`. (Validator checks this.)

---

## 9. The report

Per evaluator × candidate: all §5 fields, `field_support`, cited reason, confidence, real provider/model/fallback metadata, per-quote source-verification, `value_token_present`.

### 9.0 Report-format rule (Part A §6.4 — no document-claim erasure)
Every parameter result cell carries the full certification state AND completeness status inline, e.g. `tenant_share (Atlas): review_needed_no_qualifying_candidate (completeness: not_established)`. **No cell or header may abbreviate a `review_needed_no_qualifying_candidate` to "unsatisfied," "failed," "0/5," or any token reading as "the document lacks this."** The completeness qualifier travels with the result everywhere. Hard requirement.

### 9.1 Mechanism success criteria (pass/fail — from `431_validation.json` + `431_repository_seam_check.json` per §8.2, answer-key-INDEPENDENT)
- No unverified span or unresolved/empty-grounded cited quote entered selection.
- No parameter certified by cross-candidate assembly (validator checks same-id property supply).
- No property borrowed from a semantic-support span to cure a deficient primary.
- Per-field disagreement preserved; non-unanimous certification blocked (no implicit majority).
- No terminal `unsatisfied_*` emitted (completeness not_established).
- Certified parameters (if any) carry materialized `semantic_support_spans`, not value-only.
- Every result carries the completeness qualifier per §9.0.
- Complete audit artifact reconstructs each decision (candidate vs context citations distinct; per-candidate comparisons visible; per-panelist reasons retained).
- No live pipeline file consumes the harness output.

### 9.2 Forcing-case outcome observations (reported, NEVER pass/fail)
Findings about the models; if all three make the same honest mistake the mechanism still succeeded (§9.1):
- **cand_04 outcome hypothesis (moved here from fixture prep):** 22.4% may be retained as share-family evidence, classified to whatever basis the panel grounds, and — if that basis mismatches the declared opex requirement (§4) and no other candidate qualifies — routed to `review_needed_no_qualifying_candidate` under not-established completeness (§8.3), never a terminal `unsatisfied_wrong_basis`. This is a hypothesis about the expected outcome, recorded for comparison against what actually happens; it is NOT an instruction and was NOT in the model payload.
- Observed `charge_basis_components` for cand_04 (22.4%); whether `basis_match=mismatch` vs the declared opex requirement.
- Whether cand_05 (stub) vs cand_06 (schedule) were distinguished by `value_completeness`; which, if any, qualified alone.
- Observed `text_role` for cand_07 ("approximately 3%") vs cand_03 (operative).
- Whether Atreca's cand_01/02/03 each produced a qualifying single candidate and certified — an OBSERVATION (can the mechanism certify a clean case), NOT a criterion. If not, a recorded finding, not a failure.
- Envelope sufficiency (§10): char distance from cand_04 to the §3.3 clause; whether the frozen envelope included it; resulting basis classification or `insufficient_context`.

**A high rate of `review_needed_disagreement` is an observed model-agreement result under the frozen panel, not a mechanism failure.** With Role B at provider-default temperature 1, unanimity across three models on six enum fields may be uncommon — and that is itself the finding. The mechanism fails only if disagreement is hidden, discarded, or improperly certified; preserving and routing it is the mechanism working as designed (Part A spine). Do not read a high review-needed rate as malfunction, and do not touch the frozen threshold mid-measurement to reduce it.

**Claim bound (verbatim in report):** reduction-to-practice of governed semantic selection on these four forcing cases only — not general accuracy, not correctness across leases, not elimination of correlated error, not readiness to wire, not closure of Supplement #26 §7's semantic-verifiability boundary.

---

## 10. Envelope sufficiency measurement (Part A §3.2, §8.2)
The frozen §3 envelope is built per candidate before any call. **Missing block boundaries do NOT halt — they trigger the frozen char-window fallback (§3), whose sufficiency is itself measured.**

cand_04's 22.4% span does not reveal its basis; Atlas §3.3 does (430 §5b): `Tenant shall pay to Landlord, as Additional Rent, Tenant's Proportionate Share of: (i) Real Estate Taxes ... and (ii) Common Area Maintenance charges ("CAM Charges")...`. **Measure, do not assume, whether the frozen envelope from cand_04 reaches §3.3.** Report char distance and inclusion. Outcome HYPOTHESES (not instructions, not expected answers): if it reaches, the panel *can* ground a basis from cited context; if it does not, an `insufficient_context` → `review_needed_incomplete_scope` result would be both a mechanism success (refused rather than guessed) and §8.2 evidence that bounded envelopes fail on distant cross-references. **Do NOT tune the budget to include §3.3.**

---

## 11. Stop seams
**Halts (report, do not work around):** `EVALUATOR_LINEUP_305`/`_call_single_evaluator_305` not cleanly importable; any fixture failing preflight (§6.2) other than cand_06's declared stub-only fallback; any temptation to edit prompt/schema/profile/config/fixtures after Stage-1 review (voids measurement).
**Does NOT halt (ratified fallbacks):** no reliable block boundary → frozen char-window envelope, measured; a single degraded attempt → excluded from canonical, continue to N=5-per-candidate under ceiling; a primary-model semantic refusal → kept canonical.

---

## 12. Files
Stage 1 (build): `431_selector_prompt.txt`, `431_output_schema.json`, `431_requirement_profiles.json`, `431_measurement_config.json`, `run_431_selection_measurement.py` (+ optional `validate_431.py` and seam-checker), `431_fixture_preflight.json`, `431_config_manifest.json`. Stage 2 (run): `431_selection_measurement_sidecar.json`, `431_runtime_seam_capture.json` (§8.2, captured in-process), `431_validation.json` (§8.2 measurement class), `431_repository_seam_check.json` (§8.2 artifact/seam class), `431_selection_measurement.md` (report). All under `build_log/`. No `cam/` file touched.

---

## 13. Authorization boundary (restated)
**RATIFIED 2026-07-19 — authorizes Stage 1 build only, zero model calls. Live execution remains unauthorized pending separate sanction of the reviewed and hashed Stage-1 artifacts.** Ratifying this document authorizes Claude Code to create and commit the Stage-1 preregistration-package artifacts listed in §1 and §12, and nothing else. It does NOT authorize: the live measurement; any API/model call; changes under `cam/`; wiring; Gate B changes; prompt or configuration edits after Stage-1 review; patent drafting. The ~105-call run remains separately gated behind adversarial review and explicit sanction of the hashed Stage-1 artifacts. Wiring stays blocked behind Gates A–D (423 §8) and the two 430 blockers.

---

*Part B v3.1 — RATIFIED 2026-07-19 by Tzvi (committed 8755119; stamp applied separately). Authorizes Stage 1 build only, zero model calls; live execution remains unauthorized pending separate sanction of the reviewed and hashed Stage-1 artifacts. Preregistration package build instruction for governed evidence-selection measurement. Five aligned parameter-series per lease/parameter (no cross-series pooling); validation split across sidecar and repo/manifest/report; canonical target 105 primary calls (90 if cand_06 excluded). Next review target: the Stage-1 artifact package, especially 431_selector_prompt.txt.*
