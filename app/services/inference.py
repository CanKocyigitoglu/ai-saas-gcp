from app.schemas import ImagePrediction


def generate_text_response(prompt: str) -> str:
    """
    Placeholder for the BitNet LLM service.
    Later, this function will call the real BitNet inference pipeline.
    """
    return f"Placeholder LLM response for: {prompt}"


def predict_image_objects(filename: str, content_type: str | None, size_bytes: int) -> list[ImagePrediction]:
    """
    Placeholder for the YOLO service.
    Later, this function will call YOLO11n inference.
    """
    return [
        ImagePrediction(label="placeholder_object", confidence=0.99)
    ]
