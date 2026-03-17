(function() {
    "use strict";

    function buildSideBySideDocviewMarkup(provisions, options, helpers) {
        const esc = helpers.esc;
        const computeWordDiff = helpers.computeWordDiff;
        const renderCredibilityLine = helpers.renderCredibilityLine;
        const isDeviationWorkflowProvision = helpers.isDeviationWorkflowProvision;
        const isNoted = helpers.isNoted;
        const buildDocviewDeviationControls = helpers.buildDocviewDeviationControls;
        const buildDocviewConformingControls = helpers.buildDocviewConformingControls;
        const SEVERITY_ICONS = helpers.SEVERITY_ICONS || {};

        const tenantLeads = !!options.tenantLeads;
        const templateFile = options.templateFile || "Standard Template";
        const tenantFile = options.tenantFile || "Tenant Lease";
        const tenantIdx = options.tenantIdx;
        const modelsUsed = options.modelsUsed || {};
        const docviewSort = options.docviewSort || "contract";
        const openDocviewProvision = options.openDocviewProvision || null;

        let html = "";
        html += `<div class="docview-sbs-sticky-header">`;
        html += `<div class="docview-back-link">&#8592; Back to Summary</div>`;
        html += `<div class="docview-sbs-column-header-row">`;

        const referenceHeaderClass = docviewSort === "reference" ? "docview-column-header-primary" : "docview-column-header-secondary";
        const tenantHeaderClass = docviewSort === "contract" ? "docview-column-header-primary" : "docview-column-header-secondary";
        if (tenantLeads) {
            html += `<div class="docview-column-header ${referenceHeaderClass}">Standard Template &mdash; ${esc(templateFile)}</div>`;
            html += `<div class="docview-column-header ${tenantHeaderClass}">Tenant Lease &mdash; ${esc(tenantFile)}</div>`;
        } else {
            html += `<div class="docview-column-header ${tenantHeaderClass}">Tenant Lease &mdash; ${esc(tenantFile)}</div>`;
            html += `<div class="docview-column-header ${referenceHeaderClass}">Standard Template &mdash; ${esc(templateFile)}</div>`;
        }
        html += `</div>`;
        html += `</div>`;
        html += `<div class="docview-sbs-body">`;

        (provisions || []).forEach((p) => {
            const pid = p.provision_id || "";
            const pname = p.provision_name || "";
            const verdict = p.final_verdict || "";
            const severity = p.severity || "";
            const sectionRef = p.tenant_section_ref || "";
            const templateText = p.template_text || "";
            const tenantText = p.tenant_text || "";
            const templateSectionRef = p.template_section_ref || "";
            const tenantSectionRef = p.tenant_section_ref || "";
            const status = (p.cam_metadata || {}).extraction_status || "";
            const isWorkflowProvision = isDeviationWorkflowProvision(p, tenantIdx);
            const credibilityLine = isWorkflowProvision
                ? renderCredibilityLine(p, modelsUsed, tenantIdx, pid, severity)
                : "";

            let rowClass = "conforms";
            let severityBadge = "";
            let templateContent = esc(templateText) || '<span style="color:var(--text-muted); font-style:italic;">No text extracted</span>';
            let tenantContent = esc(tenantText) || '<span style="color:var(--text-muted); font-style:italic;">No text extracted</span>';

            if (verdict === "DEVIATES") {
                rowClass = "deviation";
                const icon = SEVERITY_ICONS[severity] || "";
                severityBadge = `<span class="severity-badge severity-${severity}">${icon} ${severity}</span>`;

                if (templateText && tenantText) {
                    const diff = computeWordDiff(templateText, tenantText);
                    templateContent = diff.templateHtml;
                    tenantContent = diff.tenantHtml;
                } else if (!tenantText) {
                    tenantContent = '<span style="color:var(--text-muted); font-style:italic;">Not found in tenant lease</span>';
                }
            } else if (status === "TEMPLATE_ONLY" || !tenantText) {
                rowClass = "omission";
                tenantContent = "&#9888;&#65039; Not found in tenant lease";
            }

            const analysisToggle = isWorkflowProvision
                ? `<button class="docview-header-toggle${openDocviewProvision === pid ? " open" : ""}"
                        data-pid="${esc(pid)}"
                        title="${openDocviewProvision === pid ? "Hide analysis" : "Show analysis"}"
                        onclick="event.stopPropagation(); window.CAM.toggleDocviewAnalysis('${esc(pid)}');">
                        ${openDocviewProvision === pid ? "▴" : "▾"}
                   </button>`
                : "";
            const readBtn = `<button class="finding-read-toggle${isNoted(tenantIdx, pid) ? " noted-active" : ""}"
                    title="Mark this provision as read"
                    onclick="window.CAM.toggleNoted(${tenantIdx}, '${esc(pid)}', this); event.stopPropagation();">
                ${isNoted(tenantIdx, pid) ? "✓ Read" : "Mark as Read"}
            </button>`;

            html += `<div class="docview-provision-header docview-${rowClass}" data-pid="${esc(pid)}" data-template-ref="${esc(templateSectionRef)}" data-tenant-ref="${esc(tenantSectionRef)}" id="sidebyside-${esc(pid)}">
                <div class="deviation-header-main">
                    <div class="deviation-header-left">
                        <span class="provision-title">${esc(pid)} ${esc(pname)}</span>
                        ${severityBadge}
                        ${credibilityLine || ""}
                    </div>
                    <div class="deviation-header-right">
                        ${sectionRef ? `<span class="section-ref">${esc(sectionRef)}</span>` : ""}
                    </div>
                </div>
                <div class="deviation-header-actions">
                    ${readBtn}
                    ${analysisToggle}
                </div>
            </div>`;

            if (tenantLeads) {
                html += `<div class="docview-text docview-template docview-${rowClass}">${templateContent}</div>`;
                html += `<div class="docview-text docview-tenant docview-${rowClass}">${tenantContent}</div>`;
            } else {
                html += `<div class="docview-text docview-tenant docview-${rowClass}">${tenantContent}</div>`;
                html += `<div class="docview-text docview-template docview-${rowClass}">${templateContent}</div>`;
            }

            const whatChanged = (p.challenge_details || "").trim();
            const recommendedAction = (p.recommended_action || "").trim();
            if (isWorkflowProvision && (whatChanged || recommendedAction)) {
                html += `<div class="docview-clause-summary" style="grid-column: 1 / -1;">`;
                if (whatChanged) {
                    html += `<div class="detail-section">
                        <div class="detail-label">What Changed</div>
                        <div class="detail-text">${esc(whatChanged)}</div>
                    </div>`;
                }
                if (recommendedAction) {
                    html += `<div class="detail-section">
                        <div class="detail-label">Recommended Action</div>
                        <div class="detail-text">${esc(recommendedAction)}</div>
                    </div>`;
                }
                html += `</div>`;
            }

            if (isWorkflowProvision) {
                html += `<div class="docview-row-controls" style="grid-column: 1 / -1;">${buildDocviewDeviationControls(p, tenantIdx)}</div>`;
            } else {
                html += `<div class="docview-row-controls" style="grid-column: 1 / -1;">${buildDocviewConformingControls(p, tenantIdx)}</div>`;
            }
        });

        html += `</div>`;
        return html;
    }

    window.CAMDocviewRenderShared = {
        buildSideBySideDocviewMarkup,
    };
})();
