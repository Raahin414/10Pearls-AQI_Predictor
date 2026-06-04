"""Compatibility wrapper for model training."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from karachi_aqi.pipelines.run_train import main


if __name__ == "__main__":
    main()
