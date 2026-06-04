# Streamlit Community Cloud Setup

Use this guide after uploading the project to a new GitHub repository.

## 1. Repository

1. Create a new GitHub repository.
2. Upload the project files from this folder.
3. Do not upload `.env`, `.venv`, cache folders, or `secrets.toml`.

## 2. Streamlit App

1. Open Streamlit Community Cloud.
2. Choose **New app**.
3. Select the GitHub repository and branch.
4. Set the main file path to:

```text
app.py
```

5. Deploy with Python 3.11.

## 3. Secrets

In Streamlit app settings, add secrets using the same shape as `.streamlit/secrets.toml.example`:

```toml
MONGODB_USERNAME = "your_username"
MONGODB_PASSWORD = "your_password"
MONGODB_CLUSTER = "aqiproject.5cqik42.mongodb.net"
MONGODB_DATABASE = "karachi_aqi"
```

Alternatively, provide a full URI:

```toml
MONGODB_URI = "mongodb+srv://username:password@cluster.example.mongodb.net/?retryWrites=true&w=majority"
MONGODB_DATABASE = "karachi_aqi"
```

## 4. Atlas Network Access

For Streamlit Community Cloud, Atlas Network Access must allow the Streamlit runtime to connect. The simplest setting is `0.0.0.0/0`; for a stricter setup, use Atlas/Streamlit-supported outbound IP allowlisting if available.

## 5. Validation

After deployment:

1. Open the app.
2. Confirm the dashboard loads.
3. Open the **Operations** page.
4. Confirm it shows `MongoDB connection is healthy.`
5. Run scheduled pipelines from GitHub Actions after repository secrets are configured.

## 6. Local Commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/diagnose_mongodb.py
python -m karachi_aqi.pipelines.run_update
python -m karachi_aqi.pipelines.run_train
python -m karachi_aqi.pipelines.run_forecast
streamlit run app.py
```
