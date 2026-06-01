"""372-AC Part 2 probe: A and C x15 on clear-present short-prompt cells.
LP-32 (de_minimis_carveout, 8 elems): clause exists; tests A's 50/50 split.
LP-13 (negligence_carveouts, 6 elems): clause exists; tests C's sub-class instability.
"""
import os, sys, json, hashlib, re
from collections import Counter

KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
for line in open(KEYS_ENV, encoding="utf-8"):
    k, _, v = line.strip().partition("=")
    if k.strip() in WANTED: os.environ[k.strip()] = v.strip().strip('"').strip("'")
os.environ["DISABLE_OPENROUTER"] = "1"

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path: sys.path.insert(0, CAM_ROOT)

from cam.adapters.lease_review.lease_knowledge import get_all_issue_areas
from cam.adapters.lease_review.lease_coverage_305 import (
    _build_user_prompt, _SYSTEM_PROMPT as SYS, EVALUATOR_LINEUP_305,
)
from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
from cam.core.json_extract import safe_json_extract

LEASE = r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\results"
H2 = f"{LEASE}/lease_review_20260530_233514_370c_H2/tenant_0/pipeline_results.json"
d = json.load(open(H2, encoding="utf-8"))
by_id = {a["issue_area_id"]: a for a in d["coverage_assessment"]}
all_areas = {a["id"]: a for a in get_all_issue_areas()}
all_lp_texts = {a["issue_area_id"]:a.get("tenant_text","") for a in d["coverage_assessment"] if a.get("tenant_text")}
gov = (d.get("jurisdiction") or {}).get("governing_law")

CELLS = [
    ("LP-32", "LP-32.de_minimis_carveout",   ["A","C"]),
    ("LP-13", "LP-13.negligence_carveouts",   ["A","C"]),
]
N = 15

def make_prompt(lp_id):
    area = all_areas[lp_id]
    el305 = area.get("expected_elements_305", [])
    cross = {}
    for e in el305:
        clp = e.get("cross_LP_coverage")
        if isinstance(clp, str) and clp: cross[clp] = all_lp_texts.get(clp,"")
        elif isinstance(clp, list):
            for c in clp: cross[c] = all_lp_texts.get(c,"")
    a = by_id[lp_id]
    return _build_user_prompt(lp_id, area.get("name",""), a.get("tenant_text",""),
                              el305, a.get("negative_space_signals",[]), gov,
                              cross_lp_texts=cross if cross else None), el305

def call_once(role, lp_id, prompt, el305, sample_idx):
    ev_cfg = EVALUATOR_LINEUP_305[role]
    _tokens = max(ev_cfg.get("max_output_tokens",3000), len(el305)*300+500)
    target = ModelTarget(
        name=f"{ev_cfg['provider']}:{ev_cfg['model']}-ac-{lp_id}-{role}-s{sample_idx}",
        provider=ev_cfg["provider"], model=ev_cfg["model"],
        max_output_tokens=_tokens, temperature=ev_cfg["temperature"],
        timeout_sec=ev_cfg["timeout_sec"],
    )
    router = ProviderRouter([target], RouterConfig())
    adapter = router._get_adapter(ev_cfg["provider"])
    raw = adapter.call(SYS, prompt, target).strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = safe_json_extract(raw)
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list): parsed = v; break
    if not isinstance(parsed, list):
        return "PARSE_ERROR", None, ""
    for item in parsed:
        if isinstance(item, dict) and item.get("element_id") == CELLS[[c[0] for c in CELLS].index(lp_id)][1]:
            return item.get("verdict","?"), item.get("citation"), item.get("reasoning","")[:300]
    return "NOT_FOUND", None, ""

results = {}
for lp_id, target_elem, roles in CELLS:
    prompt, el305 = make_prompt(lp_id)
    ph = hashlib.md5(prompt.encode("utf-8","replace")).hexdigest()[:8]
    budget = max(3000, len(el305)*300+500)
    print(f"\n=== {lp_id}/{target_elem} | prompt_md5={ph} budget={budget} ===")
    results[(lp_id, target_elem)] = {}
    for role in roles:
        samples = []
        for i in range(N):
            try:
                v, cite, reason = call_once(role, lp_id, prompt, el305, i)
                cited = bool(cite and (cite.get("section_ref") if isinstance(cite,dict) else cite))
                samples.append({"verdict":v, "cited":cited, "reasoning":reason[:200]})
            except Exception as e:
                samples.append({"verdict":"ERROR","error":str(e)[:80]})
            if (i+1) % 5 == 0:
                vc = Counter(s["verdict"] for s in samples)
                print(f"  {role} s{i+1}: {dict(vc)}")
        results[(lp_id, target_elem)][role] = samples
        vc = Counter(s["verdict"] for s in samples)
        modal = vc.most_common(1)[0]
        n_ok = sum(1 for s in samples if s["verdict"] not in ("ERROR","PARSE_ERROR","NOT_FOUND"))
        print(f"  {role} FINAL: {dict(vc)} modal={modal[0]}x{modal[1]}/{n_ok} agree={round(100*modal[1]/max(n_ok,1))}%")

json.dump({str(k):v for k,v in results.items()},
          open(r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\_372ac_results.json","w",encoding="utf-8"),
          indent=2, ensure_ascii=False)
print("\nSaved to _372ac_results.json")
