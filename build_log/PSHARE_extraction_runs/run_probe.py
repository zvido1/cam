"""Proportionate Share (22.4%) cross-filing diagnostic. MEASUREMENT ONLY -- extraction stage in isolation.

Six runs on the Atlas fixture. Full extraction output persisted per run so the
observations are re-examinable; the earlier LP-12 observations are unrecoverable
because nothing kept them.

Changes nothing. No fix, no prompt change, no deploy.
"""
import os, sys, json, time
sys.path.insert(0, r"C:\Users\Owner\OneDrive\CAM")
for line in open(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env", encoding="utf-8"):
    k, _, v = line.strip().partition("=")
    if k.strip().endswith("_API_KEY"):
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc
from cam.adapters.lease_review.lease_provision_taxonomy import PROVISIONS

OUT = os.path.join(r"C:\Users\Owner\OneDrive\CAM", "build_log", "PSHARE_extraction_runs")
LEASE = r"05 Lease Analyzer\test_data\tenants\atlas_meridian_warehouse_lease.txt"
text = open(LEASE, encoding="utf-8").read()
provs = [p for p in PROVISIONS if p.get("default_enabled")]

# Needles unique to the Proportionate Share DEFINITION clause (line 22), verified by
# occurrence count against the lease before use. "Proportionate Share" itself is NOT used:
# it occurs 3x (definition + Sections 3.2 and 3.3), so a hit would not prove provenance.
NEEDLES = {
    "shall mean 22.4%": 1,
    "ratio of the rentable area": 1,
    "total rentable area of the Building": 1,
}
# 421C names this pair: Tenant's Share -> LP-07 relevance, Rent Adjustment Percentage ->
# LP-02 relevance. LP-00 is recorded there as a sink for key-terms/definition content.
TRACKED = ["LP-07", "LP-02", "LP-01", "LP-00"]

rows = []
for i in range(1, 7):
    rec = {"run": i, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    t0 = time.time()
    try:
        res = extract_provisions_single_doc(text, provs, {}, canonical=True)
    except Exception as e:
        rec.update({"outcome": "EXTRACTION_ERROR", "error": str(e)[:300],
                    "elapsed": round(time.time() - t0, 1)})
        rows.append(rec)
        print("run %d: EXTRACTION_ERROR %s" % (i, str(e)[:120]), flush=True)
        continue
    rec["elapsed"] = round(time.time() - t0, 1)
    meta = res.get("meta", {}) or {}
    rec["model"] = meta.get("model")
    rec["provider"] = meta.get("provider")
    rec["fallback_used"] = meta.get("fallback_used")
    rec["primary_model"] = meta.get("primary_model")

    with open(os.path.join(OUT, "run_%02d_full.json" % i), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    provs_out = res.get("provisions", [])
    per_lp = {}
    for lp in TRACKED:
        e = next((p for p in provs_out if p.get("provision_id") == lp), None)
        t = (e or {}).get("tenant_text") or ""
        per_lp[lp] = {
            "status": (e or {}).get("status"),
            "len": len(t),
            "section_ref": (e or {}).get("tenant_section_ref"),
            "has_2240": "22.4" in t,
            "needles": [n for n in NEEDLES if n in t],
        }
    rec["per_lp"] = per_lp

    # Where does the 13.2/13.3 text live in THIS run's output?
    found = {}
    for needle in NEEDLES:
        hits = [p.get("provision_id") for p in provs_out
                if needle in (p.get("tenant_text") or "")]
        found[needle] = hits
    rec["needle_locations"] = found
    rec["definition_present_somewhere"] = any(found[n] for n in NEEDLES)
    rec["all_lps_carrying_22_4"] = [p.get("provision_id") for p in provs_out
                                    if "22.4" in (p.get("tenant_text") or "")]
    rows.append(rec)
    print("run %d: def-clause in %s | 22.4%% in %s | LP-07 len=%d LP-02 len=%d | %s"
          % (i, found["shall mean 22.4%"] or "NOWHERE",
             rec["all_lps_carrying_22_4"] or "NOWHERE",
             per_lp["LP-07"]["len"], per_lp["LP-02"]["len"], rec["model"]), flush=True)

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)
print("\npersisted to build_log/PSHARE_extraction_runs/", flush=True)
