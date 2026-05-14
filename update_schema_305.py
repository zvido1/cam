"""
One-shot script: update retail_lease_knowledge.json to schema v2.0.0.
Adds expected_elements_305 to 5 pilot LPs + step_305_pilot_lps + version bump.
Run from CAM root: python update_schema_305.py
"""
import json
from pathlib import Path

SCHEMA_PATH = Path("cam/adapters/lease_review/schemas/retail_lease_knowledge.json")
PILOT_DIR = Path("Docs")

# ── Load main schema ──────────────────────────────────────────────────────────
with open(SCHEMA_PATH, encoding="utf-8") as f:
    schema = json.load(f)

# ── Load pilot element arrays ─────────────────────────────────────────────────
pilot_elements = {}
for lp_id in ["LP-09", "LP-11", "LP-22", "LP-26", "LP-27"]:
    pilot_path = PILOT_DIR / f"Step_305_Schema_Pilot_{lp_id}.json"
    with open(pilot_path, encoding="utf-8") as f:
        pilot = json.load(f)
    pilot_elements[lp_id] = pilot["expected_elements"]
    print(f"  {lp_id}: {len(pilot['expected_elements'])} pilot elements loaded")

# ── LP-11 additions from build instruction ────────────────────────────────────
lp11_additions = [
    {
        "element_id": "LP-11.abandonment_default",
        "element_label": "Abandonment or vacating as event of default",
        "must_be_explicit": False,
        "explicit_drafting_preferred": False,
        "default_law_covers": False,
        "default_law_jurisdiction_dependent": None,
        "synonyms": [
            "abandonment of the Premises",
            "vacating the Premises without commercially reasonable security",
            "Tenant abandons or vacates",
            "if Tenant ceases to occupy the Premises"
        ],
        "implicit_coverage_acceptable": False,
        "cross_LP_coverage": None,
        "absence_severity": "medium",
        "absence_adverse_to": "landlord",
        "review_notes": (
            "Explicitly named in AIR CRE Section 13.1. Absence means landlord has no specific "
            "contractual trigger for abandonment scenarios. Lower severity than monetary/non-monetary "
            "default definitions because abandonment can often be captured under the general "
            "non-monetary default category."
        )
    },
    {
        "element_id": "LP-11.diligent_pursuit_extension",
        "element_label": "Extension of non-monetary cure period when cure is being diligently pursued",
        "must_be_explicit": False,
        "explicit_drafting_preferred": True,
        "default_law_covers": False,
        "default_law_jurisdiction_dependent": None,
        "synonyms": [
            "such longer period as may be reasonably necessary provided Tenant has commenced cure",
            "if cure cannot be completed within thirty days, Tenant shall have additional time",
            "diligently pursuing cure to completion",
            "commenced and is diligently pursuing"
        ],
        "implicit_coverage_acceptable": False,
        "cross_LP_coverage": None,
        "absence_severity": "high",
        "absence_adverse_to": "tenant",
        "review_notes": (
            "AIR CRE Section 13.1(e) explicitly. Confirmed by California Lawyers Association and "
            "Baker Burton Lundy practitioner analyses. Without this, tenant can be defaulted for "
            "good-faith cure that takes longer than 30 days. Separate from cure_period_non_monetary "
            "because they receive different verdicts: cure period present + extension absent is a "
            "materially different state than both present."
        )
    },
    {
        "element_id": "LP-11.mortgagee_guarantor_cure_right",
        "element_label": "Third-party (mortgagee or guarantor) cure right on tenant default",
        "must_be_explicit": False,
        "explicit_drafting_preferred": False,
        "default_law_covers": False,
        "default_law_jurisdiction_dependent": None,
        "synonyms": [
            "mortgagee may cure on behalf of Tenant",
            "guarantor may cure",
            "third party cure right",
            "Tenant's lender shall have the right to cure",
            "Landlord shall give simultaneous notice to Tenant's mortgagee"
        ],
        "implicit_coverage_acceptable": False,
        "cross_LP_coverage": ["LP-22"],
        "absence_severity": "low",
        "absence_adverse_to": "tenant",
        "review_notes": (
            "Common in institutional leases with SNDA. Cross-LP coverage to LP-22 is legitimate "
            "when the SNDA itself grants mortgagee cure rights. Lower severity because it is not "
            "present in all leases and its absence does not fundamentally weaken the default framework."
        )
    },
]

pilot_elements["LP-11"] = pilot_elements["LP-11"] + lp11_additions
print(f"  LP-11: +3 elements from build instruction -> {len(pilot_elements['LP-11'])} total")

# ── Apply to schema ───────────────────────────────────────────────────────────
pilot_lp_ids = list(pilot_elements.keys())
for area in schema.get("issue_areas", []):
    pid = area.get("id", "")
    if pid in pilot_elements:
        area["expected_elements_305"] = pilot_elements[pid]
        print(f"  Added expected_elements_305 to {pid}: {len(pilot_elements[pid])} elements")

# ── Add top-level pilot LP list ───────────────────────────────────────────────
schema["step_305_pilot_lps"] = pilot_lp_ids
print(f"  Added step_305_pilot_lps: {pilot_lp_ids}")

# ── Bump schema version ───────────────────────────────────────────────────────
old_version = schema.get("schema_version")
schema["schema_version"] = "2.0.0"
schema["updated"] = "2026-05-11"

# ── Add notes entry ───────────────────────────────────────────────────────────
notes = schema.get("notes", [])
if isinstance(notes, list):
    notes.append(
        "v2.0.0 (2026-05-11): Step 305 per-element coverage governance. Added "
        "expected_elements_305 arrays to 5 pilot LPs (LP-09: 12, LP-11: 17, LP-22: 11, "
        "LP-26: 7, LP-27: 10 elements). Added step_305_pilot_lps list. Feature gated "
        "behind STEP_305_ENABLED=False in lease_coverage_305.py. Existing expected_elements "
        "fields unchanged for backward compatibility."
    )
    schema["notes"] = notes

# ── Write back ────────────────────────────────────────────────────────────────
with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"\nSchema updated: {old_version} -> 2.0.0")
print(f"Written to {SCHEMA_PATH}")

# ── Verify ────────────────────────────────────────────────────────────────────
with open(SCHEMA_PATH, encoding="utf-8") as f:
    verify = json.load(f)
assert verify["schema_version"] == "2.0.0"
assert verify.get("step_305_pilot_lps") == pilot_lp_ids
for pid in pilot_lp_ids:
    area = next(a for a in verify["issue_areas"] if a["id"] == pid)
    assert "expected_elements_305" in area, f"Missing expected_elements_305 on {pid}"
    print(f"  ✓ {pid}: {len(area['expected_elements_305'])} elements in schema")
print("Verification passed.")
