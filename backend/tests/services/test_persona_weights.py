"""Tests for persona_weights module."""

from app.services.persona_weights import get_weights


def test_get_weights_founder_boosts_opportunity():
    w = get_weights("Founder")
    assert w["expiring"] > 1.0  # HIGH
    assert w["company"] > 1.0  # HIGH


def test_get_weights_vc_boosts_expiry():
    w = get_weights("VC")
    assert w["expiring"] > 1.0  # HIGH
    assert w["trend"] > 1.0  # HIGH


def test_get_weights_engineer_boosts_notable():
    w = get_weights("Engineer")
    assert w["notable"] > 1.0  # HIGH
    assert w["trend"] > 1.0  # HIGH
    assert w["expiring"] < 1.0  # LOW-MED


def test_get_weights_researcher_boosts_trend():
    w = get_weights("Researcher")
    assert w["trend"] > 1.0  # HIGH
    assert w["notable"] > 1.0  # HIGH


def test_get_weights_operator_boosts_company():
    w = get_weights("Operator")
    assert w["company"] > 1.0  # HIGH
    assert w["foryou"] > 1.0  # MED-HIGH


def test_get_weights_none_returns_all_baseline():
    w = get_weights(None)
    for k, v in w.items():
        assert v == 1.0, f"{k} should be 1.0 for None persona"


def test_get_weights_other_returns_all_baseline():
    w = get_weights("Other")
    for k, v in w.items():
        assert v == 1.0, f"{k} should be 1.0 for 'Other' persona"


def test_get_weights_unknown_returns_all_baseline():
    w = get_weights("UnknownRole")
    for k, v in w.items():
        assert v == 1.0


def test_get_weights_idempotent():
    w1 = get_weights("Founder")
    w2 = get_weights("Founder")
    assert w1 == w2


def test_get_weights_all_keys_present():
    required = {"expiring", "company", "trend", "notable", "foryou"}
    for persona in ["Founder", "VC", "Engineer", "Researcher", "Operator", "Other", None]:
        w = get_weights(persona)
        assert set(w.keys()) == required, f"Missing keys for {persona}"
