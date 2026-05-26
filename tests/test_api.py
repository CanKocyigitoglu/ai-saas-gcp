import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import get_current_user
from app.schemas import BoundingBox, ImagePrediction
from app.services.postprocess import postprocess_model_output


def fake_current_user():
    return {
        "uid": "test-user-123",
        "email": "testuser@example.com",
        "email_verified": True,
        "claims": {
            "uid": "test-user-123",
            "email": "testuser@example.com",
            "email_verified": True,
        },
    }


@pytest.fixture(autouse=True)
def override_auth_dependency():
    app.dependency_overrides[get_current_user] = fake_current_user
    yield
    app.dependency_overrides.clear()


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


def fake_publish_postprocess_job(*args, **kwargs):
    return "job-test-123"


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


def test_text_generate_is_recorded_and_queued(monkeypatch):
    monkeypatch.setattr("app.main.generate_bitnet_response", fake_generate_bitnet_response)
    monkeypatch.setattr("app.main.firebase_save_model_output", fake_firebase_save_model_output)
    monkeypatch.setattr("app.main.publish_postprocess_job", fake_publish_postprocess_job)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/text/generate",
            json={"prompt": "Explain what this system does."},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "bitnet-b1.58-2B-4T"
        assert data["firebase_output_id"] == "firebase-test-doc"
        assert data["postprocess_job_id"] == "job-test-123"

        history_response = client.get("/api/v1/history?request_type=text&limit=10")
        assert history_response.status_code == 200

    history = history_response.json()
    assert any(
        item["request_type"] == "text"
        and item["output"]["input"] == "Explain what this system does."
        and item["model"] == "bitnet-b1.58-2B-4T"
        for item in history
    )


def test_image_predict_is_recorded_and_queued(monkeypatch):
    monkeypatch.setattr("app.main.predict_image_objects", fake_predict_image_objects)
    monkeypatch.setattr("app.main.firebase_save_model_output", fake_firebase_save_model_output)
    monkeypatch.setattr("app.main.publish_postprocess_job", fake_publish_postprocess_job)

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
        assert data["firebase_output_id"] == "firebase-test-doc"
        assert data["postprocess_job_id"] == "job-test-123"

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


def test_postprocess_image_output():
    result = postprocess_model_output(
        request_type="image",
        output={
            "predictions": [
                {"label": "car", "confidence": 0.91},
                {"label": "person", "confidence": 0.81},
                {"label": "car", "confidence": 0.60},
            ]
        },
    )

    assert result["type"] == "image_postprocessing"
    assert result["num_predictions"] == 3
    assert result["label_counts"]["car"] == 2
    assert result["high_confidence_count"] == 2


def test_postprocess_text_output():
    result = postprocess_model_output(
        request_type="text",
        output={"output": "This is a short generated answer."},
    )

    assert result["type"] == "text_postprocessing"
    assert result["word_count"] == 6


def test_postprocess_result_endpoints(monkeypatch):
    fake_result = {
        "id": "job-test-123",
        "job_id": "job-test-123",
        "request_type": "image",
        "input_summary": "traffic.png",
        "model": "yolo11n",
        "firebase_output_id": "firebase-test-doc",
        "source_interaction_id": None,
        "original_output": {"predictions": []},
        "processed_output": {"summary": "No objects were detected."},
        "metadata": {"worker": "postprocess-worker"},
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    monkeypatch.setattr("app.main.firebase_list_postprocessed_outputs", lambda request_type=None, limit=50: [fake_result])
    monkeypatch.setattr("app.main.firebase_get_postprocessed_output", lambda job_id: fake_result)

    with TestClient(app) as client:
        list_response = client.get("/api/v1/postprocess/results?limit=5")
        assert list_response.status_code == 200
        assert list_response.json()[0]["job_id"] == "job-test-123"

        get_response = client.get("/api/v1/postprocess/results/job-test-123")
        assert get_response.status_code == 200
        assert get_response.json()["job_id"] == "job-test-123"


def test_auth_me_returns_current_user():
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == "test-user-123"
    assert data["email"] == "testuser@example.com"


def test_protected_endpoint_requires_authentication():
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        response = client.get("/api/v1/history")

    assert response.status_code == 401


def test_metrics_endpoint_is_public():
    app.dependency_overrides.clear()

    with TestClient(app) as client:
        health_response = client.get("/health")
        metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert metrics_response.status_code == 200
    assert "ai_saas_http_requests_total" in metrics_response.text
    assert "ai_saas_http_request_duration_seconds" in metrics_response.text
