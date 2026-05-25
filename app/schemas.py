from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language input for the LLM service")


class TextResponse(BaseModel):
    input: str
    output: str
    model: str
    firebase_output_id: str | None = None
    postprocess_job_id: str | None = None


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
    firebase_output_id: str | None = None
    postprocess_job_id: str | None = None


class InteractionHistoryResponse(BaseModel):
    id: int
    request_type: str
    input_summary: str | None
    model: str | None
    status_code: int
    output: dict[str, Any]
    created_at: datetime


class FirebaseOutputCreate(BaseModel):
    request_type: str = Field(..., pattern="^(text|image|manual)$")
    input_summary: str | None = None
    model: str | None = None
    output: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_interaction_id: int | None = None


class FirebaseOutputUpdate(BaseModel):
    input_summary: str | None = None
    model: str | None = None
    output: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class FirebaseOutputResponse(BaseModel):
    id: str
    request_type: str
    input_summary: str | None = None
    model: str | None = None
    output: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_interaction_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class PostprocessResultResponse(BaseModel):
    id: str
    job_id: str
    request_type: str
    input_summary: str | None = None
    model: str | None = None
    firebase_output_id: str | None = None
    source_interaction_id: int | None = None
    original_output: dict[str, Any]
    processed_output: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
