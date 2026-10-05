"""Chronos-2 forecasting implementation for the Solar Agent.

This module contains production forecasting only. Historical backtesting and
metric calculation remain separate from the agent.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd

from .config import (
    CONTEXT_LENGTH,
    DATETIME_COLUMN,
    DEVICE,
    FUTURE_COVARIATES,
    HORIZONS,
    ID_COLUMN,
    MODEL_NAME,
    POINT_QUANTILE,
    QUANTILE_LEVELS,
    TARGET_COLUMN,
    FEATURE_COLUMNS,
    HISTORICAL_ONLY_FEATURES,
)


@lru_cache(maxsize=1)
def _load_pipeline():
    """Load Chronos-2 once per Python process."""
    try:
        from chronos import Chronos2Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "Chronos-2 is not installed. Install the project's "
            "chronos-forecasting dependency first."
        ) from exc

    return Chronos2Pipeline.from_pretrained(
        MODEL_NAME,
        device_map=DEVICE,
    )


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create the two cyclic calendar feature pairs when absent."""
    out = df.copy()
    dt = pd.to_datetime(out[DATETIME_COLUMN], errors="coerce")

    if dt.isna().any():
        raise ValueError(f"{DATETIME_COLUMN} contains invalid timestamps.")

    if "hour_sin" not in out.columns:
        import numpy as np
        out["hour_sin"] = np.sin(2 * np.pi * dt.dt.hour / 24.0)
    if "hour_cos" not in out.columns:
        import numpy as np
        out["hour_cos"] = np.cos(2 * np.pi * dt.dt.hour / 24.0)
    if "day_of_year_sin" not in out.columns:
        import numpy as np
        out["day_of_year_sin"] = np.sin(
            2 * np.pi * (dt.dt.dayofyear - 1) / 365.25
        )
    if "day_of_year_cos" not in out.columns:
        import numpy as np
        out["day_of_year_cos"] = np.cos(
            2 * np.pi * (dt.dt.dayofyear - 1) / 365.25
        )

    return out


def _add_historical_target_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build target-derived features using only values available at each time."""
    out = df.copy()
    target = out[TARGET_COLUMN]

    out["solar_lag_1"] = target.shift(1)
    out["solar_lag_24"] = target.shift(24)
    out["solar_lag_168"] = target.shift(168)
    out["solar_rolling_mean_24"] = target.shift(1).rolling(24).mean()
    out["solar_rolling_mean_168"] = target.shift(1).rolling(168).mean()

    return out


def _validate_base_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required = [DATETIME_COLUMN, TARGET_COLUMN, *(
        c for c in FEATURE_COLUMNS
        if c not in HISTORICAL_ONLY_FEATURES
        and c not in {"hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos"}
    )]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Solar dataset is missing required columns: {missing}")

    out = df.copy()
    out[DATETIME_COLUMN] = pd.to_datetime(out[DATETIME_COLUMN], errors="coerce")
    if out[DATETIME_COLUMN].isna().any():
        raise ValueError("Solar dataset contains invalid datetime values.")

    out = out.sort_values(DATETIME_COLUMN).drop_duplicates(DATETIME_COLUMN)
    out = _add_time_features(out)
    out = _add_historical_target_features(out)
    return out


def _resolve_horizon(horizon: dict[str, Any]) -> tuple[str, int]:
    name = str(horizon.get("name", "1_day"))
    if name not in HORIZONS:
        allowed = ", ".join(HORIZONS)
        raise ValueError(f"Unsupported solar horizon '{name}'. Use one of: {allowed}")

    requested_hours = horizon.get("hours")
    hours = int(requested_hours) if requested_hours else HORIZONS[name]

    if hours != HORIZONS[name]:
        raise ValueError(
            f"Horizon '{name}' is configured for {HORIZONS[name]} hours, "
            f"but {hours} was requested."
        )

    return name, hours


def _get_forecast_origin(
    df: pd.DataFrame,
    forecast_origin: str | None,
) -> pd.Timestamp:
    if forecast_origin is None:
        return pd.Timestamp(df[DATETIME_COLUMN].max())

    origin = pd.Timestamp(forecast_origin)
    if origin not in set(df[DATETIME_COLUMN]):
        raise ValueError(
            f"forecast_origin {origin} is not present in the source dataset."
        )
    return origin


def forecast_solar(
    source_df: pd.DataFrame,
    *,
    horizon_name: str,
    horizon_hours: int,
    forecast_origin: str | None = None,
) -> dict[str, Any]:
    """Run one Chronos-2 solar forecast.

    For historical replay/testing, source_df may contain both context and the
    subsequent rows. For real deployment, the rows after forecast_origin must
    contain forecasted/known weather covariates; future solar output is never
    supplied to Chronos-2.
    """
    df = _validate_base_dataframe(source_df)
    origin = _get_forecast_origin(df, forecast_origin)

    context = df[df[DATETIME_COLUMN] <= origin].tail(CONTEXT_LENGTH).copy()
    future = df[df[DATETIME_COLUMN] > origin].head(horizon_hours).copy()

    if len(context) < CONTEXT_LENGTH:
        raise ValueError(
            f"Need {CONTEXT_LENGTH} historical rows before the forecast origin; "
            f"only {len(context)} are available."
        )

    if len(future) < horizon_hours:
        raise ValueError(
            f"Need {horizon_hours} future weather rows after {origin}; "
            f"only {len(future)} are available. "
            "Provide a future weather-forecast dataset for live forecasting."
        )

    # Chronos-2 expects an ID column.
    context[ID_COLUMN] = "gujarat_solar"
    future[ID_COLUMN] = "gujarat_solar"

    # Historical input: target + all configured features.
    context_columns = [
        ID_COLUMN,
        DATETIME_COLUMN,
        TARGET_COLUMN,
        *FEATURE_COLUMNS,
    ]
    context = context[context_columns]

    # Future input: ID + timestamp + only genuinely known covariates.
    # Target and all target-derived features are intentionally excluded.
    future_columns = [
        ID_COLUMN,
        DATETIME_COLUMN,
        *FUTURE_COVARIATES,
    ]
    future = future[future_columns]

    # Fail early rather than silently passing NaNs into the model.
    if context.isna().any().any():
        bad = context.columns[context.isna().any()].tolist()
        raise ValueError(
            f"Historical context contains missing values in: {bad}. "
            "Clean/validate the weather data before forecasting."
        )

    if future[FUTURE_COVARIATES].isna().any().any():
        bad = future[FUTURE_COVARIATES].columns[
            future[FUTURE_COVARIATES].isna().any()
        ].tolist()
        raise ValueError(
            f"Future weather covariates contain missing values in: {bad}. "
            "A complete future weather forecast is required."
        )

    pipeline = _load_pipeline()

    prediction = pipeline.predict_df(
        context,
        future_df=future,
        prediction_length=horizon_hours,
        quantile_levels=QUANTILE_LEVELS,
        id_column=ID_COLUMN,
        timestamp_column=DATETIME_COLUMN,
        target=TARGET_COLUMN,
        context_length=CONTEXT_LENGTH,
    )

    # Chronos-2 returns one row per forecast timestamp. The exact quantile
    # column labels are normalized here so the agent output stays stable.
    prediction = prediction.copy()
    prediction[DATETIME_COLUMN] = pd.to_datetime(
        prediction[DATETIME_COLUMN], errors="coerce"
    )

    def _find_quantile_column(level: float):
        candidates = [
            str(level),
            level,
            f"q{level}",
            f"quantile_{level}",
        ]
        for candidate in candidates:
            if candidate in prediction.columns:
                return candidate
        # Numeric column labels are common in forecast DataFrames.
        for col in prediction.columns:
            try:
                if abs(float(col) - level) < 1e-9:
                    return col
            except (TypeError, ValueError):
                pass
        return None

    q10 = _find_quantile_column(0.1)
    q50 = _find_quantile_column(0.5)
    q90 = _find_quantile_column(0.9)

    if q50 is None:
        raise RuntimeError(
            f"Could not locate the 0.5 quantile in Chronos-2 output. "
            f"Returned columns: {prediction.columns.tolist()}"
        )

    records = []
    for _, row in prediction.head(horizon_hours).iterrows():
        item = {
            "timestamp": row[DATETIME_COLUMN].isoformat(),
            "forecast_mu": float(row[q50]),
        }
        if q10 is not None:
            item["q10"] = float(row[q10])
        if q90 is not None:
            item["q90"] = float(row[q90])
        records.append(item)

    return {
        "model": MODEL_NAME,
        "horizon": horizon_name,
        "horizon_hours": horizon_hours,
        "forecast_origin": origin.isoformat(),
        "context_length": CONTEXT_LENGTH,
        "point_quantile": POINT_QUANTILE,
        "forecast": records,
    }
