from __future__ import annotations

import pandas as pd

from src.recommendation.models import ChartSpec


AGG_FUNCTIONS = {
    "sum": "sum",
    "avg": "mean",
    "mean": "mean",
    "count": "count",
    "max": "max",
    "min": "min",
}


class DataTransformer:
    def transform(self, df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        df = df.copy()

        # Apply filters
        for col, val in (spec.filters or {}).items():
            if col in df.columns:
                df = df[df[col].astype(str) == str(val)]

        if df.empty:
            return df

        # Aggregate when we have x and y
        if spec.x_col and spec.y_col and spec.x_col in df.columns and spec.y_col in df.columns:
            df = self._aggregate(df, spec)

        # Sort
        if spec.sort_order and spec.y_col and spec.y_col in df.columns:
            df = df.sort_values(spec.y_col, ascending=(spec.sort_order == "asc"))

        # Top N
        if spec.top_n and spec.top_n > 0:
            df = df.head(spec.top_n)

        return df.reset_index(drop=True)

    def _aggregate(self, df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        agg_fn = AGG_FUNCTIONS.get(spec.aggregation or "sum", "sum")
        group_cols = [c for c in [spec.x_col, spec.color_col] if c and c in df.columns]

        if not group_cols:
            return df

        # Keep only numeric target
        try:
            df[spec.y_col] = pd.to_numeric(df[spec.y_col], errors="coerce")
        except Exception:
            pass

        try:
            result = df.groupby(group_cols, as_index=False)[spec.y_col].agg(agg_fn)
            return result
        except Exception:
            return df
