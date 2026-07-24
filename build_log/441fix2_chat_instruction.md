# Step 441-fix2 — REWORK COMMIT BINDING TO CONSTRUCTION A (verbatim brief, filed per Rule 7)

**Filed to disk before execution.** Two Chat messages compose this brief: (1) the 441-fix2
instruction, (2) the Option-3 ruling answering the builder's attestation-form question. Both are
reproduced verbatim below. The builder is audited against these bytes.

---

## MESSAGE 1 — 441-fix2 instruction (verbatim)

STEP 441-fix2 — REWORK COMMIT BINDING TO CONSTRUCTION A. The committed manifest records the
CONTAINING commit inside the package commit (construction (d)) — a fixed-point fiction: a manifest
blob inside commit C cannot contain C, so the commit-pointer is not third-party reproducible and the
runtime HEAD check validates an impossible value. The blob-anchored TOKEN is sound and unchanged;
only the COMMIT-BINDING must be reworked. ZERO model calls, fresh token, stop for delta audit.

WHAT'S BROKEN (confirmed from committed bytes): 431_config_manifest.json, committed inside the
package commit, contains a pinned_commit field referencing that same commit. Impossible by
construction. Must move to Construction A.

CONSTRUCTION A — implement exactly:
1. The COMMITTED PACKAGE MANIFEST (431_config_manifest.json) contains NO commit SHA. Only:
   - artifact git paths;
   - per-artifact committed-blob SHA-256;
   - manifest self-hash;
   - token derivation data + the derived token.
   Remove the pinned_commit / containing-commit field entirely from the committed manifest.
2. Commit the package (call it commit P). P now exists and has a real SHA.
3. Create a SEPARATE sanction/attestation record (a distinct file, e.g. build_log/431_sanction_record.json,
   committed in a LATER commit, OR an annotated/signed tag on P) that records:
   - package_commit = P (now known, because P already exists);
   - token = T;
   - manifest_blob_sha = M.
   This record is created AFTER P exists, so it can name P without circularity.
4. RUNTIME preflight verifies, halting on any mismatch before the first provider call:
   - working tree clean;
   - each executed artifact's working-tree bytes == the manifest's committed-blob SHA ==
     SHA(HEAD:<path>)  [the load-bearing blob-equality gate — unchanged, sound];
   - HEAD == the package_commit recorded in the SEPARATE sanction record (not a value inside the
     package manifest);
   - .gitattributes yields the pinned LF representation.
   The commit identity the runtime checks comes from the ATTESTATION record, not from a self-
   referential field inside the package commit.

CONSTRAINTS: no mechanism/semantic change — FIX 1a, 434 message-halt, run_stage2 terminal-fatal,
F2, corrected Role-C report language all UNCHANGED and byte-identical. Five reviewed semantic
artifacts remain byte-identical to 65556ee (confirm). edit NO cam/ file. ZERO provider calls. Re-run
deterministic zero-call tests. The token remains blob-anchored (unchanged derivation); if the
manifest's byte content changes by removing the commit field, the token/self-hash recompute
accordingly — mint the fresh token and extend the chain.

PROVENANCE: keep the prior wording (earlier tokens machine-local, not retroactively rescued) and add
that commit binding is now via a separate post-commit attestation record, not a self-referential
manifest field.

REPORT (raw, from the commit — GPT will require committed bytes, provide them proactively):
  git rev-parse HEAD
  git show --format=fuller --stat --patch <package_commit_P>
  git show <P>:build_log/431_config_manifest.json   (must show NO commit field)
  the separate sanction/attestation record (file contents or tag), showing it names P and was
    created after P
  git show <P>:.gitattributes
  the committed code for: blob-hash calc, self-hash, token derivation, WHERE the runtime reads the
    package_commit (must be the attestation record, not the package manifest), the three-way blob
    equality check, clean-tree + HEAD-vs-attestation check
  fresh token + chain; files changed; git status --porcelain cam/ empty
Commit git add -f explicit paths, no push. STOP for delta audit.

---

## MESSAGE 2 — Option-3 ruling (verbatim; answer to the attestation-form question)

STEP 441-fix2 — COMMIT BINDING via Construction A/Option-3 (signed tag load-bearing + committed
record legibility-only), per GPT ruling. Widget answer: 3. ZERO model calls, fresh token, stop for
delta audit. The two attestation artifacts have DIFFERENT jobs — do not conflate them or it's a
fancier circle.

ROOT-CAUSE CORRECTION (Rule 6 — state accurately everywhere): the earlier defect was NOT "manifest
contains its own SHA / pinned_commit=C." It was: the manifest stored the PARENT commit (f9048ed) as
head_at_build_time, and the runtime check head == head_at_build_time is structurally ALWAYS-FALSE
once the containing commit exists (run-time HEAD is the containing commit, not the parent). Use THIS
description in the report, provenance record, and status file. Do not repeat the "pinned_commit=C"
framing — the committed bytes contradict it.

CONSTRUCTION (exact sequence):
1. The COMMITTED PACKAGE MANIFEST (431_config_manifest.json) contains NO commit SHA and NO
   head_at_build_time / self-referential commit field. Only: artifact git paths, per-artifact
   committed-blob SHA-256, manifest self-hash, token-derivation data + derived token. REMOVE the
   parent-proxy commit field entirely.
2. Commit the final package as commit P. Derive token T from the committed artifact blobs
   (blob-anchored, unchanged).
3. LOAD-BEARING: create and sign an ANNOTATED tag pointing at P, containing: token T, manifest
   self-hash, complete artifact-blob identity (per-artifact blob SHA-256), package commit P, signer
   + timestamp, and the statement "Stage 2 authorized only for this exact package at P."
4. LEGIBILITY-ONLY: commit a human-readable sanction record (e.g. build_log/431_sanction_record.json)
   in a LATER commit Q, recording: package commit P, signed-tag name + tag-object ID, token T,
   manifest self-hash, artifact identity, sanction date, reviewer disposition, and the corrected
   historical explanation of the failed parent-proxy construction. This file is NOT part of the
   runtime gate.
5. RUNTIME authorization gate (execution runs from P, NOT Q):
   - check out P, detached HEAD;
   - verify HEAD == peeled signed-tag target == P;
   - verify signed tag signature valid;
   - verify working tree clean;
   - verify, per artifact: working-tree SHA-256 == SHA-256(HEAD:<path>) == manifest committed-blob
     hash;
   - verify .gitattributes yields pinned LF.
   HALT before any provider call on any mismatch. The runtime reads the sanction commit identity
   from the SIGNED TAG (which names P from outside P), NOT from any field inside the package
   manifest. Runtime does NOT need to be at Q and does NOT relax HEAD==P.

WHY NOT option 2 alone: the harness imports other repo code (cam.core.provider_router,
lease_coverage_305, etc.); executing from a descendant Q could differ in imported modules even when
the six package artifacts match, unless every dependency is separately pinned. Running from exact P
avoids that entirely.

CONSTRAINTS: no mechanism/semantic change — FIX 1a, 434 message-halt, run_stage2 terminal-fatal,
F2, corrected Role-C report language UNCHANGED and byte-identical. Five reviewed semantic artifacts
byte-identical to 65556ee (confirm). edit NO cam/ file. ZERO provider calls. Re-run deterministic
zero-call tests. Fresh token (blob-anchored) + extend chain.

REPORT (raw committed bytes, provide proactively):
  git rev-parse HEAD
  git show --format=fuller --stat --patch <P>  and  <Q>
  git show <P>:build_log/431_config_manifest.json   (must show NO commit/head_at_build_time field)
  git tag -v <tagname>   (show the signed annotated tag verifies and names P)
  git cat-file -p <tagname>  (tag object contents: token, blob identity, P, signer, statement)
  git show <Q>:build_log/431_sanction_record.json   (the legibility record)
  git show <P>:.gitattributes
  committed code for: blob-hash calc, self-hash, token derivation, the runtime gate (tag verify +
    HEAD==peeled-tag==P + clean tree + three-way blob equality) — showing the commit identity comes
    from the TAG, not the package manifest
  fresh token + chain; files changed; git status --porcelain cam/ empty
Commit git add -f explicit paths, no push. STOP for delta audit.

---

## BUILDER NOTE (environment constraint discovered at execution, Rule 6)

This environment has NO signing key configured (`git config gpg.format`/`user.signingkey` empty; gpg
holds zero secret keys). The signature on the load-bearing tag is, by this project's model, Tzvi's
sanction act — the builder neither can nor should apply it. Therefore this step delivers: (1) the
committed package **P** with the manifest carrying NO commit SHA; (2) the reworked runtime gate that
reads commit identity from a signed annotated tag (never from the manifest); (3) the fresh
blob-anchored token **T**; (4) zero-call build/tests. The signed tag (step 3) and the legibility
record Q (step 4) are handed to Tzvi with the exact commands and body, to be applied AFTER P exists —
which is the intended non-circular ordering.
