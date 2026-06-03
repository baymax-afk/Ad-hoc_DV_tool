from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp

from src.ingestion.models import DataProfile
from src.recommendation.models import ChartSpec, MultiChartSpec
from src.rendering.plotly_renderer import PlotlyRenderer
from src.rendering.transformer import DataTransformer


class VisualizationPipeline:
    def __init__(self) -> None:
        self._transformer = DataTransformer()
        self._renderer = PlotlyRenderer()

    def run(self, profile: DataProfile, specs: list[ChartSpec]) -> list[tuple[ChartSpec, go.Figure]]:
        results = []
        for spec in specs:
            try:
                # We need to pass understanding if we had it, but for pipeline run it's optional.
                df = self._transformer.transform(profile.df, spec)
                if df.empty:
                    continue
                fig = self._renderer.render(df, spec)
                results.append((spec, fig))
            except Exception as e:
                import logging
                logging.warning(f"Failed to render chart {spec.chart_type}: {e}")
                continue
        return results
        
    def execute(self, profile: DataProfile, spec: ChartSpec) -> dict:
        # Legacy execute for backwards compatibility where possible
        df = self._transformer.transform(profile.df, spec)
        fig = self._renderer.render(df, spec)
        return {
            "plotly_json": fig.to_json(),
            "chart_type": spec.chart_type,
            "row_count_rendered": len(df),
            "alternatives": spec.alternatives,
            "title": spec.title,
        }

    def execute_multi(self, profile: DataProfile, spec: MultiChartSpec) -> dict:
        """Execute multi-chart visualization with subplots."""
        try:
            n_specs = len(spec.specs)
            if n_specs == 0:
                # Fallback: return empty spec result
                return self.execute(profile, spec.specs[0]) if spec.specs else {
                    "plotly_json": "{}",
                    "chart_type": "error",
                    "row_count_rendered": 0,
                    "title": "No charts to render",
                }
            
            if spec.layout_type == "grid":
                rows = (n_specs + spec.grid_cols - 1) // spec.grid_cols
                cols = min(n_specs, spec.grid_cols)
            elif spec.layout_type == "row":
                rows, cols = 1, n_specs
            elif spec.layout_type == "column":
                rows, cols = n_specs, 1
            else:  # faceted
                rows = (n_specs + 2) // 2
                cols = 2
            
            # Create subplot grid (simple specs without secondary_y)
            fig = sp.make_subplots(
                rows=rows,
                cols=cols,
                subplot_titles=[s.title for s in spec.specs],
            )
            
            # Render and add each chart
            row_count_total = 0
            for idx, chart_spec in enumerate(spec.specs, 1):
                row_idx = (idx - 1) // cols + 1
                col_idx = (idx - 1) % cols + 1
                
                try:
                    df_transformed = self._transformer.transform(profile.df, chart_spec)
                    if df_transformed.empty:
                        continue
                    individual_fig = self._renderer.render(df_transformed, chart_spec)
                    
                    # Add traces from individual figure
                    for trace in individual_fig.data:
                        fig.add_trace(trace, row=row_idx, col=col_idx)
                    
                    row_count_total += len(df_transformed)
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to render chart {idx}: {str(e)}")
                    continue
            
            # Update layout
            fig.update_layout(
                title={
                    "text": f"<b>{spec.title}</b>",
                    "x": 0.05,
                    "font": {"size": 18},
                },
                height=max(300 * rows, 600),
                showlegend=spec.combine_legend,
                template="plotly_white",
                font={"family": "Inter, system-ui, sans-serif", "size": 13},
            )
            
            return {
                "plotly_json": fig.to_json(),
                "chart_type": "multi",
                "row_count_rendered": row_count_total,
                "title": spec.title,
                "layout_type": spec.layout_type,
            }
        except Exception as e:
            import logging
            logging.warning(f"Multi-chart render failed: {str(e)}. Falling back to single chart.")
            # Fallback to first single chart
            if spec.specs:
                return self.execute(profile, spec.specs[0])
            raise

    def supported_chart_types(self) -> list[str]:
        return self._renderer.supported_types()
