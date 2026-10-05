"""Standard Solar Agent interface."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from common.schemas import AgentInput, AgentOutput, AgentError

from .config import HORIZONS, MODEL_NAME
from .forecasting import forecast_solar


def _load_source(data: dict[str, Any]) -> pd.DataFrame:
    source = data.get("source")
    if not source:
        raise ValueError(
            "Solar input requires data.source pointing to a CSV containing "
            "historical solar generation and weather covariates."
        )

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Solar source file not found: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError("The current Solar Agent expects a CSV source.")

    return pd.read_csv(path)


def run_agent(input_data: dict[str, Any]) -> dict[str, Any]:
    """Run the standardized Solar Agent.

    Required:
        request_id, timestamp, location, horizon, data.source

    Optional:
        data.forecast_origin
        config.save_output
        config.output_path
    """
    request_id = str(input_data.get("request_id", "solar_unknown"))

    try:
        validated = AgentInput.model_validate(input_data)

        if validated.location != "Gujarat":
            # The current trained/evaluated configuration is specifically
            # for the Gujarat solar target.
            raise ValueError(
                "This Solar Agent configuration is currently for Gujarat."
            )

        horizon_name = validated.horizon.name
        horizon_hours = validated.horizon.hours

        if horizon_name not in HORIZONS:
            raise ValueError(
                f"Unsupported horizon '{horizon_name}'. "
                f"Allowed: {list(HORIZONS)}"
            )

        if horizon_hours != HORIZONS[horizon_name]:
            raise ValueError(
                f"Horizon '{horizon_name}' requires {HORIZONS[horizon_name]} hours."
            )

        df = _load_source(validated.data)

        forecast_origin = validated.data.get("forecast_origin")

        result = forecast_solar(
            df,
            horizon_name=horizon_name,
            horizon_hours=horizon_hours,
            forecast_origin=forecast_origin,
        )

        save_output = bool(validated.config.get("save_output", False))
        output_path = validated.config.get(
            "output_path",
            "reports/solar/latest_forecast.json",
        )

        if save_output:
            import json
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(result, indent=2),
                encoding="utf-8",
            )

        return AgentOutput(
            status="success",
            agent="solar",
            request_id=request_id,
            result=result,
            metadata={
                "location": validated.location,
                "model": MODEL_NAME,
                "execution_time_utc": datetime.now(timezone.utc).isoformat(),
                "forecast_origin": result["forecast_origin"],
            },
            error=None,
        ).model_dump()

    except Exception as exc:
        return AgentOutput(
            status="error",
            agent="solar",
            request_id=request_id,
            result=None,
            metadata={},
            error=AgentError(
                code=type(exc).__name__,
                message=str(exc),
            ),
        ).model_dump()
