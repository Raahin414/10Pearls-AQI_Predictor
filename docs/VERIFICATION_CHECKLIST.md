# Verification Checklist

- [x] Reference repository main branch inspected.
- [x] Attached project brief inspected.
- [x] Original architecture and workflows documented.
- [x] Refactored project structure created.
- [x] Streamlit app created with a separate operations page.
- [x] MongoDB credentials removed from source and replaced with environment variables.
- [x] `.env.example` added without committed secrets.
- [x] Three replacement models integrated.
- [x] Model registry, ensemble config, training logs, and forecast writes implemented.
- [x] Dependency list cleaned.
- [x] Unit tests added.
- [x] Project-local dependency install completed from `requirements.txt`.
- [x] `ruff check . --exclude .venv` passed.
- [x] `python -m compileall karachi_aqi scripts tests app.py pages` passed.
- [x] `pytest` passed: 4 tests.
- [x] Streamlit server launched locally and returned HTTP 200 for health, root, and Operations routes.
- [x] Streamlit page execution checked with `streamlit.testing.v1.AppTest`.
- [x] GitHub Actions CI workflow added for push and pull request validation.
- [x] MongoDB diagnostic suite added.
- [x] Minimal PyMongo ping reproduction added.
- [x] Compass-equivalent Node driver check added.
- [x] MongoDB connection code updated to use `certifi` explicitly.
- [x] PyMongo upgraded to 4.17.0.
- [x] MongoDB live connectivity verified with production credentials.
  Final diagnostic result on June 3, 2026: DNS, SRV, TXT, TCP, TLS, PyMongo ping/auth, database listing, collection listing, CRUD, and GridFS all passed. Summary: 14 passed, 0 failed.
- [x] Full live pipeline run completed against MongoDB.
  `run_update` refreshed 3 raw rows and 1,235 engineered rows. `run_train` saved three active models and ensemble metrics. `run_forecast` generated and persisted four AQI forecasts for June 3-6, 2026.
- [x] Large model artifacts moved to GridFS.
  Live training exposed MongoDB's 16 MB BSON document limit for model pickles; `ModelArtifactStore` now stores pickles in GridFS and registry metadata in `model_registry`.
- [x] Legacy active model rows retired during training.
  Active registry now contains only `extra_trees`, `hist_gradient_boosting`, and `elastic_net`.
- [x] Streamlit app manually verified against live MongoDB data.
  Dashboard, Trends, Pollutants, Models, and Operations were opened in the browser against live Atlas data. The final clean Streamlit server returned HTTP 200 for `/_stcore/health`.
