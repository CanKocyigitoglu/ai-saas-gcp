from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language input for the LLM service")


class TextResponse(BaseModel):
    input: str
    output: str
    model: str


class ImagePrediction(BaseModel):
    label: str
    confidence: float


class ImageResponse(BaseModel):
    filename: str
    content_type: str | None
    size_bytes: int
    predictions: list[ImagePrediction]
    model: str
