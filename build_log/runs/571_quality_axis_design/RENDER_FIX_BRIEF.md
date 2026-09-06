# 571-impl — fix the renderResults scope regression

**From:** chat session, 2026-09-05, after the audit (`bd7bbe0`)
**This outranks item 3.** Its own change, its own on-device pass, its own
push. Do not fold it into anything else.

---

## What is broken

`renderResults()` throws `ReferenceError: currentResults is not defined` at
`:3226`, swallowed by `loadResults`'s catch. Step 477 appended code after
the IIFE closes (`app.js:6`–`18776`), so it sits in global scope where
`currentResults` is undeclared.

`:3226` is the **first** render call after the pre-amble. Everything after
it is dead:

- 20+ render calls
- the entire tab wiring — top-tab and sub-tab handlers unwired
- ten functions with zero other callers: `renderIncompleteBanner`,
  `renderPanelBanner`, `renderDealBrief`, `renderProvisionsScopeCard`,
  `renderDealOverview`, `renderAISummaryBar`, `renderContractStatusPanel`,
  `renderTenantSelector`, `initFilterBar`, `initChatScope`
- two more reachable only inside `if (!currentJobData)`, which both entry
  points pre-set: `renderNavSidebar`, `renderProvisionHeatmap`

Measured on a clean load with no manual calls: **0 badges, tabs not
wired**, deal overview / contract status / tenant select / incomplete
banner all empty. What survives is `applyModeSpecificUI`,
`startExpiryCountdown`, `initChat`, and static HTML.

**Nothing on that page is drawn by JavaScript.**

## It is in production

`4fc4fce` (2026-08-24) is an ancestor of `origin/main`; Railway
auto-deploys from main; working-tree `app.js` is byte-identical to
origin/main's with the same post-IIFE references. Three later app.js
commits (497, 522, 533) did not disturb it — which is what an error
swallowed by a catch looks like.

**Thirteen days, silent.**

## The one piece of good news

All ten orphans read fields that **exist in today's output** — verified
field by field in the audit. This is current code that has never been
allowed to run, not rot behind a broken door. The fix should restore
working panels rather than expose a second layer, and that is testable the
moment it lands.

---

## Do

**1. Fix it.** Parameterise `currentResults` rather than moving the
functions, so the boundary that failed is explicit rather than dependent
on position in the file. Your call on shape; that was your recommendation
and it is the right one.

**2. On-device pass immediately after.** Not a replay, not a data-contract
check — load the page clean, no manual `switchResultsTab`, and confirm:
badges render, top and sub tabs are wired, and each of the twelve
previously-dead functions either draws or fails visibly. Twelve functions
executing for the first time against real records is the risk; the audit
says the shapes match, and this is where that gets confirmed.

**3. Push it.** The standing no-push rule exists to keep unreviewed work
out of production, not to keep a two-week production outage in place.
This is the case it was not written for.

**4. Then list what was judged against the shell.** Anything since
2026-08-24 whose conclusion depended on *viewing the page* was assessed
against a static shell — you flagged 549 and 558; there may be more.
Measurements taken from stored output are unaffected (570d-2, 570f, 570g
all read JSON), so scope this to claims about presentation, layout, or
what a reader sees.

---

## Note on the audit

You reported "items 1 and 2 render correctly" and then established it was
true only because you had called `switchResultsTab` by hand. Correcting
that yourself, rather than letting it stand, is why the audit is worth
acting on — "verified on device" would otherwise have been carried forward
as settled.

Item 3 after this, unchanged.
