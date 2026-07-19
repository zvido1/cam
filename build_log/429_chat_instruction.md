# Step 429 — Chat Instruction: Robust target resolution + loud failure on unresolvable target + real-output fixture, then Gate C re-run

**Author:** Chat instance
**Date:** 2026-07-14
**Builder model:** Sonnet 5, HIGH reasoning
**Provenance:** Written verbatim to `build_log/429_chat_instruction.md` before any code (CLAUDE.md Rule 7). This file is the sanctioned instruction; do not deviate from it without a new written instruction.

---

## Part 0 — Instruction provenance (do this first)

This file must exist on disk, committed, before any code change. It already does (Chat wrote it). Claude Code: confirm it is present and read it in full before touching either module. If it is not present, STOP and report — do not reconstruct it from memory.

---

## Why 429 exists (read before coding)

428 (Gate C, N=10) returned **0/10 extraction, 0/10 Gate B pass, 10/10 abort** — verdict NO. Config-integrity PASSED (prompt/config hashes identical across all 10 and matching 427). The 0/10 is **not a recall failure**: a diagnostic probe showed the model located and quoted all four parameter values correctly (`100%`, `45.79%`, `3%`, `$3.75 per rentable square foot`). The failure is a target-label format mismatch:

- The schema/prompt asks for the bare ordinal `"Target 1"`.
- The model instead echoed the full descriptive label, e.g. `"Target 1: Tenant's Share of Operating Expenses percentage"`.
- `extract_parameters()` in `lease_parameter_block.py` maps that field back to a parameter with `target_to_param.get(match.get("target", ""), match.get("target", ""))`, the lookup misses, it falls back to the raw fuller string, that string is not in `PARAMETER_NAMES`, and the `continue` **silently discards the whole record — quotes included** — before `resolve_span` is ever called.

This is the same defect class 421C documented (correctly-located evidence lost to an unreviewed assumption between model output and gate), now one layer down. 428's failure mode is **silent discard**. The fix is **"never discard or mislabel silently,"** NOT "discard less."

Full report: `build_log/428_gate_c_parameter_assignment_stability.md`.

---

## The two fragile sites (exact, current code)

### Site 1 — `cam/adapters/lease_review/lease_parameter_block.py`, `extract_parameters()`

Current code (verbatim):

```python
target_to_param = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
parameters: Dict[str, Parameter] = {}

for match in elicitation_result.get("target_matches", []):
    param_name = target_to_param.get(match.get("target", ""), match.get("target", ""))
    if param_name not in PARAMETER_NAMES:
        continue
```

The `.get(key, default)` returns the raw label on a miss; `if param_name not in PARAMETER_NAMES: continue` then throws the record away with no record of the loss. **This is the site that turns model behavior into total data loss.**

### Site 2 — `cam/adapters/lease_review/lease_element_elicitation.py`, `resolve_elicited_spans()`

Current code (verbatim):

```python
target_to_element = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
records: List[dict] = []
counter = 0
for match in elicitation_result.get("target_matches", []):
    target_label = match.get("target", "")
    element_id = target_to_element.get(target_label, target_label)
```

Here the miss falls back to `target_label` (the fuller string) and **keeps the record, tagged with the wrong `element_id`** — the "silent mislabel-and-keep" variant. On the LP path (this module is on the live LP path — it is an adapter, NOT `cam/core/`, so editing it is permitted), a malformed label silently corrupts `elicited_by` provenance rather than losing data, but it is the same unreviewed assumption and must be fixed too.

---

## The fix (in principle)

1. **Resolve the target robustly by parsing the leading `Target N` ordinal.** The ordinal is a deterministic structural fact present at the start of the label in both the bare form (`"Target 1"`) and the echoed form (`"Target 1: <description>"`). Parse the integer `N` from the leading `Target\s+(\d+)` and map `N → elements[N-1]` (1-indexed, matching the existing `enumerate(..., start=1)` construction). Do NOT exact-string-match the whole label. Do NOT attempt fuzzy/semantic matching on the description text — only the ordinal is authoritative.

2. **On resolution FAILURE, RAISE — loud, recorded — never silent discard, never silent mislabel.** An unresolvable target (no parseable leading `Target N`, or `N` out of range for the `elements` list) is an ERROR. It means the model returned something the code cannot map, and guessing past it is exactly the 428 failure. Raise a clear exception naming the offending `target` value and the expected form.
   - In `extract_parameters()` (`lease_parameter_block.py`): replace the silent `continue`-on-miss with a raise.
   - In `resolve_elicited_spans()` (`lease_element_elicitation.py`): replace the `target_to_element.get(label, label)` mislabel-and-keep fallback with the same robust ordinal parse and the same raise-on-unresolvable.

3. **Behavior when resolution SUCCEEDS must not change.** When the ordinal parses and is in range, both functions must produce byte-identical output to today. This is a narrowing of the failure surface, not a change to the happy path. State this boundary explicitly in the report.

4. **Add a fixture built from REAL observed model output.** The 428 bug was invisible because existing tests fed clean `"Target 1"` records the model does not actually produce. Build a fixture whose `target` fields carry the echoed form `"Target 1: <full label>"` (use the exact strings from the 428 report's diagnostic probe — `"Target 1: Tenant's Share of Operating Expenses percentage"`, `"Target 2: Building's Share of Project Operating Expenses percentage"`, `"Target 3: Rent Adjustment Percentage (annual escalation rate)"`, `"Target 4: Base Rent amount stated in the key-terms block"`, with their quotes). A test using this fixture must show the values now resolve — i.e. the fix actually recovers what 428 lost.

5. **Re-run Gate C (N=10)** to confirm stability before any wiring. Same harness as 428. Report the new per-parameter extraction rate, Gate B pass rate, config-integrity, and verdict.

---

## Scope discipline (hard boundary)

- Touch exactly two source files: `lease_parameter_block.py` and `lease_element_elicitation.py`. Both are adapters (`cam/adapters/lease_review/`), NOT `cam/core/` — editing them is permitted; `cam/core/` epistemic logic is frozen for patent purposes and must not be touched.
- `lease_element_elicitation.py` is on the live LP path. Keep the change NARROW: fix ONLY (a) target-resolution robustness (ordinal parse) and (b) silent-failure behavior (raise instead of mislabel-and-keep). Change NOTHING about behavior when resolution succeeds — same offsets, same `elicited_by`, same dedup, same records for well-formed input.
- Do NOT change the prompt, the schema, the resolver (`resolve_span` / `lease_evidence_spans.py`), the normalization profile, `PARAMETER_TARGETS`, `DEPENDENCY_MAP`, Gate B, or attachment logic. The model-output variation is real and will recur; the fix is to handle it in resolution, not to try to force the model to emit the bare form.
- Do NOT wire the parameter block into the live pipeline in this step. Wiring is gated on Gate C passing (423 spec §8), which is what the re-run measures.

---

## Do-NOT list

- Do NOT "discard less" — the failure was silent discard; do not replace it with a quieter discard, a log-and-continue, or a default parameter. Unresolvable target → raise.
- Do NOT add fuzzy/semantic matching on the label description. Only the leading ordinal is authoritative.
- Do NOT change happy-path behavior in either function.
- Do NOT touch anything in `resolve_elicited_spans()` beyond the two sanctioned changes (ordinal-parse resolution + raise-on-unresolvable), and do NOT edit any other function in `lease_element_elicitation.py` at all — `dedupe_elicited_spans`, `elicit_and_resolve_for_lp`, `build_elicitation_sidecar`, `elicit_spans_for_targets`, loaders, and the module docstring are OFF-LIMITS. This is the live LP path; no "while I'm in the file" cleanup, refactor, rename, or comment-tidy rides along. Same fence for `extract_parameters()` in `lease_parameter_block.py`: only the resolution/failure lines change; every other function in that file stays byte-identical.
- Do NOT edit `cam/core/` anything.
- Do NOT modify the prompt, schema, resolver, normalization profile, or the target/dependency tables.
- Do NOT test only with clean `"Target 1"` records — that is exactly what hid the 428 bug. The real-output fixture is required.
- Do NOT push. Explicit-path staging with `git add -f` only.
- Do NOT characterize document content or model output from priors — quote the artifact (Rule 6).

---

## Required tests

1. **Real-output fixture, parameter block:** feed `extract_parameters()` (via a mocked `elicit_spans_for_targets` returning the echoed-label fixture from the 428 probe) and assert all four parameters now resolve to verified `Parameter` objects with the correct values. This is the regression test that would have caught 428.
2. **Real-output fixture, element elicitation:** feed `resolve_elicited_spans()` the echoed-label fixture and assert each record is tagged with the CORRECT `element_id` (not the raw label), with unchanged offsets/verification.
3. **Raise-on-unresolvable, BOTH modules:** a target with no parseable leading `Target N` (e.g. `"Tenant's Share"` with the ordinal stripped) and a target whose ordinal is out of range (e.g. `"Target 99"` against a 4-element list) must each raise a clear, named exception in BOTH `extract_parameters()` and `resolve_elicited_spans()`. Assert the exception message names the offending value.
4. **Happy-path unchanged, BOTH modules:** a clean bare-`"Target N"` fixture must produce output byte-identical to the pre-429 behavior (same parameters / same records, offsets, `elicited_by`). This guards the narrow-scope boundary.
5. Existing test suite: 0 regressions against the current total.

---

## Report requirement

Write `build_log/429_robust_target_resolution.md`:
- What changed, in both files, with the exact before/after of the resolution lines.
- Explicit statement that happy-path behavior is unchanged and why (the boundary).
- The real-output fixture and what it recovers relative to 428.
- Gate C re-run results: per-parameter extraction rate (N=10), Gate B pass rate, config-integrity hashes (confirm they still match 427/428's prompt/config hashes, since prompt/config did not change), and the plain verdict (stable enough to wire, yes/no).
- If Gate C still does not pass, state the new failure mode plainly and do NOT wire — same discipline as 428.
- **LP-path terminal-design note (record this explicitly, do not resolve it in 429).** 429 makes both paths raise-on-unresolvable uniformly. On the parameter path this is unambiguously correct and terminal: the parameter set is small and every entry is Gate-B-load-bearing, so a call-level abort is the right final behavior. On the LP path, uniform raise is strictly safer than today's silent mislabel-and-keep and is correct FOR NOW, but whether the *terminal* LP-path behavior should be call-level abort or a record-level unresolvable-target error routed to Review Needed — consistent with "a failed trace kills the trace, not the evidence" (423 spec §7) — is an OPEN design question, deliberately DEFERRED to a follow-on (429b or the wiring step), not settled by 429. State in the report that the LP-path abort is now live but UNTESTED by Gate C (Gate C exercises only the parameter path), and that its terminal design is a tracked, deferred decision — not a latent edge case. Do not widen 429 to carry this routing-doctrine decision; 429's whole point is the narrow fix.

---

## Git (explicit-path staging, no push)

```
git add -f build_log/429_chat_instruction.md
git add -f build_log/429_robust_target_resolution.md
git add cam/adapters/lease_review/lease_parameter_block.py
git add cam/adapters/lease_review/lease_element_elicitation.py
git add <new/changed test files by explicit path>
git status   # confirm nothing unintended staged; no .tmp.driveupload sweep
git commit -m "429: robust Target-N ordinal resolution + raise-on-unresolvable in parameter block and element elicitation; real-output fixture; Gate C re-run"
```

No `git add .` / `git add -A`. No push.

---

## Copy-paste prompt for Claude Code

> Read `build_log/429_chat_instruction.md` in full before doing anything; it is the sanctioned instruction for this step (CLAUDE.md Rule 7). Confirm it is present on disk — if not, STOP and report.
>
> Then read, in full, the current state of both files you will edit — `cam/adapters/lease_review/lease_parameter_block.py` (`extract_parameters()`) and `cam/adapters/lease_review/lease_element_elicitation.py` (`resolve_elicited_spans()`) — before writing any code. Do not work from memory of them.
>
> Implement 429 exactly as the instruction specifies: (1) resolve targets by parsing the leading `Target N` ordinal (map N→elements[N-1], 1-indexed) instead of exact-string-matching the whole label; (2) on unresolvable target (no parseable leading ordinal, or N out of range) RAISE a clear named exception in BOTH functions — never silently discard (parameter block) and never silently mislabel-and-keep (element elicitation); (3) leave happy-path behavior byte-identical when the ordinal parses and is in range. Change nothing else — not the prompt, schema, resolver, normalization profile, target/dependency tables, Gate B, or attachment; do not touch `cam/core/`; do not wire into the live pipeline.
>
> Add the required tests, including a fixture built from the REAL echoed-label model output in the 428 report (`"Target 1: Tenant's Share of Operating Expenses percentage"` etc., with their quotes) proving the values now resolve, and a raise-on-unresolvable test in BOTH modules. Confirm 0 regressions.
>
> Re-run Gate C (N=10, same harness as 428). Write `build_log/429_robust_target_resolution.md` with the before/after resolution lines, the unchanged-happy-path statement, the fixture, and the Gate C results (per-parameter extraction rate, Gate B pass rate, config-integrity hashes, plain verdict). If Gate C still does not pass, do NOT wire — report the failure plainly.
>
> Stage with explicit paths and `git add -f` for `build_log/` files (never `git add .`/`-A`), commit with the 429 message, do NOT push. Reasoning effort: HIGH — this hinges on not guessing past an unresolvable target.
