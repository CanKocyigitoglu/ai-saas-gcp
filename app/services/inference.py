import os
from functools import lru_cache
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO

from app.schemas import BoundingBox, ImagePrediction


def generate_text_response(prompt: str) -> str:
    """
    Placeholder for the BitNet LLM service.
    Later, this function will call the real BitNet inference pipeline.
    """
    return f"Placeholder LLM response for: {prompt}"


@lru_cache(maxsize=1)
def get_yolo_model() -> YOLO:
    """
    Load YOLO11n once and reuse it across requests.

    By default, Ultralytics downloads yolo11n.pt automatically on first use
    if it is not already available in the container.
    """
    model_path = os.getenv("YOLO_MODEL_PATH", "yolo11n.pt")
    return YOLO(model_path)


def predict_image_objects(image_bytes: bytes) -> list[ImagePrediction]:
    """
    Run YOLO11n object detection on uploaded image bytes.
    """
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("Uploaded file is not a valid image.") from exc

    model = get_yolo_model()

    conf_threshold = float(os.getenv("YOLO_CONF_THRESHOLD", "0.25"))
    image_size = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
    device = os.getenv("YOLO_DEVICE", "cpu")

    results = model.predict(
        source=image,
        conf=conf_threshold,
        imgsz=image_size,
        device=device,
        verbose=False,
    )

    if not results:
        return []

    result = results[0]
    predictions: list[ImagePrediction] = []

    if result.boxes is None:
        return predictions

    names = result.names

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        label = names.get(class_id, str(class_id)) if isinstance(names, dict) else str(class_id)

        predictions.append(
            ImagePrediction(
                label=label,
                confidence=round(confidence, 4),
                bbox=BoundingBox(
                    x1=round(float(x1), 2),
                    y1=round(float(y1), 2),
                    x2=round(float(x2), 2),
                    y2=round(float(y2), 2),
                ),
            )
        )

    return predictions
