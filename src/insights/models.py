from dataclasses import dataclass, field


@dataclass
class StatInsight:
    type: str           # outlier|trend|correlation|missing|skew|top_value
    description: str
    severity: str       # info|notable|warning
    columns: list[str] = field(default_factory=list)


@dataclass
class InsightBundle:
    statistical: list[StatInsight] = field(default_factory=list)
    narrative: list[str] = field(default_factory=list)
