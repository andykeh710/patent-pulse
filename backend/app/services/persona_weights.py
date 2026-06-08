"""Persona-aware briefing ranking weights.

Provides get_weights(persona) → dict[str, float] mapping briefing
signal types to rank-boost multipliers.

Per Andy's spec (Phase 2 PR 3):
  HIGH = 1.5x, MED-HIGH = 1.25x, MED = 1.0x (baseline),
  LOW-MED = 0.8x, LOW = 0.6x

Weights are multipliers applied to existing scores — they soft-boost
or de-emphasise, never hard-filter. Persons=None or "Other" returns
all 1.0 (identity — fully backward compatible).

Signal type mapping (Andy's names → briefing types):
  opportunity / expiry → expiring
  company_moves         → company
  filing_spikes / trends → trend
  notable_patents       → notable
  themes / technical    → foryou
"""

# ── Per-persona weight definitions ────────────────────────────────

# Qualitative → multiplier
_HIGH = 1.5
_MED_HIGH = 1.25
_MED = 1.0
_LOW_MED = 0.8
_LOW = 0.6

_PERSONA_WEIGHTS: dict[str, dict[str, float]] = {
    "Founder": {
        "expiring": _HIGH,
        "company": _HIGH,
        "trend": _MED_HIGH,
        "notable": _MED,
        "foryou": _MED,
    },
    "VC": {
        "expiring": _HIGH,
        "company": _HIGH,
        "trend": _HIGH,
        "notable": _MED,
        "foryou": _LOW_MED,
    },
    "Engineer": {
        "expiring": _LOW_MED,
        "company": _MED,
        "trend": _HIGH,
        "notable": _HIGH,
        "foryou": _MED_HIGH,
    },
    "Researcher": {
        "expiring": _LOW_MED,
        "company": _MED,
        "trend": _HIGH,
        "notable": _HIGH,
        "foryou": _MED,
    },
    "Operator": {
        "expiring": _MED,
        "company": _HIGH,
        "trend": _MED,
        "notable": _MED,
        "foryou": _MED_HIGH,
    },
}

# ── Public API ─────────────────────────────────────────────────────


def get_weights(persona: str | None) -> dict[str, float]:
    """Return a rank-boost multiplier dict for the given persona.

    Returns all 1.0 for None, "Other", or unknown persona strings.
    """
    if persona is None or persona == "Other":
        return {"expiring": 1.0, "company": 1.0, "trend": 1.0,
                "notable": 1.0, "foryou": 1.0}
    return _PERSONA_WEIGHTS.get(persona, {
        "expiring": 1.0, "company": 1.0, "trend": 1.0,
        "notable": 1.0, "foryou": 1.0,
    })
