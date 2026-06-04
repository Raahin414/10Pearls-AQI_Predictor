"""Generate and persist the latest AQI forecast."""

from __future__ import annotations

from karachi_aqi.data.mongo import MongoRepository
from karachi_aqi.models.artifacts import ModelArtifactStore
from karachi_aqi.services.forecasting import ForecastService


def main() -> None:
    repo = MongoRepository.connect()
    doc = ForecastService(repo, ModelArtifactStore(repo)).generate()
    print({"anchor_date": doc["anchor_date"], "forecasts": doc["forecasts"]})


if __name__ == "__main__":
    main()
