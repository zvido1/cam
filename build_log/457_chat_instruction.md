# Step 457 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 457. Measure the Step-455 locator prefix. MEASUREMENT ONLY.
No tuning, no seam changes, no design decision.

FIRST — confirm the panel is intact before spending a run.
The last two runs had ~97% of role-B verdicts served by fallback
gemini-2.5-pro after OpenAI credits ran out six verdicts in. Credits are
topped up. Verify gpt-5.5 is actually serving before the full run:
make one cheap call and report the model and is_fallback. If it falls back,
STOP — another degraded run is uninterpretable.

THEN — three runs, unchanged configuration.
Full 33-LP Atlas Mode C, canonical, SPAN_EVIDENCE_LPS={"LP-07","LP-27"},
locator prefix ACTIVE. Up to four gate attempts per run.

THE QUESTION
Do LP-27's eight suppressed elements survive the citation gate now?

Per run, for LP-27:
  - how many of the 10 elements land in elements_found / elements_missing
    / neither (unclear)
  - for each element that is still unclear, the merge `reason` — is it
    still citation_required_but_absent, or something else
  - the raw section_ref each evaluator returned. Are they the locators the
    prefix supplied, or invented strings?
  - coverage_state, materiality, confidence

And for LP-07:
  - is proportionate_share_calculation still in elements_found
  - what section_ref did the evaluators return — the locator "Section 1.2"
    that the offline check produced, or the "Paragraph 1" /
    "Proportionate Share definition" strings from before?

That last one is the sharpest test. Before the locator, LP-07 passed the
gate on manufactured labels. If it now cites the supplied locator, the
prefix is doing the work rather than luck.

Also report per run: role-B model and fallback census across all verdicts,
call count, elapsed, gate aborts.

Do NOT tune the locator, the prefix format, or the assembly to improve the
result. Report whichever way it lands.
