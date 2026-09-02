"""Step 524 — qualifier cross-reference. Annotation only; never evidence.

WHAT THIS IS FOR
----------------
Step 460 found §11.3 (Limitation of Liability) sitting 239 characters past the
end of the evidence handed to the LP-27 panel. The panel reported "monetary
damages: explicitly present, high confidence" without seeing the clause that
caps the remedy. It is not a bad span: elicitation retrieves clauses matching an
ELEMENT DESCRIPTION, and no LP-27 element describes a limitation, so the
qualifier is structurally unreachable from that LP.

Steps 466/467 ruled out containing-section expansion (measured PRECISION
REGRESSION: element 4 moved from a correct `missing` to `disputed`, stably over
two runs). Step 468 ruled out prompt-level strictness as a class. Step 523
concluded the remaining lever is to stop trying to make the panel see it and
instead tell the reader it did not.

THE INVARIANT THAT MAKES THIS SAFE
----------------------------------
**Nothing here is ever written to `tenant_text` or to `span_evidence`.** The
panel's input is byte-identical with this module enabled or disabled, so
precision over previously-clean elements cannot regress -- by construction, not
by measurement. Step 524 verified it anyway, against the Step-522 baseline.

IF YOU ARE EDITING THIS FILE: the moment any output of this module reaches the
text a panel reasons over, that guarantee is void and the Step-466 regression is
back in scope. This must remain a read-only observer.

WHY DETERMINISTIC, AND WHY NOT A MODEL CALL
-------------------------------------------
Step 523 recommended a second, limitation-targeted elicitation pass -- one
provider call per document. **The Step-524 measurement retired that proposal.**
On the Step-522 Atlas run:

  * §11.3 appears in NO span_evidence_records -- 31 records across the four
    seamed LPs, zero overlapping [15490, 15748];
  * §11.3 DOES appear in LP-13 "Indemnification & Liability" tenant_text, whose
    coverage_state is `covered`.

So the pipeline already retrieves the clause and already judges it -- under a
different LP. A model call to find text the pipeline has in hand would be
spending tokens to rediscover a fact already in the result.

A deterministic scan over the canonical document has a property a model call
cannot have: **every hit is a verbatim substring with offsets, resolvable
against the source hash. It cannot fabricate a clause.** Given the output is an
annotation shown to a reader and never a verdict, an auditable detector with a
known-incomplete recall is the better trade than an unauditable one with unknown
recall.

It also scans the WHOLE document rather than the ~67% covered by the union of
extraction buckets, so a limitation in a section no LP retrieved is still found.
The cross-reference fact -- that another LP did get the clause -- is reported as
an attribute (`also_retrieved_under`), not used as the trigger.

GENERALITY LIMIT — READ THIS BEFORE TRUSTING THE OUTPUT
-------------------------------------------------------
Atlas puts its cap 239 characters from the finding. **Proximity is a coincidence
of that fixture and is NOT how this pass works**: detection is document-wide and
linking is by SUBJECT (a qualifier's subject keywords against an LP's element
labels). `distance_chars` is reported for the reader's benefit and is never a
linking criterion. A cap in a miscellaneous article, an exculpation clause, or a
non-recourse provision links the same way as an adjacent one.

What it does NOT reach, stated plainly:
  * a qualifier expressed without any of the surface forms in `_PATTERNS`;
  * a qualifier whose effect is semantic rather than lexical -- e.g. a definition
    of "Landlord" that excludes successors;
  * anything incorporated by reference (an SNDA, a rider not in the text): the
    document does not contain the words, so nothing can match them.

MEASUREMENT STATUS: exercised on ONE document. divall parses at zero headings
and 21 of the 32 corpus fixtures derive from a single synthetic template, so the
corpus cannot establish generality. Recall is unmeasured. A miss leaves the
report exactly as it was before this module existed -- it fails safe -- but
"fails safe" is not "works".
"""
from typing import Any, Dict, List, Optional
import re

# Surface forms of a remedy/liability qualifier. Deliberately narrow: a false
# positive costs a reader one line of noise, a false negative costs nothing that
# was not already lost, and a broad net would bury the signal.
_PATTERNS = [
    ("damages_cap",      r"consequential,?\s+indirect|indirect,?\s+consequential|punitive,?\s+or\s+special|special\s+damages|consequential\s+damages"),
    ("liability_cap",    r"liability\s+shall\s+be\s+limited|limited\s+to\s+(?:\w+['’]s\s+)?interest\s+in|shall\s+not\s+be\s+liable|in\s+no\s+event\s+shall"),
    ("exclusive_remedy", r"sole\s+(?:and\s+exclusive\s+)?remedy|exclusive\s+remedy|only\s+remedy"),
    ("non_recourse",     r"no\s+personal\s+liability|without\s+recourse|non-?recourse|exculpat"),
    ("waiver",           r"waives?\s+(?:any|all)\s+(?:right|claim)|hereby\s+waives"),
]

# Subject terms per qualifier kind, matched WORD-BOUNDED against an LP's element
# labels. This is the LINKING rule -- subject, not distance.
#
# Word boundaries are load-bearing, not tidiness. The first draft used bare
# substrings and produced two false positives that a reader would rightly call
# nonsense, both found by running it over the Step-522 Atlas result:
#   * "remed" matched LP-32's "Tenant's REMEDIATION obligation for contamination"
#     -- environmental cleanup is not a legal remedy;
#   * "liability" matched LP-08's "Commercial general LIABILITY minimum coverage"
#     -- an insurance product, not an allocation of liability.
# Bare "liability" is gone entirely for that reason; LP-27 still links through
# `damages`, `remedies` and `default`, so nothing was lost to remove it.
_SUBJECT_TERMS = {
    "damages_cap":      (r"damages", r"remedy|remedies", r"liable", r"default"),
    "liability_cap":    (r"damages", r"remedy|remedies", r"liable", r"indemnif\w*", r"default"),
    "exclusive_remedy": (r"remedy|remedies", r"terminat\w*", r"offset", r"self-help", r"default"),
    "non_recourse":     (r"damages", r"remedy|remedies", r"liable", r"default"),
    "waiver":           (r"waiv\w*", r"remedy|remedies", r"claim", r"default"),
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.;])\s+")


def _sentence_bounds(text: str, pos: int) -> tuple:
    """Offsets of the sentence containing `pos`. Quotes are whole sentences so a
    reader is never handed a fragment that changes meaning when completed."""
    start = text.rfind(". ", 0, pos)
    start = 0 if start < 0 else start + 2
    nl = text.rfind("\n", 0, pos)
    if nl > start:
        start = nl + 1
    end = text.find(". ", pos)
    end = len(text) if end < 0 else end + 1
    nl2 = text.find("\n", pos)
    if 0 <= nl2 < end:
        end = nl2
    return start, end


_SECTION_RE = re.compile(r"Section\s+(\d+\.\d+)", re.I)


def _section_ref_for(text: str, pos: int) -> Optional[str]:
    """Nearest preceding `Section N.N` heading. Reported for the reader's
    orientation; NOT used for linking, and None is an acceptable answer."""
    best = None
    for m in _SECTION_RE.finditer(text, 0, pos + 1):
        best = m
    return ("Section %s" % best.group(1)) if best else None


def detect_qualifiers(document_text: str) -> List[Dict[str, Any]]:
    """Every qualifier-shaped sentence in the document, with offsets.

    Pure and deterministic: same text in, same list out, no model, no network.
    """
    found: Dict[tuple, Dict[str, Any]] = {}
    for kind, pat in _PATTERNS:
        for m in re.finditer(pat, document_text, re.I):
            s, e = _sentence_bounds(document_text, m.start())
            quote = document_text[s:e].strip()
            if len(quote) < 25 or len(quote) > 700:
                continue
            key = (s, e)
            if key in found:
                # One sentence can match several patterns; keep every kind so
                # subject-linking sees all of them rather than the first.
                if kind not in found[key]["qualifier_kinds"]:
                    found[key]["qualifier_kinds"].append(kind)
                continue
            found[key] = {
                "qualifier_kinds": [kind],
                "start_char": s,
                "end_char": e,
                "section_ref": _section_ref_for(document_text, s),
                "quote": quote,
            }
    return [found[k] for k in sorted(found)]


def _lp_subject_terms(assessment: Dict[str, Any]) -> str:
    """The LP's own vocabulary: element labels plus the issue-area name.

    Element labels are the substantive part -- they are what the panel was asked
    about. The name is included because a non-305 LP has no element verdicts.
    """
    parts = [str(assessment.get("issue_area_name") or "")]
    for ev in (assessment.get("element_verdicts") or []):
        parts.append(str(ev.get("element_label") or ev.get("element_id") or ""))
    for lst in ("elements_found", "elements_missing"):
        for el in (assessment.get(lst) or []):
            parts.append(str(el))
    return " ".join(parts).lower()


def _subject_matches(kinds: List[str], terms: str) -> bool:
    for kind in kinds:
        for pat in _SUBJECT_TERMS.get(kind, ()):
            if re.search(r"\b(?:%s)\b" % pat, terms):
                return True
    return False


def _evidence_intervals(assessment, document_text):
    """The offsets this LP was ACTUALLY judged on, as a list of intervals.

    A list, not a hull. A seamed LP's evidence is several disjoint spans, and
    collapsing them to (min, max) claims the LP was judged on everything in
    between. That is not a cosmetic difference: with a hull, LP-12's evidence
    appeared to contain §11.3 and the annotation reported
    `also_retrieved_under: ['LP-12']` -- a false statement about what another
    provision was judged on, in a field a reader would rely on. Found by reading
    the output, not the code.
    """
    recs = assessment.get("span_evidence_records") or []
    offs = [(r["start_char"], r["end_char"]) for r in recs
            if r.get("start_char") is not None and r.get("end_char") is not None]
    if offs:
        return sorted(offs)
    tt = (assessment.get("tenant_text") or "").strip()
    if not tt:
        return []
    p = document_text.find(tt[:200])
    return [(p, p + len(tt))] if p >= 0 else []


def _contains(intervals, start, end):
    return any(s <= start and end <= e for s, e in intervals)


def _distance(intervals, start, end):
    if not intervals:
        return None
    return min(min(abs(start - e), abs(s - end)) for s, e in intervals)


def annotate_assessments(
    assessments: List[Dict[str, Any]],
    document_text: str,
) -> int:
    """Attach `qualifier_annotations` to assessments. Returns the count attached.

    MUTATES ONLY the annotation key. It never touches `tenant_text`,
    `span_evidence`, `element_verdicts`, `coverage_state`, `requires_attention`
    or `assessment_status` -- see the invariant at the top of this module.
    """
    if not assessments or not document_text:
        return 0

    quals = detect_qualifiers(document_text)
    if not quals:
        return 0

    # Which LP, if any, was handed each qualifier as part of its own evidence.
    # Reported as context ("another provision was judged on this text"); it is
    # NOT the trigger, so a qualifier no LP retrieved is still annotated.
    spans = {a.get("issue_area_id"): _evidence_intervals(a, document_text) for a in assessments}

    attached = 0
    for a in assessments:
        pid = a.get("issue_area_id")
        # An LP that was never judged has no finding for a qualifier to qualify.
        if (a.get("assessment_status") or "unset") != "assessed":
            continue
        terms = _lp_subject_terms(a)
        own = spans.get(pid) or []
        notes = []
        for q in quals:
            if _contains(own, q["start_char"], q["end_char"]):
                continue  # already inside this LP's evidence -- the panel saw it
            if not _subject_matches(q["qualifier_kinds"], terms):
                continue
            also = [
                opid for opid, sp in spans.items()
                if opid != pid and _contains(sp, q["start_char"], q["end_char"])
            ]
            notes.append({
                "qualifier_kinds": list(q["qualifier_kinds"]),
                "section_ref": q["section_ref"],
                "start_char": q["start_char"],
                "end_char": q["end_char"],
                "quote": q["quote"],
                # Reported, never used to link. Atlas's 239 characters are a
                # property of that document, not of the method.
                "distance_chars": _distance(own, q["start_char"], q["end_char"]),
                "also_retrieved_under": also,
                "link_basis": "subject",
                # The annotation asserts three checkable things and no more: the
                # clause exists at these offsets, it was not in this LP's
                # evidence, and it concerns the same subject. It does NOT assert
                # that it limits the finding -- the panel did not judge it and
                # neither did we.
                "weighed_by_panel": False,
            })
        if notes:
            a["qualifier_annotations"] = notes
            attached += 1
    return attached
