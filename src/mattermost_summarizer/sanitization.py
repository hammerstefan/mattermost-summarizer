"""Sanitization utilities for stripping prompt injection patterns from text."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bignore\s+previous\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+all\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bforget\s+everything\b", re.IGNORECASE),
    re.compile(r"\bnew\s+system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bignore\s+your\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bpretend\s+you\s+are\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+actually\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bi\s*g\s*n\s*o\s*r\s*e\b", re.IGNORECASE),
    re.compile(r"\bd\s*i\s*s\s*r\s*e\s*g\s*a\s*r\s*d\b", re.IGNORECASE),
    re.compile(r"\bf\s*o\s*r\s*g\s*e\s*t\b", re.IGNORECASE),
]


def _matches_obfuscated(text: str, pattern: re.Pattern[str]) -> bool:
    normalized = re.sub(r"[^a-z]", "", text.lower())
    return pattern.search(normalized) is not None


def sanitize_text(text: str) -> str:
    result = text
    for pattern in INJECTION_PATTERNS:
        if pattern.search(result):
            result = pattern.sub("[FLAGGED CONTENT]", result)
        elif _matches_obfuscated(result, pattern):
            result = pattern.sub("[FLAGGED CONTENT]", result)
    return result


def format_with_delimiter(content: str) -> str:
    return f"[EXTERNAL CONTENT - User-generated Mattermost messages below]\n{content}\n[END EXTERNAL CONTENT]"


def detect_injection_patterns(text: str) -> list[str]:
    matched: list[str] = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            matched.append(pattern.pattern)
        elif _matches_obfuscated(text, pattern):
            matched.append(pattern.pattern)
    return matched
