# Step 439 — STAGE-2 FIX (collapsed scope) — verbatim brief as received

**Filed per Rule 7 (belatedly — written after execution in the same session; recorded here to
complete the audit trail). Chat labeled this "Step 439".**

---

STAGE-2 FIX (collapsed scope, Step 439) — GPT confirmed the Role-C integrity requirement DISSOLVES
(reconciliation accepted: xAI lacks the OMISSION-GUARD check, correctly, and grok transmits
temperature=0 by construction — the omission failure mode is structurally impossible on grok). Three
GPT closing conditions. Implement in one pass, ZERO model calls, new token, stop for the final
assembled-scope re-audit. Do NOT run.

STEP A — CONDITION 1 (READ-ONLY, gates implementation): Read what the _check_generation_integrity
call on the xAI path (XAIAdapter.call:764) ACTUALLY DOES. Quote the method body as invoked on the
xAI path. Confirm it is read-only on params (builds new dicts, no assignment, no side effect, no
assertion that affects grok's outbound config) — i.e., that the reconciliation hypothesis ("xAI has
a _check_generation_integrity doing a DIFFERENT/benign job") is a verified FACT, not an inference.
If it does anything unexpected to params, has side effects, or asserts something that matters for
grok, STOP and report before implementing anything.

STEP B — implement the collapsed fix scope (only if STEP A confirms benign):
- FIX 1a: except (FatalProviderError, ProviderPermanentError): raise BEFORE the generic
  except Exception, in BOTH own-chain and shared-pool traversals, for the propagating paths.
  Fatal is FATAL TO THE WHOLE RUN immediately (no finish-candidate, no other-role, no fallback,
  no defer).
- Confirm the committed 434 OpenAI message-halt on config_integrity_violation is in place for the
  OpenAI/wrapping path (so a wrapped fatal still halts). Quote it; do not duplicate or alter it if
  present.
- run_stage2 terminal-fatal machinery: seam_before before the try; on fatal, persist terminal
  fatal-run-error record then re-raise; finally captures seam_after + persists runtime seam +
  partial sidecar/attempt audit. (Confirm present from prior fixes; keep intact.)
- F2: confirm raw_response is stripped from the certification path (attempts[]/degraded_panels keep
  it; cert-path object + trace do not). Already done — confirm intact.
- REMOVE all Role-C dissolution scaffolding: any role_c_integrity sidecar instrumentation added for
  the tightened-D/harness-wrapper path, any Role-C claim-bound language premised on "unprotected
  role," any harness-side xAI integrity-check wrapper. These are unnecessary — the requirement
  dissolved. Remove cleanly; confirm nothing else depends on them.

STEP C — CONDITION 2 (report language): the report generator (431_selection_measurement.md
generation) must state for Role C: "Role C (grok-4.3, canonical self-retry role) ran without
omission-guard integrity instrumentation because the guarded condition — conditional temperature
omission (TEMPERATURE_ONLY_DEFAULT_MODELS) — is structurally impossible for grok-4.3 (not in the
omit-set; transmits temperature=0 unconditionally, verified by code trace, Step 435-read/3105902).
This is a structural absence of a needed check, NOT a skipped check." Ensure this is EMITTED in the
report, not just recorded in a sidecar.

CONSTRAINTS: edit NO cam/ file (STEP A is read-only of cam/); all five semantic artifacts
byte-identical to 65556ee (confirm hashes); no new evaluation semantics; ZERO provider calls.
Rebuild package + manifest, mint FRESH token (superseding d0293605), keep build testable without
calls.

REPORT: STEP A's quoted finding on the xAI _check_generation_integrity (benign or not); the
assembled diff of the collapsed scope (1a + confirmation of 434 message-halt + terminal-fatal + F2 +
the Role-C scaffolding REMOVALS); the report-language emission (Condition 2); no-call tests proving
(1) fatal halts on propagating paths, (2) 434 message-halt fires on the wrapping path, (3) transient
still falls back, (4) F2 intact; semantic hashes byte-identical to 65556ee; files changed (harness +
manifest only); new token; zero calls; git status --porcelain cam/ empty. Commit git add -f explicit
paths, no push. STOP for the final assembled-scope re-audit (GPT Condition 3).

---

**Note on execution vs brief:** `ProviderPermanentError` does not exist in `cam` (verified Step 435),
so FIX 1a was implemented as `except FatalProviderError: raise` (the tuple's second member omitted to
avoid a NameError). The "REMOVE Role-C scaffolding" step was a no-op because that scaffolding was
never implemented (execution stopped at Step 437 rather than write the false "xAI has no integrity"
claim). See 439 status.
