# Step 370b — Eval-A directional wrapper: verify, then narrowly recover

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Verification-gated. Verification ruled out the hypothesis → **Branch B → NO code change.**
**Base SHA:** `9a25c0d` (370c). No code committed this step (Branch B); status file only.

---

## BLUF

**Branch B.** The working hypothesis (`[[...]]` double-wrapped array) is **disproven**. The
four all_lost Eval-A responses did **not** wrap a complete inner list of findings. Each
parsed to a **one-element list whose sole member is a bare LP-id string** (`"LP-27"`,
`"LP-29"`, `"LP-29"`, `"LP-28"`) — a truncation-salvage artifact, not a recoverable
wrapper. The real defect is **response truncation at the 8000-token output ceiling**:
Eval-A's verbose Pass-2 JSON exceeds the budget, the top-level array is cut off unclosed,
`json.loads` fails, and the parser's last-ditch `safe_json_extract` salvages a trailing
`involved_lps` fragment.

No normalizer was written. A `[[...]]` single-level unwrap **would not even fire** here
(its precondition is "sole member is a list"; the sole member is a string). The findings
are *absent* from the parsed output — truncated away — so no unwrap can recover them.

This is a **Sonnet output-reliability / token-budget problem**, to be specced separately
(candidate fixes below). The Step 369 guard already handles it correctly: it fires
`all_lost`, B+C carry the count, nothing is fabricated. **No behavior change made.**

---

## Step 1 — Verification table (the deliverable)

Source of truth: `_stage_data.synthesis_meta.pass2_raw.A.verdicts` persisted in each run's
`pipeline_results.json` (the full parsed object — not the 3000-char log preview).

| Run | path | raw_len (chars) | parsed outer | sole member type | sole member value | inner findings list? | inner count | fields complete? | matches working shape? |
|---|---|---|---|---|---|---|---|---|---|
| **W1** | web | (server stdout, not captured)¹ | `list[1]` | **str** | `"LP-27"` | **NO** | n/a | n/a (no findings) | **NO** |
| **H1** | headless | 29177 | `list[1]` | **str** | `"LP-29"` | **NO** | n/a | n/a | **NO** |
| **W3** | web | (server stdout, not captured)¹ | `list[1]` | **str** | `"LP-29"` | **NO** | n/a | n/a | **NO** |
| **H3** | headless | 28531 | `list[1]` | **str** | `"LP-28"` | **NO** | n/a | n/a | **NO** |
| H2 (working) | headless | 27087 | `list[36]` | dict | — | flat list of dicts | 36 (28 Dir-) | YES | — (reference) |
| W2 (working) | web | (server stdout) | `list[31]` | dict | — | flat list of dicts | 31 (22 Dir-) | YES | — (reference) |

¹ Web-run raw lengths weren't piped to a file in 370c, but the **parsed `verdicts`** for W1/W3
*are* persisted in their stored `pipeline_results.json` — that is the decisive field, and it
shows `list[1]` with a string sole member, identical to the headless failures.

### The hypothesis's specific questions, answered

- **Is the parsed output a one-element outer array whose sole member is a list (`[[...]]`)?**
  **NO** — for all four, the sole member is a **string** (an LP id), not a list.
- **How many findings in the inner array?** There is no inner array. Zero findings are
  present in the parsed output.
- **Do inner finding_ids/shape match a working run?** N/A — no inner findings exist.
- **Does every inner item carry required fields?** N/A — no items.
- **Free of malformation other than the extra wrapper?** **NO** — the malformation *is*
  truncation, not an extra wrapper. The response is incomplete.

---

## Root-cause evidence — truncation at the output-token ceiling

1. **Salvage signature.** All four parse to `[<LP-id string>]`. An LP-id string is the
   value of an `involved_lps` array element. `safe_json_extract` returns this when the
   top-level array is unclosed and the last cleanly-extractable JSON near the cut is a
   trailing `involved_lps: ["LP-xx"]` fragment. This is the fingerprint of truncation
   mid-response, not of a structural wrapper.

2. **Length vs budget.** Pass-2 `max_output_tokens = 8000` for all three evaluators
   (confirmed in `_EVALUATOR_LINEUP_PASS2`). The failing Eval-A responses are **29177**
   (H1) and **28531** (H3) chars — *longer* than the working **27087** (H2). At ~3.5–4
   chars/token, ~28–29K chars sits right at/above the 8000-token cap. The verbose runs
   exceed budget and get cut off unclosed; the slightly shorter working run closes its
   array in time. This explains the intermittent 4/6 rate and the path-independence found
   in 370c — it's a coin-flip on whether Sonnet's directional reasoning fits in 8000 tokens.

3. **Parser replay.** Reserializing H2's valid 36-finding response and truncating it at
   50–99% reproduces the failure class: the parser salvages a fragment (a partial dict or
   a trailing array), never the complete list. A truncated array-of-objects is
   unrecoverable into N complete findings by any single-level unwrap.

4. **Starts identical, ends different.** The first 3000 chars of the failing responses are
   indistinguishable from the working ones (`[\n  {\n  "candidate_id": "CRX-01"...`) — the
   response is a well-formed array *in progress* that simply never finishes. Consistent
   with truncation, inconsistent with a wrapper defect.

---

## Branch decision — B (explicit)

> **Branch B — any failed response is malformed DIFFERENTLY** (varying shapes, incomplete
> inner findings, prose hybrids, deeper nesting, **truncation**) → do NOT write a
> normalizer.

The failure is **truncation** — explicitly named in the instruction as a Branch B trigger.
Two independent reasons Branch A is wrong:

1. **Precondition fails.** Branch A's unwrap requires "outer len 1, **sole member a list**,
   inner non-empty, every inner member a dict passing the validator." The sole member is a
   **string**. The unwrap would never fire — it would be dead code for this defect.
2. **Findings are absent, not wrapped.** Even a more aggressive "extract complete objects
   from a truncated array" parser (which the instruction explicitly forbids as a "tolerant
   interpret-whatever-Sonnet-sent adapter") would recover only a *partial, arbitrary
   prefix* of the findings — silently producing wrong directional counts. That is worse
   than the current fail-loud behavior.

Normalizing this would "just move the failure" — exactly the outcome Branch B exists to
prevent.

---

## Recommendation (to be specced as a SEPARATE step — not done here)

Eval-A Pass-2 truncation is a **model-output / token-budget reliability problem**, not a
parser problem. Candidate fixes for a future step (do not implement now):

1. **Raise `max_output_tokens` for Eval-A Pass-2** above 8000 (it is currently the binding
   constraint; B/gpt-5.4 and C/grok-4.3 evidently fit, but Sonnet's verbosity does not).
   Lowest-risk, most direct.
2. **Reduce per-item output verbosity via prompt** (shorter `reason`/`lease_evidence`, or
   request compact single-line JSON) so the full set fits the budget.
3. **Detect truncation explicitly** (unclosed top-level array / finish_reason=max_tokens)
   and retry once with a higher budget — an *audited* retry, not silent.

All three are out of 370b's scope. The Step 369 guard + `pass2_integrity` remain the
boundary until one is specced and shipped.

---

## Current handling is already correct (no change needed)

For this truncation mode, the existing pipeline already does the right thing:
- `_safe_parse_synthesis` salvages a fragment → `verdicts = [<string>]`
- the directional matcher matches 0 of N candidates from Eval-A
- Step 369 sets `pass2_integrity.A.all_lost = True` and prints the `INTEGRITY WARNING`
- Eval-B and Eval-C carry the directional count; nothing is fabricated; the count is not
  silently degraded to zero (it reflects B+C)

No code was modified. The 369 fail-loud path is intact and is the correct interim behavior.

---

## Scope / commit

- **No `lease_synthesis.py` change.** Branch B → "commit nothing but the status file."
- No `cam/core/`. No frontend change. No version bump. No fresh keyed run (Branch B needs
  no normalizer and no fixture replay; the decision is made entirely from preserved 370c
  artifacts, which is the stronger proof per the instruction).
- The 370c logging-only dumps (`[pass2_raw_dump]`, `[pass1_prompt_hash]`) remain in place
  from `eaf130f`; they are what made this verification possible and are harmless to leave.

**Do not start any follow-on.** Paste the Step 1 table + Branch B to Chat; Chat decides
whether/when to spec the Eval-A token-budget fix.
