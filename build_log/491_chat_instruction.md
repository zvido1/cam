# Step 491 — Instruction

**Received:** 2026-08-26, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 491. Abort rate + harness proof. Three Atlas runs.

FIRST, before any run: verify the panel end to end. Step 487's runs had
role A served by gemini-2.5-pro on both, and nothing in the output said so.

Make one cheap call per role through the real ProviderRouter and adapter
path — anthropic:claude-sonnet-4-6, openai:gpt-5.5, xai:grok-4.3. Report
each: served model, is_fallback, elapsed, and the RAW error if any fails.

If role A still falls back: HALT and report. Three runs on a substituted
panel measure a two-model panel's abort rate, which is not the question.

THEN, three Atlas runs through run_mode_c.py — full-LP Mode C, canonical,
sequential, up to four gate attempts each. This is the harness's first real
invocation; if it fails, that is the finding and stop.

REPORT
  1. Completions vs aborts, and on which LPs. Three runs plus Step 487's
     two gives five deployed observations under this configuration.
  2. Per run, the provenance census from run_store: stubs, contradictions,
     distinct_ts, served-model counts per role.
  3. LP-07, LP-12, LP-27 against the Step-484 local runs and Step-487's
     deployed ones. Byte-identical elements_found, or what moved.
  4. Any run marked degraded, by what reason, and whether anything the user
     would see reflects it.
  5. Calls and elapsed per run.
  6. That every result persisted, with paths.

Do NOT tune. Do NOT retry beyond four gate attempts per run. If the panel
degrades mid-run, report it rather than continuing to a fourth run.
