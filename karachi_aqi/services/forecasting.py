"""Forecast generation service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from karachi_aqi.data.mongo import ENSEMBLE_CONFIG, PREDICTIONS, MongoRepository
from karachi_aqi.models.artifacts import ModelArtifactStore
from karachi_aqi.models.ensemble import blend_predictions


@dataclass
class ForecastService:
    repo: MongoRepository
    artifacts: ModelArtifactStore

    def generate(self) -> dict[str, Any]:
        frame = self.repo.load_feature_frame(require_aqi=True)
        if frame.empty:
            raise RuntimeError("feature_store is empty.")

        ensemble = self.repo.collection(ENSEMBLE_CONFIG).find_one({})
        if not ensemble:
            raise RuntimeError("No ensemble_config found. Run training first.")

        latest = frame.iloc[-1]
        anchor_date = pd.Timestamp(latest["date"]).date()
        component_predictions: dict[str, np.ndarray] = {}
        component_models: dict[str, str] = {}

        for model_type in ensemble["order"]:
            try:
                model, scaler, metadata = self.artifacts.load_active(model_type)
            except ValueError:
                continue
            row = self._latest_feature_row(frame, metadata["features"], metadata.get("hyperparameters", {}))
            if scaler is not None:
                row_values = scaler.transform(row)
            else:
                row_values = row.values
            component_predictions[model_type] = np.asarray(model.predict(row_values))[0]
            component_models[model_type] = metadata["_id"]

        if not component_predictions:
            raise RuntimeError("No active component models could be loaded.")

        predictions = blend_predictions(component_predictions, ensemble["order"], ensemble["weights"])
        forecasts = [
            {
                "date": (anchor_date + timedelta(days=index + 1)).isoformat(),
                "predicted_AQI": float(max(0, predictions[index])),
            }
            for index in range(len(predictions))
        ]
        doc = {
            "predicted_at": datetime.now(timezone.utc),
            "model_type": "ensemble",
            "anchor_date": anchor_date.isoformat(),
            "component_models": component_models,
            "component_predictions": {name: values.tolist() for name, values in component_predictions.items()},
            "forecasts": forecasts,
        }
        self.repo.collection(PREDICTIONS).insert_one(doc)
        return doc

    def _latest_feature_row(
        self, frame: pd.DataFrame, features: list[str], hyperparameters: dict[str, Any]
    ) -> pd.DataFrame:
        row = frame.iloc[[-1]][features].astype(float).replace([np.inf, -np.inf], np.nan)
        medians = hyperparameters.get("feature_medians", {})
        for column in features:
            if row[column].isna().any():
                fill_value = medians.get(column)
                if fill_value is None or pd.isna(fill_value):
                    fill_value = frame[column].median()
                row[column] = row[column].fillna(fill_value)
        return row
