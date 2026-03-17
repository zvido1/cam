(function() {
    "use strict";

    function isManualEscalatedProvision(provision, concernState) {
        if (!provision || provision.provision_id === "LP-00" || provision.final_verdict !== "CONFORMS") return false;
        return concernState === "flag";
    }

    function isDeviationWorkflowProvision(provision, concernState) {
        if (!provision || provision.provision_id === "LP-00") return false;
        return provision.final_verdict === "DEVIATES"
            || provision.final_verdict === "UNCLEAR"
            || isManualEscalatedProvision(provision, concernState);
    }

    function buildManualEscalatedProvision(provision, reason) {
        return {
            ...provision,
            final_verdict: "DEVIATES",
            severity: (provision.severity || "MEDIUM").toUpperCase(),
            risk_headline: reason || "Manually escalated from conforming provision",
            challenge_details: reason || "Reviewer manually escalated this conforming clause into the deviation workflow.",
            recommended_action: "Review this manually escalated clause using the same workflow tools as other deviations.",
            manual_escalation: true,
        };
    }

    function getDeviationWorkflowProvisions(provisions, tenantIdx, helpers) {
        const getConcernState = helpers && helpers.getConcernState ? helpers.getConcernState : function() { return "none"; };
        const getConcernReason = helpers && helpers.getConcernReason ? helpers.getConcernReason : function() { return ""; };
        const base = [];
        (provisions || []).forEach((provision) => {
            if (!provision || provision.provision_id === "LP-00") return;
            if (provision.final_verdict === "DEVIATES" || provision.final_verdict === "UNCLEAR") {
                base.push(provision);
                return;
            }
            const concernState = getConcernState(tenantIdx, provision.provision_id);
            if (isManualEscalatedProvision(provision, concernState)) {
                base.push(buildManualEscalatedProvision(provision, getConcernReason(tenantIdx, provision.provision_id)));
            }
        });
        return base;
    }

    function getDocviewWorkflowProvisions(provisions, tenantIdx, helpers) {
        const getConcernState = helpers && helpers.getConcernState ? helpers.getConcernState : function() { return "none"; };
        const getConcernReason = helpers && helpers.getConcernReason ? helpers.getConcernReason : function() { return ""; };
        return (provisions || []).map((provision) => {
            const concernState = getConcernState(tenantIdx, provision && provision.provision_id);
            if (isManualEscalatedProvision(provision, concernState)) {
                return buildManualEscalatedProvision(provision, getConcernReason(tenantIdx, provision.provision_id));
            }
            return provision;
        });
    }

    function getContractResolutionKey(jobId, tenant, tenantIdx) {
        const name = tenant ? (tenant.filename || `tenant_${tenantIdx}`) : `tenant_${tenantIdx}`;
        return `cam_res_${jobId}_${name}`;
    }

    function getContractResolution(jobId, tenant, tenantIdx, workflowProvisions, resolutionState, storage) {
        if (!tenant || !tenant.results) return "unreviewed";
        if ((workflowProvisions || []).length === 0) return "clean";
        const allClosed = (workflowProvisions || []).every((provision) => {
            const key = `${tenantIdx}:${provision.provision_id}`;
            const status = (resolutionState[key] || {}).status || "open";
            return status === "resolved" || status === "not_a_deviation";
        });
        if (allClosed) return "resolved";
        const key = getContractResolutionKey(jobId, tenant, tenantIdx);
        try {
            return storage.getItem(key) || "unreviewed";
        } catch (err) {
            return "unreviewed";
        }
    }

    window.CAMWorkflowShared = {
        isManualEscalatedProvision,
        isDeviationWorkflowProvision,
        buildManualEscalatedProvision,
        getDeviationWorkflowProvisions,
        getDocviewWorkflowProvisions,
        getContractResolutionKey,
        getContractResolution,
    };
})();
