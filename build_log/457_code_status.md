# Step 457 — Status: the locator prefix, measured

**Instruction:** `build_log/457_chat_instruction.md`
**Date:** 2026-08-23
**Status:** COMPLETE for the named objective. **2 of 3 runs landed** — run 2 lost all four attempts to
the LP-12 gate. Nothing tuned, no seam change, no design decision.
**Not committed. Not deployed.**

---

## Panel check — PASSED, run before spending anything

`EVALUATOR_B_PRIMARY = openai:gpt-5.5`, called through the same `ProviderRouter` / `_get_adapter`
path `_do_single_call` uses:

```
served=openai:gpt-5.5  3.1s  usage={'output_tokens': 28, 'input_tokens': 19, 'reasoning_tokens': 18}
response: 'OK'
```

No 429, no chain entry, `is_fallback=False`. Stop condition did not trigger.

**Confirmed in the runs themselves** — role-B census across all verdicts, all 33 LPs:

| run | role-B models | is_fallback |
|---|---|---|
| 1 | `gpt-5.5: 197` | `False: 197` |
| 3 | `gpt-5.5: 197` | `False: 197` |

**197/197 primary in both runs.** The Step-456 confound (191/197 fallback) is absent. These runs are
comparative-grade; the earlier pair were not.

## THE QUESTION — yes. All eight survive.

**LP-27, per run:**

| | run 1 | run 3 |
|---|---|---|
| elements_found | **8** | **8** |
| elements_missing | 1 | 1 |
| neither (unclear) | **0** | **0** |
| coverage_state | **partial** | **partial** |
| materiality | high | high |
| confidence | **high** | **high** |
| merged verdicts | 7 EXP, 1 IMP, 2 MIS | 6 EXP, 2 IMP, 2 MIS |
| merge reasons | `{None: 10}` | `{None: 10}` |
| tenant_text / spans | 1043 chars / 8 | 1043 chars / 8 |

**Zero elements remain unclear, so the "for each element still unclear, report the merge reason"
question has no rows.** `citation_required_but_absent` does not appear anywhere in either run — the
reason field is `None` on all 10 elements, both runs.

Before and after, per element:

| element | s4 | s5 | n1 | n3 |
|---|---|---|---|---|
| Landlord default is defined | UNC | UNC | **EXP** | **EXP** |
| Tenant must give written notice of default | UNC | UNC | **EXP** | **EXP** |
| Cure period specified | UNC | UNC | **EXP** | **EXP** |
| Perform and offset against rent | MIS | MIS | MIS | MIS |
| Right to terminate on uncured default | UNC | UNC | **EXP** | **EXP** |
| Right to monetary damages | UNC | UNC | **EXP** | **EXP** |
| Specific performance / injunction | UNC | UNC | **EXP** | **IMP** |
| Lender notice and cure period | MIS | MIS | MIS | MIS |
| Common law remedies preserved | UNC | UNC | **EXP** | **EXP** |
| Remedies cumulative | UNC | UNC | **IMP** | **IMP** |

LP-level: `review_needed` / confidence `low` → **`partial` / confidence `high`**. The two `missing`
elements were `missing` before the locator too — those are genuine absences, unchanged.

One element differs between the two new runs (specific performance: EXP vs IMP). Both are
presence-tier, so `elements_found` is 8 in both.

## The sharpest test — LP-07 now cites the supplied locator

`proportionate_share_calculation` is in `elements_found` in both runs. `section_ref`:

| run | A | B | C |
|---|---|---|---|
| **s457_r1** | `'Section 1.2'` | `'Section 1.2'` | `'Section 1.2'` |
| **s457_r3** | `'Section 1.2'` | `'Section 1.2'` | `'Section 1.2'` |

All three evaluators, both runs, `citation_quality='section_and_quote'`. Compare the pre-locator
runs, where no evaluator ever produced a section number:

| run | A | B | C |
|---|---|---|---|
| seam_out | `None` | `'LP-07 CAM provision, paragraph 1'` | `'"Proportionate Share" shall mean'` |
| seam_out_r2 | `None` | `'LP-07 CAM Provision, paragraph 1'` | `None` |
| seam_out_r3 | `None` | `'Proportionate Share paragraph'` | `None` |
| seam2lp_r4 | `None` | `'Paragraph 1'` | `'Proportionate Share definition'` |
| seam2lp_r5 | `None` | `'Para. 1'` | `None` |

**`Section 1.2` is exactly the locator the Step-455 offline check derived** for the Proportionate
Share definition — the section the definition genuinely lives in, and one no evaluator produced in
any of the five prior runs. **The prefix is doing the work, not luck.**

## Every citation audited against what the prefix actually emitted

Parsed the `[...]` prefixes from each LP's assembled `tenant_text` and checked every evaluator
citation against that set (normalising `Section 5.1` / `5.1`):

| run | LP | prefixes emitted | non-null citations | match supplied | not supplied |
|---|---|---|---|---|---|
| r1 | LP-07 | 1.2, 3.3 ×3, 3.4 | 15 of 18 | **15** | 0 |
| r1 | LP-27 | 5.1 ×6, 11.2 ×2 | 26 of 30 | 25 | **1** |
| r3 | LP-07 | 1.2, 3.3 ×3, 3.4 | 15 of 18 | **15** | 0 |
| r3 | LP-27 | 5.1 ×6, 11.2 ×2 | 26 of 30 | **26** | 0 |

**81 of 82 non-null citations are locators the prefix supplied.** No `Paragraph N`, no clause-prose
labels, in either run.

**The single exception**, recorded not smoothed: run 1, role B, element *"Tenant must notify lender
and afford lender cure period"* → `section_ref='LP-22 Sections 19.1-19.3'`. That is a cross-LP
reference, not one of LP-27's supplied prefixes. Its merged verdict is `missing`, so it passed
nothing through the gate — but it shows the manufacture behaviour is reduced, not eliminated, and it
appears on precisely the element with no supporting span.

## Run-level

| run | aborts | calls | elapsed | wall |
|---|---|---|---|---|
| 1 | 0 | 94 | 727.5s | 1205.7s |
| 2 | **4 — no result** | – | – | – |
| 3 | 0 | 94 | 718.0s | 1194.3s |

## LP-12 gate — attribution now resolved

The untruncated message, captured this run:

```
Extraction completeness failure: 1 required LP(s) have missing evidence and are not classified
NOT_APPLICABLE. Failed LPs: ['LP-12']. Cannot produce a valid legal analysis report from incomplete
evidence. Detail: [{'provision_id': 'LP-12', 'tenant_text_len': 0, 'extraction_status': 'AMBIGUOUS', ...
```

**It is LP-12**, `tenant_text_len=0`, `extraction_status=AMBIGUOUS`. Previous status files recorded
this attribution as inherited and unverified because the harness truncated the exception at 90
characters. **It is now measured.** `FINDING_span_seam_citation_gap.md` should be read with that
correction.

Session tally: 4 aborts / 6 attempts this step; 14 aborts / 18 attempts across the session.

## What is NOT established

- **Third replicate.** Run 2 lost all four attempts. Two runs, not three.
- **Whether the verdicts are correct.** Measured: they survive the gate and cite supplied locators.
  Not measured: whether `explicitly_present` is the *right* answer for those eight elements. The
  spans resolve to Sections 5.1 and 11.2 only — Section 11.2 is an indemnity clause, and whether it
  properly evidences "right to monetary damages for landlord default" is a precision question this
  step did not ask.
- **Generalisation.** One lease, a clean `.txt` fixture with `Section N.N.` headings at line start.
- **Whether `citation_quality` is trusted anywhere else.** All three evaluators now report
  `section_and_quote` with a real `section_ref`, so the Step-456 defect did not recur here — but it
  was not audited for other consumers.
- **LP-07 span text varied** (1635 vs 1957 chars) across runs while emitting the same five prefixes.
  Not investigated.
