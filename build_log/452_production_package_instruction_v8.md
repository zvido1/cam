# Step 452 — Sanctioned Deterministic Post-Run Production Package

## PREREGISTRATION BUILD INSTRUCTION — **v8.2**

**Ratification status is NOT carried by this document.** It is recorded externally in `build_log/452_ratification_record.md`, which names the reviewed content hash and the reviewing party. A document that declares its own ratification status cannot be ratified and then committed without changing the bytes that were ratified — the same self-reference §3.2 avoids by keeping the manifest outside its own artifact set. This document's status at any moment is whatever the ratification record says of its current hash, and nothing in these bytes asserts it.

**Author:** Chat instance
**Date:** 2026-07-29 (current draft). Drafting arc began 2026-07-26.
**Lineage:** v1 (ten) → v2 (fourteen) → v3 (ten) → v4 (eight) → v5 (seven) → v6 (five) → v7 (six) → **v8**. Sixty addressed. Prior drafts retained in `build_log/`, each headed SUPERSEDED.
**v8.1 PATCH (buildability review, 2026-07-29):** three targeted repairs, no rewrite — the empty-domain boundary (§4.2.2), a producer for `execution_integrity` (§4.12), and atomic publication plus post-promotion rollback for the production invocation record (§4.17). Filename unchanged, so §3.1's self-reference is unaffected. (This trailing sentence was truncated by a Chat edit on 2026-08-15 while adding the v8.2 record, partially repaired in the same session, and fully restored after Claude Code compared the line against its intact form observed earlier in that session. Recorded because a silent repair is indistinguishable from a line that was never damaged.)
**v8.2 PATCH (Stage-1 producer binding, 2026-08-15):** ONE change — §3.1 gains `build_log/452_run_censuses.py` and `build_log/452_stage1b.py`. Both produce §3.1 products (the two censuses; the charge-scope determination and input-sufficiency record) and neither was itself bound, so the manifest would have hashed the products while nothing pinned the producing code. `452_stage1b.py` did not exist in the repository at all until 2026-08-15; its Stage-1B products were generated from a session scratchpad that hardcoded an absolute path, and it has since been materialized, made root-relative per the Step-444 rule, and confirmed to reproduce both determinations byte-identically. Found by Claude Code during the step-4 freeze check. This is the tenth instance of the producerless-artifact defect class and the first inside Step 452 itself: the per-field census asks whether products have producers and never asked whether producers exist. Enforced going forward by rule R21 in `452_deterministic_rules.json` (clause 1: every expected_producer must resolve to a repository file or be explicitly exempted as an L1/P4-era producer bound by the 431 manifest; clause 2: every non-exempt producer file must itself be a §3.1 artifact), with a closed 49-entry exemption list held in the rules file rather than compiled into code. Filename unchanged, so §3.1's self-reference is unaffected. Supersedes ratification of `002b3afa…`; requires re-ratification of the new hash.
**v8.3 PATCH (provenance recoverability and non-vacuous gates, 2026-08-15):** THREE changes, all found by Claude Code. (1) §3.1 gains `build_log/452_key_isolation_record.md`, 37 paths → 38 — it is the evidence base for §8.2, the one precondition nothing else can verify, and evidence for an unfakeable requirement cannot itself be mutable after sanction. (2) §7.1 gains a non-vacuous `input_hashes` requirement: `452_input_sufficiency.json` declared none and so passed Stage-2 revalidation trivially. (3) §7.0 gains checkpoint commits at 0a, 2a and 3c, because until an artifact is committed it has no recoverable prior state and "the edit was confined to these lines" is unprovable; this also makes step 4's freeze enforceable, since gitignored `build_log/` leaves the cleanliness check blind to §3.1 edits. Supersedes ratification of `b9343bd9…`; requires re-ratification of the new hash.
**Type:** PREREGISTRATION BUILD INSTRUCTION for Claude Code. Three-stage authorization.
**Built on:** `build_log/431_partA_governed_selection_spec.md` (v5, RATIFIED, `e702bf0`) and `build_log/431_partB_measurement_instruction.md` (v3.3, RATIFIED, `38785e7`), under §5.0.

**SCOPE STATEMENT.** This package **implements the previously specified Part-A / Part-B products** and **adds explicitly identified post-run governance, ambiguity-handling and provenance mechanisms adopted before Stage-2 execution**, each flagged in place in its own section. **They were adopted at different points across the drafting arc of 2026-07-26 to 2026-07-29, not on a single day.** A prior blanket date of 2026-07-26 was false and is withdrawn: the envelope-local ambiguity ruling was decided 2026-07-26 and is corroborated by `452_ambiguity_ruling.md`, but the precedence rules, the replay-integrity halt, the Pass-A fidelity criterion, the status split and its boundary rule, transactional publication, and the provenance layer were each adopted in later drafts. Per-mechanism adoption dates are NOT established in this document; if the patent record requires them, they must be derived from the per-draft file timestamps and recorded separately.

**Provider calls:** ZERO across both sanctioned script invocations, proven by §4.14.

---

## 0. Why this exists

P4 (`d679eec8`, token `ef1a7af7…`, tag `stage2-sanction-431-ef1a7af7`) executed Step 447 correctly and produced an immutable sidecar, a runtime seam capture, and a thin report of terminal states.

Step 451's census found P4 did not produce most of what Part B specified: seven products with no producer, one field computed then discarded, two §9.1 criteria naming a subject never materialized, one certification conjunction unsatisfiable for two of four parameter types (originating in **Part A §4.1 + §6.3**), one Part A §11.1 clause dropped in transit.

Every substantive finding first reported after the run came from ad hoc probes bound by no execution-identity construction.

**This package does not re-run the measurement, does not repair P4, and does not retroactively make its outputs products of P4.**

---

## 1. Three layers

| Layer | What it is | Identity binding |
|---|---|---|
| **L1 — P4 / Step 447** | Sanctioned generation of panel judgments, terminal states, seam capture | Tag `stage2-sanction-431-ef1a7af7` |
| **L2 — Ad hoc probes (447–451)** | Exploratory analysis over L1 artifacts | **None.** Comparison inputs only (§6.9). |
| **L3 — This package** | Authoritative deterministic production | P452 commit, new token, message, signed tag |

Every post-run substantive finding first reported through Step 451 was **outside the P4 sanctioned-output set** and is **L2 until independently reproduced by L3**.

**Token-header rule:** every **Stage-2** output carries `identity_layer: "L3"` and the package token. Stage-1 artifacts are inputs to the token's derivation and cannot contain it.

---

## 2. Three-stage authorization

**Stage 1A — BUILD.** Production script, tests, schemas, rules, inventory, gate records. **No read of any L1 run artifact.** Synthetic fixtures embedded as literals.

**Stage 1B — STRUCTURAL PREFLIGHT.** Reads frozen L1 inputs **for structure only** and produces two artifacts in a fixed internal order (§7.0). **Forbidden, and a halt:** ambiguity counts; identifying which `satisfied` states would unseat; any Pass B computation; any certification count, outcome table, or criterion status.

**Stage 1B produces artifacts. It never edits a Stage-1A artifact.**

**Stage 2 — SANCTIONED PRODUCTION.** The two-pass computation, detached at P452, after signature.

---

## 3. Closed artifact sets — exact repository-relative paths

### 3.1 `EXPECTED_PACKAGE_ARTIFACTS`
```
build_log/431_selection_measurement_sidecar.json
build_log/431_runtime_seam_capture.json
build_log/431_selection_measurement.md
build_log/431_measurement_config.json
build_log/431_requirement_profiles.json
build_log/431_output_schema.json
build_log/431_fixture_preflight.json
build_log/431_config_manifest.json
05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt
05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt
build_log/431_partA_governed_selection_spec.md
build_log/431_partB_measurement_instruction.md
build_log/452_production_package_instruction_v8.md
build_log/452_ratification_record.md
build_log/452_production_script.py
build_log/452_production_tests.py
build_log/452_run_censuses.py
build_log/452_stage1b.py
build_log/452_output_schema.json
build_log/452_deterministic_rules.json
build_log/452_required_product_inventory.json
build_log/452_ambiguity_ruling.md
build_log/452_stage1_test_results.json
build_log/452_producer_consumer_census.json
build_log/452_predicate_reachability_census.json
build_log/452_charge_scope_applicability_determination.json
build_log/452_input_sufficiency.json
build_log/452_key_isolation_record.md
build_log/431_postrun_partial_validation.json
build_log/447_code_status.md
build_log/448_code_status.md
build_log/449_code_status.md
build_log/450_code_status.md
build_log/451_code_status.md
build_log/448_input_hashes.md
build_log/452_sanction_allowed_signers
build_log/452_sanction_key.pub
build_log/452_sanction_policy.json
```

### 3.2 The manifest sits OUTSIDE the token-input set
```
MANIFEST_GITPATH = "build_log/452_config_manifest.json"
```
A manifest carrying the derived token cannot be an input to that token. Runtime requires: manifest from `HEAD:<MANIFEST_GITPATH>`; worktree copy byte-identical; manifest declaring exactly `EXPECTED_PACKAGE_ARTIFACTS`; every recorded hash equal to the recomputed HEAD blob; four-way token equality.

### 3.3 Stage-2 outputs — THREE atomically published sets

**Set A — `build_log/452_stage2_results/`, exactly:**
```
source_records.json          pass_a_results.json        pass_a_fidelity.json
grounding_enforcement.json   pass_b_results.json        pass_comparison.json
certified_parameter_evidence.json   envelope_sufficiency.json   observations.json
validation.json              repository_seam_check.json report.md
post_report_validation.json  final_mechanism_disposition.json
l2_comparison.json           contract_reconciliation.md
zero_provider_call_check.json  output_manifest.json
```
**Set A′ — `build_log/452_production_invocation_record.json`** (§4.17), single file, written after Set A is promoted, while the production guard is still active.
**Set B — `build_log/452_execution_record_final.md`** (§4.12), separate invocation.

**Non-authoritative failure product — `build_log/452_stage2_failure_record.json`** (§4.15), emitted only on failure, carrying no L3 authority, excluded from every success artifact and claim.

`build_log/` is gitignored, so `git status --porcelain --untracked-files=all` stays clean even if the script emits an unexpected file. **Whole-tree cleanliness and output closure are different invariants.**

### 3.4 `cam/` dependencies
Bound **at P452** by reusing the whole-repository cleanliness and detached-commit construction proven during P4 hardening. The method is reused; the binding is new.

---

## 4. Products

### 4.0 Inventory — typed consumers
```json
{ "product_id": "...", "source_document": "...", "source_section": "...",
  "verbatim_requirement": "...", "required_fields": ["..."],
  "expected_producer": "...", "expected_output_path": "...",
  "temporal_layer": "stage_1 | stage_1b | stage_2_output | post_production_provenance | post_p452_provenance",
  "consumers": [ { "consumer_type": "runtime_gate | validator | report | signer | construction_audit | future_citation",
                   "consumer": "...", "required": true } ] }
```
The census proves every product has its **declared applicable consumer**. A product with no consumer of any type still halts. **Seeded by the Chat instance, falsifiable not authoritative**; the sweep covers **Part A + Part B + Step 452 itself**, and any product found and absent is a **halt**.

### 4.0.1 Frozen identity formulas
All ids: `SHA-256 over the UTF-8 encoding of a canonical JSON array` of the listed components, hex, truncated to 16, prefixed. Canonical JSON: `json.dumps(components, ensure_ascii=False, separators=(",", ":"))`.
```
judgment_id      "J-"   [lease_id, parameter, candidate_id, series_index, role]
citation_occ_id  "CO-"  [judgment_id, citation_class, citation_id]
envelope_id      "EV-"  [lease_id, candidate_id, context_start_char, context_end_char]
support_span_id  "SS-"  [source_document_hash, start_char, end_char]
failed_trace_id  "FT-"  [lease_id, parameter, candidate_id, series_index, role,
                         field, citation_class, citation_id, sha256_of_quote]
missing_trace_id "MT-"  [lease_id, parameter, candidate_id, series_index, role, field]
```

### 4.1 Storage shape
`source_records.json` written ONCE (candidates, judgments, citations, provenance, envelopes, frozen IDs, `value_token_present`, L1 provenance per §4.2.1); `pass_a_results.json` as-computed; `pass_b_results.json` the full recomputation of §4.4.6; `pass_comparison.json` deltas.

### 4.2 Validation outputs

#### 4.2.1 `pass_a_l1_fidelity` — Pass A must be PROVEN faithful
Every source record carries `l1_artifact`, `l1_json_pointer`, `l1_value_canonical_json_sha256`. `pass_a_fidelity.json` verifies: every canonical L1 judgment represented exactly once; every raw semantic field, citation id, quote, and provider/model/fallback field unchanged; every candidate, parameter, series and role mapping unchanged; every P4 merged result and terminal state unchanged; all thirty series and all canonical and degraded attempts reconciled; no L1 record omitted or invented. **Pass A may add identity and provenance wrappers. It may not reinterpret the payload inside them.** Failure halts immediately.

#### 4.2.2 GENERAL RULE — any criterion with a possibly-empty domain carries TWO statuses

v7 introduced `pass_vacuous` as a third value and told the aggregator never to collapse it into `pass`, **without defining what the aggregator does with it.** With every other criterion passing and #6 vacuous, the Pass-B disposition was undefined. Teaching a generic aggregator a special fourth truth value invented for one criterion is the wrong shape. The right shape separates two different questions:

```
<criterion>_logical_status   : pass | fail | not_established   # consumed by the §9.1 conjunction
<criterion>_exercise_status  : exercised | vacuous              # consumed by RTP and patent claims
```

**THE BOUNDARY RULE, which prevents the whole construction from becoming a laundering device:**

> **`vacuous` is available only when the criterion's own antecedent permits an empty domain. Failure to produce a required subject is not converted into a vacuous pass.**

An empty domain arises for two fundamentally different reasons, and v8 conflated them: the criterion expressly allows there to be no subjects, or the package failed to produce a subject that was required. Only the first is `vacuous`. `logical_status` therefore admits `not_established`, for the case where the subject needed to assess the criterion is blocked or absent.

**This applies to every criterion whose subject can be empty, not to #6 alone.** Frozen treatment for the two named instances:

| Criterion | Situation | logical_status | exercise_status |
|---|---|---|---|
| #6 Pass A | Fourteen certifications, required packages absent | `fail` | `exercised` |
| #6 Pass B | Zero post-enforcement certifications | `pass` | `vacuous` |
| #6 Pass B | Certifications exist, every package complete | `pass` | `exercised` |
| #6 Pass B | A certification exists without a complete package | `fail` | `exercised` |
| #3 Pass A package layer | P4 never materialized a package subject | `not_established` | `vacuous` |
| #3 Pass B | Complete packages exist, none carries support spans | `pass` | `vacuous` |
| #3 Pass B | One or more support-bearing complete packages exist | `pass` or `fail` | `exercised` |
| #3 Pass B | A package needed for assessment is blocked or absent | `not_established` | `vacuous` |

**#6 Pass A is `exercised`, not `vacuous`** — its antecedent was met by fourteen certifications and the required subject was absent. That is the boundary rule operating.

**The predicate-reachability census (§7.3) must identify every criterion with a possibly-empty domain, confirm each carries both statuses, and confirm each has a frozen treatment table.** Two named instances are not asserted to be the complete list.

#### 4.2.3 Criterion #6 rules
```
Pass A #6: logical fail — P4 produced satisfied states without certified packages.

Pass B #6: logical pass only if
    every post-enforcement satisfied state has materialization_status == complete
    AND every context citation actually relied upon for the basis/scope/role
    subset is represented by a verified semantic_support_span.
```
**An empty `semantic_support_spans[]` may pass only when the source judgment shows no context citation was relied upon for those fields.** Empty because nothing was materialized is failure; empty because nothing needed materializing is legitimate. Subset membership per §5.0.3.

#### 4.2.4 Exercise fields — granular enough for the supplement

A complete package can legitimately carry `semantic_support_spans: []` when the classification relied entirely on candidate citations. In that case package construction was exercised, **support-span materialization was not**, and runtime anti-borrowing against a support-bearing package was not.

```
pass_b_satisfied_count
pass_b_complete_package_count
materialization_function_exercised                    # bool
materialization_exercised_by_pass                     # "A" | "B" | "A_and_B" | null
post_enforcement_certified_package_exercised          # bool
support_span_materialization_exercised                # bool
support_span_materialization_exercised_by_pass        # "A" | "B" | "A_and_B" | null
support_bearing_complete_package_count_by_pass        # { "A": int, "B": int }
anti_borrowing_dataflow_verified                      # bool — static derivation-path property
anti_borrowing_runtime_exercised                      # bool — required an actual support-bearing package
anti_borrowing_runtime_exercised_by_pass              # "A" | "B" | "A_and_B" | null
ambiguous_support_invalidation_count
empty_support_invalidation_count
```

**`materialization_exercised_by_pass` is load-bearing for the supplement.** Pass A materialization runs over judgments that were never grounding-enforced, so a Pass-A-only exercise demonstrates that the deterministic construction works — **not** that governance produced the package.

**The invalidation counts serve the same purpose one layer down.** Synthetic tests (§7.5) establish the ambiguity and empty-support branches exist; these counts establish whether the frozen live record exercised them.

#### 4.2.5 Remaining criteria
**Tenth check:** Part A §11.1 #5's dropped clause — no candidate with `candidate_support_state == insufficient_context` certified. The self-referential seam criterion is handled by §4.10 and §4.16.

### 4.3 §7.1 certified-package materialization

#### 4.3.1 Resolution — two windows
```python
def _find_normalized_matches(
    canonical_text: str, quote: str,
    normalization_profile: str = NORMALIZATION_PROFILE_V1,
) -> List[Tuple[int, int]]:
    """Locate every position in canonical_text that matches `quote`.
    ... Returns (start_char, end_char) tuples in source order.
```
`cam/adapters/lease_review/lease_evidence_spans.py`. Part B §2 already authorizes importing `_call_single_evaluator_305`.

**`resolve_span` MUST NOT be used** — document-wide search returns `AMBIGUOUS` whenever a quote occurs more than once anywhere in the lease, including when unique in the window the panelist saw.
```
candidate citation  → ONLY within [candidate_start_char, candidate_end_char)
context citation    → ONLY within [context_start_char, context_end_char)
```
A **tighter window, not a second resolver.** Import the matcher and `EvidenceSpan` machinery; match against the **full** canonical source; filter to the window; apply 0/1/2+; re-check `is_valid_invariant` before VERIFIED, failing closed. Do not build a `CanonicalSource` over a window slice. Do not reimplement matching. `resolve_span`'s anchor path is **inert**: P4 records neither `source_anchor` nor `section_ref`.

#### 4.3.2 Primary candidate span
`evidence_span_id` = original `cand_01`…`cand_07`; `source_document_hash` = frozen preflight hash; `canonical_text_hash` = freshly constructed; offsets = pinned preflight offsets; **`span_text` = the exact canonical slice**; `span_text_hash` = imported `_span_text_hash(span_text)`; `normalization_profile` required `canonical_whitespace_v2`; `verification_status` = VERIFIED after all checks; `section_ref`/`source_anchor` = preflight value or `None`.

**The two hashes are required equal, and the constructor proves it:**
```python
    canonical_digest = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
    return CanonicalSource(
        source_document_hash=canonical_digest,
        ...
        canonical_text_hash=canonical_digest,
```

**Asymmetry with support spans, stated rather than harmonized:** the primary is **offset-pinned**, so `span_text` is the canonical slice and the preflight quote is a *verification target*. A support span is **quote-proposed**, so `span_text` is the panelist's verbatim quote, matching `resolve_span`'s own `span_text=quote`.

**Uniqueness:** verify the pinned slice; **do not rediscover**. Document-wide uniqueness only where the preflight required it — **cand_06 alone**. Any pin, hash or profile mismatch **halts the package** (§5.0.2).

#### 4.3.3–4.3.5 Support spans, failed traces, missing traces
Support spans constructed **only** on exactly one window-local match, deduplicated on `(source_document_hash, start_char, end_char)` with `citation_occ_ids`, `supports_fields` and `supporting_panelists` unioned, ordered by `start_char`, `end_char`, id. `failed_support_trace` (UNVERIFIED or AMBIGUOUS) and `missing_support_trace` (empty `field_support`, per Part A §4.5) carry their own ids and **no `EvidenceSpan` is constructed**. Schema-fixed `not_applicable` fields are exempt from the missing-support rule (§5.0.3).

#### 4.3.6 Selection rule
Context citation ids in `field_support` under the **basis, scope and role** fields, scope membership per §5.0.3.

#### 4.3.7 Anti-borrowing — a DATAFLOW test
Borrowing is a derivation path, not the presence of digits. Verify through the actual computation: `value_token_present` from **primary-candidate text only**; `value_completeness` from **the primary's panel judgment only**; `value_ok` consuming **only** those two; **no support-span field an input to any of them.** The static property is `anti_borrowing_dataflow_verified`; exercising it on a package that actually contains support spans is `anti_borrowing_runtime_exercised` (§4.2.4).

#### 4.3.8 `materialization_status`
Attempted for **every** Pass-A `satisfied` state; blocked records **emitted, not skipped**. `complete` when the primary verifies and every §4.3.6 citation resolves uniquely in its window; `blocked` when any §4.3.6 citation is UNVERIFIED, window-ambiguous or missing. A primary failing verification halts the package (§5.0.2). A failed or missing citation **outside** the §4.3.6 subset is recorded in enforcement and may unseat Pass B but does not block materialization.

### 4.4 Grounding enforcement and the Pass-B recomputation contract
```
0 matches in window   → UNVERIFIED → invalidated (failed_support_trace)
1 match  in window    → VERIFIED   → EvidenceSpan
2+ matches in window  → AMBIGUOUS  → invalidated (failed_support_trace)
empty field_support   → EMPTY      → invalidated (missing_support_trace)
```
**Enforced field value:** `unclear`, all six substantive fields. `not_assessable` is **not** a field value — per Part A §5.2 it belongs to `agreement_by_field`.

1. `unclear` is the **visible enforced value**, retained for audit.
2. The invalidated vote is **omitted from substantive aggregation** — not counted at all.
3. **A field with any role invalidated cannot be `unanimous`.** Part A §4.5: "a field cannot remain `unanimous` (§5.2) on the strength of a quote that does not exist in the source, or on no quote at all." Two survivors are **not** "2/2 unanimous"; that manufactures unanimity by deletion, which §6.3 forbids.
4. `agreement_by_field` becomes **`not_assessable`**.
5. Under the frozen unanimous-required threshold, `not_assessable` **cannot support `satisfied`**.

Confidence is **not** reset or capped — §4.5 is explicit this is invalidation, "not a confidence haircut."

**Parameter-aware `basis_ok`** (authority §5.0.1):
```
basis_ok = (basis_match == "match")        where the profile declares a basis-bearing parameter
basis_ok = (basis field == "not_applicable" AND the profile declares it so)
                                           for base_rent and rent_adjustment_pct
```

#### 4.4.6 Pass-B recomputation — the whole chain, nothing copied
```
1  effective per-evaluator fields
2  grounded relevance and cited-union retention   (Part A §5.1)
3  per-candidate semantic merge                   (Part A §5.2)
4  agreement_by_field
5  parameter_candidate_comparison                 (Part A §6.1)
6  applicability_match                            (Part A §6.2)
7  certification_trace                            (Part B §8.1)
8  terminal certification state                   (Part A §6.3)
```
**Step 2 is not optional.** Part A §5.1: "A candidate enters the parameter's `retained_evidence` if **≥1** panelist marks `parameter_family_relevance: relevant` **with a grounded, source-resolving reason.**" Retention and certification have **different consumers** by design, so an invalidated relevance judgment can change the retained-evidence ledger as well as the terminal label.

### 4.5–4.9 Report, observations, envelope sufficiency, recoverable fields
`report.md` with §9.0's inline completeness qualifier as a hard requirement, no cell abbreviating `review_needed_no_qualifying_candidate`. `observations.json` covering all six §9.2 classes including cand_04's `none`/`unclear` abstention-versus-negation pattern stated explicitly, Atreca control variance as replicate variance, and the `reasoning_exhaustion` naming note. `envelope_sufficiency.json` with establishing-clause map, distance, inclusion and five citation categories frozen and **no sufficiency threshold declared**. `value_token_present` at `source_records.json → candidates[].value_token_present`, referenced by everything and recomputed by nothing.

### 4.10 Complete topological production order
```
 0  install network guard (standard-library-only entrypoint, §4.14)
 1  source_records.json          (frozen IDs, value_token_present, L1 provenance)
 2  pass_a_results.json
 3  pass_a_fidelity.json         (§4.2.1 — HALTS immediately on failure)
 4  grounding_enforcement.json
 5  pass_b_results.json          (full recomputation, §4.4.6)
 6  pass_comparison.json
 7  certified_parameter_evidence.json      (both passes; consumes 4)
 8  envelope_sufficiency.json
 9  observations.json
10  validation.json              (measurement class; consumes 7)
11  repository_seam_check.json   (NON-report criteria only)
12  report.md                    (consumes 1–11)
13  post_report_validation.json
14  final_mechanism_disposition.json       (§4.16)
15  l2_comparison.json           (isolated; §6.9)
16  contract_reconciliation.md   (Part A/B promised products ONLY, §4.13)
17  zero_provider_call_check.json (production computation up to the prepublication boundary)
18  output_manifest.json         (hashes 1–17; excludes itself)
19  verify staged directory closure
20  ONE directory rename: staging → build_log/452_stage2_results/   (§4.15)
21  452_production_invocation_record.json  (§4.17 — Set A′, guard still active)
—   452_execution_record_final.md          (separate invocation, §4.12)
```

### 4.11 `output_manifest.json`
Package commit; token; tag name and object id; input hashes before and after; **path and SHA-256 for every Set-A product except itself**, with the self-exclusion and its reason recorded; script version; timestamps; detached HEAD; whole-tree cleanliness before and after; exit status.

**It does not carry the staged-closure result.** v7 required it to, while the closure check ran two steps in its future. Closure and completion live in §4.17, which is produced after both.

### 4.12 `452_execution_record_final.md`
**Producer:** `python build_log/452_production_script.py finalize-record`
**Consumer:** construction audit; future citation of any L3 result.
**Contents:** SHA-256 of `output_manifest.json`, `zero_provider_call_check.json`, and `452_production_invocation_record.json`; P452 commit, token, signed-tag object id; **output hashes designated for the results commit** (the record precedes the commit); **the post-report aggregate from `final_mechanism_disposition.json`, not the step-10 partial**; the §4.2.4 exercise fields; all four gate records' aggregates; and its **own** `finalize_invocation_zero_call` section (§4.14).

**Before writing Set B it must:** re-run the P452 identity/tag/token gate; install the network guard before project imports; verify every Set-A file against `output_manifest.json` **and** `452_production_invocation_record.json`; verify no Set-A file changed after production; enforce Set-B closure. **Published transactionally: temporary file plus one atomic rename.** One file can have the atomicity seventeen could not.

**`execution_integrity_status: pass | fail`** — computed here, the producer §4.16's second axis previously lacked. `pass` only when ALL of the following hold:

1. P452 commit, tag, token, principal, fingerprint and message binding all verify;
2. all four Stage-1 gate records exist, passed, and their declared input hashes match HEAD;
3. L1 inputs hash identically before and after production;
4. `pass_a_l1_fidelity` passed;
5. whole-repository cleanliness held before and after production;
6. Set-A closure passed;
7. `452_production_invocation_record.json` reports successful completion;
8. the production-invocation zero-call evidence passed;
9. the finalize-invocation zero-call evidence passed;
10. every Set-A hash verifies against both the manifest and the invocation record;
11. Set-B closure passed.

**If any term fails, no successful final execution record is emitted.** The failure path emits only `452_stage2_failure_record.json` (§4.15), which carries no L3 authority.

**One results commit** containing `452_stage2_results/`, `452_production_invocation_record.json`, and this record. `build_log/` is gitignored, so `git add -f` with explicit paths.

### 4.13 Contract reconciliation — Part A and Part B products ONLY

v7 computed this against the **full** inventory, which includes `452_execution_record_final.md`, produced later by a separate invocation. At step 16 that product is neither produced nor absent, so the reconciliation could not truthfully classify it.

**`contract_reconciliation.md` covers only the products Part A and Part B promised**, each mapped to produced-by-P4 / produced-by-this-package / genuinely-absent. That restores it to the §12 contract comparison it was meant to be. Step-452-native lifecycle products are covered by the inventory, the producer-consumer census, output closure, and the final execution record.

### 4.14 Zero-call proof — two attestations
**Common to both invocations:** guard installed before any non-standard-library or project module is imported, as the first executable statement of a standard-library-only entrypoint; AST and import scan over the **transitive project-import closure** with an explicit allowlist; outbound socket connection attempts blocked and counted; **an exact subprocess-command allowlist containing only non-network Git operations** (a Python socket guard does not govern child processes); a provider-call counter either hooked to a named call site or omitted.

**Production invocation → `zero_provider_call_check.json`** at step 17, recording the computation up to the prepublication boundary. The guard **remains active through steps 18–21**; the final outbound count and allowlist result for the whole invocation are recorded in §4.17, not here.

**Finalize invocation → its own section inside `452_execution_record_final.md`:**
```
finalize_invocation_zero_call:
  guard_installed_before_project_imports
  outbound_attempt_count
  subprocess_commands[]
  allowlist_result
  status
```
**The second invocation's proof cannot be borrowed from the first.**

**Claim narrowed to: zero provider calls across both sanctioned script invocations.** The subsequent `git add -f` and results commit are provenance actions outside those two guarded Python invocations, restricted to local Git with no push, and **not** proved by the socket guard.

### 4.15 Transactional publication, and the failure record

Seventeen flat files cannot be atomically promoted; `os.replace()` is atomic per path, not collectively.
```
staging   build_log/.452_stage2_results.staging-<nonce>/
target    build_log/452_stage2_results/
```
Produce and validate every Set-A file **inside staging**; verify exact directory closure; verify the target does not already exist unless an explicitly sanctioned replacement rule applies; **rename staging to target in one same-filesystem operation.**

**On failure — `build_log/452_stage2_failure_record.json`.** v7 said the package could "optionally emit a clearly named failure record," which was neither clearly named nor given a producer, schema, consumer, path, or membership in any closed set: a producerless product introduced by the package built to eliminate producerless products.

```
producer      452_production_script.py, failure path
schema        { failure_stage, failure_reason, staged_paths_present[],
                staged_paths_missing[], inputs_verified, guard_status,
                outbound_attempt_count, staging_directory_disposition,
                l3_authority: false }
publication   temporary file plus one atomic rename
consumer      construction audit
authority     NONE. Excluded from every success artifact, every claim, and
              every set in §3.3. Never cited as an L3 result.
```
Staging is deleted or quarantined; **no final-named L3 product is left behind.**

### 4.16 `final_mechanism_disposition.json` — mechanism only
Consumes `validation.json` + `repository_seam_check.json` + `post_report_validation.json`.
```
any required criterion logical_status == fail   → fail
no fail, any not_established                    → not_established
all logical_status == pass                      → pass
```
The conjunction consumes **`logical_status` only**. Every `exercise_status` is carried alongside, reported, and consumed by RTP and patent claims — never by the conjunction. A split criterion contributes its **weakest** component.

**Two axes, kept apart:**
```
mechanism_disposition   — this artifact
execution_integrity     — computed by `finalize-record` as `execution_integrity_status`
                          inside `452_execution_record_final.md` (§4.12)
```
A semantic pass must not silently imply that publication and provenance also passed. **v8 named `execution_integrity` as an axis and told the final record to cite it while nothing computed it** — the same defect class this package exists to eliminate, committed inside the package. No new artifact is needed; §4.12 gives it a producer.

### 4.17 `452_production_invocation_record.json` — production completion provenance

v7's manifest was required to carry a closure result produced two steps in its future, and `finalize-record` was told to verify the zero-call artifact against a manifest that deliberately excluded it. Files remain linear in time.

Produced **after** the results directory is promoted, **while the production guard is still active**:
```
final_target_directory_closure
output_manifest_sha256
zero_provider_call_check_sha256
final_outbound_attempt_count
subprocess_allowlist_result
completion_status
```
This binds the manifest, the zero-call result, and completed publication into one receipt. `finalize-record` verifies all three (§4.12).

**Atomic publication and post-promotion rollback.** v8 called Set A′ atomically published without giving it an atomic-publication instruction, and left a reachable state in which the results directory is promoted but the invocation record fails to appear — a final-named L3 directory with no completion record, contradicting §4.15's rule that no final-named L3 product is left behind.

This record is written to a temporary file and **atomically renamed** into place. If its production or rename fails **after** Set A was promoted:

1. atomically rename `build_log/452_stage2_results/` to a clearly non-authoritative quarantine path, or remove it;
2. confirm the authoritative target path no longer exists;
3. emit `452_stage2_failure_record.json`, recording the quarantine disposition;
4. halt.

**Production success requires BOTH `build_log/452_stage2_results/` and `build_log/452_production_invocation_record.json` to exist as one completed unit. Neither is authoritative without the other.** This is a consumption rule as well as a production rule: `finalize-record`, the construction audit, and any future citation of an L3 result must verify both are present before treating either as authoritative.

---

## 5. `452_deterministic_rules.json` — frozen at Stage 1A

### 5.0.1 Part A / Part B precedence
Part A v5 §4.1 names `charge_basis_components`; Part B v3.3 replaces it schema-wide with `value_applies_to_charge_basis_components`.

> **For semantic-field identity and all basis comparisons, Part B v3.3's relation-bearing amendment supersedes Part A v5's `charge_basis_components` token. Part A's field-grounding, merge, disagreement and certification semantics otherwise remain controlling.**

**Extended to the certification conjunction.** The unsatisfiable predicate originates in **Part A §6.3** — "`satisfied` requires ONE SINGLE candidate for which relevance_ok AND basis_match=match AND text_role_ok AND value_ok AND support_ok all hold together" — while §4.1 declares the basis dimension `not_applicable` for `base_rent` and `rent_adjustment_pct`.

> **Within the conjunction, `basis_match = match` is read as `basis_ok` per §4.4, satisfied by a declared `not_applicable` dimension where the profile declares it so. This resolves a contradiction internal to Part A v5, adopted in draft v4 of this instruction.**

### 5.0.2 L3 replay integrity supersedes Part B's cand_06 exclusion fallback
> **For L3 replay integrity, failure to reverify any candidate that contributed to the frozen L1 record halts the entire production package. This supersedes Part B's prospective cand_06 exclusion fallback, which governed whether the original provider measurement could proceed before calls were made.**

### 5.0.3 `charge_scope` applicability — a Stage-1B PRODUCT
`452_deterministic_rules.json` freezes at Stage 1A **the algorithm for consuming the determination**. Stage 1B produces `452_charge_scope_applicability_determination.json`, per parameter:
```
schema_applicability, qualification_use, materialization_subset_membership,
source_artifact, source_pointer, quoted_rule,
status: resolved | unresolved | conflicting
```
**Two source artifacts, because one cannot answer both questions.** `431_requirement_profiles.json` establishes whether `charge_scope` participates in **qualification**; whether the field is **schema-fixed `not_applicable`** is answered by `431_output_schema.json`. Part A lists `charge_scope` only under the share parameters; Part B describes scope as metadata for `tenant_share` and omits it elsewhere. That divergence is why inference is unsafe and why the profiles alone may not settle it.

**`unresolved` or `conflicting` on any parameter fails the input-sufficiency gate and halts.** This is load-bearing twice: it determines whether an empty or failed scope citation invalidates a field (§4.3.5), and it determines §4.3.6 subset membership, on which **Pass B #6's logical status turns**.

### 5.1–5.18
Identity formulas and serialization; support-span selection with Part A §7.1 quoted; **ambiguity handling** per `452_ambiguity_ruling.md`, recorded as an **extension of Part A §4.5 to the ambiguous case decided 2026-07-26**; the empty-support rule; two-window resolution; per-field invalidation and merge semantics; the Pass-B recomputation chain; the Pass-A fidelity criterion; the **logical/exercise status split and its general applicability rule**; field-scope sets; parameter-aware `basis_ok`; the `charge_scope` consumption algorithm; the final-disposition aggregation and the two-axis split; §10 maps and formulas; span construction, failure boundaries, deduplication and ordering; the primary/support asymmetry; `value_token_present` canonical path; the topological order; transactional directory publication and the failure record; Pass A / Pass B definitions.

---

## 6. Unseating clause — committed before any count is seen

> No prior `satisfied` count is preserved as a target. Any prior state may be retained, unseated, or rendered not established under the preregistered rules. The resulting count may increase, decrease, or remain unchanged.
>
> This package applies §4.5 field-grounding at a granularity P4 did not enforce, narrows the resolution window for candidate citations, invalidates fields with empty support, and recomputes the full deterministic chain including cited-union retention. A Pass B count below fourteen — **including zero** — is anticipated, legitimate, and demonstrates the grounding rule operating. **A zero count produces a vacuous exercise status, not a failure, and establishes nothing.** Fourteen remains what P4 computed. Neither supersedes the other.

Step 450 found one non-resolving context citation in the as-computed state (cand_03, panel 4, role C, `xc1`). The ambiguity and empty-support passes have not been run and their scope is unknown to every party. **No one reads which traces are affected before this clause is committed.**

### 6.9 L2 comparison — one-way
> The comparison function may write **only** `l2_comparison.json`. It may not mutate, overwrite, or feed any authoritative field in `source_records.json`, either pass result, the fidelity record, validation, observations, materialization, grounding enforcement, envelope sufficiency, the report, post-report validation, or the final disposition.

---

## 7. Four pre-sanction gates

### 7.0 Stage-1 ordering
Gate records are themselves Stage-1 artifacts inside `EXPECTED_PACKAGE_ARTIFACTS`, so **they cannot hash themselves**.
```
0  RATIFICATION. The reviewing party ratifies the exact bytes of
   452_production_package_instruction_v8.md and records the decision in
   build_log/452_ratification_record.md, naming the reviewed content hash,
   the reviewing party, and the date. This record is a §3.1 artifact and
   must exist before step 5. It is terminal: it is not itself ratified.
   Stage 1A does not begin until it exists.
1  finalize script, tests, rules, schemas, inventory
2  run tests and the two censuses; each record hashes the NON-GATE Stage-1
   artifacts and MUST declare input_hashes (§7.1)
2a STAGE-1A CHECKPOINT. Force-add and commit the exact Stage-1A artifacts.
   No subsequent Stage-1 step may consume an untracked Stage-1A artifact.
3  Stage 1B, in this order:
     3a  452_charge_scope_applicability_determination.json
     3b  452_input_sufficiency.json, CONSUMING and HASHING that exact determination,
         DECLARING as input_hashes every artifact it read;
         it passes only if every parameter is resolved
3c STAGE-1B CHECKPOINT. Force-add and commit the exact Stage-1B products and any
   legitimately updated gate records.
4  FREEZE. Working tree clean relative to the Stage-1B checkpoint. NO further
   §3.1 artifact edits.
5  build 452_config_manifest.json from the COMMITTED §3.1 blobs
6  package commit P452 — the first package-identity commit, and the commit used
   for token derivation, sanction, and Stage-2 execution
```

**Step 0a, WORKING BASELINE (added v8.3).** Before any new Stage-1 edit, force-add and commit every currently existing §3.1 artifact as a clearly labelled NON-SANCTIONED Stage-1 checkpoint. Provenance only: not P452, not token-bearing, cannot authorize Stage 2.

**Why the checkpoints exist.** Until an artifact is committed it has **no recoverable prior state** — the gate records store its digest, not its bytes. A closed package whose bound source artifacts were never tracked can prove which bytes entered P452 and **cannot** prove that an asserted intermediate edit was confined to what was claimed. Those are different claims. Found when Claude Code was asked to confirm a citation repoint in `452_ambiguity_ruling.md` was confined to one line and correctly answered that it could not, because the file had never been committed.

**A single pre-freeze commit is NOT sufficient**, and was the first proposal: it establishes a baseline only from that point forward, so any silent change before it becomes part of the baseline. The rule is per-stage — **no Stage-1 §3.1 artifact may remain untracked after the ordered stage that produces or modifies it has completed.**

**Second effect, and it makes step 4 enforceable.** `build_log/` is gitignored, so `git status --porcelain --untracked-files=all` is currently **blind to every §3.1 artifact** — the same blindness §3.3 records on the output side. Once the checkpoints track them, a Stage-1 edit after the freeze becomes visible to the cleanliness check. Before this, step 4's freeze was declaratory; after it, it is checkable.

**Checkpoint commits carry NO token or sanction significance.** Their only job is historical recoverability. Because `build_log/` is gitignored, use explicit `git add -f -- <paths>`; **never** blanket-force-add the directory.
**The determination is a non-gate Stage-1B input to the input-sufficiency gate, not its sibling.** The earlier gate records do not hash it — they precede it and test different things. The manifest binds all of them afterward. The gate records must describe **the exact bytes being sanctioned, not their ancestors.**

### 7.1 Stage-2 revalidation
**Stage 2 recomputes every gate record's declared input hashes against the corresponding HEAD blobs. Any mismatch halts.** Existence and a `passed` field are necessary and not sufficient.

**Every gate record MUST declare `input_hashes` for every artifact it consumed. A gate record declaring no `input_hashes` FAILS Stage-2 revalidation; it does not pass it vacuously.** `452_input_sufficiency.json` binds the charge-scope determination by hash and must additionally declare, as `input_hashes`, every artifact it read. Added v8.3 after Claude Code found that §7.4's record declared none and therefore satisfied this check trivially — a check that cannot fail is the defect class §7.1 was written to close, reappearing as a record with nothing to go stale.

### 7.2 `452_producer_consumer_census.json`

Every inventory entry, across Part A + Part B + Step 452, traced **per required field, not per product**:

```
product
  → every entry in required_fields[]
      → field-producing function
      → persisted location
      → consuming check or reader
```

**A product passes only if EVERY one of its required fields passes.** "The product has a producer" is not sufficient. This wording is load-bearing and was added after a demonstrated miss: v8 named `execution_integrity` as an axis and instructed `452_execution_record_final.md` to cite it while nothing computed it. A product-level census would have passed that record — it had a producer, a path and a consumer — while the required field inside it had none. The census exists to catch producerless things; a producerless *field* inside a valid product is the same defect wearing a smaller hat.

Respects `temporal_layer`. A path constant, a planned section, or a derivable-later note is **not** a producer. First missing link halts.

### 7.3 `452_predicate_reachability_census.json`
Every success predicate traced to a conforming reachable assignment. **Must additionally identify every criterion with a possibly-empty domain and confirm each carries both `logical_status` and `exercise_status` (§4.2.2).** #3 and #6 are named instances, not asserted to be the complete list. Also: parameter-aware `basis_ok` both branches; `pass_a_l1_fidelity`; incomplete-scope rejection; grounding invalidation and its `not_assessable` token; the missing-support path; `materialization_status` both branches; the tenth check; envelope categories; both disposition axes.

### 7.4 `452_input_sufficiency.json` (Stage 1B, step 3b)
Every §4 product proven deterministically derivable from frozen inputs, under Stage-1B's forbidden-outputs constraint. Consumes and hashes `452_charge_scope_applicability_determination.json`; **passes only if every parameter is `resolved`.** Open item: §10 needs Atlas §3.3's offset against the frozen hash. Step 450's `field_support` 108/108 finding is L2 and is **re-established**, not assumed.

### 7.5 `452_stage1_test_results.json`
Producer `452_production_tests.py`; both in `EXPECTED_PACKAGE_ARTIFACTS`. Fixtures **embedded as literals**.

**Positive coverage:** two-window resolution split; 0/1/2+ classification; empty-support → `missing_support_trace`; invalidation to `not_assessable`; the failed-trace boundary; parameter-aware `basis_ok` both branches; **#6 and #3 each across logical pass, logical fail, and exercise vacuous**; the Pass-B recomputation chain including retention change on invalidated relevance; **`pass_a_l1_fidelity` detecting a deliberately corrupted transformation**; a complete package with `semantic_support_spans: []` classified as construction-exercised but support-span-materialization-unexercised; support-span deduplication and ordering; identity-formula collision resistance; anti-borrowing against a synthetic support span containing the primary's value.

**Adverse coverage** — the P4 construction was proven against the P4 harness, and reusing a design does not prove an implementation. Each must halt **before promotion**, with the result recorded here:

edited working-tree manifest; manifest binding omission; manifest binding addition; stale CLI token; stale signed-tag token; modified repository-local imported module; missing gate record; gate record marked pass carrying stale input hashes; modified L1 input; unexpected staged output; missing staged output; pre-existing target directory; attempted outbound network connection in either invocation; subprocess outside the allowlist; failed primary pin/hash/profile check; output-manifest omission; Set-A file altered between production and `finalize-record`; `charge_scope` determination `unresolved`; failure-path emission producing a valid failure record and **no** final-named L3 product; **invocation-record write or rename failing AFTER Set-A promotion, producing quarantine of the results directory, absence of the authoritative target path, a failure record recording the disposition, and no final execution record (§4.17)**; **each `execution_integrity_status` conjunct failing individually and suppressing the successful final execution record (§4.12)**.

---

## 8. Provenance construction

Committed-blob token under path-pinned LF; committed trust anchor at P452; external signed annotated tag created after P452 and pointing at it; exact sanction message hashed and recorded; HEAD-authoritative manifest with the worktree copy byte-identical; **closed input set with the manifest outside it** and **three closed output sets**; runtime token recomputation from HEAD blobs; four-way token equality; whole-repository cleanliness; clean detached worktree at P452; `CAM_ROOT` derived from script location.

### 8.1 Manifest naming
`452_config_manifest.json`. `431_config_manifest.json` is a **frozen L1 input only**.

### 8.2 Sanction key — operational precondition
> Before sanction, Tzvi confirms that the private sanction key is not provided to, read by, copied by, or invoked from the Code/build process. The build environment contains only the committed public key and trust policy. Code produces the exact unsigned sanction message; Tzvi personally signs only after the construction audit is clear.

**Do not claim physical separation unless it is physically separate.** Unconfirmed until Tzvi states the fact.

### 8.3 Sanction products and lifecycle
**`452_sanction_message.txt`** and **`452_sanction_record.md`**, `temporal_layer: post_p452_provenance`, neither a token input.
```
1  P452            — exact Stage-1 artifact set (§3.1) + 452_config_manifest.json
2  Q-prep          — 452_sanction_message.txt, draft 452_sanction_record.md
3  Construction audit clears the exact message bytes
4  Tzvi personally creates the signed annotated tag targeting P452
5  Stage 2 runs detached at P452
6  Results commit  — 452_stage2_results/ + 452_production_invocation_record.json
                     + 452_execution_record_final.md
```

---

## 9. Scope constraints
Read-only against all L1 artifacts; hash before and after, identical or halt. No `cam/` file created, modified or deleted; `EvidenceSpan`, `_find_normalized_matches`, `_span_text_hash` and the status constants imported, never reimplemented. Zero provider calls across both sanctioned invocations. All new files under `build_log/`. No live pipeline file consumes any output. Gate B is not invoked; the §7 orchestration seam is modelled, not wired.

---

## 10. Stop seams

**Halts:** any gate failing, its record missing, or its declared input hashes not matching HEAD; `pass_a_l1_fidelity` failing; any L1 input hash mismatch; `lease_evidence_spans` symbols not cleanly importable; **any primary failing pin, hash or profile verification**; `source_document_hash != canonical_text_hash`; §5.0.3 returning `unresolved` or `conflicting`; any product requiring semantic invention; any Stage-1B computation revealing an outcome; any artifact not on §3.1; any staged product not on §3.3; a pre-existing target directory without a sanctioned replacement rule; a failing zero-call check in either invocation; a subprocess outside the allowlist; a Set-A file altered before `finalize-record`; any edit to a Stage-1 artifact after step 4 of §7.0.

**Does not halt:** a Pass B count differing from fourteen, including zero; a citation invalidating a field; a blocked materialization record (emitted); a failed or missing support trace (emitted); a Pass-B retention change; **any `exercise_status: vacuous`**; §10 reporting a distance exceeding the envelope; a primary whose quote appears elsewhere in the document, except cand_06.

---

## 11. What this package establishes — RESULT-CONDITIONAL

> **This package tests and, if the corresponding exercise fields come back true, may establish deterministic certified-package materialization, source-addressed support-span materialization, and runtime anti-borrowing. The output records which were actually exercised (§4.2.4).**

**Established unconditionally on completion:** a dated, execution-identity-bound deterministic production of Part-A / Part-B products P4 did not emit, over frozen live judgments; a proven-faithful Pass-A historical baseline (§4.2.1); §4.5 grounding enforcement at field granularity with the ambiguity and empty-support extensions; the full Pass-B recomputation chain; the §10 envelope-sufficiency measurement.

**Established only if the corresponding field is true:** deterministic certified-package construction (`materialization_function_exercised`, qualified by `materialization_exercised_by_pass`, since a Pass-A-only exercise runs over unenforced judgments and shows construction rather than governed production); governed post-enforcement certified-package production (`post_enforcement_certified_package_exercised`); source-addressed support-span materialization (`support_span_materialization_exercised`); runtime anti-borrowing on a support-bearing package (`anti_borrowing_runtime_exercised`), as distinct from the static `anti_borrowing_dataflow_verified`; and the ambiguity and empty-support invalidation branches, per their counts.

**Does not establish:** anything about the historical §9.1 conjunction, which fails on #6 for Pass A and is not retroactively converted; a mechanism refusing to certify at decision time; general semantic accuracy; recall; share-versus-fee discrimination; production readiness.

**Claim bound, verbatim in every output:** deterministic post-run production of specified governed-selection products over the frozen Step-447 record for these seven provisioned candidates. Not a re-measurement. Not a repair of P4.

---

## 12. Authorization boundary

Ratifying this authorizes **Stage 1A and Stage 1B only**. Not Stage 2, `cam/` changes, wiring, Gate B changes, or patent drafting.

Stage 2 is authorized only by a separate explicit sanction bound to a signed annotated tag over the freshly hashed artifacts, after the construction and the exact sanction message are audited and personally signed.

The patent supplement remains deferred until this package produces an outcome, and must then state which of §11's conditional items were actually exercised.

---

*v8 DRAFT. Six v7 items addressed: `pass_vacuous` replaced by a `logical_status` / `exercise_status` split, with the conjunction consuming only the former (1); `452_production_invocation_record.json` added so no artifact carries a closure result produced in its own future, and the manifest no longer claims one (2); Stage-1B internal order frozen, the determination made an input to the input-sufficiency gate rather than its sibling (3); contract reconciliation limited to Part-A and Part-B promised products, since the full inventory contains a product that does not yet exist when it runs (4); six further exercise fields plus two invalidation counts, so a complete package carrying no support spans cannot be read as exercising support-span materialization or runtime anti-borrowing (5); the optional failure record given an exact path, producer, schema, consumer and atomic publication, and Set B made transactional (6). Plus, beyond the audit: the logical/exercise split is stated as a GENERAL rule for any criterion with a possibly-empty domain, applied to #3 as well as #6, with the reachability census required to identify any others rather than trusting that two is the complete list. Requires re-audit before Code sees it.*
