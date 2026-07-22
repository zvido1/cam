# Step 436 — STAGE-2 CALL-PATH FIXES (Chat labeled "Step 433"; filed as 436) — verbatim brief + STEP 1a gate

**Filed per Rule 7 before executing.** Chat labeled this "Step 433"; 433/434/435 are already
committed. Filed as 436. STEP 1a (read-only) returns STOP-AND-REPORT: the brief's adapter premise is
inverted (see 436 status), and the wrapped-fatal signal is message-only — both trigger the brief's
own stop conditions.

---

STAGE-2 CALL-PATH FIXES (Step 433) — implement two fixes, ZERO model calls, new token, stop for
delta re-audit. Do NOT run. GPT ruled: scoped-C (harness compensates for the xAI wrapping), B
(edit xAI adapter for uniform fatal propagation) RECORDED AS DEBT, not done now.

FIX 1 — halt-on-fatal, covering the mixed adapter boundary:

STEP 1a (READ-ONLY, gates the allow-list): Read the xAI adapter's call() and its ProviderError
construction in cam/core/provider_router.py. ENUMERATE the specific, named signatures a fatal/
config-integrity/permanent condition produces when wrapped into the generic ProviderError on the
xAI path — e.g. the wrapped exception's original type, a status code, an error-code field, or an
exact message prefix. Report the enumerated set with quoted lines. This is the fatal allow-list; do
NOT guess it — derive it from what the adapter actually emits. If the xAI ProviderError carries NO
reliable structured fatal signature (only an opaque message), STOP and report — we then need GPT to
rule whether message-prefix matching is acceptable or whether B (adapter edit) becomes necessary
after all.

STEP 1b (implement, against the STEP 1a allow-list):
- In call_panelist, in BOTH the own-chain traversal AND the shared-pool traversal, BEFORE the
  generic `except Exception`:
  (i) `except (FatalProviderError, ProviderPermanentError): raise` — covers the OpenAI/Anthropic
      (A/B) paths that propagate the fatal type directly;
  (ii) for a caught generic ProviderError (the xAI/Grok path): apply an explicit predicate
      `_is_wrapped_fatal(err)` that returns True ONLY if the error matches the enumerated fatal
      allow-list from STEP 1a. If True → raise (treat as fatal, halt). If False → ordinary transient
      handling (fall back). This is a POSITIVE allow-list: fatal only on affirmative match;
      EVERYTHING else is transient. No loose substring grep — match the specific enumerated
      signatures only.
- The fatal is FATAL TO THE WHOLE RUN, immediately: no finish-candidate, no other-role, no
  own-chain/pool fallback, no defer.
- In run_stage2: capture seam_before before the try; on fatal, persist a terminal fatal-run-error
  record then re-raise; in `finally`, capture seam_after + persist runtime seam + partial
  sidecar/attempt audit. Terminal record identifies: role + candidate active at fatal; requested
  provider/model; fatal exception type + message; whether earlier calls completed; that NO fallback
  was attempted after the fatal; partial sidecar + seam locations.

FIX 2 (F2): strip raw_response from the certification path — keep it in attempts[]/degraded_panels
(audit), STRIP from the object feeding certify_parameter_series/merge_panel/compare_candidate and
from certification_trace per_candidate. Verify (no call) the cert-path object carries no raw_response.

RECORD (in the 433 status file + the sidecar provenance): xAI adapter wraps fatal conditions into
generic ProviderError, breaking fatal-propagation uniformity across the panel (OpenAI/Anthropic
propagate FatalProviderError directly; xAI does not). The harness compensates via the STEP-1a
allow-list. OWED DEBT: the xAI adapter should be made uniform (raise/propagate FatalProviderError
like the others) in a SEPARATE cam/ change under its own review — deferred, not done in 431.

CONSTRAINTS: edit NO cam/ file (STEP 1a is READ-ONLY of cam/); all five semantic artifacts
byte-identical to 65556ee (confirm hashes); no new evaluation semantics; ZERO provider calls.
Rebuild package + manifest, mint FRESH token (superseding 833fd43e), keep build testable without
calls.

REPORT: STEP 1a's enumerated fatal allow-list with quoted adapter lines; the diff of both fixes;
no-call tests proving (1) a FatalProviderError on the A/B path halts the run, (2) a wrapped-fatal
ProviderError on the xAI path halts the run (stub raising a ProviderError matching the allow-list),
(3) a transient ProviderError on the xAI path still falls back (stub raising a non-matching
ProviderError), (4) F2 strips raw from the cert path; semantic-artifact hashes byte-identical to
65556ee; files changed (harness + manifest only); new token; zero calls; git status --porcelain
cam/ empty. Commit git add -f explicit paths, no push. STOP for delta re-audit.
