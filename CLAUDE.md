# Intelligent Ad-Hoc Data Visualization Tool

## Project Purpose
End-to-end system that ingests CSV files, understands their structure, and generates meaningful visualizations + insights from natural language queries.

## Architecture — 6 Phases

```
CSV Upload → DataIngestor → DataUnderstandingEngine → IntentDetector
                               InsightBundle ← VisualizationPipeline ← ChartRecommendationEngine (Multi-Chart)
```

### Phase 1 — Data Ingestion (`src/ingestion/`)
- `DataIngestor`: encoding detection (chardet), delimiter sniffing, sanitization, row capping at 500K
- `DataProfile`: canonical output — df, file_hash, row/col counts, parse_warnings

### Phase 2 — Data Understanding (`src/understanding/`)
- `DataUnderstandingEngine`: two-pass analysis — statistical then semantic
- Column roles: DIMENSION, MEASURE, TEMPORAL, IDENTIFIER, TEXT, GEOGRAPHIC
- `ColumnProfile`: null_pct, cardinality, distribution type, outlier flag, date_format
- `DataUnderstanding`: grouped column lists, has_time_series flag, llm_summary

### Phase 3 — Intent Detection (`src/intent/`)
- `QueryPreprocessor`: Normalizes conversational dates (e.g., "last month") into ISO boundaries.
- Tier 1: `LLMIntentClassifier` — Claude Sonnet, structured JSON output, includes history and rule hints.
- Tier 2: `RuleIntentClassifier` — regex patterns, fast fallback when LLM is unavailable.
- Intents: distribution, trend, comparison, correlation, composition, ranking, geographic, anomaly, summary, multi_dimension, faceted, combined
- `IntentResult`: intent, confidence, target_columns, filters (date_filter), aggregation, group_by, top_n

### Phase 4 — Chart Recommendation (`src/recommendation/`)
- `ChartRecommendationEngine`: deterministic decision tree → returns list of `ChartSpec`
- Decision matrix: intent × measure_count × dimension_cardinality × has_temporal
- Supports multi-chart outputs (faceted, colored grids, combined charts).

### Phase 5 — Rendering (`src/rendering/`)
- `DataTransformer`: date filter parsing → general filter → aggregate → sort → top-N
- `VisualizationPipeline`: Run parallel execution on `list[ChartSpec]` returning `list[tuple[ChartSpec, Figure]]`
- `PlotlyRenderer`: @register decorator per chart type → Plotly Express/GO figure
- `FigureDecorator`: theme (plotly_white), layout polish, legend positioning
- Export via kaleido (PNG/SVG/PDF)

### Phase 6 — Insights (`src/insights/`)
- `StatisticalAnalyzer`: missing data, outliers (3×IQR), correlations (r≥0.7), trend direction
- `DatasetAnalyst`: Profiles whole dataset natively on upload and narrate 3-5 business insights post-query.
- `LLMNarrator`: Generates natural language summary of statistical properties.

## API (`src/api/`)
- `POST /api/v1/sessions` → session_id
- `POST /api/v1/sessions/{id}/upload` → column_profiles, summary
- `POST /api/v1/sessions/{id}/query` → chart_spec, plotly_json, insights
- `GET  /api/v1/sessions/{id}/schema` → columns, understanding
- `POST /api/v1/sessions/{id}/refine` → updated chart
- `GET  /api/v1/sessions/{id}/export` → PNG/PDF blob

## Entry Points
- `app.py` — Streamlit Persistent Chat UI (MVP frontend)
- `src/api/main.py` — FastAPI backend

## Key Libraries
- pandas, chardet — ingestion
- scipy, numpy — statistics
- rapidfuzz — fuzzy column matching
- plotly, kaleido — rendering + export
- fastapi, pydantic-settings — API
- anthropic — LLM (Claude 3.5 Sonnet)
- streamlit — UI

## Edge Cases to Handle
1. All-null column → skip in recommendations
2. Single-row DataFrame → block distribution/trend, show KPI card
3. All-identical values → zero variance warning, skip correlation
4. Mixed date formats → try each pattern, pick highest parse rate
5. Numeric-looking IDs (ZIP, product codes) → cardinality ratio + leading zero check
6. LLM returns malformed JSON → fall back to rule classifier
7. Pivot with NaN-heavy matrix → configurable fill strategy
8. Query references nonexistent column → fuzzy match + confirm

## Development Phases (MVP Order)
1. Phase 1+2 (no LLM dependency) — get understanding working
2. API skeleton with session store
3. Phase 3+4 (rule-based first, LLM second)
4. Phase 5 rendering with core chart types
5. Phase 6 insights
6. Streamlit UI wiring
7. LLM layers (intent fallback + narrator)

## Project Defaults

**Python conventions:**
- PEP 8 style; all public functions have type hints
- Docstrings only when WHY is non-obvious; omit when naming is clear
- Avoid defensive programming (error handling only at system boundaries)
- No half-finished implementations; don't add features beyond the task scope

**New files & projects:**
- Always generate `.gitignore` appropriate to the stack
- Include `requirements.txt` or `pyproject.toml` for reproducibility
- Generate `.env.example` for configuration templates
- After scaffolding, run smoke tests and fix bugs before declaring completion

## Environment
- Python 3.11+
- Set `ANTHROPIC_API_KEY` in `.env` to enable LLM intent fallback + AI insights
- Set `LLM_MODEL` in `.env` to choose Claude model (default: `claude-sonnet-4-6`)
- Venv already created at `./venv`

---

## Deployment

### Streamlit UI (Frontend)
```bash
# Development
streamlit run app.py

# Production (via Docker or cloud platform)
# Requires: ANTHROPIC_API_KEY in environment or secrets
# Recommended: host on Streamlit Cloud, Heroku, or Docker
```

**Streamlit Cloud (fastest):**
1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo, select `app.py`
4. Add `ANTHROPIC_API_KEY` in Settings → Secrets (TOML format)

**Docker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

### FastAPI Backend
```bash
# Development
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production (via gunicorn + uvicorn workers)
gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Environment variables:**
- `ANTHROPIC_API_KEY` — required for LLM features
- `LLM_MODEL` — Claude model ID (default: `claude-sonnet-4-6`)
- `SESSION_TTL_SECONDS` — session expiry in seconds (default: 3600)
- `MAX_UPLOAD_MB` — max CSV file size (default: 50)
- `MAX_ROWS` — max rows to ingest (default: 500000)
- `REDIS_URL` — Redis connection for distributed sessions (optional; in-memory store used if not set)

**Production checklist:**
- [ ] Use `--workers 4+` based on CPU cores
- [ ] Run behind reverse proxy (nginx) for TLS
- [ ] Set `ANTHROPIC_API_KEY` via secrets manager, not `.env`
- [ ] Set `SESSION_TTL_SECONDS` conservatively (e.g., 1800 for 30 min sessions)
- [ ] Add Redis for session persistence across restarts
- [ ] Enable CORS only for trusted domains in `src/api/main.py`
- [ ] Monitor API logs for malformed queries and LLM API errors

### Running Both Together
```bash
# Terminal 1: Backend
uvicorn src.api.main:app --port 8000

# Terminal 2: Streamlit (points to http://localhost:8000 by default)
streamlit run app.py
```

To redirect Streamlit to a different backend, modify the `session_state` in `app.py` or add a sidebar config option.

---

## Troubleshooting

### Data Understanding

**Q: Revenue/Sales columns are classified as IDENTIFIER instead of MEASURE**
- **Cause:** Small dataset (< 50 rows) where cardinality ratio > 0.95
- **Fix:** Column role inference requires `n >= MIN_ROWS_FOR_CARDINALITY_ID` OR a name hint (e.g., "id", "key", "code")
- **Prevention:** Ensure column names are semantic (avoid generic "value_1", "value_2")

**Q: Temporal column not detected (date_format = None)**
- **Cause:** Date format not in `DATE_FORMATS` list or parser hit a locale issue
- **Fix:** Check `src/understanding/analyzer.py` and add missing format to `DATE_FORMATS`
- **Example:** If dates are "01.05.2024" (DE locale), add `"%d.%m.%Y"` to the list

**Q: All-null column causes AttributeError downstream**
- **Cause:** Attempt to access `.mean()` or `.std()` on empty Series
- **Fix:** `_enrich_measure()` checks `len(numeric) == 0` and returns early; ensure `null_pct >= 0.99` rows trigger this

### Intent Detection

**Q: Query returns "Rule classifier returned no result and no ANTHROPIC_API_KEY is set"**
- **Cause:** Rule classifier confidence < 0.3 (too ambiguous) and no LLM fallback available
- **Fix:** 
  - Add `ANTHROPIC_API_KEY` to `.env`
  - OR rephrase query with clearer keywords ("trend", "compare", "top 10", "distribute")

**Q: LLM returns malformed JSON or wrong intent**
- **Cause:** Query is too vague or LLM misunderstood the schema
- **Fix:** Check `raw_llm_response` in query result; if parsing fails, rule classifier output is used as last resort
- **Debug:** Print `understanding.schema_str()` to see what the LLM was given

### Chart Rendering

**Q: Empty chart or "No data after filters"**
- **Cause:** Filters eliminated all rows, or column names in spec don't exist in filtered data
- **Fix:** Check `spec.filters` dict; verify column names match post-transformation dataframe
- **Debug:** Log the dataframe shape after `DataTransformer.transform()`

**Q: Unsupported chart type error**
- **Cause:** ChartRecommendationEngine suggested a type not registered in PlotlyRenderer
- **Fix:** All 20 chart types are pre-registered; check that `spec.chart_type` is in `PlotlyRenderer.supported_types()`
- **Debug:** Print `PlotlyRenderer().supported_types()` to verify registration

**Q: Plotly chart renders but looks wrong (bad labels, poor scale)**
- **Cause:** Column names not cleaned or axis ranges not optimized
- **Fix:** Check `spec.x_label`, `spec.y_label`; Plotly auto-scales axes based on data
- **Workaround:** Use the "Advanced options" panel to force a different aggregation or chart type

**Q: PNG/SVG export fails with "kaleido not installed"**
- **Cause:** `kaleido` dependency missing; requires system libs (e.g., libGL on Linux)
- **Fix:** `pip install kaleido`
- **Linux:** `apt-get install -y libgl1 xvfb` may be needed
- **Windows/Mac:** Usually installs cleanly; check for proxy/SSL cert issues

### Insights

**Q: Narrative insights are empty or generic**
- **Cause:** LLM saw no interesting statistical findings, or API key is invalid
- **Fix:** 
  - Verify `ANTHROPIC_API_KEY` is set and valid
  - Check `stat_insights` list is non-empty (statistical findings exist)
  - Review `_narrator._build_context()` to see what facts were sent to the LLM

**Q: Correlation insights show r=NaN**
- **Cause:** Numeric column conversion failed or contains all-identical values
- **Fix:** Check `numeric_df.isna().all()` before correlation; skip if true
- **Debug:** Print numeric_df.describe() to spot zero variance

### API & Sessions

**Q: Session expires too quickly / "Session not found" error**
- **Cause:** `SESSION_TTL_SECONDS` too low or session store not persisted
- **Fix:** 
  - Increase `SESSION_TTL_SECONDS` in `.env` (e.g., 7200 for 2 hours)
  - For production: add Redis backend instead of in-memory store

**Q: File upload size limit exceeded**
- **Cause:** CSV larger than `MAX_UPLOAD_MB`
- **Fix:** Increase `MAX_UPLOAD_MB` in `.env` (default: 50)
- **Note:** Row capping at `MAX_ROWS` still applies; file size and row count are independent

**Q: CORS errors when calling API from frontend**
- **Cause:** Browser blocks requests to different origin
- **Fix:** FastAPI app includes CORS middleware with `allow_origins=["*"]` — verify it's running
- **Debug:** Check browser console for "Access-Control-Allow-Origin" headers

### Performance

**Q: Smoke test or query is slow (> 5s)**
- **Cause:** Large dataset (many rows), slow LLM API, or CPU-bound stats
- **Fix:**
  - Reduce `MAX_ROWS` to sample data
  - Skip LLM layers (comment out `_narrator` in Streamlit)
  - Profile with `cProfile` or `py-spy`

**Q: Memory bloat on repeated queries**
- **Cause:** DataFrame copies not garbage-collected or session store accumulates old data
- **Fix:**
  - Call `gc.collect()` after large transforms
  - Implement session eviction in `session_store._evict_expired()`
  - Use Redis to offload to disk

---

## Quick Reference: Adding Features

### Add a new chart type
1. In `src/rendering/plotly_renderer.py`, add a function with `@register("chart_name")` decorator
2. Implement the function: `def _mychart(df: pd.DataFrame, spec: ChartSpec) -> go.Figure`
3. Update decision tree in `src/recommendation/engine.py` to suggest it for certain intents
4. Test: `PlotlyRenderer().supported_types()` should include it

### Add a new intent
1. Add to `QueryIntent` enum in `src/intent/models.py`
2. Add regex patterns to `INTENT_PATTERNS` in `src/intent/rule_classifier.py`
3. Add decision tree branch in `src/recommendation/engine.py._decision_tree()`
4. Test with smoke test or manual query

### Add a new column role
1. Add to `ColumnRole` enum in `src/understanding/models.py`
2. Update `_infer_role()` logic in `src/understanding/analyzer.py`
3. Add enrichment logic (e.g., `_enrich_custom_role()`) if needed
4. Update API response schema in `src/api/routes/sessions.py`
