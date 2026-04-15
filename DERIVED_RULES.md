# HeartSync — Derived Agent Rules

**Derived from:** Analysis of CLAUDE.md, STATE.md, BOARD.md, PROTOCOL.md, and 37 handoff notes (2026-03-22 through 2026-04-06). These rules distill recurring corrections, friction points, and approval patterns across agent sessions.

---

## 1. Scope Discipline

**Rule:** Do not extend the requested change beyond the explicit brief description. If a task says "fix emoji crash," do not refactor the entire message-handling layer.

**Why:** Multiple handoffs show scope creep causing rework, late discoveries of side effects, and delays (BOARD.md shows repeated sessions with "fix regressions from previous work" items).

**How to apply:** Before starting work, list the exact file changes needed. If you discover an adjacent bug while working, add it to BOARD.md as a separate task instead of fixing it inline.

---

## 2. Safety-Critical Changes Require Tests

**Rule:** Any change to `crisis_detector.dart`, BCL-001 logic (index.js system prompts), or session-state persistence MUST include a test case or a clear explanation of which existing test validates the change.

**Why:** STATE.md documents BCL-001 v28 with 10 passing scenarios and policy-engine tests at 19/20 pass. These are the production safety guardrails. A silent regression breaks user protection. (STATE.md § Test Packs).

**How to apply:** Run `node test_constraints.js http://localhost:3000` locally before submitting. Add new S-numbered test case if the change warrants it. Do not commit crisis-detector changes without running the test pack.

---

## 3. Privacy-First: Never Store Raw Messages

**Rule:** Do not persist user or partner messages in plain text to Firestore, SharedPreferences, or any shared storage. Store only: extracted signals, summary vectors, decision-log entries, or memory tier metadata.

**Why:** CLAUDE.md § Rules explicitly forbids raw message storage. STATE.md § Privacy notes that RelationshipMapService is the reference pattern — it stores structured data, not quotes. Multiple handoffs mention audit findings around message leakage. (BOARD.md Brief 09 Memory Privacy, Brief 07B Data Trust).

**How to apply:** If adding a feature that needs to remember user input, ask: "Is this a signal or a raw message?" Signals go in WorkingNote, LearningSignal, or FollowUp. Raw messages do not go in any persistent store.

---

## 4. Test on Both Android and Web Before Touching UI

**Rule:** Any UI change (button wording, layout, navigation, input field) must be verified on Android device and web before marking done. Do not assume platform parity.

**Why:** CLAUDE.md § Rules. BOARD.md shows repeated Android-specific issues: keyboard sync problems (repeated 2026-03-26–27), IME jitter, file-picker byte-path failures (2026-03-30), biometric auth flow edge cases. The app uses native Android bridges (ChatKeyboardBridge) and Flutter's adaptive widgets. Web and Android render differently.

**How to apply:** Checklist before marking a UI task done: (1) tested on Android device (or emulator if device unavailable), (2) tested on web, (3) no console errors or crashes, (4) take screenshots if layout changed.

---

## 5. Don't Over-Engineer: Lean Feature Delivery

**Rule:** Implement exactly what the brief asks for. Do not add: optional feature flags, unused enums, speculative infrastructure, or "we might need this later" code paths.

**Why:** CLAUDE.md § Rules. BOARD.md shows rework costs when agents build elaborate scaffolding (shell-hosted composer experiment 2026-03-26, which was rolled back; extra menu category layer 2026-03-27, which was condensed). Lean code is easier to debug and audit.

**How to apply:** When a brief says "add a text field," add the field. If it says "validate with regex," add only that regex. No extra error states, loading indicators, or retry logic unless explicitly requested.

---

## 6. Handoff Hygiene: Write Before You Leave

**Rule:** Before ending a session where you made code or config changes, (1) update STATE.md with what changed, (2) update BOARD.md — move finished tasks to Done, add new discovered tasks, and (3) write a handoff .md file if the next agent will need context beyond STATE/BOARD.

**Why:** PROTOCOL.md § On Exit. STATE.md gets stale; handoffs bridge the gap when new agents pick up mid-project. Multiple sessions show missing handoffs or incomplete updates causing rework (agents re-discovering the same bug, or re-implementing the same fix).

**How to apply:** Use the template in PROTOCOL.md § handoffs. Minimum 3 sections: What I Did (bullets), What's Left (bullets), Watch Out For (gotchas). Include file paths and line numbers if the next agent needs to find your changes.

---

## 7. Context Clarity: State Current Version and Test Status

**Rule:** When updating STATE.md or a handoff, always include: current server version number, BCL-001 test count/pass rate, and date/agent of last change.

**Why:** STATE.md § Current Version is the single source of truth. Multiple handoffs reference "v11.9.0" or "10/10 local, 10/10 production" to know whether a change is production-ready. Stale version numbers cause agents to apply fixes against the wrong baseline.

**How to apply:** Edit STATE.md with: `> Last updated: YYYY-MM-DD by agent-name` at the top. Include "Server: vX.Y.Z" and test counts when relevant.

---

## 8. Flutter Context: Use ChangeNotifier + MultiProvider Pattern

**Rule:** New state-management code in Flutter must use ChangeNotifier (not raw setState) and be wired into the existing MultiProvider at the app level.

**Why:** BOARD.md shows successful integration of WorkingNotesService, LearningSignalsService, FollowUpService (2026-03-30 briefs 20–22), all built on ChangeNotifier. This pattern keeps state reactive and debuggable. Raw StatefulWidget setState is hard to test and causes stale-closure bugs.

**How to apply:** When adding a new service (e.g., FeedbackService), (1) extend ChangeNotifier, (2) add it to MultiProvider in main.dart, (3) access it via context.read<FeedbackService>() or context.watch<FeedbackService>().

---

## 9. Backend Deployment: Test Chain Must Pass Before Cloud Run

**Rule:** Before deploying to Cloud Run, run the full test chain locally: `node test_constraints.js http://localhost:3000` && `node test_policy.js http://localhost:3000`, then after deploy run it again against production URL.

**Why:** STATE.md documents the deployment command and test status (10/10 BCL-001, 19/20 policy). A silent test failure in production is a safety leak. Multiple handoffs note "verified locally" and "confirmed in production" as distinct checkpoints.

**How to apply:** Deployment checklist: (1) local tests pass, (2) gcloud deploy runs without error, (3) re-run full test suite against production URL, (4) update STATE.md with new version number and test result, (5) document any deferred test failures (e.g., "P1 PARTIAL — known, deferred to next sprint").

---

## 10. Crisis Detector Is Tier 1: Changes Require Deliberate Testing

**Rule:** The crisis_detector.dart file is safety-critical. Any change — even a word swap in a regex or threshold adjustment — requires (1) updating the matching test case in test_constraints.js, (2) running local tests, and (3) documenting why the change does not weaken detection.

**Why:** STATE.md § Safety Architecture, § Three-State Classifier. The crisis detector feeds BCL-001's ACTIVE/MONITORING/CLEAR state machine. False negatives = user at risk. False positives = bad coaching UX. This is not a performance optimization; it's a safety system.

**How to apply:** Before touching crisis_detector.dart, find the corresponding test case (S1–S10 in test_constraints.js). Confirm the change doesn't make the case fail. If adding a new pattern, add a new test case and run it locally.

---

## 11. AI Provider Fallback: Respect the Chain

**Rule:** The AI provider chain is OpenAI → Anthropic → Gemini → xAI. Do not add new providers, reorder, or hard-code a single provider in the app.

**Why:** STATE.md § Stack notes "four-provider fallback." BOARD.md Brief 19 tests screenshot upload with "GPT-4o primary, four-provider fallback." This redundancy is production hardening. Hard-coding OpenAI causes outages when OpenAI is unavailable.

**How to apply:** If adding an AI call, use the existing AiService fallback chain (sendImageChatMessage, runSessionEndUpdate, etc.). Do not create a new method that calls OpenAI directly.

---

## 12. Brief Completeness: Mark Brief Execution in BOARD.md

**Rule:** When a brief (e.g., "Brief 20: Intelligence Layer") is finished, the BOARD.md Done section should list every sub-task (Part A, Part B, Part C) with checkmarks and agent name.

**Why:** BOARD.md 2026-03-30 shows the pattern: "Brief 20: WorkingNote + EpisodicMemory models — [x] — @claude-code 2026-03-30". This granularity helps future agents understand scope and identify regressions quickly.

**How to apply:** When starting a brief, copy all sub-tasks from the brief document into BOARD.md as a checklist under "In Progress". Move to "Done" with [x] when complete. Include agent name and date on each line.

---

## 13. No Feature Flags Without a Circuit Breaker

**Rule:** Do not add a feature flag (boolean config, environment variable, or app setting) unless there is a documented way to disable it and a reason it might need to be disabled in production.

**Why:** BOARD.md shows feature delivery without feature flags — briefs are built end-to-end, tested, and deployed. Feature flags add complexity and testing burden. If a feature is not ready, it should stay on the BOARD as "todo," not hidden behind a flag.

**How to apply:** When asked "should we flag this?", first ask "is it ready to ship?" If yes, ship without a flag. If no, leave it off the branch.

---

## 14. Android Build Failures: Check Gradle Lock and Temp Workspace

**Rule:** When Gradle or pub get fails with "file in use" errors, the cause is usually an old temp workspace or a Gradle daemon lock. Do not retry from OneDrive directly. Use a fresh temp build workspace per run (see run_android.ps1).

**Why:** BOARD.md 2026-03-26 Android launch script hardening: "Add cleanup and safer device detection to reduce OneDrive/Gradle lock failures". Multiple sessions recovered from this by using temp workspaces, then switching to `--no-enable-impeller` when Vulkan crashed on-device.

**How to apply:** If Gradle fails, (1) check run_android.ps1 to confirm it's using a temp workspace, (2) kill any lingering Gradle daemons (`jps | grep Gradle` or Task Manager), (3) rebuild. If it still fails on Android device, add `--no-enable-impeller` flag.

---

## 15. Keyboard/IME Sync: Android Requires Native Bridge

**Rule:** Chat input keyboard motion on Android must use the native IME bridge (ChatKeyboardBridge in Kotlin) to track actual keyboard position. Do not rely on `viewInsets` alone — it's delayed.

**Why:** BOARD.md 2026-03-27 Chat keyboard timing shows five refinement iterations, ending with a native Android IME inset bridge that "moves only the input bar instead of the reinforcement card". Plain Flutter viewInsets has 100–200ms delay; the native bridge is realtime.

**How to apply:** If touching chat keyboard behavior on Android, check that ChatKeyboardBridge is being used. Do not remove it or replace it with pure-Flutter viewInsets. Test with rapid typing on Android device to confirm no jitter.

---

## 16. Lock Screen: Unified Auth, No Auto-Biometric on Resume

**Rule:** The lock screen uses one unified system auth flow (device credentials if available, HeartSync PIN as fallback). Do not auto-launch biometric on resume; instead, land on the full-screen LockScreen and let the user choose.

**Why:** BOARD.md 2026-03-27 Lock auth flow and 2026-03-31 "Disable auto biometric on resume so app relaunches land on the full-screen LockScreen instead of a popup over sensitive routes". Previous auto-biometric caused UX confusion and double-auth on some devices.

**How to apply:** If touching AppLockService or LockScreen, verify (1) app resumes on LockScreen, not behind it, (2) biometric is not auto-launched, (3) user taps to auth (once), (4) both device creds and PIN fallback are offered.

---

## 17. Session-Only Memory: Do Not Persist to Cloud on Private Sessions

**Rule:** When a user enables private-session mode or marks content as "session-only," do not persist that conversation to Firestore, decision logs, or any cloud service. This data stays in-memory and is wiped when the session closes.

**Why:** CLAUDE.md § Never store raw user messages; STATE.md § Privacy. BOARD.md 2026-03-25 "Fix private session mode so it does not save coaching sessions to history/cloud". Users disclose sensitive information in private mode and trust it will not be stored.

**How to apply:** Before any Firestore write (ChatService._fireSessionEndUpdate, decision log, learning signal), check `_isPrivateSession`. If true, skip the write. Confirm private sessions are excluded from RelationshipMap context assembly.

---

## 18. Notification Copy: No Partner Names or Sensitive Details

**Rule:** All notifications (lock-screen copy, reminder text, follow-up prompts) must be privacy-safe. Do not include partner names, specific issues, or identifying details that would leak context if the phone is unlocked or shared.

**Why:** BOARD.md 2026-03-25 "Notification privacy — all lock-screen copy is privacy-safe, no partner names". A notification like "Follow up: Your partner's infidelity" is a leak if the phone is seen by a roommate or left on a table.

**How to apply:** When writing notification text or prompt cards, use generic language: "How's it going?" not "Let's talk about your argument with [partner_name]". Test with relationship data filled in; confirm no names or details appear.

---

## 19. Audit Findings: Do Not Ignore Red Flags

**Rule:** When an audit (code review, test failure, or security scan) flags an issue, document it in STATE.md § Known Issues or on BOARD.md. Do not suppress the finding or mark it done without addressing it.

**Why:** STATE.md § Known Issues lists "P1 PARTIAL — pool-boy infidelity test still opens with sympathy instead of naming trust/betrayal." This is documented, not hidden. Previous handoffs show unresolved audit findings (e.g., "Fix audit findings across..." on BOARD.md 2026-03-25).

**How to apply:** If an audit surfaces a gap, (1) add it to BOARD.md under "Todo" or "Backlog", (2) document it in STATE.md § Known Issues with context, (3) if it's safety-critical, mark it as "Blocked" and note the reason.

---

## 20. Firestore Sync: RelationshipMapService Is the Reference Pattern

**Rule:** For any data that needs to persist to Firestore (RelationshipMap, decision logs, learning signals), follow the RelationshipMapService pattern: (1) define a model with toJson/fromJson, (2) add Firestore read/write methods, (3) wire into MultiProvider, (4) test persistence on restore.

**Why:** BOARD.md notes "Firestore sync missing" for WorkingNotesService, LearningSignalsService, FollowUpService. RelationshipMapService was the first complete reference; it has encryption, restore logic, and error handling. STATE.md § Stack notes RelationshipMapService works; others "persist to SharedPreferences only."

**How to apply:** When wiring a service to Firestore, (1) copy the RelationshipMapService toJson/fromJson pattern, (2) add an `_uploadToFirestore()` method, (3) call it from the service's persistence hook, (4) add restore logic to startup cloud-sync, (5) test by exporting and importing a session.

---

## 21. BOARD.md Cleanup: Move Old Done Items to Archive

**Rule:** Keep BOARD.md Done section focused on recent (< 2 weeks) completions. Move items older than 2 weeks to an Archive section or a separate file.

**Why:** PROTOCOL.md § Rules note "Keep BOARD.md lean — move items older than 2 weeks out of Done, archive if needed." BOARD.md currently has 100+ lines of done items. This makes the board hard to scan for current work.

**How to apply:** When a done item reaches 2 weeks old, move it to `## Archive (before [date])`. Keep the archive in the same file but at the bottom.

---

## 22. Context Collapse: Affair Partners Look Better Because Conditions Are Different

**Rule:** When coaching on partner comparisons (current spouse vs. affair partner, current vs. ex, current vs. idealized past), always name the distortion: the other person exists in different conditions (no shared load, no accumulated grievances, low-stakes secret). The marriage stands on its own, not how it compares to someone under favorable conditions.

**Why:** STATE.md § Key Coaching Doctrines Added (v11.9.0) — Context Collapse Doctrine. This is embedded in the WORKABLE prompt and tested in BCL-001 test pack (S2: STI deception, S10: Normal conversation). The doctrine prevents coaching that validates unfair comparisons.

**How to apply:** This is a server-side coaching rule, not a client-side rule. Ensure the system prompt includes the context-collapse doctrine, and audit any new CHAT_SYSTEM_PROMPT additions to confirm they do not contradict this pattern.

---

## 23. Decision Commitment: Affair Is Not Resolved by Talking About the Future

**Rule:** When a user says "I'll leave if things don't improve" or "I'm giving it one more try," the decision is not resolved. The user is still in the affair (or still uncommitted). Do not treat a promise about the future as a resolution of the current breach.

**Why:** STATE.md § Decision Under Active Breach: "Evaluating whether a marriage is repairable while actively running an affair is epistemically compromised." BOARD.md Brief 19 Part B adds focus guidance: "decision commitment language → spike action, dampen validation."

**How to apply:** This is embedded in the mode scaffold and MONITORING prompt. When reviewing system prompt changes, confirm the ACTIVE/MONITORING prompts include this rule. Do not add coaching that validates future promises as a substitute for present action.

---

## 24. Message History: Labels and Frames Do Not Override Behavioral History

**Rule:** The user's stated frame ("I love my partner", "This is just a rough patch") does not override the transcript. If the conversation shows infidelity, abandonment, or coercion, the frame does not change the evidence. Coaching acknowledges the stated frame and the evidence separately.

**Why:** STATE.md § Architecture Principle: "Labels and framing do not override behavioral history." This is a core safety principle in BCL-001. Multiple test cases (S5: Revenge/malicious framing, S8: Tone laundering) ensure coaching does not get manipulated by the user's label.

**How to apply:** This is implicit in the turn classifier and system prompt. When auditing system prompts, confirm there is no rule like "if the user says X is fine, treat it as fine." Always look at what actually happened in the transcript.

---

## 25. Testing New Anchor Patterns: Add Both Local Test and Production Confirmation

**Rule:** If you add a new anchor type (e.g., `new_pattern_detector`) to chat_service.dart, (1) add test cases to test_constraints.js that trigger the anchor, (2) run local tests, (3) after production deploy, monitor production transcripts to confirm the anchor fires as intended. Do not ship an anchor without local test coverage.

**Why:** STATE.md § Flutter-Side Anchor Detection lists 15+ active anchor types. Each one changes the BCL-001 state machine. A buggy anchor can cause mode scaffolds to spike the wrong coaching style or suppress validation when it should be present.

**How to apply:** When adding an anchor, (1) write a test case that describes the situation, (2) confirm the anchor fires on that input, (3) confirm the state transitions correctly, (4) run the full test pack before deploying.

---

## 26. Deployment Ordering: Deploy Server Before App

**Rule:** When server and app changes ship together, deploy the server first, confirm it's healthy, then roll out the app update. If the order is reversed, old clients hit a new server (possible incompatibility).

**Why:** This is implicit in STATE.md § Deployment Command and the test-after-deploy step. Server changes are backward-compatible with old app clients. App changes assume the server is updated.

**How to apply:** During deployment, (1) update server, (2) run production test suite, (3) roll out app update via app store or beta channel, (4) monitor for regressions, (5) update STATE.md with version numbers.

---

## 27. Enum and Model Stability: Changes Require Migration Logic or Deprecation

**Rule:** Do not change the serialization key of an enum (e.g., renaming `comparison_drift` to `comparison_drift_v2`), change a model's toJson format, or remove a field from a stored model without (1) writing migration logic that converts old data to the new format, or (2) deprecating the field and keeping it for backward compatibility.

**Why:** RelationshipMapService persists models to SharedPreferences and Firestore. If v1 stored `{relation: "spouse", relation_alias: "partner"}` and v2 removes `relation`, old data restored on upgrade will crash during fromJson.

**How to apply:** When modifying a stored model, check (1) is there migration logic in the fromJson constructor (e.g., `relation_alias = relation_alias ?? relation`)?, (2) are old enum values still handled (e.g., `try/catch` around enum lookup)?, (3) if removing a field, keep it in fromJson but do not use it in the app.

---

## 28. Development Logs: Use Save File, Not Copy All

**Rule:** When exporting development logs for analysis, use the Save File button on dev_log_screen.dart (writes to timestamped .txt) instead of Copy All. For sessions > 50 events, Copy All will truncate on clipboard paste.

**Why:** STATE.md § Dev Log Export explicitly notes this. Clipboard paste has a size limit; the Save File button writes the full transcript to device storage.

**How to apply:** When collecting a dev log from a real session, click "Save File" on the dev log screen. Upload the resulting .txt file for analysis.

---

## 29. Relationship Context: Bind Once at Assembly Time, Not Per Turn

**Rule:** When assembling context for an AI call, extract the relationship anchor (coreIssueAnchor, highSeverityContext) once at the start of ContextAssembler.buildFullContext() and reuse it across all subsequent prompt injections. Do not re-detect the anchor per turn.

**Why:** STATE.md § Flutter-Side Anchor Detection shows the anchor is the "primary frame injected into the server prompt". Re-detecting it per turn can cause frame drift (the user's language changes slightly, the anchor flips, the coaching frame suddenly shifts). The anchor should be stable per conversation.

**How to apply:** In ContextAssembler, call chat_service.detectAnchors() once and cache the result. Pass it to all helper methods (buildWorkingNotesContext, buildLearningContext, etc.).

---

## 30. No Template Injection: Use Explicit Fields, Not String Interpolation

**Rule:** Do not inject user input into prompt templates via string interpolation (e.g., `"The user said: ${userInput}"`). Use explicit fields on the context object and document which user data flows into the prompt.

**Why:** BOARD.md 2026-03-25 Bug 4: "Removed raw template injection (_specificAppreciationPrompt) from build_screen". Template injection can cause prompt injection attacks if user input includes prompt delimiters or instructions.

**How to apply:** If a prompt needs the user's name, relationship status, or other data, (1) add a field to the context object (e.g., `context.userFirstName`), (2) inject the field into the prompt via a tagged placeholder (e.g., `{{USER_FIRST_NAME}}`), (3) do not use string interpolation or `${}` syntax in the prompt itself.

---

**End of Derived Rules**

These 30 rules distill patterns from 37+ handoff sessions, multiple audits, and production deployments. They are organized by theme (Scope, Safety, Privacy, Testing, Architecture, Deployment, Coaching, UX, Development Practices) to make them easier to scan and apply.
