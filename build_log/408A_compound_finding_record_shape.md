# 408A — Compound Finding Record-Shape Trace

**Date:** 2026-07-08
**Type:** Read-only measurement / design. No code, prompt, model, pipeline, `cam/core/`, routing, or bucket change. No build. No push.
**Purpose:** Inspect the actual Stage 7 `compound_risk` object shape before writing the 408B build spec, so the compound-aware prompt builder is specced against the real object contract rather than inferred fields.

**Primary artifact read:** `05 Lease Analyzer/results/lease_407_atreca_runA/pipeline_results.json` (1.31 MB — exceeds the ~1MB MCP whole-read cap; extracted via head/tail slices reassembled and brace-matched in a scratch environment). Canonical `cross_provision_findings` array recovered from the tail region; LP-scope `use_impact` and `coverage_assessment` from the head region.
**Supporting reads:** `build_log/407_second_lease_widened_5e_diagnostic.md`; `cam/adapters/lease_review/lease_finding_consequence.py`; `cam/adapters/lease_review/lease_use_impact.py`; `cam/adapters/lease_review/lease_synthesis.py` (header + Stage 7 config); `build_log/375E-COV-A1_results.md`; `build_log/375E-COV-A2_code_status.md`; `build_log/375E-COV-A2b_code_status.md`; `build_log/375E-COV-A2-DIR-Q_results.md`; `stage7_pass1_parsed_candidates.json`, `stage7_pass1_raw_input.json`.

---

## 0. Headline conclusion

**Extend COV-A. Do not build a separate consequence lane.** The compound gap is confined to ONE function — the prompt-input builder. `_merge_finding_verdicts` is `finding_id`-keyed and LP-count-agnostic; it can be reused unchanged. Compound findings carry enough section-level provenance to rebuild the interaction neutrally, but the neutral facts must come from `cited_sections` → lease text, NOT from the finding's `headline`/`title`/`detail`, which are pre-framed and would re-trigger the verified A1 contamination failure.

---

## 1. What a `compound_risk` finding object actually contains

Recovered field set (identical keys across all 6 CRX findings in the Atreca run-A canonical `cross_provision_findings` array):

```
finding_id                    "CRX-01" … "CRX-06"
finding_type                  "compound_risk"
implicated_lps                ["LP-22","LP-27"]           # 2–7 LPs; the multi-LP list
title                         "Conditional possession protection"
headline                      "<pre-framed risk sentence>"
short_summary                 "<truncated headline>"
detail                        "<3 evaluators' clause recitations, pipe-delimited>"
cited_sections                ["Section 27"]              # actual lease sections
verdict                       "compound_risk_confirmed"
directionality                null                        # ALWAYS null on compound
severity                      "HIGH" | "MEDIUM"
evaluator_agreement           "3-0"
evaluator_verdicts            {"A":"compound_risk_present","B":...,"C":...}
pattern_type                  "subordination_trap" | "directional_asymmetry" |
                              "lever_elimination" | "cascading_no_remedy" |
                              "operational_dead_end"
affected_party                "tenant"
compound_consequence_source   "not_assessed"              # the gap, stamped by COV-A
```

**Fields NOT present on compound findings** (present on directional findings — confirms the two are different shapes): `use_consequence`, `use_consequence_source`, `materiality`, `materiality_source`, `assessment_scope`, `stage7_direction`, `stage7_direction_source`, `use_consequence_reasoning`, `consequence_confidence`, `consequence_evaluator_agreement`, `p2pp_routing`, `verification_incomplete*`. A compound finding has NO materiality field at all (directional findings do).

**Note on field naming vs the questionnaire:** the object uses `implicated_lps` (not `lp_ids`/`related_lps`), `detail` (not `description`/`reasoning`), `cited_sections` (not free-form `evidence`), `evaluator_verdicts` (not `source_findings`), and `pattern_type` (not `cross_provision_pattern`). There is no `confidence` field — `evaluator_agreement` + `evaluator_verdicts` carry that. `issue_area_id`/`issue_area_name` are `null` on compound findings (they are LP-scoped fields, N/A for cross-LP findings).

**Provenance caution recorded:** the 407 diagnostic's narrative CRX table (CRX-01 = LP-01/11/27, etc.) does NOT match the artifact. The artifact's real mapping is in §3 below. The narrative report renumbered and simplified; the artifact is ground truth. The report's "6 compound findings" count is correct; its per-CRX LP lists and titles are not.

---

## 2. How Stage 7 represents the interaction

The object gives **all four** of: a narrative summary (`headline`/`short_summary`), a structured LP list (`implicated_lps`), per-section clause references (`cited_sections` + per-evaluator recitations in `detail`), and an agreement record (`evaluator_agreement`/`evaluator_verdicts`). It does NOT give source directional finding-ids (no back-pointer to the `Dir-NN` findings that fed the compound synthesis).

**Is there enough to rebuild the interaction neutrally? Yes — but only from `cited_sections`, not from the finding's own prose.** Concretely:

- `headline` / `title` / `short_summary` are **pre-framed risk conclusions**. Examples: *"One-sided default enforcement"*; *"The risk is real because the lease gives Tenant far fewer practical enforcement tools"*; *"Dead-end impairment structure."* These are exactly the adversarial framing that A1 proved contaminates 5e. They must NOT be fed to the consequence evaluator.
- `detail` is the three evaluators' clause recitations, pipe-delimited. It is *mostly* factual and section-cited ("Sections 20-21 provide detailed Tenant default triggers and Landlord remedies; Section 31 requires Tenant notice…") but carries residual adverse coloring ("no comparable Tenant remedy framework is stated"). It is **not clean enough** to pass verbatim.
- `cited_sections` is a clean list of lease section references. This is the safe anchor: resolve each cited section to its actual lease text (the same move the A2 fix made with `tenant_text`) and present THOSE facts neutrally.

**Design consequence:** the compound prompt builder should consume `implicated_lps` + `cited_sections` and reconstruct neutral clause facts from the LP coverage assessments / lease text, and must treat `headline`/`title`/`detail` as provenance-only (stored, never fed as evaluator input).

---

## 3. Clause facts per implicated LP + the real CRX→LP mapping (Atreca run-A)

| CRX | title (provenance only) | pattern_type | severity | implicated_lps | cited_sections |
|-----|------------------------|--------------|----------|----------------|----------------|
| CRX-01 | Conditional possession protection | subordination_trap | HIGH | LP-22, LP-27 | S27 |
| CRX-02 | One-sided default enforcement | directional_asymmetry | HIGH | LP-01, LP-11, LP-27, LP-31 | S20, S31, S3, S36 |
| CRX-03 | Rights without enforcement levers | lever_elimination | MEDIUM | LP-01, LP-11, LP-17, LP-27, LP-07 | S31, S3, S13, S5 |
| CRX-04 | Default-conditioned non-disturbance protection | subordination_trap | HIGH | LP-22, LP-26 | S27 |
| CRX-05 | Dead-end impairment structure | cascading_no_remedy | HIGH | LP-01, LP-14, LP-24, LP-27, LP-29, LP-11, LP-19 | S1, S2, S13, S34, S3, S31, S18, S11 |
| CRX-06 | No exit during shutdown | operational_dead_end | MEDIUM | LP-01, LP-14, LP-19, LP-24, LP-27, LP-29, LP-06 | S11, S13, S34, S3, S31, S32, S18 |

**Where the clause facts live:** for each implicated LP, the coverage assessment entry (`coverage_assessment[]`, keyed by `issue_area_id`) carries `coverage_state`, `element_verdicts`, and `tenant_text` — the same fields the directional COV-A prompt already pulls via `_build_finding_user_prompt`. `cited_sections` gives the section anchors. Both are available in the artifact. **A compound prompt CAN assemble neutral clause facts for all implicated LPs without using Stage 7's risk-framed conclusion.**

---

## 4. Are implicated LPs already assessed by LP-scope Stage 5e?

Yes — nearly all of them. On Atreca run-A, 19/32 LPs were wide-eligible and assessed; the CRX-implicated LP set is {LP-01, 06, 07, 11, 14, 17, 19, 22, 24, 26, 27, 29, 31}. Most carry an LP-scope `use_impact` verdict. Per the 407 report, all assessed LPs read harmful except LP-20/LP-30 (neutral) and LP-21 (beneficial) — **none of which appear in any CRX.** Therefore every CRX-implicated LP that is assessed is `harmful`.

**Would using those per-LP verdicts contaminate the compound assessment? YES — structurally.** The whole reason COV-A stamps compound findings `not_assessed` (see §5) is that single-LP consequence ≠ cross-provision consequence. Reusing LP-27's "harmful" verdict as the compound verdict would launder a single-provision consequence into a multi-provision question — the exact category error COV-A already refuses. A compound risk is not the sum or max of its LPs' individual consequences; it is a property of their interaction.

**Recommendation: the compound prompt builder must IGNORE existing per-LP `use_impact` and assemble raw clause facts fresh.** Existing `use_impact` may be retained as provenance/audit context but must never be the input or the answer.

**Mixed-consequence check:** on Atreca, every CRX combines LPs whose individual (directional/LP-scope) consequence is uniformly `harmful` — **no mixed case exists on this lease.** This is lease-specific and must not be read as reassurance. The dangerous case 405 §4 anticipated — one CRX combining a `beneficial` LP with a `harmful` LP, where the compound consequence is neither — is UNTESTED. Atreca happens not to produce it. A future lease will.

---

## 5. Why compound findings are currently `not_assessed`

Source: `cam/adapters/lease_review/lease_finding_consequence.py`, `assess_finding_consequence`, the "Annotate compound findings" block:

```python
for f in cross_provision_findings:
    if f.get("finding_type") == "compound_risk":
        f["compound_consequence_source"] = "not_assessed"
        n_compound += 1
```

Module docstring: *"compound_risk findings: compound_consequence_source = 'not_assessed' (structurally forced)"* and *"(Structurally forced — no single LP consequence is correct for multi-LP compound findings)."*

**Classification: DELIBERATE STRUCTURAL REFUSAL, not missing implementation, not a safety guard, not accidental omission.** COV-A sees every compound finding, iterates it, and chooses to stamp `not_assessed` because the only consequence mechanism it has is finding→single-LP (`implicated_lps[0]` + single-LP clause facts). Applying that to a multi-LP finding would produce a misleading verdict, so COV-A correctly declines. 408B removes the refusal by giving COV-A a mechanism that is actually correct for multi-LP findings (a compound-aware prompt), not by deleting the guard.

---

## 6. Can COV-A merge/provenance machinery be reused unchanged?

**Yes.** Inspection of `_merge_finding_verdicts`:

- **Keyed by `finding_id`, not LP.** The merge loop is `for f in findings: fid = f.get("finding_id")`. It never reads `implicated_lps` or any LP field. A finding with 7 implicated LPs merges exactly like one with 1.
- **DEF-003 consequence support floor** (assert / assert_weak / assert_duo / insufficient_support / no_evaluators / split) — applies unchanged; it counts valid evaluator verdicts, LP-count-agnostic.
- **DEF-004 materiality majority merge** (majority wins; `route_to_review_needed` on no-majority) — applies unchanged.
- **The merge layer does not care whether a finding maps to one LP or many.** Confirmed.

**What is LP-bound (the ONLY parts that need compound-aware replacement):**
- `_build_finding_user_prompt` — resolves `lp_id = lp_ids[0]` (first implicated LP only) and pulls clause facts from that single LP. This is the structural wall: it discards all but the first implicated LP.
- The `_is_already_assessed` / copy-from-LP-scope path in `assess_finding_consequence` — LP-scoped by design; compound findings must bypass it (they route to fresh assessment, never copy).
- The compound annotation block — currently stamps `not_assessed`; 408B replaces this branch with a call to the compound assessment path.

`_FINDING_SYSTEM_PROMPT` (the directional consequence-independent prompt) is close but written for single-provision gaps; the compound path needs its own system prompt asking the interaction question (see §8).

---

## 7. COV-A1 prompt-contamination lesson — VERIFIED FROM SOURCE

Source: `build_log/375E-COV-A1_results.md` (run `19f9a7`, 4-finding panel) + `375E-COV-A2_code_status.md`.

**The LP-11 flip, exact:** under Variant A (as-shipped COV-A, which fed Stage 7's FIXED-adverse title/direction), all 3 evaluators returned **harmful / high**. Under Variant B (direction-redacted, clause facts only), all 3 returned **beneficial / medium**. Direction of flip: **harmful→beneficial when the adverse framing was removed.** Cause: the old prompt opened with *"the finding direction is FIXED… accept the adverse direction as a settled fact"* and passed the Stage 7 headline verbatim ("Accelerated liability without limits"), so 5e ratified the framing instead of assessing. The absence of a rent-acceleration remedy is in fact net-positive for the tenant; the adverse frame inverted the sign by construction.

(The recalled tuple "harmful/high → beneficial/medium" is CORRECT and matches Variant B. Recording it verified rather than from memory, per the trace discipline.)

**The lesson is broader than LP-11.** Contamination was confirmed across the panel, not a single anecdote: LP-05 (A=neutral vs B=harmful), LP-15 (A=harmful vs B/C=neutral, FLIP), LP-20 (A=harmful vs C=neutral, FLIP), LP-11 (A=harmful vs B=beneficial, FLIP). The monochrome 24-harmful directional distribution was shown to be prompt-driven, not lease-driven. Fix (A2, commit `fc8d3dc`): removed the FIXED-direction framing and the headline/detail from the user prompt; fed coverage state + element facts + `tenant_text` excerpt instead. A2b (`8de0d74`) later stopped hardcoding `stage7_direction` and read the actual value — which is why the Atreca artifact shows `stage7_direction_source: "stage7"`, confirming the fix shipped.

**Level supported by source, to carry into 408B:** adverse/leading framing measurably contaminates consequence assessment (sign inversion demonstrated, 3-0 unanimous, repeatable across 4 findings); compound prompts must not embed Stage 7's `headline`/`title`/`detail` conclusion as evaluator input.

---

## 8. Neutral compound prompt-builder requirements

A compound-aware prompt builder must include:

- **All implicated LP ids and labels** — the full `implicated_lps` list (not `[0]`), each resolved to its `issue_area_name`.
- **Neutral clause facts per implicated LP** — coverage state, present/missing element labels, and `tenant_text` excerpts, assembled the way the A2 directional prompt does — but for ALL implicated LPs, plus the lease text at each `cited_sections` anchor.
- **The alleged interaction expressed as a QUESTION, not an asserted risk** — e.g. "Given these provisions and how they reference each other, what is the practical consequence for THIS tenant's operations if they interact?" — never "this is a one-sided enforcement trap; how bad is it?"
- **No leading Stage 7 severity label** — omit `severity`, `title`, `headline`, `short_summary`, `pattern_type` from the evaluator input.
- **No unexamined `affected_party`/`compound_risk_confirmed`/one-sided framing** as evidence. `affected_party` and `pattern_type` may be stored as provenance on the output; they must not enter the prompt.

Explicit A1 account: because adverse framing inverted LP-11's sign 3-0, and because compound `headline`/`title`/`detail` are MORE strongly pre-framed than the directional titles that caused A1 (they assert a named trap pattern), feeding them would risk contamination at least as severe. The compound builder must launder nothing from Stage 7's conclusion into the evaluator input.

---

## 9. Many-to-many guard

**One LP appears in multiple compound findings — confirmed, extensively, on Atreca run-A:**

| LP | appears in | count |
|----|-----------|-------|
| LP-27 | CRX-01, 02, 03, 05, 06 | 5 |
| LP-01 | CRX-02, 03, 05, 06 | 4 |
| LP-11 | CRX-02, 03, 05 | 3 |
| LP-14 | CRX-05, 06 | 2 |
| LP-19 | CRX-05, 06 | 2 |
| LP-22 | CRX-01, 04 | 2 |
| LP-24 | CRX-05, 06 | 2 |
| LP-29 | CRX-05, 06 | 2 |
| LP-06, 07, 17, 26, 31 | one CRX each | 1 |

This is exactly the many-to-many case COV-A's docstring flagged as DEFERRED/UNEXERCISED ("many-to-many only arises in compound layer"). It is now EXERCISED and OBSERVED.

- **Does the same LP appear in multiple consequence contexts? Yes** — LP-27 participates in 5 distinct compound risks (subordination trap, one-sided default, lever elimination, cascading no-remedy, operational dead-end). Its consequence in each is a different question.
- **Would storing only per-LP `use_impact` create state bleed? Yes.** A single per-LP consequence slot for LP-27 cannot represent 5 different compound roles. Any design that writes compound consequence back onto the LP would collapse 5 answers into 1. Compound consequence must be stored on the FINDING, never on the LP.
- **Identity key for compound consequence: `finding_id` (the `CRX-NN` id).** It is stable, unique per compound finding, already the merge key, and one-per-interaction. Not `compound_id` (no such field exists), not any LP key (many-to-many breaks it). This matches how the directional lane already keys consequence by `Dir-NN`.

---

## 10. Output recommendation (for 408B)

1. **408B should EXTEND COV-A with a compound prompt path — not a separate lane.** The merge/provenance core is reusable; only the prompt-input builder and the routing branch are new.
2. **A separate consequence lane is NOT needed.** A second merge/governance implementation would create divergent consequence semantics (a patent-record hazard, since `_merge_finding_verdicts` is the frozen governance instance). Reuse it.
3. **`_merge_finding_verdicts` can be reused UNCHANGED.** It is `finding_id`-keyed and LP-count-agnostic. DEF-003 and DEF-004 apply as-is.
4. **Fields the compound prompt builder should CONSUME:** `implicated_lps` (all), each LP's `issue_area_name` + `coverage_state` + `element_verdicts` + `tenant_text`, and `cited_sections` → resolved lease text. Output keyed by `finding_id`.
5. **Fields the builder must IGNORE (contamination risk):** `headline`, `title`, `short_summary`, `detail`, `severity`, `pattern_type`, `verdict` ("compound_risk_confirmed"), `affected_party` as-evidence. Store them as provenance on the output if useful; never feed them to the evaluator.
6. **Existing LP-level `use_impact`: IGNORE as input; reference only as provenance.** Do not launder single-LP consequence into compound consequence. Assemble raw clause facts fresh.
7. **Must be avoided:** feeding any Stage 7 conclusion (title/headline/detail/severity/pattern) into the prompt; writing compound consequence back onto an LP (state bleed via the many-to-many); reusing `implicated_lps[0]` single-LP resolution.
8. **Do the artifacts contain enough neutral clause facts to build safely? YES.** `implicated_lps` + `cited_sections` + the per-LP coverage assessments provide sufficient neutral material to reconstruct each interaction without Stage 7's framing. The one genuinely new piece of machinery 408B needs is multi-LP fact assembly with a finding-id identity key (the many-to-many guard) — small and well-scoped.

**Open item for 408B to decide (not resolved here):** the compound consequence prompt asks a genuinely different question (interaction, not single-gap). Its system prompt is new work and carries the highest contamination risk in the whole feature; it should be drafted with the A1/A2 discipline explicit and, ideally, A/B-tested (framed vs neutral) on at least CRX-02 and CRX-05 before wiring, the same way A1 tested the directional prompt. A mixed-consequence CRX (beneficial LP + harmful LP) remains UNTESTED on both leases and is the real stress case; 408B cannot claim to have solved compound consequence until such a case is run.

---

## Interpretation discipline

Single lease (Atreca run-A) for the object-shape extraction; the 407 diagnostic covers both runs and both leases for eligibility/value stability. Field shapes confirmed on run-A canonical array; run-B assumed identical (same pipeline, same code, 6 CRX both runs per 407). All DIRECTIONAL, NOT promoted, NOT patent record. No code changed. No commit performed by the trace itself. No push.

*Trace artifact: Step 408A. Read-only.*
