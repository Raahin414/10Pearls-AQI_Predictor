"""Typed runtime settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongodb_username: str | None
    mongodb_password: str | None
    mongodb_cluster: str | None
    mongodb_uri: str | None
    mongodb_database: str = "karachi_aqi"
    request_timeout_seconds: int = 30
    backfill_start_date: str = "2023-01-01"
    model_retention_days: int = 7

    @property
    def resolved_mongodb_uri(self) -> str:
        """Build a MongoDB URI without baking credentials into source code."""
        if self.mongodb_uri:
            return self.mongodb_uri

        if not self.mongodb_cluster:
            raise RuntimeError("MONGODB_CLUSTER or MONGODB_URI must be set.")

        if self.mongodb_cluster.startswith(("mongodb://", "mongodb+srv://")):
            return self.mongodb_cluster

        if not self.mongodb_username or not self.mongodb_password:
            raise RuntimeError(
                "MONGODB_USERNAME and MONGODB_PASSWORD are required when "
                "MONGODB_CLUSTER is a hostname."
            )

        user = quote_plus(self.mongodb_username)
        password = quote_plus(self.mongodb_password)
        return f"mongodb+srv://{user}:{password}@{self.mongodb_cluster}/?appName=KarachiAQI"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide settings."""
    return Settings(
        mongodb_username=os.getenv("MONGODB_USERNAME"),
        mongodb_password=os.getenv("MONGODB_PASSWORD"),
        mongodb_cluster=os.getenv("MONGODB_CLUSTER"),
        mongodb_uri=os.getenv("MONGODB_URI"),
        mongodb_database=os.getenv("MONGODB_DATABASE", "karachi_aqi"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        backfill_start_date=os.getenv("BACKFILL_START_DATE", "2023-01-01"),
        model_retention_days=int(os.getenv("MODEL_RETENTION_DAYS", "7")),
    )
