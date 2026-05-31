"""372-NDET harness — N=20 resample per (cell, model) with reasoning-fingerprint recording.

Calls each model 20 times on the fixed production prompt for 4 cells.
Records verdict + fingerprint flags per sample. NO full pipeline.

Fingerprint flags (defined BEFORE running):
  LP-03: flag_derive_s22 = did reasoning derive expiry from S2.2 renewal-start date?
  LP-09: flag_merger_coc  = did reasoning treat merger/consolidation as covering CoC?
  LP-28: flag_retrospec   = did reasoning read "as of Commencement Date" retrospectively?
  LP-22: flag_timing_req  = did reasoning engage the "before commencement" timing qualifier?
"""
import os, sys, json, hashlib, re, time, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Keys ──
KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
WANTED = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY"}
for line in open(KEYS_ENV, encoding="utf-8"):
    k, _, v = line.strip().partition("=")
    if k.strip() in WANTED:
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
os.environ["DISABLE_OPENROUTER"] = "1"
os.environ["OPENROUTER_DRY_RUN"] = "1"

CAM_ROOT = r"C:\Users\Owner\OneDrive\CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

from cam.adapters.lease_review.lease_coverage_305 import (
    _build_user_prompt, _SYSTEM_PROMPT as _SYSTEM_PROMPT_305, EVALUATOR_LINEUP_305,
)
from cam.adapters.lease_review.lease_knowledge import get_all_issue_areas
from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
from cam.core.json_extract import safe_json_extract
from cam.core.provider_health import get_health_tracker

LEASE = r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\results"
H2 = f"{LEASE}/lease_review_20260530_233514_370c_H2/tenant_0/pipeline_results.json"
d_h2 = json.load(open(H2, encoding="utf-8"))
by_id_h2 = {a["issue_area_id"]: a for a in d_h2["coverage_assessment"]}
all_areas = {a["id"]: a for a in get_all_issue_areas()}  # has expected_elements_305
gov = (d_h2.get("jurisdiction") or {}).get("governing_law")
# Cross-LP texts (same as production lease_coverage.py)
all_lp_texts = {a["issue_area_id"]: a.get("tenant_text","") for a in d_h2["coverage_assessment"] if a.get("tenant_text")}

N_SAMPLES = 20

# ── Cells: (lp_id, element_id) ──
CELLS = [
    ("LP-03", "LP-03.expiration_date"),
    ("LP-09", "LP-09.change_of_control_addressed"),
    ("LP-28", "LP-28.grandfathering_pre_existing"),
    ("LP-22", "LP-22.landlord_obligation_obtain_snda_existing_lenders"),
]

# ── Fingerprint classifiers (defined before running, applied post-hoc) ──
def fingerprint(lp_id, reasoning_text):
    r = reasoning_text.lower()
    if lp_id == "LP-03":
        # Did reasoning derive expiry from S2.2 renewal-start date?
        derive = bool(
            re.search(r"2031|march 31|april 1|renewal.*impl|impl.*expir|imply.*expir|expir.*impl|calculat|inferr|section 2\.2", r)
        )
        return {"derive_from_s22": derive}
    elif lp_id == "LP-09":
        # Did reasoning treat merger/consolidation language as covering change-of-control?
        merger_covers = bool(
            re.search(r"merger.*cover|consol.*cover|cover.*merger|cover.*consol|synonym|address.*change.?of.?control|satisf.*change.?of.?control|change.?of.?control.*address|match.*synonym", r)
        )
        return {"merger_covers_coc": merger_covers}
    elif lp_id == "LP-28":
        # Did reasoning read "as of" retrospectively (covering pre-existing)?
        retrospec = bool(
            re.search(r"pre.?exist|retroact|backward|prior to.*commencement|before.*commencement|cover.*pre|pre.*condition|violations.*exist.*before|existing.*violation|retrosp", r)
        )
        return {"retrospective_reading": retrospec}
    elif lp_id == "LP-22":
        # Did reasoning engage the "before commencement" timing sub-requirement?
        timing = bool(
            re.search(r"before.*commence|prior.*commence|timing|delivery.*before|before.*delivery|when.*deliver|deliver.*when|not.*state.*before|require.*before", r)
        )
        return {"timing_before_commencement": timing}
    return {}


def call_evaluator_once(role, ev_cfg, user_prompt, lp_id, element_id, sample_idx):
    """One evaluator call. Returns {role, verdict, citation, reasoning, fingerprint}."""
    health = get_health_tracker()
    provider = ev_cfg["provider"]
    model = ev_cfg["model"]
    if not health.is_available(provider):
        return {"role": role, "sample": sample_idx, "verdict": "ERROR", "error": f"provider {provider} degraded"}
    try:
        target = ModelTarget(
            name=f"{provider}:{model}-ndet-{lp_id}-{role}-s{sample_idx}",
            provider=provider, model=model,
            max_output_tokens=ev_cfg["max_output_tokens"],
            temperature=ev_cfg["temperature"],
            timeout_sec=ev_cfg["timeout_sec"],
        )
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(provider)
        raw = adapter.call(_SYSTEM_PROMPT_305, user_prompt, target).strip()

        # parse to find this element's verdict + reasoning
        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = safe_json_extract(raw)
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    parsed = v
                    break
        if not isinstance(parsed, list):
            return {"role": role, "sample": sample_idx, "verdict": "PARSE_ERROR", "raw_len": len(raw)}

        # find matching element
        verdict = "NOT_FOUND"
        citation = None
        reasoning = ""
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if item.get("element_id") == element_id:
                verdict = item.get("verdict", "?")
                c = item.get("citation") or {}
                citation = c.get("section_ref") if c else None
                reasoning = item.get("reasoning", "")
                break

        fp = fingerprint(lp_id, reasoning)
        return {
            "role": role, "sample": sample_idx,
            "verdict": verdict, "citation": citation,
            "reasoning": reasoning[:500],   # truncate for storage
            "fingerprint": fp,
        }
    except Exception as e:
        return {"role": role, "sample": sample_idx, "verdict": "ERROR", "error": str(e)[:120]}


def run_cell(lp_id, element_id):
    """Run N=20 × 3 models for one cell. Returns list of result dicts."""
    a = by_id_h2[lp_id]
    area = all_areas[lp_id]
    elements_305 = area.get("expected_elements_305", [])
    # Build cross_lp_texts for this LP (same as production; cross_LP_coverage may be str or list)
    cross_lp_texts = {}
    for e in elements_305:
        clp = e.get("cross_LP_coverage")
        if isinstance(clp, str) and clp:
            cross_lp_texts[clp] = all_lp_texts.get(clp, "")
        elif isinstance(clp, list):
            for c in clp:
                cross_lp_texts[c] = all_lp_texts.get(c, "")
    user_prompt = _build_user_prompt(
        lp_id, area.get("name", ""),
        a.get("tenant_text", ""),
        elements_305,
        a.get("negative_space_signals", []),
        gov,
        cross_lp_texts=cross_lp_texts if cross_lp_texts else None,
    )
    ph = hashlib.md5(user_prompt.encode("utf-8", "replace")).hexdigest()[:8]
    print(f"\n{'='*60}", flush=True)
    print(f"CELL {lp_id}/{element_id}  prompt_md5={ph}", flush=True)

    results = []
    # Run sequentially per sample (each sample calls A/B/C in parallel)
    for i in range(N_SAMPLES):
        sample_results = {}
        with ThreadPoolExecutor(max_workers=3) as pool:
            futs = {
                pool.submit(call_evaluator_once, role, ev_cfg, user_prompt, lp_id, element_id, i): role
                for role, ev_cfg in EVALUATOR_LINEUP_305.items()
            }
            for fut in as_completed(futs):
                role = futs[fut]
                try:
                    sample_results[role] = fut.result()
                except Exception as e:
                    sample_results[role] = {"role": role, "sample": i, "verdict": "EXCEPTION", "error": str(e)[:100]}
        results.extend(sample_results.values())
        # log every 5
        if (i + 1) % 5 == 0:
            for role in ["A", "B", "C"]:
                r = sample_results.get(role, {})
                fp = r.get("fingerprint", {})
                print(f"  s{i+1:02d} {role}({r.get('verdict','?')}|{r.get('citation','none')}) fp={fp}", flush=True)
    return results


def summarize_cell(lp_id, results):
    by_role = {"A": [], "B": [], "C": []}
    for r in results:
        role = r.get("role")
        if role in by_role:
            by_role[role].append(r)
    print(f"\n{'='*60}", flush=True)
    print(f"SUMMARY  {lp_id}", flush=True)
    for role in ["A", "B", "C"]:
        items = by_role[role]
        verdicts = Counter(r.get("verdict") for r in items)
        # fingerprint distributions
        fp_keys = set()
        for r in items:
            fp_keys |= set((r.get("fingerprint") or {}).keys())
        fp_dists = {}
        for k in fp_keys:
            vals = [r.get("fingerprint", {}).get(k) for r in items if "fingerprint" in r]
            fp_dists[k] = Counter(vals)
        # correlation: for each fp key, does verdict track it?
        correlations = {}
        for k in fp_keys:
            groups = {}
            for r in items:
                if "fingerprint" not in r: continue
                fp_val = r["fingerprint"].get(k)
                v = r.get("verdict")
                groups.setdefault(fp_val, Counter())[v] += 1
            correlations[k] = groups
        print(f"  {role} N={len(items)}: verdicts={dict(verdicts)}", flush=True)
        for k in fp_keys:
            print(f"    fp.{k}: {dict(fp_dists[k])}", flush=True)
            for fp_val, vc in correlations[k].items():
                print(f"      when {k}={fp_val}: {dict(vc)}", flush=True)
    return by_role


all_results = {}
for lp_id, element_id in CELLS:
    cell_results = run_cell(lp_id, element_id)
    all_results[(lp_id, element_id)] = cell_results
    by_role = summarize_cell(lp_id, cell_results)

# Save raw results
out = {f"{lp}/{eid}": res for (lp, eid), res in all_results.items()}
open(r"C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\_372ndet_results.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=2, ensure_ascii=False)
)
print("\nSaved to _372ndet_results.json", flush=True)
