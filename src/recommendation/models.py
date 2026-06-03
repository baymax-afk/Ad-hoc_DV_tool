from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChartSpec:
    chart_type: str                     # bar|line|scatter|pie|histogram|heatmap|choropleth|…
    x_col: Optional[str]
    y_col: Optional[str]
    color_col: Optional[str] = None
    size_col: Optional[str] = None
    facet_col: Optional[str] = None
    aggregation: str = "sum"
    sort_order: Optional[str] = None    # asc|desc
    top_n: Optional[int] = None
    filters: dict = field(default_factory=dict)
    title: str = ""
    subtitle: str = ""
    alternatives: list[str] = field(default_factory=list)
    x_label: Optional[str] = None
    y_label: Optional[str] = None


@dataclass
class MultiChartSpec:
    """Multi-chart specification for compound visualizations."""
    specs: list[ChartSpec]              # Individual chart specs
    layout_type: str = "grid"           # grid|row|column|faceted
    title: str = ""
    subtitle: Optional[str] = None
    grid_cols: int = 2
    combine_legend: bool = True         # Show single legend for all charts

