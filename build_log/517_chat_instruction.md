# Step 517 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation.

**RULE 7 SLIP, recorded rather than hidden.** CLAUDE.md Reporting Integrity Rule 7 requires the
instruction be written to disk *before* execution. This file was written *after* the step's work was
complete, when `git add` failed on the missing path. The text below is the brief verbatim as received;
nothing was reconstructed from memory of what was done. But the ordering guarantee — that the brief
could not have been shaped to fit the outcome — does not hold for this one file, and saying so is the
point of the rule.

---

Step 517. Build the run preflight. Design per Step 516.

Mark degraded by default. Refuse only when the panel cannot be assembled
at all — no primary, no fallback, no pool — or the extractor is entirely
down. Blocking re-check, 5-minute TTL, at pipeline entry, beside
tools/check_models.py so cam/ imports nothing from the app.

Add Step 516's field: substitution KNOWN AT START, distinct from
discovered mid-run. That distinction is the difference between "we found
out" and "we knew and proceeded", and it should survive into the record.

Record the dissent in the code, not only in the status: a comment at the
decision point stating that mark-degraded is the default because no
submission-time consent surface exists, and that a user is being told
afterwards they received a different product than the one named. If that
surface is ever built, this default should be revisited.

VERIFY BY EXERCISE, transport and providers stubbed, no real calls:
  - all healthy -> proceeds, no mark
  - one role substituted but assemblable -> proceeds, marked, known-at-start
  - panel unassemblable -> REFUSED, and the message names the provider,
    says it is not the document's fault, and does NOT claim nothing was
    charged
  - extractor entirely down -> REFUSED
  - TTL live: second run within 5 minutes makes no calls
  - TTL expired: re-checks
  - preflight itself errors -> what happens? It must not fail open. State
    what it does and defend it.

Then ONE real Atlas run through run_mode_c.py. It should proceed unmarked,
and cost 7 calls more than the Step-503 baseline. Report both numbers.

Do NOT deploy.
