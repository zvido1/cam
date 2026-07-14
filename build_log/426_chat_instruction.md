Claude Code — Step 426: recall re-measurement under `canonical_v2`

Part 0 (mandatory, CLAUDE.md Rule 7): write this brief verbatim to `build_log/426_chat_instruction.md` before any other work.

Purpose

Step 425 stripped page-number lines from the canonical text and the LP-07 exclusions-list quote resolved in an n=1, single-LP smoke run. That is a plumbing result, not a recall result. The 0/5 finding it appears to answer came from a 5-run, 32-LP measurement; a one-LP smoke run is not its counterpart and cannot be treated as one.

426 reruns exactly the 424 protocol under `canonical_v2` and produces a before/after on the same instrument.

Method — identical to 424, one variable changed

* N = 5 runs, all 32 LPs, 160 calls. Same source, same prompt, same declared config.
* The only change is `normalization_profile=canonical_whitespace_v2`. Nothing else. If you find yourself wanting to adjust the prompt, the schema, or the resolver because of what you see: don't. That is a later, separately authorized step.
* Config-integrity assertion (Step 416 class): assert identical `prompt_hash` and `config_hash` across all 160 calls, `canonical=True`, `fallback_used=False`. If they drift, the measurement is void — say so and stop.
* Same 12 predefined targets as 424. Do not add, remove, or redefine them. The point is comparability.

A target counts as HIT only if a `verified` span's offsets contain the target text. Offsets, or it didn't happen.

And — this is not optional — verify the matched text. 424 produced a false positive: the locator reported 5/5 on the exclusions list by landing inside the adjacent inclusions span, which merely ends with the words "excluding only:". Code caught it manually and corrected the headline against its own interest. Do that again. For every target scored HIT, print the matched span's actual text and confirm it is the target. A locator that reports a hit is a claim, and claims get checked.

The three questions this must answer

1. Did the exclusions list recover, and how completely? 0/5 → 5/5 is a different result from 0/5 → 3/5. Report the number.
2. Did the parser-artifact failures actually clear? 424 categorized 166 unverified spans: 52 page-number, 33 space-before-punctuation, 48 ellipsis-elision, 7 quote-padding, 26 residual. Re-categorize under v2 and produce the delta. The 48 ellipsis failures should be entirely untouched — the model eliding text with `"..."` is a model behavior, not a parser artifact, and no page-number strip can fix it. If that class shrank, something is wrong with the categorization and I want to know.
3. Did anything REGRESS? Every offset in the document shifted, by however many page-lines precede it. A span that verified under v1 may now fail. This is the question I care most about, it is the one nothing currently checks, and it is exactly the shape of bug this project keeps finding. Diff the per-target table against 424's. Name any target that went from HIT to MISS. If none did, say so explicitly — a clean negative is a finding.

Report — `build_log/426_recall_remeasurement_canonical_v2.md`

* Config-integrity assertion result
* Per-run stats (spans, verified / ambiguous / unverified, dedup ratio)
* Per-target table with a 424 column and a 426 column, side by side. This is the headline.
* Offset stability — do targets resolve to consistent offsets across the 5 runs?
* Unverified-span categorization, with the delta from 424
* A REGRESSIONS section. Empty is an acceptable and valuable answer; absent is not.
* The open `(` question from 425: `_V2_TOLERANT_CHARS` includes `)` but not `(`. Say in one sentence whether that asymmetry is deliberate and whether anything in the corpus depends on it.

Required statements:

This measures recall on ONE document under `canonical_v2`. It does not validate the architecture and does not measure recall on unseen documents.

425 and 426 do not make LP-07 see the 100% tenant share. The parameter block, dependency map, and selector panel remain unbuilt.

Do not

Change the prompt, schema, resolver, or normalization profile. Build the parameter block, dependency map, or selector panel. Wire anything into Stage 5. Run a baseline. Touch `cam/core/`, evaluator identities, Stage 5 stabilization, or Priority Exposure. Push.

Commit: `426 recall remeasurement under canonical_v2` — explicit paths, `git add -f` for `build_log/`.

Why this and not the parameter block. The parameter block's job is to guarantee a declared parameter's verified span reaches its dependent LP. Building it on a substrate whose recall you haven't remeasured means you won't know whether a future gate failure is the gate working or the substrate leaking. Measure the ground before you build on it — which has been the discipline all along, and it's the one that's caught every real finding in this project, including two of mine today.
