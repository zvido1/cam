# 452 PARK RECORD

**Step 452 proved the integrity of a program that was not wired to execute Step 452.**

Written 2026-08-17 at park. No repair attempted. This record is not a package artifact,
is not in §3.1, and does not affect the token.

---

## State at park — the seven facts

1. **Stage 2 did not run.**

2. **`cmd_produce` is sealed in P452 as an unconditional NOT AUTHORIZED path.**
   AST-verified: the raise is not inside any conditional and does not branch on the
   sanction, tag, or token.

3. **§4.10's 21-step production DAG is specified but never invoked.** Every Set-A producer
   is defined and none is called — `certify`, `enforce_grounding`, `promote`,
   `verify_set_a_closure`, `project_import_closure_scan`, `envelope_id`.

4. **No Pass A or Pass B governed outputs, no exercise statuses, no final mechanism
   disposition exist.** Reporting any count would be fabrication.

5. **Repairing it changes `452_production_script.py`, changes the token, and invalidates
   the signed tag.** A new construction cycle is required.

6. **The Steps 448–451 findings remain valid ON THEIR OWN PROVENANCE** and must NEVER be
   represented as results of the unexecuted L3 package.

7. **No repair attempted at park.**

---

## The two other defects, recorded so they are not rediscovered

- **`head_blob_sha256` crashes on this machine.** `guarded_git` runs `text=True`, so
  decoding uses the locale codec (`cp1255` here). Nine declared gate inputs contain UTF-8
  multibyte sequences; `452_production_script.py` alone has 4,358 non-ASCII bytes.
  `verify_gate_records()` cannot run at all and never reached the stub.
  **Fix: capture bytes, not locale-decoded text.**

- **The failure path did not fire.** `AttributeError` is not `ProductionHalt`, so §4.15's
  quarantine, failure record and halt never ran — raw traceback, no
  `452_stage2_failure_record.json`, orphaned staging directory.
  **Fix: catch `BaseException` so §4.15 always fires.**

---

## What held

Every identity gate passed. Tag verifies against the HEAD-materialized allowed-signers
blob. Tag peels to P452. Four-way token equality holds. All four gate records passed with
29 declared hashes and 0 stale. Whole repository clean. All 38 artifacts resolve from P452
and match the manifest. The construction audit was correct on the bytes it checked.

**None of these controls asks whether the entrypoint does anything.**

---

## The reusable finding

All thirteen instances of the defect class share one shape — **a thing named and not made.**
Products with no producer. Fields with no producer. Producers with no file. Finally an
entrypoint with no body. Each control added checked one layer, and each new control was
itself an instance, which is why the count kept climbing.

---

## Requirement for any future resurrection

Begin with a **pre-ratification EXECUTION gate**, not another prose gate. Before anything is
hashed, a synthetic invocation of the actual production entrypoint must demonstrably
traverse the production DAG and emit the expected synthetic closure.

**Ceremony protects what already works; it cannot confer working.**

---

## Identities at park

```
P452         3ae08d763ac1b41fe85ae583db8d2ef196e600b8
token        e0b985b43b95b311907aae7909f9c5da129ba55eebecd2980749524dd390f5a4
tag          stage2-sanction-452-e0b985b4, signed personally by Tzvi, verifies
message      a664cfef... cleared by GPT-5.6 Sol 2026-08-16
instruction  b72ec14d... ratified for Stage 1A and 1B only
```

**THE TAG DIES ON REPAIR.** The moment `452_production_script.py` changes, the token moves
and this tag authorizes nothing. Nobody should later assume it remains live.

---

## Physical state

- Worktree left at `scratchpad/wt452a` (detached at P452).
- Orphaned staging directory `.452_stage2_results.staging-1klvnv70` left intact as evidence,
  inside that worktree's `build_log/`.

Neither path is a package artifact. Both are debris from the halted invocation, recorded
here so a future session knows what they are and does not mistake them for products.
