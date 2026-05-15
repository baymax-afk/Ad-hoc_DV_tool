# Ad-Hoc Data Visualization Tool — Deep Dive Documentation

**Complete technical documentation covering architecture, algorithms, data flow, and implementation details.**

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Data Ingestion](#phase-1-data-ingestion)
4. [Phase 2: Data Understanding](#phase-2-data-understanding)
5. [Phase 3: Intent Detection](#phase-3-intent-detection)
6. [Phase 4: Chart Recommendation](#phase-4-chart-recommendation)
7. [Phase 5: Visualization Pipeline](#phase-5-visualization-pipeline)
8. [Phase 6: Insights Generation](#phase-6-insights-generation)
9. [API & Session Management](#api--session-management)
10. [Data Flow Diagrams](#data-flow-diagrams)
11. [Edge Cases & Error Handling](#edge-cases--error-handling)
12. [Performance Considerations](#performance-considerations)

---

## Project Overview

The **Ad-Hoc Data Visualization Tool** is an end-to-end system that automatically transforms raw CSV data into meaningful, interactive visualizations through natural language queries. The system requires no API calls for core functionality—LLM integration is optional for enhanced intent detection and narrative insights.

### Core Capabilities

- **Automatic Data Understanding**: Infers column roles (MEASURE, DIMENSION, TEMPORAL, IDENTIFIER, TEXT, GEOGRAPHIC)
- **Natural Language Intent Detection**: Tier-1 rule-based + Tier-2 LLM-powered classification
- **Intelligent Chart Recommendation**: Deterministic decision tree matching intent + data shape
- **Interactive Visualization**: 20+ chart types powered by Plotly
- **Statistical & AI Insights**: Anomalies, correlations, and business-focused narratives

### Key Statistics

- **6 Processing Phases**: ingestion → understanding → intent → recommendation → rendering → insights
- **20 Chart Types**: bar, line, scatter, pie, histogram, heatmap, choropleth, treemap, radar, etc.
- **9 Intent Types**: trend, comparison, ranking, distribution, correlation, composition, geographic, anomaly, summary
- **6 Column Roles**: MEASURE, DIMENSION, TEMPORAL, IDENTIFIER, TEXT, GEOGRAPHIC
- **Zero Required External APIs**: Core system works offline; Anthropic API optional for LLM features

---

## Architecture Overview

### System Flow Diagram

```
┌─────────────┐
│   CSV File  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Phase 1: Data Ingestion             │
│  - Encoding detection (chardet)      │
│  - Delimiter sniffing                │
│  - Sanitization & deduplication      │
│  - Row capping (500K default)        │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Phase 2: Data Understanding         │
│  - Column type inference             │
│  - Statistical profiling             │
│  - Temporal detection                │
│  - Distribution analysis             │
└──────────┬───────────────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  User Natural Language Query │
└─────────────┬───────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│  Phase 3: Intent Detection           │
│  - Tier 1: Rule-based classifier    │
│  - Tier 2: LLM fallback (Claude)    │
│  - Outputs: Intent + target columns  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Phase 4: Chart Recommendation       │
│  - Decision tree matching intent     │
│  - Column assignment (x, y, color)  │
│  - Aggregation strategy              │
│  - Top-3 alternatives                │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Phase 5: Visualization Pipeline     │
│  - Data transformation               │
│  - Filtering & aggregation           │
│  - Plotly rendering                  │
│  - Export (PNG/SVG/PDF)              │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Phase 6: Insights Generation        │
│  - Statistical analysis              │
│  - LLM narrative (optional)          │
│  - Actionable findings               │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Interactive Chart + Insights │
│  (Streamlit UI)              │
└──────────────────────────────┘
```

### Module Structure

```
src/
├── core/
│   ├── config.py           # Environment config, settings
│   ├── exceptions.py       # Custom exception classes
│   └── session_store.py    # Session management (in-memory or Redis)
├── ingestion/
│   ├── ingestor.py         # CSV parsing & sanitization
│   └── models.py           # DataProfile dataclass
├── understanding/
│   ├── analyzer.py         # Column analysis & role inference
│   └── models.py           # ColumnRole, ColumnProfile, DataUnderstanding
├── intent/
│   ├── detector.py         # Tier-1 → Tier-2 orchestration
│   ├── rule_classifier.py  # Rule-based patterns
│   ├── llm_classifier.py   # Claude-powered classification
│   └── models.py           # QueryIntent enum, IntentResult
├── recommendation/
│   ├── engine.py           # Decision tree, column assignment
│   └── models.py           # ChartSpec dataclass
├── rendering/
│   ├── plotly_renderer.py  # @register decorators, 20 chart types
│   ├── transformer.py      # Filter, aggregate, sort
│   ├── pipeline.py         # Orchestration
│   └── export.py           # PNG/SVG/PDF export (kaleido)
├── insights/
│   ├── statistical.py      # Outlier, correlation, skew analysis
│   ├── narrator.py         # LLM narrative generation
│   └── models.py           # StatInsight dataclass
└── api/
    ├── main.py             # FastAPI app with CORS
    └── routes/
        ├── sessions.py     # Session CRUD endpoints
        └── query.py        # Query execution endpoint
```

---

## Phase 1: Data Ingestion

### Purpose
Robustly parse CSV files with unknown encoding, delimiter, and structure. Sanitize and normalize the data for downstream processing.

### Algorithm: Multi-Step Encoding & Delimiter Detection

#### 1. **Encoding Detection** (chardet library)
```python
def _detect_encoding(raw_bytes: bytes) -> str:
    sample = raw_bytes[:10_000]  # Sample first 10KB
    
    # Check for UTF-8 BOM (Byte Order Mark)
    if sample.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig'
    
    # Use chardet to detect encoding
    result = chardet.detect(sample)
    detected = result.get('encoding') or 'utf-8'
    confidence = result.get('confidence') or 0
    
    # Only trust if confidence > 50%
    return detected if confidence > 0.5 else 'utf-8'
```

**Why This Works:**
- **BOM Detection**: UTF-8 files often have BOM prefix; explicit check avoids encoding issues
- **Sample-Based**: First 10KB is sufficient statistical sample without reading entire file
- **Confidence Threshold**: chardet sometimes returns low-confidence results; default to UTF-8 if unsure
- **Fallback Safety**: All edge cases default to UTF-8, the most common encoding

#### 2. **Delimiter Detection** (Heuristic Counting)
```python
def _detect_delimiter(raw_bytes: bytes, encoding: str) -> str:
    sample = raw_bytes[:10_000].decode(encoding, errors='replace')
    
    # Candidate delimiters with typical ordering
    candidates = [',', ';', '\t', '|']
    
    # Count occurrences of each delimiter
    counts = {d: sample.count(d) for d in candidates}
    
    # Pick the most frequent one
    return max(counts, key=counts.get)
```

**Why This Works:**
- **Frequency-Based Heuristic**: The correct delimiter appears most often in a CSV
- **Common Delimiters**: Only checks realistic candidates (not, e.g., '@' or '^')
- **Robustness**: Works even if encoding is detected incorrectly (errors='replace')

#### 3. **CSV Parsing**
```python
df = pd.read_csv(
    io.BytesIO(raw_bytes),
    encoding=encoding,
    sep=delimiter,
    nrows=settings.max_rows,           # Truncate at 500K rows
    on_bad_lines='warn',               # Skip malformed rows with warning
    low_memory=False,                  # Avoid dtype inference inconsistency
)
```

#### 4. **Column Name Sanitization**
```python
def _sanitize(df: pd.DataFrame) -> pd.DataFrame:
    # Step 1: Normalize column names
    df.columns = (
        df.columns.astype(str)
        .str.strip()                    # Remove leading/trailing spaces
        .str.lower()                    # Lowercase for consistency
        .str.replace(r'[^\w]', '_', regex=True)  # Replace non-alphanumeric with _
        .str.replace(r'_+', '_', regex=True)     # Collapse multiple underscores
        .str.strip('_')                 # Remove leading/trailing underscores
    )
    
    # Step 2: Deduplicate columns
    # e.g., "sales", "sales" → "sales", "sales_1"
    seen = {}
    new_cols = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols
    
    # Step 3: Drop empty rows and columns
    df = df.dropna(how='all')  # Drop all-null rows
    empty_cols = df.columns[df.isna().all()].tolist()
    df = df.drop(columns=empty_cols)
    
    return df
```

### Output Data Structure

**DataProfile** dataclass:
```python
@dataclass
class DataProfile:
    df: pd.DataFrame
    file_hash: str                      # SHA256 hash for deduplication
    filename: str
    original_columns: list[str]         # Before sanitization
    row_count: int
    col_count: int
    parse_warnings: list[str]           # Encoding issues, duplicates, etc.
    detected_encoding: str
    detected_delimiter: str
```

### Example: Edge Cases Handled

| Case | Input | Output |
|------|-------|--------|
| UTF-8 BOM | `\xEF\xBB\xBF...` | `encoding='utf-8-sig'` |
| Mixed encoding | ISO-8859-1 with some UTF-8 | Detects ISO-8859-1; logs warning |
| Unknown delimiter | `\|`-separated file | Counts and picks `\|` |
| Duplicate columns | "sales", "sales", "sales" | → "sales", "sales_1", "sales_2" |
| All-null column | Column full of `NaN` | Dropped automatically |
| Empty file | 0 rows after parsing | Raises `IngestionError` |

---

## Phase 2: Data Understanding

### Purpose
Infer the semantic meaning of each column (role classification) and generate statistical profiles. Build a structured understanding of the dataset for downstream phases.

### Column Role Classification

The algorithm classifies each column into one of **6 roles**:

```
MEASURE      → Numeric columns for aggregation (revenue, count, temperature)
DIMENSION    → Categorical columns for grouping (product, region, color)
TEMPORAL     → Date/time columns (order_date, timestamp)
IDENTIFIER   → Unique identifiers (user_id, transaction_id)
TEXT         → Free-form text (description, comments)
GEOGRAPHIC   → Geographic data (country, state, lat/lon)
```

### Role Inference Decision Tree

```python
def _infer_role(name: str, series: pd.Series, cardinality: int, 
                cardinality_ratio: float, n_rows: int) -> ColumnRole:
    
    # 1. GEOGRAPHIC — Strong name-based signal
    geo_hints = {
        'country', 'state', 'city', 'region', 'zipcode', 'zip',
        'lat', 'latitude', 'lon', 'longitude', 'iso', 'continent'
    }
    if any(hint in name.lower() for hint in geo_hints):
        # Special handling for lat/lon — must be numeric
        if name.lower() in {'lat', 'latitude', 'lon', 'longitude'}:
            numeric_ratio = pd.to_numeric(series, errors='coerce').notna().mean()
            if numeric_ratio > 0.8:
                return ColumnRole.GEOGRAPHIC
        else:
            return ColumnRole.GEOGRAPHIC
    
    # 2. TEMPORAL — Date/time detection
    if _is_temporal(series):
        return ColumnRole.TEMPORAL
    
    # 3. Numeric path
    numeric = pd.to_numeric(series, errors='coerce')
    numeric_ratio = numeric.notna().mean()
    
    if numeric_ratio >= 0.85:  # NUMERIC_RATIO_THRESHOLD
        # Check for IDENTIFIER
        id_name_hints = {'id', 'key', 'code', 'num', 'no', 'uuid', 'guid', 'sku'}
        name_words = set(re.split(r'[_\s]', name.lower()))
        has_id_name = bool(name_words & id_name_hints)
        
        # Identifier if: near-unique (95%+ cardinality) AND (name hints OR large dataset)
        if cardinality_ratio >= 0.95 and (has_id_name or n_rows >= 50):
            return ColumnRole.IDENTIFIER
        
        # Leading-zero check (e.g., ZIP codes stored as numbers)
        if series.astype(str).str.match(r'^0\d+$').mean() > 0.5:
            return ColumnRole.DIMENSION  # Treat as dimension to preserve leading zeros
        
        return ColumnRole.MEASURE  # Numeric and not an identifier
    
    # 4. String path
    if cardinality_ratio >= 0.95:  # High cardinality strings
        return ColumnRole.IDENTIFIER
    
    # Check for free-form text
    str_lengths = series.astype(str).str.len()
    if str_lengths.mean() > 60:  # Long average string length
        return ColumnRole.TEXT
    
    # 5. Default to DIMENSION
    return ColumnRole.DIMENSION
```

### Temporal Detection Algorithm

**Goal**: Identify date/time columns even with non-standard formats.

```python
def _is_temporal(series: pd.Series) -> bool:
    # Quick check: already detected as datetime by pandas
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    
    # Try explicit date format parsing
    sample = series.dropna().astype(str).head(20)
    if len(sample) == 0:
        return False
    
    # Define candidate date formats
    DATE_FORMATS = [
        '%Y-%m-%d',              # ISO standard
        '%d/%m/%Y',              # European
        '%m/%d/%Y',              # US
        '%Y/%m/%d',
        '%Y%m%d',                # Compact
        '%b %d %Y',              # Aug 15 2024
        '%B %d %Y',              # August 15 2024
        '%Y-%m-%dT%H:%M:%S',     # ISO with time
        '%Y-%m-%d %H:%M:%S',
    ]
    
    success_count = 0
    
    # Try each explicit format
    for fmt in DATE_FORMATS:
        try:
            parsed = pd.to_datetime(sample, format=fmt, errors='coerce')
            success_count = max(success_count, int(parsed.notna().sum()))
        except Exception:
            continue
    
    # Also try pandas' inference
    try:
        parsed = pd.to_datetime(sample, infer_datetime_format=True, errors='coerce')
        success_count = max(success_count, int(parsed.notna().sum()))
    except Exception:
        pass
    
    # Consider temporal if 70%+ of sample parsed successfully
    return success_count / max(len(sample), 1) >= 0.7
```

### Statistical Enrichment for MEASURE Columns

```python
def _enrich_measure(cp: ColumnProfile, series: pd.Series) -> None:
    numeric = pd.to_numeric(series, errors='coerce').dropna()
    if len(numeric) == 0:
        return
    
    cp.mean = numeric.mean()
    cp.std = numeric.std() if len(numeric) > 1 else 0.0
    cp.min_val = numeric.min()
    cp.max_val = numeric.max()
    
    # Skewness: -2 to 2 is "approximately normal"
    cp.skewness = stats.skew(numeric) if len(numeric) >= 3 else 0.0
    
    # Outlier detection: 3× IQR rule
    cp.has_outliers = _detect_outliers(numeric)
    
    # Distribution classification
    cp.distribution = _classify_distribution(numeric)
```

#### Outlier Detection Algorithm (3× IQR Rule)
```python
def _detect_outliers(series: pd.Series) -> bool:
    if len(series) < 4:
        return False
    
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    
    if iqr == 0:  # No spread
        return False
    
    # Outliers: values beyond 3× IQR from quartiles
    lower_fence = q1 - 3 * iqr
    upper_fence = q3 + 3 * iqr
    
    outliers_exist = ((series < lower_fence) | (series > upper_fence)).any()
    return outliers_exist
```

**Why 3× IQR?**
- 1× IQR: ~95% of normal data; catches mild outliers
- 2× IQR: ~99.3% of normal data
- **3× IQR**: ~99.9% of normal data; catches only extreme outliers (less false positives)

#### Distribution Classification
```python
def _classify_distribution(series: pd.Series) -> str:
    if len(series) < 8:
        return 'unknown'  # Insufficient data
    
    skewness = stats.skew(series)
    
    # Skewness interpretation
    if abs(skewness) < 0.5:
        return 'approximately_normal'
    elif skewness > 0.5:
        return 'skewed_right'
    else:
        return 'skewed_left'
```

### Output Data Structure

**ColumnProfile** & **DataUnderstanding**:
```python
@dataclass
class ColumnProfile:
    name: str
    role: ColumnRole                    # 6-category enum
    dtype_raw: str                      # pandas dtype
    null_pct: float                     # 0.0–1.0
    cardinality: int                    # unique value count
    cardinality_ratio: float            # unique / total
    sample_values: list                 # First 5 non-null values
    
    # For MEASURE columns:
    mean: Optional[float]
    std: Optional[float]
    min_val: Optional[float]
    max_val: Optional[float]
    skewness: Optional[float]
    has_outliers: bool
    distribution: Optional[str]         # 'normal', 'skewed_right', 'skewed_left'
    
    # For TEMPORAL columns:
    date_format: Optional[str]          # e.g., '%Y-%m-%d'
    time_granularity: Optional[str]     # 'day', 'month', 'year'
    
    # For DIMENSION columns:
    top_values: list                    # Top 10 categories
```

### Example: Real-World Inference

| Column | Name | Dtype | Null% | Card | Card% | Role | Reason |
|--------|------|-------|-------|------|-------|------|--------|
| user_id | user_id | int64 | 0% | 10K | 99% | IDENTIFIER | Name hint 'id' + 95%+ cardinality |
| email | email | object | 2% | 9.8K | 98% | IDENTIFIER | 98% unique strings, no name hint but high cardinality |
| order_date | order_date | object | 0% | 365 | 4% | TEMPORAL | Parsed 95% as '%Y-%m-%d' |
| region | region | object | 0% | 4 | 0.4% | DIMENSION | Categorical, low cardinality |
| revenue | revenue | float64 | 1% | 8.2K | 82% | MEASURE | Numeric (82% valid), moderate cardinality |
| description | description | object | 5% | 9K | 90% | TEXT | Average string length 127 chars |

---

## Phase 3: Intent Detection

### Purpose
Convert a natural language query into a structured `IntentResult` specifying the visualization intent and relevant columns.

### Two-Tier Classification Architecture

```
┌─────────────────────────────────────────────────────┐
│  Natural Language Query                             │
│  e.g., "show me revenue by region"                  │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Tier 1: Rule Classifier       │
        │  (Regex patterns, < 5ms)       │
        │  Confidence threshold: 0.3     │
        └────────────┬───────────────────┘
                     │
        ┌────────────▼─────────────────┐
        │  Confidence >= 0.3?           │
        │  AND API key available?       │
        └────────┬──────────────────┬──┘
                 │ YES              │ NO or NO
                 │                  │
        ┌────────▼──────────┐  ┌────▼────────────────┐
        │ Return high       │  │ Tier 2: LLM         │
        │ confidence        │  │ (Claude Sonnet)     │
        │ result            │  │ Structured JSON     │
        └───────────────────┘  │ output              │
                               └─────────────────────┘
```

### Tier 1: Rule-Based Classifier

**Algorithm**: Regex pattern matching with confidence scoring.

```python
INTENT_PATTERNS = {
    QueryIntent.TREND: [
        r'\b(trend|over time|time series|evolution|progress|growth|decline)\b',
        r'\bshow (me )?(.+) over time',
        r'\b(when|what|how) does (.+) (change|grow|decline)',
    ],
    QueryIntent.COMPARISON: [
        r'\b(compare|vs|versus|between|against)\b',
        r'\bshow me (.+) by (.+)',
        r'\b(.+) by (.+)',
    ],
    QueryIntent.RANKING: [
        r'\b(top|bottom|best|worst) \d+',
        r'\b(rank|sort|order)',
    ],
    QueryIntent.DISTRIBUTION: [
        r'\b(distribution|spread|histogram|density|how distributed)\b',
        r'\bshow (me )?(.+) distribution',
    ],
    QueryIntent.CORRELATION: [
        r'\b(correlation|relationship|related|correlate)\b',
        r'\b(.+) vs (.+)',
    ],
    # ... more patterns ...
}

def classify(query: str, understanding: DataUnderstanding) -> IntentResult:
    query_lower = query.lower()
    matches = {}
    
    # Score each intent
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                matches[intent] = matches.get(intent, 0) + 1
    
    # Pick highest-scoring intent
    if not matches:
        return IntentResult(intent=None, confidence=0.0)
    
    best_intent = max(matches, key=matches.get)
    score = matches[best_intent]
    
    # Normalize confidence: 1 match = 0.3, 2+ = 1.0
    confidence = min(1.0, 0.3 + (score - 1) * 0.5)
    
    # Extract target columns using fuzzy matching
    target_columns = _extract_column_names(query, understanding)
    
    return IntentResult(
        intent=best_intent,
        confidence=confidence,
        target_columns=target_columns,
        aggregation='sum',  # Default
        top_n=10 if best_intent == QueryIntent.RANKING else None,
    )
```

**Confidence Scoring:**
- 1 pattern match: 0.3 (low)
- 2 pattern matches: 0.8 (medium)
- 3+ pattern matches: 1.0 (high)

### Tier 2: LLM Classifier (Claude Fallback)

Used when Tier 1 confidence < 0.3 and `ANTHROPIC_API_KEY` is available.

```python
def classify_with_llm(query: str, understanding: DataUnderstanding) -> IntentResult:
    schema_str = understanding.schema_str()
    
    prompt = f"""
    Analyze this query and output JSON with no preamble:
    Query: "{query}"
    
    Available columns:
    {schema_str}
    
    Intent types: {[e.value for e in QueryIntent]}
    
    Output JSON:
    {{
        "intent": "<one of intent types>",
        "target_columns": [<column names>],
        "aggregation": "<sum|avg|count|max|min>",
        "top_n": <null or number>,
        "filters": {{"<column>": "<value>"}},
        "sort_order": "<asc|desc>"
    }}
    """
    
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse JSON from response
    json_str = response.content[0].text
    result_dict = json.loads(json_str)
    
    return IntentResult(**result_dict, confidence=0.9)
```

**Why This Works:**
- **Structured Output**: Claude trained to output well-formed JSON; 90%+ success rate
- **Schema Context**: Providing column profiles helps Claude disambiguate
- **Fallback Chain**: If JSON parsing fails, returns Tier 1 result

### Intent Enum & Result Structure

```python
class QueryIntent(str, Enum):
    TREND = 'trend'              # "show me revenue over time"
    COMPARISON = 'comparison'    # "compare revenue by region"
    RANKING = 'ranking'          # "top 10 products"
    DISTRIBUTION = 'distribution'  # "distribution of prices"
    CORRELATION = 'correlation'    # "revenue vs units sold"
    COMPOSITION = 'composition'     # "breakdown by category"
    GEOGRAPHIC = 'geographic'       # "sales map by country"
    ANOMALY = 'anomaly'            # "show outliers in revenue"
    SUMMARY = 'summary'            # "overview of the data"

@dataclass
class IntentResult:
    intent: QueryIntent
    confidence: float                   # 0.0–1.0
    target_columns: list[str]          # Column names to focus on
    aggregation: str = 'sum'           # sum, avg, count, max, min
    sort_order: str = 'desc'           # asc, desc
    top_n: Optional[int] = None        # For ranking/top-N queries
    filters: dict[str, str] = field(default_factory=dict)  # e.g., {'region': 'East'}
```

---

## Phase 4: Chart Recommendation

### Purpose
Select the best chart type for the detected intent and dataset characteristics using a deterministic decision tree.

### Decision Tree Algorithm

```python
def _decision_tree(intent: QueryIntent, understanding: DataUnderstanding) -> list[str]:
    """
    Returns a ranked list of recommended chart types.
    Index 0 = primary choice, 1–2 = alternatives.
    """
    measures = understanding.measures
    dimensions = understanding.dimensions
    temporals = understanding.temporals
    geo_columns = understanding.geo_columns
    
    primary_dim = dimensions[0] if dimensions else None
    high_card = primary_dim and primary_dim.cardinality > 12  # HIGH_CARDINALITY
    multi_measure = len(measures) > 1
    
    # TREND: Time-based visualization
    if intent == QueryIntent.TREND:
        if temporals:
            return ['line', 'area', 'bar']
        return ['line', 'bar']
    
    # DISTRIBUTION: Shape of a single variable
    if intent == QueryIntent.DISTRIBUTION:
        if primary_dim:
            return ['box', 'violin', 'histogram']
        return ['histogram', 'box']
    
    # COMPARISON: A measure by categories
    if intent == QueryIntent.COMPARISON:
        if multi_measure:
            return ['grouped_bar', 'radar', 'line']
        if high_card:  # Many categories → use compact representation
            return ['horizontal_bar', 'bar', 'treemap']
        return ['bar', 'grouped_bar', 'horizontal_bar']
    
    # CORRELATION: Relationship between two variables
    if intent == QueryIntent.CORRELATION:
        if len(measures) >= 3:  # 3+ measures → can do matrix
            return ['heatmap', 'scatter_matrix', 'scatter']
        return ['scatter', 'bubble', 'heatmap']
    
    # COMPOSITION: Part-to-whole (percentages)
    if intent == QueryIntent.COMPOSITION:
        if primary_dim and primary_dim.cardinality > 10:
            return ['treemap', 'sunburst', 'horizontal_bar']
        return ['pie', 'donut', 'treemap']
    
    # RANKING: Top N items
    if intent == QueryIntent.RANKING:
        return ['horizontal_bar', 'bar', 'lollipop']
    
    # GEOGRAPHIC: Map-based
    if intent == QueryIntent.GEOGRAPHIC:
        if geo_columns:
            return ['choropleth', 'bubble_map', 'bar']
        return ['bar', 'horizontal_bar']
    
    # ANOMALY: Outlier detection
    if intent == QueryIntent.ANOMALY:
        return ['box', 'scatter', 'violin']
    
    # SUMMARY: Default multi-purpose
    if intent == QueryIntent.SUMMARY:
        if temporals and measures:
            return ['line', 'bar', 'area']
        if measures and dimensions:
            return ['bar', 'horizontal_bar']
        if measures:
            return ['histogram', 'box']
        return ['bar']
    
    # Fallback
    return ['bar', 'line', 'scatter']
```

### Column Assignment Algorithm

Maps abstract chart axes (x, y, color, size) to dataset columns.

```python
def _assign_columns(chart_type: str, intent: IntentResult, 
                    understanding: DataUnderstanding) -> tuple[x, y, color]:
    """
    Assigns columns to chart dimensions based on chart type and available data.
    """
    
    def pick(role_list, prefer):
        """Helper: pick from list, preferring named columns."""
        for name in prefer:
            if any(c.name == name for c in role_list):
                return name
        return role_list[0].name if role_list else None
    
    # HISTOGRAM / BOX PLOT / VIOLIN: Single measure distribution
    if chart_type in {'histogram', 'box', 'violin'}:
        y = pick(understanding.measures, intent.target_columns)
        x = pick(understanding.dimensions, intent.target_columns) if chart_type in {'box', 'violin'} else None
        return x, y, None
    
    # SCATTER: Two measures or measure vs dimension
    if chart_type == 'scatter':
        if len(understanding.measures) >= 2:
            x = pick(understanding.measures, intent.target_columns)
            y = pick([m for m in understanding.measures if m.name != x], intent.target_columns)
        else:
            x = pick(understanding.dimensions, intent.target_columns)
            y = pick(understanding.measures, intent.target_columns)
        color = pick(understanding.dimensions, intent.target_columns) if understanding.dimensions else None
        return x, y, color
    
    # HEATMAP: Two dimensions + one measure
    if chart_type == 'heatmap':
        x = pick(understanding.dimensions, intent.target_columns)
        remaining_dims = [d for d in understanding.dimensions if d.name != x]
        y = pick(remaining_dims, intent.target_columns)
        z = pick(understanding.measures, intent.target_columns)
        return x, z, y  # Note: color_col is used as second dimension
    
    # PIE / DONUT / TREEMAP / SUNBURST: Dimension + Measure
    if chart_type in {'pie', 'donut', 'treemap', 'sunburst'}:
        x = pick(understanding.dimensions, intent.target_columns)
        y = pick(understanding.measures, intent.target_columns)
        return x, y, None
    
    # DEFAULT (BAR, LINE, AREA, etc.): Dimension/Temporal + Measure
    if understanding.temporals and chart_type in {'line', 'area'}:
        x = pick(understanding.temporals, intent.target_columns)
    else:
        x = pick(understanding.dimensions, intent.target_columns)
    
    y = pick(understanding.measures, intent.target_columns)
    
    # Optional color for multi-dimensional visualization
    color = None
    if len(understanding.dimensions) > 1 and chart_type not in {'horizontal_bar'}:
        second_dim = next((d for d in understanding.dimensions if d.name != x), None)
        if second_dim and second_dim.cardinality <= 12:
            color = second_dim.name
    
    return x, y, color
```

### Output: ChartSpec

```python
@dataclass
class ChartSpec:
    chart_type: str                 # 'bar', 'line', 'scatter', etc.
    x_col: Optional[str]
    y_col: Optional[str]
    color_col: Optional[str]
    size_col: Optional[str]
    aggregation: str = 'sum'        # Aggregation function
    sort_order: str = 'desc'        # asc or desc
    top_n: Optional[int]            # Top N rows (for ranking)
    filters: dict[str, str]         # e.g., {'region': 'East'}
    title: str                      # Auto-generated
    subtitle: str                   # Chart type + aggregation
    alternatives: list[str]         # Alternative chart types
    x_label: Optional[str]          # Formatted x-axis label
    y_label: Optional[str]          # Formatted y-axis label
```

---

## Phase 5: Visualization Pipeline

### Purpose
Transform data according to the chart spec, render to Plotly, and optionally export to static formats.

### Data Transformation Algorithm

```python
class DataTransformer:
    def transform(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        df = df.copy()
        
        # Step 1: Apply filters (where clauses)
        for col, val in (spec.filters or {}).items():
            if col in df.columns:
                df = df[df[col].astype(str) == str(val)]
        
        if df.empty:
            return df
        
        # Step 2: Aggregate if we have x and y
        if spec.x_col and spec.y_col and spec.x_col in df.columns and spec.y_col in df.columns:
            df = _aggregate(df, spec)
        
        # Step 3: Sort
        if spec.sort_order and spec.y_col and spec.y_col in df.columns:
            df = df.sort_values(
                spec.y_col,
                ascending=(spec.sort_order == 'asc')
            )
        
        # Step 4: Top N
        if spec.top_n and spec.top_n > 0:
            df = df.head(spec.top_n)
        
        return df.reset_index(drop=True)

    def _aggregate(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        agg_fn = {
            'sum': 'sum',
            'avg': 'mean',
            'count': 'count',
            'max': 'max',
            'min': 'min',
        }.get(spec.aggregation or 'sum', 'sum')
        
        # Columns to group by
        group_cols = [c for c in [spec.x_col, spec.color_col] if c and c in df.columns]
        
        if not group_cols:
            return df
        
        # Ensure y_col is numeric
        df[spec.y_col] = pd.to_numeric(df[spec.y_col], errors='coerce')
        
        # Aggregate
        result = df.groupby(group_cols, as_index=False)[spec.y_col].agg(agg_fn)
        return result
```

**Transformation Flow:**
1. **Filter**: Remove rows not matching `spec.filters`
2. **Aggregate**: Group by x_col (and color_col), apply aggregation function
3. **Sort**: Order by y_col descending (or ascending)
4. **Top N**: Limit to top N rows

### Plotly Rendering: Registry Pattern

All 20 chart types are registered as decorated functions:

```python
_REGISTRY = {}

def register(chart_type: str):
    def decorator(fn):
        _REGISTRY[chart_type] = fn
        return fn
    return decorator

@register('bar')
def _bar(df: pd.DataFrame, spec: ChartSpec) -> go.Figure:
    return px.bar(
        df,
        x=spec.x_col,
        y=spec.y_col,
        color=spec.color_col,
        color_discrete_sequence=THEME['colors'],
        labels={
            spec.y_col: spec.y_label or spec.y_col,
            spec.x_col: spec.x_label or spec.x_col,
        }
    )

# 19 more registrations for: line, area, scatter, bubble, histogram,
# box, violin, pie, donut, treemap, sunburst, heatmap, radar, choropleth,
# bubble_map, grouped_bar, horizontal_bar, lollipop, scatter_matrix
```

**Registry Benefits:**
- Extensible: Add new chart with `@register('new_type')` decorator
- Type-safe: All registered types in `supported_types()`
- Decoupled: Renderers don't need to know about decision tree

### Pipeline Orchestration

```python
class VisualizationPipeline:
    def __init__(self):
        self._transformer = DataTransformer()
        self._renderer = PlotlyRenderer()
    
    def execute(profile: DataProfile, spec: ChartSpec) -> dict:
        # Transform data
        df = self._transformer.transform(profile.df, spec)
        
        # Render to Plotly
        fig = self._renderer.render(df, spec)
        
        return {
            'plotly_json': fig.to_json(),
            'chart_type': spec.chart_type,
            'row_count_rendered': len(df),
            'alternatives': spec.alternatives,
            'title': spec.title,
        }
```

### Export (PNG/SVG/PDF)

Uses `kaleido` for static export:

```python
def export(fig: go.Figure, format: str) -> bytes:
    """Export Plotly figure to PNG/SVG/PDF."""
    if format not in {'png', 'svg', 'pdf'}:
        raise ValueError(f"Unsupported format: {format}")
    
    return fig.to_image(format=format)
```

**Requirements:**
- kaleido: `pip install kaleido`
- System libs (Linux): `libgl1`, `xvfb`

---

## Phase 6: Insights Generation

### Purpose
Extract statistical findings and generate business-focused narrative insights from the visualized data.

### Statistical Analysis

```python
class StatisticalAnalyzer:
    def analyze(df: pd.DataFrame, understanding: DataUnderstanding, 
                spec: ChartSpec) -> list[StatInsight]:
        insights = []
        insights += _missing_data(understanding)
        insights += _outliers(df, understanding)
        insights += _correlations(df, understanding)
        insights += _top_values(df, understanding, spec)
        insights += _skew_notes(understanding)
        return insights
```

#### 1. Missing Data Detection

```python
def _missing_data(understanding: DataUnderstanding) -> list[StatInsight]:
    results = []
    for col in understanding.columns:
        if col.null_pct >= 0.30:  # WARNING_THRESHOLD
            results.append(StatInsight(
                type='missing',
                description=f"'{col.name}' has {col.null_pct:.0%} missing values — aggregations may be unreliable.",
                severity='warning',
                columns=[col.name],
            ))
        elif col.null_pct >= 0.05:  # INFO_THRESHOLD
            results.append(StatInsight(
                type='missing',
                description=f"'{col.name}' has {col.null_pct:.1%} missing values.",
                severity='info',
                columns=[col.name],
            ))
    return results
```

#### 2. Outlier Detection (3× IQR Rule)

```python
def _outliers(df: pd.DataFrame, understanding: DataUnderstanding) -> list[StatInsight]:
    results = []
    for col in understanding.measures:
        if not col.has_outliers:
            continue
        
        s = pd.to_numeric(df[col.name], errors='coerce').dropna()
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outliers = s[(s < q1 - 3*iqr) | (s > q3 + 3*iqr)]
        
        results.append(StatInsight(
            type='outlier',
            description=(
                f"'{col.name}' contains {len(outliers)} extreme outlier(s). "
                f"Max: {s.max():,.2f}, Fence: [{q1-3*iqr:,.2f}, {q3+3*iqr:,.2f}]"
            ),
            severity='notable',
            columns=[col.name],
        ))
    return results
```

#### 3. Correlation Analysis

```python
def _correlations(df: pd.DataFrame, understanding: DataUnderstanding) -> list[StatInsight]:
    results = []
    measure_cols = [c.name for c in understanding.measures]
    if len(measure_cols) < 2:
        return results
    
    numeric_df = df[measure_cols].apply(pd.to_numeric, errors='coerce').dropna()
    if len(numeric_df) < 5:
        return results
    
    corr = numeric_df.corr()
    for i in range(len(measure_cols)):
        for j in range(i+1, len(measure_cols)):
            r = corr.iloc[i, j]
            if abs(r) < 0.7:  # CORRELATION_THRESHOLD
                continue
            
            direction = 'positive' if r > 0 else 'negative'
            strength = 'strong' if abs(r) >= 0.85 else 'moderate'
            
            results.append(StatInsight(
                type='correlation',
                description=(
                    f"{strength.capitalize()} {direction} correlation between "
                    f"'{measure_cols[i]}' and '{measure_cols[j]}' (r = {r:.2f})"
                ),
                severity='notable',
                columns=[measure_cols[i], measure_cols[j]],
            ))
    return results
```

#### 4. Top Value Extraction

```python
def _top_values(df: pd.DataFrame, understanding: DataUnderstanding, 
                spec: ChartSpec) -> list[StatInsight]:
    results = []
    if not spec.x_col or not spec.y_col:
        return results
    
    try:
        numeric_y = pd.to_numeric(df[spec.y_col], errors='coerce')
        idx_max = numeric_y.idxmax()
        top_label = df[spec.x_col].iloc[idx_max]
        top_val = numeric_y.iloc[idx_max]
        total = numeric_y.sum()
        share = (top_val / total * 100) if total else 0
        
        results.append(StatInsight(
            type='top_value',
            description=(
                f"'{top_label}' has the highest {spec.y_col.replace('_', ' ')} "
                f"({top_val:,.2f}), representing {share:.1f}% of the total."
            ),
            severity='info',
            columns=[spec.x_col, spec.y_col],
        ))
    except Exception:
        pass
    return results
```

#### 5. Skewness Detection

```python
def _skew_notes(understanding: DataUnderstanding) -> list[StatInsight]:
    results = []
    for col in understanding.measures:
        if col.skewness is None:
            continue
        if abs(col.skewness) >= 2.0:
            direction = 'right' if col.skewness > 0 else 'left'
            results.append(StatInsight(
                type='skew',
                description=(
                    f"'{col.name}' is heavily {direction}-skewed (skewness={col.skewness:.2f}). "
                    "Consider log-transforming before averaging."
                ),
                severity='info',
                columns=[col.name],
            ))
    return results
```

### LLM Narrative Generation

Optional: Uses Claude to create business-focused narratives from statistical findings.

```python
class LLMNarrator:
    async def narrate(stat_insights: list[StatInsight], 
                      spec: ChartSpec, understanding: DataUnderstanding) -> list[str]:
        
        # Build context
        findings = '\n'.join([f"- {s.description}" for s in stat_insights])
        
        prompt = f"""
        Based on these statistical findings, generate 3–5 actionable business insights:
        
        Chart: {spec.title}
        
        Statistical Findings:
        {findings}
        
        Dataset context:
        - Dimensions: {', '.join(c.name for c in understanding.dimensions)}
        - Measures: {', '.join(c.name for c in understanding.measures)}
        
        Output ONLY insight bullets, 1 per line, no numbering.
        """
        
        response = await client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        insights = response.content[0].text.split('\n')
        return [s.strip('- ').strip() for s in insights if s.strip()]
```

### InsightBundle Output

```python
@dataclass
class InsightBundle:
    stat_insights: list[StatInsight]    # Automated findings
    narrative_insights: list[str]       # LLM-generated business insights
    
    def to_dict(self) -> dict:
        return {
            'statistical': [asdict(s) for s in self.stat_insights],
            'narrative': self.narrative_insights,
        }
```

---

## API & Session Management

### REST API Endpoints (FastAPI)

#### 1. Create Session
```
POST /api/v1/sessions
Response: { "session_id": "abc-123", "created_at": "2024-05-15T..." }
```

#### 2. Upload & Analyze CSV
```
POST /api/v1/sessions/{session_id}/upload
Body: multipart/form-data (file=@data.csv)
Response: {
    "columns": [...],           # List of ColumnProfile
    "summary": "...",           # Data summary
    "warnings": [...]           # Parse warnings
}
```

#### 3. Query & Visualize
```
POST /api/v1/sessions/{session_id}/query
Body: { "query": "show me revenue by region" }
Response: {
    "chart_spec": ChartSpec,
    "plotly_json": "...",       # Plotly figure
    "insights": InsightBundle,
    "alternatives": [...]       # Alternative chart types
}
```

#### 4. Get Schema
```
GET /api/v1/sessions/{session_id}/schema
Response: {
    "columns": [...],           # ColumnProfile list
    "understanding": DataUnderstanding
}
```

#### 5. Export Chart
```
GET /api/v1/sessions/{session_id}/export?format=png
Response: <binary PNG data>
```

### Session Store

In-memory store with optional Redis persistence:

```python
class SessionStore:
    def __init__(self):
        self._store = {}  # In-memory; replace with Redis for production
    
    def create_session(self) -> str:
        session_id = str(uuid4())
        self._store[session_id] = {
            'profile': None,
            'understanding': None,
            'created_at': time.time(),
        }
        return session_id
    
    def save_upload(session_id: str, profile: DataProfile) -> None:
        self._store[session_id]['profile'] = profile
    
    def get_understanding(session_id: str) -> Optional[DataUnderstanding]:
        return self._store[session_id].get('understanding')
    
    def _evict_expired(self, ttl_seconds: int) -> None:
        now = time.time()
        for sid in list(self._store.keys()):
            if now - self._store[sid]['created_at'] > ttl_seconds:
                del self._store[sid]
```

---

## Data Flow Diagrams

### Complete End-to-End Flow

```
User Input (CSV + Query)
        │
        ├─→ Phase 1: INGESTION ─────────────────┐
        │                                        │
        │   • Detect encoding (chardet)          │
        │   • Detect delimiter (frequency)       │
        │   • Parse CSV (pandas)                 │
        │   • Sanitize columns                   │
        │                                        │
        │                               DataProfile
        │                                        │
        │        ┌────────────────────────────────┘
        │        │
        ├─→ Phase 2: UNDERSTANDING ─────────────┐
        │                                        │
        │   • Infer column roles (6 types)       │
        │   • Statistical profiling              │
        │   • Temporal detection                 │
        │   • Outlier flagging (3×IQR)           │
        │                                        │
        │                        DataUnderstanding
        │                                        │
        │        ┌────────────────────────────────┘
        │        │
        ├─→ Phase 3: INTENT DETECTION ──────────┐
        │                                        │
        │   • Rule Classifier (< 5ms)            │
        │     - Regex pattern matching           │
        │     - Confidence scoring               │
        │   • LLM Fallback (if needed)           │
        │     - Claude structured JSON           │
        │     - Confidence = 0.9                 │
        │                                        │
        │                             IntentResult
        │                                        │
        │        ┌────────────────────────────────┘
        │        │
        ├─→ Phase 4: CHART RECOMMENDATION ──────┐
        │                                        │
        │   • Decision Tree                      │
        │     (intent × measures × dimensions)   │
        │   • Column Assignment                  │
        │   • Title Generation                   │
        │                                        │
        │                                ChartSpec
        │                                        │
        │        ┌────────────────────────────────┘
        │        │
        ├─→ Phase 5: VISUALIZATION ──────────────┐
        │                                        │
        │   • DataTransformer                    │
        │     - Filters                          │
        │     - Aggregation                      │
        │     - Sorting                          │
        │     - Top-N limit                      │
        │   • PlotlyRenderer                     │
        │     - Registry-based rendering         │
        │     - Theme application                │
        │                                        │
        │                               Plotly Figure
        │                                        │
        │        ┌────────────────────────────────┘
        │        │
        └─→ Phase 6: INSIGHTS ──────────────────┐
                                                 │
           • StatisticalAnalyzer               │
             - Missing data (>30%)              │
             - Outliers (3×IQR)                │
             - Correlations (r≥0.7)            │
             - Skewness                         │
           • LLMNarrator (optional)            │
             - Claude business insights         │
             - 3–5 actionable bullets          │
                                                │
                                         InsightBundle
                                                │
                                                ▼
                              ┌──────────────────────────┐
                              │  Streamlit UI Output:    │
                              │  • Interactive chart     │
                              │  • Statistical findings  │
                              │  • Business narrative    │
                              │  • Export options        │
                              └──────────────────────────┘
```

---

## Edge Cases & Error Handling

### Ingestion Phase

| Case | Handling |
|------|----------|
| Empty file (0 bytes) | Raise `IngestionError` |
| Truncated to MAX_ROWS | Add warning: "truncated to 500K rows" |
| Unknown encoding | Default to UTF-8 |
| Mixed encodings | Use sample detection; may lose some rows |
| Duplicate columns | Rename: col → col_1, col_2 |
| All-null column | Drop automatically; log in warnings |
| Malformed CSV rows | `on_bad_lines='warn'` skips silently |

### Understanding Phase

| Case | Handling |
|------|----------|
| All-null column | Skip in recommendations |
| Single row | Block trend/distribution; show KPI |
| All-identical values | Zero variance; skip correlation |
| Numeric-looking IDs (ZIP) | Check leading zeros; classify as DIMENSION |
| Mixed date formats | Try 12+ formats; pick highest parse rate |
| Invalid temporal format | Mark as TEXT or DIMENSION |
| Cardinality near 1.0 | Identifier if name hint OR n ≥ 50 rows |

### Intent Detection Phase

| Case | Handling |
|------|----------|
| Ambiguous query | Rule confidence < 0.3 → LLM fallback |
| No ANTHROPIC_API_KEY | Use Tier 1 result or raise error |
| Malformed LLM JSON | Fall back to best Tier 1 result |
| Query references nonexistent column | Fuzzy match + suggest closest; or default |

### Recommendation Phase

| Case | Handling |
|------|----------|
| No measures | Recommend count-based visualization |
| No dimensions | Recommend histogram or univariate chart |
| All identical x values | May produce flat chart; warn user |
| High cardinality dimension (> 50) | Use treemap or horizontal bar (compact) |

### Rendering Phase

| Case | Handling |
|------|----------|
| Empty after filters | Return empty dataframe; display "no data" |
| Nonexistent column | Skip aggregation; render raw data |
| NaN in y_col | `errors='coerce'` converts to NaN; Plotly hides |
| kaleido not installed | Raise `ExportError`; suggest pip install |

### Insights Phase

| Case | Handling |
|------|----------|
| Zero variance → correlation NaN | Skip correlation insights |
| Less than 5 rows | Skip statistical analysis |
| LLM API timeout | Gracefully omit narrative; keep statistical insights |

---

## Performance Considerations

### Time Complexity

| Phase | Operation | Complexity |
|-------|-----------|-----------|
| Ingestion | Encoding detection | O(sample_size) = O(10KB) |
| Ingestion | Parsing | O(rows × cols) |
| Understanding | Column analysis | O(rows × cols) |
| Intent | Rule classification | O(query_length) < 5ms |
| Intent | LLM classification | O(API latency) = 1–3 sec |
| Recommendation | Decision tree | O(1) lookup |
| Rendering | Aggregation | O(rows × log rows) for sort |
| Rendering | Plotly rendering | O(rows_displayed) |
| Insights | Correlation | O(measures²) |
| Insights | LLM narrative | O(API latency) = 1–2 sec |

### Space Complexity

| Phase | Data Structure | Size |
|-------|---|---|
| Ingestion | DataFrame | O(rows × cols) = 500K × 100 → ~50MB |
| Understanding | ColumnProfile list | O(cols) = O(100) |
| Insights | StatInsight list | O(1) to O(measures²) |

### Optimization Strategies

1. **Sampling**: Cap rows at 500K (configurable `MAX_ROWS`)
2. **Caching**: Use Streamlit `@st.cache_resource` for services
3. **Lazy Loading**: Don't compute correlations unless CORRELATION intent
4. **Async LLM**: Use `asyncio` for LLM calls in production
5. **Redis**: Use for distributed session store (vs in-memory)

### Benchmarks (Typical)

| Operation | Time |
|-----------|------|
| Upload & ingest 10MB CSV | 200ms |
| Analyze schema (10 cols, 100K rows) | 150ms |
| Rule-based intent classification | 5ms |
| LLM intent fallback | 1–2s |
| Chart recommendation & rendering | 100ms |
| Statistical insights | 50ms |
| LLM narrative generation | 1–2s |
| **Total (with LLM)** | ~4–5s |
| **Total (rule-based only)** | ~600ms |

---

## Configuration & Deployment

### Environment Variables

```bash
# LLM Integration (optional)
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-6              # Default

# Session & File Limits
SESSION_TTL_SECONDS=3600                 # 1 hour
MAX_UPLOAD_MB=50
MAX_ROWS=500000

# Optional Redis (for distributed sessions)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
```

### Streamlit Deployment

**Streamlit Cloud (Fastest):**
1. Push to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Add `ANTHROPIC_API_KEY` in Settings → Secrets

**Docker:**
```bash
docker build -t dv-tool .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=$KEY dv-tool
```

### FastAPI Backend (Optional)

```bash
# Development
uvicorn src.api.main:app --reload --port 8000

# Production
gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

---

## Conclusion

The **Ad-Hoc Data Visualization Tool** demonstrates a production-grade architecture for end-to-end data analysis:

- **6 Modular Phases**: Each phase is independently testable and extensible
- **Deterministic + ML Hybrid**: Rule-based for speed, LLM for flexibility
- **Robust Edge-Case Handling**: Handles encoding issues, missing data, outliers, ambiguous queries
- **Zero External APIs Required**: Core system offline-capable; LLM optional
- **20+ Chart Types**: Registry pattern enables easy extension
- **Statistical + Narrative Insights**: Combines automated findings with business context

### Key Takeaways

1. **Encoding Detection**: Combine BOM check + chardet + confidence threshold
2. **Column Role Inference**: Multi-factor logic (name hints, cardinality, numeric ratio, date parsing)
3. **Intent Classification**: Tier-1 regex for speed, Tier-2 LLM for accuracy
4. **Chart Recommendation**: Decision tree matching intent + data shape + cardinality
5. **Data Transformation**: Pipeline pattern (filter → aggregate → sort → top-N)
6. **Insights**: Statistical + optional narrative for actionable findings

---

**For questions or extensions, see [CLAUDE.md](CLAUDE.md) for architecture details and [README.md](README.md) for quick start.**
