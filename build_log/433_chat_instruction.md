# Step 433 — 431 Part B Stage-2 CALL-PATH FIXES (verbatim brief as received)

**Filed to disk per Reporting-Integrity Rule 7 before executing.** Two fixes from GPT's scoped
audit of the 432 call path (CLEAR-WITH-FIXES). Implement only, ZERO model calls, new token, stop
for delta re-audit. Do NOT run. Semantic artifacts stay byte-identical to 65556ee.

---

STAGE-2 CALL-PATH FIXES (Step 433) — two fixes from GPT's scoped audit (CLEAR-WITH-FIXES).
Implement only, ZERO model calls, new token, stop for delta re-audit. Do NOT run. Semantic
artifacts stay byte-identical to 65556ee.

CONTEXT: GPT's scoped audit of the 432 call path returned CLEAR-WITH-FIXES. Ruling #1 (shape-not-
literal provider reuse) AFFIRMED; canonicality, payload, no-repair, series, no-new-semantics all
confirmed correct. Two fixes required before the run:

FIX V3 (BLOCKING — highest priority): the call path calls router._get_adapter(provider) then
adapter.call(...) DIRECTLY, bypassing the router public path where _check_generation_integrity runs
(the 416 assertion that catches silent temperature drift / config omission). As written, the
measurement calls would fire WITHOUT 416's integrity protection — the exact silent-config-drift
failure class 415/416 exists to prevent.
  - Fix: route the 431 provider call through the SAME entry point _call_single_evaluator_305 uses
    that triggers _check_generation_integrity, OR invoke the integrity assertion explicitly on the
    outbound payload before/at the adapter call, so EVERY 431 call gets the config-integrity check.
  - Do NOT reimplement the integrity check — call the real one from cam/core (imported, not copied).
  - Verify: after the fix, a call with a mismatched/omitted temperature would RAISE the integrity
    error (add a no-call unit test that asserts the integrity path is invoked — e.g. a stub adapter
    whose integrity record is checked, or assert the code path reaches the assertion). The point is
    that 416's protection is now ACTIVE on 431 calls, provably.

FIX F2: raw_response is retained on the certified panel result, so raw model/lease text flows into
merge_panel/certification and into the certification trace.
  - Fix: keep raw_response (and raw attempt text) in the AUDIT layer only — the attempts[] list and
    degraded_panels — and STRIP it from the object that feeds certify_parameter_series /
    merge_panel / compare_candidate and from the per-candidate certification_trace. Certification
    consumes ONLY the parsed, grounded judgment, never the raw response.
  - Verify (no call): a unit check that the object passed into merge_panel/certify carries no
    raw_response field, and that the certification_trace per_candidate entries carry no raw text.

CONSTRAINTS (unchanged): edit NO cam/ file; keep all five semantic artifacts (prompt, schema,
profiles, config, fixtures/preflight) BYTE-IDENTICAL to 65556ee — confirm hashes after. These fixes
touch ONLY the harness call/provenance path. Introduce no new evaluation semantics. Zero provider
calls in this step.

Then: rebuild the executable package + manifest, mint a FRESH token (superseding 833fd43e for
execution), keep the build testable without calls. Report: the exact diff of BOTH fixes;
confirmation V3 now routes through / invokes _check_generation_integrity (with the no-call test
result proving the assertion is reachable); confirmation F2 strips raw_response from the
certification path (with the no-call test result); semantic-artifact hashes byte-identical to
65556ee; files changed (expect harness + manifest only); the new token; zero calls; git status
--porcelain cam/ empty. Commit git add -f explicit paths, no push. STOP for the delta re-audit —
do not run.
