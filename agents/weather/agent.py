from __future__ import annotations

import time
from pathlib import Path

from common.schemas import AgentInput, AgentOutput, AgentError
from .diagnostics import (
    load_dataset, profile_dataset, validate_datetime, analyze_duplicates,
    analyze_missing_values, detect_sentinel_values, detect_domain_violations,
    analyze_statistics, detect_outliers,
)
from .decision import generate_decisions
from .cleaning import apply_cleaning
from .reporting import quality_impact, save_report

AGENT_NAME = "weather"
DEFAULT_INPUT = "data/weather/raw/dataset.csv"
DEFAULT_OUTPUT = "data/weather/processed/weather_cleaned_dataset.csv"
DEFAULT_REPORT = "reports/weather/weather_report.json"


def run_agent(input_data: dict | AgentInput) -> dict:
    started = time.perf_counter()
    request = input_data if isinstance(input_data, AgentInput) else AgentInput.model_validate(input_data)
    source = request.data.get("source", DEFAULT_INPUT)
    output_path = request.config.get("output_path", DEFAULT_OUTPUT)
    report_path = request.config.get("report_path", DEFAULT_REPORT)
    run_llm = bool(request.config.get("run_llm", False))

    try:
        df = load_dataset(source)
        profile = profile_dataset(df)
        datetime_result = validate_datetime(df)
        missing = analyze_missing_values(df)
        duplicates = analyze_duplicates(df)
        statistics = analyze_statistics(df)
        sentinel = detect_sentinel_values(df)
        domain = detect_domain_violations(df)
        outliers = detect_outliers(df)

        diagnostics = {
            "profile": profile,
            "datetime": datetime_result,
            "missing": missing,
            "duplicates": duplicates,
            "statistics": statistics,
            "sentinel": sentinel,
            "domain": domain,
            "outliers": outliers,
        }

        deterministic_decisions = generate_decisions(df, sentinel, domain, outliers)
        llm_analysis = None
        if run_llm:
            from .llm_decision import run_llm_decision
            llm_analysis = run_llm_decision(diagnostics)

        cleaned, execution_log = apply_cleaning(df, deterministic_decisions)
        final_missing = int(cleaned.isna().sum().sum())
        final_domain = detect_domain_violations(cleaned)
        final_validation = {
            "rows": int(len(cleaned)),
            "columns": int(len(cleaned.columns)),
            "missing_values": final_missing,
            "duplicate_rows": int(cleaned.duplicated().sum()),
            "domain_violations": final_domain,
            "ready_for_forecasting": final_missing == 0 and not final_domain,
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(output_path, index=False)

        result = {
            "cleaned_dataset_path": output_path,
            "diagnostics": diagnostics,
            "decisions": deterministic_decisions,
            "llm_analysis": llm_analysis,
            "execution_log": execution_log,
            "final_validation": final_validation,
            "quality_impact": quality_impact(df, cleaned, execution_log),
        }
        metadata = {
            "location": request.location,
            "source": source,
            "execution_time_seconds": round(time.perf_counter() - started, 3),
            "llm_enabled": run_llm,
        }
        payload = AgentOutput(
            status="success",
            agent=AGENT_NAME,
            request_id=request.request_id,
            result=result,
            metadata=metadata,
            error=None,
        ).model_dump()
        save_report(report_path, payload)
        return payload
    except Exception as exc:
        return AgentOutput(
            status="error",
            agent=AGENT_NAME,
            request_id=request.request_id,
            result=None,
            metadata={"execution_time_seconds": round(time.perf_counter() - started, 3)},
            error=AgentError(code=type(exc).__name__, message=str(exc)),
        ).model_dump()
