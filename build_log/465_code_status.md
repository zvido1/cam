# Step 465 — Extraction union, computed offline

**Date:** 2026-08-23 · **Instruction:** `build_log/465_chat_instruction.md`
**DIAGNOSTIC ONLY.** No new provider calls. No pipeline change. Nothing edited.
Computed from the 18 persisted runs: `build_log/LP12_extraction_runs/` (6) and
`build_log/464_shape_runs/{unpinned,pinned}/` (12).

Shape frequencies as quoted in the brief, re-verified by digest: **A 5/18, B 12/18, C 1/18.**

---

## 1. What each shape uniquely holds

| provision | distinct `tenant_text` variants across all 18 runs | who holds which |
|---|---|---|
| LP-00 | **3** | A: 1175 · B: 2236 · C: 790 |
| LP-02 | 2 | A: 978 · B/C: 1111 |
| LP-12 | 2 | A: 767 · B/C: 0 |
| LP-17 | 2 | A: 958 · B/C: 1088 |

**The two target clauses are in disjoint shapes and neither is in C:**

- **§13.2 in LP-12 → shape A only** (5/18)
- **`"shall mean 22.4%"` anywhere → shape B only**, in LP-00 (12/18)
- **Shape C holds neither**, and is the sole holder of LP-00's 790-char variant.

**No single run has both.** All three shapes score 0/4 on full coverage of the varying provisions.

## 2. Pairs from different shapes

"Fully covered" = the union contains **every** known variant of that provision.

| union | §13.2 in LP-12 | `22.4%` | both | provisions fully covered | run-pairs |
|---|---|---|---|---|---|
| **{A,B}** | ✅ | ✅ | **✅** | **3 / 4** | 60 |
| {A,C} | ✅ | ❌ | ❌ | 3 / 4 | 5 |
| {B,C} | ❌ | ✅ | ❌ | 0 / 4 | 12 |

Of the 153 possible run-pairs, **76 are within a single shape and add nothing at all.** Only the 60
{A,B} pairs yield both clauses — **P(both) for a random pair = 60/153 = 39.2%.**

Both {A,B} and {A,C} reach 3/4 rather than 4/4 because LP-00 has three variants and any pair can hold
at most two.

## 3. Triples from different shapes

| union | §13.2 | `22.4%` | both | provisions fully covered | run-triples |
|---|---|---|---|---|---|
| **{A,B,C}** | ✅ | ✅ | **✅** | **4 / 4** | 60 |

**{A,B,C} is the only combination reaching 4/4**, because LP-00's third variant exists only in C.
For a random triple drawn from the 18, **P(both clauses) = 510/816 = 62.5%.**

## 4. Smallest N

§13.2 requires ≥1 shape A; `22.4%` requires ≥1 shape B. So
P(both) = 1 − (1−p_A)^N − (1−p_B)^N + (p_C)^N.

| N | P(both clauses) |
|---|---|
| 2 | 0.370 |
| 4 | 0.716 |
| 6 | 0.857 |
| **8** | **0.926** |
| **10** | **0.961** |
| 12 | 0.980 |
| **15** | **0.992** |
| 22 | 0.999 |

| target | smallest N |
|---|---|
| ≥ 90% | **8** |
| ≥ 95% | **10** |
| ≥ 99% | **15** |
| ≥ 99.9% | 22 |

**Full 4/4 coverage is a different and much worse problem**, because it requires shape C at 1/18:

| target | smallest N |
|---|---|
| ≥ 90% all three shapes | **41** |
| ≥ 95% | **53** |
| ≥ 99% | **81** |

**So "both clauses" costs ~10 runs; "every known variant" costs ~50.** At ~95s per extraction that is
roughly 16 minutes versus 80 minutes, per document, for the extraction stage alone.

**Two caveats on these numbers.**

1. **p_C = 1/18 is a single observation.** Its 95% confidence interval runs roughly 0.1%–27%, so the
   N-for-4/4 figures are order-of-magnitude only. The N-for-both-clauses figures rest on p_A = 5/18
   and p_B = 12/18 and are firmer, though still 18-sample estimates.
2. **This assumes the three known shapes are the whole space.** Step 464 bounded but did not exclude a
   rare fourth shape (a 5%-frequency shape would have been missed with P = 0.40). If one exists and
   holds a variant nothing else does, every coverage figure here is an overestimate.

## 5. What "union" would MEAN operationally — the ambiguity, unresolved

**This is not a detail to settle later; the two readings give materially different outputs, and the
measurement above does not choose between them.**

The runs do not disagree by adding and removing text from a common base. They disagree about
**boundaries** — where a provision starts and stops, and which sections belong to it.

**Reading 1 — concatenation / merge.** `LP-12 := A's 767 chars` (B and C contribute nothing).
`LP-00 := 1175 + 2236 + 790`.
- Recovers everything; nothing is lost.
- But LP-00's variants **overlap heavily** — all three start with the same preamble text — so naive
  concatenation duplicates it two or three times over. Downstream, `tenant_text` is what evaluators
  read and what the 305 citation gate cites into; triplicated preamble with three different section
  refs (`Preamble, Section 1.1, Section 24.15` / `Preamble, Sections 1.1, 1.2` / `Preamble,
  Section 1.1`) is not obviously readable evidence.
- It also inflates the extraction totals: 29,005 / 29,562 / 28,116 chars per run, against a 31,755-char
  lease. A three-way union is not 31,755 — it is ~86k with massive duplication.

**Reading 2 — replacement / winner-takes-all.** Pick one shape's `tenant_text` per provision, by some
rule (longest? most sections cited? majority?).
- Keeps each provision internally coherent and citable.
- **But no rule recovers both clauses.** "Longest wins" gives LP-00 = B's 2236 (holds `22.4%`) and
  LP-12 = A's 767 (holds §13.2) — that particular rule does happen to get both here. "Majority wins"
  gives B for both, which loses §13.2 and re-aborts the gate. So the rule choice *is* the behaviour,
  and it is unvalidated on anything but this fixture.

**The unresolved question underneath both:** whether a provision's `tenant_text` is a *bag of relevant
text* (concatenation is fine, duplication is noise) or *the clause* (replacement is required, and
picking wrong loses evidence). The current pipeline treats it as the latter — one string, one
`tenant_section_ref`, cited as a location. Union under Reading 1 breaks that contract; union under
Reading 2 preserves it but needs a selection rule nobody has specified.

**Not resolved here, by instruction.**

## 6. What this does not establish

- **Whether union is worth doing.** 8–15 extraction calls per document, versus 1, is the cost; nothing
  here measures the benefit against that.
- **Whether the union output would actually flip the verdicts.** No coverage run was made. That §13.2
  and `22.4%` are both *present* in an {A,B} union is a property of the text, not a demonstration that
  the panel would then read them correctly — and Step 460 showed the panel can be handed correct
  evidence and still return a false positive on adjacent material.
- **Generalisation.** One fixture, one model, 18 runs, two sittings.
- **Whether shapes recur per-document or are Atlas-specific.** Untested.
