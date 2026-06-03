import re
from typing import Tuple, List, Dict
from dateutil import parser
from datetime import datetime
from dateutil.relativedelta import relativedelta

def normalize_query(query: str) -> Tuple[str, List[Dict]]:
    """
    Finds date-like expressions in the query, normalizes them to ISO 8601,
    replaces them in the query, and returns the modified query and extracted dates.
    """
    # Simple regex to catch common date patterns
    # Matches:
    # 24th november 2024, 24/11/2024, 11-24-2024, nov 24 2024, 2024-11-24, november 24th
    # Q3 2024, last month, this year
    
    date_patterns = [
        r'\b(?:last|this|next)\s+(?:month|year|week|quarter)\b',
        r'\bQ[1-4]\s+\d{4}\b',
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(?:of\s+)?\d{4}\b',
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
    ]
    
    extracted = []
    normalized_query = query
    today = datetime.now()

    for pattern in date_patterns:
        matches = re.finditer(pattern, normalized_query, re.IGNORECASE)
        for match in list(matches)[::-1]:  # Reverse to replace without messing up indices
            original = match.group(0)
            is_relative = False
            iso_str = ""
            
            orig_lower = original.lower()
            if "last month" in orig_lower:
                target = today - relativedelta(months=1)
                # ISO range for last month
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
            else:
                try:
                    # Clean up some words like "of" or ordinal suffixes before parsing
                    clean_str = re.sub(r'(?:st|nd|rd|th)', '', original, flags=re.IGNORECASE)
                    clean_str = re.sub(r'\bof\b', '', clean_str, flags=re.IGNORECASE).strip()
                    # Add current year if not present
                    if not re.search(r'\d{4}', clean_str):
                        clean_str += f" {today.year}"
                    
                    parsed_date = parser.parse(clean_str, fuzzy=True)
                    iso_str = parsed_date.strftime('%Y-%m-%d')
                except Exception:
                    continue  # Skip if we can't parse it
            
            extracted.append({
                "original": original,
                "iso": iso_str,
                "is_relative": is_relative
            })
            
            # Replace in query
            start_idx, end_idx = match.span()
            normalized_query = normalized_query[:start_idx] + iso_str + normalized_query[end_idx:]

    return normalized_query, extracted
