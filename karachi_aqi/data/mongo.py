"""MongoDB repository layer for feature, model, and prediction documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import certifi
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection

from karachi_aqi.config.settings import Settings, get_settings


FEATURE_STORE = "feature_store"
MODEL_REGISTRY = "model_registry"
MODEL_LOGS = "model_logs"
PREDICTIONS = "predictions"
ENSEMBLE_CONFIG = "ensemble_config"
EXPLANATIONS = "explanations"


@dataclass
class MongoRepository:
    settings: Settings
    client: MongoClient

    @classmethod
    def connect(cls, settings: Settings | None = None) -> "MongoRepository":
        settings = settings or get_settings()
        client = MongoClient(
            settings.resolved_mongodb_uri,
            serverSelectionTimeoutMS=8000,
            tlsCAFile=certifi.where(),
        )
        return cls(settings=settings, client=client)

    @property
    def db(self):
        return self.client[self.settings.mongodb_database]

    def collection(self, name: str) -> Collection:
        return self.db[name]

    def ensure_indexes(self) -> None:
        self.collection(FEATURE_STORE).create_index([("date", ASCENDING)], unique=True)
        self.collection(MODEL_REGISTRY).create_index(
            [("model_type", ASCENDING), ("status", ASCENDING), ("trained_at", DESCENDING)]
        )
        self.collection(PREDICTIONS).create_index([("predicted_at", DESCENDING)])
        self.collection(MODEL_LOGS).create_index([("timestamp", DESCENDING)])

    def ping(self) -> bool:
        self.client.admin.command("ping")
        return True

    def load_feature_frame(self, require_aqi: bool = False):
        import pandas as pd

        query: dict[str, Any] = {}
        if require_aqi:
            query = {"AQI": {"$exists": True, "$ne": None}}
        docs = list(self.collection(FEATURE_STORE).find(query, {"_id": 0}))
        if not docs:
            return pd.DataFrame()
        df = pd.DataFrame(docs)
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)

    def upsert_feature_records(self, records: list[dict[str, Any]]) -> int:
        count = 0
        col = self.collection(FEATURE_STORE)
        for record in records:
            col.update_one({"date": record["date"]}, {"$set": record}, upsert=True)
            count += 1
        return count

    def latest_prediction(self) -> dict[str, Any] | None:
        return self.collection(PREDICTIONS).find_one({}, sort=[("predicted_at", DESCENDING)])

    def active_models(self) -> list[dict[str, Any]]:
        models = list(
            self.collection(MODEL_REGISTRY)
            .find({"status": "active"}, {"model_binary": 0, "scaler_binary": 0})
            .sort("trained_at", DESCENDING)
        )
        for model in models:
            if "_id" in model:
                model["_id"] = str(model["_id"])
            if "model_file_id" in model:
                model["model_file_id"] = str(model["model_file_id"])
            if "scaler_file_id" in model:
                model["scaler_file_id"] = str(model["scaler_file_id"])
        return models

    def recent_model_logs(self, limit: int = 100):
        import pandas as pd

        docs = list(
            self.collection(MODEL_LOGS)
            .find({}, {"_id": 0})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return pd.DataFrame(docs)

    def write_log(self, model_type: str, status: str, metrics: dict[str, Any]) -> None:
        self.collection(MODEL_LOGS).insert_one(
            {
                "timestamp": datetime.now(timezone.utc),
                "model_type": model_type,
                "status": status,
                **metrics,
            }
        )
