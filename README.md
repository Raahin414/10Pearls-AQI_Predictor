# Karachi AQI Forecast

An original Streamlit-first AQI forecasting system for Karachi. The project preserves the workflow of the reference implementation while restructuring the code into maintainable package layers.

## What It Does

- Fetches daily Karachi AQI, pollutant, and weather observations from Open-Meteo.
- Stores raw and engineered feature rows in MongoDB Atlas.
- Builds lag, rolling, seasonal, pollutant, weather, and forecast-lead features.
- Trains three replacement model families: Extra Trees, Histogram Gradient Boosting, and Elastic Net.
- Computes per-horizon ensemble weights for four-day AQI forecasts.
- Saves model artifacts, training logs, ensemble config, and forecasts in MongoDB.
- Serves a Streamlit dashboard with live AQI, trends, pollutant context, forecasts, and operations status.

## Project Structure

```text
karachi_aqi/
  config/          typed settings and AQI constants
  data/            MongoDB repository and Open-Meteo client
  features/        reusable feature engineering pipeline
  models/          model specs, training, artifacts, ensemble logic
  services/        ingestion, training, and forecasting orchestration
  pipelines/       python -m runnable pipeline entry points
  ui/              Streamlit dashboard components
pages/             Streamlit multipage operations view
scripts/           small compatibility wrappers
tests/             regression tests for settings, features, models
docs/              migration, architecture, deployment, and model reports
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Set MongoDB credentials in `.env` or Streamlit secrets. Do not commit real passwords.

```bash
MONGODB_USERNAME=...
MONGODB_PASSWORD=...
MONGODB_CLUSTER=aqiproject.5cqik42.mongodb.net
MONGODB_DATABASE=karachi_aqi
```

If you prefer one secret, set `MONGODB_URI` instead.

## Verify MongoDB

```bash
python scripts/diagnose_mongodb.py
python scripts/minimal_mongodb_ping.py
```

The diagnostic suite checks DNS/SRV/TXT lookup, TCP, TLS, authentication, database listing, collection listing, CRUD, and GridFS write/read/delete.

## Local Pipeline

```bash
python -m karachi_aqi.pipelines.run_backfill
python -m karachi_aqi.pipelines.run_update
python -m karachi_aqi.pipelines.run_train
python -m karachi_aqi.pipelines.run_forecast
streamlit run app.py
```

## Verification

```bash
pytest
ruff check .
python -m compileall karachi_aqi scripts tests app.py pages
python scripts/check_mongodb.py
```

`scripts/check_mongodb.py` requires valid MongoDB environment variables.

## Streamlit Community Cloud

Use [STREAMLIT_SETUP.md](STREAMLIT_SETUP.md) for the full deployment checklist. The Streamlit entrypoint is:

```text
app.py
```

Configure secrets in Streamlit Community Cloud using `.streamlit/secrets.toml.example`. Do not commit real `.env` or `.streamlit/secrets.toml` files.

## GitHub Actions

The repository includes:

- `.github/workflows/ci.yml`: lint, tests, build validation, and Streamlit startup smoke validation on push and pull request.
- `.github/workflows/feature_pipeline.yml`: scheduled feature refresh.
- `.github/workflows/training_pipeline.yml`: scheduled training and forecast generation.

Add MongoDB credentials as GitHub repository secrets before enabling scheduled workflows.
