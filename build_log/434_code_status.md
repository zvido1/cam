# Step 434 — CORRECTION to V3 + config-integrity HARD-HALT ruling — CODE STATUS

**Status:** COMPLETE (build-only; ZERO provider calls). The V3 premise was verified against source
and found partly false; the 433 V3 mirror is WITHDRAWN and replaced with the ruled fix (config-
integrity → hard halt). F2 retained. Fresh token minted. STOP for re-audit.
**Instruction on disk:** `build_log/434_chat_instruction.md` (verbatim correction + my code
verification + ruling, Rule 7).
**Scope:** harness call/provenance path only. No new evaluation semantics. Semantic artifacts
byte-identical to `65556ee`.

---

## 1. Verification of the correction against actual source (Rule 2 — quote the code)

All three claims CONFIRMED by reading `cam/core/provider_router.py` and
`cam/adapters/lease_review/lease_coverage_305.py`:

1. **`ProviderRouter` (class @ `provider_router.py:848`)** has exactly `__init__`, `_get_adapter`
   (`:867`), `call_json` (`:884`). **No `route()`, no `_check_generation_integrity` method.**
   `_check_generation_integrity` is a **module-level function** (`:53`), invoked *inside adapters*.
2. **`_call_single_evaluator_305` (`lease_coverage_305.py:433-435`)** does
   `router._get_adapter(provider)` then `adapter.call(...)` — the **same path** the 431 harness uses.
   There is no router-level integrity path to "route through," so nothing was bypassed.
3. **The canonical-panel adapters self-check on `adapter.call`:** OpenAIAdapter `_call_once:375`,
   AnthropicAdapter `call:461`, XAIAdapter `call:764` (which also `except FatalProviderError: raise`,
   `:770`). So the 431 harness **already inherited** 416 for A/B/C. `GoogleGenAIAdapter.call:505`
   does NOT self-check but **always transmits temperature** (`:521`) and is degraded-only; there is
   **no MistralAdapter** (`_get_adapter` `:880` → `FatalProviderError("Unknown provider")`).
4. **`FatalProviderError(ProviderError)` (`:141`) → `ProviderError(Exception)` (`:135`)** — it IS
   caught by the harness's `except Exception`, so pre-434 a config-integrity violation was absorbed
   into fallback (behavior **(b)**).

**Consequence:** my 433 `_assert_call_integrity` mirror pre-check was redundant (A/B/C already
self-check the REAL payload) and rested on a partly-false "bypass" premise, and it checked a
*reconstructed* param view rather than the real outbound payload. **WITHDRAWN.**

## 2. Ruling on the real open question — (a) HARD-HALT is required

A 416 config-integrity violation means the FROZEN generation config was about to be silently
altered — the exact silent-config-drift class 415/416 exist to prevent, and the measurement's
"config-integrity-asserted / identity-frozen panel" claims (config `§3`) depend on it. Absorbing it
into `except Exception` → fallback would (i) silently degrade the *frozen panel* on a *config bug*,
(ii) misclassify a non-retryable fatal as a provider outage, and (iii) bury the violation in the
audit as a generic failure. **§11 stop seam: the measurement must ABORT, not work around it.**
(Other FatalProviderErrors — provider safety filter, missing pool key, unknown pool provider — are
legitimate per-call failures on already-degraded attempts and correctly proceed to fallback.)

## 3. The fix (net change vs the 433 commit `45b94ce2`)

- **WITHDRAWN:** `_assert_call_integrity` (the 433 V3 mirror) and its pre-call invocation; the
  mirror-derived `integrity_record` provenance. `_provider_call` reverts to obtaining the adapter
  and calling `adapter.call(...)` (which runs the REAL 416 check on the REAL payload for A/B/C); it
  now captures the REAL `adapter.last_integrity` for provenance (`temperature_integrity`).
- **ADDED:** `class MeasurementIntegrityHalt(RuntimeError)` (deliberately NOT a `ProviderError`, so
  `except Exception` in the traversal cannot re-absorb it) and `_is_config_integrity_violation(exc)`
  (message match on `config_integrity_violation`, robust to adapter re-wrapping). Both the own-chain
  (Phase 1) and pool (Phase 2) handlers now check `_is_config_integrity_violation(e)` **before**
  classification and `raise MeasurementIntegrityHalt(...)` — a hard halt that propagates through
  `run_panel_attempt` → `run_candidate_series` → `run_stage2` to `main()`, which prints a clear
  banner and exits non-zero. No fallback is attempted on an integrity violation.
- **RETAINED from 433:** `import time` (real latent-bug fix — `call_panelist` uses `time.time()`)
  and **F2** (certified per-role object carries no `raw_response`; certification reads only
  `judgment`; raw text lives only in the `attempts[]` audit layer).

## 4. No-call verification — ACTUAL output (Rule 1)

### 4a. Config-integrity HARD-HALT (`test_434_halt_nocall.py`; provider I/O monkeypatched to raise)
```
[434.1] config-integrity violation -> MeasurementIntegrityHalt (no degrade)  OK
[434.2] MeasurementIntegrityHalt is not a ProviderError (cannot be absorbed)  OK
[434.3] non-integrity fatal (safety filter) degrades, does NOT halt  OK
[434.4] generic provider error degrades (unchanged)  OK
```
- **434.1** — a `FatalProviderError("config_integrity_violation: …")` on the primary call makes
  `call_panelist` raise `MeasurementIntegrityHalt`; it does **not** return a degraded result and
  does **not** attempt any fallback.
- **434.2** — `MeasurementIntegrityHalt` is not a `ProviderError`, so the traversal's
  `except Exception` cannot absorb it (structural).
- **434.3** — a NON-integrity `FatalProviderError` (provider safety filter) does **not** halt; it
  degrades like any provider failure (proves the halt is SPECIFIC to config-integrity).
- **434.4** — a generic provider error still degrades (unchanged).

### 4b. F2 still enforced (`test_434_f2_nocall.py`)
```
[F2.1-3] certified object/judgment clean; attempts[] retains raw  OK
[F2.4] certification_trace carries no raw text; still certifies  OK
```

### 4c. 432 orchestration regression
`ALL NO-CALL ORCHESTRATION CHECKS PASSED — zero provider calls made.` (grounding / no-repair /
unanimous certify / same-series pairing / honest shortfall / no-implicit-majority.)

### 4d. Build gate (`--mode build`)
4/4 relationship tests PASS; stale-sweep clean; wiring check `payloads_built=7`,
`PROVIDER CALLS MADE: 0`; `cam/ clean`; `MODEL CALLS MADE: 0`.

## 5. Byte-identity of semantic artifacts (confirmed `git diff --quiet HEAD` → UNCHANGED)

`431_measurement_config.json` `6bfb6e5e…`, `431_requirement_profiles.json` `48c55c98…`,
`431_output_schema.json` `3925001c…`, `431_selector_prompt.txt` `3a146f41…`,
`431_fixture_preflight.json` `03316302…` — all IDENTICAL to `65556ee`.

## 6. Files changed & the new token

- **Changed (tracked):** `build_log/run_431_selection_measurement.py`,
  `build_log/431_config_manifest.json`. **Expected: harness + manifest only.**
- **New (`-f`):** `build_log/434_chat_instruction.md`, `build_log/434_code_status.md`.
- **NEW Stage-2 sanction token:**
  `48054981045fc1a5f37e8b235d3cccb10586d3a04fa35eaf4a36b6a41f375487`
- Manifest `stage2_supersession.chain` now records `47cb312a` (preregistration), `833fd43e` (432),
  and `9c2cc8e1` (433) as **SUPERSEDED-FOR-EXECUTION — NOT void**.

## 7. Discipline confirmations
- **Zero provider calls** (build + all test suites provider-free; `MODEL CALLS MADE: 0`).
- `git status --porcelain cam/` **empty** (imports only; the tests monkeypatch harness symbols at
  runtime, never editing any committed `cam/` file).
- No semantic artifact edited; no new evaluation semantics; `_check_generation_integrity` is neither
  invoked-as-mirror nor reimplemented — the real adapter check on the real payload is relied upon.

## 8. STOP
Committed locally (`-f` paths), **NOT pushed**, **measurement NOT run.** The run happens only after
the re-audit of the 434 diff clears and Tzvi sanctions the new token `48054981…`.
