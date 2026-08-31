# Step 505 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 505. Where the checks belong. DESIGN, then build. No scheduling yet.

Step 504 established the local model check gives API health, not deployment
health — it would NOT have caught the 2026-08-26 break, because Claude was
listed and served fine and Railway's SDK was the problem.

1. Grep the Railway log for "Email not configured". Report whether
   SendGrid has ever sent from production, or has been returning True
   into a discarded value since March.

2. Propose where each check runs, and defend it:
   - the model check (tools/check_models.py) — API health
   - the Step-502 requirements drift test — deployment health
   Only the second would have caught August 26, and only if it runs in
   the deployed environment.

   State plainly what a green result from each does and does NOT mean.

3. Propose the deployed-health check. What is the smallest thing that
   runs IN production and would have caught the temperature break on the
   day it happened? Consider: a startup assertion, a health endpoint that
   makes one real call per provider, or a scheduled job. State the cost of
   each and which you would choose.

   It must fail loudly. Step 504's SendGrid defect and every other in this
   arc is something returning success on an unconfigured or broken path.

4. Alerting. Only after 1-3. What triggers an email, what stays silent, and
   how do you avoid the daily-noise failure that the gemini false positive
   nearly caused?

Report the design. Do NOT schedule, do NOT wire email, do NOT build the
deployed check yet.
