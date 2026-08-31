# Step 508 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 508. Fix the dead gate model. Then production is green.

cam/adapters/lease_review/lease_gate.py:49 defaults to
claude-sonnet-4-20250514, which 404s on every run. The document classifier
has been silently running on its fallback for as long as that id has been
retired — Step 491 found it, five steps have recorded it, nothing has
fixed it.

1. What does the gate do when the model call fails? Quote the fallback.
   It returns is_lease=True — establish whether that is a considered
   default or an accident. A classifier that defaults to "yes" would pass
   a non-lease document straight through.

2. Choose the replacement. It should be the model the pipeline already
   uses for role A, or state why a different one. Report what
   model_config.py:68 maps that retired id to — Step 491 found it labelled
   "Claude Sonnet 4.6", a label naming a current model for a retired id.
   Fix that too, or say why not.

3. Verify by call, not by config read: does the new id resolve, and does
   the gate classify Atlas as a lease and something that is not a lease as
   not a lease? If no non-lease fixture exists, say so rather than
   claiming the negative case is tested.

4. Re-run the startup assertion locally. It must now report HEALTHY on all
   seven targets. If it does not, report which and stop.

5. Push. Preflight as before, branch only, no tags.

6. Confirm production reports healthy via the authenticated endpoint.

Only then is alerting worth wiring — and it should key on the per-model set
regardless, since a summary status hides which target moved.
