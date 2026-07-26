# Step 442 — TRUST ANCHOR AT P′ + EXPLICIT KEY ENFORCEMENT (verbatim brief, filed per Rule 7)

STEP 442 — TRUST ANCHOR AT P′ + EXPLICIT KEY ENFORCEMENT. Two commits this step: P′ (package, anchor,
policy), then Q-prep (exact message, created AFTER P′ exists so it can name P′ without
self-reference). ZERO model calls, no signing, no push.

1. PROVENANCE CORRECTION (replace the premature-tag statement — do not preserve my claim as fact):
   Replace the existing withdrawal statement with exactly:
   "No premature sanction tag or tag object was found in this repository. No model calls occurred.
   Any alleged tag created in another clone is outside this repository's current evidentiary record
   unless its raw tag object and provenance are separately produced."

2. COMMIT AT P′ — three new runtime-load-bearing authorization artifacts:
   - build_log/431_sanction_allowed_signers  (already drafted; commit it AT P′)
   - build_log/431_sanction_key.pub          (standalone public key)
   - build_log/431_sanction_policy.json      (authorized_principal: zvido@yahoo.com;
     authorized_fingerprint: SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs;
     allowed_namespace: git)
   Optionally also a message TEMPLATE with PLACEHOLDERS (never P′ itself).
   All three MUST be added to: .gitattributes eol=lf pins, committed_blob_binding, artifact_hashes,
   token derivation, and the runtime clean-tree + three-way blob checks. (artifact_hashes goes 6 → 9.)

3. RUNTIME GATE — anchor materialized from HEAD, never inherited from .git/config:
   - read the allowed-signers BYTES from HEAD:build_log/431_sanction_allowed_signers, materialize to
     a temp file;
   - invoke: git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=<materialized-temp> tag -v <tag>
   - do NOT rely on any ambient gpg.ssh.allowedSignersFile.

4. EXPLICIT KEY ENFORCEMENT (do not parse git's human-readable success prose):
   a. parse the sole authorized public key from the committed allowed-signers file;
   b. compute its SHA-256 fingerprint;
   c. require equality with the committed policy fingerprint;
   d. require the expected principal and namespaces="git";
   e. require the tag body's authorized_principal and sanction_key_fingerprint fields to match the
      policy;
   f. verify the tag using an allowed-signers file containing ONLY that authorized key.
   Rationale to encode in a comment: if verification succeeds under a one-key trust anchor whose
   fingerprint was independently checked, the tag necessarily came from the authorized key.

5. COMMIT P′ and re-mint token T′ (blob-anchored over the now-9 artifacts). Manifest still carries
   NO commit SHA. Confirm the five reviewed semantic artifacts remain byte-identical to 65556ee.

6. THEN — after P′ exists — create commit Q-prep containing the EXACT unsigned sanction message
   naming: P′, token T′, manifest self-hash, all artifact identities, principal zvido@yahoo.com,
   fingerprint SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs, and the unconditional
   authorization text. Record its SHA-256 in Q-prep. Q-prep is provenance only — NOT in the runtime
   gate, NOT in token derivation.

CONSTRAINTS: no mechanism/semantic change (FIX 1a, 434 halt, terminal-fatal, F2, Role-C language
unchanged). edit NO cam/ file. Do NOT create or sign any tag. ZERO provider calls. Re-run the
deterministic zero-call tests.

REPORT — literal command output, no placeholders, no summaries:
  git rev-parse HEAD; git status --short
  git show <P′>:build_log/431_config_manifest.json
  git show <P′>:build_log/431_sanction_allowed_signers
  git show <P′>:build_log/431_sanction_key.pub
  git show <P′>:build_log/431_sanction_policy.json
  git show <P′>:.gitattributes
  git show <Q-prep>:<exact-message-path> + its SHA-256
  the committed gate code from P′ (anchor materialization + the six enforcement steps)
  token T′ recomputation table (9 artifacts, self-hash input bytes, derived vs expected, match)
  newline-equivalence per artifact
  the corrected provenance statement as committed
  proof no tag exists; proof the gate halts absent a valid signed tag
  cam/ clean; not pushed; zero model calls

---

## BUILDER NOTE (execution decisions, Rule 6)

- `build_log/431_sanction_message_draft.txt` (SHA-256 a5d80b82…, naming the superseded package commit
  c9f6dd7) is REMOVED at P′: it names a superseded commit and a superseded token, and leaving a stale
  "sanction message" in the tree is exactly the kind of misleading artifact this project has been
  burned by. The exact message is re-issued in Q-prep against P′/T′.
- `431_sanction_provenance.md` is committed AT P′ and therefore deliberately does NOT name P′ — the
  same self-reference bar that governs the manifest. Concrete P′/T′ values live in Q-prep.
- No tag is created or signed. This environment holds no sanction private key.
