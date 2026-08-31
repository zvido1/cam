# Step 506 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 506. Resolve the healthcheck interaction, then build.

PART A — answer your own flag first. No code.
  1. Does railway.toml or the Railway service configure a healthcheck path?
     Quote it. If none is configured, what does Railway do by default?
  2. If a healthcheck exists and points at a path that would return non-200
     on provider failure, that is the loop you identified. Report whether
     it does.
  3. Propose the separation: the startup assertion's result must be
     readable without any endpoint Railway polls for liveness. State how.
     A distinct path, a different status code convention, or something else
     — defend the choice.

  If this cannot be resolved safely, say so and stop. A monitor that can
  restart the container is worse than no monitor.

PART B — build the startup assertion, only if A is clean
  One call per provider at boot, through the real ProviderRouter and
  adapter path with the parameters the pipeline sends. Six models per
  Step 504, PROBE_OUTPUT_TOKENS=256.

  Record: per-model listed/callable/served/raw error, and the installed
  version of every pinned SDK.

  Default UNHEALTHY. Absence of a result is never a pass. The app STARTS
  regardless — log loudly, do not exit.

  Expose the cached result on a path Railway does not poll.

PART C — prove it discriminates
  It must report UNHEALTHY for claude-sonnet-4-20250514, which 404s today.
  If a fresh boot reports all-green, the check is not testing what it
  claims — same trap as the gemini false positive.

Do NOT wire alerting. Do NOT schedule the model check. Do NOT deploy.

---

## Note on Part B scope, recorded before execution

The brief says "six models per Step 504". Step 504's TARGETS list has **seven** entries — six
pipeline models plus the document gate's `claude-sonnet-4-20250514`. Part C requires the check to
report UNHEALTHY for that seventh, so all seven are probed. Read as six pipeline models + the gate.
