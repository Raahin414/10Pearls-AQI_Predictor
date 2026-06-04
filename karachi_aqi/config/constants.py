"""Application-wide constants."""

from __future__ import annotations

from dataclasses import dataclass


KARACHI_LATITUDE = 24.8607
KARACHI_LONGITUDE = 67.0011
KARACHI_TIMEZONE = "Asia/Karachi"

TARGET_COLUMNS = ["AQI_t+1", "AQI_t+2", "AQI_t+3", "AQI_t+4"]
FORECAST_HORIZON_DAYS = 4

RAW_COLUMNS = [
    "date",
    "AQI",
    "PM2_5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "O3",
    "Temperature",
    "Humidity",
    "Precipitation",
    "wind_speed",
    "wind_direction",
    "apparent_temp",
    "surface_pressure",
    "wind_gusts",
    "BLH",
    "cloud_cover",
    "shortwave_rad",
    "uv_index",
    "aod",
    "dust",
]

POLLUTANT_COLUMNS = ["PM2_5", "PM10", "NO2", "SO2", "CO", "O3"]

WHO_24H_LIMITS = {
    "PM2_5": 15.0,
    "PM10": 45.0,
    "NO2": 25.0,
    "SO2": 40.0,
    "O3": 100.0,
    "CO": 4000.0,
}


@dataclass(frozen=True)
class AqiBand:
    lower: int
    upper: int
    label: str
    color: str


AQI_BANDS = [
    AqiBand(0, 50, "Good", "#009966"),
    AqiBand(51, 100, "Moderate", "#d9a404"),
    AqiBand(101, 150, "Unhealthy for Sensitive Groups", "#e87522"),
    AqiBand(151, 200, "Unhealthy", "#cc3030"),
    AqiBand(201, 300, "Very Unhealthy", "#7d4fa1"),
    AqiBand(301, 500, "Hazardous", "#8c1d40"),
]


def describe_aqi(value: float) -> AqiBand:
    """Return the AQI band for a numeric AQI value."""
    for band in AQI_BANDS:
        if value <= band.upper:
            return band
    return AQI_BANDS[-1]
