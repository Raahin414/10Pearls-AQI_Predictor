"""Minimal PyMongo ping reproduction.

Use this when you need the smallest possible MongoDB connection test with a
full stack trace on failure.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import certifi
from pymongo import MongoClient

from scripts.diagnose_mongodb import redact_uri, standardize_uri


def main() -> int:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("MONGODB_URI is required for the minimal ping test.")
        return 2

    uri = standardize_uri(uri)
    print(f"URI: {redact_uri(uri)}")
    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            tlsCAFile=certifi.where(),
        )
        print(client.admin.command("ping"))
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
