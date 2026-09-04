Step 553. Push. Branch only.

Preflight per CLAUDE.md: fetch, unpushed count, every commit touching
"05 Lease Analyzer/" or "cam/", secret scan on the diff, tests against
HEAD.

Confirm the six flags are unchanged from Step 548.

State what changes for a user:
  - GZipMiddleware: 1,450,841 -> 304,955 bytes per page load
  - both shell routes now stamp content-hashed asset URLs
  - asset_version computes on every request, 1.39ms, no cache
  - no-store unchanged; no caching headers added

Push branch only, NOT --follow-tags.

THEN measure the deployed "after": request the page and both static
assets, report Content-Encoding and wire bytes against Step 551's
production baseline of 1,370,065. This is the one figure Step 552 could
not produce.

Also confirm both shell routes stamp in production, and that
/static/index.html is still reachable and unstamped -- recorded, not fixed.
