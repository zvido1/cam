# Step 464 — Shape structure: is the attractor set stable, and does pinning collapse it?

**Date:** 2026-08-23 · **Instruction:** `build_log/464_chat_instruction.md`
**DIAGNOSTIC ONLY.** No repo file changed, no prompt edited, no deployed configuration touched, no
fix attempted. 12 new extraction-only Atlas runs persisted at `build_log/464_shape_runs/`.

---

## Answers

**Q1 — the shape set is stable. No new shapes in twelve unpinned runs.**
**Q2 — pinning does NOT collapse it. This is not a decoding-configuration defect.**

## Method

Both arms call the real `extract_provisions_single_doc` — same prompt, schema, model, temperature and
token budget. The pinned arm adds `top_p=0.0, top_k=1` by wrapping
`google.genai.models.Models.generate_content_stream` **in the probe process only**; `lease_extract.py`
and `provider_router.py` are untouched. The harness logs the decoding parameters actually transmitted
on every call, so the pinning is evidenced rather than assumed:

```
unpinned run 1: ... cfg={'temperature': 0.0}
pinned   run 1: ... cfg={'temperature': 0.0, 'top_p': 0.0, 'top_k': 1}
```

Shape identity is a SHA-256 over all 33 provisions and every field, not the LP-12/LP-00 summary
numbers — a new shape coinciding on those would still be caught.

## Q1 — shape distribution across all twelve unpinned runs

| arm | A | B | C | new |
|---|---|---|---|---|
| Step 463 (runs 1–6) | 2 | 3 | 1 | — |
| Step 464 unpinned (runs 1–6) | 1 | 5 | 0 | **0** |
| **twelve unpinned total** | **3** | **8** | **1** | **0** |

**Exactly three distinct digests across all 18 runs including the pinned arm.** No shape D.

```
shape A = 1a230918a7ba8547   LP-12=767  LP-00=1175
shape B = 71b09b36ab9f306c   LP-12=0    LP-00=2236
shape C = f232bc566569794d   LP-12=0    LP-00=790
```

**The attractor set is small and enumerable, which makes this tractable** — the condition the brief
set for the easier fix.

**With the bound stated honestly.** Shape C has appeared once in 18 runs (5.6%) and only in the
original set, so rare shapes are not excluded. Probability a fourth shape would be missed entirely in
18 runs, by its true frequency:

| true frequency | P(missed in 18 runs) |
|---|---|
| 30% | 0.002 |
| 20% | 0.018 |
| 15% | 0.054 |
| 10% | 0.150 |
| 5% | 0.397 |

So **a common unseen shape is excluded; a rare one is not.** "Three attractors" is safe as "three
common attractors", and any enumeration-based fix must handle an unseen tail rather than assume
closure at three.

## Q2 — pinning `top_p`/`top_k` changes nothing

| arm | A | B | C |
|---|---|---|---|
| pinned (6 runs) | **2** | **4** | 0 |

**It did not collapse to one shape.** Both arms produce the same two common shapes.

The strongest form of the result: **the pinned runs are byte-identical to the unpinned runs.** They do
not merely resemble them — they reuse the *same digests*:

```
shape A = 1a230918a7ba8547   463 runs 1,4  |  unpinned 4    |  pinned 2,3
shape B = 71b09b36ab9f306c   463 runs 2,3,5 | unpinned 1,2,3,5,6 | pinned 1,4,5,6
```

Greedy pinning did not shift the outputs, did not narrow them, and did not produce a new one. The
shape-A rate is 3/12 unpinned vs 2/6 pinned — **Fisher exact two-sided p = 1.000**, no detectable
difference. (Sample is small; a modest shift is not excluded, but a collapse plainly is.)

**Conclusion: the variance is not explained by unpinned decoding parameters.** The fix is not a config
line. Whatever selects between shapes A, B and C survives `temperature=0.0, top_p=0.0, top_k=1`.

## Operational notes

All 12 runs completed on the primary model, `fallback_used: false`, no errors. Elapsed 88.7–99.2s
except **pinned run 4 at 210.3s**, a latency outlier that produced shape B with the standard digest —
no correlation with shape.

## What this does and does not license

**Supports:** the LP-12 gate abort is a *discrete* phenomenon with a small common attractor set, not
continuous jitter that happens to cluster. Enumeration is a viable basis for a fix.

**Rules out:** decoding configuration as the cause. `temperature=0` was already transmitted
(Step 463 Q4), and adding greedy `top_p`/`top_k` changes nothing.

**Not established:**
- **Why** the model selects a shape. Still unmeasured — this step narrowed the cause, it did not find it.
- Whether a seed would collapse it. The Gemini API surface used here exposes no seed parameter in the
  config path the adapter builds; not attempted.
- Whether the three shapes reproduce on other documents or are an Atlas artifact. One fixture.
- Whether the distribution is stationary. 18 runs across two sittings on 2026-08-20 and 2026-08-23;
  shape C appeared only in the first.
- Whether server-side factors (model version pinning behind the `-preview` alias, batching,
  mixture-of-experts routing) account for it. Outside what this harness can see.
