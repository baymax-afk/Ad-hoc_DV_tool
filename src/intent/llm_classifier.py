from __future__ import annotations

import json

import anthropic

from src.core.config import settings
from src.core.exceptions import IntentError
from src.intent.models import IntentResult, QueryIntent
from src.understanding.models import DataUnderstanding


SYSTEM_PROMPT = """\
You are a data visualization intent classifier.
Given a user query and a dataset schema, extract the visualization intent as structured JSON.

Dataset schema:
{schema}

Respond ONLY with valid JSON — no markdown, no explanation — matching exactly this structure:
{{
  "intent": "<distribution|trend|comparison|correlation|composition|ranking|geographic|anomaly|summary>",
  "confidence": <0.0-1.0>,
  "target_columns": ["col1", "col2"],
  "filters": {{"column_name": "value"}},
  "aggregation": "<sum|avg|count|max|min|null>",
  "group_by": "<column_name or null>",
  "sort_order": "<asc|desc|null>",
  "top_n": <integer or null>
}}
"""


class LLMIntentClassifier:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def classify(self, query: str, understanding: DataUnderstanding) -> IntentResult:
        system = SYSTEM_PROMPT.format(schema=understanding.schema_str())
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
            raw_llm_response=data,
        )
