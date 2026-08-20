"""LP-12 extraction diagnostic. MEASUREMENT ONLY -- extraction stage in isolation.

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

OUT = os.path.join(r"C:\Users\Owner\OneDrive\CAM", "build_log", "LP12_extraction_runs")
LEASE = r"05 Lease Analyzer\test_data\tenants\atlas_meridian_warehouse_lease.txt"
text = open(LEASE, encoding="utf-8").read()
provs = [p for p in PROVISIONS if p.get("default_enabled")]

# Needles unique to Section 13.2 / 13.3 in this lease.
NEEDLES = {
    "Termination Right": 1,
    "replacement value of the Building": 1,
    "Rent Abatement": 1,
}

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
    lp12 = next((p for p in provs_out if p.get("provision_id") == "LP-12"), None)
    txt12 = (lp12 or {}).get("tenant_text") or ""
    rec["lp12_status"] = (lp12 or {}).get("status")
    rec["lp12_len"] = len(txt12)
    rec["lp12_has_13_2"] = "Section 13.2" in txt12
    rec["lp12_has_termination_right"] = "Termination Right" in txt12
    rec["lp12_section_ref"] = (lp12 or {}).get("tenant_section_ref")

    # Where does the 13.2/13.3 text live in THIS run's output?
    found = {}
    for needle in NEEDLES:
        hits = [p.get("provision_id") for p in provs_out
                if needle in (p.get("tenant_text") or "")]
        found[needle] = hits
    rec["needle_locations"] = found
    rec["lp12_empty"] = rec["lp12_len"] == 0
    rec["text_present_somewhere"] = any(found[n] for n in NEEDLES)
    rows.append(rec)
    print("run %d: LP-12 %s len=%d | 'Termination Right' in %s | %s"
          % (i, rec["lp12_status"], rec["lp12_len"],
             found["Termination Right"] or "NOWHERE", rec["model"]), flush=True)

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)
print("\npersisted to build_log/LP12_extraction_runs/", flush=True)
