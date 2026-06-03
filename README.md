# Ad-Hoc Data Visualization Tool

**Automatically understand CSV data and generate meaningful visualizations from natural language queries.**

Upload a CSV file, ask a question in plain English, and get an interactive chart + AI-powered insights instantly.

---

## Quick Start

### Prerequisites
- Python 3.11+
- `pip` or `conda`

### Setup (5 minutes)

```bash
# Clone or download the repo
cd Ad-hoc_DV_tool

# Create virtual environment (already exists at ./venv)
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env

# Add your Anthropic API key to .env (optional, but required for AI insights)
# ANTHROPIC_API_KEY=sk-ant-...
```

### Run the App

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Features

### 📊 Automatic Data Understanding
- **Column type inference:** MEASURE, DIMENSION, TEMPORAL, IDENTIFIER, TEXT, GEOGRAPHIC
- **Statistical profiling:** null %, cardinality, distribution, outliers, correlations
- **Temporal detection:** automatically identifies date columns and time granularity

### 💬 Natural Language Intent Detection
- **Tier-1 (LLM-Primary):** Claude-powered intent extraction with rule-based hints.
- **Tier-2 (Rule fallback):** Fast, regex-powered classification when LLM is unavailable.
- **Robust Date Parsing:** Extracts relative dates (e.g., "last month", "Q3") into strict ISO filters.
- **Supported intents:** trend, comparison, ranking, distribution, correlation, composition, geographic, anomaly, summary, multi_dimension, faceted, combined

### 📈 Intelligent Chart Recommendation
- **Multi-Chart Generation:** Recommends and renders 3-5 valid charts simultaneously for complex queries.
- **20 chart types:** bar, line, scatter, pie, histogram, heatmap, choropleth, treemap, radar, and more
- **Decision tree:** matches intent + data shape → best chart automatically

### 🎨 Interactive Visualization & Chat UI
- **Persistent Chat:** Intuitive chat interface preserving conversation history across queries.
- **Multi-Tab Layout:** View multiple generated charts side-by-side in Streamlit tabs.
- **Plotly-powered:** fully interactive charts (zoom, pan, hover tooltips)
- **Export:** download as PNG or SVG (requires kaleido)

### 💡 AI-Powered Insights
- **Dataset Analysis:** Automatically profiles and summarizes uploaded datasets to suggest angles.
- **Narrative Insights:** Claude generates specific, actionable business insights grounded in statistical findings.
- **Optional:** works without API key; LLM features gracefully disabled

---

## Example Queries

Try these on a sample CSV (columns: `region`, `product`, `revenue`, `date`):

| Query | Intent | Chart |
|-------|--------|-------|
| "Show me revenue over time" | Trend | Line chart |
| "Compare revenue by region" | Comparison | Bar chart |
| "Top 10 products by revenue" | Ranking | Horizontal bar |
| "Distribution of revenue" | Distribution | Histogram + box plot |
| "Revenue vs units sold" | Correlation | Scatter plot |
| "Breakdown by product category" | Composition | Pie/treemap |
| "Sales map by country" | Geographic | Choropleth |
| "Show outliers in revenue" | Anomaly | Box + scatter |

---

## Architecture

```
CSV Upload
    ↓
DataIngestor (encoding detection, delimiter sniffing)
    ↓
DataUnderstandingEngine (type inference, statistical profiling)
    ↓
IntentDetector (rule-based → LLM fallback)
    ↓
ChartRecommendationEngine (decision tree → multi-chart list)
    ↓
VisualizationPipeline (transform w/ dates → parallel render with Plotly)
    ↓
InsightBundle (statistical + DatasetAnalyst narrative)
    ↓
Streamlit Chat UI (interactive charts in tabs + insights)
```

6 phases, 39 files, zero external APIs required for core functionality.

See [CLAUDE.md](CLAUDE.md) for detailed architecture, edge case handling, and extension guide.

---

## Configuration

### Environment Variables

Create a `.env` file (or set in your shell):

```env
# Required for AI insights and LLM intent fallback
ANTHROPIC_API_KEY=sk-ant-...

# Optional: choose Claude model (default: claude-sonnet-4-6)
LLM_MODEL=claude-sonnet-4-6

# Optional: session and file limits
SESSION_TTL_SECONDS=3600        # Session expiry (1 hour)
MAX_UPLOAD_MB=50                # Max CSV file size
MAX_ROWS=500000                 # Max rows to ingest

# Optional: for FastAPI backend only
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### Streamlit Config

Streamlit-specific settings go in `~/.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#2E86DE"
backgroundColor = "#F5F5F5"
secondaryBackgroundColor = "#E0E0E0"
textColor = "#333333"

[server]
maxUploadSize = 50
```

---

## Deployment

### Development
```bash
streamlit run app.py
```

### Streamlit Cloud (Recommended for MVP)
1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and select `app.py`
4. Add `ANTHROPIC_API_KEY` in Settings → Secrets

### Docker
```bash
docker build -t dv-tool .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY dv-tool
```

### FastAPI Backend (Optional Separate Server)
```bash
# Development
uvicorn src.api.main:app --reload --port 8000

# Production
gunicorn src.api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

API docs auto-generated at [http://localhost:8000/docs](http://localhost:8000/docs)

See [CLAUDE.md → Deployment](CLAUDE.md#deployment) for detailed production setup.

---

## Troubleshooting

### "No chart generated"
- Check sidebar for parse warnings (encoding, delimiter issues)
- Verify CSV has at least one numeric column (MEASURE)
- Try a simpler query: "show me..." or "compare X by Y"

### "Column not recognized"
- Ensure column name exists in the uploaded CSV
- Tool uses fuzzy matching; close variants work ("revenu" → "revenue")
- Check dataset schema in "Schema" expandable

### "No AI insights generated"
- Add `ANTHROPIC_API_KEY` to `.env` and restart the app
- AI insights are optional; statistical findings work without it

### "Chart renders but looks wrong"
- Use "Advanced options" to force a different chart type or aggregation
- Check data filters: some queries filter rows away entirely

### Memory / Performance Issues
- Reduce `MAX_ROWS` in `.env` to sample data
- Disable LLM insights if running on low-memory systems
- Profile with `streamlit run app.py --logger.level=debug`

See [CLAUDE.md → Troubleshooting](CLAUDE.md#troubleshooting) for more Q&A.

---

## Project Structure

```
Ad-hoc_DV_tool/
├── app.py                 # Streamlit UI entry point
├── smoke_test.py          # End-to-end validation script
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template
├── .gitignore             # Git exclusions
├── CLAUDE.md              # Architecture & dev guide
├── README.md              # This file
│
└── src/
    ├── core/              # Config, exceptions, session store
    ├── ingestion/         # CSV parsing & sanitization
    ├── understanding/     # Column type inference & profiling
    ├── intent/            # Query intent detection (rule + LLM)
    ├── recommendation/    # Chart type selection
    ├── rendering/         # Plotly rendering pipeline
    ├── insights/          # Statistical & narrative insights
    └── api/               # FastAPI backend (optional)
```

---

## Development

### Running Tests
```bash
# Smoke test (validates all 6 phases)
python smoke_test.py

# Unit tests (if pytest fixtures added)
pytest tests/ -v
```

### Adding Features

**New chart type:**
1. Add function with `@register("chart_name")` in `src/rendering/plotly_renderer.py`
2. Update decision tree in `src/recommendation/engine.py`
3. Test: `PlotlyRenderer().supported_types()`

**New intent:**
1. Add to `QueryIntent` enum in `src/intent/models.py`
2. Add regex patterns to `src/intent/rule_classifier.py`
3. Add decision tree branch in `src/recommendation/engine.py`

**New column role:**
1. Add to `ColumnRole` enum in `src/understanding/models.py`
2. Update `_infer_role()` in `src/understanding/analyzer.py`
3. Add enrichment logic if needed

See [CLAUDE.md → Quick Reference](CLAUDE.md#quick-reference-adding-features) for details.

---

## API Reference

If running the FastAPI backend separately:

### Sessions
```bash
# Create session
curl -X POST http://localhost:8000/api/v1/sessions

# Upload CSV
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/upload \
  -F "file=@data.csv"

# Query
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "show revenue by region"}'

# Get schema
curl http://localhost:8000/api/v1/sessions/{session_id}/schema

# Delete session
curl -X DELETE http://localhost:8000/api/v1/sessions/{session_id}
```

Full OpenAPI docs at `/docs` when backend is running.

---

## Libraries & Dependencies

| Component | Library | Why |
|-----------|---------|-----|
| CSV parsing | pandas, chardet | Robust, handles encodings |
| Statistics | scipy, numpy | Industry standard |
| Fuzzy matching | rapidfuzz | Fast column name matching |
| Visualization | plotly | Interactive, browser-native |
| LLM | anthropic | Claude API access |
| Web UI | streamlit | Rapid prototyping, interactivity |
| API | fastapi, pydantic | Modern, type-safe, auto-docs |
| Data transform | pandas | Aggregation, filtering, sorting |

---

## Known Limitations

- **Row limit:** Truncated to 500K rows for performance (configurable)
- **File size:** Max 50 MB (configurable)
- **Session expiry:** 1 hour by default (in-memory store; use Redis for persistence)
- **LLM cost:** Each query with ambiguous intent calls Claude (watch API usage)
- **Concurrency:** In-memory session store; single-process only (add Redis for distributed)

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m "Add my feature"`)
4. Run smoke tests (`python smoke_test.py`)
5. Push and open a PR

See [CLAUDE.md](CLAUDE.md) for architecture details before major changes.

---

## License

MIT (adjust if needed)

---

## Support

- **Bugs/Issues:** Open a GitHub issue with sample CSV + query
- **Architecture Questions:** See [CLAUDE.md](CLAUDE.md)
- **Troubleshooting:** Check [CLAUDE.md → Troubleshooting](CLAUDE.md#troubleshooting)
- **API Docs:** Run FastAPI backend; visit `/docs`

---

## What's Next?

- [ ] Add unit tests (pytest fixtures for each phase)
- [ ] Support Parquet/Excel/JSON file formats
- [ ] Advanced filtering UI (date ranges, multi-select)
- [ ] Chart customization (colors, titles, axis labels)
- [x] Query history & saved visualizations (now supported via Chat UI)
- [ ] Collaborative sessions (share charts via URL)
- [ ] Export to PDF reports with multiple charts
- [ ] Real-time data streaming support

---

**Built with Python, Plotly, Claude, and ❤️**
