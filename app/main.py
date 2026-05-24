from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.crud import (
    create_interaction,
    get_interaction,
    interaction_to_dict,
    list_interactions,
)
from app.database import get_db, init_db
from app.schemas import (
    ImageResponse,
    InteractionHistoryResponse,
    TextRequest,
    TextResponse,
)
from app.services.inference import predict_image_objects
from app.services.llm_client import generate_bitnet_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI SaaS on GCP",
    description="A FastAPI-based SaaS prototype for image and language model inference.",
    version="0.4.0",
    lifespan=lifespan,
)


def pydantic_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-saas-api",
        "version": "0.4.0",
    }


@app.post("/api/v1/text/generate", response_model=TextResponse)
async def generate_text(request: TextRequest, db: Session = Depends(get_db)):
    try:
        output = await generate_bitnet_response(request.prompt)
    except RuntimeError as exc:
        create_interaction(
            db=db,
            request_type="text",
            input_summary=request.prompt[:500],
            output={"error": str(exc)},
            model="bitnet-b1.58-2B-4T",
            status_code=503,
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response = TextResponse(
        input=request.prompt,
        output=output,
        model="bitnet-b1.58-2B-4T",
    )

    create_interaction(
        db=db,
        request_type="text",
        input_summary=request.prompt[:500],
        output=pydantic_to_dict(response),
        model=response.model,
        status_code=200,
    )

    return response


@app.post("/api/v1/image/predict", response_model=ImageResponse)
async def predict_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    content = await file.read()
    size_bytes = len(content)

    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    try:
        predictions = predict_image_objects(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ImageResponse(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=size_bytes,
        num_predictions=len(predictions),
        predictions=predictions,
        model="yolo11n",
    )

    create_interaction(
        db=db,
        request_type="image",
        input_summary=f"{file.filename} | {file.content_type} | {size_bytes} bytes",
        output=pydantic_to_dict(response),
        model=response.model,
        status_code=200,
    )

    return response


@app.get("/api/v1/history", response_model=list[InteractionHistoryResponse])
def get_history(
    request_type: str | None = Query(
        default=None,
        pattern="^(text|image)$",
        description="Filter by request type: text or image",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    interactions = list_interactions(
        db=db,
        request_type=request_type,
        limit=limit,
    )

    return [interaction_to_dict(item) for item in interactions]


@app.get("/api/v1/history/{interaction_id}", response_model=InteractionHistoryResponse)
def get_history_item(interaction_id: int, db: Session = Depends(get_db)):
    interaction = get_interaction(db=db, interaction_id=interaction_id)

    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    return interaction_to_dict(interaction)
