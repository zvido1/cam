# CAM — New Thread Prompt
_Last updated: 2026-06-13 (end of a four-session paper arc: Supplement #25 Architecture A Phase 2, Step 397 closed-form question-set design, attorney question bundle)._

> **CANONICAL LOCATION: this file (`Docs/NEW_THREAD_PROMPT.md`) is the single source of truth.** A second copy at `build_log/NEW_THREAD_PROMPT.md` exists for historical reasons and may be stale — ignore it; update only this one. (As of 2026-06-13 both hold the same content; going forward, refresh THIS file and treat the build_log copy as a stub.)

> **First task of any new thread: confirm this file is current.** If the most recent dated work below predates your actual last session, this is stale — check `Docs/CAM_Current_State.md` and `Docs/Patent_Current_State.md` frontiers, which are the authoritative end-of-session state, and refresh this file.

---

## What this project is

CAM (Constrained Assertion Method) is a framework for governing **when** an AI system may assert a conclusion. The patent is the endgame (licensing via broker; non-provisional target ~Nov 2026; attorney conversation before Sept 2026). The vered.ai lease analyzer is the first validation instance, **not the invention**. Tzvi is the sole inventor.

**Core doctrine that must not soften:** the action-type ontology (Risk / Improvement / Review Needed / Addressed are *action-type categories, not confidence levels and not leverage*); minority never silenced; measure-before-enforce; n=1 findings stay DIRECTIONAL and out of the patent record except as example. Full guardrail list (now #1–#18) in `Patent_Current_State.md`.

---

## How this session works (read before doing anything)

- **Two filesystems that cannot see each other.** The **filesystem MCP** (this Desktop session) reaches ONLY OneDrive paths (`C:\Users\Owner\OneDrive\CAM\...`). The **bash container** reaches ONLY `/mnt/...` and `/home/claude`. They are isolated. The MCP cannot run git or read container paths; the container cannot read OneDrive. For docx, build in the container from content, then deliver to `/mnt/user-data/outputs/`.
- **str_replace fails on OneDrive paths** — use `write_file` (full overwrite) or `edit_file` (line edits). `write_file` OVERWRITES the whole file — use `edit_file` to append. (A supplement was once destroyed by a careless `write_file`; be careful.)
- **Chat (this instance) writes paper; Claude Code implements + commits.** Chat does not run the pipeline or push. Sessions end with a copy-paste commit prompt for Claude Code.
- **`git add .` is PROHIBITED from the repo root** — the OneDrive `.tmp.driveupload` staging folder (heavily populated, known hazard) would get swept in. Always stage explicit paths. `build_log/` is gitignored, so Code force-adds build_log files with `-f`; `Docs/` is NOT gitignored (no `-f`).
- **Commit local, do NOT push, unless told.**
- **Stack-freeze is active.** Three evaluator models are held constant (A=claude-sonnet-4-6, B=gpt-5.4/5.5, C=grok-4.3) so output changes attribute to code, not model swaps. Do NOT swap models mid-investigation. This is a controlled variable, not a parked setting.
- Style: terse, no em-dashes, markdown in docs. Tzvi dislikes unprompted "want me to stop here?" offers, but DOES want honest pushback when continuing would be low-value.

---

## Current state (2026-06-13)

- **Patent record:** through **Supplement #25** (Architecture A Phase 2, written today). `Patent_Current_State.md` is current through 2026-06-13 and is the orientation doc — read it first for patent state.
- **Build:** stack-frozen, in DEF-010 recall-stability DIAGNOSIS (not measurement). Last shipped code was the 378/383 governance + DEF-010a work; nothing shipped since — recent sessions are all paper/design under freeze.
- **Most recent commits (local, UNPUSHED):** today's paper work needs committing (see commit prompt at bottom). Prior unpushed: `0c591cd` (Step 396 + Packet 02), `a5905d1` (394c/395/395b + Packet 01 + patent docs).
- **Schema:** v2.2.0, 32 LPs + 212 elements.

---

## What the last four sessions produced (paper arc, all freeze-safe)

| Artifact | What it is |
|---|---|
| **Supplement #24** (2026-06-12) | Cross-domain auditor lineage (FEVER/GPQA/SciFact/ContractNLI); three-layer directional governance (axis discipline / trace auditor / materiality-routing); refined minority doctrine. Guardrails #17, #18. |
| **§8.3 absence census** (393/394a/394c) | The Landlord's-Work/fixed-commencement trap is a trap of ABSENCE the four present-text axes miss. Atlas = one clean instance; Albireo = clean counter-instance; "zero cleanly-measurable cross-lease RECURRENCE instances" (strict wording). (b) Axis-2-variant vs (c) fifth-axis stays OPEN. |
| **Step 395 / 395b** | Leverage / Client Advantage as an orthogonal SECOND axis (protective disposition + advantage disposition). Favorable-absence census: AXIS WARRANTED (present-text leverage recurs; favorable absence real but drafting-dependent). NOT a patent contribution yet — design result. |
| **Step 396** | DEF-010 variance classification. LP-03 = generation defect, majority=SIGNAL, safe to gate. LP-19/LP-26 = consequence-nondeterminism, majority=UNKNOWN, LAWYER-GATED. 11-finding tail untraced. Completeness gate must be SPLIT by class. |
| **Packet 01 / Packet 02 (BLIND)** | Blind CRE-lawyer validation packets. Packet 02 supersedes 01 for sending (§8.3 Atlas/Albireo + LP-19 + LP-26). The B2/C2 "confident vs genuinely-depends" question resolves the Step 396 class-3-vs-class-4 fork. docx in `build_log/`. |
| **Supplement #25** (2026-06-13) | Architecture A Phase 2: LP-layer verdict distance + Stage 5f confidence cap (formalizes Steps 351/351b/352 RTP). Second instantiation of Supplement #18 ordinal-distance governance. Deliberate-gap rank scale; NOT_ASSESSED sentinel. |
| **Step 397** (2026-06-13) | Closed-form question-set design (paper half). Designed **Axis 5** (obligation-against-foreseeable-failure / absence-of-paired-relief) to give the §8.3 trap a closed-form home. On-paper forcing-test: Axis 5 fires on LP-03 §8.3, stays silent on LP-26/§11.2 (the discrimination property). World-question stays lawyer-gated. |
| **Attorney Question Bundle** (2026-06-13) | `Docs/Attorney_Question_Bundle.md`. Consolidated, theme-grouped, grounded question list for the patent-attorney conversation. Updates the June-9 review's Part 4 list + four parked items + today's new questions. |

---

## THE BINDING CONSTRAINT (read this before picking next work)

The `CAM_Project_Review_2026_06_09.md` named the project's **largest risk**, and it is still true and now sharper: **external validation is at zero.** 25 supplements, a question bundle, a closed-form design — and no outside person has reacted to any of it. Every commercial track and the patent's commercial-significance narrative are blocked behind this. The recent arc has been superb internal work with zero external signal.

**The discipline for the next session: be honest about internal-motion-vs-progress.** More paper is increasingly low-value. The two moves that actually change the trajectory:
1. **Get one lease in front of one lawyer** (closed-lease validation — a deal they already know; their hindsight is ground truth). Blocked on lawyer access, which Tzvi has flagged as currently thin.
2. **EDGAR mini-corpus** — 5–10 real executed leases from SEC filings. The one piece of external validation that needs NO lawyer. Solves cross-lease stability + recall fixtures + demo material at once. This is startable alone.

If a session is about to become "fourth paper deliverable in a row," stop and name it.

---

## Next-session menu (in honest priority order)

**Tier 1 — moves the binding constraint (do these if at all possible):**
- **EDGAR mini-corpus** — fetch 5–10 real executed commercial leases (10-K/10-Q Exhibit 10.x). Needs a build/fetch, not pure paper. The Albireo fixture (`build_albireo_fixture.py`) is the pattern. Highest trajectory-changing value that's in Tzvi's own control. NOTE: the FETCH needs the bash container's network (sec.gov), not the filesystem MCP — this is a Claude Code / container task, not a Desktop-paper task.
- **Closed-lease validation outreach** — if any lawyer is reachable (Josh, or anyone), get Packet 02 or a known closed lease in front of them. The packets are built and waiting.

**Tier 2 — heavy patent keystones (each its own fresh session, not a tail-end block):**
- **Prior-art triage memo** (Gap 3 / Bundle B1) — structured search of the four closest families: selective prediction/learning-to-defer, conformal prediction, self-consistency/ensemble, LLM-as-judge/debate. One memo: closest art + distinguishing feature per contribution. Prerequisite to the next item.
- **Claim-priority memo** (Gap 3) — rank the 25 supplements by novelty × support × detectability. The keystone the attorney conversation turns on. Do AFTER prior-art.

**Tier 3 — lighter owed odds-and-ends (an afternoon each):**
- Data-handling one-page statement + access-code upgrade (Gap 8) — blocks the validation ask at the first question a lawyer asks.
- Cost/runtime capture (Gap 9) — one probe script; licensing math needs it.
- Tamper-evident evidence repo (Gap 4) — private git remote with the ignore lifted for Docs/build_log; gives hashed dated commits for the conception/RTP narrative. The OneDrive sync trouble is itself an argument for this.
- `twilio_2FA_recovery_code.txt` sits in `Docs/` in plaintext on a synced drive — move to a password manager.

**Gated / parked (NOT actionable now — do not start):**
- LP-03 generation gate (the one safe DEF-010 code fix) — touches the freeze; deliberate decision, not a casual start.
- Axis-5 build — needs the lawyer panel's world-question answer first (is LP-03 §8.3 a true risk?).
- Model-tier robustness experiment — behind the freeze (don't swap models mid-investigation).
- The four parked claim-scope items (second domain, two-axis coverage, recall governance, model-tier) — these are ATTORNEY QUESTIONS (now in the bundle), not builds. Build only if the attorney says it helps the claims.
- DEF-002 — blocked by recall instability.

---

## Two different lawyer conversations — do not conflate

- **CRE attorney PANEL** — answers "is this lease finding CORRECT?" (the world-question). Instrument: Packet 02 (blind, built). Resolves LP-19/LP-26 class-3-vs-class-4 and the §8.3 world-question.
- **PATENT attorney** — answers "what claim scope?" Instrument: `Docs/Attorney_Question_Bundle.md` (built). Different person, different conversation, different urgency.

---

## Patent documentation protocol (standing)

New patent insight → in the SAME session: (1) write `Docs/Patent_Supplement_YYYY_MM_DD*.md` (full record); (2) update `Docs/Patent_Current_State.md` (Contribution Map + Supplement Index + Patent Sentences + Guardrails + Canonical Examples as applicable). The two files are always updated together. Strict wording on absence findings: "zero cleanly-measurable cross-lease RECURRENCE instances," NEVER "zero instances exist." Quantitative lease findings stay DIRECTIONAL / out of the patent record except as example.

---

## LP-ID dual-numbering hazard (read before citing any "LP-NN")

The directional prototype (Steps 389–397) uses LP IDs that DO NOT all match `cam/adapters/lease_review/lease_provision_taxonomy.py`. Partial collision (the dangerous kind): prototype LP-03/LP-26 coincide with taxonomy; prototype LP-11/LP-15/LP-19 do NOT. Crosswalk: `Docs/LP_ID_Crosswalk_Directional_Prototype_to_Taxonomy.md`. Directional-method docs use prototype IDs; patent/attorney-facing summaries must cite BOTH.

---

## Key paths

- **Orientation (read first):** `Docs/Patent_Current_State.md` (patent), `Docs/CAM_Current_State.md` (build)
- **Strategic ledger:** `Docs/CAM_Project_Review_2026_06_09.md` (gaps + 12-week sequencing), `build_log/parked_strategic_ideas.md`
- **Attorney prep:** `Docs/Attorney_Question_Bundle.md`
- **Defects:** `build_log/defects.md` (DEF-002 blocked, DEF-010 sorted by Step 396)
- **Closed-form module (RTP):** `cam/adapters/lease_review/lease_closed_form_directional.py`; results in `389`/`391`/`397` build_log files
- **Verdict distance (Supp #25):** `cam/adapters/lease_review/lease_verdict_distance.py`
- **Fixtures:** `05 Lease Analyzer/test_data/tenants/` (atlas_meridian_warehouse_lease.txt, albireo_10postoffice_lease.txt)
- **API keys:** `C:\Users\Owner\OneDrive\CAM\DoubleCheck\doublecheck-api\api_keys\.env`
- **Deployment:** Railway ("grand-nature"), GitHub `zvido1/cam`, auto-deploys on push to main. Browser: **Edge** (not Chrome).

---

## Housekeeping flagged this session

- **OneDrive `.tmp.driveupload` is heavily populated** (CAM root) — OneDrive's own sync staging is backed up; NOT a Google Drive conflict (no Google Drive markers found in work folders). Safe to leave (gitignored) but worth clearing when OneDrive is paused if sync stays stuck. This is the reason `git add .` is prohibited.
- **Two NEW_THREAD_PROMPT.md copies existed** (Docs/ and build_log/) and had drifted to different content — resolved 2026-06-13 by making `Docs/` canonical. Keep it that way; do not let a second copy go stale.
- **Refresh this file at the end of any substantive session** so the next thread orients correctly. It was ~4 weeks stale (build_log copy) / ~1 day-arc stale (Docs copy) before the 2026-06-13 overwrite.
