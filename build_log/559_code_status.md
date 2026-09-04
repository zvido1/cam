# Step 559A — albireo ABORTS. Third document, same matcher, and one of the two blocking hits is the lease saying "Guarantor: None".

**Date:** 2026-09-04 · **Instruction:** `build_log/559_chat_instruction.md`
**STOPPED after the abort, per the brief. Documents 2–4 not run. No code changed, nothing tuned.**
**Run: `build_log/runs/559A_albireo_10postoffice_lease.txt-modec_20260904_131859`**

---

# 1. IT ABORTS, AND IT IS THE APPLICABILITY MATCHER — 3 OF 3

```
[lease_adapter:analyze] completeness gate applicability:
  {'LP-12': 'applicable', 'LP-16': 'unclear', 'LP-20': 'applicable',
   'LP-21': 'applicable', 'LP-23': 'unclear', 'LP-31': 'unclear'}
  must_abort=['LP-20', 'LP-21']  degradable=['LP-16','LP-23','LP-31']  seam_exempt=['LP-12']
```

**Six LPs came back with empty text. Four were handled correctly** — LP-12 exempted because the 423
seam supplied its evidence, LP-16/LP-23/LP-31 classified `unclear` and therefore degradable.
**LP-20 and LP-21 were classified `applicable`, and both are false.**

**Extraction is not the problem.** It succeeded on all four attempts: `gemini-3.1-pro-preview succeeded
in 234.9s / 236.5s / 243.3s / 240.2s (primary)`. Four identical aborts, no variance.

## LP-20 Exclusivity — one clue fired, inside its own negation

Of eight activation clues, exactly one matched, at offset 6977:

> *"…located outside the Premises on the Property that are provided and designated by Landlord for the
> general **non-exclusive use** and convenience of Tenant and other tenants."*

**`exclusive use` inside `non-exclusive use`.** This is the identical failure Step 534 recorded on
ncino and Step 537 recorded on butler_crossing. **Third document, same substring, same clue.**

## LP-21 Guaranty of Lease — and this one is worse than a negation

Two clues matched. The one that decides it, at offset 6055, in the lease's own cover-page term sheet:

> *"Security Deposit: $87,398.00 (Subject to Section 26.2) **Guarantor: None** Broker(s): Jones Lang
> LaSalle…"*

**The document states in terms that there is no guarantor, and the matcher reads it as evidence that
there is one.**

The other occurrences are conditional boilerplate that presupposes a guarantor who does not exist:

> *"…any **guarantor** of this Lease refuses to approve the proposed Transfer…"*
> *"…the obligations of a principal (and **not** as the obligations of a **guarantor** or surety)."*
> *"…the filing by Tenant or Tenant's **guarantor (if any)** of a petition in bankruptcy…"*

## Is it a pattern? Yes — and the LP-20 mechanism is now 3 of 3

| document | LP-20 clue | the text it matched |
|---|---|---|
| **everbridge** | `exclusive use` | *"certain areas designated for the exclusive use of certain tenants… ("Common Areas")"* |
| **ncino** | `exclusive use` | *"a **non-exclusive** right… areas **not** regularly and customarily leased for the exclusive use of tenants"* |
| **albireo** | `exclusive use` | *"designated by Landlord for the general **non-exclusive use** and convenience of Tenant"* |

**Every document that has aborted has aborted with LP-20 on `exclusive use`, matched inside a Common
Areas definition.** All three are office/lab leases where the phrase appears because common areas are
shared, i.e. *not* exclusive. **The clue is firing on the exact opposite of the concept it is meant to
detect, and it has now done so on every real office lease we have tried.**

## Would Step 535's designed rule have saved this run? Measured, not assumed.

I implemented the documented rule from `535_code_status.md:20-27` — negating token in the span
preceding the hit within its sentence; tokens `no | not | non- | never | other than | exclud*`;
per-occurrence — as a throwaway script and ran it against albireo. **Nothing in the repo changed.**

```
LP-20  1 occurrence   SUPPRESSED (neg='non-')          => LP would be SUPPRESSED
LP-21 12 occurrences  6 suppressed, 6 STILL FIRE       => LP STILL ACTIVATES
```

**LP-20 would be fixed. LP-21 would not, so albireo would still abort** — the same verdict Step 535
reached for everbridge, which is why it was not built.

**And the surviving family is structurally out of reach of that rule:**

```
[STILL FIRES] 'guarantor' @6055     "Guarantor: None"
[STILL FIRES] 'guarantor' @114234   "Tenant or Tenant's guarantor (if any) in writing of its inability..."
[STILL FIRES] 'guarantor' @114351   "the filing by Tenant or Tenant's guarantor (if any) of a petition..."
[STILL FIRES] 'guarantor' @114598   "...guarantor (if any) of an answer admitting or failing timely to contest..."
```

**`X: None` and `X (if any)` are post-positional absence markers — the negation comes AFTER the token.**
A rule that reads the preceding span cannot see them by construction. **This is a third failure shape,
distinct from both the negation case Step 535 solved and the subject/conditional cases it named as
survivors.** Reporting it; not proposing a rule for it.

---

# 2–8. THE REST OF THE BRIEF IS UNANSWERABLE, AND I AM SAYING SO RATHER THAN SKIPPING IT

The abort happens at the extraction-completeness gate, **before the panel runs**. There is no
`coverage_assessment` on disk — only `index.json` and `run_01_gate_aborts.json`.

- **2. Headlines contradicting the document — NOT MEASURED.** No coverage entries exist, so no
  exposure prose was generated. *The class this arc has been closing cannot be observed on a run that
  never reached the panel.*
- **3. The four seamed LPs — PARTIAL, and it is the one positive result.** `LP-12` is recorded as
  `seam_exempt`: *"1 LP(s) exempt — evidence sourced from verified spans, not the extraction bucket:
  ['LP-12']"*. **The 423 seam produced verified spans for LP-12 where extraction returned nothing.**
  LP-07, LP-17 and LP-27 are not in the empty list at all, so extraction covered them; whether their
  seams fired is unrecorded, because the run died before the coverage stage wrote anything.
- **4. Summary top line — NOT PRODUCED.** No summary stage ran.
- **5. `assessment_status` / `broken_xref` — NOT PRODUCED.** No assessments were built.
- **6. Locator resolution rate and heading count — NOT MEASURABLE.** Both are computed from element
  citations, which require the panel.
- **7. Calls and elapsed — 1,703 s wall, 4 attempts.** `api_calls_total` is `None`: the result object
  is never constructed on an abort, so the call count is not recorded. **Four extractions at ~239 s
  each is ~956 s of the 1,703 s, all of it spent re-running an extraction that succeeded every time to
  clear a gate that fails for a reason extraction cannot affect.**
- **8. Read it as a lawyer would — THERE IS NOTHING TO READ.** The user gets an abort. Since Step 533
  that abort carries a specific reason code rather than "not a lease", which is the correct behaviour
  and is also the whole of the deliverable.

---

# THE FINDING, STATED PLAINLY

**Four of nine real leases have now been attempted past extraction and three of them abort on the same
clue.** everbridge, ncino and albireo all fail LP-20 on `exclusive use` matched inside a Common Areas
definition. **That is no longer two documents; it is the matcher's behaviour on office leases.**

**And LP-21 adds a shape nobody has named: a lease that declares an absence in its own term sheet —
`Guarantor: None` — activates the LP for the provision it just said it does not have.**

**I stopped here.** bokf, atreca_industrial and atreca_eastjamie are not run.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was fixed or tuned**, per the brief. The negation measurement in §1 is a throwaway script
  in the scratchpad; the repo is unchanged.
- **The remaining three documents are unrun**, so whether the pattern extends to them is unknown. bokf
  and both atrecas are office/lab leases of the same kind, which is a reason to expect it and not
  evidence of it.
- **Whether albireo genuinely lacks an exclusivity covenant and a guaranty was checked only through the
  activation clues.** Every `exclusive`/`guaranty`/`guarantor` occurrence in the document was listed
  and read, and none is a grant of exclusivity or a guaranty; **but I did not read the whole 179 KB
  lease**, and a covenant phrased without any of those words would not have appeared.
- **`api_calls_total` is unrecorded on aborts.** The 1,703 s wall time and four extractions at ~239 s
  are from the log; the provider-call count for this run does not exist anywhere.
- **The brief's ordering is self-contradictory and I chose one reading.** *"Run them in that order,
  smallest first"* — the enumerated order ends with the smallest file (atreca_eastjamie, 160,244 bytes,
  against albireo's 179,764). I followed the enumeration. If true ascending order was meant, the first
  document should have been atreca_eastjamie.
- **The panel was verified against the DEPLOYED provider-health endpoint**, not the local environment
  the harness runs in. All seven models listed, callable, no fallback; `status: unhealthy` is SDK drift
  on three Google packages. The harness ran its own model-check preflight, which I did not capture
  separately.
