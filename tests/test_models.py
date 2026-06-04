from __future__ import annotations

from karachi_aqi.features import FeatureEngineer
from karachi_aqi.models.training import ModelTrainer
from tests.test_feature_engineering import make_raw


def test_trainer_builds_three_replacement_models() -> None:
    features = FeatureEngineer().transform(make_raw(160), keep_unlabeled_tail=False)
    trained = ModelTrainer().train_holdout(features, holdout_days=30)

    assert {model.model_type for model in trained} == {"extra_trees", "hist_gradient_boosting", "elastic_net"}
    for model in trained:
        assert model.features
        assert "R2" in model.metrics
        assert model.holdout_predictions.shape[1] == 4
