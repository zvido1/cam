"""Step 375-Q READ-ONLY retrospective: Stage 7 (synthesis) variance across existing Atlas Meridian runs.
No pipeline run, no API calls, no production change. Splits compound vs directional, severity dists,
and identity churn — with the same-day back-to-back repeat sets (s370r1/2/3, 370c_H1/2/3) highlighted as
the cleanest same-commit Track-A samples."""
import json, os, glob, hashlib
from collections import Counter

SHA = "fbf5f362ae10"
runs = []
for d in glob.glob("05 Lease Analyzer/results/lease_review_*"):
    for sub in ("tenant_0/pipeline_results.json", "pipeline_results.json"):
        p = os.path.join(d, sub)
        if not os.path.exists(p):
            continue
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:
            break
        tt = j.get("full_tenant_text") or ""
        if hashlib.sha1(tt.encode("utf-8", "ignore")).hexdigest()[:12] != SHA:
            break
        runs.append((os.path.basename(d), (j.get("timestamp") or "")[:19], j))
        break
runs.sort(key=lambda r: r[1])


def metrics(j):
    cpf = j.get("cross_provision_findings", []) or []
    comp = [f for f in cpf if f.get("finding_type") == "compound_risk"]
    direc = [f for f in cpf if f.get("finding_type") == "directional_mismatch"]
    other = [f for f in cpf if f.get("finding_type") not in ("compound_risk", "directional_mismatch")]

    def sev(lst):
        return Counter((f.get("severity") or "?").upper() for f in lst)

    def sig(lst):
        # content identity: type + implicated LPs (+ directionality) — stable across positional id churn
        return {(f.get("finding_type"), tuple(sorted(f.get("implicated_lps") or [])), f.get("directionality"))
                for f in lst}
    return dict(total=len(cpf), comp_n=len(comp), dir_n=len(direc), other_n=len(other),
                comp_sev=sev(comp), dir_sev=sev(direc), all_sev=sev(cpf),
                comp_sig=sig(comp), dir_sig=sig(direc))


print("%-44s %-19s | tot  C/D/O |  HIGH MED LOW | dirHIGH dirMED dirLOW | compHIGH compMED" % ("run", "ts"))
M = {}
for name, ts, j in runs:
    m = metrics(j); M[name] = m
    print("%-44s %-19s | %3d %2d/%2d/%2d | %4d %3d %3d | %6d %6d %6d | %7d %7d" % (
        name, ts, m["total"], m["comp_n"], m["dir_n"], m["other_n"],
        m["all_sev"].get("HIGH", 0), m["all_sev"].get("MEDIUM", 0), m["all_sev"].get("LOW", 0),
        m["dir_sev"].get("HIGH", 0), m["dir_sev"].get("MEDIUM", 0), m["dir_sev"].get("LOW", 0),
        m["comp_sev"].get("HIGH", 0), m["comp_sev"].get("MEDIUM", 0)))

# Same-commit repeat sets (back-to-back same-day variance experiments) + the 030920 vs 0604 pair
SETS = {
    "s370r1/2/3 (May29 repeat)": ["lease_review_20260529_191130_s370r1", "lease_review_20260529_193136_s370r2", "lease_review_20260529_195234_s370r3"],
    "370c_H1/2/3 (May30 repeat)": ["lease_review_20260530_231425_370c_H1", "lease_review_20260530_233514_370c_H2", "lease_review_20260530_235847_370c_H3"],
    "030920 vs 0604 (the reported pair)": ["lease_review_20260602_030920_d0e19e", "lease_review_20260604_033046_52adbf"],
}
for label, names in SETS.items():
    present = [n for n in names if n in M]
    if len(present) < 2:
        continue
    print("\n==== SET: %s ====" % label)
    for n in present:
        m = M[n]
        print("  %-40s total=%2d | dir=%2d (H%d/M%d/L%d) | comp=%2d (H%d/M%d)" % (
            n, m["total"], m["dir_n"], m["dir_sev"].get("HIGH", 0), m["dir_sev"].get("MEDIUM", 0), m["dir_sev"].get("LOW", 0),
            m["comp_n"], m["comp_sev"].get("HIGH", 0), m["comp_sev"].get("MEDIUM", 0)))
    # identity churn across the set (directional + compound separately)
    for kind in ("dir_sig", "comp_sig"):
        sigs = [M[n][kind] for n in present]
        union = set().union(*sigs)
        core = set(sigs[0]).intersection(*sigs)
        print("  %s identities: union=%d persist-all=%d churned=%d" % (
            kind.replace("_sig", ""), len(union), len(core), len(union) - len(core)))
        # of the persistent ones, how many flip severity across the set?
        # build (sig -> [sev per run]) for persistent sigs
        bysig = {}
        for n in present:
            j = next(jj for nm, ts, jj in runs if nm == n)
            for f in (j.get("cross_provision_findings") or []):
                ft = f.get("finding_type")
                if (kind == "dir_sig" and ft != "directional_mismatch") or (kind == "comp_sig" and ft != "compound_risk"):
                    continue
                s = (ft, tuple(sorted(f.get("implicated_lps") or [])), f.get("directionality"))
                bysig.setdefault(s, {})[n] = (f.get("severity") or "?").upper()
        flips = 0
        for s in core:
            sevs = {bysig[s].get(n) for n in present}
            if len(sevs) > 1:
                flips += 1
        print("    persist-all that FLIP severity across set: %d / %d" % (flips, len(core)))
