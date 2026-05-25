from collections import Counter
from typing import Any


def postprocess_model_output(
    request_type: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """
    Post-processes model outputs produced by the main API.

    For image outputs:
    - counts detected objects
    - summarises label distribution
    - extracts high-confidence detections

    For text outputs:
    - computes basic text statistics
    - produces a short preview
    """
    if request_type == "image":
        predictions = output.get("predictions", [])

        labels = [
            prediction.get("label", "unknown")
            for prediction in predictions
            if isinstance(prediction, dict)
        ]

        confidences = [
            float(prediction.get("confidence", 0.0))
            for prediction in predictions
            if isinstance(prediction, dict)
        ]

        label_counts = dict(Counter(labels))
        high_confidence_predictions = [
            prediction
            for prediction in predictions
            if isinstance(prediction, dict)
            and float(prediction.get("confidence", 0.0)) >= 0.75
        ]

        return {
            "type": "image_postprocessing",
            "num_predictions": len(predictions),
            "unique_labels": sorted(set(labels)),
            "label_counts": label_counts,
            "max_confidence": max(confidences) if confidences else None,
            "high_confidence_count": len(high_confidence_predictions),
            "high_confidence_predictions": high_confidence_predictions,
            "summary": _build_image_summary(label_counts),
        }

    if request_type == "text":
        generated_text = str(output.get("output", ""))
        words = generated_text.split()

        return {
            "type": "text_postprocessing",
            "character_count": len(generated_text),
            "word_count": len(words),
            "preview": generated_text[:200],
            "summary": f"Generated text contains {len(words)} words and {len(generated_text)} characters.",
        }

    return {
        "type": "generic_postprocessing",
        "summary": "Unsupported request type for specialised post-processing.",
        "keys": sorted(output.keys()),
    }


def _build_image_summary(label_counts: dict[str, int]) -> str:
    if not label_counts:
        return "No objects were detected."

    parts = [
        f"{label}: {count}"
        for label, count in sorted(label_counts.items())
    ]

    return "Detected objects - " + ", ".join(parts)
