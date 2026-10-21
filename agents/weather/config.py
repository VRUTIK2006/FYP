DOMAIN_RULES = {
    "RH2M": {"min": 0, "max": 100},
    "WS10M": {"min": 0},
    "WS50M": {"min": 0},
    "PS": {"min": 0},
    "WD10M": {"min": 0, "max": 360},
    "WD50M": {"min": 0, "max": 360},
    "Gujarat_Solar_MU_hourly_est": {"min": 0},
    "Gujarat_Wind_MU_hourly_est": {"min": 0},
    "Gujarat_Solar_MU_daily_total": {"min": 0},
    "Gujarat_Wind_MU_daily_total": {"min": 0},
    "PRECTOTCORR": {"min": 0},
}

# Regional Gujarat default, not a specific solar-plant location. Override these
# values when the plant coordinates are known.
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_LATITUDE = 22.3
WEATHER_LONGITUDE = 71.5
WEATHER_TIMEZONE = "Asia/Kolkata"
WEATHER_REQUEST_TIMEOUT = 30

SENTINEL_VALUES = {
    "ALLSKY_SFC_SW_DWN": [-999],
    "CLRSKY_SFC_SW_DWN": [-999],
}

# Long unresolved gaps are deliberately not auto-imputed.
MAX_INTERPOLATION_GAP = 6


# Multi-point regional clusters representing Gujarat's wind & solar generation hubs.
# Used for state-wide aggregate weather forecasting when no single plant location is specified.
DEFAULT_WEATHER_CLUSTERS = [
    {"name": "Kutch Wind Hub", "latitude": 23.25, "longitude": 69.67, "weight": 0.40},
    {"name": "Jamnagar/Saurashtra Coast", "latitude": 22.47, "longitude": 70.06, "weight": 0.30},
    {"name": "Bhavnagar Gulf Corridor", "latitude": 21.76, "longitude": 72.15, "weight": 0.20},
    {"name": "Central Gujarat", "latitude": 22.30, "longitude": 71.50, "weight": 0.10},
]
