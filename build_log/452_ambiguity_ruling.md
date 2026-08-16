# 452 — Ambiguity Ruling: envelope-ambiguous citations in `field_support`

**Decided:** 2026-07-26 by Tzvi.
**Raised by:** Chat instance (Step 450, the open item in the replay-feasibility ruling).
**Ruled by:** GPT adversarial reviewer, accepted by Tzvi with one correction from Chat (§3 below).
**Status:** RATIFIED. Token-bound input to the Step-452 production package (`452_deterministic_rules.json` item 2).

---

## 1. The question

Part A §4.5 invalidates an evaluator's judgment on a field when a citation listed in that field's `field_support` **does not resolve**. It does not address a citation that resolves **ambiguously** — one that matches more than one location.

An ambiguous citation is not a non-resolving one. It resolves; it simply does not resolve uniquely. Nothing in Part A or Part B decides what happens to the field it grounds.

## 2. The ruling

**An envelope-ambiguous citation listed in a field's `field_support` invalidates that evaluator's judgment on that field.**

It is not silently discarded while the field survives on whatever other citations happen to remain.

### Resolution table (frozen)

For each citation id listed under a field's `field_support`, resolved within the exact envelope shown to that panelist:

```
0 matches within the cited envelope
    → UNVERIFIED
    → evaluator field invalidated

1 match within the cited envelope
    → VERIFIED
    → materialize as an absolute-offset EvidenceSpan

2+ matches within the cited envelope
    → AMBIGUOUS
    → evaluator field invalidated
```

The quote remains in the raw audit record in the zero-match and multi-match cases. It does not enter `semantic_support_spans`.

## 3. THIS IS AN EXTENSION, NOT A READING

**Stated explicitly because an auditor checking Part A §4.5 will not find this rule there.**

The reviewer's ruling justified the decision by holding that §4.5 controls over a "looser sentence in §7.1 saying a non-resolving citation is dropped and, if load-bearing, lowers confidence." **§7.1 says no such thing.** Its actual text:

> a context citation that does not resolve is **dropped and, per §4.5, invalidates the field it was grounding** (the affected evaluator's judgment on that field downgrades to `unclear`/`not_assessable`) [...] It does not silently vanish, and it does not survive as a substantive judgment with merely reduced confidence.

§7.1 already carries the v5 rule and cross-references §4.5. There is no precedence conflict and nothing to override.

Both sections address citations that **do not resolve**. Neither addresses ambiguous ones. 423A expressly deferred the question:

> `ambiguous` is recorded but not used canonically (whether it may serve as degraded diagnostic evidence is an explicitly later decision — 423 spec §4)
> — `cam/adapters/lease_review/lease_evidence_spans.py`, `is_usable_in_canonical_stage5`

So this ruling **extends §4.5 to the ambiguous case**, decided 2026-07-26. It is not derivable from the ratified text and must never be presented as though it were.

## 4. Reasoning

Dropping one ambiguous citation while preserving the field would rewrite the model's evidentiary basis after the outcome was visible. Part A §7.1 requires the certified package to carry the context quotes the panel **actually relied upon**, not a cleaned-up subset chosen later by a replay.

Letting the omission make the anti-borrowing rule vacuously true would also reward the instrument for deleting the thing it was supposed to police.

### What "failed trace kills the trace, not the evidence" means

Part A §4.5's asymmetry is preserved:

- the primary candidate span remains untouched;
- cited-union retention (§5.1) does not erase the candidate;
- other fields with independently valid support remain intact;
- other evaluators remain intact;
- **the affected evaluator's unsupported field vote does not survive.**

It does **not** mean an unsupported field remains substantive because another citation might have been enough.

### No inference of citation redundancy

A future schema could encode citation sufficiency explicitly — conjunctive versus alternative support. This one does not. Inferring redundancy after seeing the result would be fresh semantic authorship in deterministic clothing. Not permitted.

## 5. Envelope-constrained resolution (forced, not chosen)

Ambiguity is measured **within the exact envelope shown to that panelist**, never document-wide.

A panelist saw only `canonical_text[context_start_char:context_end_char]`. A quote it emitted can only have come from there. Crediting a document-wide occurrence it could not see would fabricate provenance.

This is forced by the facts of what was observable, not selected among alternatives.

### Consequence for the substrate

`resolve_span` **cannot be used** for context citations. It searches document-wide and returns `AMBIGUOUS` whenever a quote occurs more than once anywhere in the lease, including when it is unique inside the envelope. Using it would manufacture ambiguity and invalidate fields that are sound.

The correct construction imports `_find_normalized_matches`, which returns every match location, filters to the envelope window, and applies the table in §2 to the filtered set. See `452_production_package_instruction_v8.md` §4.3.1, the ratified instruction bound in §3.1.

> **Citation repointed 2026-08-15.** This line previously cited `452_production_package_instruction_v2.md` §4.3.1 — an unbound superseded draft. This ruling is a §3.1 artifact the manifest hashes; v2 is not. A bound artifact delegating its correctness claim to an unbound one is the producer-binding defect R21 closed, in citation form: citing artifact bound, cited authority unbound. Editing v2 after the manifest was built would have changed this ruling's stated authority while every hash still verified. Found by Claude Code during the unbound-evidence sweep. Binding v2 would have been the wrong fix; v8.2 is both bound and ratified, and the construction it describes at §4.3.1 is unchanged from v2's.

`resolve_span`'s `source_anchor` / `section_ref` disambiguation path is **inert** here: the P4 schema records neither for context citations. The path exists and has no input, and that fact is recorded rather than passed over silently.

## 6. Scope

- Applies to citations listed under a field's `field_support`.
- An ambiguous citation appearing **elsewhere** in a panelist's response, not supporting the field under test, does not affect that field.
- Applies to all six substantive semantic fields per Part A §4.1, except where a field is schema-fixed `not_applicable` (§4.5's own carve-out).
- The invalidated value is `unclear` for every field. `not_assessable` is **not** used: per Part A §5.2 it belongs to the `agreement_by_field` vocabulary, not to the per-field judgment enums, and using it as a field value would introduce a token the merge functions do not recognise.

## 7. Anticipated effect, recorded before it is measured

This rule applies §4.5 at a granularity package P4 did not enforce. It may unseat prior `satisfied` states.

Step 450 found one non-resolving context citation in the as-computed state (cand_03, panel 4, role C, `xc1`). **The ambiguity pass has not been run and its scope is unknown to every party at the time of this ruling.** No one read which traces are affected before this document was committed.

Any resulting count is what this rule produces over frozen judgments. It neither supersedes nor is superseded by what P4 computed.
