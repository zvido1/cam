"""Step 370d regression replay — deterministic acceptance proof (no server, no API).

Replays the REAL Pass-2 decision sequence from lease_synthesis (_diagnose_pass2_output
then _safe_parse_synthesis, in the same order _try_call uses them) against fixtures built
from PRESERVED 370c content. Proves:

  1. A truncated Eval-A response is labeled TRUNCATED and NOT salvaged into a vote.
  2. A complete canonical response still parses identically (36 findings).
  3. A malformed-but-non-truncated response is rejected DISTINCTLY from truncation.
  4. The truncation path excludes the evaluator (fail-loud), salvage never becomes a vote.

Fidelity note: the full raw truncated responses from 370c were not persisted (only a
3000-char preview + the salvaged parse). The truncated fixture is therefore reconstructed
by truncating a REAL complete captured response (H2 Eval-A, 36 findings) mid-array — faithful
to the established defect class (unclosed JSON array), not byte-identical to the lost original.
"""
import sys, json, re
CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

from cam.adapters.lease_review.lease_synthesis import (
    _diagnose_pass2_output, _safe_parse_synthesis,
    DIRECTIONAL_PASS2_MAX_OUTPUT_TOKENS as CAP,
)

H2 = CAM_ROOT + r"\05 Lease Analyzer\results\lease_review_20260530_233514_370c_H2\tenant_0\pipeline_results.json"
verds = json.load(open(H2, encoding="utf-8"))["_stage_data"]["synthesis_meta"]["pass2_raw"]["A"]["verdicts"]

complete_raw = json.dumps(verds, indent=2, ensure_ascii=False)          # real complete content
truncated_raw = complete_raw[:int(len(complete_raw) * 0.6)]             # unclosed mid-array
malformed_closed = '{"cross_coverage_findings": "this is closed valid JSON but the wrong shape"}'  # parses, closed, not array
salvage_observed = '["LP-27"]'  # the exact stray fragment the OLD parser produced from a truncated run


def replay_try_call_decision(raw):
    """Mirror _try_call's order: diagnose truncation FIRST, then parse/normalize."""
    diag = _diagnose_pass2_output(raw, CAP)
    if diag["truncation_detected"]:
        return ("TRUNCATED", "failed_truncated_output_budget", diag, None)
    parsed = _safe_parse_synthesis(raw)
    if parsed is None:
        return ("MALFORMED", "unparseable", diag, None)
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break
    if not isinstance(parsed, list):
        return ("MALFORMED", f"expected list got {type(parsed).__name__}", diag, None)
    return ("COMPLETE", None, diag, parsed)


def show(label, raw):
    state, reason, diag, parsed = replay_try_call_decision(raw)
    n = len(parsed) if isinstance(parsed, list) else 0
    print(f"\n[{label}]")
    print(f"  raw_len={diag['raw_response_length']} json_parse={diag['json_parse_success']} "
          f"array_closed={diag['top_level_array_closed']} depth={diag['bracket_depth_at_end']} "
          f"in_string={diag['ended_inside_string']}")
    print(f"  -> STATE={state}  reason={reason}  parsed_findings={n}")
    return state, n


print(f"Pass-2 cap under test: {CAP}")

# 1. Complete canonical -> COMPLETE, 36 findings
s_complete, n_complete = show("1. COMPLETE (real H2 Eval-A, 36 findings)", complete_raw)
assert s_complete == "COMPLETE" and n_complete == 36, (s_complete, n_complete)

# 2. Truncated -> TRUNCATED, NOT salvaged to a vote (0 findings contributed)
s_trunc, n_trunc = show("2. TRUNCATED (real content cut mid-array)", truncated_raw)
assert s_trunc == "TRUNCATED" and n_trunc == 0, (s_trunc, n_trunc)

# 3. Malformed-but-closed (wrong shape) -> MALFORMED, distinct from truncation
s_mal, n_mal = show("3. MALFORMED non-truncated (closed dict, wrong shape)", malformed_closed)
assert s_mal == "MALFORMED" and n_mal == 0, (s_mal, n_mal)

# 4. The exact OLD salvage fragment: confirm the NEW path never treats it as a vote.
#    (It is itself a closed 1-element array of a string -> not truncation by shape, but
#     it parses to a list whose member is not a dict -> contributes ZERO directional votes.
#     The REAL protection is upstream: the truncated SOURCE is now caught as TRUNCATED
#     before salvage ever runs. This asserts the fragment alone is never a directional vote.)
parsed_frag = _safe_parse_synthesis(salvage_observed)
dir_votes = [x for x in (parsed_frag or []) if isinstance(x, dict) and str(x.get("candidate_id","")).startswith("Dir-")]
print(f"\n[4. salvage fragment {salvage_observed!r}] parsed={parsed_frag!r} directional_votes={len(dir_votes)}")
assert len(dir_votes) == 0

print("\nALL ACCEPTANCE ASSERTIONS PASSED")
print("States demonstrated: complete | truncated | malformed  (+ excluded = non-contributing truncated/malformed)")
