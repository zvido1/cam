# CAM Current State — Updated 2026-06-12 (DIRECTIONAL-METHOD ARC: prototype built + tested; auditor architecture discovered. 389 prototype = Case B (LP-11 scalpel proof 10/10→0/5 DECISIVE; LP-15 didn't drop). 390/391 = LP-15 Axis-2 over-fire tightened but migrated Axis-2→Axis-3 (whack-a-mole). 392A/B = cross-domain AUDITOR pattern found (FEVER/GPQA/SciFact/ContractNLI); THREE-LAYER architecture: axis discipline / trace auditor / materiality-routing. LP-15 reframed: not a bug, a valid-trace materiality dispute. §8.3 still unsurfaced = cleanest next target. DEF-002 still blocked on layer-3.)

> **ORIENTATION FOR A NEW READER (next-thread Claude / GPT) — read THIS block first.** The live
> frontier as of 2026-06-12 is the DIRECTIONAL-METHOD / CROSS-DOMAIN-AUDITOR arc (steps 389–392B),
> summarized in the "Where things stand (2026-06-11)" section immediately below this block. The
> 2026-06-10 RECALL-STABILITY arc (steps 377–385) is now CLOSED HISTORY (shipped: `6990434`,
> `d134ef8`) and appears below the directional-method section under the "CLOSED HISTORY" divider.
> The 2026-06-07 P2''/376h block is CLOSED HISTORY (shipped, pushed, live). The 375E-DIR and 375I–L
> blocks are SETTLED HISTORY. The 372-chain is CLOSED HISTORY. Authoritative defect/decision record:
> `build_log/defects.md` (DEF-001 through DEF-012) and `build_log/parked_strategic_ideas.md`.
>
> **NEW ASSET 2026-06-14 (not a build change, freeze intact):** EDGAR mini-corpus — first external
> real-lease fixture set. 8 executed commercial leases from SEC filings (10-K/10-Q Exhibit 10.x),
> 4 property types, 6 jurisdictions, populated/absent work-scope split 3/5, 48/48 fixture checks pass.
> Committed local `b1ec8e7` (UNPUSHED). Fixtures in `05 Lease Analyzer/test_data/tenants/`; manifest
> `05 Lease Analyzer/test_data/edgar_corpus_manifest.json`; build `build_log/build_edgar_corpus.py`.
> This is FIXTURE MATERIAL ONLY — NOT yet run through the pipeline, NOT a validation result, NOT a
> patent contribution. Sharpest fixtures: Atreca pair (near-controlled contrast in the STRUCTURE of
> landlord work — EX-10.18 existing-building Landlord's-Work vs EX-10.19 to-be-constructed shell +
> tenant-built TIs; BOTH populated) and BOKF As-Is Work Letter (document-present / obligation-absent
> edge case). The cleanest populated-vs-ABSENT contrast pairs a populated lease against an absent one
> (DiVall Wendy's NNN / Quanterix / SolidPower), NOT the two Atreca leases. See `Docs/NEW_THREAD_PROMPT.md`
> for the binding-constraint framing: this closed the self-serviceable validation move; human (lawyer)
> reaction is now the sole remaining trajectory-mover.

## Where things stand (2026-06-11 — the live frontier: the closed-form directional METHOD)

**NEW READER: read the directional-method docs in this order:**
`build_log/strategic_pivot_methodology_2026_06_11.md` (CAM is a domain-general method; lease analyzer
is instance one) → `build_log/directional_question_audit_2026_06_11.md` (the current Q2 is a wish-list
defect factory; the discriminating question is latent in Evaluator B's q2a/q2b; four domain-general
axes extracted + paper-validated) → `build_log/387_directional_axis_coverage_and_control_audit.md`
(axes tested vs 27 findings: 12 dropped as wish-list, 15 retained, marginal Case A) →
`build_log/388_chat_instruction.md` (the LIVE GATE: is Axis-1 fact-anchored or just the
"landlord-has-Article-17" constant in disguise?).

### The directional-method arc (2026-06-11) — where the recall investigation LANDED
The recall flicker (LP-03/19/26) traced to source: the directional-risk question has no enumerated
home. Stage 7 Pass-1 asks Q1 cross-coverage (enumerated, stable) + Q2 directional (freeform "is it
one-sided?", flickers). The current Q2 is a WISH-LIST GENERATOR — it flagged 27 of 27 LPs as
`tenant_unprotected` by asking, in effect, "can you imagine an additional protection this clause
lacks?" (always yes). KEY DISCOVERY: the discriminating question already exists, latent in Evaluator
B's use of `q2a` (does protection exist + run the right way) and `q2b` (proportional vs
disproportionate). Evaluator C wanders to "tenant unprotected"; B finds the real asymmetry. FIX SHAPE:
make q2a/q2b the REQUIRED closed verdict, demote the freeform note to explanation-only (the
closed-verdict+reason principle). Four domain-general axes extracted from the real findings:
(1) Proportionality, (2) Obligation-without-remedy, (3) Conditional-protection, (4) Unilateral-control.
These are CONTRACT-GENERAL (NDA/SaaS/employment too) = the cookie cutter, the methodology pivot made
concrete.

**387 axis audit result:** 27 findings -> 12 DROPPED as wish-list-only, 15 retained = MARGINAL Case A
(landed exactly on the threshold). The 44% drop is meaningful (discarded findings were concentrated in
the old failure mode). Known cases: LP-03 = FIXABLE via Axis 2 (the §8.3 rent-before-ready trap is
deterministic once the closed obligation/remedy pair is asked; this run produced only the LOW-severity
wish-list version, the closed question forces the HIGH-severity real finding every run). LP-19 =
GENUINELY CONTESTED (Axis 2 "remedy exists via §6.3" vs Axis 3 "remedy gated on negligence +
untenantable + 5-day threshold, common case uncovered" — opposite readings = the 1:1:1 cause; route as
Review Needed/contested, NOT forced Risk; non-deliberation doctrine validated at clause level). LP-26 =
AXIS-SUPPORTED (Axis 3 conditional + Axis 1 proportionality). The axes are both a FIX (force closed
verdict) and a DIAGNOSTIC (separate fixable-unasked-question from genuinely-contested).

**388 is the LIVE GATE (a real gate, NOT a rubber stamp — predicted result is Case B).** The retained
15 landed exactly on threshold, so the marginal pass hinges on Axis 1. Risk: Axis 1 (proportionality)
may be firing on the near-CONSTANT "landlord has broader Article 17 remedies than tenant" (true of
almost every lease = a second defect factory in a tie) rather than concrete SAME-RISK disproportions.
Evaluator B used the same "narrower than Article 17" sentence across 6 findings. 388 checks whether
Axis-1-only findings are same-risk-anchored (keep) or generic-Article-17 (demote). The HEADLINE number
is the POST-TIGHTENING retained count, compared to threshold — not the pre-tightening 15. If Case B:
demote Axis 1 to MODIFIER-ONLY (can strengthen an Axis-2/3/4 finding, never a standalone trigger), then
prototype. If Case A: prototype 5-8 LPs (LP-03 stability + LP-19 contested-routing). DEF-002 blocked
through all of it.

**388 RESULT (2026-06-11, commit 0447005 local-only) — Case B confirmed, ZERO collateral. GATE CLEARED.**
The feared "Axis 1 props up the count" turned out FALSE in the best way: ZERO retained findings are
Axis-1-ONLY, so demoting Axis 1 to modifier-only drops NOTHING — the 15 hold. Axis 1 appears in 7 of 15
(LP-06, LP-11, LP-20, LP-22, LP-26, LP-27, LP-28); in 6 of 7 it is DECORATIVE (the finding survives on
Axis 2 or 3 without it). The ONE genuine same-risk Axis-1 finding is LP-27 ("default by either party"
is the symmetric event; §5.1 vs Article 17 is a specific NAMED parallel comparison). 3 of 7 are pure
generic-Article-17 (LP-11, LP-22, LP-26); LP-26's real support is Axis 3 ALONE (confirmed). So the
"marginal" Case A from 387 was an artifact of counting Axis-1 decoration as support — the real retained
set is 15 genuine Axis-2/3 findings, a comfortable clear. **Axis 1 RULE for v1: modifier-only, never a
standalone trigger; requires a SAME-RISK cited comparison; "narrower than Article 17 generally" does
NOT satisfy it.** Canonical fixtures now labeled: LP-03 = Axis-2 obligation-without-remedy prototype;
LP-19 = axis-contested (Axis 2 vs 3); LP-26 = Axis-3 conditional (Axis 1 must NOT carry it); LP-27 =
valid same-risk Axis-1; LP-11/LP-22 = negative Axis-1 controls; LP-15/LP-16 = wish-list controls.

**NEXT = Step 389 closed-form directional PROTOTYPE (mechanism test, NOT transfer test).** Sequencing
decided: prototype NOW (5-8 LPs on Atlas) → then second LEASE (transfer) → then second DOMAIN. Rationale:
389 tests whether the closed-form MECHANISM works at all; testing transfer before mechanism is
"validating fog." THREE CONTAMINATION GUARDS the 389 spec MUST enforce (these are the difference
between a real test and a false Case A): (1) the axis questions in the model-facing prompt must be
GENERIC / lease-agnostic — the canonical LP-03/19/26 expectations are POST-RUN human ACCEPTANCE CHECKS
and must NEVER appear in the prompt (writing "find the §8.3 trap" into the prompt makes LP-03 surface
for the wrong reason = false pass); (2) require a FREEFORM BASELINE run on the SAME N — LP-03 was
already present 8/10 in freeform, so 5/5 closed-form could be luck; stabilization must be measured
AGAINST the old behavior, not in a vacuum; (3) enforce "prose can't create findings" STRUCTURALLY —
routing/candidate logic reads CLOSED ANSWER FIELDS ONLY; the reason/citation fields are display-only and
not visible to candidate generation (structure, not instruction). Even a clean 389 = "mechanism works
on ONE lease," NOT "axes are right/complete" — the negative controls (LP-15/16, LP-11/22) are what give
Case A its teeth.

**389 PROTOTYPE RESULT (2026-06-11/12, commit 0ff3cc2 local) — Case B; LP-11 scalpel proof DECISIVE.**
Closed-form prototype on 6 LPs, N=5 closed-form vs N=10 freeform baseline, all three guards enforced
(Guard 3 structural: candidate logic reads closed-answer fields only, prose display-only, 27/27 unit
tests). HEADLINE: LP-11 freeform 10/10 → closed-form 0/5 — a finding the OLD system flagged every run,
the closed form rejects every run = the scalpel proof; the mechanism DISCRIMINATES, not a reworded
wish-list. LP-03/19/26 went 80-90% freeform → 5/5 closed-form (stabilized against baseline). LP-19
routes contested. LP-26 surfaces without Axis 1 (2/3 evaluators). LP-27 genuine Axis-1 (2/3; Eval-C
all-no = largest split). BUT LP-15 (wish-list control) did NOT drop (5/5). LP-03 honesty: the surfacing
finding is the RENEWAL/§2.2-appraiser trap, NOT the §8.3 Landlord's-Work trap — §8.3 STILL UNSURFACED.

**390/391 LP-15 — Axis-2 over-fire tightened, then MIGRATED (whack-a-mole).** 390 read: Eval-A's LP-15
Axis-2 was an over-fire ("landlord conditions SUCH AS ... MAY NOT be met" = hypothetical category, fails
the four-part test). 391 (commit c709b74 + 33c139f local) tightened Axis 2 to require naming all four
(obligation / specific landlord failure / specific consequence / missing remedy) with a q_a_confirmed
field. Result: Axis-2 over-fire BLOCKED for Eval-A/C — but LP-15 STILL 5/5, because the over-fire MOVED
to Axis 3 (Eval-A reads the insurance covenant as conditional protection) and Eval-B fires Axis 2 in
3/5. Under ANY-evaluator voting, one over-eager evaluator sustains the candidate alone. KEY INSIGHT:
the wish-list bias isn't in any single axis — it's in Eval-A's DISPOSITION to find LP-15 problematic,
re-expressing through whatever axis is open. (Three data points: Axis-1/LP-26 in 388, Axis-2/LP-15 in
390, Axis-3/LP-15 in 391 — the "smarter model editorializes" pattern, parked model-tier hypothesis.)

**392A — CROSS-DOMAIN AUDITOR LINEAGE (patent asset; `build_log/392A_*`).** Tzvi recalled an "enforcer."
It exists, named AUDITOR, in ALL FOUR benchmark domains, evolving: FEVER (standalone process auditor —
checks reasoning TRACE vs declared standard, can invalidate even under consensus; violation codes
HIDDEN_ASSUMPTION / UNSUPPORTED_INFERENCE) → GPQA (auditor + adversarial falsification: unanimity
challenge, fidelity/representation/resurrection/stress-test) → SciFact (auditor FLAG + rule library +
WITHHOLD + conviction test — DOCUMENTED over-withhold failure: RULE-SF-002 suppressed correct NEIs) →
ContractNLI (auditor + elimination + model-DIVERSIFIED governance — QUANTIFIED tradeoff: CCA 80.4%→83.2%
but Withheld 17→33, MANY correct [OK]→[WH]). CONCLUSION: auditor is GENERAL CAM machinery, grew BIGGER
across domains (Tzvi's "later ones didn't need it" corrected — they needed it MORE). The lease analyzer
is the ONLY domain LACKING the layer — why LP-15 survives. The HEAVY withhold/elimination version is
DANGEROUS for legal review (over-withhold = suppressing real risk = unforgivable). Port the LIGHT
FEVER-style trace-compliance auditor FIRST, not the rule-library/elimination stack.

**392B — LP-15/LP-03 AUDITOR PAPER TEST (`build_log/392B_*`) — Case B-variant; THREE-LAYER architecture.**
Hand-ran the light auditor against REAL 391 traces. Result is NOT the expected clean kill: the 390 LP-15
trace (hypothetical) WOULD be invalidated, but the 391 LP-15 trace is now SPECIFIC and CITED ($10M
umbrella §10.1(e) vs $5M §10.2(b); negligence §11.1(b) vs gross-negligence §11.2(b); §10.3 subrogation
waiver limited to insured losses) — so the light auditor PRESERVES it (passes valid traces by design).
LP-03 renewal trap and LP-27 same-risk Axis-1 also preserved (specific, cited, four-part). THE FINDING:
LP-15 MIGRATED from a trace-validity problem (390, auditable, killable) to a MATERIALITY problem (391,
NOT auditable — the asymmetries are REAL and IN THE TEXT; B/C judge them immaterial = a genuine 1-vs-2
materiality split). LP-15 is likely NOT a bug — possibly a correctly-surfaced contested finding,
MISLABELED as a control.

**THE THREE-LAYER ARCHITECTURE (now official doctrine):**
1. Axis discipline — force closed-form questions (387-391; SOLVED).
2. Trace auditor — reject unsupported/hypothetical reasoning (light FEVER-style; DESIGNED+paper-validated,
   NOT built; port spec-gated, trace-compliance ONLY not withhold/elimination).
3. Materiality / routing — decide what to do with valid-but-disputed/minority findings (OPEN; needs the
   lawyer panel as a structural input; BLOCKS DEF-002, whose bucketing IS a layer-3 decision).
Refined minority doctrine (KEEPER): **a lone evaluator survives if its trace is VALID, not because it
produced a finding / is loud in JSON.** Minority preserved as SIGNAL after passing the validity gate,
but valid ≠ automatic Risk — materiality and agreement govern the bucket. This sharpens "minority never
silenced": protected when WELL-REASONED, not merely PRESENT.

**OPEN ITEMS (all gated, none built):** (a) port light auditor as layer 2 (spec required; trace-
compliance only). (b) LP-15 → lawyer-panel materiality question ("is $10M/$5M + negligence/gross-
negligence a material one-sided term or standard allocation?"); if lawyers split, route Review Needed,
LP-15 was a mislabeled control. (c) §8.3 Landlord's-Work trap = cleanest next closed-form target — a
trap of ABSENCE (missing abatement remedy), different shape than the four present-text axes; may reveal
whether a 5th axis is needed or Axis-2 just isn't triggering. (d) layer-3 voting question: does a lone
valid-but-low-materiality trace force a candidate? (e) DEF-002 stays BLOCKED until layer-3 doctrine
settles. Artifacts: `build_log/389_*`, `390_*`, `391_*`, `392A_*`, `392B_*`; auditor prompts at
`01 FEVER/prompts/auditor_prompt_V1.2.txt`, `02 GPQA/prompts/auditor.txt`+`unanimity_challenge.txt`.

**STANDING:** all directional-method validation so far is on ONE lease (Atlas). Even a clean 388 means
"ready for PROTOTYPE," not "validated" — real validation is the closed-form questions holding their
drop-rate + axis-distribution across MULTIPLE leases (the cross-domain methodology test). Do NOT build
the schema until 388 clears Axis 1 AND (for contested findings) a calibration source confirms the
split is real professional disagreement, not tool noise.

---

## CLOSED HISTORY below this line (2026-06-10 recall-stability arc and earlier)

## Where things stood (2026-06-10 — the recall-stability frontier, now folded into the method arc above)

**Two things shipped to main since 06-07: the 378 governance-correctness batch (`6990434`) and
DEF-010a coverage-consensus normalization (`d134ef8`). The live question is now RECALL STABILITY —
whether material directional findings are GENERATED consistently enough run-to-run to support an
external-facing consolidated view (DEF-002). DEF-002 is BLOCKED on this.**

### Shipped since 06-07
- **Step 378 governance-correctness batch (`6990434`, pushed)** — fixed verified defects DEF-003
  through DEF-009 (consequence support floor, materiality majority-merge replacing strict-min,
  materiality_source masquerade, unknown-verdict distance hardening, API-call counting, the stale
  STAGE_5D doc, F8 smaller items). Two doctrine pins enforced in code: (DEF-003) a single valid
  consequence evaluator may not route Risk as `assert`/`assessed`; (DEF-004) materiality merges by
  2/3 majority not strict-min, and no-majority {high,medium,low} routes Review Needed. F7/DEF-009
  (tenant-hardwired consequence prompt on landlord runs) FENCED not fixed — landlord-perspective
  consequence output remains unvalidated. Validated by post-push repeatability check (two Atlas runs
  on same commit): Dir-18 confirmed the DEF-004 majority correction live, Dir-21 confirmed the
  no-majority pin live, no Case-C regression. cam/core untouched.
- **DEF-010a coverage-consensus normalization (`d134ef8`, pushed)** — `merge_element_verdicts()` in
  `lease_coverage_305.py` now normalizes the four present-like verdicts (explicitly_present /
  implicitly_present / covered_by_default_law / covered_in_other_LP) to one "present_like" tier for
  the Counter / majority computation ONLY, then re-expands to the most-explicit specific label.
  Raw per-evaluator labels preserved unchanged for audit. Fixes the LP-13 flicker: three evaluators
  agreeing an element is PRESENT but disagreeing on MECHANISM no longer collapse to `unclear`.
  `lease_verdict_distance.py` and Stage 7 `_FLAGGED_STATES` deliberately UNTOUCHED. 18/18 tests.
  cam/core untouched.

### The recall investigation (377–384, the arc that produced the above)
- **Root cause found (380):** LP-13 (indemnification/negligence-carveout, a harmful high-materiality
  unanimous Risk finding) appeared in some runs and VANISHED in others on byte-identical input. Traced
  to Stage 305 coverage consensus treating mechanism-disagreement as existence-disagreement → spurious
  `unclear` → coverage_state flips review_needed↔covered → Stage 7 attention gate forwards on
  review_needed, excludes on covered → finding appears/vanishes. DEF-010a fixes the consensus half.
- **Live validation (383, N=10 keyed Atlas runs on `d134ef8`):** LP-13 now `covered` 10/10, never
  flickers. The HARD case recurred live in run 3 (IP / EP / CD_by_default_law — three distinct
  present-like labels, no majority pre-fix) and DEF-010a resolved it correctly. DEF-010a validated
  at the strongest available level (unit test + live hard-case recurrence).
- **Residual recall instability (384, the DEF-002 blocker):** three OTHER material findings still
  appear/disappear, via THREE DISTINCT mechanisms (Case A/B MIXED — they do NOT cluster):
  - **LP-03** (disappears runs 6,7): a Stage 7 PASS-1 GENERATION miss — CONFIRMED by step 385
    trace (Case B). Coverage output is pixel-identical across compared runs and LP-03 is correctly
    in Stage 7 `attention_items` in the absent runs, so neither coverage nor the attention gate is
    the failure layer. LP-03 disappears solely because Stage 7 Pass-1 does not PROPOSE it as a
    candidate in runs 6,7 (candidate count 24 vs 26-27; run 7 also dropped LP-17). When LP-03 does
    reach Pass-2 it confirms harmful/high/Risk consistently — so the finding would have survived had
    Pass-1 generated it. It is legally unambiguous; NO Joshua question needed. LIMITATION: Pass-1 raw
    input/output is NOT persisted, so the trace found the failure LAYER but not the MECHANISM
    (truncation/capacity vs prompt-ordering vs model-judgment omission vs parser loss). The run-7
    LP-03+LP-17 co-drop hints the drops correlate with candidate-list length → truncation is a live
    hypothesis. NEXT: step 386 instruments Pass-1 (persist raw input/output, finish_reason, parsed
    candidates, dropped-attention summary, candidate density) then N=10 to capture the mechanism.
    Do NOT build the post-Pass-1 validation gate until the mechanism is measured — if it is
    truncation, a config fix is correct and a governance gate would be over-engineering (and a
    weaker patent story). This is the second live instance of Future Patent Item B
    (candidate-completeness / recall governance); LP-13 was the first.

  **386 RESULT (2026-06-11) — CONFIRMED: MODEL-JUDGMENT OMISSION, and LP-03 REFRAMED.** N=10
  instrumented Atlas run (raw Pass-1 output persisted). LP-03 dropped 1/10 (run 5, density 0.926).
  Reading the raw output: all three evaluators SAW LP-03 at its attention position, assessed the
  initial-term coverage adequate (cited Sections 1.2/2.1/2.2, actual dates), and returned
  `mismatch_flag=false`. NOT truncation, NOT parser loss, NOT identity drift — the models
  affirmatively JUDGED no mismatch. The "selective summarizer" hypothesis is confirmed at the most
  direct level (you can read the model reasoning its way to "this is fine").
  **CRITICAL REFRAME:** LP-03 is NO LONGER a "clean code bug / no Joshua needed." It is
  JUDGMENT-VARIANCE, the same phenomenon as LP-19/LP-26 — the model reaches a genuinely different
  substantive judgment run-to-run. The "3-0 when present" was misleading: it confirms 3-0
  CONDITIONAL on being raised, but whether it gets raised is itself a judgment coin-flip. The fix
  is now WORLD-DEPENDENT and cannot be chosen from artifacts:
    - IF LP-03's coverage is genuinely adequate (model's "no mismatch" is correct) → the
      over-generation runs are the error; correct behavior is CONSISTENT non-flagging; LP-03 was
      never supposed to be Risk (the LP-13 pattern). Fix = stabilize toward silence.
    - IF coverage is genuinely inadequate (the "mismatch" runs are correct) → the "no mismatch"
      judgment is the model being WRONG some runs; fix = candidate-completeness governance (flagged
      LP must produce a candidate so Pass-2 adjudicates). = Future Patent Item B.
  Only a lawyer reading the actual clause can say which world. So LP-03 JOINS the lawyer-panel list.
  **BROADER FINDING (the real DEF-002 blocker):** the drop pattern is NOT LP-03-specific. Across 10
  runs: LP-03 dropped 1×, LP-26 1×, LP-19 2×, LP-17 1× — FOUR different findings, density dipping to
  0.926. Pass-1 has a GENERAL judgment-variance recall property (~10-15% of runs omit some flagged
  provision by judgment). This is a PROPERTY of the generation stage, not a per-finding quirk — which
  makes candidate-completeness an ARCHITECTURAL question (Future Patent Item B), not a patch.
  **DO NOT BUILD THE COMPLETENESS GATE YET:** in world-1 (model judgment correct) a gate that forces
  findings through would MANUFACTURE false positives. Measure which world via the lawyer panel first.
  **NEXT MOVE: lawyer-PANEL calibration (NOT one oracle, NOT $800/hr Joshua-as-authority).** Send
  LP-03/LP-19/LP-26/§11.2 to 2-3 CRE lawyers, fixed-fee, bucket-only (Risk/Review-Needed-depends/
  Drafting-improvement/Standard), ANSWERED INDEPENDENTLY (no conferring — the DISTRIBUTION is the
  data; conferring collapses the panel into one consensus and destroys the signal). The four buckets
  map onto CAM's own output buckets, so the panel calibrates CAM's routing against human routing on
  contested clauses. If the human panel SPLITS the same way the models split, that is LIVE EVIDENCE
  the non-deliberation doctrine (Supp #22) is calibrated to genuine professional disagreement — a
  patent-grade validation with a human control group, for the cost of three emails.

  **OPERATIONAL FLAG:** the 386 harness ran messily (two harnesses competed on one checkpoint, stale
  .pyc, a stalled run, recovery-from-disk). The raw-OUTPUT reads are trustworthy (files on disk); the
  checkpoint bookkeeping is less so. Second time the harness tooling itself was the fragile link (379
  couldn't run, 386 ran twice over itself). The measurement apparatus needs HARDENING before it feeds
  anything validator-facing.
  - **LP-19** (disappears runs 2,5): consequence NONDETERMINISM — evaluators split 1:1:1 on
    use_consequence (harmful/beneficial/context_dependent) across runs. May be genuine interpretive
    ambiguity (service-interruption gap may be neutral for a separately-metered tenant), not a bug.

  **386 PREFLIGHT UPDATE (2026-06-10) — truncation structurally disfavored for LP-03.** The Pass-1
  output cap is 12K tokens (raised 8K→12K at Step 372c, `9f60d23` — the bump that protects THIS
  call), estimated successful Pass-1 output is ~5.4–10.8K (comfortable headroom), AND the killer
  fact: LP-03 is at POSITION 5 of 27 in the attention list. Tail-truncation cannot drop item 5
  while keeping items 1–4 intact. So the remaining live hypothesis is MODEL-JUDGMENT OMISSION at
  candidate generation — Pass-1 is behaving like a discretionary issue-spotter ("selective
  summarizer") instead of a high-recall candidate generator. This is a ROLE-ASSIGNMENT mismatch:
  discretion belongs in Pass-2 (which culls), not Pass-1 (which should cast wide). The same
  judgment-nondeterminism may underlie LP-19/LP-26 — all three could be one phenomenon (frontier
  models making non-deterministic salience calls on judgeable questions) surfacing at different
  stages. Step 386 instrumentation persists verbatim Pass-1 raw output; reading whether LP-03
  appears at position 5 in the raw text on dropped runs is MORE diagnostic than finish_reason and
  resolves parser-loss vs model-omission directly. finish_reason threading deferred (clean
  Step-372c-class telemetry pass-through, available if needed, NOT needed given position-5).
  Likely fix order IF model-omission confirmed: (1) correct Pass-1 PROMPT ROLE to mandate a
  candidate per attention LP (cheap, root cause), (2) add candidate-completeness GATE as enforcement
  (durable, = Future Patent Item B), (3) re-run N to confirm. Do NOT skip the prompt fix for the
  gate alone. N=10 instrumented run in progress.
  - **LP-26** (disappears runs 5,6): same mechanism — polarity reversal (harmful↔neutral) on quiet
    enjoyment / SNDA absence. May be genuine ambiguity (non-disturbance need depends on deal context).
  - The run-2/run-10 bucket outliers (low Risk, high Review Needed via mismatch_support_insufficient)
    are a SEPARATE Stage 7 softness issue and do NOT drive the disappearances. Lowest urgency.

### Live decisions / two-lane workplan (2026-06-10)
- **Code lane:** LP-03 generation trace (385, read-only, on the 10 existing N=10 artifacts) — locate
  why a confident finding intermittently fails to generate. No lawyer needed.
- **Legal-calibration lane (NOT on the critical path):** LP-19 / LP-26 / §11.2 indemnification need a
  legal read on whether the clause is genuinely CONTESTED among CRE lawyers — NOT "what is the answer."
  If lawyers genuinely disagree, CAM's preserved evaluator disagreement is CORRECT (non-deliberation
  doctrine, Supplement #22), and the "disappearance" is the consequence layer correctly declining to
  assert — a presentation question, not a stability bug. Design decision: do NOT treat one lawyer as
  oracle (esp. at $800/hr); use a fixed-fee micro-panel (≥2–3 CRE contacts, bucket-only:
  Risk/Depends/Standard/Improvement). The DISTRIBUTION of their answers is the data: 3/3 agree → route
  confidently; 1/1/1 split → CAM's Review-Needed output is validated, log as evidence not defect.
  §11.2 indemnification is the one most likely to have a CONSENSUS answer, so it's the best single-read
  target if a panel isn't available.
- **DEF-010b DEFERRED** (Stage 7 gate widening to forward `covered` LPs with mechanism-disagreement):
  do NOT build until the legal lane says LP-13's clause deserves to be a finding. Forcing LP-13 back
  into Stage 7 may be resurrecting a finding the corrected pipeline correctly declined to make.
- **DEF-002 BLOCKED** until LP-03 is diagnosed AND the legal lane resolves whether LP-19/LP-26 are
  bugs or working-as-designed ambiguity.

### Telemetry / cost (DEF-012, logged not built)
N=10 confirmed 94 API calls/run but artifacts store NO per-call token counts, so cost-per-run cannot
be computed (only call count). Needed before pricing/licensing math, not before DEF-002. The 4-model
frontier stack (gpt-5.5, grok-4.3, gemini-3.1-pro-preview, claude-sonnet-4-6) also lacks a reliable
pricing table. Future telemetry-economics item.

### Environment note (resolved this arc)
The keyed-run harness initially could not run locally (AppX Python 3.13 shell lacked the model SDKs).
Root cause: wrong interpreter + missing SDKs, NOT missing keys. API keys live at
`C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env` — now documented in CLAUDE.md
under "Environment — RUNNING THE PIPELINE." Keyed runs execute correctly once the right venv/SDKs are
used; the N=10 harness (383) ran clean. Any future "cannot run" must name which of keys/SDK/interpreter
is missing, not stop at "no API keys."

---

> **CLOSED HISTORY BELOW — the 2026-06-07 P2''/376h frontier (shipped, pushed, live):**
> The 375E-DIR investigation arc is CLOSED at the code-seam + policy-paper level.
> The 375I–L block below it is SETTLED INVESTIGATION (correct, but superseded by its closeout).
> Everything under the 372-chain is CLOSED HISTORY.

## Where things stand (2026-06-07 — the live frontier)

**P2'' directional routing is SHIPPED to production. The 375E-DIR arc is fully closed:
investigation → policy → production wiring → audit-hole fix, all on main.**

### Shipped TODAY (2026-06-07)
- **376h (`8bd4267`)** — P2'' production routing wired into the live directional classification
  path. New helper `classify_directional_p2pp()` + `apply_p2pp_routing()` in
  `cam/adapters/lease_review/lease_p2pp_routing.py`; wired in `lease_adapter.py` after Stage 5e-F;
  `app.js` classifyFindingType reads P2'' buckets first (v466→v467). Strict early-return precedence
  (rules 1→6): provenance/support guardrail → context_dependent → harmful-material → beneficial →
  neutral → low-harmful. Sign computed + emitted but `routing_use=diagnostic_only` — never moves a
  bucket. All 6 gates passed. cam/core untouched.
  - **Governance principle enshrined: agreement on direction is not agreement on harm.** P2'' routes
    genuinely-uncertain (context_dependent) consequence to Review Needed even on unanimous directional
    agreement.
  - **Canonical proof case: fb6529 LP-24.** Pre-376h routed it to Risk by sign/vote (3-0 verified,
    tenant_unprotected). 376h routes it to Review Needed because consequence is context_dependent,
    grounded in lease text (LP-10 §8.4 TI framework; LP-25 §14.1 trade-fixture protection; LP-24
    silent on insurance-proceeds disposition). Harm not established as present, but contingency is
    real and lease-grounded — Review Needed is correct. Demotion is intentional and documented.
  - Behavioral change vs pre-376h: ONLY fb6529 LP-24 (Risk→Review Needed). c0927f LP-05/LP-32
    unchanged (already review_needed). All others unchanged.
- **DEF-001 (`ba26ed8`)** — consequence-reasoning persistence. Stage 5e-F already computed
  `use_reasoning` / `confidence` / `evaluator_agreement` per finding but the attach loops dropped them.
  Now persists `use_consequence_reasoning` / `consequence_confidence` /
  `consequence_evaluator_agreement` across all 4 attach paths (copy where available, null honestly where
  no evaluator ran). Closes the audit hole surfaced by LP-24: `source=assessed` is now backed by
  inspectable reasoning. No routing/prompt/model change; cam/core untouched. Resolved in defects.md.

### Verification owed (housekeeping)
Railway CLI token expired both pushes — auto-deploy of `8bd4267` and `ba26ed8` must be confirmed
green in the Railway dashboard, then hard-refresh for v467.

### Known soft spot (not a blocker, watch opportunistically)
DEF-001 proved the persistence MECHANISM via fixture (hand-written reasoning strings). The QUALITY of
persisted reasoning on a real keyed run is unverified. Next time a real run happens for other reasons,
glance at whether a context_dependent finding's `use_consequence_reasoning` is substantive enough to
audit a demotion, or a thin one-liner. If thin → future prompt-tuning item. Not a build to start now.

---

## Prior frontier (2026-06-06 — superseded by the 2026-06-07 shipping above)

**The 375E-DIR arc reached a clean stopping point: code seam closed, doctrine caught up, routing
policy named provisional on paper. No production routing build is authorized.**

### Shipped code (on main, `3873854`, Railway redeployed)
Push bundle in order: `771f1ef` (COV-A) → `fc8d3dc` (A2) → `8de0d74` (A2b) → `3873854` (376).
- **COV-A / A2 / A2b**: corrected consequence (`use_consequence`) + provenance (`*_source`) fields;
  `stage7_direction` now copies actual `directionality` at every write site (hardcode removed).
- **376**: removed the LP-27 hardcoded directional-sign override. `_DIRECTIONALITY_MAP` and
  `_AFFECTED_PARTY_MAP` in `cam/adapters/lease_review/lease_synthesis.py` emptied to `{}`;
  `_normalize_directionality` is now a pass-through no-op (unit-tested 5/5). Scan
  (`376_sign_constant_scan.py`) confirmed NO remaining forced-sign constants — only the legitimate
  `exposed_party`-driven derivation (L1944/L1946), a comment (L495), and prompt schemas remain.
- No routing logic in `lease_synthesis.py` changed for the policy work — that is all paper.

### Doctrine caught up (architecture doc amended)
`build_log/375E_architecture_doc.md` block (d) corrects block (a): **sign instability is
EVALUATOR-LEVEL, upstream of the merge** (per-evaluator `exposed_party` flips run-to-run). Merge
governance is necessary but NOT sufficient. Two hardcoded-sign sites existed (1941 + the LP-27 map;
latter removed in 376). Doctrine #7 and the 375E-DIR executable step updated to match.

### Provisional routing policy named: P2' (paper only, NOT production-enabled)
`build_log/375E-DIR_policy_conclusion.md` is the deliverable. **P2' = consequence-anchored,
support-gated, high/medium-collapsed, HARMFUL-ONLY Risk.** Routes 7 of 28 directional findings to
Risk on the audited primary artifact (34f3b9), vs P0-legacy 5-via-wrong-axis and unconstrained P5's
17. Key properties:
- Risk = harmful + assessed high/medium materiality + adequate mismatch support + aligned sign.
- context_dependent → Review Needed (undetermined polarity cannot determine lawyer action type).
- P2' over P1 is a SPECIFICATION-ROBUSTNESS choice (explicit high/medium collapse), NOT a measured
  win — P1/P2 are empirically identical on this artifact.
- **P2' has sign-load-bearing = 0** (does not depend on unmeasured sign-stability) — so production
  gate (iii) is satisfied for P2' specifically, but production WIRING is still a separate build.
- Keyless counterfactual ran clean: 0 hard-constraint leaks, 0 unanchored Risk (375J 18/26 cure
  confirmed), P3/P4 parked at 0 Risk (modeling artifact, sign-stability defaulted unstable).
- **⚠ PERSPECTIVE CAVEAT (2026-06-06): 34f3b9 is a LANDLORD-perspective run** (job.json
  perspective=landlord; 27/28 findings landlord_unprotected). The 7-Risk audit is MECHANISM
  evidence, NOT tenant-facing validation. P2' is downgraded to "structurally specified + row-audited
  on a landlord artifact; tenant-facing validation OUTSTANDING." See
  build_log/375E-DIR_policy_conclusion.md PERSPECTIVE CAVEAT.
- **✅ GATE #1 PASSED (2026-06-07): P2' is INTERNALLY sign-stable on a fresh tenant draw (n=1,
  K=10).** Tenant run fb6529 (376d, all 7 structural exit criteria) → instrumented fresh-draw
  freeze + keyed K=10 replay (376e). 7/7 original Risk rows + 6/6 perspective-flip additions stayed
  P2'-eligible 10/10; 0 unstable, 0 reversals. Consequence-join guardrail worked (3 misses visible,
  routed NeedsReview, outside the Risk set). First-confirming-role rotates overall (A:221/C:25/B:24)
  — uniform tenant sign is NOT a single-role sweep — BUT COHORT R itself was A-first 10/10 (state
  that precisely; multi-role convergence is carried by the broader set, not the 7). Does NOT
  establish cross-contract generalization; does NOT authorize production wiring. Pause holds. See
  build_log/375E-DIR_policy_conclusion.md GATE #1 RESULT.
- **⚠ GATE #2 (2026-06-07): consequence-axis generalization PASSED (n=2); sign gate
  NON-DISCRIMINATING.** Second distinct lease T-09_mixed (retail, run c0927f): directionality came
  back FLAT 23/23 tenant_unprotected (3rd uniform lease in a row — sign tracks RUN PERSPECTIVE, not
  clause balance), but use_consequence was LIVE/MIXED. P2' routed the consequence axis correctly
  (LP-12 beneficial→Favorable; neutrals/context_dependent→Improvement; 13 harmful-material-supported
  →Risk; LP-08 gated out by inadequate support). Sign-gate contribution = 0 rows (removing the
  aligned-sign gate changed nothing). CORRECTION: gate #1 proved sign STABILITY, not MEANINGFULNESS
  — the aligned-sign gate is a rubber stamp on all evidence to date. Production wiring BLOCKED until
  sign is fixed or demoted (376g). Pause holds. See policy conclusion GATE #2 RESULT.
- **✅ P2'' adopted (2026-06-07): sign demoted to diagnostic-only.** 376f-2 confirmed 0 routing drift
  vs P2' on c0927f + fb6529. Sign routes nothing; re-entry requires 376g repair+validation.

### Gated next steps — each a separate deliberate call, NONE pre-authorized
1. **[DONE] Gate #1 — tenant internal sign-stability.** fb6529 (376d) + fresh-draw keyed harness
   (376e). PASSED. P2' Risk set stable K=10 on the tenant draw.
2. **[DONE] Gate #2 — second distinct lease (T-09, c0927f).** Consequence-axis generalization
   PASSED (n=2). Surfaced: sign/directionality is perspective-coupled and non-discriminating.
3. **[DONE — via demotion, NOT repair] P2'' adopted + shipped (376h).** Sign demoted to
   diagnostic-only and wired to production. 376g (sign-mechanism REPAIR) remains OPEN as a separate
   later thread — the open question is still whether to repair sign so it means something or formally
   retire it. Demotion made shipping safe; it did not answer why sign encodes run-perspective.
4. **[DONE] 375E-DIR production build = 376h.** P2'' wired into `lease_adapter.py` after Stage 5e-F
   (new `lease_p2pp_routing.py` helper rather than in-place edits to `lease_synthesis.py:1936/:1941`;
   the old vote→severity and first-confirming-role sign fields are PRESERVED for display/audit, not
   read by routing). DEF-001 then closed the reasoning-persistence audit hole. Both on main.

### REMAINING open build queue (post-376h — none pre-authorized)
- **376g — sign-mechanism investigation (most-pointed-to unstarted build).** Why does directionality
  encode run perspective, not clause balance (uniform across 3 leases)? Decide: repair sign, or
  formally retire it from CAM. Sign is currently inert (diagnostic_only) so this is not urgent, but it
  is the one unresolved question from the directional arc.
- **375H-C — direction-sensitive present-term schema repair.** The THIRD directional problem, never
  fixed: a present-but-one-sided clause (LP-09) scores "covered" and bypasses directional review (no
  polarity check on coverage "present"). DEPLOYMENT TRAP: validated 375H findings must NOT enter
  lawyer-facing Risk until this + routing are sound. GATES the external-use pause lift.
- **Pass-1 candidate-generation recall.** A clause sometimes isn't flagged at all; governed separately
  (a Pass-2 redesign can't fix what never reaches Pass-2). GATES the external-use pause lift.
- **Tenant-facing / cross-perspective breadth validation.** P2'' consequence axis proven n=2; one
  audited artifact (34f3b9) was landlord-perspective. A second consequence-bearing artifact would let
  P2'' be claimed to generalize rather than "works on tenant leases." Needed before over-claiming in a
  patent supplement.
- **Coverage-stage perspective threading (NEXT0)** — fixture-gated correctness repair, deferred.
- **Email notifications broken** (SendGrid 401 / SMTP 535) — real product defect, deferred.
- **UI overhaul** — the original trigger for this whole arc ("why does this show tenant Risk when it's
  favorable" = the routing bug, now fixed). Outstanding UI work: (a) confirm the UI surfaces the
  P2'' bucket + the DEF-001 reasoning so a Review Needed finding explains WHY on screen; (b) broader
  navigation overhaul. Earlier snapshot had a 7→5 tab-reduction sprint — status unconfirmed against
  current frontier.

### Standing constraints (IN FORCE)
- Never read `stage7_direction` or LP-27 `directionality` from frozen artifacts (34f3b9 / 52adbf are
  pre-376); the clean push fixes FUTURE runs, not frozen ones. For LP-27 on frozen artifacts derive
  sign from `exposed_party`.
- **52adbf is P0-continuity ONLY**, never a consequence-anchored cross-walk.
- No count (7 / 9 / 17 etc.) is a CAM metric or patent record — n=1 contract, DIRECTIONAL only.
- **External-use pause on directional Risk totals remains IN FORCE.** 376h fixed the ROUTING half
  (consequence-anchored, sign demoted). The RECALL half is NOT fixed (Pass-1 candidate variance +
  375H-C present-but-one-sided bypass). By the standing criterion the pause lifts only when BOTH
  routing AND recall no longer depend on evaluator-support collapse — so the pause HOLDS. Do not put
  directional Risk/Priority in front of Joshua/demo until recall is also addressed.
- neutral → Improvement is LOCKED this session (don't reopen): a neutral directional finding is not
  a protective-action item; forcing it to Needs Review turns that bucket into a junk drawer.
- `cam/core/` never modified — all 375E-DIR work is adapter-layer.
- Patent: attorney conversation before Sept; non-provisional deadline ~Nov 2026; Architecture A
  Phase 2 standalone supplement still owed.

---

## SETTLED INVESTIGATION — Steps 373–375L (directional-instability; 375I/J/K/L measured; “sign conflict” resolved as vocabulary collision) — superseded by the 375E-DIR closeout above
 
> **ORIENTATION FOR A NEW READER (next-thread Claude / GPT) — read this block first.**
> The CURRENT frontier is the **375 directional investigation**, recorded in the
> "## 375 …" sections lower in this doc and summarized here. The 372-chain material below
> (and the runs/incident sections that follow it) is CLOSED HISTORY — correct, but not the
> live frontier. Do not orient to 372 as "where things stand."
 
## Where things stand (2026-06-04 — the live frontier)
 
The "why does Risk swing 20→36 on the same lease" investigation bottomed out in a clear,
measured diagnosis. SHIPPED this session: absence-polarity sign-error fix (374Z), Pass-2
integrity tripwire (375C), Client Impact block (375G). The core finding (375-R, doctrine-level,
settled): the **directional synthesis path collapses verification-strength into legal severity**
(`3-0→HIGH→Risk` at lease_synthesis.py:1936) — agreement count is being used as the Risk gate,
which is a category error (15b's six-concept ontology forbids it). Frozen-input replay (375D /
375D-2) PROVED the directional vote cannot be stabilized by re-prompting/batching: it's
per-candidate, context-sensitive, and even "stable-unanimous" controls wobble under some context;
separately, Pass-1 candidate GENERATION also varies (a clause sometimes isn't flagged at all).
And 375H found a THIRD, distinct problem: one-sidedness is mis-filed as a coverage-gap property —
a present-but-one-sided clause (LP-09) can score "covered" and bypass directional review entirely
(a SCHEMA defect: coverage "present" = topical presence, no polarity check).
 
**THREE distinct directional problems, do not conflate:** (i) vote-count-as-severity [fix =
375E-DIR two-output redesign]; (ii) Pass-1 candidate-generation variance [recall governance];
(iii) coverage-gated bypass of present-adverse terms [375H direction-sensitive schema repair].
 
**375E architecture doc written** (build_log/375E_architecture_doc.md): doctrine LOCKED
(vote=verification not severity; remove 3-0→HIGH→Risk; materiality assessed independently;
disagreement+integrity stay visible; recall governed separately), routing formula NOT yet locked
(needs counterfactual testing). The redesign makes MATERIALITY the Risk anchor.
 
**375I DONE (materiality-fitness audit; `abf4909`, n=1 frozen lease 52adbf — DIRECTIONAL only).**
Three separate findings, not one headline:
- POPULATED: 5e reaches only 8 of 32 LPs (gate: missing/review_needed always; partial only if ≥50%
  elements missing; covered/N-A never). 100% fill ON those 8 — but 24 LPs get NO assessment.
- ASSESSED-not-DEFAULTED: all 8 are genuine assessments (confidence assert/assert_weak), 0 floor-defaults
  this run. BUT the `or "moderate"` floor (lease_adapter.py:1006/:1461) silently stamps consequence=moderate
  on the 24 gated-out LPs in routing, and NOTHING in the artifact records it as defaulted vs assessed.
  Missing field: `materiality_source`. Silent-default-masquerade is live.
- STABLE (keyed Q3, N=10 identical-input replays): materiality WOBBLES high↔medium on 6/8 eligible LPs
  (LP-03/10/14/16/26/32); LP-05 (medium) and LP-20 (low) held on the materiality axis. Adjacent-bucket
  only, 0 full swings, 0 sign reversals, 0 fallback. NOTE: LP-20 is materiality-stable / DIRECTION-unstable
  (gap_impact wobbled neutral/adverse/context_dependent) — not a clean control.
**375I VERDICT (settled): materiality is promising as a COARSE action axis, NOT trustworthy as a fine
high-vs-medium switch, and NOT trustworthy at all when silently defaulted.** It cannot anchor 375E routing
as-is — but the high↔medium wobble is only a DEFECT if 375E routing treats high and medium as different
action tiers. If 375E collapses high+medium into one "actionable material" tier, 5 of the 6 crossings stop
mattering by design. So the next move is NOT keyed stabilization (that would stabilize a boundary that may
not matter) — it is a keyless test of whether the boundary matters.
 
**375J DONE (routing-boundary counterfactual; `ef3ce96`, KEYLESS, n=1 lease 52adbf — DIRECTIONAL only).**
Replayed candidate routing policies (A high-only / B high+medium-collapse / C source-strict / D conservative /
E materiality-only control) over the 375I Q3 samples + frozen Stage 7 findings. Three results, in priority order:
 
- **(headline that 375J was FOR) the high↔medium wobble does NOT move action buckets under Policy B.** All 6
  wobbling LPs are adverse + {high,medium}; under high+medium collapse all 60 sample-slots route to
  actionable_material_risk — 0 bucket changes. **→ keyed 5e stabilization is NOT needed** (the boundary that
  375I's wobble straddles is erased by design under B). Policy A (high-only) by contrast manufactures pure
  boundary-artifact instability (1–9 risk/needs_review splits) that B eliminates entirely. Provisional on n=1.
- **(THE BIGGER FINDING — sparsity, not wobble, is the danger) 73% of current directional Risk is UNANCHORED.**
  The live classifier routes all 26 directional findings to `risk`. But only 7 have assessed medium/high
  materiality; 18/26 are `source=not_eligible` (LP never reached 5e) and reach Risk ONLY via the silent
  `or "moderate"` floor in lease_adapter.py, undisclosed. So a large part of the Risk count is volume from
  the default floor, not from assessment. This is a SECOND root cause of the original "Risk swing" alongside
  vote-count-as-severity. The 18 not-eligible LPs include provisions material to this warehouse tenant
  (maintenance, SNDA, force majeure, CAM dispute) — not noise.
- **(LP-05 sign question — REFRAMED by 375K below; read that block) Stage 7 and Stage 5e produce different
  signs for the same finding.** Stage 7 says direction=adverse (tenant_unprotected); Stage 5e says
  gap_impact=favorable (absence helps this tenant). 375J read this as "two contradicting direction axes";
  375K corrected that — see the 375K block. Recorded verbatim for the n=1 control: "direction gate not
  exercised by this n=1 artifact — the lease was too one-sided to stress the sign axis, NOT that direction is
  decorative."
**375K DONE (direction-axis reconciliation; `b979da0`, KEYLESS, n=1 lease — DIRECTIONAL only). The 375J
"two contradicting direction axes" framing was itself slightly wrong — 375K reframes it: there is ONE
direction axis and ONE consequence axis, and the bug was routing about to read the consequence axis as a
second opinion on sign.** Axis distribution: 6 aligned / 2 sign_conflict (LP-05, LP-20) / 18 missing-5e / 0
ambiguous. The conflict is a SCHEMA CATEGORY ERROR, not an arbitration problem:
- LP-05 (the load-bearing case; 5e gap_impact STABLE = favorable across all 10 Q3 replays): Stage 7 answers
  "is the conventionally-protective clause PRESENT?" → no → adverse. Stage 5e answers "does its ABSENCE help or
  hurt THIS tenant?" → for a warehouse tenant, absence of a strict permitted-use clause is favorable. BOTH ARE
  CORRECT — different questions, same field name. The clause is missing (direction=adverse) AND its absence
  suits this use (consequence=favorable) simultaneously. The lawyer needs BOTH, not a winner.
- LP-20 (NOT load-bearing): gap_impact UNSTABLE (neutral×8/adverse×1/context_dependent×1) — weak evidence, may
  not be a real conflict at all. So the pattern is n=1 SOLID conflict case, a design signal not a prevalence.
**375K DOCTRINAL FINDING (the real payload): `gap_impact` is a CONSEQUENCE field, not a sign field.** Treating
it as a competing sign producer is the source of the "contradiction." Resolution is NOT "pick a sign winner"
(Rule A vs B) — it's: **Stage 7 = sign, Stage 5e = consequence, both surfaced, neither overriding the other.**
LP-05's correct bucket = adverse-sign + favorable-consequence = "favorable position / don't-negotiate-away"
(≈ Rule B's `improvement_favorable`, but reached via the consequence axis, NOT by overriding the sign). The
"conflict → Needs Review" interim stays correct ONLY until the schema is fixed, because today the system
can't tell a real sign disagreement from this category error. **UNMEASURED:** whether the fix is DEMOTE
gap_impact to consequence-context or SPLIT it into `gap_direction` + `gap_materiality_in_use` — LP-20's
wobble (it emitted "adverse" on one replay) suggests gap_impact may be a confused hybrid TODAY, already
sometimes used as a sign field. Which fix is clean depends on whether the 5e prompt ever legitimately needs a
direction read — a 375E-DIR design question requiring a look at the 5e prompt, not settled by 375K.
 
**375L DONE (gap_impact prompt-contract audit; `21a10ad`, KEYLESS code-inspection — code facts, not n-dependent).
FINDING A: `gap_impact` is a CLEAN consequence field. The "sign conflict" was a VOCABULARY COLLISION, not a
schema category error and NOT a two-axis contradiction.** Decisive evidence (prompt text, not inference): the
5e system prompt EMBEDS LP-05 as a worked example and teaches that an ABSENT provision = FAVORABLE; it carries
explicit anti-sign rules ("absence ≠ adverse by default," "do not give generic lease-risk answers"). A prompt
asking for sign could not contain that example. Confirmed: 0 production consumers read gap_impact as sign (12
call sites across app.js / _step371 / _step372 all gate on it as consequence polarity); the 375K "conflict"
lived ENTIRELY in the analytical harness comparing two stage outputs — no production code ever compares
gap_impact against Stage 7 directionality. gap_impact (polarity) and materiality (severity) are distinct,
jointly-used consequence dimensions; favorable overrides materiality (favorable+high → green).
 
**375L CONSEQUENCE FOR COV — the fix SHRINKS, and two corrections to Code's framing:**
- There is NO second sign axis to arbitrate. COV does NOT need `sign_source` / `sign_value` / `sign_conflict` /
  `axis_conflict` machinery — that was solving a non-problem. DROPPED. The 5e provenance COV needs is
  `use_consequence_source` (assessed / defaulted_floor / not_eligible / absent) — the 375I silent-floor fix on
  the renamed field. That stays.
- **The VALUE rename is the actual fix, not "optional polish" (flipping Code's optional/required framing).**
  Renaming the field to `use_consequence` while keeping values favorable/adverse leaves the collision vector in
  place — the VALUES are what made it look like sign, not the field name. 375K's phantom conflict was built on
  comparing `favorable` vs `adverse` across stages. Values MUST go to `{beneficial, harmful, neutral,
  context_dependent}` or the next cross-stage audit re-creates the phantom. Field-rename alone is cosmetic;
  value-rename is the substance.
- Fix scope: rename gap_impact→use_consequence + revalue, in lease_use_impact.py (field def + prompt return
  instruction + merge logic), 8 app.js consumers, _step371_variance.py, _step372_decomp.py. This is the FIRST
  step in the 375I–L chain that changes RUNNING behavior (production app.js Mode-C routing/coloring) — so it is
  the first that needs care not to break live behavior, and the first that may warrant a deploy. Treat as a
  build step, not a read-only diagnostic.
**STILL OPEN after 375L (do NOT let "it's just vocabulary" absorb this): LP-20 CONSEQUENCE jitter.** 375L
explains LP-05 completely. It does NOT explain why LP-20's consequence wobbled (neutral×8 / adverse×1 /
context_dependent×1) across 10 identical replays. That is now a within-stage CONSEQUENCE-stability question
(not a sign question), still real, still unmeasured — it belongs to the 375I stability finding: 5e consequence
is sparse (8/32), genuinely-assessed-where-present, and jittery at the favorable/neutral boundary on ≥1 LP.
The rename does not touch it.
 
**375J VERDICT: the wobble is cosmetic under Policy B; the SPARSITY is load-bearing.** This inverts the redesign
priority: **375E-COV (widen the 8/32 gate + add `materiality_source`) now GATES 375E-DIR**, not the reverse.
Shipping source-strict routing (C) before widening 5e would crash the lawyer-facing Risk count from 26→7 —
its own instability, opposite direction. So the doctrine "materiality anchors Risk" is sound, but materiality
doesn't yet COVER enough of the lease to be the anchor; coverage is the blocker, not the wobble.
 
**NEXT MOVE (queue — 375M SHIPPED `a939b01`; STOP POINT, then 375H-diagnostic BEFORE COV):**
 
> **CLEAN STOPPING SEAM (2026-06-05).** 375I–M is a complete diagnostic arc + one behavior-preserving ship.
> Do NOT spec 375E-COV cold off this — COV is the first step that changes HEADLINE behavior (what happens to
> the 18 unassessed directional Risks), and its gate-widening shape DEPENDS on a 375H characterization not yet
> done. Next session order:
> 1. **Close 375M write-path** on the next keyed run: confirm Stage 5e writes `use_consequence` and legacy
>    `gap_impact` is absent in fresh artifacts. (Monitoring note, not a blocker.)
>    → PREFLIGHT DONE 2026-06-05: NO fresh post-375M run exists (newest on disk is the pre-deploy frozen
>    52adbf). So the write-path check is OWED on the next real keyed run; 375N reads 52adbf through the
>    normalizer (legacy gap_impact, correct) and is NOT the write-path test.
> 2. **375N/375O DONE; precheck DONE; COV REFRAMED + SPLIT; 375E-COV-A SPECCED**
>    (build_log/375E-COV-A_chat_instruction.md). **THE COV REFRAME (settled): COV is NOT LP-eligibility
>    widening — it is FINDING-LEVEL consequence-provenance.** The 50%-threshold was a coverage-completeness
>    heuristic impersonating a consequence-need gate (same axis-impersonation as gap_impact). Real invariant:
>    a finding that requires action routing needs assessed consequence; entry attaches to the FINDING.
>    - 375O proved: F(current-Risk)=B=G-cand=G-ver=H=26 on this lease — current-Risk entry is CIRCULAR
>      (Risk status was caused by missing consequence assessment). G-cand=G-ver here (delta 0) but G-cand is
>      the architectural choice (G-ver re-imports the Pass-2 vote-wobble into eligibility). A-rail (threshold)
>      does ZERO marginal work (A33 ⊆ G-cand); FLAGGED-NOT-BUILT (Tzvi call), re-add at lease #2 if a real
>      high-gap NON-directional LP appears; NOT a Pass-1 recall backstop.
>    - PRECHECK (Chat, from 375J_results.json): every directional finding is 1:1 with its LP (0 LPs carry >1
>      directional finding) → build finding-scoped output PLAINLY, no LP-reuse-guard machinery, reuse-safety
>      DEFERRED. The many-to-many reuse problem is entirely in the COMPOUND layer (LP-01 ∈ Dir-01 + CRX-02 +
>      CRX-05 + CRX-06, four consequence contexts) → per-LP 5e STRUCTURALLY cannot serve compound findings →
>      `compound_consequence_source: not_assessed` is forced, not bookkeeping.
>    - **COV SPLIT A/B (Tzvi call):** COV-A = populate/record only (G-cand finding-scoped 5e + use_consequence_
>      source/materiality_source + CRX not_assessed), **NO routing change**, falsifiable 0-drift gate like 375M;
>      COV-B = lawyer-facing landing (Risk/Improvement/Needs-Review-subtype/CRX surfacing) decided after A
>      proves provenance generates without breaking routing. COV-A is KEYED — its run ALSO closes the owed
>      375M write-path check AND answers the open 375I gate-vs-yield question (does 5e actually assess the 18
>      newly-admitted LPs or abstain). Deploy-gated.
> 3. (was: decide COV widening policy) — SUPERSEDED by the reframe. The remaining Tzvi call is COV-B's
>    landing-bucket design, made with COV-A's yield numbers in hand.
>
> **COV-A KEYED RUN DONE (lease_review_20260605_174504_19f9a7, committed 771f1ef NOT pushed). VERDICT: HOLD.**
> Mechanically COV-A works: use_consequence written, gap_impact gone (375M write-path CLOSED), provenance on
> all 25 directional + 7 CRX (not_assessed), CRX not falsely assessed. **YIELD (the open 375I answer) is
> STRONGLY POSITIVE: 14/18 newly-admitted decisive, 0 abstain; thin-gap LP-01/11/24/25 ALL 4/4 DECISIVE** —
> G-cand finding-trigger works even on near-complete provisions; consequence IS assessable from finding-level
> context; A-rail likely not needed for that class. BUT two HOLD flags, re-attributed:
>   - **Criterion-4 "routing drift" = CONFOUNDED, demote.** It compared the fresh run vs frozen 52adbf (two
>     independent runs); the severity flips (Dir-03, CRX-01/03/04/06 HIGH<->MEDIUM) are the KNOWN 375-R Stage-7
>     synthesis instability, NOT COV-A. Keyless structural check already proved COV-A can't move routing. Do
>     NOT "fix" criterion 4 — it measures run-to-run synthesis wobble.
>   - **Criterion-F "LP-05 flipped beneficial->harmful" = NOT clean.** The candidate REGENERATED (Pass-1
>     variance): frozen Dir-05 = absence of permitted-use restriction (beneficial); fresh Dir-05 = no
>     co-tenancy protections (different question). LP-05 is no longer the same semantic test case.
>   - **THE REAL CONCERN — consequence-INDEPENDENCE.** Distribution = 24 harmful / 1 neutral / 0 beneficial
>     across 25 directionals (frozen baseline had a beneficial AND a neutral). Suspected: COV-A's
>     finding-scoped 5e prompt hands over Stage-7 adverse framing ("tenant_unprotected", "no relief", "risk")
>     and 5e RATIFIES it instead of independently assessing — vote-count-as-severity's cousin
>     (Stage-7-framing -> harmful). If true, COV-A converts every adverse finding to harmful/material,
>     defeating sign/consequence separation. GATES PUSH.
> **→ 375E-COV-A1 SPECCED (build_log/375E-COV-A1_chat_instruction.md): small keyed prompt-bias panel** — 4
> findings (Dir-05 changed / Dir-12 the lone neutral / Dir-15 LP-20 wobbler / a thin-gap harmful) x 3 prompt
> variants (A current / B direction-redacted / C explicit-independence). If B/C yield neutral/beneficial where
> A is harmful -> contamination confirmed -> fix COV-A prompt before push. If all stay harmful -> genuine,
> push defensible. If chaotic -> consequence axis unstable, COV-B can't route single-sample. ~36 calls, Tzvi
> runs. COV-A push HELD until A1 resolves.
>
> **375E-COV-A1 RUN DONE (keyed, after a key-load fix; build_log/375E-COV-A1_results.md +
> _raw_results.json). VERDICT: CONTAMINATION CONFIRMED — cleanest possible signature.** (First run failed
> all-`no_evaluators`: standalone harness didn't inherit keys; FIXED by load_dotenv of the keys .env — see
> Key working notes. Re-run: all 3 evaluators 3/3 every cell.)
>   - **LP-11 = the smoking gun, UNANIMOUS.** Variant A (current prompt, adverse title handed over): all 3
>     evaluators -> harmful/high. Variant B (direction-redacted, clause facts only): all 3 INDEPENDENTLY ->
>     **beneficial** (3-0, merged beneficial/medium). Same clause/models/run; the ONLY change is whether the
>     adverse title was passed. The framing INVERTED the sign on a tenant-beneficial absence (missing
>     rent-acceleration + missing landlord cure-right = less landlord remedy = good for tenant; the 374Z
>     polarity insight). Reasoning under B verbatim-gist: "absence of rent acceleration + third-party cure
>     rights limits landlord remedies, reducing tenant exposure."
>   - **LP-15 (the lone neutral) confirms bias was live in the real run.** A: harmful (2-1 assert_weak). B:
>     neutral 3-0. Even the finding that survived as neutral was being pushed toward harmful by framing.
>   - LP-20 (wobbler): A/B harmful, C neutral/context_dependent — genuine instability, discount. LP-05:
>     A neutral / B harmful / C neutral — noisier; contamination is NOT uniform, bites hardest where the
>     adverse title is most vivid (LP-11/LP-15), consistent with framing-bias not a blanket harm-stamp.
>   - **DIAGNOSIS LOCKED:** COV-A's finding-scoped 5e prompt hands 5e the adverse title + tenant_unprotected
>     direction as a leading frame; 5e RATIFIES it. The 24-harmful monochrome distribution is substantially
>     prompt-driven, not lease-driven. vote-count-as-severity's cousin, confirmed empirically.
>   - **THE FIX IS PROVEN, not hypothesized: variant B IS the fix.** Feed 5e CLAUSE FACTS + use profile;
>     store stage7_direction as provenance only; do NOT pass adverse title/direction as a leading frame.
>     Under B, LP-11 recovers to (correct) beneficial. Stage 7 keeps sign; 5e assesses consequence
>     independently — the separation this whole arc protects.
> **→ 375E-COV-A2 = the prompt fix (spec next). Real build (changes the 5e finding-scoped prompt) → gets
> 0-drift discipline + keyed re-validation; must NOT be bundled with anything else. COV-A push (771f1ef)
> STAYS HELD until A2 fix + re-validation.** After A2: re-measure consequence distribution (how many of the
> 24 harmful flip to neutral/beneficial) — that CORRECTED distribution, not the contaminated one, is what
> COV-B routing must be designed against. COV-B routing CANNOT be designed off the 19f9a7 numbers.
>
> **375E-COV-A2 SHIPPED (commit fc8d3dc, NOT pushed) + KEYED RE-VALIDATED (run
> lease_review_20260605_195225_34f3b9). CONSEQUENCE FIX = CONFIRMED SUCCESS; ONE NEW ANOMALY GATES PUSH.**
> The prompt fix (variant-B shape: strip Stage-7 adverse title/direction from the 5e consequence prompt;
> feed clause facts + use profile; store stage7_direction as provenance only) WORKED:
>   - **Distribution de-monochromed:** 28 directionals = 15 harmful / 6 context_dependent / 5 neutral /
>     3 beneficial (vs contaminated 19f9a7 = 24 harmful / 1 neutral / 0 beneficial). Real spread, 3 genuine
>     beneficial (LP-26/27/29). This is what an INDEPENDENT consequence layer produces.
>   - **LP-11 canonical regression PASSED:** context_dependent/medium, NOT harmful/high. Contamination
>     signature gone. (Isolated A1 variant-B got beneficial; full-pipeline context lands context_dependent —
>     still a clean pass on the "NOT harmful/high" assertion.)
>   - Criteria 1/2/3/6 PASS (write-path closed; fields on all 28 dir + 5 CRX; CRX not_assessed). Criterion 5
>     PASS at 12/18 decisive (more findings now honestly context_dependent instead of false-harmful). NOTE a
>     validator inconsistency: gate text says >=14 but logic passed at 12 — fix the validator gate/logic
>     mismatch, not a blocker.
>   - LP-05 consequence still harmful (criterion F) = NOT clean — candidate regenerated AGAIN (Pass-1
>     variance). LP-05 retired as fixture; LP-11 is the canonical regression case now.
> **⚠ NEW ANOMALY — GATES PUSH, must be explained before COV-A+A2 deploy:** criterion 4 this run is NOT the
> old severity-wobble confound. EVERY directional finding flipped `directionality` tenant_unprotected ->
> **landlord_unprotected** (uniform across all 28) plus severity HIGH->LOW/MEDIUM across the board. Uniform =
> NOT random run-to-run noise. THE TELL: within LP-05, `directionality`=landlord_unprotected BUT the
> preserved `stage7_direction`=tenant_unprotected — they DISAGREE inside the same finding. So something
> recomputed/overwrote the routing `directionality` field but NOT the stored provenance. A2 was supposed to be
> consequence-prompt-input ONLY and must not have touched Stage-7 directionality. Either (a) a side effect in
> the COV-A/A2 code path writes directionality, or (b) Stage 7 produced different directionality this run. The
> uniform tenant->landlord flip + the provenance mismatch point at (a). MUST be traced before push. The
> CONSEQUENCE fix is DONE and GOOD; this is a SEPARATE directionality-field question opened by the same run.
> **→ 375E-COV-A2-DIR-Q (spec next, read-only): trace why `directionality` flipped tenant->landlord on all 28
> directionals and why it disagrees with stage7_direction. Determine if COV-A/A2 code writes it or it's fresh
> Stage-7 output. COV-A (771f1ef) + A2 (fc8d3dc) push STAYS HELD until resolved.**
>
> **375E-COV-A2-DIR-Q DONE (read-only trace; build_log/375E-COV-A2-DIR-Q_results.md). VERDICT: (b) STAGE 7
> NONDETERMINISM — NOT A2. Plus TWO findings the trace surfaced.**
>   - **(a) CLEARED:** COV-A/A2 writes `directionality` NOWHERE (only a comment at lease_finding_consequence.py
>     492-493). A2 commit touched only lease_finding_consequence.py. _normalize_directionality maps LP-27 only.
>   - **(c) CLEARED:** validator reads `directionality` under the same key in fresh + baseline; the drift is a
>     real value change, criterion 4 correctly confounded cross-run.
>   - **(b) CONFIRMED ROOT CAUSE:** `directionality` derives from Pass-2 LLM `exposed_party` via
>     `best = first confirming role` (lease_synthesis.py ~1941). 19f9a7: all 3 roles confirmed,
>     exposed_party=tenant -> all tenant_unprotected. 34f3b9: roles A+B said no_mismatch/landlord+bilateral,
>     ONLY role C (grok) confirmed and said landlord -> all 28 landlord_unprotected. Same models, byte-identical
>     lease. Uniform because C alone set the sign for every finding.
> **A2 CONSEQUENCE FIX IS SAFE TO PUSH** (the directionality flip is pre-existing Stage-7 nondeterminism, not
> A2). BUT two things the trace exposed, in priority:
>   - **🔴 COV-A DEFECT (BLOCKS push, must fix first): `stage7_direction` is HARDCODED** to
>     "tenant_unprotected" (lease_finding_consequence.py:524, 608), unconditionally, on every directional
>     finding — it does NOT read Stage 7's actual directionality. This run: 27/28 findings have
>     stage7_direction=tenant_unprotected while the REAL Stage-7 directionality=landlord_unprotected. The
>     provenance field we added to RECORD Stage 7's sign DOES NOT record it — it stamps a constant that was
>     right once. SAME stamp-not-assessment pattern as everything else this session, shipped inside COV-A.
>     A provenance field that lies is worse than none. FIX before COV-A+A2 push: read the actual finding
>     `directionality` into `stage7_direction` instead of hardcoding. Small fix, same module, then re-validate.
>   - **🔴 NEW LOAD-BEARING FINDING for 375E-DIR: the directional SIGN is nondeterministic, not just severity.**
>     375-R found Pass-2 SEVERITY swings run-to-run; this shows the SIGN ITSELF swings — all 28 findings flipped
>     tenant<->landlord on identical input because `best = first-confirming-role` lets WHICHEVER single
>     evaluator confirms decide the exposed party for the whole report. That is the SAME category error as
>     vote-as-severity (a verification artifact — who confirmed — silently setting a substantive label — which
>     party is exposed). 375E-DIR's "Stage 7 owns a STABLE sign" assumption is FALSE; the sign needs the same
>     governance as severity. Record under 375E-DIR.
> **→ NEXT: 375E-COV-A2b (tiny fix) = stop hardcoding stage7_direction; read actual directionality + add
> stage7_direction_source ("stage7"/"absent", NO fallback to tenant_unprotected). VALIDATION IS KEYLESS
> (GPT): a keyed re-run reopens Stage-7 sign nondeterminism and muddies it; instead apply A2b to the existing
> 34f3b9 artifact and check the INTERNAL invariant stage7_direction==directionality per finding (NO cross-run
> compare — cursed). Then push COV-A+A2+A2b together. The sign-nondeterminism finding feeds 375E-DIR (no fix
> now).**
>
> **375E-COV-A2b DONE (commit 8de0d74, NOT pushed). Keyless-validated. PUSH GATE NOW OPEN.** Code fixed
> THREE hardcoded sites (lines 523, 536, 608 — not two; I'd missed 536), all in the same `f` (Stage-7 finding
> dict) context where `f.get("directionality")` is the correct accessor. Each now reads the actual
> directionality and sets stage7_direction_source="stage7"/"absent" (no fallback). Keyless validation on the
> 34f3b9 artifact: **stage7_direction == directionality on 28/28 findings (0 mismatches)**; all 28 have
> non-None directionality so all source="stage7"; CRX 5/5 still not_assessed; consequence/materiality/routing
> untouched. (Note: actual 34f3b9 distribution is 16/5/4/3, not the 15/6/5/3 I cited earlier from the
> validator table — A2b doesn't touch consequence so the small recount difference is just my earlier
> miscount, not a change.) NOT touched: A2, lease_synthesis.py, cam/core/, routing, lease_use_impact.py.
> **ALL FIVE PUSH CONDITIONS MET:** (1) read-not-hardcoded ✓ (2) stage7_direction==directionality 28/28 ✓
> (3) consequence decontaminated ✓ (4) no COV-B routing ✓ (5) CRX not_assessed ✓.
> **→ NEXT: push COV-A (771f1ef) + A2 (fc8d3dc) + A2b (8de0d74) TOGETHER (Tzvi's call; push to main triggers
> Railway redeploy ~60s). THEN COV-B routing design against the corrected distribution. Sign-nondeterminism
> still banked for 375E-DIR.**
> 4. **Spec 375E-COV**: widen gate + add `use_consequence_source` + route unassessed consequence VISIBLY.
> 5. **Then** 375E-DIR production routing.
 
**TWO COV DESIGN CALLS HELD FOR TZVI (do not pre-decide):**
- **Where do the 18 unassessed directional findings land?** They must NOT silently vanish from Risk (that's
  the opposite failure: more honest internally, worse product externally). Do NOT add a 5th top-level bucket —
  keep the four action buckets. Preliminary rule: directional-adverse + assessed high/medium consequence →
  Risk; + assessed low/beneficial → Improvement / favorable-position note; + consequence_source
  not_assessed/defaulted_floor → **Needs Review, subtype "consequence not assessed."** Preserves visibility
  without pretending default-floor materiality was real.
- **How to widen the gate** — see step 3 above (gated on the 375H diagnostic).
0b. **375M DEPLOYED (`a939b01` on main, Railway redeployed): gap_impact→use_consequence rename/revalue LIVE.**
   Behavior-preserving refactor proven 0-drift (375J 32/32 + 375K 130/130 per-finding slots byte-identical
   through the normalizer). Field + values both changed (favorable→beneficial, adverse→harmful); single
   canonical field on write (no dual-write); normalize-on-read for old artifacts. LP-05 vocabulary collision
   eliminated. **POST-DEPLOY CHECK STILL OPEN:** inspect the first fresh keyed run's artifact to confirm Stage
   5e writes `use_consequence` {beneficial|harmful|neutral|context_dependent} and `gap_impact` no longer
   appears (V3 was synthetic; write-path validates on first real run). Not a blocker; a monitoring note.
0a. **375L (specced, KEYLESS): gap_impact prompt-contract audit** (build_log/375L_chat_instruction.md). Reads
   the actual 5e prompt builder + schema + every gap_impact consumer to decide the fix shape: Finding A clean
   consequence / B overloaded hybrid / C consequence-prompt-but-misread-downstream / D ambiguous contract.
   Picks demote vs rename vs SPLIT from the real contract, not from memory. Keeps prompt-SAYS vs
   outputs-CONTAIN separate (LP-20's "adverse" emission proves the MODEL produced sign, not that the PROMPT
   asked for it — that distinction picks B vs C). COV cannot define `sign_source`/consequence fields cleanly
   until 375L lands.
0. **375K (specced, KEYLESS): direction-axis reconciliation** (build_log/375K_chat_instruction.md). Goes
   BEFORE COV, because COV widens assessment and LP-05 proves SIGN can disagree across stages — widening
   before defining "direction" propagates the contradiction. Tests candidate sign-hierarchy rules (A
   Stage7-primary / B 5e-primary / C conflict-abstention; D/E diagnostic baselines) over frozen artifacts,
   NO model calls. Does NOT pre-pick a winner; conflict→Needs Review is the diagnostic-safe interim; the
   permanent hierarchy is decided from the CAUSE of conflicts + whether 5e's own sign is stable (375I Q3
   recorded 5e gap_impact as direction-unstable on LP-20, so 5e is not assumed trustworthy as the sign axis).
1. **375E-COV** — widen `_should_assess` past the 8/32 gate + add `use_consequence_source`
   {assessed|defaulted_floor|not_eligible|absent} on the RENAMED field (375M lands first). NO `sign_conflict` /
   NO axis machinery — 375L proved there is no second sign axis; sign stays Stage 7, 5e carries
   use_consequence + materiality. (`materiality_source` provenance still needed too.) PARTLY keyless. The
   load-bearing coverage fix. NEXT ONLY AFTER 375M.
2. **375E-DIR** — routing formula, consumes COV fields + the 375K sign rule. Candidate policy B+C
   (high+medium collapse + source-strict), provisional-on-n=1. SPEC may precede COV; production-enable must NOT.
3. **375H-C** keyed fixture matrix → direction-sensitive schema repair. DEPLOYMENT TRAP unchanged: validated
   375H findings must NOT enter lawyer-facing Risk until 375E-DIR fixes routing.
Keyed 5e stabilization is OFF the queue unless lease #2 shows full (low↔high) materiality swings.
**EXTERNAL-USE PAUSE IN FORCE:** directional Risk / Priority totals are NOT lawyer/Joshua/demo
ready — they move with evaluator-support wobble and with which candidates happened to generate.
The pause lifts only when BOTH candidate recall AND directional routing no longer depend on
evaluator-support collapse.
 
*(Full detail: search "## 375" sections below. Everything from here to those sections is the
closed 372 chain — history, not frontier.)*
 
---
 
## The 372 chain — ALL VALIDATED LIVE (`fd002c1`)
 
Confirmed across two live runs: `...170305` (during the Grok outage — proved graceful
degradation + honest recording) and `...181402` (clean, all three real families).
 
- **372a — evaluator identity auditability** ✅ VALIDATED LIVE. Per-verdict `actual_model` /
  `actual_label` / `is_fallback`; `lp_meta.fallback_used`. Proved its worth in the Grok
  outage: every Gemini substitution was honestly recorded as `gemini-2.5-pro/is_fallback=True`
  instead of mislabeled "Grok 4.3." Metadata-only; verdicts unchanged on clean runs.
- **372c — budget prevention + observability** ✅ VALIDATED LIVE. The win: **LP-22/B completes
  on gpt-5.5 (`is_fallback=False`, `split=True, nsub=2`)** — it fell back to gpt-5.4 every
  prior run. LP-11 → 3 batches, completes on primary, A `truncated=False`. Real adapter usage:
  B util 20–49%, A 16–26% on the clean run. Per-mechanism: A budget raise (600/elem+1000),
  B prompt split ≤8 elem (gpt-5.x only, shape-preserving), Stage 7 Pass-1 12000 / compound 8000.
  `fallback_reason` correctly classified C's outage as `api_error` (403), distinct from
  reasoning_exhaustion / truncation.
- **372b — fallback visibility in Stages 3/5d/5e** ✅ VALIDATED LIVE. During the outage
  `use_aware_governance (5d).fallback_used=True` correctly named `gemini-2.5-pro`; on the clean
  run both flags `False` (correct — nothing fell back). `use_impact_governance (5e)` present.
  Also corrected Stage 3's pre-existing POOL-ONLY `fallback_used` (missed own-chain fallbacks)
  via actual-model-vs-primary comparison.
- **372D2-fix — surface disagreement citations** ✅ VALIDATED LIVE. **All disputed elements
  carry `disagreement_citations`** (21/21 then 18/18; e.g. LP-14 rent_abatement → Section 24.1,
  LP-20 radius_restriction → Section 24.14, LP-22 SNDA → S19.2/S19.3) — merged citation stays
  None, grounding surfaced as "Contested · <section>" in Key Issues + Evidence. coverage_state
  byte-identical.
**Chain status: CLOSED.** Identity auditable, failures prevented, pressure observable,
cross-stage fallbacks visible, contested-but-grounded findings surfaced. Next steps are
characterization, not fixes.
 
---
 
## ✅ Grok-credits incident (2026-06-01) — RESOLVED + confirmed live
 
During the afternoon validation runs (`143142`, `170305`), **every Eval-C (grok-4.3) call
failed with HTTP 403 "team has used all available credits or reached its monthly spending
limit."** Consequences:
- C fell back to `gemini-2.5-pro` via shared pool on nearly every LP in Stage 305 / 5d, and
  failed *entirely* in 5e (no pool path there) and Stage 7.
- This had been happening on the prior runs too — the "C unstable / C→Gemini" pattern was THIS,
  not Grok model instability. Credits were already dead.
- **Therefore: all C-slot data in `143142`, `170305` (and likely both 372STAB runs) reflects
  Gemini standing in for Grok** — contaminated for C-characterization; discard.
- 372a/b/c made this **visible and safe** rather than silent: graceful degradation (mostly 3/3
  or 2/3 via pool), every substitution honestly recorded, governance flags fired.
- **Resolution: xAI account funded + auto-refill enabled.** CONFIRMED live in `...181402` and
  again in `...030920`: every Eval-C call succeeded on grok-4.3 on primary — 0 fallbacks.
---
 
## ⭐ Clean baseline run: `lease_review_20260601_181402_2d1700`
 
First uncontaminated full run with all three real model families (Claude / GPT / Grok) on
every LP, on validated `fd002c1`. **Use THIS as the canonical C-baseline.**
- Coverage: 23 partial, 3 review_needed, 2 missing, 1 covered, 3 N/A. Stage 7: 33 findings,
  5 compound after dedup, 28 directional.
- Observations (non-blocking): Stage-7 Eval-A (Claude) is now the long pole (Pass-1 188s,
  Pass-2 144s) — note for the deferred Stage-7 observability follow-up. Email still broken.
---
 
## ⭐ Second clean run + stability diff: `lease_review_20260602_030920_d0e19e` vs `181402`
 
`build_log/372DIFF_stability.py` (reusable; auto-newest vs `181402`). First clean-vs-clean
matched pair with **real grok-4.3 in BOTH runs** (372STAB's C column was likely Gemini). Result:
 
- **Identical flagged LP count (28) and identical Stage 7 finding count (33).**
- **0 substantive present↔absent element crossings** — this is the metric that matters. No clause
  oscillated between "present" and "missing." The post-372 fear (clause-existence churn on
  identical input) did NOT occur.
- 15/197 elements (7.6%) changed: 3 EP/IP subclass jitter (consequence-free) + 12 disputed/unclear
  transitions AROUND already-contested elements. None crossed the present/absent line.
- 5 LPs moved `partial → review_needed` (LP-16/19/22/28/32), each driven by an element entering
  `disputed` and triggering dispute-governance escalation.
**These are ESCALATION-boundary flips, NOT reassurance-boundary flips — and the distinction
matters.** `partial → review_needed` = "already flagged, now escalated" (the lawyer was already
going to look). That is fundamentally lower-risk than `addressed → risk/review_needed` =
"nothing to do" becoming "you must look." All 5 flips were the low-risk escalation kind; 0 were
the high-risk reassurance kind. **Do NOT lump these under one "Tier-1" label** — the diff tool's
old bucket proxy did, but escalation flips and reassurance flips are different lawyer experiences.
 
**Conclusion:** coverage assessment is STABLE; observed variance occurred primarily at the
disagreement-sensitive escalation boundary. The governance layer reacts differently when the
evaluator-disagreement pattern shifts slightly run-to-run — which is the system behaving as
designed, not coverage instability. n=2, ONE contract (Atlas Meridian), real Grok both —
DIRECTIONAL, not a platform stability rate.
 
> **SCOPE CAVEAT (added 2026-06-04 — do not misread this section):** "STABLE" here is about the
> COVERAGE layer (element present↔absent) on this n=2 pair. It is NOT a claim about the
> DIRECTIONAL layer. The later 375 investigation found the DIRECTIONAL path (Stage 7 Pass-2
> severity + candidate generation) IS unstable on identical input (Risk count swung 21→7 across
> 5 frozen replays; Pass-1 sometimes drops candidates). Coverage-stable and directional-unstable
> are BOTH true — different layers. See the "## 375" sections.
 
**Future governance question (RECORD, do not act):** is the `dispute_signal → review_needed`
promotion threshold correctly tuned? A single disputed critical element currently promotes the
LP. Candidates to evaluate later: require multiple disputed critical elements, or high-confidence
dispute, or critical-dispute + material consequence. This is governance TUNING, not a bug — and
tuning should only happen once current behavior is fully understood (we are not there yet).
 
---
 
## Current versions
 
- git SHA: `b1159a0` (375H A+B; session shipped 374Z `609af43` → 375C `b1ce16f` → 375G `b053c80`
  → 375H `b1159a0`). NOTE: the older `fd002c1` / `v447` below referred to the 372-era baseline —
  superseded.
- app.js `v466` / style.css `v400` (375G Client Impact block).
- Models: extractor gemini-3.1-pro-preview; Eval-A claude-sonnet-4-6; Eval-B gpt-5.5 (Stage
  305) / gpt-5.4 (Stage 7); Eval-C grok-4.3 (pool fallback → gemini-2.5-pro). B is temp-1-only
  by model constraint (372V1).
---
 
## Per-evaluator disagreement (clean `181402`, DIRECTIONAL, n=1 contract)
 
`build_log/372CV_disagreement.py` + `372CV_why.py`. 36/197 elements (18.3%) had raw-verdict
disagreement — matches 372STAB's ~17%. Lone-dissenter counts **A:15, B:13, C:8** — i.e. Grok
dissents LEAST often, **inverting** the prior "C is the noisy one" hypothesis (which was a
Gemini-contamination artifact). Disagreement KIND: presence_absence_cross 18, unclear_split 11,
subclass_jitter_only ONLY 7 — so disagreements are mostly SUBSTANTIVE, not EP/IP jitter; the
**EP/IP-collapse idea is largely moot** (7/36). Pattern: when C is lone dissenter it almost
always says `missing` while A/B say present — **C is the strict/literalist reader**; A/B more
readily credit implicitly_present / covered_by_default_law / covered_in_other_LP (inferential
coverage). `372CV_why.py` dump confirmed nobody hallucinates a clause in/out: in every crossing
all three read the SAME text and split on whether it SATISFIES the rubric element (cleanest:
LP-10, A and B both cite Section 8.4 and reach opposite present/missing verdicts). This is the
interpretive-threshold fork the multi-evaluator design + verdict-distance ladder + dispute_signal
+ 372D2 citation surfacing exist to CAPTURE — working as designed. CAVEAT: "C is strict" is n=1
directional and "strict" ≠ "correct" — whose threshold matches professional practice is a LAWYER
question (put LP-10 / LP-16 / LP-02 before a CRE attorney).
---
 
## Boundary-fragile / Stage-7 selection boundary (investigated 2026-06-01 — DESIGN PARKED, feature INERT here)
 
**The architectural insight (correct):** Stage 7 does not merely inherit Stage 305's merged
*conclusion* — it inherits Stage 305's *selection boundary*. A clean-classified LP is excluded
from the compound prompt entirely, so no amount of independent re-reasoning inside Stage 7 can
surface a compound interaction involving it. The exclusion gate, not interpretation-flattening,
is the first-order pressure point. (Matrix-flattening of contested elements is a real but
second-order leak.)
 
**The agreed design (you + GPT + Claude), IF the problem proves real:** add a third LP category
— `boundary_proximity` (NOT `boundary_unstable`; honest naming — this is single-run PREDICTED
fragility, not OBSERVED cross-run instability, which production does not yet have). Computed in
the **coverage layer** (one source of truth — Stage 7, Contract View, Evidence, Audit all read
the same field; avoid "two truths"). Fed into Stage 7 as a **conditional contributor**, told
explicitly "not an established defect." Rendered as **Conditional Compound Risk** (depends on an
unstable underlying LP reading) separately from **Confirmed Compound Risk**. Conditional findings
go to Review Needed / Conditional, NEVER into confirmed Risk counts. Split **Type A
(disputed-because-present: clause cited, interpretation differs)** vs **Type B
(disputed-because-silent: no citation, absence inference)** — B carries weaker epistemic weight
and deserves a stricter promotion bar. Do NOT explode Stage 7 into alternate-universe synthesis;
do NOT force Stage 305 to stabilize upstream (that launders interpretive uncertainty into fake
stability — the exact 372 anti-pattern).
 
**Measure-first result — `build_log/372BU_prevalence.py` on `181402`: 0 boundary-fragile clean LPs.**
Stage 7 already invites 28/32 LPs; only LP-12/13/23/31 are excluded, and all four are clean at
the element level (0 disputed, 0 present/absent crossings, 0 unclear-splits). So on this contract
the exclusion boundary traps nothing. Note this is close to a worst case for *detecting* the
problem: a heavily-flagged contract (28/32) has almost no clean-LP population for the feature to
bite on. **Conclusion: feature is architecturally valid but OPERATIONALLY INERT on Atlas Meridian
(n=1). Do NOT spec.** The honest claim is "0 fragile clean LPs here," NOT "feature unnecessary."
 
**Revisit trigger:** re-run `372BU_prevalence.py` on (a) the first LIGHTLY-flagged contract (large
clean-LP population) or (b) matched runs that yield OBSERVED cross-run instability. If it returns
"fragile + not-found + plausibly compounds," that is the proof case → route design to GPT → spec.
Likely **patent-relevant** when built (instability metadata propagated as conditional candidate
status; confirmed vs conditional compound rendering) — ties to dispute_signal / deliberate
non-deliberation / temporal-governance themes; wants a supplement.
 
---
 
## Evaluator behavior (established this investigation — DIRECTIONAL, n=1 contract)
 
- **A (Claude Sonnet, temp 0): ~97%** — near-deterministic, wobbles only on genuinely
  ambiguous text (signal).
- **B (gpt-5.x, temp-1-only by constraint): ~78–82%** — structurally stochastic, not a bug.
  Reasoning-exhausts on long prompts — RESOLVED by 372c split (LP-22/LP-11 now complete on primary).
- **C (Grok, temp 0): the strict/literalist reader.** On clean `181402` C is the LEAST-frequent
  lone dissenter (8 vs A:15, B:13); its dissents are overwhelmingly strict `missing` calls,
  mostly Type B (silence-inference). The earlier "C noisy/jitter" read was Gemini contamination.
  C-validity (is the strictness stable AND correct) is OPEN — needs a lawyer; the `030920` diff
  showed C's substantive calls did NOT flip present↔absent (encouraging on the stability half).
- **Temperature is NOT the driver** (C strict at temp 0). Variance is multi-causal.
- **Ensemble value (372STAB, Atlas Meridian):** "primarily consensus confirmation, tie-
  breaking, and dispute detection rather than independent risk discovery." 82% unanimous.
  Do NOT restate as "tie-breaking only" (universal) or "independent discovery" (not shown).
---
 
## 372STAB stability characterization (2026-06-01, n=2, DIRECTIONAL not a platform property)
 
Two byte-identical-input runs: 29/32 LPs identical coverage_state, **0 Tier-1 flips**, 11/197
elements differ — all genuine model instability, 0 fallback substitution (validated 372a).
CAVEAT: these two runs likely predate the Grok funding — their C column may already have been
Gemini. SUPERSEDED for C-characterization by the clean `181402`/`030920` pair, which has real
Grok in both. NOT established: platform-wide stability rate, multi-contract, patent claims.
 
---
 
## Step 373 — Priority Review triage chip (SHIPPED be4a8eb; one OPEN doctrinal question)
 
UI work resumed (the original goal this session, before the 372 detour). Single Risk bucket needs
within-bucket triage. A UI-field audit (`build_log/UIFIELDS_audit.py` → `UIFIELDS_audit.txt`) killed
the stale March "Severity × Confidence" design: **no per-LP `severity` field, and the old
`governance_signal` enum is GONE** (do not reference it). Real fields: coverage LPs carry
`review_priority_distance_signal.hard_flag` (Stage 5f), `use_impact.materiality` (Stage 5e,
sometimes ABSENT), `lp_confidence` (high/low), `verdict_distance.severity` (none/moderate/severe);
Stage 7 findings carry `severity` (HIGH/MEDIUM) + `evaluator_agreement`.
 
**Shipped design (be4a8eb, app.js v448 / style.css v396):** a single shared `isPriorityReview()`
helper (window.CAM, same single-source pattern as `classifyFindingType()`) used by BOTH Key Issues
and Overview. Coverage → Priority Review iff `hard_flag`; Stage 7 → iff `severity==='HIGH'`.
`⚠ Priority Review` chip + sort-to-top within Risk. Consequence label from `use_impact.materiality`
ONLY — OMITTED when absent (never falls back to plain `materiality` on the card — that would be
semantic fraud: same slot, different meaning). No synthetic severity, no middle tier,
`classifyFindingType()` untouched.
 
**DOCUMENTED EQUIVALENCE (not a severity theory):** "Priority Review" is a UI triage tier meaning
"CAM flags this for first-pass attention." Coverage source = Stage 5f hard_flag (distance ×
consequence); Stage 7 source = severity=HIGH. SAME review tier, DIFFERENT source logic — never
represented as the same underlying computation. (Doctrine-safe: hard_flag is a GATE, not a merged
severity×confidence score; Guardrail #3 preserved.)
 
**Validation on `181402` (tenant):** Risk total 10; Priority Review = 2 coverage (LP-28, LP-32) +
3 Stage 7 HIGH (CRX-01/03/04) = 5, ratio 0.50; 1 card correctly omitted consequence (LP-27);
plain-materiality-as-consequence count = 0 ✅.
 
**⚠ OPEN — the question Code's build surfaced (decide before any bucket-independent chip):**
Stage 5f hard-flagged **7** coverage LPs (02,06,14,16,20,28,32) but only **2** land in the Risk
bucket. The other 5: LP-02/06/16/20 → **Improvement**, LP-14 → **Needs Review**. So the engine's
triage signal and `classifyFindingType()` DISAGREE on 5 of 7. An adverse + severe-disagreement +
hard_flag finding in *Improvement* ("optional upside") is a contradiction in lawyer-action terms.
Three possibilities: **#1 classifier under-routing** (adverse hard_flags should be Risk/Review —
fix is upstream, not a chip); **#2 hard_flag over-firing** (ties to the parked dispute→review
sensitivity question); **#3 legitimate** (favorable hard_flag CAN be an Improvement). Early signal
from the audit: LP-02 & LP-16 are `gap_impact=adverse` + hard_flag + Improvement → smells like #1.
**Check written: `build_log/373CHK_hardflag_bucket.py`** (categorizes the 7 by gap_impact × bucket:
A favorable+Improvement=plausible / B adverse+Improvement=anomaly / C Risk/Review=expected). Run
it before deciding. Code correctly did NOT make the chip bucket-independent — that would advertise
a possible mis-route as "look here first." Current scoped build STAYS as shipped pending the check.
 
### ✅ RESOLVED — it was #1, classifier under-routing. Fixed in 373C (SHA d043e53).
 
**373CHK result:** Category A = 0 (NO favorable hard_flags — #3 dead), Category B = 4 (LP-02/06/16/20,
all adverse/neutral hard_flags wrongly in Improvement), Category C = 3 (LP-14/28/32 correct).
 
**373B (read-only dump of `classifyFindingType()`) PROVED the mechanism:** the classifier routes on
CONSEQUENCE ONLY (`use_impact.materiality` + `partial_class` + `gap_impact`). It NEVER reads
`hard_flag` or `verdict_distance`. Per Q4 the omission is ACCIDENTAL — the materiality tiers have
three defending comments; nothing defends excluding the escalation signal. Stage 5f was built later
and never wired back into bucketing. LP-20 died at the `mat==='not_applicable' → improvement` gate
before severity was even considered, despite its engine reason "review required regardless of vote count."
 
**373C fix (SHA d043e53, app.js v449):** added a promote-only FLOOR as the genuine last step of the
Mode C coverage path — `hard_flag===true` AND consequence-bucket is improvement/addressed → floor to
`review_needed`. Consequence tiers wrapped verbatim in an IIFE (unchanged); floor only raises, never
demotes. Defending comment added. NOT `hard_flag→Risk` (hard_flag = severe disagreement + meaningful
consequence, which earns "must look" = Needs Review, NOT "confirmed problem" = Risk). Orthogonal per
Guardrail #3: consequence = ceiling, hard_flag = floor.
 
**Validation (classifier-replay against `181402` — the authoritative, non-circular check):**
Improvement 19→15 (−4), Needs Review 3→7 (+4), Risk 5→5 unchanged, Addressed 2→2 unchanged. Exactly
LP-02/06/16/20 moved Improvement→Needs Review; no other finding changed bucket; 373 chip count
unchanged at 5. (Note: the 373CHK "Category B=0" line is partly circular — the script's hardcoded
CODE_BUCKET map was synced to the post-fix buckets since it can't run the JS. The trustworthy proof
is the classifier-replay bucket movement, which is a real computation against real data.)
 
**Doctrinal question RESOLVED:** Priority Review stays WITHIN-bucket ("among Risks, start here"). The
cross-bucket cases were a routing bug, not a reason to go global. Bucket-independent chips would have
been a UI band-aid over the routing defect. Settled.
 
### ✅ 373D — "Risks to Act On" headline fixed to count the FULL Risk bucket (SHA 8c852c7, v450)
 
Visual confirm of 373/373C on run `030920` surfaced a headline incoherence: "RISKS TO ACT ON 7"
but "16 Priority Review" (16 > 7 is impossible if PR ⊆ Risk). Read-only classifier replay (373D-Q)
overturned two wrong Chat hypotheses: (a) NOT a surface-disagreement bug — sidebar chip and Overview
both count PR at 16, they AGREE; (b) NOT a scope leak — all 16 Stage-7 HIGH findings genuinely route
to Risk. "One-Sided Terms" is a SUB-GROUP inside Risk, not a separate bucket; the 13 directionals are
Risk-bucket findings (3-0 verified + tenant_unprotected → 'risk'). The REAL bug: "Risks to Act On"
counted only `gaps + crossClause`, EXCLUDING the 13 directionals — contradicting action-type doctrine
(directional imbalances ARE a Risk subtype requiring protective action). The "7" was a legacy artifact
from before directionals were folded into Risk.
 
**373D fix:** `total = gaps + crossClause + directional` — "Risks to Act On" now equals the full Risk
bucket = sidebar Risk card count by construction. Sub-line shows all three sub-groups. Priority Review
UNCHANGED (was already correct, Risk-scoped). Validated both runs: `030920` 7→20 (2+5+13), PR 16, 16≤20;
`181402` 10→33 (5+5+23), PR 28, 28≤33. Headline==sidebar on both; no other bucket changed.
 
**⚠ LATENT FRAGILITY (recorded, not a bug today):** `total==sidebar` holds only because `riskOther==0`
on both runs (every synthesis Risk finding is compound or directional, so the 3 sub-groups exhaust the
bucket). A future finding type routing to Risk WITHOUT falling into gaps/cross-clause/one-sided (e.g. a
HIGH `cross_coverage_gap`) would be in the sidebar Risk bucket but invisible to both the sub-line and
the total — silently undercounting again. The robust form counts the Risk bucket DIRECTLY rather than
`gaps+crossClause+directional`. Flagged for the sidebar-rendering owner; out of scope for 373D.
 
**⚠ PRESENTATION NOTE (not correctness):** `181402` headline jumps 10→33. Doctrinally correct (full
Risk bucket, always was), but a lawyer who saw "10 risks" before may flinch at "33." If it reads as
scarier than reality in practice, that's a presentation question (how to show "33 risks, 28 priority"
calmly) — NOT a recount. Watch for it; don't pre-solve.
 
**Step 373 chain COMPLETE:** 373 (chip) → 373B (read-only classifier dump) → 373C (hard_flag routing
floor) → 373D (headline counts full Risk bucket). The original UI task — triage on a single Risk bucket
— is done: chip on cards, correct routing underneath, doctrine-consistent headline. Net SHAs:
be4a8eb → d043e53 → 8c852c7, app.js v450.
 
### ✅ 373E + ⏳ 373F — Overview labeling + headline-total hardening
 
**373E (SHA 04f4234, v451) — DONE.** Visual confirm of 373D showed "RISKS TO ACT ON 20" sitting above
a Coverage Snapshot pill "2 Risk" — two adjacent red Risk numbers reading as a contradiction. They're
different things (headline=all actionable Risk findings; pill=LP-level coverage-state count = the 2
coverage gaps). Pure relabel: panel "Coverage Snapshot" → "Coverage by Issue Area"; pill "N Risk" →
"N Coverage Gaps" (number unchanged, now mirrors sidebar sub-group). No logic touched. Validated both
runs: pill 2/5 unchanged, headline 20/33 unchanged.
 
**373F (SHA d6e5948, v452) — DONE.** 373F-Q (read-only) proved 373D's
`total = gaps+crossClause+directional` equals the true bucket only BY COINCIDENCE (`riskOther==0`
because both runs have zero cross_coverage_gap). A HIGH/CRITICAL `cross_coverage_gap` routes to 'risk'
but is tagged 'SYNTHESIS', matches none of the 3 displayed sub-groups, and is SILENTLY DROPPED from
`_computeRiskCounts` (else-branch leaves typeLabel=''). 373F-Q also found the authoritative count
ALREADY EXISTS: the sidebar builds `risk[]` bucket-first via classifyFindingType (app.js:18023/18027),
`risk.length`=20/33 — just never exported. 373F fix: total = direct classifyFindingType==='risk' count
(share the sidebar routing if feasible); subtype line becomes display-only + "Other Risks" fallback
(shown only when >0). Invariant: gaps+crossClause+directional+otherRisks === total. **Validation MUST
include a synthetic HIGH cross_coverage_gap injection** — both real runs have riskOther=0 so they can't
exercise the bug; the synthetic case is the only proof the silent drop can't recur.
 
**373F RESULT:** total now = direct `classifyFindingType==='risk'` count (`riskTotal`, incremented in both
loops — same bucket-first routing as sidebar `risk[]`). Subtypes display-only; `otherRisks` fallback
renders `· N Other Risks` only when >0; negative-guard console.warn (no silent clamp). Validated: real
runs 030920 (20, otherRisks 0) / 181402 (33, otherRisks 0) unchanged; **synthetic HIGH cross_coverage_gap
injection → total 20→21, otherRisks 0→1, "1 Other Risks" rendered** (the silent drop is now impossible to
reproduce). Invariant g+c+d+o==total holds all cases. PR unchanged on real runs (16/28); in the synthetic
case PR 16→17 is CORRECT (injected finding is a genuine HIGH synthesis Risk = legitimately Priority Review).
 
**Doctrine principle (banked):** the CLASSIFIER is the authoritative source of truth for Risk-bucket
membership; the subtype breakdown is DISPLAY-ONLY and must never define the total. Same family as
"record the field before you need it" (372) and "count the bucket, not a hand-list" — headline derives
from the authoritative computation, never re-derives it from an enumerable that can fall out of sync.
 
**⚠ SEPARATE FOLLOW-UP (do NOT fold into 373F):** 373F-Q noted `_computeRiskCounts` does NOT iterate
Mode-A DEVIATION Risk items at all — a distinct defect on a different (unmeasured) code path. Needs its
own read-then-spec. Recorded so it isn't lost; out of scope for the current chain.
 
### ✅ 373G — Coverage-by-Issue-Area panel scoped to current contract (SHA 85dd38c, v453)
 
Visual confirm raised: the two "coverage gaps" numbers (headline sub-line vs panel pill) agreed on
030920 only by coincidence. 373G-Q (read-only) proved: same predicate, but TWO INDEPENDENT LOOPS with
DIFFERENT SCOPE — headline = selected tenant, panel pills = SUM ACROSS ALL TENANTS (`tenants.forEach`).
They diverge on multi-doc jobs (panel job-wide sum vs headline current-contract). Tzvi decision:
current-contract scope, one contract at a time, NO cross-document sums (consistent with Step 048
removing the batch-summary card — product has always moved away from cross-doc aggregation).
 
**373G fix (SINGLE-SOURCE path):** `_computeRiskCounts` now ALSO returns the selected tenant's full
5-bucket coverage tally (`coverage:{risk,review_needed,improvement,addressed,na}`), built in the SAME
loop as `gaps` — so `coverage.risk` IS the headline `gaps`, one iteration, cannot desync. Removed the
job-wide `tenants.forEach`; all 5 pills read the selected-tenant tally. Captions reframed to
current-contract. Validated: 030920 (2/9/16/2/3=32), 181402 (5/7/15/2/3=32); **multi-doc fixture
(`mode_c_multi_test`, 2 contracts): OLD summed 6 gaps/36, NEW shows 3 gaps/18 per selected contract,
switching contract updates every pill, headline==panel per contract, no rollup.** The proof ran on the
input that actually exercises divergence, not just single-doc replay.
 
**⚠ FOLLOW-UP (Tzvi's call, recorded not done):** the conflict pill and "Governed by X" gov-law badge
still derive from a separate job-wide `tenants.forEach` (~app.js:4700) — the only job-wide aggregates
left on an otherwise current-contract Overview. Gov-law especially could be WRONG (not just inconsistent)
if contracts in a multi-doc job have different governing law. Lean: extend current-contract scope to
them too. Minor; decide when convenient.
 
**Step 373 chain (373→373C→373D→373E→373F→373G) — Overview now fully internally consistent and
current-contract scoped.** Headline counts the Risk bucket directly (classifier = source of truth),
Priority Review nests, panel describes the same contract at the same scope, the two coverage-gap numbers
are ONE number. Original UI task (triage on a single Risk bucket) DONE + hardened. Latest app.js v453,
SHA 85dd38c.
 
### ✅ 374 — Overview FINDINGS-FIRST redesign: Action Summary replaces the coverage census (SHA 7f394d7, v454)
 
Your observation drove this: the dashboard showed coverage gaps but not the other 2 Risk subtypes,
and the sidebar/Key-Findings counts disagreed on the same contract (Needs Review 24 vs 9, Addressed
1 vs 2, blank sidebar Risk number). 374-Q (read-only) traced ALL of it to one root cause: the Overview
mixed a FINDINGS taxonomy (sidebar) and a COVERAGE-STATE taxonomy (Key Findings pills) without deciding
which is the spine. Decision (Tzvi): findings-first — the four ACTION buckets are the Overview, the raw
32-LP coverage census is removed (per-LP states stay accessible in Coverage&Gaps tab / heatmap / Evidence).
 
**Action Summary (current-contract, single-source):** `_computeRiskCounts` now returns all four action
bucket counts + Needs Review subtypes, replicating the sidebar routing → Overview == sidebar by
construction (the blank sidebar Risk header is also un-blanked). Honest asymmetry:
- RISK 20 — subtypes (2 gaps · 5 cross-clause · 13 one-sided · +Other if>0); chip relabeled
  **"N Priority Risks"** (was "Priority Review" — collided with the Needs Review bucket; logic unchanged).
- NEEDS REVIEW 24 — THREE subtypes: **8 unresolved coverage · 1 disputed protection issue · 15 unverified
  one-sided**. The 1 disputed-protection item (disagreement-floored) is kept DISTINCT, not folded — it's
  the visible consequence of CAM's deliberate-non-deliberation governance, the signal the architecture
  exists to preserve. A one-item subtype is justified when it's a different REASON for review.
- IMPROVEMENT 16 — count + gloss only (15-vs-1 split is degenerate; no taxonomy theater).
- ADDRESSED 1 — count + gloss only; **suppression rule** (an issue area implicated in any Risk/Review/
  Improvement finding is NOT Addressed — LP-05 excluded though coverage-positive, since it's in Dir-05+CRX-05).
**Partition discipline (banked):** the four Action Summary numbers are lawyer-facing ACTION ITEMS, NOT a
partition of the 32 assessed issue areas, and must not be compared to raw coverage-state totals (Risk/Review
include synthesized+directional findings; Addressed is a residual after suppression). No "32 issue areas"
caption on the Action Summary.
 
**Scope fixes folded in (GPT correctness flag):** gov-law badge + conflict pill were JOB-WIDE — scoped to
the selected contract. **Proven on a genuine MIXED fixture** (`...011541...`: laws None/None/NY, conflicts
2/2/3): OLD = "Governed by NY" for all + 7 summed conflicts (the badge was FALSE on mixed-law); NEW =
per-contract (tenant_1 no badge/2 vs tenant_3 NY/3). Exercised the actual failure mode, not equal-valued
contracts — the 373F mixed-fixture lesson applied.
 
**Validation:** 030920 (R20/NR24[8+1+15]/I16/A1) and 181402 (R33/NR12[3+4+5]/I15/A1), each bucket ==
sidebar by construction, subtypes sum to totals, Addressed=1 via suppression. classifyFindingType/routing/
Priority-Review logic UNCHANGED (display + count-sourcing + scope only). NOTE: visual layout change —
numbers replay-validated, rendered CSS needs a hard-refresh eyeball.
 
**Overview thread CLOSED.** 373 chain reconciled counts WITHIN the old layout; 374 fixed the layout's
organizing principle (findings-first). Sidebar and Overview now tell ONE story from ONE source. Original
UI task fully done. Latest app.js v454, style.css v397, SHA 7f394d7.
 
### ✅ 374B — Needs Review gloss copy fix + canonical gloss table (SHA 7c42221, v455)
 
Tzvi flagged the Needs Review gloss "CAM couldn't decide — you review" as vague (doesn't say WHY or
WHAT) and mis-framing (it framed CAM's deliberate disagreement-preservation as a failure). GPT caught a
near-miss: the proposed fix "Potential Risks / Identified Risks" rename would have COLLAPSED confidence
into action type — the exact action-type doctrine violated. **Doctrine reaffirmed:** Risk / Needs Review /
Improvement / Addressed are ACTION TYPES, not confidence tiers. Risk can hold low-confidence findings
where consequence warrants action; Needs Review = CAM can't safely determine WHICH action type applies
(some will become Risk after review, some Improvement, some Addressed — that uncertainty IS the category).
NO bucket renamed. Copy-only.
 
**Canonical gloss table (both surfaces aligned):** Risk = "Identified exposure — act to protect"; Needs
Review = **"Unresolved or disputed — inspect evidence"** (changed; "inspect evidence" points into the
built Evidence drilldown, not "manually" which implies CAM stopped helping); Improvement = "Protection
exists — could be tightened"; Addressed = "No action recommended". The subtype line carries the why/what
(8 unresolved coverage · 1 disputed protection issue · 15 unverified one-sided terms); the gloss only
names the action. NO subtype tooltips (deeper explanation belongs in click-through Evidence, not hover
balloons — poor on touch). 
 
**Intentional surface-specific asymmetry (RECORDED so it isn't "fixed" later):** in the Action Summary,
the Risk bucket OMITS the generic gloss because its "Priority Risks" chip + subtype line already
communicate urgency and structure (a gloss would be a 3rd explanatory layer while other cards have 1).
The SIDEBAR retains the Risk gloss because collapsed navigation needs a compact action cue before the
user examines findings. Same doctrine, different density per surface — NOT a doctrinal difference.
Caveat for later (not now): if a responsive/mobile layout shows the Action Summary WITHOUT the sidebar
and the Risk card reads unclear in isolation, revisit then.
 
### ✅ 374C — Needs Review copy: lead with exposure, lawyer-facing language (SHA 7df3640, v456)
 
Tzvi pushed further: even after 374B removed "couldn't decide," the gloss "Unresolved or disputed —
inspect evidence" still described a finding STATE (passive, sounds like CAM shrugged) and leaked internal
governance vocabulary (unresolved/unverified/disputed) onto the executive surface. He wanted positive
verbiage signaling CAM DID the work. Resolution (Tzvi's wording): lead with the substantive concern, name
lawyer-facing possibilities, recommend review without implying CAM gave up. Considered + REJECTED "models
disagreed" as the bucket gloss — true for only 1 of 24 (the conflicting reading); would over-claim for the
15 one-sided + 8 coverage. Solved by putting the disagreement signal at the ONE subtype where it's true.
 
**Final Needs Review copy (both surfaces):**
- Gloss: "Potential exposure: protections may be incomplete or missing, terms may be one-sided, or readings
  may conflict. Attorney review recommended."
- Subtype line (Action Summary): "8 coverage questions · 15 possible one-sided terms · 1 conflicting reading"
  (reworded + reordered from unresolved/disputed/unverified internal terms; counts UNCHANGED 8/15/1;
  pluralizes correctly — 181402 shows "4 conflicting readings"). Internal field names unchanged; display only.
Doctrine guard held (3rd time): action types not confidence tiers; no bucket renamed. Detailed evaluator
split/citations stay in Evidence/Audit; Overview speaks lawyer language. Sidebar took the full sentence
(no trim needed — `.nav-section-gloss` wraps).
 
**Overview copy SETTLED.** Labels, glosses, subtype language all final. The UI thread (373→374C) is
complete: layout findings-first, counts single-source, labels doctrine-correct, copy lawyer-facing and
CAM-positive. Latest app.js v456, SHA 7df3640.
 
### ✅ 374D/E/F — Risk gloss added, unified across surfaces, punctuation consistent (SHA 7dc61d1→, v459)
 
Once the panel was framed as "Action Summary," Risk was the only main card NOT stating an action (374B
had deliberately left it gloss-less, but that predated the action framing). 374D added an action gloss;
374E unified it across sidebar + Action Summary (they'd drifted to two different Risk glosses, which reads
as accidental inconsistency once both show simultaneously); 374F fixed trailing-period drift across the
four glosses. Implemented via a SHARED CONSTANT `CAM_RISK_GLOSS` (app.js:4738) read by both surfaces —
the copy-layer version of the single-source discipline this whole session enforced; the Risk gloss can't
drift between surfaces again.
 
**FINAL canonical gloss set (all four, both surfaces, period-terminated):**
- Risk: "Identified exposure — protective action recommended." (status + action, no subtype repetition,
  no "confirmed" — doesn't collapse confidence into action type)
- Needs Review: "Potential exposure: protections may be incomplete or missing, terms may be one-sided,
  or readings may conflict. Attorney review recommended."
- Improvement: "Protection exists — could be tightened."
- Addressed: "No action recommended."
Not redundant on the Risk card: subtype line = WHAT KINDS (2 coverage gaps · 5 cross-clause · 13 one-sided),
gloss = WHAT TO DO. Same division as Needs Review. **Overview copy now genuinely COMPLETE.** Latest app.js
v459.
 
### Improvement subtype question — checked, count+gloss confirmed correct (374IMP-Q, n=1)
 
Tzvi asked whether Improvement / Needs Review should be subdivided like Risk. Answer:
- **Needs Review ALREADY is** ("8 coverage questions · 15 possible one-sided terms · 1 conflicting reading")
  — symmetric with Risk, on the card now.
- **Improvement correctly is NOT.** `build_log/374IMP-Q.py` on 030920: the Improvement-routed findings are
  overwhelmingly ONE combo — 14 identical `partial / partial_typical / low-materiality / no-hard_flag`
  (partial-but-typical, low-stakes drafting). No honest second group to break out; a subtype line would
  be taxonomy theater (confirms 374-Q's "15-vs-1 degenerate"). Count + gloss is the truthful rendering.
- Addressed (1) — count + gloss, nothing to divide.
**This is the honest-asymmetry design working:** each bucket shows the structure it genuinely has, not
forced visual parallelism. **CONDITIONAL for the future (n=1 caveat):** "Improvement is one flavor" is
true for Atlas Meridian. A lightly-flagged contract with varied partial provisions COULD give Improvement
real sub-structure (e.g. low-mat drafting vs medium-mat tightening). Rule: Improvement gets a subtype line
IF/WHEN a contract shows real sub-structure — re-run 374IMP-Q on such a contract before deciding. Do NOT
hardcode "Improvement never has subtypes."
 
### ✅ 374G — Needs Review sidebar sub-headers, single-sourced with the Action Summary (SHA f72d113, v460)
 
Tzvi noticed the sidebar Needs Review was a FLAT list of 24 while Risk's sidebar grouped under collapsible
sub-headers. (The Action Summary already showed the subtype LINE; the sidebar was the inconsistent surface.)
374G-Q (read-only) found the collapsible wrapper `_navSubGroupWrap` is reusable, but the sidebar would have
re-derived subtypes from `typeLabel` — a DIFFERENT signal than the authoritative `reviewSub` rule
(`hard_flag + coverage_state`). They reproduce 8/15/1 today only by COINCIDENCE; grouping by typeLabel
would have created a THIRD classification path that silently disagrees with the Action Summary on the
unclassifiable edge — the exact two-surface drift this session kept fixing.
 
**374G fix (single-source):** factored `_reviewSubtypeOf(finding)` (authoritative rule) — `_computeRiskCounts`
was REFACTORED to call it for reviewSub (inline branching removed, not duplicated), and the sidebar stamps
`_reviewSubtype` via the SAME helper at all push sites, partitions, and renders each group through the
existing `_navSubGroupWrap` (collapse/persist free). Three sub-headers: Coverage Questions / Possible
One-Sided Terms / Conflicting Reading (big one-sided group default-collapsed, mirroring Risk). Validated:
030920 8/15/1, 181402 3/5/4 — sidebar == Action Summary BY CONSTRUCTION (one helper, two consumers); they
can no longer diverge. Risk grouping untouched; totals unchanged; no finding moved buckets.
 
**Sidebar now symmetric:** both Risk and Needs Review grouped into collapsible subtype sub-headers, both
single-sourced with their Action Summary counts. The "I'm not seeing subcategories in Needs Review" gap
is closed. Latest app.js v460.
 
### ✅ 374H/I — sidebar color-keying to match Action Summary cards (CSS-only, style.css v399)
 
Tzvi: sidebar buckets ran together (color was header-text only), should match the Action Summary cards
and read as distinct when collapsed. Option B chosen (tinted header, neutral finding bodies — full body
tint rejected as too heavy in the narrow column once real findings list). CSS-ONLY, no JS/markup.
- **374H** (SHA 68fec02): tinted each bucket's collapsible header with the EXACT Action Summary card
  tokens (Risk #fef2f2/#fecaca, Review #fffbeb/#fde68a, Improvement #dbeafe/#60a5fa, Addressed
  #ecfdf5/#a7f3d0) on the real `.nav-section-{bucket} .nav-section-header` element; 0.5rem gap between
  buckets for separation (no divider lines). Sub-group headers + finding rows stay neutral.
- **374I** (SHA 583c490): per Tzvi live feedback — (1) moved the gloss INTO the colored band (tinted
  `.nav-section-gloss` same bg + bottom rounding so header+gloss = one continuous block; CSS-only, gloss
  was already the header's sibling); (2) fixed unreadable pale grey — gloss text → each bucket's dark
  color (#991b1b/#92400e/#1e40af/#047857), `.nav-subgroup-title`/`.nav-subgroup-count` #6b7280/#9ca3af →
  #374151 (readability floor, was an accessibility problem not a preference). style.css v399, app.js
  untouched. Visual — not replay-validatable; needs Tzvi eyeball. Optional dial-backs if it reads heavy:
  lighten tint a notch, or per-bucket sub-label coloring.
### ⚠️ 374K finding — LP-level "severe disagreement" can be a TIE-BREAK ARTIFACT; Overview may be contaminated
 
**The Overview is NOT yet safe to call "done."** A user-spotted banner mismatch on LP-06 opened a real
epistemic-governance finding (full writeup: `Docs/Finding_2026_06_03_disagreement_signal_tiebreak_artifact.md`).
 
WHAT: The LP-level per-evaluator verdict is a DETERMINISTIC plurality rollup of element verdicts
(tie→most-pessimistic), NOT an independent judgment. LP-06's "severe: missing vs explicitly_present" was
manufactured by a 2-2 element tie (GPT called HVAC `unclear`, Grok/Claude `missing`) broken pessimistically,
then amplified by the ordinal ladder to distance-5. Its hard_flag fired only because `use_impact` was MISSING
→ consequence defaulted to "moderate" (lease_adapter.py:1006; true materiality `low` → would be hard_flag=false).
Generalizes: ~9 of 13 severe cases across 2 runs are tie-break artifacts.
 
WHY IT MATTERS: hard_flag drives the 373C floor (improvement→Needs Review) AND the "Priority Risks" chip.
LP-06 is the "1 conflicting reading" surfaced in the Overview/sidebar — i.e. THAT finding is this artifact.
So "16 Priority Risks" + the Risk/Needs Review counts may include artifact-escalated findings. The copy was
polished on numbers whose input signal isn't validated.
 
CORRECTION TO PRIOR STATE: earlier this session the chat (and these notes) called the disputed-protection
finding "CAM's signature behavior working as designed." That was WRONG — on this contract it's largely a
rollup/tie-break artifact. Overturned by reading the producer function (lease_verdict_distance.py:202).
 
ACTIONS: 374M (containment, shipping) reworded the false banner ("Severe disagreement: missing vs
explicitly_present... Full evaluator reasoning below" → "Review escalation triggered from derived coverage
signals. Element-level evidence shown below") — NO logic changed. 374N-Q (read-only, queued) measures
contamination of the Overview counts across all runs before declaring stable. DO NOT fix the rollup/
tie-break/ladder or the `or "moderate"` default from n=2 — core/patent-relevant epistemic logic, measured
work only. The `or "moderate"` defect is unknown-masquerading-as-assessed, likely wants an explicit
not_assessed state, NOT a value swap.
 
### 374K/M/N QUANTIFIED — contamination is real, bounded, and SEPARABLE (audit 030920 + 181402)
 
374M shipped (v461, SHA 41a4dbb): UI honesty containment across FOUR lawyer-facing surfaces that
presented the derived LP rollup as direct evaluator disagreement (card banner 16413, status chip 16473,
Audit note 12013 — the worst, "one evaluator found X another found Y", and Evidence note 8010). All
reworded to derivation-honest language; element-level disagreement strings (genuine, auditable) left
intact. WORDING ONLY — no logic/routing/taxonomy.
 
374N-Q downstream audit (read-only; 011541 predates the verdict_distance/use_impact schema → nothing to
audit there). Per-LP classification:
- **030920** (6 severe/hard_flag): tie-artifacts LP-06/14/16/28, genuine LP-20/32. Floor moved bucket:
  LP-06 only. Defaulted consequence: LP-06. In Priority Risks: 0.
- **181402** (7): tie-artifacts LP-06/14/16/28/32, genuine LP-02/20. Floor moved: 4 (LP-06/16 artifact,
  LP-02/20 genuine). Defaulted: LP-06. In Priority Risks: **LP-28, LP-32 — both tie-artifacts.**
Q6 current vs artifact-marked (display-only, no logic changed):
- 030920: Needs Review 24→23, Improvement 16→17, Risk 20 (unch), Priority Risks 16 (unch — all synthesis).
- 181402: Needs Review 12→10, Improvement 15→17, Risk 33 (unch), **Priority Risks 28→26.**
VERDICT on "is the Overview stable?":
1. **Risk count: UNCONTAMINATED** both runs (membership consequence-driven).
2. **Needs Review: CONTAMINATED** — 1/run (030920: the entire "1 conflicting reading" = LP-06 artifact) to
   2/run (181402).
3. **Priority Risks: NOT STRUCTURALLY SAFE.** Clean on 030920 (16, all synthesis) but 2 artifact-elevated
   on 181402 (LP-28/32). Cleanliness is luck-of-the-contract — DO NOT declare the chip stable until the
   rollup + consequence-default governance fix lands.
4. Every contaminator is a tie-artifact and/or defaulted case; genuine escalations (LP-02/20) survive the
   filter — so the fix has a clean target with no collateral on real findings.
Full tables: build_log/374N-Q_code_status.md. Remediation options: 374K_governance_finding.md §8 (and
Docs/Finding_2026_06_03_disagreement_signal_tiebreak_artifact.md). NEXT on this thread = measured
governance work (rollup/tie-break derivation + consequence_status design), NOT same-session patching, NOT
from n=2. Executive-copy work on the counts is PAUSED until that lands.
 
### 374P/Q — provenance instrumentation, candidate recompute, relabel-only containment
 
**374P** (read-only, production byte-identical): added provenance sidecars (lp_verdict_derivation_source,
distance_includes_tie_derived_verdict, consequence_source, hard_flag_inputs, priority_risk_basis) for
every severe/hard_flag LP, and recomputed 5 candidate policies. RESULTS: C2/C3/C4 (relabel-only) PASS all
exit criteria — conflicting_reading 1→0 (030920), 4→2 (181402), Risk/NeedsReview/PriorityRisks counts
unchanged, genuine escalations (LP-02/20/28/32) preserved. C5 (corroboration) BLOCKED (changes routing).
Stage 5e gap identified (NOT fixed): `_should_assess` only assesses `partial` LPs at ≥50% non-present
elements; LP-06 is 40% → skipped → no use_impact → defaulted consequence.
**EXCEPTION found:** 181402 Priority Risks LP-28/32 are tie-derived severe BUT assessed-high consequence,
so NO candidate contains them — needs a doctrine decision, parked (see 374R-Q below).
 
**374Q** (relabel-only containment, v462, PROVISIONAL): withholds the "conflicting reading" subtype label
where basis is tie-derived/defaulted (findings STAY in Needs Review under truthful subtype; total
unchanged); presents defaulted consequence as "consequence not assessed — attorney review recommended".
NO count/routing/logic change — only the executive characterization. Lawyer-facing stays outcome-worded;
plumbing language confined to Audit.
 
**PARKED — 374R-Q DONE (read-only recompute); scoping correction REVERSED by the data.** I had told 374R-Q
that LP-28 was the artifact and LP-32 was genuine severe. WRONG — the recompute checked raw element verdicts:
LP-32's A=missing is itself a 4-4 pessimistic tie-break (severity_if_tie_optimistic="none"), structurally
identical to LP-28's 3-3 tie. BOTH are tie_derived_severe=TRUE (agrees with the original 374P sidecar; my
"correction" was the error). Treat them SYMMETRICALLY. But both ALSO carry a genuine independent basis
(unanimous critical-missing element + assessed-HIGH consequence; LP-28 additionally a real element-level
dispute) — so it's "right priority OUTCOME, false stated BASIS" for BOTH.
 
374R-Q policy table (181402 is the only run with coverage Priority members; 030920 has none):
- P4 baseline: PR 28, basis shown "severe disagreement" (FALSE for LP-28/32), masquerade on both.
- P1 provenance-pure: PR 26, demotes LP-28+LP-32 — BLOCKED (demotes genuinely high-consequence items).
- **P2 consequence-first: PR 28, basis "high assessed consequence" (TRUE), no demotion, no masquerade — PASSES.**
- P3 combined-evidence: same PR set, richer basis, but relies on an unvalidated corroboration detector (n=2).
RECOMMENDATION (input to a doctrine decision, NOT the decision): P2 — true basis, no genuine demotion,
minimal relabel footprint. A later 374S basis-relabel must apply the consequence-based basis to BOTH
LP-28 AND LP-32 equally (symmetric). Still needs MORE CONTRACTS before enforcement; n=2 directional only.
META: this is the 3rd time this session that reading the real artifact overturned a confident interpretation
— and this time the wrong interpretation was the chat's own "scoping correction," caught because 374R-Q was
instructed to VERIFY the split against the sidecar rather than accept the premise. Measure-don't-enforce
caught a chat error, not just a system one.
 
NOTE (also for 374Q, found via provenance): the "Confidence capped at low" banner phrase is itself part of
the tie-break artifact for tie-derived LPs (LP-06 severity_if_tie_optimistic=none) — 374Q now also drops
that phrase for tie_derived_severe cases (wording only; confidence computation unchanged).
 
**PROVENANCE OF THE WHOLE FINDING (do not overclaim):** CAM did NOT self-detect. Human (Tzvi) challenged a
UI that didn't reconcile with visible evidence → forced a read of the producer → Code found the mechanism →
audit quantified it. Human-in-the-loop AUDITABILITY story, not self-detection. Validation finding, NOT a
patent contribution until a corrected mechanism is validated across more contracts.
 
### ✅ 374U/V — reasoning un-clip + lawyer-facing copy for the not-assessed-consequence card (v464)
 
**374U** (SHA 006331a, v463): removed the 300-char display clip on expanded evaluator reasoning
(app.js:16454). 374T-Q confirmed the truncation Tzvi spotted (Claude's LP-06 HVAC reasoning cut at
"...no other provision in the LP ...") was DISPLAY-ONLY — data complete (325 chars, ends clean). Full
reasoning now shows, still behind the disagreement expand. Max reasoning 795 chars (<1500, no scroll guard).
 
**374V** (SHA d6b990a, v464): lawyer-facing copy for the consequence-not-assessed card. Tzvi rejected
"not assessed" framing (sounds like CAM was lazy); reframed as deliberate escalation/restraint (constrained
assertion = don't assert what you can't ground, hand judgment to the attorney). Three relabels:
- Badge "derived review signal" → "Consequence requires attorney judgment"
- Impact label "Impact Unclear" → "Impact: attorney judgment required"
- Banner → "Attorney review recommended: potential exposure was identified; consequence requires your
  judgment. Element-level evidence appears below."
**CRITICAL GATE (the trap):** these relabels are CONDITIONAL on `_reviewSubtypeOf===consequence_not_assessed`
(how 374Q surfaces the provenance), NOT the raw `consequenceDefaulted` flag — which fires on 17/18 cards
(most LPs lack use_impact) and would have blanket-relabeled the whole report. Gated correctly → exactly
LP-06 per run. Proven: LP-16 (same severity=severe but materiality=high, genuinely assessed) → gate FALSE,
keeps real labels. Label keys off consequence PROVENANCE, not severity.
**Tzvi's "sounds lazy" instinct = a real correction:** the honest fact (consequence not assessed) was
already true; what changed was the VOICE — from "CAM didn't get to it" (defect framing) to "CAM hands you
the judgment" (restraint framing). For a tool whose value IS not-overclaiming, the UI should sound
confident-by-restraint, not apologetic-by-omission. Same species of catch as the banner/confidence-cap/
impact-label overclaims — Tzvi caught the card asserting more (or framing worse) than the system warranted,
a 4th time. Latest app.js v464.
 
### ⚠️ 374W-Q finding — `absence_adverse_to` is DEAD DATA (perspective-polarity sign error, SYSTEMIC)
 
Tzvi asked "is this a problem for the tenant?" on LP-27's missing "tenant must notify lender + afford lender
cure period" element (Missing 3-0, genuine). That element is a tenant BURDEN — its absence is favorable/
neutral to the tenant, not exposure. Read-only investigation (374W-Q, full writeup
build_log/Finding_2026_06_03_absence_polarity_sign_direction.md) found a SYSTEMIC defect:
 
**`absence_adverse_to` (the per-element field recording WHOM an absence hurts) is captured in the schema but
read by ZERO pipeline Python files** — only by update_schema_305.py (which writes it). The pipeline reads
magnitude (`absence_severity`) but never the SIGN. So every missing expected element is treated as a gap
adverse to the selected perspective regardless of polarity — violating the documented coverage-vs-polarity
split. **73 of 212 elements (34%) are tagged non-tenant** (53 landlord, 20 both; 29 high-severity): tenant
obligations (indemnity, compliance, estoppel, hazmat, subordination-execution), the entire LP-11
landlord-remedy suite (re-entry/terminate/acceleration/recapture), landlord consent/insurance rights.
 
**CONFIRMED HARM (bounded):** (1) the exposure HEADLINE — `_build_model_exposure` feeds `missing[:4]` to the
model as "missing/unfavorable" with NO polarity filter (lease_exposure.py:295), so "lender cure delay"
narrates a favorable absence as exposure — directionally backward, lawyer-facing; (2) coverage_state — a
lease omitting a tenant burden can be marked partial/gap instead of favorable.
**NOT harmed on LP-27:** Risk ROUTING. LP-27 ∈ _HIGH_MATERIALITY_LPS (per-LP floor) + the genuine missing
self-help/offset element keep it Risk regardless. LP-27 correctly STAYS Risk; only the headline is wrong;
no counts change. (Tzvi's "don't conclude LP-27 leaves Risk" held.)
 
**LANDMINE:** _HIGH_MATERIALITY_ELEMENTS lists landlord-favorable "rent acceleration"/"recapture" as
high-materiality — polarity blindness is baked into the materiality tables, not just the missing-counter.
 
**FIX SCOPE (decision pending):** narrow = polarity-filter the exposure-model input (display-adjacent, no
routing change, safe now). Systematic = wire `absence_adverse_to × perspective` into derive_lp_state +
_classify_materiality + exposure filter — shifts routing on some of the 73, so MEASURE-before-enforce
(374P/374R-Q pattern), NOT an n=1 patch to core logic. Joshua validates legal framing AFTER the
deterministic fix. This is the biggest finding of the session — a designed safety field never wired in.
 
**REFRAME (Tzvi): favorable absence is INTELLIGENCE, not just noise.** A missing tenant BURDEN / missing
opposing-party protection is usable client position (enforcement flexibility, leverage), not merely "not a
gap." Turns `absence_adverse_to` from a FILTER into a ROUTER: adverse→Risk, favorable→Favorable Position,
context-dependent→Needs Review, neutral→suppress. Guardrails: favorable does NOT net against Risk; NOT
buried in Addressed; MUST carry the SNDA/lender-agreement/law caveat (absence here ≠ absence everywhere);
NO 5th bucket until 374Y-Q frequency data justifies it (and it may be a POSITION-TYPE facet within cards,
not an ACTION-TYPE peer bucket). Full writeup + guardrails in the Finding doc.
 
**✅ 374X SHIPPED (SHA 70ecb70, backend only, no version bump):** exposure-headline polarity containment,
PROSE ONLY. Precondition confirmed (exposure prose is display-only, not consumed by routing/state/
materiality — single template call site, computed upstream of exposure). `_build_model_exposure` now
partitions missing elements by `absence_adverse_to × perspective`: adverse-to-perspective → "Missing or
unfavorable" input (unchanged); opposite-party → separate "Favorable or non-adverse absences (context
only)" slot; null/both/contextual → stay adverse-eligible (not reinterpreted). LP-27: self-help stays
adverse-eligible, lender-cure moves to favorable slot, lender element no longer in the missing/unfavorable
line. LP-27 STAYS Risk (floor + self-help, computed upstream — untouched). No count change. Effect shows on
NEXT run (prose generated at run time); validated via partition unit-test + rendered prompt. RESIDUAL
flagged for 374Y-Q: `_build_schema_exposure` `missing[0]` fallback is also polarity-blind (only fires for
LPs with no schema exposure_statement; LP-27 uses the model path so already fixed).
 
**✅ 374Z SPECCED (build_log/374Z_chat_instruction.md) — GATE CORRECTED: fixtures, NOT contract count.**
I was WRONG that enforcement waits for more contracts. GPT caught it: this is NOT the tie-break problem
(multiple defensible policies → measure prevalence). It is a DIRECTIONALITY INVARIANT — "a missing element
adverse to the opposite party must not be counted as a selected-perspective gap merely because missing" is
the MEANING of absence_adverse_to, not a threshold judgment. C3 = consume the field as designed. More
leases VALIDATE; they do not GATE correctness. The real gate is targeted regression FIXTURES (6 cases:
missing protection / missing burden / mixed LP-27 shape / null-polarity / exact-match high-materiality
opposite-polarity / cross-doc dependency) — which exercise exact conditions random leases may never hit.
374Z: enforce C3 in derive_lp_state + the missing[0] exposure fallback + _classify_materiality; FIX the
rent-accel/recapture landmine IN-step (high materiality amplifies an adverse absence, never reverses
polarity; correct label alignment must not arm a false positive). Exit criteria match the 374Y-Q C3
prediction (LP-08 Improvement→Addressed, LP-27 stays Risk, nothing else). Provisional pending broader
VALIDATION (not correctness). Do NOT bundle favorable-position UI (data slot preserved, surfacing gated on
374Y-Q funnel + lawyer validation) or tie-break/Priority governance (separate open policy).
 
**Favorable measurement refined (374Y-Q + GPT):** opposite-polarity is NECESSARY NOT SUFFICIENT for
"favorable." landlord-adverse absence → CANDIDATE favorable → dependency check (SNDA/law/other LP) → surface
only where supportable. Don't collapse favorable with non-adverse. Name "Favorable Position" (not Strategic
Advantage / Negotiating Leverage — those overclaim). Position-type facet within cards, separate axis from
the action-type buckets.
 
**✅ 374Z DONE & DEPLOYED (SHA 609af43, Railway auto-deploy, backend only).** C3 polarity correction enforced;
landmine neutralized. `absence_adverse_to` now CONSUMED at all three sinks (tenant default): (1) derive_lp_state
— opposite-polarity missing = favorable absence not gap; LP whose only non-present elements are favorable →
covered; (2) favorable_or_non_adverse_absences data slot populated (with cross_LP_coverage caveat), elements_missing
becomes adverse-only so state/materiality/exposure/display all turn polarity-correct in one move — NO UI bucket,
never offsets Risk; (3) _classify_materiality filters high-materiality match to perspective-adverse only —
high materiality AMPLIFIES an adverse absence, never reverses polarity. GATE (all green before push):
6/6 targeted fixtures pass incl. #5 landmine (rent-acceleration string ALIGNED to its LP-11 label still yields
materiality=low, not tenant Risk — trap defused, not just flagged); exit criteria on 030920+181402 = ΔRisk 0,
ΔPriority 0, none lost, LP-08 Improvement→Addressed, LP-27 stays Risk — matches 374Y-Q C3 prediction exactly.
Provisional pending broader-contract VALIDATION (not correctness). Effect shows on NEXT run (stored results keep
old coverage_state — re-run a lease to see LP-08→Addressed and LP-27 lender→favorable slot).
 
**⚠️ 374Z DOCUMENTED LIMITATION (follow-up, not a blocker):** the COVERAGE STAGE runs perspective-blind —
`assess_coverage` has no perspective param (perspective enters only at exposure), so derive_lp_state DEFAULTS to
tenant. Correct for ALL current runs/fixtures (tenant perspective). But LANDLORD/NEUTRAL reviews will not get
correct polarity until perspective is threaded into the coverage stage. Flagged follow-up (374-series): thread
perspective from cfg through assess_coverage → derive_lp_state. Until then, the polarity fix is tenant-correct
only. Don't run a landlord-perspective review and trust coverage_state polarity until this lands.
 
**✅ 374Z-V — 374Z VERIFIED LIVE on the fresh run (SHA 1c3f4ff verification, read-only).** Fresh run
lease_review_20260604_033046_52adbf (same Atlas Meridian lease, identical text SHA, pipeline v1.0.0,
deployed SHA 609af43). ALL 374Z-specific predictions match on the LIVE pipeline (not just the recompute):
LP-08→covered→Addressed (certificate in favorable slot, elements_missing=[]); LP-27 stays partial/
partial_material/high→Risk, lender-cure in favorable_or_non_adverse_absences WITH cross_LP_coverage:[LP-22],
self-help still adverse, headline now "No self-help rent offset" — "lender cure delay" GONE. Favorable slot:
11 elements / 6 LPs (LP-08/09/10/11/22/27), ALL landlord-polarity, zero tenant mis-routed; the LP-11
rent_acceleration LANDMINE element correctly sits in the favorable slot (not a tenant gap, didn't drive
Risk) — live confirmation the landmine fix holds. NO LP dropped out of Risk; no genuine adverse finding lost.
Count prediction NOT claimed confirmed by this run (see synthesis-instability flag) — the clean count check
is the frozen-verdict recompute in 374Z (ΔRisk=0); a fresh run re-runs all LLM stages so absolute counts
between two runs aren't comparable. Code correctly refused to rationalize the count divergence.
 
**🔴 NEW FLAG — SYNTHESIS-SEVERITY INSTABILITY (Stage 7, independent of 374Z, worth its own look):** on the
fresh same-lease re-run, the UNTOUCHED synthesis stage (lease_synthesis.py) swung HIGH severity 16→30,
driving Risk 20→36 and PriorityRisks +15 vs the 030920 baseline; 5 of 7 coverage-state changes were
review_needed→partial verdict-variance flips (collapsing NeedsReview 24→4). This is byte-identical-input
severity instability in the SYNTHESIS path — same family as the 372-chain coverage-instability work but in
Stage 7 severity, and large. NOT caused by 374Z (374Z only moved LP-08 Improvement→Addressed). This is the
bigger live signal: the Risk headline is dominated by synthesis re-run nondeterminism, not by the
deterministic coverage layer. Candidate for a measured instability investigation (matched-run diff on
synthesis HIGH-severity assignment). Does NOT block 374Z (mechanism verified) or NEXT0.
 
**→ 375-Q SPECCED & PRIORITIZED FIRST (build_log/375-Q_chat_instruction.md), read-only two-track.** GPT call
(accepted): this is the CURRENT lawyer-trust BLOCKER, not a future nicety — "nothing's on fire" was wrong;
the executive summary has smoke coming out of it. Same lease → Risk 20 vs 36 blocks demo/Joshua use of the
headline counts. CAPTURE-BEFORE-CHANGE: run on the current 374Z commit (609af43) BEFORE merging NEXT0 or
any pipeline change, so we don't perturb the pipeline while measuring its biggest swing. NEXT0 is DEFERRED
(not discarded) for attribution hygiene. Two tracks: A = ≥5 full reruns (shape of instability); B = ≥5
frozen-pre-Stage-7-input synthesis-only replays (ATTRIBUTION: is Stage 7 the source or the messenger?).
The decisive question is "did Stage 7 find DIFFERENT issues or RATE the same issues differently," reported
for compound and directional populations SEPARATELY. Measurement only — no prompt/threshold/severity/Risk/
Priority/routing change until attribution lands. PRODUCT STATUS: 374Z polarity = verified live; Risk-headline
stability = NOT validated; external demo / Joshua use of Risk totals, Priority totals, Stage 7 counts = PAUSED.
 
**✅ 375-Q DONE (SHA d20c5d8, read-only, production byte-identical at 609af43). ATTRIBUTION: directional
Pass-2 severity instability; STAGE 7 IS THE SOURCE, not the messenger.** Code couldn't run live Track A/B
(sandbox has only the Claude gateway key — no OpenAI/Grok; pipeline routes to those) so it used the ~20
existing byte-identical Atlas Meridian runs incl. two SAME-COMMIT back-to-back triplets (s370r1/2/3,
370c_H1/2/3) + the current-code 030920↔0604 pair, decomposed PER PASS-2 ROLE — a stronger isolation than 5
black-box reruns. Findings:
- **Mechanism — lease_synthesis.py:1936:** directional severity is NOT a calibrated label, it's the Pass-2
  VOTE COUNT (3-0→HIGH, 2-1→MED, 1-2→LOW); only 3-0 HIGH directional findings route to Risk. So Risk total
  = count of directional candidates getting unanimous Pass-2 confirmation that run.
- **Candidates STABLE** (28/28/28 across a triplet, 85-95% identity persistence) but 60-96% of persistent
  findings FLIP SEVERITY run-to-run, all at temperature=0.
- **Swing voter:** current-code pair — A (Claude 4.6) + C (Grok 4.3) confirm in both runs; role B (GPT-5.4,
  forced fallback bc gpt-5.5 returns bad format) is the SOLE swinger (no_mismatch/unclear→mismatch_confirmed),
  flipping all 26 directional to HIGH→Risk 36. (Older triplets: A also swings — general Pass-2 drift.)
- **Compound STABLE** — map-based severity (_severity_map, line 1528), 0 persistent flips. Clean control:
  the calibrated-map path is stable, the vote-count path is not. Compound is NOT the driver.
- Pattern: directional = #3 Pass-2 verification instability surfacing as #2 severity-flip, with a possible
  #5 infra flavor (B's `unclear` votes may be LOST via the _NO_OBJECT default = truncation/parse, the thing
  Step 370d's budget raise targeted). NOT candidate-gen / consolidation / upstream.
**TWO OWED MEASUREMENTS (need Tzvi's KEYED machine — no provider keys in sandbox):**
1. **Formal Track B** — freeze pre-Stage-7 input, replay run_synthesis ≥5× (harness _step370d_replay.py exists).
2. **THE CRITICAL FORK — split flips into genuine-verdict-change vs LOST-VOTE** using pass2_integrity match /
   _NO_OBJECT-default counts. This decides the FIX CLASS: #3 verification-stability (B truly changes its
   verdict at temp 0 → calibrate/stabilize) vs #5 infra (B's vote is dropped to truncation/parse and defaults
   to `unclear` → raise budget / fix parse). Completely different fixes. DO NOT patch before this split.
3. Quantify GPT-5.4 (Pass-2 role B) reproducibility specifically.
NO prompt/threshold/severity/Risk/Priority/routing change until #1-#2 separate #3 from #5.
**→ 375B-Q SPECCED (build_log/375B-Q_chat_instruction.md), read-only fork + counterfactual. KEY REFRAME
(GPT, accepted): this is a DESIGN defect, not just instability — directional Pass-2 confirmation COUNT is
rendered/routed as legal SEVERITY** (line 1936; 3-0→HIGH/2-1→MED/1-2→LOW, only 3-0→Risk). A directional
finding doesn't become more SEVERE because a 3rd evaluator agreed — it becomes better VERIFIED. The mapping
conflates epistemic support with substantive consequence — the SAME separation the project preserves
everywhere else (verdict distance epistemic; consequence substantive; action-type ≠ confidence-tier). This
category error persists even if GPT behaves perfectly tomorrow; the instability merely EXPOSED it. 375B-Q
is read-only: FIRST checks whether stored artifacts (pass2_integrity / raw status / _NO_OBJECT) can even
distinguish genuine-verdict-change from lost-vote (if not → mark UNAUDITABLE, keyed replay needed); then
classifies every Role B swing (genuine / lost-vote / candidate-match / routing / unauditable) and runs the
counterfactual (how many directionals enter/leave Risk SOLELY on a 3-0↔(2-1) tally flip; what the Risk
headline would be if integrity-failed votes were "not assessed" instead of silently non-confirming).
LIKELY ARCHITECTURE (doctrine question for later, NOT this step): directionals need TWO outputs —
materiality/impact AND verification strength — aligning Stage 7 with the epistemic/substantive split held
everywhere else. No behavior change; external-use pause stays.
 
**✅ 375-R DONE (SHA 7379dc0, read-only, production byte-identical at 609af43). FORK RESOLVED FULLY OFFLINE**
(stored _stage_data/synthesis_meta/{pass2_raw,pass2_integrity} made genuine-vs-lost auditable — no keys).
TWO-REGIME story:
- **Historical (370-era) = LOST VOTES, ALREADY FIXED.** Role A (Claude) returned EMPTY directional output
  (dir_object_count=0) → every finding silently "2 confirmed + 1 lost" → directional Risk suppressed to 0
  (integrity failure masquerading as "no risk"). Contained by Step 370d/372c (A now returns full output).
  The "raise budget / fix parse" branch is DONE.
- **Current code (030920↔0604) = GENUINE.** Integrity clean (0 unmatched, no truncation, parse OK). The
  14/14 Risk enter/leave flips are 100% genuine GPT-5.4 (Role B) verdict changes at TEMP=0
  (no_mismatch↔mismatch_confirmed), A/C stable, candidate identity unchanged. 0 lost votes.
- **CONSEQUENCE: an integrity fix will NOT stabilize today's headline.** The lost-vote problem is solved;
  what remains is a model genuinely non-deterministic on a verdict at temp=0. Can't parse/budget-fix "the
  model changed its mind." Real options are architectural: (1) stop using a single B verdict as load-bearing
  (stability-across-N-calls, or explicit uncertainty), and/or (2) stop mapping confirmation-count→severity
  at all (the design defect; survives any stability fix). Both branches CONVERGE on: directionals need TWO
  outputs — materiality/impact AND verification strength.
**OWED (in priority order):**
1. **INTEGRITY TRIPWIRE (proceed-able, cheap, defensive):** surface "verification incomplete" when
   unmatched_directional>0 / status!=complete / truncation, instead of silently down-counting a lost vote
   to non-confirming. Prevents A-empty (or any future loss) from masquerading as "lower severity / not
   Risk" again. Doesn't fix today's genuine instability but closes the historical failure mode permanently.
2. **KEYED frozen-input replay (needs Tzvi's machine):** measure GPT-5.4 (Pass-2 B) reproducibility
   directly (run_synthesis ≥5× on frozen pre-Stage-7 input; _step370d_replay.py harness) — quantify how
   unstable B actually is, and whether unanimity is an appropriate Risk gate at all.
3. **SPEC (don't build) the TWO-OUTPUT directional model:** separate impact/materiality from verification
   strength, so "Risk/HIGH" stops meaning "B agreed this run." This is the durable fix; both the genuine-
   semantic branch and the category-error reframing land here. Doctrine + design, gated on #2's data.
**THE DURABLE FINDING (independent of all instability):** confirmation count == legal severity == Risk gate
(line 1936) is a CATEGORY ERROR — verification strength mislabeled as substantive consequence. The dashboard
says "Risk/HIGH" for directionals when it means "this finding hit unanimous Pass-2 confirmation this run."
Same species as the 4 LP-06 overclaims, but STRUCTURAL (baked into severity mapping, not copy). Persists even
if B is perfectly stable. Compound findings are the clean CONTROL (mapped severity, line 1528, 0 flips).
External demo / Joshua use of Risk/Priority/Stage-7 directional totals STAYS PAUSED until the two-output fix.
 
**DOCTRINE FRAMING (Tzvi caught this, then TIGHTENED it — the precise, defensible statement):** First cut
was "the directional path does consensus voting, the one thing CAM is built to never do." That is TOO BROAD
and technically false — CAM legitimately aggregates evaluator outputs elsewhere (deterministic merge rules,
adjacency thresholds, mapped severity for compound). An opposing reader would refute it in one move. Do NOT
record the broad version. The doctrine is NOT "never compute from votes"; it is: preserve MEANINGFUL
disagreement; don't silence the minority; keep verification/confidence SEPARATE from legal consequence;
don't let agreement COUNT masquerade as substantive SEVERITY.
The precise violation (record THIS): **The directional synthesis path converts evaluator AGREEMENT COUNT
directly into substantive SEVERITY and action routing (line 1936: 3-0→HIGH→Risk, 2-1→MED, 1-2→LOW). Although
the underlying disagreement may remain recoverable in artifacts, the LAWYER-FACING outcome collapses
verification strength into legal consequence: the same one-sided issue is HIGH Risk only when unanimously
confirmed, downgraded/omitted when one evaluator dissents — so genuine interpretive variance controls
substantive classification instead of being preserved as a separate governed signal. Legal materiality is
never independently measured.** That survives a skeptic; the broad version doesn't.
 
**"DESIGN WAS RIGHT, IMPLEMENTATION FAILED" — de-romanticized (don't over-claim foresight):** The three
session findings are NOT uniformly "already invented correctly, implementation merely failed." Honest split:
- absence_adverse_to = a designed field left unused → genuine clean implementation gap (foresight WAS there).
- directional verification/materiality SEPARATION = CORRECTION (Tzvi remembered a prior design discussion;
  CONFIRMED in docs). This WAS designed: Patent_Supplement_2026_05_15b.md defines the full six-concept
  ontology (Severity/Confidence/Review-Priority/Distance/Materiality/Vote-Count) and states "collapsing any
  two produces incorrect governance." Its Phase 4 rule: "High-distance disagreement + high consequence =
  hard flag REGARDLESS of vote count" — consequence-first, vote count is NOT the gate. Its worked Example 3
  (2v1, distance=5, consequence=LOW, the PARKING-COST case) explicitly stays MODERATE, not HIGH — the exact
  "insignificant item must not become high risk" principle. So the directional path is NOT an undesigned
  area; it's the SAME gap as absence_adverse_to — designed doctrine (15b), unwired in ONE path. The
  directional path is a 2-D model (vote-count→severity) that 15b explicitly PROVED insufficient ("no
  two-dimensional model produces the correct output for all four examples"). The parking-spot-becomes-HIGH
  absurdity is the precise failure case 15b warned about, now live.
  (The two-output ELEMENT-merge instantiation is also already specced — Patent_Supplement_2026_05_17.md,
  element_merged_verdict + element_dissent_signal + criticality gate. 375E extends the SAME pattern to the
  directional/CPF path.)
- tie-break artifact = not just implementation-failing-to-follow-doctrine; it revealed that derived rollups
  THEMSELVES need provenance + guardrails (a new requirement, not a missed one).
PATENT FRAMING (defensible, NOT triumphalist): "Live validation revealed that CAM's established principles
require EXPLICIT APPLICATION at additional decomposition paths — perspective-aware absence routing,
provenance-aware derived signals, and separation of directional verification strength from substantive
consequence." That's true and sounds like engineering, not like winning an argument with your own source code.
**✅ 375E-PRE-Q (SHA 0783771, read-only) — LP-16 Parking is the POSITIVE CONTROL: reasoned, NOT stamped.**
Tzvi's screenshot (0604) showed LP-16 Parking RISK / Consequence:High / severe / PRIORITY REVIEW — looked
like the "insignificant item becomes high risk" defect. TRACE PROVED THE OPPOSITE:
- "High" is NOT the floor (LP-16 ∉ _HIGH_MATERIALITY_LPS={LP-27}), NOT the table (table said "low"). It's a
  GENUINE Stage-5e use_impact: 3-0 unanimous, confidence=assert, warehouse-specific reasoning ("truck and
  trailer staging areas critical for daily loading"). The ASSESSMENT OVERRODE the table's low. The card's
  Consequence badge reads use_impact.materiality (app.js:8068). This is CAM doing 15b CORRECTLY — reasoned
  per-tenant consequence beats the generic table. For a logistics tenant, parking-high is RIGHT, and CAM
  reasoned its way there.
- LP-16 stays Risk WITHOUT floor/artifact (genuine missing elements + assessed-high consequence).
- "severe disagreement" is GENUINE on 0604 (tie_derived_severe=FALSE, C diverges via clean plurality) but a
  TIE-BREAK ARTIFACT on 030920 — the disagreement/PRIORITY signal is run-fragile (same coverage-verdict-
  variance family as the directional instability), even though the CONSEQUENCE is solidly reasoned. Two
  signals on one card, different trust levels.
**SCOPE SHARPENED — the stamp-not-reason defect is ONLY on the FALLBACK path:**
- ASSESSED path (Stage 5e ran → use_impact exists) = reasoned, use-aware, overrides the table. ALREADY WORKS
  (LP-16). The consequence-by-mechanism defect is NOT here.
- FALLBACK path (Stage 5e absent/skipped — e.g. LP-06 at 40% non-present below the 50% gate — or defaulted
  via `… or "moderate"`) → falls to _HIGH_MATERIALITY_LPS floor / table / default = TABLE STAMPS consequence
  with NO reasoning. LP-27 = negative control (fell to floor); LP-06 = absent-assessment default.
375E coverage-materiality scope (NARROW, not "rip out tables"): (1) PREFER assessed use_impact whenever a
real Stage-5e assessment exists (already true for routing — make it the explicit rule); (2) on the FALLBACK,
absent-assessment must NOT silently become a table-stamped consequence — it should be "consequence not
assessed → attorney judgment" (already started in the 374V LP-06 card copy), NOT a floor stamp; (3) the
Stage-5e gate (50% non-present) that SKIPS assessable LPs like LP-06 is the upstream cause of fallbacks —
widening/fixing it reduces how often the fallback fires at all. This is the SAME principle as the directional
fix (consequence/severity must be ASSESSED, never stamped-by-mechanism) applied to coverage materiality.
**✅ 375F-Q (SHA 40afaa5, read-only) — is the use-driven "brings it home" message surfaced? ANSWER: shown
well WHERE it exists, but generated for only 28% of findings.** Tzvi's question: is the use-specific
consequence ("truck/trailer staging critical for daily loading") reaching the lawyer, and do we need to spell
out consequence-of-inaction or trust the lawyer to infer?
- **Surfacing (NOT buried — Chat's earlier 'buried' guess was WRONG):** use_impact.use_reasoning renders
  card-level by DEFAULT on the Key Issues main panel (buildItem, app.js:16660, the "⚠ Tenant-specific
  concern—…" note). The sidebar triage line (18222) and Evidence badge (8068) show only the bare
  "Consequence: High" label — quick-scan surfaces are bare, the card body is rich.
- **THE REAL GAP — non-computation, not burial:** of 29 non-N/A coverage LPs, only **8 (28%) have use_impact
  /use_reasoning at all; 21 (72%) have NO use_impact** (the defaulted/floor path, incl. Risk cards like
  LP-27). So the "brings it home" use-driven message is ABSENT for ~72% of findings because Stage 5e never
  assessed them (same 50%-gate coverage hole as 374P/375E-PRE-Q). CAM's most DIFFERENTIATING output
  (gap-tied-to-THIS-tenant's-operation) is under-GENERATED, not under-displayed.
- **Two consequence layers (answers the design question):** GENERIC consequence-of-inaction = UNIVERSAL via
  exposure_statement ("tenant may face parking restrictions without recourse") — renders on every card; a
  smart lawyer could mostly infer this; label suffices. USE-DRIVEN consequence (use_reasoning) = the
  can't-infer-without-knowing-the-client part, the actual product edge — and it's the one at 28%. So: don't
  spell out generic consequence MORE; make the USE-DRIVEN layer FIRE on more findings.
- **Dropped data (absence_adverse_to pattern again):** use_impact.confidence ("assert") + evaluator_agreement
  ("3-0") are computed and NEVER rendered — even the 28% assessed don't show how confident/agreed the
  use-assessment was.
**375E PRIORITY REDIRECT:** the highest-value fix is CLOSING THE STAGE-5e COVERAGE GAP (72% of LPs get no
use_impact), NOT UI re-surfacing. The use-driven "brings it home" message is the product edge and it's dark
on ~3/4 of findings. Widening the Stage-5e assessment gate (the 50% non-present threshold that skips LPs
like LP-06) is the lever. Secondary: surface confidence/evaluator_agreement on assessed cards; enrich the
bare sidebar/Evidence quick-scan surfaces. This is consistent across the session's findings: rich use-aware
data exists in the design; it's either unwired (absence_adverse_to), under-generated (use_impact 72% gap),
or mechanism-substituted on the fallback (floor/table). All trace to the same root — CAM reasons well when
it assesses, and falls back to stamps/silence when it doesn't.
 
**375F-Q ADDENDUM (Tzvi: "looks a little hidden if you ask me") — RENDERED ≠ PROMINENT.** Second screenshot
confirmed: the use-driven concern note ("truck and trailer staging areas critical for daily loading") IS
rendered card-level by default (app.js:16660) — but it is VISUALLY BURIED: a small orange-tinted footnote at
the BOTTOM of the card, below the fold, beneath the element-verdict table, in smaller text. The single most
valuable sentence on the card (the gap tied to THIS tenant's operation = CAM's product edge) is styled as
the LEAST important element. The card's information architecture is INVERTED: mechanical detail (per-element
evaluator votes, citations) is loud + central; the use-specific judgment is a quiet footnote. A lawyer
triaging wants: (1) what's the issue, (2) why it matters to MY client, (3) what to do — the card leads with
"how the sausage was made" and ends with "why it matters." This is a DISTINCT finding from the
compute-gap (375F-Q): not "is it computed/rendered" (yes, for the 28%) but "is it given prominence worthy
of its value" (NO). Connects to the parked UI-overhaul thread (reorganize for lawyer workflow). FIX (UI/IA,
separate from the Stage-5e compute-gap fix): promote use_reasoning above/into the card header region for
assessed findings — the use-driven "why it matters to you" should be the SECOND thing read (after the
issue title), not a bottom footnote. Element-verdict mechanics belong below it. Spec as
375G (UI prominence) — independent of 375E (compute more use_impact) and the directional work.
 
**→ 375G SPECCED (build_log/375G_chat_instruction.md) — bounded Client Impact block, GPT's middle path.**
NOT a cosmetic note-move, NOT a sweeping redesign that hides evidence. Insert a CLIENT IMPACT block under
the title/badges, ABOVE the element table: leads with use_reasoning (when present) + the existing
exposure_statement; remove the duplicated bottom footnote. HARD CONSTRAINTS: (1) PROMOTE/ORGANIZE EXISTING
FIELDS ONLY — generate NO new prose, no model call; (2) when use_reasoning absent (the 72%), show ONLY the
generic exposure_statement, do NOT fabricate tenant-specific impact (the "not assessed" fallback wording
waits for 375E); (3) KEEP the element evidence table + lease text VISIBLE — do NOT collapse/demote them.
RATIONALE for (3): we are CURRENTLY finding governance defects (tie-break, directional instability,
per-evaluator splits) by inspecting those very details — CAM has NOT earned the right to hide evidence while
Stage 7 / priority / fallback materiality are under investigation. Re-order emphasis (judgment first), don't
hide mechanism. SEQUENCING (GPT): do 375G BEFORE widening Stage 5e — else 5e generates more of CAM's best
insight only to bury more of it. Build the destination before producing more of what goes in it. Display
only; no computed-value change.
 
**✅ 375G SHIPPED (SHA b053c80, app.js v466 / style.css v400) — Client Impact block live, verified on screen.**
buildItem now renders a prominent CLIENT IMPACT block immediately under the title/badges, ABOVE the element
table: leads with use_reasoning (when present) + exposure_statement; bottom footnote + below-table cv-item-stmt
removed (no dup); .cv-client-impact style is judgment-prominent (indigo accent, 0.92rem reason text, not the
old 0.72rem footnote). Constraints honored: promote-only (esc'd verbatim, no new prose/model call); no
fabrication when use_reasoning absent (block shows only exposure_statement — validated LP-27/LP-08); element
table + lease text still visible below; zero computed-value change. Tzvi screenshot (LP-14 Force Majeure)
confirms LIVE: bold tenant-specific line up top under title, exposure prose beneath, element table below. The
card hierarchy is now judgment-first — the destination is built, so when 375E widens Stage-5e use_impact the
new insight lands prominently instead of in a footnote.
 
**THE ORTHOGONALITY PRINCIPLE (Tzvi's framing question — the design north star for 375E):** "Is Risk solely a
property of evaluator votes, or of the actual risk? Is 3-yes on a parking spot the same as 3-yes (or even a
split) on a severe issue?" Answer: under CURRENT code, Risk is SOLELY a property of the votes — directional
severity = vote count, materiality NEVER enters. So YES, today a 3-0 parking-spot asymmetry = the same
HIGH/Risk as a 3-0 uncapped-indemnity asymmetry, and a 2-1 on the catastrophic issue is DEMOTED below the
trivial unanimous one. That is the defect in one sentence: a trivial issue everyone agrees on outranks a
severe issue with one dissenter, because legal weight isn't in the formula. The fix is ORTHOGONAL SEPARATION:
materiality (how much it matters, from legal consequence) and verification strength (how sure we are, from
evaluators) are INDEPENDENT axes; action routing is materiality-FIRST with verification shown alongside.
Parking spot @3-0 → low materiality → Improvement/minor; indemnity @2-1 → high materiality → stays Risk with
"one evaluator disagreed" as a SEPARATE confidence signal, not a demotion. OPEN QUESTION for 375E/Code: do
directional findings ALREADY carry a materiality field that synthesis ignores (like absence_adverse_to was
unwired) — or does directional materiality need to be assessed fresh? That distinction sets the fix size;
confirm against the finding schema before drafting 375E.
 
**KEY FRAMING CORRECTION (GPT, accepted):** "you can't engineer determinism into a model that changes its
mind" is true but backwards as a diagnosis. You can't make GPT-5.4 deterministic, but engineering a STABLE
GOVERNED SYSTEM around an UNSTABLE evaluator IS THE ENTIRE POINT OF CAM. 375-R didn't find a fatal model
limitation — it found the ONE place CAM stopped governing and promoted a raw vote tally straight onto a
lawyer-facing Risk decision without the governance layer present everywhere else. The fix is not "stabilize
B"; it's "govern B like every other evaluator." A governance gap, not a model defect.
 
**✅ 375C SHIPPED (SHA b1ce16f, backend + app.js v465, PROVISIONAL) — Pass-2 integrity tripwire.** Closes the
HISTORICAL failure mode: a missing/empty/truncated/unmatched Pass-2 role output is no longer a silent
negative vote. When a role is `_NO_OBJECT` for a candidate, the directional finding → `verification_incomplete`
(distinct state), severity → VERIFICATION_INCOMPLETE (overrides AFTER the line-1936 map, which is UNTOUCHED),
the dead role → `not_assessed`, and `evaluator_agreement` reports USABLE ROLES ONLY (a 2-of-3-usable result
reads "2 confirmed, 1 incomplete," NEVER a fake "2-1 disagreement"). Raw cause (empty_directional_output,
dir_object_count, model) preserved for Audit. UI v465 renders a "⚠ Verification incomplete" badge.
VALIDATED 6/6 against the real builder over stored artifacts (no keys): fires 28/28 on historical A-empty
runs (s370r1, 370c_H1; A=not_assessed, honest usable tally, never silent-MEDIUM/0-Risk); 0 findings change
on the clean current pair (030920/0604) — PROVES it's scoped to the failure mode, not the GPT-5.4 flips;
clean 3-0 stays HIGH, clean valid 2-1 stays MEDIUM (semantic-flip case untouched); compound unchanged.
Effect on NEW runs (current stored findings carry verification_incomplete=False, unchanged). Demo/Joshua
use of directional Risk STAYS PAUSED — this removes silent suppression but does not validate the headline.
 
**375D = KEYED REPLAY (needs Tzvi's machine, after 375C):** frozen pre-Stage-7 input — (1) ≥5 full Stage-7
replays for end-to-end stability; (2) targeted Role B ~10 calls/candidate across entered/exited-Risk +
stable-unanimous + stable-non-unanimous candidates, reporting mismatch_confirmed/no_mismatch/unclear counts
+ integrity per call + BORDERLINE-finding vs BROADLY-UNSTABLE-evaluator + two-output counterfactual routing.
This chooses the governance POLICY, not just confirms instability.
**✅ 375D RESULTS IN (Tzvi ran both on keyed machine; build_log/375D_full_replay.json + 375D_roleB.json).**
[CORRECTED after GPT review — Chat's first-pass headline "the instability is single-evaluator B variance" was
an OVERCLAIM. "B is the SWING ROLE in the full pass" is true; "B is unstable" is FALSE — the roleB file shows
the opposite. Corrected reading below.]
FROZEN run 52adbf. ALL passes integrity-clean (0 verification_incomplete, no truncation/unmatched/parse-fail).
- **Full replay (5 passes, byte-identical input):** 3-0 Risk count per pass = **21, 12, 7, 15, 13** (7–21
  threefold spread on IDENTICAL input). Compound STABLE at 6 every pass (mapped-severity control). Of the 20
  candidates present in ALL five passes: C/Grok stable on all 20; A/Claude varied on 1; **B/GPT-5.4 varied
  on 17 of 20**. Only LP-14/22/27 were HIGH in all five. So B is the SWING ROLE driving the directional Risk
  volatility INSIDE the full pass.
- **SECOND instability (Chat under-reported this; GPT caught it):** the directional candidate COUNT itself is
  not stable — passes 1/2/3/5 = 26 findings, **pass 4 = 20** (six vanished: LP-03/06/11/17/18/24). Not just
  severity-flipping on a fixed set — candidate presence/retention also varies run-to-run.
- **Targeted role-B (10×/candidate, 9 sampled candidates, ISOLATED single-candidate prompt):** 89/90 calls =
  mismatch_confirmed, 1/90 = unclear, 0 no_mismatch, 0 integrity-fail. Four of five sampled FLIPPERS =
  **10/10 confirmed** in isolation; the fifth 9/10; all four stable-unanimous controls 10/10. **B is NEARLY
  DETERMINISTIC in isolation** — the OPPOSITE of "B is unstable."
- **THE CORRECTED DIAGNOSIS:** B is the swing role in the FULL Stage-7 pass but near-deterministic on the
  SAMPLED candidates in ISOLATION. → LEADING HYPOTHESIS is context sensitivity; the PRECISE cause is NOT yet
  proven. [GPT second correction — Chat overclaimed twice more, both fixed here:]
  (a) "the fault is BATCH context" is NOT established — only "instability appears in full-context, doesn't
  reproduce in isolation." The full-vs-isolated gap could be batch SIZE / ORDER / NEIGHBORS / a PROMPT-FORMAT
  diff between the full-pass and isolated harness / upstream candidate-set instability / a combination. Batch
  context is the leading hypothesis, not the verdict. (b) the isolated sample is INCOMPLETE: roleB tested
  only 5 flippers (LP-01/02/03/04/07) + 4 controls, NOT the 14 available flippers. So the proven claim is
  "every SAMPLED flipper was stable in isolation," NOT "all flippers are stable in isolation" — 9 flippers
  untested. Do not build a fix around the 5 friendly witnesses. CAVEATS unchanged: n=1 contract,
  direction-only, never a CAM metric/patent number.
- **TWO DISTINCT INSTABILITIES — MUST NOT BE BLURRED (GPT's load-bearing constraint):** (1) candidate-SET
  instability (pass 4 = 20 not 26; LP-03/06/11/17/18/24 vanished); (2) verification/routing instability
  (HIGH/Risk swings among PERSISTENT candidates). If candidate generation is allowed to float in 375D-2, you
  will mistake "which candidates arrived for verification" for "batching changed verification." 375D-2 Track A
  uses a FROZEN candidate set to test Pass-2 sensitivity; Track B SEPARATELY audits the vanished six. Never mix.
**→ 375D-2 SPECCED (GPT, REQUIRED before building the directional redesign) — BATCH-CONTEXT SENSITIVITY AUDIT.**
375D establishes the NEED for the two-output architecture but exposes a new upstream question: is full-pass
Role-B instability caused by BATCHED multi-candidate evaluation rather than candidate-level uncertainty?
Same frozen Stage-7 input + same role-B model, compare for the same representative candidates: (1)
single-candidate prompt repeated; (2) original full batch repeated; (3) fixed small batches (e.g. groups of
5) repeated; (4) same batch with SHUFFLED order; (5) same candidate embedded in DIFFERENT neighboring sets.
Measure per candidate: confirmed/no_mismatch/unclear; changes-only-when-batched?; order-sensitive?;
set-size-sensitive?; is only B sensitive or do A/C show smaller versions? This decides whether the directional
verifier needs per-candidate evaluation / smaller batches / stronger prompt isolation / OR merely the
separate verification-materiality outputs. DO NOT treat 375D as the final basis for the two-output build yet.
 
**→ 375D-2 HARNESS SPECCED (build_log/375D-2_chat_instruction.md) — Code writes, Tzvi runs keyed.** TWO
SEPARATE TRACKS (never blurred): Track A = FROZEN canonical candidate set, Role B under 5 conditions (single
/ full batch / small batches / shuffled order / neighbor-perturbation), ≥10 repeats, capturing position +
neighbor ids + prompt hash per call — MUST include ALL 14 flippers (not just the 5 sampled) + controls +
any genuine 2-1 split. Track B = SEPARATELY audit why pass 4 lost 6 candidates (diff Pass-1→Pass-2 artifacts;
never generated / filtered / deduped / gated / unauditable). Output = per-candidate stability table, whether
isolation-stability generalizes 5→14, which factor (size/order/neighbor/prompt-mismatch) drives B variance
(inconclusive ALLOWED), separate candidate-loss explanation, implementation OPTIONS only. Gates the STABILITY
fix; does NOT gate the two-output DOCTRINE (draftable now).
 
**✅ 375D-2 RESULTS IN (Tzvi ran both tracks keyed; 375D2_trackA.json + 375D2_trackB.json; K=10, all 14
flippers in canonical set). THIS OVERTURNS the 375D "near-deterministic in isolation" reading.**
The 375D roleB sample (5 flippers, all stable in isolation) was UNREPRESENTATIVE. With all 14 + controls:
- **Isolation is NOT uniformly stable.** LP-02 isolation = 5 mismatch_confirmed / 5 no_mismatch — a literal
  COIN FLIP on the same candidate asked alone. LP-25 = 7/3, LP-24/15/28/30 = 9/1. So B is genuinely
  borderline on SOME candidates even in isolation; "B is deterministic alone" is false beyond the 5 sampled.
- **The dominant pattern is CONTEXT-SENSITIVITY, and it's not simple batching.** Per-candidate verdict
  distribution swings wildly BY CONDITION on the same frozen candidate:
  - LP-01: isolation 10-confirmed → full_batch 4-confirmed/6-unclear → small_batch 10-UNCLEAR → neighbor
    9-confirmed. Same clause, four conditions, four different verdict profiles.
  - LP-03: isolation 10-confirmed → full_batch 10-UNCLEAR → small_batch 10-confirmed → neighbor 10-confirmed.
    Full-batch ALONE flips it entirely to unclear; small-batch restores it.
  - LP-18: isolation 10 → full_batch 4/6-unclear → small_batch 10. Same shape: FULL batch degrades it.
  - LP-02: isolation 5/5 → full_batch 8-confirmed → neighbor 10-confirmed. Here batching STABILIZES it.
- **No single knob explains it.** Sometimes full-batch → unclear (LP-01/03/18); sometimes full-batch is
  fine and isolation is the unstable one (LP-02); small-batch sometimes rescues (LP-03) sometimes degrades
  (LP-01). Shuffled-order shows high unclear rates on several. So the driver is COMPOSITION/CONTEXT broadly
  (what else is in the prompt + how it's arranged), NOT a clean "big batch bad" rule. The leading hypothesis
  is confirmed as CONTEXT-SENSITIVITY but the SUB-cause is mixed/per-candidate — there is no one switch to
  flip. Stable-unanimous controls (LP-05 etc.) largely hold across conditions (LP-32 = 10/10/10/30/10 perfect).
- **integrity_fail appears rarely (LP-21/24/25/28 small_batch, 1 each)** — those are 375C's territory, correctly
  rare and separate.
**TRACK B — candidate-count loss is NOT a hidden filter; it's Pass-1 generation variance.** Re-running Pass-1→
Pass-2 5×: counts 26/24/26/26/26. Of the 6 vanished LPs, fate tally: LP-03 in_final 4× + never_generated 1×;
LP-17 in_final 4× + never_generated 1×; LP-06/11/18/24 in_final 5/5. So candidates vanish because **Pass-1
sometimes doesn't FLAG them** (pass1_mismatch_flag_evaluators drops to 0 — e.g. LP-03 run 2), NOT because a
downstream filter/dedup drops a generated candidate. The candidate-SET instability is upstream evaluator
flag variance at Pass-1, a DIFFERENT instability from the Pass-2 verdict variance. Confirms the two were
correctly kept separate — conflating them would have mis-attributed Pass-1 flag-drop as Pass-2 batch effect.
 
**CORRECTED DIAGNOSIS (supersedes the 375D version):** B's directional verdict is context-sensitive in a
PER-CANDIDATE, MIXED way — not a single batch-size law, and NOT "stable in isolation" (LP-02 is 50/50 alone).
Some candidates are genuinely borderline (isolation already splits); others are stable alone but destabilized
by full-batch context (LP-03/18); a few are stabilized by context (LP-02). Plus an independent Pass-1
flag-generation variance that changes WHICH candidates exist.
[GPT THIRD-ROUND CORRECTIONS — Chat overclaimed AGAIN, three fixes:]
(1) NOT "no stability knob can exist." Accurate: no TESTED context (isolation/full/small/shuffled/neighbor)
    yields a UNIFORMLY reliable signal, and NONE can rescue 3-0→HIGH→Risk. A better prompt/batch design MIGHT
    improve stability — but even a more stable vote is still verification strength, not severity, so it can't
    rescue the current architecture regardless. Don't claim impossibility; claim the tested set fails + the
    architecture is wrong in kind.
(2) NOT "instability confined to the borderline set." Chat read the controls too fast. ≥7 of 12
    "stable-unanimous" controls ALSO vary under some tested context: LP-17 collapses to 3-confirmed/7-unclear
    in full batch; LP-05/LP-10 = 8/2 full batch; LP-14/LP-22/LP-29 wobble in isolation; LP-19 mixed under
    full/small/shuffled. So "stable vs borderline" is NOT a property the system currently knows — a finding
    can look stable in two stored runs and wobble under another legitimate prompt context. Do NOT carry a
    "we know which are stable" model. LP-32 IS stable across all conditions (10/10/10/30/10), which proves
    the harness detects real per-candidate behavior, not generic noise.
(3) Track B is NARROWER than Chat stated. It REPRODUCED Pass-1 recall failure for LP-03 + LP-17 only (count
    26→24; those two had pass1_mismatch_flag_evaluators=0 in one run). It did NOT reproduce the original
    six-LP / 20-count disappearance — LP-06/11/18/24 stayed present all 5 runs. Careful statement: Pass-1
    generation variance is a CONFIRMED MECHANISM of candidate loss (reproduced for 2 LPs); the full earlier
    six-LP event is NOT yet reproduced or fully attributed. A Pass-2 redesign does NOTHING for a candidate
    that never reaches Pass-2 — so candidate recall is a SEPARATE defect that must be governed separately.
 
**→ 375E ARCHITECTURE DOC WRITTEN (build_log/375E_architecture_doc.md) — DOCTRINE + OPEN-POLICY, NOT a
production spec.** Per GPT: 375D-2 established the redesign PRINCIPLE, NOT the routing policy. Doc locks the
SETTLED doctrine (vote=verification not severity; remove 3-0→HIGH→Risk; unanimity not required for material
finding; materiality assessed independently; disagreement+integrity stay visible; Pass-1 recall governed
separately) and explicitly LEAVES OPEN the routing formula — "materiality gates Risk" is incomplete (a
high-consequence finding with NO adequate support must not auto-Risk). Routing policy table (consequence ×
support-state) must be chosen by COUNTERFACTUAL testing against the canonical set + frozen artifacts before
implementation. Executable split: 375E-DIR (directional redesign + Pass-1 recall, gated on counterfactual);
375E-COV (widen Stage-5e, independent, partly keyless-modelable); 375G (shipped). Pause holds until BOTH
recall AND routing no longer depend on evaluator-support collapse.
 
**WHAT SURVIVES REGARDLESS (the structural doctrine — unchanged by all the above):** agreement strength cannot
masquerade as legal severity. EVEN IF B were perfectly stable, 3-0→HIGH/Risk and 2-1→MED/not-Risk is wrong
IN KIND — unanimity measures verification support, not how harmful the one-sided term is to the tenant. So the
two-output redesign (materiality gates Risk independent of vote; verification reported separately) is still
required. What 375D-2 changes is the STABILITY fix: it may NOT be "replace/re-call GPT-5.4" but "stop
evaluating directional candidates in a big batch." Two distinct problems: (a) doctrine (vote≠severity) —
settled, fix known; (b) stability (batch-context variance) — needs 375D-2 to locate before fixing.
- NOTE re 375C: every pass was integrity-clean (B genuinely answered, just differently across contexts) —
  tripwire correctly does NOT fire. 375C scope confirmed correct: different failure mode from this one.
**TARGET REDESIGN (375E, spec-after-375D, do NOT build yet):** directionals get SEPARATE fields —
directional_verdict (confirmed/unconfirmed/disputed/verification_incomplete); verification_strength
(unanimous/majority/split/incomplete); materiality (high/med/low from legal consequence, NOT vote count);
recommended_action (Risk/Review/Improvement/Addressed from materiality + governed confidence). Candidate
policy: high-materiality one-sided term stays actionable (Risk/Review by consequence) even with split/
unstable verification; unanimity raises VERIFICATION confidence, never legal materiality; incomplete output
= verification_incomplete, never silent dissent. Preserves action-type doctrine: high-consequence exposure
actionable even with imperfect epistemic confidence, confidence shown SEPARATELY.
 
**✅ 374Y-Q DONE (SHA eb0d3f3, read-only, production byte-identical).** ALL 4 candidates pass on both runs:
ΔRisk=0, ΔPriority=0, ZERO genuine tenant-adverse findings lost. The polarity fix does not disturb the Risk
surface at n=2. Details:
- **C3 ≡ C4** on live data (no LP became Risk SOLELY from an opposite-polarity absence, so C4's extra guard
  never fires). **C2 vs C3 differ on exactly ONE LP: LP-01** — C2 flips it on a NULL-polarity element
  (`accepted_payment_methods`), i.e. silently calls an ambiguous absence favorable; C3 keeps it reviewable.
  This is the "don't auto-flip ambiguous" guardrail proving live. → **RECOMMEND C3** (flip clearly-favorable,
  keep null/contextual reviewable).
- Only clean favorable flip: **LP-08** (partial→covered, Improvement→Addressed; sole missing element is a
  landlord-protective insurance certificate; never was Risk). All movements are in Improvement/Addressed
  tiers — lawyer-facing Risk surface unaffected at n=2.
- **LP-27 never moves** (self-help + floor → stays partial/Risk). Confirms 374W/374X.
- METHODOLOGY: Code caught a fidelity bug in its OWN recompute — LP-14/22/28/32 are review_needed via
  unclear/dispute paths (not missing-count), so polarity can't move them; added a governance gate (only LPs
  where re-derived state reproduces production coverage_state can move) and discarded the false movements.
  Same self-correction discipline as the LP-32 scoping reversal.
**⚠️ LANDMINE — rent_acceleration/recapture (must be handled IN 374Z, do NOT "tidy" separately):** the
`_HIGH_MATERIALITY_ELEMENTS` strings "rent acceleration"/"recapture" (landlord-favorable) currently have NO
305-label match, so they CANNOT fire. LP-11.rent_acceleration_remedy (landlord, high, live-missing) escapes
the materiality bump ONLY by this label mismatch. If anyone "aligns" those strings to the 305 labels (looks
like harmless cleanup), it becomes a LIVE landlord-favorable→high-materiality→Risk FALSE POSITIVE. The
materiality-set polarity fix must be done in the same measured 374Z step. (The opposite-polarity entries
that DO match — lien_discharge, unamortized_ti, landlord — are MEDIUM → Improvement only.)
 
**374Z — DONE & DEPLOYED (SHA 609af43).** See the ✅ 374Z block above. C3 polarity correction enforced,
landmine neutralized, 6/6 fixtures + exit criteria green before push. Effect shows on next pipeline run.
Favorable-position SURFACING remains a separate later decision (374Y-Q funnel data + Joshua), NOT built.
 
---
 
## Active queue
 
```
NEXT0 CORRECTNESS FOLLOW-UP (proceed-able, fixture-gated like 374Z — NOT contract-gated):
      ⚠️ DEFERRED behind 375-Q (capture-before-change): do NOT merge until the 375-Q instability baseline +
      Stage 7 frozen-input replay artifacts are captured on commit 609af43, so NEXT0's merge can't
      contaminate attribution. Ready + blocked for hygiene only; proceeds after baseline unless it changes
      Stage 7 input fields.
      COVERAGE-STAGE PERSPECTIVE THREADING. 374Z fixed polarity but the coverage stage runs
      perspective-blind — assess_coverage has no perspective param (perspective enters only at exposure),
      so derive_lp_state DEFAULTS to tenant. Correct for ALL current tenant runs/fixtures, WRONG for
      landlord/neutral reviews. Thread perspective from cfg → assess_coverage → derive_lp_state +
      _classify_materiality. Gate: a landlord-perspective fixture (a missing TENANT protection should be
      landlord-FAVORABLE under landlord perspective; a missing LANDLORD remedy should be landlord-ADVERSE).
      Until this lands: do NOT trust coverage_state polarity on a landlord-perspective review.
      This is a CORRECTNESS repair (same class as 374Z) — proceeds on a fixture, not on more contracts.
DONE  Step 373 chain + 374/374B/374C COMPLETE. 373(→373G) reconciled counts within the old layout;
      374 made the Overview FINDINGS-FIRST (Action Summary = 4 buckets, single-source w/ sidebar,
      census removed, "Priority Risks" relabel, disputed-protection subtype surfaced, Addressed
      suppression, gov-law + conflict scoped to selected contract — proven on mixed fixture); 374B-F
      settled all copy (canonical period-terminated gloss set via shared CAM_RISK_GLOSS constant;
      lawyer-facing subtype lines); 374G gave Needs Review sidebar sub-headers (Coverage Questions /
      Possible One-Sided Terms / Conflicting Reading) single-sourced via shared _reviewSubtypeOf —
      sidebar now symmetric with Risk. app.js v460. UI thread CLOSED + copy COMPLETE. NEEDS VISUAL
      CONFIRM (hard-refresh eyeball — numbers/strings replay-validated, CSS not).
      Recorded follow-ups (own read-then-spec, neither urgent): (1) _computeRiskCounts doesn't iterate
      Mode-A DEVIATION Risk items — separate unmeasured path.
      Plus: disputed-protection click-through (Evidence view should show "evaluators materially
      disagreed; CAM preserved the split" + citations — the right home for that explanation, not a
      tooltip); responsive/mobile check on Action Summary Risk card if it ever shows without sidebar.
NEXT  GOVERNANCE FIX (measured, NOT same-session): the 374K finding — LP-level "severe" disagreement is
      often a deterministic plurality-rollup tie-break artifact (9/13 severe cases over 2 runs), amplified
      by the ordinal ladder; hard_flag can also fire from a DEFAULTED consequence (use_impact missing →
      `or "moderate"`). Contaminates Needs Review (1-2/run) and Priority Risks (clean on 030920, 2 artifacts
      on 181402 — NOT structurally safe). UI honesty SHIPPED (374M v461). Two design questions before any
      logic change, both needing >n=2: (a) should a pessimistic 2-2 element tie produce max-distance
      "severe" at all / is plurality-rollup the right LP-distance abstraction; (b) consequence_status
      not_assessed state so a default can't masquerade as assessed + drive escalation. Investigate WHY
      LP-06 lacks use_impact (Stage 5e gap) separately. See Docs/Finding_2026_06_03_*.md + 374K_governance_finding.md §8.
      Executive-copy work on Overview counts PAUSED until this lands.
NEXT2 C characterization, HALF DONE — SEPARATE question from the governance fix (do NOT merge them).
      Joshua answers MATERIALITY/USEFULNESS (is HVAC responsibility legally important here; is this lease
      commercially problematic for the tenant; would an attorney want this reviewed). He does NOT validate
      the COMPUTATION (should a tie-broken plurality rollup produce distance-5; should unassessed
      consequence drive hard_flag; should a derived LP signal override element evidence — those are
      architecture questions for the governance fix). IMPORTANT: do NOT use Priority-Risks or
      conflicting-reading outputs as validated signals in a Joshua review until containment is in — they
      are contaminated. Stability half encouraging (030920 diff: C's substantive
      missing-calls did NOT flip present↔absent). REMAINING: (a) is C's strictness CORRECT —
      a CRE attorney (Joshua) on crisp disputed elements (LP-10, LP-16, LP-02); a lawyer call,
      not engineering. EP/IP-collapse LOWERED priority (7/36 jitter).
THEN  Multi-contract stability validation (the high-value generality work; needs other contracts).
      Boundary-fragile: re-run 372BU_prevalence.py on first lightly-flagged contract OR on
        matched-run observed-instability data; spec ONLY if a real proof case appears.
      dispute_signal → review_needed threshold tuning (governance TUNING, not bug; record only;
        revisit after behavior fully understood — see 030920 diff section).
      Stage 7 observability follow-up (fallback_reason into synthesis_meta — deferred, grab next run)
      372b pool-fallback adapters not instrumented for real usage (estimate-only — flagged)
      Overview redesign resumption (parked at original session start)
      Tab-count reduction: fold Contract Interaction → Contract View → 5 tabs
```
 
---
 
## Tab architecture (unchanged)
 
```
Overview | Key Issues | Contract View | Contract Interaction | Evidence | Audit
```
Target: 5 tabs — fold Contract Interaction → Contract View.
 
---
 
## Standing open items (non-372)
 
- **API cost note (2026-06-05):** the live cost driver is CLAUDE CODE agentic file-reading (cache-read
  volume from re-reading app.js + large artifacts across long sessions; ~$25-50 on heavy Code days), NOT the
  VeredAI lease pipeline. No breach — verified against the usage CSV (two keys, both Tzvi's:
  `VeredAI` + `claude_code_key_zvido2_beqc`; no foreign activity). Code caches AUTOMATICALLY (the 21M
  cache-read tokens ARE caching working — the platform "not using prompt caching" screen was filtered to the
  Default/VeredAI workspace, not the Claude Code workspace). LEVERS: scoped/shorter Code sessions; push
  read-only diagnostics into standalone Python scripts Tzvi runs (zero Code context cost) rather than Code
  reading artifacts into context to reason over them.
- **Pipeline prompt-caching — DEFERRED (do NOT add during active development):** `cache_control` on the
  VeredAI pipeline (system prompt / rubric / shared lease text across the 3 evaluators) could cut input cost
  50-90% — but ONLY once those chunks are STABLE and reused at VOLUME. During development the prompts/schema/
  rubric keep changing (cache invalidates every edit) and throughput is a few Meridian validation runs, so
  caching would be effort that keeps resetting. Revisit when (a) prompts/schema stabilize AND (b) real lease
  throughput replaces Meridian re-validation. Production optimization, not a development one.
- Patent non-provisional — deadline ~Nov 11 2026; attorney conversation recommended before Sept
- Architecture A Phase 2 standalone patent supplement — flagged gap, before attorney conversation
- Stage 5d formalization — **ENABLED** (`STAGE_5D_ENABLED = True` since Step 303, 2026-05-04).
  Confirmed product-behavior: generic/absent permitted-use clause → no use_profile →
  Stage 5e-F runs keyless → P2'' Rule 1a routes all directional findings to
  review_needed/consequence_not_assessed (zero directional Risk by construction).
  (DEF-008 doc correction, 2026-06-10)
- Architecture B / D / E — deferred (E = Temporal Governance / Calibration Drift; see arch plan)
- **Email notifications broken — SendGrid 401 + SMTP 535 BadCredentials** (confirmed still broken
  in the 2026-06-01/02 runs; deferred by Tzvi — "deal with email another time")
---
 
## 375 — ONE-SIDEDNESS vs PRESENCE conflation (Tzvi conceptual finding, code-confirmed; NOT YET run-verified)
 
Tzvi's question: "if the clause is one-sided, what does that have to do with whether it's present or not?"
Reading the Stage-7 directional prompt (_EVALUATOR_SYSTEM in lease_synthesis.py) confirms a real conflation
PLUS a bypass. Two distinct failure modes, same root.
 
**1. CONFLATION (confirmed in the Q2 prompt text):** Q2a asks "Does a protection/remedy/default framework
EXIST, and does it protect the correct party against the correct risk? yes/no/unclear." The `no` definition
is literally "protection runs toward the wrong party, OR IS ABSENT." mismatch_flag fires when Q2a=no. So
PRESENT-BUT-TILTED and ABSENT collapse into the SAME no/mismatch_flag. The directional path cannot
distinguish "clause is here but one-sided" from "clause is missing." Presence and direction are FUSED into
one question. (Example: "no sublet w/o landlord sole discretion" = present+one-sided → Q2a=no; a missing
sublet clause → also Q2a=no. Same bucket.)
 
**2. BYPASS (the skip Tzvi was hunting):** Stage 7 only runs on FLAGGED LPs (_FLAGGED_STATES = missing /
partial_material / partial_typical / review_needed). A FULLY-COVERED LP is NOT flagged into Stage 7. So a
clause that is PRESENT, element-complete, but SUBSTANTIVELY ONE-SIDED CAN bypass directional review.
[GPT NARROWING — Chat overclaimed the bypass; do NOT assert every present-one-sided clause scores "covered"
and therefore needs an all-LP directional pass.] In a CORRECT schema, some hostile present terms SHOULD
already fail a protective element (e.g. if the expected element is "consent not unreasonably withheld,"
then "landlord sole discretion" should score DEFICIENT, not covered). So a "sole discretion" clause passing
as covered indicates ONE OF THREE distinct defects, each with a DIFFERENT fix — the audit must distinguish:
  (1) SCHEMA defect: the rubric only checks whether a consent standard is MENTIONED, not whether it protects
      the tenant → fix the element schema. (NOT fixed by running Stage 7 on every covered LP.)
  (2) EVALUATOR defect: schema is correct, but the evaluator treated hostile language as satisfying the
      protective element → fix the prompt/evaluator. (NOT fixed by another pass that inherits the blindness.)
  (3) TRUE independent-directionality gap: all defined elements genuinely satisfied, yet the clause is still
      materially one-sided → THIS supports an independent one-sidedness candidate path.
Chat's earlier formulation jumped to (3) as the diagnosis; which defect actually operates is UNMEASURED.
ROOT (still valid): the pipeline treats one-sidedness as a downstream property of coverage gaps, when it is
an INDEPENDENT contract-position property that may arise from missing protections, HOSTILE PRESENT LANGUAGE,
DISPROPORTIONATE remedy structures, or CROSS-CLAUSE interactions. Candidate generation must EVENTUALLY be
able to originate a directional finding from PRESENT ADVERSE LANGUAGE, not only from coverage gaps — but
that does NOT automatically mean a whole-lease model pass; it may mean schema/evaluator fixes that let
coverage emit directional candidates correctly.
 
**STATUS: mechanism confirmed by code read; NOT yet run-verified.** Have NOT confirmed that a real
present-and-one-sided clause actually scored "covered" and bypassed Stage 7 in the Atlas Meridian run — the
sublet case is ILLUSTRATIVE. Empirical step (if pursued): scan 0604 coverage output for any LP scored
"covered"/element-complete whose CONTENT is landlord-favorable, and confirm it never reached Stage 7. Until
then this is a code-level finding, direction-only, n=0 on prevalence. Do NOT cite as a CAM metric / patent
record.
 
**IMPLICATION for 375E:** the two-output redesign (verification vs materiality) addresses findings that ARE
flagged. It does NOT by itself fix the BYPASS — a one-sided present clause that never enters Stage 7 gets no
directional output to redesign. So "assess one-sidedness independently of coverage gap-state" is a SEPARATE
architectural item from the verification/materiality split. Record both under 375E-DIR; do not assume the
vote redesign covers the bypass.
 
**→ 375H DIRECTIONAL RECALL AUDIT SPECCED (build_log/375H_chat_instruction.md) — READ-ONLY; A+B keyless,
C keyed.** Determines WHICH of the three defects (schema / evaluator / true-directionality-gap) produces the
bypass, and how big it is — does NOT prejudge an all-LP pass. Part A (keyless): exact Stage-7 gate; Q2
absent-vs-wrong-direction conflation; whether Stage 7 distinguishes absent/one-sided/disproportionate; and
THE CRUCIAL question — what "covered" MEANS in the coverage prompt/schema (textual presence vs functional
protection vs element-satisfaction-without-polarity; quote consent + alterations element defs). Part B
(keyless): scan the 0604 run — every non-flagged LP, find present landlord-favorable language, classify each
as schema/evaluator/true-gap/none, COUNT per class. Part C (keyed): 5 synthetic fixtures (tenant-favorable
vs sole-discretion sublet; broad landlord access; unrestricted alterations consent; remedies asymmetry) →
does coverage reliably emit directional candidates from present-adverse language? RECORD AS A SEPARATE
WORKSTREAM, not folded into 375E-DIR. Three distinct directional problems: (i) vote-as-severity [375E-DIR];
(ii) Pass-1 generation variance [recall governance]; (iii) coverage-gated bypass of present adverse terms
[375H]. Part A+B can run now keyless; Part C waits for a keyed session.
 
**✅ 375H Parts A+B DONE (SHA b1159a0, read-only). DOMINANT DEFECT = SCHEMA (not evaluator, not true-gap),
MARGINALLY LIVE in this lease.**
- Part A mechanism: _FLAGGED_STATES = {missing, partial_material, partial_typical, review_needed} (+ partial_class
  + HIGH/MED conflict as a 2nd path; 0604 had 0 conflicts so flag is effectively the sole gate). `covered` /
  `covered_unfavorable` / `not_applicable` BYPASS Stage 7. Q2a conflation confirmed VERBATIM: line 256 `no` =
  "wrong party, OR IS ABSENT"; line 268 mismatch_flag on "wrong direction or absent." Q2b distinguishes
  disproportionate, but absent vs present-one-sided are NOT distinguished (both → no → mismatch_flag).
- THE LOAD-BEARING ANSWER: coverage "present" = "appears as literal or near-literal text" (line 191) — TOPICAL
  presence, NO polarity check. LP-09 consent elements (assignment_requires_landlord_consent,
  consent_standard_supplied) + LP-10 approval_threshold check the TOPIC, not a protective standard — there is
  NO "consent not unreasonably withheld" element. A "sole discretion" clause satisfies them → covered → bypass.
  This is a SCHEMA defect (defect type #1), NOT evaluator, NOT true-directionality-gap.
- COUNTER-EXAMPLE proving the architecture works where encoded: LP-13 schema HAS protective-direction
  elements (mutual_vs_one_way, landlord_indemnification_scope, negligence_carveouts); Section 11.2 has a real
  reciprocal landlord→tenant indemnity, so "covered" is CORRECT. Polarity IS checkable where the schema
  encodes it. So the fix = extend LP-13's pattern to consent/approval elements; NOT a new subsystem.
- Part B live scan (6 not-flagged LPs): SCHEMA defect 1 (LP-09); EVALUATOR 0; TRUE-gap 0; no-bypass 5 (LP-08
  standard insurance, LP-13 genuinely mutual, LP-12/23/31 N/A). 1/6 = marginal in THIS balanced lease — which
  is exactly why Part C (one-sided fixtures) is needed before sizing the schema gap as broadly dangerous.
- OPTIONS (not pre-picked): (1) targeted schema element-polarity fix [leading — LP-13 proves it works];
  (2) evaluator-prompt polarity annotation; (3) all-LP directional path [heaviest, don't prejudge];
  (4) fixture-gated-only. Leading read: (1) validated by Part C fixtures (4); (3) only if fixtures show (1)
  insufficient.
[GPT TERMINOLOGY + SEQUENCING CORRECTION — three fixes:]
(a) NOT an absence_adverse_to / "polarity" fix. absence_adverse_to answers "does a MISSING element help/hurt";
    LP-09 is PRESENT hostile language. The schema asks "is there a consent standard?" not "what KIND, and does
    it preserve a real tenant right?" Correct name: **DIRECTION-SENSITIVE PRESENT-TERM / PROTECTION-QUALITY
    schema repair.** Likely elements for LP-09: consent not unreasonably withheld/conditioned/delayed;
    affiliate-transfer carve-outs; recapture; profit-sharing limits; objective approval criteria. Do NOT route
    Code to the absence field — wrong machinery.
(b) Schema repair does NOT eliminate the independent-directionality need. TWO classes: (i) hostile present
    language a better ELEMENT can catch (LP-09); (ii) every protection technically PRESENT yet the combined
    remedial structure materially LOPSIDED (tenant notice+cure+termination all "present"; landlord self-help+
    acceleration+fee-shifting+multi-path) — NOT a missing-element defect, a relationship-level disproportionality
    that STAGE 7 SYNTHESIS must catch once repaired. Part C MUST test BOTH families, else we fix LP-09 and
    falsely declare recall solved.
(c) DEPLOYMENT TRAP — the workstreams are conceptually orthogonal but operationally coupled: once schema
    repair lands, LP-09 STARTS reaching Stage 7, where 3-0→HIGH→Risk still lives. So repair RECOVERS a real
    finding and feeds it into the known-broken routing, enlarging the unstable headline. → DESIGN+VALIDATE the
    repair now, but do NOT deploy recovered findings into lawyer-facing Risk until 375E-DIR fixes routing;
    keep them internal/comparison-mode until then.
- PART C (keyed) PENDING — reframed as a VALIDATION MATRIX (not a prevalence estimate): test BOTH (i) present
  hostile language that should fail a protective element (sole-discretion vs reasonable consent; unrestricted
  vs reasonable alteration approval; unrestricted vs notice-limited landlord access; unilateral recapture vs
  protected position) AND (ii) technically-complete-but-disproportionate remedies (does independent synthesis
  remain required after schema repair). Coverage→flag?→Stage 7, obvious expected answers.
**→ SEQUENCING CORRECTION (GPT): the HIGHEST-priority next measurement is STAGE 5e COMPLETENESS/STABILITY,
not Part C.** The three-way redesign makes MATERIALITY the substantive Risk anchor. Materiality cannot replace
vote-count severity in production until shown to be: (1) sufficiently POPULATED (currently only ~28% of
coverage LPs have use_impact); (2) genuinely ASSESSED not DEFAULTED (the `or "moderate"` / floor fallback);
(3) STABLE on frozen input (5e is batched + temp-0 + vote-merged — the SAME architecture that produced the
directional wobble; UNTESTED for stability); (4) AVAILABLE for the newly-recovered present-hostile findings.
This is the PRODUCTION GATE for the new Risk architecture — if materiality wobbles like the vote, the redesign
moves the wobble instead of removing it. Spec as **375I — Stage 5e completeness/stability audit** (keyed
replay, same shape as 375D-2 pointed at lease_use_impact). This OUTRANKS 375H-C in the queue.
 
---
 
## Key working notes
 
- **COST-ROUTING RULE (2026-06-05, corrected):** THREE meters, not two.
  (1) **Claude Code via API key** (`claude_code_key_zvido2_beqc`, "Claude Code" workspace) = real $ per token,
      dominated by Code RE-READING large files (app.js + artifacts) each turn — this WAS the ~$22/day driver.
  (2) **Claude Code via VS Code, Auth method = "Claude AI"** (logged in as zvido2@gmail.com, Tzvi's Individual
      Org) = runs against the MAX SUBSCRIPTION, NOT metered in dollars — confirmed via the Account & Usage panel
      2026-06-05. **This is the cheap path and it already exists.** Same tool, same repo access, same
      capability — just billed to the subscription cap (which Tzvi never hits; day job, doesn't live in the
      interface).
  (3) **This Chat** = Max subscription, ~free-in-dollars for Tzvi (never maxes the cap).
  THEREFORE, in priority order: (a) standalone scripts / read-only diagnostics / harnesses → CHAT writes,
  Tzvi runs LOCALLY (python = zero tokens, re-run forever free); (b) repo-touching agentic work (edit live
  code, commit, restart server — which Chat can't do) → **Claude Code via the VS Code "Claude AI" auth**, NOT
  the API-key Code, so it lands on the subscription not the dollar meter; (c) the VeredAI PIPELINE must stay
  on its API key (a server calling models programmatically can't use subscription auth) — but that's the cheap
  part (Eval-A modest rows). ACTION: route day-to-day Code work through VS Code (Claude AI auth); stop using
  the API-key Code session for interactive work — that retires the ~$22/day. Executing a script locally is
  ALWAYS free regardless of who wrote it; the cost was Code-via-API-key AUTHORING (esp. its file reads).
  **RESOLVED 2026-06-05: the `claude_code_key_zvido2_beqc` API key was DISABLED by Tzvi.** Claude Code now
  runs only on the VS Code "Claude AI" subscription auth (rail 2). The ~$22/day API-key Code driver is
  retired. Remaining API-metered spend = the VeredAI pipeline only (rail c, the cheap part). Cost story
  CLOSED. (The earlier "was it Tzvi-authorized or auto-provisioned" question is now moot — key is off.)
- **API KEYS location:** `C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env` (holds ANTHROPIC_API_KEY / OPENAI_API_KEY / XAI_API_KEY etc). The SERVER loads these on startup; standalone diagnostic scripts run in a fresh shell do NOT inherit them and fail with `<PROVIDER>_API_KEY missing` → the harness must `load_dotenv(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env")` at top (or the shell must set the vars) before any keyed model call. (Discovered 2026-06-05 when 375E-COV-A1 returned all-`no_evaluators` defaults because the standalone harness had no keys — a SETUP failure, not a result.)
- Chat writes `build_log/NNN_*.md`; Claude Code implements/commits/writes `NNN_code_status.md`.
- OneDrive `write_file` overwrites whole files — read full, then rewrite (str_replace unreliable on synced paths).
- Backend changes need FULL uvicorn restart (`--reload` doesn't watch `cam/adapters/`). Frontend needs hard refresh + cache-bust bump.
- Local server launch: `cd "05 Lease Analyzer"; kill port 8000; $env:PYTHONPATH="...\CAM"; uvicorn app.main:app --port 8000`. Bare `uvicorn` uses the right interpreter; `python3 -m uvicorn` uses the Store Python which lacks deps.
- Reusable diagnostics: `372_extract_signals.py` (signals, auto-newest), `372_verify_deploy.py` (deploy check), `372CV_disagreement.py` / `372CV_why.py` (per-evaluator disagreement), `372BU_prevalence.py` (boundary-fragile probe), `372DIFF_stability.py` (matched-run stability diff vs 181402).
- n=1-contract diagnostics are DIRECTIONAL only — never cite as CAM metrics or enter the patent record.
- Stability vocabulary: distinguish ESCALATION-boundary flips (partial→review_needed; lower risk) from REASSURANCE-boundary flips (addressed→risk/review; higher risk). "0 present↔absent crossings" is the metric that matters, not raw bucket-change count.
- "Record the field before you need it" — the Grok outage was diagnosable in one read because actual_model/is_fallback/fallback_reason existed.
- "Measure first. Spec second. Celebrate last." — boundary-fragile was correctly NOT specced (prevalence check returned 0 on real data). A valid stop result.
- A stale uvicorn worker can serve OLD cam/adapters/ code while looking restarted. Symptom: new fields absent. Fix: kill port 8000, cold start. Canary: LP-11 split_applied=True.
- Architecture doc (`Docs/CAM_Architecture_Plan.md`) has the full 372 chain detail + the proven/not-established split for 372STAB.
- Dead temp files safe to delete: `Docs/_BU_block_tmp.md`, `Docs/CAM_Current_State_incident_block.md` (content folded into this doc).
 
