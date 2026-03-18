"""
CAM Lease Review — Pre-scan Module

Fast Gemini calls to discover non-standard provisions before analysis.
Runs at upload time so users can review and confirm before pipeline starts.
"""

import asyncio
import json
import os
import re

# All 18 LP provision names — used to prevent false positives
LP_PROVISION_NAMES = [
    "Rent & Payment Terms",
    "Rent Escalation",
    "Lease Term & Renewal",
    "Security Deposit",
    "Permitted Use",
    "Maintenance & Repairs",
    "Common Area Maintenance (CAM)",
    "Insurance Requirements",
    "Subletting & Assignment",
    "Alterations & Improvements",
    "Default & Remedies",
    "Early Termination",
    "Indemnification & Liability",
    "Force Majeure",
    "Signage Rights",
    "Parking",
    "Dispute Resolution",
    "Holdover Provisions",
]

LP_LIST_TEXT = "\n".join(f"- {name}" for name in LP_PROVISION_NAMES)


def _make_dedup_key(name: str) -> str:
    """Robust dedup: strip stop words, use first 3 significant words."""
    stop = {"the", "a", "an", "of", "to", "and", "or", "for", "in", "on"}
    words = [w for w in name.lower().split() if w not in stop]
    return " ".join(words[:3])


# Models to try in order — if one is unavailable or errors, fall through to the next
_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


# Per-model generation configs — thinking models need thinking_budget=0 for determinism
_MODEL_CONFIGS = {
    "gemini-2.5-flash": {
        "temperature": 0,
        "max_output_tokens": 2000,
        "thinking_config": {"thinking_budget": 0},
    },
    "gemini-2.5-pro": {
        "temperature": 0,
        "max_output_tokens": 2000,
        "thinking_config": {"thinking_budget": 0},
    },
}


def _call_gemini_sync(prompt: str) -> str:
    """Synchronous Gemini call with automatic model fallback.

    Returns the model response text. Logs which model was used.
    All models in the fallback chain are configured for deterministic output:
    - temperature=0 locks sampling
    - thinking_budget=0 disables internal chain-of-thought on flash/pro models
    """
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")

    client = genai.Client(api_key=api_key)
    last_error = None

    for model in _GEMINI_MODELS:
        config = _MODEL_CONFIGS.get(model, {"temperature": 0, "max_output_tokens": 2000})
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            print(f"[prescan] Used model: {model}")
            return response.text or ""
        except Exception as e:
            last_error = e
            print(f"[prescan] Model {model} failed: {e}, trying next...")
            continue

    raise RuntimeError(f"All prescan models failed. Last error: {last_error}")


def _call_claude_sync(prompt: str) -> str:
    """Synchronous Claude call for prescan."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text if response.content else ""


def _call_gpt_sync(prompt: str) -> str:
    """Synchronous GPT call for prescan."""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


_MODEL_CALLERS = {
    "gemini": _call_gemini_sync,
    "claude": _call_claude_sync,
    "gpt":    _call_gpt_sync,
}


def _merge_model_results(all_results: list[list[dict]]) -> list[dict]:
    """
    Merge results from multiple models.

    Existence vote is implicit: a model that quoted clause_text voted "exists".
    A model that couldn't find text simply omitted the item — that IS its vote.
    counts[key] = number of models that found and quoted text.

    Confidence after merge (before LP kill round):
      counts == total_models  → "confirmed" (all models found it)
      counts < total_models   → "possible"  (not all models found it)

    Items where zero models quoted text are dropped entirely.
    """
    total_models = len(all_results)
    counts = {}   # dedup_key -> count of models that found+quoted text
    best   = {}   # dedup_key -> best item dict
    sig_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

    for model_results in all_results:
        for item in model_results:
            name = item.get("name", "").strip()
            if not name:
                continue
            # Only count as existence vote if model actually quoted text
            clause_text = item.get("clause_text", "").strip()
            if not clause_text:
                print(f"[prescan] Skipping '{name}' — model provided no clause_text")
                continue
            key = _make_dedup_key(name)
            counts[key] = counts.get(key, 0) + 1
            if key not in best:
                best[key] = item.copy()
            else:
                # Prefer higher significance
                existing_sig = best[key].get("significance", "LOW")
                new_sig = item.get("significance", "LOW")
                if sig_order.get(new_sig, 2) < sig_order.get(existing_sig, 2):
                    best[key] = item.copy()

    merged = []
    for key, item in best.items():
        vote_count = counts.get(key, 0)
        if vote_count == 0:
            print(f"[prescan] Dropping '{item.get('name','')}' — no model quoted text")
            continue
        item["existence_votes"] = vote_count
        item["existence_total"] = total_models
        # All models found it = confirmed. Any disagreement = possible.
        item["confidence"] = "confirmed" if vote_count == total_models else "possible"
        merged.append(item)

    conf_order = {"confirmed": 0, "possible": 1}
    merged.sort(key=lambda x: (
        conf_order.get(x.get("confidence", "possible"), 1),
        sig_order.get(x.get("significance", "LOW"), 2)
    ))
    return merged


def _semantic_dedup(items: list[dict]) -> list[dict]:
    """
    Post-merge semantic deduplication.
    Sends just the names to a model and asks which are semantically equivalent.
    Returns deduplicated list.
    """
    if len(items) <= 1:
        return items

    names = [item.get("name", "") for item in items]
    numbered = "\n".join(f"{i+1}. {name}" for i, name in enumerate(names))

    prompt = (
        "Below is a list of non-standard lease provision names found by AI models.\n"
        "Some may refer to the same underlying clause, just phrased differently.\n\n"
        f"{numbered}\n\n"
        "Identify groups of names that refer to the SAME underlying lease concept.\n"
        "Return ONLY a JSON array of groups. Each group is an array of 1-based indices.\n"
        "Items that are unique (no duplicate) should appear as a single-item group.\n"
        "Example: [[1,3],[2],[4,5,6]] means items 1&3 are the same, 2 is unique, 4&5&6 are the same.\n"
        "Return ONLY the JSON array, no explanation."
    )

    try:
        # Use the fastest available model — just names, no documents
        raw = _call_gemini_sync(prompt)
        # Extract JSON array from response
        match = re.search(r'\[[\s\S]*\]', raw)
        if not match:
            return items  # fallback: no dedup
        groups = json.loads(match.group())
        if not isinstance(groups, list):
            return items

        # Merge each group
        sig_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        conf_order = {"confirmed": 0, "possible": 1}
        merged = []
        for group in groups:
            if not isinstance(group, list) or len(group) == 0:
                continue
            # Collect items in this group (convert 1-based to 0-based)
            group_items = []
            for idx in group:
                if isinstance(idx, int) and 1 <= idx <= len(items):
                    group_items.append(items[idx - 1])
            if not group_items:
                continue
            if len(group_items) == 1:
                merged.append(group_items[0])
                continue
            # Pick best: highest confidence, then highest significance
            best = sorted(group_items, key=lambda x: (
                conf_order.get(x.get("confidence", "possible"), 1),
                sig_order.get(x.get("significance", "LOW"), 2)
            ))[0].copy()
            # If ANY item in group is confirmed, the merged item is confirmed
            if any(x.get("confidence") == "confirmed" for x in group_items):
                best["confidence"] = "confirmed"
            # Combine tenant lists if present
            all_tenants = []
            for x in group_items:
                all_tenants.extend(x.get("tenants", []))
            if all_tenants:
                best["tenants"] = list(dict.fromkeys(all_tenants))  # dedupe preserving order
            merged.append(best)

        return merged if merged else items

    except Exception as e:
        print(f"[prescan] Semantic dedup failed ({e}), returning undeduped results")
        return items


def _lp_kill_round(items: list[dict], models: list[str] = None) -> list[dict]:
    """
    Challenge round: ask models whether each prescan finding is actually
    covered by one of the 18 standard LP provisions.

    Verdicts per model per item:
      KILL     — clearly covered by an existing LP provision
      KEEP     — genuinely non-standard, not covered by any LP
      UNCERTAIN — ambiguous

    Tally logic:
      All models say KILL         → remove item entirely
      Majority KILL, not all      → keep, add lp_overlap field (which LP)
      Any KEEP/UNCERTAIN majority → keep as-is

    Returns filtered list with optional lp_overlap field added where relevant.
    Falls back to returning items unmodified if anything fails.
    """
    if not items or len(items) == 0:
        return items
    if models is None:
        models = ["gemini", "claude"]

    # Build numbered list of items for prompt
    numbered = "\n".join(
        f"{i+1}. Name: {item.get('name','')}\n   Description: {item.get('description','')}"
        for i, item in enumerate(items)
    )

    prompt = (
        "You are reviewing a list of non-standard provisions found in a commercial lease.\n"
        "For each provision, determine whether it is GENUINELY non-standard, or whether\n"
        "it actually falls under one of the 18 standard provisions our system already covers.\n\n"
        "THE 18 STANDARD PROVISIONS:\n"
        f"{LP_LIST_TEXT}\n\n"
        "PROVISIONS TO EVALUATE:\n"
        f"{numbered}\n\n"
        "For each numbered provision, return:\n"
        "  verdict: KILL if it clearly belongs under one of the 18 standard provisions above,\n"
        "           KEEP if it is genuinely non-standard and not covered by any of the 18,\n"
        "           UNCERTAIN if you cannot confidently determine either way.\n"
        "  lp_name: If verdict is KILL or UNCERTAIN, the name of the most relevant standard\n"
        "           provision from the list above (e.g. 'Parking', 'Lease Term & Renewal').\n"
        "           Use null if verdict is KEEP.\n\n"
        "Return ONLY a JSON array, one object per provision, in the same order:\n"
        "[\n"
        "  {\"index\": 1, \"verdict\": \"KEEP|KILL|UNCERTAIN\", \"lp_name\": null},\n"
        "  {\"index\": 2, \"verdict\": \"KILL\", \"lp_name\": \"Parking\"},\n"
        "  ...\n"
        "]\n"
        "Return ONLY the JSON array, no other text."
    )

    # Collect verdicts from each model
    # model_verdicts[i] = list of verdict strings across models for item i
    model_verdicts = {i: [] for i in range(len(items))}
    model_lp_names = {i: [] for i in range(len(items))}

    for model_key in models:
        caller = _MODEL_CALLERS.get(model_key)
        if not caller:
            continue
        try:
            raw = caller(prompt)
            match = re.search(r'\[[\s\S]*\]', raw)
            if not match:
                continue
            verdicts = json.loads(match.group())
            if not isinstance(verdicts, list):
                continue
            for v in verdicts:
                idx = v.get("index", 0) - 1  # convert to 0-based
                if 0 <= idx < len(items):
                    verdict = v.get("verdict", "UNCERTAIN")
                    lp_name = v.get("lp_name")
                    model_verdicts[idx].append(verdict)
                    if lp_name:
                        model_lp_names[idx].append(lp_name)
        except Exception as e:
            print(f"[prescan] LP kill round model {model_key} failed: {e}")
            continue

    # Tally and filter
    surviving = []
    for i, item in enumerate(items):
        verdicts = model_verdicts[i]
        if not verdicts:
            # No model responded — keep it
            surviving.append(item)
            continue

        kill_count = verdicts.count("KILL")
        total = len(verdicts)

        if kill_count == total:
            # Unanimous kill — all models agree it's covered by standard provisions
            print(f"[prescan] Kill round: KILLED '{item.get('name','')}' (unanimous {kill_count}/{total})")
            continue
        else:
            item = item.copy()
            if kill_count > 0:
                # At least one model thinks it overlaps — mark uncertain, note which LP
                lp_names = model_lp_names[i]
                lp_note = lp_names[0] if lp_names else None
                if lp_note:
                    item["lp_overlap"] = lp_note
                item["confidence"] = "possible"
                print(f"[prescan] Kill round: UNCERTAIN '{item.get('name','')}' "
                      f"({kill_count}/{total} say overlaps with {lp_note})")
            else:
                # All models say KEEP — confidence unchanged (stays confirmed or possible
                # from existence vote)
                print(f"[prescan] Kill round: KEPT '{item.get('name','')}' "
                      f"(all {total} models say distinct)")
            surviving.append(item)

    return surviving


async def scan_template(template_text: str, models: list[str] = None) -> dict:
    """
    Scan template lease for non-standard provisions using one or more models.

    models: list of model keys from _MODEL_CALLERS. Defaults to ["gemini", "claude"].
    Returns: {"non_standard": [...]} where each item has confidence field added.
    """
    if models is None:
        models = ["gemini", "claude"]

    prompt = f"""You are analyzing a commercial lease template to identify non-standard provisions.

The following 18 topics are ALREADY covered by our standard analysis:
{LP_LIST_TEXT}

These 18 topics correspond to articles labeled "(LP-XX)" in the document.
Any provision inside an article already labeled (LP-01) through (LP-18)
is already covered — do NOT flag those.

Only flag provisions in articles or sections that have NO "(LP-XX)" label
and are not boilerplate (definitions, recitals, signature blocks,
notices, severability, counterparts, governing law, entire agreement,
waiver, successors, quiet enjoyment, estoppel, subordination,
confidentiality, or surrender).

Read this lease template and identify any MAJOR sections or provisions that:
1. Do NOT fall under any of the 18 standard topics listed above
2. Are substantive legal obligations (not boilerplate recitals, definitions, or signature blocks)
3. Would materially affect the rights or obligations of either party

For each non-standard provision found, provide:
- name: Short descriptive name (3-5 words)
- section_ref: Section number/heading from the document
- description: One sentence explaining what this provision does
- significance: HIGH (major rights/obligations), MEDIUM (notable but secondary), or LOW (minor)
- clause_text: REQUIRED. The verbatim text of this clause copied directly from the document.
  If you cannot find and copy the actual text, do NOT include this item at all.

Return ONLY a JSON object in this exact format, no other text:
{{
  "non_standard": [
    {{
      "name": "...",
      "section_ref": "...",
      "description": "...",
      "significance": "HIGH|MEDIUM|LOW",
      "clause_text": "...verbatim text copied from document..."
    }}
  ]
}}

CRITICAL: Only include provisions where you can copy the actual clause text verbatim.
If you believe a provision concept is present but cannot find and quote the actual text,
omit it entirely. Do not fabricate or paraphrase — copy the actual words from the document.

LEASE TEMPLATE:
{template_text}
"""

    async def call_one_model(model_key: str) -> list[dict]:
        caller = _MODEL_CALLERS.get(model_key)
        if not caller:
            return []
        try:
            text = await asyncio.to_thread(caller, prompt)
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                data = json.loads(match.group())
                return data.get("non_standard", [])
        except Exception as e:
            print(f"[prescan] Template scan model {model_key} failed: {e}")
        return []

    all_results = await asyncio.gather(*[call_one_model(m) for m in models])
    merged = _merge_model_results(list(all_results))
    merged = _semantic_dedup(merged)
    merged = _lp_kill_round(merged, models=models)
    return {"non_standard": merged}


async def scan_tenants(
    tenant_texts: dict,
    template_text: str = "",
    models: list[str] = None,
    template_non_standard: list[dict] = None,
) -> dict:
    """
    Scan tenant leases for provisions outside LP-01–LP-18 AND template non-standard provisions.

    template_non_standard: provisions already found in the template scan (tier 2 exclusion).
                           Tenants are only scanned for provisions NOT already in this list.
    models: list of model keys. Defaults to ["gemini", "claude"].
    Returns: {"non_standard": [...]} with confidence field.
    """
    if models is None:
        models = ["gemini", "claude"]
    if template_non_standard is None:
        template_non_standard = []

    if not tenant_texts:
        return {"non_standard": []}

    # Build tier 2 exclusion text for prompts
    tier2_exclusion = ""
    if template_non_standard:
        names = [item.get("name", "") for item in template_non_standard if item.get("name")]
        if names:
            tier2_exclusion = (
                "\n\nThe following non-standard provisions were already found in the "
                "LANDLORD'S TEMPLATE — do NOT flag these again:\n"
                + "\n".join(f"- {n}" for n in names)
            )

    per_tenant_findings = {}  # dedup_key -> {info, tenants[], model_counts{}}

    for filename, text in tenant_texts.items():
        prompt = f"""You are analyzing a tenant's lease to find clauses the tenant added
that are NOT present in the landlord's standard template.

Standard provisions ALREADY covered by our analysis (ignore these completely):
{LP_LIST_TEXT}

These 18 topics correspond to articles labeled "(LP-XX)" in the document.
Any provision inside an article already labeled (LP-01) through (LP-18)
is already covered — do NOT flag those.
{tier2_exclusion}

{"LANDLORD TEMPLATE (for reference):" + chr(10) + template_text if template_text else ""}

TENANT LEASE:
{text}

Identify provisions in the TENANT lease that meet ALL of these criteria:
1. Are NOT covered by the 18 standard topics listed above
2. Are NOT in the tier-2 exclusion list above (already found in landlord template)
3. Either: (a) do not appear in the landlord's template at all, OR
          (b) add NEW obligations or rights beyond what the template contains
4. Are substantively meaningful — not just formatting or minor wording changes
5. Represent new rights or obligations that a landlord's attorney should know about

Return ONLY a JSON object, no other text:
{{
  "non_standard": [
    {{
      "name": "...",
      "section_ref": "...",
      "description": "...",
      "significance": "HIGH|MEDIUM|LOW",
      "clause_text": "...verbatim text copied from tenant lease..."
    }}
  ]
}}

CRITICAL: Only include provisions where you can copy the actual clause text verbatim
from the tenant lease. If you cannot find and quote the actual text, omit the item entirely.

If no tenant-added provisions found, return {{"non_standard": []}}.
"""

        async def call_one_model(model_key: str, fname: str = filename) -> tuple[str, list[dict]]:
            caller = _MODEL_CALLERS.get(model_key)
            if not caller:
                return model_key, []
            try:
                text_out = await asyncio.to_thread(caller, prompt)
                match = re.search(r'\{[\s\S]*\}', text_out)
                if match:
                    data = json.loads(match.group())
                    return model_key, data.get("non_standard", [])
            except Exception as e:
                print(f"[prescan] Tenant scan model {model_key} failed for {fname}: {e}")
            return model_key, []

        model_results_pairs = await asyncio.gather(*[call_one_model(m) for m in models])
        all_results_for_tenant = [r for _, r in model_results_pairs]
        merged_for_tenant = _merge_model_results(all_results_for_tenant)

        for item in merged_for_tenant:
            name = item.get("name", "").strip()
            if not name:
                continue
            key = _make_dedup_key(name)
            if key not in per_tenant_findings:
                per_tenant_findings[key] = {
                    "name": name,
                    "description": item.get("description", ""),
                    "significance": item.get("significance", "MEDIUM"),
                    "confidence": item.get("confidence", "possible"),
                    "tenants": [],
                }
            per_tenant_findings[key]["tenants"].append(filename)
            # Upgrade confidence and significance if better
            sig_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            if item.get("confidence") == "confirmed":
                per_tenant_findings[key]["confidence"] = "confirmed"
            existing_sig = per_tenant_findings[key]["significance"]
            new_sig = item.get("significance", "MEDIUM")
            if sig_order.get(new_sig, 2) < sig_order.get(existing_sig, 2):
                per_tenant_findings[key]["significance"] = new_sig

    # Sort: confirmed first, then HIGH > MEDIUM > LOW
    conf_order = {"confirmed": 0, "possible": 1}
    sig_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    added = sorted(
        per_tenant_findings.values(),
        key=lambda x: (
            conf_order.get(x.get("confidence", "possible"), 1),
            sig_order.get(x.get("significance", "MEDIUM"), 1)
        )
    )
    added = _semantic_dedup(added)
    added = _lp_kill_round(added, models=models)
    return {"non_standard": added}
