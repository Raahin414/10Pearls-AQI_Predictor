"""Compatibility wrapper for the update and preprocessing pipeline."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from karachi_aqi.pipelines.run_update import main


if __name__ == "__main__":
    main()
