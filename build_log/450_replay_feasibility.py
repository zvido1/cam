"""independent post-run validation, not emitted by the sanctioned harness

Read-only against run outputs. Establishes REPLAY FEASIBILITY: whether the immutable sidecar
carries, per candidate and role, (i) a field_support mapping from each semantic field to
citation ids, (ii) context_citations with id + verbatim quote, and (iii) whether each quote
resolves against the frozen canonical source.

Canonical sources are rebuilt deterministically from the token-bound lease fixtures using the
same functions the harness used (parse_document -> build_canonical_source with
NORMALIZATION_PROFILE_V2) and are checked against FROZEN_LEASE_HASHES. Zero model calls.
Resolution uses the same normalization the harness's quote_resolves() applies.
"""
import json
import re
import sys
from collections import Counter

sys.path.insert(0, ".")
from cam.adapters.lease_review.lease_parser import parse_document
from cam.adapters.lease_review.lease_evidence_spans import (
    build_canonical_source, NORMALIZATION_PROFILE_V2,
)

SEMANTIC_FIELDS = [
    "parameter_family_relevance", "candidate_support_state",
    "value_applies_to_charge_basis_components", "charge_scope", "text_role",
    "value_completeness",
]
FROZEN = {"atreca": "7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b",
          "atlas": "da9b5655c5cab382577f139a1884625d81f42b2610a146042018026dc28d2b71"}
LEASES = {
    "atreca": "05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt",
    "atlas": "05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt",
}

# Same normalization the harness's quote_resolves() applies (harness lines ~257-264).
_WS = re.compile(r"\s+")


def norm(s):
    return _WS.sub(" ", (s or "")).strip().lower()


sources, canon = {}, {}
for slug, path in LEASES.items():
    src = build_canonical_source(parse_document(path), run_id="431-" + slug,
                                 normalization_profile=NORMALIZATION_PROFILE_V2)
    sources[slug] = src
    canon[slug] = norm(src.canonical_text)
    print(f"canonical source {slug}: source_document_hash={src.source_document_hash} "
          f"matches_frozen={src.source_document_hash == FROZEN[slug]}")
print()

d = json.load(open("build_log/431_selection_measurement_sidecar.json", encoding="utf-8"))

rows = []
agg = Counter()
for cid, s in d["series"].items():
    lease = s["lease"]
    for kind in ("canonical_panels", "degraded_panels"):
        for p in s[kind]:
            for role in ("A", "B", "C"):
                r = p["per_role"][role]
                j = r.get("judgment") or {}
                fs = j.get("field_support")
                cc = j.get("candidate_citations") or []
                xc = j.get("context_citations") or []
                fs_present = isinstance(fs, dict) and len(fs) > 0
                fs_covers = fs_present and all(f in fs for f in SEMANTIC_FIELDS)
                fs_maps_ids = fs_present and all(
                    isinstance(fs.get(f), dict)
                    and ("candidate_citation_ids" in fs[f] or "context_citation_ids" in fs[f])
                    for f in SEMANTIC_FIELDS if f in fs)
                ctx_ok = all(("citation_id" in c and "quote" in c and c.get("quote"))
                             for c in xc)
                # resolution of EVERY quote (candidate + context) against canonical text
                unres = []
                for c in cc + xc:
                    q = norm(c.get("quote"))
                    if not q or q not in canon[lease]:
                        unres.append((c.get("citation_id"), (c.get("quote") or "")[:40]))
                rows.append({
                    "candidate": cid, "lease": lease, "kind": kind,
                    "panel": p.get("canonical_attempt_index") or f"raw{p['raw_attempt_index']}",
                    "role": role, "model": r["actual_model"],
                    "field_support_present": fs_present,
                    "field_support_covers_all_6_fields": fs_covers,
                    "field_support_maps_to_citation_ids": fs_maps_ids,
                    "n_candidate_citations": len(cc), "n_context_citations": len(xc),
                    "context_citations_have_id_and_quote": ctx_ok,
                    "n_unresolved_quotes": len(unres),
                    "unresolved": unres,
                })
                agg["judgments"] += 1
                agg["fs_present"] += fs_present
                agg["fs_covers"] += fs_covers
                agg["fs_maps"] += fs_maps_ids
                agg["ctx_ok"] += ctx_ok
                agg["with_ctx"] += 1 if xc else 0
                agg["unresolved_judgments"] += 1 if unres else 0
                agg["unresolved_quotes"] += len(unres)

print("PER-CANDIDATE / PER-ROLE SUMMARY (judgments = panels x roles)")
print("cand | role | judgments | fs_present | fs_covers_6 | fs_maps_ids | with_ctx_citations | ctx_id+quote_ok | judgments_with_unresolved")
by = {}
for r in rows:
    k = (r["candidate"], r["role"])
    b = by.setdefault(k, Counter())
    b["n"] += 1
    b["fs"] += r["field_support_present"]
    b["cov"] += r["field_support_covers_all_6_fields"]
    b["map"] += r["field_support_maps_to_citation_ids"]
    b["ctx"] += 1 if r["n_context_citations"] else 0
    b["ctxok"] += r["context_citations_have_id_and_quote"]
    b["unres"] += 1 if r["n_unresolved_quotes"] else 0
for (cid, role), b in sorted(by.items()):
    print(f"{cid} | {role} | {b['n']} | {b['fs']} | {b['cov']} | {b['map']} | {b['ctx']} | {b['ctxok']} | {b['unres']}")

print()
print("TOTALS across all", agg["judgments"], "judgments:")
print("  field_support present                :", agg["fs_present"])
print("  field_support covers all 6 fields    :", agg["fs_covers"])
print("  field_support maps fields->citation ids:", agg["fs_maps"])
print("  judgments carrying context_citations :", agg["with_ctx"])
print("  context citations have id + quote    :", agg["ctx_ok"], "(of", agg["judgments"], "judgments)")
print("  judgments with >=1 unresolved quote  :", agg["unresolved_judgments"])
print("  unresolved quotes total              :", agg["unresolved_quotes"])
print()
print("UNRESOLVED DETAIL:")
for r in rows:
    if r["n_unresolved_quotes"]:
        print(f"  {r['candidate']} {r['kind']} panel {r['panel']} role {r['role']} ({r['model']}): {r['unresolved']}")
