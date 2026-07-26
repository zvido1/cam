# Step 445 — TRACK THE LEASE FIXTURES AND BIND THEM INTO THE PACKAGE (verbatim brief, Rule 7)

STEP 445 — TRACK THE LEASE FIXTURES AND BIND THEM INTO THE PACKAGE. Tzvi ruled (A): the leases are
generic off-the-internet documents with no confidentiality constraint, so they go into version
control and become token-bound artifacts. This closes the last provenance gap — a fresh worktree at
the package commit must contain everything the measurement needs. ZERO model calls, no tag, no
signing, no push. DO NOT sign 56bce9e9... / 84e6aab4... / 3de7329c... — all obsolete.

REQUIRED:
1. Track BOTH lease fixtures. `.gitignore:51` ignores `05 Lease Analyzer/test_data/` — force-add the
   two leases (atreca is already force-added; add atlas_meridian_warehouse_lease.txt the same way).
   Do NOT unignore the whole directory — force-add only the two lease files the measurement reads.
2. Add both to the .gitattributes eol=lf pin set (same treatment as the other text artifacts), so
   their committed blobs are deterministic across platforms.
3. Add both to the package artifact set: EXPECTED_PACKAGE_ARTIFACTS (names AND git paths),
   committed_blob_binding, artifact_hashes, token derivation, and the runtime three-way blob equality
   + clean-tree checks. The nine-artifact set becomes eleven. Update the hardcoded expected-set
   constant accordingly.
4. Confirm FROZEN_LEASE_HASHES still matches the committed blob content (the leases must hash
   identically to what 430 pinned — if the LF pin changes their bytes, report it and STOP rather
   than silently re-pinning; the reviewed fixtures must not change content).
5. Rebuild: commit P4 (fix + re-minted T4 over the eleven artifacts), then AFTER P4 exists commit
   Q-prep4 with the new exact sanction message naming P4/T4/eleven hashes/principal zvido@yahoo.com/
   fingerprint SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs + unconditional authorization text
   + its SHA-256. Mark 56bce9e9... OBSOLETE.

NEGATIVE TESTS (each must HALT pre-call in a clean detached worktree at P4; capture full output):
  k. a lease fixture MODIFIED in the worktree (tag verification stubbed to SUCCEED) -> must halt on
     blob equality / cleanliness;
  l. a lease fixture MISSING from the worktree -> must halt;
  Re-run the full prior suite (a-g, f2, f3, h, i, j) in the new build; all must still halt.
  Also demonstrate the POSITIVE case: a fresh detached worktree at P4 CONTAINS both leases (ls them),
  preflight admits 7/7, and the gate halts ONLY on the missing signed tag.

ALSO: git diff --exit-code <P4> <Q-prep4> -- <the eleven package paths and the manifest> (exit 0).

CONSTRAINTS: edit NO cam/ file. Five reviewed semantic artifacts byte-identical to 65556ee (confirm).
Manifest carries NO commit SHA. All 442/443/444 protections preserved (trust anchor, key enforcement,
hardcoded scope, HEAD-manifest authority, runtime token recomputation, four-way token equality,
whole-tree cleanliness, CAM_ROOT derived not hardcoded). ZERO provider calls. Re-run deterministic
zero-call tests. Measure per-region mechanism hashes across P‴ -> P4 and provide scoped diffs for
anything that changed.

EVIDENCE: emit build_log/445_audit_evidence.txt by EXECUTING commands and capturing stdout/stderr —
same driver discipline, ASCII-only probes, valid UTF-8, `(command produced no output)` markers. Must
include: the tracked-lease commit evidence (git show P4:<lease paths> | head, and their blob hashes);
FROZEN_LEASE_HASHES vs committed-blob comparison; the eleven-artifact token recomputation; the new
gate code from P4; all negative-test outputs (k, l, plus the re-run suite); the positive clean-worktree
demonstration (leases present, 7/7 preflight, halt only on missing tag); the P4 vs Q-prep4 identity
diff; mechanism-unchanged hashes; the new Q-prep4 message + SHA-256; the obsolete-message notice.
Commit with git add -f, no push. Report the path, P4, T4, Q-prep4, message SHA-256.

---

## BUILDER NOTES (Rule 6)

**Item 4 resolved BEFORE any change was committed, empirically.** The atreca working-tree copy was
CRLF (160,608 bytes) while its committed blob was already LF (160,244); atlas was already LF. The
question was whether the `eol=lf` pin changes the reviewed fixture content. Measured by running the
real code path (`parse_document` -> `build_canonical_source(NORMALIZATION_PROFILE_V2)`) against both
the CRLF and LF representations of each lease:

    atreca  CRLF -> 7118cc6d...   LF -> 7118cc6d...   == FROZEN_LEASE_HASHES: True (both)
    atlas   CRLF -> da9b5655...   LF -> da9b5655...   == FROZEN_LEASE_HASHES: True (both)

`source_document_hash` is INVARIANT under CRLF->LF, so the LF pin does not alter reviewed content and
the "report and STOP" branch of item 4 was not triggered. The working-tree atreca copy was then
normalized to LF so the runtime LF-pin check passes.

**A latent path bug was fixed while adding the leases.** `build_stage1` synthesized each artifact's
binding entry as `git_path = f"build_log/{name}"`, which silently assumed every artifact lives in
`build_log/`. The leases do not. Rather than special-case them, the hashed file set and the binding
git paths are now DERIVED from `EXPECTED_PACKAGE_ARTIFACTS` — the same constant the runtime gate
enforces — so the build-time set and the run-time set are one source of truth and cannot drift.
