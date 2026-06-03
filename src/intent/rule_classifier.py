from __future__ import annotations

import re
from typing import Optional

from rapidfuzz import fuzz, process

from src.intent.models import IntentResult, QueryIntent
from src.understanding.models import DataUnderstanding


INTENT_PATTERNS: dict[QueryIntent, list[str]] = {
    QueryIntent.TREND: [
        r"\bover time\b", r"\btrend\b", r"\bby (month|year|day|week|quarter)\b",
        r"\btimeline\b", r"\bhistor(y|ical)\b", r"\bprogress(ion)?\b",
        r"\btime series\b", r"\bgrowth\b", r"\bevolut(ion|e)\b",
    ],
    QueryIntent.DISTRIBUTION: [
        r"\bdistribut(ion|ed)\b", r"\bspread\b", r"\brange\b",
        r"\bhistogram\b", r"\bfrequen(cy|cies)\b", r"\bvariat(ion|ance)\b",
        r"\bhow (is|are).+ spread\b",
    ],
    QueryIntent.COMPARISON: [
        r"\bcompare\b", r"\bby (region|country|category|segment|group|type|department)\b",
        r"\bacross\b", r"\bbetween\b", r"\bdifference\b", r"\bvs\b",
        r"\bbreak(down)? by\b",
    ],
    QueryIntent.CORRELATION: [
        r"\bvs\.?\b", r"\bversus\b", r"\bcorrelat(e|ion)\b",
        r"\brelationship\b", r"\bscatter\b", r"\bimpact of\b",
        r"\baffect\b", r"\bdepend(s)? on\b",
    ],
    QueryIntent.RANKING: [
        r"\btop \d+\b", r"\bbottom \d+\b", r"\bbest\b", r"\bworst\b",
        r"\branking\b", r"\bleaderboard\b", r"\bhighest\b", r"\blowest\b",
        r"\bmost\b", r"\bleast\b",
    ],
    QueryIntent.COMPOSITION: [
        r"\bbreakdown\b", r"\bcomposition\b", r"\bshare\b",
        r"\bproportion\b", r"\bpercentage\b", r"\bpie\b",
        r"\bpart(s)? of\b", r"\bmix\b", r"\bportfolio\b",
    ],
    QueryIntent.GEOGRAPHIC: [
        r"\bmap\b", r"\bcountry\b", r"\bregion\b", r"\bstate\b",
        r"\bcity\b", r"\bgeograph(y|ic)\b", r"\blocation\b",
    ],
    QueryIntent.ANOMALY: [
        r"\boutlier\b", r"\banomal(y|ies)\b", r"\bspike\b", r"\bdrop\b",
        r"\bunusual\b", r"\bextreme\b", r"\baberration\b",
    ],
    QueryIntent.SUMMARY: [
        r"\bsummar(y|ize|ise)\b", r"\boverview\b", r"\bstat(istic)?s\b",
        r"\bdescribe\b", r"\bwhat (is|are)\b", r"\btell me about\b",
    ],
    # Multi-chart intents
    QueryIntent.MULTI_DIMENSION: [
        r"\bby \w+ and \w+\b", r"\bby \w+(?:\s+and|,)\s+by \w+\b",
        r"\bacross \w+ and \w+\b", r"\b\w+ AND \w+\b",
        r"\bboth\b.*\bby\b", r"\bfor\s+both\b",
    ],
    QueryIntent.FACETED: [
        r"\bfor each \w+\b", r"\bby each \w+\b",
        r"\bseparately\b", r"\beach (category|region|product|group)\b",
        r"\bper \w+\b", r"\bsplit by\b",
    ],
    QueryIntent.COMBINED: [
        r"\btrend.*distribution\b", r"\bdistribution.*trend\b",
        r"\band\b", r"\bplus\b", r"\bas well as\b",
        r"\bboth.*and\b", r"\nside.?by.?side\b",
    ],
}

AGGREGATION_PATTERNS = {
    "sum": [r"\btotal\b", r"\bsum\b", r"\bcumulative\b"],
    "avg": [r"\baverage\b", r"\bavg\b", r"\bmean\b", r"\btypical\b"],
    "count": [r"\bcount\b", r"\bnumber of\b", r"\bhow many\b", r"\bvolume\b"],
    "max": [r"\bmaximum\b", r"\bmax\b", r"\bpeak\b", r"\bhighest\b"],
    "min": [r"\bminimum\b", r"\bmin\b", r"\blowest\b"],
}

TOP_N_PATTERN = re.compile(r"\b(?:top|bottom)\s+(\d+)\b", re.IGNORECASE)


class RuleIntentClassifier:
    CONFIDENCE_THRESHOLD = 0.3

    def classify(
        self, query: str, understanding: DataUnderstanding
    ) -> Optional[IntentResult]:
        q = query.lower()
        scores: dict[QueryIntent, int] = {}
        for intent, patterns in INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, q))
            if score:
                scores[intent] = score

        if not scores:
            return None

        best = max(scores, key=scores.get)
        # 1 match → 0.4, 2 matches → 0.7, 3+ → 1.0
        confidence = min(0.3 + scores[best] * 0.35, 1.0)

        if confidence < self.CONFIDENCE_THRESHOLD:
            return None

        return IntentResult(   #here it returns the json format
            intent=best,
            confidence=confidence,
            target_columns=self._extract_columns(q, understanding),
            filters=self._extract_filters(q, understanding),
            aggregation=self._extract_aggregation(q),
            top_n=self._extract_top_n(q),
            tier="rule",
            explicit_chart_type=self._extract_explicit_chart(q),
        )

    # ------------------------------------------------------------------
    def _extract_columns(self, q: str, u: DataUnderstanding) -> list[str]:
        all_cols = [c.name for c in u.columns]
        matched = []
        for col in all_cols:
            variants = [col, col.replace("_", " ")]
            if any(v in q for v in variants):
                matched.append(col)
        if not matched:
            results = process.extract(q, all_cols, scorer=fuzz.partial_ratio, limit=2)
            matched = [r[0] for r in results if r[1] > 70]
        return matched

    def _extract_aggregation(self, q: str) -> Optional[str]:
        for agg, patterns in AGGREGATION_PATTERNS.items():
            if any(re.search(p, q) for p in patterns):
                return agg
        return "sum"

    def _extract_top_n(self, q: str) -> Optional[int]:
        match = TOP_N_PATTERN.search(q)
        return int(match.group(1)) if match else None

    def _extract_filters(self, q: str, u: DataUnderstanding) -> dict:
        filters: dict = {}
        for col in u.dimensions:
            for val in col.top_values:
                val_str = str(val).lower()
                if val_str in q:
                    filters[col.name] = val
        return filters

    def _extract_explicit_chart(self, q: str) -> Optional[str]:
        chart_types = [
            "bar", "line", "scatter", "pie", "histogram", "heatmap", 
            "choropleth", "treemap", "radar", "grouped_bar", "horizontal_bar", 
            "area", "donut", "sunburst", "bubble_map", "scatter_matrix", 
            "box", "violin", "bubble"
        ]
        chart_types_sorted = sorted(chart_types, key=len, reverse=True)
        for ct in chart_types_sorted:
            clean_ct = ct.replace("_", " ")
            if re.search(r'\b' + re.escape(clean_ct) + r'(?:\s+chart|plot|map)?\b', q):
                return ct
        return None
