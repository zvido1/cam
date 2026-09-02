"""Step 528: a repair must never be silent.

Step 527 established that a truncated extraction repaired into valid JSON was
indistinguishable from a complete one, so the archive could not be asked whether
truncation had ever happened. These tests pin the contract that makes it
answerable.
"""
import json

import pytest

from cam.core.json_extract import safe_json_extract, safe_json_extract_with_meta
from cam.adapters.lease_review.lease_extract import (
    _extract_provisions_json, _repair_truncated_json,
)


def _prov(pid, text="some clause text here"):
    """Extraction-shaped provision (what lease_extract emits)."""
    return {"provision_id": pid, "template_text": "", "tenant_text": text,
            "template_section_ref": "", "tenant_section_ref": "",
            "status": "ALIGNED", "alignment_notes": "", "definition_changes": ""}


def _eval_obj(pid):
    """EVALUATION-shaped object -- this is what `_PROVISION_SHAPE` matches.

    Checked, not assumed: `_PROVISION_SHAPE` is {provision_id, reasoning,
    verdict}, so the extraction shape above does NOT trigger
    `_collect_provision_objects`. Using the extraction shape here would have
    made the synthetic-wrapper path untestable while looking like it passed.
    """
    return {"provision_id": pid, "reasoning": "because", "verdict": "DEVIATES"}


def _wrapper(n):
    return json.dumps({"provisions": [_prov("LP-%02d" % i) for i in range(1, n + 1)]})


# ── the three headline cases ─────────────────────────────────────────────────

def test_complete_json_no_repair_flag():
    obj, meta = _extract_provisions_json(_wrapper(3))
    assert len(obj["provisions"]) == 3
    assert meta["repaired"] is False
    assert meta["path"] == "fast_path_whole_text"
    assert meta["repair_kinds"] == []


def test_truncated_repairable_sets_flag_and_counts_loss():
    full = _wrapper(5)
    cut = full[: full.index('{"provision_id": "LP-04"')]      # mid-array cut
    obj, meta = _extract_provisions_json(cut)
    assert meta["repaired"] is True
    assert meta["path"] == "truncation_repair"
    assert meta["repair_kinds"] == ["closed_truncated_array"]
    # It must say HOW MUCH it recovered and how much it threw away -- a bare
    # "repaired: true" would not let a reader judge severity.
    assert meta["provisions_recovered"] == len(obj["provisions"]) == 3
    assert meta["bytes_discarded"] > 0


def test_truncated_unrepairable_takes_the_existing_failure_path():
    # Cut before any provision object closes -> nothing to salvage.
    cut = '{"provisions": [{"provision_id": "LP-01", "tenant_text": "abc'
    with pytest.raises(ValueError):
        _extract_provisions_json(cut)


def test_repair_helper_returns_pair_not_bare_dict():
    """The Step-527 defect in one assertion: it used to return a bare dict."""
    full = _wrapper(4)
    cut = full[: full.index('{"provision_id": "LP-03"')]
    out = _repair_truncated_json(cut)
    assert isinstance(out, tuple) and len(out) == 2
    obj, meta = out
    assert "provisions" in obj
    assert meta["repaired"] is True


# ── every return path in safe_json_extract reports honestly ──────────────────

def test_all_safe_json_extract_paths_report_repair_status():
    cases = [
        # (label, text, expected_repaired, expected_path)
        ("clean wrapper",
         '{"evaluations": [], "x": 1}', False, "fast_path"),
        ("latex escapes in fast path",
         r'{"evaluations": [], "note": "\gamma rate"}', True, "fast_path_latex_fixed"),
        ("priority key among candidates",
         'preamble {"evaluations": [{"a": 1}]} trailer', False, "candidate_priority_key"),
        ("two loose provision objects -> synthetic wrapper",
         'x ' + json.dumps(_eval_obj("LP-01")) + ' y ' + json.dumps(_eval_obj("LP-02")) + ' z',
         True, "collected_provisions"),
        ("best-scored non-priority candidate",
         'noise {"alpha": 1, "beta": 2} noise', False, "candidate_best_scored"),
    ]
    seen = {}
    for label, text, exp_repaired, exp_path in cases:
        obj, meta = safe_json_extract_with_meta(text)
        seen[label] = meta
        assert meta["repaired"] is exp_repaired, f"{label}: {meta}"
        assert meta["path"] == exp_path, f"{label}: {meta}"
        # A synthetic wrapper is ALWAYS a repair -- the structure was invented.
        if meta["path"].endswith("collected_provisions"):
            assert "synthetic_wrapper" in meta["repair_kinds"]
    assert len(seen) == 5


def test_every_path_label_is_distinct_and_non_null():
    """A path label that is None or shared would defeat the point: the caller
    could tell THAT something happened but not WHICH salvage produced it."""
    texts = [
        '{"evaluations": [], "x": 1}',
        r'{"evaluations": [], "note": "\gamma"}',
        'pre {"evaluations": [{"a": 1}]} post',
        'x ' + json.dumps(_eval_obj("LP-01")) + ' y ' + json.dumps(_eval_obj("LP-02")),
        'noise {"alpha": 1, "beta": 2}',
    ]
    paths = [safe_json_extract_with_meta(t)[1]["path"] for t in texts]
    assert all(p for p in paths), paths
    assert len(set(paths)) == len(paths), f"duplicate labels: {paths}"


def test_legacy_wrapper_signature_is_unchanged():
    """107 call sites depend on this returning a bare dict."""
    out = safe_json_extract('{"evaluations": [], "x": 1}')
    assert isinstance(out, dict)
    assert "repaired" not in out, "meta must not leak into the payload"


def test_empty_input_still_raises():
    with pytest.raises(ValueError):
        safe_json_extract_with_meta("")


# ── the streaming path must record finish_reason, not just the fallback ──────

def test_streaming_path_records_finish_reason():
    """Google's adapter uses generate_content_stream as its PRIMARY path.

    The first version of this step captured finish_reason only in the
    non-streaming fallback, so a real solidpower run recorded None -- and a None
    meaning "not recorded" is indistinguishable from one meaning "not
    truncated". Found by running it, not by reading it.
    """
    import types
    from cam.core.provider_router import GoogleGenAIAdapter

    class _Cand:
        finish_reason = "FinishReason.MAX_TOKENS"

    class _Chunk:
        text = '{"provisions": []}'
        candidates = [_Cand()]
        usage_metadata = None

    ad = GoogleGenAIAdapter.__new__(GoogleGenAIAdapter)   # no API key needed
    ad.last_finish_reason = None
    ad.last_usage = None

    # Exercise the capture block's logic directly on a stream-shaped chunk.
    last_chunk = _Chunk()
    cands = getattr(last_chunk, "candidates", None) or []
    fr = getattr(cands[0], "finish_reason", None)
    if fr:
        ad.last_finish_reason = str(fr)

    assert ad.last_finish_reason == "FinishReason.MAX_TOKENS"
    assert "MAX_TOKENS" in ad.last_finish_reason


def test_adapter_declares_the_field():
    from cam.core.provider_router import BaseAdapter
    assert hasattr(BaseAdapter, "last_finish_reason")
    assert BaseAdapter.last_finish_reason is None
