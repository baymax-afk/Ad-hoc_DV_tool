from __future__ import annotations

from typing import Optional

import pandas as pd


# Column name hints for geographic data
GEO_HINTS = {
    # Countries
    "country", "nation", "territory",
    # US States
    "state", "province", "region", "district", "county",
    # Cities
    "city", "town", "municipality",
    # Coordinates
    "lat", "latitude", "lon", "longitude", "location",
    # Postal
    "zipcode", "zip", "zip_code", "postal", "postal_code",
    # Geographic codes
    "iso", "iso_code", "iso3", "fips", "geoid", "geoname_id",
    # General
    "geography", "geo", "continent", "area",
}

# Common country names and ISO codes
COUNTRY_CODES = {
    "us": "USA", "usa": "USA", "united states": "USA", "us a": "USA", "america": "USA", "american": "USA",
    "uk": "GBR", "gb": "GBR", "great britain": "GBR", "united kingdom": "GBR",
    "de": "DEU", "germany": "DEU", "deutschland": "DEU",
    "fr": "FRA", "france": "FRA",
    "it": "ITA", "italy": "ITA",
    "es": "ESP", "spain": "ESP", "españa": "ESP",
    "nl": "NLD", "netherlands": "NLD",
    "be": "BEL", "belgium": "BEL",
    "ch": "CHE", "switzerland": "CHE",
    "se": "SWE", "sweden": "SWE",
    "no": "NOR", "norway": "NOR",
    "dk": "DNK", "denmark": "DNK",
    "fi": "FIN", "finland": "FIN",
    "at": "AUT", "austria": "AUT",
    "pl": "POL", "poland": "POL",
    "cz": "CZE", "czechia": "CZE", "czech republic": "CZE",
    "ca": "CAN", "canada": "CAN",
    "mx": "MEX", "mexico": "MEX",
    "br": "BRA", "brazil": "BRA",
    "ar": "ARG", "argentina": "ARG",
    "cl": "CHL", "chile": "CHL",
    "au": "AUS", "australia": "AUS",
    "jp": "JPN", "japan": "JPN",
    "cn": "CHN", "china": "CHN",
    "in": "IND", "india": "IND",
    "kr": "KOR", "south korea": "KOR",
}


US_STATES = {
    "al", "alabama", "ak", "alaska", "az", "arizona", "ar", "arkansas",
    "ca", "california", "co", "colorado", "ct", "connecticut", "de", "delaware",
    "fl", "florida", "ga", "georgia", "hi", "hawaii", "id", "idaho",
    "il", "illinois", "in", "indiana", "ia", "iowa", "ks", "kansas",
    "ky", "kentucky", "la", "louisiana", "me", "maine", "md", "maryland",
    "ma", "massachusetts", "mi", "michigan", "mn", "minnesota", "ms", "mississippi",
    "mo", "missouri", "mt", "montana", "ne", "nebraska", "nv", "nevada",
    "nh", "new hampshire", "nj", "new jersey", "nm", "new mexico", "ny", "new york",
    "nc", "north carolina", "nd", "north dakota", "oh", "ohio", "ok", "oklahoma",
    "or", "oregon", "pa", "pennsylvania", "ri", "rhode island", "sc", "south carolina",
    "sd", "south dakota", "tn", "tennessee", "tx", "texas", "ut", "utah",
    "vt", "vermont", "va", "virginia", "wa", "washington", "wv", "west virginia",
    "wi", "wisconsin", "wy", "wyoming", "dc", "district of columbia",
}


def is_geographic_hint(col_name: str) -> bool:
    col_lower = col_name.lower().replace("_", " ").replace("-", " ")
    words = set(col_lower.split())
    return bool(words & GEO_HINTS)


def validate_latitude(s: pd.Series) -> bool:
    try:
        numeric = pd.to_numeric(s.dropna(), errors="coerce")
        return bool(((numeric >= -90) & (numeric <= 90)).all())
    except Exception:
        return False


def validate_longitude(s: pd.Series) -> bool:
    try:
        numeric = pd.to_numeric(s.dropna(), errors="coerce")
        return bool(((numeric >= -180) & (numeric <= 180)).all())
    except Exception:
        return False


def is_latitude_column(col_name: str, s: pd.Series) -> bool:
    name_lower = col_name.lower()
    if name_lower in {"lat", "latitude", "y"}:
        return validate_latitude(s)
    return False


def is_longitude_column(col_name: str, s: pd.Series) -> bool:
    name_lower = col_name.lower()
    if name_lower in {"lon", "longitude", "long", "x"}:
        return validate_longitude(s)
    return False


def is_country_column(s: pd.Series) -> bool:
    sample = s.dropna().astype(str).head(20)
    if len(sample) == 0:
        return False
    
    # Check for common country patterns
    sample_lower = sample.str.lower()
    
    # Check for full country names or common abbreviations
    country_matches = sample_lower.isin(list(COUNTRY_CODES.keys())).sum()
    if country_matches / len(sample) >= 0.5:
        return True
    
    # Check for ISO3 codes (3 uppercase letters)
    iso3_matches = sample.str.match(r"^[A-Z]{3}$").sum()
    if iso3_matches / len(sample) >= 0.6:
        return True
    
    # Check for ISO2 codes (2 uppercase letters)
    iso2_matches = sample.str.match(r"^[A-Z]{2}$").sum()
    if iso2_matches / len(sample) >= 0.6:
        return True
    
    return False


def is_state_column(s: pd.Series) -> bool:
    sample = s.dropna().astype(str).head(20)
    if len(sample) == 0:
        return False
    
    sample_lower = sample.str.lower()
    state_matches = sample_lower.isin(US_STATES).sum()
    
    return state_matches / len(sample) >= 0.5


def detect_geo_type(col_name: str, s: pd.Series) -> Optional[str]:
    if is_latitude_column(col_name, s):
        return "latitude"
    if is_longitude_column(col_name, s):
        return "longitude"
    if is_country_column(s):
        return "country"
    if is_state_column(s):
        return "state"
    return None


def suggest_geographic_chart(geo_types: dict[str, str]) -> Optional[str]:
    types = set(geo_types.values())
    
    # Lat/lon pair → scatter geo
    if "latitude" in types and "longitude" in types:
        return "scatter_geo"
    
    # Only latitude or longitude → not useful for maps
    if "latitude" in types or "longitude" in types:
        return None
    
    # Country data → choropleth
    if "country" in types:
        return "choropleth"
    
    # State data → state choropleth
    if "state" in types:
        return "state_choropleth"
    
    return None
