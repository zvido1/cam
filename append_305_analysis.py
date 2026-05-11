path = 'C:/Users/Owner/OneDrive/CAM/build_log/305_variance_test.md'
analysis = """
---

## Analysis of Failing Elements

### Pattern: unclear vs missing (LP-09, LP-22, LP-27)

Three of the five unstable elements swing between `unclear` and `missing` across runs.
These two verdicts have the same downstream effect on LP-state in most cases.

LP-state consequences:
- LP-11: LP-state STABLE at `covered_unfavorable` across all 3 runs despite element variance. The unstable element (reletting_rights_and_obligations) does not change the LP outcome.
- LP-27: LP-state STABLE at `review_needed` across all 3 runs despite element variance. Other unclear elements drive review_needed regardless of this element.
- LP-09: LP-state VARIES (review_needed vs partial). The unclear/missing swing triggers different LP-state derivation paths.
- LP-22: LP-state VARIES (missing vs review_needed). non_disturbance_obligation_for_future_lenders swings missing to explicitly_present in run 2, materially changing element count.

### Most significant variance: LP-22.non_disturbance_obligation_for_future_lenders

This element swings from `missing` (run 1) to `explicitly_present` (runs 2, 3). This is not
a borderline unclear/missing distinction -- it is a genuine missing-vs-present disagreement.
T-10 likely has language that one evaluator pass misses and two subsequent passes find. This
is the element most worth investigating -- either the T-10 text is genuinely ambiguous on this
point, or the evaluator prompt needs to be more directive about what counts as explicit
coverage of future-lender non-disturbance obligations.

### LP-11.reletting_rights_and_obligations

Three different verdicts: explicitly_present, unclear, implicitly_present. This element has
implicit_coverage_acceptable=True and default_law_covers=jurisdiction-dependent. The text
likely contains reletting language that different passes categorize differently (explicit
clause vs implicit from general remedies language). The LP-state stays stable at
covered_unfavorable regardless.

### LP-26: fully stable (7/7 elements)

All quiet-enjoyment elements produced identical verdicts across 3 runs. LP-26 is the
simplest LP architecturally (broad default-law coverage, clear textual anchors), and
the variance test confirms that structure produces stable output.

---

## Decision

STEP_305_ENABLED remains False. Per acceptance criterion, all element-level verdicts
must be stable across 3 runs. 5 elements failed.

Recommended next steps for Chat to evaluate:

1. Relax acceptance criterion to LP-state stability. LP-11 and LP-27 are LP-state-stable
   even with element variance. Under this criterion LP-09 and LP-22 still fail, but
   LP-11, LP-26, LP-27 pass. LP-22 non_disturbance element is the most material failure.

2. Investigate LP-22.non_disturbance_obligation_for_future_lenders specifically. The
   missing to explicitly_present swing in run 1 to run 2 suggests a prompt or extraction
   issue for this specific element. T-10 SNDA text should be examined directly.

3. Add tighter verdict guidance for the specific unstable elements -- especially the
   unclear/missing boundary for SNDA and lender-notice provisions.

4. Note: GPT-5.5 consistently returns empty_output for LP-11 and LP-27 across all 3 runs.
   Fallback to GPT-5.4 works, but Eval-B for these LPs effectively runs on GPT-5.4.

---

## Infrastructure findings (surfaced during test runs)

Three implementation bugs found and fixed (commit f3ce608):
1. Missing `import re` in lease_coverage_305.py (NameError in fence-strip code)
2. Dict-of-dicts response pattern not handled (GPT/Grok return verdict objects keyed by
   element_id rather than a list; fix: convert dict values to list when all are dicts)
3. safe_json_extract returns the last JSON object found, not the full array. Claude
   returns a correct bare array but it was being mangled to a single dict element.
   Fix: use json.loads() first, fall back to safe_json_extract for malformed responses.

All three fixes are in the codebase. The module is functional; the variance failure is
a genuine evaluator-variance issue on borderline provisions, not an infrastructure issue.
"""
with open(path, 'a', encoding='utf-8') as f:
    f.write(analysis)
print('Analysis appended.')
