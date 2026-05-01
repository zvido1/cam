"""
CAM Lease Review — Provision Taxonomy

Defines the default lease provisions for analysis.
Supports custom provisions added by users.
"""

PROVISIONS = [
    {
        "id": "LP-00",
        "name": "Parties & Premises",
        "description": (
            "Extract contract identifying fields: landlord entity, tenant entity, "
            "property name/address, suite/unit, square footage, commencement date, "
            "expiration date, and guarantors. "
            "What gets flagged depends on run configuration: by default, flags only "
            "if landlord entity or property address differs from the reference. "
            "Tenant name, suite, and dates are fill-in fields and are not flagged "
            "unless explicitly configured. In metadata-only mode, no verdict is issued."
        ),
        "search_hints": [
            "landlord", "tenant", "premises", "property", "suite", "square feet",
            "commencement", "expiration", "guarantor", "lessor", "lessee"
        ],
        "default_enabled": True,
        "always_on": True,
        "identity_check": True,
    },
    {
        "id": "LP-01",
        "name": "Rent & Payment Terms",
        "description": "Base rent amount, payment schedule, late fees, accepted payment methods, additional rent definitions",
        "search_hints": ["base rent", "monthly rent", "payment", "late charge", "additional rent", "net lease"],
        "default_enabled": True,
    },
    {
        "id": "LP-02",
        "name": "Rent Escalation",
        "description": "Annual rent increase mechanism, escalation caps, CPI adjustments vs fixed percentage increases",
        "search_hints": ["escalation", "annual increase", "CPI", "consumer price index", "rent adjustment", "percentage increase"],
        "default_enabled": True,
    },
    {
        "id": "LP-03",
        "name": "Lease Term & Renewal",
        "description": "Initial term duration, renewal options, notice periods for renewal, holdover provisions",
        "search_hints": ["lease term", "renewal", "option to renew", "expiration", "commencement", "holdover"],
        "default_enabled": True,
    },
    {
        "id": "LP-04",
        "name": "Security Deposit",
        "description": "Deposit amount, return conditions, interest on deposit, permitted deductions, letter of credit alternatives",
        "search_hints": ["security deposit", "deposit", "return", "deduction", "letter of credit"],
        "default_enabled": True,
    },
    {
        "id": "LP-05",
        "name": "Permitted Use",
        "description": "Allowed business activities, exclusive use rights, restrictions on operations, continuous operation requirements",
        "search_hints": ["permitted use", "exclusive use", "restriction", "continuous operation", "business activity"],
        "default_enabled": True,
    },
    {
        "id": "LP-06",
        "name": "Maintenance & Repairs",
        "description": "Structural vs routine maintenance obligations, HVAC responsibility, plumbing, who pays for what repairs",
        "search_hints": ["maintenance", "repair", "structural", "HVAC", "plumbing", "roof", "tenant responsibility"],
        "default_enabled": True,
    },
    {
        "id": "LP-07",
        "name": "Common Area Maintenance (CAM)",
        "description": "Tenant's proportionate share of CAM charges, what costs are included/excluded, caps on CAM increases, audit rights",
        "search_hints": ["common area", "CAM charges", "proportionate share", "operating expenses", "audit"],
        "default_enabled": True,
    },
    {
        "id": "LP-08",
        "name": "Insurance Requirements",
        "description": "Required insurance types and minimum coverage amounts, named insured parties, rental interruption insurance",
        "search_hints": ["insurance", "liability", "coverage", "named insured", "rental interruption", "property insurance"],
        "default_enabled": True,
    },
    {
        "id": "LP-09",
        "name": "Subletting & Assignment",
        "description": "Right to sublet or assign lease, landlord approval requirements, affiliate exceptions, profit sharing on sublets",
        "search_hints": ["sublet", "subletting", "assignment", "assign", "consent", "affiliate", "transfer"],
        "default_enabled": True,
    },
    {
        "id": "LP-10",
        "name": "Alterations & Improvements",
        "description": "Right to modify leased space, approval requirements, ownership of tenant improvements at lease end",
        "search_hints": ["alteration", "improvement", "modification", "tenant improvement", "approval", "restoration"],
        "default_enabled": True,
    },
    {
        "id": "LP-11",
        "name": "Default & Remedies",
        "description": "Events constituting default, cure periods, landlord and tenant remedies, acceleration of rent",
        "search_hints": ["default", "event of default", "cure period", "remedy", "termination", "acceleration"],
        "default_enabled": True,
    },
    {
        "id": "LP-12",
        "name": "Early Termination",
        "description": "Conditions allowing early lease termination, termination penalties/fees, required notice periods",
        "search_hints": ["early termination", "termination right", "termination fee", "break clause", "exit"],
        "default_enabled": True,
    },
    {
        "id": "LP-13",
        "name": "Indemnification & Liability",
        "description": "Mutual or one-way indemnification obligations, scope of indemnity, caps on liability, waiver of consequential damages",
        "search_hints": ["indemnification", "indemnify", "liability", "hold harmless", "consequential damages", "cap", "limitation"],
        "default_enabled": True,
    },
    {
        "id": "LP-14",
        "name": "Force Majeure",
        "description": "Excused performance events, rent abatement during force majeure, suspension of obligations, definition of qualifying events",
        "search_hints": ["force majeure", "act of God", "excused performance", "casualty", "abatement", "suspension"],
        "default_enabled": True,
    },
    {
        "id": "LP-15",
        "name": "Signage Rights",
        "description": "Exterior and interior signage rights, approval process, specifications, compliance with codes",
        "search_hints": ["signage", "sign", "exterior sign", "pylon", "directory", "approval"],
        "default_enabled": True,
    },
    {
        "id": "LP-16",
        "name": "Parking",
        "description": "Allocated parking spaces, cost per space, reserved vs unreserved, visitor parking, modifications to parking areas",
        "search_hints": ["parking", "spaces", "reserved", "unreserved", "parking area", "allocation"],
        "default_enabled": True,
    },
    {
        "id": "LP-17",
        "name": "Dispute Resolution",
        "description": "Mediation, arbitration, or litigation requirements, venue and jurisdiction, attorney fee allocation, waiver of jury trial",
        "search_hints": ["dispute", "arbitration", "mediation", "litigation", "jurisdiction", "attorney fees", "jury trial"],
        "default_enabled": True,
    },
    {
        "id": "LP-18",
        "name": "Holdover Provisions",
        "description": "Post-lease holdover terms, holdover rent rate multiplier, conversion to month-to-month tenancy, notice requirements",
        "search_hints": ["holdover", "month-to-month", "post-expiration", "holdover rent"],
        "default_enabled": True,
    },
    {
        "id": "LP-19",
        "name": "Utilities",
        "description": "Allocation of utility costs (electric, gas, water, sewer, telecom, trash), submetering rights, service interruption remedies, responsibility for installation and upgrade costs",
        "search_hints": ["utility", "utilities", "electric", "gas", "water", "sewer", "submetering", "service interruption"],
        "default_enabled": True,
    },
    {
        "id": "LP-20",
        "name": "Exclusivity",
        "description": "Tenant's exclusive use right scope, carve-outs for existing or ancillary tenants, radius restriction, definition of competing use, remedies for landlord violation",
        "search_hints": ["exclusive use", "exclusivity", "exclusive right", "competing use", "no competing", "radius restriction"],
        "default_enabled": True,
    },
    {
        "id": "LP-21",
        "name": "Guaranty of Lease",
        "description": "Guarantor identification, scope and type of guaranty (full, limited, good guy, burndown), recourse mechanism, duration, release conditions, survival after assignment",
        "search_hints": ["guaranty", "guarantor", "personal guarantee", "corporate guarantee", "good guy guaranty", "burndown guaranty"],
        "default_enabled": True,
    },
    {
        "id": "LP-22",
        "name": "SNDA (Subordination, Non-Disturbance & Attornment)",
        "description": "Subordination of lease to senior mortgage, non-disturbance covenant from lender, attornment obligation on foreclosure, SNDA form approval right, lender execution deadline",
        "search_hints": ["SNDA", "subordination", "non-disturbance", "attornment", "lender", "mortgagee", "deed of trust"],
        "default_enabled": True,
    },
    {
        "id": "LP-23",
        "name": "Percentage Rent",
        "description": "Gross sales definition, percentage rate and breakpoint, reporting period and frequency, landlord audit rights, exclusions from gross sales",
        "search_hints": ["percentage rent", "gross sales", "natural breakpoint", "breakpoint", "overage rent", "percentage of gross"],
        "default_enabled": True,
    },
    {
        "id": "LP-24",
        "name": "Damage & Destruction",
        "description": "Landlord repair obligation after casualty, rent abatement during repair, repair deadline, tenant termination right on prolonged repair, total loss threshold",
        "search_hints": ["casualty", "damage", "destruction", "restore", "rebuild", "fire", "repair obligation"],
        "default_enabled": True,
    },
    {
        "id": "LP-25",
        "name": "Condemnation / Eminent Domain",
        "description": "Total vs. material partial taking definition, termination right, rent abatement on partial taking, condemnation award allocation, tenant's separate award for fixtures and improvements",
        "search_hints": ["condemnation", "eminent domain", "taking", "condemning authority", "governmental acquisition"],
        "default_enabled": True,
    },
    {
        "id": "LP-26",
        "name": "Quiet Enjoyment",
        "description": "Express landlord covenant of quiet enjoyment, conditioned on tenant's performance, binding on successors and lenders",
        "search_hints": ["quiet enjoyment", "quiet possession", "peaceable enjoyment", "undisturbed possession"],
        "default_enabled": True,
    },
    {
        "id": "LP-27",
        "name": "Landlord Default & Tenant Remedies",
        "description": "Landlord default definition, notice and cure period, tenant self-help right, rent offset, tenant termination right, lender cure period, landlord liability limitation",
        "search_hints": ["landlord default", "landlord's default", "landlord fails", "tenant's remedies", "self-help", "landlord's failure"],
        "default_enabled": True,
    },
    {
        "id": "LP-28",
        "name": "Compliance with Laws",
        "description": "Tenant compliance obligation for tenant's use, landlord delivery in compliance, structural vs. use-specific cost allocation, ADA responsibility, future law changes, grandfathering",
        "search_hints": ["comply", "compliance", "applicable laws", "codes", "regulations", "ADA", "Americans with Disabilities"],
        "default_enabled": True,
    },
    {
        "id": "LP-29",
        "name": "Right of Entry / Landlord Access",
        "description": "Notice period before entry, permitted purposes, emergency entry without notice, tenant representative right, entry frequency or timing restrictions, non-interference obligation",
        "search_hints": ["right of entry", "landlord access", "right to enter", "inspection right", "landlord may enter"],
        "default_enabled": True,
    },
    {
        "id": "LP-30",
        "name": "Estoppel Certificate",
        "description": "Tenant obligation to provide estoppel certificate on request, response deadline, certificate form and content scope, deemed-approval consequence, frequency limitation",
        "search_hints": ["estoppel", "estoppel certificate", "tenant estoppel", "certify", "certificate of lease status"],
        "default_enabled": True,
    },
    {
        "id": "LP-31",
        "name": "Co-Tenancy",
        "description": "Opening and ongoing co-tenancy conditions, anchor tenant definition, remedy during co-tenancy failure, cure period, termination right, occupancy threshold",
        "search_hints": ["co-tenancy", "anchor tenant", "co-anchor", "occupancy threshold", "go dark", "major tenant"],
        "default_enabled": True,
    },
    {
        "id": "LP-32",
        "name": "Hazardous Materials",
        "description": "Definition of prohibited substances, carve-out for ordinary business materials, remediation obligation, pre-existing contamination representations, tenant notification obligations",
        "search_hints": ["hazardous", "hazmat", "environmental", "toxic", "contaminant", "remediation", "CERCLA", "RCRA"],
        "default_enabled": True,
    },
]

# Quick lookup by ID
_PROVISION_MAP = {p["id"]: p for p in PROVISIONS}


def get_provision(provision_id: str) -> dict:
    """Get a single provision by ID. Returns None if not found."""
    return _PROVISION_MAP.get(provision_id)


def get_active_provisions(
    selected_ids: list = None,
    custom_provisions: list = None,
) -> list:
    """Return only the provisions the user selected, plus any custom ones.

    Args:
        selected_ids: List of provision IDs to include (e.g. ["LP-01", "LP-09"]).
                      If None, all default-enabled provisions are included.
        custom_provisions: List of custom provision dicts with at minimum
                          {"id": "CUSTOM-01", "name": "...", "description": "..."}.

    Returns:
        List of provision dicts ready for the extraction prompt.
    """
    # Always include always_on provisions (LP-00) first
    always_on = [p for p in PROVISIONS if p.get("always_on", False)]
    active = [p for p in PROVISIONS if p.get("default_enabled", True) and not p.get("always_on", False)]
    active = always_on + active

    if custom_provisions:
        for cp in custom_provisions:
            if "id" not in cp:
                cp["id"] = f"CUSTOM-{len(active) + 1:02d}"
            if "search_hints" not in cp:
                cp["search_hints"] = []
            if "default_enabled" not in cp:
                cp["default_enabled"] = True
            active.append(cp)

    return active


def make_custom_provision(name: str, index: int, section_ref: str = "") -> dict:
    """Create a CUSTOM-XX provision dict for a discovered unique provision.

    Args:
        name: Human-readable name for this provision.
        index: Sequential number for the CUSTOM-XX ID (e.g. 1 → CUSTOM-01).
        section_ref: Optional section reference hint for extraction context.

    Returns:
        A provision dict compatible with get_active_provisions() output.
    """
    pid = f"CUSTOM-{index:02d}"
    return {
        "id": pid,
        "name": name,
        "description": f"Unique provision discovered in template: {name}. "
                       f"Not part of the standard provision taxonomy.",
        "search_hints": [name.lower(), section_ref] if section_ref else [name.lower()],
        "default_enabled": True,
        "discovered": True,
        "section_ref": section_ref,
    }
