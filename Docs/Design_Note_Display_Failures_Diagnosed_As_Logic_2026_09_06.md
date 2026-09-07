# Design note — display failures keep getting diagnosed as logic failures

**Written:** 2026-09-06, at Tzvi's direction, after Step 580-1.
**Status:** observation with three instances. Not a rule; a place to look.

---

## The shape

A surface renders something wrong. The wrongness is read as evidence that the thing *behind* the
surface is wrong. The layer behind it is then changed or removed — and the display defect is
either fixed separately or was never the problem.

The cost is asymmetric. A display bug annoys a reader until someone fixes it. A logic change made
to chase a display bug removes a capability, and nothing downstream notices, because the thing
that would have noticed is the surface that was already broken.

## The three instances

**1. `covered_unfavorable`, Step 314 (2026-05-13).** A landlord-lens run showed LP-11 as
`covered_unfavorable` — a state the schema defines as *"present but materially one-sided against
tenant"* — with exposure prose reading "landlord enforcement position significantly weakened". The
instruction called the classification *"factually wrong"*. It was not: the regex had correctly found
a 15-day non-monetary cure period, which is one-sided against the tenant. What was wrong was
tenant-side prose shown to a landlord. **The detector was removed for all 32 topics.** Step 318,
four steps later in the same commit, fixed the card face that caused the misreading — its own
instruction notes the sidebar *"correctly perspective-flips"* already. The detector never came back.
Found in Step 580-1.

**2. The disclosure banners, Steps 477/571 (fixed `bea1787`).** `renderIncompleteBanner` and
`renderPanelBanner` threw on an `esc` scope boundary — and only when they had content to render, so
the failure was invisible whenever there was nothing to disclose and total whenever there was. The
banner was the product's own account of what it could not assess. A reader saw the opposite of the
truth for thirteen days.

**3. Retained dissent, Step 571-impl item 1.** The merge preserved evaluator disagreement correctly
and no surface rendered it. The data was right the whole time; the absence of a display made it
indistinguishable from consensus.

## Why it recurs here specifically

CAM's output is almost entirely *narration about a judgment*. The judgment and the sentence that
describes it are produced in different layers, by different code, under different assumptions —
and the perspective lens sits between them. So a correct judgment narrated under the wrong lens
reads exactly like an incorrect judgment. There is no visual difference between the two, and the
debugging instinct goes to the layer that produced the number.

## What to do with it

**Before changing a detector, an aggregation, or a verdict because its output looks wrong:
establish that the sentence around it is pointed at the right reader.** Specifically —

- Which lens was the run executed under, and which lens was the prose written for? Step 577 found
  these are resolved by two different mechanisms that can disagree, and that the authoritative one
  (`input_config.perspective`) is not recorded in the stored result at all.
- Is the state's *definition* party-relative? `covered_unfavorable` is defined against the tenant.
  Read under a landlord lens without the flip, every correct firing looks like a false positive.
- Does the surface that would have caught this actually render? Items 1 and 2 of 571-impl were
  reported as rendering when they only did so after a manual call.

**And when the trade is made anyway, record it as a trade.** Step 314 has no status file; the word
`unfavorable` appears in no status file for steps 311–320; the code comment asserts the replacement
is better rather than noting what was given up. Nothing surfaced it for four months.

## What this predicts

The places to look next are surfaces whose correctness is party-relative and whose upstream signal
is still live: `_isFavorable` and the Coverage & Gaps "favorable" bucket (gated on a state that
rarely fires — Step 580-1), `exposure_statement`'s 12 topics with no perspective variants (Step
577), and the 20 with variants where the variant is selected by a resolver that has no
authoritative input.
