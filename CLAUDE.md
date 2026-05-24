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
