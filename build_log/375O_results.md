# Step 375O — COV Entry-Policy Counterfactual Results

**Date:** 2026-06-05  **Mode:** READ-ONLY / keyless. No model calls, no 5e run.
**Artifact:** frozen run `lease_review_20260604_033046_52adbf` (52adbf), use_impact read through
`_normalize_use_consequence` (375M normalizer). n=1 lease (Atlas Meridian warehouse).
**External-use pause:** still in force. 375O does not lift it.

---

## ⚠️ GATE-VS-YIELD CAVEAT (state plainly before all counts)

**375O measures GATE (who each strategy ADMITS), not YIELD (whether newly-admitted LPs
assess well).** "Strategy X admits N, leaves M unassessed" means "if 5e successfully produces
an assert-strength use_consequence verdict for all N" — which is UNPROVEN. Stage 5e is sparse
and shows instability on some LPs (LP-20 jitter in Q3 replays; LP-07/16/19/25 abstained in
use_aware_governance). The open 375I-class question — do newly-admitted LPs produce decisive
assessments? — cannot be answered without a keyed run. All volume projections in this report are
upper bounds on defect coverage, not guarantees.

---

## Entry Strategies Replayed

Eight strategies were replayed over the full 32-LP coverage_assessment using `element_verdicts`
(not `elements_found`/`elements_missing`) for correct partial-threshold computation, and reading
all use_impact through the 375M normalizer.

**Reference set:**
- Total LPs: 32 (including 3 not_applicable)
- Directional Risk finding LPs (26): LP-01/02/03/04/05/06/07/10/11/14/15/16/17/18/19/20/21/22/24/25/26/27/28/29/30/32
- Currently 5e-assessed (8): LP-03/05/10/14/16/20/26/32 (have use_impact in 52adbf)
- Currently unassessed directional (18): LP-01/02/04/06/07/11/15/17/18/19/21/22/24/25/27/28/29/30
- LP-09: covered, 0% gap, no directional finding, no Risk routing — NOT reachable by any strategy without 375H-C

---

## Per-Strategy Summary Table

| Strategy | Admitted | Already-assessed | Newly-admitted | Unassessed dir. covered | LP-09 | Circular? | New 5e calls |
|---|---|---|---|---|---|---|---|
| **A50** | 8 | 8 | 0 | 0/18 | No | No | 0 |
| **A33** | 19 | 8 | 11 | 11/18 | No | No | 11 |
| **A25** | 20 | 8 | 12 | 12/18 | No | No | 12 |
| **B** | 26 | 8 | 18 | 18/18 | No | No | 18 |
| **F** ⚠️ | 26 | 8 | 18 | 18/18 | No | **YES** | 18 |
| **G-cand** | 26 | 8 | 18 | 18/18 | No | No | 18 |
| **G-ver** | 26 | 8 | 18 | 18/18 | No | No | 18 |
| **H** | 26 | 8 | 18 | 18/18 | No | No | 18 |

**H = G-cand on this lease.** A33 is a strict subset of G-cand; the union H = A33 ∪ G-cand
equals G-cand exactly. The threshold spine contributes zero marginal admissions on this artifact.

---

## Per-Strategy Detail

### A50 — Current gate (missing/review_needed always; partial ≥50% missing)

**Admitted (8):** LP-03, LP-05, LP-10, LP-14, LP-16, LP-20, LP-26, LP-32  
**Already-assessed:** 8 (all admitted are already assessed)  
**Newly-admitted:** 0  
**Unassessed directional Risk covered:** 0/18  
**LP-09:** No  
**Circular:** No  

This is the status quo. The gate admits exactly the 8 LPs that already have use_impact records.
Zero coverage of the 18-finding defect. The A50 gate is the defect — not a solution.

---

### A33 — Threshold-lower (partial ≥33% missing)

**Admitted (19):** LP-03, LP-04, LP-05, LP-06, LP-07, LP-10, LP-14, LP-15, LP-16, LP-17, LP-19,
LP-20, LP-21, LP-22, LP-26, LP-28, LP-29, LP-30, LP-32  
**Already-assessed:** 8 (LP-03/05/10/14/16/20/26/32)  
**Newly-admitted (11):** LP-04, LP-06, LP-07, LP-15, LP-17, LP-19, LP-21, LP-22, LP-28, LP-29, LP-30  
**Unassessed directional Risk covered:** 11/18  
**LP-09:** No (covered, threshold-lowering provably cannot reach; see 375N Q5)  
**Circular:** No  

LPs NOT covered by A33 but with directional findings: LP-01 (17%), LP-02 (25%), LP-11 (12%),
LP-18 (20%), LP-24 (14%), LP-25 (14%), LP-27 (20%) — all partial with <33% missing.

Key property: **A33 ⊆ G-cand.** Every LP admitted by A33 is also admitted by G-cand (all 11
newly-admitted A33 LPs have adverse directional findings). A33 adds zero marginal admissions over
G-cand on this artifact.

---

### A25 — Sensitivity run (partial ≥25% missing)

**Admitted (20):** adds LP-02 (25%) vs A33  
**Newly-admitted (12):** LP-02, LP-04, LP-06, LP-07, LP-15, LP-17, LP-19, LP-21, LP-22, LP-28, LP-29, LP-30  
**Unassessed directional Risk covered:** 12/18  
**LP-09:** No  

Adds LP-02 (Rent Escalation, 25% missing). LP-02 has an adverse directional finding (Dir-02),
so it's also in G-cand. A25 ⊆ G-cand as well — still zero marginal admissions over the
finding-triggered lane.

---

### B — Raw directional-adverse entry (all 26 adverse-directional LPs)

**Admitted (26):** all 26 directional finding LPs  
**Newly-admitted (18):** all 18 unassessed directional LPs  
**Unassessed directional Risk covered:** 18/18 (100%)  
**LP-09:** No (LP-09 has no directional finding — it's covered, not flagged)  
**Circular:** No  

Full defect coverage. On this lease: **B = G-cand = G-ver = H** (all 26 adverse-directional LPs,
since every adverse-directional LP has a candidate-level adverse finding and all verified 3-0).
The distinction between B/G-cand/G-ver only matters when there are findings with partial
verification (not present on this run).

---

### F ⚠️ — Current-Risk entry (DIAGNOSTIC ONLY — exposes circularity)

**Admitted (26):** all LPs appearing in any current-Risk finding  
**Newly-admitted (18):** same 18 as B/G-cand  
**Unassessed directional Risk covered:** 18/18  
**LP-09:** No (LP-09 has no finding routed to Risk — it's covered, `requires_attention=False`)  
**Circular:** **YES — DO NOT IMPLEMENT**  

**Circularity demonstrated concretely:** F admits the same 26 LPs as B/G-cand/G-ver.
F = B = G-cand = G-ver on this artifact. This proves the circularity: "LP is in Risk" equals
"LP has an adverse-directional finding" on this lease because all adverse-directional LPs were
floor-promoted to Risk without assessed consequence (375J Q2: 18/32 LPs use implicit routing floor).
Using current Risk as an entry condition means: admit to consequence assessment every LP whose
current Risk status was caused by missing consequence assessment. That is precisely circular.
F is included only to make the circularity visible as a concrete count match.

---

### G-cand — Finding-triggered, candidate-level (verification-agnostic)

**Admitted (26):** all 26 directional finding LPs  
**Already-assessed:** 8 (LP-03/05/10/14/16/20/26/32)  
**Newly-admitted (18):** LP-01/02/04/06/07/11/15/17/18/19/21/22/24/25/27/28/29/30  
**Unassessed directional Risk covered:** 18/18 (100%)  
**LP-09:** No  
**Circular:** No — condition is "has an adverse-directional CANDIDATE FINDING" (determined by
Pass 1 candidate generation, not by current bucket routing)  

G-cand reads the Stage 7 candidate set (Pass 1), not the current Risk bucket. On this artifact:
Pass 1 generated exactly 26 directional candidates; all 26 are adverse (tenant_unprotected).
Entry condition: LP appears as an implicated_lp in a directional_mismatch candidate, regardless
of whether that candidate was subsequently verified.

LPs G-cand admits that A33 does NOT (the finding-triggered marginal set, 7 LPs):
LP-01 (17%), LP-02 (25%), LP-11 (12%), LP-18 (20%), LP-24 (14%), LP-25 (14%), LP-27 (20%)
These are the thin-gap LPs (<33% missing) that A33's threshold cannot reach but which have
adverse directional findings and therefore belong in consequence assessment.

---

### G-ver — Finding-triggered, 3-0 verified

**Admitted (26):** same as G-cand  
**G-cand vs G-ver delta: ZERO on this run**

Pass 2 confirmation: all 3 evaluators (A: claude-sonnet-4-6, B: gpt-5.4, C: grok-4.3) returned
`mismatch_confirmed: 26` — all 26 directional candidates verified at 3-0. No partial verification.
G-cand = G-ver on this artifact.

**The delta is the wobble-re-import measurement.** Delta=0 here means the vote-wobble re-import
risk is not observable on this run, not that it doesn't exist. 375D-2 / 375-R proved Pass 2 votes
flip run-to-run. On a re-run where one finding drops from 3-0 to 2-1 or 1-1-1, G-ver would
de-admit that LP while G-cand would keep it. This is the architectural reason G-cand is preferred
over G-ver: G-ver relocates Pass 2 vote wobble into the 5e entry condition, making eligibility
itself unstable. G-cand (verification-agnostic) is stable across re-runs as long as the finding
is still generated at the candidate level.

---

### H — Two-lane hybrid (A33 ∪ G-cand)

**Admitted (26):** H = A33 ∪ G-cand = G-cand exactly  
**Newly-admitted (18):** same as G-cand  
**Unassessed directional Risk covered:** 18/18  
**LP-09:** No  

**H = G-cand on this lease.** A33 is a strict subset of G-cand — every LP admitted by A33 also
has an adverse-directional finding and is therefore in G-cand. The union equals G-cand.

The threshold spine (A33) does ZERO marginal work on this artifact. Its value is forward-looking
only: on a future lease where some partially-covered LPs do NOT have adverse directional findings
(e.g., a coverage gap that Stage 7 assessed as favorable or match, or where Pass 1 didn't generate
a candidate), A33 would admit those LPs while G-cand would not.

---

## Q1 — Does G-cand differ from G-ver on this lease?

**PROVEN CLAIM: G-cand = G-ver on this run. Delta = 0.**

Pass 1 generated 26 directional candidates (`pass1_directional_candidate_count: 26`,
`candidate_density: 1.0`). Pass 2 verified all 26 as `mismatch_confirmed` at 3-0 by all three
evaluators. No partially-verified findings exist on this artifact.

**Therefore: the vote-wobble re-import risk is real but not observable here.**

The absence of delta on 52adbf does NOT mean the risk doesn't exist. It means 375D-2/375-R's
run-to-run verification wobble did not produce any 2-1 or 1-1-1 split on this particular run.
On a re-run of the same lease, some findings may drop below 3-0 in Pass 2.

**Entry-condition consequence:** Even though G-cand = G-ver here, the architectural preference
for G-cand over G-ver stands. If COV implemented G-ver (verification-gated), then on a re-run
where LP-07 drops from 3-0 to 2-1, LP-07's 5e eligibility would change run-to-run with no
change to the underlying provision. G-cand removes this instability: a finding at the candidate
level (Pass 1) is more stable than its verification vote, and consequence assessment is independent
of whether the verification was unanimous.

**Caveat:** n=1 run. The identity G-cand=G-ver on 52adbf is run-specific, not a general property.

**Still-unmeasured:** Whether any future run of this lease produces G-cand ≠ G-ver. Requires a
second run of the same lease through Stage 7.

---

## Q2 — How many currently-unassessed Risk findings does each strategy cover?

**PROVEN CLAIM: Defect coverage rates per strategy:**

| Strategy | Covers (of 18 unassessed directional) | Missed (remaining defect) |
|---|---|---|
| A50 | 0/18 (0%) | 18 |
| A33 | 11/18 (61%) | LP-01/02/11/18/24/25/27 |
| A25 | 12/18 (67%) | LP-01/11/18/24/25/27 |
| B | 18/18 (100%) | 0 |
| F | 18/18 (100%) | 0 (but circular) |
| G-cand | 18/18 (100%) | 0 |
| G-ver | 18/18 (100%) | 0 |
| H | 18/18 (100%) | 0 |

A33's 7-LP gap is structurally determined by the 33% threshold and this lease's element histogram:
LP-01 (17%), LP-11 (12%), LP-18 (20%), LP-24 (14%), LP-25 (14%), LP-27 (20%) are all
<33% missing. LP-02 (25%) is also below 33%. These 7 are thin-gap LPs — partial but highly
covered — and A33 intentionally excludes them by threshold design.

**Caveat:** "Covers" means "admits to 5e" not "produces a decisive assessment." These 18 LPs
need a keyed run to confirm yield (see gate-vs-yield caveat).

**Still-unmeasured:** How many of the 7 A33-missed LPs (the thin-gap set) would produce
actionable assessments if 5e ran on them. LP-11 (Default, 12% missing) and LP-24/LP-25
(14% missing) are near-complete provisions — 5e's input may be thin.

---

## Q3 — Does F admit ~the same set as B/G, demonstrating the circularity?

**PROVEN CLAIM: F = B = G-cand = G-ver = H exactly on this artifact. The circularity is
demonstrated as a concrete identity, not a structural argument.**

F admitted 26 LPs. B admitted 26 LPs. G-cand admitted 26 LPs. G-ver admitted 26 LPs. H admitted
26 LPs. All five admit exactly the same set.

**Why they're identical:** The current Risk bucket on this lease is populated exclusively by
adverse-directional findings (26 directional + 6 compound that implicate only directional LPs).
All 26 directional LPs were floor-promoted to Risk (375J Q2: 18 via implicit floor, 8 via
genuine assessment). So "in current Risk" ⟺ "has adverse-directional finding" on this lease.

**The circularity exposed:** If COV used F (current Risk) as its entry condition, it would admit
to consequence assessment every LP whose Risk status was CAUSED by missing consequence assessment.
Result: LPs floor-promoted to Risk become eligible for 5e; 5e runs; if it returns harmful/high,
they stay in Risk — now with assessed consequence. If 5e returns beneficial or low, they exit
Risk. The entry condition would be validated post-hoc by the assessment it's supposed to enable.
That's circular: Risk status cannot be both the gate and the output.

G-cand avoids this: the entry condition is "has a directional-candidate finding" (a Stage 7
output), not "is in Risk" (a routing output). Stage 7 is upstream of routing; using it as the
gate is not circular.

**Caveat:** F = G-cand only because ALL adverse-directional LPs are currently in Risk. On a
lease where some adverse-directional LPs are deliberately not in Risk (e.g., explicitly exempted
by a routing override), F ≠ G-cand. But on any lease where the floor promotes all adverse
directionals to Risk by default (which is the current behavior), F = G-cand trivially.

**Still-unmeasured:** Whether the equivalence breaks on a lease with routing overrides or
non-directional Risk findings.

---

## Q4 — Under H, admitted / newly-assessed / still-unassessed; LP-09 reached?

**PROVEN CLAIM: H admits 26 LPs, adds 18 new 5e calls, covers 18/18 defect target. LP-09 is
NOT reached by H. H = G-cand on this lease.**

H = A33 ∪ G-cand = G-cand (A33 ⊆ G-cand confirmed by set arithmetic).

Under H (assuming all 18 newly-admitted LPs are successfully assessed):
- Admitted: 26 LPs
- Already-assessed: 8 (no change)
- Newly-admitted: 18 → need 18 new 5e calls
- Directional unassessed after H: 0 (if all 18 yield decisive assessments)
- Compound-risk unassessed: 6 (CRX-01 through CRX-06 — multi-LP findings; 5e operates per-LP)
- LP-09: NOT reached (covered, no directional finding, not in G-cand or A33)

**LP-09 remains outside all H lanes.** The present-hostile covered lane is explicitly deferred
to 375H-C. The `landlord_leverage_point` caution signal on LP-09 was confirmed insufficient
as a COV entry condition in 375N Q4 — it fires on balanced LPs and cannot reliably distinguish
present-hostile from topically-covered.

**Projected UI landing (consequence_unassessed design call input):**
- If 5e yields 18 decisive assessments → 0 directional unassessed; total ~6 unassessed (CRX only)
- If some yield context_dependent or no_evaluators → those LPs stay unassessed; count rises
- If 5e yields 0 decisive (pathological) → 18 directional unassessed; same as today
- Gate-vs-yield caveat applies: these are outcome ranges, not guaranteed results

**Caveat:** H = G-cand on this lease. Whether H ≠ G-cand on a future lease (the architectural
motivation for including A33 in H) depends on whether that lease has partially-covered LPs without
adverse-directional findings. Not currently testable.

**Still-unmeasured:** 5e yield rate on the 18 newly-admitted LPs (requires a keyed run). LP-09
remains unassessed.

---

## Q5 — Is any threshold value defensible as a coverage-lane rule independent of this lease?

**PROVEN CLAIM: On this artifact, A33 (and any threshold variant) is a STRICT SUBSET of G-cand.
The threshold-spine does zero marginal work on this lease. Its only value is forward-looking
(safety net for lease #2).**

A33 ⊆ G-cand: every LP admitted by A33 also has an adverse-directional finding and is therefore
in G-cand. A33 contributes zero LPs to H beyond what G-cand already admits. The 11 newly-admitted
A33 LPs (LP-04/06/07/15/17/19/21/22/28/29/30) are all in G-cand.

**The 33% threshold is n=1 tuned.** The value 33% (= 2/6 or 2/5 elements missing) emerged from
375N's analysis of this lease's element-count histogram. A different lease with different element
schemas per LP would produce a different "natural cluster" of partial thresholds. There is no
lease-independent reason to prefer 33% over 30%, 35%, or 25%.

**Does the threshold have independent value at all?**
On this lease: no. The finding-triggered lane (G-cand) is the operative mechanism.

On future leases: potentially yes. The scenario where A-lane adds value over G-cand alone:
a LP with ≥33% element gap where Stage 7 generated NO adverse-directional candidate. This could
happen if: (a) the provision gap is in a topic Stage 7 doesn't flag directionally (e.g., a
procedural omission); (b) Pass 1 generated no candidate for that LP for whatever reason; (c) the
lease has favorable-direction directional findings that G-cand doesn't admit (G-cand only admits
adverse-directional). In any of these scenarios, A33 would admit the LP while G-cand wouldn't.

**Defensibility verdict:**
- As a FUTURE-SAFE coverage rail: defensible.
- As a mechanism addressing the 375J defect on this lease: zero marginal value over G-cand.
- As a threshold choice: the specific value (33%) is n=1 tuned, not derivable from first principles.
  Any threshold-lane implementation should be revisited when lease #2 exists and the element
  histogram is compared.

**Caveat:** The threshold's n=1 tuning problem is a stronger criticism than "it's redundant." A
threshold that perfectly clusters to this lease's element-count distribution may completely miss or
over-admit on a lease with different element schemas.

**Still-unmeasured:** Whether any LP on lease #2 would be in A33 but NOT in G-cand. This requires
a lease where some high-gap provision has no adverse directional finding — which is structurally
possible but not confirmed.

---

## Entry-Architecture Recommendation

**Recommendation: Two-lane architecture (H = G-cand + A-coverage-rail), using G-cand as the
operative lane and A-rail as the forward-safe coverage supplement. G-ver NOT recommended as
the finding-triggered lane. Present-hostile lane deferred to 375H-C.**

This is a recommendation on architecture shape; the specific threshold within A-rail and the
landing-bucket for unassessed findings remain Tzvi's two COV design calls (unchanged from 375N).

### Why G-cand (not G-ver) as the finding-triggered lane

G-cand = G-ver on this run (Q1: delta=0). But the architectural preference for G-cand is
structural, not artifact-specific:

- G-ver gates 5e eligibility on the Pass 2 vote. Pass 2 votes are demonstrably run-unstable
  (375D-2/375-R: finding drops from 3-0 to 2-1 on re-run). If LP-07's verification drops to 2-1
  on re-run #2, G-ver de-admits LP-07 from 5e. LP-07's provision content hasn't changed; only a
  model vote changed. This is vote-wobble relocation from the Risk tier into the eligibility gate —
  the same instability problem, one layer up.
- G-cand reads Pass 1 (candidate generation). Pass 1 is more stable: it asks "does the finding
  assert a one-sided concern?" — a lower bar than "is the finding 3-0 verified?" Pass 1 drops a
  finding only if the provision is so unambiguous that no evaluator generates a directional
  candidate at all. That's a stronger signal of non-adverse than a 2-1 verification vote.
- For consequence-assessment eligibility, the right question is "does this provision have an
  adverse-directional concern that might affect this tenant?" (G-cand), not "was that concern
  unanimously verified?" (G-ver). The consequence assessment itself will be the verification of
  whether the provision is harmful — separate from Pass 2's directional confirmation.

### Why keep the A-rail at all if G-cand does all the work

On this lease, A-rail adds nothing. The honest answer is: A-rail provides coverage for a class
of LPs that doesn't appear on this lease — partially-covered LPs without adverse-directional
findings. This is a future-safety argument, not a present-defect argument.

Arguments for including A-rail:
1. Completeness: a provision with ≥33% missing elements might have significant tenant consequence
   even if Stage 7 didn't flag it directionally (Stage 7 can miss candidates).
2. Defense-in-depth: the finding-triggered lane depends on Stage 7's candidate generation quality.
   If Stage 7 misses a directional concern, A-rail catches the coverage gap.
3. Architectural clarity: two-lane design makes it explicit that there are TWO reasons a LP
   enters 5e (coverage completeness vs finding-triggered consequence). A single G-cand-only design
   obscures this distinction.

Arguments against making A-rail mandatory:
1. Zero demonstrated value on n=1. Any specific threshold is n=1 tuned.
2. On future leases, A-rail may over-admit (e.g., a lease where every partial LP has a beneficial
   consequence, and the threshold dumps them all into 5e unnecessarily).
3. G-cand already subsumes the partially-covered high-gap LPs on this lease. The marginal set
   (LPs with high gaps but no directional finding) may be small in practice.

**Disposition:** Include A-rail in the COV spec as a defined lane with the explicit note that
its threshold is provisional (n=1) and will be revisited on lease #2. Do not treat A33 as a
permanent design decision.

### What NOT to implement

- **F (current-Risk entry):** Circular. Proven circular by concrete identity with G-cand (Q3).
- **G-ver (verification-gated):** Relocates vote-wobble into the eligibility gate. G-cand is
  preferred.
- **B (raw directional-adverse entry):** Equivalent to G-cand on this lease (all 26 directionals
  are adverse). B is B = G-cand here, so it's not wrong, but it doesn't distinguish adverse-only
  selection from candidate-level selection. On a future lease with favorable-direction directional
  findings, B would admit those too (favorable-direction LPs don't need consequence assessment
  via this gate); G-cand is more precise.
- **Present-hostile covered lane:** Deferred to 375H-C. `landlord_leverage_point` is confirmed
  noisy (375N Q4). No proxy available.

### Framing for Tzvi's two COV design calls

**Design Call 1: Gate shape (unchanged from 375N, now with architecture context)**

The two-lane shape (G-cand + A-rail) is the recommendation. The specific A-rail threshold (33%
vs 25% vs 20%) remains Tzvi's call. Key additional context from 375O:
- A33 adds 0 marginal LPs over G-cand on this lease. The threshold number is a provisional
  forward-safety rail, not a present-defect fix.
- G-cand alone covers 18/18 unassessed directional findings. A33 covers 11/18.
- If cost/volume is a concern, G-cand-only covers the full defect; A-rail adds future-safety at
  the cost of 0 extra calls on this lease (and potentially some extra calls on future leases).

**Design Call 2: Landing bucket for consequence_unassessed findings (unchanged from 375N)**

Under G-cand (or H), 18 LPs enter 5e. If all 18 produce decisive assessments, the unassessed
bucket shrinks to ~6 (compound CRX findings only, which 5e doesn't assess per-LP). If some fail,
the residual lands somewhere. The options (floor/Risk, visible subtype, source-strict) remain
open per 375N Design Call 2.

Additional data point from 375O: even under G-cand's full coverage (18/18), the 6 compound_risk
findings (CRX-01 through CRX-06) will remain consequence_unassessed. These multi-LP findings
don't have a single LP to assess. Design Call 2 must account for this irreducible floor of ~6.

---

## Scope guard confirmed

| Guard | Status |
|---|---|
| `_should_assess` unchanged | YES |
| No routing changed | YES |
| No cam/core/ touched | YES |
| No model calls, no 5e run | YES — purely keyless artifact + JSON reads |
| External-use pause NOT lifted | YES |
| Present-hostile lane NOT implemented | YES — deferred to 375H-C |
| DEPLOYMENT TRAP unchanged | YES |
| 375M write-path check still OWED | YES — see 375O_code_status.md |
