from __future__ import annotations

import logging
from src.core.config import settings
from src.core.exceptions import IntentError
from src.intent.llm_classifier import LLMIntentClassifier
from src.intent.models import IntentResult
from src.intent.rule_classifier import RuleIntentClassifier
from src.intent.query_preprocessor import normalize_query
from src.understanding.models import DataUnderstanding


class IntentDetector:
    """
    Tier-1: RuleIntentClassifier (fast, deterministic).
    Tier-2: LLMIntentClassifier (fallback when rule confidence is insufficient).
    """

    RULE_CONFIDENCE_MIN = 0.3

    def __init__(self) -> None:
        self._rule = RuleIntentClassifier()
        self._llm: LLMIntentClassifier | None = None

    def detect(self, query: str, understanding: DataUnderstanding, conversation_history: list[dict] = None) -> IntentResult:
        normalized_query, extracted_dates = normalize_query(query)

        rule_result = self._rule.classify(normalized_query, understanding)
        hint_intent = rule_result.intent.value if rule_result and rule_result.intent else "unknown"
        hint_conf = rule_result.confidence if rule_result else 0.0

        result = None

        if not settings.anthropic_api_key:
            logging.warning("ANTHROPIC_API_KEY not set. Falling back to rule-only classification.")
            if rule_result:
                result = rule_result
            else:
                raise IntentError("Rule classifier returned no result and no ANTHROPIC_API_KEY is set.")
        else:
            if self._llm is None:
                self._llm = LLMIntentClassifier()

            try:
                result = self._llm.classify(
                    normalized_query, 
                    understanding, 
                    hint_intent=hint_intent, 
                    hint_conf=hint_conf,
                    conversation_history=conversation_history
                )
            except IntentError as e:
                logging.warning(f"LLM classification failed: {e}. Falling back to rule classifier.")
                if rule_result:
                    result = rule_result
                else:
                    raise

        if result and extracted_dates:
            result.filters = result.filters or {}
            result.filters["date_filter"] = extracted_dates

        return result
