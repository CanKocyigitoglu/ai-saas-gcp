from fastapi.testclient import TestClient
from app.main import app

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


def test_image_predict():
    response = client.post(
        "/api/v1/image/predict",
        files={"file": ("sample.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["size_bytes"] > 0
    assert data["model"] == "yolo11n-placeholder"
    assert len(data["predictions"]) == 1
