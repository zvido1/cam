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
        if (asg == null || isNaN(asg)) return { label: "Unknown", tone: "neutral", width: 0 };
        if (asg < 15) return { label: "Low sensitivity", tone: "good", width: 18 };
        if (asg < 35) return { label: "Moderate sensitivity", tone: "caution", width: 46 };
        if (asg < 55) return { label: "High sensitivity", tone: "warning", width: 74 };
        return { label: "Very high sensitivity", tone: "danger", width: 100 };
    }

    function getAuditConfidenceTone(camPerm) {
        if (camPerm == null || isNaN(camPerm)) return { label: "Unknown", tone: "neutral", width: 0 };
        if (camPerm >= 85) return { label: "High confidence", tone: "good", width: camPerm };
        if (camPerm >= 70) return { label: "Strong confidence", tone: "good", width: camPerm };
        if (camPerm >= 50) return { label: "Moderate confidence", tone: "caution", width: camPerm };
        return { label: "Low confidence", tone: "danger", width: Math.max(18, camPerm) };
    }

    function getAuditFragilityTone(fragilityRaw) {
        const score = fragilityRaw && fragilityRaw.fragility_score != null ? Number(fragilityRaw.fragility_score) : null;
        if (score == null || isNaN(score)) return { label: "No fragility score", tone: "neutral", width: 0 };
        const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
        if (pct < 15) return { label: "Low structural fragility", tone: "good", width: pct };
        if (pct < 35) return { label: "Moderate structural fragility", tone: "caution", width: pct };
        if (pct < 60) return { label: "High structural fragility", tone: "warning", width: pct };
        return { label: "Very high structural fragility", tone: "danger", width: pct };
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

    function renderAuditScoreBar(label, value, helper, toneInfo, escFn) {
        const esc = escFn || (value => String(value ?? ""));
        const tone = toneInfo && toneInfo.tone ? toneInfo.tone : "neutral";
        const width = toneInfo && toneInfo.width != null ? toneInfo.width : 0;
        return `<div class="audit-score-card audit-score-${tone}">
            <div class="audit-score-head">
                <span class="audit-score-label">${esc(label)}</span>
                <span class="audit-score-value">${esc(value)}</span>
            </div>
            <div class="audit-score-track"><span class="audit-score-fill audit-score-fill-${tone}" style="width:${Math.max(0, Math.min(100, width))}%"></span></div>
            <div class="audit-score-helper">${esc(helper)}</div>
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
            ASSERT_SIGNAL:        { label: "Confirmed",  cssClass: "confirmed",  dots: "\u25cf\u25cf\u25cf\u25cf" },
            ASSERT_REVIEW_SIGNAL: { label: "Fragile",    cssClass: "fragile",    dots: "\u25cf\u25cf\u25cf\u25cb" },
            REVIEW_SIGNAL:        { label: "Uncertain",  cssClass: "uncertain",  dots: "\u25cf\u25cf\u25cb\u25cb" },
            WITHHOLD_SIGNAL:      { label: "Unverified", cssClass: "unverified", dots: "\u25cf\u25cb\u25cb\u25cb" },
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

    function getConfidenceToneText(governanceSignal) {
        const map = {
            ASSERT_SIGNAL:        "Strong finding \u2014 survived both permissive and strict review",
            ASSERT_REVIEW_SIGNAL: "High confidence, but sensitive to interpretation",
            REVIEW_SIGNAL:        "Mixed evaluator evidence \u2014 verify before acting",
            WITHHOLD_SIGNAL:      "Insufficient confidence to assert \u2014 treat as a flag only",
        };
        return map[governanceSignal] || "";
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
    };
})();
