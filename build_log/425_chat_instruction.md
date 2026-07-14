Claude Code — Step 425: canonical source normalization v2

Part 0 (mandatory, per CLAUDE.md Rule 7): write this brief verbatim to `build_log/425_chat_instruction.md` before doing anything else.

The diagnosis

Step 424 measured segmentation recall, N=5, 32 LPs, 160 calls. The verified-span substrate behaved correctly throughout. The canonical source text is dirty, and 92 of 166 unverified spans (55%) trace to typographic artifacts in `lease_parser.parse_document()` output — not to model error and not to resolver error.

The worst case: the Operating Expense exclusions list, items (a)–(u) — the single most material tenant protection in LP-07 — was 0/5. Never captured, in any run. The model quoted it faithfully every time. The quote crossed an inline page-number line (`"...renovation;\n4\n(b) capital expenditures..."`) and the resolver correctly refused, because a digit is not whitespace.

The resolver was right. The source was wrong. That `4` is a page number from the SEC filing. The fixture header says so explicitly: "Page-number artifacts from the filing are left inline."

The governing principle — read before writing any code

Strip what is not in the document. Never rewrite what is.

This is the line that separates a fix from a corruption, and it must not be crossed:

* Page-number lines are not lease content. They are filing furniture. Removing them makes the canonical text more faithful to the lease. → Strip from canonical text.
* Ugly spacing IS lease content. `" Assignment Termination "`, `"Section 22 , Tenant"` — those characters are genuinely in the document we were given. Rewriting them to match what the model said is editing the evidence to fit the claim, which is precisely what this architecture exists to prevent. → Leave the text alone. Loosen the declared matching rule instead.

If you find yourself editing canonical text so that a model's quote will match, stop. That is the failure, not the fix.

Task

1. Strip bare page-number lines from canonical text (`canonical_v2`).

Remove lines consisting solely of digits, optionally whitespace-padded: `\n4\n`, `\n 12 \n`.

Must NOT remove: `Section 4`, `4. Operating Expenses`, `(4)`, `4%`, `$4`, `4 days`, `Page 4 of 20`, or any digit adjacent to non-whitespace on its own line. Keep the rule as narrow as it can possibly be. A false strip is worse than a missed one.

Preserve `raw_source_text` and `raw_source_text_hash` alongside. `canonical_v2` changes the canonical text hash and invalidates all prior span offsets by design — that is the substrate working, not breaking.

2. Extend the matching profile to `canonical_whitespace_v2` — do NOT touch the text.

Declared tolerance, in the profile, tested:

* whitespace-run equivalence (already in v1)
* space adjacent to punctuation (`word ;` ≡ `word;`)
* padding immediately inside quote marks (`" Term "` ≡ `"Term"`)

Every non-whitespace, non-punctuation-adjacent character must still match literally. A digit is never whitespace. `45.79%` can never match `45.80%`. No fuzzy matching, no edit distance, no paraphrase. Ever.

3. Provenance. Record `normalization_profile`, `raw_source_text_hash`, `canonical_text_hash`, and transformation counts (page-lines stripped, etc.) as diagnostic metadata only — never as validation.

Do NOT

Weaken the resolver. Treat digits as whitespace. Add fuzzy matching. Rewrite substantive text. Build the parameter block, dependency map, selector panel, or many-to-many assignment. Feed spans into Stage 5. Run a baseline. Touch `cam/core/`, evaluator identities, Stage 5 stabilization, or Priority Exposure. Push.

Tests

* Page-number line stripped; exclusions-list quote now resolves (this is the fixture that matters — build it from the real `renovation;\n4\n(b)` text)
* `Section 4`, `4%`, `$4`, `(4)`, `4 days` all survive
* Space-before-punctuation and quote-padding tolerated in matching, with canonical text unchanged (assert the text is byte-identical to raw except for stripped page lines)
* `45.79%` vs `45.80%` → still UNVERIFIED. Non-negotiable.
* Hash drift: a span resolved against v1 canonical is invalid against v2
* Full regression green

Smoke run (n=1, quarantined)

One run on Atreca under `canonical_v2`. Required disclaimer, verbatim:

This is an n=1 plumbing smoke test. It is not a measurement of recall, not evidence the architecture works, and no count from it may be cited as validation.

Report whether the exclusions list resolves. As an observation, not a checklist, not a hit rate.

Report — `build_log/425_canonical_source_normalization_v2.md`

Include the artifact class, why the resolver was right to reject, the strip/tolerate split and why, tests executed with output, and this section:

The canonical-source layer is a known-weak seam. Today's parser flattens a structured SEC HTML filing into a character stream, discarding markup in which page breaks and footers were unambiguous — and we now infer them back from character patterns. The page-number strip is a narrow, testable rule that removes content provably not in the lease. It is not a general solution to document parsing. A structure-aware parser (reading the HTML as HTML) is a real future step, not a hypothetical one. This is recorded now so it is not rediscovered as a surprise on the next document.

Plus: this does not make LP-07 see the 100%. Parameter block, dependency map, and selector panel remain unbuilt.

Commit: `425 canonical source normalization v2` — explicit paths, `git add -f` for `build_log/`, no push.
