"""
Prompt file loader + hash.

Prompt files live next to this module as Markdown with a simple
front-matter-free sectioned format:

    # SYSTEM
    <system prompt text>

    # SCHEMA
    <optional schema description block>

    # USER
    <user template text with {placeholders}>

``prompt_hash`` is a deterministic SHA-256 of the raw file bytes, so any
whitespace or wording change creates a new cache key and forces a
regeneration (see ``app.ai.llm_client``).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent
_SECTION_RE = re.compile(r"^#\s+(SYSTEM|USER|SCHEMA)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class PromptSpec:
    name: str
    version: int
    system: str
    user_template: str
    schema_description: str | None
    prompt_hash: str
    source_path: Path

    @property
    def version_label(self) -> str:
        return f"v{self.version}"


def _parse_sections(raw: str) -> tuple[str, str, str | None]:
    """Parse a prompt markdown file into (system, user, schema)."""
    parts = _SECTION_RE.split(raw)
    # parts[0] is anything before first section (discarded)
    sections: dict[str, str] = {}
    it = iter(parts[1:])
    for header, body in zip(it, it, strict=False):
        sections[header] = body.strip()
    system = sections.get("SYSTEM", "").strip()
    user = sections.get("USER", "").strip()
    schema = sections.get("SCHEMA")
    schema = schema.strip() if schema else None
    if not system or not user:
        raise ValueError(
            f"Prompt file must contain '# SYSTEM' and '# USER' sections; "
            f"got sections: {list(sections.keys())}"
        )
    return system, user, schema


@lru_cache(maxsize=64)
def get_prompt(name: str, version: int = 1) -> PromptSpec:
    """Load a prompt by name + version. Result is cached in-process."""
    filename = f"{name}_v{version}.md"
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    raw_bytes = path.read_bytes()
    raw_text = raw_bytes.decode("utf-8")
    system, user, schema = _parse_sections(raw_text)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return PromptSpec(
        name=name,
        version=version,
        system=system,
        user_template=user,
        schema_description=schema,
        prompt_hash=digest,
        source_path=path,
    )


def list_prompts() -> list[tuple[str, int]]:
    """Return all available (name, version) prompts found on disk."""
    out: list[tuple[str, int]] = []
    pattern = re.compile(r"^(?P<name>[a-z_]+)_v(?P<version>\d+)\.md$")
    for f in sorted(_PROMPTS_DIR.glob("*.md")):
        m = pattern.match(f.name)
        if m:
            out.append((m["name"], int(m["version"])))
    return out


def prompt_hash(name: str, version: int = 1) -> str:
    """Convenience wrapper returning just the hash for a given prompt."""
    return get_prompt(name, version).prompt_hash
