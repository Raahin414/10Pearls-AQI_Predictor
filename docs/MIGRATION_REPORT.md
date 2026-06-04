# Migration Report

## Completed

- Created a new package-first implementation under `karachi_aqi/`.
- Replaced hardcoded database construction with typed environment configuration.
- Added `.env.example` with placeholders and no committed secrets.
- Isolated MongoDB access, Open-Meteo access, feature engineering, model training, model storage, forecast generation, and Streamlit UI.
- Replaced the original model families with three integrated deployment-friendly alternatives.
- Preserved four-day AQI target and prediction output format.
- Added GitHub Actions for hourly feature updates and daily training/forecast generation.
- Added Streamlit dashboard and operations page.
- Added unit tests for settings, feature engineering, and model integration.
- Reduced dependencies by removing TensorFlow, LightGBM, Flask, LIME, SHAP, Kaleido, and unused experiment-only packages.

## MongoDB Configuration

Use environment variables:

```text
MONGODB_USERNAME
MONGODB_PASSWORD
MONGODB_CLUSTER
MONGODB_URI
MONGODB_DATABASE
```

`MONGODB_URI` is optional. When it is present, it takes precedence. When `MONGODB_CLUSTER` is a hostname, username and password are URL-encoded into a URI at runtime. When `MONGODB_CLUSTER` is already a full MongoDB URI, it is used as provided from the environment.

Model registry documents store metrics and metadata in `model_registry`, while serialized model and scaler artifacts are stored in GridFS. This avoids MongoDB's 16 MB BSON document limit for larger estimators.

## Operational Commands

```bash
python -m karachi_aqi.pipelines.run_backfill
python -m karachi_aqi.pipelines.run_update
python -m karachi_aqi.pipelines.run_train
python -m karachi_aqi.pipelines.run_forecast
streamlit run app.py
```

## Verification Notes

MongoDB verification requires valid runtime credentials. The repository avoids committing the supplied password; configure it as a local `.env` value, GitHub secret, or Streamlit secret. Live Atlas connectivity, CRUD, training persistence, and forecast persistence were verified on June 3, 2026.
