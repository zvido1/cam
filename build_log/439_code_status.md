# Step 439 — collapsed final scope: FIX 1a + 434 message-halt + terminal-fatal + report + F2

**Status:** COMPLETE (build-only; ZERO provider calls). STEP A gate passed (xAI integrity call is
benign, verified as fact). Collapsed scope implemented in one pass, all no-call-tested. Fresh token
minted. Semantic artifacts byte-identical to `65556ee`. STOP for the final assembled-scope re-audit
(GPT Condition 3).
**Instruction on disk:** `build_log/437_chat_instruction.md`/`439` (this brief filed as 439).

---

## STEP A (Condition 1, READ-ONLY gate) — xAI `_check_generation_integrity` is BENIGN (verified, not inferred)
Traced the full body of `_check_generation_integrity` (`cam/core/provider_router.py:53-122`) as
invoked on the xAI path (`XAIAdapter.call:764`, `temperature_omit_reason=None`; params always carry
`temperature` (`:759`) and `max_tokens` (`:760`)):
- `:68-76` builds `declared` (from `target`) + empty `transmitted/omitted/omission_reasons` — new dicts.
- `:79-80` `"temperature" in params` is **True** → `transmitted["temperature"] = params["temperature"]`
  (reads params, writes a NEW dict); the `else` raise (`:85-91`) is unreachable for grok.
- `:94-97` `"max_tokens" in params` is **True** → recorded; raise (`:99-102`) unreachable.
- `:105-113` skipped (`target.reasoning_effort is None` for Role C).
- `:115-122` returns a NEW record dict.
**It never assigns to `params`, never mutates `target`, has no side effects, and cannot raise for
grok.** Read-only and benign — a verified FACT. Gate passed → proceeded to STEP B.

## STEP B — the assembled collapsed scope (diff = harness + manifest only)

### FIX 1a — halt-on-fatal for the PROPAGATING paths (A and C)
`call_panelist` now has, in BOTH the own-chain and shared-pool traversals, `except FatalProviderError
as e: … raise` BEFORE the generic `except Exception`. A `FatalProviderError` that reaches the harness
TYPED (Anthropic role A `:471-472`, xAI role C `:770-771`, plus xAI-mapped auth fatals) is fatal to
the WHOLE RUN immediately — never a degraded attempt, never fallback. The exception is annotated
(`_role_431/_candidate_431/_provider_431/_model_431`) for the terminal record.
**`ProviderPermanentError` is OMITTED from the tuple — it does not exist in `cam` (Step 435);
referencing it would `NameError`.** This deviation from the brief's literal `except (FatalProviderError,
ProviderPermanentError)` is required and recorded.

### OpenAI/wrapping path — the committed 434 message-halt is KEPT, unaltered (quoted)
```
except Exception as e:
    if _is_config_integrity_violation(e):
        raise MeasurementIntegrityHalt("HARD HALT (§11): config-integrity violation on …") from e
```
OpenAI (role B) WRAPS its integrity fatal into a generic `ProviderError` (message preserved); the
`config_integrity_violation` message-match halts it. So config-integrity halts on all three canonical
roles: A/C by type (FIX 1a), B by message (434). Not duplicated, not altered.

### `run_stage2` terminal-fatal machinery
`seam_before` before the try; the candidate loop is the only thing inside; on
`(FatalProviderError, MeasurementIntegrityHalt)` a terminal `431_fatal_run_error.json` is written
(role+candidate active, requested provider/model, fatal type+message, whether earlier calls
completed, `no_fallback_attempted_after_fatal: True`, partial-sidecar+seam paths) then re-raised;
`finally` captures `seam_after`, writes the runtime seam (`fatal_occurred`), and persists a `_partial`
sidecar so nothing is lost. `main()` catches both fatal types → banner + `SystemExit(2)`.

### Role-C scaffolding removal — NONE existed
The 437 FIX-1c scaffolding (a `role_c_integrity: {adapter_integrity_check: "absent_on_xai_adapter"}`
field, an "unprotected role" claim-bound, a harness-side xAI integrity wrapper) was **never
implemented** — I STOPPED at 437 rather than write the false claim. `grep` confirms none of it is in
the harness. Nothing to remove. (The new `role_c_integrity_note` field is the CORRECT Condition-2
structural-absence language, not the withdrawn scaffolding.)

### F2 — intact, unchanged
Certified per-role object carries no `raw_response`; certification reads only `judgment`; raw text
lives only in `attempts[]`. `grep -c '"raw_response": call_meta.get'` = 0.

## STEP C (Condition 2) — Role-C language EMITTED in the report, not just the sidecar
`render_report()` writes `431_selection_measurement.md` (a RUN output; not built now) and emits the
verbatim Role-C note via `ROLE_C_INTEGRITY_REPORT_LANGUAGE`, plus the true §9 adapter-asymmetry
framing (A/C propagate → type-halt; B wraps → message-halt; Google is the only no-assertion adapter,
degraded-only). Test 439.5 reads the rendered `.md` and confirms the exact sentence
("…structural absence of a needed check, NOT a skipped check.") and the `Step 435-read/3105902`
citation are present in the REPORT file.

## No-call tests — ACTUAL output (Rule 1)
```
[439.1] FIX 1a: propagated FatalProviderError (integrity AND auth) halts, annotated  OK
[439.2] 434 message-halt: OpenAI-wrapped config-integrity -> MeasurementIntegrityHalt  OK
[439.3] transient error degrades through fallback, does NOT halt  OK
[439.4] F2 intact: no raw_response in certified object/judgment/trace  OK
[439.5] report EMITS the Role-C structural-absence language (Condition 2)  OK
[439.6] run_stage2 terminal-fatal: terminal record + partial sidecar + seam persisted  OK
```
(439.6 prints run_stage2's "RUN" banner because run_stage2 was invoked with `run_candidate_series`
monkeypatched to raise — NO model call fired; the test redirects all output paths to scratchpad, so
no `build_log` artifact was created.) Plus: 432 orchestration regression 6/6; build gate 4/4.

## Byte-identity + files + token
- Five semantic artifacts **byte-identical to `65556ee`** (`git diff --quiet HEAD` → UNCHANGED each).
- Changed (tracked): `run_431_selection_measurement.py`, `431_config_manifest.json` — harness +
  manifest only.
- **NEW token:** `ce284b55950a1ce152e312eb96b0276933e0cb0fa8fb574f7051742515e6fa0f`
- Chain records `47cb312a` / `833fd43e` / `9c2cc8e1` / `48054981` as SUPERSEDED-FOR-EXECUTION.
- **Token-tracking note:** the brief said "superseding d0293605", which is NOT this harness's
  lineage; the actual prior committed token was `48054981` (Step 434). The manifest chain and this
  status reflect the REAL committed lineage. Flagged in the manifest `_token_tracking_note`.

## Discipline
Zero provider calls; `git status --porcelain cam/` empty; no `cam/` edit (the owed OpenAI-adapter
uniformity fix — the real debt, retargeted from xAI per Step 436 — remains a SEPARATE reviewed
change, not done here). STOP for the final assembled-scope re-audit.
