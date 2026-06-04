"""Daily AQI feature engineering for training and inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from karachi_aqi.config.constants import RAW_COLUMNS, TARGET_COLUMNS


WEATHER_LEAD_COLUMNS = ["Temperature", "Humidity", "Precipitation", "wind_speed", "surface_pressure"]
AIR_LEAD_COLUMNS = ["PM2_5", "aod", "dust", "uv_index"]
LEAD_COLUMNS = [f"{column}_t{day}" for column in WEATHER_LEAD_COLUMNS + AIR_LEAD_COLUMNS for day in range(1, 5)]
IQR_COLUMNS = ["PM10", "SO2", "NO2", "O3", "Temperature", "Humidity", "Precipitation", "wind_speed", "aod", "dust"]


@dataclass(frozen=True)
class FeatureEngineer:
    raw_columns: list[str] = field(default_factory=lambda: list(RAW_COLUMNS))

    def transform(
        self,
        raw: pd.DataFrame,
        forecast_by_date: dict[str, dict[str, float]] | None = None,
        keep_unlabeled_tail: bool = True,
    ) -> pd.DataFrame:
        """Return a calendar-complete feature frame from raw daily observations."""
        if raw.empty:
            raise ValueError("Cannot engineer features from an empty data frame.")

        df = self._prepare_calendar(raw)
        df = self._cap_outliers(df)
        df = self._add_pollutant_transforms(df)
        df = self._add_wind_components(df)
        df = self._add_calendar_features(df)
        df = self._add_lags_and_windows(df)
        df = self._add_weather_features(df)
        df = self._add_interactions(df)
        df = self._add_leads(df)
        df = self._add_targets(df)
        if forecast_by_date:
            df = self._fill_leads_from_forecast(df, forecast_by_date)

        skipped = set(LEAD_COLUMNS + TARGET_COLUMNS + ["date", "processed_at"])
        core_columns = [column for column in df.columns if column not in skipped]
        df = df.dropna(subset=core_columns).reset_index(drop=True)

        if not keep_unlabeled_tail:
            df = df.dropna(subset=TARGET_COLUMNS).reset_index(drop=True)

        return df

    def to_records(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for record in frame.to_dict("records"):
            date_value = pd.Timestamp(record["date"]).date().isoformat()
            cleaned = {"date": date_value}
            for key, value in record.items():
                if key == "date":
                    continue
                if pd.isna(value):
                    cleaned[key] = None
                elif isinstance(value, (np.integer, np.floating)):
                    cleaned[key] = value.item()
                elif isinstance(value, pd.Timestamp):
                    cleaned[key] = value.to_pydatetime()
                else:
                    cleaned[key] = value
            records.append(cleaned)
        return records

    def _prepare_calendar(self, raw: pd.DataFrame) -> pd.DataFrame:
        df = raw.copy()
        if "date" not in df.columns:
            raise ValueError("Raw feature data must include a date column.")

        df["date"] = pd.to_datetime(df["date"])
        present = [column for column in self.raw_columns if column in df.columns]
        df = df[present].sort_values("date").drop_duplicates(subset=["date"], keep="last")

        for column in self.raw_columns:
            if column not in df.columns and column != "date":
                df[column] = np.nan

        full_index = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
        df = df.set_index("date").reindex(full_index).ffill().reset_index().rename(columns={"index": "date"})
        return df[self.raw_columns]

    def _cap_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        for column in IQR_COLUMNS:
            if column not in df.columns:
                continue
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            if pd.isna(iqr) or iqr == 0:
                continue
            df[column] = df[column].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        return df

    def _add_pollutant_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        df["log_PM2_5"] = np.log1p(df["PM2_5"])
        df["log_CO"] = np.log1p(df["CO"])
        df["log_PM10"] = np.log1p(df["PM10"])
        return df

    def _add_wind_components(self, df: pd.DataFrame) -> pd.DataFrame:
        radians = np.deg2rad(df["wind_direction"].fillna(0))
        df["wind_dir_sin"] = np.sin(radians)
        df["wind_dir_cos"] = np.cos(radians)
        return df

    def _add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        date_series = pd.to_datetime(df["date"])
        df["month"] = date_series.dt.month
        df["day_of_year"] = date_series.dt.dayofyear
        df["weekday"] = date_series.dt.weekday
        df["is_weekend"] = df["weekday"].isin([5, 6]).astype(float)
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
        df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365.25)
        df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
        df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)
        df["season_Winter"] = df["month"].isin([12, 1, 2]).astype(float)
        df["season_Spring"] = df["month"].isin([3, 4, 5]).astype(float)
        df["season_Summer"] = df["month"].isin([6, 7, 8]).astype(float)
        return df

    def _add_lags_and_windows(self, df: pd.DataFrame) -> pd.DataFrame:
        shifted_aqi = df["AQI"].shift(1)
        for lag in [1, 2, 3, 7, 14]:
            df[f"AQI_lag_{lag}"] = df["AQI"].shift(lag)
        for window in [3, 7, 14]:
            rolling = shifted_aqi.rolling(window)
            df[f"AQI_roll_mean_{window}"] = rolling.mean()
            df[f"AQI_roll_std_{window}"] = rolling.std()
            df[f"AQI_roll_min_{window}"] = rolling.min()
            df[f"AQI_roll_max_{window}"] = rolling.max()
        df["AQI_ewm_7"] = shifted_aqi.ewm(span=7, adjust=False).mean()
        df["AQI_ewm_14"] = shifted_aqi.ewm(span=14, adjust=False).mean()
        df["AQI_diff_1"] = shifted_aqi.diff()
        df["AQI_diff_2"] = shifted_aqi.diff().diff()

        for column in ["PM2_5", "PM10", "NO2", "CO", "Temperature", "Humidity", "wind_speed"]:
            for lag in [1, 3, 7]:
                df[f"{column}_lag_{lag}"] = df[column].shift(lag)
            df[f"{column}_roll_mean_7"] = df[column].shift(1).rolling(7).mean()
        return df

    def _add_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        temperature = df["Temperature"]
        humidity = df["Humidity"].clip(lower=1, upper=100)
        df["dew_point"] = temperature - ((100 - humidity) / 5)
        df["heat_index_proxy"] = temperature + 0.05 * humidity
        df["stagnant_air"] = ((df["wind_speed"] < 2.0) & (df["Precipitation"] <= 0.1)).astype(float)
        df["dry_windy"] = ((humidity < 45) & (df["wind_speed"] > 12)).astype(float)
        df["AQI_high_flag"] = (df["AQI"] > 150).astype(float)

        for column in ["BLH", "cloud_cover", "shortwave_rad", "uv_index", "aod", "dust"]:
            df[f"{column}_lag_1"] = df[column].shift(1)
            df[f"{column}_roll_mean_7"] = df[column].shift(1).rolling(7).mean()
        df["log_aod"] = np.log1p(df["aod"].clip(lower=0))
        return df

    def _add_interactions(self, df: pd.DataFrame) -> pd.DataFrame:
        df["PM2_5_x_Humidity"] = df["PM2_5"] * df["Humidity"]
        df["PM2_5_x_stagnant"] = df["PM2_5"] * df["stagnant_air"]
        df["CO_x_Temperature"] = df["CO"] * df["Temperature"]
        df["AQI_x_wind"] = df["AQI"] * df["wind_speed"]
        df["AQI_x_month_sin"] = df["AQI"] * df["month_sin"]
        df["dust_x_wind"] = df["dust"] * df["wind_speed"]
        return df

    def _add_leads(self, df: pd.DataFrame) -> pd.DataFrame:
        lead_data = {
            f"{column}_t{day}": df[column].shift(-day)
            for column in WEATHER_LEAD_COLUMNS + AIR_LEAD_COLUMNS
            for day in range(1, 5)
        }
        return pd.concat([df, pd.DataFrame(lead_data, index=df.index)], axis=1)

    def _add_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        target_data = {f"AQI_t+{day}": df["AQI"].shift(-day) for day in range(1, 5)}
        return pd.concat([df, pd.DataFrame(target_data, index=df.index)], axis=1)

    def _fill_leads_from_forecast(
        self, df: pd.DataFrame, forecast_by_date: dict[str, dict[str, float]]
    ) -> pd.DataFrame:
        last_date = pd.Timestamp(df["date"].max()).date()
        last_index = df.index[-1]
        for horizon in range(1, 5):
            forecast_date = (last_date + timedelta(days=horizon)).isoformat()
            forecast = forecast_by_date.get(forecast_date, {})
            for column in WEATHER_LEAD_COLUMNS + AIR_LEAD_COLUMNS:
                value = forecast.get(column)
                target_column = f"{column}_t{horizon}"
                if value is not None and target_column in df.columns:
                    df.loc[last_index, target_column] = value
        return df
