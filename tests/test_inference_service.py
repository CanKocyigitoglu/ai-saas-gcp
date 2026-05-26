from io import BytesIO

import pytest
from PIL import Image

from app.services import inference


class FakeScalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class FakeXYXY:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeBox:
    cls = [FakeScalar(2)]
    conf = [FakeScalar(0.87654)]
    xyxy = [FakeXYXY([1.0, 2.0, 100.0, 120.0])]


class FakeResult:
    boxes = [FakeBox()]
    names = {2: "car"}


class FakeModel:
    def predict(self, source, conf, imgsz, device, verbose):
        return [FakeResult()]


def make_png_bytes():
    image = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_predict_image_objects_rejects_invalid_image_bytes():
    with pytest.raises(ValueError):
        inference.predict_image_objects(b"not an image")


def test_predict_image_objects_uses_yolo_model(monkeypatch):
    monkeypatch.setattr(inference, "get_yolo_model", lambda: FakeModel())

    predictions = inference.predict_image_objects(make_png_bytes())

    assert len(predictions) == 1
    assert predictions[0].label == "car"
    assert predictions[0].confidence == 0.8765
    assert predictions[0].bbox.x1 == 1.0
    assert predictions[0].bbox.y2 == 120.0
