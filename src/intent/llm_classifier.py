from __future__ import annotations

import json

import anthropic

from src.core.config import settings
from src.core.exceptions import IntentError
from src.intent.models import IntentResult, QueryIntent
from src.understanding.models import DataUnderstanding


SYSTEM_PROMPT = """\
You are a data visualization intent classifier for a data analysis tool.
Given a user query, a dataset schema, and optional conversation history, extract the visualization intent as structured JSON.

INTENT TYPES:
- trend: temporal progression, changes over time
- comparison: side-by-side values across categories
- ranking: top/bottom N items, sorting
- distribution: spread, histogram, variation
- correlation: relationship between two measures
- composition: breakdown, parts of a whole (pie, treemap)
- geographic: maps, choropleth, country/region data
- anomaly: outliers, unusual patterns
- summary: overview, key metrics (KPI cards)
- multi_dimension: multiple dimensions in one view
- faceted: repeated charts for different groups
- combined: multiple chart types together

RULE-BASED HINTS:
Rule-based pre-analysis suggests intent={hint_intent} with confidence={hint_conf}. Use this as a weak signal only.

DATE PARSING:
Extract any date references from the query into ISO 8601 format and include them in a "date_filter" array inside the "filters" object.

Dataset schema:
{schema}

Conversation history (last 6 turns):
{history}

Respond ONLY with a valid JSON object (no markdown, no code blocks, no explanation):
{{
  "intent": "trend|comparison|ranking|distribution|correlation|composition|geographic|anomaly|summary|multi_dimension|faceted|combined",
  "confidence": 0.0,
  "target_columns": [],
  "filters": {{"date_filter": []}},
  "aggregation": null,
  "group_by": null,
  "sort_order": null, // "asc" for bottom/worst, "desc" for top/best
  "top_n": null,
  "explicit_chart_type": null // e.g. "bar", "pie", "scatter", "heatmap" if explicitly requested
}}
"""


class LLMIntentClassifier:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def classify(self, query: str, understanding: DataUnderstanding, hint_intent: str = "unknown", hint_conf: float = 0.0, conversation_history: list[dict] = None) -> IntentResult:
        hist_str = "None"
        if conversation_history:
            hist_str = "\\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]])
        
        system = SYSTEM_PROMPT.format(schema=understanding.schema_str(), hint_intent=hint_intent, hint_conf=hint_conf, history=hist_str)
        try:
            response = self._client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens_intent,
                system=system,
                messages=[{"role": "user", "content": query}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data: dict = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IntentError(f"LLM returned non-JSON response: {exc}") from exc
        except Exception as exc:
            raise IntentError(f"LLM intent classification failed: {exc}") from exc

        # Validate intent value
        try:
            intent_val = QueryIntent(data.get("intent", "summary"))
        except ValueError:
            intent_val = QueryIntent.SUMMARY

        return IntentResult(
            intent=intent_val,
            confidence=float(data.get("confidence", 0.7)),
            target_columns=data.get("target_columns") or [],
            filters=data.get("filters") or {},
            aggregation=data.get("aggregation") or "sum",
            group_by=data.get("group_by"),
            sort_order=data.get("sort_order"),
            top_n=data.get("top_n"),
            tier="llm",
            explicit_chart_type=data.get("explicit_chart_type"),
            raw_llm_response=data,
        )
