# Step 375-R — Status: directional confirmation-count-as-severity fork diagnostic (READ-ONLY, offline)
**Date:** 2026-06-03  **Mode:** read-only attribution + counterfactual. **NO production change** (no prompt/
threshold/severity/routing/Risk/Priority/model/UI edit; byte-identical at 609af43). Script:
`build_log/_375r_fork.py`. **Ran entirely from stored artifacts — no provider keys needed** (the stored
`_stage_data/synthesis_meta/{pass2_raw,pass2_integrity}` make the genuine-vs-lost distinction auditable).

## Reframed issue (accepted)
Not "synthesis-severity instability." The architectural defect is: **directional Pass-2 confirmation COUNT
is rendered as legal severity and gates Risk** — `3-0 → HIGH`, `2-1 → MEDIUM`, `1-2 → LOW`, only `3-0` routes
to Risk (`lease_synthesis.py:1936`). That conflates **epistemic support** (how many verifiers agreed) with
**substantive consequence** (legal materiality). A directional finding is not legally more severe because a
third evaluator agreed — it is better *verified*. This defect persists even if every model behaves perfectly.

## The fork (offline diagnostic spec, executed)
For every persistent directional finding (same `implicated_lps`) whose severity/Risk routing changed across
byte-identical same-commit runs, classify the per-role vote change using `pass2_integrity`
(matched/`unmatched_directional`/truncation/parse/status) + `pass2_raw[role].verdicts` (per-candidate parsed
object presence + verdict): **genuine-semantic** | **lost/integrity** | **candidate-match-failure** |
**routing/fallback** | **unauditable**. Then the product-consequence counterfactual. Pass-2 roles:
**A = Claude Sonnet 4.6, B = GPT-5.4 (forced fallback), C = Grok 4.3**.

---

## Q1 — WHY the vote count moves: per-run Pass-2 integrity (the decisive table)
| run | A | B | C |
|---|---|---|---|
| **030920** (current) | m=28 un=0 trunc=F parse=T **complete** | m=28 un=0 **complete** | m=28 un=0 **complete** |
| **0604** (current) | m=26 un=0 trunc=F parse=T **complete** | m=26 un=0 **complete** | m=26 un=0 **complete** |
| s370r1 / r2 / r3 | **m=0 un=ALL (empty output)** | m=full un=0 | m=full un=0 |
| 370c_H1 / H3 | **m=0 un=ALL (empty output)** | m=full un=0 | m=full un=0 |
| 370c_H2 | m=28 un=0 | m=28 un=0 | m=28 un=0 |

`pass2_raw[A]` confirms the mechanism: in the 370-era runs **Role A (Claude) returned `dir_object_count=0`
(`n_objects=1`)** — an EMPTY directional Pass-2 output, so all 28 candidates defaulted to `_NO_OBJECT`
(category **b: lost output**, not candidate-match failure — A returned no directional objects to mis-match).
On current code A returns `dir_object_count=28/26` with genuine verdicts. **Two distinct regimes:**

1. **Historical (pre-370d): LOST-VOTE / INTEGRITY FAILURE dominated.** Role A's empty directional output
   silently counted as non-confirming for every finding → no finding could reach 3-0 → **directional Risk
   forced to 0** in those runs. An integrity gap masqueraded as "MEDIUM / not-Risk." Contained by Step
   370d/372c (budget/integrity work) — A now returns full output.
2. **Current code (030920 ↔ 0604): integrity CLEAN; instability is GENUINE SEMANTIC.** Zero lost votes,
   no truncation, parse success, status=complete on all roles. The fork classifier returns **15 GENUINE
   semantic verdict changes, 0 lost/integrity** for the current-code pair. The swing is **Role B (GPT-5.4)
   genuinely changing `no_mismatch ↔ mismatch_confirmed`** on identical input at temperature 0, while A
   (Claude) and C (Grok) stably confirm.

Per the brief's categories, current-code instability = **(a) genuine semantic verdict change** (dominant);
historical instability = **(b) lost vote / integrity failure** (dominant, now contained); **(c)
candidate-matching failure, (d) routing/fallback, (e) unauditable: not material on current code.**

## Q2 — PRODUCT CONSEQUENCE of confirmation-count-as-severity (counterfactuals)
| set | persistent directional | flip severity | **enter/leave Risk solely on 3-0↔2-1 tally** | genuine vs lost |
|---|---|---|---|---|
| **current-code pair (030920→0604)** | 26 | 14 | **14** | **14 genuine (0 lost)** |
| s370r1/2/3 | 25 | 15 | 0* | A-empty all 3 runs → Risk pinned at 0 |
| 370c_H1/2/3 | 24 | 23 | 21 | 23 integrity-driven (A appears in H2 only) |

*s370 set: A empty in all 3 → directional Risk = 0 every run (no enter/leave because none ever reaches 3-0).

- **Current Risk headline is, for directionals, literally "count of directional candidates that hit unanimous
  Pass-2 confirmation this run."** On the current-code pair that count is **13 (030920) vs 26 (0604)** — the
  entire Risk 20→36 swing — and **all 14 boundary crossings are genuine Role-B verdict flips, candidate
  identity unchanged.** The lawyer sees "Risk / not-Risk"; the system means "B agreed this run / B didn't."
- **Counterfactual (integrity-failed votes → "not assessed" instead of silent non-confirming):**
  - Current-code runs: no integrity-failed votes → headline unchanged (13/26). The swing is genuine, not
    integrity — so an integrity fix would NOT stabilize the current headline.
  - Historical runs: A-empty findings were "2 confirmed + 1 NOT ASSESSED" = **pipeline-incomplete**, yet
    presented as 2-1 MEDIUM / non-Risk. Correctly marking them "directional verification incomplete" would
    have shown those runs as *incomplete*, not as "no directional risk found." The `directional Risk = 0`
    was an artifact of A-loss, not a clean negative.
- **What the UI calls "severity" that is only confirmation strength:** **100% of directional HIGH/MEDIUM/LOW
  labels** (they are the Pass-2 vote tally, line 1936). **Compound is the stable control** — its severity is
  a mapped value (`_severity_map.get(pattern_type)`, line 1528) + max-merge, with **0 persistent-severity
  flips** in every set and HIGH steady 3–5 — confirming the instability is specific to the
  confirmation-count mapping, not Stage 7 generally.

## ATTRIBUTION VERDICT
- **Stage 7 is the SOURCE** (Pass-2 directional verification), confirmed offline: candidate identities stable;
  variance entirely in Pass-2 per-role verdicts (Stage-7-internal).
- **Historically:** lost-vote/integrity failure (Role A empty directional output) dominated → **already
  contained by Step 370d/372c.**
- **On current code:** **genuine semantic verdict nondeterminism in Role B (GPT-5.4) at temp=0** dominates;
  integrity is clean. 14/14 current Risk swings are genuine-tally-driven.
- **Overarching design defect (regime-independent):** confirmation count == legal severity == Risk gate. It
  silently converted A's lost output into "lower severity/non-Risk" (historical) and converts B's verdict
  flip into "HIGH/Risk vs MEDIUM/non-Risk" (current). It mislabels verification strength as consequence.

## Branch decision (per the brief)
"Both occurred" historically — **but integrity failure (A-loss) is already fixed on current code**, so the
live-relevant branch is the **genuine-semantic** one:
1. **Run the formal frozen-input Stage-7 replay** (keyed machine; `_step370d_replay.py` harness) to quantify
   **Role B (GPT-5.4) directional verdict reproducibility** at temp=0 on identical input, and whether A/C
   stay stable. This is now a focused measurement (integrity already clean), not a hunt.
2. **Keep an integrity tripwire:** A-empty-output recurred across many historical runs; assert
   `unmatched_directional == 0 && status == complete` per run and surface "directional verification
   incomplete" instead of silently down-counting — so a future regression can't masquerade as MEDIUM again.
3. **The real architecture question (measure/spec, do NOT implement here):** split directional output into
   **(i) impact/materiality** and **(ii) verification strength**, so the Risk headline stops reporting
   "unanimous-this-run" as legal severity. This aligns Stage 7 with the confidence-vs-consequence doctrine
   enforced everywhere else (Architecture A Guardrail #3).

## DO-NOT / status (unchanged)
- No change to prompts, routing, severity mapping, Risk/Priority logic, model assignments, or UI labels.
- **374Z verified; Risk-headline stability NOT validated.** External demo / Joshua use of Risk totals,
  Priority totals, and Stage-7 directional counts remains **PAUSED**.

## Decisions Needed
1. Authorize the focused frozen-input replay measuring **GPT-5.4 (Pass-2 B) reproducibility** + unanimity-as-
   Risk-gate appropriateness (keyed env; I cannot run it here).
2. Greenlight specing the **two-output directional model** (impact vs verification) as the architectural
   follow-up — the confirmation-count-as-severity defect persists even with a perfectly stable B.
