# Step 375E-COV-A — Results: G-cand Finding Consequence Provenance

**Date:** 2026-06-05
**Mode:** POPULATE/RECORD only — no routing change, no bucket moves.
**Keyed:** Code complete + keyless 0-drift proven. KEYED run owed — Tzvi runs it to populate
the 18 newly-assessed findings and close the 375M write-path check.

---

## Validation 1: 0-Drift Proof (COMPLETE — keyless)

**Gate:** re-run `assess_finding_consequence` on frozen 52adbf artifact (keyless,
`use_profile=None`) and assert every routing-relevant field is unchanged.

Routing fields checked (all present on raw findings, unchanged):
`finding_id`, `finding_type`, `directionality`, `severity`, `verdict`

**Result: ALL PASS — no routing drift.**

```
[PASS] 0 routing drift across all 32 findings
[PASS] Provenance fields present on all 26 directional findings
[PASS] compound_consequence_source='not_assessed' on all 6 compound findings
[PASS] Finding counts verified: 26 directional, 6 compound (matches 375J)
```

Structural proof: `lease_finding_consequence.py` adds new keys to finding dicts; it
reads `finding_type`, `implicated_lps`, `directionality` but writes ONLY new keys
(`stage7_direction`, `use_consequence`, `materiality`, `use_consequence_source`,
`materiality_source`, `assessment_scope`, `compound_consequence_source`).
No existing field is mutated — routing drift is structurally impossible.

**Caveat:** `current_bucket` is NOT stored on findings in `pipeline_results.json`;
it is a derived/computed field. Routing impact is confirmed structurally, not by
comparing bucket fields on the artifact.

---

## Validation 2: Provenance Populated (keyless portion complete; keyed owed)

### Already-assessed findings (8 LPs — source=assessed, keyless-confirmed)

These 8 LPs had LP-scope `use_impact` from the pre-COV-A Stage 5e run.
COV-A copies their verdicts to finding-level provenance. Confirmed via
`_normalize_use_consequence` (legacy `gap_impact` → `use_consequence`):

| Finding | LP    | use_consequence | materiality | source   |
|---------|-------|-----------------|-------------|----------|
| Dir-03  | LP-03 | harmful         | high        | assessed |
| Dir-05  | LP-05 | **beneficial**  | medium      | assessed |
| Dir-08  | LP-10 | harmful         | high        | assessed |
| Dir-10  | LP-14 | harmful         | medium      | assessed |
| Dir-12  | LP-16 | harmful         | high        | assessed |
| Dir-16  | LP-20 | neutral         | low         | assessed |
| Dir-21  | LP-26 | harmful         | high        | assessed |
| Dir-26  | LP-32 | harmful         | medium      | assessed |

**LP-05 spot-check (Validation 4 combined):** Dir-05 is an adverse directional finding
(`directionality: "tenant_unprotected"`) with `use_consequence: "beneficial"`. This
confirms the Stage 7 / 5e doctrine: Stage 7 owns direction (adverse = landlord-favoring
absent term), 5e owns consequence (absence of use restriction = MORE operational
flexibility for this industrial tenant = beneficial). The adverse direction was NOT
re-litigated. ✓

### Unassessed findings (18 LPs — keyed run owed)

In keyless mode: all 18 marked `use_consequence_source: "absent"`,
`use_consequence: "context_dependent"`, `materiality: "low"` — no model calls.

The 18 newly-admitted LPs (from G-cand, no prior use_impact):
LP-01/02/04/06/07/11/15/17/18/19/21/22/24/25/27/28/29/30

**OWED: Tzvi runs the keyed pipeline.** On the keyed run:
- 3 parallel evaluators assess all 18 in one batched call each
- Provenance is attached per-finding with `use_consequence_source: "assessed"` (if 5e succeeds)
- 375M write-path check is also closed by the keyed run artifact

### Compound findings (6 — annotated, no 5e)

All 6 compound findings (CRX-01 through CRX-06) carry
`compound_consequence_source: "not_assessed"`. Structurally forced — no single LP
consequence is correct for multi-LP compound findings (375P precheck: LP-01 appears in
Dir-01 AND CRX-02 AND CRX-05 AND CRX-06 — one LP, four consequence contexts).
CRX stays in current routing. COV-B will decide stay-or-demote.

---

## Validation 3: 5e Yield Table (OWED — keyed run)

This is the headline measurement COV-A was built to produce. 375N/375O could not
measure yield (keyless); COV-A is the first time 5e runs on the 18.

**Format when Tzvi runs the keyed pipeline:**

| LP    | Finding | use_consequence | materiality | confidence    |
|-------|---------|-----------------|-------------|---------------|
| LP-01 | Dir-01  | [keyed result]  | [keyed]     | [assert/weak] |
| LP-02 | Dir-02  | ...             |             |               |
| ...   | ...     |                 |             |               |

Key questions the yield table answers:
- How many of the 18 return `assert` or `assert_weak` (decisive)?
- How many return `context_dependent` (yield failure for the finding-scope gate)?
- How many return `no_evaluators` (model failure)?
- If many abstain: COV-B's landing design must route `consequence_unassessed` differently
  than `consequence_assessed + context_dependent`.

**Still-unmeasured until keyed run:** whether G-cand's 18 newly-admitted findings
produce decisive assessments. This is the open 375I-class question COV-A was built to close.

---

## Validation 4: LP-05 Spot-Check (COMPLETE — see Validation 2)

**Confirmed:** Dir-05 (LP-05, Permitted Use) carries `directionality: "tenant_unprotected"`
(Stage 7 adverse direction) AND `use_consequence: "beneficial"` (5e consequence from
pre-COV-A LP-scope run). The beneficial consequence was NOT overwritten or re-litigated
by COV-A. The new finding-scoped provenance correctly copies the LP-scope verdict.

**Doctrine check passed:** Stage 7 owns direction sign; 5e owns use-consequence magnitude.
Beneficial use_consequence on an adverse directional finding is architecturally correct,
not a contradiction.

---

## Architecture decisions confirmed by COV-A implementation

1. **G-cand gate is `finding_type == "directional_mismatch"`**, not `direction == "adverse"`
   or verification-gated. All `directional_mismatch` findings carry
   `directionality: "tenant_unprotected"` — finding_type alone is the gate.

2. **LP field in Stage 7 output is `implicated_lps`**, not `all_implicated_lps`.
   Discovered during implementation; fixed before first run.

3. **No `current_bucket` on findings** in `pipeline_results.json`. Routing bucket
   is computed downstream; provenance fields are upstream enrichment only.

4. **Finding↔LP is 1:1 for all directional findings** on this lease (per 375P precheck).
   `implicated_lps[0]` is the correct LP id for all 26 directional findings. Confirmed.

5. **LP-reuse-guard machinery not needed** — deferred/unexercised per 375P precheck.
   The many-to-many reuse problem is entirely in the compound layer (CRX), which is
   annotated `not_assessed` precisely because no single LP consequence serves it.

---

## COV-A Hard-Guard Confirmation

Per instruction, COV-A does NOT do these (all confirmed in code):
- NO routing change (Risk/Needs Review/Improvement buckets unchanged)
- NO consequence_unassessed UI bucket / Needs Review subtype (COV-B)
- NO A-rail (threshold lane deferred to lease #2)
- NO present-hostile lane (375H-C deferred; landlord_leverage_point too noisy)
- NO CRX demotion (CRX keeps Risk; COV-B decides)
- NO cam/core/ changes

---

## Queue after COV-A keyed run passes

1. **375M write-path check close** — inspect keyed artifact for `use_consequence` key
   (not `gap_impact`) in `coverage_assessment[LP-XX].use_impact`
2. **Review yield table** — is G-cand's 5e yield decisive enough for COV-B routing?
3. **375E-COV-B** — lawyer-facing landing:
   - adverse + harmful/high-med → Risk
   - adverse + beneficial/low → Improvement/favorable-position
   - adverse + unassessed → Needs Review subtype "consequence not assessed"
   - CRX stay-or-demote decided
4. **375E-DIR** — vote≠severity routing redesign
5. **375H-C** — keyed fixture matrix → schema repair for present-hostile covered LPs

**DEPLOYMENT TRAP unchanged:** 375H repair findings must NOT enter lawyer-facing Risk
until 375E-DIR routing fix is live.
