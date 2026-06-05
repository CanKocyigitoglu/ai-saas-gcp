from app.services.postprocess import postprocess_model_output


def test_postprocess_image_output_counts_labels_and_confidence():
    result = postprocess_model_output(
        request_type="image",
        output={
            "predictions": [
                {"label": "car", "confidence": 0.91},
                {"label": "person", "confidence": 0.80},
                {"label": "car", "confidence": 0.60},
            ]
        },
    )

    assert result["type"] == "ecowaste_image_postprocessing"
    assert result["num_predictions"] == 3
    assert result["label_counts"] == {"car": 2, "person": 1}
    assert result["high_confidence_count"] == 2
    assert result["max_confidence"] == 0.91


def test_postprocess_image_output_handles_no_predictions():
    result = postprocess_model_output(
        request_type="image",
        output={"predictions": []},
    )

    assert result["summary"] == "No objects were detected."
    assert result["num_predictions"] == 0
    assert result["unique_labels"] == []


def test_postprocess_text_output_counts_words_and_characters():
    result = postprocess_model_output(
        request_type="text",
        output={"output": "This is a generated answer."},
    )

    assert result["type"] == "text_postprocessing"
    assert result["word_count"] == 5
    assert result["character_count"] == len("This is a generated answer.")
    assert "Generated text contains" in result["summary"]


def test_postprocess_unknown_type_returns_generic_summary():
    result = postprocess_model_output(
        request_type="unknown",
        output={"z": 1, "a": 2},
    )

    assert result["type"] == "generic_postprocessing"
    assert result["keys"] == ["a", "z"]
