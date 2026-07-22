# Step 436 — STEP 1a finding: adapter premise INVERTED + wrapped signal is message-only → STOP

**Status:** STEP 1a (read-only) complete → **STOP-AND-REPORT** on FIX 1, for TWO independent reasons,
each a stop condition the brief itself defines. No FIX-1 code implemented; no rebuild; no new token.
FIX 2 (F2) already implemented + committed (433/434), re-verified. `cam/` untouched (read-only).

---

## STEP 1a — the actual per-adapter fatal-propagation behavior (Rule 2: quote the code)

The brief says: *"xAI adapter wraps fatal conditions into generic ProviderError … OpenAI/Anthropic
propagate FatalProviderError directly; xAI does not."* **The source shows this is INVERTED for
OpenAI and xAI.** Verified in `cam/core/provider_router.py`:

### xAI — PROPAGATES the fatal (does NOT wrap it)
```
745    def call(self, system_prompt, user_prompt, target) -> str:
...
764            integrity = _check_generation_integrity(target, params)   # raises FatalProviderError
765            self.last_integrity = integrity
...
770        except FatalProviderError:
771            raise                                                     # ← fatal PROPAGATES as-is
772        except Exception as e:
773            msg = f"xai_error: {type(e).__name__}: {e}"
...
777            if "401" in s or "unauthorized" in s or "invalid api key" in s:
778                raise FatalProviderError(msg)                         # auth → also FatalProviderError
779            raise ProviderError(msg)                                  # only NON-fatal SDK errors → generic
```
A config-integrity or auth (permanent) condition on the xAI path arrives at the harness typed as
`FatalProviderError`. Only genuinely non-fatal SDK errors become generic `ProviderError`.

### Anthropic — PROPAGATES (`:471-472`)
```
471        except FatalProviderError:
472            raise
```

### OpenAI — WRAPS the fatal into generic `ProviderError` (this is the real wrapper)
```
391    def call(self, system_prompt, user_prompt, target) -> str:
392        try:
393            result = self._call_once(...)          # _call_once raises FatalProviderError at :375 (integrity)
...
414        except Exception as e:                      # ← NO `except FatalProviderError: raise` above this
415            msg = f"openai_error: {type(e).__name__}: {e}"
416            s = str(e).lower()
417            if "rate limit" in s or "429" in s or "timeout" in s or "temporarily" in s:
418                raise RetryableProviderError(msg)
419            raise ProviderError(msg)                # ← integrity FatalProviderError → GENERIC ProviderError
```

**Corrected adapter map:** A (Anthropic) propagates · **B (OpenAI) WRAPS** · C (xAI) propagates.
The wrapping adapter is **OpenAI (role B)**, not xAI. The brief, GPT's scoped-C-vs-B ruling, and the
recorded debt ("edit the xAI adapter") are all aimed at the wrong adapter.

## STEP 1a — the ACTUAL wrapped-fatal signature on the wrapping (OpenAI) path
On the OpenAI `call()` path the ONLY fatal raised inside the try is the config-integrity assertion
(`_call_once` → `_check_generation_integrity:86/99`); missing-key fatals come from `OpenAIAdapter.__init__`
via `_get_adapter` (BEFORE `.call()`), so they propagate as `FatalProviderError` unwrapped. The
wrapped form is therefore precisely:
```
ProviderError("openai_error: FatalProviderError: config_integrity_violation: declared temperature=… was dropped …")
ProviderError("openai_error: FatalProviderError: config_integrity_violation: max_output_tokens=… not present …")
```
Enumerated signal available: **message only** — no structured attribute, no status code, no
error-code field. What IS deterministic in the message: the format `f"openai_error: {type(e).__name__}: {e}"`
embeds the original type name (`FatalProviderError`) and the original message, which for the
integrity assertion always begins `config_integrity_violation` (a marker emitted ONLY by
`_check_generation_integrity`, nowhere else).

**Per the brief's STEP 1a gate — "If the … ProviderError carries NO reliable structured fatal
signature (only an opaque message), STOP and report … we then need GPT to rule whether
message-prefix matching is acceptable or whether B (adapter edit) becomes necessary after all."**
That condition is met: the signal is message-only. STOP.

## Two stop conditions, both the brief's own

1. **Inverted premise.** Implementing the brief literally (`_is_wrapped_fatal` on "the xAI/Grok
   path") would attach the allow-list to an adapter that does NOT wrap, and leave the adapter that
   DOES wrap (OpenAI/role B) uncovered — a fix aimed at the wrong path. Must not implement against
   an inverted premise (cf. the 434 correction pattern).
2. **Message-only signal** on the real wrapping path (OpenAI) → the brief's explicit STOP-for-GPT
   condition.

## What this changes for GPT's scoped-C-vs-B decision (new facts)
GPT chose scoped-C (harness allow-list) over B (adapter edit) believing the wrap was a pervasive
xAI issue. Reality: **exactly ONE adapter (OpenAI) is non-uniform** — it is the only one of the
three canonical adapters lacking an `except FatalProviderError: raise`. So option B is a **one-line**
change to `OpenAIAdapter.call` (add `except FatalProviderError: raise` before `:414`), which would
make fatal propagation uniform across A/B/C and REMOVE the need for any harness message-matching.
That may now be cleaner than scoped-C. GPT should re-rule with the corrected facts.

If GPT still prefers scoped-C: the correct positive allow-list on the OpenAI-wrapped path is the
**`config_integrity_violation` marker** (deterministic; emitted only by the integrity assertion;
survives the wrap intact) — NOT a loose grep, an exact enumerated signature. Note this is precisely
what the already-committed Step 434 `_is_config_integrity_violation` matches, and its no-call test
proved it halts on the OpenAI-wrapped form (role B included). So scoped-C for the config-integrity
case is effectively already implemented in 434; what remains is (a) GPT's blessing of message-match,
(b) the `run_stage2` terminal-fatal record + partial-sidecar/seam-in-`finally` machinery (gap; 434
lacks it), and (c) whether scope stays config-integrity-only or broadens.

## Debt correction
The recorded debt must target the **OpenAI adapter** (add `except FatalProviderError: raise`), not
the xAI adapter (which already propagates). xAI needs no change for fatal uniformity.

## FIX 2 (F2) — already implemented + committed (433/434); re-verified no-call
```
[F2.1-3] certified object/judgment clean; attempts[] retains raw  OK
[F2.4] certification_trace carries no raw text; still certifies  OK
```

## Decisions needed before I implement FIX 1 (one clean pass after the ruling)
1. **B vs scoped-C, with corrected facts:** OpenAI is the sole non-uniform adapter — prefer a
   one-line `except FatalProviderError: raise` in `OpenAIAdapter.call` (a separate, reviewed cam/
   change), or keep the harness-side allow-list?
2. If scoped-C: **confirm message-matching** on the `config_integrity_violation` marker is
   acceptable (the brief reserved this ruling).
3. **Scope:** config-integrity-only (434), or broaden — and to exactly which affirmatively
   enumerated conditions?
4. **`run_stage2` terminal-fatal machinery:** authorize the `seam_before`/try/terminal-record/
   `finally`-`seam_after`+partial-sidecar additions (independent of 1–3; I can build them under any
   ruling).

## Discipline
`git status --porcelain cam/` empty (STEP 1a read-only). Zero provider calls. Semantic artifacts
unchanged (no rebuild). No new token (no code change pending the ruling). No `cam/` edit (the OpenAI
one-liner, if chosen, is a separate reviewed change — NOT done here).
