# Step 440-fix — STAGE-2 REPORT-LANGUAGE FIX (verbatim brief as received)

**Filed per Rule 7.** One minimal correction to the emitted Role-C §9 report language. No mechanism,
no fatal-handling, no F2, no semantic-artifact edits. Fresh token superseding ce284b55.

---

STAGE-2 REPORT-LANGUAGE FIX (Step 440-fix) — one minimal correction, ZERO model calls, fresh token,
stop for final delta audit. GPT audit verdict: ce284b55 DO NOT SANCTION — the emitted Role-C report
paragraph is stale and byte-wrong (says "structural absence of a needed check"; the bytes show xAI
INVOKES the check at line 764). Replace the heading and paragraph ONLY. No other change authorized.

In render_report() in run_431_selection_measurement.py, replace the stale Role-C heading and
paragraph.

REPLACE the heading (currently reads "structural absence, not a skipped check" or similar stale
text) WITH:
  Role C (grok-4.3) — shared integrity checking and structurally inapplicable omission branch

REPLACE the Role-C paragraph (currently contains "ran without omission-guard integrity
instrumentation" and "This is a structural absence of a needed check") WITH exactly:
  Role C (`grok-4.3`, canonical self-retry role) invokes the shared module-level outbound
  generation-integrity check and records the resulting integrity metadata. Its configured
  temperature is transmitted explicitly as `0`, and the xAI call path re-raises fatal integrity
  failures. Grok is outside `TEMPERATURE_ONLY_DEFAULT_MODELS`, so the conditional-temperature-omission
  branch is structurally inapplicable to Role C.

Confirm the emitted text contains NONE of the forbidden phrasings: "lacks an integrity check", "ran
without integrity checking", "inherits the integrity method", "wraps fatal integrity failures",
"structural absence", "xai-specific mechanism".

CONSTRAINTS: this is the ONLY change. No mechanism, no fatal-handling, no F2, no semantic-artifact
edits. Confirm the five reviewed semantic artifacts (prompt, schema, profiles, config,
fixtures/preflight) remain BYTE-IDENTICAL to 65556ee after. edit NO cam/ file. ZERO provider calls.

Then: re-run the deterministic zero-call tests; regenerate the manifest; mint a FRESH token
(superseding ce284b55).

REPORT: the exact diff (heading + paragraph only); the verbatim NEW emitted Role-C text; confirmation
none of the forbidden phrasings appear; deterministic tests pass with zero calls; the five
semantic-artifact hashes still byte-identical to 65556ee; the fresh token + updated chain (now ...→
ce284b55 → <new>); files changed (harness + manifest only); git status --porcelain cam/ empty. Commit
git add -f explicit paths, no push. STOP for final delta audit.

---

**Execution note:** the emitted paragraph is sourced from the module-level constant
`ROLE_C_INTEGRITY_REPORT_LANGUAGE` (which both `render_report` and the sidecar `role_c_integrity_note`
field draw from), so the paragraph was corrected there; the heading was corrected inline in
`render_report`; the constant's own descriptive comment (which had mis-said "STRUCTURAL ABSENCE") was
updated to match so it does not stale-describe the replaced text. The supersession chain +
authorizing_step were updated (as the brief's "updated chain" requires). No other harness change.
