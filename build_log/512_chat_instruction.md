# Step 512 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 512. Wire alerting. The contract can now report its own failure.

PART A — the trigger set, per Step 505's design
Key on the PER-MODEL set, never the summary status. Step 507's standing
unhealthy is the argument: a summary says "red", the set says which moved.

Loud:
  - a model goes healthy -> unhealthy, two consecutive checks
  - any listed=False, immediately, no consecutive requirement — retirement
    is never transient
  - any SDK version change between deploys, even when every call passes.
    That is the August 26 signal, visible before it breaks anything.
Silent otherwise. Alert on state change, not state.

State where the previous state is stored and what happens on a cold start
with no prior state — that must not fire on first boot.

PART B — send it, and record whether it sent
Use the Step-511 contract. The alert dispatch must capture
{"sent", "channel", "reason"} and log it — an alerting system that
discards its own send result is the defect this step exists past.

If an alert fails to send, that failure must be visible somewhere a human
would look. Say where and defend it.

PART C — prove it discriminates, without emailing anyone
Stub the transport, as in Step 511. Exercise:
  - first boot, no prior state -> silent
  - all healthy, unchanged -> silent
  - one model unhealthy, first occurrence -> silent
  - same model unhealthy, second consecutive -> ALERT
  - listed=False -> ALERT immediately
  - SDK version changed, all calls passing -> ALERT
  - alert send fails -> the failure is recorded, not swallowed

Quote what each produces. The near-miss to avoid is Step 504's gemini false
positive: a monitor that cries wolf is worse than none.

Also record the two Step-511 flags in the status: dict-always-truthy, and
notification_* reaching the endpoint by a different mechanism than
_JOB_QUALITY_FIELDS.

Do NOT send a real email. Do NOT deploy.
