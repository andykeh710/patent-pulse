"""Tests for health endpoint probes (PR11)."""

import pytest


@pytest.mark.asyncio(loop_scope="function")
async def test_health_returns_all_probes(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "db" in data
    assert "redis" in data
    assert "resend" in data
    assert "overall" in data


@pytest.mark.asyncio(loop_scope="function")
async def test_health_db_unreachable_reported(client, monkeypatch):
    async def failing_db(db):
        return "unreachable"
    monkeypatch.setattr("app.api.health._check_db", failing_db)
    r = await client.get("/health")
    assert r.json()["db"] == "unreachable"
    assert r.json()["overall"] == "degraded"


@pytest.mark.asyncio(loop_scope="function")
async def test_health_resend_dev_preview_in_dev_mode(client, monkeypatch):
    # Test settings run in email_send_mode="dev": Resend is not used for
    # delivery, so the probe must report "dev_preview" and NOT degrade overall.
    monkeypatch.setattr("app.api.health.settings.email_send_mode", "dev")
    r = await client.get("/health")
    data = r.json()
    assert data["resend"] == "dev_preview"
    assert data["overall"] == "ok"


@pytest.mark.asyncio(loop_scope="function")
async def test_health_resend_disabled_when_key_unset_in_production(client, monkeypatch):
    monkeypatch.setattr("app.api.health.settings.email_send_mode", "production")
    monkeypatch.setattr("app.api.health.settings.resend_api_key", "")
    r = await client.get("/health")
    data = r.json()
    assert data["resend"] == "disabled"
    # "disabled" is a deliberate config, not a failure.
    assert data["overall"] == "ok"


@pytest.mark.asyncio(loop_scope="function")
async def test_health_overall_ok_when_services_ok(client, monkeypatch):
    # Regression: alembic_head (a revision string) must not pin overall to
    # "degraded". With healthy services + dev_preview email, overall is "ok".
    monkeypatch.setattr("app.api.health.settings.email_send_mode", "dev")
    r = await client.get("/health")
    data = r.json()
    assert data["db"] == "ok"
    assert data["overall"] == "ok"
    assert data["alembic_head"]  # informational, present but not health-gating


@pytest.mark.asyncio(loop_scope="function")
async def test_health_resend_unreachable(client, monkeypatch):
    monkeypatch.setattr("app.api.health.settings.resend_api_key", "re_test")

    async def failing_check():
        return "unreachable"
    monkeypatch.setattr("app.api.health._check_resend", failing_check)
    r = await client.get("/health")
    assert r.json()["resend"] == "unreachable"
    assert r.json()["overall"] == "degraded"
