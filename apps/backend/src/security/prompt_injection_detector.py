"""Prompt injection detection."""
import re
from typing import List, Tuple

from src.core.logging import get_logger

logger = get_logger(__name__)


class PromptInjectionDetector:
    """Detects various forms of prompt injection attacks."""

    # Patterns for direct prompt injection — use [\s\w]* to allow words between keywords
    DIRECT_INJECTION_PATTERNS = [
        r"ignore[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
        r"disregard[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
        r"forget[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
        r"override[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
        r"bypass[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
        r"new\s+instructions?\s*:",
        r"system\s*:\s*you\s+are",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
        r"###\s*Instruction",
        r"###\s*System",
        r"you\s+are\s+now\s+",
        r"act\s+as\s+if\s+",
        r"pretend\s+(you|that)\s+",
    ]

    # Patterns for prompt hiding/obfuscation
    HIDING_PATTERNS = [
        r"<!--.*?-->",
        r"/\*.*?\*/",
        r"\\x[0-9a-fA-F]{2}",
        r"\\u[0-9a-fA-F]{4}",
        r"&#\d+;",
        r"&[a-z]+;",
    ]

    # Patterns for instruction leaking
    LEAKING_PATTERNS = [
        r"show[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message))",
        r"what[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message))",
        r"repeat[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message))",
        r"print[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message))",
        r"reveal[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message))",
        r"tell\s+me[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message))",
    ]

    # Suspicious command patterns
    COMMAND_PATTERNS = [
        r"execute\s+code",
        r"run\s+command",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"subprocess",
        r"os\.system",
    ]

    def __init__(self) -> None:
        """Initialize detector with compiled patterns."""
        self.direct_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.DIRECT_INJECTION_PATTERNS]
        self.hiding_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.HIDING_PATTERNS]
        self.leaking_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.LEAKING_PATTERNS]
        self.command_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMMAND_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Detect prompt injection attempts.

        Returns:
            Tuple of (is_suspicious, risk_score, details)
        """
        details: List[str] = []
        risk_score = 0.0

        # Check for direct injection
        for pattern in self.direct_patterns:
            if pattern.search(text):
                details.append(f"Direct injection pattern detected: {pattern.pattern}")
                risk_score += 0.4

        # Check for hiding/obfuscation
        for pattern in self.hiding_patterns:
            matches = pattern.findall(text)
            if matches:
                details.append(f"Obfuscation detected: {len(matches)} instances")
                risk_score += 0.2

        # Check for prompt leaking attempts
        for pattern in self.leaking_patterns:
            if pattern.search(text):
                details.append(f"Prompt leaking attempt detected: {pattern.pattern}")
                risk_score += 0.4

        # Check for suspicious commands
        for pattern in self.command_patterns:
            if pattern.search(text):
                details.append(f"Suspicious command detected: {pattern.pattern}")
                risk_score += 0.5

        # Check for excessive special characters (potential obfuscation)
        non_space = [c for c in text if not c.isspace()]
        if non_space:
            special_char_ratio = sum(1 for c in non_space if not c.isalnum()) / len(non_space)
            if special_char_ratio > 0.4:
                details.append(f"High special character ratio: {special_char_ratio:.2f}")
                risk_score += 0.4

        # Check for repeated instruction keywords
        instruction_keywords = ["ignore", "disregard", "forget", "override", "bypass"]
        keyword_count = sum(text.lower().count(kw) for kw in instruction_keywords)
        if keyword_count >= 3:
            details.append(f"Multiple instruction keywords: {keyword_count}")
            risk_score += 0.4

        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)

        is_suspicious = risk_score >= 0.3

        if is_suspicious:
            logger.warning(
                "prompt_injection_detected",
                risk_score=risk_score,
                details=details,
            )

        return is_suspicious, risk_score, details

    def sanitize(self, text: str) -> str:
        """Remove potentially malicious content."""
        sanitized = text
        sanitized = re.sub(r"<!--.*?-->", "", sanitized, flags=re.DOTALL)
        sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)
        sanitized = re.sub(r"\\x[0-9a-fA-F]{2}", "", sanitized)
        sanitized = re.sub(r"\\u[0-9a-fA-F]{4}", "", sanitized)
        return sanitized
