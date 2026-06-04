"""Streamlit operations page."""

from __future__ import annotations

import streamlit as st

from karachi_aqi.data.mongo import MongoRepository


st.set_page_config(page_title="AQI Operations", page_icon="Ops", layout="wide")
st.title("Operations")

try:
    repo = MongoRepository.connect()
    with st.spinner("Checking MongoDB..."):
        repo.ping()
    st.success("MongoDB connection is healthy.")

    left, right = st.columns(2)
    with left:
        st.subheader("Recent training logs")
        logs = repo.recent_model_logs(limit=100)
        if logs.empty:
            st.info("No training logs found.")
        else:
            st.dataframe(logs, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Active model registry")
        models = repo.active_models()
        if not models:
            st.info("No active model artifacts found.")
        else:
            st.dataframe(models, use_container_width=True, hide_index=True)
except Exception as exc:
    st.error("Operational data is unavailable.")
    st.caption(str(exc))
