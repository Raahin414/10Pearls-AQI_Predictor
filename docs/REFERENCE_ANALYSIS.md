# Reference Repository Analysis

Reference main commit inspected: `272f6b1b41d66d1a688f199a09cd57c2ce320181`.

## Original Architecture

The reference implementation is organized as a script-oriented project:

- `config/db.py` creates a MongoDB client, exposes collection constants, and serializes/deserializes model artifacts.
- `src/fetch_data.py` backfills daily Open-Meteo AQI and weather observations.
- `src/update_daily_data.py` incrementally syncs recent days.
- `src/preprocess_daily_data.py` engineers raw, lagged, rolling, seasonal, interaction, weather-lead, and target columns.
- `src/train.py` loads MongoDB features, trains Ridge, LightGBM, and LSTM models, computes NNLS ensemble weights, and writes artifacts to MongoDB.
- `src/predict.py` loads active models and ensemble weights, generates four-day forecasts, and writes a `predictions` document.
- `app.py` is a Streamlit dashboard that reads feature, prediction, model, LIME, and SHAP collections.
- GitHub Actions run feature updates hourly and model training daily.

## Data Flow

Open-Meteo APIs supply hourly air quality and weather data. The pipeline averages hourly rows into one document per calendar day, stores it in MongoDB, then re-reads the whole feature store to build time-series features. Training uses rows with known `AQI_t+1` through `AQI_t+4`; inference uses the latest row with lead features filled by weather and air-quality forecasts.

## Models

The original active training path uses:

- LightGBM regressors, one model per horizon.
- TensorFlow LSTM over seven-day feature windows.
- Multi-output Ridge regression.
- Per-horizon NNLS ensemble weights.

## Workflows And Outputs

User-facing outputs are a Streamlit dashboard, current AQI context, pollutant breakdowns, four-day AQI forecasts, model logs, and explanation summaries. Operational outputs are MongoDB documents in `feature_store`, `model_registry`, `model_logs`, `ensemble_config`, and `predictions`.

## Observed Engineering Issues

- Database access, artifact persistence, and configuration are concentrated in a single module.
- Training orchestration, metric calculation, model selection, ensemble fitting, and persistence are interleaved.
- The large feature engineering file mixes API calls, transformation logic, record sanitization, and MongoDB writes.
- TensorFlow increases deployment weight for Streamlit Cloud.
- `README.md` names older script paths that no longer match the repository.
- Archived experiments and production code are colocated, which makes the deployment surface hard to audit.
