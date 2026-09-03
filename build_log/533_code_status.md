# Step 533 — Six raise sites, not four. Three frontend sites, not two. The everbridge user now sees what happened.

**Date:** 2026-09-03 · **Instruction:** `build_log/533_chat_instruction.md`
**Tests: 406 passed, 3 skipped, 12 subtests — 7 new. Frontend `app.js?v=475`. Not deployed.**

---

# 1. THE CAUSES — SIX, AND THEY WERE INDISTINGUISHABLE

`grep -n "raise GateAbortError"` finds **six sites, not four**:

| # | site | cause | payload it carried |
|---|---|---|---|
| 1 | `lease_adapter.py:346` | classifier, Mode A | `gate_result["abort_message"]` |
| 2 | `lease_adapter.py:1391` | classifier, Mode C | `gate_result["abort_message"]` |
| 3 | `lease_adapter.py:1410` | extraction integrity failure | prose + last 3 errors |
| 4 | `lease_adapter.py:1424` | all extractors unparseable | prose + last 3 errors |
| 5 | `lease_adapter.py:1521` | 422C completeness | prose + failed LPs + applicability |
| 6 | **`lease_parameter_block.py:244`** | **Gate B parameter dependency** | prose + failures |

**Site 6 is not in the brief's count.** It is a fifth distinct meaning reaching the same branch.

## What the frontend could distinguish: nothing

```python
class GateAbortError(Exception):
    """Raised when the document gate check fails — not a lease."""
    def __init__(self, message: str):
        self.message = message
```

**One string, no code, no structure.** `job_manager` stored `error = f"GATE_ABORT: {e.message}"` and the
tenant record exposed nothing else. **The only discriminator available to the frontend was the prose
itself.**

**And the class docstring asserted the wrong thing for five of six sites** — "not a lease" is true only
of sites 1 and 2.

**So item 1's condition was met and the backend change was required first.** `reason_code` and `detail`
are now on the exception, set at all six sites, and carried additively through `update_tenant_status`
as `error_reason` / `error_detail`. **The `error` string keeps its exact shape**, so any consumer
matching `"GATE_ABORT:"` is unaffected.

## Fail-closed on the default

```python
        # Default is deliberately NOT `not_a_lease`. A site that forgets to
        # classify itself must not inherit the one code that blames the user's
        # document -- fail toward "we do not know", never toward accusation.
        self.reason_code = reason_code or "unspecified"
```

`test_default_is_not_not_a_lease` pins it.

---

# 2. THE WORDING

| reason_code | what the user is shown |
|---|---|
| `not_a_lease` | **"Not a commercial lease"** — the only case where this sentence is true |
| `extractor_failed` | "Analysis could not run — our extraction service failed. **This is not a problem with your document.** Please try again." |
| `extraction_unparseable` | "Analysis could not run — we could not read the extraction result. **This is not a problem with your document.** Please try again." |
| `incomplete_evidence` | "Incomplete analysis — no evidence was found for N issue areas (**named**). **Your document was read successfully**; these provisions could not be located in it." |
| `parameter_dependency` | "Incomplete analysis — a required parameter could not be determined from the lease. **Your document was read successfully.**" |
| `unspecified` / unknown | "Analysis stopped before completion. Your document was read; the run did not finish." |

**The two cases that mean our extractor broke say so explicitly.** The two that mean incomplete
analysis affirm the document was read. **An unknown code falls through to a neutral message** — a run
we cannot classify must not be reported as the user's fault.

The completeness case names the issue areas from `detail.failed_lp_names`, which the gate already
computed per Steps 476-478; nothing new is calculated.

---

# 3. THE EXERCISE — DRIVEN, NOT READ

`test_533_gate_abort_messages.py` parses `gateAbortMessage()` **out of the shipped `app.js` text** and
evaluates it, so the test fails if the wording changes. It is not a copy of the intent.

**The everbridge case, end to end, from its real payload:**

```
everbridge user now sees:
  Incomplete analysis — no evidence was found for 3 issue areas (Exclusivity,
  Guaranty of Lease, Percentage Rent). Your document was read successfully;
  these provisions could not be located in it.
```

Previously: **"Not a commercial lease"** — on a document whose classifier logged `is_lease=True` four
times.

Seven tests: all six sites classified, the fail-closed default, only-the-classifier-accuses,
our-failures-say-they-are-ours, the named issue areas, the everbridge payload, and the
error-string contract.

## A defect in my own test, caught by running it

The first version located raise sites with `re.findall(r"raise GateAbortError\((.{0,600}?)\n\s*\)")`
— which matches only raises ending on their own line. **It found 3 of 6 and passed**, while three sites
remained unclassified. Rewritten to count occurrences by index and scan a bounded window. **The
comment in the test records this**, because a site-counting test that cannot count sites is worse than
none.

---

# 4. THE CENSUS — A THIRD FRONTEND SITE, AND A FOURTH THAT IS CORRECT

**Three frontend sites mapped GATE_ABORT to a document accusation, not two:**

| site | before | now |
|---|---|---|
| `app.js:5489` | `"Not a commercial lease"` | `gateAbortMessage(t)` |
| `app.js:14393` (now :14430) | `"Not a commercial lease"` | `gateAbortMessage(t)` |
| **`app.js:5589`** | **"This document does not appear to be a commercial lease. Please check the uploaded file."** | `esc(gateAbortMessage(t))` |

**Site 5589 was missed by the brief and by me.** It is a different ternary shape with different
wording, so a grep for the string at the other two sites would not have found it. **Item 4's census is
what surfaced it.**

**A fourth site is correct and was left alone.** `app.js:1157`:

```js
gateErrorEl.textContent = data.gate_message || "This document does not appear to be a commercial lease agreement.";
```

`gate_message` comes from `main.py:746` = `gate["abort_message"]`, guarded by `if not gate["is_lease"]`
— **the classifier's own verdict on the template-upload path.** This is the one place entitled to say
it, and its fallback is right. **Not changed.**

## Everywhere else: no conflation

`grep` for `GATE_ABORT` and for tenant-error reads across `lease_docx_annotator.py`,
`lease_pdf_annotator.py`, `lease_report_generator.py` and `summary_generator.py` returns **nothing**.
**The annotators and the batch summary never see the tenant error at all** — they render results, and a
gate-aborted run has no result to render. **The conflation was frontend-only, across three sites.**

The API error body is the raw `error` string, unchanged, now accompanied by `error_reason` and
`error_detail`.

---

# WHAT IS NOT ESTABLISHED

- **The frontend was not exercised in a browser.** `gateAbortMessage()` is verified by parsing the
  shipped source and evaluating its branches in Python, plus `node --check`. **No rendered page was
  observed**, and Step 522's note that this surface is untested still stands for the DOM itself.
- **Only `incomplete_evidence` has been driven from a real payload.** The other five codes are
  exercised from constructed values; no live run has produced `extractor_failed`,
  `extraction_unparseable`, `parameter_dependency` or `unspecified`.
- **`not_a_lease` has never been observed on a real document in this arc** — every real lease passed
  the classifier.
- **Older jobs have no `error_reason`.** A job record created before this change falls to the
  `unspecified` branch and shows the neutral message, not the old text. That is the intended
  degradation but it is a visible change for in-flight jobs.
- **Nothing about the gate, the matcher or extraction was changed.** The three real leases still abort;
  they now say why. **This is a message fix, and the defect Step 531 measured is untouched.**
- **Not deployed.**
