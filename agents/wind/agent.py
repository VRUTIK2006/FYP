from datetime import datetime, timezone

from common.schemas import AgentInput, AgentOutput, AgentError
from .config import HORIZONS
from .forecasting import forecast_once
from .reporting import save_report


def run_agent(input_data: dict | AgentInput) -> dict:
    request = AgentInput.model_validate(input_data)
    try:
        dataset_path = request.data.get("source") or request.data.get("dataset_path")
        if not dataset_path:
            raise ValueError("Wind agent requires data.source or data.dataset_path pointing to a CSV dataset.")

        horizon_hours = request.horizon.hours
        horizon_name = request.horizon.name
        if horizon_name in HORIZONS and HORIZONS[horizon_name] != horizon_hours:
            raise ValueError(f"Horizon mismatch: {horizon_name} expects {HORIZONS[horizon_name]} hours, got {horizon_hours}.")

        result = forecast_once(
            dataset_path=dataset_path,
            horizon_hours=horizon_hours,
            forecast_origin=request.data.get("forecast_origin"),
            model_name=request.config.get("model_name", "amazon/chronos-2"),
        )

        if request.config.get("save_output", True):
            report_path = request.config.get("report_path", "reports/wind/wind_report.json")
            result["report_path"] = save_report(result, report_path)

        return AgentOutput(
            status="success",
            agent="wind",
            request_id=request.request_id,
            result=result,
            metadata={
                "location": request.location,
                "source": dataset_path,
                "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            error=None,
        ).model_dump()
    except Exception as exc:
        return AgentOutput(
            status="error",
            agent="wind",
            request_id=request.request_id,
            result=None,
            metadata={"location": request.location},
            error=AgentError(code=type(exc).__name__, message=str(exc)),
        ).model_dump()
