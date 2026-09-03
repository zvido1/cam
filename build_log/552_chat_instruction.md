Step 552. Compress, then close the Step-550 gaps. No caching change.

Per Step 551: gzip saves 1,053 KB on every load including the first;
caching saves the remaining 292 KB on repeat loads only, against a failure
mode that pins a user to a broken build. no-store stays.

1. Add GZipMiddleware. Report wire bytes before and after, measured
   against the deployed service, not computed.

2. serve_results_page does not stamp. Fix it. Report every shell route
   that serves the app and confirm each stamps -- Step 550 patched one of
   two and reported it as covering the page.

3. An INDEPENDENT hash-binding test. The Step-550 test computes the
   expected value from asset_version, the same function the stamper
   called, so a wrong-but-self-consistent hash passes. Compute the
   expected hash independently -- read the file, hash it in the test, and
   assert the served URL carries that value.

   Verify by exercise the way Step 551 did: stamp with a deliberately
   wrong but self-consistent hash and confirm the NEW test fails where the
   old one passed.

4. Re-key the asset_version cache. (mtime_ns, size) returns a stale hash
   when content changes without either moving. Propose the key and say
   what it costs -- content hashing on every request is correct and not
   free.

5. Record in CLAUDE.md that the index.html version literals are now
   decorative and hand-bumping has no effect. The standing instruction is
   obsolete and will mislead the next author.

Do NOT remove no-store. Do NOT add caching headers.
