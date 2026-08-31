# Step 504 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 504. Daily model check. Build the check first, scheduling after.
No new provider spend beyond the probe itself.

PART A — what exists. Report before building.
  1. Where is SendGrid configured and called? Is it live in production, or
     present-but-unwired like the 423 stack was? Quote the call site.
  2. What credential does it use, and is it set in Railway?
  3. Does anything currently send email successfully? If the PDF-results
     path is aspirational rather than working, say so.

PART B — the check itself
Standalone script, build_log/ or a tools dir — your call, state it.

For each model in the frozen panel and the pipeline:
  anthropic  claude-sonnet-4-6, claude-haiku-4-5 (role A fallback)
  openai     gpt-5.5
  xai        grok-4.3
  google     gemini-3.1-pro-preview (extractor), gemini-2.5-pro (pool)
  and the document gate's claude-sonnet-4-20250514

Two checks per model, because a models-list check would NOT have caught
the temperature break — Claude was still served, the SDK changed:

  1. Is it listed by the provider's models endpoint?
  2. Does one tiny call with THE PARAMETERS THE PIPELINE ACTUALLY SENDS
     succeed? Route it through the real ProviderRouter and adapter path,
     not a hand-rolled client, or it tests something the pipeline doesn't do.

Report per model: listed, callable, actual model served, is_fallback, any
lifecycle metadata the endpoint returns, and the RAW error on failure.
Raw, not classified — Step 502 established the classifier misdirects.

PART C — prove it discriminates
The gate's claude-sonnet-4-20250514 404s on every run. The check must fail
on it. If it passes, the check is not testing what it claims.

Report the output. Do NOT schedule it, do NOT wire email yet.
