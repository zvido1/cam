(function () {
"use strict";

const PROVISION_FLAG_RATES = {
    "LP-01": 0.26, "LP-02": 0.11, "LP-03": 0.33, "LP-04": 0.09,
    "LP-05": 0.41, "LP-06": 0.27, "LP-07": 0.31, "LP-08": 0.30,
    "LP-09": 0.62, "LP-10": 0.38, "LP-11": 0.60, "LP-12": 0.46,
    "LP-13": 0.60, "LP-14": 0.26, "LP-15": 0.14, "LP-16": 0.32,
    "LP-17": 0.05, "LP-18": 0.22,
};

const VARIABLE_COST_PER_FLAGGED = 40;
const EXTRACTION_BASE_SECS = 180;

const PROCESSING_STAGE_WEIGHTS = {
    1: 0.46,
    2: 0.08,
    3: 0.22,
    4: 0.08,
    5: 0.10,
    6: 0.06,
};

function calcEstimate(provCount, idChecks, numLeases, selectedIds) {
    const idCheckCount = idChecks
        ? [idChecks.landlord, idChecks.property, idChecks.tenant].filter(Boolean).length
        : 0;

    let variableSecs = 0;
    if (selectedIds && selectedIds.length > 0) {
        selectedIds.forEach((pid) => {
            const rate = PROVISION_FLAG_RATES[pid] !== undefined
                ? PROVISION_FLAG_RATES[pid]
                : 0.85;
            variableSecs += rate * VARIABLE_COST_PER_FLAGGED;
        });
    } else {
        variableSecs = provCount * 0.35 * VARIABLE_COST_PER_FLAGGED;
    }

    const identitySecs = idCheckCount * 10;
    const gapRepairBuffer = provCount >= 12 ? 300 : 180;
    const parsingSecs = EXTRACTION_BASE_SECS + identitySecs;
    const provisionSecs = variableSecs;
    const bufferSecs = gapRepairBuffer;
    const secsPerLease = Math.max(60, parsingSecs + provisionSecs + bufferSecs);
    const minsPerLease = Math.ceil(secsPerLease / 60);
    const totalMins = Math.max(1, numLeases * minsPerLease);

    const leaseLabel = `${numLeases} lease${numLeases > 1 ? "s" : ""}`;
    const totalProvisionReviews = Math.max(0, provCount * numLeases);
    const provisionLabel = totalProvisionReviews > 0
        ? `, ${totalProvisionReviews} provision${totalProvisionReviews !== 1 ? "s" : ""} (${provCount}x${numLeases})`
        : "";
    const idLabel = idCheckCount > 0 ? `, ${idCheckCount} identity check${idCheckCount !== 1 ? "s" : ""}` : "";
    const detail = `${leaseLabel}${provisionLabel}${idLabel}`;

    return {
        mins: totalMins,
        minsPerLease,
        detail,
        secsPerLease,
        parsingSecs,
        provisionSecs,
        bufferSecs
    };
}

function formatDurationShort(totalSecs) {
    const secs = Math.max(0, Math.round(totalSecs || 0));
    const mins = Math.floor(secs / 60);
    const remSecs = secs % 60;
    return mins > 0 ? `${mins}m ${remSecs}s` : `${remSecs}s`;
}

function formatDurationApprox(totalSecs) {
    const mins = Math.max(1, Math.round((totalSecs || 0) / 60));
    return mins === 1 ? "~1 minute" : `~${mins} minutes`;
}

function getProcessingStageCopy(stage, detail) {
    const fallbackDetail = detail || "";
    switch (Number(stage) || 0) {
        case 1:
            return {
                headline: "Parsing and mapping the lease documents",
                detail: fallbackDetail || "CAM is extracting the clause structure, including LP-00, and aligning the tenant lease to the standard form."
            };
        case 2:
            return {
                headline: "Checking clause patterns and rule triggers",
                detail: fallbackDetail || "CAM is looking for structured signals that suggest a provision may deviate from the standard lease."
            };
        case 3:
            return {
                headline: "Reviewing provisions with multiple AI evaluators",
                detail: fallbackDetail || "CAM is asking separate evaluators to compare provisions independently and explain what changed."
            };
        case 4:
            return {
                headline: "Testing evaluator agreement and challenge paths",
                detail: fallbackDetail || "CAM is checking whether the finding holds up when evaluator conclusions are challenged."
            };
        case 5:
            return {
                headline: "Assessing business risk and severity",
                detail: fallbackDetail || "CAM is turning the confirmed clause changes into practical risk levels and attorney action signals."
            };
        case 6:
            return {
                headline: "Finalizing findings and generating outputs",
                detail: fallbackDetail || "CAM is locking in final verdicts, summaries, and deliverables."
            };
        default:
            return {
                headline: "Preparing the analysis",
                detail: fallbackDetail || "CAM is starting the lease review workflow."
            };
    }
}

function getTenantProgressFraction(tenant, jobStatus) {
    const effectiveStatus = (tenant.status === "queued" && jobStatus === "processing")
        ? "processing"
        : tenant.status;

    if (effectiveStatus === "completed" || effectiveStatus === "failed" || effectiveStatus === "cancelled") {
        return 1;
    }

    if (effectiveStatus === "processing" && tenant.current_stage && tenant.total_stages) {
        const stage = Number(tenant.current_stage) || 0;
        const orderedStages = Object.keys(PROCESSING_STAGE_WEIGHTS)
            .map(Number)
            .sort((a, b) => a - b);
        let completedWeight = 0;
        orderedStages.forEach((s) => {
            if (s < stage) completedWeight += PROCESSING_STAGE_WEIGHTS[s] || 0;
        });
        const currentWeight = PROCESSING_STAGE_WEIGHTS[stage] || 0.08;
        return Math.max(0, Math.min(1, completedWeight + (currentWeight * 0.5)));
    }

    if (effectiveStatus === "processing") {
        return 0.08;
    }

    return 0;
}

function getResultsScrollContainer() {
    return document.getElementById("results-content") || document.querySelector(".results-content");
}

function getContractDetailStickyHeight() {
    const stickyShell = document.querySelector(".contract-detail-sticky-shell");
    if (!stickyShell || stickyShell.classList.contains("hidden")) return 0;
    return Math.round(stickyShell.getBoundingClientRect().height || 0);
}

function scrollResultsTargetIntoView(target, extraOffset) {
    if (!target) return;
    const scrollContainer = getResultsScrollContainer();
    if (!scrollContainer) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
    }

    const containerRect = scrollContainer.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const stickyOffset = getContractDetailStickyHeight();
    const topOffset = stickyOffset + (extraOffset || 0);
    const nextTop = scrollContainer.scrollTop + (targetRect.top - containerRect.top) - topOffset;
    scrollContainer.scrollTo({ top: Math.max(0, nextTop), behavior: "smooth" });
}

function flashResultsTarget(target, duration) {
    if (!target) return;
    target.classList.add("highlight-flash");
    setTimeout(() => target.classList.remove("highlight-flash"), duration || 1500);
}

function waitForResultsTarget(findFn, options) {
    const attempts = (options && options.attempts) || 12;
    const delay = (options && options.delay) || 80;
    let remaining = attempts;

    return new Promise((resolve) => {
        const tick = () => {
            let target = null;
            try {
                target = findFn();
            } catch (err) {
                target = null;
            }
            if (target || remaining <= 0) {
                resolve(target || null);
                return;
            }
            remaining -= 1;
            setTimeout(tick, delay);
        };
        tick();
    });
}

window.CAMShared = {
    PROVISION_FLAG_RATES,
    VARIABLE_COST_PER_FLAGGED,
    EXTRACTION_BASE_SECS,
    PROCESSING_STAGE_WEIGHTS,
    calcEstimate,
    formatDurationShort,
    formatDurationApprox,
    getProcessingStageCopy,
    getTenantProgressFraction,
    getResultsScrollContainer,
    getContractDetailStickyHeight,
    scrollResultsTargetIntoView,
    flashResultsTarget,
    waitForResultsTarget,
};
})();
