# Step 484 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 484. Seam LP-12 and make the gate seam-aware. Two changes.

1. Add LP-12 to SPAN_EVIDENCE_LPS.

2. The completeness gate must not abort on an LP whose evidence comes from
   spans rather than buckets. It currently runs on extraction["provisions"]
   upstream of coverage and would still see an empty LP-12 bucket.

   Report the design BEFORE the diff. The gate needs to know which LPs are
   seamed, and SPAN_EVIDENCE_LPS lives in lease_coverage.py while the gate
   is in lease_adapter.py. State how you propose to make that visible
   without creating a circular import or a second source of truth.

   The gate's exemption must be conditional on the seam actually
   PRODUCING evidence, not merely on the LP being listed. If elicitation
   falls back — as LP-07 did on divall, zero spans, logged fallback — the
   LP is back on the bucket path and the gate's original reasoning applies.
   State how you handle that ordering, given the gate runs first.

   If the honest answer is that a seamed LP cannot be exempted before
   coverage runs without restructuring, say so. Moving the gate after
   coverage is a larger change and I would rather know than have it
   attempted.

TEST
Atlas and divall, full-LP, canonical, up to four attempts each.
  - abort rate. Atlas's predicted rate is ~72% without this; divall is
    100%. What is it now?
  - LP-12's coverage entry on both. Does it find §13.2 via spans, and does
    the entry match Step 482's bucket-sourced one?
  - does divall complete again? Step 478 got the first completed divall
    result and Step 481 destroyed it.
  - LP-07 and LP-27 unchanged?
  - cost: calls and elapsed against Step 482.

Do NOT tune. Report whichever way it lands.

---

## DESIGN, stated before the diff

**The honest answer to the framed question: a seamed LP CAN be exempted before coverage runs, without
restructuring the gate. The fix is to move the ELICITATION earlier, not the gate later.**

### 1. Single source of truth, no circular import

`lease_coverage.py` contains **0** references to `lease_adapter`; `lease_adapter` already imports from
`lease_coverage` (`:875`, `:1518`). So the dependency direction adapter → coverage is established and
safe. `SPAN_EVIDENCE_ENABLED` / `SPAN_EVIDENCE_LPS` stay where they are and are **imported**, not
duplicated. No second source of truth, no new coupling direction.

### 2. Exemption conditional on PRODUCTION, not membership — solved by ordering

The span computation is already a self-contained pre-loop block in `assess_coverage` (`:277-293`). It
is extracted verbatim into a module-level `build_span_evidence(full_tenant_text)` and called from
`lease_adapter` **before the gate**. `assess_coverage` gains an optional `span_evidence` parameter and
uses the precomputed value when supplied, otherwise computes it exactly as now (backward compatible;
existing callers and tests unaffected).

The gate then exempts an LP only if it appears in the **computed** dict — which `_assemble_span_evidence`
populates solely when elicitation returned verified spans. An LP-07-on-divall style fallback (zero
spans, logged error, returns `(None, [])`) never enters the dict, is **not** exempted, and the gate's
original reasoning applies unchanged.

**So the exemption is conditional on evidence actually existing, evaluated before the gate runs.**

### 3. What this costs, stated plainly

Elicitation now runs **before** the gate. On a run that aborts for a different LP, those calls are
spent and discarded — ~1 provider call per seamed LP (3 LPs ≈ 3 calls, ~3% of a 96-call run). That is
the price of answering the gate's question honestly, and it is paid only on aborting runs.

### 4. What was rejected

- **Unconditional exemption by membership** — violates the brief's requirement and reintroduces the
  exact harm the gate prevents when elicitation falls back.
- **Moving the gate after coverage** — the larger change the brief warned about. Not needed.
- **Duplicating the LP set in `lease_adapter`** — a second source of truth that would drift.
