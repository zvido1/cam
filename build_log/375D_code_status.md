# Step 375D — Status: keyed GPT-5.4 (Pass-2 role B) reproducibility harnesses (WRITTEN, NOT RUN)
**Date:** 2026-06-03  **Mode:** Code wrote two replay harnesses; **Code did NOT run them** (no provider keys
in this sandbox, and runs cost money). **NO production change** — both scripts live in `build_log/`, call the
REAL pipeline code path, and write only `build_log/375D_*.json`. No prompt/severity/routing/code change.
PROVISIONAL measurement step; feeds 375E (two-output directional redesign spec).

## What was written
| harness | file | what it does | output |
|---|---|---|---|
| **A — full frozen-input Stage-7 replay** | `build_log/_375d_full_replay.py` | Freezes the pre-Stage-7 input (`full_tenant_text` + `coverage_assessment` + `conflicts`) from the validated current-code run **0604** and calls the REAL `run_synthesis(...)` **N≥5** times against that identical input. Upstream coverage/extraction is NOT re-run. | `build_log/375D_full_replay.json` |
| **B — targeted role-B reproducibility** | `build_log/_375d_roleB.py` | Runs Pass-1 ONCE (real `_call_single_evaluator` x3) to freeze the directional candidate set, selects a representative ~9–12 candidates (Risk-flippers / stable-unanimous / stable-2-1, classified from the stored 030920+0604 runs), then calls ONLY Pass-2 **role B (gpt-5.4)** **K≈10** times per candidate on the identical single-candidate prompt. | `build_log/375D_roleB.json` |

Both call the REAL functions (no reimplementation): `run_synthesis`, `_collect_flagged_lps`,
`_build_evaluator_user_prompt`, `_call_single_evaluator`, `_EVALUATOR_LINEUP_PASS1`,
`_collect_directional_candidates`, `_build_pass2_user_prompt`, `_call_pass2_evaluator`,
`_EVALUATOR_LINEUP_PASS2["B"]` (= openai/gpt-5.4), `_p2_build_directional_index`, `_p2_lookup_directional`.

## Captured metrics
- **A, per pass:** directional count; severity dist (HIGH/MED/LOW + `VERIFICATION_INCOMPLETE`); the set of
  3-0 (→Risk) directional findings; verification-incomplete set; full `pass2_integrity` (matched / unmatched
  / status / truncation / parse_ok / model) every pass; per-finding tally + evaluator_verdicts. Plus a
  summary table (pass × metrics) and `directional_3_0_risk_count_per_pass`.
- **B, per candidate:** `{n_confirmed, n_no_mismatch, n_unclear, n_integrity_fail}` over K calls, the stored
  030920/0604 agreements for context, and the raw per-call verdicts. (A flipper that's ~50/50 = genuinely
  borderline; a "stable" one that's ~K/0/0 = reproducible; high `n_integrity_fail` = infra, not judgment.)

## ▶ HOW TZVI RUNS THEM (keyed machine — has OPENAI/XAI/ANTHROPIC/GEMINI keys)
Keys are loaded by the scripts from `C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env`
(same pattern as `_step370c_headless.py`; sets `DISABLE_OPENROUTER=1`, `OPENROUTER_DRY_RUN=1`, pops
`OPENROUTER_API_KEY`). Run from the CAM repo root:

```bat
cd "C:\Users\Owner\OneDrive\CAM"
git pull

REM Harness A — full Stage-7 replay (default 5 passes; pass an int to change N)
python "build_log\_375d_full_replay.py"
REM   e.g. python "build_log\_375d_full_replay.py" 8

REM Harness B — role-B reproducibility (default 10 calls/candidate; pass an int to change K)
python "build_log\_375d_roleB.py"
REM   e.g. python "build_log\_375d_roleB.py" 12
```

Then commit the emitted JSON:
```bat
git add -f "build_log\375D_full_replay.json" "build_log\375D_roleB.json"
git commit -m "Step 375D: emitted GPT-5.4 Pass-2 reproducibility replay artifacts"
git push origin main
```

Each script prints a live summary table as it runs and writes the JSON at the end. If a script errors on
keys, confirm the `.env` path above exists and contains `OPENAI_API_KEY` (role B = gpt-5.4).

## Cost (heads-up)
- Harness A: **N full Stage-7 runs** (each = Pass-1 ×3 + Pass-2 ×3 + compound + consolidation). Default N=5.
- Harness B: **1 Pass-1 (×3 calls) + K × (≤12 candidates)** role-B calls. Default K=10 → ≤123 calls.
Keep N/K modest as written.

## Dry validation performed by Code (no model calls)
- `py_compile` clean on both harnesses.
- Symbol/signature check against the live module: all 11 imported names present;
  `run_synthesis(full_tenant_text, coverage_assessment, conflicts, perspective='tenant', cfg=None)`,
  `_build_pass2_user_prompt(clusters, relief, directional_candidates, flagged_lps, perspective)`,
  `_call_pass2_evaluator(role, ev_cfg, user_prompt)` — all match the harness call sites.
- `_EVALUATOR_LINEUP_PASS2["B"]` = `{provider: openai, model: gpt-5.4, max_output_tokens, temperature,
  timeout_sec, ...}` (all required keys present). Pass-1 roles A/B/C confirmed.
- Frozen input present in the 0604 run: `full_tenant_text`, `coverage_assessment` (32), `conflicts` (0).
- Candidate shape from `_collect_directional_candidates`: each carries `lp_ids` + `candidate_id` (`Dir-NN`),
  so the per-candidate isolation + `_p2_lookup_directional` matching (by id OR lp_ids) is robust.

## What the analysis will answer (after Tzvi runs them → 375E)
1. Is role B broadly unstable (most candidates split) or only the borderline ones (stable stay stable)?
2. Of the 14 Risk-crossing flippers, how many are ~even splits (genuinely borderline) vs lopsided (noise)?
3. Does unanimity-as-Risk-gate survive this data, or is Risk a coin-flip on borderline one-sided terms?
4. Counterfactual under a two-output model (materiality separate from verification strength): which
   candidates would be Risk regardless of the vote split?

## Constraints honored
- Harness is READ-ONLY w.r.t. production (writes only `build_log/` JSON; calls models but changes no
  code/output). No prompt/severity/routing change. Measurement only. **Code did NOT execute them.**
- External demo / Joshua use of Risk / Priority / Stage-7 directional totals remains **PAUSED**.

## Decisions Needed
1. Tzvi runs both harnesses on the keyed machine and commits the two JSON artifacts.
2. Then Code/Chat analyzes them → 375E (two-output directional redesign spec + governance policy choice).
