# Step 374R-Q — Status: Priority-Risks basis recompute (READ-ONLY, MEASURE don't enforce)
**Date:** 2026-06-03  **Mode:** read-only analysis. **NO production file modified** — `app.js` / `index.html`
unchanged since v462 (Step 374Q); no hard_flag / escalation / routing / count / Priority logic touched.
Recompute is a sidecar over the existing run JSONs: `build_log/_374rq_recompute.py`. n=2 → DIRECTIONAL ONLY.

---

## ⚠️ Scoping-correction check — the instruction's LP-28/LP-32 split does NOT hold
The instruction asked me to confirm "LP-28 tie-derived (artifact) vs LP-32 genuine severe (real basis)"
and to **report any LP where `tie_derived_severe` disagrees with the 374P sidecar.** Recomputing
`tie_derived_severe` from the raw element verdicts:

| LP (181402) | per-evaluator LP verdict | derivation | sev_prod | sev_if_tie_optimistic | **tie_derived_severe** |
|---|---|---|---|---|---|
| LP-28 | C=missing, A=present, B=present | C via **pessimistic_tie_break** (3-present / 3-missing = 50/50 tie) | severe | none | **TRUE** |
| LP-32 | A=missing, C=present, B=present | A via **pessimistic_tie_break** (4-present / 4-missing = 50/50 tie) | severe | none | **TRUE** |

**Both are tie-derived.** LP-32's `A=missing` is itself a 4-4 pessimistic tie-break (optimistic roll → present;
`severity_if_tie_optimistic="none"`), structurally identical to LP-28's C=missing 3-3 tie-break. The recompute
**agrees with the 374P sidecar** (both TRUE) and **contradicts the instruction's scoping correction** (which
asserted LP-32=FALSE/genuine). The premise that LP-32 is a "genuine A=missing vs C/B split" is not supported:
at the LP-rollup level A's "missing" is a coin-flip tie-break, not a standalone evaluator conclusion.

### …but both ALSO carry a genuine, non-artifact basis (element level)
Examining elements explains the instruction's intuition and gives the real remedy. Beyond the (artifactual)
LP-rollup severe, BOTH members have an independent, non-tie signal:

- **LP-28** — (a) a **genuine element-level severe dispute**: element "Future changes in law … (who bears
  cost)" → C=missing vs A=present, B=present (a real per-element disagreement, not a rollup tie); and (b) a
  **unanimous critical-missing** element: "Grandfathering for pre-existing non-compliant conditions" → all 3
  evaluators `missing`. Consequence assessed **high**.
- **LP-32** — a **unanimous critical-missing** element: "Landlord's representations on pre-existing
  contamination" → all 3 evaluators `missing`. Consequence assessed **high**.

So the correct reading is **symmetric, not asymmetric**: each member's *displayed* "LP-level severe
disagreement" basis is a tie artifact (false), while each has a *true* alternate basis (critical-missing
element + assessed-high consequence; LP-28 additionally a real element-level dispute). Neither should be
presented as Priority *because of a severe disagreement*; both can legitimately remain Priority on
consequence / critical-missing grounds. This is exactly the "right outcome, false stated basis" pattern.

---

## Priority-Risks membership (baseline)
`isPriorityReview` = coverage LP in **risk** bucket with `hard_flag` **OR** synthesis card with HIGH severity.

| run | PR total | coverage members | synthesis-HIGH members | tie-derived coverage members |
|---|---|---|---|---|
| 030920 | 16 | **0** | 16 | none |
| 181402 | 28 | 2 (LP-28, LP-32) | 26 | **LP-28, LP-32** |

030920 has **no** coverage Priority member (its severe LPs are floored to Needs Review, not risk-bucket) →
no tie-derived contamination at the Priority tier. Synthesis-HIGH members carry their own HIGH severity (not
an LP-rollup tie) and are **out of scope** for the artifact question — no policy below moves them.

---

## 4-policy recompute (production preserved)

### Run 030920 (PR=16, zero coverage members — nothing to move)
| policy | PR | LPs leaving | displayed basis change | genuine assessed-high demoted | residual masquerade |
|---|---|---|---|---|---|
| P4 baseline | 16 | — | — | none | none |
| P1 provenance-pure | 16 | — | — | none | none |
| P2 consequence-first | 16 | — | — | none | none |
| P3 combined-evidence | 16 | — | — | none | none |

All four identical — clean. No tie-derived Priority basis exists on this run.

### Run 181402 (PR=28 = 2 tie-derived coverage + 26 synthesis-HIGH)
| policy | PR | LPs leaving | displayed basis for LP-28 / LP-32 | genuine assessed-high demoted (must be NONE) | residual masquerade |
|---|---|---|---|---|---|
| **P4 baseline** | 28 | — | "severe disagreement" (hard_flag) — **FALSE** (tie artifact) | none | **LP-28, LP-32** |
| **P1 provenance-pure** | **26** | **LP-28, LP-32** | basis removed → both LEAVE Priority | **❌ LP-28, LP-32** (both assessed **high** + genuine critical-missing) | none |
| **P2 consequence-first** | 28 | — | **"high assessed consequence"** (TRUE) | none | **none** ✓ |
| **P3 combined-evidence** | 28 | — | **"high consequence + critical element missing / element-level dispute"** (TRUE) | none | **none** ✓ |

Notes:
- **P1 FAILS** the gate: it demotes LP-28 and LP-32, both of which have genuinely assessed **high**
  consequence and a unanimous critical-missing element — these are real Priority items, not artifacts. P1
  throws out the baby (consequence) with the bathwater (tie-derived disagreement framing).
- **P4** leaves the masquerade in place: both members are presented as Priority *because of* a severe
  disagreement that was tie-manufactured.
- **P2 PASSES**: keeps PR=28, no demotion, and replaces the false "severe disagreement" basis with the true
  "high assessed consequence". Minimal, exit-criteria-shaped (relabel only, evidence trail intact).
- **P3 PASSES with identical PR outcome here** (both members happen to carry corroboration), and yields an
  even *truer*, more specific basis (names the critical-missing element / the genuine element dispute). It is
  stricter — it WOULD drop a tie-derived assessed-high member that lacked any independent element signal —
  but no such member exists in this n=2 set, so P2 and P3 are indistinguishable on outcome today.

---

## Answers to the required per-policy questions (181402, the only run with movement)
- **Priority Risks count:** P4=28, P1=26, P2=28, P3=28.
- **LPs entering/leaving:** only P1 moves any (LP-28, LP-32 LEAVE). P2/P3 move none. None enter under any policy.
- **Displayed basis per affected LP:** P4 "severe disagreement" (false); P1 removed; P2 "high assessed
  consequence" (true); P3 "high consequence + critical-element-missing / element-level dispute" (true).
- **Genuine assessed-high Risk incorrectly demoted:** **P1 only** (LP-28, LP-32). P2/P3/P4 demote none.
- **Residual tie-derived-as-disagreement masquerade:** **P4 only** (LP-28, LP-32 shown as "severe
  disagreement"). P1/P2/P3 eliminate it.

---

## Recommendation (INPUT to a doctrine decision — NOT the decision)
**P2 (consequence-first)** best satisfies "true basis, no genuine demotion" with the smallest footprint: it
retains the correct Priority OUTCOME (genuine high consequence warrants first attention) while replacing the
false "severe disagreement" BASIS with "high assessed consequence". No genuine demotion; masquerade removed;
pure relabel (evidence trail untouched) — the same shape as the 374Q containment.

**P3** reaches the identical Priority set on this data and arguably states an even truer basis (the actual
critical-missing element), but it depends on a corroboration-signal detector that is unvalidated at n=2;
treat it as the eventual target IF element-level corroboration detection proves robust across more contracts,
not as the first patch.

**P1 is blocked** — it demotes genuinely high-consequence Priority items (fails the no-genuine-demotion gate).

### Caveats for the decision
- **The instruction's LP-28/LP-32 asymmetry is incorrect** — both are tie-derived at the LP-rollup level, and
  both have a genuine alternate basis. Any 374S basis-relabel must treat them **symmetrically** (both get the
  same "consequence/critical-missing" basis), not relabel one and leave the other.
- **n=2 is directional only.** 030920 contributes zero coverage Priority members, so the entire signal rests
  on two LPs in one contract. NEEDS MORE CONTRACTS before any enforcement.
- This step authorizes/blocks nothing on its own; it is the comparison that a later narrow basis-relabel
  patch (374S) would have to clear exit criteria against (no genuine escalation demoted; evidence trail
  intact; provisional; documented), as 374P did for 374Q.

## Out of scope / not done
NO production change; NO policy enforced; NO hard_flag / escalation / routing / count / Priority logic
touched. Provenance fields not surfaced lawyer-facing. Production byte-identical to post-374Q (v462).

## Decisions Needed
1. **Doctrine call:** adopt P2 (relabel Priority basis to consequence-based, applied symmetrically to LP-28
   and LP-32) as the 374S target? — pending more contracts.
2. Acknowledge the scoping-correction reversal: the instruction's "LP-32 genuine" premise is not supported by
   the data; confirm the symmetric treatment before any 374S patch is drafted.
