"""
Versioned prompts package.

Each prompt lives in its own ``<name>_v<version>.md`` file. The file content
is the source of truth for the prompt text and is hashed as ``prompt_hash``
at load time so any edit produces a new cache key.

Back-compat: the original ``prompts.py`` module exported ``SYSTEM_PROMPT``,
``SUMMARY_SCHEMA_DESCRIPTION``, ``USER_PROMPT_TEMPLATE`` and
``CLAIMS_EXTRACTION_PROMPT``. Those symbols are re-exported here so existing
imports keep working.
"""

from app.ai.prompts.loader import (
    PromptSpec,
    get_prompt,
    list_prompts,
    prompt_hash,
)

_summarize = get_prompt("summarize", version=1)
_claims_extraction = get_prompt("claims_extraction", version=1)

SYSTEM_PROMPT = _summarize.system
SUMMARY_SCHEMA_DESCRIPTION = _summarize.schema_description or ""
USER_PROMPT_TEMPLATE = _summarize.user_template
CLAIMS_EXTRACTION_PROMPT = _claims_extraction.user_template

__all__ = [
    "PromptSpec",
    "get_prompt",
    "list_prompts",
    "prompt_hash",
    "SYSTEM_PROMPT",
    "SUMMARY_SCHEMA_DESCRIPTION",
    "USER_PROMPT_TEMPLATE",
    "CLAIMS_EXTRACTION_PROMPT",
]
