"""Tests for email template rendering."""

from app.email.sender import _render


def test_magic_link_template_renders():
    out = _render(
        "magic_link.html",
        magic_link_url="http://x/verify?token=abc",
        magic_link_base_url="http://x",
    )
    assert "Invention Index 8" in out
    assert "Manage email preferences" in out


def test_instant_alert_template_renders():
    out = _render(
        "instant_alert.html",
        topic_name="Test Topic",
        match_count="3",
        patents=[
            {
                "title": "P1",
                "url": "http://x/p/1",
                "assignee": "A",
                "publication_number": "US123",
                "expiry_status": "active",
                "abstract_snippet": "abstract",
            }
        ],
        unsubscribe_url="http://x/unsub",
        magic_link_base_url="http://x",
    )
    assert "P1" in out
    assert "US123" in out
    assert "Unsubscribe" in out
    assert "Invention Index 8" in out


def test_weekly_digest_template_renders_sections():
    out = _render(
        "weekly_digest.html",
        greeting="Weekly Digest",
        intro_blurb="Headline here",
        sections=[{"title": "S1", "body": "Body 1"}, {"title": "S2", "body": "Body 2"}],
        call_to_action="Act",
        cta_url="http://x",
        cta_text="Go",
        unsubscribe_url="http://x/unsub",
        magic_link_base_url="http://x",
    )
    assert "S1" in out
    assert "Body 1" in out
    assert "S2" in out
    assert "Unsubscribe" in out
    assert "Invention Index 8" in out


def test_all_templates_have_no_leftover_tags():
    for name in ("magic_link.html", "instant_alert.html", "weekly_digest.html"):
        out = _render(
            name,
            magic_link_url="http://x",
            magic_link_base_url="http://x",
            topic_name="T",
            match_count="1",
            patents=[
                {
                    "title": "P",
                    "url": "x",
                    "assignee": "A",
                    "publication_number": "N",
                    "expiry_status": "active",
                    "abstract_snippet": "S",
                }
            ],
            greeting="G",
            intro_blurb="I",
            sections=[{"title": "T", "body": "B"}],
            call_to_action="C",
            cta_url="x",
            cta_text="Go",
            unsubscribe_url="http://x/unsub",
        )
        assert "{{" not in out, f"{name} has unrendered {{"
        assert "{%" not in out, f"{name} has unrendered {{%"
