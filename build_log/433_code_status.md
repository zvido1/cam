# Step 433 — 431 Part B Stage-2 CALL-PATH FIXES (V3 + F2) — CODE STATUS

**Status:** COMPLETE (build-only; ZERO provider calls). Both audit fixes implemented, both proven
by no-call tests, fresh token minted, STOP for delta re-audit.
**Instruction on disk:** `build_log/433_chat_instruction.md` (verbatim brief, Rule 7).
**Scope:** harness call/provenance path only. No new evaluation semantics. Semantic artifacts
byte-identical to `65556ee`.

---

## 0. One additional fix surfaced while testing (reported at top, Rule 5)

The F2 test exercised `call_panelist` end-to-end for the first time (build/gate/orchestration paths
never reached it) and surfaced a **latent bug from Step 432**: `call_panelist` uses `time.time()`
for `elapsed_sec`, but the harness never imported `time`. Left unfixed, the **live run would have
crashed on the first panelist call** with `NameError: name 'time' is not defined`. Fixed by adding
`import time` (diff line ~29). This is in-scope (call-path provenance) and is called out here so the
re-audit sees it explicitly rather than buried.

---

## 1. FIX V3 (BLOCKING) — uniform 416 config-integrity assertion on every 431 call

**Root cause confirmed by reading `cam/core/provider_router.py`:** `_check_generation_integrity`
runs inside `.call()` for OpenAI (`_call_once:375`), Anthropic (`:461`), and xAI (`:764`) — but
**`GoogleGenAIAdapter.call()` (`:505`) does NOT invoke it.** The 432 call path used
`router._get_adapter(provider)` + `adapter.call(...)` directly and relied on each adapter to
self-check, which is not uniform: a **pool-fallback Gemini** request (role A/B/C degrading to the
shared pool) would fire with **no 416 protection** — exactly the silent config-drift class 415/416
exist to prevent.

**Fix (per the audit's sanctioned option — explicit invocation, not reimplementation):** new
`_assert_call_integrity(target)` **imports and calls the real `_check_generation_integrity` from
`cam.core`** (never reimplemented). It assembles only the outbound-param VIEW, mirroring the
adapters' own temperature decision with the **same capability map** `TEMPERATURE_ONLY_DEFAULT_MODELS`
(temperature omitted-with-documented-reason for gpt-5.5; transmitted otherwise). `_provider_call`
invokes it **before any provider machinery is obtained** (moved ahead of `ProviderRouter` /
`_get_adapter`), so a config-integrity failure raises `FatalProviderError` before the adapter/client
is even built. The returned integrity record is carried in provenance (`call_meta["integrity_record"]`,
and on the certified object).

**Quote of the guarantee (harness):**
```python
integrity_record = _assert_call_integrity(target)     # BEFORE router/_get_adapter/adapter.call
router = ProviderRouter([target], RouterConfig())
adapter = router._get_adapter(provider)
raw = adapter.call("", payload, target) or ""
```

**No-call verification (ACTUAL output, Rule 1):**
```
[V3.1] _assert_call_integrity reachable: B=omitted+reason, A=transmitted  OK
[V3.2] silent temperature drift -> FatalProviderError (416 active)  OK
[V3.3] _provider_call invokes integrity gate before adapter (no call fired)  OK
```
- **V3.1** — `_assert_call_integrity` returns a record for the real panel: B (gpt-5.5, omit-set) →
  temperature omitted **with** documented reason; A (sonnet) → temperature transmitted.
- **V3.2** — the REAL assertion my code invokes **RAISES** `config_integrity_violation` when
  temperature is dropped from the outbound payload with no capability exception. 416 is provably
  active.
- **V3.3** — monkeypatching `_assert_call_integrity` to a sentinel and calling `_provider_call`
  shows the sentinel propagates **before** any adapter/client is built — the integrity gate is
  wired ahead of the call, and no provider request can fire past a failing check.

## 2. FIX F2 — raw_response stripped from the certification path, retained in audit only

**Fix:** the certified per-role object returned by `_finalize` no longer carries a top-level
`raw_response` key. Raw model text is retained **only** in the `attempts[]` audit layer (and thus,
for non-canonical attempts, inside `degraded_panels`). `certify_parameter_series` reads **only**
`panel["per_role"][r]["judgment"]` (the parsed + grounded judgment), which never contained
`raw_response`.

**No-call verification (ACTUAL output):**
```
[F2.1-3] certified object has no raw_response; audit attempts[] retains it; judgment clean  OK
[F2.4] certification_trace carries no raw text; per_candidate clean; still certifies  OK
```
- **F2.1** — the certified object has no top-level `raw_response`.
- **F2.2** — `attempts[0]["raw_response"]` still equals the injected marker (audit layer preserved;
  the 432 "retain raw provider responses" requirement is still met).
- **F2.3** — the `judgment` object handed to `merge_panel` has no `raw_response`.
- **F2.4** — with a distinctive raw marker injected via the provider I/O boundary, the marker does
  **not** appear anywhere in the `certification_trace` JSON, and no `per_candidate` entry carries a
  `raw_response`; certification still returns `satisfied`.

*(Test harness: `_provider_call` was monkeypatched at the I/O boundary to inject the marker — ZERO
real provider calls. `_assert_call_integrity` was monkeypatched to a sentinel for the V3.3 wiring
proof. Both are runtime test-only patches in the scratchpad; no `cam/` file and no committed harness
code was altered by the tests.)*

## 3. Regression — 432 orchestration still holds
The 432 no-call orchestration suite (grounding / no-repair invalidation / unanimous certification /
same-series pairing / honest shortfall / no-implicit-majority) re-run against the final harness:
`ALL NO-CALL ORCHESTRATION CHECKS PASSED — zero provider calls made.`

## 4. Byte-identity of semantic artifacts (confirmed `git diff --quiet HEAD` → UNCHANGED)

| Artifact | sha256 | vs 65556ee |
|---|---|---|
| `431_measurement_config.json` | `6bfb6e5e…178ca` | IDENTICAL |
| `431_requirement_profiles.json` | `48c55c98…304fed` | IDENTICAL |
| `431_output_schema.json` | `3925001c…6dd11` | IDENTICAL |
| `431_selector_prompt.txt` | `3a146f41…e0007` | IDENTICAL |
| `431_fixture_preflight.json` | `03316302…fc79d` | IDENTICAL |

The fixes touch ONLY the harness call/provenance path; the blind reviews carry over unchanged.

## 5. Files changed & the new token

- **Changed (tracked):** `build_log/run_431_selection_measurement.py` (V3 + F2 + `import time`),
  `build_log/431_config_manifest.json` (regenerated). **Expected: harness + manifest only.**
- **New (untracked, gitignored → `-f`):** `build_log/433_chat_instruction.md`,
  `build_log/433_code_status.md`.
- Harness sha256: `22242e48814b62fb387223727cae28ef1275047a6e665dee990f27729803e40b`
  (before the manifest-supersession edit; final harness re-hashes in the committed manifest).
- **NEW Stage-2 sanction token (executable package, V3+F2):**
  `9c2cc8e157627d880068c6bb380c09e00c0ae0321fbac52253b268326b7dc9cd`
- Manifest `stage2_supersession.chain` records `47cb312a…` (preregistration) and `833fd43e…`
  (Step-432 call-path v1) as **SUPERSEDED-FOR-EXECUTION — NOT void**.

## 6. Discipline confirmations

- **Zero provider calls** (build + wiring + both test suites all provider-free; `MODEL CALLS MADE: 0`).
- `git status --porcelain cam/` **empty** (imports only; no `cam/` edit/subclass/monkeypatch of
  committed code).
- No semantic artifact edited; no new evaluation semantics; `_check_generation_integrity` imported,
  not reimplemented.
- Build remains testable without calls (`--mode build`; wiring check makes 0 provider calls).

## 7. STOP

Committed locally (explicit `-f` paths), **NOT pushed**, **measurement NOT run.** The run happens
only after the delta re-audit of the V3+F2 fix diff clears and Tzvi sanctions the new token
`9c2cc8e1…`. New surface for the re-audit: the V3+F2 diff in `run_431_selection_measurement.py`
(`git show <SHA>`).
