# Step 466 — Section-expanded spans, LP-27: measured

**Date:** 2026-08-23 · **Instruction:** `build_log/466_chat_instruction.md`
**MEASUREMENT.** Two runs, clean panel (`gpt-5.5` 197/197, `is_fallback` False on both).
Change gated behind `SECTION_EXPANDED_SPAN_LPS = {"LP-27"}`. Nothing tuned. Not deployed.

---

## Headline: §11.3 does not reach the panel, and cannot by this mechanism

**Answer to the step's question: NO, and it was determinable before the runs.**

```
[Section 5.1]   offsets  8631- 9905   1272 chars
[Section 11.2]  offsets 14905-15490    583 chars
'Limitation of Liability' present: False   '11.3' present: False
```

§11.2's section ends at **15490**. §11.3 *begins* at **15490**. Section expansion widens a span to its
**containing** section; the liability cap is a **different** section, so expansion stops precisely at
its doorstep — the same 239-character gap Step 460 recorded, now reached by a wider route rather than
closed.

**Zero mentions of the liability cap, consequential damages, or §11.3 in any evaluator's reasoning,
either run.** The panel cannot weigh what it was not shown.

Step 460 §1B named two candidate directions. This measures the **section-boundary** one and finds it
does not address the gap. The other — **co-retrieval of adjacent text**, or a non-element-driven
limitations pass — remains untested and is the only one of the two that could reach §11.3.

## What the expansion did change

| | baseline (457, clause bodies) | expanded (466) |
|---|---|---|
| assembled text | 1043 chars | **1886 chars** (+81%) |
| span/section count | 8 spans | **2 sections** |
| found / missing / unclear | 8 / 1 / 0 | **8 / 0 / 0** |
| coverage_state, materiality, confidence | partial · high · high | partial · high · high |
| calls, elapsed | 94, ~723s | 94 & 93, 719s & 727s |

**+843 characters bought no new evidence for any element.** The added text is §5.1's security-deposit
prose and §11.2's subsections (b) and (c) — the material clause-body spans had correctly excluded.
This is the "over-inclusion within a section" failure that extraction buckets had; the expansion trades
one of Step 460's two failure modes for the other rather than removing either.

## Element-by-element, against the Step-457 baseline

| element | b1 | b3 | x1 | x2 | |
|---|---|---|---|---|---|
| 1 Landlord default defined | EXP | EXP | EXP | EXP | |
| 2 Written notice of default | EXP | EXP | EXP | EXP | |
| 3 Cure period | EXP | EXP | EXP | EXP | |
| **4 Self-help / offset against rent** | **MIS** | **MIS** | **disputed** | **disputed** | **← MOVED** |
| 5 Right to terminate | EXP | EXP | EXP | EXP | |
| **6 Monetary damages** | EXP | EXP | **EXP** | **EXP** | still false-present |
| **7 Specific performance** | EXP | IMP | **IMP** | **IMP** | stabilised, still false-present |
| 8 Lender notice and cure | MIS | MIS | MIS | MIS | |
| 9 Common law remedies preserved | EXP | EXP | EXP | EXP | |
| 10 Remedies cumulative | IMP | IMP | IMP | IMP | |

Merge reasons, both runs: `{None: 9, distant_split_presence_missing: 1}`.

### Element 4 — a previously clean element regressed

**This is the cost, and it is not small.** Step 460 recorded element 4 as the panel's best moment: the
one place it *declined* a near-miss, because the element asks for offset **against rent** and the lease
gives setoff **against the security deposit**. Baseline: unanimous-enough `missing`, both runs.

With the full §5.1 in view, A flipped:

- **A (claude-sonnet-4-6) → `explicitly_present`**, citing `Section 5.1`, quoting *"Tenant shall have
  the right to draw upon the Security Deposit as a setoff against damages"*: *"…which constitutes an
  explicit self-help and offset [right]"*.
- **B (gpt-5.5) → `missing`**: *"The lease allows Tenant to draw upon the Security Deposit as a setoff
  against damages, but it does not expressly allow Tenant to perform Landlord's obligation or offset
  costs against Rent."*
- **C (grok-4.3) → `missing`**: same distinction, same conclusion.

Merged: **`disputed`**, reason `distant_split_presence_missing`, confidence `low`. Identical in both
runs — a stable regression, not noise.

B and C held the exact distinction they held at baseline. **A did not, and the only thing that changed
was that it was shown more of §5.1.** The element left `elements_missing` — which is why the count went
1 → 0 — but it did not join `elements_found`; it now sits in neither, as a low-confidence dispute.

### Element 6 — unchanged, and the fuller §11.2 did not help

Still `explicitly_present` at high confidence in both runs, still resting on §11.2's indemnity. The
expansion added §11.2's subsections (b) and (c) — negligence, condition of common areas — which are
further from a damages grant, not closer. A and B cite §11.2; C cites §5.1's *"setoff against damages"*
and reasons the two "collectively" imply a damages remedy.

**The false positive Step 460 identified is unchanged.** Nothing in the expanded evidence grants Tenant
damages for landlord default, because the lease contains no such grant, and the clause that *limits*
what damages are available is exactly the one still missing.

### Element 7 — stabilised, still not supported by the text

Baseline disagreed across runs (EXP / IMP); both expanded runs return `implicitly_present`, all three
evaluators, high confidence. That is a real improvement in *stability*. It is not a correction: every
judgment still rests on §5.1's savings clause, and `"specific performance"`, `"injunctive"` and
`"equitable relief"` remain 0-hit in the lease.

## Cost summary

- **Evidence size:** +81% (1043 → 1886 chars) for zero new element-relevant content.
- **Regression:** one previously clean element (4) degraded from correct `missing` to
  low-confidence `disputed`, stably, in both runs.
- **Improvement:** one element (7) stabilised across runs, without becoming correct.
- **Provider cost:** unchanged — 94 and 93 calls, 719s and 727s, versus 94 calls / ~723s at baseline.
  Expansion is free at the API layer; it is a text-assembly change.
- **Gate tax:** 3 aborts across 5 attempts (`LP-12`), consistent with the standing rate.

## Verdict on the direction

**On its own terms this direction fails.** It does not deliver §11.3, it enlarges the evidence by 81%
with no informational gain, and it costs a previously correct verdict. The one benefit — element 7's
run-to-run stability — is stability on a verdict that is still wrong.

Rolling back is one edit: `SECTION_EXPANDED_SPAN_LPS = set()`.

**Not recommending a decision here** — the brief said report whichever way it lands, and this is where
it landed.

## What is NOT established

- Whether **co-retrieval of adjacent text** (the other Step-460 candidate) reaches §11.3. Untested;
  it is the only one of the two that could, since §11.3 is a neighbouring section rather than
  containing text.
- Whether element 4's regression generalises, or is specific to §5.1's structure — a landlord-default
  paragraph appended to a security-deposit clause.
- Whether expansion would help any *other* LP. LP-27 only; LP-07 was left unexpanded and unchanged.
- Two runs. The regression is identical in both, but n=2.
