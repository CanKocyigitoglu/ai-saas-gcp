import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import pika


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://ai_user:ai_password@rabbitmq:5672/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "postprocess_jobs")


def publish_postprocess_job(
    request_type: str,
    output: dict[str, Any],
    model: str | None,
    input_summary: str | None,
    firebase_output_id: str | None = None,
    source_interaction_id: int | None = None,
) -> str:
    """
    Publish a post-processing job to RabbitMQ.
    Returns the generated job id.
    """
    job_id = str(uuid.uuid4())

    message = {
        "job_id": job_id,
        "request_type": request_type,
        "input_summary": input_summary,
        "model": model,
        "firebase_output_id": firebase_output_id,
        "source_interaction_id": source_interaction_id,
        "output": output,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)

    try:
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

        channel.basic_publish(
            exchange="",
            routing_key=RABBITMQ_QUEUE,
            body=json.dumps(message).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
            ),
        )

    finally:
        connection.close()

    return job_id
