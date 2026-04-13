    with open(latest, encoding="utf-8") as f:
        r = json.load(f)

    ca = r.get("coverage_assessment", [])
    if not ca:
        print("No coverage_assessment in results — run Step 244 first.")
        sys.exit(0)

    # Dry-run: schema only (no API calls)
    print(f"\nDry-run (schema only) -- {len(ca)} issue areas:\n")

    model_would_fire = 0
    for assessment in ca:
        mat = _classify_materiality(assessment)
        pcls = _classify_partial(assessment, mat)
        state = assessment.get("coverage_state", "")
        pid = assessment.get("issue_area_id", "")
        name = assessment.get("issue_area_name", pid)

        # Would model fire?
        would_use_model = (
            state in _MODEL_STATES
            or (mat == "high" and state in ("partial", "missing"))
        )
        if would_use_model:
            model_would_fire += 1

        # Schema exposure
        exposure = _build_schema_exposure(assessment)
        stmt = exposure["exposure_statement"]

        source_marker = "[MODEL]" if would_use_model else "[schema]"
        mat_marker = {"high": "[H]", "medium": "[M]", "low": "[L]"}.get(mat, "?")
        print(f"  {mat_marker} {source_marker} {pid} {name[:28]}: {state}")
        if would_use_model or mat != "low":
            print(f"    -> {stmt[:90]}{'...' if len(stmt) > 90 else ''}")
        if pcls:
            print(f"    partial_class: {pcls}")

    print(f"\nSummary: {model_would_fire} would invoke model, "
          f"{len(ca) - model_would_fire} schema-only")
    print("(Dry-run complete -- no API calls made)")
