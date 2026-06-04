# Architecture Comparison

## Reference Shape

```text
app.py
config/db.py
src/
  fetch_data.py
  update_daily_data.py
  preprocess_daily_data.py
  train.py
  predict.py
  models/
archive/
scripts/
tests/
```

The reference project is effective but script-centric. Most workflows are top-level scripts that import shared constants and call MongoDB directly.

## Refactored Shape

```text
karachi_aqi/
  config/
  data/
  features/
  models/
  services/
  pipelines/
  ui/
app.py
pages/
scripts/
tests/
docs/
```

The refactor uses explicit layers:

- `config`: environment and stable constants.
- `data`: persistence and external API clients.
- `features`: deterministic feature construction.
- `models`: model catalogue, metrics, artifacts, and ensemble math.
- `services`: application workflows.
- `pipelines`: command-line entry points for automation.
- `ui`: Streamlit rendering.

## Key Changes

- MongoDB credentials are loaded from environment variables only.
- MongoDB logic is isolated in `MongoRepository`.
- Open-Meteo request handling is isolated in `OpenMeteoClient`.
- Feature engineering is testable without MongoDB or network access.
- Model choices are declared in `MODEL_SPECS`.
- Training service performs holdout evaluation, ensemble fitting, full retraining, artifact saves, and model-log writes.
- Forecasting service loads the same artifacts and ensemble configuration used by training.
- Streamlit pages are separated from pipeline code.

## Preserved Behavior

- Daily Karachi AQI forecasting.
- MongoDB feature store and model registry.
- Automated feature update and training workflows.
- Four-day forecast output documents.
- AQI dashboard with trends, pollutant readings, model status, and warnings.
- At least three integrated models plus an ensemble.
