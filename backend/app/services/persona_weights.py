"""Persona-aware briefing weights (Phase 2 PR 3 will wire these).

These constants define how Today briefing content is weighted per
user persona. They are saved here as a reference for the implementer
of PR 3, which will read these dicts and apply them to the briefing
ranking pipeline.

Currently unused — this file exists so PR 3 can import the weights
without reverse-engineering them from the PR spec.
"""

# ── Content weighting per persona ─────────────────────────────────
# Each value is a float 0-1 representing the proportion of briefing
# content dedicated to that section. Must sum to 1.0.

INVESTOR_WEIGHTS = {
    "expiry_opportunities": 0.40,
    "company_moves": 0.30,
    "trends": 0.20,
    "notable_patents": 0.10,
}

OPERATOR_WEIGHTS = {
    "company_moves": 0.40,
    "trends": 0.30,
    "notable_patents": 0.20,
    "expiry_opportunities": 0.10,
}

CURIOUS_WEIGHTS = {
    "trends": 0.25,
    "company_moves": 0.25,
    "notable_patents": 0.25,
    "expiry_opportunities": 0.25,
}
