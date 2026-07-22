# Step 432 — 431 Part B Stage-2 CALL-PATH IMPLEMENTATION (verbatim brief as received)

**Filed to disk per Reporting-Integrity Rule 7 (every step needs a written instruction) before executing.**
This is the Stage-2 call-path implementation of the 431 Part B governed-selection measurement. It is
given its own step number (432) because it is a discrete new brief that supersedes-for-EXECUTION the
frozen preregistration package `65556ee`; all 431 artifacts and their hashes are unchanged in meaning.

---

STAGE-2 CALL-PATH IMPLEMENTATION — implement only, ZERO model calls. Do NOT run the measurement.
This supersedes the frozen preregistration package 65556ee for EXECUTION; the reviewed semantic
artifacts must stay byte-identical so the blind reviews carry over unchanged.

CONTEXT: The sanctioned package 65556ee is a PREREGISTRATION package — its call path is
NotImplementedError by design. Executing requires writing the call path, which changes the harness
hash and voids token 47cb312a. That is expected and correct (GPT informed audit + Tzvi ruling):
implement the call path, rebuild, mint a NEW token, and STOP for a scoped informed audit before any
run. Read v3.3 §7/§8 and your own manifest note ("implement against _call_single_evaluator_305's
call/fallback/provenance shape under Stage-2 sanction, then re-hash") first.

IMPLEMENT (call path only):
1. Implement the Stage-2 call path in run_431_selection_measurement.py against the EXISTING frozen
   evaluator machinery. It MUST:
   - import the real EVALUATOR_LINEUP_305 (A=claude-sonnet-4-6, B=gpt-5.5, C=grok-4.3) and call
     through the real _call_single_evaluator_305 path — do NOT copy, approximate, or reimplement
     provider logic;
   - take Role A/B/C identity from the ACTUAL returned metadata, not from requested identity;
   - preserve gpt-5.5's temperature exception explicitly (provider-default temp, logged, not
     silently dropped);
   - treat canonicality correctly: only a same-model Grok self-retry at the FROZEN config is
     canonical; Haiku / gpt-5.4 / Gemini / any substituted model is preserved as DEGRADED audit
     evidence and EXCLUDED from canonical N; is_fallback alone never infers canonicality; provider
     + model + config_hash all participate in the canonical decision;
   - send each call exactly one candidate + its deterministic envelope + neutral family label +
     applicability dimensions + the reviewed schema — nothing appended, no schema/label/fixture/
     expected-outcome text injected at runtime; panelists never see each other's outputs;
   - retain raw provider responses and parse failures; invalid JSON / missing fields / unresolved
     citations / grounding failures follow the REVIEWED rules — no meaning-changing "repairs";
   - assign raw_attempt_index / canonical_attempt_index / series_index exactly as preregistered
     (§7); retries cannot shop for a preferred result; enforce same-series pairing; ceiling
     produces an honest canonical-N shortfall, not a silent top-up;
   - keep the pre-first-call manifest+token gate and the in-process runtime seam capture
     (before first call / after last call).
2. Do NOT touch the semantic artifacts: 431_selector_prompt.txt, 431_output_schema.json,
   431_requirement_profiles.json, 431_measurement_config.json, the fixtures/preflight. Confirm
   their hashes are BYTE-IDENTICAL to 65556ee after the rebuild. Certification stays in the
   reviewed validator — do NOT compute any relevance/basis/role/value/support/applicability
   judgment inside the call loop, and introduce no majority behavior.
3. Rebuild the executable package + manifest, mint a FRESH sanction token, and record that
   47cb312a is superseded-for-execution (retained as evidence the preregistration was sanctioned).
4. The executable must remain testable WITHOUT firing calls (a build/dry path that does not hit
   providers). Verify the call path exists and is wired, but make ZERO provider calls in this step.

VERIFY + REPORT (make NO run):
- semantic-artifact hashes byte-identical to 65556ee (list each);
- which files changed (expected: harness + manifest only);
- the new token;
- confirm zero provider calls made, git status --porcelain cam/ empty;
- produce the exact diff of the call-path implementation and the final harness, ready for a scoped
  informed audit.
Commit with git add -f explicit paths, no push. Then STOP. Do not run the measurement. The run
happens only after the scoped audit clears and Tzvi sanctions the new token.
