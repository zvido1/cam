# 375E-COV-A1 Consequence-Independence Diagnostic Results

**Status: PENDING — Tzvi must run `python build_log/_375ecova1_diagnostic.py`**

This file is overwritten by the harness upon completion.

---

## What this diagnostic tests

Distribution from COV-A keyed run (19f9a7): **24 harmful / 1 neutral / 0 beneficial**
across 25 directional findings.

Concern: COV-A finding-scoped 5e prompt hands 5e adversarially-framed findings
(tenant_unprotected / exposure-flavored titles / direction FIXED) and asks "how consequential
is this adverse finding" — so 5e ratifies the framing instead of independently assessing
consequence. If true, COV-A converts every verified adverse finding into harmful/material,
defeating Stage-7-owns-sign / 5e-owns-consequence.

## Panel

| Finding | LP | LP Name | COV-A result | Why in panel |
|---------|-----|---------|-------------|-------------|
| Dir-05 | LP-05 | Permitted Use | harmful/medium | Regenerated case (was beneficial in frozen 52adbf) |
| Dir-12 | LP-15 | Signage Rights | neutral/low | LONE NEUTRAL -- calibrates bias strength |
| Dir-15 | LP-20 | Exclusivity | harmful/not_applicable | Known wobbler (assert_weak 2-1 in frozen) |
| Dir-10 | LP-11 | Default & Remedies | harmful/high | Thin-gap (15/17 elements present) -- tests framing effect |

## Prompt variants

- **A (current COV-A):** as shipped -- hands Stage 7 direction (tenant_unprotected/adverse/FIXED) to 5e
- **B (direction-redacted):** clause facts + use profile only; no adverse framing, no direction label
- **C (explicit-independence):** finding included but explicit instruction: do not infer harmfulness
  from direction label; assess consequence from clause facts independently

## Read criteria

| Signal | Read |
|--------|------|
| B/C yield neutral/beneficial where A is harmful (>=2 findings) | CONTAMINATION CONFIRMED -- fix prompt before push |
| All variants agree (all harmful) | GENUINE -- distribution is the lease, not the prompt; push defensible |
| Chaotic across variants (A/B/C all differ per finding) | UNSTABLE -- larger panel needed |

## Output files (written by harness)

- `build_log/375E-COV-A1_results.md` (this file -- overwritten)
- `build_log/375E-COV-A1_raw_results.json` (raw evaluator outputs)

---

*Harness: `build_log/_375ecova1_diagnostic.py`*
*Run: `python build_log/_375ecova1_diagnostic.py` from repo root*
*~36 model calls (4 findings x 3 variants x 3 evaluators); no Railway deploy needed*
