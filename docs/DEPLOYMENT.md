# Deployment Instructions

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app from `app.py`.
3. Set Python version to 3.11 if prompted.
4. Add secrets using `.streamlit/secrets.toml.example` as the template:

```toml
MONGODB_USERNAME = "..."
MONGODB_PASSWORD = "..."
MONGODB_CLUSTER = "aqiproject.5cqik42.mongodb.net"
MONGODB_DATABASE = "karachi_aqi"
```

Alternatively set `MONGODB_URI` as a single secret.

5. Confirm MongoDB Atlas Network Access allows Streamlit Cloud outbound traffic.
6. Deploy the app.
7. Open the **Operations** page and confirm `MongoDB connection is healthy.`

## Self-Hosted Streamlit

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py --server.port 8501
```

Before running Streamlit locally, configure MongoDB values in `.env`.

## GitHub Actions

Add the following repository secrets:

- `MONGODB_USERNAME`
- `MONGODB_PASSWORD`
- `MONGODB_CLUSTER`
- optionally `MONGODB_URI`

Workflows:

- `.github/workflows/ci.yml`: validates lint, tests, build/import checks, and Streamlit startup on push and pull request.
- `.github/workflows/feature_pipeline.yml`: hourly data update and feature refresh.
- `.github/workflows/training_pipeline.yml`: daily model training and forecast generation.

## First Run

Run one historical backfill before enabling scheduled training:

```bash
python -m karachi_aqi.pipelines.run_backfill
python -m karachi_aqi.pipelines.run_update
python -m karachi_aqi.pipelines.run_train
python -m karachi_aqi.pipelines.run_forecast
```

## Final Local Validation

```bash
python scripts/diagnose_mongodb.py
pytest
ruff check .
python -m compileall karachi_aqi scripts tests app.py pages
streamlit run app.py
```
