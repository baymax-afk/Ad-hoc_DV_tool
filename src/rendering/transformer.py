from __future__ import annotations

import pandas as pd

from src.recommendation.models import ChartSpec
from src.understanding.models import DataUnderstanding


AGG_FUNCTIONS = {
    "sum": "sum",
    "avg": "mean",
    "mean": "mean",
    "count": "count",
    "max": "max",
    "min": "min",
}


class DataTransformer:
    def transform(self, df: pd.DataFrame, spec: ChartSpec, understanding: DataUnderstanding = None) -> pd.DataFrame:
        df = df.copy()

        # Apply filters
        for col, val in (spec.filters or {}).items():
            if col == "date_filter" and isinstance(val, list):
                if not understanding:
                    continue
                temporal_cols = [c.name for c in understanding.temporals if c.name in df.columns]
                if temporal_cols and val:
                    for d_filter in val:
                        iso_str = d_filter.get("iso")
                        if not iso_str:
                            continue
                        
                        mask = pd.Series(False, index=df.index)
                        if "/" in iso_str:
                            start_str, end_str = iso_str.split("/")
                            try:
                                start_dt = pd.to_datetime(start_str)
                                end_dt = pd.to_datetime(end_str)
                                for t_col in temporal_cols:
                                    t_series = pd.to_datetime(df[t_col], errors='coerce')
                                    mask = mask | ((t_series >= start_dt) & (t_series <= end_dt))
                            except Exception:
                                pass
                        else:
                            try:
                                exact_dt = pd.to_datetime(iso_str).date()
                                for t_col in temporal_cols:
                                    t_series = pd.to_datetime(df[t_col], errors='coerce')
                                    mask = mask | (t_series.dt.date == exact_dt)
                            except Exception:
                                pass
                        
                        df = df[mask]
                continue

            if col in df.columns:
                df = df[df[col].astype(str) == str(val)]

        if df.empty:
            return df

        # Aggregate when we have x and y
        if spec.x_col and spec.y_col and spec.x_col in df.columns and spec.y_col in df.columns:
            df = self._aggregate(df, spec)

        # Sort
        is_temporal_x = False
        if understanding and spec.x_col:
            is_temporal_x = any(c.name == spec.x_col for c in understanding.temporals)

        if is_temporal_x and not spec.top_n:
            df = df.sort_values(spec.x_col, ascending=True)
        elif spec.y_col and spec.y_col in df.columns:
            if spec.sort_order:
                df = df.sort_values(spec.y_col, ascending=(spec.sort_order == "asc"))
            elif spec.top_n:
                df = df.sort_values(spec.y_col, ascending=False)

        # Top N
        if spec.top_n and spec.top_n > 0:
            df = df.head(spec.top_n)
            # if we took top N, and it's temporal, re-sort chronologically for display
            if is_temporal_x:
                df = df.sort_values(spec.x_col, ascending=True)

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
