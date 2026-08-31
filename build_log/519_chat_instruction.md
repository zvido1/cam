# Step 519 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 519. Should production retry a gate abort? DESIGN, no build.

Every divall completion in this arc came on a retry — attempt 2 locally at
Step 496 and 504. Production makes one attempt and fails the job. So a lease
that would complete on a second try fails outright for a real user.

The cause is LP-07's shape variance: extraction returns different provision
boundaries run to run, and some shapes leave LP-07 empty. Step 464
established three stable attractors at temperature 0 with decoding
configuration ruled out. Nothing has addressed that.

1. Should production retry? Argue both sides.
   For: the failure is known-transient, the retry is one extraction call
   (~100s), and the alternative is telling a user their valid lease cannot
   be processed.
   Against: a retry that succeeds hides a defect, and Step 465 established
   that the shapes which SURVIVE the gate are sometimes the shapes that
   LOST content — shape A cross-files §13.2 into LP-12 while dropping the
   22.4% definition. Retrying until the gate passes may select for the
   worse extraction.

   That second point is the one I want weighed properly. A retry policy
   that optimises for completion may be optimising against correctness.

2. If retry: how many attempts, and what does the user see during and
   after? Does the result record that it took N attempts, and which shape
   it landed on?

3. If not retry: what does the user get instead? Currently a raw
   completeness-failure message. Step 476-478 built a degraded path for
   applicability; this is a different case — the LP is applicable and the
   evidence is genuinely absent from the extraction.

4. Is there a third option? Seaming LP-07 was already considered — it is
   in SPAN_EVIDENCE_LPS, and Step 518 shows it still failed. Report why
   the seam did not save it, because that is not obvious.

Do NOT build. Report the design and your recommendation.
