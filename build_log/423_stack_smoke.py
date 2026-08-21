"""Does the 423 stack actually find the clauses, on a real lease?

STANDALONE SMOKE TEST. Wires nothing. Touches no pipeline module. Imports the
423A/423C functions exactly as they are and calls them directly.

Established by build_log/FINDING_evidence_architecture_unwired.md: the whole
423/425/427 stack has no production caller and has only ever run against test
fixtures. Before anyone builds a seam to it, this establishes whether it does the
thing it was built to do on a real document.

THE TWO QUESTIONS:
  LP-07 -- does any verified span contain "shall mean 22.4%"?
           (the Proportionate Share definition, line 22, which Mode C extraction
           delivers to LP-07 in 0 of 6 runs -- FINDING_definitional_clause_loss.md)
  LP-12 -- does any verified span contain "Termination Right"?
           (Atlas 13.2, which extraction cross-files to LP-12 in only 2 of 6 runs
           -- FINDING_lease_term_years_contingent_term.md section 5)

If the elicitor does not find them, wiring the stack changes nothing and the
problem is recall in the elicitor, which is a different project.

Run:  python build_log/423_stack_smoke.py
"""
import json
import os
import sys
import time
from pathlib import Path

CAM = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAM))

for line in open(r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env", encoding="utf-8"):
    k, _, v = line.strip().partition("=")
    if k.strip().endswith("_API_KEY"):
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

from cam.adapters.lease_review.lease_evidence_spans import (  # noqa: E402
    build_canonical_source,
    NORMALIZATION_PROFILE_V2,
)
from cam.adapters.lease_review.lease_element_elicitation import (  # noqa: E402
    load_expected_elements_by_lp,
    elicit_and_resolve_for_lp,
    dedupe_elicited_spans,
    ELICITATION_PRIMARY,
)

LEASE = CAM / "05 Lease Analyzer" / "test_data" / "tenants" / "atlas_meridian_warehouse_lease.txt"
OUT = Path(__file__).resolve().parent / "423_stack_smoke_out"
OUT.mkdir(exist_ok=True)

# The needles, each verified unique in the lease (see the two findings).
TARGETS = {
    "LP-07": "shall mean 22.4%",
    "LP-12": "Termination Right",
}

raw_text = LEASE.read_text(encoding="utf-8")
source = build_canonical_source(
    raw_text,
    source_type="lease_tenant_document",
    run_id="423_stack_smoke",
    normalization_profile=NORMALIZATION_PROFILE_V2,
)
print("canonical source: %d chars | hash %s | profile %s"
      % (len(source.canonical_text), source.canonical_text_hash[:16], NORMALIZATION_PROFILE_V2), flush=True)
print("needle present in canonical text: %s"
      % {n: (n in source.canonical_text) for n in TARGETS.values()}, flush=True)
print("elicitor: %s:%s" % ELICITATION_PRIMARY, flush=True)

# These are the REAL elements coverage uses -- expected_elements_305 from
# retail_lease_knowledge.json, the same file lease_coverage_305 reads.
elements_by_lp = load_expected_elements_by_lp()

report = {}
for lp_id, needle in TARGETS.items():
    entry = elements_by_lp.get(lp_id)
    if entry is None:
        print("%s: NOT IN SCHEMA" % lp_id, flush=True)
        continue
    print("\n" + "=" * 88, flush=True)
    print("%s %s -- %d elements" % (lp_id, entry["lp_name"], len(entry["elements"])), flush=True)
    for e in entry["elements"]:
        print("    %s" % e["element_id"], flush=True)

    t0 = time.time()
    try:
        result, raw_records = elicit_and_resolve_for_lp(source, lp_id, elements_by_lp, canonical=True)
    except Exception as exc:
        print("  ELICITATION FAILED: %s: %s" % (type(exc).__name__, str(exc)[:300]), flush=True)
        report[lp_id] = {"ok": False, "error": str(exc)[:300]}
        continue
    elapsed = round(time.time() - t0, 1)
    deduped = dedupe_elicited_spans(raw_records)

    verified = [r for r in deduped if r.get("verification_status") == "verified"]
    by_status = {}
    for r in deduped:
        s = r.get("verification_status")
        by_status[s] = by_status.get(s, 0) + 1

    hits = [r for r in verified if needle in (r.get("span_text") or "")]

    print("  elapsed %.1fs | provider calls 1 | raw %d -> deduped %d | %s"
          % (elapsed, len(raw_records), len(deduped), by_status), flush=True)
    print("  NEEDLE %r found in a VERIFIED span: %s" % (needle, bool(hits)), flush=True)
    for h in hits:
        print("     span [%s,%s] elicited_by=%s" % (h.get("start_char"), h.get("end_char"), h.get("elicited_by")), flush=True)
        print("     text: %s" % (h.get("span_text") or "")[:300].replace("\n", " "), flush=True)

    report[lp_id] = {
        "ok": True,
        "lp_name": entry["lp_name"],
        "elements": len(entry["elements"]),
        "elapsed_sec": elapsed,
        "provider_calls": 1,
        "raw_records": len(raw_records),
        "deduped_records": len(deduped),
        "status_counts": by_status,
        "verified_count": len(verified),
        "needle": needle,
        "needle_found_in_verified_span": bool(hits),
        "hit_spans": [{"start": h.get("start_char"), "end": h.get("end_char"),
                       "elicited_by": h.get("elicited_by"),
                       "span_text": h.get("span_text")} for h in hits],
    }
    (OUT / ("%s_deduped.json" % lp_id)).write_text(
        json.dumps(deduped, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / ("%s_elicitation_meta.json" % lp_id)).write_text(
        json.dumps(result.get("meta", {}), indent=2, ensure_ascii=False), encoding="utf-8")

(OUT / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("\n" + "=" * 88, flush=True)
for lp_id, r in report.items():
    if r.get("ok"):
        print("%s: needle %r found=%s (verified spans %d)"
              % (lp_id, r["needle"], r["needle_found_in_verified_span"], r["verified_count"]), flush=True)
print("persisted to build_log/423_stack_smoke_out/", flush=True)
