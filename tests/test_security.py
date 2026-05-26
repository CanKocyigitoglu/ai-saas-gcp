from fastapi.testclient import TestClient

from app.main import app
from app.security import (
    validate_image_content_type,
    validate_upload_size,
)


def test_security_headers_are_added_to_public_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_metrics_endpoint_remains_public():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "ai_saas_http_requests_total" in response.text


def test_upload_content_type_validation_accepts_png():
    validate_image_content_type("image/png")


def test_upload_content_type_validation_rejects_text():
    try:
        validate_image_content_type("text/plain")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Expected validation to reject text/plain")


def test_upload_size_validation_rejects_empty_file():
    try:
        validate_upload_size(0)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Expected validation to reject empty file")


def test_request_size_limit_rejects_large_request(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "10")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/text/generate",
            json={"prompt": "This request body is larger than ten bytes."},
        )

    assert response.status_code == 413


def test_rate_limit_blocks_after_threshold(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    with TestClient(app) as client:
        first = client.get("/api/v1/history")
        second = client.get("/api/v1/history")
        third = client.get("/api/v1/history")

    assert first.status_code in {401, 429}
    assert second.status_code in {401, 429}
    assert third.status_code == 429
