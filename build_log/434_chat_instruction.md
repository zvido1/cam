# Step 434 — CORRECTION TO THE V3 AUDIT FINDING (verbatim, as received) + ruling

**Filed to disk per Reporting-Integrity Rule 7 before executing.** Supersedes Step 433's V3 fix.

---

CORRECTION TO THE V3 AUDIT FINDING — premise appears false; please verify against actual code.

Claude Code, reading the actual source (my own MCP read is currently failing, so I cannot
independently confirm and am relaying its code-cited claim), reports that V3's premise is wrong:

- ProviderRouter has NO route() method and NO _check_generation_integrity method.
- The real _call_single_evaluator_305 uses the SAME path the 431 harness uses:
  _get_adapter(provider) then adapter.call(...). There is no router-level integrity path to
  "route through" — so the 431 harness did NOT bypass one.
- The 416 integrity assertion (_check_generation_integrity, raising FatalProviderError) lives
  INSIDE the adapters (e.g. OpenAIAdapter), and because the 431 harness calls adapter.call(...),
  it ALREADY INHERITS that check. 416's protection was never bypassed.

If this is accurate, V3-as-specified (route through ProviderRouter.route()) is WITHDRAWN — it would
require inventing a method to match an incorrect premise, which we will not do.

Claude Code is pasting the actual relevant source (ProviderRouter's method list; the body of
_call_single_evaluator_305; the adapter's _check_generation_integrity) so you can verify against
code, not summary.

THE REAL OPEN QUESTION V3 was gesturing at, which still needs your ruling: the adapter's
_check_generation_integrity raises FatalProviderError on a temperature-transmission violation. In
the 431 harness's own-chain traversal, provider calls are wrapped in `except Exception`. So: when a
FatalProviderError fires mid-measurement, does the harness (a) let it propagate as a HARD HALT
(a config-integrity violation aborts the measurement — arguably required), or (b) catch it as just
another provider failure and move to fallback (silently degrading the panel on an integrity
violation)? Rule on which behavior is required. If (b) is what the code does and (a) is what's
required, THAT is the real fix — catch FatalProviderError specifically and halt, rather than
absorbing it into fallback.

F2 (strip raw_response from the certification path) is unaffected and still stands.

---

## Code Verification (Claude Code, against cam/core/provider_router.py @ working tree)

CONFIRMED — the correction is accurate:
1. `ProviderRouter` (class @ line 848) methods: `__init__`, `_get_adapter` (867), `call_json` (884).
   NO `route()`, NO `_check_generation_integrity` method. `_check_generation_integrity` is a
   MODULE-LEVEL function (line 53), invoked inside adapters.
2. `_call_single_evaluator_305` (lease_coverage_305.py:433-435) does `router._get_adapter(provider)`
   then `adapter.call(...)` — the SAME path the 431 harness uses. No router integrity path exists.
3. Canonical-panel adapters self-check on `adapter.call`: OpenAIAdapter `_call_once:375`,
   AnthropicAdapter `call:461`, XAIAdapter `call:764` (re-raises FatalProviderError cleanly). The
   431 harness ALREADY inherits 416 for A/B/C. (GoogleGenAIAdapter `call:505` does NOT self-check
   but ALWAYS transmits temperature @ line 521 and is degraded-only; there is no MistralAdapter —
   `_get_adapter("mistral")` raises FatalProviderError "Unknown provider".)
4. `FatalProviderError(ProviderError)` (line 141) → `ProviderError(Exception)` (135): it IS caught
   by the harness's `except Exception`, so today a config-integrity violation is absorbed into
   fallback — behavior (b).

## Ruling (Claude Code)
Behavior (a) HARD-HALT is REQUIRED. A config-integrity violation means the FROZEN generation config
was about to be silently altered — the exact silent-config-drift class 415/416 exist to prevent, and
the measurement's "config-integrity-asserted / identity-frozen panel" claims depend on it. Absorbing
it into fallback would (i) silently degrade the frozen panel on a config bug, (ii) misclassify a
non-retryable fatal as a provider outage, and (iii) hide the violation in the audit. §11 stop seam:
the measurement must ABORT, not work around it. Other FatalProviderErrors (provider safety filter,
missing pool key, unknown pool provider) are legitimate per-call failures on already-degraded
attempts and may proceed to fallback.

## Fix delivered in Step 434
- WITHDRAW the 433 `_assert_call_integrity` mirror pre-check (redundant; adapters self-check on the
  real payload for A/B/C; the mirror checked a reconstructed view and rested on a partly-false
  premise). Rely on the adapters' own real-payload 416 check.
- ADD the real fix: a config-integrity violation (matched by the `_check_generation_integrity`
  message, robust to adapter re-wrapping) raises `MeasurementIntegrityHalt` and propagates as a HARD
  HALT — never absorbed into the own-chain/pool fallback.
- KEEP `import time` (real latent-bug fix from 433) and F2 (raw_response stripped from certification).
- Rebuild, fresh token superseding 9c2cc8e1; zero calls; semantic artifacts byte-identical to
  65556ee. STOP for re-audit.
