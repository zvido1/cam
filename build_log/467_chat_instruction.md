# Step 467 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 467. Roll back section expansion. Record the result.

1. SECTION_EXPANDED_SPAN_LPS = set(). One edit. Leave the machinery in
   place — it is measured and may be wanted later; it is the flag that
   goes to empty.

2. Record in build_log/, appended to the Step-460 finding or its own file:

   - Containing-section expansion CANNOT reach §11.3 and this was
     established offline before spending runs. §11.2's section ends at
     15490; §11.3 begins at 15490. Of Step 460's two candidate directions,
     this measures the section-boundary one and rules it out. CO-RETRIEVAL
     OF ADJACENT TEXT remains untested and is the only one of the two that
     could reach a neighbouring section.

   - Cost: +81% assembled evidence, zero new element-relevant content. The
     addition is §5.1's security-deposit prose and §11.2(b),(c) — the
     material clause-body spans correctly excluded. This trades
     under-inclusion across sections for over-inclusion within one, which
     is the bucket failure reintroduced.

   - REGRESSION, and record it as the substantive result: element 4 moved
     from a correct `missing` to `disputed` / distant_split_presence_missing
     / low confidence, stably in both runs. Evaluator A flipped to
     explicitly_present quoting "draw upon the Security Deposit as a setoff
     against damages"; B and C held the offset-against-RENT distinction.
     The only change was seeing more of §5.1.

   - THE INFERENCE: more context did not improve reasoning, it supplied
     more topically adjacent material to be seduced by. This is a direct
     measurement of the operative-entailment problem — the failure is that
     topical proximity substitutes for entailment, and adding proximity
     makes it worse. Any future context-widening direction inherits this.

   - Element 6 unchanged: still explicitly_present on the indemnity. The
     false positive stands and the clause limiting damages is still absent.
     Element 7 stabilised to implicitly_present in both runs — stability on
     a wrong answer, which is worse than the baseline disagreement, since
     the disagreement at least signalled thin evidence.

Commit. Do not push. Do not deploy.
