# Step 386b — Re-land of Step 386 Pass-1 Instrumentation (post-rebase recovery)

**Date:** 2026-06-14
**Author:** Claude Code
**Type:** Port / recovery. No behavior changes, no prompt changes, no model routing changes.

---

## Root cause

Step 386 (Pass-1 artifact instrumentation) was implemented and tested locally on 2026-06-11
but was marked "NOT pushed (pending review)" in its status file. During the 2026-06-14
OneDrive `-Dad` conflict recovery and rebase of local main onto origin/main (113 commits
ahead), the Step 386 code was lost:

- In the rebase conflict on `lease_synthesis.py` at commit 8/8 (`51d20ef`), the conflict
  resolver mistakenly kept the remote's pre-386 stub (lines with comment "those stay empty
  until 370c adds them") instead of the -Dad version with the real instrumentation.
- The `-Dad` backup at `build_log/onedrive_dad_backup_2026_06_14/cam/adapters/lease_review/
  lease_synthesis-Dad.py` was the only surviving copy.

This step re-lands the instrumentation as a port against the current tree.

---

## What changed

**Single file:** `cam/adapters/lease_review/lease_synthesis.py`

Replaced the stub block at the end of `run_synthesis()` (former lines 2591–2596):
```python
# ... stay empty until 370c adds them.
directional_guard["execution_path"] = "unknown"
directional_guard["raw_response_paths"] = []
directional_guard["request_hashes"] = []
```

With the full Step 386 artifact block (~85 lines, try/except guarded) plus real assignments:
```python
directional_guard["raw_response_paths"] = _p1_artifact_paths
directional_guard["request_hashes"] = {"pass1_prompt_md5": _p1_hash}
```

---

## Artifacts written per run (when `cfg["_p1_artifact_dir"]` is set)

| File | Contents |
|------|----------|
| `stage7_pass1_raw_input.json` | `flagged_lp_count`, `flagged_lp_ids`, `prompt_hash_md5`, `prompt_len` |
| `stage7_pass1_raw_output.txt` | Per-evaluator model/completed header + raw response text |
| `stage7_pass1_parsed_candidates.json` | Full `directional_candidates` list |
| `stage7_pass1_dropped_attention_items.json` | Flagged LPs not present in any candidate; `finish_reasons` per evaluator |

---

## Complete port — raw_response capture also re-landed

Pre-commit assessment confirmed the `_call_single_evaluator()` change is purely additive:
- `_try_call()` return type changed `dict` → `tuple` (`raw, parsed`); call mechanic unchanged
- 2 unpack sites updated (`raw_text, result = _try_call(...)`)
- 4 return dicts gain `"raw_response": raw_text/None` and `"finish_reason": None`
- Zero downstream readers of `raw_response` outside the 386 artifact block
- No retry, truncation, streaming, or schema changes

All 4 artifacts are fully populated on success paths. `finish_reason` remains `None`
(not exposed by `cam/core` adapter — unchanged from original Step 386 intent).

---

## Anchor map (current tree variable locations)

| Variable | Line in current tree | Note |
|----------|---------------------|------|
| `_p1_hash` | 2258 | Already existed; reused, not redefined |
| `flagged_lps` | 2232 | Available throughout `run_synthesis()` |
| `user_prompt` | 2255 | Available throughout |
| `evaluator_outputs` | 2264–2273 | Fully populated by line 2273 |
| `directional_candidates` | 2341 | Set by `_collect_directional_candidates()` |
| Insertion point | 2591 (stub replaced) | After all required vars in scope |

---

## Verification

```
import OK
AST OK, lines: 2719
```

Pipeline run skipped — costs real model tokens.

---

## Not yet committed

Waiting for review of the diff before commit.
