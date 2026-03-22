(function() {
    "use strict";

    function getAuditGovernanceLabel(signal) {
        const map = {
            ASSERT_SIGNAL: "Assert",
            ASSERT_REVIEW_SIGNAL: "Assert, but review carefully",
            REVIEW_SIGNAL: "Review recommended",
            WITHHOLD_SIGNAL: "Withhold",
        };
        return map[signal] || signal || "—";
    }

    function getAuditPatternLabel(pattern) {
        const map = {
            PATTERN_1_RELIABLE: "Reliable",
            PATTERN_2_FRAGILE_PERSUASIVE: "Fragile Persuasive",
            PATTERN_3_WEAK: "Weak",
            PATTERN_3_WEAK_UNCLEAR: "Weak / Unclear",
            PATTERN_4_MISSED_WEAKNESS: "Missed Weakness",
        };
        return map[pattern] || pattern || "—";
    }

    function getAuditAsgTone(asg) {
        if (asg == null || isNaN(asg)) return { label: "Not available", tone: "neutral", width: 0 };
        const width = Math.max(5, Math.min(100, Math.round(asg)));
        if (asg < 15) return { label: "Stable \u2014 finding holds up even under the most conservative reading.", tone: "good", width };
        if (asg < 35) return { label: "Mostly stable \u2014 solid finding that could look slightly different under a stricter reading.", tone: "caution", width };
        if (asg < 55) return { label: "Sensitive \u2014 how this clause is ultimately read could change the practical impact.", tone: "warning", width };
        return { label: "Highly sensitive \u2014 the practical impact depends significantly on how the clause is interpreted.", tone: "danger", width };
    }

    function getAuditConfidenceTone(camPerm) {
        if (camPerm == null || isNaN(camPerm)) return { label: "Not available", tone: "neutral", width: 0 };
        if (camPerm >= 85) return { label: "Very strong \u2014 reviewers were highly consistent and the finding can be relied upon.", tone: "good", width: camPerm };
        if (camPerm >= 70) return { label: "Strong \u2014 solid reviewer agreement, well-supported finding.", tone: "good", width: camPerm };
        if (camPerm >= 50) return { label: "Moderate \u2014 some variation between reviewers; worth checking directly.", tone: "caution", width: camPerm };
        return { label: "Weak \u2014 reviewers disagreed significantly; treat this as a flag rather than a confirmed finding.", tone: "danger", width: Math.max(18, camPerm) };
    }

    function getAuditFragilityTone(fragilityRaw) {
        const score = fragilityRaw && fragilityRaw.fragility_score != null ? Number(fragilityRaw.fragility_score) : null;
        if (score == null || isNaN(score)) return { label: "Not available", tone: "neutral", width: 0 };
        const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
        if (pct < 15) return { label: "Simple clause \u2014 clear language that doesn\u2019t depend on other parts of the lease.", tone: "good", width: pct };
        if (pct < 35) return { label: "Moderate complexity \u2014 mostly clear, with some elements that may need careful reading.", tone: "caution", width: pct };
        if (pct < 60) return { label: "Complex \u2014 cross-references or defined terms make the meaning dependent on context.", tone: "warning", width: pct };
        return { label: "Highly complex \u2014 the clause\u2019s meaning is heavily tied to how other parts of the lease are read.", tone: "danger", width: pct };
    }

    function getAuditAgreementSummary(pattern) {
        if (!pattern) return "Evaluator agreement was not available.";
        if (pattern.includes("3/3")) return "All three evaluators reached the same conclusion.";
        if (pattern.includes("2/3")) return "Two of the three evaluators agreed on the outcome.";
        return `Evaluator agreement pattern: ${pattern}.`;
    }

    function getAuditEvidenceSummary(provision, challengeRaw) {
        const basis = ((provision.cam_score || {}).evidence_basis || "").toLowerCase();
        if (basis === "explicit_text") return "The conclusion is tied to direct contract text.";
        if (basis === "structural_inference") return "The conclusion depends partly on structural inference rather than only explicit text.";
        if (basis === "absence") return "The conclusion is based on missing language in one of the documents.";
        if (basis === "ambiguous") return "The available text supports multiple readings, so the evidence is ambiguous.";
        if (basis === "unverified_citation") return "The evidence chain contains citations that could not be fully verified.";
        if (challengeRaw && challengeRaw.substantive_finding) return "The challenger found a substantive issue in the text comparison.";
        return "CAM reviewed the clause text but the evidence basis was not explicitly labeled.";
    }

    function getAuditReasoningSummary(provision, stagesRun, challengeRaw) {
        if (stagesRun.has(4) && challengeRaw) {
            return "This clause went through the full review chain, including a challenge step.";
        }
        if (stagesRun.has(3)) {
            return "This clause reached evaluator review, but the challenge stage was skipped.";
        }
        return "This clause did not move through the full reasoning chain.";
    }

    function getAuditFragilitySummary(fragilityRaw, translations) {
        const rules = (fragilityRaw && fragilityRaw.rules_fired) || [];
        if (!rules.length) return "No structural fragility signals were detected.";
        const translated = rules.map(r => (translations || {})[r.signal] || r.signal || r.rule_id).filter(Boolean);
        return `Structural fragility was detected because of ${translated.join(", ")}.`;
    }

    function renderAuditScoreBar(label, value, helper, toneInfo, escFn, context) {
        const esc = escFn || (value => String(value ?? ""));
        const tone = toneInfo && toneInfo.tone ? toneInfo.tone : "neutral";
        const width = toneInfo && toneInfo.width != null ? toneInfo.width : 0;
        const contextHtml = context ? `<div class="audit-score-context">${esc(context)}</div>` : "";
        return `<div class="audit-score-card audit-score-${tone}">
            <div class="audit-score-head">
                <span class="audit-score-label">${esc(label)}</span>
                <span class="audit-score-value">${value}</span>
            </div>
            <div class="audit-score-track"><span class="audit-score-fill audit-score-fill-${tone}" style="width:${Math.max(0, Math.min(100, width))}%"></span></div>
            <div class="audit-score-helper">${esc(helper)}</div>
            ${contextHtml}
        </div>`;
    }

    function renderAuditRawRecord(title, record, escFn) {
        if (!record) return "";
        const esc = escFn || (value => String(value ?? ""));
        return `<details class="audit-raw-record">
            <summary>${esc(title)}</summary>
            <pre>${esc(JSON.stringify(record, null, 2))}</pre>
        </details>`;
    }

    function renderAuditPromptBlock(title, text, escFn) {
        if (!text) return "";
        const esc = escFn || (value => String(value ?? ""));
        return `<details class="audit-raw-record">
            <summary>${esc(title)}</summary>
            <pre>${esc(text)}</pre>
        </details>`;
    }

    function renderAuditTechnicalGroup(title, innerHtml, escFn) {
        if (!innerHtml) return "";
        const esc = escFn || (value => String(value ?? ""));
        return `<div class="audit-technical-group">
            <div class="audit-technical-group-title">${esc(title)}</div>
            ${innerHtml}
        </div>`;
    }

    function getConfidenceBadgeData(governanceSignal, severity) {
        const map = {
            ASSERT_SIGNAL:        { label: "Verified",       cssClass: "confirmed",  dots: "\u25cf\u25cf\u25cf\u25cf" },
            ASSERT_REVIEW_SIGNAL: { label: "Impact Unclear", cssClass: "fragile",    dots: "\u25cf\u25cf\u25cf\u25cb" },
            REVIEW_SIGNAL:        { label: "Needs Review",   cssClass: "uncertain",  dots: "\u25cf\u25cf\u25cb\u25cb" },
            WITHHOLD_SIGNAL:      { label: "Inconclusive",   cssClass: "unverified", dots: "\u25cf\u25cb\u25cb\u25cb" },
        };
        const data = map[governanceSignal];
        if (!data) return null;

        // High-severity + low-confidence special case
        const isHighSeverity = severity === "CRITICAL" || severity === "HIGH";
        const isLowConfidence = governanceSignal === "REVIEW_SIGNAL" || governanceSignal === "WITHHOLD_SIGNAL";
        if (isHighSeverity && isLowConfidence) {
            return { ...data, needsReview: true };
        }
        return data;
    }

    function getSidebarConfidenceLabel(governanceSignal) {
        const map = {
            ASSERT_SIGNAL:        "Verified",
            ASSERT_REVIEW_SIGNAL: "Impact Unclear",
            REVIEW_SIGNAL:        "Needs Review",
            WITHHOLD_SIGNAL:      "Inconclusive",
        };
        return map[governanceSignal] || null;
    }

    function getSidebarExplanationText(provision) {
        if (!provision) return "";
        var sig = (provision.cam_score || {}).governance_signal || "";
        var signals = (provision.fragility || {}).signals || [];
        var pattern = provision.agreement_pattern || "";
        var challenge = provision.challenge_finding || "";
        var basis = (provision.cam_score || {}).evidence_basis || "";

        // WITHHOLD / INCONCLUSIVE cases
        if (sig === "WITHHOLD_SIGNAL") {
            if (pattern.includes("3-way") || pattern.includes("split"))
                return "Evaluators reached different conclusions on this clause.";
            if (basis === "absence")
                return "This clause is not explicitly addressed in the lease.";
            return "Insufficient evidence to reach a reliable conclusion.";
        }

        // REVIEW_SIGNAL / NEEDS REVIEW cases
        if (sig === "REVIEW_SIGNAL") {
            if (pattern.includes("2-1") || pattern.includes("split"))
                return "Evaluators disagreed on whether this is a real deviation.";
            if (challenge === "NEEDS_EXPERT")
                return "This requires expert legal interpretation to resolve.";
            if (basis === "ambiguous")
                return "The language supports multiple readings.";
            return "Mixed signals \u2014 verify before acting on this finding.";
        }

        // ASSERT_REVIEW_SIGNAL / CHECK INTERPRETATION cases
        if (sig === "ASSERT_REVIEW_SIGNAL") {
            if (signals.includes("definition_override"))
                return "Depends on how a redefined term is interpreted.";
            if (signals.includes("cross_reference_dependency"))
                return "Meaning depends on how related clauses are read together.";
            if (signals.includes("negation_pattern"))
                return "New limiting language may affect the scope of this clause.";
            if (signals.includes("quantitative_deviation"))
                return "A numerical change may shift the practical impact.";
            if (signals.includes("qualifier_shift"))
                return "Obligation strength has changed (e.g., 'shall' to 'may').";
            return "The finding is solid but depends on interpretation of the clause.";
        }

        // ASSERT_SIGNAL / VERIFIED cases
        if (sig === "ASSERT_SIGNAL") {
            if (basis === "explicit_text")
                return "Clearly supported by explicit lease language.";
            if (challenge === "SUBSTANTIVE_DEVIATION")
                return "Verified as a real deviation by independent review.";
            return "Well-supported finding \u2014 low interpretation risk.";
        }

        return "";
    }

    function getCombinedTooltipText(severity, governanceSignal) {
        const key = (severity || "").toUpperCase() + ":" + (governanceSignal || "");
        const map = {
            "CRITICAL:ASSERT_SIGNAL":        "Fundamental deal terms changed with clear impact. All evaluators agree, reasoning grounded in explicit text.",
            "CRITICAL:ASSERT_REVIEW_SIGNAL": "Fundamental change identified but practical impact depends on how specific terms or cross-references are interpreted.",
            "CRITICAL:REVIEW_SIGNAL":        "Evaluators disagreed on a potentially high-impact change. The clause text should be examined directly.",
            "CRITICAL:WITHHOLD_SIGNAL":      "A potentially significant change was flagged but the pipeline lacks sufficient basis to characterize it. Independent examination warranted.",
            "HIGH:ASSERT_SIGNAL":            "Material change to rights or obligations. Well-supported by evaluator consensus and explicit lease language.",
            "HIGH:ASSERT_REVIEW_SIGNAL":     "Material change identified but significance depends on how terms, definitions, or related clauses are read together.",
            "HIGH:REVIEW_SIGNAL":            "Possible material change with mixed evaluator evidence. May be significant if confirmed.",
            "HIGH:WITHHOLD_SIGNAL":          "A possible material issue was flagged with insufficient confidence to characterize. Should not be relied upon without independent review.",
            "MEDIUM:ASSERT_SIGNAL":          "Notable change with limited impact. Confirmed by evaluator agreement and grounded in text.",
            "MEDIUM:ASSERT_REVIEW_SIGNAL":   "Notable change found but practical significance depends on interpretation. Unlikely to be a deal-breaker.",
            "MEDIUM:REVIEW_SIGNAL":          "Possible change with limited risk and mixed evidence. Lower priority for review.",
            "MEDIUM:WITHHOLD_SIGNAL":        "Weak signal on a moderate issue. Unlikely to warrant attention unless part of a broader pattern.",
            "LOW:ASSERT_SIGNAL":             "Minor deviation confirmed. De minimis impact. Noted for completeness.",
            "LOW:ASSERT_REVIEW_SIGNAL":      "Minor change with some interpretive nuance. Recorded but action unlikely to be needed.",
            "LOW:REVIEW_SIGNAL":             "Possible minor change with mixed evidence. Low priority.",
            "LOW:WITHHOLD_SIGNAL":           "Weak signal on a minor issue.",
        };
        return map[key] || "";
    }

    function getConfidenceToneText(governanceSignal) {
        const map = {
            ASSERT_SIGNAL:        "Strong finding \u2014 survived both permissive and strict review",
            ASSERT_REVIEW_SIGNAL: "High confidence, but sensitive to interpretation",
            REVIEW_SIGNAL:        "Mixed evaluator evidence \u2014 verify before acting",
            WITHHOLD_SIGNAL:      "Insufficient confidence to assert \u2014 treat as a flag only",
        };
        return map[governanceSignal] || "";
    }

    /**
     * Convert **bold** markdown syntax to <strong> HTML.
     * Used only for interpretation notes — do NOT use for untrusted content.
     * Only processes **text** patterns, nothing else.
     */
    function boldMarkdown(text) {
        if (!text) return "";
        // Escape HTML first, then convert **bold** → <strong>
        var escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    }

    window.CAMAuditShared = {
        getAuditGovernanceLabel,
        getAuditPatternLabel,
        getAuditAsgTone,
        getAuditConfidenceTone,
        getAuditFragilityTone,
        getAuditAgreementSummary,
        getAuditEvidenceSummary,
        getAuditReasoningSummary,
        getAuditFragilitySummary,
        renderAuditScoreBar,
        renderAuditRawRecord,
        renderAuditPromptBlock,
        renderAuditTechnicalGroup,
        getConfidenceBadgeData,
        getConfidenceToneText,
        getCombinedTooltipText,
        getSidebarConfidenceLabel,
        getSidebarExplanationText,
        boldMarkdown,
    };
})();
