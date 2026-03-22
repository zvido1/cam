(function() {
    "use strict";

    function buildConformingConcernBar(provision, tenantIdx, concernState, helpers) {
        const esc = helpers.esc;
        const pid = provision.provision_id || "";
        return `
            <div class="conforming-concern-bar">
                <span class="conforming-concern-label">Mark:</span>
                <button class="conforming-concern-btn${concernState === 'concern' ? ' concern-active' : ''}"
                    data-pid="${esc(pid)}" data-action="concern">
                    Note a concern
                </button>
                <button class="conforming-concern-btn${concernState === 'flag' ? ' flag-active' : ''}"
                    data-pid="${esc(pid)}" data-action="flag">
                    Escalate as Deviation
                </button>
                ${concernState !== 'none' ? `<button class="conforming-concern-btn" data-pid="${esc(pid)}" data-action="clear" style="color:var(--text-muted);">✕ Clear</button>` : ""}
                <div class="workflow-open-actions workflow-group">
                    <a class="card-docview-link card-docview-link--btn"
                       href="#"
                       onclick="window.CAM.jumpToDocview('${esc(pid)}'); return false;"
                       title="Open this clause in Document Comparison">
                        Open Document Comparison
                    </a>
                    <a class="card-audit-link card-audit-link--btn"
                       href="#"
                       onclick="window.CAM.jumpToAuditProvision(${tenantIdx}, '${esc(pid)}'); return false;"
                       title="View full CAM analysis in Audit Trail">
                        Open CAM Audit Trail
                    </a>
                </div>
            </div>`;
    }

    function buildConformingItem(provision, options, helpers) {
        const esc = helpers.esc;
        const isNoted = helpers.isNoted;
        const getDissentingEvaluators = helpers.getDissentingEvaluators;

        const pid = provision.provision_id || "";
        const detailId = `conf-detail-${pid}`;
        const concernState = options.concernState || "none";
        const evalNames = options.evalNames || {};
        const sectionRef = provision.tenant_section_ref || provision.template_section_ref || "";
        const summaryMeta = options.summaryMeta || "";
        const dissenters = getDissentingEvaluators(provision, evalNames);

        const discoveredTag = provision.discovered
            ? ` <span class="discovered-inline">🔍</span>`
            : "";

        const concernBadge = concernState === "flag"
            ? ` <span style="font-size:0.7rem;background:#fee2e2;color:#991b1b;padding:1px 6px;border-radius:3px;font-weight:600;">⚠ Flagged</span>`
            : concernState === "concern"
            ? ` <span style="font-size:0.7rem;background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:3px;font-weight:600;">📋 Concern noted</span>`
            : "";

        const tmplText = provision.template_text || "";
        const tenantText = provision.tenant_text || "";
        const clausePairHtml = (tmplText || tenantText) ? `
            <div class="conforming-clause-pair">
                <div class="conforming-clause-col">
                    <div class="conforming-clause-label">Reference Lease</div>
                    <div class="conforming-clause-text">${esc(tmplText || "—")}</div>
                </div>
                <div class="conforming-clause-col">
                    <div class="conforming-clause-label">Tenant Lease</div>
                    <div class="conforming-clause-text">${esc(tenantText || "—")}</div>
                </div>
            </div>` : `<div style="font-size:0.8rem;color:var(--text-muted);padding:0.25rem 0;">Clause text not available — view in Audit Trail.</div>`;

        let dissentHtml = "";
        if (dissenters.length > 0) {
            const dissentPanelId = `dissent-${pid}`;
            const flagLabel = dissenters.length === 1
                ? "1 evaluator flagged"
                : `${dissenters.length} evaluators flagged`;
            const panels = dissenters.map(d => `
                <div class="dissent-evaluator">
                    <div class="dissent-evaluator-header">
                        <span class="dissent-evaluator-name">${esc(d.name)}</span>
                        <span class="evaluator-verdict verdict-DEVIATES">DEVIATES</span>
                    </div>
                    <div class="dissent-evaluator-reasoning">${esc(d.reasoning)}</div>
                </div>`).join("");
            dissentHtml = `
                <div class="dissent-toggle" data-target="${dissentPanelId}">
                    &#9873; ${esc(flagLabel)} &middot; challenger determined cosmetic
                    <span class="dissent-chevron">&#9662;</span>
                </div>
                <div class="dissent-panel hidden" id="${dissentPanelId}">
                    <div class="dissent-panel-header">&#9873; Minority Flag &mdash; Challenger Overruled</div>
                    <div class="dissent-panel-intro">One evaluator independently flagged this provision as a deviation. The challenger reviewed the reasoning and determined the difference is cosmetic. Shown for transparency.</div>
                    ${panels}
                </div>`;
        }

        return `<li class="conforming-item${dissenters.length > 0 ? " has-dissent" : ""}" data-pid="${esc(pid)}">
            <div class="conforming-main" data-detail-id="${detailId}">
                <div class="conforming-main-left">
                    <div class="conforming-summary-title-row">
                        <span class="conforming-summary-title">${esc(pid)} ${esc(provision.provision_name)}</span>${discoveredTag}${concernBadge}
                    </div>
                    ${summaryMeta ? `<div class="conforming-summary-meta">${esc(summaryMeta)}</div>` : ""}
                </div>
                <div class="conforming-main-right">
                    ${sectionRef ? `<span class="section-ref">${esc(sectionRef)}</span>` : ""}
                    <button class="finding-read-toggle${isNoted(options.tenantIdx, pid) ? " noted-active" : ""}"
                        title="Mark this provision as read"
                        onclick="window.CAM.toggleNoted(${options.tenantIdx}, '${esc(pid)}', this); event.stopPropagation();">
                        ${isNoted(options.tenantIdx, pid) ? "Read" : "Mark as Read"}
                    </button>
                    <span class="conforming-chevron">&#9652;</span>
                </div>
            </div>
            <div class="conforming-detail" id="${detailId}">
                ${clausePairHtml}
                ${dissentHtml}
                ${buildConformingConcernBar(provision, options.tenantIdx, concernState, helpers)}
            </div>
        </li>`;
    }

    window.CAMSummaryShared = {
        buildConformingConcernBar,
        buildConformingItem,
    };
})();
