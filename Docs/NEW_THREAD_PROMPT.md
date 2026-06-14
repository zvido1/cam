# CAM — New Thread Prompt
_Last updated: 2026-06-14 (EDGAR mini-corpus built: first external real-lease fixture set. Prior: four-session paper arc through Supplement #25 / Step 397 / attorney question bundle.)_

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

## Current state (2026-06-14)

- **Patent record:** through **Supplement #25** (Architecture A Phase 2). `Patent_Current_State.md` is current through 2026-06-13 and is the orientation doc — read it first for patent state. The EDGAR corpus is NOT a patent contribution and NOT a validation result — it is a fixture asset only; do not add it to the patent record.
- **External corpus (NEW 2026-06-14):** first external real-lease fixture set built from SEC filings — 8 executed commercial leases (10-K/10-Q Exhibit 10.x), 4 property types (office / lab-office / retail-NNN / industrial), 6 jurisdictions (CA/CO/MA/NC/OK/SC), populated-vs-absent work-scope split 3/5. 48/48 fixture-integrity checks pass. Fixtures in `05 Lease Analyzer/test_data/tenants/`; manifest `05 Lease Analyzer/test_data/edgar_corpus_manifest.json`; build script `build_log/build_edgar_corpus.py` (regenerable). NO pipeline run yet — corpus is built, not evaluated. Sharpest fixtures: the **Atreca pair** (same tenant/landlord-family/date, EX-10.18 existing-building Landlord's-Work vs EX-10.19 to-be-constructed shell + tenant-built TIs = a near-controlled contrast in the STRUCTURE of landlord work, both populated) and **BOKF As-Is Work Letter** (exhibit present but obligation functionally absent = the document-presence-vs-obligation-substance edge case). NOTE: the cleanest populated-vs-ABSENT contrast is a populated lease (e.g. Atreca EX-10.18) vs an absent one (DiVall Wendy's NNN, or Quanterix/SolidPower tenant-work), NOT the two Atreca leases against each other — both Atreca leases are populated.
- **Build:** stack-frozen, in DEF-010 recall-stability DIAGNOSIS (not measurement). Last shipped code was the 378/383 governance + DEF-010a work; nothing shipped since. Corpus-building is a test_data asset, not a build change — freeze intact.
- **Most recent commits (local, UNPUSHED):** `b1ec8e7` (EDGAR mini-corpus: 8 fixtures + manifest + build script, 2026-06-14). Prior: `0c591cd` (Step 396 + Packet 02), `a5905d1` (394c/395/395b + Packet 01 + patent docs). The 2026-06-13 paper work was committed before this session.
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

The `CAM_Project_Review_2026_06_09.md` named the project's **largest risk**: **external validation is at zero.** As of 2026-06-14 one of the two trajectory-movers is DONE — the EDGAR mini-corpus is built (8 real executed leases). But that closed the *self-serviceable* half. The corpus is real external **material**; it is not yet external **reaction**. No outside person has reacted to any CAM finding. The constraint has moved from "no real leases" to "no human signal" — sharper and now bottlenecked entirely on lawyer access.

**The discipline for the next session: be honest about internal-motion-vs-progress.** Running the pipeline on the new corpus is tempting and is still INTERNAL signal — do not mistake "CAM ran on 8 real leases" for validation. The one move that now changes the trajectory:
1. **Get one real lease finding in front of one lawyer.** The corpus makes this stronger than before: you can now hand over a real, public, executed lease instead of a synthetic packet. Lead candidate fixtures identified (BOKF document-vs-obligation edge case; Atreca near-controlled pair). Blocked only on lawyer access, which Tzvi has flagged as thin.

A pipeline run on the corpus is a legitimate SECOND step, but only as a DESIGNED run with a frozen hypothesis (recall-stability), not exploratory — and it does not substitute for human reaction. If a session is about to become "run CAM on more leases and admire the output," stop and name it.

---

## Next-session menu (in honest priority order)

**Tier 1 — moves the binding constraint (do these if at all possible):**
- **Closed-lease / real-lease validation outreach** — NOW THE TOP MOVE. The EDGAR corpus gives you real public leases to put in front of a lawyer (stronger than the synthetic Packet 02). If any lawyer is reachable (Josh, or anyone), get a real lease finding in front of them. Lead fixture candidates: BOKF As-Is Work Letter (document-presence-vs-obligation-substance — sharpest value-prop question) or the Atreca pair (near-controlled absence test — most likely to produce a clear yes/no reaction). Packets/fixtures built and waiting.
- **EDGAR mini-corpus — DONE 2026-06-14** (`b1ec8e7`, local). 8 fixtures, 48/48 checks. The self-serviceable validation move is complete; what remains is human reaction (above) and an optional DESIGNED recall-stability run (see Tier-2 note).

**Tier 2 — heavy patent keystones (each its own fresh session, not a tail-end block):**
- **Prior-art triage memo** (Gap 3 / Bundle B1) — structured search of the four closest families: selective prediction/learning-to-defer, conformal prediction, self-consistency/ensemble, LLM-as-judge/debate. One memo: closest art + distinguishing feature per contribution. Prerequisite to the next item.
- **Claim-priority memo** (Gap 3) — rank the 25 supplements by novelty × support × detectability. The keystone the attorney conversation turns on. Do AFTER prior-art.

**Tier 3 — lighter owed odds-and-ends (an afternoon each):**
- Data-handling one-page statement + access-code upgrade (Gap 8) — blocks the validation ask at the first question a lawyer asks.
- Cost/runtime capture (Gap 9) — one probe script; licensing math needs it.
- Tamper-evident evidence repo (Gap 4) — private git remote with the ignore lifted for Docs/build_log; gives hashed dated commits for the conception/RTP narrative. The OneDrive sync trouble is itself an argument for this.
- `twilio_2FA_recovery_code.txt` sits in `Docs/` in plaintext on a synced drive — move to a password manager.

**Gated / parked (NOT actionable now — do not start):**
- DESIGNED recall-stability run on the EDGAR corpus — legitimate but must be hypothesis-first and freeze-respecting (it consumes model calls and touches the DEF-010 diagnosis). Not exploratory. Do only with a written hypothesis; do NOT swap models.
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
- **Fixtures:** `05 Lease Analyzer/test_data/tenants/` (atlas_meridian_warehouse_lease.txt, albireo_10postoffice_lease.txt; + EDGAR corpus 2026-06-14: bokf/everbridge/ncino/atreca x2/quanterix/divall/solidpower). Manifest: `05 Lease Analyzer/test_data/edgar_corpus_manifest.json`. Build script: `build_log/build_edgar_corpus.py`.
- **API keys:** `C:\Users\Owner\OneDrive\CAM\DoubleCheck\doublecheck-api\api_keys\.env`
- **Deployment:** Railway ("grand-nature"), GitHub `zvido1/cam`, auto-deploys on push to main. Browser: **Edge** (not Chrome).

---

## Housekeeping flagged this session

- **OneDrive `.tmp.driveupload` is heavily populated** (CAM root) — OneDrive's own sync staging is backed up; NOT a Google Drive conflict (no Google Drive markers found in work folders). Safe to leave (gitignored) but worth clearing when OneDrive is paused if sync stays stuck. This is the reason `git add .` is prohibited.
- **Two NEW_THREAD_PROMPT.md copies existed** (Docs/ and build_log/) and had drifted to different content — resolved 2026-06-13 by making `Docs/` canonical. Keep it that way; do not let a second copy go stale.
- **Refresh this file at the end of any substantive session** so the next thread orients correctly. It was ~4 weeks stale (build_log copy) / ~1 day-arc stale (Docs copy) before the 2026-06-13 overwrite.
