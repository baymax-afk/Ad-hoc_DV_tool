"""Streamlit MVP UI for the Ad-Hoc Data Visualization Tool."""
from __future__ import annotations

import json
import os

import plotly.io as pio
import streamlit as st

from src.core.exceptions import DVToolError, IntentError
from src.ingestion.ingestor import DataIngestor
from src.insights.narrator import LLMNarrator
from src.insights.statistical import StatisticalAnalyzer
from src.intent.detector import IntentDetector
from src.recommendation.engine import ChartRecommendationEngine
from src.rendering.pipeline import VisualizationPipeline
from src.understanding.analyzer import DataUnderstandingEngine

# ── page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ad-Hoc Data Viz",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── singleton services ───────────────────────────────────────────────
@st.cache_resource
def get_services():
    return {
        "ingestor": DataIngestor(),
        "understanding_engine": DataUnderstandingEngine(),
        "intent_detector": IntentDetector(),
        "chart_engine": ChartRecommendationEngine(),
        "viz_pipeline": VisualizationPipeline(),
        "stat_analyzer": StatisticalAnalyzer(),
        "narrator": LLMNarrator(),
    }


svc = get_services()

# ── sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📊 Data Viz Tool")
    st.markdown("---")

    api_key = st.text_input(
        "Anthropic API Key",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Required for LLM-powered intent detection and narrative insights.",
    )
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key
        from src.core import config
        config.settings.anthropic_api_key = api_key

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if "understanding" in st.session_state:
        u = st.session_state["understanding"]
        st.markdown("### Dataset Info")
        st.metric("Rows", f"{u.profile.row_count:,}")
        st.metric("Columns", u.profile.col_count)
        st.metric("Measures", len(u.measures))
        st.metric("Dimensions", len(u.dimensions))
        if u.has_time_series:
            st.success("Time series detected")
        if u.profile.parse_warnings:
            for w in u.profile.parse_warnings:
                st.warning(w)

# ── file ingestion ────────────────────────────────────────────────────
if uploaded_file is not None:
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.get("file_key") != file_key:
        with st.spinner("Analyzing dataset…"):
            try:
                raw = uploaded_file.read()
                profile = svc["ingestor"].ingest(raw, uploaded_file.name)
                understanding = svc["understanding_engine"].analyze(profile)
                st.session_state["profile"] = profile
                st.session_state["understanding"] = understanding
                st.session_state["file_key"] = file_key
                st.session_state["query_history"] = []
            except DVToolError as e:
                st.error(f"Ingestion failed: {e}")
                st.stop()

# ── main area ─────────────────────────────────────────────────────────
if "understanding" not in st.session_state:
    st.markdown(
        """
        ## Welcome to the Ad-Hoc Data Visualization Tool

        **How it works:**
        1. Upload a CSV file using the sidebar
        2. Type a natural language question about your data
        3. Get an interactive chart + AI-powered insights instantly

        **Example queries:**
        - *"Show me monthly revenue trend by region"*
        - *"What are the top 10 products by sales?"*
        - *"Distribution of customer ages"*
        - *"Compare profit across departments"*
        - *"Correlation between price and quantity"*
        """
    )
    st.stop()

profile = st.session_state["profile"]
understanding = st.session_state["understanding"]

# ── schema explorer (expandable) ──────────────────────────────────────
with st.expander("Dataset Schema", expanded=False):
    import pandas as pd
    schema_data = [
        {
            "Column": c.name,
            "Role": c.role.value,
            "Nulls": f"{c.null_pct:.1%}",
            "Cardinality": c.cardinality,
            "Sample": str(c.sample_values[:3]),
        }
        for c in understanding.columns
    ]
    st.dataframe(pd.DataFrame(schema_data), use_container_width=True, hide_index=True)

st.markdown("---")

# ── query input ───────────────────────────────────────────────────────
col_q, col_btn = st.columns([5, 1])
with col_q:
    query = st.text_input(
        "Ask a question about your data",
        placeholder="e.g. Show top 10 categories by revenue",
        label_visibility="collapsed",
    )
with col_btn:
    run = st.button("Visualize", type="primary", use_container_width=True)

# ── advanced options ──────────────────────────────────────────────────
with st.expander("Advanced options", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        chart_override = st.selectbox(
            "Force chart type",
            ["(auto)"] + svc["viz_pipeline"].supported_chart_types(),
        )
    with col2:
        top_n_override = st.number_input("Limit rows (top N)", min_value=0, value=0, step=5)
    with col3:
        agg_override = st.selectbox("Aggregation", ["(auto)", "sum", "avg", "count", "max", "min"])

# ── query execution ───────────────────────────────────────────────────
if run and query.strip():
    with st.spinner("Detecting intent…"):
        try:
            intent = svc["intent_detector"].detect(query, understanding)
        except IntentError as e:
            st.error(f"Could not understand query: {e}")
            st.stop()

    spec = svc["chart_engine"].recommend(intent, understanding)

    if chart_override != "(auto)":
        spec.chart_type = chart_override
    if top_n_override > 0:
        spec.top_n = int(top_n_override)
    if agg_override != "(auto)":
        spec.aggregation = agg_override

    with st.spinner("Rendering chart…"):
        render_result = svc["viz_pipeline"].execute(profile, spec)

    # Chart
    st.markdown(f"### {spec.title}")
    if spec.subtitle:
        st.caption(spec.subtitle)

    fig = pio.from_json(render_result["plotly_json"])
    st.plotly_chart(fig, use_container_width=True)

    # Alternatives
    if spec.alternatives:
        alt_cols = st.columns(min(len(spec.alternatives), 4))
        for i, alt in enumerate(spec.alternatives[:4]):
            with alt_cols[i]:
                if st.button(f"Try: {alt.replace('_', ' ').title()}", key=f"alt_{alt}_{i}"):
                    spec.chart_type = alt
                    render_result = svc["viz_pipeline"].execute(profile, spec)
                    fig = pio.from_json(render_result["plotly_json"])
                    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Insights
    stat_insights = svc["stat_analyzer"].analyze(profile.df, understanding, spec)

    col_stat, col_narr = st.columns(2)

    with col_stat:
        st.markdown("#### Statistical Findings")
        if stat_insights:
            severity_icon = {"warning": "⚠️", "notable": "💡", "info": "ℹ️"}
            for ins in stat_insights:
                icon = severity_icon.get(ins.severity, "•")
                st.markdown(f"{icon} {ins.description}")
        else:
            st.info("No significant statistical patterns detected.")

    with col_narr:
        st.markdown("#### AI Insights")
        if not api_key:
            st.info("Add your Anthropic API key in the sidebar to enable AI narrative insights.")
        else:
            with st.spinner("Generating insights…"):
                narrative = svc["narrator"].narrate(stat_insights, spec, understanding)
            if narrative:
                for i, point in enumerate(narrative, 1):
                    st.markdown(f"**{i}.** {point}")
            else:
                st.info("No narrative insights generated.")

    # Query metadata
    with st.expander("Query details", expanded=False):
        st.json({
            "intent": intent.intent.value,
            "confidence": round(intent.confidence, 2),
            "tier": intent.tier,
            "chart_type": spec.chart_type,
            "x_col": spec.x_col,
            "y_col": spec.y_col,
            "color_col": spec.color_col,
            "aggregation": spec.aggregation,
            "filters": spec.filters,
            "top_n": spec.top_n,
        })

    # History
    if "query_history" not in st.session_state:
        st.session_state["query_history"] = []
    st.session_state["query_history"].append(query)

# ── query history ─────────────────────────────────────────────────────
if st.session_state.get("query_history"):
    with st.sidebar:
        st.markdown("### Recent Queries")
        for q in reversed(st.session_state["query_history"][-5:]):
            st.markdown(f"- {q}")
