"""Date parsing, validation, and conversion utilities."""
from __future__ import annotations

from typing import Optional

import pandas as pd


# Comprehensive date formats sorted by likelihood of occurrence
DATE_FORMATS = [
    # ISO standard (most reliable)
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    # US formats
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m-%d-%Y",
    # EU formats
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d.%m.%Y %H:%M:%S",
    # Other common formats
    "%Y/%m/%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y%m%d",
    # Named months
    "%b %d %Y",
    "%b %d %Y %H:%M:%S",
    "%B %d %Y",
    "%B %d %Y %H:%M:%S",
    "%d %b %Y",
    "%d %b %Y %H:%M:%S",
    "%d %B %Y",
    "%d %B %Y %H:%M:%S",
    # Time-first variants
    "%H:%M:%S %Y-%m-%d",
    "%H:%M %Y-%m-%d",
    # Numeric with time
    "%Y%m%d %H:%M:%S",
    "%d%m%Y",
    # Other variants
    "%Y-%m-%d %H:%M",
    "%m/%d/%y",
    "%d/%m/%y",
]


def parse_date_column(s: pd.Series, strict: bool = True) -> tuple[Optional[pd.Series], Optional[str]]:
    """
    Parse a series into datetime using multiple format strategies.
    
    Returns: (parsed_series, format_used) or (None, None) if parsing fails
    """
    if pd.api.types.is_datetime64_any_dtype(s):
        return s, "already_datetime"
    
    sample = s.dropna().astype(str).head(50)
    if len(sample) == 0:
        return None, None
    
    # Try each explicit format
    for fmt in DATE_FORMATS:
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
            success_rate = parsed.notna().mean()
            if success_rate >= (0.9 if strict else 0.7):
                # Full parse on entire series
                result = pd.to_datetime(s.astype(str), format=fmt, errors="coerce")
                if result.notna().mean() >= (0.9 if strict else 0.7):
                    return result, fmt
        except Exception:
            continue
    
    # Fallback: pandas inference (most flexible)
    try:
        parsed = pd.to_datetime(sample, infer_datetime_format=True, errors="coerce")
        success_rate = parsed.notna().mean()
        if success_rate >= (0.85 if strict else 0.7):
            result = pd.to_datetime(s.astype(str), infer_datetime_format=True, errors="coerce")
            if result.notna().mean() >= (0.85 if strict else 0.7):
                return result, "inferred"
    except Exception:
        pass
    
    return None, None


def ensure_datetime(s: pd.Series) -> pd.Series:
    """
    Convert series to datetime, attempting multiple strategies.
    Returns original series if conversion fails.
    """
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    
    parsed, _ = parse_date_column(s, strict=False)
    return parsed if parsed is not None else s


def infer_granularity(dates: pd.Series) -> str:
    """Infer temporal granularity (day, week, month, quarter, year)."""
    try:
        parsed = pd.to_datetime(dates, errors="coerce").dropna()
        if len(parsed) < 2:
            return "day"
        
        sorted_dates = parsed.sort_values()
        diffs = sorted_dates.diff().dropna()
        
        if len(diffs) == 0:
            return "day"
        
        # Get median and min time differences
        median_seconds = diffs.dt.total_seconds().median()
        min_seconds = diffs.dt.total_seconds().min()
        
        # Allow some flexibility around boundaries
        if median_seconds < 86400 * 3:  # Less than 3 days
            if min_seconds < 3600:  # Some diffs < 1 hour
                return "hour"
            return "day"
        elif median_seconds < 86400 * 10:  # Less than 10 days
            return "day"
        elif median_seconds < 86400 * 35:  # Less than 35 days
            return "month"
        elif median_seconds < 86400 * 120:  # Less than 120 days
            return "quarter"
        else:
            return "year"
    except Exception:
        return "day"


def is_temporal(s: pd.Series) -> bool:
    """Check if series represents temporal data."""
    if pd.api.types.is_datetime64_any_dtype(s):
        return True
    
    sample = s.dropna().astype(str).head(30)
    if len(sample) == 0:
        return False
    
    # Try explicit formats first
    for fmt in DATE_FORMATS[:10]:  # Try most likely first
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
            if parsed.notna().mean() >= 0.8:
                return True
        except Exception:
            continue
    
    # Try inference
    try:
        parsed = pd.to_datetime(sample, infer_datetime_format=True, errors="coerce")
        if parsed.notna().mean() >= 0.75:
            return True
    except Exception:
        pass
    
    return False
