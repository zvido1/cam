/* ═══════════════════════════════════════════════════════════════
   CAM Lease Analyzer — Frontend Application
   Single-page app with 5 states: gate, select, upload, processing, results
   ═══════════════════════════════════════════════════════════════ */

(() => {
"use strict";

// ── Configuration ──
const ANALYSIS_TYPES = [
    {
        id: "lease_review",
        domain: "Legal",
        name: "CAM™ Intelligence",
        description: "Compare tenant leases against a standard template to detect deviations, assess risk, and generate annotated reports.",
        endpoint: "/api/jobs/lease",
        provisions_endpoint: "/api/provisions"
    }
];

const POLL_INTERVAL_MS = 5000;
const HEADER_TAGLINE = "by Vered.ai";
const SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const SEVERITY_DISPLAY = { CRITICAL: "Critical", HIGH: "High", MEDIUM: "Medium", LOW: "Low", CONFORMS: "Conforms" };
function sevDisplay(s) { return SEVERITY_DISPLAY[(s || "").toUpperCase()] || s || ""; }
const SEVERITY_ICONS = {
    CRITICAL: "\uD83D\uDD34",
    HIGH: "\u26A0\uFE0F",
    MEDIUM: "\u26A0",
    LOW: "\u2139\uFE0F",
    CONFORMS: "\u2705"
};

// ── Model Display Names (populated from /api/models at startup) ──
let MODEL_DISPLAY_NAMES = {};
let EVALUATOR_SLOT_NAMES = {};  // slot letter → display name, e.g. { A: "Claude Sonnet 4.6" }

async function loadModelNames() {
    try {
        const resp = await fetch('/api/models');
        if (resp.ok) {
            const data = await resp.json();
            MODEL_DISPLAY_NAMES = data.display_names || {};
            EVALUATOR_SLOT_NAMES = data.evaluator_slots || {};
        }
    } catch (e) {
        console.warn('[CAM] Could not load model names:', e);
    }
}

// Return the display name for an evaluator slot (A/B/C).
// Falls back to "Eval {slot}" if the slot mapping hasn't loaded yet.
function evalName(slot) {
    return EVALUATOR_SLOT_NAMES[slot] || ('Eval ' + slot);
}

// ── Evaluator Color Classes ──
const CAMShared = window.CAMShared || {};
const calcEstimate = CAMShared.calcEstimate || function() { return { mins: 1, minsPerLease: 1, detail: "", secsPerLease: 60, parsingSecs: 0, provisionSecs: 0, bufferSecs: 0 }; };
const formatDurationShort = CAMShared.formatDurationShort || function(totalSecs) { return `${Math.max(0, Math.round(totalSecs || 0))}s`; };
const formatDurationApprox = CAMShared.formatDurationApprox || function(totalSecs) { return `~${Math.max(1, Math.round((totalSecs || 0) / 60))} minutes`; };
const getProcessingStageCopy = CAMShared.getProcessingStageCopy || function(stage, detail) { return { headline: `Stage ${stage || 0}`, detail: detail || "" }; };
const getTenantProgressFraction = CAMShared.getTenantProgressFraction || function() { return 0; };
const getResultsScrollContainer = CAMShared.getResultsScrollContainer || function() { return document.getElementById("results-content") || document.querySelector(".results-content"); };
const getContractDetailStickyHeight = CAMShared.getContractDetailStickyHeight || function() { return 0; };
const scrollResultsTargetIntoView = CAMShared.scrollResultsTargetIntoView || function(target) { if (target) target.scrollIntoView({ behavior: "smooth", block: "start" }); };
const flashResultsTarget = CAMShared.flashResultsTarget || function(target, duration) { if (target) { target.classList.add("highlight-flash"); setTimeout(() => target.classList.remove("highlight-flash"), duration || 1500); } };
const waitForResultsTarget = CAMShared.waitForResultsTarget || function(findFn) { return Promise.resolve(findFn()); };
const CAMAuditShared = window.CAMAuditShared || {};
const getAuditGovernanceLabel = CAMAuditShared.getAuditGovernanceLabel || function(signal) { return signal || "—"; };
const getAuditPatternLabel = CAMAuditShared.getAuditPatternLabel || function(pattern) { return pattern || "—"; };
const getAuditAsgTone = CAMAuditShared.getAuditAsgTone || function() { return { label: "Unknown", tone: "neutral", width: 0 }; };
const getAuditConfidenceTone = CAMAuditShared.getAuditConfidenceTone || function() { return { label: "Unknown", tone: "neutral", width: 0 }; };
const getAuditFragilityTone = CAMAuditShared.getAuditFragilityTone || function() { return { label: "No fragility score", tone: "neutral", width: 0 }; };
const getAuditAgreementSummary = CAMAuditShared.getAuditAgreementSummary || function(pattern) { return pattern || "Evaluator agreement was not available."; };
const getAuditEvidenceSummary = CAMAuditShared.getAuditEvidenceSummary || function() { return "CAM reviewed the clause text but the evidence basis was not explicitly labeled."; };
const getAuditReasoningSummary = CAMAuditShared.getAuditReasoningSummary || function() { return "This clause did not move through the full reasoning chain."; };
const getAuditFragilitySummary = CAMAuditShared.getAuditFragilitySummary
    ? function(fragilityRaw) { return CAMAuditShared.getAuditFragilitySummary(fragilityRaw, FRAGILITY_TRANSLATIONS); }
    : function() { return "No structural fragility signals were detected."; };
const renderAuditScoreBar = CAMAuditShared.renderAuditScoreBar
    ? function(label, value, helper, toneInfo, escFn, context) { return CAMAuditShared.renderAuditScoreBar(label, value, helper, toneInfo, esc, context); }
    : function() { return ""; };
const renderAuditRawRecord = CAMAuditShared.renderAuditRawRecord
    ? function(title, record) { return CAMAuditShared.renderAuditRawRecord(title, record, esc); }
    : function() { return ""; };
const renderAuditPromptBlock = CAMAuditShared.renderAuditPromptBlock
    ? function(title, text) { return CAMAuditShared.renderAuditPromptBlock(title, text, esc); }
    : function() { return ""; };
const renderAuditTechnicalGroup = CAMAuditShared.renderAuditTechnicalGroup
    ? function(title, innerHtml) { return CAMAuditShared.renderAuditTechnicalGroup(title, innerHtml, esc); }
    : function() { return ""; };
const getConfidenceBadgeData = CAMAuditShared.getConfidenceBadgeData || function() { return null; };
const getConfidenceToneText = CAMAuditShared.getConfidenceToneText || function() { return ""; };
const CAMWorkflowShared = window.CAMWorkflowShared || {};
const isManualEscalatedProvision = CAMWorkflowShared.isManualEscalatedProvision
    ? function(p, tenantIdx = currentTenantIndex) { return CAMWorkflowShared.isManualEscalatedProvision(p, getConformingConcernState(tenantIdx, p && p.provision_id)); }
    : function() { return false; };
const isDeviationWorkflowProvision = CAMWorkflowShared.isDeviationWorkflowProvision
    ? function(p, tenantIdx = currentTenantIndex) { return CAMWorkflowShared.isDeviationWorkflowProvision(p, getConformingConcernState(tenantIdx, p && p.provision_id)); }
    : function(p) { return !!(p && p.final_verdict === "DEVIATES"); };
const buildManualEscalatedProvision = CAMWorkflowShared.buildManualEscalatedProvision
    ? function(p, tenantIdx = currentTenantIndex) { return CAMWorkflowShared.buildManualEscalatedProvision(p, getConformingConcernReason(tenantIdx, p && p.provision_id)); }
    : function(p) { return p; };
const getDeviationWorkflowProvisions = CAMWorkflowShared.getDeviationWorkflowProvisions
    ? function(provisions, tenantIdx = currentTenantIndex) {
        return CAMWorkflowShared.getDeviationWorkflowProvisions(provisions, tenantIdx, {
            getConcernState: getConformingConcernState,
            getConcernReason: getConformingConcernReason,
        });
    }
    : function(provisions) { return provisions || []; };
const getDocviewWorkflowProvisions = CAMWorkflowShared.getDocviewWorkflowProvisions
    ? function(provisions, tenantIdx = currentTenantIndex) {
        return CAMWorkflowShared.getDocviewWorkflowProvisions(provisions, tenantIdx, {
            getConcernState: getConformingConcernState,
            getConcernReason: getConformingConcernReason,
        });
    }
    : function(provisions) { return provisions || []; };
const getContractResolutionKey = CAMWorkflowShared.getContractResolutionKey
    ? function(tenantIdx) {
        const tenant = currentResults && currentResults.tenants && currentResults.tenants[tenantIdx];
        return CAMWorkflowShared.getContractResolutionKey(currentJobId, tenant, tenantIdx);
    }
    : function(tenantIdx) { return `cam_res_${currentJobId}_tenant_${tenantIdx}`; };
const getContractResolution = CAMWorkflowShared.getContractResolution
    ? function(tenantIdx) {
        const tenant = currentResults && currentResults.tenants && currentResults.tenants[tenantIdx];
        const workflowProvisions = getDeviationWorkflowProvisions(((tenant && tenant.results && tenant.results.provisions) || []), tenantIdx);
        return CAMWorkflowShared.getContractResolution(currentJobId, tenant, tenantIdx, workflowProvisions, resolutionState, localStorage);
    }
    : function() { return "unreviewed"; };
const CAMDocviewShared = window.CAMDocviewShared || {};
const buildDocviewDraftDecisionControls = CAMDocviewShared.buildDocviewDraftDecisionControls
    ? function(provision, tenantIdx) {
        return CAMDocviewShared.buildDocviewDraftDecisionControls(provision, tenantIdx, {
            esc,
            getFinalDraftDecision,
        });
    }
    : function() { return ""; };
const buildDocviewDeviationControls = CAMDocviewShared.buildDocviewDeviationControls
    ? function(provision, tenantIdx) {
        return CAMDocviewShared.buildDocviewDeviationControls(provision, tenantIdx, {
            esc,
            resolutionState,
            getDocviewDomIdSuffix,
            buildDraftDecisionControls: buildDocviewDraftDecisionControls,
            formatResTimestamp,
            coverageAssessment: ((currentResults && currentResults.tenants && currentResults.tenants[tenantIdx]) || {}).results && currentResults.tenants[tenantIdx].results.coverage_assessment || [],
        });
    }
    : function() { return ""; };
const buildDocviewConformingControls = CAMDocviewShared.buildDocviewConformingControls
    ? function(provision, tenantIdx) {
        return CAMDocviewShared.buildDocviewConformingControls(provision, tenantIdx, {
            esc,
            getConformingConcernState,
            coverageAssessment: ((currentResults && currentResults.tenants && currentResults.tenants[tenantIdx]) || {}).results && currentResults.tenants[tenantIdx].results.coverage_assessment || [],
        });
    }
    : function() { return ""; };
const buildTocSeverityMaps = CAMDocviewShared.buildTocSeverityMaps
    ? function(provisions, primarySide = "tenant") {
        return CAMDocviewShared.buildTocSeverityMaps(provisions, primarySide, {
            isDeviationWorkflowProvision: function(p) { return isDeviationWorkflowProvision(p, currentTenantIndex); }
        });
    }
    : function() { return { sectionMap: new Map(), articleMap: new Map() }; };
const parseSidebarTocOutline = CAMDocviewShared.parseSidebarTocOutline || function() { return { articles: [], sections: [], outline: [] }; };
const buildSidebarArticleGroups = CAMDocviewShared.buildSidebarArticleGroups || function() { return []; };
const CAMDocviewRenderShared = window.CAMDocviewRenderShared || {};
const buildSideBySideDocviewMarkup = CAMDocviewRenderShared.buildSideBySideDocviewMarkup
    ? function(provisions, options) {
        return CAMDocviewRenderShared.buildSideBySideDocviewMarkup(provisions, options, {
            esc,
            computeWordDiff,
            renderCredibilityLine,
            isDeviationWorkflowProvision,
            isNoted,
            buildDocviewDeviationControls,
            buildDocviewConformingControls,
            SEVERITY_ICONS,
        });
    }
    : function() { return ""; };
const CAMSummaryShared = window.CAMSummaryShared || {};
const buildConformingItem = CAMSummaryShared.buildConformingItem
    ? function(provision, options) {
        const _ti = options.tenantIdx != null ? options.tenantIdx : currentTenantIndex;
        return CAMSummaryShared.buildConformingItem(provision, options, {
            esc,
            isNoted,
            getDissentingEvaluators,
            coverageAssessment: ((currentResults && currentResults.tenants && currentResults.tenants[_ti]) || {}).results && currentResults.tenants[_ti].results.coverage_assessment || [],
        });
    }
    : function() { return ""; };
const CAMNotesShared = window.CAMNotesShared || {};
const buildNotesToggleHtml = CAMNotesShared.buildNotesToggleHtml || function(label) { return label || "Notes"; };
const renderNotesPanelEntries = CAMNotesShared.renderNotesPanelEntries
    ? function(panel, notes, inputRow, helpers) { return CAMNotesShared.renderNotesPanelEntries(panel, notes, inputRow, helpers); }
    : function() {};

const EVALUATOR_COLORS = {
    A: "eval-blue",
    B: "eval-green",
    C: "eval-red",
};

// Step 308: fallback display labels for evaluator roles — now delegated to evalName() (Step 347i)
const EVAL_ROLE_LABELS = {}; // retained for back-compat; evalName(role) is the canonical source

// ── Fragility Signal Translations (1D) ──
const FRAGILITY_TRANSLATIONS = {
    "exception_clause": "New exception language found in tenant version",
    "definition_override": "Key term redefined differently from template",
    "qualifier_shift": "Obligation strength changed (e.g., 'shall' to 'may')",
    "quantitative_deviation": "Numerical values or thresholds differ",
    "negation_pattern": "New limiting or negating language added",
    "cross_reference_dependency": "Clause depends on other sections that may also differ",
    "omission": "Template language removed or missing from tenant version",
    "obligation_swap": "Party responsibilities shifted (landlord \u2194 tenant)",
};

const ALL_FRAGILITY_SIGNALS = [
    "exception_clause", "definition_override", "qualifier_shift",
    "quantitative_deviation", "negation_pattern", "cross_reference_dependency",
    "omission", "obligation_swap",
];

// ── Pipeline Stage Descriptions (1C) ──
const STAGE_DESCRIPTIONS = {
    1: { name: "Extraction", desc: "Gemini 3.1 Pro (Google) extracted and aligned provision text" },
    2: { name: "Independent Evaluation", desc: "Claude Sonnet 4 (Anthropic), GPT-5.2 (OpenAI), Grok 3 (xAI) each analyzed independently" },
    3: { name: "Challenge", desc: "GPT-5.2 (OpenAI) probed the finding for accuracy" },
    4: { name: "Rules Engine", desc: "8 automated detection rules checked for patterns" },
    5: { name: "Severity Assessment", desc: "GPT-5.2 (OpenAI) evaluated impact and financial risk" },
    6: { name: "Final Disposition", desc: "Rule-based verdict determined" },
};

// ── State ──
let currentState = null;
let currentJobId = null;
let currentJobData = null;
let currentResults = null;
let pollTimer = null;
let expiryTimer = null;
let templateFile = null;
let tenantFiles = [];
let tenantDragIndex = null;
let provisions = [];
let customProvisions = [];
let selectedAnalysisType = ANALYSIS_TYPES[0];
let currentTenantIndex = 0;
let navSidebarFocusMap = {};
let activeResultsTab = "findings";
let openDocviewProvision = null; // track which provision's analysis panel is open
let docviewReturnTarget = null; // track which provision to scroll back to
let docviewMode = "sidebyside"; // "full" or "sidebyside" — default to side-by-side
let docviewSort = "contract";   // "contract" or "reference" — tenant-led or reference-led docview order
let pollNotFoundCount = 0;
let addMoreMode = null; // null or "addmore"
let modeExplicitlySelected = false;
let jobEmail = null;    // Tracks confirmed notification email across all screens
let templateSummary = null;      // Step 138: {landlord, property, base_rent, lease_term, gate_passed}
let identityChecks = {           // Step 138: which identity fields to verify (all off by default)
    landlord: false,
    property: false,
    tenant: false,
};
let lockedProvisionIds = new Set();
let chatHistory = [];
let cancelRequested = false;
let currentSecsPerLease = 240; // Step 195: per-lease time estimate, updated at submission
let jobStartTime = null;           // Step 196: wall-clock start of current job
let processingDetailsExpanded = false;
let estimateCountdownTimer = null; // Step 196: per-second countdown ticker
let estimateTotalSecs = 0;         // Step 196: total estimated seconds for this job
let estimateProgressFraction = 0;  // Step 196: whole-job completion fraction
let resolutionState = {};   // key: "{tenantIdx}:{pid}" → {status, notes, updated_at}
let finalDraftDecisions = {};  // key: "{tenantIdx}:{pid}" → {choice: 'template'|'tenant'|'custom', text: '...'}
let contractSummaryCollapseState = {};
let isAddMoreRun = false;
let activeTopTab = "overview";     // "overview" | "snapshot"
let contractDetailOpen = false;
let contractDetailIdx = -1;
let snapshotActiveIndex = null;    // Step 120: remembers open contract in Run Snapshot
let snapshotVisited = false;       // Step 122: true after first visit to Run Snapshot tab
let snapshotSort = 'risk';         // Step 124: sort dropdown
let snapshotSeverityFilter = new Set(); // empty = All
let snapshotConfidenceFilter = new Set(); // empty = All
let snapshotStatusFilter = 'all';  // Step 124: status filter
let snapshotSearch = '';           // Step 124: live search text
let snapshotContractFilter = new Set(); // Step 130: empty = show all
let contractClauseSeverityFilter = new Set(); // empty = All
let contractClauseStatusFilter = 'all';
let contractClauseReadFilter = 'all';
let contractClauseNotesFilter = 'all';
let contractClauseConfidenceFilter = new Set(); // empty = All
let contractClauseProvisionFilter = new Set(); // empty = All provisions
let contractClauseSort = 'severity'; // severity | confidence | provision_id
let contractPickerSeverityFilter = 'all';
let contractDetailRenderPromise = Promise.resolve();

// Global provision ID sort key: LP-xx (0,xx), CUSTOM-xx (1,xx), ADDED-xx (2,xx)
function pidSortKeyGlobal(pid) {
    const m = (pid || "").match(/^(LP|CUSTOM|ADDED)-(\d+)/i);
    if (!m) return [2, 999];
    const prefix = m[1].toUpperCase();
    const num = parseInt(m[2], 10);
    if (prefix === "LP") return [0, num];
    if (prefix === "CUSTOM") return [1, num];
    return [2, num];
}
let contractDetailRenderSeq = 0;

function getResultsViewStateKey() {
    return currentJobId ? `cam:view-state:${currentJobId}` : "";
}

function persistResultsViewState() {
    const key = getResultsViewStateKey();
    if (!key) return;
    try {
        sessionStorage.setItem(key, JSON.stringify({
            activeTopTab,
            activeResultsTab,
            contractDetailOpen,
            currentTenantIndex,
            snapshotActiveIndex
        }));
    } catch (e) { /* silent */ }
}

function restoreResultsViewState() {
    const key = getResultsViewStateKey();
    if (!key) return;
    try {
        const raw = sessionStorage.getItem(key);
        if (!raw) return;
        const state = JSON.parse(raw);
        if (state && typeof state === "object") {
            if (typeof state.activeTopTab === "string") activeTopTab = state.activeTopTab;
            if (typeof state.activeResultsTab === "string") activeResultsTab = state.activeResultsTab;
            if (typeof state.currentTenantIndex === "number") currentTenantIndex = state.currentTenantIndex;
            if (typeof state.snapshotActiveIndex === "number" || state.snapshotActiveIndex === null) snapshotActiveIndex = state.snapshotActiveIndex;
            contractDetailOpen = !!state.contractDetailOpen;
        }
    } catch (e) { /* silent */ }
}

// ── Filter State (043) ──
let filterContracts = new Set();   // empty = All Contracts
let filterSeverities = new Set();  // empty = All Severities
let filterProvisions = new Set();  // empty = All Provisions
let filterConfidence = new Set();  // empty = All (Step 184)

// ── Chat Scope State (044) ──
let chatScopeTenantIdx = "";    // "" = All Contracts
let chatScopeProvisionId = "";  // "" = All Provisions
let chatStarterMode = "analysis";

// ── Help Chat State (086) ──
let helpChatHistory = [];
let helpChatInitialized = false;

// ── Processing Chat State ──
let processingChatHistory = [];
let processingChatInitialized = false;
let resultsTopBarLayoutBound = false;

// (Prescan state removed in step 112 — discovery moved into pipeline)

// ── DOM references ──
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── Step 2 activation helpers (Step 139) ──
function activateStep2() {
    const phase2 = $("#phase2-content");
    const contractsCol = $("#contracts-column");
    [phase2, contractsCol].forEach(el => {
        if (el) {
            el.classList.remove("step2-inactive");
            el.classList.remove("hidden");
        }
    });
}

function deactivateStep2() {
    const phase2 = $("#phase2-content");
    const contractsCol = $("#contracts-column");
    [phase2, contractsCol].forEach(el => {
        if (el) el.classList.add("step2-inactive");
    });
}

function shouldActivateUploadLowerSteps() {
    if (addMoreMode === "addmore" || templateSummary) return true;
    if (getSelectedMode() === "analyze") return getSelectedPerspective() !== null;
    return false;
}

function syncReviewAreasAvailability() {
    const provSidebar = $("#provisions-sidebar");
    if (!provSidebar) return;

    const mode = getSelectedMode();
    const hasTenants = tenantFiles.length > 0;
    const ready = addMoreMode === "addmore"
        || (mode === "analyze" && getSelectedPerspective() !== null && hasTenants)
        || (mode !== "analyze" && !!templateSummary && hasTenants);

    provSidebar.classList.remove("step2-inactive");
    provSidebar.classList.toggle("review-areas-inactive", !ready);
    provSidebar.classList.remove("hidden");
}

// ══════════════════════════════════════════════════════
// State Management
// ══════════════════════════════════════════════════════

function showState(name) {
    currentState = name;
    ["gate", "select", "upload", "processing", "results"].forEach(s => {
        const el = $(`#state-${s}`);
        if (el) el.classList.toggle("hidden", s !== name);
    });
    // Lock page scroll when results are showing — prevents sticky header jitter
    document.body.classList.toggle('results-active', name === 'results');

    // Show cancel button in nav only during active processing
    const wfCancelBtn = $("#workflow-cancel-btn");
    if (wfCancelBtn) wfCancelBtn.classList.toggle("hidden", name !== "processing");

    const tagline = $("#header-tagline");
    if (name === "gate") {
        tagline.textContent = HEADER_TAGLINE;
        $("#app-header").style.display = "none";
    } else {
        tagline.textContent = HEADER_TAGLINE;
        $("#app-header").style.display = "";
    }

    // Help chat is part of upload-layout grid — no toggling needed

    // Step 139: Manage step2 active/inactive state (step2 always visible, just inactive until template processed)
    if (name === "upload") {
        if (shouldActivateUploadLowerSteps()) {
            activateStep2();
        } else {
            deactivateStep2();
        }
        syncReviewAreasAvailability();
    }

    // Mobile: populate results URL for copy/email
    if (name === "results") {
        const urlField = $("#mobile-results-url");
        if (urlField) urlField.value = window.location.href;
    }

    syncEmailState();
    updateWorkflowNav();
    // Step 263: keep audit-trail tab visibility in sync with the current
    // job's mode (Mode C hides it because the multi-evaluator pipeline doesn't run).
    applyModeAwareTabVisibility();
}

/**
 * Syncs the confirmed email across all screens.
 * If jobEmail is set, replaces email inputs with a confirmation message.
 */
function syncEmailState() {
    if (!jobEmail) return;

    const escapedEmail = esc(jobEmail);
    const confirmHtml = `<div class="email-confirmed-notice">&#128231; Notifications will be sent to <strong>${escapedEmail}</strong></div>`;

    // Upload page: replace email accordion body
    const accBody = document.getElementById('email-accordion-body');
    if (accBody && !accBody.dataset.emailSet) {
        accBody.innerHTML = confirmHtml;
        accBody.dataset.emailSet = "1";
        // Ensure it's visible
        accBody.classList.remove('hidden');
    }

    // Processing page: replace email capture card
    const procCard = document.getElementById('processing-email-capture');
    if (procCard) {
        procCard.innerHTML = confirmHtml;
        procCard.classList.remove('hidden');
        procCard.dataset.emailSet = "1";
    }

    // Processing page: update the email notice
    const emailNotice = $("#email-notice");
    if (emailNotice) {
        emailNotice.innerHTML = `&#128231; We'll email you at <strong>${escapedEmail}</strong> when results are ready.`;
    }

    // Mobile results page: replace email row
    const mobileEmailRow = document.querySelector('.mobile-results-email-row');
    if (mobileEmailRow && !mobileEmailRow.dataset.emailSet) {
        mobileEmailRow.innerHTML = confirmHtml;
        mobileEmailRow.dataset.emailSet = "1";
    }
}

/**
 * Sets the global email and syncs all screens.
 */
function setJobEmail(email) {
    if (!email) return;
    jobEmail = email.trim();
    syncEmailState();
}

window.CAM = window.CAM || {};
window.CAM.sendMobileResultsLink = async function() {
    const emailInput = $("#mobile-results-email");
    const statusEl = $("#mobile-results-email-status");
    const btn = $("#mobile-results-email-btn");
    if (!emailInput || !emailInput.value) return;
    btn.disabled = true;
    btn.textContent = "Sending…";
    try {
        const resp = await fetch("/api/send-results-link", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailInput.value, url: window.location.href })
        });
        if (resp.ok) {
            setJobEmail(emailInput.value);
        } else {
            statusEl.textContent = "Failed to send. Please copy the link instead.";
            statusEl.style.color = "#dc2626";
        }
    } catch (e) {
        statusEl.textContent = "Failed to send. Please copy the link instead.";
        statusEl.style.color = "#dc2626";
    }
    statusEl.classList.remove("hidden");
    btn.disabled = false;
    btn.textContent = "Send";
};

function updateWorkflowNav() {
    const nav = $("#workflow-nav");
    if (!nav) return;

    const shouldShow = ["upload", "processing", "results"].includes(currentState);
    nav.classList.toggle("hidden", !shouldShow);
    if (!shouldShow) return;

    const processingAvailable = !!currentJobId && (
        currentState === "processing" ||
        (currentJobData && ["processing", "queued", "failed", "cancelled"].includes(currentJobData.status))
    );
    const resultsAvailable = currentState === "results" || !!(currentResults && currentResults.tenants);

    ["upload", "processing", "results"].forEach((stateName) => {
        const btn = $(`#workflow-tab-${stateName}`);
        if (!btn) return;
        btn.classList.toggle("active", currentState === stateName);
        if (stateName === "upload") {
            btn.disabled = false;
        } else if (stateName === "processing") {
            btn.disabled = !processingAvailable;
        } else {
            btn.disabled = !resultsAvailable;
        }
    });
}

async function navigateWorkflowState(targetState) {
    if (targetState === "upload") {
        // Step 274: clicking the Upload tab while sitting on a results
        // (or completed/cancelled processing) URL was leaving the URL
        // pinned at /results/{id} and `currentJobId` set, so the upload
        // flow could not actually start a fresh run. If a job is loaded
        // and the user navigates back to upload, treat it as a real
        // "start over": clear job state and reset the URL to "/".
        const onResults = currentState === "results";
        const completedJob = currentJobData && [
            "completed", "cancelled", "failed",
        ].includes(currentJobData.status);
        if (currentJobId && (onResults || completedJob)) {
            resetApp();
            history.replaceState(null, "", "/");
            // Also clear residual job/results refs that resetApp doesn't
            // touch (those live outside the upload-form scope).
            currentJobData = null;
            currentResults = null;
            currentTenantIndex = 0;
            stopPolling();
            if (expiryTimer) { clearInterval(expiryTimer); expiryTimer = null; }
            const expiryEl = $("#expiry-notice");
            if (expiryEl) expiryEl.classList.add("hidden");
            const navContent = $("#nav-sidebar-content");
            if (navContent) navContent.innerHTML = "";
            enterApp();
            return;
        }
        showState("upload");
        return;
    }

    if (!currentJobId) return;

    if (targetState === "processing") {
        if (!(currentJobData && ["processing", "queued", "failed", "cancelled"].includes(currentJobData.status)) && currentState !== "processing") {
            return;
        }
        if (currentJobData) {
            showState("processing");
            if (currentJobData.status === "cancelled") {
                handleCancelledJob(currentJobData);
            } else {
                initProcessingView(currentJobData);
            }
        }
        return;
    }

    if (targetState === "results") {
        if (!(currentResults && currentResults.tenants)) {
            if (currentJobData && currentJobData.status === "completed") {
                await loadResults();
            } else {
                return;
            }
        }
        showState("results");
        renderResults();
        return;
    }
}

function measureScrollbarWidth() {
    // Create off-screen scrolling div to measure browser's scrollbar width
    var probe = document.createElement('div');
    probe.style.cssText = 'position:absolute;top:-9999px;left:-9999px;width:100px;height:100px;overflow:scroll;';
    document.body.appendChild(probe);
    var w = probe.offsetWidth - probe.clientWidth;
    document.body.removeChild(probe);
    document.documentElement.style.setProperty('--scrollbar-w', w + 'px');
}

function init() {
    // Measure browser scrollbar width so non-scrolling siblings can compensate
    measureScrollbarWidth();

    const path = window.location.pathname;
    const resultsMatch = path.match(/^\/results\/(.+)$/);

    if (resultsMatch) {
        const jobId = resultsMatch[1];
        loadJobDirect(jobId);
        return;
    }

    // Also support /?job=<jobId> query param (e.g. after refresh or shared link)
    const urlParams = new URLSearchParams(window.location.search);
    const jobParam = urlParams.get("job");
    if (jobParam) {
        loadJobDirect(jobParam);
        return;
    }

    if (sessionStorage.getItem("cam_access_code")) {
        enterApp();
    } else {
        showState("gate");
    }

    setupEventListeners();
}

async function enterApp() {
    await loadModelNames(); // ensure evalName() is ready before any rendering
    if (ANALYSIS_TYPES.length === 1) {
        selectedAnalysisType = ANALYSIS_TYPES[0];
        showState("upload");
        loadProvisions();
    } else {
        showState("select");
        renderAnalysisTypes();
    }
}

// ══════════════════════════════════════════════════════
// Event Listeners
// ══════════════════════════════════════════════════════

// Close all custom filter dropdowns when clicking outside
document.addEventListener("click", function(e) {
    if (e.target.closest(".clause-filter-dropdown, .snapshot-contract-filter-wrap")) return;
    document.querySelectorAll(".clause-filter-panel, .snapshot-contract-dropdown").forEach(function(el) {
        el.classList.add("hidden");
    });
});

function setupEventListeners() {
    $$("#workflow-nav [data-workflow-state]").forEach(btn => {
        btn.onclick = async () => {
            if (btn.disabled) return;
            await navigateWorkflowState(btn.dataset.workflowState);
        };
    });

    // Gate
    $("#gate-submit").addEventListener("click", handleGateSubmit);
    $("#gate-code").addEventListener("keydown", e => {
        if (e.key === "Enter") handleGateSubmit();
    });

    // Upload zones
    setupDropZone("template-drop", "template-input", handleTemplateFiles);
    setupDropZone("tenant-drop", "tenant-input", handleTenantFiles);

    // Mode selector (Step 253)
    document.querySelectorAll('input[name="analysis-mode"]').forEach(radio => {
        radio.addEventListener("change", () => {
            modeExplicitlySelected = true;
            handleModeChange();
        });
    });

    // Perspective selector (Step 261) — must select; flashes red if user tries
    // to submit without choosing. Wiring is identical to mode radios except it
    // also clears the required-indicator class on first selection.
    document.querySelectorAll('input[name="analysis-perspective"]').forEach(radio => {
        radio.addEventListener("change", handlePerspectiveChange);
    });

    // Step 284: apply the initial mode-aware state. Step 346: also mark
    // mode as explicitly selected so the default (analyze) is pre-chosen
    // and the submit gate doesn't prompt the user to pick a mode.
    handleModeChange();
    modeExplicitlySelected = true;

    // Help chat
    initHelpChat();

    // Clear buttons
    const templateClearBtn = $("#template-clear-btn");
    if (templateClearBtn) templateClearBtn.addEventListener("click", clearTemplateFile);
    const tenantClearBtn = $("#tenant-clear-btn");
    if (tenantClearBtn) tenantClearBtn.addEventListener("click", clearAllTenantFiles);

    // Demo tenant checkboxes — update Load button state
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('demo-tenant-check')) {
            updateDemoLoadBtn();
        }
    });

    // Provisions
    $("#add-custom-provision").addEventListener("click", addCustomProvision);
    $("#custom-provision-input").addEventListener("keydown", e => {
        if (e.key === "Enter") addCustomProvision();
    });

    // Email confirmation
    const emailConfirm = $("#email-confirm-input");
    if (emailConfirm) {
        emailConfirm.addEventListener("paste", e => e.preventDefault());
        emailConfirm.addEventListener("input", updateSubmitState);
    }
    const emailInput = $("#email-input");
    if (emailInput) {
        emailInput.addEventListener("input", updateSubmitState);
    }

    // Submit
    $("#analyze-btn").addEventListener("click", handleSubmit);

    // Cancel analysis
    $("#cancel-btn").addEventListener("click", handleCancel);

    // Copy link
    $("#copy-link-btn").addEventListener("click", () => {
        const input = $("#results-link-input");
        input.select();
        navigator.clipboard.writeText(input.value).catch(() => {
            document.execCommand("copy");
        });
        $("#copy-link-btn").textContent = "Copied!";
        setTimeout(() => { $("#copy-link-btn").textContent = "Copy Link"; }, 2000);
    });

    // Tenant selector (findings tab)
    $("#tenant-select").addEventListener("change", e => {
        currentTenantIndex = parseInt(e.target.value, 10);
        renderTenantResults();
        syncChatScopeToCurrentTenant(true);
        // Sync docview tenant select
        const dts = $("#docview-tenant-select");
        if (dts) dts.value = currentTenantIndex;
        // Sync nav sidebar active state
        updateNavActive(currentTenantIndex);
        // Re-render audit trail if active
        if (activeResultsTab === "audittrail") renderAuditTrail();
    });

    // Tenant selector (document comparison tab)
    const docviewTenantSelect = $("#docview-tenant-select");
    if (docviewTenantSelect) {
        docviewTenantSelect.addEventListener("change", e => {
            currentTenantIndex = parseInt(e.target.value, 10);
            renderDocumentView();
            syncChatScopeToCurrentTenant(true);
            // Sync findings tenant select
            $("#tenant-select").value = currentTenantIndex;
            // Sync nav sidebar active state
            updateNavActive(currentTenantIndex);
        });
    }

    // Contract sub-tabs wired in renderResults() via onclick (Step 170 fix)

    // Document view search
    initDocviewSearch();

    // Docview mode toggle (Full Document / Side-by-Side)
    document.querySelectorAll(".docview-mode-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const mode = btn.dataset.mode;
            if (mode === docviewMode) return;
            docviewMode = mode;
            document.querySelectorAll(".docview-mode-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            clearDocSearch();
            renderDocumentView();
        });
    });

    document.querySelectorAll(".docview-sort-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const sort = btn.dataset.sort;
            if (sort === docviewSort) return;
            docviewSort = sort;
            document.querySelectorAll(".docview-sort-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            clearDocSearch();
            renderDocumentView();
        });
    });


    // New Analysis button
    const newAnalysisBtn = $("#new-analysis-btn");
    if (newAnalysisBtn) {
        newAnalysisBtn.addEventListener("click", () => {
            // Clear job state
            currentJobId = null;
            currentJobData = null;
            currentResults = null;
            currentTenantIndex = 0;
            addMoreMode = null;
            activeTopTab = "overview"; snapshotActiveIndex = null; snapshotVisited = false; snapshotSort = 'risk'; snapshotSeverityFilter = new Set(); snapshotConfidenceFilter = new Set(); snapshotStatusFilter = 'all'; snapshotSearch = ''; snapshotContractFilter = new Set();  // Step 120/122/124/130: reset
            // prescan removed (112)
            cancelRequested = false;
            chatHistory = [];
            // Reset chat panel
            const chatPanel = $("#chat-panel");
            if (chatPanel) chatPanel.classList.remove("mobile-open");
            const chatMessages = $("#chat-messages");
            if (chatMessages) chatMessages.innerHTML = "";
            // Reset multi-options panel and synthesis toggle
            const multiOpts = $("#chat-multi-options");
            if (multiOpts) multiOpts.classList.add("hidden");
            const synthDefault = document.querySelector('input[name="synth-mode"][value="synthesized"]');
            if (synthDefault) synthDefault.checked = true;
            // Hide expiry notice in header
            const expiryEl = $("#expiry-notice");
            if (expiryEl) expiryEl.classList.add("hidden");
            // Clear nav sidebar
            const navContent = $("#nav-sidebar-content");
            if (navContent) navContent.innerHTML = "";
            if (expiryTimer) { clearInterval(expiryTimer); expiryTimer = null; }
            stopPolling();
            // Clear URL
            history.replaceState(null, "", "/");
            // Return to upload screen
            enterApp();
        });
    }

    // Add More button (unified: leases + provisions)
    const addMoreBtn = $("#add-more-btn");
    if (addMoreBtn) {
        addMoreBtn.addEventListener("click", () => {
            addMoreMode = "addmore";
            tenantFiles = [];
            showState("upload");
            loadProvisions();
            // Lock template display
            const templateDrop = $("#template-drop");
            const origTemplate = currentJobData && currentJobData.input_config
                ? currentJobData.input_config.template_file : "Reference Lease";
            templateDrop.classList.add("has-files", "locked");
            const templateList = $("#template-file-list");
            templateList.classList.remove("hidden");
            templateList.innerHTML = `<li><span class="file-name">\u2705 ${esc(origTemplate)} (locked)</span></li>`;
            renderTenantFileList();
            updateSubmitState();
            // lockAnalyzedProvisions() is called at end of renderProvisions() when mode === "addmore"
        });
    }

    // Conforming toggle
    const conformingToggle = $("#conforming-toggle");
    if (conformingToggle) {
        conformingToggle.addEventListener("click", () => {
            const list = $("#conforming-list");
            const toggle = $("#conforming-toggle");
            const isOpen = !list.classList.contains("hidden");
            list.classList.toggle("hidden");
            toggle.innerHTML = (isOpen ? "&#9654;" : "&#9660;") + " Conforming Provisions (no action needed)";
        });
    }

    // Tech details toggle
    const techToggle = $("#tech-details-toggle");
    if (techToggle) {
        techToggle.addEventListener("click", () => {
            const content = $("#tech-details-content");
            const isOpen = content.classList.contains("open");
            content.classList.toggle("open");
            techToggle.innerHTML = (isOpen ? "&#9654;" : "&#9660;") + " Technical Details";
        });
    }

    // Downloads
    const downloadBatchBtn = $("#download-batch-summary");
    if (downloadBatchBtn) {
        downloadBatchBtn.addEventListener("click", () => {
            if (currentJobId) downloadFile(`/api/jobs/${currentJobId}/summary`);
        });
    }
    const exportJsonBtn = $("#export-all-json");
    if (exportJsonBtn) exportJsonBtn.addEventListener("click", exportAllJSON);

    // Privacy modal
    $("#privacy-toggle").addEventListener("click", () => {
        $("#privacy-modal").classList.add("open");
    });
    $("#privacy-close").addEventListener("click", () => {
        $("#privacy-modal").classList.remove("open");
    });
    $("#privacy-modal").addEventListener("click", e => {
        if (e.target === $("#privacy-modal")) {
            $("#privacy-modal").classList.remove("open");
        }
    });

    // About CAM modal
    const aboutToggle = $("#about-cam-toggle");
    if (aboutToggle) {
        aboutToggle.addEventListener("click", () => {
            $("#about-cam-modal").classList.add("open");
        });
    }
    const aboutClose = $("#about-cam-close");
    if (aboutClose) {
        aboutClose.addEventListener("click", () => {
            $("#about-cam-modal").classList.remove("open");
        });
    }
    const aboutModal = $("#about-cam-modal");
    if (aboutModal) {
        aboutModal.addEventListener("click", e => {
            if (e.target === aboutModal) {
                aboutModal.classList.remove("open");
            }
        });
    }

    // Chat panel (mobile FAB + close button)
    const chatFabMobile = $("#chat-fab-mobile");
    if (chatFabMobile) chatFabMobile.addEventListener("click", () => {
        const panel = $("#chat-panel");
        if (panel) { panel.classList.add("mobile-open"); chatFabMobile.classList.add("hidden"); }
        initChat();
        const chatInput = $("#chat-input");
        if (chatInput) chatInput.focus();
    });
    const chatCloseBtn = $("#chat-close-btn");
    if (chatCloseBtn) chatCloseBtn.addEventListener("click", () => {
        const panel = $("#chat-panel");
        if (panel) panel.classList.remove("mobile-open");
        const mobileFab = $("#chat-fab-mobile");
        if (mobileFab) mobileFab.classList.remove("hidden");
    });

    // Chat export button
    const chatExportBtn = $("#chat-export-btn");
    if (chatExportBtn) chatExportBtn.addEventListener("click", exportChat);

    // Chat panel resize handle
    initPanelResize();

    // Delete Analysis button
    const deleteBtn = $("#delete-job-btn");
    if (deleteBtn) deleteBtn.addEventListener("click", deleteCurrentJob);
}

// ══════════════════════════════════════════════════════
// STATE 1: Access Gate
// ══════════════════════════════════════════════════════

async function handleGateSubmit() {
    const code = $("#gate-code").value.trim();
    if (!code) return;

    const errorEl = $("#gate-error");
    errorEl.classList.add("hidden");

    try {
        const resp = await fetch("/api/auth/verify", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({access_code: code})
        });

        if (resp.ok) {
            sessionStorage.setItem("cam_access_code", code);
            enterApp();
        } else {
            errorEl.textContent = "Invalid access code. Please try again.";
            errorEl.classList.remove("hidden");
            $("#gate-code").value = "";
            $("#gate-code").focus();
        }
    } catch (err) {
        errorEl.textContent = "Connection error. Please check your network.";
        errorEl.classList.remove("hidden");
    }
}

// ══════════════════════════════════════════════════════
// STATE 2: Analysis Type Selection
// ══════════════════════════════════════════════════════

function renderAnalysisTypes() {
    const container = $("#analysis-types-container");
    container.innerHTML = "";
    ANALYSIS_TYPES.forEach(type => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.cursor = "pointer";
        card.style.marginBottom = "1rem";
        card.innerHTML = `
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <div>
                    <div style="font-weight:600; font-size:1rem;">${type.name}</div>
                    <div style="font-size:0.875rem; color:var(--text-muted); margin-top:0.25rem;">${type.description}</div>
                </div>
                <span class="btn btn-primary btn-sm">Go &rarr;</span>
            </div>
        `;
        card.addEventListener("click", () => {
            selectedAnalysisType = type;
            showState("upload");
            loadProvisions();
        });
        container.appendChild(card);
    });
}

// ══════════════════════════════════════════════════════
// STATE 3: Upload & Configure
// ══════════════════════════════════════════════════════

function setupDropZone(dropId, inputId, handler) {
    const drop = $(`#${dropId}`);
    const input = $(`#${inputId}`);

    drop.addEventListener("click", () => input.click());
    drop.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") input.click();
    });

    input.addEventListener("change", () => {
        handler(Array.from(input.files));
        input.value = "";
    });

    drop.addEventListener("dragover", e => {
        e.preventDefault();
        drop.classList.add("dragover");
    });
    drop.addEventListener("dragleave", () => {
        drop.classList.remove("dragover");
    });
    drop.addEventListener("drop", e => {
        e.preventDefault();
        drop.classList.remove("dragover");
        handler(Array.from(e.dataTransfer.files));
    });
}

function handleTemplateFiles(files) {
    if (files.length === 0) return;
    const file = files[0];
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "txt"].includes(ext)) {
        alert("Template must be PDF, DOCX, or TXT");
        return;
    }
    templateFile = file;
    renderTemplateFileList();
    updateSubmitState();

    // Step 138: Run gate check + summary extraction
    processTemplateSummary(file);
}

async function processTemplateSummary(file) {
    const loadingEl = $("#template-loading");
    const gateErrorEl = $("#template-gate-error");
    const summaryContainer = $("#template-summary-container");

    // Reset — Step 139: use deactivateStep2 instead of hidden
    if (gateErrorEl) gateErrorEl.classList.add("hidden");
    if (summaryContainer) summaryContainer.innerHTML = "";
    deactivateStep2();
    templateSummary = null;

    // Show loading
    if (loadingEl) loadingEl.classList.remove("hidden");

    try {
        const formData = new FormData();
        formData.append("template_file", file);
        formData.append("access_code", sessionStorage.getItem("cam_access_code") || "");

        const resp = await fetch("/api/template/summary", {
            method: "POST",
            body: formData,
        });

        if (!resp.ok) {
            throw new Error("Server error (" + resp.status + ")");
        }

        const data = await resp.json();

        if (!data.gate_passed) {
            // Gate failed — show error, stay in phase 1
            if (gateErrorEl) {
                gateErrorEl.textContent = data.gate_message || "This document does not appear to be a commercial lease agreement.";
                gateErrorEl.classList.remove("hidden");
            }
            // Clear the template file since it failed
            templateFile = null;
            renderTemplateFileList();
            updateSubmitState();
            return;
        }

        // Gate passed — store summary and reveal phase 2
        templateSummary = data;
        renderTemplateSummaryCard(data);
        revealPhase2();

    } catch (err) {
        console.error("Template summary error:", err);
        if (gateErrorEl) {
            gateErrorEl.textContent = "Failed to read template: " + err.message;
            gateErrorEl.classList.remove("hidden");
        }
    } finally {
        if (loadingEl) loadingEl.classList.add("hidden");
    }
}

function renderTemplateSummaryCard(data) {
    const container = $("#template-summary-container");
    if (!container) return;

    const val = (v) => v ? esc(v) : "\u2014";
    // Three-state render for deal terms: real value / placeholder / not found
    const dealVal = (v) => {
        if (!v) return "<span class=\"tscard-placeholder\">\u2014</span>";
        if (v === "[blank]") return "<span class=\"tscard-placeholder\">Template placeholder</span>";
        return `<strong>${esc(v)}</strong>`;
    };

    container.innerHTML = `
        <div id="template-summary-card">
            <div class="tscard-header">Reference Lease \u2014 Confirmed</div>
            <div class="tscard-fields">
                <div class="tscard-field">
                    <span class="tscard-label">Landlord</span>
                    <span class="tscard-value" id="tscard-landlord">${val(data.landlord)}</span>
                </div>
                <div class="tscard-field">
                    <span class="tscard-label">Property</span>
                    <span class="tscard-value" id="tscard-property">${val(data.property)}</span>
                </div>
                <div class="tscard-field">
                    <span class="tscard-label">Base Rent</span>
                    <span class="tscard-value" id="tscard-rent">${dealVal(data.base_rent)}</span>
                </div>
                <div class="tscard-field">
                    <span class="tscard-label">Lease Term</span>
                    <span class="tscard-value" id="tscard-term">${dealVal(data.lease_term)}</span>
                </div>
            </div>
            <div class="tscard-identity-row">
                <span class="tscard-identity-label">Also verify identity fields:</span>
                <label class="tscard-check">
                    <input type="checkbox" id="id-check-landlord"> Landlord entity
                </label>
                <label class="tscard-check">
                    <input type="checkbox" id="id-check-property"> Property name/address
                </label>
                <label class="tscard-check">
                    <input type="checkbox" id="id-check-tenant"> Tenant entity
                </label>
            </div>
        </div>
    `;

    // Wire up identity checkboxes
    const landlordCb = document.getElementById("id-check-landlord");
    const propertyCb = document.getElementById("id-check-property");
    const tenantCb = document.getElementById("id-check-tenant");

    if (landlordCb) landlordCb.addEventListener("change", e => {
        identityChecks.landlord = e.target.checked;
        updateSubmitState();
    });
    if (propertyCb) propertyCb.addEventListener("change", e => {
        identityChecks.property = e.target.checked;
        updateSubmitState();
    });
    if (tenantCb) tenantCb.addEventListener("change", e => {
        identityChecks.tenant = e.target.checked;
        updateSubmitState();
    });
}

function revealPhase2() {
    activateStep2();
    syncReviewAreasAvailability();
}

function handleTenantFiles(files) {
    const validExts = ["pdf", "docx", "txt", "zip"];
    for (const file of files) {
        const ext = file.name.split(".").pop().toLowerCase();
        if (!validExts.includes(ext)) {
            alert(`Unsupported file: ${file.name}. Use PDF, DOCX, TXT, or ZIP.`);
            continue;
        }
        if (!tenantFiles.some(f => f.name === file.name && f.size === file.size)) {
            tenantFiles.push(file);
        }
    }
    renderTenantFileList();
    updateSubmitState();
}

function clearTemplateFile() {
    templateFile = null;
    templateSummary = null;
    identityChecks = { landlord: false, property: false, tenant: false };
    renderTemplateFileList();

    // Step 139: Reset to phase 1 (deactivate step 2)
    const summaryContainer = $("#template-summary-container");
    if (summaryContainer) summaryContainer.innerHTML = "";
    deactivateStep2();
    const gateErrorEl = $("#template-gate-error");
    if (gateErrorEl) gateErrorEl.classList.add("hidden");
    updateUploadModeLabels();
    const subtitle = $("#upload-subtitle");
    if (subtitle) subtitle.textContent = "Upload your reference lease (standard template or prior executed lease).";

    updateSubmitState();
}

function clearAllTenantFiles() {
    tenantFiles = [];
    tenantDragIndex = null;
    renderTenantFileList();
    updateSubmitState();
}

function moveTenantFile(fromIndex, toIndex) {
    if (fromIndex === toIndex) return;
    if (fromIndex < 0 || toIndex < 0) return;
    if (fromIndex >= tenantFiles.length || toIndex >= tenantFiles.length) return;
    const [moved] = tenantFiles.splice(fromIndex, 1);
    tenantFiles.splice(toIndex, 0, moved);
}

function renderTemplateFileList() {
    const drop = $("#template-drop");
    const list = $("#template-file-list");
    const clearBtn = $("#template-clear-btn");

    if (templateFile) {
        drop.classList.add("has-files");
        list.classList.remove("hidden");
        if (clearBtn) clearBtn.classList.remove("hidden");
        list.innerHTML = `<li>
            <span class="file-name">\u2705 ${esc(templateFile.name)}</span>
            <button class="remove-file" title="Remove">&times;</button>
        </li>`;
        list.querySelector(".remove-file").addEventListener("click", e => {
            e.stopPropagation();
            clearTemplateFile();
        });
    } else {
        drop.classList.remove("has-files");
        list.classList.add("hidden");
        if (clearBtn) clearBtn.classList.add("hidden");
        list.innerHTML = "";
    }

    // Show/hide demo template section based on whether a template is loaded
    const demoTemplateSection = $('#demo-template-section');
    if (demoTemplateSection) {
        demoTemplateSection.classList.toggle('hidden', !!templateFile);
    }
}

function renderTenantFileList() {
    const drop = $("#tenant-drop");
    const list = $("#tenant-file-list");
    const clearBtn = $("#tenant-clear-btn");

    if (tenantFiles.length > 0) {
        drop.classList.add("has-files");
        list.classList.remove("hidden");
        if (clearBtn) clearBtn.classList.remove("hidden");
        list.innerHTML = tenantFiles.map((f, i) => `<li class="tenant-file-item" draggable="true" data-index="${i}">
            <div class="tenant-file-main">
                <button class="tenant-file-drag" type="button" title="Drag to reorder" aria-label="Drag to reorder">&#9776;</button>
                <span class="tenant-file-order">${i + 1}.</span>
                <span class="file-name">\u2705 ${esc(f.name)}</span>
            </div>
            <div class="tenant-file-actions">
                <button class="tenant-file-move" data-index="${i}" data-direction="up" title="Move up"${i === 0 ? " disabled" : ""}>&uarr;</button>
                <button class="tenant-file-move" data-index="${i}" data-direction="down" title="Move down"${i === tenantFiles.length - 1 ? " disabled" : ""}>&darr;</button>
                <button class="remove-file" data-index="${i}" title="Remove">&times;</button>
            </div>
        </li>`).join("");

        list.insertAdjacentHTML("afterbegin", `
            <li class="tenant-file-order-note">
                <span class="tenant-file-order-label">Processing order</span>
            </li>
        `);

        list.querySelectorAll(".remove-file").forEach(btn => {
            btn.addEventListener("click", e => {
                e.stopPropagation();
                const idx = parseInt(btn.dataset.index, 10);
                tenantFiles.splice(idx, 1);
                tenantDragIndex = null;
                renderTenantFileList();
                updateSubmitState();
            });
        });

        list.querySelectorAll(".tenant-file-move").forEach(btn => {
            btn.addEventListener("click", e => {
                e.stopPropagation();
                const idx = parseInt(btn.dataset.index, 10);
                const dir = btn.dataset.direction === "up" ? -1 : 1;
                moveTenantFile(idx, idx + dir);
                renderTenantFileList();
                updateSubmitState();
            });
        });

        list.querySelectorAll(".tenant-file-item").forEach(item => {
            item.addEventListener("dragstart", () => {
                tenantDragIndex = parseInt(item.dataset.index, 10);
                item.classList.add("dragging");
            });
            item.addEventListener("dragend", () => {
                tenantDragIndex = null;
                item.classList.remove("dragging");
                list.querySelectorAll(".tenant-file-item").forEach(li => li.classList.remove("drag-over"));
            });
            item.addEventListener("dragover", e => {
                e.preventDefault();
                item.classList.add("drag-over");
            });
            item.addEventListener("dragleave", () => {
                item.classList.remove("drag-over");
            });
            item.addEventListener("drop", e => {
                e.preventDefault();
                const targetIndex = parseInt(item.dataset.index, 10);
                if (tenantDragIndex == null || Number.isNaN(targetIndex)) return;
                moveTenantFile(tenantDragIndex, targetIndex);
                tenantDragIndex = null;
                renderTenantFileList();
                updateSubmitState();
            });
        });
    } else {
        drop.classList.remove("has-files");
        list.classList.add("hidden");
        if (clearBtn) clearBtn.classList.add("hidden");
        list.innerHTML = "";
    }

    // Show/hide demo tenant section based on whether any files are loaded
    const demoSection = $('#demo-tenant-section');
    if (demoSection) {
        demoSection.classList.toggle('hidden', tenantFiles.length > 0);
    }
}

// Step 194: Per-provision weighted time estimate
// Calibrated from 108 runs:
//   ~90s fixed base (Gemini extraction — one call, independent of provision count)
//   Variable cost per provision = flag_rate × 29s (empirical: ~29s per flagged provision)
//   +10s per identity check (LP-00 identity field overhead)
//   CUSTOM/ADDED provisions always flag at ~100% — use 29s each
//   LP-00 included in fixed base
//
// Flag rates from 108-run empirical analysis:
const LEGACY_PROVISION_FLAG_RATES = {
    "LP-01": 0.26, "LP-02": 0.11, "LP-03": 0.33, "LP-04": 0.09,
    "LP-05": 0.41, "LP-06": 0.27, "LP-07": 0.31, "LP-08": 0.30,
    "LP-09": 0.62, "LP-10": 0.38, "LP-11": 0.60, "LP-12": 0.46,
    "LP-13": 0.60, "LP-14": 0.26, "LP-15": 0.14, "LP-16": 0.32,
    "LP-17": 0.05, "LP-18": 0.22,
};
const LEGACY_VARIABLE_COST_PER_FLAGGED = 29; // seconds
const LEGACY_EXTRACTION_BASE_SECS = 90;      // seconds
const LEGACY_PROCESSING_STAGE_WEIGHTS = {
    1: 0.46, // extraction + alignment
    2: 0.08, // rules / detections
    3: 0.22, // multi-evaluator review
    4: 0.08, // challenge / agreement analysis
    5: 0.10, // severity assessment
    6: 0.06, // finalization / outputs
};









function renderProcessingOverview(job, tenants) {
    const panel = $("#processing-overview-status");
    if (!panel) return;

    if (!job || !tenants || tenants.length === 0) {
        panel.classList.add("hidden");
        panel.innerHTML = "";
        return;
    }

    const totalCount = tenants.length;
    let completedCount = 0;
    let overallFraction = 0;
    const processingTenants = [];
    const completedTenants = [];

    tenants.forEach((tenant) => {
        const effectiveStatus = (tenant.status === "queued" && job.status === "processing") ? "processing" : tenant.status;
        if (effectiveStatus === "completed") {
            completedCount++;
            completedTenants.push(tenant);
        }
        if (effectiveStatus === "processing") processingTenants.push(tenant);
        overallFraction += getTenantProgressFraction(tenant, job.status || "");
    });

    const overallPct = totalCount > 0 ? Math.round((overallFraction / totalCount) * 100) : 0;
    const leadTenant = processingTenants
        .slice()
        .sort((a, b) => {
            const stageDelta = (Number(b.current_stage) || 0) - (Number(a.current_stage) || 0);
            if (stageDelta !== 0) return stageDelta;
            return (Number(b.total_stages) || 0) - (Number(a.total_stages) || 0);
        })[0];
    const currentFocusPct = leadTenant
        ? Math.round(getTenantProgressFraction(leadTenant, job.status || "") * 100)
        : overallPct;

    const readyText = completedCount === 1
        ? "1 contract ready now"
        : `${completedCount} contracts ready now`;
    const remainingCount = Math.max(0, totalCount - completedCount);
    const remainingText = remainingCount === 1
        ? "1 contract still processing"
        : `${remainingCount} contracts still processing`;

    // Step 254: Mode C runs a 3-stage pipeline (parse, extract, coverage);
    // Mode A runs 6. Adjust the "X of Y stages" rollup so it reads correctly.
    const _isModeCRollup = job && job.input_config && job.input_config.mode === "analyze";
    const _stagesPerTenant = _isModeCRollup ? 4 : 6;
    const currentStageNum = leadTenant
        ? (Number(leadTenant.current_stage) || 1)
        : (completedCount === totalCount ? _stagesPerTenant : 1);
    const totalStageCount = leadTenant
        ? (Number(leadTenant.total_stages) || _stagesPerTenant)
        : _stagesPerTenant;
    const primaryReadyTenant = completedTenants[0] || null;
    const overallStagesTotal = totalCount * _stagesPerTenant;
    const overallStagesDone = tenants.reduce((sum, tenant) => {
        const effectiveStatus = (tenant.status === "queued" && job.status === "processing") ? "processing" : tenant.status;
        if (effectiveStatus === "completed") return sum + _stagesPerTenant;
        if (effectiveStatus === "processing") return sum + Math.max(0, Number(tenant.current_stage) || 0);
        return sum;
    }, 0);
    const contractCountLabel = totalCount === 1 ? "Total contracts: 1" : `Total contracts: ${totalCount}`;
    const overallStageLabel = overallStagesTotal > 0
        ? `Overall stage progress: ${overallStagesDone} of ${overallStagesTotal} stages`
        : "Overall stage progress unavailable";
    const overallProgressLabel = `Overall progress: ${overallPct}%`;
    const completedContractLabel = totalCount === 1
        ? `${completedCount} of 1 contract complete`
        : `${completedCount} of ${totalCount} contracts complete`;
    const headline = completedCount === totalCount
        ? "All contracts are ready"
        : "All contracts";
    const detail = completedCount === totalCount
        ? "CAM finished all contract reviews and the results workspace is ready."
        : `${completedContractLabel} • ${remainingText}.`;

    panel.classList.remove("hidden");
    panel.innerHTML = `
        <div class="processing-overview-meta-row">
            <span class="processing-overview-meta-pill">${esc(contractCountLabel)}</span>
            <span class="processing-overview-meta-pill">${esc(overallStageLabel)}</span>
            <span class="processing-overview-meta-pill">${esc(overallProgressLabel)}</span>
        </div>
        <div class="processing-hero-summary">
            <div class="processing-hero-copy">
                <div class="processing-hero-label">All contracts</div>
                <div class="processing-hero-headline">${esc(headline)}</div>
                <div class="processing-hero-detail">${esc(detail)}</div>
            </div>
            <div class="processing-hero-meta">
                <div class="processing-hero-percent">${overallPct}%</div>
                <div class="processing-hero-status">Overall progress</div>
                <div class="processing-hero-substatus">${esc(completedContractLabel)}</div>
            </div>
        </div>
        <div class="processing-hero-bar">
            <div class="processing-hero-bar-track">
                <div class="processing-hero-bar-fill" style="width:${overallPct}%"></div>
            </div>
        </div>
        <div class="processing-hero-footer">
            <span class="processing-hero-pill">${esc(readyText)}</span>
            <span class="processing-hero-pill">${esc(remainingText)}</span>
        </div>
        ${completedTenants.length > 0 ? completedTenants.map(ct => `
        <div class="processing-hero-ready">
            <div>
                <div class="processing-hero-ready-title">${esc(ct.filename || "Completed contract")} is ready to review</div>
                <div class="processing-hero-ready-meta">Open it now while CAM continues processing the remaining leases.</div>
            </div>
            <button class="btn btn-primary" data-hero-ready-open="${tenants.indexOf(ct)}">Open Contract</button>
        </div>
        `).join("") : ""}
    `;
    panel.querySelectorAll("[data-hero-ready-open]").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const idx = Number(btn.dataset.heroReadyOpen);
            if (Number.isNaN(idx)) return;
            await openReadyContractFromProcessing(idx);
        });
    });
}

function getProcessingSelectedProvisionCount(job) {
    const inputCfg = (job && job.input_config) || {};
    const base = Array.isArray(inputCfg.provisions) ? inputCfg.provisions.length : 0;
    const custom = Array.isArray(inputCfg.custom_provisions) ? inputCfg.custom_provisions.length : 0;
    return base + custom;
}

function getProcessingTenantProvisionCount(job, tenant) {
    if (tenant && tenant.status === "completed" && tenant.results && Array.isArray(tenant.results.provisions)) {
        return tenant.results.provisions.length;
    }
    const selected = getProcessingSelectedProvisionCount(job);
    return selected > 0 ? selected : null;
}

function formatProvisionCountLabel(count, singular = "provision", plural = "provisions") {
    if (!Number.isFinite(count) || count <= 0) return "";
    return `${count} ${count === 1 ? singular : plural}`;
}

function buildProcessingChecklistSteps(job, tenant) {
    const currentStage = Number(tenant && tenant.current_stage) || 0;
    const tenantStatus = (tenant && tenant.status) || "queued";
    const provisionCount = getProcessingTenantProvisionCount(job, tenant);
    const challengeCount = tenant && tenant.results && Array.isArray(tenant.results.provisions)
        ? tenant.results.provisions.filter((p) => p && p.final_verdict === "DEVIATES").length
        : null;

    const isComplete = tenantStatus === "completed";
    const stageDone = (stageNum) => isComplete || currentStage > stageNum;
    const stageActive = (stageNum) => !isComplete && tenantStatus === "processing" && currentStage === stageNum;
    const stagePending = (stageNum) => !stageDone(stageNum) && !stageActive(stageNum);

    // Step 254: Mode C runs a 4-stage pipeline (parse → extract → coverage → synthesis).
    // The backend progress_callback fires (1,4), (2,4), (3,4), (4,4) — match that here
    // so the checklist doesn't show Mode-A-only stages as pending forever.
    const isModeC = job && job.input_config && job.input_config.mode === "analyze";
    if (isModeC) {
        const modeCSteps = [
            {
                stage: 1,
                title: "Parse document",
                meta: "Reading the uploaded lease and preparing it for schema-driven analysis.",
            },
            {
                stage: 2,
                title: "Extract provisions",
                meta: `Extracting ${provisionCount || 'all'} issue-area clauses from the document (Gemini 3.1 Pro).`,
            },
            {
                stage: 3,
                title: "Analyze coverage",
                meta: "Evaluating all 32 issue areas with three independent models. This is the longest stage — typically 8–15 minutes depending on lease length.",
            },
            {
                stage: 4,
                title: "Cross-provision review",
                meta: "Reading the full lease as a whole to find interactions between provisions. Takes 3–5 minutes.",
            },
        ];
        return modeCSteps.map((step) => ({
            ...step,
            state: stageDone(step.stage) ? "complete" : stageActive(step.stage) ? "active" : "pending",
            icon: stageDone(step.stage) ? "✓" : stageActive(step.stage) ? "●" : "○",
        }));
    }

    const steps = [
        {
            stage: 1,
            title: "Parse, extract, and map the lease",
            meta: provisionCount ? `Extracting and aligning ${formatProvisionCountLabel(provisionCount)} — large leases may discover additional clauses beyond the standard checklist.` : "Extracting provisions and aligning tenant lease to the reference. Large leases split into multiple extraction passes.",
        },
        {
            stage: 2,
            title: "Run rules and cascade checks",
            meta: "Applying lease-specific detection rules and definition-cascade review.",
        },
        {
            stage: 3,
            title: "Run evaluator review",
            meta: provisionCount ? `Reviewing ${formatProvisionCountLabel(provisionCount)} with CAM's independent evaluator layer.` : "Running the independent evaluator review step.",
        },
        {
            stage: 4,
            title: "Challenge flagged findings",
            meta: challengeCount != null ? `Re-checking ${formatProvisionCountLabel(challengeCount)} for substance vs. cosmetic change.` : "Testing whether flagged findings are substantive, cosmetic, or expert-only.",
        },
        {
            stage: 5,
            title: "Assign severity",
            meta: "Turning confirmed differences into critical, high, medium, or low review signals.",
        },
        {
            stage: 6,
            title: "Finalize results",
            meta: "Finalizing dispositions, CAM confidence scoring, summaries, and outputs.",
        },
    ];

    return steps.map((step) => ({
        ...step,
        state: stageDone(step.stage) ? "complete" : stageActive(step.stage) ? "active" : "pending",
        icon: stageDone(step.stage) ? "✓" : stageActive(step.stage) ? "●" : "○",
    }));
}

function renderProcessingChecklist(job) {
    const container = $("#processing-checklist-list");
    if (!container) return;

    const tenants = (job && job.input_config && job.input_config.tenants) || [];
    if (!job || tenants.length === 0) {
        container.innerHTML = `<div class="processing-checklist-empty"><span class="spinner"></span> Starting analysis checklist...</div>`;
        return;
    }

    const selectedCount = getProcessingSelectedProvisionCount(job);
    const completedCount = tenants.filter((tenant) => tenant && tenant.status === "completed").length;
    const referenceComplete = completedCount > 0 || tenants.some((tenant) => Number(tenant.current_stage) >= 1);
    const referenceProvisionLabel = formatProvisionCountLabel(selectedCount);
    const leadTenantIndex = tenants.findIndex((tenant) => {
        const effectiveStatus = (tenant && tenant.status === "queued" && job.status === "processing")
            ? "processing"
            : ((tenant && tenant.status) || "queued");
        return effectiveStatus === "processing";
    });
    const orderedTenants = (leadTenantIndex >= 0)
        ? [tenants[leadTenantIndex], ...tenants.filter((_, idx) => idx !== leadTenantIndex)]
        : tenants.slice();

    // Step 254: Mode C has no reference lease — skip the reference-prep group.
    const isModeC = job && job.input_config && job.input_config.mode === "analyze";

    let html = isModeC ? "" : `
        <div class="processing-checklist-group ${referenceComplete ? "complete" : "current"}">
            <div class="processing-checklist-group-header">
                <div>
                    <div class="processing-checklist-group-title">Reference Lease</div>
                    <div class="processing-checklist-group-meta">${referenceProvisionLabel ? `${referenceProvisionLabel} in standard checklist — additional provisions discovered automatically.` : "Preparing the reference lease for comparison."}</div>
                </div>
                <div class="processing-checklist-group-badge">${referenceComplete ? "Ready" : "Starting"}</div>
            </div>
            <div class="processing-checklist-steps">
                <div class="processing-checklist-step ${referenceComplete ? "is-complete" : "is-active"}">
                    <div class="processing-checklist-icon">${referenceComplete ? "✓" : "●"}</div>
                    <div>
                        <div class="processing-checklist-step-title">Parse the reference lease</div>
                        <div class="processing-checklist-step-meta">CAM reads the reference lease and uses it as the comparison baseline for every tenant contract in this job.</div>
                    </div>
                </div>
                <div class="processing-checklist-step ${referenceComplete ? "is-complete" : "is-pending"}">
                    <div class="processing-checklist-icon">${referenceComplete ? "✓" : "○"}</div>
                    <div>
                        <div class="processing-checklist-step-title">Extract provisions and discover additions</div>
                        <div class="processing-checklist-step-meta">${referenceProvisionLabel ? `Checking the standard ${referenceProvisionLabel} plus any additional clauses found in the tenant lease.` : "Extracting provisions and identifying non-standard clauses for comparison."}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    orderedTenants.forEach((tenant) => {
        const idx = tenants.indexOf(tenant);
        const status = (tenant && tenant.status) || "queued";
        const groupState = status === "completed" ? "complete" : status === "processing" ? "current" : "";
        const provisionCount = getProcessingTenantProvisionCount(job, tenant);
        const steps = buildProcessingChecklistSteps(job, tenant);
        const completedSteps = steps.filter((step) => step.state === "complete").length;
        const totalSteps = steps.length;
        const provisionLabel = formatProvisionCountLabel(provisionCount);
        const metaText = status === "completed"
            ? `${completedSteps}/${totalSteps} complete${provisionLabel ? ` • ${provisionLabel} reviewed` : ""}`
            : status === "processing"
                ? `${completedSteps}/${totalSteps} complete${provisionLabel ? ` • ${provisionLabel} in checklist — may grow during extraction` : ""}`
                : `Queued${provisionLabel ? ` • ${provisionLabel} in checklist` : ""}`;
        const defaultStages = isModeC ? 4 : 6;
        const badgeText = status === "completed" ? "Complete" : status === "processing" ? `Step ${Number(tenant.current_stage) || 1} of ${Number(tenant.total_stages) || defaultStages}` : "Queued";

        html += `
            <div class="processing-checklist-group ${groupState}">
                <div class="processing-checklist-group-header">
                    <div>
                        <div class="processing-checklist-group-title">Contract ${idx + 1}: ${esc(tenant.filename || `Lease ${idx + 1}`)}</div>
                        <div class="processing-checklist-group-meta">${esc(metaText)}</div>
                    </div>
                    <div class="processing-checklist-group-badge">${esc(badgeText)}</div>
                </div>
                <div class="processing-checklist-steps">
                    ${steps.map((step) => `
                        <div class="processing-checklist-step is-${step.state}">
                            <div class="processing-checklist-icon">${step.icon}</div>
                            <div>
                                <div class="processing-checklist-step-title">${esc(step.title)}</div>
                                <div class="processing-checklist-step-meta">${esc(step.meta)}</div>
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function updateEstimateDisplay() {
    // Time estimates removed — too variable to be reliable
    // Show only elapsed time so users know work is progressing
    const estimateEl = $("#estimate-remaining");
    if (!estimateEl) return;
    const elapsedSecs = jobStartTime ? Math.max(0, (Date.now() - jobStartTime) / 1000) : 0;
    if (elapsedSecs > 5) {
        estimateEl.textContent = `${formatDurationShort(elapsedSecs)} elapsed`;
    } else {
        estimateEl.textContent = "";
    }
}

// Step 196: Stable whole-job progress timer for processing page
function startEstimateCountdown(totalSecs, options = {}) {
    stopEstimateCountdown();
    const alreadyElapsedSecs = Math.max(0, options.alreadyElapsedSecs || 0);
    const initialProgressFraction = Math.max(0, Math.min(1, options.initialProgressFraction || 0));
    jobStartTime = Date.now() - (alreadyElapsedSecs * 1000);
    estimateTotalSecs = totalSecs;
    estimateProgressFraction = initialProgressFraction;

    updateEstimateDisplay();

    estimateCountdownTimer = setInterval(updateEstimateDisplay, 1000);
}

function stopEstimateCountdown() {
    if (estimateCountdownTimer) {
        clearInterval(estimateCountdownTimer);
        estimateCountdownTimer = null;
    }
}



// Mode selector helpers (Step 253)
function getSelectedMode() {
    const checked = document.querySelector('input[name="analysis-mode"]:checked');
    return (checked && checked.value) || "compare";
}

// Step 261: Perspective selector helpers. Returns null when no radio is
// selected (the user MUST pick one — there is no default). Submit logic
// uses the null return to gate submission and flash the card red.
function getSelectedPerspective() {
    const checked = document.querySelector('input[name="analysis-perspective"]:checked');
    return (checked && checked.value) || null;
}
const PERSPECTIVE_LABELS = {
    tenant:   "tenant",
    landlord: "landlord",
    neutral:  "neutral / commercially reasonable",
};
function getPerspectiveLabel(value) {
    return PERSPECTIVE_LABELS[value] || value || "";
}
// Step 284: cache the user's Mode C perspective selection so a Mode C →
// Mode A → Mode C toggle restores their choice. `null` means the user has
// not yet picked one in Mode C this session.
let _modeCPerspectiveCache = null;

function handlePerspectiveChange() {
    // Remove the red required-indicator the moment the user picks something.
    const card = document.querySelector(".perspective-selector-card");
    if (card) card.classList.remove("required-indicator");
    // Step 284: capture the user's selection so it survives a hop into Mode A
    // and back. Only update the cache when in Mode C — Mode A drives the
    // value programmatically and we don't want that overwriting the user's
    // intent.
    if (getSelectedMode() === "analyze") {
        const checked = document.querySelector('input[name="analysis-perspective"]:checked');
        if (checked) _modeCPerspectiveCache = checked.value;
    }
    if (shouldActivateUploadLowerSteps()) {
        activateStep2();
    } else {
        deactivateStep2();
    }
    syncReviewAreasAvailability();
    updateSubmitState();
}

function updateUploadModeLabels(mode = getSelectedMode()) {
    const uploadStepLabel = document.getElementById("upload-step-label");
    if (uploadStepLabel) {
        uploadStepLabel.textContent = "Step 2: Upload your reference lease";
    }

    const tenantStepLabel = document.getElementById("tenant-step-label");
    if (tenantStepLabel) {
        tenantStepLabel.textContent = "Step 3: Upload Tenant Leases";
    }

    const sidebarTitle = document.querySelector(".provisions-panel-title");
    if (sidebarTitle) {
        sidebarTitle.textContent = "Review Areas";
    }


}

function handleModeChange() {
    const mode = getSelectedMode();
    const grid = document.querySelector(".upload-cols-grid");
    if (grid) {
        grid.classList.toggle("mode-analyze", mode === "analyze");
    }

    // Perspective selector: show in both modes. Mode A's deviation pipeline
    // detects changes objectively; perspective governs how the coverage layer,
    // exposure statements, Synopsis, and annotated documents frame those changes.
    // Default to tenant if user hasn't explicitly chosen (preserves pre-Step-293d behavior).
    const persWrap = document.getElementById("perspective-selector-wrapper");
    const persCard = document.querySelector(".perspective-selector-card");
    if (persWrap) {
        persWrap.classList.remove("hidden");
        if (mode === "analyze") {
            // Mode C: restore the user's prior choice (if any).
            if (_modeCPerspectiveCache) {
                const restore = document.querySelector(
                    'input[name="analysis-perspective"][value="' + _modeCPerspectiveCache + '"]'
                );
                if (restore) restore.checked = true;
            } else {
                // No cached choice — leave radios as-is
                document.querySelectorAll('input[name="analysis-perspective"]').forEach(r => {
                    if (r.checked && r.dataset.modeAForced === "1") {
                        r.checked = false;
                        delete r.dataset.modeAForced;
                    }
                });
            }
        } else {
            // Mode A: if user hasn't chosen yet, default to tenant (the historical default).
            // But don't override an explicit user selection.
            const checked = document.querySelector('input[name="analysis-perspective"]:checked');
            if (!checked || checked.dataset.modeAForced === "1") {
                const tenantRadio = document.querySelector(
                    'input[name="analysis-perspective"][value="tenant"]'
                );
                if (tenantRadio) {
                    tenantRadio.checked = true;
                    tenantRadio.dataset.modeAForced = "1";
                }
            }
            if (persCard) persCard.classList.remove("required-indicator");
        }
    }

    // Step 285: keep visible upload steps gap-free in both modes and keep the
    // sidebar label mode-neutral.
    updateUploadModeLabels(mode);
    // Keep lower upload/sidebar gating in sync with mode changes.
    if (shouldActivateUploadLowerSteps()) {
        activateStep2();
    } else {
        deactivateStep2();
    }
    syncReviewAreasAvailability();
    updateSubmitState();
}

// Step 263: keep Mode-aware UI tweaks (currently: hide CAM Audit Trail tab in
// Mode C since the multi-evaluator framework doesn't run there) in sync with
// the active job. Toggles a `mode-c` class on <body>; CSS hides the audit tab
// when set. Safe to call any time — if currentJobData isn't loaded yet, just
// clears the class.
function applyModeAwareTabVisibility() {
    const isModeC = !!(currentJobData
        && currentJobData.input_config
        && currentJobData.input_config.mode === "analyze");
    document.body.classList.toggle("mode-c", isModeC);
}

function updateSubmitState() {
    const btn = $("#analyze-btn");
    const est = $("#estimate-text");
    syncReviewAreasAvailability();

    // addMore mode has different requirements
    if (addMoreMode === "addmore") {
        const checkedCount = document.querySelectorAll("#provision-list input[type=checkbox]:checked").length;
        const newProvisionCount = checkedCount - lockedProvisionIds.size;
        const hasNewTenants = tenantFiles.length > 0;
        const hasNewProvisions = newProvisionCount > 0;

        btn.disabled = !(hasNewTenants || hasNewProvisions);

        if (hasNewTenants && hasNewProvisions) {
            btn.textContent = `Add ${tenantFiles.length} Lease${tenantFiles.length !== 1 ? "s" : ""} + ${newProvisionCount} Provision${newProvisionCount !== 1 ? "s" : ""}`;
            est.textContent = `Adding ${tenantFiles.length} new lease${tenantFiles.length !== 1 ? "s" : ""} and ${newProvisionCount} new provision${newProvisionCount !== 1 ? "s" : ""} to existing analysis`;
        } else if (hasNewTenants) {
            btn.textContent = `Add ${tenantFiles.length} Lease${tenantFiles.length !== 1 ? "s" : ""}`;
            est.textContent = `Adding ${tenantFiles.length} new lease${tenantFiles.length !== 1 ? "s" : ""} to existing analysis`;
        } else if (hasNewProvisions) {
            btn.textContent = `Review ${newProvisionCount} New Provision${newProvisionCount !== 1 ? "s" : ""}`;
            est.textContent = `Adding ${newProvisionCount} new provision${newProvisionCount !== 1 ? "s" : ""} to existing analysis`;
        } else {
            btn.textContent = "Add More";
            est.textContent = "Upload new leases or select new provisions to analyze";
        }
        return;
    }

    // Step 253: Mode C (analyze) does not require a template file.
    const analysisMode = getSelectedMode();
    const hasTemplate = templateFile !== null;
    const hasTenants  = tenantFiles.length > 0;
    const filesReady  = analysisMode === "analyze"
        ? hasTenants
        : (hasTemplate && hasTenants);

    // Check email confirmation match
    const emailVal = ($("#email-input") || {}).value || "";
    const confirmVal = ($("#email-confirm-input") || {}).value || "";
    const mismatchEl = $("#email-mismatch-error");
    let emailOk = true;

    if (emailVal && confirmVal && emailVal !== confirmVal) {
        emailOk = false;
        if (mismatchEl) mismatchEl.classList.remove("hidden");
    } else {
        if (mismatchEl) mismatchEl.classList.add("hidden");
    }

    // Step 261: perspective is required for Mode C only.
    // Mode A always has perspective forced to "tenant" — don't gate on it.
    const perspectiveSelected = analysisMode === "analyze"
        ? getSelectedPerspective() !== null
        : true;
    const ready = filesReady && emailOk && perspectiveSelected;
    btn.disabled = !ready;

    btn.textContent = "Review Leases";

    if (analysisMode === "analyze" && !perspectiveSelected) {
        est.textContent = "Choose a perspective above to continue";
    } else if (filesReady) {
        est.textContent = "";
    } else if (analysisMode === "analyze" && tenantFiles.length === 0) {
        est.textContent = "Upload at least one lease to analyze";
    } else if (!templateFile && tenantFiles.length === 0) {
        est.textContent = "Upload a reference lease and at least one tenant lease to compare";
    } else if (!templateFile && analysisMode !== "analyze") {
        est.textContent = "Upload a reference lease to continue";
    } else {
        est.textContent = "Upload at least one tenant lease to continue";
    }

    // Show/hide add-more back link
    const addmoreBackLink = $("#addmore-back-link");
    if (addmoreBackLink) {
        const inAddMore = addMoreMode === "addmore";
        addmoreBackLink.classList.toggle("hidden", !inAddMore);
    }
}

function lockAnalyzedProvisions() {
    // Lock provisions that were already analyzed in the existing job
    lockedProvisionIds = new Set();
    if (!currentResults || !currentResults.tenants || !currentResults.tenants[0]) return;
    const firstTenant = currentResults.tenants[0];
    if (!firstTenant.results || !firstTenant.results.provisions) return;
    firstTenant.results.provisions.forEach(p => {
        if (p.provision_id) lockedProvisionIds.add(p.provision_id);
    });

    // Disable and check locked provisions in the UI
    const checkboxes = document.querySelectorAll("#provision-list input[type=checkbox]");
    checkboxes.forEach(cb => {
        if (lockedProvisionIds.has(cb.value)) {
            cb.checked = true;
            cb.disabled = true;
            cb.closest("li").classList.add("provision-locked");
            cb.closest("li").title = "Already analyzed \u2014 will be included automatically";
        }
    });

    // Insert section dividers: "Already analyzed" above locked items, "Add to analysis" above unlocked
    const list = document.querySelector("#provision-list");
    if (list && lockedProvisionIds.size > 0) {
        // Remove any existing dividers
        list.querySelectorAll(".provision-section-label").forEach(el => el.remove());

        const items = Array.from(list.querySelectorAll("li:not(.provision-section-label)"));
        let insertedLocked = false;
        let insertedNew = false;

        for (const li of items) {
            const cb = li.querySelector("input[type=checkbox]");
            if (!cb) continue;
            const isLocked = lockedProvisionIds.has(cb.value);

            if (isLocked && !insertedLocked) {
                const label = document.createElement("li");
                label.className = "provision-section-label provision-section-locked";
                label.textContent = "\u2713 Already analyzed \u2014 included automatically";
                list.insertBefore(label, li);
                insertedLocked = true;
            } else if (!isLocked && !insertedNew) {
                const label = document.createElement("li");
                label.className = "provision-section-label provision-section-new";
                label.textContent = "+ Select review areas to add";
                list.insertBefore(label, li);
                insertedNew = true;
            }
        }
    }

    updateSubmitState();
}

async function loadProvisions() {
    try {
        const resp = await fetch(selectedAnalysisType.provisions_endpoint);
        if (!resp.ok) throw new Error("Failed to load provisions");
        provisions = await resp.json();
        renderProvisions();
    } catch (err) {
        console.error("Failed to load provisions:", err);
        provisions = [];
    }
}

function renderProvisions() {
    const list = $("#provision-list");
    list.innerHTML = "";
    provisions.forEach(p => {
        // Skip LP-00 (always_on) — it runs automatically, not shown in list
        if (p.id === "LP-00" || p.always_on) return;
        const li = document.createElement("li");
        li.innerHTML = `<span title="${esc(p.description)}">${esc(p.id)} ${esc(p.name)}</span>`;
        list.appendChild(li);
    });
    customProvisions.forEach((cp, i) => {
        const li = document.createElement("li");
        li.innerHTML = `<span>${esc(cp.name)}</span>
            <button class="remove-file" data-custom="${i}" title="Remove">&times;</button>`;
        li.querySelector(".remove-file").addEventListener("click", e => {
            e.stopPropagation();
            customProvisions.splice(i, 1);
            renderProvisions();
            updateSubmitState();
        });
        list.appendChild(li);
    });

    // If in add-more mode, lock already-analyzed provisions immediately after render
    if (addMoreMode === "addmore") {
        lockAnalyzedProvisions();
    }
}

function toggleAllProvisions(checked) {
    // Standard provisions
    $$("#provision-list input[type=checkbox]").forEach(cb => {
        if (!cb.disabled) cb.checked = checked;
    });
    // Non-standard provisions (from prescan)
    $$(".nonstandard-cb").forEach(cb => {
        if (!cb.disabled) cb.checked = checked;
    });
    updateSubmitState();
}

function addCustomProvision() {
    const input = $("#custom-provision-input");
    const name = input.value.trim();
    if (!name) return;

    const id = `CUSTOM-${String(customProvisions.length + 1).padStart(2, "0")}`;
    customProvisions.push({id, name, description: name, search_hints: []});
    input.value = "";
    renderProvisions();
    updateSubmitState();
}

function getSelectedProvisionIds() {
    const checked = [];
    $$("#provision-list input[type=checkbox]:checked").forEach(cb => {
        checked.push(cb.value);
    });
    return checked;
}


// (showRunConfigModal removed in Step 138 — replaced by inline identity checkboxes)

async function handleSubmit() {
    const btn = $("#analyze-btn");
    const errorEl = $("#submit-error");
    errorEl.classList.add("hidden");

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
        // ── Add More mode ──
        if (addMoreMode === "addmore" && currentJobId) {
            const selectedIds = getSelectedProvisionIds();
            const newIds = selectedIds.filter(id => !lockedProvisionIds.has(id));
            const hasNewTenants = tenantFiles.length > 0;
            const hasNewProvisions = newIds.length > 0;

            if (!hasNewTenants && !hasNewProvisions) {
                throw new Error("Upload new leases or select new provisions to continue.");
            }

            isAddMoreRun = true;
            addMoreMode = null;
            lockedProvisionIds = new Set();

            // If new tenants: add them, optionally bundling new provisions in the same call
            // to avoid the race condition where add-provisions sees status="processing"
            if (hasNewTenants) {
                const formData = new FormData();
                tenantFiles.forEach(f => formData.append("tenant_files", f));
                // Bundle new provisions into add-tenants so they're applied before
                // incremental processing starts — avoids race condition
                if (hasNewProvisions) {
                    formData.append("add_provisions", JSON.stringify(newIds));
                }
                const resp = await fetch(`/api/jobs/${currentJobId}/add-tenants`, {
                    method: "POST",
                    body: formData,
                });
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    throw new Error(err.detail || `Server error (${resp.status})`);
                }
                // Provisions were bundled — skip separate add-provisions call
                showState("processing");
                const statusResp = await fetch(`/api/jobs/${currentJobId}`);
                initProcessingView(await statusResp.json());
                startPolling();
                return;
            }

            // Provisions-only path (no new tenants): safe to call add-provisions directly
            if (hasNewProvisions) {
                const resp = await fetch(`/api/jobs/${currentJobId}/add-provisions`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provisions: newIds }),
                });
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    throw new Error(err.detail || `Server error (${resp.status})`);
                }
                showState("processing");
                initProcessingView(await resp.json());
                startPolling();
                return;
            }
        }

        // ── Normal submission ──
        const submitMode = getSelectedMode();
        // Step 261: perspective is mandatory. If the user somehow reached submit
        // without picking one (e.g. via a stale enabled state), bail and red-flag
        // the card. updateSubmitState should already prevent this on the happy path.
        const submitPerspective = getSelectedPerspective();
        if (!submitPerspective) {
            const card = document.querySelector(".perspective-selector-card");
            if (card) card.classList.add("required-indicator");
            const wrap = document.getElementById("perspective-selector-wrapper");
            if (wrap) wrap.scrollIntoView({ behavior: "smooth", block: "center" });
            updateSubmitState();
            return;
        }
        if (tenantFiles.length === 0) return;
        if (submitMode !== "analyze" && !templateFile) return;

        // Step 138: Derive identity_check from inline checkboxes (replaces modal)
        let identityCheck = "clauses_only";
        if (identityChecks.landlord && identityChecks.tenant) {
            identityCheck = "landlord_tenant";
        } else if (identityChecks.landlord || identityChecks.property) {
            identityCheck = "landlord_property";
        }

        const formData = new FormData();
        formData.append("access_code", sessionStorage.getItem("cam_access_code") || "");
        const _uploadEmail = $("#email-input").value.trim();
        formData.append("email", _uploadEmail);
        if (_uploadEmail) setJobEmail(_uploadEmail);

        // Step 253: in Mode C (analyze), template is optional/ignored.
        formData.append("mode", submitMode);
        // Step 261: persist perspective alongside mode so the backend can branch on it.
        formData.append("perspective", submitPerspective);
        if (submitMode !== "analyze" && templateFile) {
            formData.append("template_file", templateFile);
        }

        tenantFiles.forEach(f => {
            formData.append("tenant_files", f);
        });

        if (customProvisions.length > 0) {
            formData.append("custom_provisions", JSON.stringify(customProvisions));
        }

        formData.append("strictness", "standard");
        formData.append("template_type", "blank_template");
        formData.append("identity_check", identityCheck);

        const resp = await fetch(selectedAnalysisType.endpoint, {
            method: "POST",
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            const detail = Array.isArray(err.detail)
                ? err.detail.map(e => e.msg || e.message || JSON.stringify(e)).join("; ")
                : err.detail;
            throw new Error(detail || `Server error (${resp.status})`);
        }

        const data = await resp.json();
        currentJobId = data.job_id;

        history.pushState(null, "", `/results/${currentJobId}`);

        isAddMoreRun = false;
        showState("processing");
        initProcessingView(data);
        startPolling();
    } catch (err) {
        if (err.message !== "_MODAL_CANCELLED_") {
            errorEl.textContent = err.message;
            errorEl.classList.remove("hidden");
        }
        btn.disabled = false;
        btn.textContent = "Review Leases";
    }
}

// ══════════════════════════════════════════════════════
// STATE 4: Processing
// ══════════════════════════════════════════════════════

function initProcessingView(jobData) {
    processingDetailsExpanded = true;

    // Use global jobEmail (set from upload page or processing capture)
    if (jobEmail) {
        syncEmailState();
    } else {
        // No email yet — show capture card and default notice
        $("#email-notice").textContent = "Bookmark this link to return to your results.";
        maybeShowEmailCapture(null);
    }

    // Start educational carousel
    mountProcessingCarousel();
    mountProcessingHero();
    initCarousel();

    // Initialize processing chat
    initProcessingChat();

    const resultsUrl = `${window.location.origin}/results/${currentJobId}`;
    $("#results-link-input").value = resultsUrl;

    // Reset cancel button state
    const cancelBtn = $("#cancel-btn");
    cancelBtn.classList.remove("hidden");
    cancelBtn.disabled = false;
    cancelBtn.textContent = "Cancel Analysis";
    // Show nav cancel button during processing
    const navCancelBtn = $("#workflow-cancel-btn");
    if (navCancelBtn) { navCancelBtn.classList.remove("hidden"); navCancelBtn.disabled = false; }

    // Back-to-results link (add-more runs only)
    const backLink = $("#processing-back-link");
    if (backLink) {
        backLink.classList.toggle("hidden", !isAddMoreRun);
    }

    const detailToggle = $("#processing-detail-toggle");
    if (detailToggle) {
        detailToggle.onclick = () => {
            processingDetailsExpanded = !processingDetailsExpanded;
            const detailList = $("#tenant-progress-list");
            if (detailList) detailList.classList.toggle("hidden", !processingDetailsExpanded);
            detailToggle.textContent = processingDetailsExpanded ? "Hide details" : "Show details";
            detailToggle.setAttribute("aria-expanded", processingDetailsExpanded ? "true" : "false");
        };
        detailToggle.textContent = processingDetailsExpanded ? "Hide details" : "Show details";
        detailToggle.setAttribute("aria-expanded", processingDetailsExpanded ? "true" : "false");
    }

    // Show tenant names immediately with "Queued" status (don't wait for first poll)
    const container = $("#tenant-progress-list");
    const estimateEl = $("#estimate-remaining");
    const readyCard = $("#processing-ready-card");
    const readyList = $("#processing-ready-list");
    if (readyCard) readyCard.classList.add("hidden");
    if (readyList) readyList.innerHTML = "";
    // Use local tenantFiles if available, else pull filenames from job data
    let names = tenantFiles.map(f => f.name);
    if (names.length === 0 && jobData && jobData.input_config && jobData.input_config.tenants) {
        names = jobData.input_config.tenants.map(t => t.filename || "Lease");
    }
    if (names.length > 0) {
        container.innerHTML = names.map(name => `<div class="processing-tenant-card">
            <div class="processing-tenant-top">
                <div class="processing-tenant-name">${esc(name)}</div>
                <div class="processing-tenant-status">Queued</div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width:0%"></div>
            </div>
        </div>`).join("");
        container.classList.toggle("hidden", !processingDetailsExpanded);
        // Step 196: start stable whole-job progress tracking from the initial estimate
        const _provIds = (jobData && jobData.input_config && jobData.input_config.provisions) || [];
        const _customProvisions = (jobData && jobData.input_config && jobData.input_config.custom_provisions) || [];
        const _provCount = (_provIds.length + _customProvisions.length) || LP_PROGRESS_ITEMS.length;
        const { secsPerLease, mins } = calcEstimate(_provCount, identityChecks, names.length, [..._provIds, ..._customProvisions.map((p) => p.id || p.provision_id || "CUSTOM")]);
        currentSecsPerLease = secsPerLease;
        const estimateMinutesFromJob = Number(jobData && jobData.estimated_minutes);
        const _totalSecs = Number.isFinite(estimateMinutesFromJob) && estimateMinutesFromJob > 0
            ? estimateMinutesFromJob * 60
            : mins * 60;
        const startedAt = (jobData && (jobData.started_at || jobData.created_at)) || null;
        const _alreadyElapsed = startedAt
            ? Math.max(0, (Date.now() - new Date(startedAt).getTime()) / 1000)
            : 0;
        startEstimateCountdown(_totalSecs, { alreadyElapsedSecs: _alreadyElapsed, initialProgressFraction: 0 });
        renderProcessingOverview(jobData, (jobData.input_config || {}).tenants || []);
    } else {
        container.innerHTML = '<div class="processing-ready-empty"><span class="spinner"></span> Starting analysis...</div>';
        container.classList.toggle("hidden", !processingDetailsExpanded);
        estimateEl.textContent = "";
        renderProcessingOverview(jobData, []);
    }

    // If this view is initialized mid-run (for example after a frontend reload),
    // replace placeholder queued rows with the live job state immediately.
    initLpProgressPanel(jobData);
    renderProgress(jobData);
    renderProcessingChecklist(jobData);
}

// ── LP Progress Panel (Step 288) ──────────────────────────────

const LP_PROGRESS_ITEMS = [
    { id: "LP-01", name: "Rent & Payment Terms" },
    { id: "LP-02", name: "Rent Escalation" },
    { id: "LP-03", name: "Lease Term & Renewal" },
    { id: "LP-04", name: "Security Deposit" },
    { id: "LP-05", name: "Permitted Use" },
    { id: "LP-06", name: "Maintenance & Repairs" },
    { id: "LP-07", name: "CAM Charges" },
    { id: "LP-08", name: "Insurance Requirements" },
    { id: "LP-09", name: "Subletting & Assignment" },
    { id: "LP-10", name: "Alterations & Improvements" },
    { id: "LP-11", name: "Default & Remedies" },
    { id: "LP-12", name: "Early Termination" },
    { id: "LP-13", name: "Indemnification & Liability" },
    { id: "LP-14", name: "Force Majeure" },
    { id: "LP-15", name: "Signage Rights" },
    { id: "LP-16", name: "Parking" },
    { id: "LP-17", name: "Dispute Resolution" },
    { id: "LP-18", name: "Holdover Provisions" },
    { id: "LP-19", name: "Utilities" },
    { id: "LP-20", name: "Exclusivity" },
    { id: "LP-21", name: "Guaranty of Lease" },
    { id: "LP-22", name: "SNDA" },
    { id: "LP-23", name: "Percentage Rent" },
    { id: "LP-24", name: "Damage & Destruction" },
    { id: "LP-25", name: "Condemnation" },
    { id: "LP-26", name: "Quiet Enjoyment" },
    { id: "LP-27", name: "Landlord Default" },
    { id: "LP-28", name: "Compliance with Laws" },
    { id: "LP-29", name: "Right of Entry" },
    { id: "LP-30", name: "Estoppel Certificate" },
    { id: "LP-31", name: "Co-Tenancy" },
    { id: "LP-32", name: "Hazardous Materials" },
];

function _lpStateDisplay(state) {
    switch (state) {
        case "processing":               return { icon: "◌", cls: "state-processing" };
        case "covered":                  return { icon: "✓", cls: "state-covered" };
        case "covered_unfavorable":      return { icon: "⚠", cls: "state-covered_unfavorable" };
        case "potentially_unenforceable":return { icon: "⚠", cls: "state-potentially_unenforceable" };
        case "partial":                  return { icon: "◑", cls: "state-partial" };
        case "ambiguous":
        case "review_needed":            return { icon: "?", cls: "state-review_needed" };
        case "missing":                  return { icon: "✗", cls: "state-missing" };
        case "broken_xref":              return { icon: "⚡", cls: "state-broken_xref" };
        case "not_applicable":           return { icon: "—", cls: "state-not_applicable" };
        default:                         return { icon: "·", cls: "state-pending" };
    }
}

function initLpProgressPanel(jobData) {
    const panel = $("#lp-progress-panel");
    const list = $("#lp-progress-list");
    if (!panel || !list) return;

    const customPs = (jobData && jobData.input_config && jobData.input_config.custom_provisions) || [];
    const allItems = [
        ...LP_PROGRESS_ITEMS,
        ...customPs.map(cp => ({
            id: cp.id || cp.provision_id || "CUSTOM",
            name: cp.name || cp.provision_name || "Custom Review Area",
        })),
    ];

    // Update subtitle to reflect actual count (standard + custom)
    const subtitle = panel.querySelector(".processing-side-subtitle");
    if (subtitle) {
        const customCount = customPs.length;
        const standardCount = LP_PROGRESS_ITEMS.length;
        subtitle.textContent = customCount > 0
            ? `CAM is checking all ${standardCount} standard issue areas plus ${customCount} custom area${customCount !== 1 ? "s" : ""}.`
            : `CAM is checking all ${standardCount} standard issue areas.`;
    }

    // Interleave first half / second half so row-flow grid gives left col = LP-01..LP-16,
    // right col = LP-17..LP-32 without relying on grid-auto-flow: column (Step 319).
    const mid = Math.ceil(allItems.length / 2);
    const firstHalf = allItems.slice(0, mid);
    const secondHalf = allItems.slice(mid);
    const interleaved = firstHalf.flatMap((item, i) => secondHalf[i] ? [item, secondHalf[i]] : [item]);

    list.innerHTML = interleaved.map(item =>
        `<div class="lp-progress-row state-pending" id="lp-row-${esc(item.id)}">` +
        `<span class="lp-progress-icon">·</span>` +
        `<span class="lp-progress-name" title="${esc(item.name)}">${esc(item.name)}</span>` +
        `</div>`
    ).join("");

    panel.classList.remove("hidden");
}

function updateLpProgressPanel(lpProgress, jobStatus) {
    const list = $("#lp-progress-list");
    if (!list) return;

    if (lpProgress) {
        Object.values(lpProgress).forEach(entry => {
            const row = document.getElementById(`lp-row-${entry.lp_id}`);
            if (!row) return;
            const { icon, cls } = _lpStateDisplay(entry.state);
            row.className = `lp-progress-row ${cls}`;
            const iconEl = row.querySelector(".lp-progress-icon");
            if (iconEl) iconEl.textContent = icon;
        });
    }

    if (jobStatus === "completed") {
        list.querySelectorAll(".lp-progress-row.state-pending").forEach(row => {
            row.className = "lp-progress-row state-covered";
            const iconEl = row.querySelector(".lp-progress-icon");
            if (iconEl) iconEl.textContent = "✓";
        });
    }
}

function mountProcessingCarousel() {
    const slot = $("#processing-carousel-slot");
    const carousel = $("#cam-carousel");
    if (!slot || !carousel) return;
    if (carousel.parentElement !== slot) {
        slot.appendChild(carousel);
    }
}

function mountProcessingHero() {
    const slot = $("#processing-status-slot");
    const hero = $$(".processing-hero-shell")[0];
    if (!slot || !hero) return;
    if (hero.parentElement !== slot) {
        slot.appendChild(hero);
    }
}

async function handleCancel() {
    if (!currentJobId) return;
    if (!confirm("Cancel this analysis? Completed results will be kept.")) return;

    const btn = $("#cancel-btn");
    btn.disabled = true;
    btn.textContent = "Cancelling...";

    try {
        const resp = await fetch(`/api/jobs/${currentJobId}/cancel`, { method: "POST" });
        if (!resp.ok) {
            const data = await resp.json().catch(() => ({}));
            console.warn("[CAM] Cancel failed:", data.detail || resp.status);
            cancelRequested = false;
            btn.disabled = false;
            btn.textContent = "Cancel Analysis";
            return;
        }
        // Show cancelling state immediately
        cancelRequested = true;
        showCancellingState();
        // Polling continues to detect when status flips to "cancelled"
    } catch (err) {
        console.error("Cancel error:", err);
        cancelRequested = false;
        btn.disabled = false;
        btn.textContent = "Cancel Analysis";
    }
}

function showCancellingState() {
    const container = $("#tenant-progress-list");
    const estimateEl = $("#estimate-remaining");
    estimateEl.textContent = "";
    container.innerHTML = `
        <div class="cancelling-state">
            <span class="spinner"></span>
            <div class="cancelling-title">Cancelling analysis...</div>
            <div class="cancelling-detail">Waiting for the current operation to finish. This may take up to a minute.</div>
        </div>`;
    // Hide cancel button and processing info while cancelling
    const cancelBtn = $("#cancel-btn");
    if (cancelBtn) cancelBtn.classList.add("hidden");
    const wfCancelBtn = $("#workflow-cancel-btn");
    if (wfCancelBtn) { wfCancelBtn.textContent = "Cancelling\u2026"; wfCancelBtn.disabled = true; }
}

function renderProgress(job) {
    const container = $("#tenant-progress-list");
    const estimateEl = $("#estimate-remaining");
    const readyCard = $("#processing-ready-card");
    const readyList = $("#processing-ready-list");
    const detailToggle = $("#processing-detail-toggle");

    if (!job) {
        if (container) container.innerHTML = '<div class="processing-ready-empty"><span class="spinner"></span> Starting analysis...</div>';
        if (readyList) readyList.innerHTML = "";
        if (readyCard) readyCard.classList.add("hidden");
        estimateEl.textContent = "";
        renderProcessingOverview(job, []);
        renderProcessingChecklist(job);
        return;
    }

    const tenants = (job.input_config || {}).tenants || [];
    const jobStatus = job.status || "";
    updateLpProgressPanel(job.lp_progress || {}, jobStatus);

    // Step 316: compute Stage 3 LP sub-progress for Mode C progress interpolation.
    // lp_progress entries with a terminal state (anything except 'pending'/'processing')
    // indicate that LP's coverage assessment is done.
    const _isModeC316 = (job.input_config || {}).mode === "analyze";
    const _lpProg316 = job.lp_progress || {};
    const _lpDone316 = _isModeC316
        ? Object.values(_lpProg316).filter(e => e.state && e.state !== 'pending' && e.state !== 'processing').length
        : 0;
    const _lpFrac316 = Math.min(1, _lpDone316 / 32); // fraction of 32 standard LPs complete

    // Step 319 debug: log what stage/total_stages the frontend sees for Mode C tenants.
    if (_isModeC316) {
        tenants.forEach((t, i) => {
            if (t.status === 'processing') {
                console.log(`[progress_debug] tenant[${i}] stage=${t.current_stage}/${t.total_stages} lpDone=${_lpDone316} lpFrac=${_lpFrac316.toFixed(2)} status=${t.status}`);
            }
        });
    }

    let overallFraction = 0;
    tenants.forEach(t => {
        let frac = getTenantProgressFraction(t, jobStatus);
        // Stage 3 interpolation: smooth 50%→75% as each LP completes instead of flat bar.
        // total_stages === 4 guard ensures this only fires when the backend reports the
        // correct 4-stage Mode C pipeline (post-Step-317 backend fix).
        if (_isModeC316 && Number(t.current_stage) === 3 && Number(t.total_stages) === 4) {
            frac = 0.50 + (_lpFrac316 * 0.25);
        }
        overallFraction += frac;
    });
    const totalCount = tenants.length;
    estimateProgressFraction = totalCount > 0 ? (overallFraction / totalCount) : 0;
    updateEstimateDisplay();
    renderProcessingOverview(job, tenants);
    renderProcessingChecklist(job);
    const completedTenants = [];
    const displayTenants = tenants
        .map((tenant, idx) => ({ tenant, idx }))
        .sort((a, b) => {
            const effectiveA = (a.tenant.status === "queued" && jobStatus === "processing") ? "processing" : a.tenant.status;
            const effectiveB = (b.tenant.status === "queued" && jobStatus === "processing") ? "processing" : b.tenant.status;
            const rank = (status) => {
                if (status === "processing") return 0;
                if (status === "completed") return 1;
                if (status === "failed") return 2;
                if (status === "cancelled") return 3;
                return 4;
            };
            const delta = rank(effectiveA) - rank(effectiveB);
            if (delta !== 0) return delta;
            const stageDelta = (Number(b.tenant.current_stage) || 0) - (Number(a.tenant.current_stage) || 0);
            if (stageDelta !== 0) return stageDelta;
            return a.idx - b.idx;
        });

    // Filter out completed tenants — they appear in the top ready card instead
    const inProgressTenants = displayTenants.filter(({ tenant: t }) => {
        const es = (t.status === "queued" && jobStatus === "processing") ? "processing" : t.status;
        if (es === "completed") {
            completedTenants.push({ ...t, tenantIdx: displayTenants.find(d => d.tenant === t)?.idx });
        }
        return es !== "completed";
    });

    if (container) {
        container.innerHTML = inProgressTenants.map(({ tenant: t, idx: i }) => {
            let statusLabel = "Queued";
            let stageDetail = "";
            let fillClass = "";
            let width = "0%";
            let statusMeta = "";
            let percentValue = "0%";
            let progressPill = "Queued";
            let stagePill = "Queued";

            const effectiveStatus = (t.status === "queued" && jobStatus === "processing")
                ? "processing" : t.status;

            if (effectiveStatus === "processing") {
                fillClass = "processing";
                if (t.current_stage && t.total_stages) {
                    let _rawFrac = getTenantProgressFraction(t, jobStatus);
                    // Step 316/317: Stage 3 interpolation — use LP completion count.
                    // Requires total_stages === 4 (set by backend post-Step-317).
                    if (_isModeC316 && Number(t.current_stage) === 3 && Number(t.total_stages) === 4) {
                        _rawFrac = 0.50 + (_lpFrac316 * 0.25);
                    }
                    // Step 316/319: Stage 4 pulse — additive so "processing" base class is kept.
                    if (_isModeC316 && Number(t.current_stage) === 4) {
                        fillClass += " progress-fill--pulsing";
                    }
                    const tenantPct = Math.round(_rawFrac * 100);
                    statusLabel = getProcessingStageCopy(t.current_stage, "").headline;
                    width = `${tenantPct}%`;
                    const stageMeta = `Stage ${Number(t.current_stage) || 1} of ${Number(t.total_stages) || 6}`;
                    statusMeta = `${tenantPct}% • ${stageMeta}`;
                    stageDetail = t.stage_detail || "";
                } else {
                    statusLabel = "Preparing analysis";
                    width = "8%";
                    statusMeta = "Queued • Preparing analysis";
                }
            } else if (effectiveStatus === "cancelled") {
                statusLabel = "Cancelled";
                statusMeta = "Cancelled";
            } else if (effectiveStatus === "failed") {
                statusLabel = "Failed";
                fillClass = "failed";
                width = "100%";
                statusMeta = "Failed";
                stageDetail = t.error || "";
            } else {
                statusMeta = "Queued";
            }

            percentValue = width;
            if (effectiveStatus === "processing") {
                progressPill = statusLabel;
                stagePill = t.current_stage && t.total_stages
                    ? `Stage ${Number(t.current_stage) || 1} of ${Number(t.total_stages) || 6}`
                    : "Queued";
            } else if (effectiveStatus === "failed") {
                progressPill = "Failed";
                stagePill = "Stopped";
            } else if (effectiveStatus === "cancelled") {
                progressPill = "Cancelled";
                stagePill = "Stopped";
            }

            if (effectiveStatus === "processing") {
                statusMeta = stagePill === "Queued" ? "Preparing analysis" : stagePill;
            }

            return `<div class="processing-tenant-card">
                <div class="processing-tenant-meta-row">
                    <span class="processing-overview-meta-pill">${esc(progressPill)}</span>
                    <span class="processing-overview-meta-pill">${esc(stagePill)}</span>
                </div>
                <div class="processing-tenant-top">
                    <div class="processing-tenant-name">${esc(t.filename || `Contract ${i + 1}`)}</div>
                    <div class="processing-tenant-status-wrap">
                        <div class="processing-tenant-percent">${esc(percentValue)}</div>
                        <div class="processing-tenant-status">${esc(statusLabel)}</div>
                        <div class="processing-tenant-status-meta">${esc(statusMeta)}</div>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${fillClass}" style="width:${width}"></div>
                </div>
                <div class="processing-tenant-detail-row">
                    ${stageDetail ? `<div class="processing-tenant-detail">${esc(stageDetail)}</div>` : `<div class="processing-tenant-detail"></div>`}
                </div>
                <div class="processing-tenant-action-row"><button class="btn btn-primary btn-sm processing-tenant-open-btn" data-tenant-open="${i}" ${effectiveStatus === "completed" ? "" : "disabled"}>Open Contract</button></div>
            </div>`;
        }).join("");
        container.querySelectorAll("[data-tenant-open]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const idx = Number(btn.dataset.tenantOpen);
                if (Number.isNaN(idx)) return;
                await openReadyContractFromProcessing(idx);
            });
        });
    }

    if (readyCard && readyList) {
        readyCard.classList.add("hidden");
        readyList.innerHTML = "";
    }

    // Hide the entire detail card if no in-progress tenants remain
    const detailCard = container ? container.closest(".processing-detail-card") : null;
    if (detailCard && inProgressTenants.length === 0) {
        detailCard.classList.add("hidden");
    } else if (detailCard) {
        detailCard.classList.remove("hidden");
    }

    if (detailToggle) {
        detailToggle.textContent = processingDetailsExpanded ? "Hide details" : "Show details";
        detailToggle.setAttribute("aria-expanded", processingDetailsExpanded ? "true" : "false");
    }
    if (container) {
        container.classList.toggle("hidden", !processingDetailsExpanded);
    }
}

function handleCancelledJob(job) {
    cancelRequested = false;
    isAddMoreRun = false;

    // Hide cancel button
    const cancelBtn = $("#cancel-btn");
    if (cancelBtn) cancelBtn.classList.add("hidden");
    const navCancelBtnDone = $("#workflow-cancel-btn");
    if (navCancelBtnDone) navCancelBtnDone.classList.add("hidden");

    const estimateEl = $("#estimate-remaining");
    if (estimateEl) estimateEl.textContent = "";

    // Check if any tenants completed
    const tenants = (job.input_config || {}).tenants || [];
    const completedTenants = tenants.filter(t => t.status === "completed");

    const container = $("#tenant-progress-list");

    if (completedTenants.length > 0) {
        container.innerHTML = `
            <div class="cancel-confirm">
                <div class="cancel-confirm-icon">&#10003;</div>
                <div class="cancel-confirm-title">Analysis cancelled</div>
                <div class="cancel-confirm-detail">
                    Your analysis was stopped. ${completedTenants.length} of ${tenants.length}
                    lease${tenants.length > 1 ? "s" : ""} completed before cancellation.
                    Results for completed leases have been preserved.
                </div>
                <div class="cancel-confirm-actions">
                    <button class="btn btn-primary" id="cancel-new-analysis-btn">&#128196; Start New Analysis</button>
                    <button class="btn btn-outline" id="cancel-view-partial-btn">&#128203; View Partial Results</button>
                </div>
            </div>`;
        $("#cancel-new-analysis-btn").addEventListener("click", () => {
            currentJobId = null; currentJobData = null; currentResults = null;
            currentTenantIndex = 0; addMoreMode = null; activeTopTab = "overview"; snapshotActiveIndex = null; snapshotVisited = false; snapshotSort = 'risk'; snapshotSeverityFilter = new Set(); snapshotConfidenceFilter = new Set(); snapshotStatusFilter = 'all'; snapshotSearch = ''; snapshotContractFilter = new Set(); // prescan removed (112), Step 130
            if (expiryTimer) { clearInterval(expiryTimer); expiryTimer = null; }
            stopPolling(); history.replaceState(null, "", "/"); enterApp();
        });
        $("#cancel-view-partial-btn").addEventListener("click", () => {
            window.CAM.viewCancelledResults();
        });
    } else {
        container.innerHTML = `
            <div class="cancel-confirm">
                <div class="cancel-confirm-icon">&#10003;</div>
                <div class="cancel-confirm-title">Analysis cancelled</div>
                <div class="cancel-confirm-detail">
                    Your analysis was stopped before any results were available.
                </div>
                <div class="cancel-confirm-actions">
                    <button class="btn btn-primary" id="cancel-new-analysis-btn">&#128196; Start New Analysis</button>
                </div>
            </div>`;
        $("#cancel-new-analysis-btn").addEventListener("click", () => {
            currentJobId = null; currentJobData = null; currentResults = null;
            currentTenantIndex = 0; addMoreMode = null; activeTopTab = "overview"; snapshotActiveIndex = null; snapshotVisited = false; snapshotSort = 'risk'; snapshotSeverityFilter = new Set(); snapshotConfidenceFilter = new Set(); snapshotStatusFilter = 'all'; snapshotSearch = ''; snapshotContractFilter = new Set(); // prescan removed (112), Step 130
            if (expiryTimer) { clearInterval(expiryTimer); expiryTimer = null; }
            stopPolling(); history.replaceState(null, "", "/"); enterApp();
        });
    }
}

function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(pollJobStatus, POLL_INTERVAL_MS);
    pollJobStatus();
}

function stopPolling() {
    stopEstimateCountdown(); // Step 196: always kill countdown when polling stops
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

async function openReadyContractFromProcessing(tenantIdx) {
    if (!currentJobId || Number.isNaN(Number(tenantIdx))) return;
    try {
        await loadResults();
        showState("results");
        await openContractDetail(Number(tenantIdx));
    } catch (err) {
        console.error("Error opening ready contract from processing:", err);
    }
}

function handleBackToResults() {
    stopPolling();
    loadResults().then(() => {
        showState("results");
    });
}

function cancelAddMore() {
    addMoreMode = null;
    lockedProvisionIds = new Set();
    showState("results");
}

async function pollJobStatus() {
    if (!currentJobId) return;
    // Safety: stop polling if we've already left the processing state
    if (currentState !== "processing") {
        stopPolling();
        return;
    }

    try {
        const resp = await fetch(`/api/jobs/${currentJobId}`);

        if (resp.status === 410) {
            stopPolling();
            showExpiredPage();
            return;
        }
        if (resp.status === 404) {
            pollNotFoundCount = (pollNotFoundCount || 0) + 1;
            if (pollNotFoundCount >= 3) {
                stopPolling();
                // Show a clear server-restart message on the processing screen
                // rather than navigating away — the user can simply re-upload
                const heroShell = $("#processing-hero-shell") || document.querySelector(".processing-hero-shell");
                const statusCard = document.querySelector(".processing-status-card");
                if (statusCard) {
                    statusCard.innerHTML = `
                        <div class="processing-kicker" style="color:var(--error,#dc2626);">Analysis interrupted</div>
                        <div class="processing-title">Server restarted mid-run</div>
                        <div class="processing-subtitle" style="max-width:30rem;">
                            The server was restarted while your analysis was running &mdash; likely because a code change was saved during processing.
                            Your results were not saved.
                        </div>
                        <div class="processing-subtitle" style="margin-top:1rem;">
                            <strong>To avoid this:</strong> run the server without <code>--reload</code> during long uploads.
                        </div>
                        <div style="margin-top:1.5rem;">
                            <button class="btn btn-primary" onclick="window.CAM.resetApp(); return false;">Start Over</button>
                        </div>
                    `;
                } else {
                    showExpiredPage("The server was restarted while your analysis was running. Results were not saved. Please start over.");
                }
            }
            return;
        }
        pollNotFoundCount = 0;
        if (!resp.ok) throw new Error("Failed to poll job status");

        const job = await resp.json();
        currentJobData = job;

        if (currentState === "processing" && !cancelRequested) {
            const tenants = (job.input_config || {}).tenants || [];
            console.log(`[CAM Poll] job.status=${job.status}, tenants:`, tenants.map(t => ({
                filename: t.filename, status: t.status, stage: t.stage,
                current_stage: t.current_stage, total_stages: t.total_stages,
                stage_detail: t.stage_detail
            })));
            renderProgress(job);
        }

        if (job.status === "completed") {
            stopPolling();
            stopCarousel();
            resetProcessingChat();
            await loadResults();
            showState("results");
            // Scroll to top so synopsis/summary bar is visible
            if (isAddMoreRun) {
                const resultsContent = $("#results-content");
                if (resultsContent) resultsContent.scrollIntoView({ behavior: "smooth", block: "start" });
                isAddMoreRun = false;
            }
        } else if (job.status === "cancelled") {
            stopPolling();
            stopCarousel();
            resetProcessingChat();
            handleCancelledJob(job);
        } else if (job.status === "failed") {
            stopPolling();
            stopCarousel();
            resetProcessingChat();
            renderProgress(job);
            const errorMsg = job.error || "Analysis failed. Please try again.";
            const container = $("#tenant-progress-list");
            container.innerHTML += `<div class="alert alert-error mt-2">${esc(errorMsg)}</div>`;
        }
    } catch (err) {
        console.error("Poll error:", err);
    }
}

// ══════════════════════════════════════════════════════
// Expiry Handling
// ══════════════════════════════════════════════════════

function showExpiredPage(message) {
    // Show expired/unavailable state
    const msg = message || "Results are no longer available. For security, all analysis data is automatically deleted after the expiry window. Please run a new analysis if needed.";
    const main = $(".app-main");
    main.innerHTML = `
        <div style="text-align:center; padding:4rem 2rem;">
            <div style="font-size:3rem; margin-bottom:1rem;">\uD83D\uDD12</div>
            <h2 style="margin-bottom:0.5rem;">Analysis Unavailable</h2>
            <p style="color:var(--text-muted); max-width:30rem; margin:0 auto 2rem;">
                ${esc(msg)}
            </p>
            <a href="/" class="btn btn-primary">Start New Analysis</a>
        </div>
    `;
}

function startExpiryCountdown(expiresAt) {
    if (expiryTimer) clearInterval(expiryTimer);

    const noticeEl = $("#expiry-notice");
    if (!noticeEl) return;

    function updateCountdown() {
        const now = Date.now();
        const expiry = new Date(expiresAt).getTime();
        const remainMs = expiry - now;

        if (remainMs <= 0) {
            noticeEl.textContent = "Results have expired.";
            noticeEl.className = "expiry-notice urgent";
            if (expiryTimer) clearInterval(expiryTimer);
            return;
        }

        const remainingMin = Math.floor(remainMs / 60000);
        const urgent = remainMs < 300000; // urgent under 5 minutes
        const warning = remainMs < 3600000; // warning under 60 minutes

        let timeStr;
        if (remainingMin >= 1440) {
            const days = Math.floor(remainingMin / 1440);
            const hours = Math.floor((remainingMin % 1440) / 60);
            const mins = remainingMin % 60;
            timeStr = `${days}d ${hours}h ${mins}m`;
        } else if (remainingMin > 60) {
            const hours = Math.floor(remainingMin / 60);
            const mins = remainingMin % 60;
            timeStr = `${hours}h ${mins}m`;
        } else {
            const secs = Math.floor((remainMs % 60000) / 1000);
            timeStr = remainingMin > 0 ? `${remainingMin}m ${secs}s` : `${secs}s`;
        }

        noticeEl.classList.remove("hidden");
        if (urgent) {
            noticeEl.textContent = `⚠ ${timeStr} to deletion`;
            noticeEl.className = "expiry-notice urgent";
        } else if (warning) {
            noticeEl.textContent = `🔒 ${timeStr} to deletion`;
            noticeEl.className = "expiry-notice warning";
        } else {
            noticeEl.textContent = `🔒 ${timeStr} to deletion`;
            noticeEl.className = "expiry-notice";
        }
    }

    updateCountdown();
    expiryTimer = setInterval(updateCountdown, 10000);
}

// ══════════════════════════════════════════════════════
// STATE 5: Results
// ══════════════════════════════════════════════════════

async function loadResults() {
    if (!currentJobId) return;

    try {
        window._conformingConcernsLoaded = false;
        const resp = await fetch(`/api/jobs/${currentJobId}/results`);

        if (resp.status === 410) {
            showExpiredPage();
            return;
        }
        if (!resp.ok) throw new Error("Failed to load results");
        currentResults = await resp.json();
        window.evidenceFocus = null;  // Step 361: reset on new job load
        restoreResultsViewState();
        renderResults();
    } catch (err) {
        console.error("Load results error:", err);
    }
}

// Step 254: returns true iff this job's results are Mode C (analyze).
// Uses input_config.mode from the job API (which Step 252 persists) and
// falls back to the per-tenant results.mode for safety.
function isJobModeC() {
    if (currentJobData && currentJobData.input_config && currentJobData.input_config.mode === "analyze") {
        return true;
    }
    if (currentResults && currentResults.tenants) {
        const first = currentResults.tenants.find(t => t && t.results && t.results.mode);
        if (first && first.results.mode === "analyze") return true;
    }
    return false;
}

// Step 261: returns the perspective the job was run with ("tenant" / "landlord"
// / "neutral") or null for jobs created before Step 261. Used by results-page
// renderers (AI Summary bar) and chat ui_context.
function getJobPerspective() {
    if (currentJobData && currentJobData.input_config && currentJobData.input_config.perspective) {
        return currentJobData.input_config.perspective;
    }
    if (currentResults && currentResults.tenants) {
        const first = currentResults.tenants.find(t => t && t.results && t.results.perspective);
        if (first && first.results.perspective) return first.results.perspective;
    }
    return null;
}

// Step 261: small pill HTML for the results-page perspective indicator. Returns
// empty string if no perspective is set (older jobs) so callers can drop it in
// without conditional logic.
function getPerspectiveIndicatorHtml() {
    const p = getJobPerspective();
    if (!p) return "";
    const label = getPerspectiveLabel(p);
    return '<span class="perspective-indicator" title="This run was analyzed from the ' + esc(label) + ' perspective.">Analyzed from <strong>' + esc(label) + '</strong> perspective</span>';
}

// Step 254: apply mode-specific UI rules. Step 257 expanded to hide Lease
// Summary + Document Comparison sub-tabs in Mode C; the Coverage & Gaps tab
// becomes the primary contract view, with Audit Trail kept for extraction info.
// Called from renderResults() and kept idempotent so re-renders stay in sync.
function applyModeSpecificUI() {
    const isC = isJobModeC();
    document.body.classList.toggle("mode-c", isC);
    // Step 257: hide Mode-A-only sub-tab buttons.
    // Lease Summary's empty state in Mode C reads "fully conforms with no deviations"
    // — misleading because there is no template to deviate from. Document Comparison
    // was hidden in Step 254 (no template = nothing to compare).
    const findingsBtn = document.getElementById("contract-tab-findings");
    const docviewBtn = document.getElementById("contract-tab-docview");
    const evidenceBtn = document.getElementById("contract-tab-evidence");
    const synthesisBtn = document.getElementById("contract-tab-synthesis");
    const contractviewBtn = document.getElementById("contract-tab-contractview");
    if (findingsBtn) findingsBtn.classList.toggle("hidden", isC);
    if (docviewBtn) docviewBtn.classList.toggle("hidden", isC);
    // Step 306b: Evidence View is Mode C-only (no template to compare against in Mode A)
    if (evidenceBtn) evidenceBtn.classList.toggle("hidden", !isC);
    // Step 311: Contract Interaction Review is Mode C-only
    if (synthesisBtn) synthesisBtn.classList.toggle("hidden", !isC);
    // Step 359: Contract View is Mode C-only
    if (contractviewBtn) contractviewBtn.classList.toggle("hidden", !isC);
    // Step 257: if persisted activeResultsTab points at a now-hidden tab, coerce
    // to coverage. This catches users who switched mode mid-session, or whose
    // sessionStorage retained "findings"/"docview" from a prior Mode A run.
    if (isC && (activeResultsTab === "findings" || activeResultsTab === "docview")) {
        activeResultsTab = "coverage";
    }
}

function renderResults() {
    if (!currentResults || !currentResults.tenants) return;

    applyModeSpecificUI();

    // Load job data if we don't have it
    if (!currentJobData) {
        fetch(`/api/jobs/${currentJobId}`)
            .then(r => r.json())
            .then(job => {
                currentJobData = job;
                if (job.expires_at) startExpiryCountdown(job.expires_at);
                applyModeSpecificUI();  // Step 254: re-apply once mode is known
                // Re-render perspective-aware surfaces now that job config is known.
                // renderNavSidebar and renderProvisionHeatmap both call getJobPerspective()
                // which reads currentJobData.input_config.perspective; they ran before
                // this fetch completed and got null perspective. Step 297d.J / 299 fix.
                renderNavSidebar();
                renderProvisionHeatmap();
            })
            .catch(() => {});
    } else {
        if (currentJobData.expires_at) startExpiryCountdown(currentJobData.expires_at);
    }

    // Initialize chat panel (always-on, no FAB on wide screens)
    initChat();
    // Show mobile FAB
    const mobileFab = $("#chat-fab-mobile");
    if (mobileFab) mobileFab.classList.remove("hidden");

    renderIncompleteBanner();   // Step 477: must run before any summary surface
    renderPanelBanner();        // Step 497: panel provenance, distinct from the above
    renderNavSidebar();
    syncResultsTopBarLayout();
    renderDealBrief();
    renderProvisionsScopeCard();
    renderDealOverview();
    renderAISummaryBar();
    renderProvisionHeatmap();
    renderContractStatusPanel();
    renderTechDetails();
    renderTenantSelector();

    // Step 122: Filter bar no longer shown on Analysis Overview — moved to Run Snapshot
    // initFilterBar() still needed to initialize the dropdowns
    const filterBar = $("#filter-bar");
    if (filterBar) filterBar.classList.add("hidden");

    // Populate docview tenant selector
    const dts = $("#docview-tenant-select");
    if (dts) {
        dts.innerHTML = currentResults.tenants.map((t, i) =>
            `<option value="${i}">${esc(t.filename)}</option>`
        ).join("");
        dts.value = currentTenantIndex;
    }

    // Initialize filter bar (043)
    initFilterBar();

    // Initialize chat scope selector (044)
    initChatScope();

    // ── Step 116: Top-level tabs + Run Snapshot ──
    const topTabBar = $("#top-tab-bar");
    if (topTabBar) {
        topTabBar.querySelectorAll(".top-tab").forEach(btn => {
            btn.onclick = () => switchTopTab(btn.dataset.topTab);
        });
    }
    // Hide Leases tab when only one lease in the run — it's just noise for single-lease
    const _leasesTabBtn = document.getElementById('top-tab-contracts');
    if (_leasesTabBtn) _leasesTabBtn.classList.toggle('hidden', currentResults.tenants.length <= 1);

    const backBtn = $("#contract-detail-back");
    if (backBtn) backBtn.onclick = closeContractDetail;

    // Wire detail sub-tab clicks (now in top nav)
    document.querySelectorAll("#contract-tab-findings, #contract-tab-docview, #contract-tab-audittrail, #contract-tab-coverage, #contract-tab-contractview, #contract-tab-evidence, #contract-tab-synthesis").forEach(function(btn) {
        btn.onclick = function() {
            var _l = { findings: 'Lease Summary', docview: 'Document Comparison', audittrail: 'Audit', coverage: 'Key Issues', contractview: 'Contract View', evidence: 'Evidence', synthesis: 'Contract Interaction' };
            // Step 281: include perspective indicator on the coverage
            // tab so the bar doesn't flash from "no perspective" to
            // "perspective" when switchResultsTab runs after this.
            var _subRight = (btn.dataset.tab === "coverage") ? _coverageSubheaderRight() : "";
            setSubheader(_l[btn.dataset.tab] || btn.dataset.tab, _subRight);
            if (!contractDetailOpen) {
                showNoContractPlaceholder(btn.dataset.tab);
            } else {
                switchResultsTab(btn.dataset.tab);
            }
        };
    });

    renderRunSnapshot();
    checkCompletionBanner();

    if (
        contractDetailOpen &&
        Number.isInteger(currentTenantIndex) &&
        currentTenantIndex >= 0 &&
        currentTenantIndex < currentResults.tenants.length &&
        (activeTopTab === "findings" || activeTopTab === "docview" || activeTopTab === "audittrail" || activeTopTab === "coverage")
    ) {
        openContractDetail(currentTenantIndex);
    } else {
        switchTopTab(activeTopTab);
    }
}

// ── Left Nav Sidebar (039x) ──

function renderNavSidebar() {
    const container = $("#nav-sidebar-content");
    if (!container || !currentResults) return;
    container.innerHTML = "";

    const tenants = currentResults.tenants || [];
    const legendChecked = localStorage.getItem("cam_show_legend") === "1";
    const header = document.querySelector(".nav-sidebar-header");
    if (header) {
        const totalIssues = tenants.reduce((sum, tenant, tenantIdx) => {
            const provisions = (tenant.results && tenant.results.provisions) || [];
            const unresolved = getDeviationWorkflowProvisions(provisions, tenantIdx).filter((p) => {
                const key = `${tenantIdx}:${p.provision_id}`;
                const status = (resolutionState[key] || {}).status || "open";
                return status !== "resolved" && status !== "not_a_deviation";
            });
            return sum + unresolved.length;
        }, 0);
        header.innerHTML =
            '<div class="nav-sidebar-header-top">' +
                '<div class="nav-sidebar-header-main">Open Issues</div>' +
                '<label class="nav-legend-toggle"><input type="checkbox" id="nav-legend-checkbox"' + (legendChecked ? ' checked' : '') + '> Legend</label>' +
            '</div>' +
            '<div class="nav-sidebar-header-meta">' + esc(String(tenants.length)) + ' lease' + (tenants.length === 1 ? '' : 's') + ' \u2022 ' + esc(String(totalIssues)) + ' issue' + (totalIssues === 1 ? '' : 's') + '</div>'
    }

    // Collect all severity+signal combinations from unresolved issues
    const sevOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    const legendCombos = {};
    tenants.forEach((tenant, tenantIdx) => {
        const provisions = (tenant.results && tenant.results.provisions) || [];
        getDeviationWorkflowProvisions(provisions, tenantIdx).forEach((p) => {
            const key = `${tenantIdx}:${p.provision_id}`;
            const status = (resolutionState[key] || {}).status || "open";
            if (status === "resolved" || status === "not_a_deviation") return;
            let sev = (p.severity || "MEDIUM").toUpperCase();
            // Normalize invalid severity values (e.g. "REVIEW" from UNCLEAR verdicts)
            if (!sevOrder.hasOwnProperty(sev)) sev = "MEDIUM";
            const sig = p.cam_score ? p.cam_score.governance_signal : "";
            const comboKey = sev + ":" + sig;
            if (!legendCombos[comboKey]) {
                legendCombos[comboKey] = { severity: sev, signal: sig, count: 0 };
            }
            legendCombos[comboKey].count++;
        });
    });

    // Build and insert legend panel
    const legendPanel = document.getElementById("nav-legend-panel") || document.createElement("div");
    legendPanel.id = "nav-legend-panel";
    legendPanel.className = "nav-legend-panel" + (legendChecked ? "" : " hidden");
    const sortedCombos = Object.values(legendCombos).sort((a, b) => {
        const sd = (sevOrder[a.severity] ?? 99) - (sevOrder[b.severity] ?? 99);
        if (sd !== 0) return sd;
        const sigOrder = { ASSERT_SIGNAL: 0, ASSERT_REVIEW_SIGNAL: 1, REVIEW_SIGNAL: 2, WITHHOLD_SIGNAL: 3 };
        return (sigOrder[a.signal] ?? 99) - (sigOrder[b.signal] ?? 99);
    });
    const getBadge = window.CAMAuditShared.getConfidenceBadgeData || function() { return null; };
    const getLabel = window.CAMAuditShared.getSidebarConfidenceLabel || function() { return ""; };
    const getTooltip = window.CAMAuditShared.getCombinedTooltipText || function() { return ""; };
    legendPanel.innerHTML = sortedCombos.length === 0
        ? '<div class="nav-legend-empty">No open issues</div>'
        : sortedCombos.map(c => {
            const badge = getBadge(c.signal, c.severity);
            const dots = badge ? badge.dots : "";
            const confLabel = getLabel(c.signal);
            const meaning = getTooltip(c.severity, c.signal);
            const sevLow = c.severity.toLowerCase();
            return `<div class="nav-legend-entry">
                <div class="nav-legend-entry-header">
                    <span class="nav-issue-sev nav-issue-sev-${sevLow}">${esc(sevDisplay(c.severity))}</span>
                    <span class="nav-confidence-dots">${dots}</span>
                    <span class="nav-legend-conf-label">${esc(confLabel)}</span>
                    <span class="nav-legend-count">(${c.count})</span>
                </div>
                <div class="nav-legend-meaning">${esc(meaning)}</div>
            </div>`;
        }).join("");

    const headerEl = document.querySelector(".nav-sidebar-header");
    if (headerEl) {
        const existingPanel = document.getElementById("nav-legend-panel");
        if (existingPanel) {
            existingPanel.replaceWith(legendPanel);
        } else {
            headerEl.after(legendPanel);
        }
        const checkbox = document.getElementById("nav-legend-checkbox");
        if (checkbox) {
            checkbox.onchange = function() {
                legendPanel.classList.toggle("hidden", !this.checked);
                localStorage.setItem("cam_show_legend", this.checked ? "1" : "0");
            };
        }
    }

    // LP/CUSTOM/ADDED sort key
    const pidSortKey = function(pid) {
        const m = (pid || "").match(/^(LP|CUSTOM|ADDED)-(\d+)/i);
        if (!m) return [3, 999];
        const prefix = m[1].toUpperCase();
        const num = parseInt(m[2], 10);
        if (prefix === "LP")     return [0, num];
        if (prefix === "CUSTOM") return [1, num];
        return [2, num];
    };

    tenants.forEach((tenant, i) => {
        const tenantEl = document.createElement("div");
        tenantEl.className = "nav-tenant";
        tenantEl.setAttribute("data-tenant-index", String(i));

        // Deduplicate provisions
        const rawProvisions = (tenant.results && tenant.results.provisions) || [];
        const seenNavPids = new Set();
        const provisions = rawProvisions.filter(p => {
            const pid = p.provision_id || p.id;
            if (seenNavPids.has(pid)) return false;
            seenNavPids.add(pid);
            return true;
        });

        const tenantName = formatTenantName(tenant.filename) || ("Tenant " + (i + 1));
        const tenantStillProcessing = !tenant.results;
        const s121 = tenant.results && tenant.results.summary ? tenant.results.summary : null;
        const unresolvedDeviations = getDeviationWorkflowProvisions(provisions, i).filter(function(p) {
            const key = `${i}:${p.provision_id}`;
            const status = (resolutionState[key] || {}).status || "open";
            return status !== "resolved" && status !== "not_a_deviation";
        });
        const outstandingCount = unresolvedDeviations.length;

        // Resolution-aware status icon
        const resolution = getContractResolution(i);
        let statusIcon, statusCls;
        if (resolution === "clean")    { statusIcon = "\u2713"; statusCls = "nav-status-clean"; }
        else if (resolution === "resolved") { statusIcon = "\u2713"; statusCls = "nav-status-resolved"; }
        else                           { statusIcon = "\u26A0"; statusCls = "nav-status-unreviewed"; }

        // Overall status label — confidence-aware health label
        let navStatusLabel = '', navStatusClass = '';
        if (s121) {
            const _navDevs = getDeviationWorkflowProvisions(provisions, i);
            const _navCritical = _navDevs.filter(p => p.severity === "CRITICAL").length;
            const _navHigh = _navDevs.filter(p => p.severity === "HIGH").length;
            const _navFragile = _navDevs.filter(p => (p.cam_score || {}).governance_signal === "ASSERT_REVIEW_SIGNAL").length;
            const _navWithhold = _navDevs.filter(p => (p.cam_score || {}).governance_signal === "WITHHOLD_SIGNAL").length;

            if (_navCritical > 0) {
                navStatusLabel = 'Critical Issues Found'; navStatusClass = 'nav-status-critical';
            } else if (_navHigh >= 5 && _navFragile >= _navHigh * 0.6) {
                navStatusLabel = 'Complex Redline'; navStatusClass = 'nav-status-high';
            } else if (_navDevs.length > 0 && _navWithhold >= _navDevs.length * 0.5) {
                navStatusLabel = 'Uncertain'; navStatusClass = 'nav-status-high';
            } else if (_navHigh >= 3) {
                navStatusLabel = 'Significant Issues'; navStatusClass = 'nav-status-high';
            } else if (s121.deviates > 0) {
                navStatusLabel = 'Monitor'; navStatusClass = 'nav-status-medium';
            } else {
                navStatusLabel = 'Clear'; navStatusClass = 'nav-status-clear';
            }
        }

        // Tenant label
        const label = document.createElement("div");
        label.className = "nav-tenant-label";
        label.setAttribute("data-nav-tenant-index", String(i));

        const titleWrap = document.createElement("span");
        titleWrap.className = "nav-tenant-title-wrap";

        const statusIconEl = document.createElement("span");
        statusIconEl.className = "nav-tenant-status " + statusCls;
        statusIconEl.textContent = statusIcon;
        titleWrap.appendChild(statusIconEl);

        const titleTextEl = document.createElement("span");
        titleTextEl.className = "nav-tenant-title-text";
        titleTextEl.textContent = outstandingCount > 0 ? (tenantName + " (" + outstandingCount + ")") : tenantName;
        titleWrap.appendChild(titleTextEl);

        label.appendChild(titleWrap);

        if (navStatusLabel) {
            const headerStatusEl = document.createElement("span");
            headerStatusEl.className = "nav-tenant-header-status " + navStatusClass;
            headerStatusEl.textContent = navStatusLabel;
            label.appendChild(headerStatusEl);
        }

        label.onclick = function() { scrollToTenant(i); };
        tenantEl.appendChild(label);

        const sevMap = { 'nav-status-critical': 'sev-critical', 'nav-status-high': 'sev-high', 'nav-status-medium': 'sev-medium', 'nav-status-clear': 'sev-clear' };
        if (sevMap[navStatusClass]) tenantEl.classList.add(sevMap[navStatusClass]);
        if (tenantStillProcessing) {
            const procLabel = document.createElement('div');
            procLabel.className = 'nav-status-label nav-status-processing';
            procLabel.innerHTML = '<span class="spinner-inline"></span> Processing\u2026';
            tenantEl.appendChild(procLabel);
            tenantEl.classList.add('nav-tenant-processing');
        } else if (navStatusLabel) {
            const statusLabelEl = document.createElement('div');
            statusLabelEl.className = 'nav-status-label ' + navStatusClass;
            statusLabelEl.textContent = navStatusLabel;
            tenantEl.appendChild(statusLabelEl);
        }

        if (s121) {
            const countsRow = document.createElement('div');
            countsRow.className = 'nav-tenant-counts';
            const chips = [];
            if ((s121.critical || 0) > 0) chips.push('<span class="nav-count-chip critical">' + esc(String(s121.critical)) + ' critical</span>');
            if ((s121.high || 0) > 0) chips.push('<span class="nav-count-chip high">' + esc(String(s121.high)) + ' high</span>');
            if ((s121.medium || 0) > 0) chips.push('<span class="nav-count-chip medium">' + esc(String(s121.medium)) + ' medium</span>');
            if ((s121.low || 0) > 0) chips.push('<span class="nav-count-chip low">' + esc(String(s121.low)) + ' low</span>');
            countsRow.innerHTML = chips.join('');
            tenantEl.appendChild(countsRow);
        }

        // Coverage gap callout inside contract box
        const _covCa = (tenant.results && tenant.results.coverage_assessment) || [];
        const _covAttention = _covCa.filter(a =>
            a.partial_class === 'partial_material' ||
            a.coverage_state === 'covered_unfavorable' ||
            a.coverage_state === 'missing'
        ).length;
        const _covReview = _covCa.filter(a =>
            a.partial_class === 'partial_review'
        ).length;
        const _covCount = _covAttention + _covReview;
        if (_covCount > 0) {
            const covCallout = document.createElement('div');
            covCallout.className = 'nav-coverage-callout';
            covCallout.title = 'View Coverage & Gaps';
            const _covParts = [];
            if (_covAttention > 0) _covParts.push(_covAttention + ' need attention');
            if (_covReview > 0) _covParts.push(_covReview + ' worth reviewing');
            covCallout.textContent = '\u25D1 Coverage: ' + _covParts.join(', ');
            const _covTi = i;
            covCallout.onclick = function(e) {
                e.stopPropagation();
                // openContractDetail is internal; switchResultsTab is internal
                if (typeof openContractDetail === 'function') {
                    openContractDetail(_covTi);
                }
                setTimeout(function() {
                    if (typeof switchResultsTab === 'function') switchResultsTab('coverage');
                }, 200);
            };
            tenantEl.appendChild(covCallout);
        }

        // ── OPEN ISSUES section (deviations sorted by severity) ──────────────
        const deviations = unresolvedDeviations
            .sort((a, b) => {
                const sa = sevOrder[a.severity] !== undefined ? sevOrder[a.severity] : 99;
                const sb = sevOrder[b.severity] !== undefined ? sevOrder[b.severity] : 99;
                return sa - sb;
            });

        if (deviations.length > 0) {
            const issuesHeader = document.createElement("div");
            issuesHeader.className = "nav-section-header";
            issuesHeader.textContent = "Open Issues";
            tenantEl.appendChild(issuesHeader);

            const issuesList = document.createElement("div");
            issuesList.className = "nav-issues-list";
            deviations.forEach((p, idx) => {
                const pid = p.provision_id || "";
                const sev = (p.severity || "MEDIUM").toUpperCase();
                const sevLow = sev.toLowerCase();
                const isFocused = navSidebarFocusMap[i] ? navSidebarFocusMap[i] === pid : idx === 0;
                // Strip LP-XX prefix from provision name for display
                const cleanName = (p.provision_name || pid).replace(/^LP-\d{2}\s+/, "").replace(/^CUSTOM-\d+\s+/, "");
                const concern = getConformingConcernState(i, pid);

                const _navGovernanceSignal = p.cam_score ? p.cam_score.governance_signal : "";
                const _navBadge = getConfidenceBadgeData(_navGovernanceSignal, sev);
                const _sidebarLabel = window.CAMAuditShared.getSidebarConfidenceLabel
                    ? window.CAMAuditShared.getSidebarConfidenceLabel(_navGovernanceSignal)
                    : null;
                const _explanationText = window.CAMAuditShared.getSidebarExplanationText
                    ? window.CAMAuditShared.getSidebarExplanationText(p)
                    : "";

                // Build dots (keep for visual scanning)
                const _navDotsHtml = _navBadge
                    ? `<span class="nav-confidence-dots">${_navBadge.dots}</span>`
                    : "";

                // Build sidebar confidence label (plain English, no jargon)
                const _sidebarLabelHtml = _sidebarLabel
                    ? `<span class="nav-confidence-label nav-confidence-${(_navBadge || {}).cssClass || ''}">${esc(_sidebarLabel)}</span>`
                    : "";

                // Build explanation text
                const _explanationHtml = _explanationText
                    ? `<span class="nav-issue-explanation">${esc(_explanationText)}</span>`
                    : "";

                const item = document.createElement("div");
                item.className = "nav-issue-item nav-issue-" + sevLow
                    + ((sev === "CRITICAL" || sev === "HIGH") ? " nav-issue-priority" : "")
                    + (isFocused ? " nav-issue-topfocus" : "");
                item.innerHTML =
                    `<div class="nav-issue-main-row">` +
                    `<span class="nav-issue-signal">` +
                    `<span class="nav-issue-sev nav-issue-sev-${sevLow}">${esc(sevDisplay(sev))}</span>` +
                    _navDotsHtml +
                    `</span>` +
                    `<span class="nav-issue-name">${esc(cleanName)}</span>` +
                    `</div>` +
                    (_sidebarLabelHtml || _explanationHtml
                        ? `<div class="nav-issue-sub-row">${_sidebarLabelHtml}${_explanationHtml}</div>`
                        : "");
                const _combinedTooltip = window.CAMAuditShared.getCombinedTooltipText
                    ? window.CAMAuditShared.getCombinedTooltipText(sev, _navGovernanceSignal)
                    : "";
                item.title = _combinedTooltip || (pid + " \u2014 " + sev + (_sidebarLabel ? " \u2014 " + _sidebarLabel : ""));
                item.onclick = function() {
                    navSidebarFocusMap[i] = pid;
                    issuesList.querySelectorAll(".nav-issue-item").forEach(el => el.classList.remove("nav-issue-topfocus"));
                    item.classList.add("nav-issue-topfocus");
                    jumpToProvisionFromSidebar(pid, i);
                };
                issuesList.appendChild(item);
            });
            tenantEl.appendChild(issuesList);
        }

        // ── ALL PROVISIONS section (LP order) ────────────────────────────────
        const allProvsCount = provisions.filter(p => p.provision_id !== "LP-00").length;
        const allProvsDivider = document.createElement("div");
        allProvsDivider.className = "nav-section-header nav-section-header--all nav-section-toggle";
        allProvsDivider.innerHTML =
            `<span class="nav-section-toggle-label">Show All Clauses <span class="nav-all-count">(${allProvsCount})</span></span>` +
            `<span class="nav-toggle-chevron">&#9654;</span>`;
        allProvsDivider.onclick = function() {
            const isHidden = allProvsList.classList.contains("hidden");
            allProvsList.classList.toggle("hidden", !isHidden);
            allProvsDivider.querySelector(".nav-toggle-chevron").innerHTML = isHidden ? "&#9660;" : "&#9654;";
            const toggleLabel = allProvsDivider.querySelector(".nav-section-toggle-label");
            if (toggleLabel) {
                toggleLabel.innerHTML = `${isHidden ? "Hide Full Clause List" : "Show All Clauses"} <span class="nav-all-count">(${allProvsCount})</span>`;
            }
        };
        tenantEl.appendChild(allProvsDivider);

        const allProvsList = document.createElement("div");
        allProvsList.className = "nav-all-provisions hidden"; // collapsed by default

        const sorted = provisions
            .filter(p => p.provision_id !== "LP-00")
            .slice()
            .sort((a, b) => {
                const ka = pidSortKey(a.provision_id || "");
                const kb = pidSortKey(b.provision_id || "");
                return ka[0] - kb[0] || ka[1] - kb[1];
            });

        sorted.forEach(p => {
            const pid = p.provision_id || "";
            const verdict = p.final_verdict || "";
            const sev = (p.severity || "").toLowerCase();
            const cleanName = (p.provision_name || pid).replace(/^LP-\d{2}\s+/, "").replace(/^CUSTOM-\d+\s+/, "");
            const displayName = pid ? `${pid} ${cleanName}` : cleanName;
            const concern = getConformingConcernState(i, pid);
            const resolution = (resolutionState[`${i}:${pid}`] || {}).status || "open";
            const isResolved = resolution === "resolved";
            const isNotDeviation = resolution === "not_a_deviation";
            const isWorkflowDeviation = isDeviationWorkflowProvision(p, i);

            const item = document.createElement("div");
            item.className = "nav-all-item" + (isWorkflowDeviation ? " nav-all-deviates" : " nav-all-conforms") + ((isResolved || isNotDeviation) ? " nav-all-resolved" : "");

            let iconHtml;
            if (isResolved) {
                iconHtml = `<span class="nav-all-icon nav-all-resolved-icon">&#10003;</span>`;
            } else if (isNotDeviation) {
                iconHtml = `<span class="nav-all-icon nav-all-resolved-icon">&#10003;</span>`;
            } else if (isWorkflowDeviation) {
                iconHtml = `<span class="nav-dot ${esc(sev)}"></span>`;
            } else if (concern === "flag") {
                iconHtml = `<span class="nav-all-icon" style="color:#dc2626">&#9888;</span>`;
            } else if (concern === "concern") {
                iconHtml = `<span class="nav-all-icon" style="color:#d97706">&#128203;</span>`;
            } else {
                iconHtml = `<span class="nav-all-icon nav-all-check">&#10003;</span>`;
            }

            item.innerHTML = iconHtml +
                `<span class="nav-all-name">${esc(displayName)}</span>` +
                (isResolved ? `<span class="nav-all-resolved-label">Resolved</span>` : (isNotDeviation ? `<span class="nav-all-resolved-label">Not a Deviation</span>` : ""));
            item.title = pid;
            item.onclick = function() {
                jumpToProvisionFromSidebar(pid, i);
            };
            allProvsList.appendChild(item);
        });

        tenantEl.appendChild(allProvsList);
        container.appendChild(tenantEl);
    });

    updateNavActive(currentTenantIndex);
}

function getConformingConcernCompositeKey(tenantIdx, pid) {
    return `${tenantIdx}:${pid}`;
}

function getConformingConcernEntry(tenantIdx, pid) {
    const resEntry = resolutionState[`${tenantIdx}:${pid}`];
    if (resEntry && (resEntry.concern_state || resEntry.concern_reason)) {
        return {
            state: resEntry.concern_state || "none",
            reason: (resEntry.concern_reason || "").trim(),
        };
    }
    ensureConformingConcernsLoaded();
    return window._conformingConcerns[getConformingConcernCompositeKey(tenantIdx, pid)] || null;
}

function getConformingConcernStoreKey() {
    return currentJobId ? `cam:conforming-concerns:${currentJobId}` : "";
}

function ensureConformingConcernsLoaded() {
    if (window._conformingConcernsLoaded) return;
    window._conformingConcerns = {};
    const storeKey = getConformingConcernStoreKey();
    if (!storeKey) {
        window._conformingConcernsLoaded = true;
        return;
    }
    try {
        const raw = window.localStorage.getItem(storeKey);
        if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === "object") {
                window._conformingConcerns = parsed;
            }
        }
    } catch (err) {
        console.warn("Could not load conforming concern state", err);
    }
    window._conformingConcernsLoaded = true;
}

function persistConformingConcerns() {
    const storeKey = getConformingConcernStoreKey();
    if (!storeKey) return;
    try {
        window.localStorage.setItem(storeKey, JSON.stringify(window._conformingConcerns || {}));
    } catch (err) {
        console.warn("Could not persist conforming concern state", err);
    }
}

function getConformingConcernState(tenantIdx, pid) {
    const entry = getConformingConcernEntry(tenantIdx, pid);
    if (!entry) return "none";
    if (typeof entry === "string") return entry;
    return entry.state || "none";
}

function getConformingConcernReason(tenantIdx, pid) {
    const entry = getConformingConcernEntry(tenantIdx, pid);
    if (!entry || typeof entry === "string") return "";
    return (entry.reason || "").trim();
}

function setConformingConcernEntry(tenantIdx, pid, state, reason) {
    ensureConformingConcernsLoaded();
    const key = getConformingConcernCompositeKey(tenantIdx, pid);
    const resKey = `${tenantIdx}:${pid}`;
    if (!resolutionState[resKey]) resolutionState[resKey] = { status: "open", notes: [] };
    resolutionState[resKey].concern_state = state || "none";
    resolutionState[resKey].concern_reason = "";
    if (!state || state === "none") {
        window._conformingConcerns[key] = "none";
        persistConformingConcerns();
        return;
    }
    if (state === "concern") {
        window._conformingConcerns[key] = { state: "concern", reason: "" };
        persistConformingConcerns();
        return;
    }
    resolutionState[resKey].concern_reason = (reason || "").trim();
    window._conformingConcerns[key] = { state, reason: (reason || "").trim() };
    persistConformingConcerns();
}











function getDocviewDomIdSuffix(pid, tenantIdx) {
    return `${tenantIdx}-${String(pid || "").replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}

function getTenantData(tenantIdx = currentTenantIndex) {
    return currentResults && currentResults.tenants ? currentResults.tenants[tenantIdx] : null;
}

function getTenantResultsData(tenantIdx = currentTenantIndex) {
    const tenant = getTenantData(tenantIdx);
    return tenant && tenant.results ? tenant.results : null;
}

function getTenantRawProvisions(tenantIdx = currentTenantIndex) {
    const results = getTenantResultsData(tenantIdx);
    return (results && results.provisions) || [];
}

function getTenantWorkflowProvisions(tenantIdx = currentTenantIndex) {
    return getDocviewWorkflowProvisions(getTenantRawProvisions(tenantIdx), tenantIdx);
}

function getTenantDeviationWorkflowItems(tenantIdx = currentTenantIndex) {
    return getDeviationWorkflowProvisions(getTenantRawProvisions(tenantIdx), tenantIdx);
}











function ensureSummaryProvisionVisible(pid) {
    let targetCard = document.getElementById(`dev-${pid}`);
    if (targetCard) return targetCard;

    const conformingList = document.getElementById("conforming-list");
    const conformingToggle = document.getElementById("conforming-toggle");
    if (conformingList && conformingList.classList.contains("hidden")) {
        conformingList.classList.remove("hidden");
        if (conformingToggle) {
            conformingToggle.innerHTML = "&#9660; Conforming Provisions (no action needed)";
        }
    }

    const conformingItem = document.querySelector(`.conforming-item[data-pid="${CSS.escape(pid)}"]`);
    if (!conformingItem) return null;
    const detail = conformingItem.querySelector(".conforming-detail");
    const chevron = conformingItem.querySelector(".conforming-chevron");
    if (detail && detail.classList.contains("hidden")) {
        detail.classList.remove("hidden");
    }
    if (chevron) chevron.innerHTML = "&#9652;";
    return conformingItem;
}

function getProvisionWorkflowExportState(tenantIdx, pid) {
    const resKey = `${tenantIdx}:${pid}`;
    const entry = resolutionState[resKey] || {};
    return {
        status: entry.status || "open",
        notes: entry.notes || [],
        read: isNoted(tenantIdx, pid),
        concern_state: entry.concern_state || "none",
        concern_reason: entry.concern_reason || "",
    };
}

function getAuditExportComplexity(provision) {
    const fragility = provision && provision.fragility ? provision.fragility : {};
    const rawScore = fragility.fragility_score != null
        ? Number(fragility.fragility_score)
        : fragility.score != null
            ? Number(fragility.score)
            : null;
    if (rawScore == null || isNaN(rawScore)) {
        return { label: null, score_pct: null };
    }
    const pct = rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore);
    const label = pct < 15 ? "Simple"
        : pct < 35 ? "Moderate"
        : pct < 60 ? "Complex"
        : "Highly complex";
    return { label, score_pct: pct };
}

function serializeProvisionForAuditExport(p, tenantIdx) {
    const pid = p.provision_id || "";
    const workflow = getProvisionWorkflowExportState(tenantIdx, pid);
    const verdict = p.final_verdict || "";
    const evVerdicts = p.evaluator_verdicts || {};
    const evTotal = Object.keys(evVerdicts).length || 0;
    const evAgree = verdict === "DEVIATES"
        ? Object.values(evVerdicts).filter(v => v === "DEVIATES").length
        : verdict === "CONFORMS"
            ? Object.values(evVerdicts).filter(v => v === "CONFORMS").length
            : Object.values(evVerdicts).filter(v => v === "UNCLEAR").length;
    const agreementSummary = evTotal > 0
        ? `${evAgree}/${evTotal} reviewers ${verdict === "DEVIATES" ? "flagged this" : verdict === "CONFORMS" ? "confirmed" : "marked this unclear"}`
        : "";
    const confidenceBadge = getConfidenceBadgeData
        ? getConfidenceBadgeData((p.cam_score || {}).governance_signal || "", (p.severity || "").toUpperCase())
        : null;
    const complexity = getAuditExportComplexity(p);
    return {
        provision_id: pid,
        provision_name: p.provision_name,
        final_verdict: p.final_verdict,
        severity: p.severity,
        severity_floor_applied: p.severity_floor_applied,
        confidence_label: confidenceBadge ? confidenceBadge.label : null,
        confidence_dots: confidenceBadge ? confidenceBadge.dots : null,
        agreement_pattern: p.agreement_pattern,
        reviewer_agreement_summary: agreementSummary,
        evaluator_verdicts: p.evaluator_verdicts,
        evaluator_reasoning: p.evaluator_reasoning,
        evaluator_confidences: p.evaluator_confidences,
        challenge_finding: p.challenge_finding,
        challenge_details: p.challenge_details,
        fragility: p.fragility,
        complexity_label: complexity.label,
        complexity_score_pct: complexity.score_pct,
        cam_metadata: p.cam_metadata,
        cam_score: p.cam_score,
        risk_headline: p.risk_headline,
        severity_reasoning: p.severity_reasoning,
        financial_impact: p.financial_impact,
        recommended_action: p.recommended_action,
        template_text: p.template_text,
        tenant_text: p.tenant_text,
        template_section_ref: p.template_section_ref,
        tenant_section_ref: p.tenant_section_ref,
        manual_escalation: !!p.manual_escalation,
        workflow_status: workflow.status,
        read: workflow.read,
        notes: workflow.notes,
        concern_state: workflow.concern_state,
        concern_reason: workflow.concern_reason,
    };
}







async function scrollToTenant(index) {
    // Step 116: Navigate to contract detail via Contracts tab
    if (activeTopTab !== "contracts") {
        switchTopTab("contracts");
    }
    return await openContractDetail(index);
}

function refreshDocviewIfActive(tenantIdx) {
    if (activeResultsTab === "docview" && contractDetailOpen && tenantIdx === currentTenantIndex) {
        renderDocumentView();
    }
}

function openDocviewModify(tenantIdx, pid) {
    switchResultsTab("findings");
    const targetCard = document.getElementById(`dev-${pid}`);
    if (targetCard) {
        setTimeout(() => {
            targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
            targetCard.classList.add("highlight-flash");
            setTimeout(() => targetCard.classList.remove("highlight-flash"), 1500);
            finalDraftModify(tenantIdx, pid);
        }, 100);
    } else {
        finalDraftModify(tenantIdx, pid);
    }
}

function openDocviewSummary(tenantIdx, pid) {
    switchResultsTab("findings");
    waitForResultsTarget(() => ensureSummaryProvisionVisible(pid), { attempts: 16, delay: 90 }).then((targetCard) => {
        if (!targetCard) return;
        scrollResultsTargetIntoView(targetCard, 12);
        flashResultsTarget(targetCard, 1500);
    });
}





function updateDocviewResolutionNoteCount(pid, tenantIdx) {
    const key = `${tenantIdx}:${pid}`;
    const count = ((resolutionState[key] || {}).notes || []).length;
    const toggleBtn = document.querySelector(`.docview-resolution-bar .res-notes-toggle[data-pid="${pid}"][data-tenant-idx="${tenantIdx}"]`);
    if (!toggleBtn) return;
    toggleBtn.innerHTML = buildNotesToggleHtml("Notes", count);
}

function renderDocviewResolutionNotesPanel(pid, tenantIdx) {
    const suffix = getDocviewDomIdSuffix(pid, tenantIdx);
    const panel = document.getElementById(`docview-res-notes-${suffix}`);
    if (!panel) return;
    const key = `${tenantIdx}:${pid}`;
    const notes = ((resolutionState[key] || {}).notes || []);
    const inputRow = panel.querySelector(".res-note-input-row");
    renderNotesPanelEntries(panel, notes, inputRow, {
        esc,
        formatResTimestamp,
        buildDeleteButtonHtml: (noteIdx) => `<button class="res-note-delete" onclick="window.CAM.deleteDocviewResolutionNote('${esc(pid)}', ${tenantIdx}, ${noteIdx}); event.stopPropagation();">Delete</button>`,
    });
}

function toggleDocviewResolutionNotes(pid, tenantIdx) {
    const suffix = getDocviewDomIdSuffix(pid, tenantIdx);
    const panel = document.getElementById(`docview-res-notes-${suffix}`);
    if (!panel) return;
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) {
        const input = document.getElementById(`docview-res-input-${suffix}`);
        if (input) input.focus();
    }
}

async function saveDocviewResolutionNote(pid, tenantIdx) {
    const suffix = getDocviewDomIdSuffix(pid, tenantIdx);
    const input = document.getElementById(`docview-res-input-${suffix}`);
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    const saved = await addResolutionNote(pid, tenantIdx, text);
    if (saved) {
        input.value = "";
        renderDocviewResolutionNotesPanel(pid, tenantIdx);
        updateDocviewResolutionNoteCount(pid, tenantIdx);
    }
}

async function deleteDocviewResolutionNote(pid, tenantIdx, noteIdx) {
    const deleted = await deleteResolutionNote(pid, tenantIdx, noteIdx);
    if (deleted) {
        renderDocviewResolutionNotesPanel(pid, tenantIdx);
        updateDocviewResolutionNoteCount(pid, tenantIdx);
    }
}

async function persistConformingConcernState(pid, tenantIdx) {
    const key = `${tenantIdx}:${pid}`;
    const entry = resolutionState[key] || {};
    try {
        await fetch(`/api/jobs/${currentJobId}/resolution`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                tenant_idx: tenantIdx,
                provision_id: pid,
                concern_state: entry.concern_state || "none",
                concern_reason: entry.concern_reason || "",
            }),
        });
    } catch (err) {
        console.error("Conforming concern save failed", err);
    }
}

async function handleConformingConcernAction(pid, action) {
    const tenant = currentResults && currentResults.tenants ? currentResults.tenants[currentTenantIndex] : null;
    const provisions = (tenant && tenant.results && tenant.results.provisions) || [];
    const modelsUsed = (tenant && tenant.results && tenant.results.models_used) || {};
    const provision = provisions.find((entry) => entry.provision_id === pid);
    const current = getConformingConcernState(currentTenantIndex, pid);

    if (action === "clear") {
        setConformingConcernEntry(currentTenantIndex, pid, "none");
    } else if (action === current) {
        setConformingConcernEntry(currentTenantIndex, pid, "none");
    } else if (action === "flag") {
        const reason = window.prompt(
            "Optional reason for escalating this clause as a deviation:",
            getConformingConcernReason(currentTenantIndex, pid)
        );
        if (reason === null) return;
        setConformingConcernEntry(currentTenantIndex, pid, "flag", reason);
        if (confirm("Create a rule so this is flagged automatically next time?")) {
            window.CAM.showRuleCreationDialog(pid, (provision && provision.provision_name) || pid);
        }
    } else {
        setConformingConcernEntry(currentTenantIndex, pid, action);
    }

    await persistConformingConcernState(pid, currentTenantIndex);

    renderConforming(provisions, modelsUsed);
    renderDeviations(provisions, modelsUsed, currentTenantIndex, currentDiscoveries || {});
    renderNavSidebar();
    if (contractDetailOpen && currentTenantIndex >= 0) {
        renderContractClauseFilterBar(provisions);
    }
    updateFinalDraftBar();
    applyContractClauseFilters();
    refreshDocviewIfActive(currentTenantIndex);

    if (action === "flag") {
        setTimeout(() => jumpToFinding(pid), 50);
    }
}

function updateNavActive(index) {
    const detailView = document.getElementById("contract-detail-view");
    const shouldHighlight =
        contractDetailOpen &&
        detailView &&
        !detailView.classList.contains("hidden") &&
        (activeResultsTab === "findings" || activeResultsTab === "docview" || activeResultsTab === "audittrail");

    document.querySelectorAll(".nav-tenant").forEach(function(el) {
        el.classList.remove("active");
    });
    document.querySelectorAll(".nav-tenant-label").forEach(function(el) {
        el.classList.remove("active");
    });
    if (!shouldHighlight) return;
    const navCard = document.querySelector('.nav-sidebar .nav-tenant[data-tenant-index="' + index + '"]');
    if (navCard) navCard.classList.add("active");
    const navLabel = document.querySelector('.nav-sidebar .nav-tenant-label[data-nav-tenant-index="' + index + '"]');
    if (navLabel) navLabel.classList.add("active");
}

function fmtDuration(secs) {
    const s = Math.round(secs);
    if (s < 60) return s + "s";
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const rem = s % 60;
    if (h > 0) return `${h}h ${m}m ${rem}s`;
    return rem > 0 ? `${m}m ${rem}s` : `${m}m`;
}

function formatTenantName(filename) {
    if (!filename) return "Unknown";
    // Strip extension
    let name = filename.replace(/\.[^.]+$/, "");
    // Replace underscores/hyphens with spaces, format nicely
    // "T-04_subtle" → "T-04 (subtle)", "T-07_aggressive" → "T-07 (aggressive)"
    const match = name.match(/^(T-\d+)[_-](.+)$/i);
    if (match) return `${match[1]} (${match[2]})`;
    return name.replace(/[_-]/g, " ");
}

function renderDealOverview() {
    const panel = $("#deal-overview-panel");
    if (!panel) return;
    if (!currentResults || !currentResults.tenants || !currentResults.tenants.length) {
        panel.classList.add("hidden");
        return;
    }

    // Use first tenant's deal_overview (all tenants share the same lease template context)
    const firstResult = currentResults.tenants[0].results;
    if (!firstResult) {
        panel.classList.add("hidden");
        return;
    }

    const deal = firstResult.deal_overview || {};
    const meta = firstResult.contract_metadata || {};

    // Resolve fields: deal_overview preferred, fall back to contract_metadata
    const landlord = deal.landlord_name || (shouldShowField(meta.landlord) ? meta.landlord : "");
    const tenant = deal.tenant_name || (shouldShowField(meta.tenant) ? meta.tenant : "");
    const property = deal.property_address || (shouldShowField(meta.property_description) ? meta.property_description : "");
    const propertyType = deal.property_type || "";
    const leaseTermYears = deal.lease_term_years;
    const commencement = deal.commencement_date || (shouldShowField(meta.effective_date) ? meta.effective_date : "");
    const expiration = deal.expiration_date || (shouldShowField(meta.expiration_date) ? meta.expiration_date : "");
    const renewal = deal.renewal_options || "";
    const rent = deal.base_rent_monthly || (shouldShowField(meta.base_rent) ? meta.base_rent : "");
    const escalation = deal.escalation || "";
    const security = deal.security_deposit || "";
    const cam = deal.cam_structure || "";
    const use = deal.permitted_use || (shouldShowField(meta.permitted_use) ? meta.permitted_use : "");
    const govLaw = deal.governing_law || (shouldShowField(meta.governing_law) ? meta.governing_law : "");
    // Check if we have enough data to show the panel
    const hasData = landlord || tenant || property || rent || leaseTermYears;
    if (!hasData) {
        panel.classList.add("hidden");
        return;
    }

    // Build term string
    let termStr = "";
    if (leaseTermYears) {
        termStr = leaseTermYears + " year" + (leaseTermYears !== 1 ? "s" : "");
        if (commencement && expiration) termStr += ` (${esc(commencement)} \u2013 ${esc(expiration)})`;
        else if (commencement) termStr += ` (from ${esc(commencement)})`;
    } else if (shouldShowField(meta.term_length)) {
        termStr = meta.term_length;
        if (commencement) termStr += ` (from ${esc(commencement)})`;
    }

    // Build parties header
    let partiesHtml = "";
    if (landlord) partiesHtml += `<div class="deal-party">${esc(landlord)} <span class="deal-role">(Landlord)</span></div>`;
    if (tenant) partiesHtml += `<div class="deal-party">${esc(tenant)} <span class="deal-role">(Tenant)</span></div>`;

    // Property line
    let propertyHtml = "";
    if (property) {
        propertyHtml = `<div class="deal-property">${esc(property)}`;
        if (propertyType) propertyHtml += ` &mdash; ${esc(propertyType)}`;
        propertyHtml += `</div>`;
    }

    // Build deal grid rows (two-column layout for terms)
    const gridItems = [];
    if (termStr) gridItems.push(["Term", termStr]);
    if (rent) gridItems.push(["Rent", rent]);
    if (escalation) gridItems.push(["Escalation", escalation]);
    if (security) gridItems.push(["Security", security]);
    if (cam) gridItems.push(["CAM/OpEx", cam]);
    if (use) gridItems.push(["Use", use]);
    if (renewal) gridItems.push(["Renewal", renewal]);
    if (govLaw) gridItems.push(["Governing Law", govLaw]);

    let gridHtml = "";
    if (gridItems.length) {
        gridHtml = `<div class="deal-grid">`;
        gridItems.forEach(([label, value]) => {
            gridHtml += `<div class="deal-grid-item"><span class="deal-label">${esc(label)}</span><span class="deal-value">${esc(value)}</span></div>`;
        });
        gridHtml += `</div>`;
    }

    const analyzedProvisions = firstResult.provisions || [];
    const provCount = analyzedProvisions.length;

    const tenantFile = firstResult.tenant_file || "";
    const subtitleHtml = tenantFile
        ? `<div class="deal-overview-subtitle">${esc(tenantFile)}</div>`
        : "";
    panel.innerHTML = `<div class="deal-overview-card">
        <div class="deal-overview-header">BASE LEASE TERMS</div>
        ${subtitleHtml}
        ${partiesHtml}
        ${propertyHtml}
        ${gridHtml}
    </div>`;
    panel.classList.remove("hidden");
}

// ── AI Summary Bar (048) ──

async function renderAISummaryBar() {
    const bar = $("#ai-summary-bar");
    if (!bar || !currentResults || !currentResults.tenants) return;

    bar.classList.remove("hidden");

    // Step 258: Mode C analyzes a single document against an issue-area schema
    // — there is no template, so deviation-based summary copy doesn't apply.
    // Short-circuit to a coverage-oriented summary before the Mode A pipeline
    // runs (which would either render nothing or blow up on missing severity
    // counts in the Mode C results shape).
    if (isJobModeC()) {
        renderModeCAISummaryBar(bar);
        return;
    }

    // ── Stats line ──
    const tenants = currentResults.tenants;
    const firstResult = tenants[0]?.results || {};
    const provisionsPerTenant = firstResult.provisions?.length || 0;
    let totalDeviations = 0, totalCritical = 0, totalHigh = 0;
    let tenantsWithDeviations = 0;

    tenants.forEach(t => {
        const s = t.results?.summary;
        if (!s) return;
        totalDeviations += s.deviates || 0;
        totalCritical  += s.critical || 0;
        totalHigh      += s.high || 0;
        if (s.deviates > 0) tenantsWithDeviations++;
    });

    const statsEl = $("#ai-summary-stats");
    if (statsEl) {
        let stats = `${tenants.length} lease${tenants.length !== 1 ? "s" : ""} reviewed`;
        if (provisionsPerTenant) stats += ` \u00B7 ${provisionsPerTenant} provisions per lease`;
        if (totalCritical > 0) stats += ` \u00B7 ${totalCritical} critical finding${totalCritical !== 1 ? "s" : ""}`;
        else if (totalDeviations > 0) stats += ` \u00B7 ${totalDeviations} deviation${totalDeviations !== 1 ? "s" : ""}`;
        statsEl.textContent = stats;
    }

    // Step 297c.8: Mode A conflict pill
    const _modeA_conflicts = (tenants[0] && tenants[0].results && tenants[0].results.conflicts) || [];
    if (_modeA_conflicts.length > 0) {
        bar.insertAdjacentHTML("beforeend",
            `<span class="ai-summary-pill ai-summary-pill--conflict">${_modeA_conflicts.length} provision conflict${_modeA_conflicts.length === 1 ? "" : "s"}</span>`
        );
    }

    // ── AI paragraph ──
    const paraEl = $("#ai-summary-paragraph");
    if (!paraEl) return;

    // Check cache — don't regenerate if already done for this job
    if (currentResults._aiSummary) {
        paraEl.innerHTML = currentResults._aiSummary;
        return;
    }

    // Build compact context for the AI call
    const isSingle = tenants.length === 1;
    const summaryData = tenants.map(t => {
        const s = t.results?.summary || {};
        const deviations = (t.results?.provisions || [])
            .filter(p => p.final_verdict === "DEVIATES")
            .map(p => `${p.provision_id} ${p.provision_name || ""} (${p.severity || "MEDIUM"})`)
            .join(", ");
        // For single-lease runs, omit the tenant label so the AI doesn't name or count tenants
        const label = isSingle ? "" : `${formatTenantName(t.filename)}: `;
        return `${label}${s.deviates || 0} deviation${(s.deviates || 0) !== 1 ? "s" : ""} \u2014 ${deviations || "none"}`;
    }).join("\n");

    // Count clean vs deviating tenants for summary context (Step 116)
    const cleanCount = tenants.filter(t => {
        const s = t.results?.summary;
        return s && (s.deviates || 0) === 0;
    }).length;
    const cleanContext = cleanCount > 0 ? `\n\n${cleanCount} of ${tenants.length} leases conform fully to the standard template.` : "";

    // Step 183: Build CAM confidence context for AI summary
    let camContext = '';
    let hasUncertain = false;
    if (!isSingle) {
        let totalWithhold = 0;
        let totalReview = 0;
        let totalScored = 0;
        tenants.forEach(t => {
            const cs = t.results?.cam_contract_summary;
            if (cs) {
                totalWithhold += (cs.withhold_uncertain ?? (cs.governance_counts?.WITHHOLD_SIGNAL || 0));
                totalReview += (cs.governance_counts?.REVIEW_SIGNAL || 0);
                totalScored += ((cs.provisions_scored || 0) - (cs.withhold_no_baseline || 0));
            }
        });
        const uncertain = totalWithhold + totalReview;
        if (uncertain > 0 && totalScored > 0) {
            camContext = `\n\nNote: Across all leases, ${uncertain} of ${totalScored} total clause evaluations had lower AI confidence and may benefit from additional human review.`;
            hasUncertain = true;
        }
    } else {
        const t0 = tenants[0];
        const cs0 = t0?.results?.cam_contract_summary;
        if (cs0) {
            const withhold0 = cs0.withhold_uncertain ?? (cs0.governance_counts?.WITHHOLD_SIGNAL || 0);
            const review0 = cs0.governance_counts?.REVIEW_SIGNAL || 0;
            const noBaseline0 = cs0.withhold_no_baseline || 0;
            const uncertain0 = withhold0 + review0;  // excludes no-baseline withholds
            const total0 = (cs0.provisions_scored || 0) - noBaseline0;  // denominator excludes no-baseline
            const confident0 = cs0.governance_counts?.ASSERT_SIGNAL || 0;
            const ratio0 = total0 > 0 ? confident0 / total0 : 0;
            const tier0 = ratio0 >= 0.75 ? 'high' : ratio0 >= 0.50 ? 'moderate' : 'low';
            if (uncertain0 > 0) {
                camContext = `\n\nNote: AI confidence was ${tier0} overall. ${uncertain0} of ${total0} standard clause evaluations had lower confidence and may benefit from additional human review.`;
                hasUncertain = true;
            } else {
                camContext = `\n\nNote: AI confidence was ${tier0} overall across all ${total0} standard clauses evaluated.`;
            }
        }
    }
    const confidenceInstruction = hasUncertain
        ? (isSingle
            ? " If the note above mentions lower-confidence clauses, add a brief third sentence mentioning this."
            : " If the note above mentions lower-confidence clause evaluations, include a brief final sentence about this.")
        : "";

    const singleConforms = isSingle && cleanCount === 1;
    const prompt = isSingle
        ? `You are summarizing a single lease deviation analysis for a lawyer's review. Write 2-3 plain-English sentences about this one lease. ${
            singleConforms
              ? "State that the lease fully conforms to the standard template."
              : "State that the lease does not fully conform to the reference lease. Describe which types of provisions deviate and their severity."
          } Always refer to it as 'the standard template', never 'our template' or 'our standard template'. Do not use the words 'leases' or 'tenants'. Do not name or label the lease. Do not recommend signing, rejecting, or revising. Do not give legal advice. Do not use bullet points.${confidenceInstruction}${camContext}\n\nLease findings:\n${summaryData}`
        : `You are summarizing lease deviation analysis results for a lawyer's review. Write 2-3 plain-English sentences. Start by stating how many of the ${tenants.length} leases conform fully to the standard template (${cleanCount} do). Then identify which tenants have the most significant issues and what types of provisions are affected. Report what was found. Do not recommend signing, rejecting, or revising any lease. Do not give legal advice. Do not use bullet points. Do not mention AI or analysis pipelines.${confidenceInstruction}\n\nResults:\n${summaryData}${cleanContext}${camContext}`;

    try {
        const resp = await fetch("/api/ai-summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt, job_id: currentJobId }),
        });
        const data = await resp.json();
        const text = data.summary || "";
        if (text) {
            const escaped = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            paraEl.innerHTML = escaped;
            currentResults._aiSummary = escaped;
        } else {
            paraEl.innerHTML = `<span class="ai-summary-error">Summary unavailable.</span>`;
        }
    } catch (err) {
        console.error("AI summary error:", err);
        paraEl.innerHTML = `<span class="ai-summary-error">Summary unavailable.</span>`;
    }
}

function toggleTechDetails() {
    const content = $("#tech-details-content");
    const toggle = $("#tech-details-toggle");
    if (!content) return;
    const isHidden = content.classList.contains("hidden");
    content.classList.toggle("hidden", !isHidden);
    if (toggle) toggle.innerHTML = (isHidden ? "&#9660;" : "&#9658;") + " Technical Details";
    if (isHidden) renderTechDetails();
}

function downloadSynopsis() {
    if (currentJobId) downloadFile(`/api/jobs/${currentJobId}/summary`);
}

function exportJSON() {
    exportAllJSON();
}

function renderBatchMeta() {
    const el = $("#batch-meta");
    if (!currentResults || !currentResults.tenants) return;

    const tenants = currentResults.tenants;
    const firstResult = tenants.length > 0 && tenants[0].results ? tenants[0].results : {};
    const meta = firstResult.contract_metadata || {};

    // Portfolio header from template metadata
    const propertyName = shouldShowField(meta.property_description) ? meta.property_description : "";
    const landlordName = shouldShowField(meta.landlord) ? meta.landlord : "";

    // Headline: property name or generic
    const portfolioTitle = propertyName || "Lease Portfolio Review";
    const dateStr = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

    // Stats
    const totalTenants = tenants.length;
    const provisionsPerTenant = firstResult.provisions ? firstResult.provisions.length : 0;
    let tenantsWithDeviations = 0;
    let totalCritical = 0;
    let totalHigh = 0;
    tenants.forEach(t => {
        if (t.results && t.results.summary) {
            if (t.results.summary.deviates > 0) tenantsWithDeviations++;
            totalCritical += t.results.summary.critical || 0;
            totalHigh += t.results.summary.high || 0;
        }
    });

    let statsLine = `${totalTenants} tenant lease${totalTenants !== 1 ? "s" : ""} reviewed`;
    if (provisionsPerTenant) statsLine += ` \u00B7 ${provisionsPerTenant} provisions per lease`;

    let findingsLine = "";
    if (tenantsWithDeviations > 0) {
        findingsLine = `${tenantsWithDeviations} of ${totalTenants} tenant${totalTenants !== 1 ? "s" : ""} require review`;
        if (totalCritical > 0) findingsLine += ` \u00B7 ${totalCritical} critical finding${totalCritical !== 1 ? "s" : ""}`;
        else if (totalHigh > 0) findingsLine += ` \u00B7 ${totalHigh} high-severity finding${totalHigh !== 1 ? "s" : ""}`;
    } else {
        findingsLine = `\u2705 All ${totalTenants} tenants conform to reference lease`;
    }

    const sectionHeading = tenantsWithDeviations > 0 && tenantsWithDeviations === totalTenants
        ? "Leases with Significant Deviations"
        : "Lease Analysis Results";

    el.innerHTML = `<div class="batch-portfolio-header">
        <div class="batch-section-heading">${esc(sectionHeading)}</div>
        <div class="batch-portfolio-title">${esc(portfolioTitle)}</div>
        ${landlordName ? `<div class="batch-portfolio-sub">Landlord: ${esc(landlordName)}</div>` : ""}
        <div class="batch-portfolio-sub">${esc(dateStr)}</div>
        <div class="batch-portfolio-stats">${statsLine}</div>
        <div class="batch-portfolio-stats" style="font-weight:600;">${findingsLine}</div>
    </div>`;
}

function renderCrossTenantMatrix() {
    const container = $("#cross-tenant-matrix");
    if (!container) return;
    if (!currentResults || !currentResults.tenants || currentResults.tenants.length < 2) {
        container.classList.add("hidden");
        return;
    }

    const tenants = currentResults.tenants;

    // Aggregate: for each provision_id, collect which tenants have it as DEVIATES
    const issueMap = {};  // pid -> { pname, severity, tenants: [{index, filename}] }
    const cleanTenants = [];

    tenants.forEach((t, i) => {
        if (!t.results || !t.results.provisions) return;
        let hasDeviation = false;
        t.results.provisions.forEach(p => {
            if (p.final_verdict === "DEVIATES") {
                hasDeviation = true;
                const pid = p.provision_id;
                if (!issueMap[pid]) {
                    issueMap[pid] = {
                        pname: p.provision_name || pid,
                        severity: p.severity || "MEDIUM",
                        tenants: [],
                    };
                }
                // Use highest severity across tenants
                const existingSev = SEVERITY_ORDER.indexOf(issueMap[pid].severity);
                const thisSev = SEVERITY_ORDER.indexOf(p.severity || "MEDIUM");
                if (thisSev >= 0 && (existingSev < 0 || thisSev < existingSev)) {
                    issueMap[pid].severity = p.severity;
                }
                issueMap[pid].tenants.push({ index: i, filename: t.filename });
            }
        });
        if (!hasDeviation) cleanTenants.push({ index: i, filename: t.filename });
    });

    const issues = Object.entries(issueMap).map(([pid, info]) => ({ pid, ...info }));
    if (issues.length === 0 && cleanTenants.length === 0) {
        container.classList.add("hidden");
        return;
    }

    // Sort by severity
    issues.sort((a, b) => {
        const ai = SEVERITY_ORDER.indexOf(a.severity);
        const bi = SEVERITY_ORDER.indexOf(b.severity);
        return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    });

    const sevIcons = { CRITICAL: "\uD83D\uDD34", HIGH: "\uD83D\uDFE0", MEDIUM: "\uD83D\uDFE1", LOW: "\u2B1C" };

    let html = `<div class="card cross-tenant-card">
        <div class="card-header">Cross-Tenant Issue Matrix</div>`;

    issues.forEach(issue => {
        const icon = sevIcons[issue.severity] || "\u2B1C";
        const label = `${issue.pid} ${(issue.pname || "").replace(/^LP-\d{2}\s*/, "")}`;
        const chips = issue.tenants.map(t =>
            `<span class="xtenant-chip" data-tenant="${t.index}" data-pid="${esc(issue.pid)}">${esc(formatTenantName(t.filename))}</span>`
        ).join("");
        html += `<div class="xtenant-row xtenant-row-${issue.severity}" data-severity="${esc(issue.severity)}" data-tenants="${esc(JSON.stringify(issue.tenants.map(t => String(t.index))))}">
            <span class="xtenant-icon">${icon}</span>
            <span class="xtenant-issue">${esc(label)}</span>
            <div class="xtenant-chips">${chips}</div>
        </div>`;
    });

    if (cleanTenants.length > 0) {
        const cleanNames = cleanTenants.map(t => esc(formatTenantName(t.filename))).join(", ");
        html += `<div class="xtenant-row xtenant-row-CONFORMS">
            <span class="xtenant-icon">\uD83D\uDFE2</span>
            <span class="xtenant-issue">All provisions conform</span>
            <div class="xtenant-chips">${cleanNames}</div>
        </div>`;
    }

    html += `</div>`;
    container.innerHTML = html;
    container.classList.remove("hidden");

    // Wire up tenant chip clicks
    container.querySelectorAll(".xtenant-chip").forEach(chip => {
        chip.addEventListener("click", async () => {
        const tenantIdx = parseInt(chip.dataset.tenant, 10);
        const pid = chip.dataset.pid;
        switchTopTab("contracts");
            await openContractDetail(tenantIdx);
            jumpToFinding(pid);
        });
    });
}

// Step 374G: Needs Review subtype classifier — the SINGLE source for the subtype split shown by
// BOTH the Overview Action Summary (_computeRiskCounts.reviewSub) and the Key Issues sidebar
// sub-headers. Operates on the RAW finding (a coverage_assessment LP or a cross_provision_finding)
// so both surfaces classify identically — never re-derive from typeLabel (374G-Q: typeLabel is a
// different signal that can drift on the unclassifiable-fallthrough edge). Only meaningful for a
// finding classifyFindingType() routes to 'review_needed'.
//   'possible_one_sided'  — synthesis finding (directional_mismatch) routed to review (unverified).
//   'conflicting_reading' — coverage LP floored to review by the Step 373C hard_flag (a disputed
//                           critical element preventing a clean assertion; state !== 'review_needed').
//   'coverage_question'   — coverage LP with no verdict (coverage_state === 'review_needed').
// Step 374Q (PROVISIONAL relabel-only containment — pending calibration across more contracts):
// derive DISPLAY-ONLY provenance flags for an LP-level coverage finding, mirroring the 374P
// recompute (build_log/_374p_recompute.py) EXACTLY — same RANK, pessimistic/optimistic plurality
// rollup with tie-break, and severity bands. Two flags:
//   tieDerivedSevere   — the "severe" LP-level disagreement is an ARTIFACT of the pessimistic
//                        tie-break (production severity is severe but the SAME verdicts rolled
//                        optimistically are NOT severe). Per 374P: the disagreement only looks
//                        severe because a tie broke pessimistically — not a supported conflict.
//   consequenceDefaulted — the consequence was DEFAULTED (use_impact absent) or not assessed
//                        (materiality empty), i.e. NOT an assessed consequence (374P Stage-5e gap).
// These change NO count, routing, bucket, hard_flag, escalation, or how confidence is computed.
// They ONLY decide which truthful Needs-Review subtype label a finding carries and whether the
// unsupported "conflicting reading" / "confidence capped at low" executive wording is withheld.
var _CAM_VERDICT_RANK_374Q = {
    explicitly_present: 0, implicitly_present: 1,
    covered_in_other_lp: 2, covered_in_other_LP: 2, covered_by_default_law: 2,
    unclear: 3, missing: 5
};
function _camRoll374Q(elems, pess) {
    if (!elems || !elems.length) return { verdict: 'unclear', tie: false };
    var counts = {};
    elems.forEach(function(v) { counts[v] = (counts[v] || 0) + 1; });
    var mx = 0;
    Object.keys(counts).forEach(function(k) { if (counts[k] > mx) mx = counts[k]; });
    var cand = Object.keys(counts).filter(function(k) { return counts[k] === mx; });
    if (cand.length <= 1) return { verdict: cand[0], tie: false };
    var best = cand[0];
    var br = (_CAM_VERDICT_RANK_374Q[best] !== undefined) ? _CAM_VERDICT_RANK_374Q[best] : 3;
    for (var i = 1; i < cand.length; i++) {
        var r = (_CAM_VERDICT_RANK_374Q[cand[i]] !== undefined) ? _CAM_VERDICT_RANK_374Q[cand[i]] : 3;
        if ((pess && r > br) || (!pess && r < br)) { best = cand[i]; br = r; }
    }
    return { verdict: best, tie: true };
}
function _camSeverity374Q(vs) {
    var md = 0;
    for (var i = 0; i < vs.length; i++) {
        for (var j = i + 1; j < vs.length; j++) {
            var a = _CAM_VERDICT_RANK_374Q[vs[i]], b = _CAM_VERDICT_RANK_374Q[vs[j]];
            if (a === undefined || b === undefined) continue;
            var d = Math.abs(a - b);
            if (d > md) md = d;
        }
    }
    return md >= 4 ? 'severe' : md >= 2 ? 'moderate' : md >= 1 ? 'minor' : 'none';
}
function _lpProvenanceFlags374Q(finding) {
    var out = { tieDerivedSevere: false, consequenceDefaulted: false };
    if (!finding) return out;
    var byRole = {};
    (finding.element_verdicts || []).forEach(function(e) {
        (e.evaluator_verdicts || []).forEach(function(ev) {
            var role = (ev && ev.role != null) ? ev.role : null;
            if (role === null) return;
            (byRole[role] = byRole[role] || []).push(ev.verdict);
        });
    });
    var roles = Object.keys(byRole);
    if (roles.length) {
        var prodList = [], optList = [], anyTie = false;
        roles.forEach(function(role) {
            var p = _camRoll374Q(byRole[role], true);
            var o = _camRoll374Q(byRole[role], false);
            prodList.push(p.verdict); optList.push(o.verdict);
            if (p.tie) anyTie = true;
        });
        out.tieDerivedSevere = anyTie
            && _camSeverity374Q(prodList) === 'severe'
            && _camSeverity374Q(optList) !== 'severe';
    }
    var ui = finding.use_impact;
    if (ui === null || ui === undefined) out.consequenceDefaulted = true;
    else { var mat = ui.materiality; if (mat === null || mat === undefined || mat === '') out.consequenceDefaulted = true; }
    return out;
}
function _reviewSubtypeOf(finding) {
    if (!finding) return 'coverage_question';
    if (finding.finding_type) return 'possible_one_sided'; // synthesis (cross_provision_findings)
    var state = finding.coverage_state || '';
    var rpds  = finding.review_priority_distance_signal;
    if (rpds && rpds.hard_flag === true && state !== 'review_needed') {
        // Step 374Q: the finding STAYS in Needs Review (bucket/count untouched) — but withhold the
        // "conflicting reading" executive characterization when its basis is a tie-break artifact
        // and/or a defaulted consequence (374P provenance), routing it to its TRUTHFUL subtype:
        //   defaulted consequence  → 'consequence_not_assessed' (transparent, no implied assessment)
        //   tie-derived (assessed) → 'coverage_question' (real coverage basis, not a supported conflict)
        // Only a genuine, non-artifactual disagreement keeps 'conflicting_reading' (e.g. LP-02/LP-20).
        var _pf = _lpProvenanceFlags374Q(finding);
        if (_pf.consequenceDefaulted) return 'consequence_not_assessed';
        if (_pf.tieDerivedSevere)     return 'coverage_question';
        return 'conflicting_reading';
    }
    return 'coverage_question';
}

// Step 366: compute risk sub-bucket counts for a single tenant's results,
// using the same classification logic as the sidebar. Returns:
//   { gaps: N, crossClause: N, directional: N, otherRisks: N, total: N }
// Step 373F: "Risks to Act On" total = COUNT OF EVERY FINDING classifyFindingType() ROUTES TO 'risk'.
// The classifier is the authoritative source of truth for bucket membership. The subtype
// breakdown (Coverage Gaps / Cross-Clause / One-Sided Terms) is DISPLAY-ONLY and must never
// define the total. Any Risk-routed finding not matching a displayed subtype falls into
// "Other Risks" so it can never be silently dropped from the headline.
//
// This re-runs the SAME bucket-first routing the sidebar uses in renderUnifiedKeyIssues
// (classifyFindingType over coverage_assessment + cross_provision_findings, same govSig
// derivation), so `total` here equals the sidebar's local risk[].length by construction.
// The sidebar's risk[] is a render-local not exported, so we replicate the routing rule here;
// this MUST stay in sync with the sidebar routing (app.js ~18039-18090). Scope: Mode-C
// coverage + synthesis only — Mode-A deviation Risk items are NOT counted here (separate
// unmeasured path, tracked as a 373F follow-up; do not fold in).
function _computeRiskCounts(r, perspective) {
    if (!r) return { gaps: 0, crossClause: 0, directional: 0, otherRisks: 0, priorityReview: 0, total: 0,
                     coverage: { risk: 0, review_needed: 0, improvement: 0, addressed: 0, na: 0 },
                     action: { risk: 0, reviewNeeded: 0, improvement: 0, addressed: 0 },
                     reviewSub: { unresolvedCoverage: 0, disputedProtection: 0, unverifiedOneSided: 0, consequenceNotAssessed: 0 } };
    var caByLp = {};
    (r.coverage_assessment || []).forEach(function(a) {
        caByLp[a.issue_area_id || a.provision_id] = a;
    });
    var riskTotal = 0; // direct count of classifyFindingType()==='risk' — the authoritative total
    var gaps = 0, crossClause = 0, directional = 0, priorityReview = 0;
    // Step 373G: full 5-bucket coverage tally for THIS tenant, so the Coverage-by-Issue-Area
    // panel pills and the headline read from ONE per-tenant computation (single source — they
    // cannot desync). `coverage.risk` IS `gaps` (same loop iteration). The panel pills consume
    // _riskCounts.coverage in renderModeCAISummaryBar — keep these in sync; do not reintroduce a
    // separate panel-side loop over coverage_assessment.
    var coverage = { risk: 0, review_needed: 0, improvement: 0, addressed: 0, na: 0 };
    // Step 374: findings-first ACTION buckets + Needs Review subtypes, the single source for BOTH
    // the Overview Action Summary AND the sidebar bucket counts. This replicates the exact routing
    // the sidebar (renderNavSidebar ~18049-18256) uses to build its risk[]/reviewNeeded[]/
    // improvement[]/addressed[] arrays — MUST stay in sync with that routing. reviewNeeded /
    // improvement count coverage + synthesis findings (not 1-per-LP); addressed is the suppressed
    // residual computed after the loops (see suppression comment below).
    var reviewNeeded = 0, improvement = 0;
    var unresolvedCoverage = 0, disputedProtection = 0, unverifiedOneSided = 0, consequenceNotAssessed = 0;
    var lpWithIssues = {};         // issue-area ids implicated in a Risk/Needs Review/Improvement finding
    var coverageAddressedIds = []; // coverage LPs routed to 'addressed' (Addressed action = coverage-only, per sidebar)
    function _markImplicated(pidStr) {
        String(pidStr || '').split(/[\s,]+/).forEach(function(s) { s = s.trim(); if (s) lpWithIssues[s] = true; });
    }
    (r.coverage_assessment || []).forEach(function(a) {
        var state = a.coverage_state || '';
        var lpId  = a.issue_area_id || a.provision_id || '';
        if (state === 'not_applicable') { coverage.na++; return; }
        var bucket = classifyFindingType(a, 'c', { perspective: perspective });
        if (bucket === 'risk') coverage.risk++;
        else if (bucket === 'review_needed') coverage.review_needed++;
        else if (bucket === 'improvement') coverage.improvement++;
        else coverage.addressed++;
        if (bucket === 'risk') {
            riskTotal++;
            gaps++;
            _markImplicated(lpId);
            // Step 373: same isPriorityReview rule the sidebar uses — within-Risk triage.
            if (isPriorityReview(a)) priorityReview++;
        } else if (bucket === 'review_needed') {
            reviewNeeded++;
            _markImplicated(lpId);
            // Step 374G: subtype from the shared classifier _reviewSubtypeOf (single source with the
            // sidebar sub-headers). Coverage LPs yield 'conflicting_reading' (hard_flag-floored,
            // 374-Q B2) or 'coverage_question' (no-verdict review_needed state).
            var _sub = _reviewSubtypeOf(a);
            if (_sub === 'conflicting_reading') disputedProtection++;
            else if (_sub === 'possible_one_sided') unverifiedOneSided++;
            else if (_sub === 'consequence_not_assessed') consequenceNotAssessed++; // Step 374Q: defaulted-consequence subtype (total unchanged)
            else unresolvedCoverage++;
        } else if (bucket === 'improvement') {
            improvement++;
            _markImplicated(lpId);
        } else {
            coverageAddressedIds.push(lpId);
        }
    });
    (r.cross_provision_findings || []).forEach(function(f) {
        var govSig = f.finding_type === 'compound_risk' ? deriveCompoundGovernanceSignal(f, caByLp)
                   : f.finding_type === 'directional_mismatch' ? deriveDirectionalGovernanceSignal(f) : null;
        var fi = { _item_type: 'synthesis', finding_type: f.finding_type,
                   severity: f.severity, directionality: f.directionality || '',
                   p2pp_routing: f.p2pp_routing || null }; // Step 376h: P2'' pre-computed bucket
        var bucket = classifyFindingType(fi, 'c', { perspective: perspective, govSig: govSig });
        var implicated = (f.implicated_lps || []).join(', ');
        if (bucket !== 'risk') {
            // Step 374: synthesis findings also populate the Needs Review / Improvement action buckets.
            if (bucket === 'review_needed') {
                reviewNeeded++;
                // Step 374G: subtype from the shared classifier (single source with the sidebar).
                // A synthesis finding routed to review is 'possible_one_sided' (directional, unverified).
                var _sub = _reviewSubtypeOf(f);
                if (_sub === 'possible_one_sided') unverifiedOneSided++;
                else if (_sub === 'conflicting_reading') disputedProtection++;
                else unresolvedCoverage++;
                _markImplicated(implicated);
            } else if (bucket === 'improvement') {
                improvement++;
                _markImplicated(implicated);
            }
            // synthesis 'addressed' (favorable directional / relief) does NOT create an Addressed
            // action count — the sidebar Addressed chips are coverage-only.
            return;
        }
        // Step 373F: count the Risk-routed finding FIRST (authoritative), then sub-classify
        // for display. A finding_type other than compound/directional (e.g. a HIGH
        // cross_coverage_gap) stays in the total via riskTotal and surfaces as Other Risks.
        riskTotal++;
        _markImplicated(implicated);
        var typeLabel = f.finding_type === 'compound_risk' ? 'COMPOUND'
                      : f.finding_type === 'directional_mismatch' ? 'DIRECTIONAL' : '';
        if (typeLabel === 'COMPOUND') crossClause++;
        else if (typeLabel === 'DIRECTIONAL') directional++;
        // Step 373: same rule again on the synthesis side (severity === HIGH).
        if (isPriorityReview(f)) priorityReview++;
    });
    // Step 373F: Other Risks = Risk-bucket findings not matched by a displayed subtype.
    // Self-consistency invariant: gaps + crossClause + directional + otherRisks === total.
    var otherRisks = riskTotal - (gaps + crossClause + directional);
    if (otherRisks < 0) {
        // A subtype counted something not in the Risk bucket — logic error, surface it (no silent clamp).
        console.warn('[CAM _computeRiskCounts] otherRisks negative — subtype overcount vs Risk bucket:',
            { total: riskTotal, gaps: gaps, crossClause: crossClause, directional: directional });
    }
    // Addressed (action layer) = an issue area is counted Addressed ONLY when it has NO associated
    // Risk, Needs Review, or Improvement finding. A coverage-positive LP implicated in another open
    // finding (e.g. LP-05: favorably covered but implicated in Dir-05 + CRX-05 Risk) is NOT counted as
    // Addressed — "Addressed" means no action, and you cannot tell the lawyer "no action" about a
    // provision you are also flagging in a Risk. Raw positive coverage evidence is preserved in the
    // coverage/evidence layer; it does not create an Addressed action count when another finding acts
    // on the same issue area. Matches the sidebar's existing suppression: Addressed = 1, not raw 2.
    var _seen = {}, addressedAction = 0;
    coverageAddressedIds.forEach(function(id) {
        if (!id || _seen[id] || lpWithIssues[id]) return;
        _seen[id] = true;
        addressedAction++;
    });
    return { gaps: gaps, crossClause: crossClause, directional: directional,
             otherRisks: otherRisks, priorityReview: priorityReview, total: riskTotal,
             coverage: coverage,
             // Step 374: findings-first action-bucket counts (== sidebar arrays by construction).
             action: { risk: riskTotal, reviewNeeded: reviewNeeded, improvement: improvement, addressed: addressedAction },
             reviewSub: { unresolvedCoverage: unresolvedCoverage, disputedProtection: disputedProtection,
                          unverifiedOneSided: unverifiedOneSided, consequenceNotAssessed: consequenceNotAssessed } };
}

// Step 374E: canonical Risk-bucket gloss — ONE shared string read by BOTH the Overview
// Action Summary (renderModeCAISummaryBar) and the Key Issues sidebar (renderNavSidebar),
// so the two surfaces cannot drift (374D had two separate inline strings). States the
// substantive status + the lawyer action without repeating the subtype line; does not say
// "confirmed" (doctrine: action-type, not a confidence tier).
const CAM_RISK_GLOSS = "Identified exposure — protective action recommended.";

// Step 258: Mode C variant of the AI Summary bar. Aggregates coverage_assessment
// across all tenants in the job and renders a four-bucket pill row that mirrors
// the Coverage & Gaps tab's framing (covered / need attention / worth reviewing /
// not applicable). Synchronous — no model call — because all data is already on
// currentResults; the Mode A version makes an LLM call which is overkill here.
function renderModeCAISummaryBar(bar) {
    if (!bar) return;
    const tenants = (currentResults && currentResults.tenants) || [];

    const _snapPerspective = getJobPerspective();

    // Step 374: the Overview is the ACTION SUMMARY — findings-first, current-contract scope. All
    // four action buckets AND the sidebar bucket counts derive from ONE per-tenant computation
    // (_computeRiskCounts) so they cannot desync (373F/373G single-source lesson). The raw per-LP
    // coverage-state census moved off the Overview (still inspectable in Coverage & Gaps / heatmap /
    // evidence); the Overview must not render it (avoids the two-ontologies-one-screen trust problem).
    const _riskTenant = tenants[currentTenantIndex] || tenants[0];
    const _riskCounts = _computeRiskCounts(_riskTenant && _riskTenant.results, _snapPerspective);
    const _action = _riskCounts.action || { risk: 0, reviewNeeded: 0, improvement: 0, addressed: 0 };
    const _reviewSub = _riskCounts.reviewSub || { unresolvedCoverage: 0, disputedProtection: 0, unverifiedOneSided: 0, consequenceNotAssessed: 0 };
    const docCount = tenants.length;

    // The Action Summary presents lawyer-facing ACTION ITEMS. It is NOT a partition of the 32 assessed
    // issue areas and must not be compared numerically to raw coverage-state totals. Risk and Needs
    // Review include synthesized/directional findings (not 1-per-LP); Addressed is a residual no-action
    // count after suppression. Do not render these four numbers as "32 split four ways."

    // Step 297c.2 / Step 374: conflicts + governing law scoped to the SELECTED contract (was job-wide,
    // which showed the first contract's law and a cross-document conflict sum — false on a mixed-law /
    // mixed-conflict multi-doc job; 374-Q flagged). Current-contract only, same scope as the buckets.
    const _mc_STATE_FULL_NAMES = {"NY": "New York", "CA": "California", "TX": "Texas", "FL": "Florida", "IL": "Illinois"};
    const _selRes = (_riskTenant && _riskTenant.results) || null;
    const _mcConflicts = (_selRes && _selRes.conflicts) || [];
    const _mcGovLaw = (_selRes && _selRes.jurisdiction && _selRes.jurisdiction.governing_law) || null;
    const _mcGovLawDisplay = _mcGovLaw ? (_mc_STATE_FULL_NAMES[_mcGovLaw] || _mcGovLaw) : null;
    const _mcConflictPill = _mcConflicts.length > 0
        ? `<span class="ai-summary-pill ai-summary-pill--conflict">${_mcConflicts.length} provision conflict${_mcConflicts.length === 1 ? "" : "s"}</span>`
        : "";
    const _mcGovBadge = _mcGovLawDisplay
        ? `<span class="ai-summary-modec-meta" style="margin-left:0.5rem;">Governed by ${esc(_mcGovLawDisplay)}</span>`
        : "";

    // RISK subtype line (display-only; total stays the authoritative 'risk' count — 373F).
    const _riskParts = [];
    if (_riskCounts.gaps > 0)        _riskParts.push(_riskCounts.gaps + (_riskCounts.gaps === 1 ? ' coverage gap' : ' coverage gaps'));
    if (_riskCounts.crossClause > 0) _riskParts.push(_riskCounts.crossClause + ' cross-clause risk' + (_riskCounts.crossClause === 1 ? '' : 's'));
    if (_riskCounts.directional > 0) _riskParts.push(_riskCounts.directional + ' one-sided term' + (_riskCounts.directional === 1 ? '' : 's'));
    if (_riskCounts.otherRisks > 0)  _riskParts.push(_riskCounts.otherRisks + ' Other Risks'); // 373F: never silently dropped
    const _riskDetailLine = _riskParts.join(' · ');

    // NEEDS REVIEW subtype line — THREE genuine subtypes (374-Q B2); sums to the Needs Review total.
    // Step 374C: lawyer-facing wording + order (coverage · one-sided · conflicting). Internal
    // governance vocabulary (unresolved/unverified/disputed) stays in Evidence/Audit, not the
    // executive surface. COUNTS are unchanged (same 374-Q computation): unresolvedCoverage →
    // "coverage questions", unverifiedOneSided → "possible one-sided terms", disputedProtection →
    // "conflicting reading" (the disagreement signal named only where it is true — do not generalize).
    const _reviewParts = [];
    if (_reviewSub.unresolvedCoverage > 0) _reviewParts.push(_reviewSub.unresolvedCoverage + ' coverage question' + (_reviewSub.unresolvedCoverage === 1 ? '' : 's'));
    // Step 374Q: defaulted/unassessed-consequence findings surface as "consequence not assessed" — a
    // transparent line, not an implied assessed consequence and not an unsupported "conflicting reading".
    if (_reviewSub.consequenceNotAssessed > 0) _reviewParts.push(_reviewSub.consequenceNotAssessed + ' consequence not assessed');
    if (_reviewSub.unverifiedOneSided > 0) _reviewParts.push(_reviewSub.unverifiedOneSided + ' possible one-sided term' + (_reviewSub.unverifiedOneSided === 1 ? '' : 's'));
    if (_reviewSub.disputedProtection > 0) _reviewParts.push(_reviewSub.disputedProtection + ' conflicting reading' + (_reviewSub.disputedProtection === 1 ? '' : 's'));
    const _reviewDetailLine = _reviewParts.join(' · ');

    // Step 374: "Priority Risks" (NOT "Priority Review" — that label collides with the Needs Review
    // bucket). Display string only; isPriorityReview LOGIC is unchanged.
    const _priorityRisksHtml = (_riskCounts.priorityReview > 0)
        ? `<span class="overview-priority-review" title="CAM flags these Risk items for first-pass review (coverage hard_flag + Stage 7 HIGH)">&#9888; ${_riskCounts.priorityReview} Priority Risks</span>`
        : '';

    bar.innerHTML = `
        <div class="ai-summary-modec action-summary">
            <div class="action-summary-head">
                <strong>Action Summary</strong>
                ${getPerspectiveIndicatorHtml()}
                ${_mcGovBadge}
                ${_mcConflictPill}
            </div>

            <div class="action-bucket action-bucket--risk">
                <div class="action-bucket-top">
                    <span class="action-bucket-label">Risk</span>
                    <span class="action-bucket-count">${_action.risk}</span>
                    ${_priorityRisksHtml}
                </div>
                ${_riskDetailLine ? `<div class="action-bucket-sub">${esc(_riskDetailLine)}</div>` : ''}
                <div class="action-bucket-gloss">${CAM_RISK_GLOSS}</div>
            </div>

            <div class="action-bucket action-bucket--review">
                <div class="action-bucket-top">
                    <span class="action-bucket-label">Needs Review</span>
                    <span class="action-bucket-count">${_action.reviewNeeded}</span>
                </div>
                ${_reviewDetailLine ? `<div class="action-bucket-sub">${esc(_reviewDetailLine)}</div>` : ''}
                <div class="action-bucket-gloss">Potential exposure: protections may be incomplete or missing, terms may be one-sided, or readings may conflict. Attorney review recommended.</div>
            </div>

            <div class="action-bucket action-bucket--improvement">
                <div class="action-bucket-top">
                    <span class="action-bucket-label">Improvement</span>
                    <span class="action-bucket-count">${_action.improvement}</span>
                </div>
                <div class="action-bucket-gloss">Protection exists — could be tightened.</div>
            </div>

            <div class="action-bucket action-bucket--addressed">
                <div class="action-bucket-top">
                    <span class="action-bucket-label">Addressed</span>
                    <span class="action-bucket-count">${_action.addressed}</span>
                </div>
                <div class="action-bucket-gloss" title="Counted Addressed only when an issue area has no associated Risk, Needs Review, or Improvement finding. Coverage-positive provisions implicated in an open finding are shown in that finding, not here.">No action recommended.</div>
            </div>

            ${docCount > 1 ? `<div class="ai-summary-modec-combined-note">Showing the selected contract only — ${docCount} contracts in this job. Switch contracts to view each one&rsquo;s action summary.</div>` : ''}
            <div class="ai-summary-modec-cta">Open <strong>Coverage &amp; Gaps</strong> for the full per-issue coverage map.</div>
        </div>
    `;
}

// ── Step 299: Provision Health Heatmap ──
// One horizontal row of 32 colored cells per tenant. Color encodes coverage
// state relative to the viewer's perspective (same rule as Step 297d.J).
// Clicking a cell calls jumpToCoverageProvision to navigate to that LP.

const _HEATMAP_LP_IDS = [
    "LP-01","LP-02","LP-03","LP-04","LP-05","LP-06","LP-07","LP-08",
    "LP-09","LP-10","LP-11","LP-12","LP-13","LP-14","LP-15","LP-16",
    "LP-17","LP-18","LP-19","LP-20","LP-21","LP-22","LP-23","LP-24",
    "LP-25","LP-26","LP-27","LP-28","LP-29","LP-30","LP-31","LP-32",
];

// Step 375M: normalizeUseConsequence — single read-side normalizer for all use_impact consumers.
// New artifacts write use_consequence with values {beneficial, neutral, harmful, context_dependent}.
// Old artifacts (pre-375M) write gap_impact with values {favorable, neutral, adverse, context_dependent}.
// This function prefers use_consequence and maps legacy gap_impact so every consumer works on both.
function normalizeUseConsequence(ui) {
    if (!ui) return null;
    if (ui.use_consequence !== undefined && ui.use_consequence !== null) return ui.use_consequence;
    // Legacy: map gap_impact vocabulary to new vocabulary
    var legacy = ui.gap_impact;
    if (legacy === 'favorable') return 'beneficial';
    if (legacy === 'adverse')   return 'harmful';
    return legacy || null;  // neutral, context_dependent unchanged; absent → null
}

// Step 338: derive risk level from LP assessment + cross_provision_findings.
// Pure function — no DOM access, no side effects.
// Rule ladder: first match wins. coverage_state is ONE input, not the output.
function deriveProvisionRiskLevel(lp, crossProvisionFindings, perspective) {
    const lpId  = lp.issue_area_id || lp.provision_id || "";
    const state = lp.coverage_state || "";
    const cpfs  = (crossProvisionFindings || []).filter(function(f) {
        return (f.implicated_lps || []).indexOf(lpId) !== -1;
    });

    function isAdverse(directionality) {
        if (!directionality || !perspective || perspective === 'neutral') return false;
        const adverseTo = directionality === 'tenant_unprotected' ? 'tenant' : 'landlord';
        return perspective === adverseTo;
    }

    // GRAY — not applicable
    if (state === 'not_applicable') {
        return { lp_id: lpId, risk_level: 'gray', dominant_reason: 'Not applicable' };
    }

    // Step 341b: check use_impact BEFORE compound override.
    // Compound override: HIGH compound risk always supersedes a beneficial use_consequence.
    const ui = lp.use_impact || null;
    const _uc = normalizeUseConsequence(ui);
    const hasHighCompound = cpfs.some(function(f) {
        return f.finding_type === 'compound_risk' && (f.severity || '').toUpperCase() === 'HIGH';
    });
    if (ui && !hasHighCompound) {
        if (_uc === 'beneficial') {
            return { lp_id: lpId, risk_level: 'green', dominant_reason: 'Beneficial absence — ' + (ui.use_reasoning || '') };
        }
        if (_uc === 'neutral' && ui.materiality === 'low') {
            return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Low impact for this tenant — ' + (ui.use_reasoning || '') };
        }
        if (ui.materiality === 'not_applicable') {
            return { lp_id: lpId, risk_level: 'gray', dominant_reason: 'Not relevant to this tenant\'s use' };
        }
    }

    // RED — missing material LP
    if (state === 'missing') {
        return { lp_id: lpId, risk_level: 'red', dominant_reason: 'Missing provision' };
    }

    // RED — HIGH compound risk (regardless of coverage_state)
    const highCpf = cpfs.find(function(f) {
        return f.finding_type === 'compound_risk' && (f.severity || '').toUpperCase() === 'HIGH';
    });
    if (highCpf) {
        return { lp_id: lpId, risk_level: 'red', dominant_reason: 'HIGH compound risk' };
    }

    // RED — 3-0 adverse directional mismatch
    const dir3_0 = cpfs.find(function(f) {
        return f.finding_type === 'directional_mismatch' &&
               f.evaluator_agreement === '3-0' && isAdverse(f.directionality);
    });
    if (dir3_0) {
        return { lp_id: lpId, risk_level: 'red', dominant_reason: '3-0 adverse directional mismatch' };
    }

    // RED — covered_unfavorable adverse to current perspective (with no severity on LP object,
    // treat as RED when directly adverse to viewer)
    if ((state === 'covered_unfavorable' || state === 'potentially_unenforceable') &&
        perspective && lp.covered_unfavorable_adverse_to &&
        lp.covered_unfavorable_adverse_to === perspective) {
        return { lp_id: lpId, risk_level: 'red', dominant_reason: 'Adverse coverage at viewer perspective' };
    }

    // Step 345: review_needed — Stage 5e result overrides when available
    if (state === 'review_needed') {
        const ui = lp.use_impact;
        const _uc2 = normalizeUseConsequence(ui);
        if (ui && ui.confidence !== 'no_evaluators') {
            if (_uc2 === 'harmful' && ui.materiality === 'high')
                return { lp_id: lpId, risk_level: 'red', dominant_reason: 'Review needed — harmful high-materiality gap' };
            if (_uc2 === 'harmful' && ui.materiality === 'medium')
                return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Review needed — harmful medium-materiality gap' };
            if (_uc2 === 'harmful' && ui.materiality === 'low')
                return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Review needed — harmful low-materiality gap' };
            if (_uc2 === 'beneficial' || _uc2 === 'neutral')
                return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Review needed — beneficial or neutral gap' };
        }
    }

    // RED — review_needed with significant missing evidence (>=50% elements missing)
    if (state === 'review_needed') {
        const evs = lp.element_verdicts || [];
        const missingCount = evs.filter(function(ev) { return ev.verdict === 'missing'; }).length;
        if (evs.length > 0 && missingCount / evs.length >= 0.5) {
            return { lp_id: lpId, risk_level: 'red', dominant_reason: 'Review needed — insufficient evidence' };
        }
    }

    // AMBER — partial with material element gaps
    if (state === 'partial' && lp.partial_class === 'partial_material') {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Partial — material gaps' };
    }

    // AMBER — MEDIUM compound risk
    const medCpf = cpfs.find(function(f) {
        return f.finding_type === 'compound_risk' && (f.severity || '').toUpperCase() === 'MEDIUM';
    });
    if (medCpf) {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'MEDIUM compound risk' };
    }

    // AMBER — 2-1 adverse directional mismatch
    const dir2_1 = cpfs.find(function(f) {
        return f.finding_type === 'directional_mismatch' &&
               f.evaluator_agreement === '2-1' && isAdverse(f.directionality);
    });
    if (dir2_1) {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: '2-1 adverse directional mismatch' };
    }

    // AMBER — covered_unfavorable (any remaining case)
    if (state === 'covered_unfavorable' || state === 'potentially_unenforceable') {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Adverse coverage terms' };
    }

    // AMBER — review_needed (general)
    if (state === 'review_needed') {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Review needed' };
    }

    // AMBER — cross_coverage_relief (structural dependency)
    const relief = cpfs.find(function(f) { return f.finding_type === 'cross_coverage_relief'; });
    if (relief) {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Coverage depends on another provision' };
    }

    // AMBER — partial (general, not already classified)
    if (state === 'partial') {
        return { lp_id: lpId, risk_level: 'amber', dominant_reason: 'Partial coverage' };
    }

    // GREEN — covered with no adverse signals
    return { lp_id: lpId, risk_level: 'green', dominant_reason: 'Addressed' };
}

// Step 338: map risk_level to cell colors.
function _riskLevelStyle(riskLevel) {
    if (riskLevel === 'red')   return { bg: '#dc2626', fg: '#fff', label: 'High Risk' };
    if (riskLevel === 'amber') return { bg: '#f59e0b', fg: '#78350f', label: 'Review Needed' };
    if (riskLevel === 'green') return { bg: '#22c55e', fg: '#fff', label: 'Addressed' };
    return { bg: '#9ca3af', fg: '#fff', label: 'Not Applicable' };  // gray
}

// Retained for Coverage & Gaps tab compatibility — other renderers still use coverage_state colors.
function _heatmapCellStyle(a, viewerPerspective) {
    const state = a.coverage_state;
    const pcls  = a.partial_class;
    const isFav = state === "covered_unfavorable" &&
        viewerPerspective && viewerPerspective !== "neutral" &&
        a.covered_unfavorable_adverse_to &&
        a.covered_unfavorable_adverse_to !== viewerPerspective;

    const isNeutralViewer = !viewerPerspective || viewerPerspective === "neutral";
    if (state === "potentially_unenforceable") return { bg: "#dc2626", fg: "#fff", label: "Enforceability" };
    if (isFav)                                 return { bg: "#16a34a", fg: "#fff", label: "Favorable" };
    if (state === "covered_unfavorable")       return isNeutralViewer
        ? { bg: "#f9a8d4", fg: "#9d174d", label: "Asymmetric" }
        : { bg: "#fca5a5", fg: "#7f1d1d", label: "Unfavorable" };
    if (state === "missing")                   return { bg: "#f97316", fg: "#fff", label: "Missing" };
    if (pcls  === "partial_material")          return { bg: "#fbbf24", fg: "#78350f", label: "Partial – Needs Attention" };
    if (pcls  === "partial_review")            return { bg: "#fef08a", fg: "#713f12", label: "Worth Reviewing" };
    if (state === "covered")                return { bg: "#22c55e", fg: "#fff",     label: "Covered" };
    if (pcls  === "partial_typical")        return { bg: "#e5e7eb", fg: "#374151", label: "Adequate" };
    if (state === "not_applicable")            return { bg: "#9ca3af", fg: "#fff", label: "Not Applicable" };
    return { bg: "#d1d5db", fg: "#6b7280", label: state || "—" };
}

// Step 337: return the correct directional arrow HTML entity for a heatmap badge.
// ← (&#x2190;) = adverse to viewer, → (&#x2192;) = favorable, ↔ (&#x2194;) = neutral/unknown.
function _dirArrow(directionality, perspective) {
    if (!directionality || !perspective || perspective === 'neutral') return '&#x2194;';
    const adverseTo = directionality === 'tenant_unprotected' ? 'tenant' : 'landlord';
    return perspective === adverseTo ? '&#x2190;' : '&#x2192;';
}

function renderProvisionHeatmap() {
    const panel = $("#provision-heatmap-panel");
    if (!panel) return;

    const tenants = (currentResults && currentResults.tenants) || [];
    const viewerPerspective = getJobPerspective();

    // Filter to tenants that have a coverage_assessment
    const rows = tenants.filter(t => t && t.results && (t.results.coverage_assessment || []).length > 0);
    if (rows.length === 0) {
        panel.classList.add("hidden");
        return;
    }

    // Step 338: RISK MAP header + legend
    let html = '<div class="provision-heatmap-section"><div class="provision-heatmap-section-header">RISK MAP</div>';

    // Use tenants (not rows) to preserve the original tenant index for navigation.
    tenants.forEach(function(tenant, tIdx) {
        if (!tenant || !tenant.results || !(tenant.results.coverage_assessment || []).length) return;
        const ca = tenant.results.coverage_assessment || [];
        const cpfs = tenant.results.cross_provision_findings || [];
        const filename = tenant.results.tenant_file || tenant.filename || "";

        // Build pid → assessment lookup
        const map = {};
        ca.forEach(function(a) { map[a.issue_area_id] = a; });

        // Step 337: build directional mismatch index: LP id → {desc, directionality}
        const dirMap = {};
        cpfs.forEach(function(f) {
            if (f.finding_type !== 'directional_mismatch') return;
            (f.implicated_lps || []).forEach(function(lpId) {
                if (!dirMap[lpId]) dirMap[lpId] = {
                    desc: f.headline || f.detail || "Directional mismatch",
                    directionality: f.directionality || null,
                };
            });
        });

        const labelHtml = filename
            ? `<div class="provision-heatmap-label">${esc(filename)}</div>`
            : "";

        const cellsHtml = _HEATMAP_LP_IDS.map(function(pid) {
            const a = map[pid];
            const dirInfo = dirMap[pid];
            const dirBadge = dirInfo
                ? `<span class="heatmap-dir-badge">${_dirArrow(dirInfo.directionality, viewerPerspective)}</span>`
                : "";

            if (!a) {
                // LP not in assessment — show as gray (no data)
                const cellTip = dirInfo ? esc(dirInfo.desc) : esc(pid);
                return `<div class="provision-heatmap-cell" style="background:#d1d5db;color:#9ca3af;position:relative;" title="${cellTip}">${pid.replace("LP-","")}${dirBadge}</div>`;
            }

            // Step 338: derive risk level from findings, not coverage_state alone
            const risk = deriveProvisionRiskLevel(a, cpfs, viewerPerspective);
            const s    = _riskLevelStyle(risk.risk_level);
            const name = a.issue_area_name || pid;
            const stateLabel = (a.coverage_state || "").replace(/_/g, ' ');
            // Tooltip: risk signal first, then coverage state for context
            const riskTip = risk.risk_level.toUpperCase() + ': ' + risk.dominant_reason;
            const covTip  = pid + ' — ' + name + ' — ' + stateLabel;
            const cellTip = dirInfo
                ? esc(dirInfo.desc + ' | ' + riskTip)
                : esc(riskTip + ' | ' + covTip);
            const num = pid.replace("LP-","");
            return `<div class="provision-heatmap-cell" style="background:${s.bg};color:${s.fg};position:relative;" title="${cellTip}" onclick="window.CAM.jumpHeatmapCell(${tIdx},'${esc(pid)}')">${num}${dirBadge}</div>`;
        }).join("");

        html += `<div class="provision-heatmap-contract">${labelHtml}<div class="provision-heatmap-row">${cellsHtml}</div></div>`;
    });

    // Step 338: legend
    html += '<div class="provision-heatmap-legend">'
          +   '<span class="hm-legend-item"><span class="hm-legend-dot" style="background:#dc2626"></span>High risk</span>'
          +   '<span class="hm-legend-item"><span class="hm-legend-dot" style="background:#f59e0b"></span>Review needed</span>'
          +   '<span class="hm-legend-item"><span class="hm-legend-dot" style="background:#22c55e"></span>Addressed</span>'
          +   '<span class="hm-legend-item"><span class="hm-legend-dot" style="background:#9ca3af"></span>N/A</span>'
          + '</div>'
          + '<div class="provision-heatmap-legend-note">Risk reflects adverse findings, missing protections, and compound interactions. Coverage state is one input.</div>';
    html += "</div>";
    panel.innerHTML = html;
    panel.classList.remove("hidden");
}

// ── Step 132: Deal Brief Banner on Analysis Overview ──
function renderDealBrief() {
    var banner = document.getElementById('deal-brief-banner');
    if (!banner || !currentResults || !currentResults.tenants) return;

    var tenants = currentResults.tenants;
    var firstResult = tenants[0] && tenants[0].results ? tenants[0].results : null;
    if (!firstResult) { banner.classList.add('hidden'); return; }

    // ── Line 1: Deal identity ──
    var deal = firstResult.deal_overview || {};
    var meta = firstResult.contract_metadata || {};
    var landlord = deal.landlord_name || meta.landlord || '';
    var property = deal.property_address || meta.property_description || '';
    var leaseType = deal.lease_type || deal.property_type || '';
    var termYears = deal.lease_term_years;
    var termStr = '';
    if (termYears) {
        termStr = termYears + ' year' + (termYears !== 1 ? 's' : '');
    } else if (meta.term_length) {
        termStr = meta.term_length;
    }

    var identityParts = [landlord, property, leaseType, termStr].filter(function(v) { return v; });
    var line1Html = '';
    if (identityParts.length > 0) {
        line1Html = '<div class="deal-brief-identity">' + identityParts.map(function(v) { return esc(String(v)); }).join(' \u00B7 ') + '</div>';
    }

    // ── Compute deviations, highest severity, top flag across all tenants ──
    var SEV_RANK = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'CONFORMS': 0 };
    var totalDeviations = 0;
    var highestSev = 'CONFORMS';
    var highestRank = 0;
    var topFlag = null; // { name, headline }

    tenants.forEach(function(t) {
        var provisions = t.results && t.results.provisions ? t.results.provisions : [];
        provisions.forEach(function(p) {
            if (!p.provision_id || p.provision_id === 'LP-00') return;
            if (p.final_verdict !== 'CONFORMS') {
                totalDeviations++;
                var sev = p.severity || 'LOW';
                var rank = SEV_RANK[sev] !== undefined ? SEV_RANK[sev] : 0;
                if (rank > highestRank) {
                    highestRank = rank;
                    highestSev = sev;
                    var headline = p.risk_headline || p.challenge_details || p.what_changed || '';
                    if (headline.length > 80) headline = headline.substring(0, 77) + '...';
                    topFlag = { name: p.provision_name || p.provision_id, headline: headline };
                } else if (rank === highestRank && !topFlag) {
                    var hl = p.risk_headline || p.challenge_details || p.what_changed || '';
                    if (hl.length > 80) hl = hl.substring(0, 77) + '...';
                    topFlag = { name: p.provision_name || p.provision_id, headline: hl };
                }
            }
        });
    });

    // ── Line 2: Verdict ──
    var tenantCount = tenants.length;
    var line2Html = '';
    if (totalDeviations === 0) {
        line2Html = '<div class="deal-brief-verdict" style="color: var(--success, #15803d);">'
            + esc(tenantCount + ' lease' + (tenantCount !== 1 ? 's' : '') + ' reviewed')
            + ' \u00B7 All provisions conform to reference lease</div>';
    } else {
        var sevClass = highestSev === 'CRITICAL' ? 'color: var(--danger, #dc2626);'
            : highestSev === 'HIGH' ? 'color: #c2410c;'
            : highestSev === 'MEDIUM' ? 'color: var(--warning, #d97706);'
            : 'color: var(--info, #64748b);';
        line2Html = '<div class="deal-brief-verdict">'
            + esc(tenantCount + ' lease' + (tenantCount !== 1 ? 's' : '') + ' reviewed')
            + ' \u00B7 ' + esc(totalDeviations + ' deviation' + (totalDeviations !== 1 ? 's' : '') + ' found')
            + ' \u00B7 Highest: <span style="' + sevClass + '">' + esc(highestSev) + '</span>'
            + '</div>';
    }

    // ── Line 3: Top flag ──
    var line3Html = '';
    if (totalDeviations > 0 && topFlag) {
        line3Html = '<div class="deal-brief-topflag"><strong>Top flag:</strong> ' + esc(topFlag.name);
        if (topFlag.headline) {
            line3Html += ' \u2014 ' + esc(topFlag.headline);
        }
        line3Html += '</div>';
    }

    banner.innerHTML = line1Html + line2Html + line3Html;
    banner.classList.remove('hidden');
    // Show the "Run Summary" section heading
    var summaryHeading = document.getElementById('run-summary-heading');
    if (summaryHeading) summaryHeading.classList.remove('hidden');
}

// ── Step 131: Provisions Scope Card on Analysis Overview ──
function renderProvisionsScopeCard() {
    var container = document.getElementById('provisions-scope-card');
    if (!container || !currentResults || !currentResults.tenants) return;

    var tenants = currentResults.tenants;

    // ── Build worst-severity map across all tenants ──
    var SEV_RANK = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'CONFORMS': 0 };
    var worstMap = {}; // provision_id → { severity, name }

    tenants.forEach(function(t) {
        var provisions = t.results && t.results.provisions ? t.results.provisions : [];
        provisions.forEach(function(p) {
            var pid = p.provision_id;
            if (!pid || pid === 'LP-00') return; // skip identity provision
            var sev = p.severity || 'CONFORMS';
            var rank = SEV_RANK[sev] !== undefined ? SEV_RANK[sev] : 0;
            if (!worstMap[pid] || rank > SEV_RANK[worstMap[pid].severity]) {
                worstMap[pid] = {
                    severity: sev,
                    name: p.provision_name || pid
                };
            }
        });
    });

    if (Object.keys(worstMap).length === 0) {
        container.classList.add('hidden');
        return;
    }

    // ── Sort provision IDs: LP-xx numerically, then CUSTOM-xx, then ADDED-xx ──
    var pidSortKey = function(pid) {
        var m = (pid || '').match(/^(LP|CUSTOM|ADDED)-(\d+)/i);
        if (!m) return [2, 999];
        var prefix = m[1].toUpperCase();
        var num = parseInt(m[2], 10);
        if (prefix === 'LP') return [0, num];
        if (prefix === 'CUSTOM') return [1, num];
        return [2, num];
    };

    var sortedIds = Object.keys(worstMap).sort(function(a, b) {
        var ka = pidSortKey(a), kb = pidSortKey(b);
        return ka[0] - kb[0] || ka[1] - kb[1];
    });

    // ── Build pill HTML ──
    var chips = sortedIds.map(function(pid) {
        var entry = worstMap[pid];
        var sev = entry.severity;
        var fullName = entry.name || '';
        // Strip "LP-XX " prefix from display name
        var shortName = fullName.replace(/^LP-\d{2}\s*/, '').replace(/^CUSTOM-\d+\s*/, '');
        var label = pid + ' ' + shortName;
        var sevClass = sev === 'CONFORMS' ? 'conforms' : sev.toLowerCase();
        return '<span class="pscope-pill pscope-pill-' + sevClass + '" title="' + esc(fullName) + '">'
            + esc(label) + '</span>';
    }).join('');

    // ── Non-standard scan tag ──
    var scanRan = false;
    var scanFoundCount = 0;
    tenants.forEach(function(t) {
        var disc = t.results && t.results.discoveries;
        if (disc && typeof disc === 'object' && Object.keys(disc).length > 0) {
            scanRan = true;
            var standalone = disc.standalone || [];
            scanFoundCount += standalone.length;
        }
    });

    var scanTag = '';
    if (scanRan) {
        if (scanFoundCount === 0) {
            scanTag = '<span class="pscope-scan-tag pscope-scan-clean">+ Non-standard clause scan \u2713</span>';
        } else {
            scanTag = '<span class="pscope-scan-tag pscope-scan-found">+ Non-standard clause scan \u00B7 ' + scanFoundCount + ' found</span>';
        }
    }

    container.innerHTML = '<div class="pscope-header">PROVISIONS ANALYZED</div>'
        + '<div class="pscope-pills">' + chips + scanTag + '</div>';
    container.classList.remove('hidden');
}

function renderContractStatusPanel() {
    const panel = $("#contract-status-panel");
    if (!panel || !currentResults || !currentResults.tenants) return;

    const tenants = currentResults.tenants;
    const firstResult = currentResults.tenants[0] && currentResults.tenants[0].results;
    const provCount = firstResult && firstResult.provisions ? firstResult.provisions.length : 0;

    // Build sortable list with severity scoring
    const cards = tenants.map((t, i) => {
        const s = t.results && t.results.summary ? t.results.summary : null;
        const provisions = t.results && t.results.provisions ? t.results.provisions : [];
        const deviations = provisions
            .filter(p => p.final_verdict === "DEVIATES")
            .sort((a, b) => {
                const ai = SEVERITY_ORDER.indexOf(a.severity);
                const bi = SEVERITY_ORDER.indexOf(b.severity);
                return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
            });
        const highestSev = s ? getHighestSeverity(s) : null;
        const sevScore = highestSev ? (SEVERITY_ORDER.indexOf(highestSev) + 1 || 99) : 99;
        return { t, i, s, deviations, highestSev, sevScore };
    });

    // Sort: worst severity first, then clean contracts
    cards.sort((a, b) => a.sevScore - b.sevScore);

    let html = `<div class="findings-panel-header">
        <div class="findings-panel-subtitle">Reference lease &mdash; deviations from these terms are flagged below</div>
        ${provCount > 0 ? `<div class="findings-panel-provcount">${provCount} provision${provCount !== 1 ? "s" : ""} analyzed</div>` : ""}
    </div>`;
    cards.forEach(({ t, i, s, deviations, highestSev }) => {
        const name = esc(formatTenantName(t.filename || ""));
        const isActive = i === currentTenantIndex;

        if (!s) {
            // No results (cancelled/error)
            const msg = t.status === "cancelled" ? "Cancelled" : (t.error && t.error.startsWith("GATE_ABORT:") ? "Not a commercial lease" : (t.error || "No results"));
            html += `<div class="contract-card contract-card-empty ${isActive ? "contract-card-active" : ""}"
                         data-tenant="${i}">
                <div class="contract-card-header">
                    <span class="contract-card-name">${name}</span>
                    <span class="contract-card-status status-empty">${esc(msg)}</span>
                </div>
            </div>`;
            return;
        }

        // Status badge — use contract health label with confidence awareness
        let statusLabel, statusClass;
        const _healthProvs = deviations;
        const _healthCritical = _healthProvs.filter(p => p.severity === "CRITICAL").length;
        const _healthHigh = _healthProvs.filter(p => p.severity === "HIGH").length;
        const _healthFragile = _healthProvs.filter(p => (p.cam_score || {}).governance_signal === "ASSERT_REVIEW_SIGNAL").length;
        const _healthWithhold = _healthProvs.filter(p => (p.cam_score || {}).governance_signal === "WITHHOLD_SIGNAL").length;

        if (_healthCritical > 0) {
            statusLabel = "\u26A0 Critical Issues Found"; statusClass = "status-critical";
        } else if (_healthHigh >= 5 && _healthFragile >= _healthHigh * 0.6) {
            statusLabel = "\u26A0 Complex Redline \u2014 Structured Review Required"; statusClass = "status-high";
        } else if (_healthProvs.length > 0 && _healthWithhold >= _healthProvs.length * 0.5) {
            statusLabel = "\u26A0 Uncertain \u2014 Attorney Review Required"; statusClass = "status-high";
        } else if (_healthHigh >= 3) {
            statusLabel = "\u26A0 Significant Issues \u2014 Review Recommended"; statusClass = "status-high";
        } else if (s.deviates > 0) {
            statusLabel = "\u00B7 Monitor"; statusClass = "status-medium";
        } else {
            statusLabel = "\u2713 Clear"; statusClass = "status-clear";
        }

        // Step 119: Build tenant/property subtitle line
        const meta = t.results && t.results.contract_metadata ? t.results.contract_metadata : {};
        const tenantStr = (meta.tenant_name || '').trim() || 'N/A';
        const propertyStr = (meta.property_description || '').trim() || 'N/A';
        const metaLine = `<div class="contract-card-meta">
            <span class="contract-meta-item">Tenant: ${esc(tenantStr)}</span>
            <span class="contract-meta-sep">&middot;</span>
            <span class="contract-meta-item">Property: ${esc(propertyStr)}</span>
        </div>`;

        // Step 125: Lease blurb
        const blurb125 = buildLeaseBlurb(t.results);
        const blurbLine = blurb125 ? `<div class="contract-card-blurb">${esc(blurb125)}</div>` : '';

        html += `<div class="contract-card ${isActive ? "contract-card-active" : ""}"
                     data-tenant="${i}" data-severity="${esc(highestSev || "")}">
            <div class="contract-card-header">
                <span class="contract-card-name">${name}</span>
                <span class="contract-card-status ${statusClass}">${statusLabel}</span>
            </div>
            ${metaLine}
            ${blurbLine}`;

        // Severity-colored provision chips — compact visual fingerprint
        if (deviations.length === 0) {
            html += `<div class="contract-card-clean">\u2713 All ${s.total_provisions_checked || provCount} provisions conform to reference lease</div>`;
        } else {
            html += `<div class="overview-chip-row">`;
            deviations.forEach(p => {
                const sev = (p.severity || 'MEDIUM').toUpperCase();
                const pid = p.provision_id || '';
                const shortName = (p.provision_name || '').replace(/^LP-\d{2}\s*/, '').replace(/^CUSTOM-\d{2}\s*/, '');
                const label = shortName ? `${esc(pid)} ${esc(shortName)}` : esc(pid);
                html += `<span class="overview-chip overview-chip-${sev.toLowerCase()}">${label}</span>`;
            });
            html += `</div>`;
        }

        html += `</div>`;
    });

    // Top contract cards removed — all contracts shown in unified CONTRACTS section below
    panel.innerHTML = '';
    panel.classList.add('hidden');

}

function renderBatchTable() {
    const tbody = $("#batch-table-body");
    const tenants = currentResults.tenants;

    // Build sortable array with original indices
    const sortable = tenants.map((t, i) => ({ tenant: t, origIndex: i }));
    // Sort by severity descending
    sortable.sort((a, b) => {
        const sa = a.tenant.results && a.tenant.results.summary ? a.tenant.results.summary : {};
        const sb = b.tenant.results && b.tenant.results.summary ? b.tenant.results.summary : {};
        const sevA = SEVERITY_ORDER.indexOf(getHighestSeverity(sa));
        const sevB = SEVERITY_ORDER.indexOf(getHighestSeverity(sb));
        return (sevA === -1 ? 99 : sevA) - (sevB === -1 ? 99 : sevB);
    });

    tbody.innerHTML = sortable.map(({ tenant: t, origIndex: i }) => {
        const r = t.results;
        if (!r || !r.summary) {
            const msg = t.status === "cancelled"
                ? '<span class="cancelled-badge">Cancelled</span>'
                : (t.error && t.error.startsWith("GATE_ABORT:")
                    ? "This document does not appear to be a commercial lease. Please check the uploaded file."
                    : (t.error ? esc(t.error) : "No results"));
            return `<tr data-index="${i}">
                <td>${esc(formatTenantName(t.filename))}</td>
                <td colspan="3">${msg}</td>
            </tr>`;
        }

        const s = r.summary;

        let actionLabel = "No action";
        let actionClass = "action-clear";
        if (s.critical > 0) { actionLabel = "Immediate"; actionClass = "action-immediate"; }
        else if (s.high > 0) { actionLabel = "Review"; actionClass = "action-review"; }
        else if (s.deviates > 0) { actionLabel = "Monitor"; actionClass = "action-monitor"; }

        // Build severity breakdown — show each non-zero severity as its own mini badge
        const sevBreakdown = [];
        if (s.critical > 0) sevBreakdown.push(`<span class="severity-badge severity-CRITICAL">${SEVERITY_ICONS["CRITICAL"] || ""} ${s.critical} Critical</span>`);
        if (s.high > 0)     sevBreakdown.push(`<span class="severity-badge severity-HIGH">${SEVERITY_ICONS["HIGH"] || ""} ${s.high} High</span>`);
        if (s.medium > 0)   sevBreakdown.push(`<span class="severity-badge severity-MEDIUM">${SEVERITY_ICONS["MEDIUM"] || ""} ${s.medium} Medium</span>`);
        if (s.low > 0)      sevBreakdown.push(`<span class="severity-badge severity-LOW">${SEVERITY_ICONS["LOW"] || ""} ${s.low} Low</span>`);
        const sevCell = sevBreakdown.length > 0
            ? `<div class="sev-breakdown">${sevBreakdown.join("")}</div>`
            : `<span class="text-muted">—</span>`;

        return `<tr data-index="${i}" class="${i === currentTenantIndex ? "active-row" : ""}">
            <td>${esc(formatTenantName(t.filename))}</td>
            <td>${s.deviates}</td>
            <td>${sevCell}</td>
            <td><span class="batch-action ${actionClass}">${actionLabel}</span></td>
        </tr>`;
    }).join("");

    tbody.querySelectorAll("tr[data-index]").forEach(tr => {
        tr.addEventListener("click", () => {
            const idx = parseInt(tr.dataset.index, 10);
            switchTopTab("contracts");
            openContractDetail(idx);
        });
    });
}

function renderTechDetails() {
    const el = $("#tech-details-content");
    if (!el || !currentResults || !currentResults.tenants) return;

    const tenants = currentResults.tenants;
    const firstResult = tenants.length > 0 && tenants[0].results ? tenants[0].results : {};
    const templateName = firstResult.template_file || "N/A";
    const modelsUsed = firstResult.models_used || {};

    let totalTime = 0;
    let totalCalls = 0;
    const provisionIds = new Set();
    tenants.forEach(t => {
        if (t.results) {
            totalTime += t.results.elapsed_sec || 0;
            totalCalls += t.results.api_calls_total || 0;
            (t.results.provisions || []).forEach(p => {
                if (p.provision_id) provisionIds.add(p.provision_id);
            });
        }
    });

    const modelNames = [];
    if (modelsUsed.extraction) modelNames.push(`Extraction: ${getModelDisplayName(modelsUsed.extraction)}`);
    if (modelsUsed.evaluator_a) modelNames.push(`${evalName('A')}: ${getModelDisplayName(modelsUsed.evaluator_a)}`);
    if (modelsUsed.evaluator_b) modelNames.push(`${evalName('B')}: ${getModelDisplayName(modelsUsed.evaluator_b)}`);
    if (modelsUsed.evaluator_c) modelNames.push(`${evalName('C')}: ${getModelDisplayName(modelsUsed.evaluator_c)}`);
    if (modelsUsed.challenger) modelNames.push(`Challenger: ${getModelDisplayName(modelsUsed.challenger)}`);
    if (modelsUsed.severity) modelNames.push(`Severity: ${getModelDisplayName(modelsUsed.severity)}`);

    const pids = Array.from(provisionIds).sort().join(", ");

    el.innerHTML = `<div style="display:grid; grid-template-columns:auto 1fr; gap:0.25rem 1rem; font-size:0.8125rem;">
        <span style="color:var(--text-muted);">Template:</span><span>${esc(templateName)}</span>
        <span style="color:var(--text-muted);">Processing time:</span><span>${formatTime(totalTime)}</span>
        <span style="color:var(--text-muted);">API calls:</span><span>${totalCalls} total (${Math.round(totalCalls / tenants.length)} per tenant)</span>
        ${modelNames.length ? `<span style="color:var(--text-muted);">Models:</span><span>${modelNames.map(n => esc(n)).join("<br>")}</span>` : ""}
        <span style="color:var(--text-muted);">Provisions:</span><span>${esc(pids)}</span>
    </div>`;
}

function renderTenantSelector() {
    const select = $("#tenant-select");
    select.innerHTML = currentResults.tenants.map((t, i) =>
        `<option value="${i}">${esc(t.filename)}</option>`
    ).join("");
    select.value = currentTenantIndex;
}

function shortProvisionName(pid, fullName) {
    // "LP-01 Rent & Payment Terms" → "LP-01 Rent"
    if (!fullName) return pid || "";
    // Remove the "LP-XX " prefix from the name to get just the topic
    const topic = fullName.replace(/^LP-\d{2}\s*/, "");
    // Take first word or two (up to first & / , or 3rd word)
    const words = topic.split(/\s+/);
    const short = words.length <= 2 ? words.join(" ") : words.slice(0, 2).join(" ");
    return `${pid} ${short}`;
}

function renderProvisionsChecklist(provisions) {
    const container = $("#provisions-checklist");
    if (!provisions || provisions.length === 0) {
        container.classList.add("hidden");
        return;
    }

    // Suppress LP-00 from checklist pills unless it deviates (Step 116)
    const filteredProvisions = provisions.filter(p => p.provision_id !== "LP-00" || p.final_verdict === "DEVIATES");

    // Sort by provision ID: LP-xx numerically, then CUSTOM-xx, then ADDED-xx
    const pidSortKey = function(pid) {
        const m = (pid || "").match(/^(LP|CUSTOM|ADDED)-(\d+)/i);
        if (!m) return [2, 999];
        const prefix = m[1].toUpperCase();
        const num = parseInt(m[2], 10);
        if (prefix === "LP") return [0, num];
        if (prefix === "CUSTOM") return [1, num];
        return [2, num];
    };

    const sorted = filteredProvisions.slice().sort(function(a, b) {
        const ka = pidSortKey(a.provision_id || "");
        const kb = pidSortKey(b.provision_id || "");
        return ka[0] - kb[0] || ka[1] - kb[1];
    });

    const chips = sorted.map(p => {
        const pid = p.provision_id || "";
        const fullName = p.provision_name || "";
        const label = `${pid} ${fullName.replace(/^LP-\d{2}\s*/, "")}`;

        // Step 184: Confidence class and data attribute
        const sig = p.cam_score ? p.cam_score.governance_signal : '';
        const confClass = {
            'ASSERT_SIGNAL':        '',
            'ASSERT_REVIEW_SIGNAL': 'prov-chip-conf-review',
            'REVIEW_SIGNAL':        'prov-chip-conf-review',
            'WITHHOLD_SIGNAL':      'prov-chip-conf-uncertain',
        }[sig] || '';
        const confData = sig ? ` data-confidence="${esc(sig)}"` : '';
        const confSuffix = confClass ? ' <span class="prov-chip-conf-dot" title="AI confidence lower on this clause">~</span>' : '';

        if (p.final_verdict === "DEVIATES") {
            const sev = p.severity || "MEDIUM";
            return `<span class="prov-chip prov-chip-deviates prov-chip-${esc(sev)} ${confClass}" data-pid="${esc(pid)}"${confData}>${esc(label)}${confSuffix}</span>`;
        } else if (p.final_verdict === "UNCLEAR") {
            return `<span class="prov-chip prov-chip-unclear ${confClass}" data-pid="${esc(pid)}"${confData}>${esc(label)}${confSuffix}</span>`;
        } else {
            return `<span class="prov-chip prov-chip-conforms ${confClass}"${confData}>${esc(label)}${confSuffix}</span>`;
        }
    }).join("");

    // Step 123: append non-standard clause scan indicator
    const scanTag = '<span class="provision-scan-tag">+ Non-standard clause scan</span>';

    container.innerHTML = `<div class="provisions-checked-header">Provisions Checked</div>
        <div class="provisions-checked-chips">${chips}${scanTag}</div>`;
    container.classList.remove("hidden");

    // Show the results legend
    const legend = $("#results-legend");
    if (legend) legend.classList.remove("hidden");

    // Wire up clicking on deviation/unclear chips to scroll to that finding
    container.querySelectorAll(".prov-chip-deviates, .prov-chip-unclear").forEach(chip => {
        chip.addEventListener("click", () => {
            jumpToFinding(chip.dataset.pid);
        });
    });
}

function jumpToFinding(pid) {
    // Ensure we're on the findings tab
    if (activeResultsTab !== "findings") switchResultsTab("findings");
    waitForResultsTarget(() => ensureSummaryProvisionVisible(pid), {
        attempts: activeResultsTab !== "findings" ? 18 : 14,
        delay: 90
    }).then((card) => {
        if (!card) return;
        scrollResultsTargetIntoView(card, 12);
        flashResultsTarget(card, 1500);
    });
}

async function loadResolutions() {
    if (!currentJobId) return;
    try {
        const [resp, covResp] = await Promise.all([
            fetch(`/api/jobs/${currentJobId}/resolutions`),
            fetch(`/api/jobs/${currentJobId}/cov-resolutions`),
        ]);
        if (resp.ok) {
            const data = await resp.json();
            resolutionState = data.resolutions || {};
        }
        if (covResp.ok) {
            const covData = await covResp.json();
            const incoming = covData.cov_resolutions || {};
            Object.assign(_covResState, incoming);
        }
    } catch (e) { /* silent */ }
}

async function renderTenantResults() {
    const tenant = currentResults.tenants[currentTenantIndex];
    if (!tenant || !tenant.results) {
        $("#contract-summary").innerHTML = "<p>No results available for this tenant.</p>";
        $("#deviations-list").innerHTML = "";
        $("#conforming-list").innerHTML = "";
        $("#provisions-checklist").classList.add("hidden");
        return;
    }

    syncChatScopeToCurrentTenant(false);

    await loadResolutions();
    const r = tenant.results;
    renderContractSummary(r.contract_metadata || {});
    renderContractAIComment(currentTenantIndex);
    renderProvisionsChecklist(r.provisions || []);
    const discoveries = r.discoveries || {};
    renderDeviations(r.provisions || [], r.models_used || {}, currentTenantIndex, discoveries);
    renderContractClauseFilterBar(r.provisions || []);
    renderConforming(r.provisions || [], r.models_used || {});
    renderAdditionalFindings(discoveries, r.models_used || {});
    applyFilters(); // 043: reapply active severity filter to new finding-cards
    applyContractClauseFilters();
    loadExistingFeedback();
    injectFinalDraftBar();
}

function updateContractDetailHeader(tenantIdx) {
    var tenant = currentResults && currentResults.tenants ? currentResults.tenants[tenantIdx] : null;
    var headerEl = document.getElementById("contract-detail-header");
    if (!tenant || !headerEl) return;

    var name = formatTenantName(tenant.filename || "");
    var provisions = tenant.results && tenant.results.provisions ? tenant.results.provisions : [];
    var deviationCount = getDeviationWorkflowProvisions(provisions, tenantIdx).length;
    var s = tenant.results && tenant.results.summary;
    var sevCounts = {};
    if (s) {
        ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].forEach(function(sv) {
            sevCounts[sv] = s[sv.toLowerCase()] || 0;
        });
    }

    // Step 315/318: action badge for Mode A only (severity-based). "Clear" removed \u2014
    // it has no actionable meaning ("no deviations found" is already self-evident).
    const _isModeCHeader = isJobModeC();
    var actionBadge = '';
    if (!_isModeCHeader) {
        if (sevCounts['CRITICAL'] > 0)       actionBadge = ' <span class="snapshot-action-badge action-badge-critical">\u26A0 Immediate Action</span>';
        else if (sevCounts['HIGH'] > 0)      actionBadge = ' <span class="snapshot-action-badge action-badge-high">\u26A0 Review Recommended</span>';
        else if (s && (s.deviates || 0) > 0) actionBadge = ' <span class="snapshot-action-badge action-badge-medium">\u00B7 Monitor</span>';
        // "\u2713 Clear" removed (Step 318) \u2014 self-evident from the absence of severity badges
    }

    // Compute fragility badge — show when high-severity findings are predominantly Fragile
    var fragilityBadge = '';
    var _allDevs = getDeviationWorkflowProvisions(provisions, tenantIdx);
    var _highSevDevs = _allDevs.filter(function(p) {
        return p.severity === 'CRITICAL' || p.severity === 'HIGH';
    });
    var _fragileCount = _highSevDevs.filter(function(p) {
        return (p.cam_score || {}).governance_signal === 'ASSERT_REVIEW_SIGNAL';
    }).length;
    // Show fragility badge if 60%+ of high-severity findings are Fragile
    if (_highSevDevs.length >= 2 && _fragileCount >= _highSevDevs.length * 0.6) {
        fragilityBadge = ' <span class="snapshot-action-badge action-badge-fragile">\u26A0 Fragile Findings</span>';
    }

    var deviationBadge = deviationCount > 0
        ? ' <span class="contract-detail-deviation-badge">' + deviationCount + ' Deviation' + (deviationCount !== 1 ? 's' : '') + '</span>'
        : '';

    // Step 318: "\u2713 Clean" / "\u2713 Resolved" pills removed \u2014 no clear meaning in either mode.

    var r2 = tenant.results || {};
    var provCount = provisions.length;
    var elapsed = r2.elapsed_sec ? fmtDuration(r2.elapsed_sec) : null;
    var apiCalls = r2.api_calls_total || null;
    var runStatParts = [];
    if (provCount) runStatParts.push(provCount + ' provision' + (provCount !== 1 ? 's' : ''));
    if (elapsed) runStatParts.push(elapsed + ' runtime');
    if (apiCalls) runStatParts.push(apiCalls + ' model calls');
    var runStatBadge = runStatParts.length
        ? ' <span class="contract-detail-run-stats">' + runStatParts.join(' &middot; ') + '</span>'
        : '';

    headerEl.innerHTML = '<div class="contract-detail-header-row">'
        + '<h2 class="contract-detail-name">' + esc(name) + actionBadge + fragilityBadge + deviationBadge + '</h2>'
        + runStatBadge
        + '<div id="final-draft-status-header" class="contract-final-draft-status hidden"></div>'
        + '</div>';
}

function getContractPickerStatusValue(tenant) {
    var s = tenant && tenant.results ? tenant.results.summary : null;
    if (!s) return null;
    if (s.critical > 0) return 'critical';
    if (s.high > 0) return 'high';
    if ((s.medium || 0) > 0) return 'medium';
    if ((s.deviates || 0) > 0) return 'low';
    return 'clear';
}

function getAvailableContractPickerStatuses() {
    const tenants = (currentResults && currentResults.tenants) ? currentResults.tenants : [];
    const statuses = new Set();
    tenants.forEach(function(tenant) {
        const status = getContractPickerStatusValue(tenant);
        if (status) statuses.add(status);
    });
    return statuses;
}

function buildContractPickerStatusOptions() {
    const available = getAvailableContractPickerStatuses();
    const optionDefs = [
        { value: 'critical', label: 'Critical' },
        { value: 'high', label: 'High' },
        { value: 'medium', label: 'Medium' },
        { value: 'low', label: 'Low' },
        { value: 'clear', label: 'Clear' }
    ];
    if (contractPickerSeverityFilter !== 'all' && !available.has(contractPickerSeverityFilter)) {
        contractPickerSeverityFilter = 'all';
    }
    let html = '<option value="all">Severity: All</option>';
    optionDefs.forEach(function(opt) {
        if (!available.has(opt.value)) return;
        html += '<option value="' + opt.value + '"' + (contractPickerSeverityFilter === opt.value ? ' selected' : '') + '>' + opt.label + '</option>';
    });
    return html;
}

function renderContractPickerFilterBar() {
    const bar = $("#contract-clause-filter-bar");
    if (!bar) return;
    bar.classList.remove("hidden");
    bar.innerHTML = `
        <div class="contract-clause-filter-layout">
            <div class="contract-clause-filter-controls">
                <select id="contract-selector-dropdown" class="contract-selector-select"></select>
                <select id="contract-picker-severity-filter" class="contract-clause-filter-select">
                    ${buildContractPickerStatusOptions()}
                </select>
            </div>
        </div>
    `;
    $("#contract-picker-severity-filter")?.addEventListener("change", (e) => {
        contractPickerSeverityFilter = e.target.value;
        renderContractSelectorBar(null);
    });
}

function getAvailableClauseFilterValues(provisions) {
    const rawProvisions = provisions || [];
    const deviations = rawProvisions
        .filter(function(p) {
            return p
                && p.provision_id !== "LP-00"
                && (p.final_verdict === "DEVIATES"
                    || p.final_verdict === "UNCLEAR"
                    || isManualEscalatedProvision(p, currentTenantIndex));
        })
        .map(function(p) {
            return isManualEscalatedProvision(p, currentTenantIndex)
                ? buildManualEscalatedProvision(p, currentTenantIndex)
                : p;
        });
    const conforming = rawProvisions.filter(function(p) {
        return p && p.provision_id !== "LP-00" && p.final_verdict === "CONFORMS" && !isManualEscalatedProvision(p, currentTenantIndex);
    });
    const severitySet = new Set();
    const statusSet = new Set();
    const confidenceSet = new Set();
    let hasRead = false;
    let hasUnread = false;
    let hasNotes = false;
    let hasNoNotes = false;

    const getClauseConfidenceBucket = function(signal) {
        switch ((signal || '').toUpperCase()) {
            case 'ASSERT_SIGNAL':
                return 'verified';
            case 'ASSERT_REVIEW_SIGNAL':
                return 'impact_unclear';
            case 'REVIEW_SIGNAL':
                return 'needs_review';
            case 'WITHHOLD_SIGNAL':
                return 'inconclusive';
            default:
                return '';
        }
    };

    deviations.forEach(function(p) {
        const pid = p.provision_id || "";
        const severity = (p.severity || "").toUpperCase();
        if (severity) severitySet.add(severity);
        const confBucket = getClauseConfidenceBucket(p && p.cam_score ? p.cam_score.governance_signal : '');
        if (confBucket) confidenceSet.add(confBucket);
        const key = `${currentTenantIndex}:${pid}`;
        const resolution = (resolutionState[key] || {}).status || 'open';
        statusSet.add(resolution);
        const noteCount = ((resolutionState[key] || {}).notes || []).length;
        if (noteCount > 0) hasNotes = true;
        else hasNoNotes = true;
        if (isNoted(currentTenantIndex, pid)) hasRead = true;
        else hasUnread = true;
    });

    conforming.forEach(function(p) {
        const pid = p.provision_id || "";
        statusSet.add('conforming');
        const confBucket = getClauseConfidenceBucket(p && p.cam_score ? p.cam_score.governance_signal : '');
        if (confBucket) confidenceSet.add(confBucket);
        if (isNoted(currentTenantIndex, pid)) hasRead = true;
        else hasUnread = true;
        if (getConformingConcernState(currentTenantIndex, pid) === 'concern') hasNotes = true;
        else hasNoNotes = true;
    });

    // Provision names
    const provisionSet = new Map(); // pid -> name
    deviations.forEach(function(p) {
        const pid = p.provision_id || "";
        const name = (p.provision_name || pid).replace(/^LP-\d{2}\s*/, "");
        provisionSet.set(pid, name);
    });
    conforming.forEach(function(p) {
        const pid = p.provision_id || "";
        const name = (p.provision_name || pid).replace(/^LP-\d{2}\s*/, "");
        provisionSet.set(pid, name);
    });

    return {
        severities: severitySet,
        statuses: statusSet,
        confidences: confidenceSet,
        provisions: provisionSet,
        hasRead,
        hasUnread,
        hasNotes,
        hasNoNotes
    };
}

function renderContractSelectorBar(selectedTenantIdx) {
    var selectorBar = document.getElementById('contract-selector-bar');
    var filterBar = document.getElementById('contract-clause-filter-bar');
    if (!selectorBar || !currentResults || !currentResults.tenants) return;

    if (selectedTenantIdx === null || selectedTenantIdx === undefined) {
        selectorBar.classList.remove('hidden');
        renderContractPickerFilterBar();
        // Populate dropdown after filter bar renders it
        var selectorDrop = document.getElementById('contract-selector-dropdown');
        if (!selectorDrop) return;
        var filteredTenants = currentResults.tenants
            .map(function(t, i) { return { tenant: t, index: i }; })
            .filter(function(entry) {
                if (contractPickerSeverityFilter === 'all') return true;
                return getContractPickerStatusValue(entry.tenant) === contractPickerSeverityFilter;
            });

        selectorDrop.innerHTML = '<option value="">— Select a contract —</option>'
            + filteredTenants.map(function(entry) {
                var name = (entry.tenant.filename || ('Contract ' + (entry.index + 1))).replace(/\.[^/.]+$/, '');
                return '<option value="' + entry.index + '">' + esc(name) + '</option>';
            }).join('');
        selectorDrop.value = '';
        selectorDrop.onchange = function() {
            var idx = parseInt(selectorDrop.value, 10);
            if (!isNaN(idx)) openContractDetail(idx);
        };
        return;
    }

    // Detail mode — just show the bars; dropdown is populated by renderContractClauseFilterBar
    selectorBar.classList.remove('hidden');
    if (filterBar) filterBar.classList.remove('hidden');
}

function renderContractClauseFilterBar(provisions) {
    const bar = $("#contract-clause-filter-bar");
    if (!bar) return;
    const available = getAvailableClauseFilterValues(provisions);
    const severityDefs = [
        { value: 'CRITICAL', label: 'Critical' },
        { value: 'HIGH', label: 'High' },
        { value: 'MEDIUM', label: 'Medium' },
        { value: 'LOW', label: 'Low' }
    ];
    const statusDefs = [
        { value: 'conforming', label: 'Conforming' },
        { value: 'open', label: 'Open' },
        { value: 'in_review', label: 'In Review' },
        { value: 'escalated', label: 'Escalated' },
        { value: 'not_a_deviation', label: 'Not a Deviation' },
        { value: 'resolved', label: 'Resolved' }
    ];

    // Remove selected severities that are no longer available
    for (const s of [...contractClauseSeverityFilter]) {
        if (!available.severities.has(s)) contractClauseSeverityFilter.delete(s);
    }
    if (contractClauseStatusFilter !== 'all' && !available.statuses.has(contractClauseStatusFilter)) {
        contractClauseStatusFilter = 'all';
    }
    if (contractClauseReadFilter === 'read' && !available.hasRead) contractClauseReadFilter = 'all';
    if (contractClauseReadFilter === 'unread' && !available.hasUnread) contractClauseReadFilter = 'all';
    if (contractClauseNotesFilter === 'has_notes' && !available.hasNotes) contractClauseNotesFilter = 'all';
    if (contractClauseNotesFilter === 'no_notes' && !available.hasNoNotes) contractClauseNotesFilter = 'all';
    for (const c of [...contractClauseConfidenceFilter]) {
        if (!available.confidences.has(c)) contractClauseConfidenceFilter.delete(c);
    }

    const severityDropdownHtml = `<div class="filter-dropdown clause-filter-dropdown" id="clause-severity-dropdown">
        <button class="btn btn-outline filter-dropdown-trigger clause-filter-trigger" id="clause-severity-trigger" type="button">
            Severity: <span id="clause-severity-label">${contractClauseSeverityFilter.size === 0 ? 'All' : contractClauseSeverityFilter.size === 1 ? [...contractClauseSeverityFilter][0] : 'Custom'}</span> &#9662;
        </button>
        <div class="filter-dropdown-panel clause-filter-panel hidden" id="clause-severity-panel">
            <label class="filter-option filter-option-all">
                <input type="checkbox" id="clause-severity-all"${contractClauseSeverityFilter.size === 0 ? ' checked' : ''}>
                <span>All Severities</span>
            </label>
            ${severityDefs.filter(def => available.severities.has(def.value)).map(def =>
                `<label class="filter-option">
                    <input type="checkbox" value="${def.value}" class="clause-sev-cb"${contractClauseSeverityFilter.has(def.value) ? ' checked' : ''}>
                    <span>${def.label}</span>
                </label>`
            ).join('')}
        </div>
    </div>`;
    const statusOptions = ['<option value="all">Status: All</option>']
        .concat(statusDefs.filter(def => available.statuses.has(def.value)).map(def =>
            `<option value="${def.value}"${contractClauseStatusFilter === def.value ? ' selected' : ''}>${def.label}</option>`
        )).join('');
    const readOptions = ['<option value="all">Read: All</option>']
        .concat(available.hasRead ? [`<option value="read"${contractClauseReadFilter === 'read' ? ' selected' : ''}>Read</option>`] : [])
        .concat(available.hasUnread ? [`<option value="unread"${contractClauseReadFilter === 'unread' ? ' selected' : ''}>Unread</option>`] : [])
        .join('');
    const notesOptions = ['<option value="all">Notes: All</option>']
        .concat(available.hasNotes ? [`<option value="has_notes"${contractClauseNotesFilter === 'has_notes' ? ' selected' : ''}>Has Notes</option>`] : [])
        .concat(available.hasNoNotes ? [`<option value="no_notes"${contractClauseNotesFilter === 'no_notes' ? ' selected' : ''}>No Notes</option>`] : [])
        .join('');
    const confDefs = [
        { value: 'verified', label: 'Verified' },
        { value: 'impact_unclear', label: 'Impact Unclear' },
        { value: 'needs_review', label: 'Needs Review' },
        { value: 'inconclusive', label: 'Inconclusive' },
    ];
    const confidenceDropdownHtml = `<div class="filter-dropdown clause-filter-dropdown" id="clause-confidence-dropdown">
        <button class="btn btn-outline filter-dropdown-trigger clause-filter-trigger" id="clause-confidence-trigger" type="button">
            Confidence: <span id="clause-confidence-label">${contractClauseConfidenceFilter.size === 0 ? 'All' : contractClauseConfidenceFilter.size === 1 ? [...contractClauseConfidenceFilter][0] : 'Custom'}</span> &#9662;
        </button>
        <div class="filter-dropdown-panel clause-filter-panel hidden" id="clause-confidence-panel">
            <label class="filter-option filter-option-all">
                <input type="checkbox" id="clause-confidence-all"${contractClauseConfidenceFilter.size === 0 ? ' checked' : ''}>
                <span>All Confidence</span>
            </label>
            ${confDefs.filter(def => available.confidences.has(def.value)).map(def =>
                `<label class="filter-option">
                    <input type="checkbox" value="${def.value}" class="clause-conf-cb"${contractClauseConfidenceFilter.has(def.value) ? ' checked' : ''}>
                    <span>${def.label}</span>
                </label>`
            ).join('')}
        </div>
    </div>`;

    const tenant = currentResults && currentResults.tenants ? currentResults.tenants[currentTenantIndex] : null;
    const annotatedButton = tenant && tenant.has_annotated
        ? `<button type="button" class="btn btn-secondary btn-sm contract-annotated-btn"
            onclick="window.CAM.downloadFile('/api/jobs/${currentJobId}/results/${currentTenantIndex}/annotated')">
            &#128196; Download Working Draft
        </button>`
        : '';
    // Step 255: Aligned Provision Comparison View — Mode A only.
    // Server omits has_comparison_view in Mode C, so the button never appears
    // there even before the isJobModeC() guard kicks in.
    const comparisonButton = tenant && tenant.has_comparison_view && !isJobModeC()
        ? `<button type="button" class="btn btn-secondary btn-sm contract-comparison-btn"
            title="Open the Aligned Provision Comparison PDF — view template and tenant clause-by-clause"
            onclick="window.CAM.downloadFile('/api/jobs/${currentJobId}/results/${currentTenantIndex}/comparison')">
            &#128196; Aligned Provision Comparison
        </button>`
        : '';
    // Step 277: Generate Final Draft consumes provisions[] (Mode A
    // deviation findings) and is inert in Mode C — would produce a
    // 10-paragraph stub with all-zero counts. Hide the button entirely
    // in Mode C runs. Mirror the comparisonButton guard pattern.
    const finalDraftButton = !isJobModeC()
        ? `<button type="button" class="fd-generate-btn contract-final-draft-btn" id="fd-generate-btn" disabled
            onclick="window.CAM.generateFinalDraft()">Generate Final Draft ↓</button>`
        : '';

    // Provision filter select (Step 346b — replaces checkbox dropdown)
    const provEntries = [...available.provisions.entries()].sort(function(a, b) {
        const ka = pidSortKeyGlobal(a[0]), kb = pidSortKeyGlobal(b[0]);
        return ka[0] - kb[0] || ka[1] - kb[1];
    });
    for (const pid of [...contractClauseProvisionFilter]) {
        if (!available.provisions.has(pid)) contractClauseProvisionFilter.delete(pid);
    }
    const currentProvVal = contractClauseProvisionFilter.size === 1 ? [...contractClauseProvisionFilter][0] : '';
    const provisionDropdownHtml = `<select id="clause-provision-select" class="filter-provision-select contract-clause-filter-select">
        <option value="">All Provisions</option>
        ${provEntries.map(function(e) {
            return '<option value="' + esc(e[0]) + '"' + (contractClauseProvisionFilter.has(e[0]) ? ' selected' : '') + '>' + esc(e[0] + ' ' + e[1]) + '</option>';
        }).join('')}
    </select>`;

    // Sort dropdown
    const sortOptions = '<option value="severity"' + (contractClauseSort === 'severity' ? ' selected' : '') + '>Order: Risk level</option>'
        + '<option value="confidence"' + (contractClauseSort === 'confidence' ? ' selected' : '') + '>Order: Confidence</option>'
        + '<option value="provision_id"' + (contractClauseSort === 'provision_id' ? ' selected' : '') + '>Order: Provision ID</option>';

    bar.classList.remove("hidden");
    bar.innerHTML = `
        <div class="contract-clause-filter-layout">
            <div class="contract-clause-filter-toprow">
                <div class="contract-clause-filter-actions">
                    ${annotatedButton}
                    ${comparisonButton}
                    ${finalDraftButton}
                </div>
            </div>
            <div class="contract-clause-filter-controls">
                ${currentResults && currentResults.tenants && currentResults.tenants.length > 1 ? '<select id="contract-selector-dropdown" class="contract-selector-select"></select>' : ''}
                ${severityDropdownHtml}
                <select id="contract-clause-read-filter" class="contract-clause-filter-select">
                    ${readOptions}
                </select>
                <select id="contract-clause-notes-filter" class="contract-clause-filter-select">
                    ${notesOptions}
                </select>
                <button type="button" class="contract-clause-filter-reset" id="contract-clause-filter-reset">Reset</button>
            </div>
        </div>
    `;

    // Position a fixed dropdown panel below its trigger button
    function positionClausePanel(trigger, panel) {
        const rect = trigger.getBoundingClientRect();
        panel.style.top = rect.bottom + 2 + "px";
        panel.style.left = rect.left + "px";
    }

    // Severity multi-select dropdown
    function closeAllClausePanels(except) {
        ["clause-severity-panel", "clause-confidence-panel"].forEach(function(id) {
            if (id !== except) { const p = $("#" + id); if (p) p.classList.add("hidden"); }
        });
    }
    const _sevTrigger = $("#clause-severity-trigger");
    if (_sevTrigger) _sevTrigger.addEventListener("click", () => {
        closeAllClausePanels("clause-severity-panel");
        const panel = $("#clause-severity-panel");
        if (panel) {
            panel.classList.toggle("hidden");
            if (!panel.classList.contains("hidden")) positionClausePanel(_sevTrigger, panel);
        }
    });
    const _sevAll = $("#clause-severity-all");
    if (_sevAll) _sevAll.addEventListener("change", function() {
        if (this.checked) {
            contractClauseSeverityFilter.clear();
            document.querySelectorAll(".clause-sev-cb").forEach(cb => cb.checked = false);
        }
        applyContractClauseFilters();
        const label = $("#clause-severity-label");
        if (label) label.textContent = "All";
    });
    document.querySelectorAll(".clause-sev-cb").forEach(cb => {
        cb.addEventListener("change", function() {
            if (this.checked) contractClauseSeverityFilter.add(this.value);
            else contractClauseSeverityFilter.delete(this.value);
            const allCb = $("#clause-severity-all");
            if (allCb) allCb.checked = contractClauseSeverityFilter.size === 0;
            const label = $("#clause-severity-label");
            if (label) label.textContent = contractClauseSeverityFilter.size === 0 ? "All" : contractClauseSeverityFilter.size === 1 ? [...contractClauseSeverityFilter][0] : "Custom";
            applyContractClauseFilters();
        });
    });

    // Step 347: confidence, provision, sort, status removed from toolbar.
    // Read and Notes remain.
    $("#contract-clause-read-filter")?.addEventListener("change", (e) => {
        contractClauseReadFilter = e.target.value;
        applyContractClauseFilters();
    });
    $("#contract-clause-notes-filter")?.addEventListener("change", (e) => {
        contractClauseNotesFilter = e.target.value;
        applyContractClauseFilters();
    });
    $("#contract-clause-filter-reset")?.addEventListener("click", () => {
        contractClauseSeverityFilter.clear();
        contractClauseStatusFilter = 'all';
        contractClauseReadFilter = 'all';
        contractClauseNotesFilter = 'all';
        contractClauseConfidenceFilter.clear();
        contractClauseProvisionFilter.clear();
        contractClauseSort = 'severity';
        const tenant = currentResults && currentResults.tenants ? currentResults.tenants[currentTenantIndex] : null;
        renderContractClauseFilterBar((tenant && tenant.results && tenant.results.provisions) || []);
        applyContractClauseFilters();
    });
    updateFinalDraftBar();

    // Populate the contract selector dropdown (now inside filter bar HTML)
    var selectorDrop = document.getElementById('contract-selector-dropdown');
    if (selectorDrop && currentResults && currentResults.tenants) {
        selectorDrop.innerHTML = currentResults.tenants.map(function(t, i) {
            var dName = formatTenantName(t.filename || ('Contract ' + (i + 1)));
            return '<option value="' + i + '">' + esc(dName) + '</option>';
        }).join('');
        selectorDrop.value = String(currentTenantIndex);
        selectorDrop.onchange = function() {
            var idx = parseInt(selectorDrop.value, 10);
            if (!isNaN(idx)) openContractDetail(idx);
        };
    }
}

function applyContractClauseFilters() {
    const cards = Array.from(document.querySelectorAll("#deviations-list .finding-card"));
    const conformingItems = Array.from(document.querySelectorAll("#conforming-list .conforming-item"));
    const header = $("#deviations-header");
    const total = cards.length;
    let visible = 0;
    const provisionMap = new Map((((currentResults || {}).tenants || [])[currentTenantIndex]?.results?.provisions || []).map(function(p) {
        return [p.provision_id || "", p];
    }));
    const getClauseConfidenceBucket = function(signal) {
        switch ((signal || '').toUpperCase()) {
            case 'ASSERT_SIGNAL':
                return 'verified';
            case 'ASSERT_REVIEW_SIGNAL':
                return 'impact_unclear';
            case 'REVIEW_SIGNAL':
                return 'needs_review';
            case 'WITHHOLD_SIGNAL':
                return 'inconclusive';
            default:
                return '';
        }
    };
    const confidenceMatches = function(bucket) {
        return contractClauseConfidenceFilter.size === 0 || contractClauseConfidenceFilter.has(bucket);
    };

    // Sort order for confidence signals (lower = higher priority)
    const confSortOrder = { ASSERT_SIGNAL: 3, ASSERT_REVIEW_SIGNAL: 2, REVIEW_SIGNAL: 1, WITHHOLD_SIGNAL: 0 };
    const sevSortOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

    // Sort cards if needed
    if (contractClauseSort !== 'severity') {
        const devList = document.getElementById("deviations-list");
        if (devList && cards.length > 1) {
            cards.sort(function(a, b) {
                if (contractClauseSort === 'confidence') {
                    const ca = confSortOrder[(a.dataset.confidence || '').toUpperCase()] ?? 4;
                    const cb = confSortOrder[(b.dataset.confidence || '').toUpperCase()] ?? 4;
                    if (ca !== cb) return ca - cb;
                    // Tiebreak by severity
                    const sa = sevSortOrder[(a.dataset.severity || '').toUpperCase()] ?? 4;
                    const sb = sevSortOrder[(b.dataset.severity || '').toUpperCase()] ?? 4;
                    return sa - sb;
                }
                if (contractClauseSort === 'provision_id') {
                    const ka = pidSortKeyGlobal(a.dataset.provision || "");
                    const kb = pidSortKeyGlobal(b.dataset.provision || "");
                    return ka[0] - kb[0] || ka[1] - kb[1];
                }
                return 0;
            });
            cards.forEach(function(c) { devList.appendChild(c); });
        }
    } else {
        // Default sort: severity (re-sort in case prior sort changed DOM order)
        const devList = document.getElementById("deviations-list");
        if (devList && cards.length > 1) {
            cards.sort(function(a, b) {
                const sa = sevSortOrder[(a.dataset.severity || '').toUpperCase()] ?? 4;
                const sb = sevSortOrder[(b.dataset.severity || '').toUpperCase()] ?? 4;
                if (sa !== sb) return sa - sb;
                const ka = pidSortKeyGlobal(a.dataset.provision || "");
                const kb = pidSortKeyGlobal(b.dataset.provision || "");
                return ka[0] - kb[0] || ka[1] - kb[1];
            });
            cards.forEach(function(c) { devList.appendChild(c); });
        }
    }

    cards.forEach(card => {
        const pid = card.dataset.provision || "";
        const tenantIdx = parseInt(card.dataset.tenantIdx || String(currentTenantIndex), 10);
        const severity = (card.dataset.severity || '').toUpperCase();
        const confidenceBucket = getClauseConfidenceBucket(card.dataset.confidence || '');
        const key = `${tenantIdx}:${pid}`;
        const resolution = (resolutionState[key] || {}).status || 'open';
        const hasNotes = ((resolutionState[key] || {}).notes || []).length > 0;
        const isRead = isNoted(tenantIdx, pid);

        const provisionOk = contractClauseProvisionFilter.size === 0 || contractClauseProvisionFilter.has(pid);
        const severityOk = contractClauseSeverityFilter.size === 0 || contractClauseSeverityFilter.has(severity) || !severity;
        const statusOk = contractClauseStatusFilter === 'all' || resolution === contractClauseStatusFilter;
        const readOk = contractClauseReadFilter === 'all'
            || (contractClauseReadFilter === 'read' && isRead)
            || (contractClauseReadFilter === 'unread' && !isRead);
        const notesOk = contractClauseNotesFilter === 'all'
            || (contractClauseNotesFilter === 'has_notes' && hasNotes)
            || (contractClauseNotesFilter === 'no_notes' && !hasNotes);
        const confidenceOk = confidenceMatches(confidenceBucket);

        const show = severityOk && statusOk && readOk && notesOk && confidenceOk && provisionOk;
        card.classList.toggle("hidden", !show);
        if (show) visible++;
    });

    conformingItems.forEach(item => {
        const pid = item.dataset.pid || "";
        const isRead = isNoted(currentTenantIndex, pid);
        const hasNotes = getConformingConcernState(currentTenantIndex, pid) === 'concern';
        const provision = provisionMap.get(pid) || null;
        const confidenceBucket = getClauseConfidenceBucket(provision && provision.cam_score ? provision.cam_score.governance_signal : '');
        const provisionOk = contractClauseProvisionFilter.size === 0 || contractClauseProvisionFilter.has(pid);
        const statusOk = contractClauseStatusFilter === 'all' || contractClauseStatusFilter === 'conforming';
        const readOk = contractClauseReadFilter === 'all'
            || (contractClauseReadFilter === 'read' && isRead)
            || (contractClauseReadFilter === 'unread' && !isRead);
        const notesOk = contractClauseNotesFilter === 'all'
            || (contractClauseNotesFilter === 'has_notes' && hasNotes)
            || (contractClauseNotesFilter === 'no_notes' && !hasNotes);
        const severityOk = contractClauseSeverityFilter.size === 0;
        const confidenceOk = confidenceMatches(confidenceBucket);
        item.classList.toggle("hidden", !(severityOk && statusOk && readOk && notesOk && confidenceOk && provisionOk));
    });

    if (header) header.textContent = "Deviations \u2014 Review Recommended";
}

function shouldShowField(value) {
    if (!value || typeof value !== "string") return false;
    // Strip underscores and TBDs, then check for meaningful content
    const cleaned = value.replace(/_{2,}/g, "").replace(/TBD/gi, "").trim();
    if (cleaned.length < 5) return false;
    // Known useless patterns
    if (/TBD.*\$.*TBD/i.test(value)) return false;   // "TBD Dollars ($TBD)"
    if (/TBD day of TBD/i.test(value)) return false;  // "TBD day of TBD, 20__"
    if (/^20__$/.test(value.trim())) return false;
    return true;
}

function truncateToSentence(text, maxChars) {
    if (maxChars === undefined) maxChars = 250;
    if (!text || text.length <= maxChars) return text;
    var truncated = text.substring(0, maxChars);
    var lastEnd = Math.max(
        truncated.lastIndexOf(". "),
        truncated.lastIndexOf(".) "),
        truncated.lastIndexOf("; ")
    );
    if (lastEnd > 80) return text.substring(0, lastEnd + 1);
    var lastSpace = truncated.lastIndexOf(" ");
    if (lastSpace > 80) return truncated.substring(0, lastSpace) + "...";
    return truncated + "...";
}

// Step 125: Build deal overview table HTML for Contract Summary tab
function buildDealOverviewTable(tenantResult) {
    if (!tenantResult) return '';
    var deal = tenantResult.deal_overview || {};
    var meta = tenantResult.contract_metadata || {};

    var d = function(v) { return (v && typeof v === 'string' && v.trim()) ? esc(v.trim()) : '\u2014'; };

    var landlord = deal.landlord_name || meta.landlord || '';
    var tenantName = deal.tenant_name || meta.tenant_name || meta.tenant || '';
    var property = deal.property_address || meta.property_description || '';
    var termYears = deal.lease_term_years;
    var commencement = deal.commencement_date || meta.effective_date || '';
    var expiration = deal.expiration_date || '';
    var rent = deal.base_rent_monthly || meta.base_rent || '';
    var escalation = deal.escalation || '';
    var camStructure = deal.cam_structure || '';
    var security = deal.security_deposit || '';
    var renewal = deal.renewal_options || '';
    var permittedUse = deal.permitted_use || meta.permitted_use || '';
    var govLaw = deal.governing_law || meta.governing_law || '';
    var keyTerms = deal.key_terms_summary || [];

    // Build term string
    var termStr = '';
    if (termYears) {
        termStr = termYears + ' year' + (termYears !== 1 ? 's' : '');
        if (commencement || expiration) {
            termStr += '  \u00B7  Commencement: ' + d(commencement) + '  \u00B7  Expiration: ' + d(expiration);
        }
    } else if (meta.term_length) {
        termStr = meta.term_length;
    }

    // Build economics lines
    var econLines = [];
    econLines.push('Base Rent: ' + d(rent));
    if (escalation) econLines.push('Escalation: ' + d(escalation));
    if (camStructure) econLines.push('CAM: ' + d(camStructure));
    if (security) econLines.push('Security Deposit: ' + d(security));

    // Build rows
    var rows = '';
    rows += '<div class="deal-overview-label">Parties</div><div class="deal-overview-value">'
        + 'Landlord: ' + d(landlord) + '<br>Tenant: ' + d(tenantName) + '</div>';
    rows += '<div class="deal-overview-label">Property</div><div class="deal-overview-value' + (!property ? ' empty' : '') + '">'
        + d(property) + '</div>';
    rows += '<div class="deal-overview-label">Term</div><div class="deal-overview-value' + (!termStr ? ' empty' : '') + '">'
        + (termStr ? esc(termStr) : '\u2014') + '</div>';
    rows += '<div class="deal-overview-label">Economics</div><div class="deal-overview-value">'
        + econLines.join('<br>') + '</div>';
    rows += '<div class="deal-overview-label">Options</div><div class="deal-overview-value' + (!renewal ? ' empty' : '') + '">'
        + 'Renewal: ' + d(renewal) + '</div>';
    rows += '<div class="deal-overview-label">Use</div><div class="deal-overview-value">'
        + d(permittedUse)
        + (govLaw ? '<br>Governing Law: ' + d(govLaw) : '')
        + '</div>';

    // Key terms bullets
    var keyTermsHtml = '';
    if (keyTerms && keyTerms.length > 0) {
        keyTermsHtml = '<div class="deal-key-terms"><div class="deal-key-terms-heading">Key Terms</div><ul>';
        keyTerms.forEach(function(kt) {
            if (kt && typeof kt === 'string' && kt.trim()) {
                keyTermsHtml += '<li>' + esc(kt.trim()) + '</li>';
            }
        });
        keyTermsHtml += '</ul></div>';
    }

    return '<div class="deal-overview-section">'
        + '<div class="deal-overview-heading">Deal Overview</div>'
        + '<div class="deal-overview-table">' + rows + '</div>'
        + keyTermsHtml
        + '</div>';
}

function renderContractSummary(meta) {
    const container = $("#contract-summary");

    // Get current tenant's results for deviation stats
    const tenant = currentResults.tenants[currentTenantIndex];
    const r = tenant && tenant.results ? tenant.results : {};
    const summary = r.summary || {};
    const provisions = r.provisions || [];
    const totalProvisions = provisions.length;
    const deviationCount = summary.deviates || 0;

    // Filter metadata — only show fields with real data
    const tenantName = shouldShowField(meta.tenant) ? meta.tenant : "";
    const landlord = shouldShowField(meta.landlord) ? meta.landlord : "";
    const property = shouldShowField(meta.property_description) ? meta.property_description : "";
    const term = shouldShowField(meta.term_length) ? meta.term_length : "";
    const rent = shouldShowField(meta.base_rent) ? meta.base_rent : "";
    const startDate = shouldShowField(meta.effective_date) ? meta.effective_date : "";
    const govLaw = shouldShowField(meta.governing_law) ? meta.governing_law : "";

    // If ALL key fields are empty, show fallback
    const hasAnyField = tenantName || landlord || property || term || rent;
    if (!hasAnyField && !deviationCount) {
        container.innerHTML = `<div class="contract-hero">
            <div class="contract-headline">${esc(tenant.filename || "Tenant Lease")}</div>
            <div class="contract-subline">Contract details not available \u2014 see executed lease.</div>
            <div class="contract-footer">${totalProvisions} provision${totalProvisions !== 1 ? "s" : ""} analyzed${govLaw ? ` &middot; Governing law: ${esc(govLaw)}` : ""}</div>
        </div>`;
        return;
    }

    // Headline
    const headline = tenantName || tenant.filename || "Tenant Lease";
    const sublines = [];
    if (property) sublines.push(esc(property));
    if (landlord) sublines.push(`Landlord: ${esc(landlord)}`);

    // Term as text line (added to sublines)
    if (term) sublines.push(`Term: ${esc(term)}`);

    // Deviation chips row
    const deviationProvisions = provisions
        .filter(p => p.final_verdict === "DEVIATES")
        .sort((a, b) => {
            const ai = SEVERITY_ORDER.indexOf(a.severity);
            const bi = SEVERITY_ORDER.indexOf(b.severity);
            return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
        });

    let chipsHtml = "";
    if (deviationProvisions.length > 0) {
        // 6a: Deviation count on its own line
        const sevParts = [];
        if (summary.critical) sevParts.push(`${summary.critical} CRITICAL`);
        if (summary.high) sevParts.push(`${summary.high} HIGH`);
        if (summary.medium) sevParts.push(`${summary.medium} MEDIUM`);
        if (summary.low) sevParts.push(`${summary.low} LOW`);
        const countText = `${deviationCount} Deviation${deviationCount !== 1 ? "s" : ""} &middot; ${sevParts.join(" &middot; ")}`;

        // 6b + 6c: Risk headline chips color-coded by severity, clickable
        const headlineChips = deviationProvisions.map(d => {
            const sev = d.severity || "LOW";
            const pid = d.provision_id || "";
            let headline = d.risk_headline || d.challenge_details || d.what_changed || "";
            return `<span class="risk-headline-chip risk-headline-${sev}" data-pid="${esc(pid)}">${esc(headline)}</span>`;
        }).join("");

        chipsHtml = `<div class="contract-chips-row">
            <span class="deviation-count-chip">${countText}</span>
        </div>
        <div class="contract-chips-row">
            ${headlineChips}
        </div>`;
    } else {
        chipsHtml = `<div class="contract-chips-row">
            <span class="deviation-count-chip conforming-chip">\u2705 All provisions conform</span>
        </div>`;
    }

    // Footer
    const footerParts = [];
    footerParts.push(`${totalProvisions} provision${totalProvisions !== 1 ? "s" : ""} analyzed`);
    if (govLaw) footerParts.push(`Governing law: ${esc(govLaw)}`);

    // Step 182: CAM confidence summary line
    let camConfidenceHtml = '';
    const camSummary = r.cam_contract_summary;
    if (camSummary) {
        const confident   = (camSummary.governance_counts && camSummary.governance_counts.ASSERT_SIGNAL) || 0;
        const total       = camSummary.provisions_scored || 0;
        const noBaseline  = camSummary.withhold_no_baseline || 0;
        const effectiveTotal = total - noBaseline;
        const ratio = effectiveTotal > 0 ? confident / effectiveTotal : 1.0;
        const tier = ratio >= 0.75 ? 'High' : ratio >= 0.50 ? 'Medium' : 'Low';

        let noBaselineNote = '';
        if (noBaseline > 0) {
            noBaselineNote = ` <span class="cam-confidence-note">+ ${noBaseline} tenant-added clause${noBaseline !== 1 ? 's' : ''} reviewed separately (no template baseline)</span>`;
        }
        camConfidenceHtml = `<div class="cam-confidence-line">Analysis confidence: <strong>${tier}</strong> (${confident} of ${effectiveTotal} standard provisions confidently evaluated)${noBaselineNote} <a href="#" class="cam-confidence-help" onclick="window.CAM.showAboutModal('cam-confidence-explainer'); return false;" title="What does this mean?">?</a></div>`;
    }

    // analysis_completeness display (Step 192)
    const completeness = r.analysis_completeness || {};
    const cStatus = completeness.status || '';
    let completenessHtml = '';
    if (cStatus === 'COMPLETE') {
        completenessHtml = `<div class="analysis-completeness completeness-complete">
            &#10003; Full document coverage confirmed
        </div>`;
    } else if (cStatus === 'GAPS_RESOLVED') {
        const repaired = completeness.gaps_resolved_by_reextraction || 0;
        // Only show if something was actually repaired — zero is noise
        if (repaired > 0) {
            completenessHtml = `<div class="analysis-completeness completeness-resolved">
                &#10003; ${repaired} subsection${repaired !== 1 ? 's' : ''} recovered via targeted re-extraction
            </div>`;
        }
    } else if (cStatus === 'GAPS_UNRESOLVED') {
        const remaining = completeness.gaps_remaining || 0;
        completenessHtml = `<div class="analysis-completeness completeness-unresolved">
            &#9888; ${remaining} section${remaining !== 1 ? 's' : ''} could not be fully extracted
            &mdash; manual review recommended
        </div>`;
    }

    // Step 125: Deal overview table above hero
    const dealOverviewHtml = buildDealOverviewTable(r);

    const isCollapsed = !!contractSummaryCollapseState[currentTenantIndex];
    const compactParties = [landlord ? `Landlord: ${esc(landlord)}` : "", tenantName ? `Tenant: ${esc(tenantName)}` : ""]
        .filter(Boolean)
        .join("  •  ");

    container.innerHTML = `
        <button type="button" class="contract-summary-toggle${isCollapsed ? ' is-collapsed' : ''}"
            onclick="window.CAM.toggleContractSummaryCollapse(${currentTenantIndex}); return false;">
            <span class="contract-summary-toggle-text">Contract Overview</span>
            <span class="contract-summary-toggle-icon">${isCollapsed ? '&#9656;' : '&#9662;'}</span>
        </button>
        <div class="contract-summary-compact${isCollapsed ? '' : ' hidden'}">${compactParties || esc(headline)}</div>
        <div id="contract-summary-body" class="contract-summary-body${isCollapsed ? ' hidden' : ''}">
            ${dealOverviewHtml}<div class="contract-hero">
                <div class="contract-headline">${esc(headline)}</div>
                ${sublines.length ? `<div class="contract-subline">${sublines.join("<br>")}</div>` : ""}
                ${chipsHtml}
                ${camConfidenceHtml}
                ${completenessHtml}
                <div class="contract-footer">${footerParts.join(" &middot; ")}</div>
            </div>
        </div>`;

    // Wire up "View in context" links in contract summary
    container.querySelectorAll(".docview-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.stopPropagation();
            e.preventDefault();
            jumpToDocview(link.dataset.pid);
        });
    });

    // Wire up clickable risk headline chips (6c)
    container.querySelectorAll(".risk-headline-chip[data-pid]").forEach(chip => {
        chip.style.cursor = "pointer";
        chip.addEventListener("click", () => {
            jumpToFinding(chip.dataset.pid);
        });
    });
}

function toggleContractSummaryCollapse(tenantIdx) {
    const idx = Number.isInteger(tenantIdx) ? tenantIdx : currentTenantIndex;
    contractSummaryCollapseState[idx] = !contractSummaryCollapseState[idx];
    const body = document.getElementById("contract-summary-body");
    const toggle = document.querySelector(".contract-summary-toggle");
    const compact = document.querySelector(".contract-summary-compact");
    const aiComment = document.getElementById("contract-ai-comment");
    if (body) body.classList.toggle("hidden", !!contractSummaryCollapseState[idx]);
    if (compact) compact.classList.toggle("hidden", !contractSummaryCollapseState[idx]);
    if (aiComment) aiComment.classList.toggle("hidden", !!contractSummaryCollapseState[idx] || !aiComment.innerHTML.trim());
    if (toggle) {
        toggle.classList.toggle("is-collapsed", !!contractSummaryCollapseState[idx]);
        const icon = toggle.querySelector(".contract-summary-toggle-icon");
        if (icon) icon.innerHTML = contractSummaryCollapseState[idx] ? "&#9656;" : "&#9662;";
    }
}

// ── Per-Contract AI Comment ──

async function renderContractAIComment(tenantIdx) {
    var el = document.getElementById('contract-ai-comment');
    if (!el || !currentResults) return;

    var tenant = currentResults.tenants[tenantIdx];
    if (!tenant || !tenant.results) { el.classList.add('hidden'); return; }

    // Cache per tenant
    if (tenant._aiComment) {
        el.innerHTML = tenant._aiComment;
        el.classList.toggle('hidden', !!contractSummaryCollapseState[tenantIdx]);
        return;
    }

    var r = tenant.results;
    var summary = r.summary || {};
    var provisions = r.provisions || [];
    var deviations = provisions.filter(function(p) { return p.final_verdict === 'DEVIATES'; });
    var name = formatTenantName(tenant.filename || 'this lease');

    // Show loading state
    el.innerHTML = '<span class="contract-ai-comment-loading">&#x2728; Analyzing&hellip;</span>';
    el.classList.toggle('hidden', !!contractSummaryCollapseState[tenantIdx]);

    // Build compact context
    var devList = deviations.map(function(d) {
        return (d.provision_id || '') + ' ' + (d.provision_name || '') + ' (' + (d.severity || 'MEDIUM') + ')'
            + (d.risk_headline ? ': ' + d.risk_headline : '');
    }).join('\n');

    // Step 183: CAM confidence note for per-contract AI comment
    var camNote = '';
    var uncertain183 = 0;
    var camSumm = tenant && tenant.results ? tenant.results.cam_contract_summary : null;
    if (camSumm) {
        var withhold183 = (camSumm.governance_counts && camSumm.governance_counts.WITHHOLD_SIGNAL) || 0;
        var reviewSig183 = (camSumm.governance_counts && camSumm.governance_counts.REVIEW_SIGNAL) || 0;
        uncertain183 = withhold183 + reviewSig183;
        var total183 = camSumm.provisions_scored || 0;
        if (uncertain183 > 0) {
            camNote = '\n\nNote: ' + uncertain183 + ' of ' + total183 + ' clause evaluations had lower AI confidence.';
        }
    }

    var prompt;
    var confInstruction183;
    if (deviations.length === 0) {
        confInstruction183 = uncertain183 > 0 ? " If the note mentions lower-confidence clauses, add a second sentence mentioning this." : "";
        prompt = 'You are summarizing a single commercial lease analysis for a lawyer. Write exactly 1 plain-English sentence stating that this lease fully conforms to the standard template across all provisions reviewed. Do not recommend signing or any action. Do not mention AI or analysis pipelines. Do not use the words \'tenant\' or \'landlord\' or name the lease.' + confInstruction183 + camNote;
    } else {
        confInstruction183 = uncertain183 > 0 ? " If the note above mentions lower-confidence clauses, add a brief third sentence: 'Note that [N] clause(s) had lower AI confidence and should be reviewed carefully.'" : "";
        prompt = 'You are summarizing a single commercial lease analysis for a lawyer. Write exactly 2 plain-English sentences. Sentence 1: state the number of deviations found and the highest severity level. Sentence 2: identify the most significant risk (the highest-severity provision) and briefly explain what changed. Do not recommend signing, rejecting, or revising. Do not give legal advice. Do not use bullet points. Do not mention AI or analysis pipelines. Do not name the lease or tenant.' + confInstruction183 + '\n\nFindings:\n' + devList + camNote;
    }

    try {
        var resp = await fetch('/api/ai-summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt, job_id: currentJobId }),
        });
        var data = await resp.json();
        var text = data.summary || '';
        if (text) {
            var escaped = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            var html = '<span class="contract-ai-comment-icon">&#x2728;</span><span class="contract-ai-comment-text">' + escaped + '</span>';
            el.innerHTML = html;
            tenant._aiComment = html;
            el.classList.toggle('hidden', !!contractSummaryCollapseState[tenantIdx]);
        } else {
            el.classList.add('hidden');
        }
    } catch (err) {
        el.classList.add('hidden');
        console.error('Contract AI comment error:', err);
    }
}

// ── Model Name Helpers ──

function getModelDisplayName(modelId) {
    return MODEL_DISPLAY_NAMES[modelId] || modelId || "Unknown Model";
}

function getEvaluatorNames(modelsUsed) {
    return {
        A: {
            name: getModelDisplayName(modelsUsed.evaluator_a),
            fallback: modelsUsed.evaluator_a_fallback || false,
        },
        B: {
            name: getModelDisplayName(modelsUsed.evaluator_b),
            fallback: modelsUsed.evaluator_b_fallback || false,
        },
        C: {
            name: getModelDisplayName(modelsUsed.evaluator_c),
            fallback: modelsUsed.evaluator_c_fallback || false,
        },
    };
}

function getProviderShortNames(modelsUsed) {
    const names = getEvaluatorNames(modelsUsed);
    const companies = new Set();
    Object.values(names).forEach(obj => {
        const n = obj.name || obj;
        const match = n.match(/\(([^)]+)\)/);
        if (match) companies.add(match[1]);
    });
    return Array.from(companies);
}

// ── Cross-Reference Linking ──

/**
 * Render detail text with paragraph splitting and bold markdown.
 * Splits on \n\n into paragraphs, converts **bold** to <strong>, wraps in <p> tags.
 * Formatting is produced by the models — this just renders it.
 */
function formatDetailMarkdown(text) {
    if (!text) return "";
    const normalized = String(text).replace(/\r\n?/g, "\n").trim();
    if (!normalized) return "";
    return normalized
        .split(/\n{2,}/)
        .map((block) => {
            const strongTokens = [];
            const withTokens = block.trim().replace(/\*\*(.+?)\*\*/g, (_, content) => {
                const idx = strongTokens.length;
                strongTokens.push(content);
                return `%%DETAIL_STRONG_${idx}%%`;
            });
            let escaped = esc(withTokens)
                .replace(/\n/g, "<br>");
            strongTokens.forEach((content, idx) => {
                escaped = escaped.replace(`%%DETAIL_STRONG_${idx}%%`, `<strong>${esc(content)}</strong>`);
            });
            return escaped ? `<p>${escaped}</p>` : "";
        })
        .join("");
}

function renderDetailText(text) {
    return formatDetailMarkdown(text);
}

function hydrateRenderedDetailMarkdown(root) {
    if (!root) return;
    root.querySelectorAll(".detail-text:not(.interpretation-note-body)").forEach((el) => {
        if (!el) return;
        if (el.querySelector("strong")) return;
        const raw = el.textContent || "";
        if (!raw.includes("**")) return;
        el.innerHTML = renderDetailText(raw);
    });
}

function linkifyProvisions(text, analyzedPids, currentPid) {
    if (!text) return "";
    // Escape first, then replace LP-XX patterns
    let html = esc(text);
    html = html.replace(/LP-\d{2}/g, (match) => {
        if (match === currentPid) return match; // Don't link to self
        if (analyzedPids.has(match)) {
            return `<span class="provision-link" data-pid="${match}">${match}</span>`;
        }
        return `<span class="provision-link-unanalyzed" title="This provision was not included in the analysis. Re-run with ${match} selected to see full impact.">${match} (not analyzed)</span>`;
    });
    return html;
}

function detectCascadeRefs(d, analyzedPids) {
    // Look for LP-XX references in key text fields (excluding self)
    const pid = d.provision_id || "";
    const fields = [
        d.challenge_details, d.severity_reasoning, d.financial_impact,
        d.recommended_action, d.cascade_analysis,
    ].filter(Boolean).join(" ");
    const refs = new Set();
    const matches = fields.match(/LP-\d{2}/g) || [];
    matches.forEach(m => { if (m !== pid) refs.add(m); });
    return Array.from(refs);
}


// ── Deviation Rendering ──

function renderDeviations(provisions, modelsUsed, tenantIdx, discoveries) {
    // Build a map: provision_id → [discovery items that belong to it]
    const discByProvision = {};
    const discStandalone = (discoveries && discoveries.standalone) || [];
    for (const disc of discStandalone) {
        const lps = disc.unique_suggested_lps || [];
        for (const lp of lps) {
            if (!discByProvision[lp]) discByProvision[lp] = [];
            discByProvision[lp].push(disc);
        }
    }

    const container = $("#deviations-list");
    const deviations = getDeviationWorkflowProvisions(provisions, tenantIdx)
        .sort((a, b) => {
            const ai = SEVERITY_ORDER.indexOf(a.severity);
            const bi = SEVERITY_ORDER.indexOf(b.severity);
            return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
        });

    const header = $("#deviations-header");
    header.textContent = "Deviations \u2014 Review Recommended";

    const progressEl = document.getElementById("resolution-progress");
    if (progressEl) progressEl.remove();

    if (deviations.length === 0) {
        container.innerHTML = '<div class="alert alert-success">No deviations detected. All analyzed provisions conform to the reference lease.</div>';
        return;
    }

    const evalNames = getEvaluatorNames(modelsUsed);

    // Build set of all analyzed provision IDs
    const analyzedPids = new Set(provisions.map(p => p.provision_id).filter(Boolean));

    container.innerHTML = deviations.map(d => {
        const pid = d.provision_id || "";
        const pname = d.provision_name || "";
        const sev = d.severity || "";
        const sectionRef = d.tenant_section_ref || "";
        const icon = SEVERITY_ICONS[sev] || "";

        const challenge = d.challenge_details || "";
        const riskHeadline = d.risk_headline || "";
        const action = d.recommended_action || "";

        const credibilityLine = renderCredibilityLine(d, modelsUsed, tenantIdx, pid, sev);

        // Linkify cross-references
        const lChallenge = linkifyProvisions(challenge, analyzedPids, pid);
        const lAction = linkifyProvisions(action, analyzedPids, pid);

        // Cascade badge
        const cascadeRefs = detectCascadeRefs(d, analyzedPids);
        const cascadeBadge = cascadeRefs.length > 0
            ? `<span class="cascade-badge">\uD83D\uDD17 Affects ${cascadeRefs.join(", ")}</span>`
            : "";

        // Template vs tenant language blocks (shown in card-summary)
        const templateText = d.template_text || "";
        const tenantText = d.tenant_text || "";
        const hasDeviation = d.final_verdict === "DEVIATES";

        let languageHtml = "";
        if (templateText || tenantText) {
            const isDeviates = d.final_verdict === "DEVIATES";
            const isAdded    = !templateText && tenantText;
            const isRemoved  = templateText && !tenantText;
            const isModified = templateText && tenantText && isDeviates;

            if (isAdded) {
                languageHtml = `
                <div class="finding-language-pair">
                    <div class="finding-language finding-language--added">
                        <div class="finding-language-label finding-language-label--added">
                            \u2795 Inserted by tenant — not present in standard template
                        </div>
                        <div class="finding-language-text finding-language-text--added">${esc(tenantText)}</div>
                    </div>
                </div>`;
            } else if (isRemoved) {
                languageHtml = `
                <div class="finding-language-pair">
                    <div class="finding-language finding-language--removed">
                        <div class="finding-language-label finding-language-label--removed">
                            Reference Lease — omitted from tenant lease
                        </div>
                        <div class="finding-language-text finding-language-text--removed">${esc(templateText)}</div>
                    </div>
                    <div class="finding-language finding-language--removed-placeholder">
                        <div class="finding-language-label">Tenant Lease</div>
                        <div class="finding-language-text finding-language-text--removed-placeholder">
                            This provision was omitted from the tenant's lease.
                        </div>
                    </div>
                </div>`;
            } else if (isModified) {
                const { templateHtml, tenantHtml } = computeWordDiff(templateText, tenantText);
                languageHtml = `
                <div class="finding-language-pair finding-language-pair--diff">
                    <div class="finding-language">
                        <div class="finding-language-label">
                            Reference Lease
                            <span class="diff-legend diff-legend--removed">removed</span>
                        </div>
                        <div class="finding-language-text finding-language-text--template-diff">${templateHtml}</div>
                    </div>
                    <div class="finding-language finding-language--modified">
                        <div class="finding-language-label finding-language-label--modified">
                            Tenant Lease
                            <span class="diff-legend diff-legend--added">added</span>
                        </div>
                        <div class="finding-language-text finding-language-text--tenant-diff">${tenantHtml}</div>
                    </div>
                </div>`;
            } else {
                languageHtml = `
                <div class="finding-language-pair">
                    ${templateText ? `<div class="finding-language">
                        <div class="finding-language-label">Reference Lease</div>
                        <div class="finding-language-text">${esc(templateText)}</div>
                    </div>` : ""}
                    ${tenantText ? `<div class="finding-language">
                        <div class="finding-language-label">Tenant Lease</div>
                        <div class="finding-language-text">${esc(tenantText)}</div>
                    </div>` : ""}
                </div>`;
            }
        }

        // Cascade source callout (Item 4b)
        const cascadeSource = d.cascade_source;
        let cascadeSourceHtml = "";
        if (cascadeSource && cascadeSource.term) {
            const csSection = cascadeSource.defined_in || "";
            cascadeSourceHtml = `<div class="cascade-source-callout">
                <span>\uD83D\uDCCC Key definition: "${esc(cascadeSource.term)}"${csSection ? ` &mdash; ${esc(csSection)}` : ""}</span>
                ${csSection ? `<a class="cascade-source-link" data-section="${esc(csSection)}">Click to view in document &#8594;</a>` : ""}
            </div>`;
        }

        // Item 6: UNCLEAR → "Needs Review" styling
        const isUnclear = d.final_verdict === "UNCLEAR";
        const displaySev = isUnclear ? "Needs Review" : sevDisplay(sev);
        const displayIcon = isUnclear ? "\u2753" : icon;
        const sevClass = isUnclear ? "severity-review" : `severity-${sev}`;

        const discoveredBadge = d.discovered
            ? `<span class="discovered-badge">\uD83D\uDD0D Unique</span>`
            : "";

        // Step 186: notedCls needed by resolution bar below
        const notedCls = isNoted(tenantIdx, pid) ? " noted-active" : "";

        // Resolution bar — look up current state for this card
        const resKey = `${tenantIdx}:${pid}`;
        const res = resolutionState[resKey] || { status: "open", notes: [] };
        const resStatus = res.status || "open";
        const resNotes = res.notes || [];
        const lastNote = resNotes.length > 0 ? resNotes[resNotes.length - 1] : null;
        const noteCount = resNotes.length;
        const noteCountHtml = noteCount > 0
            ? `<span class="res-note-count">${noteCount} note${noteCount > 1 ? "s" : ""}</span>`
            : "";

        const statusDefs = [
            { key: "open",       label: "Open",               cls: "res-open"     },
            { key: "in_review",  label: "In Review",           cls: "res-inreview" },
            { key: "escalated",  label: "Escalate to Client",  cls: "res-escalated"},
            { key: "not_a_deviation", label: "Not a Deviation", cls: "res-notdeviation" },
            { key: "resolved",   label: "Resolved",           cls: "res-resolved" },
        ];
        const statusPillsHtml = statusDefs.map(s =>
            `<button class="res-pill ${s.cls}${resStatus === s.key ? " res-pill-active" : ""}"
                     data-status="${s.key}" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}"
                     onclick="window.CAM.setResolutionStatus('${esc(pid)}', ${tenantIdx}, '${s.key}', this)">
                 ${s.label}
             </button>`
        ).join("");

        const workflowActionsHtml = `
            <div class="workflow-open-actions workflow-group">
                <a class="docview-link card-docview-link card-docview-link--btn" data-pid="${esc(pid)}">Open Document Comparison</a>
                <a class="card-audit-link card-audit-link--btn"
                   href="#"
                   onclick="window.CAM.jumpToAuditProvision(${tenantIdx}, '${esc(pid)}'); return false;"
                   title="View full CAM analysis in Audit Trail">
                    Open CAM Audit Trail
                </a>
                ${window.CAMShared.buildCoverageGapLink(pid, ((currentResults.tenants[tenantIdx]||{}).results||{}).coverage_assessment, esc)}
            </div>
        `;

        let draftDecisionControlsHtml = "";
        if (d.final_verdict === 'DEVIATES') {
            const dec = getFinalDraftDecision(tenantIdx, pid);
            const activeChoice = dec ? dec.choice : null;
            const hasSavedCustom = activeChoice === 'custom' && dec && dec.text;
            const modifyLabel = hasSavedCustom ? 'Keep Modified \u2713' : 'Modify\u2026';
            draftDecisionControlsHtml = `
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
                    onclick="window.CAM.finalDraftModify(${tenantIdx}, '${esc(pid)}'); event.stopPropagation();">
                    ${modifyLabel}
                </button>
            `;
        }

        const resolutionBarHtml = `
        <div class="resolution-bar summary-resolution-bar" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}">
            <div class="res-status-row finding-workflow-row">
                <div class="workflow-group workflow-group-status">
                    <span class="res-label">Status:</span>
                    <div class="res-pills">${statusPillsHtml}</div>
                    <span class="summary-pipe" aria-hidden="true"></span>
                    <span class="res-tools-label">Tools:</span>
                    <button class="res-notes-toggle" onclick="window.CAM.toggleResolutionNotes('${esc(pid)}', ${tenantIdx})"
                            data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}">
                        \uD83D\uDCDD Notes${noteCountHtml ? " " + noteCountHtml : ""}
                    </button>
                    <button class="res-advisor-btn" onclick="window.CAM.openResolutionAdvisor('${esc(pid)}', ${tenantIdx})">
                        \uD83D\uDCA1 AI Advisor
                    </button>
                </div>
                ${draftDecisionControlsHtml ? `<div class="workflow-group workflow-group-decision">${draftDecisionControlsHtml}</div>` : ""}
                ${workflowActionsHtml}
            </div>
            <div class="res-notes-panel hidden" id="res-notes-${esc(pid)}-${tenantIdx}">
                ${resNotes.map((n, noteIdx) => `
                    <div class="res-note-entry">
                        <span class="res-note-ts">${formatResTimestamp(n.timestamp)}</span>
                        <span class="res-note-text">${esc(n.text)}</span>
                        <button class="res-note-delete" onclick="window.CAM.deleteResolutionNote('${esc(pid)}', ${tenantIdx}, ${noteIdx}); event.stopPropagation();">Delete</button>
                    </div>`).join("")}
                <div class="res-note-input-row">
                    <textarea class="res-note-input" id="res-input-${esc(pid)}-${tenantIdx}"
                              placeholder="Add a note\u2026 (saved on blur or Enter+Shift)" rows="2"></textarea>
                    <button class="res-note-save-btn"
                            onclick="window.CAM.saveResolutionNote('${esc(pid)}', ${tenantIdx})">Save</button>
                </div>
            </div>
        </div>`;

        const resolvedCls = (resStatus === "resolved" || resStatus === "not_a_deviation") ? " resolution-resolved" : "";
        const govSig184 = d.cam_score ? (d.cam_score.governance_signal || '') : '';
        const _confBadgeData = window.CAMAuditShared.getConfidenceBadgeData ? window.CAMAuditShared.getConfidenceBadgeData(govSig184, (sev || "").toUpperCase()) : null;
        const _needsReviewTag = _confBadgeData && _confBadgeData.needsReview
            ? `<span class="cam-confidence-needs-review">Needs Review</span>` : "";
        const confidenceBadgeHtml = _confBadgeData
            ? `<span class="cam-confidence-badge ${_confBadgeData.cssClass}${_confBadgeData.needsReview ? ' needs-review-combo' : ''}"><span class="cam-confidence-dots">${_confBadgeData.dots}</span>${_confBadgeData.label}${_needsReviewTag}</span>`
            : "";
        const expandedCls = (resStatus === "resolved" || resStatus === "not_a_deviation") ? "" : " card-expanded";
        return `<div class="finding-card ${sevClass}${resolvedCls}${expandedCls}" id="dev-${pid}" data-provision="${esc(pid)}" data-severity="${esc(sev)}" data-tenant-idx="${tenantIdx}" data-confidence="${esc(govSig184)}">
            <div class="deviation-header">
                <div class="deviation-header-main">
                    <div class="deviation-header-left">
                        <span class="provision-title">${esc(pid)} ${esc(pname)}</span>
                        <span class="severity-badge ${sevClass}">${displayIcon} ${displaySev}</span>
                        ${confidenceBadgeHtml}
                        ${credibilityLine}
                        ${discoveredBadge}
                    </div>
                    <div class="deviation-header-right">
                        ${sectionRef ? `<span class="section-ref">${esc(sectionRef)}</span>` : ""}
                    </div>
                </div>
                <div class="deviation-header-actions">
                    <button class="finding-read-toggle${notedCls}"
                            title="Mark this provision as read"
                            onclick="window.CAM.toggleNoted(${tenantIdx}, '${esc(pid)}', this); event.stopPropagation();">
                        ${isNoted(tenantIdx, pid) ? "\u2713 Read" : "Mark as Read"}
                    </button>
                    <span class="finding-collapse-indicator" aria-hidden="true"></span>
                </div>
            </div>
            ${cascadeBadge ? `<div style="padding:0.25rem 1rem;">${cascadeBadge}</div>` : ""}
            ${cascadeSourceHtml}
            <div class="card-summary">
                ${riskHeadline ? `<div class="risk-headline">${esc(riskHeadline)}</div>` : ""}
                ${languageHtml}
                ${(challenge || action) ? `<div class="detail-two-col">
                    ${challenge ? `<div class="detail-section">
                        <div class="detail-label">What Changed</div>
                        <div class="detail-text">${renderDetailText(challenge)}</div>
                    </div>` : ""}
                    ${action ? `<div class="detail-section">
                        <div class="detail-label">Why It Matters</div>
                        <div class="detail-text">${renderDetailText(action)}</div>
                    </div>` : ""}
                </div>` : ""}
                ${d.interpretation_note ? (() => {
                    const _boldMd = window.CAMAuditShared && window.CAMAuditShared.boldMarkdown
                        ? window.CAMAuditShared.boldMarkdown
                        : (t) => (t || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
                    const _renderNote = (text) => {
                        const paras = text.split(/\n\n+/).map(p => p.trim()).filter(Boolean);
                        if (paras.length <= 1) return `<p>${_boldMd(text)}</p>`;
                        return paras.map(p => `<p>${_boldMd(p)}</p>`).join("");
                    };
                    return `<div class="detail-section interpretation-note-section">
                        <div class="detail-label">Interpretation Note</div>
                        <div class="detail-text interpretation-note-body">${_renderNote(d.interpretation_note)}</div>
                    </div>`;
                })() : ""}
            </div>
            ${resolutionBarHtml}
            ${d.final_verdict === 'DEVIATES' ? (() => {
                const dec = getFinalDraftDecision(tenantIdx, pid);
                const activeChoice = dec ? dec.choice : null;
                return `
                <div class="fd-modify-panel${activeChoice === 'custom' ? '' : ' hidden'}">
                    <div class="fd-modify-cols">
                        <div class="fd-modify-col">
                            <div class="fd-modify-col-label">Reference</div>
                            <div class="fd-modify-col-text">${esc(d.template_text || '\u2014')}</div>
                        </div>
                        <div class="fd-modify-col">
                            <div class="fd-modify-col-label">Tenant</div>
                            <div class="fd-modify-col-text">${esc(d.tenant_text || '\u2014')}</div>
                        </div>
                    </div>
                    <textarea class="fd-modify-textarea" rows="4"
                        placeholder="Type your draft text here, or use Smart Draft in Chat\u2026">${dec && dec.choice === 'custom' ? esc(dec.text) : ''}</textarea>
                    <div class="fd-modify-actions">
                        <button class="fd-ai-draft-btn"
                            onclick="window.CAM.fdOpenChatDraft(${tenantIdx}, '${esc(pid)}', 'custom'); event.stopPropagation();">
                            \u2728 Smart Draft in Chat
                        </button>
                        <button class="fd-note-btn"
                            onclick="window.CAM.fdSaveAsNote(${tenantIdx}, '${esc(pid)}'); event.stopPropagation();">
                            Save as Note
                        </button>
                        <button class="fd-clear-btn"
                            onclick="window.CAM.fdClear(${tenantIdx}, '${esc(pid)}'); event.stopPropagation();">
                            Clear
                        </button>
                        <button class="fd-save-open-btn"
                            onclick="window.CAM.fdSave(${tenantIdx}, '${esc(pid)}', false); event.stopPropagation();">
                            Save Leave Open
                        </button>
                        <button class="fd-save-btn"
                            onclick="window.CAM.fdSave(${tenantIdx}, '${esc(pid)}', true); event.stopPropagation();">
                            Save & Resolve
                        </button>
                    </div>
                </div>`;
            })() : ''}
            ${buildNotableClausesHtml(discByProvision[pid] || [], pid, modelsUsed, d)}
        </div>`;
    }).join("");

    // Wire up header click to toggle card open/close (for resolution bar etc)
    container.querySelectorAll(".finding-card .deviation-header").forEach(header => {
        header.addEventListener("click", () => {
            header.closest(".finding-card").classList.toggle("card-expanded");
        });
    });

    // Wire up cross-reference links
    container.querySelectorAll(".provision-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.stopPropagation();
            const targetPid = link.dataset.pid;
            const targetCard = document.getElementById(`dev-${targetPid}`);
            if (targetCard) {
                targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                targetCard.classList.add("highlight-flash");
                setTimeout(() => targetCard.classList.remove("highlight-flash"), 1500);
            }
        });
    });

    // Wire up "View in document comparison" links
    container.querySelectorAll(".docview-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.stopPropagation();
            e.preventDefault();
            jumpToDocview(link.dataset.pid);
        });
    });

    // Wire up cascade source links
    container.querySelectorAll(".cascade-source-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.stopPropagation();
            // Switch to doc view and search for the section reference
            switchResultsTab("docview");
            const sectionText = link.dataset.section || "";
            setTimeout(() => {
                const searchInput = $("#docview-search-input");
                if (searchInput && sectionText) {
                    searchInput.value = sectionText;
                    performDocSearch(sectionText);
                }
            }, 200);
        });
    });
}

// ── Credibility Line (1F) ──

function renderCredibilityLine(d, modelsUsed, tenantIdx, pid, sev) {
    const verdicts = d.evaluator_verdicts || {};
    const agreeing = Object.values(verdicts).filter(v => v === "DEVIATES").length;
    const total = Object.keys(verdicts).length || 3;

    const agreementText = `${agreeing}/${total} evaluators agree`;
    const label = agreementText + " \u2192";

    const colorCls = {
        'CRITICAL': 'credibility-critical',
        'HIGH':     'credibility-high',
        'MEDIUM':   'credibility-medium',
        'LOW':      'credibility-low',
    }[sev] || 'credibility-low';

    return `<a class="credibility-line credibility-link ${colorCls}"
               href="#"
               title="View full evaluator analysis in Audit Trail"
               onclick="window.CAM.jumpToAuditProvision(${tenantIdx}, '${pid}'); return false;"
            >${label}</a>`;
}

// ── Evaluator Panels (1B) ──

function renderEvaluatorPanels(d, evalNames) {
    const reasoning = d.evaluator_reasoning;
    const verdicts = d.evaluator_verdicts || {};
    const confidences = d.evaluator_confidences || {};

    if (!reasoning || typeof reasoning === "string") return "";

    const keys = ["A", "B", "C"];
    const panels = keys.map(key => {
        const nameStr = (evalNames[key] && evalNames[key].name) || `Evaluator ${key}`;
        const isFallback = evalNames[key] && evalNames[key].fallback;
        const fallbackBadge = isFallback
            ? ` <span class="fallback-note" title="Primary model unavailable — fallback used">↩ fallback</span>`
            : "";
        const verdict = verdicts[key] || "";
        const reason = reasoning[key] || "";
        const colorClass = EVALUATOR_COLORS[key] || "eval-blue";

        if (!reason) return "";

        return `<div class="evaluator-card ${colorClass}">
            <div class="evaluator-card-header">
                <span class="evaluator-name">${esc(nameStr)}${fallbackBadge}</span>
                <span class="evaluator-verdict verdict-${verdict}">${esc(verdict)}</span>
            </div>
            <div class="evaluator-card-body">${esc(reason)}</div>
        </div>`;
    }).filter(Boolean);

    if (panels.length === 0) return "";

    return `<div class="evaluator-analysis-section">
        <div class="evaluator-analysis-header">Independent Evaluator Analysis</div>
        <div class="evaluator-analysis-intro">Three AI models from different providers independently analyzed this provision without seeing each other's work.</div>
        <div class="evaluator-panels">${panels.join("")}</div>
    </div>`;
}

// ── Pipeline Stages (1C) ──

function renderPipelineStages(d, modelsUsed) {
    const meta = d.cam_metadata || {};
    const stagesRun = meta.stages_run || [];
    const rulesFired = meta.rules_fired || [];
    const verdict = d.final_verdict || "";
    const severity = d.severity || "";
    const providers = getProviderShortNames(modelsUsed);

    const allStages = [1, 2, 3, 4, 5, 6];
    const lines = allStages.map(stage => {
        const ran = stagesRun.includes(stage);
        const info = STAGE_DESCRIPTIONS[stage] || { name: `Stage ${stage}`, desc: "" };
        let icon = ran ? "\u2705" : "\u23ED\uFE0F";
        let extra = "";

        if (stage === 2 && ran) {
            extra = providers.length > 0 ? ` (${providers.join(", ")})` : "";
        } else if (stage === 3 && !ran) {
            extra = " \u2014 Skipped (unanimous agreement, no challenge needed)";
        } else if (stage === 4 && ran) {
            extra = rulesFired.length > 0
                ? ` \u2014 ${rulesFired.length} detection rule${rulesFired.length > 1 ? "s" : ""} triggered`
                : "";
        } else if (stage === 5 && !ran) {
            extra = " \u2014 Skipped (conforms)";
        } else if (stage === 6 && ran) {
            extra = ` \u2014 Verdict: ${verdict}` + (severity && severity !== "CONFORMS" ? ` (${severity})` : "");
        }

        return `<div class="pipeline-stage ${ran ? "stage-ran" : "stage-skipped"}">
            <span class="stage-icon">${icon}</span>
            <span class="stage-name">${esc(info.name)}</span>
            <span class="stage-desc">${esc(info.desc)}${extra}</span>
        </div>`;
    });

    return `<div class="pipeline-section expandable">
        <button class="expandable-toggle" data-label="How This Was Analyzed">&#9654; How This Was Analyzed</button>
        <div class="expandable-content pipeline-content">${lines.join("")}</div>
    </div>`;
}

// ── Fragility Signals in Plain English (1D) ──
// Always renders all 8 rules (fired + unfired) in Detailed mode

function renderFragilitySignals(d) {
    const frag = d.fragility;
    if (!frag) return "";

    const signals = frag.signals || [];
    const totalRules = ALL_FRAGILITY_SIGNALS.length;
    const firedCount = signals.length;

    if (firedCount === 0 && !frag.fragile) return "";

    const allLines = ALL_FRAGILITY_SIGNALS.map(sig => {
        const fired = signals.includes(sig);
        const translation = FRAGILITY_TRANSLATIONS[sig] || sig;
        return `<div class="rule-line ${fired ? "rule-fired" : "rule-clear"}">
            <span>${fired ? "\u2705" : "\u2796"}</span>
            <span class="rule-name">${esc(sig.replace(/_/g, " "))}</span>
            <span class="rule-desc">\u2014 ${esc(translation)}</span>
        </div>`;
    });

    return `<div class="fragility-section">
        <div class="fragility-header">Detection Rules${firedCount > 0 ? ` \u2014 ${firedCount} Triggered` : ""}</div>
        <div class="fragility-rules">${allLines.join("")}</div>
    </div>`;
}

// ── Cross-Reference Warnings (Step 115) ──

function renderCrossReferenceWarnings(d) {
    const xref = d.cross_reference_links;
    if (!xref || !xref.linked_deviations || xref.linked_deviations.length === 0) return "";

    const items = xref.linked_deviations.map(ld => {
        return `<div class="crossref-item">
            <span class="crossref-term">${esc(ld.defined_term)}</span>
            <span class="crossref-arrow">\u2192</span>
            <span class="crossref-ref">See ${esc(ld.deviating_provision)} \u2014 <span class="sev-badge sev-${(ld.severity || "").toUpperCase()}">${esc(ld.severity)}</span></span>
            <div class="crossref-summary">${esc(ld.summary)}</div>
        </div>`;
    });

    return `<div class="crossref-section">
        <div class="crossref-header">\u26A0 Cross-Reference Warnings</div>
        <div class="crossref-note">${esc(xref.linkage_warning)}</div>
        <div class="crossref-items">${items.join("")}</div>
    </div>`;
}

// ── Confidence Display (1E) ──

function renderConfidences(d, evalNames) {
    const confidences = d.evaluator_confidences;
    const verdicts = d.evaluator_verdicts || {};
    if (!confidences) return "";

    const keys = ["A", "B", "C"];
    const lines = keys.map(key => {
        const name = (evalNames[key] && evalNames[key].name) || `Evaluator ${key}`;
        const conf = confidences[key];
        const verdict = verdicts[key] || "";
        if (conf === undefined) return "";
        const pct = Math.round(conf * 100);
        return `<div class="confidence-line">
            <span class="confidence-name">${esc(name)}</span>
            <span class="confidence-verdict verdict-${verdict}">${esc(verdict)}</span>
            <span class="confidence-bar-wrap">
                <span class="confidence-bar-fill" style="width:${pct}%"></span>
            </span>
            <span class="confidence-pct">${pct}%</span>
        </div>`;
    }).filter(Boolean);

    if (lines.length === 0) return "";

    return `<div class="confidence-section">
        <div class="confidence-header">Evaluator Confidence Scores</div>
        ${lines.join("")}
    </div>`;
}

// ── Expandable Sections ──

function renderExpandableAutoOpen(label, content) {
    if (!content) return "";
    return `<div class="expandable">
        <button class="expandable-toggle" data-label="${esc(label)}">&#9660; ${esc(label)}</button>
        <div class="expandable-content open">${esc(content)}</div>
    </div>`;
}

// ── Dissent Detection (042) ──

function getDissentingEvaluators(provision, evalNames) {
    // Returns array of {name, reasoning} for evaluators who said DEVIATES
    // on a provision that ultimately CONFORMS via challenger COSMETIC_ONLY
    if (
        provision.final_verdict !== "CONFORMS" ||
        provision.challenge_finding !== "COSMETIC_ONLY"
    ) return [];

    const verdicts = provision.evaluator_verdicts || {};
    const reasoning = provision.evaluator_reasoning || {};
    const dissenters = [];

    for (const key of ["A", "B", "C"]) {
        if (verdicts[key] === "DEVIATES") {
            const nameObj = evalNames[key];
            const name = (nameObj && nameObj.name) ? nameObj.name : `Evaluator ${key}`;
            dissenters.push({
                key,
                name,
                reasoning: reasoning[key] || "",
            });
        }
    }
    return dissenters;
}

// ── Conforming Provisions ──

function renderConforming(provisions, modelsUsed) {
    const list = $("#conforming-list");
    const conforming = provisions.filter(p => p.provision_id !== "LP-00" && p.final_verdict === "CONFORMS" && !isManualEscalatedProvision(p, currentTenantIndex));
    list.classList.add("hidden");
    $("#conforming-toggle").innerHTML = `&#9654; Conforming Provisions (${conforming.length})`;

    const providers = getProviderShortNames(modelsUsed);
    const evalNames = getEvaluatorNames(modelsUsed);

    ensureConformingConcernsLoaded();

    list.innerHTML = conforming.map(c => {
        const pid = c.provision_id || "";
        const detailId = `conf-detail-${pid}`;
        const concernState = getConformingConcernState(currentTenantIndex, pid);

        const discoveredTag = c.discovered
            ? ` <span class="discovered-inline">\uD83D\uDD0D</span>`
            : "";

        // Concern indicator on the summary line
        const concernBadge = concernState === "flag"
            ? ` <span style="font-size:0.7rem;background:#fee2e2;color:#991b1b;padding:0.0625rem 0.375rem;border-radius:0.1875rem;font-weight:600;">\u26A0 Flagged</span>`
            : concernState === "concern"
            ? ` <span style="font-size:0.7rem;background:#fef3c7;color:#92400e;padding:0.0625rem 0.375rem;border-radius:0.1875rem;font-weight:600;">\uD83D\uDCCB Concern noted</span>`
            : "";

        const summaryMeta = providers.length > 0 ? providers.join(", ") : "";
        const sectionRef = c.tenant_section_ref || c.template_section_ref || "";

        // Clause text pair
        const tmplText = c.template_text || "";
        const tenantText = c.tenant_text || "";
        const clausePairHtml = (tmplText || tenantText) ? `
            <div class="conforming-clause-pair">
                <div class="conforming-clause-col">
                    <div class="conforming-clause-label">Reference Lease</div>
                    <div class="conforming-clause-text">${esc(tmplText || "\u2014")}</div>
                </div>
                <div class="conforming-clause-col">
                    <div class="conforming-clause-label">Tenant Lease</div>
                    <div class="conforming-clause-text">${esc(tenantText || "\u2014")}</div>
                </div>
            </div>` : `<div style="font-size:0.8rem;color:var(--text-muted);padding:0.25rem 0;">Clause text not available — view in Audit Trail.</div>`;

        // Dissent detection (042)
        const dissenters = getDissentingEvaluators(c, evalNames);
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

        return buildConformingItem(c, {
            tenantIdx: currentTenantIndex,
            concernState,
            evalNames,
            summaryMeta,
        });
    }).join("") + `<li class="conforming-close-row">
        <button class="conforming-close-all-btn" onclick="window.CAM.collapseAllConforming(); return false;">&#9660; Close all</button>
    </li>`;

    // Wire up expand/collapse on conforming-main click
    list.querySelectorAll(".conforming-main").forEach(row => {
        row.addEventListener("click", e => {
            if (e.target.closest(".dissent-toggle, .conforming-concern-btn")) return;
            const detailId = row.dataset.detailId;
            const detail = document.getElementById(detailId);
            if (!detail) return;
            const isOpen = !detail.classList.contains("hidden");
            detail.classList.toggle("hidden", isOpen);
            const chevron = row.querySelector(".conforming-chevron");
            if (chevron) chevron.innerHTML = isOpen ? "&#9662;" : "&#9652;";
        });
    });

    // Wire up concern bar buttons
    list.querySelectorAll(".conforming-concern-btn").forEach(btn => {
        btn.addEventListener("click", e => {
            e.stopPropagation();
            const pid = btn.dataset.pid;
            const action = btn.dataset.action;
            const current = getConformingConcernState(currentTenantIndex, pid);
            if (action === "clear") {
                setConformingConcernEntry(currentTenantIndex, pid, "none");
            } else if (action === current) {
                setConformingConcernEntry(currentTenantIndex, pid, "none"); // toggle off
            } else if (action === "flag") {
                const provision = conforming.find(entry => entry.provision_id === pid);
                const reason = window.prompt(
                    "Optional reason for escalating this clause as a deviation:",
                    getConformingConcernReason(currentTenantIndex, pid)
                );
                if (reason === null) return;
                setConformingConcernEntry(currentTenantIndex, pid, "flag", reason);
                if (confirm("Create a rule so this is flagged automatically next time?")) {
                    window.CAM.showRuleCreationDialog(pid, (provision && provision.provision_name) || pid);
                }
            } else {
                setConformingConcernEntry(currentTenantIndex, pid, action);
            }
            // Re-render just this item's concern bar + badge
            // Full re-render is cleanest — re-call with same args
            renderConforming(provisions, modelsUsed);
            renderDeviations(provisions, modelsUsed, currentTenantIndex, currentDiscoveries || {});
            renderNavSidebar();
            if (contractDetailOpen && currentTenantIndex >= 0) {
                renderContractClauseFilterBar(provisions);
            }
            updateFinalDraftBar();
            applyContractClauseFilters();
            // Re-open the detail panel for this provision after re-render
            const newDetail = document.getElementById(`conf-detail-${pid}`);
            if (newDetail && action !== "flag") newDetail.classList.remove("hidden");
            const newChevron = list.querySelector(`li[data-pid="${pid}"] .conforming-chevron`);
            if (newChevron && action !== "flag") newChevron.innerHTML = "&#9652;";
            if (action === "flag") {
                setTimeout(() => jumpToFinding(pid), 50);
            }
        });
    });

    // Wire up dissent toggle clicks (042)
    list.querySelectorAll(".dissent-toggle").forEach(toggle => {
        toggle.addEventListener("click", e => {
            e.stopPropagation();
            const targetId = toggle.dataset.target;
            const panel = document.getElementById(targetId);
            if (!panel) return;
            const isOpen = !panel.classList.contains("hidden");
            panel.classList.toggle("hidden", isOpen);
            const chevron = toggle.querySelector(".dissent-chevron");
            if (chevron) chevron.innerHTML = isOpen ? "&#9662;" : "&#9652;";
        });
    });
}

function renderTenantDownloads(idx, filename) {
    return;
}

// ══════════════════════════════════════════════════════
// Results Tab Switching & Document Comparison View
// ══════════════════════════════════════════════════════

function jumpToDocview(pid) {
    docviewReturnTarget = pid;
    switchResultsTab("docview");
    waitForResultsTarget(() => {
        return document.getElementById(`fulldoc-${pid}`) ||
               document.querySelector(`.docview-provision-header[data-pid="${CSS.escape(pid)}"]`);
    }, { attempts: 18, delay: 90 }).then((target) => {
        if (!target) return;
        scrollDocviewTargetIntoView(target);
        flashResultsTarget(target, 1500);
    });
}

function jumpToProvisionOnActivePage(pid, tenantIdx) {
    const activeTenantIdx = typeof tenantIdx === "number" ? tenantIdx : currentTenantIndex;
    if (activeResultsTab === "docview") {
        jumpToDocview(pid);
        return;
    }
    if (activeResultsTab === "audittrail") {
        jumpToAuditProvision(activeTenantIdx, pid);
        return;
    }
    jumpToFinding(pid);
}

async function jumpToProvisionFromSidebar(pid, tenantIdx) {
    const activeTenantIdx = typeof tenantIdx === "number" ? tenantIdx : currentTenantIndex;
    if (activeResultsTab === 'audittrail' && contractDetailOpen && currentTenantIndex === activeTenantIdx) {
        jumpToAuditProvision(activeTenantIdx, pid);
        return;
    }
    await openContractDetail(activeTenantIdx);
    switchResultsTab('findings');
    await waitForResultsTarget(() =>
        document.getElementById('dev-' + pid) ||
        document.querySelector('[data-pid="' + CSS.escape(pid) + '"]')
    );
    jumpToFinding(pid);
}

// Show a "no contract selected" placeholder in the detail area
function showNoContractPlaceholder(tab) {
    activeTopTab = tab;
    activeResultsTab = tab;
    persistResultsViewState();
    if (!currentResults || !currentResults.tenants) {
        // No run loaded at all — show a helpful empty state instead of blank
        var _subLabels = { findings: 'Lease Summary', docview: 'Document Comparison', audittrail: 'Audit Trail' };
        setSubheader(_subLabels[tab] || tab);
        var detail = document.getElementById('contract-detail-view');
        var overview = document.getElementById('overview-tab-content');
        var contractsTab = document.getElementById('contracts-tab-content');
        if (overview) overview.classList.add('hidden');
        if (contractsTab) contractsTab.classList.add('hidden');
        if (detail) detail.classList.remove('hidden');
        setResultsContentDetailMode(true);
        var placeholder = document.getElementById('no-contract-placeholder');
        if (!placeholder) {
            placeholder = document.createElement('div');
            placeholder.id = 'no-contract-placeholder';
            if (detail) detail.appendChild(placeholder);
        }
        placeholder.classList.remove('hidden');
        placeholder.innerHTML = '<div class="ncp-inner">'
            + '<div class="ncp-icon">&#128196;</div>'
            + '<div class="ncp-title">No analysis loaded</div>'
            + '<div class="ncp-msg">Upload contracts to begin, or reload a previous run.</div>'
            + '</div>';
        return;
    }
    var tenants = currentResults.tenants;

    // Update subheader immediately
    var _subLabels = { findings: 'Lease Summary', docview: 'Document Comparison', audittrail: 'Audit Trail' };
    setSubheader(_subLabels[tab] || tab);

    // Single contract: auto-open immediately
    if (tenants.length === 1) {
        openContractDetail(0);
        return;
    }

    // Show detail area, hide overview + contracts tab
    var overview     = document.getElementById('overview-tab-content');
    var contractsTab = document.getElementById('contracts-tab-content');
    var detail       = document.getElementById('contract-detail-view');
    if (overview)     overview.classList.add('hidden');
    if (contractsTab) contractsTab.classList.add('hidden');
    if (detail)       detail.classList.remove('hidden');
    setResultsContentDetailMode(true);

    // Mark the clicked tab as active (no contract open)
    var tabNames = { findings: 'Lease Summary', docview: 'Document Comparison', audittrail: 'Audit Trail' };
    document.querySelectorAll('#top-tab-bar .top-tab[data-top-tab]').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('#top-tab-bar .top-tab[data-tab]').forEach(function(t) {
        t.classList.toggle('active', t.dataset.tab === tab);
    });

    // Clear tab content areas
    ['findings-tab', 'docview-tab', 'audittrail-tab'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });

    // Clear the detail header
    var headerEl = document.getElementById('contract-detail-header');
    if (headerEl) headerEl.innerHTML = '';

    // Show contract selector + contract-level filters before a contract is selected
    renderContractSelectorBar(null);

    // Render the placeholder message below the selector
    var placeholder = document.getElementById('no-contract-placeholder');
    if (!placeholder) {
        placeholder = document.createElement('div');
        placeholder.id = 'no-contract-placeholder';
        if (detail) detail.appendChild(placeholder);
    }
    placeholder.classList.remove('hidden');
    var label = tabNames[tab] || 'this view';
    placeholder.innerHTML = '<div class="ncp-inner">'
        + '<div class="ncp-icon">&#128196;</div>'
        + '<div class="ncp-title">No contract selected</div>'
        + '<div class="ncp-msg">Choose a contract from the dropdown above, or click <strong>Contracts</strong> to browse all contracts.</div>'
        + '</div>';
}

var TAB_SUBHEADER_LABELS = {
    findings:     'Contract Summary',
    docview:      'Document Comparison',
    audittrail:   'Audit',
    coverage:     'Key Issues',
    contractview: 'Contract View',
    evidence:     'Evidence',
    synthesis:    'Contract Interaction',
};

function setDocviewStickyControlsVisible(isVisible) {
    var controls = document.getElementById('docview-sticky-controls');
    if (!controls) return;
    controls.classList.toggle('hidden', !isVisible);
}

// Step 361: Evidence View focus state — set by navigation actions, null = standalone browse
window.evidenceFocus = null;

// ── Step 361: Evidence View as Targeted Proof Inspector ──

var _EV_VERDICT_CFG = {
    'explicitly_present':     { cls: 'ev-v-present',  label: 'Present' },
    'implicitly_present':     { cls: 'ev-v-implicit', label: 'Implicit' },
    'covered_by_default_law': { cls: 'ev-v-default',  label: 'Default Law' },
    'covered_in_other_LP':    { cls: 'ev-v-crosslp',  label: 'Cross-LP' },
    'missing':                { cls: 'ev-v-missing',  label: 'Missing' },
    'unclear':                { cls: 'ev-v-unclear',  label: 'Unclear' },
    'disputed':               { cls: 'ev-v-disputed', label: 'Disputed' },
};

var _currentEvBucket = '';

function _evBucketChip(bucket) {
    var labels = { risk: 'Risk', review_needed: 'Needs Review', improvement: 'Improvement', addressed: 'Addressed' };
    var clss = { risk: 'ev-bucket-risk', review_needed: 'ev-bucket-review', improvement: 'ev-bucket-improve', addressed: 'ev-bucket-addressed' };
    if (!bucket) return '';
    return '<span class="ev-bucket-chip ' + (clss[bucket] || 'ev-bucket-default') + '">' + esc(labels[bucket] || bucket) + '</span>';
}

function _evCoverageStateLabel(state) {
    var labels = {
        covered_favorable: 'Favorable', covered_unfavorable: 'Unfavorable',
        missing: 'Missing', partial: 'Partial', covered: 'Covered', unclear: 'Unclear',
    };
    return labels[state] || '';
}

function _findElementLabel(lp, elementId) {
    if (!lp || !elementId) return null;
    var evs = lp.element_verdicts || [];
    for (var i = 0; i < evs.length; i++) {
        if (evs[i].element_id === elementId) return evs[i].element_label || evs[i].element_id || null;
    }
    return null;
}

function _evToggleLp(safePid) {
    var body = document.getElementById('ev-lp-body-' + safePid);
    if (!body) return;
    var opening = body.style.display === 'none';
    body.style.display = opening ? '' : 'none';
    var group = body.parentElement;
    if (group) {
        var arrow = group.querySelector('.ev-lp-arrow');
        if (arrow) arrow.textContent = opening ? '▾' : '▸';
    }
}

function _evToggleCpf() {
    var body = document.getElementById('ev-cpf-body');
    var arrow = document.getElementById('ev-cpf-arrow');
    if (!body) return;
    var opening = body.style.display === 'none';
    body.style.display = opening ? '' : 'none';
    if (arrow) arrow.textContent = opening ? '▾' : '▸';
}

function _evGoBack(tabName) {
    window.evidenceFocus = null;
    switchResultsTab(tabName);
}

function _evFilter(searchText) {
    var lc = (searchText || '').toLowerCase();
    document.querySelectorAll('.ev-lp-group').forEach(function(group) {
        var text = (group.dataset.searchText || '').toLowerCase();
        var groupBucket = group.dataset.bucket || '';
        var matchSearch = !lc || text.indexOf(lc) >= 0;
        var matchBucket = !_currentEvBucket || groupBucket === _currentEvBucket;
        group.style.display = (matchSearch && matchBucket) ? '' : 'none';
    });
}

function _evSetFilter(bucket) {
    _currentEvBucket = bucket;
    document.querySelectorAll('.ev-filter-chip').forEach(function(chip) {
        chip.classList.toggle('ev-filter-active', chip.dataset.bucket === bucket);
    });
    var inp = document.getElementById('ev-search-input');
    _evFilter(inp ? inp.value : '');
}

function _navGoEvidenceFromContract(issueAreaId, elementId, findingId, sectionKey, actionBucket) {
    window.evidenceFocus = {
        origin: 'contract_view',
        origin_label: 'Contract View',
        issue_area_id: issueAreaId || null,
        element_id: elementId || null,
        finding_id: findingId || null,
        section_key: sectionKey || null,
        action_bucket: actionBucket || null,
    };
    switchResultsTab('evidence');
}

function _navGoEvidenceFromKeyIssues(issueAreaId, actionBucket) {
    window.evidenceFocus = {
        origin: 'key_issues',
        origin_label: 'Key Issues',
        issue_area_id: issueAreaId || null,
        element_id: null,
        finding_id: null,
        section_key: null,
        action_bucket: actionBucket || null,
    };
    switchResultsTab('evidence');
}

// Step 372D2-fix: shared render helper for CONTESTED citations. On a disputed /
// no-consensus element the merged citation is intentionally null (the merge declines
// to pick one), but the per-evaluator citations exist in disagreement_citations.
// Surface the cited section(s) framed honestly as CONTESTED — visually distinct from
// a clean consensus citation. Used by Key Issues + Evidence. Returns '' if nothing cited.
function contestedCitationHtml(disagreementCitations, opts) {
    opts = opts || {};
    if (!disagreementCitations || !disagreementCitations.length) return '';
    var secs = [];
    disagreementCitations.forEach(function(d) {
        var ref = d && d.citation && d.citation.section_ref;
        if (ref && secs.indexOf(ref) === -1) secs.push(ref);
    });
    if (!secs.length) return '';
    var firstQuote = (disagreementCitations[0].citation && disagreementCitations[0].citation.quote) || '';
    var secList = secs.join(', ');
    var perEval = disagreementCitations.map(function(d) {
        return (d.actual_label || d.role || '?') + ': ' + (d.verdict || '?')
             + ' (' + ((d.citation && d.citation.section_ref) || '—') + ')';
    }).join(' · ');
    var tip = 'Contested — evaluators cited ' + secList
            + ' but disagreed on whether it satisfies this element. ' + perEval;
    var label = secs.length === 1 ? ('Contested · ' + secs[0])
                                   : ('Contested · ' + secs.length + ' sections cited');
    var cls = 'cam-contested-cit' + (opts.style === 'block' ? ' cam-contested-cit-block' : '');
    return '<span class="' + cls + '" data-ref="' + esc(secs[0]) + '" data-quote="' + esc(firstQuote)
         + '" onclick="event.stopPropagation();window.CAM.jumpToEvidence(this.dataset.ref,this.dataset.quote)" title="'
         + esc(tip) + '">⚠ ' + esc(label) + '</span>';
}
window.CAM = window.CAM || {};
window.CAM.contestedCitationHtml = contestedCitationHtml;

function _buildElementRow(ev, safePid, highlighted) {
    var verdict = ev.verdict || 'unclear';
    var vcfg = _EV_VERDICT_CFG[verdict] || { cls: 'ev-v-unclear', label: verdict };
    var label = ev.element_label || ev.element_id || '?';
    var citation = ev.citation || {};
    var citRef = citation.section_ref || '';
    var citQuote = citation.quote || '';
    var evalVerdicts = ev.per_evaluator_verdicts || ev.evaluator_verdicts || [];
    // Step 364: missing + unclear minority → "Missing / Unclear"
    var hasUnclearMinority = verdict === 'missing' && evalVerdicts.some(function(evi) {
        return evi.verdict === 'unclear';
    });
    var vcLabel = hasUnclearMinority ? 'Missing / Unclear' : vcfg.label;
    var safeEid = (ev.element_id || label).replace(/[^a-zA-Z0-9_-]/g, '_');
    var evalPanelId = 'ev-ep-' + safePid + '-' + safeEid;

    // Step 361d: red border for missing/disputed, amber for unclear
    var problemClass = (verdict === 'missing' || verdict === 'disputed') ? ' ev-problem' :
                       (verdict === 'unclear') ? ' ev-problem-warn' : '';
    var html = '<div class="ev-elem-row' + (highlighted ? ' ev-elem-highlighted' : '') + problemClass + '">';
    html += '<div class="ev-elem-header">';
    html += '<span class="ev-elem-label">' + esc(label) + '</span>';
    html += '<span class="ev-v-pill ' + vcfg.cls + '">' + esc(vcLabel) + '</span>';
    if (verdict === 'disputed') html += '<span class="ev-disputed-badge">◈ Disputed</span>';
    if (citRef) {
        html += '<span class="ev-elem-citation">' + esc(citRef) + '</span>';
    } else if (ev.disagreement_citations) {
        // Step 372D2-fix: merged citation null on disagreement — surface the contested grounding.
        html += contestedCitationHtml(ev.disagreement_citations, { style: 'inline' });
    }
    html += '</div>';
    if (verdict === 'missing') {
        html += '<div class="ev-elem-missing">✗ Missing — not found in lease</div>';
    } else if (citQuote) {
        var qDisplay = citQuote.length > 120 ? citQuote.slice(0, 120) + '…' : citQuote;
        html += '<div class="ev-elem-quote">"' + esc(qDisplay) + '"</div>';
    }
    if (evalVerdicts.length > 0) {
        html += '<button class="ev-evals-toggle" onclick="(function(btn){var p=document.getElementById(\'' + evalPanelId + '\');if(p){var h=p.style.display===\'none\';p.style.display=h?\'\':\'none\';btn.classList.toggle(\'ev-evals-open\',h)}})(this);event.stopPropagation()" type="button">'
            + evalVerdicts.length + ' Evaluators</button>';
        html += '<div class="ev-evals-panel" id="' + evalPanelId + '" style="display:none">';
        evalVerdicts.forEach(function(evi) {
            var eRole = evi.role || evi.evaluator_id || '?';
            var eName = evi.label || evalName(eRole);
            var eVerdict = evi.verdict || 'unclear';
            var evcfg = _EV_VERDICT_CFG[eVerdict] || { cls: 'ev-v-unclear', label: eVerdict };
            var eRef = evi.citation && evi.citation.section_ref ? evi.citation.section_ref : '';
            var eColor = EVALUATOR_COLORS[eRole] || 'eval-blue';
            html += '<div class="ev-eval-row">';
            html += '<span class="ev-eval-badge eval-badge-' + esc(eRole) + ' ' + esc(eColor) + '">' + esc(eRole) + '</span>';
            html += '<span class="ev-eval-name">' + esc(eName) + '</span>';
            html += '<span class="ev-v-pill ' + evcfg.cls + ' ev-eval-vpill">' + esc(evcfg.label) + '</span>';
            if (eRef) html += '<span class="ev-eval-ref">' + esc(eRef) + '</span>';
            html += '</div>';
        });
        html += '</div>';
    }
    html += '</div>';
    return html;
}

function _buildLpBlock(lp, idx, expanded, highlightElementId) {
    var pid = lp.issue_area_id || '';
    var safePid = pid.replace(/[^a-zA-Z0-9_-]/g, '_');
    var name = lp.issue_area_name || pid;
    var actionBucket = lp.action_bucket || '';

    var searchText = name.toLowerCase();
    var elements = lp.element_verdicts || [];
    elements.forEach(function(ev) {
        searchText += ' ' + (ev.element_label || ev.element_id || '').toLowerCase();
        if (ev.citation && ev.citation.quote) searchText += ' ' + ev.citation.quote.toLowerCase();
    });

    // Step 361d: materiality badge (purple/neutral) replaces old lp_confidence badge
    var matVal = (lp.use_impact && lp.use_impact.materiality) || lp.lp_confidence || '';
    var matBadge = matVal
        ? '<span class="ev-badge-mat ev-badge-mat-' + esc(matVal) + '">' + esc(matVal) + ' impact</span>'
        : '';
    // Step 361d: LP identifier chip
    var lpNum = idx + 1;
    var lpIdChip = '<span class="ev-lp-id-chip">LP-' + (lpNum < 10 ? '0' + lpNum : lpNum) + '</span>';
    // Step 361c: vdSev used only in LP body note — NOT in the header row
    var vdSev = lp.verdict_distance && lp.verdict_distance.severity;
    var stateLabel = _evCoverageStateLabel(lp.coverage_state);
    var stateBadge = stateLabel
        ? '<span class="ev-state-badge ev-state-' + esc(lp.coverage_state || '') + '">' + esc(stateLabel) + '</span>'
        : '';

    var bodyId = 'ev-lp-body-' + safePid;
    var toggleFn = 'window.CAM._evToggleLp(\'' + safePid + '\')';

    var html = '<div class="ev-lp-group" data-pid="' + esc(pid) + '" data-bucket="' + esc(actionBucket) + '" data-search-text="' + esc(searchText) + '">';
    // Step 361c: header is a single flex row — name (truncating), badges wrapper, arrow
    html += '<div class="ev-lp-header" onclick="' + toggleFn + '">';
    html += '<span class="ev-lp-name">' + esc(name) + '</span>';
    html += '<div class="ev-lp-badges">';
    html += _evBucketChip(actionBucket);
    html += stateBadge;
    if (matBadge) html += matBadge;
    html += lpIdChip;
    html += '</div>';
    html += '<span class="ev-lp-arrow">' + (expanded ? '▾' : '▸') + '</span>';
    html += '</div>';

    html += '<div class="ev-lp-body" id="' + bodyId + '" style="' + (expanded ? '' : 'display:none') + '">';
    // Step 361c: distance note at TOP of body — not in the header row
    if (vdSev && (vdSev === 'moderate' || vdSev === 'severe')) {
        // Step 374K: derived LP rollup, not direct evaluator disagreement.
        html += '<div class="ev-distance-note ev-distance-' + esc(vdSev) + '">⚡ Review signal derived from aggregated element verdicts (' + esc(vdSev) + ' distance) — see element evidence</div>';
    }
    if (lp.evidence_summary) {
        html += '<div class="ev-lp-summary">' + esc(lp.evidence_summary) + '</div>';
    }
    // Step 361d: sort elements — disputed(0) → missing(1) → unclear(2) → present variants(3)
    var _evVOrder = { 'disputed': 0, 'missing': 1, 'unclear': 2 };
    var sortedElements = elements.slice().sort(function(a, b) {
        var oa = (_evVOrder[a.verdict] !== undefined) ? _evVOrder[a.verdict] : 3;
        var ob = (_evVOrder[b.verdict] !== undefined) ? _evVOrder[b.verdict] : 3;
        return oa - ob;
    });
    if (sortedElements.length > 0) {
        html += '<div class="ev-elements">';
        sortedElements.forEach(function(ev) {
            html += _buildElementRow(ev, safePid, ev.element_id === highlightElementId);
        });
        html += '</div>';
    } else {
        html += '<div class="ev-empty" style="padding:.5rem 1rem;font-size:.8rem">No element evidence available.</div>';
    }
    html += '</div>';
    html += '</div>';
    return html;
}

// Step 365: CPF card heading — prefer the model-authored short title, then
// short_summary, then the (now full) headline sentence. headline is no longer
// used as a heading directly; it is shown as body text where it adds detail.
function cpfTitle(f) {
    if (!f) return '';
    return (f.title || f.short_summary || f.headline || f.finding_id || '').trim();
}

function _buildCpfDetail(cpfItem) {
    var html = '<div class="ev-cpf-detail">';
    html += '<div class="ev-cpf-detail-meta">';
    var ftLabel = cpfItem.finding_type ? cpfItem.finding_type.replace(/_/g, ' ') : '';
    if (ftLabel) html += '<span class="ev-cpf-type-badge">' + esc(ftLabel) + '</span>';
    // Step 375C: a Pass-2 integrity-incomplete directional finding is NOT a legal severity and NOT a
    // genuine evaluator disagreement — render the distinct "verification incomplete" state, not a raw
    // severity label or a deflated tally. (Backend marks verification_incomplete + the role not_assessed
    // + raw cause; current-code findings never carry this, so no current display changes.)
    if (cpfItem.verification_incomplete || cpfItem.severity === 'VERIFICATION_INCOMPLETE') {
        var _incRoles = (cpfItem.verification_incomplete_roles || []).join(', ');
        html += '<span class="ev-cpf-sev-badge ev-cpf-sev-incomplete" title="Pass-2 verification incomplete'
              + (_incRoles ? ' (evaluator ' + esc(_incRoles) + ' returned no usable output)' : '')
              + ' — confirmation strength could not be established; not a severity and not a disagreement">'
              + '&#9888; Verification incomplete</span>';
    } else if (cpfItem.severity) {
        html += '<span class="ev-cpf-sev-badge ev-cpf-sev-' + esc(cpfItem.severity) + '">' + esc(cpfItem.severity) + '</span>';
    }
    html += '</div>';
    var _cpfHl = (cpfItem.headline || '').trim();
    var _cpfHeading = cpfTitle(cpfItem);
    if (_cpfHeading) html += '<div class="ev-cpf-headline">' + esc(_cpfHeading) + '</div>';
    var detail = cpfItem.detail || cpfItem.summary || '';
    if (_cpfHl && _cpfHl !== _cpfHeading) html += '<div class="ev-cpf-text">' + esc(_cpfHl) + '</div>';
    if (detail) html += '<div class="ev-cpf-text">' + esc(detail) + '</div>';
    if (cpfItem.cited_sections && cpfItem.cited_sections.length > 0) {
        html += '<div class="ev-cpf-sections">Cited sections: ';
        html += cpfItem.cited_sections.map(function(s) {
            return '<span class="ev-cpf-sec-chip">' + esc(s) + '</span>';
        }).join(' ');
        html += '</div>';
    }
    if (cpfItem.implicated_lps && cpfItem.implicated_lps.length > 0) {
        html += '<div class="ev-cpf-lps">Implicated LPs: ';
        html += cpfItem.implicated_lps.map(function(lp) {
            return '<span class="ev-lp-chip">' + esc(lp) + '</span>';
        }).join(' ');
        html += '</div>';
    }
    if (cpfItem.evaluator_consensus === 'unanimous') {
        html += '<div class="ev-cpf-consensus"><span class="ev-consensus-badge">✓ Unanimous</span></div>';
    }
    html += '</div>';
    return html;
}

function _buildCpfSection(cpf) {
    var html = '<div class="ev-cpf-section">';
    html += '<div class="ev-cpf-section-header" onclick="window.CAM._evToggleCpf()">';
    html += '<span class="ev-cpf-section-title">Cross-Provision Findings (' + cpf.length + ')</span>';
    html += '<span class="ev-cpf-arrow" id="ev-cpf-arrow">▸</span>';
    html += '</div>';
    html += '<div class="ev-cpf-body" id="ev-cpf-body" style="display:none">';
    cpf.forEach(function(cpfItem) {
        var fid = cpfItem.finding_id || '';
        var safeId = fid.replace(/[^a-zA-Z0-9_-]/g, '_');
        var bodyId = 'ev-cpf-row-' + safeId;
        html += '<div class="ev-cpf-row">';
        html += '<div class="ev-cpf-row-header" onclick="(function(el){var b=document.getElementById(\'' + bodyId + '\');var arr=el.querySelector(\'.ev-cpf-row-arrow\');if(b){var h=b.style.display===\'none\';b.style.display=h?\'\':\'none\';if(arr)arr.textContent=h?\'▾\':\'▸\'}})(this)">';
        html += '<span class="ev-cpf-row-id">' + esc(fid) + '</span>';
        var hl = cpfTitle(cpfItem);
        html += '<span class="ev-cpf-row-headline">' + esc(hl.length > 80 ? hl.slice(0, 80) + '…' : hl) + '</span>';
        html += '<span class="ev-cpf-row-arrow">▸</span>';
        html += '</div>';
        html += '<div class="ev-cpf-row-body" id="' + bodyId + '" style="display:none">' + _buildCpfDetail(cpfItem) + '</div>';
        html += '</div>';
    });
    html += '</div>';
    html += '</div>';
    return html;
}

function renderEvidencePanel() {
    var tab = document.getElementById('evidence-tab');
    if (!tab) return;
    var tenant = currentResults && currentResults.tenants && currentResults.tenants[currentTenantIndex];
    if (!tenant || !tenant.results) {
        tab.innerHTML = '<div class="ev-empty">No analysis data available.</div>';
        return;
    }
    var pr = tenant.results;
    var coverage = pr.coverage_assessment || [];
    var cpf = pr.cross_provision_findings || [];
    var focus = window.evidenceFocus;
    if (focus && focus.issue_area_id) {
        _renderEvidenceFocused(tab, coverage, cpf, focus);
    } else {
        _currentEvBucket = '';
        _renderEvidenceStandalone(tab, coverage, cpf);
    }
}

function _renderEvidenceFocused(tab, coverage, cpf, focus) {
    var html = '';
    if (focus.origin) {
        var backTab = focus.origin === 'contract_view' ? 'contractview' : 'keyissues';
        html += '<div class="ev-back-bar"><button class="ev-back-btn" onclick="window.CAM._evGoBack(\'' + esc(backTab) + '\')" type="button">← Back to ' + esc(focus.origin_label || focus.origin) + '</button></div>';
    }
    if (focus.finding_id) {
        var cpfItem = null;
        for (var i = 0; i < cpf.length; i++) {
            if (cpf[i].finding_id === focus.finding_id) { cpfItem = cpf[i]; break; }
        }
        html += cpfItem ? _buildCpfDetail(cpfItem) : '<div class="ev-empty">Cross-provision finding ' + esc(focus.finding_id) + ' not found.</div>';
        tab.innerHTML = html;
        return;
    }
    var lp = null;
    for (var j = 0; j < coverage.length; j++) {
        if (coverage[j].issue_area_id === focus.issue_area_id) { lp = coverage[j]; break; }
    }
    var headerLabel = (focus.element_id && lp)
        ? (_findElementLabel(lp, focus.element_id) || focus.element_id)
        : ((lp && lp.issue_area_name) || focus.issue_area_id);
    html += '<div class="ev-focus-header">';
    html += '<div class="ev-focus-title">Evidence for: <strong>' + esc(headerLabel) + '</strong></div>';
    if (focus.origin_label || focus.section_key) {
        html += '<div class="ev-focus-source">';
        if (focus.origin_label) html += 'Source: <span class="ev-source-origin">' + esc(focus.origin_label) + '</span>';
        if (focus.section_key) html += ' → <span class="ev-source-section">' + esc(focus.section_key) + '</span>';
        html += '</div>';
    }
    html += '<div class="ev-focus-meta">';
    if (focus.action_bucket) html += _evBucketChip(focus.action_bucket) + ' ';
    if (focus.issue_area_id) {
        html += '<span class="ev-lp-chip">' + esc(focus.issue_area_id) + '</span>';
        if (lp && lp.issue_area_name) html += ' <span class="ev-focus-lpname">' + esc(lp.issue_area_name) + '</span>';
    }
    html += '</div></div>';
    if (!lp) {
        html += '<div class="ev-fallback">Could not locate exact evidence. No LP found for ' + esc(focus.issue_area_id) + '.</div>';
        tab.innerHTML = html;
        return;
    }
    html += _buildLpBlock(lp, 0, true, focus.element_id);
    tab.innerHTML = html;
    if (focus.element_id) {
        setTimeout(function() {
            var el = tab.querySelector('.ev-elem-highlighted');
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 80);
    }
}

function _renderEvidenceStandalone(tab, coverage, cpf) {
    var html = '';
    html += '<div class="ev-standalone-header">';
    html += '<div class="ev-search-bar"><input type="text" class="ev-search-input" id="ev-search-input" placeholder="Search evidence…" oninput="window.CAM._evFilter(this.value)" autocomplete="off"></div>';
    html += '<div class="ev-filter-chips" id="ev-filter-chips">';
    var chips = [
        { key: '', label: 'All' },
        { key: 'risk', label: 'Risk' },
        { key: 'review_needed', label: 'Review Needed' },
        { key: 'improvement', label: 'Improvement' },
        { key: 'addressed', label: 'Addressed' },
    ];
    chips.forEach(function(c) {
        html += '<button class="ev-filter-chip' + (c.key === '' ? ' ev-filter-active' : '') + '" data-bucket="' + esc(c.key) + '" onclick="window.CAM._evSetFilter(\'' + esc(c.key) + '\')" type="button">' + esc(c.label) + '</button>';
    });
    html += '</div></div>';
    html += '<div class="ev-lp-list" id="ev-lp-list">';
    var bucketOrder = { risk: 0, review_needed: 1, improvement: 2, addressed: 3 };
    var sorted = coverage.slice().sort(function(a, b) {
        var ao = bucketOrder[a.action_bucket] !== undefined ? bucketOrder[a.action_bucket] : 99;
        var bo = bucketOrder[b.action_bucket] !== undefined ? bucketOrder[b.action_bucket] : 99;
        return ao - bo;
    });
    sorted.forEach(function(lp, idx) {
        html += _buildLpBlock(lp, idx, false, null);
    });
    if (cpf.length > 0) html += _buildCpfSection(cpf);
    html += '</div>';
    tab.innerHTML = html;
}

// Step 361: jumpToEvidence — raw contract text view removed; switch to evidence tab standalone.
function jumpToEvidence(sectionRef, quote) {
    switchResultsTab('evidence');
}

function switchResultsTab(tab) {
    // Step 254: Document Comparison is hidden in Mode C; redirect to Coverage & Gaps
    // if restoreResultsViewState or a stale link tries to open it.
    if (tab === "docview" && isJobModeC()) {
        tab = "coverage";
    }

    // Guard — if no contract is open:
    // Audit Trail can show the full run view; other tabs need a contract
    if (!contractDetailOpen) {
        if (tab === 'audittrail') {
            setSubheader('Audit');
            // Show detail area, hide overview + contracts tab, mark tab active
            var overview     = document.getElementById('overview-tab-content');
            var contractsTab = document.getElementById('contracts-tab-content');
            var detail       = document.getElementById('contract-detail-view');
            if (overview)     overview.classList.add('hidden');
            if (contractsTab) contractsTab.classList.add('hidden');
            if (detail)       detail.classList.remove('hidden');
            setResultsContentDetailMode(true);
            document.querySelectorAll('#top-tab-bar .top-tab[data-top-tab]').forEach(function(t) { t.classList.remove('active'); });
            document.querySelectorAll('#top-tab-bar .top-tab[data-tab]').forEach(function(t) {
                t.classList.toggle('active', t.dataset.tab === 'audittrail');
            });
            // Hide placeholder if showing
            var ncp = document.getElementById('no-contract-placeholder');
            if (ncp) ncp.classList.add('hidden');
            renderContractSelectorBar(null);
            // Clear header
            var hdr = document.getElementById('contract-detail-header');
            if (hdr) hdr.innerHTML = '<h2 class="contract-detail-name">Full Run Audit Trail</h2>';
            // Show audit tab content, hide others
            var _fTab = document.getElementById('findings-tab');
            var _dTab = document.getElementById('docview-tab');
            var _aTab = document.getElementById('audittrail-tab');
            var _cTab = document.getElementById('coverage-tab');
            var _cvTab = document.getElementById('contractview-tab');
            if (_fTab) _fTab.classList.add('hidden');
            if (_dTab) _dTab.classList.add('hidden');
            if (_aTab) _aTab.classList.remove('hidden');
            if (_cTab) _cTab.classList.add('hidden');
            if (_cvTab) _cvTab.classList.add('hidden');
            setDocviewStickyControlsVisible(false);
            activeResultsTab = 'audittrail';
            renderAuditTrail(true);
            return;
        }
        setDocviewStickyControlsVisible(false);
        showNoContractPlaceholder(tab);
        return;
    }

    // Step 361: Evidence View re-renders every call — no scroll preservation needed.

    activeResultsTab = tab;
    if (tab === "findings" || tab === "docview" || tab === "audittrail" || tab === "coverage" || tab === "contractview" || tab === "evidence" || tab === "synthesis") {
        activeTopTab = tab;
    }
    // Step 281: Coverage & Gaps tab in Mode C carries a right-aligned
    // perspective indicator. All other tabs (and Mode A on the
    // Coverage tab) get the plain label-only subheader as before.
    var _subRight = (tab === "coverage") ? _coverageSubheaderRight() : "";
    setSubheader(TAB_SUBHEADER_LABELS[tab] || tab, _subRight);

    // Update tab bar active state (Step 129 fix: $ → $ for querySelectorAll)
    document.querySelectorAll("#contract-tab-findings, #contract-tab-docview, #contract-tab-audittrail, #contract-tab-coverage, #contract-tab-contractview, #contract-tab-evidence, #contract-tab-synthesis").forEach(t => {
        t.classList.toggle("active", t.dataset.tab === tab);
    });

    // Show/hide tab content
    const findingsTab = $("#findings-tab");
    const docviewTab = $("#docview-tab");
    const auditTab = $("#audittrail-tab");
    const coverageTab = $("#coverage-tab");
    const contractviewTab = $("#contractview-tab");
    const evidenceTab = $("#evidence-tab");
    const synthesisTab = $("#synthesis-tab");

    if (tab === "findings") {
        findingsTab.classList.remove("hidden");
        docviewTab.classList.add("hidden");
        auditTab.classList.add("hidden");
        if (coverageTab) coverageTab.classList.add("hidden");
        if (contractviewTab) contractviewTab.classList.add("hidden");
        if (synthesisTab) synthesisTab.classList.add("hidden");
        setDocviewStickyControlsVisible(false);
    } else if (tab === "audittrail") {
        findingsTab.classList.add("hidden");
        docviewTab.classList.add("hidden");
        auditTab.classList.remove("hidden");
        if (coverageTab) coverageTab.classList.add("hidden");
        if (contractviewTab) contractviewTab.classList.add("hidden");
        if (synthesisTab) synthesisTab.classList.add("hidden");
        setDocviewStickyControlsVisible(false);
        renderAuditTrail();
    } else if (tab === "coverage") {
        findingsTab.classList.add("hidden");
        docviewTab.classList.add("hidden");
        auditTab.classList.add("hidden");
        if (coverageTab) coverageTab.classList.remove("hidden");
        if (contractviewTab) contractviewTab.classList.add("hidden");
        if (evidenceTab) evidenceTab.classList.add("hidden");
        if (synthesisTab) synthesisTab.classList.add("hidden");
        setDocviewStickyControlsVisible(false);
        renderCoveragePanel();
    } else if (tab === "contractview") {
        findingsTab.classList.add("hidden");
        docviewTab.classList.add("hidden");
        auditTab.classList.add("hidden");
        if (coverageTab) coverageTab.classList.add("hidden");
        if (contractviewTab) contractviewTab.classList.remove("hidden");
        if (evidenceTab) evidenceTab.classList.add("hidden");
        if (synthesisTab) synthesisTab.classList.add("hidden");
        // Hide the shared clause filter bar — it belongs to the findings/audit tabs
        var _cvFilterBar = document.getElementById('contract-clause-filter-bar');
        if (_cvFilterBar) _cvFilterBar.classList.add('hidden');
        setDocviewStickyControlsVisible(false);
        renderContractViewPanel();
    } else if (tab === "evidence") {
        findingsTab.classList.add("hidden");
        docviewTab.classList.add("hidden");
        auditTab.classList.add("hidden");
        if (coverageTab) coverageTab.classList.add("hidden");
        if (contractviewTab) contractviewTab.classList.add("hidden");
        if (evidenceTab) evidenceTab.classList.remove("hidden");
        if (synthesisTab) synthesisTab.classList.add("hidden");
        // Step 361: hide shared clause filter bar (same as contractview case)
        var _evFilterBar = document.getElementById('contract-clause-filter-bar');
        if (_evFilterBar) _evFilterBar.classList.add('hidden');
        setDocviewStickyControlsVisible(false);
        renderEvidencePanel();
    } else if (tab === "synthesis") {
        findingsTab.classList.add("hidden");
        docviewTab.classList.add("hidden");
        auditTab.classList.add("hidden");
        if (coverageTab) coverageTab.classList.add("hidden");
        if (contractviewTab) contractviewTab.classList.add("hidden");
        if (evidenceTab) evidenceTab.classList.add("hidden");
        if (synthesisTab) synthesisTab.classList.remove("hidden");
        setDocviewStickyControlsVisible(false);
        renderSynthesisPanel();
    } else {
        findingsTab.classList.add("hidden");
        docviewTab.classList.remove("hidden");
        auditTab.classList.add("hidden");
        if (coverageTab) coverageTab.classList.add("hidden");
        if (contractviewTab) contractviewTab.classList.add("hidden");
        if (evidenceTab) evidenceTab.classList.add("hidden");
        if (synthesisTab) synthesisTab.classList.add("hidden");
        setDocviewStickyControlsVisible(true);
        renderDocumentView();
    }

    // Scroll to top on every tab switch (Evidence re-renders fresh each time)
    var detail = document.getElementById('contract-detail-view');
    if (detail) detail.scrollTo({ top: 0, behavior: 'instant' });
    var resultsPane = document.getElementById('results-content') || document.querySelector('.results-content');
    if (resultsPane) resultsPane.scrollTo({ top: 0, behavior: 'instant' });
    persistResultsViewState();
}

// Sort provisions for docview based on docviewSort setting.
// "reference" = reference-lease article/section order
// "contract"  = tenant-led article/section order, with template refs only as fallback
function sortProvisionsForDocview(provisions) {
    if (docviewSort === "taxonomy") {
        return provisions.slice().sort((a, b) => {
            const aid = a.provision_id || "";
            const bid = b.provision_id || "";
            if (aid === "LP-00" && bid !== "LP-00") return -1;
            if (bid === "LP-00" && aid !== "LP-00") return 1;
            return aid.localeCompare(bid, undefined, { numeric: true });
        });
    }
    const romanToInt = s => {
        const R = { I:1, V:5, X:10, L:50, C:100, D:500, M:1000 };
        let val = 0, prev = 0;
        for (const c of [...s.toUpperCase()].reverse()) {
            const n = R[c] || 0;
            val += n >= prev ? n : -n;
            prev = n;
        }
        return val;
    };
    const contractPos = p => {
        const ref = p.template_section_ref || p.tenant_section_ref || "";
        // Article number (Roman or decimal) takes precedence
        let m = ref.match(/Article\s+([IVXLCDM]+)/i);
        if (m) return romanToInt(m[1]);
        m = ref.match(/Article\s+(\d+)/i);
        if (m) return parseInt(m[1], 10);
        // Fall back to first section number
        m = ref.match(/Section\s+([\d.]+)/i);
        if (m) return parseFloat(m[1]) + 0.001; // fractional so article wins
        // CUSTOM/ADDED and no ref go last, preserving their LP order within that group
        const pid = p.provision_id || "";
        if (pid.startsWith("CUSTOM-") || pid.startsWith("ADDED-")) return 9000;
        return 8000; // known provision but no ref — before CUSTOM
    };
    return provisions.slice().sort((a, b) => contractPos(a) - contractPos(b));
}

function sortProvisionsForDocviewTenantLed(provisions) {
    if (docviewSort === "reference") {
        return sortProvisionsForDocview(provisions);
    }

    const romanToInt = (s) => {
        const R = { I:1, V:5, X:10, L:50, C:100, D:500, M:1000 };
        let val = 0;
        let prev = 0;
        for (const c of [...s.toUpperCase()].reverse()) {
            const n = R[c] || 0;
            val += n >= prev ? n : -n;
            prev = n;
        }
        return val;
    };

    const parseOrderRef = (ref) => {
        const normalized = (ref || "").trim();
        if (!normalized) return null;

        let article = 9999;
        let match = normalized.match(/Article\s+([IVXLCDM]+)/i);
        if (match) {
            article = romanToInt(match[1]);
        } else {
            match = normalized.match(/Article\s+(\d+)/i);
            if (match) article = parseInt(match[1], 10);
        }

        let sectionParts = [];
        match = normalized.match(/Sections?\s+([\d.\-]+)/i);
        if (match) {
            const firstSection = match[1].split("-")[0];
            sectionParts = firstSection.split(".").map((part) => parseInt(part, 10) || 0);
        }

        return {
            article,
            sectionParts,
            raw: normalized.toLowerCase(),
        };
    };

    const compareRefs = (aRef, bRef) => {
        if (!aRef && !bRef) return 0;
        if (!aRef) return 1;
        if (!bRef) return -1;
        if (aRef.article !== bRef.article) return aRef.article - bRef.article;
        const len = Math.max(aRef.sectionParts.length, bRef.sectionParts.length);
        for (let i = 0; i < len; i++) {
            const aPart = aRef.sectionParts[i] || 0;
            const bPart = bRef.sectionParts[i] || 0;
            if (aPart !== bPart) return aPart - bPart;
        }
        return aRef.raw.localeCompare(bRef.raw, undefined, { numeric: true });
    };

    const getSortMeta = (p) => {
        const pid = p.provision_id || "";
        return {
            tenantRef: parseOrderRef(p.tenant_section_ref || ""),
            templateRef: parseOrderRef(p.template_section_ref || ""),
            pid,
            isCustom: pid.startsWith("CUSTOM-") || pid.startsWith("ADDED-"),
        };
    };

    return (provisions || []).slice().sort((a, b) => {
        const aMeta = getSortMeta(a);
        const bMeta = getSortMeta(b);

        if (aMeta.pid === "LP-00" && bMeta.pid !== "LP-00") return -1;
        if (bMeta.pid === "LP-00" && aMeta.pid !== "LP-00") return 1;

        const tenantCmp = compareRefs(aMeta.tenantRef, bMeta.tenantRef);
        if (tenantCmp !== 0) return tenantCmp;

        const templateCmp = compareRefs(aMeta.templateRef, bMeta.templateRef);
        if (templateCmp !== 0) return templateCmp;

        if (aMeta.isCustom !== bMeta.isCustom) return aMeta.isCustom ? 1 : -1;
        return aMeta.pid.localeCompare(bMeta.pid, undefined, { numeric: true });
    });
}

function renderDocumentView() {
    if (!currentResults || !currentResults.tenants) return;

    // Sync mode and sort toggle button active states
    document.querySelectorAll(".docview-mode-btn").forEach(function(b) {
        b.classList.toggle("active", b.dataset.mode === docviewMode);
    });
    document.querySelectorAll(".docview-sort-btn").forEach(function(b) {
        b.classList.toggle("active", b.dataset.sort === docviewSort);
    });

    // Populate docview tenant selector
    const dts = $("#docview-tenant-select");
    if (dts && dts.options.length === 0) {
        dts.innerHTML = currentResults.tenants.map((t, i) =>
            `<option value="${i}">${esc(t.filename)}</option>`
        ).join("");
    }
    if (dts) dts.value = currentTenantIndex;

    if (docviewMode === "full") {
        $("#docview-full").classList.remove("hidden");
        $("#docview-sidebyside-wrapper").classList.add("hidden");
        renderFullDocumentView();
    } else {
        $("#docview-full").classList.add("hidden");
        $("#docview-sidebyside-wrapper").classList.remove("hidden");
        renderSideBySideView();
    }
}

// ── Full Document View (Item 5) ──

function renderFullDocumentView() {
    const tenant = currentResults.tenants[currentTenantIndex];
    if (!tenant || !tenant.results) {
        $("#docview-main").innerHTML = '<div style="padding:2rem; text-align:center; color:var(--text-muted);">No results available for this tenant.</div>';
        $("#docview-sidebar").innerHTML = "";
        return;
    }

    const r = tenant.results;
    const fullText = r.full_tenant_text || "";
    const provisions = sortProvisionsForDocviewTenantLed(getDocviewWorkflowProvisions(r.provisions || []));

    // If no full text available, fall back to side-by-side
    if (!fullText) {
        $("#docview-main").innerHTML = '<div style="padding:2rem; text-align:center; color:var(--text-muted);">Full document text not available for this analysis. Use Side-by-Side view instead.</div>';
        renderFullDocSidebar(provisions, []);
        return;
    }

    // ── Section matching: find each provision's location in the full text ──
    const matches = []; // { pid, start, end, provision }
    provisions.forEach(p => {
        const tenantText = (p.tenant_text || "").trim();
        if (!tenantText || tenantText.length < 20) return;

        // Try progressively shorter substrings
        let found = false;
        for (const len of [80, 60, 40]) {
            if (found) break;
            const needle = tenantText.substring(0, Math.min(len, tenantText.length)).trim();
            if (needle.length < 15) continue;
            const idx = fullText.indexOf(needle);
            if (idx !== -1) {
                // Try to find the end too
                const endNeedle = tenantText.length > 40
                    ? tenantText.substring(tenantText.length - 30).trim()
                    : "";
                let endIdx = idx + needle.length;
                if (endNeedle) {
                    const searchEnd = fullText.indexOf(endNeedle, idx);
                    if (searchEnd !== -1) endIdx = searchEnd + endNeedle.length;
                }
                matches.push({ pid: p.provision_id, start: idx, end: endIdx, provision: p });
                found = true;
            }
        }
        // Fallback: case-insensitive search
        if (!found) {
            const needle = tenantText.substring(0, Math.min(50, tenantText.length)).trim().toLowerCase();
            if (needle.length >= 15) {
                const idx = fullText.toLowerCase().indexOf(needle);
                if (idx !== -1) {
                    matches.push({ pid: p.provision_id, start: idx, end: idx + needle.length, provision: p });
                }
            }
        }
    });

    // Sort matches by position
    matches.sort((a, b) => a.start - b.start);

    // ── Build main panel HTML with inline annotations ──
    let mainHtml = "";
    let cursor = 0;

    matches.forEach(m => {
        const p = m.provision;
        const isDeviation = p.final_verdict === "DEVIATES";

        // Text before this match
        if (m.start > cursor) {
            mainHtml += `<span>${esc(fullText.substring(cursor, m.start))}</span>`;
        }

        // Highlighted region
        const sevClass = isDeviation ? `fulldoc-hl-${p.severity || "MEDIUM"}` : "";
        mainHtml += `<span class="fulldoc-highlight ${sevClass}" id="fulldoc-${m.pid}" data-pid="${esc(m.pid)}">${esc(fullText.substring(m.start, m.end))}</span>`;

        // Margin callout for deviations (compact sticky-note style)
        if (isDeviation) {
            const icon = SEVERITY_ICONS[p.severity] || "";
            const headline = p.risk_headline || p.challenge_details || "";
            mainHtml += `<div class="fulldoc-callout fulldoc-callout-${p.severity || "MEDIUM"}">
                <span class="fulldoc-callout-header"><span class="severity-badge severity-${p.severity || ""}">${icon} ${sevDisplay(p.severity)}</span> ${esc(m.pid)}</span>
                ${headline ? `<span class="fulldoc-callout-text">&mdash; ${esc(truncateToSentence(headline, 120))}</span>` : ""}
                <a class="fulldoc-callout-link" data-pid="${esc(m.pid)}">View full analysis &#8594;</a>
            </div>`;
        }

        cursor = m.end;
    });

    // Remaining text after last match
    if (cursor < fullText.length) {
        mainHtml += `<span>${esc(fullText.substring(cursor))}</span>`;
    }

    const mainEl = $("#docview-main");
    mainEl.innerHTML = `<div class="fulldoc-text">${mainHtml}</div>`;

    // Wire callout links
    mainEl.querySelectorAll(".fulldoc-callout-link").forEach(link => {
        link.addEventListener("click", () => {
            const pid = link.dataset.pid;
            switchResultsTab("findings");
            const card = document.getElementById(`dev-${pid}`);
            if (card) {
                setTimeout(() => {
                    card.scrollIntoView({ behavior: "smooth", block: "center" });
                    card.classList.add("highlight-flash");
                    setTimeout(() => card.classList.remove("highlight-flash"), 1500);
                }, 100);
            }
        });
    });

    // ── Build sidebar ──
    renderFullDocSidebar(provisions, matches);

    // ── Scroll sync: track active provision ──
    const highlights = mainEl.querySelectorAll(".fulldoc-highlight");
    if (highlights.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const pid = entry.target.dataset.pid;
                    document.querySelectorAll(".fulldoc-sidebar-item").forEach(item => {
                        item.classList.toggle("active", item.dataset.pid === pid);
                    });
                }
            });
        }, { root: mainEl, threshold: 0.3 });

        highlights.forEach(hl => observer.observe(hl));
    }
}

function legacyBuildTocSeverityMaps(provisions, primarySide = "tenant") {
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

    getDeviationWorkflowProvisions(provisions || []).forEach((p) => {
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

function renderFullDocSidebar(provisions, matches) {
    const sidebar = $("#docview-sidebar");
    // Provisions TOC moved to left nav sidebar — docview sidebar now shows article TOC only
    sidebar.innerHTML = '<div class="fulldoc-sidebar-header">Document Sections</div>';
    const tenant = currentResults.tenants[currentTenantIndex];
    const fullText = tenant && tenant.results ? (tenant.results.full_tenant_text || "") : "";
    renderSidebarTOC(sidebar, fullText, "fulldoc", { provisions, primarySide: "tenant" });
}

function legacyRenderSidebarTOC(sidebar, fullText, scrollTargetPrefix, options = {}) {
    if (!fullText) return;
    const { provisions = [], primarySide = "tenant" } = options;
    const { sectionMap, articleMap } = buildTocSeverityMaps(provisions, primarySide);

    // Parse article headers from lease text
    const articlePattern = /^(?:={3,}\s*)?(?:ARTICLE\s+[IVXLC\d]+\s*[—–\-]\s*(.+?))(?:\s*={3,})?$/gmi;
    const articles = [];
    const sections = [];
    const sectionPattern = /^Section\s+([\d.]+)\.\s+(.+)$/gmi;
    let match;
    while ((match = articlePattern.exec(fullText)) !== null) {
        const fullMatch = match[0].replace(/={3,}/g, "").trim();
        articles.push({ title: fullMatch, index: match.index });
    }
    while ((match = sectionPattern.exec(fullText)) !== null) {
        const sectionNumber = match[1];
        const remainder = (match[2] || "").trim();
        const shortTitle = remainder.split(".")[0].trim();
        const sectionLabel = shortTitle
            ? `Section ${sectionNumber}. ${shortTitle}`
            : `Section ${sectionNumber}`;
        sections.push({ title: sectionLabel, index: match.index, sectionNumber });
    }

    const outline = articles
        .map((entry) => ({ ...entry, type: "article" }))
        .concat(sections.map((entry) => ({ ...entry, type: "section" })))
        .sort((a, b) => a.index - b.index);

    if (outline.length === 0) return;

    let tocHtml = `<div class="fulldoc-sidebar-divider"></div>
        <div class="sidebar-toc-toggle" id="toc-toggle-${scrollTargetPrefix}">
            <span class="toc-arrow">&#9660;</span> TABLE OF CONTENTS
        </div>
        <div class="sidebar-toc-content" id="toc-content-${scrollTargetPrefix}">`;

    outline.forEach((entry, i) => {
        const entryClass = entry.type === "section" ? " sidebar-toc-item-section" : " sidebar-toc-item-article";
        const sectionAttr = entry.sectionNumber ? ` data-section-number="${esc(entry.sectionNumber)}"` : "";
        const severity = entry.type === "section"
            ? (sectionMap.get(entry.sectionNumber || "") || "")
            : (() => {
                const articleMatch = entry.title.match(/ARTICLE\s+([IVXLC\d]+)/i);
                return articleMatch ? (articleMap.get(articleMatch[1].toUpperCase()) || "") : "";
            })();
        const severityDot = severity ? `<span class="sidebar-toc-severity sidebar-toc-severity-${severity}"></span>` : "";
        tocHtml += `<div class="sidebar-toc-item${entryClass}" data-toc-idx="${i}" data-toc-text="${esc(entry.title)}"${sectionAttr}>${severityDot}<span>${esc(entry.title)}</span></div>`;
    });
    tocHtml += `</div>`;

    sidebar.insertAdjacentHTML("beforeend", tocHtml);

    // Wire toggle
    const toggle = sidebar.querySelector(`#toc-toggle-${scrollTargetPrefix}`);
    const content = sidebar.querySelector(`#toc-content-${scrollTargetPrefix}`);
    if (toggle && content) {
        toggle.addEventListener("click", () => {
            const isOpen = !content.classList.contains("hidden");
            content.classList.toggle("hidden");
            const arrow = toggle.querySelector(".toc-arrow");
            if (arrow) arrow.innerHTML = isOpen ? "&#9654;" : "&#9660;";
        });
    }

    // Wire TOC item clicks — find text in the main panel and scroll to it
    sidebar.querySelectorAll(".sidebar-toc-item").forEach(item => {
        item.addEventListener("click", () => {
            const entry = outline[parseInt(item.dataset.tocIdx, 10)];
            const searchText = entry.title;
            if (scrollTargetPrefix === "sbs") {
                const articleMatch = searchText.match(/ARTICLE\s+([IVXLC\d]+)/i);
                const sectionNumber = item.dataset.sectionNumber || "";
                const primaryAttr = docviewSort === "reference" ? "data-template-ref" : "data-tenant-ref";
                const headers = Array.from(document.querySelectorAll(".docview-provision-header"));

                let target = null;
                if (sectionNumber) {
                    const escapedSection = sectionNumber.replace(".", "\\.");
                    target = headers.find((header) => {
                        const ref = header.getAttribute(primaryAttr) || "";
                        return new RegExp(`Sections?\\s+${escapedSection}\\b|Section\\s+${escapedSection}\\b`, "i").test(ref);
                    }) || null;
                }
                if (articleMatch) {
                    const articleToken = articleMatch[1].toUpperCase();
                    target = target || headers.find((header) => {
                        const ref = header.getAttribute(primaryAttr) || "";
                        return new RegExp(`Article\\s+${articleToken}\\b`, "i").test(ref);
                    }) || null;
                }
                if (target) {
                    const mainPanel = $(".docview-main-sbs");
                    scrollElementIntoPanelView(target, mainPanel, getDocviewJumpOffset(mainPanel));
                    target.classList.add("highlight-flash");
                    setTimeout(() => target.classList.remove("highlight-flash"), 1500);
                    return;
                }
            }
            const mainPanel = scrollTargetPrefix === "fulldoc" ? $("#docview-main") : $(".docview-main-sbs");
            if (!mainPanel) return;

            // Find the text in the rendered content
            const walker = document.createTreeWalker(mainPanel, NodeFilter.SHOW_TEXT, null);
            while (walker.nextNode()) {
                const idx = walker.currentNode.textContent.indexOf(searchText.substring(0, 30));
                if (idx !== -1) {
                    const parent = walker.currentNode.parentElement;
                    scrollElementIntoPanelView(parent, mainPanel, getDocviewJumpOffset(mainPanel));
                    parent.classList.add("highlight-flash");
                    setTimeout(() => parent.classList.remove("highlight-flash"), 1500);
                    break;
                }
            }
        });
    });
}

function renderSidebarTOC(sidebar, fullText, scrollTargetPrefix, options = {}) {
    if (!fullText) return;
    const { provisions = [], primarySide = "tenant" } = options;
    const { sectionMap, articleMap } = buildTocSeverityMaps(provisions, primarySide);
    const { articles, sections, outline } = parseSidebarTocOutline(fullText);
    if (outline.length === 0) return;

    const articleGroups = buildSidebarArticleGroups(articles, sections, outline);

    let tocHtml = `<div class="fulldoc-sidebar-divider"></div>
        <div class="sidebar-toc-toggle" id="toc-toggle-${scrollTargetPrefix}">
            <span class="toc-arrow">&#9660;</span> TABLE OF CONTENTS
        </div>
        <div class="sidebar-toc-content" id="toc-content-${scrollTargetPrefix}">`;

    if (articleGroups.some((group) => group.sections.length > 0)) {
        tocHtml += `<button type="button" class="sidebar-toc-expand-all" data-expanded="false">Expand All Sections</button>`;
    }

    articleGroups.forEach((group, articleIdx) => {
        const articleSeverity = group.articleToken ? (articleMap.get(group.articleToken) || "") : "";
        const articleSeverityDot = articleSeverity ? `<span class="sidebar-toc-severity sidebar-toc-severity-${articleSeverity}"></span>` : "";
        const hasSections = group.sections.length > 0;
        const firstSectionAttr = hasSections ? ` data-first-section-number="${esc(group.sections[0].sectionNumber)}"` : "";
        tocHtml += `<div class="sidebar-toc-group" data-article-group="${articleIdx}">
            <div class="sidebar-toc-item sidebar-toc-item-article" data-toc-idx="${group.outlineIndex}" data-toc-text="${esc(group.title)}"${firstSectionAttr}>
                <button type="button" class="sidebar-toc-group-toggle${hasSections ? "" : " sidebar-toc-group-toggle-hidden"}" data-article-group-toggle="${articleIdx}" aria-label="Toggle sections">${hasSections ? "&#9654;" : ""}</button>
                ${articleSeverityDot}
                <span>${esc(group.title)}</span>
            </div>`;

        if (hasSections) {
            tocHtml += `<div class="sidebar-toc-sections hidden" data-article-sections="${articleIdx}">`;
            group.sections.forEach((section) => {
                const sectionSeverity = sectionMap.get(section.sectionNumber || "") || "";
                const sectionSeverityDot = sectionSeverity ? `<span class="sidebar-toc-severity sidebar-toc-severity-${sectionSeverity}"></span>` : "";
                tocHtml += `<div class="sidebar-toc-item sidebar-toc-item-section" data-toc-idx="${section.outlineIndex}" data-toc-text="${esc(section.title)}" data-section-number="${esc(section.sectionNumber)}">${sectionSeverityDot}<span>${esc(section.title)}</span></div>`;
            });
            tocHtml += `</div>`;
        }

        tocHtml += `</div>`;
    });
    tocHtml += `</div>`;

    sidebar.insertAdjacentHTML("beforeend", tocHtml);

    const toggle = sidebar.querySelector(`#toc-toggle-${scrollTargetPrefix}`);
    const content = sidebar.querySelector(`#toc-content-${scrollTargetPrefix}`);
    if (toggle && content) {
        toggle.addEventListener("click", () => {
            const isOpen = !content.classList.contains("hidden");
            content.classList.toggle("hidden");
            const arrow = toggle.querySelector(".toc-arrow");
            if (arrow) arrow.innerHTML = isOpen ? "&#9654;" : "&#9660;";
        });
    }

    const navigateToTocEntry = (item) => {
        const entry = outline[parseInt(item.dataset.tocIdx, 10)];
        if (!entry) return;
        const searchText = entry.title;
        if (scrollTargetPrefix === "sbs") {
            const articleMatch = searchText.match(/ARTICLE\s+([IVXLC\d]+)/i);
            const sectionNumber = item.dataset.sectionNumber || item.dataset.firstSectionNumber || "";
            const primaryAttr = docviewSort === "reference" ? "data-template-ref" : "data-tenant-ref";
            const headers = Array.from(document.querySelectorAll(".docview-provision-header"));

            let target = null;
            if (sectionNumber) {
                const escapedSection = sectionNumber.replace(".", "\\.");
                target = headers.find((header) => {
                    const ref = header.getAttribute(primaryAttr) || "";
                    return new RegExp(`Sections?\\s+${escapedSection}\\b|Section\\s+${escapedSection}\\b`, "i").test(ref);
                }) || null;
            }
            if (articleMatch) {
                const articleToken = articleMatch[1].toUpperCase();
                target = target || headers.find((header) => {
                    const ref = header.getAttribute(primaryAttr) || "";
                    return new RegExp(`Article\\s+${articleToken}\\b`, "i").test(ref);
                }) || null;
            }
            if (target) {
                const mainPanel = $(".docview-main-sbs");
                scrollElementIntoPanelView(target, mainPanel, getDocviewJumpOffset(mainPanel));
                target.classList.add("highlight-flash");
                setTimeout(() => target.classList.remove("highlight-flash"), 1500);
                return;
            }
        }

        const mainPanel = scrollTargetPrefix === "fulldoc" ? $("#docview-main") : $(".docview-main-sbs");
        if (!mainPanel) return;
        const walker = document.createTreeWalker(mainPanel, NodeFilter.SHOW_TEXT, null);
        while (walker.nextNode()) {
            const idx = walker.currentNode.textContent.indexOf(searchText.substring(0, 30));
            if (idx !== -1) {
                const parent = walker.currentNode.parentElement;
                scrollElementIntoPanelView(parent, mainPanel, getDocviewJumpOffset(mainPanel));
                parent.classList.add("highlight-flash");
                setTimeout(() => parent.classList.remove("highlight-flash"), 1500);
                break;
            }
        }
    };

    sidebar.querySelectorAll(".sidebar-toc-group-toggle[data-article-group-toggle]").forEach((toggleBtn) => {
        toggleBtn.addEventListener("click", (event) => {
            event.stopPropagation();
            const groupId = toggleBtn.dataset.articleGroupToggle;
            const sectionBlock = sidebar.querySelector(`[data-article-sections="${groupId}"]`);
            if (!sectionBlock) return;
            const isOpen = !sectionBlock.classList.contains("hidden");
            sectionBlock.classList.toggle("hidden");
            toggleBtn.innerHTML = isOpen ? "&#9654;" : "&#9660;";
        });
    });

    const expandAllBtn = sidebar.querySelector(".sidebar-toc-expand-all");
    if (expandAllBtn) {
        expandAllBtn.addEventListener("click", () => {
            const expand = expandAllBtn.dataset.expanded !== "true";
            sidebar.querySelectorAll(".sidebar-toc-sections").forEach((sectionBlock) => {
                sectionBlock.classList.toggle("hidden", !expand);
            });
            sidebar.querySelectorAll(".sidebar-toc-group-toggle[data-article-group-toggle]").forEach((toggleBtn) => {
                if (!toggleBtn.classList.contains("sidebar-toc-group-toggle-hidden")) {
                    toggleBtn.innerHTML = expand ? "&#9660;" : "&#9654;";
                }
            });
            expandAllBtn.dataset.expanded = expand ? "true" : "false";
            expandAllBtn.textContent = expand ? "Collapse All Sections" : "Expand All Sections";
        });
    }

    sidebar.querySelectorAll(".sidebar-toc-item").forEach((item) => {
        item.addEventListener("click", (event) => {
            if (event.target.closest(".sidebar-toc-group-toggle")) return;
            navigateToTocEntry(item);
        });
    });
}

function scrollElementIntoPanelView(target, panel, topOffset = 72) {
    if (!target || !panel) return;
    const panelRect = panel.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const nextTop = panel.scrollTop + (targetRect.top - panelRect.top) - topOffset;
    panel.scrollTo({ top: Math.max(0, nextTop), behavior: "smooth" });
}

function getDocviewJumpOffset(panel) {
    if (!panel) return 72;
    if (panel.classList.contains("docview-main-sbs")) {
        const stickyHeader = panel.querySelector(".docview-sbs-sticky-header");
        const stickyHeight = stickyHeader ? stickyHeader.getBoundingClientRect().height : 0;
        return Math.round(stickyHeight + 12);
    }
    return 40;
}

function scrollDocviewTargetIntoView(target) {
    if (!target) return;
    const panel = target.closest(".docview-main-sbs, #docview-main") || (docviewMode === "full" ? $("#docview-main") : $(".docview-main-sbs"));
    if (!panel) return;
    scrollElementIntoPanelView(target, panel, getDocviewJumpOffset(panel));
}

// ── Side-by-Side View (original) ──

function legacyRenderSideBySideView() {
    const tenant = currentResults.tenants[currentTenantIndex];
    if (!tenant || !tenant.results) {
        $("#docview-container").innerHTML = '<div style="padding:2rem; text-align:center; color:var(--text-muted);">No results available for this tenant.</div>';
        $("#docview-sidebar-sbs").innerHTML = "";
        return;
    }

    const r = tenant.results;
    const provisions = sortProvisionsForDocviewTenantLed(getDocviewWorkflowProvisions(r.provisions || []));

    const templateFile = r.template_file || "Reference Lease";
    const tenantFile = r.tenant_file || tenant.filename || "Tenant Lease";

    // Build the side-by-side frame
    let html = "";

    const tenantLeads = docviewSort === "contract";

    html += `<div class="docview-sbs-sticky-header">`;
    html += `<div class="docview-back-link">&#8592; Back to Summary</div>`;
    html += `<div class="docview-sbs-column-header-row">`;

    // Column headers
    const referenceHeaderClass = docviewSort === "reference" ? "docview-column-header-primary" : "docview-column-header-secondary";
    const tenantHeaderClass = docviewSort === "contract" ? "docview-column-header-primary" : "docview-column-header-secondary";
    if (tenantLeads) {
        html += `<div class="docview-column-header ${referenceHeaderClass}">Reference Lease &mdash; ${esc(templateFile)}</div>`;
        html += `<div class="docview-column-header ${tenantHeaderClass}">Tenant Lease &mdash; ${esc(tenantFile)}</div>`;
    } else {
        html += `<div class="docview-column-header ${tenantHeaderClass}">Tenant Lease &mdash; ${esc(tenantFile)}</div>`;
        html += `<div class="docview-column-header ${referenceHeaderClass}">Reference Lease &mdash; ${esc(templateFile)}</div>`;
    }
    html += `</div>`;
    html += `</div>`;
    html += `<div class="docview-sbs-body">`;

    provisions.forEach(p => {
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
        const credibilityLine = isDeviationWorkflowProvision(p, currentTenantIndex)
            ? renderCredibilityLine(p, r.models_used || {}, currentTenantIndex, pid, severity)
            : "";

        let rowClass = "conforms";
        let severityBadge = "";
        let templateContent = esc(templateText) || '<span style="color:var(--text-muted); font-style:italic;">No text extracted</span>';
        let tenantContent   = esc(tenantText)   || '<span style="color:var(--text-muted); font-style:italic;">No text extracted</span>';

        if (verdict === "DEVIATES") {
            rowClass = "deviation";
            const icon = SEVERITY_ICONS[severity] || "";
            severityBadge = `<span class="severity-badge severity-${severity}">${icon} ${sevDisplay(severity)}</span>`;

            // Apply word-level diff when both sides exist
            if (templateText && tenantText) {
                const { templateHtml, tenantHtml } = computeWordDiff(templateText, tenantText);
                templateContent = templateHtml;
                tenantContent   = tenantHtml;
            } else if (!tenantText) {
                tenantContent = '<span style="color:var(--text-muted); font-style:italic;">Not found in tenant lease</span>';
            }
        } else if (status === "TEMPLATE_ONLY" || !tenantText) {
            rowClass = "omission";
            tenantContent = "&#9888;&#65039; Not found in tenant lease";
        }

        // Provision header (spans full width via grid-column)
        const analysisToggle = isDeviationWorkflowProvision(p, currentTenantIndex)
            ? `<button class="docview-header-toggle${openDocviewProvision === pid ? " open" : ""}"
                    data-pid="${esc(pid)}"
                    title="${openDocviewProvision === pid ? "Hide analysis" : "Show analysis"}"
                    onclick="event.stopPropagation(); window.CAM.toggleDocviewAnalysis('${esc(pid)}');">
                    ${openDocviewProvision === pid ? "▴" : "▾"}
               </button>`
            : "";
        const readBtn = `<button class="finding-read-toggle${isNoted(currentTenantIndex, pid) ? " noted-active" : ""}"
                title="Mark this provision as read"
                onclick="window.CAM.toggleNoted(${currentTenantIndex}, '${esc(pid)}', this); event.stopPropagation();">
            ${isNoted(currentTenantIndex, pid) ? "✓ Read" : "Mark as Read"}
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

        // Text cells: the leading document stays on the right
        if (tenantLeads) {
            html += `<div class="docview-text docview-template docview-${rowClass}">${templateContent}</div>`;
            html += `<div class="docview-text docview-tenant docview-${rowClass}">${tenantContent}</div>`;
        } else {
            html += `<div class="docview-text docview-tenant docview-${rowClass}">${tenantContent}</div>`;
            html += `<div class="docview-text docview-template docview-${rowClass}">${templateContent}</div>`;
        }

        const whatChanged = (p.challenge_details || "").trim();
        const recommendedAction = (p.recommended_action || "").trim();
        if (isDeviationWorkflowProvision(p, currentTenantIndex) && (whatChanged || recommendedAction)) {
            html += `<div class="docview-clause-summary" style="grid-column: 1 / -1;">`;
            html += `<div class="detail-two-col">`;
            if (whatChanged) {
                html += `<div class="detail-section">
                    <div class="detail-label">What Changed</div>
                    <div class="detail-text">${renderDetailText(whatChanged)}</div>
                </div>`;
            }
            if (recommendedAction) {
                html += `<div class="detail-section">
                    <div class="detail-label">Why It Matters</div>
                    <div class="detail-text">${renderDetailText(recommendedAction)}</div>
                </div>`;
            }
            html += `</div>`;
            if (p.interpretation_note) {
                const _boldMd = window.CAMAuditShared && window.CAMAuditShared.boldMarkdown
                    ? window.CAMAuditShared.boldMarkdown
                    : (t) => esc(t);
                const _paras = p.interpretation_note.split(/\n\n+/).map(s => s.trim()).filter(Boolean);
                const _noteHtml = _paras.length <= 1
                    ? `<p>${_boldMd(p.interpretation_note)}</p>`
                    : _paras.map(s => `<p>${_boldMd(s)}</p>`).join("");
                html += `<div class="detail-section interpretation-note-section">
                    <div class="detail-label">Interpretation Note</div>
                    <div class="detail-text interpretation-note-body">${_noteHtml}</div>
                </div>`;
            }
            html += `</div>`;
        }

        if (isDeviationWorkflowProvision(p, currentTenantIndex)) {
            html += `<div class="docview-row-controls" style="grid-column: 1 / -1;">${buildDocviewDeviationControls(p, currentTenantIndex, {
                    esc,
                    resolutionState,
                    getDocviewDomIdSuffix,
                    buildDraftDecisionControls: buildDocviewDraftDecisionControls,
                    formatResTimestamp,
                    getConformingConcernState,
                    getFinalDraftDecision,
                    coverageAssessment: ((currentResults && currentResults.tenants && currentResults.tenants[currentTenantIndex]) || {}).results && currentResults.tenants[currentTenantIndex].results.coverage_assessment || [],
                })}</div>`;
        } else {
            html += `<div class="docview-row-controls" style="grid-column: 1 / -1;">${buildDocviewConformingControls(p, currentTenantIndex, {
                    esc,
                    resolutionState,
                    getDocviewDomIdSuffix,
                    buildDraftDecisionControls: buildDocviewDraftDecisionControls,
                    formatResTimestamp,
                    getConformingConcernState,
                    getFinalDraftDecision,
                    coverageAssessment: ((currentResults && currentResults.tenants && currentResults.tenants[currentTenantIndex]) || {}).results && currentResults.tenants[currentTenantIndex].results.coverage_assessment || [],
                })}</div>`;
        }

    });
    html += `</div>`;

    const container = $("#docview-container");
    container.className = "docview-container docview-container-sbs";
    container.innerHTML = html;
    hydrateRenderedDetailMarkdown(container);

    // Shared back-to-summary handler
    function handleBackToSummary() {
        switchResultsTab("findings");
        if (docviewReturnTarget) {
            const targetCard = document.getElementById(`dev-${docviewReturnTarget}`);
            if (targetCard) {
                setTimeout(() => {
                    targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                    targetCard.classList.add("highlight-flash");
                    setTimeout(() => targetCard.classList.remove("highlight-flash"), 1500);
                }, 100);
            }
            docviewReturnTarget = null;
        }
    }

    // Wire up back-to-summary link (top of grid)
    const backLink = container.querySelector(".docview-back-link");
    if (backLink) {
        backLink.addEventListener("click", handleBackToSummary);
    }

    // Populate side-by-side sidebar
    renderSbsSidebar(provisions, tenantLeads, r);
}

function renderSideBySideView() {
    const tenant = currentResults.tenants[currentTenantIndex];
    if (!tenant || !tenant.results) {
        $("#docview-container").innerHTML = '<div style="padding:2rem; text-align:center; color:var(--text-muted);">No results available for this tenant.</div>';
        $("#docview-sidebar-sbs").innerHTML = "";
        return;
    }

    const r = tenant.results;
    const provisions = sortProvisionsForDocviewTenantLed(getDocviewWorkflowProvisions(r.provisions || []));
    const templateFile = r.template_file || "Reference Lease";
    const tenantFile = r.tenant_file || tenant.filename || "Tenant Lease";
    const tenantLeads = docviewSort === "contract";

    const html = buildSideBySideDocviewMarkup(provisions, {
        tenantLeads,
        templateFile,
        tenantFile,
        tenantIdx: currentTenantIndex,
        modelsUsed: r.models_used || {},
        docviewSort,
        openDocviewProvision,
    });

    const container = $("#docview-container");
    container.className = "docview-container docview-container-sbs";
    container.innerHTML = html;
    hydrateRenderedDetailMarkdown(container);

    function handleBackToSummary() {
        switchResultsTab("findings");
        if (docviewReturnTarget) {
            const targetCard = document.getElementById(`dev-${docviewReturnTarget}`);
            if (targetCard) {
                setTimeout(() => {
                    targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                    targetCard.classList.add("highlight-flash");
                    setTimeout(() => targetCard.classList.remove("highlight-flash"), 1500);
                }, 100);
            }
            docviewReturnTarget = null;
        }
    }

    const backLink = container.querySelector(".docview-back-link");
    if (backLink) {
        backLink.addEventListener("click", handleBackToSummary);
    }

    renderSbsSidebar(provisions, tenantLeads, r);
}

function renderSbsSidebar(provisions, tenantLeads, results) {
    const sidebar = $("#docview-sidebar-sbs");
    if (!sidebar) return;

    sidebar.innerHTML = `<div class="fulldoc-sidebar-header">${tenantLeads ? "Tenant Lease Sections" : "Reference Lease Sections"}</div>`;

    const primaryFullText = tenantLeads
        ? ((results && results.full_tenant_text) || "")
        : ((results && results.full_template_text) || "");

    if (primaryFullText) {
        renderSidebarTOC(sidebar, primaryFullText, "sbs", { provisions, primarySide: tenantLeads ? "tenant" : "template" });
        return;
    }

    renderMappedSidebarTOC(sidebar, provisions, tenantLeads ? "tenant" : "template");
}

function renderMappedSidebarTOC(sidebar, provisions, primarySide = "tenant") {
    if (!sidebar) return;
    const seen = new Set();
    const refs = [];

    (provisions || []).forEach((p) => {
        const ref = primarySide === "tenant" ? (p.tenant_section_ref || "") : (p.template_section_ref || "");
        if (!ref || seen.has(ref)) return;
        seen.add(ref);
        refs.push(ref);
    });

    if (refs.length === 0) {
        sidebar.insertAdjacentHTML("beforeend", `<div class="fulldoc-sidebar-divider"></div><div class="sidebar-empty-note">No document sections available.</div>`);
        return;
    }

    const sectionTitle = primarySide === "tenant" ? "TENANT SECTIONS" : "REFERENCE SECTIONS";
    let html = `<div class="fulldoc-sidebar-divider"></div>
        <div class="sidebar-toc-toggle" id="toc-toggle-sbs-mapped">
            <span class="toc-arrow">&#9660;</span> ${sectionTitle}
        </div>
        <div class="sidebar-toc-content" id="toc-content-sbs-mapped">`;

    refs.forEach((ref, idx) => {
        html += `<div class="sidebar-toc-item" data-ref-idx="${idx}" data-ref-value="${esc(ref)}">${esc(ref)}</div>`;
    });
    html += `</div>`;
    sidebar.insertAdjacentHTML("beforeend", html);

    sidebar.querySelectorAll(".sidebar-toc-item[data-ref-value]").forEach((item) => {
        item.addEventListener("click", () => {
            const refValue = item.dataset.refValue || "";
            const selector = primarySide === "tenant"
                ? `.docview-provision-header[data-tenant-ref="${CSS.escape(refValue)}"]`
                : `.docview-provision-header[data-template-ref="${CSS.escape(refValue)}"]`;
            const target = document.querySelector(selector);
            if (target) {
                const mainPanel = $(".docview-main-sbs");
                scrollElementIntoPanelView(target, mainPanel, getDocviewJumpOffset(mainPanel));
                target.classList.add("highlight-flash");
                setTimeout(() => target.classList.remove("highlight-flash"), 1500);
            }
        });
    });
}

function toggleDocviewAnalysis(pid, provisions) {
    const container = $("#docview-container");
    const analysisHost = container.querySelector(".docview-sbs-body") || container;
    if (!provisions) {
        const tenant = currentResults && currentResults.tenants ? currentResults.tenants[currentTenantIndex] : null;
        provisions = sortProvisionsForDocviewTenantLed(getDocviewWorkflowProvisions((tenant && tenant.results && tenant.results.provisions) || []));
    }

    // Close any existing open panel
    const existing = analysisHost.querySelector(".docview-analysis");
    if (existing) {
        const existingPid = existing.dataset.pid;
        existing.remove();
        if (existingPid === pid) {
            openDocviewProvision = null;
            const toggleBtn = container.querySelector(`.docview-header-toggle[data-pid="${CSS.escape(pid)}"]`);
            if (toggleBtn) {
                toggleBtn.classList.remove("open");
                toggleBtn.innerHTML = "▾";
                toggleBtn.title = "Show analysis";
            }
            return; // Clicking same provision toggles off
        }
    }

    openDocviewProvision = pid;
    container.querySelectorAll(".docview-header-toggle").forEach((btn) => {
        btn.classList.toggle("open", btn.dataset.pid === pid);
        btn.innerHTML = btn.dataset.pid === pid ? "▴" : "▾";
        btn.title = btn.dataset.pid === pid ? "Hide analysis" : "Show analysis";
    });

    // Find the provision data
    const p = provisions.find(pr => pr.provision_id === pid);
    if (!p) return;

    const severity = p.severity || "";
    const icon = SEVERITY_ICONS[severity] || "";
    const riskHL = p.risk_headline || "";
    const challenge = p.challenge_details || "";
    const sevReasoning = p.severity_reasoning || "";
    const financial = p.financial_impact || "";
    const action = p.recommended_action || "";
    const verdicts = p.evaluator_verdicts || {};
    const agreeing = Object.values(verdicts).filter(v => v === "DEVIATES").length;
    const total = Object.keys(verdicts).length || 3;

    let panelHtml = `<div class="docview-analysis" data-pid="${esc(pid)}">
        <div class="docview-analysis-header">
            <span><span class="severity-badge severity-${severity}">${icon} ${sevDisplay(severity)}</span> &mdash; ${esc(p.provision_name || "")}</span>
            <button class="docview-analysis-close">&times;</button>
        </div>`;

    if (riskHL) {
        panelHtml += `<div class="risk-headline" style="padding:0 1rem;">${esc(riskHL)}</div>`;
    }
    if (challenge) {
        panelHtml += `<div class="detail-section">
            <div class="detail-label">What Changed</div>
            <div class="detail-text">${renderDetailText(challenge)}</div>
        </div>`;
    }
    if (sevReasoning) {
        panelHtml += `<div class="detail-section">
            <div class="detail-label">Impact</div>
            <div class="detail-text">${renderDetailText(sevReasoning)}</div>
        </div>`;
    }
    if (financial) {
        panelHtml += `<div class="detail-section">
            <div class="detail-label">Financial Impact</div>
            <div class="detail-text">${renderDetailText(financial)}</div>
        </div>`;
    }
    if (action) {
        panelHtml += `<div class="detail-section">
            <div class="detail-label">Why It Matters</div>
            <div class="detail-text">${renderDetailText(action)}</div>
        </div>`;
    }
    if (p.interpretation_note) {
        const _boldMd = window.CAMAuditShared && window.CAMAuditShared.boldMarkdown
            ? window.CAMAuditShared.boldMarkdown
            : (t) => esc(t);
        const _paras = p.interpretation_note.split(/\n\n+/).map(s => s.trim()).filter(Boolean);
        const _noteHtml = _paras.length <= 1
            ? `<p>${_boldMd(p.interpretation_note)}</p>`
            : _paras.map(s => `<p>${_boldMd(s)}</p>`).join("");
        panelHtml += `<div class="detail-section interpretation-note-section">
            <div class="detail-label">Interpretation Note</div>
            <div class="detail-text interpretation-note-body">${_noteHtml}</div>
        </div>`;
    }

    if (!riskHL && !challenge && !sevReasoning && !financial && !action) {
        panelHtml += `<div class="detail-section">
            <div class="detail-label">Analysis</div>
            <div class="detail-text">No narrative analysis is available for this clause yet. You can still review the text comparison, notes, and workflow tools from the summary page.</div>
        </div>`;
    }

    panelHtml += `<div class="evaluator-line">Evaluators: ${agreeing}/${total} agree DEVIATES</div>`;
    panelHtml += `<div class="docview-back-to-card" data-provision="${esc(pid)}">&#8592; Back to Summary</div>`;
    panelHtml += `</div>`;

    // Insert the panel after the provision's text cells (header + 2 text cells)
    const allChildren = Array.from(analysisHost.children);
    const headerEl = analysisHost.querySelector(`.docview-provision-header[data-pid="${pid}"]`);
    if (headerEl) {
        const headerIdx = allChildren.indexOf(headerEl);
        // After header come 2 text cells (headerIdx+1 = template, headerIdx+2 = tenant)
        const insertAfter = allChildren[headerIdx + 2] || headerEl;
        insertAfter.insertAdjacentHTML("afterend", panelHtml);
    }

    // Wire close button
    const panel = analysisHost.querySelector(`.docview-analysis[data-pid="${pid}"]`);
    if (panel) {
        panel.querySelector(".docview-analysis-close").addEventListener("click", () => {
            panel.remove();
            openDocviewProvision = null;
        });
        // Wire "Back to Summary" link
        const backLink = panel.querySelector(".docview-back-to-card");
        if (backLink) {
            backLink.addEventListener("click", () => {
                switchResultsTab("findings");
                const targetCard = document.getElementById(`dev-${pid}`);
                if (targetCard) {
                    setTimeout(() => {
                        targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
                        targetCard.classList.add("highlight-flash");
                        setTimeout(() => targetCard.classList.remove("highlight-flash"), 1500);
                    }, 100);
                }
            });
        }
    }
}

// ── Feedback ──

async function submitFeedback(provisionId, assessment, btn) {
    if (!currentJobId) return;

    // Support both new card-quick-feedback and old feedback-area
    const area = btn.closest(".card-quick-feedback") || btn.closest(".feedback-area");
    if (!area) return;

    const savedEl = area.querySelector(".quick-feedback-saved") ||
                    area.querySelector(".feedback-saved");

    // Mark button as selected
    area.querySelectorAll(".qfb, [data-assessment]").forEach(b => {
        b.classList.remove("qfb-selected", "active");
    });
    btn.classList.add("qfb-selected");

    // Show confirmation inline
    if (savedEl) {
        const labels = { agree: "Flagged \u2713", disagree: "Dismissed \u2713", unsure: "Noted \u2713" };
        savedEl.textContent = labels[assessment] || "Saved \u2713";
        savedEl.classList.remove("hidden");
    }

    try {
        await fetch(`/api/jobs/${currentJobId}/feedback`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                tenant_index: currentTenantIndex,
                provision_id: provisionId,
                assessment: assessment,
            })
        });
    } catch (err) {
        console.error("Feedback error:", err);
    }

    // Show inline follow-up prompt when user clicks "No" (disagree)
    if (assessment === 'disagree') {
        const existing = area.querySelector('.qfb-followup');
        if (existing) existing.remove();

        const pname = btn.closest('.finding-card')?.dataset?.provision || provisionId;
        const followup = document.createElement('div');
        followup.className = 'qfb-followup';
        followup.dataset.pid = provisionId;
        followup.dataset.pname = pname;
        followup.innerHTML = `
            <span class="qfb-followup-msg">This finding will remain visible in this run.
            Want to create a rule so it won't be flagged in future analyses?</span>
            <div class="qfb-followup-btns">
                <button class="qfb-followup-yes">Create Rule</button>
                <button class="qfb-followup-cancel">Cancel</button>
            </div>`;

        followup.querySelector('.qfb-followup-yes').addEventListener('click', (e) => {
            e.stopPropagation();
            window.CAM.showRuleCreationDialog(provisionId, pname);
            followup.remove();
        });
        followup.querySelector('.qfb-followup-cancel').addEventListener('click', (e) => {
            e.stopPropagation();
            followup.remove();
        });

        area.appendChild(followup);
    }
}

function loadExistingFeedback() {
    if (!currentJobData || !currentJobData.feedback) return;

    const feedback = currentJobData.feedback.filter(
        f => f.tenant_index === currentTenantIndex
    );

    feedback.forEach(f => {
        // Try new quick-feedback first, fall back to old feedback-area
        const area = document.querySelector(`.card-quick-feedback[data-pid="${f.provision_id}"]`)
                  || document.querySelector(`.feedback-area[data-pid="${f.provision_id}"]`);
        if (!area) return;

        const labels = { agree: "Flagged \u2713", disagree: "Dismissed \u2713", unsure: "Noted \u2713" };
        const savedEl = area.querySelector(".quick-feedback-saved") ||
                        area.querySelector(".feedback-saved");
        if (savedEl) {
            savedEl.textContent = labels[f.assessment] || "Saved";
            savedEl.classList.remove("hidden");
        }
        // Mark the matching button selected
        const btn = area.querySelector(`[data-assessment="${f.assessment}"]`);
        if (btn) {
            area.querySelectorAll(".qfb, [data-assessment]").forEach(b => {
                b.classList.remove("qfb-selected", "active");
            });
            btn.classList.add("qfb-selected");
        }
    });
}

// ── Downloads & Export ──

function _triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function downloadFile(url) {
    const a = document.createElement("a");
    a.href = url;
    a.download = "";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function exportAllJSON() {
    if (!currentResults) return;
    const blob = new Blob([JSON.stringify(currentResults, null, 2)], {type: "application/json"});
    _triggerDownload(blob, `CAM_Results_${currentJobId || "export"}.json`);
}

function exportTenantJSON(idx) {
    if (!currentResults || !currentResults.tenants[idx]) return;
    const data = currentResults.tenants[idx];
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: "application/json"});
    _triggerDownload(blob, `CAM_Results_${data.filename || "tenant"}.json`);
}

function exportAuditJSON(singleContract) {
    if (!currentResults) return;
    const jobId = currentJobId || "unknown";
    const date = new Date().toISOString().slice(0, 10);
    const scope = singleContract ? `_T${currentTenantIndex + 1}` : "_all";
    const filename = `CAM_Audit_Trail_${jobId}${scope}_${date}.json`;

    const allTenants = currentResults.tenants || [];
    const tenantsToExport = singleContract ? [allTenants[currentTenantIndex]].filter(Boolean) : allTenants;
    const totalProvisions = tenantsToExport.reduce((sum, t) => sum + (((t || {}).results || {}).provisions || []).length, 0);
    const totalElapsed = tenantsToExport.reduce((sum, t) => sum + ((((t || {}).results || {}).elapsed_sec) || 0), 0);
    const totalCalls = tenantsToExport.reduce((sum, t) => sum + ((((t || {}).results || {}).api_calls_total) || 0), 0);
    const primaryResults = tenantsToExport[0] && tenantsToExport[0].results ? tenantsToExport[0].results : null;
    const primaryModels = primaryResults ? (primaryResults.models_used || {}) : {};

    // Build export object: job-level metadata + per-tenant pipeline results
    const exportObj = {
        export_type: singleContract ? "CAM Audit Trail (Single Contract)" : "CAM Audit Trail (All Contracts)",
        exported_at: new Date().toISOString(),
        job_id: jobId,
        review_context: primaryResults ? {
            reference_document: primaryResults.template_file || null,
            pipeline_version: primaryResults.pipeline_version || null,
            pipeline_domain_label: primaryResults.pipeline_domain_label || null,
        } : null,
        cam_reviewers: primaryResults ? {
            extraction: primaryModels.extractor ? getModelDisplayName(primaryModels.extractor) : null,
            provision_comparison: [
                primaryModels.evaluator_a,
                primaryModels.evaluator_b,
                primaryModels.evaluator_c,
            ].filter(Boolean).map(getModelDisplayName),
            challenge_review: primaryModels.challenger ? getModelDisplayName(primaryModels.challenger) : null,
            severity_review: primaryModels.severity_assessor ? getModelDisplayName(primaryModels.severity_assessor) : null,
        } : null,
        run_stats: {
            contracts_included: tenantsToExport.length,
            provisions_reviewed: totalProvisions,
            actual_runtime_sec: totalElapsed,
            model_calls: totalCalls,
        },
        tenants: tenantsToExport.map((t) => {
            const tenantIdx = allTenants.indexOf(t);
            const workflowProvisions = getTenantWorkflowProvisions(tenantIdx);
            return {
                filename: t.filename,
                pipeline_version: t.results && t.results.pipeline_version,
                pipeline_domain_label: t.results && t.results.pipeline_domain_label,
                timestamp: t.results && t.results.timestamp,
                models_used: t.results && t.results.models_used,
                api_calls_total: t.results && t.results.api_calls_total,
                elapsed_sec: t.results && t.results.elapsed_sec,
                summary: t.results && t.results.summary,
                provisions: workflowProvisions.map((p) => serializeProvisionForAuditExport(p, tenantIdx)),
            };
        }),
    };

    const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: "application/json" });
    _triggerDownload(blob, filename);
}

function exportAuditText(singleContract) {
    if (!currentResults) return;
    const jobId = currentJobId || "unknown";
    const date = new Date().toISOString().slice(0, 10);
    const scope = singleContract ? `_T${currentTenantIndex + 1}` : "_all";
    const filename = `CAM_Audit_Report_${jobId}${scope}_${date}.txt`;

    const allTenants = currentResults.tenants || [];
    const tenantsToExport = singleContract ? [allTenants[currentTenantIndex]].filter(Boolean) : allTenants;

    const STAGE_NAMES = {1:"Extraction",2:"Rules Check",3:"Evaluation",4:"Challenge",5:"Severity",6:"Disposition"};
    const lines = [];
    const hr = (char = "\u2550", n = 72) => char.repeat(n);
    const sep = (char = "\u2500", n = 56) => char.repeat(n);

    lines.push("CAM\u2122 AUDIT TRAIL REPORT");
    lines.push(`Patent Pending \u00b7 ${new Date().toLocaleString()}`);
    lines.push(`Job ID: ${jobId}`);
    lines.push(singleContract ? `Scope: Single Contract (T${currentTenantIndex + 1})` : "Scope: All Contracts");
    lines.push(hr());
    lines.push("");

    tenantsToExport.forEach((tenant, ti) => {
        const tenantIdx = allTenants.indexOf(tenant);
        const r = tenant.results || {};
        const m = r.models_used || {};
        const workflowProvisions = getTenantWorkflowProvisions(tenantIdx);
        lines.push(hr("\u2550"));
        lines.push(`TENANT ${ti + 1}: ${tenant.filename || "Unknown"}`);
        lines.push(hr("\u2550"));
        lines.push("");

        // Run metadata
        lines.push("RUN METADATA");
        lines.push(sep());
        lines.push(`Pipeline:   ${r.pipeline_version || "\u2014"} \u00b7 ${r.pipeline_domain_label || ""}`);
        lines.push(`Timestamp:  ${r.timestamp || "\u2014"}`);
        lines.push(`Template:   ${r.template_file || "\u2014"}`);
        lines.push(`API calls:  ${r.api_calls_total || "\u2014"}  |  Elapsed: ${r.elapsed_sec ? fmtDuration(r.elapsed_sec) : "\u2014"}`);
        lines.push(`Workflow clauses: ${workflowProvisions.length}`);
        lines.push("");

        lines.push("MODELS USED");
        lines.push(sep());
        if (m.extractor) lines.push(`  Extractor:   ${m.extractor} (${m.extractor_provider || ""})`);
        if (m.evaluator_a) lines.push(`  ${evalName('A')}: ${m.evaluator_a} (${m.evaluator_a_provider || ""})`);
        if (m.evaluator_b) lines.push(`  ${evalName('B')}: ${m.evaluator_b} (${m.evaluator_b_provider || ""})`);
        if (m.evaluator_c) lines.push(`  ${evalName('C')}: ${m.evaluator_c} (${m.evaluator_c_provider || ""})`);
        if (m.challenger)  lines.push(`  Challenger:  ${m.challenger}`);
        if (m.severity_assessor) lines.push(`  Severity:    ${m.severity_assessor}`);
        lines.push("");

        // Per-provision trace
        lines.push("PROVISION PIPELINE TRACES");
        lines.push(sep());
        lines.push("");

        workflowProvisions.forEach(p => {
            const meta = p.cam_metadata || {};
            const stagesRun = new Set(meta.stages_run || []);
            const rulesFired = meta.rules_fired || [];
            const frag = p.fragility || {};
            const workflow = getProvisionWorkflowExportState(tenantIdx, p.provision_id || "");

            lines.push(`[${p.provision_id || ""}] ${p.provision_name || ""}`);
            lines.push(`  Final Verdict: ${p.final_verdict || "\u2014"}  |  Severity: ${p.severity || "\u2014"}${p.severity_floor_applied ? " (floor applied)" : ""}`);
            lines.push(`  Workflow: ${workflow.status || "open"}${p.manual_escalation ? "  |  Manual escalation: yes" : ""}${workflow.read ? "  |  Read: yes" : ""}`);
            if ((workflow.notes || []).length > 0) lines.push(`  Notes: ${workflow.notes.length}`);
            lines.push(`  Agreement: ${p.agreement_pattern || "\u2014"}`);
            lines.push("");

            lines.push("  PIPELINE STAGES:");
            [1,2,3,4,5,6].forEach(s => {
                const ran = stagesRun.has(s);
                let note = ran ? "" : " \u2014 skipped";
                if (s === 2 && ran) note = ` \u2192 rules: ${rulesFired.length > 0 ? rulesFired.join(", ") : "none"} \u2192 ${meta.triage_result || ""}`;
                if (s === 4 && ran && p.challenge_finding) note = ` \u2192 ${p.challenge_finding}`;
                lines.push(`    ${ran ? "\u2713" : "\u2298"} Stage ${s}: ${STAGE_NAMES[s]}${note}`);
            });
            lines.push("");

            lines.push("  EVALUATOR VOTES:");
            ["A","B","C"].forEach(k => {
                const verdict = (p.evaluator_verdicts || {})[k] || "unavailable";
                const conf = (p.evaluator_confidences || {})[k];
                const confStr = conf != null && conf > 0 ? ` (confidence: ${conf.toFixed(2)})` : "";
                const reasoning = (p.evaluator_reasoning || {})[k] || "";
                lines.push(`    ${k}: ${verdict}${confStr}`);
                if (reasoning && reasoning !== "(evaluator unavailable)") {
                    // Wrap reasoning at ~70 chars
                    const wrapped = reasoning.match(/.{1,70}(\s|$)/g) || [reasoning];
                    wrapped.forEach(line => lines.push(`       ${line.trim()}`));
                }
            });
            lines.push("");

            if (p.challenge_finding) {
                lines.push(`  CHALLENGE: ${p.challenge_finding}`);
                if (p.challenge_details) lines.push(`    ${p.challenge_details}`);
                lines.push("");
            }

            if (frag.fragile != null) {
                lines.push(`  FRAGILITY: ${frag.fragile ? "yes" : "no"}${frag.score != null ? " (score: " + frag.score.toFixed(3) + ")" : ""}`);
                if ((frag.signals || []).length > 0) {
                    lines.push(`    Signals: ${frag.signals.join(", ")}`);
                }
                lines.push("");
            }

            lines.push(sep("\u00b7", 40));
            lines.push("");
        });
    });

    lines.push(hr());
    lines.push("Generated by CAM\u2122 \u00b7 Patent Pending \u00b7 This is a diagnostic tool, not legal advice.");

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    _triggerDownload(blob, filename);
}

// ── Direct Job Load (from URL) ──

async function loadJobDirect(jobId) {
    await loadModelNames(); // ensure evalName() is ready before any rendering
    currentJobId = jobId;

    setupEventListeners();

    try {
        const resp = await fetch(`/api/jobs/${jobId}`);

        if (resp.status === 410) {
            showExpiredPage();
            return;
        }
        if (!resp.ok) {
            showState("gate");
            return;
        }

        const job = await resp.json();
        currentJobData = job;

        // Restore email state from server
        if (job.email) setJobEmail(job.email);

        if (job.status === "completed") {
            await loadResults();
            showState("results");
        } else if (job.status === "cancelled") {
            showState("processing");
            handleCancelledJob(job);
        } else if (job.status === "processing" || job.status === "queued") {
            showState("processing");
            initProcessingView(job);
            startPolling();
        } else if (job.status === "failed") {
            showState("processing");
            renderProgress(job);
            const container = $("#tenant-progress-list");
            container.innerHTML += `<div class="alert alert-error mt-2">${esc(job.error || "Analysis failed.")}</div>`;
        }
    } catch (err) {
        console.error("Direct load error:", err);
        showState("gate");
    }
}

// ── Helpers ──

/**
 * computeWordDiff(templateText, tenantText)
 * Returns { templateHtml, tenantHtml } with inline span highlights.
 * Uses LCS (longest common subsequence) on word tokens.
 */
function computeWordDiff(templateText, tenantText) {
    function tokenize(text) {
        return text.match(/\S+|\s+/g) || [];
    }

    const tplTokens = tokenize(templateText);
    const tenTokens = tokenize(tenantText);
    const m = tplTokens.length;
    const n = tenTokens.length;

    // For large texts, fall back to sentence-level diff
    if (m > 400 || n > 400) {
        return fallbackDiff(templateText, tenantText);
    }

    const dp = Array.from({ length: m + 1 }, () => new Int16Array(n + 1));
    for (let i = m - 1; i >= 0; i--) {
        for (let j = n - 1; j >= 0; j--) {
            if (tplTokens[i] === tenTokens[j]) {
                dp[i][j] = dp[i + 1][j + 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
            }
        }
    }

    let tplHtml = "";
    let tenHtml = "";
    let i = 0, j = 0;

    while (i < m || j < n) {
        if (i < m && j < n && tplTokens[i] === tenTokens[j]) {
            tplHtml += esc(tplTokens[i]);
            tenHtml += esc(tenTokens[j]);
            i++; j++;
        } else if (j < n && (i >= m || dp[i][j + 1] >= dp[i + 1][j])) {
            if (tenTokens[j].trim()) {
                tenHtml += `<span class="diff-added">${esc(tenTokens[j])}</span>`;
            } else {
                tenHtml += esc(tenTokens[j]);
            }
            j++;
        } else {
            if (tplTokens[i].trim()) {
                tplHtml += `<span class="diff-removed">${esc(tplTokens[i])}</span>`;
            } else {
                tplHtml += esc(tplTokens[i]);
            }
            i++;
        }
    }

    return { templateHtml: tplHtml, tenantHtml: tenHtml };
}

/**
 * Fallback for long texts: sentence-level diff.
 */
function fallbackDiff(templateText, tenantText) {
    const tplSentences = templateText.split(/(?<=[.!?])\s+/);
    const tenSentences = tenantText.split(/(?<=[.!?])\s+/);
    const tplSet = new Set(tplSentences.map(s => s.trim()));
    const tenSet = new Set(tenSentences.map(s => s.trim()));

    const tplHtml = tplSentences.map(s =>
        tenSet.has(s.trim())
            ? esc(s)
            : `<span class="diff-removed">${esc(s)}</span>`
    ).join(" ");

    const tenHtml = tenSentences.map(s =>
        tplSet.has(s.trim())
            ? esc(s)
            : `<span class="diff-added">${esc(s)}</span>`
    ).join(" ");

    return { templateHtml: tplHtml, tenantHtml: tenHtml };
}

function esc(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
}

function getHighestSeverity(summary) {
    for (const sev of SEVERITY_ORDER) {
        if (summary[sev.toLowerCase()] > 0) return sev;
    }
    return "CONFORMS";
}

// Step 129: Status label for contract selector dropdown
function getStatusLabel(highestSev) {
    if (!highestSev || highestSev === 'CONFORMS') return 'Clear';
    if (highestSev === 'CRITICAL') return 'Immediate Action';
    if (highestSev === 'HIGH') return 'Review Recommended';
    if (highestSev === 'MEDIUM') return 'Monitor';
    if (highestSev === 'LOW') return 'Monitor';
    return 'Clear';
}

// Step 125: Build one-sentence lease blurb from structured fields
function buildLeaseBlurb(tenantResult) {
    if (!tenantResult) return null;
    var deal = tenantResult.deal_overview || {};
    var meta = tenantResult.contract_metadata || {};
    var parts = [];

    // Term
    var term = deal.lease_term_years
        ? (deal.lease_term_years + '-year')
        : (meta.term_length || null);
    if (term) parts.push(term);

    // CAM structure (net vs gross)
    var cam = (deal.cam_structure || '').toLowerCase();
    if (cam.indexOf('triple net') !== -1 || cam.indexOf('nnn') !== -1) parts.push('triple net');
    else if (cam.indexOf('gross') !== -1) parts.push('gross');

    // Always "retail lease"
    parts.push('retail lease');

    // Renewal
    var renewal = deal.renewal_options || meta.renewal_options || '';
    if (renewal && renewal.toLowerCase() !== 'none' && renewal.trim() !== '') {
        var r = renewal.replace(/one \(1\)/ig, 'one')
                       .replace(/additional period of /ig, '')
                       .replace(/\(\d+\)/g, '').trim().toLowerCase();
        if (r) parts.push('with ' + r);
    }

    if (parts.length <= 1) return null; // just "retail lease" — not useful
    return parts.join(' ').replace(/\s+/g, ' ').trim() + '.';
}

function getRiskRating(summary) {
    if (summary.critical > 0 || summary.high >= 2) {
        return {label: "\uD83D\uDD34 HIGH", class: "risk-high"};
    }
    if (summary.high > 0 || summary.medium >= 2) {
        return {label: "\u26A0\uFE0F MEDIUM", class: "risk-medium"};
    }
    if (summary.deviates > 0) {
        return {label: "LOW", class: "risk-low"};
    }
    return {label: "\u2705 CLEAR", class: "risk-low"};
}

// ══════════════════════════════════════════════════════
// Document View Text Search (039t Item 3)
// ══════════════════════════════════════════════════════

let searchMatches = [];
let searchCurrentIndex = -1;
let searchDebounceTimer = null;

function initDocviewSearch() {
    const input = $("#docview-search-input");
    const prevBtn = $("#docview-search-prev");
    const nextBtn = $("#docview-search-next");
    const clearBtn = $("#docview-search-clear");

    if (!input) return;

    input.addEventListener("input", () => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => performDocSearch(input.value), 300);
    });
    input.addEventListener("keydown", e => {
        if (e.key === "Enter") {
            e.preventDefault();
            if (e.shiftKey) navigateSearch(-1);
            else navigateSearch(1);
        }
    });
    prevBtn.addEventListener("click", () => navigateSearch(-1));
    nextBtn.addEventListener("click", () => navigateSearch(1));
    clearBtn.addEventListener("click", () => {
        input.value = "";
        clearDocSearch();
        input.focus();
    });
}

function getSearchTarget() {
    // Get the visible content panel based on current view mode
    if (docviewMode === "full") {
        return $("#docview-main");
    } else {
        return $("#docview-container");
    }
}

function performDocSearch(query) {
    clearDocSearch();
    if (!query || query.length < 2) {
        $("#docview-search-count").textContent = "";
        return;
    }

    const target = getSearchTarget();
    if (!target) return;

    const searchText = query.toLowerCase();

    // Walk text nodes and wrap matches
    const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT, null);
    const textNodes = [];
    while (walker.nextNode()) {
        // Skip nodes inside search bar or callout links
        if (walker.currentNode.parentElement.closest(".docview-search-bar")) continue;
        textNodes.push(walker.currentNode);
    }

    textNodes.forEach(node => {
        const text = node.textContent;
        const lower = text.toLowerCase();
        let idx = lower.indexOf(searchText);
        if (idx === -1) return;

        const frag = document.createDocumentFragment();
        let cursor = 0;

        while (idx !== -1) {
            // Text before match
            if (idx > cursor) {
                frag.appendChild(document.createTextNode(text.substring(cursor, idx)));
            }
            // Match
            const mark = document.createElement("mark");
            mark.className = "search-match";
            mark.textContent = text.substring(idx, idx + searchText.length);
            frag.appendChild(mark);
            searchMatches.push(mark);

            cursor = idx + searchText.length;
            idx = lower.indexOf(searchText, cursor);
        }
        // Text after last match
        if (cursor < text.length) {
            frag.appendChild(document.createTextNode(text.substring(cursor)));
        }
        node.parentNode.replaceChild(frag, node);
    });

    const countEl = $("#docview-search-count");
    if (searchMatches.length > 0) {
        searchCurrentIndex = 0;
        updateSearchActive();
        countEl.textContent = `1 of ${searchMatches.length}`;
    } else {
        countEl.textContent = "No matches";
    }
}

function navigateSearch(direction) {
    if (searchMatches.length === 0) return;
    searchCurrentIndex = (searchCurrentIndex + direction + searchMatches.length) % searchMatches.length;
    updateSearchActive();
    $("#docview-search-count").textContent = `${searchCurrentIndex + 1} of ${searchMatches.length}`;
}

function updateSearchActive() {
    searchMatches.forEach((m, i) => {
        m.className = i === searchCurrentIndex ? "search-match-active" : "search-match";
    });
    if (searchMatches[searchCurrentIndex]) {
        searchMatches[searchCurrentIndex].scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function clearDocSearch() {
    // Remove all <mark> elements and restore text
    const target = getSearchTarget();
    if (target) {
        target.querySelectorAll("mark.search-match, mark.search-match-active").forEach(mark => {
            const parent = mark.parentNode;
            parent.replaceChild(document.createTextNode(mark.textContent), mark);
            parent.normalize();
        });
    }
    searchMatches = [];
    searchCurrentIndex = -1;
    const countEl = $("#docview-search-count");
    if (countEl) countEl.textContent = "";
}

// ══════════════════════════════════════════════════════
// FOLLOW-UP Q&A CHAT — Always-On Panel (039v)
// ══════════════════════════════════════════════════════

let chatInitialized = false;

// ── Multi-Model Chat Guards (039z) ──

function updateSynthesizerDefault() {
    const checked = new Set(
        Array.from(document.querySelectorAll('#chat-model-options input[type=checkbox]:checked'))
            .map(cb => cb.value)
    );
    const all = ["claude", "gpt", "grok", "gemini"];
    const synthSelect = $("#chat-synthesizer-select");
    if (!synthSelect) return;

    // Find first model not in the checked set
    const preferred = all.find(m => !checked.has(m));
    if (preferred) {
        synthSelect.value = preferred;
    } else {
        synthSelect.value = "claude";
    }

    // Grey out options that ARE in the checked set
    Array.from(synthSelect.options).forEach(opt => {
        opt.disabled = checked.has(opt.value);
        if (opt.disabled && synthSelect.value === opt.value) {
            synthSelect.value = preferred || "claude";
        }
    });
}

function updateSynthesisAvailability() {
    const checkedCount = document.querySelectorAll('#chat-model-options input[type=checkbox]:checked').length;
    const synthRadio = document.querySelector('input[name="synth-mode"][value="synthesized"]');
    const synthLabel = synthRadio?.closest('.synth-option');
    const individualRadio = document.querySelector('input[name="synth-mode"][value="individual"]');
    const hintEl = $("#chat-synth-hint");

    if (checkedCount <= 1) {
        if (synthRadio) {
            synthRadio.disabled = true;
            if (synthLabel) synthLabel.style.opacity = "0.4";
            if (individualRadio) individualRadio.checked = true;
            individualRadio?.dispatchEvent(new Event("change"));
        }
        if (hintEl) {
            hintEl.textContent = checkedCount === 1 ? "Select 2+ models to synthesize" : "";
            hintEl.classList.remove("hidden");
        }
    } else {
        if (synthRadio) {
            synthRadio.disabled = false;
            if (synthLabel) synthLabel.style.opacity = "";
        }
        if (hintEl) hintEl.classList.add("hidden");
    }
}

function updateAskButtonState() {
    const checkedCount = document.querySelectorAll('#chat-model-options input[type=checkbox]:checked').length;
    const isMulti = $("#chat-mode-select")?.value === "multi";
    const sendBtn = $("#chat-send-btn");
    if (!sendBtn) return;

    if (isMulti && checkedCount === 0) {
        sendBtn.disabled = true;
        sendBtn.title = "Select at least one model";
    } else {
        sendBtn.disabled = false;
        sendBtn.title = "";
    }
}

function renderAnalysisChatWelcome() {
    const messagesEl = $("#chat-messages");
    if (!messagesEl) return;
    if (messagesEl.querySelector(".chat-analysis-welcome")) return;

    const isScoped = chatScopeTenantIdx !== "" || chatScopeProvisionId !== "";
    const isDraftMode = isScoped && chatStarterMode === "draft";
    // Step 259: Mode C uses a coverage/issue-area mental model, not deviation/template.
    // Branch starters by mode first so the suggestions match what the user is actually
    // looking at — there are no "deviations" or "reference language" in Mode C.
    const isModeC = (typeof isJobModeC === 'function') && isJobModeC();
    const starters = isModeC
        ? (isDraftMode
            ? [
                "Draft language to address this gap",
                "What standard language should I push for here?",
                "Make this more tenant-friendly",
                "Draft a fallback if the landlord pushes back",
            ]
            : isScoped
            ? [
                "What's the coverage status of this clause?",
                "Why is this flagged?",
                "What language should I negotiate for?",
                "What's the risk if I leave this as-is?",
            ]
            : [
                "Where does this lease have coverage gaps?",
                "Which issue areas need attention first?",
                "What clauses are missing or unfavorable?",
                "What should I push back on?",
            ])
        : (isDraftMode
        ? [
            "What is CAM trying to fix in this provision?",
            "Draft balanced replacement language for this provision",
            "Make this more landlord-friendly",
            "Narrow the change to just one point",
            "Draft a reasonable fallback position",
            "Draft a compromise clause I can mark up",
        ]
        : isScoped
        ? [
            "What did CAM conclude here?",
            "Why was this flagged?",
            "How confident is this result?",
            "What should I do next on this issue?",
            "Draft replacement language for this provision",
        ]
        : [
            "What did CAM find in this lease?",
            "Which findings should I review first?",
            "What should I do next with these results?",
            "What are the biggest negotiation risks?",
        ]);

    const welcome = document.createElement("div");
    welcome.className = "chat-analysis-welcome";
    welcome.innerHTML =
        (isDraftMode
            ? "Use chat to understand what CAM wants changed, then draft and refine replacement language for this provision."
            : isScoped
            ? "Use chat to understand this issue, why CAM flagged it, and what a practical next step looks like."
            : "Use chat to understand what CAM found, decide what to review first, and plan your next move.") +
        '<div class="chat-analysis-starters">' +
        starters.map(s => `<button class="chat-analysis-starter" onclick="window.CAM.askAnalysisQuestion(this.textContent)">${esc(s)}</button>`).join("") +
        '</div>';
    messagesEl.appendChild(welcome);
}

function refreshAnalysisChatWelcome() {
    const messagesEl = $("#chat-messages");
    if (!messagesEl) return;
    const welcome = messagesEl.querySelector(".chat-analysis-welcome");
    if (welcome) welcome.remove();
    if (!messagesEl.querySelector(".chat-msg")) renderAnalysisChatWelcome();
}

function initChat() {
    if (chatInitialized) return;
    const sendBtn = $("#chat-send-btn");
    const input = $("#chat-input");
    const modeSelect = $("#chat-mode-select");
    const multiOptions = $("#chat-multi-options");

    if (!sendBtn || !input) return;
    chatInitialized = true;
    renderAnalysisChatWelcome();

    sendBtn.addEventListener("click", () => sendChatMessage());
    input.addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    if (modeSelect) {
        modeSelect.addEventListener("change", () => {
            if (multiOptions) multiOptions.classList.toggle("hidden", modeSelect.value !== "multi");
            // Run guards when switching to multi mode
            if (modeSelect.value === "multi") {
                updateSynthesisAvailability();
                updateSynthesizerDefault();
                updateAskButtonState();
            } else {
                // Re-enable Ask button for single mode
                sendBtn.disabled = false;
                sendBtn.title = "";
            }
        });
    }

    // Checkbox change listeners — run all guards
    document.querySelectorAll('#chat-model-options input[type=checkbox]').forEach(cb => {
        cb.addEventListener("change", () => {
            updateSynthesisAvailability();
            updateSynthesizerDefault();
            updateAskButtonState();
        });
    });

    // Synth radio change — show/hide synthesizer row
    document.querySelectorAll('input[name="synth-mode"]').forEach(radio => {
        radio.addEventListener("change", () => {
            const isSynth = document.querySelector('input[name="synth-mode"]:checked')?.value === "synthesized";
            const synthRow = $("#chat-synthesizer-row");
            if (synthRow) synthRow.classList.toggle("hidden", !isSynth);
        });
    });
}

// ── Panel Resize Handle (Item 1) ──
function syncResultsTopBarLayout() {
    const root = document.documentElement;
    if (!root) return;

    const isNarrow = window.innerWidth <= 900;
    const chatPanel = $("#chat-panel");
    const navSidebar = $("#nav-sidebar");
    const chatVisible = chatPanel && getComputedStyle(chatPanel).display !== "none";
    const navVisible = navSidebar && getComputedStyle(navSidebar).display !== "none";

    root.style.setProperty("--chat-panel-width", (!isNarrow && chatVisible) ? `${chatPanel.offsetWidth}px` : "0px");
    root.style.setProperty("--results-sidebar-width", (!isNarrow && navVisible) ? `${navSidebar.offsetWidth}px` : "0px");
}

function initPanelResize() {
    const handle = $("#chat-panel-resize");
    const panel = $("#chat-panel");
    syncResultsTopBarLayout();
    if (!resultsTopBarLayoutBound) {
        window.addEventListener("resize", syncResultsTopBarLayout);
        resultsTopBarLayoutBound = true;
    }
    if (!handle || !panel) return;

    let startX, startWidth;

    function onMouseDown(e) {
        e.preventDefault();
        startX = e.clientX;
        startWidth = panel.offsetWidth;
        handle.classList.add("active");
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    }

    function onMouseMove(e) {
        const dx = startX - e.clientX; // dragging left = wider
        let newWidth = startWidth + dx;
        newWidth = Math.max(320, Math.min(newWidth, window.innerWidth * 0.7));
        panel.style.width = newWidth + "px";
        syncResultsTopBarLayout();
    }

    function onMouseUp() {
        handle.classList.remove("active");
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        syncResultsTopBarLayout();
    }

    handle.addEventListener("mousedown", onMouseDown);
}

// ── Export Chat (Item 3) ──
function exportChat() {
    if (chatHistory.length === 0) return;

    const messagesEl = $("#chat-messages");
    if (!messagesEl) return;

    let text = "CAM Lease Analysis — Chat Transcript\n";
    text += "Date: " + new Date().toLocaleDateString() + "\n";
    text += "=".repeat(50) + "\n\n";

    messagesEl.querySelectorAll(".chat-msg").forEach(msg => {
        if (msg.classList.contains("chat-msg-user")) {
            text += "YOU:\n" + msg.textContent.trim() + "\n\n";
        } else if (msg.classList.contains("chat-msg-ai")) {
            const label = msg.querySelector(".chat-msg-label");
            const modelName = label ? label.textContent.trim() : "AI";
            const content = msg.cloneNode(true);
            const labelEl = content.querySelector(".chat-msg-label");
            if (labelEl) labelEl.remove();
            text += modelName.toUpperCase() + ":\n" + content.textContent.trim() + "\n\n";
        } else if (msg.classList.contains("chat-msg-synthesis")) {
            text += "NOTE:\n" + msg.textContent.trim() + "\n\n";
        }
        text += "-".repeat(50) + "\n\n";
    });

    text += "\nDisclaimer: AI-generated analysis — not legal advice.\n";

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lease_chat_${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Linkify Provisions in Chat Responses (Item 7) ──
function linkifyChatProvisions(html) {
    if (!html) return html;

    // Match LP-XX provision IDs
    html = html.replace(/\b(LP-\d{2})\b/g, (match, pid) => {
        return `<a class="chat-provision-link" href="#" onclick="window.CAM.jumpToProvision('${pid}'); return false;">${match}</a>`;
    });

    // Match Section X.X references
    html = html.replace(/\b(Section\s+\d+\.\d+)\b/gi, (match, section) => {
        return `<a class="chat-provision-link" href="#" onclick="window.CAM.searchInDoc('${section}'); return false;">${match}</a>`;
    });

    return html;
}

function jumpToProvision(pid) {
    jumpToFinding(pid);
}

function searchInDoc(text) {
    // Switch to document comparison tab
    switchResultsTab("docview");

    // Trigger search
    setTimeout(() => {
        const searchInput = $("#docview-search-input");
        if (searchInput) {
            searchInput.value = text;
            searchInput.dispatchEvent(new Event("input", { bubbles: true }));
        }
    }, 200);
}

function formatChatResponse(text) {
    if (!text) return "";

    // Item 8: Extract code blocks before HTML escaping, replace with placeholders
    const codeBlocks = [];
    text = text.replace(/```[\w]*\n?([\s\S]*?)```/g, (match, code) => {
        const idx = codeBlocks.length;
        codeBlocks.push(code.trim());
        return `%%CODEBLOCK_${idx}%%`;
    });

    // HTML escape
    text = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Markdown formatting
    text = text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/^### (.*?)$/gm, "<h4>$1</h4>")
        .replace(/^## (.*?)$/gm, "<h3>$1</h3>")
        .replace(/^# (.*?)$/gm, "<h2>$1</h2>")
        .replace(/^\d+\.\s+(.*?)$/gm, "<li>$1</li>")
        .replace(/^- (.*?)$/gm, "<li>$1</li>")
        .replace(/\n{2,}/g, "<br><br>")
        .replace(/\n/g, "<br>");

    // Restore code blocks as styled blockquotes
    codeBlocks.forEach((code, idx) => {
        const escapedCode = code
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
        text = text.replace(`%%CODEBLOCK_${idx}%%`, `<blockquote class="chat-code-block">${escapedCode}</blockquote>`);
    });

    return text;
}

function appendSuggestedFollowups(msgEl, followups, askFnName, wrapperClass, buttonClass) {
    if (!msgEl || !Array.isArray(followups) || followups.length === 0 || !askFnName) return;

    const valid = followups
        .map(item => typeof item === "string" ? item.trim() : "")
        .filter(Boolean)
        .slice(0, 3);
    if (valid.length === 0) return;

    const wrap = document.createElement("div");
    wrap.className = wrapperClass;
    valid.forEach(question => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = buttonClass;
        btn.textContent = question;
        btn.addEventListener("click", () => {
            const fn = window.CAM?.[askFnName];
            if (typeof fn === "function") fn(question);
        });
        wrap.appendChild(btn);
    });
    msgEl.appendChild(wrap);
}

function canSaveChatNote() {
    return chatScopeProvisionId !== "" && chatScopeTenantIdx !== "";
}

function appendChatNoteAction(msgEl, noteText) {
    if (!msgEl || !noteText || !canSaveChatNote()) return;
    const actions = document.createElement("div");
    actions.className = "chat-msg-actions";
    const btn = document.createElement("button");
    btn.className = "chat-save-note-btn";
    btn.type = "button";
    btn.textContent = "Save as Note";
    btn.addEventListener("click", async (event) => {
        event.stopPropagation();
        btn.disabled = true;
        btn.textContent = "Saving...";
        const ok = await saveChatResponseAsNote(noteText);
        btn.textContent = ok ? "Saved to Notes" : "Save as Note";
        if (!ok) btn.disabled = false;
    });
    actions.appendChild(btn);
    msgEl.appendChild(actions);
}

async function sendChatMessage() {
    const input = $("#chat-input");
    const messagesEl = $("#chat-messages");
    if (!input || !messagesEl || !currentJobId) return;

    const question = input.value.trim();
    if (!question) return;

    const welcome = messagesEl.querySelector(".chat-analysis-welcome");
    if (welcome) welcome.remove();

    const modeSelect = $("#chat-mode-select");
    const selectedValue = modeSelect ? modeSelect.value : "claude";

    // Item 5: Determine mode and model from combined picker
    const isMulti = selectedValue === "multi";
    const mode = isMulti ? "multi" : "single";
    const singleModel = isMulti ? null : selectedValue;

    const models = [];
    let synthesize = false;
    if (isMulti) {
        document.querySelectorAll("#chat-model-options input[type=checkbox]:checked").forEach(cb => {
            models.push(cb.value);
        });
        const synthRadio = document.querySelector('input[name="synth-mode"]:checked');
        synthesize = !synthRadio || synthRadio.value === "synthesized";
    }

    // Show user message
    const userMsg = document.createElement("div");
    userMsg.className = "chat-msg chat-msg-user";
    userMsg.textContent = question;
    messagesEl.appendChild(userMsg);
    input.value = "";

    // Show typing indicator
    const typing = document.createElement("div");
    typing.className = "chat-typing";
    typing.textContent = isMulti ? "Getting responses from multiple models..." : "Thinking...";
    messagesEl.appendChild(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const synthesizerModel = $("#chat-synthesizer-select")?.value || "claude";
        // Use chat scope state (044) — scope set by dropdown or askAboutFinding()
        const activeTenantIdx = chatScopeTenantIdx !== "" ? parseInt(chatScopeTenantIdx, 10) : null;
        const activeProvisionId = chatScopeProvisionId !== "" ? chatScopeProvisionId : null;

        const fetchBody = {
            question,
            mode,
            models,
            synthesize,
            synthesizer: synthesizerModel,
            provision_id: activeProvisionId,
            tenant_idx: activeTenantIdx,    // NEW — pass to backend
            ui_context: buildResultsChatUIContext(),
            history: chatHistory,
        };
        // Item 5: Send model for single mode
        if (singleModel) fetchBody.model = singleModel;

        const resp = await fetch(`/api/jobs/${currentJobId}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(fetchBody),
        });

        typing.remove();

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Chat failed");
        }

        const data = await resp.json();

        if (data.mode === "multi" && data.synthesized_response) {
            // Synthesized mode — single unified response
            const aiMsg = document.createElement("div");
            aiMsg.className = "chat-msg chat-msg-ai";
            aiMsg.setAttribute("data-model", "synthesized");
            const label = document.createElement("div");
            label.className = "chat-msg-label";
            const synthBy = data.synthesized_by || "Claude";
            label.innerHTML = `<span class="chat-model-dot synthesized"></span> Synthesized by ${esc(synthBy)}`;
            aiMsg.appendChild(label);
            const content = document.createElement("div");
            content.innerHTML = linkifyChatProvisions(formatChatResponse(data.synthesized_response));
            aiMsg.appendChild(content);
            appendSuggestedFollowups(
                aiMsg,
                data.suggested_followups || [],
                "askAnalysisQuestion",
                "chat-analysis-starters",
                "chat-analysis-starter"
            );
            appendChatNoteAction(aiMsg, data.synthesized_response || "");
            messagesEl.appendChild(aiMsg);

            // Store both synthesis and individual responses in history
            chatHistory.push({ role: "user", content: question });
            const historyContent = data.synthesized_response +
                "\n\nIndividual model responses:\n" +
                Object.entries(data.individual_responses || {})
                    .map(([k, v]) => `[${k.toUpperCase()}]: ${v}`)
                    .join("\n\n");
            chatHistory.push({ role: "assistant", content: historyContent });

        } else if (data.mode === "multi" && data.responses) {
            // Individual mode — show each model separately
            const modelLabels = { claude: "Claude", gpt: "GPT-5.2", grok: "Grok", gemini: "Gemini" };
            const expectedModels = { claude: "claude-sonnet-4-20250514", gpt: "gpt-5.2", grok: "grok-3", gemini: "gemini-2.5-pro" };

            // Item 4: Build labeled history content
            let historyContent = "";
            for (const [modelKey, response] of Object.entries(data.responses)) {
                const baseLabel = modelLabels[modelKey] || modelKey;
                const actualModel = (data.actual_models || {})[modelKey] || "";
                const friendlyActual = getModelDisplayName(actualModel);
                const isFallback = actualModel && actualModel !== expectedModels[modelKey];

                const displayLabel = isFallback
                    ? `${friendlyActual} <span class="fallback-note">\u21a9 fallback</span>`
                    : baseLabel + (actualModel ? ` <span class="model-version">(${esc(friendlyActual)})</span>` : "");

                historyContent += `[${baseLabel}]: ${response}\n\n`;

                const aiMsg = document.createElement("div");
                aiMsg.className = "chat-msg chat-msg-ai";
                aiMsg.setAttribute("data-model", modelKey);
                const label = document.createElement("div");
                label.className = "chat-msg-label";
                label.innerHTML = `<span class="chat-model-dot ${esc(modelKey)}"></span> ${displayLabel}`;
                aiMsg.appendChild(label);
                const content = document.createElement("div");
                content.innerHTML = linkifyChatProvisions(formatChatResponse(response));
                aiMsg.appendChild(content);
                appendChatNoteAction(aiMsg, response || "");
                messagesEl.appendChild(aiMsg);
            }

            // Synthesis note if responses differ significantly
            const responses = Object.values(data.responses);
            if (responses.length > 1) {
                const lengths = responses.map(r => r.length);
                const avgLen = lengths.reduce((a, b) => a + b, 0) / lengths.length;
                const hasVariance = lengths.some(l => Math.abs(l - avgLen) > avgLen * 0.3);
                if (hasVariance) {
                    const synthMsg = document.createElement("div");
                    synthMsg.className = "chat-msg chat-msg-synthesis";
                    const synthLabel = document.createElement("div");
                    synthLabel.className = "chat-msg-label";
                    synthLabel.textContent = "Note";
                    synthMsg.appendChild(synthLabel);
                    const synthContent = document.createElement("div");
                    synthContent.textContent = "The models provided different perspectives. Consider reviewing each response and consulting qualified counsel.";
                    synthMsg.appendChild(synthContent);
                    messagesEl.appendChild(synthMsg);
                }
            }

            // Item 4: Store labeled multi-model responses in chatHistory
            chatHistory.push({ role: "user", content: question });
            chatHistory.push({ role: "assistant", content: historyContent });

        } else {
            // Single model response with attribution
            const modelKey = data.model_key || singleModel || "claude";
            const actualModel = data.actual_model || "";
            const friendlyActual = actualModel ? getModelDisplayName(actualModel) : "";
            const singleLabel = data.model_label || "Claude";
            const singleDisplayLabel = friendlyActual
                ? `${esc(singleLabel)} <span class="model-version">(${esc(friendlyActual)})</span>`
                : esc(singleLabel);

            const aiMsg = document.createElement("div");
            aiMsg.className = "chat-msg chat-msg-ai";
            aiMsg.setAttribute("data-model", modelKey);
            const label = document.createElement("div");
            label.className = "chat-msg-label";
            label.innerHTML = `<span class="chat-model-dot ${esc(modelKey)}"></span> ${singleDisplayLabel}`;
            aiMsg.appendChild(label);
            const content = document.createElement("div");
            content.innerHTML = linkifyChatProvisions(formatChatResponse(data.response || ""));
            aiMsg.appendChild(content);
            appendSuggestedFollowups(
                aiMsg,
                data.suggested_followups || [],
                "askAnalysisQuestion",
                "chat-analysis-starters",
                "chat-analysis-starter"
            );
            appendChatNoteAction(aiMsg, data.response || "");
            messagesEl.appendChild(aiMsg);

            // Update chat history
            chatHistory.push({ role: "user", content: question });
            chatHistory.push({ role: "assistant", content: data.response || "" });
        }

    } catch (err) {
        typing.remove();
        const errMsg = document.createElement("div");
        errMsg.className = "chat-msg chat-msg-ai";
        errMsg.style.color = "var(--danger)";
        errMsg.textContent = `Error: ${err.message}`;
        messagesEl.appendChild(errMsg);
    }

    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function askAboutFinding(pid, tenantIdx, presetQuestion, starterMode = "analysis") {
    // Set scope to the relevant contract + provision
    const contractSel = $("#chat-scope-contract");
    const provisionSel = $("#chat-scope-provision");

    let resolvedTenantIdx = (typeof tenantIdx === "number" && !isNaN(tenantIdx)) ? tenantIdx : null;

    // Find which tenant index has this provision if no explicit tenant was passed
    if ((resolvedTenantIdx == null || isNaN(resolvedTenantIdx)) && currentResults && currentResults.tenants) {
        resolvedTenantIdx = currentResults.tenants.findIndex(t =>
            t.results && t.results.provisions &&
            t.results.provisions.some(p => p.provision_id === pid)
        );
    }

    if (resolvedTenantIdx != null && resolvedTenantIdx >= 0) {
        chatScopeTenantIdx = String(resolvedTenantIdx);
        if (contractSel) contractSel.value = chatScopeTenantIdx;
        populateChatScopeProvisions();
    }

    chatScopeProvisionId = pid;
    if (provisionSel) provisionSel.value = pid;
    chatStarterMode = starterMode;
    updateChatScopeIndicator();

    // Pre-fill input
    const input = $("#chat-input");
    if (input) {
        input.value = typeof presetQuestion === "string" ? presetQuestion : `What are the practical implications of this deviation?`;
        input.focus();
    }

    // Open panel on mobile
    const panel = $("#chat-panel");
    if (panel && window.innerWidth <= 900) {
        panel.classList.add("mobile-open");
        const fab = $("#chat-fab-mobile");
        if (fab) fab.classList.add("hidden");
    }

    const messagesEl = $("#chat-messages");
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
    initChat();
    refreshAnalysisChatWelcome();
}

async function deleteCurrentJob() {
    if (!currentJobId) return;
    if (!confirm("Permanently delete all uploaded documents and analysis results from our server? This cannot be undone.")) return;

    try {
        const resp = await fetch(`/api/jobs/${currentJobId}`, { method: "DELETE" });
        if (!resp.ok) throw new Error("Delete failed");

        currentJobId = null;
        currentJobData = null;
        currentResults = null;
        currentTenantIndex = 0;
        addMoreMode = null;
        // prescan removed (112)
        cancelRequested = false;
        chatHistory = [];
        // Reset chat panel
        const chatPanel = $("#chat-panel");
        if (chatPanel) chatPanel.classList.remove("mobile-open");
        const chatMessages = $("#chat-messages");
        if (chatMessages) chatMessages.innerHTML = "";
        // Reset multi-options panel
        const multiOpts = $("#chat-multi-options");
        if (multiOpts) multiOpts.classList.add("hidden");
        // Hide expiry notice in header
        const expiryEl = $("#expiry-notice");
        if (expiryEl) expiryEl.classList.add("hidden");
        // Clear nav sidebar
        const navContent = $("#nav-sidebar-content");
        if (navContent) navContent.innerHTML = "";
        if (expiryTimer) { clearInterval(expiryTimer); expiryTimer = null; }
        stopPolling();
        history.replaceState(null, "", "/");
        enterApp();
    } catch (err) {
        alert("Failed to delete: " + err.message);
    }
}

// ══════════════════════════════════════════════════════
// ADDITIONAL FINDINGS (step 112 — in-pipeline discovery)
// ══════════════════════════════════════════════════════

function renderAdditionalFindings(discoveries, modelsUsed) {
    const section = $("#additional-findings-section");
    const container = $("#additional-findings-list");
    if (!section || !container) return;

    // Step 118: Check if discovery check ran at all (step 112 populates discoveries object)
    const discoveryCheckRan = discoveries && typeof discoveries === "object" && Object.keys(discoveries).length > 0;
    const allStandalone = (discoveries && discoveries.standalone) || [];
    // Only show true orphans — discoveries with no suggested LP
    // Discoveries with a suggested_lp are folded into the parent card
    const standalone = allStandalone.filter(d =>
        !d.unique_suggested_lps || d.unique_suggested_lps.length === 0
    );

    if (standalone.length === 0) {
        // No orphan discoveries — hide section entirely
        section.style.display = "none";
        container.innerHTML = "";
        return;
    }

    section.style.display = "";
    container.innerHTML = standalone.map(item => {
        const name = esc(item.clause_name || "Unnamed Clause");
        const badge = esc(item.resolution_label || "");
        const sectionRef = item.tenant_section_ref ? `<div class="discovery-section-ref">${esc(item.tenant_section_ref)}</div>` : "";
        const clauseText = item.clause_text || "";
        const truncated = clauseText.length > 500;
        const displayText = truncated ? clauseText.substring(0, 500) + "..." : clauseText;

        // Model details — resolve A/B/C to actual model names
        const evalNames = modelsUsed ? getEvaluatorNames(modelsUsed) : {};
        const evaluators = (item.evaluators_found || []).map(key =>
            evalNames[key] ? evalNames[key].name : key
        ).join(", ");
        const lps = (item.unique_suggested_lps || []).length > 0
            ? item.unique_suggested_lps.join(", ")
            : "no standard match";

        // Per-evaluator reasoning (expandable)
        let reasoningHtml = "";
        if (item.evaluator_details) {
            const details = Object.entries(item.evaluator_details).map(([key, det]) => {
                const modelName = evalNames[key] ? evalNames[key].name : `Model ${key}`;
                return `<div><strong>${esc(modelName)}:</strong> ${esc(det.reasoning || "")}</div>`;
            }).join("");
            reasoningHtml = `<details class="discovery-reasoning"><summary>Model reasoning</summary>${details}</details>`;
        }

        return `<div class="discovery-card">
            <div class="discovery-header">
                <span class="discovery-name">${name}</span>
                <span class="discovery-resolution-badge">${badge}</span>
            </div>
            ${sectionRef}
            <div class="discovery-clause-text">${esc(displayText)}</div>
            <div class="discovery-meta">
                Flagged by: ${esc(evaluators)} &middot; Suggested LP: ${esc(lps)}
            </div>
            ${reasoningHtml}
        </div>`;
    }).join("");
}

// (updatePrescanUI, unlockStandardProvisions, lockStandardProvisions removed in step 112)

function resetApp() {
    // 1. Clear file state
    templateFile = null;
    tenantFiles = [];
    addMoreMode = null;
    modeExplicitlySelected = false;
    currentJobId = null;
    jobEmail = null;
    templateSummary = null;
    identityChecks = { landlord: false, property: false, tenant: false };
    renderTemplateFileList();
    renderTenantFileList();

    // 2. Clear email fields, reset email confirmation notices.
    //
    // Step 276 root-cause fix: the email accordion's HTML default state
    // is body-visible (no `hidden` class on `email-accordion-body` at
    // page load). The expand/collapse trigger element
    // (`email-accordion-trigger`) referenced by older code does NOT
    // exist in `index.html` — the "accordion" was never wired up as a
    // real collapsible widget. Adding `hidden` here therefore took the
    // email inputs out of layout with no path back, so users navigating
    // back to upload from results saw a "stuck" / non-typable email
    // field. We rebuild the inputs to clear values and DELETE any
    // residual `hidden` class so the body is visible like the default.
    const accBody = document.getElementById('email-accordion-body');
    if (accBody) {
        delete accBody.dataset.emailSet;
        accBody.innerHTML = `
            <label class="input-label" for="email-input">Email address</label>
            <input type="email" id="email-input" class="input-field" placeholder="you@lawfirm.com" autocomplete="off">
            <label class="input-label mt-2" for="email-confirm-input">Confirm email</label>
            <input type="email" id="email-confirm-input" class="input-field" placeholder="Retype your email" autocomplete="off">
            <div id="email-mismatch-error" class="email-mismatch-error hidden">Email addresses don't match</div>`;
        accBody.classList.remove('hidden');
    }
    // Legacy accordion-trigger reference — element doesn't exist in
    // current HTML; left as a no-op safeguard for older deploys.
    const accTrigger = document.getElementById('email-accordion-trigger');
    if (accTrigger) accTrigger.classList.remove('open');

    // Reset processing email capture card. The card's innerHTML may
    // still hold a "Notifications will be sent to ..." confirmation
    // div from a prior run — restore the original capture markup so a
    // future processing screen renders writable inputs again.
    const procCard = document.getElementById('processing-email-capture');
    if (procCard) {
        delete procCard.dataset.emailSet;
        procCard.innerHTML = `
            <label class="input-label" for="processing-email-input">Email me when complete <span class="muted">(optional)</span></label>
            <input type="email" id="processing-email-input" class="input-field" placeholder="you@lawfirm.com" autocomplete="off">
            <button class="btn btn-secondary" id="processing-email-submit-btn" type="button">Save email</button>
            <div id="processing-email-status" class="muted"></div>`;
    }

    // Reset mobile email row. Same shape as the processing card —
    // restore writable inputs after a prior confirmation replaced them.
    const mobileEmailRow = document.querySelector('.mobile-results-email-row');
    if (mobileEmailRow) delete mobileEmailRow.dataset.emailSet;

    // Step 276: explicitly clear text inputs that exist outside the
    // email accordion. innerHTML rebuild above handles the email
    // accordion inputs; this catches any other free-standing inputs
    // on the upload form (currently none, but guards against future
    // additions like instructions textarea).
    const uploadSection = document.getElementById('state-upload');
    if (uploadSection) {
        uploadSection.querySelectorAll('input[type="text"], input[type="email"], textarea')
            .forEach(el => {
                // Skip inputs we just rebuilt inside the email accordion
                if (el.closest('#email-accordion-body')) return;
                el.value = '';
            });
    }

    // 3. Step 139: Reset to phase 1 (deactivate step 2)
    const summaryContainer = $("#template-summary-container");
    if (summaryContainer) summaryContainer.innerHTML = "";
    deactivateStep2();
    const gateErrorEl = $("#template-gate-error");
    if (gateErrorEl) gateErrorEl.classList.add("hidden");
    updateUploadModeLabels();
    const subtitle = $("#upload-subtitle");
    if (subtitle) subtitle.textContent = "Upload your reference lease (standard template or prior executed lease).";

    // 4. Update UI state
    updateSubmitState();
}

function toggleEmailAccordion() {
    const trigger = document.getElementById('email-accordion-trigger');
    const body = document.getElementById('email-accordion-body');
    if (!trigger || !body) return;
    const isOpen = !body.classList.contains('hidden');
    body.classList.toggle('hidden', isOpen);
    trigger.classList.toggle('open', !isOpen);
}

function toggleSecurityAccordion() {
    const trigger = document.getElementById('security-accordion-trigger');
    const body = document.getElementById('security-accordion-body');
    if (!trigger || !body) return;
    const isOpen = !body.classList.contains('hidden');
    body.classList.toggle('hidden', isOpen);
    trigger.classList.toggle('open', !isOpen);
}

// (reEnableScan removed in step 112)

// (triggerTemplateScan, triggerTenantScan, runNonStandardScan, skipPrescan, renderNonStandardList removed in step 112)

// ══════════════════════════════════════════════════════
// FILTER BAR (043)
// ══════════════════════════════════════════════════════

function toggleFilterDropdown(which) {
    const ids = {
        contract:   { trigger: "filter-contract-trigger",   panel: "filter-contract-panel"   },
        severity:   { trigger: "filter-severity-trigger",   panel: "filter-severity-panel"   },
        confidence: { trigger: "filter-confidence-trigger", panel: "filter-confidence-panel" },
        provision:  { trigger: "filter-provision-trigger",  panel: "filter-provision-panel"  },
    };
    const others = Object.keys(ids).filter(k => k !== which);

    const { trigger: triggerId, panel: panelId } = ids[which];
    const trigger = $("#" + triggerId);
    const panel   = $("#" + panelId);
    if (!panel || !trigger) return;

    // Close other panels
    others.forEach(k => {
        const p = $("#" + ids[k].panel);
        if (p) p.classList.add("hidden");
    });

    const isOpen = !panel.classList.contains("hidden");
    if (isOpen) { panel.classList.add("hidden"); return; }

    const rect = trigger.getBoundingClientRect();
    panel.style.top  = (rect.bottom + 4) + "px";
    panel.style.left = rect.left + "px";
    panel.classList.remove("hidden");
}

// Close open filter panels when clicking outside
document.addEventListener("click", (e) => {
    if (!e.target.closest(".filter-dropdown")) {
        ["filter-contract-panel", "filter-severity-panel", "filter-provision-panel"].forEach(id => {
            const p = $("#" + id);
            if (p) p.classList.add("hidden");
        });
    }
});

function initFilterBar() {
    // Populate contract options
    const contractOptions = $("#filter-contract-options");
    if (contractOptions && currentResults && currentResults.tenants) {
        contractOptions.innerHTML = currentResults.tenants.map((t, i) => `
            <label class="filter-option">
                <input type="checkbox" value="${i}" class="filter-contract-cb">
                <span>${esc(formatTenantName(t.filename || ""))}</span>
            </label>
        `).join("");
    }

    // Contract "All" checkbox
    const contractAll = $("#filter-contract-all");
    if (contractAll) {
        contractAll.addEventListener("change", () => {
            if (contractAll.checked) {
                filterContracts.clear();
                document.querySelectorAll(".filter-contract-cb").forEach(cb => cb.checked = false);
            }
            updateFilterLabels();
            applyFilters();
        });
    }

    // Individual contract checkboxes
    document.querySelectorAll(".filter-contract-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            if (cb.checked) {
                filterContracts.add(cb.value);
            } else {
                filterContracts.delete(cb.value);
            }
            // Sync "All" checkbox
            const allCb = $("#filter-contract-all");
            if (allCb) allCb.checked = filterContracts.size === 0;
            updateFilterLabels();
            applyFilters();
        });
    });

    // Severity "All" checkbox
    const sevAll = $("#filter-severity-all");
    if (sevAll) {
        sevAll.addEventListener("change", () => {
            if (sevAll.checked) {
                filterSeverities.clear();
                document.querySelectorAll(".filter-sev-cb").forEach(cb => cb.checked = false);
            }
            updateFilterLabels();
            updateContractOptions();
            applyFilters();
        });
    }

    // Individual severity checkboxes
    document.querySelectorAll(".filter-sev-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            if (cb.checked) {
                filterSeverities.add(cb.value);
            } else {
                filterSeverities.delete(cb.value);
            }
            // Sync "All" checkbox
            const allCb = $("#filter-severity-all");
            if (allCb) allCb.checked = filterSeverities.size === 0;
            updateFilterLabels();
            updateContractOptions();
            applyFilters();
        });
    });

    // ── Provision filter (049, select replacement Step 346) ──
    const provisionSel = $("#filter-provision-select");
    if (provisionSel && currentResults && currentResults.tenants) {
        const lpProvisions = new Map();
        const customProvisions = new Map();

        currentResults.tenants.forEach(t => {
            if (!t.results || !t.results.provisions) return;
            t.results.provisions.forEach(p => {
                const pid = p.provision_id;
                const name = p.provision_name || pid;
                if (!pid) return;
                if (pid.startsWith("CUSTOM-") || pid.startsWith("ADDED-")) {
                    if (!customProvisions.has(pid)) customProvisions.set(pid, name);
                } else {
                    if (!lpProvisions.has(pid)) lpProvisions.set(pid, name);
                }
            });
        });

        const lpSorted = [...lpProvisions.entries()].sort((a, b) => a[0].localeCompare(b[0]));
        const customSorted = [...customProvisions.entries()].sort((a, b) => a[0].localeCompare(b[0]));

        let optHtml = '<option value="">All Provisions</option>';
        if (lpSorted.length > 0) {
            optHtml += '<optgroup label="Standard">';
            optHtml += lpSorted.map(([pid, name]) => {
                const shortName = name.replace(/^LP-\d{2}\s*/, "");
                return `<option value="${esc(pid)}">${esc(pid + ' ' + shortName)}</option>`;
            }).join("");
            optHtml += '</optgroup>';
        }
        if (customSorted.length > 0) {
            optHtml += '<optgroup label="Discovered">';
            optHtml += customSorted.map(([pid, name]) => {
                const shortName = name.replace(/^CUSTOM-\d+\s*/, "").replace(/^ADDED-\d+\s*/, "");
                return `<option value="${esc(pid)}">${esc(pid + ' ' + shortName)}</option>`;
            }).join("");
            optHtml += '</optgroup>';
        }
        provisionSel.innerHTML = optHtml;
        provisionSel.value = filterProvisions.size === 1 ? [...filterProvisions][0] : '';
    }

    // Step 184: Confidence filter
    const confAll = document.getElementById('filter-confidence-all');
    if (confAll) {
        confAll.addEventListener('change', function() {
            if (this.checked) {
                filterConfidence.clear();
                document.querySelectorAll('.filter-conf-cb').forEach(cb => cb.checked = false);
            }
            updateFilterLabels();
            applyFilters();
        });
    }
    document.querySelectorAll('.filter-conf-cb').forEach(cb => {
        cb.addEventListener('change', function() {
            if (this.checked) {
                filterConfidence.add(this.value);
            } else {
                filterConfidence.delete(this.value);
            }
            const allCb = document.getElementById('filter-confidence-all');
            if (allCb) allCb.checked = filterConfidence.size === 0;
            updateFilterLabels();
            applyFilters();
        });
    });

    // Clear button
    const clearBtn = $("#filter-clear-btn");
    if (clearBtn) {
        clearBtn.addEventListener("click", clearFilters);
    }

    updateFilterLabels();
    applyFilters();
}

function updateContractOptions() {
    if (!currentResults || !currentResults.tenants) return;
    const contractOptions = $("#filter-contract-options");
    if (!contractOptions) return;

    const tenants = currentResults.tenants;
    const hasSevFilter = filterSeverities.size > 0;
    const hasProvFilter = filterProvisions.size > 0;
    const noFilter = !hasSevFilter && !hasProvFilter;

    // Determine which tenant indices have at least one matching deviation
    const eligibleIndices = new Set();
    tenants.forEach((t, i) => {
        if (noFilter) {
            eligibleIndices.add(i);
            return;
        }
        const provisions = (t.results && t.results.provisions) || [];
        const hasMatch = provisions.some(p => {
            if (p.final_verdict !== "DEVIATES") return false;
            const sevMatch = !hasSevFilter || filterSeverities.has(p.severity);
            const provMatch = !hasProvFilter || filterProvisions.has(p.provision_id);
            return sevMatch && provMatch;
        });
        if (hasMatch) eligibleIndices.add(i);
    });

    // Remove any selected contracts that are no longer eligible
    filterContracts.forEach(idx => {
        if (!eligibleIndices.has(Number(idx))) {
            filterContracts.delete(idx);
        }
    });

    // Rebuild contract option checkboxes — only eligible contracts
    contractOptions.innerHTML = [...eligibleIndices].map(i => {
        const t = tenants[i];
        const isChecked = filterContracts.has(String(i));
        return `<label class="filter-option">
            <input type="checkbox" value="${i}" class="filter-contract-cb"${isChecked ? " checked" : ""}>
            <span>${esc(formatTenantName(t.filename || ""))}</span>
        </label>`;
    }).join("");

    // Re-wire contract checkbox event listeners
    contractOptions.querySelectorAll(".filter-contract-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            if (cb.checked) {
                filterContracts.add(cb.value);
            } else {
                filterContracts.delete(cb.value);
            }
            const allCb = $("#filter-contract-all");
            if (allCb) allCb.checked = filterContracts.size === 0;
            updateFilterLabels();
            applyFilters();
        });
    });

    // Update "All" checkbox state
    const allCb = $("#filter-contract-all");
    if (allCb) allCb.checked = filterContracts.size === 0;
}

function updateFilterLabels() {
    // Contract label
    const contractLabel = $("#filter-contract-label");
    if (contractLabel) {
        if (filterContracts.size === 0) {
            contractLabel.textContent = "All";
        } else if (filterContracts.size === 1) {
            const idx = [...filterContracts][0];
            const tenant = currentResults && currentResults.tenants && currentResults.tenants[idx];
            contractLabel.textContent = tenant ? formatTenantName(tenant.filename || "") : `1 selected`;
        } else {
            contractLabel.textContent = `${filterContracts.size} selected`;
        }
    }

    // Severity label
    const sevLabel = $("#filter-severity-label");
    if (sevLabel) {
        if (filterSeverities.size === 0) {
            sevLabel.textContent = "All";
        } else if (filterSeverities.size === 1) {
            sevLabel.textContent = [...filterSeverities][0];
        } else {
            sevLabel.textContent = [...filterSeverities].join(", ");
        }
    }

    // Provision select sync (049, Step 346)
    const provSelSync = $("#filter-provision-select");
    if (provSelSync) {
        provSelSync.value = filterProvisions.size === 1 ? [...filterProvisions][0] : '';
    }

    // Step 184: Confidence label
    const confLabel = $('#filter-confidence-label');
    if (confLabel) {
        if (filterConfidence.size === 0) confLabel.textContent = 'All';
        else if (filterConfidence.size === 1) {
            const val = [...filterConfidence][0];
            const labelMap = { HIGH: 'Verified', IMPACT_UNCLEAR: 'Impact Unclear', NEEDS_REVIEW: 'Needs Review', INCONCLUSIVE: 'Inconclusive' };
            confLabel.textContent = labelMap[val] || val;
        }
        else confLabel.textContent = 'Custom';
    }

    // Clear button visibility
    const hasFilters = filterContracts.size > 0 || filterSeverities.size > 0 || filterProvisions.size > 0 || filterConfidence.size > 0;
    const clearBtn = $("#filter-clear-btn");
    if (clearBtn) clearBtn.classList.toggle("hidden", !hasFilters);
    // Also highlight active triggers
    const contractTrigger = $("#filter-contract-trigger");
    const sevTrigger = $("#filter-severity-trigger");
    const provTrigger = $("#filter-provision-trigger");
    const confTrigger = $("#filter-confidence-trigger");
    if (contractTrigger) contractTrigger.classList.toggle("filter-trigger-active", filterContracts.size > 0);
    if (sevTrigger) sevTrigger.classList.toggle("filter-trigger-active", filterSeverities.size > 0);
    if (provTrigger) provTrigger.classList.toggle("filter-trigger-active", filterProvisions.size > 0);
    if (confTrigger) confTrigger.classList.toggle("filter-trigger-active", filterConfidence.size > 0);
}

function applyFilters() {
    const countEl = $("#filter-active-count");
    let visible = 0, total = 0;

    // Step 184: confidence match helper
    function confMatch(signal) {
        if (filterConfidence.size === 0) return true;
        if (filterConfidence.has('HIGH') && signal === 'ASSERT_SIGNAL') return true;
        if (filterConfidence.has('IMPACT_UNCLEAR') && signal === 'ASSERT_REVIEW_SIGNAL') return true;
        if (filterConfidence.has('NEEDS_REVIEW') && signal === 'REVIEW_SIGNAL') return true;
        if (filterConfidence.has('INCONCLUSIVE') && signal === 'WITHHOLD_SIGNAL') return true;
        return false;
    }

    // Filter finding-cards (per-tenant view — severity + provision + confidence)
    document.querySelectorAll(".finding-card[data-severity]").forEach(card => {
        total++;
        const sev = card.dataset.severity;
        const pid = card.dataset.pid;
        const sig = card.dataset.confidence || 'ASSERT_SIGNAL';
        const sevMatch = filterSeverities.size === 0 || filterSeverities.has(sev);
        const provMatch = filterProvisions.size === 0 || filterProvisions.has(pid);
        const show = sevMatch && provMatch && confMatch(sig);
        card.style.display = show ? "" : "none";
        if (show) visible++;
    });

    // Filter contract status panel deviation rows (severity + provision)
    document.querySelectorAll(".contract-deviation-row[data-severity]").forEach(row => {
        const sev = row.dataset.severity;
        const pid = row.dataset.pid;
        const sevMatch = filterSeverities.size === 0 || filterSeverities.has(sev);
        const provMatch = filterProvisions.size === 0 || filterProvisions.has(pid);
        row.style.display = (sevMatch && provMatch) ? "" : "none";
    });

    // Hide contract cards entirely if contract filter is active and card not selected
    document.querySelectorAll(".contract-card[data-tenant]").forEach(card => {
        const tenantIdx = card.dataset.tenant;
        const contractMatch = filterContracts.size === 0 || filterContracts.has(String(tenantIdx));
        card.style.display = contractMatch ? "" : "none";
    });

    // Update count
    if (countEl) {
        if ((filterSeverities.size > 0 || filterContracts.size > 0 || filterProvisions.size > 0 || filterConfidence.size > 0) && total > 0) {
            countEl.textContent = `${visible} of ${total} issues`;
            countEl.classList.remove("hidden");
        } else {
            countEl.classList.add("hidden");
        }
    }

    // (contract filter no longer auto-navigates to a single contract — just filters the cards in place)
}

function setProvisionFilter(value) {
    filterProvisions.clear();
    if (value) filterProvisions.add(value);
    updateFilterLabels();
    updateContractOptions();
    applyFilters();
}

function clearFilters() {
    filterContracts.clear();
    filterSeverities.clear();
    filterProvisions.clear();
    filterConfidence.clear();
    document.querySelectorAll(".filter-contract-cb, .filter-sev-cb, .filter-conf-cb").forEach(cb => cb.checked = false);
    const allContract = $("#filter-contract-all");
    const allSev = $("#filter-severity-all");
    const allConf = $("#filter-confidence-all");
    const provSel = $("#filter-provision-select");
    if (allContract) allContract.checked = true;
    if (allSev) allSev.checked = true;
    if (allConf) allConf.checked = true;
    if (provSel) provSel.value = '';
    updateFilterLabels();
    updateContractOptions();
    applyFilters();
}

// ══════════════════════════════════════════════════════
// CHAT SCOPE SELECTOR (044)
// ══════════════════════════════════════════════════════

function updateChatContractOptions() {
    if (!currentResults || !currentResults.tenants) return;
    const contractSel = $("#chat-scope-contract");
    if (!contractSel) return;

    const tenants = currentResults.tenants;
    const activeProvFilter = chatScopeProvisionId || "";
    const hasProvFilter = !!activeProvFilter;

    // Rebuild "All Contracts" + eligible tenants only
    const eligibleIndices = [];
    tenants.forEach((t, i) => {
        if (!hasProvFilter) {
            eligibleIndices.push(i);
            return;
        }
        const provisions = (t.results && t.results.provisions) || [];
        const hasMatch = provisions.some(p => {
            if (p.final_verdict !== "DEVIATES") return false;
            return p.provision_id === activeProvFilter;
        });
        if (hasMatch) eligibleIndices.push(i);
    });

    // Preserve current selection if still eligible, else reset to ""
    const currentVal = contractSel.value;
    const currentStillEligible = currentVal === "" ||
        eligibleIndices.includes(Number(currentVal));

    contractSel.innerHTML = '<option value="">All Contracts</option>';
    eligibleIndices.forEach(i => {
        const t = tenants[i];
        const opt = document.createElement("option");
        opt.value = String(i);
        opt.textContent = formatTenantName(t.filename || "");
        contractSel.appendChild(opt);
    });

    contractSel.value = currentStillEligible ? currentVal : "";
    if (!currentStillEligible) {
        chatScopeTenantIdx = "";
        populateChatScopeProvisions();
    }
}

function syncChatScopeToCurrentTenant(resetProvision) {
    const contractSel = $("#chat-scope-contract");
    const provisionSel = $("#chat-scope-provision");
    if (!currentResults || !currentResults.tenants || !currentResults.tenants[currentTenantIndex]) return;

    chatScopeTenantIdx = String(currentTenantIndex);
    if (resetProvision) {
        chatScopeProvisionId = "";
    }

    if (contractSel) {
        contractSel.value = chatScopeTenantIdx;
    }

    populateChatScopeProvisions();

    if (provisionSel && chatScopeProvisionId) {
        provisionSel.value = chatScopeProvisionId;
    }

    updateChatContractOptions();
    updateChatScopeIndicator();
}

function initChatScope() {
    const contractSel = $("#chat-scope-contract");
    const provisionSel = $("#chat-scope-provision");
    const resetBtn = $("#chat-scope-reset");
    if (!contractSel) return;

    // Populate contract options from loaded tenants
    contractSel.innerHTML = '<option value="">All Contracts</option>';
    if (currentResults && currentResults.tenants) {
        currentResults.tenants.forEach((t, i) => {
            const opt = document.createElement("option");
            opt.value = String(i);
            opt.textContent = formatTenantName(t.filename || "");
            contractSel.appendChild(opt);
        });
    }

    if (currentResults && currentResults.tenants && currentResults.tenants[currentTenantIndex]) {
        chatScopeTenantIdx = String(currentTenantIndex);
        contractSel.value = chatScopeTenantIdx;
    }

    // Contract change → repopulate provisions
    contractSel.addEventListener("change", () => {
        chatScopeTenantIdx = contractSel.value;
        chatScopeProvisionId = "";
        populateChatScopeProvisions();
        hideChatAdvisorPrompts();
        updateChatScopeIndicator();
    });

    // Provision change
    if (provisionSel) {
        provisionSel.addEventListener("change", () => {
            chatScopeProvisionId = provisionSel.value;
            updateChatContractOptions();
            hideChatAdvisorPrompts();
            updateChatScopeIndicator();
        });
    }

    populateChatScopeProvisions();
    updateChatContractOptions();
    updateChatScopeIndicator();
}

function populateChatScopeProvisions() {
    const provisionSel = $("#chat-scope-provision");
    if (!provisionSel || !currentResults) return;

    // Collect provisions
    const seen = new Set();
    const options = [];

    const tenants = currentResults.tenants || [];
    const targetIdx = chatScopeTenantIdx !== "" ? parseInt(chatScopeTenantIdx, 10) : null;

    tenants.forEach((t, i) => {
        if (targetIdx !== null && i !== targetIdx) return;
        const provisions = t.results && t.results.provisions ? t.results.provisions : [];
        provisions.forEach(p => {
            const pid = p.provision_id;
            if (!pid || seen.has(pid)) return;
            seen.add(pid);
            const label = `${pid} ${p.provision_name || ""}`.trim();
            const isDeviation = p.final_verdict === "DEVIATES";
            options.push({ pid, label, isDeviation });
        });
    });

    // Sort: deviations first, then alphabetically
    options.sort((a, b) => {
        if (a.isDeviation && !b.isDeviation) return -1;
        if (!a.isDeviation && b.isDeviation) return 1;
        return a.pid.localeCompare(b.pid);
    });

    provisionSel.innerHTML = '<option value="">All Provisions</option>';
    options.forEach(o => {
        const opt = document.createElement("option");
        opt.value = o.pid;
        opt.textContent = o.isDeviation ? `⚠ ${o.label}` : o.label;
        provisionSel.appendChild(opt);
    });

    // Restore selection if still valid
    if (chatScopeProvisionId && seen.has(chatScopeProvisionId)) {
        provisionSel.value = chatScopeProvisionId;
    } else {
        provisionSel.value = "";
        chatScopeProvisionId = "";
    }
}

function updateChatScopeIndicator() {
    const indicator = $("#chat-scope-indicator");
    const resetBtn = $("#chat-scope-reset");
    const isScoped = chatScopeTenantIdx !== "" || chatScopeProvisionId !== "";

    if (resetBtn) resetBtn.classList.toggle("hidden", !isScoped);

    if (!indicator) return;
    if (!isScoped) {
        indicator.classList.add("hidden");
        indicator.textContent = "";
        return;
    }

    const parts = [];
    if (chatScopeTenantIdx !== "" && currentResults && currentResults.tenants) {
        const t = currentResults.tenants[parseInt(chatScopeTenantIdx, 10)];
        if (t) parts.push(formatTenantName(t.filename || ""));
    }
    if (chatScopeProvisionId !== "") {
        // Find provision name
        const tenants = currentResults && currentResults.tenants || [];
        for (const t of tenants) {
            const p = t.results && t.results.provisions &&
                      t.results.provisions.find(p => p.provision_id === chatScopeProvisionId);
            if (p) {
                parts.push(`${p.provision_id} ${p.provision_name || ""}`.trim());
                break;
            }
        }
        if (parts.length === 0 || (parts.length === 1 && chatScopeTenantIdx === "")) {
            parts.push(chatScopeProvisionId);
        }
    }

    indicator.textContent = "\uD83D\uDCCC " + parts.join(" \u00B7 ");
    indicator.classList.remove("hidden");
    refreshAnalysisChatWelcome();
}

function showChatAdvisorPrompts(pid, tenantIdx) {
    const container = $("#chat-advisor-prompts");
    if (!container) return;
    container.innerHTML = `
        <div class="chat-advisor-label">AI Advisor</div>
        <button class="chat-advisor-chip" onclick="window.CAM.askResolution('${esc(pid)}', ${tenantIdx}, 'summary')">Summarize this issue</button>
        <button class="chat-advisor-chip" onclick="window.CAM.askResolution('${esc(pid)}', ${tenantIdx}, 'advice')">Advise what to do</button>
        <button class="chat-advisor-chip" onclick="window.CAM.askResolution('${esc(pid)}', ${tenantIdx}, 'rewrite')">Draft replacement language</button>
        <button class="chat-advisor-chip" onclick="window.CAM.askResolution('${esc(pid)}', ${tenantIdx}, 'risk')">Risk if accepted as-is</button>
        <button class="chat-advisor-chip" onclick="window.CAM.askResolution('${esc(pid)}', ${tenantIdx}, 'standard')">Is this market/standard?</button>
        <button class="chat-advisor-chip" onclick="window.CAM.aggressiveRead('${esc(pid)}', ${tenantIdx})">&#x26A1; Strongest tenant reading</button>
    `;
    container.classList.remove("hidden");
}

function hideChatAdvisorPrompts() {
    const container = $("#chat-advisor-prompts");
    if (!container) return;
    container.innerHTML = "";
    container.classList.add("hidden");
}

function resetChatScope() {
    chatScopeTenantIdx = "";
    chatScopeProvisionId = "";
    chatStarterMode = "analysis";
    const contractSel = $("#chat-scope-contract");
    const provisionSel = $("#chat-scope-provision");
    if (contractSel) contractSel.value = "";
    if (provisionSel) {
        populateChatScopeProvisions();
        provisionSel.value = "";
    }
    hideChatAdvisorPrompts();
    updateChatScopeIndicator();
}

function askAnalysisQuestion(question) {
    const input = $("#chat-input");
    if (!input) return;
    input.value = question;
    input.focus();
}

// ── Audit Trail ──

function legacyGetAuditGovernanceLabel(signal) {
    const map = {
        ASSERT_SIGNAL: "Assert",
        ASSERT_REVIEW_SIGNAL: "Assert, but review carefully",
        REVIEW_SIGNAL: "Review recommended",
        WITHHOLD_SIGNAL: "Withhold",
    };
    return map[signal] || signal || "—";
}

function legacyGetAuditPatternLabel(pattern) {
    const map = {
        PATTERN_1_RELIABLE: "Reliable",
        PATTERN_2_FRAGILE_PERSUASIVE: "Fragile Persuasive",
        PATTERN_3_WEAK: "Weak",
        PATTERN_3_WEAK_UNCLEAR: "Weak / Unclear",
        PATTERN_4_MISSED_WEAKNESS: "Missed Weakness",
    };
    return map[pattern] || pattern || "—";
}

function legacyGetAuditAsgTone(asg) {
    if (asg == null || isNaN(asg)) return { label: "Unknown", tone: "neutral", width: 0 };
    if (asg < 15) return { label: "Low sensitivity", tone: "good", width: 18 };
    if (asg < 35) return { label: "Moderate sensitivity", tone: "caution", width: 46 };
    if (asg < 55) return { label: "High sensitivity", tone: "warning", width: 74 };
    return { label: "Very high sensitivity", tone: "danger", width: 100 };
}

function legacyGetAuditConfidenceTone(camPerm) {
    if (camPerm == null || isNaN(camPerm)) return { label: "Unknown", tone: "neutral", width: 0 };
    if (camPerm >= 85) return { label: "High confidence", tone: "good", width: camPerm };
    if (camPerm >= 70) return { label: "Strong confidence", tone: "good", width: camPerm };
    if (camPerm >= 50) return { label: "Moderate confidence", tone: "caution", width: camPerm };
    return { label: "Low confidence", tone: "danger", width: Math.max(18, camPerm) };
}

function legacyGetAuditFragilityTone(fragilityRaw) {
    const score = fragilityRaw && fragilityRaw.fragility_score != null ? Number(fragilityRaw.fragility_score) : null;
    if (score == null || isNaN(score)) return { label: "No fragility score", tone: "neutral", width: 0 };
    const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
    if (pct < 15) return { label: "Low structural fragility", tone: "good", width: pct };
    if (pct < 35) return { label: "Moderate structural fragility", tone: "caution", width: pct };
    if (pct < 60) return { label: "High structural fragility", tone: "warning", width: pct };
    return { label: "Very high structural fragility", tone: "danger", width: pct };
}

function legacyGetAuditAgreementSummary(pattern) {
    if (!pattern) return "Evaluator agreement was not available.";
    if (pattern.includes("3/3")) return "All three evaluators reached the same conclusion.";
    if (pattern.includes("2/3")) return "Two of the three evaluators agreed on the outcome.";
    return `Evaluator agreement pattern: ${pattern}.`;
}

function legacyGetAuditEvidenceSummary(provision, challengeRaw) {
    const basis = ((provision.cam_score || {}).evidence_basis || "").toLowerCase();
    if (basis === "explicit_text") return "The conclusion is tied to direct contract text.";
    if (basis === "structural_inference") return "The conclusion depends partly on structural inference rather than only explicit text.";
    if (basis === "absence") return "The conclusion is based on missing language in one of the documents.";
    if (basis === "ambiguous") return "The available text supports multiple readings, so the evidence is ambiguous.";
    if (basis === "unverified_citation") return "The evidence chain contains citations that could not be fully verified.";
    if (challengeRaw && challengeRaw.substantive_finding) return "The challenger found a substantive issue in the text comparison.";
    return "CAM reviewed the clause text but the evidence basis was not explicitly labeled.";
}

function legacyGetAuditReasoningSummary(provision, stagesRun, challengeRaw) {
    if (stagesRun.has(4) && challengeRaw) {
        return "This clause went through the full review chain, including a challenge step.";
    }
    if (stagesRun.has(3)) {
        return "This clause reached evaluator review, but the challenge stage was skipped.";
    }
    return "This clause did not move through the full reasoning chain.";
}

function legacyGetAuditFragilitySummary(fragilityRaw) {
    const rules = (fragilityRaw && fragilityRaw.rules_fired) || [];
    if (!rules.length) return "No structural fragility signals were detected.";
    const translated = rules.map(r => FRAGILITY_TRANSLATIONS[r.signal] || r.signal || r.rule_id).filter(Boolean);
    return `Structural fragility was detected because of ${translated.join(", ")}.`;
}

function legacyRenderAuditScoreBar(label, value, helper, toneInfo) {
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

function legacyRenderAuditRawRecord(title, record) {
    if (!record) return "";
    return `<details class="audit-raw-record">
        <summary>${esc(title)}</summary>
        <pre>${esc(JSON.stringify(record, null, 2))}</pre>
    </details>`;
}

function legacyRenderAuditPromptBlock(title, text) {
    if (!text) return "";
    return `<details class="audit-raw-record">
        <summary>${esc(title)}</summary>
        <pre>${esc(text)}</pre>
    </details>`;
}

function legacyRenderAuditTechnicalGroup(title, innerHtml) {
    if (!innerHtml) return "";
    return `<div class="audit-technical-group">
        <div class="audit-technical-group-title">${esc(title)}</div>
        ${innerHtml}
    </div>`;
}

// Step 307b: Derive a governance-equivalent signal from element-level evaluator data.
// Maps to the same ASSERT/ASSERT_REVIEW/REVIEW/WITHHOLD signals used by Mode A,
// so getConfidenceBadgeData() and getSidebarConfidenceLabel() can be called directly.
function deriveCoverageGovernanceSignal(elementVerdicts) {
    if (!elementVerdicts || !elementVerdicts.length) return null;
    var total = elementVerdicts.length;
    var highConf   = elementVerdicts.filter(function(e) { return e.confidence === 'high'; }).length;
    var medConf    = elementVerdicts.filter(function(e) { return e.confidence === 'medium'; }).length;
    var lowConf    = elementVerdicts.filter(function(e) { return e.confidence === 'low'; }).length;
    var hasDisag   = elementVerdicts.some(function(e) { return e.disagreements && e.disagreements.length > 0; });
    if (highConf === total && !hasDisag) return 'ASSERT_SIGNAL';
    if (lowConf === 0 && highConf >= total * 0.7) return 'ASSERT_REVIEW_SIGNAL';
    if (lowConf > 0 || medConf > total * 0.3) return 'REVIEW_SIGNAL';
    if (lowConf >= total * 0.3) return 'WITHHOLD_SIGNAL';
    return 'REVIEW_SIGNAL';
}

// Step 339: pure governance signal helpers for sidebar confidence indicators.
// These mirror the Mode A infrastructure for compound_risk and directional_mismatch
// findings, so the sidebar speaks the same 4-dot language as Mode A.

const _SIG_ORDER = { ASSERT_SIGNAL: 0, ASSERT_REVIEW_SIGNAL: 1, REVIEW_SIGNAL: 2, WITHHOLD_SIGNAL: 3 };

function getWeakestGovernanceSignal(signals) {
    var weakest = null;
    (signals || []).forEach(function(s) {
        if (!s) return;
        if (weakest === null || (_SIG_ORDER[s] ?? 99) > (_SIG_ORDER[weakest] ?? 99)) weakest = s;
    });
    return weakest;
}

// Maps compound finding evaluator agreement to governance signal, then caps by
// the weakest involved LP confidence.
function deriveCompoundGovernanceSignal(finding, coverageAssessmentByLp) {
    var parts   = (finding.evaluator_agreement || '').split('-');
    var agreed  = parseInt(parts[0], 10) || 0;
    var baseSignal = agreed >= 3 ? 'ASSERT_SIGNAL'
                   : agreed === 2 ? 'ASSERT_REVIEW_SIGNAL'
                   : agreed === 1 ? 'REVIEW_SIGNAL'
                   : null;
    if (!baseSignal) return null;
    // TODO Step 339+: cap by citation validity once compound evaluator
    // output includes validated citation support
    var lpSignals = (finding.implicated_lps || []).map(function(lpId) {
        var lp = coverageAssessmentByLp && coverageAssessmentByLp[lpId];
        if (!lp) return null;
        var evs = lp.element_verdicts || [];
        return evs.length > 0 ? deriveCoverageGovernanceSignal(evs) : null;
    }).filter(Boolean);
    return getWeakestGovernanceSignal([baseSignal].concat(lpSignals)) || baseSignal;
}

// Maps directional_mismatch finding evaluator agreement to governance signal.
// 3-0 → ASSERT_SIGNAL, 2-1 → ASSERT_REVIEW_SIGNAL (Impact Unclear), 1-2 → REVIEW_SIGNAL.
function deriveDirectionalGovernanceSignal(finding) {
    var parts  = (finding.evaluator_agreement || '').split('-');
    var agreed = parseInt(parts[0], 10) || 0;
    if (agreed >= 3) return 'ASSERT_SIGNAL';
    if (agreed === 2) return 'ASSERT_REVIEW_SIGNAL';
    if (agreed === 1) return 'REVIEW_SIGNAL';
    return null;
}

// Render compact confidence dots span for sidebar items.
// Shows only the Unicode dot sequence; full label is in the title tooltip.
function _navConfDotsHtml(govSig, tooltipText) {
    if (!govSig) return '';
    var bd = window.CAMAuditShared ? window.CAMAuditShared.getConfidenceBadgeData(govSig) : null;
    if (!bd) return '';
    var tip = tooltipText || ('Confidence: ' + bd.label);
    return '<span class="nav-item-conf nav-item-conf-dots" title="' + esc(tip) + '">' + bd.dots + '</span>';
}

// Step 306d helpers — Mode C coverage evaluation in audit trail

var _COV_AUDIT_VERDICT_SHORT = {
    'explicitly_present':     'Present',
    'implicitly_present':     'Implicit',
    'covered_by_default_law': 'Default Law',
    'covered_in_other_LP':    'Cross-LP',
    'missing':                'Missing',
    'unclear':                'Unclear',
    'review_needed':          'Review',
};
var _COV_AUDIT_VERDICT_CLS = {
    'explicitly_present':     'cv-ev-present',
    'implicitly_present':     'cv-ev-implicit',
    'covered_by_default_law': 'cv-ev-default',
    'covered_in_other_LP':    'cv-ev-crosslp',
    'missing':                'cv-ev-missing',
    'unclear':                'cv-ev-unclear',
    'review_needed':          'cv-ev-unclear',
};

function _buildCovAuditTable(evs, roleList) {
    var html = '<div class="audit-cov-table-wrap"><table class="audit-cov-table"><thead><tr><th class="audit-cov-th">Element</th>';
    roleList.forEach(function(role) { html += '<th class="audit-cov-th">' + esc(evalName(role)) + '</th>'; });
    html += '<th class="audit-cov-th">Merged</th></tr></thead><tbody>';
    evs.forEach(function(ev) {
        var hasDisag = ev.disagreements && ev.disagreements.length > 0;
        html += '<tr class="audit-cov-row' + (hasDisag ? ' audit-cov-row-disag' : '') + '">';
        html += '<td class="audit-cov-td-label">' + esc(ev.element_label || ev.element_id) + '</td>';
        var evByRole = {};
        (ev.evaluator_verdicts || []).forEach(function(evr) { evByRole[evr.role || '?'] = evr; });
        roleList.forEach(function(role) {
            var evr = evByRole[role];
            if (!evr) { html += '<td class="audit-cov-td">—</td>'; return; }
            var vcls = _COV_AUDIT_VERDICT_CLS[evr.verdict] || 'cv-ev-unclear';
            var vlabel = _COV_AUDIT_VERDICT_SHORT[evr.verdict] || evr.verdict;
            var citRef = (evr.citation && evr.citation.section_ref) ? ' <span class="audit-cov-cit">' + esc(evr.citation.section_ref) + '</span>' : '';
            var reasonHtml = '';
            if (hasDisag && evr.reasoning) {
                reasonHtml = '<div class="audit-cov-ev-reason">' + esc(evr.reasoning) + '</div>';
            }
            html += '<td class="audit-cov-td"><span class="cv-ev-pill ' + vcls + '">' + vlabel + '</span>' + citRef + reasonHtml + '</td>';
        });
        var mvcls = _COV_AUDIT_VERDICT_CLS[ev.verdict] || 'cv-ev-unclear';
        var mvlabel = _COV_AUDIT_VERDICT_SHORT[ev.verdict] || ev.verdict;
        var conf = ev.confidence ? ' (' + ev.confidence + ')' : '';
        var reasonNote = ev.reason ? ' <span class="audit-cov-reason">' + esc(ev.reason.replace(/_/g, ' ')) + '</span>' : '';
        // Step 349b: disputed verdict — amber badge with vote count
        if (ev.verdict === 'disputed') {
            var _dpPres = ['explicitly_present','implicitly_present','covered_by_default_law','covered_in_other_LP'];
            var _dpPresCount = (ev.disagreements || []).filter(function(d){ return _dpPres.indexOf(d.verdict) !== -1; }).length;
            var _dpMissCount = (ev.disagreements || []).filter(function(d){ return d.verdict === 'missing'; }).length;
            html += '<td class="audit-cov-td"><span class="element-merged-disputed">Disputed</span><span class="element-merged-votes">(' + _dpPresCount + 'v' + _dpMissCount + ')</span></td>';
        } else {
            html += '<td class="audit-cov-td"><span class="cv-ev-pill ' + mvcls + '">' + mvlabel + '</span>' + conf + reasonNote + '</td>';
        }
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    return html;
}

function _buildMergeTraceHtml(disagElems) {
    var html = '<div class="audit-cov-trace-list">';
    disagElems.forEach(function(ev) {
        var dissents = ev.disagreements || [];
        html += '<div class="audit-cov-trace-item">'
            + '<span class="audit-cov-trace-elem">' + esc(ev.element_label || ev.element_id) + '</span>'
            + ' <span class="audit-cov-trace-arrow">→</span>'
            + ' <span class="audit-cov-trace-merged">merged: <strong>' + esc(_COV_AUDIT_VERDICT_SHORT[ev.verdict] || ev.verdict) + '</strong>';
        if (ev.reason) html += ' <span class="audit-cov-reason">' + esc(ev.reason.replace(/_/g, ' ')) + '</span>';
        html += '</span>';
        if (dissents.length > 0) {
            html += '<div class="audit-cov-trace-dissents">';
            dissents.forEach(function(d) {
                var dReason = (d.reasoning || '').trim();
                html += '<div class="audit-cov-trace-dissent-row">'
                    + '<span class="audit-cov-trace-dissent">' + esc(evalName(d.role || d.evaluator_id || '?')) + ': ' + esc(_COV_AUDIT_VERDICT_SHORT[d.verdict] || d.verdict) + '</span>'
                    + (dReason ? ' <span class="audit-cov-trace-reason">' + esc(dReason) + '</span>' : '')
                    + '</div>';
            });
            html += '</div>';
        }
        html += '</div>';
    });
    html += '</div>';
    return html;
}

function buildCoverageAuditSection(items) {
    var _POSITIVE = new Set(['explicitly_present', 'implicitly_present', 'covered_by_default_law', 'covered_in_other_LP']);
    var html = '<div class="audit-cov-section"><div class="audit-cov-section-heading">Coverage Evaluation — ' + items.length + ' pilot LP' + (items.length > 1 ? 's' : '') + ' (Step 305)</div>';
    items.forEach(function(a, idx) {
        var pid = a.issue_area_id || '';
        var name = a.issue_area_name || pid;
        var baseline = a.coverage_state_baseline || a.coverage_state || '';
        var method = a.coverage_method || 'step_305_per_element';
        var evs = a.element_verdicts || [];
        var totalCount = evs.length;
        var nPresent = evs.filter(function(e) { return _POSITIVE.has(e.verdict); }).length;
        var nMissing = evs.filter(function(e) { return e.verdict === 'missing'; }).length;
        var nUnclear = evs.filter(function(e) { return e.verdict === 'unclear'; }).length;
        var disagElems = evs.filter(function(e) { return e.disagreements && e.disagreements.length > 0; });
        var stateVcls = _COV_AUDIT_VERDICT_CLS[baseline] || 'cv-ev-unclear';
        var stateLabel = _COV_AUDIT_VERDICT_SHORT[baseline] || baseline;
        var lpBodyId = 'audit-cov-lp-body-' + idx;
        var elemListId = 'audit-cov-elems-' + idx;
        var tableId = 'audit-cov-table-' + idx;
        var traceId = 'audit-cov-trace-' + idx;
        // Determine evaluator roles
        var roleSet = {};
        evs.forEach(function(ev) {
            (ev.evaluator_verdicts || []).forEach(function(evr) { roleSet[evr.role || '?'] = true; });
        });
        var roleList = Object.keys(roleSet).sort();
        var tableHtml = roleList.length > 0 ? _buildCovAuditTable(evs, roleList) : '';
        var mergeHtml = disagElems.length > 0 ? _buildMergeTraceHtml(disagElems) : '';
        var elemListHtml = '<ul class="audit-cov-elem-list">' + evs.map(function(e) { return '<li>' + esc(e.element_label || e.element_id) + '</li>'; }).join('') + '</ul>';
        var derivNote = 'LP state: <strong>' + esc(baseline) + '</strong> — ' + nPresent + ' present, ' + nMissing + ' missing, ' + nUnclear + ' unclear of ' + totalCount + ' elements'
            + (disagElems.length > 0 ? ' (' + disagElems.length + ' element' + (disagElems.length > 1 ? 's' : '') + ' with evaluator disagreement)' : '');
        // Step 351: audit trail disagreement severity language
        var _auditVd = a.verdict_distance;
        var _auditSev = _auditVd && _auditVd.severity;
        var _auditSevNote = '';
        // Step 374K: audit-provenance honesty. The LP-level verdict_distance is DERIVED from each
        // evaluator's element-verdict plurality (pessimistic tie-break — lease_verdict_distance.py),
        // NOT standalone LP-level evaluator conclusions. The X↔Y pair is the derived rollup; it must
        // not be described as "one evaluator found X, another found Y." Wording only.
        if (_auditSev === 'minor') {
            _auditSevNote = '<div class="audit-cov-sev-note audit-cov-sev-minor">LP-level review trigger derived from aggregated element verdicts — minor distance (drafting nuance only).</div>';
        } else if (_auditSev === 'moderate') {
            _auditSevNote = '<div class="audit-cov-sev-note audit-cov-sev-moderate">LP-level review trigger derived from aggregated element verdicts — moderate distance; not a standalone evaluator conclusion.</div>';
        } else if (_auditSev === 'severe') {
            var _pair = (_auditVd.pair || []);
            var _v1 = esc(_pair[0] || '');
            var _v2 = esc(_pair[1] || '');
            _auditSevNote = '<div class="audit-cov-sev-note audit-cov-sev-severe">&#x26A0; LP-level review trigger derived from aggregated element verdicts; not a standalone evaluator conclusion. Derived ordinal distance is maximal (<strong>' + _v1 + '</strong> &#8596; <strong>' + _v2 + '</strong>), produced from per-evaluator element-verdict pluralities. See per-element evaluator verdicts below.</div>';
        }
        // Step 356 Phase 3: dispute_signal note
        var _ds = a.dispute_signal || {};
        var _auditDisputeNote = '';
        if (_ds.triggered) {
            var _dsCrit = _ds.critical_disputed_count || 0;
            var _dsBaseline = esc(a.coverage_state_baseline || '');
            _auditDisputeNote = '<div class="audit-cov-sev-note audit-cov-dispute-signal">'
                + '&#x2691; <strong>Critical dispute — majority verdict withheld.</strong><br>'
                + _dsCrit + ' critical rubric element' + (_dsCrit !== 1 ? 's' : '') + ' produced evaluator disagreement spanning presence and absence. '
                + 'Review Required regardless of majority reading.<br>'
                + '<span class="audit-cov-dispute-baseline">Baseline verdict: <strong>' + _dsBaseline + '</strong></span>'
                + '</div>';
        }
        // Step 307b: score bars using the shared audit infrastructure (same as Mode A)
        var _sharedLib = window.CAMAuditShared;
        var scoreBarsHtml = '';
        if (_sharedLib && totalCount > 0) {
            var _unaniCount = evs.filter(function(e) { return !e.disagreements || e.disagreements.length === 0; }).length;
            var _agreePct = Math.round(_unaniCount / totalCount * 100);
            var _agreeTone = _agreePct >= 85 ? {tone: 'good', width: _agreePct} : _agreePct >= 60 ? {tone: 'caution', width: _agreePct} : {tone: 'danger', width: _agreePct};
            var _sensPct = Math.round(disagElems.length / totalCount * 100);
            var _sensTone = _sensPct <= 10 ? {tone: 'good', width: _sensPct} : _sensPct <= 30 ? {tone: 'caution', width: _sensPct} : {tone: 'danger', width: _sensPct};
            var _crossCount = evs.filter(function(e) { return e.verdict === 'covered_in_other_LP'; }).length;
            var _crossPct = Math.round(_crossCount / totalCount * 100);
            scoreBarsHtml = '<div class="audit-cov-score-bars">'
                + _sharedLib.renderAuditScoreBar('Element Agreement', _agreePct + '%', _unaniCount + ' of ' + totalCount + ' elements had unanimous evaluator agreement', _agreeTone, esc)
                + _sharedLib.renderAuditScoreBar('Evaluator Sensitivity', _sensPct + '%', disagElems.length + ' of ' + totalCount + ' elements had evaluator disagreement', _sensTone, esc)
                + (_crossCount > 0 ? _sharedLib.renderAuditScoreBar('Cross-LP Coverage', _crossPct + '%', _crossCount + ' element' + (_crossCount !== 1 ? 's' : '') + ' resolved via cross-provision coverage', {tone: 'caution', width: _crossPct}, esc) : '')
                + '</div>';
        }
        html += '<div class="audit-cov-lp" data-pid="' + esc(pid) + '">'
            + '<div class="audit-cov-lp-header" onclick="(function(h){var b=document.getElementById(\'' + lpBodyId + '\');var o=b.style.display===\'none\';b.style.display=o?\'block\':\'none\';h.querySelector(\'.audit-cov-chevron\').textContent=o?\'▾\':\'▸\';})(this)">'
            + '<span class="audit-cov-lp-id">' + esc(pid) + '</span>'
            + '<span class="audit-cov-lp-name">' + esc(name) + '</span>'
            + '<span class="cv-ev-pill ' + stateVcls + '">' + stateLabel + '</span>'
            + '<span class="audit-cov-method-badge">' + esc(method) + '</span>'
            + '<span class="audit-cov-chevron">▸</span>'
            + '</div>'
            + '<div id="' + lpBodyId + '" class="audit-cov-lp-body" style="display:none">'
            + _auditDisputeNote
            + _auditSevNote
            + '<div class="audit-cov-deriv-note">' + derivNote + '</div>'
            + scoreBarsHtml
            + '<div class="audit-cov-sub-toggle" onclick="(function(t){var b=document.getElementById(\'' + elemListId + '\');var o=b.style.display===\'none\';b.style.display=o?\'block\':\'none\';t.querySelector(\'.audit-sub-chev\').textContent=o?\'▾\':\'▸\';})(this)"><span class="audit-sub-chev">▸</span> ' + totalCount + ' expected elements</div>'
            + '<div id="' + elemListId + '" style="display:none">' + elemListHtml + '</div>'
            + (tableHtml ? '<div class="audit-cov-sub-toggle" onclick="(function(t){var b=document.getElementById(\'' + tableId + '\');var o=b.style.display===\'none\';b.style.display=o?\'block\':\'none\';t.querySelector(\'.audit-sub-chev\').textContent=o?\'▾\':\'▸\';})(this)"><span class="audit-sub-chev">▸</span> Per-evaluator verdicts</div><div id="' + tableId + '" style="display:none">' + tableHtml + '</div>' : '')
            + (mergeHtml ? '<div class="audit-cov-sub-toggle" onclick="(function(t){var b=document.getElementById(\'' + traceId + '\');var o=b.style.display===\'none\';b.style.display=o?\'block\':\'none\';t.querySelector(\'.audit-sub-chev\').textContent=o?\'▾\':\'▸\';})(this)"><span class="audit-sub-chev">▸</span> Merge trace (' + disagElems.length + ' disagreement' + (disagElems.length > 1 ? 's' : '') + ')</div><div id="' + traceId + '" style="display:none">' + mergeHtml + '</div>' : '')
            + '</div>'
            + '</div>';
    });
    html += '</div>';
    return html;
}

function _parseTimestampFromRunId(runId) {
    if (!runId) return null;
    const m = String(runId).match(/(\d{8})_(\d{6})/);
    if (!m) return null;
    const d = m[1], t = m[2];
    return d.slice(0,4) + '-' + d.slice(4,6) + '-' + d.slice(6,8)
         + 'T' + t.slice(0,2) + ':' + t.slice(2,4) + ':' + t.slice(4,6);
}

function renderAuditTrail(allTenants) {
    const tab = $("#audittrail-tab");
    if (!tab || !currentResults) return;

    // Full-run mode: render all tenants stacked by collecting each tenant's HTML
    if (allTenants) {
        const savedIdx = currentTenantIndex;
        let combined = '';
        currentResults.tenants.forEach(function(t, idx) {
            if (!t || !t.results) return;
            currentTenantIndex = idx;
            renderAuditTrail(false);
            combined += '<div class="audit-tenant-section">'
                + '<div class="audit-tenant-heading">' + esc(t.filename || ('Contract ' + (idx + 1))) + '</div>'
                + tab.innerHTML
                + '</div>';
        });
        currentTenantIndex = savedIdx;
        tab.innerHTML = combined || '<p>No audit data available.</p>';
        return;
    }

    const tenant = currentResults.tenants[currentTenantIndex];
    if (!tenant || !tenant.results) {
        tab.innerHTML = "<p>No audit data available.</p>";
        return;
    }
    const r = tenant.results;

    // Step 254: Mode C skips the evaluator/challenger/severity stages entirely.
    // Replace the em-dash "missing data" appearance with an explanatory paragraph
    // that frames the absence as intentional. Step 297c: also show Stage 5b when present.
    if (r.mode === "analyze") {
        const _at_SFN = {"NY": "New York", "CA": "California", "TX": "Texas", "FL": "Florida", "IL": "Illinois"};
        const _at_jur = r.jurisdiction || {};
        const _at_govLaw = _at_jur.governing_law;
        const _at_govLabel = _at_govLaw ? (_at_SFN[_at_govLaw] || _at_govLaw) : "Not detected";
        const _at_escs = _at_jur.escalations || [];
        let _at_stage5b = "";
        if (_at_govLaw || _at_escs.length > 0) {
            const _at_escHtml = _at_escs.length === 0
                ? `<div class="audit-stage-body"><div style="color:#64748b;font-size:0.875rem;">No state-specific escalations applied.</div></div>`
                : `<div class="audit-stage-body"><div style="color:#64748b;font-size:0.875rem;">${_at_escs.length} escalation(s) applied:</div><ul style="margin:0.4rem 0 0 1rem;padding:0;font-size:0.875rem;">${
                    _at_escs.map(e => `<li><strong>${esc(e.lp_id)}</strong>: ${esc(e.from)} &rarr; ${esc(e.to)}<div style="color:#64748b;font-size:0.8rem;">${esc(e.rationale || "")}</div></li>`).join("")
                }</ul></div>`;
            _at_stage5b = `<div class="audit-stage-block" style="margin-top:1rem;padding:0.75rem 1rem;background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;">
                <div class="audit-stage-title"><span class="audit-stage-num">Stage 5b</span><span class="audit-stage-name">Jurisdiction Rules</span><span class="audit-stage-model">Automated · 0 API calls</span></div>
                <div class="audit-stage-body"><div><strong>Governing law:</strong> ${esc(_at_govLabel)}</div></div>
                ${_at_escHtml}
            </div>`;
        }
        // Step 306d: build Coverage Evaluation section for pilot LPs
        var _at_ca = (r.coverage_assessment || []).filter(function(a) {
            return (a.element_verdicts || []).length > 0;
        });
        var _at_covEval = _at_ca.length > 0 ? buildCoverageAuditSection(_at_ca) : '';

        const _mcFilename = tenant.filename || '—';
        const _mcRawTs = r.timestamp
            || (currentJobData && (currentJobData.completed_at || currentJobData.started_at))
            || _parseTimestampFromRunId(currentJobId);
        const _mcTs = _mcRawTs
            ? new Date(_mcRawTs).toLocaleString('en-US', { month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
            : '—';
        const _mcElapsed = r.elapsed_sec ? fmtDuration(r.elapsed_sec) : '—';
        tab.innerHTML = `
            <div class="audit-mode-c-message">
                <div class="audit-mode-c-heading">Analyze-mode audit</div>
                <div class="audit-mode-c-meta">
                    <span><strong>File:</strong> ${esc(_mcFilename)}</span>
                    <span><strong>Processed:</strong> ${esc(_mcTs)}</span>
                    <span><strong>Elapsed:</strong> ${esc(_mcElapsed)}</span>
                </div>
                <p>
                    This section shows provision-by-provision evaluator outputs, challenge reviews, and
                    severity assignments. These stages run only in <strong>Compare mode</strong>, where
                    findings are produced by deviation detection against a reference template.
                </p>
                <p>
                    In <strong>Analyze mode</strong>, the analysis path is schema-driven coverage
                    assessment. Findings for this run are on the
                    <a href="#" onclick="window.CAM.switchResultsTab &amp;&amp; window.CAM.switchResultsTab('coverage'); return false;">
                    Coverage &amp; Gaps</a> tab.
                </p>
                ${_at_stage5b}
            </div>
            ${_at_covEval}
        `;
        return;
    }

    let provisions = getTenantWorkflowProvisions(currentTenantIndex)
        .filter(p => !p.absent_from_both);
    const modelsUsed = r.models_used || {};

    // Run metadata block
    const _rawTs = r.timestamp
        || (currentJobData && (currentJobData.completed_at || currentJobData.started_at))
        || _parseTimestampFromRunId(currentJobId);
    const ts = _rawTs
        ? new Date(_rawTs).toLocaleString('en-US', { month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
        : "Unknown";
    const evalModels = [
        modelsUsed.evaluator_a,
        modelsUsed.evaluator_b,
        modelsUsed.evaluator_c
    ].filter(Boolean).join(" · ");

    const readableEvalModels = [
        modelsUsed.evaluator_a,
        modelsUsed.evaluator_b,
        modelsUsed.evaluator_c
    ].filter(Boolean).map(getModelDisplayName).join(" · ");

    // Aggregate run stats across all tenants
    const _allTenants = (currentResults && currentResults.tenants) || [];
    const _totalProvs   = _allTenants.reduce((s,t) => s + ((t.results && t.results.provisions) ? t.results.provisions.length : 0), 0);
    // Step 335: use job-level wall-clock elapsed (job_created → job_completed) from the
    // results payload. Fall back to summing per-tenant pipeline elapsed if not available.
    const _jobElapsed   = (currentResults && currentResults.elapsed_seconds) || null;
    const _totalElapsed = _jobElapsed || _allTenants.reduce((s,t) => s + ((t.results && t.results.elapsed_sec) || 0), 0);
    const _totalCalls   = _allTenants.reduce((s,t) => s + ((t.results && t.results.api_calls_total) || 0), 0);
    const _pipeVer      = r.pipeline_version || '';
    const _pipeDomain   = r.pipeline_domain_label || '';
    const _runStatLine  = [
        _totalProvs   ? `${_totalProvs} provisions` : '',
        _totalElapsed ? fmtDuration(_totalElapsed) + ' total runtime' : '',
        _totalCalls   ? `${_totalCalls} model calls` : '',
        _pipeVer      ? `Pipeline ${esc(_pipeVer)}` : '',
    ].filter(Boolean).join(' &middot; ');

    const _auditFilename = tenant.filename || r.tenant_file || '—';
    let html = `<div class="audit-run-header">
        <span class="audit-run-header-file"><strong>File:</strong> ${esc(_auditFilename)}</span>
        <span class="audit-run-header-sep">|</span>
        <span class="audit-run-header-ts"><strong>Processed:</strong> ${esc(ts)}</span>
    </div>
    <div class="audit-export-bar">
        <div class="audit-export-group">
            <span class="audit-export-label">This contract:</span>
            <button class="btn btn-secondary btn-sm" onclick="window.CAM.exportAuditJSON(true)">
                Download JSON
            </button>
            <button class="btn btn-secondary btn-sm" onclick="window.CAM.exportAuditText(true)">
                Download Audit Report
            </button>
        </div>
        <div class="audit-export-group">
            <span class="audit-export-label">All contracts:</span>
            <button class="btn btn-secondary btn-sm" onclick="window.CAM.exportAuditJSON(false)">
                Download JSON
            </button>
            <button class="btn btn-secondary btn-sm" onclick="window.CAM.exportAuditText(false)">
                Download Audit Report
            </button>
        </div>
        ${_runStatLine ? `<div class="audit-export-run-stats">${_runStatLine}</div>` : ''}
    </div>
    <div class="audit-run-meta">
        <div class="audit-meta-section">
            <div class="audit-meta-label">LEASE DETAILS</div>
            <div>Tenant lease: ${esc(tenant.filename || r.tenant_file || "—")}</div>
            <div>Completed at: ${esc(ts)}</div>
            <div>Standard lease: ${esc(r.template_file || "—")}</div>
        </div>
        <div class="audit-meta-section">
            <div class="audit-meta-label">MODELS &amp; ROLES</div>
            <div>Extraction: ${esc(getModelDisplayName(modelsUsed.extractor || "—"))}</div>
            <div>Provision comparison: ${esc(readableEvalModels || "—")}</div>
            <div>Challenge review: ${esc(getModelDisplayName(modelsUsed.challenger || "—"))}</div>
            <div>Severity review: ${esc(getModelDisplayName(modelsUsed.severity_assessor || "—"))}</div>
        </div>
        <div class="audit-meta-section">
            <div class="audit-meta-label">LEASE STATS</div>
            <div>${provisions.length} provision${provisions.length !== 1 ? "s" : ""} reviewed</div>
            <div>${_jobElapsed ? fmtDuration(_jobElapsed) + " actual runtime" : r.elapsed_sec ? fmtDuration(r.elapsed_sec) + " pipeline runtime" : "Actual runtime unavailable"}</div>
            <div>${r.api_calls_total || "—"} model calls</div>

        </div>
    </div>`;

    // Extract _stage_data for buildAuditDetail
    const stageData = (currentResults && currentResults.tenants &&
                       currentResults.tenants[currentTenantIndex] &&
                       currentResults.tenants[currentTenantIndex].results &&
                       currentResults.tenants[currentTenantIndex].results._stage_data) || {};

    // Provision rows
    const _sortIcon = (col) => {
        if (window._auditSortCol !== col) return `<span class="audit-sort-icon">⇕</span>`;
        return `<span class="audit-sort-icon">${window._auditSortDir === 'asc' ? '↑' : '↓'}</span>`;
    };
    const _sortClass = (col) => window._auditSortCol === col ? 'active' : '';
    html += `<div class="audit-controls-bar">
        <div class="audit-table-header">
            <button class="audit-sort-btn audit-sort-btn-provision ${_sortClass('provision')}" onclick="window.CAM.sortAuditTrail('provision')">Provisions (${provisions.length}) ${_sortIcon('provision')}</button>
            <button class="audit-sort-btn ${_sortClass('severity')}" onclick="window.CAM.sortAuditTrail('severity')">Severity ${_sortIcon('severity')}</button>
            <button class="audit-sort-btn ${_sortClass('confidence')}" onclick="window.CAM.sortAuditTrail('confidence')">Confidence ${_sortIcon('confidence')}</button>
            <button class="audit-sort-btn ${_sortClass('agreement')}" onclick="window.CAM.sortAuditTrail('agreement')">Reviewer Agreement ${_sortIcon('agreement')}</button>
            <button class="audit-sort-btn ${_sortClass('complexity')}" onclick="window.CAM.sortAuditTrail('complexity')">Complexity ${_sortIcon('complexity')}</button>
            <div class="audit-controls-buttons">
                <button class="btn-audit-control audit-expand-btn" onclick="window.CAM.expandAllAuditRows()">Expand all</button>
            </div>
        </div>

    </div>`;
    // Default sort: provision ascending on first load
    if (window._auditSortCol === undefined) {
        window._auditSortCol = 'provision';
        window._auditSortDir = 'asc';
    }

    // Apply sort if active
    const SEVERITY_RANK = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, CONFORMS: 4 };
    if (window._auditSortCol) {
        const dir = window._auditSortDir === 'asc' ? 1 : -1;
        provisions = provisions.slice().sort((a, b) => {
            switch (window._auditSortCol) {
                case 'provision': {
                    const pa = a.provision_id || '';
                    const pb = b.provision_id || '';
                    return dir * pa.localeCompare(pb);
                }
                case 'severity': {
                    const ra = SEVERITY_RANK[a.severity] ?? (a.final_verdict === 'CONFORMS' ? 4 : 3);
                    const rb = SEVERITY_RANK[b.severity] ?? (b.final_verdict === 'CONFORMS' ? 4 : 3);
                    return dir * (ra - rb);
                }
                case 'confidence': {
                    const ca = (a.cam_score || {}).CAM_perm ?? -1;
                    const cb = (b.cam_score || {}).CAM_perm ?? -1;
                    return dir * (cb - ca);
                }
                case 'agreement': {
                    const ea = Object.values(a.evaluator_verdicts || {}).filter(v => v === 'DEVIATES').length;
                    const eb = Object.values(b.evaluator_verdicts || {}).filter(v => v === 'DEVIATES').length;
                    return dir * (eb - ea);
                }
                case 'complexity': {
                    const fa = (a.fragility || {}).fragility_score ?? -1;
                    const fb = (b.fragility || {}).fragility_score ?? -1;
                    return dir * (fb - fa);
                }
                default: return 0;
            }
        });
    }

    html += `<div class="audit-provision-list">`;
    provisions.forEach((p, idx) => {
        const pid = p.provision_id || "";
        const pname = p.provision_name || "";
        const verdict = p.final_verdict || "";
        const sev = p.severity || "";
        const meta = p.cam_metadata || {};
        const rulesFired = (meta.rules_fired || []);
        const agPattern = p.agreement_pattern || "—";
        const fragile = p.fragility && p.fragility.fragile;

        // ── Redesigned audit row (Step 229) — human-readable, no jargon ──

        // 1. Severity / verdict badge
        const verdictBadge = verdict === "DEVIATES"
            ? `<span class="audit-verdict audit-verdict-deviates">${esc(sevDisplay(sev))}</span>`
            : verdict === "CONFORMS"
                ? `<span class="audit-verdict audit-verdict-conforms">Conforms</span>`
                : `<span class="audit-verdict audit-verdict-unclear">Unclear</span>`;

        // 2. Confidence dots badge — reuse existing badge data
        const govSig = (p.cam_score || {}).governance_signal || "";
        const badgeData = getConfidenceBadgeData ? getConfidenceBadgeData(govSig, sev.toUpperCase()) : null;
        const dotsBadge = badgeData
            ? `<span class="audit-confidence-badge audit-confidence-${badgeData.cssClass}">${badgeData.dots} ${badgeData.label}</span>`
            : "";

        // 3. Plain-English evaluator agreement
        const evVerdicts = p.evaluator_verdicts || {};
        const evTotal = Object.keys(evVerdicts).length || 3;
        const evAgree = verdict === "DEVIATES"
            ? Object.values(evVerdicts).filter(v => v === "DEVIATES").length
            : Object.values(evVerdicts).filter(v => v === "CONFORMS").length;
        const agreementText = evTotal === 0 ? ""
            : `${evAgree}/${evTotal} reviewers ${verdict === "DEVIATES" ? "flagged this" : "confirmed"}`;
        const agreementSpan = agreementText
            ? `<span class="audit-reviewer-agreement">${esc(agreementText)}</span>`
            : "";

        // Clause complexity mini-badge for collapsed row
        const _rowFragSigs = (p.cam_score || {}).fragility_signals || [];
        const _rowFragRaw = (stageData.fragility || []).find(x => x.provision_id === pid) || null;
        const _rowFragScore = _rowFragRaw && _rowFragRaw.fragility_score != null ? Math.round(_rowFragRaw.fragility_score * 100) : null;
        const _rowComplexityLabel = _rowFragScore == null ? null
            : _rowFragScore < 15 ? "Simple"
            : _rowFragScore < 35 ? "Moderate"
            : _rowFragScore < 60 ? "Complex"
            : "Highly complex";
        const _rowComplexityCls = _rowFragScore == null ? ""
            : _rowFragScore < 15 ? "audit-complexity-simple"
            : _rowFragScore < 35 ? "audit-complexity-moderate"
            : _rowFragScore < 60 ? "audit-complexity-complex"
            : "audit-complexity-high";
        const complexityBadge = _rowComplexityLabel
            ? `<span class="audit-complexity-badge ${_rowComplexityCls}">${esc(_rowComplexityLabel)}</span>`
            : "";



        html += `<div class="audit-provision-row" data-idx="${idx}" data-pid="${esc(pid)}" data-tenant="${currentTenantIndex}">
            <div class="audit-provision-header" onclick="window.CAM.toggleAuditRow(${idx})">
                <span class="audit-pid">${esc(pid)}</span>
                <span class="audit-pname">${esc(pname)}</span>
                <span class="audit-row-signals">
                    ${verdictBadge}
                    ${dotsBadge}
                    ${agreementSpan}
                    ${complexityBadge}
                </span>
                <span class="audit-chevron">&#9654;</span>
            </div>
            <div class="audit-provision-detail hidden" id="audit-detail-${idx}">
                ${buildAuditDetailV2(p, modelsUsed, stageData, idx)}
                            </div>
        </div>`;
    });
    html += `</div>`;

    // Step 297c.7: Stage 5b — Jurisdiction Rules (job-level, shown after provision rows)
    const _at2_SFN = {"NY": "New York", "CA": "California", "TX": "Texas", "FL": "Florida", "IL": "Illinois"};
    const _at2_jur = r.jurisdiction || {};
    if (_at2_jur.governing_law || (_at2_jur.escalations && _at2_jur.escalations.length > 0)) {
        const _at2_govLabel = _at2_SFN[_at2_jur.governing_law] || _at2_jur.governing_law || "Not detected";
        const _at2_escs = _at2_jur.escalations || [];
        const _at2_escDetail = _at2_escs.length === 0
            ? `<div class="audit-detail-label">No state-specific escalations applied.</div>`
            : `<div class="audit-detail-label">${_at2_escs.length} escalation(s) applied:</div>
               <ul style="margin:0.4rem 0 0 1rem;padding:0;font-size:0.875rem;">${
                _at2_escs.map(e => `<li><strong>${esc(e.lp_id)}</strong>: ${esc(e.from)} &rarr; ${esc(e.to)}<div style="color:#64748b;font-size:0.8rem;">${esc(e.rationale || "")}</div></li>`).join("")
               }</ul>`;
        html += `<div class="audit-stage-block" style="margin-top:1.5rem;padding:0.75rem 1rem;background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 5b</span>
                <span class="audit-stage-name">Jurisdiction Rules</span>
                <span class="audit-stage-model">Automated &middot; 0 API calls</span>
            </div>
            <div class="audit-stage-body">
                <div><strong>Governing law:</strong> ${esc(_at2_govLabel)}</div>
                ${_at2_escDetail}
            </div>
        </div>`;
    }

    tab.innerHTML = html;
    syncAuditExpandToggle();
}

function buildAuditDetailV2(p, modelsUsed, stageData, idx) {
    idx = idx != null ? idx : 0;
    stageData = stageData || {};
    const pid = p.provision_id || "";
    const meta = p.cam_metadata || {};
    const stagesRun = new Set(meta.stages_run || []);
    const rulesFired = meta.rules_fired || [];
    const evalRaw = stageData.evaluator_raw || {};
    const evalPrompts = stageData.evaluator_prompts || {};
    const challengeRaw = (stageData.challenge_raw || []).find(x => x.provision_id === pid) || null;
    const challengePrompts = stageData.challenge_prompts || {};
    const severityRaw = (stageData.severity_raw || []).find(x => x.provision_id === pid) || null;
    const severityPrompts = stageData.severity_prompts || {};
    const fragilityRaw = (stageData.fragility || []).find(x => x.provision_id === pid) || null;
    const sev = p.severity || "";
    const triage = stageData.triage || {};
    const wasFlagged = (triage.flagged || []).includes(pid);
    const camScore = p.cam_score || {};
    const governanceLabel = getAuditGovernanceLabel(camScore.governance_signal);
    const patternLabel = getAuditPatternLabel(camScore.pattern);
    const confidenceTone = getAuditConfidenceTone(camScore.CAM_perm);
    const asgTone = getAuditAsgTone(camScore.ASG);
    const fragilityTone = getAuditFragilityTone(fragilityRaw);
    const challengeModel = modelsUsed.challenger || "—";
    const evalMeta = stageData.evaluation_meta || {};
    const evalModelMap = {
        A: modelsUsed.evaluator_a || evalName('A'),
        B: modelsUsed.evaluator_b || evalName('B'),
        C: modelsUsed.evaluator_c || evalName('C'),
    };

    // ── Redesigned audit detail (Step 229) ──
    // Lead with interpretation note (if any), then each model's view,
    // then the challenge round. Confidence scores come last, collapsed.
    // No duplicate content from Contract Summary / Document Comparison.

    const boldMd = window.CAMAuditShared && window.CAMAuditShared.boldMarkdown
        ? window.CAMAuditShared.boldMarkdown
        : (t) => (t || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

    let html = `<div class="audit-detail-v3">`;

    // 0. Confidence label explanation — one sentence at the top explaining why
    //    the badge says what it says (e.g. why Impact Unclear vs Verified)
    const _sidebarExplain = window.CAMAuditShared && window.CAMAuditShared.getSidebarExplanationText
        ? window.CAMAuditShared.getSidebarExplanationText(p)
        : "";
    const _badgeForExplain = getConfidenceBadgeData ? getConfidenceBadgeData(
        (p.cam_score || {}).governance_signal, (p.severity || "").toUpperCase()) : null;
    if (_sidebarExplain && _badgeForExplain) {
        const _seeNote = p.interpretation_note ? " See interpretation note below." : "";
        html += `<div class="adv3-confidence-explainer">
            <span class="adv3-confidence-explainer-badge audit-confidence-${_badgeForExplain.cssClass}">${_badgeForExplain.dots} ${_badgeForExplain.label}</span>
            <span class="adv3-confidence-explainer-text">${esc(_sidebarExplain)}${esc(_seeNote)}</span>
        </div>`;
    }

    // 1. What each reviewer said
    const verdictLabel = { DEVIATES: "Flagged as deviation", CONFORMS: "Confirmed conforming", UNCLEAR: "Unclear" };
    const verdictCls   = { DEVIATES: "adv3-verdict-flag", CONFORMS: "adv3-verdict-ok", UNCLEAR: "adv3-verdict-unclear" };

    html += `<div class="adv3-section-label">What each reviewer said</div>
    <div class="adv3-evaluators">`;

    ["A", "B", "C"].forEach(key => {
        const items = evalRaw[key] || [];
        const ev = items.find(x => x.provision_id === pid);
        if (!ev) return;
        const verdict = ev.verdict || "";
        const modelName = evalModelMap[key] || `Reviewer ${key}`;
        const vLabel = verdictLabel[verdict] || verdict;
        const vCls   = verdictCls[verdict]   || "";
        const diffs = (ev.key_differences || []).filter(Boolean);

        html += `<div class="adv3-eval-card">
            <div class="adv3-eval-header">
                <span class="adv3-eval-model">${esc(modelName)}</span>
                <span class="adv3-eval-verdict ${vCls}">${esc(vLabel)}</span>
            </div>
            ${ev.reasoning ? `<div class="adv3-eval-reasoning">${boldMd(ev.reasoning)}</div>` : ""}
            ${diffs.length ? `<ul class="adv3-eval-diffs">${diffs.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : ""}
        </div>`;
    });

    html += `</div>`; // adv3-evaluators

    // 3. Independent review (challenge)
    if (stagesRun.has(4) && challengeRaw) {
        const challengeText = challengeRaw.substantive_finding || p.challenge_details || "";
        const hiddenDeps = challengeRaw.hidden_dependencies || [];
        html += `<div class="adv3-section-label">Independent review <span class="adv3-model-tag">${esc(challengeModel)}</span></div>
        <div class="adv3-challenge-card">
            ${challengeText ? `<div class="adv3-challenge-text">${boldMd(challengeText)}</div>` : ""}
            ${hiddenDeps.length ? `<ul class="adv3-eval-diffs">${hiddenDeps.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : ""}
        </div>`;
    }

    // 3b. Interpretation note — after reviewers and challenge, before scores
    if (p.interpretation_note) {
        const noteParas = p.interpretation_note.split(/\n\n+/).map(s => s.trim()).filter(Boolean);
        const noteHtml = noteParas.map(s => `<p>${boldMd(s)}</p>`).join("");
        html += `<div class="adv3-interp-note">
            <div class="adv3-section-label">Interpretation note</div>
            <div class="adv3-interp-body">${noteHtml}</div>
        </div>`;
    }

    // 4. Confidence scores — collapsed by default
    const _auditBadgeData = getConfidenceBadgeData ? getConfidenceBadgeData(camScore.governance_signal, (sev || "").toUpperCase()) : null;
    const _auditToneText  = getConfidenceToneText  ? getConfidenceToneText(camScore.governance_signal) : "";
    const _auditBadgeHtml = _auditBadgeData
        ? `<span class="cam-confidence-badge ${_auditBadgeData.cssClass}"><span class="cam-confidence-dots">${_auditBadgeData.dots}</span>${_auditBadgeData.label}</span>`
        : "";
    const _camPermDisplay = camScore.CAM_perm != null ? String(camScore.CAM_perm) : "\u2014";

    // Context lines — always explain what drove each score
    const _fragSigs = (camScore.fragility_signals || []);

    const _reliabilityContext = (() => {
        const reasons = [];
        if (_fragSigs.includes("definition_override"))        reasons.push("a redefined term introduced interpretive uncertainty");
        if (_fragSigs.includes("cross_reference_dependency")) reasons.push("the finding depends on how cross-referenced sections are read");
        if (_fragSigs.includes("negation_pattern"))           reasons.push("new limiting language may narrow the scope of the obligation");
        if (_fragSigs.includes("exception_clause"))           reasons.push("an added exception affects what the obligation covers");
        if (_fragSigs.includes("qualifier_shift"))            reasons.push("a change in obligation strength (e.g. \u2018shall\u2019 to \u2018may\u2019)");
        if (_fragSigs.includes("quantitative_deviation"))     reasons.push("a numeric change whose practical impact depends on context");
        if (reasons.length) return `Why not higher: ${reasons.join("; ")}.`;
        // No specific signals — explain based on evaluator confidence
        const perm = camScore.CAM_perm;
        if (perm >= 85) return "Reviewers were highly consistent and the finding is well-grounded in the clause text.";
        if (perm >= 70) return "Solid reviewer agreement with minor variation in how the clause impact was assessed.";
        if (perm >= 50) return "Some variation between reviewers on the scope or significance of the deviation.";
        return "Reviewers disagreed significantly — treat this as a flag rather than a confirmed finding.";
    })();

    const _stricterContext = (() => {
        const cd = (challengeRaw && challengeRaw.substantive_finding) || p.challenge_details || "";
        if (cd) {
            const plain = cd.replace(/\*\*(.+?)\*\*/g, "$1").replace(/\n/g, " ").trim();
            const firstSentence = plain.split(/\.\s+/)[0];
            const snippet = firstSentence.length > 160 ? firstSentence.slice(0, 157) + "\u2026" : firstSentence;
            if (snippet) return `The independent reviewer found: ${snippet}.`;
        }
        // No challenge text — explain based on ASG value
        const asg = camScore.ASG;
        if (asg == null) return "";
        if (asg < 15) return "The finding is consistent across both permissive and strict readings of the clause.";
        if (asg < 35) return "Under a conservative reading, the deviation would look broadly similar but with slightly different emphasis.";
        if (asg < 55) return "A stricter reading of the clause could shift how significant this deviation appears to be.";
        return "Under the most conservative reading, the practical impact of this deviation could differ substantially.";
    })();

    const _complexityContext = (() => {
        const cm = p.cascade_mechanism || "";
        if (cm) {
            const plain = cm.replace(/\*\*(.+?)\*\*/g, "$1").trim();
            const snippet = plain.length > 180 ? plain.slice(0, 177) + "\u2026" : plain;
            return `This clause is tied to: ${snippet}`;
        }
        if (_fragSigs.includes("cross_reference_dependency")) return "This clause references other sections or defined terms — changes elsewhere in the lease could affect how it is read.";
        if (_fragSigs.includes("definition_override"))        return "A defined term used in this clause was changed, making the clause\u2019s meaning dependent on how that definition is interpreted.";
        if (_fragSigs.includes("exception_clause"))           return "An exception clause was added that may interact with other provisions in the lease.";
        // Generic based on score
        const fScore = fragilityRaw && fragilityRaw.fragility_score != null ? Math.round(fragilityRaw.fragility_score * 100) : null;
        if (fScore == null) return "";
        if (fScore < 15) return "This clause stands on its own — its meaning is self-contained.";
        if (fScore < 35) return "This clause has some dependencies on standard lease definitions and other sections.";
        return "This clause interacts with other provisions — its full impact can only be assessed in the context of the whole lease.";
    })();

    // Word ratings for each score — lawyers don't need raw numbers
    const _reliabilityRating = (() => {
        const p = camScore.CAM_perm;
        if (p == null) return "\u2014";
        if (p >= 85) return "Very strong";
        if (p >= 70) return "Strong";
        if (p >= 50) return "Moderate";
        return "Weak";
    })();
    const _stabilityRating = (() => {
        const a = camScore.ASG;
        if (a == null) return "\u2014";
        if (a < 15) return "Stable";
        if (a < 35) return "Mostly stable";
        if (a < 55) return "Sensitive";
        return "Highly sensitive";
    })();
    const _complexityRating = (() => {
        const f = fragilityRaw && fragilityRaw.fragility_score != null ? Math.round(fragilityRaw.fragility_score * 100) : null;
        if (f == null) return "\u2014";
        if (f < 15) return "Simple";
        if (f < 35) return "Moderate";
        if (f < 60) return "Complex";
        return "Highly complex";
    })();

    const _permNum = camScore.CAM_perm != null ? camScore.CAM_perm.toFixed(1) : null;
    const _asgNum  = camScore.ASG != null ? camScore.ASG.toFixed(1) : null;
    const _fragNum = fragilityRaw && fragilityRaw.fragility_score != null ? Math.round(fragilityRaw.fragility_score * 100) : null;

    const _reliabilityValue = _permNum ? `${_reliabilityRating} <span class="adv3-score-num">${_permNum}/100 \u2191</span>` : _reliabilityRating;
    const _stabilityValue   = _asgNum  ? `${_stabilityRating} <span class="adv3-score-num">${_asgNum} drop \u2193</span>` : _stabilityRating;
    const _complexityValue  = _fragNum != null ? `${_complexityRating} <span class="adv3-score-num">${_fragNum}% \u2191</span>` : _complexityRating;

    html += `<div class="adv3-scores-section">
        <div class="adv3-section-label">Confidence &amp; stability <button class="adv3-scores-info" onclick="window.CAM.showAboutModal('cam-scoring-explainer')" title="How scoring works">&#9432;</button></div>
        <div class="audit-score-grid">
            ${renderAuditScoreBar("Finding reliability", _reliabilityValue, "How much can you rely on this finding?", confidenceTone, esc, _reliabilityContext)}
            ${renderAuditScoreBar("Stricter review", _stabilityValue, "How does this hold up under the most conservative reading?", asgTone, esc, _stricterContext)}
            ${renderAuditScoreBar("Clause complexity", _complexityValue, "How tied is this clause to other parts of the lease?", fragilityTone, esc, _complexityContext)}
        </div>
    </div>`;

    // 5. Technical details — for nerds, collapsed by default
    const _techA      = camScore.A      != null ? String(camScore.A)      : '\u2014';
    const _techE      = camScore.E_perm != null ? camScore.E_perm.toFixed(4) : '\u2014';
    const _techR      = camScore.R_perm != null ? camScore.R_perm.toFixed(4) : '\u2014';
    const _techF      = camScore.F_perm != null ? camScore.F_perm.toFixed(4) : '\u2014';
    const _techPerm   = camScore.CAM_perm  != null ? camScore.CAM_perm.toFixed(2)  : '\u2014';
    const _techStrict = camScore.CAM_strict != null ? camScore.CAM_strict.toFixed(2) : '\u2014';
    const _techASG    = camScore.ASG != null ? camScore.ASG.toFixed(2) : '\u2014';
    const _techSignal = camScore.governance_signal || '\u2014';
    const _techPattern = camScore.pattern || '\u2014';
    const _techBasis  = camScore.evidence_basis || '\u2014';

    const _techId = `tech-${esc(pid)}-${idx}`;
    let techHtml = `<div class="adv3-tech-details" id="${_techId}-wrap">
        <div class="adv3-tech-toggle-row">
            <span class="adv3-tech-toggle-label">🔧 Technical details</span>
            <button class="audit-chevron adv3-tech-btn" onclick="(function(){
                var b = document.getElementById('${_techId}-body');
                var w = document.getElementById('${_techId}-wrap');
                b.classList.remove('hidden');
                w.classList.add('adv3-tech-open');
            })()">&#9654;</button>
        </div>
        <div class="adv3-tech-body hidden" id="${_techId}-body">

            <div class="adv3-tech-section">
                <div class="adv3-tech-label">Scoring formula</div>
                <div class="adv3-tech-formula">
                    <span class="adv3-tech-formula-row">
                        <span class="adv3-tech-term">Agreement (A)</span>
                        <span class="adv3-tech-val">${esc(_techA)}</span>
                        <span class="adv3-tech-op">\u00d7</span>
                        <span class="adv3-tech-term">Evaluator (E)</span>
                        <span class="adv3-tech-val">${esc(_techE)}</span>
                        <span class="adv3-tech-op">\u00d7</span>
                        <span class="adv3-tech-term">Reasoning (R)</span>
                        <span class="adv3-tech-val">${esc(_techR)}</span>
                        <span class="adv3-tech-op">\u00d7 100 =</span>
                        <span class="adv3-tech-result">CAM_perm ${esc(_techPerm)}</span>
                    </span>
                    <span class="adv3-tech-formula-row">
                        <span class="adv3-tech-term">Fragility (F)</span>
                        <span class="adv3-tech-val">${esc(_techF)}</span>
                        <span class="adv3-tech-op">applied to ASG gap \u2192</span>
                        <span class="adv3-tech-result">CAM_strict ${esc(_techStrict)}</span>
                        <span class="adv3-tech-op">&nbsp;&nbsp;drop =</span>
                        <span class="adv3-tech-result">ASG ${esc(_techASG)}</span>
                    </span>
                    <span class="adv3-tech-formula-row">
                        <span class="adv3-tech-term">Signal</span>
                        <span class="adv3-tech-val">${esc(_techSignal)}</span>
                        <span class="adv3-tech-op">&nbsp;&nbsp;Pattern</span>
                        <span class="adv3-tech-val">${esc(_techPattern)}</span>
                        <span class="adv3-tech-op">&nbsp;&nbsp;Evidence basis</span>
                        <span class="adv3-tech-val">${esc(_techBasis)}</span>
                    </span>
                </div>
            </div>`;

    // Raw evaluator responses
    ['A','B','C'].forEach(key => {
        const items = evalRaw[key] || [];
        const ev = items.find(x => x.provision_id === pid);
        if (!ev) return;
        techHtml += `<details class="adv3-tech-raw">
            <summary>Evaluator ${esc(key)} — ${esc(evalModelMap[key])} raw response</summary>
            <pre class="adv3-tech-pre">${esc(JSON.stringify(ev, null, 2))}</pre>
        </details>`;
    });

    // Raw challenge response
    if (challengeRaw) {
        techHtml += `<details class="adv3-tech-raw">
            <summary>Challenge round — ${esc(challengeModel)} raw response</summary>
            <pre class="adv3-tech-pre">${esc(JSON.stringify(challengeRaw, null, 2))}</pre>
        </details>`;
    }

    // Fragility signals
    const _fragSigsRaw = (camScore.fragility_signals || []);
    if (_fragSigsRaw.length) {
        techHtml += `<div class="adv3-tech-section">
            <div class="adv3-tech-label">Fragility signals fired</div>
            <ul class="adv3-tech-list">${_fragSigsRaw.map(s => `<li>${esc(s)}</li>`).join('')}</ul>
        </div>`;
    }

    techHtml += `
        <div class="adv3-tech-close-row">
            <span class="adv3-tech-toggle-label">🔧 Technical details</span>
            <button class="audit-chevron adv3-tech-btn" onclick="(function(){
                var b = document.getElementById('${_techId}-body');
                var w = document.getElementById('${_techId}-wrap');
                b.classList.add('hidden');
                w.classList.remove('adv3-tech-open');
            })()">&#9660;</button>
        </div>
    </div></div>`;
    html += techHtml;

    html += `</div>`; // audit-detail-v3
    return html;
}

function buildAuditDetail(p, modelsUsed, stageData) {
    stageData = stageData || {};
    const pid = p.provision_id || "";
    const meta = p.cam_metadata || {};
    const stagesRun = new Set(meta.stages_run || []);
    const rulesFired = meta.rules_fired || [];

    // --- Build per-stage lookup tables from _stage_data ---
    const evalRaw = stageData.evaluator_raw || {};
    const challengeRaw = (stageData.challenge_raw || []).find(x => x.provision_id === pid) || null;
    const severityRaw = (stageData.severity_raw || []).find(x => x.provision_id === pid) || null;
    const fragilityRaw = (stageData.fragility || []).find(x => x.provision_id === pid) || null;
    const triage = stageData.triage || {};
    const wasFlagged = (triage.flagged || []).includes(pid);

    let html = `<div class="audit-narrative">`;

    // ── STAGE 1: EXTRACTION ──────────────────────────────────────────────
    const extMeta = stageData.extraction_meta || {};
    html += `
    <div class="audit-stage-block">
        <div class="audit-stage-title">
            <span class="audit-stage-num">Stage 1</span>
            <span class="audit-stage-name">Extraction</span>
            <span class="audit-stage-model">${esc(extMeta.model || modelsUsed.extractor || '\u2014')}</span>
        </div>
        <div class="audit-stage-body">
            <div class="audit-text-pair">
                <div class="audit-text-col">
                    <div class="audit-text-label">Template</div>
                    <div class="audit-text-content">${esc(p.template_text || '(not present in template)')}</div>
                </div>
                <div class="audit-text-col">
                    <div class="audit-text-label">Tenant</div>
                    <div class="audit-text-content">${esc(p.tenant_text || '(not found in tenant lease)')}</div>
                </div>
            </div>${(() => {
                const integrity = p._stage1_integrity;
                if (!integrity) return '';
                const status = integrity.verification_status || 'unknown';
                const statusClass = status === 'verified' ? 'audit-integrity-ok'
                    : (status === 'paraphrased' || status === 'expanded' || status === 'incomplete') ? 'audit-integrity-warn'
                    : 'audit-integrity-neutral';
                let intHtml = `<div class="audit-integrity ${statusClass}">`;
                intHtml += `<span class="audit-integrity-label">Extraction integrity:</span> `;
                intHtml += `<span class="audit-integrity-status">${esc(status)}</span>`;
                if (integrity.length_ratio && integrity.length_ratio !== 1.0) {
                    intHtml += ` <span class="audit-integrity-ratio">(ratio: ${integrity.length_ratio})</span>`;
                }
                if (integrity.repair_applied) {
                    intHtml += ` <span class="audit-integrity-repair">Repaired: ${(integrity.repair_sections || []).join(', ')}</span>`;
                }
                if (integrity.input_frozen) {
                    intHtml += ` <span class="audit-integrity-frozen">&#x1f512; Frozen</span>`;
                }
                intHtml += `</div>`;
                return intHtml;
            })()}
        </div>
    </div>`;

    // ── STAGE 2: RULES CHECK ─────────────────────────────────────────────
    const triageResult = wasFlagged ? 'Flagged for evaluation' : 'Passed \u2014 skipped evaluation';
    const triageClass = wasFlagged ? 'audit-triage-flagged' : 'audit-triage-passed';
    html += `
    <div class="audit-stage-block">
        <div class="audit-stage-title">
            <span class="audit-stage-num">Stage 2</span>
            <span class="audit-stage-name">Rules Check</span>
            <span class="audit-stage-model">Automated (0 API calls)</span>
        </div>
        <div class="audit-stage-body">`;

    if (rulesFired.length > 0) {
        html += `<div class="audit-rules-list">`;
        rulesFired.forEach(ruleId => {
            const fr = fragilityRaw && fragilityRaw.rules_fired && fragilityRaw.rules_fired.find(r => r.rule_id === ruleId);
            const detail = fr ? fr.details : '';
            const excerpts = fr ? (fr.excerpts || []) : [];

            // Build excerpt HTML with highlighted matched phrase
            let excerptHtml = '';
            if (excerpts.length > 0) {
                excerptHtml = excerpts.map(ex => {
                    if (typeof ex === 'string') {
                        return `<div class="audit-rule-excerpt">${esc(ex)}</div>`;
                    }
                    // Highlight matched phrase within context
                    const text = ex.text || '';
                    const phrase = ex.matched_phrase || '';
                    if (phrase && text.toLowerCase().includes(phrase.toLowerCase())) {
                        const idx = text.toLowerCase().indexOf(phrase.toLowerCase());
                        const before = esc(text.slice(0, idx));
                        const match  = esc(text.slice(idx, idx + phrase.length));
                        const after  = esc(text.slice(idx + phrase.length));
                        return `<div class="audit-rule-excerpt">${before}<mark class="audit-rule-highlight">${match}</mark>${after}</div>`;
                    }
                    return `<div class="audit-rule-excerpt">${esc(text)}</div>`;
                }).join('');
            } else if (detail) {
                // Fallback: show detail text without highlighting
                excerptHtml = `<div class="audit-rule-excerpt">${esc(detail)}</div>`;
            }

            html += `<div class="audit-rule-block">
                <div class="audit-rule-header">
                    <span class="audit-rule-id">${esc(ruleId)}</span>
                    ${fr && fr.details && !excerpts.length ? `<span class="audit-rule-detail">${esc(fr.details)}</span>` : ''}
                </div>
                ${excerptHtml}
            </div>`;
        });
        html += `</div>`;
    } else {
        html += `<div class="audit-rule-row audit-rule-none">No rules fired</div>`;
    }
    html += `<div class="audit-triage-result ${triageClass}">${esc(triageResult)}</div>`;
    html += `</div></div>`;

    // ── STAGE 3: EVALUATION ──────────────────────────────────────────────
    if (stagesRun.has(3)) {
        const evalMeta = stageData.evaluation_meta || {};
        html += `
        <div class="audit-stage-block">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 3</span>
                <span class="audit-stage-name">Independent Evaluation</span>
                <span class="audit-stage-model">${esc(evalMeta.evaluator_count || 3)} models in parallel \u00b7 blind to each other</span>
            </div>
            <div class="audit-stage-body">
                <div class="audit-evaluators">`;

        const evalModelMap = {
            A: modelsUsed.evaluator_a || evalName('A'),
            B: modelsUsed.evaluator_b || evalName('B'),
            C: modelsUsed.evaluator_c || evalName('C'),
        };

        ['A','B','C'].forEach(key => {
            const items = evalRaw[key] || [];
            const ev = items.find(x => x.provision_id === pid);
            if (!ev) return;

            const verdict = ev.verdict || '\u2014';
            const conf = ev.confidence != null ? (ev.confidence * 100).toFixed(0) + '%' : '';
            const basis = ev.evidence_basis || '';
            const verdClass = verdict === 'DEVIATES' ? 'audit-eval-deviates'
                            : verdict === 'CONFORMS'  ? 'audit-eval-conforms'
                            : 'audit-eval-na';

            const basisLabel = {
                'explicit_text':        '\uD83D\uDCCC Explicit text',
                'structural_inference': '\uD83D\uDD0D Structural inference',
                'absence':              '\u2205 Absence',
                'ambiguous':            '? Ambiguous',
                'unverified_citation':  '\u26A0 Unverified citation',
            }[basis] || '';

            const keyDiffs = (ev.key_differences || []);

            html += `<div class="audit-eval-card">
                <div class="audit-eval-header2">
                    <span class="audit-eval-key">${esc(key)}</span>
                    <span class="audit-eval-model-name">${esc(evalModelMap[key])}</span>
                    <span class="audit-eval-verdict2 ${verdClass}">${esc(verdict)}</span>
                    ${conf ? `<span class="audit-eval-conf2">${conf}</span>` : ''}
                    ${basisLabel ? `<span class="audit-eval-basis">${basisLabel}</span>` : ''}
                </div>
                ${ev.reasoning ? `<div class="audit-eval-reasoning2">${esc(ev.reasoning)}</div>` : ''}
                ${keyDiffs.length > 0 ? `<ul class="audit-eval-diffs">${keyDiffs.map(d => `<li>${esc(d)}</li>`).join('')}</ul>` : ''}
            </div>`;
        });

        html += `</div>
                <div class="audit-agreement-summary">
                    Agreement: <strong>${esc(p.agreement_pattern || '\u2014')}</strong>
                    ${p.cam_score ? ` \u00b7 Evidence basis: <strong>${esc(p.cam_score.evidence_basis || '\u2014')}</strong>` : ''}
                </div>
            </div>
        </div>`;
    } else {
        html += `<div class="audit-stage-block audit-stage-skipped">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 3</span>
                <span class="audit-stage-name">Evaluation</span>
                <span class="audit-stage-skipped-label">Skipped \u2014 passed rules check</span>
            </div>
        </div>`;
    }

    // ── STAGE 4: CHALLENGE ───────────────────────────────────────────────
    if (stagesRun.has(4) && challengeRaw) {
        const challengeModel = modelsUsed.challenger || '\u2014';
        const cv = challengeRaw.challenge_verdict || '\u2014';
        const cvClass = cv === 'SUBSTANTIVE_DEVIATION' ? 'audit-challenge-sub'
                       : cv === 'COSMETIC_ONLY' ? 'audit-challenge-cos'
                       : cv === 'NEEDS_EXPERT' ? 'audit-challenge-exp'
                       : '';

        html += `
        <div class="audit-stage-block">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 4</span>
                <span class="audit-stage-name">Challenge</span>
                <span class="audit-stage-model">${esc(challengeModel)}</span>
            </div>
            <div class="audit-stage-body">
                <div class="audit-challenge-verdict ${cvClass}">
                    Verdict: ${esc(cv)}
                </div>
                ${challengeRaw.substantive_finding ? `<div class="audit-challenge-finding">${esc(challengeRaw.substantive_finding)}</div>` : ''}
                ${(challengeRaw.hidden_dependencies || []).length > 0 ? `
                <div class="audit-hidden-deps">
                    <div class="audit-detail-label">Hidden Dependencies</div>
                    <ul>${challengeRaw.hidden_dependencies.map(d => `<li>${esc(d)}</li>`).join('')}</ul>
                </div>` : ''}
            </div>
        </div>`;
    } else if (!stagesRun.has(4)) {
        html += `<div class="audit-stage-block audit-stage-skipped">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 4</span>
                <span class="audit-stage-name">Challenge</span>
                <span class="audit-stage-skipped-label">Skipped \u2014 unanimous agreement</span>
            </div>
        </div>`;
    }

    // ── STAGE 5: SEVERITY ────────────────────────────────────────────────
    if (stagesRun.has(5) && severityRaw) {
        const sevModel = (stageData.severity_meta || {}).model || modelsUsed.severity_assessor || '\u2014';
        html += `
        <div class="audit-stage-block">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 5</span>
                <span class="audit-stage-name">Severity Assessment</span>
                <span class="audit-stage-model">${esc(sevModel)}</span>
            </div>
            <div class="audit-stage-body">
                <div class="audit-severity-rating">
                    Rating: <strong>${esc(severityRaw.severity || p.severity || '\u2014')}</strong>
                    ${p.severity_floor_applied ? ' <span class="audit-floor-note">(floor applied)</span>' : ''}
                </div>
                ${severityRaw.severity_reasoning ? `<div class="audit-sev-reasoning">${esc(severityRaw.severity_reasoning)}</div>` : ''}
                ${severityRaw.financial_impact ? `<div class="audit-detail-label" style="margin-top:0.5rem;">Financial Impact</div>
                <div class="audit-sev-reasoning">${esc(severityRaw.financial_impact)}</div>` : ''}
            </div>
        </div>`;
    } else if (!stagesRun.has(5)) {
        html += `<div class="audit-stage-block audit-stage-skipped">
            <div class="audit-stage-title">
                <span class="audit-stage-num">Stage 5</span>
                <span class="audit-stage-name">Severity Assessment</span>
                <span class="audit-stage-skipped-label">Skipped \u2014 provision conforms</span>
            </div>
        </div>`;
    }

    // ── STAGE 6: FRAGILITY + CAM SCORE ──────────────────────────────────
    const camScore = p.cam_score || {};
    html += `
    <div class="audit-stage-block">
        <div class="audit-stage-title">
            <span class="audit-stage-num">Stage 6</span>
            <span class="audit-stage-name">CAM Reliability Score</span>
            <span class="audit-stage-model">Automated \u00b7 0 API calls</span>
        </div>
        <div class="audit-stage-body">`;

    if (fragilityRaw) {
        html += `<div class="audit-fragility-row">
            <span>Fragility: <strong>${fragilityRaw.fragile ? 'yes' : 'no'}</strong></span>
            ${fragilityRaw.fragility_score != null ? `<span style="margin-left:1rem;">Score: ${fragilityRaw.fragility_score.toFixed(3)}</span>` : ''}
        </div>`;
        if ((fragilityRaw.rules_fired || []).length > 0) {
            html += `<div class="audit-frag-signals">`;
            fragilityRaw.rules_fired.forEach(r => {
                html += `<div class="audit-frag-signal-row">
                    <span class="audit-rule-id">${esc(r.rule_id)}</span>
                    <span class="audit-frag-signal-name">${esc(r.signal)}</span>
                    <span class="audit-frag-detail">${esc(r.details || '')}</span>
                    <span class="audit-frag-conf">conf: ${r.confidence.toFixed(2)}</span>
                </div>`;
            });
            html += `</div>`;
        }
    }

    if (camScore.CAM_perm != null) {
        html += `<div class="audit-cam-scores">
            <div class="audit-cam-row">
                <span class="audit-cam-label">CAM (permissive)</span>
                <span class="audit-cam-val">${camScore.CAM_perm}</span>
            </div>
            <div class="audit-cam-row">
                <span class="audit-cam-label">CAM (strict)</span>
                <span class="audit-cam-val">${camScore.CAM_strict}</span>
            </div>
            <div class="audit-cam-row">
                <span class="audit-cam-label">ASG (sensitivity gap)</span>
                <span class="audit-cam-val">${camScore.ASG}</span>
            </div>
            <div class="audit-cam-row">
                <span class="audit-cam-label">Governance signal</span>
                <span class="audit-cam-val"><strong>${esc(camScore.governance_signal || '\u2014')}</strong></span>
            </div>
            <div class="audit-cam-row">
                <span class="audit-cam-label">A \u00b7 E \u00b7 R \u00b7 F</span>
                <span class="audit-cam-val">${camScore.A} \u00b7 ${camScore.E_perm} \u00b7 ${camScore.R_perm} \u00b7 ${camScore.F_perm}</span>
            </div>
        </div>`;
    }

    html += `</div></div>`;

    // ── FINAL DISPOSITION ────────────────────────────────────────────────
    html += `
    <div class="audit-stage-block audit-disposition-block">
        <div class="audit-stage-title">
            <span class="audit-stage-name">Final Disposition</span>
        </div>
        <div class="audit-stage-body">
            <div class="audit-disp-row">
                <span>Verdict: <strong>${esc(p.final_verdict || '\u2014')}</strong></span>
                <span style="margin-left:1.5rem;">Severity: <strong>${esc(p.severity || (p.final_verdict === 'CONFORMS' ? 'N/A' : '\u2014'))}</strong></span>
                ${p.agreement_pattern ? `<span style="margin-left:1.5rem;">Agreement: <strong>${esc(p.agreement_pattern)}</strong></span>` : ''}
            </div>
        </div>
    </div>`;

    html += `</div>`; // close audit-narrative
    return html;
}

function toggleAuditRow(idx) {
    const detail = $(`#audit-detail-${idx}`);
    const header = document.querySelector(`.audit-provision-row[data-idx="${idx}"] .audit-provision-header`);
    if (!detail) return;
    const isOpen = !detail.classList.contains("hidden");
    detail.classList.toggle("hidden");
    const chevron = header && header.querySelector(".audit-chevron");
    if (chevron) chevron.innerHTML = isOpen ? "&#9654;" : "&#9660;";
    syncAuditExpandToggle();
}

function openAllTechDetails() {
    document.querySelectorAll(".adv3-tech-body").forEach(b => b.classList.remove('hidden'));
    document.querySelectorAll(".adv3-tech-details").forEach(w => w.classList.add('adv3-tech-open'));
}

function closeAllTechDetails() {
    document.querySelectorAll(".adv3-tech-body").forEach(b => b.classList.add('hidden'));
    document.querySelectorAll(".adv3-tech-details").forEach(w => w.classList.remove('adv3-tech-open'));
}

function sortAuditTrail(col) {
    if (window._auditSortCol === col) {
        window._auditSortDir = window._auditSortDir === 'asc' ? 'desc' : 'asc';
    } else {
        window._auditSortCol = col;
        window._auditSortDir = 'asc';
    }
    renderAuditTrail();
}

function expandAllAuditRows() {
    const details = Array.from(document.querySelectorAll(".audit-provision-detail"));
    const hasCollapsed = details.some(d => d.classList.contains("hidden"));
    details.forEach(d => d.classList.toggle("hidden", !hasCollapsed));
    document.querySelectorAll(".audit-chevron").forEach(c => { c.innerHTML = hasCollapsed ? "&#9660;" : "&#9654;"; });
    syncAuditExpandToggle();
}

function collapseAllConforming() {
    // Collapse the whole section back to original state — same as clicking the toggle
    const list = document.getElementById('conforming-list');
    const toggle = document.getElementById('conforming-toggle');
    if (!list || !toggle) return;
    list.classList.add('hidden');
    toggle.innerHTML = toggle.innerHTML.replace('&#9660;', '&#9654;');
    // Scroll to the toggle so user lands back at the section header
    toggle.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function collapseAllAuditRows() {
    document.querySelectorAll(".audit-provision-detail").forEach(d => d.classList.add("hidden"));
    document.querySelectorAll(".audit-chevron").forEach(c => { c.innerHTML = "&#9662;"; });
    syncAuditExpandToggle();
}

function syncAuditExpandToggle() {
    const buttons = Array.from(document.querySelectorAll(".audit-controls-buttons .btn-audit-control"));
    if (buttons.length === 0) return;
    const primary = buttons[0];
    const secondary = buttons[1];
    if (secondary) secondary.classList.add("hidden");
    const details = Array.from(document.querySelectorAll(".audit-provision-detail"));
    const hasCollapsed = details.some(d => d.classList.contains("hidden"));
    if (primary) {
        primary.textContent = hasCollapsed ? "Expand all" : "Collapse all";
        primary.setAttribute("onclick", "window.CAM.expandAllAuditRows()");
    }
}

// ── Resolution Workflow Functions ──

function formatResTimestamp(iso) {
    try {
        const d = new Date(iso);
        return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
             + " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    } catch { return ""; }
}

async function setResolutionStatus(pid, tenantIdx, status, buttonEl) {
    const key = `${tenantIdx}:${pid}`;
    if (!resolutionState[key]) resolutionState[key] = { status: "open", notes: [] };
    if (status === "resolved" && resolutionState[key].status === "resolved") {
        status = "open";
    }
    if (status === "not_a_deviation" && resolutionState[key].status === "not_a_deviation") {
        status = "open";
    }
    resolutionState[key].status = status;

    // Optimistic UI: update pills
    const bar = document.querySelector(`.resolution-bar[data-pid="${pid}"][data-tenant-idx="${tenantIdx}"]`);
    if (bar) {
        bar.querySelectorAll(".res-pill").forEach(p => {
            p.classList.toggle("res-pill-active", p.dataset.status === status);
        });
    }

    // Update card resolved class
    const card = document.getElementById(`dev-${pid}`);
    if (card) {
        card.classList.toggle("resolution-resolved", status === "resolved" || status === "not_a_deviation");
    }

    if (status === "not_a_deviation") {
        try {
            await fetch(`/api/jobs/${currentJobId}/feedback`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    tenant_index: tenantIdx,
                    provision_id: pid,
                    assessment: "disagree",
                })
            });
        } catch (err) {
            console.error("Feedback error:", err);
        }
        if (confirm("Create a rule so this won't be flagged in future analyses?")) {
            window.CAM.showRuleCreationDialog(pid, pid);
        }
    }

    // Refresh progress bar
    refreshResolutionProgress(tenantIdx);
    renderNavSidebar();
    if (contractDetailOpen && tenantIdx === currentTenantIndex) updateContractDetailHeader(tenantIdx);
    if (contractDetailOpen && tenantIdx === currentTenantIndex) {
        const tenant = currentResults && currentResults.tenants ? currentResults.tenants[tenantIdx] : null;
        renderContractClauseFilterBar((tenant && tenant.results && tenant.results.provisions) || []);
    }
    updateFinalDraftBar();
    applyContractClauseFilters();
    refreshDocviewIfActive(tenantIdx);

    // Persist
    try {
        await fetch(`/api/jobs/${currentJobId}/resolution`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tenant_idx: tenantIdx, provision_id: pid, status })
        });
    } catch (e) { console.error("Resolution save failed", e); }
}

function setResolutionResolvedFromDecision(tenantIdx, pid) {
    const key = `${tenantIdx}:${pid}`;
    if (!resolutionState[key]) resolutionState[key] = { status: "open", notes: [] };
    if (resolutionState[key].status === "resolved") return;
    setResolutionStatus(pid, tenantIdx, "resolved");
}

function toggleResolutionNotes(pid, tenantIdx) {
    const panel = document.getElementById(`res-notes-${pid}-${tenantIdx}`);
    const advisorPanel = document.getElementById(`res-advisor-${pid}-${tenantIdx}`);
    if (!panel) return;
    if (advisorPanel) advisorPanel.classList.add("hidden");
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) {
        const input = document.getElementById(`res-input-${pid}-${tenantIdx}`);
        if (input) input.focus();
    }
}

function openResolutionAdvisor(pid, tenantIdx) {
    const panel = document.getElementById(`res-advisor-${pid}-${tenantIdx}`);
    const notesPanel = document.getElementById(`res-notes-${pid}-${tenantIdx}`);
    if (notesPanel) notesPanel.classList.add("hidden");
    if (panel) panel.classList.add("hidden");
    askAboutFinding(pid, tenantIdx, "");
    showChatAdvisorPrompts(pid, tenantIdx);
}

async function saveResolutionNote(pid, tenantIdx) {
    const input = document.getElementById(`res-input-${pid}-${tenantIdx}`);
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    const saved = await addResolutionNote(pid, tenantIdx, text);
    if (saved) input.value = "";
}

function legacyUpdateResolutionNoteCount(pid, tenantIdx) {
    const key = `${tenantIdx}:${pid}`;
    const count = ((resolutionState[key] || {}).notes || []).length;
    const toggleBtn = document.querySelector(`.res-notes-toggle[data-pid="${pid}"][data-tenant-idx="${tenantIdx}"]`);
    if (!toggleBtn) return;
    if (count > 0) {
        toggleBtn.innerHTML = `📝 Notes <span class="res-note-count">${count} note${count > 1 ? "s" : ""}</span>`;
    } else {
        toggleBtn.innerHTML = `📝 Notes`;
    }
}

function legacyRenderResolutionNotesPanel(pid, tenantIdx) {
    const key = `${tenantIdx}:${pid}`;
    const panel = document.getElementById(`res-notes-${pid}-${tenantIdx}`);
    if (!panel) return;
    const notes = ((resolutionState[key] || {}).notes || []);
    const inputRow = panel.querySelector(".res-note-input-row");
    panel.querySelectorAll(".res-note-entry").forEach(el => el.remove());
    notes.forEach((note, noteIdx) => {
        const noteDiv = document.createElement("div");
        noteDiv.className = "res-note-entry";
        noteDiv.innerHTML = `<span class="res-note-ts">${formatResTimestamp(note.timestamp)}</span><span class="res-note-text">${esc(note.text)}</span><button class="res-note-delete" onclick="window.CAM.deleteResolutionNote('${esc(pid)}', ${tenantIdx}, ${noteIdx}); event.stopPropagation();">Delete</button>`;
        if (inputRow) panel.insertBefore(noteDiv, inputRow);
        else panel.appendChild(noteDiv);
    });
}

function updateResolutionNoteCount(pid, tenantIdx) {
    const key = `${tenantIdx}:${pid}`;
    const count = ((resolutionState[key] || {}).notes || []).length;
    const toggleBtn = document.querySelector(`.res-notes-toggle[data-pid="${pid}"][data-tenant-idx="${tenantIdx}"]`);
    if (!toggleBtn) return;
    toggleBtn.innerHTML = buildNotesToggleHtml("Notes", count);
}

function renderResolutionNotesPanel(pid, tenantIdx) {
    const key = `${tenantIdx}:${pid}`;
    const panel = document.getElementById(`res-notes-${pid}-${tenantIdx}`);
    if (!panel) return;
    const notes = ((resolutionState[key] || {}).notes || []);
    const inputRow = panel.querySelector(".res-note-input-row");
    renderNotesPanelEntries(panel, notes, inputRow, {
        esc,
        formatResTimestamp,
        buildDeleteButtonHtml: (noteIdx) => `<button class="res-note-delete" onclick="window.CAM.deleteResolutionNote('${esc(pid)}', ${tenantIdx}, ${noteIdx}); event.stopPropagation();">Delete</button>`,
    });
}

async function addResolutionNote(pid, tenantIdx, text) {
    const key = `${tenantIdx}:${pid}`;
    const now = new Date().toISOString();
    const normalized = (text || "").trim();
    if (!normalized) return false;
    if (!resolutionState[key]) resolutionState[key] = { status: "open", notes: [] };
    resolutionState[key].notes.push({ text: normalized, timestamp: now });

    // Append note to panel immediately
    renderResolutionNotesPanel(pid, tenantIdx);

    // Update note count on toggle button
    updateResolutionNoteCount(pid, tenantIdx);

    // Persist
    try {
        await fetch(`/api/jobs/${currentJobId}/resolution`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tenant_idx: tenantIdx, provision_id: pid, note: normalized })
        });
    } catch (e) { console.error("Note save failed", e); }
    if (contractDetailOpen && tenantIdx === currentTenantIndex) {
        const tenant = currentResults && currentResults.tenants ? currentResults.tenants[tenantIdx] : null;
        renderContractClauseFilterBar((tenant && tenant.results && tenant.results.provisions) || []);
    }
    applyContractClauseFilters();
    refreshDocviewIfActive(tenantIdx);
    renderDocviewResolutionNotesPanel(pid, tenantIdx);
    updateDocviewResolutionNoteCount(pid, tenantIdx);
    return true;
}

async function deleteResolutionNote(pid, tenantIdx, noteIdx) {
    const key = `${tenantIdx}:${pid}`;
    if (!resolutionState[key] || !Array.isArray(resolutionState[key].notes)) return false;
    if (noteIdx < 0 || noteIdx >= resolutionState[key].notes.length) return false;
    if (!window.confirm("Delete this note?")) return false;
    resolutionState[key].notes.splice(noteIdx, 1);

    renderResolutionNotesPanel(pid, tenantIdx);
    updateResolutionNoteCount(pid, tenantIdx);

    try {
        await fetch(`/api/jobs/${currentJobId}/resolution`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tenant_idx: tenantIdx, provision_id: pid, notes: resolutionState[key].notes })
        });
    } catch (e) { console.error("Note delete failed", e); }
    if (contractDetailOpen && tenantIdx === currentTenantIndex) {
        const tenant = currentResults && currentResults.tenants ? currentResults.tenants[tenantIdx] : null;
        renderContractClauseFilterBar((tenant && tenant.results && tenant.results.provisions) || []);
    }
    applyContractClauseFilters();
    refreshDocviewIfActive(tenantIdx);
    renderDocviewResolutionNotesPanel(pid, tenantIdx);
    updateDocviewResolutionNoteCount(pid, tenantIdx);
    return true;
}

async function saveChatResponseAsNote(text) {
    if (!canSaveChatNote()) return false;
    const tenantIdx = parseInt(chatScopeTenantIdx, 10);
    const pid = chatScopeProvisionId;
    if (Number.isNaN(tenantIdx) || !pid) return false;
    return await addResolutionNote(pid, tenantIdx, text);
}

const ADVISOR_PROMPTS = {
    summary:   "Summarize this clause issue for me in practical terms. What changed, why it matters, and what to watch.",
    advice:    "Advise what to do with this clause. Should we keep tenant language, push for reference language, modify it, or escalate to the client?",
    rewrite:   "Draft replacement language for this provision that restores the standard template intent while giving the tenant something reasonable.",
    risk:      "What is the practical legal and financial risk if we accept this deviation as-is without modification?",
    standard:  "Is this type of provision modification standard or common in commercial lease negotiations? How unusual is it?",
};

function askResolution(pid, tenantIdx, promptKey) {
    const promptText = ADVISOR_PROMPTS[promptKey] || "Tell me more about this deviation.";

    // Close advisor panel
    const panel = document.getElementById(`res-advisor-${pid}-${tenantIdx}`);
    if (panel) panel.classList.add("hidden");

    // Use existing askAboutFinding to set context, then override the prompt
    askAboutFinding(pid, tenantIdx);
    showChatAdvisorPrompts(pid, tenantIdx);
    const input = $("#chat-input");
    if (input) {
        input.value = promptText;
        input.focus();
    }
}

function refreshResolutionProgress(tenantIdx) {
    return;
}

// ══════════════════════════════════════════════════════
// STEP 116 — Three-level Navigation, Run Snapshot,
//            Contract Resolution, Completion Banner
// ══════════════════════════════════════════════════════

// ── Contract Resolution (localStorage) ──

function legacyGetContractResolutionKey(tenantIdx) {
    const tenant = currentResults && currentResults.tenants && currentResults.tenants[tenantIdx];
    const name = tenant ? (tenant.filename || "tenant_" + tenantIdx) : "tenant_" + tenantIdx;
    return "cam_res_" + currentJobId + "_" + name;
}

function legacyGetContractResolution(tenantIdx) {
    if (!currentResults || !currentResults.tenants || !currentResults.tenants[tenantIdx]) return "unreviewed";
    const tenant = currentResults.tenants[tenantIdx];
    if (!tenant.results) return "unreviewed";
    const workflowProvisions = getDeviationWorkflowProvisions((tenant.results.provisions || []), tenantIdx);
    if (workflowProvisions.length === 0) return "clean";
    const allClosed = workflowProvisions.every(function(p) {
        const key = `${tenantIdx}:${p.provision_id}`;
        const status = (resolutionState[key] || {}).status || "open";
        return status === "resolved" || status === "not_a_deviation";
    });
    if (allClosed) return "resolved";
    const key = legacyGetContractResolutionKey(tenantIdx);
    try { return localStorage.getItem(key) || "unreviewed"; } catch(e) { return "unreviewed"; }
}

function setContractResolution(tenantIdx, status) {
    const key = getContractResolutionKey(tenantIdx);
    try { localStorage.setItem(key, status); } catch(e) { /* silent */ }
    renderNavSidebar();
    if (!contractDetailOpen) renderRunSnapshot();
    checkCompletionBanner();
}

function markContractResolved(tenantIdx) {
    setContractResolution(tenantIdx, "resolved");
    closeContractDetail();
}

function reopenContract(tenantIdx) {
    setContractResolution(tenantIdx, "unreviewed");
    renderContractResolutionControls(tenantIdx);
    renderNavSidebar();
}

// ── Per-provision Noted toggle (localStorage) ──

function getNotedKey(tenantIdx, pid) {
    return "cam_noted_" + currentJobId + "_" + tenantIdx + "_" + pid;
}

function toggleNoted(tenantIdx, pid, btn) {
    const key = getNotedKey(tenantIdx, pid);
    try {
        const current = localStorage.getItem(key) === "1";
        if (current) {
            localStorage.removeItem(key);
            btn.classList.remove("noted-active");
            btn.textContent = "Mark as Read";
        } else {
            localStorage.setItem(key, "1");
            btn.classList.add("noted-active");
            btn.textContent = "\u2713 Read";
        }
    } catch(e) { /* silent */ }
    if (contractDetailOpen && tenantIdx === currentTenantIndex) {
        const tenant = currentResults && currentResults.tenants ? currentResults.tenants[tenantIdx] : null;
        renderContractClauseFilterBar((tenant && tenant.results && tenant.results.provisions) || []);
    }
    applyContractClauseFilters();
    refreshDocviewIfActive(tenantIdx);
}

function isNoted(tenantIdx, pid) {
    try { return localStorage.getItem(getNotedKey(tenantIdx, pid)) === "1"; } catch(e) { return false; }
}

// ── Completion Banner ──

function checkCompletionBanner() {
    const banner = document.getElementById("review-completion-banner");
    if (!banner || !currentResults || !currentResults.tenants) return;
    const allDone = currentResults.tenants.every(function(_, i) {
        const res = getContractResolution(i);
        return res === "resolved" || res === "clean";
    });
    if (allDone && currentResults.tenants.length > 0) {
        banner.innerHTML = '\u2713 Review complete \u2014 all contracts have been assessed.';
        banner.classList.remove("hidden");
    } else {
        banner.classList.add("hidden");
    }
}

// ── Top-Level Tab Switching ──

function setSubheader(label, rightHtml) {
    var el = document.getElementById('tab-subheader');
    if (!el) return;
    // Step 281: subheader bar can carry an optional right-aligned
    // suffix (e.g. "Perspective: Tenant" on the Coverage & Gaps tab
    // for Mode C runs). When rightHtml is omitted the bar renders
    // exactly as it did pre-Step-281 — left-aligned label only.
    if (rightHtml) {
        el.innerHTML =
            '<span class="tab-subheader-label">' + esc(label) + '</span>' +
            '<span class="tab-subheader-right">' + rightHtml + '</span>';
        el.classList.add('tab-subheader-flex');
    } else {
        el.textContent = label;
        el.classList.remove('tab-subheader-flex');
    }
}

// Step 281: perspective indicator for the Coverage & Gaps tab subheader.
// Mirrors the same precedence the Synopsis PDF uses: top-level
// `perspective` field on the result dict → most-common
// `coverage_assessment[].exposure_perspective` → "tenant" default.
// Returns the formatted right-side HTML (empty string when not Mode C).
function _coverageSubheaderRight() {
    if (!isJobModeC()) return "";
    var tr = (currentResults && currentResults.tenants)
        ? currentResults.tenants[currentTenantIndex || 0]
        : null;
    var pr = tr && tr.results ? tr.results : null;
    if (!pr) return "";
    var p = (pr.perspective || "").toString().trim().toLowerCase();
    if (!p) {
        var ca = pr.coverage_assessment || [];
        var counts = {};
        for (var i = 0; i < ca.length; i++) {
            var v = (ca[i].exposure_perspective || "").toString().trim().toLowerCase();
            if (!v) continue;
            counts[v] = (counts[v] || 0) + 1;
        }
        var best = "";
        var bestN = 0;
        for (var k in counts) {
            if (counts[k] > bestN) { best = k; bestN = counts[k]; }
        }
        p = best || "tenant";
    }
    var labels = { tenant: "Tenant", landlord: "Landlord", neutral: "Neutral" };
    var label = labels[p] || (p.charAt(0).toUpperCase() + p.slice(1));
    return '<span class="tab-subheader-perspective"><span class="tab-subheader-perspective-key">Perspective:</span> ' + esc(label) + '</span>';
}

function switchTopTab(tab) {
    const overview   = document.getElementById('overview-tab-content');
    const contractsT = document.getElementById('contracts-tab-content');
    const detail     = document.getElementById('contract-detail-view');
    const ncp        = document.getElementById('no-contract-placeholder');

    if (tab === 'contracts') {
        activeTopTab = 'contracts';
        persistResultsViewState();
        setSubheader('Contracts');
        if (overview)   overview.classList.add('hidden');
        if (detail)     detail.classList.add('hidden');
        if (ncp)        ncp.classList.add('hidden');
        if (contractsT) contractsT.classList.remove('hidden');
        document.querySelectorAll('#top-tab-bar .top-tab[data-top-tab]').forEach(function(t) {
            t.classList.toggle('active', t.dataset.topTab === 'contracts');
        });
        document.querySelectorAll('#top-tab-bar .top-tab[data-tab]').forEach(function(t) { t.classList.remove('active'); });
        renderRunSnapshot();
        return;
    }

    // Contract detail tabs — findings / docview / audittrail / coverage
    if (tab === 'findings' || tab === 'docview' || tab === 'audittrail' || tab === 'coverage') {
        activeTopTab = tab;
        activeResultsTab = tab;
        persistResultsViewState();
        // Hide overview and contracts list panels
        if (overview)   overview.classList.add('hidden');
        if (contractsT) contractsT.classList.add('hidden');
        // Show the detail container (switchResultsTab manages inner panels + ncp)
        if (detail)     detail.classList.remove('hidden');
        // Mark the correct top-tab button as active
        document.querySelectorAll('#top-tab-bar .top-tab[data-top-tab]').forEach(function(t) {
            t.classList.toggle('active', t.dataset.topTab === tab);
        });
        // Delegate inner panel switching to switchResultsTab
        switchResultsTab(tab);
        return;
    }

    // overview / snapshot
    activeTopTab = 'overview';
    persistResultsViewState();
    setSubheader('Overview');
    document.querySelectorAll('#top-tab-bar .top-tab[data-top-tab]').forEach(function(t) {
        t.classList.toggle('active', t.dataset.topTab === 'overview');
    });
    if (contractDetailOpen) {
        closeContractDetail();
    }
    if (ncp)        ncp.classList.add('hidden');
    if (contractsT) contractsT.classList.add('hidden');
    if (overview)   overview.classList.remove('hidden');
    if (detail)     detail.classList.add('hidden');
    document.querySelectorAll('#top-tab-bar .top-tab[data-tab]').forEach(function(t) { t.classList.remove('active'); });
}

// ── Step 130: Contract name filter dropdown builder ──

function buildContractFilterDropdown() {
    var dropdown = document.getElementById('snapshot-contract-dropdown');
    var btn = document.getElementById('snapshot-contract-filter-btn');
    var wrap = document.getElementById('snapshot-contract-filter-wrap');
    if (!dropdown || !btn || !currentResults || !currentResults.tenants) return;

    // Determine which tenants pass the current non-contract filters.
    var tenants = currentResults.tenants;
    var eligibleIndices = [];
    tenants.forEach(function(t, i) {
        var s = t.results && t.results.summary ? t.results.summary : null;
        var provisions = t.results && t.results.provisions ? t.results.provisions : [];
        var deviations = getDeviationWorkflowProvisions(provisions, i);
        var highestSev = s ? getHighestSeverity(s) : null;
        if (deviations.length > 0) {
            highestSev = deviations.reduce(function(best, p) {
                if (!best) return p.severity || 'MEDIUM';
                return SEVERITY_ORDER.indexOf(p.severity || 'LOW') <= SEVERITY_ORDER.indexOf(best) ? (p.severity || best) : best;
            }, highestSev);
        }
        var isClean = deviations.length === 0 && s;
        var resolution = getContractResolution(i);

        // Severity filter (multi-select)
        var sevOk = true;
        if (snapshotSeverityFilter.size > 0) {
            if (isClean) {
                sevOk = snapshotSeverityFilter.has('CLEAR');
            } else {
                sevOk = snapshotSeverityFilter.has((highestSev || '').toUpperCase());
            }
        }

        // Confidence filter (multi-select) — match if ANY deviation has the selected signal
        var confOk = true;
        if (snapshotConfidenceFilter.size > 0) {
            var provs = t.results && t.results.provisions ? t.results.provisions : [];
            var devs = getDeviationWorkflowProvisions(provs, i);
            confOk = devs.some(function(p) {
                var sig = p.cam_score ? p.cam_score.governance_signal : '';
                return snapshotConfidenceFilter.has(sig);
            });
        }

        // Status filter
        var statusOk = true;
        if (snapshotStatusFilter === 'unreviewed') statusOk = resolution !== 'resolved' && !isClean;
        else if (snapshotStatusFilter === 'resolved') statusOk = resolution === 'resolved';
        else if (snapshotStatusFilter === 'clear') statusOk = isClean;

        var searchOk = true;
        if (snapshotSearch) {
            var q = snapshotSearch.toLowerCase();
            var meta = t.results && t.results.contract_metadata ? t.results.contract_metadata : {};
            var name = formatTenantName(t.filename || ('Contract ' + (i + 1)));
            var tenantName = (meta.tenant_name || '').trim();
            var propertyDesc = (meta.property_description || '').trim();
            searchOk = name.toLowerCase().indexOf(q) !== -1
                || tenantName.toLowerCase().indexOf(q) !== -1
                || propertyDesc.toLowerCase().indexOf(q) !== -1;
        }

        if (sevOk && confOk && statusOk && searchOk) eligibleIndices.push(i);
    });

    // Build checkbox list
    var html = '<div class="snapshot-contract-dropdown-inner">';
    if (eligibleIndices.length === 0) {
        html += '<div class="snapshot-contract-dropdown-empty">No contracts match current filters</div>';
    } else {
        // "All" checkbox at top
        var allChecked = snapshotContractFilter.size === 0;
        html += '<label class="snapshot-contract-check-row snapshot-contract-all-row">'
            + '<input type="checkbox" class="snapshot-contract-check-all" ' + (allChecked ? 'checked' : '') + '>'
            + '<span>All contracts</span>'
            + '</label>';

        eligibleIndices.forEach(function(i) {
            var t = tenants[i];
            var name = formatTenantName(t.filename || ('Contract ' + (i + 1)));
            var s = t.results && t.results.summary ? t.results.summary : null;
            var highest = s ? getHighestSeverity(s) : null;
            var statusLabel = getStatusLabel(highest);
            var checked = snapshotContractFilter.size === 0 || snapshotContractFilter.has(i);
            html += '<label class="snapshot-contract-check-row">'
                + '<input type="checkbox" class="snapshot-contract-check-item" data-tenant="' + i + '" ' + (checked ? 'checked' : '') + '>'
                + '<span class="snapshot-contract-check-name">' + esc(name) + '</span>'
                + '<span class="snapshot-contract-check-status">' + esc(statusLabel) + '</span>'
                + '</label>';
        });
    }
    // Apply button at bottom — closes dropdown and triggers render
    html += '<div class="snapshot-contract-dropdown-footer">'
        + '<button class="snapshot-contract-apply-btn">Apply</button>'
        + '</div>';
    html += '</div>';
    dropdown.innerHTML = html;

    // Wire: toggle dropdown open/close on button click
    btn.onclick = function(e) {
        e.stopPropagation();
        // Close other filter dropdowns
        ['snap-severity-panel', 'snap-confidence-panel'].forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.classList.add('hidden');
        });
        dropdown.classList.toggle('hidden');
    };

    // Wire: "All contracts" checkbox — just updates state, no re-render yet
    var allChk = dropdown.querySelector('.snapshot-contract-check-all');
    if (allChk) {
        allChk.addEventListener('change', function() {
            // Check all individual boxes
            dropdown.querySelectorAll('.snapshot-contract-check-item').forEach(function(c) {
                c.checked = true;
            });
        });
    }

    // Wire: individual checkboxes — just update "All" state, no re-render yet
    dropdown.querySelectorAll('.snapshot-contract-check-item').forEach(function(chk) {
        chk.addEventListener('change', function() {
            var allItems = dropdown.querySelectorAll('.snapshot-contract-check-item');
            var allCheckedNow = Array.from(allItems).every(function(c) { return c.checked; });
            if (allChk) allChk.checked = allCheckedNow;
        });
    });

    // Wire: Apply button — commit selection, close dropdown, re-render
    var applyBtn = dropdown.querySelector('.snapshot-contract-apply-btn');
    if (applyBtn) {
        applyBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            var allItems = dropdown.querySelectorAll('.snapshot-contract-check-item');
            var newSet = new Set();
            allItems.forEach(function(c) {
                if (c.checked) newSet.add(parseInt(c.dataset.tenant, 10));
            });
            // If all checked, treat as no filter
            if (newSet.size === eligibleIndices.length) newSet = new Set();
            snapshotContractFilter = newSet;
            btn.textContent = snapshotContractFilter.size === 0
                ? 'Contracts: All \u25BE'
                : 'Contracts: ' + snapshotContractFilter.size + ' selected \u25BE';
            dropdown.classList.add('hidden');
            renderRunSnapshot();
        });
    }
}

function applyContractFilterAndRenderCards() {
    renderRunSnapshot();
}

// ── Run Snapshot Rendering ──

function setResultsContentDetailMode(enabled) {
    var resultsContent = document.getElementById('results-content');
    if (!resultsContent) return;
    resultsContent.classList.toggle('results-content-detail', !!enabled);
}

// Step 259: Mode C variant of the Run Snapshot card grid. Buckets each tenant
// by worst coverage tier (attention > review > ok) and emits cards using the
// .snapshot-card classes plus a Mode-C-specific .snapshot-card-modec marker.
// The Mode A toolbar is hidden via .hidden because its severity/confidence/
// status filters don't apply when there are no deviations to filter.
function renderModeCRunSnapshot(container) {
    const tenants = (currentResults && currentResults.tenants) || [];

    var toolbarBar = document.getElementById('snapshot-toolbar-bar');
    if (toolbarBar) {
        toolbarBar.classList.add('hidden');
        toolbarBar.innerHTML = '';
    }

    if (tenants.length === 0) {
        container.innerHTML = '<div class="snapshot-no-results">No leases analyzed yet</div>';
        return;
    }

    // Step 340: Build per-tenant risk triage summary using deriveProvisionRiskLevel().
    // cross_provision_findings and perspective are now included so the card tells
    // the same story as the Risk Map \u2014 coverage_state alone was insufficient.
    const _covRes = window._covResStateRef || {};
    const _cardPerspective = getJobPerspective();

    // Priority order for top risk driver sorting.
    function _driverPriority(reason) {
        if (reason === 'HIGH compound risk') return 4;
        if (reason === '3-0 adverse directional mismatch') return 3;
        if (reason === 'Missing provision') return 2;
        return 1;
    }

    const tenantData = tenants.map(function(t, i) {
        const ca    = (t && t.results && t.results.coverage_assessment) || [];
        const cpfs  = (t && t.results && t.results.cross_provision_findings) || [];

        // Derive risk levels for every LP.
        let riskRed = 0, riskAmber = 0, riskGreen = 0, riskGray = 0;
        const redLps = [];
        ca.forEach(function(a) {
            const risk = deriveProvisionRiskLevel(a, cpfs, _cardPerspective);
            if (risk.risk_level === 'red')        { riskRed++;   redLps.push({ a: a, risk: risk }); }
            else if (risk.risk_level === 'amber') { riskAmber++; }
            else if (risk.risk_level === 'green') { riskGreen++; }
            else                                 { riskGray++;  }
        });

        // Top risk drivers: top 5 RED LPs ranked by dominant signal.
        redLps.sort(function(x, y) {
            return _driverPriority(y.risk.dominant_reason) - _driverPriority(x.risk.dominant_reason);
        });
        const topDrivers = redLps.slice(0, 5);

        // Coverage gaps: missing LPs.
        const coverageGaps = ca.filter(function(a) { return a.coverage_state === 'missing'; });

        // Secondary finding counts.
        const compoundCount = cpfs.filter(function(f) { return f.finding_type === 'compound_risk'; }).length;
        const dirCount      = cpfs.filter(function(f) { return f.finding_type === 'directional_mismatch'; }).length;

        const name = formatTenantName(t.filename) || ("Lease " + (i + 1));
        let tier, action, actionClass;
        if (riskRed > 0) {
            tier = 'problems'; action = '\u26A0 Issues to Address'; actionClass = 'action-badge-critical';
        } else if (riskAmber > 0) {
            tier = 'review';   action = '\u00B7 Review Recommended'; actionClass = 'action-badge-medium';
        } else if (riskGreen > 0) {
            tier = 'ok';       action = '\u2713 Adequate Coverage';  actionClass = 'action-badge-clear';
        } else {
            tier = 'empty';    action = 'No analysis';               actionClass = 'res-badge-empty';
        }

        return {
            t: t, i: i, name: name,
            riskRed: riskRed, riskAmber: riskAmber, riskGreen: riskGreen, riskGray: riskGray,
            topDrivers: topDrivers, coverageGaps: coverageGaps,
            compoundCount: compoundCount, dirCount: dirCount,
            tier: tier, action: action, actionClass: actionClass
        };
    });

    // Sort: problems first (most red LPs), then review (most amber), then ok
    const tierOrder = { problems: 0, review: 1, ok: 2, empty: 3 };
    tenantData.sort(function(a, b) {
        const tDiff = (tierOrder[a.tier] || 99) - (tierOrder[b.tier] || 99);
        if (tDiff !== 0) return tDiff;
        if (b.riskRed !== a.riskRed) return b.riskRed - a.riskRed;
        return b.riskAmber - a.riskAmber;
    });

    let html = '<div class="snapshot-grid">';
    tenantData.forEach(function(d) {
        const activeClass = (snapshotActiveIndex === d.i) ? ' contract-card-active' : '';
        const nameEsc = esc(d.name);

        // Step 340: risk summary pills (reuse existing modec-count color classes)
        const countParts = [];
        if (d.riskRed > 0)   countParts.push('<span class="modec-count modec-count-attn"><strong>' + d.riskRed + '</strong> high risk</span>');
        if (d.riskAmber > 0) countParts.push('<span class="modec-count modec-count-review"><strong>' + d.riskAmber + '</strong> review</span>');
        if (d.riskGreen > 0) countParts.push('<span class="modec-count modec-count-ok"><strong>' + d.riskGreen + '</strong> clean</span>');
        if (d.riskGray > 0)  countParts.push('<span class="modec-count modec-count-na"><strong>' + d.riskGray + '</strong> N/A</span>');
        const countLine = countParts.length > 0 ? '<div class="modec-count-row">' + countParts.join('') + '</div>' : '';

        // Secondary counts row: compound, directional, coverage gap counts
        const secParts = [];
        if (d.compoundCount > 0)         secParts.push(d.compoundCount + ' compound risk' + (d.compoundCount !== 1 ? 's' : ''));
        if (d.dirCount > 0)              secParts.push(d.dirCount + ' directional finding' + (d.dirCount !== 1 ? 's' : ''));
        if (d.coverageGaps.length > 0)   secParts.push(d.coverageGaps.length + ' coverage gap' + (d.coverageGaps.length !== 1 ? 's' : ''));
        const secondaryLine = secParts.length > 0
            ? '<div class="modec-secondary-row">' + esc(secParts.join(' · ')) + '</div>'
            : '';

        // Top risk drivers: ranked red LP chips (max 5)
        let driverHtml = '';
        if (d.topDrivers.length > 0) {
            driverHtml = '<div class="modec-risk-drivers"><span class="modec-risk-drivers-label">Top risk drivers:</span><div class="overview-chip-row">';
            d.topDrivers.forEach(function(item) {
                const a = item.a;
                const pid = a.issue_area_id || '';
                const shortName = (a.issue_area_name || pid).replace(/^LP-\d{2}\s*/, '');
                const label = pid + (shortName ? ' ' + shortName : '');
                driverHtml += '<span class="overview-chip overview-chip-risk chip-jumpable-risk"'
                            + ' data-tenant="' + d.i + '" data-pid="' + esc(pid) + '"'
                            + ' title="' + esc(item.risk.dominant_reason) + '">'
                            + esc(label) + '</span>';
            });
            driverHtml += '</div></div>';
        }

        // Coverage gaps text line (labeled, not chips)
        let gapLine = '';
        if (d.coverageGaps.length > 0) {
            const gapIds = d.coverageGaps.map(function(a) { return a.issue_area_id || ''; }).filter(Boolean);
            gapLine = '<div class="modec-gap-line"><span class="modec-gap-label">Coverage gaps:</span> ' + esc(gapIds.join(' · ')) + '</div>';
        }

        let bodyMsg = '';
        if (d.tier === 'ok') {
            bodyMsg = 'All issue areas addressed — no adverse findings';
        } else if (d.tier === 'empty') {
            bodyMsg = 'No coverage analysis available';
        }
        const bodyLine = bodyMsg ? '<div class="snapshot-card-body snapshot-card-body-clean">' + esc(bodyMsg) + '</div>' : '';

        html += '<div class="snapshot-card snapshot-card-modec snapshot-card-modec-' + d.tier + activeClass + '" data-tenant="' + d.i + '">'
            + '<div class="snapshot-card-header">'
            + '<span class="snapshot-card-name">' + nameEsc + '</span>'
            + '<div class="snapshot-card-badges">'
            + '<span class="snapshot-action-badge ' + d.actionClass + '">' + d.action + '</span>'
            + '</div>'
            + '</div>'
            + countLine
            + secondaryLine
            + driverHtml
            + gapLine
            + bodyLine
            + '<div class="snapshot-card-footer">'
            + '<button class="snapshot-open-btn" data-tenant="' + d.i + '">Open Contract \u2192</button>'
            + '</div>'
            + '</div>';
    });
    html += '</div>';

    container.innerHTML = html;

    // Wire "Open Contract" buttons
    container.querySelectorAll('.snapshot-open-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var idx = parseInt(btn.dataset.tenant, 10);
            openContractDetail(idx);
        });
    });

    // Wire top risk driver chips: open contract (user navigates from there)
    container.querySelectorAll('.chip-jumpable-risk[data-pid]').forEach(function(chip) {
        chip.addEventListener('click', function(e) {
            e.stopPropagation();
            var idx = parseInt(chip.dataset.tenant, 10);
            openContractDetail(idx);
        });
    });
}

function renderRunSnapshot() {
    const container = document.getElementById("snapshot-cards");
    if (!container || !currentResults || !currentResults.tenants) return;
    // Ensure the contracts tab content is visible
    var contractsTab = document.getElementById('contracts-tab-content');
    if (contractsTab) contractsTab.classList.remove('hidden');

    // Step 259: Mode C — branch BEFORE building Mode A cards/toolbar.
    // Mode A's filters (severity/confidence/status) and chip layout don't fit
    // Mode C; the coverage-tier variant emits its own grid + hides the toolbar.
    if (isJobModeC()) {
        renderModeCRunSnapshot(container);
        return;
    }

    const tenants = currentResults.tenants;
    function getSnapshotSeverityRank(severity) {
        const idx = SEVERITY_ORDER.indexOf((severity || "").toUpperCase());
        return idx === -1 ? 99 : idx;
    }
    function normalizeSnapshotSeverity(severity, fallback) {
        const sev = (severity || "").toUpperCase();
        if (SEVERITY_ORDER.includes(sev)) return sev;
        return fallback || "LOW";
    }

    // ── Step 124: Build enriched card data for pipeline ──
    var allCards = tenants.map(function(t, i) {
        var s = t.results && t.results.summary ? t.results.summary : null;
        var provisions = t.results && t.results.provisions ? t.results.provisions : [];
        var deviations = getDeviationWorkflowProvisions(provisions, i);
        var highestSev = s ? getHighestSeverity(s) : null;
        highestSev = highestSev === "CONFORMS" ? null : normalizeSnapshotSeverity(highestSev, null);
        if (deviations.length > 0) {
            highestSev = deviations.reduce(function(best, p) {
                var nextSev = normalizeSnapshotSeverity(p.severity, null);
                if (!nextSev) return best;
                if (!best) return nextSev;
                return getSnapshotSeverityRank(nextSev) <= getSnapshotSeverityRank(best) ? nextSev : best;
            }, highestSev);
        }
        var sevScore = highestSev ? (getSnapshotSeverityRank(highestSev) + 1) : 99;
        var isClean = deviations.length === 0 && s;
        var resolution = getContractResolution(i);
        var name = formatTenantName(t.filename || "");
        var meta = t.results && t.results.contract_metadata ? t.results.contract_metadata : {};
        var tenantName = (meta.tenant_name || '').trim();
        var propertyDesc = (meta.property_description || '').trim();
        // Severity counts
        var sevCounts = {};
        deviations.forEach(function(d) { var sv = (d.severity || "MEDIUM").toUpperCase(); sevCounts[sv] = (sevCounts[sv] || 0) + 1; });
        return {
            t: t, i: i, s: s, provisions: provisions, deviations: deviations,
            highestSev: highestSev, sevScore: sevScore, isClean: isClean,
            resolution: resolution, name: name, tenantName: tenantName,
            propertyDesc: propertyDesc, sevCounts: sevCounts
        };
    });

    // ── Enrich cards with confidence signals ──
    allCards.forEach(function(c) {
        c.confSignals = new Set();
        c.sevSet = new Set();
        if (c.isClean) {
            c.sevSet.add('CLEAR');
        } else {
            Object.keys(c.sevCounts || {}).forEach(function(key) {
                if ((c.sevCounts[key] || 0) > 0) c.sevSet.add(normalizeSnapshotSeverity(key, null));
            });
            if (c.sevSet.size === 0) c.sevSet.add(normalizeSnapshotSeverity(c.highestSev, 'LOW'));
        }
        c.sevLabel = c.isClean ? 'CLEAR' : normalizeSnapshotSeverity(c.highestSev, 'LOW');
        c.deviations.forEach(function(p) {
            var sig = p.cam_score ? p.cam_score.governance_signal : '';
            if (sig) c.confSignals.add(sig);
        });
    });

    // ── Filter helpers ──
    function passesSev(c) {
        if (snapshotSeverityFilter.size === 0) return true;
        for (var sev of snapshotSeverityFilter) {
            if ((c.sevSet || new Set()).has(sev)) return true;
        }
        return false;
    }
    function passesConf(c) {
        if (snapshotConfidenceFilter.size === 0) return true;
        for (var sig of snapshotConfidenceFilter) { if (c.confSignals.has(sig)) return true; }
        return false;
    }
    function passesStatus(c) {
        if (snapshotStatusFilter === 'all') return true;
        if (snapshotStatusFilter === 'unreviewed') return c.resolution === 'unreviewed';
        if (snapshotStatusFilter === 'resolved') return c.resolution === 'resolved';
        if (snapshotStatusFilter === 'clear') return c.isClean;
        return true;
    }
    function passesContract(c) {
        if (snapshotContractFilter.size === 0) return true;
        return snapshotContractFilter.has(c.i);
    }
    function passesSearch(c) {
        if (!snapshotSearch) return true;
        var q = snapshotSearch.toLowerCase();
        return c.name.toLowerCase().indexOf(q) !== -1
            || c.tenantName.toLowerCase().indexOf(q) !== -1
            || c.propertyDesc.toLowerCase().indexOf(q) !== -1;
    }

    // ── Cascading available values (each computed with all OTHER filters applied) ──
    function hasSnapshotNarrowing() {
        return snapshotSeverityFilter.size > 0
            || snapshotConfidenceFilter.size > 0
            || snapshotStatusFilter !== 'all'
            || snapshotContractFilter.size > 0
            || !!snapshotSearch;
    }
    var _snapAvailSev = new Set();
    var _snapAvailConf = new Set();
    var _snapAvailStatus = new Set();
    var _useCascadingAvail = hasSnapshotNarrowing();
    allCards.forEach(function(c) {
        if (!_useCascadingAvail || (passesConf(c) && passesStatus(c) && passesContract(c) && passesSearch(c))) {
            (c.sevSet || new Set()).forEach(function(sev) { _snapAvailSev.add(sev); });
        }
        if (!_useCascadingAvail || (passesSev(c) && passesStatus(c) && passesContract(c) && passesSearch(c))) {
            c.confSignals.forEach(function(sig) { _snapAvailConf.add(sig); });
            if (c.isClean) _snapAvailConf.add('_CLEAR');
        }
        if (!_useCascadingAvail || (passesSev(c) && passesConf(c) && passesContract(c) && passesSearch(c))) {
            if (c.isClean) _snapAvailStatus.add('clear');
            if (c.resolution === 'unreviewed') _snapAvailStatus.add('unreviewed');
            if (c.resolution === 'resolved') _snapAvailStatus.add('resolved');
        }
    });

    // ── Auto-clear selections that are no longer available ──
    for (var s of [...snapshotSeverityFilter]) { if (!_snapAvailSev.has(s)) snapshotSeverityFilter.delete(s); }
    for (var c of [...snapshotConfidenceFilter]) { if (!_snapAvailConf.has(c)) snapshotConfidenceFilter.delete(c); }
    if (snapshotStatusFilter !== 'all' && !_snapAvailStatus.has(snapshotStatusFilter)) snapshotStatusFilter = 'all';

    // ── Apply all filters ──
    var filtered = allCards.filter(function(c) {
        return passesSev(c) && passesConf(c) && passesStatus(c) && passesContract(c) && passesSearch(c);
    });

    // ── Pipeline Step 5: Sort ──
    if (snapshotSort === 'risk') {
        filtered.sort(function(a, b) {
            if (a.isClean && !b.isClean) return 1;
            if (!a.isClean && b.isClean) return -1;
            if (a.sevScore !== b.sevScore) return a.sevScore - b.sevScore;
            // Tiebreak: most critical first, then high, then medium, then total
            var ac = a.sevCounts['CRITICAL'] || 0, bc = b.sevCounts['CRITICAL'] || 0;
            if (ac !== bc) return bc - ac;
            var ah = a.sevCounts['HIGH'] || 0, bh = b.sevCounts['HIGH'] || 0;
            if (ah !== bh) return bh - ah;
            var am = a.sevCounts['MEDIUM'] || 0, bm = b.sevCounts['MEDIUM'] || 0;
            if (am !== bm) return bm - am;
            return b.deviations.length - a.deviations.length;
        });
    } else if (snapshotSort === 'issues') {
        filtered.sort(function(a, b) { return b.deviations.length - a.deviations.length; });
    } else if (snapshotSort === 'name') {
        filtered.sort(function(a, b) { return a.name.localeCompare(b.name); });
    } else if (snapshotSort === 'unreviewed') {
        filtered.sort(function(a, b) {
            var aUn = a.resolution === 'unreviewed' ? 0 : 1;
            var bUn = b.resolution === 'unreviewed' ? 0 : 1;
            if (aUn !== bUn) return aUn - bUn;
            // Within same group, sort by risk
            if (a.isClean && !b.isClean) return 1;
            if (!a.isClean && b.isClean) return -1;
            return a.sevScore - b.sevScore;
        });
    }

    // ── Label helpers ──
    var _sevLabelMap = { CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low', CLEAR: 'Clear' };
    var _confLabelMap = { ASSERT_SIGNAL: 'Verified', ASSERT_REVIEW_SIGNAL: 'Impact Unclear', REVIEW_SIGNAL: 'Needs Review', WITHHOLD_SIGNAL: 'Inconclusive' };
    function _snapSevLabel() {
        if (snapshotSeverityFilter.size === 0) return 'All';
        if (snapshotSeverityFilter.size === 1) return _sevLabelMap[[...snapshotSeverityFilter][0]] || [...snapshotSeverityFilter][0];
        return snapshotSeverityFilter.size + ' selected';
    }
    function _snapConfLabel() {
        if (snapshotConfidenceFilter.size === 0) return 'All';
        if (snapshotConfidenceFilter.size === 1) return _confLabelMap[[...snapshotConfidenceFilter][0]] || [...snapshotConfidenceFilter][0];
        return snapshotConfidenceFilter.size + ' selected';
    }

    // ── Render toolbar into persistent bar (stays visible in contract detail too) ──
    var toolbarBar = document.getElementById('snapshot-toolbar-bar');
    if (toolbarBar) toolbarBar.classList.remove('hidden');
    var toolbarHtml = '<div class="snapshot-toolbar">'
        + '<select class="snapshot-toolbar-select" id="snapshot-sort-select">'
        + '<option value="risk"' + (snapshotSort === 'risk' ? ' selected' : '') + '>Sort: Risk</option>'
        + '<option value="issues"' + (snapshotSort === 'issues' ? ' selected' : '') + '>Sort: Most Issues</option>'
        + '<option value="name"' + (snapshotSort === 'name' ? ' selected' : '') + '>Sort: Name (A\u2013Z)</option>'
        + '<option value="unreviewed"' + (snapshotSort === 'unreviewed' ? ' selected' : '') + '>Sort: Unreviewed First</option>'
        + '</select>'
        + '<div class="filter-dropdown clause-filter-dropdown" id="snap-severity-dropdown">'
        + '<button class="btn btn-outline filter-dropdown-trigger clause-filter-trigger snap-filter-btn" id="snap-severity-trigger" type="button">'
        + 'Severity: <span id="snap-severity-label">' + _snapSevLabel() + '</span> &#9662;'
        + '</button>'
        + '<div class="filter-dropdown-panel clause-filter-panel hidden" id="snap-severity-panel">'
        + '<label class="filter-option filter-option-all"><input type="checkbox" id="snap-severity-all"' + (snapshotSeverityFilter.size === 0 ? ' checked' : '') + '><span>All Severities</span></label>'
        + (_snapAvailSev.has('CRITICAL') ? '<label class="filter-option"><input type="checkbox" value="CRITICAL" class="snap-sev-cb"' + (snapshotSeverityFilter.has('CRITICAL') ? ' checked' : '') + '><span>Critical</span></label>' : '')
        + (_snapAvailSev.has('HIGH') ? '<label class="filter-option"><input type="checkbox" value="HIGH" class="snap-sev-cb"' + (snapshotSeverityFilter.has('HIGH') ? ' checked' : '') + '><span>High</span></label>' : '')
        + (_snapAvailSev.has('MEDIUM') ? '<label class="filter-option"><input type="checkbox" value="MEDIUM" class="snap-sev-cb"' + (snapshotSeverityFilter.has('MEDIUM') ? ' checked' : '') + '><span>Medium</span></label>' : '')
        + (_snapAvailSev.has('LOW') ? '<label class="filter-option"><input type="checkbox" value="LOW" class="snap-sev-cb"' + (snapshotSeverityFilter.has('LOW') ? ' checked' : '') + '><span>Low</span></label>' : '')
        + (_snapAvailSev.has('CLEAR') ? '<label class="filter-option"><input type="checkbox" value="CLEAR" class="snap-sev-cb"' + (snapshotSeverityFilter.has('CLEAR') ? ' checked' : '') + '><span>Clear</span></label>' : '')
        + '</div></div>'
        + '<div class="filter-dropdown clause-filter-dropdown" id="snap-confidence-dropdown">'
        + '<button class="btn btn-outline filter-dropdown-trigger clause-filter-trigger snap-filter-btn" id="snap-confidence-trigger" type="button">'
        + 'Confidence: <span id="snap-confidence-label">' + _snapConfLabel() + '</span> &#9662;'
        + '</button>'
        + '<div class="filter-dropdown-panel clause-filter-panel hidden" id="snap-confidence-panel">'
        + '<label class="filter-option filter-option-all"><input type="checkbox" id="snap-confidence-all"' + (snapshotConfidenceFilter.size === 0 ? ' checked' : '') + '><span>All Confidence</span></label>'
        + (_snapAvailConf.has('ASSERT_SIGNAL') ? '<label class="filter-option"><input type="checkbox" value="ASSERT_SIGNAL" class="snap-conf-cb"' + (snapshotConfidenceFilter.has('ASSERT_SIGNAL') ? ' checked' : '') + '><span>Verified</span></label>' : '')
        + (_snapAvailConf.has('ASSERT_REVIEW_SIGNAL') ? '<label class="filter-option"><input type="checkbox" value="ASSERT_REVIEW_SIGNAL" class="snap-conf-cb"' + (snapshotConfidenceFilter.has('ASSERT_REVIEW_SIGNAL') ? ' checked' : '') + '><span>Impact Unclear</span></label>' : '')
        + (_snapAvailConf.has('REVIEW_SIGNAL') ? '<label class="filter-option"><input type="checkbox" value="REVIEW_SIGNAL" class="snap-conf-cb"' + (snapshotConfidenceFilter.has('REVIEW_SIGNAL') ? ' checked' : '') + '><span>Needs Review</span></label>' : '')
        + (_snapAvailConf.has('WITHHOLD_SIGNAL') ? '<label class="filter-option"><input type="checkbox" value="WITHHOLD_SIGNAL" class="snap-conf-cb"' + (snapshotConfidenceFilter.has('WITHHOLD_SIGNAL') ? ' checked' : '') + '><span>Inconclusive</span></label>' : '')
        + '</div></div>'
        + '<select class="snapshot-toolbar-select" id="snapshot-status-select">'
        + '<option value="all"' + (snapshotStatusFilter === 'all' ? ' selected' : '') + '>Status: All</option>'
        + (_snapAvailStatus.has('unreviewed') ? '<option value="unreviewed"' + (snapshotStatusFilter === 'unreviewed' ? ' selected' : '') + '>Unreviewed</option>' : '')
        + (_snapAvailStatus.has('resolved') ? '<option value="resolved"' + (snapshotStatusFilter === 'resolved' ? ' selected' : '') + '>Resolved</option>' : '')
        + (_snapAvailStatus.has('clear') ? '<option value="clear"' + (snapshotStatusFilter === 'clear' ? ' selected' : '') + '>Clear</option>' : '')
        + '</select>'
        + '<div class="snapshot-contract-filter-wrap" id="snapshot-contract-filter-wrap">'
        + '<button class="snapshot-toolbar-select snapshot-contract-filter-btn" id="snapshot-contract-filter-btn">'
        + (snapshotContractFilter.size === 0 ? 'Contracts: All' : 'Contracts: ' + snapshotContractFilter.size + ' selected')
        + '</button>'
        + '<div class="snapshot-contract-dropdown hidden" id="snapshot-contract-dropdown"></div>'
        + '</div>'
        + '<div class="snapshot-toolbar-search">'
        + '<span class="search-icon">\uD83D\uDD0D</span>'
        + '<input type="text" id="snapshot-search-input" placeholder="Search contracts..." value="' + esc(snapshotSearch) + '">'
        + '</div>'
        + '</div>';

    // Render toolbar into persistent bar (not into cards container)
    if (toolbarBar) toolbarBar.innerHTML = toolbarHtml;

    // ── Build cards HTML ──
    var html = '';

    if (filtered.length === 0) {
        html += '<div class="snapshot-no-results">No contracts match your search</div>';
    } else {
        html += '<div class="snapshot-grid">';
        filtered.forEach(function(c) {
            var t = c.t, i = c.i, s = c.s, deviations = c.deviations, highestSev = c.highestSev, isClean = c.isClean;
            var nameEsc = esc(c.name);
            var resolution = c.resolution;
            var provCount = c.provisions.length;

            var sTenantStr = c.tenantName || 'N/A';
            var sPropertyStr = c.propertyDesc || 'N/A';
            var sMetaLine = '<div class="snapshot-card-meta">'
                + 'Tenant: ' + esc(sTenantStr) + ' &middot; Property: ' + esc(sPropertyStr)
                + '</div>';

            var activeClass = (snapshotActiveIndex === i) ? ' contract-card-active' : '';

            // Step 125: Lease blurb
            var blurb125 = buildLeaseBlurb(t.results);
            var blurbLine = blurb125 ? '<div class="contract-card-blurb">' + esc(blurb125) + '</div>' : '';

            if (isClean) {
                html += '<div class="snapshot-card snapshot-card-clean' + activeClass + '" data-tenant="' + i + '">'
                    + '<div class="snapshot-card-header">'
                    + '<span class="snapshot-card-name">' + nameEsc + '</span>'
                    + '<div class="snapshot-card-badges"><span class="snapshot-resolution-badge res-badge-clean">\u2713 Clear</span></div>'
                    + '</div>'
                    + sMetaLine
                    + blurbLine
                    + '<div class="snapshot-card-body snapshot-card-body-clean">'
                    + 'All ' + provCount + ' provisions conform to reference lease'
                    + '</div>'
                    + '<div class="snapshot-card-footer">'
                    + '<button class="snapshot-open-btn" data-tenant="' + i + '">Open Contract \u2192</button>'
                    + '</div>'
                    + '</div>';
            } else if (!s) {
                var msg = t.status === "cancelled" ? "Cancelled" : (t.error && t.error.startsWith("GATE_ABORT:") ? "Not a commercial lease" : (t.error || "No results"));
                html += '<div class="snapshot-card snapshot-card-empty' + activeClass + '" data-tenant="' + i + '">'
                    + '<div class="snapshot-card-header">'
                    + '<span class="snapshot-card-name">' + nameEsc + '</span>'
                    + '<span class="snapshot-resolution-badge res-badge-empty">' + esc(msg) + '</span>'
                    + '</div></div>';
            } else {
                // Action-level badge
                var actionLabel, actionClass;
                if ((c.sevCounts['CRITICAL'] || 0) > 0)      { actionLabel = '\u26A0 Immediate Action'; actionClass = 'action-badge-critical'; }
                else if ((c.sevCounts['HIGH'] || 0) > 0)     { actionLabel = '\u26A0 Review Recommended'; actionClass = 'action-badge-high'; }
                else if (deviations.length > 0)              { actionLabel = '\u00B7 Monitor'; actionClass = 'action-badge-medium'; }
                else                                          { actionLabel = '\u2713 Clear'; actionClass = 'action-badge-clear'; }

                var statusBadge;
                if (resolution === "resolved") {
                    statusBadge = '<span class="snapshot-resolution-badge res-badge-resolved">\u2713 Resolved</span>';
                } else {
                    statusBadge = '<span class="snapshot-resolution-badge res-badge-unreviewed">\u26A0 Unreviewed</span>';
                }

                // Severity-colored provision chips — clickable, jump to provision in contract detail
                var chipRow = '<div class="overview-chip-row">';
                var sortedDevs = deviations.slice().sort(function(a, b) {
                    return (SEVERITY_ORDER.indexOf(a.severity) || 99) - (SEVERITY_ORDER.indexOf(b.severity) || 99);
                });
                sortedDevs.forEach(function(d) {
                    var pid = d.provision_id || '';
                    var shortName = (d.provision_name || '').replace(/^LP-\d{2}\s*/, '').replace(/^CUSTOM-\d{2}\s*/, '');
                    var label = shortName ? pid + ' ' + shortName : pid;
                    var chipSev = (d.severity || 'MEDIUM').toLowerCase();
                    var chipTitle = d.risk_headline ? esc(d.risk_headline) : 'Jump to ' + esc(pid);
                    chipRow += '<span class="overview-chip overview-chip-' + chipSev + ' chip-jumpable" data-tenant="' + i + '" data-pid="' + esc(pid) + '" title="' + chipTitle + '">' + esc(label) + '</span>';
                });
                chipRow += '</div>';

                // Coverage gap chips (missing / covered_unfavorable from coverage_assessment)
                var covCa = (c.t.results && c.t.results.coverage_assessment) || [];
                var gapItems = covCa.filter(function(a) {
                    return a.coverage_state === 'missing' || a.coverage_state === 'covered_unfavorable';
                }).slice(0, 4);
                var gapChipRow = '';
                if (gapItems.length > 0) {
                    gapChipRow = '<div class="overview-chip-row overview-gap-chip-row">';
                    gapItems.forEach(function(a) {
                        var gpid = a.issue_area_id || '';
                        var gshort = (a.issue_area_name || gpid).replace(/^LP-\d{2}\s*/, '');
                        var glabel = gpid + (gshort ? ' ' + gshort : '');
                        var gtitle = (a.exposure_statement || 'Coverage gap: ' + gpid).replace(/"/g, '&quot;');
                        gapChipRow += '<span class="overview-chip overview-chip-gap chip-jumpable-modec" data-tenant="' + i + '" data-pid="' + esc(gpid) + '" title="' + esc(gtitle) + '">' + esc(glabel) + '</span>';
                    });
                    var gapRemainder = covCa.filter(function(a) {
                        return a.coverage_state === 'missing' || a.coverage_state === 'covered_unfavorable';
                    }).length - gapItems.length;
                    if (gapRemainder > 0) {
                        gapChipRow += '<span class="overview-chip overview-chip-gap-overflow">+' + gapRemainder + ' more gaps</span>';
                    }
                    gapChipRow += '</div>';
                }

                // Conforming provisions \u2014 collapsed count row
                var conformingProvs = c.provisions.filter(function(p) {
                    return p.final_verdict === 'CONFORMS' && p.provision_id !== 'LP-00' && !p.absent_from_both;
                });
                var conformingHtml = '';
                if (conformingProvs.length > 0) {
                    var conformChips = conformingProvs.map(function(p) {
                        return '<span class="overview-chip overview-chip-conforming chip-jumpable"'
                            + ' data-tenant="' + i + '" data-pid="' + esc(p.provision_id) + '"'
                            + ' title="' + esc(p.provision_name || p.provision_id) + '">'
                            + esc(p.provision_id) + '</span>';
                    }).join('');
                    conformingHtml = '<div class="conforming-chip-row" data-tenant="' + i + '">'
                        + '<button class="conforming-count-badge" onclick="window.CAM._toggleConformingChips(this, event)">'
                        + '\u2713 ' + conformingProvs.length + ' conforming'
                        + '</button>'
                        + '<div class="conforming-chips hidden">' + conformChips + '</div>'
                        + '</div>';
                }

                html += '<div class="snapshot-card snapshot-card-findings' + activeClass + '" data-tenant="' + i + '">'
                    + '<div class="snapshot-card-header">'
                    + '<span class="snapshot-card-name">' + nameEsc + '</span>'
                    + '<div class="snapshot-card-badges">'
                    + '<span class="snapshot-action-badge ' + actionClass + '">' + actionLabel + '</span>'
                    + statusBadge
                    + '</div>'
                    + '</div>'
                    + sMetaLine
                    + blurbLine
                    + chipRow
                    + gapChipRow
                    + conformingHtml
                    + '<div class="snapshot-card-footer">'
                    + '<button class="snapshot-open-btn" data-tenant="' + i + '">Open Contract \u2192</button>'
                    + '</div>'
                    + '</div>';
            }
        });
        html += '</div>';
    }

    container.innerHTML = html;

    // ── Wire toolbar controls ──
    var sortSel = document.getElementById('snapshot-sort-select');
    if (sortSel) sortSel.addEventListener('change', function() {
        snapshotSort = sortSel.value;
        renderRunSnapshot();
    });
    // Close all snapshot filter dropdowns except the specified one
    function closeSnapDropdowns(except) {
        ['snap-severity-panel', 'snap-confidence-panel', 'snapshot-contract-dropdown'].forEach(function(id) {
            if (id !== except) {
                var el = document.getElementById(id);
                if (el) el.classList.add('hidden');
            }
        });
    }

    // Severity multi-select dropdown
    var _snapSevTrigger = document.getElementById('snap-severity-trigger');
    if (_snapSevTrigger) _snapSevTrigger.addEventListener('click', function() {
        closeSnapDropdowns('snap-severity-panel');
        var panel = document.getElementById('snap-severity-panel');
        if (panel) {
            panel.classList.toggle('hidden');
            if (!panel.classList.contains('hidden')) {
                var rect = _snapSevTrigger.getBoundingClientRect();
                panel.style.top = (rect.bottom + 2) + 'px';
                panel.style.left = rect.left + 'px';
            }
        }
    });
    var _snapSevAll = document.getElementById('snap-severity-all');
    if (_snapSevAll) _snapSevAll.addEventListener('change', function() {
        if (this.checked) {
            snapshotSeverityFilter.clear();
            document.querySelectorAll('.snap-sev-cb').forEach(function(cb) { cb.checked = false; });
        }
        renderRunSnapshot();
    });
    document.querySelectorAll('.snap-sev-cb').forEach(function(cb) {
        cb.addEventListener('change', function() {
            if (this.checked) snapshotSeverityFilter.add(this.value);
            else snapshotSeverityFilter.delete(this.value);
            var allCb = document.getElementById('snap-severity-all');
            if (allCb) allCb.checked = snapshotSeverityFilter.size === 0;
            renderRunSnapshot();
        });
    });

    // Confidence multi-select dropdown
    var _snapConfTrigger = document.getElementById('snap-confidence-trigger');
    if (_snapConfTrigger) _snapConfTrigger.addEventListener('click', function() {
        closeSnapDropdowns('snap-confidence-panel');
        var panel = document.getElementById('snap-confidence-panel');
        if (panel) {
            panel.classList.toggle('hidden');
            if (!panel.classList.contains('hidden')) {
                var rect = _snapConfTrigger.getBoundingClientRect();
                panel.style.top = (rect.bottom + 2) + 'px';
                panel.style.left = rect.left + 'px';
            }
        }
    });
    var _snapConfAll = document.getElementById('snap-confidence-all');
    if (_snapConfAll) _snapConfAll.addEventListener('change', function() {
        if (this.checked) {
            snapshotConfidenceFilter.clear();
            document.querySelectorAll('.snap-conf-cb').forEach(function(cb) { cb.checked = false; });
        }
        renderRunSnapshot();
    });
    document.querySelectorAll('.snap-conf-cb').forEach(function(cb) {
        cb.addEventListener('change', function() {
            if (this.checked) snapshotConfidenceFilter.add(this.value);
            else snapshotConfidenceFilter.delete(this.value);
            var allCb = document.getElementById('snap-confidence-all');
            if (allCb) allCb.checked = snapshotConfidenceFilter.size === 0;
            renderRunSnapshot();
        });
    });
    var statusSel = document.getElementById('snapshot-status-select');
    if (statusSel) statusSel.addEventListener('change', function() {
        snapshotStatusFilter = statusSel.value;
        renderRunSnapshot();
    });
    var searchInput = document.getElementById('snapshot-search-input');
    if (searchInput) {
        var debounceTimer = null;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                snapshotSearch = searchInput.value;
                renderRunSnapshot();
                // Restore focus + cursor position after re-render
                var inp = document.getElementById('snapshot-search-input');
                if (inp) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
            }, 150);
        });
    }

    // ── Step 130: Contract name filter dropdown ──
    buildContractFilterDropdown();

    // Wire "Open Contract →" buttons
    container.querySelectorAll('.snapshot-open-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var idx = parseInt(btn.dataset.tenant, 10);
            openContractDetail(idx);
        });
    });

    // Wire chip clicks → open Contract Detail + jump to provision in findings
    container.querySelectorAll('.chip-jumpable[data-pid]').forEach(function(chip) {
        chip.addEventListener('click', async function(e) {
            e.stopPropagation();
            var idx = parseInt(chip.dataset.tenant, 10);
            var pid = chip.dataset.pid;
            await openContractDetail(idx);
            switchResultsTab('findings');
            await waitForResultsTarget(() =>
                document.getElementById('dev-' + pid) ||
                document.querySelector('[data-pid="' + CSS.escape(pid) + '"]')
            );
            jumpToFinding(pid);
        });
    });

    // Wire coverage gap chips → open Contract Detail + jump to Coverage & Gaps tab
    container.querySelectorAll('.chip-jumpable-modec[data-pid]').forEach(function(chip) {
        chip.addEventListener('click', async function(e) {
            e.stopPropagation();
            var idx = parseInt(chip.dataset.tenant, 10);
            var pid = chip.dataset.pid;
            await openContractDetail(idx);
            if (typeof jumpToCoverageProvision === 'function') {
                jumpToCoverageProvision(pid);
            }
        });
    });
}

// ── Contract Detail ──

async function openContractDetail(tenantIdx) {
    const renderSeq = ++contractDetailRenderSeq;
    contractDetailOpen = true;
    contractDetailIdx = tenantIdx;
    currentTenantIndex = tenantIdx;
    snapshotActiveIndex = tenantIdx;   // Step 120: remember for tab switch
    syncChatScopeToCurrentTenant(true);

    // Hide overview + contracts tab, show detail
    var overview     = document.getElementById('overview-tab-content');
    var contractsTab = document.getElementById('contracts-tab-content');
    var detail       = document.getElementById('contract-detail-view');
    if (overview)     overview.classList.add('hidden');
    if (contractsTab) contractsTab.classList.add('hidden');
    if (detail)       detail.classList.remove('hidden');
    setResultsContentDetailMode(true);

    // Hide the no-contract placeholder if it was showing
    var ncp = document.getElementById('no-contract-placeholder');
    if (ncp) ncp.classList.add('hidden');

    // Deactivate top-level tabs; subheader will be set by the active results tab
    document.querySelectorAll("#top-tab-bar .top-tab[data-top-tab]").forEach(function(t) {
        t.classList.remove("active");
    });

    // Render header
    var tenant = currentResults.tenants[tenantIdx];
    updateContractDetailHeader(tenantIdx);

    // Step 129: Contract selector dropdown + clause filters
    renderContractSelectorBar(tenantIdx);

    // Step 129: Hide toolbar bar when in contract detail
    var tb = document.getElementById('snapshot-toolbar-bar');
    if (tb) tb.classList.add('hidden');

    // Set docview tenant selector
    var dts = document.getElementById("docview-tenant-select");
    if (dts) dts.value = tenantIdx;

    // Set hidden tenant selector
    var ts = document.getElementById("tenant-select");
    if (ts) ts.value = tenantIdx;

    const desiredResultsTab = activeResultsTab || "findings";
    contractDetailRenderPromise = Promise.resolve(contractDetailRenderPromise).catch(() => {}).then(async () => {
        if (renderSeq !== contractDetailRenderSeq) return;
        await renderTenantResults();

        // Bail if another tenant was opened while this one was rendering.
        if (!contractDetailOpen || currentTenantIndex !== tenantIdx || renderSeq !== contractDetailRenderSeq) return;

        renderContractResolutionControls(tenantIdx);
        switchResultsTab(desiredResultsTab);
        persistResultsViewState();
        updateNavActive(tenantIdx);
        const resultsPane = document.getElementById('results-content') || document.querySelector('.results-content');
        if (resultsPane) resultsPane.scrollTo({ top: 0, behavior: 'instant' });
    });

    await contractDetailRenderPromise;
}

function closeContractDetail() {
    contractDetailOpen = false;
    contractDetailIdx = -1;
    snapshotActiveIndex = null;  // Step 122: back button clears memory
    var overview     = document.getElementById('overview-tab-content');
    var contractsTab = document.getElementById('contracts-tab-content');
    var detail       = document.getElementById('contract-detail-view');
    if (detail) detail.classList.add('hidden');
    setResultsContentDetailMode(false);
    persistResultsViewState();

    // Return to whichever top tab was active before opening detail
    var returnTab = (activeTopTab === 'contracts') ? 'contracts' : 'overview';
    if (returnTab === 'contracts') {
        if (contractsTab) contractsTab.classList.remove('hidden');
        if (overview)     overview.classList.add('hidden');
    } else {
        if (overview)     overview.classList.remove('hidden');
        if (contractsTab) contractsTab.classList.add('hidden');
    }

    // Hide the no-contract placeholder if it was showing
    var ncp = document.getElementById('no-contract-placeholder');
    if (ncp) ncp.classList.add('hidden');

    // Step 129: Hide contract selector dropdown
    var selectorBar = document.getElementById('contract-selector-bar');
    if (selectorBar) selectorBar.classList.add('hidden');

    // Re-activate the correct top-tab
    document.querySelectorAll('#top-tab-bar .top-tab[data-top-tab]').forEach(function(t) {
        t.classList.toggle('active', t.dataset.topTab === returnTab);
    });

    // Hide per-tenant checklist — it belongs inside contract detail, not run overview
    var checklist = document.getElementById('provisions-checklist');
    if (checklist) checklist.classList.add('hidden');
    var legend = document.getElementById('results-legend');
    if (legend) legend.classList.add('hidden');

    renderRunSnapshot();
}

// ── Section collapse/expand ──
var sectionCollapsed = { 'run-summary': false, 'contracts': false };

function toggleSection(name) {
    sectionCollapsed[name] = !sectionCollapsed[name];
    var collapsed = sectionCollapsed[name];

    var icon = document.getElementById(name + '-toggle-icon');
    if (icon) icon.textContent = collapsed ? '\u25b8' : '\u25be';

    if (name === 'run-summary') {
        var ids = ['deal-brief-banner', 'deal-overview-panel', 'ai-summary-bar',
                   'provision-heatmap-panel',
                   'provisions-checklist', 'results-legend', 'filter-bar',
                   'provisions-scope-card', 'contract-status-panel', 'review-completion-banner'];
        ids.forEach(function(id) {
            var el = document.getElementById(id);
            // only touch elements that are currently visible (not already hidden for other reasons)
            if (el && !el.classList.contains('section-user-hidden') && collapsed) {
                el.dataset.sectionHidden = '1';
                el.classList.add('hidden');
            } else if (el && el.dataset.sectionHidden === '1' && !collapsed) {
                delete el.dataset.sectionHidden;
                el.classList.remove('hidden');
            }
        });
    } else if (name === 'contracts') {
        var ids2 = ['snapshot-toolbar-bar', 'snapshot-tab-content'];
        ids2.forEach(function(id) {
            var el = document.getElementById(id);
            if (el && collapsed) {
                el.dataset.sectionHidden = '1';
                el.classList.add('hidden');
            } else if (el && el.dataset.sectionHidden === '1' && !collapsed) {
                delete el.dataset.sectionHidden;
                el.classList.remove('hidden');
            }
        });
    }
}

function renderContractResolutionControls(tenantIdx) {
    return;
}

// ══════════════════════════════════════════════════════
// HELP CHAT (upload page) (086)
// ══════════════════════════════════════════════════════

function initHelpChat() {
    if (helpChatInitialized) return;
    const panel = $("#help-chat-panel");
    const sendBtn = $("#help-chat-send-btn");
    const input = $("#help-chat-input");
    if (!panel) return;
    helpChatInitialized = true;

    sendBtn.addEventListener("click", () => sendHelpChatMessage());
    input.addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendHelpChatMessage();
        }
    });

    renderHelpChatWelcome();
}

function renderHelpChatWelcome() {
    const messagesEl = $("#help-chat-messages");
    if (!messagesEl) return;
    messagesEl.innerHTML = "";

    const starters = [
        "What does CAM do with these leases?",
        "What do I need before I click Review Leases?",
        "What's the difference between comparison and analysis mode?",
        "Ask any lease-related question...",
    ];

    const welcome = document.createElement("div");
    welcome.className = "help-chat-welcome";
    welcome.innerHTML = "Use chat to understand what CAM will analyze, what to upload, and what to do before you run the review." +
        '<div class="help-chat-starters">' +
        starters.map(s => {
            if (s.endsWith("...")) {
                return `<span class="help-chat-hint">${esc(s)}</span>`;
            }
            return `<button class="help-chat-starter" onclick="window.CAM.askHelpQuestion(this.textContent)">${esc(s)}</button>`;
        }).join("") + '</div>';
    messagesEl.appendChild(welcome);
}

function refreshHelpChatStarters() {
    const messagesEl = $("#help-chat-messages");
    if (!messagesEl) return;
    const welcome = messagesEl.querySelector(".help-chat-welcome");
    if (!welcome) return;

    const starters = [
        "What does CAM do with these leases?",
        "What do I need before I click Review Leases?",
        "What's the difference between comparison and analysis mode?",
    ];

    starters.push("Ask any lease-related question...");

    welcome.innerHTML = "Use chat to understand what CAM will analyze, what to upload, and what to do before you run the review." +
        '<div class="help-chat-starters">' +
        starters.map(s => {
            if (s.endsWith("...")) {
                return `<span class="help-chat-hint">${esc(s)}</span>`;
            }
            return `<button class="help-chat-starter" onclick="window.CAM.askHelpQuestion(this.textContent)">${esc(s)}</button>`;
        }).join("") + '</div>';
}

function gatherUploadContext() {
    const ctx = {};

    // Selected provision IDs
    const selected = [];
    document.querySelectorAll("#provision-list input[type=checkbox]:checked").forEach(cb => {
        selected.push(cb.value);
    });
    if (selected.length > 0) {
        ctx.selected_provisions = selected;
        ctx.selected_review_areas = selected;
    }

    // Uploaded filenames
    const files = [];
    document.querySelectorAll("#template-file-list .file-name, #tenant-file-list .file-name").forEach(el => {
        files.push(el.textContent.trim());
    });
    if (files.length > 0) ctx.uploaded_files = files;

    // Custom provisions
    const customs = customProvisions.map(cp => cp.name || cp.id);
    if (customs.length > 0) {
        ctx.custom_provisions = customs;
        ctx.custom_review_areas = customs;
    }

    // (Prescan results removed in step 112 — discovery moved into pipeline)

    return ctx;
}

function getResultsChatUIViewMap() {
    // Step 259: Mode C has no template, so findings/docview don't render and
    // shouldn't appear as available views to the chat backend. Coverage & Gaps
    // is the primary contract view.
    if (typeof isJobModeC === 'function' && isJobModeC()) {
        return [
            { id: "overview", label: "Run Synopsis", purpose: "Portfolio-level coverage snapshot across all analyzed leases" },
            { id: "contracts", label: "Leases", purpose: "Lease cards with coverage tier and entry point" },
            { id: "coverage", label: "Coverage & Gaps", purpose: "Per-issue-area coverage status, exposure statements, and gap analysis" },
            { id: "audittrail", label: "CAM Audit Trail", purpose: "Per-clause extraction confidence and analysis trace" }
        ];
    }
    return [
        { id: "overview", label: "Run Synopsis", purpose: "Portfolio-level summary across all analyzed leases" },
        { id: "contracts", label: "Contracts", purpose: "Contract cards and contract-level entry point" },
        { id: "findings", label: "Contract Summary", purpose: "Deviations, conforming provisions, and contract summary" },
        { id: "docview", label: "Document Comparison", purpose: "Reference and tenant text in context" },
        { id: "audittrail", label: "CAM Audit Trail", purpose: "Reviewer reasoning, challenge review, confidence, and scoring trace" }
    ];
}

function buildResultsChatUIContext() {
    const currentContract = currentResults && currentResults.tenants && currentResults.tenants[currentTenantIndex];
    const currentContractLabel = currentContract
        ? (formatTenantName(currentContract.filename) || currentContract.filename || `Contract ${currentTenantIndex + 1}`)
        : "";
    const topTabId = activeTopTab === "contracts" ? "contracts" : "overview";
    const topTabLabel = topTabId === "contracts" ? "Contracts" : "Run Synopsis";
    const resultsTabLabels = {
        findings: "Contract Summary",
        docview: "Document Comparison",
        audittrail: "CAM Audit Trail"
    };
    const scopedTenantIdx = chatScopeTenantIdx !== "" ? parseInt(chatScopeTenantIdx, 10) : null;
    const scopedContract = scopedTenantIdx != null && currentResults && currentResults.tenants
        ? currentResults.tenants[scopedTenantIdx]
        : null;
    const scopedContractLabel = scopedContract
        ? (formatTenantName(scopedContract.filename) || scopedContract.filename || `Contract ${scopedTenantIdx + 1}`)
        : "";
    const scopedProvisionLabel = (() => {
        if (!chatScopeProvisionId) return "";
        const tenantIdx = scopedTenantIdx != null ? scopedTenantIdx : currentTenantIndex;
        const tenant = currentResults && currentResults.tenants && currentResults.tenants[tenantIdx];
        const provisions = tenant && tenant.results && tenant.results.provisions ? tenant.results.provisions : [];
        const match = provisions.find(p => p.provision_id === chatScopeProvisionId);
        return match ? `${match.provision_id} ${match.provision_name || ""}`.trim() : chatScopeProvisionId;
    })();

    return {
        screen: "results",
        // Step 259: surface job mode so the chat backend can adapt prompting/framing.
        // "analyze" = Mode C (single-doc coverage), "compare" = Mode A (template diff).
        mode: (typeof isJobModeC === 'function' && isJobModeC()) ? "analyze" : "compare",
        // Step 261: surface perspective so the chat backend can adapt its framing
        // (tenant / landlord / neutral). Older jobs without this field send null,
        // which the backend treats as "perspective not specified."
        perspective: getJobPerspective(),
        active_top_tab: { id: topTabId, label: topTabLabel },
        active_results_tab: activeResultsTab ? {
            id: activeResultsTab,
            label: resultsTabLabels[activeResultsTab] || activeResultsTab
        } : null,
        contract_detail_open: !!contractDetailOpen,
        current_contract: currentContract ? {
            tenant_idx: currentTenantIndex,
            label: currentContractLabel
        } : null,
        chat_scope: {
            contract_label: scopedContractLabel,
            provision_label: scopedProvisionLabel
        },
        available_views: getResultsChatUIViewMap()
    };
}

function buildGeneralChatUIContext(screen) {
    if (screen === "processing") {
        const tenants = (currentJobData && currentJobData.input_config && currentJobData.input_config.tenants) || [];
        const inputCfg = (currentJobData && currentJobData.input_config) || {};
        const completedContractCount = tenants.filter(t => t && t.status === "completed").length;
        return {
            screen: "processing",
            mode: inputCfg.mode || "",
            perspective: inputCfg.perspective || null,
            job_status: (currentJobData && currentJobData.status) || "",
            completed_contract_count: completedContractCount,
            remaining_contract_count: Math.max(0, tenants.length - completedContractCount),
            available_views: [
                { id: "upload", label: "Upload" },
                { id: "processing", label: "Processing" },
                { id: "results", label: "Results" }
            ]
        };
    }

    const mode = getSelectedMode();
    const perspective = getSelectedPerspective();
    const modeChosen = modeExplicitlySelected;
    const selectedReviewAreaCount = document.querySelectorAll("#provision-list input[type=checkbox]:checked").length;
    const hasTemplate = !!templateFile;
    const hasTemplateSummary = !!templateSummary;
    const hasTenants = tenantFiles.length > 0;
    const reviewAreasReady = addMoreMode === "addmore"
        || (mode === "analyze" && perspective !== null && hasTenants)
        || (mode !== "analyze" && hasTemplateSummary && hasTenants);
    const missingRequirements = [];
    let nextStep = "";

    if (!modeChosen) {
        missingRequirements.push("choose whether to compare to a reference or analyze a single document");
        nextStep = "choose_mode";
    } else if (mode === "analyze") {
        if (!perspective) {
            missingRequirements.push("choose a review perspective");
            nextStep = "choose_perspective";
        }
        if (!hasTenants) {
            missingRequirements.push("upload at least one lease to analyze");
            if (!nextStep) nextStep = "upload_lease";
        }
    } else {
        if (!hasTemplate) {
            missingRequirements.push("upload a reference lease");
            nextStep = "upload_reference_lease";
        } else if (!hasTemplateSummary) {
            missingRequirements.push("wait for CAM to finish reading the reference lease");
            nextStep = "wait_for_reference_lease";
        }
        if (!hasTenants) {
            missingRequirements.push("upload at least one tenant lease");
            if (!nextStep) nextStep = "upload_tenant_lease";
        }
    }

    if (selectedReviewAreaCount === 0) {
        missingRequirements.push("select at least one review area");
        if (!nextStep) nextStep = "select_review_area";
    }

    if (!nextStep) {
        nextStep = !(($("#analyze-btn") || {}).disabled)
            ? "click_review_leases"
            : "check_email_or_required_fields";
    }

    return {
        screen: "upload",
        mode,
        mode_explicitly_selected: modeChosen,
        perspective,
        template_loaded: !!templateFile,
        reference_ready: !!templateSummary,
        tenant_count: tenantFiles.length,
        selected_review_area_count: selectedReviewAreaCount,
        review_areas_ready: reviewAreasReady,
        missing_requirements: missingRequirements,
        next_step: nextStep,
        analyze_enabled: !(($("#analyze-btn") || {}).disabled),
        available_views: [
            { id: "upload", label: "Upload" },
            { id: "processing", label: "Processing" },
            { id: "results", label: "Results" }
        ]
    };
}

async function sendHelpChatMessage() {
    const input = $("#help-chat-input");
    const messagesEl = $("#help-chat-messages");
    if (!input || !messagesEl) return;

    const question = input.value.trim();
    if (!question) return;

    // Show user message
    const userMsg = document.createElement("div");
    userMsg.className = "chat-msg chat-msg-user";
    userMsg.textContent = question;
    messagesEl.appendChild(userMsg);
    input.value = "";

    // Scroll page so the chat is visible
    messagesEl.closest(".help-chat-panel, .processing-chat-panel")
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Show typing indicator
    const typing = document.createElement("div");
    typing.className = "chat-typing";
    typing.textContent = "Thinking\u2026";
    messagesEl.appendChild(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const context = gatherUploadContext();
        const resp = await fetch("/api/chat/general", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                context,
                ui_context: buildGeneralChatUIContext("upload"),
                history: helpChatHistory.slice(-10),
            }),
        });

        typing.remove();

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Chat failed");
        }

        const data = await resp.json();

        const aiMsg = document.createElement("div");
        aiMsg.className = "chat-msg chat-msg-ai";
        aiMsg.innerHTML = formatChatResponse(data.response || "");
        appendSuggestedFollowups(
            aiMsg,
            data.suggested_followups || [],
            "askHelpQuestion",
            "help-chat-starters",
            "help-chat-starter"
        );
        messagesEl.appendChild(aiMsg);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        helpChatHistory.push({ role: "user", content: question });
        helpChatHistory.push({ role: "assistant", content: data.response || "" });

    } catch (err) {
        typing.remove();
        const errMsg = document.createElement("div");
        errMsg.className = "chat-msg chat-msg-ai";
        errMsg.textContent = "Sorry, something went wrong. Please try again.";
        messagesEl.appendChild(errMsg);
        console.error("Help chat error:", err);
    }
}

function askHelpQuestion(question) {
    const input = $("#help-chat-input");
    if (input) {
        input.value = question;
        sendHelpChatMessage();
    }
}

// ── Expose to global scope ──
// ══════════════════════════════════════════════════════
// Processing Email Capture (099)
// ══════════════════════════════════════════════════════

function maybeShowEmailCapture(emailArg) {
    const card = document.getElementById('processing-email-capture');
    if (!card) return;
    // If global jobEmail is already set, syncEmailState handles the card
    if (jobEmail) return;
    if (!emailArg) {
        card.classList.remove('hidden');
    } else {
        card.classList.add('hidden');
    }
}

async function submitProcessingEmail() {
    const input = document.getElementById('processing-email-input');
    const confirm = document.getElementById('processing-email-confirm');
    const mismatch = document.getElementById('processing-email-mismatch');
    const status = document.getElementById('processing-email-status');
    const btn = document.getElementById('processing-email-btn');
    if (!input || !currentJobId) return;

    const email = input.value.trim();
    const confirmEmail = confirm ? confirm.value.trim() : email;

    if (!email || !email.includes('@')) {
        showProcessingEmailStatus('Please enter a valid email address.', 'error');
        return;
    }
    if (email !== confirmEmail) {
        if (mismatch) mismatch.classList.remove('hidden');
        return;
    }
    if (mismatch) mismatch.classList.add('hidden');

    btn.disabled = true;
    try {
        const resp = await fetch(`/api/jobs/${currentJobId}/email`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email })
        });
        if (resp.ok) {
            setJobEmail(email);
        } else {
            showProcessingEmailStatus('Something went wrong. Please try again.', 'error');
            btn.disabled = false;
        }
    } catch (e) {
        showProcessingEmailStatus('Connection error. Please try again.', 'error');
        btn.disabled = false;
    }
}

function showProcessingEmailStatus(msg, type) {
    const el = document.getElementById('processing-email-status');
    if (!el) return;
    el.textContent = msg;
    el.className = `processing-email-status ${type}`;
    el.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════
// Educational Carousel (099)
// ══════════════════════════════════════════════════════

let _carouselIndex = 0;
let _carouselTotal = 0;
let _carouselTimer = null;

function initCarousel() {
    const track = document.getElementById('cam-carousel-track');
    const dotsContainer = document.getElementById('cam-carousel-dots');
    if (!track || !dotsContainer) return;

    const slides = track.querySelectorAll('.cam-slide');
    _carouselTotal = slides.length;
    _carouselIndex = 0;

    // Build dots
    dotsContainer.innerHTML = '';
    for (let i = 0; i < _carouselTotal; i++) {
        const dot = document.createElement('span');
        dot.className = 'cam-carousel-dot' + (i === 0 ? ' active' : '');
        dot.onclick = () => carouselGoTo(i);
        dotsContainer.appendChild(dot);
    }

    carouselGoTo(0);
    _startCarouselTimer();
}

function _startCarouselTimer() {
    if (_carouselTimer) clearInterval(_carouselTimer);
    _carouselTimer = setInterval(() => {
        carouselGoTo((_carouselIndex + 1) % _carouselTotal);
    }, 14000);
}

function carouselGoTo(idx) {
    _carouselIndex = idx;
    const track = document.getElementById('cam-carousel-track');
    const dotsContainer = document.getElementById('cam-carousel-dots');
    if (!track) return;
    track.style.transform = `translateX(-${idx * 100}%)`;
    if (dotsContainer) {
        dotsContainer.querySelectorAll('.cam-carousel-dot').forEach((d, i) => {
            d.classList.toggle('active', i === idx);
        });
    }
}

function carouselNext() {
    carouselGoTo((_carouselIndex + 1) % _carouselTotal);
    _startCarouselTimer(); // reset auto-advance on manual nav
}

function carouselPrev() {
    carouselGoTo((_carouselIndex - 1 + _carouselTotal) % _carouselTotal);
    _startCarouselTimer();
}

function stopCarousel() {
    if (_carouselTimer) {
        clearInterval(_carouselTimer);
        _carouselTimer = null;
    }
}

// ══════════════════════════════════════════════════════
// Processing Chat (while-you-wait)
// ══════════════════════════════════════════════════════

function initProcessingChat() {
    if (processingChatInitialized) return;
    const panel = $("#processing-chat-panel");
    const sendBtn = $("#processing-chat-send-btn");
    const input = $("#processing-chat-input");
    if (!panel) return;
    processingChatInitialized = true;

    sendBtn.addEventListener("click", () => sendProcessingChatMessage());
    input.addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendProcessingChatMessage();
        }
    });

    renderProcessingChatWelcome();
}

function renderProcessingChatWelcome() {
    const messagesEl = $("#processing-chat-messages");
    if (!messagesEl) return;
    messagesEl.innerHTML = "";

    const starters = [
        "What is CAM doing right now?",
        "What should I expect when results are ready?",
        "Can I review anything yet?",
        "Ask anything about leases...",
    ];

    const welcome = document.createElement("div");
    welcome.className = "processing-chat-welcome";
    welcome.innerHTML = "Use chat to understand what CAM is doing now, what will appear in results, and what to review next." +
        '<div class="processing-chat-starters">' +
        starters.map(s => {
            if (s.endsWith("...")) {
                return `<span class="help-chat-hint">${esc(s)}</span>`;
            }
            return `<button class="processing-chat-starter" onclick="window.CAM.askProcessingQuestion(this.textContent)">${esc(s)}</button>`;
        }).join("") + '</div>';
    messagesEl.appendChild(welcome);
}

async function sendProcessingChatMessage() {
    const input = $("#processing-chat-input");
    const messagesEl = $("#processing-chat-messages");
    if (!input || !messagesEl) return;

    const question = input.value.trim();
    if (!question) return;

    // Show user message
    const userMsg = document.createElement("div");
    userMsg.className = "chat-msg chat-msg-user";
    userMsg.textContent = question;
    messagesEl.appendChild(userMsg);
    input.value = "";

    // Scroll page so the chat is visible
    messagesEl.closest(".help-chat-panel, .processing-chat-panel")
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Show typing indicator
    const typing = document.createElement("div");
    typing.className = "chat-typing";
    typing.textContent = "Thinking\u2026";
    messagesEl.appendChild(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const resp = await fetch("/api/chat/general", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question,
                context: { phase: "processing", job_id: currentJobId || "" },
                ui_context: buildGeneralChatUIContext("processing"),
                history: processingChatHistory.slice(-10),
            }),
        });

        typing.remove();

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Chat failed");
        }

        const data = await resp.json();

        const aiMsg = document.createElement("div");
        aiMsg.className = "chat-msg chat-msg-ai";
        aiMsg.innerHTML = formatChatResponse(data.response || "");
        appendSuggestedFollowups(
            aiMsg,
            data.suggested_followups || [],
            "askProcessingQuestion",
            "processing-chat-starters",
            "processing-chat-starter"
        );
        messagesEl.appendChild(aiMsg);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        processingChatHistory.push({ role: "user", content: question });
        processingChatHistory.push({ role: "assistant", content: data.response || "" });

    } catch (err) {
        typing.remove();
        const errMsg = document.createElement("div");
        errMsg.className = "chat-msg chat-msg-ai";
        errMsg.textContent = "Sorry, something went wrong. Please try again.";
        messagesEl.appendChild(errMsg);
        console.error("Processing chat error:", err);
    }
}

function askProcessingQuestion(question) {
    const input = $("#processing-chat-input");
    if (input) {
        input.value = question;
        sendProcessingChatMessage();
    }
}

function resetProcessingChat() {
    processingChatHistory = [];
    processingChatInitialized = false;
}

// ══════════════════════════════════════════════════════
// User Rules (Step 140)
// ══════════════════════════════════════════════════════

function showRuleCreationDialog(provCode, provName) {
    const suggestion = `Provision ${provCode} (${provName}): treat this type of change as conforming in future analyses.`;
    const modal = $("#rules-dialog-modal");
    const textarea = $("#rules-dialog-text");
    const provHint = $("#rules-dialog-provision-hint");
    const statusEl = $("#rules-dialog-status");
    if (!modal || !textarea) return;

    textarea.value = suggestion;
    if (provHint) provHint.value = provCode;
    if (statusEl) { statusEl.textContent = ""; statusEl.classList.add("hidden"); }

    modal.classList.add("open");
    textarea.focus();
    textarea.select();
}

async function saveRule() {
    const textarea = $("#rules-dialog-text");
    const provHint = $("#rules-dialog-provision-hint");
    const saveBtn = $("#rules-dialog-save");
    const statusEl = $("#rules-dialog-status");

    const text = (textarea?.value || "").trim();
    if (!text) return;

    const code = sessionStorage.getItem("cam_access_code") || "";

    if (saveBtn) saveBtn.disabled = true;
    if (statusEl) { statusEl.textContent = "Saving..."; statusEl.classList.remove("hidden"); }

    try {
        const resp = await fetch("/api/rules", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                access_code: code,
                text: text,
                provision_hint: provHint?.value || "",
            }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Save failed");
        }
        if (statusEl) { statusEl.textContent = "\u2713 Rule saved \u2014 will apply to future runs."; }
        setTimeout(() => closeRuleDialog(), 2000);
    } catch (err) {
        if (statusEl) { statusEl.textContent = "Error: " + err.message; }
    } finally {
        if (saveBtn) saveBtn.disabled = false;
    }
}

function closeRuleDialog() {
    const modal = $("#rules-dialog-modal");
    if (modal) modal.classList.remove("open");
}

async function showRulesPanel() {
    const modal = $("#rules-panel-modal");
    const list = $("#rules-panel-list");
    if (!modal || !list) return;

    const code = sessionStorage.getItem("cam_access_code") || "";
    list.innerHTML = '<div style="color:var(--text-muted)">Loading...</div>';
    modal.classList.add("open");

    try {
        const resp = await fetch(`/api/rules?access_code=${encodeURIComponent(code)}`);
        if (!resp.ok) throw new Error("Failed to load rules");
        const data = await resp.json();
        const rules = data.rules || [];

        if (rules.length === 0) {
            list.innerHTML = '<div style="color:var(--text-muted);font-size:0.875rem;">No rules yet. Click "No" on a finding\'s feedback row to create one.</div>';
            return;
        }

        list.innerHTML = "";
        rules.forEach(rule => {
            const item = document.createElement("div");
            item.className = "rules-panel-item";
            item.innerHTML = `
                <div class="rules-panel-item-text">${esc(rule.text)}</div>
                <div class="rules-panel-item-meta">
                    ${rule.provision_hint ? `<span class="rules-panel-tag">${esc(rule.provision_hint)}</span>` : ""}
                    <span class="rules-panel-date">${rule.created_at.slice(0,10)}</span>
                </div>
                <button class="rules-panel-delete" data-id="${esc(rule.id)}" onclick="window.CAM.deleteRule('${esc(rule.id)}', this)">Delete</button>
            `;
            list.appendChild(item);
        });
    } catch (err) {
        list.innerHTML = `<div style="color:var(--text-muted)">Error: ${esc(err.message)}</div>`;
    }
}

async function deleteRule(ruleId, btnEl) {
    const code = sessionStorage.getItem("cam_access_code") || "";
    if (btnEl) btnEl.disabled = true;
    try {
        const resp = await fetch(`/api/rules/${encodeURIComponent(ruleId)}?access_code=${encodeURIComponent(code)}`, {
            method: "DELETE",
        });
        if (!resp.ok) throw new Error("Delete failed");
        const item = btnEl?.closest(".rules-panel-item");
        if (item) item.remove();
    } catch (err) {
        if (btnEl) { btnEl.disabled = false; btnEl.textContent = "Error"; }
    }
}

// ── Final Draft ──────────────────────────────────────────────────────────────

function getFinalDraftKey(tenantIdx, pid) {
    return `${tenantIdx}:${pid}`;
}

function setFinalDraftDecision(tenantIdx, pid, choice, text) {
    const key = getFinalDraftKey(tenantIdx, pid);
    const prev = finalDraftDecisions[key] || {};
    finalDraftDecisions[key] = { ...prev, choice, text };
    updateFinalDraftBar();
    updateDecisionBadge(tenantIdx, pid, choice);
}

function getFinalDraftDecision(tenantIdx, pid) {
    return finalDraftDecisions[getFinalDraftKey(tenantIdx, pid)] || null;
}

function getFinalDraftTenantIndices() {
    if (!currentResults || !Array.isArray(currentResults.tenants)) return [];
    if (contractDetailOpen && currentTenantIndex >= 0 && currentTenantIndex < currentResults.tenants.length) {
        return [currentTenantIndex];
    }
    return currentResults.tenants.map((_, idx) => idx);
}

function countFinalDraftDecisions() {
    if (!currentResults) return { decided: 0, resolved: 0, ready: 0, total: 0 };
    let total = 0, decided = 0, resolved = 0, ready = 0;
    getFinalDraftTenantIndices().forEach(i => {
        const t = currentResults.tenants[i];
        getDeviationWorkflowProvisions((t.results?.provisions || []), i).forEach(p => {
                total++;
                const dec = finalDraftDecisions[getFinalDraftKey(i, p.provision_id)];
                const status = (resolutionState[`${i}:${p.provision_id}`] || {}).status || 'open';
                // custom only counts as decided if text has been explicitly saved
                const isDecided = !!(dec && (dec.choice === 'template' || dec.choice === 'tenant' || (dec.choice === 'custom' && dec.saved && dec.text)));
                if (isDecided) decided++;
                if (status === 'resolved' || status === 'not_a_deviation') resolved++;
                if ((status === 'not_a_deviation') || (isDecided && status === 'resolved')) ready++;
        });
    });
    return { decided, resolved, ready, total };
}

function updateFinalDraftBar() {
    const statusEl = $('#final-draft-status');
    const headerStatusEl = $('#final-draft-status-header');
    const btn = $('#fd-generate-btn');
    if (!statusEl && !headerStatusEl && !btn) return;
    const { decided, resolved, ready, total } = countFinalDraftDecisions();
    const remaining = Math.max(0, total - ready);
    const statusHTML = '<span class="fd-bar-label">\uD83D\uDCCB Final Draft:</span> '
        + '<span class="fd-counter">' + `${remaining} deviation${remaining === 1 ? '' : 's'} remaining` + '</span>';
    [statusEl, headerStatusEl].forEach(el => {
        if (!el) return;
        if (total === 0) el.classList.add('hidden');
        else { el.classList.remove('hidden'); el.innerHTML = statusHTML; }
    });
    if (btn) btn.disabled = ready < total;
}

function updateDecisionBadge(tenantIdx, pid, choice) {
    // Update the button states on the card
    const card = document.getElementById(`dev-${pid}`);
    if (!card) return;
    card.querySelectorAll('.fd-btn').forEach(btn => {
        btn.classList.toggle('fd-btn-active', btn.dataset.choice === choice);
    });
    // Show/hide the modify panel
    const modifyPanel = card.querySelector('.fd-modify-panel');
    if (modifyPanel) modifyPanel.classList.toggle('hidden', choice !== 'custom');
}

// Open the modify panel (no AI call — user must explicitly click AI Draft)
function finalDraftModify(tenantIdx, pid) {
    const dec = getFinalDraftDecision(tenantIdx, pid);
    // If switching away from a saved custom back to Modify, just re-open panel
    if (!dec || dec.choice !== 'custom') {
        // Mark as custom but with no saved text yet (unsaved)
        finalDraftDecisions[getFinalDraftKey(tenantIdx, pid)] = { choice: 'custom', text: '', saved: false };
        updateFinalDraftBar();
    }
    const card = document.getElementById(`dev-${pid}`);
    if (!card) return;
    const panel = card.querySelector('.fd-modify-panel');
    if (!panel) return;
    panel.classList.remove('hidden');
    card.querySelectorAll('.fd-btn').forEach(btn => {
        btn.classList.toggle('fd-btn-active', btn.dataset.choice === 'custom');
    });
}

// Keep Reference or Keep Tenant — with override confirm if saved custom text exists
function fdChooseSimple(tenantIdx, pid, choice) {
    const dec = getFinalDraftDecision(tenantIdx, pid);
    if (dec && dec.choice === 'custom' && dec.saved && dec.text) {
        const label = choice === 'template' ? 'Keep Reference' : 'Keep Tenant';
        if (!confirm(`You have saved modified text for this provision. Switch to "${label}" and discard your edits?`)) return;
    }
    setFinalDraftDecision(tenantIdx, pid, choice, '');
    refreshDocviewIfActive(tenantIdx);
    const key = `${tenantIdx}:${pid}`;
    const isResolved = (resolutionState[key] || {}).status === "resolved";
    if (!isResolved && confirm("Mark this issue as resolved now?")) {
        setResolutionStatus(pid, tenantIdx, "resolved");
    }
}

// AI Draft button — fetch suggestion and insert into textarea (not auto-saved)
function fdOpenChatDraft(tenantIdx, pid, mode = 'custom') {
    askAboutFinding(pid, tenantIdx, "", "draft");
}

async function fdAiDraft(tenantIdx, pid, mode = 'custom') {
    let templateText = '', tenantText = '';
    if (currentResults && currentResults.tenants && currentResults.tenants[tenantIdx]) {
        const provs = currentResults.tenants[tenantIdx].results?.provisions || [];
        const p = provs.find(p => p.provision_id === pid);
        if (p) { templateText = p.template_text || ''; tenantText = p.tenant_text || ''; }
    }
    const card = document.getElementById(`dev-${pid}`);
    if (!card) return;
    const panel = card.querySelector('.fd-modify-panel');
    if (!panel) return;
    const textarea = panel.querySelector('.fd-modify-textarea');
    const instructionInput = panel.querySelector('.fd-modify-instruction');
    const aiBtn = panel.querySelector('.fd-ai-draft-btn');
    const saveBtn = panel.querySelector('.fd-save-btn');
    if (aiBtn) { aiBtn.disabled = true; aiBtn.textContent = 'Drafting\u2026'; }
    if (saveBtn) saveBtn.disabled = true;
    if (textarea) textarea.placeholder = 'AI is drafting a compromise\u2026';
    const customInstruction = instructionInput ? instructionInput.value.trim() : '';
    const modeInstructionMap = {
        middle: 'Draft a balanced middle-ground clause between the reference and tenant language.',
        landlord: 'Draft a clause that remains commercially reasonable but leans toward the landlord position.',
        tenant: 'Draft a clause that remains commercially reasonable but leans toward the tenant position.',
        narrow: 'Draft the smallest targeted change needed to address the deviation while preserving as much existing language as possible.',
        custom: customInstruction
            ? `Draft based on this user instruction: ${customInstruction}`
            : 'Draft a balanced middle-ground clause between the reference and tenant language.'
    };
    try {
        const prompt = `You are a commercial real estate attorney drafting compromise lease language.

Standard template clause:
${templateText}

Tenant's proposed clause:
${tenantText}

Draft a single clause revision that follows this drafting direction:
${modeInstructionMap[mode] || modeInstructionMap.custom}

Requirements:
- Balances landlord and tenant interests
- Honor specific numeric or business instructions if the user gave any
- Uses clear, standard commercial lease language
- Is concise (do not add commentary or explanation)
- Returns ONLY the clause text, nothing else`;
        const resp = await fetch('/api/ai-summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
        });
        const data = await resp.json();
        if (textarea) {
            textarea.value = data.summary || '';
            textarea.placeholder = 'Edit or click Save to keep this text\u2026';
        }
        const key = getFinalDraftKey(tenantIdx, pid);
        if (instructionInput && customInstruction) {
            finalDraftDecisions[key] = { ...(finalDraftDecisions[key] || {}), choice: 'custom', instruction: customInstruction };
        }
    } catch(e) {
        if (textarea) textarea.placeholder = 'AI draft failed \u2014 type your compromise text here';
    } finally {
        if (aiBtn) { aiBtn.disabled = false; aiBtn.textContent = '\u2728 Draft from instruction'; }
        if (saveBtn) saveBtn.disabled = false;
    }
}

// Save button — explicitly commits textarea content
function fdSave(tenantIdx, pid, markResolved = true) {
    const card = document.getElementById(`dev-${pid}`);
    if (!card) return;
    const textarea = card.querySelector('.fd-modify-textarea');
    const text = textarea ? textarea.value.trim() : '';
    if (!text) { alert('Please enter some text before saving.'); return; }
    finalDraftDecisions[getFinalDraftKey(tenantIdx, pid)] = {
        choice: 'custom',
        text,
        saved: true
    };
    updateFinalDraftBar();
    // Re-render just this card's buttons to show "Keep Modified ✓"
    const modifyBtn = card.querySelector('.fd-btn[data-choice="custom"]');
    if (modifyBtn) modifyBtn.textContent = 'Keep Modified \u2713';
    card.querySelectorAll('.fd-btn').forEach(btn => {
        btn.classList.toggle('fd-btn-active', btn.dataset.choice === 'custom');
    });
    const saveBtn = card.querySelector('.fd-save-btn');
    if (saveBtn) { saveBtn.textContent = 'Saved \u2713'; saveBtn.disabled = true; }
    // Re-enable save on further edits
    if (textarea) textarea.oninput = () => {
        if (saveBtn) { saveBtn.textContent = 'Save'; saveBtn.disabled = false; }
    };
    if (markResolved) setResolutionStatus(pid, tenantIdx, "resolved");
    else {
        const key = `${tenantIdx}:${pid}`;
        if ((resolutionState[key] || {}).status === "resolved") {
            setResolutionStatus(pid, tenantIdx, "open");
        }
    }
    refreshDocviewIfActive(tenantIdx);
}

// Clear button — wipe textarea (does not unsave previous save)
async function fdSaveAsNote(tenantIdx, pid) {
    const card = document.getElementById(`dev-${pid}`);
    if (!card) return;
    const textarea = card.querySelector('.fd-modify-textarea');
    const noteBtn = card.querySelector('.fd-note-btn');
    const draftText = textarea ? textarea.value.trim() : '';
    let noteText = '';
    if (draftText) {
        noteText = `Possible clause language:\n${draftText}`;
    }
    if (!noteText) {
        alert('Add a rough instruction or draft text first.');
        return;
    }
    if (noteBtn) { noteBtn.disabled = true; noteBtn.textContent = 'Saving...'; }
    const saved = await addResolutionNote(pid, tenantIdx, noteText);
    if (noteBtn) noteBtn.textContent = saved ? 'Saved to Notes' : 'Save as Note';
}

function fdClear(tenantIdx, pid) {
    const card = document.getElementById(`dev-${pid}`);
    if (!card) return;
    const textarea = card.querySelector('.fd-modify-textarea');
    if (textarea) { textarea.value = ''; textarea.focus(); }
    const saveBtn = card.querySelector('.fd-save-btn');
    if (saveBtn) { saveBtn.textContent = 'Save'; saveBtn.disabled = false; }
}

async function generateFinalDraft() {
    const { ready, total } = countFinalDraftDecisions();
    if (ready < total) return;

    const btn = $('#fd-generate-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Generating\u2026'; }

    // Build decisions payload
    const decisions = {};
    if (currentResults) {
        getFinalDraftTenantIndices().forEach(i => {
            const t = currentResults.tenants[i];
            (t.results?.provisions || []).forEach(p => {
                const key = getFinalDraftKey(i, p.provision_id);
                const dec = finalDraftDecisions[key];
                if (dec) {
                    decisions[p.provision_id] = {
                        choice: dec.choice,
                        text: dec.choice === 'template' ? (p.template_text || '')
                            : dec.choice === 'tenant'   ? (p.tenant_text || '')
                            : dec.text,
                        provision_name: p.provision_name || '',
                        final_verdict: p.final_verdict,
                        severity: p.severity || '',
                    };
                } else if (p.final_verdict === 'CONFORMS') {
                    decisions[p.provision_id] = {
                        choice: 'tenant',
                        text: p.tenant_text || '',
                        provision_name: p.provision_name || '',
                        final_verdict: 'CONFORMS',
                        severity: '',
                    };
                }
            });
        });
    }

    try {
        const resp = await fetch('/api/final-draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: currentJobId, decisions }),
        });
        if (!resp.ok) throw new Error('Server error');
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `final_draft_${currentJobId || 'lease'}.docx`;
        a.click();
        URL.revokeObjectURL(url);
    } catch(e) {
        alert('Failed to generate final draft. Please try again.');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Generate Final Draft \u2193'; }
        updateFinalDraftBar();
    }
}

function injectFinalDraftBar() {
    const existing = $('#final-draft-bar');
    if (existing) existing.remove();
    updateFinalDraftBar();
}

// Step 186: Jump to audit trail provision row (or coverage audit LP for Mode C)
function jumpToAuditProvision(tenantIdx, pid) {
    switchResultsTab('audittrail');
    waitForResultsTarget(() => {
        // Mode A: find the standard provision row
        const modeARow = document.querySelector(`.audit-provision-row[data-pid="${CSS.escape(pid)}"][data-tenant="${tenantIdx}"]`) ||
               document.querySelector(`.audit-provision-row[data-pid="${CSS.escape(pid)}"]`);
        if (modeARow) return modeARow;
        // Mode C: find the coverage audit LP section
        return document.querySelector(`.audit-cov-lp[data-pid="${CSS.escape(pid)}"]`);
    }, { attempts: 18, delay: 90 }).then((row) => {
        if (!row) return;
        if (row.classList.contains('audit-cov-lp')) {
            // Coverage audit LP — expand its body if collapsed
            const header = row.querySelector('.audit-cov-lp-header');
            const lpBodyId = row.querySelector('[id^="audit-cov-lp-body-"]');
            if (lpBodyId && lpBodyId.style.display === 'none') {
                if (header) header.click();
            }
        } else {
            // Mode A provision row
            const idx = row.dataset.idx;
            const detail = idx ? document.getElementById(`audit-detail-${idx}`) : null;
            if (detail && detail.classList.contains('hidden')) {
                toggleAuditRow(idx);
            }
        }
        setTimeout(() => {
            scrollResultsTargetIntoView(row, 8);
            flashResultsTarget(row, 2000);
        }, 100);
    });
}

// Step 183: Open About CAM modal, optionally scroll to a section
function showAboutModal(scrollToId) {
    const modal = $("#about-cam-modal");
    if (modal) modal.classList.add("open");
    if (scrollToId) {
        setTimeout(() => {
            const el = document.getElementById(scrollToId);
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
}

// ── Notable clauses sub-section (Step 207) ──

function buildNotableClausesHtml(discs, pid, modelsUsed, provision) {
    if (!discs || discs.length === 0) return '';

    // Suppress if the provision was fully challenged — challenge output already
    // articulates the specific clause-level findings. Notable clauses only add
    // value when the provision wasn't challenged (WITHHOLD, triage-skipped).
    const challengeDetails = (provision && provision.challenge_details) || '';
    const challengeFinding = (provision && provision.challenge_finding) || '';
    const wasFullyChallenged = challengeDetails.length > 50 ||
                               (challengeFinding && challengeFinding !== 'NO_ISSUE');
    if (wasFullyChallenged) return '';

    const evalNames = modelsUsed ? getEvaluatorNames(modelsUsed) : {};

    const items = discs.map(d => {
        const name = esc(d.clause_name || 'Unnamed Clause');
        const secRef = d.tenant_section_ref ? `<span class="notable-section-ref">${esc(d.tenant_section_ref)}</span>` : '';
        const text = d.clause_text || '';
        const displayText = text.length > 200 ? text.substring(0, 200) + '...' : text;

        // Per-model reasoning
        let reasoningHtml = '';
        if (d.evaluator_details && Object.keys(d.evaluator_details).length > 0) {
            const details = Object.entries(d.evaluator_details).map(([key, det]) => {
                const modelName = evalNames[key] ? evalNames[key].name : `Model ${key}`;
                return `<div><strong>${esc(modelName)}:</strong> ${esc(det.reasoning || '')}</div>`;
            }).join('');
            reasoningHtml = `<details class="notable-reasoning"><summary>Model reasoning</summary><div class="notable-reasoning-body">${details}</div></details>`;
        }

        return `<div class="notable-clause-item">
            <div class="notable-clause-header">
                <span class="notable-clause-name">${name}</span>
                ${secRef}
            </div>
            <div class="notable-clause-text">${esc(displayText)}</div>
            ${reasoningHtml}
        </div>`;
    }).join('');

    const label = discs.length === 1
        ? '1 notable clause identified within this provision'
        : `${discs.length} notable clauses identified within this provision`;

    const subId = `notable-${esc(pid)}`;

    return `<div class="notable-clauses-section">
        <button class="notable-clauses-toggle" onclick="window.CAM.toggleNotableClauses('${subId}'); event.stopPropagation();">
            &#9656; ${label}
        </button>
        <div class="notable-clauses-body hidden" id="${subId}">
            ${items}
        </div>
    </div>`;
}

function toggleNotableClauses(subId) {
    const body = document.getElementById(subId);
    const btn = body && body.previousElementSibling;
    if (!body) return;
    const isOpen = !body.classList.contains('hidden');
    body.classList.toggle('hidden', isOpen);
    if (btn) {
        btn.innerHTML = btn.innerHTML.replace(
            isOpen ? '&#9662;' : '&#9656;',
            isOpen ? '&#9656;' : '&#9662;'
        );
    }
}

// ── Demo file library (Step 206) ──

async function loadDemoTemplate() {
    // Only load if no template is already set
    if (templateFile) return;

    try {
        const resp = await fetch('/static/demo/template.txt');
        if (!resp.ok) return; // demo files not present — silently skip
        const blob = await resp.blob();
        const file = new File([blob], 'Meridian Standard Template (demo).txt',
                              { type: 'text/plain' });
        handleTemplateFiles([file]);
    } catch (e) {
        // Demo files unavailable — fail silently, don't block normal use
        console.warn('Demo template not available:', e);
    }
}

function toggleDemoTenantPicker() {
    const picker = $('#demo-tenant-picker');
    const arrow  = $('#demo-toggle-arrow');
    if (!picker) return;
    const isOpen = !picker.classList.contains('hidden');
    picker.classList.toggle('hidden', isOpen);
    if (arrow) arrow.innerHTML = isOpen ? '&#9660;' : '&#9650;';
}

function updateDemoLoadBtn() {
    const btn = $('#demo-load-btn');
    if (!btn) return;
    const anyChecked = document.querySelectorAll('.demo-tenant-check:checked').length > 0;
    btn.disabled = !anyChecked;
}

async function loadDemoTenants() {
    const checked = [...document.querySelectorAll('.demo-tenant-check:checked')];
    if (checked.length === 0) return;

    const btn = $('#demo-load-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Loading...'; }

    const files = [];
    for (const cb of checked) {
        try {
            const resp = await fetch(`/static/demo/${cb.value}`);
            if (!resp.ok) continue;
            const blob = await resp.blob();
            const nameMap = {
                'T-01_clean.txt':        'Demo — Clean Lease.txt',
                'T-03_obvious.txt':      'Demo — Obvious Changes.txt',
                'T-07_aggressive.txt':   'Demo — Aggressive Counsel.txt',
                'T-10_sophisticated.txt':'Demo — Sophisticated Counsel.txt',
            };
            const displayName = nameMap[cb.value] || cb.value;
            files.push(new File([blob], displayName, { type: 'text/plain' }));
        } catch (e) {
            console.warn('Failed to load demo file:', cb.value, e);
        }
    }

    if (files.length > 0) {
        handleTenantFiles(files);
    }

    // Collapse picker after loading
    const picker = $('#demo-tenant-picker');
    if (picker) picker.classList.add('hidden');
    const arrow = $('#demo-toggle-arrow');
    if (arrow) arrow.innerHTML = '&#9660;';
    if (btn) { btn.textContent = 'Load Selected'; }
}

// ── Aggressive Read (Step 228) ──
async function aggressiveRead(pid, tenantIdx) {
    const resultId = `aggressive-result-${pid}`;
    const btnId = `aggressive-btn-${pid}`;
    const existing = document.getElementById(resultId);
    const btn = document.getElementById(btnId);

    // Toggle: if result already showing, hide it
    if (existing && !existing.classList.contains('hidden')) {
        existing.classList.add('hidden');
        if (btn) btn.textContent = 'Strongest Tenant Reading';
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Analyzing…'; }

    try {
        const resp = await fetch(`/api/jobs/${currentJobId}/aggressive-read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tenant_index: tenantIdx, provision_id: pid }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || 'Request failed');
        }

        const data = await resp.json();
        const analysis = data.analysis || '';

        // Find or create result panel
        let panel = document.getElementById(resultId);
        if (!panel) {
            // Insert after the action bar — find the resolution-bar parent
            const bar = document.querySelector(`.resolution-bar[data-pid="${CSS.escape(pid)}"][data-tenant-idx="${tenantIdx}"]`)
                || document.querySelector(`.resolution-bar[data-pid="${CSS.escape(pid)}"]`);
            if (bar) {
                panel = document.createElement('div');
                panel.id = resultId;
                panel.className = 'aggressive-read-panel';
                bar.after(panel);
            }
        }

        if (panel) {
            // Format the four numbered sections with simple paragraph breaks
            const formatted = esc(analysis)
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>');
            panel.innerHTML = `
                <div class="aggressive-read-header">
                    <span class="aggressive-read-label">⚡ Strongest Tenant Reading</span>
                    <span class="aggressive-read-advisory">Advisory only — does not affect scores or findings</span>
                    <button class="aggressive-read-close" onclick="document.getElementById('${resultId}').classList.add('hidden'); document.getElementById('${btnId}').textContent='Strongest Tenant Reading';">✕</button>
                </div>
                <div class="aggressive-read-body"><p>${formatted}</p></div>
            `;
            panel.classList.remove('hidden');
        }

        if (btn) btn.textContent = 'Strongest Tenant Reading';

    } catch (err) {
        if (btn) btn.textContent = 'Strongest Tenant Reading';
        console.error('Aggressive read error:', err);
        alert(`Could not generate analysis: ${err.message}`);
    } finally {
        if (btn) btn.disabled = false;
    }
}

window.CAM = {
    aggressiveRead,
    showAboutModal,
    jumpToDocview,
    jumpToAuditProvision,
    submitFeedback,
    downloadFile,
    exportTenantJSON,
    askAboutFinding,
    jumpToProvision,
    searchInDoc,
    toggleFilterDropdown,
    clearFilters,
    setProvisionFilter,
    resetChatScope,
    toggleTechDetails,
    downloadSynopsis,
    exportJSON,
    checkAllProvisions: () => toggleAllProvisions(true),
    uncheckAllProvisions: () => toggleAllProvisions(false),
    resetApp,
    toggleEmailAccordion,
    toggleSecurityAccordion,
    askHelpQuestion,
    askAnalysisQuestion,
    handleBackToResults,
    cancelAddMore,
    toggleAuditRow,
    expandAllAuditRows,
    syncAuditExpandToggle,
    collapseAllConforming,
    collapseAllAuditRows,
    exportAuditJSON,
    exportAuditText,
    setResolutionStatus,
    toggleResolutionNotes,
    openResolutionAdvisor,
    saveResolutionNote,
    deleteResolutionNote,
    askResolution,
    submitProcessingEmail,
    carouselNext,
    carouselPrev,
    askProcessingQuestion,
    markContractResolved,
    reopenContract,
    toggleNoted,
    closeContractDetail,
    showRuleCreationDialog,
    saveRule,
    closeRuleDialog,
    showRulesPanel,
    deleteRule,
    setFinalDraftDecision,
    finalDraftModify,
    fdChooseSimple,
    fdOpenChatDraft,
    fdAiDraft,
    fdSave,
    fdSaveAsNote,
    fdClear,
    generateFinalDraft,
    openDocviewSummary,
    openDocviewModify,
    toggleDocviewResolutionNotes,
    saveDocviewResolutionNote,
    deleteDocviewResolutionNote,
    handleConformingConcernAction,
    toggleDocviewAnalysis,
    toggleContractSummaryCollapse,
    toggleSection,
    switchToDocview: function() { switchResultsTab("docview"); },
    switchResultsTab,
    viewCancelledResults: async function() {
        try {
            await loadResults();
            showState("results");
        } catch (err) {
            console.error("Error loading cancelled results:", err);
        }
    },
    sortAuditTrail,
    openAllTechDetails,
    closeAllTechDetails,
    showAboutModal,
    toggleNotableClauses,
    loadDemoTemplate,
    toggleDemoTenantPicker,
    loadDemoTenants,
    jumpToEvidence,
    // Step 361: Evidence View Proof Inspector
    _evToggleLp,
    _evToggleCpf,
    _evGoBack,
    _evFilter,
    _evSetFilter,
    _navGoEvidenceFromContract,
    _navGoEvidenceFromKeyIssues,
};

// ── Step 245: Coverage & Gaps Panel ──
function buildCovToolbar(a, tenantIdx) {
    const pid = a.issue_area_id || '';
    const state = a.coverage_state || '';
    const pcls = a.partial_class || '';
    const evidSumm = a.evidence_summary || '';

    // Status pills only for high-priority items
    const showStatus = (state === 'covered_unfavorable' || pcls === 'partial_material');
    // Audit Trail only when evaluators actually ran (evidence_summary mentions Step 305)
    const showAuditBtn = evidSumm.includes('Step 305');

    const res = _getCovRes(tenantIdx, pid);
    const resStatus = res.status || 'open';
    const noteCount = (res.notes || []).length;

    const statusDefs = [
        { key: 'reviewed',    label: 'Reviewed',              cls: 'cov-pill-reviewed' },
        { key: 'flagged',     label: 'Flag for Negotiation',  cls: 'cov-pill-flagged' },
        { key: 'accepted',    label: 'Accepted Risk',         cls: 'cov-pill-accepted' },
    ];

    const pillsHtml = showStatus ? statusDefs.map(s =>
        `<button class="cov-pill ${s.cls}${resStatus === s.key ? ' cov-pill-active' : ''}"
            data-status="${s.key}" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}"
            onclick="window.CAM._setCovStatus('${esc(pid)}', ${tenantIdx}, '${s.key}'); event.stopPropagation();">
            ${s.label}
        </button>`
    ).join('') : '';

    const notesHtml = `<button class="cov-notes-btn res-notes-toggle" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}"
        onclick="window.CAM._toggleCovNotes('${esc(pid)}', ${tenantIdx}); event.stopPropagation();">
        📝 Notes${noteCount > 0 ? ` <span class="res-note-count">${noteCount}</span>` : ''}
    </button>`;

    // Step 341b: suppress "Draft Missing Clause" when use_impact marks gap as beneficial
    const _uiFavorable = normalizeUseConsequence(a.use_impact) === 'beneficial';
    const isMissingAdvisor = state === 'missing' && !_uiFavorable;
    const advisorLabel = isMissingAdvisor ? '💡 Draft Missing Clause' : '💡 AI Advisor';
    const advisorCls = isMissingAdvisor ? 'res-advisor-btn cov-advisor-primary' : 'res-advisor-btn';
    const advisorHtml = `<button class="${advisorCls}"
        onclick="window.CAM._openCovAdvisor('${esc(pid)}', ${tenantIdx}, '${esc(a.issue_area_name || pid)}', '${esc((a.exposure_statement || '').replace(/'/g, ''))}', ${isMissingAdvisor}); event.stopPropagation();">
        ${advisorLabel}
    </button>`;

    const isMissing = state === 'missing';
    const docLabel = isMissing ? 'View Template Clause' : 'Document Comparison';
    const navHtml = `<div class="workflow-open-actions workflow-group">
        ${!isMissing ? `<a class="card-docview-link card-docview-link--btn" href="#"
           onclick="window.CAM.openDocviewSummary(${tenantIdx}, '${esc(pid)}'); return false;">Lease Summary</a>` : ''}
        <a class="card-docview-link card-docview-link--btn" href="#"
           onclick="window.CAM.jumpToDocview('${esc(pid)}'); return false;">${docLabel}</a>
        ${showAuditBtn ? `<a class="card-audit-link card-audit-link--btn" href="#"
           onclick="window.CAM.jumpToAuditProvision(${tenantIdx}, '${esc(pid)}'); return false;">CAM Audit Trail</a>` : ''}
    </div>`;

    const notesPanel = `<div class="cov-notes-panel res-notes-panel hidden" id="cov-notes-${tenantIdx}-${esc(pid)}">
        <div class="res-note-input-row cov-note-input-row">
            <textarea class="res-note-input" id="cov-note-input-${tenantIdx}-${esc(pid)}"
                placeholder="Add a note…" rows="2"></textarea>
            <button class="res-note-save-btn"
                onclick="window.CAM._saveCovNote('${esc(pid)}', ${tenantIdx})">Save</button>
        </div>
    </div>`;

    return `<div class="cov-toolbar resolution-bar finding-workflow-row" data-pid="${esc(pid)}" data-tenant-idx="${tenantIdx}">
        ${showStatus ? `<div class="workflow-group workflow-group-status"><span class="res-label">Status:</span><div class="res-pills">${pillsHtml}</div></div><div class="workflow-divider"></div>` : ''}
        <div class="workflow-group workflow-group-tools"><span class="res-tools-label">Tools:</span>${notesHtml}${advisorHtml}</div>
        <div class="workflow-divider workflow-divider-spacer"></div>
        ${navHtml}
    </div>
    ${notesPanel}`;
}

function renderCoveragePanel() {
    const tab = $("#coverage-tab");
    if (!tab) return;

    const tenantIdx = currentTenantIndex;
    const tenant = (currentResults && currentResults.tenants) ? currentResults.tenants[tenantIdx] : null;
    const pr = tenant && tenant.results ? tenant.results : null;
    const ca = pr && pr.coverage_assessment ? pr.coverage_assessment : null;

    _coverageTierFilter = 'all';
    _coverageStatusFilter = 'all';
    _coverageProvisionFilter = '';
    _cvShowFavorable = false;

    if (!ca || ca.length === 0) {
        tab.innerHTML = '<div class="coverage-empty"><p>Coverage analysis not available for this run.</p></div>';
        return;
    }

    // Step 297c: conflicts + jurisdiction data
    const STATE_FULL_NAMES = {"NY": "New York", "CA": "California", "TX": "Texas", "FL": "Florida", "IL": "Illinois"};
    const _prConflicts = (pr && pr.conflicts) || [];
    const _prJurisdiction = (pr && pr.jurisdiction) || {};

    // Build set of provision IDs in the pipeline (for nav links)
    const _pipelineProvIds = new Set((pr && pr.provisions || []).map(p => p.provision_id).filter(Boolean));

    // Step 297d.J / fix: perspective-aware favorability uses covered_unfavorable_adverse_to
    // (written by lease_coverage.py from schema field), not exposure_perspective.
    // exposure_perspective records whose perspective the exposure text was written from,
    // which equals the run perspective — not a reliable adversity signal across perspectives.
    const _viewerPerspective = getJobPerspective();
    function _isFavorable(a) {
        return a.coverage_state === "covered_unfavorable" &&
            _viewerPerspective && _viewerPerspective !== "neutral" &&
            a.covered_unfavorable_adverse_to &&
            a.covered_unfavorable_adverse_to !== _viewerPerspective;
    }

    // Step 341b: use_impact.use_consequence = "beneficial" or materiality = "not_applicable"
    // moves a missing/partial LP out of problems and into the favorable group.
    function _isUseImpactFavorable(a) {
        const ui = a.use_impact;
        if (!ui) return false;
        if (normalizeUseConsequence(ui) === 'beneficial') return true;
        if (ui.materiality === 'not_applicable') return true;
        return false;
    }
    const problems = ca.filter(a =>
        !_isFavorable(a) && !_isUseImpactFavorable(a) &&
        (a.coverage_state === "covered_unfavorable" || a.partial_class === "partial_material"
            || a.coverage_state === "missing" || a.coverage_state === "review_needed")
    );  // Step 357: review_needed added (Phase 3 LPs surface in Needs Attention)
    const favorable = ca.filter(a => _isFavorable(a) || _isUseImpactFavorable(a));
    const review   = ca.filter(a => a.partial_class === "partial_review" && !_isUseImpactFavorable(a));
    const covered  = ca.filter(a => a.coverage_state === "covered");
    const typical  = ca.filter(a => a.partial_class === "partial_typical");
    // Step 318: exclude favorable items so they don't also appear in the "Adequately Covered" rollup
    const other    = ca.filter(a => !problems.includes(a) && !favorable.includes(a) && !review.includes(a) && !covered.includes(a) && !typical.includes(a));

    const _cvIsNeutral = !_viewerPerspective || _viewerPerspective === "neutral";
    const STATE_LABELS = {
        "covered":             { label: "\u2713 Covered",     cls: "cv-badge-ok" },
        "covered_unfavorable": _cvIsNeutral
            ? { label: "\u26A0 Asymmetric",  cls: "cv-badge-asymmetric" }
            : { label: "\u26A0 Unfavorable", cls: "cv-badge-unfav" },
        "partial":             { label: "\u25D1 Partial",     cls: "cv-badge-partial" },
        "missing":             { label: "\u2717 Missing",     cls: "cv-badge-missing" },
        "not_applicable":      { label: "\u2014 N/A",         cls: "cv-badge-na" },
    };

    function buildItem(a, tier) {
        const pid = a.issue_area_id || "";
        const name = a.issue_area_name || pid;
        const state = a.coverage_state || "";
        const pcls = a.partial_class || "";
        const stmt = a.exposure_statement || "";
        const src = a.exposure_source || "";
        const missing = a.elements_missing || [];
        const nsSignals = (a.negative_space_signals || []).filter(s =>
            s.signal_type === "broken_xref" || s.signal_type === "missing_exhibit" || s.signal_type === "reserved_section"
        );
        // Step 280: read the same headline field the sidebar uses
        // (Step 278's `exposure_headline`); fall back to the JS-side
        // deterministic extractor so cached pre-Step-278 result dicts
        // still render a usable headline.
        const headline = (a.exposure_headline || _deriveHeadlineFromExposure(stmt) || "").trim();

        // Step 318: perspective flip — if this provision is unfavorable to the other party,
    // show FAVORABLE on the card face (same logic the sidebar already uses).
        const stateInfo = (tier === "favorable" || _isFavorable(a))
            ? { label: "✓ Favorable", cls: "cv-badge-favorable" }
            : (STATE_LABELS[state] || { label: state, cls: "cv-badge-na" });
        let pclsBadge = "";
        if (pcls === "partial_material") pclsBadge = '<span class="cv-pcls-badge cv-pcls-material">Needs attention</span>';
        else if (pcls === "partial_review") pclsBadge = '<span class="cv-pcls-badge cv-pcls-review">Worth reviewing</span>';

        const missingHtml = missing.length > 0
            ? '<div class="cv-missing-elements"><span class="cv-missing-label">Missing:</span>' +
              missing.map(m => `<span class="cv-missing-item">${esc(m)}</span>`).join("") +
              '</div>'
            : "";

        const nsHtml = nsSignals.length > 0
            ? '<div class="cv-ns-signals">' +
              nsSignals.slice(0, 2).map(s => `<span class="cv-ns-signal">${esc(s.description || s.signal_type)}</span>`).join("") +
              '</div>'
            : "";

        const _expSrc = src || (a.exposure_reason_code || "");
        const expProvenanceChip = _expSrc === "model"
            ? '<span class="cv-exp-provenance-chip">Lease-specific exposure</span>'
            : (_expSrc === "schema" || _expSrc === "schema_default")
                ? '<span class="cv-exp-provenance-chip cv-exp-default">Default exposure</span>'
                : '<span class="cv-exp-provenance-chip cv-exp-unknown">Exposure source unknown</span>';
        const tenantText = (a.tenant_text || "").trim();
        const leaseTextHtml = tenantText
            ? `<div class="cv-lease-text-row" onclick="(function(row){var body=row.nextElementSibling;var opening=body.style.display==='none';body.style.display=opening?'block':'none';row.querySelector('.cv-lt-arrow').textContent=opening?'▾':'▸';row.querySelector('.cv-lt-label').textContent=opening?'Hide lease text':'Show lease text';})(this)"><span class="cv-lt-arrow">▾</span><span class="cv-lt-label"> Hide lease text</span></div><div class="cv-lease-text-body"><pre class="cv-lease-text-pre">${esc(tenantText)}</pre></div>`
            : "";

        const toolbarHtml = buildCovToolbar(a, tenantIdx);

        // Step 306a + 307b: per-element progressive disclosure + confidence badge
        const elementVerdicts = a.element_verdicts || [];
        // Step 307b: derive governance signal and confidence badge (same infrastructure as Mode A)
        const _covGovSig = elementVerdicts.length > 0 ? deriveCoverageGovernanceSignal(elementVerdicts) : null;
        const _covBadgeData = (_covGovSig && window.CAMAuditShared) ? window.CAMAuditShared.getConfidenceBadgeData(_covGovSig) : null;
        // Step 374V: CONDITIONAL lawyer-facing copy for the consequence-not-assessed provenance state.
        // Keys off the EXACT 374Q surfacing of the consequence_source provenance flag — the
        // 'consequence_not_assessed' Needs-Review subtype (_reviewSubtypeOf), which 374Q already routes a
        // card to ONLY when it is a hard_flag-floored signal AND the consequence was defaulted/not assessed.
        // This is the critical anti-blanket guard: the raw consequenceDefaulted flag is true for ~17 cards
        // (most LPs lack use_impact), but the subtype gate isolates exactly the LP-06-style card (n=1 per run).
        // Doctrine: "Impact Unclear" falsely implies CAM assessed impact and reached uncertainty; here CAM
        // declined to assert an ungrounded consequence (constrained assertion) and routes it to the attorney.
        // Cards with genuinely-assessed impact keep their real label. Display/copy only — no logic change.
        const _consNotAssessed374V = (_reviewSubtypeOf(a) === 'consequence_not_assessed');
        const _covImpactLabel374V = _consNotAssessed374V ? 'Impact: attorney judgment required'
                                  : (_covBadgeData ? _covBadgeData.label : '');
        const confidenceBadgeHtml = _covBadgeData
            ? '<span class="cov-conf-label">Confidence:</span><span class="cam-confidence-badge cam-conf-' + _covBadgeData.cssClass + '" title="' + esc(_covImpactLabel374V) + '">' + _covBadgeData.dots + ' ' + esc(_covImpactLabel374V) + '</span>'
            : '';
        const _covEvidSumm = a.evidence_summary || '';
        const _evalCountMatch = _covEvidSumm.match(/(\d+\/\d+)\s+evaluator/);
        const assessMethodHtml = _covEvidSumm.includes('Step 305')
            ? '<span class="cv-assess-method cv-assess-method-eval">Assessed by ' + esc(_evalCountMatch ? _evalCountMatch[1] : '') + ' evaluators</span>'
            : '<span class="cv-assess-method cv-assess-method-preclass">Pre-classified</span>';
        let elementDetailHtml = "";
        if (elementVerdicts.length > 0) {
            const _POSITIVE_VERDICTS = new Set(['explicitly_present', 'implicitly_present', 'covered_by_default_law', 'covered_in_other_LP']);
            const coveredCount = elementVerdicts.filter(e => _POSITIVE_VERDICTS.has(e.verdict)).length;
            const totalCount = elementVerdicts.length;
            const summaryText = coveredCount === totalCount
                ? `All ${totalCount} elements covered`
                : `${coveredCount} of ${totalCount} elements covered`;
            const elemTableId = "cv-elem-body-" + pid;
            const VERDICT_CFG = {
                'explicitly_present':     { cls: 'cv-ev-present',  label: 'Present' },
                'implicitly_present':     { cls: 'cv-ev-implicit', label: 'Implicit' },
                'covered_by_default_law': { cls: 'cv-ev-default',  label: 'Default Law' },
                'covered_in_other_LP':    { cls: 'cv-ev-crosslp',  label: 'Cross-LP' },
                'missing':                { cls: 'cv-ev-missing',  label: 'Missing' },
                'unclear':                { cls: 'cv-ev-unclear',  label: 'Unclear' },
            };
            // Step 306c: derive LP-level jump link from best positive citation
            const _bestCit = elementVerdicts.find(function(e) {
                return _POSITIVE_VERDICTS.has(e.verdict) && e.citation && e.citation.section_ref;
            });
            const lpJumpHtml = _bestCit
                ? ' <span class="cv-section-link cv-elem-lp-jump" data-ref="' + esc(_bestCit.citation.section_ref) + '" data-quote="' + esc(_bestCit.citation.quote || '') + '" onclick="event.stopPropagation();window.CAM.jumpToEvidence(this.dataset.ref,this.dataset.quote)" title="View ' + esc(_bestCit.citation.section_ref) + ' in Evidence View">View in document</span>'
                : '';

            // Step 363: sort elements — disputed(0) → missing(1) → unclear(2) → present variants(3)
            const _cvVOrder = { 'disputed': 0, 'missing': 1, 'unclear': 2 };
            const sortedVerdicts = elementVerdicts.slice().sort(function(a, b) {
                const oa = (_cvVOrder[a.verdict] !== undefined) ? _cvVOrder[a.verdict] : 3;
                const ob = (_cvVOrder[b.verdict] !== undefined) ? _cvVOrder[b.verdict] : 3;
                return oa - ob;
            });
            const rowsHtml = sortedVerdicts.map(function(ev) {
                const vc = VERDICT_CFG[ev.verdict] || { cls: 'cv-ev-unclear', label: ev.verdict || '?' };
                // Step 306c: clickable citation
                const hasCit = ev.citation && ev.citation.section_ref;
                // Step 372D2-fix: on disagreement the merged citation is null; surface the
                // contested-but-cited section(s) instead of a bare "—".
                const _contestedCit = (!hasCit && ev.disagreement_citations)
                    ? contestedCitationHtml(ev.disagreement_citations, { style: 'inline' }) : '';
                const citHtml = hasCit
                    ? '<span class="cv-section-link" data-ref="' + esc(ev.citation.section_ref) + '" data-quote="' + esc(ev.citation.quote || '') + '" onclick="window.CAM.jumpToEvidence(this.dataset.ref,this.dataset.quote)">' + esc(ev.citation.section_ref) + '</span>'
                    : (_contestedCit || '—');
                // Step 307b: confidence dots
                const confDots = ev.confidence === 'high'   ? '<span class="ev-conf-dots ev-conf-high" title="3/3 consensus">●●●</span>'
                               : ev.confidence === 'medium' ? '<span class="ev-conf-dots ev-conf-medium" title="2/3 consensus">●●○</span>'
                               : ev.confidence === 'low'    ? '<span class="ev-conf-dots ev-conf-low" title="Split/inconclusive">●○○</span>'
                               : '';
                // Step 349b: vote count for disputed verdict
                const _DISP_PRES_VERDICTS = new Set(['explicitly_present','implicitly_present','covered_by_default_law','covered_in_other_LP']);
                const _dispPresCount = (ev.disagreements || []).filter(function(d){ return _DISP_PRES_VERDICTS.has(d.verdict); }).length;
                const _dispMissCount = (ev.disagreements || []).filter(function(d){ return d.verdict === 'missing'; }).length;
                const _dispVoteLabel = '(' + _dispPresCount + 'v' + _dispMissCount + ')';
                // Step 308: per-evaluator expandable panel
                const hasDisagreement = ev.disagreements && ev.disagreements.length > 0;
                // Step 364: missing + 2v1 disagreement → "Missing / Unclear"
                const vcLabel = (ev.verdict === 'missing' && hasDisagreement) ? 'Missing / Unclear' : vc.label;
                const evalVerdicts = ev.evaluator_verdicts;
                // Sanitize IDs (remove chars that break getElementById)
                const _safeEid = (ev.element_id || '').replace(/[^a-zA-Z0-9_-]/g, '_');
                const _safePid = pid.replace(/[^a-zA-Z0-9_-]/g, '_');
                const evalPanelId = 'ev-panel-' + _safePid + '-' + _safeEid;
                let evalToggle = '';
                let panelRow = '';
                if (evalVerdicts && evalVerdicts.length > 0) {
                    // Step 349c: disputed rows use plain "N Evaluators" label (not warning badge)
                    const _evalCount = evalVerdicts.length;
                    const btnLabel = (ev.verdict === 'disputed' || !hasDisagreement)
                        ? (_evalCount + (_evalCount === 1 ? ' Evaluator' : ' Evaluators'))
                        : '⚠ 2v1 Disagreement';
                    const btnCls = 'cv-ev-evals-btn' + ((hasDisagreement && ev.verdict !== 'disputed') ? ' cv-ev-evals-btn-disag' : '');
                    evalToggle = '<button class="' + btnCls + '" onclick="(function(btn){var p=document.getElementById(\'' + evalPanelId + '\');if(p){var wasHidden=p.style.display===\'none\';p.style.display=wasHidden?\'\':\'none\';btn.classList.toggle(\'cv-ev-evals-open\',wasHidden);}})(this);event.stopPropagation();" type="button">' + esc(btnLabel) + '</button>';
                    // Build inner per-evaluator rows for the panel
                    const evalRowsHtml = evalVerdicts.map(function(evi) {
                        const evLabel = evi.label || evalName(evi.role || '?');
                        const evc = VERDICT_CFG[evi.verdict] || { cls: 'cv-ev-unclear', label: evi.verdict || '?' };
                        const roleCls = EVALUATOR_COLORS[evi.role] ? 'cv-eval-badge eval-badge-' + evi.role + ' ' + EVALUATOR_COLORS[evi.role] : 'cv-eval-badge';
                        const evCitRef = evi.citation && evi.citation.section_ref ? ' <span class="cv-eval-ref">' + esc(evi.citation.section_ref) + '</span>' : '';
                        // Step 374U: show the FULL evaluator reasoning (display fix). This is already
                        // gated behind the per-element "2v1 Disagreement" expand toggle — the user has
                        // opted into the evidence — so clipping WITHIN that view hid the conclusion (the
                        // 300-char slice cut LP-06's Claude reasoning mid-sentence). Data was complete;
                        // 374T-Q confirmed display-only truncation. Max observed reasoning = 795 chars
                        // (well under the ~1500 scroll threshold), so plain full flow is fine. Escaping
                        // via esc() is preserved at the render site. No logic/count/routing change.
                        const reasoning = (evi.reasoning || '').trim();
                        const isDissent = evi.verdict !== ev.verdict;
                        // Step 372a: quiet audit-surface-only fallback tick. When a slot's
                        // primary model was unavailable and a fallback answered, mark it so
                        // the auditor knows the real model — not a lawyer-facing alarm.
                        const fallbackTick = evi.is_fallback
                            ? ' <span class="cv-eval-fallback" title="Primary model unavailable — answered by fallback ' + esc(evLabel) + '">↩ fallback</span>'
                            : '';
                        return '<div class="cv-eval-row' + (isDissent ? ' cv-eval-row-dissent' : '') + '">'
                            + '<span class="' + roleCls + '">' + esc(evi.role || '?') + '</span>'
                            + '<span class="cv-eval-name">' + esc(evLabel) + '</span>'
                            + fallbackTick
                            + '<span class="cv-ev-pill ' + evc.cls + ' cv-eval-verdict-pill">' + esc(evc.label) + '</span>'
                            + evCitRef
                            + (reasoning ? '<div class="cv-eval-reasoning">' + esc(reasoning) + '</div>' : '')
                            + '</div>';
                    }).join('');
                    panelRow = '<tr class="cv-ev-panel-row" id="' + evalPanelId + '" style="display:none">'
                        + '<td colspan="5" class="cv-ev-panel-cell">'
                        + '<div class="cv-eval-panel">' + evalRowsHtml + '</div>'
                        + '</td>'
                        + '</tr>';
                } else if (hasDisagreement) {
                    // Fallback for pre-308 cached data: show minimal disagreement info (role-correct)
                    const evalLines = ev.disagreements.map(function(d) {
                        return esc(d.role || d.evaluator_id || '?') + ': ' + esc(d.verdict || '');
                    }).join(' | ');
                    evalToggle = '<span class="cv-ev-disag-btn" onclick="(function(btn){var b=btn.nextElementSibling;b.style.display=b.style.display===\'none\'?\'block\':\'none\';})(this);event.stopPropagation();" title="Evaluator disagreement">⚠ Disagreement</span>'
                        + '<div class="cv-ev-disag-body" style="display:none">' + evalLines + ' → merged: ' + esc(ev.verdict) + '</div>';
                }
                // Step 363: red highlight for missing/disputed, amber for unclear
                const rowProblemClass = (ev.verdict === 'missing' || ev.verdict === 'disputed') ? ' elem-row-problem'
                    : ev.verdict === 'unclear' ? ' elem-row-warn' : '';
                // Step 364f: split STATUS into three separate <td> columns for true cross-row alignment
                const pillTd = ev.verdict === 'disputed'
                    ? '<td class="cv-ev-td-pill"><span class="element-status-disputed">Disputed</span></td>'
                    : '<td class="cv-ev-td-pill"><span class="cv-ev-pill ' + vc.cls + '">' + esc(vcLabel) + '</span></td>';
                const dotsTd = ev.verdict === 'disputed'
                    ? '<td class="cv-ev-td-dots"><span class="element-vote-count">' + _dispVoteLabel + '</span></td>'
                    : '<td class="cv-ev-td-dots">' + confDots + '</td>';
                const evalTd = '<td class="cv-ev-td-eval">' + evalToggle + '</td>';
                const mainRow = '<tr class="cv-ev-row' + rowProblemClass + '">'
                    + '<td class="cv-ev-label">' + esc(ev.element_label || ev.element_id || '') + '</td>'
                    + pillTd + dotsTd + evalTd
                    + '<td class="cv-ev-citation">' + citHtml + '</td>'
                    + '</tr>';
                return mainRow + panelRow;
            }).join('');
            // Step 351: LP-level severity header above element table
            const _lpVd = a.verdict_distance;
            const _lpSev = _lpVd && _lpVd.severity;
            const _lpConf = a.lp_confidence || a.lp_confidence_base || '';
            let _sevHeaderHtml = '';
            // Step 374K: HONEST CONTAINMENT. verdict_distance.pair is a DERIVED LP-level rollup
            // (plurality of each evaluator's element verdicts, pessimistic tie-break —
            // lease_verdict_distance.py:derive_per_evaluator_lp_verdict), NOT a standalone evaluator
            // conclusion, and the element rows below do NOT show that LP-level pair. So we stop
            // rendering "<v1> vs <v2> … Full evaluator reasoning below" (objectively false on-screen).
            // Wording only — no logic/routing/taxonomy change. See build_log/374K_governance_finding.md.
            if (_lpSev === 'severe') {
                // Step 374Q (PROVISIONAL): drop "Confidence capped at low" when the severe signal is a
                // tie-break artifact (tie_derived_severe). 374P confirmed the confidence cap rode in on
                // the SAME pessimistic tie-break as the disagreement — it is a consequence of the
                // artifact, not a substantive low-confidence finding. For genuine low-confidence severe
                // signals (not tie-derived) the cap note is kept. Wording only — confidence is NOT recomputed.
                const _tieDerivedSevere374Q = _lpProvenanceFlags374Q(a).tieDerivedSevere;
                const _capNote = (_lpConf && !_tieDerivedSevere374Q) ? ' Confidence capped at ' + esc(_lpConf) + '.' : '';
                // Step 374V: on the consequence-not-assessed provenance state, frame the escalation as
                // deliberate restraint routed to the attorney (constrained assertion), not a CAM shortfall.
                // Conditional on the same provenance flag; other severe cards keep the derived-signal banner.
                _sevHeaderHtml = _consNotAssessed374V
                    ? '<div class="cv-lp-sev-header cv-lp-sev-header-severe">&#x26A0; Attorney review recommended: potential exposure was identified; consequence requires your judgment. Element-level evidence appears below.</div>'
                    : '<div class="cv-lp-sev-header cv-lp-sev-header-severe">&#x26A0; Review escalation triggered from derived coverage signals.' + _capNote + ' Element-level evidence shown below.</div>';
            } else if (_lpSev === 'moderate') {
                const _capNote = _lpConf ? ' Confidence capped.' : '';
                _sevHeaderHtml = '<div class="cv-lp-sev-header cv-lp-sev-header-moderate">〜 Coverage-signal divergence derived from element verdicts.' + _capNote + ' Element-level evidence shown below.</div>';
            }
            elementDetailHtml = '<div class="cv-elem-summary-row" onclick="(function(row){var body=document.getElementById(\'' + elemTableId + '\');var opening=body.style.display===\'none\';body.style.display=opening?\'block\':\'none\';row.querySelector(\'.cv-elem-chevron\').textContent=opening?\'▾\':\'▸\';})(this)">'
                + '<span class="cv-elem-chevron">▸</span>'
                + '<span class="cv-elem-summary-text">' + summaryText + '</span>'
                + lpJumpHtml
                + '</div>'
                + '<div id="' + elemTableId + '" class="cv-elem-table-body" style="display:none">'
                + _sevHeaderHtml
                + '<table class="cv-ev-table"><thead><tr>'
                + '<th class="cv-ev-th cv-ev-th-label">Element</th>'
                + '<th class="cv-ev-th cv-ev-th-pill">Status</th>'
                + '<th class="cv-ev-th cv-ev-th-dots"></th>'
                + '<th class="cv-ev-th cv-ev-th-eval"></th>'
                + '<th class="cv-ev-th cv-ev-th-citation">Citation</th>'
                + '</tr></thead><tbody>' + rowsHtml + '</tbody></table>'
                + '</div>';
        }

        // Step 280: combined-line header — `LP-id  Name — Headline  [badge]`.
        // Mirrors the Step 279 single-line treatment in the four
        // PDF/DOCX renderers so the dashboard, sidebar, Synopsis, and
        // annotated artifacts all carry the same shape. Headline is
        // wrapped in its own span so CSS can style it (em-dash + muted
        // color); when headline is empty we omit the span entirely
        // rather than render a dangling em-dash.
        const headlineHtml = headline
            ? ` <span class="cv-item-headline-sep">—</span> <span class="cv-item-headline">${esc(headline)}</span>`
            : "";

        // Step 297c.3: jurisdiction escalation indicator
        const escalation = a.jurisdiction_escalation;
        let escalationHtml = "";
        if (escalation) {
            const stateLabel = STATE_FULL_NAMES[escalation.state] || escalation.state;
            escalationHtml = `<div class="cv-item-escalation" title="${esc(escalation.rationale || "")}"><span class="cv-escalation-badge">${esc(stateLabel)} rule</span><span class="cv-escalation-text">Escalated from ${esc(escalation.from)} to ${esc(escalation.to)}</span></div>`;
        }

        // Step 311: synthesis badge — if this LP is implicated in any CPF finding,
        // show the ↔ Synthesis badge that switches to the synthesis tab.
        const _cpfs = (pr && pr.cross_provision_findings) || [];
        const _cpfMatch = _cpfs.find(f => Array.isArray(f.implicated_lps) && f.implicated_lps.includes(pid));
        const _reliefMatch = _cpfs.find(f => f.finding_type === "cross_coverage_relief" && Array.isArray(f.implicated_lps) && f.implicated_lps.includes(pid));
        const synthBadgeHtml = _cpfMatch
            ? `<button class="cv-synthesis-badge" title="Appears in Contract Interaction Review: ${esc(_cpfMatch.headline || _cpfMatch.finding_id)}" onclick="event.stopPropagation();window.CAM.jumpToSynthesisFinding('${esc(pid)}','${esc(_cpfMatch.finding_id)}')" type="button">&#x21D4; Synthesis</button>`
            : "";
        const reliefBadgeHtml = _reliefMatch
            ? `<button class="cv-relief-badge" title="${esc(_reliefMatch.headline || 'Substance addressed elsewhere')}" onclick="event.stopPropagation();window.CAM.jumpToSynthesisFinding('${esc(pid)}','${esc(_reliefMatch.finding_id)}')" type="button">&#x2713; Addressed elsewhere</button>`
            : "";

        // Step 351: disagreement severity label beneath STATUS badge
        const _vd = a.verdict_distance;
        const _vdSev = _vd && _vd.severity;
        // Step 374K: honest containment — derived LP rollup, not a standalone evaluator conclusion.
        // Step 374V: on the consequence-not-assessed provenance state, name the badge for what the lawyer
        // must do (the consequence needs their judgment) rather than the generic "derived review signal".
        // Conditional on the same 374Q provenance flag; assessed cards keep "derived review signal". Copy only.
        const _disagBadgeText374V = _consNotAssessed374V ? 'Consequence requires attorney judgment' : 'derived review signal';
        const disagSeverityHtml = (_vdSev === 'moderate')
            ? '<span class="cv-disag-severity cv-disag-severity-moderate" title="Review signal derived from aggregated element verdicts (moderate distance) — not a standalone evaluator conclusion">〜 ' + _disagBadgeText374V + '</span>'
            : (_vdSev === 'severe')
            ? '<span class="cv-disag-severity cv-disag-severity-severe" title="Review signal derived from aggregated element verdicts — not a standalone evaluator conclusion; see element evidence">&#x26A0; ' + _disagBadgeText374V + '</span>'
            : '';

        // Step 356 Phase 3: dispute_signal badge
        const _dispCrit = a.elements_disputed_critical || 0;
        const _dispImp  = a.elements_disputed_important || 0;
        const disputeSignalHtml = _dispCrit > 0
            ? '<span class="cv-dispute-signal cv-dispute-signal-critical" title="' + _dispCrit + ' critical rubric element(s) disputed — LP reclassified to Review Needed">&#x2691; Critical Dispute</span>'
            : (_dispImp > 0
                ? '<span class="cv-dispute-signal cv-dispute-signal-important" title="Evaluator disagreement on ' + _dispImp + ' important element(s) — LP classification unaffected">Disputed</span>'
                : '');

        // Step 375G: CLIENT IMPACT block. PROMOTE existing fields only — no new prose, no model call.
        // Leads with use_impact.use_reasoning (the tenant-specific reason it matters, when present),
        // paired with the existing exposure_statement (consequence-of-inaction prose). Rendered at the
        // TOP of the card (under the title/badges, above the element evidence table) so judgment — why it
        // matters to THIS client — leads, instead of being a buried bottom footnote. When use_reasoning is
        // absent (the 72% with no Stage-5e use_impact) it shows ONLY the generic exposure_statement — NO
        // fabricated tenant-specific sentence. The element table + lease text stay fully visible below.
        // Pure layout/IA + footnote relocation — no count/routing/classifier/computed-value change.
        const _ciUi = a.use_impact;
        const _ciReason = (_ciUi && _ciUi.use_reasoning) ? String(_ciUi.use_reasoning).trim() : '';
        const _ciGap = normalizeUseConsequence(_ciUi) || '';
        const _ciReasonCls = _ciGap === 'beneficial' ? 'cv-ci-reason-favorable'
                           : (_ciGap === 'harmful' ? 'cv-ci-reason-adverse' : 'cv-ci-reason-neutral');
        const _ciParts = [];
        if (_ciReason) _ciParts.push('<div class="cv-ci-reason ' + _ciReasonCls + '">' + esc(_ciReason) + '</div>');
        if (stmt) _ciParts.push('<div class="cv-ci-exposure">' + esc(stmt) + ' ' + expProvenanceChip + '</div>');
        const clientImpactHtml = _ciParts.length
            ? '<div class="cv-client-impact"><div class="cv-client-impact-label">Client Impact</div>' + _ciParts.join('') + '</div>'
            : '';

        // Step 398 / 398b: Context Dependency signal strip — surfaces Stage 5e use_consequence=
        // "context_dependent" and the evaluator-agreement split when present.
        // use_reasoning is intentionally NOT reprinted here: 375G already renders it in the
        // "Client Impact" box above, so reprinting it here would duplicate user-facing content.
        // This block is a thin signal strip only: consequence tag + optional 1-1-1 split note.
        // Fires only when use_consequence === "context_dependent". Display only — no logic change.
        var _cdUi = a.use_impact;
        var _cdConsequence = normalizeUseConsequence(_cdUi) || '';
        var _cdAgreement = (_cdUi && _cdUi.evaluator_agreement) || '';
        var _cdIsContextDep = _cdConsequence === 'context_dependent';
        var contextDepHtml = '';
        if (_cdIsContextDep) {
            var _cdBody = _cdAgreement === '1-1-1'
                ? '<div class="cv-cd-split-note">Genuinely unsettled — could cut either way.</div>'
                : '<div class="cv-cd-consequence">Impact depends on your specific operations.</div>';
            contextDepHtml = '<div class="cv-context-dep"><div class="cv-context-dep-label">Depends on your use</div>' + _cdBody + '</div>';
        }

        // Step 400: materiality provenance
        var _matDefault = a.materiality || "";
        var _matAssessed = (a.use_impact && a.use_impact.materiality) || "";
        var matProvHtml = "";
        if (_matAssessed) {
            matProvHtml = '<div class="cv-mat-prov"><span class="cv-mat-prov-chip">Assessed materiality: ' + _matAssessed + '</span>';
            if (_matDefault && _matDefault !== _matAssessed) {
                matProvHtml += ' <span class="cv-mat-prov-chip cv-mat-default">Default: ' + _matDefault + '</span>';
            }
            matProvHtml += '</div>';
        } else if (_matDefault) {
            matProvHtml = '<div class="cv-mat-prov"><span class="cv-mat-prov-chip cv-mat-default">Default materiality: ' + _matDefault + '</span></div>';
        }

        return `<div class="cv-item cv-item-${tier}" data-pid="${esc(pid)}">
            <div class="cv-item-header">
                <span class="cv-item-id">${esc(pid)}</span>
                <span class="cv-item-name">${esc(name)}</span>${headlineHtml}
                <span class="cv-badge ${stateInfo.cls}">${stateInfo.label}</span>
                ${disagSeverityHtml}
                ${disputeSignalHtml}
                ${confidenceBadgeHtml}
                ${assessMethodHtml}
                ${pclsBadge}
                ${synthBadgeHtml}
                ${reliefBadgeHtml}
            </div>
            ${escalationHtml}
            ${clientImpactHtml}
            ${matProvHtml}
            ${contextDepHtml}
            ${leaseTextHtml}
            ${elementDetailHtml}
            ${state === 'missing'
              ? (tenantText
                  ? '<div class="cv-missing-provision-note cv-missing-gaps-note">⚠ This provision has significant gaps — key protections are missing.</div>'
                  : '<div class="cv-missing-provision-note">⚠ This provision is absent from the lease. Use <strong>Draft Missing Clause</strong> to request language from the landlord.</div>')
              : ''}
            ${missingHtml}
            ${nsHtml}
            ${toolbarHtml}
        </div>`;
    }

    const totalAttention = problems.length + review.length;
    const allGoodCount = [...covered, ...typical, ...other].length;
    // Expose _covResState for status filter function
    window._covResStateRef = _covResState;
    _coverageStatusFilter = 'all';

    let html = `<div class="coverage-summary-bar">
        <span class="coverage-summary-label">Show:</span>
        <button id="cv-stat-all" class="btn btn-outline cv-tier-btn cv-tier-btn-active" data-tier="all" onclick="window.CAM._applyCoverageTierFilter('all')">All</button>
        <button class="btn btn-outline cv-tier-btn" data-tier="problems" onclick="window.CAM._applyCoverageTierFilter('problems')">${problems.length} Need Attention</button>
        <button class="btn btn-outline cv-tier-btn" data-tier="review" onclick="window.CAM._applyCoverageTierFilter('review')">${review.length} Worth Reviewing</button>
        <button class="btn btn-outline cv-tier-btn" data-tier="covered" onclick="window.CAM._applyCoverageTierFilter('covered')">${allGoodCount} Covered</button>
        ${favorable.length > 0 ? `<button class="btn btn-outline cv-tier-btn cv-favorable-toggle-btn" onclick="window.CAM._applyCoverageFavorableToggle()">${favorable.length} Favorable &#9660;</button>` : ""}
        <span class="cv-filter-divider">|</span>
        <span class="coverage-summary-label">Status:</span>
        <button class="btn btn-outline cv-status-filter-btn cv-tier-btn-active" data-status="all" onclick="window.CAM._applyCoverageStatusFilter('all')">All</button>
        <button class="btn btn-outline cv-status-filter-btn" data-status="open" onclick="window.CAM._applyCoverageStatusFilter('open')">Unreviewed</button>
        <button class="btn btn-outline cv-status-filter-btn" data-status="flagged" onclick="window.CAM._applyCoverageStatusFilter('flagged')">Flagged</button>
        <button class="btn btn-outline cv-status-filter-btn" data-status="accepted" onclick="window.CAM._applyCoverageStatusFilter('accepted')">Accepted Risk</button>
        <button class="btn btn-outline cv-status-filter-btn" data-status="reviewed" onclick="window.CAM._applyCoverageStatusFilter('reviewed')">Reviewed</button>
        <span class="cv-filter-divider">|</span>
        <select id="cv-provision-select" class="cv-provision-select" onchange="window.CAM._applyCoverageProvisionFilter(this.value)">
            <option value="">All provisions</option>
            ${ca.map(function(a) {
                const pid = a.issue_area_id || a.provision_id || '';
                const name = a.issue_area_name || a.provision_name || pid;
                return '<option value="' + esc(pid) + '">' + esc(pid + ' ' + name) + '</option>';
            }).join('')}
        </select>
    </div>`;

    // Step 297c.1: Provision Conflicts section above issue area list
    if (_prConflicts.length > 0) {
        html += `<section class="cv-conflicts-section">
            <div class="cv-conflicts-header-row">
                <h3 class="cv-conflicts-header">Provision Conflicts (${_prConflicts.length})</h3>
                <p class="cv-conflicts-intro">The following pairs of provisions create internal conflicts within the lease. Each implicates multiple issue areas at once.</p>
            </div>
            ${_prConflicts.map(c => {
                const severityClass = `cv-conflict-${c.severity || "medium"}`;
                const severityLabel = (c.severity || "medium").toUpperCase();
                const lpLinks = (c.lps_implicated || []).map(lp =>
                    `<a class="cv-conflict-lp-link" href="javascript:void(0)" onclick="window.CAM.jumpToCoverageProvision && window.CAM.jumpToCoverageProvision('${esc(lp)}'); return false;">${esc(lp)}</a>`
                ).join(", ");
                return `<div class="cv-conflict-card ${severityClass}">
                    <div class="cv-conflict-header">
                        <span class="cv-conflict-id">${esc(c.id || "")}</span>
                        <span class="cv-conflict-name">${esc(c.name || "")}</span>
                        <span class="cv-conflict-severity-badge">${severityLabel}</span>
                    </div>
                    <div class="cv-conflict-lps">Implicates: ${lpLinks}</div>
                    <div class="cv-conflict-description">${esc(c.description || "")}</div>
                </div>`;
            }).join("")}
        </section>`;
    }

    if (totalAttention === 0) {
        html += '<div class="coverage-all-clear">\u2705 No high-priority gaps detected across all material issue areas.</div>';
    }

    if (problems.length > 0) {
        html += `<div class="cv-section" id="cv-section-problems"><div class="cv-section-header cv-section-problems">Needs Attention (${problems.length})</div>${problems.map(a => buildItem(a, "problem")).join("")}</div>`;
    }
    if (review.length > 0) {
        html += `<div class="cv-section" id="cv-section-review"><div class="cv-section-header cv-section-review">Worth Reviewing (${review.length})</div>${review.map(a => buildItem(a, "review")).join("")}</div>`;
    }
    if (favorable.length > 0) {
        html += `<div class="cv-section" id="cv-section-favorable" style="display:none"><div class="cv-section-header cv-section-favorable">Favorable to You (${favorable.length})</div>${favorable.map(a => buildItem(a, "favorable")).join("")}</div>`;
    }

    const allGood = [...covered, ...typical, ...other];
    if (allGood.length > 0) {
        html += `<div class="cv-section" id="cv-section-covered">
            <div class="cv-section-header cv-section-ok" style="cursor:pointer" onclick="
                var list=document.getElementById('cv-ok-list');
                var arrow=document.getElementById('cv-ok-arrow');
                if(list){list.classList.toggle('hidden');}
                if(arrow){arrow.textContent=list&&list.classList.contains('hidden')?'\u25B6':'\u25BC';}
            ">
                <span id="cv-ok-arrow">\u25B6</span> Adequately Covered (${allGood.length}) <span class="cv-section-toggle-hint">click to expand</span>
            </div>
            <div id="cv-ok-list" class="hidden">${allGood.map(a => buildItem(a, "ok")).join("")}</div>
        </div>`;
    }

    tab.innerHTML = html;
}
// ── Coverage resolution state (separate from deviation resolutionState) ──
// Keyed by 'cov:tenantIdx:pid' to avoid collision with deviation workflow
const _covResState = {};

function _getCovRes(tenantIdx, pid) {
    const key = 'cov:' + tenantIdx + ':' + pid;
    return _covResState[key] || { status: 'open', notes: [] };
}

function _setCovStatus(pid, tenantIdx, status) {
    const key = 'cov:' + tenantIdx + ':' + pid;
    if (!_covResState[key]) _covResState[key] = { status: 'open', notes: [] };
    // Toggle: clicking active status resets to open
    const newStatus = (_covResState[key].status === status) ? 'open' : status;
    _covResState[key].status = newStatus;
    // Update pills in DOM
    document.querySelectorAll(`.cov-pill[data-pid="${pid}"][data-tenant-idx="${tenantIdx}"]`).forEach(btn => {
        btn.classList.toggle('cov-pill-active', btn.dataset.status === newStatus);
    });
    // Persist to server
    if (currentJobId) {
        fetch(`/api/jobs/${currentJobId}/cov-resolution`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tenant_idx: tenantIdx, provision_id: pid, status: newStatus }),
        }).catch(() => {}); // silent failure
    }
}

function _toggleCovNotes(pid, tenantIdx) {
    const panel = document.getElementById('cov-notes-' + tenantIdx + '-' + pid);
    if (panel) panel.classList.toggle('hidden');
}

function _saveCovNote(pid, tenantIdx) {
    const input = document.getElementById('cov-note-input-' + tenantIdx + '-' + pid);
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    const key = 'cov:' + tenantIdx + ':' + pid;
    if (!_covResState[key]) _covResState[key] = { status: 'open', notes: [] };
    _covResState[key].notes.push({ text: text, timestamp: new Date().toISOString() });
    input.value = '';
    _renderCovNotes(pid, tenantIdx);
    _updateCovNoteCount(pid, tenantIdx);
}

function _deleteCovNote(pid, tenantIdx, noteIdx) {
    const key = 'cov:' + tenantIdx + ':' + pid;
    if (_covResState[key] && _covResState[key].notes) {
        _covResState[key].notes.splice(noteIdx, 1);
        _renderCovNotes(pid, tenantIdx);
        _updateCovNoteCount(pid, tenantIdx);
    }
}

function _renderCovNotes(pid, tenantIdx) {
    const panel = document.getElementById('cov-notes-' + tenantIdx + '-' + pid);
    if (!panel) return;
    const key = 'cov:' + tenantIdx + ':' + pid;
    const notes = (_covResState[key] || {}).notes || [];
    const inputRow = panel.querySelector('.cov-note-input-row');
    panel.querySelectorAll('.cov-note-entry').forEach(el => el.remove());
    notes.forEach((note, noteIdx) => {
        const div = document.createElement('div');
        div.className = 'cov-note-entry';
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'res-note-delete';
        deleteBtn.textContent = 'Delete';
        const _pid = pid, _ti = tenantIdx, _ni = noteIdx;
        deleteBtn.onclick = function(e) { e.stopPropagation(); window.CAM._deleteCovNote(_pid, _ti, _ni); };
        const tsSpan = document.createElement('span');
        tsSpan.className = 'res-note-ts';
        tsSpan.textContent = formatResTimestamp(note.timestamp);
        const textSpan = document.createElement('span');
        textSpan.className = 'res-note-text';
        textSpan.textContent = note.text;
        div.appendChild(tsSpan);
        div.appendChild(textSpan);
        div.appendChild(deleteBtn);
        if (inputRow) panel.insertBefore(div, inputRow);
        else panel.appendChild(div);
    });
}
function _updateCovNoteCount(pid, tenantIdx) {
    const btn = document.querySelector('.cov-notes-btn[data-pid="' + pid + '"][data-tenant-idx="' + tenantIdx + '"]');
    if (!btn) return;
    const key = 'cov:' + tenantIdx + ':' + pid;
    const count = ((_covResState[key] || {}).notes || []).length;
    btn.innerHTML = '📝 Notes' + (count > 0 ? ' <span class="res-note-count">' + count + '</span>' : '');
}

let _coverageTierFilter = 'all';
let _coverageStatusFilter = 'all'; // 'all' | 'open' | 'flagged' | 'accepted' | 'reviewed'
let _cvShowFavorable = false;    // Step 297d.J: toggle for viewer-favorable provisions
let _coverageProvisionFilter = ''; // '' = all; LP-XX = show only that LP

function _applyCoverageProvisionFilter(pid) {
    _coverageProvisionFilter = pid;
    const sel = document.getElementById('cv-provision-select');
    if (sel) sel.value = _coverageProvisionFilter;
    document.querySelectorAll('.cv-item').forEach(function(item) {
        if (!_coverageProvisionFilter) {
            item.classList.remove('cv-prov-hidden');
        } else {
            item.classList.toggle('cv-prov-hidden', item.dataset.pid !== _coverageProvisionFilter);
        }
    });
    // Reveal the matched item if it was inside a hidden tier section
    if (_coverageProvisionFilter) {
        const target = document.querySelector('.cv-item[data-pid="' + CSS.escape(_coverageProvisionFilter) + '"]');
        if (target) {
            const hiddenParent = target.closest('.hidden');
            if (hiddenParent) hiddenParent.classList.remove('hidden');
            setTimeout(function() { scrollResultsTargetIntoView(target, 8); }, 100);
        }
    }
}
window.CAM._applyCoverageProvisionFilter = _applyCoverageProvisionFilter;

function _applyCoverageStatusFilter(status) {
    _coverageStatusFilter = (_coverageStatusFilter === status) ? 'all' : status;
    // Update button active states
    document.querySelectorAll('.cv-status-filter-btn').forEach(btn => {
        btn.classList.toggle('cv-tier-btn-active', btn.dataset.status === _coverageStatusFilter);
    });
    // Show/hide items based on status
    const tenantIdx = currentTenantIndex;
    document.querySelectorAll('.cv-item').forEach(item => {
        const pid = item.dataset.pid;
        if (!pid || _coverageStatusFilter === 'all') {
            item.classList.remove('hidden');
            return;
        }
        const key = 'cov:' + tenantIdx + ':' + pid;
        const itemStatus = (window._covResStateRef && window._covResStateRef[key] || {}).status || 'open';
        item.classList.toggle('hidden', itemStatus !== _coverageStatusFilter);
    });
}

function _applyCoverageTierFilter(tier) {
    _coverageTierFilter = (_coverageTierFilter === tier) ? 'all' : tier;
    const sections = {
        problems: document.getElementById('cv-section-problems'),
        review:   document.getElementById('cv-section-review'),
        covered:  document.getElementById('cv-section-covered'),
    };
    const all = _coverageTierFilter === 'all';
    Object.entries(sections).forEach(([key, el]) => {
        if (!el) return;
        el.classList.toggle('hidden', !all && _coverageTierFilter !== key);
    });
    document.querySelectorAll('.cv-tier-btn').forEach(btn => {
        const isActive = btn.dataset.tier === _coverageTierFilter;
        btn.classList.toggle('cv-tier-btn-active', isActive);
    });
}

function _applyCoverageFavorableToggle() {
    _cvShowFavorable = !_cvShowFavorable;
    const section = document.getElementById('cv-section-favorable');
    if (section) section.style.display = _cvShowFavorable ? '' : 'none';
    document.querySelectorAll('.cv-favorable-toggle-btn').forEach(btn => {
        btn.classList.toggle('cv-tier-btn-active', _cvShowFavorable);
    });
}

window.CAM = window.CAM || {};
window.CAM.renderCoveragePanel = renderCoveragePanel;
window.CAM._applyCoverageTierFilter = _applyCoverageTierFilter;
window.CAM._applyCoverageFavorableToggle = _applyCoverageFavorableToggle;
function _openCovAdvisor(pid, tenantIdx, provName, stmt, isMissing) {
    let question;
    if (isMissing) {
        question = 'The ' + provName + ' clause is completely absent from this lease. ' +
            (stmt ? 'The risk is: ' + stmt + ' ' : '') +
            'What standard language should I request the landlord include, and what are the most important terms to negotiate for this provision?';
    } else {
        question = 'I\'m reviewing the ' + provName + ' provision. ' +
            (stmt ? 'Coverage analysis: ' + stmt + ' ' : '') +
            'What should I negotiate or flag for this clause?';
    }
    if (typeof askAboutFinding === 'function') {
        askAboutFinding(pid, Number(tenantIdx), question, 'coverage');
    }
}
window.CAM._setCovStatus = _setCovStatus;

function jumpToCoverageProvision(pid, opts) {
    // Reset tier filter so the item is visible regardless of current filter
    _coverageTierFilter = 'all';
    switchResultsTab('coverage');
    const expandElements = opts && opts.expandElements;
    waitForResultsTarget(function() {
        const el = document.querySelector('.cv-item[data-pid="' + CSS.escape(pid) + '"]');
        return el;
    }, { attempts: 25, delay: 100 }).then(function(el) {
        if (!el) return;
        // cv-section-favorable uses style="display:none" (not class), so closest('.hidden')
        // misses it. Reveal it first so getBoundingClientRect() works in the scroll below.
        const favSection = document.getElementById('cv-section-favorable');
        if (favSection && favSection.contains(el) && favSection.style.display === 'none') {
            favSection.style.display = '';
            _cvShowFavorable = true;
            document.querySelectorAll('.cv-favorable-toggle-btn').forEach(function(btn) {
                btn.classList.add('cv-tier-btn-active');
            });
        }
        // cv-ok-list uses class hidden \u2014 reveal and update the section arrow.
        // Must check this BEFORE the general closest('.hidden') call, otherwise
        // closest removes hidden first and the okList.contains check becomes false.
        const okList = document.getElementById('cv-ok-list');
        if (okList && okList.classList.contains('hidden') && okList.contains(el)) {
            okList.classList.remove('hidden');
            const arrow = document.getElementById('cv-ok-arrow');
            if (arrow) arrow.textContent = '\u25BC';
        } else {
            // General: reveal any other class-hidden ancestor (e.g. tier-filtered section)
            const hiddenParent = el.closest('.hidden');
            if (hiddenParent) hiddenParent.classList.remove('hidden');
        }
        // Auto-expand element table when navigating directly (e.g. via sidebar click)
        if (expandElements) {
            const elemBody = document.getElementById('cv-elem-body-' + CSS.escape(pid));
            if (elemBody && elemBody.style.display === 'none') {
                elemBody.style.display = 'block';
                const summaryRow = elemBody.previousElementSibling;
                if (summaryRow) {
                    const chev = summaryRow.querySelector('.cv-elem-chevron');
                    if (chev) chev.textContent = '\u25BE';
                }
            }
        }
        setTimeout(function() {
            scrollResultsTargetIntoView(el, 8);
            flashResultsTarget(el, 2000);
        }, 150);
    });
}
window.CAM._toggleConformingChips = function(btn, e) {
    if (e) e.stopPropagation();
    var row = btn.closest('.conforming-chip-row');
    if (!row) return;
    var chips = row.querySelector('.conforming-chips');
    if (!chips) return;
    chips.classList.toggle('hidden');
    var count = row.querySelectorAll('.chip-jumpable').length;
    btn.textContent = chips.classList.contains('hidden')
        ? '✓ ' + count + ' conforming'
        : '∨ Hide conforming';
};
// Step 299 fix: navigate heatmap cell to the correct contract then the correct LP.
// openContractDetail sets currentTenantIndex and re-renders the detail view,
// then jumpToCoverageProvision switches to the Coverage & Gaps tab and scrolls.
function jumpHeatmapCell(tIdx, pid) {
    openContractDetail(tIdx).then(function() {
        jumpToCoverageProvision(pid, { expandElements: true });
    });
}
window.CAM.switchResultsTab = switchResultsTab;
window.CAM.jumpToCoverageProvision = jumpToCoverageProvision;
window.CAM.navToSynthesis = function(tIdxStr) {
    var idx = parseInt(tIdxStr, 10);
    if (isNaN(idx)) idx = currentTenantIndex;
    openContractDetail(idx).then(function() { switchResultsTab('synthesis'); });
};
window.CAM.jumpHeatmapCell = jumpHeatmapCell;
window.CAM._toggleCovNotes = _toggleCovNotes;
window.CAM._saveCovNote = _saveCovNote;
window.CAM._deleteCovNote = _deleteCovNote;
window.CAM._openCovAdvisor = _openCovAdvisor;
window.CAM.openDocviewSummary = openDocviewSummary;
window.CAM.jumpToDocview = jumpToDocview;
window.CAM.jumpToAuditProvision = jumpToAuditProvision;
window.CAM._applyCoverageTierFilter = _applyCoverageTierFilter;
window.CAM._applyCoverageStatusFilter = _applyCoverageStatusFilter;
window.CAM.renderCoveragePanel = renderCoveragePanel;

// ══════════════════════════════════════════════════════
// Step 264: Unified left-sidebar enrichment (Mode A + Mode C)
//
// Both modes share one item layout: provision/area ID + name + state-or-
// severity badge + truncated risk descriptor. Mode A pulls from
// provisions[].final_verdict === "DEVIATES" (existing deviation workflow).
// Mode C pulls from coverage_assessment[] (Phase 5 Coverage & Exposure).
//
// These function declarations are intentionally placed at the END of the
// IIFE: in JS, when two `function` declarations share a name in the same
// scope, the LATER one wins after hoisting. This lets us override the
// earlier renderNavSidebar/updateNavActive without reading or removing them.
// ══════════════════════════════════════════════════════

// Step 264.1: prefer truncating at a sentence boundary within `max` chars.
// Walks backward looking for `.`, `!`, or `?` followed by a space (or end of
// slice). The trailing-space check avoids matching mid-abbreviation cases
// like "e.g." or "U.S." Falls back to clean word-boundary truncation with an
// ellipsis if no sentence boundary is found. Mid-word cuts are never
// produced — the descriptor always ends at clean punctuation or whitespace.
//
// Step 264.2: defensive sanitizer for existing data with pipeline truncation
// artifacts. The pipeline bug (in lease_exposure.py, fixed in 264.2) used
// `statement.split('.')` which shattered abbreviations — producing endings
// like "...default. (e." or "...default. (e. g." Strip those before
// truncation so historical runs render cleanly without re-processing.
function _navSanitize(s) {
    if (!s) return s;
    let result = String(s).trim();
    // Pattern A: trailing parenthetical abbreviation — " (e. g.", " (e.g.",
    // " (e.", " (i. e.", " (i.". Requires opening paren so we don't strip
    // legitimate sentence endings.
    result = result.replace(/\s+\(\s*[a-zA-Z]\.\s*([a-zA-Z]\.?)?\s*$/, "");
    // Pattern B: trailing bare abbreviation without paren — " e. g.", " e.g."
    result = result.replace(/\s+[a-zA-Z]\.\s+[a-zA-Z]\.?\s*$/, "");
    // Strip any dangling open paren or trailing comma left behind
    result = result.replace(/[(,\s]+$/, "").trim();
    // If we changed the string and it doesn't end in sentence punctuation,
    // append a period for a clean ending.
    if (result !== String(s).trim() && result && !/[.!?]$/.test(result)) {
        result += ".";
    }
    return result || String(s);
}

function _navTruncate(s, max) {
    if (!s) return "";
    s = _navSanitize(String(s).trim());
    if (s.length <= max) return s;
    const slice = s.slice(0, max);
    let cut = -1;
    for (let i = slice.length - 1; i >= 40; i--) {
        const ch = slice[i];
        if (ch === "." || ch === "!" || ch === "?") {
            const next = slice[i + 1];
            if (next === undefined || next === " ") {
                cut = i + 1;
                break;
            }
        }
    }
    if (cut > 0) {
        return s.slice(0, cut);
    }
    const wordEnd = slice.lastIndexOf(" ");
    if (wordEnd >= 40) {
        return s.slice(0, wordEnd).trimEnd() + "\u2026";
    }
    return s.slice(0, max - 1).trimEnd() + "\u2026";
}

function _navBuildModeAItem(d, tIdx) {
    const pid = d.provision_id || "";
    const name = d.provision_name || pid || "Unnamed provision";
    const sev = (d.severity || "MEDIUM").toUpperCase();
    const desc = (d.risk_headline || d.challenge_details || d.summary || "").trim();
    const truncDesc = _navTruncate(desc, 180);
    const sevLabel = sevDisplay(sev);
    const sevCls = sev.toLowerCase();
    return '<button class="nav-item-enriched nav-item-sev-' + sevCls + '" data-pid="' + esc(pid) + '" data-tenant-idx="' + tIdx + '" data-mode="a" title="' + esc(desc || name) + '">'
         +   '<div class="nav-item-top">'
         +     '<span class="nav-item-id">' + esc(pid) + '</span>'
         +     '<span class="nav-item-name">' + esc(name) + '</span>'
         +     '<span class="nav-item-badge nav-badge-' + sevCls + '">' + esc(sevLabel) + '</span>'
         +   '</div>'
         +   (truncDesc ? '<div class="nav-item-desc">' + esc(truncDesc) + '</div>' : "")
         + '</button>';
}

function _navBuildModeCItem(a, tIdx) {
    const pid = a.issue_area_id || a.provision_id || "";
    const name = a.issue_area_name || a.provision_name || pid || "Unnamed area";
    const state = a.coverage_state || "";
    const pcls = a.partial_class || "";
    const stmt = (a.exposure_statement || a.exposure || "").trim();
    // Step 278: prefer the upstream-attached headline (model-path JSON
    // envelope or schema-path deterministic extraction). Fall back to
    // a JS-side semicolon/sentence split if a result dict predates
    // Step 278 — this keeps every Mode C render consistent without
    // requiring a backend re-run for cached jobs. The full prose is
    // still kept on the title attribute for hover.
    const headline = (a.exposure_headline || _deriveHeadlineFromExposure(stmt)).trim();
    const _navViewerPerspective = getJobPerspective();
    const _navIsFavorable = state === "covered_unfavorable" &&
        _navViewerPerspective && _navViewerPerspective !== "neutral" &&
        a.covered_unfavorable_adverse_to &&
        a.covered_unfavorable_adverse_to !== _navViewerPerspective;
    let badgeLabel, badgeCls;
    if (_navIsFavorable) {
        badgeLabel = "FAVORABLE"; badgeCls = "nav-badge-favorable";
    } else if (state === "potentially_unenforceable") {
        badgeLabel = "ENFORCEABILITY"; badgeCls = "nav-badge-enforceability";
    } else if (state === "covered_unfavorable") {
        const isNeutral = !_navViewerPerspective || _navViewerPerspective === "neutral";
        badgeLabel = isNeutral ? "ASYMMETRIC" : "Unfavorable";
        badgeCls   = isNeutral ? "nav-badge-asymmetric" : "nav-badge-unfavorable";
    } else if (state === "missing") {
        badgeLabel = "Missing"; badgeCls = "nav-badge-missing";
    } else if (pcls === "partial_material") {
        badgeLabel = "Partial"; badgeCls = "nav-badge-partial-material";
    } else if (pcls === "partial_review") {
        badgeLabel = "Review"; badgeCls = "nav-badge-partial-review";
    } else {
        badgeLabel = state || "—"; badgeCls = "nav-badge-default";
    }
    // Steps 307b/315: derive governance signal for confidence label.
    // Show for every LP that has element_verdicts — same derivation as buildItem().
    var _navEvs = a.element_verdicts || [];
    var _navGovSig = _navEvs.length > 0 ? deriveCoverageGovernanceSignal(_navEvs) : null;
    var _navConfFallback = { ASSERT_SIGNAL: "Verified", ASSERT_REVIEW_SIGNAL: "Impact Unclear", REVIEW_SIGNAL: "Needs Review", WITHHOLD_SIGNAL: "Inconclusive" };
    var _navConfLabel = _navGovSig
        ? ((window.CAMAuditShared && window.CAMAuditShared.getSidebarConfidenceLabel)
            ? window.CAMAuditShared.getSidebarConfidenceLabel(_navGovSig)
            : _navConfFallback[_navGovSig] || null)
        : null;
    var _navEvidSumm = a.evidence_summary || '';
    // Step 339: show confidence dots (●●●●) instead of text label; full label in tooltip.
    var confLabelHtml = _navGovSig
        ? _navConfDotsHtml(_navGovSig, 'Confidence: ' + (_navConfLabel || _navGovSig))
        : (!_navGovSig && !_navEvidSumm.includes('Step 305'))
            ? '<span class="nav-item-conf nav-item-conf-preclass">Extraction-based</span>'
            : '';
    // Issue 4: build richer hover tooltip — exposure statement + missing elements summary.
    const _keyMissing = (a.key_missing || []).slice(0, 3);
    const _missingLine = _keyMissing.length > 0 ? 'Missing: ' + _keyMissing.join('; ') : '';
    const _tooltipParts = [stmt.slice(0, 320), _missingLine].filter(Boolean);
    const _navItemTooltip = _tooltipParts.join(' | ') || name;
    return '<button class="nav-item-enriched" data-pid="' + esc(pid) + '" data-tenant-idx="' + tIdx + '" data-mode="c" title="' + esc(_navItemTooltip) + '">'
         +   '<div class="nav-item-top">'
         +     '<span class="nav-item-id">' + esc(pid) + '</span>'
         +     '<span class="nav-item-name">' + esc(name) + '</span>'
         +     '<span class="nav-item-badge ' + badgeCls + '">' + esc(badgeLabel) + '</span>'
         +     confLabelHtml
         +   '</div>'
         +   (headline ? '<div class="nav-item-desc">' + esc(headline) + '</div>' : "")
         + '</button>';
}

// Step 313: agreement badge for CPF findings — "N of 3 evaluators" with color coding.
function _synthAgreementBadge(agreementStr) {
    const parts = (agreementStr || "").split("-");
    const reported = parseInt(parts[0], 10) || 0;
    const cls = reported === 3 ? "cpf-agree-unanimous"
               : reported === 2 ? "cpf-agree-majority"
               : reported === 1 ? "cpf-agree-minority"
               : "cpf-agree-none";
    const label = reported === 3 ? "✓ Unanimous · 3 of 3"
                : reported === 2 ? "2 of 3 evaluators"
                : reported === 1 ? "⚠ Minority · 1 of 3"
                : "Not confirmed";
    return `<span class="cpf-agree-badge ${cls}" title="Evaluator agreement">${esc(label)}</span>`;
}

// Step 311: render the Contract Interaction Review tab from cross_provision_findings[].
function _detectRootCauseGroups(compoundFindings) {
    const lpCount = {};
    compoundFindings.forEach(function(f) {
        (f.implicated_lps || []).forEach(function(lp) {
            lpCount[lp] = (lpCount[lp] || 0) + 1;
        });
    });
    return Object.entries(lpCount)
        .filter(function(e) { return e[1] >= 2; })
        .sort(function(a, b) { return b[1] - a[1]; })
        .map(function(e) { return e[0]; });
}

function _rootCauseLabel(rootLpId, coverageAssessment) {
    const lp = (coverageAssessment || []).find(function(a) { return a.issue_area_id === rootLpId; });
    if (!lp) return rootLpId + " absent";
    const name  = lp.issue_area_name || rootLpId;
    const state = lp.coverage_state;
    if (state === "missing")  return "No " + name.toLowerCase() + " framework";
    if (state === "partial")  return "Incomplete " + name.toLowerCase() + " framework";
    return name + " gap";
}

function renderSynthesisPanel() {
    const tab = $("#synthesis-tab");
    if (!tab) return;

    const tenantIdx = currentTenantIndex;
    const tenant = (currentResults && currentResults.tenants) ? currentResults.tenants[tenantIdx] : null;
    const pr = tenant && tenant.results ? tenant.results : null;
    const cpfs = (pr && pr.cross_provision_findings) ? pr.cross_provision_findings : null;

    if (!cpfs || cpfs.length === 0) {
        tab.innerHTML = '<div class="coverage-empty"><p>No contract interaction findings available for this run. This tab populates after a fresh analysis.</p></div>';
        return;
    }

    const FTYPE_LABEL = {
        "cross_coverage_gap":    "Cross-Coverage Gap",
        "directional_mismatch":  "Directional Mismatch",
        "compound_risk":         "Compound Risk",
        "cross_coverage_relief": "Cross-Coverage Relief",
    };
    const SEV_CLS = {
        "HIGH":   "cv-badge-missing",
        "MEDIUM": "cv-badge-partial",
        "LOW":    "cv-badge-ok",
        "INFO":   "cpf-relief-badge",
    };

    function buildCpfCard(f) {
        const fid      = f.finding_id || "";
        const ftype    = f.finding_type || "cross_coverage_gap";
        const ftLabel  = FTYPE_LABEL[ftype] || ftype;
        const implicated = (f.implicated_lps || []);
        const heading  = cpfTitle(f);
        const headline = (f.headline || "").trim();
        const detail   = (f.detail || "").trim();
        const cited    = (f.cited_sections || []);
        const sev      = (f.severity || "MEDIUM").toUpperCase();
        const sevCls   = SEV_CLS[sev] || "cv-badge-na";
        const agree    = f.evaluator_agreement || "";
        const evVerd   = f.evaluator_verdicts || {};
        const safeId   = fid.replace(/[^a-zA-Z0-9_-]/g, '_');

        const lpPills = implicated.map(lpId =>
            `<button class="cpf-lp-pill" onclick="switchResultsTab('coverage');setTimeout(function(){window.CAM.jumpToCoverageProvision&&window.CAM.jumpToCoverageProvision('${esc(lpId)}');},120);" type="button">${esc(lpId)}</button>`
        ).join(" ");

        const citedHtml = cited.length > 0
            ? '<div class="cpf-cited"><span class="cpf-cited-label">Cited:</span> ' + cited.map(s => `<span class="cpf-cited-section">${esc(s)}</span>`).join(" ") + '</div>'
            : "";

        const agreeHtml = _synthAgreementBadge(agree);
        const evLines = Object.entries(evVerd).map(([role, v]) =>
            `<span class="cpf-ev-verdict"><strong>${esc(role)}</strong>: ${esc(v)}</span>`
        ).join("  ");
        const reportedCount = parseInt((agree || "0").split("-")[0], 10) || 0;
        const minorityNote = reportedCount === 1
            ? '<div class="cpf-minority-note">One evaluator identified this interaction. The other two did not flag it independently. Review the cited sections to assess whether the risk applies to this lease.</div>'
            : "";

        const dirNote = (ftype === "directional_mismatch" && f.directionality)
            ? `<div class="cpf-directionality"><span class="cpf-dir-label">Directionality:</span> ${esc(f.directionality.replace(/_/g, " "))}</div>`
            : "";

        const reliefNote = (ftype === "cross_coverage_relief" && f.relief_section)
            ? `<div class="cpf-relief-section"><span class="cpf-dir-label">Found in:</span> ${esc(f.relief_section)}</div>`
            : "";

        return `<div class="cpf-card cpf-type-${esc(ftype)}" id="cpf-${esc(safeId)}" data-finding-id="${esc(fid)}" data-lps="${esc(implicated.join(','))}">
            <div class="cpf-card-header">
                <span class="cpf-finding-id">${esc(fid)}</span>
                <span class="cpf-type-label">${esc(ftLabel)}</span>
                <span class="cv-badge ${sevCls}">${sev}</span>
                ${agreeHtml}
            </div>
            <div class="cpf-lps">${lpPills}</div>
            ${heading ? `<div class="cpf-headline">${esc(heading)}</div>` : ""}
            ${(headline && headline !== heading) ? `<div class="cpf-detail">${esc(headline)}</div>` : ""}
            ${detail   ? `<div class="cpf-detail">${esc(detail)}</div>` : ""}
            ${dirNote}
            ${reliefNote}
            ${citedHtml}
            ${evLines ? `<div class="cpf-ev-row">${evLines}</div>` : ""}
            ${minorityNote}
        </div>`;
    }

    const reliefs    = cpfs.filter(f => f.finding_type === "cross_coverage_relief");
    const mismatches = cpfs.filter(f => f.finding_type === "directional_mismatch");
    const compounds  = cpfs.filter(f => f.finding_type === "compound_risk");
    const gaps       = cpfs.filter(f => f.finding_type === "cross_coverage_gap");

    let html = '<div class="synthesis-panel">';
    html += '<div class="synthesis-intro"><p>This review asks three questions across the full contract: where is the missing protection actually hiding, which direction does it run, and what happens when multiple gaps combine?</p></div>';

    if (reliefs.length > 0) {
        html += '<div class="cpf-group cpf-group-relief"><div class="cpf-group-header cpf-group-header-relief">Cross-Coverage Relief <span class="nav-section-count">' + reliefs.length + '</span></div>';
        reliefs.forEach(function(f) { html += buildCpfCard(f); });
        html += '</div>';
    }
    // Step 370a: Directional Synthesis Completeness Guard. When synthesis flagged the
    // directional pass as incomplete (large flagged-LP set + near-empty Pass-1 candidate
    // set), do NOT let an empty/thin directional section read as a clean all-clear.
    // Surface a Needs Review banner at the top of the directional area and still show
    // whatever directional findings were returned.
    const _synMeta = (pr && pr._stage_data && pr._stage_data.synthesis_meta)
                  || (pr && pr.synthesis_meta) || {};
    const _dirIncomplete = _synMeta.directional_synthesis_status === 'incomplete_low_candidate_anomaly';
    if (_dirIncomplete || mismatches.length > 0) {
        html += '<div class="cpf-group">';
        if (_dirIncomplete) {
            html += '<div class="cpf-dir-incomplete" role="alert">'
                 +    '<div class="cpf-dir-incomplete-tag">⚠ Needs Review</div>'
                 +    '<div class="cpf-dir-incomplete-msg">Directional synthesis produced an unusually low candidate set relative to the analyzed issue volume. One-sided-term review may be incomplete.</div>'
                 +  '</div>';
        }
        html += '<div class="cpf-group-header">Directional Mismatches <span class="nav-section-count">' + mismatches.length + '</span></div>';
        mismatches.forEach(f => { html += buildCpfCard(f); });
        html += '</div>';
    }
    if (compounds.length > 0) {
        html += '<div class="cpf-group"><div class="cpf-group-header">Compound Risks <span class="nav-section-count">' + compounds.length + '</span></div>';
        const rootCauses = _detectRootCauseGroups(compounds);
        const coverageAssessment = (pr && pr.coverage_assessment) || [];
        if (rootCauses.length > 0 && compounds.length >= 2) {
            var renderedIds = {};
            rootCauses.forEach(function(rootLp) {
                var grouped = compounds.filter(function(f) {
                    return (f.implicated_lps || []).indexOf(rootLp) !== -1;
                });
                grouped.forEach(function(f) { renderedIds[f.finding_id || ""] = true; });
                var label = esc(_rootCauseLabel(rootLp, coverageAssessment));
                html += '<div class="cpf-root-group">';
                html += '<div class="cpf-root-header">'
                    + '<span class="cpf-root-label">ROOT EXPOSURE</span>'
                    + '<span class="cpf-root-theme">' + label + '</span>'
                    + '<span class="cpf-root-count">' + grouped.length + ' compound risk finding' + (grouped.length !== 1 ? 's' : '') + '</span>'
                    + '</div>';
                html += '<div class="cpf-root-findings">';
                grouped.forEach(function(f) { html += buildCpfCard(f); });
                html += '</div></div>';
            });
            // Render any compound findings not captured by a root cause group
            compounds.forEach(function(f) {
                if (!renderedIds[f.finding_id || ""]) { html += buildCpfCard(f); }
            });
        } else {
            compounds.forEach(function(f) { html += buildCpfCard(f); });
        }
        html += '</div>';
    }
    if (gaps.length > 0) {
        html += '<div class="cpf-group"><div class="cpf-group-header">Cross-Coverage Gaps <span class="nav-section-count">' + gaps.length + '</span></div>';
        gaps.forEach(f => { html += buildCpfCard(f); });
        html += '</div>';
    }

    html += '</div>';
    tab.innerHTML = html;
}

window.CAM.renderSynthesisPanel = renderSynthesisPanel;

// ── Step 359: Contract View Panel ──────────────────────────────────────────
// Renders the contract_section_index from pipeline_results as a
// hierarchical article → section → findings view.

function renderContractViewPanel() {
    var tab = document.getElementById('contractview-tab');
    if (!tab) return;

    var tenantIdx = currentTenantIndex;
    var tenant = (currentResults && currentResults.tenants) ? currentResults.tenants[tenantIdx] : null;
    var pr = tenant && tenant.results ? tenant.results : null;
    if (!pr) return;

    var idx = pr.contract_section_index;
    if (!idx || !Array.isArray(idx) || idx.length === 0) {
        tab.innerHTML = '<div class="cv-empty" style="padding:2rem;text-align:center;color:var(--text-muted,#888)">' +
            '<p style="font-size:1rem;margin-bottom:.5rem">Contract View is not available for this analysis.</p>' +
            '<p style="font-size:.875rem">Re-run the analysis to generate the contract section index.</p>' +
            '</div>';
        return;
    }

    // Bucket display config
    var BUCKET_ICON = { risk: '🔴', review_needed: '🟠', improvement: '🔵', addressed: '✅' };
    var BUCKET_LABEL = { risk: 'Risk', review_needed: 'Review Needed', improvement: 'Improvement', addressed: 'Addressed' };

    // Helper: compare section keys numerically ("3.1" < "3.2" < "3.10" < "15.1")
    function compareSectionKeys(a, b) {
        var parseKey = function(k) { return (k || '').split('.').map(function(p) { return parseInt(p, 10) || 0; }); };
        var aParts = parseKey(a);
        var bParts = parseKey(b);
        for (var i = 0; i < Math.max(aParts.length, bParts.length); i++) {
            var diff = (aParts[i] || 0) - (bParts[i] || 0);
            if (diff !== 0) return diff;
        }
        return 0;
    }

    // Group sections by article_key, then sort articles and sections numerically
    var articleMap = {};
    var articleOrder = [];
    idx.forEach(function(entry) {
        var ak = entry.article_key;
        if (!articleMap[ak]) {
            articleMap[ak] = { article_key: ak, article_display: entry.article_display, sections: [] };
            articleOrder.push(ak);
        }
        articleMap[ak].sections.push(entry);
    });

    // Sort articles numerically by article_key; non-numeric keys (NaN) sort to the end
    articleOrder.sort(function(a, b) {
        var artARaw = parseInt(a, 10);
        var artBRaw = parseInt(b, 10);
        var artA = isNaN(artARaw) ? Infinity : artARaw;
        var artB = isNaN(artBRaw) ? Infinity : artBRaw;
        return artA !== artB ? artA - artB : a.localeCompare(b);
    });

    // Sort sections within each article numerically by section_key
    articleOrder.forEach(function(ak) {
        articleMap[ak].sections.sort(function(a, b) {
            var artA = parseInt(a.article_key, 10) || 0;
            var artB = parseInt(b.article_key, 10) || 0;
            if (artA !== artB) return artA - artB;
            return compareSectionKeys(a.section_key, b.section_key);
        });
    });

    function esc(s) {
        return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // Step 360: filter out evaluator/pipeline-internal CPF quotes from lawyer-facing display
    function isCPFQuoteDisplayable(quote) {
        if (!quote) return false;
        var lower = quote.toLowerCase();
        if (lower.indexOf('evaluator') === 0) return false;   // "Evaluator C flagged..."
        if (lower.indexOf('merged from') === 0) return false; // "Merged from CRX-01..."
        if (/^(crx|cpf|rlf)-\d+/i.test(quote)) return false; // bare finding IDs
        return true;
    }

    var html = '<div class="cv-index" style="padding:1rem 1.25rem">';

    articleOrder.forEach(function(ak) {
        var article = articleMap[ak];
        var artId = 'cvi-art-' + esc(ak).replace(/[^a-zA-Z0-9]/g, '-');
        html += '<div class="cvi-article" id="' + artId + '">';
        html += '<div class="cvi-article-header" onclick="this.parentElement.classList.toggle(\'cvi-collapsed\')" style="cursor:pointer;display:flex;align-items:center;gap:.5rem;padding:.5rem 0;border-bottom:1px solid var(--border,#e0e0e0);margin-bottom:.25rem;user-select:none">';
        html += '<span class="cvi-art-arrow" style="font-size:.75rem;transition:transform .15s">▼</span>';
        html += '<span style="font-weight:600;font-size:.85rem;letter-spacing:.05em;color:var(--text-muted,#888);text-transform:uppercase">' + esc(article.article_display) + '</span>';
        html += '<span style="font-size:.75rem;color:var(--text-muted,#999);margin-left:auto">' + article.sections.length + ' section' + (article.sections.length !== 1 ? 's' : '') + '</span>';
        html += '</div>';
        html += '<div class="cvi-article-body">';

        article.sections.forEach(function(entry) {
            var secId = 'cvi-sec-' + entry.source_order;
            var icon = BUCKET_ICON[entry.primary_action_bucket] || '⬜';
            var bucketLabel = BUCKET_LABEL[entry.primary_action_bucket] || entry.primary_action_bucket;
            var primaryFinding = entry.findings[0] || {};
            var primaryLabel = primaryFinding.element_label || '';
            var lpChips = entry.affected_lp_ids.slice(0, 5).map(function(lpId) {
                return '<span class="cvi-lp-chip" style="font-size:.7rem;background:var(--bg-subtle,#f0f0f0);border-radius:3px;padding:1px 5px;color:var(--text-muted,#666);margin-left:3px">' + esc(lpId) + '</span>';
            }).join('');

            html += '<div class="cvi-section" id="' + secId + '">';
            // Section row (collapsed)
            html += '<div class="cvi-section-row" onclick="document.getElementById(\'' + secId + '\').classList.toggle(\'cvi-sec-expanded\')" style="cursor:pointer;display:flex;align-items:center;gap:.5rem;padding:.4rem .25rem;border-bottom:1px solid var(--border-light,#f0f0f0)">';
            html += '<span title="' + esc(bucketLabel) + '" style="font-size:1rem;flex-shrink:0">' + icon + '</span>';
            html += '<span style="font-weight:500;font-size:.875rem;flex-shrink:0;min-width:7rem">' + esc(entry.display_ref) + '</span>';
            if (primaryLabel) {
                html += '<span style="font-size:.8rem;color:var(--text-muted,#666);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(primaryLabel) + '</span>';
            } else {
                html += '<span style="flex:1"></span>';
            }
            html += '<span style="font-size:.75rem;color:var(--text-muted,#888);white-space:nowrap;margin-left:.5rem">' + entry.finding_count + ' finding' + (entry.finding_count !== 1 ? 's' : '') + '</span>';
            if (lpChips) html += '<span class="cvi-lp-chips" style="flex-shrink:0">' + lpChips + '</span>';
            html += '<span class="cvi-sec-arrow" style="font-size:.65rem;color:var(--text-muted,#aaa);flex-shrink:0;transition:transform .15s">▶</span>';
            html += '</div>';

            // Section expanded findings
            html += '<div class="cvi-section-findings" style="display:none;padding:.5rem .5rem .5rem 1.75rem;background:var(--bg-subtle,#fafafa)">';
            entry.findings.forEach(function(f) {
                var fIcon = BUCKET_ICON[f.action_bucket] || '⬜';
                var fLabel = BUCKET_LABEL[f.action_bucket] || f.action_bucket;
                var isCross = f.finding_source === 'cross_provision';
                var lps = isCross ? (f.implicated_lps || []).join(', ') : (f.issue_area_id || '');

                // Step 361: click navigates to Evidence View (replaces old coverage/synthesis navigation)
                var _evIssueAreaId = f.issue_area_id || '';
                var _evElementId = (f.finding_source === 'coverage_element') ? (f.finding_id || '') : '';
                var _evFindingId = (f.finding_source === 'cross_provision') ? (f.finding_id || '') : '';
                var _evSectionKey = f.section_ref_normalized || '';
                var _evActionBucket = f.action_bucket || '';
                var clickFn = 'event.stopPropagation();window.CAM._navGoEvidenceFromContract(\''
                    + esc(_evIssueAreaId) + '\',\'' + esc(_evElementId) + '\',\''
                    + esc(_evFindingId) + '\',\'' + esc(_evSectionKey) + '\',\'' + esc(_evActionBucket) + '\')';

                html += '<div class="cvi-finding" onclick="' + clickFn + '" style="padding:.4rem .25rem .4rem 0;border-bottom:1px solid var(--border-light,#f0f0f0);cursor:' + (clickFn ? 'pointer' : 'default') + '">';
                html += '<div style="display:flex;align-items:center;gap:.4rem;margin-bottom:.2rem">';
                html += '<span title="' + esc(fLabel) + '" style="font-size:.85rem">' + fIcon + '</span>';
                html += '<span style="font-size:.8rem;font-weight:500">' + esc(f.element_label || f.finding_id) + '</span>';
                if (f.verdict === 'disputed') {
                    html += '<span style="font-size:.7rem;background:#fff3cd;color:#856404;border-radius:3px;padding:1px 5px;margin-left:3px">◈ Disputed</span>';
                }
                html += '</div>';
                if (lps) {
                    html += '<div style="font-size:.75rem;color:var(--text-muted,#888);margin-bottom:.2rem">';
                    if (isCross) {
                        // Step 360: "Multi-clause" replaces internal "Cross-provision" label
                        html += 'Multi-clause · ' + esc(lps);
                    } else {
                        html += esc(f.issue_area_name || '') + ' · ' + esc(lps);
                    }
                    html += '</div>';
                }
                // Step 360: filter evaluator attribution and merge notes from CPF quotes
                var _quoteOk = isCross ? isCPFQuoteDisplayable(f.quote) : !!f.quote;
                if (_quoteOk) {
                    var quoteText = f.quote.length > 120 ? f.quote.slice(0, 120) + '…' : f.quote;
                    html += '<div style="font-size:.75rem;color:var(--text-muted,#777);font-style:italic;border-left:2px solid var(--border,#e0e0e0);padding-left:.4rem;margin-top:.2rem">"' + esc(quoteText) + '"</div>';
                }
                html += '</div>';
            });
            html += '</div>'; // /cvi-section-findings
            html += '</div>'; // /cvi-section
        });

        html += '</div>'; // /cvi-article-body
        html += '</div>'; // /cvi-article
    });

    html += '</div>'; // /cv-index
    tab.innerHTML = html;

    // Wire expand/collapse CSS for articles and sections
    tab.querySelectorAll('.cvi-article').forEach(function(art) {
        var obs = new MutationObserver(function() {
            var collapsed = art.classList.contains('cvi-collapsed');
            var body = art.querySelector('.cvi-article-body');
            var arrow = art.querySelector('.cvi-art-arrow');
            if (body) body.style.display = collapsed ? 'none' : '';
            if (arrow) arrow.style.transform = collapsed ? 'rotate(-90deg)' : '';
        });
        obs.observe(art, { attributes: true, attributeFilter: ['class'] });
    });

    tab.querySelectorAll('.cvi-section').forEach(function(sec) {
        var obs = new MutationObserver(function() {
            var expanded = sec.classList.contains('cvi-sec-expanded');
            var findings = sec.querySelector('.cvi-section-findings');
            var arrow = sec.querySelector('.cvi-sec-arrow');
            if (findings) findings.style.display = expanded ? '' : 'none';
            if (arrow) arrow.style.transform = expanded ? 'rotate(90deg)' : '';
        });
        obs.observe(sec, { attributes: true, attributeFilter: ['class'] });
    });
}

window.CAM.renderContractViewPanel = renderContractViewPanel;

// Jump to a CPF card in the synthesis tab.
// Called from ↔ Synthesis badge onclick — extracted to avoid double-quote
// collision between the HTML onclick attribute delimiter and the CSS
// attribute selector value (JSON.stringify produced "LP-27" which broke
// the outer onclick="..." delimiters).
window.CAM.jumpToSynthesisFinding = function(pid, findingId) {
    if (typeof switchResultsTab !== 'function') return;
    switchResultsTab('synthesis');
    // renderSynthesisPanel() runs synchronously inside switchResultsTab.
    // requestAnimationFrame waits for the browser to paint before scrolling.
    requestAnimationFrame(function() {
        var target = null;
        if (pid) {
            target = document.querySelector('.cpf-card[data-lps*="' + pid + '"]');
        }
        if (!target && findingId) {
            var safeId = findingId.replace(/[^a-zA-Z0-9_-]/g, '_');
            target = document.getElementById('cpf-' + safeId);
        }
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            target.classList.add('highlight-flash');
            setTimeout(function() { target.classList.remove('highlight-flash'); }, 1500);
        }
    });
};

// Step 339: sidebar item builder for synthesis findings (cross_provision_findings).
// govSig: pre-computed governance signal (ASSERT_SIGNAL etc.) or null.
// Navigation is handled by the centralized event listener (mode === "synthesis" branch).
function _navBuildSynthesisItem(f, tIdx, govSig) {
    const fid    = f.finding_id || "";
    const lps    = (f.implicated_lps || []).join(", ");
    const hl     = (f.headline || fid).trim();
    const sev    = (f.severity || "HIGH").toUpperCase();
    const sevCls = sev === "HIGH" ? "nav-badge-high" : sev === "MEDIUM" ? "nav-badge-medium" : "nav-badge-low";
    const label  = f.finding_type === 'compound_risk'        ? 'COMPOUND RISK'
                 : f.finding_type === 'cross_coverage_relief' ? 'RELIEF'
                 : "[SYNTHESIS — " + sev + "]";
    const descText = _navTruncate(cpfTitle(f) || hl, 80);
    const truncHl = descText;
    const tooltipText = f.detail ? hl + " — " + f.detail : hl;
    // Step 339: confidence dots — compound items use deriveCompoundGovernanceSignal (pre-computed).
    var confBd = govSig && window.CAMAuditShared
        ? window.CAMAuditShared.getConfidenceBadgeData(govSig)
        : null;
    var confDotsHtml = confBd
        ? '<span class="nav-item-conf nav-item-conf-dots" title="Confidence: ' + esc(confBd.label) + '">' + confBd.dots + '</span>'
        : '';
    return '<button class="nav-item-enriched nav-item-synthesis" data-cpf-id="' + esc(fid) + '" data-tenant-idx="' + tIdx + '" data-mode="synthesis" title="' + esc(tooltipText) + '" type="button">'
         +   '<div class="nav-item-top">'
         +     '<span class="nav-item-id">' + esc(lps || fid) + '</span>'
         +     '<span class="nav-item-name">' + esc(label) + '</span>'
         +     '<span class="nav-item-badge ' + sevCls + '">' + sev + '</span>'
         +     confDotsHtml
         +   '</div>'
         +   (truncHl ? '<div class="nav-item-desc">' + esc(truncHl) + '</div>' : "")
         + '</button>';
}

// Step 278: client-side mirror of `extract_headline` from
// `cam/adapters/lease_review/lease_display.py`. Used as a fallback when
// the result dict was generated before Step 278 (no `exposure_headline`
// field on the assessment). Same priority: semicolon split → first
// sentence → 60-char word-boundary truncate.
function _deriveHeadlineFromExposure(text) {
    if (!text) return "";
    const max = 60;
    text = String(text).trim();
    if (!text) return "";
    if (text.indexOf(";") >= 0) {
        const candidate = text.split(";", 1)[0].trim();
        if (candidate && candidate.length <= max) return candidate;
    }
    const sentMatch = text.match(/^[^.!?]+[.!?](?:\s|$)/);
    if (sentMatch) {
        const candidate = sentMatch[0].replace(/[.!?]\s*$/, "").trim();
        if (candidate && candidate.length <= max) return candidate;
    }
    if (text.length <= max) return text;
    const wordEnd = text.slice(0, max).lastIndexOf(" ");
    const cut = wordEnd > 0 ? text.slice(0, wordEnd) : text.slice(0, max);
    return cut.replace(/[.,;:!?-]+$/, "") + "...";
}

function renderNavSidebar() {
    const container = document.getElementById("nav-sidebar-content");
    if (!container) return;
    if (!currentResults || !currentResults.tenants) {
        container.innerHTML = "";
        return;
    }
    const tenants = currentResults.tenants;
    const isModeC = isJobModeC();
    const showTenantHeaders = tenants.length > 1;
    let html = "";

    if (isModeC) {
        // Mode C: group coverage_assessment items into Needs Attention / Worth Reviewing tiers.
        // covered + partial_typical are intentionally excluded — they're surfaced in the
        // collapsed "Adequately Covered" section of the main panel.
        tenants.forEach((tenant, tIdx) => {
            const ca = (tenant.results && tenant.results.coverage_assessment) || [];
            const cpfs = ((tenant.results && tenant.results.cross_provision_findings) || [])
                .filter(f => (f.severity || "").toUpperCase() === "HIGH");
            const needsAttention = [];
            const worthReviewing = [];
            ca.forEach(a => {
                const _uiGap = normalizeUseConsequence(a.use_impact);
                const _uiMat = a.use_impact && a.use_impact.materiality;
                const _skipForUseImpact = _uiGap === 'beneficial' || _uiMat === 'not_applicable';
                if (!_skipForUseImpact && (
                    a.coverage_state === "potentially_unenforceable"
                    || a.coverage_state === "covered_unfavorable"
                    || a.coverage_state === "missing"
                    || a.coverage_state === "review_needed"   // Step 357: Phase 3 LPs
                    || a.partial_class === "partial_material")) {
                    needsAttention.push(a);
                } else if (a.partial_class === "partial_review") {
                    worthReviewing.push(a);
                }
            });
            if (needsAttention.length === 0 && worthReviewing.length === 0 && cpfs.length === 0) {
                if (showTenantHeaders) {
                    html += '<div class="nav-tenant-group" data-tenant-idx="' + tIdx + '">'
                         +   '<div class="nav-tenant-header">' + esc(tenant.filename || ("Lease " + (tIdx + 1))) + '</div>'
                         +   '<div class="nav-empty">No high-priority gaps</div>'
                         + '</div>';
                }
                return;
            }
            html += '<div class="nav-tenant-group" data-tenant-idx="' + tIdx + '">';
            if (showTenantHeaders) {
                html += '<div class="nav-tenant-header">' + esc(tenant.filename || ("Lease " + (tIdx + 1))) + '</div>';
            }
            if (needsAttention.length > 0) {
                html += '<div class="nav-section nav-section-attention">'
                     +   '<div class="nav-section-header">Needs Attention <span class="nav-section-count">' + needsAttention.length + '</span></div>';
                needsAttention.forEach(a => { html += _navBuildModeCItem(a, tIdx); });
                html += '</div>';
            }
            // Step 311/315: HIGH synthesis findings in sidebar — after Needs Attention, before Worth Reviewing.
            // Drop single-LP cross_coverage_gap entries whose LP is already in Needs Attention (redundant).
            // Step 332: Tier 1 → individual items; Tier 2 → single summary line.
            // Step 333: split compound_risk and cross_coverage_relief into separate sections so
            // the Compound Risk count matches the backend cluster count (not inflated by relief items).
            const _needsAttnIds = new Set(needsAttention.map(a => a.issue_area_id));
            const cpfsFiltered = cpfs.filter(f => {
                if (f.finding_type !== 'cross_coverage_gap') return true;
                const lps = f.implicated_lps || [];
                if (lps.length === 1 && _needsAttnIds.has(lps[0])) return false;
                return true;
            });
            const _compounds   = cpfsFiltered.filter(f => f.finding_type === 'compound_risk');
            const _reliefItems = cpfsFiltered.filter(f => f.finding_type === 'cross_coverage_relief');
            const _directionals = cpfsFiltered.filter(f => f.finding_type === 'directional_mismatch');

            // Step 339: build LP id → assessment map for compound confidence capping.
            const _caByLp = {};
            ca.forEach(function(a) { _caByLp[a.issue_area_id] = a; });

            if (_compounds.length > 0) {
                html += '<div class="nav-section nav-section-synthesis">'
                     +   '<div class="nav-section-header">Compound Risk <span class="nav-section-count">' + _compounds.length + '</span></div>';
                _compounds.forEach(function(f) {
                    const govSig = deriveCompoundGovernanceSignal(f, _caByLp);
                    html += _navBuildSynthesisItem(f, tIdx, govSig);
                });
                html += '</div>';
            }
            if (_reliefItems.length > 0) {
                html += '<div class="nav-section nav-section-synthesis">'
                     +   '<div class="nav-section-header">Coverage Relief <span class="nav-section-count">' + _reliefItems.length + '</span></div>';
                _reliefItems.forEach(f => { html += _navBuildSynthesisItem(f, tIdx, null); });
                html += '</div>';
            }
            if (_directionals.length > 0) {
                // Step 339: compute aggregate confidence distribution for collapsed directional row.
                const _dirSignals = _directionals.map(deriveDirectionalGovernanceSignal).filter(Boolean);
                const _sigLabels = { ASSERT_SIGNAL: 'verified', ASSERT_REVIEW_SIGNAL: 'impact unclear', REVIEW_SIGNAL: 'needs review', WITHHOLD_SIGNAL: 'inconclusive' };
                const _sigCounts = {};
                _dirSignals.forEach(function(s) { _sigCounts[s] = (_sigCounts[s] || 0) + 1; });
                const _sigOrder  = ['ASSERT_SIGNAL', 'ASSERT_REVIEW_SIGNAL', 'REVIEW_SIGNAL', 'WITHHOLD_SIGNAL'];
                const _allVerified = _dirSignals.length > 0 && _dirSignals.every(s => s === 'ASSERT_SIGNAL');
                var _dirConfHtml;
                if (_allVerified) {
                    var _bd = window.CAMAuditShared ? window.CAMAuditShared.getConfidenceBadgeData('ASSERT_SIGNAL') : null;
                    _dirConfHtml = '<span class="nav-dir-conf">' + (_bd ? _bd.dots + ' Verified' : 'Verified') + '</span>';
                } else if (_dirSignals.length > 0) {
                    const _distParts = _sigOrder.filter(s => _sigCounts[s]).map(s => _sigCounts[s] + ' ' + _sigLabels[s]);
                    _dirConfHtml = '<span class="nav-dir-conf">' + esc(_distParts.join(' · ')) + '</span>';
                } else {
                    _dirConfHtml = '';
                }

                html += '<div class="nav-section nav-section-directional">'
                     +   '<button class="nav-directional-summary" type="button"'
                     +   ' data-tenant-idx="' + tIdx + '"'
                     +   ' onclick="window.CAM.navToSynthesis(this.dataset.tenantIdx)">'
                     +     '<span class="nav-dir-label">DIRECTIONAL RISKS</span>'
                     +     '<span class="nav-dir-count">' + _directionals.length + '</span>'
                     +     '<span class="nav-dir-arrow">→</span>'
                     +   '</button>'
                     +   _dirConfHtml
                     + '</div>';
            }
            if (worthReviewing.length > 0) {
                html += '<div class="nav-section nav-section-review">'
                     +   '<div class="nav-section-header">Worth Reviewing <span class="nav-section-count">' + worthReviewing.length + '</span></div>';
                worthReviewing.forEach(a => { html += _navBuildModeCItem(a, tIdx); });
                html += '</div>';
            }
            html += '</div>';
        });
    } else {
        // Mode A: per tenant, render deviation sections (by severity) AND
        // coverage gap sections (Needs Attention / Worth Reviewing). Deviations
        // come from the multi-evaluator pipeline (provisions[].final_verdict);
        // coverage gaps come from Phase 5 (coverage_assessment[]). Both are
        // generated for Mode A jobs, so the sidebar should surface both.
        const SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "REVIEW"];
        tenants.forEach((tenant, tIdx) => {
            const provs = (tenant.results && tenant.results.provisions) || [];
            const devs = getDeviationWorkflowProvisions(provs, tIdx);
            const ca = (tenant.results && tenant.results.coverage_assessment) || [];
            const needsAttention = [];
            const worthReviewing = [];
            ca.forEach(a => {
                if (a.coverage_state === "potentially_unenforceable"
                    || a.coverage_state === "covered_unfavorable"
                    || a.coverage_state === "missing"
                    || a.partial_class === "partial_material") {
                    needsAttention.push(a);
                } else if (a.partial_class === "partial_review") {
                    worthReviewing.push(a);
                }
            });
            const totalIssues = devs.length + needsAttention.length + worthReviewing.length;
            if (totalIssues === 0) {
                if (showTenantHeaders) {
                    html += '<div class="nav-tenant-group" data-tenant-idx="' + tIdx + '">'
                         +   '<div class="nav-tenant-header">' + esc(tenant.filename || ("Lease " + (tIdx + 1))) + '</div>'
                         +   '<div class="nav-empty">No open issues</div>'
                         + '</div>';
                }
                return;
            }
            html += '<div class="nav-tenant-group" data-tenant-idx="' + tIdx + '">';
            if (showTenantHeaders) {
                html += '<div class="nav-tenant-header">' + esc(tenant.filename || ("Lease " + (tIdx + 1))) + '</div>';
            }
            // Deviation severity sections
            if (devs.length > 0) {
                const grouped = {};
                devs.forEach(d => {
                    let sev = (d.severity || "MEDIUM").toUpperCase();
                    if (!SEV_ORDER.includes(sev)) sev = "MEDIUM";
                    if (!grouped[sev]) grouped[sev] = [];
                    grouped[sev].push(d);
                });
                SEV_ORDER.forEach(sev => {
                    const items = grouped[sev];
                    if (!items || items.length === 0) return;
                    const sevCls = sev.toLowerCase();
                    html += '<div class="nav-section nav-section-sev-' + sevCls + '">'
                         +   '<div class="nav-section-header">' + esc(sevDisplay(sev)) + ' <span class="nav-section-count">' + items.length + '</span></div>';
                    items.forEach(d => { html += _navBuildModeAItem(d, tIdx); });
                    html += '</div>';
                });
            }
            // Coverage gap sections (same layout as Mode C)
            if (needsAttention.length > 0) {
                html += '<div class="nav-section nav-section-attention">'
                     +   '<div class="nav-section-header">Coverage — Needs Attention <span class="nav-section-count">' + needsAttention.length + '</span></div>';
                needsAttention.forEach(a => { html += _navBuildModeCItem(a, tIdx); });
                html += '</div>';
            }
            if (worthReviewing.length > 0) {
                html += '<div class="nav-section nav-section-review">'
                     +   '<div class="nav-section-header">Coverage — Worth Reviewing <span class="nav-section-count">' + worthReviewing.length + '</span></div>';
                worthReviewing.forEach(a => { html += _navBuildModeCItem(a, tIdx); });
                html += '</div>';
            }
            html += '</div>';
        });
    }

    if (!html.trim()) {
        html = '<div class="nav-empty-state">No open issues to review</div>';
    }

    container.innerHTML = html;

    // Wire click handlers — item-type-aware routing (Step 283).
    // The sidebar can carry two kinds of items:
    //   - data-mode="a" — Mode A deviations (rendered via _navBuildModeAItem).
    //     These have a `provision_id`; their primary writeup is the Lease
    //     Summary (Findings) view, so the click jumps to `jumpToFinding`
    //     which switches to the findings tab and scrolls to the deviation
    //     card.
    //   - data-mode="c" — coverage gap items (rendered via _navBuildModeCItem).
    //     These have an `issue_area_id`; their native view is the
    //     Coverage & Gaps panel, so the click jumps to
    //     `jumpToCoverageProvision`.
    //
    // Pre-Step-283, Mode A items routed to `jumpToDocview` (Doc Comparison),
    // which is supporting evidence rather than the primary writeup. The
    // tenant-index sync logic above is unchanged — only the per-mode
    // navigation target moved.
    container.querySelectorAll(".nav-item-enriched").forEach(btn => {
        btn.addEventListener("click", async () => {
            const pid = btn.dataset.pid;
            const tIdx = parseInt(btn.dataset.tenantIdx, 10);
            const mode = btn.dataset.mode;
            // Step 337: synthesis items — navigate to Contract Interaction Review tab.
            // Navigation moved from inline onclick to this listener to avoid HTML-escaping
            // fragility (complex onclick attributes can be silently broken by esc()).
            if (mode === "synthesis") {
                const cpfId  = btn.dataset.cpfId || "";
                const safeId = cpfId.replace(/[^a-zA-Z0-9_-]/g, '_');
                const synthTIdx = isNaN(tIdx) ? 0 : tIdx;
                if (typeof openContractDetail === 'function') {
                    openContractDetail(synthTIdx).then(function() {
                        switchResultsTab('synthesis');
                        setTimeout(function() {
                            const el = document.getElementById('cpf-' + safeId);
                            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }, 200);
                    });
                } else if (typeof switchResultsTab === 'function') {
                    switchResultsTab('synthesis');
                }
                return;
            }
            if (!isNaN(tIdx) && tIdx !== currentTenantIndex) {
                currentTenantIndex = tIdx;
                const ts = document.getElementById("tenant-select");
                if (ts) ts.value = String(tIdx);
                const dts = document.getElementById("docview-tenant-select");
                if (dts) dts.value = String(tIdx);
                if (typeof syncChatScopeToCurrentTenant === "function") {
                    try { syncChatScopeToCurrentTenant(true); } catch (e) { /* silent */ }
                }
            }
            if (mode === "c") {
                // Coverage gap → open the right contract then jump to the LP.
                // jumpHeatmapCell calls openContractDetail(tIdx) first so the
                // Coverage & Gaps tab renders without requiring a prior selection.
                if (typeof jumpHeatmapCell === "function") {
                    jumpHeatmapCell(tIdx, pid);
                } else if (window.CAM && typeof window.CAM.jumpToCoverageProvision === "function") {
                    window.CAM.jumpToCoverageProvision(pid, { expandElements: true });
                }
            } else {
                // Mode A deviation → open contract detail if needed, then jump to finding
                if (activeResultsTab === "audittrail" && contractDetailOpen && currentTenantIndex === tIdx) {
                    // Already on audit trail for this contract — scroll within it
                    if (typeof jumpToAuditProvision === "function") jumpToAuditProvision(tIdx, pid);
                } else {
                    await openContractDetail(tIdx);
                    switchResultsTab("findings");
                    await waitForResultsTarget(() =>
                        document.getElementById(`dev-${pid}`) ||
                        document.querySelector(`[data-pid="${CSS.escape(pid)}"]`)
                    );
                    if (typeof jumpToFinding === "function") jumpToFinding(pid);
                }
            }
            updateNavActive(currentTenantIndex, pid);
        });
    });

    updateNavActive(currentTenantIndex);
}

function updateNavActive(tenantIdx, focusPid) {
    const container = document.getElementById("nav-sidebar-content");
    if (!container) return;
    container.querySelectorAll(".nav-item-enriched.active").forEach(el => el.classList.remove("active"));
    container.querySelectorAll(".nav-tenant-group").forEach(g => {
        const idx = parseInt(g.dataset.tenantIdx, 10);
        g.classList.toggle("nav-tenant-active", idx === tenantIdx);
    });
    if (focusPid) {
        try {
            const sel = '.nav-item-enriched[data-pid="' + (window.CSS && CSS.escape ? CSS.escape(focusPid) : focusPid) + '"][data-tenant-idx="' + tenantIdx + '"]';
            const item = container.querySelector(sel);
            if (item) item.classList.add("active");
        } catch (e) { /* silent */ }
    }
}

// ── Step 347: Architecture C Phase 1 — Unified Sidebar ─────────────────────

// context: { perspective, govSig }
// Step 347e: Risk = HIGH/CRIT only. MEDIUM → Improvement everywhere.
// Step 373: Priority Review — a UI triage tier, NOT a severity theory.
// It means "CAM flags this for first-pass lawyer attention." This is the SINGLE
// source of truth for the triage tier, used by BOTH the Key Issues sidebar and
// the Overview risk summary (same single-source-of-truth pattern as
// classifyFindingType). Do NOT inline the rule anywhere else.
//
//   Coverage card  → Priority Review IFF review_priority_distance_signal.hard_flag === true
//                    (Stage 5f: verdict distance × tenant consequence)
//   Stage 7 card   → Priority Review IFF severity === "HIGH"
//
// These are DIFFERENT source metrics mapped into ONE lawyer-facing tier — same
// review tier, different source logic. We do NOT represent them as the same
// underlying computation, and we do NOT synthesize a HIGH/MED/LOW severity for
// coverage LPs. hard_flag is a GATE, not a merged score; both underlying axes
// (confidence via lp_confidence + consequence via use_impact) stay visible in
// the card detail, which keeps this doctrine-safe under Architecture A
// Guardrail #3 (confidence and consequence are orthogonal, never merged).
function isPriorityReview(finding) {
    if (!finding) return false;
    // Stage 7 synthesis cards (cross_provision_findings): HIGH severity.
    if (finding._item_type === 'synthesis' || finding.finding_type) {
        return String(finding.severity || '').toUpperCase() === 'HIGH';
    }
    // Coverage LP cards: Stage 5f hard_flag.
    var rpds = finding.review_priority_distance_signal;
    return !!(rpds && rpds.hard_flag === true);
}

function classifyFindingType(finding, mode, context) {
    var perspective = (context && context.perspective) || null;
    var ctxGovSig   = (context && context.govSig)   || null;
    var isVerified  = ctxGovSig === 'ASSERT_SIGNAL';

    if (finding._item_type === 'synthesis') {
        var ft  = finding.finding_type || '';
        var sev = (finding.severity || 'MEDIUM').toUpperCase();

        if (ft === 'compound_risk') return 'risk'; // guardrail #1: always Risk

        if (ft === 'directional_mismatch') {
            // Step 376h P2'': bucket pre-computed by backend from consequence/materiality/
            // consequence_source/mismatch_support. Sign/directionality is diagnostic-only
            // and must NOT affect the bucket (routing_use === 'diagnostic_only').
            var p2pp = finding.p2pp_routing;
            if (p2pp && p2pp.bucket) {
                return p2pp.bucket;
            }
            // Backward-compat: artifacts produced before 376h lack p2pp_routing.
            // Fall back to sign-based routing for those artifacts only.
            var dir = finding.directionality || '';
            var adverseTo = dir === 'tenant_unprotected' ? 'tenant'
                          : dir === 'landlord_unprotected' ? 'landlord' : null;
            if (!adverseTo || !perspective || perspective === 'neutral') return 'review_needed';
            if (adverseTo !== perspective) return 'addressed'; // favorable to viewer
            // Step 367: unverified + adverse → Needs Review, not Addressed.
            // Withholding an assertion is not a claim the lease handles it. Surface for human review.
            return isVerified ? 'risk' : 'review_needed';
        }
        if (ft === 'cross_coverage_relief') return 'addressed';
        // cross_coverage_gap: HIGH/CRIT → risk; MEDIUM/LOW → improvement
        if (sev === 'CRITICAL' || sev === 'HIGH') return 'risk';
        return 'improvement';
    }

    if (mode === 'a' || finding._item_type === 'deviation') {
        var verdict = finding.final_verdict || '';
        if (verdict !== 'DEVIATES') return 'addressed';
        var gs     = (finding.cam_score && finding.cam_score.governance_signal) || '';
        var govSig = gs ? gs.toUpperCase() : null;
        var sev2   = (finding.severity || 'MEDIUM').toUpperCase();
        if (govSig === 'REVIEW_SIGNAL' || govSig === 'WITHHOLD_SIGNAL') return 'review_needed';
        if (sev2 === 'CRITICAL' || sev2 === 'HIGH') return 'risk';
        if (govSig === 'ASSERT_SIGNAL') return 'risk';
        if (sev2 === 'LOW') return 'improvement';
        return 'review_needed';
    }

    // Mode C coverage assessment — HIGH/CRIT → Risk; MEDIUM/LOW → Improvement
    var state    = finding.coverage_state || '';
    var pcls     = finding.partial_class  || '';
    var ui       = finding.use_impact;
    var gap      = normalizeUseConsequence(ui);
    var mat      = ui && ui.materiality;
    var uiActive = ui && ui.confidence !== 'no_evaluators';

    // Consequence tier (UNCHANGED — use_impact.materiality + partial_class + use_consequence).
    // Wrapped so the hard_flag floor below can run as the genuine LAST step (promote-only).
    var _consequenceBucket = (function() {
        if (state === 'covered' || state === 'covered_typical' || state === 'not_applicable') return 'addressed';
        if (state === 'potentially_unenforceable') return 'risk';

        // Severity tier: HIGH when materiality is high or unknown; else MEDIUM/LOW
        var matTier = (pcls === 'partial_material') ? 'HIGH'
                    : mat === 'high' ? 'HIGH'
                    : mat === 'low'  ? 'LOW'
                    : 'MEDIUM';
        var isHighSev = (matTier === 'HIGH');

        if (state === 'covered_unfavorable') {
            var advTo = finding.covered_unfavorable_adverse_to || null;
            if (advTo && perspective && perspective !== 'neutral' && advTo !== perspective) return 'addressed';
            // Adverse or unknown direction: triage by severity
            return isHighSev ? 'risk' : 'improvement';
        }

        // For missing / partial: severity-first
        function sevTriage() {
            if (isHighSev) return 'risk';
            return 'improvement'; // MEDIUM and LOW → improvement
        }

        if (state === 'missing') {
            if (uiActive && gap === 'beneficial') return 'addressed';
            if (uiActive && mat === 'not_applicable') return 'improvement';
            return sevTriage();
        }
        if (state === 'partial') {
            if (pcls === 'partial_review') return 'improvement';
            if (pcls === 'partial_material') return sevTriage();
            return sevTriage();
        }
        if (state === 'review_needed') return 'review_needed'; // CAM has no coverage verdict; use_impact is downstream

        console.warn('[CAM classifyFindingType] Unclassifiable finding — state:', state, 'pcls:', pcls);
        return 'review_needed';
    })();

    // Step 373C: hard_flag (Stage 5f: severe verdict distance x meaningful consequence) floors at Needs Review.
    // Epistemic disagreement is an independent routing signal from consequence (Architecture A,
    // two independent signals). A hard-flagged finding must never fall to Improvement/Addressed.
    // Floor PROMOTES ONLY (Improvement/Addressed → Needs Review); it never demotes Risk/Needs Review,
    // and never elevates to Risk — consequence still sets the ceiling, hard_flag sets the floor.
    var _rpds = finding.review_priority_distance_signal;
    if (_rpds && _rpds.hard_flag === true
        && (_consequenceBucket === 'improvement' || _consequenceBucket === 'addressed')) {
        return 'review_needed';
    }
    return _consequenceBucket;
}

// Step 374G: default-collapsed state per sub-group base (sectionId minus trailing _<tenantIdx>).
// Shared by Risk and Needs Review sub-headers. Mirror Risk's pattern: the large directional /
// one-sided group defaults collapsed; the smaller groups default open.
var _NAV_SUBGROUP_DEFAULT_COLLAPSED = {
    risk_gaps: true, risk_compound: true, risk_directional: true,
    review_coverage: true, review_onesided: true, review_conflicting: true,
    review_consnotassessed: true
};

function _navSubGroupCollapsed(sectionId, jobId) {
    var key = 'cam_sidebar_' + sectionId + (jobId ? '_' + jobId : '');
    var stored = localStorage.getItem(key);
    if (stored !== null) return stored === '1';
    // Strip trailing _N (tenant index) to get the base sub-group name
    var base = sectionId.replace(/_\d+$/, '');
    return _NAV_SUBGROUP_DEFAULT_COLLAPSED[base] || false;
}

function _navSubGroupWrap(sectionId, title, count, bodyHtml, jobId) {
    var collapsed = _navSubGroupCollapsed(sectionId, jobId);
    var oc = "window.CAM._navSectionToggle('" + sectionId + "','" + (jobId || '') + "')";
    return '<div class="nav-subgroup">'
         + '<div class="nav-subgroup-header">'
         + '<span class="nav-subgroup-title">' + esc(title) + '</span>'
         + ' <span class="nav-subgroup-count">' + count + '</span>'
         + '<button class="nav-collapse-toggle nav-subgroup-toggle" id="nav-section-toggle-' + sectionId
         + '" onclick="' + oc + '" type="button">' + (collapsed ? '▶' : '▼') + '</button>'
         + '</div>'
         + '<div class="nav-section-body" id="nav-section-body-' + sectionId + '"'
         + (collapsed ? ' style="display:none"' : '') + '>'
         + bodyHtml + '</div></div>';
}

// Step 373: triage detail fields for a coverage LP Risk card. Consequence comes
// ONLY from use_impact.materiality — if use_impact / use_impact.materiality is
// absent the consequence line is OMITTED (we never fall back to the plain
// `materiality` field; same visual slot, different meaning = semantic fraud).
function _navCoverageTriageFields(a) {
    var rpds = a.review_priority_distance_signal;
    var ui   = a.use_impact;
    var m    = ui && ui.materiality;
    var consequence = (m === 'high') ? 'High' : (m === 'medium') ? 'Medium' : (m === 'low') ? 'Low' : null;
    var conf = (a.lp_confidence === 'high' || a.lp_confidence === 'low') ? a.lp_confidence : null;
    var vd   = a.verdict_distance;
    var disag = (vd && (vd.severity === 'moderate' || vd.severity === 'severe')) ? vd.severity : null;
    return {
        priority:     isPriorityReview(a),
        consequence:  consequence,
        confidence:   conf,
        disagreement: disag,
        reason:       (rpds && rpds.hard_flag && rpds.reason) ? rpds.reason : null
    };
}

// Step 373: triage detail fields for a Stage 7 synthesis Risk card.
function _navSynthTriageFields(f) {
    return {
        priority:  isPriorityReview(f),
        severity:  (f.severity || '').toUpperCase() || null,
        agreement: f.evaluator_agreement || null
    };
}

// Step 360: provision name leads, action chip replaces severity badge + typeLabel + confidence dots.
function _navBuildUnifiedItem(item, tIdx) {
    const sev = (item.sev || 'MEDIUM').toUpperCase();
    const sevCls = sev.toLowerCase();
    const dataAttrs = 'data-item-type="' + esc(item._item_type || '') + '"'
        + ' data-pid="' + esc(item.pid || '') + '"'
        + ' data-tenant-idx="' + tIdx + '"'
        + ' data-mode="' + esc(item._mode || '') + '"'
        + (item.cpfId ? ' data-cpf-id="' + esc(item.cpfId) + '"' : '');
    const disputedHtml = item.elements_disputed_critical > 0
        ? '<span class="cv-disputed-indicator cv-disputed-indicator--critical">⚑ Critical Disputed</span>'
        : item.elements_disputed > 0
        ? '<span class="cv-disputed-indicator">◈ Disputed</span>'
        : '';
    // Action bucket chip: Risk / Needs Review / Improvement / Addressed
    var _bucketLabel = { risk: 'Risk', review_needed: 'Needs Review', improvement: 'Improvement', addressed: 'Addressed' };
    var _bucketBadge = { risk: 'nav-badge-high', review_needed: 'nav-badge-review', improvement: 'nav-badge-medium', addressed: 'nav-badge-favorable' };
    var _bucket = item._bucket || '';
    var actionChipHtml = _bucket
        ? '<span class="nav-item-badge ' + (_bucketBadge[_bucket] || 'nav-badge-default') + '" style="margin-left:auto;flex-shrink:0">' + esc(_bucketLabel[_bucket] || _bucket) + '</span>'
        : '';
    // LP identifier line below description (small, muted)
    var lpMetaHtml = item.pid
        ? '<div style="font-size:.7rem;color:var(--text-muted,#888);margin-top:.15rem;font-family:var(--font-mono,monospace);letter-spacing:.02em">' + esc(item.pid) + '</div>'
        : '';
    // Step 361: "View Evidence" link (only for LP-level items with a pid)
    var evidenceLinkHtml = (item.pid && item._item_type !== 'synthesis')
        ? '<div style="text-align:right;margin-top:.15rem">'
        + '<span class="nav-ev-link" onclick="event.stopPropagation();window.CAM._navGoEvidenceFromKeyIssues(\''
        + esc(item.pid) + '\',\'' + esc(item._bucket || '') + '\')" tabindex="0" role="link">View Evidence →</span>'
        + '</div>'
        : '';
    // Step 373: Priority Review triage chip + detail line (Risk-bucket cards only).
    var priorityChipHtml = item._priority
        ? '<div class="nav-priority-row"><span class="nav-priority-chip" title="CAM flags this for first-pass review">&#9888; Priority Review</span></div>'
        : '';
    var _triParts = [];
    if (item._consequence)  _triParts.push('Consequence: ' + item._consequence);
    if (item._confidence)   _triParts.push('Confidence: ' + item._confidence);
    if (item._disagreement) _triParts.push('Disagreement: ' + item._disagreement);
    if (item._severity)     _triParts.push('Severity: ' + item._severity);
    if (item._agreement)    _triParts.push('Agreement: ' + item._agreement);
    var triageMetaHtml = _triParts.length
        ? '<div class="nav-triage-meta">' + esc(_triParts.join(' · ')) + '</div>'
        : '';
    var _title = item.tooltip || item.summary || item.name || '';
    if (item._reason) _title = (_title ? _title + ' — ' : '') + 'Priority reason: ' + item._reason;
    return '<button class="nav-item-enriched nav-item-unified nav-item-sev-' + sevCls + '" '
         + dataAttrs + ' title="' + esc(_title) + '" type="button">'
         +   '<div class="nav-item-top">'
         +     '<span class="nav-item-name">' + esc(item.name || item.pid || '') + '</span>'
         +     actionChipHtml
         +   '</div>'
         +   priorityChipHtml
         +   (item.summary ? '<div class="nav-item-desc">' + esc(item.summary) + '</div>' : '')
         +   triageMetaHtml
         +   lpMetaHtml
         +   disputedHtml
         +   evidenceLinkHtml
         + '</button>';
}

var _NAV_SECTION_DEFAULT_COLLAPSED = {
    risk: true, review: true, improvement: true, addressed: true
};
function _navSectionCollapsed(sectionId, jobId) {
    var stored = localStorage.getItem('cam_sidebar_' + sectionId + (jobId ? '_' + jobId : ''));
    if (stored !== null) return stored === '1';
    var base = sectionId.replace(/_\d+$/, '');
    return _NAV_SECTION_DEFAULT_COLLAPSED[base] || false;
}

function _navSectionToggle(sectionId, jobId) {
    const body = document.getElementById('nav-section-body-' + sectionId);
    const btn  = document.getElementById('nav-section-toggle-' + sectionId);
    if (!body) return;
    const collapsing = body.style.display !== 'none';
    body.style.display = collapsing ? 'none' : '';
    if (btn) btn.textContent = collapsing ? '▶' : '▼';
    localStorage.setItem('cam_sidebar_' + sectionId + (jobId ? '_' + jobId : ''), collapsing ? '1' : '0');
}

// Step 366: gloss is an optional one-line action description shown muted below the header.
function _navSectionWrap(sectionId, icon, title, count, bodyHtml, jobId, gloss) {
    const collapsed = _navSectionCollapsed(sectionId, jobId);
    const oc = "window.CAM._navSectionToggle('" + sectionId + "','" + (jobId || '') + "')";
    return '<div class="nav-section nav-section-unified nav-section-' + sectionId.replace(/_\d+$/, '') + '">'
         + '<div class="nav-section-header nav-section-header-collapsible">'
         + '<span class="nav-section-icon">' + icon + '</span>'
         + '<span class="nav-section-title">' + esc(title) + '</span>'
         + ' <span class="nav-section-count">' + count + '</span>'
         + '<button class="nav-collapse-toggle" id="nav-section-toggle-' + sectionId
         + '" onclick="' + oc + '" type="button">' + (collapsed ? '▶' : '▼') + '</button>'
         + '</div>'
         + (gloss ? '<div class="nav-section-gloss">' + esc(gloss) + '</div>' : '')
         + '<div class="nav-section-body" id="nav-section-body-' + sectionId + '"'
         + (collapsed ? ' style="display:none"' : '') + '>'
         + bodyHtml
         + '</div></div>';
}

function _navAddressedChips(items, tIdx) {
    if (!items.length) return '<div class="nav-empty-inner">—</div>';
    return '<div class="nav-chip-list">'
         + items.map(function(item) {
               const tip = item.pid + (item.name && item.name !== item.pid ? ' — ' + item.name : '');
               return '<span class="nav-chip" data-pid="' + esc(item.pid) + '" data-tenant-idx="' + tIdx
                    + '" title="' + esc(tip) + '">' + esc(item.pid) + '</span>';
           }).join('')
         + '</div>';
}

// Overrides the earlier renderNavSidebar (JS hoisting: last declaration wins).
function renderNavSidebar() {
    const container = document.getElementById('nav-sidebar-content');
    if (!container) return;
    if (!currentResults || !currentResults.tenants) { container.innerHTML = ''; return; }

    const tenants = currentResults.tenants;
    const isModeC = isJobModeC();
    const showTenantHeaders = tenants.length > 1;
    const jobId = currentJobId || '';
    const sevRank = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    function sortItems(arr) {
        return arr.sort(function(a, b) {
            // Step 373: Priority Review floats to the TOP within the bucket
            // (only Risk-bucket items carry _priority, so other buckets are unaffected).
            var pa = a._priority ? 0 : 1, pb = b._priority ? 0 : 1;
            if (pa !== pb) return pa - pb;
            var sa = sevRank[a.sev] !== undefined ? sevRank[a.sev] : 4;
            var sb = sevRank[b.sev] !== undefined ? sevRank[b.sev] : 4;
            if (sa !== sb) return sa - sb;
            return (a.pid || '').localeCompare(b.pid || '');
        });
    }
    var html = '';

    tenants.forEach(function(tenant, tIdx) {
        var r = tenant.results;
        if (!r) return;
        var risk = [], reviewNeeded = [], improvement = [], addressed = [];

        function pushItem(bucket, item) {
            item._bucket = bucket; // Step 360: used by _navBuildUnifiedItem for action chip
            if (bucket === 'risk') risk.push(item);
            else if (bucket === 'review_needed') reviewNeeded.push(item);
            else if (bucket === 'improvement') improvement.push(item);
            else addressed.push(item);
        }

        if (isModeC) {
            var ca = r.coverage_assessment || [];
            var caByLp = {};
            ca.forEach(function(a) { caByLp[a.issue_area_id || a.provision_id] = a; });

            var _perspective = getJobPerspective();
            ca.forEach(function(a) {
                var state = a.coverage_state || '';
                if (state === 'not_applicable') return;
                var bucket = classifyFindingType(a, 'c', { perspective: _perspective });
                var pid = a.issue_area_id || a.provision_id || '';
                var name = a.issue_area_name || a.provision_name || pid;
                var ui = a.use_impact, mat = ui && ui.materiality;
                var sev = (state === 'potentially_unenforceable' || state === 'covered_unfavorable') ? 'HIGH'
                        : a.partial_class === 'partial_material' ? 'HIGH'
                        : mat === 'high' ? 'HIGH' : mat === 'medium' ? 'MEDIUM' : mat === 'low' ? 'LOW' : 'MEDIUM';
                var typeLabel = state === 'missing' ? 'GAP' : state === 'partial' ? 'PARTIAL'
                              : state === 'review_needed' ? 'REVIEW' : state === 'covered_unfavorable' ? 'UNFAVORABLE'
                              : state === 'potentially_unenforceable' ? 'ENFORCEABILITY' : '';
                var evs = a.element_verdicts || [];
                var govSig = evs.length > 0 ? deriveCoverageGovernanceSignal(evs) : null;
                var summary = (a.exposure_headline || _deriveHeadlineFromExposure(a.exposure_statement || '')).trim();
                // Step 373: triage fields only on Risk-bucket cards (within-bucket triage).
                var _tri = (bucket === 'risk') ? _navCoverageTriageFields(a) : null;
                pushItem(bucket, { _item_type: 'gap', _mode: 'c', pid: pid, name: name,
                    sev: sev, typeLabel: typeLabel, govSig: govSig, summary: summary,
                    elements_disputed: a.elements_disputed || 0,
                    elements_disputed_critical: a.elements_disputed_critical || 0,
                    _priority: !!(_tri && _tri.priority),
                    _consequence: _tri && _tri.consequence, _confidence: _tri && _tri.confidence,
                    _disagreement: _tri && _tri.disagreement, _reason: _tri && _tri.reason,
                    // Step 374G: Needs Review sub-header grouping — same shared classifier as the Action Summary.
                    _reviewSubtype: (bucket === 'review_needed') ? _reviewSubtypeOf(a) : null,
                    tooltip: (a.exposure_statement || '').slice(0, 200) || name });
            });

            var cpfs = r.cross_provision_findings || [];
            cpfs.forEach(function(f) {
                var govSig = f.finding_type === 'compound_risk' ? deriveCompoundGovernanceSignal(f, caByLp)
                           : f.finding_type === 'directional_mismatch' ? deriveDirectionalGovernanceSignal(f) : null;
                var fi = { _item_type: 'synthesis', finding_type: f.finding_type,
                           severity: f.severity, directionality: f.directionality || '',
                           p2pp_routing: f.p2pp_routing || null }; // Step 376h: P2'' pre-computed bucket
                var bucket = classifyFindingType(fi, 'c', { perspective: _perspective, govSig: govSig });
                var sev = (f.severity || 'HIGH').toUpperCase();
                var lps = (f.implicated_lps || []).join(', ');
                var typeLabel = f.finding_type === 'compound_risk' ? 'COMPOUND'
                              : f.finding_type === 'directional_mismatch' ? 'DIRECTIONAL'
                              : f.finding_type === 'cross_coverage_relief' ? 'RELIEF' : 'SYNTHESIS';
                var summary = _navTruncate(cpfTitle(f), 80);
                // Step 373: triage fields only on Risk-bucket cards.
                var _tris = (bucket === 'risk') ? _navSynthTriageFields(f) : null;
                // Step 369: pass evaluator_agreement for directional ranking + tag
                pushItem(bucket, { _item_type: 'synthesis', _mode: 'synthesis', pid: lps,
                    name: cpfTitle(f) || f.finding_id || '', sev: sev, typeLabel: typeLabel,
                    govSig: govSig, summary: summary, cpfId: f.finding_id || '',
                    tooltip: f.headline || '',
                    _priority: !!(_tris && _tris.priority),
                    _severity: _tris && _tris.severity, _agreement: _tris && _tris.agreement,
                    // Step 374G: Needs Review sub-header grouping — same shared classifier as the Action Summary.
                    _reviewSubtype: (bucket === 'review_needed') ? _reviewSubtypeOf(f) : null,
                    evaluator_agreement: f.evaluator_agreement || '' });
            });
        } else {
            var provs = r.provisions || [];
            var devs = getDeviationWorkflowProvisions(provs, tIdx);
            devs.forEach(function(d) {
                var di = { _item_type: 'deviation', final_verdict: d.final_verdict,
                           cam_score: d.cam_score, severity: d.severity };
                var bucket = classifyFindingType(di, 'a');
                var gs = d.cam_score && d.cam_score.governance_signal;
                var govSig = gs ? gs.toUpperCase() : null;
                var desc = (d.risk_headline || d.challenge_details || d.summary || '').trim();
                pushItem(bucket, { _item_type: 'deviation', _mode: 'a',
                    pid: d.provision_id || '', name: d.provision_name || d.provision_id || '',
                    sev: (d.severity || 'MEDIUM').toUpperCase(), typeLabel: 'DEVIATION',
                    // Step 374G: Needs Review sub-header grouping — same shared classifier (Mode-A deviations → coverage_question).
                    _reviewSubtype: (bucket === 'review_needed') ? _reviewSubtypeOf(d) : null,
                    govSig: govSig, summary: _navTruncate(desc, 80), tooltip: desc || d.provision_name || '' });
            });
            var ca2 = r.coverage_assessment || [];
            var _perspA = getJobPerspective();
            ca2.forEach(function(a) {
                var state = a.coverage_state || '';
                if (state === 'not_applicable') return;
                var bucket = classifyFindingType(a, 'c', { perspective: _perspA });
                var pid = a.issue_area_id || a.provision_id || '';
                var ui = a.use_impact, mat = ui && ui.materiality;
                var sev = mat === 'high' ? 'HIGH' : mat === 'medium' ? 'MEDIUM' : mat === 'low' ? 'LOW' : 'MEDIUM';
                var typeLabel = state === 'missing' ? 'GAP' : state === 'partial' ? 'PARTIAL' : '';
                var evs = a.element_verdicts || [];
                var govSig = evs.length > 0 ? deriveCoverageGovernanceSignal(evs) : null;
                var summary = (a.exposure_headline || _deriveHeadlineFromExposure(a.exposure_statement || '')).trim();
                // Step 373: triage fields only on Risk-bucket cards (same rule as Mode C).
                var _triA = (bucket === 'risk') ? _navCoverageTriageFields(a) : null;
                pushItem(bucket, { _item_type: 'gap', _mode: 'c', pid: pid,
                    name: a.issue_area_name || a.provision_name || pid, sev: sev,
                    typeLabel: typeLabel, govSig: govSig, summary: summary,
                    elements_disputed: a.elements_disputed || 0,
                    elements_disputed_critical: a.elements_disputed_critical || 0,
                    _priority: !!(_triA && _triA.priority),
                    _consequence: _triA && _triA.consequence, _confidence: _triA && _triA.confidence,
                    _disagreement: _triA && _triA.disagreement, _reason: _triA && _triA.reason,
                    // Step 374G: Needs Review sub-header grouping — same shared classifier as the Action Summary.
                    _reviewSubtype: (bucket === 'review_needed') ? _reviewSubtypeOf(a) : null,
                    tooltip: (a.exposure_statement || '').slice(0, 200) || pid });
            });
        }

        sortItems(risk); sortItems(improvement); sortItems(addressed);

        // Step 369: Sort Needs Review — directionals by agreement-then-severity first,
        // then everything else by severity. Also inject "N of 3" text tag into
        // directional items' summary so it shows in nav-item-desc (colorblind-safe text).
        (function() {
            var sevRankLocal = { HIGH: 0, MEDIUM: 1, LOW: 2 };
            function _agreeCount(item) {
                // e.g. "2-1" → 2; "3-0" → 3; unknown → 0
                var ag = (item.evaluator_agreement || '').split('-')[0];
                var n = parseInt(ag, 10);
                return isNaN(n) ? 0 : n;
            }
            var dirs = reviewNeeded.filter(function(i) { return i.typeLabel === 'DIRECTIONAL'; });
            var others = reviewNeeded.filter(function(i) { return i.typeLabel !== 'DIRECTIONAL'; });
            dirs.sort(function(a, b) {
                var da = _agreeCount(a), db = _agreeCount(b);
                if (da !== db) return db - da;   // 3/3 before 2/1
                var sa = sevRankLocal[(a.sev || 'MEDIUM').toUpperCase()] !== undefined
                       ? sevRankLocal[(a.sev || 'MEDIUM').toUpperCase()] : 4;
                var sb = sevRankLocal[(b.sev || 'MEDIUM').toUpperCase()] !== undefined
                       ? sevRankLocal[(b.sev || 'MEDIUM').toUpperCase()] : 4;
                return sa - sb;
            });
            // Inject agreement tag into summary for directionals
            dirs.forEach(function(item) {
                var n = _agreeCount(item);
                if (n > 0 && !item._agreeTagged) {
                    var tag = n + ' of 3';
                    item.summary = (item.summary ? item.summary + ' — ' : '') + tag;
                    item._agreeTagged = true;
                }
            });
            others.sort(function(a, b) {
                var sa = sevRankLocal[(a.sev || 'MEDIUM').toUpperCase()] !== undefined
                       ? sevRankLocal[(a.sev || 'MEDIUM').toUpperCase()] : 4;
                var sb = sevRankLocal[(b.sev || 'MEDIUM').toUpperCase()] !== undefined
                       ? sevRankLocal[(b.sev || 'MEDIUM').toUpperCase()] : 4;
                return sa - sb;
            });
            reviewNeeded.length = 0;
            dirs.forEach(function(i) { reviewNeeded.push(i); });
            others.forEach(function(i) { reviewNeeded.push(i); });
        }());

        html += '<div class="nav-tenant-group" data-tenant-idx="' + tIdx + '">';
        if (showTenantHeaders) {
            html += '<div class="nav-tenant-header">' + esc(tenant.filename || ('Lease ' + (tIdx + 1))) + '</div>';
        }
        if (risk.length > 0) {
            var riskGaps = risk.filter(function(i) { return i._item_type !== 'synthesis'; });
            var riskCompound = risk.filter(function(i) { return i.typeLabel === 'COMPOUND'; });
            var riskDirectional = risk.filter(function(i) { return i.typeLabel === 'DIRECTIONAL'; });
            var subHtml = '';
            if (riskGaps.length > 0)
                subHtml += _navSubGroupWrap('risk_gaps_' + tIdx, 'Coverage Gaps', riskGaps.length,
                    riskGaps.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            if (riskCompound.length > 0)
                subHtml += _navSubGroupWrap('risk_compound_' + tIdx, 'Cross-clause Risks', riskCompound.length,
                    riskCompound.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            if (riskDirectional.length > 0)
                subHtml += _navSubGroupWrap('risk_directional_' + tIdx, 'One-sided Terms', riskDirectional.length,
                    riskDirectional.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            // Step 374: show the Risk count on the header (was intentionally blank since Step 360) so
            // RISK matches the other three buckets and the Overview Action Summary (risk.length ==
            // _computeRiskCounts.action.risk by construction — same routing). Sub-group counts remain.
            html += _navSectionWrap('risk_' + tIdx, '⚠', 'RISK', risk.length, subHtml, jobId, CAM_RISK_GLOSS);
        }
        if (reviewNeeded.length > 0) {
            // Step 374G: Needs Review sub-headers, mirroring Risk's grouping — but partitioned by the
            // SHARED _reviewSubtypeOf classifier (stamped as item._reviewSubtype at push), NOT a
            // typeLabel re-derivation. Counts == _computeRiskCounts.reviewSub by construction (both call
            // _reviewSubtypeOf). Order matches the Action Summary subtype line (coverage · one-sided ·
            // conflicting). Items with no subtype (e.g. Mode-A deviations) default to Coverage Questions.
            // Step 374Q: 'consequence_not_assessed' is its own truthful sub-header (defaulted consequence),
            // split out from Coverage Questions and from the withheld "Conflicting Reading" label.
            var reviewConsNotAssessed = reviewNeeded.filter(function(i) { return i._reviewSubtype === 'consequence_not_assessed'; });
            var reviewCoverage    = reviewNeeded.filter(function(i) { return i._reviewSubtype !== 'possible_one_sided' && i._reviewSubtype !== 'conflicting_reading' && i._reviewSubtype !== 'consequence_not_assessed'; });
            var reviewOneSided    = reviewNeeded.filter(function(i) { return i._reviewSubtype === 'possible_one_sided'; });
            var reviewConflicting = reviewNeeded.filter(function(i) { return i._reviewSubtype === 'conflicting_reading'; });
            var reviewSubHtml = '';
            if (reviewCoverage.length > 0)
                reviewSubHtml += _navSubGroupWrap('review_coverage_' + tIdx, 'Coverage Questions', reviewCoverage.length,
                    reviewCoverage.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            if (reviewConsNotAssessed.length > 0)
                reviewSubHtml += _navSubGroupWrap('review_consnotassessed_' + tIdx, 'Consequence Not Assessed', reviewConsNotAssessed.length,
                    reviewConsNotAssessed.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            if (reviewOneSided.length > 0)
                reviewSubHtml += _navSubGroupWrap('review_onesided_' + tIdx, 'Possible One-Sided Terms', reviewOneSided.length,
                    reviewOneSided.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            if (reviewConflicting.length > 0)
                reviewSubHtml += _navSubGroupWrap('review_conflicting_' + tIdx, 'Conflicting Reading', reviewConflicting.length,
                    reviewConflicting.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId);
            html += _navSectionWrap('review_' + tIdx, '?', 'Needs Review', reviewNeeded.length,
                reviewSubHtml, jobId,
                "Potential exposure: protections may be incomplete or missing, terms may be one-sided, or readings may conflict. Attorney review recommended.");
        }
        if (improvement.length > 0)
            html += _navSectionWrap('improvement_' + tIdx, '✶', 'IMPROVEMENT', improvement.length,
                improvement.map(function(i) { return _navBuildUnifiedItem(i, tIdx); }).join(''), jobId,
                'Protection exists — could be tightened.');
        // Dedupe addressed chips: only gap items not also in risk/reviewNeeded/improvement
        var _lpWithIssues = new Set();
        function _splitPids(pid) {
            return String(pid || '').split(/[\s,]+/).map(function(s) { return s.trim(); }).filter(Boolean);
        }
        [risk, reviewNeeded, improvement].forEach(function(bucket) {
            bucket.forEach(function(i) { _splitPids(i.pid).forEach(function(id) { _lpWithIssues.add(id); }); });
        });
        var _chipSeen = new Set();
        var addressedChips = [];
        addressed.forEach(function(i) {
            if (i._item_type !== 'gap') return;
            var id = i.pid;
            if (!id || _chipSeen.has(id) || _lpWithIssues.has(id)) return;
            _chipSeen.add(id);
            addressedChips.push({ pid: id, name: i.name });
        });
        if (addressedChips.length > 0)
            html += _navSectionWrap('addressed_' + tIdx, '✓', 'ADDRESSED', addressedChips.length,
                _navAddressedChips(addressedChips, tIdx), jobId, 'No action recommended.');
        if (!risk.length && !reviewNeeded.length && !improvement.length && !addressed.length)
            html += '<div class="nav-empty">No findings</div>';
        html += '</div>';
    });

    if (!html.trim()) html = '<div class="nav-empty-state">No open issues to review</div>';
    container.innerHTML = html;

    // Chip clicks → Coverage & Gaps
    container.querySelectorAll('.nav-chip').forEach(function(chip) {
        chip.addEventListener('click', function() {
            var pid = chip.dataset.pid;
            var tIdx = parseInt(chip.dataset.tenantIdx, 10);
            if (!isNaN(tIdx) && tIdx !== currentTenantIndex) currentTenantIndex = tIdx;
            if (typeof jumpHeatmapCell === 'function') jumpHeatmapCell(tIdx, pid);
            else if (window.CAM && typeof window.CAM.jumpToCoverageProvision === 'function')
                window.CAM.jumpToCoverageProvision(pid, { expandElements: true });
        });
    });

    // Item clicks — routed by _mode
    container.querySelectorAll('.nav-item-unified').forEach(function(btn) {
        btn.addEventListener('click', async function() {
            var pid = btn.dataset.pid;
            var tIdx = parseInt(btn.dataset.tenantIdx, 10);
            var mode = btn.dataset.mode;
            var cpfId = btn.dataset.cpfId || '';
            if (!isNaN(tIdx) && tIdx !== currentTenantIndex) {
                currentTenantIndex = tIdx;
                var ts = document.getElementById('tenant-select');
                if (ts) ts.value = String(tIdx);
                var dts = document.getElementById('docview-tenant-select');
                if (dts) dts.value = String(tIdx);
                if (typeof syncChatScopeToCurrentTenant === 'function') {
                    try { syncChatScopeToCurrentTenant(true); } catch(e) {}
                }
            }
            if (mode === 'synthesis') {
                if (typeof openContractDetail === 'function') {
                    await openContractDetail(isNaN(tIdx) ? 0 : tIdx);
                    switchResultsTab('synthesis');
                    setTimeout(function() {
                        var el = document.getElementById('cpf-' + cpfId.replace(/[^a-zA-Z0-9_-]/g, '_'));
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 200);
                }
            } else if (mode === 'c') {
                if (typeof jumpHeatmapCell === 'function') jumpHeatmapCell(tIdx, pid);
                else if (window.CAM && typeof window.CAM.jumpToCoverageProvision === 'function')
                    window.CAM.jumpToCoverageProvision(pid, { expandElements: true });
            } else {
                if (activeResultsTab === 'audittrail' && contractDetailOpen && currentTenantIndex === tIdx) {
                    if (typeof jumpToAuditProvision === 'function') jumpToAuditProvision(tIdx, pid);
                } else {
                    await openContractDetail(tIdx);
                    switchResultsTab('findings');
                    await waitForResultsTarget(function() {
                        return document.getElementById('dev-' + pid) ||
                               document.querySelector('[data-pid="' + CSS.escape(pid) + '"]');
                    });
                    if (typeof jumpToFinding === 'function') jumpToFinding(pid);
                }
            }
            updateNavActive(currentTenantIndex, pid);
        });
    });

    updateNavActive(currentTenantIndex);
}
window.CAM._navSectionToggle = _navSectionToggle;
window.CAM.classifyFindingType = classifyFindingType;
window.CAM.isPriorityReview = isPriorityReview; // Step 373: shared triage tier

// ── Boot ──
document.addEventListener("DOMContentLoaded", init);

})();


// ── Step 477: incomplete-report banner ───────────────────────────────────────
// Step 476 made the pipeline continue past an extraction-completeness failure and
// mark the result invalid_for_legal_analysis instead of dying. Nothing rendered
// those markers, so a degraded run displayed as a normal completed report -- a
// silent success in place of a loud failure. This renders the statement ABOVE the
// deal brief and every summary counter, because Step 461 recorded a counter
// improving while the answer got worse.
function renderIncompleteBanner() {
    var el = document.getElementById('incomplete-report-banner');
    if (!el) return;
    if (!currentResults || !currentResults.tenants) { el.classList.add('hidden'); return; }

    var stmts = [];
    var lps = {};
    currentResults.tenants.forEach(function (t) {
        var r = t && t.results;
        if (!r) return;
        if (r.invalid_for_legal_analysis || r.extraction_completeness_failed) {
            if (r.degraded_statement) stmts.push(r.degraded_statement);
            (r.extraction_completeness_failed_lps || []).forEach(function (lp) { lps[lp] = 1; });
        }
    });
    if (!stmts.length) { el.classList.add('hidden'); el.innerHTML = ''; return; }

    var ids = Object.keys(lps).sort();
    el.className = 'incomplete-report-banner';
    el.innerHTML =
        '<div class="incomplete-report-banner__title">&#9888; INCOMPLETE REPORT &mdash; NOT VALID FOR LEGAL ANALYSIS</div>' +
        stmts.map(function (m) {
            return '<div class="incomplete-report-banner__body">' + esc(m) + '</div>';
        }).join('') +
        (ids.length
            ? '<div class="incomplete-report-banner__lps">Issue areas with no evidence: <strong>'
              + esc(ids.join(', ')) + '</strong></div>'
            : '');
    el.classList.remove('hidden');
}

// Step 497: panel substitution. A SEPARATE banner from the one above, because it
// is a separate fact: incompleteness means part of the document was not analysed,
// substitution means the panel that analysed it was not the panel named. Runs with
// run_degraded=True and degraded_reason='evaluator_fallback' set
// invalid_for_legal_analysis=False, so the banner above stays hidden for them --
// Step 487's two deployed runs disclosed nothing anywhere.
// The escaper in this file is esc(), NOT escapeHtml -- see Step 477.
function renderPanelBanner() {
    var el = document.getElementById('panel-substitution-banner');
    if (!el) return;
    if (!currentResults || !currentResults.tenants) { el.classList.add('hidden'); return; }

    var lines = [];
    currentResults.tenants.forEach(function (t) {
        var r = t && t.results;
        if (!r) return;
        var ps = r.panel_substitution || {};
        if (r.panel_substituted || ps.tier === 'substituted') {
            if (r.panel_substitution_statement) lines.push(r.panel_substitution_statement);
        }
    });
    if (!lines.length) { el.classList.add('hidden'); el.innerHTML = ''; return; }

    el.className = 'panel-substitution-banner';
    el.innerHTML =
        '<div class="panel-substitution-banner__title">&#9888; PANEL SUBSTITUTED &mdash; NOT THE EVALUATOR PANEL THIS REPORT NAMES</div>' +
        lines.map(function (m) {
            return '<div class="panel-substitution-banner__body">' + esc(m) + '</div>';
        }).join('');
    el.classList.remove('hidden');
}
