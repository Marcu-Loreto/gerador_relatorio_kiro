"""Loads agent system prompts from .prompts/ markdown files."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from src.core.logging import get_logger

logger = get_logger(__name__)

# .prompts/ lives at apps/backend/.prompts/ — two levels up from this file (src/agents/)
_PROMPTS_DIR = Path(__file__).parent.parent.parent / ".prompts"


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """
    Load a prompt from .prompts/<name>.md.

    Args:
        name: filename without extension, e.g. "analytical_summary"

    Returns:
        Prompt text. Raises FileNotFoundError if the file is missing.
    """
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(
            f"Prompt file not found: {path}. "
            f"Create apps/backend/.prompts/{name}.md to define this agent's system prompt."
        )
    text = path.read_text(encoding="utf-8").strip()
    logger.info("prompt_loaded", name=name, chars=len(text))
    return text
