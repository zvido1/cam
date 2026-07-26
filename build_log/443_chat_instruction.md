# Step 443 — CLOSE THE MANIFEST-TRUST BYPASS (verbatim brief, filed per Rule 7)

STEP 443 — CLOSE THE MANIFEST-TRUST BYPASS. GPT FLAG: the runtime consumes a WORKING-TREE manifest
to decide WHAT to verify. Editing it (drop the harness from committed_blob_binding, keep the token
field) lets a modified harness run under a valid tag. Executed bytes != sanctioned bytes. Fix, rebuild
to P''/T'', new Q-prep. ZERO model calls, no tag, no signing, no push. DO NOT sign the current Q-prep
message — it is obsolete.

REQUIRED FIX in the runtime gate:
1. Read HEAD:build_log/431_config_manifest.json as the AUTHORITATIVE manifest.
2. Require the working-tree manifest bytes to equal that committed blob exactly — or never consume
   the working-tree copy at all (prefer: consume only the HEAD blob).
3. Require the manifest's artifact keys AND git paths to equal a FIXED expected nine-artifact set
   (hardcode the expected set in the harness so a shrunken/extended binding halts).
4. Recompute the token at runtime from those nine HEAD:<path> blobs — do not trust recorded hashes.
5. Require: recomputed token == committed-manifest token == CLI --stage2-sanction token ==
   signed-tag embedded token. Any inequality halts before the first provider call.

NEGATIVE TESTS (each must HALT pre-call; capture full halt output for the evidence file):
  a. working-tree manifest bytes differ from HEAD blob;
  b. harness entry removed from committed_blob_binding;
  c. an artifact added to the binding;
  d. an artifact omitted from the binding;
  e. a manifest artifact hash altered;
  f. stale/incorrect token field;
  g. THE BYPASS ITSELF: harness modified AND its manifest entry removed, valid tag present,
     detached at the package commit — must halt.

REBUILD: commit P'' (fix + re-minted T'' over the same nine artifacts), then — after P'' exists —
commit Q-prep'' containing the new exact sanction message naming P''/T''/nine hashes/principal
zvido@yahoo.com/fingerprint SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs + unconditional
authorization text, with its SHA-256 recorded. Mark the prior Q-prep message OBSOLETE — superseded,
never signed.

MECHANISM-UNCHANGED EVIDENCE (GPT's secondary gap — provide, don't assert): a scoped committed diff
or exact before/after blob hashes proving FIX 1a, the 434 config_integrity_violation message-halt,
run_stage2 terminal-fatal machinery, F2, and the corrected Role-C report language are untouched
across 442 and 443. Show the diff of those regions, or hash the functions/sections before and after.

CONSTRAINTS: edit NO cam/ file. Five reviewed semantic artifacts remain byte-identical to 65556ee
(confirm). Manifest still carries NO commit SHA. Trust anchor + key enforcement from 442 preserved.
ZERO provider calls. Re-run the deterministic zero-call tests.

EVIDENCE: regenerate build_log/442_audit_evidence.txt (or a 443 successor) by EXECUTING commands and
capturing stdout/stderr — same driver discipline, ASCII-only probes, valid UTF-8, `(command produced
no output)` markers. Must include: the new gate code from P''; all seven negative-test outputs; the
runtime token recomputation from HEAD blobs; the nine-artifact table; the detached-at-P'' gate
exercise; the mechanism-unchanged diff/hashes; the new Q-prep'' message + SHA-256; the obsolete-
message notice. Commit with git add -f, no push. Report the path, P'', T'', Q-prep'', and the
message SHA-256.

---

## BUILDER NOTE (Rule 6)

`run_stage2` is one of the frozen-mechanism regions (FIX 1a + terminal-fatal). Step 443 necessarily
edits its FIRST few lines — the gate invocation and how `config_hash` is obtained — because that is
where the bypass lives. The fatal-handling machinery inside it (the `except (FatalProviderError,
MeasurementIntegrityHalt)` terminal record, the `finally` seam/partial-sidecar closure) is NOT
touched. The mechanism-unchanged evidence therefore reports `run_stage2` as DIFFERS and shows the
scoped diff of exactly what changed in it, rather than claiming an identical hash that would be
false. Every other frozen region is hash-identical.
