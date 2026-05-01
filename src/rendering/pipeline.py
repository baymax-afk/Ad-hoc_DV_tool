from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.ingestion.models import DataProfile
from src.recommendation.models import ChartSpec
from src.rendering.plotly_renderer import PlotlyRenderer
from src.rendering.transformer import DataTransformer


class VisualizationPipeline:
    def __init__(self) -> None:
        self._transformer = DataTransformer()
        self._renderer = PlotlyRenderer()

    def execute(self, profile: DataProfile, spec: ChartSpec) -> dict:
        df = self._transformer.transform(profile.df, spec)
        fig = self._renderer.render(df, spec)

        return {
            "plotly_json": fig.to_json(),
            "chart_type": spec.chart_type,
            "row_count_rendered": len(df),
            "alternatives": spec.alternatives,
            "title": spec.title,
        }

    def supported_chart_types(self) -> list[str]:
        return self._renderer.supported_types()
