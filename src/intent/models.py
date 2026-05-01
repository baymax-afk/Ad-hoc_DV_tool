from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class QueryIntent(str, Enum):
    DISTRIBUTION = "distribution"
    TREND = "trend"
    COMPARISON = "comparison"
    CORRELATION = "correlation"
    COMPOSITION = "composition"
    RANKING = "ranking"
    GEOGRAPHIC = "geographic"
    ANOMALY = "anomaly"
    SUMMARY = "summary"


@dataclass
class IntentResult:
    intent: QueryIntent
    confidence: float
    target_columns: list[str] = field(default_factory=list)
    filters: dict = field(default_factory=dict)
    aggregation: Optional[str] = None       # sum|avg|count|max|min
    group_by: Optional[str] = None
    sort_order: Optional[str] = None        # asc|desc
    top_n: Optional[int] = None
    tier: str = "rule"                      # "rule" or "llm"
    raw_llm_response: Optional[dict] = None
