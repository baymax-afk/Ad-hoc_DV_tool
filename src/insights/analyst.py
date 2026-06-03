from __future__ import annotations

import anthropic

from src.ingestion.models import DataProfile
from src.recommendation.models import ChartSpec
from src.understanding.models import DataUnderstanding
from src.insights.models import StatInsight


class DatasetAnalyst:
    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self.client = client
        self.model = model

    async def analyze_dataset(self, understanding: DataUnderstanding, profile: DataProfile) -> str:
        prompt = f"""
You are an expert data analyst. Please provide a brief dataset analysis in markdown format. 
Maximum length: 400 tokens.

DATASET CONTEXT:
- Total rows: {profile.row_count}
- Total columns: {profile.col_count}
- Has time series: {understanding.has_time_series}

COLUMN PROFILES:
{understanding.schema_str()}

Based on this, cover the following:
1. Data quality assessment (nulls, outliers, cardinality).
2. Key patterns and relationships.
3. Recommended analysis angles.
4. Potential business questions this dataset can answer.
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            import logging
            logging.warning(f"Failed to analyze dataset with LLM: {e}")
            return "Analysis failed due to API error."

    async def analyze_query_result(self, query: str, understanding: DataUnderstanding, stat_insights: list[StatInsight], chart_spec: ChartSpec) -> str:
        insights_str = "\n".join([f"- {i.description} (Severity: {i.severity})" for i in stat_insights])
        prompt = f"""
You are an expert data analyst. Please provide 3-5 specific, non-generic business insights grounded in the numbers. 
Maximum length: 300 tokens.

USER QUERY: {query}
CHART GENERATED: {chart_spec.chart_type} (x: {chart_spec.x_col}, y: {chart_spec.y_col})
STATISTICAL FINDINGS:
{insights_str}

Please generate actionable business insights based on the findings and the query.
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            import logging
            logging.warning(f"Failed to analyze query result with LLM: {e}")
            return "Query analysis failed due to API error."
