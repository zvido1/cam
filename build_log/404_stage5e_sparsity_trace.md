# 404 — Stage 5e `use_impact` Sparsity Trace (read-only, code-only)

**Date:** 2026-07-05
**Type:** Read-only investigation. CODE read only. NO run instrumentation (not needed — code fully explains it). NO code change. NO pipeline change. NO prompt change. NO `cam/core/`. NO commit by Chat.
**Author:** Chat
**Question (from `build_log/NEXT_stage5e_sparsity_investigation.md`):** Why does assessed `use_impact` attach to only 7–9 of 32 Mode C coverage cards across repeated runs of the same lease, and why does the assessed set move run-to-run?

**Method:** Read `cam/adapters/lease_review/lease_use_impact.py` in full. The census artifacts (399/399b/399c) tell us WHICH cards got `use_impact`; this trace answers WHY the others didn't, from source. Per the spine doc's ladder, Rung 1 (code read) was attempted first and is sufficient — Rung 2 (run instrumentation) is NOT warranted, because the eligibility logic is deterministic and fully accounts for both the count and the run-to-run movement.

---

## 0. Freeze status (confirm before any future change)

Stage 5e lives at `cam/adapters/lease_review/lease_use_impact.py` — an **adapter**, NOT `cam/core/`. It is outside the patent freeze boundary.

Caveat with teeth: the file's **governance-merge rules** (`_merge_verdicts`: 3-0 → assert, 2-1 → assert_weak, 1-1-1 → context_dependent; materiality = most-conservative) are an *instance* of the core epistemic semantics. Any change to the MERGE logic should be treated with core-level caution even though the file sits in adapters. The **eligibility filter** (`_should_assess`) is plain domain-adapter infrastructure and is freely modifiable. The unblock below touches only `_should_assess`, not the merge. This distinction matters for patent prosecution and must be stated in any handoff.

---

## 1. Exact eligibility / invocation path (from code)

Single gate: **`_should_assess(a)`**. In `assess_use_impact()`:

```python
flagged = [a for a in coverage_assessment if _should_assess(a)]
if not flagged:
    return coverage_assessment, {... "status": "no_flagged_lps"}
```

Only `flagged` LPs are put into the batched evaluator prompt and receive a `use_impact` key. Everything not flagged is returned untouched — no `use_impact` attached, ever.

`_should_assess` returns True for exactly three cases:

```python
def _should_assess(a):
    state = a.get("coverage_state", "")
    if state == "missing":       return True
    if state == "review_needed": return True
    if state == "partial":
        evs = a.get("element_verdicts") or []
        if not evs: return False
        n_present = sum(1 for e in evs if e.get("verdict") in _PRESENT_VERDICTS)
        n_total   = len(evs)
        return n_total > 0 and (n_total - n_present) / n_total >= 0.5
    return False
```

- `missing` → always eligible
- `review_needed` → always eligible
- `partial` → eligible **only if** it has element_verdicts AND missing-element fraction **≥ 0.5** (at least half the elements are not in `_PRESENT_VERDICTS`)
- everything else (`covered`, `covered_unfavorable`, `not_applicable`, `potentially_unenforceable`, `partial` with < 50% missing) → NOT eligible, filtered out up front

`_PRESENT_VERDICTS = {explicitly_present, implicitly_present, covered_by_default_law, covered_in_other_LP}`.

Invocation is a single batched call per evaluator over all flagged LPs (ThreadPoolExecutor, max_workers=3). There is no per-LP call, no cap, no LP allow-list, no subset, no prompt-size gate, no downstream prune.

---

## 2. Why only a minority get `use_impact` — WHICH mechanism

**Mechanism = up-front eligibility filter (SKIPPED-BY-FILTER). Not null-result, not prune, not cap, not nondeterministic selection.**

Distinguishing the four mechanisms the spine doc named:

- **never ran / skipped by filter** ← THIS. The 23–25 unassessed cards fail `_should_assess` and are never sent to the evaluators. This is the dominant and essentially sole mechanism.
- **ran-and-returned-null** — possible in principle (a flagged LP the evaluators omit falls to a `context_dependent`/`no_evaluators` default in `_merge_verdicts`), but that still ATTACHES a `use_impact` dict. So a null-result card would still count as "assessed" in the census. It does not explain missing `use_impact`. Not the mechanism.
- **pruned downstream** — no prune step exists. Not the mechanism.
- **cap** — no cap exists. Not the mechanism.

The dominant exclusion is the **`partial` + 50%-threshold branch**. Most of the 32 LPs land as `partial` with majority-present elements (< 50% missing) and are filtered out — even when their consequence would be harmful on the one missing element that matters. This is exactly consistent with the 399/399b census: the stable-core assessed cards (LP-03, LP-05, LP-14, LP-16, LP-20, LP-32, +LP-10) are all `missing` / `review_needed` / high-gap `partial`; the excluded majority are covered-or-lightly-partial.

**Cross-check against 399c's own field dump (July run `443e33`):** LP-16 is `partial` / `partial_typical` yet assessed — so it cleared the 50% gate (its element_verdicts were ≥50% missing). LP-10 is also `partial`/`partial_typical` and assessed. Both are consistent with the gate: `partial_class` (typical vs material) is a SEPARATE downstream field and is NOT what `_should_assess` keys on — `_should_assess` keys on the raw element_verdict present/absent ratio. Do not conflate the two `partial` sub-signals.

---

## 3. Intentional, accidental, or bug

**Intentional by design, defensible original rationale, but the design predates the Priority Exposure goal — so it is the WRONG gate for the new purpose, while being CORRECT for its original one.**

The module docstring states the scope explicitly: assess only `missing` / `review_needed` / `partial with ≥50% missing elements`. Rationale is cost/scope: don't spend three evaluator calls assessing well-covered provisions. Not a bug — the filter does exactly what it was written to do.

The mismatch: the 50% `partial` threshold is a **coverage-completeness** criterion. It is orthogonal to **consequence severity**. A card can be 60% covered (fails the gate) and still carry a harmful gap on its single most important missing element. So for a consequence-led Priority Exposure surface, this gate systematically excludes exactly the cards that a "biggest traps first" view most needs to reason about. The gate is right for "where is coverage thin"; it is wrong for "where is the client most exposed."

This is the crux finding: **sparsity is a designed coverage-gate; Priority Exposure needs a consequence-gate. They are different questions and the current filter answers only the first.**

---

## 4. Run-to-run movement: UPSTREAM-FIELD-DRIVEN, not selection-driven

**`_should_assess` is fully deterministic.** Given the same `coverage_state` and `element_verdicts`, it returns the same answer every run. No RNG, no sampling, no cap-induced churn, no nondeterministic pick.

Therefore the July appearance of LP-02 and LP-28 (not assessed on 2026-06-11, assessed on 2026-07-05) can ONLY mean their **upstream inputs changed** between runs:
- their `coverage_state` moved (e.g. into `review_needed`, which is unconditionally eligible), OR
- their `element_verdicts` shifted enough to cross the ≥50%-missing line.

This traces to Stage-5-UPSTREAM nondeterminism — the same DEF-010 coverage/consequence instability already catalogued (the LP-05 flip family) — NOT to anything inside 5e's selection. 5e selects deterministically; what it selects FROM wobbles.

The census's "stable core + growing edge" pattern is the exact signature of a **deterministic gate sitting on a slightly nondeterministic upstream**: cards parked well inside or well outside the threshold stay put every run; cards sitting NEAR the 50% boundary, or near a `partial`↔`review_needed` state line, flip eligibility when the upstream verdicts wobble across the line.

**Two distinct churn sources, different causes (important — do not merge them):**
- **Eligibility churn** (LP-02/LP-28 appearing/disappearing) → UPSTREAM of 5e (coverage_state / element_verdict instability moving cards across the gate). Fixing this = stabilizing upstream coverage, OR removing the boundary the wobble crosses (broaden the gate).
- **Value churn** (LP-05's three classifications: context_dependent/1-1-1 → beneficial/2-1 → harmful/2-1 across three runs) → INSIDE 5e's evaluators (genuine 3-way model disagreement on an under-determined clause). This is not an eligibility question at all; it is the evaluators honestly disagreeing on an under-determined clause, collapsed by the governance merge. Broadening the gate does not fix (and slightly widens the surface for) value churn.

---

## 5. What honest Priority Exposure requires

To rank consequence across all 32 cards, you must broaden what gets ASSESSED. This is an eligibility-filter change, not a merge change, not a core change. Options, cost-ordered:

1. **Cheapest / smallest — lower or drop the `partial` 50% threshold** so all `partial` cards are assessed regardless of gap fraction. Pulls most of the excluded 23–25 into the evaluated set.
2. **Fuller — assess all applicable LPs** (everything except `not_applicable`, and a decision on whether to include fully `covered`). Maximum consequence coverage.

**Cost note (matters for the decision):** the architecture already sends ONE batched call per evaluator covering ALL flagged LPs. Broadening eligibility grows the PROMPT (more LPs listed in `_build_user_prompt`), it does NOT multiply the call count. Marginal cost is input tokens + a larger single response, not 3× more API round-trips. So broadening is cheaper than the "3 calls per card" intuition suggests. Watch two real ceilings: (a) `max_output_tokens=3000` per evaluator must hold all LP verdicts in one JSON object — 32 LPs of `{use_consequence, materiality, use_reasoning}` should fit, but this is the thing to verify if broadened; (b) the `_build_user_prompt` "PROVISION GAPS TO ASSESS" list grows, but each line is short.

**A second, honesty-preserving caveat:** broadening pulls more under-determined clauses through the evaluators. The LP-05 evidence says the evaluators genuinely wobble on such clauses. So broadening WILL widen the surface for run-to-run value churn. That is not a reason not to broaden — it is a reason the Priority Exposure surface must render `context_dependent` / low-agreement HONESTLY (show the split, don't rank a 1-1-1 as hard signal). Consistent with the existing doctrine: agreement-on-direction ≠ agreement-on-harm; the refined-minority doctrine; over-withhold is the unforgivable failure.

---

## 6. Minimal display-only mitigation in the meantime

**None warranted beyond what 400 already shipped.** The 400 provenance chips (Assessed vs Default materiality; Lease-specific vs Default exposure) already mark the assessed 7–9 as distinct from the unassessed 23–25 — that is the honest floor and it is done. Sorting or surfacing the 7–9 as "priority" while 23–25 remain structurally unassessed would reintroduce confidence theater at the top of the product — exactly what 399 warned against. The real move is the eligibility broadening in §5, which is a pipeline change (Code), not display.

---

## Answers to the required-report questions (spine doc §"Required read-only report")

1. **Exact Stage 5e eligibility/invocation path:** `_should_assess(a)` gate; `flagged` = cards passing it; batched 3-evaluator call over `flagged` only. §1.
2. **Why only a minority + which mechanism:** SKIPPED-BY-FILTER (up-front eligibility), dominated by the `partial` ≥50%-missing threshold. Not null/prune/cap/selection. §2.
3. **Intentional / accidental / bug:** intentional coverage-scope gate, correct for its original purpose, wrong gate for the consequence-coverage goal. Not a bug. §3.
4. **Run-to-run movement upstream or selection:** UPSTREAM-field-driven (coverage_state / element_verdicts wobbling across a deterministic gate). Selection is deterministic. Distinct from the separate INSIDE-5e value churn (LP-05). §4.
5. **What Priority Exposure honestly requires:** broaden `_should_assess` (lower/drop the partial threshold, or assess all applicable). Adapter change, not core, not merge. Cost is prompt tokens, not call count. Must render context_dependent honestly. §5.
6. **Worthwhile display-only mitigation meanwhile:** none beyond 400's chips. §6.

---

## Decision fork (per spine doc — NOT pre-committed)

The trace lands on the **"broaden use-impact assessment"** fork. It is the honest unblock, it is an adapter change outside the freeze, it does not touch merge semantics, and its cost is prompt tokens not call count. Open sub-choice for Tzvi: how far to broaden — all-`partial` (smallest) vs all-applicable (fullest). The other forks (limited Priority Exposure on the assessed subset only / consequence-aware partial escalation / badge split) do not require this change and remain available, but none of them removes the underlying sparsity — only broadening does.

**Not taken here.** No build. Recorded as the read-only trace the spine doc asked for.

## Discipline

- DIRECTIONAL. One lease, reasoning from two run artifacts + source. NOT promoted. NOT patent record.
- No code, no pipeline, no prompt, no commit authorized by this note. It is a code-read report.
- Stage 5e = adapter (not frozen); its merge rules are a core-semantics instance and must not be altered under the guise of an eligibility tweak.
