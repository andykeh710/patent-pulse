"""Deterministic expiry assessment engine.

Produces an ExpiryAssessment payload from a PatentPublication record
and optional family-member context. No LLM — pure rules.

The default ``EXPIRING_SOON_WINDOW_DAYS`` is conservative: patents
estimated to expire within 3 years are flagged for attention. This
can be tightened later with settings-based configuration.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.models import PatentPublication

# ── tunable thresholds ──────────────────────────────────────────────
EXPIRING_SOON_WINDOW_DAYS: int = 365 * 3  # 3 years
# ────────────────────────────────────────────────────────────────────

ALLOWED_STATUSES = {
    "active_estimated",
    "expiring_soon",
    "expired_estimated",
    "lapsed_possible",
    "lapsed_confirmed",
    "expired_confirmed",
    "unknown",
}

ALLOWED_CONFIDENCE = {"low", "medium", "high", "confirmed"}

# Legal statuses we consider "likely granted" for expiry estimation.
_GRANT_LIKE_STATUSES = {"GRANTED", "ACTIVE", "ISSUED", "IN FORCE"}

# Maintenance statuses suggesting an active (fee-paid) patent.
_ACTIVE_MAINTENANCE = {"PAID", "CURRENT", "ACTIVE", "GRANTED"}

# Maintenance statuses that suggest lapse or abandonment.
_LAPSED_MAINTENANCE = {
    "LAPSED",
    "EXPIRED",
    "ABANDONED",
    "CANCELLED",
    "WITHDRAWN",
    "REVOKED",
    "CEASED",
}


def compute_expiry_assessment(
    patent: PatentPublication,
    *,
    family_members: list[str] | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Produce a deterministic expiry assessment for a single patent.

    Args:
        patent: The source patent record.
        family_members: Optional list of family publication numbers.
            If not provided, ``patent.family_members`` is used.
        as_of_date: Reference date for "now". Defaults to ``date.today()``.

    Returns:
        A dict suitable for creating or updating an ExpiryAssessment row.
        Keys: estimated_expiry_date, expiry_status, expiry_status_confidence,
        maintenance_status, maintenance_status_source, active_family_risk,
        active_family_risk_reason, terminal_disclaimer_flag,
        patent_term_adjustment_days, legal_caveats, assessment_json.
    """
    today = as_of_date or date.today()
    family = family_members if family_members is not None else (patent.family_members or [])

    # ── 1. Determine estimated expiry date ──────────────────────────
    estimated = patent.estimated_expiry_date
    maintenance_raw = patent.maintenance_status

    # ── 2. Maintenance status normalization ─────────────────────────
    maintenance_normalized = _normalize_maintenance(maintenance_raw)
    maintenance_source = "patent_publications.maintenance_status" if maintenance_raw else None

    # ── 3. Expiry status ────────────────────────────────────────────
    if estimated is None:
        status = "unknown"
    elif maintenance_normalized == "lapsed_confirmed":
        status = "lapsed_confirmed"
    elif maintenance_normalized == "expired_confirmed":
        status = "expired_confirmed"
    elif estimated <= today:
        status = "expired_estimated"
    elif estimated <= today + timedelta(days=EXPIRING_SOON_WINDOW_DAYS):
        status = "expiring_soon"
    else:
        status = "active_estimated"

    # ── 4. Confidence ───────────────────────────────────────────────
    confidence = _compute_confidence(
        patent=patent,
        status=status,
        has_maintenance_data=maintenance_raw is not None,
        has_expiry_date=estimated is not None,
        has_family_data=len(family) > 0,
        has_grant_date=patent.grant_date is not None,
    )

    # ── 5. Active family risk ───────────────────────────────────────
    family_risk, family_reason = _assess_family_risk(
        patent=patent,
        family=family,
        status=status,
    )

    # ── 6. Legal caveats ────────────────────────────────────────────
    caveats = _build_caveats(
        status=status,
        confidence=confidence,
        family_risk=family_risk,
        has_maintenance_data=maintenance_raw is not None,
        has_legal_status_confidence=(patent.legal_status_confidence == "confirmed"),
    )

    # ── 7. Assemble ─────────────────────────────────────────────────
    return {
        "estimated_expiry_date": estimated,
        "expiry_status": status,
        "expiry_status_confidence": confidence,
        "maintenance_status": maintenance_normalized,
        "maintenance_status_source": maintenance_source,
        "active_family_risk": family_risk,
        "active_family_risk_reason": family_reason,
        "terminal_disclaimer_flag": False,
        "patent_term_adjustment_days": None,
        "legal_caveats": caveats,
        "assessment_json": {
            "source": "deterministic",
            "version": 1,
            "window_days": EXPIRING_SOON_WINDOW_DAYS,
            "as_of_date": today.isoformat(),
            "input_summary": {
                "has_estimated_expiry": estimated is not None,
                "has_grant_date": patent.grant_date is not None,
                "has_filing_date": patent.filing_date is not None,
                "has_maintenance_status": maintenance_raw is not None,
                "family_member_count": len(family),
                "legal_status": patent.legal_status,
                "legal_status_confidence": patent.legal_status_confidence,
            },
        },
    }


# ══════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════


def _normalize_maintenance(raw: str | None) -> str:
    """Map raw maintenance_status to a canonical label or 'unknown'."""
    if not raw:
        return "unknown"
    upper = raw.strip().upper()
    if upper in _ACTIVE_MAINTENANCE:
        return "active"
    if upper in _LAPSED_MAINTENANCE:
        if upper in ("EXPIRED",):
            return "expired_confirmed"
        return "lapsed_confirmed"
    return "unknown"


def _compute_confidence(
    *,
    patent: PatentPublication,
    status: str,
    has_maintenance_data: bool,
    has_expiry_date: bool,
    has_family_data: bool,
    has_grant_date: bool,
) -> str:
    """Assign confidence level based on data completeness and signal quality."""
    if status == "unknown":
        return "low"

    # Confirmed statuses (with real maintenance-fee data) are the highest tier.
    if status in ("lapsed_confirmed", "expired_confirmed") and has_maintenance_data:
        return "confirmed"

    # If legal_status_confidence is "confirmed" (INPADOC reconciliation done),
    # that is a strong signal.
    if patent.legal_status_confidence == "confirmed":
        if has_expiry_date and has_grant_date:
            return "high"
        return "medium"

    # Estimated expiry date exists, and we have the grant date needed to
    # compute it = reasonable confidence.
    if has_expiry_date and has_grant_date:
        return "medium"

    # Estimated expiry date exists but no grant date — the estimate is
    # less reliable (may be filing-based, which is weaker).
    if has_expiry_date:
        return "low"

    return "low"


def _assess_family_risk(
    *,
    patent: PatentPublication,
    family: list[str],
    status: str,
) -> tuple[bool, str | None]:
    """Determine whether active family members pose a risk.

    The current implementation uses a heuristic: if the patent appears
    expired/expiring but has family members beyond itself, there *may*
    be active family members in other jurisdictions. This is a
    conservative flag — it errs on the side of warning the user.

    Future versions will cross-reference actual family legal status
    from the family members table.
    """
    # If the patent has family members beyond just itself, flag risk.
    # Remove duplicates and count unique family members.
    unique_family = list(set(f for f in family if f))
    self_in_family = patent.publication_number in unique_family or patent.doc_id in unique_family

    effective_count = len(unique_family)
    if self_in_family and effective_count > 1:
        pass  # has at least one other family member
    elif not self_in_family and effective_count > 0:
        pass  # has family members (just not itself listed — still a risk)

    if effective_count > 1 or (effective_count == 1 and not self_in_family):
        # Only flag risk if this patent's status looks expired/expiring.
        # An active patent with a large family is not a "risk" — it's normal.
        if status in (
            "expired_estimated",
            "expiring_soon",
            "lapsed_possible",
            "lapsed_confirmed",
            "expired_confirmed",
            "unknown",
        ):
            return True, (
                f"This patent has {effective_count} family member(s). "
                f"Active family members in other jurisdictions may still "
                f"be enforceable. Verify family status before relying on "
                f"expiry in your jurisdiction."
            )
    return False, None


def _build_caveats(
    *,
    status: str,
    confidence: str,
    family_risk: bool,
    has_maintenance_data: bool,
    has_legal_status_confidence: bool,
) -> list[str]:
    """Build the list of legal caveats for this assessment."""
    caveats: list[str] = []

    # Status-specific caveats.
    if status == "expired_estimated":
        caveats.append(
            "Expiry is estimated — not confirmed by official register. "
            "Verify with the patent office before relying on this status."
        )
    elif status == "expiring_soon":
        caveats.append(
            "Expiry date is estimated. The actual expiry may differ due to "
            "patent term adjustments, terminal disclaimers, or maintenance "
            "fee status. Confirm with official records."
        )
    elif status == "unknown":
        caveats.append(
            "Expiry cannot be determined. The patent is missing a filing "
            "date, grant date, or estimated expiry date. Without these, "
            "no expiry assessment is possible."
        )

    # Confidence caveats.
    if confidence == "low":
        caveats.append(
            "Low confidence. Key data (maintenance fees, grant date, or "
            "legal status confirmation) is missing. Treat this assessment "
            "as a starting point, not a definitive determination."
        )
    elif confidence == "medium":
        caveats.append(
            "Medium confidence. Some data is estimated rather than confirmed. "
            "Cross-check with official patent office records."
        )

    # Family risk caveat.
    if family_risk:
        caveats.append(
            "Active family risk: related patents in other jurisdictions or "
            "family members may still be enforceable. Do not assume global "
            "expiry based on this single patent's status."
        )

    # Maintenance data caveat.
    if not has_maintenance_data:
        caveats.append(
            "Maintenance fee status is unknown. This patent may have lapsed "
            "due to unpaid fees. Check the patent office fee register."
        )

    # Legal status confidence caveat.
    if not has_legal_status_confidence:
        caveats.append(
            "Legal status has not been confirmed against official registers. "
            "The status shown may differ from the current legal reality."
        )

    return caveats


# ══════════════════════════════════════════════════════════════════════
# Expiry opportunity scoring (Sprint 2B — deterministic, not LLM)
# ══════════════════════════════════════════════════════════════════════


def compute_expiry_opportunity_score(
    patent: PatentPublication,
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """Compute a deterministic expiry-specific opportunity score (0–100).

    This is separate from the general ``opportunity_score``. It measures
    how *valuable* this patent is for expiry-driven opportunity discovery:
    expired/expiring status, data confidence, commercial relevance, and
    legal clarity.

    Args:
        patent: The source patent record (for opportunity_score, claims, etc.).
        assessment: Result from ``compute_expiry_assessment()``.

    Returns:
        Dict with ``score`` (float, 0–100) and ``breakdown`` with component
        scores for transparency.
    """
    status = assessment["expiry_status"]
    confidence = assessment["expiry_status_confidence"]
    family_risk = assessment["active_family_risk"]
    has_claims = bool(patent.claims_text)
    base_opp = patent.opportunity_score or 0.0

    # ── component scoring ──────────────────────────────────────────

    # 1. Expiry status (0–30): expired/expiring patents are the most interesting.
    status_scores = {
        "expired_confirmed": 30,
        "lapsed_confirmed": 28,
        "expired_estimated": 22,
        "lapsed_possible": 20,
        "expiring_soon": 18,
        "active_estimated": 5,
        "unknown": 0,
    }
    status_component = status_scores.get(status, 0)

    # 2. Confidence multiplier (0.3–1.0): confirmed = full value, low = 30%.
    confidence_mult = {
        "confirmed": 1.0,
        "high": 0.85,
        "medium": 0.65,
        "low": 0.30,
    }
    conf_mult = confidence_mult.get(confidence, 0.30)
    confidence_component = status_component * conf_mult

    # 3. Base opportunity alignment (0–20): how commercially relevant the
    #    patent already is, normalized from the 0–100 opportunity_score.
    base_opp_component = min(base_opp * 0.20, 20.0)

    # 4. Active family risk penalty (0–15): active family members reduce
    #    the "safe to investigate" appeal. Heavier penalty for low confidence.
    if family_risk:
        if confidence in ("low", "medium"):
            family_penalty = 15.0
        else:
            family_penalty = 8.0
    else:
        family_penalty = 0.0

    # 5. Claims availability (0–10): patents with claims text are more
    #    actionable — you can understand what's actually covered.
    claims_component = 10.0 if has_claims else 0.0

    # 6. Legal uncertainty penalty (0–10): if confidence is low or medium,
    #    and legal status isn't confirmed, penalize.
    if confidence == "low":
        legal_penalty = 10.0
    elif confidence == "medium":
        legal_penalty = 5.0
    else:
        legal_penalty = 0.0

    # ── assemble ────────────────────────────────────────────────────

    raw = (
        confidence_component
        + base_opp_component
        - family_penalty
        + claims_component
        - legal_penalty
    )
    score = max(0.0, min(100.0, round(raw, 1)))

    return {
        "score": score,
        "breakdown": {
            "status_component": status_component,
            "confidence_multiplier": conf_mult,
            "confidence_component": round(confidence_component, 1),
            "base_opportunity_component": round(base_opp_component, 1),
            "family_risk_penalty": family_penalty,
            "claims_component": claims_component,
            "legal_uncertainty_penalty": legal_penalty,
            "raw": round(raw, 1),
            "score": score,
        },
    }
