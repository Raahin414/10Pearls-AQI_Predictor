"""Training orchestration with MongoDB persistence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

from karachi_aqi.config.constants import TARGET_COLUMNS
from karachi_aqi.config.settings import get_settings
from karachi_aqi.data.mongo import ENSEMBLE_CONFIG, MongoRepository
from karachi_aqi.models.artifacts import ModelArtifactStore
from karachi_aqi.models.ensemble import fit_nonnegative_weights
from karachi_aqi.models.training import ModelTrainer, compute_metrics


@dataclass
class TrainingService:
    repo: MongoRepository
    trainer: ModelTrainer
    artifacts: ModelArtifactStore

    def train(self, holdout_days: int = 60) -> dict[str, object]:
        frame = self.repo.load_feature_frame(require_aqi=True)
        if frame.empty:
            raise RuntimeError("feature_store is empty. Run ingestion and preprocessing first.")

        trained = self.trainer.train_holdout(frame, holdout_days=holdout_days)
        labeled = self.trainer.labeled_frame(frame)
        _, holdout = self.trainer.time_split(labeled, holdout_days=holdout_days)
        y_holdout = holdout[TARGET_COLUMNS].astype(float).values

        holdout_predictions = {item.model_type: item.holdout_predictions for item in trained}
        ensemble = fit_nonnegative_weights(holdout_predictions, y_holdout)
        ensemble_prediction = np.zeros_like(y_holdout, dtype=float)
        for horizon in range(y_holdout.shape[1]):
            weights = np.array(ensemble["weights"][horizon])
            names = ensemble["order"]
            ensemble_prediction[:, horizon] = sum(
                weights[i] * holdout_predictions[name][:, horizon] for i, name in enumerate(names)
            )
        ensemble_metrics = compute_metrics(y_holdout, ensemble_prediction)

        self.repo.collection(ENSEMBLE_CONFIG).replace_one(
            {},
            {
                "order": ensemble["order"],
                "weights": ensemble["weights"],
                "metrics": ensemble_metrics,
                "updated_at": datetime.now(timezone.utc),
            },
            upsert=True,
        )
        self.repo.write_log("ensemble", "success", ensemble_metrics)

        managed_model_types = {item.model_type for item in trained}
        retired_count = self.artifacts.retire_unmanaged(managed_model_types)
        if retired_count:
            self.repo.write_log(
                "model_registry",
                "success",
                {"retired_unmanaged_models": retired_count, "managed_model_types": sorted(managed_model_types)},
            )

        saved: list[dict[str, object]] = []
        for item in trained:
            model, scaler = self.trainer.retrain_full(frame, item)
            model_id = self.artifacts.save(
                model_type=item.model_type,
                model=model,
                scaler=scaler,
                features=item.features,
                metrics=item.metrics,
                hyperparameters=item.hyperparameters,
                automated=os.getenv("AUTOMATED_RUN") == "true",
            )
            self.repo.write_log(item.model_type, "success", {"model_id": model_id, **item.metrics})
            self.artifacts.purge_inactive(item.model_type, keep_days=get_settings().model_retention_days)
            saved.append({"model_type": item.model_type, "model_id": model_id, "metrics": item.metrics})

        return {"models": saved, "ensemble": {"order": ensemble["order"], "metrics": ensemble_metrics}}
