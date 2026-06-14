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

---

## ⚠️ GIT WORKFLOW — CRITICAL ⚠️

### Why we push and pull

Claude Code runs in its own container. File edits in that container do NOT
automatically reach Tzvi's Windows machine. The ONLY bridge between Code's
container and Tzvi's local repo is GitHub: Code pushes, Tzvi pulls.

**This is non-negotiable. Without the push, the work does not exist for Tzvi.**

### Work directly on main — no worktrees, no branches

```bash
cd "C:\Users\Owner\OneDrive\CAM"
git checkout main
git pull origin main
# edit files
git add -A
git commit -m "Step NNN: [short description]"
git push origin main
```

Railway auto-deploys from main. Tzvi pulls from GitHub to sync his local repo.

### The One Rule
**Every change must be pushed to `main` before a step is marked complete.**
A step is not done until the commit is on `main` AND the version number in
`05 Lease Analyzer/static/index.html` is confirmed.

### Never Do This
- ❌ Create a `claude/*` worktree or branch
- ❌ Edit files anywhere other than `C:\Users\Owner\OneDrive\CAM`
- ❌ Push to a feature branch and call the step complete
- ❌ Commit without pushing — the commit is invisible to Tzvi
- ❌ Declare a step done without verifying the version number in index.html

### If There Are Merge Conflicts on Main
Report in the status file under "Decisions Needed" — do not force-push.

---

## After Every Step
End your message to Tzvi with:

```
✅ Step NNN complete. Status written to build_log/NNN_code_status.md.
Pushed to main as <SHA>. Run: git pull (in C:\Users\Owner\OneDrive\CAM)
then hard-refresh browser.
👉 Tell Chat: "Step NNN is done"
```

Or if blocked:

```
⚠️ Step NNN blocked. See build_log/NNN_code_status.md for details.
👉 Tell Chat: "Step NNN is blocked, read the status"
```
