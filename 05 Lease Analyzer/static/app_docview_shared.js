(function() {
    "use strict";

    function buildDocviewDraftDecisionControls(provision, tenantIdx, helpers) {
        if (!provision || provision.final_verdict !== "DEVIATES") return "";
        const esc = helpers.esc;
        const getFinalDraftDecision = helpers.getFinalDraftDecision;
        const pid = provision.provision_id || "";
        const dec = getFinalDraftDecision(tenantIdx, pid);
        const activeChoice = dec ? dec.choice : null;
        const hasSavedCustom = activeChoice === "custom" && dec && dec.text;
        const modifyLabel = hasSavedCustom ? "Keep Modified ✓" : "Modify in Summary...";
        return `
            <span class="fd-decision-label">Draft Decision:</span>
            <button class="fd-btn${activeChoice === 'template' ? ' fd-btn-active' : ''}" data-choice="template"
                onclick="window.CAM.fdChooseSimple(${tenantIdx}, '${esc(pid)}', 'template'); event.stopPropagation();">
                Keep Reference Draft
            </button>
            <button class="fd-btn${activeChoice === 'tenant' ? ' fd-btn-active' : ''}" data-choice="tenant"
                onclick="window.CAM.fdChooseSimple(${tenantIdx}, '${esc(pid)}', 'tenant'); event.stopPropagation();">
                Keep Tenant Draft
            </button>
            <button class="fd-btn${activeChoice === 'custom' ? ' fd-btn-active' : ''}" data-choice="custom"
                onclick="window.CAM.openDocviewModify(${tenantIdx}, '${esc(pid)}'); event.stopPropagation();">
                ${modifyLabel}
            </button>
        `;
    }

    function buildDocviewDeviationControls(provision, tenantIdx, helpers) {
        if (!provision) return "";
        const esc = helpers.esc;
        const resolutionState = helpers.resolutionState;
        const getDocviewDomIdSuffix = helpers.getDocviewDomIdSuffix;
        const buildDraftDecisionControls = helpers.buildDraftDecisionControls;
        const formatResTimestamp = helpers.formatResTimestamp;
        const pid = provision.provision_id || "";
        const suffix = getDocviewDomIdSuffix(pid, tenantIdx);
        const resKey = `${tenantIdx}:${pid}`;
        const res = resolutionState[resKey] || { status: "open", notes: [] };
        const resStatus = res.status || "open";
        const resNotes = res.notes || [];
        const noteCount = resNotes.length;
        const noteCountHtml = noteCount > 0 ? `<span class="res-note-count">${noteCount} note${noteCount !== 1 ? "s" : ""}</span>` : "";
        const statusDefs = [
            { key: "open", label: "Open", cls: "res-open" },
            { key: "in_review", label: "In Review", cls: "res-inreview" },
            { key: "escalated", label: "Escalate to Client", cls: "res-escalated" },
            { key: "not_a_deviation", label: "Not a Deviation", cls: "res-notdeviation" },
            { key: "resolved", label: "Resolved", cls: "res-resolved" },
        ];
        const statusPillsHtml = statusDefs.map((s) =>
            `<button class="res-pill ${s.cls}${resStatus === s.key ? " res-pill-active" : ""}"
                data-status="${s.key}" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}"
                onclick="window.CAM.setResolutionStatus('${esc(pid)}', ${tenantIdx}, '${s.key}', this)">
                ${s.label}
            </button>`
        ).join("");

        const covLinkHtml = window.CAMShared.buildCoverageGapLink(pid, helpers.coverageAssessment, esc);

        return `
            <div class="resolution-bar docview-resolution-bar" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}">
                <div class="res-status-row finding-workflow-row">
                    <div class="workflow-group workflow-group-status">
                        <span class="res-label">Status:</span>
                        <div class="res-pills">${statusPillsHtml}</div>
                        <span class="docview-pipe" aria-hidden="true"></span>
                        <span class="res-tools-label">Tools:</span>
                        <button class="res-notes-toggle" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}"
                            onclick="window.CAM.toggleDocviewResolutionNotes('${esc(pid)}', ${tenantIdx}); event.stopPropagation();">
                            Notes${noteCountHtml ? ` ${noteCountHtml}` : ""}
                        </button>
                        <button class="res-advisor-btn" onclick="window.CAM.openResolutionAdvisor('${esc(pid)}', ${tenantIdx}); event.stopPropagation();">
                            AI Advisor
                        </button>
                    </div>
                    <div class="workflow-divider" aria-hidden="true"></div>
                    <div class="workflow-group workflow-group-decision">
                        ${buildDraftDecisionControls(provision, tenantIdx)}
                    </div>
                    <div class="workflow-divider workflow-divider-spacer" aria-hidden="true"></div>
                    <div class="workflow-open-actions workflow-group">
                        <a class="docview-link card-docview-link card-docview-link--btn"
                           href="#"
                           onclick="window.CAM.openDocviewSummary(${tenantIdx}, '${esc(pid)}'); return false;">
                            Open Lease Summary
                        </a>
                        <a class="card-audit-link card-audit-link--btn"
                           href="#"
                           onclick="window.CAM.jumpToAuditProvision(${tenantIdx}, '${esc(pid)}'); return false;"
                           title="View full CAM analysis in Audit Trail">
                            Open CAM Audit Trail
                        </a>
                        ${covLinkHtml}
                    </div>
                </div>
                <div class="res-notes-panel hidden docview-res-notes-panel" id="docview-res-notes-${suffix}">
                    ${resNotes.map((n, noteIdx) => `
                        <div class="res-note-entry">
                            <span class="res-note-ts">${formatResTimestamp(n.timestamp)}</span>
                            <span class="res-note-text">${esc(n.text)}</span>
                            <button class="res-note-delete" onclick="window.CAM.deleteDocviewResolutionNote('${esc(pid)}', ${tenantIdx}, ${noteIdx}); event.stopPropagation();">Delete</button>
                        </div>`).join("")}
                    <div class="res-note-input-row">
                        <textarea class="res-note-input" id="docview-res-input-${suffix}"
                            placeholder="Add a note..." rows="2"></textarea>
                        <button class="res-note-save-btn"
                            onclick="window.CAM.saveDocviewResolutionNote('${esc(pid)}', ${tenantIdx})">Save</button>
                    </div>
                </div>
            </div>
        `;
    }

    function buildDocviewConformingControls(provision, tenantIdx, helpers) {
        if (!provision || !provision.provision_id || provision.provision_id === "LP-00") return "";
        const esc = helpers.esc;
        const getConformingConcernState = helpers.getConformingConcernState;
        const pid = provision.provision_id;
        const concernState = getConformingConcernState(tenantIdx, pid);

        const covLinkHtml = window.CAMShared.buildCoverageGapLink(pid, helpers.coverageAssessment, esc);

        return `
            <div class="conforming-concern-bar docview-concern-bar">
                <span class="conforming-concern-label">Mark:</span>
                <button class="conforming-concern-btn${concernState === 'concern' ? ' concern-active' : ''}"
                    onclick="window.CAM.handleConformingConcernAction('${esc(pid)}', 'concern'); event.stopPropagation();">
                    Note a concern
                </button>
                <button class="conforming-concern-btn${concernState === 'flag' ? ' flag-active' : ''}"
                    onclick="window.CAM.handleConformingConcernAction('${esc(pid)}', 'flag'); event.stopPropagation();">
                    Escalate as Deviation
                </button>
                ${concernState !== 'none' ? `<button class="conforming-concern-btn"
                    onclick="window.CAM.handleConformingConcernAction('${esc(pid)}', 'clear'); event.stopPropagation();">Clear</button>` : ""}
                <div class="workflow-open-actions workflow-group">
                    <a class="docview-link card-docview-link card-docview-link--btn"
                       href="#"
                       onclick="window.CAM.openDocviewSummary(${tenantIdx}, '${esc(pid)}'); return false;">
                        Open Lease Summary
                    </a>
                    <a class="card-audit-link card-audit-link--btn"
                       href="#"
                       onclick="window.CAM.jumpToAuditProvision(${tenantIdx}, '${esc(pid)}'); return false;"
                       title="View full CAM analysis in Audit Trail">
                        Open CAM Audit Trail
                    </a>
                    ${covLinkHtml}
                </div>
            </div>
        `;
    }

    function buildTocSeverityMaps(provisions, primarySide, helpers) {
        const isDeviationWorkflowProvision = helpers.isDeviationWorkflowProvision;
        const sectionMap = new Map();
        const articleMap = new Map();
        const severityRank = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

        const promote = (map, key, severity) => {
            if (!key || !severity) return;
            const current = map.get(key);
            if (!current || (severityRank[severity] || 0) > (severityRank[current] || 0)) {
                map.set(key, severity);
            }
        };

        (provisions || []).forEach((p) => {
            if (!isDeviationWorkflowProvision(p)) return;
            const severity = (p.severity || "MEDIUM").toUpperCase();
            const ref = primarySide === "template" ? (p.template_section_ref || "") : (p.tenant_section_ref || "");
            if (!ref) return;
            const sectionMatch = ref.match(/Sections?\s+([\d.]+)/i);
            if (sectionMatch) promote(sectionMap, sectionMatch[1], severity);
            const articleMatch = ref.match(/Article\s+([IVXLC\d]+)/i);
            if (articleMatch) promote(articleMap, articleMatch[1].toUpperCase(), severity);
        });

        return { sectionMap, articleMap };
    }

    function parseSidebarTocOutline(fullText) {
        if (!fullText) return { articles: [], sections: [], outline: [] };
        const articlePattern = /^(?:={3,}\s*)?(?:ARTICLE\s+[IVXLC\d]+\s*[—–\-]\s*(.+?))(?:\s*={3,})?$/gmi;
        const sectionPattern = /^Section\s+([\d.]+)\.\s+(.+)$/gmi;
        const articles = [];
        const sections = [];
        let match;

        while ((match = articlePattern.exec(fullText)) !== null) {
            articles.push({ title: match[0].replace(/={3,}/g, "").trim(), index: match.index });
        }
        while ((match = sectionPattern.exec(fullText)) !== null) {
            const sectionNumber = match[1];
            const remainder = (match[2] || "").trim();
            const shortTitle = remainder.split(".")[0].trim();
            sections.push({
                title: shortTitle ? `Section ${sectionNumber}. ${shortTitle}` : `Section ${sectionNumber}`,
                index: match.index,
                sectionNumber
            });
        }

        const outline = articles
            .map((entry) => ({ ...entry, type: "article" }))
            .concat(sections.map((entry) => ({ ...entry, type: "section" })))
            .sort((a, b) => a.index - b.index);

        return { articles, sections, outline };
    }

    function buildSidebarArticleGroups(articles, sections, outline) {
        return (articles || []).map((article, idx) => {
            const nextArticleIndex = idx < articles.length - 1 ? articles[idx + 1].index : Number.POSITIVE_INFINITY;
            const groupedSections = (sections || []).filter((section) => section.index > article.index && section.index < nextArticleIndex);
            return {
                ...article,
                outlineIndex: (outline || []).findIndex((entry) => entry.type === "article" && entry.index === article.index),
                articleToken: (article.title.match(/ARTICLE\s+([IVXLC\d]+)/i) || [null, ""])[1].toUpperCase(),
                sections: groupedSections.map((section) => ({
                    ...section,
                    outlineIndex: (outline || []).findIndex((entry) => entry.type === "section" && entry.index === section.index)
                }))
            };
        });
    }

    window.CAMDocviewShared = {
        buildDocviewDraftDecisionControls,
        buildDocviewDeviationControls,
        buildDocviewConformingControls,
        buildTocSeverityMaps,
        parseSidebarTocOutline,
        buildSidebarArticleGroups,
    };
})();
