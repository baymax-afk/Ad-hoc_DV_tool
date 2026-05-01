from __future__ import annotations

import json

import anthropic

from src.core.config import settings
from src.insights.models import StatInsight
from src.recommendation.models import ChartSpec
from src.understanding.models import DataUnderstanding

SYSTEM_PROMPT = """\
You are a senior data analyst writing concise business insights.
Given statistical facts about a dataset visualization, write 3-5 clear, actionable insights.

Rules:
- Each insight must cite specific numbers from the facts provided.
- Focus on business implications, not just what the chart shows.
- Maximum 2 sentences per insight.
- Do NOT restate obvious visual patterns.
- Respond ONLY as a JSON array of strings — no markdown, no preamble.

Example response:
["Revenue in Q4 grew 34% YoY, driven by...", "The North region accounts for..."]
"""


class LLMNarrator:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def narrate(
        self,
        stat_insights: list[StatInsight],
        spec: ChartSpec,
        understanding: DataUnderstanding,
    ) -> list[str]:
        if not settings.anthropic_api_key:
            return []

        context = self._build_context(stat_insights, spec, understanding)
        try:
            response = self._client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens_insights,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception:
            return []

    def _build_context(
        self,
        insights: list[StatInsight],
        spec: ChartSpec,
        u: DataUnderstanding,
    ) -> str:
        facts = "\n".join(f"- {i.description}" for i in insights) or "No statistical anomalies found."
        measure_summary = ", ".join(
            f"{m.name} (mean={m.mean:.2f}, std={m.std:.2f}, skew={m.skewness:.2f})"
            for m in u.measures[:5]
            if m.mean is not None
        )
        return (
            f"Chart: {spec.chart_type} — {spec.title}\n"
            f"X-axis: {spec.x_col} | Y-axis: {spec.y_col} | Aggregation: {spec.aggregation}\n\n"
            f"Statistical findings:\n{facts}\n\n"
            f"Measure summaries: {measure_summary or 'n/a'}\n"
            f"Dataset rows: {u.profile.row_count:,} | Columns: {u.profile.col_count}"
        )
