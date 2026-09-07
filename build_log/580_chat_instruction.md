# Step 580 — chat instruction (verbatim, written before execution per Rule 7)

**Received:** 2026-09-06, from Tzvi, pasted from the chat session.

---

Read build_log/runs/580_attribution_fix/HANDOFF.md and run 580-1. Read only — report before starting 580-2.

---

The brief itself is `build_log/runs/580_attribution_fix/HANDOFF.md`, written by the chat session on
2026-09-06 after 579 (`7392bd3`) and already on disk. It is the document this step is audited
against; it is not reproduced here because it was not pasted into the conversation, it was written
to the repo directly.

**Two tasks. 580-1 is the history question and is read-only — do it first, because what it finds
may change 580-2's scope.** This instruction covers 580-1 only; 580-2 is not started.

**580-1 — what happened to `covered_unfavorable`.** It is defined in the schema as *"Present but
materially one-sided against tenant"*, is on all 32 topics, and fired 0 of 32 on the Butler run.
It is disabled on the 305 path at `lease_coverage.py:575` on the stated grounds that the element
layer "already assessed it more accurately", and 579 established that the element layer computes no
notion of one-sidedness at all. **So a working capability was switched off in favour of one that
was never built. Establish how that happened, from the record rather than from inference:**

- Which step disabled it? Find the commit and step number and read that step's status file. What
  did it claim the element layer would do?
- Did the element layer ever assess one-sidedness, or was the claim wrong when written? 574–576
  found `absence_adverse_to` is the only polarity signal on an element and it is read only on the
  `missing` branch — check whether that was true at the time.
- What did `covered_unfavorable` do before? The schema has `covered_unfavorable` patterns on LP-09,
  LP-12, LP-29 (v1.4.0) and a v1.1.4 note about detecting "materially asymmetric mutual
  indemnification". Were those firing? Is there a stored run from before the change showing them
  working?
- Was the trade recorded anywhere as a trade, or did it read as a cleanup?

**Report what the record says, including if it says the decision was sound at the time and
something else changed later. This is not a hunt for a culprit; it is establishing whether the
capability is recoverable and what it would take.**

**Two other perspective-adjacent things went the same way and are worth checking in the same pass,
since they may share a cause:** `exposure_perspective` (v1.4.4 says the frontend stopped using it)
and `covered_unfavorable_adverse_to` (added to all 32 topics, constant `"tenant"`, `None` in all
output per 571 §0).

**Constraints:** 580-1 read only; report before starting 580-2; no schema edits; read the code, not
the docstring.

---

# 580-2 — chat instruction (verbatim, written before execution per Rule 7)

**Received:** 2026-09-06, from Tzvi, after 580-1 was reported (`b7d82bc`).

---

I amplified 579's error rather than catching it. I called "a capability retired in favour of one that was never built" the sharpest thing in the report. It was half true — one route removed, not the capability — and I stated it as settled.

**But the correction makes the actual finding better, not weaker.**

The detector was right. A landlord-lens run showed LP-11 as `covered_unfavorable` — a state defined as one-sided *against the tenant* — and the regex had correctly found a 15-day non-monetary cure period. The output looked absurd because tenant-side prose was being shown to a landlord.

So a **narration** defect was diagnosed as a **detection** defect, and the detector was removed.

That's the third time this week the same shape has appeared. The disclosure banner threw at the exact moment it had something to disclose. The dissent was retained at merge and never rendered. And now a correct signal deleted because the sentence wrapped around it was pointed at the wrong reader.

**Display failures keep getting diagnosed as logic failures.** That's worth writing down somewhere permanent, because it's now a pattern with three instances and it predicts where to look next.

**Step 318 is the part that stings.** Four steps later, same commit, it fixed the card face that caused the misreading — its own instruction says the sidebar "correctly perspective-flips" already. The cause was repaired and the thing removed because of it never came back.

**And the scope creep is the mechanism.** 314's instruction offered three root causes, none of them this one, and limited scope to LP-11 and LP-27. The change removed the override for all 32. No status file, and "unfavorable" appears in no status file for 311–320 — so nothing recorded it as a trade, and nothing surfaced it for four months.

**On sequencing: I agree, 580-2 first.** The revert is four lines but it reinstates a keyword verdict overriding a panel verdict, which is a real design question rather than a restoration. And it converges on the same `absence_adverse_to` field 580-2(a) adds — so doing the fix first makes the revert cheaper and better-founded.

Run 580-2.

---

The 580-2 scope is in `build_log/runs/580_attribution_fix/HANDOFF.md`: (a) carry
`absence_adverse_to` through to `verdict_record`; (b) annotate the count, do not filter it;
(c) render a `Covered:` list. Verify on device on a clean load through the real user path — not a
replay, not a data-contract check. Deployment gets the same treatment as `ca68f2f` and `bea1787`:
its own change, its own effect written down, not bundled — **do not push without a separate
instruction.** State in the status what this does not fix: annotation makes the misattribution
visible, it does not make the element list less landlord-framed. No schema edits.
