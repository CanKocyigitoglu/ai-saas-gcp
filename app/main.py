from fastapi import FastAPI, File, UploadFile, HTTPException
from app.schemas import TextRequest, TextResponse, ImageResponse
from app.services.inference import generate_text_response, predict_image_objects

app = FastAPI(
    title="AI SaaS on GCP",
    description="A FastAPI-based SaaS prototype for image and language model inference.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-saas-api",
        "version": "0.1.0",
    }


@app.post("/api/v1/text/generate", response_model=TextResponse)
def generate_text(request: TextRequest):
    output = generate_text_response(request.prompt)

    return TextResponse(
        input=request.prompt,
        output=output,
        model="bitnet-placeholder",
    )


@app.post("/api/v1/image/predict", response_model=ImageResponse)
async def predict_image(file: UploadFile = File(...)):
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    content = await file.read()
    size_bytes = len(content)

    predictions = predict_image_objects(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=size_bytes,
    )

    return ImageResponse(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=size_bytes,
        predictions=predictions,
        model="yolo11n-placeholder",
    )
