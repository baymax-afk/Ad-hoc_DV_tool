"""Streamlit MVP UI for the Ad-Hoc Data Visualization Tool."""
from __future__ import annotations

import json
import os
import asyncio

import plotly.io as pio
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

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
    import anthropic
    from src.core.config import settings
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
    analyst = None
    if client:
        from src.insights.analyst import DatasetAnalyst
        analyst = DatasetAnalyst(client, settings.llm_model)

    return {
        "ingestor": DataIngestor(),
        "understanding_engine": DataUnderstandingEngine(),
        "intent_detector": IntentDetector(),
        "chart_engine": ChartRecommendationEngine(),
        "viz_pipeline": VisualizationPipeline(),
        "stat_analyzer": StatisticalAnalyzer(),
        "narrator": LLMNarrator(),
        "analyst": analyst,
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
        # Clear cache to reinitialize services with new API key
        st.cache_resource.clear()

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
                
                if svc["analyst"]:
                    analysis = asyncio.run(svc["analyst"].analyze_dataset(understanding, profile))
                else:
                    analysis = "Enable AI analysis by adding ANTHROPIC_API_KEY to .env"
                st.session_state["dataset_analysis"] = analysis

                if "messages" not in st.session_state:
                    st.session_state.messages = []
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"New dataset loaded: {uploaded_file.name} ({profile.row_count:,} rows, {profile.col_count} cols)"
                })
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

# ── dataset analysis (expandable) ──────────────────────────────────────
if "dataset_analysis" in st.session_state:
    with st.expander("Dataset analysis", expanded=True):
        st.markdown(st.session_state["dataset_analysis"])

st.markdown("---")

# ── chat interface ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "system":
        st.info(msg["content"])
    else:
        with st.chat_message(msg["role"]):
            if "content" in msg and msg["content"]:
                st.markdown(msg["content"])
            if "charts" in msg and msg["charts"]:
                # Multi-chart tabs
                if len(msg["charts"]) > 1:
                    tabs = st.tabs([c["title"] for c in msg["charts"]])
                    for chart_idx, (tab, chart_data) in enumerate(zip(tabs, msg["charts"])):
                        with tab:
                            if chart_data.get("subtitle"):
                                st.caption(chart_data["subtitle"])
                            fig = pio.from_json(chart_data["plotly_json"])
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}_{chart_idx}")
                else:
                    chart_data = msg["charts"][0]
                    if chart_data.get("subtitle"):
                        st.caption(chart_data["subtitle"])
                    fig = pio.from_json(chart_data["plotly_json"])
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{i}_0")

            if "insights" in msg and msg["insights"]:
                col_stat, col_narr = st.columns(2)
                with col_stat:
                    st.markdown("#### Statistical Findings")
                    if msg["insights"]["stat"]:
                        for ins in msg["insights"]["stat"]:
                            st.markdown(f"• {ins}")
                    else:
                        st.info("No significant statistical patterns detected.")
                with col_narr:
                    st.markdown("#### AI Insights")
                    st.markdown(msg["insights"]["ai"])

# Chat input
if query := st.chat_input("Ask a question about your data"):
    st.session_state.messages.append({"role": "user", "content": query})
    st.rerun()

# Run agent on last message if it's user
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    query = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Analyzing…"):
            try:
                history = [m for m in st.session_state.messages if m["role"] in ["user", "assistant"]]
                intent = svc["intent_detector"].detect(query, understanding, conversation_history=history)
                specs = svc["chart_engine"].recommend(intent, understanding)
                
                results = svc["viz_pipeline"].run(profile, specs)
                
                if not specs:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Could not determine a suitable chart for this query.",
                    })
                    st.rerun()

                top_spec = specs[0]
                stat_insights = svc["stat_analyzer"].analyze(profile.df, understanding, top_spec)
                
                if svc["analyst"]:
                    ai_insight = asyncio.run(svc["analyst"].analyze_query_result(query, understanding, stat_insights, top_spec))
                else:
                    ai_insight = "Enable AI analysis by adding ANTHROPIC_API_KEY to .env"

                charts_data = []
                fallback_warning = None
                for spec, fig, is_fallback, warning_msg in results:
                    if is_fallback and not fallback_warning:
                        fallback_warning = warning_msg
                    charts_data.append({
                        "title": spec.title or spec.chart_type,
                        "subtitle": spec.subtitle,
                        "plotly_json": fig.to_json()
                    })

                insights_data = {
                    "stat": [f"[{i.severity}] {i.description}" for i in stat_insights],
                    "ai": ai_insight
                }
                
                if fallback_warning:
                    insights_data["stat"].insert(0, f"[WARNING] {fallback_warning}")

                content = f"Based on your query, here is the analysis."
                
                # Update session state messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": content,
                    "charts": charts_data,
                    "insights": insights_data
                })
                
                st.rerun()
            except IntentError as e:
                st.error(f"Could not understand query: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Could not understand query: {e}",
                })
                # Don't rerun, just show the error in the current flow
            except Exception as e:
                st.error(f"Error processing query: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error processing query: {e}",
                })
