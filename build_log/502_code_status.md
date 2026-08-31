# Step 502 — Three causes, three fixes. Two more below-floor packages found.

**Date:** 2026-08-30 · **Instruction:** `build_log/502_chat_instruction.md`
**Tests 369 passed** (367 + 2 new). **Not deployed.**

---

# PART A — BOUND THE DEPENDENCIES

## A.1 Currently-resolving versions, measured before choosing any bound

```
declared                     installed              spec
--------------------------------------------------------------------------
fastapi                      0.124.4                >=0.110.0            <-- UNBOUNDED
uvicorn[standard]            0.34.3                 >=0.27.0             <-- UNBOUNDED
python-multipart             0.0.22                 >=0.0.6              <-- UNBOUNDED
python-dotenv                1.2.1                  >=1.0.0              <-- UNBOUNDED
anthropic                    0.125.0                >=0.78.0,<1.0.0      (bounded at Step 501)
openai                       2.8.1                  >=2.0.0              <-- UNBOUNDED
google-genai                 1.52.0                 >=1.74.0             <-- UNBOUNDED  ** BELOW FLOOR **
httpx                        0.28.1                 >=0.27.0             <-- UNBOUNDED
google-api-python-client     2.187.0                >=2.100.0            <-- UNBOUNDED
google-auth                  2.49.1                 >=2.23.0             <-- UNBOUNDED
python-docx                  0.8.11                 >=1.1.0              <-- UNBOUNDED  ** BELOW FLOOR **
PyMuPDF                      1.26.0                 >=1.24.0             <-- UNBOUNDED
reportlab                    4.4.1                  >=4.0.0              <-- UNBOUNDED
```

**Twelve unbounded, as the brief said — and TWO MORE below their declared floor,
the same defect as `anthropic`:**

- **`google-genai` 1.52.0 against a floor of 1.74.0.** This is the extractor *and* the shared-pool
  fallback — the model that stood in for Claude on every deployed run.
- **`python-docx` 0.8.11 against a floor of 1.1.0.** A full minor-series behind; this drives the
  DOCX annotator.

**Three of thirteen dependencies were below their own declared floor and nothing said so.**

## A.2 Drift corrected — what the pin CHANGED locally

| package | before | after | note |
|---|---|---|---|
| `anthropic` | 0.75.0 | **0.125.0** | Step 501; was below floor |
| **`google-genai`** | **1.52.0** | **2.20.0** | **crossed a MAJOR boundary** |
| **`python-docx`** | **0.8.11** | **1.2.0** | crossed a major boundary |

**`google-genai` jumping 1.52.0 → 2.20.0 is the `anthropic` scenario repeating.** The floor allowed
1.x, no ceiling existed, and a fresh resolve lands on 2.x — **which is what Railway has been
installing.** I tested it rather than assuming:

```
google-genai 2.20.0 | anthropic 0.125.0 | openai 2.8.1
   google    gemini-2.5-pro             OK  2.10s
   google    gemini-3.1-pro-preview     OK  1.31s
   anthropic claude-sonnet-4-6          OK  1.11s
   openai    gpt-5.5                    OK  2.41s
   xai       grok-4.3                   OK  2.11s
```

**All five live provider calls succeed on the upgraded set.** `google-genai` 2.x did **not** break the
adapter — unlike `anthropic` 1.x. Recorded so nobody infers that a major bump is always fatal.

## A.3 The policy, stated rather than assumed

```
ceiling = the next breaking boundary above the VERIFIED version:
          next major for >=1.0 packages, next minor for 0.x
          (0.x makes breaking changes in minors -- anthropic 0.125.0 -> 1.0.0
           is the case in point, and fastapi/httpx behave the same way)
floor   = the existing declared floor, RAISED only where the verified version
          sits in a different major than that floor allowed
```

Only `google-genai` needed a raised floor (1.74.0 → 2.0.0): 2.20.0 is the version actually exercised,
and the old floor admitted a 1.x that was not.

**Tests against the pinned set: 369 passed.**

---

# PART B — MAKE LOCAL MATCH PRODUCTION

## B.1 The check, and why it is a test

`cam/adapters/lease_review/tests/test_502_environment_matches_requirements.py` — two tests:

1. **every declared dependency is installed and satisfies its spec** — the check that would have
   caught `anthropic` 0.75.0 under a `>=0.78.0` floor;
2. **every dependency has an upper bound** — so an unbounded `>=` cannot be reintroduced silently.

**Why the test suite and not a harness preflight or a script**, since the brief asked me to defend it:

- **A harness preflight only runs when someone runs the harness — and the harness is what produced
  the six misleading local runs.** It would have been checking the environment it was already
  misreporting from.
- **A standalone script only runs when someone remembers it.** Nobody remembered for five days.
- **The suite runs on every step**, its output is quoted in every status file, and CLAUDE.md forbids
  marking a step COMPLETE without pasting real test output. **A drifted environment now cannot reach
  a status file unnoticed.**

**No network, no deploy:** it compares `requirements.txt` against installed metadata via
`importlib.metadata`. It never contacts an index and never asks what the newest version is — only
whether what is installed satisfies what is declared.

**What it deliberately does NOT do:** assert that local and production resolve to the *same* version.
That cannot be checked without querying the deployed service. Bounding every dependency (Part A) is
what narrows the band; this test enforces that local sits inside it.

## B.2 What it says about the current environment

```
2 passed in 0.07s
```

**And it discriminates** — replaying the pre-502 state:

```
anthropic>=0.78.0        installed 0.75.0    satisfies: False
google-genai>=1.74.0     installed 1.52.0    satisfies: False
python-docx>=1.1.0       installed 0.8.11    satisfies: False
-> the pre-502 environment would have FAILED on all three.
```

---

# PART C — STOP THE CLASSIFIER LYING ABOUT WHERE A FAILURE HAPPENED

## C.1 The exact matching logic, and why the substring fired

`cam/core/provider_router.py:474` wraps **every** adapter exception the same way:

```python
            msg = f"anthropic_error: {type(e).__name__}: {e}"
```

The same pattern exists for `openai_error:` (`:415`), `google_error:` (`:722`), `xai_error:` (`:773`),
`openrouter_error:` (`:839`).

`_classify_failure` then tested, as its **first** substantive clause:

```python
    if ("_error:" in m or "timeout" in m or "timed out" in m or "rate" in m
            or "429" in m or "connection" in m or "unauthorized" in m
            or "401" in m or " 500" in m or " 502" in m or " 503" in m):
        return "api_error"
```

**`"_error:"` matches the provider prefix that every wrapped exception carries.** It does not detect
an API error — it detects *"this came from an adapter."* And being first, **it shadowed every clause
below it** for any wrapped provider exception: truncation, malformed and empty-content messages
arriving with a provider prefix would all have been swallowed as `api_error` too.

## C.2 The distinction, and where it belongs

**A builtin exception type can only be raised inside this process.** The wrapped message already
carries the type name, so the test is available without new plumbing:

```python
_CLIENT_SIDE_EXCEPTIONS = (
    "typeerror", "attributeerror", "nameerror", "importerror",
    "modulenotfounderror", "indexerror", "keyerror", "syntaxerror",
    "unbounderror", "notimplementederror",
)
```

Checked **before** the `_error:` clause, returning a new class **`client_error`**. Deliberately
narrow: SDK exceptions (`APIStatusError`, `RateLimitError`, `APIConnectionError`, `APITimeoutError`)
are **not** in the list — those did reach, or did try to reach, the network.

**Where it belongs — and a caveat.** I put it in `_classify_failure`
(`cam/adapters/lease_review/lease_coverage_305.py`). **The structurally better home is the wrap site
in `provider_router`**, where the exception object is in hand and no string parsing is needed. I did
not put it there: `cam/core/` is frozen for epistemic changes without explicit authorization, and how
a failure is classified is auditor semantics. **Recommended as a follow-up requiring authorization,
not done unilaterally.**

## C.3 Verified — the real message, and no collateral change

```
input : anthropic_error: TypeError: Messages.create() got an unexpected keyword argument 'temperature'
BEFORE: api_error       (matched '_error:' inside 'anthropic_error:')
AFTER : client_error

genuine API failures still classify correctly:
   RateLimitError: 429       -> api_error       AuthenticationError: 401 -> api_error
   APIConnectionError        -> api_error       APITimeoutError          -> api_error
   APIStatusError: 503       -> api_error

non-provider classes unchanged:
   empty_content / gpt-5.5   -> reasoning_exhaustion    empty_content / grok -> empty_response
   truncation                -> truncation              malformed / gpt-5.5  -> reasoning_exhaustion
   provider degraded         -> provider_unavailable    unmatched            -> unknown
```

## C.4 Does Part C close the Step-488 open item? **No — and they should stay separate.**

They fix different things:

- **Part C stops the label asserting something false.** A `client_error` no longer claims the call
  reached the API.
- **Step 488 open item 1 makes the detail queryable.** Even with a correct `client_error` label, the
  string *"unexpected keyword argument 'temperature'"* is still absent from the record. Nothing in the
  result would name the dependency, so a census still cannot find it.

**Part C would have stopped the investigation going to the billing dashboard. It would not have named
the SDK.** Persisting the raw error alongside the class remains open, and is now better specified:
the message is already printed at `lease_coverage_305.py:611`, so this is a plumbing change, not a
capture change — **as Step 501 corrected: the record loses it, stdout does not.**

---

## WHAT IS NOT ESTABLISHED

- **Not deployed.** The pins take effect on the next Railway rebuild, which is a push.
- **`google-genai` 2.20.0 is verified by five live calls and the suite, not by a pipeline run.** No
  Mode C run has executed on it. The two gemini models answered; the extractor's full JSON path did
  not.
- **Whether production currently has `python-docx` 0.8.11 or 1.x.** Local had 0.8.11; production
  resolves independently and was never inspected.
- **The ceilings are judgements, not measurements.** Each is the next breaking boundary above a
  verified version; none has been tested against the version it excludes.
- **`client_error` reaches no surface.** It is a new class in the fallback record; no banner, report
  or API field mentions it. That is the Step-488 disclosure question, still open.
