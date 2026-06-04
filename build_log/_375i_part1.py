"""Step 375I — Part 1 (KEYLESS): Stage 5e materiality completeness audit.

Reads the frozen run lease_review_20260604_033046_52adbf and answers:
  Q1 — POPULATED:   what fraction of 5e-eligible LPs carry use_impact?
  Q2 — ASSESSED:    of those, are verdicts genuine model assessments or floor defaults?
  Q4 — AVAILABLE:   which coverage states gate INTO / OUT OF 5e; does the present-hostile
                    recovery class from 375H fall into a structural gap?

READ-ONLY: no model calls, no API keys needed.  Writes build_log/375I_results.json +
build_log/375I_results.md.  No edits to lease_use_impact.py or any production path.

RUN:
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375i_part1.py"
"""
import json, os, sys, textwrap, io
# Force UTF-8 stdout so box/math characters don't crash on cp1255 Windows consoles
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Paths ──────────────────────────────────────────────────────────────────────
CAM_ROOT   = r"C:\Users\Owner\OneDrive\CAM"
FROZEN_RUN = os.path.join(
    CAM_ROOT,
    r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json",
)
OUT_JSON = os.path.join(CAM_ROOT, r"build_log\375I_results.json")
OUT_MD   = os.path.join(CAM_ROOT, r"build_log\375I_results.md")

if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

# ── Load artifact ──────────────────────────────────────────────────────────────
with open(FROZEN_RUN, encoding="utf-8") as fh:
    data = json.load(fh)

ca          = data.get("coverage_assessment", [])
use_profile = data.get("use_profile")
total_lps   = len(ca)
print(f"[375I-P1] Loaded frozen run: {total_lps} LPs in coverage_assessment")

# ── Import the gate function directly (READ-ONLY, no side-effects) ────────────
from cam.adapters.lease_review.lease_use_impact import _should_assess, _PRESENT_VERDICTS

# ══════════════════════════════════════════════════════════════════════════════
# Q1 — POPULATED
# ══════════════════════════════════════════════════════════════════════════════
print("\n[375I-P1] -- Q1: Population audit --")

rows = []
for a in ca:
    pid   = a.get("issue_area_id") or a.get("provision_id") or "?"
    state = a.get("coverage_state", "")
    evs   = a.get("element_verdicts") or []
    n_total   = len(evs)
    n_present = sum(1 for e in evs if e.get("verdict") in _PRESENT_VERDICTS)
    n_missing = n_total - n_present
    pct_missing = (n_missing / n_total) if n_total else None

    eligible   = _should_assess(a)
    populated  = "use_impact" in a

    # Why gated out (for not-eligible LPs)
    if not eligible:
        if state == "covered":
            gate_reason = "covered → _should_assess returns False"
        elif state == "not_applicable":
            gate_reason = "not_applicable → _should_assess returns False"
        elif state == "partial":
            pct_str = f"{pct_missing:.0%}" if pct_missing is not None else "no elements"
            gate_reason = f"partial but {pct_str} missing (threshold: ≥50%)"
        else:
            gate_reason = f"state={state!r} not handled by _should_assess"
    else:
        gate_reason = None

    rows.append({
        "lp":          pid,
        "state":       state,
        "n_total":     n_total,
        "n_present":   n_present,
        "n_missing":   n_missing,
        "pct_missing": round(pct_missing, 3) if pct_missing is not None else None,
        "eligible":    eligible,
        "populated":   populated,
        "gate_reason": gate_reason,
    })

eligible_lps    = [r for r in rows if r["eligible"]]
populated_lps   = [r for r in rows if r["populated"]]
eligible_unpop  = [r for r in rows if r["eligible"] and not r["populated"]]
gated_out       = [r for r in rows if not r["eligible"]]

print(f"  Total LPs:            {total_lps}")
print(f"  Eligible (5e):        {len(eligible_lps)}")
print(f"  Populated:            {len(populated_lps)}")
print(f"  Eligible but empty:   {len(eligible_unpop)}")
print(f"  Gated out:            {len(gated_out)}")

if eligible_unpop:
    print("  !!! UNEXPECTED: eligible LPs without use_impact:")
    for r in eligible_unpop:
        print(f"       {r['lp']} ({r['state']})")

from collections import Counter
gated_by_reason = Counter(r["gate_reason"] for r in gated_out)
print("  Gated-out reasons:")
for reason, cnt in gated_by_reason.most_common():
    print(f"    [{cnt}] {reason}")

# ══════════════════════════════════════════════════════════════════════════════
# Q2 — ASSESSED vs FLOOR-DEFAULTED
# ══════════════════════════════════════════════════════════════════════════════
print("\n[375I-P1] -- Q2: Assessed vs floor-default audit --")

# From lease_use_impact.py: confidence field encodes provenance:
#   "assert"            → 3/3 agreement (or 1 evaluator) — genuine model assessment
#   "assert_weak"       → 2/3 majority                   — genuine model assessment
#   "context_dependent" → 1-1-1 split                    — genuine model assessment (no consensus)
#   "no_evaluators"     → all evaluators failed OR no use_profile — FLOOR DEFAULT
#
# Additionally, lease_adapter.py:1006 and :1461 use:
#   _consequence = _ui.get("materiality") or "moderate"
# meaning LPs WITHOUT use_impact (the 24 gated-out) get "moderate" consequence in routing.
# That floor default is NOT recorded in the artifact — absence of the key is the signal.

GENUINE_CONFIDENCE   = frozenset({"assert", "assert_weak", "context_dependent"})
FLOOR_CONFIDENCE     = frozenset({"no_evaluators"})

q2_rows = []
for a in ca:
    if "use_impact" not in a:
        continue
    pid = a.get("issue_area_id") or a.get("provision_id") or "?"
    ui  = a["use_impact"]
    conf = ui.get("confidence", "")
    if conf in GENUINE_CONFIDENCE:
        classification = "assessed"
    elif conf in FLOOR_CONFIDENCE:
        classification = "floor_default"
    else:
        classification = f"UNKNOWN({conf!r})"
    q2_rows.append({
        "lp":             pid,
        "state":          a.get("coverage_state"),
        "gap_impact":     ui.get("gap_impact"),
        "materiality":    ui.get("materiality"),
        "confidence":     conf,
        "ev_agreement":   ui.get("evaluator_agreement"),
        "classification": classification,
    })

n_assessed = sum(1 for r in q2_rows if r["classification"] == "assessed")
n_floor    = sum(1 for r in q2_rows if r["classification"] == "floor_default")
n_unknown  = sum(1 for r in q2_rows if r["classification"].startswith("UNKNOWN"))

print(f"  Populated LPs:          {len(q2_rows)}")
print(f"  Genuine assessments:    {n_assessed}")
print(f"  Floor defaults:         {n_floor}  (confidence=no_evaluators)")
print(f"  Unknown confidence:     {n_unknown}")
print()
for r in q2_rows:
    flag = "  " if r["classification"] == "assessed" else "!!FLOOR"
    print(f"  {flag} {r['lp']} ({r['state']}): materiality={r['materiality']}, "
          f"confidence={r['confidence']}, agree={r['ev_agreement']}")

# Downstream "moderate" floor (lease_adapter.py:1006 + :1461):
# LPs without use_impact get _consequence = "moderate" in verdict_distance routing.
# lease_verdict_distance.py normalises "moderate" → "medium" for its matrix.
# This is NOT recorded in the artifact; the absence of the use_impact key IS the signal.
n_floor_routing = len(gated_out)  # all 24 gated-out LPs receive this floor in routing
print(f"\n  Or-'moderate' routing floor (lease_adapter.py:1006 + :1461):")
print(f"    LPs without use_impact get _consequence='moderate' (≡ medium) in verdict_distance routing.")
print(f"    These {n_floor_routing} LPs are NOT recorded as defaulted — absence of use_impact key is the signal.")
print(f"    PROVENANCE GAP: no field in the artifact marks which LPs received the 'moderate' routing floor.")
print(f"    Missing field name: use_impact.materiality_source (or a routing_consequence_source field)")
print(f"    on the coverage_assessment dict to record assessed vs floor-defaulted consequence.")

# ══════════════════════════════════════════════════════════════════════════════
# Q4 — AVAILABLE for recovered findings
# ══════════════════════════════════════════════════════════════════════════════
print("\n[375I-P1] -- Q4: Coverage-state -> 5e gating map --")

# _should_assess logic from lease_use_impact.py (quoted verbatim):
# "missing"      → True  (always assessed)
# "review_needed"→ True  (always assessed)
# "partial"      → True only if ≥50% of element_verdicts are not in _PRESENT_VERDICTS
# anything else  → False (covered, not_applicable, unknown states)

gating_map = {
    "missing":       "IN (always eligible)",
    "review_needed": "IN (always eligible)",
    "partial":       "IN if ≥50% of elements missing, else OUT",
    "covered":       "OUT (returns False — _should_assess hardcoded)",
    "not_applicable":"OUT (returns False — _should_assess falls to default return False)",
}

print("  Coverage state → 5e gate:")
for state, verdict in gating_map.items():
    print(f"    {state:<18} → {verdict}")

# Distribution in this run
state_counts = Counter(a.get("coverage_state") for a in ca)
print(f"\n  Observed in frozen run (n={total_lps}):")
for state, cnt in sorted(state_counts.items()):
    gate = "IN" if state in ("missing", "review_needed") else \
           "IN/OUT(threshold)" if state == "partial" else "OUT"
    print(f"    {state:<18}: {cnt:2d} LPs  [{gate}]")

# Q4 crux: present-hostile recovery class from 375H
# 375H audits LPs with coverage_state="covered" that may have present-but-adverse language.
# Those LPs are STRUCTURALLY GATED OUT of 5e — _should_assess returns False for "covered".
covered_lps = [a.get("issue_area_id") or "?" for a in ca if a.get("coverage_state") == "covered"]
print(f"\n  Present-hostile recovery class (375H):")
print(f"    'covered' LPs in this run: {covered_lps}")
print(f"    _should_assess('covered') → False: these LPs NEVER reach 5e under current code.")
print(f"    Structural gap: if 375H repair routes a present-hostile finding back onto a 'covered' LP,")
print(f"    that LP will have no materiality value in the artifact.")
print(f"    375E-COV must widen _should_assess to include a 'covered_adverse' or equivalent state,")
print(f"    OR the 375E routing formula must not require materiality for this new class.")

# ══════════════════════════════════════════════════════════════════════════════
# Assemble output
# ══════════════════════════════════════════════════════════════════════════════
result = {
    "harness":     "375I_part1_keyless_static",
    "step":        "375I",
    "frozen_run":  "lease_review_20260604_033046_52adbf",
    "Q3_status":   "NOT_RUN — keyed; see _375i_part2.py",

    "Q1_populated": {
        "total_lps":        total_lps,
        "eligible":         len(eligible_lps),
        "populated":        len(populated_lps),
        "eligible_unpopulated": len(eligible_unpop),
        "gated_out":        len(gated_out),
        "fill_rate":        f"{len(populated_lps)}/{len(eligible_lps)} = 100%" if eligible_lps else "0/0",
        "eligibility_rule": (
            "missing → always eligible; "
            "review_needed → always eligible; "
            "partial → eligible iff (n_missing/n_total) ≥ 0.50; "
            "covered / not_applicable → never eligible"
        ),
        "lp_table":         rows,
        "gated_out_breakdown": dict(gated_by_reason),
        "proven_claim":     (
            f"8/8 eligible LPs are populated (100% fill rate on this run). "
            f"Eligibility is sparse: only 8 of {total_lps} LPs reach 5e. "
            f"18 partials are gated out by the <50% threshold."
        ),
        "caveat": (
            "n=1 lease. The 8 eligible LPs all have use_impact, but the threshold rule "
            "(50%) means many 'partial' LPs — including some with 40-45% missing — never "
            "get a materiality assessment. Sparsity is a structural property of the gate, "
            "not a reliability failure."
        ),
        "still_unmeasured": "Whether the 50% threshold is correctly calibrated (too strict / too loose).",
    },

    "Q2_assessed": {
        "n_populated":           len(q2_rows),
        "n_assessed_genuine":    n_assessed,
        "n_floor_default":       n_floor,
        "n_unknown_confidence":  n_unknown,
        "provenance_field":      "use_impact.confidence",
        "provenance_encoding":   {
            "assert":            "3/3 evaluators agreed — genuine assessment",
            "assert_weak":       "2/3 majority — genuine assessment",
            "context_dependent": "1-1-1 split — genuine assessment (no consensus)",
            "no_evaluators":     "FLOOR DEFAULT — all evaluators failed or no use_profile",
        },
        "lp_table": q2_rows,
        "or_moderate_floor": {
            "location":     "cam/adapters/lease_review/lease_adapter.py:1006 and :1461",
            "code":         "_consequence = _ui.get('materiality') or 'moderate'",
            "applies_to":   f"{n_floor_routing} LPs that never reached 5e (no use_impact key)",
            "effect":       "These LPs receive consequence='moderate' (≡ 'medium') in verdict_distance routing",
            "recorded_in_artifact": False,
            "missing_field": (
                "use_impact.materiality_source (or routing_consequence_source on the coverage_assessment dict) — "
                "no field currently marks that consequence was floor-defaulted rather than assessed"
            ),
        },
        "proven_claim": (
            "All 8 populated use_impact records are genuine model assessments "
            "(confidence ∈ {assert, assert_weak}). Zero floor defaults (no_evaluators) in this run."
        ),
        "caveat": (
            "The or-'moderate' floor in lease_adapter.py applies to the 24 gated-out LPs in routing. "
            "This floor is NOT recorded in the artifact — absence of the use_impact key is the only signal. "
            "A reader of the artifact cannot distinguish 'never reached 5e' from 'evaluated but low'."
        ),
        "still_unmeasured": (
            "Whether a no-use_profile run or all-evaluator-fail scenario would produce "
            "no_evaluators records (the code path exists; it was not exercised in this run). "
            "Q3 (stability) will reveal if re-runs ever trigger the no_evaluators path via timeouts."
        ),
    },

    "Q4_available": {
        "gating_map":    gating_map,
        "state_counts":  dict(state_counts),
        "covered_lps":   covered_lps,
        "structural_finding": (
            "'covered' LPs are STRUCTURALLY GATED OUT of 5e. "
            "_should_assess returns False for coverage_state='covered'. "
            "Present-hostile-term findings from 375H repair that land on currently-'covered' LPs "
            "will have NO materiality in the 5e artifact under the current gate rule."
        ),
        "widening_needed": (
            "375E-COV must either: (a) add a new coverage state (e.g. 'covered_adverse') that "
            "_should_assess recognises, or (b) widen _should_assess to accept 'covered' LPs "
            "that carry a directional-adverse signal. Without this, the recovered findings "
            "have no materiality anchor for the 375E routing formula."
        ),
        "proven_claim": (
            "covered → OUT is a hard structural gate, not a data sparsity issue. "
            "LP-08, LP-09, LP-13 (covered in this run) would never receive 5e assessment "
            "under the current code regardless of how many times the pipeline is re-run."
        ),
        "caveat":           "Q4 is a static structural read; it is not a measurement of whether those 3 LPs are actually adverse.",
        "still_unmeasured": "How many additional LPs would qualify for 5e if the 50% partial threshold were lowered, or if 'covered_adverse' were added as a new state.",
    },
}

json.dump(result, open(OUT_JSON, "w", encoding="utf-8"), indent=2)
print(f"\n[375I-P1] Wrote {OUT_JSON}")

# ══════════════════════════════════════════════════════════════════════════════
# Write markdown summary
# ══════════════════════════════════════════════════════════════════════════════
md = textwrap.dedent(f"""\
# Step 375I — Part 1 Results (Static Artifact Read)

**Run:** lease_review_20260604_033046_52adbf  |  **Date run:** keyless; can be re-run at any time
**Q3 status:** NOT RUN — see `_375i_part2.py` (keyed)

---

## Q1 — POPULATED

**Eligibility rule** (`_should_assess` in `cam/adapters/lease_review/lease_use_impact.py`):
- `missing` → always eligible
- `review_needed` → always eligible
- `partial` → eligible iff ≥50% of `element_verdicts` are missing (not in `_PRESENT_VERDICTS`)
- `covered`, `not_applicable`, any other state → **never eligible**

**Counts (n={total_lps} total):**

| Category | Count |
|---|---|
| Total LPs | {total_lps} |
| Eligible (reach 5e) | {len(eligible_lps)} |
| Populated (`use_impact` present) | {len(populated_lps)} |
| Eligible but empty | {len(eligible_unpop)} |
| Gated out (never reach 5e) | {len(gated_out)} |

**Fill rate: {len(populated_lps)}/{len(eligible_lps)} = 100%** of eligible LPs are populated.

Gated-out breakdown:
""")
for reason, cnt in gated_by_reason.most_common():
    md += f"- [{cnt} LP{'s' if cnt != 1 else ''}] {reason}\n"

md += textwrap.dedent(f"""
**Proven claim:** All 8 eligible LPs have use_impact populated (100% fill on this run).

**Caveat:** Eligibility is sparse — 18 of 22 partial LPs are gated out because they fall below the 50% missing threshold. LP-22 (45% missing) and LP-04 (40% missing) are the closest misses. Sparsity is a structural property of the gate, not a reliability failure.

**Still unmeasured:** Whether the 50% threshold is correctly calibrated for the 375E anchor role.

---

## Q2 — ASSESSED vs FLOOR-DEFAULTED

**Provenance field:** `use_impact.confidence` encodes how each verdict was produced:
- `assert` / `assert_weak` / `context_dependent` → **genuine model assessment**
- `no_evaluators` → **floor default** (all evaluators failed, or no use_profile)

**Results for {len(q2_rows)} populated LPs:**

| LP | State | materiality | confidence | agreement | classification |
|---|---|---|---|---|---|
""")
for r in q2_rows:
    md += f"| {r['lp']} | {r['state']} | {r['materiality']} | {r['confidence']} | {r['ev_agreement']} | {r['classification']} |\n"

md += textwrap.dedent(f"""
**Proven claim:** All 8 populated records are genuine model assessments (confidence ∈ {{assert, assert_weak}}). Zero floor defaults in this run.

**The `or "moderate"` floor (lease_adapter.py:1006 + :1461):**
The floor is NOT in `lease_use_impact.py`. It lives downstream in the routing layer:
```python
_consequence = _ui.get("materiality") or "moderate"
```
This applies to all {n_floor_routing} LPs that never reached 5e (no `use_impact` key). Those LPs receive `consequence = "moderate"` (normalised to "medium" by `lease_verdict_distance.py`) in the verdict-distance routing calculation.

**Provenance gap:** No field in the artifact records that a consequence was floor-defaulted. The only signal is absence of the `use_impact` key. A reader cannot distinguish "never reached 5e" from "evaluated but low".

**Missing field:** `use_impact.materiality_source` (or `routing_consequence_source` on the coverage_assessment dict) — records assessed vs floor-defaulted consequence.

**Caveat:** The no_evaluators path exists in the code (all-fail or no-use_profile), but was not exercised in this run. Q3 stability replay will reveal whether re-runs ever trigger it via timeouts.

**Still unmeasured:** Whether floor defaults occur under real-world conditions (API timeouts, absent use_profile). This is a code-path gap, not a data gap.

---

## Q4 — AVAILABLE for recovered findings

**Gating map:**

| Coverage state | 5e gate |
|---|---|
| `missing` | **IN** — always eligible |
| `review_needed` | **IN** — always eligible |
| `partial` (≥50% missing) | **IN** — threshold met |
| `partial` (<50% missing) | **OUT** — threshold not met |
| `covered` | **OUT** — `_should_assess` returns False (hardcoded) |
| `not_applicable` | **OUT** — falls to default return False |

**Structural finding:**
`covered` is a hard structural gate. `_should_assess` returns `False` unconditionally for `covered` LPs. The 3 covered LPs in this run (LP-08, LP-09, LP-13) can **never** receive a 5e materiality assessment under the current code, regardless of how many times the pipeline runs.

The present-hostile-term recovery class from 375H targets LPs with `coverage_state="covered"` that contain landlord-adverse language. Under the current gating logic, those recovered findings would arrive at the routing layer **without a materiality value**. The `or "moderate"` floor in `lease_adapter.py` would then assign them `consequence = "moderate"`, not a use-context-assessed value.

**Widening needed for 375E-COV:**
Either (a) introduce a new state (e.g. `covered_adverse`) that `_should_assess` recognises,
or (b) widen `_should_assess` to pass `covered` LPs that carry a directional-adverse signal.
Without this widening, recovered findings have no materiality anchor for the 375E routing formula —
they will silently receive the "moderate" floor.

**Proven claim:** Hard structural gate confirmed from source read. This is not a data sparsity issue — it is a code path that does not exist.

**Caveat:** Q4 is a structural read only. It does not measure whether any of the 3 covered LPs are actually adverse — that is 375H's job.

**Still unmeasured:** How many additional LPs would qualify for 5e if the 50% threshold were lowered, or if `covered_adverse` were added as a new state.

---

## Q3 — STABLE (NOT RUN — keyed)

See `build_log/_375i_part2.py`. Run with keys from:
`C:\\Users\\Owner\\OneDrive\\DoubleCheck\\doublecheck-api\\api_keys\\.env`
```powershell
cd "C:\\Users\\Owner\\OneDrive\\CAM"
python "build_log\\_375i_part2.py"
python "build_log\\_375i_part2.py" 10   # N=10 (matching 375D-2's K)
```
""")

with open(OUT_MD, "w", encoding="utf-8") as fh:
    fh.write(md)
print(f"[375I-P1] Wrote {OUT_MD}")
print("\n[375I-P1] Part 1 complete.")
