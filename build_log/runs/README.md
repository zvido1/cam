# build_log/runs/ — persisted local run results

Written by `build_log/_harness/run_store.py`. One directory per harness
invocation: `<step>_<label>_<UTC stamp>/`.

    run_NN_full.json      the full pipeline result, verbatim
    run_NN_census.json    provenance census computed at write time
    index.json            per-run metadata, git HEAD, and the flag snapshot

**These are run artifacts. Do not commit them.** `build_log/` is gitignored, so
they stay local unless someone force-adds them; do not. Commit the harness and
the status file that cites the numbers, not the payloads — an Atlas Mode C
result is ~1 MB.

The harness itself IS committed: `build_log/_harness/` is force-added, the same
way status files are.

## Why this exists

Step 489 found that no completed local coverage run from Steps 457-484 survived
on disk, so those steps' fallback censuses cannot be re-verified. Step 463
recorded the same loss earlier. Persistence is now the default and has no off
switch — see the module docstring.
