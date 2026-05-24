from fastapi.testclient import TestClient

from app.main import app
from app.schemas import BoundingBox, ImagePrediction


def fake_firebase_save_model_output(*args, **kwargs):
    return {
        "id": "firebase-test-doc",
        "request_type": kwargs.get("request_type", "manual"),
        "input_summary": kwargs.get("input_summary"),
        "model": kwargs.get("model"),
        "output": kwargs.get("output", {}),
        "metadata": kwargs.get("metadata", {}),
        "source_interaction_id": kwargs.get("source_interaction_id"),
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


async def fake_generate_bitnet_response(prompt: str):
    return f"Fake BitNet response for: {prompt}"


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


def test_text_generate_is_recorded(monkeypatch):
    monkeypatch.setattr("app.main.generate_bitnet_response", fake_generate_bitnet_response)
    monkeypatch.setattr("app.main.firebase_save_model_output", fake_firebase_save_model_output)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/text/generate",
            json={"prompt": "Explain what this system does."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "bitnet-b1.58-2B-4T"
        assert "Fake BitNet response" in data["output"]
        assert data["firebase_output_id"] == "firebase-test-doc"

        history_response = client.get("/api/v1/history?request_type=text&limit=10")
        assert history_response.status_code == 200

    history = history_response.json()
    assert any(
        item["request_type"] == "text"
        and item["output"]["input"] == "Explain what this system does."
        and item["model"] == "bitnet-b1.58-2B-4T"
        for item in history
    )


def test_image_predict_is_recorded(monkeypatch):
    monkeypatch.setattr("app.main.predict_image_objects", fake_predict_image_objects)
    monkeypatch.setattr("app.main.firebase_save_model_output", fake_firebase_save_model_output)

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
        assert data["firebase_output_id"] == "firebase-test-doc"

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


def test_firebase_crud_endpoints(monkeypatch):
    fake_doc = fake_firebase_save_model_output(
        request_type="manual",
        input_summary="manual test",
        model="test-model",
        output={"result": "ok"},
        metadata={"source": "unit-test"},
    )

    monkeypatch.setattr("app.main.firebase_save_model_output", lambda **kwargs: fake_doc)
    monkeypatch.setattr("app.main.firebase_list_model_outputs", lambda request_type=None, limit=50: [fake_doc])
    monkeypatch.setattr("app.main.firebase_get_model_output", lambda document_id: fake_doc)
    monkeypatch.setattr("app.main.firebase_update_model_output", lambda document_id, updates: {**fake_doc, **updates})
    monkeypatch.setattr("app.main.firebase_delete_model_output", lambda document_id: True)

    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/firebase/outputs",
            json={
                "request_type": "manual",
                "input_summary": "manual test",
                "model": "test-model",
                "output": {"result": "ok"},
                "metadata": {"source": "unit-test"},
            },
        )
        assert create_response.status_code == 201
        assert create_response.json()["id"] == "firebase-test-doc"

        list_response = client.get("/api/v1/firebase/outputs?limit=5")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        get_response = client.get("/api/v1/firebase/outputs/firebase-test-doc")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == "firebase-test-doc"

        patch_response = client.patch(
            "/api/v1/firebase/outputs/firebase-test-doc",
            json={"metadata": {"reviewed": True}},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["metadata"]["reviewed"] is True

        delete_response = client.delete("/api/v1/firebase/outputs/firebase-test-doc")
        assert delete_response.status_code == 204
