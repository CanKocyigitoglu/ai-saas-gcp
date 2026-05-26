import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.services import auth as auth_service


def test_get_current_user_rejects_missing_token():
    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_current_user(None)

    assert exc_info.value.status_code == 401
    assert "Missing Firebase ID token" in exc_info.value.detail


def test_get_current_user_rejects_non_bearer_scheme():
    credentials = HTTPAuthorizationCredentials(
        scheme="Basic",
        credentials="abc",
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert "Invalid authentication scheme" in exc_info.value.detail


def test_get_current_user_accepts_valid_firebase_token(monkeypatch):
    monkeypatch.setattr(auth_service, "initialise_firebase_admin", lambda: None)
    monkeypatch.setattr(
        auth_service.auth,
        "verify_id_token",
        lambda token: {
            "uid": "user-123",
            "email": "test@example.com",
            "email_verified": True,
        },
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="valid-token",
    )

    user = auth_service.get_current_user(credentials)

    assert user["uid"] == "user-123"
    assert user["email"] == "test@example.com"
    assert user["email_verified"] is True


def test_get_current_user_rejects_invalid_firebase_token(monkeypatch):
    monkeypatch.setattr(auth_service, "initialise_firebase_admin", lambda: None)

    def fake_verify_id_token(token):
        raise ValueError("bad token")

    monkeypatch.setattr(auth_service.auth, "verify_id_token", fake_verify_id_token)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_current_user(credentials)

    assert exc_info.value.status_code == 401
    assert "Invalid or expired Firebase ID token" in exc_info.value.detail
