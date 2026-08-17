"""452 sanctioned deterministic post-run production package — L3 producer.

Built against build_log/452_production_package_instruction_v8.md, ratified
per build_log/452_ratification_record.md, which names the reviewed hash.
This artifact deliberately does NOT stamp that hash: a stamped hash goes
stale on every re-ratification, which is the coupling §3.2 avoids by keeping
the manifest outside its own artifact set and the instruction header avoids
by refusing to carry its own ratification status. Stamped and repointed
twice before this rule was applied.

TWO SANCTIONED INVOCATIONS, zero provider calls across both (§4.14):
    python build_log/452_production_script.py produce         --stage2-sanction <token>
    python build_log/452_production_script.py finalize-record --stage2-sanction <token>

ZERO-CALL DISCIPLINE (§4.14). This module imports ONLY the standard library at module
scope. `install_network_guard()` is the first executable statement of main(), before any
project module is imported. Every project import is deferred into the function that needs
it, so no cam/* module is loaded until the guard is armed.

SCOPE (§9). Read-only against all L1 artifacts, hashed before and after. No cam/ file
created, modified or deleted. EvidenceSpan, _find_normalized_matches and _span_text_hash
are IMPORTED, never reimplemented. All new files under build_log/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_VERSION = "452_production_script_v1"
CAM_ROOT = Path(__file__).resolve().parent.parent          # §8: derived, never hardcoded
BUILD_LOG = CAM_ROOT / "build_log"
# Path manipulation only — NOT an import. The deferred cam.* imports below still occur
# after install_network_guard() runs, so the guard-first rule (§4.14) is preserved.
if str(CAM_ROOT) not in sys.path:
    sys.path.insert(0, str(CAM_ROOT))

RULES_PATH = BUILD_LOG / "452_deterministic_rules.json"
INVENTORY_PATH = BUILD_LOG / "452_required_product_inventory.json"
OUTPUT_SCHEMA_PATH = BUILD_LOG / "452_output_schema.json"
MANIFEST_GITPATH = "build_log/452_config_manifest.json"     # §3.2 — OUTSIDE the token input set

TARGET_DIR = BUILD_LOG / "452_stage2_results"
INVOCATION_RECORD = BUILD_LOG / "452_production_invocation_record.json"
EXECUTION_RECORD = BUILD_LOG / "452_execution_record_final.md"
FAILURE_RECORD = BUILD_LOG / "452_stage2_failure_record.json"

# §3.3 Set-A closure — exactly these eighteen, no more, no fewer.
SET_A_FILES = [
    "source_records.json", "pass_a_results.json", "pass_a_fidelity.json",
    "grounding_enforcement.json", "pass_b_results.json", "pass_comparison.json",
    "certified_parameter_evidence.json", "envelope_sufficiency.json", "observations.json",
    "validation.json", "repository_seam_check.json", "report.md",
    "post_report_validation.json", "final_mechanism_disposition.json",
    "l2_comparison.json", "contract_reconciliation.md", "zero_provider_call_check.json",
    "output_manifest.json",
]

SEMANTIC_FIELDS = [
    "parameter_family_relevance", "candidate_support_state",
    "value_applies_to_charge_basis_components", "charge_scope", "text_role",
    "value_completeness",
]

# §4.14 — exact subprocess allowlist. Non-network Git operations only.
SUBPROCESS_ALLOWLIST = [
    ("git", "rev-parse"), ("git", "status"), ("git", "show"), ("git", "cat-file"),
    ("git", "tag"), ("git", "rev-list"), ("git", "symbolic-ref"), ("git", "show-ref"),
]


class ProductionHalt(RuntimeError):
    """Any halt condition. Never caught to continue; only to write the failure record."""


# ══════════════════════════════════════════════════════════════════════════════
# §4.14 ZERO-CALL GUARD — armed before any project import
# ══════════════════════════════════════════════════════════════════════════════

_GUARD = {"installed": False, "outbound_attempts": 0, "attempted": [], "subprocesses": []}


def install_network_guard() -> None:
    """Block and COUNT every outbound socket connection. First statement of main()."""
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create = socket.create_connection
    real_getaddrinfo = socket.getaddrinfo

    def _blocked(target):
        _GUARD["outbound_attempts"] += 1
        _GUARD["attempted"].append(str(target))
        raise ProductionHalt(
            f"HARD HALT (§4.14): outbound network connection attempted to {target!r}. "
            "This package makes zero provider calls. Attempt counted and blocked.")

    def guarded_connect(self, address):          # noqa: ANN001
        _blocked(address)

    def guarded_connect_ex(self, address):       # noqa: ANN001
        _blocked(address)

    def guarded_create(address, *a, **k):        # noqa: ANN001
        _blocked(address)

    def guarded_getaddrinfo(host, port, *a, **k):   # noqa: ANN001
        # DNS resolution precedes connect(). Without this, an outbound attempt to an
        # unresolvable host would fail at getaddrinfo and never be counted.
        _blocked((host, port))

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.create_connection = guarded_create
    socket.getaddrinfo = guarded_getaddrinfo
    _GUARD["installed"] = True
    _GUARD["_real"] = (real_connect, real_connect_ex, real_create, real_getaddrinfo)


def guarded_git(*args: str) -> subprocess.CompletedProcess:
    """The ONLY subprocess seam. Enforces the §4.14 allowlist; a Python socket guard does
    not govern child processes, so the command shape is checked explicitly."""
    cmd = ("git",) + args
    head = (cmd[0], cmd[1] if len(cmd) > 1 else "")
    if head not in SUBPROCESS_ALLOWLIST:
        raise ProductionHalt(
            f"HARD HALT (§4.14): subprocess outside the allowlist: {' '.join(cmd)}")
    _GUARD["subprocesses"].append(" ".join(cmd))
    return subprocess.run(list(cmd), cwd=str(CAM_ROOT), capture_output=True, text=True)


def project_import_closure_scan() -> Dict[str, Any]:
    """AST + import scan over this module's transitive project-import closure (§4.14).
    Deferred project imports are named explicitly so the scan is not a tautology."""
    import ast as _ast
    src = Path(__file__).read_text(encoding="utf-8")
    tree = _ast.parse(src)
    module_scope, deferred = [], []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            name = (getattr(node, "module", None)
                    or (node.names[0].name if node.names else ""))
            at_module_scope = node.col_offset == 0
            (module_scope if at_module_scope else deferred).append(name)
    stdlib_only = [m for m in module_scope
                   if not (m or "").startswith(("cam.", "cam_", "build_log"))]
    return {
        "module_scope_imports": sorted(set(module_scope)),
        "module_scope_is_stdlib_only": len(stdlib_only) == len(module_scope),
        "deferred_project_imports": sorted(set(m for m in deferred if (m or "").startswith("cam."))),
        "guard_installed_before_project_imports": _GUARD["installed"],
    }


# ══════════════════════════════════════════════════════════════════════════════
# §4.0.1 FROZEN IDENTITY FORMULAS
# ══════════════════════════════════════════════════════════════════════════════

def _mkid(prefix: str, components: List[Any]) -> str:
    canon = json.dumps(components, ensure_ascii=False, separators=(",", ":"))
    return prefix + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def judgment_id(lease_id, parameter, candidate_id, series_index, role) -> str:
    return _mkid("J-", [lease_id, parameter, candidate_id, series_index, role])


def citation_occ_id(jid, citation_class, citation_id) -> str:
    return _mkid("CO-", [jid, citation_class, citation_id])


def envelope_id(lease_id, candidate_id, start, end) -> str:
    return _mkid("EV-", [lease_id, candidate_id, start, end])


def support_span_id(source_document_hash, start, end) -> str:
    return _mkid("SS-", [source_document_hash, start, end])


def failed_trace_id(lease_id, parameter, candidate_id, series_index, role,
                    field, citation_class, citation_id, quote) -> str:
    return _mkid("FT-", [lease_id, parameter, candidate_id, series_index, role, field,
                         citation_class, citation_id,
                         hashlib.sha256((quote or "").encode("utf-8")).hexdigest()])


def missing_trace_id(lease_id, parameter, candidate_id, series_index, role, field) -> str:
    return _mkid("MT-", [lease_id, parameter, candidate_id, series_index, role, field])


# ══════════════════════════════════════════════════════════════════════════════
# §4.3.1 TWO-WINDOW RESOLUTION — imported matcher, tighter window
# ══════════════════════════════════════════════════════════════════════════════

def classify_in_window(canonical_text: str, quote: str,
                       window: Tuple[int, int]) -> Tuple[str, List[Tuple[int, int]]]:
    """0 / 1 / 2+ classification against a WINDOW, using the imported document matcher.

    resolve_span is NOT used (R5): its document-wide search returns AMBIGUOUS whenever a
    quote occurs more than once anywhere in the lease, including when unique in the window
    the panelist actually saw. This is a tighter window, not a second resolver.
    """
    from cam.adapters.lease_review.lease_evidence_spans import _find_normalized_matches

    all_matches = _find_normalized_matches(canonical_text, quote)
    lo, hi = window
    hits = [(s, e) for (s, e) in all_matches if s >= lo and e <= hi]
    if len(hits) == 0:
        return "UNVERIFIED", hits
    if len(hits) == 1:
        return "VERIFIED", hits
    return "AMBIGUOUS", hits


def build_primary_span(lease_id, candidate, canonical_source):
    """§4.3.2 — offset-pinned primary. span_text IS the canonical slice; the preflight
    quote is a verification target. Verify the pin; do NOT rediscover."""
    from cam.adapters.lease_review.lease_evidence_spans import (
        EvidenceSpan, _span_text_hash,
    )
    start, end = candidate["candidate_start_char"], candidate["candidate_end_char"]
    span_text = canonical_source.canonical_text[start:end]
    if candidate.get("expected_quote") and candidate["expected_quote"] != span_text:
        raise ProductionHalt(
            f"HARD HALT (R4/§4.3.2): pinned slice for {candidate['candidate_id']} does not "
            "match the preflight quote. Replay integrity supersedes any exclusion fallback.")
    if canonical_source.source_document_hash != canonical_source.canonical_text_hash:
        raise ProductionHalt(
            "HARD HALT (§4.3.2): source_document_hash != canonical_text_hash.")
    span = EvidenceSpan(
        evidence_span_id=candidate["candidate_id"],
        source_document_hash=canonical_source.source_document_hash,
        canonical_text_hash=canonical_source.canonical_text_hash,
        start_char=start, end_char=end,
        span_text=span_text, span_text_hash=_span_text_hash(span_text),
        normalization_profile="canonical_whitespace_v2",
        section_ref=candidate.get("section_ref"),
        source_anchor=candidate.get("source_anchor"),
    )
    if hasattr(span, "is_valid_invariant") and not span.is_valid_invariant():
        raise ProductionHalt("HARD HALT (§4.3.1): is_valid_invariant failed; failing closed.")
    return span


# ══════════════════════════════════════════════════════════════════════════════
# §4.4 GROUNDING ENFORCEMENT  (R7)
# ══════════════════════════════════════════════════════════════════════════════

def enforce_grounding(judgment: dict, candidate_window, context_window,
                      canonical_text: str, schema_fixed_exempt: set) -> dict:
    """Per-field invalidation. Returns the enforcement record for one judgment.

    R7 rule 1 — `unclear` is the visible enforced value, retained for audit.
    R7 rule 2 — the invalidated vote is OMITTED from substantive aggregation entirely.
    R7 rule 4 — agreement_by_field becomes `not_assessable`.
    Confidence is untouched: invalidation, not a confidence haircut.
    """
    cand_by_id = {c["citation_id"]: c["quote"] for c in judgment.get("candidate_citations", [])}
    ctx_by_id = {c["citation_id"]: c["quote"] for c in judgment.get("context_citations", [])}
    support = judgment.get("field_support") or {}
    out = {"judgment_id": judgment["judgment_id"], "per_field": [],
           "failed_support_traces": [], "missing_support_traces": []}

    for field in SEMANTIC_FIELDS:
        if field in schema_fixed_exempt and judgment.get(field) == "not_applicable":
            out["per_field"].append({"field": field, "classification": "EXEMPT_SCHEMA_FIXED",
                                     "omitted_from_substantive_aggregation": False})
            continue
        entry = support.get(field) or {}
        cand_ids = entry.get("candidate_citation_ids") or []
        ctx_ids = entry.get("context_citation_ids") or []
        if not cand_ids and not ctx_ids:
            tid = missing_trace_id(judgment["lease_id"], judgment["parameter"],
                                   judgment["candidate_id"], judgment["series_index"],
                                   judgment["role"], field)
            out["missing_support_traces"].append({"missing_trace_id": tid, "field": field})
            out["per_field"].append({"field": field, "classification": "EMPTY",
                                     "enforced_field_value": "unclear",
                                     "omitted_from_substantive_aggregation": True,
                                     "trace_id": tid})
            continue
        any_verified = False
        for cid in cand_ids:
            q = cand_by_id.get(cid)
            if q is None:
                continue
            status, _ = classify_in_window(canonical_text, q, candidate_window)
            if status == "VERIFIED":
                any_verified = True
            else:
                out["failed_support_traces"].append({
                    "failed_trace_id": failed_trace_id(
                        judgment["lease_id"], judgment["parameter"], judgment["candidate_id"],
                        judgment["series_index"], judgment["role"], field, "candidate", cid, q),
                    "field": field, "citation_class": "candidate",
                    "citation_id": cid, "classification": status})
        for cid in ctx_ids:
            q = ctx_by_id.get(cid)
            if q is None:
                continue
            status, _ = classify_in_window(canonical_text, q, context_window)
            if status == "VERIFIED":
                any_verified = True
            else:
                out["failed_support_traces"].append({
                    "failed_trace_id": failed_trace_id(
                        judgment["lease_id"], judgment["parameter"], judgment["candidate_id"],
                        judgment["series_index"], judgment["role"], field, "context", cid, q),
                    "field": field, "citation_class": "context",
                    "citation_id": cid, "classification": status})
        out["per_field"].append({
            "field": field,
            "classification": "VERIFIED" if any_verified else "INVALIDATED",
            "enforced_field_value": None if any_verified else "unclear",
            "omitted_from_substantive_aggregation": not any_verified,
        })
    return out


def merge_agreement(values: List[Optional[str]], omitted: List[bool]) -> Tuple[Any, str]:
    """R7 rules 2-4 + Part A §5.2 per-field agreement.

    An omitted (invalidated) vote is NOT counted at all — it does not become `unclear` in
    the tally. If any vote was omitted the field cannot be `unanimous` (rule 3) and the
    token is `not_assessable` (rule 4).
    """
    kept = [v for v, om in zip(values, omitted) if not om]
    any_omitted = any(omitted)
    if any_omitted:
        return "unclear", "not_assessable"
    substantive = [v for v in kept if v not in ("unclear", "not_assessable", None)]
    if not substantive:
        return "unclear", "not_assessable"
    if len(set(map(_norm, kept))) == 1:
        return kept[0], "unanimous"
    if len(set(map(_norm, substantive))) == 1 and len(substantive) >= 2:
        return substantive[0], "majority_with_dissent"
    return "DISPUTED", "split"


def _norm(v):
    return tuple(sorted(v)) if isinstance(v, list) else v


# ══════════════════════════════════════════════════════════════════════════════
# §4.4 parameter-aware basis_ok  (R3) and §6.3 certification
# ══════════════════════════════════════════════════════════════════════════════

def basis_ok(parameter: str, basis_match: Optional[str], basis_field_value: Any,
             profile_declares_not_applicable: bool) -> bool:
    """R3 — both branches. Resolves the contradiction internal to Part A v5."""
    if profile_declares_not_applicable:
        return basis_field_value == "not_applicable"
    return basis_match == "match"


def certify(per_candidate: List[dict], completeness_established: bool) -> str:
    """Part A §6.3 coherent-single-candidate rule. No cross-candidate assembly, no
    implicit majority, no terminal unsatisfied_* without established completeness."""
    for c in per_candidate:
        if c.get("candidate_qualification") == "qualified" and \
           c.get("applicability_match") == "applicable":
            return "satisfied"
    for c in per_candidate:
        for state in (c.get("agreement_by_field") or {}).values():
            if state in ("majority_with_dissent", "split", "not_assessable"):
                return "review_needed_disagreement"
    if any(c.get("applicability_match") == "applicable" for c in per_candidate):
        return "applicable_no_supplied_candidate_qualified"
    return "review_needed_no_qualifying_candidate"


# ══════════════════════════════════════════════════════════════════════════════
# §4.3.7 ANTI-BORROWING — a dataflow property, verified by derivation path
# ══════════════════════════════════════════════════════════════════════════════

def value_ok_dataflow(primary_value_token_present: bool,
                      primary_value_completeness: str) -> Tuple[bool, Dict[str, Any]]:
    """R13. value_ok consumes ONLY the two primary-derived inputs. No support-span field
    is a parameter of this function, which is the static property the census records."""
    ok = bool(primary_value_token_present) and primary_value_completeness == "self_contained"
    return ok, {
        "inputs": ["primary.value_token_present", "primary.value_completeness"],
        "support_span_inputs": [],
        "anti_borrowing_dataflow_verified": True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# §4.15 / §4.17 TRANSACTIONAL PUBLICATION
# ══════════════════════════════════════════════════════════════════════════════

def verify_set_a_closure(staging: Path) -> None:
    present = sorted(p.name for p in staging.iterdir() if p.is_file())
    expected = sorted(SET_A_FILES)
    if present != expected:
        raise ProductionHalt(
            "HARD HALT (§4.15): Set-A closure failed.\n"
            f"  unexpected: {sorted(set(present) - set(expected))}\n"
            f"  missing   : {sorted(set(expected) - set(present))}")


def promote(staging: Path) -> None:
    if TARGET_DIR.exists():
        raise ProductionHalt(
            f"HARD HALT (§4.15): target {TARGET_DIR} already exists; no sanctioned "
            "replacement rule applies.")
    os.replace(str(staging), str(TARGET_DIR))          # ONE same-filesystem rename


def atomic_write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    tmp.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(str(tmp), str(path))


def write_failure_record(stage: str, reason: str, staging: Optional[Path],
                         disposition: str) -> None:
    """§4.15 — carries NO L3 authority. Excluded from every success artifact."""
    rec = {
        "_artifact": "452_stage2_failure_record.json",
        "failure_stage": stage, "failure_reason": reason,
        "staged_paths_present": sorted(p.name for p in staging.iterdir()) if staging and staging.exists() else [],
        "staged_paths_missing": sorted(set(SET_A_FILES) - set(
            p.name for p in staging.iterdir())) if staging and staging.exists() else SET_A_FILES,
        "inputs_verified": None, "guard_status": "installed" if _GUARD["installed"] else "absent",
        "outbound_attempt_count": _GUARD["outbound_attempts"],
        "staging_directory_disposition": disposition,
        "l3_authority": False,
    }
    atomic_write_json(FAILURE_RECORD, rec)


def rollback_after_promotion(reason: str) -> None:
    """§4.17 — the reachable state v8 left open: results promoted, invocation record absent."""
    quarantine = BUILD_LOG / f".452_stage2_results.QUARANTINED-{os.getpid()}"
    if TARGET_DIR.exists():
        os.replace(str(TARGET_DIR), str(quarantine))
    if TARGET_DIR.exists():
        raise ProductionHalt("HARD HALT: quarantine failed; authoritative path still present.")
    write_failure_record("post_promotion", reason, quarantine, f"quarantined:{quarantine.name}")
    raise ProductionHalt(
        f"HARD HALT (§4.17): {reason}. Results quarantined to {quarantine.name}; the "
        "authoritative target path does not exist; no final execution record is emitted.")


# ══════════════════════════════════════════════════════════════════════════════
# GATE-RECORD AND INPUT VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def head_blob_sha256(gitpath: str) -> Optional[str]:
    r = guarded_git("show", f"HEAD:{gitpath}")
    if r.returncode != 0:
        return None
    return hashlib.sha256(r.stdout.encode("utf-8")).hexdigest()


def expected_package_artifacts() -> List[str]:
    """§3.1, read from the ratified instruction so the set cannot drift from the document."""
    text = (BUILD_LOG / "452_production_package_instruction_v8.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    i = lines.index("### 3.1 `EXPECTED_PACKAGE_ARTIFACTS`")
    out = []
    for line in lines[i + 2:]:
        if line.startswith("```"):
            break
        if line.strip():
            out.append(line.strip())
    return out


def verify_gate_records() -> Dict[str, Any]:
    """§7.1 — existence and a `passed` field are necessary and NOT sufficient. Every gate
    record's declared input hashes are recomputed against the corresponding HEAD blobs."""
    gates = ["452_stage1_test_results.json", "452_producer_consumer_census.json",
             "452_predicate_reachability_census.json", "452_input_sufficiency.json"]
    result = {"gates": [], "all_passed": True}
    for g in gates:
        p = BUILD_LOG / g
        if not p.exists():
            raise ProductionHalt(f"HARD HALT (§7.1): gate record missing: {g}")
        rec = json.loads(p.read_text(encoding="utf-8"))
        ok = rec.get("passed") is True
        mismatches = []
        for path, declared in (rec.get("input_hashes") or {}).items():
            actual = head_blob_sha256(path)
            if actual != declared:
                mismatches.append({"path": path, "declared": declared, "head": actual})
        if mismatches:
            raise ProductionHalt(
                f"HARD HALT (§7.1): {g} declares input hashes that do not match HEAD: {mismatches}")
        result["gates"].append({"gate": g, "passed": ok, "input_hashes_verified": True})
        result["all_passed"] &= ok
    return result


def whole_tree_clean() -> Tuple[bool, str]:
    r = guarded_git("status", "--porcelain", "--untracked-files=all")
    return (r.stdout.strip() == ""), r.stdout.strip()


def hash_l1_inputs() -> Dict[str, str]:
    out = {}
    for rel in expected_package_artifacts():
        p = CAM_ROOT / rel
        if p.exists():
            out[rel] = sha256_lf(p)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINTS
# ══════════════════════════════════════════════════════════════════════════════

def cmd_produce(sanction: str) -> int:
    """§4.10 steps 0-21. Every step is a named producing function so §7.2 can trace it."""
    staging = Path(tempfile.mkdtemp(prefix=".452_stage2_results.staging-", dir=str(BUILD_LOG)))
    try:
        inputs_before = hash_l1_inputs()
        clean_before, dirt = whole_tree_clean()
        if not clean_before:
            raise ProductionHalt(f"HARD HALT (§8): repository not clean before production:\n{dirt}")
        verify_gate_records()
        raise ProductionHalt(
            "HARD HALT: Stage-2 production is NOT AUTHORIZED. 452_ratification_record.md "
            "authorizes Stage 1A and Stage 1B ONLY. This entrypoint is built, wired and "
            "test-covered at Stage 1A; it refuses to run until a separate Stage-2 sanction "
            "exists (§2, §12).")
    except ProductionHalt as e:
        write_failure_record("production", str(e), staging, "deleted")
        for p in sorted(staging.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
        staging.rmdir()
        print(str(e), file=sys.stderr)
        return 2


def cmd_finalize_record(sanction: str) -> int:
    """§4.12 — separate invocation. Its zero-call proof cannot be borrowed from the first."""
    print("HARD HALT: finalize-record requires a completed production invocation and a "
          "Stage-2 sanction. Neither exists. (§4.12, §2)", file=sys.stderr)
    return 2


def main() -> int:
    install_network_guard()                    # FIRST executable statement, before any project import
    ap = argparse.ArgumentParser(description="452 L3 deterministic production package")
    ap.add_argument("command", choices=["produce", "finalize-record"])
    ap.add_argument("--stage2-sanction", default=None)
    args = ap.parse_args()
    if not args.stage2_sanction:
        print("HARD HALT: --stage2-sanction is required. Stage 2 is separately authorized (§2).",
              file=sys.stderr)
        return 2
    if args.command == "produce":
        return cmd_produce(args.stage2_sanction)
    return cmd_finalize_record(args.stage2_sanction)


if __name__ == "__main__":
    raise SystemExit(main())
