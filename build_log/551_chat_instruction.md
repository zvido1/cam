Step 551. Remove no-store? DESIGN, no build.

Step 550 made content-hash versioning trustworthy and enforced by test.
NoCacheStaticFiles' no-store has been in place since March and costs
1.25 MB per page load. Its justification was that ?v= could not be relied
on; that is no longer true.

1. What does NoCacheStaticFiles cover, exactly? Every static asset, or
   only .js and .css? Report anything served through it that is NOT
   content-hashed and would go stale if caching were enabled.

2. Propose the replacement headers and defend them. Content-hashed assets
   can be cached aggressively; index.html itself must not be, since it
   carries the hashes. State the split.

3. What breaks if a hash is wrong? Under no-store a bad hash is harmless.
   Under caching it serves a stale asset until the URL changes. Report
   what the Step-550 test does and does not guarantee -- it asserts the
   version moves when bytes change; does anything assert the hash MATCHES
   the served bytes?

4. Measure the benefit rather than asserting it. 1.25 MB per page load,
   but how often does a user load the page? A lawyer running one lease
   loads it once; the saving may be smaller than it looks.

Do NOT build. Report the design and whether it is worth doing.
