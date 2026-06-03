from __future__ import annotations

from typing import Optional

from src.intent.models import IntentResult, QueryIntent
from src.recommendation.models import ChartSpec, MultiChartSpec
from src.understanding.models import ColumnProfile, ColumnRole, DataUnderstanding

HIGH_CARDINALITY = 12


class ChartRecommendationEngine:
    def recommend(
        self, intent: IntentResult, understanding: DataUnderstanding
    ) -> list[ChartSpec]:
        candidates = self._decision_tree(intent, understanding)
        
        specs = []
        for chart_type in candidates:
            x, y, color, lat, lon = self._assign_columns(chart_type, intent, understanding)
            title, subtitle = self._build_titles(chart_type, intent, x, y)
            
            spec = ChartSpec(
                chart_type=chart_type,
                x_col=x,
                y_col=y,
                color_col=color,
                lat_col=lat,
                lon_col=lon,
                aggregation=intent.aggregation or "sum",
                sort_order=intent.sort_order,
                top_n=intent.top_n,
                filters=intent.filters,
                title=title,
                subtitle=subtitle,
                alternatives=[],
                x_label=x.replace("_", " ").title() if x else None,
                y_label=y.replace("_", " ").title() if y else None,
            )
            specs.append(spec)

        return specs

    def recommend_multi(
        self, intent: IntentResult, understanding: DataUnderstanding
    ) -> MultiChartSpec:
        """Generate multi-chart recommendation for compound intents."""
        
        if intent.intent == QueryIntent.FACETED:
            # Small-multiple faceted visualization
            specs = self._recommend_faceted(intent, understanding)
            return MultiChartSpec(
                specs=specs,
                layout_type="grid",
                title="Faceted Analysis",
                grid_cols=2,
            )
        
        elif intent.intent == QueryIntent.MULTI_DIMENSION:
            # Multiple dimensions analyzed side-by-side
            specs = self._recommend_multi_dimension(intent, understanding)
            return MultiChartSpec(
                specs=specs,
                layout_type="row",
                title="Multi-Dimensional Comparison",
                grid_cols=len(specs),
            )
        
        elif intent.intent == QueryIntent.COMBINED:
            # Combined visualizations (e.g., trend + distribution)
            specs = self._recommend_combined(intent, understanding)
            return MultiChartSpec(
                specs=specs,
                layout_type="grid",
                title="Combined Analysis",
                grid_cols=2,
            )
        
        # Fallback to single chart
        return MultiChartSpec(specs=self.recommend(intent, understanding)[:1])

    def _recommend_faceted(
        self, intent: IntentResult, understanding: DataUnderstanding
    ) -> list[ChartSpec]:
        """Create faceted charts by primary dimension."""
        specs = []
        
        # Use up to 3 dimensions for faceting
        dimensions_to_use = understanding.dimensions[:3] if understanding.dimensions else []
        if not dimensions_to_use:
            # If no dimensions, can't facet - fall back to single chart
            return self.recommend(intent, understanding)[:1]
        
        for dim in dimensions_to_use:
            if dim.cardinality <= 1:
                # Skip dimensions with only one value
                continue
            spec = self.recommend(intent, understanding)[0]
            spec.facet_col = dim.name
            spec.title = f"By {dim.name}"
            spec.subtitle = f"Grouped by {dim.name}"
            specs.append(spec)
        
        return specs if specs else self.recommend(intent, understanding)[:1]

    def _recommend_multi_dimension(
        self, intent: IntentResult, understanding: DataUnderstanding
    ) -> list[ChartSpec]:
        """Create comparison charts across multiple dimensions."""
        specs = []
        
        # Get primary and secondary dimensions (only if we have at least 2)
        dims = understanding.dimensions[:2] if len(understanding.dimensions) >= 2 else []
        if not dims:
            # Fall back to single chart if not enough dimensions
            return self.recommend(intent, understanding)[:1]
        
        for i, dim in enumerate(dims):
            spec = self.recommend(intent, understanding)[0]
            spec.color_col = dim.name
            spec.title = f"{spec.title} - Colored by {dim.name}"
            specs.append(spec)
        
        return specs if specs else self.recommend(intent, understanding)[:1]

    def _recommend_combined(
        self, intent: IntentResult, understanding: DataUnderstanding
    ) -> list[ChartSpec]:
        """Create complementary charts (e.g., trend + distribution)."""
        specs = []
        
        # Trend chart (if we have temporal data)
        if understanding.temporals and understanding.measures:
            try:
                trend_intent = IntentResult(
                    intent=QueryIntent.TREND,
                    confidence=0.9,
                    target_columns=intent.target_columns or [understanding.measures[0].name],
                    aggregation=intent.aggregation or "sum",
                    tier="rule",
                )
                specs.append(self.recommend(trend_intent, understanding)[0])
            except Exception:
                pass  # Skip if trend recommendation fails
        
        # Distribution chart (if we have measures)
        if understanding.measures:
            try:
                dist_intent = IntentResult(
                    intent=QueryIntent.DISTRIBUTION,
                    confidence=0.9,
                    target_columns=intent.target_columns or [understanding.measures[0].name],
                    aggregation=intent.aggregation or "sum",
                    tier="rule",
                )
                specs.append(self.recommend(dist_intent, understanding)[0])
            except Exception:
                pass  # Skip if distribution recommendation fails
        
        return specs if specs else self.recommend(intent, understanding)[:1]


    # ------------------------------------------------------------------
    def _decision_tree(
        self, intent: IntentResult, u: DataUnderstanding
    ) -> list[str]:
        i = intent.intent
        measures = u.measures
        dimensions = u.dimensions
        temporals = u.temporals
        geo = u.geo_columns

        primary_dim: Optional[ColumnProfile] = dimensions[0] if dimensions else None
        high_card = primary_dim is not None and primary_dim.cardinality > HIGH_CARDINALITY
        multi_measure = len(measures) > 1

        candidates = []
        
        if i == QueryIntent.TREND:
            if temporals:
                candidates.extend(["line", "area", "bar"])
            else:
                candidates.extend(["line", "bar"])

        elif i == QueryIntent.DISTRIBUTION:
            if primary_dim:
                candidates.extend(["box", "violin", "histogram"])
            else:
                candidates.extend(["histogram", "box"])

        elif i == QueryIntent.COMPARISON:
            if multi_measure:
                candidates.extend(["grouped_bar", "radar", "line"])
            elif high_card:
                candidates.extend(["horizontal_bar", "bar", "treemap"])
            else:
                candidates.extend(["bar", "grouped_bar", "horizontal_bar"])

        elif i == QueryIntent.CORRELATION:
            if len(measures) >= 3:
                candidates.extend(["heatmap", "scatter_matrix", "scatter"])
            else:
                candidates.extend(["scatter", "bubble", "heatmap"])

        elif i == QueryIntent.COMPOSITION:
            if primary_dim and primary_dim.cardinality > 10:
                candidates.extend(["treemap", "sunburst", "horizontal_bar"])
            else:
                candidates.extend(["pie", "donut", "treemap"])

        elif i == QueryIntent.RANKING:
            candidates.extend(["horizontal_bar", "bar", "lollipop"])

        elif i == QueryIntent.GEOGRAPHIC:
            if geo:
                candidates.extend(["choropleth", "bubble_map", "bar"])
            else:
                candidates.extend(["bar", "horizontal_bar"])

        elif i == QueryIntent.ANOMALY:
            candidates.extend(["box", "scatter", "violin"])

        elif i == QueryIntent.SUMMARY:
            if temporals and measures:
                candidates.extend(["line", "bar", "area"])
            elif measures and dimensions:
                candidates.extend(["bar", "horizontal_bar"])
            elif measures:
                candidates.extend(["histogram", "box"])
            else:
                candidates.extend(["bar"])

        elif i in {QueryIntent.MULTI_DIMENSION, QueryIntent.FACETED, QueryIntent.COMBINED}:
            candidates.extend(["bar", "line", "scatter"])
        else:
            candidates.extend(["bar", "line", "scatter"])
            
        # Handle explicit chart override
        if getattr(intent, 'explicit_chart_type', None):
            explicit = intent.explicit_chart_type
            if explicit in candidates:
                candidates.remove(explicit)
            candidates.insert(0, explicit)
            
        return candidates

    def _assign_columns(
        self,
        chart_type: str,
        intent: IntentResult,
        u: DataUnderstanding,
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        targeted = intent.target_columns

        def pick(role_list: list[ColumnProfile], prefer: list[str]) -> Optional[str]:
            for name in prefer:
                match = next((c for c in role_list if c.name == name), None)
                if match:
                    return match.name
            return role_list[0].name if role_list else None
            
        lat_col = next((c.name for c in u.columns if c.name.lower() in ('lat', 'latitude')), None)
        lon_col = next((c.name for c in u.columns if c.name.lower() in ('lon', 'longitude', 'lng')), None)

        if chart_type in {"histogram", "box", "violin"}:
            y = pick(u.measures, targeted)
            x = pick(u.dimensions, targeted) if chart_type in {"box", "violin"} else None
            return x, y, None, lat_col, lon_col

        if chart_type == "scatter":
            if len(u.measures) >= 2:
                x = pick(u.measures, targeted)
                remaining = [m for m in u.measures if m.name != x]
                y = pick(remaining, targeted)
            else:
                x = pick(u.dimensions, targeted)
                y = pick(u.measures, targeted)
            color = pick(u.dimensions, targeted) if u.dimensions else None
            return x, y, color, lat_col, lon_col

        if chart_type == "heatmap":
            x = pick(u.dimensions, targeted)
            y = pick([d for d in u.dimensions if d.name != x] if u.dimensions else [], targeted)
            z = pick(u.measures, targeted)
            return x, z, y, lat_col, lon_col  # color_col used as second dimension

        if chart_type in {"pie", "donut", "treemap", "sunburst"}:
            x = pick(u.dimensions, targeted)
            y = pick(u.measures, targeted)
            return x, y, None, lat_col, lon_col

        if chart_type in {"choropleth", "bubble_map"}:
            x = pick(u.geo_columns, targeted) or pick(u.dimensions, targeted)
            y = pick(u.measures, targeted)
            return x, y, None, lat_col, lon_col

        # Default: bar, line, area, horizontal_bar, grouped_bar, lollipop, radar
        if u.temporals and chart_type in {"line", "area"}:
            x = pick(u.temporals, targeted)
        else:
            x = pick(u.dimensions, targeted)
        y = pick(u.measures, targeted)
        color = None
        if len(u.dimensions) > 1 and chart_type not in {"horizontal_bar"}:
            second_dim = next((d for d in u.dimensions if d.name != x), None)
            if second_dim and second_dim.cardinality <= HIGH_CARDINALITY:
                color = second_dim.name

        return x, y, color, lat_col, lon_col

    def _build_titles(
        self,
        chart_type: str,
        intent: IntentResult,
        x: Optional[str],
        y: Optional[str],
    ) -> tuple[str, str]:
        y_label = y.replace("_", " ").title() if y else "Value"
        x_label = x.replace("_", " ").title() if x else "Category"

        TITLE_TEMPLATES = {
            QueryIntent.TREND: f"{y_label} Over Time",
            QueryIntent.DISTRIBUTION: f"Distribution of {y_label}",
            QueryIntent.COMPARISON: f"{y_label} by {x_label}",
            QueryIntent.CORRELATION: f"{y_label} vs {x_label}",
            QueryIntent.COMPOSITION: f"Composition of {y_label}",
            QueryIntent.RANKING: f"{'Bottom' if intent.sort_order == 'asc' else 'Top'} {intent.top_n or ''} {x_label} by {y_label}".strip(),
            QueryIntent.GEOGRAPHIC: f"{y_label} by Geography",
            QueryIntent.ANOMALY: f"Outlier Analysis — {y_label}",
            QueryIntent.SUMMARY: f"Summary: {y_label} by {x_label}",
        }
        title = TITLE_TEMPLATES.get(intent.intent, f"{y_label} by {x_label}")
        subtitle = f"Chart type: {chart_type.replace('_', ' ').title()} | Aggregation: {intent.aggregation or 'sum'}"
        return title, subtitle
