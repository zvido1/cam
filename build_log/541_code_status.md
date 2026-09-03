# Step 541 — REPORT ONLY. `export_findings` does not exist, the change was already made at Step 539, and it cost 11% length for 3× the findings.

**Date:** 2026-09-03 · **Instruction:** `build_log/541_chat_instruction.md`
**No code changed. Nothing built. Not deployed.**

---

# 0. THE PREMISE HAS NO REFERENT — AND THE CHANGE IS ALREADY IN

**`export_findings` does not exist.** `grep -rn "export_findings"` across `cam/` and
`05 Lease Analyzer/` returns nothing.

**Nothing filters coverage on `deviates` either.** The only `DEVIATES` filtering is on the **Mode A**
template-comparison path (`final_verdict == "DEVIATES"` at `lease_docx_annotator.py:312`, `:352`,
`:684`, `lease_pdf_annotator.py:249`). Mode C coverage does not have a `final_verdict` field at all.

**The real filter is `ANNOTATED_BUCKETS`** (`lease_display.py`), tested at
`lease_docx_annotator.py:735` and `lease_pdf_annotator.py:351`:

```python
        if disp["bucket"] not in ANNOTATED_BUCKETS:
            continue
```

**And Step 539 already widened it.** Measured on the Step-537 result:

```
ANNOTATED_BUCKETS pre-539 : 12 LPs admitted
ANNOTATED_BUCKETS now     : 30 LPs admitted
newly admitted by 539     : LP-01,04,05,06,07,08,09,10,13,16,17,18,19,21,24,26,30,32
```

**LP-30 is in that newly-admitted list. LP-20 was already admitted** — Step 538's zero-elements guard
moved it to `needs_attention`, which was always in the set.

**So both LPs the brief names already appear in the DOCX and PDF**, and the "6 findings to 13" figure
matches nothing measured: it is **12 → 30 LPs**, or **7 → 23 rendered callouts**.

---

# 1. WHY THE FILTER WAS WRITTEN THAT WAY — the intent is recoverable, and it is narrower than "deviates"

`lease_display.py`, the original comment, still present:

> *"Buckets whose items get a coverage callout in the annotated PDF/DOCX (`[GAP]` stickies for
> Tenant/Neutral and the same-anchor callout block in Landlord runs). **`missing` items have no anchor
> in the document body and are excluded by the annotator regardless of bucket.**"*

**The intent was anchoring, not severity.** A margin callout has to attach to a paragraph; an LP whose
provision is absent has no paragraph to attach to. The set was chosen to admit items that *have text
in the document* — which is why `covered` was excluded, since a covered provision needed no comment.

**That reasoning was sound and is now stale.** It predates `partial_typical`, which produces items that
*do* have anchorable text and *do* have a missing element worth flagging. **The exclusion of LP-30 was
a side effect of a rule about anchors, not a decision about relevance.**

Evidence it was never a severity rule: `worth_reviewing` was always in the set, and `missing` items are
excluded *inside* the annotator loop by a separate check — severity and anchoring are handled
independently.

---

# 2. WHAT AN EXPORT SHOULD CONTAIN

**The audience is tenant's counsel reading a marked-up copy of their own lease.** For that reader:

- **A provision that exists and disfavours them is the most actionable thing in the document.** They
  can negotiate a term. They cannot negotiate an absence as easily.
- **An anchored callout is worth more than a summary line**, because it sits beside the clause. That is
  the whole value of the annotated artefact over the cover PDF.
- **An absence has no anchor**, so it belongs in the summary, not the margin — which is what the
  annotator already does.

**So the rule that follows is: the margin carries everything that has text to attach to and something
to say about it; the summary carries everything.** That is what the code now does, and it is closer to
"everything requiring attention appears" than to "the export is the short list".

---

# 3. THE VOLUME CHANGE — AND IT IS NOT DOUBLING

**This is the number the decision turns on, and it is much smaller than the finding count suggests:**

```
variant       bytes    paras      chars   [GAP] callouts
pre-539      50,639      314     44,132        7
now          52,245      330     48,841       23

delta         +3.2%     +16      +10.7%      +229%
```

**Three times the findings for 11% more text.** Sixteen extra paragraphs on a 330-paragraph document.

The reason is structural: a `[GAP]` callout is two or three short lines, while the document is
242,900 characters of lease. **The findings are not the bulk of the artefact and adding them does not
make it long.**

**"Doubling the findings could make the report less usable" is the right question and the measurement
answers it: the cost is not length.** If these 16 callouts are unwelcome it will be because they are
*low-signal*, not because they are *many* — and that is a different objection, testable by reading
them rather than counting them.

**On signal:** all 18 newly-admitted LPs are `partial_typical` — present provisions with at least one
missing element, `requires_attention: True`, materiality low. LP-30's is *"Missing: Limitation on
request frequency is addressed"* on an estoppel clause, anchored at the clause. **That is a real
negotiating point for a tenant.** Whether all 18 clear that bar was not assessed; I read one.

---

# 4. THE ARTEFACT — BEFORE AND AFTER

## LP-20 Exclusivity

**Before (as shipped at Step 537):** no callout — it was in the `covered` bucket, excluded by
`ANNOTATED_BUCKETS`.
**After (Step 538's guard):**
> *[GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW materiality)*
> *Missing: Specific exclusive use scope is defined (protected business activities), Carve-outs for
> existing tenants at the center are addressed, …*

## LP-30 Estoppel Certificate

**Before:** no callout anywhere in the DOCX. **After (Step 539's `minor_gaps`):**
> *[GAP] LP-30 Estoppel Certificate — Estoppel certificate terms undefined (LOW materiality)*
> *Missing: Limitation on request frequency is addressed*
> anchored at *"Within ten (10) days after Landlord's written request, Tenant shall execute and deliver
> to Landlord an estoppel certificate in the form reasonably required by Landlord…"*

## Document length

`50,639 → 52,245 bytes`; `314 → 330` non-empty paragraphs.

---

# RECOMMENDATION

**Keep it as it now stands. Do not narrow it back, and do not widen it further.**

The current rule — margin callouts for anything with anchorable text and a named missing element,
summary for everything — is the one the measurement supports. **The feared cost did not materialise:
11% more text, not double.**

**Two things I would NOT do:**

- **Do not add `covered` to `ANNOTATED_BUCKETS`.** A provision with every element present has nothing
  to say in the margin, and that genuinely would be length without signal.
- **Do not build the `deviates`-based filter the brief describes.** It does not exist to change, and
  recreating it would re-hide LP-20 and LP-30.

**The open question worth its own step is not the filter — it is `materiality`.** Every one of these 23
callouts reads *"(LOW materiality)"*, including LP-20 exclusivity on a shopping-centre lease, which is
implausible. **If the 23 callouts do feel low-signal, that is where the defect is**, and Steps 538 and
539 both flagged `_classify_materiality` as untouched and out of scope.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was built or changed.** This is a report, as the brief directed.
- **One document.** All volume figures are butler_crossing's. A lease with more `partial` LPs would add
  more callouts; none has been measured.
- **I read one of the 18 newly-admitted findings** (LP-30) and judged it substantive. The other 17 were
  not read, so "low-signal or not" is genuinely open.
- **The DOCX comparison used `T-04_subtle.docx` as the carrier document**, not the real ex6-4 source,
  because the fixture is `.txt`. Paragraph and byte counts are therefore relative, not the exact
  artefact a user of this lease would receive.
- **4 callouts failed to anchor** (`LP-21`, `LP-22`, `LP-29`, `LP-32`) and were dropped silently by the
  annotator — 23 rendered of 27 admitted. That is a separate defect and is not this step's subject.
