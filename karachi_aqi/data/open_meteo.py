"""Open-Meteo client for Karachi AQI and weather data."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
import requests

from karachi_aqi.config.constants import KARACHI_LATITUDE, KARACHI_LONGITUDE, KARACHI_TIMEZONE
from karachi_aqi.config.settings import Settings, get_settings


AIR_ARCHIVE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

AIR_HOURLY = (
    "us_aqi,pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone,"
    "aerosol_optical_depth,dust,uv_index"
)
WEATHER_HOURLY = (
    "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,"
    "wind_direction_10m,apparent_temperature,surface_pressure,wind_gusts_10m,"
    "boundary_layer_height,cloud_cover,shortwave_radiation"
)

AIR_COLUMN_MAP = {
    "us_aqi": "AQI",
    "pm2_5": "PM2_5",
    "pm10": "PM10",
    "nitrogen_dioxide": "NO2",
    "sulphur_dioxide": "SO2",
    "carbon_monoxide": "CO",
    "ozone": "O3",
    "aerosol_optical_depth": "aod",
    "dust": "dust",
    "uv_index": "uv_index",
}
WEATHER_COLUMN_MAP = {
    "temperature_2m": "Temperature",
    "relative_humidity_2m": "Humidity",
    "precipitation": "Precipitation",
    "wind_speed_10m": "wind_speed",
    "wind_direction_10m": "wind_direction",
    "apparent_temperature": "apparent_temp",
    "surface_pressure": "surface_pressure",
    "wind_gusts_10m": "wind_gusts",
    "boundary_layer_height": "BLH",
    "cloud_cover": "cloud_cover",
    "shortwave_radiation": "shortwave_rad",
}


@dataclass(frozen=True)
class OpenMeteoClient:
    settings: Settings

    @classmethod
    def from_env(cls) -> "OpenMeteoClient":
        return cls(settings=get_settings())

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=self.settings.request_timeout_seconds)
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2**attempt)
        return {}

    def fetch_hourly_range(self, start: date, end: date) -> pd.DataFrame:
        base = {
            "latitude": KARACHI_LATITUDE,
            "longitude": KARACHI_LONGITUDE,
            "timezone": KARACHI_TIMEZONE,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
        air = self._get_json(AIR_ARCHIVE_URL, {**base, "hourly": AIR_HOURLY})["hourly"]
        weather = self._get_json(WEATHER_ARCHIVE_URL, {**base, "hourly": WEATHER_HOURLY})["hourly"]
        df = pd.merge(pd.DataFrame(air), pd.DataFrame(weather), on="time")
        df["time"] = pd.to_datetime(df["time"])
        return df.rename(columns={**AIR_COLUMN_MAP, **WEATHER_COLUMN_MAP})

    def fetch_daily_records(self, start: date, end: date) -> list[dict[str, Any]]:
        hourly = self.fetch_hourly_range(start, end)
        hourly["date"] = hourly["time"].dt.date
        records: list[dict[str, Any]] = []
        for day, group in hourly.groupby("date"):
            row = group.drop(columns=["time", "date"]).mean(numeric_only=True)
            records.append({"date": day.isoformat(), **row.to_dict()})
        return records

    def fetch_daily_forecast(self) -> dict[str, dict[str, float]]:
        base = {
            "latitude": KARACHI_LATITUDE,
            "longitude": KARACHI_LONGITUDE,
            "timezone": KARACHI_TIMEZONE,
            "forecast_days": 5,
        }
        weather = self._get_json(WEATHER_FORECAST_URL, {**base, "hourly": WEATHER_HOURLY})["hourly"]
        air = self._get_json(AIR_ARCHIVE_URL, {**base, "hourly": "pm2_5,aerosol_optical_depth,dust,uv_index"})[
            "hourly"
        ]
        merged = pd.merge(pd.DataFrame(weather), pd.DataFrame(air), on="time")
        merged["time"] = pd.to_datetime(merged["time"])
        merged = merged.rename(columns={**WEATHER_COLUMN_MAP, **AIR_COLUMN_MAP})
        merged["date"] = merged["time"].dt.date
        daily = merged.drop(columns=["time"]).groupby("date").mean(numeric_only=True)
        return {day.isoformat(): values.dropna().to_dict() for day, values in daily.iterrows()}
