from app.api.v1.patents import _normalize_office_filter, _normalize_score_filter


def test_normalize_office_filter_accepts_frontend_code() -> None:
    assert _normalize_office_filter("US") == "USPTO"


def test_normalize_office_filter_preserves_stored_office_value() -> None:
    assert _normalize_office_filter("EPO") == "EPO"


def test_normalize_score_filter_accepts_ui_percentage() -> None:
    assert _normalize_score_filter(65) == 0.65


def test_normalize_score_filter_treats_one_as_one_percent() -> None:
    assert _normalize_score_filter(1) == 0.01


def test_normalize_score_filter_preserves_existing_fraction() -> None:
    assert _normalize_score_filter(0.65) == 0.65
