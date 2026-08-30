"""Local Mode C coverage harness. Persists by default.

WHY THIS EXISTS
---------------
Steps 457-484 ran local Mode C coverage repeatedly and Step 489 could not find
a single persisted result: the arc had no checked-in coverage harness, so each
step invoked the pipeline ad hoc and the data died with the process. The three
August probes that DO persist (LP12_extraction_runs, PSHARE_extraction_runs,
464_shape_runs) are all extraction-stage only.

This is the missing one. It calls `run_lease_coverage_only` -- the same entry
point run_417_baseline.py used -- and routes every result through
run_store.run_and_persist, which writes the full JSON and a provenance census
before anything inspects it.

Changes no pipeline behaviour: it passes `config={}` (production defaults) and
writes whatever comes back.

USAGE
-----
    python build_log/_harness/run_mode_c.py --step 491 --n 3
    python build_log/_harness/run_mode_c.py --step 491 --fixture divall --n 1
    python build_log/_harness/run_mode_c.py --list-fixtures
    python build_log/_harness/run_mode_c.py --step 491 --n 1 --dry-run

COST: a full Atlas Mode C run is ~97 provider calls and ~15-17 minutes.
--dry-run persists a synthetic result and spends nothing; use it to verify the
harness itself.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_store import bootstrap_env, run_and_persist, CAM_ROOT  # noqa: E402

FIXTURE_DIR = os.path.join(CAM_ROOT, "05 Lease Analyzer", "test_data", "tenants")

FIXTURES = {
    "atlas": "atlas_meridian_warehouse_lease.txt",
    "atreca": "atreca_eastjamie_southsf_lease.txt",
    "divall": "divall_wendys_mtpleasant_lease.txt",
}


def resolve_fixture(name):
    """Return an absolute fixture path, or raise with what IS available."""
    if os.path.isabs(name) and os.path.exists(name):
        return name
    fn = FIXTURES.get(name, name)
    p = os.path.join(FIXTURE_DIR, fn)
    if os.path.exists(p):
        return p
    avail = sorted(f for f in os.listdir(FIXTURE_DIR)) if os.path.isdir(FIXTURE_DIR) else []
    raise SystemExit(
        "fixture %r not found at %s\navailable in %s:\n  %s"
        % (name, p, FIXTURE_DIR, "\n  ".join(avail) or "(none)")
    )


def _synthetic_result(i):
    """A result-shaped payload for --dry-run. No provider calls."""
    return {
        "run_id": "dryrun_%02d" % i,
        "mode": "analyze",
        "api_calls_total": 0,
        "elapsed_sec": 0.0,
        "run_degraded": False,
        "degraded_reason": None,
        "invalid_for_legal_analysis": False,
        "extraction_completeness_failed_lps": [],
        "fallback_events": [],
        "models_used": {"extraction": "(dry-run)"},
        "coverage_assessment": [{
            "issue_area_id": "LP-00",
            "element_verdicts": [{
                "element_id": "LP-00.dryrun",
                "evaluator_verdicts": [
                    {"role": "A", "actual_model": "(dry-run)", "is_fallback": False,
                     "verdict": "unclear", "reasoning": "synthetic"},
                ],
            }],
        }],
        "_dry_run": True,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Local Mode C coverage harness (persists by default)")
    ap.add_argument("--step", required=False, default="adhoc",
                    help="step number, names the output directory (e.g. 491)")
    ap.add_argument("--fixture", default="atlas",
                    help="fixture key (%s) or a path" % "/".join(sorted(FIXTURES)))
    ap.add_argument("--n", type=int, default=1, help="number of runs")
    ap.add_argument("--gate-attempts", type=int, default=4,
                    help="max extraction-gate attempts per run before giving up (default 4). "
                         "A GateAbortError is an extraction-shape failure, not a pipeline "
                         "fault; retrying re-extracts. Nothing is tuned between attempts.")
    ap.add_argument("--notes", default=None, help="free text stored in index.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="persist a synthetic result; makes no provider calls")
    ap.add_argument("--list-fixtures", action="store_true")
    args = ap.parse_args(argv)

    if args.list_fixtures:
        print("known keys: %s" % ", ".join(sorted(FIXTURES)))
        if os.path.isdir(FIXTURE_DIR):
            print("files in %s:" % FIXTURE_DIR)
            for f in sorted(os.listdir(FIXTURE_DIR)):
                print("  " + f)
        return 0

    if args.dry_run:
        out, rows = run_and_persist(
            _synthetic_result, step=args.step, label="dryrun", n=args.n,
            notes=args.notes or "dry run -- synthetic result, no provider calls",
        )
        print("\ndry run persisted to %s" % out)
        return 0

    keys = bootstrap_env()
    if not keys:
        raise SystemExit(
            "no *_API_KEY loaded. Expected them in the .env named in CLAUDE.md; "
            "a real run cannot proceed without keys."
        )
    print("[run_mode_c] keys loaded: %s" % ", ".join(sorted(keys)))

    tenant_path = resolve_fixture(args.fixture)
    print("[run_mode_c] fixture: %s" % tenant_path)
    print("[run_mode_c] runs: %d  (~97 provider calls and ~15-17 min EACH)" % args.n)

    from cam.adapters.lease_review.lease_adapter import (
        run_lease_coverage_only, GateAbortError,
    )

    import json as _json
    import re as _re

    def _failed_lps(msg):
        """Pull the failed-LP list out of a GateAbortError message."""
        m = _re.search(r"Failed LPs: \[([^\]]*)\]", msg)
        return _re.findall(r"'([^']+)'", m.group(1)) if m else []

    _abort_dir = {"path": None}       # set by run_and_persist's first print

    def _dump_aborts(i, aborts):
        """Persist the abort history for a run that produced no result at all."""
        d = _abort_dir["path"]
        if not d:
            return
        try:
            with open(os.path.join(d, "run_%02d_gate_aborts.json" % i),
                      "w", encoding="utf-8") as f:
                _json.dump({"run": i, "attempts": len(aborts), "aborts": aborts},
                           f, indent=2, ensure_ascii=False)
            print("[run_mode_c] abort history persisted (%d attempts)" % len(aborts),
                  flush=True)
        except Exception as e:
            print("[run_mode_c] could not persist abort history: %s" % str(e)[:160],
                  flush=True)

    def one(i):
        """One run, retrying only on a gate abort. Nothing is tuned between attempts."""
        aborts = []
        for attempt in range(1, args.gate_attempts + 1):
            try:
                res = run_lease_coverage_only(
                    tenant_path=tenant_path,
                    run_id="s%s_%s_r%02d_a%d" % (args.step, args.fixture, i, attempt),
                    config={},          # production defaults -- do not tune here
                )
            except GateAbortError as e:
                aborts.append({"attempt": attempt, "error": str(e)[:500],
                               "failed_lps": _failed_lps(str(e))})
                print("[run_mode_c] run %d attempt %d: GATE ABORT -- %s"
                      % (i, attempt, str(e)[:200]), flush=True)
                if attempt == args.gate_attempts:
                    # Step 492: on a total abort no result exists, so the
                    # per-attempt history had nowhere to live and survived only
                    # in stdout -- the exact loss Step 490 exists to prevent.
                    # Write it beside the run before re-raising.
                    _dump_aborts(i, aborts)
                    raise                      # store records it as EXCEPTION
                continue
            # Record the abort history ON the result so it persists with the run.
            res["_harness_gate_attempts"] = attempt
            res["_harness_gate_aborts"] = aborts
            if aborts:
                print("[run_mode_c] run %d completed on attempt %d after %d abort(s)"
                      % (i, attempt, len(aborts)), flush=True)
            return res

    out, rows = run_and_persist(
        one, step=args.step, label="%s-modec" % args.fixture, n=args.n,
        notes=args.notes,
        on_dir=lambda d: _abort_dir.__setitem__("path", d),
    )

    ok = [r for r in rows if r.get("outcome") == "ok"]
    print("\n%d/%d runs persisted to %s" % (len(ok), args.n, out))
    for r in rows:
        c = r.get("census") or {}
        print("  run %s: %s calls=%s degraded=%s stubs=%s contradictions=%s"
              % (r.get("run"), r.get("outcome"), c.get("api_calls_total"),
                 c.get("run_degraded"), c.get("stub_count"),
                 c.get("provenance_contradictions")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
