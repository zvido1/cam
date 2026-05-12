"""Parse Step_305_Full_Schema_Enhancement.md and merge 27 LP element arrays
into retail_lease_knowledge.json. Also removes the per-LP gate in lease_coverage.py."""

import json, re, pathlib

DOC = pathlib.Path("Docs/Step_305_Full_Schema_Enhancement.md").read_text(encoding="utf-8")
SCHEMA_PATH = pathlib.Path("cam/adapters/lease_review/schemas/retail_lease_knowledge.json")
schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

# ── 1. Parse LP element arrays from the doc ──────────────────────────────────
# Each LP section heading is "## LP-XX: Name"
# Followed by a ```json [...] ``` block

lp_elements = {}
lp_sections = list(re.finditer(r"^## (LP-\d+)", DOC, re.MULTILINE))

for i, m in enumerate(lp_sections):
    lp_id = m.group(1)
    # Section body ends at next ## heading
    section_end = lp_sections[i + 1].start() if i + 1 < len(lp_sections) else len(DOC)
    section_body = DOC[m.end():section_end]
    # Find ```json block
    bm = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", section_body)
    if not bm:
        print(f"WARNING: No JSON block for {lp_id}")
        continue
    try:
        elements = json.loads(bm.group(1))
        lp_elements[lp_id] = elements
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse failure for {lp_id}: {e}")

print(f"Parsed {len(lp_elements)} LP sections with "
      f"{sum(len(v) for v in lp_elements.values())} total elements")

# ── 2. Merge into schema ──────────────────────────────────────────────────────
merged = 0
skipped_existing = 0
not_found = []

for area in schema["issue_areas"]:
    pid = area.get("id")
    if pid in lp_elements:
        if "expected_elements_305" in area:
            skipped_existing += 1
            print(f"  SKIP {pid}: already has expected_elements_305")
        else:
            area["expected_elements_305"] = lp_elements[pid]
            merged += 1
            print(f"  ADD  {pid}: {len(lp_elements[pid])} elements")

for lp_id in lp_elements:
    if not any(a.get("id") == lp_id for a in schema["issue_areas"]):
        not_found.append(lp_id)

print(f"\nMerged: {merged} LPs  |  Skipped (already had data): {skipped_existing}  |  Not found: {not_found}")

# ── 3. Update schema version and pilot_lps flag ───────────────────────────────
schema["schema_version"] = "2.1.0"
schema["updated"] = "2026-05-12"
# All 32 LPs now have elements; remove the pilot-only flag (or update it)
schema["step_305_pilot_lps"] = sorted(
    [a["id"] for a in schema["issue_areas"] if "expected_elements_305" in a]
)
print(f"\nstep_305_pilot_lps now covers {len(schema['step_305_pilot_lps'])} LPs")
print("Schema version:", schema["schema_version"])

# ── 4. Write schema ───────────────────────────────────────────────────────────
SCHEMA_PATH.write_text(
    json.dumps(schema, indent=2, ensure_ascii=False),
    encoding="utf-8"
)
print(f"\nWrote {SCHEMA_PATH}")
