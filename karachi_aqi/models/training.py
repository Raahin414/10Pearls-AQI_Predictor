"""Model training primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from karachi_aqi.config.constants import TARGET_COLUMNS
from karachi_aqi.models.specs import MODEL_SPECS, ModelSpec


EXCLUDED_FEATURES = {
    "date",
    "processed_at",
    "_id",
    *TARGET_COLUMNS,
}


@dataclass
class TrainedModel:
    model_type: str
    model: Any
    scaler: StandardScaler | None
    features: list[str]
    metrics: dict[str, float]
    hyperparameters: dict[str, Any]
    holdout_predictions: np.ndarray


class ModelTrainer:
    """Train all configured replacement models on a time-aware split."""

    def __init__(self, specs: list[ModelSpec] | None = None) -> None:
        self.specs = specs or list(MODEL_SPECS)

    def feature_columns(self, df: pd.DataFrame) -> list[str]:
        numeric = df.select_dtypes(include=["number", "bool"]).columns
        return [column for column in numeric if column not in EXCLUDED_FEATURES]

    def labeled_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.dropna(subset=TARGET_COLUMNS).sort_values("date").reset_index(drop=True)

    def time_split(self, df: pd.DataFrame, holdout_days: int = 60) -> tuple[pd.DataFrame, pd.DataFrame]:
        if "date" not in df.columns:
            raise ValueError("Training data must include a date column.")
        split_date = pd.to_datetime(df["date"]).max() - pd.Timedelta(days=holdout_days)
        train = df[pd.to_datetime(df["date"]) <= split_date]
        test = df[pd.to_datetime(df["date"]) > split_date]
        if train.empty or test.empty:
            raise ValueError("Time split produced an empty train or holdout partition.")
        return train, test

    def train_holdout(self, df: pd.DataFrame, holdout_days: int = 60) -> list[TrainedModel]:
        labeled = self.labeled_frame(df)
        train, test = self.time_split(labeled, holdout_days=holdout_days)
        features = self.feature_columns(labeled)

        X_train = train[features].astype(float).replace([np.inf, -np.inf], np.nan)
        X_test = test[features].astype(float).replace([np.inf, -np.inf], np.nan)
        medians = X_train.median()
        X_train = X_train.fillna(medians)
        X_test = X_test.fillna(medians)
        y_train = train[TARGET_COLUMNS].astype(float).values
        y_test = test[TARGET_COLUMNS].astype(float).values

        trained: list[TrainedModel] = []
        for spec in self.specs:
            trained.append(self._fit_spec(spec, X_train, y_train, X_test, y_test, features, medians))
        return trained

    def retrain_full(self, df: pd.DataFrame, template: TrainedModel) -> tuple[Any, StandardScaler | None]:
        labeled = self.labeled_frame(df)
        X = labeled[template.features].astype(float).replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median())
        y = labeled[TARGET_COLUMNS].astype(float).values

        spec = next(item for item in self.specs if item.name == template.model_type)
        model = spec.build()
        scaler: StandardScaler | None = None
        if spec.scale_features:
            scaler = StandardScaler()
            X_values = scaler.fit_transform(X)
        else:
            X_values = X.values
        model.fit(X_values, y)
        return model, scaler

    def _fit_spec(
        self,
        spec: ModelSpec,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        features: list[str],
        medians: pd.Series,
    ) -> TrainedModel:
        model = spec.build()
        scaler: StandardScaler | None = None
        if spec.scale_features:
            scaler = StandardScaler()
            X_train_values = scaler.fit_transform(X_train)
            X_test_values = scaler.transform(X_test)
        else:
            X_train_values = X_train.values
            X_test_values = X_test.values

        model.fit(X_train_values, y_train)
        predictions = np.asarray(model.predict(X_test_values))
        metrics = compute_metrics(y_test, predictions)
        hyperparameters = {
            "description": spec.description,
            "replacement_for": spec.replacement_for,
            "rationale": spec.rationale,
            "feature_medians": medians.to_dict(),
        }
        return TrainedModel(
            model_type=spec.name,
            model=model,
            scaler=scaler,
            features=features,
            metrics=metrics,
            hyperparameters=hyperparameters,
            holdout_predictions=predictions,
        )


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    metrics: dict[str, float] = {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
    }
    for index in range(y_true.shape[1]):
        day = index + 1
        metrics[f"MAE_d{day}"] = float(mean_absolute_error(y_true[:, index], y_pred[:, index]))
        metrics[f"RMSE_d{day}"] = float(np.sqrt(mean_squared_error(y_true[:, index], y_pred[:, index])))
        metrics[f"R2_d{day}"] = float(r2_score(y_true[:, index], y_pred[:, index]))
    return metrics
