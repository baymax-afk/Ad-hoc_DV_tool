from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.ingestion.models import DataProfile


class ColumnRole(str, Enum):
    DIMENSION = "dimension"
    MEASURE = "measure"
    TEMPORAL = "temporal"
    IDENTIFIER = "identifier"
    TEXT = "text"
    GEOGRAPHIC = "geographic"


@dataclass
class ColumnProfile:
    name: str
    role: ColumnRole
    dtype_raw: str
    null_pct: float
    cardinality: int
    cardinality_ratio: float
    sample_values: list

    # measures
    mean: Optional[float] = None
    std: Optional[float] = None
    skewness: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    has_outliers: bool = False
    distribution: Optional[str] = None  # "normal"|"skewed_right"|"skewed_left"|"approximately_normal"

    # temporal
    date_format: Optional[str] = None
    time_granularity: Optional[str] = None  # "day"|"month"|"year"

    # dimension
    top_values: list = field(default_factory=list)


@dataclass
class DataUnderstanding:
    profile: DataProfile
    columns: list[ColumnProfile]

    # Convenient grouped views
    measures: list[ColumnProfile] = field(default_factory=list)
    dimensions: list[ColumnProfile] = field(default_factory=list)
    temporals: list[ColumnProfile] = field(default_factory=list)
    geo_columns: list[ColumnProfile] = field(default_factory=list)
    identifiers: list[ColumnProfile] = field(default_factory=list)
    text_columns: list[ColumnProfile] = field(default_factory=list)

    has_time_series: bool = False
    suggested_grain: Optional[str] = None
    llm_summary: Optional[str] = None

    def schema_str(self) -> str:
        lines = []
        for c in self.columns:
            extras = f", cardinality={c.cardinality}, sample={c.sample_values[:3]}"
            if c.role == ColumnRole.MEASURE:
                extras += f", mean={c.mean:.2f}, skew={c.skewness:.2f}" if c.mean is not None else ""
            lines.append(f"- {c.name} ({c.role.value}{extras})")
        return "\n".join(lines)
