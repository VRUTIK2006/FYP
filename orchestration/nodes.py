from .state import FYPState

from agents.solar.agent import run_agent as run_solar_agent
from agents.wind.agent import run_agent as run_wind_agent
from agents.demand.agent import run_agent as run_demand_agent
from agents.optimization.agent import run_agent as run_optimization_agent
from datetime import datetime, timedelta

def _solar_horizon(name: str) -> str:
    mapping = {
        "1h": "1_hour",
        "1d": "1_day",
        "1w": "1_week",
        "15d": "15_days",
    }

    if name not in mapping:
        raise ValueError(f"Unsupported Solar horizon: {name}")

    return mapping[name]


def _wind_horizon(name: str) -> str:
    # Wind agent uses the common FYP naming.
    return name


def _demand_horizon(name: str) -> str:
    # Demand agent uses the common FYP naming.
    return name

def _error(state: FYPState, agent: str, message: str) -> FYPState:
    errors = list(state.get("errors", []))

    errors.append({
        "agent": agent,
        "message": message,
    })

    return {
        **state,
        "status": "error",
        "errors": errors,
    }


def solar_node(state: FYPState) -> FYPState:
    """Execute Solar Agent."""

    request = {
        "request_id": f"{state['request_id']}_solar",
        "timestamp": state["timestamp"],
        "location": state["location"],
        "horizon": {
        "name": _solar_horizon(state["horizon_name"]),
        "hours": state["horizon_hours"],
        },
        "data": {
            "source": state["solar_source"],
            "forecast_origin": state["forecast_origin"],
        },
        "config": {
            "save_output": True,
        },
    }

    response = run_solar_agent(request)

    if response.get("status") != "success":
        return {
            "status": "error",
            "errors": [{
                "agent": "solar",
                "message": str(response.get("error")),
            }],
        }

    return {
        "solar_result": response,
    }

def wind_node(state: FYPState) -> FYPState:
    """Execute Wind Agent."""

    request = {
        "request_id": f"{state['request_id']}_wind",
        "timestamp": state["timestamp"],
        "location": state["location"],
        "horizon": {
        "name": _wind_horizon(state["horizon_name"]),
        "hours": state["horizon_hours"],
    },
        "data": {
            "source": state["wind_source"],
            "forecast_origin": state["forecast_origin"],
        },
        "config": {
            "save_output": True,
        },
    }

    response = run_wind_agent(request)

    if response.get("status") != "success":
        return {
            "status": "error",
            "errors": [{
                "agent": "wind",
                "message": str(response.get("error")),
            }],
        }

    return {
        "wind_result": response,
    }

def demand_node(state: FYPState) -> FYPState:
    """Execute Demand Agent."""

    request = {
        "request_id": f"{state['request_id']}_demand",
        "timestamp": state["timestamp"],
        "location": state["location"],
        "horizon": {
        "name": _demand_horizon(state["horizon_name"]),
        "hours": state["horizon_hours"],
    },
        "data": {
            "source": state["demand_source"],
        },
        "config": {
            "save_output": True,
        },
    }

    response = run_demand_agent(request)

    if response.get("status") != "success":
        return {
            "status": "error",
            "errors": [{
                "agent": "demand",
                "message": str(response.get("error")),
            }],
        }

    return {
        "demand_result": response,
    }

def _extract_forecast(
    result: dict,
    agent_name: str,
    forecast_origin: str,
    horizon_hours: int,
):
    """
    Extract forecast values from a standardized agent response.

    Timestamps are derived from forecast_origin when the agent
    does not explicitly return them.
    """

    data = result.get("result", result)

    forecast = (
        data.get("forecast")
        or data.get("forecast_values")
        or data.get("predictions")
        or data.get(f"{agent_name}_forecast")
    )

    if forecast is None:
        raise ValueError(
            f"{agent_name} result does not contain a forecast."
        )

    forecast = list(forecast)

    # Try agent-provided timestamps first.
    timestamps = (
        data.get("timestamps")
        or data.get("prediction_timestamps")
        or data.get("forecast_timestamps")
    )

    if timestamps:
        timestamps = list(timestamps)

    else:
        # Derive timestamps from forecast origin.
        origin = datetime.fromisoformat(
            forecast_origin.replace("Z", "+00:00")
        )

        timestamps = [
            (
                origin + timedelta(hours=i + 1)
            ).isoformat()
            for i in range(len(forecast))
        ]

    return forecast, timestamps

def prepare_forecasts(state: FYPState) -> FYPState:
    """
    Collect raw prediction objects from Solar, Wind and Demand
    and normalise them into plain float lists for the optimizer.
    """

    if state.get("status") == "error":
        return state

    try:
        solar_result = state["solar_result"]
        wind_result = state["wind_result"]
        demand_result = state["demand_result"]

        # --- Solar: result["result"]["forecast"] ---
        # Each item: {timestamp, forecast_mu, q10, q90}
        solar_raw = solar_result.get("result", {}).get("forecast", [])
        solar_data = [float(item["forecast_mu"]) for item in solar_raw]
        timestamps = [item["timestamp"] for item in solar_raw]

        # --- Wind: result["result"]["predictions"] ---
        # Each item: {datetime, predicted, actual}
        wind_raw = wind_result.get("result", {}).get("predictions", [])
        wind_data = [float(item["predicted"]) for item in wind_raw]

        # --- Demand: result["result"]["predictions"] ---
        # Each item: {datetime, forecast, lower_10, upper_90}
        demand_raw = demand_result.get("result", {}).get("predictions", [])
        demand_data = [float(item["forecast"]) for item in demand_raw]

        if not solar_data:
            return _error(
                state,
                "orchestration",
                "Solar predictions are empty.",
            )

        if not wind_data:
            return _error(
                state,
                "orchestration",
                "Wind predictions are empty.",
            )

        if not demand_data:
            return _error(
                state,
                "orchestration",
                "Demand predictions are empty.",
            )

        if not timestamps:
            return _error(
                state,
                "orchestration",
                "No forecast timestamps returned.",
            )

        lengths = {
            "solar": len(solar_data),
            "wind": len(wind_data),
            "demand": len(demand_data),
            "timestamps": len(timestamps),
        }

        if len(set(lengths.values())) != 1:
            return _error(
                state,
                "orchestration",
                f"Forecast length mismatch: {lengths}",
            )

        return {
            "solar_forecast": solar_data,
            "wind_forecast": wind_data,
            "demand_forecast": demand_data,
            "timestamps": list(timestamps),
            "status": "ready_for_optimization",
        }

    except Exception as exc:
        return _error(
            state,
            "orchestration",
            str(exc),
        )

def optimization_node(state: FYPState) -> FYPState:

    if state.get("status") == "error":
        return state

    request = {
        "request_id": f"{state['request_id']}_optimization",
        "timestamp": state["timestamp"],
        "location": state["location"],
        "horizon": {
            "name": state["horizon_name"],
            "hours": state["horizon_hours"],
        },
        "data": {
            "solar_forecast": state["solar_forecast"],
            "wind_forecast": state["wind_forecast"],
            "demand_forecast": state["demand_forecast"],
            "timestamps": state["timestamps"],
        },
        "config": {},
    }

    response = run_optimization_agent(request)

    if response.get("status") != "success":
        return _error(
            state,
            "optimization",
            str(response.get("error")),
        )

    return {
        "optimization_result": response,
        "status": "completed",
    }