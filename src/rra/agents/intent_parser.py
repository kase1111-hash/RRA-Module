# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Enhanced Intent Parser for Negotiation Messages.

Provides sophisticated intent recognition with:
- Configurable pattern matching with confidence scoring
- Multiple intent detection (not just single intent)
- Entity extraction (prices, durations, quantities)
- Sentiment analysis hooks
- Future NLP/LLM integration points

Addresses M-002: Intent parsing uses keyword matching - enhanced with NLP patterns.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Types of buyer intents."""

    # Information seeking
    PRICE_INQUIRY = "price_inquiry"
    FEATURE_INQUIRY = "feature_inquiry"
    TERMS_INQUIRY = "terms_inquiry"
    TECHNICAL_INQUIRY = "technical_inquiry"
    SUPPORT_INQUIRY = "support_inquiry"

    # Negotiation actions
    PRICE_PROPOSAL = "price_proposal"
    COUNTER_OFFER = "counter_offer"
    ACCEPT_OFFER = "accept_offer"
    REJECT_OFFER = "reject_offer"

    # Transaction actions
    PURCHASE_INTENT = "purchase_intent"
    REQUEST_DEMO = "request_demo"
    REQUEST_TRIAL = "request_trial"

    # Conversation management
    GREETING = "greeting"
    FAREWELL = "farewell"
    CLARIFICATION = "clarification"
    GENERAL = "general"

    # Negative signals
    OBJECTION = "objection"
    HESITATION = "hesitation"
    COMPARISON = "comparison"


class Sentiment(str, Enum):
    """Message sentiment classification."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


@dataclass
class ExtractedEntity:
    """An entity extracted from the message."""

    entity_type: str  # price, duration, quantity, currency, etc.
    value: Any
    raw_text: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0


@dataclass
class IntentMatch:
    """A matched intent with confidence score."""

    intent_type: IntentType
    confidence: float  # 0.0 to 1.0
    matched_patterns: List[str] = field(default_factory=list)
    entities: List[ExtractedEntity] = field(default_factory=list)


@dataclass
class ParsedIntent:
    """
    Complete parsed intent result.

    Contains primary intent, secondary intents, entities, and sentiment.
    """

    primary_intent: IntentMatch
    secondary_intents: List[IntentMatch] = field(default_factory=list)
    entities: List[ExtractedEntity] = field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    raw_message: str = ""
    normalized_message: str = ""

    @property
    def has_price_proposal(self) -> bool:
        """Check if message contains a price proposal."""
        return any(
            i.intent_type in [IntentType.PRICE_PROPOSAL, IntentType.COUNTER_OFFER]
            for i in [self.primary_intent] + self.secondary_intents
        )

    @property
    def proposed_price(self) -> Optional[ExtractedEntity]:
        """Get proposed price entity if present."""
        for entity in self.entities:
            if entity.entity_type == "price":
                return entity
        return None

    @property
    def is_ready_to_purchase(self) -> bool:
        """Check if buyer is ready to purchase."""
        return any(
            i.intent_type in [IntentType.PURCHASE_INTENT, IntentType.ACCEPT_OFFER]
            for i in [self.primary_intent] + self.secondary_intents
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            "type": self.primary_intent.intent_type.value,
            "confidence": self.primary_intent.confidence,
            "asks_about_price": self.primary_intent.intent_type == IntentType.PRICE_INQUIRY,
            "proposes_price": self.has_price_proposal,
            "asks_about_features": self.primary_intent.intent_type == IntentType.FEATURE_INQUIRY,
            "asks_about_terms": self.primary_intent.intent_type == IntentType.TERMS_INQUIRY,
            "ready_to_purchase": self.is_ready_to_purchase,
            "proposed_amount": (
                f"{self.proposed_price.value} {self.proposed_price.raw_text}"
                if self.proposed_price
                else None
            ),
            "sentiment": self.sentiment.value,
            "entities": [
                {
                    "type": e.entity_type,
                    "value": e.value,
                    "text": e.raw_text,
                }
                for e in self.entities
            ],
            "secondary_intents": [
                {"type": i.intent_type.value, "confidence": i.confidence}
                for i in self.secondary_intents
            ],
        }


@dataclass
class IntentPattern:
    """
    A pattern for matching intents.

    Supports regex patterns with optional entity extraction.
    """

    intent_type: IntentType
    patterns: List[str]  # Regex patterns
    keywords: List[str]  # Simple keyword matches
    weight: float = 1.0  # Pattern weight for confidence calculation
    entity_extractors: List[str] = field(default_factory=list)  # Entity types to extract


class IntentParser:
    """
    Enhanced intent parser with pattern matching and entity extraction.

    Features:
    - Configurable intent patterns
    - Multi-intent detection with confidence scoring
    - Entity extraction (prices, durations, quantities)
    - Sentiment analysis
    - Extensible for NLP/LLM integration
    """

    # Default intent patterns
    DEFAULT_PATTERNS: List[IntentPattern] = [
        # Price inquiry
        IntentPattern(
            intent_type=IntentType.PRICE_INQUIRY,
            patterns=[
                r"how much (does|do|is|are|would)",
                r"what('s| is| are) (the )?price",
                r"what (do you|does it) cost",
                r"pricing (info|information|details)",
                r"quote (me|for)",
            ],
            keywords=["price", "cost", "expensive", "cheap", "affordable", "budget", "pricing"],
            weight=1.0,
        ),
        # Price proposal
        IntentPattern(
            intent_type=IntentType.PRICE_PROPOSAL,
            patterns=[
                r"(i('d| would)?|we('d| would)?|can i|can we) (offer|pay|do)",
                r"(my|our) (offer|budget|price) (is|would be)",
                r"would you (accept|take|consider)",
                r"counter.?offer",
            ],
            keywords=["offer", "propose", "suggest", "counter"],
            weight=1.2,
            entity_extractors=["price"],
        ),
        # Feature inquiry
        IntentPattern(
            intent_type=IntentType.FEATURE_INQUIRY,
            patterns=[
                r"what (does it|do you|is) (include|offer|provide)",
                r"what (features|capabilities|functionality)",
                r"(does|do) (it|you) (support|have|include)",
                r"tell me (about|more)",
            ],
            keywords=["feature", "include", "capability", "support", "functionality", "provide"],
            weight=1.0,
        ),
        # Terms inquiry
        IntentPattern(
            intent_type=IntentType.TERMS_INQUIRY,
            patterns=[
                r"what (are )?the terms",
                r"license (terms|conditions|agreement)",
                r"(how long|duration|period)",
                r"(can i|am i allowed)",
            ],
            keywords=["terms", "conditions", "license", "duration", "agreement", "rights"],
            weight=1.0,
        ),
        # Technical inquiry
        IntentPattern(
            intent_type=IntentType.TECHNICAL_INQUIRY,
            patterns=[
                r"(what|which) (language|framework|tech)",
                r"(how does it|how do you) (work|function)",
                r"(is it|does it) compatible",
                r"technical (details|specs|specifications)",
            ],
            keywords=[
                "technical", "language", "framework", "api", "integration",
                "compatible", "requirements", "dependencies",
            ],
            weight=1.0,
        ),
        # Purchase intent
        IntentPattern(
            intent_type=IntentType.PURCHASE_INTENT,
            patterns=[
                r"(i('d| would)?|we('d| would)?) (like to|want to) (buy|purchase|get)",
                r"(ready to|let'?s) (buy|purchase|proceed)",
                r"(take|have) (my|the) money",
                r"where (do i|can i) (pay|purchase)",
            ],
            keywords=["buy", "purchase", "acquire", "get", "proceed"],
            weight=1.5,
        ),
        # Accept offer
        IntentPattern(
            intent_type=IntentType.ACCEPT_OFFER,
            patterns=[
                r"(i|we) (accept|agree|confirm)",
                r"(deal|done|agreed|sounds good)",
                r"(let'?s|we should) (do it|proceed|go ahead)",
                r"(that|this) works",
            ],
            keywords=["accept", "agree", "deal", "confirm", "yes", "okay", "ok"],
            weight=1.5,
        ),
        # Reject offer
        IntentPattern(
            intent_type=IntentType.REJECT_OFFER,
            patterns=[
                r"(i|we) (can'?t|cannot|won'?t|decline)",
                r"(too|way too) (expensive|much|high)",
                r"(no|nope|not interested)",
                r"(pass|skip|forget it)",
            ],
            keywords=["reject", "decline", "no", "pass", "expensive", "cannot"],
            weight=1.3,
        ),
        # Hesitation
        IntentPattern(
            intent_type=IntentType.HESITATION,
            patterns=[
                r"(i('m| am)|we('re| are)) not sure",
                r"(need to|have to) (think|consider)",
                r"(maybe|perhaps|possibly)",
                r"(let me|i('ll| will)) (think|consider)",
            ],
            keywords=["maybe", "perhaps", "unsure", "think", "consider", "possibly"],
            weight=0.8,
        ),
        # Greeting
        IntentPattern(
            intent_type=IntentType.GREETING,
            patterns=[
                r"^(hi|hello|hey|greetings)",
                r"^good (morning|afternoon|evening)",
            ],
            keywords=["hi", "hello", "hey", "greetings"],
            weight=0.5,
        ),
        # Request demo/trial
        IntentPattern(
            intent_type=IntentType.REQUEST_DEMO,
            patterns=[
                r"(can i|could i|may i) (see|try|test)",
                r"(demo|demonstration|trial|test)",
                r"(show me|walk me through)",
            ],
            keywords=["demo", "trial", "test", "try", "preview"],
            weight=1.1,
        ),
        # Comparison/competition
        IntentPattern(
            intent_type=IntentType.COMPARISON,
            patterns=[
                r"(compared to|vs|versus|better than)",
                r"(other|alternative|competitor)",
                r"(why should i|what makes you)",
            ],
            keywords=["compare", "alternative", "competitor", "versus", "better", "different"],
            weight=0.9,
        ),
    ]

    # Entity extraction patterns
    ENTITY_PATTERNS: Dict[str, Pattern[str]] = {
        "price": re.compile(
            r"(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(eth|usdc|usdt|dai|usd|\$|dollars?)",
            re.IGNORECASE,
        ),
        "duration": re.compile(
            r"(\d+)\s*(year|month|week|day|hour)s?",
            re.IGNORECASE,
        ),
        "quantity": re.compile(
            r"(\d+)\s*(seat|user|license|developer|team)s?",
            re.IGNORECASE,
        ),
        "percentage": re.compile(
            r"(\d+(?:\.\d+)?)\s*(%|percent)",
            re.IGNORECASE,
        ),
    }

    # Sentiment indicators
    POSITIVE_INDICATORS = [
        "great", "excellent", "perfect", "love", "amazing", "fantastic",
        "good", "nice", "thanks", "appreciate", "helpful", "interested",
    ]
    NEGATIVE_INDICATORS = [
        "bad", "terrible", "awful", "hate", "expensive", "overpriced",
        "disappointed", "frustrating", "complicated", "difficult",
    ]
    URGENT_INDICATORS = [
        "urgent", "asap", "immediately", "quickly", "deadline", "rush",
        "need now", "time sensitive", "critical",
    ]

    def __init__(
        self,
        custom_patterns: Optional[List[IntentPattern]] = None,
        confidence_threshold: float = 0.3,
        enable_sentiment: bool = True,
        nlp_callback: Optional[Callable[[str], Dict[str, Any]]] = None,
    ):
        """
        Initialize the intent parser.

        Args:
            custom_patterns: Additional intent patterns to use
            confidence_threshold: Minimum confidence for intent matching
            enable_sentiment: Enable sentiment analysis
            nlp_callback: Optional callback for NLP/LLM-based parsing
        """
        self.patterns = list(self.DEFAULT_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)

        self.confidence_threshold = confidence_threshold
        self.enable_sentiment = enable_sentiment
        self.nlp_callback = nlp_callback
        self._locked = False

        # Valid intents that the NLP callback is allowed to return
        self._valid_nlp_intents: set = {it.value for it in IntentType}

        # Financial intents that require pattern matching agreement
        self._financial_intents: set = {
            IntentType.PURCHASE_INTENT.value,
            IntentType.ACCEPT_OFFER.value,
        }

        # Compile regex patterns
        self._compiled_patterns: Dict[IntentType, List[Pattern[str]]] = {}
        for pattern in self.patterns:
            self._compiled_patterns.setdefault(pattern.intent_type, [])
            for p in pattern.patterns:
                try:
                    self._compiled_patterns[pattern.intent_type].append(
                        re.compile(p, re.IGNORECASE)
                    )
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{p}': {e}")

    def parse(self, message: str) -> ParsedIntent:
        """
        Parse a message to extract intents, entities, and sentiment.

        Args:
            message: The message to parse

        Returns:
            ParsedIntent with all extracted information
        """
        # Lock patterns on first parse call to prevent runtime injection
        if not self._locked:
            self._locked = True

        if not message or not message.strip():
            return ParsedIntent(
                primary_intent=IntentMatch(
                    intent_type=IntentType.GENERAL,
                    confidence=0.0,
                ),
                raw_message=message,
            )

        normalized = self._normalize_message(message)

        # Always run pattern matching (needed for financial intent validation)
        pattern_intent_matches = self._match_intents(normalized)

        # Try NLP callback if available
        if self.nlp_callback:
            try:
                nlp_result = self.nlp_callback(message)
                if nlp_result:
                    validated = self._validate_nlp_result(nlp_result, pattern_intent_matches)
                    if validated is not None:
                        return self._convert_nlp_result(validated, message, normalized)
                    else:
                        logger.warning("NLP callback result failed validation, falling back to pattern matching")
            except Exception as e:
                logger.warning(f"NLP callback failed: {e}, falling back to pattern matching")

        # Pattern-based parsing
        intent_matches = pattern_intent_matches
        entities = self._extract_entities(message)
        sentiment = self._analyze_sentiment(normalized) if self.enable_sentiment else Sentiment.NEUTRAL

        # Sort by confidence and select primary/secondary
        intent_matches.sort(key=lambda x: x.confidence, reverse=True)

        if not intent_matches:
            primary = IntentMatch(intent_type=IntentType.GENERAL, confidence=0.5)
            secondary: List[IntentMatch] = []
        else:
            primary = intent_matches[0]
            secondary = [
                m for m in intent_matches[1:]
                if m.confidence >= self.confidence_threshold
            ]

        return ParsedIntent(
            primary_intent=primary,
            secondary_intents=secondary,
            entities=entities,
            sentiment=sentiment,
            raw_message=message,
            normalized_message=normalized,
        )

    def _normalize_message(self, message: str) -> str:
        """Normalize message for pattern matching."""
        # Convert to lowercase
        normalized = message.lower()

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Expand common contractions
        contractions = {
            "i'm": "i am",
            "i'd": "i would",
            "i'll": "i will",
            "i've": "i have",
            "we're": "we are",
            "we'd": "we would",
            "we'll": "we will",
            "we've": "we have",
            "what's": "what is",
            "that's": "that is",
            "it's": "it is",
            "can't": "cannot",
            "won't": "will not",
            "don't": "do not",
            "doesn't": "does not",
            "let's": "let us",
        }
        for contraction, expansion in contractions.items():
            normalized = normalized.replace(contraction, expansion)

        return normalized

    def _match_intents(self, message: str) -> List[IntentMatch]:
        """Match intents against the message."""
        matches: List[IntentMatch] = []

        for pattern in self.patterns:
            confidence = 0.0
            matched_patterns: List[str] = []

            # Check regex patterns
            compiled = self._compiled_patterns.get(pattern.intent_type, [])
            for regex in compiled:
                if regex.search(message):
                    confidence += 0.4 * pattern.weight
                    matched_patterns.append(regex.pattern)

            # Check keywords
            message_words = set(message.split())
            keyword_matches = message_words.intersection(set(pattern.keywords))
            if keyword_matches:
                confidence += 0.2 * len(keyword_matches) * pattern.weight
                matched_patterns.extend(list(keyword_matches))

            if confidence >= self.confidence_threshold:
                matches.append(
                    IntentMatch(
                        intent_type=pattern.intent_type,
                        confidence=min(confidence, 1.0),
                        matched_patterns=matched_patterns,
                    )
                )

        return matches

    def _extract_entities(self, message: str) -> List[ExtractedEntity]:
        """Extract entities from the message."""
        entities: List[ExtractedEntity] = []

        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            for match in pattern.finditer(message):
                value = match.group(1)
                unit = match.group(2) if match.lastindex >= 2 else None

                # Parse numeric value
                try:
                    numeric_value = float(value.replace(",", ""))
                except ValueError:
                    numeric_value = value

                entities.append(
                    ExtractedEntity(
                        entity_type=entity_type,
                        value=numeric_value,
                        raw_text=unit.upper() if unit else "",
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.9,
                    )
                )

        return entities

    def _analyze_sentiment(self, message: str) -> Sentiment:
        """Analyze message sentiment."""
        words = set(message.split())

        positive_count = len(words.intersection(set(self.POSITIVE_INDICATORS)))
        negative_count = len(words.intersection(set(self.NEGATIVE_INDICATORS)))
        urgent_count = len(words.intersection(set(self.URGENT_INDICATORS)))

        if urgent_count > 0:
            return Sentiment.URGENT

        if positive_count > negative_count:
            return Sentiment.POSITIVE
        elif negative_count > positive_count:
            return Sentiment.NEGATIVE

        return Sentiment.NEUTRAL

    def _validate_nlp_result(
        self,
        nlp_result: Any,
        pattern_matches: List[IntentMatch],
    ) -> Optional[Dict[str, Any]]:
        """
        Validate NLP callback result before trusting it.

        Checks:
        - Result is a dict with "intent" and "confidence" keys
        - Confidence >= 0.8
        - Intent is a known valid intent
        - Financial intents (PURCHASE_INTENT, ACCEPT_OFFER) require pattern matching agreement

        Args:
            nlp_result: Raw result from NLP callback
            pattern_matches: Results from pattern matching for cross-validation

        Returns:
            Validated result dict, or None if validation fails
        """
        # Must be a dict with required keys
        if not isinstance(nlp_result, dict):
            logger.warning("NLP callback returned non-dict result")
            return None

        if "intent" not in nlp_result or "confidence" not in nlp_result:
            logger.warning("NLP callback result missing 'intent' or 'confidence' keys")
            return None

        # Confidence must be >= 0.8
        confidence = nlp_result.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or confidence < 0.8:
            logger.warning(f"NLP callback confidence too low: {confidence}")
            return None

        # Intent must be a known valid intent
        intent_str = nlp_result.get("intent", "")
        if intent_str not in self._valid_nlp_intents:
            logger.warning(f"NLP callback returned unknown intent: {intent_str}")
            return None

        # Financial intents require pattern matching agreement
        if intent_str in self._financial_intents:
            pattern_intent_types = {m.intent_type.value for m in pattern_matches}
            if intent_str not in pattern_intent_types:
                logger.warning(
                    f"NLP callback returned financial intent '{intent_str}' "
                    f"but pattern matching did not agree. Falling back to patterns."
                )
                return None

        return nlp_result

    def _convert_nlp_result(
        self,
        nlp_result: Dict[str, Any],
        raw_message: str,
        normalized_message: str,
    ) -> ParsedIntent:
        """Convert NLP callback result to ParsedIntent."""
        # Expects nlp_result to have: intent, confidence, entities, sentiment
        intent_str = nlp_result.get("intent", "general")
        try:
            intent_type = IntentType(intent_str)
        except ValueError:
            intent_type = IntentType.GENERAL

        confidence = nlp_result.get("confidence", 0.8)

        entities: List[ExtractedEntity] = []
        for e in nlp_result.get("entities", []):
            entities.append(
                ExtractedEntity(
                    entity_type=e.get("type", "unknown"),
                    value=e.get("value"),
                    raw_text=e.get("text", ""),
                    start_pos=e.get("start", 0),
                    end_pos=e.get("end", 0),
                    confidence=e.get("confidence", 0.8),
                )
            )

        sentiment_str = nlp_result.get("sentiment", "neutral")
        try:
            sentiment = Sentiment(sentiment_str)
        except ValueError:
            sentiment = Sentiment.NEUTRAL

        return ParsedIntent(
            primary_intent=IntentMatch(
                intent_type=intent_type,
                confidence=confidence,
            ),
            entities=entities,
            sentiment=sentiment,
            raw_message=raw_message,
            normalized_message=normalized_message,
        )

    def add_pattern(self, pattern: IntentPattern) -> None:
        """
        Add a custom intent pattern.

        Args:
            pattern: The pattern to add

        Raises:
            RuntimeError: If patterns are locked after first parse() call
        """
        if self._locked:
            raise RuntimeError(
                "Cannot add patterns after parsing has started. "
                "Add all patterns before the first call to parse()."
            )

        self.patterns.append(pattern)

        # Compile regex patterns
        self._compiled_patterns.setdefault(pattern.intent_type, [])
        for p in pattern.patterns:
            try:
                self._compiled_patterns[pattern.intent_type].append(
                    re.compile(p, re.IGNORECASE)
                )
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{p}': {e}")

    def set_nlp_callback(
        self,
        callback: Callable[[str], Dict[str, Any]],
    ) -> None:
        """
        Set NLP/LLM callback for enhanced parsing.

        The callback should accept a message string and return a dict with:
        - intent: str (IntentType value)
        - confidence: float (0-1)
        - entities: List[dict] with type, value, text
        - sentiment: str (Sentiment value)

        Args:
            callback: The NLP callback function
        """
        self.nlp_callback = callback


# Convenience function for backward compatibility
def parse_buyer_intent(message: str) -> Dict[str, Any]:
    """
    Parse buyer intent from a message.

    Convenience function for backward compatibility with existing code.

    Args:
        message: The message to parse

    Returns:
        Dictionary with intent information
    """
    parser = IntentParser()
    result = parser.parse(message)
    return result.to_dict()
