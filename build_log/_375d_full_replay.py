"""Step 375D — Harness A: full-pipeline frozen-input Stage-7 replay (>=5x).

Freezes the PRE-Stage-7 input (full_tenant_text + coverage_assessment + conflicts) from ONE validated
current-code run (0604: lease_review_20260604_033046_52adbf) and replays ONLY run_synthesis against that
identical frozen input N times. Upstream coverage/extraction is NOT re-run. Calls the REAL pipeline code
path (cam.adapters.lease_review.lease_synthesis.run_synthesis). READ-ONLY w.r.t. production: writes only
build_log/375D_full_replay.json; changes no code/output/prompt/severity/routing.

RUN (on the keyed machine):
    cd "C:\\Users\\Owner\\OneDrive\\CAM"
    python "build_log\\_375d_full_replay.py"            # default 5 passes
    python "build_log\\_375d_full_replay.py" 8          # optional: N passes

Cost: N full Stage-7 runs (Pass-1 x3 + Pass-2 x3 + compound + consolidation per pass).
"""
import os, sys, json
from collections import Counter

# ── Keys (proven pattern from _step370c_headless.py) ──
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
try:
    for line in open(KEYS_ENV, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() in WANTED:
            os.environ[k.strip()] = v.strip().strip('"').strip("'")
except FileNotFoundError:
    print(f"[375D-A] WARNING: keys file not found at {KEYS_ENV} — provider calls will fail.", flush=True)
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

FROZEN_RUN = r"05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json"
OUT = r"build_log\375D_full_replay.json"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5

from cam.adapters.lease_review.lease_synthesis import run_synthesis

src = json.load(open(os.path.join(CAM_ROOT, FROZEN_RUN), encoding="utf-8"))
full_tenant_text    = src["full_tenant_text"]
coverage_assessment = src["coverage_assessment"]
conflicts           = src.get("conflicts", []) or []
perspective         = "tenant"
print(f"[375D-A] frozen input: tenant_text_len={len(full_tenant_text)} "
      f"coverage_assessment={len(coverage_assessment)} conflicts={len(conflicts)} | passes={N}", flush=True)


def _agree_first(a):
    try:
        return int((a or "0-0").split("-")[0] or 0)
    except Exception:
        return 0


passes = []
for i in range(1, N + 1):
    print(f"\n[375D-A] ===== PASS {i}/{N} — calling run_synthesis (real Stage 7) =====", flush=True)
    try:
        result = run_synthesis(full_tenant_text, coverage_assessment, conflicts, perspective, cfg={})
    except Exception as e:
        passes.append({"pass": i, "error": repr(e)})
        print(f"[375D-A] PASS {i} ERROR: {e!r}", flush=True)
        continue
    cpf = result.get("cross_provision_findings", []) or []
    meta = result.get("meta", {}) or {}
    direc = [f for f in cpf if f.get("finding_type") == "directional_mismatch"]
    comp  = [f for f in cpf if f.get("finding_type") == "compound_risk"]
    sev_dir = Counter((f.get("severity") or "?") for f in direc)
    # 3-0 directional = Risk-routed (ASSERT_SIGNAL). verification_incomplete is its own distinct state.
    risk_30 = sorted("|".join(sorted(f.get("implicated_lps") or [])) for f in direc
                     if _agree_first(f.get("evaluator_agreement")) >= 3 and not f.get("verification_incomplete"))
    vincomplete = [("|".join(sorted(f.get("implicated_lps") or []))) for f in direc if f.get("verification_incomplete")]
    pi = meta.get("pass2_integrity", {}) or {}
    pi_slim = {r: {"matched": pi[r].get("matched_directional"), "unmatched": pi[r].get("unmatched_directional"),
                   "status": pi[r].get("status"), "truncation": pi[r].get("truncation_detected"),
                   "parse_ok": pi[r].get("json_parse_success"), "model": (meta.get("pass2_raw", {}).get(r, {}) or {}).get("model")}
              for r in pi}
    per_finding = [{"lps": "|".join(sorted(f.get("implicated_lps") or [])), "severity": f.get("severity"),
                    "agreement": f.get("evaluator_agreement"), "verification_incomplete": bool(f.get("verification_incomplete")),
                    "evaluator_verdicts": f.get("evaluator_verdicts")} for f in direc]
    rec = {
        "pass": i,
        "directional_count": len(direc),
        "compound_count": len(comp),
        "directional_severity_dist": dict(sev_dir),
        "directional_3_0_risk_count": len(risk_30),
        "directional_3_0_risk_set": risk_30,
        "verification_incomplete_count": len(vincomplete),
        "verification_incomplete_set": vincomplete,
        "pass2_integrity": pi_slim,
        "per_finding": per_finding,
    }
    passes.append(rec)
    print(f"[375D-A] PASS {i}: directional={len(direc)} sev={dict(sev_dir)} "
          f"3-0_Risk={len(risk_30)} vincomplete={len(vincomplete)} integrity={pi_slim}", flush=True)

summary = {
    "harness": "A_full_replay",
    "frozen_run": "lease_review_20260604_033046_52adbf",
    "n_passes": N,
    "directional_3_0_risk_count_per_pass": [p.get("directional_3_0_risk_count") for p in passes],
    "directional_severity_dist_per_pass": [p.get("directional_severity_dist") for p in passes],
    "passes": passes,
}
os.makedirs(os.path.join(CAM_ROOT, "build_log"), exist_ok=True)
with open(os.path.join(CAM_ROOT, OUT), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)

print("\n[375D-A] ===== SUMMARY TABLE =====", flush=True)
print("  pass | dir | 3-0 Risk | vincomplete | HIGH/MED/LOW", flush=True)
for p in passes:
    if "error" in p:
        print(f"  {p['pass']:>4} | ERROR {p['error']}", flush=True)
        continue
    sd = p["directional_severity_dist"]
    print(f"  {p['pass']:>4} | {p['directional_count']:>3} | {p['directional_3_0_risk_count']:>8} | "
          f"{p['verification_incomplete_count']:>11} | "
          f"{sd.get('HIGH',0)}/{sd.get('MEDIUM',0)}/{sd.get('LOW',0)}", flush=True)
print(f"\n[375D-A] wrote {OUT}", flush=True)
