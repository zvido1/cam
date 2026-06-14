#!/usr/bin/env python3
"""
build_edgar_corpus.py - EDGAR mini-corpus fetch for CAM external validation.

Fetches 8 executed commercial lease exhibits from SEC EDGAR, normalizes to
plaintext fixtures matching the Albireo pattern (see build_albireo_fixture.py),
and emits a JSON manifest.

Corpus: 8 leases across 7 US jurisdictions -- office (OK, CA, NC), lab/life-science (CA x2, MA),
retail/restaurant NNN (SC), industrial (CO). Mix of populated and absent Landlord's-Work exhibits.

Usage:
    python build_edgar_corpus.py              # build all fixtures + manifest
    python build_edgar_corpus.py --dry-run    # print plan, no writes
    python build_edgar_corpus.py --force      # re-download even if cached

Regenerable and idempotent: re-running on the same cached HTML yields identical fixtures.
Raw HTML is cached in edgar_cache/ (gitignored) so re-runs do not re-hit EDGAR.

SEC fair-access: User-Agent identifies the project; rate-limited to <= 10 req/s (0.15 s delay);
all SEC-filed exhibits are public record per 17 C.F.R. § 232.

Output:
    05 Lease Analyzer/test_data/tenants/<slug>_lease.txt  (one per lease)
    05 Lease Analyzer/test_data/edgar_corpus_manifest.json
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# CORPUS CONFIG TABLE  --  edit here to add/remove leases
# Each entry is the canonical definition of one fixture.
# ---------------------------------------------------------------------------
LEASE_CONFIGS = [
    {
        # 1. Office -- Oklahoma -- ABSENT work scope (As-Is Work Letter, no construction)
        "slug":          "bokf_oklahoma_tower",
        "tenant":        "BOKF, NA (d/b/a Bank of Oklahoma)",
        "landlord":      "One Williams Center Building (Landlord entity not extracted from public filing)",
        "address":       "Bank of Oklahoma Tower, Tulsa, Oklahoma",
        "effective_date": "2019-12-31",     # period of 10-K containing this exhibit
        "property_type": "office",
        "jurisdiction":  "OK",
        "cik":           "875357",
        "accession":     "0000875357-20-000017",
        "exhibit_file":  "a20191231bokfex108.htm",
        "exhibit_label": "EX-10.8",
        "work_scope":    "absent",
        "work_scope_note": ("Exhibit G is titled 'As-Is Work Letter' -- premises delivered in existing "
                            "condition, no Landlord construction. Exhibits C-1 and C-2 (original TI "
                            "schedules) are marked [INTENTIONALLY DELETED] in this filing. "
                            "Functionally: no Landlord's-Work construction obligation."),
        "graphical_note": None,
        "verify_checks": [
            "BOKF",
            "Bank of Oklahoma",
            "Tulsa",
            "As-Is Work Letter",
            "Base Rent",
            "Commencement Date",
        ],
    },
    {
        # 2. Office -- California (Pasadena) -- POPULATED work scope (Exhibit C: Tenant Work Letter)
        "slug":          "everbridge_northlake_pasadena",
        "tenant":        "Everbridge, Inc.",
        "landlord":      "PR 155 North Lake, LLC",
        "address":       "155 North Lake Ave, Suite 900, Pasadena, CA 91101",
        "effective_date": "2018-04-26",
        "property_type": "office",
        "jurisdiction":  "CA",
        "cik":           "1437352",
        "accession":     "0001564590-19-005821",
        "exhibit_file":  "evbg-ex101_778.htm",
        "exhibit_label": "EX-10.1",
        "work_scope":    "populated",
        "work_scope_note": ("Exhibit C is the 'Tenant Work Letter' in which Landlord commits to "
                            "performing construction work for the Tenant. Populated landlord "
                            "construction-scope exhibit."),
        "graphical_note": "Exhibit B (floor plan of Premises) is graphical and may appear as a section header only.",
        "verify_checks": [
            "Everbridge",
            "155 North Lake",
            "Pasadena",
            "Tenant Work Letter",
            "Base Rent",
            "Commencement Date",
        ],
    },
    {
        # 3. Office -- North Carolina -- ABSENT work scope (existing building, no Work Letter found)
        "slug":          "ncino_parkerfarm_wilmington",
        "tenant":        "nCino, Inc.",
        "landlord":      "Cloud Real Estate Holdings, LLC",
        "address":       "6770 Parker Farm Drive, Wilmington, NC 28405",
        "effective_date": "2020-11-29",
        "property_type": "office",
        "jurisdiction":  "NC",
        "cik":           "1566895",
        "accession":     "0001628280-20-016993",
        "exhibit_file":  "existingbuildinglease-.htm",
        "exhibit_label": "EX-10.1",
        "work_scope":    "absent",
        "work_scope_note": ("Full-building lease (89,975 sq ft, 3-story building) for an existing "
                            "building that Landlord is acquiring. No Work Letter or Landlord's-Work "
                            "exhibit identified in the public filing. Lease commences on the date "
                            "Landlord acquires record title. Probably no Landlord construction obligation."),
        "graphical_note": "Exhibit A-1 (premises plan) is graphical.",
        "verify_checks": [
            "nCino",
            "Parker Farm Drive",
            "Wilmington",
            "North Carolina",
            "Basic Rent",
            "Commencement Date",
        ],
    },
    {
        # 4. Lab/Office (life science, existing building) -- California -- POPULATED work scope
        #    (Exhibit C: Landlord's Work -- private office construction)
        "slug":          "atreca_eastjamie_southsf",
        "tenant":        "Atreca, Inc.",
        "landlord":      "ARE-East Jamie Court, LLC (Alexandria Real Estate Equities)",
        "address":       "450 East Jamie Court, South San Francisco, CA",
        "effective_date": "2019-07-17",
        "property_type": "lab/office",
        "jurisdiction":  "CA",
        "cik":           "1532346",
        "accession":     "0001104659-19-041460",
        "exhibit_file":  "a19-13139_1ex10d18.htm",
        "exhibit_label": "EX-10.18",
        "work_scope":    "populated",
        "work_scope_note": ("Exhibit C is 'Landlord's Work' -- describes construction of private offices "
                            "in the Premises pursuant to an attached plan. Populated landlord "
                            "construction-scope exhibit. Companion to EX-10.19 (to-be-constructed "
                            "building at 835 Industrial Road, same transaction)."),
        "graphical_note": "Exhibit A (Premises plan) is graphical and appears as a section header only.",
        "verify_checks": [
            "Atreca",
            "450 East Jamie",
            "South San Francisco",
            "Landlord's Work",
            "Base Rent",
            "Commencement Date",
        ],
    },
    {
        # 5. Lab/Office (life science, to-be-constructed) -- California -- POPULATED work scope
        #    (Exhibit C: Work Letter with TI allowance for to-be-constructed building)
        "slug":          "atreca_industrial_rd_sancarlos",
        "tenant":        "Atreca, Inc.",
        "landlord":      "ARE-San Francisco No. 63, LLC (Alexandria Real Estate Equities)",
        "address":       "835 Industrial Road, San Carlos, CA (6-story building, to be constructed)",
        "effective_date": "2019-07-17",
        "property_type": "lab/office",
        "jurisdiction":  "CA",
        "cik":           "1532346",
        "accession":     "0001104659-19-041460",
        "exhibit_file":  "a19-13139_1ex10d19.htm",
        "exhibit_label": "EX-10.19",
        "work_scope":    "populated",
        "work_scope_note": ("Exhibit C is the 'Work Letter' for a to-be-constructed 6-story building. "
                            "Landlord constructs building shell; tenant improvements constructed by "
                            "Tenant pursuant to the Work Letter and TI Allowance. Companion to "
                            "EX-10.18 (existing building at 450 East Jamie Court, same transaction)."),
        "graphical_note": "Exhibit A (site plan) is graphical and appears as a section header only.",
        "verify_checks": [
            "Atreca",
            "835 Industrial",
            "San Carlos",
            "Work Letter",
            "Base Rent",
            "Commencement Date",
        ],
    },
    {
        # 6. Lab/Office (life science, multi-building) -- Massachusetts -- ABSENT work scope
        #    (Tenant performs its own 'Tenant Work'; Landlord provides TI allowance but no construction)
        "slug":          "quanterix_crosby_bedford",
        "tenant":        "Quanterix Corporation",
        "landlord":      "XChange Owner LLC (c/o Jumbo Capital Incorporated)",
        "address":       "14 Crosby Drive and 18 Crosby Drive, Bedford, MA 01730",
        "effective_date": "2022-01-28",
        "property_type": "lab/office",
        "jurisdiction":  "MA",
        "cik":           "1503274",
        "accession":     "0001104659-22-009514",
        "exhibit_file":  "tm2135533d1_ex10-1.htm",
        "exhibit_label": "EX-10.1",
        "work_scope":    "absent",
        "work_scope_note": ("Commencement dates tied to 'Substantial Completion of Tenant's Work' per "
                            "Section 3.2.1 -- Tenant performs the fit-out, not Landlord. No Landlord's-Work "
                            "construction exhibit. Landlord may provide TI allowance but is not the "
                            "constructing party. Two-building campus lease."),
        "graphical_note": "Exhibit A (floor plans) is graphical.",
        "verify_checks": [
            "Quanterix",
            "Crosby Drive",
            "Bedford",
            "Tenant's Work",
            "Base Rent",
            "Commencement Date",
        ],
    },
    {
        # 7. Retail / QSR restaurant -- South Carolina -- ABSENT work scope
        #    (Absolutely Net lease, tenant responsible for all; no Landlord's Work)
        "slug":          "divall_wendys_mtpleasant",
        "tenant":        "Wendy's franchise operator",
        "landlord":      "DiVall Insured Income Properties 2, Ltd. Partnership",
        "address":       "361 Highway 17 Bypass, Mt. Pleasant, SC",
        "effective_date": "2020-07-27",   # amendment date; original execution date unknown
        "property_type": "retail",
        "jurisdiction":  "SC",
        "cik":           "825788",
        "accession":     "0001493152-20-014064",
        "exhibit_file":  "ex10-1.htm",
        "exhibit_label": "EX-10.1",
        "work_scope":    "absent",
        "work_scope_note": ("'Absolutely Net' (triple-net NNN) restaurant lease. Tenant responsible for "
                            "all maintenance, taxes, and insurance. No Landlord's-Work exhibit. "
                            "Filed as 'Amended and Restated' -- full restated lease text is complete "
                            "and self-contained."),
        "graphical_note": None,
        "verify_checks": [
            "Wendy",
            "Highway 17",
            "Mt. Pleasant",
            "Net Lease",
            "Base Rent",
            "Commencement Date",
        ],
    },
    {
        # 8. Industrial -- Colorado -- ABSENT work scope
        #    (Exhibit D: Tenant Work -- Tenant constructs its own improvements)
        "slug":          "solidpower_thornton_industrial",
        "tenant":        "Solid Power, Inc.",
        "landlord":      "25 North Investors SPE1, LLC",
        "address":       "14902 Grant Street, Suite 140 (Building 2), Thornton, CO 80023",
        "effective_date": "2021-09-01",
        "property_type": "industrial",
        "jurisdiction":  "CO",
        "cik":           "1844862",
        "accession":     "0001104659-21-148821",
        "exhibit_file":  "tm2132574d4_ex10-21.htm",
        "exhibit_label": "EX-10.21",
        "work_scope":    "absent",
        "work_scope_note": ("Exhibit D describes 'Tenant Work' -- Tenant constructs its own improvements "
                            "to the 75,022 sq ft industrial suite. No Landlord's-Work construction. "
                            "Commencement Date is earlier of Tenant completing its Tenant Work or "
                            "January 1, 2022. EV battery manufacturing facility."),
        "graphical_note": "Exhibit A (premises plan) and Exhibit B (land description) are graphical.",
        "verify_checks": [
            "Solid Power",
            "Grant Street",
            "Thornton",
            "Industrial",
            "Base Rent",
            "Commencement Date",
        ],
    },
]

# ---------------------------------------------------------------------------
# EDGAR fetch config
# ---------------------------------------------------------------------------
USER_AGENT = "CAM-research contact@vered.ai"
REQUEST_DELAY = 0.15   # seconds between requests -- stays well under 10 req/s limit
EDGAR_BASE = "https://www.sec.gov"

REPO_ROOT = Path(__file__).parent.parent  # CAM repo root
CACHE_DIR = REPO_ROOT / "05 Lease Analyzer" / "test_data" / "edgar_cache"
FIXTURES_DIR = REPO_ROOT / "05 Lease Analyzer" / "test_data" / "tenants"
MANIFEST_PATH = REPO_ROOT / "05 Lease Analyzer" / "test_data" / "edgar_corpus_manifest.json"

IMPORT_DATE = "2026-06-14"

# ---------------------------------------------------------------------------
# SEC fetch with caching and rate limiting
# ---------------------------------------------------------------------------
def _edgar_get(url: str, force: bool = False) -> bytes:
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.cache"
    if not force and cache_file.exists():
        return cache_file.read_bytes()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    time.sleep(REQUEST_DELAY)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} fetching {url}: {e.reason}") from e
    cache_file.write_bytes(data)
    return data


def build_exhibit_url(cfg: dict) -> str:
    cik_num = str(int(cfg["cik"]))
    acc_clean = cfg["accession"].replace("-", "")
    return f"{EDGAR_BASE}/Archives/edgar/data/{cik_num}/{acc_clean}/{cfg['exhibit_file']}"


# ---------------------------------------------------------------------------
# HTML → text extraction  (same algorithm as build_albireo_fixture.py)
# ---------------------------------------------------------------------------
def extract(html: str) -> str:
    h = html
    h = re.sub(r"(?i)</p>",  "\n", h)
    h = re.sub(r"(?i)</tr>", "\n", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</td>", " \t", h)
    text = re.sub(r"<[^>]+>", " ", h)
    ent = {
        "&nbsp;": " ", "&amp;": "&", "&#160;": " ",
        "&#8220;": '"', "&#8221;": '"', "&#8217;": "'", "&#8216;": "'",
        "&#8211;": "-", "&#8212;": "-", "&#8226;": "*", "&#x2022;": "*",
        "&#x2019;": "'", "&#39;": "'", "&quot;": '"', "&lt;": "<", "&gt;": ">",
        "&#147;": '"', "&#148;": '"', "&#146;": "'", "&#150;": "-",
        "&ldquo;": '"', "&rdquo;": '"', "&lsquo;": "'", "&rsquo;": "'",
        "&ndash;": "-", "&mdash;": "-", "&bull;": "*",
    }
    for k, v in ent.items():
        text = text.replace(k, v)
    text = re.sub(r"&#x?[0-9a-fA-F]+;", " ", text)   # remaining numeric entities
    out = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            out.append(line)
    clean = "\n".join(out)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean


# ---------------------------------------------------------------------------
# Fixture header (matches Albireo convention exactly)
# ---------------------------------------------------------------------------
def build_header(cfg: dict) -> str:
    work_label = "POPULATED" if cfg["work_scope"] == "populated" else "ABSENT"
    lines = [
        f"# SOURCE FIXTURE - {cfg['tenant']} / {cfg['landlord']} {cfg['property_type'].lower()} lease",
        f"# {cfg['address']}. Effective Date {cfg['effective_date']}.",
        f"# Real executed commercial lease, filed as SEC {cfg['exhibit_label']} (source: {cfg['exhibit_file']}).",
        f"# Accession: {cfg['accession']}  CIK: {cfg['cik']}",
        f"# Imported {IMPORT_DATE} for the EDGAR mini-corpus (Tier-1 external validation, CAM NEW_THREAD_PROMPT).",
        f"# Landlord's-Work / Work-Letter: {work_label} -- {cfg['work_scope_note']}",
        "#",
        "# Text extracted from the SEC HTML filing via build_edgar_corpus.py (regenerable).",
    ]
    if cfg.get("graphical_note"):
        lines.append(f"# {cfg['graphical_note']}")
    lines.append("# Page-number artifacts from the filing are left inline.")
    lines.append("# ============================================================================")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Build one fixture: download → extract → header + body
# ---------------------------------------------------------------------------
def build_fixture(cfg: dict, force: bool = False) -> str:
    url = build_exhibit_url(cfg)
    raw_bytes = _edgar_get(url, force=force)
    html = raw_bytes.decode("utf-8", errors="replace")
    body = extract(html)
    header = build_header(cfg)
    return header + body


# ---------------------------------------------------------------------------
# Verify checks
# ---------------------------------------------------------------------------
def verify_fixture(text: str, checks: list[str]) -> dict:
    results = {}
    for c in checks:
        hits = text.lower().count(c.lower())
        results[c] = hits
    return results


# ---------------------------------------------------------------------------
# Stable content hash (SHA-256 of UTF-8 body text, hex)
# ---------------------------------------------------------------------------
def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def write_manifest(entries: list[dict]) -> None:
    manifest = {
        "generated": IMPORT_DATE,
        "description": (
            "EDGAR mini-corpus manifest -- 8 executed commercial leases fetched from SEC EDGAR "
            "for CAM external validation (Tier-1, NEW_THREAD_PROMPT). One row per lease. "
            "Designed as input to cross-lease recall/stability testing. "
            "content_hash: SHA-256 of the fixture text (UTF-8). "
            "work_scope: 'populated' = Landlord's-Work/Work-Letter exhibit with substantive content; "
            "'absent' = no Landlord construction obligation."
        ),
        "leases": entries,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written: {MANIFEST_PATH}  ({len(entries)} leases)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    args = set(sys.argv[1:])
    dry_run = "--dry-run" in args
    force = "--force" in args

    print(f"EDGAR corpus build  ({len(LEASE_CONFIGS)} leases configured)")
    print(f"  dry_run={dry_run}  force_refetch={force}")
    print(f"  fixtures -> {FIXTURES_DIR}")
    print(f"  cache    -> {CACHE_DIR}")
    print(f"  manifest -> {MANIFEST_PATH}")
    print()

    manifest_entries = []
    all_ok = True

    for i, cfg in enumerate(LEASE_CONFIGS, 1):
        slug = cfg["slug"]
        fixture_path = FIXTURES_DIR / f"{slug}_lease.txt"
        exhibit_url = build_exhibit_url(cfg)

        print(f"[{i}/{len(LEASE_CONFIGS)}] {slug}")
        print(f"    {cfg['property_type'].upper()} | {cfg['jurisdiction']} | work={cfg['work_scope']}")
        print(f"    URL: {exhibit_url}")

        if dry_run:
            print("    (dry-run: skipping download)")
            manifest_entries.append({
                "slug":          slug,
                "tenant":        cfg["tenant"],
                "landlord":      cfg["landlord"],
                "address":       cfg["address"],
                "property_type": cfg["property_type"],
                "jurisdiction":  cfg["jurisdiction"],
                "effective_date": cfg["effective_date"],
                "accession":     cfg["accession"],
                "exhibit":       cfg["exhibit_label"],
                "exhibit_file":  cfg["exhibit_file"],
                "cik":           cfg["cik"],
                "work_scope":    cfg["work_scope"],
                "work_scope_note": cfg["work_scope_note"],
                "fixture_path":  str(fixture_path.relative_to(REPO_ROOT)),
                "content_hash":  "(dry-run)",
                "source_url":    exhibit_url,
                "licensing_note": "SEC-filed exhibit; public record per 17 C.F.R. § 232.",
            })
            print()
            continue

        try:
            text = build_fixture(cfg, force=force)
        except Exception as e:
            print(f"    ERROR: {e}")
            all_ok = False
            print()
            continue

        # Verify
        check_results = verify_fixture(text, cfg["verify_checks"])
        missing = [k for k, v in check_results.items() if v == 0]
        if missing:
            print(f"    VERIFICATION WARN -- missing phrases: {missing}")
            all_ok = False
        else:
            print(f"    Verification: OK ({len(check_results)} checks passed)")

        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write(text)

        chars = len(text)
        lines = text.count("\n") + 1
        h = content_hash(text)
        print(f"    Written: {fixture_path.name}  ({chars:,} chars, {lines:,} lines, sha256={h[:16]}...)")

        manifest_entries.append({
            "slug":          slug,
            "tenant":        cfg["tenant"],
            "landlord":      cfg["landlord"],
            "address":       cfg["address"],
            "property_type": cfg["property_type"],
            "jurisdiction":  cfg["jurisdiction"],
            "effective_date": cfg["effective_date"],
            "accession":     cfg["accession"],
            "exhibit":       cfg["exhibit_label"],
            "exhibit_file":  cfg["exhibit_file"],
            "cik":           cfg["cik"],
            "work_scope":    cfg["work_scope"],
            "work_scope_note": cfg["work_scope_note"],
            "fixture_path":  str(fixture_path.relative_to(REPO_ROOT)),
            "content_hash":  h,
            "source_url":    exhibit_url,
            "licensing_note": "SEC-filed exhibit; public record per 17 C.F.R. § 232.",
        })
        print()

    if not dry_run:
        write_manifest(manifest_entries)

    # Summary
    populated = sum(1 for e in manifest_entries if e.get("work_scope") == "populated")
    absent    = sum(1 for e in manifest_entries if e.get("work_scope") == "absent")
    types_seen = sorted(set(e["property_type"] for e in manifest_entries))
    juris_seen = sorted(set(e["jurisdiction"] for e in manifest_entries))
    print("=" * 60)
    print(f"Corpus: {len(manifest_entries)} leases  |  populated={populated}  absent={absent}")
    print(f"Property types: {types_seen}")
    print(f"Jurisdictions:  {juris_seen}")
    if all_ok:
        print("All verification checks PASSED.")
    else:
        print("WARNING: one or more verification checks FAILED (see above).")
        sys.exit(1)


if __name__ == "__main__":
    main()
