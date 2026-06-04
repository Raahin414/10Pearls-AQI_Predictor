from __future__ import annotations

import numpy as np
import pandas as pd

from karachi_aqi.config.constants import TARGET_COLUMNS
from karachi_aqi.features import FeatureEngineer


def make_raw(days: int = 90) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "AQI": 80 + np.sin(np.arange(days) / 5) * 10,
            "PM2_5": 25 + np.sin(np.arange(days) / 4) * 5,
            "PM10": 50,
            "NO2": 20,
            "SO2": 8,
            "CO": 700,
            "O3": 40,
            "Temperature": 28,
            "Humidity": 60,
            "Precipitation": 0,
            "wind_speed": 8,
            "wind_direction": 180,
            "apparent_temp": 30,
            "surface_pressure": 1005,
            "wind_gusts": 16,
            "BLH": 900,
            "cloud_cover": 20,
            "shortwave_rad": 220,
            "uv_index": 5,
            "aod": 0.4,
            "dust": 12,
        }
    )


def test_feature_engineer_creates_targets_and_lags() -> None:
    frame = FeatureEngineer().transform(make_raw(), keep_unlabeled_tail=False)

    assert not frame.empty
    assert set(TARGET_COLUMNS).issubset(frame.columns)
    assert {"AQI_lag_7", "AQI_roll_mean_14", "PM2_5_t1", "dew_point"}.issubset(frame.columns)
    assert frame[TARGET_COLUMNS].isna().sum().sum() == 0
