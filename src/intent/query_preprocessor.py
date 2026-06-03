import re
from typing import Tuple, List, Dict
import dateparser
from dateparser.search import search_dates
from datetime import datetime
from dateutil.relativedelta import relativedelta

def normalize_query(query: str) -> Tuple[str, List[Dict]]:
    """
    Finds date-like expressions in the query, normalizes them to ISO 8601,
    replaces them in the query, and returns the modified query and extracted dates.
    """
    extracted = []
    normalized_query = query
    today = datetime.now()

    # 1. Custom handling for ranges like "last month", "this year", "Q3 2024"
    # because dateparser converts them to a single point in time, not a range.
    date_patterns = [
        r'\b(?:last|this|next)\s+(?:month|year|week|quarter)\b',
        r'\bQ[1-4]\s+\d{4}\b',
    ]

    for pattern in date_patterns:
        matches = re.finditer(pattern, normalized_query, re.IGNORECASE)
        for match in list(matches)[::-1]:
            original = match.group(0)
            is_relative = False
            iso_str = ""
            orig_lower = original.lower()
            
            if "last month" in orig_lower:
                target = today - relativedelta(months=1)
                start = target.replace(day=1)
                next_month = target + relativedelta(months=1)
                end = next_month.replace(day=1) - relativedelta(days=1)
                iso_str = f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                is_relative = True
            elif "this year" in orig_lower:
                start = today.replace(month=1, day=1)
                end = today.replace(month=12, day=31)
                iso_str = f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                is_relative = True
            elif re.match(r'^q([1-4])\s+(\d{4})$', orig_lower):
                m = re.match(r'^q([1-4])\s+(\d{4})$', orig_lower)
                quarter = int(m.group(1))
                year = int(m.group(2))
                start_month = 3 * quarter - 2
                start = datetime(year, start_month, 1)
                end = start + relativedelta(months=3) - relativedelta(days=1)
                iso_str = f"{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
                is_relative = False
                
            if iso_str:
                extracted.append({
                    "original": original,
                    "iso": iso_str,
                    "is_relative": is_relative
                })
                start_idx, end_idx = match.span()
                normalized_query = normalized_query[:start_idx] + iso_str + normalized_query[end_idx:]

    # 2. Use dateparser.search.search_dates for robust natural language extraction
    found_dates = search_dates(normalized_query, settings={'STRICT_PARSING': False, 'PREFER_DATES_FROM': 'past'})
    if found_dates:
        for text, dt in found_dates:
            # Avoid replacing tiny fragments that might just be numbers, like "1", "May" etc if they are too generic.
            if len(text) < 4 and text.lower() not in ['now', 'today', 'tdy', 'yes', 'yda', 'yest']:
                continue
                
            iso_str = dt.strftime('%Y-%m-%d')
            extracted.append({
                "original": text,
                "iso": iso_str,
                "is_relative": False
            })
            normalized_query = normalized_query.replace(text, iso_str)

    return normalized_query, extracted
