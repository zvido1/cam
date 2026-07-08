# 408B — Compound Consequence Build Spec

**Date:** 2026-07-08
**Type:** Build spec (implementation design). **No code written. No implementation. No model calls. No push.**
**Predecessor:** 408A (`build_log/408A_compound_finding_record_shape.md`, committed `c84d8aa`) settled the architecture. This spec is the implementation plan for Claude Code to execute in a later, separately-authorized step.
**Scope guardrails:** No `cam/core/` change. No `_merge_finding_verdicts` change. No routing/bucket change. No Priority Exposure. No default flips.

---

## 1. Executive summary

408A proved the compound-consequence gap is confined to ONE function: the prompt-input builder. COV-A's `_merge_finding_verdicts` governance/provenance layer is `finding_id`-keyed and LP-count-agnostic, so it is reused unchanged. 408B adds a **compound-aware prompt-input builder** and a **routing branch** in `assess_finding_consequence` that sends `finding_type == "compound_risk"` findings through the existing evaluator lineup and existing merge, then writes the result back onto the compound finding keyed by `finding_id`.

The single largest hazard is prompt contamination. COV-A1 verified (3-0, repeatable, sign-inverting) that feeding Stage 7's adverse framing to the consequence evaluator corrupts the answer. The compound finding's `headline`/`title`/`detail` are MORE strongly pre-framed than the directional titles that caused A1. Therefore the compound builder must feed neutral clause facts only and quarantine every Stage 7 conclusion field as provenance.

The single largest build dependency is section-resolved lease text for `cited_sections`. **RESOLVED (was Open Question 1):** the full lease text IS available at the call site. In `run_lease_coverage_only` (`lease_adapter.py`), `tenant_text` is in local scope throughout and is already passed to `run_synthesis(full_tenant_text=tenant_text, ...)`, but the `assess_finding_consequence(...)` call one block below does NOT pass it. The fix is a one-argument thread: add `full_tenant_text=tenant_text` to that existing call. No new parse, no new plumbing — the data is real and one keyword away. Per-LP `tenant_text` (already on `coverage_assessment`) remains the fallback.

**Compound consequence is NOT assumed harmful.** Stage 7 emitting `compound_risk` is a directional/pattern signal, not a consequence verdict. The evaluator must be free to return beneficial / neutral / context_dependent, exactly as the directional lane can.

---

## 2. 408A findings carried forward (the fixed constraints)

1. Reuse `_merge_finding_verdicts` unchanged (DEF-003 support floor + DEF-004 materiality majority apply as-is; both are LP-count-agnostic).
2. Store compound consequence on the compound finding, keyed by `finding_id`. Never on any LP.
3. No second governance/merge lane (a divergent merge would fork the frozen governance semantics — patent-record hazard).
4. Add only: a compound prompt-input builder + a `compound_risk` routing branch.
5. Consume `implicated_lps` (ALL, never `[0]`) + `cited_sections` + per-LP neutral clause facts + use profile.
6. Forbid from prompt input: `headline`, `title`, `short_summary`, `detail`, `severity`, `verdict`, `pattern_type`, `evaluator_agreement`, `affected_party`-as-evidence, and any adverse Stage 7 wording.
7. Many-to-many is real and exercised: LP-27 in 5 CRX, LP-01 in 4. Identity key must be `finding_id`; no LP-level write-back; each CRX assessed independently.
8. Existing LP-level `use_impact` is provenance at most, never prompt input (using it re-imports the category error COV-A refused).
9. Mixed-consequence CRX (beneficial LP + harmful LP in one finding) is UNTESTED on both leases — the real stress case; 408B cannot claim to have solved compound consequence until such a case runs.

---

## 3. Exact current code path and current refusal behavior

File: `cam/adapters/lease_review/lease_finding_consequence.py`, function `assess_finding_consequence(cross_provision_findings, coverage_assessment, use_profile, perspective, cfg=None)`.

**Current compound handling — the deliberate refusal (to be replaced, not deleted):**

```python
# ── Annotate compound findings (structurally forced — no LP consequence) ──
n_compound = 0
for f in cross_provision_findings:
    if f.get("finding_type") == "compound_risk":
        f["compound_consequence_source"] = "not_assessed"
        n_compound += 1
```

**Current directional path (the template to mirror, NOT reuse verbatim):**
- `directional = [f for f in cross_provision_findings if f.get("finding_type") == "directional_mismatch"]`
- Splits into already-assessed (copy from LP-scope `use_impact`) vs needs-assessment (fresh 5e).
- `_build_finding_user_prompt(findings_to_assess, coverage_by_lp, use_profile, perspective)` builds the prompt. **This is the LP-bound function**: it resolves `lp_id = lp_ids[0]` (first implicated LP only) and pulls clause facts from that single LP's `coverage_state` / `element_verdicts` / `tenant_text`.
- `_call_finding_evaluator` runs the 3-evaluator lineup with `_FINDING_SYSTEM_PROMPT`.
- `_merge_finding_verdicts(evaluator_results, findings_to_assess)` merges by `finding_id`.
- Write-back loop stamps `use_consequence`, `use_consequence_source`, `materiality`, `materiality_source`, DEF-003 fields (`consequence_support_label`, `expected_evaluator_count`, `valid_evaluator_count`, `vote_distribution`), DEF-004 fields (`materiality_votes`, `materiality_support`, `materiality_agreement`, `materiality_disputed`), reasoning provenance (`use_consequence_reasoning`, `consequence_confidence`, `consequence_evaluator_agreement`), and `assessment_scope = "finding_linked_lp"`.

**The write-back gating logic that MUST be reused (DEF-003 semantics):**
- `support_label not in ("no_evaluators", "insufficient_support")` → source = `"assessed"`.
- `insufficient_support` (1 valid evaluator) → source = `"insufficient_consequence_support"`, counts as absent for routing.
- `route_to_review_needed` (no-majority materiality) → source = `"no_majority_materiality"`.
- else → `"absent"`.

408B's compound write-back reuses this exact gating, changed only in field names (§5) and `assessment_scope` value (§8).

---

## 4. Proposed compound prompt-builder path

**New function:** `_build_compound_finding_user_prompt(compound_findings, coverage_by_lp, full_tenant_text, use_profile, perspective)`.

Signature notes:
- `compound_findings`: the list of `finding_type == "compound_risk"` dicts.
- `coverage_by_lp`: the existing `{issue_area_id: assessment}` lookup already built in `assess_finding_consequence`.
- `full_tenant_text`: the parsed lease text, threaded from `run_lease_coverage_only` (RESOLVED — see §11 OQ1). A small in-module section resolver locates each `cited_sections` entry (e.g. "Section 27") within `full_tenant_text` and extracts a neutral excerpt. If `full_tenant_text` is empty/None (defensive), or a section cannot be located, the builder falls back to per-LP `tenant_text` from `coverage_by_lp`; if even that is missing for all implicated LPs, the finding is not assessed (§9).
- Returns a batched prompt string (one block per CRX finding, keyed by `finding_id`), mirroring the batched shape of `_build_finding_user_prompt`.

**Section resolver (new, small):** a helper that, given a section ref string and `full_tenant_text`, returns a bounded neutral excerpt of that section. The existing `_section_relevant_to_provision` in `lease_adapter.py` already does regex section-location (`\bsection\s+<ref>\b`) — the compound resolver can follow the same locate-then-slice pattern (bounded excerpt, e.g. ≤600 chars per section). This is neutral clause text, not Stage 7 prose.

**Per-CRX prompt block assembly (neutral):**
1. Header line: `finding_id` only (e.g. "CRX-02") — NO title, NO headline.
2. For each LP in `implicated_lps` (ALL of them): the LP label (`issue_area_name`), coverage state in neutral language ("partial — N of M elements confirmed"), present/missing element labels, and `tenant_text` excerpt (≤400 chars, as the directional builder does).
3. For each section in `cited_sections`: the resolved neutral lease text (via the section resolver over `full_tenant_text`), if locatable. This is the multi-provision material that lets the evaluator see the interaction.
4. The interaction QUESTION (see §Neutral prompt discipline below).

**New system prompt:** `_COMPOUND_FINDING_SYSTEM_PROMPT` — a compound analogue of `_FINDING_SYSTEM_PROMPT`, carrying the same INDEPENDENCE REQUIREMENT ("absence/structure ≠ adverse by default; assess consequence independently"), adapted to ask about the *interaction* of multiple provisions rather than a single gap. It must NOT name the Stage 7 pattern, must NOT assert a compound risk exists, and must allow beneficial/neutral/context_dependent outcomes.

**New routing branch in `assess_finding_consequence`:** after the directional path, add a compound path that (a) collects `compound_risk` findings, (b) attempts neutral input assembly, (c) routes assemblable ones through `_build_compound_finding_user_prompt` → `_call_finding_evaluator` (reused) → `_merge_finding_verdicts` (reused), (d) write-back per §5/§8, (e) leaves unassemblable ones at `not_assessed` with a reason code (§9).

### Neutral prompt discipline

The prompt asks:

> "Given the clauses below and how they reference one another, does the interaction among these provisions increase, reduce, or not materially affect this tenant's practical/legal exposure for the stated use context?"

It must NOT ask "given this compound risk, how harmful is it?" and must NOT pre-name the pattern. The four allowed return values are `harmful` / `beneficial` / `neutral` / `context_dependent`. Do not make `harmful` the default because Stage 7 emitted `compound_risk`.

---

## 5. Fields consumed (prompt input)

Per compound finding:
- `finding_id` (identity + prompt key)
- `implicated_lps` (ALL entries)
- `cited_sections` (for section-text resolution)

Per implicated LP, from `coverage_by_lp`:
- `issue_area_name` (neutral label)
- `coverage_state` (rendered in neutral language)
- `element_verdicts` (present/missing element labels)
- `tenant_text` (neutral lease excerpt)

Per cited section:
- resolved neutral lease text — located in `full_tenant_text` via the section resolver (RESOLVED — §11 OQ1)

Shared:
- `use_profile` (business_type, operational_dependencies, other_use_risk_factors) — same as directional
- `perspective`

---

## 6. Fields explicitly FORBIDDEN from prompt input

From the compound finding, these may be retained as provenance on the OUTPUT but must never enter the evaluator prompt:
- `headline`, `title`, `short_summary`
- `detail` (evaluator prose — carries residual adverse coloring per 408A §2; not clean enough even though section-cited)
- `severity`, `verdict` ("compound_risk_confirmed"), `pattern_type`
- `evaluator_agreement`, `evaluator_verdicts` (Stage 7's, not the consequence evaluators')
- `affected_party` as evidence
- Any adverse wording: "one-sided", "tenant_unprotected", "dead-end", "trap", "risk is real", "enforcement machinery", etc.

**Also forbidden as prompt input:** existing LP-level `use_impact` verdicts for the implicated LPs (§8 reason).

---

## 7. Merge / provenance reuse plan

- **`_merge_finding_verdicts` reused UNCHANGED.** It loops `for f in findings: fid = f.get("finding_id")` and never reads any LP field. Compound findings pass through identically. DEF-003 (support floor) and DEF-004 (materiality majority + `route_to_review_needed`) apply as-is.
- **`_call_finding_evaluator` needs a one-line signature change (RESOLVED — was Open Question 2).** It currently HARDCODES `_FINDING_SYSTEM_PROMPT` inside its inner `_try`: `adapter.call(_FINDING_SYSTEM_PROMPT, user_prompt, target)`. The minimal refactor: add a `system_prompt: str = _FINDING_SYSTEM_PROMPT` parameter and pass it through to `adapter.call(system_prompt, user_prompt, target)`. The directional callers are unaffected (default preserves current behavior); the compound branch passes `_COMPOUND_FINDING_SYSTEM_PROMPT`. The F8d claim-before-call / no-release-on-failure block is in the same function but is independent of which prompt string is used — it MUST NOT be touched. This is the only edit to that function.
- **Write-back gating reused** (the DEF-003 `support_label` ladder from §3), with compound field names (§5 output fields below) and `assessment_scope = "finding_compound"` (§8).

---

## 8. Many-to-many identity guard

- Compound consequence identity key = `finding_id` (CRX-NN). Confirmed stable, unique, one-per-interaction, already the merge key.
- Never write compound consequence to any LP's `use_impact`. LP-27 participates in 5 CRX with 5 potentially different consequences; an LP slot can hold only one.
- Each CRX assessed independently; no collapsing multiple CRX into one LP verdict.
- `assessment_scope` on compound output = a NEW distinct value, e.g. `"finding_compound"` (directional uses `"finding_linked_lp"`; LP-scope uses none / LP-level). The three consequence layers must be distinguishable downstream (UI + future Priority Exposure): LP-level `use_impact`, directional finding consequence (`finding_linked_lp`), compound finding consequence (`finding_compound`).

---

## 9. Fallback / not_assessed preservation

If neutral clause facts cannot be assembled for a compound finding (no resolvable section text AND no `tenant_text` on any implicated LP):
- Do NOT assess it.
- Preserve `compound_consequence_source = "not_assessed"`.
- Add a reason code, e.g. `compound_consequence_reason = "compound_input_unavailable"`.
- NEVER assess from Stage 7 prose (`detail`/`headline`) as a substitute.

Also preserve `not_assessed` (with an appropriate support-derived reason) when the evaluators run but `_merge_finding_verdicts` returns `no_evaluators` / `insufficient_support` — mirroring the directional lane's DEF-003 behavior, so a 1-evaluator compound verdict is never stamped "assessed".

Keyless mode (no `use_profile`): mark compound findings `not_assessed` with reason `no_use_profile`, matching the directional lane's keyless behavior.

---

## 10. Validation plan

Run 408B on a frozen/current Atreca artifact (CRX-01..06 present) — reuse the 407 fixture. Minimum checks:

1. All six CRX receive either an assessed compound consequence or an explicit not-assessed reason code.
2. No compound consequence written to any LP-level `use_impact` (grep the coverage_assessment entries for the implicated LPs — unchanged).
3. `_merge_finding_verdicts` reused unchanged (git diff shows no edit to that function).
4. No `cam/core/` change.
5. Prompt text (dump the assembled prompt) contains NONE of: `headline`, `title`, `short_summary`, `detail`, `severity`, `verdict`, `pattern_type`, or adverse pattern wording.
6. CRX findings keyed by `finding_id` throughout.
7. LP-27 participates in all 5 of its CRX findings with 5 independent verdicts — no state bleed (verify each CRX's consequence is computed from its own prompt block).
8. Parser/merge handles all CRX outputs (no truncation; chunk if >~11 findings, mirroring 5e chunking — though 6 CRX is well under).
9. Output distribution recorded: harmful / beneficial / neutral / context_dependent counts; evaluator agreement; materiality; not_assessed fallback count.
10. **Contamination A/B sensitivity probe (REQUIRED before wiring the default) — measures sensitivity, does NOT require divergence.** On at least CRX-02 and CRX-05, run the compound prompt in two variants: (A) neutral as specced; (B) a deliberately-framed variant with Stage 7 `headline`/`title` injected. **The purpose is to measure prompt sensitivity and to audit the neutral prompt's grounding — NOT to force a divergent label.** Correct interpretation:
    - Divergence between A and B IS evidence that Stage 7 framing can contaminate compound consequence (as it did LP-11 in A1). Record it as sensitivity evidence.
    - **Non-divergence is NOT proof of safety and NOT proof of failure.** If the underlying clause interaction is genuinely harmful (or neutral, or beneficial), both prompts may legitimately return the same label. A matching label may just mean the lease is actually that way — do not read agreement as "the neutral prompt is broken."
    - The real check is the REASONING, not the label. Inspect each variant's `use_reasoning`:
      - Variant A (neutral) reasoning MUST cite raw clause facts / section text / LP facts. If A's reasoning echoes forbidden Stage 7 terms ("one-sided," "dead-end," "trap," "enforcement machinery," the pattern name, etc.), the neutral prompt has leaked — **fail the prompt even if the final label looks plausible.**
      - Variant B (framed) reasoning may echo Stage 7 wording; that echo is the contamination signal the probe exists to expose.
    - **Success criteria (NOT "A and B diverge"):** (1) the neutral prompt excludes all §6 forbidden fields; (2) neutral reasoning is grounded in raw clause facts, free of Stage 7 vocabulary; (3) the framed variant is clearly labeled a contamination probe in the harness, never a shipping path; (4) any divergence is recorded as framing-sensitivity evidence; (5) non-divergence is recorded plainly, without overclaiming safety.
    This mirrors the A1 diagnostic in method (probe the prompt for framing dependence) while avoiding A1's one specific outcome (LP-11 happened to flip) as a required result. The failure mode this guards against is a validation test that encodes its own desired answer.

N≥2 runs for any distribution claim (directional discipline: single run is anecdote). All results DIRECTIONAL until reproduced; not CAM metrics, not patent record.

---

## 11. Open questions

**OQ1 — RESOLVED (section-text availability).** The full lease text IS available at the call site. `run_lease_coverage_only` in `lease_adapter.py` holds `tenant_text` in local scope and already passes it to `run_synthesis(full_tenant_text=tenant_text, ...)`. The `assess_finding_consequence(...)` call immediately below (the Stage 5e-F block) passes `cross_provision_findings`, `coverage_assessment`, `use_profile=use_profile_data_c`, `perspective`, `cfg` — but NOT the text. Fix: add `full_tenant_text=tenant_text` to that one call and add the matching parameter to `assess_finding_consequence`'s signature (defaulted to `""`/None so the directional-only path and any other caller are unaffected). No new parse, no new plumbing. Note: `assess_finding_consequence` is invoked ONLY from `run_lease_coverage_only` (Mode C) — the `run_lease_analysis` Mode A path does not call it — so there is a single call site to update.

**OQ2 — RESOLVED (system-prompt parameterization).** `_call_finding_evaluator` HARDCODES `_FINDING_SYSTEM_PROMPT` in its inner `_try` (`adapter.call(_FINDING_SYSTEM_PROMPT, user_prompt, target)`). Fix: add `system_prompt: str = _FINDING_SYSTEM_PROMPT` as a parameter, pass through to `adapter.call(...)`. Directional callers unaffected by the default; compound branch passes `_COMPOUND_FINDING_SYSTEM_PROMPT`. Do NOT touch the F8d claim-before-call/no-release logic in the same function.

Still open:

3. **Output field naming.** Proposed compound fields (below) must be checked against existing COV-A naming for consistency and against the UI/report readers so a compound consequence is not mistaken for LP-level `use_impact`. Distinct prefix `compound_` is proposed; confirm no reader keys off the bare `use_consequence` field on a `finding_type == "compound_risk"` object in a way that would misread it.
4. **Does the compound prompt need cross-references between sections made explicit?** Stage 7 found the interaction; the neutral prompt gives the evaluator the raw clauses but not Stage 7's "how they interact" narrative (correctly quarantined). Open question whether the evaluator can re-derive the interaction from clause facts alone, or whether a neutral structural hint ("these provisions govern related obligations: X, Y, Z") is needed without laundering the conclusion. Decide during the A/B pre-check.
5. **Materiality on compound findings.** Compound findings carry NO materiality field from Stage 7 (408A §1). The consequence evaluator will produce one via DEF-004. Confirm that's the intended source and that no downstream reader expects a pre-existing compound materiality.

---

## Proposed output fields (subject to Open Question 3)

Written onto each assessed compound finding, `compound_`-prefixed to stay structurally distinct from LP-level and directional consequence:
- `compound_use_consequence` — harmful | beneficial | neutral | context_dependent
- `compound_materiality` — high | medium | low | not_applicable
- `compound_consequence_source` — assessed | insufficient_consequence_support | no_majority_materiality | not_assessed
- `compound_consequence_reason` — reason code when not assessed (e.g. `compound_input_unavailable`, `no_use_profile`)
- `compound_consequence_support_label` — DEF-003 label (full_assert / majority_assert / duo_assert / insufficient_support / split / no_evaluators)
- `compound_consequence_reasoning` — merged reasoning (null on 1-1-1 split, per F8c)
- `compound_evaluator_agreement` — "3-0" | "2-1" | "1-1-1" | etc.
- `compound_vote_distribution`, `compound_valid_evaluator_count`, `compound_expected_evaluator_count` — DEF-003 provenance
- `compound_materiality_votes`, `compound_materiality_support`, `compound_materiality_disputed` — DEF-004 provenance
- `assessment_scope = "finding_compound"`
- Retain (provenance, NOT prompt input): existing `severity`, `pattern_type`, `affected_party`, `title`, `headline` untouched on the object; add `compound_assessment_input_source` recording what fed the prompt (e.g. `"section_text+tenant_text"` vs `"tenant_text_only"`).

---

## 12. Implementation checklist (for the later build step)

- [ ] Thread `full_tenant_text=tenant_text` into the single `assess_finding_consequence(...)` call in `run_lease_coverage_only` (OQ1 resolved); add the matching defaulted parameter to `assess_finding_consequence`.
- [ ] Add a small section resolver (locate `cited_sections` ref in `full_tenant_text`, bounded excerpt) following the existing `_section_relevant_to_provision` regex pattern.
- [ ] Add `_COMPOUND_FINDING_SYSTEM_PROMPT` (neutral, interaction question, absence≠adverse, all four outcomes allowed).
- [ ] Add `_build_compound_finding_user_prompt(...)` consuming ALL `implicated_lps` + `cited_sections` + `full_tenant_text`, forbidding §6 fields.
- [ ] Add `system_prompt` parameter (defaulted to `_FINDING_SYSTEM_PROMPT`) to `_call_finding_evaluator` (OQ2 resolved) without touching F8d claim logic.
- [ ] Add compound routing branch in `assess_finding_consequence`; replace the `not_assessed` stamp with assess-or-fallback.
- [ ] Reuse `_merge_finding_verdicts` UNCHANGED.
- [ ] Write-back with `compound_`-prefixed fields + `assessment_scope="finding_compound"`, reusing DEF-003 gating ladder.
- [ ] Preserve `not_assessed` + reason code for unassemblable/keyless/insufficient cases.
- [ ] Update module docstring (compound path now assesses; document the neutral-input contract and the quarantine list).
- [ ] Validation §10 including the CRX-02/CRX-05 A/B contamination pre-check, N≥2.
- [ ] No `cam/core/`, no `_merge_finding_verdicts` edit, no routing/bucket change, no default flip, no push.
- [ ] Do NOT wire any downstream routing/Priority-Exposure consumption of compound consequence in this step — populate/record only, mirroring COV-A's populate-only discipline; a later COV-B-style step decides lawyer-facing landing.

---

## Interpretation discipline

This is a spec, not a result. No code changed, no model called, no artifact produced. All downstream claims (yield, distribution, contamination divergence) are hypotheses until 408B runs and reproduces N≥2. The compound path stays populate/record-only; it must not alter Risk routing or buckets in this step. Mixed-consequence CRX remains the untested stress case and is the real bar for "compound consequence solved."

*Spec artifact: Step 408B. No implementation performed.*
