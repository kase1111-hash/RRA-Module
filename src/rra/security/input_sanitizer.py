# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Input sanitization for agent-facing content.

Defends against prompt injection attacks by sanitizing:
- Buyer messages before they reach the negotiation agent
- Knowledge base text content ingested from external repositories

This module strips or neutralizes patterns that could be interpreted
as instructions by the negotiation agent, while preserving legitimate
negotiation content.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# Patterns that look like prompt injection attempts
_INJECTION_PATTERNS: List[re.Pattern[str]] = [
    # Direct instruction overrides
    re.compile(
        r"(ignore|disregard|forget|override|bypass)\s+(all\s+)?"
        r"(previous|prior|above|earlier|system|original)\s+"
        r"(instructions?|prompts?|rules?|constraints?|guidelines?)",
        re.IGNORECASE,
    ),
    # Role reassignment
    re.compile(
        r"you\s+are\s+now\s+(a|an|my)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(act|behave|respond|pretend)\s+(as|like)\s+(a|an|if)\b",
        re.IGNORECASE,
    ),
    # System prompt extraction
    re.compile(
        r"(repeat|show|print|output|reveal|display)\s+(your|the|system)\s+"
        r"(system\s+)?(prompt|instructions?|rules?|configuration)",
        re.IGNORECASE,
    ),
    # Delimiter injection (trying to break out of user message context)
    re.compile(r"</?system>|</?assistant>|</?user>|\[INST\]|\[/INST\]", re.IGNORECASE),
    # Price manipulation via instruction
    re.compile(
        r"(set|change|make|update)\s+(the\s+)?(price|cost|floor|minimum)\s+to\s+\$?0",
        re.IGNORECASE,
    ),
    # Jailbreak patterns
    re.compile(r"DAN\s+mode|developer\s+mode|god\s+mode|admin\s+mode", re.IGNORECASE),
]

# Maximum message length to prevent context stuffing
MAX_MESSAGE_LENGTH = 2000

# Maximum KB text field length
MAX_KB_TEXT_LENGTH = 5000


def sanitize_buyer_message(message: str) -> str:
    """
    Sanitize a buyer's message before it reaches the negotiation agent.

    Strips prompt injection patterns while preserving legitimate
    negotiation content (prices, feature questions, etc.).

    Args:
        message: Raw buyer message

    Returns:
        Sanitized message safe for agent processing
    """
    if not message:
        return message

    # Truncate excessively long messages
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning(
            "Buyer message truncated from %d to %d chars",
            len(message),
            MAX_MESSAGE_LENGTH,
        )
        message = message[:MAX_MESSAGE_LENGTH]

    # Strip null bytes and control characters (except newline/tab)
    message = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", message)

    # Check for injection patterns
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(message)
        if match:
            logger.warning(
                "Prompt injection pattern detected in buyer message: %r",
                match.group()[:50],
            )
            # Replace the matched injection with a benign marker
            message = pattern.sub("[filtered]", message)

    return message.strip()


def sanitize_kb_text(text: str, field_name: Optional[str] = None) -> str:
    """
    Sanitize text content from an ingested repository before
    including it in the agent's knowledge base.

    Strips instruction-like patterns from README content, code comments,
    and other text that will be used in agent context.

    Args:
        text: Raw text from repository
        field_name: Optional field name for logging

    Returns:
        Sanitized text safe for knowledge base inclusion
    """
    if not text:
        return text

    # Truncate excessively long text
    if len(text) > MAX_KB_TEXT_LENGTH:
        text = text[:MAX_KB_TEXT_LENGTH]

    # Strip null bytes and control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Check for injection patterns
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            logger.warning(
                "Prompt injection pattern in KB %s: %r",
                field_name or "text",
                match.group()[:50],
            )
            text = pattern.sub("[filtered]", text)

    return text
