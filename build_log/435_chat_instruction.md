# Step 435 — STAGE-2 CALL-PATH FIXES (Chat labeled this "Step 433"; filed as 435) — verbatim brief + STEP 0 gate

**Filed to disk per Reporting-Integrity Rule 7 before executing.**
**Numbering note:** Chat labeled this brief "Step 433," but Steps 433 and 434 are already committed
(`45b94ce`, `a504cc9`). This brief post-dates and REFINES them (it acknowledges V3 is withdrawn,
which was the 434 finding). Filed as 435 to keep a clean, non-clobbering audit trail. FIX 1 is
gated by a STEP 0 verification that I completed and that returns STOP-AND-REPORT (see 435 status).

---

STAGE-2 CALL-PATH FIXES (Step 433) — implement two fixes from GPT's scoped audit, ZERO model
calls, new token, stop for delta re-audit. Do NOT run. V3-as-specified is WITHDRAWN (confirmed:
ProviderRouter has no route()/_check_generation_integrity; the harness already inherits 416's
adapter-level check). Two real fixes remain.

STEP 0 — VERIFICATION THAT GATES FIX 1 (read code first, do NOT assume):
Read OpenAIAdapter.call (and the other adapters' .call) in cam/core/provider_router.py. Determine:
when _check_generation_integrity raises FatalProviderError (temperature/config violation), does
that exception PROPAGATE OUT of adapter.call() AS FatalProviderError — or does adapter.call() have
an outer except that WRAPS it into a generic ProviderError / other type before it reaches the
caller?
- Report the exact answer with the relevant lines quoted.
- If FatalProviderError (and ProviderPermanentError) propagate uncaught as their own types →
  FIX 1 as written below works. Proceed.
- If the adapter WRAPS them into a generic type → the harness cannot re-raise what it never
  receives. STOP and report: FIX 1 must instead key on a structured fatal classification the
  adapter DOES expose (or the adapter boundary must preserve the fatal type). Do NOT implement a
  re-raise of a type that never arrives — that would be a fix that looks correct and does nothing.
  Bring the finding back before implementing.

FIX 1 (implement only if STEP 0 confirms the fatal types propagate) — halt-on-fatal:
- In call_panelist, in BOTH the own-chain traversal AND the shared-fallback-pool traversal, add
  `except (FatalProviderError, ProviderPermanentError): raise` BEFORE the generic `except Exception`
  handler, so a fatal/permanent error is re-raised, never classified as a degraded attempt and
  never triggering fallback. Match the real _call_single_evaluator_305 treatment exactly.
- The fatal must be FATAL TO THE WHOLE RUN, immediately: do not finish the current candidate, do
  not try another role, do not try own-chain or pool fallback, do not defer to candidate end.
- In run_stage2, wrap the measurement body so the fatal propagates but audit surfaces still close
  via finally: capture seam_before before the try; on (FatalProviderError, ProviderPermanentError)
  persist a terminal fatal-run-error record then re-raise; in finally, capture seam_after and
  persist the runtime seam + whatever partial sidecar/attempt audit exists. The terminal record
  identifies: role + candidate active at the fatal; requested provider/model; fatal exception type
  + message; whether any earlier calls completed; that NO fallback was attempted after the fatal;
  and the partial sidecar + runtime seam locations.

FIX 2 (F2, unaffected — implement) — strip raw_response from the certification path:
- Keep raw_response and raw attempt text in the AUDIT layer only (attempts[], degraded_panels).
  STRIP raw_response from the object that feeds certify_parameter_series / merge_panel /
  compare_candidate and from the per-candidate certification_trace. Certification consumes ONLY the
  parsed, grounded judgment.
- Verify (no call): a check that the object passed into merge_panel/certify carries no
  raw_response, and that certification_trace per_candidate entries carry no raw text.

CONSTRAINTS: edit NO cam/ file (STEP 0 is READ-ONLY of cam/); all five semantic artifacts
byte-identical to 65556ee (confirm hashes); no new evaluation semantics; ZERO provider calls.
Rebuild executable package + manifest, mint FRESH token (superseding 833fd43e for execution), keep
build testable without calls.

REPORT: STEP 0's finding with quoted adapter lines (this determines whether FIX 1 is as-written or
needs the structured-classification variant); the diff of both fixes; a no-call test proving
FatalProviderError now propagates to a run halt (e.g. a stub adapter that raises it, asserting the
harness re-raises rather than falls back) AND a no-call test that F2 strips raw from the cert path;
semantic-artifact hashes byte-identical to 65556ee; files changed (harness + manifest only); the
new token; zero calls; git status --porcelain cam/ empty. Commit git add -f explicit paths, no
push. STOP for delta re-audit.
