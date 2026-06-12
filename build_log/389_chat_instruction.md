# Step 389 — Closed-Form Directional Prototype v1 (Chat instruction to Code)

Implement **Step 389 — Closed-Form Directional Prototype v1**. Narrow prototype only.

Do not implement DEF-002. Do not redesign the UI or change the final report surface. Do not implement
across all LPs. Do not remove existing Stage 7 freeform logic (the prototype runs ALONGSIDE it on the
prototype LPs). Do not push until reviewed.

## Background

Steps 386–388 found the current freeform Stage 7 directional question is a wish-list generator
(flagged 27/27 LPs as tenant_unprotected). The fix: for a limited prototype set, replace freeform
directional discovery with closed-form questions (one question at a time, fixed choices, citation,
reason). 388 confirmed:
- Axis 1 is MODIFIER-ONLY — it is the "narrower than Article 17" near-constant in 6 of 7 appearances;
  it cannot be a standalone trigger.
- Only LP-27 has genuine same-risk Axis 1 (the §5.1 vs Article 17 default-framework comparison, where
  "default by either party" is the symmetric event).
- Post-tightening retained count: 15 (unchanged — zero findings were Axis-1-ONLY, so no count loss).
- The retained 15 are cleanly supported by Axes 2, 3, and 4.
- GATE CLEARED for prototype.

## THREE CONTAMINATION GUARDS — MANDATORY
Violating any one produces a FALSE result and wastes the entire run.

### Guard 1 — Generic prompts only. NO canonical-case hints in the model-facing prompt.
Do NOT write "find the §8.3 Landlord's-Work trap" or any clause-specific hint into the prompt
the model sees. The canonical LP-03 / LP-19 / LP-26 / LP-27 expectations listed in the Acceptance
Checks section below are **POST-RUN ACCEPTANCE CHECKS the human verifies** — they must NEVER appear
in the model-facing prompt.

The entire test is whether a GENERIC closed-form question forces the specific finding out WITHOUT
being told to look for it. If "§8.3 Landlord's Work" or "rent-before-ready" or any named finding
appears in the prompt, LP-03 surfaces for the wrong reason and Case A is false. The model gets the
generic Axis 2 question; the human checks whether §8.3 fell out of it.

### Guard 2 — Freeform baseline on the SAME N.
LP-03 was already present in 8/10 freeform runs, so a clean closed-form run could be luck. You MUST
measure closed-form stability AGAINST the current freeform build on the SAME N, SAME lease, SAME
conditions. Report both flicker rates side by side. "LP-03 stable in N closed-form runs" alone proves
nothing without the freeform comparison. The baseline is the control; the closed-form run is the
treatment; the DIFFERENCE is the evidence.

### Guard 3 — "Prose can't create findings" enforced STRUCTURALLY, not by instruction.
The candidate-generation and routing logic must read the CLOSED ANSWER FIELDS ONLY (axis_id,
question_id, answer, routing). The reason and citation fields are write-only from the model's
perspective and DISPLAY-ONLY downstream — the candidate-generation code path must structurally NOT
be able to see them. A finding exists if and only if a closed answer supports it. Do not rely on
an instruction like "please don't let prose override closed answers" — make it structurally impossible
by ensuring the code path that decides `axis_supported_candidate=True` can only read the closed fields.

## Prototype scope — 5-8 LPs (closed-form), rest stay freeform

**Required:**
- LP-03 — Axis 2 obligation-without-remedy (the fixable recall miss)
- LP-19 — axis-contested (Axis 2 says remedy exists; Axis 3 says it's heavily conditioned)
- LP-26 — Axis 3 conditional (Axis 1 must NOT be needed; Axis 3 alone is the real support)
- LP-27 — genuine same-risk Axis 1 (the §5.1 vs Article 17 parallel default-framework comparison)
- LP-11 OR LP-22 — negative Axis 1 control (generic Article-17 comparison must NOT produce Axis 1 support)
- LP-15 OR LP-16 — wish-list control (should NOT survive as a candidate under closed-form questions)

**Optional (add if run budget permits):**
- LP-06 or LP-20 — Axis 3 or Axis 2 findings that should surface without Axis 1
- A clean / no-mismatch control if one is available in the atlas lease

## Axes — model-facing questions (GENERIC, no canonical hints)

### Axis 1 — Same-risk proportionality (MODIFIER-ONLY)
"Is there a specific same-risk comparison where both parties face a parallel event, default, or
obligation, and the tenant's remedy or protection is materially narrower than the landlord's for that
same event?"

Choices: yes / no / unclear / n.a.

Citation rule: must cite BOTH sides of the same-risk comparison specifically. Generic observations
("landlord has broader Article 17 remedies" / "the landlord's default machinery is more developed")
do NOT satisfy this — those are near-constants of commercial leases and carry no information about
this specific clause.

Routing rule: **Axis 1 may NOT independently create a finding.** It only modifies an
Axis-2/3/4-supported finding, and only if a specific same-risk comparison is cited. Without an
independently-firing Axis 2/3/4, an Axis-1 yes answer produces no candidate.

### Axis 2 — Obligation without remedy
**Q-A:** "Is the tenant obligated to perform, pay, accept risk, commence obligations, lose rights,
or continue performance if a landlord-side condition fails, is incomplete, or is not met?"
Choices: yes / no / unclear / n.a.

**Q-B:** "If yes — does the tenant have a practical remedy: abatement, delay right, termination
trigger, cure period, offset right, or other meaningful protection that activates if the
landlord-side condition fails?"
Choices: yes / no / unclear / n.a.

Routing: yes+no → candidate (Risk or Review Needed by materiality); yes+unclear → Review Needed
(contested); yes+yes → no issue on Axis 2; no → no issue.

### Axis 3 — Conditional protection
**Q-A:** "Does the tenant have a protection, remedy, right, or limitation on landlord action for
this provision?"
Choices: yes / no / unclear

**Q-B:** "If yes — is that protection conditioned on narrow, difficult-to-meet, landlord-controlled,
or uncommon triggers, such that common or foreseeable failure cases are left uncovered?"
Choices: yes / no / unclear / n.a.

Routing: yes+yes → candidate or Review Needed (by materiality and how restrictive the condition is);
yes+unclear → Review Needed; yes+no → no issue on Axis 3; no → no issue.

### Axis 4 — Unilateral control
"Can the landlord, or another party not the tenant, alter, trigger, waive, delay, or control the
condition that affects the tenant's protection or exposure — without meaningful tenant consent,
notification right, or remedy?"
Choices: yes / no / unclear / n.a.

Citation: cite the control right AND the tenant consequence specifically.

Routing: yes → candidate if material; unclear → Review Needed; no → no issue.

## Output schema (per prototype LP)

```
lp_id: string
lp_name: string
axis_results: [
  {
    axis_id: "axis1" | "axis2" | "axis3" | "axis4"
    question_id: "q_a" | "q_b" | "standalone"
    answer: "yes" | "no" | "unclear" | "n.a."
    citations: [string]   // section references; required for axis1 and axis4
    reason: string        // explanation only — DISPLAY-ONLY, never read by routing
  }
]
axis_supported_candidate: bool   // computed from CLOSED ANSWERS ONLY
contested: bool
contested_reason: string | null
proposed_bucket: "Risk" | "Review Needed" | "Improvement" | "Addressed"
materiality: "high" | "medium" | "low" | "unclear"
materiality_reason: string
final_candidate_summary: string
```

**Critical schema constraint:** the `reason` and `citations` fields in each `axis_result` are
DISPLAY-ONLY. The code that sets `axis_supported_candidate` must not read them. It reads only:
`axis_id`, `question_id`, and `answer`. Structure enforces this — not instruction.

## Run plan

1. Schema and routing implementation. Unit test the closed-form routing logic (yes+no=candidate,
   yes+unclear=Review Needed, etc.) on mock data before any live runs.
2. One live Atlas run (closed-form prototype LPs only) to verify the schema outputs correctly and
   the structural prose-cannot-create-findings constraint holds.
3. **FREEFORM BASELINE: N=5 on the CURRENT build** (all-freeform, before prototype changes affect
   the prototype LPs). Record LP-03, LP-19, LP-26, LP-27 presence/absence per run.
4. **CLOSED-FORM: N=5 on the prototype build**, same lease, same conditions. Record same LPs.
5. Compare flicker rates freeform vs. closed-form. If closed-form is clean AND LP-03 stabilizes
   relative to the freeform baseline: run N=10 closed-form (and N=10 freeform baseline for comparison).

## Acceptance checks — HUMAN verifies POST-RUN, NOT in the prompt

These are NOT prompts or hints to give the model. They are the criteria the human uses to assess
results after the runs complete.

- **LP-03:** Closed-form Axis 2 should surface the obligation-without-remedy issue consistently
  (Q-A yes + Q-B no), or route Review Needed if Q-B is unclear. AND it should do so more
  stably than the freeform baseline on the same N. If LP-03 appears in 5/5 closed-form runs
  but also 5/5 freeform runs, that's not evidence the closed form helped — check the baseline.
- **LP-19:** Axis 2 should see a remedy exists (Q-A yes + Q-B yes → no Axis 2 issue). Axis 3
  should see it is conditioned on narrow, difficult-to-meet triggers (Q-A yes + Q-B yes →
  Axis 3 candidate or Review Needed). Result: routes contested / Review Needed — NOT forced
  Risk, NOT forced no-action. The tension between Axis 2 and Axis 3 is the diagnostic signal.
- **LP-26:** Should surface via Axis 3 alone (§18.1 double-conditioned protection). Axis 1
  must NOT be needed to surface this finding. Axis 1 should read n.a. or no for LP-26 (the
  "quiet enjoyment breach: §5.1 vs Article 17" generic comparison must NOT produce a yes).
- **LP-27:** Axis 1 should fire and produce a finding (§5.1 vs Article 17 as parallel
  default frameworks IS the valid same-risk comparison). Axis 2 should also fire (60-day
  waiting period, no interim remedy). This is the one LP where Axis 1 contributes substantively.
- **Negative controls (LP-11 or LP-22):** Axis 1 must NOT fire from the generic Article-17
  comparison alone. These findings survive on Axis 2 (LP-11: acceleration obligation without
  anti-acceleration clause) or Axis 3 (LP-22: future SNDA conditioned on commercially-
  reasonable-efforts). Axis 1 should read no or n.a. — not yes — because no specific same-risk
  parallel obligation is named.
- **Wish-list controls (LP-15 or LP-16):** axis_supported_candidate must be FALSE. None of the
  four axes should produce a yes+actionable-routing answer on wish-list findings. These are the
  negative controls for the framework's scalpel property — if LP-15/16 survive, the framework
  is still a wish-list generator.

## Results report — build_log/389_closed_form_directional_prototype_RESULTS.md

Must include:
1. Files changed; prototype LPs in scope; schema/prompt changes.
2. **Structural confirmation:** how the code enforces that prose cannot create findings (which code
   path computes `axis_supported_candidate`; which fields it reads; confirmation it cannot see
   `reason` or `citations`).
3. **The key comparison table:** LP-03 presence/absence across N freeform runs vs. N closed-form
   runs, side by side. This is the primary evidence; everything else is secondary.
4. LP-03 stability result (with baseline comparison).
5. LP-19 contested-routing result.
6. LP-26 Axis-3-only surfacing result (confirm Axis 1 not needed).
7. LP-27 same-risk Axis-1 result.
8. Negative-control results (LP-11/22 — Axis 1 must not fire; LP-15/16 — no candidate generated).
9. Overall wish-list-bias reduction (what fraction of prototype LPs generate a candidate
   closed-form vs. what fraction generated one freeform).
10. DEF-002 status.
11. Case verdict: **A** (mechanism works, negative controls hold, LP-03 stabilizes vs. baseline) /
    **B** (mechanism works, needs refinement) / **C** (fails — recreates wish-list or false stable) /
    **D** (artifact insufficient).

Commit locally. Do not push.

## What 389 can and cannot prove (honest scope)

A clean Case A means: "the closed-form mechanism works on this lease." It does NOT mean the four
axes are the right axes, complete axes, or correctly scoped — the negative controls (LP-15/16
wish-list, LP-11/22 generic-Axis-1) are what give Case A its teeth. If those correctly do NOT
survive while LP-03/19/26/27 do, that is real signal the framework discriminates. But it is still
one lease. 389 is the mechanism test. Second lease is the transfer test. They are different
experiments and 389 cannot substitute for the second-lease test. A clean 389 does not authorize
schema implementation across all LPs or deployment to a second domain.
