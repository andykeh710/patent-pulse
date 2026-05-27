"""Tests for health endpoint probes (PR11)."""
from unittest.mock import AsyncMock, patch

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
async def test_health_resend_skipped_when_key_unset(client, monkeypatch):
    monkeypatch.setattr("app.api.health.settings.resend_api_key", "")
    r = await client.get("/health")
    assert r.json()["resend"] == "skipped"


@pytest.mark.asyncio(loop_scope="function")
async def test_health_resend_unreachable(client, monkeypatch):
    monkeypatch.setattr("app.api.health.settings.resend_api_key", "re_test")

    async def failing_check():
        return "unreachable"
    monkeypatch.setattr("app.api.health._check_resend", failing_check)
    r = await client.get("/health")
    assert r.json()["resend"] == "unreachable"
