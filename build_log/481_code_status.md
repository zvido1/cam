# Step 481 — Part A: LP-12's clue list widened. Part B: analysis only.

**Date:** 2026-08-24 · **Instruction:** `build_log/481_chat_instruction.md`
**Part A implemented and verified offline. Part B is analysis only, nothing implemented.**
No pipeline runs. Not deployed. Tests **357 passed**.

---

# PART A

## The survey, before choosing

Every sentence in either fixture that *grants or effects* a termination, `[M]`:

**Atlas**
> *"…if such failure continues for an additional thirty (30) days, **Tenant may terminate this Lease**
> upon written notice to Landlord."*
> *"…either party **may terminate this Lease** upon sixty (60) days' written notice."*
> *"If restoration is not completed within two hundred forty (240) days and neither party has exercised
> **a termination right**, Tenant **shall have the right to terminate this Lease** upon thirty (30)
> days' written notice…"*
> *"…this Lease **shall terminate** as of the date of such taking."*
> *"…or if neither party **elects to terminate**, this Lease shall continue…"*

**divall**
> *"…Landlord and Tenant may mutually **agree to terminate this Lease**…"*
> *"…Tenant will have **the right to terminate the Lease** as of the date of such Total Destruction…"*
> *"If Tenant so **elects to terminate the Lease**, neither party will be obligated to repair…"*
> *"…this Lease **shall terminate and expire** as of the date of taking."*

## The baseline, which reframes the problem

Current LP-12 across all 32 fixtures `[M]`: **19 applicable, 12 not_applicable, 1 excluded.**

The 19 applicable are almost entirely the synthetic `T-xx` family, firing on `early termination right`
and `termination fee` — because those fixtures literally contain a section headed *"Tenant's Early
Termination Right."*

**Every real-world executed lease returned `not_applicable`** — Atlas, divall, albireo, both Atrecas,
bokf, everbridge, ncino, quanterix. Only solidpower fired. **Real-world: 1 of 10.**

*[R]* The clue list is not merely narrow; it is tuned to documents written in the vocabulary the list
was drawn from. It succeeds on synthetics and fails on executed leases — the exact inverse of what a
detector should do.

## Candidate distributions — the over-trigger test

`[M]`, fire rate across 32 fixtures:

| candidate | fixtures | Atlas | divall |
|---|---|---|---|
| `terminate this lease` | **32/32** | ✅ | ✅ |
| `may terminate` | 30/32 | ✅ | — |
| `right to terminate` | 28/32 | ✅ | ✅ |
| `tenant shall have the right to terminate` | 22/32 | ✅ | — |
| `termination right` | 21/32 | ✅ | — |
| `elects to terminate` | **8/32** | ✅ | ✅ |
| `terminate the lease` | 4/32 | — | ✅ |

`terminate this lease` is **unusable**: it fires on every fixture, and its contexts include landlord
remedies — *"(a) **terminate this lease** by written notice to tenant"* — which belong to LP-11, not
LP-12.

Option distributions `[M]`:

| option | applicable | not_applicable | Atlas | divall | real leases |
|---|---|---|---|---|---|
| baseline | 19 | 12 | NOT | NOT | 1/10 |
| **A** `+right to terminate the/this lease` | 27 | 4 | APP | APP | 9/10 |
| **B** = A `+elects/elect to terminate` | **28** | **3** | **APP** | **APP** | **10/10** |
| C = B `+may terminate this lease` | 31 | **0** | APP | APP | 10/10 |
| D | bare `terminate this lease` | 31 | **0** | APP | APP | 10/10 |

**C and D fire on 31 of 32 and leave zero negatives — those are not fixes**, exactly as the brief
warned. **Option B chosen.**

## Chosen change — 4 clues added, 0 removed

```json
"activation_clues": [
    "early termination right", "early termination option", "right to terminate early",
    "break option", "break clause", "kick-out clause", "co-tenancy termination",
    "go dark", "termination option", "termination fee",
    "right to terminate this lease",   ← added
    "right to terminate the lease",    ← added
    "elects to terminate",             ← added
    "elect to terminate"               ← added
]
```

Exclusion clues untouched (3).

## Post-change verification `[M]`

```
distribution: {'applicable': 28, 'not_applicable': 3, 'excluded': 1}
ATLAS  -> applicable        DIVALL -> applicable
real-world leases applicable: 10/10  (was 1/10)
```

**Both target fixtures flip. The distribution does not collapse — 3 negatives and 1 exclusion survive.**

**Are the flips correct?** Spot-checked three, all genuine tenant exits `[M]`:

- **albireo** — *"Tenant may **elect to terminate this Lease** by giving Landlord written notice…
  within sixty (60) days after the Event of Casualty."*
- **bokf** — *"…if such interruption continues for a total of sixty (60) days… Tenant shall have the
  **right to terminate this Lease** effective as of the date ten (10) days following written notice…"*
- **quanterix** — *"…cannot be made tenantable within two hundred seventy (270) days… then either
  party shall have the **right to terminate this Lease**…"*

**Are the remaining 3 negatives correct? Yes** `[M]`. `T-10-NY`, `T-12_missing_clauses`,
`T-12_omissions` each contain exactly one termination sentence:

> *"**landlord may terminate** such holdover tenancy at any time upon thirty (30) days' written notice
> to tenant."*

A landlord right over a holdover tenancy, not a tenant early-termination right. `not_applicable` is
correct for all three. `T-15_lp00_tester` remains `excluded` on an exclusion clue.

*[R]* So the change flips exactly the population that was wrong and leaves the population that was
right. **No pipeline run was made — this is `is_applicable()` evaluated offline. Whether the LP-12
coverage entry now reads correctly end-to-end is unverified.**

---

# PART B — analysis only, nothing implemented

## Who reads `requires_attention` `[M]`

| site | use |
|---|---|
| `lease_coverage.py:1006` | the definition — membership test over `coverage_state` |
| `lease_coverage.py:1050`, `:1063` | summary logging |
| `lease_coverage.py:1132` | CLI marker — `⚠` / `✓` / `—` |
| `lease_exposure.py:519-524` | **overrides it to `True`** for high-materiality LPs in non-covered states |
| `lease_adapter.py:2088` | **the summary counter** `summary.requires_attention` |
| `_step371_variance.py` | a variance harness |

**Nothing in `05 Lease Analyzer/` reads it** — not `app.js`, not `job_manager.py`, not `main.py`. The
frontend consumes coverage entries directly. So the blast radius is the summary counter, the CLI
marker, and the exposure override.

Note `lease_exposure.py` already sets `requires_attention = True` after the fact, with the comment
*"_build_assessment sets requires_attention before materiality is known; fix it here"* — **there is
already precedent for the flag being corrected downstream**, so it is not treated as immutable.

## Would flipping `not_applicable` and unclear-routed entries to `True` flood the report? `[M]`

| run | entries | current attention | not_applicable (unclear-routed) | would become |
|---|---|---|---|---|
| Atlas `s478_atlas_r2` | 32 | 27 | 3 (2) | **30 / 32** |
| divall `s478_divall` | 32 | 26 | 5 (4) | **31 / 32** |

**Yes — it floods.** 30 and 31 of 32 entries flagged. *[R]* At 97% the flag stops carrying information:
a reader cannot triage a report where everything needs attention, and the summary counter
`requires_attention` becomes a restatement of `issue_areas_assessed`. That is the Step-461 defect in
reverse — a counter that moves without the underlying answer improving.

## Recommendation `[R]` — do NOT overload the boolean

`requires_attention` answers *"should a reviewer look at this?"* The missing question is *"did the
system actually assess this?"* Those are different, and conflating them destroys the first without
answering the second.

**Proposed: a separate field, not a third value.**

```
assessment_status:  "assessed"      -- evaluators ran, verdicts exist
                    "not_assessed"  -- short-circuited before Stage 5
                                       (applicability not_applicable / unclear, or evidence_missing)
```

Rationale:
- **Additive.** Every existing consumer keeps working; no counter moves; no CLI marker changes.
- **Orthogonal.** `requires_attention` stays a triage signal; `assessment_status` is a provenance
  signal. A reader can ask for "not assessed" without the triage list collapsing.
- **Already half-built.** Steps 476/477 added `evidence_missing` for extraction-completeness failures.
  `assessment_status` generalises it to the applicability short-circuits, which is the larger
  population — 3 to 5 entries per run versus 1 to 4.
- **A third boolean value would break the membership test's type** and every truthiness check on it,
  including the exposure override at `lease_exposure.py:523`.

**Not implemented, per instruction.** One thing a implementer should check that this analysis did not:
whether the report generator and the DOCX/PDF annotators — which Step 477 found read no degraded
markers at all — would surface a new field, or silently ignore it as they do the others.

## What is NOT established

- Whether LP-12's coverage entry now reads correctly end to end. `is_applicable()` only; no run.
- Whether the 4 new clues over-trigger on documents outside these 32 fixtures.
- Whether `applicable` is the right answer for the 9 flipped leases at the *element* level — the
  entry will now be assessed by evaluators, and nothing here measures those verdicts.
- Part B's flood estimate rests on two runs.
