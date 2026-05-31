# Step 370d — Stage 7 Directional Output-Budget Integrity

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Truncation diagnosis + labeling + measured budget (lease_synthesis.py).
**Base SHA:** `9eee1a1` (370b). `lease_synthesis.py` only; no `cam/core/`; no frontend.

---

## BLUF

**Branch D2.** The truncation SHAPE is established (370b + this step); the max-token CAUSE
is **probable, not established** — the `cam/core` provider adapter returns only text, so
`stop_reason` / output-token usage are unavailable, and obtaining them would require a
locked-module change. Implemented all three layers, with the cap raise labeled provisional.

- **Layer A** — explicit truncation diagnosis (`_diagnose_pass2_output`): a Pass-2 response
  that began an array but never validly closed (unbalanced brackets / ended mid-string and
  fails to parse) is detected and **labeled `failed_truncated_output_budget`** *before*
  salvage runs. Per-evaluator state persisted in `pass2_integrity` as one of
  **complete | truncated | malformed | excluded**.
- **Layer B** — Pass-2 output cap raised **8000 → 12000 tokens**, uniform across A/B/C.
  Measured from the largest *complete* payload (below). Pass-1 (8000) and consolidation
  (6000) budgets unchanged.
- **Layer C** — 369 fail-loud preserved; salvage may **never** become a vote; a truncated
  evaluator is excluded (non-contributing); B/C carry; nothing fabricated.

Primary proof (deterministic replay of real captured content) **passes all four states**.
Fresh monitoring run: **see "Fresh run" below.**

---

## Verification gate — six-run A/B/C table (370c artifacts)

Source: `pass2_raw[role]` in each stored `pipeline_results.json` (parsed objects) +
`[pass2_raw_dump]` raw lengths from headless logs. **No provider `stop_reason` / token
usage exists** — the adapter doesn't expose it (the decisive D1/D2 fact).

| Run | path | A raw_len | A parsed | A state | B raw_len | B parsed | B state | C raw_len | C parsed | C state |
|---|---|---|---|---|---|---|---|---|---|---|
| W1 | web | n/c¹ | 1 (salvage `"LP-27"`) | **truncated** | n/c | 36 | complete | n/c | 36 | complete |
| H1 | headless | **29177** | 1 (salvage `"LP-29"`) | **truncated** | 21058 | 35 | complete | 14657 | 35 | complete |
| H2 | headless | 27087 | 36 | complete | 19276 | 34 | complete | 12777 | 34 | complete |
| W2 | web | n/c | 31 | complete | n/c | 31 | complete | n/c | 31 | complete |
| W3 | web | n/c | 1 (salvage `"LP-29"`) | **truncated** | n/c | 36 | complete | n/c | 36 | complete |
| H3 | headless | **28531** | 1 (salvage `"LP-28"`) | **truncated** | 20985 | 37 | complete | 15197 | 37 | complete |

¹ n/c = not captured (web-run Pass-2 raw went to server stdout, not piped to a file in
370c). The *parsed* result is persisted, which is decisive: the four failures all parsed to
a one-element list whose sole member is a bare LP-id **string** — the 370b truncation-salvage
signature.

**Per-evaluator verification fields:**
- `json_parse_success`: False for the 4 failed A responses (salvaged via fallback extractor);
  True for all complete responses.
- `top_level_array_closed`: False for the 4 failed A (unclosed array = truncation); True for
  all complete.
- `stop_reason` / `output_token_count`: **unavailable** for all (adapter returns text only).
- `configured_max_output_tokens`: 8000 (at time of 370c).
- salvage on failure: yes — bare LP-id string from an incomplete array (all four).

### B/C headroom (working runs)
- **Eval-A (claude-sonnet-4-6):** 27,087 (complete) … 29,177 (truncated) chars — **at/over the cap.** Most verbose; hits the wall first.
- **Eval-B (gpt-5.4):** 19,276 / 20,985 / 21,058 chars — **~26% headroom** below A's complete size; comfortably under but not enormous.
- **Eval-C (grok-4.3):** 12,777 / 14,657 / 15,197 chars — **large headroom.**

A grazes/exceeds the ceiling; B and C are below it but **could cross it on a more verbose
run** — which is why the cap raise is applied pass-level (all three roles), not just A.

---

## Branch decision — D2 (explicit)

> **D2 — Truncation shape present but cap cause NOT proven.**

- Truncation shape: **established.** Unclosed top-level array → salvage to bare LP string
  (370b), reproduced by parser replay; the four failures share this shape exactly.
- Cap cause: **probable, not established.** The char-length boundary is strikingly tight —
  the largest complete A payload (27,087 chars) sits just under the prior 8000-token cap,
  the truncated ones (28,531 / 29,177) just over, consistent with an ~8000-token ceiling at
  ~3.4 Claude-chars/token. But this **infers** the tokenizer ratio; no provider
  `stop_reason="max_tokens"` or output-token count confirms termination at the ceiling, and
  the adapter (cam/core, locked) does not expose it. Per the instruction's explicit warning,
  "probable" is not upgraded to "established."

Per D2: detection + labeling implemented; **cause not asserted in records** (the persisted
`stop_reason`/`output_token_count` are `null`, and the budget raise is labeled provisional);
**flagged for separate investigation:** to confirm the cause, a future step must surface
provider `stop_reason`/usage from the adapter — a `cam/core` change, out of 370d scope —
and/or check transport/streaming/response-extraction.

---

## Layer B — the measured number behind the new cap

- **Largest COMPLETE directional Pass-2 payload observed:** Eval-A, run H2 = **27,087 chars**,
  parsing to 36 complete findings.
- That payload consumed **essentially the entire prior 8000-token budget** (the truncation
  boundary lands right here: 27,087 complete vs 28,531/29,177 truncated).
- **New cap = 8000 × 1.5 = 12,000 tokens**, applied **uniformly to A/B/C** for the Pass-2
  call. This is ~1.5× the largest complete payload's budget and ~40% above the largest
  *attempted* (truncated) content (~28.5–29.2K chars ≈ 8,400–8,600 est. tokens), so ordinary
  run-to-run verbosity no longer grazes the ceiling.
- Not a round number chosen for feel: it is 1.5× the binding ceiling that the largest
  complete payload exhausted. No provider hard-limit prevents 12,000 for claude-sonnet-4-6 /
  gpt-5.4 / grok-4.3.
- **Scope note:** the Stage 7 Pass-2 call evaluates compound + relief + directional
  candidates together (one call), so the raised cap covers that whole call — there is no
  separate "directional-only" Pass-2 call to isolate. The separate **Pass-1** (8000) and
  **consolidation** (6000) budgets were left **unchanged** as instructed.

---

## Acceptance criteria — replay proof (deterministic, no server/API)

`_step370d_replay.py` replays the real decision sequence (`_diagnose_pass2_output` then
`_safe_parse_synthesis`, same order as `_try_call`) against fixtures built from preserved
370c content:

| # | Fixture | Result |
|---|---|---|
| 1 | Complete canonical (real H2 Eval-A, 36 findings) | **COMPLETE**, parses to 36 — unchanged ✓ |
| 2 | Truncated (real content cut mid-array; unclosed) | **TRUNCATED** (`failed_truncated_output_budget`), 0 findings — **not salvaged to a vote** ✓ |
| 3 | Malformed non-truncated (closed dict, wrong shape) | **MALFORMED** ("expected list got dict") — rejected **distinctly** from truncation ✓ |
| 4 | The exact OLD salvage fragment `["LP-27"]` | parses to `['LP-27']`, **0 directional votes** — fragment can never be a vote ✓ |

Truncated fixture diagnostics: `json_parse=False, array_closed=False, depth=2,
in_string=True` → unmistakable truncation shape. All assertions pass.

**Fidelity caveat (honest):** the full raw truncated 370c responses were not persisted (only
a 3000-char preview + the salvaged parse). The truncated fixture is a **real complete
captured response truncated mid-array** — faithful to the established defect class, not
byte-identical to the lost originals. This is the best available "captured truncated"
artifact and is sufficient to prove the detection/labeling behavior.

**Criterion 4 (369 fail-loud intact):** the Step 369 `INTEGRITY WARNING` code in
`_build_pass2_directional_findings` is **unchanged** and still fires for a *completed*
evaluator that returns objects but matches zero candidates (genuine format drift). A
*truncated* evaluator now gets its own louder `[lease_synthesis] TRUNCATION:` line at
detection and is excluded — a more precise signal than the old crude `all_lost`.

### Four persisted states demonstrated
`pass2_integrity[role].status` ∈ { **complete | truncated | malformed | excluded** } with
`reason_code`, `contributing`, `truncation_detected`, `raw_response_length`,
`json_parse_success`, `top_level_array_closed`, `stop_reason` (null), `output_token_count`
(null), `configured_max_output_tokens`.

---

## Fresh run (monitoring evidence — NOT the acceptance gate)

One fresh headless run on the new code (`lease_review_20260531_011705_370d_fresh1`):

| Role | status | contributing | matched_directional | raw_len | configured_cap | array_closed |
|---|---|---|---|---|---|---|
| A | complete | True | 28 | **28168** | 12000 | True |
| B | complete | True | 28 | — | 12000 | True |
| C | complete | True | 28 | — | 12000 | True |

Run-level: total_cpf=34, directional_final=28, flagged_lp=28, pass1_candidates=28,
guard `complete`/not-triggered.

**Significance:** Eval-A produced a **28,168-char** response and **completed**
(37 objects, 28 directional matched, `all_lost=False`). Under the old 8000-token cap a
response of this size truncated (370c H3 truncated at 28,531 chars). With the 12,000 cap it
fit and contributed. This is **monitoring evidence**, not proof — truncation is intermittent
and one green run cannot prove the cap eliminated it; it shows the raised budget lets a
previously-truncating-size response complete, and that the new `status` persistence is
correct (all three roles `status=complete`, `configured_max_output_tokens=12000`).

---

## Honest proof-chain statement

- **Established:** Stage 7 Pass-2 directional output truncates (unclosed JSON array) and the
  old parser salvaged the fragment into a non-vote; Eval-A is the most verbose and fails
  first (4/6 in 370c); detection now labels it `failed_truncated_output_budget` and excludes
  it; salvage can no longer become a vote; B/C carry; 369 fail-loud intact.
- **Probable, not established:** that the truncation is caused by hitting
  `max_output_tokens=8000`. The char-length boundary aligns almost exactly with an 8000-token
  ceiling, but no provider `stop_reason`/usage confirms it (adapter, in locked `cam/core`,
  returns text only). The 12,000 cap is therefore a **provisional, likely-helpful** measure,
  not a proven root-cause fix. If truncation recurs above 12,000, the cause is not the cap
  and the transport/streaming/extraction path (or a `cam/core` change to surface stop_reason)
  must be investigated.

---

## Scope / commit

- `lease_synthesis.py` only: truncation diagnosis helper + exception, wired into
  `_call_pass2_evaluator` (all three roles); Pass-2 cap 8000→12000; `pass2_integrity`
  extended with the four-state status + diagnostics.
- No `cam/core/`. No Pass-1 / Pass-2 matching / consolidation / bucket changes. No prompt
  verbosity reduction. No automatic retry. No frontend change, no version bump.
- Pre-existing uncommitted `app/config.py` (Step 369 reload comment) left untouched.
- Committed: the change + `_step370d_replay.py` (regression fixture). 370c runner scripts
  remain.
