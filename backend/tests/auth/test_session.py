"""Tests for JWT session sign/verify."""

import jwt
import pytest

SECRET = "test-secret-key-for-tests"


def test_jwt_roundtrip():
    import datetime as _dt

    now = _dt.datetime.now(_dt.timezone.utc)
    payload = {"sub": "local-user", "iat": now, "exp": now + _dt.timedelta(days=30)}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    decoded = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert decoded["sub"] == "local-user"


def test_expired_jwt_rejected():
    import datetime as _dt

    past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=1)
    payload = {"sub": "local-user", "iat": past - _dt.timedelta(days=30), "exp": past}
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": True})


def test_tampered_jwt_rejected():
    token = jwt.encode({"sub": "local-user", "exp": 9999999999}, SECRET, algorithm="HS256")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(tampered, SECRET, algorithms=["HS256"])
