"""Train replacement models and refresh ensemble weights."""

from __future__ import annotations

from karachi_aqi.data.mongo import MongoRepository
from karachi_aqi.models.artifacts import ModelArtifactStore
from karachi_aqi.models.training import ModelTrainer
from karachi_aqi.services.training import TrainingService


def main() -> None:
    repo = MongoRepository.connect()
    repo.ensure_indexes()
    result = TrainingService(repo, ModelTrainer(), ModelArtifactStore(repo)).train()
    print(result)


if __name__ == "__main__":
    main()
