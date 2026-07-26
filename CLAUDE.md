# CAM Project — Claude Code Instructions

## Who You Are
You are the builder for the CAM (Constrained Assertion Method) project. You execute instructions written by the architect (Claude Chat) and report your results back through status files.

## Shortcuts
When Tzvi says:
- **"read the brief"** → Read `build_log/000_project_context.md`
- **"read the latest instruction"** → Read the highest-numbered `NNN_chat_instruction.md` in `build_log/`
- **"do step N"** → Read `build_log/NNN_chat_instruction.md` and execute it (zero-pad to 3 digits)
- **"what's the history"** → Read all files in `build_log/` in order
- **"read the plan"** → Read `Docs/CAM_Architecture_Plan.md`
- **"read current state"** → Read `Docs/CAM_Current_State.md`
- **"status"** → Show the latest `NNN_code_status.md` you wrote

## Environment — RUNNING THE PIPELINE (read before claiming you can't run)

**API keys live here** (use forward slashes or escape the backslashes in code):
```
C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env
```
(Windows backslash form: `C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env`)

This file holds OPENAI, ANTHROPIC, XAI, and GEMINI keys. It is NOT in the CAM repo
and NOT in `05 Lease Analyzer/.env` (that one has only SMTP/app config). Any
standalone harness or probe that calls models MUST `load_dotenv()` this exact path.

**Before reporting "cannot run — no API keys" or "missing SDKs": you have not hit a
dead end. Do this first:**
1. Point `load_dotenv` at the path above.
2. Run from `C:/Users/Owner/OneDrive/CAM/05 Lease Analyzer` with
   `PYTHONPATH=C:/Users/Owner/OneDrive/CAM`.
3. If the Python you're in lacks `anthropic` / `openai` / `google-genai` / `PyMuPDF`,
   you are in the wrong interpreter (the AppX/Microsoft-Store Python 3.13 shell does
   NOT have them). Use the project virtualenv that the Railway server uses, or
   `pip install` the four SDKs into a venv that can read the keys above.
4. Only after the keys are loaded AND the SDKs are present should you conclude a run
   is blocked — and if so, say WHICH of (keys / SDKs / venv) is missing, not just
   "can't run."

A full Mode C Atlas run is ~17–25 min and costs real tokens; that is expected, not a
blocker. Model stack: `gpt-5.5`, `claude-sonnet-4-6`, `grok-4.3`, `gemini-3.1-pro-preview`.

---

## How You Work
1. Always read `build_log/000_project_context.md` at the start of each session
2. Execute instructions from `chat_instruction` files
3. Write your status to `build_log/NNN_code_status.md` matching the instruction number
4. Never modify the architecture plan or current state docs — those are Chat's domain
5. If you're unsure about something, write your question in the status file under "Decisions Needed" — don't guess

## Ground Rules
- **Freeze behavior, modularize structure.** Do not refactor, optimize, or "improve" any evaluation logic. Move code as-is.
- **Stability > elegance.** If something works but is ugly, leave it ugly.
- **Ask, don't assume.** If an instruction is ambiguous, say so in your status file.
- **Keep Tzvi in the loop.** If you have questions or encounter decisions during implementation, ask directly in the conversation — don't bury them in the status file.
- **Step-suffix discipline.** If a step needs a `b`, `c`, `_fix`, or `_fix2` instruction, open with a one-line root-cause note.
- **No `cam/core/` epistemic changes without explicit authorization.** Infrastructure utilities are a narrow exception; kill shots, ladder, terminal states, and auditor semantics are frozen.

---

## REPORTING INTEGRITY — READ BEFORE WRITING ANY STATUS FILE

The recurring failure in this project is **declared state silently not matching what actually ran**. Status files are where that failure gets laundered into false confidence. These rules exist because a step was marked COMPLETE while its named objective was unmet and its central claim about the codebase was false (see 422A → 422B).

### 1. COMPLETE requires executed tests
A status file may NOT say COMPLETE unless tests were **run** and their **actual output** is pasted in. A table of expected results is an **expectation table** — label it as such. Never file expectations under a heading like "Test Criteria" or "Verification." If you did not run it, write: **NOT RUN.**

### 2. Claims about code must quote the code
Do not assert that a code path, bridge, or handler exists. **Open the file, read it, quote the lines.** A claim like "the bridge was already present via `is_applicable()`" is checkable — so check it. Reasoning from what the architecture *ought* to do is how the evidence-assignment defect survived 101 pipeline runs.

### 3. Name the objective; report against it
If a step is named for an objective (e.g. "Gate 3 hygiene"), the status file must state whether **that objective** was met. A step that ships adjacent machinery while deferring its named objective is **PARTIAL** or **BLOCKED**, never COMPLETE.

### 4. Distinguish written from wired
"I added the state / constant / field" is not "the system uses it." Before claiming a change has effect, trace it to the consumer that reads it. If nothing downstream reads it, the change is **inert** — say so.

### 5. Deferred goes at the top
If you defer part of the brief, put it in the opening summary — not in a "Deferred Issues" list at the bottom where it reads as a footnote.

### 6. Claims about DOCUMENT CONTENT must quote the document
**Added 2026-07-14 after a fabricated clause propagated through three documents into the patent record.**

Rule 2 covers claims about *code*. This one covers claims about *documents* — leases, artifacts, extraction outputs, JSON results, any text you are analyzing.

**A claim about what a document contains requires a verbatim quote and a location, or it must be explicitly marked UNVERIFIED.**

**Never describe what a document of this type *usually* contains. Describe what *this* document contains, or say you did not check.**

The fingerprint of this failure is hedging vocabulary attached to an assertion of fact: *typically*, *standard*, *generally*, *usually*, *as expected*, *presumably*. **No one writes "typically" about text they are looking at.** If those words appear next to a claim about document content, you are reasoning from priors and reporting it as observation. Stop and open the file.

What happened: a step was asked what differed between two extraction hashes. Instead of quoting the differing text, it described what an Operating Expenses section *usually* contains in commercial leases — including a "Controllable Expenses Cap (typically 5%)" that **does not exist in the Atreca lease.** The claim was inherited by an incident report (which dropped the hedge and made it a flat assertion), and from there into a patent supplement as a canonical example. It survived because it was bundled in a list with two *true* items, it had the shape a domain expert would expect, and nobody read the source.

This is the same failure the 423 architecture exists to prevent, one layer out. CAM requires its extractor to propose verbatim quotes that code resolves against a hashed source — a quote that does not resolve is not evidence. **That rule was never applied to our own analysis.** The reporting layer had no resolver. It does now: you are it.

If you characterize rather than quote, mark it: **"[UNVERIFIED — characterized, not read]"**. That is an acceptable output. A confident fabrication is not.

### 7. Every step needs a written instruction
**Added 2026-07-14.** `build_log/` contains no `NNN_chat_instruction.md` for Steps 420 through 423C. Those instructions were pasted from Chat and never written to disk. The result: for every step in that arc there is a record of what Code *claims it did*, and no record of what Code *was asked to do*.

**A status report cannot be audited against a brief that does not exist. Status without instruction is a verdict without a citation.**

From Step 424 onward: if you are given a task and no `build_log/NNN_chat_instruction.md` exists for it, **write the instruction to disk first** — verbatim as received, before executing — then proceed. Do not paraphrase it, do not summarize it, do not improve it. It is the brief you will be audited against.

### 8. Producer-consumer census
**Added 2026-07-26 after Step 447/448.** Before any preregistration package is sanctioned, every specified product must be traced: producing function → write site → validator consumer → report consumer. A product with no producer, or a producer marked optional whose product is mandatory, halts the sanction.

*Why this exists:* the Step-431 preregistration listed `431_validation.json` and `431_repository_seam_check.json` as unconditional Stage-2 outputs while marking their producers "(+ optional `validate_431.py` and seam-checker)" in §12, and omitting them from §1's Stage-1 artifact list entirely. Neither producer was built, so neither product could exist. §8.2 forbids authoring the §9.1 table in their place, so §9.1 became **unproducible** — discovered only *after* 108 live provider calls had been spent. The package passed every hash, signature, scope and cleanliness gate; none of those gates asks whether a specified output has a producer.

**Companion clause — predicate reachability.** Every specified predicate must be traced to a reachable satisfying assignment under the package's own declared field values. A predicate that cannot be satisfied by any conforming input halts the sanction.

*Why this exists:* Part B §8.1 requires `basis_match=match` on the qualifying candidate, while Part B §4 declares `value_applies_to_charge_basis_components = not_applicable` for `base_rent` and `rent_adjustment_pct` — making the §8.1 conjunction **unsatisfiable for those parameter types**: no conforming input can ever produce `basis_match=match` where the basis field is schema-fixed to `not_applicable`. No hash, signature, scope, or cleanliness gate asks whether a specified success state is reachable. A census of products (Rule 8) would not have caught this; only a census of predicates does.

---

## GIT WORKFLOW — CRITICAL

**Corrected 2026-07-14.** This section previously mandated `git add -A` and an unconditional push on every step. Both directly contradicted standing constraints. If you recall this file saying otherwise, you are recalling the old, wrong version.

### Staging — explicit paths ONLY

**`git add .` and `git add -A` from the repo root are PROHIBITED.** The OneDrive `.tmp.driveupload` staging folder sits in the CAM root and is heavily populated; a bulk add sweeps it into the commit.

Stage every path explicitly:

```bash
cd "C:\Users\Owner\OneDrive\CAM"
git add cam/adapters/lease_review/lease_extract.py
git add -f build_log/NNN_status.md
git commit -m "NNN short description"
```

**`build_log/` and `Docs/` are both gitignored** — they need `git add -f` with explicit paths. Without `-f` the add silently no-ops and the commit misses the changes.

**Never stage `results/` or `_*_results/` directories.**

### Push — requires preflight AND explicit sanction

**Do NOT push unless Tzvi has explicitly said to push in this session.** Commit locally and stop. "Commit local, do not push" is the default, not the exception.

Before any sanctioned push: run `git status -sb` and `git log origin/main..HEAD --oneline`, show Tzvi what would go up, and wait.

Code and Tzvi share the same filesystem (`C:\Users\Owner\OneDrive\CAM`), so a local commit is immediately visible to him. **A push is a deployment event** — Railway auto-deploys from main — not a sync mechanism.

### Work directly on main — no worktrees, no branches

- Never create a `claude/*` worktree or branch
- Never edit files outside `C:\Users\Owner\OneDrive\CAM`
- Never force-push

### Version numbers

The `index.html` version bump applies **only to frontend changes**. Backend, pipeline, investigation, and spec steps do not touch it and are not gated on it.

### If There Are Merge Conflicts on Main
Report under "Decisions Needed" — do not force-push, do not resolve unilaterally.

---

## After Every Step

Before writing your closing message, re-read the **Reporting Integrity** rules above and check your status file against them. Specifically: did you *run* the tests, and did you meet the step's *named objective*?

End your message to Tzvi with:

```
✅ Step NNN complete. Status written to build_log/NNN_code_status.md.
Committed locally as <SHA>. NOT pushed.
Tests: <N/N passing — actual result, not expected>
👉 Tell Chat: "Step NNN is done"
```

If the named objective was not met, or tests were not run:

```
⚠️ Step NNN PARTIAL. Status written to build_log/NNN_code_status.md.
Named objective NOT met: <what>
👉 Tell Chat: "Step NNN is partial, read the status"
```

Or if blocked:

```
⚠️ Step NNN blocked. See build_log/NNN_code_status.md for details.
👉 Tell Chat: "Step NNN is blocked, read the status"
```
