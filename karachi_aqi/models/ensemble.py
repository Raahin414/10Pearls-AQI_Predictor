"""Per-horizon non-negative ensemble weighting."""

from __future__ import annotations

import numpy as np
from scipy.optimize import nnls


def fit_nonnegative_weights(predictions: dict[str, np.ndarray], y_true: np.ndarray) -> dict[str, list[float]]:
    """Fit one normalized NNLS weight vector per target horizon."""
    model_order = list(predictions)
    if not model_order:
        raise ValueError("No model predictions were supplied.")

    weights_by_horizon: dict[str, list[float]] = {"order": model_order, "weights": []}  # type: ignore[assignment]
    for horizon in range(y_true.shape[1]):
        design = np.column_stack([predictions[name][:, horizon] for name in model_order])
        weights, _ = nnls(design, y_true[:, horizon])
        if weights.sum() == 0:
            weights = np.ones(len(model_order)) / len(model_order)
        else:
            weights = weights / weights.sum()
        weights_by_horizon["weights"].append(weights.tolist())  # type: ignore[index]
    return weights_by_horizon


def blend_predictions(
    predictions: dict[str, np.ndarray],
    order: list[str],
    weights: list[list[float]],
) -> np.ndarray:
    """Blend component predictions with per-horizon weights."""
    if not predictions:
        raise ValueError("No component predictions are available.")

    horizon_count = len(next(iter(predictions.values())))
    output = np.zeros(horizon_count)
    available = [name for name in order if name in predictions]
    for horizon in range(horizon_count):
        horizon_weights = np.array([weights[horizon][order.index(name)] for name in available], dtype=float)
        horizon_weights = horizon_weights / horizon_weights.sum() if horizon_weights.sum() else horizon_weights
        output[horizon] = sum(horizon_weights[i] * predictions[name][horizon] for i, name in enumerate(available))
    return output
