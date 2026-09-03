Step 550. Make the cache-bust automatic. It failed twice unnoticed.

app.js?v=474 was six weeks stale — Steps 522 and 539 both changed frontend
rendering without bumping it. A returning user would have seen the old
summary against new data. Caught only by requesting the deployed page.

A discipline that requires someone to remember is one that fails silently.

1. Report every place a version query string is hand-maintained — app.js,
   style.css, anything else. How many are there and when was each last
   bumped against when its file last changed?

2. Propose making it automatic. Options include the file's content hash,
   the git SHA already available as GIT_SHA, or build-time generation.
   Defend the choice — GIT_SHA changes on every deploy including ones that
   touch nothing frontend, which busts caches unnecessarily but is
   simple; a content hash busts only on real change but needs computing.

3. If a hand-maintained string survives anywhere, propose a test that
   fails when a frontend file changes and its version does not. A test is
   the only thing that makes this discipline non-optional.

4. Verify by exercise: change a frontend file, confirm the version moves
   or the test fails. Do not verify by reading.

Do NOT deploy.
