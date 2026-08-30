# Step 492 — Instruction

**Received:** 2026-08-30, from Tzvi in conversation, transcribed to disk before execution per
CLAUDE.md Reporting Integrity Rule 7. The brief was given as prose plus an answer to one
clarifying question from Code; both are recorded verbatim below.

---

## Tzvi, in conversation (verbatim extract)

> And divall
>
> Still never completed deployed, and it's the only fixture that would test whether any abort
> cause remains. Atlas's aborts were LP-12's, and that cause is now removed by design. Five
> Atlas runs can't tell you about a document with six or seven failing LPs.
>
> That's the measurement I'd want next, and it's one run.

## Clarifying question asked by Code, and the answer

**Q:** divall — local or deployed? Deployed needs a push I don't have sanction for.

**A: "Local first (recommended)"** — one divall run through `run_mode_c.py`, up to 4 gate
attempts. Needs no push. Directly answers the abort-cause question: divall aborted 4/4 in
Step 482 and 1/2 in Step 484, so it is the fixture with a live abort cause. Persists with
census like the Atlas three.

**Deployed divall is NOT authorized by this step.** No push. The "never completed deployed"
gap remains open.

## Standing constraints carried from Step 491

- Do NOT tune anything.
- Do NOT retry beyond four gate attempts.
- If the panel degrades mid-run, report it rather than continuing.
- Report against the same six headings: completions vs aborts and on which LPs; the provenance
  census; the seam LPs against prior divall observations; degraded markers and whether any user
  surface reflects them; calls and elapsed; and that the result persisted, with paths.
