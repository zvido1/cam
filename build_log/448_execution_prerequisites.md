# 431 Stage-2 — Execution prerequisites contract

**This is a POST-RUN ARTIFACT DOCUMENTING AN UNDECLARED PACKAGE REQUIREMENT.** It is not a
restatement of a declaration the package carries. The sanctioned package **names no required
environment variable and defines no failure mode for their absence**; the requirement below was
established by inspection of `cam/core/provider_router.py` before launch, not read off the package.

Evidence that the package declares nothing:

```
$ git show d679eec:build_log/run_431_selection_measurement.py | grep -c "getenv\|environ\|dotenv"
0
$ git show d679eec:build_log/431_config_manifest.json | grep -ci "env\|api_key"
0
```

(The four `env` matches in `431_measurement_config.json` are `context_policy_version:
"431_envelope_v1"`, `"envelope"`, `"context_envelope_id (opaque)"`, `"context_text (deterministic
envelope)"` — the envelope algorithm, not environment variables.)

## The call sites that impose the requirement
Verbatim, `cam/core/provider_router.py`:

```
319:        api_key = os.getenv("OPENAI_API_KEY")
431:        api_key = os.getenv("ANTHROPIC_API_KEY")
738:        api_key = os.getenv("XAI_API_KEY")
```

The harness reads these indirectly, through the router, at call time. Nothing in the token-bound
package surfaces them.

## Required environment-variable NAMES (names only — no value appears in this document)
- `ANTHROPIC_API_KEY` — role A
- `OPENAI_API_KEY` — role B
- `XAI_API_KEY` — role C

## Provider connectivity requirements
Outbound HTTPS to the Anthropic, OpenAI and xAI API endpoints for the duration of the run
(~21 minutes observed for 108 role-calls). No proxy or offline mode is supported by the package.

## Sanctioned model identities
| role | provider | model |
|---|---|---|
| A | anthropic | `claude-sonnet-4-6` |
| B | openai | `gpt-5.5` (own-chain fallback `gpt-5.4`, noncanonical) |
| C | xai | `grok-4.3` |

## External-launcher responsibility
The launcher — outside the package — is responsible for populating the three variables in the
process environment before invoking the harness, and for never writing their values to a log,
console, or file. In Step 447 this was done by a scratchpad launcher that read the key file, set
`env` for the subprocess, and printed variable **names** only.

## Environment injection does not modify token-bound package bytes
Environment variables are process state, not repository content. They are not among the eleven
token-bound artifacts, are not inputs to `recompute_token_from_head()`, and do not appear in
`git status`. Injecting them therefore cannot change the package token, cannot invalidate the
sanction tag, and leaves the whole-tree cleanliness check unaffected. This is why injection was the
correct seam: the harness could not be edited to load them without voiding the sanction.

## Confirmation that no secret value was captured in any log
Scanned the complete Step-447 run log (23,378 chars):

```
sk- prefixed:  0 match(es)
xai- prefixed: 0 match(es)
long b64ish:   1 match(es)
```

The single long-token match is
`ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca` — the **sanction token T4**,
which is public by design (it appears in the committed manifest and in the signed tag body). **No
API key material was captured.**

## Reproducibility statement (verbatim as directed)

"Package identity is repository-reproducible; successful live execution additionally requires a
declared external environment."
