## Claude Code — Step 424: commit corrections, then measure segmentation recall

**Part 0 is mandatory and comes first.** Per CLAUDE.md Rule 7 (added today): write this brief, verbatim, to `build_log/424_chat_instruction.md` before doing anything else. Do not paraphrase, summarize, or improve it. It is the document you will be audited against.

---

### Part 1 — Commit the corrections (no new work)

Four files were corrected by Chat on 2026-07-14 and are unstaged:

- `build_log/422_code_status.md` — fabricated cap removed from the LP-07 variance section, correction block added
- `build_log/421C_evidence_assignment_incident.md` — two instances removed (§2a, §3a); new §9 recording the reporting-layer incident
- `Docs/Patent_Supplement_2026_07_14.md` — §11 canonical examples: cap removed, fabrication incident added in its place
- `CLAUDE.md` — reporting-integrity Rules 6 and 7 added

Stage explicitly (`build_log/` and `Docs/` are gitignored — use `git add -f`). Commit as:

`424 correct fabricated Controllable Expenses Cap; add reporting integrity rules 6-7`

Do not push.

---

### Part 2 — Segmentation recall measurement

**This is a measurement, not a fix. Do not change the elicitation prompt, the schema, or the resolver in this step, whatever the results show.** Measure first. That discipline has surfaced every real finding in this project, and violating it now would be the third failure of the day.

**Hypothesis (stated before the data, per protocol):**

> Element-guided elicitation produces a materially more complete span universe than the LP-blind approach, but recall is not 100% and varies across runs on the same input.

**Method**

- **N = 5 runs**, same canonical source (Atreca), same prompt, same config. Record the prompt hash and config hash on every run; assert they are identical across runs (this is a config-integrity assertion, same class as Step 416 — if they drift, the measurement is void).
- **All 32 LPs** — not the 2-LP subset from the 423C smoke test.
- **Predefined target set.** Declare it in the instruction file *before* running:

| Target | Source location | Rationale |
|---|---|---|
| `Tenant's Share of Operating Expenses of Building: 100%` | page-1 key-terms block | LP-07 parameter |
| `Building's Share of Project: 45.79%` | page-1 key-terms block | LP-07 parameter |
| `Rent Adjustment Percentage: 3%` | page-1 key-terms block | LP-02 parameter |
| `Base Rent: $3.75 per rentable square foot` | page-1 key-terms block | LP-02 parameter |
| Operating Expense exclusions list, items (a)–(u) | Section 5 | LP-07 protection |
| Annual Statement / reconciliation | Section 5 | LP-07 protection |
| Independent Review (audit rights) | Section 5 | LP-07 protection |
| 95% occupancy gross-up | Section 5 | LP-07 protection |
| Condition Precedent (prior tenant vacates) | Section 2 | LP-12 protection — the boundary-drift victim |
| Landlord's Work access rights | Section 2 | LP-12 — the other boundary-drift victim |
| 120-day delivery termination right | Section 2 | LP-12 protection |
| Service-interruption rent abatement | Section 11 | LP-11 protection |

**Every target above has been verified present in the source by direct read.** There is no Controllable Expenses Cap in the target set, because there is no Controllable Expenses Cap in the lease.

**A target counts as HIT only if a span whose offsets contain the target text resolved as `verified`.** Not "the model mentioned it." Not "a nearby span exists." Offsets, or it didn't happen.

**Report**

`build_log/424_segmentation_recall_measurement.md`:

- Per-run: total spans, verified / ambiguous / unverified counts, dedup ratio
- **Per-target hit rate across the 5 runs** (0/5 through 5/5) — this is the headline
- **Span-count variance** across runs — is the universe stable?
- **Offset stability** — does the same target resolve to the same offsets each run, or do boundaries drift?
- Any target at <5/5 gets named explicitly as a recall gap
- Any `unverified` span gets its failure reason recorded (the 423C run showed a page-number artifact breaking a long quote — expect more of these)

**State plainly what this measures and what it does not.** It measures whether element-guided elicitation reliably surfaces known-present material on *one document*. It does not measure recall on unseen documents, and it does not validate the architecture.

**Constraints:** no prompt changes, no resolver changes, no pipeline wiring, no `cam/core/`, no baseline claims. Explicit path staging, `git add -f`, no push.

---

That's the step. The measurement will tell us whether the parameter block can be built on this substrate or whether elicitation needs work first — and either answer is useful.
