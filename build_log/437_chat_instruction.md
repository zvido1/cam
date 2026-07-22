# Step 437 — STAGE-2 CALL-PATH FIXES "final shape" (ruling D; Chat labeled "Step 433"; filed as 437)

**Filed per Rule 7.** Chat labeled this "Step 433"; 433/434/435/436 are committed. Filed as 437.
Ruling D's FIX 1c rests on a claim about the xAI adapter that is FALSE against the code (see 437
status). I cannot write that claim into the report/sidecar/patent (Rule 2/Rule 6). STOP-and-report
with the corrected facts + a ready-to-bless corrected design.

---

STAGE-2 CALL-PATH FIXES (Step 433, final shape) — implement, ZERO model calls, new token, stop for
delta re-audit. Do NOT run. GPT ruled D: run with the xAI/Role-C integrity gap DOCUMENTED AND
INSTRUMENTED (not assumed-fine); B (edit xAI adapter) recorded as owed debt, NOT done now.

FIX 1a — halt-on-fatal for the A/B (OpenAI/Anthropic) paths, which DO propagate the fatal type:
- In call_panelist, BOTH own-chain and shared-pool traversals, BEFORE the generic `except Exception`:
  `except (FatalProviderError, ProviderPermanentError): raise`.
- Fatal is FATAL TO THE WHOLE RUN, immediately: no finish-candidate, no other-role, no fallback,
  no defer.
- In run_stage2: seam_before before the try; on fatal, persist a terminal fatal-run-error record
  then re-raise; in `finally`, capture seam_after + persist runtime seam + partial sidecar/attempt
  audit. Terminal record: role+candidate active at fatal; requested provider/model; fatal type+msg;
  whether earlier calls completed; that NO fallback followed the fatal; partial sidecar+seam paths.

FIX 1c — xAI/Role-C: DOCUMENTED + INSTRUMENTED gap (NOT fatal-detection — there is no reliable
signal; that is the accepted gap):
- Do NOT attempt to detect/halt on xAI fatals (no structured signature exists; message-grep is
  unsafe both directions — that's why D was chosen over C).
- INSTRUMENT instead: for every Role-C (xAI) call, capture into the per-role sidecar record the
  ACTUAL config the call transmitted — the temperature actually sent (from call_meta / the
  adapter's transmitted-config surface), plus whatever the adapter exposes about what it actually
  sent — alongside the DECLARED frozen config (temperature 0). Add an explicit per-C-call field,
  e.g. `role_c_integrity: {declared_temperature, transmitted_temperature, adapter_integrity_check:
  "absent_on_xai_adapter", matches_declared: <bool or "unverifiable">}`. The point: the run RECORDS
  the evidence from which config drift is detectable in the artifact, since the adapter will not
  assert it.
- In the report (§9): state explicitly that Role C (xAI/Grok, the canonical self-retry role) ran
  WITHOUT adapter-level config-integrity assertion (the xAI adapter has no _check_generation_integrity,
  unlike OpenAI/Anthropic); that its transmitted config was RECORDED per-call for post-hoc
  verification; and that any `satisfied` result on a parameter whose certification depends on a
  canonical Role-C panel must be read as "certified under a Role-C call whose config was
  recorded-but-not-assertion-guarded," NOT as "certified under fully integrity-checked conditions."
  A/B were halt-protected; C was observation-recorded — the report must carry this asymmetry.
- RECORD OWED DEBT (433 status + sidecar provenance): xAI adapter lacks _check_generation_integrity
  and fatal propagation; should be made uniform with OpenAI/Anthropic in a SEPARATE cam/ change
  under its own review. Deferred, not done in 431.

FIX 2 (F2): strip raw_response from the certification path — keep in attempts[]/degraded_panels
(audit), STRIP from the object feeding certify_parameter_series/merge_panel/compare_candidate and
from certification_trace per_candidate. Verify (no call) the cert-path object carries no raw_response.

CONSTRAINTS: edit NO cam/ file; all five semantic artifacts byte-identical to 65556ee (confirm
hashes); no new evaluation semantics; ZERO provider calls. Rebuild package + manifest, mint FRESH
token (superseding 833fd43e), keep build testable without calls.

REPORT: [as in brief]. Commit git add -f explicit paths, no push. STOP for delta re-audit.
