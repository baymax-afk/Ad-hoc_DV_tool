from __future__ import annotations

from src.core.config import settings
from src.core.exceptions import IntentError
from src.intent.llm_classifier import LLMIntentClassifier
from src.intent.models import IntentResult
from src.intent.rule_classifier import RuleIntentClassifier
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

    def detect(self, query: str, understanding: DataUnderstanding) -> IntentResult:
        result = self._rule.classify(query, understanding)
        if result and result.confidence >= self.RULE_CONFIDENCE_MIN:
            return result

        # Fallback to LLM
        if not settings.anthropic_api_key:
            # No API key — use best rule result or default
            if result:
                return result
            raise IntentError(
                "Rule classifier returned no result and no ANTHROPIC_API_KEY is set."
            )

        if self._llm is None:
            self._llm = LLMIntentClassifier()

        try:
            return self._llm.classify(query, understanding)
        except IntentError:
            # Last resort: return rule result even with low confidence
            if result:
                return result
            raise
