import json, glob, os
from collections import Counter

def audit(path):
    d = json.load(open(path, encoding='utf-8'))
    cpfs = d.get('cross_provision_findings', [])
    dirs = [c for c in cpfs if c.get('finding_type') == 'directional_mismatch']
    comp = [c for c in cpfs if c.get('finding_type') == 'compound_risk']
    meta = (d.get('_stage_data', {}) or {}).get('synthesis_meta', {}) or d.get('synthesis_meta', {}) or {}
    integ = meta.get('pass2_integrity', {})
    raw = meta.get('pass2_raw', {})
    # directional candidates = distinct Dir- ids seen across roles' raw verdicts
    dir_cand_ids = set()
    for role, info in (raw or {}).items():
        for v in (info.get('verdicts') or []):
            if not isinstance(v, dict):
                continue
            cid = str(v.get('candidate_id', ''))
            if cid.startswith('Dir-'):
                dir_cand_ids.add(cid)
    print(f"\n=== {os.path.basename(os.path.dirname(os.path.dirname(path)))} ===")
    print(f"  directional FINDINGS:   {len(dirs)}")
    print(f"  directional CANDIDATES: {len(dir_cand_ids)}  ids={sorted(dir_cand_ids)}")
    print(f"  compound findings:      {len(comp)}")
    print(f"  DIRECTIONAL+COMPOUND:   {len(dirs) + len(comp)}   <- bucket-migration control")
    print(f"  flagged_lp_count:       {meta.get('flagged_lp_count', '?')}")
    print(f"  directional agreement:  {dict(Counter(c.get('evaluator_agreement') for c in dirs))}")
    print(f"  directional severity:   {dict(Counter(c.get('severity') for c in dirs))}")
    print(f"  pass2_integrity all_lost flags: "
          f"{ {r: i.get('all_lost') for r, i in integ.items()} }")
    print(f"  pass2_integrity matched: "
          f"{ {r: i.get('matched_directional') for r, i in integ.items()} }")

# point at the newest runs after they complete:
paths = sorted(glob.glob('results/lease_review_*/tenant_0/pipeline_results.json'),
               key=os.path.getmtime)[-4:]
for p in paths:
    audit(p)
