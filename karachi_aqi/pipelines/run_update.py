"""Update recent raw observations and refresh engineered features."""

from __future__ import annotations

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
    raw_count = service.update_recent()
    feature_count = service.preprocess(use_forecast=True)
    print(f"Updated {raw_count} raw rows and {feature_count} engineered rows.")


if __name__ == "__main__":
    main()
