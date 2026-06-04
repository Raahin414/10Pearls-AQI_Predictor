"""Replacement model catalogue."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNet
from sklearn.multioutput import MultiOutputRegressor


@dataclass(frozen=True)
class ModelSpec:
    name: str
    description: str
    replacement_for: str
    rationale: str
    scale_features: bool

    def build(self):
        if self.name == "extra_trees":
            return ExtraTreesRegressor(
                n_estimators=420,
                min_samples_leaf=2,
                max_features=0.85,
                bootstrap=False,
                random_state=42,
                n_jobs=-1,
            )
        if self.name == "hist_gradient_boosting":
            base = HistGradientBoostingRegressor(
                learning_rate=0.045,
                max_iter=420,
                max_leaf_nodes=31,
                l2_regularization=0.08,
                random_state=42,
            )
            return MultiOutputRegressor(base)
        if self.name == "elastic_net":
            base = ElasticNet(alpha=0.02, l1_ratio=0.25, max_iter=8000, random_state=42)
            return MultiOutputRegressor(base)
        raise ValueError(f"Unknown model spec: {self.name}")


MODEL_SPECS = [
    ModelSpec(
        name="extra_trees",
        description="Multi-output Extra Trees regressor",
        replacement_for="LightGBM per-horizon trees",
        rationale=(
            "Extra Trees captures non-linear pollutant and weather interactions while avoiding "
            "a native LightGBM dependency, which makes Streamlit Cloud deployment simpler."
        ),
        scale_features=False,
    ),
    ModelSpec(
        name="hist_gradient_boosting",
        description="Histogram Gradient Boosting wrapped for multi-output AQI targets",
        replacement_for="LSTM sequence model",
        rationale=(
            "The original LSTM was heavy for a daily tabular series. Histogram boosting is "
            "fast, handles non-linearities well, and performs reliably on medium-sized daily data."
        ),
        scale_features=False,
    ),
    ModelSpec(
        name="elastic_net",
        description="Regularized linear baseline with multi-output wrapper",
        replacement_for="Ridge baseline",
        rationale=(
            "Elastic Net retains the interpretability and stability of Ridge while adding sparse "
            "feature selection that is useful with many lag and interaction features."
        ),
        scale_features=True,
    ),
]
