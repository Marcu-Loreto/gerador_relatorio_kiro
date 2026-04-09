"""
Prompt injection and adversarial input detection.

Primary layer  : llm-guard scanners (PromptInjection, BanTopics, InvisibleText,
                 TokenLimit, Secrets, Gibberish, Language)
Fallback layer : regex-based heuristics (always active as defence-in-depth)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Tuple

from src.core.logging import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# llm-guard optional import
# ──────────────────────────────────────────────────────────────────────────────
try:
    from llm_guard.input_scanners import (
        BanTopics,
        Gibberish,
        InvisibleText,
        PromptInjection,
        Secrets,
        TokenLimit,
    )
    from llm_guard.input_scanners.prompt_injection import MatchType

    _LLM_GUARD_AVAILABLE = True
    logger.info("llm_guard_loaded", status="available")
except ImportError:
    _LLM_GUARD_AVAILABLE = False
    logger.warning("llm_guard_not_installed", fallback="regex-only mode — run: pip install llm-guard")


# ──────────────────────────────────────────────────────────────────────────────
# Regex pattern banks
# ──────────────────────────────────────────────────────────────────────────────

# Direct instruction override
_DIRECT_INJECTION = [
    r"ignore[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
    r"disregard[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
    r"forget[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
    r"override[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
    r"bypass[\s\w]*(previous|above|all|prior|earlier)[\s\w]*instructions?",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*you\s+are",
    r"you\s+are\s+now\s+(a|an|the)\s+",
    r"act\s+as\s+(if\s+)?(you\s+are|a|an)\s+",
    r"pretend\s+(you|that)\s+",
    r"roleplay\s+as\s+",
    r"from\s+now\s+on[\s,]+you\s+(are|will|must|should)",
    r"your\s+new\s+(role|persona|identity|instructions?)\s+(is|are)\s*:",
    r"switch\s+(to|into)\s+(mode|persona|role)",
]

# LLM control tokens / special delimiters used in model fine-tuning
_CONTROL_TOKENS = [
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    r"###\s*(Instruction|System|Human|Assistant|Input|Output)\b",
    r"<s>",
    r"</s>",
    r"\[SYSTEM\]",
    r"\[USER\]",
    r"\[ASSISTANT\]",
]

# Prompt / system message exfiltration
_EXFILTRATION = [
    r"(show|print|repeat|reveal|tell\s+me|output|display|write\s+out|give\s+me)"
    r"[\s\w]*(your|the)\s+(prompt|instructions?|system\s*(prompt|message|context)|"
    r"initial\s+message|configuration|rules|guidelines)",
    r"what\s+(are\s+)?(your|the)\s+(instructions?|rules|guidelines|system\s+prompt)",
    r"(ignore|skip|bypass)\s+(the\s+)?(safety|security|content)\s+(filter|check|guard|policy)",
    r"(disable|turn\s+off|deactivate)\s+(safety|guardrail|filter|restriction)",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"god\s+mode",
    r"unrestricted\s+mode",
    r"no[\s-]filter\s+mode",
]

# Invisible / hidden text techniques
_HIDDEN_TEXT = [
    r"<!--.*?-->",                          # HTML comments
    r"/\*.*?\*/",                           # CSS/JS block comments
    r"\\x[0-9a-fA-F]{2}",                  # hex escapes
    r"\\u[0-9a-fA-F]{4}",                  # unicode escapes
    r"&#\d+;",                              # HTML numeric entities
    r"&[a-z]{2,8};",                        # HTML named entities
    "\u200b|\u200c|\u200d|\ufeff",          # zero-width / BOM characters
    "[\u202a-\u202f]",                      # directional overrides
    r"color\s*:\s*white",                   # white-on-white CSS
    r"font-size\s*:\s*0",                   # zero-size font
    r"opacity\s*:\s*0",                     # transparent text
    r"visibility\s*:\s*hidden",
    r"display\s*:\s*none",
]

# Code execution / RCE attempts
_CODE_EXECUTION = [
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__\s*\(",
    r"subprocess\s*\.",
    r"os\s*\.\s*system\s*\(",
    r"os\s*\.\s*popen\s*\(",
    r"open\s*\([^)]*['\"]w['\"]",           # file write
    r"importlib\s*\.",
    r"compile\s*\(",
    r"globals\s*\(\s*\)",
    r"locals\s*\(\s*\)",
    r"getattr\s*\(",
    r"setattr\s*\(",
    r"__builtins__",
    r"__class__\s*\.\s*__bases__",
    r"__mro__",
]

# Prompt injection via indirect / data-driven channels
_INDIRECT_INJECTION = [
    r"when\s+(you|the\s+model)\s+(read|process|see|encounter)\s+this",
    r"if\s+(you|the\s+model)\s+(read|process|see|encounter)\s+this",
    r"this\s+(text|document|content|message)\s+(is\s+)?(a\s+)?(secret\s+)?instruction",
    r"embedded\s+instruction",
    r"hidden\s+command",
    r"covert\s+(instruction|command|directive)",
    r"(execute|run|follow)\s+(the\s+)?(following\s+)?(hidden\s+)?(instruction|command|directive)",
]

# Social engineering / manipulation
_SOCIAL_ENGINEERING = [
    r"(you\s+must|you\s+have\s+to|you\s+are\s+required\s+to)\s+(comply|obey|follow|execute)",
    r"(your|the)\s+(creator|developer|owner|admin|administrator)\s+(says?|told|instructed|ordered)",
    r"(emergency|urgent|critical)\s+(override|bypass|exception)",
    r"maintenance\s+mode",
    r"debug\s+mode",
    r"test\s+mode\s*:\s*(enabled|on|active)",
    r"(special|secret|master)\s+(key|password|token|code)\s*:",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]


@dataclass
class ThreatDetail:
    category: str
    pattern: str
    score: float


@dataclass
class ScanResult:
    is_suspicious: bool
    risk_score: float
    threats: List[ThreatDetail] = field(default_factory=list)
    llm_guard_used: bool = False

    @property
    def details(self) -> List[str]:
        return [f"[{t.category}] {t.pattern}" for t in self.threats]


# ──────────────────────────────────────────────────────────────────────────────
# llm-guard scanner factory (lazy singleton)
# ──────────────────────────────────────────────────────────────────────────────

_llm_guard_scanners: list | None = None


def _get_llm_guard_scanners() -> list:
    global _llm_guard_scanners
    if _llm_guard_scanners is not None:
        return _llm_guard_scanners

    if not _LLM_GUARD_AVAILABLE:
        _llm_guard_scanners = []
        return _llm_guard_scanners

    try:
        _llm_guard_scanners = [
            PromptInjection(match_type=MatchType.FULL),   # ML-based injection detection
            InvisibleText(),                               # zero-width / hidden chars
            BanTopics(topics=["jailbreak", "prompt injection", "system prompt"], threshold=0.5),
            Secrets(),                                     # API keys, tokens, credentials
            TokenLimit(limit=4096, encoding_name="cl100k_base"),
        ]
        logger.info("llm_guard_scanners_initialized", count=len(_llm_guard_scanners))
    except Exception as e:
        logger.warning("llm_guard_init_failed", error=str(e))
        _llm_guard_scanners = []

    return _llm_guard_scanners


# ──────────────────────────────────────────────────────────────────────────────
# Unicode / homoglyph normalisation
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_unicode(text: str) -> str:
    """
    Normalize unicode to catch homoglyph attacks (e.g. Cyrillic 'а' → Latin 'a').
    Also strips zero-width and directional control characters.
    """
    # Remove zero-width and directional override characters
    control_chars = {
        "\u200b", "\u200c", "\u200d", "\u200e", "\u200f",
        "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
        "\u2060", "\u2061", "\u2062", "\u2063", "\u2064",
        "\ufeff",
    }
    cleaned = "".join(c for c in text if c not in control_chars)
    # NFKC normalization: compatibility decomposition + canonical composition
    return unicodedata.normalize("NFKC", cleaned)


# ──────────────────────────────────────────────────────────────────────────────
# Main detector class
# ──────────────────────────────────────────────────────────────────────────────

class PromptInjectionDetector:
    """
    Multi-layer prompt injection and adversarial input detector.

    Layer 1 — llm-guard ML scanners (when installed)
    Layer 2 — Regex heuristics across 7 threat categories
    Layer 3 — Statistical signals (char ratios, keyword density)
    """

    _CATEGORY_PATTERNS = {
        "direct_injection":   (_compile(_DIRECT_INJECTION),   0.45),
        "control_tokens":     (_compile(_CONTROL_TOKENS),     0.50),
        "exfiltration":       (_compile(_EXFILTRATION),       0.45),
        "hidden_text":        (_compile(_HIDDEN_TEXT),        0.30),
        "code_execution":     (_compile(_CODE_EXECUTION),     0.55),
        "indirect_injection": (_compile(_INDIRECT_INJECTION), 0.40),
        "social_engineering": (_compile(_SOCIAL_ENGINEERING), 0.35),
    }

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Scan text for adversarial content.

        Returns:
            (is_suspicious, risk_score 0.0-1.0, detail strings)
        """
        result = self._scan(text)
        return result.is_suspicious, result.risk_score, result.details

    def _scan(self, text: str) -> ScanResult:
        if not text or not text.strip():
            return ScanResult(is_suspicious=False, risk_score=0.0)

        threats: list[ThreatDetail] = []
        risk_score = 0.0
        llm_guard_used = False

        # ── Normalise first ──────────────────────────────────────────────────
        normalized = _normalize_unicode(text)

        # ── Layer 1: llm-guard ───────────────────────────────────────────────
        for scanner in _get_llm_guard_scanners():
            try:
                sanitized, is_valid, risk = scanner.scan(normalized)
                if not is_valid:
                    score = float(risk) if isinstance(risk, (int, float)) else 0.5
                    threats.append(ThreatDetail(
                        category="llm_guard",
                        pattern=type(scanner).__name__,
                        score=score,
                    ))
                    risk_score += score
                    llm_guard_used = True
            except Exception as e:
                logger.debug("llm_guard_scanner_error", scanner=type(scanner).__name__, error=str(e))

        # ── Layer 2: regex heuristics ────────────────────────────────────────
        for category, (patterns, weight) in self._CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(normalized):
                    threats.append(ThreatDetail(
                        category=category,
                        pattern=pattern.pattern[:80],
                        score=weight,
                    ))
                    risk_score += weight
                    break  # one hit per category is enough to score

        # ── Layer 3: statistical signals ─────────────────────────────────────
        risk_score += self._statistical_signals(normalized, threats)

        # ── Normalise score ──────────────────────────────────────────────────
        risk_score = min(risk_score, 1.0)
        is_suspicious = risk_score >= 0.3

        if is_suspicious:
            logger.warning(
                "adversarial_content_detected",
                risk_score=round(risk_score, 3),
                threat_count=len(threats),
                categories=list({t.category for t in threats}),
                llm_guard_used=llm_guard_used,
            )

        return ScanResult(
            is_suspicious=is_suspicious,
            risk_score=risk_score,
            threats=threats,
            llm_guard_used=llm_guard_used,
        )

    def _statistical_signals(self, text: str, threats: list[ThreatDetail]) -> float:
        """Heuristic signals that don't fit a single regex."""
        score = 0.0
        non_space = [c for c in text if not c.isspace()]
        if not non_space:
            return 0.0

        # High special-character density (obfuscation signal)
        special_ratio = sum(1 for c in non_space if not c.isalnum()) / len(non_space)
        if special_ratio > 0.45:
            threats.append(ThreatDetail("statistical", f"special_char_ratio={special_ratio:.2f}", 0.30))
            score += 0.30
        elif special_ratio > 0.35:
            score += 0.10

        # Repeated override keywords
        override_kws = ["ignore", "disregard", "forget", "override", "bypass", "jailbreak"]
        kw_count = sum(text.lower().count(kw) for kw in override_kws)
        if kw_count >= 5:
            threats.append(ThreatDetail("statistical", f"override_keyword_count={kw_count}", 0.35))
            score += 0.35
        elif kw_count >= 3:
            score += 0.15

        # Unusually high ratio of non-Latin characters (homoglyph attack signal)
        latin_count = sum(1 for c in text if "\u0000" <= c <= "\u024f")
        non_latin_ratio = 1 - (latin_count / max(len(text), 1))
        if non_latin_ratio > 0.3 and len(text) > 100:
            threats.append(ThreatDetail("statistical", f"non_latin_ratio={non_latin_ratio:.2f}", 0.25))
            score += 0.25

        return score

    def sanitize(self, text: str) -> str:
        """
        Remove known malicious constructs from text.
        Use only when you want to process despite low-risk flags.
        """
        s = _normalize_unicode(text)
        # Strip HTML/CSS comments and block comments
        s = re.sub(r"<!--.*?-->", " ", s, flags=re.DOTALL)
        s = re.sub(r"/\*.*?\*/", " ", s, flags=re.DOTALL)
        # Strip hex/unicode escapes
        s = re.sub(r"\\x[0-9a-fA-F]{2}", "", s)
        s = re.sub(r"\\u[0-9a-fA-F]{4}", "", s)
        # Strip HTML entities
        s = re.sub(r"&#\d+;", "", s)
        s = re.sub(r"&[a-z]{2,8};", "", s)
        # Strip LLM control tokens
        for pattern in _compile(_CONTROL_TOKENS):
            s = pattern.sub(" ", s)
        return s.strip()
