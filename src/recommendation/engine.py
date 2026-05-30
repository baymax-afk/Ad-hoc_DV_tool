from __future__ import annotations

from typing import Optional

from src.intent.models import IntentResult, QueryIntent
from src.recommendation.models import ChartSpec
from src.understanding.models import ColumnProfile, ColumnRole, DataUnderstanding

HIGH_CARDINALITY = 12


class ChartRecommendationEngine:
    def recommend(
        self, intent: IntentResult, understanding: DataUnderstanding
    ) -> ChartSpec:
        candidates = self._decision_tree(intent, understanding)
        primary = candidates[0]
        alternatives = candidates[1:]

        x, y, color = self._assign_columns(primary, intent, understanding)
        title, subtitle = self._build_titles(primary, intent, x, y)

        return ChartSpec(
            chart_type=primary,
            x_col=x,
            y_col=y,
            color_col=color,
            aggregation=intent.aggregation or "sum",
            sort_order=intent.sort_order,
            top_n=intent.top_n,
            filters=intent.filters,
            title=title,
            subtitle=subtitle,
            alternatives=alternatives,
            x_label=x.replace("_", " ").title() if x else None,
            y_label=y.replace("_", " ").title() if y else None,
        )

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

        if i == QueryIntent.TREND:
            if temporals:
                return ["line", "area", "bar"]
            return ["line", "bar"]

        if i == QueryIntent.DISTRIBUTION:
            if primary_dim:
                return ["box", "violin", "histogram"]
            return ["histogram", "box"]

        if i == QueryIntent.COMPARISON:
            if multi_measure:
                return ["grouped_bar", "radar", "line"]
            if high_card:
                return ["horizontal_bar", "bar", "treemap"]
            return ["bar", "grouped_bar", "horizontal_bar"]

        if i == QueryIntent.CORRELATION:
            if len(measures) >= 3:
                return ["heatmap", "scatter_matrix", "scatter"]
            return ["scatter", "bubble", "heatmap"]

        if i == QueryIntent.COMPOSITION:
            if primary_dim and primary_dim.cardinality > 10:
                return ["treemap", "sunburst", "horizontal_bar"]
            return ["pie", "donut", "treemap"]

        if i == QueryIntent.RANKING:
            return ["horizontal_bar", "bar", "lollipop"]

        if i == QueryIntent.GEOGRAPHIC:
            if not geo:
                return ["bar", "horizontal_bar"]
            
            # Check for lat/lon coordinates
            has_lat = any(c.name.lower() in {"lat", "latitude"} for c in geo)
            has_lon = any(c.name.lower() in {"lon", "longitude", "long"} for c in geo)
            
            # Check for state/country data
            has_state = any("state" in c.name.lower() for c in geo)
            has_country = any("country" in c.name.lower() for c in geo)
            
            if has_lat and has_lon:
                return ["scatter_geo", "bubble_map", "bar"]
            elif has_state:
                return ["state_choropleth", "bar", "horizontal_bar"]
            elif has_country:
                return ["choropleth_enhanced", "choropleth", "bubble_map"]
            else:
                return ["choropleth", "bubble_map", "bar"]

        if i == QueryIntent.ANOMALY:
            return ["box", "scatter", "violin"]

        if i == QueryIntent.SUMMARY:
            if temporals and measures:
                return ["line", "bar", "area"]
            if measures and dimensions:
                return ["bar", "horizontal_bar"]
            if measures:
                return ["histogram", "box"]
            return ["bar"]

        return ["bar", "line", "scatter"]

    def _assign_columns(
        self,
        chart_type: str,
        intent: IntentResult,
        u: DataUnderstanding,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        targeted = intent.target_columns

        def pick(role_list: list[ColumnProfile], prefer: list[str]) -> Optional[str]:
            for name in prefer:
                match = next((c for c in role_list if c.name == name), None)
                if match:
                    return match.name
            return role_list[0].name if role_list else None

        if chart_type in {"histogram", "box", "violin"}:
            y = pick(u.measures, targeted)
            x = pick(u.dimensions, targeted) if chart_type in {"box", "violin"} else None
            return x, y, None

        if chart_type == "scatter":
            if len(u.measures) >= 2:
                x = pick(u.measures, targeted)
                remaining = [m for m in u.measures if m.name != x]
                y = pick(remaining, targeted)
            else:
                x = pick(u.dimensions, targeted)
                y = pick(u.measures, targeted)
            color = pick(u.dimensions, targeted) if u.dimensions else None
            return x, y, color

        if chart_type == "heatmap":
            x = pick(u.dimensions, targeted)
            y = pick([d for d in u.dimensions if d.name != x] if u.dimensions else [], targeted)
            z = pick(u.measures, targeted)
            return x, z, y  # color_col used as second dimension

        if chart_type in {"pie", "donut", "treemap", "sunburst"}:
            x = pick(u.dimensions, targeted)
            y = pick(u.measures, targeted)
            return x, y, None

        if chart_type in {"choropleth", "choropleth_enhanced", "bubble_map", "state_choropleth"}:
            x = pick(u.geo_columns, targeted) or pick(u.dimensions, targeted)
            y = pick(u.measures, targeted)
            return x, y, None
        
        if chart_type == "scatter_geo":
            # For scatter_geo: x=latitude, y=longitude (swapped due to geo projection)
            lat = next((c.name for c in u.geo_columns if c.name.lower() in {"lat", "latitude"}), None)
            lon = next((c.name for c in u.geo_columns if c.name.lower() in {"lon", "longitude", "long"}), None)
            x = lat or pick(u.geo_columns, targeted)
            y = lon or (pick([c for c in u.geo_columns if c.name != x], targeted) if x else None)
            color = pick(u.measures, targeted) or pick(u.dimensions, targeted)
            return x, y, color

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

        return x, y, color

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
            QueryIntent.RANKING: f"Top {intent.top_n or ''} {x_label} by {y_label}".strip(),
            QueryIntent.GEOGRAPHIC: f"{y_label} by Geography",
            QueryIntent.ANOMALY: f"Outlier Analysis — {y_label}",
            QueryIntent.SUMMARY: f"Summary: {y_label} by {x_label}",
        }
        title = TITLE_TEMPLATES.get(intent.intent, f"{y_label} by {x_label}")
        subtitle = f"Chart type: {chart_type.replace('_', ' ').title()} | Aggregation: {intent.aggregation or 'sum'}"
        return title, subtitle
