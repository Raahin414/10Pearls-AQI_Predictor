# Model Replacement Report

The original project trained Ridge, LightGBM, and LSTM models. The refactored system keeps three integrated models, but replaces the family choices to improve deployment portability and keep the project original.

| New model | Replaces | Reason |
| --- | --- | --- |
| Extra Trees | LightGBM per-horizon trees | Captures non-linear pollutant/weather interactions without requiring LightGBM binaries. It is robust on tabular time-series features and deploys cleanly on Streamlit Community Cloud. |
| Histogram Gradient Boosting | LSTM | The problem is a daily tabular forecasting task with extensive lag and rolling features. Histogram boosting keeps non-linear modeling capacity while avoiding TensorFlow artifact handling and large install size. |
| Elastic Net | Ridge | Preserves a stable linear baseline but adds L1 regularization, which can down-weight weak lag and interaction features. |

## Integration

All three models are declared in `karachi_aqi/models/specs.py`. `ModelTrainer` trains each model on the same feature matrix and target matrix, evaluates the same four horizons, and returns compatible `TrainedModel` objects. `ModelArtifactStore` stores every trained model with its scaler, feature list, metrics, and rationale metadata. `ForecastService` loads all active models requested by `ensemble_config` and blends whichever are available.

## Output Compatibility

The target contract is unchanged:

- `AQI_t+1`
- `AQI_t+2`
- `AQI_t+3`
- `AQI_t+4`

The prediction document still contains an `anchor_date`, `model_type=ensemble`, component model IDs, and a list of forecast dates with `predicted_AQI` values.

## R2 Expectations

The best attainable R2 depends on the live MongoDB data state. The replacement models are chosen to preserve comparable behavior by retaining the strongest predictors from the original system: lagged AQI, rolling AQI statistics, PM2.5, pollutant transforms, seasonal encodings, and forecast weather leads. If a future benchmark shows a material R2 regression, LightGBM can be reintroduced behind the same `ModelSpec` interface without changing the pipeline contract.
