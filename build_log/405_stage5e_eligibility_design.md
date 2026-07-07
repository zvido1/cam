# 405 — Stage 5e Eligibility Design / Preflight

**Date:** 2026-07-07 (revised 2026-07-07)  
**Type:** Design/preflight only. NO code, NO prompt, NO model call, NO pipeline change, NO cam/core/ change.  
**Author:** Claude Code (read-only investigation + design)  
**Precondition:** 404 sparsity trace committed `a262c92`.

---

## 0. 404 Finding Summarized

Stage 5e (`cam/adapters/lease_review/lease_use_impact.py`) gates coverage LPs through `_should_assess(a)`. The gate passes `missing` and `review_needed` unconditionally; `partial` only if ≥50% of element_verdicts are not in `_PRESENT_VERDICTS`; everything else is filtered out and never sent to evaluators. The dominant exclusion is `partial` LPs whose elements are mostly-present (< 50% missing). On two Atlas runs this accounts for 23–25 of 32 LPs receiving no `use_impact`. The gate is deterministic; run-to-run eligibility churn is upstream coverage-state / element-verdict wobble crossing the 50% boundary, not selection nondeterminism inside 5e.

---

## 1. CRITICAL — Prior-Record Verification (Question 1): 375J vs 375M vs COV-A

### The apparent tension

**375J framing (CAM_Current_State.md, line 665–669):**
> *"375E-COV (widen the 8/32 gate + add `materiality_source`) now GATES 375E-DIR, not the reverse. Shipping source-strict routing (C) before widening 5e would crash the lawyer-facing Risk count from 26→7 — its own instability, opposite direction."*

This reads as: COV = LP-level gate widening for coverage LPs, and it is the blocker for source-strict routing.

**375M reframe (CAM_Current_State.md, lines 682–686), marked settled:**
> *"THE COV REFRAME (settled): COV is NOT LP-eligibility widening — it is FINDING-LEVEL consequence-provenance. The 50%-threshold was a coverage-completeness heuristic impersonating a consequence-need gate (same axis-impersonation as gap_impact). Real invariant: a finding that requires action routing needs assessed consequence; entry attaches to the FINDING."*

This reads as: COV = directional-FINDING consequence provenance, not LP gate widening. The 50% threshold is called out by name as the wrong gate, but the "fix" is attaching consequence at the finding level, not lowering the LP threshold.

### Resolution

**These do NOT coexist as co-equal options. 375M supersedes 375J's "widen the LP gate" framing for the DIRECTIONAL finding layer.** The reconciliation is:

The 375J "8/32 gate" concern was about DIRECTIONAL findings (the 26 directionals in the 52adbf artifact). COV-A's scope was those 18 unassessed directional findings — findings that went through Stage 7 (`cross_provision_findings`), not through the coverage LP `_should_assess` path. COV-A implemented `assess_finding_consequence()` in `cam/adapters/lease_review/lease_finding_consequence.py` — a SEPARATE module that calls 5e with finding-level context, leaving `lease_use_impact.py`/`_should_assess` entirely untouched.

The 375M reframe therefore APPLIES to the directional-finding layer and says: for those, "LP-eligibility widening" was the wrong frame; finding-level consequence provenance is the right frame. The reframe does NOT apply to, and does NOT resolve, the coverage-LP `_should_assess` 50% gate question. That question was explicitly deferred behind 375H characterization (quote from line 674–676): *"COV is the first step that changes HEADLINE behavior... and its gate-widening shape DEPENDS on a 375H characterization not yet done."*

**Summary of what the 375M reframe settled and what it left open:**
- SETTLED: For directional findings, consequence attaches at the finding level via `assess_finding_consequence()`. Do not widen the LP-coverage `_should_assess` gate as a proxy for that.
- LEFT OPEN (explicitly deferred): Whether and how to widen `_should_assess` for coverage LPs to support a Priority Exposure surface. The 375J "widen the gate" language correctly identifies sparsity as a problem; 375M correctly identifies that directional findings should not be the unit. Neither addresses Mode C coverage-card consequence coverage.

### Was COV-A ever built?

**Yes. COV-A, COV-A2, and COV-A2b are confirmed in git history on `main`:**

```
8de0d74  Step 375E-COV-A2b: read actual Stage-7 directionality into stage7_direction
fc8d3dc  Step 375E-COV-A2: consequence-independence prompt fix (COV-A correction)
771f1ef  Step 375E-COV-A: G-cand finding consequence provenance (populate/record only)
```

Git commit `771f1ef` shows files changed: `cam/adapters/lease_review/lease_finding_consequence.py` (new module). Confirmed on disk: the file exists at `cam/adapters/lease_review/lease_finding_consequence.py`, operates on `cross_provision_findings` (Stage 7 directional output), and does NOT touch `_should_assess` or `assess_use_impact`.

**The current `_should_assess` still contains the raw 50% threshold (confirmed from disk at lines 86–100 of `lease_use_impact.py`).** This is consistent with COV-A's design: COV-A was deliberately scoped to directional findings and explicitly held routing-change-free. It was never intended to widen the coverage LP gate.

COV-A introduced a key provenance field, `use_consequence_source`, on directional findings — not on coverage LPs. The Mode C coverage card `use_impact` assessed-vs-unassessed situation is orthogonal to COV-A and remains exactly as it was before COV-A.

### Was 375H completed?

**Partially.** 375H Parts A+B were DONE (commit `b1159a0`, read-only, keyless). Quote from CAM_Current_State.md line 2279: *"✅ 375H Parts A+B DONE (SHA b1159a0, read-only). DOMINANT DEFECT = SCHEMA (not evaluator, not true-gap)..."*

**375H-C (the fixture-keyed repair) was NOT built.** It remains in the open build queue (line 497–500): *"375H-C — direction-sensitive present-term schema repair. The THIRD directional problem, never fixed: a present-but-one-sided clause (LP-09) scores 'covered' and bypasses directional review... GATES the external-use pause lift."*

Therefore the condition the CLEAN STOPPING SEAM stated — *"COV gate-widening shape DEPENDS on a 375H characterization not yet done"* — was partially satisfied (Parts A+B diagnosed the schema defect; Part C never fixed it). The 375H dependency was diagnostic ("understand what 375H finds before widening the gate"), not build-gated ("gate-widening must wait until 375H-C ships"). The diagnostic part is done and informs this design.

### Question 1 answers

1. **Does 375M supersede 375J?** Yes for the directional-finding layer. 375M settled that COV means finding-level consequence provenance, not LP-coverage gate widening, for directional findings. The 375J "widen the 8/32 gate" language was referring to directional findings and is superseded by the more precise 375M framing. The coverage-LP `_should_assess` gate question was explicitly deferred and remains open.

2. **Was COV-A built?** Yes. Commits `771f1ef`, `fc8d3dc`, `8de0d74` are on `main`. COV-A implemented finding-scoped consequence provenance for directional findings via a new module (`lease_finding_consequence.py`). It did NOT touch `_should_assess`. The 50% coverage threshold is still live in production today, exactly as 404 found.

3. **Does the prior record decide against LP-level widening or only defer it?** It DEFERS, with a specific condition (understand 375H). The 375M reframe says "COV is not LP-eligibility widening" in the context of directional findings. It does not say "never widen the LP coverage gate." The two design calls held for Tzvi (CAM_Current_State.md lines 843–850) include *"How to widen the gate — see step 3 above (gated on the 375H diagnostic)"* — the gate-widening question is explicitly held open, not rejected. The 375H diagnostic parts A+B are done; 375H-C is not built but the diagnostic characterization is complete enough to inform this decision.

---

## 2. Current Stage 5e Unit

Stage 5e is **LP-scoped**. `_should_assess(a)` receives a single LP assessment dict (keyed by `issue_area_id`, containing `coverage_state`, `element_verdicts`, and associated LP metadata). The batched call in `assess_use_impact()` sends all flagged LP dicts together in one user prompt and returns per-LP `{use_consequence, materiality, use_reasoning}` output.

`_build_user_prompt` (not inspected directly, but per 404 and the architecture) presents each flagged LP as a "provision gap to assess" — it is asking about LP-level coverage state, not about a specific lawyer-facing card or finding.

**Consequence:** Stage 5e in its current form correctly assesses LP-level consequence: "given that provision X is partially/fully missing, how consequential is that gap for this tenant?" It does NOT ask: "given this specific card that a lawyer will read, what consequence should they understand?" For directional/compound findings, the relevant consequence context is different (and COV-A addressed that separately). For coverage-only LPs, the current LP-level question is appropriate.

**Limitation — multi-finding-per-LP (LIVE, not resolved):** A single LP can carry multiple findings with different consequence contexts. The 375P precheck confirmed 0 such cases on the 52adbf lease (all finding↔LP is 1:1), but this is lease-specific, not a structural invariant. On a different lease, per-LP 5e assessment yields a single consequence estimate that gets silently shared across multiple cards with potentially conflicting consequence contexts — no error, no warning, just a wrong answer. Compound/CRX findings are the clearest case: COV-A correctly marks `compound_consequence_source: not_assessed` because per-LP 5e structurally cannot serve them. This limitation carries into any LP-level broadening and is NOT resolved by Option A. The yield run (§7) must check whether the 1:1 LP↔card assumption still holds on the test lease.

---

## 3. Future Eligibility Unit — Options A–E

### Option A: Assess all `partial` LPs (lower / drop the 50% threshold)

- **Implementation scope:** Change `_should_assess` to return `True` for all `partial` states, regardless of element_verdict present/absent ratio. One-line change in `lease_use_impact.py` (adapter, outside freeze). Preserves LP-level unit.
- **Likely data coverage:** Expands assessed set from 7–9 to an estimated 20–25 of 32 (all partial + existing missing/review_needed). Depends on how many LPs are partial vs covered/N-A.
- **Risk of wasted calls/tokens:** Low. Batch call grows (more LPs in one prompt), not more calls. LPs that are nearly-covered (5/6 elements present, 1 missing) will be assessed — consequence may be low, but that is a valid assessment result, not waste. Main token cost is prompt growth + larger single-response JSON.
- **Risk of mixing consequence contexts:** Low for coverage-only LPs. The LP-level question ("how consequential is the gap?") is still the right question; we're just asking it for more LPs.
- **Compatibility with action-type ontology:** Compatible. Broadening input to 5e doesn't change the merge semantics or the bucket routing.
- **Compatibility with Priority Exposure:** Good. More LPs with assessed `use_impact.materiality` → more data points for cross-bucket ordering.
- **Adapter-only vs broader-pipeline:** Adapter-only. No cam/core/ change required.
- **Option A is a CONTROLLED DIAGNOSTIC / PROTOTYPE scoped to Mode C coverage cards, not final architecture.** It is valid for the current view where coverage cards are ~1:1 with LPs. It silently fails when one LP carries multiple findings with different consequence contexts. See §4 (multi-finding caveat, live) and §7 for full rationale.

### Option B: Assess all non-NA / non-covered LPs

- **Implementation scope:** Change `_should_assess` to return `True` for all states except `not_applicable`, `covered`, and `covered_unfavorable` (perhaps also excluding `potentially_unenforceable`). Adapter-only.
- **Likely data coverage:** Near-maximal. Covered/N-A LPs genuinely don't have actionable gaps; this correctly excludes them.
- **Risk of wasted calls/tokens:** Slightly higher than A — includes LPs that are `review_needed` but might have minimal content for 5e to work with. In practice `review_needed` is already fully covered (unconditionally eligible today), so the marginal expansion over A is primarily from lightly-partial LPs.
- **Risk of mixing consequence contexts:** Same as A. Still LP-level.
- **Compatibility:** Same as A.
- **Note:** This is close to A in practice, since the currently-excluded population is dominated by below-50%-gap `partial` LPs.

### Option C: Assess all lawyer-facing cards that need consequence routing

- **Implementation scope:** Requires a card-to-LP mapping. Today's artifacts carry `issue_area_id` per coverage item but no stable per-card finding id beyond that. Coverage cards are 1:1 with LPs on Mode C (each LP generates one coverage card). So Option C reduces to Option A/B for coverage cards; the distinction only matters if a finding layer (directional/compound) also needs consequence routing through 5e.
- **Likely data coverage:** Same as B for coverage cards. The difference from A/B is conceptual: this option is "consequence follows findings," which is the 375M reframe applied to coverage cards, not just directional findings.
- **Risk:** If coverage cards are ever decoupled from 1:1 LP → this becomes the correct unit. Today it makes no practical difference vs B.
- **Compatibility with Priority Exposure:** Best conceptual fit — Priority Exposure is a lawyer-facing-card surface, so consequence should be card-scoped.
- **Adapter-only vs broader-pipeline:** Would require passing card context (not just LP dict) into 5e's prompt, which is a mild prompt change but still adapter-only.

### Option D: Assess only candidate Priority Exposure cards

- **Implementation scope:** Requires defining Priority Exposure criteria before assessing. Circular: Priority Exposure needs assessed consequence to rank; assessed consequence needs Priority Exposure criteria to filter.
- **Risk:** Tight circular dependency. Not viable as a standalone approach.
- **Verdict:** REJECTED as a first step. May be appropriate as a second-pass refinement after Option A/B establishes broader coverage.

### Option E: Hybrid — LP-level for coverage cards, finding-level for directional/compound

- **Implementation scope:** COV-A already built the finding-level path for directional findings. This option says "leave that in place, and additionally broaden LP-level 5e for coverage cards." In practice this is Option A/B for coverage + COV-A for directionals.
- **Likely data coverage:** Maximum. Coverage cards get LP-level consequence; directional findings get finding-level consequence.
- **Risk:** Complexity — two parallel consequence assessment paths. But COV-A's path is already live, so this is really just "build A/B for coverage" which is what the other options propose.
- **Compatibility:** This is the architecturally correct long-term design. LP-level for coverage gaps (is the gap consequential?); finding-level for directional/compound (is this specific adverse provision consequential?).
- **Verdict:** Implicitly correct long-term design; currently what COV-A + Option A/B together would produce.

---

## 4. Card/Finding Mapping

**Which lawyer-facing card types need assessed consequence?**

- Mode C coverage cards (partial/missing/review_needed): YES. These are the 32 items in `coverage_assessment`. Currently 7–9 get `use_impact`; the 23–25 remainder are exactly what broadening would reach.
- Directional synthesis findings: YES — COV-A addresses this already (finding-scoped consequence via `assess_finding_consequence()`).
- Compound/CRX findings: COV-A marks these `compound_consequence_source: not_assessed` (structurally forced, per 375P precheck). They require a multi-LP consequence context that per-LP 5e cannot provide. A finding-level approach (Option C/E) would eventually serve them, but this is out of scope for Stage 5e LP-level broadening.
- Improvement cards (covered_unfavorable, etc.): Arguably yes, but lower priority — the lawyer reads them as "negotiate for better terms," not "you're at risk."

**Does a stable card id exist for 5e to key on?**

Today: coverage cards key on `issue_area_id`. There is no separate per-card finding id beyond the LP id. For Mode C coverage, this is 1:1 (one card per LP) so it's sufficient. For future finding-level scoping (Option C/E), a finding id would be needed — but that infrastructure doesn't exist yet.

**Can multiple findings share one LP with different consequence contexts?**

**Structurally yes; on this lease, currently no — but this caveat is LIVE, not resolved.** The 375P precheck confirmed 0 LPs carry more than one directional finding on the 52adbf lease. But this is lease-specific. On a different lease, per-LP 5e assessment yields a single consequence estimate silently shared across all cards derived from that LP — including cards with different consequence contexts. There is no error signal when this happens; 5e returns one verdict and it stamps all cards regardless.

**This is the crux of the LP-vs-finding question.** For the current Mode C coverage use-case (one coverage card per LP), LP-level assessment is structurally correct for the coverage-card layer. The LP-vs-finding distinction becomes load-bearing when:
- A single LP appears in multiple finding contexts with different consequence implications (any lease where compound/directional findings overlap a coverage LP); OR
- Compound/multi-LP findings need consequence routing (already handled via `not_assessed` in COV-A, but that means they remain unranked on a Priority Exposure surface).

**Option A/B is sufficient ONLY as a diagnostic for the current Mode C coverage-card view.** It is NOT a general architecture for all lawyer-facing findings. For a cross-card Priority Exposure surface that includes directional and compound findings, finding-level consequence eligibility (Option C/E) is the necessary architecture. The yield run must check whether the 1:1 LP↔card assumption holds on the test lease, and record any multi-finding LP as a live risk for Option A's scope.

---

## 5. Prompt/Output Size Preflight

**Batch structure:** Current code sends ALL flagged LPs in one user prompt per evaluator, three evaluators in parallel. If broadened to all-partial (Option A), flagged LPs grow from ~7–9 to estimated ~20–25.

**Max output tokens: CONFIRMED at 3000 per evaluator.** Stage 5e sets `max_output_tokens: 3000` in `_EVALUATOR_LINEUP` in `cam/adapters/lease_review/lease_use_impact.py`. This is per-evaluator, not per-batch. The ceiling is a known constant, not something to discover in preflight — preflight goes straight to sizing measurement.

**Rough size check:**
- Per LP, 5e returns `{use_consequence, materiality, use_reasoning}`. The `use_reasoning` is a free-text explanation, typically 1–3 sentences.
- Estimate per LP in JSON: `~150–300 tokens` for the output (consequence/materiality labels + one reasoning sentence).
- At 25 LPs × 300 tokens = 7,500 output tokens — this EXCEEDS `max_output_tokens=3000`.
- At 15 LPs × 200 tokens = 3,000 output tokens — borderline.

**Conclusion: 3000 tokens is insufficient for all-partial broadening at 20–25 LPs if reasoning strings are included.** Truncated JSON → `safe_json_extract` failure is a real risk.

**Preferred mitigation: CHUNKING over raising `max_output_tokens`.** Chunking bounds the single-response failure surface — a truncated 25-LP response fails completely; two 12-LP responses fail independently and can be partially recovered. Raising `max_output_tokens` instead just moves the ceiling without reducing the blast radius of a single truncation. Preferred approach:
- Split the flagged LP batch into chunks of ~10–12 LPs per evaluator call.
- Each chunk gets its own `max_output_tokens=3000` call; results are merged before `_merge_verdicts`.
- This also makes the prompt/output size predictable at any future gate widening level.

**Secondary option:** Shorten `use_reasoning` to 1 sentence max (prompt instruction change) — reduces per-LP output to ~100–150 tokens, fits ~20 LPs in one call. Lower implementation cost but does not protect against future gate widening to 32 LPs.

**Token ceiling is the primary engineering risk and preflight must SIZE it before any live run.**

---

## 6. Run-to-Run Stability Implication

**Broadening REDUCES eligibility churn but EXPOSES more value churn.**

- **Eligibility churn (LP-02/LP-28 appearing/disappearing):** Caused by upstream coverage-state / element-verdict wobble crossing the 50% boundary. Removing the 50% boundary removes the gate the wobble crosses — LPs that were near-threshold become unconditionally included. This REDUCES eligibility churn for near-threshold LPs, at the cost of always running 5e on them.

- **Value churn (LP-05's three classifications across three runs):** Caused by model disagreement on under-determined clauses inside 5e's evaluators. Broadening to lightly-partial LPs will pull more such clauses into the assessed pool. Many of them will produce stable assessments (where the consequence is clear); some will produce genuine disagreement (where the consequence depends on context). Broadening DOES NOT fix value churn; it expands the population subject to it.

**The controlled diagnostic MUST run N≥2 on the same lease, same widened gate.** A single run is insufficient: 399b/404 found eligibility movement across runs (LP-02/LP-28 entered on Run B but not Run A). A single run would conflate eligibility churn with value churn — you can't tell whether a newly-admitted LP "got assessed" because it's stably eligible or because it happened to cross the coverage threshold on that particular run. Two runs on the same lease, same widened gate, disaggregate this:

- **Eligibility churn** (does an LP enter Stage 5e at all?): run-to-run LP set comparison. An LP is stably eligible if it appears in BOTH runs. An LP appearing in only one run is near-threshold in upstream coverage-state / element-verdicts and should be flagged as churn-susceptible.
- **Value churn** (how do evaluators classify consequence once admitted?): within-run vs cross-run comparison on the stable-eligible set. LP-05's pattern (three classifications across three runs) is the template: a `context_dependent`/1-1-1 result in one run and a `harmful`/2-1 in another are genuinely different answers, not noise.

**Do not conflate these.** A newly-admitted LP with stable eligibility (appears both runs) but flipping consequence (harmful→context_dependent) is a value-churn case: the evaluators honestly disagree on an under-determined clause. A LP that appears in one run only is an eligibility-churn case: the upstream coverage state wobbled. Priority Exposure design must handle both honestly — not rank a churn-susceptible LP as hard signal.

**Implication for Priority Exposure design:** The LP-05 evidence (three different classifications on three runs: `context_dependent`/1-1-1 → `beneficial`/2-1 → `harmful`/2-1) is the strongest warning. A Priority Exposure surface must:
- Render `context_dependent` / 1-1-1 disagreement results EXPLICITLY and near the top, labeled as "depends on context" — not buried because uncertain (per the over-withhold doctrine: showing an uncertain-but-potentially-high-exposure item is less wrong than hiding it).
- Never rank a 1-1-1 split as hard signal. Show the split pattern to the lawyer.
- Not present `agreement=2-1` assessments with the same confidence as `agreement=3-0`.

The LP-05 instability across three runs constrains Priority Exposure to a surface that communicates epistemic quality alongside consequence direction — it cannot be a clean "top 5 risks" list without acknowledging which entries are stable.

---

## 7. Recommendation

**Do not build Priority Exposure yet. Authorize Option A only as a controlled diagnostic / prototype for Mode C coverage cards, gated by token/chunking preflight and N≥2 yield measurement. Keep finding-level consequence eligibility as the likely final architecture for cross-card Priority Exposure.**

**Option A status: CONTROLLED DIAGNOSTIC / COVERAGE-CARD-SCOPED PROTOTYPE.** Not final architecture. Valid scope: Mode C coverage cards, current 1:1 LP↔card assumption. It is a diagnostic step that produces the yield data COV-B routing would need, the same logic that made COV-A "populate/record only, no routing change" before COV-B. All-partial broadening answers the primary empirical question: does 5e produce useful assessments on lightly-partial LPs, or does it abstain/produce noise?

**Option A is NOT a general architecture for all lawyer-facing findings.** It silently fails when one LP carries multiple findings with different consequence contexts (compound/CRX/directional overlap). For a cross-card Priority Exposure surface that includes directional and compound findings, finding-level consequence eligibility (Option C/E) is the necessary final architecture. That requires card-id infrastructure that doesn't exist yet; building it is a separate, later step.

**On the 375M binding question:** 375M settled "finding-level for directional findings" (COV-A implemented that, on `main`). It did NOT prohibit coverage-LP broadening. The two are orthogonal:
- Directional findings → finding-level consequence (COV-A, already built).
- Coverage LPs → LP-level consequence assessment (current 5e), gate question deferred; 404 confirmed the 50% threshold is still live.

**On whether LP-level broadening is rejected or deferred:** DEFERRED, with 375H diagnostic as the stated condition (Parts A+B done; Part C not built but the diagnostic characterization is sufficient to proceed with a prototype). 375M does not prohibit it. 404 calls the 50% threshold "the wrong gate for the new purpose" (Priority Exposure). The case for a diagnostic prototype is sound.

**Explicit non-goals for the diagnostic prototype:**
- Do NOT change merge semantics or governance rules.
- Do NOT change bucket routing (`classifyFindingType`, `sevTriage`).
- Do NOT implement Priority Exposure ranking — broadening is the precondition, not the implementation.
- Do NOT patch `cam/core/`.
- Do NOT bundle with COV-B routing design (that requires seeing the corrected yield distribution first).
- Do NOT raise `max_output_tokens` — use chunking instead (§5).

**Step sequencing — gates are sequential, no step skips:**

1. **Chunking preflight (no tokens spent):** Implement LP-batch chunking (10–12 LPs per sub-call per evaluator). Verify `_build_user_prompt` and `safe_json_extract` handle split batches correctly. Run against a synthetic `coverage_assessment` fixture (20 mock LPs, no model call) to confirm prompt builds without error and mock JSON parses successfully at the expected per-chunk size.
2. **N≥2 keyed yield run on Atlas Meridian:** Run Option A (all-partial widening + chunking) on the known lease, at least two full pipeline runs. Measure and report separately:
   - **Eligibility churn:** Which LPs appear in both runs (stably eligible) vs one run only (churn-susceptible near the old 50% boundary).
   - **Value churn:** Among stably-eligible LPs, compare consequence classifications across runs. Flag any LP with differing verdicts as a value-churn case.
   - **Yield:** How many newly-admitted partial LPs return decisive (3-0 or 2-1) vs context_dependent vs abstain results? This is COV-A's gate-vs-yield question applied to coverage LPs.
   - **Multi-finding check:** Confirm 1:1 LP↔card assumption holds on this lease; record any LP appearing in multiple finding contexts.
3. **Only after yield confirmed:** Design Priority Exposure surface against the corrected distribution and stable-eligible set.

---

## Validation Plan

**Gate 1 — chunking preflight (no tokens spent, must pass before any live run):**
- [ ] Read `_build_user_prompt` in full — confirm per-LP payload and verify the size estimate is grounded.
- [ ] Implement LP-batch chunking (10–12 LPs per sub-call); confirm `max_output_tokens=3000` is sufficient per chunk.
- [ ] Synthetic dry-run fixture (20 mock LPs, no model call): prompt builds without error; `safe_json_extract` parses a mocked per-chunk JSON response correctly; results merge cleanly across chunks.
- [ ] Confirm `use_adjusted` behavior: broadening must not inadvertently trigger `coverage_state` rewrites (`use_adjusted` is set separately — verify).

**Gate 2 — N≥2 keyed yield run (requires Gate 1 passed):**
- [ ] Run Option A (all-partial + chunking) at least twice on Atlas Meridian, same lease.
- [ ] Report **eligibility churn**: which LPs appear in both runs (stably eligible) vs one run only.
- [ ] Report **value churn**: among stably-eligible LPs, compare consequence classifications across runs; flag differing verdicts explicitly.
- [ ] Report **yield**: decisive (3-0 or 2-1) vs context_dependent vs abstain among newly-admitted partial LPs. Baseline: COV-A's G-cand lane was 14/18 decisive on directionals.
- [ ] Report **multi-finding check**: confirm 1:1 LP↔card assumption holds on this lease; note any multi-finding LP as a live scope risk for Option A.
- [ ] Do NOT design Priority Exposure surface until yield and churn reports are reviewed by Tzvi.

---

## Files involved (read-only for this step)

- `cam/adapters/lease_review/lease_use_impact.py` — `_should_assess` gate (lines 86–100), `assess_use_impact` (line 341), `_build_user_prompt`, `max_output_tokens` setting.
- `cam/adapters/lease_review/lease_finding_consequence.py` — COV-A's separate finding-scoped path (operates on `cross_provision_findings`, not `coverage_assessment`; no change needed here).

---

## Explicit Non-Goals (this step and the proposed prototype)

- NOT redefining Risk.
- NOT patching `sevTriage()` to route `medium+harmful→HIGH`.
- NOT building COV-B routing or Priority Exposure ranking.
- NOT changing `_merge_verdicts` governance rules.
- NOT touching `cam/core/`.
- NOT building a "finding-level" coverage-card unit (Option C) in this step — correct long-term direction for cross-card Priority Exposure but requires card-id infrastructure that doesn't exist yet.
- NOT treating Option A as final architecture for cross-card Priority Exposure (directional/compound/multi-finding-per-LP cases excluded by design).
