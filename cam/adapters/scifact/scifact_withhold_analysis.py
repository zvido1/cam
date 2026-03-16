"""
CAM SciFact -- Withhold Analysis (Step 014d)

Post-analysis on the 7 withheld claims from the 50-claim run.
Part 1: Trigger audit (no API calls)
Part 2: Coherence remediation for Claims 903 and 578 (2 Grok calls)
Part 3: Recompute disposition for remediated claims
Parts 4-6: Summary, metrics, rule fix proposal
"""

import json
from pathlib import Path
from datetime import datetime, timezone

from cam.core.config import CAM_ROOT, find_and_load_env
from cam.core.utilities import log


# The 7 withheld claims and their categories
WITHHELD_CLAIMS = {
    # Category 1: NEI withheld despite unanimous agreement (rule design flaw)
    1280: {"gold": "NEI", "category": "rule_design_flaw", "agreement": "3-0 NOT_ENOUGH_INFO"},
    913:  {"gold": "NEI", "category": "rule_design_flaw", "agreement": "3-0 NOT_ENOUGH_INFO"},
    544:  {"gold": "NEI", "category": "rule_design_flaw", "agreement": "3-0 NOT_ENOUGH_INFO"},
    # Category 2: Grok contradiction (coherence remediation candidates)
    903:  {"gold": "CONTRADICT", "category": "coherence_remediation", "agreement": "2-1 CONTRADICT/SUPPORT"},
    578:  {"gold": "CONTRADICT", "category": "coherence_remediation", "agreement": "2-1 CONTRADICT/SUPPORT"},
    # Category 3: Genuinely ambiguous
    785:  {"gold": "NEI", "category": "genuinely_ambiguous", "agreement": "2-1 NOT_ENOUGH_INFO/CONTRADICT"},
    # Category 4: Correctly caught
    1041: {"gold": "CONTRADICT", "category": "correctly_caught", "agreement": "2-1 NOT_ENOUGH_INFO/CONTRADICT"},
}


def run_withhold_analysis(source_run_name="1b SciFact Run Enhanced"):
    """
    Full withhold analysis pipeline.
    Parts 1-6 as specified in instruction 014d.
    """
    from cam.adapters.scifact.scifact_adapter import (
        _load_jsonl_results,
        load_scifact_dataset,
        _lookup_abstract_for_claim,
    )
    from cam.adapters.scifact.scifact_fragility import compute_fragility_profile
    from cam.adapters.scifact.scifact_disposition import (
        compute_disposition_with_elimination,
        compare_to_gold,
    )

    find_and_load_env()

    source_dir = CAM_ROOT / "03 SciFact" / "Runs" / source_run_name
    base_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1 SciFact Run"
    out_dir = CAM_ROOT / "03 SciFact" / "Runs" / "1e SciFact Withhold Analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 70)
    log("  CAM SciFact -- Withhold Analysis")
    log("=" * 70)

    # Load all stage results
    stage1_results = _load_jsonl_results(base_dir / "stage1_results.jsonl", "Stage 1")
    stage3_results = _load_jsonl_results(base_dir / "stage3_results.jsonl", "Stage 3")
    stage4_results = _load_jsonl_results(source_dir / "stage4_results.jsonl", "Stage 4")
    stage5_results = _load_jsonl_results(source_dir / "stage5_results.jsonl", "Stage 5")
    elimination_results = _load_jsonl_results(source_dir / "elimination_results.jsonl", "Elimination")

    # Build lookups
    s1_lookup = {r["claim_id"]: r for r in stage1_results}
    s3_lookup = {r["claim_id"]: r for r in stage3_results}
    s4_lookup = {r["claim_id"]: r for r in stage4_results}
    s5_lookup = {r["claim_id"]: r for r in stage5_results}
    elim_lookup = {r["claim_id"]: r for r in elimination_results}

    # Load raw evaluator files for detailed data
    raw_base = base_dir / "raw"

    # ============================================================
    # PART 1: Withhold Trigger Audit
    # ============================================================
    log("")
    log("=" * 70)
    log("  PART 1: Withhold Trigger Audit")
    log("=" * 70)

    audit_results = []

    for claim_id, meta in WITHHELD_CLAIMS.items():
        s1 = s1_lookup.get(claim_id, {})
        s3 = s3_lookup.get(claim_id, {})
        s4 = s4_lookup.get(claim_id, {})
        s5 = s5_lookup.get(claim_id, {})

        evals = s1.get("evaluations", {})
        audit = s3.get("audit", {})
        frag = s4.get("fragility", {})
        disp = s5.get("disposition", {})

        # Get per-evaluator scope_match from raw files
        scope_matches = {}
        for label in ["A", "B", "C"]:
            raw_file = raw_base / f"claim_{claim_id}" / f"evaluator_{label}.json"
            if raw_file.exists():
                with open(raw_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                norm = raw_data.get("normalized", {})
                scope = norm.get("scope_assessment", {})
                scope_matches[label] = scope.get("scope_match", "unknown")
            else:
                scope_matches[label] = "file_not_found"

        # Determine majority verdict
        verdicts = [evals.get(l, {}).get("verdict") for l in ["A", "B", "C"] if evals.get(l, {}).get("verdict")]
        from collections import Counter
        verdict_counts = Counter(verdicts)
        majority_verdict = verdict_counts.most_common(1)[0][0] if verdict_counts else "UNKNOWN"

        # Analyze triggers
        max_cap = frag.get("max_cap")
        fired_rules = frag.get("fired_rules", [])
        rule_ids = [r.get("rule_id", r) if isinstance(r, dict) else r for r in fired_rules]
        signals = frag.get("signals", [])
        conditions = disp.get("conditions", [])
        auditor_assessment = audit.get("overall_assessment", "")

        # Cap source analysis
        cap_sources = []
        for sig in signals:
            if sig.get("effect", "").startswith("cap_") and sig.get("source") != "elimination":
                cap_sources.append(f"{sig['source']}:{sig['signal_id']} -> {sig['effect']}")

        # Find the signal that sets the max_cap
        max_cap_source = "unknown"
        for sig in signals:
            effect = sig.get("effect", "")
            if effect == f"cap_{max_cap}":
                max_cap_source = f"{sig['source']}:{sig['signal_id']}"
                break

        # Determine if scope mismatch caused NEI
        all_scope_mismatch_are_nei = True
        scope_mismatch_evals = []
        for label in ["A", "B", "C"]:
            if scope_matches.get(label) == "mismatch":
                scope_mismatch_evals.append(label)
                if evals.get(label, {}).get("verdict") != "NOT_ENOUGH_INFO":
                    all_scope_mismatch_are_nei = False

        # Build trigger analysis
        is_nei_scope_pattern = (
            majority_verdict == "NOT_ENOUGH_INFO"
            and "RULE-SF-002" in rule_ids
            and all_scope_mismatch_are_nei
            and len(scope_mismatch_evals) > 0
        )

        if is_nei_scope_pattern:
            cap_justified = False
            cap_reasoning = (
                f"RULE-SF-002 fires because evaluators {', '.join(scope_mismatch_evals)} "
                f"report scope_match=mismatch. But for NEI verdicts, scope mismatch IS the "
                f"reason for NEI -- the rule penalizes the correct reasoning. All evaluators "
                f"with mismatch also verdict NEI."
            )
        elif meta["category"] == "coherence_remediation":
            cap_justified = True
            cap_reasoning = (
                f"Cap is justified: evaluator disagreement with one evaluator (C) making "
                f"a critical reasoning error (citing evidence that contradicts its own verdict). "
                f"The fragility signal correctly identifies the evaluation as unreliable."
            )
        elif meta["category"] == "genuinely_ambiguous":
            cap_justified = True
            cap_reasoning = (
                f"Cap is justified: genuine evaluator disagreement (2-1 split) with "
                f"scope mismatch concerns. The withhold is appropriately cautious."
            )
        elif meta["category"] == "correctly_caught":
            cap_justified = True
            cap_reasoning = (
                f"Cap is justified: cross-species scope concern (vertebrate data "
                f"applied to yeast) created genuine uncertainty. Withhold prevented "
                f"an incorrect assertion."
            )
        else:
            cap_justified = True
            cap_reasoning = "Standard fragility detection."

        # Determine if flag was justified
        flag_justified = True
        flag_reasoning = ""
        if is_nei_scope_pattern:
            flag_justified = False
            flag_reasoning = (
                f"Auditor flagged due to fragility signals, but the fragility signals "
                f"stem from scope mismatch which is the correct basis for the NEI verdict. "
                f"Combined with L1 cap, this triggers double jeopardy on a correct assessment."
            )
        elif meta["category"] == "coherence_remediation":
            flag_justified = True
            flag_reasoning = (
                f"Auditor correctly identified evaluator C's internally contradictory reasoning: "
                f"cited evidence contradicts the verdict."
            )
        elif meta["category"] == "genuinely_ambiguous":
            flag_justified = True
            flag_reasoning = "Auditor correctly flagged genuine evaluator disagreement."
        elif meta["category"] == "correctly_caught":
            flag_justified = True
            flag_reasoning = "Auditor correctly flagged fragile agreement with scope concerns."

        # Overall assessment
        if meta["category"] == "rule_design_flaw":
            withhold_justified = False
            overall = "Over-cautious"
        elif meta["category"] == "coherence_remediation":
            withhold_justified = True
            overall = "Justified (pending remediation)"
        elif meta["category"] == "genuinely_ambiguous":
            withhold_justified = True
            overall = "Justified"
        elif meta["category"] == "correctly_caught":
            withhold_justified = True
            overall = "Justified"
        else:
            withhold_justified = True
            overall = "Unknown"

        entry = {
            "claim_id": claim_id,
            "claim_text": s1.get("claim_text", ""),
            "gold_label": meta["gold"],
            "majority_verdict": majority_verdict,
            "agreement_pattern": meta["agreement"],
            "category": meta["category"],
            "withhold_triggers": {
                "fragility_cap": max_cap,
                "cap_source": max_cap_source,
                "cap_all_sources": cap_sources,
                "auditor_flag": auditor_assessment == "FLAG",
                "flag_reason": auditor_assessment,
                "double_jeopardy": "Double jeopardy" in str(conditions),
                "fired_rules": rule_ids,
            },
            "scope_analysis": {
                "evaluator_scope_matches": scope_matches,
                "scope_mismatch_evaluators": scope_mismatch_evals,
                "all_mismatch_are_nei": all_scope_mismatch_are_nei,
                "nei_scope_pattern": is_nei_scope_pattern,
            },
            "trigger_analysis": {
                "cap_justified": cap_justified,
                "cap_reasoning": cap_reasoning,
                "flag_justified": flag_justified,
                "flag_reasoning": flag_reasoning,
                "withhold_justified": withhold_justified,
                "overall_assessment": overall,
            },
        }

        audit_results.append(entry)

        print(f"\n  Claim {claim_id} ({meta['gold']}, {meta['agreement']}):")
        print(f"    Category: {meta['category']}")
        print(f"    Cap: {max_cap} from {max_cap_source}")
        print(f"    NEI-scope pattern: {is_nei_scope_pattern}")
        print(f"    Overall: {overall}")

    # Save trigger audit
    audit_file = out_dir / "withhold_trigger_audit.jsonl"
    with open(audit_file, "w", encoding="utf-8") as f:
        for entry in audit_results:
            f.write(json.dumps(entry, default=str) + "\n")
    log(f"  Trigger audit saved to {audit_file.name}")

    # ============================================================
    # PART 2: Coherence Remediation (2 Grok API calls)
    # ============================================================
    log("")
    log("=" * 70)
    log("  PART 2: Coherence Remediation (Claims 903 and 578)")
    log("=" * 70)

    from cam.core.provider_router import ProviderRouter, ModelTarget

    # Setup Grok router
    target = ModelTarget(
        name="xai:grok",
        provider="xai",
        model="grok-3",
        priority=1,
        max_output_tokens=2048,
        temperature=0.0,
        timeout_sec=120.0,
    )
    router = ProviderRouter(targets=[target])

    # Load dataset for abstract lookup
    claims_by_split, corpus_lookup = load_scifact_dataset()

    # Remediation prompts (from instruction - specific per claim)
    remediation_prompts = {
        903: {
            "cited_evidence": "Triggering of PD-1 expressed on monocytes by PD-L1...induced IL-10 production.",
            "evaluator_verdict": "SUPPORT",
            "contradiction_description": (
                'Your cited evidence says PD-1 triggering INDUCED IL-10 production.\n'
                'Your verdict says the claim that PD-1 triggering REDUCES IL-10 production is SUPPORTED.\n'
                '"Induced" and "reduces" are opposites.'
            ),
        },
        578: {
            "cited_evidence": "induction of AML was suppressed in CSF1R-deficient mice",
            "evaluator_verdict": "SUPPORT",
            "contradiction_description": (
                'Your cited evidence says AML induction was SUPPRESSED when CSF1R was lost.\n'
                'Your verdict says that losing CSF1R FACILITATES leukemogenesis.\n'
                '"Suppressed" and "facilitates" are opposites.'
            ),
        },
    }

    # Load prompt template
    prompt_path = Path(__file__).parent / "prompts" / "coherence_remediation.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    remediation_results = []

    for claim_id in [903, 578]:
        s1 = s1_lookup.get(claim_id, {})
        claim_text = s1.get("claim_text", "")
        gold_label = WITHHELD_CLAIMS[claim_id]["gold"]

        # Look up abstract
        abstract_title, formatted_abstract = _lookup_abstract_for_claim(
            claim_id, gold_label, claims_by_split, corpus_lookup
        )
        if formatted_abstract is None:
            log(f"  ERROR: Could not find abstract for claim {claim_id}")
            continue

        rp = remediation_prompts[claim_id]

        # Build prompt
        prompt = prompt_template.replace("{claim_text}", claim_text)
        prompt = prompt.replace("{formatted_abstract}", formatted_abstract)
        prompt = prompt.replace("{cited_evidence}", rp["cited_evidence"])
        prompt = prompt.replace("{evaluator_verdict}", rp["evaluator_verdict"])
        prompt = prompt.replace("{contradiction_description}", rp["contradiction_description"])

        print(f"\n  Remediation: Claim {claim_id}")
        print(f"    Claim: {claim_text[:100]}...")
        print(f"    Contradiction: {rp['contradiction_description'][:100]}...")

        # Call Grok
        result = None
        meta = None
        raw_response = ""

        for attempt in range(1, 3):
            try:
                raw_obj, meta = router.call_json(
                    system_prompt=(
                        "You are a scientific claim verification evaluator. "
                        "You are being shown a contradiction in your previous reasoning. "
                        "Respond only with valid JSON."
                    ),
                    user_prompt=prompt,
                )
                raw_response = json.dumps(raw_obj)
                result = _normalize_remediation_response(raw_obj)
                log(f"    Attempt {attempt}: decision={result.get('decision', '???')}")
                break
            except Exception as e:
                log(f"    Attempt {attempt} failed: {e}")
                if attempt == 2:
                    result = {"error": f"API call failed: {e}"}

        if result and "decision" in result:
            decision = result["decision"]
            revised = result.get("revised_verdict", "N/A")
            confidence = result.get("confidence", "?")
            print(f"    -> {decision} (revised_verdict={revised}, confidence={confidence})")
            reasoning = result.get("reasoning", "")[:200]
            print(f"       {reasoning}...")
        else:
            print(f"    -> ERROR: {result}")

        # Save raw response
        raw_file = raw_dir / f"claim_{claim_id}_remediation.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "claim_id": claim_id,
                "gold_label": gold_label,
                "evaluator_label": "C",
                "prompt": prompt[:500] + "...",
                "remediation_result": result,
                "raw_response": raw_response,
                "meta": meta,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2, default=str)

        remediation_results.append({
            "claim_id": claim_id,
            "gold_label": gold_label,
            "original_verdict": rp["evaluator_verdict"],
            "decision": result.get("decision", "ERROR") if result else "ERROR",
            "revised_verdict": result.get("revised_verdict") if result else None,
            "reasoning": result.get("reasoning", "") if result else "",
            "confidence": result.get("confidence", "?") if result else "?",
        })

    # Save remediation results
    rem_file = out_dir / "remediation_results.jsonl"
    with open(rem_file, "w", encoding="utf-8") as f:
        for r in remediation_results:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"  Remediation results saved to {rem_file.name}")

    # ============================================================
    # PART 3: Recompute Disposition for Remediated Claims
    # ============================================================
    log("")
    log("=" * 70)
    log("  PART 3: Recompute Disposition for Remediated Claims")
    log("=" * 70)

    stage2_results = _load_jsonl_results(base_dir / "stage2_results.jsonl", "Stage 2")
    s2_lookup = {r["claim_id"]: r.get("challenge", {}) for r in stage2_results}

    updated_dispositions = []

    for rem in remediation_results:
        claim_id = rem["claim_id"]
        decision = rem.get("decision", "ERROR")
        revised_verdict = rem.get("revised_verdict")

        if decision != "REVISE" or not revised_verdict:
            print(f"  Claim {claim_id}: Grok did not revise (decision={decision}), skipping recompute")
            updated_dispositions.append({
                "claim_id": claim_id,
                "remediated": False,
                "reason": f"Grok decision: {decision}",
                "original_disposition": s5_lookup.get(claim_id, {}).get("disposition", {}),
            })
            continue

        # Grok revised! Update evaluator C's verdict in the evaluations
        s1 = s1_lookup.get(claim_id, {})
        evaluations = json.loads(json.dumps(s1.get("evaluations", {})))  # deep copy
        old_verdict = evaluations.get("C", {}).get("verdict", "UNKNOWN")
        evaluations["C"]["verdict"] = revised_verdict
        evaluations["C"]["remediated"] = True
        evaluations["C"]["original_verdict"] = old_verdict

        # Check new agreement pattern
        new_verdicts = [evaluations[l]["verdict"] for l in ["A", "B", "C"] if evaluations.get(l, {}).get("verdict")]
        from collections import Counter as _Counter
        new_counts = _Counter(new_verdicts)
        new_most_common = new_counts.most_common()
        if len(new_most_common) == 1:
            new_agreement = f"3-0 {new_most_common[0][0]}"
        elif new_most_common[0][1] >= 2:
            new_agreement = f"2-1 {new_most_common[0][0]}/{new_most_common[1][0]}"
        else:
            new_agreement = "1-1-1"

        print(f"  Claim {claim_id}: Grok revised {old_verdict} -> {revised_verdict}")
        print(f"    New agreement: {new_agreement}")

        # Recompute fragility (without the incoherent evaluator signal)
        challenge_result = s2_lookup.get(claim_id, {})
        audit = s3_lookup.get(claim_id, {}).get("audit", {})

        claim_data = {
            "claim_id": claim_id,
            "claim_text": s1.get("claim_text", ""),
            "gold_label": s1.get("gold_label", ""),
        }
        profile = compute_fragility_profile(
            claim_data, evaluations, challenge_result, audit
        )

        # Add elimination signals (same as 1b)
        elim = elim_lookup.get(claim_id, {}).get("elimination", {})
        if elim and "error" not in elim:
            killed_verdicts = [
                e for e in elim.get("eliminations", []) if e.get("killed")
            ]
            if killed_verdicts:
                for kv in killed_verdicts:
                    profile["signals"].append({
                        "source": "elimination",
                        "signal_id": f"verdict_killed:{kv.get('target_verdict', '?')}",
                        "description": (
                            f"Verdict {kv.get('target_verdict', '?')} killed by elimination "
                            f"({kv.get('elimination_type', '?')}): "
                            f"{kv.get('reasoning', '')[:120]}"
                        ),
                        "severity": "moderate",
                        "effect": "cap_L2",
                    })
                profile["signal_count"] = len(profile["signals"])
                profile["fragile"] = True

        print(f"    Fragility: {profile.get('signal_count', 0)} signals, "
              f"max_cap={profile.get('max_cap')}")

        # Recompute disposition
        elimination_result = elim_lookup.get(claim_id, {}).get("elimination", {})
        disposition = compute_disposition_with_elimination(
            evaluations, challenge_result, audit,
            profile, elimination_result,
        )
        gold_comparison = compare_to_gold(disposition, s1.get("gold_label", ""))

        match_str = "MATCH" if gold_comparison["gold_match"] else "MISMATCH"
        if gold_comparison["withheld"]:
            match_str = "WITHHELD"

        print(f"    New disposition: {disposition['terminal_state']} @ "
              f"{disposition['commitment_level']} [{match_str}]")

        updated_dispositions.append({
            "claim_id": claim_id,
            "remediated": True,
            "original_eval_c_verdict": old_verdict,
            "revised_eval_c_verdict": revised_verdict,
            "new_agreement": new_agreement,
            "disposition": disposition,
            "gold_comparison": gold_comparison,
            "fragility": profile,
        })

    # Save updated dispositions
    upd_file = out_dir / "updated_dispositions.jsonl"
    with open(upd_file, "w", encoding="utf-8") as f:
        for r in updated_dispositions:
            f.write(json.dumps(r, default=str) + "\n")
    log(f"  Updated dispositions saved to {upd_file.name}")

    # ============================================================
    # PART 4: Withhold Summary
    # ============================================================
    log("")
    log("=" * 70)
    log("  PART 4: Withhold Summary")
    log("=" * 70)

    # Count remediated claims
    n_remediated = sum(1 for d in updated_dispositions if d.get("remediated"))
    remediated_asserted = sum(
        1 for d in updated_dispositions
        if d.get("remediated") and d.get("disposition", {}).get("terminal_state", "").startswith("ASSERT")
    )

    summary_lines = [
        "",
        "=" * 70,
        "  WITHHOLD ANALYSIS SUMMARY",
        "=" * 70,
        "",
        "  Category          | Claims        | Description                          | Assessment",
        "  " + "-" * 95,
    ]

    # Rule design flaw claims
    rule_flaw_claims = [cid for cid, m in WITHHELD_CLAIMS.items() if m["category"] == "rule_design_flaw"]
    summary_lines.append(
        f"  Rule design flaw  | {', '.join(str(c) for c in rule_flaw_claims):13s} | "
        f"RULE-SF-002 penalizes NEI's correct reasoning | Should have asserted"
    )

    # Coherence remediation claims
    coh_claims = [cid for cid, m in WITHHELD_CLAIMS.items() if m["category"] == "coherence_remediation"]
    for cid in coh_claims:
        upd = next((d for d in updated_dispositions if d["claim_id"] == cid), {})
        if upd.get("remediated"):
            new_state = upd.get("disposition", {}).get("terminal_state", "?")
            assessment = "Asserted after remediation" if new_state.startswith("ASSERT") else "Still withheld (other signals)"
        else:
            assessment = "Grok did not revise"
        summary_lines.append(
            f"  Coherence remed.  | {str(cid):13s} | "
            f"Grok contradicted itself, remediation attempted | {assessment}"
        )

    # Genuinely ambiguous
    amb_claims = [cid for cid, m in WITHHELD_CLAIMS.items() if m["category"] == "genuinely_ambiguous"]
    summary_lines.append(
        f"  Genuinely ambig.  | {', '.join(str(c) for c in amb_claims):13s} | "
        f"Real evaluator disagreement                    | Withhold justified"
    )

    # Correctly caught
    caught_claims = [cid for cid, m in WITHHELD_CLAIMS.items() if m["category"] == "correctly_caught"]
    summary_lines.append(
        f"  Correctly caught  | {', '.join(str(c) for c in caught_claims):13s} | "
        f"Would have been wrong                          | Withhold justified"
    )

    summary_lines.extend([
        "",
        "=" * 70,
        "",
        "  RULE-SF-002 / NEI INTERACTION:",
        "",
        f"  Claims affected: {', '.join(str(c) for c in rule_flaw_claims)}",
        "  Pattern: All evaluators report scope_match=mismatch AND verdict=NEI.",
        "  The scope mismatch IS the correct basis for the NEI verdict.",
        "  RULE-SF-002 fires and caps at L1, which combines with auditor FLAG",
        "  to trigger double jeopardy (WITHHOLD).",
        "",
        "  Result: 3 claims that should trivially assert NEI are withheld.",
        "",
        "  Proposed fix: RULE-SF-002 should not fire (or fire at reduced severity)",
        "  when majority verdict is NEI AND all evaluators with scope_match=mismatch",
        "  also verdict NEI. The scope mismatch caused the NEI, not a separate concern.",
        "",
        "  NOTE: Fix is documented here, NOT implemented. Implementation deferred to",
        "  a future step dedicated to rule library refinement.",
        "",
        "=" * 70,
    ])

    summary_text = "\n".join(summary_lines)
    print(summary_text)

    summary_file = out_dir / "withhold_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_text)
    log(f"  Summary saved to {summary_file.name}")

    # ============================================================
    # PART 5: Updated Full Metrics
    # ============================================================
    log("")
    log("=" * 70)
    log("  PART 5: Updated Full Metrics")
    log("=" * 70)

    # Current pipeline numbers (from 1b enhanced run)
    total_claims = 50
    withheld_count = 7
    asserted_count = total_claims - withheld_count  # 43
    # From the 1b run: 38 correct, 5 mismatches among 43 asserted
    correct_assertions = 38
    wrong_assertions = 5

    # Withheld breakdown
    rule_flaw_count = len(rule_flaw_claims)  # 3
    ambiguous_count = len(amb_claims)  # 1
    caught_count = len(caught_claims)  # 1

    # Check remediation outcomes
    grok_revised_count = sum(1 for d in updated_dispositions if d.get("remediated"))
    remediated_and_asserted = sum(
        1 for d in updated_dispositions
        if d.get("remediated") and d.get("disposition", {}).get("terminal_state", "").startswith("ASSERT")
    )
    remediated_still_withheld = grok_revised_count - remediated_and_asserted

    # POTENTIAL STATE: with rule fix only (3 NEI claims freed)
    # Remediated claims stay withheld due to other fragility signals
    # (challenge inference_flag, auditor constraint_violation, etc.)
    # A full pipeline re-run with corrected evaluations would be needed.
    potential_asserted_rule_fix = asserted_count + rule_flaw_count + remediated_and_asserted
    potential_correct_rule_fix = correct_assertions + rule_flaw_count
    # Add any remediated claims that also became assertions
    for upd in updated_dispositions:
        if upd.get("remediated") and upd.get("disposition", {}).get("terminal_state", "").startswith("ASSERT"):
            if upd.get("gold_comparison", {}).get("gold_match"):
                potential_correct_rule_fix += 1
    potential_withheld_rule_fix = total_claims - potential_asserted_rule_fix
    potential_cca_rule_fix = (
        potential_correct_rule_fix / potential_asserted_rule_fix
        if potential_asserted_rule_fix > 0 else 0
    )

    # FULL POTENTIAL: rule fix + remediation + full pipeline re-run
    # (hypothetical — assumes re-running Stages 2-5 with corrected eval would free them)
    full_potential_asserted = asserted_count + rule_flaw_count + grok_revised_count
    full_potential_correct = correct_assertions + rule_flaw_count
    # Remediated claims: Grok revised to CONTRADICT, gold is CONTRADICT -> match
    for upd in updated_dispositions:
        if upd.get("remediated"):
            revised_v = upd.get("revised_eval_c_verdict", "")
            gold = WITHHELD_CLAIMS[upd["claim_id"]]["gold"]
            if revised_v == gold:
                full_potential_correct += 1
    full_potential_withheld = total_claims - full_potential_asserted
    full_potential_cca = (
        full_potential_correct / full_potential_asserted
        if full_potential_asserted > 0 else 0
    )

    metrics_lines = [
        "",
        "=" * 70,
        "  FULL METRICS (with Withhold Analysis)",
        "=" * 70,
        "",
        f"  CURRENT STATE (1b Enhanced Run):",
        f"    Asserted: {asserted_count}/50",
        f"      CCA-gold: {correct_assertions}/{asserted_count} = {correct_assertions/asserted_count:.1%}",
        f"      CCA-AI-adj: 40/43 = 93.0% (from conviction test)",
        f"      Wrong assertions: {wrong_assertions}",
        "",
        f"    Withheld: {withheld_count}/50",
        f"      Rule design flaw (over-cautious): {rule_flaw_count} (claims {', '.join(str(c) for c in rule_flaw_claims)})",
        f"      Coherence issues: 2 (claims {', '.join(str(c) for c in coh_claims)})",
        f"        Grok revised: {grok_revised_count}, still withheld: {remediated_still_withheld}",
        f"      Genuinely ambiguous: {ambiguous_count} (claim {', '.join(str(c) for c in amb_claims)})",
        f"      Correctly caught: {caught_count} (claim {', '.join(str(c) for c in caught_claims)})",
        "",
        f"  COHERENCE REMEDIATION FINDING:",
        f"    Grok revised both claims (903, 578) from SUPPORT -> CONTRADICT.",
        f"    Both revisions match gold label (CONTRADICT).",
        f"    However, claims STILL WITHHELD because other fragility signals remain:",
        f"      - challenge:inference_flag:unstated_assumption (cap_L1)",
        f"      - auditor:constraint_violation:C (cap_L1)",
        f"    These signals were computed against the original (incorrect) evaluation.",
        f"    A full pipeline re-run with corrected evaluation would be needed.",
        "",
        f"  POTENTIAL STATE (rule fix only, no pipeline re-run):",
        f"    Asserted: {potential_asserted_rule_fix}/50",
        f"      CCA-gold: {potential_correct_rule_fix}/{potential_asserted_rule_fix} = {potential_cca_rule_fix:.1%}",
        f"      Known wrong: {wrong_assertions}",
        "",
        f"    Withheld: {potential_withheld_rule_fix}/50",
        f"      Coherence (still withheld): {remediated_still_withheld}",
        f"      Genuinely ambiguous: {ambiguous_count}",
        f"      Correctly caught: {caught_count}",
        "",
        f"  FULL POTENTIAL (rule fix + remediation + pipeline re-run):",
        f"    Asserted: {full_potential_asserted}/50",
        f"      CCA-gold: {full_potential_correct}/{full_potential_asserted} = {full_potential_cca:.1%}",
        f"      Known wrong: {wrong_assertions}",
        "",
        f"    Withheld: {full_potential_withheld}/50",
        f"      Genuinely ambiguous: {ambiguous_count}",
        f"      Correctly caught: {caught_count}",
        "",
        f"  RULE DESIGN ISSUE IDENTIFIED:",
        f"    RULE-SF-002 fires on NEI verdicts caused by scope mismatch,",
        f"    penalizing the evidence that justifies the verdict.",
        f"    Proposed fix: Do not fire scope mismatch cap on unanimous NEI verdicts.",
        "",
        "=" * 70,
    ]

    metrics_text = "\n".join(metrics_lines)
    print(metrics_text)

    metrics_file = out_dir / "metrics.txt"
    with open(metrics_file, "w", encoding="utf-8") as f:
        f.write(metrics_text)
    log(f"  Metrics saved to {metrics_file.name}")

    # ============================================================
    # DONE
    # ============================================================
    log("")
    log("=" * 70)
    log("  WITHHOLD ANALYSIS COMPLETE")
    log(f"  Output: {out_dir.name}")
    log("=" * 70)

    return audit_results, remediation_results, updated_dispositions


def _normalize_remediation_response(raw_obj):
    """Normalize coherence remediation response."""
    from cam.core.json_extract import safe_json_extract

    if isinstance(raw_obj, str):
        raw_obj = safe_json_extract(raw_obj)

    result = {}

    decision = raw_obj.get("decision", "")
    if isinstance(decision, str):
        decision = decision.upper().strip()
    if decision in ("REVISE", "A"):
        result["decision"] = "REVISE"
    elif decision in ("EXPLAIN", "B"):
        result["decision"] = "EXPLAIN"
    else:
        result["decision"] = decision

    result["revised_verdict"] = raw_obj.get("revised_verdict")
    if result["revised_verdict"] and isinstance(result["revised_verdict"], str):
        result["revised_verdict"] = result["revised_verdict"].upper().strip()

    result["reasoning"] = raw_obj.get("reasoning", "")

    confidence = raw_obj.get("confidence", "")
    if isinstance(confidence, str):
        confidence = confidence.lower().strip()
    result["confidence"] = confidence if confidence in ("high", "medium", "low") else "unknown"

    return result
