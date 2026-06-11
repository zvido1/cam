# Step 383 Code Status — N=10 DEF-010a Recall-Stability Checkpoint

**Date:** 2026-06-11  
**Commit under test:** `d134ef8` (DEF-010a — presence-tier normalization in `merge_element_verdicts`)  
**Verdict: Case B | push=True | def002_blocked=True**

---

## What was done

Ran N=10 independent live pipeline runs against the 375E lease, all at commit `d134ef8`,
using the enhanced harness `build_log/_383_run_harness.py`.

Each run: ~94 API calls, ~25 min, full Mode C (GPT-5.5 / Claude Sonnet 4.6 / Grok 4.3 / Gemini 3.1 Pro Preview).
All 10 runs completed with `quality=clean`.

Reports:
- `build_log/383_DEF010a_live_recall_stability_results.json`
- `build_log/383_DEF010a_live_recall_stability_RESULTS.md`
- `build_log/383_midrun_snapshot.md`

---

## LP-13 (negligence carveouts) — target of DEF-010a

| Metric | Result |
|--------|--------|
| Coverage rate | 10/10 `covered` |
| Stage 7 forwarded | 0/10 |
| `observed_stable_covered_across_runs` | True |
| `hard_case_seen` | **True** |

**Run 3 confirmed the hard case live:** evaluators returned `implicitly_present / explicitly_present / covered_by_default_law` — three distinct presence-tier labels, no majority under old Counter logic.
DEF-010a collapsed all three to `present_like` → unanimous → `explicitly_present`.
This is direct live validation of the fix's core mechanism.

Per-run evaluator labels:

| Run | Labels | Hard case? |
|-----|--------|------------|
| 1 | EP / EP / IP | no |
| 2 | IP / EP / IP | no |
| 3 | IP / EP / CD_by_default_law | **YES** |
| 4 | IP / EP / IP | no |
| 5 | EP / EP / IP | no |
| 6 | EP / EP / IP | no |
| 7 | EP / EP / EP | no |
| 8 | EP / EP / CD_by_default_law | no (2×EP = majority) |
| 9 | IP / EP / IP | no |
| 10 | IP / EP / IP | no |

---

## Case B — Broader recall instability (blocks DEF-002)

Three LPs are harmful + high/medium materiality + ever Risk but absent in 2/10 runs:

- **LP-03** — 8/10 | buckets: review_needed / risk
- **LP-19** — 8/10 | buckets: improvement / review_needed / risk  
- **LP-26** — 8/10 | buckets: improvement / review_needed / risk

This is not a DEF-010a regression — it predates this fix. But it prevents claiming
full recall stability for DEF-002 closed-lease external validation.

Bucket variance: Runs 2 and 10 are outliers (Risk=9 and Risk=6 vs normal 11–15,
Review Needed=12 and 16). Cause: consequence assessment for several findings returned
ambiguous support in those runs → Step 378 governance routed them to review_needed.

---

## Decisions / Recommendations

| | |
|--|--|
| Push `d134ef8` | **Yes** — LP-13 stable, hard case validated, no regressions |
| DEF-002 | **Blocked** — LP-03 / LP-19 / LP-26 instability |
| DEF-010b | **Deferred** — Stage 7 `covered` gate + CD mechanism, pending legal/product |

---

## Harness notes

- Harness died twice (context window switches killed background processes).
- Fixed by launching as detached Windows process via `cmd /c start /B` through PowerShell.
- Harness is resumable: checkpoint at `383_run_log_temp.txt`.
- `quality=unknown` in checkpoint Run 1 entry was a stale field; `derive_run_quality()` added to harness corrects this — all 10 runs were `clean`.

---

## No production code changes

Only `build_log/_383_run_harness.py` and `build_log/_383_midrun_analysis.py` were modified.
`cam/core/` is untouched.
