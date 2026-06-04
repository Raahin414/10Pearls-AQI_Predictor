# Deployment

The full deployment guide lives in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

For Streamlit Community Cloud, use [STREAMLIT_SETUP.md](STREAMLIT_SETUP.md).

Minimum deployment steps:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python scripts/diagnose_mongodb.py
streamlit run app.py
```

Never commit real `.env` or `.streamlit/secrets.toml` files.
