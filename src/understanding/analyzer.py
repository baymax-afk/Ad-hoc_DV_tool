from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.ingestion.models import DataProfile
from src.understanding.models import ColumnProfile, ColumnRole, DataUnderstanding
from src.utils.date_handler import (
    DATE_FORMATS,
    is_temporal,
    parse_date_column,
    infer_granularity as infer_date_granularity,
)
from src.utils.geo_handler import (
    GEO_HINTS,
    is_latitude_column,
    is_longitude_column,
    is_country_column,
    is_state_column,
    detect_geo_type,
)

IDENTIFIER_RATIO = 0.95
NUMERIC_RATIO_THRESHOLD = 0.85
MIN_ROWS_FOR_CARDINALITY_ID = 50  # small datasets are rarely all-identifier

# Column name keywords that strongly suggest an identifier
ID_NAME_HINTS = {"id", "key", "code", "num", "no", "uuid", "guid", "sku", "ref", "hash"}


class DataUnderstandingEngine:
    def analyze(self, profile: DataProfile) -> DataUnderstanding:
        df = profile.df
        n = len(df)
        column_profiles = [
            self._analyze_column(col, df[col], n) for col in df.columns
        ]

        understanding = DataUnderstanding(
            profile=profile,
            columns=column_profiles,
            measures=[c for c in column_profiles if c.role == ColumnRole.MEASURE],
            dimensions=[c for c in column_profiles if c.role == ColumnRole.DIMENSION],
            temporals=[c for c in column_profiles if c.role == ColumnRole.TEMPORAL],
            geo_columns=[c for c in column_profiles if c.role == ColumnRole.GEOGRAPHIC],
            identifiers=[c for c in column_profiles if c.role == ColumnRole.IDENTIFIER],
            text_columns=[c for c in column_profiles if c.role == ColumnRole.TEXT],
        )

        understanding.has_time_series = len(understanding.temporals) > 0
        understanding.suggested_grain = self._suggest_grain(understanding)
        return understanding

    # ------------------------------------------------------------------
    def _analyze_column(self, name: str, s: pd.Series, n: int) -> ColumnProfile:
        null_pct = float(s.isna().mean())
        s_clean = s.dropna()
        cardinality = int(s_clean.nunique())
        cardinality_ratio = cardinality / max(n, 1)

        role = self._infer_role(name, s_clean, cardinality, cardinality_ratio, n)

        cp = ColumnProfile(
            name=name,
            role=role,
            dtype_raw=str(s.dtype),
            null_pct=null_pct,
            cardinality=cardinality,
            cardinality_ratio=cardinality_ratio,
            sample_values=s_clean.unique()[:5].tolist(),
        )

        if role == ColumnRole.MEASURE:
            self._enrich_measure(cp, s_clean)
        elif role == ColumnRole.TEMPORAL:
            self._enrich_temporal(cp, s_clean)
        elif role == ColumnRole.DIMENSION:
            cp.top_values = s_clean.value_counts().head(10).index.tolist()

        return cp

    def _infer_role(
        self,
        name: str,
        s: pd.Series,
        cardinality: int,
        cardinality_ratio: float,
        n: int,
    ) -> ColumnRole:
        name_lower = name.lower()

        # Geographic — check both name hints and actual data validity
        if any(hint in name_lower for hint in GEO_HINTS):
            # Validate coordinates
            if is_latitude_column(name, s) or is_longitude_column(name, s):
                return ColumnRole.GEOGRAPHIC
            # Validate country/state
            if is_country_column(s) or is_state_column(s):
                return ColumnRole.GEOGRAPHIC
            # Generic geo hint without validation
            return ColumnRole.GEOGRAPHIC
        
        # Check for geographic data even without name hints
        if detect_geo_type(name, s) is not None:
            return ColumnRole.GEOGRAPHIC

        # Temporal
        if is_temporal(s):
            return ColumnRole.TEMPORAL

        # Numeric path
        numeric = pd.to_numeric(s, errors="coerce")
        numeric_ratio = float(numeric.notna().mean())

        if numeric_ratio >= NUMERIC_RATIO_THRESHOLD:
            # Identifier: near-unique numeric only on large datasets OR when the name hints at ID
            name_words = set(re.split(r"[_\s]", name.lower()))
            has_id_name = bool(name_words & ID_NAME_HINTS)
            if cardinality_ratio >= IDENTIFIER_RATIO and (has_id_name or n >= MIN_ROWS_FOR_CARDINALITY_ID):
                return ColumnRole.IDENTIFIER
            # Leading-zero strings stored as numbers → treat as dimension
            str_series = s.astype(str)
            if str_series.str.match(r"^0\d+$").mean() > 0.5:
                return ColumnRole.DIMENSION
            return ColumnRole.MEASURE

        # String path
        if cardinality_ratio >= IDENTIFIER_RATIO:
            return ColumnRole.IDENTIFIER

        # Long free-form text
        str_lengths = s.astype(str).str.len()
        if str_lengths.mean() > 60:
            return ColumnRole.TEXT

        return ColumnRole.DIMENSION

    def _is_temporal(self, s: pd.Series) -> bool:
        """Check if series represents temporal data."""
        return is_temporal(s)

    def _enrich_measure(self, cp: ColumnProfile, s: pd.Series) -> None:
        numeric = pd.to_numeric(s, errors="coerce").dropna()
        if len(numeric) == 0:
            return
        cp.mean = float(numeric.mean())
        cp.std = float(numeric.std()) if len(numeric) > 1 else 0.0
        cp.min_val = float(numeric.min())
        cp.max_val = float(numeric.max())
        cp.skewness = float(stats.skew(numeric)) if len(numeric) >= 3 else 0.0
        cp.has_outliers = self._detect_outliers(numeric)
        cp.distribution = self._classify_distribution(numeric)

    def _enrich_temporal(self, cp: ColumnProfile, s: pd.Series) -> None:
        parsed, fmt = parse_date_column(s, strict=False)
        if parsed is None:
            return
        cp.date_format = fmt
        cp.time_granularity = infer_date_granularity(parsed.dropna())

    def _detect_outliers(self, s: pd.Series) -> bool:
        if len(s) < 4:
            return False
        q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
        iqr = q3 - q1
        if iqr == 0:
            return False
        return bool(((s < q1 - 3 * iqr) | (s > q3 + 3 * iqr)).any())

    def _classify_distribution(self, s: pd.Series) -> str:
        if len(s) < 8:
            return "unknown"
        sk = float(stats.skew(s))
        if len(s) >= 20:
            try:
                _, p = stats.normaltest(s)
                if p > 0.05:
                    return "normal"
            except Exception:
                pass
        if sk > 1.0:
            return "skewed_right"
        if sk < -1.0:
            return "skewed_left"
        return "approximately_normal"

    def _infer_granularity(self, dates: pd.Series) -> str:
        """Infer temporal granularity from date series."""
        return infer_date_granularity(dates)

    def _suggest_grain(self, u: DataUnderstanding) -> Optional[str]:
        if not u.has_time_series:
            return None
        t = u.temporals[0]
        return t.time_granularity
