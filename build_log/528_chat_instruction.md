# Step 528 — Instruction

**Received:** 2026-09-02, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 528. Make truncation observable. No architectural change.

_repair_truncated_json computes `repaired` at line 275 and discards it.
safe_json_extract returns the parsed object with no indication a repair
occurred. So a truncated extraction that repairs into valid JSON is
indistinguishable from a complete one, and Step 527 could not answer
whether Atlas or divall ever truncated because nothing was recorded.

1. Surface the repair. Every path that repairs must say so — the caller
   must be able to distinguish "parsed cleanly" from "parsed after
   repair". State the contract you choose and why, following Step 511's
   rule: never return a bare success for something partially done.

2. Record finish_reason and token usage on the extraction result. If
   MAX_TOKENS, that fact belongs in the run record, not only a log.

3. A repaired extraction must mark the run. It is not a clean result and
   the user should not receive it as one. Use the existing degraded path
   from Steps 476-478 — do not build a new surface.

4. VERIFY BY EXERCISE, providers stubbed:
   - complete JSON -> no repair flag
   - truncated, repairable -> repaired flag set, run marked
   - truncated, unrepairable -> the existing failure path
   - each of the eight return paths in safe_json_extract -> does each
     correctly report whether it repaired?
   Quote each.

5. Then re-run solidpower. It should now FAIL VISIBLY rather than
   producing 5 of 33 provisions with a passing gate. Report what the user
   sees.

Do NOT attempt chunked extraction. Do NOT raise any limit — 8,192 is the
model ceiling and cannot be raised.
