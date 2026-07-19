# Step 430 — Chat Instruction: Gate B cross-lease measurement (Atreca + Atlas), read-only, no wiring

**Author:** Chat instance
**Date:** 2026-07-19
**Builder model:** Sonnet 5, HIGH reasoning
**Provenance:** Written verbatim to `build_log/430_chat_instruction.md` before any code (CLAUDE.md Rule 7). Sanctioned instruction; do not deviate without a new written instruction.

---

## Part 0 — Instruction provenance (do this first)

This file must exist on disk, committed, before any code. Claude Code: confirm it is present and read it in full before writing the harness. If not present, STOP and report — do not reconstruct from memory.

---

## What this step is, in one sentence

Run the 427/429 parameter block through its declared Gate B on **both** the Atreca lease (where it was built) and the Atlas lease (which it has **never** seen), as a **read-only measurement**, and report — per lease, per parameter — whether Gate B passes, and for every unsatisfied dependency whether the parameter is **absent-by-structure** (genuinely not in that lease in the declared form) or **present-but-missed** (a real recall/resolution failure).

## What this step is NOT

- **Not wiring.** Do NOT modify `lease_coverage.py`, `lease_adapter.py`, or any live pipeline file. 423 spec §8/§13: no wiring until Gates A–D pass together on both leases. This step measures Gate B only; Gate A is not formally passed and the spec's Gate C (panel selection) does not exist yet.
- **Not a fix.** If Atlas fails Gate B, that may be **correct behavior**, not a bug. Do NOT change the dependency map, `PARAMETER_TARGETS`, the prompt, the resolver, or `enforce_gate_b` to make Atlas green. The failure structure IS the finding.
- **Not a new baseline.** This is a two-lease diagnostic. It does not establish system performance.

---

## Context Code needs (verified against the real files this session)

**The two fixtures (both confirmed present):**
- Atreca: `05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt`
- Atlas: `05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt`

There is **no "Atlas" in the EDGAR corpus manifest** — Atlas is the synthetic warehouse fixture from the earlier directional arc, not an EDGAR lease. Both leases live in `test_data/tenants/`. Use these two files.

**Confirmed structural difference (this is why the harness must classify failures, not just pass/fail):**

Atreca's four declared parameters sit as discrete labeled lines in a header block (verified by direct read this session):
- `Tenant's Share of Operating Expenses of Building: 100%`
- `Building's Share of Project: 45.79%`
- `Rent Adjustment Percentage: 3%`
- `Base Rent: $3.75 per rentable square foot of the Premises per month...`

Atlas has **no such block** (verified by direct read this session). Its nearest equivalents:
- No "Tenant's Share of Operating Expenses" and no "Building's Share" at all. The only proportional figure is `"Proportionate Share" shall mean 22.4%` (in the §1.2 definitions block), used for Real Estate Taxes and CAM — a different concept from Atreca's operating-expense split. **Expect `tenant_share` and `building_share` to be unsatisfiable on Atlas as declared — absent-by-structure, not a bug.**
- `base_rent` present but as a **5-year escalation schedule** ("$18.50 per rentable square foot per annum" for Year 1, then Years 2–5), plus a §1.2 stub definition (`"Base Rent" shall mean the annual rent payable as set forth in Section 3.1`). Multiple plausible spans; may resolve, may resolve to a different span than Atreca-style.
- `rent_adjustment_pct` present but **implicit**: `"The above schedule reflects an annual escalation of approximately 3% per annum."` Stated as a descriptive aside under the rent table, not a labeled parameter.

**Real function signatures (verified against the real modules this session — call them exactly):**

- `from cam.adapters.lease_review.lease_parser import parse_document` → `parse_document(path: str) -> str` (raw canonical text).
- `from cam.adapters.lease_review.lease_evidence_spans import build_canonical_source, NORMALIZATION_PROFILE_V2`
  → `build_canonical_source(tenant_text: str, source_type="lease_tenant_document", run_id="", normalization_profile=NORMALIZATION_PROFILE_V2) -> CanonicalSource`. **Use `NORMALIZATION_PROFILE_V2`** — that is the profile 426/427/428/429 used (page-number-line stripping). Do not use v1.
- `from cam.adapters.lease_review.lease_parameter_block import extract_parameters, attach_parameters_to_lp_evidence, check_gate_b, enforce_gate_b, DEPENDENCY_MAP, PARAMETER_NAMES, PARAMETER_TARGETS`
  → `extract_parameters(canonical_source, canonical=True) -> {"parameters": {name: Parameter}, "meta": {...}}`
  → `check_gate_b(parameters, lp_ids=None, dependency_map=None) -> [{"lp_id","dependency","gate_status"}]` (pure, no raise — **use this for the pass/fail table**)
  → `attach_parameters_to_lp_evidence(parameters, lp_id, dependency_map=None) -> [Parameter]`
  → `enforce_gate_b(parameters, canonical=False, ...)` — **call in `canonical=False` (report) mode** so Atlas misses are reported, not aborted on first failure. (In `canonical=True` it raises `GateAbortError` on the first unsatisfied dependency, which would hide the full Atlas failure structure — that is the wrong mode for a measurement.)
- `Parameter` has `.name`, `.span` (an `EvidenceSpan` with `.verification_status`, `.start_char`, `.end_char`, `.span_text`), `.provenance`.

**API keys:** standalone harness must `load_dotenv(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env")` at the top before any model call (elicitation calls the live model). A fresh shell does NOT inherit the server's env; skipping this yields all-empty results that look like a recall failure but are a setup failure.

**PYTHONPATH:** run with `PYTHONPATH` set to the CAM root (`C:\Users\Owner\OneDrive\CAM`) so `cam.adapters...` imports resolve, same as prior harnesses.

---

## The harness (what to build)

A standalone diagnostic script, e.g. `build_log/run_430_gate_b_cross_lease.py`. Read-only: it imports the parameter block and substrate and calls them; it modifies no source module. Per lease (Atreca, then Atlas):

1. `parse_document(fixture_path)` → raw text.
2. `build_canonical_source(raw_text, run_id="430-<slug>", normalization_profile=NORMALIZATION_PROFILE_V2)`.
3. `extract_parameters(canonical_source, canonical=True)` → parameters + meta. Capture `meta`'s `prompt_hash` / `config_hash` (config-integrity — confirm Atreca's still match 427/428/429; Atlas's prompt/config hashes should equal Atreca's since prompt/config don't vary by lease).
4. `check_gate_b(parameters)` → per-(LP, dependency) pass/fail records for LP-02 and LP-07.
5. For each parameter (all four), record: resolved? (in `parameters` dict with a `verified` span), and if resolved: `param_name`, span offsets `[start,end)`, span text, elicited target label. If NOT resolved: mark unresolved and run the classification below.
6. `enforce_gate_b(parameters, canonical=False)` → capture the degraded report (gate_status + failures list) as the overall per-lease verdict. Do NOT call it in canonical mode.

**Stability, not single-shot.** Run steps 2–6 **N=5** per lease (same N-floor discipline as 426/428; a one-shot Atlas result can't distinguish absent-by-structure from an intermittent recall miss). Report per-parameter resolution rate across the 5 runs (e.g. `base_rent 5/5`, `building_share 0/5`), and offset stability for anything that resolves. Config hashes must be identical across all 5 runs of a lease (assert and report).

### The classification that is the whole point (step 5, unresolved case)

For every parameter that does NOT resolve to a verified span, the harness must classify the miss into exactly one of:

- **`absent_by_structure`** — the declared concept does not appear in this lease's text in a form the parameter targets. Evidence for this classification: a deterministic, code-side substring probe of the raw canonical text for the parameter's own declared `element_label` and `synonyms` (from `PARAMETER_TARGETS`) finds **no** occurrence. (E.g. Atlas has no "Tenant's Share of Operating Expenses" / "Building's Share" substring at all.) This is a fact about the document, decided by code, not a model judgment.
- **`present_but_missed`** — the declared concept's label/synonym **does** occur in the raw text (code-side substring hit), but elicitation+resolution failed to produce a verified span for it. This is the genuine-defect bucket — it would mean 429's fix did not hold on a second lease, or the resolver failed on this lease's phrasing.
- **`present_variant`** — a softer sub-case of the above, optional but useful: the concept is present under a **different** label than declared (e.g. Atlas's "Proportionate Share" 22.4% is arguably the tenant-share analogue but is not "Tenant's Share of Operating Expenses"). If the harness can cheaply detect a near-label via a small declared alias probe, tag it `present_variant`; otherwise fold into `absent_by_structure` and note the alias in prose. Do NOT build fuzzy matching for this — a short hardcoded alias list in the harness only (never in the source module) is acceptable, clearly marked as harness-side diagnostic scaffolding.

The classification probe is **harness-side only** — it must not touch or import decision logic from the source modules beyond reading `PARAMETER_TARGETS` for the labels/synonyms. It exists to make the report legible, not to change any gate.

---

## Do-NOT list

- Do NOT modify any file under `cam/` — this is read-only measurement. The only file written is the harness under `build_log/` and the report.
- Do NOT edit the dependency map, `PARAMETER_TARGETS`, the prompt, the schema, the resolver, or `enforce_gate_b` to make Atlas pass. Atlas failure is a finding, not a bug to fix here.
- Do NOT call `enforce_gate_b` in canonical mode (it aborts on first failure and hides the Atlas failure structure).
- Do NOT wire anything into the live pipeline. Do NOT touch `cam/core/`.
- Do NOT build fuzzy/semantic matching for the classification. Substring probe on declared labels/synonyms + an explicit harness-side alias list is the ceiling.
- Do NOT treat a single run as sufficient — N=5 per lease.
- Do NOT characterize either lease's content from priors — every content claim in the report needs a verbatim quote + offset from that run's canonical source (Rule 6).
- Do NOT push. Explicit-path staging with `git add -f`.

---

## Required outputs

**Report:** `build_log/430_gate_b_cross_lease.md`, containing:
1. **Headline verdict, per lease:** Gate B pass/fail, and if fail, which (LP, dependency) pairs failed.
2. **Per-lease, per-parameter table** (N=5): resolution rate, offset stability, span text (verbatim, quoted) for resolved params, and for unresolved params the classification (`absent_by_structure` / `present_but_missed` / `present_variant`) with the code-side substring-probe evidence that justifies it.
3. **Config-integrity:** prompt_hash / config_hash per lease, confirmation they match 427/428/429 and are stable across the 5 runs.
4. **The interpretation, stated plainly and separately** (do not compress): Atreca result; Atlas result; and — if Atlas fails on `tenant_share`/`building_share` as absent-by-structure — the explicit statement that **Gate B is functioning correctly and the finding is that the dependency map is Atreca-shaped and does not transfer unchanged to a differently-structured (warehouse, single-proportionate-share) lease.** Distinguish this sharply from any `present_but_missed` result, which WOULD be a 429-regression and must be flagged loudly.
5. **What this does and does not close:** if Atreca passes and Atlas's only failures are absent-by-structure, state that Gate B is validated as a *mechanism* on both leases (it correctly certifies Atreca and correctly refuses Atlas), but that Gate B is NOT "passed on both leases" in the §8 sense, because §8 requires the dependency to be *satisfied* — so wiring remains blocked, now with a named reason: the dependency map needs a per-document-type story (see design question below).
6. **Design question surfaced, not answered:** whether the dependency map (423 spec §5.2) should be **global** or **per-document-type** (the §9 NOT_APPLICABLE contract is the natural home for "this lease type doesn't declare this dependency"). Record it as an open decision for a follow-on; do not resolve it in 430.

**Do NOT re-run or reinterpret** if Atlas fails — capture it faithfully and report it. A loud, correct Atlas failure is a successful step.

---

## Git (explicit-path staging, no push)

```
git add -f build_log/430_chat_instruction.md
git add -f build_log/430_gate_b_cross_lease.py
git add -f build_log/430_gate_b_cross_lease.md
git add -f build_log/430_gate_b_cross_lease_sidecar.json   # if the harness emits one
git status   # confirm nothing unintended staged; no results/ dirs, no .tmp.driveupload
git commit -m "430: Gate B cross-lease measurement (Atreca + Atlas) — read-only, no wiring; dependency-map transfer finding"
```

No `git add .` / `git add -A`. No push. No `cam/` file should appear in `git status` as modified — if one does, STOP and report (something was touched that shouldn't have been).

---

## Copy-paste prompt for Claude Code

> Read `build_log/430_chat_instruction.md` in full before doing anything; it is the sanctioned instruction for this step (CLAUDE.md Rule 7). Confirm it is present on disk — if not, STOP and report.
>
> This is a READ-ONLY measurement. Do NOT modify any file under `cam/`. Do NOT wire anything into the live pipeline. Do NOT change the dependency map, PARAMETER_TARGETS, the prompt, the resolver, or enforce_gate_b to make any lease pass — a Gate B failure on Atlas may be correct behavior and is itself the finding.
>
> Build a standalone harness `build_log/run_430_gate_b_cross_lease.py` that, for BOTH `05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt` and `05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt`, runs N=5: `parse_document` → `build_canonical_source(..., normalization_profile=NORMALIZATION_PROFILE_V2)` → `extract_parameters(canonical=True)` → `check_gate_b` → `enforce_gate_b(canonical=False)` (report mode, NOT canonical/abort mode). `load_dotenv(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env")` at the top; set PYTHONPATH to the CAM root.
>
> For every parameter that does NOT resolve to a verified span, classify the miss — harness-side only, using a code substring probe of the raw canonical text against that parameter's own declared `element_label`/`synonyms` from `PARAMETER_TARGETS` — into `absent_by_structure` (label/synonym not present in the text at all), `present_but_missed` (label/synonym present but no verified span — this is the genuine-defect bucket, flag loudly), or `present_variant` (present under a different declared alias; a short hardcoded harness-side alias list is OK, no fuzzy matching).
>
> Write `build_log/430_gate_b_cross_lease.md` with: per-lease Gate B verdict; per-lease per-parameter table (resolution rate over 5 runs, offset stability, verbatim span text + offsets for resolved, classification + probe evidence for unresolved); config-integrity hashes (confirm they match 427/428/429 and are stable across the 5 runs); and a plain, separated interpretation. If Atreca passes and Atlas fails only on `tenant_share`/`building_share` as absent_by_structure, state explicitly that Gate B is working correctly and the finding is that the dependency map is Atreca-shaped and does not transfer unchanged to the warehouse lease — and that this is distinct from any `present_but_missed` result, which would be a 429 regression. Surface (do not answer) the open design question of whether the dependency map should be global or per-document-type. Do NOT re-run or massage a failing Atlas result — capture it faithfully.
>
> Stage with explicit paths and `git add -f` (never `git add .`/`-A`); confirm no `cam/` file shows as modified in `git status` (if one does, STOP and report); commit with the 430 message; do NOT push. Reasoning effort: HIGH.
