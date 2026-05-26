FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV YOLO_DEVICE=cpu
ENV YOLO_MODEL_PATH=yolo11n.pt
ENV YOLO_CONF_THRESHOLD=0.25
ENV YOLO_IMAGE_SIZE=640

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup pytest.ini ./pytest.ini
COPY --chown=appuser:appgroup tests ./tests
COPY --chown=appuser:appgroup scripts ./scripts

RUN mkdir -p /app/.cache /app/.config && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
