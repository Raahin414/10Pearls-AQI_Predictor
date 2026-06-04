"""Raw data ingestion and preprocessing service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from karachi_aqi.data.mongo import MongoRepository
from karachi_aqi.data.open_meteo import OpenMeteoClient
from karachi_aqi.features.engineering import FeatureEngineer


@dataclass
class IngestionService:
    repo: MongoRepository
    api: OpenMeteoClient
    engineer: FeatureEngineer

    def backfill(self, start: date, end: date) -> int:
        records = self.api.fetch_daily_records(start, end)
        return self.repo.upsert_feature_records(records)

    def update_recent(self, resync_days: int = 3) -> int:
        today = datetime.now(timezone.utc).date()
        frame = self.repo.load_feature_frame()
        if frame.empty:
            start = today - timedelta(days=365)
        else:
            latest = frame["date"].max().date()
            start = min(latest + timedelta(days=1), today - timedelta(days=resync_days))
        end = today - timedelta(days=1)
        if start > end:
            return 0
        records = self.api.fetch_daily_records(start, end)
        return self.repo.upsert_feature_records(records)

    def preprocess(self, use_forecast: bool = True) -> int:
        raw = self.repo.load_feature_frame()
        forecast = self.api.fetch_daily_forecast() if use_forecast else None
        engineered = self.engineer.transform(raw, forecast_by_date=forecast)
        records = self.engineer.to_records(engineered)
        return self.repo.upsert_feature_records(records)
