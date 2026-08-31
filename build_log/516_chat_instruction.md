# Step 516 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 516. Make a run aware of provider health at its start.

Today the boot assertion runs once per container. A run submitted later
inherits that verdict without re-examining it, and discovers a provider
failure mid-pipeline via fallback — one LP at a time, silently. That is
the August 26 shape: the runs completed.

DESIGN FIRST, report before building.

1. What should a run do when it starts and provider health is bad?
   Three shapes, and I want your recommendation, not a menu:
     - refuse to start, telling the user why
     - start, but mark the result degraded before any work happens
     - start, and warn only
   Consider that a report produced on a substituted panel is not the
   product the user asked for — but also that refusing on a transient blip
   costs them a run they could have had.

2. Should it RE-CHECK, or read the cached boot verdict?
   A re-check costs 7 calls per run against ~96 — under 8%. A cached
   verdict is free but can be hours stale, which is the defect.
   State which and defend it. If re-check, say whether it blocks the run
   or races it.

3. Which failures should stop a run versus mark it?
   A role-A seat entirely unavailable is not the same as one transient
   fallback on one LP. Step 512 already has a threshold for alerting —
   reuse it or say why a run needs a different one.

4. Where does this live? The pipeline entry, the job manager, or the API
   route that accepts the submission. It must be a place a run cannot
   bypass — Step 504 found SendGrid wired but never verified, and the
   423 stack built but never called.

5. What does the user see? If a run is refused, the message must say which
   provider and that it is not their document's fault. If it proceeds
   marked, it must use the Step-497 disclosure surfaces rather than a new
   one.

Do NOT build. Report the design and your recommendation.
