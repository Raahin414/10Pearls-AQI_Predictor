"""MongoDB model artifact serialization."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from gridfs import GridFS
from pymongo import DESCENDING

from karachi_aqi.data.mongo import MODEL_REGISTRY, MongoRepository


@dataclass
class ModelArtifactStore:
    repo: MongoRepository

    @property
    def fs(self) -> GridFS:
        return GridFS(self.repo.db)

    def save(
        self,
        *,
        model_type: str,
        model: Any,
        scaler: Any,
        features: list[str],
        metrics: dict[str, float],
        hyperparameters: dict[str, Any],
        automated: bool = False,
    ) -> str:
        now = datetime.now(timezone.utc)
        collection = self.repo.collection(MODEL_REGISTRY)
        model_bytes = pickle.dumps(model)
        scaler_bytes = pickle.dumps(scaler)
        model_file_id = self.fs.put(
            model_bytes,
            filename=f"{model_type}-{now:%Y%m%d_%H%M%S}-model.pkl",
            model_type=model_type,
            artifact_kind="model",
            created_at=now,
        )
        scaler_file_id = self.fs.put(
            scaler_bytes,
            filename=f"{model_type}-{now:%Y%m%d_%H%M%S}-scaler.pkl",
            model_type=model_type,
            artifact_kind="scaler",
            created_at=now,
        )
        collection.update_many({"model_type": model_type, "status": "active"}, {"$set": {"status": "inactive"}})
        try:
            result = collection.insert_one(
                {
                    "model_type": model_type,
                    "version": now.strftime("%Y%m%d_%H%M%S"),
                    "trained_at": now,
                    "status": "active",
                    "model_file_id": model_file_id,
                    "scaler_file_id": scaler_file_id,
                    "artifact_storage": "gridfs",
                    "features": features,
                    "metrics": metrics,
                    "hyperparameters": hyperparameters,
                    "automated": automated,
                    **metrics,
                }
            )
        except Exception:
            self._delete_file(model_file_id)
            self._delete_file(scaler_file_id)
            raise
        return str(result.inserted_id)

    def load_active(self, model_type: str) -> tuple[Any, Any, dict[str, Any]]:
        doc = self.repo.collection(MODEL_REGISTRY).find_one(
            {"model_type": model_type, "status": "active"},
            sort=[("trained_at", DESCENDING)],
        )
        if not doc:
            raise ValueError(f"No active model found for {model_type}.")
        model = self._load_pickle(doc, "model")
        scaler = self._load_pickle(doc, "scaler")
        metadata = {
            key: value
            for key, value in doc.items()
            if key not in {"model_binary", "scaler_binary", "model_file_id", "scaler_file_id"}
        }
        metadata["_id"] = str(doc["_id"])
        return model, scaler, metadata

    def purge_inactive(self, model_type: str, keep_days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        stale_docs = list(
            self.repo.collection(MODEL_REGISTRY).find(
                {
                    "model_type": model_type,
                    "status": "inactive",
                    "automated": True,
                    "trained_at": {"$lt": cutoff},
                },
                {"model_file_id": 1, "scaler_file_id": 1},
            )
        )
        result = self.repo.collection(MODEL_REGISTRY).delete_many(
            {
                "model_type": model_type,
                "status": "inactive",
                "automated": True,
                "trained_at": {"$lt": cutoff},
            }
        )
        for doc in stale_docs:
            self._delete_file(doc.get("model_file_id"))
            self._delete_file(doc.get("scaler_file_id"))
        return result.deleted_count

    def retire_unmanaged(self, managed_model_types: set[str]) -> int:
        now = datetime.now(timezone.utc)
        result = self.repo.collection(MODEL_REGISTRY).update_many(
            {"status": "active", "model_type": {"$nin": sorted(managed_model_types)}},
            {
                "$set": {
                    "status": "inactive",
                    "retired_at": now,
                    "retired_reason": "superseded_by_refactored_model_catalog",
                }
            },
        )
        return result.modified_count

    def _load_pickle(self, doc: dict[str, Any], kind: str) -> Any:
        file_id = doc.get(f"{kind}_file_id")
        if file_id is not None:
            return pickle.loads(self.fs.get(file_id).read())
        legacy_key = f"{kind}_binary"
        if legacy_key not in doc:
            raise ValueError(f"Active {doc.get('model_type', 'model')} artifact is missing {kind} data.")
        return pickle.loads(bytes(doc[legacy_key]))

    def _delete_file(self, file_id: Any) -> None:
        if file_id is None:
            return
        try:
            self.fs.delete(file_id)
        except Exception:
            pass
