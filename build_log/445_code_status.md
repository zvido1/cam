# Step 445 — Track the lease fixtures and bind them into the package — CODE STATUS

**Status:** COMPLETE. Both commits made. ZERO model calls, no tag, no signing, not pushed.

- **P4 (package) = `d679eec8525fa672724a012f7d1fac0d0d8e7620`**
- **T4 (token) = `ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca`** (ELEVEN artifacts)
- **Q-prep4 = the commit containing this file**
- **Exact sanction message SHA-256 = `685d9dfe60cd9de5f808803ddee5507e8d6e15f1109f78c0b79de1a4c7674ec6`**
- **OBSOLETE, never signed:** `56bce9e9…` (444), `84e6aab4…` (443), `3de7329c…` (442).

## Item 4 first — the gate on whether this step could proceed at all
The brief required stopping if the LF pin changed the reviewed fixtures. Measured **before**
committing anything, by running the real path (`parse_document` →
`build_canonical_source(NORMALIZATION_PROFILE_V2)`) over both representations of each lease:

| lease | CRLF form | LF form | == FROZEN_LEASE_HASHES |
|---|---|---|---|
| atreca | `7118cc6d…` | `7118cc6d…` | **True (both)** |
| atlas | `da9b5655…` | `da9b5655…` | **True (both)** |

`source_document_hash` is **invariant** under CRLF→LF, so the pin does not alter reviewed content and
the "report and STOP" branch was not triggered. The atreca working-tree copy (CRLF, 160,608 B) was
then normalized to LF (160,244 B), matching its already-LF committed blob; atlas was already LF.

## What changed
1. Both leases **force-added**; `05 Lease Analyzer/test_data/` remains gitignored (verified: sibling
   fixtures still ignored). Only the two files the measurement reads are tracked.
2. Both **pinned `text eol=lf`**.
3. Both added to `EXPECTED_PACKAGE_ARTIFACTS` (names **and** git paths) and therefore to
   `committed_blob_binding`, `artifact_hashes`, token derivation, and the runtime three-way blob
   equality + clean-tree checks. **Nine → eleven.**

### Latent bug fixed while doing it (Rule 6)
`build_stage1` synthesized every binding entry as `git_path = f"build_log/{name}"` — silently
assuming all artifacts live in `build_log/`. The leases do not. Rather than special-case them, the
hashed file set **and** the binding git paths are now derived from `EXPECTED_PACKAGE_ARTIFACTS`, the
same constant the runtime gate enforces, so the build-time and run-time sets cannot drift apart.

## Tests — all run in a clean detached worktree at P4
**New:** (k) atlas lease edited (`22.4%`→`99.9%`), tag stubbed VALID → HALT:
`atlas_meridian_warehouse_lease.txt: working-tree LF sha256 bbaa28ac72ec != HEAD blob da9b5655c5ca`.
(l) atreca lease deleted, tag stubbed VALID → HALT: `working-tree file … missing`.

**POSITIVE demonstration** — the point of the whole step: a fresh worktree at P4 **contains both
leases** (160,244 B / 31,755 B, 0 CRLF), preflight admits **7/7**, both `hash_matches_frozen=True`,
and the gate halts **only** on the missing signed tag.

**Re-run, all still halting:** (a)–(g), (f2), (f3), (h), (i), (j). Total **14/14 halt pre-call**.

## Mechanism-unchanged — measured across P‴ → P4
**13/13 regions IDENTICAL.** No scoped diff needed.

## Other constraints
Five reviewed semantic artifacts **byte-identical to 65556ee**. Manifest carries **no commit SHA**.
All 442/443/444 protections preserved: committed trust anchor, explicit key enforcement, hardcoded
scope, HEAD-manifest authority, runtime token recomputation, four-way token equality, whole-tree
cleanliness, derived `CAM_ROOT`. Build gate 4/4, wiring 7/7, `PROVIDER CALLS MADE: 0`,
`MODEL CALLS MADE: 0`. `git status --porcelain cam/` empty; no `cam/` file edited (tests (h), (k),
(l) mutated only a disposable worktree, restored and verified clean). **NOT pushed.** No tag created
or signed.
