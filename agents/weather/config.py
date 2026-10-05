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

SENTINEL_VALUES = {
    "ALLSKY_SFC_SW_DWN": [-999],
    "CLRSKY_SFC_SW_DWN": [-999],
}

# Long unresolved gaps are deliberately not auto-imputed.
MAX_INTERPOLATION_GAP = 6
