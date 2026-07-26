# Step 444 — Bind repository-local execution dependencies — CODE STATUS

**Status:** COMPLETE. Both commits made. ZERO model calls, no tag, no signing, not pushed.

- **P‴ (package) = `6a32d47fde64147a0987ce76027e968f3fcb8396`**
- **T‴ (token) = `f341a1886973bfec6d2e1f776b81fec29e16bdf7a3f1f2740f10aab876d7d352`** (same nine artifacts)
- **Q-prep‴ = the commit containing this file**
- **Exact sanction message SHA-256 = `56bce9e915ef56361f5a166e71a78763bbcd2babc9b1f8d341f62f75c51560be`**
- **OBSOLETE, never signed:** `84e6aab4…` (P″ `b05b735`) and `3de7329c…` (P′ `3fb5f39`).

## The flag, confirmed
The gate verified the nine package artifacts but not the repository-local modules the harness
imports. Python loads `cam/core/provider_router.py` and its transitive imports from the working tree
via `sys.path`, so with all nine artifacts pristine and a valid tag, a modified local module executed.

## Fix
1. **Whole-tree cleanliness enforced by the gate:** `git status --porcelain --untracked-files=all`
   must be EMPTY over the entire repository before any provider call; non-empty halts with the
   offending paths listed. Deliberately **not** an enumerated dependency closure.
2. **`CAM_ROOT` derived** from the harness file's own location instead of a hardcoded path.
3. **Execution from a dedicated detached worktree** at the package commit, documented in the
   sanction record.

### Why item 2 was mandatory, not cosmetic (Rule 6)
`CAM_ROOT` was `Path(r"C:\Users\Owner\OneDrive\CAM")` — a literal path to the **main** checkout. A
worktree run would have inspected the main checkout's HEAD and `git status` via `_git(cwd=CAM_ROOT)`
while `sys.path.insert(0, CAM_ROOT)` imported `cam/*` from the main tree. **Construction item 2 would
have bound nothing** and the gate would have reported on the wrong tree. Verified after the fix:
running in the worktree, the harness reports `CAM_ROOT` == the worktree and `HEAD` == P‴.

## Negative tests — 12 run in a CLEAN detached worktree at P‴, 12 HALT pre-call
**New:** (h) **the new bypass** — nine artifacts and manifest pristine, tag verification **stubbed to
succeed**, `cam/core/provider_router.py` modified → HALT on whole-tree cleanliness, offending entry
` M cam/core/provider_router.py`. · (i) untracked `cam/core/provider_router_shadow.py` → HALT,
`?? cam/core/provider_router_shadow.py`. · (j) clean worktree, no stubs → passes every new check and
halts **only** on the missing tag, proving the cleanliness check does not mask the tag gate.

**Re-run and still halting:** (a) working-tree manifest ≠ HEAD blob · (b) harness entry removed ·
(c) artifact added · (d) artifact omitted · (e) artifact hash altered · (f) stale token field ·
(f2) `--stage2-sanction` mismatch · (f3) tag embeds stale token · (g) harness modified + entry removed
+ valid tag.

## Mechanism-unchanged — measured across P″ → P‴
**13/13 regions IDENTICAL**, including `run_stage2` and `call_panelist` (which changed in 443 but not
here), the 434 classifier, both F2 paths, `render_report` (Role-C language), `merge_panel`,
`_basis_rule`, `apply_field_grounding`, `compare_candidate`, `_provider_call`,
`run_candidate_series`, `certify_parameter_series`.

## Builder-note correction (recorded per the brief, naming the exact file)
> "The builder note predicted that only `run_stage2` would change. Step 443 also changed six lines in
> `call_panelist` so `reviewed_config_hash` is read from the committed HEAD manifest. The prediction
> was incomplete; the measured diff is authoritative."

The file containing the incomplete prediction is **`build_log/443_chat_instruction.md`** (committed
inside P″ `b05b735`, section "BUILDER NOTE (Rule 6)"). It is not amended — amending it would re-mint
the token — and this record supersedes it.

## FLAGGED — an input is outside version control (needs a ruling)
`.gitignore:51` ignores `05 Lease Analyzer/test_data/`. The atreca lease is tracked (force-added);
**`atlas_meridian_warehouse_lease.txt` is not tracked and is ignored.** Verified directly: a worktree
created at P‴ does **not** contain it. Consequences:
- A sanctioned worktree run fails in preflight until the fixture is materialized there.
- `FROZEN_LEASE_HASHES` guards content, so the exposure is a **failed run, not a false result**.
- Ignored files don't appear in `--untracked-files=all`, so copying the fixture in does not break
  the new cleanliness check.
- **Ruling needed:** track the fixtures, or accept out-of-band inputs with hash pinning.

## Other constraints
Five reviewed semantic artifacts **byte-identical to 65556ee**. Manifest carries **no commit SHA**.
442 trust anchor + key enforcement and 443 hardcoded scope, HEAD-manifest authority, runtime token
recomputation, four-way token equality all preserved. Build gate 4/4, wiring 7/7,
`PROVIDER CALLS MADE: 0`, `MODEL CALLS MADE: 0`. `git status --porcelain cam/` empty; no `cam/` file
edited in the repository (case (h) mutated only a disposable worktree copy, restored and verified
clean). **NOT pushed.** No tag created or signed.
