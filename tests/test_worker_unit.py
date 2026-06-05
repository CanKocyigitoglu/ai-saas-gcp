from app import worker


def test_worker_process_message_saves_postprocessed_output(monkeypatch):

    async def fake_generate_ecowaste_interpretation(original_output, processed_output):
        return "BitNet explanation: two cans should be placed in the metal recycling bin."

    captured = {}

    def fake_save_postprocessed_output(**kwargs):
        captured.update(kwargs)
        return {
            "id": kwargs["job_id"],
            "job_id": kwargs["job_id"],
            "processed_output": kwargs["processed_output"],
        }

    monkeypatch.setattr(worker, "save_postprocessed_output", fake_save_postprocessed_output)
    monkeypatch.setattr(worker, "generate_ecowaste_interpretation", fake_generate_ecowaste_interpretation)

    message = {
        "job_id": "job-123",
        "request_type": "image",
        "input_summary": "traffic.png",
        "model": "ecowaste-yolo-taco-best",
        "firebase_output_id": "firebase-doc-1",
        "source_interaction_id": 7,
        "output": {
            "predictions": [
                {"label": "car", "confidence": 0.92},
                {"label": "person", "confidence": 0.81},
            ]
        },
    }

    result = worker.process_message(message)

    assert result["id"] == "job-123"
    assert captured["job_id"] == "job-123"
    assert captured["request_type"] == "image"
    assert captured["firebase_output_id"] == "firebase-doc-1"
    assert captured["processed_output"]["label_counts"] == {"car": 1, "person": 1}
    assert captured["processed_output"]["high_confidence_count"] == 2
    assert "BitNet explanation" in captured["processed_output"]["bitnet_interpretation"]
