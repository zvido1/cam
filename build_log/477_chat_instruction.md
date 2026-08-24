# Step 477 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 477. Make the degraded markers reach the user. Then deploy.

Step 476 established that nothing reads run_degraded — job_manager 0,
main 0, index.html 0, summary_generator 0 — so a degraded run currently
reports as a normal completed job. That is worse than the traceback it
replaces. Do not deploy until this is closed.

1. job_manager: fold the degraded markers into the job aggregate. Its
   has_any_degraded currently fires only on missing or unreadable results
   and never reads run_degraded. The job status a user polls must reflect
   that the report is incomplete.

2. Frontend: render incomplete_statement ABOVE the summary, not beside or
   below it. Step 461 recorded a counter improving while the answer got
   worse; the same reader who sees a summary first will see this first.

3. Anywhere else that consumes the result and would present it as complete.
   Report what you find rather than assuming those four are the whole set.

TEST
Re-run the degraded case locally and report what a user actually sees end
to end — job status, then the rendered page or its equivalent. Quote it.
Not the JSON: the JSON is already unmissable and that was never the problem.

Then, separately, ANSWER THIS BEFORE ANY DEPLOY DECISION:
LP-12's entry is identical clean vs degraded except the text hash. So the
gate rejects runs whose coverage output would have been the same. Is that
true for the OTHER LPs that fail the gate on divall — LP-07, LP-16, LP-17,
LP-30, LP-31, LP-32 — or is LP-12 special because the applicability layer
independently rules it not_applicable? Answer offline from the divall
extraction output if you can; say so if you cannot.

Do NOT deploy. Report and stop.

---

## Contradiction noted, resolved toward the explicit instruction

The heading says "Then deploy" and the closing line says "Do NOT deploy. Report and stop."
Executed as **no deploy**, per the explicit final line and the standing project default
("commit local, do not push" unless sanctioned in-session).
