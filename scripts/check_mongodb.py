"""Check MongoDB connectivity and required indexes."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from karachi_aqi.data.mongo import MongoRepository


def main() -> None:
    repo = MongoRepository.connect()
    repo.ping()
    repo.ensure_indexes()
    print("MongoDB connection healthy; indexes ensured.")


if __name__ == "__main__":
    main()
