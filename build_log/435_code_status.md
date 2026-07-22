# Step 435 — STEP 0 verification finding — FIX 1 is STOP-AND-REPORT (as-written premise falsified)

**Status:** STEP 0 complete → **STOP on FIX 1** per the instruction's own gate. No FIX-1 code
implemented (the as-written re-raise would be a fix that looks correct and does nothing). FIX 2 (F2)
is ALREADY implemented and committed (Steps 433/434) — re-verified below. **No rebuild, no new
token, no code change this step** (a code change would be premature until the FIX-1 approach is
confirmed). `cam/` untouched (STEP 0 was read-only).

---

## STEP 0 — the three premises FIX 1 rests on, each checked against source (Rule 2: quote the code)

### Premise A — `ProviderPermanentError` exists. **FALSE.**
`grep -rn "ProviderPermanentError" cam/` → no matches. The entire hierarchy in
`cam/core/provider_router.py`:
```
135:class ProviderError(Exception):
138:class RetryableProviderError(ProviderError):
141:class FatalProviderError(ProviderError):
```
`except (FatalProviderError, ProviderPermanentError): raise` references an undefined name — it would
`NameError` at runtime. There is no permanent-error type to catch.

### Premise B — a config-integrity `FatalProviderError` propagates out of `adapter.call()` as its own type. **FALSE for OpenAI (role B).**
The integrity `FatalProviderError` originates only inside OpenAI/Anthropic/xAI (`_check_generation_integrity`).

- **OpenAIAdapter.call — WRAPS it into generic `ProviderError`:**
```
391    def call(self, system_prompt, user_prompt, target) -> str:
392        try:
393            result = self._call_once(...)          # _call_once raises FatalProviderError at :375
...
413            return result
414        except Exception as e:                      # ← catches the FatalProviderError too
415            msg = f"openai_error: {type(e).__name__}: {e}"
...
420            raise ProviderError(msg)                 # ← re-raised as GENERIC ProviderError
```
There is NO `except FatalProviderError: raise`. So a role-B config-integrity violation reaches the
harness typed as `ProviderError`, not `FatalProviderError`. (The message is preserved:
`"openai_error: FatalProviderError: config_integrity_violation: …"`.)

- **AnthropicAdapter.call — propagates (role A):**
```
471        except FatalProviderError:
472            raise
```
- **XAIAdapter.call — propagates (role C):**
```
770        except FatalProviderError:
771            raise
```
- **GoogleGenAIAdapter.call — WRAPS (`:721 except Exception → raise ProviderError`)**, but never runs
  the integrity check, so no config-integrity `FatalProviderError` originates there.

**This is exactly the wrap-case STEP 0 said to STOP on.** A type-based
`except FatalProviderError: raise` (even after fixing Premise A) would catch A and C but **silently
miss B** — the exact "fix that looks correct and does nothing" the instruction warned against.

### Premise C — "match the real `_call_single_evaluator_305` treatment exactly" means halt-on-fatal. **FALSE.**
`_call_single_evaluator_305` never special-cases fatal errors; every handler is a broad
`except Exception` that classifies and DEGRADES:
```
532:        except Exception as e:      # _try_call: release claim, record, re-raise to caller
573:        except Exception as e:      # own-chain loop: classify, continue to next candidate
654:        except Exception as e:      # shared-pool loop: classify, continue
```
So "match 305 exactly" would mean **degrade on fatal** — the OPPOSITE of FIX 1's halt intent. 305 is
production coverage code that prefers graceful degradation; the measurement wants the opposite. The
two cannot both be honored.

## Verdict on FIX 1
FIX 1 as-written is triply blocked (undefined type; OpenAI wrap; 305-does-not-halt). Per the STEP 0
gate I am **not implementing it**. The correct approach is the one the instruction itself points to
on the wrap-branch: **"key on a structured fatal classification the adapter DOES expose."** The only
structure that survives OpenAI's wrap is the **preserved message marker** (`config_integrity_violation`).

## What is ALREADY in the committed tree (Step 434, token `48054981…`)
Step 434 already implements the message-based variant — and it correctly handles OpenAI's wrap:
- `_is_config_integrity_violation(exc)` matches `"config_integrity_violation" in str(exc)`, which is
  present even in OpenAI's wrapped `ProviderError` message. So role B IS caught (unlike the type
  approach).
- On a config-integrity violation, `call_panelist` raises `MeasurementIntegrityHalt` (NOT a
  `ProviderError`, so `except Exception` cannot re-absorb it) **before** classification/fallback, in
  BOTH the own-chain and pool handlers. It is immediate and fatal-to-whole-run: it propagates
  through `run_panel_attempt` → `run_candidate_series` → `run_stage2` → `main()` (which prints a
  banner and exits non-zero). No candidate is finished, no other role/own-chain/pool is tried.
- No-call test (434) proved: config-integrity → halt (no degrade); non-integrity fatal → degrade.

So 434 already satisfies FIX 1's **mechanism** (halt, immediate, robust to the OpenAI wrap) for the
config-integrity case, using the structured signal the adapter actually exposes.

## The two GENUINE gaps between 434 and this brief — need a ruling, not blind code
1. **Scope.** 434 halts ONLY on config-integrity. The brief wants ALL fatal/permanent to halt. But:
   (i) `ProviderPermanentError` doesn't exist; (ii) OpenAI wraps ALL its fatals (missing key,
   bad-request) into `ProviderError`, so an "all-fatal" halt via type is impossible and via message
   would require matching the fragile `"FatalProviderError"` substring; (iii) an all-fatal halt
   contradicts 305 and would abort the whole run on, e.g., a missing key or safety-filter on a
   DEGRADED pool model. **Decision needed:** keep the narrow, defensible config-integrity halt (434),
   or broaden — and if broaden, to which specific conditions, given the wrap and the pool-fatal
   cases?
2. **`run_stage2` terminal-fatal audit machinery.** The brief wants: `seam_before` before a try;
   on fatal, persist a terminal `fatal-run-error` record (role+candidate active, requested
   provider/model, exception type+message, whether earlier calls completed, that NO fallback was
   attempted, partial-sidecar+seam locations); `finally` captures `seam_after` and persists the
   runtime seam + partial sidecar. **434 does NOT have this** — it only prints a `main()` banner and
   exits. This is real, additive audit work that is independent of the type-propagation problem and
   can be implemented under EITHER scope decision.

## FIX 2 (F2) — already implemented + committed (433/434); re-verified, no call
The certified per-role object carries no top-level `raw_response`; `certify_parameter_series` reads
only `judgment`; raw text lives only in `attempts[]`. Re-verified with `test_434_f2_nocall.py`:
```
[F2.1-3] certified object/judgment clean; attempts[] retains raw  OK
[F2.4] certification_trace carries no raw text; still certifies  OK
```

## Recommendation (bringing the finding back, as instructed)
- Adopt the **message/classification-based** halt (already in 434) as the correct FIX-1 mechanism —
  NOT the type-based re-raise (blocked by the OpenAI wrap + missing type).
- Rule on **scope** (config-integrity-only vs broader, and exactly which conditions).
- Authorize me to add the **`run_stage2` terminal-fatal record + partial-sidecar/seam-in-`finally`**
  machinery (gap #2), which I will implement once scope is confirmed, then rebuild + mint a fresh
  token for the delta re-audit.

## Discipline
- `git status --porcelain cam/` empty (STEP 0 read-only). Zero provider calls. Semantic artifacts
  unchanged (no rebuild this step). No new token (no code change pending the scope ruling).
