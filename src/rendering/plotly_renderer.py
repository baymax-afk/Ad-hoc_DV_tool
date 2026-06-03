from __future__ import annotations

from typing import Callable
import warnings

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.core.exceptions import UnsupportedChartError
from src.recommendation.models import ChartSpec

THEME = {
    "template": "plotly_white",
    "colors": px.colors.qualitative.Set2,
    "font": "Inter, system-ui, sans-serif",
}

_REGISTRY: dict[str, Callable[[pd.DataFrame, ChartSpec], go.Figure]] = {}


# ── geographic utilities ──────────────────────────────────────────────
def _normalize_country_name(name: str) -> str:
    """Normalize country names to standard Plotly choropleth format."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    if not isinstance(name, str):
        return str(name).strip() if str(name).strip() else ""
    if not name.strip():
        return ""
    
    # Common aliases and corrections
    country_aliases = {
        "USA": "United States",
        "US": "United States",
        "United States of America": "United States",
        "UK": "United Kingdom",
        "England": "United Kingdom",
        "Scotland": "United Kingdom",
        "Wales": "United Kingdom",
        "Northern Ireland": "United Kingdom",
        "UAE": "United Arab Emirates",
        "Czech": "Czechia",
        "Czechia": "Czechia",
        "Slovakia": "Slovakia",
        "South Korea": "South Korea",
        "Korea": "South Korea",
        "North Korea": "North Korea",
        "Vietnam": "Vietnam",
        "Viet Nam": "Vietnam",
        "Taiwan": "Taiwan",
        "Iran": "Iran",
        "Syria": "Syria",
        "Palestine": "West Bank",
        "Congo": "Congo (Democratic Republic)",
        "DRC": "Congo (Democratic Republic)",
        "Democratic Republic of Congo": "Congo (Democratic Republic)",
        "Congo Brazzaville": "Congo",
        "Bolivia": "Bolivia",
        "East Timor": "Timor-Leste",
        "Timor-Leste": "Timor-Leste",
        "Micronesia": "Micronesia",
        "Brunei": "Brunei",
        "Brunei Darussalam": "Brunei",
        "Cape Verde": "Cape Verde",
        "Equatorial Guinea": "Equatorial Guinea",
        "Sao Tome": "São Tomé and Príncipe",
        "São Tomé and Príncipe": "São Tomé and Príncipe",
        "St Vincent": "Saint Vincent and the Grenadines",
        "Saint Lucia": "Saint Lucia",
        "Dominica": "Dominica",
        "Antigua": "Antigua and Barbuda",
        "Antigua and Barbuda": "Antigua and Barbuda",
        "Trinidad": "Trinidad and Tobago",
        "Trinidad and Tobago": "Trinidad and Tobago",
        "Bahamas": "Bahamas",
        "Barbados": "Barbados",
        "Saint Kitts": "Saint Kitts and Nevis",
        "Saint Kitts and Nevis": "Saint Kitts and Nevis",
        "Grenadines": "Saint Vincent and the Grenadines",
        "Curacao": "Curaçao",
        "Curaçao": "Curaçao",
        "Sint Maarten": "Sint Maarten (Dutch part)",
        "St Maarten": "Sint Maarten (Dutch part)",
        "Aruba": "Aruba",
        "Bonaire": "Bonaire, Sint Eustatius and Saba",
    }
    
    name_clean = name.strip()
    return country_aliases.get(name_clean, name_clean)


def _try_choropleth(df: pd.DataFrame, spec: ChartSpec, locationmode: str) -> go.Figure | None:
    """Attempt to render choropleth with given location mode. Returns None if fails."""
    try:
        df_copy = df.copy()
        # Remove rows with null/empty locations
        df_copy = df_copy[df_copy[spec.x_col].notna()]
        if locationmode == "country names":
            df_copy[spec.x_col] = df_copy[spec.x_col].apply(_normalize_country_name)
            # Remove empty strings after normalization
            df_copy = df_copy[df_copy[spec.x_col].str.strip() != ""]
        
        if df_copy.empty:
            return None
            
        fig = px.choropleth(
            df_copy,
            locations=spec.x_col,
            color=spec.y_col,
            locationmode=locationmode,
            scope="usa" if locationmode == "USA-states" else "world",
            color_continuous_scale="Viridis",
            labels={spec.y_col: spec.y_label or spec.y_col},
        )
        return fig
    except (KeyError, ValueError, AttributeError):
        return None



def register(chart_type: str):
    def decorator(fn: Callable[[pd.DataFrame, ChartSpec], go.Figure]):
        _REGISTRY[chart_type] = fn
        return fn
    return decorator


# ── chart renderers ──────────────────────────────────────────────────

@register("bar")
def _bar(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.bar(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        color_discrete_sequence=THEME["colors"],
        labels={spec.y_col: spec.y_label or spec.y_col,
                spec.x_col: spec.x_label or spec.x_col},
    )


@register("horizontal_bar")
def _hbar(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.bar(
        df, x=spec.y_col, y=spec.x_col, orientation="h",
        color=spec.color_col,
        color_discrete_sequence=THEME["colors"],
        labels={spec.y_col: spec.y_label or spec.y_col,
                spec.x_col: spec.x_label or spec.x_col},
    )


@register("grouped_bar")
def _grouped_bar(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.bar(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        barmode="group",
        color_discrete_sequence=THEME["colors"],
    )


@register("lollipop")
def _lollipop(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_shape(
            type="line",
            x0=0, x1=row[spec.y_col],
            y0=row[spec.x_col], y1=row[spec.x_col],
            line={"color": THEME["colors"][0], "width": 2},
        )
    fig.add_trace(go.Scatter(
        x=df[spec.y_col], y=df[spec.x_col],
        mode="markers",
        marker={"size": 10, "color": THEME["colors"][0]},
    ))
    fig.update_layout(xaxis_title=spec.y_label, yaxis_title=spec.x_label)
    return fig


@register("line")
def _line(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.line(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        markers=True,
        color_discrete_sequence=THEME["colors"],
        labels={spec.y_col: spec.y_label or spec.y_col,
                spec.x_col: spec.x_label or spec.x_col},
    )


@register("area")
def _area(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.area(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        color_discrete_sequence=THEME["colors"],
    )


@register("scatter")
def _scatter(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    trendline = "ols" if not spec.color_col and len(df) >= 5 else None
    return px.scatter(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        size=spec.size_col,
        trendline=trendline,
        color_discrete_sequence=THEME["colors"],
        labels={spec.y_col: spec.y_label or spec.y_col,
                spec.x_col: spec.x_label or spec.x_col},
    )


@register("bubble")
def _bubble(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.scatter(
        df, x=spec.x_col, y=spec.y_col,
        size=spec.size_col or spec.y_col,
        color=spec.color_col,
        color_discrete_sequence=THEME["colors"],
    )


@register("histogram")
def _histogram(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.histogram(
        df, x=spec.y_col or spec.x_col,
        nbins=min(50, max(10, len(df) // 20)),
        marginal="box",
        color_discrete_sequence=THEME["colors"],
    )


@register("box")
def _box(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.box(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        points="outliers",
        color_discrete_sequence=THEME["colors"],
    )


@register("violin")
def _violin(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.violin(
        df, x=spec.x_col, y=spec.y_col, color=spec.color_col,
        box=True, points="outliers",
        color_discrete_sequence=THEME["colors"],
    )


@register("pie")
def _pie(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.pie(
        df, names=spec.x_col, values=spec.y_col,
        color_discrete_sequence=THEME["colors"],
    )


@register("donut")
def _donut(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.pie(
        df, names=spec.x_col, values=spec.y_col,
        hole=0.4,
        color_discrete_sequence=THEME["colors"],
    )


@register("treemap")
def _treemap(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    path = [px.Constant("All")]
    if spec.color_col and spec.color_col in df.columns:
        path.append(spec.color_col)
    if spec.x_col and spec.x_col in df.columns:
        path.append(spec.x_col)
    return px.treemap(
        df, path=path, values=spec.y_col,
        color=spec.y_col,
        color_continuous_scale="Blues",
    )


@register("sunburst")
def _sunburst(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    path = [px.Constant("All")]
    if spec.color_col and spec.color_col in df.columns:
        path.append(spec.color_col)
    if spec.x_col and spec.x_col in df.columns:
        path.append(spec.x_col)
    return px.sunburst(df, path=path, values=spec.y_col)


@register("heatmap")
def _heatmap(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    try:
        pivot = df.pivot_table(
            index=spec.x_col, columns=spec.color_col or spec.x_col,
            values=spec.y_col, aggfunc="mean",
        )
        return px.imshow(pivot, color_continuous_scale="RdBu_r", text_auto=".1f")
    except Exception:
        return px.density_heatmap(df, x=spec.x_col, y=spec.y_col)


@register("scatter_matrix")
def _scatter_matrix(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    numeric_cols = df.select_dtypes("number").columns.tolist()[:6]
    return px.scatter_matrix(
        df, dimensions=numeric_cols, color=spec.color_col,
        color_discrete_sequence=THEME["colors"],
    )


@register("choropleth")
def _choropleth(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    # Try multiple location modes with fallback
    for locationmode in ["country names", "ISO-3", "USA-states"]:
        fig = _try_choropleth(df, spec, locationmode)
        if fig is not None:
            return fig
    
    # Fallback to bar chart if choropleth fails
    warnings.warn(
        f"Could not render choropleth with column '{spec.x_col}'. "
        "Falling back to bar chart. Ensure location data matches supported format.",
        UserWarning
    )
    return px.bar(
        df, x=spec.x_col, y=spec.y_col,
        color_discrete_sequence=THEME["colors"],
        labels={spec.y_col: spec.y_label or spec.y_col},
    )


@register("bubble_map")
def _bubble_map(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    try:
        df_copy = df.copy()
        df_copy[spec.x_col] = df_copy[spec.x_col].apply(_normalize_country_name)
        
        fig = px.scatter_geo(
            df_copy, locations=spec.x_col, size=spec.y_col,
            locationmode="country names",
            color=spec.color_col,
            color_discrete_sequence=THEME["colors"],
            labels={spec.y_col: spec.y_label or spec.y_col},
        )
        return fig
    except (KeyError, ValueError) as e:
        warnings.warn(
            f"Could not render bubble map with column '{spec.x_col}'. "
            "Falling back to scatter plot. {str(e)}",
            UserWarning
        )
        # Fallback to scatter plot
        return px.scatter(
            df, x=spec.x_col, y=spec.y_col, size=spec.y_col,
            color=spec.color_col,
            color_discrete_sequence=THEME["colors"],
            labels={spec.y_col: spec.y_label or spec.y_col},
        )


@register("radar")
def _radar(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    fig = go.Figure()
    categories = df[spec.x_col].tolist() if spec.x_col else []
    values = df[spec.y_col].tolist() if spec.y_col else []
    fig.add_trace(go.Scatterpolar(
        r=values + values[:1],
        theta=categories + categories[:1],
        fill="toself",
        line_color=THEME["colors"][0],
    ))
    fig.update_layout(polar={"radialaxis": {"visible": True}})
    return fig


# ── public renderer ───────────────────────────────────────────────────

class PlotlyRenderer:
    def render(self, df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
        fn = _REGISTRY.get(spec.chart_type)
        if fn is None:
            raise UnsupportedChartError(
                f"No renderer for chart type '{spec.chart_type}'. "
                f"Available: {sorted(_REGISTRY.keys())}"
            )
        if df.empty:
            return self._empty_figure(spec)

        fig = fn(df, spec)
        return self._decorate(fig, spec)

    def supported_types(self) -> list[str]:
        return sorted(_REGISTRY.keys())

    def _decorate(self, fig: go.Figure, spec: ChartSpec) -> go.Figure:
        fig.update_layout(
            title={
                "text": f"<b>{spec.title}</b>",
                "x": 0.05,
                "font": {"size": 18},
            },
            template=THEME["template"],
            font={"family": THEME["font"], "size": 13},
            legend={"orientation": "h", "yanchor": "bottom", "y": -0.25},
            margin={"t": 90, "b": 60, "l": 60, "r": 40},
            hoverlabel={"font_size": 13},
        )
        if spec.subtitle:
            fig.add_annotation(
                text=spec.subtitle,
                xref="paper", yref="paper",
                x=0.05, y=1.04,
                showarrow=False,
                font={"size": 11, "color": "#888"},
                xanchor="left",
            )
        return fig

    def _empty_figure(self, spec: ChartSpec) -> go.Figure:
        fig = go.Figure()
        fig.update_layout(
            title=f"{spec.title} — No data after filters",
            template=THEME["template"],
            annotations=[{
                "text": "No matching data. Try removing filters.",
                "xref": "paper", "yref": "paper",
                "x": 0.5, "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "#999"},
            }],
        )
        return fig
