"""Compatibility wrapper for forecast generation."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from karachi_aqi.pipelines.run_forecast import main


if __name__ == "__main__":
    main()
