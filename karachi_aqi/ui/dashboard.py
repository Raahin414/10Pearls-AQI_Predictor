"""Streamlit dashboard rendering."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from karachi_aqi.config.constants import AQI_BANDS, POLLUTANT_COLUMNS, WHO_24H_LIMITS, describe_aqi
from karachi_aqi.data.mongo import MongoRepository


def _rgba(hex_color: str, alpha: float) -> str:
    color = hex_color.lstrip("#")
    red, green, blue = (int(color[index : index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def get_repo() -> MongoRepository:
    return MongoRepository.connect()


@st.cache_data(ttl=900, show_spinner=False)
def load_dashboard_data() -> tuple[pd.DataFrame, dict | None, list[dict]]:
    repo = get_repo()
    return repo.load_feature_frame(require_aqi=True), repo.latest_prediction(), repo.active_models()


def render_dashboard() -> None:
    st.set_page_config(page_title="Karachi AQI Forecast", page_icon="AQI", layout="wide")
    st.title("Karachi AQI Forecast")
    st.caption("Observed air quality, pollutant drivers, and four-day ensemble forecasts.")

    try:
        with st.spinner("Loading AQI data from MongoDB..."):
            frame, prediction, models = load_dashboard_data()
    except Exception as exc:
        st.error("The dashboard could not connect to MongoDB.")
        st.caption(str(exc))
        return

    if frame.empty:
        st.warning("No AQI records are available yet.")
        return

    latest = frame.iloc[-1]
    current_aqi = float(latest["AQI"])
    current_band = describe_aqi(current_aqi)

    if current_aqi >= 151:
        st.error(f"Current AQI is {current_aqi:.0f}: {current_band.label}.")
    elif current_aqi >= 101:
        st.warning(f"Current AQI is {current_aqi:.0f}: {current_band.label}.")

    top_left, top_right = st.columns([1, 1.5], gap="large")
    with top_left:
        st.plotly_chart(_aqi_gauge(current_aqi), use_container_width=True)
    with top_right:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Latest date", pd.Timestamp(latest["date"]).date().isoformat())
        metric_cols[1].metric("Active models", len(models))
        metric_cols[2].metric("Records", f"{len(frame):,}")

        if prediction:
            st.subheader("Forecast")
            cards = st.columns(len(prediction.get("forecasts", [])) or 1)
            for column, forecast in zip(cards, prediction.get("forecasts", [])):
                value = float(forecast["predicted_AQI"])
                band = describe_aqi(value)
                column.metric(forecast["date"], f"{value:.0f}", band.label)
        else:
            st.info("No forecast has been generated yet.")

    tab_trends, tab_pollutants, tab_models = st.tabs(["Trends", "Pollutants", "Models"])
    with tab_trends:
        _render_trends(frame)
    with tab_pollutants:
        _render_pollutants(latest)
    with tab_models:
        _render_models(models)


def _aqi_gauge(value: float) -> go.Figure:
    band = describe_aqi(value)
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"font": {"color": band.color, "size": 52}},
            gauge={
                "axis": {"range": [0, 300], "tickvals": [0, 50, 100, 150, 200, 300]},
                "bar": {"color": band.color},
                "steps": [
                    {"range": [item.lower, min(item.upper, 300)], "color": _rgba(item.color, 0.14)}
                    for item in AQI_BANDS
                    if item.lower <= 300
                ],
            },
        )
    )
    figure.update_layout(height=330, margin=dict(l=20, r=20, t=20, b=20))
    return figure


def _render_trends(frame: pd.DataFrame) -> None:
    days = st.slider("History window", 30, min(730, len(frame)), min(180, len(frame)), step=30)
    plot_frame = frame.tail(days)
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=plot_frame["date"], y=plot_frame["AQI"], mode="lines", name="AQI"))
    for band in AQI_BANDS:
        if band.lower > 300:
            continue
        figure.add_hrect(
            y0=band.lower,
            y1=min(band.upper, 300),
            fillcolor=band.color,
            opacity=0.08,
            line_width=0,
        )
    figure.update_layout(height=420, yaxis_title="US AQI", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(figure, use_container_width=True)


def _render_pollutants(latest: pd.Series) -> None:
    available = [column for column in POLLUTANT_COLUMNS if column in latest.index and pd.notna(latest[column])]
    if not available:
        st.info("No pollutant readings are available for the latest row.")
        return
    values = [float(latest[column]) for column in available]
    limits = [WHO_24H_LIMITS.get(column, max(values)) for column in available]
    figure = go.Figure()
    figure.add_trace(go.Bar(x=available, y=values, name="Latest"))
    figure.add_trace(go.Scatter(x=available, y=limits, name="WHO 24h guideline", mode="markers+lines"))
    figure.update_layout(height=390, yaxis_title="Concentration", margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(figure, use_container_width=True)


def _render_models(models: list[dict]) -> None:
    if not models:
        st.info("No active models are registered.")
        return
    rows = []
    for model in models:
        rows.append(
            {
                "model_type": model.get("model_type"),
                "trained_at": model.get("trained_at"),
                "MAE": model.get("MAE"),
                "RMSE": model.get("RMSE"),
                "R2": model.get("R2"),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
