"""Step 464: is the attractor set stable, and does pinning decoding collapse it?

DIAGNOSTIC ONLY. Changes no repo file and no deployed configuration. The pinned
arm injects top_p/top_k by wrapping the Google SDK entry point IN THIS PROCESS
ONLY -- lease_extract.py and provider_router.py are untouched.

Arm 1 (unpinned): 6 runs, exactly the Step-463 harness.
Arm 2 (pinned):   6 runs, identical except top_p=0.0, top_k=1 added to the config.
Prompt, schema, model, temperature and max_output_tokens are identical in both.
"""
import os, sys, json, time
sys.path.insert(0, r"C:\Users\Owner\OneDrive\CAM")
for line in open(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env", encoding="utf-8"):
    k, _, v = line.strip().partition("=")
    if k.strip().endswith("_API_KEY"):
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc
from cam.adapters.lease_review.lease_provision_taxonomy import PROVISIONS
import google.genai.models as gm

BASE = os.path.join(r"C:\Users\Owner\OneDrive\CAM", "build_log", "464_shape_runs")
LEASE = r"05 Lease Analyzer\test_data\tenants\atlas_meridian_warehouse_lease.txt"
text = open(LEASE, encoding="utf-8").read()
provs = [p for p in PROVISIONS if p.get("default_enabled")]

_orig = gm.Models.generate_content_stream
_transmitted = []

def _pinned(self, *, model, contents, config=None, **kw):
    cfg = dict(config) if isinstance(config, dict) else config
    if isinstance(cfg, dict):
        cfg["top_p"] = 0.0
        cfg["top_k"] = 1
    _transmitted.append({k: v for k, v in cfg.items() if k in ("temperature", "top_p", "top_k")}
                        if isinstance(cfg, dict) else None)
    return _orig(self, model=model, contents=contents, config=cfg, **kw)

def _unpinned(self, *, model, contents, config=None, **kw):
    _transmitted.append({k: v for k, v in config.items() if k in ("temperature", "top_p", "top_k")}
                        if isinstance(config, dict) else None)
    return _orig(self, model=model, contents=contents, config=config, **kw)

for arm, patch in (("unpinned", _unpinned), ("pinned", _pinned)):
    out = os.path.join(BASE, arm)
    os.makedirs(out, exist_ok=True)
    gm.Models.generate_content_stream = patch
    print("\n" + "=" * 70, flush=True)
    print("ARM: %s" % arm, flush=True)
    for i in range(1, 7):
        _transmitted.clear()
        t0 = time.time()
        try:
            res = extract_provisions_single_doc(text, provs, {}, canonical=True)
        except Exception as e:
            print("  %s run %d: ERROR %s: %s" % (arm, i, type(e).__name__, str(e)[:140]), flush=True)
            continue
        el = round(time.time() - t0, 1)
        json.dump(res, open(os.path.join(out, "run_%02d.json" % i), "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        pm = {p["provision_id"]: p for p in res["provisions"]}
        lp12 = len(pm.get("LP-12", {}).get("tenant_text") or "")
        lp00 = len(pm.get("LP-00", {}).get("tenant_text") or "")
        tot = sum(len(p.get("tenant_text") or "") for p in res["provisions"])
        print("  %s run %d: %.1fs LP-12=%-4d LP-00=%-5d total=%-6d fallback=%s cfg=%s"
              % (arm, i, el, lp12, lp00, tot, (res.get("meta") or {}).get("fallback_used"),
                 _transmitted[0] if _transmitted else None), flush=True)
gm.Models.generate_content_stream = _orig
print("\nDONE", flush=True)
