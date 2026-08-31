# Step 509 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 509. Close both gaps, then alerting is worth wiring.

PART A — a non-lease fixture
Add one, checked in, so the gate has a regression test that can fail.
It must be plausible enough to be a real negative — a document someone
might actually upload by mistake — not a recipe. A software licence, an
NDA, an employment agreement, a services contract. Say which and why.

Then a test that asserts: lease fixtures classify is_lease=True, the
non-lease fixture classifies False. It will make one provider call per
case, so keep the fixture set small and say what the test costs to run.

If the suite must stay call-free, say so and propose where this lives
instead — a marked test, a harness, or the model check script.

PART B — exercise lease_template_reader
Call /api/template/summary against the new model, locally and then
deployed. Report the actual summary body, not that it returned 200.

If it comes back empty or malformed on claude-sonnet-4-6, that is the
finding — the id resolving is not the same as the call working.

PART C — alerting, only if A and B are clean
Key on the PER-MODEL set, not the summary status. Step 507's standing
unhealthy is the argument: a summary says "red", the set says which target
moved.

Triggers, per the Step-505 design:
  - healthy -> unhealthy on a given model, two consecutive checks
  - any listed=False, immediately, no consecutive requirement
  - any SDK version change between deploys, even when every call passes
Silent otherwise.

Send via the existing SendGrid path. But Step 504 found it returns True
when unconfigured and job_manager.py:1683 discards that — so first
establish whether SendGrid has ever sent from production. If it hasn't,
that is a prerequisite, not a detail.

Report A and B before building C.
