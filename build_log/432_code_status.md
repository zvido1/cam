# Step 432 — 431 Part B Stage-2 CALL-PATH IMPLEMENTATION — CODE STATUS

**Status:** COMPLETE (build-only; ZERO provider calls). Named objective — *implement the Stage-2
call path against the frozen evaluator machinery, rebuild, mint a fresh token, verify wired without
firing calls, STOP for scoped audit* — **met**.
**Instruction on disk:** `build_log/432_chat_instruction.md` (verbatim brief, filed per Rule 7).
**Authority read first:** Part B v3.3 §2/§5/§7/§8/§11 (`431_partB_measurement_instruction.md`), the
gated call-site docstring in the harness, the v3.3 manifest.

---

## 0. DEFERRED (at top, per Rule 5) — what this step did NOT produce, by scope

The brief scoped this step to **"IMPLEMENT (call path only)"** + the in-process runtime seam
capture, and **"make NO run."** Accordingly the following §8.2 artifacts are **NOT RUN / NOT
PRODUCED** here because each is computed *from a Stage-2 sidecar that only exists after the live
run*, which is forbidden in this step:

- `431_validation.json` (§8.2 measurement class) — **NOT PRODUCED** (needs a post-run sidecar).
- `431_repository_seam_check.json` (§8.2 artifact/seam class) — **NOT PRODUCED** (same).
- `431_selection_measurement.md` (the §9 report) — **NOT PRODUCED** (needs run outputs).
- `431_selection_measurement_sidecar.json` / `431_runtime_seam_capture.json` — **code path
  implemented in `run_stage2`, but NOT invoked** (writing them requires firing calls).

These are RUN-step outputs. The call path that *will* emit the sidecar + in-process runtime seam is
implemented and gated; the two validators + report are a follow-on once a sanctioned run exists.

---

## 1. LOAD-BEARING INTERPRETATION (surfaced for the scoped informed audit — veto BEFORE any run)

The brief says *"call through the real `_call_single_evaluator_305` path — do NOT copy, approximate,
or reimplement provider logic."* I did **not** literally invoke `_call_single_evaluator_305(...)`,
because that is impossible here and would violate the ratified spec:

- `_call_single_evaluator_305` hard-bakes the **coverage-analysis** prompt and parser. Quoting the
  code — `lease_coverage_305.py:435` builds the call from the module constant `_SYSTEM_PROMPT`
  ("You are a commercial real estate attorney performing per-element coverage analysis…",
  `lease_coverage_305.py:213`) and `_build_user_prompt` (`:247`), and `_parse_verdict_list` (`:377`)
  parses **element-verdict arrays**. There is **no parameter** to inject the 431 selector prompt /
  schema, and it cannot parse a 431 judgment.
- Feeding it the 431 payload would require editing/subclassing/monkeypatching `cam/` — forbidden by
  Part B §2 ("No edit/subclass-override/monkeypatch") and Guardrail #5.
- Sending its coverage prompt would violate §5's absolute payload invariant (the model may see ONLY
  the 431 selector prompt/schema/candidate/envelope/neutral label/applicability dimensions).

The ratified text I followed instead: Part B §2 — *"Import … the `_call_single_evaluator_305`
call/fallback/provenance **pattern**"* — and this file's own gated-call-site docstring: *"implement
against `_call_single_evaluator_305`'s call/fallback/provenance **shape**."* So the harness imports
and calls the **same real provider primitives `_call_single_evaluator_305` itself uses internally**
— `ProviderRouter` / `ModelTarget` / `RouterConfig` / the provider adapters (`cam.core.provider_router`)
— plus the real `EVALUATOR_LINEUP_305` identity/temperature/own_chain and the pure importable
helpers `_classify_failure` / `_is_transient_failure`, and **replicates the own-chain-fallback /
canonical-classification / provenance shape** in measurement code. Provider HTTP/SDK/temperature/
retry logic is **not reimplemented** — it stays inside the imported adapter. No `cam/` file is
edited; nothing is monkeypatched (`git status --porcelain cam/` empty, verified §6).

This interpretation is written verbatim into the code as an ARCHITECTURE NOTE at the top of the
call-path section (`run_431_selection_measurement.py`, replacing the old `NotImplementedError` stub).
**If the auditor/architect rejects it, the section changes before any run — no model call has been
made under it.**

---

## 2. What the call path does — mapped to the brief's item-1 requirements

Every requirement traces to a function in `run_431_selection_measurement.py`:

| Brief item-1 requirement | Where / how |
|---|---|
| import real `EVALUATOR_LINEUP_305`, call the real 305 provider path (no reimplement) | `call_panelist` imports `EVALUATOR_LINEUP_305`, `_classify_failure`, `_is_transient_failure`; `_provider_call` imports `ModelTarget/ProviderRouter/RouterConfig` and calls `adapter.call(...)` — the exact primitives `lease_coverage_305.py:433-435` uses |
| Role A/B/C identity from ACTUAL returned metadata | `_finalize` sets `actual_provider/actual_model/actual_label` from the entry that answered; canonicality compares actual vs frozen primary, never requested identity |
| preserve gpt-5.5 temperature exception (provider-default, logged, not silently dropped) | `ModelTarget.temperature` = frozen 0.0; the adapter omits it for models in `TEMPERATURE_ONLY_DEFAULT_MODELS` (gpt-5.5) and **logs** the omission via `_check_generation_integrity` (`provider_router.py:375-383`). Harness records `temperature_transmitted` + the adapter's `last_integrity`. Build output confirms `role B … temp_transmitted=False`, `A/C=True` |
| canonicality: only same-model Grok self-retry at frozen config is canonical; Haiku/gpt-5.4/Gemini = DEGRADED, excluded; `is_fallback` never infers canonical; provider+model+config_hash all participate | `_finalize`: `identity_ok = actual==frozen primary`; `config_ok = config_hash==reviewed manifest self-hash`; `canonical = identity_ok and config_ok`. C's own_chain entry IS grok-4.3 → self-retry stays canonical; A→Haiku / B→gpt-5.4 / pool→Gemini/Mistral are different models → `canonical=False`. `is_fallback` is recorded but **not** used in the canonical decision |
| send exactly candidate + envelope + neutral label + applicability dims + reviewed schema; nothing appended; panelists never see each other | `build_panelist_payload` renders ONLY the §5 whitelist via `str.replace` from `431_selector_prompt.txt` (positive whitelist; never reads `human_note`/`expected_quote`); `_provider_call` sends it as the sole message (empty system). Each `call_panelist` is independent — no panelist output is ever passed to another |
| retain raw responses + parse failures; invalid JSON / missing fields / unresolved citations follow REVIEWED rules; no meaning-changing repairs | every attempt (incl. parse failures) recorded in `attempts[]` with `raw_response`; parse is strict `json.loads` after fence-strip only (`_strip_code_fence`) — no object-hunting/field-synthesis; unresolved citations + missing fields handled by the reviewed `apply_field_grounding` (invalidate to `unclear`, no repair) |
| raw/canonical/series indices per §7; retries can't shop; same-series pairing; ceiling → honest shortfall | `run_candidate_series` assigns `raw_attempt_index` (wall-clock), `canonical_attempt_index`/`series_index` (1..5 in order obtained); canonical panels count in order (incl. refusals); degraded panels preserved, never promoted; `certify_parameter_series` consumes ONLY the kth canonical panel per candidate; a candidate missing index k → `absent_this_series` shortfall, never filled |
| keep pre-first-call manifest+token gate + in-process runtime seam capture | `_assert_stage2` gate at every `call_panelist` and at `run_stage2` entry; `run_stage2` captures `capture_cam_seam("before_first_model_call")` immediately before the candidate loop and `"after_last_model_call")` immediately after, writing `431_runtime_seam_capture.json` |

**Certification stays in the reviewed validator** (brief item 2): the call loop computes NO
relevance/basis/role/value/support/applicability judgment. `certify_parameter_series` calls the
pre-existing, reviewed `merge_panel` → `compare_candidate` → `certify`. No majority behavior
introduced (verified test [6] below: a non-unanimous field blocks certification).

---

## 3. Objective verification — ACTUAL test output (Rule 1: run it, paste it)

### 3a. Build (`--mode build`, zero calls) — PASSED
```
[4/6] running v3.3 relationship-contract tests (build gate)...
      [PASS] a_combined_opex_taxes (§5 test 1): expect basis_match=match, got match
      [PASS] b_sibling_tax_candidate (§5 test 2): expect basis_match=mismatch, got mismatch
      [PASS] c_comention_no_linkage (§5 test 3): expect basis_match=mismatch, got mismatch
      [PASS] d_ungrounded_linkage (§5 test 4): expect basis_match=undeterminable, got undeterminable
[5/6] ... stale 'charge_basis_components' occurrences: none
[wiring] verifying Stage-2 call path is implemented + wired (ZERO calls)...
      call path implemented (not a stub): True
      payloads built (no provider touched): 7 for ['cand_01'..'cand_07']
      §5 leak-checks passed: 7
      role A: anthropic/claude-sonnet-4-6 temp_transmitted=True  self_retry_same_model=False
      role B: openai/gpt-5.5        temp_transmitted=False self_retry_same_model=False
      role C: xai/grok-4.3          temp_transmitted=True  self_retry_same_model=True
      PROVIDER CALLS MADE (wiring check): 0
cam/ clean at build completion: True
MODEL CALLS MADE: 0
```

### 3b. Gate rejects unauthorized run — PASSED (no calls fire)
- `--mode run` (no sanction) → `StageAuthorizationError` (no `--stage2-sanction`).
- `--mode run --stage2-sanction 47cb312a…` (the OLD preregistration token) →
  `StageAuthorizationError: … '47cb312a…' != committed manifest '833fd43e…'`. The superseded token
  can no longer authorize a run against the executable harness — exactly the intended semantics.

### 3c. No-call orchestration test (synthetic judgments; scratchpad, not committed) — PASSED
Directly exercises `apply_field_grounding` / `merge_panel` / `compare_candidate` / `certify` /
`certify_parameter_series` with hand-built judgments — ZERO provider calls:
```
[1] grounding: all fields resolved, none invalidated  OK
[2] grounding: unresolved quote -> field invalidated to unclear  OK
[3] unanimous qualifying panel -> certify=satisfied  OK
[4] 5 canonical panels: per-series traces, same-series pairing, all satisfied  OK
[5] 3/5 canonical: series 4,5 honest shortfall (absent_this_series), no silent top-up  OK
[6] non-unanimous relevance -> certify=review_needed_disagreement (not satisfied)  OK
```

---

## 4. Byte-identity of semantic artifacts (brief item 2 / VERIFY)

Confirmed **byte-identical to `65556ee`** (`git diff --quiet HEAD` → UNCHANGED for each; hash unchanged
from the prior manifest):

| Artifact | sha256 | vs 65556ee |
|---|---|---|
| `431_measurement_config.json` | `6bfb6e5e…178ca` | IDENTICAL |
| `431_requirement_profiles.json` | `48c55c98…304fed` | IDENTICAL |
| `431_output_schema.json` | `3925001c…6dd11` | IDENTICAL |
| `431_selector_prompt.txt` | `3a146f41…e0007` | IDENTICAL |
| `431_fixture_preflight.json` | `03316302…fc79d` | IDENTICAL (deterministic regen) |

The blind reviews (Review A = prompt; Review B = schema+profiles) therefore carry over unchanged.

## 5. Files changed & the new token

- **Changed (tracked):** `build_log/run_431_selection_measurement.py` (harness — call path),
  `build_log/431_config_manifest.json` (regenerated). **Expected: harness + manifest only.**
- **New (untracked, gitignored → `-f` added):** `build_log/432_chat_instruction.md`,
  `build_log/432_code_status.md`.
- Harness sha256: `7c7b345bbbd417d9083d2491e58d57190d5a21f4bd520895c3266b71c41bc863`.
- **NEW Stage-2 sanction token (executable package):**
  `833fd43e7197d95c60e4b7080810764c33b4a4bd4edbbbe86390036b9f4fcacc`
- Manifest `stage2_supersession` records `47cb312a…` as **SUPERSEDED-FOR-EXECUTION — NOT void**
  (retained as evidence the preregistration was sanctioned before an executable call path existed).

## 6. Discipline confirmations

- **Zero provider calls made** in this step (build + wiring check + gate tests + orchestration test
  all provider-free; `MODEL CALLS MADE: 0`).
- `git status --porcelain cam/` **empty** (no `cam/` file created/modified/deleted; imports only).
- No live pipeline file imports or consumes the harness output.
- No semantic artifact edited; certification logic untouched (consumed, not modified); no majority
  behavior introduced.

## 7. STOP

Per the brief: committed locally (explicit `-f` paths), **NOT pushed**, **measurement NOT run.**
The ~90–105-call run happens only after the scoped informed audit of the call-path diff clears and
Tzvi sanctions the new token `833fd43e…`. Next review targets are unchanged (semantic artifacts
byte-identical); the new surface for audit is the call-path diff in
`run_431_selection_measurement.py`.
