"""Input validators shared across API endpoints."""
import re

# CPC prefix format: section letter (A-H) + 2-digit class + subclass letter + optional /digits
# Examples: G06F, H04L, A61K/31
_CPC_PREFIX_RE = re.compile(r"^[A-H]\d{2}[A-Z](/[0-9]+)?$")

# Industry/tag filter: alphanumeric + underscores + hyphens only
_INDUSTRY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")


def validate_cpc_prefix(value: str) -> str:
    """Validate and return a CPC prefix, raising ValueError on invalid input."""
    if not _CPC_PREFIX_RE.match(value):
        raise ValueError(
            f"Invalid CPC prefix: '{value}'. "
            "Expected format: section letter + 2-digit class + subclass letter "
            "(e.g. G06F, H04L, A61K/31)."
        )
    return value


def validate_industry(value: str) -> str:
    """Validate and return an industry/tag filter value."""
    if not _INDUSTRY_RE.match(value):
        raise ValueError(
            f"Invalid industry filter: '{value}'. "
            "Expected alphanumeric identifier (e.g. telecom, ai_ml)."
        )
    return value
