"""Backfill raw daily observations."""

from __future__ import annotations

from datetime import date, timedelta

from karachi_aqi.config.settings import get_settings
from karachi_aqi.data.mongo import MongoRepository
from karachi_aqi.data.open_meteo import OpenMeteoClient
from karachi_aqi.features import FeatureEngineer
from karachi_aqi.services.ingestion import IngestionService


def main() -> None:
    settings = get_settings()
    repo = MongoRepository.connect(settings)
    repo.ensure_indexes()
    service = IngestionService(repo, OpenMeteoClient(settings), FeatureEngineer())
    start = date.fromisoformat(settings.backfill_start_date)
    end = date.today() - timedelta(days=1)
    count = service.backfill(start, end)
    print(f"Backfilled {count} raw daily records.")


if __name__ == "__main__":
    main()
