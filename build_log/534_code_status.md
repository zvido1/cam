# Step 534 — everbridge and ncino have the SAME 5 empty LPs. divall's are different. 4 of 4 abort-causing calls are false.

**Date:** 2026-09-03 · **Instruction:** `build_log/534_chat_instruction.md`
**SURVEY ONLY. No provider calls, no clue list touched, nothing changed, not deployed.**

---

# 1. THE THREE SETS

```
everbridge  (5 empty)   LP-12  LP-20  LP-21  LP-23  LP-31      ABORTS on 3
ncino       (5 empty)   LP-12  LP-20  LP-21  LP-23  LP-31      ABORTS on 1
divall      (5 empty)   LP-16  LP-20  LP-30  LP-31  LP-32      COMPLETES
```

**everbridge and ncino are identical. divall is different — only LP-20 and LP-31 overlap.**

So the brief's either/or resolves as **both**: the two office leases share a set, the retail lease has
its own, *and* the two office leases still diverge from each other — 3 aborts against 1 — on an
identical set.

## Why each outcome, in one table

| doc | applicability of its 5 empty LPs | must_abort | seam_exempt | outcome |
|---|---|---|---|---|
| everbridge | `applicable` ×4, `unclear` ×1 | LP-20, LP-21, LP-23 | LP-12 | **ABORT** |
| ncino | `applicable` ×2, `unclear` ×3 | LP-20 | LP-12 | **ABORT** |
| divall | **`unclear` ×5** | — | — | **COMPLETES** |

**divall completes for one reason: the matcher found no clue for any of its five empty LPs, so all five
returned `unclear`, which is degradable.** Every one of them recorded `coverage_state:
not_applicable`.

**The outcome is decided entirely by whether a substring happened to appear somewhere in the
document.** Same count, same stage, same extraction quality — opposite results.

---

# 2. THE VERDICT AND THE FIRING CLUE, PER EMPTY LP

## everbridge

**LP-12 Early Termination → APPLICABLE**, clue `'right to terminate this lease'` at offset 6624:
> "...Tenant shall have **no right to terminate this Lease** or receive any adjustment or rebate of any
> Base Rent..." — **the clue matched inside its own negation**

**LP-20 Exclusivity → APPLICABLE**, clue `'exclusive use'` at 7557:
> "...including certain areas designated for the **exclusive use** of certain tenants, or to be shared
> by Landlord and certain tenants, are collectively referred to herein as the "Common Areas")..." —
> **the Common Areas definition**

**LP-21 Guaranty of Lease → APPLICABLE**, clue `'guarantor'` at 118298:
> "...shall constitute a release of Tenant or any **guarantor** of Tenant's performance hereunder from
> further performance..." — **a conditional reference inside the assignment clause**

**LP-23 Percentage Rent → APPLICABLE**, clue `'percentage rent'` at 36856:
> "...(xxx) Damages paid to Tenant...; **(xxxi) Fixed or percentage rent under any ground or underlying
> lease or leases;** (xxxii) The wages and benefits of any employee..." — **item xxxi of an exclusions
> enumeration**

**LP-31 Co-Tenancy → UNCLEAR**, no clue fired. Correct.

## ncino

**LP-12 → APPLICABLE**, clue `'right to terminate this lease'` at 88660:
> "...then Tenant shall **not have a right to terminate this Lease**, and Landlord shall carry out and
> complete its restoration..." — **negation again, in a casualty clause**

**LP-20 → APPLICABLE**, clue `'exclusive use'` at 994:
> "...together with a **non-exclusive right** to the use of and access to areas of the Building **not
> regularly and customarily leased for the exclusive use of tenants**, including... driveways,
> sidewalks, entranceways, public lobbies..." — **doubly negated: inside `non-exclusive`, and inside a
> clause about what is NOT leased exclusively**

**LP-21, LP-23, LP-31 → UNCLEAR**, no clue fired. All three correct.

**This is the whole difference between everbridge and ncino.** Same five empty LPs; everbridge happens
to contain a `guarantor` and a `percentage rent` string that ncino does not, so everbridge aborts on
three and ncino on one.

---

# 3. GROUND TRUTH BY READING

Searched substantively, not by clue — for the provisions themselves:

| provision | probe | everbridge | ncino |
|---|---|---|---|
| exclusivity covenant | `exclusive right to operate/sell`, `shall not lease to competitor`, `exclusivity covenant` | **NONE** — the only hit is `non-exclusive right` | **NONE** |
| guaranty of lease | `Guarantor hereby guarantees`, `Guaranty of Lease`, `executed a guaranty` | **NONE** | **NONE** |
| percentage rent | `Percentage Rent shall/means`, `Gross Sales`, `breakpoint` | **NONE** | 1 hit — *"management fees (which shall not exceed **four percent (4%)** of the gross revenues)"*, an **operating-expense cap**, not percentage rent |
| early termination option | `Termination Option`, `option to terminate effective`, `Termination Fee` | **NONE** | **NONE** |

**Neither document contains an exclusivity covenant, a guaranty of lease, a percentage-rent regime, or
an early-termination option.** Both are office leases; three of those four are retail provisions.

---

# 4. THE BASELINE

**Abort-causing applicability calls: 4. Correct: 0. False: 4.**

```
everbridge  LP-20  applicable   FALSE     (no exclusivity covenant)
everbridge  LP-21  applicable   FALSE     (no guaranty)
everbridge  LP-23  applicable   FALSE     (no percentage rent)
ncino       LP-20  applicable   FALSE     (no exclusivity covenant)
```

**100% of the calls that stopped these two runs are wrong.**

**And the non-aborting calls in the same sets are right.** Every `unclear` verdict — everbridge LP-31,
ncino LP-21/LP-23/LP-31, and all five of divall's — is correct: those provisions genuinely are absent.
**The matcher is not uniformly broken. It is right whenever it finds nothing and wrong whenever it
finds something**, on this evidence.

**LP-12 is false on both documents too** (no termination option in either) but is seam-exempt, so it
did not contribute to an abort. **That makes 6 false applicability calls of 10 non-`unclear` verdicts
across the two documents, with 4 of them load-bearing.**

---

# 5. THE MATCHING STYLE — AND A PREMISE CORRECTED AGAIN

**LP-16 has no `"exclusive"` clue.** Its list is `['parking spaces', 'parking rights', 'garage',
'surface parking', 'unreserved parking', 'reserved parking']`. The `"exclusive"`-on-a-remedies-clause
instance is **Step 480**, concerns **LP-20**, and was **my own diagnostic probe**, not the matcher —
recorded in Step 531 §2 and again here because the brief has now carried it twice.

**LP-12 is the same style and the same defect**, confirmed above on both documents.

## Structural screen: where else could this fire?

For every conditional/optional LP, every clue occurrence across all 9 real leases, classified by the
90 characters preceding it:

```
LP      name                             hits    NEG   COND   ENUM  risky%
LP-20   Exclusivity                        23     14      1      0     65%
LP-21   Guaranty of Lease                  46      2      9      0     24%
LP-30   Estoppel Certificate               75      0      3     12     20%
LP-32   Hazardous Materials               574      4     74     14     16%
LP-12   Early Termination                  47      4      3      0     15%
LP-16   Parking                            92      4      1      5     11%
LP-22   SNDA                              329      0     22     10     10%
LP-23   Percentage Rent                    35      0      1      0      3%
LP-15   Signage Rights                   1087      5     12      2      2%
LP-04   Security Deposit                  779      4      8      0      2%
LP-07   Common Area Maintenance           426      0      5      2      2%
LP-31   Co-Tenancy                          0      0      0      0      0%
```

**LP-20 is the outlier by a wide margin: 65% of its 23 corpus-wide hits sit in a negation, conditional
or enumeration, and 14 of 23 are literal negations.** It is also the LP that blocks three of the five
real leases attempted. **Those two facts are the same fact.**

**LP-21 (24%), LP-30 (20%), LP-32 (16%) and LP-12 (15%) are the next tier** and have not been
ground-truthed — LP-30 and LP-32 have never caused an abort, but nothing here says they could not.

**This table is a SCREEN, not ground truth.** The negation/conditional/enumeration regexes over-count:
a hit preceded by "any" is flagged conditional and may be perfectly legitimate. Step 495's lesson —
that an automated proxy misclassified three of thirty-two in both directions — applies to this table
too. **The four LP-20/21/23 verdicts in §3 are read; these percentages only say where to look next.**

---

# WHAT IS NOT ESTABLISHED

- **The empty-LP sets for everbridge and ncino are read from the GATE's own applicability log, not from
  stored provisions.** Step 529's harness persisted counts, not provisions (Step 532). The five LPs the
  gate names match the five-empty count exactly, but I could not independently enumerate them from the
  extraction output.
- **Only the 4 abort-causing calls plus LP-12 were ground-truthed by reading.** The other seven
  conditional LPs' verdicts on these documents were not read.
- **The §5 screen has not been validated.** No hit it flagged was read except LP-20's, and no hit it
  cleared was checked for a false negative.
- **quanterix, bokf, albireo and atreca_industrial have still never been through the gate**, so their
  empty-LP sets are unknown and this survey says nothing about them.
- **divall's completion is from the Step-496 run** under an older clue configuration; LP-16's list was
  narrowed at Step 496 and LP-12's widened at Step 481, so a divall re-run today could differ.
- **No clue list was touched and no fix was proposed**, per the brief.
