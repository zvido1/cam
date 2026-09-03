"""Step 529 — extraction-only survey harness. ONE provider call per document.

WHY EXTRACTION ONLY
-------------------
The question is what fraction of real executed leases the current single-call
33-provision extraction can process. A full Mode C run costs ~85-100 calls and
20-30 minutes and answers that question incidentally, behind coverage, gates and
synthesis. This calls `extract_provisions_single_doc` and stops -- one call, and
the answer is the whole result.

It persists through Step 490's `run_and_persist`, not ad hoc, so every row in the
survey is a durable artefact with the same provenance as a pipeline run.

WHAT IT RECORDS
---------------
Everything Step 528 made observable, which is the point of running this now and
not before: `parse_repaired`, `parse_path`, `finish_reason`, `usage`,
`raw_char_len`, plus the provision count and the document length. Before Step 528
a truncated extraction and a complete one were the same object, so this survey
could not have distinguished its own rows.
"""
import os
import sys
import time

CAM_ROOT = r"C:/Users/Owner/OneDrive/CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)
sys.path.insert(0, os.path.join(CAM_ROOT, "build_log", "_harness"))

FIXTURE_DIR = os.path.join(CAM_ROOT, "05 Lease Analyzer", "test_data", "tenants")


def _bootstrap_env():
    from dotenv import load_dotenv
    load_dotenv(r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env")


def extract_one(filename: str) -> dict:
    """One extraction call. Returns a persistable result dict, never raises.

    A failure is a ROW, not an exception: "this document cannot be processed" is
    the finding the survey exists to collect, so it has to survive into the
    record rather than abort the sweep.
    """
    from cam.adapters.lease_review.lease_extract import extract_provisions_single_doc
    from cam.adapters.lease_review.lease_provision_taxonomy import PROVISIONS
    from cam.adapters.lease_review.lease_parser import parse_document

    path = os.path.join(FIXTURE_DIR, filename)
    tenant_text = parse_document(path)

    row = {
        "fixture": filename,
        "doc_chars": len(tenant_text),
        "doc_kb": round(os.path.getsize(path) / 1024, 1),
        "provisions_requested": len(PROVISIONS),
    }

    t0 = time.time()
    try:
        out = extract_provisions_single_doc(
            tenant_text=tenant_text,
            provisions=PROVISIONS,
            config={},
            canonical=True,
        )
        meta = out.get("meta", {}) or {}
        provs = out.get("provisions", []) or []
        row.update({
            "outcome": "extraction_failed" if meta.get("extraction_failed") else "completed",
            "elapsed_sec": round(time.time() - t0, 1),
            "provisions_emitted": len(provs),
            "provisions_non_empty": sum(
                1 for p in provs if (p.get("tenant_text") or "").strip()
            ),
            "parse_repaired": meta.get("parse_repaired"),
            "parse_path": meta.get("parse_path"),
            "parse_repair_kinds": meta.get("parse_repair_kinds"),
            "provisions_recovered": meta.get("provisions_recovered"),
            "bytes_discarded": meta.get("bytes_discarded"),
            "finish_reason": meta.get("finish_reason"),
            "usage": meta.get("usage"),
            "raw_char_len": meta.get("raw_char_len"),
            "model": meta.get("model"),
            "fallback_used": meta.get("fallback_used"),
            "extraction_errors": meta.get("errors"),
            "attempt_chain": meta.get("extraction_attempt_chain"),
        })
    except Exception as e:
        # Classify without swallowing: the raw string is kept verbatim so a
        # later reader can re-classify if these buckets prove wrong.
        msg = str(e)
        low = msg.lower()
        if "429" in msg or "rate limit" in low or "resource_exhausted" in low or "quota" in low:
            kind = "rate_limited_429"
        elif "timeout" in low:
            kind = "timeout"
        else:
            kind = "other_failure"
        row.update({
            "outcome": kind,
            "elapsed_sec": round(time.time() - t0, 1),
            "error_type": type(e).__name__,
            "error": msg[:1500],
            "provisions_emitted": 0,
        })
    return row


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", default="529")
    ap.add_argument("--fixtures", nargs="+", required=True)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    _bootstrap_env()
    keys = [k for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY") if os.getenv(k)]
    if not keys:
        raise SystemExit("no Google/Gemini key loaded — a real extraction cannot proceed.")
    print("[extract_only] keys loaded: %s" % ", ".join(keys), flush=True)

    from run_store import run_and_persist

    order = list(args.fixtures)

    def one(i):
        fx = order[i - 1]
        print("\n[extract_only] === %d/%d %s ===" % (i, len(order), fx), flush=True)
        row = extract_one(fx)
        print("[extract_only] %s -> %s | provisions=%s | repaired=%s | finish=%s | %.1fs"
              % (fx, row.get("outcome"), row.get("provisions_emitted"),
                 row.get("parse_repaired"), row.get("finish_reason"),
                 row.get("elapsed_sec") or 0), flush=True)
        return row

    out, rows = run_and_persist(
        one, step=args.step, label="extract-only", n=len(order),
        notes=args.notes or ("extraction-only survey over %d real leases" % len(order)),
    )
    print("\npersisted -> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
