from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language input for the LLM service")


class TextResponse(BaseModel):
    input: str
    output: str
    model: str


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class ImagePrediction(BaseModel):
    label: str
    confidence: float
    bbox: BoundingBox | None = None


class ImageResponse(BaseModel):
    filename: str
    content_type: str | None
    size_bytes: int
    num_predictions: int
    predictions: list[ImagePrediction]
    model: str
