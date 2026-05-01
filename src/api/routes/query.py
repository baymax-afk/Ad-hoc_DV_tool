from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from typing import Optional

from src.core.exceptions import DVToolError, SessionNotFoundError
from src.core.session_store import session_store
from src.ingestion.ingestor import DataIngestor
from src.insights.models import InsightBundle
from src.insights.narrator import LLMNarrator
from src.insights.statistical import StatisticalAnalyzer
from src.intent.detector import IntentDetector
from src.recommendation.engine import ChartRecommendationEngine
from src.recommendation.models import ChartSpec
from src.rendering.pipeline import VisualizationPipeline
from src.understanding.analyzer import DataUnderstandingEngine

router = APIRouter(tags=["query"])

_ingestor = DataIngestor()
_understanding_engine = DataUnderstandingEngine()
_intent_detector = IntentDetector()
_chart_engine = ChartRecommendationEngine()
_viz_pipeline = VisualizationPipeline()
_stat_analyzer = StatisticalAnalyzer()
_narrator = LLMNarrator()


# ── Upload ────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/upload")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    raw = await file.read()
    try:
        profile = _ingestor.ingest(raw, file.filename)
    except DVToolError as e:
        raise HTTPException(status_code=422, detail=str(e))

    understanding = _understanding_engine.analyze(profile)

    session_store.set(session_id, "profile", profile)
    session_store.set(session_id, "understanding", understanding)

    return {
        "filename": file.filename,
        "row_count": profile.row_count,
        "col_count": profile.col_count,
        "parse_warnings": profile.parse_warnings,
        "columns": [
            {"name": c.name, "role": c.role.value, "cardinality": c.cardinality}
            for c in understanding.columns
        ],
    }


# ── Query ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    chart_type_override: Optional[str] = None
    filters: dict = Field(default_factory=dict)
    top_n: Optional[int] = None


@router.post("/sessions/{session_id}/query")
def run_query(session_id: str, body: QueryRequest):
    try:
        data = session_store.get(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    profile = data.get("profile")
    understanding = data.get("understanding")
    if not profile or not understanding:
        raise HTTPException(status_code=400, detail="Upload a CSV file first.")

    try:
        intent = _intent_detector.detect(body.query, understanding)
    except DVToolError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if body.filters:
        intent.filters.update(body.filters)
    if body.top_n:
        intent.top_n = body.top_n

    spec: ChartSpec = _chart_engine.recommend(intent, understanding)
    if body.chart_type_override:
        spec.chart_type = body.chart_type_override

    render_result = _viz_pipeline.execute(profile, spec)

    stat_insights = _stat_analyzer.analyze(profile.df, understanding, spec)
    narrative = _narrator.narrate(stat_insights, spec, understanding)

    return {
        "intent": {
            "intent": intent.intent.value,
            "confidence": intent.confidence,
            "target_columns": intent.target_columns,
            "tier": intent.tier,
        },
        "chart_spec": {
            "chart_type": spec.chart_type,
            "x_col": spec.x_col,
            "y_col": spec.y_col,
            "color_col": spec.color_col,
            "aggregation": spec.aggregation,
            "title": spec.title,
            "alternatives": spec.alternatives,
        },
        "visualization": render_result,
        "insights": {
            "statistical": [
                {"type": s.type, "description": s.description, "severity": s.severity}
                for s in stat_insights
            ],
            "narrative": narrative,
        },
    }


# ── Refine ────────────────────────────────────────────────────────────

class RefineRequest(BaseModel):
    chart_type: Optional[str] = None
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    color_col: Optional[str] = None
    aggregation: Optional[str] = None
    filters: dict = Field(default_factory=dict)
    top_n: Optional[int] = None


@router.post("/sessions/{session_id}/refine")
def refine_chart(session_id: str, body: RefineRequest):
    try:
        data = session_store.get(session_id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    profile = data.get("profile")
    if not profile:
        raise HTTPException(status_code=400, detail="Upload a CSV file first.")

    spec = ChartSpec(
        chart_type=body.chart_type or "bar",
        x_col=body.x_col,
        y_col=body.y_col,
        color_col=body.color_col,
        aggregation=body.aggregation or "sum",
        filters=body.filters,
        top_n=body.top_n,
        title=f"{body.y_col or 'Value'} by {body.x_col or 'Category'}",
    )
    render_result = _viz_pipeline.execute(profile, spec)
    return {"visualization": render_result, "chart_spec": spec.__dict__}


# ── Export ────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/export")
def export_chart(session_id: str, fmt: str = "png"):
    raise HTTPException(
        status_code=501,
        detail="Export endpoint: render chart client-side or POST the plotly_json to /export.",
    )
