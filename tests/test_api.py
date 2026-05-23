from fastapi.testclient import TestClient

from app.main import app
from app.schemas import BoundingBox, ImagePrediction


def fake_predict_image_objects(image_bytes: bytes):
    return [
        ImagePrediction(
            label="car",
            confidence=0.91,
            bbox=BoundingBox(x1=1.0, y1=2.0, x2=100.0, y2=120.0),
        )
    ]


def test_health_check():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_text_generate_is_recorded():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/text/generate",
            json={"prompt": "Explain what this system does."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "bitnet-placeholder"

        history_response = client.get("/api/v1/history?request_type=text&limit=10")
        assert history_response.status_code == 200

    history = history_response.json()
    assert any(
        item["request_type"] == "text"
        and item["output"]["input"] == "Explain what this system does."
        for item in history
    )


def test_image_predict_is_recorded(monkeypatch):
    monkeypatch.setattr("app.main.predict_image_objects", fake_predict_image_objects)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/image/predict",
            files={"file": ("traffic.png", b"fake-image-bytes", "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "traffic.png"
        assert data["model"] == "yolo11n"
        assert data["num_predictions"] == 1
        assert data["predictions"][0]["label"] == "car"

        history_response = client.get("/api/v1/history?request_type=image&limit=10")
        assert history_response.status_code == 200

    history = history_response.json()
    assert any(
        item["request_type"] == "image"
        and item["output"]["filename"] == "traffic.png"
        for item in history
    )


def test_image_predict_rejects_non_image():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/image/predict",
            files={"file": ("sample.txt", b"not an image", "text/plain")},
        )

    assert response.status_code == 400


def test_history_item_not_found():
    with TestClient(app) as client:
        response = client.get("/api/v1/history/999999999")

    assert response.status_code == 404
