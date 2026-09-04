Step 558. Push. Branch only.

Preflight per CLAUDE.md: fetch, unpushed count, every commit touching
"05 Lease Analyzer/" or "cam/", secret scan, tests against HEAD.

Confirm the six flags unchanged.

State what changes for a user:
  - the narrowed _RESERVED_PATTERN: 55 false positives eliminated, 0 true
    positives lost
  - negative-space signals now pass to the panel as evidence rather than
    short-circuiting it, where prose exists beside the placeholder
  - 15 of 38 placeholders corpus-wide now reach the panel; 23 still
    short-circuit
  - solidpower LP-29 stops asserting a landlord entry right the lease
    denies

State what does NOT change: genuine absences still short-circuit, the
pattern still detects all 38 true placeholders, no schema string hedged.

Push branch only, NOT --follow-tags.

Then ONE deployed solidpower run. LP-29 is the case -- confirm the fix
holds in production, and report its verdict, headline and materiality.
