# Step 375-Q — Status: synthesis-severity instability, two-track attribution (READ-ONLY, measure-only)
**Date:** 2026-06-03  **Mode:** read-only measurement. **NO production change** (no prompt/threshold/severity/
Risk/Priority/routing/NEXT0 edit; production byte-identical at 374Z / 609af43 — verified `git diff 609af43 HEAD
-- cam/` is empty). Scripts: `build_log/_375q_retro.py`, `build_log/_374zv_verify.py`.

## ⚠️ Execution-environment limitation (stated up front, not rationalized)
**Track A "≥5 fresh full-pipeline runs" and Track B "frozen-input synthesis replay" could NOT be run in this
sandbox: there are no LLM provider keys here.** The checked-in `.env` holds only ACCESS_CODE/SMTP/app settings;
the only key in the environment is the Claude-Code Anthropic gateway. The pipeline routes to `openai:gpt-5.4`
(synthesis) + `xai:grok-4.3` + `anthropic` (evaluators) via ProviderRouter — none callable here. Per the
project's "sandbox has no prod auth" rule, a live run from this session is impossible.

**What I did instead — and why it is a STRONGER Track A, not a weaker one:** there are ~20 existing runs of
the byte-identical Atlas Meridian lease (text SHA `fbf5f362ae10`), including two **controlled same-commit
back-to-back repeat triplets** (s370r1/2/3, 370c_H1/2/3) and the reported **030920↔0604 pair, both on the
CURRENT synthesis code** (`lease_synthesis.py` last changed at Step 372c `9f60d23`, before 030920; 374Z did
not touch synthesis). Decomposing these per-role isolates the variance to a single Stage-7 sub-step — which a
black-box count of 5 fresh runs would not. Track B's *goal* (source vs messenger) is answered below; the live
frozen replay remains the formal confirmation and the one measurement that still needs a key-bearing env.

---

## Track A — Stage 7 variance across same-lease runs (compound vs directional SEPARATE)
Per-run Stage-7 counts (full table in `_375q_retro.py` output). The decisive split:

| | directional count | directional severity (H/M/L) | compound count | compound HIGH |
|---|---|---|---|---|
| **030920** (current code) | 28 | **13 / 14 / 1** | 5 | 3 |
| **0604** (current code) | 26 | **26 / 0 / 0** | 6 | 4 |
| s370r1 / r2 / r3 (same commit ×3) | 28 / 28 / 28 | 0/8/20 → 1/23/4 → 0/14/14 | 8/9/6 | 5/5/3 |
| 370c_H1 / H2 / H3 (same commit ×3) | 28 / 28 / 24 | 0/18/10 → 22/6/0 → 0/23/1 | 6/5/6 | 4/3/4 |

**Reading:**
- **Directional COUNT is stable; directional SEVERITY is violently unstable.** s370r1/2/3 = 28/28/28 directional
  every time; ~85–95% of directional finding IDENTITIES persist across a repeat set (candidate generation is
  STABLE). But of the persistent directional findings, **60% flip severity in s370r1/2/3, 96% in 370c_H1/2/3,
  54% (14/26) in the 030920↔0604 pair.**
- **Compound is stable.** Compound severity flips on persistent findings = **0** in every set; compound HIGH
  holds at 3–5. Compound is NOT the inflation driver.
- The Risk 20→36 swing is therefore **directional findings flipping to HIGH**, not new findings and not compound.

### The producing mechanism (read at 609af43)
`lease_synthesis.py:1936`:
```python
severity = "HIGH" if confirmed == 3 else "MEDIUM" if confirmed == 2 else "LOW"
```
Directional severity is **not a calibrated label — it is the Pass-2 confirmation VOTE COUNT** (`confirmed` =
how many of 3 Pass-2 evaluators returned `mismatch_confirmed`; 0/3 is suppressed). Via `csynth`, only a
**3-0 (HIGH)** directional finding routes to **Risk** (ASSERT_SIGNAL). So *the Risk total is literally the
count of directional candidates that happen to get unanimous Pass-2 confirmation this run.* Compound severity,
by contrast, is map-based (`_severity_map.get(pattern_type)`, line 1528) + max-merge → stable.

### Per-role decomposition — the smoking gun (Pass-2 role identity)
Pass-2 roles: **A = Claude Sonnet 4.6**, **B = GPT-5.4** (forced fallback — gpt-5.5 returns wrong format,
per code comment), **C = Grok 4.3**. For the 26 directional findings present in BOTH 030920 and 0604, **all 14
severity flips have the identical signature:**
```
030920:  A=mismatch_confirmed  B=no_mismatch/unclear  C=mismatch_confirmed   → 2-1 → MEDIUM
0604  :  A=mismatch_confirmed  B=mismatch_confirmed    C=mismatch_confirmed   → 3-0 → HIGH
```
**A (Claude) and C (Grok) are stable confirmers in both runs; role B (GPT-5.4) is the sole swing voter** — on
0604 it confirmed everything (→ all 26 directional HIGH → Risk 36). Across the repeat triplets the per-role
verdict-CHANGE counts confirm Pass-2 verdicts are nondeterministic and the swing role varies:
- **s370r1/2/3:** only **B** changes (16/25 persistent findings; A & C = 0 changes). B's per-run mix swings
  `17 no_mismatch / 8 confirmed` → `23 confirmed / 1 no_mismatch` → `14 confirmed / 9 no_mismatch`.
- **370c_H1/2/3:** **A changes on 24/24** and B on 7 — so it is not *only* B; the GPT and Claude Pass-2 roles
  both exhibit run-to-run verdict drift at temperature 0.

All Pass-2 calls run at **temperature 0.0** (verified: lines 765/829/1223 etc.), so this is residual model
nondeterminism (and/or fallback/parse loss), NOT a sampling-temperature setting.

---

## Track B — frozen-input synthesis replay: NOT RUN (no provider key); goal answered indirectly
The formal Track B (freeze pre-Stage-7 artifact, replay `run_synthesis` ≥5× on identical input) requires
openai/xai keys absent here. **However its decisive question — is Stage 7 the SOURCE or the MESSENGER — is
answered by the per-role retrospective:** the variance lives entirely in **Pass-2 per-role model verdicts**
(Stage-7-internal calls), while directional candidate IDENTITIES are stable run-to-run. If upstream coverage
were the driver, the SET of directional findings would change; instead the same findings get different Pass-2
votes. **Stage 7 (the Pass-2 directional verification layer) is the SOURCE.** Frozen replay is still owed as
the formal confirmation and to separate genuine-verdict-nondeterminism from lost-vote parse failures (below).

---

## ATTRIBUTION VERDICT (compound and directional separately)
| population | pattern | source/messenger | evidence |
|---|---|---|---|
| **Directional** | **#3 Pass-2 verification instability → surfaces as #2 severity-flip** (severity == Pass-2 vote count, line 1936). Secondary **#5 infra** flavor (role B = GPT-5.4 fallback; some swing votes are `unclear`, which the code also assigns on the `_NO_OBJECT` "votes-lost" path, line 1932 — i.e. a fraction may be Pass-2 output truncation/parse loss, the exact failure Step 370d's budget raise targeted). | **Stage 7 is the SOURCE** | candidates stable; only Pass-2 per-role verdicts swing; A/C stable on the current-code pair, B the swing voter; temp=0. |
| **Compound** | none — **stable**. Not #1/#2/#3/#4. | n/a | map-based severity (line 1528) + max-merge; 0 persistent-severity flips in every set; HIGH steady 3–5. |
| NOT #1 (candidate-gen) | directional identities persist ~85–95% across same-commit repeats. |
| NOT #4 (consolidation) broadly | compound/consolidation severity stable; the instability is upstream of consolidation, in Pass-2 voting. |
| NOT #6 (upstream) | candidate identities stable → upstream coverage not changing WHICH findings exist. |

**Plain statement:** the same lease yields Risk 20 vs 36 because the directional Pass-2 verification verdicts
(especially GPT-5.4 in role B) are not reproducible at temperature 0, and directional severity is a hard
3-vote threshold (3-0=HIGH=Risk), so a one-vote drift per finding moves it in/out of the Risk headline. This
is a Stage-7 Pass-2 reproducibility problem, not candidate discovery and not compound.

---

## Recommendation — what to MEASURE next (NOT a fix; attribution must finish first)
1. **Run the formal Track B** in a key-bearing environment: freeze the 0604 pre-Stage-7 artifact, replay
   `run_synthesis` ≥5×; capture per-pass Pass-2 per-role verdicts + `pass2_integrity` (match vs `_NO_OBJECT`
   default counts) + final directional severities. Confirms Stage-7-source and per-role reproducibility.
2. **Split the directional flips into genuine-verdict-change vs lost-vote (infra).** The code already tracks
   Pass-2 match vs default counts (`_dir_match_counts` / `_dir_default_counts`, lines 1888-1906) and emits a
   "votes lost" integrity warning; measure how many of the `unclear`/swing votes are `_NO_OBJECT` defaults
   (truncation/format-drift) vs real `no_mismatch`. This decides whether the eventual fix is a verification-
   stability change (#3) or an output-budget/parse change (#5) — different fixes, as the brief warns.
3. **Measure GPT-5.4 (Pass-2 role B) reproducibility on this task specifically** — it is the dominant swinger
   on current code AND a forced fallback; quantify its temp-0 verdict stability vs Claude/Grok.
4. **Do NOT** touch severity mapping / thresholds / prompts / routing until 1–3 separate genuine
   nondeterminism (#3) from parse loss (#5). A premature "stability fix" would repeat this session's lesson.

## Product status
- **374Z: VERIFIED** (374Z-V) — and explicitly **NOT implicated** here (it only moved LP-08 Imp→Addressed;
  it never touches synthesis).
- **Risk-headline stability: NOT VALIDATED** — directional Pass-2 severity is non-reproducible on
  byte-identical input (Risk total swings 20↔36; PriorityRisks 16↔31).
- **PAUSED:** external demo / Joshua use of Risk totals, Priority totals, or Stage-7 HIGH counts, until Track
  B + the genuine-vs-lost-vote split land.

## Decisions Needed
1. Authorize the formal Track-B frozen replay (needs a provider-keyed env — Tzvi's terminal or deploy box;
   I cannot run it from here). The harness exists (`_step370d_replay.py` / `_step370c_headless.py`).
2. After Track B: choose the measurement that separates #3 (verification nondeterminism) from #5 (Pass-2
   parse/truncation) before any stability fix is specced.
