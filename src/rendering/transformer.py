from __future__ import annotations

import pandas as pd

from src.recommendation.models import ChartSpec
from src.utils.date_handler import ensure_datetime


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

        # Convert datetime columns for proper sorting/rendering
        for col in df.columns:
            df[col] = ensure_datetime(df[col])

        # Apply filters
        for col, val in (spec.filters or {}).items():
            if col in df.columns:
                df = df[df[col].astype(str) == str(val)]

        if df.empty:
            return df

        # Aggregate when we have x and y
        if spec.x_col and spec.y_col and spec.x_col in df.columns and spec.y_col in df.columns:
            df = self._aggregate(df, spec)

        # Sort (handles datetime properly now)
        if spec.sort_order and spec.y_col and spec.y_col in df.columns:
            df = df.sort_values(spec.y_col, ascending=(spec.sort_order == "asc"))
        # For temporal x-axis, ensure proper sorting
        elif spec.x_col and pd.api.types.is_datetime64_any_dtype(df.get(spec.x_col)):
            df = df.sort_values(spec.x_col)

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
