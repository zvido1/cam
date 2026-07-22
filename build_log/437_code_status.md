# Step 437 — ruling D's FIX 1c rests on a FALSE claim about the xAI adapter → STOP (cannot write it to the record)

**Status:** STOP-AND-REPORT. FIX 1c instructs me to write into the §9 report and sidecar provenance
that *"Role C ran WITHOUT adapter-level config-integrity assertion (the xAI adapter has no
`_check_generation_integrity`)."* **That statement is false against the source** (quoted below), and
Reporting-Integrity Rule 2 (claims about code must quote the code) and Rule 6 (no unverified
document claims — added after a fabricated clause reached the patent record) forbid me from writing
it. No FIX-1 code, no rebuild, no new token this step. FIX 2 already committed (433/434), re-verified.
`cam/` untouched.

---

## The two claims in ruling D about xAI, checked against `cam/core/provider_router.py` (freshly read)

### Claim: "the xAI adapter has no `_check_generation_integrity`." → **FALSE.**
```
763            # Step 416: integrity assertion — temperature unconditionally transmitted.
764            integrity = _check_generation_integrity(target, params)
765            self.last_integrity = integrity
```
`XAIAdapter.call` invokes `_check_generation_integrity` at line 764. It HAS the assertion.

### Claim: "xAI does not propagate the fatal type (it is the wrapping gap)." → **FALSE.**
```
770        except FatalProviderError:
771            raise
772        except Exception as e:
773            msg = f"xai_error: {type(e).__name__}: {e}"
...
778                raise FatalProviderError(msg)      # even auth errors become FatalProviderError
779            raise ProviderError(msg)               # only genuinely non-fatal SDK errors -> generic
```
`XAIAdapter.call` PROPAGATES `FatalProviderError` (770-771). Only non-fatal SDK errors become
generic `ProviderError`.

### The adapter that actually WRAPS its fatal is OpenAI (unchanged from Step 436):
```
414        except Exception as e:                 # no `except FatalProviderError: raise` above
415            msg = f"openai_error: {type(e).__name__}: {e}"
...
420            raise ProviderError(msg)            # integrity FatalProviderError -> generic ProviderError
```

## Corrected reality (all three canonical adapters run the integrity assertion)
| Role | Adapter | `_check_generation_integrity`? | Fatal type at the harness |
|---|---|---|---|
| A | Anthropic | YES (`:461`) | PROPAGATES (`:471-472`) |
| B | OpenAI | YES (`_call_once:375`) | **WRAPS → generic `ProviderError`** (`:414/:420`) |
| C | xAI | **YES (`:764`)** | **PROPAGATES (`:770-771`)** |
| (pool) | Google | NO | wraps (`:721`); degraded-only, never canonical |

So there is **no canonical-role that "ran without the integrity assertion."** Role C (xAI) both runs
the assertion AND propagates the fatal type — it is the BEST-covered role, not a gap. The only real
gap is a TYPE-propagation gap on **OpenAI (role B)**, which the committed Step 434 message-match
(`config_integrity_violation`) already halts on. The only adapter with no assertion at all is
Google, a degraded pool fallback (never a canonical role, always transmits temperature).

## The kernel of truth (stated accurately, so it CAN go in the report)
xAI transmits temperature **unconditionally** (`:759`; it does not consult
`TEMPERATURE_ONLY_DEFAULT_MODELS`), so its integrity check at `:764` cannot detect a temperature
*omission* — but since grok-4.3 accepts temperature 0, transmitting the declared temperature 0 is
CORRECT, so there is no integrity issue for Role C to detect. That is very different from "xAI has no
integrity assertion."

## Why I cannot implement FIX 1c as written
- The `role_c_integrity.adapter_integrity_check: "absent_on_xai_adapter"` field value is FALSE
  (present at `:764`).
- The §9 report sentence "the xAI adapter has no `_check_generation_integrity`" is FALSE and
  checkable — exactly the class of claim Rule 6 was written to stop from reaching the patent (the
  424 fabricated-clause incident). Writing it, even under instruction, is prohibited.
- FIX 1c's entire premise (a Role-C integrity gap needing instrumentation + a claim-bound) dissolves
  once the facts are corrected: Role C is fully integrity-asserted and fatal-propagating.

## Corrected design — ready to bless in one line, then I implement in a single pass + one token
1. **FIX 1a (halt-on-fatal, type-based) — CORRECT AS APPLIED TO THE PROPAGATING PATHS = A and C.**
   `except FatalProviderError: raise` (drop `ProviderPermanentError` — it does not exist, Step 435)
   in both traversals, before the generic `except`. This halts A (Anthropic) and C (xAI) on any
   propagated `FatalProviderError`, immediately and run-fatally.
2. **OpenAI (role B) wrap — keep the committed Step 434 message-match** (`_is_config_integrity_violation`
   → `MeasurementIntegrityHalt`). It halts OpenAI's WRAPPED config-integrity fatal (the exact
   marker, survives the wrap). Together, 1+2 cover config-integrity on all three canonical roles,
   plus all propagated fatals on A/C.
3. **`run_stage2` terminal-fatal machinery** — `seam_before` before the try; on fatal persist a
   terminal `fatal-run-error` record then re-raise; `finally` captures `seam_after` + partial
   sidecar/attempt audit. (Implement regardless.)
4. **Instrumentation — the TRUE version:** record per canonical call `declared_temperature`,
   `transmitted_temperature` (from `call_meta`), and the REAL `adapter.last_integrity` (present for
   A/B/C). Do NOT emit `"absent_on_xai_adapter"`. If a Role-C-specific note is wanted, the accurate
   one is: `xai_transmits_temperature_unconditionally: true; integrity_assertion_present: true (line 764); temperature_omission_undetectable_but_none_occurs (grok accepts temp 0)`.
5. **Report §9 — the TRUE asymmetry:** all three canonical adapters run the integrity assertion;
   OpenAI additionally WRAPS a raised integrity-fatal's TYPE (halted via message-match, not type);
   the only adapter lacking the assertion is Google (degraded pool, never canonical). Do NOT state
   Role C lacked the assertion.
6. **Debt — corrected target:** the adapter that breaks fatal-TYPE uniformity is **OpenAI** (add
   `except FatalProviderError: raise`), not xAI. (xAI already propagates and already asserts
   integrity — no debt.) Record accordingly.
7. **FIX 2 (F2)** — already committed (433/434); re-verified no-call this step.

## The single decision needed
Confirm the corrected design above (esp. items 4–6: TRUE instrumentation/report language, and the
debt retargeted to OpenAI, with NO false "xAI has no integrity" claim). On a yes, I implement 1–5 +
the F2 re-confirm in one pass, rebuild, and mint a fresh token for the delta re-audit. I will not
write the false claim under any framing.

## Discipline
`git status --porcelain cam/` empty. Zero provider calls. Semantic artifacts unchanged (no rebuild).
No new token. No `cam/` edit.
