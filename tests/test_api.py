from fastapi.testclient import TestClient

from app.main import app
from app.schemas import BoundingBox, ImagePrediction

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_text_generate():
    response = client.post(
        "/api/v1/text/generate",
        json={"prompt": "Explain what this system does."},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["input"] == "Explain what this system does."
    assert "Placeholder LLM response" in data["output"]
    assert data["model"] == "bitnet-placeholder"


def test_image_predict(monkeypatch):
    def fake_predict_image_objects(image_bytes: bytes):
        return [
            ImagePrediction(
                label="person",
                confidence=0.91,
                bbox=BoundingBox(x1=1.0, y1=2.0, x2=100.0, y2=120.0),
            )
        ]

    monkeypatch.setattr("app.main.predict_image_objects", fake_predict_image_objects)

    response = client.post(
        "/api/v1/image/predict",
        files={"file": ("sample.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["size_bytes"] > 0
    assert data["model"] == "yolo11n"
    assert data["num_predictions"] == 1
    assert data["predictions"][0]["label"] == "person"


def test_image_predict_rejects_non_image():
    response = client.post(
        "/api/v1/image/predict",
        files={"file": ("sample.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
