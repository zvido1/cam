# Step 502 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 502. Prevent the SDK-break class. Three causes, three fixes.

Step 501 established: anthropic 1.0.0 removed temperature from
Messages.create(); requirements.txt said >=0.78.0 with no ceiling; Railway
rebuilds on every push; every deployed Anthropic call has failed since
2026-08-26. It hid for five days because local ran 0.75.0 — BELOW the
declared floor — so local never ran what production runs. And it sent the
investigation to the billing dashboard because _classify_failure matched a
substring inside "anthropic_error:" and labelled a client-side TypeError as
api_error.

PART A — bound the dependencies
Pin every dependency in requirements.txt to a range with an upper bound.
Report the currently-resolving version of each BEFORE choosing bounds, and
use it — do not guess at what is safe.

Twelve are unbounded: openai>=2.0.0, google-genai, fastapi, PyMuPDF and the
rest. Report the full list with current versions.

Then confirm 367 tests pass against the pinned set, and report any
dependency where the pin CHANGES what is installed locally — that is
drift you are correcting, and it should be visible.

PART B — make local match production
Local was below the declared floor. Nothing detected that.

Propose a check that fails loudly when the local environment does not
satisfy requirements.txt. State where it belongs — test suite, harness
preflight, or a standalone script — and defend the choice. It must run
without network access and without a deploy.

Then run it and report what it says about the current environment.

PART C — stop the classifier lying about where a failure happened
_classify_failure asserted the call reached the API when it never left the
process. Report the exact matching logic and why the substring fired.

Then: a client-side exception raised before any request must not be
classified as an API error. Propose the distinction and where it belongs.

The raw error is NOT lost — lease_coverage_305.py:611 prints it, which
Step 488 wrongly said was gone. Persisting it alongside the class is the
open item from Step 488; state whether Part C should close it or whether
that remains separate.

Do NOT deploy. Report and stop.
