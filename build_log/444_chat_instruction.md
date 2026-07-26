# Step 444 — BIND REPOSITORY-LOCAL EXECUTION DEPENDENCIES (verbatim brief, filed per Rule 7)

STEP 444 — BIND REPOSITORY-LOCAL EXECUTION DEPENDENCIES. GPT FLAG: the gate verifies the nine
package artifacts but NOT the repository-local modules the harness imports. Python loads from the
working tree, so with all nine artifacts pristine and a valid tag, a modified cam/core/provider_router.py
executes. Fix, rebuild to P'''/T''', new Q-prep'''. ZERO model calls, no tag, no signing, no push.
DO NOT sign message 84e6aab4... — obsolete.

REQUIRED FIX (GPT's preferred construction — whole-tree cleanliness enforced BY THE GATE):
1. The runtime gate must require, before any provider call:
     git status --porcelain --untracked-files=all
   to be EMPTY over the whole repository — not just the nine package paths. Non-empty =>
   MeasurementIntegrityHalt with the offending paths listed.
2. Execution runs from a DEDICATED DETACHED WORKTREE at the package commit (git worktree add
   --detach <path> <P'''>), which starts clean. Document this in the sanction/run instructions.
3. This binds all tracked repository-local imports to the tag-target commit and prevents untracked
   files from shadowing sanctioned modules. Do NOT attempt an enumerated dependency closure instead
   — GPT ruled it easier to get subtly incomplete.
   Note: the main working tree has pre-existing dirt (four modified 39x/40x status files, several
   untracked _*_results/ dirs). The gate SHOULD halt there; the dedicated worktree is how the run
   gets a clean tree. Don't "fix" this by scoping the check narrower.

NEGATIVE TESTS (each must HALT pre-call, before _provider_call; capture full halt output):
  h. THE NEW BYPASS: all nine package artifacts pristine, manifest pristine, valid tag present
     (stub tag verification to SUCCEED so the halt cannot be attributed to a missing tag), but
     cam/core/provider_router.py (or another genuinely imported local module) MODIFIED — must halt.
  i. an UNTRACKED file present that could shadow a sanctioned module — must halt.
  j. clean worktree + all checks satisfied except the missing signed tag — halts only on the tag
     (proves the new check doesn't mask the tag gate).
  Re-run the prior nine negative tests (a-g, f2, f3) in the new build; all must still halt.

ALSO REQUIRED (GPT): prove the harness exercised from Q-prep''' is identical to P''' —
  git diff --exit-code <P'''> <Q-prep'''> -- <the nine package paths and the manifest>
  (exit 0, no output) — or run the final negative suite detached at P''' itself.

REBUILD: commit P''' (fix + re-minted T''' over the same nine artifacts), then AFTER P''' exists
commit Q-prep''' with the new exact sanction message naming P'''/T'''/nine hashes/principal
zvido@yahoo.com/fingerprint SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs + unconditional
authorization text + its SHA-256. Mark 84e6aab4... OBSOLETE.

RECORD (GPT's ruling on the builder note — no rebuild needed for it, but record it): "The builder
note predicted that only run_stage2 would change. Step 443 also changed six lines in call_panelist
so reviewed_config_hash is read from the committed HEAD manifest. The prediction was incomplete; the
measured diff is authoritative." Put this in the status/evidence record naming the exact file.

CONSTRAINTS: edit NO cam/ file. Five reviewed semantic artifacts byte-identical to 65556ee (confirm).
Manifest carries NO commit SHA. Trust anchor, key enforcement, hardcoded scope, HEAD-manifest
authority, runtime token recomputation, four-way token equality — all preserved from 442/443. ZERO
provider calls. Re-run the deterministic zero-call tests. Mechanism-unchanged: measure per-region
hashes again across P'' -> P''' and provide scoped diffs for anything that changed.

EVIDENCE: emit build_log/444_audit_evidence.txt by EXECUTING commands and capturing stdout/stderr —
same driver discipline, ASCII-only probes, valid UTF-8, `(command produced no output)` markers. Must
include: the new gate code from P'''; all negative-test outputs (new h/i/j plus the re-run a-g/f2/f3);
the whole-tree cleanliness check firing and passing; the worktree-based clean run reaching only the
missing-tag halt; the P''' vs Q-prep''' identity diff; runtime token recomputation; nine-artifact
table; mechanism-unchanged hashes + diffs; the new Q-prep''' message + SHA-256; the obsolete-message
notice; the builder-note correction. Commit with git add -f, no push. Report the path, P''', T''',
Q-prep''', message SHA-256.

---

## BUILDER NOTES (Rule 6 — findings that change the construction)

**1. CAM_ROOT was hardcoded; worktree execution would not have bound anything.**
`CAM_ROOT = Path(r"C:\Users\Owner\OneDrive\CAM")` was a literal path to the MAIN checkout. Running
the harness from a dedicated worktree would have inspected the main checkout's HEAD and status via
`_git(... cwd=CAM_ROOT)` while `sys.path.insert(0, CAM_ROOT)` imported `cam/*` from the main tree —
so construction item 2 would have bound nothing and the gate would have reported on the wrong tree.
CAM_ROOT is now derived: `Path(__file__).resolve().parent.parent`. Without this change the rest of
Step 444 would be theatre.

**2. A measurement INPUT is outside version control — worktree runs need an extra step.**
`.gitignore:51` ignores `05 Lease Analyzer/test_data/`. Of the two lease fixtures:
  - `atreca_eastjamie_southsf_lease.txt` IS tracked (force-added at some point),
  - `atlas_meridian_warehouse_lease.txt` is NOT tracked and IS ignored.
A dedicated detached worktree therefore will NOT contain the atlas lease, and a run there will fail
in preflight. This is reported, not worked around. Consequences:
  - Worktree run instructions must include materializing the ignored fixture(s) into the worktree.
  - `FROZEN_LEASE_HASHES` still guards content: a wrong or absent fixture halts rather than silently
    measuring the wrong text. So the exposure is a failed run, not a false result.
  - Ignored files do NOT appear in `git status --untracked-files=all`, so this does not weaken the
    new cleanliness check; it is a separate provenance gap in the INPUT set, flagged for Chat/GPT to
    rule on (track the fixtures, or accept out-of-band inputs with hash pinning).
