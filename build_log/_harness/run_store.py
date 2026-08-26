"""Shared local-run store. Persistence is the default and has no off switch.

WHY THIS EXISTS
---------------
Step 489 established that no completed local coverage run from Steps 457-484
survives on disk, so the fallback censuses those steps reported cannot be
re-verified. Step 463 recorded the same loss for five earlier LP-12
observations. Both times the run was inspected in memory and the data was
gone by the time a later step needed it.

The cause is not carelessness. Every persisting probe in build_log/ hand-rolls
the same three things -- sys.path insert, .env key load, json.dump to a
hard-coded directory -- so persistence is per-script boilerplate that an
ad-hoc run skips by default. This module inverts that: you call
`run_and_persist`, and the full result is written before you can look at it.

There is deliberately NO `persist=False` parameter. A harness that should not
write should not use this module.

SCOPE
-----
Harness-side only. Imports nothing from the app and changes no pipeline
behaviour: it calls a function you hand it and writes what comes back.

LAYOUT
------
    build_log/runs/<step>_<label>_<UTC>/
        run_01_full.json      full result, verbatim
        run_01_census.json    provenance census (see census_result)
        index.json            per-run metadata + config snapshot
"""
import io
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone

CAM_ROOT = r"C:/Users/Owner/OneDrive/CAM"
KEYS_ENV = r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env"
RUNS_DIR = os.path.join(CAM_ROOT, "build_log", "runs")

# Put CAM on the path at import, not only inside bootstrap_env(). The flag
# snapshot in index.json needs to import cam.* even on a --dry-run that loads
# no keys, and without this it silently recorded "No module named 'cam'" --
# losing the most audit-relevant field in the index.
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

_STUB_RE = re.compile(r"^Evaluator ([ABC]) did not complete$")


def bootstrap_env():
    """Put CAM on sys.path and load provider keys. Idempotent.

    The keys live outside the CAM repo (see CLAUDE.md); every harness needs
    this and every harness has re-implemented it.
    """
    if CAM_ROOT not in sys.path:
        sys.path.insert(0, CAM_ROOT)
    loaded = []
    if os.path.exists(KEYS_ENV):
        for line in io.open(KEYS_ENV, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            k = k.strip()
            if k.endswith("_API_KEY"):
                os.environ[k] = v.strip().strip('"').strip("'")
                loaded.append(k)
    return loaded


def new_run_dir(step, label):
    """Create and return build_log/runs/<step>_<label>_<UTC stamp>/."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(label)).strip("-") or "run"
    d = os.path.join(RUNS_DIR, "%s_%s_%s" % (step, safe, stamp))
    os.makedirs(d, exist_ok=True)
    return d


def census_result(result):
    """Provenance census over one pipeline result.

    Answers, at write time, the questions Steps 487-489 had to reconstruct
    afterwards: which model actually served each role, how many records are
    `all_failed` stubs, and whether any element record's provenance
    contradicts its role-level fallback event.

    Stub detection keys on the `reasoning` string, NOT on `actual_model` or
    `is_fallback` -- Step 489 established those two fields name the requested
    model on a stub, so a census over them silently over-counts provider
    service. See build_log/FINDING_evaluator_substitution_is_unmarked.md.
    """
    if not isinstance(result, dict):
        return {"error": "result is %s, not dict" % type(result).__name__}

    by_role = {}
    stubs = []
    n_records = 0
    for lp in (result.get("coverage_assessment") or []):
        lp_id = lp.get("issue_area_id")
        for ev in (lp.get("element_verdicts") or []):
            for e in (ev.get("evaluator_verdicts") or []):
                n_records += 1
                role = e.get("role")
                model = e.get("actual_model")
                is_stub = bool(_STUB_RE.match(str(e.get("reasoning") or "").strip()))
                if is_stub:
                    stubs.append({
                        "role": role, "lp_id": lp_id,
                        "element_id": ev.get("element_id"),
                        "claims_model": model,
                        "claims_is_fallback": e.get("is_fallback"),
                    })
                    continue          # a stub is not evidence of service
                slot = by_role.setdefault(role, {"served": {}, "fallback": 0})
                slot["served"][model] = slot["served"].get(model, 0) + 1
                if e.get("is_fallback"):
                    slot["fallback"] += 1

    events = result.get("fallback_events") or []
    ev_kinds = {}
    for e in events:
        ev_kinds[e.get("event_type")] = ev_kinds.get(e.get("event_type"), 0) + 1

    # Contradiction: a role-level all_failed whose element records still name a model.
    contradictions = []
    failed_pairs = {(e.get("role"), e.get("lp_id")) for e in events
                    if e.get("event_type") == "all_failed"}
    for s in stubs:
        if (s["role"], s["lp_id"]) in failed_pairs and s["claims_model"]:
            contradictions.append(s)

    ts = {e.get("timestamp") for e in events if e.get("timestamp")}

    return {
        "evaluator_records": n_records,
        "per_role_served": by_role,
        "stub_count": len(stubs),
        "stubs": stubs,
        "provenance_contradictions": len(contradictions),
        "fallback_event_kinds": ev_kinds,
        "fallback_event_count": len(events),
        # Step 488 correction 3: 30 events sharing one microsecond means the
        # field is stamped at assembly, not at failure. Record it, don't infer.
        "distinct_event_timestamps": len(ts),
        "run_degraded": result.get("run_degraded"),
        "degraded_reason": result.get("degraded_reason"),
        "invalid_for_legal_analysis": result.get("invalid_for_legal_analysis"),
        "extraction_completeness_failed_lps": result.get("extraction_completeness_failed_lps"),
        "api_calls_total": result.get("api_calls_total"),
        "elapsed_sec": result.get("elapsed_sec"),
        "models_used": result.get("models_used"),
    }


def _flag_snapshot():
    """Record the seam/gate flags in force. Read-only; import failure is not fatal."""
    snap = {}
    try:
        from cam.adapters.lease_review import lease_coverage as _lc
        snap["SPAN_EVIDENCE_ENABLED"] = getattr(_lc, "SPAN_EVIDENCE_ENABLED", None)
        snap["SPAN_EVIDENCE_LPS"] = sorted(getattr(_lc, "SPAN_EVIDENCE_LPS", []) or [])
        snap["SECTION_EXPANDED_SPAN_LPS"] = sorted(getattr(_lc, "SECTION_EXPANDED_SPAN_LPS", []) or [])
    except Exception as e:
        snap["lease_coverage"] = "unavailable: %s" % str(e)[:80]
    try:
        from cam.adapters.lease_review import lease_adapter as _la
        snap["GATE_ABORT_RETURNS_DEGRADED"] = getattr(_la, "GATE_ABORT_RETURNS_DEGRADED", None)
        snap["DEGRADABLE_APPLICABILITY"] = sorted(getattr(_la, "DEGRADABLE_APPLICABILITY", []) or [])
    except Exception as e:
        snap["lease_adapter"] = "unavailable: %s" % str(e)[:80]
    try:
        from cam.adapters.lease_review import lease_coverage_305 as _c5
        snap["ENTAILMENT_TEST_LPS"] = sorted(getattr(_c5, "ENTAILMENT_TEST_LPS", []) or [])
    except Exception as e:
        snap["lease_coverage_305"] = "unavailable: %s" % str(e)[:80]
    return snap


def _git_head():
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CAM_ROOT,
                             capture_output=True, text=True, timeout=20)
        sha = (out.stdout or "").strip()
        st = subprocess.run(["git", "status", "--porcelain"], cwd=CAM_ROOT,
                            capture_output=True, text=True, timeout=20)
        return {"head": sha, "clean": not (st.stdout or "").strip()}
    except Exception as e:
        return {"head": None, "error": str(e)[:80]}


def run_and_persist(fn, step, label, n=1, notes=None, on_result=None):
    """Call `fn(i)` n times, persisting each full result BEFORE inspecting it.

    Args:
        fn:        callable taking the 1-based run index, returning the result dict.
        step:      step number, e.g. "491". Names the output directory.
        label:     short run label, e.g. "atlas-modec".
        n:         number of runs.
        notes:     free text stored in index.json.
        on_result: optional callback(i, result, run_dir) for per-run reporting.
                   It runs AFTER the result is on disk, so a crash inside it
                   cannot cost the run.

    Returns (run_dir, [per-run index rows]).
    """
    out_dir = new_run_dir(step, label)
    index = {
        "step": step,
        "label": label,
        "n_requested": n,
        "notes": notes,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "git": _git_head(),
        "flags": _flag_snapshot(),
        "runs": [],
    }

    def _write_index():
        with io.open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False, default=str)

    _write_index()
    print("[run_store] persisting to %s" % out_dir, flush=True)

    for i in range(1, n + 1):
        row = {"run": i, "started_utc": datetime.now(timezone.utc).isoformat()}
        t0 = time.time()
        try:
            result = fn(i)
        except Exception as e:
            row.update({"outcome": "EXCEPTION", "error": str(e)[:400],
                        "traceback": traceback.format_exc()[-2000:],
                        "elapsed_sec": round(time.time() - t0, 1)})
            index["runs"].append(row)
            _write_index()
            print("[run_store] run %d EXCEPTION: %s" % (i, str(e)[:160]), flush=True)
            continue

        row["elapsed_sec"] = round(time.time() - t0, 1)

        # Persist FIRST. Everything after this point is analysis, and analysis
        # failing must not cost the data -- that is the whole point of the module.
        full_path = os.path.join(out_dir, "run_%02d_full.json" % i)
        try:
            with io.open(full_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            row["full"] = os.path.basename(full_path)
            row["bytes"] = os.path.getsize(full_path)
        except Exception as e:
            row["persist_error"] = str(e)[:300]

        try:
            cen = census_result(result)
            with io.open(os.path.join(out_dir, "run_%02d_census.json" % i), "w",
                         encoding="utf-8") as f:
                json.dump(cen, f, indent=2, ensure_ascii=False, default=str)
            row["census"] = {k: cen.get(k) for k in
                             ("evaluator_records", "stub_count",
                              "provenance_contradictions", "fallback_event_count",
                              "run_degraded", "degraded_reason", "api_calls_total")}
        except Exception as e:
            row["census_error"] = str(e)[:300]

        row["outcome"] = "ok"
        index["runs"].append(row)
        _write_index()

        c = row.get("census") or {}
        print("[run_store] run %d persisted (%s bytes) calls=%s degraded=%s stubs=%s"
              % (i, row.get("bytes"), c.get("api_calls_total"),
                 c.get("run_degraded"), c.get("stub_count")), flush=True)

        if on_result:
            try:
                on_result(i, result, out_dir)
            except Exception as e:
                print("[run_store] on_result raised (data is safe): %s" % str(e)[:200],
                      flush=True)

    index["finished_utc"] = datetime.now(timezone.utc).isoformat()
    _write_index()
    print("[run_store] done -> %s" % out_dir, flush=True)
    return out_dir, index["runs"]
