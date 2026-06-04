from __future__ import annotations

from karachi_aqi.config.settings import Settings


def test_settings_builds_uri_from_hostname() -> None:
    settings = Settings(
        mongodb_username="user",
        mongodb_password="pass word",
        mongodb_cluster="cluster.example.mongodb.net",
        mongodb_uri=None,
    )

    assert settings.resolved_mongodb_uri.startswith("mongodb+srv://user:pass+word@cluster.example.mongodb.net/")


def test_settings_accepts_full_cluster_uri() -> None:
    uri = "mongodb+srv://user:pass@cluster.example.mongodb.net/"
    settings = Settings(
        mongodb_username=None,
        mongodb_password=None,
        mongodb_cluster=uri,
        mongodb_uri=None,
    )

    assert settings.resolved_mongodb_uri == uri
