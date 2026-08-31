# Step 507 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 507. Gate /api/provider-health, then deploy.

PART A — gate it
Anonymous: HTTP 200, body carries `status` only.
Authenticated via the existing access-code mechanism: the full body —
per-model listed/callable/served, raw errors, installed SDK versions.

Always 200 either way. The status code stays the platform channel.

Use the access-code path the app already has; do not invent a second auth
mechanism. Report which one and quote the call site.

Verify by request, not by code reading — three consecutive steps have
caught defects a static read missed. Exercise both the anonymous and
authenticated paths against the real app and quote both response bodies.

PART B — deploy
Preflight as before: fetch, unpushed count, deployable commits, the six
flags from HEAD, tests against HEAD, branch only, no tags.

This carries the startup assertion, the gated endpoint, the model check
script and the Step-502 dependency bounds.

PART C — observe it in production
After the Railway rebuild, request /api/provider-health authenticated.

REPORT
  1. The full body. Does it report the six pipeline models callable and
     claude-sonnet-4-20250514 unhealthy — the same discrimination Part C
     of Step 506 proved locally?
  2. The installed SDK versions in production. This is the first time
     that has ever been observable. Do they match what requirements.txt
     now pins?
  3. Did the startup assertion delay the boot, and by how long?

Do NOT wire alerting. Do NOT schedule the model check.
