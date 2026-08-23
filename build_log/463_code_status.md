# Step 463 — LP-12 extraction gate: diagnostic

**Date:** 2026-08-23 · **Instruction:** `build_log/463_chat_instruction.md`
**DIAGNOSTIC ONLY.** Nothing changed. No runs made — all four questions answered from the six
persisted runs at `build_log/LP12_extraction_runs/` and from source.
**Side-track. Nothing in the patent plan depends on it.**

---

## Headline

**These are not six independent samples. They are three discrete output shapes, and runs within a
shape are byte-identical across all 33 provisions.**

| shape | runs | LP-12 | LP-00 | where `22.4` lands | total extracted chars |
|---|---|---|---|---|---|
| **A** | 1, 4 | **767 chars, `TENANT_ONLY`** | 1175 | **nowhere** | 29,005 |
| **B** | 2, 3, 5 | 0 chars, `AMBIGUOUS` | 2236 | `LP-00` | 29,562 |
| **C** | 6 | 0 chars, `AMBIGUOUS` | 790 | **nowhere** | 28,116 |

The calls were genuinely independent: sequential timestamps from `2026-08-20 09:31:41`, elapsed
95.7–109.5s, `fallback_used: false` on all six, same primary model, no caching layer.

**Two byte-identical 33-provision extractions occurring twice over is not what independent sampling
noise looks like.** It suggests a small number of discrete attractors rather than per-field jitter.

---

## Q1 — Does anything else differ? Yes. A great deal.

**The four non-cross-filing runs are NOT identical to each other** — runs 2, 3, 5 are identical, run 6
is its own shape. **The two cross-filing runs ARE identical to each other** (runs 1 and 4).

Digest over all 33 provisions: 3 distinct values. **Digest excluding LP-12 entirely: still 3 distinct
values, clustering identically.** So the shapes do not differ *only* in LP-12.

- **Shape A vs Shape B: 23 of 33 provisions differ.**
- **Shape B vs Shape C: 24 of 33 provisions differ.**

Most differences are in `alignment_notes`, which is free prose and expected to vary. But **four
provisions differ in actual extracted evidence**:

| provision | shape A | shape B | shape C |
|---|---|---|---|
| LP-00 | 1175 chars · `Preamble, Section 1.1, Section 24.15` | 2236 · `Preamble, Sections 1.1, 1.2` | 790 · `Preamble, Section 1.1` |
| LP-02 | 978 | 1111 | (= B) |
| LP-12 | 767 · `Sections 13.2, 14.2` | 0 · `''` | 0 · `''` |
| LP-17 | 958 · `Sections 24.4, 24.11, 24.13` | 1088 · `Sections 24.3, 24.4, 24.11, 24.13` | (= B) |

**LP-12 is not a special case. It is one of four provisions whose evidence moves, and the only one the
completeness gate happens to police.** The gate fires on LP-12 because LP-12 is on the required list
and its variance happens to reach zero characters; LP-00, LP-02 and LP-17 vary silently.

### The finding that matters most — the two defects are the same defect

**The shape where §13.2 gets cross-filed into LP-12 is exactly the shape where the Proportionate Share
definition disappears from extraction entirely.**

- **Shape A** (runs 1, 4): LP-12 populated → **gate PASSES** → and `22.4` is in **no provision at all**.
- **Shape B** (runs 2, 3, 5): LP-12 empty → **gate ABORTS** → and `22.4` is in LP-00.

So on this fixture, **the runs that survive the gate are the runs that have lost the definitional
clause**, and the runs that abort are the ones that at least retained it (albeit in LP-00, an unscored
sink that produces no coverage entry, so it is unusable by analysis either way).

`FINDING_definitional_clause_loss.md` recorded the LP-00 signature as *"2236 chars holding it, 1175
without"*. Those are exactly shape B and shape A. **The LP-12 gate abort and the Proportionate Share
loss are not two bugs. They are two observable faces of one unstable assignment pass**, and they are
anti-correlated.

## Q2 — Does LP-24 differ? No. Not at all.

**`LP-24.tenant_text` is byte-identical in all six runs**: 1310 characters,
`tenant_section_ref = "Sections 13.1, 13.2, 13.3"` in all six, containing `Termination Right` and the
§13.2 body in all six. The only LP-24 field that varies anywhere is `alignment_notes` (prose).

Confirmed too that the 767-char LP-12 text on shape A is a **duplicate**, not a move: its §13.2
sentences are also present inside LP-24's 1310 chars on the same run.

**So the variance is purely in the second placement, exactly as the brief supposed.** The primary
assignment of §13.2 to LP-24 is perfectly stable. This rules out "the whole assignment is unstable and
LP-12 is just where it shows" — for §13.2. It does **not** rule that out for the document as a whole,
because LP-00/LP-02/LP-17 do move (Q1).

## Q3 — What does the prompt say about a clause serving multiple issue areas?

**Nothing. The concept is unmentioned in all 117 lines.**

There is no instruction to cross-file, no permission to, and no prohibition. A search for
`multiple`, `more than one`, `cross`, `also`, `both`, `exclusiv`, `duplicat`, `only one`,
`same clause`, `once`, `assign` returns only the status-vocabulary lines, which are about
`NOT_APPLICABLE` vs `AMBIGUOUS` and say nothing about placement.

The governing instruction is per-issue-area and, read literally, describes independent searches:

> `For each issue area listed above:`
> `1. Locate the clause(s) in the LEASE DOCUMENT that address this issue area. Use the issue area's name and description to guide your search.`
> `2. Extract the COMPLETE clause text, including all subsections and sub-paragraphs. Do not summarize — copy the full language verbatim.`

Nothing in that loop tells the model whether a clause already extracted for LP-24 remains eligible for
LP-12. The three `CRITICAL` blocks that follow — COMPLETE EXTRACTION, OMISSION DETECTION, ADDITIONAL
SUBSECTIONS — all push toward extracting *more* text, and none addresses placement across areas.

**So the 2-of-6 is the model choosing unprompted, not the model disobeying.** As the brief notes, that
is a different fix: there is no instruction to enforce, and the behaviour is currently undefined rather
than violated. Whichever way it resolves, today both answers are prompt-conformant.

## Q4 — Is temperature actually 0? Yes, and it is transmitted.

**Config** — `cam/adapters/lease_review/lease_extract.py:885-894`, the single-doc extraction path:

```python
target = ModelTarget(
    name=f"{provider}:{model_name}-extraction-single-doc",
    provider=provider,
    model=model_name,
    priority=chain_idx + 1,
    max_output_tokens=current_max_output,
    temperature=0.0,
    timeout_sec=timeout,
    max_retries=0,
)
```

**Transmission** — `cam/core/provider_router.py:519-523`, `GoogleGenAIAdapter.call`:

```python
# Build config
config = {
    "temperature": target.temperature,
    "max_output_tokens": target.max_output_tokens,
}
```

Unconditional. No capability gate, no omission branch.

**And the model is not silently defaulting like gpt-5.5.** The omission mechanism exists, but it is an
explicit allow-list that gemini is not on — `provider_router.py:30`:

```python
TEMPERATURE_ONLY_DEFAULT_MODELS: frozenset = frozenset({
    "gpt-5.5",   # Only accepts temperature=1 (provider default). Probe 2026-07-12.
})
```

`EXTRACTION_CHAIN[0] = ("google", "gemini-3.1-pro-preview")` is absent from that set, and the router
raises rather than silently dropping the parameter for an unlisted model (*"Either add the model to
TEMPERATURE_ONLY_DEFAULT_MODELS (with probe evidence) or transmit the parameter"*).

**`temperature=0.0` is genuinely reaching the extractor, and the three-shape variance occurs anyway.**

Worth noting for whoever fixes this: temperature 0 is a greedy-decoding request, not a determinism
guarantee. No seed is set, and `top_p`/`top_k` are not pinned in the config above. Whether that
explains three stable attractors rather than continuous jitter is **not established here** — I did not
probe it.

## What is NOT established

- **Why** the model picks a shape. Three attractors is the observation; the mechanism is not measured.
- Whether the shape distribution is stable over time, or specific to that 09:31–09:42 window on
  2026-08-20. Six runs, one sitting.
- Whether shapes A/B/C reproduce on other documents, or are an Atlas artifact.
- Whether pinning `top_p`/`top_k`/a seed collapses the shapes. Not tried — that is a fix.
- Whether the LP-00/LP-02/LP-17 variance has downstream consequences the way LP-12's does. LP-00 is an
  unscored sink; LP-02 and LP-17 vary in evidence but were not traced to any verdict here.
