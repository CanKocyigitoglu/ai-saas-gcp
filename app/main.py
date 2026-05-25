from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.crud import (
    create_interaction,
    get_interaction,
    interaction_to_dict,
    list_interactions,
)
from app.database import get_db, init_db
from app.schemas import (
    FirebaseOutputCreate,
    FirebaseOutputResponse,
    FirebaseOutputUpdate,
    ImageResponse,
    InteractionHistoryResponse,
    PostprocessResultResponse,
    TextRequest,
    TextResponse,
)
from app.services.firebase_store import (
    delete_model_output as firebase_delete_model_output,
    get_model_output as firebase_get_model_output,
    list_model_outputs as firebase_list_model_outputs,
    save_model_output as firebase_save_model_output,
    update_model_output as firebase_update_model_output,
    get_postprocessed_output as firebase_get_postprocessed_output,
    list_postprocessed_outputs as firebase_list_postprocessed_outputs,
)
from app.services.inference import predict_image_objects
from app.services.llm_client import generate_bitnet_response
from app.services.rabbitmq_client import publish_postprocess_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI SaaS on GCP",
    description="A FastAPI-based SaaS prototype for image and language model inference.",
    version="0.6.0",
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
        "version": "0.6.0",
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

    try:
        firebase_doc = firebase_save_model_output(
            request_type="text",
            input_summary=request.prompt[:500],
            model=response.model,
            output=pydantic_to_dict(response),
            metadata={"endpoint": "/api/v1/text/generate"},
        )
        response.firebase_output_id = firebase_doc.get("id")
    except RuntimeError:
        response.firebase_output_id = None

    try:
        response.postprocess_job_id = publish_postprocess_job(
            request_type="text",
            input_summary=request.prompt[:500],
            model=response.model,
            output=pydantic_to_dict(response),
            firebase_output_id=response.firebase_output_id,
        )
    except Exception:
        response.postprocess_job_id = None

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

    try:
        firebase_doc = firebase_save_model_output(
            request_type="image",
            input_summary=f"{file.filename} | {file.content_type} | {size_bytes} bytes",
            model=response.model,
            output=pydantic_to_dict(response),
            metadata={"endpoint": "/api/v1/image/predict"},
        )
        response.firebase_output_id = firebase_doc.get("id")
    except RuntimeError:
        response.firebase_output_id = None

    try:
        response.postprocess_job_id = publish_postprocess_job(
            request_type="image",
            input_summary=f"{file.filename} | {file.content_type} | {size_bytes} bytes",
            model=response.model,
            output=pydantic_to_dict(response),
            firebase_output_id=response.firebase_output_id,
        )
    except Exception:
        response.postprocess_job_id = None

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


@app.post(
    "/api/v1/firebase/outputs",
    response_model=FirebaseOutputResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_firebase_output(payload: FirebaseOutputCreate):
    try:
        return firebase_save_model_output(
            request_type=payload.request_type,
            input_summary=payload.input_summary,
            model=payload.model,
            output=payload.output,
            metadata=payload.metadata,
            source_interaction_id=payload.source_interaction_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/firebase/outputs", response_model=list[FirebaseOutputResponse])
def list_firebase_outputs(
    request_type: str | None = Query(
        default=None,
        pattern="^(text|image|manual)$",
        description="Filter by stored output type",
    ),
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        return firebase_list_model_outputs(
            request_type=request_type,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/firebase/outputs/{document_id}", response_model=FirebaseOutputResponse)
def get_firebase_output(document_id: str):
    try:
        item = firebase_get_model_output(document_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if item is None:
        raise HTTPException(status_code=404, detail="Firebase output not found.")

    return item


@app.patch("/api/v1/firebase/outputs/{document_id}", response_model=FirebaseOutputResponse)
def update_firebase_output(document_id: str, payload: FirebaseOutputUpdate):
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No update fields provided.")

    try:
        item = firebase_update_model_output(document_id, updates)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if item is None:
        raise HTTPException(status_code=404, detail="Firebase output not found.")

    return item


@app.delete("/api/v1/firebase/outputs/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_firebase_output(document_id: str):
    try:
        deleted = firebase_delete_model_output(document_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Firebase output not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/v1/postprocess/results", response_model=list[PostprocessResultResponse])
def list_postprocess_results(
    request_type: str | None = Query(
        default=None,
        pattern="^(text|image)$",
        description="Filter by postprocessed output type",
    ),
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        return firebase_list_postprocessed_outputs(
            request_type=request_type,
            limit=limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/v1/postprocess/results/{job_id}", response_model=PostprocessResultResponse)
def get_postprocess_result(job_id: str):
    try:
        item = firebase_get_postprocessed_output(job_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if item is None:
        raise HTTPException(status_code=404, detail="Postprocess result not found.")

    return item
