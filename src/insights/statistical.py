from __future__ import annotations

import pandas as pd
from scipy import stats

from src.insights.models import StatInsight
from src.recommendation.models import ChartSpec
from src.understanding.models import DataUnderstanding


class StatisticalAnalyzer:
    CORRELATION_THRESHOLD = 0.7
    MISSING_WARNING_THRESHOLD = 0.30
    MISSING_INFO_THRESHOLD = 0.05

    def analyze(
        self,
        df: pd.DataFrame,
        understanding: DataUnderstanding,
        spec: ChartSpec,
    ) -> list[StatInsight]:
        insights: list[StatInsight] = []
        insights += self._missing_data(understanding)
        insights += self._outliers(df, understanding)
        insights += self._correlations(df, understanding)
        insights += self._top_values(df, understanding, spec)
        insights += self._skew_notes(understanding)
        return insights

    # ------------------------------------------------------------------
    def _missing_data(self, u: DataUnderstanding) -> list[StatInsight]:
        results = []
        for c in u.columns:
            if c.null_pct >= self.MISSING_WARNING_THRESHOLD:
                results.append(StatInsight(
                    type="missing",
                    description=(
                        f"'{c.name}' has {c.null_pct:.0%} missing values — "
                        "aggregations may be unreliable."
                    ),
                    severity="warning",
                    columns=[c.name],
                ))
            elif c.null_pct >= self.MISSING_INFO_THRESHOLD:
                results.append(StatInsight(
                    type="missing",
                    description=f"'{c.name}' has {c.null_pct:.1%} missing values.",
                    severity="info",
                    columns=[c.name],
                ))
        return results

    def _outliers(self, df: pd.DataFrame, u: DataUnderstanding) -> list[StatInsight]:
        results = []
        for c in u.measures:
            if not c.has_outliers:
                continue
            s = pd.to_numeric(df[c.name], errors="coerce").dropna()
            q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
            iqr = q3 - q1
            outliers = s[(s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)]
            results.append(StatInsight(
                type="outlier",
                description=(
                    f"'{c.name}' contains {len(outliers)} extreme outlier(s) "
                    f"(3× IQR rule). Max value: {s.max():,.2f}, "
                    f"IQR fence: [{q1 - 3*iqr:,.2f}, {q3 + 3*iqr:,.2f}]."
                ),
                severity="notable",
                columns=[c.name],
            ))
        return results

    def _correlations(self, df: pd.DataFrame, u: DataUnderstanding) -> list[StatInsight]:
        results = []
        measure_cols = [c.name for c in u.measures]
        if len(measure_cols) < 2:
            return results
        numeric_df = df[measure_cols].apply(pd.to_numeric, errors="coerce").dropna()
        if len(numeric_df) < 5:
            return results
        corr = numeric_df.corr()
        for i in range(len(measure_cols)):
            for j in range(i + 1, len(measure_cols)):
                r = float(corr.iloc[i, j])
                if abs(r) < self.CORRELATION_THRESHOLD:
                    continue
                direction = "positive" if r > 0 else "negative"
                strength = "strong" if abs(r) >= 0.85 else "moderate"
                results.append(StatInsight(
                    type="correlation",
                    description=(
                        f"{strength.capitalize()} {direction} correlation between "
                        f"'{measure_cols[i]}' and '{measure_cols[j]}' (r = {r:.2f})."
                    ),
                    severity="notable",
                    columns=[measure_cols[i], measure_cols[j]],
                ))
        return results

    def _top_values(
        self, df: pd.DataFrame, u: DataUnderstanding, spec: ChartSpec
    ) -> list[StatInsight]:
        results = []
        if not spec.x_col or not spec.y_col:
            return results
        if spec.x_col not in df.columns or spec.y_col not in df.columns:
            return results
        try:
            numeric_y = pd.to_numeric(df[spec.y_col], errors="coerce")
            if numeric_y.isna().all():
                return results
            idx_max = numeric_y.idxmax()
            top_label = df[spec.x_col].iloc[idx_max]
            top_val = numeric_y.iloc[idx_max]
            total = numeric_y.sum()
            share = top_val / total * 100 if total else 0
            results.append(StatInsight(
                type="top_value",
                description=(
                    f"'{top_label}' has the highest {spec.y_col.replace('_', ' ')} "
                    f"({top_val:,.2f}), representing {share:.1f}% of the total."
                ),
                severity="info",
                columns=[spec.x_col, spec.y_col],
            ))
        except Exception:
            pass
        return results

    def _skew_notes(self, u: DataUnderstanding) -> list[StatInsight]:
        results = []
        for c in u.measures:
            if c.skewness is None:
                continue
            if abs(c.skewness) >= 2.0:
                direction = "right" if c.skewness > 0 else "left"
                results.append(StatInsight(
                    type="skew",
                    description=(
                        f"'{c.name}' is heavily {direction}-skewed (skewness = {c.skewness:.2f}). "
                        "Consider log-transforming before averaging."
                    ),
                    severity="info",
                    columns=[c.name],
                ))
        return results
