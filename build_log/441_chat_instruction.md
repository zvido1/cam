# Step 441 — LINE-ENDING DETERMINISM + COMMITTED-BLOB TOKEN DERIVATION (verbatim brief)

**Filed per Rule 7.** GPT ruled the CRLF/LF finding a BLOCKER for patent-facing provenance: 8d14543a
unsanctioned (retain as historical machine-local evidence only). Implement the remediation. ZERO
model calls, fresh token, stop for scoped delta audit. Do NOT run.

[Full brief pasted verbatim below.]

---

STEP 441 — LINE-ENDING DETERMINISM + COMMITTED-BLOB TOKEN DERIVATION. GPT ruled the CRLF/LF finding
a BLOCKER for patent-facing provenance: 8d14543a is unsanctioned (retain as historical machine-local
evidence only). Implement the remediation. ZERO model calls, fresh token, stop for scoped delta audit.

WHY: the manifest hashes working-tree (CRLF) bytes while git stores LF blobs, so the token is not
reproducible from the repository by a third party. Measurement logic is unaffected; repository-
verifiable execution identity is not established. Fix both the policy and the derivation.

1. PATH-SCOPED LINE-ENDING POLICY — narrowly scoped .gitattributes forcing LF for the Step-431
   execution package ONLY (files that exist). Do NOT renormalize the whole repository. Renormalize
   the authorized package files and verify each file's working-tree bytes now EQUAL its committed
   blob bytes.

2. MANIFEST DERIVED FROM COMMITTED BYTES — authoritative artifact hashes come from the STAGED/
   COMMITTED git blobs, not the checked-out newline representation. Bind: exact repository commit
   SHA; exact git path for every artifact; SHA-256 of each committed blob's raw bytes; manifest
   self-hash; sanction token derived from that committed package identity.

3. RUNTIME BLOB-EQUALITY GATE (before the first provider call) — verify and HALT on any mismatch:
   working-tree SHA-256 == manifest committed-blob SHA-256 == SHA-256 of HEAD:<artifact-path>; plus
   current HEAD equals the manifest's pinned commit; the relevant working tree is clean; every
   artifact path resolves inside the expected repository; .gitattributes yields the pinned LF
   representation.

4. EVIDENCE (semantic reviews carry forward) — prove the changed artifacts differ ONLY by CRLF→LF:
   parsed JSON identical (config, profiles, schema, fixture_preflight); Python AST identical for the
   harness; selector prompt content unchanged apart from carriage returns; no model-facing character
   other than \r changed; no requirement/fixture/config/behavior changed. Report per artifact.

5. PROVENANCE RECORD (exact wording, per GPT) — record in build/provenance record, manifest metadata,
   and report:
     "Tokens generated before the line-ending correction were derived from Windows working-tree bytes
     under core.autocrlf=true. They remain evidence of local sanction-to-execution drift gating on
     that checkout, but they are not independently reproducible from the repository's LF-normalized
     Git blobs."
     "Beginning with this package, artifact identity is derived from committed Git-blob bytes under
     path-pinned LF line endings. Runtime preflight verifies that the executed working-tree bytes
     exactly equal the pinned committed blobs and that the repository commit matches the manifest."

CONSTRAINTS: edit NO cam/ file. No mechanism/semantic change — FIX 1a, the 434 message-halt,
run_stage2 terminal-fatal machinery, F2, and the corrected Role-C report language all UNCHANGED. ZERO
provider calls. Re-run the deterministic zero-call tests. Mint a FRESH token superseding 8d14543a;
extend the chain.

REPORT: the diff; the .gitattributes; proof each package file's working-tree bytes equal its
committed blob; the new manifest (commit SHA, per-artifact git path + blob SHA-256, self-hash, token);
the runtime gate code; the item-4 newline-only evidence per artifact; deterministic tests pass with
zero calls; provenance wording in place; fresh token + chain; files changed; git status --porcelain
cam/ empty. Commit git add -f explicit paths, no push. STOP for scoped delta audit.

---

## Execution note on the one part that is logically impossible as literally worded
Part 3 asks the gate to verify "current HEAD equals the manifest's pinned commit." A manifest CANNOT
contain the SHA of the commit that includes it (self-reference). The AUTHORITATIVE, enforced guarantee
implemented instead is: for EVERY artifact, `sha256(HEAD:<git_path>) == manifest.committed_blob_sha256
== working-tree LF sha256` — proving the running commit contains exactly the sanctioned bytes
(content-addressed, stronger than a commit label). `head_at_build_time` (the build's parent commit)
and `head_matches_package_commit` are recorded for provenance but are NOT halt conditions. Flagged for
the auditor.
